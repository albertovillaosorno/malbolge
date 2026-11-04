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

import io
import os
import re
import shutil

# jig-ignore-next-line: indivisible reviewed identifier
import subprocess  # ruff: ignore[suspicious-subprocess-import] - fixed TeX argv, never a shell command.
import sys
import tempfile
from pathlib import Path
from stat import S_ISDIR, S_ISLNK, S_ISREG
from typing import TYPE_CHECKING, Never, TextIO, cast

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
LATEX_TIMEOUT_SECONDS = 120
PDF_SIGNATURE = b"%PDF-"
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
        MathSpecificationError,
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


def _native_stat(receipt: object, context: str) -> os.stat_result:
    """Admit only OS-native stat metadata before reading any properties.

    Returns:
        The authenticated OS stat result.

    """
    if type(receipt) is not os.stat_result:
        _fail(f"{context} requires a native stat receipt")
    return receipt


def _native_boolean(receipt: object, context: str, status: str) -> bool:
    """Admit only OS-native redirect, directory and access verdicts.

    Returns:
        The authenticated OS boolean verdict.

    """
    if type(receipt) is not bool:
        _fail(f"{context} requires a native {status} receipt")
    return receipt


def _native_descriptor(receipt: object, context: str) -> int:
    """Reject descriptors that cannot establish exclusive stream ownership.

    Returns:
        The nonnegative native descriptor.

    """
    if type(receipt) is not int or receipt < 0:
        _fail(f"{context} requires a native descriptor receipt")
    return receipt


