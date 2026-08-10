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
import subprocess as sp  # ruff: ignore[suspicious-subprocess-import]
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, cast

import pytest
from scripts.validate import c_abi_source, c_libc_source, target_profile

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
_FORBIDDEN_PUTCHAR = "putchar"
_FORBIDDEN_STDIO = "<stdio.h>"
_CLANG = _ROOT / ".dependencies/llvm/22.1.8/bin/clang.exe"
_WINDOWS_OS_NAME = "nt"


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


def _identity(*, seed: int = 7, nodes: int = 16) -> _ChallengeIdentity:
    return _GENERATOR_MODULE.ChallengeIdentity(
        "arithmetic-dag", 1, seed, "malbolge-2026", nodes
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


def test_same_identity_replays_byte_identically(tmp_path: Path) -> None:
    """The full payload is byte-identical for one immutable identity."""
    first = _GENERATOR_MODULE.generate(_identity())
    second = _GENERATOR_MODULE.generate(_identity())
    assert first.source == second.source
    assert first.oracle == second.oracle
    assert first.manifest == second.manifest
    one = tmp_path / "one"
    two = tmp_path / "two"
    _GENERATOR_MODULE.write_challenge(_identity(), one)
    _GENERATOR_MODULE.write_challenge(_identity(), two)
    assert _snapshot(one) == _snapshot(two)


def test_identity_dimensions_change_artifact_identity() -> None:
    """Seed and difficulty remain part of the exact generated identity."""
    baseline = _GENERATOR_MODULE.generate(_identity())
    changed_seed = _GENERATOR_MODULE.generate(_identity(seed=8))
    changed_nodes = _GENERATOR_MODULE.generate(_identity(nodes=17))
    assert changed_seed.source != baseline.source
    assert changed_nodes.source != baseline.source


def test_manifest_binds_identity_hashes_and_oracle() -> None:
    """The manifest binds profile identity, difficulty, and oracle size."""
    generated = _GENERATOR_MODULE.generate(_identity(seed=0x1234, nodes=4))
    manifest = cast("dict[str, object]", json.loads(generated.manifest))
    identity = cast("dict[str, object]", manifest["identity"])
    fingerprint = cast("str", identity["target_profile_fingerprint"])
    assert identity == {
        "family": "arithmetic-dag",
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
    assert len(generated.oracle) == _ORACLE_BYTES
    source = generated.source.decode()
    assert f"uint32_t {_ENTRY_SYMBOL}(void)" in source
    assert _FORBIDDEN_PUTCHAR not in source
    assert _FORBIDDEN_STDIO not in source


def test_generated_source_is_admitted_by_current_c_profile(
    tmp_path: Path,
) -> None:
    """Generated arithmetic DAG source uses only currently admitted C."""
    generated = _GENERATOR_MODULE.generate(_identity(seed=11, nodes=32))
    source = tmp_path / "program.c"
    _ = source.write_bytes(generated.source)
    assert c_abi_source.analyze_source(source) == ()
    assert c_libc_source.analyze_source(source) == ()


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
    harness_text = chr(10).join(
        (
            "#include <stdint.h>",
            f"uint32_t {_ENTRY_SYMBOL}(void);",
            "int main(void) {",
            f"    return {_ENTRY_SYMBOL}() == UINT32_C({expected}) ? 0 : 1;",
            "}",
            "",
        )
    )
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
    ("seed", "nodes"),
    [(0, 1), (7, 64), (0x1234, 257)],
)
def test_native_source_result_matches_independent_oracle(
    tmp_path: Path,
    seed: int,
    nodes: int,
) -> None:
    """Compiled C entry result matches the independently retained oracle."""
    generated = _GENERATOR_MODULE.generate(_identity(seed=seed, nodes=nodes))
    _assert_native_oracle(generated, tmp_path)


def test_difficulty_scales_source_without_saturating_small_cases() -> None:
    """Increasing node counts continue increasing generated source size."""
    sizes = [
        len(_GENERATOR_MODULE.generate(_identity(nodes=nodes)).source)
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
        json.loads(target_profile.FINGERPRINT_MANIFEST.read_text(encoding="utf-8")),
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


def test_invalid_identity_fails_closed() -> None:
    """Malformed or non-canonical identity dimensions never generate output."""
    invalid = (
        _GENERATOR_MODULE.ChallengeIdentity("wrong", 1, 0, "malbolge-2026", 1),
        _GENERATOR_MODULE.ChallengeIdentity("arithmetic-dag", 2, 0, "malbolge-2026", 1),
        _GENERATOR_MODULE.ChallengeIdentity(
            "arithmetic-dag", 1, -1, "malbolge-2026", 1
        ),
        _GENERATOR_MODULE.ChallengeIdentity(
            "arithmetic-dag", 1, 0, " malbolge-2026", 1
        ),
        _GENERATOR_MODULE.ChallengeIdentity(
            "arithmetic-dag", 1, 0, "invented-profile", 1
        ),
        _GENERATOR_MODULE.ChallengeIdentity("arithmetic-dag", 1, 0, "malbolge-2026", 0),
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


def test_cli_replays_manifest_and_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The CLI parser and publisher replay an exact generated directory."""
    output = tmp_path / "challenge"
    arguments = [
        str(_GENERATOR),
        "arithmetic-dag",
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
