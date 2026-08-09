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
#   - End-to-end evidence for the normalized pinned-Clang C frontend boundary.
# - Must-Not:
#   - Treat raw Clang AST dumps or physical source paths as durable artifacts.
# - Allows:
#   - Inputs: tracked C fixtures, frontend contract, and exact native build.
#   - Outputs: golden, relocation, semantic, and fail-closed assertions.
#   - Side effects: ignored native build state and pytest temporary files only.
# - Split-When:
#   - Multi-translation-unit frontend evidence gains independent lifecycle.
# - Merge-When:
#   - Another suite owns this exact source-to-normalized-artifact contract.
# - Summary:
#   - Locks deterministic Clang semantic normalization before portable IR.
# - Description:
#   - Proves source IDs, hashes, locations, constants, types, and failures.
# - Usage:
#   - Collected by the repository Python test suite on Windows.
# - Defaults:
#   - Other hosts skip because the reviewed LLVM development asset is Windows.
#

"""End-to-end tests for the exact normalized C frontend."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess as sp  # ruff: ignore[suspicious-subprocess-import]
from typing import Final
from typing import cast

import pytest
from scripts.repository_root import repository_root
from scripts.validate import c_frontend_build

ROOT: Final = repository_root(Path(__file__))
FIXTURES: Final = ROOT / "tests" / "compiler" / "c-frontend"
BASIC: Final = FIXTURES / "accepted" / "basic_semantics.c"
IR_RETURN: Final = FIXTURES / "accepted" / "ir_return_constant.c"
HEADER: Final = FIXTURES / "accepted" / "header_reference.c"
DECLARATIONS: Final = FIXTURES / "accepted" / "declaration_semantics.c"
BIT_INT: Final = FIXTURES / "rejected" / "unsupported_bit_int.c"
ENUM_TOO_WIDE: Final = FIXTURES / "rejected" / "enum_domain_too_wide.c"
MALFORMED: Final = FIXTURES / "rejected" / "malformed.c"
GOLDEN: Final = FIXTURES / "golden" / "basic_semantics.json"
IR_RETURN_GOLDEN: Final = FIXTURES / "golden" / "ir_return_constant.json"
CONTRACT: Final = (
    ROOT
    / "src"
    / "compiler"
    / "c-frontend"
    / "contract"
    / "frontend-v1.json"
)
RESOURCE_DIR: Final = (
    ROOT / ".dependencies" / "llvm" / "22.1.8" / "lib" / "clang" / "22"
)
GUEST_INCLUDE: Final = (
    ROOT / "src" / "runtime" / "guest-c-library" / "contract" / "include"
)
WINDOWS_OS_NAME: Final = "nt"
ARTIFACT_ID: Final = "malbolge-c-frontend-v1"
LLVM_VERSION: Final = "22.1.8"
CLANG_TARGET: Final = "wasm32-unknown-unknown"
ABI_ID: Final = "malbolge-c32-v1"
TARGET_PROFILE: Final = "malbolge-2026"
BASIC_SOURCE_ID: Final = "fixtures/basic.c"
IR_RETURN_SOURCE_ID: Final = "fixtures/ir-return.c"
HEADER_SOURCE_ID: Final = "fixtures/header.c"
DECLARATION_SOURCE_ID: Final = "fixtures/declarations.c"
UNSUPPORTED_SOURCE_ID: Final = "fixtures/unsupported.c"
ENUM_TOO_WIDE_SOURCE_ID: Final = "fixtures/enum-too-wide.c"
MALFORMED_SOURCE_ID: Final = "fixtures/malformed.c"
INVALID_SOURCE_ID: Final = "../escape.c"
COUNT_NAME: Final = "COUNT"
COUNT_VALUE: Final = "7"
IR_RETURN_VALUE: Final = "7"
IR_RETURN_TYPE: Final = "i32"
SIZEOF_OPERATION: Final = "sizeof"
WORD_SIZE: Final = "4"
PAIR_TYPE: Final = "struct(Pair)"
EXTERNAL_MEMCPY: Final = "external:memcpy"
NORMALIZE_STATUS: Final = 4
PARSE_STATUS: Final = 3
REQUEST_STATUS: Final = 2
UNSUPPORTED_DIAGNOSTIC: Final = (
    "MALBOLGE-FRONTEND-002 unsupported normalized type BitInt "
    "(clang-class=BitInt)"
)
ENUM_DOMAIN_DIAGNOSTIC: Final = (
    "MALBOLGE-FRONTEND-002 enum value domain exceeds malbolge-c32-v1"
)
PARSE_DIAGNOSTIC: Final = (
    "MALBOLGE-FRONTEND-004 Clang parse failed for fixtures/malformed.c"
)
REQUEST_DIAGNOSTIC: Final = "MALBOLGE-FRONTEND-003 invalid frontend request\n"
EXPECTED_VERSION: Final = "malbolge-c-frontend 1 LLVM 22.1.8\n"
EXPECTED_FAILURE_CODES: Final = [
    "MALBOLGE-FRONTEND-001",
    "MALBOLGE-FRONTEND-002",
    "MALBOLGE-FRONTEND-003",
    "MALBOLGE-FRONTEND-004",
]
HOST_PATH_TOKENS: Final = (".dependencies", "src/runtime/guest-c-library")
DECLARATION_FIELDS: Final = (
    "definition",
    "enum_fixed",
    "enum_underlying",
    "inline_specified",
    "linkage",
    "storage_class",
    "storage_duration",
)
EXPECTED_FIXED_ENUM: Final = {
    "definition": "definition",
    "enum_fixed": True,
    "enum_underlying": "u16",
}
EXPECTED_IMPORTED: Final = {
    "definition": "declaration",
    "linkage": "external",
    "storage_class": "extern",
    "storage_duration": "static",
}
EXPECTED_TENTATIVE: Final = {
    "definition": "tentative-definition",
    "linkage": "external",
    "storage_class": "none",
    "storage_duration": "static",
}
EXPECTED_INTERNAL: Final = {
    "definition": "definition",
    "linkage": "internal",
    "storage_class": "static",
    "storage_duration": "static",
}
EXPECTED_THREAD: Final = {
    "definition": "tentative-definition",
    "linkage": "external",
    "storage_class": "none",
    "storage_duration": "thread",
}
EXPECTED_DECLARED_FUNCTION: Final = {
    "definition": "declaration",
    "inline_specified": False,
    "linkage": "external",
    "storage_class": "extern",
}
EXPECTED_HELPER_FUNCTION: Final = {
    "definition": "definition",
    "inline_specified": True,
    "linkage": "internal",
    "storage_class": "static",
}
EXPECTED_REGISTER_PARAMETER: Final = {
    "linkage": "none",
    "storage_class": "register",
    "storage_duration": "automatic",
}
ENUM_DECLARATION_KIND: Final = "enum-declaration"
PARAMETER_DECLARATION_KIND: Final = "parameter-declaration"
REGISTER_STORAGE_CLASS: Final = "register"
DEFAULT_ENUM_UNDERLYING: Final = "i32"
EXPECTED_NAMED_DECLARATIONS: Final = (
    ("Fixed", EXPECTED_FIXED_ENUM),
    ("imported", EXPECTED_IMPORTED),
    ("tentative", EXPECTED_TENTATIVE),
    ("internal_value", EXPECTED_INTERNAL),
    ("thread_value", EXPECTED_THREAD),
    ("declared", EXPECTED_DECLARED_FUNCTION),
    ("helper", EXPECTED_HELPER_FUNCTION),
)
EXPECTED_CONTRACT_KEYS: Final = frozenset(
    {
        "schema_version",
        "artifact_id",
        "clang_version",
        "clang_target",
        "language",
        "abi_id",
        "target_profile",
        "source_identity",
        "source_digest",
        "location_unit",
        "traversal",
        "node_fields",
        "declaration_kinds",
        "statement_kinds",
        "type_grammar",
        "failure_codes",
        "binary_operations",
        "unary_operations",
        "cast_operations",
        "unary_type_traits",
        "reference_encoding",
        "literal_encoding",
        "declaration_semantics",
    }
)

pytestmark = pytest.mark.skipif(
    os.name != WINDOWS_OS_NAME,
    reason="reviewed Clang frontend development kit is Windows x86-64",
)


def _ensure_native_frontend() -> None:
    if not c_frontend_build.EXECUTABLE.is_file():
        c_frontend_build.build()


def _run_frontend(source: Path, source_id: str) -> sp.CompletedProcess[str]:
    _ensure_native_frontend()
    command = (
        str(c_frontend_build.EXECUTABLE),
        "--source-id",
        source_id,
        "--resource-dir",
        str(RESOURCE_DIR),
        "--guest-include",
        str(GUEST_INCLUDE),
        str(source),
    )
    return sp.run(  # ruff: ignore[subprocess-without-shell-equals-true]
        command,
        cwd=ROOT,
        check=False,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        shell=False,
        timeout=30,
    )


def _artifact(completed: sp.CompletedProcess[str]) -> dict[str, object]:
    assert completed.returncode == 0, completed.stderr
    parsed = cast("object", json.loads(completed.stdout))
    assert isinstance(parsed, dict)
    return cast("dict[str, object]", parsed)


def _named_node(artifact: dict[str, object], name: str) -> dict[str, object]:
    nodes = cast("list[dict[str, object]]", artifact["nodes"])
    matches = [node for node in nodes if node.get("name") == name]
    assert len(matches) == 1
    return matches[0]


def _declaration_projection(node: dict[str, object]) -> dict[str, object]:
    return {field: node[field] for field in DECLARATION_FIELDS if field in node}


def test_frontend_contract_is_closed_and_versioned() -> None:
    """Tracked artifact authority pins exact Clang/profile semantics."""
    document = cast("dict[str, object]", json.loads(CONTRACT.read_text()))
    assert frozenset(document) == EXPECTED_CONTRACT_KEYS
    assert document["schema_version"] == 1
    assert document["artifact_id"] == ARTIFACT_ID
    assert document["clang_version"] == LLVM_VERSION
    assert document["clang_target"] == CLANG_TARGET
    assert document["abi_id"] == ABI_ID
    assert document["target_profile"] == TARGET_PROFILE
    assert document["failure_codes"] == EXPECTED_FAILURE_CODES


def test_frontend_version_is_exact() -> None:
    """Built product identifies its versioned frontend and LLVM dependency."""
    _ensure_native_frontend()
    completed = sp.run(  # ruff: ignore[subprocess-without-shell-equals-true]
        (str(c_frontend_build.EXECUTABLE), "--version"),
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        shell=False,
        timeout=10,
    )
    assert completed.returncode == 0
    assert completed.stdout == EXPECTED_VERSION


def test_basic_semantics_match_exact_golden() -> None:
    """Pinned semantics normalize to the checked-in deterministic bytes."""
    completed = _run_frontend(BASIC, BASIC_SOURCE_ID)
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout == GOLDEN.read_text(encoding="utf-8")
    artifact = _artifact(completed)
    source = cast("dict[str, object]", artifact["source"])
    expected_hash = hashlib.sha256(BASIC.read_bytes()).hexdigest()
    assert source == {"id": BASIC_SOURCE_ID, "sha256": expected_hash}
    nodes = cast("list[dict[str, object]]", artifact["nodes"])
    assert any(
        node.get("name") == COUNT_NAME
        and node.get("constant_integer") == COUNT_VALUE
        for node in nodes
    )
    assert any(
        node.get("operation") == SIZEOF_OPERATION
        and node.get("constant_integer") == WORD_SIZE
        for node in nodes
    )
    assert any(node.get("type") == PAIR_TYPE for node in nodes)
    enum_nodes = [
        node for node in nodes if node.get("kind") == ENUM_DECLARATION_KIND
    ]
    assert len(enum_nodes) == 1
    assert enum_nodes[0].get("enum_underlying") == DEFAULT_ENUM_UNDERLYING


def test_ir_return_constant_matches_exact_frontend_golden() -> None:
    """Typed-IR lowering fixture is anchored to exact pinned frontend output."""
    completed = _run_frontend(IR_RETURN, IR_RETURN_SOURCE_ID)
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout == IR_RETURN_GOLDEN.read_text(encoding="utf-8")
    artifact = _artifact(completed)
    source = cast("dict[str, object]", artifact["source"])
    expected_hash = hashlib.sha256(IR_RETURN.read_bytes()).hexdigest()
    assert source == {"id": IR_RETURN_SOURCE_ID, "sha256": expected_hash}
    nodes = cast("list[dict[str, object]]", artifact["nodes"])
    assert [node.get("kind") for node in nodes] == [
        "function-declaration",
        "compound-statement",
        "return-statement",
        "integer-literal",
    ]
    assert nodes[-1].get("type") == IR_RETURN_TYPE
    assert nodes[-1].get("constant_integer") == IR_RETURN_VALUE


def test_physical_source_relocation_does_not_change_artifact(
    tmp_path: Path,
) -> None:
    """Only logical source identity and source bytes enter normalized output."""
    left = tmp_path / "one" / "input.c"
    right = tmp_path / "other" / "tree" / "input.c"
    left.parent.mkdir(parents=True)
    right.parent.mkdir(parents=True)
    content = BASIC.read_bytes()
    _ = left.write_bytes(content)
    _ = right.write_bytes(content)
    left_result = _run_frontend(left, BASIC_SOURCE_ID)
    right_result = _run_frontend(right, BASIC_SOURCE_ID)
    assert left_result.returncode == 0, left_result.stderr
    assert right_result.returncode == 0, right_result.stderr
    assert left_result.stdout == right_result.stdout
    assert str(left.parent) not in left_result.stdout
    assert str(right.parent) not in right_result.stdout


def test_declaration_semantics_preserve_abi_relevant_facts() -> None:
    """Preserve declaration storage, linkage, definition, and enum ABI."""
    artifact = _artifact(_run_frontend(DECLARATIONS, DECLARATION_SOURCE_ID))
    for name, expected in EXPECTED_NAMED_DECLARATIONS:
        observed = _declaration_projection(_named_node(artifact, name))
        assert observed == expected
    nodes = cast("list[dict[str, object]]", artifact["nodes"])
    register_parameters = [
        node
        for node in nodes
        if node.get("kind") == PARAMETER_DECLARATION_KIND
        and node.get("storage_class") == REGISTER_STORAGE_CLASS
    ]
    assert len(register_parameters) == 1
    observed_parameter = _declaration_projection(register_parameters[0])
    assert observed_parameter == EXPECTED_REGISTER_PARAMETER


def test_header_declarations_do_not_leak_host_paths() -> None:
    """Included declarations retain semantic names without physical headers."""
    completed = _run_frontend(HEADER, HEADER_SOURCE_ID)
    artifact = _artifact(completed)
    nodes = cast("list[dict[str, object]]", artifact["nodes"])
    references = {
        cast("str", node["reference"])
        for node in nodes
        if isinstance(node.get("reference"), str)
    }
    assert EXTERNAL_MEMCPY in references
    assert str(ROOT) not in completed.stdout
    assert all(token not in completed.stdout for token in HOST_PATH_TOKENS)


def test_unsupported_type_fails_at_normalization_boundary() -> None:
    """Clang-accepted unsupported types fail with a stable diagnostic."""
    completed = _run_frontend(BIT_INT, UNSUPPORTED_SOURCE_ID)
    assert completed.returncode == NORMALIZE_STATUS
    assert not completed.stdout
    assert completed.stderr.strip() == UNSUPPORTED_DIAGNOSTIC


def test_default_enum_outside_abi_domain_fails_closed() -> None:
    """Default enum inference follows malbolge-c32-v1, not Clang widening."""
    completed = _run_frontend(ENUM_TOO_WIDE, ENUM_TOO_WIDE_SOURCE_ID)
    assert completed.returncode == NORMALIZE_STATUS
    assert not completed.stdout
    assert completed.stderr.strip() == ENUM_DOMAIN_DIAGNOSTIC


def test_malformed_source_fails_under_logical_source_identity() -> None:
    """Syntax errors fail closed without exposing the physical input path."""
    completed = _run_frontend(MALFORMED, MALFORMED_SOURCE_ID)
    assert completed.returncode == PARSE_STATUS
    assert not completed.stdout
    assert PARSE_DIAGNOSTIC in completed.stderr
    assert f"{MALFORMED_SOURCE_ID}:" in completed.stderr
    assert str(MALFORMED) not in completed.stderr


def test_escaping_source_identity_rejects_before_clang() -> None:
    """Portable source identity cannot contain path traversal or host syntax."""
    completed = _run_frontend(BASIC, INVALID_SOURCE_ID)
    assert completed.returncode == REQUEST_STATUS
    assert not completed.stdout
    assert completed.stderr == REQUEST_DIAGNOSTIC
