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
#   - Reproducible sanitizer execution of the immutable historical interpreter.
# - Must-Not:
#   - Modify historical source or make sanitizer findings language semantics.
# - Allows:
#   - Inputs: pinned Clang, reviewed case manifest, and immutable source bytes.
#   - Outputs: normalized clean/failure evidence without host addresses.
#   - Side effects: temporary build and execution files under `.temp`.
# - Split-When:
#   - Split when another host ABI needs an independent compatibility adapter.
# - Merge-When:
#   - Merge when another validator owns the same sanitizer evidence boundary.
# - Summary:
#   - Build and verify historical ASan/UBSan evidence without source edits.
# - Description:
#   - Generates a temporary `_halloc` shim and compares normalized findings.
# - Usage:
#   - Run as `python -m scripts.validate.historical_interpreter_sanitizer`.
# - Defaults:
#   - Tool, source, case, and evidence drift fail closed.
#

"""Reproduce historical interpreter sanitizer evidence."""

from __future__ import annotations

import argparse
import io
import json
import os
import re
import shutil
import subprocess  # ruff: ignore[suspicious-subprocess-import]
import sys
import tempfile
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from stat import S_ISDIR, S_ISLNK, S_ISREG
from typing import TYPE_CHECKING, Never, TextIO, cast, override

from scripts.repository_root import repository_root

if TYPE_CHECKING:
    from collections.abc import Sequence

ROOT = repository_root(Path(__file__))
SOURCE = ROOT / (
    "src/interoperability/historical-malbolge/adapter-outbound/main.c"
)
CASES = ROOT / "benchmarks/interpreter/sanitizer-cases.json"
EVIDENCE = ROOT / (
    "benchmarks/interpreter/evidence/windows-x86_64-sanitizer-findings.json"
)
CLANG = ROOT / ".dependencies/llvm/22.1.8/bin/clang.exe"
ASAN_RUNTIME = ROOT / (
    ".dependencies/llvm/22.1.8/lib/clang/22/lib/windows/"
    "clang_rt.asan_dynamic-x86_64.dll"
)
SOURCE_SHA256 = (
    "fe29a717f9f684d6cc81d5c63273d446d9c65fec73e62164538514d5737b07a6"
)
SCHEMA_VERSION = 1
RUN_TIMEOUT_SECONDS = 15
MAX_DOCUMENT_BYTES = 1_048_576
_NATIVE_JSON_DECODER = json.JSONDecoder
MAX_FIXTURE_BYTES = 1_048_576
MAX_NATIVE_DESCRIPTOR = (1 << 31) - 1
PARENT_COMPONENT = ".."
WINDOWS_OS_NAME = "nt"
ASAN_ERROR = re.compile(r"ERROR: AddressSanitizer: ([a-z0-9-]+)")
UBSAN_ERROR = re.compile(r"runtime error: ([^\r\n]+)")
CASE_IDENTIFIER_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}\Z")
WINDOWS_DEVICE_STEM = re.compile(
    r"(?:con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\..*)?\Z",
    flags=re.IGNORECASE,
)
HALLOC_HEADER = (
    "#include <stddef.h>\nvoid *_halloc(size_t count, size_t size);\n"
)
HALLOC_SOURCE = (
    "#include <stddef.h>\n"
    "#include <stdlib.h>\n"
    "\n"
    "void *_halloc(size_t count, size_t size)\n"
    "{\n"
    "    return calloc(count, size);\n"
    "}\n"
)

JsonObject = dict[str, object]


class SanitizerHarnessError(RuntimeError):
    """Historical sanitizer evidence could not be reproduced safely."""


@dataclass(frozen=True, slots=True)
class SanitizerCase:
    """One reviewed historical interpreter sanitizer input."""

    identifier: str
    input_bytes: bytes
    source_bytes: bytes

    def __post_init__(self) -> None:
        """Reject direct cases that could escape temporary fixture filenames."""
        _ = _validated_case_identifier(self.identifier)


