# Copyright:
#   - Copyright © 2026 Alberto Villa Osorno.
# SPDX-License-Identifier:
#   - MIT
# Confidential:
#   - false
# License-File:
#   - LICENSE-MIT
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

from pathlib import Path
import shutil

# jig-ignore-next-line: indivisible reviewed identifier
import subprocess  # ruff: ignore[suspicious-subprocess-import] - fixed TeX argv, never a shell command.
import sys
from typing import Never
from typing import TYPE_CHECKING

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


def document_sources() -> tuple[Path, ...]:
    """Return every standalone mathematical document in stable path order.

    Returns:
        Repository-owned `.tex` files containing a document class declaration.

    """
    if not MATH_ROOT.is_dir():
        _fail(f"mathematics root not found: {MATH_ROOT}")
    sources = tuple(
        sorted(
            (
                path
                for path in MATH_ROOT.rglob("*.tex")
                if DOCUMENT_MARKER in path.read_text(encoding="utf-8")
            ),
            key=lambda path: path.as_posix(),
        )
    )
    if not sources:
        _fail("no standalone mathematical documents found")
    return sources


def _validate_notation() -> None:
    if not NOTATION.is_file():
        _fail("shared mathematical notation file is missing")
    notation_text = NOTATION.read_text(encoding="utf-8")
    if DOCUMENT_MARKER in notation_text:
        _fail(
            "shared notation must remain an include, not a standalone document"
        )
    for macro in REQUIRED_MACROS:
        if macro not in notation_text:
            _fail(f"shared notation is missing required macro: {macro}")


def _validate_document_imports(sources: tuple[Path, ...]) -> None:
    for source in sources:
        text = source.read_text(encoding="utf-8")
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
    relative = source.relative_to(MATH_ROOT)
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
    output = output_directory(source)
    _ = output.mkdir(parents=True, exist_ok=True)
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
