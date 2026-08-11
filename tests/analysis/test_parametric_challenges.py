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
#   - Deterministic parametric compiler challenge test evidence.
# - Must-Not:
#   - Mutate repository state or substitute host semantics for guest authority.
# - Allows:
#   - Inputs: generated challenge identities, artifacts, and test-local paths.
#   - Outputs: deterministic assertions over identity, admission, and
#     publication.
#   - Side effects: test-local files, compiler subprocesses, and symlink probes.
# - Split-When:
#   - Another challenge family needs independent fixtures or oracle evidence.
# - Merge-When:
#   - Generator conformance owns these exact assertions directly.
# - Summary:
#   - Parametric challenge generator conformance evidence.
# - Description:
#   - Locks deterministic generation, canonical profile binding, and safe
#     publication.
# - Usage:
#   - Collected by the repository pytest validation boundary.
# - Defaults:
#   - Unsupported identities and unsafe publication paths fail closed.
#

"""Deterministic parametric compiler challenge evidence."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess as sp  # ruff: ignore[suspicious-subprocess-import]
import sys
from typing import Protocol
from typing import TYPE_CHECKING
from typing import cast

import pytest
from scripts.validate import c_abi_source
from scripts.validate import c_frontend_build
from scripts.validate import c_libc_source
from scripts.validate import target_profile

if TYPE_CHECKING:
    from collections.abc import Callable

_ROOT = Path(__file__).resolve().parents[2]
_GENERATOR = _ROOT / "benchmarks" / "challenges" / "generate.py"
_SHA256_HEX_LENGTH = 64
_ORACLE_BYTES = 4
_SENTINEL = "preserve"
_ENTRY_SYMBOL = "malbolge_challenge"
_ORACLE_SEMANTICS = "entry-return-u32-little-endian"
_STANDALONE_MAIN = "low-31-bits-only-not-oracle"
_ARRAY_SUBSCRIPT_KIND = "array-subscript-expression"
_CALL_EXPRESSION_KIND = "call-expression"
_FUNCTION_DECLARATION_KIND = "function-declaration"
_IF_STATEMENT_KIND = "if-statement"
_FOR_STATEMENT_KIND = "for-statement"
_UNARY_EXPRESSION_KIND = "unary-expression"
_VARIABLE_DECLARATION_KIND = "variable-declaration"
_POINTER_TYPE = "ptr(u32)"
_MEMORY_WALK_SUBSCRIPTS_PER_NODE = 3
_GRAPH_REDUCE_SUBSCRIPTS = 6
_FORBIDDEN_PUTCHAR = "putchar"
_FORBIDDEN_STDIO = "<stdio.h>"
_CLANG = _ROOT / ".dependencies/llvm/22.1.8/bin/clang.exe"
_FRONTEND_RESOURCE_DIR = _ROOT / ".dependencies/llvm/22.1.8/lib/clang/22"
_GUEST_INCLUDE = _ROOT / "src/runtime/guest-c-library/contract/include"
_WINDOWS_OS_NAME = "nt"
_ARITHMETIC_DAG_FAMILY = "arithmetic-dag"
_BRANCH_MIX_FAMILY = "branch-mix"
_CALL_CHAIN_FAMILY = "call-chain"
_LINEAR_MIX_FAMILY = "linear-mix"
_MEMORY_WALK_FAMILY = "memory-walk"
_POINTER_WALK_FAMILY = "pointer-walk"
_ALIAS_WALK_FAMILY = "alias-walk"
_STREAM_STATE_FAMILY = "stream-state"
_GRAPH_REDUCE_FAMILY = "graph-reduce"
_LAYOUT_CHAIN_FAMILY = "layout-chain"
_FAMILIES = (
    _ARITHMETIC_DAG_FAMILY,
    _BRANCH_MIX_FAMILY,
    _CALL_CHAIN_FAMILY,
    _LINEAR_MIX_FAMILY,
    _MEMORY_WALK_FAMILY,
    _POINTER_WALK_FAMILY,
    _ALIAS_WALK_FAMILY,
    _STREAM_STATE_FAMILY,
    _GRAPH_REDUCE_FAMILY,
    _LAYOUT_CHAIN_FAMILY,
)
_ARITHMETIC_DAG_V1_SOURCE_SHA256 = (
    "dcadb0753d70d16a19601bac1c05b6868767432a48eea67d599056ab28880607"
)
_ARITHMETIC_DAG_V1_ORACLE_SHA256 = (
    "0868382fe8067330f2ca3ccfcb4042ce5bcd38aaab75399d31f5f1994604b2ab"
)
_ARITHMETIC_DAG_V1_MANIFEST_SHA256 = (
    "f51043df00825e1b16fc9ded26cfeec71b10979bc852fd9533184b8aefe2d489"
)
_POINTER_WALK_V1_SOURCE_SHA256 = (
    "97a040fffa3d73fd1114944b6cd41e8fff158c54e19b6f1a9ef8209a8c4d0181"
)
_POINTER_WALK_V1_ORACLE_SHA256 = (
    "ac0317e131d5170fc13ff5b310406b1dce9473cd3c92575a8a8438acab24ada8"
)
_POINTER_WALK_V1_MANIFEST_SHA256 = (
    "e92dcb30cc2a6f1477564b3c9843a6bc47c04ed06beaafa74589dbaf788854cf"
)


class _ChallengeIdentity(Protocol):
    """Typed test view of one generated challenge identity."""

    family: str
    version: int
    seed: int
    profile: str
    nodes: int


class _GeneratedChallenge(Protocol):
    """Typed test view of generated challenge bytes."""

    source: bytes
    oracle: bytes
    manifest: bytes


class _GeneratorModule(Protocol):
    """Typed surface loaded from the standalone generator script."""

    ChallengeError: type[ValueError]
    ChallengeIdentity: Callable[[str, int, int, str, int], _ChallengeIdentity]
    _PROFILE_MANIFEST: Path

    def generate(self, identity: _ChallengeIdentity) -> _GeneratedChallenge:
        """Generate exact bytes for an identity."""
        ...

    def write_challenge(
        self,
        identity: _ChallengeIdentity,
        output: Path,
    ) -> None:
        """Publish exact challenge bytes."""

    def main(self) -> int:
        """Run the standalone CLI entrypoint."""
        ...


def _load_generator() -> _GeneratorModule:
    spec = importlib.util.spec_from_file_location(
        "malbolge_challenge_generator",
        _GENERATOR,
    )
    if spec is None or spec.loader is None:
        message = "challenge generator module cannot be loaded"
        raise RuntimeError(message)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return cast("_GeneratorModule", cast("object", module))


_GENERATOR_MODULE = _load_generator()


def _identity(
    *,
    family: str = _ARITHMETIC_DAG_FAMILY,
    seed: int = 7,
    nodes: int = 16,
) -> _ChallengeIdentity:
    return _GENERATOR_MODULE.ChallengeIdentity(
        family, 1, seed, "malbolge-2026", nodes
    )


def _run(command: list[str], cwd: Path) -> sp.CompletedProcess[str]:
    return sp.run(  # ruff: ignore[subprocess-without-shell-equals-true]
        command,
        cwd=cwd,
        check=False,
        capture_output=True,
        shell=False,
        text=True,
        timeout=30,
    )


def _snapshot(root: Path) -> dict[str, bytes]:
    return {path.name: path.read_bytes() for path in sorted(root.iterdir())}


@pytest.mark.parametrize("family", _FAMILIES)
def test_same_identity_replays_byte_identically(
    tmp_path: Path, family: str
) -> None:
    """The full payload is byte-identical for one immutable identity."""
    first = _GENERATOR_MODULE.generate(_identity(family=family))
    second = _GENERATOR_MODULE.generate(_identity(family=family))
    assert first.source == second.source
    assert first.oracle == second.oracle
    assert first.manifest == second.manifest
    one = tmp_path / "one"
    two = tmp_path / "two"
    _GENERATOR_MODULE.write_challenge(_identity(family=family), one)
    _GENERATOR_MODULE.write_challenge(_identity(family=family), two)
    assert _snapshot(one) == _snapshot(two)


def test_arithmetic_dag_v1_preserves_known_replay_vector() -> None:
    """Keep published v1 arithmetic identities byte-compatible."""
    generated = _GENERATOR_MODULE.generate(
        _identity(family=_ARITHMETIC_DAG_FAMILY, seed=0x1234, nodes=64)
    )
    assert (
        hashlib.sha256(generated.source).hexdigest()
        == _ARITHMETIC_DAG_V1_SOURCE_SHA256
    )
    assert (
        hashlib.sha256(generated.oracle).hexdigest()
        == _ARITHMETIC_DAG_V1_ORACLE_SHA256
    )
    assert (
        hashlib.sha256(generated.manifest).hexdigest()
        == _ARITHMETIC_DAG_V1_MANIFEST_SHA256
    )


def test_pointer_walk_v1_preserves_known_replay_vector() -> None:
    """Keep published v1 pointer identities byte-compatible."""
    generated = _GENERATOR_MODULE.generate(
        _identity(family=_POINTER_WALK_FAMILY, seed=0x1234, nodes=64)
    )
    assert (
        hashlib.sha256(generated.source).hexdigest()
        == _POINTER_WALK_V1_SOURCE_SHA256
    )
    assert (
        hashlib.sha256(generated.oracle).hexdigest()
        == _POINTER_WALK_V1_ORACLE_SHA256
    )
    assert (
        hashlib.sha256(generated.manifest).hexdigest()
        == _POINTER_WALK_V1_MANIFEST_SHA256
    )


def test_branch_mix_emits_one_live_diamond_per_node() -> None:
    """Branch challenges scale explicit if/else control-flow diamonds."""
    nodes = 19
    generated = _GENERATOR_MODULE.generate(
        _identity(family=_BRANCH_MIX_FAMILY, seed=0xCAFE, nodes=nodes)
    )
    source = generated.source.decode()
    assert source.count("    if (") == nodes
    assert source.count("    } else {") == nodes
    assert source.count("    uint32_t v") >= nodes


def test_alias_walk_emits_two_live_pointers_per_node() -> None:
    """Alias challenges keep two runtime-selected pointer paths per node."""
    nodes = 13
    generated = _GENERATOR_MODULE.generate(
        _identity(family=_ALIAS_WALK_FAMILY, seed=0xCAFE, nodes=nodes)
    )
    source = generated.source.decode()
    assert source.count("= &cells[value & UINT32_C(7)];") == nodes
    assert source.count("= &cells[(value >> UINT32_C(3))") == nodes
    assert source.count("    *left") == nodes
    assert source.count("    *right") == nodes


def test_pointer_walk_uses_live_data_dependent_addresses() -> None:
    """Pointer challenges select one live runtime-dependent slot per node."""
    nodes = 17
    generated = _GENERATOR_MODULE.generate(
        _identity(family=_POINTER_WALK_FAMILY, seed=0xBEEF, nodes=nodes)
    )
    source = generated.source.decode()
    assert source.count("= &cells[value & UINT32_C(7)];") == nodes
    assert source.count("    value = (*slot") == nodes
    assert source.count("    *slot") == nodes


def test_stream_state_emits_live_loop_and_branch() -> None:
    """Stream challenges keep one loop and one live state branch."""
    nodes = 19
    generated = _GENERATOR_MODULE.generate(
        _identity(family=_STREAM_STATE_FAMILY, seed=0xCAFE, nodes=nodes)
    )
    source = generated.source.decode()
    assert source.count("    for (") == 1
    assert source.count("        if (") == 1
    assert source.count("stream[index]") == 1
    assert source.count("        UINT32_C(") == nodes


def test_graph_reduce_emits_live_parent_graph() -> None:
    """Graph challenges retain generated parents and runtime graph lookup."""
    nodes = 19
    generated = _GENERATOR_MODULE.generate(
        _identity(family=_GRAPH_REDUCE_FAMILY, seed=0xFACE, nodes=nodes)
    )
    source = generated.source.decode()
    assert source.count("    for (") == 1
    assert source.count("parents[index]") == 1
    assert source.count("states[parent]") == 1
    assert source.count("weights[index]") == 1
    assert f"return states[{nodes}];" in source


def test_layout_chain_emits_distinct_live_helpers() -> None:
    """Layout challenges grow distinct helper bodies and live call sites."""
    nodes = 19
    generated = _GENERATOR_MODULE.generate(
        _identity(family=_LAYOUT_CHAIN_FAMILY, seed=0xF00D, nodes=nodes)
    )
    source = generated.source.decode()
    assert source.count("uint32_t malbolge_layout_") == nodes
    assert source.count("    value = malbolge_layout_") == nodes


def test_identity_dimensions_change_artifact_identity() -> None:
    """Seed and difficulty remain part of the exact generated identity."""
    baseline = _GENERATOR_MODULE.generate(_identity())
    changed_seed = _GENERATOR_MODULE.generate(_identity(seed=8))
    changed_nodes = _GENERATOR_MODULE.generate(_identity(nodes=17))
    changed_family = _GENERATOR_MODULE.generate(
        _identity(family=_LINEAR_MIX_FAMILY)
    )
    assert changed_seed.source != baseline.source
    assert changed_nodes.source != baseline.source
    assert changed_family.source != baseline.source


@pytest.mark.parametrize(
    ("family", "family_algorithm"),
    [
        (_ARITHMETIC_DAG_FAMILY, "splitmix64-arithmetic-dag-v1"),
        (_BRANCH_MIX_FAMILY, "splitmix64-branch-mix-v1"),
        (_CALL_CHAIN_FAMILY, "splitmix64-call-chain-v1"),
        (_LINEAR_MIX_FAMILY, "splitmix64-linear-mix-v1"),
        (_MEMORY_WALK_FAMILY, "splitmix64-memory-walk-v1"),
        (_POINTER_WALK_FAMILY, "splitmix64-pointer-walk-v1"),
        (_ALIAS_WALK_FAMILY, "splitmix64-alias-walk-v1"),
        (_STREAM_STATE_FAMILY, "splitmix64-stream-state-v1"),
        (_GRAPH_REDUCE_FAMILY, "splitmix64-graph-reduce-v1"),
        (_LAYOUT_CHAIN_FAMILY, "splitmix64-layout-chain-v1"),
    ],
)
def test_manifest_binds_identity_hashes_and_oracle(
    family: str, family_algorithm: str
) -> None:
    """The manifest binds profile identity, difficulty, and oracle size."""
    generated = _GENERATOR_MODULE.generate(
        _identity(family=family, seed=0x1234, nodes=4)
    )
    manifest = cast("dict[str, object]", json.loads(generated.manifest))
    identity = cast("dict[str, object]", manifest["identity"])
    fingerprint = cast("str", identity["target_profile_fingerprint"])
    assert identity == {
        "family": family,
        "version": 1,
        "seed": 0x1234,
        "target_profile": "malbolge-2026",
        "target_profile_fingerprint": fingerprint,
        "difficulty": {"nodes": 4},
    }
    assert fingerprint.startswith("malbolge-profile-v1:sha256:")
    suffix = fingerprint.removeprefix("malbolge-profile-v1:sha256:")
    assert len(suffix) == _SHA256_HEX_LENGTH
    artifacts = cast("dict[str, object]", manifest["artifacts"])
    source_sha256 = hashlib.sha256(generated.source).hexdigest()
    oracle_sha256 = hashlib.sha256(generated.oracle).hexdigest()
    assert artifacts["source_sha256"] == source_sha256
    assert artifacts["oracle_sha256"] == oracle_sha256
    assert artifacts["oracle_bytes"] == _ORACLE_BYTES
    assert manifest["oracle_semantics"] == _ORACLE_SEMANTICS
    assert manifest["entry_symbol"] == _ENTRY_SYMBOL
    assert manifest["standalone_main"] == _STANDALONE_MAIN
    generator = cast("dict[str, object]", manifest["generator"])
    assert generator["family_algorithm"] == family_algorithm
    assert len(generated.oracle) == _ORACLE_BYTES
    source = generated.source.decode()
    assert f"uint32_t {_ENTRY_SYMBOL}(void)" in source
    assert _FORBIDDEN_PUTCHAR not in source
    assert _FORBIDDEN_STDIO not in source


@pytest.mark.parametrize("family", _FAMILIES)
def test_generated_source_is_admitted_by_current_c_profile(
    tmp_path: Path, family: str
) -> None:
    """Every generated family uses only currently admitted C."""
    generated = _GENERATOR_MODULE.generate(
        _identity(family=family, seed=11, nodes=32)
    )
    source = tmp_path / "program.c"
    _ = source.write_bytes(generated.source)
    assert c_abi_source.analyze_source(source) == ()
    assert c_libc_source.analyze_source(source) == ()


@pytest.mark.skipif(
    os.name != _WINDOWS_OS_NAME,
    reason="reviewed normalized C frontend is Windows x86-64",
)
def test_branch_family_is_admitted_by_normalized_frontend(
    tmp_path: Path,
) -> None:
    """Keep branch nodes explicit through frontend normalization."""
    nodes = 13
    generated = _GENERATOR_MODULE.generate(
        _identity(family=_BRANCH_MIX_FAMILY, seed=23, nodes=nodes)
    )
    source = tmp_path / "branch.c"
    _ = source.write_bytes(generated.source)
    if not c_frontend_build.EXECUTABLE.is_file():
        c_frontend_build.build()
    completed = _run(
        [
            str(c_frontend_build.EXECUTABLE),
            "--source-id",
            "benchmarks/challenges/branch-probe.c",
            "--resource-dir",
            str(_FRONTEND_RESOURCE_DIR),
            "--guest-include",
            str(_GUEST_INCLUDE),
            str(source),
        ],
        _ROOT,
    )
    assert completed.returncode == 0, completed.stderr
    artifact = cast("dict[str, object]", json.loads(completed.stdout))
    normalized = cast("list[dict[str, object]]", artifact["nodes"])
    assert (
        sum(node.get("kind") == _IF_STATEMENT_KIND for node in normalized)
        == nodes
    )


@pytest.mark.skipif(
    os.name != _WINDOWS_OS_NAME,
    reason="reviewed normalized C frontend is Windows x86-64",
)
def test_call_family_is_admitted_by_normalized_frontend(
    tmp_path: Path,
) -> None:
    """Keep generated function calls explicit through normalization."""
    nodes = 17
    generated = _GENERATOR_MODULE.generate(
        _identity(family=_CALL_CHAIN_FAMILY, seed=31, nodes=nodes)
    )
    source = tmp_path / "calls.c"
    _ = source.write_bytes(generated.source)
    if not c_frontend_build.EXECUTABLE.is_file():
        c_frontend_build.build()
    completed = _run(
        [
            str(c_frontend_build.EXECUTABLE),
            "--source-id",
            "benchmarks/challenges/call-probe.c",
            "--resource-dir",
            str(_FRONTEND_RESOURCE_DIR),
            "--guest-include",
            str(_GUEST_INCLUDE),
            str(source),
        ],
        _ROOT,
    )
    assert completed.returncode == 0, completed.stderr
    artifact = cast("dict[str, object]", json.loads(completed.stdout))
    normalized = cast("list[dict[str, object]]", artifact["nodes"])
    calls = sum(
        node.get("kind") == _CALL_EXPRESSION_KIND for node in normalized
    )
    assert calls == nodes + 1


@pytest.mark.skipif(
    os.name != _WINDOWS_OS_NAME,
    reason="reviewed normalized C frontend is Windows x86-64",
)
def test_memory_family_is_admitted_by_normalized_frontend(
    tmp_path: Path,
) -> None:
    """Keep generated memory accesses explicit through normalization."""
    nodes = 11
    generated = _GENERATOR_MODULE.generate(
        _identity(family=_MEMORY_WALK_FAMILY, seed=29, nodes=nodes)
    )
    source = tmp_path / "memory.c"
    _ = source.write_bytes(generated.source)
    if not c_frontend_build.EXECUTABLE.is_file():
        c_frontend_build.build()
    completed = _run(
        [
            str(c_frontend_build.EXECUTABLE),
            "--source-id",
            "benchmarks/challenges/memory-probe.c",
            "--resource-dir",
            str(_FRONTEND_RESOURCE_DIR),
            "--guest-include",
            str(_GUEST_INCLUDE),
            str(source),
        ],
        _ROOT,
    )
    assert completed.returncode == 0, completed.stderr
    artifact = cast("dict[str, object]", json.loads(completed.stdout))
    normalized = cast("list[dict[str, object]]", artifact["nodes"])
    observed = sum(
        node.get("kind") == _ARRAY_SUBSCRIPT_KIND for node in normalized
    )
    expected = 1 + (_MEMORY_WALK_SUBSCRIPTS_PER_NODE * nodes)
    assert observed == expected


@pytest.mark.skipif(
    os.name != _WINDOWS_OS_NAME,
    reason="reviewed normalized C frontend is Windows x86-64",
)
def test_pointer_family_is_admitted_by_normalized_frontend(
    tmp_path: Path,
) -> None:
    """Keep runtime indexing and pointers explicit after normalization."""
    nodes = 11
    generated = _GENERATOR_MODULE.generate(
        _identity(family=_POINTER_WALK_FAMILY, seed=37, nodes=nodes)
    )
    source = tmp_path / "pointer.c"
    _ = source.write_bytes(generated.source)
    if not c_frontend_build.EXECUTABLE.is_file():
        c_frontend_build.build()
    completed = _run(
        [
            str(c_frontend_build.EXECUTABLE),
            "--source-id",
            "benchmarks/challenges/pointer-probe.c",
            "--resource-dir",
            str(_FRONTEND_RESOURCE_DIR),
            "--guest-include",
            str(_GUEST_INCLUDE),
            str(source),
        ],
        _ROOT,
    )
    assert completed.returncode == 0, completed.stderr
    artifact = cast("dict[str, object]", json.loads(completed.stdout))
    normalized = cast("list[dict[str, object]]", artifact["nodes"])
    subscripts = sum(
        node.get("kind") == _ARRAY_SUBSCRIPT_KIND for node in normalized
    )
    pointer_declarations = sum(
        node.get("kind") == _VARIABLE_DECLARATION_KIND
        and node.get("type") == _POINTER_TYPE
        for node in normalized
    )
    unary_operations = sum(
        node.get("kind") == _UNARY_EXPRESSION_KIND for node in normalized
    )
    assert subscripts == nodes + 1
    assert pointer_declarations == nodes
    assert unary_operations == 3 * nodes


@pytest.mark.skipif(
    os.name != _WINDOWS_OS_NAME,
    reason="reviewed normalized C frontend is Windows x86-64",
)
def test_stream_family_is_admitted_by_normalized_frontend(
    tmp_path: Path,
) -> None:
    """Keep stream loop, indexed read, and branch after normalization."""
    generated = _GENERATOR_MODULE.generate(
        _identity(family=_STREAM_STATE_FAMILY, seed=41, nodes=23)
    )
    source = tmp_path / "stream.c"
    _ = source.write_bytes(generated.source)
    if not c_frontend_build.EXECUTABLE.is_file():
        c_frontend_build.build()
    completed = _run(
        [
            str(c_frontend_build.EXECUTABLE),
            "--source-id",
            "benchmarks/challenges/stream-probe.c",
            "--resource-dir",
            str(_FRONTEND_RESOURCE_DIR),
            "--guest-include",
            str(_GUEST_INCLUDE),
            str(source),
        ],
        _ROOT,
    )
    assert completed.returncode == 0, completed.stderr
    artifact = cast("dict[str, object]", json.loads(completed.stdout))
    normalized = cast("list[dict[str, object]]", artifact["nodes"])
    assert sum(
        node.get("kind") == _FOR_STATEMENT_KIND for node in normalized
    ) == 1
    assert sum(
        node.get("kind") == _IF_STATEMENT_KIND for node in normalized
    ) == 1
    assert sum(
        node.get("kind") == _ARRAY_SUBSCRIPT_KIND for node in normalized
    ) == 1


@pytest.mark.skipif(
    os.name != _WINDOWS_OS_NAME,
    reason="reviewed normalized C frontend is Windows x86-64",
)
def test_graph_family_is_admitted_by_normalized_frontend(
    tmp_path: Path,
) -> None:
    """Keep graph parent lookup and state reduction after normalization."""
    generated = _GENERATOR_MODULE.generate(
        _identity(family=_GRAPH_REDUCE_FAMILY, seed=43, nodes=23)
    )
    source = tmp_path / "graph.c"
    _ = source.write_bytes(generated.source)
    if not c_frontend_build.EXECUTABLE.is_file():
        c_frontend_build.build()
    completed = _run(
        [
            str(c_frontend_build.EXECUTABLE),
            "--source-id",
            "benchmarks/challenges/graph-probe.c",
            "--resource-dir",
            str(_FRONTEND_RESOURCE_DIR),
            "--guest-include",
            str(_GUEST_INCLUDE),
            str(source),
        ],
        _ROOT,
    )
    assert completed.returncode == 0, completed.stderr
    artifact = cast("dict[str, object]", json.loads(completed.stdout))
    normalized = cast("list[dict[str, object]]", artifact["nodes"])
    assert sum(
        node.get("kind") == _FOR_STATEMENT_KIND for node in normalized
    ) == 1
    assert sum(
        node.get("kind") == _ARRAY_SUBSCRIPT_KIND for node in normalized
    ) == _GRAPH_REDUCE_SUBSCRIPTS


@pytest.mark.skipif(
    os.name != _WINDOWS_OS_NAME,
    reason="reviewed normalized C frontend is Windows x86-64",
)
def test_layout_family_is_admitted_by_normalized_frontend(
    tmp_path: Path,
) -> None:
    """Keep every distinct helper and live call after normalization."""
    nodes = 17
    generated = _GENERATOR_MODULE.generate(
        _identity(family=_LAYOUT_CHAIN_FAMILY, seed=47, nodes=nodes)
    )
    source = tmp_path / "layout.c"
    _ = source.write_bytes(generated.source)
    if not c_frontend_build.EXECUTABLE.is_file():
        c_frontend_build.build()
    completed = _run(
        [
            str(c_frontend_build.EXECUTABLE),
            "--source-id",
            "benchmarks/challenges/layout-probe.c",
            "--resource-dir",
            str(_FRONTEND_RESOURCE_DIR),
            "--guest-include",
            str(_GUEST_INCLUDE),
            str(source),
        ],
        _ROOT,
    )
    assert completed.returncode == 0, completed.stderr
    artifact = cast("dict[str, object]", json.loads(completed.stdout))
    normalized = cast("list[dict[str, object]]", artifact["nodes"])
    functions = sum(
        node.get("kind") == _FUNCTION_DECLARATION_KIND for node in normalized
    )
    calls = sum(
        node.get("kind") == _CALL_EXPRESSION_KIND for node in normalized
    )
    assert functions == nodes + 2
    assert calls == nodes + 1


def _assert_native_oracle(
    generated: _GeneratedChallenge,
    tmp_path: Path,
) -> None:
    source = tmp_path / "program.c"
    harness = tmp_path / "harness.c"
    object_file = tmp_path / "program.o"
    executable = tmp_path / "oracle-check.exe"
    _ = source.write_bytes(generated.source)
    expected = int.from_bytes(generated.oracle, byteorder="little")
    harness_text = chr(10).join((
        "#include <stdint.h>",
        f"uint32_t {_ENTRY_SYMBOL}(void);",
        "int main(void) {",
        f"    return {_ENTRY_SYMBOL}() == UINT32_C({expected}) ? 0 : 1;",
        "}",
        "",
    ))
    _ = harness.write_text(harness_text, encoding="utf-8")
    compiled = _run(
        [
            str(_CLANG),
            "-std=c23",
            "-Wall",
            "-Wextra",
            "-Werror",
            "-Dmain=malbolge_generated_main",
            "-c",
            str(source),
            "-o",
            str(object_file),
        ],
        _ROOT,
    )
    assert compiled.returncode == 0, compiled.stdout + compiled.stderr
    linked = _run(
        [str(_CLANG), str(object_file), str(harness), "-o", str(executable)],
        _ROOT,
    )
    assert linked.returncode == 0, linked.stdout + linked.stderr
    executed = _run([str(executable)], tmp_path)
    assert executed.returncode == 0, executed.stdout + executed.stderr


@pytest.mark.skipif(
    os.name != _WINDOWS_OS_NAME or not _CLANG.is_file(),
    reason="repository-pinned native Clang is unavailable",
)
@pytest.mark.parametrize(
    ("family", "seed", "nodes"),
    [
        (_ARITHMETIC_DAG_FAMILY, 0, 1),
        (_ARITHMETIC_DAG_FAMILY, 7, 64),
        (_ARITHMETIC_DAG_FAMILY, 0x1234, 257),
        (_BRANCH_MIX_FAMILY, 0, 1),
        (_BRANCH_MIX_FAMILY, 7, 64),
        (_BRANCH_MIX_FAMILY, 0x1234, 257),
        (_CALL_CHAIN_FAMILY, 0, 1),
        (_CALL_CHAIN_FAMILY, 7, 64),
        (_CALL_CHAIN_FAMILY, 0x1234, 257),
        (_LINEAR_MIX_FAMILY, 0, 1),
        (_LINEAR_MIX_FAMILY, 7, 64),
        (_LINEAR_MIX_FAMILY, 0x1234, 257),
        (_MEMORY_WALK_FAMILY, 0, 1),
        (_MEMORY_WALK_FAMILY, 7, 64),
        (_MEMORY_WALK_FAMILY, 0x1234, 257),
        (_POINTER_WALK_FAMILY, 0, 1),
        (_POINTER_WALK_FAMILY, 7, 64),
        (_POINTER_WALK_FAMILY, 0x1234, 257),
        (_ALIAS_WALK_FAMILY, 0, 1),
        (_ALIAS_WALK_FAMILY, 7, 64),
        (_ALIAS_WALK_FAMILY, 0x1234, 257),
        (_STREAM_STATE_FAMILY, 0, 1),
        (_STREAM_STATE_FAMILY, 7, 64),
        (_STREAM_STATE_FAMILY, 0x1234, 257),
        (_GRAPH_REDUCE_FAMILY, 0, 1),
        (_GRAPH_REDUCE_FAMILY, 7, 64),
        (_GRAPH_REDUCE_FAMILY, 0x1234, 257),
        (_LAYOUT_CHAIN_FAMILY, 0, 1),
        (_LAYOUT_CHAIN_FAMILY, 7, 64),
        (_LAYOUT_CHAIN_FAMILY, 0x1234, 257),
    ],
)
def test_native_source_result_matches_independent_oracle(
    tmp_path: Path,
    *,
    family: str,
    seed: int,
    nodes: int,
) -> None:
    """Compiled C entry result matches the independently retained oracle."""
    generated = _GENERATOR_MODULE.generate(
        _identity(family=family, seed=seed, nodes=nodes)
    )
    _assert_native_oracle(generated, tmp_path)


@pytest.mark.parametrize("family", _FAMILIES)
def test_difficulty_scales_source_without_saturating_small_cases(
    family: str,
) -> None:
    """Increasing node counts continue increasing generated source size."""
    sizes = [
        len(
            _GENERATOR_MODULE.generate(
                _identity(family=family, nodes=nodes)
            ).source
        )
        for nodes in (1, 8, 64, 512)
    ]
    assert sizes == sorted(sizes)
    assert len(set(sizes)) == len(sizes)


def test_profile_projection_cannot_introduce_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A drifted fingerprint projection cannot mint a canonical profile."""
    projection = tmp_path / "profile-fingerprints.json"
    canonical = cast(
        "dict[str, object]",
        json.loads(
            target_profile.FINGERPRINT_MANIFEST.read_text(encoding="utf-8")
        ),
    )
    profiles = cast("dict[str, object]", canonical["profiles"])
    profiles["invented-profile"] = "malbolge-profile-v1:sha256:" + (
        "0" * _SHA256_HEX_LENGTH
    )
    _ = projection.write_text(json.dumps(canonical), encoding="utf-8")
    monkeypatch.setattr(_GENERATOR_MODULE, "_PROFILE_MANIFEST", projection)
    invented = _GENERATOR_MODULE.ChallengeIdentity(
        "arithmetic-dag", 1, 0, "invented-profile", 1
    )
    with pytest.raises(
        _GENERATOR_MODULE.ChallengeError,
        match="fingerprint manifest disagrees with registry",
    ):
        _ = _GENERATOR_MODULE.generate(invented)