class _Arguments(argparse.Namespace):
    print_json: bool

    def __init__(self) -> None:
        super().__init__()
        self.print_json = False


def _fail(message: str) -> Never:
    raise SanitizerHarnessError(message)


def _validated_case_identifier(value: object) -> str:
    if type(value) is not str or not value:
        _fail("sanitizer case id must be non-empty")
    if (
        CASE_IDENTIFIER_PATTERN.fullmatch(value) is None
        or WINDOWS_DEVICE_STEM.fullmatch(value) is not None
    ):
        _fail("sanitizer case id must be a portable filename stem")
    return value


def is_supported() -> bool:
    """Report whether the pinned Windows sanitizer toolchain is available.

    Returns:
        True when the host and every required pinned tool are available.

    """
    return (
        os.name == WINDOWS_OS_NAME
        and CLANG.is_file()
        and ASAN_RUNTIME.is_file()
    )


def _mapping(value: object, context: str) -> JsonObject:
    if not isinstance(value, dict):
        _fail(f"{context} must be an object")
    raw = cast("dict[object, object]", value)
    result: JsonObject = {}
    for key, item in raw.items():
        if not isinstance(key, str):
            _fail(f"{context} contains a non-string key")
        result[key] = item
    return result


def _array(value: object, context: str) -> list[object]:
    if not isinstance(value, list):
        _fail(f"{context} must be an array")
    return cast("list[object]", value)


def _reject_duplicate_pairs(pairs: list[tuple[str, object]]) -> JsonObject:
    document: JsonObject = {}
    for key, value in pairs:
        if key in document:
            _fail(f"duplicate sanitizer JSON key: {key}")
        document[key] = value
    return document


def _regular_identity(
    status: object,
    limit: int,
) -> tuple[int, int, int, int, int]:
    if type(status) is not os.stat_result:
        _fail("sanitizer input requires native stat receipt")
    fields = (
        status.st_mode,
        status.st_dev,
        status.st_ino,
        status.st_size,
        status.st_mtime_ns,
        status.st_ctime_ns,
    )
    if any(type(field) is not int for field in fields) or status.st_size < 0:
        _fail("sanitizer input requires native stat fields")
    if not S_ISREG(status.st_mode):
        _fail("sanitizer input must be a regular file")
    if status.st_size > limit:
        _fail("sanitizer input exceeds byte limit")
    return (
        status.st_dev,
        status.st_ino,
        status.st_size,
        status.st_mtime_ns,
        status.st_ctime_ns,
    )


def _require_unredirected(path: Path) -> None:
    for check in (path.is_symlink, path.is_junction):
        redirected = check()
        if type(redirected) is not bool:
            _fail("sanitizer input requires native redirect receipt")
        if redirected:
            _fail("sanitizer input path must not redirect")


def _reject_redirected_parents(path: Path) -> None:
    for parent in path.parents:
        _require_unredirected(parent)


def _read_regular(path: Path, *, limit: int) -> bytes:
    """Bind a bounded regular input to its opened inode and original path.

    Returns:
        The exact stable bytes of a non-redirected regular input.

    """
    _reject_redirected_parents(path)
    admitted = path.lstat()
    expected = _regular_identity(admitted, limit)
    _require_unredirected(path)
    flags = (
        os.O_RDONLY
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_NONBLOCK", 0)
        | getattr(os, "O_BINARY", 0)
    )
    descriptor = os.open(path, flags)
    if type(descriptor) is not int or not 0 <= descriptor <= MAX_NATIVE_DESCRIPTOR:
        _fail("sanitizer input requires native descriptor")
    try:
        stream = os.fdopen(descriptor, "rb")
    except (OSError, ValueError, TypeError, RuntimeError) as error:
        # The descriptor remains owned by this reader until wrapping succeeds.
        try:
            os.close(descriptor)
        except OSError:
            pass
        raise SanitizerHarnessError(
            "cannot read sanitizer input: host stream wrapper failed"
        ) from error
    # A foreign fdopen wrapper could supply invented content while reporting
    # the original file descriptor. Admit only native wrappers bound to our fd.
    if type(stream) is not io.BufferedReader:
        try:
            os.close(descriptor)
        except OSError:
            pass
        _fail("sanitizer input requires native stream receipt")
    raw_stream = stream.raw
    if (
        type(raw_stream) is not io.FileIO
        or type(raw_stream.name) is not int
        or raw_stream.name != descriptor
        or raw_stream.fileno() != descriptor
        or stream.fileno() != descriptor
    ):
        # A substituted reader may own another fd. Close only our descriptor.
        try:
            os.close(descriptor)
        except OSError:
            pass
        _fail("sanitizer input requires native stream receipt")
    with stream:
        if _regular_identity(os.fstat(stream.fileno()), limit) != expected:
            _fail("sanitizer input changed before read")
        contents = stream.read(limit + 1)
        if (
            len(contents) != admitted.st_size
            or _regular_identity(os.fstat(stream.fileno()), limit) != expected
            or _regular_identity(path.lstat(), limit) != expected
        ):
            _fail("sanitizer input changed during read")
    _reject_redirected_parents(path)
    return contents


