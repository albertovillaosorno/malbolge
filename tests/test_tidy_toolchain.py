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
import io
import json
import os
from pathlib import Path
import subprocess as sp  # ruff: ignore[suspicious-subprocess-import]
import sys
from typing import Self
from typing import TYPE_CHECKING
from typing import cast
from typing import final
from typing import override

if TYPE_CHECKING:
    from collections.abc import Callable

import pytest

from scripts.validate import main as validate_main
from scripts.validate import tidy_build
from scripts.validate import tidy_build_linux
from scripts.validate import tidy_toolchain

EXPECTED_ASSET = "clang+llvm-22.1.8-x86_64-pc-windows-msvc.tar.xz"
EXPECTED_SHA256 = (
    "d96c2cc1736f4eb7fa43cb9bbdf56d93"
    "551a9ae0a9aadb9c99c3c3b2b712a234"
)
EXPECTED_SIZE = 862053924
LINUX_PLATFORM = "linux-x86_64"
WINDOWS_PLATFORM = "windows-x86_64"
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


class UntrustedHostFormatterError(TypeError):
    """Synthetic host failure whose text formatter must never be invoked."""

    @override
    def __str__(self) -> str:
        """Fail if an untrusted exception formatter is executed.

        Raises:
            AssertionError: The toolchain validator invoked foreign formatting.

        """
        message = "foreign LLVM host error formatter executed"
        raise AssertionError(message)


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


@pytest.mark.parametrize("entrypoint", ["document", "identity"])
def test_toolchain_manifest_decoder_corroborates_original_plugin_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    entrypoint: str,
) -> None:
    """An injected JSON loader cannot replace the reviewed plugin identity."""
    source = _canonical_document()
    original_windows = cast(
        "dict[str, object]",
        cast("dict[str, object]", source["platforms"])[WINDOWS_PLATFORM],
    )
    assert original_windows["plugin_library"] == "bin/malbolge-tidy.dll"
    manifest = _write_manifest(tmp_path, source)
    forged = _canonical_document()
    platforms = cast("dict[str, object]", forged["platforms"])
    windows = cast("dict[str, object]", platforms[WINDOWS_PLATFORM])
    windows["plugin_library"] = "bin/foreign-toolchain.dll"

    def forged_loads(_text: str, *, object_pairs_hook: object) -> object:
        del object_pairs_hook
        return forged

    monkeypatch.setattr(json, "loads", forged_loads)
    with pytest.raises(
        tidy_toolchain.ToolchainError,
        match="JSON decoder provider differs from source",
    ):
        if entrypoint == "document":
            _ = tidy_toolchain._document(manifest)  # pyright: ignore[reportPrivateUsage]
        else:
            _ = tidy_toolchain.load_identity(manifest, root=tmp_path)


