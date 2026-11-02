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
import shutil
import subprocess as sp  # ruff: ignore[suspicious-subprocess-import]
from pathlib import Path
from typing import Self, cast, final, override

import pytest
from scripts.bootstrap import llvm_validation

LINUX_PLATFORM = "linux-x86_64"
WINDOWS_PLATFORM = "windows-x86_64"
LLVM_VERSION = "22.1.8"
CLANG_BYTES = b"clang-22"
TIDY_BYTES = b"clang-tidy-22"
FORMAT_BYTES = b"clang-format-22"
LLVM_BYTES = b"libLLVM"
CLANG_CPP_BYTES = b"libclang-cpp"
RESOURCE_BYTES = b"resource-header"
FORGED_ALIAS_BYTES = b"forged neutral alias"
WINDOWS_MARKER_BYTES = f"llvm={LLVM_VERSION}\nplatform={WINDOWS_PLATFORM}\n".encode()
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
    assert (root / "jig-bin/clang.bin").stat().st_mode & 0o111
    assert (root / llvm_validation.LLVM_IMPORT_MARKER).is_file()
    assert llvm_validation.import_linux_llvm(tmp_path, observation) == root


@pytest.mark.parametrize("fault", (OSError, ValueError, RuntimeError, TypeError))
def test_llvm_marker_fdopen_failure_closes_owned_descriptor(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault: type[Exception],
) -> None:
    """Host stream wrapper failures cannot leak a marker file descriptor."""
    root = llvm_validation.import_linux_llvm(tmp_path, _host_observation(tmp_path))
    owned: list[int] = []

    def faulty_stream(descriptor: int, _mode: str) -> None:
        owned.append(descriptor)
        raise fault("simulated LLVM marker stream failure")

    with monkeypatch.context() as isolated:
        isolated.setattr(llvm_validation.os, "fdopen", faulty_stream)
        assert not llvm_validation._valid_marker(root, LINUX_PLATFORM)
    assert len(owned) == 1
    for descriptor in owned:
        with pytest.raises(OSError):
            _ = os.fstat(descriptor)


class _ForeignMarkerBytes(bytes):
    """Digest-matching contents are not evidence from a native byte read."""


@pytest.mark.parametrize("kind", ("mutable", "view", "subclass"))
def test_llvm_marker_rejects_nonnative_stream_bytes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
) -> None:
    """An injected stream cannot certify marker bytes via lookalike types."""
    root = llvm_validation.import_linux_llvm(tmp_path, _host_observation(tmp_path))
    marker = root / llvm_validation.LLVM_IMPORT_MARKER
    original = os.fdopen
    raw = marker.read_bytes()
    values: dict[str, object] = {
        "mutable": bytearray(raw),
        "view": memoryview(raw),
        "subclass": _ForeignMarkerBytes(raw),
    }

    @final
    class ForeignRead:
        def __init__(self, descriptor: int, mode: str) -> None:
            self.original = original(descriptor, mode)

        def __enter__(self) -> Self:
            return self

        def __exit__(self, *_arguments: object) -> None:
            self.original.close()

        def fileno(self) -> int:
            return self.original.fileno()

        def read(self, _size: int) -> object:
            return values[kind]

    monkeypatch.setattr(os, "fdopen", ForeignRead)
    assert not llvm_validation.inspect_llvm(tmp_path, LINUX_PLATFORM).ready


@pytest.mark.parametrize("kind", ("descriptor", "path"))
def test_llvm_marker_rejects_foreign_status_proxy(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
) -> None:
    """Matching numeric attributes on a proxy are not native inode evidence."""
    root = llvm_validation.import_linux_llvm(tmp_path, _host_observation(tmp_path))
    marker = root / llvm_validation.LLVM_IMPORT_MARKER
    native = marker.lstat()

    @final
    class ForgedStatus:
        st_mode = native.st_mode
        st_dev = native.st_dev
        st_ino = native.st_ino
        st_size = native.st_size
        st_nlink = native.st_nlink
        st_mtime_ns = native.st_mtime_ns
        st_ctime_ns = native.st_ctime_ns

    if kind == "path":
        original_lstat = Path.lstat

        def forged_lstat(path: Path) -> object:
            return ForgedStatus() if path == marker else original_lstat(path)

        monkeypatch.setattr(Path, "lstat", forged_lstat)
    else:
        original_fstat = os.fstat

        def forged_fstat(descriptor: int) -> object:
            _ = original_fstat(descriptor)
            return ForgedStatus()

        monkeypatch.setattr(os, "fstat", forged_fstat)
    assert not llvm_validation.inspect_llvm(tmp_path, LINUX_PLATFORM).ready


@pytest.mark.parametrize(
    "staging_fault",
    ("redirected-root", "nondirectory-root", "redirected-stage"),
)
def test_linux_import_rejects_untrusted_staging_before_copy(
    tmp_path: Path,
    staging_fault: str,
) -> None:
    """Repository-local LLVM staging cannot redirect imports outside .temp."""
    observation = _host_observation(tmp_path)
    outside = tmp_path / "unrelated-staging"
    outside.mkdir()
    temporary_root = tmp_path / ".temp"
    if staging_fault == "redirected-root":
        try:
            temporary_root.symlink_to(outside, target_is_directory=True)
        except (OSError, NotImplementedError) as error:
            pytest.skip(f"directory links unsupported: {error}")
    elif staging_fault == "nondirectory-root":
        _ = temporary_root.write_text("foreign temporary root", encoding="utf-8")
    else:
        temporary_root.mkdir()
        try:
            (temporary_root / "llvm-import-linux-x86_64").symlink_to(
                outside, target_is_directory=True
            )
        except (OSError, NotImplementedError) as error:
            pytest.skip(f"directory links unsupported: {error}")
    with pytest.raises(llvm_validation.LlvmImportError, match="LLVM.*staging"):
        _ = llvm_validation.import_linux_llvm(tmp_path, observation)
    assert not (tmp_path / llvm_validation.LLVM_ROOT).exists()
    assert not tuple(outside.iterdir())


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


