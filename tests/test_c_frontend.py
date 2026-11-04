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
#   - Collected by the repository Python suite on supported native hosts.
# - Defaults:
#   - Unsupported hosts skip; supported hosts use exact local LLVM inputs.
#

"""End-to-end tests for the exact normalized C frontend."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess as sp  # ruff: ignore[suspicious-subprocess-import]
import sys
from pathlib import Path
from typing import Final, cast

import pytest
from scripts.repository_root import repository_root

from scripts.validate import (
    c_frontend_build,
    c_frontend_build_linux,
    tidy_toolchain,
)

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


def _linux_build_tools_available() -> bool:
    try:
        _ = c_frontend_build_linux.linux_build_tools()
    except c_frontend_build_linux.LinuxFrontendBuildError:
        return False
    return True


def _frontend_available() -> bool:
    artifact_ready = c_frontend_build.EXECUTABLE.is_file()
    windows_ready = (
        c_frontend_build.HOST_PLATFORM_ID == tidy_toolchain.WINDOWS_PLATFORM
    )
    linux_ready = (
        c_frontend_build.HOST_PLATFORM_ID == tidy_toolchain.LINUX_PLATFORM
        and _linux_build_tools_available()
    )
    return artifact_ready or windows_ready or linux_ready


pytestmark = pytest.mark.skipif(
    not _frontend_available(),
    reason="reviewed platform-native Clang frontend is unavailable",
)


def _ensure_native_frontend() -> None:
    if not c_frontend_build.EXECUTABLE.is_file():
        c_frontend_build.build()


def _run_frontend(
    source: Path,
    source_id: str,
    *,
    guest_include: Path = GUEST_INCLUDE,
    timeout: int = 30,
) -> sp.CompletedProcess[str]:
    _ensure_native_frontend()
    command = (
        str(c_frontend_build.EXECUTABLE),
        "--source-id",
        source_id,
        "--resource-dir",
        str(RESOURCE_DIR),
        "--guest-include",
        str(guest_include),
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
        timeout=timeout,
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


def test_file_input_rejects_nonregular_and_oversized_sources(
    tmp_path: Path,
) -> None:
    """Source admission rejects directories and sparse files before Clang."""
    directory = tmp_path / "source-dir"
    directory.mkdir()
    oversized = tmp_path / "oversized.c"
    with oversized.open("wb") as stream:
        stream.truncate(64 * 1024 * 1024 + 1)
    for source in (directory, oversized):
        result = _run_frontend(source, BASIC_SOURCE_ID)
        assert result.returncode == REQUEST_STATUS
        assert not result.stdout
        assert result.stderr == (
            "MALBOLGE-FRONTEND-003 cannot read selected source\n"
        )


@pytest.mark.skipif(sys.platform != "linux", reason="Linux nonblocking open")
def test_writerless_fifo_and_fifo_symlink_never_stall_frontend(
    tmp_path: Path,
) -> None:
    """An unconnected FIFO cannot block the command before source admission."""
    pipe = tmp_path / "source.fifo"
    alias = tmp_path / "alias.c"
    os.mkfifo(pipe)
    alias.symlink_to(pipe)
    for source in (pipe, alias):
        result = _run_frontend(source, BASIC_SOURCE_ID, timeout=3)
        assert result.returncode == REQUEST_STATUS
        assert not result.stdout
        assert result.stderr == (
            "MALBOLGE-FRONTEND-003 cannot read selected source\n"
        )


@pytest.mark.skipif(sys.platform != "linux", reason="Linux regular-file alias")
def test_regular_file_symlink_retains_exact_normalized_artifact(
    tmp_path: Path,
) -> None:
    """Ordinary regular-file aliases retain the original stable semantics."""
    alias = tmp_path / "alias.c"
    alias.symlink_to(BASIC)
    result = _run_frontend(alias, BASIC_SOURCE_ID)
    assert result.returncode == 0, result.stderr
    assert result.stdout == GOLDEN.read_text(encoding="utf-8")


def test_scoped_tags_retain_distinct_semantic_types(tmp_path: Path) -> None:
    """Separate block-scoped tags must not alias file or sibling scopes."""
    source = tmp_path / "scoped-tags.c"
    _ = source.write_text(
        "struct Record { int value; };\n"
        "union Variant { int value; };\n"
        "enum Flag { FLAG_GLOBAL };\n"
        "int left(void) {\n"
        "  struct Record { short value; };\n"
        "  union Variant { short value; };\n"
        "  enum Flag { FLAG_LEFT };\n"
        "  struct Record left_record;\n"
        "  union Variant left_variant;\n"
        "  enum Flag left_flag;\n"
        "  return 0;\n"
        "}\n"
        "int right(void) {\n"
        "  struct Record { long long value; };\n"
        "  union Variant { long long value; };\n"
        "  enum Flag { FLAG_RIGHT };\n"
        "  struct Record right_record;\n"
        "  union Variant right_variant;\n"
        "  enum Flag right_flag;\n"
        "  return 0;\n"
        "}\n",
        encoding="utf-8",
    )
    artifact = _artifact(_run_frontend(source, "fixtures/scoped-tags.c"))
    nodes = cast("list[dict[str, object]]", artifact["nodes"])
    for prefix, name, declaration_kind, suffix in (
        ("struct", "Record", "record-declaration", "record"),
        ("union", "Variant", "record-declaration", "variant"),
        ("enum", "Flag", "enum-declaration", "flag"),
    ):
        declarations = [
            node
            for node in nodes
            if node["kind"] == declaration_kind and node.get("name") == name
        ]
        assert len(declarations) == 3
        types = [node["type"] for node in declarations]
        assert types[0] == f"{prefix}({name})"
        assert len(set(types)) == 3
        for scope, scoped_type in zip(
            ("left", "right"), types[1:], strict=True
        ):
            assert isinstance(scoped_type, str)
            assert scoped_type.startswith(f"{prefix}(@")
            variable = _named_node(artifact, f"{scope}_{suffix}")
            assert variable["type"] == scoped_type


def test_local_tag_forward_declaration_uses_one_canonical_anchor(
    tmp_path: Path,
) -> None:
    """Forward declarations and definitions of one scoped tag stay bound."""
    source = tmp_path / "forward-local-tag.c"
    _ = source.write_text(
        "struct Local { int value; };\n"
        "int use(void) {\n"
        "  struct Local;\n"
        "  struct Local { short value; };\n"
        "  struct Local local;\n"
        "  return 0;\n"
        "}\n",
        encoding="utf-8",
    )
    artifact = _artifact(_run_frontend(source, "fixtures/forward-local-tag.c"))
    nodes = cast("list[dict[str, object]]", artifact["nodes"])
    declarations = [
        node
        for node in nodes
        if node["kind"] == "record-declaration" and node.get("name") == "Local"
    ]
    assert len(declarations) == 3
    assert declarations[0]["type"] == "struct(Local)"
    assert declarations[1]["type"] == declarations[2]["type"]
    scoped_type = declarations[1]["type"]
    assert isinstance(scoped_type, str)
    assert scoped_type.startswith("struct(@")
    assert _named_node(artifact, "local")["type"] == scoped_type


def test_macro_expansion_tags_keep_distinct_canonical_types(
    tmp_path: Path,
) -> None:
    """Multiple tags at one macro callsite are distinct semantic C types."""
    source = tmp_path / "macro-tags.c"
    _ = source.write_text(
        "#define TWO struct { int first; } a; "
        "struct { long long second; } b;\n"
        "TWO\n"
        "#define RECORD(name) struct { int field; } name;\n"
        "#define DOUBLE RECORD(c) RECORD(d)\n"
        "DOUBLE\n"
        "#define UNIONS union { int field; } u; "
        "union { short field; } v;\n"
        "UNIONS\n"
        "#define FLAGS enum { FLAG_E = 1 } e; "
        "enum { FLAG_F = 2 } f;\n"
        "FLAGS\n",
        encoding="utf-8",
    )
    logical_id = "fixtures/macro-tags.c"
    first = _run_frontend(source, logical_id)
    artifact = _artifact(first)
    assert _run_frontend(source, logical_id).stdout == first.stdout
    relocated = tmp_path / "relocated.c"
    _ = relocated.write_bytes(source.read_bytes())
    assert _run_frontend(relocated, logical_id).stdout == first.stdout
    nodes = cast("list[dict[str, object]]", artifact["nodes"])
    for kind, prefix, variable_names in (
        ("record-declaration", "struct", ("a", "b", "c", "d")),
        ("record-declaration", "union", ("u", "v")),
        ("enum-declaration", "enum", ("e", "f")),
    ):
        types = [
            node["type"]
            for node in nodes
            if node["kind"] == kind
            and isinstance(node.get("type"), str)
            and cast("str", node["type"]).startswith(f"{prefix}(")
        ]
        assert len(types) == len(variable_names)
        assert len(set(types)) == len(types)
        for variable_name, tag_type in zip(variable_names, types, strict=True):
            assert isinstance(tag_type, str)
            assert tag_type.startswith(f"{prefix}(@")
            assert _named_node(artifact, variable_name)["type"] == tag_type
        assert [cast("str", value).split(":")[-1] for value in types[:2]] == [
            "1)",
            "2)",
        ]


def test_macro_local_references_match_distinct_declarations(
    tmp_path: Path,
) -> None:
    """One macro callsite can declare same-name locals in separate blocks."""
    source = tmp_path / "macro-locals.c"
    _ = source.write_text(
        "#define TWICE { int x = 1; y += x; } "
        "{ int x = 2; y += x; }\n"
        "int main(void) { int y = 0; TWICE return y; }\n",
        encoding="utf-8",
    )
    first = _run_frontend(source, "fixtures/macro-locals.c")
    artifact = _artifact(first)
    assert _run_frontend(source, "fixtures/macro-locals.c").stdout == first.stdout
    relocated = tmp_path / "relocated.c"
    _ = relocated.write_bytes(source.read_bytes())
    assert _run_frontend(relocated, "fixtures/macro-locals.c").stdout == first.stdout
    nodes = cast("list[dict[str, object]]", artifact["nodes"])
    declarations = [
        node
        for node in nodes
        if node["kind"] == "variable-declaration" and node.get("name") == "x"
    ]
    references = [
        node
        for node in nodes
        if node["kind"] == "declaration-reference-expression"
        and cast("str", node.get("reference", "")).startswith("x@")
    ]
    assert len(declarations) == len(references) == 2
    targets = [cast("str", node.get("reference", "")) for node in declarations]
    assert len(set(targets)) == 2
    assert all(target.startswith("x@") and ":" in target for target in targets)
    assert [node["reference"] for node in references] == targets


def test_header_anonymous_tags_retain_distinct_path_free_types(
    tmp_path: Path,
) -> None:
    """Different header-local anonymous tags stay distinct across relocation."""
    header = (
        "typedef struct { int narrow_value; } Narrow;\n"
        "typedef struct { long long wide_value; } Wide;\n"
        "typedef union { int left; } LeftUnion;\n"
        "typedef union { long long right; } RightUnion;\n"
        "typedef enum { FIRST = 0 } FirstEnum;\n"
        "typedef enum { SECOND = 1 } SecondEnum;\n"
    )
    source = (
        '#include "types.h"\n'
        "Narrow narrow;\n"
        "Narrow another;\n"
        "Wide wide;\n"
        "LeftUnion left_union;\n"
        "RightUnion right_union;\n"
        "FirstEnum first_enum;\n"
        "SecondEnum second_enum;\n"
    )
    outputs = []
    for directory_name in ("one", "two"):
        directory = tmp_path / directory_name
        directory.mkdir()
        _ = (directory / "types.h").write_text(header, encoding="utf-8")
        source_path = directory / "source.c"
        _ = source_path.write_text(source, encoding="utf-8")
        completed = _run_frontend(
            source_path,
            "fixtures/header-anonymous.c",
            guest_include=directory,
        )
        artifact = _artifact(completed)
        narrow = _named_node(artifact, "narrow")["type"]
        another = _named_node(artifact, "another")["type"]
        assert narrow == another
        for tag, names in (
            ("struct", ("narrow", "wide")),
            ("union", ("left_union", "right_union")),
            ("enum", ("first_enum", "second_enum")),
        ):
            first_type = _named_node(artifact, names[0])["type"]
            second_type = _named_node(artifact, names[1])["type"]
            assert first_type != second_type
            for tag_type in (first_type, second_type):
                assert isinstance(tag_type, str)
                assert tag_type.startswith(f"{tag}(external-anonymous:")
        assert str(directory) not in completed.stdout
        outputs.append(completed.stdout)
    assert outputs[0] == outputs[1]


def test_header_member_references_qualify_owning_record(
    tmp_path: Path,
) -> None:
    """Same-name fields in distinct imported records cannot alias."""
    header = (
        "typedef struct { int value; } Narrow;\n"
        "typedef struct { long long value; } Wide;\n"
        "typedef union { int value; } LeftUnion;\n"
        "typedef union { long long value; } RightUnion;\n"
    )
    source = (
        '#include "types.h"\n'
        "Narrow narrow; Wide wide;\n"
        "LeftUnion left_union; RightUnion right_union;\n"
        "int main(void) { return narrow.value + (int)wide.value + "
        "left_union.value + (int)right_union.value; }\n"
    )
    outputs = []
    for root_name in ("first", "second"):
        directory = tmp_path / root_name
        directory.mkdir()
        _ = (directory / "types.h").write_text(header, encoding="utf-8")
        source_path = directory / "source.c"
        _ = source_path.write_text(source, encoding="utf-8")
        completed = _run_frontend(
            source_path,
            "fixtures/header-members.c",
            guest_include=directory,
        )
        artifact = _artifact(completed)
        nodes = cast("list[dict[str, object]]", artifact["nodes"])
        members = [
            cast("str", node["reference"])
            for node in nodes
            if node["kind"] == "member-expression"
        ]
        assert len(members) == 4
        assert len(set(members)) == 4
        assert all(member.startswith("external:value@") for member in members)
        assert all("struct(external-anonymous:" in value for value in members[:2])
        assert all("union(external-anonymous:" in value for value in members[2:])
        assert str(directory) not in completed.stdout
        outputs.append(completed.stdout)
    assert outputs[0] == outputs[1]


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


@pytest.mark.skipif(sys.platform != "linux", reason="Linux /dev/full sink")
def test_failed_stdout_publication_returns_an_error() -> None:
    """Neither version text nor generated JSON can succeed after write failure."""
    _ensure_native_frontend()
    normal_args = (
        "--source-id",
        BASIC_SOURCE_ID,
        "--resource-dir",
        str(RESOURCE_DIR),
        "--guest-include",
        str(GUEST_INCLUDE),
        str(BASIC),
    )
    with Path("/dev/full").open("wb") as sink:
        for arguments in (("--version",), normal_args):
            completed = sp.run(  # ruff: ignore[subprocess-without-shell-equals-true]
                (str(c_frontend_build.EXECUTABLE), *arguments),
                cwd=ROOT,
                check=False,
                stdout=sink,
                stderr=sp.PIPE,
                encoding="utf-8",
                shell=False,
                timeout=10,
            )
            assert completed.returncode == REQUEST_STATUS
            assert completed.stderr == (
                "MALBOLGE-FRONTEND-003 cannot write standard output\n"
            )


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


@pytest.mark.parametrize(
    "declaration",
    [
        "struct __attribute__((packed)) P { char c; int n; };\n",
        "struct __attribute__((aligned(64))) P { char c; int n; };\n",
        (
            "#pragma pack(push, 1)\n"
            "struct P { char c; int n; };\n"
            "#pragma pack(pop)\n"
        ),
        "struct P { _Alignas(32) int n; };\n",
    ],
)
def test_unrepresented_record_layout_attributes_fail_closed(
    tmp_path: Path, declaration: str
) -> None:
    """Clang layout-affecting attributes cannot silently disappear from IR."""
    source = tmp_path / "record-layout.c"
    _ = source.write_text(declaration, encoding="utf-8")
    completed = _run_frontend(source, "fixtures/record-layout.c")
    assert completed.returncode == NORMALIZE_STATUS
    assert not completed.stdout
    assert completed.stderr == (
        "MALBOLGE-FRONTEND-002 unsupported C record layout attributes\n"
    )


@pytest.mark.parametrize(
    "declaration",
    [
        "_Alignas(64) int aligned;\n",
        "typedef int AlignedInt __attribute__((aligned(64)));\n",
    ],
)
def test_unrepresented_value_alignment_fails_closed(
    tmp_path: Path, declaration: str
) -> None:
    """Aligned values and aliases cannot silently normalize to plain i32."""
    source = tmp_path / "aligned-value.c"
    _ = source.write_text(declaration, encoding="utf-8")
    completed = _run_frontend(source, "fixtures/aligned-value.c")
    assert completed.returncode == NORMALIZE_STATUS
    assert not completed.stdout
    assert completed.stderr == (
        "MALBOLGE-FRONTEND-002 unsupported C declaration alignment\n"
    )


def test_imported_aligned_typedef_fails_closed(tmp_path: Path) -> None:
    """Imported aligned typedefs also carry unrepresented layout semantics."""
    _ = (tmp_path / "types.h").write_text(
        "typedef int AlignedInt __attribute__((aligned(64)));\n",
        encoding="utf-8",
    )
    source = tmp_path / "source.c"
    _ = source.write_text(
        '#include "types.h"\nAlignedInt imported;\n', encoding="utf-8"
    )
    completed = _run_frontend(
        source,
        "fixtures/aligned-alias.c",
        guest_include=tmp_path,
    )
    assert completed.returncode == NORMALIZE_STATUS
    assert not completed.stdout
    assert completed.stderr == (
        "MALBOLGE-FRONTEND-002 unsupported C declaration alignment\n"
    )


@pytest.mark.parametrize(
    "declaration",
    [
        "AlignedInt *pointer;\n",
        "AlignedInt **double_pointer;\n",
        "void consume(AlignedInt *value) {}\n",
        "void (*callback)(AlignedInt *value);\n",
        "const AlignedInt *qualified_pointer;\n",
        "typedef AlignedInt *AlignedPointer; AlignedPointer nested;\n",
    ],
)
def test_imported_nested_aligned_typedef_fails_closed(
    tmp_path: Path, declaration: str
) -> None:
    """Nested header typedef alignment must survive sugared type traversal."""
    _ = (tmp_path / "types.h").write_text(
        "typedef int AlignedInt __attribute__((aligned(64)));\n",
        encoding="utf-8",
    )
    source = tmp_path / "source.c"
    _ = source.write_text(
        '#include "types.h"\n' + declaration, encoding="utf-8"
    )
    completed = _run_frontend(
        source,
        "fixtures/nested-aligned-alias.c",
        guest_include=tmp_path,
    )
    assert completed.returncode == NORMALIZE_STATUS
    assert not completed.stdout
    assert completed.stderr == (
        "MALBOLGE-FRONTEND-002 unsupported C declaration alignment\n"
    )


def test_imported_plain_typedef_pointer_preserves_canonical_type(
    tmp_path: Path,
) -> None:
    """The nested-layout guard must not reject ordinary private typedefs."""
    _ = (tmp_path / "types.h").write_text(
        "typedef int PlainInt;\n",
        encoding="utf-8",
    )
    source = tmp_path / "source.c"
    _ = source.write_text(
        '#include "types.h"\nPlainInt **pointer;\n', encoding="utf-8"
    )
    artifact = _artifact(
        _run_frontend(
            source,
            "fixtures/plain-alias.c",
            guest_include=tmp_path,
        )
    )
    assert _named_node(artifact, "pointer")["type"] == "ptr(ptr(i32))"


def test_imported_packed_record_type_fails_closed(tmp_path: Path) -> None:
    """Header-defined packing still affects main-source value layout."""
    _ = (tmp_path / "types.h").write_text(
        "typedef struct __attribute__((packed)) { char c; int n; } P;\n",
        encoding="utf-8",
    )
    source = tmp_path / "source.c"
    _ = source.write_text('#include "types.h"\nP imported;\n', encoding="utf-8")
    completed = _run_frontend(
        source,
        "fixtures/packed-import.c",
        guest_include=tmp_path,
    )
    assert completed.returncode == NORMALIZE_STATUS
    assert not completed.stdout
    assert completed.stderr == (
        "MALBOLGE-FRONTEND-002 unsupported C record layout attributes\n"
    )


def test_default_enum_outside_abi_domain_fails_closed() -> None:
    """Default enum inference follows malbolge-c32-v1, not Clang widening."""
    completed = _run_frontend(ENUM_TOO_WIDE, ENUM_TOO_WIDE_SOURCE_ID)
    assert completed.returncode == NORMALIZE_STATUS
    assert not completed.stdout
    assert completed.stderr.strip() == ENUM_DOMAIN_DIAGNOSTIC


def test_malformed_private_header_diagnostics_are_path_independent(
    tmp_path: Path,
) -> None:
    """Clang must never disclose native include roots on a parse failure."""
    results = []
    for root_name in ("first", "second"):
        directory = tmp_path / root_name
        directory.mkdir()
        _ = (directory / "private.h").write_text(
            "int invalid(void { return 1; }\n", encoding="utf-8"
        )
        source = directory / "source.c"
        _ = source.write_text('#include "private.h"\n', encoding="utf-8")
        completed = _run_frontend(
            source,
            "fixtures/private-header.c",
            guest_include=directory,
        )
        assert completed.returncode == PARSE_STATUS
        assert not completed.stdout
        assert "expected ')'" in completed.stderr
        assert "MALBOLGE-FRONTEND-004 Clang parse failed" in completed.stderr
        assert "fixtures/private-header.c" in completed.stderr
        assert str(directory) not in completed.stderr
        results.append(completed.stderr)
    assert results[0] == results[1]


def test_malformed_source_fails_under_logical_source_identity() -> None:
    """Syntax errors fail closed without exposing the physical input path."""
    completed = _run_frontend(MALFORMED, MALFORMED_SOURCE_ID)
    assert completed.returncode == PARSE_STATUS
    assert not completed.stdout
    assert PARSE_DIAGNOSTIC in completed.stderr
    assert "error:" in completed.stderr
    assert "expected" in completed.stderr
    assert "MALBOLGE-FRONTEND-004 Clang parse failed" in completed.stderr
    assert str(MALFORMED) not in completed.stderr


def test_escaping_source_identity_rejects_before_clang() -> None:
    """Portable source identity cannot contain path traversal or host syntax."""
    completed = _run_frontend(BASIC, INVALID_SOURCE_ID)
    assert completed.returncode == REQUEST_STATUS
    assert not completed.stdout
    assert completed.stderr == REQUEST_DIAGNOSTIC