def test_toolchain_manifest_decoder_accepts_equivalent_adapter(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """An equivalent native adapter remains compatible with source identity."""
    manifest = _write_manifest(tmp_path, _canonical_document())
    original_loads = json.loads

    def delegated(text: str, *, object_pairs_hook: object) -> object:
        return original_loads(
            text,
            object_pairs_hook=cast(
                "Callable[[list[tuple[str, object]]], object]", object_pairs_hook
            ),
        )

    monkeypatch.setattr(json, "loads", delegated)
    identity = tidy_toolchain.load_identity(manifest, root=tmp_path)
    assert identity.plugin_library.name == "malbolge-tidy.dll"


def test_toolchain_manifest_decoder_rejects_lied_about_invalid_source(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """A forged native document cannot override original JSON syntax errors."""
    forged = _canonical_document()
    source = tmp_path / "invalid.json"
    _ = source.write_text('{"schema_version": 2,,}', encoding="utf-8")

    def fabricated(_text: str, *, object_pairs_hook: object) -> object:
        del object_pairs_hook
        return forged

    monkeypatch.setattr(json, "loads", fabricated)
    with pytest.raises(tidy_toolchain.ToolchainError, match="cannot read") as caught:
        _ = tidy_toolchain.load_identity(source, root=tmp_path)
    assert type(caught.value.__cause__) is json.JSONDecodeError


def test_toolchain_manifest_decoder_refuses_foreign_keys_without_equality(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """A foreign nested key must not run equality during source comparison."""

    class ForeignKey(str):
        @override
        def __hash__(self) -> int:
            return str.__hash__(self)

        @override
        def __eq__(self, other: object) -> bool:
            del other
            raise AssertionError("foreign LLVM toolchain key equality executed")

    native = _canonical_document()
    forged = _canonical_document()
    platforms = cast("dict[str, object]", forged["platforms"])
    windows = cast("dict[str, object]", platforms[WINDOWS_PLATFORM])
    library = windows.pop("plugin_library")
    windows[ForeignKey("plugin_library")] = library
    manifest = _write_manifest(tmp_path, native)

    def fabricated(_text: str, *, object_pairs_hook: object) -> object:
        del object_pairs_hook
        return forged

    monkeypatch.setattr(json, "loads", fabricated)
    with pytest.raises(
        tidy_toolchain.ToolchainError, match="JSON decoder provider differs"
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


@pytest.mark.parametrize(
    ("section", "field"),
    (
        ("toolchain", "runtime_root"),
        ("toolchain", "development_root"),
        ("toolchain", "plugin_output_root"),
        ("platform", "clang"),
        ("platform", "plugin_host"),
        ("platform", "plugin_library"),
        ("platform-list", "required_runtime_files"),
        ("platform-list", "required_development_files"),
    ),
)
def test_toolchain_manifest_rejects_host_dependent_backslash_paths(
    tmp_path: Path,
    section: str,
    field: str,
) -> None:
    """Pinned tools must resolve the same path on Linux and Windows."""
    document = _canonical_document()
    selected = document
    if section != "toolchain":
        platforms = cast("dict[str, object]", document["platforms"])
        selected = cast("dict[str, object]", platforms[WINDOWS_PLATFORM])
    if section == "platform-list":
        paths = cast("list[str]", selected[field])
        paths[0] = paths[0].replace("/", "\\")
    else:
        value = cast("str", selected[field])
        selected[field] = value.replace("/", "\\")
    manifest = _write_manifest(tmp_path, document)
    with pytest.raises(
        tidy_toolchain.ToolchainError,
        match="must use forward slashes",
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


def test_manifest_rejects_symlinked_leaf_and_parent(tmp_path: Path) -> None:
    """Manifest evidence cannot originate through redirected authority paths."""
    source = _write_manifest(tmp_path, _canonical_document())
    alias = tmp_path / "alias.json"
    parent = tmp_path / "alias-directory"
    try:
        alias.symlink_to(source)
        parent.symlink_to(tmp_path, target_is_directory=True)
    except (OSError, NotImplementedError) as error:
        pytest.skip(f"symlinks unavailable: {error}")
    for path in (alias, parent / source.name):
        with pytest.raises(
            tidy_toolchain.ToolchainError, match=r"redirect|regular"
        ):
            _ = tidy_toolchain.load_identity(path, root=tmp_path)


def test_archive_verification_rejects_symlinked_leaf_and_parent(
    tmp_path: Path,
) -> None:
    """Matching archive digests cannot legitimate redirected source paths."""
    payload = b"reviewed LLVM development archive"
    archive = tmp_path / "llvm.tar.xz"
    _ = archive.write_bytes(payload)
    identity = replace(
        tidy_toolchain.load_identity(root=tmp_path),
        asset_sha256=hashlib.sha256(payload).hexdigest(),
        asset_size_bytes=len(payload),
    )
    alias = tmp_path / "linked.tar.xz"
    parent = tmp_path / "linked-directory"
    try:
        alias.symlink_to(archive)
        parent.symlink_to(tmp_path, target_is_directory=True)
    except (OSError, NotImplementedError) as error:
        pytest.skip(f"symlinks unavailable: {error}")
    for path in (alias, parent / archive.name):
        with pytest.raises(
            tidy_toolchain.ToolchainError, match=r"redirect|regular"
        ):
            tidy_toolchain.verify_archive(path, identity)


def test_manifest_rejects_special_and_oversized_file(tmp_path: Path) -> None:
    """Malformed manifest path cannot hang or exhaust JSON admission."""
    with pytest.raises(tidy_toolchain.ToolchainError, match="regular"):
        _ = tidy_toolchain.load_identity(tmp_path, root=tmp_path)
    oversized = tmp_path / "oversized.json"
    with oversized.open("wb") as stream:
        _ = stream.truncate(tidy_toolchain.MAX_MANIFEST_BYTES + 1)
    with pytest.raises(tidy_toolchain.ToolchainError, match="byte limit"):
        _ = tidy_toolchain.load_identity(oversized, root=tmp_path)
    with pytest.raises(tidy_toolchain.ToolchainError, match="cannot read"):
        _ = tidy_toolchain.load_identity(
            tmp_path / "absent.json", root=tmp_path
        )


def test_manifest_rejects_invalid_utf8_as_toolchain_error(
    tmp_path: Path,
) -> None:
    """Invalid UTF-8 is a closed toolchain error, not an uncaught decoder."""
    manifest = tmp_path / "llvm.json"
    _ = manifest.write_bytes(b"{\xff}")
    with pytest.raises(tidy_toolchain.ToolchainError, match="cannot read"):
        _ = tidy_toolchain.load_identity(manifest, root=tmp_path)


def test_manifest_rejects_fifo_without_waiting_for_writer(
    tmp_path: Path,
) -> None:
    """A manifest FIFO cannot block a verifier awaiting an external writer."""
    mkfifo = cast("Callable[[Path], None] | None", getattr(os, "mkfifo", None))
    if mkfifo is None:
        pytest.skip("FIFO not supported on this host")
    fifo = tmp_path / "llvm.json"
    mkfifo(fifo)
    with pytest.raises(tidy_toolchain.ToolchainError, match="regular"):
        _ = tidy_toolchain.load_identity(fifo, root=tmp_path)


def test_manifest_rejects_same_byte_inode_swap_before_open(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A same-byte manifest replacement between lstat and open is rejected."""
    source = _write_manifest(tmp_path, _canonical_document())
    replacement = tmp_path / "replacement.json"
    _ = replacement.write_bytes(source.read_bytes())
    real_open = os.open
    swapped = False

    def swap_on_open(path: Path, flags: int) -> int:
        nonlocal swapped
        if path == source:
            _ = replacement.replace(source)
            swapped = True
        return real_open(path, flags)

    monkeypatch.setattr(os, "open", swap_on_open)
    with pytest.raises(
        tidy_toolchain.ToolchainError, match="changed before read"
    ):
        _ = tidy_toolchain.load_identity(source, root=tmp_path)
    assert swapped


def test_manifest_rejects_same_byte_swap_after_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An identically valid replacement invalidates the read manifest."""
    source = _write_manifest(tmp_path, _canonical_document())
    replacement = tmp_path / "replacement.json"
    _ = replacement.write_bytes(source.read_bytes())
    real_open = os.open
    real_lstat = Path.lstat
    opened = swapped = False

    def track_open(path: Path, flags: int) -> int:
        nonlocal opened
        descriptor = real_open(path, flags)
        if path == source:
            opened = True
        return descriptor

    def swap_at_recheck(path: Path) -> os.stat_result:
        nonlocal swapped
        if path == source and opened and not swapped:
            _ = replacement.replace(source)
            swapped = True
        return real_lstat(path)

    monkeypatch.setattr(os, "open", track_open)
    monkeypatch.setattr(Path, "lstat", swap_at_recheck)
    with pytest.raises(
        tidy_toolchain.ToolchainError, match="changed during read"
    ):
        _ = tidy_toolchain.load_identity(source, root=tmp_path)
    assert swapped


@pytest.mark.parametrize("source_kind", ["manifest", "archive"])
@pytest.mark.parametrize("fault_point", ["fdopen", "fstat"])
@pytest.mark.parametrize(
    "fault_type",
    [OSError, ValueError, TypeError, RuntimeError, UntrustedHostFormatterError],
)
def test_tidy_source_stream_fault_closes_owned_descriptor(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    source_kind: str,
    fault_point: str,
    fault_type: type[Exception],
) -> None:
    """A failed source wrapper or admission cannot leak its descriptor."""
    identity = tidy_toolchain.load_identity(root=tmp_path)
    if source_kind == "manifest":
        source = _write_manifest(tmp_path, _canonical_document())
    else:
        source = tmp_path / "archive.tar.xz"
        _ = source.write_bytes(b"reviewed archive")
    native_open = os.open
    native_fdopen = os.fdopen
    native_fstat = os.fstat
    descriptors: list[int] = []
    fault = fault_type("injected LLVM source wrapper failure")

    def capture_open(path: Path, flags: int) -> int:
        descriptor = native_open(path, flags)
        if path == source:
            descriptors.append(descriptor)
        return descriptor

    def reject_fdopen(descriptor: int, mode: str) -> object:
        if fault_point == "fdopen" and descriptor in descriptors and mode == "rb":
            raise fault
        return native_fdopen(descriptor, mode)

    def reject_fstat(descriptor: int) -> os.stat_result:
        if fault_point == "fstat" and descriptor in descriptors:
            raise fault
        return native_fstat(descriptor)

    monkeypatch.setattr(os, "open", capture_open)
    monkeypatch.setattr(os, "fdopen", reject_fdopen)
    monkeypatch.setattr(os, "fstat", reject_fstat)
    try:
        with pytest.raises(
            tidy_toolchain.ToolchainError, match="cannot read"
        ) as caught:
            if source_kind == "manifest":
                _ = tidy_toolchain.load_identity(source, root=tmp_path)
            else:
                tidy_toolchain.verify_archive(source, identity)
        assert caught.value.__cause__ is fault
        assert len(descriptors) == 1
        with pytest.raises(OSError, match="Bad file descriptor|Invalid handle"):
            _ = native_fstat(descriptors[0])
    finally:
        for descriptor in descriptors:
            try:
                os.close(descriptor)
            except OSError:
                pass


def test_archive_rejects_fifo_without_waiting_for_writer(
    tmp_path: Path,
) -> None:
    """The archive digest reader refuses pipes before streaming a hash."""
    mkfifo = cast("Callable[[Path], None] | None", getattr(os, "mkfifo", None))
    if mkfifo is None:
        pytest.skip("FIFO not supported on this host")
    fifo = tmp_path / "archive.tar.xz"
    mkfifo(fifo)
    identity = tidy_toolchain.load_identity(root=tmp_path)
    with pytest.raises(tidy_toolchain.ToolchainError, match="regular"):
        tidy_toolchain.verify_archive(fifo, identity)


def test_archive_rejects_same_byte_swap_after_hash(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Digest equality alone cannot admit a replaced archive inode."""
    payload = b"reviewed LLVM development archive"
    source = tmp_path / "archive.tar.xz"
    _ = source.write_bytes(payload)
    replacement = tmp_path / "replacement.tar.xz"
    _ = replacement.write_bytes(payload)
    identity = replace(
        tidy_toolchain.load_identity(root=tmp_path),
        asset_sha256=hashlib.sha256(payload).hexdigest(),
        asset_size_bytes=len(payload),
    )
    real_open = os.open
    real_lstat = Path.lstat
    opened = swapped = False

    def track_open(path: Path, flags: int) -> int:
        nonlocal opened
        descriptor = real_open(path, flags)
        if path == source:
            opened = True
        return descriptor

    def swap_at_recheck(path: Path) -> os.stat_result:
        nonlocal swapped
        if path == source and opened and not swapped:
            _ = replacement.replace(source)
            swapped = True
        return real_lstat(path)

    monkeypatch.setattr(os, "open", track_open)
    monkeypatch.setattr(Path, "lstat", swap_at_recheck)
    with pytest.raises(
        tidy_toolchain.ToolchainError, match="changed during read"
    ):
        tidy_toolchain.verify_archive(source, identity)
    assert swapped


def test_archive_rejects_in_place_mutation_after_hash(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Even a same-size in-place edit invalidates the stream digest."""
    payload = b"reviewed LLVM development archive"
    source = tmp_path / "archive.tar.xz"
    _ = source.write_bytes(payload)
    identity = replace(
        tidy_toolchain.load_identity(root=tmp_path),
        asset_sha256=hashlib.sha256(payload).hexdigest(),
        asset_size_bytes=len(payload),
    )
    real_open = os.open
    real_lstat = Path.lstat
    opened = False
    modified = False

    def track_open(path: Path, flags: int) -> int:
        nonlocal opened
        descriptor = real_open(path, flags)
        if path == source:
            opened = True
        return descriptor

    def modify_at_recheck(path: Path) -> os.stat_result:
        nonlocal modified
        if path == source and opened and not modified:
            with source.open("r+b") as stream:
                _ = stream.write(b"x")
            modified = True
        return real_lstat(path)

    monkeypatch.setattr(os, "open", track_open)
    monkeypatch.setattr(Path, "lstat", modify_at_recheck)
    with pytest.raises(
        tidy_toolchain.ToolchainError, match="changed during read"
    ):
        tidy_toolchain.verify_archive(source, identity)
    assert modified


def test_archive_rejects_missing_and_size_mismatch(tmp_path: Path) -> None:
    """Archive verifier reports path I/O and size failures as typed errors."""
    identity = tidy_toolchain.load_identity(root=tmp_path)
    with pytest.raises(tidy_toolchain.ToolchainError, match="cannot read"):
        tidy_toolchain.verify_archive(tmp_path / "missing.tar.xz", identity)
    archive = tmp_path / "wrong-size.tar.xz"
    _ = archive.write_bytes(b"tiny")
    with pytest.raises(tidy_toolchain.ToolchainError, match="size mismatch"):
        tidy_toolchain.verify_archive(archive, identity)


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
    """Installed optional LLVM roots match the exact host identity."""
    identity = tidy_toolchain.load_identity(
        platform_id=tidy_toolchain.host_platform_id()
    )
    runtime_ready = identity.runtime_root.is_dir()
    development_ready = identity.development_root.is_dir()
    installed = runtime_ready and development_ready
    if not installed:
        pytest.skip("optional local LLVM development kit is absent")

    tidy_toolchain.validate_installation(identity)


def test_linux_builder_produces_loadable_plugin_when_dev_kit_present() -> None:
    """Exact Linux development inputs build the reviewed clang-tidy module."""
    platform_id = tidy_toolchain.host_platform_id()
    if platform_id != LINUX_PLATFORM:
        pytest.skip("live Linux native-analysis build requires linux-x86_64")
    identity = tidy_toolchain.load_identity(platform_id=platform_id)
    roots_ready = (
        identity.development_root.is_dir() and identity.runtime_root.is_dir()
    )
    if not roots_ready:
        pytest.skip("optional local Linux LLVM development kit is absent")
    try:
        _ = tidy_build_linux.linux_build_tools()
    except tidy_build_linux.LinuxBuildError as error:
        pytest.skip(f"Linux native build tools are unavailable: {error}")

    tidy_build.build(identity)
    tidy_build.provision_clang_resources(identity)
    tidy_build.verify_outputs(identity)
    assert identity.plugin_library.is_file()


def _built_plugin_identity() -> tidy_toolchain.ToolchainIdentity:
    identity = tidy_toolchain.load_identity(
        platform_id=tidy_toolchain.host_platform_id()
    )
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
    """The default project host probes its paired plugin before validation."""
    identity = _built_plugin_identity()
    broken_plugin = tmp_path / identity.plugin_library.name
    _ = broken_plugin.write_bytes(b"not a Windows plugin")
    accepted = tidy_toolchain.ROOT / "tests/tidy/accepted/abi_layout.c"
    monkeypatch.setattr(validate_main, "PLUGIN_LIBRARY", broken_plugin)
    monkeypatch.setattr(sys, "argv", ["validate", str(accepted)])

    assert validate_main.main() == CONFIGURATION_ERROR_STATUS
    assert PLUGIN_MISMATCH in capsys.readouterr().err
    assert identity.plugin_host.is_file()


def test_built_host_has_pinned_clang_resource_headers() -> None:
    """Selected host resolves the exact repository-local Clang resources."""
    identity = _built_plugin_identity()
    resource_root = (
        identity.runtime_root
        if identity.platform_id == LINUX_PLATFORM
        else identity.plugin_output_root
    )
    resource = resource_root / "lib" / "clang" / "22"

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


@pytest.mark.skipif(
    tidy_toolchain.host_platform_id() != WINDOWS_PLATFORM,
    reason="registry-bridge bypass is specific to the Windows project host",
)
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


SOURCE_MANIFEST = "manifest"
READ_TEXT = "text"
READ_BYTES_SUBCLASS = "bytes-subclass"
EXPECTED_LLVM_PROBE = "clang version 22.1.8\nwarning"
FORGED_SUCCESS = False


class ForgedVersionReceipt:
    """Untrusted process evidence whose fields cannot be inspected."""

    @property
    def returncode(self) -> int:
        """Reject inspection of a foreign process receipt.

        Raises:
            AssertionError: The unvalidated field was accessed.

        """
        message = "foreign LLVM process receipt accessed"
        raise AssertionError(message)


def _mock_version_run(monkeypatch: pytest.MonkeyPatch, receipt: object) -> None:
    def fake_run(*args: object, **kwargs: object) -> object:
        del args, kwargs
        return receipt

    monkeypatch.setattr(sp, "run", fake_run)


@pytest.mark.parametrize(
    "receipt",
    [
        ForgedVersionReceipt(),
        sp.CompletedProcess(
            ["clang"], FORGED_SUCCESS, "clang version 22.1.8", ""
        ),
        sp.CompletedProcess(
            ["clang"], cast("int", 0.0), "clang version 22.1.8", ""
        ),
        sp.CompletedProcess(
            ["clang"],
            cast("int", cast("object", "0")),
            "clang version 22.1.8",
            "",
        ),
        sp.CompletedProcess(["clang"], 0, b"clang version 22.1.8", ""),
        sp.CompletedProcess(["clang"], 0, "clang version 22.1.8", None),
        sp.CompletedProcess(["clang"], 0, "clang version 22.1.8", b""),
    ],
)
def test_llvm_version_probe_rejects_foreign_process_receipts(
    monkeypatch: pytest.MonkeyPatch,
    receipt: object,
) -> None:
    """Only exact native process success and text can prove an LLVM version."""
    _mock_version_run(monkeypatch, receipt)
    with pytest.raises(
        tidy_toolchain.ToolchainError, match="invalid LLVM version"
    ):
        _ = tidy_toolchain._tool_output(Path("clang"))  # ruff: ignore[private-member-access]  # pyright: ignore[reportPrivateUsage]


@pytest.mark.parametrize(
    "fault_type",
    [OSError, ValueError, TypeError, RuntimeError, UntrustedHostFormatterError],
)
def test_llvm_version_probe_wraps_host_failures(
    monkeypatch: pytest.MonkeyPatch,
    fault_type: type[Exception],
) -> None:
    """Version-probe host faults preserve their cause without foreign hooks."""
    fault = fault_type("injected LLVM version execution failure")

    def failed_run(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise fault

    monkeypatch.setattr(sp, "run", failed_run)
    with pytest.raises(
        tidy_toolchain.ToolchainError, match="failed to execute"
    ) as caught:
        _ = tidy_toolchain._tool_output(Path("clang"))  # ruff: ignore[private-member-access]  # pyright: ignore[reportPrivateUsage]
    assert caught.value.__cause__ is fault


def test_llvm_version_probe_keeps_native_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Exact native subprocess results preserve the readable version text."""
    receipt = sp.CompletedProcess(
        ["clang", "--version"], 0, "clang version 22.1.8", "warning"
    )
    _mock_version_run(monkeypatch, receipt)
    output = tidy_toolchain._tool_output(Path("clang"))  # ruff: ignore[private-member-access]  # pyright: ignore[reportPrivateUsage]
    assert output == EXPECTED_LLVM_PROBE


class ForgedLLVMStat:
    """Foreign filesystem metadata must never supply source authority."""

    @property
    def st_mode(self) -> int:
        """Reject inspection of a foreign stat receipt.

        Raises:
            AssertionError: The unvalidated field was accessed.

        """
        message = "foreign LLVM stat fields accessed"
        raise AssertionError(message)


def _tidy_source_case(
    tmp_path: Path, source_kind: str
) -> tuple[Path, tidy_toolchain.ToolchainIdentity]:
    identity = tidy_toolchain.load_identity(root=tmp_path)
    if source_kind == SOURCE_MANIFEST:
        source = _write_manifest(tmp_path, _canonical_document())
    else:
        source = tmp_path / "llvm.tar.xz"
        _ = source.write_bytes(b"reviewed archive")
    return source, identity


def _verify_tidy_source(
    source: Path,
    identity: tidy_toolchain.ToolchainIdentity,
    source_kind: str,
) -> None:
    if source_kind == SOURCE_MANIFEST:
        _ = tidy_toolchain.load_identity(source, root=source.parent)
    else:
        tidy_toolchain.verify_archive(source, identity)


@pytest.mark.parametrize("source_kind", [SOURCE_MANIFEST, "archive"])
def test_tidy_source_rejects_foreign_stat_without_field_access(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    source_kind: str,
) -> None:
    """Neither JSON nor archive evidence may trust foreign lstat results."""
    source, identity = _tidy_source_case(tmp_path, source_kind)
    native_lstat = Path.lstat

    def forged_lstat(path: Path) -> object:
        return ForgedLLVMStat() if path == source else native_lstat(path)

    monkeypatch.setattr(Path, "lstat", forged_lstat)
    with pytest.raises(tidy_toolchain.ToolchainError, match=r"invalid .*stat"):
        _verify_tidy_source(source, identity, source_kind)


@pytest.mark.parametrize("source_kind", [SOURCE_MANIFEST, "archive"])
def test_tidy_source_rejects_foreign_fstat_without_field_access(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    source_kind: str,
) -> None:
    """Opened descriptors require native file identity receipts."""
    source, identity = _tidy_source_case(tmp_path, source_kind)
    native_open, native_fstat = os.open, os.fstat
    opened_descriptors: list[int] = []

    def tracked_open(path: Path, flags: int) -> int:
        descriptor = native_open(path, flags)
        if path == source:
            opened_descriptors.append(descriptor)
        return descriptor

    def forged_fstat(descriptor: int) -> object:
        if descriptor in opened_descriptors:
            return ForgedLLVMStat()
        return native_fstat(descriptor)

    monkeypatch.setattr(os, "open", tracked_open)
    monkeypatch.setattr(os, "fstat", forged_fstat)
    with pytest.raises(tidy_toolchain.ToolchainError, match=r"invalid .*stat"):
        _verify_tidy_source(source, identity, source_kind)
    assert len(opened_descriptors) == 1
    with pytest.raises(OSError, match=r"Bad file descriptor|Invalid handle"):
        _ = native_fstat(opened_descriptors[0])


@pytest.mark.parametrize("source_kind", [SOURCE_MANIFEST, "archive"])
@pytest.mark.parametrize("receipt", [False, 0.0, "3", -1])
def test_tidy_source_rejects_foreign_open_descriptor_before_fdopen(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    source_kind: str,
    receipt: object,
) -> None:
    """Bogus descriptors cannot read arbitrary host streams including stdin."""
    source, identity = _tidy_source_case(tmp_path, source_kind)
    native_open = os.open

    def forged_open(path: Path, flags: int) -> object:
        return receipt if path == source else native_open(path, flags)

    def forbidden_fdopen(*args: object, **kwargs: object) -> None:
        del args, kwargs
        message = "foreign LLVM descriptor reached fdopen"
        raise AssertionError(message)

    monkeypatch.setattr(os, "open", forged_open)
    monkeypatch.setattr(os, "fdopen", forbidden_fdopen)
    with pytest.raises(
        tidy_toolchain.ToolchainError, match=r"invalid .*descriptor"
    ):
        _verify_tidy_source(source, identity, source_kind)


class ForeignReadBytes(bytes):
    """A bytes subclass may carry foreign evidence behavior."""

    @override
    def __len__(self) -> int:
        """Reject use of an untrusted byte-count hook.

        Raises:
            AssertionError: The byte subclass was inspected.

        """
        message = "foreign LLVM read byte count accessed"
        raise AssertionError(message)


class ForgedSourceReadStream:
    """Simulate one host stream with an untrusted read receipt."""

    def __init__(self, receipt: object) -> None:
        """Retain the forged read receipt."""
        self.receipt: object = receipt

    def __enter__(self) -> Self:
        """Enter the fake stream context.

        Returns:
            The stream itself.

        """
        return self

    def __exit__(self, *args: object) -> None:
        """Exit without external resources."""
        del args

    def read(self, size: int) -> object:
        """Return the forged receipt unchanged.

        Returns:
            Untrusted host data.

        """
        del size
        return self.receipt


@pytest.mark.parametrize("source_kind", [SOURCE_MANIFEST, "archive"])
@pytest.mark.parametrize(
    "receipt_kind", [READ_TEXT, READ_BYTES_SUBCLASS, "list"]
)
def test_tidy_source_rejects_foreign_read_receipt_before_use(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    source_kind: str,
    receipt_kind: str,
) -> None:
    """Only exact bytes can establish manifest content or archive hashes."""
    identity = tidy_toolchain.load_identity(root=tmp_path)
    source = tmp_path / "source.bin"
    payload = b"reviewed archive"
    _ = source.write_bytes(payload)
    identity = replace(identity, asset_size_bytes=len(payload))
    receipts: dict[str, object] = {
        READ_TEXT: payload.decode("ascii"),
        READ_BYTES_SUBCLASS: ForeignReadBytes(payload),
        "list": list(payload),
    }

    def forged_source(
        *args: object, **kwargs: object
    ) -> tuple[object, os.stat_result]:
        del args, kwargs
        return ForgedSourceReadStream(receipts[receipt_kind]), source.lstat()

    monkeypatch.setattr(tidy_toolchain, "_open_regular_source", forged_source)
    with pytest.raises(tidy_toolchain.ToolchainError, match=r"invalid .*bytes"):
        _verify_tidy_source(source, identity, source_kind)


class ForeignLLVMHostOSError(OSError):
    """A foreign OSError whose formatter cannot be trusted."""

    @override
    def __str__(self) -> str:
        """Reject attempts to execute foreign host formatting.

        Raises:
            AssertionError: The foreign formatter was invoked.

        """
        message = "foreign LLVM filesystem error formatter executed"
        raise AssertionError(message)


@pytest.mark.parametrize("source_kind", [SOURCE_MANIFEST, "archive"])
@pytest.mark.parametrize(
    "fault_type",
    [
        OSError,
        ValueError,
        TypeError,
        RuntimeError,
        ForeignLLVMHostOSError,
        UntrustedHostFormatterError,
    ],
)
def test_tidy_source_host_failure_preserves_safe_cause(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    source_kind: str,
    fault_type: type[Exception],
) -> None:
    """Manifest and archive host errors never run foreign formatters."""
    source, identity = _tidy_source_case(tmp_path, source_kind)
    native_lstat = Path.lstat
    fault = fault_type("injected LLVM filesystem failure")

    def fail_lstat(path: Path) -> os.stat_result:
        if path == source:
            raise fault
        return native_lstat(path)

    monkeypatch.setattr(Path, "lstat", fail_lstat)
    with pytest.raises(
        tidy_toolchain.ToolchainError, match="cannot read"
    ) as caught:
        _verify_tidy_source(source, identity, source_kind)
    assert caught.value.__cause__ is fault


class ForeignLLVMStreamWrapper:
    """A forged os.fdopen return object must not own a source descriptor."""

    def fileno(self) -> int:  # ruff: ignore[no-self-use]
        """Reject inspection of a foreign descriptor hook.

        Raises:
            AssertionError: An unvalidated wrapper was inspected.

        """
        message = "foreign LLVM stream wrapper inspected"
        raise AssertionError(message)


@pytest.mark.parametrize("source_kind", [SOURCE_MANIFEST, "archive"])
def test_tidy_source_rejects_foreign_stream_wrapper_and_closes_fd(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    source_kind: str,
) -> None:
    """Only native buffered streams may take ownership of source evidence."""
    source, identity = _tidy_source_case(tmp_path, source_kind)
    native_open, native_fdopen, native_fstat = os.open, os.fdopen, os.fstat
    opened_descriptors: list[int] = []

    def capture_open(path: Path, flags: int) -> int:
        descriptor = native_open(path, flags)
        if path == source:
            opened_descriptors.append(descriptor)
        return descriptor

    def fake_fdopen(descriptor: int, mode: str) -> object:
        if descriptor in opened_descriptors:
            return ForeignLLVMStreamWrapper()
        return native_fdopen(descriptor, mode)

    monkeypatch.setattr(os, "open", capture_open)
    monkeypatch.setattr(os, "fdopen", fake_fdopen)
    with pytest.raises(
        tidy_toolchain.ToolchainError, match=r"invalid .*stream wrapper"
    ):
        _verify_tidy_source(source, identity, source_kind)
    assert len(opened_descriptors) == 1
    with pytest.raises(OSError, match=r"Bad file descriptor|Invalid handle"):
        _ = native_fstat(opened_descriptors[0])


def test_tidy_manifest_decoder_preserves_native_cause(
    tmp_path: Path,
) -> None:
    """Invalid manifest UTF-8 retains the source decoder failure."""
    source = tmp_path / "invalid.json"
    _ = source.write_bytes(b"{\xff}")
    with pytest.raises(
        tidy_toolchain.ToolchainError, match="cannot read"
    ) as caught:
        _ = tidy_toolchain.load_identity(source, root=tmp_path)
    assert type(caught.value.__cause__) is UnicodeDecodeError


class ForeignLLVMRedirectReceipt:
    """A foreign path redirect result must not run its truthiness hook."""

    def __bool__(self) -> bool:
        """Reject use of an untrusted junction or symlink status.

        Raises:
            AssertionError: A foreign truthiness hook was invoked.

        """
        message = "foreign LLVM redirect truthiness hook executed"
        raise AssertionError(message)


REDIRECT_LEAF = "leaf"
REDIRECT_SYMLINK = "is_symlink"
REDIRECT_CASES = [
    (source_kind, scope, kind)
    for source_kind in (SOURCE_MANIFEST, "archive")
    for scope in (REDIRECT_LEAF, "parent")
    for kind in (REDIRECT_SYMLINK, "is_junction")
]


@pytest.mark.parametrize("case", REDIRECT_CASES)
@pytest.mark.parametrize(
    "receipt", [None, 0, 0.0, ForeignLLVMRedirectReceipt()]
)
def test_tidy_source_rejects_foreign_redirect_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    case: tuple[str, str, str],
    receipt: object,
) -> None:
    """Only exact host booleans may decide source path redirection."""
    source_kind, scope, kind = case
    source, identity = _tidy_source_case(tmp_path, source_kind)
    selected = source if scope == REDIRECT_LEAF else tmp_path
    native_status = (
        Path.is_symlink if kind == REDIRECT_SYMLINK else Path.is_junction
    )

    def forged_redirect(path: Path) -> object:
        return receipt if path == selected else native_status(path)

    monkeypatch.setattr(Path, kind, forged_redirect)
    with pytest.raises(
        tidy_toolchain.ToolchainError, match=r"invalid .*receipt"
    ):
        _verify_tidy_source(source, identity, source_kind)


@final
class ForeignLLVMArgv:
    """A foreign process argument receipt may have comparison hooks."""

    __hash__ = object.__hash__

    @override
    def __eq__(self, other: object) -> bool:
        """Reject invoking untrusted version process argument equality.

        Raises:
            AssertionError: A foreign command comparison was invoked.

        """
        del other
        message = "foreign LLVM argv equality executed"
        raise AssertionError(message)


@pytest.mark.parametrize(
    "argv",
    [
        ["other-tool", "--version"],
        ["clang", "--help"],
        ["clang", "--version", "--unknown"],
        ("clang", "--version"),
        ForeignLLVMArgv(),
        ["clang", cast("str", cast("object", b"--version"))],
    ],
)
def test_llvm_version_probe_rejects_wrong_command_receipts(
    monkeypatch: pytest.MonkeyPatch,
    argv: object,
) -> None:
    """A passing status for another invocation is not toolchain evidence."""
    receipt: sp.CompletedProcess[str] = sp.CompletedProcess(
        cast("list[str]", argv), 0, "clang version 22.1.8", ""
    )
    _mock_version_run(monkeypatch, receipt)
    with pytest.raises(
        tidy_toolchain.ToolchainError, match="invalid LLVM version"
    ):
        _ = tidy_toolchain._tool_output(Path("clang"))  # ruff: ignore[private-member-access]  # pyright: ignore[reportPrivateUsage]


class ForeignLLVMFileStatus:
    """A foreign required-file result must not supply executable readiness."""

    def __bool__(self) -> bool:
        """Reject use of foreign file-status truthiness.

        Raises:
            AssertionError: An untrusted host formatter was invoked.

        """
        message = "foreign LLVM required-file truthiness invoked"
        raise AssertionError(message)


def _require_llvm_fixture(root: Path, relative: Path) -> None:
    """Run the pinned required-runtime-file admission for one test path."""
    tidy_toolchain._require_files(  # ruff: ignore[private-member-access]  # pyright: ignore[reportPrivateUsage]
        root, (relative,), "LLVM runtime"
    )


@pytest.mark.parametrize("receipt", [1, 1.0, ForeignLLVMFileStatus()])
def test_tidy_required_file_rejects_foreign_is_file_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    receipt: object,
) -> None:
    """Required runtime evidence cannot rely on coerced file status."""
    path = tmp_path / "compiler"
    _ = path.write_bytes(b"native LLVM binary")
    native_is_file = Path.is_file

    def forged_is_file(candidate: Path) -> object:
        return receipt if candidate == path else native_is_file(candidate)

    monkeypatch.setattr(Path, "is_file", forged_is_file)
    with pytest.raises(
        tidy_toolchain.ToolchainError, match=r"invalid .*file status"
    ):
        _require_llvm_fixture(tmp_path, Path("compiler"))


@pytest.mark.parametrize("redirect_kind", ["leaf", "parent"])
def test_tidy_required_file_rejects_redirected_installation(
    tmp_path: Path,
    redirect_kind: str,
) -> None:
    """Executable readiness cannot borrow a linked local LLVM dependency."""
    real = tmp_path / "physical"
    real.mkdir()
    _ = (real / "compiler").write_bytes(b"native LLVM binary")
    if redirect_kind == REDIRECT_LEAF:
        linked = tmp_path / "compiler"
        target = real / "compiler"
        relative = Path("compiler")
    else:
        linked = tmp_path / "linked"
        target = real
        relative = Path("linked/compiler")
    try:
        linked.symlink_to(
            target,
            target_is_directory=(redirect_kind != REDIRECT_LEAF),
        )
    except (OSError, NotImplementedError) as error:
        pytest.skip(f"symlink unavailable: {error}")
    with pytest.raises(tidy_toolchain.ToolchainError, match="redirect"):
        _require_llvm_fixture(tmp_path, relative)


def test_tidy_required_file_rejects_foreign_stat_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Required executable metadata must be native, not foreign stat hooks."""
    path = tmp_path / "compiler"
    _ = path.write_bytes(b"native LLVM binary")
    native_lstat = Path.lstat

    def forged_lstat(candidate: Path) -> object:
        return (
            ForgedLLVMStat() if candidate == path else native_lstat(candidate)
        )

    monkeypatch.setattr(Path, "lstat", forged_lstat)
    with pytest.raises(tidy_toolchain.ToolchainError, match=r"invalid .*stat"):
        _require_llvm_fixture(tmp_path, Path("compiler"))


def test_tidy_required_file_accepts_physical_installed_file(
    tmp_path: Path,
) -> None:
    """An existing local physical file remains valid installation evidence."""
    _ = (tmp_path / "compiler").write_bytes(b"native LLVM binary")
    _require_llvm_fixture(tmp_path, Path("compiler"))


class ForeignToolchainCliError(tidy_toolchain.ToolchainError):
    """A foreign toolchain CLI failure with unsafe exception formatting."""

    @override
    def __str__(self) -> str:
        """Detect untrusted exception formatter access.

        Raises:
            AssertionError: The untrusted formatter was accessed.

        """
        message = "foreign toolchain CLI error formatter was invoked"
        raise AssertionError(message)


@pytest.mark.parametrize(
    ("failure_type", "expected_diagnostic"),
    [
        (tidy_toolchain.ToolchainError, "native LLVM validation failure"),
        (ForeignToolchainCliError, "ForeignToolchainCliError"),
    ],
)
def test_toolchain_cli_does_not_format_foreign_errors(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    *,
    failure_type: type[tidy_toolchain.ToolchainError],
    expected_diagnostic: str,
) -> None:
    """CLI reports exact built-in toolchain text without foreign hooks."""
    fault = failure_type("native LLVM validation failure")

    def fail_load() -> None:
        raise fault

    monkeypatch.setattr(tidy_toolchain, "load_identity", fail_load)
    assert tidy_toolchain.main([]) == 1
    assert expected_diagnostic in capsys.readouterr().err


EXPECTED_LLVM_VERSION_TIMEOUT_SECONDS = 15


def test_llvm_version_probe_bounds_unresponsive_host(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A hung LLVM version subprocess fails with typed original cause."""
    fault = sp.TimeoutExpired(
        ["clang", "--version"], EXPECTED_LLVM_VERSION_TIMEOUT_SECONDS
    )

    def timed_out_run(*args: object, **kwargs: object) -> None:
        del args
        assert kwargs["timeout"] == EXPECTED_LLVM_VERSION_TIMEOUT_SECONDS
        raise fault

    monkeypatch.setattr(sp, "run", timed_out_run)
    with pytest.raises(
        tidy_toolchain.ToolchainError, match="TimeoutExpired"
    ) as caught:
        _ = tidy_toolchain._tool_output(Path("clang"))  # ruff: ignore[private-member-access]  # pyright: ignore[reportPrivateUsage]
    assert caught.value.__cause__ is fault


CLI_SHORT = "short"
CLI_FOREIGN = "foreign"
CLI_BOOLEAN = "boolean"
CLI_MISSING = "missing"
CLI_FLUSH = "flush"
CLI_WRITE_ERROR = "write-error"
CLI_READY_PREFIX = "clang-tidy development toolchain ready:"
CLI_ARCHIVE_FLAG = "--archive"


class _ForeignCliCount(int):
    """A nonnative write result that must not certify CLI output."""


class _BrokenCliStream(io.StringIO):
    """Emulate a bad host output receipt at one deterministic stage."""

    def __init__(self, failure: str) -> None:
        super().__init__()
        self.failure: str = failure

    @override
    def write(self, message: str) -> int:
        if self.failure == CLI_WRITE_ERROR:
            detail = "injected CLI write failure"
            raise OSError(detail)
        forged: object = {
            CLI_SHORT: len(message) - 1,
            CLI_FOREIGN: _ForeignCliCount(len(message)),
            CLI_BOOLEAN: True,
            CLI_MISSING: None,
        }.get(self.failure, len(message))
        return cast("int", forged)

    @override
    def flush(self) -> None:
        if self.failure == CLI_FLUSH:
            return cast("None", object())
        return super().flush()


def _accept_toolchain_installation(
    _identity: tidy_toolchain.ToolchainIdentity,
) -> None:
    """Stand in for local optional LLVM installation during CLI tests."""


@pytest.mark.parametrize(
    "failure",
    [
        CLI_SHORT,
        CLI_FOREIGN,
        CLI_BOOLEAN,
        CLI_MISSING,
        CLI_FLUSH,
        CLI_WRITE_ERROR,
    ],
)
def test_toolchain_cli_rejects_incomplete_success_output(
    monkeypatch: pytest.MonkeyPatch,
    failure: str,
) -> None:
    """Readiness cannot be reported after unverified stdout delivery."""
    identity = tidy_toolchain.load_identity()
    monkeypatch.setattr(tidy_toolchain, "load_identity", lambda: identity)
    monkeypatch.setattr(
        tidy_toolchain, "validate_installation", _accept_toolchain_installation
    )
    monkeypatch.setattr(sys, "stdout", _BrokenCliStream(failure))
    assert tidy_toolchain.main([]) == 1


@pytest.mark.parametrize("failure", [CLI_SHORT, CLI_FLUSH, CLI_WRITE_ERROR])
def test_toolchain_cli_diagnostic_failure_stays_nonzero(
    monkeypatch: pytest.MonkeyPatch,
    failure: str,
) -> None:
    """A bad diagnostic stream must not replace the toolchain status."""

    def fail_load() -> None:
        detail = "invalid installation"
        raise tidy_toolchain.ToolchainError(detail)

    monkeypatch.setattr(tidy_toolchain, "load_identity", fail_load)
    monkeypatch.setattr(sys, "stderr", _BrokenCliStream(failure))
    assert tidy_toolchain.main([]) == 1


def test_toolchain_cli_native_output_still_succeeds(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A complete ordinary text receipt remains a successful CLI result."""
    identity = tidy_toolchain.load_identity()
    monkeypatch.setattr(tidy_toolchain, "load_identity", lambda: identity)
    monkeypatch.setattr(
        tidy_toolchain, "validate_installation", _accept_toolchain_installation
    )
    assert tidy_toolchain.main([]) == 0
    assert CLI_READY_PREFIX in capsys.readouterr().out


@pytest.mark.parametrize("failure", [CLI_SHORT, CLI_FLUSH, CLI_WRITE_ERROR])
def test_toolchain_cli_help_requires_complete_output(
    monkeypatch: pytest.MonkeyPatch,
    failure: str,
) -> None:
    """Argparse help cannot return success without an authentic delivery."""
    monkeypatch.setattr(sys, "stdout", _BrokenCliStream(failure))
    assert tidy_toolchain.main(["--help"]) == 1


def test_toolchain_cli_help_native_output(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Normal --help remains a successful argparse request."""
    with pytest.raises(SystemExit) as caught:
        _ = tidy_toolchain.main(["--help"])
    assert caught.value.code == 0
    assert CLI_ARCHIVE_FLAG in capsys.readouterr().out


@pytest.mark.parametrize("mutation", ("executable", "append", "remove"))
def test_llvm_version_probe_rejects_mutating_launch_wrapper(
    monkeypatch: pytest.MonkeyPatch, mutation: str
) -> None:
    """The expected version argv cannot be altered by its process launcher."""

    def run(args: list[str], **_kwargs: object) -> sp.CompletedProcess[str]:
        if mutation == "executable":
            args[0] = "foreign-clang"
        elif mutation == "append":
            args.append("--unexpected")
        else:
            _ = args.pop()
        return sp.CompletedProcess(
            args, 0, stdout="clang version 22.1.8", stderr=""
        )

    monkeypatch.setattr(sp, "run", run)
    with pytest.raises(tidy_toolchain.ToolchainError, match="process receipt"):
        _ = tidy_toolchain._tool_output(Path("clang"))  # ruff: ignore[private-member-access]  # pyright: ignore[reportPrivateUsage]