@pytest.mark.parametrize("alias_kind", ("symlink", "hardlink"))
def test_linux_wrapper_writer_refuses_linked_leaf(
    tmp_path: Path, alias_kind: str
) -> None:
    """A reserved wrapper leaf must never overwrite an outside linked file."""
    destination = tmp_path / "clang.bin"
    external = tmp_path / "outside-wrapper"
    original = b"external bytes must be preserved"
    _ = external.write_bytes(original)
    try:
        if alias_kind == "symlink":
            _ = destination.symlink_to(external)
        else:
            os.link(external, destination)
    except (OSError, NotImplementedError) as error:
        pytest.skip(f"file aliases unavailable: {error}")

    with pytest.raises(llvm_validation.LlvmImportError, match="wrapper"):
        llvm_validation._write_linux_alias(  # pyright: ignore[reportPrivateUsage]
            destination, "#!/bin/sh\n"
        )
    assert external.read_bytes() == original


def test_linux_wrapper_writer_rejects_leaf_inserted_at_exclusive_open(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Even a last-moment symlink cannot redirect executable wrapper bytes."""
    wrapper = tmp_path / "clang.bin"
    external = tmp_path / "external-wrapper"
    _ = external.write_bytes(b"protected wrapper destination")
    native_open = os.open
    inserted = False

    def racing_open(
        path: str | os.PathLike[str], flags: int, mode: int = 0o777
    ) -> int:
        nonlocal inserted
        if Path(path) == wrapper:
            inserted = True
            try:
                _ = wrapper.symlink_to(external)
            except (OSError, NotImplementedError) as error:
                pytest.skip(f"symlinks unavailable: {error}")
        return native_open(path, flags, mode)

    monkeypatch.setattr(os, "open", racing_open)
    with pytest.raises(llvm_validation.LlvmImportError, match="exclusive"):
        llvm_validation._write_linux_alias(  # pyright: ignore[reportPrivateUsage]
            wrapper, "#!/bin/sh\n"
        )
    assert inserted
    assert wrapper.is_symlink()
    assert external.read_bytes() == b"protected wrapper destination"


def test_inspection_requires_completed_neutral_aliases(tmp_path: Path) -> None:
    """Readiness never accepts a partial imported LLVM tree."""
    observation = _host_observation(tmp_path)
    missing = llvm_validation.inspect_llvm(tmp_path, LINUX_PLATFORM)
    root = llvm_validation.import_linux_llvm(tmp_path, observation)
    ready = llvm_validation.inspect_llvm(tmp_path, LINUX_PLATFORM)

    assert missing.ready is False
    assert ready.ready is True
    assert ready.path == root / "jig-bin/clang.bin"


@pytest.mark.parametrize(
    "failure",
    [
        (operation, fault_type)
        for operation in ("is_symlink", "is_junction", "lstat")
        for fault_type in (TypeError, RuntimeError)
    ],
)
@pytest.mark.parametrize("target_kind", ["marker", "runtime", "resource"])
def test_llvm_inspection_host_status_faults_are_not_ready(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    failure: tuple[str, type[Exception]],
    target_kind: str,
) -> None:
    """Bad host status adapters must not turn readiness into a traceback."""
    operation, fault_type = failure
    root = llvm_validation.import_linux_llvm(tmp_path, _host_observation(tmp_path))
    target = {
        "marker": root / llvm_validation.LLVM_IMPORT_MARKER,
        "runtime": root / "jig-bin/clang.bin",
        "resource": root / "lib/clang/22",
    }[target_kind]
    original = {
        "is_symlink": Path.is_symlink,
        "is_junction": Path.is_junction,
        "lstat": Path.lstat,
    }[operation]
    fault = fault_type("injected LLVM runtime status failure")

    def fail_status(path: Path) -> object:
        if path == target:
            raise fault
        return original(path)

    with monkeypatch.context() as isolated:
        isolated.setattr(Path, operation, fail_status)
        readiness = llvm_validation.inspect_llvm(tmp_path, LINUX_PLATFORM)
    assert not readiness.ready
    assert readiness.detail.endswith("aliases are absent")


@pytest.mark.parametrize("operation", ("is_symlink", "is_junction"))
@pytest.mark.parametrize("foreign", (None, 0, ""))
@pytest.mark.parametrize("target_kind", ("marker", "alias", "resource"))
def test_llvm_inspection_rejects_foreign_link_status(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    operation: str,
    foreign: object,
    target_kind: str,
) -> None:
    """Falsy nonboolean link results cannot attest an imported LLVM file."""
    root = llvm_validation.import_linux_llvm(tmp_path, _host_observation(tmp_path))
    target = {
        "marker": root / llvm_validation.LLVM_IMPORT_MARKER,
        "alias": root / "jig-bin/clang.bin",
        "resource": root / "lib/clang/22",
    }[target_kind]
    original = Path.is_symlink if operation == "is_symlink" else Path.is_junction

    def fake_link_status(path: Path) -> object:
        return foreign if path == target else original(path)

    monkeypatch.setattr(Path, operation, fake_link_status)
    assert not llvm_validation.inspect_llvm(tmp_path, LINUX_PLATFORM).ready


@pytest.mark.parametrize("operation", ("is_symlink", "is_junction"))
@pytest.mark.parametrize("foreign", (None, 0, ""))
def test_linux_import_rejects_foreign_resource_member_status(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    operation: str,
    foreign: object,
) -> None:
    """Resource members require genuine native link decisions before copying."""
    observation = _host_observation(tmp_path)
    member = observation.resource_dir / "stddef.h"
    original = Path.is_symlink if operation == "is_symlink" else Path.is_junction

    def fake_link_status(path: Path) -> object:
        return foreign if path == member else original(path)

    monkeypatch.setattr(Path, operation, fake_link_status)
    with pytest.raises(llvm_validation.LlvmImportError, match="resource"):
        _ = llvm_validation.import_linux_llvm(tmp_path, observation)
    assert not (tmp_path / llvm_validation.LLVM_ROOT).exists()


def test_linux_import_rejects_fifo_resource_member(tmp_path: Path) -> None:
    """A host resource pipe must not be hardlinked into a published LLVM tree."""
    if not hasattr(os, "mkfifo"):
        pytest.skip("FIFO unsupported")
    observation = _host_observation(tmp_path)
    os.mkfifo(observation.resource_dir / "foreign-fifo")
    with pytest.raises(llvm_validation.LlvmImportError, match="resource"):
        _ = llvm_validation.import_linux_llvm(tmp_path, observation)
    assert not (tmp_path / llvm_validation.LLVM_ROOT).exists()


def test_linux_import_preserves_physical_nested_resource_files(
    tmp_path: Path,
) -> None:
    """Resource admission retains ordinary directories and header files."""
    observation = _host_observation(tmp_path)
    nested = observation.resource_dir / "include" / "bits"
    nested.mkdir(parents=True)
    _ = (nested / "stdint.h").write_bytes(b"nested-header")
    root = llvm_validation.import_linux_llvm(tmp_path, observation)
    assert (
        root / "lib/clang/22/include/bits/stdint.h"
    ).read_bytes() == b"nested-header"


class _ResourceTraversalError(OSError):
    """A host traversal failure with a hostile exception formatter."""

    @override
    def __str__(self) -> str:
        raise AssertionError("foreign resource failure formatter was invoked")


def test_linux_import_types_resource_traversal_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Host filesystem traversal faults become typed, cause-preserving errors."""
    observation = _host_observation(tmp_path)
    error = _ResourceTraversalError("untrusted")
    original = Path.rglob

    def broken_resource_traversal(path: Path, pattern: str):
        if path == observation.resource_dir:
            raise error
        return original(path, pattern)

    monkeypatch.setattr(Path, "rglob", broken_resource_traversal)
    with pytest.raises(
        llvm_validation.LlvmImportError, match="resource traversal"
    ) as raised:
        _ = llvm_validation.import_linux_llvm(tmp_path, observation)
    assert raised.value.__cause__ is error
    assert not (tmp_path / llvm_validation.LLVM_ROOT).exists()


def test_wrong_host_version_is_not_admitted() -> None:
    """A different host Clang release cannot satisfy the pinned toolchain."""
    assert llvm_validation.llvm_version_matches("clang version 22.1.8") is True
    assert llvm_validation.llvm_version_matches("clang version 22.1.7") is False


@pytest.mark.parametrize(
    "banner",
    (
        "clang version 22.1.80",
        "clang version 122.1.8",
        "clang version 22.1.8.1",
        "clang version 22.1.8rc1",
        "clang version 22.1.8-rc1",
        "clang version 22.1.8+dirty",
        "clang version 22.1.8_untested",
        "clang version 22.1.8.0\nclang version 22.1.7",
    ),
)
def test_llvm_host_version_rejects_embedded_or_qualified_release(
    banner: str,
) -> None:
    """Version 22.1.8 must be an exact token, not a prefix or suffix."""
    assert not llvm_validation.llvm_version_matches(banner)


@pytest.mark.parametrize(
    "banner",
    (
        "clang version 22.1.8",
        "Ubuntu clang version 22.1.8 (https://llvm.org/)",
        "clang-format version 22.1.8\nTarget: x86_64-pc-linux-gnu",
    ),
)
def test_llvm_host_version_preserves_exact_native_banner(banner: str) -> None:
    """Normal full-release tool banners remain accepted."""
    assert llvm_validation.llvm_version_matches(banner)


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


@pytest.mark.parametrize("kind", ("missing-bin", "missing-resource"))
def test_llvm_inspection_rejects_forged_runtime_lstat(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
) -> None:
    """Native-looking mode values on a proxy cannot replace runtime files."""
    root = llvm_validation.import_linux_llvm(tmp_path, _host_observation(tmp_path))
    target = root / "bin/clang" if kind == "missing-bin" else root / "lib/clang/22"
    mode = target.lstat().st_mode
    if kind == "missing-bin":
        target.unlink()
    else:
        shutil.rmtree(target)

    @final
    class ForgedStatus:
        st_mode = mode

    original = Path.lstat

    def forged_lstat(path: Path) -> object:
        return ForgedStatus() if path == target else original(path)

    monkeypatch.setattr(Path, "lstat", forged_lstat)
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


def _windows_tool_bundle(tmp_path: Path) -> Path:
    """Create synthetic Windows tools without writing any aliases.

    Returns:
        The physical root containing three synthetic PE executables.

    """
    root = tmp_path / llvm_validation.LLVM_ROOT
    tools = root / "bin"
    tools.mkdir(parents=True)
    for name, content in (
        ("clang.exe", CLANG_BYTES),
        ("clang-tidy.exe", TIDY_BYTES),
        ("clang-format.exe", FORMAT_BYTES),
    ):
        _ = (tools / name).write_bytes(content)
    return root


@pytest.mark.parametrize("target_kind", ("alias", "directory"))
def test_windows_aliases_reject_masked_symlink_destinations(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    target_kind: str,
) -> None:
    """False-looking path statuses cannot route alias writes to an outside tree."""
    root = _windows_tool_bundle(tmp_path)
    outside = tmp_path / "unrelated-windows-aliases"
    outside.mkdir()
    target = root / "jig-bin"
    if target_kind == "alias":
        target.mkdir()
        target = target / "clang.bin"
        sentinel = outside / "clang.bin"
        _ = sentinel.write_bytes(b"outside-alias-bytes")
    else:
        sentinel = outside / "sentinel.bin"
        _ = sentinel.write_bytes(b"outside-directory-bytes")
    try:
        target.symlink_to(
            sentinel if target_kind == "alias" else outside,
            target_is_directory=target_kind == "directory",
        )
    except (OSError, NotImplementedError) as error:
        pytest.skip(f"links unavailable: {error}")
    real_exists = Path.exists
    real_symlink = Path.is_symlink
    real_junction = Path.is_junction

    def masked_exists(path: Path) -> bool:
        return False if path == target else real_exists(path)

    def masked_symlink(path: Path) -> object:
        return 0 if path == target else real_symlink(path)

    def masked_junction(path: Path) -> object:
        return None if path == target else real_junction(path)

    monkeypatch.setattr(Path, "exists", masked_exists)
    monkeypatch.setattr(Path, "is_symlink", masked_symlink)
    monkeypatch.setattr(Path, "is_junction", masked_junction)
    with pytest.raises(llvm_validation.LlvmImportError, match="alias"):
        _ = llvm_validation.write_windows_llvm_aliases(root)
    assert sentinel.read_bytes() == (
        b"outside-alias-bytes" if target_kind == "alias" else b"outside-directory-bytes"
    )


def test_windows_alias_copy_rejects_symlink_inserted_before_fallback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cross-device fallback cannot overwrite a symlink installed mid-copy."""
    root = _windows_tool_bundle(tmp_path)
    alias = root / "jig-bin/clang.bin"
    sentinel = tmp_path / "alias-sentinel"
    _ = sentinel.write_bytes(b"external-data")
    real_link = os.link

    def racing_link(source: str, destination: str) -> None:
        if Path(destination) == alias:
            try:
                alias.symlink_to(sentinel)
            except (OSError, NotImplementedError) as error:
                pytest.skip(f"symlinks unavailable: {error}")
            raise OSError("simulated cross-device link failure")
        real_link(source, destination)

    monkeypatch.setattr(os, "link", racing_link)
    with pytest.raises(llvm_validation.LlvmImportError, match="copy"):
        _ = llvm_validation.write_windows_llvm_aliases(root)
    assert sentinel.read_bytes() == b"external-data"
    assert not (root / llvm_validation.LLVM_IMPORT_MARKER).exists()


def test_windows_alias_cross_device_fallback_preserves_tool_bytes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Exclusive fallback remains usable when ordinary host hardlinks fail."""
    root = _windows_tool_bundle(tmp_path)

    def no_hardlinks(_source: str, _destination: str) -> None:
        raise OSError("cross-device import")

    monkeypatch.setattr(os, "link", no_hardlinks)
    aliases = llvm_validation.write_windows_llvm_aliases(root)
    assert aliases[0].read_bytes() == CLANG_BYTES
    assert aliases[1].read_bytes() == TIDY_BYTES
    assert aliases[2].read_bytes() == FORMAT_BYTES
    assert llvm_validation.inspect_llvm(tmp_path, WINDOWS_PLATFORM).ready


def test_windows_aliases_reject_existing_drift(tmp_path: Path) -> None:
    """An existing neutral Clang alias cannot overwrite pinned PE identity."""
    root = _windows_tool_bundle(tmp_path)
    alias = root / "jig-bin/clang.bin"
    alias.parent.mkdir()
    _ = alias.write_bytes(FORGED_ALIAS_BYTES)
    with pytest.raises(llvm_validation.LlvmImportError, match=r"alias|mismatch"):
        _ = llvm_validation.write_windows_llvm_aliases(root)
    assert not (root / llvm_validation.LLVM_IMPORT_MARKER).exists()
    assert alias.read_bytes() == FORGED_ALIAS_BYTES


def test_windows_aliases_reject_linked_existing_alias(tmp_path: Path) -> None:
    """Exact PE bytes behind a symlink do not authorize an alias."""
    root = _windows_tool_bundle(tmp_path)
    alias = root / "jig-bin/clang.bin"
    alias.parent.mkdir()
    try:
        _ = alias.symlink_to(root / "bin/clang.exe")
    except OSError as error:
        pytest.skip(f"symlinks unavailable: {error}")
    with pytest.raises(llvm_validation.LlvmImportError, match=r"alias|redirect"):
        _ = llvm_validation.write_windows_llvm_aliases(root)
    assert not (root / llvm_validation.LLVM_IMPORT_MARKER).exists()


def test_windows_aliases_reject_linked_source_tool(tmp_path: Path) -> None:
    """A pinned Windows executable cannot be borrowed from an alias path."""
    root = _windows_tool_bundle(tmp_path)
    source = root / "bin/clang.exe"
    real = source.with_name("clang-physical.exe")
    _ = source.replace(real)
    try:
        _ = source.symlink_to(real)
    except OSError as error:
        pytest.skip(f"symlinks unavailable: {error}")
    with pytest.raises(llvm_validation.LlvmImportError, match=r"source|tool"):
        _ = llvm_validation.write_windows_llvm_aliases(root)
    assert not (root / llvm_validation.LLVM_IMPORT_MARKER).exists()


@pytest.mark.parametrize("kind", ("symlink", "hardlink", "regular"))
def test_windows_aliases_reject_preexisting_invalid_marker_before_writing(
    tmp_path: Path,
    kind: str,
) -> None:
    """A poisoned marker cannot redirect writes or publish partial aliases."""
    root = _windows_tool_bundle(tmp_path)
    marker = root / llvm_validation.LLVM_IMPORT_MARKER
    sentinel = tmp_path / "unrelated-marker"
    _ = sentinel.write_bytes(b"unrelated-sentinel")
    if kind == "symlink":
        try:
            marker.symlink_to(sentinel)
        except (OSError, NotImplementedError) as error:
            pytest.skip(f"symlinks unavailable: {error}")
    elif kind == "hardlink":
        try:
            os.link(sentinel, marker)
        except OSError as error:
            pytest.skip(f"hardlinks unavailable: {error}")
    else:
        _ = marker.write_bytes(b"stale-marker")
    with pytest.raises(llvm_validation.LlvmImportError, match="marker"):
        _ = llvm_validation.write_windows_llvm_aliases(root)
    assert sentinel.read_bytes() == b"unrelated-sentinel"
    assert not (root / "jig-bin").exists()
    assert marker.is_symlink() if kind == "symlink" else marker.exists()


def test_windows_aliases_reject_exact_hardlinked_marker(tmp_path: Path) -> None:
    """Even matching marker bytes borrowed by hardlink are not unique state."""
    root = _windows_tool_bundle(tmp_path)
    outside = tmp_path / "borrowed-marker"
    _ = outside.write_bytes(WINDOWS_MARKER_BYTES)
    try:
        os.link(outside, root / llvm_validation.LLVM_IMPORT_MARKER)
    except OSError as error:
        pytest.skip(f"hardlinks unavailable: {error}")
    with pytest.raises(llvm_validation.LlvmImportError, match="marker"):
        _ = llvm_validation.write_windows_llvm_aliases(root)
    assert not (root / "jig-bin").exists()
    assert outside.read_bytes() == WINDOWS_MARKER_BYTES


def test_windows_aliases_cannot_follow_marker_inserted_during_create(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Exclusive publication rejects an inserted symlink, preserving its target."""
    root = _windows_tool_bundle(tmp_path)
    marker = root / llvm_validation.LLVM_IMPORT_MARKER
    sentinel = tmp_path / "unrelated-marker-race"
    _ = sentinel.write_bytes(b"outside-bytes")
    original = os.open

    def racing_open(path: str | os.PathLike[str], flags: int, mode: int = 0o777) -> int:
        if Path(path) == marker:
            try:
                marker.symlink_to(sentinel)
            except (OSError, NotImplementedError) as error:
                pytest.skip(f"symlinks unavailable: {error}")
        return original(path, flags, mode)

    monkeypatch.setattr(os, "open", racing_open)
    with pytest.raises(llvm_validation.LlvmImportError, match="exclusive creation"):
        _ = llvm_validation.write_windows_llvm_aliases(root)
    assert sentinel.read_bytes() == b"outside-bytes"
    assert marker.is_symlink()


def test_llvm_inspection_rejects_hardlinked_import_marker(
    tmp_path: Path,
) -> None:
    """A borrowed marker inode cannot attest local LLVM readiness."""
    root = llvm_validation.import_linux_llvm(tmp_path, _host_observation(tmp_path))
    marker = root / llvm_validation.LLVM_IMPORT_MARKER
    outside = tmp_path / "borrowed-linux-marker"
    _ = marker.replace(outside)
    try:
        os.link(outside, marker)
    except OSError as error:
        pytest.skip(f"hardlinks unavailable: {error}")
    assert not llvm_validation.inspect_llvm(tmp_path, LINUX_PLATFORM).ready


def test_windows_aliases_reuse_marker_without_rewriting(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A valid existing marker is already published and must not be rewritten."""
    root = _windows_tool_bundle(tmp_path)
    expected = llvm_validation.write_windows_llvm_aliases(root)
    marker = root / llvm_validation.LLVM_IMPORT_MARKER
    original_status = marker.stat()

    def forbid_marker_rewrite(_descriptor: int, _data: bytes) -> int:
        raise AssertionError("valid LLVM marker was rewritten")

    monkeypatch.setattr(os, "write", forbid_marker_rewrite)
    assert llvm_validation.write_windows_llvm_aliases(root) == expected
    assert marker.stat().st_mtime_ns == original_status.st_mtime_ns


def test_llvm_marker_writer_closes_descriptor_after_host_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Typed marker write failure cannot leak a descriptor or publish a marker."""
    root = _windows_tool_bundle(tmp_path)
    marker = root / llvm_validation.LLVM_IMPORT_MARKER
    error = _ResourceTraversalError("marker write failed")
    observed: list[int] = []

    def faulty_write(descriptor: int, _data: bytes) -> int:
        observed.append(descriptor)
        raise error

    monkeypatch.setattr(os, "write", faulty_write)
    with pytest.raises(
        llvm_validation.LlvmImportError, match="marker write failed"
    ) as raised:
        _ = llvm_validation.write_windows_llvm_aliases(root)
    assert raised.value.__cause__ is error
    assert len(observed) == 1
    with pytest.raises(OSError):
        _ = os.fstat(observed[0])
    assert not marker.exists()


def test_windows_aliases_reuse_exact_unlinked_aliases(tmp_path: Path) -> None:
    """Idempotent setup preserves previously verified native PE bytes."""
    root = _windows_tool_bundle(tmp_path)
    aliases = llvm_validation.write_windows_llvm_aliases(root)
    assert llvm_validation.write_windows_llvm_aliases(root) == aliases
    assert llvm_validation.inspect_llvm(tmp_path, WINDOWS_PLATFORM).ready


def test_linux_import_rejects_linked_resource_member(tmp_path: Path) -> None:
    """Resource trees cannot preserve links to ambient host paths."""
    observation = _host_observation(tmp_path)
    alias = observation.resource_dir / "ambient.h"
    try:
        _ = alias.symlink_to(observation.clang)
    except OSError as error:
        pytest.skip(f"symlinks unavailable: {error}")
    with pytest.raises(llvm_validation.LlvmImportError, match=r"resource|redirect"):
        _ = llvm_validation.import_linux_llvm(tmp_path, observation)
    assert not (tmp_path / llvm_validation.LLVM_ROOT).exists()


def test_linux_import_rejects_linked_resource_directory(tmp_path: Path) -> None:
    """A host resource root alias is not physical compiler state."""
    observation = _host_observation(tmp_path)
    resource = observation.resource_dir
    real = resource.with_name("resource-physical")
    _ = resource.replace(real)
    try:
        _ = resource.symlink_to(real, target_is_directory=True)
    except OSError as error:
        pytest.skip(f"symlinks unavailable: {error}")
    with pytest.raises(llvm_validation.LlvmImportError, match=r"resource|redirect"):
        _ = llvm_validation.import_linux_llvm(tmp_path, observation)
    assert not (tmp_path / llvm_validation.LLVM_ROOT).exists()


def test_linux_import_rejects_linked_host_tool(tmp_path: Path) -> None:
    """The host observation must not follow an aliased compiler binary."""
    observation = _host_observation(tmp_path)
    source = observation.clang
    real = source.with_name("clang-physical")
    _ = source.replace(real)
    try:
        _ = source.symlink_to(real)
    except OSError as error:
        pytest.skip(f"symlinks unavailable: {error}")
    with pytest.raises(llvm_validation.LlvmImportError, match="host LLVM"):
        _ = llvm_validation.import_linux_llvm(tmp_path, observation)
    assert not (tmp_path / llvm_validation.LLVM_ROOT).exists()


def test_windows_aliases_reject_linked_alias_directory(tmp_path: Path) -> None:
    """No alias may be published through a redirected parent directory."""
    root = _windows_tool_bundle(tmp_path)
    outside = tmp_path / "unrelated-aliases"
    outside.mkdir()
    linked = root / "jig-bin"
    try:
        _ = linked.symlink_to(outside, target_is_directory=True)
    except OSError as error:
        pytest.skip(f"symlinks unavailable: {error}")
    with pytest.raises(llvm_validation.LlvmImportError, match="alias directory"):
        _ = llvm_validation.write_windows_llvm_aliases(root)
    assert list(outside.iterdir()) == []
    assert not (root / llvm_validation.LLVM_IMPORT_MARKER).exists()


def test_windows_aliases_preflight_checks_all_existing_members(
    tmp_path: Path,
) -> None:
    """A corrupt final alias cannot cause partial new alias publication."""
    root = _windows_tool_bundle(tmp_path)
    alias = root / "jig-bin/clang-format.bin"
    alias.parent.mkdir()
    _ = alias.write_bytes(FORGED_ALIAS_BYTES)
    with pytest.raises(llvm_validation.LlvmImportError, match="alias mismatch"):
        _ = llvm_validation.write_windows_llvm_aliases(root)
    assert not (root / "jig-bin/clang.bin").exists()
    assert not (root / "jig-bin/clang-tidy.bin").exists()
    assert not (root / llvm_validation.LLVM_IMPORT_MARKER).exists()


_INVALID_COUNTS = ("short", "overlong", "boolean", "missing")
_CLANG_ALIAS = "clang.bin"


def _invalid_count(kind: str, expected: int) -> int:
    """Simulate an invalid host write result.

    Returns:
        Short, overstated, boolean, or missing acknowledgement.

    """
    values: dict[str, object] = {
        "short": expected - 1,
        "overlong": expected + 1,
        "boolean": True,
        "missing": None,
    }
    return cast("int", values[kind])


def _mock_bad_marker_write(
    monkeypatch: pytest.MonkeyPatch,
    invalid_count: str,
) -> None:
    real_write = os.write

    def wrong_write(descriptor: int, data: bytes) -> int:
        _ = real_write(descriptor, data[:-1])
        return _invalid_count(invalid_count, len(data))

    monkeypatch.setattr(os, "write", wrong_write)


@pytest.mark.parametrize("invalid_count", list(_INVALID_COUNTS))
def test_linux_import_rejects_incomplete_wrapper_acknowledgement(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    invalid_count: str,
) -> None:
    """An incomplete wrapper write must not publish an LLVM toolchain."""
    observation = _host_observation(tmp_path)
    real_write = os.write

    def wrong_write(descriptor: int, data: bytes) -> int:
        if data.startswith(b"#!/bin/sh\n"):
            _ = real_write(descriptor, data[:-1])
            return _invalid_count(invalid_count, len(data))
        return real_write(descriptor, data)

    monkeypatch.setattr(os, "write", wrong_write)
    with pytest.raises(llvm_validation.LlvmImportError, match="write count"):
        _ = llvm_validation.import_linux_llvm(tmp_path, observation)
    assert not (tmp_path / llvm_validation.LLVM_ROOT).exists()


@pytest.mark.parametrize("invalid_count", list(_INVALID_COUNTS))
def test_linux_import_rejects_incomplete_marker_acknowledgement(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    invalid_count: str,
) -> None:
    """An incomplete import marker must not commit a Linux runtime."""
    observation = _host_observation(tmp_path)
    _mock_bad_marker_write(monkeypatch, invalid_count)
    with pytest.raises(llvm_validation.LlvmImportError, match="write count"):
        _ = llvm_validation.import_linux_llvm(tmp_path, observation)
    assert not (tmp_path / llvm_validation.LLVM_ROOT).exists()


@pytest.mark.parametrize("invalid_count", list(_INVALID_COUNTS))
def test_windows_aliases_reject_incomplete_marker_acknowledgement(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    invalid_count: str,
) -> None:
    """A partial marker write cannot authorize a Windows LLVM alias set."""
    root = _windows_tool_bundle(tmp_path)
    _mock_bad_marker_write(monkeypatch, invalid_count)
    with pytest.raises(llvm_validation.LlvmImportError, match="write count"):
        _ = llvm_validation.write_windows_llvm_aliases(root)
    assert not (root / llvm_validation.LLVM_IMPORT_MARKER).exists()
    assert not llvm_validation.inspect_llvm(tmp_path, WINDOWS_PLATFORM).ready


@pytest.mark.parametrize(
    "kind", ("bytes", "subclass", "foreign", "os-error", "value-error")
)
def test_llvm_host_which_rejects_foreign_resolution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
) -> None:
    """Optional host discovery must require a native path and typed failures."""

    class ForeignPath:
        def __fspath__(self) -> str:
            raise AssertionError("foreign host path adapter invoked")

    class ForeignString(str):
        pass

    class ForeignHostError(OSError):
        @override
        def __str__(self) -> str:
            raise AssertionError("foreign host error formatter invoked")

    host_tool = tmp_path / "clang"
    _ = host_tool.write_bytes(CLANG_BYTES)
    outcomes: dict[str, object] = {
        "bytes": str(host_tool).encode(),
        "subclass": ForeignString(str(host_tool)),
        "foreign": ForeignPath(),
        "os-error": ForeignHostError("missing host PATH"),
        "value-error": ValueError("host path failure"),
    }

    def fake_which(_name: str) -> object:
        result = outcomes[kind]
        if isinstance(result, Exception):
            raise result
        return result

    monkeypatch.setattr(shutil, "which", fake_which)
    assert llvm_validation._observed_tool("clang") is None  # pyright: ignore[reportPrivateUsage]


def test_llvm_host_which_accepts_native_tool_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A real host path remains available through normal discovery."""
    tool = tmp_path / "clang"
    _ = tool.write_bytes(CLANG_BYTES)

    def native_which(_name: str) -> str:
        return str(tool)

    monkeypatch.setattr(shutil, "which", native_which)
    assert llvm_validation._observed_tool("clang") == tool  # pyright: ignore[reportPrivateUsage]


@pytest.mark.parametrize("kind", ("missing", "forged-is-file", "resolve-error"))
def test_llvm_ldd_does_not_admit_unphysical_library(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
) -> None:
    """A soname line alone cannot establish physical library existence."""
    library = tmp_path / "libLLVM.so.22.1"
    if kind == "resolve-error":
        _ = library.write_bytes(LLVM_BYTES)

    def fake_capture(_command: list[str]) -> str:
        return f"libLLVM.so.22.1 => {library} (0x1234)"

    monkeypatch.setattr(llvm_validation, "_capture", fake_capture)
    original_is_file = Path.is_file
    original_resolve = Path.resolve

    def forged_is_file(path: Path) -> object:
        return True if path == library else original_is_file(path)

    def fail_resolve(path: Path, *, strict: bool = False) -> Path:
        if path == library:
            raise OSError("host resolve failed")
        return original_resolve(path, strict=strict)

    if kind == "forged-is-file":
        monkeypatch.setattr(Path, "is_file", forged_is_file)
    elif kind == "resolve-error":
        monkeypatch.setattr(Path, "resolve", fail_resolve)
    assert (
        llvm_validation._ldd_library(  # pyright: ignore[reportPrivateUsage]
            tmp_path / "clang", "libLLVM.so.22.1"
        )
        is None
    )


def test_llvm_ldd_accepts_physical_library(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Actual physical pinned library resolves through native ldd output."""
    library = tmp_path / "libLLVM.so.22.1"
    _ = library.write_bytes(LLVM_BYTES)

    def fake_capture(_command: list[str]) -> str:
        return f"libLLVM.so.22.1 => {library} (0x1234)"

    monkeypatch.setattr(llvm_validation, "_capture", fake_capture)
    assert (
        llvm_validation._ldd_library(  # pyright: ignore[reportPrivateUsage]
            tmp_path / "clang", "libLLVM.so.22.1"
        )
        == library
    )


@pytest.mark.parametrize("kind", ("masked-missing", "resolve-error"))
def test_llvm_host_resource_discovery_rejects_foreign_directory_status(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
) -> None:
    """Clang's reported resource directory requires native physical evidence."""
    resource = tmp_path / "missing-resources"
    if kind == "resolve-error":
        resource.mkdir()
    clang = tmp_path / "clang"
    library = tmp_path / "libLLVM.so.22.1"
    _ = library.write_bytes(LLVM_BYTES)

    def fake_capture(_arguments: list[str]) -> str:
        return str(resource)

    def fake_library(_executable: Path, _soname: str) -> Path:
        return library

    monkeypatch.setattr(llvm_validation, "_capture", fake_capture)
    monkeypatch.setattr(llvm_validation, "_ldd_library", fake_library)
    original_is_dir = Path.is_dir
    original_resolve = Path.resolve

    def masked_directory(path: Path) -> bool:
        return path == resource or original_is_dir(path)

    def failing_resolution(path: Path, *, strict: bool = False) -> Path:
        if path == resource:
            raise RuntimeError("resource path resolution failed")
        return original_resolve(path, strict=strict)

    if kind == "masked-missing":
        monkeypatch.setattr(Path, "is_dir", masked_directory)
    else:
        monkeypatch.setattr(Path, "resolve", failing_resolution)
    assert llvm_validation._linux_runtime_paths(clang) is None  # pyright: ignore[reportPrivateUsage]


def test_llvm_host_resource_discovery_accepts_native_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A genuine resource tree stays discoverable for exact host LLVM."""
    resource = tmp_path / "resources"
    resource.mkdir()
    clang = tmp_path / "clang"
    library = tmp_path / "libLLVM.so.22.1"
    _ = library.write_bytes(LLVM_BYTES)

    def fake_capture(_arguments: list[str]) -> str:
        return str(resource)

    def fake_library(_executable: Path, _soname: str) -> Path:
        return library

    monkeypatch.setattr(llvm_validation, "_capture", fake_capture)
    monkeypatch.setattr(llvm_validation, "_ldd_library", fake_library)
    assert llvm_validation._linux_runtime_paths(clang) == (  # pyright: ignore[reportPrivateUsage]
        resource,
        library,
        library,
    )


@pytest.mark.parametrize(
    "kind",
    (
        "wrong-command",
        "tuple-argv",
        "boolean-status",
        "foreign-process",
        "bytes-stdout",
        "missing-stdout",
        "bytes-stderr",
        "missing-stderr",
    ),
)
def test_llvm_host_capture_rejects_foreign_process_receipts(
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
) -> None:
    """Version and ldd probes must not accept fabricated subprocess evidence."""
    command = ["clang", "--version"]

    class ForeignCompletion(sp.CompletedProcess[str]):
        pass

    def fake_run(args: list[str], **_kwargs: object) -> sp.CompletedProcess[str]:
        command_args: object = args
        status: object = 0
        stdout: object = "clang version 22.1.8"
        stderr: object = ""
        constructor = sp.CompletedProcess
        if kind == "wrong-command":
            command_args = ["other-clang", "--version"]
        elif kind == "tuple-argv":
            command_args = tuple(args)
        elif kind == "boolean-status":
            status = False
        elif kind == "foreign-process":
            constructor = ForeignCompletion
        elif kind == "bytes-stdout":
            stdout = b"clang version 22.1.8"
        elif kind == "missing-stdout":
            stdout = None
        elif kind == "bytes-stderr":
            stderr = b""
        else:
            stderr = None
        return constructor(
            cast("list[str]", command_args),
            cast("int", status),
            stdout=cast("str", stdout),
            stderr=cast("str", stderr),
        )

    monkeypatch.setattr(sp, "run", fake_run)
    assert llvm_validation._capture(command) is None  # pyright: ignore[reportPrivateUsage]
    assert command == ["clang", "--version"]


@pytest.mark.parametrize("mutation", ("executable", "flag", "append"))
def test_llvm_host_capture_rejects_mutated_launch_arguments(
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
) -> None:
    """Mutable launcher argv cannot rewrite the pinned command expectation."""
    command = ["clang", "--version"]

    def fake_run(args: list[str], **_kwargs: object) -> sp.CompletedProcess[str]:
        if mutation == "executable":
            args[0] = "/foreign/clang"
        elif mutation == "flag":
            args[1] = "--help"
        else:
            args.append("--unexpected")
        return sp.CompletedProcess(args, 0, stdout="clang version 22.1.8", stderr="")

    monkeypatch.setattr(sp, "run", fake_run)
    assert llvm_validation._capture(command) is None  # pyright: ignore[reportPrivateUsage]
    assert command == ["clang", "--version"]


@pytest.mark.parametrize("fault", ("os", "foreign-os", "value", "type", "runtime"))
def test_llvm_host_capture_treats_host_launch_faults_as_unavailable(
    monkeypatch: pytest.MonkeyPatch,
    fault: str,
) -> None:
    """An unavailable host LLVM probe cannot execute foreign format hooks."""

    class ForeignOSError(OSError):
        @override
        def __str__(self) -> str:
            raise AssertionError("foreign LLVM exception formatter invoked")

    errors: dict[str, Exception] = {
        "os": OSError("missing executable"),
        "foreign-os": ForeignOSError("untrusted"),
        "value": ValueError("bad argv"),
        "type": TypeError("bad runner"),
        "runtime": RuntimeError("bad subprocess"),
    }

    def fake_run(_args: list[str], **_kwargs: object) -> None:
        raise errors[fault]

    monkeypatch.setattr(sp, "run", fake_run)
    assert llvm_validation._capture(["clang", "--version"]) is None  # pyright: ignore[reportPrivateUsage]


@pytest.mark.parametrize("status", (0, 1))
def test_llvm_host_capture_accepts_native_text_receipts(
    monkeypatch: pytest.MonkeyPatch,
    status: int,
) -> None:
    """Successful version probes return authentic text; failing probes do not."""
    command = ["clang", "--version"]

    def fake_run(args: list[str], **_kwargs: object) -> sp.CompletedProcess[str]:
        return sp.CompletedProcess(
            args, status, stdout="clang version 22.1.8\n", stderr=""
        )

    monkeypatch.setattr(sp, "run", fake_run)
    assert llvm_validation._capture(command) == (  # pyright: ignore[reportPrivateUsage]
        "clang version 22.1.8" if status == 0 else None
    )
