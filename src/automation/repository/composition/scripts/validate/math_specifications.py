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
#   - The repository behavior implemented by this source file.
# - Must-Not:
#   - Bypass the contracts or authority boundaries of its owning package.
# - Allows:
#   - Inputs: values admitted by the file's public or internal interface.
#   - Outputs: deterministic values or effects declared by that interface.
#   - Side effects: only those explicitly owned by the implementation.
# - Split-When:
#   - Split when one responsibility gains an independent lifecycle.
# - Merge-When:
#   - Merge when another file owns the exact same responsibility.
# - Summary:
#   - Validate and build repository mathematical specification documents.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#

"""Validate and build repository mathematical specification documents."""

from __future__ import annotations

import shutil

# jig-ignore-next-line: indivisible reviewed identifier
import subprocess  # ruff: ignore[suspicious-subprocess-import] - fixed TeX argv, never a shell command.
import sys
from pathlib import Path
from stat import S_ISDIR, S_ISLNK, S_ISREG
from typing import TYPE_CHECKING, Never

if TYPE_CHECKING:
    from collections.abc import Callable

if __package__ in {None, ""}:
    composition_root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(composition_root))

from scripts.repository_root import repository_root

ROOT = repository_root(Path(__file__))
MATH_ROOT = ROOT / "src/specification/formal-model/math"
CACHE_ROOT = ROOT / ".cache" / "latex"
NOTATION = MATH_ROOT / "malbolge-notation.tex"
DOCUMENT_MARKER = r"\documentclass"
NOTATION_INCLUDE = r"\input{../malbolge-notation.tex}"
LATEX_COMPILER = "pdflatex"
REQUIRED_MACROS = (
    r"\CostVector",
    r"\CrazyN",
    r"\DecodeOp",
    r"\EncryptOp",
    r"\ObservedEquivalent",
    r"\RotateN",
    r"\WordDomain",
)


class MathSpecificationError(ValueError):
    """Deterministic math-source layout or LaTeX build failure."""


def _fail(message: str) -> Never:
    raise MathSpecificationError(message)


def _physical_math_status(path: Path, *, directory: bool) -> None:
    """Require physical in-root TeX artifacts, without filesystem redirects."""
    try:
        relative = path.relative_to(ROOT)
    except ValueError:
        _fail(f"mathematics source must stay inside repository root: {path}")
    if ".." in relative.parts:
        _fail(f"mathematics source must not escape repository root: {path}")
    current = ROOT
    for index, component in enumerate(relative.parts):
        current = current / component
        try:
            status = current.lstat()
        except OSError as error:
            _fail(f"mathematics source status failed: {error}")
        if S_ISLNK(status.st_mode) or current.is_junction():
            _fail(f"mathematics source must not redirect: {relative.as_posix()}")
        expect_directory = directory if index == len(relative.parts) - 1 else True
        is_expected = (
            S_ISDIR(status.st_mode) if expect_directory else S_ISREG(status.st_mode)
        )
        if not is_expected:
            _fail(f"mathematics source must be a physical regular artifact: {path}")


def _discovered_tex_paths() -> tuple[Path, ...]:
    _physical_math_status(MATH_ROOT, directory=True)
    sources: list[Path] = []

    def fail_walk(error: OSError) -> None:
        _fail(f"mathematics source scan failed: {error}")

    for parent, directories, filenames in MATH_ROOT.walk(on_error=fail_walk):
        _physical_math_status(parent, directory=True)
        for name in directories:
            _physical_math_status(parent / name, directory=True)
        for name in filenames:
            candidate = parent / name
            if candidate.suffix == ".tex":
                _physical_math_status(candidate, directory=False)
                sources.append(candidate)
            elif candidate.is_symlink() and candidate.is_dir():
                _fail(f"mathematics source directory must not redirect: {candidate}")
    return tuple(sorted(sources, key=lambda path: path.as_posix()))


