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
from dataclasses import dataclass
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import shutil
import subprocess  # ruff: ignore[suspicious-subprocess-import]
import sys
import tempfile
from typing import Never
from typing import TYPE_CHECKING
from typing import cast

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
WINDOWS_OS_NAME = "nt"
ASAN_ERROR = re.compile(r"ERROR: AddressSanitizer: ([a-z0-9-]+)")
UBSAN_ERROR = re.compile(r"runtime error: ([^\r\n]+)")
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


class _Arguments(argparse.Namespace):
    print_json: bool

    def __init__(self) -> None:
        super().__init__()
        self.print_json = False


def _fail(message: str) -> Never:
    raise SanitizerHarnessError(message)


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


def _load_object(path: Path) -> JsonObject:
    try:
        parsed = cast(
            "object",
            json.loads(
                path.read_text(encoding="utf-8"),
                object_pairs_hook=_reject_duplicate_pairs,
            ),
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        _fail(f"cannot load {path}: {error}")
    return _mapping(parsed, str(path))


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
    path = (source_root / value).resolve()
    try:
        _ = path.relative_to(ROOT)
    except ValueError:
        _fail(f"case {identifier} source escapes the repository")
    if not path.is_file():
        _fail(f"case {identifier} source is missing: {path}")
    return path.read_bytes()


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
    identifier = case.get("id")
    if not isinstance(identifier, str) or not identifier:
        _fail("sanitizer case id must be non-empty")
    if identifier in identifiers:
        _fail(f"duplicate sanitizer case: {identifier}")
    identifiers.add(identifier)
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
    source_root = (ROOT / value).resolve()
    try:
        _ = source_root.relative_to(ROOT)
    except ValueError:
        _fail("sanitizer source_root escapes the repository")
    if not source_root.is_dir():
        _fail("sanitizer source_root is missing")
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
    return subprocess.run(  # ruff: ignore[subprocess-without-shell-equals-true]
        command,
        cwd=cwd,
        check=False,
        shell=False,
        capture_output=True,
        timeout=RUN_TIMEOUT_SECONDS,
    )


def _compiler_identity() -> None:
    completed = _run((str(CLANG), "--version"), cwd=ROOT)
    first_line = completed.stdout.decode("utf-8", errors="replace").splitlines()
    if completed.returncode != 0 or not first_line:
        _fail("pinned Clang version query failed")
    if not first_line[0].startswith("clang version 22.1.8 "):
        _fail(f"unexpected compiler: {first_line[0]}")


def _verify_source() -> None:
    try:
        source = SOURCE.read_bytes()
    except OSError as error:
        _fail(f"historical source is unavailable: {error}")
    observed = sha256(source).hexdigest()
    if observed != SOURCE_SHA256:
        _fail(f"historical source hash mismatch: {observed}")


def _build(work: Path) -> Path:
    header = work / "halloc_compat.h"
    shim = work / "halloc_compat.c"
    executable = work / "malbolge-sanitized.exe"
    _ = header.write_text(HALLOC_HEADER, encoding="ascii", newline="\n")
    _ = shim.write_text(HALLOC_SOURCE, encoding="ascii", newline="\n")
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
        str(SOURCE),
        str(shim),
        "-o",
        str(executable),
    )
    completed = _run(command, cwd=ROOT)
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
    source = work / f"{case.identifier}.malbolge"
    _ = source.write_bytes(case.source_bytes)
    environment = os.environ.copy()
    environment["ASAN_OPTIONS"] = (
        "halt_on_error=1:abort_on_error=0:detect_leaks=0:symbolize=0"
    )
    environment["UBSAN_OPTIONS"] = "halt_on_error=1:print_stacktrace=0"
    # jig-ignore-next-line: reviewed local subprocess boundary uses argv only
    completed = subprocess.run(  # ruff: ignore[subprocess-without-shell-equals-true]
        (str(executable), str(source)),
        cwd=work,
        check=False,
        shell=False,
        input=case.input_bytes,
        capture_output=True,
        timeout=RUN_TIMEOUT_SECONDS,
        env=environment,
    )
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


def run_harness() -> JsonObject:
    """Build, execute, and return normalized sanitizer evidence.

    Returns:
        Reproduced address/undefined sanitizer evidence.

    """
    if not is_supported():
        _fail("pinned Windows Clang sanitizer toolchain is unavailable")
    _compiler_identity()
    _verify_source()
    temporary_root = ROOT / ".temp"
    temporary_root.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix="historical-sanitizer-",
        dir=temporary_root,
    ) as directory:
        work = Path(directory)
        executable = _build(work)
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


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
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
    arguments = _parse_arguments()
    try:
        actual = _verified_harness()
    except (
        OSError,
        SanitizerHarnessError,
        subprocess.SubprocessError,
    ) as error:
        _ = sys.stderr.write(f"error: {error}\n")
        return 1
    if arguments.print_json:
        _ = sys.stdout.write(json.dumps(actual, indent=2) + "\n")
    else:
        message = "historical interpreter sanitizer evidence valid\n"
        _ = sys.stdout.write(message)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
