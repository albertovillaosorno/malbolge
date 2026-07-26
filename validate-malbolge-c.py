#!/usr/bin/env python3
"""Manually validate explicitly selected C files against the Malbolge guest profile."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DEFAULT_PROFILE = ROOT / "tools" / "tidy" / "malbolge-clang-tidy.yaml"
PINNED_LLVM = ROOT / ".dependencies" / "llvm" / "22.1.8" / "bin"


def _default_clang_tidy() -> Path:
    for name in ("clang-tidy.exe", "clang-tidy"):
        candidate = PINNED_LLVM / name
        if candidate.is_file():
            return candidate
    return PINNED_LLVM / "clang-tidy"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Validate only the C translation units named on this command line "
            "against the Malbolge guest-C compatibility profile."
        )
    )
    parser.add_argument(
        "files",
        nargs="+",
        metavar="FILE.c",
        help="explicit C translation units to validate; directories are never scanned",
    )
    parser.add_argument(
        "--profile",
        type=Path,
        default=DEFAULT_PROFILE,
        help="clang-tidy profile (default: tools/tidy/malbolge-clang-tidy.yaml)",
    )
    parser.add_argument(
        "--clang-tidy",
        type=Path,
        default=_default_clang_tidy(),
        help="clang-tidy executable (default: repository-pinned LLVM 22.1.8)",
    )
    parser.add_argument(
        "--plugin",
        type=Path,
        help="optional built tools/tidy clang-tidy plugin to load",
    )
    return parser


def _validated_files(raw_files: list[str]) -> list[Path]:
    files: list[Path] = []
    for raw in raw_files:
        path = Path(raw)
        if not path.exists():
            raise ValueError(f"input does not exist: {path}")
        if not path.is_file():
            raise ValueError(f"directories are not accepted; name each .c file explicitly: {path}")
        if path.suffix.lower() != ".c":
            raise ValueError(f"Malbolge guest validation accepts C translation units only: {path}")
        files.append(path.resolve())
    return files


def _run(command: list[str]) -> int:
    completed = subprocess.run(command, cwd=ROOT, check=False)
    return completed.returncode


def main() -> int:
    args = _parser().parse_args()

    clang_tidy = args.clang_tidy.resolve()
    profile = args.profile.resolve()
    plugin = args.plugin.resolve() if args.plugin else None

    if not clang_tidy.is_file():
        print(f"error: clang-tidy not found: {clang_tidy}", file=sys.stderr)
        return 2
    if not profile.is_file():
        print(f"error: Malbolge guest profile not found: {profile}", file=sys.stderr)
        return 2
    if plugin is not None and not plugin.is_file():
        print(f"error: clang-tidy plugin not found: {plugin}", file=sys.stderr)
        return 2

    try:
        files = _validated_files(args.files)
    except ValueError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    verify = [str(clang_tidy), "--verify-config", f"--config-file={profile}"]
    if _run(verify) != 0:
        print("error: Malbolge clang-tidy profile failed self-verification", file=sys.stderr)
        return 2

    status = 0
    for source in files:
        command = [str(clang_tidy), f"--config-file={profile}"]
        if plugin is not None:
            command.append(f"--load={plugin}")
        command.extend([str(source), "--", "-x", "c"])
        result = _run(command)
        if result != 0:
            status = result

    return status


if __name__ == "__main__":
    raise SystemExit(main())
