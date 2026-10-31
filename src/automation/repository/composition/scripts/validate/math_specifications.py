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

import os
import shutil

# jig-ignore-next-line: indivisible reviewed identifier
import subprocess  # ruff: ignore[suspicious-subprocess-import] - fixed TeX argv, never a shell command.
import sys
import tempfile
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
MAX_TEX_BYTES = 1024 * 1024
PARENT_SEGMENT = ".."
TEX_SUFFIX = ".tex"
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


def _host_error_detail(error: Exception) -> str:
    """Retain native host diagnostics without invoking foreign formatter hooks.

    Returns:
        Native exception text, or the foreign exception's type name.

    """
    if type(error) in (
        OSError,
        ValueError,
        TypeError,
        RuntimeError,
        PermissionError,
        FileNotFoundError,
        FileExistsError,
        IsADirectoryError,
        NotADirectoryError,
    ):
        return str(error)
    return type(error).__name__


def _source_relative_path(path: Path) -> Path:
    """Admit a lexical repository-relative source path.

    Returns:
        One path that cannot escape the repository by parent traversal.

    """
    try:
        relative = path.relative_to(ROOT)
    except ValueError:
        _fail(f"mathematics source must stay inside repository root: {path}")
    if PARENT_SEGMENT in relative.parts:
        _fail(f"mathematics source must not escape repository root: {path}")
    return relative


def _physical_math_status(path: Path, *, directory: bool) -> None:
    """Require physical in-root TeX artifacts, without filesystem redirects."""
    relative = _source_relative_path(path)
    current = ROOT
    for index, component in enumerate(relative.parts):
        current /= component
        try:
            status = current.lstat()
        except (OSError, ValueError, TypeError, RuntimeError) as error:
            raise MathSpecificationError(
                f"mathematics source status failed: {_host_error_detail(error)}"
            ) from error
        try:
            junction = current.is_junction()
        except (OSError, ValueError, TypeError, RuntimeError) as error:
            raise MathSpecificationError(
                f"mathematics source redirect status failed: {_host_error_detail(error)}"
            ) from error
        if S_ISLNK(status.st_mode) or junction:
            _fail(f"mathematics source must not redirect: {relative.as_posix()}")
        expect_directory = directory if index == len(relative.parts) - 1 else True
        is_expected = (
            S_ISDIR(status.st_mode) if expect_directory else S_ISREG(status.st_mode)
        )
        if not is_expected:
            reason = "mathematics source must be a physical regular artifact"
            _fail(f"{reason}: {path}")


def _admit_tex_candidate(candidate: Path, sources: list[Path]) -> None:
    """Collect an admissible TeX source and reject redirected directories."""
    if candidate.suffix == TEX_SUFFIX:
        _physical_math_status(candidate, directory=False)
        sources.append(candidate)
    elif candidate.is_symlink() and candidate.is_dir():
        _fail(f"mathematics source directory must not redirect: {candidate}")


def _discovered_tex_paths() -> tuple[Path, ...]:
    _physical_math_status(MATH_ROOT, directory=True)
    sources: list[Path] = []

    def fail_walk(error: OSError) -> None:
        raise MathSpecificationError(
            f"mathematics source scan failed: {_host_error_detail(error)}"
        ) from error

    try:
        for parent, directories, filenames in MATH_ROOT.walk(on_error=fail_walk):
            _physical_math_status(parent, directory=True)
            for name in directories:
                _physical_math_status(parent / name, directory=True)
            for name in filenames:
                _admit_tex_candidate(parent / name, sources)
    except MathSpecificationError:
        raise
    except (OSError, ValueError, TypeError, RuntimeError) as error:
        raise MathSpecificationError(
            f"mathematics source scan failed: {_host_error_detail(error)}"
        ) from error
    return tuple(sorted(sources, key=lambda path: path.as_posix()))


def _tex_source_identity(
    status: os.stat_result,
) -> tuple[int, int, int, int, int]:
    """Admit a bounded regular file and capture its physical identity.

    Returns:
        Device, inode, size, mtime and ctime of the admitted source.

    """
    if not S_ISREG(status.st_mode):
        _fail("mathematics source must be a physical regular artifact")
    if status.st_size > MAX_TEX_BYTES:
        _fail("mathematics source exceeds byte limit")
    return (
        status.st_dev,
        status.st_ino,
        status.st_size,
        status.st_mtime_ns,
        status.st_ctime_ns,
    )


