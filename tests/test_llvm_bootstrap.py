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
from collections.abc import Callable
from contextlib import suppress
from dataclasses import replace
from io import BufferedRandom, BufferedReader
from pathlib import Path
from stat import S_ISREG
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
FOREIGN_TOOL_BYTES = b"untrusted host tool"
HOST_CLANG_KIND = "clang"
DELIVERY_COPY = "copy"
HOST_POSIX = "posix"
WINDOWS_MARKER_BYTES = f"llvm={LLVM_VERSION}\nplatform={WINDOWS_PLATFORM}\n".encode()
WRAPPER_LIBRARY_PATH = "LD_LIBRARY_PATH"
WRAPPER_CLANG_EXEC = 'exec "$ROOT/bin/clang" "$@"'


def _copy_target_is_file(target: BufferedRandom, path: Path) -> bool:
    """Resolve either a path-backed or dirfd-backed exclusive copy stream."""
    name = target.name
    if type(name) is int:
        try:
            opened = os.fstat(name)
            named = path.lstat()
        except (OSError, ValueError):
            return False
        return (opened.st_dev, opened.st_ino) == (named.st_dev, named.st_ino)
    return type(name) is str and Path(name) == path


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


def _replace_import_source_during_link(
    monkeypatch: pytest.MonkeyPatch,
    paths: tuple[Path, Path, Path],
    *,
    delivery: str,
) -> Callable[[], bool]:
    """Simulate a late physical host tool replacement at link admission.

    Returns:
        A function reporting whether the simulated substitution occurred.

    """
    source, parked, foreign = paths
    native_link = os.link
    swapped = False

    def swap_source(
        original: str | os.PathLike[str],
        destination: str | os.PathLike[str],
        *,
        src_dir_fd: int | None = None,
        dst_dir_fd: int | None = None,
        follow_symlinks: bool = True,
    ) -> None:
        nonlocal swapped
        if Path(original) == source and not swapped:
            _ = source.rename(parked)
            _ = foreign.rename(source)
            swapped = True
        if delivery == DELIVERY_COPY and Path(original) == source:
            fault = OSError("simulated cross-device tool import")
            raise fault
        native_link(
            original,
            destination,
            src_dir_fd=src_dir_fd,
            dst_dir_fd=dst_dir_fd,
            follow_symlinks=follow_symlinks,
        )

    monkeypatch.setattr(os, "link", swap_source)
    return lambda: swapped


@pytest.mark.skipif(
    os.name != HOST_POSIX, reason="requires physical source replacement"
)
@pytest.mark.parametrize(
    "scenario",
    [
        ("clang", "hardlink"),
        ("clang", "copy"),
        ("library", "hardlink"),
        ("library", "copy"),
    ],
)
def test_linux_import_refuses_late_replaced_host_tool(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    scenario: tuple[str, str],
) -> None:
    """A swapped host binary or library cannot authorize a complete import."""
    kind, delivery = scenario
    observed = _host_observation(tmp_path)
    source = observed.clang if kind == HOST_CLANG_KIND else observed.llvm
    previous = source.read_bytes()
    parked = tmp_path / "parked-host-tool"
    foreign = tmp_path / "foreign-host-tool"
    _ = foreign.write_bytes(FOREIGN_TOOL_BYTES)

    with monkeypatch.context() as isolated:
        swapped = _replace_import_source_during_link(
            isolated, (source, parked, foreign), delivery=delivery
        )
        with pytest.raises(
            llvm_validation.LlvmImportError,
            match="LLVM import source file changed during copying",
        ):
            _ = llvm_validation.import_linux_llvm(tmp_path, observed)
    assert swapped()
    assert parked.read_bytes() == previous
    assert source.read_bytes() == FOREIGN_TOOL_BYTES
    assert not (tmp_path / llvm_validation.LLVM_ROOT).exists()


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


def test_linux_import_uses_required_sonames_for_resolved_host_libraries(
    tmp_path: Path,
) -> None:
    """Resolved versioned host filenames cannot break local linker sonames."""
    observed = _host_observation(tmp_path)
    llvm = observed.llvm.with_name("libLLVM.so.22.1.8")
    clang_cpp = observed.clang_cpp.with_name("libclang-cpp.so.22.1.8")
    _ = observed.llvm.rename(llvm)
    _ = observed.clang_cpp.rename(clang_cpp)
    observation = replace(observed, llvm=llvm, clang_cpp=clang_cpp)

    local = llvm_validation.import_linux_llvm(tmp_path, observation)

    assert (local / "lib/libLLVM.so.22.1").read_bytes() == LLVM_BYTES
    assert (local / "lib/libclang-cpp.so.22.1").read_bytes() == CLANG_CPP_BYTES
    assert llvm_validation.inspect_llvm(tmp_path, LINUX_PLATFORM).ready
    assert llvm_validation.import_linux_llvm(tmp_path, observation) == local