def _same_native_json(actual: object, expected: object) -> bool:
    """Compare entire decoded JSON trees without foreign equality hooks."""
    kind = type(expected)
    if type(actual) is not kind:
        return False
    if kind is dict:
        observed = cast("dict[object, object]", actual)
        source = cast("dict[object, object]", expected)
        # Reject a colliding foreign key before dictionary lookup.
        if any(type(key) is not str for key in observed):
            return False
        return len(observed) == len(source) and all(
            key in observed and _same_native_json(observed[key], value)
            for key, value in source.items()
        )
    if kind is list:
        observed = cast("list[object]", actual)
        source = cast("list[object]", expected)
        return len(observed) == len(source) and all(
            _same_native_json(left, right)
            for left, right in zip(observed, source, strict=True)
        )
    return kind in (bool, int, float, str, type(None)) and actual == expected


def _load_object(path: Path) -> JsonObject:
    try:
        source = _read_regular(path, limit=MAX_DOCUMENT_BYTES).decode("utf-8")
        # Capture before invocation: an injected provider may restore the
        # module loader during its call to conceal forged case/evidence data.
        decoder = json.loads
        parsed = cast(
            "object",
            decoder(source, object_pairs_hook=_reject_duplicate_pairs),
        )
        # The public JSON loader also delegates to mutable json.JSONDecoder.
        # Always parse using the class selected before public substitution,
        # then compare every native value without running foreign hooks.
        original = cast(
            "object",
            _NATIVE_JSON_DECODER(object_pairs_hook=_reject_duplicate_pairs).decode(
                source
            ),
        )
        if not _same_native_json(parsed, original):
            _fail("sanitizer JSON decoder provider differs from source")
        # Do not retain any nested mutable aliases owned by the adapter.
        parsed = original
    except (
        OSError,
        ValueError,
        UnicodeDecodeError,
        json.JSONDecodeError,
        RecursionError,
    ) as error:
        _fail(f"cannot load {path}: {error}")
    return _mapping(parsed, str(path))


def _relative_source_path(value: str, context: str) -> Path:
    relative = Path(value)
    if (
        relative.is_absolute()
        or PARENT_COMPONENT in relative.parts
        or relative.drive
    ):
        _fail(f"{context} escapes the repository")
    return relative


def _decode_hex(value: object, context: str) -> bytes:
    if not isinstance(value, str):
        _fail(f"{context} must be a hexadecimal string")
    try:
        return bytes.fromhex(value)
    except ValueError as error:
        _fail(f"invalid {context}: {error}")


def _path_source(
    value: object,
    identifier: str,
    source_root: Path,
) -> bytes:
    if not isinstance(value, str):
        _fail(f"case {identifier} source must be text")
    relative = _relative_source_path(value, f"case {identifier} source")
    path = source_root / relative
    try:
        _ = path.relative_to(ROOT)
        return _read_regular(path, limit=MAX_FIXTURE_BYTES)
    except ValueError:
        _fail(f"case {identifier} source escapes the repository")
    except OSError as error:
        _fail(f"case {identifier} source is unavailable: {error}")


