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
#   - Source-located admission checks for the version-one guest libc surface.
# - Must-Not:
#   - Guess calls with regex, resolve host libraries, or reject user functions.
# - Allows:
#   - Inputs: explicit guest C units, canonical libc data, and pinned Clang AST.
#   - Outputs: deterministic unavailable or forbidden routine diagnostics.
#   - Side effects: pinned Clang execution and tracked source reads only.
# - Split-When:
#   - Split when another library schema needs independent source diagnostics.
# - Merge-When:
#   - Merge when another preflight owns this exact guest-library admission rule.
# - Summary:
#   - Rejects unavailable and host-dependent libc routine uses before lowering.
# - Description:
#   - Uses Clang declaration references so user-defined unrelated calls survive.
# - Usage:
#   - Runs after ABI preflight and before clang-tidy for selected guest C units.
# - Defaults:
#   - Malformed AST evidence or wrong tool identity fails closed.
#

"""Source-level admission checks for malbolge-libc-v1 routine uses."""

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
from scripts.validate import c_libc

ROOT = repository_root(Path(__file__))
PINNED_LLVM_VERSION = "22.1.8"
PINNED_CLANG = ROOT / ".dependencies/llvm/22.1.8/bin/clang.exe"
DIAGNOSTIC_UNAVAILABLE = "MALBOLGE-LIBC-001"
DIAGNOSTIC_FORBIDDEN = "MALBOLGE-LIBC-002"
AST_DECL_REF = "DeclRefExpr"
AST_FUNCTION_DECL = "FunctionDecl"
AST_COMPOUND_STMT = "CompoundStmt"


type JsonScalar = bool | int | float | str | None
type JsonValue = JsonScalar | list[JsonValue] | dict[str, JsonValue]
type JsonObject = dict[str, JsonValue]


@dataclass(frozen=True, slots=True)
class LibcDiagnostic:
    """One deterministic source-located guest libc rejection."""

    code: str
    column: int
    line: int
    message: str
    path: Path

    def render(self) -> str:
        """Render a stable Clang-style diagnostic line.

        Returns:
            Source-located error text.

        """
        return (
            f"{self.path}:{self.line}:{self.column}: error: "
            f"{self.code} {self.message}"
        )


class LibcSourceError(RuntimeError):
    """Pinned Clang or guest-libc source evidence is malformed."""


class _Arguments(argparse.Namespace):
    files: list[Path]
    clang: Path

    def __init__(self) -> None:
        """Initialize typed defaults for argparse mutation."""
        super().__init__()
        self.files = []
        self.clang = PINNED_CLANG


@dataclass(frozen=True, slots=True)
class _AstConfig:
    clang: Path
    abi: c_abi.CAbiProjection
    libc: c_libc.CLibcProjection


@dataclass(frozen=True, slots=True)
class _AnalysisContext:
    source: Path
    source_bytes: bytes
    libc: c_libc.CLibcProjection
    local_function_ids: frozenset[str]


def _fail(message: str) -> Never:
    raise LibcSourceError(message)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Check named guest C files against malbolge-libc-v1.",
    )
    _ = parser.add_argument("files", nargs="+", type=Path, metavar="FILE")
    _ = parser.add_argument("--clang", type=Path, default=PINNED_CLANG)
    return parser


def _parse_arguments() -> _Arguments:
    arguments = _Arguments()
    _ = _parser().parse_args(namespace=arguments)
    return arguments


def _clang_identity(clang: Path) -> str:
    try:
        # jig-ignore-next-line: indivisible reviewed Ruff rule identifier
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


def _ast_command(source: Path, config: _AstConfig) -> list[str]:
    return [
        str(config.clang),
        f"--target={config.abi.clang_target}",
        "-std=c23",
        "-ffreestanding",
        "-fno-builtin",
        "-pedantic-errors",
        "-Werror=implicit-function-declaration",
        f"-I{config.libc.include_root}",
        "-fsyntax-only",
        "-Xclang",
        "-ast-dump=json",
        str(source),
    ]


def _require_clang(clang: Path) -> None:
    if not clang.is_file():
        _fail(f"pinned Clang not found: {clang}")
    expected = f"clang version {PINNED_LLVM_VERSION}"
    if expected not in _clang_identity(clang):
        _fail(f"Clang must report {expected}: {clang}")


def _parse_ast(text: str, source: Path) -> JsonObject:
    try:
        parsed = cast("object", json.loads(text))
    except json.JSONDecodeError as error:
        _fail(f"invalid Clang AST JSON for {source}: {error}")
    if not isinstance(parsed, dict):
        _fail(f"Clang AST root must be an object for {source}")
    return cast("JsonObject", parsed)


