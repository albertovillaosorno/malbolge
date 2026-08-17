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
#   - Regression evidence for the pinned clang-tidy development identity.
# - Must-Not:
#   - Download LLVM or require optional local native dependencies in CI.
# - Allows:
#   - Inputs: temporary manifests, archives, and optional repository LLVM roots.
#   - Outputs: deterministic admission and rejection evidence.
#   - Side effects: temporary files and exact-version executable probes only.
# - Split-When:
#   - Split when plugin loading gains independent cross-platform test policy.
# - Merge-When:
#   - Merge when another suite owns this exact development identity contract.
# - Summary:
#   - Lock the clang-tidy development toolchain boundary.
# - Description:
#   - Exercises manifest closure, path safety, hashes, and local version probes.
# - Usage:
#   - Runs with the repository Python test suite.
# - Defaults:
#   - Optional local installation evidence is skipped when LLVM is absent.
#

"""Regression evidence for the pinned clang-tidy development toolchain."""

from __future__ import annotations

from dataclasses import replace
import hashlib
import json
import subprocess as sp  # ruff: ignore[suspicious-subprocess-import]
import sys
from typing import TYPE_CHECKING
from typing import cast

if TYPE_CHECKING:
    from pathlib import Path

import pytest
from scripts.validate import main as validate_main
from scripts.validate import tidy_toolchain

EXPECTED_ASSET = "clang+llvm-22.1.8-x86_64-pc-windows-msvc.tar.xz"
EXPECTED_SHA256 = (
    "d96c2cc1736f4eb7fa43cb9bbdf56d93"
    "551a9ae0a9aadb9c99c3c3b2b712a234"
)
EXPECTED_SIZE = 862053924
LINUX_PLATFORM = "linux-x86_64"
LINUX_PROVIDER = "fedora-rpm-set-v1"
LINUX_PLUGIN_STRATEGY = "upstream-host-loadable-module-v1"
LINUX_ASSETS = (
    (
        "clang-devel-22.1.8-4.fc44.x86_64.rpm",
        4_239_048,
        "3f2e18cc4d5b8dd6e3d986b53d9e422ad709a8421d7bbcab34c08fe7cf0166ce",
    ),
    (
        "clang-tools-extra-devel-22.1.8-4.fc44.x86_64.rpm",
        326_651,
        "10e950ff5fae5544887231d307230eb8daa1e1097659089bbe896240f3c7a5c9",
    ),
    (
        "llvm-devel-22.1.8-4.fc44.x86_64.rpm",
        5_958_784,
        "c22b616026fab232529c678624760bca93ad429329c3cee4d1495b6db632f0e3",
    ),
)
CONFIGURATION_ERROR_STATUS = 2
PLUGIN_MISMATCH = "plugin registration mismatch"
OBSERVED_NONE = "observed none"
BIT_FIELD_CODE = "MALBOLGE-ABI-001"
BIT_FIELD_WARNING = "[malbolge-abi-bit-field,-warnings-as-errors]"
BIT_FIELD_LOCATION = "abi_bit_field.c:36:14:"
IMPORTED_ALIAS_FIXTURE = "abi_imported_forbidden_alias.c"
PLUGIN_REJECTIONS = (
    ("abi_bit_field.c", "MALBOLGE-ABI-001", "malbolge-abi-bit-field"),
    (
        "abi_packed_attribute.c",
        "MALBOLGE-ABI-002",
        "malbolge-abi-packed-layout",
    ),
    ("abi_packed_field.c", "MALBOLGE-ABI-002", "malbolge-abi-packed-layout"),
    ("abi_pragma_pack.c", "MALBOLGE-ABI-003", "malbolge-abi-pragma-pack"),
    (
        "abi_extended_alignment.c",
        "MALBOLGE-ABI-004",
        "malbolge-abi-over-alignment",
    ),
    ("abi_bit_int.c", "MALBOLGE-ABI-005", "malbolge-abi-type-surface"),
    (
        "abi_imported_forbidden_alias.c",
        "MALBOLGE-ABI-006",
        "malbolge-abi-type-surface",
    ),
    (
        "abi_int128_extension.c",
        "MALBOLGE-ABI-006",
        "malbolge-abi-type-surface",
    ),
    (
        "abi_vector_extension.c",
        "MALBOLGE-ABI-007",
        "malbolge-abi-type-surface",
    ),
    (
        "abi_address_space.c",
        "MALBOLGE-ABI-008",
        "malbolge-abi-type-surface",
    ),
)