def _case_source(
    raw: JsonObject,
    identifier: str,
    source_root: Path,
) -> bytes:
    source = raw.get("source")
    source_hex = raw.get("source_hex")
    if (source is None) == (source_hex is None):
        _fail(f"case {identifier} must declare exactly one source form")
    if source is not None:
        return _path_source(source, identifier, source_root)
    return _decode_hex(source_hex, f"case {identifier} source_hex")


def _parse_case(
    raw: object,
    identifiers: set[str],
    source_root: Path,
) -> SanitizerCase:
    case = _mapping(raw, "sanitizer case")
    identifier = _validated_case_identifier(case.get("id"))
    normalized_identifier = identifier.casefold()
    if normalized_identifier in identifiers:
        _fail(f"duplicate sanitizer case: {identifier}")
    identifiers.add(normalized_identifier)
    return SanitizerCase(
        identifier=identifier,
        input_bytes=_decode_hex(
            case.get("input_hex"),
            f"case {identifier} input_hex",
        ),
        source_bytes=_case_source(case, identifier, source_root),
    )


def _source_root(document: JsonObject) -> Path:
    value = document.get("source_root")
    if not isinstance(value, str):
        _fail("sanitizer source_root must be text")
    relative = _relative_source_path(value, "sanitizer source_root")
    source_root = ROOT / relative
    _reject_redirected_parents(source_root)
    try:
        if source_root.is_symlink() or source_root.is_junction():
            _fail("sanitizer source_root must not redirect")
        if not S_ISDIR(source_root.lstat().st_mode):
            _fail("sanitizer source_root is not a directory")
    except OSError as error:
        _fail(f"sanitizer source_root is unavailable: {error}")
    return source_root


def load_cases() -> tuple[SanitizerCase, ...]:
    """Load and validate the reviewed sanitizer case manifest.

    Returns:
        Ordered immutable sanitizer cases from the reviewed manifest.

    """
    document = _load_object(CASES)
    if document.get("schema_version") != SCHEMA_VERSION:
        _fail("unsupported sanitizer case schema")
    source_root = _source_root(document)
    raw_cases = _array(document.get("cases"), "sanitizer cases")
    if not raw_cases:
        _fail("sanitizer cases must be a non-empty list")
    identifiers: set[str] = set()
    return tuple(
        _parse_case(raw, identifiers, source_root) for raw in raw_cases
    )


def load_evidence() -> JsonObject:
    """Load the reviewed normalized sanitizer result.

    Returns:
        Reviewed normalized sanitizer evidence object.

    """
    document = _load_object(EVIDENCE)
    if document.get("schema_version") != SCHEMA_VERSION:
        _fail("unsupported sanitizer evidence schema")
    return document


def _run(
    command: Sequence[str],
    *,
    cwd: Path,
) -> subprocess.CompletedProcess[bytes]:
    try:
        return subprocess.run(  # ruff: ignore[subprocess-without-shell-equals-true]
            command,
            cwd=cwd,
            check=False,
            shell=False,
            capture_output=True,
            timeout=RUN_TIMEOUT_SECONDS,
        )
    except (
        OSError,
        ValueError,
        TypeError,
        RuntimeError,
        subprocess.TimeoutExpired,
    ) as error:
        detail = _native_host_error_detail(error)
        raise SanitizerHarnessError(
            f"sanitizer compiler process launch failed: {detail}"
        ) from error


def _native_process_receipt(
    result: object,
    command: tuple[str, ...],
) -> subprocess.CompletedProcess[bytes]:
    """Admit exact argv, native exit status and byte streams as process evidence.

    Returns:
        The checked subprocess completion without invoking foreign hooks.

    """
    if type(result) is not subprocess.CompletedProcess:
        _fail("invalid sanitizer process receipt")
    completed = cast("subprocess.CompletedProcess[bytes]", result)
    if (
        type(completed.args) is not tuple
        or len(completed.args) != len(command)
        or any(type(argument) is not str for argument in completed.args)
        or completed.args != command
        or type(completed.returncode) is not int
        or type(completed.stdout) is not bytes
        or type(completed.stderr) is not bytes
    ):
        _fail("invalid sanitizer process receipt")
    return completed


