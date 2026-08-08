# Copyright:
#   - Copyright (c) 2026 Alberto Villa Osorno.
# SPDX-License-Identifier:
#   - MIT
# Confidential:
#   - false
# License-File:
#   - LICENSE-MIT
#
# Boundary-Contract:
# - Owns:
#   - ABI-only source preflight against the canonical deterministic guest-C ABI.
# - Must-Not:
#   - Replace the full tools/tidy lowerability contract or infer host ABI rules.
# - Allows:
#   - Inputs: explicitly selected C translation units and pinned Clang AST JSON.
#   - Outputs: deterministic source-located malbolge-abi diagnostics.
#   - Side effects: one pinned Clang parse per explicitly selected source file.
# - Split-When:
#   - Split when an ABI rule requires independent semantic analysis ownership.
# - Merge-When:
#   - Merge when the clang-tidy plugin owns these exact checks through one API.
# - Summary:
#   - Enforces v1 layout exclusions before the clang-tidy plugin is complete.
# - Description:
#   - Uses Clang only for syntax/type/source-location evidence; policy is local.
# - Usage:
#   - Called by manual guest-C validation and ABI fixture regression tests.
# - Defaults:
#   - Parse failures and malformed required AST evidence fail closed.
#

"""Emit source-located ABI diagnostics from pinned Clang AST evidence."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import subprocess as sp  # ruff: ignore[suspicious-subprocess-import]
import sys
from typing import Never
from typing import cast

if __package__ in {None, ""}:
    composition_root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(composition_root))

from scripts.repository_root import repository_root
from scripts.validate import c_abi

ROOT = repository_root(Path(__file__))
PINNED_LLVM_VERSION = "22.1.8"
PINNED_CLANG = ROOT / ".dependencies/llvm/22.1.8/bin/clang.exe"
DIAGNOSTIC_BIT_FIELD = "MALBOLGE-ABI-001"
DIAGNOSTIC_PACKED = "MALBOLGE-ABI-002"
DIAGNOSTIC_PRAGMA_PACK = "MALBOLGE-ABI-003"
DIAGNOSTIC_ALIGNMENT = "MALBOLGE-ABI-004"
DIAGNOSTIC_BIT_INT = "MALBOLGE-ABI-005"
DIAGNOSTIC_INT128 = "MALBOLGE-ABI-006"
DIAGNOSTIC_VECTOR = "MALBOLGE-ABI-007"
DIAGNOSTIC_ADDRESS_SPACE = "MALBOLGE-ABI-008"
AST_FIELD_DECL = "FieldDecl"
AST_PACKED_ATTR = "PackedAttr"
AST_PACK_ALIGNMENT_ATTR = "MaxFieldAlignmentAttr"
AST_ALIGNED_ATTR = "AlignedAttr"
TYPE_BIT_INT = "_BitInt("
TYPE_INT128 = "__int128"
TYPE_VECTOR_SIZE = "__vector_size__"
TYPE_EXT_VECTOR = "ext_vector_type"
TYPE_ADDRESS_SPACE = "address_space("


type JsonScalar = bool | int | float | str | None
type JsonValue = JsonScalar | list[JsonValue] | dict[str, JsonValue]
type JsonObject = dict[str, JsonValue]


@dataclass(frozen=True, slots=True)
class AbiDiagnostic:
    """One deterministic source-located guest ABI rejection."""

    code: str
    column: int
    line: int
    message: str
    path: Path

    def render(self) -> str:
        """Render one Clang-style deterministic diagnostic line.

        Returns:
            A stable source-located diagnostic string.

        """
        return (
            f"{self.path}:{self.line}:{self.column}: error: "
            f"{self.code} {self.message}"
        )


@dataclass(frozen=True, slots=True)
class _Location:
    path: Path
    line: int
    column: int
    offset: int | None


@dataclass(frozen=True, slots=True)
class _AnalysisContext:
    source: Path
    source_bytes: bytes


class SourceAnalysisError(RuntimeError):
    """Pinned Clang could not provide valid AST evidence."""


class _Arguments(argparse.Namespace):
    files: list[Path]
    clang: Path

    def __init__(self) -> None:
        """Initialize typed defaults before argparse mutates this namespace."""
        super().__init__()
        self.files = []
        self.clang = PINNED_CLANG


def _fail(message: str) -> Never:
    raise SourceAnalysisError(message)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Check explicitly named C files for malbolge-c32-v1 ABI exclusions."
        )
    )
    _ = parser.add_argument("files", nargs="+", type=Path, metavar="FILE")
    _ = parser.add_argument("--clang", type=Path, default=PINNED_CLANG)
    return parser


def _parse_arguments() -> _Arguments:
    arguments = _Arguments()
    _ = _parser().parse_args(namespace=arguments)
    return arguments


def _ast_command(source: Path, clang: Path, target: str) -> list[str]:
    return [
        str(clang),
        f"--target={target}",
        "-std=c23",
        "-ffreestanding",
        "-fno-builtin",
        "-pedantic-errors",
        "-Werror=implicit-function-declaration",
        "-Werror=incompatible-pointer-types",
        "-Werror=int-conversion",
        "-Werror=return-type",
        "-Werror=uninitialized",
        "-fsyntax-only",
        "-Xclang",
        "-ast-dump=json",
        str(source),
    ]


def _clang_identity(clang: Path) -> str:
    try:
        # jig-ignore-next-line: indivisible reviewed identifier
        completed = sp.run(  # ruff: ignore[subprocess-without-shell-equals-true]
            [str(clang), "--version"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            shell=False,
        )
    except OSError as error:
        _fail(f"failed to execute Clang version query {clang}: {error}")
    if completed.returncode != 0:
        _fail(f"Clang version query failed for {clang}")
    return completed.stdout + chr(10) + completed.stderr


def _require_ast_inputs(source: Path, clang: Path) -> None:
    if not clang.is_file():
        _fail(f"pinned Clang not found: {clang}")
    expected = f"clang version {PINNED_LLVM_VERSION}"
    if expected not in _clang_identity(clang):
        _fail(f"Clang must report {expected}: {clang}")
    if not source.is_file():
        _fail(f"source is not a regular file: {source}")


def _parse_ast_output(text: str, source: Path) -> JsonObject:
    try:
        parsed = cast("object", json.loads(text))
    except json.JSONDecodeError as error:
        _fail(f"invalid Clang AST JSON for {source}: {error}")
    if not isinstance(parsed, dict):
        _fail(f"Clang AST root must be an object for {source}")
    return cast("JsonObject", parsed)


def _run_ast(source: Path, clang: Path, target: str) -> JsonObject:
    _require_ast_inputs(source, clang)
    try:
        # jig-ignore-next-line: indivisible reviewed identifier
        completed = sp.run(  # ruff: ignore[subprocess-without-shell-equals-true]
            _ast_command(source, clang, target),
            cwd=ROOT,
            check=False,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            shell=False,
        )
    except OSError as error:
        _fail(f"failed to execute Clang AST parse {clang}: {error}")
    if completed.returncode != 0:
        detail = completed.stderr.strip()
        _fail(detail or f"Clang AST parse failed for {source}")
    return _parse_ast_output(completed.stdout, source)


def _line_column_from_offset(
    source_bytes: bytes,
    offset: int,
) -> tuple[int, int]:
    if offset < 0 or offset > len(source_bytes):
        _fail(f"Clang AST offset is outside source extent: {offset}")
    line = source_bytes.count(b"\n", 0, offset) + 1
    previous_newline = source_bytes.rfind(b"\n", 0, offset)
    column = offset + 1 if previous_newline < 0 else offset - previous_newline
    return line, column


def _location_mapping(value: JsonValue | None) -> JsonObject | None:
    return value if isinstance(value, dict) else None


def _location_candidates(node: JsonObject) -> tuple[JsonObject, ...]:
    result: list[JsonObject] = []
    direct = _location_mapping(node.get("loc"))
    if direct is not None:
        result.append(direct)
    raw_range = _location_mapping(node.get("range"))
    begin = (
        None if raw_range is None else _location_mapping(raw_range.get("begin"))
    )
    if begin is not None:
        result.append(begin)
    return tuple(result)


def _optional_int(value: JsonValue | None) -> int | None:
    return value if type(value) is int else None


def _candidate_path(
    candidate: JsonObject,
    context: _AnalysisContext,
    inherited: _Location | None,
) -> Path:
    file_value = candidate.get("file")
    if isinstance(file_value, str):
        path = Path(file_value)
        return path if path.is_absolute() else (ROOT / path).resolve()
    return inherited.path if inherited is not None else context.source


def _candidate_line_column(
    candidate: JsonObject,
    context: _AnalysisContext,
    path: Path,
    *,
    inherited: _Location | None,
) -> tuple[int | None, int | None, int | None]:
    offset = _optional_int(candidate.get("offset"))
    line = _optional_int(candidate.get("line"))
    column = _optional_int(candidate.get("col"))
    derived_column: int | None = None
    if line is None and offset is not None and path == context.source:
        line, derived_column = _line_column_from_offset(
            context.source_bytes, offset
        )
    if column is None:
        column = derived_column
    if inherited is not None:
        line = line if line is not None else inherited.line
        column = column if column is not None else inherited.column
    return line, column, offset


def _candidate_location(
    candidate: JsonObject,
    context: _AnalysisContext,
    inherited: _Location | None,
) -> _Location | None:
    path = _candidate_path(candidate, context, inherited)
    line, column, offset = _candidate_line_column(
        candidate,
        context,
        path,
        inherited=inherited,
    )
    if line is None or column is None:
        return None
    return _Location(path=path, line=line, column=column, offset=offset)


def _node_location(
    node: JsonObject,
    context: _AnalysisContext,
    inherited: _Location | None,
) -> _Location | None:
    for candidate in _location_candidates(node):
        location = _candidate_location(candidate, context, inherited)
        if location is not None:
            return location
    return inherited


def _decimal_value(node: JsonObject) -> int | None:
    raw = node.get("value")
    if not isinstance(raw, str) or not raw.isdecimal():
        return None
    return int(raw, 10)


def _aligned_value(node: JsonObject) -> int | None:
    inner = node.get("inner")
    if not isinstance(inner, list):
        return None
    for candidate in inner:
        if isinstance(candidate, dict):
            value = _decimal_value(candidate)
            if value is not None:
                return value
    return None


def _diagnostic(
    *,
    code: str,
    location: _Location | None,
    message: str,
    source: Path,
) -> AbiDiagnostic:
    if location is None:
        _fail(f"Clang AST omitted a source location for {code} in {source}")
    return AbiDiagnostic(
        code=code,
        column=location.column,
        line=location.line,
        message=message,
        path=location.path,
    )


def _bit_field_diagnostic(
    node: JsonObject,
    location: _Location | None,
    source: Path,
) -> AbiDiagnostic | None:
    if node.get("kind") != AST_FIELD_DECL or node.get("isBitfield") is not True:
        return None
    return _diagnostic(
        code=DIAGNOSTIC_BIT_FIELD,
        location=location,
        message="bit-fields are outside malbolge-c32-v1 object layout",
        source=source,
    )


def _attribute_diagnostic(
    node: JsonObject,
    location: _Location | None,
    source: Path,
) -> AbiDiagnostic | None:
    rules = {
        AST_PACKED_ATTR: (
            DIAGNOSTIC_PACKED,
            "packed record layout is outside malbolge-c32-v1",
        ),
        AST_PACK_ALIGNMENT_ATTR: (
            DIAGNOSTIC_PRAGMA_PACK,
            "#pragma pack is outside malbolge-c32-v1",
        ),
    }
    kind = node.get("kind")
    rule = rules.get(kind) if isinstance(kind, str) else None
    if rule is None:
        return None
    code, message = rule
    return _diagnostic(
        code=code,
        location=location,
        message=message,
        source=source,
    )


def _alignment_diagnostic(
    node: JsonObject,
    location: _Location | None,
    source: Path,
) -> AbiDiagnostic | None:
    if node.get("kind") != AST_ALIGNED_ATTR:
        return None
    alignment = _aligned_value(node)
    if alignment is None or alignment <= c_abi.MAX_ALIGNMENT:
        return None
    return _diagnostic(
        code=DIAGNOSTIC_ALIGNMENT,
        location=location,
        message=(
            f"requested alignment {alignment} exceeds "
            f"malbolge-c32-v1 maximum {c_abi.MAX_ALIGNMENT}"
        ),
        source=source,
    )


def _type_text(node: JsonObject) -> str:
    raw_type = node.get("type")
    if not isinstance(raw_type, dict):
        return ""
    desugared = raw_type.get("desugaredQualType")
    if isinstance(desugared, str):
        return desugared
    qualified = raw_type.get("qualType")
    return qualified if isinstance(qualified, str) else ""


def _type_diagnostics(
    node: JsonObject,
    location: _Location | None,
    source: Path,
) -> list[AbiDiagnostic]:
    if location is None:
        return []
    type_text = _type_text(node)
    rules = (
        (
            (TYPE_BIT_INT,),
            DIAGNOSTIC_BIT_INT,
            "bit-precise integers are outside malbolge-c32-v1",
        ),
        (
            (TYPE_INT128,),
            DIAGNOSTIC_INT128,
            "128-bit integer extensions are outside malbolge-c32-v1",
        ),
        (
            (TYPE_VECTOR_SIZE, TYPE_EXT_VECTOR),
            DIAGNOSTIC_VECTOR,
            "compiler vector types are outside malbolge-c32-v1",
        ),
        (
            (TYPE_ADDRESS_SPACE,),
            DIAGNOSTIC_ADDRESS_SPACE,
            "non-default address spaces are outside malbolge-c32-v1",
        ),
    )
    result: list[AbiDiagnostic] = []
    for markers, code, message in rules:
        if any(marker in type_text for marker in markers):
            result.append(
                _diagnostic(
                    code=code,
                    location=location,
                    message=message,
                    source=source,
                )
            )
    return result


def _node_diagnostics(
    node: JsonObject,
    location: _Location | None,
    source: Path,
) -> list[AbiDiagnostic]:
    if node.get("isImplicit") is True:
        return []
    result = _type_diagnostics(node, location, source)
    for diagnostic in (
        _bit_field_diagnostic(node, location, source),
        _attribute_diagnostic(node, location, source),
        _alignment_diagnostic(node, location, source),
    ):
        if diagnostic is not None:
            result.append(diagnostic)
    return result


def _walk_ast(
    value: JsonValue,
    context: _AnalysisContext,
    *,
    inherited: _Location | None,
    diagnostics: list[AbiDiagnostic],
) -> None:
    if isinstance(value, list):
        for item in value:
            _walk_ast(
                item,
                context,
                inherited=inherited,
                diagnostics=diagnostics,
            )
        return
    if not isinstance(value, dict):
        return
    location = _node_location(value, context, inherited)
    diagnostics.extend(_node_diagnostics(value, location, context.source))
    inner = value.get("inner")
    if isinstance(inner, (dict, list)):
        _walk_ast(
            inner,
            context,
            inherited=location,
            diagnostics=diagnostics,
        )


def _deduplicate(diagnostics: list[AbiDiagnostic]) -> tuple[AbiDiagnostic, ...]:
    seen: set[tuple[str, Path, int, int]] = set()
    result: list[AbiDiagnostic] = []
    for diagnostic in diagnostics:
        key = (
            diagnostic.code,
            diagnostic.path,
            diagnostic.line,
            diagnostic.column,
        )
        if key in seen:
            continue
        seen.add(key)
        result.append(diagnostic)
    result.sort(
        key=lambda item: (
            item.path.as_posix(),
            item.line,
            item.column,
            item.code,
        )
    )
    return tuple(result)


def analyze_source(
    source: Path,
    *,
    clang: Path = PINNED_CLANG,
    projection: c_abi.CAbiProjection | None = None,
) -> tuple[AbiDiagnostic, ...]:
    """Analyze one explicit translation unit against ABI-only v1 exclusions.

    Returns:
        The stable source-located ABI diagnostics, if any.

    """
    resolved = source.resolve()
    active_projection = projection or c_abi.canonical_projection()
    try:
        source_bytes = resolved.read_bytes()
        _ = source_bytes.decode("utf-8")
    except UnicodeDecodeError as error:
        _fail(f"invalid guest-C UTF-8 in {resolved}: {error}")
    except OSError as error:
        _fail(f"failed to read guest C source {resolved}: {error}")
    ast = _run_ast(resolved, clang.resolve(), active_projection.clang_target)
    diagnostics: list[AbiDiagnostic] = []
    context = _AnalysisContext(source=resolved, source_bytes=source_bytes)
    _walk_ast(
        ast,
        context,
        inherited=None,
        diagnostics=diagnostics,
    )
    return _deduplicate(diagnostics)


def validate_source(
    source: Path,
    *,
    clang: Path = PINNED_CLANG,
    projection: c_abi.CAbiProjection | None = None,
) -> bool:
    """Print ABI diagnostics for one source.

    Returns:
        Whether the source is admitted by the ABI-only preflight.

    """
    diagnostics = analyze_source(source, clang=clang, projection=projection)
    for diagnostic in diagnostics:
        _ = sys.stderr.write(f"{diagnostic.render()}\n")
    return not diagnostics


def main() -> int:
    """Validate explicitly named source files against ABI-only v1 rules.

    Returns:
        Zero for admitted input, one for ABI rejections, or two for tool errors.

    """
    arguments = _parse_arguments()
    try:
        projection = c_abi.canonical_projection()
        admitted = True
        for source in arguments.files:
            if not validate_source(
                source,
                clang=arguments.clang,
                projection=projection,
            ):
                admitted = False
    except (c_abi.CAbiValidationError, SourceAnalysisError) as error:
        _ = sys.stderr.write(f"error: {error}\n")
        return 2
    return 0 if admitted else 1


if __name__ == "__main__":
    raise SystemExit(main())