def _canonical_document() -> dict[str, object]:
    parsed = cast(
        "object",
        json.loads(tidy_toolchain.MANIFEST.read_text(encoding="utf-8")),
    )
    assert isinstance(parsed, dict)
    return cast("dict[str, object]", parsed)


def _write_manifest(tmp_path: Path, document: dict[str, object]) -> Path:
    manifest = tmp_path / "llvm-clang-tidy-toolchain.json"
    _ = manifest.write_text(
        json.dumps(document),
        encoding="utf-8",
        newline="\n",
    )
    return manifest


def test_canonical_identity_pins_exact_release_artifact() -> None:
    """Tracked development identity is the reviewed LLVM 22.1.8 asset."""
    identity = tidy_toolchain.load_identity()

    assert identity.llvm_version == tidy_toolchain.LLVM_VERSION
    assert identity.release_tag == tidy_toolchain.RELEASE_TAG
    assert identity.platform_id == tidy_toolchain.WINDOWS_PLATFORM
    assert identity.asset_name == EXPECTED_ASSET
    assert identity.asset_size_bytes == EXPECTED_SIZE
    assert identity.asset_sha256 == EXPECTED_SHA256
    assert (
        identity.windows_plugin_strategy
        == tidy_toolchain.WINDOWS_PLUGIN_STRATEGY
    )
    assert (
        identity.registry_bridge_export
        == tidy_toolchain.REGISTRY_BRIDGE_EXPORT
    )
    assert identity.plugin_checks == tidy_toolchain.PLUGIN_CHECKS


def test_linux_identity_selects_exact_rpm_set_and_neutral_runtime() -> None:
    """Linux selects exact Fedora inputs and neutral LLVM runtime."""
    identity = tidy_toolchain.load_identity(platform_id=LINUX_PLATFORM)

    assert identity.platform_id == LINUX_PLATFORM
    assert identity.development_provider == LINUX_PROVIDER
    assert identity.plugin_strategy == LINUX_PLUGIN_STRATEGY
    assert tuple(
        (asset.name, asset.size_bytes, asset.sha256)
        for asset in identity.development_assets
    ) == LINUX_ASSETS
    assert identity.clang == (
        tidy_toolchain.ROOT
        / ".dependencies/llvm/22.1.8/jig-bin/clang.bin"
    )
    assert identity.clang_tidy == (
        tidy_toolchain.ROOT
        / ".dependencies/llvm/22.1.8/jig-bin/clang-tidy.bin"
    )
    assert identity.plugin_host == identity.clang_tidy
    assert identity.plugin_library == (
        tidy_toolchain.ROOT
        / ".dependencies/tools-tidy/22.1.8/bin/malbolge-tidy.so"
    )


def test_platform_identity_normalizes_linux_x86_64() -> None:
    """Linux x86-64 normalizes to the tracked native-analysis platform key."""
    assert (
        tidy_toolchain.host_platform_id(system="Linux", machine="x86_64")
        == LINUX_PLATFORM
    )
    assert (
        tidy_toolchain.host_platform_id(system="linux", machine="AMD64")
        == LINUX_PLATFORM
    )


def test_unknown_platform_identity_fails_closed() -> None:
    """Native-analysis never invents a toolchain for an untracked platform."""
    with pytest.raises(
        tidy_toolchain.ToolchainError,
        match="unsupported clang-tidy toolchain platform",
    ):
        _ = tidy_toolchain.load_identity(platform_id="linux-aarch64")