def _read_open_tex_bytes(
    path: Path,
    admitted: tuple[int, int, int, int, int],
) -> bytes:
    """Read one bounded descriptor and verify its pre/post physical identity.

    Returns:
        Exact bytes of the open regular file.

    """
    flags = (
        os.O_RDONLY
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_NONBLOCK", 0)
        | getattr(os, "O_BINARY", 0)
    )
    descriptor = os.open(path, flags)
    try:
        stream = os.fdopen(descriptor, "rb")
    except (OSError, ValueError, TypeError, RuntimeError):
        try:
            os.close(descriptor)
        except OSError:
            pass
        raise
    with stream:
        if _tex_source_identity(os.fstat(stream.fileno())) != admitted:
            _fail("mathematics source changed before read")
        data = stream.read(MAX_TEX_BYTES + 1)
        if (
            len(data) != admitted[2]
            or _tex_source_identity(os.fstat(stream.fileno())) != admitted
        ):
            _fail("mathematics source changed during read")
    return data


def _stable_tex_source_bytes(path: Path) -> bytes:
    """Require a stable no-redirect path around one descriptor read.

    Returns:
        Exact physical bytes after a second pathname identity check.

    """
    _physical_math_status(path, directory=False)
    admitted = _tex_source_identity(path.lstat())
    data = _read_open_tex_bytes(path, admitted)
    _physical_math_status(path, directory=False)
    if _tex_source_identity(path.lstat()) != admitted:
        _fail("mathematics source changed during read")
    return data


def _read_tex(path: Path) -> str:
    """Read a stable, bounded, physically admitted TeX source snapshot.

    Returns:
        UTF-8 text only when the named source remains unchanged.

    """
    try:
        return _stable_tex_source_bytes(path).decode("utf-8")
    except UnicodeDecodeError as error:
        _fail(f"invalid mathematics source UTF-8: {path}: {error}")
    except MathSpecificationError:
        raise
    except (OSError, ValueError, TypeError, RuntimeError) as error:
        raise MathSpecificationError(
            f"mathematics source read failed: {path}: {_host_error_detail(error)}"
        ) from error


def _cache_relative_path(output: Path) -> Path:
    """Admit a lexical repository-relative cache path.

    Returns:
        One path that cannot escape the repository by parent traversal.

    """
    try:
        relative = output.relative_to(ROOT)
    except ValueError:
        _fail(f"mathematics cache must stay inside repository root: {output}")
    if PARENT_SEGMENT in relative.parts:
        _fail(f"mathematics cache must not escape repository root: {output}")
    return relative


def _cache_component_is_physical(path: Path, relative: Path) -> bool:
    """Verify one existing cache ancestor, or report an absent component.

    Returns:
        True when the physical directory exists; false when still absent.

    """
    try:
        status = path.lstat()
    except FileNotFoundError:
        return False
    except (OSError, ValueError, TypeError, RuntimeError) as error:
        raise MathSpecificationError(
            f"mathematics cache status failed: {_host_error_detail(error)}"
        ) from error
    try:
        junction = path.is_junction()
    except (OSError, ValueError, TypeError, RuntimeError) as error:
        raise MathSpecificationError(
            f"mathematics cache redirect status failed: {_host_error_detail(error)}"
        ) from error
    if S_ISLNK(status.st_mode) or junction:
        _fail(f"mathematics cache path must not redirect: {relative.as_posix()}")
    if not S_ISDIR(status.st_mode):
        _fail(f"mathematics cache path must be a directory: {path}")
    return True


def _reject_cache_redirects(output: Path) -> None:
    """Reject an existing redirected cache ancestor before creating output."""
    relative = _cache_relative_path(output)
    current = ROOT
    for component in relative.parts:
        current /= component
        if not _cache_component_is_physical(current, relative):
            break


def document_sources() -> tuple[Path, ...]:
    """Return every standalone mathematical document in stable path order.

    Returns:
        Repository-owned `.tex` files containing a document class declaration.

    """
    try:
        _ = MATH_ROOT.lstat()
    except FileNotFoundError:
        _fail(f"mathematics root not found: {MATH_ROOT}")
    except (OSError, ValueError, TypeError, RuntimeError) as error:
        raise MathSpecificationError(
            f"mathematics root status failed: {_host_error_detail(error)}"
        ) from error
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
    except (OSError, ValueError, TypeError, RuntimeError) as error:
        raise MathSpecificationError(
            f"mathematics notation status failed: {_host_error_detail(error)}"
        ) from error
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
    if PARENT_SEGMENT in relative.parts or not relative.parts:
        _fail(f"mathematics source must not escape math root: {source}")
    return CACHE_ROOT / relative.parent / relative.stem