def _run_ast(source: Path, config: _AstConfig) -> JsonObject:
    _require_clang(config.clang)
    try:
        # jig-ignore-next-line: indivisible reviewed Ruff rule identifier
        completed = sp.run(  # ruff: ignore[subprocess-without-shell-equals-true]
            _ast_command(source, config),
            cwd=ROOT,
            check=False,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            shell=False,
        )
    except OSError as error:
        _fail(f"failed to execute Clang AST parse {config.clang}: {error}")
    if completed.returncode != 0:
        detail = completed.stderr.strip()
        _fail(detail or f"Clang AST parse failed for {source}")
    return _parse_ast(completed.stdout, source)


def _range_begin(node: JsonObject) -> JsonObject | None:
    raw_range = node.get("range")
    if not isinstance(raw_range, dict):
        return None
    begin = cast("JsonObject", raw_range).get("begin")
    return cast("JsonObject", begin) if isinstance(begin, dict) else None


def _location_candidate(node: JsonObject) -> JsonObject | None:
    location = node.get("loc")
    if isinstance(location, dict):
        return cast("JsonObject", location)
    return _range_begin(node)


def _nonempty_string(value: JsonValue | None) -> str | None:
    return value if isinstance(value, str) and value else None


def _reference_identity(node: JsonObject) -> tuple[str, str] | None:
    result: tuple[str, str] | None = None
    referenced = node.get("referencedDecl")
    if node.get("kind") == AST_DECL_REF and isinstance(referenced, dict):
        declaration = cast("JsonObject", referenced)
        name = _nonempty_string(declaration.get("name"))
        identifier = _nonempty_string(declaration.get("id"))
        is_function = declaration.get("kind") == AST_FUNCTION_DECL
        if is_function and name is not None and identifier is not None:
            result = (name, identifier)
    return result


def _source_offset(
    node: JsonObject,
    name: str,
    source_bytes: bytes,
) -> int | None:
    result: int | None = None
    candidate = _location_candidate(node)
    raw_offset = None if candidate is None else candidate.get("offset")
    if type(raw_offset) is int:
        offset = raw_offset
        spelling = name.encode("utf-8")
        within_source = 0 <= offset <= len(source_bytes) - len(spelling)
        actual = source_bytes[offset : offset + len(spelling)]
        if within_source and actual == spelling:
            result = offset
    return result


def _has_compound_body(inner: JsonValue | None) -> bool:
    return isinstance(inner, list) and any(
        isinstance(item, dict) and item.get("kind") == AST_COMPOUND_STMT
        for item in inner
    )


def _local_definition_id(
    node: JsonObject,
    source_bytes: bytes,
) -> str | None:
    result: str | None = None
    name = _nonempty_string(node.get("name"))
    identifier = _nonempty_string(node.get("id"))
    if name is None or identifier is None:
        return None
    is_function = node.get("kind") == AST_FUNCTION_DECL
    has_body = _has_compound_body(node.get("inner"))
    source_local = _source_offset(node, name, source_bytes) is not None
    if is_function and has_body and source_local:
        result = identifier
    return result


def _collect_definition_items(
    values: list[JsonValue],
    source_bytes: bytes,
    result: set[str],
) -> None:
    for item in values:
        _collect_local_definition_ids(item, source_bytes, result)


def _collect_local_definition_ids(
    value: JsonValue,
    source_bytes: bytes,
    result: set[str],
) -> None:
    if isinstance(value, list):
        _collect_definition_items(value, source_bytes, result)
        return
    if not isinstance(value, dict):
        return
    node = cast("JsonObject", value)
    identifier = _local_definition_id(node, source_bytes)
    if identifier is not None:
        result.add(identifier)
    inner = node.get("inner")
    if isinstance(inner, (dict, list)):
        _collect_local_definition_ids(
            cast("JsonValue", inner),
            source_bytes,
            result,
        )


def _local_definition_ids(
    ast: JsonObject,
    source_bytes: bytes,
) -> frozenset[str]:
    result: set[str] = set()
    _collect_local_definition_ids(ast, source_bytes, result)
    return frozenset(result)


def _line_column(source_bytes: bytes, offset: int) -> tuple[int, int]:
    line = source_bytes.count(b"\n", 0, offset) + 1
    previous = source_bytes.rfind(b"\n", 0, offset)
    column = offset + 1 if previous < 0 else offset - previous
    return line, column


def _routine_rejection(
    name: str,
    libc: c_libc.CLibcProjection,
) -> tuple[str, str] | None:
    result: tuple[str, str] | None = None
    if name in libc.unavailable_routines:
        message = (
            f"{name} is contracted by {libc.libc_id} but unavailable until "
            "guest runtime implementation"
        )
        result = (DIAGNOSTIC_UNAVAILABLE, message)
    elif name in libc.forbidden_routines:
        message = (
            f"{name} requires host-dependent semantics forbidden by "
            f"{libc.libc_id}"
        )
        result = (DIAGNOSTIC_FORBIDDEN, message)
    return result