def test_platform_identity_normalizes_windows_x86_64() -> None:
    """Windows machine aliases resolve to one manifest platform key."""
    assert (
        tidy_toolchain.host_platform_id(system="Windows", machine="AMD64")
        == tidy_toolchain.WINDOWS_PLATFORM
    )
    assert (
        tidy_toolchain.host_platform_id(system="windows", machine="x86_64")
        == tidy_toolchain.WINDOWS_PLATFORM
    )


def test_manifest_rejects_unknown_top_level_key(tmp_path: Path) -> None:
    """Toolchain identity is closed against undeclared policy fields."""
    document = _canonical_document()
    document["latest"] = True
    manifest = _write_manifest(tmp_path, document)

    with pytest.raises(tidy_toolchain.ToolchainError, match="unknown latest"):
        _ = tidy_toolchain.load_identity(manifest, root=tmp_path)


def test_manifest_rejects_duplicate_json_key(tmp_path: Path) -> None:
    """Pinned identity never uses last-value-wins JSON semantics."""
    manifest = tmp_path / "llvm-clang-tidy-toolchain.json"
    _ = manifest.write_text(
        '{"schema_version":1,"schema_version":2}',
        encoding="utf-8",
        newline="\n",
    )

    with pytest.raises(
        tidy_toolchain.ToolchainError,
        match="duplicate clang-tidy toolchain JSON key: schema_version",
    ):
        _ = tidy_toolchain.load_identity(manifest, root=tmp_path)


def test_manifest_rejects_escaping_runtime_root(tmp_path: Path) -> None:
    """Native roots cannot redirect validation outside the repository."""
    document = _canonical_document()
    document["runtime_root"] = "../llvm"
    manifest = _write_manifest(tmp_path, document)

    with pytest.raises(
        tidy_toolchain.ToolchainError,
        match="runtime_root must stay within the repository",
    ):
        _ = tidy_toolchain.load_identity(manifest, root=tmp_path)


def test_manifest_rejects_drive_relative_development_root(
    tmp_path: Path,
) -> None:
    """Windows drive-relative roots cannot escape repository ownership."""
    document = _canonical_document()
    document["development_root"] = "D:llvm-dev"
    manifest = _write_manifest(tmp_path, document)

    with pytest.raises(
        tidy_toolchain.ToolchainError,
        match="development_root must stay within the repository",
    ):
        _ = tidy_toolchain.load_identity(manifest, root=tmp_path)


def test_manifest_rejects_drifted_llvm_version(tmp_path: Path) -> None:
    """A manifest edit cannot silently select another LLVM revision."""
    document = _canonical_document()
    document["llvm_version"] = "22.1.9"
    manifest = _write_manifest(tmp_path, document)

    with pytest.raises(
        tidy_toolchain.ToolchainError,
        match=r"llvm_version must be 22\.1\.8",
    ):
        _ = tidy_toolchain.load_identity(manifest, root=tmp_path)


def test_archive_verification_accepts_exact_bytes(tmp_path: Path) -> None:
    """Archive admission binds both byte count and SHA-256."""
    payload = b"reviewed LLVM development archive"
    archive = tmp_path / "llvm.tar.xz"
    _ = archive.write_bytes(payload)
    identity = replace(
        tidy_toolchain.load_identity(root=tmp_path),
        asset_sha256=hashlib.sha256(payload).hexdigest(),
        asset_size_bytes=len(payload),
    )

    tidy_toolchain.verify_archive(archive, identity)


def test_archive_verification_rejects_hash_mismatch(tmp_path: Path) -> None:
    """Same-size forged archive bytes fail closed."""
    payload = b"reviewed LLVM development archive"
    forged = b"forged!! LLVM development archive"
    assert len(payload) == len(forged)
    archive = tmp_path / "llvm.tar.xz"
    _ = archive.write_bytes(forged)
    identity = replace(
        tidy_toolchain.load_identity(root=tmp_path),
        asset_sha256=hashlib.sha256(payload).hexdigest(),
        asset_size_bytes=len(payload),
    )

    with pytest.raises(tidy_toolchain.ToolchainError, match="SHA-256 mismatch"):
        tidy_toolchain.verify_archive(archive, identity)