def test_invalid_profile_projection_encoding_is_domain_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Broken projection encoding fails through the generator contract."""
    projection = tmp_path / "profile-fingerprints.json"
    _ = projection.write_bytes(bytes((0xFF, 0xFE)))
    monkeypatch.setattr(_GENERATOR_MODULE, "_PROFILE_MANIFEST", projection)
    with pytest.raises(
        _GENERATOR_MODULE.ChallengeError,
        match="fingerprint manifest is unavailable",
    ):
        _ = _GENERATOR_MODULE.generate(_identity())


def test_public_api_rejects_foreign_identity_and_output_types() -> None:
    """Direct API misuse stays inside the challenge error boundary."""
    with pytest.raises(
        _GENERATOR_MODULE.ChallengeError,
        match="identity must use the exact immutable type",
    ):
        _ = _GENERATOR_MODULE.generate(
            cast("_ChallengeIdentity", object())
        )
    with pytest.raises(
        _GENERATOR_MODULE.ChallengeError,
        match="output root must use pathlib Path",
    ):
        _GENERATOR_MODULE.write_challenge(
            _identity(),
            cast("Path", cast("object", "challenge")),
        )


def test_invalid_identity_fails_closed() -> None:
    """Malformed or non-canonical identity dimensions never generate output."""
    invalid = (
        _GENERATOR_MODULE.ChallengeIdentity("wrong", 1, 0, "malbolge-2026", 1),
        _GENERATOR_MODULE.ChallengeIdentity(
            "arithmetic-dag", 2, 0, "malbolge-2026", 1
        ),
        _GENERATOR_MODULE.ChallengeIdentity(
            "linear-mix", 2, 0, "malbolge-2026", 1
        ),
        _GENERATOR_MODULE.ChallengeIdentity(
            "arithmetic-dag", 1, -1, "malbolge-2026", 1
        ),
        _GENERATOR_MODULE.ChallengeIdentity(
            "arithmetic-dag", 1, 0, " malbolge-2026", 1
        ),
        _GENERATOR_MODULE.ChallengeIdentity(
            "arithmetic-dag", 1, 0, "invented-profile", 1
        ),
        _GENERATOR_MODULE.ChallengeIdentity(
            "arithmetic-dag", 1, 0, "malbolge-2026", 0
        ),
    )
    for identity in invalid:
        with pytest.raises(_GENERATOR_MODULE.ChallengeError, match=r".+"):
            _ = _GENERATOR_MODULE.generate(identity)


def test_publication_never_deletes_unrelated_output(tmp_path: Path) -> None:
    """An occupied output directory is preserved rather than replaced."""
    output = tmp_path / "challenge"
    output.mkdir()
    sentinel = output / "keep.txt"
    _ = sentinel.write_text(_SENTINEL, encoding="utf-8")
    with pytest.raises(
        _GENERATOR_MODULE.ChallengeError,
        match="output path already exists",
    ):
        _GENERATOR_MODULE.write_challenge(_identity(), output)
    assert sentinel.read_text(encoding="utf-8") == _SENTINEL


@pytest.mark.parametrize(
    "artifact_name", sorted(("manifest.json", "oracle.bin", "program.c"))
)
def test_exact_replay_with_linked_artifact_fails_closed(
    tmp_path: Path,
    artifact_name: str,
) -> None:
    """Replay cannot inherit any generated payload through a linked leaf."""
    output = tmp_path / "challenge"
    _GENERATOR_MODULE.write_challenge(_identity(), output)
    artifact = output / artifact_name
    target = tmp_path / f"external-{artifact_name}"
    _ = artifact.replace(target)
    try:
        artifact.symlink_to(target)
    except OSError as error:
        _ = target.replace(artifact)
        pytest.skip(f"file symlinks unavailable on this host: {error}")
    with pytest.raises(
        _GENERATOR_MODULE.ChallengeError,
        match="output path already exists",
    ):
        _GENERATOR_MODULE.write_challenge(_identity(), output)
    assert artifact.is_symlink()
    assert target.read_bytes() == artifact.read_bytes()


def test_exact_replay_cannot_bypass_distinct_output_requirement(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An exact replay at `.` cannot bypass the distinct-directory contract."""
    generated = _GENERATOR_MODULE.generate(_identity())
    _ = (tmp_path / "program.c").write_bytes(generated.source)
    _ = (tmp_path / "oracle.bin").write_bytes(generated.oracle)
    _ = (tmp_path / "manifest.json").write_bytes(generated.manifest)
    monkeypatch.chdir(tmp_path)
    with pytest.raises(
        _GENERATOR_MODULE.ChallengeError,
        match="output path must name a distinct directory",
    ):
        _GENERATOR_MODULE.write_challenge(_identity(), Path())