def latex_compiler(
    lookup: Callable[[str], str | None] = shutil.which,
) -> str:
    """Resolve the required LaTeX compiler or fail with one stable diagnostic.

    Returns:
        Absolute or PATH-resolved `pdflatex` executable.

    """
    try:
        compiler = lookup(LATEX_COMPILER)
    except (OSError, ValueError, TypeError, RuntimeError) as error:
        raise MathSpecificationError(
            f"LaTeX compiler lookup failed: {_host_error_detail(error)}"
        ) from error
    if compiler is None:
        _fail(f"LaTeX compiler not found: {LATEX_COMPILER}")
    if type(compiler) is not str or not compiler or not Path(compiler).is_absolute():
        _fail("LaTeX compiler resolver must return an absolute executable path")
    try:
        executable = Path(compiler).is_file() and os.access(compiler, os.X_OK)
    except (OSError, ValueError, TypeError, RuntimeError) as error:
        raise MathSpecificationError(
            f"LaTeX compiler status failed: {_host_error_detail(error)}"
        ) from error
    if not executable:
        _fail(f"LaTeX compiler is not an executable file: {compiler}")
    return compiler


def _admit_math_build_log(log_path: Path) -> None:
    """Reject a redirected or nonregular existing cache-log destination."""
    try:
        redirected = log_path.is_symlink() or log_path.is_junction()
    except (OSError, ValueError, TypeError, RuntimeError) as error:
        raise MathSpecificationError(
            f"mathematics cache log redirect status failed: {_host_error_detail(error)}"
        ) from error
    if redirected:
        _fail(f"mathematics cache log must not redirect: {log_path}")
    try:
        observed = log_path.lstat()
    except FileNotFoundError:
        return
    except (OSError, ValueError, TypeError, RuntimeError) as error:
        raise MathSpecificationError(
            f"mathematics cache log status failed: {_host_error_detail(error)}"
        ) from error
    if not S_ISREG(observed.st_mode):
        _fail(f"mathematics cache log must be a regular file: {log_path}")


def _write_math_build_log(log_path: Path, log: str) -> None:
    """Atomically replace one physical log without opening a linked leaf."""
    _reject_cache_redirects(log_path.parent)
    _admit_math_build_log(log_path)
    try:
        descriptor, temporary_name = tempfile.mkstemp(
            dir=log_path.parent, prefix=".build.stdout."
        )
    except (OSError, ValueError, TypeError, RuntimeError) as error:
        raise MathSpecificationError(
            f"mathematics build log temporary creation failed: {_host_error_detail(error)}"
        ) from error
    temporary = Path(temporary_name)
    try:
        try:
            try:
                stream = os.fdopen(descriptor, "w", encoding="utf-8", newline="\n")
            except (OSError, ValueError, TypeError, RuntimeError):
                try:
                    os.close(descriptor)
                except OSError:
                    pass
                raise
            with stream:
                written = stream.write(log)
                if type(written) is not int or written != len(log):
                    _fail(f"incomplete LaTeX build log write: {log_path}")
                stream.flush()
        except MathSpecificationError:
            raise
        except (OSError, ValueError, TypeError, RuntimeError) as error:
            raise MathSpecificationError(
                f"mathematics build log write failed: {log_path}: {_host_error_detail(error)}"
            ) from error
        _reject_cache_redirects(log_path.parent)
        _admit_math_build_log(log_path)
        try:
            _ = temporary.replace(log_path)
        except (OSError, ValueError, TypeError, RuntimeError) as error:
            raise MathSpecificationError(
                f"mathematics build log replace failed: {_host_error_detail(error)}"
            ) from error
    finally:
        primary = sys.exception()
        try:
            temporary.unlink(missing_ok=True)
        except (OSError, ValueError, TypeError, RuntimeError) as error:
            detail = _host_error_detail(error)
            if primary is None:
                raise MathSpecificationError(
                    f"mathematics build log cleanup failed: {detail}"
                ) from error
            if type(primary) is MathSpecificationError:
                primary.add_note(f"mathematics build log cleanup failed: {detail}")


def _compile_document(source: Path) -> None:
    _physical_math_status(source, directory=False)
    output = output_directory(source)
    _reject_cache_redirects(output)
    _ = output.mkdir(parents=True, exist_ok=True)
    _reject_cache_redirects(output)
    log_path = output / "build.stdout.txt"
    _admit_math_build_log(log_path)
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
    try:
        completed = subprocess.run(  # ruff: ignore[subprocess-without-shell-equals-true]
            command,
            cwd=source.parent,
            check=False,
            capture_output=True,
            shell=False,
            text=True,
        )
    except (OSError, ValueError, TypeError, RuntimeError) as error:
        raise MathSpecificationError(
            f"LaTeX compiler execution failed: {_host_error_detail(error)}"
        ) from error
    if (
        type(completed.returncode) is not int
        or not isinstance(completed.stdout, str)
        or not isinstance(completed.stderr, str)
    ):
        _fail("malformed LaTeX compiler process receipt")
    log = completed.stdout + completed.stderr
    _write_math_build_log(log_path, log)
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