def _compiler_identity() -> None:
    command = (str(CLANG), "--version")
    completed = _native_process_receipt(_run(command, cwd=ROOT), command)
    first_line = completed.stdout.decode("utf-8", errors="replace").splitlines()
    if completed.returncode != 0 or not first_line:
        _fail("pinned Clang version query failed")
    if not first_line[0].startswith("clang version 22.1.8 "):
        _fail(f"unexpected compiler: {first_line[0]}")


def _verify_source() -> bytes:
    """Validate and return the exact bytes of the historical interpreter.

    Returns:
        Hash-verified C source bytes for the isolated compiler input.

    """
    try:
        source = _read_regular(SOURCE, limit=MAX_FIXTURE_BYTES)
    except OSError as error:
        detail = _native_host_error_detail(error)
        raise SanitizerHarnessError(
            f"historical source is unavailable: {detail}"
        ) from error
    observed = sha256(source).hexdigest()
    if observed != SOURCE_SHA256:
        _fail(f"historical source hash mismatch: {observed}")
    return source


def _write_staged_bytes(path: Path, content: bytes) -> None:
    """Demand a complete staged source write before external execution."""
    written = path.write_bytes(content)
    if type(written) is not int or written != len(content):
        _fail(f"sanitizer staged {path.name} has invalid write count")


def _write_staged_text(path: Path, content: str) -> None:
    """Demand a complete generated C shim write before compiler execution."""
    written = path.write_text(content, encoding="ascii", newline="\n")
    if type(written) is not int or written != len(content):
        _fail(f"sanitizer staged {path.name} has invalid write count")


def _build(work: Path, *, source_bytes: bytes) -> Path:
    source = work / "main.c"
    _write_staged_bytes(source, source_bytes)
    if _read_regular(source, limit=MAX_FIXTURE_BYTES) != source_bytes:
        _fail("staged historical source differs from verified source")
    header = work / "halloc_compat.h"
    shim = work / "halloc_compat.c"
    executable = work / "malbolge-sanitized.exe"
    _write_staged_text(header, HALLOC_HEADER)
    _write_staged_text(shim, HALLOC_SOURCE)
    command = (
        str(CLANG),
        "-D_CRT_SECURE_NO_WARNINGS=1",
        "-include",
        str(header),
        "-std=c89",
        "-O1",
        "-g",
        "-fno-omit-frame-pointer",
        "-fsanitize=address,undefined",
        "-Wall",
        "-Wextra",
        "-Werror",
        "-Wno-unused-variable",
        str(source),
        str(shim),
        "-o",
        str(executable),
    )
    completed = _native_process_receipt(_run(command, cwd=ROOT), command)
    if completed.returncode != 0 or not executable.is_file():
        stderr = completed.stderr.decode("utf-8", errors="replace")
        message = "sanitizer build failed: " + stderr
        _fail(message)
    _ = shutil.copy2(ASAN_RUNTIME, work / ASAN_RUNTIME.name)
    return executable


def _findings(stderr: bytes) -> list[str]:
    text = stderr.decode("utf-8", errors="replace")
    findings = [
        f"address-sanitizer:{match.group(1)}"
        for match in ASAN_ERROR.finditer(text)
    ]
    findings.extend(
        f"undefined-behavior-sanitizer:{match.group(1).strip()}"
        for match in UBSAN_ERROR.finditer(text)
    )
    return sorted(set(findings))


