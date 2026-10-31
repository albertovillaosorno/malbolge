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
#   - Cross-platform repository-local LLVM 22.1.8 bootstrap evidence.
# - Must-Not:
#   - Install system packages or use unversioned LLVM as validation authority.
# - Allows:
#   - Inputs: synthetic exact host LLVM observations and local package fixtures.
#   - Outputs: neutral executable aliases, local runtime/resources, readiness.
#   - Side effects: test-local files only.
# - Split-When:
#   - LLVM package downloading gains an independent lifecycle.
# - Merge-When:
#   - Project bootstrap tests own the same exact LLVM import boundary.
# - Summary:
#   - Proves Linux import and Windows neutral alias preservation for LLVM.
# - Description:
#   - Locks version, local runtime, wrapper, marker, and readiness contracts.
# - Usage:
#   - Collected without changing the host LLVM installation.
# - Defaults:
#   - Missing or wrong-version host LLVM remains unavailable.
#

"""Cross-platform repository-local LLVM 22.1.8 bootstrap evidence."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

import pytest
from scripts.bootstrap import llvm_validation

if TYPE_CHECKING:
    from pathlib import Path

LINUX_PLATFORM = "linux-x86_64"
WINDOWS_PLATFORM = "windows-x86_64"
LLVM_VERSION = "22.1.8"
CLANG_BYTES = b"clang-22"
TIDY_BYTES = b"clang-tidy-22"
FORMAT_BYTES = b"clang-format-22"
LLVM_BYTES = b"libLLVM"
CLANG_CPP_BYTES = b"libclang-cpp"
RESOURCE_BYTES = b"resource-header"
WRAPPER_LIBRARY_PATH = "LD_LIBRARY_PATH"
WRAPPER_CLANG_EXEC = 'exec "$ROOT/bin/clang" "$@"'


def _host_observation(tmp_path: Path) -> llvm_validation.LlvmHostObservation:
    host = tmp_path / "host"
    bin_dir = host / "bin"
    lib_dir = host / "lib"
    resource = host / "resource"
    bin_dir.mkdir(parents=True)
    lib_dir.mkdir()
    resource.mkdir()
    clang = bin_dir / "clang"
    tidy = bin_dir / "clang-tidy"
    formatter = bin_dir / "clang-format"
    llvm = lib_dir / "libLLVM.so.22.1"
    clang_cpp = lib_dir / "libclang-cpp.so.22.1"
    _ = clang.write_bytes(CLANG_BYTES)
    _ = tidy.write_bytes(TIDY_BYTES)
    _ = formatter.write_bytes(FORMAT_BYTES)
    _ = llvm.write_bytes(LLVM_BYTES)
    _ = clang_cpp.write_bytes(CLANG_CPP_BYTES)
    _ = (resource / "stddef.h").write_bytes(RESOURCE_BYTES)
    return llvm_validation.LlvmHostObservation(
        clang=clang,
        clang_format=formatter,
        clang_tidy=tidy,
        clang_cpp=clang_cpp,
        llvm=llvm,
        resource_dir=resource,
        version=LLVM_VERSION,
    )


def test_linux_import_materializes_local_runtime_and_neutral_aliases(
    tmp_path: Path,
) -> None:
    """Exact Linux LLVM imports binaries, libraries, resources, and wrappers."""
    observation = _host_observation(tmp_path)

    root = llvm_validation.import_linux_llvm(tmp_path, observation)

    assert (root / "bin/clang").read_bytes() == CLANG_BYTES
    assert (root / "bin/clang-tidy").read_bytes() == TIDY_BYTES
    assert (root / "bin/clang-format").read_bytes() == FORMAT_BYTES
    assert (root / "lib/libLLVM.so.22.1").read_bytes() == LLVM_BYTES
    assert (root / "lib/libclang-cpp.so.22.1").read_bytes() == CLANG_CPP_BYTES
    assert (root / "lib/clang/22/stddef.h").read_bytes() == RESOURCE_BYTES
    wrapper = (root / "jig-bin/clang.bin").read_text(encoding="utf-8")
    assert WRAPPER_LIBRARY_PATH in wrapper
    assert WRAPPER_CLANG_EXEC in wrapper
    assert (root / llvm_validation.LLVM_IMPORT_MARKER).is_file()
    assert llvm_validation.import_linux_llvm(tmp_path, observation) == root


def test_windows_aliases_preserve_existing_executable_bytes(
    tmp_path: Path,
) -> None:
    """Windows keeps native PE bytes while exposing neutral Jig aliases."""
    root = tmp_path / llvm_validation.LLVM_ROOT
    bin_dir = root / "bin"
    bin_dir.mkdir(parents=True)
    for name, payload in (
        ("clang.exe", CLANG_BYTES),
        ("clang-tidy.exe", TIDY_BYTES),
        ("clang-format.exe", FORMAT_BYTES),
    ):
        _ = (bin_dir / name).write_bytes(payload)

    aliases = llvm_validation.write_windows_llvm_aliases(root)

    assert tuple(path.name for path in aliases) == (
        "clang.bin",
        "clang-tidy.bin",
        "clang-format.bin",
    )
    assert aliases[0].read_bytes() == CLANG_BYTES
    assert aliases[1].read_bytes() == TIDY_BYTES
    assert aliases[2].read_bytes() == FORMAT_BYTES
    assert llvm_validation.inspect_llvm(tmp_path, WINDOWS_PLATFORM).ready


def test_inspection_requires_completed_neutral_aliases(tmp_path: Path) -> None:
    """Readiness never accepts a partial imported LLVM tree."""
    observation = _host_observation(tmp_path)
    missing = llvm_validation.inspect_llvm(tmp_path, LINUX_PLATFORM)
    root = llvm_validation.import_linux_llvm(tmp_path, observation)
    ready = llvm_validation.inspect_llvm(tmp_path, LINUX_PLATFORM)

    assert missing.ready is False
    assert ready.ready is True
    assert ready.path == root / "jig-bin/clang.bin"


def test_wrong_host_version_is_not_admitted() -> None:
    """A different host Clang release cannot satisfy the pinned toolchain."""
    assert llvm_validation.llvm_version_matches("clang version 22.1.8") is True
    assert llvm_validation.llvm_version_matches("clang version 22.1.7") is False


def test_linux_import_rejects_forged_existing_marker(tmp_path: Path) -> None:
    """A marker's presence cannot authorize an incomplete imported tree."""
    observation = _host_observation(tmp_path)
    destination = tmp_path / llvm_validation.LLVM_ROOT
    destination.mkdir(parents=True)
    _ = (destination / llvm_validation.LLVM_IMPORT_MARKER).write_bytes(
        b"unverified marker"
    )
    with pytest.raises(
        llvm_validation.LlvmImportError,
        match="without the exact import marker",
    ):
        _ = llvm_validation.import_linux_llvm(tmp_path, observation)
    assert not (destination / "jig-bin/clang.bin").exists()