def test_llvm_marker_writer_rejects_substituted_open_descriptor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A forged marker open result cannot write bytes into another inode."""
    root = tmp_path / "runtime"
    root.mkdir()
    marker = root / llvm_validation.LLVM_IMPORT_MARKER
    outside = tmp_path / "outside-marker"
    original = b"external marker sentinel"
    _ = outside.write_bytes(original)
    native_open = os.open

    def foreign_open(
        path: str | os.PathLike[str],
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        if Path(path) == marker or (path == marker.name and dir_fd is not None):
            return native_open(outside, os.O_WRONLY)
        return native_open(path, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(os, "open", foreign_open)
    with pytest.raises(llvm_validation.LlvmImportError, match="descriptor"):
        llvm_validation._write_import_marker(  # pyright: ignore[reportPrivateUsage]
            root, LINUX_PLATFORM
        )
    assert outside.read_bytes() == original
    assert not marker.exists()


@pytest.mark.parametrize("replacement", ("symlink", "physical"))
def test_llvm_marker_writer_does_not_follow_late_parent_swap(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    replacement: str,
) -> None:
    """An imported marker cannot escape through a raced parent name."""
    if os.name != "posix":
        pytest.skip("POSIX marker parent descriptor boundary")
    root = tmp_path / "owned-marker-parent"
    root.mkdir()
    marker = root / llvm_validation.LLVM_IMPORT_MARKER
    parked = tmp_path / "parked-marker-parent"
    outside = tmp_path / "outside-marker-parent"
    outside.mkdir()
    sentinel = outside / "sentinel"
    _ = sentinel.write_bytes(b"foreign marker data")
    native_open = os.open
    native_write = os.write
    swapped = False
    wrote_foreign = False

    def swap_parent_at_marker_open(
        path: str | os.PathLike[str],
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        nonlocal swapped
        if not swapped and (
            Path(path) == marker or (path == marker.name and dir_fd is not None)
        ):
            _ = root.rename(parked)
            if replacement == "symlink":
                _ = root.symlink_to(outside, target_is_directory=True)
            else:
                _ = outside.rename(root)
            swapped = True
        return native_open(path, flags, mode, dir_fd=dir_fd)

    def monitor_write(fd: int, data: bytes) -> int:
        nonlocal wrote_foreign
        foreign = outside if replacement == "symlink" else root
        if (foreign / marker.name).exists():
            wrote_foreign = True
        return native_write(fd, data)

    monkeypatch.setattr(os, "open", swap_parent_at_marker_open)
    monkeypatch.setattr(os, "write", monitor_write)
    with pytest.raises(llvm_validation.LlvmImportError, match="marker"):
        llvm_validation._write_import_marker(  # pyright: ignore[reportPrivateUsage]
            root, LINUX_PLATFORM
        )
    assert swapped
    assert not wrote_foreign
    foreign = outside if replacement == "symlink" else root
    assert (foreign / sentinel.name).read_bytes() == b"foreign marker data"
    assert not (foreign / marker.name).exists()


def test_llvm_marker_rejects_physical_parent_replacement_before_open(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A physical replacement cannot impersonate the admitted marker parent."""
    if os.name != "posix":
        pytest.skip("POSIX marker parent descriptor boundary")
    root = tmp_path / "owned-marker-parent"
    root.mkdir()
    parked = tmp_path / "parked-marker-parent"
    foreign = tmp_path / "foreign-marker-parent"
    foreign.mkdir()
    sentinel = foreign / "sentinel"
    _ = sentinel.write_bytes(b"foreign marker directory")
    native_open = os.open
    replaced = False

    def swap_before_parent_open(
        path: str | os.PathLike[str],
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        nonlocal replaced
        if Path(path) == root and not replaced:
            _ = root.rename(parked)
            _ = foreign.rename(root)
            replaced = True
        return native_open(path, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(os, "open", swap_before_parent_open)
    with pytest.raises(llvm_validation.LlvmImportError, match="parent descriptor"):
        llvm_validation._write_import_marker(  # pyright: ignore[reportPrivateUsage]
            root, LINUX_PLATFORM
        )
    assert replaced
    assert (root / sentinel.name).read_bytes() == b"foreign marker directory"
    assert not (root / llvm_validation.LLVM_IMPORT_MARKER).exists()


def test_llvm_marker_parent_close_failure_is_typed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failed close of the owned marker parent preserves its native cause."""
    if os.name != "posix":
        pytest.skip("POSIX marker parent descriptor boundary")
    root = tmp_path / "runtime"
    root.mkdir()
    native_open = os.open
    native_close = os.close
    opened_parent: set[int] = set()
    fault = OSError("synthetic marker parent close fault")

    def track_open(
        path: str | os.PathLike[str],
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        fd = native_open(path, flags, mode, dir_fd=dir_fd)
        if Path(path) == root:
            opened_parent.add(fd)
        return fd

    def fail_parent_close(fd: int) -> None:
        native_close(fd)
        if fd in opened_parent:
            opened_parent.remove(fd)
            raise fault

    with monkeypatch.context() as isolated:
        isolated.setattr(os, "open", track_open)
        isolated.setattr(os, "close", fail_parent_close)
        with pytest.raises(
            llvm_validation.LlvmImportError, match="marker parent close failed"
        ) as caught:
            llvm_validation._write_import_marker(  # pyright: ignore[reportPrivateUsage]
                root, LINUX_PLATFORM
            )
    assert caught.value.__cause__ is fault
    assert not opened_parent
    assert (root / llvm_validation.LLVM_IMPORT_MARKER).read_bytes() == (
        f"llvm={LLVM_VERSION}\nplatform={LINUX_PLATFORM}\n".encode()
    )


@pytest.mark.parametrize("invalid_descriptor", [None, True, -1])
def test_llvm_marker_writer_rejects_noninteger_open_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    invalid_descriptor: object,
) -> None:
    """Invalid marker open receipts must not be written or closed."""
    root = tmp_path / "runtime"
    root.mkdir()
    native_open = os.open
    native_close = os.close
    parent_descriptors: set[int] = set()

    def foreign_open(
        path: str | os.PathLike[str],
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        if (path == llvm_validation.LLVM_IMPORT_MARKER and dir_fd is not None) or (
            Path(path) == root / llvm_validation.LLVM_IMPORT_MARKER
        ):
            return cast("int", invalid_descriptor)
        opened = native_open(path, flags, mode, dir_fd=dir_fd)
        if Path(path) == root:
            parent_descriptors.add(opened)
        return opened

    def unexpected_write(_fd: int, _content: bytes) -> int:
        raise AssertionError("foreign marker descriptor was written")

    def unexpected_close(fd: int) -> None:
        if fd not in parent_descriptors:
            raise AssertionError("foreign marker descriptor was closed")
        native_close(fd)
        parent_descriptors.remove(fd)

    monkeypatch.setattr(os, "open", foreign_open)
    monkeypatch.setattr(os, "write", unexpected_write)
    monkeypatch.setattr(os, "close", unexpected_close)
    with pytest.raises(llvm_validation.LlvmImportError, match="descriptor"):
        llvm_validation._write_import_marker(  # pyright: ignore[reportPrivateUsage]
            root, LINUX_PLATFORM
        )

    assert not parent_descriptors


@pytest.mark.parametrize("status_source", ["descriptor", "path"])
def test_llvm_marker_writer_rejects_foreign_stat_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    status_source: str,
) -> None:
    """Marker publication requires native status for the new empty inode."""
    root = tmp_path / "runtime"
    root.mkdir()
    marker = root / llvm_validation.LLVM_IMPORT_MARKER
    native_fstat = os.fstat
    native_lstat = Path.lstat

    @final
    class ForeignStatus:
        def __init__(self, status: os.stat_result) -> None:
            self.st_mode = status.st_mode
            self.st_dev = status.st_dev
            self.st_ino = status.st_ino
            self.st_nlink = status.st_nlink
            self.st_size = status.st_size

    def false_fstat(descriptor: int) -> object:
        status = native_fstat(descriptor)
        return ForeignStatus(status) if S_ISREG(status.st_mode) else status

    def false_lstat(path: Path) -> object:
        status = native_lstat(path)
        return ForeignStatus(status) if path == marker else status

    with monkeypatch.context() as isolated:
        if status_source == "descriptor":
            isolated.setattr(os, "fstat", false_fstat)
        else:
            isolated.setattr(Path, "lstat", false_lstat)
        with pytest.raises(llvm_validation.LlvmImportError, match="descriptor"):
            llvm_validation._write_import_marker(  # pyright: ignore[reportPrivateUsage]
                root, LINUX_PLATFORM
            )
    assert marker.read_bytes() == b""


def test_llvm_marker_writer_rejects_hardlink_after_open(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Marker bytes cannot reach a second link installed before the write."""
    root = tmp_path / "runtime"
    root.mkdir()
    marker = root / llvm_validation.LLVM_IMPORT_MARKER
    outside = tmp_path / "outside-new-marker"
    native_open = os.open

    def linked_open(
        path: str | os.PathLike[str],
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        fd = native_open(path, flags, mode, dir_fd=dir_fd)
        if Path(path) == marker or (path == marker.name and dir_fd is not None):
            os.link(marker, outside)
        return fd

    monkeypatch.setattr(os, "open", linked_open)
    with pytest.raises(llvm_validation.LlvmImportError, match="descriptor"):
        llvm_validation._write_import_marker(  # pyright: ignore[reportPrivateUsage]
            root, LINUX_PLATFORM
        )
    assert outside.read_bytes() == b""


@pytest.mark.parametrize("write_fault", [False, True])
def test_llvm_marker_writer_preserves_foreign_leaf_after_write_swap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, write_fault: bool
) -> None:
    """Verification failure cannot delete an unrelated marker-path replacement."""
    root = tmp_path / "runtime"
    root.mkdir()
    marker = root / llvm_validation.LLVM_IMPORT_MARKER
    original = tmp_path / "published-original"
    foreign = tmp_path / "foreign-replacement"
    sentinel = b"unrelated marker data must survive"
    _ = foreign.write_bytes(sentinel)
    native_write = os.write
    swapped = False

    def swapping_write(fd: int, data: bytes) -> int:
        nonlocal swapped
        count = native_write(fd, data)
        if data.startswith(b"llvm="):
            _ = marker.replace(original)
            _ = foreign.replace(marker)
            swapped = True
            if write_fault:
                raise OSError("writer failed after marker leaf swap")
        return count

    monkeypatch.setattr(os, "write", swapping_write)
    with pytest.raises(llvm_validation.LlvmImportError, match="marker"):
        llvm_validation._write_import_marker(  # pyright: ignore[reportPrivateUsage]
            root, LINUX_PLATFORM
        )
    assert swapped
    assert original.read_bytes().startswith(b"llvm=22.1.8")
    assert marker.read_bytes() == sentinel


@pytest.mark.parametrize("forgery", ["empty", "incorrect"])
def test_llvm_marker_writer_rejects_false_full_write_acknowledgement(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    forgery: str,
) -> None:
    """A complete reported write count cannot publish missing marker bytes."""
    root = tmp_path / "runtime"
    root.mkdir()
    marker = root / llvm_validation.LLVM_IMPORT_MARKER
    native_write = os.write

    def false_write(fd: int, data: bytes) -> int:
        if forgery == "incorrect":
            _ = native_write(fd, b"X" * len(data))
        return len(data)

    monkeypatch.setattr(os, "write", false_write)
    with pytest.raises(llvm_validation.LlvmImportError, match="marker"):
        llvm_validation._write_import_marker(  # pyright: ignore[reportPrivateUsage]
            root, LINUX_PLATFORM
        )
    assert not marker.exists()


@pytest.mark.parametrize("fault", (OSError, ValueError, RuntimeError, TypeError))
def test_llvm_marker_fdopen_failure_closes_owned_descriptor(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault: type[Exception],
) -> None:
    """Host stream wrapper failures cannot leak a marker file descriptor."""
    _ = llvm_validation.import_linux_llvm(tmp_path, _host_observation(tmp_path))
    owned: list[int] = []

    def faulty_stream(descriptor: int, _mode: str) -> None:
        owned.append(descriptor)
        raise fault("simulated LLVM marker stream failure")

    with monkeypatch.context() as isolated:
        isolated.setattr(os, "fdopen", faulty_stream)
        assert not llvm_validation.inspect_llvm(tmp_path, LINUX_PLATFORM).ready
    assert len(owned) == 1
    for descriptor in owned:
        with pytest.raises(OSError):
            _ = os.fstat(descriptor)


@pytest.mark.parametrize("invalid_descriptor", [False, True, None, -1])
def test_llvm_marker_reader_rejects_nonnative_open_descriptor(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    invalid_descriptor: object,
) -> None:
    """A false marker-open receipt cannot wrap or close another descriptor."""
    root = llvm_validation.import_linux_llvm(tmp_path, _host_observation(tmp_path))
    marker = root / llvm_validation.LLVM_IMPORT_MARKER
    native_open = os.open

    def false_open(path: str | os.PathLike[str], flags: int, mode: int = 0o777) -> int:
        if Path(path) == marker:
            return cast("int", invalid_descriptor)
        return native_open(path, flags, mode)

    def forbid_fdopen(_fd: int, _mode: str) -> None:
        raise AssertionError("non-native marker descriptor wrapped")

    def forbid_close(_fd: int) -> None:
        raise AssertionError("non-native marker descriptor closed")

    with monkeypatch.context() as isolated:
        isolated.setattr(os, "open", false_open)
        isolated.setattr(os, "fdopen", forbid_fdopen)
        isolated.setattr(os, "close", forbid_close)
        assert not llvm_validation.inspect_llvm(tmp_path, LINUX_PLATFORM).ready


def _release_import_test_descriptors(opened: list[int], parent_fd: int) -> None:
    """Reclaim test descriptors even when an injected wrapper leaks one."""
    try:
        for descriptor in opened:
            with suppress(OSError):
                os.close(descriptor)
    finally:
        os.close(parent_fd)


@pytest.mark.skipif(os.name != HOST_POSIX, reason="requires dirfd-backed copy")
@pytest.mark.parametrize("foreign_stream", [True, False])
def test_llvm_fallback_stream_rejection_closes_owned_descriptor(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    foreign_stream: bool,
) -> None:
    """A substitute destination stream must not leak the new file handle."""
    parent = tmp_path / "import-parent"
    parent.mkdir()
    other = tmp_path / "unrelated"
    _ = other.write_bytes(b"foreign stream")
    parent_fd = os.open(parent, os.O_RDONLY)
    original_fdopen = os.fdopen
    owned: list[int] = []

    def substituted_stream(descriptor: int, mode: str) -> object:
        owned.append(descriptor)
        if foreign_stream:
            return object()
        borrowed = os.open(other, os.O_RDWR)
        return original_fdopen(borrowed, mode)

    try:
        with monkeypatch.context() as isolated:
            isolated.setattr(os, "fdopen", substituted_stream)
            with pytest.raises(llvm_validation.LlvmImportError, match="stream"):
                _ = cast(
                    "Callable[[Path, int | None], BufferedRandom]",
                    vars(llvm_validation)["_exclusive_import_target"],
                )(parent / "clang", parent_fd)
        assert len(owned) == 1
        with pytest.raises(OSError, match="Bad file descriptor"):
            _ = os.fstat(owned[0])
    finally:
        _release_import_test_descriptors(owned, parent_fd)


@pytest.mark.skipif(os.name != HOST_POSIX, reason="requires dirfd-backed copy")
@pytest.mark.parametrize("closed_by_wrapper", [False, True])
def test_llvm_fallback_fdopen_failure_preserves_cause_and_closes_fd(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    closed_by_wrapper: bool,
) -> None:
    """A failing fd wrapper may have already closed the owned destination fd."""
    parent = tmp_path / "import-parent"
    parent.mkdir()
    parent_fd = os.open(parent, os.O_RDONLY)
    opened: list[int] = []
    failure = ValueError("simulated destination stream wrap failure")

    def failed_fdopen(descriptor: int, mode: str) -> None:
        assert mode.endswith("b")
        opened.append(descriptor)
        if closed_by_wrapper:
            os.close(descriptor)
        raise failure

    try:
        with monkeypatch.context() as isolated:
            isolated.setattr(os, "fdopen", failed_fdopen)
            with pytest.raises(
                llvm_validation.LlvmImportError, match="stream"
            ) as error:
                _ = cast(
                    "Callable[[Path, int | None], BufferedRandom]",
                    vars(llvm_validation)["_exclusive_import_target"],
                )(parent / "clang", parent_fd)
        assert error.value.__cause__ is failure
        assert len(opened) == 1
        with pytest.raises(OSError, match="Bad file descriptor"):
            _ = os.fstat(opened[0])
    finally:
        _release_import_test_descriptors(opened, parent_fd)


def test_llvm_marker_reader_closes_fd_on_foreign_plain_stream(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An injected non-context stream cannot leak the opened marker handle."""
    _ = llvm_validation.import_linux_llvm(tmp_path, _host_observation(tmp_path))
    opened: list[int] = []

    def plain_fdopen(descriptor: int, _mode: str) -> object:
        opened.append(descriptor)
        return object()

    with monkeypatch.context() as isolated:
        isolated.setattr(os, "fdopen", plain_fdopen)
        assert not llvm_validation.inspect_llvm(tmp_path, LINUX_PLATFORM).ready
    assert len(opened) == 1
    try:
        with pytest.raises(OSError):
            _ = os.fstat(opened[0])
    finally:
        try:
            os.close(opened[0])
        except OSError:
            pass


def test_llvm_marker_reader_rejects_different_native_stream(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A native stream from another inode cannot certify an import marker."""
    root = llvm_validation.import_linux_llvm(tmp_path, _host_observation(tmp_path))
    marker = root / llvm_validation.LLVM_IMPORT_MARKER
    outside = tmp_path / "borrowed-marker-stream"
    _ = outside.write_bytes(marker.read_bytes())
    opened: list[int] = []

    def wrong_fdopen(fd: int, mode: str) -> object:
        opened.append(fd)
        return outside.open(mode)

    with monkeypatch.context() as isolated:
        isolated.setattr(os, "fdopen", wrong_fdopen)
        assert not llvm_validation.inspect_llvm(tmp_path, LINUX_PLATFORM).ready
    assert len(opened) == 1
    try:
        with pytest.raises(OSError):
            _ = os.fstat(opened[0])
    finally:
        try:
            os.close(opened[0])
        except OSError:
            pass
    # The marker was rejected, not rewritten, and ordinary reading still works.
    assert marker.read_bytes() == outside.read_bytes()


class _ForeignMarkerBytes(bytes):
    """Digest-matching contents are not evidence from a native byte read."""


@pytest.mark.parametrize("kind", ("mutable", "view", "subclass", "exact"))
def test_llvm_marker_rejects_nonnative_stream_bytes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
) -> None:
    """An injected stream cannot certify marker bytes, even when exact."""
    root = llvm_validation.import_linux_llvm(tmp_path, _host_observation(tmp_path))
    marker = root / llvm_validation.LLVM_IMPORT_MARKER
    original = os.fdopen
    raw = marker.read_bytes()
    values: dict[str, object] = {
        "mutable": bytearray(raw),
        "view": memoryview(raw),
        "subclass": _ForeignMarkerBytes(raw),
        "exact": bytes(raw),
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


def test_linux_import_preserves_occupied_staging_directory(tmp_path: Path) -> None:
    """A prior unrelated staging tree has no ownership receipt for deletion."""
    observation = _host_observation(tmp_path)
    staging = tmp_path / ".temp/llvm-import-linux-x86_64"
    staging.mkdir(parents=True)
    sentinel = staging / "preserve-existing-stage"
    _ = sentinel.write_bytes(b"preexisting unrelated data")
    with pytest.raises(llvm_validation.LlvmImportError, match="staging"):
        _ = llvm_validation.import_linux_llvm(tmp_path, observation)
    assert sentinel.read_bytes() == b"preexisting unrelated data"
    assert not (tmp_path / llvm_validation.LLVM_ROOT).exists()


@pytest.mark.parametrize("redirected", ("dependencies", "llvm-parent"))
def test_linux_import_rejects_redirected_final_parent(
    tmp_path: Path, redirected: str
) -> None:
    """Final LLVM publishing must not escape through a redirected parent."""
    observation = _host_observation(tmp_path)
    outside = tmp_path / "foreign-destination"
    outside.mkdir()
    dependencies = tmp_path / ".dependencies"
    if redirected == "dependencies":
        linked_parent = dependencies
    else:
        dependencies.mkdir()
        linked_parent = dependencies / "llvm"
    try:
        linked_parent.symlink_to(outside, target_is_directory=True)
    except (OSError, NotImplementedError) as error:
        pytest.skip(f"directory links unavailable: {error}")
    with pytest.raises(llvm_validation.LlvmImportError, match="destination"):
        _ = llvm_validation.import_linux_llvm(tmp_path, observation)
    assert not tuple(outside.iterdir())
    assert linked_parent.is_symlink()


def test_linux_import_does_not_publish_through_late_parent_swap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Final publication uses the opened physical parent, not its raced name."""
    observation = _host_observation(tmp_path)
    outside = tmp_path / "outside-publish"
    outside.mkdir()
    sentinel = outside / "sentinel"
    _ = sentinel.write_bytes(b"foreign data")
    parent = tmp_path / ".dependencies/llvm"
    parked = tmp_path / "parked-owned-parent"
    staged = tmp_path / ".temp/llvm-import-linux-x86_64/llvm"
    native_rename = llvm_validation._rename_linux_import_no_replace  # pyright: ignore[reportPrivateUsage]
    swapped = False

    def swapping_replace(
        source: Path,
        destination: str,
        *,
        src_dir_fd: int,
        dst_dir_fd: int,
    ) -> None:
        nonlocal swapped
        if Path(source) == staged:
            _ = parent.rename(parked)
            _ = parent.symlink_to(outside, target_is_directory=True)
            swapped = True
        native_rename(source, destination, src_dir_fd=src_dir_fd, dst_dir_fd=dst_dir_fd)

    monkeypatch.setattr(
        llvm_validation, "_rename_linux_import_no_replace", swapping_replace
    )
    with pytest.raises(llvm_validation.LlvmImportError, match="parent"):
        _ = llvm_validation.import_linux_llvm(tmp_path, observation)
    assert swapped
    assert sentinel.read_bytes() == b"foreign data"
    assert not (outside / LLVM_VERSION).exists()
    assert (parked / LLVM_VERSION).is_dir()
    assert parent.is_symlink()


def test_linux_import_rejects_substituted_parent_descriptor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An open receipt for another directory cannot redirect publication."""
    observation = _host_observation(tmp_path)
    outside = tmp_path / "outside-descriptor"
    outside.mkdir()
    parent = tmp_path / ".dependencies/llvm"
    native_open = os.open

    def substituted_open(
        path: str | os.PathLike[str],
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        if Path(path) == parent:
            return native_open(outside, flags, mode)
        return native_open(path, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(os, "open", substituted_open)
    with pytest.raises(llvm_validation.LlvmImportError, match="descriptor"):
        _ = llvm_validation.import_linux_llvm(tmp_path, observation)
    assert not tuple(outside.iterdir())
    assert not (parent / LLVM_VERSION).exists()


def test_linux_import_does_not_overwrite_late_occupied_destination(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A newly occupied final LLVM directory may not be replaced."""
    observation = _host_observation(tmp_path)
    destination = tmp_path / llvm_validation.LLVM_ROOT
    native_ensure = llvm_validation._ensure_physical_import_parent  # pyright: ignore[reportPrivateUsage]
    inserted = False

    def occupy_after_parent_creation(root: Path) -> Path:
        nonlocal inserted
        parent = native_ensure(root)
        if parent == destination.parent and not inserted:
            inserted = True
            destination.mkdir()
        return parent

    monkeypatch.setattr(
        llvm_validation, "_ensure_physical_import_parent", occupy_after_parent_creation
    )
    with pytest.raises(llvm_validation.LlvmImportError, match="destination"):
        _ = llvm_validation.import_linux_llvm(tmp_path, observation)
    assert inserted
    assert destination.is_dir()
    assert not tuple(destination.iterdir())


@pytest.mark.parametrize("target", ("staging", "child"))
def test_linux_import_rejects_replaced_staging_without_deleting_foreign_tree(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    target: str,
) -> None:
    """Only the owned stage and child may be published or recursively deleted."""
    observation = _host_observation(tmp_path)
    staging = tmp_path / ".temp/llvm-import-linux-x86_64"
    foreign = tmp_path / "foreign-stage"
    foreign.mkdir()
    sentinel = foreign / "sentinel"
    _ = sentinel.write_bytes(b"unrelated foreign data")
    parked = tmp_path / "parked-owned"
    native_stage = llvm_validation._stage_linux_llvm  # pyright: ignore[reportPrivateUsage]

    def swapped_stage(
        staged: Path,
        observed: llvm_validation.LlvmHostObservation,
        *,
        expected_staged_inode: tuple[int, int] | None = None,
    ) -> None:
        native_stage(staged, observed, expected_staged_inode=expected_staged_inode)
        replacement = staging if target == "staging" else staged
        replacement.rename(parked)
        foreign.rename(replacement)

    monkeypatch.setattr(llvm_validation, "_stage_linux_llvm", swapped_stage)
    with pytest.raises(llvm_validation.LlvmImportError, match="staging"):
        _ = llvm_validation.import_linux_llvm(tmp_path, observation)
    original = staging if target == "staging" else staging / "llvm"
    assert (original / "sentinel").read_bytes() == b"unrelated foreign data"
    assert parked.exists()
    assert not (tmp_path / llvm_validation.LLVM_ROOT).exists()


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


@pytest.mark.parametrize("mutation", ("wrong-size", "same-size", "external-link"))
def test_windows_inspection_rejects_corrupted_fallback_alias(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mutation: str
) -> None:
    """Readiness may not reuse a detached copy whose PE bytes have changed."""
    root = _windows_tool_bundle(tmp_path)

    native_link = os.link

    def no_hardlinks(
        _source: str, _destination: str, *, dst_dir_fd: int | None = None
    ) -> None:
        raise OSError("cross-device import")

    monkeypatch.setattr(os, "link", no_hardlinks)
    aliases = llvm_validation.write_windows_llvm_aliases(root)
    assert llvm_validation.inspect_llvm(tmp_path, WINDOWS_PLATFORM).ready
    if mutation == "wrong-size":
        _ = aliases[0].write_bytes(FORGED_ALIAS_BYTES)
    elif mutation == "same-size":
        _ = aliases[0].write_bytes(b"x" * len(CLANG_BYTES))
    else:
        try:
            native_link(aliases[0], tmp_path / "borrowed-alias")
        except (OSError, NotImplementedError) as error:
            pytest.skip(f"hardlinks unavailable: {error}")
    assert (root / "bin/clang.exe").read_bytes() == CLANG_BYTES
    assert not llvm_validation.inspect_llvm(tmp_path, WINDOWS_PLATFORM).ready


def test_windows_inspection_rejects_externally_linked_imported_source(
    tmp_path: Path,
) -> None:
    """Extra names must not borrow source or alias trust after publication."""
    root = _windows_tool_bundle(tmp_path)
    aliases = llvm_validation.write_windows_llvm_aliases(root)
    source = root / "bin/clang.exe"
    assert llvm_validation.inspect_llvm(tmp_path, WINDOWS_PLATFORM).ready
    try:
        os.link(source, tmp_path / "external-clang")
    except (OSError, NotImplementedError) as error:
        pytest.skip(f"hardlinks unavailable: {error}")
    assert source.stat().st_nlink == 3
    assert aliases[0].stat().st_ino == source.stat().st_ino
    assert not llvm_validation.inspect_llvm(tmp_path, WINDOWS_PLATFORM).ready


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
        path: str | os.PathLike[str],
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        nonlocal inserted
        if Path(path) == wrapper or (path == wrapper.name and dir_fd is not None):
            inserted = True
            try:
                _ = wrapper.symlink_to(external)
            except (OSError, NotImplementedError) as error:
                pytest.skip(f"symlinks unavailable: {error}")
        return native_open(path, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(os, "open", racing_open)
    with pytest.raises(llvm_validation.LlvmImportError, match="exclusive"):
        llvm_validation._write_linux_alias(  # pyright: ignore[reportPrivateUsage]
            wrapper, "#!/bin/sh\n"
        )
    assert inserted
    assert wrapper.is_symlink()
    assert external.read_bytes() == b"protected wrapper destination"


def test_linux_wrapper_writer_does_not_follow_late_parent_swap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A swapped wrapper parent cannot write a foreign executable."""
    parent = tmp_path / "owned-wrapper-parent"
    parent.mkdir()
    wrapper = parent / "clang.bin"
    parked = tmp_path / "parked-wrapper-parent"
    outside = tmp_path / "outside-wrapper-parent"
    outside.mkdir()
    sentinel = outside / "sentinel"
    _ = sentinel.write_bytes(b"preserve foreign data")
    native_open = os.open
    swapped = False

    def swap_parent_at_open(
        path: str | os.PathLike[str],
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        nonlocal swapped
        if not swapped and (
            Path(path) == wrapper or (path == wrapper.name and dir_fd is not None)
        ):
            _ = parent.rename(parked)
            _ = parent.symlink_to(outside, target_is_directory=True)
            swapped = True
        return native_open(path, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(os, "open", swap_parent_at_open)
    with pytest.raises(llvm_validation.LlvmImportError, match="wrapper"):
        llvm_validation._write_linux_alias(  # pyright: ignore[reportPrivateUsage]
            wrapper, "#!/bin/sh\n"
        )
    assert swapped
    assert parent.is_symlink()
    assert sentinel.read_bytes() == b"preserve foreign data"
    assert not (outside / wrapper.name).exists()


def test_linux_wrapper_rejects_replaced_physical_parent_at_open(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A different physical directory cannot impersonate the admitted parent."""
    parent = tmp_path / "owned-wrapper-parent"
    parent.mkdir()
    wrapper = parent / "clang.bin"
    parked = tmp_path / "parked-wrapper-parent"
    outside = tmp_path / "foreign-wrapper-parent"
    outside.mkdir()
    sentinel = outside / "sentinel"
    _ = sentinel.write_bytes(b"foreign directory must survive")
    native_open = os.open
    replaced = False

    def replace_parent_at_open(
        path: str | os.PathLike[str],
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        nonlocal replaced
        if Path(path) == parent and not replaced:
            _ = parent.rename(parked)
            _ = outside.rename(parent)
            replaced = True
        return native_open(path, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(os, "open", replace_parent_at_open)
    with pytest.raises(llvm_validation.LlvmImportError, match="parent"):
        llvm_validation._write_linux_alias(  # pyright: ignore[reportPrivateUsage]
            wrapper, "#!/bin/sh\n"
        )
    assert replaced
    assert (parent / sentinel.name).read_bytes() == b"foreign directory must survive"
    assert not wrapper.exists()


def test_linux_wrapper_rejects_foreign_parent_descriptor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A native directory descriptor for another tree cannot create wrappers."""
    wrapper = tmp_path / "owned" / "clang.bin"
    wrapper.parent.mkdir()
    foreign = tmp_path / "foreign"
    foreign.mkdir()
    native_open = os.open
    substituted = False

    def substitute_parent(
        path: str | os.PathLike[str],
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        nonlocal substituted
        if Path(path) == wrapper.parent:
            substituted = True
            return native_open(foreign, flags)
        return native_open(path, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(os, "open", substitute_parent)
    with pytest.raises(llvm_validation.LlvmImportError, match="parent descriptor"):
        llvm_validation._write_linux_alias(  # pyright: ignore[reportPrivateUsage]
            wrapper, "#!/bin/sh\n"
        )
    assert substituted
    assert not wrapper.exists()
    assert not tuple(foreign.iterdir())


def test_linux_wrapper_parent_close_failure_is_typed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An owned directory close failure stays typed with its original cause."""
    wrapper = tmp_path / "clang.bin"
    native_open = os.open
    native_close = os.close
    opened_parent: set[int] = set()
    fault = OSError("synthetic wrapper parent close fault")

    def track_open(
        path: str | os.PathLike[str],
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        fd = native_open(path, flags, mode, dir_fd=dir_fd)
        if Path(path) == wrapper.parent:
            opened_parent.add(fd)
        return fd

    def fail_parent_close(fd: int) -> None:
        native_close(fd)
        if fd in opened_parent:
            opened_parent.remove(fd)
            raise fault

    with monkeypatch.context() as isolated:
        isolated.setattr(os, "open", track_open)
        isolated.setattr(os, "close", fail_parent_close)
        with pytest.raises(
            llvm_validation.LlvmImportError, match="wrapper parent close failed"
        ) as caught:
            llvm_validation._write_linux_alias(  # pyright: ignore[reportPrivateUsage]
                wrapper, "#!/bin/sh\n"
            )
    assert caught.value.__cause__ is fault
    assert not opened_parent
    assert wrapper.read_bytes() == b"#!/bin/sh\n"


def test_linux_wrapper_rejects_foreign_open_descriptor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A substituted open descriptor must not receive executable bytes."""
    wrapper = tmp_path / "clang.bin"
    outside = tmp_path / "outside-wrapper"
    original = b"external file must not be rewritten"
    _ = outside.write_bytes(original)
    native_open = os.open

    def wrong_open(
        path: str | os.PathLike[str],
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        if Path(path) == wrapper or (path == wrapper.name and dir_fd is not None):
            return native_open(outside, os.O_WRONLY)
        return native_open(path, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(os, "open", wrong_open)
    with pytest.raises(llvm_validation.LlvmImportError, match="descriptor"):
        llvm_validation._write_linux_alias(  # pyright: ignore[reportPrivateUsage]
            wrapper, "#!/bin/sh\n"
        )
    assert outside.read_bytes() == original
    assert not wrapper.exists()


@pytest.mark.parametrize("descriptor", [False, None, True, -1])
def test_linux_wrapper_rejects_nonnative_open_descriptor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, descriptor: object
) -> None:
    """Invalid open receipts cannot write or close unrelated descriptors."""
    wrapper = tmp_path / "clang.bin"

    native_open = os.open
    native_close = os.close
    parent_descriptors: set[int] = set()

    def wrong_open(
        path: str | os.PathLike[str],
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        if path == wrapper.name and dir_fd is not None:
            return cast("int", descriptor)
        opened = native_open(path, flags, mode, dir_fd=dir_fd)
        if Path(path) == wrapper.parent:
            parent_descriptors.add(opened)
        return opened

    def forbid_write(_fd: int, _content: bytes) -> int:
        raise AssertionError("foreign wrapper descriptor was written")

    def forbid_close(fd: int) -> None:
        if fd not in parent_descriptors:
            raise AssertionError("foreign wrapper descriptor was closed")
        native_close(fd)
        parent_descriptors.remove(fd)

    monkeypatch.setattr(os, "open", wrong_open)
    monkeypatch.setattr(os, "write", forbid_write)
    monkeypatch.setattr(os, "close", forbid_close)
    with pytest.raises(llvm_validation.LlvmImportError, match="descriptor"):
        llvm_validation._write_linux_alias(  # pyright: ignore[reportPrivateUsage]
            wrapper, "#!/bin/sh\n"
        )
    assert not wrapper.exists()

    assert not parent_descriptors


@pytest.mark.parametrize("status_source", ["descriptor", "path"])
def test_linux_wrapper_rejects_foreign_stat_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    status_source: str,
) -> None:
    """Matching stat attributes are not a native owned-file receipt."""
    wrapper = tmp_path / "clang.bin"
    native_fstat = os.fstat
    native_lstat = Path.lstat

    @final
    class ForeignStatus:
        def __init__(self, status: os.stat_result) -> None:
            self.st_mode = status.st_mode
            self.st_dev = status.st_dev
            self.st_ino = status.st_ino
            self.st_nlink = status.st_nlink
            self.st_size = status.st_size

    def foreign_fstat(fd: int) -> object:
        status = native_fstat(fd)
        return ForeignStatus(status) if S_ISREG(status.st_mode) else status

    def foreign_lstat(path: Path) -> object:
        status = native_lstat(path)
        return ForeignStatus(status) if path == wrapper else status

    with monkeypatch.context() as isolated:
        if status_source == "descriptor":
            isolated.setattr(os, "fstat", foreign_fstat)
        else:
            isolated.setattr(Path, "lstat", foreign_lstat)
        with pytest.raises(llvm_validation.LlvmImportError, match="descriptor"):
            llvm_validation._write_linux_alias(  # pyright: ignore[reportPrivateUsage]
                wrapper, "#!/bin/sh\n"
            )
    assert wrapper.read_bytes() == b""


def test_linux_wrapper_rejects_newly_hardlinked_descriptor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A second link created after exclusive open voids sole-file ownership."""
    wrapper = tmp_path / "clang.bin"
    outside = tmp_path / "outside-hardlink"
    native_open = os.open

    def linked_open(
        path: str | os.PathLike[str],
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        fd = native_open(path, flags, mode, dir_fd=dir_fd)
        if Path(path) == wrapper or (path == wrapper.name and dir_fd is not None):
            os.link(wrapper, outside)
        return fd

    monkeypatch.setattr(os, "open", linked_open)
    with pytest.raises(llvm_validation.LlvmImportError, match="descriptor"):
        llvm_validation._write_linux_alias(  # pyright: ignore[reportPrivateUsage]
            wrapper, "#!/bin/sh\n"
        )
    assert outside.read_bytes() == b""


@pytest.mark.parametrize("forgery", ("empty", "incorrect"))
def test_linux_wrapper_rejects_forged_complete_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    forgery: str,
) -> None:
    """A complete write receipt cannot authorize physically different bytes."""
    wrapper = tmp_path / "clang.bin"
    content = "#!/bin/sh\nexec true\n"
    native_write = os.write

    def forged_write(descriptor: int, data: bytes) -> int:
        if forgery == "incorrect":
            _ = native_write(descriptor, b"x" * len(data))
        return len(data)

    monkeypatch.setattr(os, "write", forged_write)
    with pytest.raises(llvm_validation.LlvmImportError, match="content"):
        llvm_validation._write_linux_alias(  # pyright: ignore[reportPrivateUsage]
            wrapper, content
        )
    assert wrapper.read_bytes() != content.encode()


def test_linux_wrapper_rejects_leaf_swapped_after_open(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A replaced wrapper path cannot be published after a valid write."""
    wrapper = tmp_path / "clang.bin"
    parked = tmp_path / "parked-wrapper"
    outside = tmp_path / "outside-wrapper"
    sentinel = b"external executable bytes"
    _ = outside.write_bytes(sentinel)
    native_write = os.write

    def swapped_write(descriptor: int, data: bytes) -> int:
        count = native_write(descriptor, data)
        wrapper.rename(parked)
        _ = wrapper.symlink_to(outside)
        return count

    monkeypatch.setattr(os, "write", swapped_write)
    with pytest.raises(llvm_validation.LlvmImportError, match="identity"):
        llvm_validation._write_linux_alias(  # pyright: ignore[reportPrivateUsage]
            wrapper, "#!/bin/sh\n"
        )
    assert parked.read_bytes() == b"#!/bin/sh\n"
    assert wrapper.is_symlink()
    assert outside.read_bytes() == sentinel


@pytest.mark.parametrize("target_kind", ["file", "directory"])
def test_llvm_physical_predicates_reject_masked_linked_ancestors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    target_kind: str,
) -> None:
    """A masked symlink ancestor is not a physical runtime path."""
    physical = tmp_path / "real-runtime"
    physical.mkdir()
    (physical / "nested").mkdir()
    _ = (physical / "nested" / "clang").write_bytes(CLANG_BYTES)
    linked = tmp_path / "linked-runtime"
    try:
        linked.symlink_to(physical, target_is_directory=True)
    except (OSError, NotImplementedError) as error:
        pytest.skip(f"directory symlinks unavailable: {error}")
    native_is_symlink = Path.is_symlink

    def masked_link_status(path: Path) -> bool:
        return False if path == linked else native_is_symlink(path)

    monkeypatch.setattr(Path, "is_symlink", masked_link_status)
    target = linked / "nested"
    if target_kind == "file":
        assert not llvm_validation._physical_file(  # pyright: ignore[reportPrivateUsage]
            target / "clang"
        )
    else:
        assert not llvm_validation._physical_directory(  # pyright: ignore[reportPrivateUsage]
            target
        )


@pytest.mark.parametrize("target_kind", ["file", "directory"])
def test_llvm_physical_predicates_reject_foreign_ancestor_stat(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    target_kind: str,
) -> None:
    """A foreign parent lstat cannot authorize descendant runtime evidence."""
    parent = tmp_path / "host-runtime"
    parent.mkdir()
    (parent / "nested").mkdir()
    _ = (parent / "nested" / "clang").write_bytes(CLANG_BYTES)
    native_lstat = Path.lstat

    @final
    class ForeignStat:
        def __init__(self, status: os.stat_result) -> None:
            self.st_mode = status.st_mode

    def forged_lstat(path: Path) -> object:
        status = native_lstat(path)
        return ForeignStat(status) if path == parent else status

    monkeypatch.setattr(Path, "lstat", forged_lstat)
    target = parent / "nested"
    if target_kind == "file":
        assert not llvm_validation._physical_file(  # pyright: ignore[reportPrivateUsage]
            target / "clang"
        )
    else:
        assert not llvm_validation._physical_directory(  # pyright: ignore[reportPrivateUsage]
            target
        )


def test_inspection_requires_completed_neutral_aliases(tmp_path: Path) -> None:
    """Readiness never accepts a partial imported LLVM tree."""
    observation = _host_observation(tmp_path)
    missing = llvm_validation.inspect_llvm(tmp_path, LINUX_PLATFORM)
    root = llvm_validation.import_linux_llvm(tmp_path, observation)
    ready = llvm_validation.inspect_llvm(tmp_path, LINUX_PLATFORM)

    assert missing.ready is False
    assert ready.ready is True
    assert ready.path == root / "jig-bin/clang.bin"


@pytest.mark.parametrize("mutation", ("bytes", "mode", "hardlink"))
def test_llvm_inspection_rejects_modified_linux_wrapper(
    tmp_path: Path, mutation: str
) -> None:
    """A published marker does not authorize drifted executable launchers."""
    root = llvm_validation.import_linux_llvm(tmp_path, _host_observation(tmp_path))
    wrapper = root / "jig-bin/clang.bin"
    assert llvm_validation.inspect_llvm(tmp_path, LINUX_PLATFORM).ready
    if mutation == "bytes":
        _ = wrapper.write_bytes(b"x" * wrapper.stat().st_size)
    elif mutation == "mode":
        wrapper.chmod(0o600)
    else:
        try:
            os.link(wrapper, tmp_path / "borrowed-wrapper")
        except (OSError, NotImplementedError) as error:
            pytest.skip(f"hardlinks unavailable: {error}")
    assert not llvm_validation.inspect_llvm(tmp_path, LINUX_PLATFORM).ready


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
    mkfifo = getattr(os, "mkfifo", None)
    if not callable(mkfifo):
        pytest.skip("FIFO unsupported")
    observation = _host_observation(tmp_path)
    create_fifo = cast("Callable[[Path], None]", mkfifo)
    create_fifo(observation.resource_dir / "foreign-fifo")
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


@pytest.mark.parametrize(
    "banner",
    (
        " clang version 22.1.8",
        "clang version 22.1.8 ",
        "clang version 22.1.8\t",
        "clang version 22.1.8\n\n",
        "\nclang version 22.1.8",
        "clang version 22.1.8\r",
    ),
)
def test_llvm_host_version_rejects_whitespace_forgery(banner: str) -> None:
    """A release receipt must not contain extra padding or blank lines."""
    assert not llvm_validation.llvm_version_matches(banner)


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
        "LLVM (http://llvm.org/):\n  LLVM version 22.1.8\n  Optimized build.",
        "LLVM (http://llvm.org/):\n  LLVM version 22.1.8\n  Debug build.",
        "clang version 22.1.8 (https://github.com/llvm/llvm-project 85ac560)",
        (
            "clang version 22.1.8 (https://github.com/llvm/llvm-project 85ac560)\n"
            "Target: x86_64-unknown-linux-gnu\nThread model: posix\n"
            "InstalledDir: /opt/LLVM-22.1.8-Linux-X64/bin"
        ),
        "Debian clang version 22.1.8 (22.1.8-1)",
        "Apple clang version 22.1.8 (clang-1600.0.26.3)",
    ),
)
def test_llvm_host_version_preserves_exact_native_banner(banner: str) -> None:
    """Normal full-release tool banners remain accepted."""
    assert llvm_validation.llvm_version_matches(banner)


@pytest.mark.parametrize(
    "banner",
    (
        "diagnostic: expected LLVM 22.1.8 but found 21.1.8",
        "clang version 21.1.8\nwarning: expected LLVM 22.1.8",
        "clang version 21.1.8\nclang version 22.1.8",
        "clang-format version 21.1.8\nLLVM version 22.1.8",
        "LLVM version 22.1.8",
        "clang-tidy unexpectedly failed: 22.1.8",
    ),
)
def test_llvm_host_version_rejects_diagnostic_or_secondary_version(
    banner: str,
) -> None:
    """An unrelated diagnostic or later line is not a pinned tool banner."""
    assert not llvm_validation.llvm_version_matches(banner)


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


@pytest.mark.skipif(
    os.name != HOST_POSIX, reason="requires physical source replacement"
)
@pytest.mark.parametrize("delivery", ["hardlink", "copy"])
def test_windows_aliases_refuse_late_replaced_host_tool(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, delivery: str
) -> None:
    """A replaced Windows source cannot authorize a neutral PE alias marker."""
    root = _windows_tool_bundle(tmp_path)
    source = root / "bin/clang.exe"
    parked = tmp_path / "parked-host-tool"
    foreign = tmp_path / "foreign-host-tool"
    _ = foreign.write_bytes(FOREIGN_TOOL_BYTES)

    with monkeypatch.context() as isolated:
        swapped = _replace_import_source_during_link(
            isolated, (source, parked, foreign), delivery=delivery
        )
        with pytest.raises(
            llvm_validation.LlvmImportError,
            match="LLVM import source file changed during copying",
        ):
            _ = llvm_validation.write_windows_llvm_aliases(root)
    assert swapped()
    assert parked.read_bytes() == CLANG_BYTES
    assert source.read_bytes() == FOREIGN_TOOL_BYTES
    assert not (root / llvm_validation.LLVM_IMPORT_MARKER).exists()


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

    def racing_link(
        source: str, destination: str, *, dst_dir_fd: int | None = None
    ) -> None:
        if Path(destination) == alias or (
            dst_dir_fd is not None and destination == alias.name
        ):
            try:
                alias.symlink_to(sentinel)
            except (OSError, NotImplementedError) as error:
                pytest.skip(f"symlinks unavailable: {error}")
            raise OSError("simulated cross-device link failure")
        real_link(source, destination, dst_dir_fd=dst_dir_fd)

    monkeypatch.setattr(os, "link", racing_link)
    with pytest.raises(llvm_validation.LlvmImportError, match="copy"):
        _ = llvm_validation.write_windows_llvm_aliases(root)
    assert sentinel.read_bytes() == b"external-data"
    assert not (root / llvm_validation.LLVM_IMPORT_MARKER).exists()


@pytest.mark.parametrize("forgery", ("missing", "wrong-inode", "foreign-receipt"))
def test_windows_aliases_reject_forged_hardlink_publication(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    forgery: str,
) -> None:
    """A claimed successful hardlink must physically name the same inode."""
    root = _windows_tool_bundle(tmp_path)
    alias = root / "jig-bin/clang.bin"
    native_link = os.link

    def forged_link(
        source: str, destination: str, *, dst_dir_fd: int | None = None
    ) -> object:
        if Path(destination) == alias or (
            dst_dir_fd is not None and destination == alias.name
        ):
            if forgery == "wrong-inode":
                _ = alias.write_bytes(b"not a hardlink")
            elif forgery == "foreign-receipt":
                native_link(source, destination, dst_dir_fd=dst_dir_fd)
                return False
            return
        native_link(source, destination, dst_dir_fd=dst_dir_fd)

    monkeypatch.setattr(os, "link", forged_link)
    with pytest.raises(llvm_validation.LlvmImportError, match="link"):
        _ = llvm_validation.write_windows_llvm_aliases(root)
    assert not (root / llvm_validation.LLVM_IMPORT_MARKER).exists()


def test_windows_alias_fallback_rejects_corrupted_copy(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A cross-device copy must prove exact bytes before marker publication."""
    root = _windows_tool_bundle(tmp_path)
    alias = root / "jig-bin/clang.bin"
    native_copy = shutil.copyfileobj

    def no_hardlinks(
        _source: str, _destination: str, *, dst_dir_fd: int | None = None
    ) -> None:
        raise OSError("cross-device import")

    def forged_copy(
        source: BufferedReader, target: BufferedRandom, length: int = 0
    ) -> None:
        if _copy_target_is_file(target, alias):
            _ = target.write(b"x" * len(CLANG_BYTES))
        else:
            native_copy(source, target, length)

    monkeypatch.setattr(os, "link", no_hardlinks)
    monkeypatch.setattr(shutil, "copyfileobj", forged_copy)
    with pytest.raises(llvm_validation.LlvmImportError, match="copy"):
        _ = llvm_validation.write_windows_llvm_aliases(root)
    assert not (root / llvm_validation.LLVM_IMPORT_MARKER).exists()


def test_windows_alias_fallback_rejects_leaf_swapped_during_copy(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A swapped alias may not receive source metadata or authorize imports."""
    root = _windows_tool_bundle(tmp_path)
    alias = root / "jig-bin/clang.bin"
    parked = tmp_path / "parked-alias"
    outside = tmp_path / "outside-alias"
    _ = outside.write_bytes(b"external metadata sentinel")
    outside.chmod(0o600)
    original_mode = outside.stat().st_mode
    native_copy = shutil.copyfileobj

    def no_hardlinks(
        _source: str, _destination: str, *, dst_dir_fd: int | None = None
    ) -> None:
        raise OSError("cross-device import")

    def swapped_copy(
        source: BufferedReader, target: BufferedRandom, length: int = 0
    ) -> None:
        native_copy(source, target, length)
        if _copy_target_is_file(target, alias):
            alias.rename(parked)
            _ = alias.symlink_to(outside)

    monkeypatch.setattr(os, "link", no_hardlinks)
    monkeypatch.setattr(shutil, "copyfileobj", swapped_copy)
    with pytest.raises(llvm_validation.LlvmImportError, match="copy"):
        _ = llvm_validation.write_windows_llvm_aliases(root)
    assert parked.read_bytes() == CLANG_BYTES
    assert alias.is_symlink()
    assert outside.read_bytes() == b"external metadata sentinel"
    assert outside.stat().st_mode == original_mode
    assert not (root / llvm_validation.LLVM_IMPORT_MARKER).exists()


def test_windows_alias_cross_device_fallback_preserves_tool_bytes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Exclusive fallback remains usable when ordinary host hardlinks fail."""
    root = _windows_tool_bundle(tmp_path)

    def no_hardlinks(
        _source: str, _destination: str, *, dst_dir_fd: int | None = None
    ) -> None:
        raise OSError("cross-device import")

    monkeypatch.setattr(os, "link", no_hardlinks)
    aliases = llvm_validation.write_windows_llvm_aliases(root)
    assert aliases[0].read_bytes() == CLANG_BYTES
    assert aliases[1].read_bytes() == TIDY_BYTES
    assert aliases[2].read_bytes() == FORMAT_BYTES
    assert llvm_validation.inspect_llvm(tmp_path, WINDOWS_PLATFORM).ready


def test_windows_alias_fallback_rejects_new_hardlink_after_open(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An alias linked during fallback copy cannot authorize neutral tools."""
    root = _windows_tool_bundle(tmp_path)
    alias = root / "jig-bin/clang.bin"
    outside = tmp_path / "linked-alias"
    native_link = os.link
    native_copy = shutil.copyfileobj

    def no_hardlinks(
        _source: str, _destination: str, *, dst_dir_fd: int | None = None
    ) -> None:
        raise OSError("cross-device import")

    def linked_copy(
        source: BufferedReader, target: BufferedRandom, length: int = 0
    ) -> None:
        if _copy_target_is_file(target, alias):
            native_link(alias, outside)
        native_copy(source, target, length)

    monkeypatch.setattr(os, "link", no_hardlinks)
    monkeypatch.setattr(shutil, "copyfileobj", linked_copy)
    with pytest.raises(llvm_validation.LlvmImportError, match="copy"):
        _ = llvm_validation.write_windows_llvm_aliases(root)
    assert outside.read_bytes() == CLANG_BYTES
    assert not (root / llvm_validation.LLVM_IMPORT_MARKER).exists()


@pytest.mark.parametrize("replacement", ("symlink", "physical"))
def test_llvm_import_hardlink_does_not_follow_late_destination_parent_swap(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    replacement: str,
) -> None:
    """Hardlink import cannot publish into a swapped foreign destination tree."""
    if os.name != "posix":
        pytest.skip("POSIX hardlink directory descriptor boundary")
    source = tmp_path / "host-tool"
    _ = source.write_bytes(b"pinned host binary bytes")
    parent = tmp_path / "owned-target"
    parent.mkdir()
    destination = parent / "clang"
    parked = tmp_path / "parked-target"
    foreign = tmp_path / "foreign-target"
    foreign.mkdir()
    sentinel = foreign / "sentinel"
    _ = sentinel.write_bytes(b"unrelated foreign data")
    native_link = os.link
    swapped = False

    def swap_during_link(
        src: str | os.PathLike[str],
        dst: str | os.PathLike[str],
        *,
        src_dir_fd: int | None = None,
        dst_dir_fd: int | None = None,
        follow_symlinks: bool = True,
    ) -> None:
        nonlocal swapped
        if not swapped:
            _ = parent.rename(parked)
            if replacement == "symlink":
                _ = parent.symlink_to(foreign, target_is_directory=True)
            else:
                _ = foreign.rename(parent)
            swapped = True
        native_link(
            src,
            dst,
            src_dir_fd=src_dir_fd,
            dst_dir_fd=dst_dir_fd,
            follow_symlinks=follow_symlinks,
        )

    monkeypatch.setattr(os, "link", swap_during_link)
    with pytest.raises(llvm_validation.LlvmImportError, match="import"):
        llvm_validation._link_or_copy(  # pyright: ignore[reportPrivateUsage]
            str(source), str(destination)
        )
    assert swapped
    foreign_tree = foreign if replacement == "symlink" else parent
    assert (foreign_tree / sentinel.name).read_bytes() == b"unrelated foreign data"
    assert not (foreign_tree / destination.name).exists()


def test_llvm_copy_file_rejects_existing_parent_replaced_during_mkdir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An idempotent mkdir cannot silently replace the admitted import tree."""
    if os.name != "posix":
        pytest.skip("POSIX import parent identity boundary")
    source = tmp_path / "host-source"
    _ = source.write_bytes(b"physical host source")
    parent = tmp_path / "owned-parent"
    parent.mkdir()
    destination = parent / "clang"
    parked = tmp_path / "parked-parent"
    foreign = tmp_path / "foreign-parent"
    foreign.mkdir()
    sentinel = foreign / "sentinel"
    _ = sentinel.write_bytes(b"foreign sentinel")
    native_mkdir = os.mkdir
    swapped = False

    def swap_after_existing_mkdir(
        path: str | os.PathLike[str],
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> None:
        nonlocal swapped
        try:
            native_mkdir(path, mode, dir_fd=dir_fd)
        except FileExistsError:
            if (path == parent.name or Path(path) == parent) and not swapped:
                _ = parent.rename(parked)
                _ = foreign.rename(parent)
                swapped = True
            raise

    monkeypatch.setattr(os, "mkdir", swap_after_existing_mkdir)
    with pytest.raises(llvm_validation.LlvmImportError, match="parent"):
        llvm_validation._copy_file(  # pyright: ignore[reportPrivateUsage]
            source, destination
        )
    assert swapped
    assert (parent / sentinel.name).read_bytes() == b"foreign sentinel"
    assert not destination.exists()


def test_llvm_copy_file_preserves_initial_parent_identity_across_reopen(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A later reopen must match the parent admitted before idempotent mkdir."""
    if os.name != "posix":
        pytest.skip("POSIX import parent identity boundary")
    source = tmp_path / "host-source"
    _ = source.write_bytes(b"host binary")
    parent = tmp_path / "owned-parent"
    parent.mkdir()
    destination = parent / "clang"
    parked = tmp_path / "parked-parent"
    foreign = tmp_path / "foreign-parent"
    foreign.mkdir()
    sentinel = foreign / "sentinel"
    _ = sentinel.write_bytes(b"foreign data")
    native_open_parent = llvm_validation._open_physical_import_parent  # pyright: ignore[reportPrivateUsage]
    swapped = False

    def swap_before_directory_reopen(path: Path, label: str) -> int:
        nonlocal swapped
        if path == parent and not swapped:
            _ = parent.rename(parked)
            _ = foreign.rename(parent)
            swapped = True
        return native_open_parent(path, label)

    monkeypatch.setattr(
        llvm_validation, "_open_physical_import_parent", swap_before_directory_reopen
    )
    with pytest.raises(llvm_validation.LlvmImportError, match="parent"):
        llvm_validation._copy_file(  # pyright: ignore[reportPrivateUsage]
            source, destination
        )
    assert swapped
    assert (parent / sentinel.name).read_bytes() == b"foreign data"
    assert not destination.exists()


@pytest.mark.parametrize("replacement", ("symlink", "physical"))
def test_llvm_import_fallback_copy_does_not_write_to_swapped_parent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    replacement: str,
) -> None:
    """Cross-device import cannot write foreign bytes before ownership checks."""
    if os.name != "posix":
        pytest.skip("POSIX import fallback descriptor boundary")
    source = tmp_path / "host-source"
    _ = source.write_bytes(b"host file for fallback copy")
    parent = tmp_path / "owned-fallback"
    parent.mkdir()
    destination = parent / "clang"
    parked = tmp_path / "parked-fallback"
    foreign = tmp_path / "foreign-fallback"
    foreign.mkdir()
    sentinel = foreign / "sentinel"
    _ = sentinel.write_bytes(b"foreign sentinel")
    native_open = os.open
    native_path_open = Path.open
    native_copy = shutil.copyfileobj
    swapped = False
    foreign_written = False

    def no_hardlinks(
        _source: str, _destination: str, *, dst_dir_fd: int | None = None
    ) -> None:
        raise OSError("cross-device")

    def swap_parent() -> None:
        nonlocal swapped
        if swapped:
            return
        _ = parent.rename(parked)
        if replacement == "symlink":
            _ = parent.symlink_to(foreign, target_is_directory=True)
        else:
            _ = foreign.rename(parent)
        swapped = True

    def racing_path_open(
        path: Path,
        mode: str = "r",
        buffering: int = -1,
        encoding: str | None = None,
        errors: str | None = None,
        newline: str | None = None,
    ):
        if path == destination and mode == "x+b":
            swap_parent()
        return native_path_open(
            path,
            mode,
            buffering=buffering,
            encoding=encoding,
            errors=errors,
            newline=newline,
        )

    def racing_os_open(
        path: str | os.PathLike[str],
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        if path == destination.name and dir_fd is not None:
            swap_parent()
        return native_open(path, flags, mode, dir_fd=dir_fd)

    def record_copy(
        source_stream: BufferedReader, target: BufferedRandom, length: int = 0
    ) -> None:
        nonlocal foreign_written
        native_copy(source_stream, target, length)
        foreign_tree = foreign if replacement == "symlink" else parent
        if (foreign_tree / destination.name).exists():
            foreign_written = True

    monkeypatch.setattr(os, "link", no_hardlinks)
    monkeypatch.setattr(os, "open", racing_os_open)
    monkeypatch.setattr(Path, "open", racing_path_open)
    monkeypatch.setattr(shutil, "copyfileobj", record_copy)
    with pytest.raises(llvm_validation.LlvmImportError, match="import"):
        llvm_validation._link_or_copy(  # pyright: ignore[reportPrivateUsage]
            str(source), str(destination)
        )
    assert swapped
    assert not foreign_written
    foreign_tree = foreign if replacement == "symlink" else parent
    assert (foreign_tree / sentinel.name).read_bytes() == b"foreign sentinel"
    assert not (foreign_tree / destination.name).exists()


def test_linux_import_cross_device_fallback_keeps_runtime_executable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verified fallback copies must retain Linux tool bytes and execute bits."""
    observation = _host_observation(tmp_path)
    for tool in (observation.clang, observation.clang_tidy, observation.clang_format):
        tool.chmod(0o755)

    def no_hardlinks(
        _source: str, _destination: str, *, dst_dir_fd: int | None = None
    ) -> None:
        raise OSError("cross-device import")

    monkeypatch.setattr(os, "link", no_hardlinks)
    root = llvm_validation.import_linux_llvm(tmp_path, observation)
    assert (root / "bin/clang").read_bytes() == CLANG_BYTES
    assert (root / "bin/clang").stat().st_mode & 0o111
    assert (root / "lib/libLLVM.so.22.1").read_bytes() == LLVM_BYTES
    assert (root / "lib/clang/22/stddef.h").read_bytes() == RESOURCE_BYTES
    assert llvm_validation.inspect_llvm(tmp_path, LINUX_PLATFORM).ready


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


@pytest.mark.parametrize("borrowed", ("alias", "source"))
def test_windows_aliases_reject_external_hardlink_before_marker(
    tmp_path: Path, borrowed: str
) -> None:
    """Matching PE bytes cannot authorize borrowed aliases before setup."""
    root = _windows_tool_bundle(tmp_path)
    source = root / "bin/clang.exe"
    alias = root / "jig-bin/clang.bin"
    alias.parent.mkdir()
    outside = tmp_path / "external-windows-clang"
    if borrowed == "alias":
        _ = outside.write_bytes(CLANG_BYTES)
        link_source, link_destination = outside, alias
    else:
        _ = alias.write_bytes(CLANG_BYTES)
        link_source, link_destination = source, outside
    try:
        os.link(link_source, link_destination)
    except (OSError, NotImplementedError) as error:
        pytest.skip(f"hardlinks unavailable: {error}")
    with pytest.raises(llvm_validation.LlvmImportError, match="alias"):
        _ = llvm_validation.write_windows_llvm_aliases(root)
    assert not (root / llvm_validation.LLVM_IMPORT_MARKER).exists()
    assert outside.read_bytes() == CLANG_BYTES


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

    def racing_open(
        path: str | os.PathLike[str],
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        if Path(path) == marker or (path == marker.name and dir_fd is not None):
            try:
                marker.symlink_to(sentinel)
            except (OSError, NotImplementedError) as error:
                pytest.skip(f"symlinks unavailable: {error}")
        return original(path, flags, mode, dir_fd=dir_fd)

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


@pytest.mark.parametrize(
    "suffix",
    (
        "\v",
        "\f",
        "\r",
        "\u2028",
        "\x85",
        "\n\x1b[31mforged diagnostic\x1b[0m",
    ),
)
def test_llvm_ldd_rejects_hidden_loader_controls(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, suffix: str
) -> None:
    """Unknown control separators cannot disappear from loader evidence."""
    library = tmp_path / "libLLVM.so.22.1"
    _ = library.write_bytes(LLVM_BYTES)
    clang = tmp_path / "clang"
    stdout = f"libLLVM.so.22.1 => {library} (0x1234){suffix}"

    def run(args: list[str], **_kwargs: object) -> sp.CompletedProcess[str]:
        assert args == ["ldd", str(clang)]
        return sp.CompletedProcess(args, 0, stdout=stdout, stderr="")

    monkeypatch.setattr(sp, "run", run)
    assert (
        llvm_validation._ldd_library(  # pyright: ignore[reportPrivateUsage]
            clang, "libLLVM.so.22.1"
        )
        is None
    )


@pytest.mark.parametrize("terminator", ("", "\n", "\r\n"))
def test_llvm_ldd_accepts_canonical_loader_line_endings(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, terminator: str
) -> None:
    """One normal process line ending does not invalidate a real mapping."""
    library = tmp_path / "libLLVM.so.22.1"
    _ = library.write_bytes(LLVM_BYTES)
    clang = tmp_path / "clang"
    stdout = f"\tlibLLVM.so.22.1 => {library} (0x1234){terminator}"

    def run(args: list[str], **_kwargs: object) -> sp.CompletedProcess[str]:
        assert args == ["ldd", str(clang)]
        return sp.CompletedProcess(args, 0, stdout=stdout, stderr="")

    monkeypatch.setattr(sp, "run", run)
    assert (
        llvm_validation._ldd_library(  # pyright: ignore[reportPrivateUsage]
            clang, "libLLVM.so.22.1"
        )
        == library
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


@pytest.mark.parametrize(
    "suffix", ["", " (not-an-address)", " (0x1234) diagnostics appended"]
)
def test_llvm_ldd_rejects_malformed_loader_mapping(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    suffix: str,
) -> None:
    """Malformed loader receipts cannot authorize a physical library."""
    library = tmp_path / "libLLVM.so.22.1"
    _ = library.write_bytes(LLVM_BYTES)
    line = f"libLLVM.so.22.1 => {library}{suffix}"

    def capture(arguments: list[str]) -> str:
        assert arguments == ["ldd", str(tmp_path / "clang")]
        return line

    monkeypatch.setattr(llvm_validation, "_capture", capture)
    entrypoint = vars(llvm_validation)["_ldd_library"]
    resolve = cast("Callable[[Path, str], Path | None]", entrypoint)
    assert resolve(tmp_path / "clang", "libLLVM.so.22.1") is None


def test_llvm_ldd_accepts_parenthesized_library_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Path parentheses are data, not a loader-address delimiter."""
    directory = tmp_path / "llvm (debug)"
    directory.mkdir()
    library = directory / "libLLVM.so.22.1"
    _ = library.write_bytes(LLVM_BYTES)
    line = f"libLLVM.so.22.1 => {library} (0x1234)"

    def capture(arguments: list[str]) -> str:
        assert arguments == ["ldd", str(tmp_path / "clang")]
        return line

    monkeypatch.setattr(llvm_validation, "_capture", capture)
    entrypoint = vars(llvm_validation)["_ldd_library"]
    resolve = cast("Callable[[Path, str], Path | None]", entrypoint)
    assert resolve(tmp_path / "clang", "libLLVM.so.22.1") == library


@pytest.mark.parametrize("second_line", ["same", "other", "missing"])
def test_llvm_ldd_rejects_ambiguous_duplicate_soname(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    second_line: str,
) -> None:
    """Conflicting or repeated loader receipts cannot select a trusted inode."""
    library = tmp_path / "libLLVM.so.22.1"
    _ = library.write_bytes(LLVM_BYTES)
    other = tmp_path / "elsewhere.so"
    _ = other.write_bytes(b"foreign library")
    suffixes = {
        "same": f"{library} (0x5678)",
        "other": f"{other} (0x5678)",
        "missing": "not found",
    }
    soname = "libLLVM.so.22.1"
    first = f"{soname} => {library} (0x1234)"
    second = f"{soname} => {suffixes[second_line]}"
    output = f"{first}\n{second}"

    def repeated_capture(arguments: list[str]) -> str:
        assert arguments == ["ldd", str(tmp_path / "clang")]
        return output

    monkeypatch.setattr(llvm_validation, "_capture", repeated_capture)
    entrypoint = vars(llvm_validation)["_ldd_library"]
    resolve = cast("Callable[[Path, str], Path | None]", entrypoint)
    assert resolve(tmp_path / "clang", soname) is None


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


@pytest.mark.parametrize(
    "receipt",
    (
        " {path}\n",
        "{path} \n",
        "{path}\n\n",
        "{path}\r",
        "\n{path}\n",
    ),
)
def test_llvm_host_resource_receipt_does_not_trim_ambiguous_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, receipt: str
) -> None:
    """Host resource paths cannot be recovered from padded or forged stdout."""
    resource = tmp_path / "resource-dir"
    resource.mkdir()
    clang = tmp_path / "clang"
    library = tmp_path / "libLLVM.so.22.1"
    _ = library.write_bytes(LLVM_BYTES)

    def run(args: list[str], **_kwargs: object) -> sp.CompletedProcess[str]:
        assert args == [str(clang), "-print-resource-dir"]
        return sp.CompletedProcess(
            args, 0, stdout=receipt.format(path=resource), stderr=""
        )

    monkeypatch.setattr(sp, "run", run)
    monkeypatch.setattr(llvm_validation, "_ldd_library", lambda _clang, _name: library)
    assert llvm_validation._linux_runtime_paths(clang) is None  # pyright: ignore[reportPrivateUsage]


def test_llvm_host_resource_receipt_requires_absolute_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A relative output cannot bind its meaning to the bootstrap cwd."""
    resource = tmp_path / "relative-resources"
    resource.mkdir()
    library = tmp_path / "libLLVM.so.22.1"
    _ = library.write_bytes(LLVM_BYTES)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(llvm_validation, "_capture", lambda _args: resource.name)
    monkeypatch.setattr(llvm_validation, "_ldd_library", lambda _clang, _name: library)
    assert (
        llvm_validation._linux_runtime_paths(  # pyright: ignore[reportPrivateUsage]
            tmp_path / "clang"
        )
        is None
    )


@pytest.mark.parametrize("terminator", ("", "\n", "\r\n"))
def test_llvm_host_resource_receipt_accepts_canonical_line_endings(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, terminator: str
) -> None:
    """Single native LF/CRLF terminators preserve a real resource path."""
    resource = tmp_path / "resource-dir"
    resource.mkdir()
    clang = tmp_path / "clang"
    library = tmp_path / "libLLVM.so.22.1"
    _ = library.write_bytes(LLVM_BYTES)

    def run(args: list[str], **_kwargs: object) -> sp.CompletedProcess[str]:
        assert args == [str(clang), "-print-resource-dir"]
        return sp.CompletedProcess(args, 0, stdout=f"{resource}{terminator}", stderr="")

    monkeypatch.setattr(sp, "run", run)
    monkeypatch.setattr(llvm_validation, "_ldd_library", lambda _clang, _name: library)
    assert llvm_validation._linux_runtime_paths(clang) == (  # pyright: ignore[reportPrivateUsage]
        resource,
        library,
        library,
    )


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


@pytest.mark.parametrize(
    "banner",
    (
        " clang version 22.1.8\n",
        "clang version 22.1.8 \n",
        "clang version 22.1.8\n\n",
        "clang version 22.1.8\r",
        "\nclang version 22.1.8",
    ),
)
def test_llvm_host_version_probe_preserves_untrusted_whitespace(
    monkeypatch: pytest.MonkeyPatch, banner: str
) -> None:
    """Subprocess capture cannot trim forged whitespace into a pinned version."""
    command = ["/usr/bin/clang", "--version"]

    def fake_run(args: list[str], **_kwargs: object) -> sp.CompletedProcess[str]:
        return sp.CompletedProcess(args, 0, stdout=banner, stderr="")

    monkeypatch.setattr(sp, "run", fake_run)
    assert not llvm_validation._linux_tool_versions_match(  # pyright: ignore[reportPrivateUsage]
        (Path(command[0]),) * 3
    )


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
        "clang version 22.1.8\n" if status == 0 else None
    )


@pytest.mark.parametrize(
    "diagnostic",
    ["warning: using alternative compiler", "\x1b[31mfailed\x1b[0m"],
)
def test_llvm_host_capture_refuses_success_with_diagnostics(
    monkeypatch: pytest.MonkeyPatch,
    diagnostic: str,
) -> None:
    """A zero process status does not neutralize a contradictory stderr."""
    command = ["clang", "--version"]

    def run(args: list[str], **kwargs: object) -> sp.CompletedProcess[str]:
        assert args == command
        assert kwargs["shell"] is False
        return sp.CompletedProcess(
            args, 0, stdout="clang version 22.1.8", stderr=diagnostic
        )

    monkeypatch.setattr(sp, "run", run)
    observe = cast(
        "Callable[[list[str]], str | None]", vars(llvm_validation)["_capture"]
    )
    assert observe(command) is None


@pytest.mark.parametrize("stream", ("stdout", "stderr"))
def test_llvm_host_capture_rejects_oversized_native_output(
    monkeypatch: pytest.MonkeyPatch,
    stream: str,
) -> None:
    """Optional host probe output may not be arbitrarily large."""
    command = ["clang", "--version"]

    def fake_run(args: list[str], **_kwargs: object) -> sp.CompletedProcess[str]:
        output = "x" * 16_385
        return sp.CompletedProcess(
            args,
            0,
            stdout=output if stream == "stdout" else "clang version 22.1.8",
            stderr=output if stream == "stderr" else "",
        )

    monkeypatch.setattr(sp, "run", fake_run)
    assert llvm_validation._capture(command) is None  # pyright: ignore[reportPrivateUsage]


@pytest.mark.parametrize("foreign", (False, True))
def test_llvm_host_capture_treats_timeout_as_unavailable(
    monkeypatch: pytest.MonkeyPatch,
    foreign: bool,
) -> None:
    """A hung optional host probe remains missing, without exception formatting."""

    class ForeignTimeout(sp.TimeoutExpired):
        @override
        def __str__(self) -> str:
            raise AssertionError("foreign LLVM timeout formatter invoked")

    def fake_run(_args: list[str], **_kwargs: object) -> None:
        timeout = ForeignTimeout if foreign else sp.TimeoutExpired
        raise timeout(cmd="clang", timeout=15)

    monkeypatch.setattr(sp, "run", fake_run)
    assert llvm_validation._capture(["clang", "--version"]) is None  # pyright: ignore[reportPrivateUsage]


def test_llvm_host_capture_binds_probe_deadline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Every optional LLVM host command must have a finite launch deadline."""
    seen: list[object] = []

    def fake_run(args: list[str], **kwargs: object) -> sp.CompletedProcess[str]:
        seen.append(kwargs.get("timeout"))
        return sp.CompletedProcess(args, 0, stdout="clang version 22.1.8", stderr="")

    monkeypatch.setattr(sp, "run", fake_run)
    assert llvm_validation._capture(["clang", "--version"]) == "clang version 22.1.8"  # pyright: ignore[reportPrivateUsage]
    assert seen == [15]


@pytest.mark.skipif(os.name != "posix", reason="requires POSIX directory descriptors")
@pytest.mark.parametrize("fault", [OSError, RuntimeError])
def test_llvm_publish_types_destination_parent_close_fault(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault: type[Exception],
) -> None:
    """Final import close failures preserve the native cause, not a raw fault."""
    staged = tmp_path / "staged-llvm"
    staged.mkdir()
    destination = tmp_path / ".dependencies" / "llvm" / LLVM_VERSION
    native_open = os.open
    native_close = os.close
    parent_descriptors: set[int] = set()
    close_fault = fault("foreign directory close failure")

    def track_open(
        path: str | os.PathLike[str],
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        descriptor = native_open(path, flags, mode, dir_fd=dir_fd)
        if Path(path) == destination.parent:
            parent_descriptors.add(descriptor)
        return descriptor

    def fail_parent_close(descriptor: int) -> None:
        native_close(descriptor)
        if descriptor in parent_descriptors:
            parent_descriptors.remove(descriptor)
            raise close_fault

    with monkeypatch.context() as isolated:
        isolated.setattr(os, "open", track_open)
        isolated.setattr(os, "close", fail_parent_close)
        with pytest.raises(
            llvm_validation.LlvmImportError, match="destination parent close failed"
        ) as caught:
            llvm_validation._publish_linux_import(  # pyright: ignore[reportPrivateUsage]
                tmp_path, staged, destination
            )
    assert caught.value.__cause__ is close_fault
    assert not parent_descriptors
    assert destination.is_dir()
    assert not staged.exists()


@pytest.mark.skipif(os.name != "posix", reason="requires POSIX directory descriptors")
def test_llvm_publish_rejects_physical_parent_replaced_during_rename(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A rename into a detached parent cannot report a successful import."""
    staged = tmp_path / "staged-llvm"
    staged.mkdir()
    parent = tmp_path / ".dependencies" / "llvm"
    parent.mkdir(parents=True)
    destination = parent / LLVM_VERSION
    parked = tmp_path / "parked-llvm-parent"
    foreign = tmp_path / "foreign-llvm-parent"
    foreign.mkdir()
    sentinel = foreign / "sentinel"
    _ = sentinel.write_bytes(b"foreign parent data")
    native_rename = llvm_validation._rename_linux_import_no_replace  # pyright: ignore[reportPrivateUsage]
    swapped = False

    def swap_during_rename(
        source: Path,
        target: str,
        *,
        src_dir_fd: int,
        dst_dir_fd: int,
    ) -> None:
        nonlocal swapped
        if not swapped:
            _ = parent.rename(parked)
            _ = foreign.rename(parent)
            swapped = True
        native_rename(source, target, src_dir_fd=src_dir_fd, dst_dir_fd=dst_dir_fd)

    monkeypatch.setattr(
        llvm_validation, "_rename_linux_import_no_replace", swap_during_rename
    )
    with pytest.raises(
        llvm_validation.LlvmImportError, match="destination parent changed"
    ):
        llvm_validation._publish_linux_import(  # pyright: ignore[reportPrivateUsage]
            tmp_path, staged, destination
        )
    assert swapped
    assert (parent / sentinel.name).read_bytes() == b"foreign parent data"
    assert not destination.exists()


@pytest.mark.parametrize("receipt", [None, False, 0])
def test_llvm_publish_rejects_false_success_without_source_move(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, receipt: object
) -> None:
    """A host no-op must not attest an import without moving the staged inode."""
    staged = tmp_path / "staged-llvm"
    staged.mkdir()
    destination = tmp_path / ".dependencies" / "llvm" / LLVM_VERSION
    calls = 0

    def false_replace(
        _source: Path,
        _target: str,
        *,
        src_dir_fd: int,
        dst_dir_fd: int,
    ) -> object:
        nonlocal calls
        calls += 1
        return receipt

    monkeypatch.setattr(
        llvm_validation, "_rename_linux_import_no_replace", false_replace
    )
    with pytest.raises(llvm_validation.LlvmImportError, match="publication"):
        llvm_validation._publish_linux_import(  # pyright: ignore[reportPrivateUsage]
            tmp_path, staged, destination
        )
    assert calls == 1
    assert staged.is_dir()
    assert not destination.exists()


@pytest.mark.skipif(os.name != "posix", reason="requires Linux directory descriptors")
@pytest.mark.parametrize("occupant", ["directory", "file", "symlink"])
def test_llvm_publish_never_overwrites_destination_inserted_after_stat(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, occupant: str
) -> None:
    """An occupied leaf must survive a race after the final absence check."""
    staged = tmp_path / "staged-llvm"
    staged.mkdir()
    destination = tmp_path / ".dependencies" / "llvm" / LLVM_VERSION
    foreign = tmp_path / "foreign"
    foreign.mkdir()
    sentinel = foreign / "sentinel"
    _ = sentinel.write_bytes(b"unrelated occupant target")
    native_stat = os.stat
    inserted_inode: tuple[int, int] | None = None

    def insert_after_absence_check(
        path: str | os.PathLike[str],
        *,
        dir_fd: int | None = None,
        follow_symlinks: bool = True,
    ) -> os.stat_result:
        nonlocal inserted_inode
        try:
            result = native_stat(path, dir_fd=dir_fd, follow_symlinks=follow_symlinks)
        except FileNotFoundError:
            if path == destination.name and dir_fd is not None:
                if occupant == "directory":
                    destination.mkdir()
                elif occupant == "file":
                    _ = destination.write_bytes(b"reserved")
                else:
                    _ = destination.symlink_to(foreign, target_is_directory=True)
                status = destination.lstat()
                inserted_inode = (status.st_dev, status.st_ino)
            raise
        return result

    with monkeypatch.context() as isolated:
        isolated.setattr(os, "stat", insert_after_absence_check)
        with pytest.raises(llvm_validation.LlvmImportError, match="destination"):
            llvm_validation._publish_linux_import(  # pyright: ignore[reportPrivateUsage]
                tmp_path, staged, destination
            )
    assert inserted_inode is not None
    current = destination.lstat()
    assert (current.st_dev, current.st_ino) == inserted_inode
    assert staged.is_dir()
    assert sentinel.read_bytes() == b"unrelated occupant target"


def test_llvm_publish_refuses_host_without_atomic_noreplace_rename(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Missing Linux no-replace support must fail before moving a toolkit."""
    staged = tmp_path / "staged-llvm"
    staged.mkdir()
    destination = tmp_path / ".dependencies" / "llvm" / LLVM_VERSION

    def no_renameat2(_name: object, *, use_errno: bool) -> object:
        assert use_errno
        return object()

    with monkeypatch.context() as isolated:
        isolated.setattr(llvm_validation.ctypes, "CDLL", no_renameat2)
        with pytest.raises(
            llvm_validation.LlvmImportError, match="native Linux no-replace"
        ):
            llvm_validation._publish_linux_import(  # pyright: ignore[reportPrivateUsage]
                tmp_path, staged, destination
            )
    assert staged.is_dir()
    assert not destination.exists()


@pytest.mark.skipif(os.name != "posix", reason="requires Linux directory descriptors")
@pytest.mark.parametrize("replacement", ["physical", "symlink"])
def test_llvm_publish_does_not_move_substituted_staging_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, replacement: str
) -> None:
    """Final rename must not move a foreign stage substituted after preflight."""
    staging = tmp_path / "staging"
    staging.mkdir()
    staged = staging / "llvm"
    staged.mkdir()
    _ = (staged / "owned").write_bytes(b"owned staging data")
    foreign = tmp_path / "foreign-staging"
    foreign.mkdir()
    foreign_staged = foreign / "llvm"
    foreign_staged.mkdir()
    sentinel = foreign_staged / "sentinel"
    _ = sentinel.write_bytes(b"foreign staging data")
    parked = tmp_path / "parked-staging"
    destination = tmp_path / ".dependencies" / "llvm" / LLVM_VERSION
    original_rename = llvm_validation._rename_linux_import_no_replace  # pyright: ignore[reportPrivateUsage]
    swapped = False

    def substitute_source(
        source: Path, target: str, *, src_dir_fd: int, dst_dir_fd: int
    ) -> None:
        nonlocal swapped
        if not swapped:
            _ = staging.rename(parked)
            if replacement == "symlink":
                _ = staging.symlink_to(foreign, target_is_directory=True)
            else:
                _ = foreign.rename(staging)
            swapped = True
        original_rename(source, target, src_dir_fd=src_dir_fd, dst_dir_fd=dst_dir_fd)

    monkeypatch.setattr(
        llvm_validation, "_rename_linux_import_no_replace", substitute_source
    )
    with pytest.raises(llvm_validation.LlvmImportError, match="staging|publication"):
        llvm_validation._publish_linux_import(  # pyright: ignore[reportPrivateUsage]
            tmp_path, staged, destination
        )
    assert swapped
    foreign_tree = foreign if replacement == "symlink" else staging
    assert (foreign_tree / "llvm/sentinel").read_bytes() == b"foreign staging data"
    assert (parked / "llvm/owned").read_bytes() == b"owned staging data"
    assert not destination.exists()


@pytest.mark.skipif(os.name != "posix", reason="requires Linux directory descriptors")
@pytest.mark.parametrize("fault", [OSError, RuntimeError])
def test_llvm_publish_types_staging_parent_close_fault(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: type[Exception]
) -> None:
    """Closing the admitted source parent must preserve a typed host cause."""
    staged = tmp_path / "staged-llvm"
    staged.mkdir()
    destination = tmp_path / ".dependencies" / "llvm" / LLVM_VERSION
    native_open = os.open
    native_close = os.close
    native_ensure = llvm_validation._ensure_physical_import_parent  # pyright: ignore[reportPrivateUsage]
    source_descriptors: set[int] = set()
    destination_ready = False

    def ensure_then_track(root: Path) -> Path:
        nonlocal destination_ready
        parent = native_ensure(root)
        destination_ready = True
        return parent

    close_fault = fault("foreign staging close fault")

    def track_open(
        path: str | os.PathLike[str],
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        descriptor = native_open(path, flags, mode, dir_fd=dir_fd)
        if destination_ready and Path(path) == staged.parent:
            source_descriptors.add(descriptor)
        return descriptor

    def fail_source_close(descriptor: int) -> None:
        native_close(descriptor)
        if descriptor in source_descriptors:
            source_descriptors.remove(descriptor)
            raise close_fault

    with monkeypatch.context() as isolated:
        isolated.setattr(os, "open", track_open)
        isolated.setattr(os, "close", fail_source_close)
        isolated.setattr(
            llvm_validation, "_ensure_physical_import_parent", ensure_then_track
        )
        with pytest.raises(
            llvm_validation.LlvmImportError, match="staging source parent close"
        ) as caught:
            llvm_validation._publish_linux_import(  # pyright: ignore[reportPrivateUsage]
                tmp_path, staged, destination
            )
    assert caught.value.__cause__ is close_fault
    assert not source_descriptors
    assert destination.is_dir()
    assert not staged.exists()


@pytest.mark.skipif(os.name != "posix", reason="requires physical directory pinning")
@pytest.mark.parametrize("replacement", ["physical", "symlink"])
def test_linux_import_does_not_create_stage_in_swapped_temp_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, replacement: str
) -> None:
    """A late .temp replacement must not receive any staging directory."""
    observation = _host_observation(tmp_path)
    temporary_root = tmp_path / ".temp"
    staging = temporary_root / "llvm-import-linux-x86_64"
    parked = tmp_path / "parked-temp-root"
    foreign = tmp_path / "foreign-temp-root"
    foreign.mkdir()
    sentinel = foreign / "sentinel"
    _ = sentinel.write_bytes(b"unrelated foreign data")
    native_mkdir = os.mkdir
    replaced = False

    def swap_at_stage_creation(
        path: str | os.PathLike[str],
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> None:
        nonlocal replaced
        if (Path(path) == staging or path == staging.name) and not replaced:
            _ = temporary_root.rename(parked)
            if replacement == "symlink":
                _ = temporary_root.symlink_to(foreign, target_is_directory=True)
            else:
                _ = foreign.rename(temporary_root)
            replaced = True
        native_mkdir(path, mode=mode, dir_fd=dir_fd)

    monkeypatch.setattr(os, "mkdir", swap_at_stage_creation)
    with pytest.raises(llvm_validation.LlvmImportError, match="staging"):
        _ = llvm_validation.import_linux_llvm(tmp_path, observation)
    assert replaced
    foreign_tree = foreign if replacement == "symlink" else temporary_root
    assert (foreign_tree / "sentinel").read_bytes() == b"unrelated foreign data"
    assert not (foreign_tree / staging.name).exists()
    assert not (tmp_path / llvm_validation.LLVM_ROOT).exists()


@pytest.mark.skipif(os.name != "posix", reason="requires physical directory pinning")
@pytest.mark.parametrize("replacement", ["physical", "symlink"])
def test_linux_import_does_not_create_child_in_swapped_staging_parent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, replacement: str
) -> None:
    """Staging child creation cannot use a replaced source directory alias."""
    observation = _host_observation(tmp_path)
    staging = tmp_path / ".temp/llvm-import-linux-x86_64"
    child = staging / "llvm"
    parked = tmp_path / "parked-stage"
    foreign = tmp_path / "foreign-stage"
    foreign.mkdir()
    sentinel = foreign / "sentinel"
    _ = sentinel.write_bytes(b"unrelated foreign data")
    native_mkdir = os.mkdir
    replaced = False

    def swap_at_child_creation(
        path: str | os.PathLike[str],
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> None:
        nonlocal replaced
        if (
            Path(path) == child or (path == child.name and dir_fd is not None)
        ) and not replaced:
            _ = staging.rename(parked)
            if replacement == "symlink":
                _ = staging.symlink_to(foreign, target_is_directory=True)
            else:
                _ = foreign.rename(staging)
            replaced = True
        native_mkdir(path, mode=mode, dir_fd=dir_fd)

    monkeypatch.setattr(os, "mkdir", swap_at_child_creation)
    with pytest.raises(llvm_validation.LlvmImportError, match="staging"):
        _ = llvm_validation.import_linux_llvm(tmp_path, observation)
    assert replaced
    foreign_tree = foreign if replacement == "symlink" else staging
    assert (foreign_tree / "sentinel").read_bytes() == b"unrelated foreign data"
    assert not (foreign_tree / child.name).exists()
    assert (parked / child.name).is_dir()
    assert not (tmp_path / llvm_validation.LLVM_ROOT).exists()


@pytest.mark.skipif(os.name != "posix", reason="requires Linux directory descriptors")
@pytest.mark.parametrize("replacement", ["physical", "symlink"])
def test_linux_import_does_not_create_aliases_in_swapped_stage(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, replacement: str
) -> None:
    """A foreign staging root may never receive Jig wrapper directories."""
    observation = _host_observation(tmp_path)
    staged = tmp_path / ".temp/llvm-import-linux-x86_64/llvm"
    alias_root = staged / "jig-bin"
    parked = tmp_path / "parked-stage-llvm"
    foreign = tmp_path / "foreign-alias-stage"
    foreign.mkdir()
    sentinel = foreign / "sentinel"
    _ = sentinel.write_bytes(b"unrelated alias parent")
    native_mkdir = os.mkdir
    replaced = False

    def swap_at_alias_directory_creation(
        path: str | os.PathLike[str],
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> None:
        nonlocal replaced
        if (Path(path) == alias_root or path == alias_root.name) and not replaced:
            _ = staged.rename(parked)
            if replacement == "symlink":
                _ = staged.symlink_to(foreign, target_is_directory=True)
            else:
                _ = foreign.rename(staged)
            replaced = True
        native_mkdir(path, mode=mode, dir_fd=dir_fd)

    monkeypatch.setattr(os, "mkdir", swap_at_alias_directory_creation)
    with pytest.raises(llvm_validation.LlvmImportError, match="staging|alias|parent"):
        _ = llvm_validation.import_linux_llvm(tmp_path, observation)
    assert replaced
    foreign_tree = foreign if replacement == "symlink" else staged
    assert (foreign_tree / "sentinel").read_bytes() == b"unrelated alias parent"
    assert not (foreign_tree / alias_root.name).exists()
    assert not (tmp_path / llvm_validation.LLVM_ROOT).exists()


@pytest.mark.skipif(os.name != "posix", reason="requires physical directory pinning")
@pytest.mark.parametrize("replacement", ["physical", "symlink"])
def test_linux_staging_root_creation_does_not_write_to_swapped_checkout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, replacement: str
) -> None:
    """An ancestor swap while creating .temp must not create foreign state."""
    root = tmp_path / "checkout"
    root.mkdir()
    parked = tmp_path / "parked-checkout"
    foreign = tmp_path / "foreign-checkout"
    foreign.mkdir()
    _ = (foreign / "sentinel").write_bytes(b"unrelated checkout")
    native_mkdir = os.mkdir
    swapped = False

    def swap_during_temp_creation(
        path: str | os.PathLike[str],
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> None:
        nonlocal swapped
        if not swapped and (Path(path) == root / ".temp" or path == ".temp"):
            _ = root.rename(parked)
            if replacement == "symlink":
                _ = root.symlink_to(foreign, target_is_directory=True)
            else:
                _ = foreign.rename(root)
            swapped = True
        native_mkdir(path, mode, dir_fd=dir_fd)

    with monkeypatch.context() as isolated:
        isolated.setattr(os, "mkdir", swap_during_temp_creation)
        with pytest.raises(llvm_validation.LlvmImportError):
            llvm_validation._admit_linux_import_staging(  # pyright: ignore[reportPrivateUsage]
                root, root / ".temp/llvm-import-linux-x86_64"
            )
    assert swapped
    foreign_root = foreign if replacement == "symlink" else root
    assert (foreign_root / "sentinel").read_bytes() == b"unrelated checkout"
    assert not (foreign_root / ".temp").exists()


@pytest.mark.skipif(os.name != "posix", reason="requires physical directory pinning")
@pytest.mark.parametrize("replacement", ["physical", "symlink"])
@pytest.mark.parametrize("component", [".dependencies", "llvm"])
def test_linux_destination_parent_creation_does_not_write_to_swapped_ancestor(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    replacement: str,
    component: str,
) -> None:
    """Creating the import parent cannot populate a substituted ancestor."""
    root = tmp_path / "checkout"
    root.mkdir()
    dependencies = root / ".dependencies"
    if component == "llvm":
        dependencies.mkdir()
    ancestor = root if component == ".dependencies" else dependencies
    parked = tmp_path / "parked-ancestor"
    foreign = tmp_path / "foreign-ancestor"
    foreign.mkdir()
    _ = (foreign / "sentinel").write_bytes(b"unrelated ancestor")
    native_mkdir = os.mkdir
    swapped = False

    def swap_during_parent_creation(
        path: str | os.PathLike[str],
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> None:
        nonlocal swapped
        if not swapped and (Path(path) == ancestor / component or path == component):
            _ = ancestor.rename(parked)
            if replacement == "symlink":
                _ = ancestor.symlink_to(foreign, target_is_directory=True)
            else:
                _ = foreign.rename(ancestor)
            swapped = True
        native_mkdir(path, mode, dir_fd=dir_fd)

    with monkeypatch.context() as isolated:
        isolated.setattr(os, "mkdir", swap_during_parent_creation)
        with pytest.raises(llvm_validation.LlvmImportError):
            llvm_validation._ensure_physical_import_parent(  # pyright: ignore[reportPrivateUsage]
                root
            )
    assert swapped
    foreign_root = foreign if replacement == "symlink" else ancestor
    assert (foreign_root / "sentinel").read_bytes() == b"unrelated ancestor"
    assert not (foreign_root / component).exists()


@pytest.mark.skipif(os.name != "posix", reason="requires POSIX physical inodes")
@pytest.mark.parametrize("replacement", ["physical", "symlink"])
def test_llvm_resource_copy_rejects_source_swapped_after_preflight(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    replacement: str,
) -> None:
    """Completed resource admission cannot be transferred to a new directory."""
    source = tmp_path / "host-resources"
    source.mkdir()
    _ = (source / "stdlib.h").write_bytes(RESOURCE_BYTES)
    stage = tmp_path / "stage/lib/clang"
    stage.mkdir(parents=True)
    destination = stage / "22"
    parked = tmp_path / "parked-resources"
    foreign = tmp_path / "foreign-resources"
    foreign.mkdir()
    _ = (foreign / "sentinel").write_bytes(b"unrelated host resource")
    original_check = llvm_validation._require_physical_resources  # pyright: ignore[reportPrivateUsage]
    swapped = False

    def swap_after_preflight(path: Path) -> None:
        nonlocal swapped
        original_check(path)
        if path == source and not swapped:
            _ = source.rename(parked)
            if replacement == "symlink":
                _ = source.symlink_to(foreign, target_is_directory=True)
            else:
                _ = foreign.rename(source)
            swapped = True

    with monkeypatch.context() as isolated:
        isolated.setattr(
            llvm_validation, "_require_physical_resources", swap_after_preflight
        )
        with pytest.raises(llvm_validation.LlvmImportError):
            llvm_validation._copy_resource_tree(  # pyright: ignore[reportPrivateUsage]
                source, destination
            )
    assert swapped
    foreign_path = foreign if replacement == "symlink" else source
    assert (foreign_path / "sentinel").read_bytes() == b"unrelated host resource"
    assert not destination.exists()


@pytest.mark.skipif(os.name != "posix", reason="requires POSIX physical inodes")
@pytest.mark.parametrize("replacement", ["physical", "symlink"])
@pytest.mark.parametrize("delivery", ["hardlink", "copy"])
def test_llvm_resource_copy_rejects_file_swapped_at_hardlink(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    replacement: str,
    delivery: str,
) -> None:
    """A renamed host header must not silently authorize foreign file bytes."""
    source = tmp_path / "host-resources"
    source.mkdir()
    header = source / "stdlib.h"
    _ = header.write_bytes(RESOURCE_BYTES)
    stage = tmp_path / "stage/lib/clang"
    stage.mkdir(parents=True)
    destination = stage / "22"
    parked = tmp_path / "parked-header"
    foreign = tmp_path / "foreign-header"
    _ = foreign.write_bytes(b"foreign resource bytes")
    native_link = os.link
    swapped = False

    def swapped_link(
        original: str | os.PathLike[str],
        target: str | os.PathLike[str],
        *,
        src_dir_fd: int | None = None,
        dst_dir_fd: int | None = None,
        follow_symlinks: bool = True,
    ) -> None:
        nonlocal swapped
        if Path(original) == header and not swapped:
            _ = header.rename(parked)
            if replacement == "symlink":
                _ = header.symlink_to(foreign)
            else:
                _ = foreign.rename(header)
            swapped = True
        if delivery == "copy" and Path(original) == header:
            raise OSError("simulated cross-device hardlink failure")
        native_link(
            original,
            target,
            src_dir_fd=src_dir_fd,
            dst_dir_fd=dst_dir_fd,
            follow_symlinks=follow_symlinks,
        )

    with monkeypatch.context() as isolated:
        isolated.setattr(os, "link", swapped_link)
        with pytest.raises(llvm_validation.LlvmImportError):
            llvm_validation._copy_resource_tree(  # pyright: ignore[reportPrivateUsage]
                source, destination
            )
    assert swapped
    assert parked.read_bytes() == RESOURCE_BYTES
    foreign_path = foreign if replacement == "symlink" else header
    assert foreign_path.read_bytes() == b"foreign resource bytes"


@pytest.mark.parametrize("forgery", ["outside", "dotdot", "foreign-type"])
def test_llvm_resource_preflight_rejects_forged_recursive_members(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    forgery: str,
) -> None:
    """A recursive status walk must not admit outside or nonpath receipts."""
    root = tmp_path / "host-resources"
    root.mkdir()
    outside = tmp_path / "outside.h"
    _ = outside.write_bytes(b"foreign resource content")
    member: Path | str
    if forgery == "dotdot":
        member = root / ".." / outside.name
    elif forgery == "foreign-type":
        member = str(outside)
    else:
        member = outside
    native_rglob = Path.rglob

    def forged_rglob(path: Path, pattern: str):  # type: ignore[no-untyped-def]
        if path == root and pattern == "*":
            return iter((member,))
        return native_rglob(path, pattern)

    with monkeypatch.context() as isolated:
        isolated.setattr(Path, "rglob", forged_rglob)
        with pytest.raises(llvm_validation.LlvmImportError, match="resource member"):
            llvm_validation._require_physical_resources(  # pyright: ignore[reportPrivateUsage]
                root
            )
    assert outside.read_bytes() == b"foreign resource content"


@pytest.mark.parametrize("kind", ["file", "directory", "foreign-type", "dotdot"])
def test_llvm_resource_copy_refuses_foreign_iterator_members(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
) -> None:
    """An iterator may not nominate resources outside its source directory."""
    source = tmp_path / "host-resources"
    source.mkdir()
    stage = tmp_path / "staged/lib/clang"
    stage.mkdir(parents=True)
    destination = stage / "22"
    outside = tmp_path / "foreign-resource"
    if kind == "directory":
        outside.mkdir()
        _ = (outside / "sentinel.h").write_bytes(b"untrusted header")
    else:
        _ = outside.write_bytes(b"untrusted header")
    native_iterdir = Path.iterdir

    def forged_iterdir(path: Path):  # type: ignore[no-untyped-def]
        if path == source:
            member: Path | str = outside
            if kind == "foreign-type":
                member = str(outside)
            elif kind == "dotdot":
                member = source / ".." / outside.name
            return iter((member,))
        return native_iterdir(path)

    with monkeypatch.context() as isolated:
        isolated.setattr(Path, "iterdir", forged_iterdir)
        with pytest.raises(llvm_validation.LlvmImportError, match="resource member"):
            llvm_validation._copy_resource_tree(  # pyright: ignore[reportPrivateUsage]
                source, destination
            )
    expected = outside / "sentinel.h" if kind == "directory" else outside
    assert expected.read_bytes() == b"untrusted header"
    assert not (destination / outside.name).exists()


@pytest.mark.skipif(os.name != "posix", reason="requires POSIX physical inodes")
def test_linux_import_does_not_publish_late_substituted_host_resource(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A substituted resource header must not reach the final LLVM import."""
    observation = _host_observation(tmp_path)
    header = observation.resource_dir / "stddef.h"
    parked = tmp_path / "parked-stddef"
    foreign = tmp_path / "foreign-header"
    _ = foreign.write_bytes(b"untrusted imported resource")
    native_link = os.link
    swapped = False

    def swap_header_at_link(
        original: str | os.PathLike[str],
        target: str | os.PathLike[str],
        *,
        src_dir_fd: int | None = None,
        dst_dir_fd: int | None = None,
        follow_symlinks: bool = True,
    ) -> None:
        nonlocal swapped
        if Path(original) == header and not swapped:
            _ = header.rename(parked)
            _ = foreign.rename(header)
            swapped = True
        native_link(
            original,
            target,
            src_dir_fd=src_dir_fd,
            dst_dir_fd=dst_dir_fd,
            follow_symlinks=follow_symlinks,
        )

    with monkeypatch.context() as isolated:
        isolated.setattr(os, "link", swap_header_at_link)
        with pytest.raises(
            llvm_validation.LlvmImportError,
            match="host LLVM resource file changed during copying",
        ):
            _ = llvm_validation.import_linux_llvm(tmp_path, observation)
    assert swapped
    assert parked.read_bytes() == RESOURCE_BYTES
    assert header.read_bytes() == b"untrusted imported resource"
    assert not (tmp_path / llvm_validation.LLVM_ROOT).exists()
    assert not (tmp_path / ".temp/llvm-import-linux-x86_64").exists()


@pytest.mark.skipif(os.name != "posix", reason="requires POSIX physical inodes")
@pytest.mark.parametrize("replacement", ["physical", "symlink"])
@pytest.mark.parametrize("depth", ["root", "nested"])
def test_llvm_resource_copy_rejects_late_source_directory_swap(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    replacement: str,
    depth: str,
) -> None:
    """A substituted host resource directory cannot become import authority."""
    source = tmp_path / "host-resources"
    (source / "include").mkdir(parents=True)
    _ = (source / "include/stdlib.h").write_bytes(RESOURCE_BYTES)
    stage = tmp_path / "stage/lib/clang"
    stage.mkdir(parents=True)
    destination = stage / "22"
    original = source if depth == "root" else source / "include"
    parked = tmp_path / "parked-resources"
    foreign = tmp_path / "foreign-resources"
    foreign.mkdir()
    _ = (foreign / "sentinel").write_bytes(b"unrelated host bytes")
    _ = (foreign / "malicious.h").write_bytes(b"foreign resource bytes")
    native_iterdir = Path.iterdir
    swapped = False

    def swapped_iterdir(directory: Path):  # type: ignore[no-untyped-def]
        nonlocal swapped
        if directory == original and not swapped:
            _ = original.rename(parked)
            if replacement == "symlink":
                _ = original.symlink_to(foreign, target_is_directory=True)
            else:
                _ = foreign.rename(original)
            swapped = True
        return native_iterdir(directory)

    with monkeypatch.context() as isolated:
        isolated.setattr(Path, "iterdir", swapped_iterdir)
        with pytest.raises(llvm_validation.LlvmImportError):
            llvm_validation._copy_resource_tree(  # pyright: ignore[reportPrivateUsage]
                source, destination
            )
    assert swapped
    foreign_root = foreign if replacement == "symlink" else original
    assert (foreign_root / "sentinel").read_bytes() == b"unrelated host bytes"
    assert not (destination / "malicious.h").exists()
    assert not (destination / "include/malicious.h").exists()


@pytest.mark.skipif(os.name != "posix", reason="requires physical directory pinning")
@pytest.mark.parametrize("replacement", ["physical", "symlink"])
@pytest.mark.parametrize("depth", ["root", "nested"])
def test_llvm_resource_copy_does_not_populate_swapped_destination_parent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    replacement: str,
    depth: str,
) -> None:
    """Resource traversal may not create files under a substituted parent."""
    source = tmp_path / "host-resources"
    (source / "include").mkdir(parents=True)
    _ = (source / "include/stdlib.h").write_bytes(b"host resource")
    root = tmp_path / "stage"
    parent = root / "lib/clang"
    parent.mkdir(parents=True)
    destination = parent / "22"
    swapped_parent = parent if depth == "root" else destination
    created = destination if depth == "root" else destination / "include"
    parked = tmp_path / "parked-resource-parent"
    foreign = tmp_path / "foreign-resource-parent"
    foreign.mkdir()
    _ = (foreign / "sentinel").write_bytes(b"unrelated resource directory")
    native_mkdir = os.mkdir
    swapped = False

    def swap_during_resource_creation(
        path: str | os.PathLike[str],
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> None:
        nonlocal swapped
        if not swapped and (Path(path) == created or path == created.name):
            _ = swapped_parent.rename(parked)
            if replacement == "symlink":
                _ = swapped_parent.symlink_to(foreign, target_is_directory=True)
            else:
                _ = foreign.rename(swapped_parent)
            swapped = True
        native_mkdir(path, mode, dir_fd=dir_fd)

    with monkeypatch.context() as isolated:
        isolated.setattr(os, "mkdir", swap_during_resource_creation)
        with pytest.raises(llvm_validation.LlvmImportError):
            llvm_validation._copy_resource_tree(  # pyright: ignore[reportPrivateUsage]
                source, destination
            )
    assert swapped
    foreign_parent = foreign if replacement == "symlink" else swapped_parent
    assert (foreign_parent / "sentinel").read_bytes() == b"unrelated resource directory"
    assert not (foreign_parent / created.name).exists()


@pytest.mark.skipif(os.name != "posix", reason="requires physical directory pinning")
@pytest.mark.parametrize("replacement", ["physical", "symlink"])
def test_llvm_copy_file_does_not_create_missing_parent_in_swapped_stage(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, replacement: str
) -> None:
    """A missing import bin directory cannot be created in a foreign stage."""
    source = tmp_path / "host-tool"
    _ = source.write_bytes(b"native clang bytes")
    staged = tmp_path / "owned-stage"
    staged.mkdir()
    destination = staged / "bin/clang"
    parked = tmp_path / "parked-stage"
    foreign = tmp_path / "foreign-stage"
    foreign.mkdir()
    _ = (foreign / "sentinel").write_bytes(b"foreign bytes")
    native_mkdir = os.mkdir
    swapped = False

    def swap_during_bin_creation(
        path: str | os.PathLike[str],
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> None:
        nonlocal swapped
        if not swapped and (Path(path) == destination.parent or path == "bin"):
            _ = staged.rename(parked)
            if replacement == "symlink":
                _ = staged.symlink_to(foreign, target_is_directory=True)
            else:
                _ = foreign.rename(staged)
            swapped = True
        native_mkdir(path, mode, dir_fd=dir_fd)

    with monkeypatch.context() as isolated:
        isolated.setattr(os, "mkdir", swap_during_bin_creation)
        with pytest.raises(llvm_validation.LlvmImportError, match="parent"):
            llvm_validation._copy_file(  # pyright: ignore[reportPrivateUsage]
                source, destination
            )
    assert swapped
    foreign_stage = foreign if replacement == "symlink" else staged
    assert (foreign_stage / "sentinel").read_bytes() == b"foreign bytes"
    assert not (foreign_stage / "bin").exists()


@pytest.mark.skipif(os.name != "posix", reason="requires physical directory pinning")
@pytest.mark.parametrize("replacement", ["physical", "symlink"])
def test_llvm_aliases_reject_parent_swapped_between_directory_and_wrapper(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, replacement: str
) -> None:
    """An alias parent exchanged after mkdir cannot receive wrapper bytes."""
    staged = tmp_path / "stage"
    staged.mkdir()
    alias_root = staged / "jig-bin"
    parked = tmp_path / "parked-aliases"
    foreign = tmp_path / "foreign-aliases"
    foreign.mkdir()
    _ = (foreign / "sentinel").write_bytes(b"foreign alias directory")
    original_write = llvm_validation._write_linux_alias  # pyright: ignore[reportPrivateUsage]
    swapped = False

    def substitute_before_first_wrapper(
        path: Path,
        content: str,
        *,
        expected_parent_inode: tuple[int, int] | None = None,
    ) -> None:
        nonlocal swapped
        if path.parent == alias_root and not swapped:
            _ = alias_root.rename(parked)
            if replacement == "symlink":
                _ = alias_root.symlink_to(foreign, target_is_directory=True)
            else:
                _ = foreign.rename(alias_root)
            swapped = True
        if expected_parent_inode is None:
            original_write(path, content)
        else:
            original_write(path, content, expected_parent_inode=expected_parent_inode)

    with monkeypatch.context() as isolated:
        isolated.setattr(
            llvm_validation, "_write_linux_alias", substitute_before_first_wrapper
        )
        with pytest.raises(llvm_validation.LlvmImportError, match="parent"):
            llvm_validation._write_linux_aliases(  # pyright: ignore[reportPrivateUsage]
                staged
            )
    assert swapped
    foreign_root = foreign if replacement == "symlink" else alias_root
    assert (foreign_root / "sentinel").read_bytes() == b"foreign alias directory"
    assert not (foreign_root / "clang.bin").exists()


@pytest.mark.skipif(os.name != "posix", reason="requires physical directory pinning")
@pytest.mark.parametrize("replacement", ["physical", "symlink"])
def test_linux_import_does_not_write_marker_to_substituted_stage(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, replacement: str
) -> None:
    """A late stage substitution cannot receive a valid LLVM import marker."""
    observation = _host_observation(tmp_path)
    staged = tmp_path / ".temp/llvm-import-linux-x86_64/llvm"
    parked = tmp_path / "parked-stage-llvm"
    foreign = tmp_path / "foreign-stage-llvm"
    foreign.mkdir()
    sentinel = foreign / "sentinel"
    _ = sentinel.write_bytes(b"unrelated foreign bytes")
    original_marker = llvm_validation._write_import_marker  # pyright: ignore[reportPrivateUsage]
    swapped = False

    def replace_before_marker(root: Path, platform_id: str, **kwargs: object) -> None:
        nonlocal swapped
        if root == staged and not swapped:
            _ = staged.rename(parked)
            if replacement == "symlink":
                _ = staged.symlink_to(foreign, target_is_directory=True)
            else:
                _ = foreign.rename(staged)
            swapped = True
        original_marker(root, platform_id, **kwargs)

    with monkeypatch.context() as isolated:
        isolated.setattr(llvm_validation, "_write_import_marker", replace_before_marker)
        with pytest.raises(llvm_validation.LlvmImportError):
            _ = llvm_validation.import_linux_llvm(tmp_path, observation)
    assert swapped
    foreign_stage = foreign if replacement == "symlink" else staged
    assert (foreign_stage / "sentinel").read_bytes() == b"unrelated foreign bytes"
    assert not (foreign_stage / llvm_validation.LLVM_IMPORT_MARKER).exists()
    assert not (tmp_path / llvm_validation.LLVM_ROOT).exists()


@pytest.mark.parametrize(
    "banner",
    (
        "clang version 22.1.8 forged diagnostic",
        "clang-format version 22.1.8\tunexpected suffix",
        "Ubuntu clang version 22.1.8 (https://llvm.org/) forged suffix",
        "clang version 22.1.8\nclang version 21.1.0",
        "clang version 22.1.8\nmalicious unrecognized line",
        "clang version 22.1.8\nTarget: x86_64-pc-linux-gnu\nerror: forged",
        "LLVM (http://llvm.org/):\n  LLVM version 22.1.8 arbitrary suffix",
        "LLVM (http://llvm.org/):\n  LLVM version 22.1.8\nclang version 21.1.0",
        "LLVM (http://llvm.org/):\n  LLVM version 22.1.8\n  Optimized build.\nInjected",
    ),
)
def test_llvm_host_version_rejects_appended_foreign_banner_text(banner: str) -> None:
    """A pinned release cannot mask arbitrary appended version report content."""
    assert not llvm_validation.llvm_version_matches(banner)


@pytest.mark.parametrize(
    "banner",
    [
        "clang version 22.1.8 (build\x00spoof)",
        "clang version 22.1.8 (build\x1b[31mspoof)",
        "clang version 22.1.8 (build\x7fspoof)",
        "clang version 22.1.8 (build\tspoof)",
        "clang version 22.1.8 (build\u200bspoof)",
        "clang version 22.1.8\vTarget: x86_64-pc-linux-gnu",
    ],
)
def test_llvm_host_version_rejects_nonprintable_banner_receipts(
    banner: str,
) -> None:
    """Control and invisible characters cannot forge a native LLVM banner."""
    assert not llvm_validation.llvm_version_matches(banner)


@pytest.mark.skipif(os.name != "posix", reason="requires physical directory pinning")
@pytest.mark.parametrize("fault", [OSError, RuntimeError])
def test_llvm_staging_marker_parent_stat_failure_is_typed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: type[Exception]
) -> None:
    """A parent descriptor receipt fault cannot escape the typed import boundary."""
    root = tmp_path / "owned-stage"
    root.mkdir()
    expected = root.lstat()
    tracked: set[int] = set()
    native_open_parent = llvm_validation._open_physical_import_parent  # pyright: ignore[reportPrivateUsage]
    native_fstat = os.fstat
    failure = fault("invalid parent status receipt")

    def track_parent(path: Path, label: str) -> int:
        descriptor = native_open_parent(path, label)
        if path == root:
            tracked.add(descriptor)
        return descriptor

    def fail_parent_receipt(descriptor: int) -> os.stat_result:
        if descriptor in tracked:
            raise failure
        return native_fstat(descriptor)

    with monkeypatch.context() as isolated:
        isolated.setattr(llvm_validation, "_open_physical_import_parent", track_parent)
        isolated.setattr(os, "fstat", fail_parent_receipt)
        with pytest.raises(
            llvm_validation.LlvmImportError, match="parent status"
        ) as caught:
            llvm_validation._write_import_marker(  # pyright: ignore[reportPrivateUsage]
                root,
                LINUX_PLATFORM,
                expected_parent_inode=(expected.st_dev, expected.st_ino),
            )
    assert caught.value.__cause__ is failure
    assert not (root / llvm_validation.LLVM_IMPORT_MARKER).exists()
    for descriptor in tracked:
        with pytest.raises(OSError):
            native_fstat(descriptor)


@pytest.mark.skipif(os.name != "posix", reason="requires POSIX parent swapping")
@pytest.mark.parametrize("replacement", ("symlink", "physical"))
@pytest.mark.parametrize("target", ("root", "alias"))
def test_windows_aliases_never_create_under_swapped_parent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, replacement: str, target: str
) -> None:
    """A late root or alias-directory swap must not populate foreign trees."""
    root = _windows_tool_bundle(tmp_path)
    alias_root = root / "jig-bin"
    if target == "alias":
        alias_root.mkdir()
    selected = root if target == "root" else alias_root
    parked = tmp_path / f"parked-windows-{target}"
    foreign = tmp_path / f"foreign-windows-{target}"
    foreign.mkdir()
    original_mkdir = os.mkdir
    swapped = False

    def swap_during_mkdir(
        path: str | os.PathLike[str],
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> None:
        nonlocal swapped
        if not swapped and (
            Path(path) == alias_root or (path == "jig-bin" and dir_fd is not None)
        ):
            selected.rename(parked)
            if replacement == "symlink":
                selected.symlink_to(foreign, target_is_directory=True)
            else:
                foreign.rename(selected)
            swapped = True
        original_mkdir(path, mode, dir_fd=dir_fd)

    with monkeypatch.context() as isolated:
        isolated.setattr(os, "mkdir", swap_during_mkdir)
        with pytest.raises(llvm_validation.LlvmImportError):
            _ = llvm_validation.write_windows_llvm_aliases(root)
    assert swapped
    outside = selected if replacement == "physical" else foreign
    assert not (outside / "clang.bin").exists()
    assert not (outside / "clang-tidy.bin").exists()
    assert not (outside / "clang-format.bin").exists()
    if target == "root":
        assert not (outside / "jig-bin").exists()
    assert not (outside / llvm_validation.LLVM_IMPORT_MARKER).exists()


@pytest.mark.skipif(os.name != "posix", reason="requires POSIX parent swapping")
@pytest.mark.parametrize("replacement", ("physical", "symlink"))
def test_windows_aliases_reject_root_swapped_before_marker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, replacement: str
) -> None:
    """Alias completion cannot mark a different physical bundle root ready."""
    root = _windows_tool_bundle(tmp_path)
    parked = tmp_path / "parked-windows-marker-root"
    foreign = tmp_path / "foreign-windows-marker-root"
    foreign.mkdir()
    original_check = llvm_validation._existing_import_marker  # pyright: ignore[reportPrivateUsage]
    calls = 0

    def swap_after_marker_check(path: Path, platform_id: str) -> bool:
        nonlocal calls
        result = original_check(path, platform_id)
        calls += 1
        if calls == 2:
            root.rename(parked)
            if replacement == "physical":
                foreign.rename(root)
            else:
                root.symlink_to(foreign, target_is_directory=True)
        return result

    with monkeypatch.context() as isolated:
        isolated.setattr(
            llvm_validation, "_existing_import_marker", swap_after_marker_check
        )
        with pytest.raises(llvm_validation.LlvmImportError):
            _ = llvm_validation.write_windows_llvm_aliases(root)
    assert calls == 2
    outside = root if replacement == "physical" else foreign
    assert not (outside / llvm_validation.LLVM_IMPORT_MARKER).exists()
    assert (parked / "jig-bin/clang.bin").read_bytes() == CLANG_BYTES


@pytest.mark.skipif(os.name != "posix", reason="requires POSIX directory pinning")
def test_windows_aliases_reject_unowned_directory_inserted_during_mkdir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A newly inserted alias directory is not owned by the importer."""
    root = _windows_tool_bundle(tmp_path)
    alias_root = root / "jig-bin"
    native_mkdir = os.mkdir
    inserted = False

    def insert_before_mkdir(
        path: str | os.PathLike[str],
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> None:
        nonlocal inserted
        if not inserted and (
            Path(path) == alias_root or (path == "jig-bin" and dir_fd is not None)
        ):
            native_mkdir(alias_root)
            inserted = True
        native_mkdir(path, mode, dir_fd=dir_fd)

    with monkeypatch.context() as isolated:
        isolated.setattr(os, "mkdir", insert_before_mkdir)
        with pytest.raises(llvm_validation.LlvmImportError):
            _ = llvm_validation.write_windows_llvm_aliases(root)
    assert inserted
    assert list(alias_root.iterdir()) == []
    assert not (root / llvm_validation.LLVM_IMPORT_MARKER).exists()


@pytest.mark.skipif(os.name != "posix", reason="requires POSIX pinned cleanup")
@pytest.mark.parametrize("replacement", ("physical", "symlink"))
@pytest.mark.parametrize("phase", ("success", "failure"))
def test_linux_import_cleanup_never_deletes_swapped_staging(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    replacement: str,
    phase: str,
) -> None:
    """Cleanup must never recursively remove a late foreign staging tree."""
    observation = _host_observation(tmp_path)
    staging = tmp_path / ".temp/llvm-import-linux-x86_64"
    parked = tmp_path / "parked-cleanup-stage"
    foreign = tmp_path / "foreign-cleanup-stage"
    foreign.mkdir()
    sentinel = foreign / "preserve"
    _ = sentinel.write_bytes(b"foreign staging contents")
    original_guard = llvm_validation._owned_staging_safe_to_clean  # pyright: ignore[reportPrivateUsage]
    original_stage = llvm_validation._stage_linux_llvm  # pyright: ignore[reportPrivateUsage]
    swapped = False

    def swap_after_check(
        path: Path,
        staged: Path,
        owned_staging: tuple[int, int],
        owned_child: tuple[int, int] | None,
    ) -> bool:
        nonlocal swapped
        ready = original_guard(path, staged, owned_staging, owned_child)
        if ready and not swapped:
            staging.rename(parked)
            if replacement == "physical":
                foreign.rename(staging)
            else:
                staging.symlink_to(foreign, target_is_directory=True)
            swapped = True
        return ready

    def fail_after_staging(
        staged: Path,
        observed: llvm_validation.LlvmHostObservation,
        *,
        expected_staged_inode: tuple[int, int] | None = None,
    ) -> None:
        original_stage(staged, observed, expected_staged_inode=expected_staged_inode)
        raise llvm_validation.LlvmImportError("intentional staging failure")

    with monkeypatch.context() as isolated:
        isolated.setattr(
            llvm_validation, "_owned_staging_safe_to_clean", swap_after_check
        )
        if phase == "failure":
            isolated.setattr(llvm_validation, "_stage_linux_llvm", fail_after_staging)
        with pytest.raises(llvm_validation.LlvmImportError):
            _ = llvm_validation.import_linux_llvm(tmp_path, observation)
    assert swapped
    outside = staging if replacement == "physical" else foreign
    assert (outside / "preserve").read_bytes() == b"foreign staging contents"
    if phase == "failure":
        assert (parked / "llvm/bin/clang").read_bytes() == CLANG_BYTES
        assert not (tmp_path / llvm_validation.LLVM_ROOT).exists()
    else:
        assert (tmp_path / llvm_validation.LLVM_ROOT / "bin/clang").is_file()


@pytest.mark.skipif(os.name != "posix", reason="requires POSIX pinned cleanup")
@pytest.mark.parametrize("replacement", ("physical", "symlink"))
def test_linux_import_cleanup_pins_stage_before_recursive_child_removal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, replacement: str
) -> None:
    """A swap during recursive removal must not delete foreign contents."""
    observation = _host_observation(tmp_path)
    staging = tmp_path / ".temp/llvm-import-linux-x86_64"
    parked = tmp_path / "parked-recursive-cleanup"
    foreign = tmp_path / "foreign-recursive-cleanup"
    foreign.mkdir()
    _ = (foreign / "preserve").write_bytes(b"foreign recursive cleanup")
    original_stage = llvm_validation._stage_linux_llvm  # pyright: ignore[reportPrivateUsage]
    original_remove = shutil.rmtree
    original_open = os.open
    swapped = False

    def fail_after_staging(
        staged: Path,
        observed: llvm_validation.LlvmHostObservation,
        *,
        expected_staged_inode: tuple[int, int] | None = None,
    ) -> None:
        original_stage(staged, observed, expected_staged_inode=expected_staged_inode)
        raise llvm_validation.LlvmImportError("expected staging error")

    def swap_during_remove(
        path: str | os.PathLike[str], *, dir_fd: int | None = None
    ) -> None:
        nonlocal swapped
        if not swapped and (Path(path) == staging or path == "bin"):
            staging.rename(parked)
            if replacement == "physical":
                foreign.rename(staging)
            else:
                staging.symlink_to(foreign, target_is_directory=True)
            swapped = True
        original_remove(path, dir_fd=dir_fd)

    def swap_before_nested_open(
        path: str | os.PathLike[str],
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        nonlocal swapped
        if not swapped and path == "bin" and dir_fd is not None:
            staging.rename(parked)
            if replacement == "physical":
                foreign.rename(staging)
            else:
                staging.symlink_to(foreign, target_is_directory=True)
            swapped = True
        return original_open(path, flags, mode, dir_fd=dir_fd)

    with monkeypatch.context() as isolated:
        isolated.setattr(llvm_validation, "_stage_linux_llvm", fail_after_staging)
        isolated.setattr(shutil, "rmtree", swap_during_remove)
        isolated.setattr(os, "open", swap_before_nested_open)
        with pytest.raises(llvm_validation.LlvmImportError):
            _ = llvm_validation.import_linux_llvm(tmp_path, observation)
    assert swapped
    outside = staging if replacement == "physical" else foreign
    assert (outside / "preserve").read_bytes() == b"foreign recursive cleanup"


@pytest.mark.skipif(os.name != "posix", reason="requires POSIX pinned cleanup")
def test_linux_import_rejects_false_successful_staging_cleanup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An absent native rmdir receipt cannot claim completed cleanup."""
    observation = _host_observation(tmp_path)
    staging = tmp_path / ".temp/llvm-import-linux-x86_64"
    native_rmdir = os.rmdir
    suppressed = False

    def false_cleanup_rmdir(
        path: str | os.PathLike[str], *, dir_fd: int | None = None
    ) -> object:
        nonlocal suppressed
        if Path(path) == staging or (path == staging.name and dir_fd is not None):
            suppressed = True
            return False
        return native_rmdir(path, dir_fd=dir_fd)

    with monkeypatch.context() as isolated:
        isolated.setattr(os, "rmdir", false_cleanup_rmdir)
        with pytest.raises(llvm_validation.LlvmImportError, match="cleanup"):
            _ = llvm_validation.import_linux_llvm(tmp_path, observation)
    assert suppressed
    assert staging.is_dir()
    assert (tmp_path / llvm_validation.LLVM_ROOT / "bin/clang").is_file()


@pytest.mark.skipif(os.name != "posix", reason="requires POSIX pinned cleanup")
@pytest.mark.parametrize("replacement", ("physical", "symlink"))
def test_linux_import_cleanup_rejects_child_swapped_after_status(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, replacement: str
) -> None:
    """The importer's owned staging child cannot be replaced before removal."""
    observation = _host_observation(tmp_path)
    child = tmp_path / ".temp/llvm-import-linux-x86_64/llvm"
    parked = tmp_path / "parked-staged-child"
    foreign = tmp_path / "foreign-staged-child"
    foreign.mkdir()
    _ = (foreign / "preserve").write_bytes(b"foreign child content")
    original_stage = llvm_validation._stage_linux_llvm  # pyright: ignore[reportPrivateUsage]
    original_stat = os.stat
    swapped = False

    def fail_after_staging(
        staged: Path,
        observed: llvm_validation.LlvmHostObservation,
        *,
        expected_staged_inode: tuple[int, int] | None = None,
    ) -> None:
        original_stage(staged, observed, expected_staged_inode=expected_staged_inode)
        raise llvm_validation.LlvmImportError("expected staging error")

    def swap_after_child_stat(
        path: str | os.PathLike[str],
        *,
        dir_fd: int | None = None,
        follow_symlinks: bool = True,
    ) -> os.stat_result:
        nonlocal swapped
        result = original_stat(path, dir_fd=dir_fd, follow_symlinks=follow_symlinks)
        if not swapped and path == child.name and dir_fd is not None:
            child.rename(parked)
            if replacement == "physical":
                foreign.rename(child)
            else:
                child.symlink_to(foreign, target_is_directory=True)
            swapped = True
        return result

    with monkeypatch.context() as isolated:
        isolated.setattr(llvm_validation, "_stage_linux_llvm", fail_after_staging)
        isolated.setattr(os, "stat", swap_after_child_stat)
        with pytest.raises(llvm_validation.LlvmImportError):
            _ = llvm_validation.import_linux_llvm(tmp_path, observation)
    assert swapped
    outside = child if replacement == "physical" else foreign
    assert (outside / "preserve").read_bytes() == b"foreign child content"
    assert (parked / "bin/clang").read_bytes() == CLANG_BYTES


@pytest.mark.skipif(os.name != "posix", reason="requires POSIX directory handles")
@pytest.mark.parametrize("replacement", ("physical", "symlink"))
def test_linux_import_cleanup_preserves_swapped_nested_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, replacement: str
) -> None:
    """Late nested directory swaps cannot make recursive cleanup delete foreign data."""
    observation = _host_observation(tmp_path)
    bin_dir = tmp_path / ".temp/llvm-import-linux-x86_64/llvm/bin"
    parked = tmp_path / "parked-nested-cleanup"
    foreign = tmp_path / "foreign-nested-cleanup"
    foreign.mkdir()
    _ = (foreign / "preserve").write_bytes(b"foreign nested data")
    original_stage = llvm_validation._stage_linux_llvm  # pyright: ignore[reportPrivateUsage]
    native_remove = shutil.rmtree
    native_open = os.open
    swapped = False

    def fail_after_staging(
        staged: Path,
        observed: llvm_validation.LlvmHostObservation,
        *,
        expected_staged_inode: tuple[int, int] | None = None,
    ) -> None:
        original_stage(staged, observed, expected_staged_inode=expected_staged_inode)
        raise llvm_validation.LlvmImportError("expected staging error")

    def swap_bin() -> None:
        nonlocal swapped
        bin_dir.rename(parked)
        if replacement == "physical":
            foreign.rename(bin_dir)
        else:
            bin_dir.symlink_to(foreign, target_is_directory=True)
        swapped = True

    def swap_before_rmtree(
        path: str | os.PathLike[str], *, dir_fd: int | None = None
    ) -> None:
        if not swapped and path == "bin" and dir_fd is not None:
            swap_bin()
        native_remove(path, dir_fd=dir_fd)

    def swap_before_open(
        path: str | os.PathLike[str],
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        if not swapped and path == "bin" and dir_fd is not None:
            swap_bin()
        return native_open(path, flags, mode, dir_fd=dir_fd)

    with monkeypatch.context() as isolated:
        isolated.setattr(llvm_validation, "_stage_linux_llvm", fail_after_staging)
        isolated.setattr(shutil, "rmtree", swap_before_rmtree)
        isolated.setattr(os, "open", swap_before_open)
        with pytest.raises(llvm_validation.LlvmImportError):
            _ = llvm_validation.import_linux_llvm(tmp_path, observation)
    assert swapped
    outside = bin_dir if replacement == "physical" else foreign
    assert (outside / "preserve").read_bytes() == b"foreign nested data"
    assert (parked / "clang").read_bytes() == CLANG_BYTES


@pytest.mark.skipif(os.name != "posix", reason="requires POSIX directory handles")
@pytest.mark.parametrize("replacement", ("physical", "symlink"))
def test_linux_import_cleanup_preserves_nested_directory_swapped_after_open(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, replacement: str
) -> None:
    """An opened nested directory remains bound when its pathname is replaced."""
    observation = _host_observation(tmp_path)
    bin_dir = tmp_path / ".temp/llvm-import-linux-x86_64/llvm/bin"
    parked = tmp_path / "parked-open-nested"
    foreign = tmp_path / "foreign-open-nested"
    foreign.mkdir()
    _ = (foreign / "preserve").write_bytes(b"foreign-after-open")
    original_stage = llvm_validation._stage_linux_llvm  # pyright: ignore[reportPrivateUsage]
    native_scandir = os.scandir
    swapped = False

    def fail_after_staging(
        staged: Path,
        observed: llvm_validation.LlvmHostObservation,
        *,
        expected_staged_inode: tuple[int, int] | None = None,
    ) -> None:
        original_stage(staged, observed, expected_staged_inode=expected_staged_inode)
        raise llvm_validation.LlvmImportError("expected staging error")

    def swap_before_scandir(
        path: str | os.PathLike[str] | int,
    ) -> os.ScandirIterator[str]:
        nonlocal swapped
        if type(path) is int and not swapped and bin_dir.is_dir():
            opened = os.fstat(path)
            named = bin_dir.lstat()
            if (opened.st_dev, opened.st_ino) == (named.st_dev, named.st_ino):
                bin_dir.rename(parked)
                if replacement == "physical":
                    foreign.rename(bin_dir)
                else:
                    bin_dir.symlink_to(foreign, target_is_directory=True)
                swapped = True
        return native_scandir(path)

    with monkeypatch.context() as isolated:
        isolated.setattr(llvm_validation, "_stage_linux_llvm", fail_after_staging)
        isolated.setattr(os, "scandir", swap_before_scandir)
        with pytest.raises(llvm_validation.LlvmImportError):
            _ = llvm_validation.import_linux_llvm(tmp_path, observation)
    assert swapped
    outside = bin_dir if replacement == "physical" else foreign
    assert (outside / "preserve").read_bytes() == b"foreign-after-open"


@pytest.mark.skipif(os.name != "posix", reason="requires POSIX directory handles")
@pytest.mark.parametrize("kind", ("file", "directory"))
def test_linux_cleanup_rejects_foreign_scandir_members(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: str
) -> None:
    """Foreign directory entries cannot escape cleanup through traversal names."""
    observation = _host_observation(tmp_path)
    child = tmp_path / ".temp/llvm-import-linux-x86_64/llvm"
    outside = tmp_path / "foreign-scandir-target"
    if kind == "directory":
        outside.mkdir()
        sentinel = outside / "preserve"
        _ = sentinel.write_bytes(b"not owned by LLVM")
    else:
        sentinel = outside
        _ = sentinel.write_bytes(b"not owned by LLVM")
    native_scandir = os.scandir
    native_stage = llvm_validation._stage_linux_llvm  # pyright: ignore[reportPrivateUsage]
    injected = False

    @final
    class ForgedEntry:
        name = "../../../foreign-scandir-target"

        def stat(self, *, follow_symlinks: bool = True) -> os.stat_result:
            return outside.lstat()

    @final
    class ForgedScan:
        def __enter__(self) -> list[ForgedEntry]:
            return [ForgedEntry()]

        def __exit__(
            self,
            exc_type: object,
            exc_value: object,
            traceback: object,
        ) -> None:
            return None

    def fail_after_stage(
        staged: Path,
        observed: llvm_validation.LlvmHostObservation,
        *,
        expected_staged_inode: tuple[int, int] | None = None,
    ) -> None:
        native_stage(staged, observed, expected_staged_inode=expected_staged_inode)
        raise llvm_validation.LlvmImportError("expected staging failure")

    def foreign_scandir(path: str | os.PathLike[str] | int) -> object:
        nonlocal injected
        if type(path) is int and not injected and child.is_dir():
            opened = os.fstat(path)
            named = child.lstat()
            if (opened.st_dev, opened.st_ino) == (named.st_dev, named.st_ino):
                injected = True
                return ForgedScan()
        return native_scandir(path)

    with monkeypatch.context() as isolated:
        isolated.setattr(llvm_validation, "_stage_linux_llvm", fail_after_stage)
        isolated.setattr(os, "scandir", foreign_scandir)
        with pytest.raises(llvm_validation.LlvmImportError):
            _ = llvm_validation.import_linux_llvm(tmp_path, observation)
    assert injected
    assert sentinel.read_bytes() == b"not owned by LLVM"