def _execute_case(
    executable: Path,
    work: Path,
    case: SanitizerCase,
) -> JsonObject:
    identifier = _validated_case_identifier(case.identifier)
    source = work / f"{identifier}.malbolge"
    _write_staged_bytes(source, case.source_bytes)
    environment = os.environ.copy()
    environment["ASAN_OPTIONS"] = (
        "halt_on_error=1:abort_on_error=0:detect_leaks=0:symbolize=0"
    )
    environment["UBSAN_OPTIONS"] = "halt_on_error=1:print_stacktrace=0"
    command = (str(executable), str(source))
    try:
        # jig-ignore-next-line: reviewed local subprocess boundary uses argv only
        completed = subprocess.run(  # ruff: ignore[subprocess-without-shell-equals-true]
            command,
            cwd=work,
            check=False,
            shell=False,
            input=case.input_bytes,
            capture_output=True,
            timeout=RUN_TIMEOUT_SECONDS,
            env=environment,
        )
    except (
        OSError,
        ValueError,
        TypeError,
        RuntimeError,
        subprocess.TimeoutExpired,
    ) as error:
        detail = _native_host_error_detail(error)
        raise SanitizerHarnessError(
            f"sanitizer case {identifier} process launch failed: {detail}"
        ) from error
    completed = _native_process_receipt(completed, command)
    findings = _findings(completed.stderr)
    if findings:
        if completed.returncode == 0:
            _fail(f"case {case.identifier} reported a finding with status zero")
        status = "sanitizer-failure"
    else:
        if completed.returncode != 0:
            stderr = completed.stderr.decode("utf-8", errors="replace")
            message = (
                f"case {case.identifier} failed without sanitizer evidence: "
                + stderr
            )
            _fail(message)
        status = "clean"
    return {
        "id": case.identifier,
        "status": status,
        "stdout_hex": completed.stdout.hex(),
        "findings": findings,
    }


def _native_host_error_detail(error: Exception) -> str:
    """Render exact native host faults without calling foreign text hooks.

    Returns:
        Native diagnostic text or the foreign exception's class name.

    """
    if type(error) in {
        OSError,
        FileNotFoundError,
        FileExistsError,
        PermissionError,
        IsADirectoryError,
        NotADirectoryError,
        TimeoutError,
        ValueError,
        TypeError,
        RuntimeError,
    }:
        return str(error)
    return type(error).__name__


def _require_physical_staging_directory(path: Path, label: str) -> None:
    """Require native stat and redirect receipts for a staging directory."""
    try:
        status = path.lstat()
    except (OSError, ValueError, TypeError, RuntimeError) as error:
        detail = _native_host_error_detail(error)
        raise SanitizerHarnessError(f"{label} status failed: {detail}") from error
    if type(status) is not os.stat_result or type(status.st_mode) is not int:
        _fail(f"{label} has invalid stat receipt")
    try:
        symlink = path.is_symlink()
        junction = path.is_junction()
        exists = path.exists()
        directory = path.is_dir()
    except (OSError, ValueError, TypeError, RuntimeError) as error:
        detail = _native_host_error_detail(error)
        raise SanitizerHarnessError(f"{label} status failed: {detail}") from error
    if any(type(value) is not bool for value in (symlink, junction, exists, directory)):
        _fail(f"{label} has invalid path status receipt")
    if symlink or junction or S_ISLNK(status.st_mode):
        _fail(f"{label} must not redirect")
    if not (exists and directory and S_ISDIR(status.st_mode)):
        _fail(f"{label} must be a physical directory")


def _admit_temporary_root(root: Path) -> None:
    """Require a physical repository-local staging root before building."""
    try:
        root.mkdir(exist_ok=True)
    except FileExistsError as error:
        if type(error) is not FileExistsError:
            detail = _native_host_error_detail(error)
            raise SanitizerHarnessError(
                f"sanitizer temporary root creation failed: {detail}"
            ) from error
        # Validate the existing leaf, rather than leaking raw mkdir failure.
    except (OSError, ValueError, TypeError, RuntimeError) as error:
        detail = _native_host_error_detail(error)
        raise SanitizerHarnessError(
            f"sanitizer temporary root creation failed: {detail}"
        ) from error
    _require_physical_staging_directory(root, "sanitizer temporary root")