def test_linux_import_rejects_incomplete_aliased_tool(tmp_path: Path) -> None:
    """A valid marker does not allow reuse if the imported Clang is missing."""
    observation = _host_observation(tmp_path)
    destination = llvm_validation.import_linux_llvm(tmp_path, observation)
    (destination / "bin/clang").unlink()
    with pytest.raises(
        llvm_validation.LlvmImportError,
        match="without the exact import marker",
    ):
        _ = llvm_validation.import_linux_llvm(tmp_path, observation)
    assert not llvm_validation.inspect_llvm(tmp_path, LINUX_PLATFORM).ready


def test_llvm_inspection_rejects_wrong_marker_content(tmp_path: Path) -> None:
    """Wrong release content cannot become ready from marker existence."""
    destination = llvm_validation.import_linux_llvm(
        tmp_path, _host_observation(tmp_path)
    )
    _ = (destination / llvm_validation.LLVM_IMPORT_MARKER).write_text(
        "llvm=22.1.7\nplatform=linux-x86_64\n",
        encoding="utf-8",
    )
    assert not llvm_validation.inspect_llvm(tmp_path, LINUX_PLATFORM).ready


def test_llvm_inspection_rejects_cross_platform_marker(tmp_path: Path) -> None:
    """A Linux LLVM bundle cannot claim Windows readiness or vice versa."""
    _ = llvm_validation.import_linux_llvm(tmp_path, _host_observation(tmp_path))
    assert llvm_validation.inspect_llvm(tmp_path, LINUX_PLATFORM).ready
    assert not llvm_validation.inspect_llvm(tmp_path, WINDOWS_PLATFORM).ready


