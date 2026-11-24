#!/usr/bin/env python3
# Copyright:
#   - Copyright © 2026 Alberto Villa Osorno.
# SPDX-License-Identifier:
#   - Apache-2.0
# Confidential:
#   - false
# License-File:
#   - LICENSE
#
# Boundary-Contract:
# - Owns:
#   - Ordered, source-bound native C frontend to verified Malbolge handoff.
# - Must-Not:
#   - Parse C, replace Clang, manufacture typed IR, or bypass guest verification.
# - Allows:
#   - Inputs: explicit C file, source ID, and three trusted executable paths.
#   - Outputs: downstream verified .malbolge artifact or explicit failure.
#   - Side effects: bounded source reads and sequential child invocations.
# - Split-When:
#   - The native compiler CLI integrates source admission in one process.
# - Merge-When:
#   - This bridge becomes the standard native compiler frontend command.
# - Summary:
#   - Prevents producer failure and source/JSON mismatch from publishing code.
# - Description:
#   - The JSON adapter/layout backend retain typed and guest semantic authority.
# - Usage:
#   - python3 c2malbolge.py --frontend BIN --json-adapter BIN
#     --layout-backend BIN --guest-include DIR --resource-dir DIR
#     --source-id ID --output TARGET [--capsule] SOURCE.c
# - Defaults:
#   - Any failed stage or changed source rejects before the next stage.

"""Compose explicitly selected compiler stages without relaxing their checks."""

import argparse
import hashlib
import json
import os
import signal
import stat
import subprocess
import sys
import tempfile
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import cast

MAX_SOURCE_BYTES = 64 * 1024 * 1024
MAX_JSON_BYTES = 1_048_576
CHUNK_BYTES = 64 * 1024
REPOSITORY_ROOT = Path(__file__).resolve().parents[5]
PINNED_LLVM_VERSION = "22.1.8"
PORTABLE_SOURCE_CHARACTERS = frozenset(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-"
)


@dataclass(frozen=True, slots=True)
class Arguments:
    """Fully typed command arguments after argparse admission."""

    frontend: str
    json_adapter: str
    layout_backend: str
    guest_include: str
    resource_dir: str
    source_id: str
    output: str
    capsule: bool
    source: str
    max_wall_seconds: int | None


class PipelineError(Exception):
    """One stage could not establish the supported compiler contract."""


@dataclass(frozen=True, slots=True)
class SourceFingerprint:
    """Content and stable inode metadata from one checked source acquisition."""

    sha256: str
    identity: tuple[int, int, int, int, int]


def source_fingerprint(path: Path) -> SourceFingerprint:
    """Pin original source bytes and file identity across all compiler stages."""
    flags = os.O_RDONLY | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_CLOEXEC", 0)
    flags |= getattr(os, "O_BINARY", 0)
    try:
        descriptor = os.open(path, flags)
        with os.fdopen(descriptor, "rb") as stream:
            before = os.fstat(stream.fileno())
            if not stat.S_ISREG(before.st_mode) or before.st_size > MAX_SOURCE_BYTES:
                raise PipelineError("source must be a regular file of at most 64 MiB")
            digest = hashlib.sha256()
            total = 0
            while chunk := stream.read(CHUNK_BYTES):
                total += len(chunk)
                if total > MAX_SOURCE_BYTES:
                    raise PipelineError("source exceeds the 64 MiB bound")
                digest.update(chunk)
            after = os.fstat(stream.fileno())
        named = path.stat()
    except OSError as error:
        raise PipelineError(f"cannot read stable source: {error}") from error

    def identity(item: os.stat_result) -> tuple[int, int, int, int, int]:
        return (
            item.st_dev,
            item.st_ino,
            item.st_size,
            item.st_mtime_ns,
            item.st_ctime_ns,
        )

    if (
        not stat.S_ISREG(after.st_mode)
        or not stat.S_ISREG(named.st_mode)
        or identity(before) != identity(after)
        or identity(before) != identity(named)
        or total != before.st_size
    ):
        raise PipelineError("source changed during acquisition")
    return SourceFingerprint(digest.hexdigest(), identity(after))


def strict_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate normalized JSON field")
        result[key] = value
    return result


