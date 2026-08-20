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

from typing import TYPE_CHECKING

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
