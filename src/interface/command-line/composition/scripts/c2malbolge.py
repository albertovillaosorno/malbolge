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
    for flag in (
        "frontend",
        "json-adapter",
        "layout-backend",
        "guest-include",
        "resource-dir",
        "source-id",
        "output",
    ):
        _ = parser.add_argument(f"--{flag}", required=True)
    _ = parser.add_argument("--capsule", action="store_true")
    _ = parser.add_argument("source", help="explicit C source file")
    return parser


def parse_arguments() -> Arguments:
    parsed = build_parser().parse_args()
    return Arguments(
        frontend=cast(str, parsed.frontend),
        json_adapter=cast(str, parsed.json_adapter),
        layout_backend=cast(str, parsed.layout_backend),
        guest_include=cast(str, parsed.guest_include),
        resource_dir=cast(str, parsed.resource_dir),
        source_id=cast(str, parsed.source_id),
        output=cast(str, parsed.output),
        capsule=cast(bool, parsed.capsule),
        source=cast(str, parsed.source),
    )


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
        try:
            # The link is atomic and fails if a peer occupied the target while
            # compilation ran; a rename would silently replace it on POSIX.
            os.link(staged, target)
        except FileExistsError as error:
            raise PipelineError("output path already exists (no-clobber)") from error
        except OSError as error:
            raise PipelineError(f"cannot publish guest target: {error}") from error


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