def _admit_temporary_workspace(root: Path, directory: object) -> Path:
    """Admit the exact physical stage yielded by TemporaryDirectory."""
    if type(directory) is not str:
        _fail("sanitizer temporary workspace must have a native path receipt")
    work = Path(directory)
    if (
        not work.is_absolute()
        or work != Path(os.path.abspath(work))  # ruff: ignore[os-path-abspath]
        or work.parent != Path(os.path.abspath(root))  # ruff: ignore[os-path-abspath]
        or re.fullmatch(r"historical-sanitizer-[a-z0-9_]{8}", work.name) is None
    ):
        _fail("sanitizer temporary workspace is outside requested staging root")
    _require_physical_staging_directory(work, "sanitizer temporary workspace")
    return work


def run_harness() -> JsonObject:
    """Build, execute, and return normalized sanitizer evidence.

    Returns:
        Reproduced address/undefined sanitizer evidence.

    """
    if not is_supported():
        _fail("pinned Windows Clang sanitizer toolchain is unavailable")
    _compiler_identity()
    source_bytes = _verify_source()
    temporary_root = ROOT / ".temp"
    _admit_temporary_root(temporary_root)
    with tempfile.TemporaryDirectory(
        prefix="historical-sanitizer-",
        dir=temporary_root,
    ) as directory:
        _admit_temporary_root(temporary_root)
        work = _admit_temporary_workspace(temporary_root, directory)
        executable = _build(work, source_bytes=source_bytes)
        results = [
            _execute_case(executable, work, case) for case in load_cases()
        ]
    return {
        "schema_version": SCHEMA_VERSION,
        "compiler": "clang-22.1.8",
        "sanitizers": ["address", "undefined"],
        "source_sha256": SOURCE_SHA256,
        "cases": results,
    }


def _write_cli_record(stream: TextIO, message: str) -> bool:
    """Require a full native text-write acknowledgement and completed flush.

    Returns:
        Whether the complete CLI record was emitted.

    """
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


def _require_output(stream: TextIO, message: str) -> None:
    if not _write_cli_record(stream, message):
        _fail("sanitizer CLI output write or flush failed")


class _DeliveryParser(argparse.ArgumentParser):
    """Authenticate argparse help and argument-error diagnostic delivery."""

    @override
    def _print_message(self, message: str, file: object = None) -> None:
        if message:
            stream = sys.stderr if file is None else cast("TextIO", file)
            _require_output(stream, message)


def _parser() -> argparse.ArgumentParser:
    parser = _DeliveryParser(description=__doc__)
    _ = parser.add_argument(
        "--print-json",
        action="store_true",
        help="print normalized evidence after verification",
    )
    return parser


def _verified_harness() -> JsonObject:
    actual = run_harness()
    expected = load_evidence()
    if actual != expected:
        actual_text = json.dumps(actual, indent=2, sort_keys=True)
        expected_text = json.dumps(expected, indent=2, sort_keys=True)
        message = (
            f"sanitizer evidence drift\nexpected:\n{expected_text}"
            f"\nactual:\n{actual_text}"
        )
        _fail(message)
    return actual


def _parse_arguments() -> _Arguments:
    arguments = _Arguments()
    _ = _parser().parse_args(namespace=arguments)
    return arguments


def main() -> int:
    """Reproduce and verify the reviewed sanitizer evidence.

    Returns:
        Zero when evidence matches, otherwise one.

    """
    try:
        arguments = _parse_arguments()
        actual = _verified_harness()
        if arguments.print_json:
            message = json.dumps(actual, indent=2) + "\n"
        else:
            message = "historical interpreter sanitizer evidence valid\n"
        _require_output(sys.stdout, message)
    except (
        OSError,
        SanitizerHarnessError,
        subprocess.SubprocessError,
    ) as error:
        detail = (
            str(error)
            if type(error)
            in {
                OSError,
                SanitizerHarnessError,
                subprocess.SubprocessError,
                subprocess.TimeoutExpired,
                subprocess.CalledProcessError,
            }
            else type(error).__name__
        )
        _ = _write_cli_record(sys.stderr, f"error: {detail}\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