def test_exact_replay_under_linked_parent_still_fails_closed(
    tmp_path: Path,
) -> None:
    """Exact replay cannot bypass linked-ancestor rejection."""
    target = tmp_path / "real-parent"
    target.mkdir()
    real_output = target / "challenge"
    _GENERATOR_MODULE.write_challenge(_identity(), real_output)
    linked = tmp_path / "linked-parent"
    try:
        linked.symlink_to(target, target_is_directory=True)
    except OSError as error:
        pytest.skip(f"directory symlinks unavailable on this host: {error}")
    with pytest.raises(
        _GENERATOR_MODULE.ChallengeError,
        match="output path has linked ancestor",
    ):
        _GENERATOR_MODULE.write_challenge(_identity(), linked / "challenge")
    assert _snapshot(real_output) == _snapshot(target / "challenge")


def test_linked_output_parent_fails_closed(tmp_path: Path) -> None:
    """A linked output ancestor cannot redirect challenge publication."""
    target = tmp_path / "real-parent"
    target.mkdir()
    linked = tmp_path / "linked-parent"
    try:
        linked.symlink_to(target, target_is_directory=True)
    except OSError as error:
        pytest.skip(f"directory symlinks unavailable on this host: {error}")
    with pytest.raises(
        _GENERATOR_MODULE.ChallengeError,
        match="output path has linked ancestor",
    ):
        _GENERATOR_MODULE.write_challenge(_identity(), linked / "challenge")
    assert not (target / "challenge").exists()