def _read_tex(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as error:
        _fail(f"invalid mathematics source UTF-8: {path}: {error}")


def _reject_cache_redirects(output: Path) -> None:
    """Reject an existing redirected cache ancestor before creating output."""
    try:
        relative = output.relative_to(ROOT)
    except ValueError:
        _fail(f"mathematics cache must stay inside repository root: {output}")
    if ".." in relative.parts:
        _fail(f"mathematics cache must not escape repository root: {output}")
    current = ROOT
    for component in relative.parts:
        current = current / component
        try:
            status = current.lstat()
        except FileNotFoundError:
            break
        except OSError as error:
            _fail(f"mathematics cache status failed: {error}")
        if S_ISLNK(status.st_mode) or current.is_junction():
            _fail(f"mathematics cache path must not redirect: {relative.as_posix()}")
        if not S_ISDIR(status.st_mode):
            _fail(f"mathematics cache path must be a directory: {current}")


def document_sources() -> tuple[Path, ...]:
    """Return every standalone mathematical document in stable path order.

    Returns:
        Repository-owned `.tex` files containing a document class declaration.

    """
    try:
        _ = MATH_ROOT.lstat()
    except FileNotFoundError:
        _fail(f"mathematics root not found: {MATH_ROOT}")
    sources = tuple(
        path for path in _discovered_tex_paths() if DOCUMENT_MARKER in _read_tex(path)
    )
    if not sources:
        _fail("no standalone mathematical documents found")
    return sources


def _validate_notation() -> None:
    try:
        _ = NOTATION.lstat()
    except FileNotFoundError:
        _fail("shared mathematical notation file is missing")
    _physical_math_status(NOTATION, directory=False)
    notation_text = _read_tex(NOTATION)
    if DOCUMENT_MARKER in notation_text:
        _fail("shared notation must remain an include, not a standalone document")
    for macro in REQUIRED_MACROS:
        if macro not in notation_text:
            _fail(f"shared notation is missing required macro: {macro}")


def _validate_document_imports(sources: tuple[Path, ...]) -> None:
    for source in sources:
        _physical_math_status(source, directory=False)
        text = _read_tex(source)
        if NOTATION_INCLUDE not in text:
            relative = source.relative_to(ROOT).as_posix()
            _fail(f"math document does not import shared notation: {relative}")


def validate_source_layout() -> tuple[Path, ...]:
    """Validate shared notation and document inclusion invariants.

    Returns:
        Stable standalone document paths after all source-layout checks pass.

    """
    _validate_notation()
    sources = document_sources()
    _validate_document_imports(sources)
    return sources


def output_directory(source: Path) -> Path:
    """Return the cache-only build directory for one math source.

    Returns:
        A `.cache/latex/` path preserving source directory and stem identity.

    """
    try:
        relative = source.relative_to(MATH_ROOT)
    except ValueError:
        _fail(f"mathematics source must stay inside math root: {source}")
    if ".." in relative.parts or not relative.parts:
        _fail(f"mathematics source must not escape math root: {source}")
    return CACHE_ROOT / relative.parent / relative.stem


def latex_compiler(
    lookup: Callable[[str], str | None] = shutil.which,
) -> str:
    """Resolve the required LaTeX compiler or fail with one stable diagnostic.

    Returns:
        Absolute or PATH-resolved `pdflatex` executable.

    """
    compiler = lookup(LATEX_COMPILER)
    if compiler is None:
        _fail(f"LaTeX compiler not found: {LATEX_COMPILER}")
    return compiler


def _compile_document(source: Path) -> None:
    _physical_math_status(source, directory=False)
    output = output_directory(source)
    _reject_cache_redirects(output)
    _ = output.mkdir(parents=True, exist_ok=True)
    _reject_cache_redirects(output)
    command = [
        latex_compiler(),
        "-disable-installer",
        "-disable-write18",
        "-interaction=nonstopmode",
        "-halt-on-error",
        "-file-line-error",
        f"-output-directory={output}",
        source.name,
    ]
    # Repository-controlled TeX flags/source names; argv is explicit, no shell.
    # jig-ignore-next-line: indivisible reviewed identifier
    completed = subprocess.run(  # ruff: ignore[subprocess-without-shell-equals-true]
        command,
        cwd=source.parent,
        check=False,
        capture_output=True,
        shell=False,
        text=True,
    )
    log = completed.stdout + completed.stderr
    log_path = output / "build.stdout.txt"
    written = log_path.write_text(log, encoding="utf-8", newline="\n")
    if written != len(log):
        _fail(f"incomplete LaTeX build log write: {log_path}")
    if completed.returncode != 0:
        relative = source.relative_to(ROOT).as_posix()
        message = (
            f"LaTeX build failed: {relative} exit={completed.returncode}; "
            f"log={output.relative_to(ROOT).as_posix()}/build.stdout.txt"
        )
        _fail(message)


def build_documents() -> tuple[Path, ...]:
    """Compile every standalone math document into the repository cache.

    Returns:
        Stable document paths after every fail-closed LaTeX build succeeds.

    """
    sources = validate_source_layout()
    for source in sources:
        _compile_document(source)
    return sources


def main() -> int:
    """Validate/build mathematical documents and return process status.

    Returns:
        Zero after all documents build; otherwise one with a deterministic
        error.

    """
    try:
        sources = build_documents()
    except (OSError, MathSpecificationError) as error:
        _ = sys.stderr.write(f"error: {error}\n")
        return 1
    _ = sys.stdout.write(
        f"mathematical specifications valid: {len(sources)} documents\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