def _owned_stream_descriptor(receipt: object, owned: int, context: str) -> int:
    """Bind a wrapped stream to its exact previously admitted descriptor.

    Returns:
        The native descriptor owned by the stream.

    """
    descriptor = _native_descriptor(receipt, context)
    if descriptor != owned:
        _fail(f"{context} stream descriptor changed")
    return descriptor


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
        status = _native_stat(status, "mathematics source")
        try:
            junction = current.is_junction()
        except (OSError, ValueError, TypeError, RuntimeError) as error:
            raise MathSpecificationError(
                f"mathematics source redirect status failed: {_host_error_detail(error)}"
            ) from error
        junction = _native_boolean(junction, "mathematics source", "junction")
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
    else:
        symlink = _native_boolean(
            candidate.is_symlink(), "mathematics source scan", "symlink"
        )
        if symlink:
            directory = _native_boolean(
                candidate.is_dir(), "mathematics source scan", "directory"
            )
            if directory:
                reason = "mathematics source directory must not redirect"
                _fail(f"{reason}: {candidate}")


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
    status = _native_stat(status, "mathematics source")
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
    descriptor = _native_descriptor(os.open(path, flags), "mathematics source")
    try:
        stream = os.fdopen(descriptor, "rb")
    except (OSError, ValueError, TypeError, RuntimeError):
        try:
            os.close(descriptor)
        except OSError:
            pass
        raise
    # Fileno equality alone cannot certify bytes from an fdopen replacement.
    # The native buffered reader and raw FileIO must own the opened descriptor.
    if type(stream) is not io.BufferedReader:
        try:
            os.close(descriptor)
        except OSError:
            pass
        _fail("mathematics source requires native stream receipt")
    raw_stream = stream.raw
    if (
        type(raw_stream) is not io.FileIO
        or type(raw_stream.name) is not int
        or raw_stream.name != descriptor
        or raw_stream.fileno() != descriptor
        or stream.fileno() != descriptor
    ):
        # A substituted native stream may own another descriptor: close ours.
        try:
            os.close(descriptor)
        except OSError:
            pass
        _fail("mathematics source requires native stream receipt")
    with stream:
        stream_descriptor = _owned_stream_descriptor(
            stream.fileno(), descriptor, "mathematics source"
        )
        if _tex_source_identity(os.fstat(stream_descriptor)) != admitted:
            _fail("mathematics source changed before read")
        data = stream.read(MAX_TEX_BYTES + 1)
        if type(data) is not bytes:
            _fail("malformed mathematics source byte receipt")
        if (
            len(data) != admitted[2]
            or _tex_source_identity(os.fstat(stream_descriptor)) != admitted
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
        detail = (
            str(error)
            if type(error) is UnicodeDecodeError
            else "foreign Unicode decoder failure"
        )
        raise MathSpecificationError(
            f"invalid mathematics source UTF-8: {path}: {detail}"
        ) from error
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
    status = _native_stat(status, "mathematics cache")
    try:
        junction = path.is_junction()
    except (OSError, ValueError, TypeError, RuntimeError) as error:
        raise MathSpecificationError(
            f"mathematics cache redirect status failed: {_host_error_detail(error)}"
        ) from error
    junction = _native_boolean(junction, "mathematics cache", "junction")
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
        is_file = Path(compiler).is_file()
        can_execute = (
            os.access(compiler, os.X_OK)
            if type(is_file) is bool and is_file
            else False
        )
    except (OSError, ValueError, TypeError, RuntimeError) as error:
        raise MathSpecificationError(
            f"LaTeX compiler status failed: {_host_error_detail(error)}"
        ) from error
    is_file = _native_boolean(is_file, "LaTeX compiler", "file status")
    can_execute = _native_boolean(
        can_execute, "LaTeX compiler", "executable status"
    )
    if not (is_file and can_execute):
        _fail(f"LaTeX compiler is not an executable file: {compiler}")
    return compiler


def _admit_math_build_log(log_path: Path) -> None:
    """Reject a redirected or nonregular existing cache-log destination."""
    try:
        symlink = log_path.is_symlink()
        junction = log_path.is_junction()
    except (OSError, ValueError, TypeError, RuntimeError) as error:
        raise MathSpecificationError(
            f"mathematics cache log redirect status failed: {_host_error_detail(error)}"
        ) from error
    symlink = _native_boolean(symlink, "mathematics cache log", "redirect")
    junction = _native_boolean(junction, "mathematics cache log", "redirect")
    if symlink or junction:
        _fail(f"mathematics cache log must not redirect: {log_path}")
    try:
        observed = log_path.lstat()
    except FileNotFoundError:
        return
    except (OSError, ValueError, TypeError, RuntimeError) as error:
        raise MathSpecificationError(
            f"mathematics cache log status failed: {_host_error_detail(error)}"
        ) from error
    observed = _native_stat(observed, "mathematics cache log")
    if not S_ISREG(observed.st_mode):
        _fail(f"mathematics cache log must be a regular file: {log_path}")


def _admit_math_log_temporary(
    log_path: Path,
    descriptor: int,
    name: object,
) -> tuple[Path, tuple[int, int]]:
    """Bind an exclusive staging descriptor to its expected cache-only name.

    Returns:
        The admitted path and its regular-file device/inode identity.

    """
    # An invalid receipt never owns a descriptor, especially fd 0 or fd 1.
    descriptor = _native_descriptor(descriptor, "mathematics build log")
    try:
        if type(name) is not str:
            _fail("mathematics build log temporary path receipt must be a string")
        temporary = Path(name)
        # mkstemp reports an absolute name even for a relative requested dir.
        parent = Path(os.path.abspath(log_path.parent))  # ruff: ignore[os-path-abspath]
        if (
            not temporary.is_absolute()
            or temporary != Path(os.path.abspath(temporary))  # ruff: ignore[os-path-abspath]
            or temporary.parent != parent
            or re.fullmatch(r"\.build\.stdout\.[a-z0-9_]{8}", temporary.name) is None
        ):
            _fail("mathematics build log temporary path receipt is outside staging")
        opened = os.fstat(descriptor)
        named = temporary.lstat()
        if (
            type(opened) is not os.stat_result
            or type(named) is not os.stat_result
            or not S_ISREG(opened.st_mode)
            or not S_ISREG(named.st_mode)
            or opened.st_nlink != 1
            or named.st_nlink != 1
            or opened.st_size != 0
            or (opened.st_dev, opened.st_ino) != (named.st_dev, named.st_ino)
        ):
            _fail("mathematics build log temporary path receipt has wrong inode")
    except (
        MathSpecificationError,
        OSError,
        ValueError,
        TypeError,
        RuntimeError,
    ) as error:
        # Never unlink the untrusted name: it may identify an unrelated file.
        try:
            os.close(descriptor)
        except (OSError, ValueError, TypeError) as close_error:
            error.add_note(
                f"mathematics temporary descriptor close failed: {_host_error_detail(close_error)}"
            )
        if isinstance(error, MathSpecificationError):
            raise
        raise MathSpecificationError(
            f"mathematics build log temporary path receipt failed: {_host_error_detail(error)}"
        ) from error
    return temporary, (opened.st_dev, opened.st_ino)


def _check_math_log_temporary_identity(
    temporary: Path, identity: tuple[int, int]
) -> None:
    """Reject staged file replacement before publishing a captured log."""
    try:
        observed = temporary.lstat()
    except (OSError, ValueError, TypeError, RuntimeError) as error:
        raise MathSpecificationError(
            f"mathematics build log temporary status failed: {_host_error_detail(error)}"
        ) from error
    if (
        type(observed) is not os.stat_result
        or not S_ISREG(observed.st_mode)
        or observed.st_nlink != 1
        or (observed.st_dev, observed.st_ino) != identity
    ):
        _fail("mathematics build log temporary inode changed before publication")


def _cleanup_math_log_temporary(temporary: Path, identity: tuple[int, int]) -> None:
    """Remove only the originally admitted staging inode, if still present."""
    try:
        observed = temporary.lstat()
    except FileNotFoundError:
        # Preserve missing_ok cleanup for already-committed publication.
        pass
    except (OSError, ValueError, TypeError, RuntimeError) as error:
        raise MathSpecificationError(
            f"mathematics build log temporary cleanup status failed: {_host_error_detail(error)}"
        ) from error
    else:
        if (
            type(observed) is not os.stat_result
            or not S_ISREG(observed.st_mode)
            or observed.st_nlink != 1
            or (observed.st_dev, observed.st_ino) != identity
        ):
            _fail("mathematics build log temporary inode changed before cleanup")
    temporary.unlink(missing_ok=True)


def _verify_math_log_payload(descriptor: int, expected_text: str) -> None:
    """Match actual staged bytes to the claimed successful write receipt."""
    expected = expected_text.encode("utf-8")
    offset = os.lseek(descriptor, 0, os.SEEK_SET)
    if type(offset) is not int or offset != 0:
        _fail("mathematics build log payload has invalid offset receipt")
    actual = os.read(descriptor, len(expected) + 1)
    if type(actual) is not bytes or actual != expected:
        _fail("mathematics build log payload differs from submitted text")


def _write_math_build_log(log_path: Path, log: str) -> None:
    """Atomically replace one physical log without opening a linked leaf."""
    if type(log) is not str:
        _fail("malformed mathematics build log text")
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
    temporary, temporary_identity = _admit_math_log_temporary(
        log_path, descriptor, temporary_name
    )
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
                _ = _owned_stream_descriptor(
                    stream.fileno(), descriptor, "mathematics build log"
                )
                written = stream.write(log)
                if type(written) is not int or written != len(log):
                    _fail(f"incomplete LaTeX build log write: {log_path}")
                stream.flush()
                _verify_math_log_payload(descriptor, log)
        except MathSpecificationError:
            raise
        except (OSError, ValueError, TypeError, RuntimeError) as error:
            raise MathSpecificationError(
                f"mathematics build log write failed: {log_path}: {_host_error_detail(error)}"
            ) from error
        _reject_cache_redirects(log_path.parent)
        _admit_math_build_log(log_path)
        _check_math_log_temporary_identity(temporary, temporary_identity)
        try:
            _ = temporary.replace(log_path)
        except (OSError, ValueError, TypeError, RuntimeError) as error:
            raise MathSpecificationError(
                f"mathematics build log replace failed: {_host_error_detail(error)}"
            ) from error
    finally:
        primary = sys.exception()
        try:
            _cleanup_math_log_temporary(temporary, temporary_identity)
        except (OSError, ValueError, TypeError, RuntimeError) as error:
            detail = _host_error_detail(error)
            if primary is None:
                raise MathSpecificationError(
                    f"mathematics build log cleanup failed: {detail}"
                ) from error
            if type(primary) is MathSpecificationError:
                primary.add_note(f"mathematics build log cleanup failed: {detail}")


def _require_latex_command_receipt(receipt: object, command: list[str]) -> None:
    """Require a native argv list with exact executable, options and input."""
    if type(receipt) is not list:
        _fail("malformed LaTeX compiler command receipt")
    arguments = cast("list[object]", receipt)
    if len(arguments) != len(command) or any(
        type(argument) is not str or argument != expected
        for argument, expected in zip(arguments, command, strict=True)
    ):
        _fail("malformed LaTeX compiler command receipt")


def _run_latex_process(command: list[str], directory: Path) -> tuple[int, str]:
    """Execute one bounded TeX build and authenticate the command receipt.

    Returns:
        Native return code and captured stdout/stderr text.

    Raises:
        MathSpecificationError: On execution or process-receipt failure.

    """
    # Repository-controlled TeX flags/source names; argv is explicit, no shell.
    # jig-ignore-next-line: indivisible reviewed identifier
    try:
        completed = subprocess.run(  # ruff: ignore[subprocess-without-shell-equals-true]
            command.copy(),
            cwd=directory,
            check=False,
            capture_output=True,
            shell=False,
            text=True,
            timeout=LATEX_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as error:
        message = (
            f"LaTeX compiler timed out after {LATEX_TIMEOUT_SECONDS} seconds"
        )
        raise MathSpecificationError(message) from error
    except (OSError, ValueError, TypeError, RuntimeError) as error:
        message = (
            f"LaTeX compiler execution failed: {_host_error_detail(error)}"
        )
        raise MathSpecificationError(message) from error
    if (
        type(completed) is not subprocess.CompletedProcess
        or type(completed.returncode) is not int
        or type(completed.stdout) is not str
        or type(completed.stderr) is not str
    ):
        _fail("malformed LaTeX compiler process receipt")
    _require_latex_command_receipt(cast("object", completed.args), command)
    return completed.returncode, completed.stdout + completed.stderr


def _require_latex_pdf_descriptor(
    descriptor: int, observed: os.stat_result
) -> None:
    """Bind a PDF header to the same previously admitted physical inode."""
    opened = _native_stat(os.fstat(descriptor), "LaTeX PDF")
    if (
        (opened.st_dev, opened.st_ino) != (observed.st_dev, observed.st_ino)
        or not S_ISREG(opened.st_mode)
        or opened.st_size < len(PDF_SIGNATURE)
    ):
        _fail("LaTeX PDF artifact changed or is incomplete")
    header = os.read(descriptor, len(PDF_SIGNATURE))
    if type(header) is not bytes or header != PDF_SIGNATURE:
        _fail("LaTeX PDF artifact has an invalid header")


def _probe_latex_pdf(pdf: Path) -> None:
    """Inspect the physical PDF leaf and its opened descriptor."""
    observed = _native_stat(pdf.lstat(), "LaTeX PDF")
    if not S_ISREG(observed.st_mode) or observed.st_nlink != 1:
        _fail("LaTeX PDF must be a physical regular file")
    descriptor = _native_descriptor(
        os.open(pdf, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)),
        "LaTeX PDF",
    )
    try:
        _require_latex_pdf_descriptor(descriptor, observed)
    finally:
        os.close(descriptor)


def _require_latex_pdf(source: Path, output: Path) -> None:
    """Require a physical regular PDF carrying the native PDF signature.

    Raises:
        MathSpecificationError: When the successful build has no physical PDF.

    """
    try:
        _probe_latex_pdf(output / f"{source.stem}.pdf")
    except MathSpecificationError:
        raise
    except (OSError, ValueError, TypeError, RuntimeError) as error:
        message = f"LaTeX PDF status failed: {_host_error_detail(error)}"
        raise MathSpecificationError(message) from error


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
    returncode, log = _run_latex_process(command, source.parent)
    _write_math_build_log(log_path, log)
    if returncode != 0:
        relative = source.relative_to(ROOT).as_posix()
        message = (
            f"LaTeX build failed: {relative} exit={returncode}; "
            f"log={output.relative_to(ROOT).as_posix()}/build.stdout.txt"
        )
        _fail(message)
    _require_latex_pdf(source, output)


def build_documents() -> tuple[Path, ...]:
    """Compile every standalone math document into the repository cache.

    Returns:
        Stable document paths after every fail-closed LaTeX build succeeds.

    """
    sources = validate_source_layout()
    for source in sources:
        _compile_document(source)
    return sources


def _write_cli_record(stream: TextIO, message: str) -> bool:
    """Return whether an exact native text write and flush both completed."""
    try:
        written = stream.write(message)
        if type(written) is not int or written != len(message):
            return False
        return stream.flush() is None
    except (
        AttributeError,
        IndexError,
        OSError,
        OverflowError,
        RuntimeError,
        TypeError,
        ValueError,
    ):
        return False


def main() -> int:
    """Validate/build mathematical documents and return process status.

    Returns:
        Zero after all documents build and deliver the CLI record, else one.

    """
    try:
        sources = build_documents()
        message = f"mathematical specifications valid: {len(sources)} documents\n"
        if not _write_cli_record(sys.stdout, message):
            _fail("mathematical specifications CLI output write or flush failed")
    except (OSError, MathSpecificationError) as error:
        _ = _write_cli_record(sys.stderr, f"error: {_host_error_detail(error)}\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