@pytest.mark.skipif(
    os.name != _WINDOWS_OS_NAME,
    reason="NTFS junctions are a Windows path-redirection boundary",
)
def test_junction_output_parent_fails_closed(tmp_path: Path) -> None:
    """A junction ancestor cannot redirect challenge publication."""
    target = tmp_path / "real-parent"
    target.mkdir()
    linked = tmp_path / "junction-parent"
    created = _run(
        ["cmd.exe", "/d", "/c", "mklink", "/J", str(linked), str(target)],
        tmp_path,
    )
    if created.returncode != 0 or not linked.is_junction():
        pytest.skip("directory junction creation is unavailable on this host")
    with pytest.raises(
        _GENERATOR_MODULE.ChallengeError,
        match="output path has linked ancestor",
    ):
        _GENERATOR_MODULE.write_challenge(_identity(), linked / "challenge")
    assert not (target / "challenge").exists()


def test_parent_collision_fails_without_overwriting_blocker(
    tmp_path: Path,
) -> None:
    """A non-directory output parent becomes one closed publication error."""
    blocker = tmp_path / "blocked-parent"
    _ = blocker.write_text(_SENTINEL, encoding="utf-8")
    with pytest.raises(
        _GENERATOR_MODULE.ChallengeError,
        match="output parent cannot be prepared",
    ):
        _GENERATOR_MODULE.write_challenge(_identity(), blocker / "challenge")
    assert blocker.read_text(encoding="utf-8") == _SENTINEL


