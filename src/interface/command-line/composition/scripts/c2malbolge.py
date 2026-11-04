#!/usr/bin/env python3
# Copyright:
#   - Copyright © 2026 Alberto Villa Osorno.
# SPDX-License-Identifier:
#   - LicenseRef-Proprietary
# Confidential:
#   - true
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
import stat
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import cast

MAX_SOURCE_BYTES = 64 * 1024 * 1024
MAX_JSON_BYTES = 1_048_576
CHUNK_BYTES = 64 * 1024
REPOSITORY_ROOT = Path(__file__).resolve().parents[5]
PINNED_LLVM_VERSION = "22.1.8"


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


class PipelineError(Exception):
    """One stage could not establish the supported compiler contract."""


def source_digest(path: Path) -> str:
    """Hash one stable regular source inode without trusting an initial path stat."""
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
    return digest.hexdigest()


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
    except (UnicodeError, ValueError) as error:
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


def run_frontend(arguments: Arguments) -> bytes:
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
    try:
        with subprocess.Popen(command, stdout=subprocess.PIPE) as child:
            assert child.stdout is not None
            data = cast(bytes, child.stdout.read(MAX_JSON_BYTES + 1))
            child.stdout.close()
            status = child.wait()
    except OSError as error:
        raise PipelineError(f"cannot execute native C frontend: {error}") from error
    if status != 0:
        raise PipelineError(f"native C frontend failed with status {status}")
    if not data or len(data) > MAX_JSON_BYTES:
        raise PipelineError("native C frontend JSON is empty or exceeds 1 MiB")
    return data


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
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
            source_id = Path(source).name
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
    if (
        not arguments.source_id
        or "\\" in arguments.source_id
        or arguments.source_id.startswith("/")
        or any(part in ("", ".", "..") for part in arguments.source_id.split("/"))
    ):
        raise PipelineError("source ID must be a portable relative path")
    if os.path.lexists(arguments.output):
        raise PipelineError("output path already exists (no-clobber)")
    source = Path(arguments.source)
    expected = source_digest(source)
    normalized = run_frontend(arguments)
    admit_source_identity(normalized, arguments.source_id, expected)
    if source_digest(source) != expected:
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
        if arguments.capsule:
            command.append("--capsule")
        try:
            completed = subprocess.run(command, input=normalized, check=False)
        except OSError as error:
            raise PipelineError(
                f"cannot execute JSON-to-target adapter: {error}"
            ) from error
        if completed.returncode != 0:
            raise PipelineError(
                f"JSON-to-target adapter failed with status {completed.returncode}"
            )
        try:
            published = staged.lstat()
        except OSError as error:
            raise PipelineError(f"adapter did not publish a target: {error}") from error
        if not stat.S_ISREG(published.st_mode) or published.st_size < 2:
            raise PipelineError("adapter did not publish a regular Malbolge target")
        if source_digest(source) != expected:
            raise PipelineError("source changed during guest compilation")
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