def admit_source_identity(frontend_bytes: bytes, source_id: str, digest: str) -> None:
    """Compare the normalized artifact to the actual source, not JSON assertions."""
    try:
        parsed = cast(
            object, json.loads(frontend_bytes, object_pairs_hook=strict_object)
        )
    except (RecursionError, UnicodeError, ValueError) as error:
        # A bounded byte stream can still exceed the JSON parser stack.
        raise PipelineError(f"invalid normalized frontend JSON: {error}") from error
    if not isinstance(parsed, dict):
        raise PipelineError("normalized frontend JSON lacks source identity")
    artifact = cast(dict[str, object], parsed)
    reported_value = artifact.get("source")
    if not isinstance(reported_value, dict):
        raise PipelineError("normalized frontend JSON lacks source identity")
    reported = cast(dict[str, object], reported_value)
    if reported.get("id") != source_id or reported.get("sha256") != digest:
        raise PipelineError("normalized frontend source ID or SHA-256 mismatch")


def remaining_seconds(deadline: float | None) -> float | None:
    """Use one budget across both child stages; zero is never a new allowance."""
    if deadline is None:
        return None
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise PipelineError("compiler wall-time limit exceeded")
    return remaining


def terminate_child(child: subprocess.Popen[bytes]) -> None:
    """Reap our own child and its ordinary POSIX descendants after failure."""
    try:
        if os.name == "posix":
            # The leader may have exited while a same-group descendant still
            # holds the frontend stdout pipe open. Kill the entire owned group.
            os.killpg(child.pid, signal.SIGKILL)
        elif child.poll() is None:
            child.kill()
    except ProcessLookupError:
        pass
    try:
        _ = child.wait(timeout=3)
    except subprocess.TimeoutExpired:
        # A child that has escaped its process group cannot be reaped by
        # waiting forever. An ordinary child is always bounded here.
        pass


def run_frontend(arguments: Arguments, deadline: float | None) -> bytes:
    command = [
        arguments.frontend,
        "--guest-include",
        arguments.guest_include,
        "--resource-dir",
        arguments.resource_dir,
        "--source-id",
        arguments.source_id,
        arguments.source,
    ]
    _ = remaining_seconds(deadline)
    try:
        with subprocess.Popen(
            command, stdout=subprocess.PIPE, start_new_session=os.name == "posix"
        ) as child:
            stdout = child.stdout
            assert stdout is not None
            # A reader keeps the existing 1 MiB cap even when a frontend
            # stalls before EOF. Popen.communicate would buffer unlimited JSON.
            content: list[bytes] = []
            faults: list[OSError] = []

            def bounded_read() -> None:
                try:
                    content.append(cast(bytes, stdout.read(MAX_JSON_BYTES + 1)))
                except OSError as error:
                    faults.append(error)

            reader = threading.Thread(target=bounded_read, daemon=True)
            reader.start()
            try:
                reader.join(timeout=remaining_seconds(deadline))
            except PipelineError:
                terminate_child(child)
                raise
            if reader.is_alive():
                terminate_child(child)
                raise PipelineError("native C frontend wall-time limit exceeded")
            if faults:
                terminate_child(child)
                raise PipelineError(f"cannot read native C frontend: {faults[0]}")
            data = content[0]
            if len(data) > MAX_JSON_BYTES:
                terminate_child(child)
                raise PipelineError("native C frontend JSON is empty or exceeds 1 MiB")
            try:
                status = child.wait(timeout=remaining_seconds(deadline))
            except (subprocess.TimeoutExpired, PipelineError) as error:
                terminate_child(child)
                raise PipelineError(
                    "native C frontend wall-time limit exceeded"
                ) from error
    except OSError as error:
        raise PipelineError(f"cannot execute native C frontend: {error}") from error
    if status != 0:
        raise PipelineError(f"native C frontend failed with status {status}")
    if not data:
        raise PipelineError("native C frontend JSON is empty or exceeds 1 MiB")
    return data


def positive_wall_seconds(raw: str) -> int:
    try:
        seconds = int(raw)
    except ValueError as error:
        raise argparse.ArgumentTypeError("wall limit must be an integer") from error
    if not 1 <= seconds <= 86_400:
        raise argparse.ArgumentTypeError("wall limit must be 1..86400 seconds")
    return seconds


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    _ = parser.add_argument(
        "--max-wall-seconds",
        type=positive_wall_seconds,
        help="optional total wall-time budget for frontend and target lowering",
    )
    _ = parser.add_argument(
        "--repository-tools",
        action="store_true",
        help="use the built repository-pinned compiler tools and headers",
    )
    for flag in (
        "frontend",
        "json-adapter",
        "layout-backend",
        "guest-include",
        "resource-dir",
        "source-id",
    ):
        _ = parser.add_argument(f"--{flag}")
    _ = parser.add_argument("--output", required=True)
    _ = parser.add_argument("--capsule", action="store_true")
    _ = parser.add_argument("source", help="explicit C source file")
    return parser