def _diagnostic_for_reference(
    node: JsonObject,
    context: _AnalysisContext,
) -> LibcDiagnostic | None:
    result: LibcDiagnostic | None = None
    identity = _reference_identity(node)
    name = None if identity is None else identity[0]
    is_local = (
        identity is not None and identity[1] in context.local_function_ids
    )
    rejection = (
        None
        if name is None or is_local
        else _routine_rejection(name, context.libc)
    )
    offset = None if name is None else _source_offset(
        node, name, context.source_bytes
    )
    if rejection is not None and offset is not None:
        code, message = rejection
        line, column = _line_column(context.source_bytes, offset)
        result = LibcDiagnostic(
            code=code,
            column=column,
            line=line,
            message=message,
            path=context.source,
        )
    return result


def _walk_items(
    values: list[JsonValue],
    context: _AnalysisContext,
    diagnostics: list[LibcDiagnostic],
) -> None:
    for item in values:
        _walk(item, context, diagnostics)


def _walk(
    value: JsonValue,
    context: _AnalysisContext,
    diagnostics: list[LibcDiagnostic],
) -> None:
    if isinstance(value, list):
        _walk_items(value, context, diagnostics)
        return
    if not isinstance(value, dict):
        return
    node = cast("JsonObject", value)
    diagnostic = _diagnostic_for_reference(node, context)
    if diagnostic is not None:
        diagnostics.append(diagnostic)
    inner = node.get("inner")
    if isinstance(inner, (dict, list)):
        _walk(cast("JsonValue", inner), context, diagnostics)


def _deduplicate(
    diagnostics: list[LibcDiagnostic],
) -> tuple[LibcDiagnostic, ...]:
    unique = {
        (item.code, item.path, item.line, item.column, item.message): item
        for item in diagnostics
    }
    return tuple(
        sorted(
            unique.values(),
            key=lambda item: (
                item.path.as_posix(),
                item.line,
                item.column,
                item.code,
            ),
        )
    )


def analyze_source(
    source: Path,
    *,
    clang: Path = PINNED_CLANG,
    abi: c_abi.CAbiProjection | None = None,
    libc: c_libc.CLibcProjection | None = None,
) -> tuple[LibcDiagnostic, ...]:
    """Analyze one explicit source against guest-libc routine availability.

    Returns:
        Stable source-located library diagnostics.

    """
    resolved = source.resolve()
    active_abi = abi or c_abi.canonical_projection()
    active_libc = libc or c_libc.canonical_projection()
    try:
        source_bytes = resolved.read_bytes()
        _ = source_bytes.decode("utf-8")
    except UnicodeDecodeError as error:
        _fail(f"invalid guest-C UTF-8 in {resolved}: {error}")
    except OSError as error:
        _fail(f"failed to read guest C source {resolved}: {error}")
    config = _AstConfig(
        clang=clang.resolve(),
        abi=active_abi,
        libc=active_libc,
    )
    ast = _run_ast(resolved, config)
    context = _AnalysisContext(
        source=resolved,
        source_bytes=source_bytes,
        libc=active_libc,
        local_function_ids=_local_definition_ids(ast, source_bytes),
    )
    diagnostics: list[LibcDiagnostic] = []
    _walk(ast, context, diagnostics)
    return _deduplicate(diagnostics)


def validate_source(
    source: Path,
    *,
    clang: Path = PINNED_CLANG,
    abi: c_abi.CAbiProjection | None = None,
    libc: c_libc.CLibcProjection | None = None,
) -> bool:
    """Print libc diagnostics for one source.

    Returns:
        Whether the source is admitted by the current guest libc contract.

    """
    diagnostics = analyze_source(source, clang=clang, abi=abi, libc=libc)
    for diagnostic in diagnostics:
        _ = sys.stderr.write(diagnostic.render() + chr(10))
    return not diagnostics


def main() -> int:
    """Validate explicitly named source files against malbolge-libc-v1.

    Returns:
        Zero for admitted sources, one for libc rejection, or two for errors.

    """
    arguments = _parse_arguments()
    try:
        abi = c_abi.canonical_projection()
        libc = c_libc.canonical_projection()
        results = tuple(
            validate_source(
                source,
                clang=arguments.clang,
                abi=abi,
                libc=libc,
            )
            for source in arguments.files
        )
        admitted = all(results)
    except (
        c_abi.CAbiValidationError,
        c_libc.CLibcValidationError,
        LibcSourceError,
    ) as error:
        _ = sys.stderr.write(f"error: {error}\n")
        return 2
    return 0 if admitted else 1


if __name__ == "__main__":
    raise SystemExit(main())