def test_llvm_inspection_rejects_linked_alias(tmp_path: Path) -> None:
    """A symlinked launcher cannot substitute for repository-local Clang."""
    destination = llvm_validation.import_linux_llvm(
        tmp_path, _host_observation(tmp_path)
    )
    alias = destination / "jig-bin/clang.bin"
    relocated = alias.with_name("clang-physical.bin")
    _ = alias.replace(relocated)
    try:
        _ = alias.symlink_to(relocated)
    except OSError as error:
        pytest.skip(f"symlinks unavailable: {error}")
    assert not llvm_validation.inspect_llvm(tmp_path, LINUX_PLATFORM).ready


def test_llvm_inspection_rejects_linked_marker(tmp_path: Path) -> None:
    """A linked completion marker is not physical LLVM runtime authority."""
    destination = llvm_validation.import_linux_llvm(
        tmp_path, _host_observation(tmp_path)
    )
    marker = destination / llvm_validation.LLVM_IMPORT_MARKER
    relocated = marker.with_name("marker-physical")
    _ = marker.replace(relocated)
    try:
        _ = marker.symlink_to(relocated)
    except OSError as error:
        pytest.skip(f"symlinks unavailable: {error}")
    assert not llvm_validation.inspect_llvm(tmp_path, LINUX_PLATFORM).ready


def test_llvm_inspection_rejects_linked_root(tmp_path: Path) -> None:
    """An alias cannot redirect the LLVM toolchain root to other content."""
    destination = llvm_validation.import_linux_llvm(
        tmp_path, _host_observation(tmp_path)
    )
    relocated = destination.with_name("llvm-physical")
    _ = destination.replace(relocated)
    try:
        _ = destination.symlink_to(relocated, target_is_directory=True)
    except OSError as error:
        pytest.skip(f"symlinks unavailable: {error}")
    assert not llvm_validation.inspect_llvm(tmp_path, LINUX_PLATFORM).ready
    with pytest.raises(
        llvm_validation.LlvmImportError,
        match="without the exact import marker",
    ):
        _ = llvm_validation.import_linux_llvm(
            tmp_path, _host_observation(tmp_path / "other-host")
        )


def test_llvm_inspection_rejects_oversized_marker(tmp_path: Path) -> None:
    """Marker comparison must not ingest unbounded local state."""
    destination = llvm_validation.import_linux_llvm(
        tmp_path, _host_observation(tmp_path)
    )
    marker = destination / llvm_validation.LLVM_IMPORT_MARKER
    with marker.open("wb") as stream:
        _ = stream.truncate(2_000_000)
    assert not llvm_validation.inspect_llvm(tmp_path, LINUX_PLATFORM).ready


def test_llvm_inspection_rejects_same_byte_marker_inode_swap(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An inode change before marker read is not valid ready evidence."""
    destination = llvm_validation.import_linux_llvm(
        tmp_path, _host_observation(tmp_path)
    )
    marker = destination / llvm_validation.LLVM_IMPORT_MARKER
    replacement = marker.with_name("marker-replacement")
    _ = replacement.write_bytes(marker.read_bytes())
    real_open = os.open

    def swap_before_open(path: Path, flags: int) -> int:
        if path == marker:
            _ = replacement.replace(marker)
        return real_open(path, flags)

    monkeypatch.setattr(os, "open", swap_before_open)
    assert not llvm_validation.inspect_llvm(tmp_path, LINUX_PLATFORM).ready


def test_llvm_inspection_rejects_missing_runtime_library(
    tmp_path: Path,
) -> None:
    """The neutral launcher is not ready without local linked libraries."""
    destination = llvm_validation.import_linux_llvm(
        tmp_path, _host_observation(tmp_path)
    )
    (destination / "lib/libLLVM.so.22.1").unlink()
    assert not llvm_validation.inspect_llvm(tmp_path, LINUX_PLATFORM).ready


def test_llvm_inspection_rejects_fifo_marker_without_blocking(
    tmp_path: Path,
) -> None:
    """Named pipes cannot masquerade as completion markers or block checks."""
    mkfifo = getattr(os, "mkfifo", None)
    if mkfifo is None:
        pytest.skip("FIFO unsupported")
    destination = llvm_validation.import_linux_llvm(
        tmp_path, _host_observation(tmp_path)
    )
    marker = destination / llvm_validation.LLVM_IMPORT_MARKER
    marker.unlink()
    mkfifo(marker)
    assert not llvm_validation.inspect_llvm(tmp_path, LINUX_PLATFORM).ready