def default_source_id(source: str) -> str:
    """Use the basename when portable, otherwise an unambiguous stable digest."""
    basename = Path(source).name
    if (
        basename
        and basename not in (".", "..")
        and all(character in PORTABLE_SOURCE_CHARACTERS for character in basename)
    ):
        return basename
    return f"source-{hashlib.sha256(os.fsencode(basename)).hexdigest()}.c"


def portable_source_id(source_id: str) -> bool:
    """Mirror the native frontend's portable ASCII path-component grammar."""
    return all(
        component not in ("", ".", "..")
        and all(character in PORTABLE_SOURCE_CHARACTERS for character in component)
        for component in source_id.split("/")
    )


def parse_arguments(
    argv: list[str] | None = None, *, repository_root: Path = REPOSITORY_ROOT
) -> Arguments:
    """Select exactly one trusted tool mode before reading any source bytes."""
    parser = build_parser()
    parsed = parser.parse_args(argv)
    configured = {
        "frontend": cast(str | None, parsed.frontend),
        "json-adapter": cast(str | None, parsed.json_adapter),
        "layout-backend": cast(str | None, parsed.layout_backend),
        "guest-include": cast(str | None, parsed.guest_include),
        "resource-dir": cast(str | None, parsed.resource_dir),
    }
    source_id = cast(str | None, parsed.source_id)
    source = cast(str, parsed.source)
    if cast(bool, parsed.repository_tools):
        if overrides := [
            flag for flag, value in configured.items() if value is not None
        ]:
            parser.error(
                "--repository-tools cannot be mixed with explicit tool flags: "
                + ", ".join(f"--{flag}" for flag in overrides)
            )
        native_name = (
            "malbolge-c-frontend.exe" if os.name == "nt" else "malbolge-c-frontend"
        )
        native = repository_root / (
            f".dependencies/compiler-c-frontend/{PINNED_LLVM_VERSION}/bin/{native_name}"
        )
        rust_root = repository_root / ".cache/rust/target/debug"
        rust_suffix = ".exe" if os.name == "nt" else ""
        configured = {
            "frontend": str(native),
            "json-adapter": str(rust_root / f"c2malbolge_json{rust_suffix}"),
            "layout-backend": str(rust_root / f"malbolge_layout{rust_suffix}"),
            "guest-include": str(
                repository_root / "src/runtime/guest-c-library/contract/include"
            ),
            "resource-dir": str(
                repository_root
                / f".dependencies/llvm/{PINNED_LLVM_VERSION}/lib/clang/22"
            ),
        }
        for flag in ("frontend", "json-adapter", "layout-backend"):
            binary = Path(configured[flag])
            if not binary.is_file() or not os.access(binary, os.X_OK):
                parser.error(
                    f"repository-pinned {flag} executable is unavailable: {binary}"
                )
        for flag in ("guest-include", "resource-dir"):
            directory = Path(configured[flag])
            if not directory.is_dir():
                parser.error(
                    f"repository-pinned {flag} directory is unavailable: {directory}"
                )
        if source_id is None:
            source_id = default_source_id(source)
    elif missing := [flag for flag, value in configured.items() if value is None]:
        parser.error(
            "explicit compiler tools required without --repository-tools: "
            + ", ".join(f"--{flag}" for flag in missing)
        )
    if source_id is None:
        parser.error("--source-id is required without --repository-tools")
    return Arguments(
        frontend=cast(str, configured["frontend"]),
        json_adapter=cast(str, configured["json-adapter"]),
        layout_backend=cast(str, configured["layout-backend"]),
        guest_include=cast(str, configured["guest-include"]),
        resource_dir=cast(str, configured["resource-dir"]),
        source_id=source_id,
        output=cast(str, parsed.output),
        capsule=cast(bool, parsed.capsule),
        source=source,
        max_wall_seconds=cast(int | None, parsed.max_wall_seconds),
    )