def test_staging_collision_preserves_existing_state(tmp_path: Path) -> None:
    """A pre-existing staging path is not followed, removed, or overwritten."""
    output = tmp_path / "challenge"
    staging = tmp_path / ".challenge.staging"
    staging.mkdir()
    sentinel = staging / "keep.txt"
    _ = sentinel.write_text(_SENTINEL, encoding="utf-8")
    with pytest.raises(
        _GENERATOR_MODULE.ChallengeError,
        match="staging path already exists",
    ):
        _GENERATOR_MODULE.write_challenge(_identity(), output)
    assert sentinel.read_text(encoding="utf-8") == _SENTINEL
    assert not output.exists()


def test_raced_staging_claim_never_deletes_other_writer(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A staging race fails before cleanup ownership is acquired."""
    output = tmp_path / "challenge"
    staging = tmp_path / ".challenge.staging"
    sentinel = staging / "keep.txt"
    staging_path = cast(
        "Callable[[Path], Path]",
        vars(_GENERATOR_MODULE)["_staging_path"],
    )

    def race_after_precheck(candidate: Path) -> Path:
        observed = staging_path(candidate)
        observed.mkdir()
        _ = sentinel.write_text(_SENTINEL, encoding="utf-8")
        return observed

    monkeypatch.setattr(_GENERATOR_MODULE, "_staging_path", race_after_precheck)
    with pytest.raises(
        _GENERATOR_MODULE.ChallengeError,
        match="staging path already exists",
    ):
        _GENERATOR_MODULE.write_challenge(_identity(), output)
    assert sentinel.read_text(encoding="utf-8") == _SENTINEL
    assert not output.exists()


def test_linux_publication_dispatches_to_no_replace_primitive(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Linux publication is routed through renameat2 no-replace."""
    staging = tmp_path / "staging"
    output = tmp_path / "output"
    staging.mkdir()
    observed: list[tuple[Path, Path]] = []

    def publish(source: Path, destination: Path) -> None:
        observed.append((source, destination))

    monkeypatch.setattr(_GENERATOR_MODULE, "_linux_rename_noreplace", publish)
    publisher = cast(
        "Callable[..., None]",
        vars(_GENERATOR_MODULE)["_publish_staging_no_replace"],
    )
    publisher(staging, output, os_name="posix", platform="linux")
    assert observed == [(staging, output)]


def test_unknown_platform_publication_fails_closed(tmp_path: Path) -> None:
    """Unsupported hosts never fall back to replacing an existing path."""
    staging = tmp_path / "staging"
    output = tmp_path / "output"
    staging.mkdir()
    publisher = cast(
        "Callable[..., None]",
        vars(_GENERATOR_MODULE)["_publish_staging_no_replace"],
    )

    with pytest.raises(
        OSError, match="no-replace directory publication is unsupported"
    ):
        publisher(staging, output, os_name="posix", platform="unsupported")
    assert staging.is_dir()
    assert not output.exists()


def test_raced_final_output_file_is_preserved(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A final-path race cannot overwrite unrelated state."""
    output = tmp_path / "challenge"
    staging = tmp_path / ".challenge.staging"
    write_staging = cast(
        "Callable[[Path, _GeneratedChallenge], None]",
        vars(_GENERATOR_MODULE)["_write_staging"],
    )

    def race_after_staging(
        candidate: Path,
        generated: _GeneratedChallenge,
    ) -> None:
        write_staging(candidate, generated)
        _ = output.write_text(_SENTINEL, encoding="utf-8")

    monkeypatch.setattr(_GENERATOR_MODULE, "_write_staging", race_after_staging)
    with pytest.raises(
        _GENERATOR_MODULE.ChallengeError,
        match="challenge publication failed",
    ):
        _GENERATOR_MODULE.write_challenge(_identity(), output)
    assert output.read_text(encoding="utf-8") == _SENTINEL
    assert not staging.exists()


@pytest.mark.parametrize("family", _FAMILIES)
def test_cli_replays_manifest_and_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    family: str,
) -> None:
    """The CLI parser and publisher replay an exact generated directory."""
    output = tmp_path / "challenge"
    arguments = [
        str(_GENERATOR),
        family,
        "--version",
        "1",
        "--seed",
        "99",
        "--profile",
        "malbolge-2026",
        "--nodes",
        "32",
        "--output",
        str(output),
    ]
    monkeypatch.setattr(sys, "argv", arguments)
    assert _GENERATOR_MODULE.main() == 0
    snapshot = _snapshot(output)
    assert _GENERATOR_MODULE.main() == 0
    assert snapshot == _snapshot(output)