def test_installation_rejects_wrong_host_platform(tmp_path: Path) -> None:
    """Windows development identity is never inferred to support Linux."""
    identity = tidy_toolchain.load_identity(root=tmp_path)

    with pytest.raises(
        tidy_toolchain.ToolchainError,
        match="host is linux-x86_64",
    ):
        tidy_toolchain.validate_installation(
            identity,
            observed_platform="linux-x86_64",
        )


def test_local_installation_matches_manifest_when_present() -> None:
    """Installed optional LLVM roots, when present, match exact identity."""
    identity = tidy_toolchain.load_identity()
    runtime_ready = identity.runtime_root.is_dir()
    development_ready = identity.development_root.is_dir()
    installed = runtime_ready and development_ready
    if not installed:
        pytest.skip("optional local LLVM development kit is absent")

    tidy_toolchain.validate_installation(identity)


def _built_plugin_identity() -> tidy_toolchain.ToolchainIdentity:
    identity = tidy_toolchain.load_identity()
    if (
        not identity.plugin_host.is_file()
        or not identity.plugin_library.is_file()
    ):
        pytest.skip("optional local clang-tidy plugin build is absent")
    return identity


def test_canonical_host_pairs_plugin_by_default(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The default project host probes its paired DLL before source checks."""
    identity = _built_plugin_identity()
    broken_plugin = tmp_path / "malbolge-tidy.dll"
    _ = broken_plugin.write_bytes(b"not a Windows plugin")
    accepted = tidy_toolchain.ROOT / "tests/tidy/accepted/abi_layout.c"
    monkeypatch.setattr(validate_main, "PLUGIN_LIBRARY", broken_plugin)
    monkeypatch.setattr(sys, "argv", ["validate", str(accepted)])

    assert validate_main.main() == CONFIGURATION_ERROR_STATUS
    assert PLUGIN_MISMATCH in capsys.readouterr().err
    assert identity.plugin_host.is_file()


def test_built_host_has_pinned_clang_resource_headers() -> None:
    """Generated host layout carries the Clang builtin include resource."""
    identity = _built_plugin_identity()
    resource = identity.plugin_output_root / "lib" / "clang" / "22"

    assert (resource / "include" / "limits.h").is_file()


def test_built_plugin_registers_only_reviewed_malbolge_checks() -> None:
    """The canonical DLL contributes the closed reviewed Malbolge check set."""
    identity = _built_plugin_identity()
    completed = sp.run(  # ruff: ignore[subprocess-without-shell-equals-true]
        [
            str(identity.plugin_host),
            f"--load={identity.plugin_library}",
            "--checks=-*,malbolge-*",
            "--list-checks",
        ],
        cwd=tidy_toolchain.ROOT,
        check=False,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        shell=False,
    )
    assert completed.returncode == 0, completed.stderr
    observed = {
        line.strip()
        for line in completed.stdout.splitlines()
        if line.strip().startswith("malbolge-")
    }
    assert observed == set(identity.plugin_checks)


def test_built_plugin_accepts_and_rejects_fixture_boundary() -> None:
    """The real DLL emits deterministic source-located ABI diagnostics."""
    identity = _built_plugin_identity()
    resource = identity.runtime_root / "lib" / "clang" / "22"
    common = [
        str(identity.plugin_host),
        f"--load={identity.plugin_library}",
        "--checks=-*,malbolge-abi-bit-field",
        "--warnings-as-errors=malbolge-abi-bit-field",
    ]
    compile_args = [
        "--",
        f"-resource-dir={resource}",
        "-x",
        "c",
        "--target=wasm32-unknown-unknown",
        "-std=c23",
        "-ffreestanding",
        "-fno-builtin",
        "-pedantic-errors",
    ]
    accepted = sp.run(  # ruff: ignore[subprocess-without-shell-equals-true]
        [
            *common,
            str(tidy_toolchain.ROOT / "tests/tidy/accepted/abi_layout.c"),
            *compile_args,
        ],
        cwd=tidy_toolchain.ROOT,
        check=False,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        shell=False,
    )
    assert accepted.returncode == 0, accepted.stderr

    rejected_path = tidy_toolchain.ROOT / "tests/tidy/rejected/abi_bit_field.c"
    rejected = sp.run(  # ruff: ignore[subprocess-without-shell-equals-true]
        [*common, str(rejected_path), *compile_args],
        cwd=tidy_toolchain.ROOT,
        check=False,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        shell=False,
    )
    assert rejected.returncode != 0
    diagnostics = rejected.stdout + rejected.stderr
    assert BIT_FIELD_CODE in diagnostics
    assert BIT_FIELD_WARNING in diagnostics
    assert BIT_FIELD_LOCATION in diagnostics


@pytest.mark.parametrize(("fixture", "code", "check"), PLUGIN_REJECTIONS)
def test_built_plugin_rejects_all_reviewed_abi_exclusions(
    fixture: str,
    code: str,
    check: str,
) -> None:
    """Every canonical ABI exclusion is independently enforced by the DLL."""
    identity = _built_plugin_identity()
    resource = identity.runtime_root / "lib" / "clang" / "22"
    corpus = (
        "plugin-rejected"
        if fixture == IMPORTED_ALIAS_FIXTURE
        else "rejected"
    )
    source = tidy_toolchain.ROOT / "tests" / "tidy" / corpus / fixture
    completed = sp.run(  # ruff: ignore[subprocess-without-shell-equals-true]
        [
            str(identity.plugin_host),
            f"--load={identity.plugin_library}",
            "--checks=-*,malbolge-*",
            "--warnings-as-errors=malbolge-*",
            str(source),
            "--",
            f"-resource-dir={resource}",
            "-x",
            "c",
            "--target=wasm32-unknown-unknown",
            "-std=c23",
            "-ffreestanding",
            "-fno-builtin",
            "-pedantic-errors",
        ],
        cwd=tidy_toolchain.ROOT,
        check=False,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        shell=False,
    )
    assert completed.returncode != 0
    diagnostics = completed.stdout + completed.stderr
    assert code in diagnostics
    assert f"[{check},-warnings-as-errors]" in diagnostics
    assert fixture in diagnostics


def test_manual_validator_loads_built_plugin_additively() -> None:
    """Manual validation adds plugin checks without dropping stock checks."""
    identity = _built_plugin_identity()
    validator = (
        tidy_toolchain.ROOT
        / "src/automation/repository/composition/scripts/validate/main.py"
    )
    accepted = tidy_toolchain.ROOT / "tests/tidy/accepted/abi_layout.c"
    completed = sp.run(  # ruff: ignore[subprocess-without-shell-equals-true]
        [
            sys.executable,
            str(validator),
            "--clang-tidy",
            str(identity.plugin_host),
            "--plugin",
            str(identity.plugin_library),
            str(accepted),
        ],
        cwd=tidy_toolchain.ROOT,
        check=False,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        shell=False,
    )
    assert completed.returncode == 0, completed.stderr


def test_manual_validator_rejects_loader_without_plugin_registry() -> None:
    """The upstream Windows executable cannot silently bypass plugin checks."""
    identity = _built_plugin_identity()
    validator = (
        tidy_toolchain.ROOT
        / "src/automation/repository/composition/scripts/validate/main.py"
    )
    accepted = tidy_toolchain.ROOT / "tests/tidy/accepted/abi_layout.c"
    completed = sp.run(  # ruff: ignore[subprocess-without-shell-equals-true]
        [
            sys.executable,
            str(validator),
            "--clang-tidy",
            str(identity.clang_tidy),
            "--plugin",
            str(identity.plugin_library),
            str(accepted),
        ],
        cwd=tidy_toolchain.ROOT,
        check=False,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        shell=False,
    )
    assert completed.returncode == CONFIGURATION_ERROR_STATUS
    assert PLUGIN_MISMATCH in completed.stderr
    assert OBSERVED_NONE in completed.stderr