def sync_published_directory(target: Path) -> None:
    """Persist the final hard-link name before claiming compiler success."""
    if os.name != "posix":
        # Opening directories for fsync is not portable to Windows.
        return
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    flags |= getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_CLOEXEC", 0)
    try:
        descriptor = os.open(target.parent, flags)
        try:
            if not stat.S_ISDIR(os.fstat(descriptor).st_mode):
                raise PipelineError("publication sync target is not a directory")
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    except OSError as error:
        raise PipelineError(
            f"cannot sync published output directory: {error}"
        ) from error


def compile_source(arguments: Arguments) -> None:
    if not portable_source_id(arguments.source_id):
        raise PipelineError("source ID must be a portable relative path")
    if os.path.lexists(arguments.output):
        raise PipelineError("output path already exists (no-clobber)")
    deadline = (
        time.monotonic() + arguments.max_wall_seconds
        if arguments.max_wall_seconds is not None
        else None
    )
    source = Path(arguments.source)
    expected = source_fingerprint(source)
    _ = remaining_seconds(deadline)
    normalized = run_frontend(arguments, deadline)
    admit_source_identity(normalized, arguments.source_id, expected.sha256)
    if source_fingerprint(source) != expected:
        raise PipelineError("source changed during frontend compilation")
    target = Path(arguments.output)
    try:
        stage = tempfile.TemporaryDirectory(prefix=".c2malbolge-", dir=target.parent)
    except OSError as error:
        raise PipelineError(f"cannot stage guest target: {error}") from error

    # The downstream layout publisher runs on a private path. Do not expose
    # its artifact until source identity and the final guest file are checked.
    with stage as directory:
        staged = Path(directory) / target.name
        command = [
            arguments.json_adapter,
            "--layout-backend",
            arguments.layout_backend,
            "--output",
            str(staged),
        ]
        # The JSON adapter needs the original lexer bytes to distinguish an
        # unsigned-byte cast from an equal-width forged signed cast.
        command.extend(("--source", arguments.source))
        if arguments.capsule:
            command.append("--capsule")
        _ = remaining_seconds(deadline)
        try:
            with subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                start_new_session=os.name == "posix",
            ) as child:
                try:
                    _ = child.communicate(
                        input=normalized, timeout=remaining_seconds(deadline)
                    )
                except (subprocess.TimeoutExpired, PipelineError) as error:
                    terminate_child(child)
                    raise PipelineError(
                        "JSON-to-target adapter wall-time limit exceeded"
                    ) from error
                status = child.returncode
        except OSError as error:
            raise PipelineError(
                f"cannot execute JSON-to-target adapter: {error}"
            ) from error
        if status != 0:
            raise PipelineError(f"JSON-to-target adapter failed with status {status}")
        _ = remaining_seconds(deadline)
        try:
            published = staged.lstat()
        except OSError as error:
            raise PipelineError(f"adapter did not publish a target: {error}") from error
        if not stat.S_ISREG(published.st_mode) or published.st_size < 2:
            raise PipelineError("adapter did not publish a regular Malbolge target")
        # A durable directory entry is insufficient if its file data was never
        # synced. Pin the published stage inode before exposing its new name.
        try:
            with staged.open("rb") as output:
                observed = os.fstat(output.fileno())
                if (observed.st_dev, observed.st_ino, observed.st_size) != (
                    published.st_dev,
                    published.st_ino,
                    published.st_size,
                ):
                    raise PipelineError("staged guest artifact changed before sync")
                os.fsync(output.fileno())
        except OSError as error:
            raise PipelineError(
                f"cannot sync staged guest artifact: {error}"
            ) from error
        # The stage sync is still part of guest compilation. Check the source
        # again afterward, immediately before exposing the verified artifact.
        if source_fingerprint(source) != expected:
            raise PipelineError("source changed during guest compilation")
        _ = remaining_seconds(deadline)
        try:
            # The link is atomic and fails if a peer occupied the target while
            # compilation ran; a rename would silently replace it on POSIX.
            os.link(staged, target)
        except FileExistsError as error:
            raise PipelineError("output path already exists (no-clobber)") from error
        except OSError as error:
            raise PipelineError(f"cannot publish guest target: {error}") from error
        # Hard-link creation is atomic but not a directory durability barrier.
        # A sync failure is reported even though the new name may already exist.
        sync_published_directory(target)


def main() -> int:
    arguments = parse_arguments()
    try:
        compile_source(arguments)
    except PipelineError as error:
        print(f"c2malbolge: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
