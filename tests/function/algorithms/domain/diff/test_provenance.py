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
#   - The repository behavior implemented by this source file.
# - Must-Not:
#   - Bypass the contracts or authority boundaries of its owning package.
# - Allows:
#   - Inputs: values admitted by the file's public or internal interface.
#   - Outputs: deterministic values or effects declared by that interface.
#   - Side effects: only those explicitly owned by the implementation.
# - Split-When:
#   - Split when one responsibility gains an independent lifecycle.
# - Merge-When:
#   - Merge when another file owns the exact same responsibility.
# - Summary:
#   - Synthetic tests for exact external source revision pins.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#

"""Synthetic tests for exact external source revision pins."""

from __future__ import annotations

import builtins
import hashlib
import ntpath
import os
from contextlib import contextmanager
from pathlib import Path, PurePath, PurePosixPath, PureWindowsPath
from stat import S_IFDIR
from types import SimpleNamespace
from typing import TYPE_CHECKING, cast, override

import pytest
from algorithms.diff import provenance as provenance_module
from algorithms.diff.exact import ExactTreeError
from algorithms.diff.provenance import (
    SourcePin,
    SourcePinError,
    SourcePinEvidence,
    require_source_pin,
    source_snapshot_evidence,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Generator, Iterator, Sized

_COMMIT = "0123456789abcdef0123456789abcdef01234567"
_EXPECTED_FILE_COUNT = 3
_WINDOWS_OS_NAME = "nt"
_REPOSITORY_ERROR = "repository must be a non-empty string"
_ROOTS_ERROR = "exact immutable tuple type"
_ROOT_ENTRY_ERROR = "exact string paths"


def _write(root: Path, relative: str, data: bytes) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    _ = path.write_bytes(data)


def _expect(condition: object, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _pin(root: Path) -> SourcePin:
    evidence = source_snapshot_evidence(root, ("README", "src"))
    return SourcePin(
        repository="https://example.invalid/source.git",
        commit=_COMMIT,
        roots=("README", "src"),
        file_count=evidence.file_count,
        snapshot_sha256=evidence.snapshot_sha256,
    )


class _ForeignPinnedRoot(type(Path())):
    """Source-pin identity must never invoke untrusted path methods."""

    @override
    def __str__(self) -> str:
        message = "foreign source pin root path conversion executed"
        raise AssertionError(message)


@pytest.mark.parametrize("operation", ["snapshot", "require"])
def test_source_pin_rejects_foreign_path_subclasses_before_methods(
    tmp_path: Path, operation: str
) -> None:
    """Both source pin public APIs reject overridden root paths early."""
    foreign = _ForeignPinnedRoot(tmp_path / "untrusted")
    pin = SourcePin("repository", _COMMIT, ("src",), 1, "0" * 64)
    actions = {
        "snapshot": lambda: source_snapshot_evidence(foreign, ("src",)),
        "require": lambda: require_source_pin(foreign, pin),
    }
    with pytest.raises(SourcePinError, match="must use exact pathlib Path"):
        _ = actions[operation]()


def test_source_pin_rejects_non_utf8_root_metadata(tmp_path: Path) -> None:
    """Selected roots must be UTF-8 encodable before source inspection."""
    bad_root = "src\ud800"
    with pytest.raises(SourcePinError, match="UTF-8"):
        _ = SourcePin("repo", _COMMIT, (bad_root,), 1, "0" * 64)
    with pytest.raises(SourcePinError, match="UTF-8"):
        _ = source_snapshot_evidence(tmp_path, (bad_root,))


@pytest.mark.parametrize("invalid", ["nul\x00root", "unpaired\ud800root"])
def test_source_snapshot_rejects_nonportable_root_path(
    tmp_path: Path, invalid: str
) -> None:
    """Native filesystem path errors must remain source-pin failures."""
    with pytest.raises(SourcePinError, match="root path"):
        _ = source_snapshot_evidence(tmp_path / invalid, ("src",))


@pytest.mark.parametrize(
    "path",
    [
        "C:/absolute.c",
        "D:relative.c",
        "CON",
        "src/COM1/child.c",
        "src/trailing.",
        "src/stream:fork",
    ],
)
def test_source_pin_rejects_windows_drive_roots_before_traversal(
    tmp_path: Path,
    path: str,
) -> None:
    """Pinned root labels cannot change path authority across host OSes."""
    with pytest.raises(SourcePinError, match="unsafe pinned source path"):
        _ = SourcePin("repo", _COMMIT, (path,), 1, "0" * 64)
    with pytest.raises(SourcePinError, match="unsafe pinned source path"):
        _ = source_snapshot_evidence(tmp_path, (path,))


def _forged_absolute(path: PurePosixPath) -> bool:
    del path
    return False


def _forged_parts(path: PurePosixPath) -> tuple[str, ...]:
    del path
    return ("src", "safe.c")


def _forged_as_posix(path: PurePosixPath) -> str:
    del path
    return "src//unsafe.c"


def _forged_drive(path: PureWindowsPath) -> str:
    del path
    return ""


def _forged_parents(path: PurePosixPath) -> tuple[PurePosixPath, ...]:
    del path
    return ()


@pytest.mark.parametrize(
    ("unsafe_path", "owner", "method", "replacement"),
    [
        ("/absolute.c", PurePosixPath, "is_absolute", _forged_absolute),
        ("src/../unsafe.c", PurePosixPath, "parts", property(_forged_parts)),
        ("src//unsafe.c", PurePosixPath, "as_posix", _forged_as_posix),
        ("C:unsafe.c", PureWindowsPath, "drive", property(_forged_drive)),
    ],
)
def test_source_pin_rejects_post_import_path_spoof(
    monkeypatch: pytest.MonkeyPatch,
    unsafe_path: str,
    owner: type[PurePath],
    method: str,
    replacement: object,
) -> None:
    """Late pathlib hooks cannot certify malformed pin labels."""
    with monkeypatch.context() as patched:
        patched.setattr(owner, method, replacement)
        with pytest.raises(SourcePinError, match="unsafe pinned source path"):
            _ = SourcePin("repo", _COMMIT, (unsafe_path,), 1, "0" * 64)


def test_source_pin_rejects_post_import_parent_spoof(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Late pathlib parent hooks cannot hide overlapping root selections."""
    with monkeypatch.context() as patched:
        patched.setattr(PurePosixPath, "parents", property(_forged_parents))
        with pytest.raises(SourcePinError, match="must not overlap"):
            _ = SourcePin("repo", _COMMIT, ("src", "src/child.c"), 1, "0" * 64)


@pytest.mark.parametrize(
    "reserved_path", ["CON", "src/COM1/child.c", "src/trailing."]
)
def test_source_pin_reserved_roots_ignore_host_policy_mutation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    reserved_path: str,
) -> None:
    """Post-import callbacks cannot authorize nonportable source pins."""

    def forged_isreserved(path: str) -> bool:
        del path
        return False

    monkeypatch.setattr(ntpath, "isreserved", forged_isreserved)
    with pytest.raises(SourcePinError, match="unsafe pinned source path"):
        _ = SourcePin("repo", _COMMIT, (reserved_path,), 1, "0" * 64)
    with pytest.raises(SourcePinError, match="unsafe pinned source path"):
        _ = source_snapshot_evidence(tmp_path, (reserved_path,))


@pytest.mark.parametrize("invalid", ["nul\x00repo", "unpaired\ud800repo"])
def test_source_pin_rejects_nonportable_repository_label(
    invalid: str,
) -> None:
    """Distributable pin names must not carry unsafe string encodings."""
    with pytest.raises(SourcePinError, match="repository"):
        _ = SourcePin(invalid, _COMMIT, ("src",), 1, "0" * 64)


def test_source_snapshot_rejects_non_utf8_walk_filename(
    tmp_path: Path,
) -> None:
    """Non-UTF-8 filesystem entries cannot leak raw encoding exceptions."""
    if os.name == _WINDOWS_OS_NAME:
        pytest.skip("raw-byte filesystem names require POSIX")
    _write(tmp_path, "src/valid.c", b"valid source")
    filename = os.fsencode(tmp_path / "src") + b"/invalid-\xff.c"
    descriptor = os.open(filename, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        _ = os.write(descriptor, b"non-UTF8 path")
    finally:
        os.close(descriptor)
    with pytest.raises(SourcePinError, match="UTF-8"):
        _ = source_snapshot_evidence(tmp_path, ("src",))


def test_source_pin_rejects_linked_directory_after_enumeration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Reject aliases introduced between path discovery and file reads."""
    _write(tmp_path, "src/nested/source.c", b"source bytes")
    original_pinned_files = cast(
        "Callable[[Path, tuple[str, ...]], tuple[Path, ...]]",
        vars(provenance_module)["_pinned_files"],
    )
    changed = False

    def replace_after_discovery(root: Path, roots: tuple[str, ...]) -> tuple[Path, ...]:
        nonlocal changed
        files = original_pinned_files(root, roots)
        _ = (root / "src/nested").rename(root / "src/actual")
        try:
            (root / "src/nested").symlink_to(
                root / "src/actual", target_is_directory=True
            )
        except OSError:
            pytest.skip("directory symlinks unavailable")
        changed = True
        return files

    monkeypatch.setattr(provenance_module, "_pinned_files", replace_after_discovery)
    with pytest.raises(SourcePinError, match="symlink"):
        _ = source_snapshot_evidence(tmp_path, ("src",))
    _expect(changed, "post-enumeration alias fixture was not installed")


def test_source_pin_evidence_rejects_malformed_direct_construction() -> None:
    """Observed pin evidence uses the same count and digest domain as pins."""
    with pytest.raises(SourcePinError, match="positive integer"):
        _ = SourcePinEvidence(file_count=True, snapshot_sha256="0" * 64)
    with pytest.raises(SourcePinError, match="lowercase SHA-256"):
        _ = SourcePinEvidence(file_count=1, snapshot_sha256="A" * 64)


def test_pinned_snapshot_accepts_exact_selected_tree(tmp_path: Path) -> None:
    """Bind path set and bytes while ignoring unrelated external assets."""
    _write(tmp_path, "README", b"release")
    _write(tmp_path, "src/a.c", b"int a;\n")
    _write(tmp_path, "src/b.h", b"#define B 1\n")
    _write(tmp_path, "data/external.bin", b"not part of source pin")
    pin = _pin(tmp_path)

    observed = require_source_pin(tmp_path, pin)

    _expect(
        observed.file_count == _EXPECTED_FILE_COUNT,
        "pinned source count changed",
    )


def test_source_pin_rejects_post_import_as_posix_digest_spoof(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Late mutable path formatting cannot hide a changed source file name."""
    _write(tmp_path, "src/original.c", b"unchanged source")
    original = source_snapshot_evidence(tmp_path, ("src",))
    pin = SourcePin("repo", _COMMIT, ("src",), 1, original.snapshot_sha256)
    _ = (tmp_path / "src/original.c").rename(tmp_path / "src/renamed.c")
    original_as_posix = PurePosixPath.as_posix
    calls = 0

    def forged_as_posix(path: PurePosixPath) -> str:
        nonlocal calls
        if str(path) == "src/renamed.c":
            calls += 1
            return "src/original.c"
        return original_as_posix(path)

    with monkeypatch.context() as patched:
        patched.setattr(PurePosixPath, "as_posix", forged_as_posix)
        with pytest.raises(SourcePinError, match="snapshot mismatch"):
            _ = require_source_pin(tmp_path, pin)
    assert calls == 0, "late path formatter was consulted for source pin labels"


def test_pinned_snapshot_ignores_replaced_relative_path_labels(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A foreign path formatter cannot change file identity in a pin digest."""
    _write(tmp_path, "src/a.c", b"int a;\n")
    baseline = source_snapshot_evidence(tmp_path, ("src",))
    target = tmp_path / "src/a.c"
    native_relative = Path.relative_to
    calls = 0

    def forged_relative(
        path: Path, other: Path, *, walk_up: bool = False
    ) -> Path:
        nonlocal calls
        if path == target and other == tmp_path:
            calls += 1
            return Path("src/forged.c")
        return native_relative(path, other, walk_up=walk_up)

    monkeypatch.setattr(Path, "relative_to", forged_relative)
    actual = source_snapshot_evidence(tmp_path, ("src",))
    assert calls == 0
    assert actual == baseline


def test_pinned_snapshots_ignore_replaced_global_sha256(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A replaced global hash cannot pin two different trees as identical."""
    first_root = tmp_path / "original"
    second_root = tmp_path / "changed"
    _write(first_root, "src/code.c", b"trusted")
    _write(second_root, "src/code.c", b"altered")
    calls = 0

    class _CollidingHash:
        def update(self, _data: bytes) -> None:
            _ = _data

        def digest(self) -> bytes:
            return bytes(32)

        def hexdigest(self) -> str:
            return bytes(32).hex()

    def forged_sha256(_data: bytes = b"") -> _CollidingHash:
        nonlocal calls
        calls += 1
        return _CollidingHash()

    monkeypatch.setattr(hashlib, "sha256", forged_sha256)
    original = source_snapshot_evidence(first_root, ("src",))
    changed = source_snapshot_evidence(second_root, ("src",))
    _expect(original.file_count == changed.file_count, "fixture count diverged")
    _expect(
        original.snapshot_sha256 != changed.snapshot_sha256,
        "foreign hash gave distinct source trees the same pin",
    )
    _expect(calls == 0, "mutable process-global SHA-256 was consulted")


def test_pinned_snapshot_rejects_byte_or_path_change(tmp_path: Path) -> None:
    """Reject local mutation even when the named commit stays unchanged."""
    _write(tmp_path, "README", b"release")
    _write(tmp_path, "src/a.c", b"int a;\n")
    pin = _pin(tmp_path)
    _write(tmp_path, "src/a.c", b"int changed;\n")

    with pytest.raises(SourcePinError, match="snapshot mismatch"):
        _ = require_source_pin(tmp_path, pin)

    _write(tmp_path, "src/a.c", b"int a;\n")
    _write(tmp_path, "src/new.c", b"int new_file;\n")
    with pytest.raises(SourcePinError, match="file count mismatch"):
        _ = require_source_pin(tmp_path, pin)


@pytest.mark.parametrize("target", ["root", "selected", "parent"])
def test_source_pin_rejects_foreign_directory_status_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, target: str
) -> None:
    """A fabricated stat mode cannot authorize selected source traversal."""
    _write(tmp_path, "src/nested/source.c", b"trusted source")
    selected = {
        "root": tmp_path,
        "selected": tmp_path / "src/nested",
        "parent": tmp_path / "src",
    }[target]
    original_lstat = cast(
        "Callable[[Path], os.stat_result]",
        vars(provenance_module)["_NATIVE_PATH_LSTAT"],
    )
    forged = False

    def forge_status(path: Path) -> object:
        nonlocal forged
        if path == selected:
            forged = True
            return SimpleNamespace(st_mode=S_IFDIR | 0o755)
        return original_lstat(path)

    monkeypatch.setattr(provenance_module, "_NATIVE_PATH_LSTAT", forge_status)
    with pytest.raises(SourcePinError, match="status must be native"):
        _ = source_snapshot_evidence(tmp_path, ("src/nested",))
    _expect(forged, "fabricated directory status was not consumed")


def test_source_pin_rejects_foreign_file_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A fabricated complete file identity cannot certify snapshot stability."""
    _write(tmp_path, "src/a.c", b"trusted source")
    leaf = tmp_path / "src/a.c"
    native_status = leaf.lstat()
    original_lstat = cast(
        "Callable[[Path], os.stat_result]",
        vars(provenance_module)["_NATIVE_PATH_LSTAT"],
    )
    forged = SimpleNamespace(
        st_mode=native_status.st_mode,
        st_dev=native_status.st_dev,
        st_ino=native_status.st_ino,
        st_size=native_status.st_size,
        st_mtime_ns=native_status.st_mtime_ns,
        st_ctime_ns=native_status.st_ctime_ns,
    )

    def forge_receipt(path: Path) -> object:
        if path == leaf:
            return forged
        return original_lstat(path)

    monkeypatch.setattr(provenance_module, "_NATIVE_PATH_LSTAT", forge_receipt)
    receipt = cast(
        "Callable[[Path, str], tuple[int, ...]]",
        vars(provenance_module)["_pinned_file_receipt"],
    )
    with pytest.raises(SourcePinError, match="status must be native"):
        _ = receipt(leaf, "src/a.c")


class _HostileHostError(OSError):
    """An external filesystem hook must not control exception formatting."""

    @override
    def __str__(self) -> str:
        message = "hostile status error formatter executed"
        raise AssertionError(message)

    @override
    def __repr__(self) -> str:
        message = "hostile status error representation executed"
        raise AssertionError(message)


@pytest.mark.parametrize("operation", ["status", "junction", "resolve", "walk"])
def test_source_pin_errors_do_not_invoke_foreign_formatters(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, operation: str
) -> None:
    """Filesystem failures must remain typed without invoking foreign hooks."""
    _write(tmp_path, "src/a.c", b"trusted source")
    original_lstat = cast(
        "Callable[[Path], os.stat_result]",
        vars(provenance_module)["_NATIVE_PATH_LSTAT"],
    )
    original_junction = Path.is_junction
    original_resolve = Path.resolve
    original_scandir = os.scandir

    def fail_lstat(path: Path) -> object:
        if path == tmp_path:
            raise _HostileHostError("do not stringify")
        return original_lstat(path)

    def fail_junction(path: Path) -> bool:
        if path == tmp_path:
            raise _HostileHostError("do not stringify")
        return original_junction(path)

    def fail_resolve(path: Path, *, strict: bool = False) -> Path:
        if path == tmp_path:
            raise _HostileHostError("do not stringify")
        return original_resolve(path, strict=strict)

    def fail_scandir(path: str) -> object:
        if Path(path) == tmp_path / "src":
            raise _HostileHostError("do not stringify")
        return original_scandir(path)

    selected = {
        "status": (
            provenance_module, "_NATIVE_PATH_LSTAT", fail_lstat, "status failed"
        ),
        "junction": (
            provenance_module, "_NATIVE_PATH_IS_JUNCTION", fail_junction,
            "status failed",
        ),
        "resolve": (
            provenance_module,
            "_NATIVE_PATH_RESOLVE",
            fail_resolve,
            "resolution failed",
        ),
        "walk": (
            provenance_module, "_NATIVE_OS_SCANDIR", fail_scandir,
            "traversal failed",
        ),
    }[operation]
    owner, method_name, replacement, expected = selected
    monkeypatch.setattr(owner, method_name, replacement)
    with pytest.raises(SourcePinError, match=expected):
        _ = source_snapshot_evidence(tmp_path, ("src",))


class _HostileExactError(ExactTreeError):
    """A delegated byte reader must not control failure formatting."""

    @override
    def __str__(self) -> str:
        message = "hostile source read formatter executed"
        raise AssertionError(message)


def test_source_pin_read_failure_does_not_invoke_foreign_formatter(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failed read stays typed even if its error cannot be stringified."""
    _write(tmp_path, "README", b"trusted source")

    def fail_read(path: Path, context: str) -> bytes:
        _ = path, context
        raise _HostileExactError("do not stringify")

    monkeypatch.setattr(provenance_module, "read_exact_regular_file", fail_read)
    with pytest.raises(SourcePinError, match="pinned source read failed"):
        _ = source_snapshot_evidence(tmp_path, ("README",))


@pytest.mark.parametrize("failure_type", [PermissionError, ValueError, RuntimeError])
def test_pinned_source_root_status_error_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure_type: type[Exception],
) -> None:
    """An inaccessible pin root cannot be normalized into a weaker error."""
    original_lstat = cast(
        "Callable[[Path], os.stat_result]",
        vars(provenance_module)["_NATIVE_PATH_LSTAT"],
    )

    def fail_status(path: Path) -> object:
        if path == tmp_path:
            message = "blocked pin root"
            raise failure_type(message)
        return original_lstat(path)

    monkeypatch.setattr(provenance_module, "_NATIVE_PATH_LSTAT", fail_status)
    with pytest.raises(SourcePinError, match="pinned source status failed"):
        _ = source_snapshot_evidence(tmp_path, ("src",))


def test_source_pin_rejects_post_import_root_resolution_redirect(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A mutable host resolver cannot substitute another pinned source tree."""
    source = tmp_path / "source"
    redirected = tmp_path / "redirected"
    _write(source, "README", b"trusted")
    _write(redirected, "README", b"foreign")
    baseline = source_snapshot_evidence(source, ("README",))
    original_resolve = Path.resolve
    calls = 0

    def forged_resolve(path: Path, *, strict: bool = False) -> Path:
        nonlocal calls
        if path == source and strict:
            calls += 1
            return original_resolve(redirected, strict=True)
        return original_resolve(path, strict=strict)

    with monkeypatch.context() as patched:
        patched.setattr(Path, "resolve", forged_resolve)
        observed = source_snapshot_evidence(source, ("README",))
    assert calls == 0
    assert observed == baseline


@pytest.mark.parametrize("failure_type", [ValueError, RuntimeError])
def test_pinned_source_root_resolution_errors_fail_typed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure_type: type[Exception],
) -> None:
    """Do not leak invalid or cyclic root normalization from source-pin APIs."""
    _write(tmp_path, "README", b"pinned")
    original_resolve = Path.resolve

    def fail_resolve(path: Path, *, strict: bool = False) -> Path:
        if path == tmp_path:
            message = "blocked pin root resolution"
            raise failure_type(message)
        return original_resolve(path, strict=strict)

    monkeypatch.setattr(provenance_module, "_NATIVE_PATH_RESOLVE", fail_resolve)
    with pytest.raises(SourcePinError, match="pinned source root resolution failed"):
        _ = source_snapshot_evidence(tmp_path, ("README",))


def test_pinned_source_rejects_linked_root_when_supported(
    tmp_path: Path,
) -> None:
    """Do not resolve a linked pin root before applying provenance policy."""
    target = tmp_path / "target"
    _write(target, "README", b"release")
    _write(target, "src/a.c", b"int a;" + bytes((10,)))
    linked = tmp_path / "linked"
    try:
        linked.symlink_to(target, target_is_directory=True)
    except OSError:
        pytest.skip("directory symlink creation is unavailable on this host")

    with pytest.raises(SourcePinError, match="symlink is not accepted"):
        _ = source_snapshot_evidence(linked, ("README", "src"))


@pytest.mark.parametrize("status_hook", ["path", "os"])
def test_source_pin_rejects_linked_selection_after_status_hook_spoof(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    status_hook: str,
) -> None:
    """Native-looking follow-link stat must not certify an out-of-tree pin."""
    root = tmp_path / "source"
    root.mkdir()
    outside = tmp_path / "outside"
    _write(outside, "private.c", b"outside the pinned source")
    try:
        (root / "linked").symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("directory symlinks unavailable")
    with monkeypatch.context() as patched:
        if status_hook == "path":
            patched.setattr(Path, "lstat", Path.stat)
        else:
            patched.setattr(os, "lstat", os.stat)
        with pytest.raises(SourcePinError, match="symlink is not accepted"):
            _ = source_snapshot_evidence(root, ("linked",))


def test_pinned_source_accepts_regular_nested_root(tmp_path: Path) -> None:
    """A valid multi-component source root remains eligible for hashing."""
    _write(tmp_path, "src/nested/leaf.c", b"valid source")
    evidence = source_snapshot_evidence(tmp_path, ("src/nested",))
    _expect(evidence.file_count == 1, "nested pinned root lost its file")


@pytest.mark.parametrize("outside", [False, True])
def test_pinned_source_rejects_linked_intermediate_root_component(
    tmp_path: Path,
    *,
    outside: bool,
) -> None:
    """Selected subpaths cannot traverse symlink ancestors."""
    root = tmp_path / "source"
    root.mkdir()
    actual = tmp_path / "outside" if outside else root / "real"
    _write(actual, "nested/leaf.c", b"secret source")
    try:
        (root / "link").symlink_to(actual, target_is_directory=True)
    except OSError:
        pytest.skip("directory symlink creation is unavailable")

    with pytest.raises(SourcePinError, match="symlink is not accepted"):
        _ = source_snapshot_evidence(root, ("link/nested",))


@pytest.mark.parametrize("walk_hook", ["path", "os"])
def test_source_pin_rejects_mutation_hidden_by_late_walk_hook(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    walk_hook: str,
) -> None:
    """A domain hook cannot hide an extra source file from pin identity."""
    _write(tmp_path, "src/original.c", b"original")
    baseline = source_snapshot_evidence(tmp_path, ("src",))
    pin = SourcePin("repo", _COMMIT, ("src",), 1, baseline.snapshot_sha256)
    _write(tmp_path, "src/extra.c", b"new source")
    selected = tmp_path / "src"
    native_scandir = os.scandir
    calls = 0

    def forged_walk(
        path: Path,
        *,
        top_down: bool = True,
        on_error: Callable[[OSError], object] | None = None,
        follow_symlinks: bool = False,
    ) -> Iterator[tuple[Path, list[str], list[str]]]:
        nonlocal calls
        if path == selected:
            calls += 1
            yield path, [], ["original.c"]
        else:
            yield from Path.walk(
                path,
                top_down=top_down,
                on_error=on_error,
                follow_symlinks=follow_symlinks,
            )

    @contextmanager
    def filtered_scan() -> Generator[Iterator[os.DirEntry[str]]]:
        with native_scandir(selected) as entries:
            yield (item for item in entries if item.name != "extra.c")

    def forged_scandir(path: Path | str | bytes) -> object:
        nonlocal calls
        if os.fspath(path) == os.fspath(selected):
            calls += 1
            return filtered_scan()
        return native_scandir(path)

    with monkeypatch.context() as patched:
        if walk_hook == "path":
            patched.setattr(Path, "walk", forged_walk)
        else:
            patched.setattr(os, "scandir", forged_scandir)
        with pytest.raises(SourcePinError, match="file count mismatch"):
            _ = require_source_pin(tmp_path, pin)
    assert calls == 0, "late host traversal hook received source identity authority"


def test_pinned_snapshot_walk_errors_fail_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A recursive scan failure cannot disappear from a revision pin."""
    selected = tmp_path / "src"
    selected.mkdir()

    def fail_scandir(path: str) -> object:
        del path
        raise PermissionError("blocked pinned source")

    monkeypatch.setattr(provenance_module, "_NATIVE_OS_SCANDIR", fail_scandir)
    with pytest.raises(SourcePinError, match="pinned source traversal failed"):
        _ = source_snapshot_evidence(tmp_path, ("src",))


@pytest.mark.parametrize("failure_type", [OSError, ValueError, RuntimeError])
def test_pinned_source_junction_status_errors_fail_typed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure_type: type[Exception],
) -> None:
    """A failed host junction query cannot escape the source-pin boundary."""
    _write(tmp_path, "src/leaf.c", b"int leaf;\n")
    selected = tmp_path / "src" / "leaf.c"
    original_is_junction = cast(
        "Callable[[Path], bool]",
        vars(provenance_module)["_NATIVE_PATH_IS_JUNCTION"],
    )

    def fail_junction(path: Path) -> bool:
        if path == selected:
            message = "blocked junction query"
            raise failure_type(message)
        return original_is_junction(path)

    monkeypatch.setattr(provenance_module, "_NATIVE_PATH_IS_JUNCTION", fail_junction)
    with pytest.raises(SourcePinError, match="pinned source status failed"):
        _ = source_snapshot_evidence(tmp_path, ("src",))


@pytest.mark.parametrize("failure_type", [OSError, ValueError, RuntimeError])
def test_pinned_source_walk_iterator_errors_fail_typed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure_type: type[Exception],
) -> None:
    """Errors from a source walk iterator remain typed pin failures."""
    _write(tmp_path, "src/leaf.c", b"int leaf;\n")

    original_scandir = os.scandir

    @contextmanager
    def fail_scandir(path: str) -> Generator[Iterator[os.DirEntry[str]]]:
        with original_scandir(path) as entries:
            def interrupted() -> Iterator[os.DirEntry[str]]:
                for item in entries:
                    yield item
                    break
                message = "blocked pinned traversal"
                raise failure_type(message)

            yield interrupted()

    monkeypatch.setattr(provenance_module, "_NATIVE_OS_SCANDIR", fail_scandir)
    with pytest.raises(SourcePinError, match="pinned source traversal failed"):
        _ = source_snapshot_evidence(tmp_path, ("src",))


@pytest.mark.parametrize("failure_type", [PermissionError, ValueError, RuntimeError])
def test_pinned_entry_status_errors_fail_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure_type: type[Exception],
) -> None:
    """An inaccessible pinned entry cannot disappear from source evidence."""
    blocked = tmp_path / "src" / "blocked.c"
    _write(tmp_path, "src/blocked.c", b"int blocked;\n")
    original_lstat = cast(
        "Callable[[Path], os.stat_result]",
        vars(provenance_module)["_NATIVE_PATH_LSTAT"],
    )

    def fail_status(path: Path) -> object:
        if path == blocked:
            message = "blocked pinned entry"
            raise failure_type(message)
        return original_lstat(path)

    monkeypatch.setattr(provenance_module, "_NATIVE_PATH_LSTAT", fail_status)
    with pytest.raises(SourcePinError, match="pinned source status failed"):
        _ = source_snapshot_evidence(tmp_path, ("src",))


def test_pinned_entry_read_error_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An unreadable admitted source file cannot leak a host exception."""
    blocked = tmp_path / "src" / "a.c"
    _write(tmp_path, "src/a.c", b"int a;")
    original_open = os.open

    def fail_open(
        file: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        if os.fspath(file) == os.fspath(blocked):
            message = "blocked pinned source read"
            raise PermissionError(message)
        return original_open(file, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(os, "open", fail_open)
    with pytest.raises(SourcePinError, match="pinned source read failed"):
        _ = source_snapshot_evidence(tmp_path, ("src",))


def test_pinned_source_rejects_symlink_swapped_after_status(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A pre-read status cannot admit a later foreign leaf pathname."""
    root = tmp_path / "source"
    root.mkdir()
    leaf = root / "README"
    _ = leaf.write_bytes(b"same byte content")
    foreign = tmp_path / "foreign"
    _ = foreign.write_bytes(b"same byte content")
    original_status = cast(
        "Callable[[Path], os.stat_result]",
        vars(provenance_module)["_NATIVE_PATH_LSTAT"],
    )
    swapped = False

    def swap_after_status(path: Path) -> object:
        nonlocal swapped
        status = original_status(path)
        if path == leaf and not swapped:
            leaf.unlink()
            try:
                leaf.symlink_to(foreign)
            except OSError:
                pytest.skip("filesystem symlinks unavailable")
            swapped = True
        return status

    monkeypatch.setattr(provenance_module, "_NATIVE_PATH_LSTAT", swap_after_status)
    with pytest.raises(
        SourcePinError, match=r"pinned source (read failed|file changed)"
    ):
        _ = source_snapshot_evidence(root, ("README",))
    _expect(swapped, "source pin symlink substitution did not execute")


def test_missing_or_symlinked_selected_root_fails_closed(
    tmp_path: Path,
) -> None:
    """Require concrete selected roots before computing source identity."""
    _write(tmp_path, "README", b"release")
    pin = SourcePin(
        repository="https://example.invalid/source.git",
        commit=_COMMIT,
        roots=("README", "src"),
        file_count=2,
        snapshot_sha256="0" * 64,
    )

    with pytest.raises(SourcePinError, match="missing pinned source root"):
        _ = require_source_pin(tmp_path, pin)


def test_source_pin_rejects_foreign_runtime_metadata() -> None:
    """Pins admit exact strings, immutable roots, and integer file counts."""
    with pytest.raises(SourcePinError, match="non-empty string"):
        _ = SourcePin(cast("str", object()), _COMMIT, ("src",), 1, "0" * 64)
    with pytest.raises(SourcePinError, match="40 lowercase"):
        _ = SourcePin("repo", cast("str", object()), ("src",), 1, "0" * 64)
    with pytest.raises(SourcePinError, match="positive integer"):
        _ = SourcePin(
            repository="repo",
            commit=_COMMIT,
            roots=("src",),
            file_count=True,
            snapshot_sha256="0" * 64,
        )
    with pytest.raises(SourcePinError, match="immutable tuple"):
        _ = SourcePin(
            "repo",
            _COMMIT,
            cast("tuple[str, ...]", cast("object", ["src"])),
            1,
            "0" * 64,
        )
    with pytest.raises(SourcePinError, match="lowercase SHA-256"):
        _ = SourcePin("repo", _COMMIT, ("src",), 1, cast("str", object()))


@pytest.mark.parametrize(
    "roots",
    [
        ("src/../escaped",),
        (cast("str", cast("object", 11)),),
    ],
)
def test_source_pin_root_admission_ignores_late_any_override(
    monkeypatch: pytest.MonkeyPatch, roots: tuple[str, ...]
) -> None:
    """Late consumer hooks cannot admit unsafe or foreign selected roots."""
    with monkeypatch.context() as patched:
        patched.setattr(builtins, "any", lambda values: False)
        with pytest.raises(SourcePinError):
            _ = SourcePin("repo", _COMMIT, roots, 1, "0" * 64)


@pytest.mark.parametrize("record", ["commit", "snapshot"])
def test_source_pin_digest_admission_ignores_late_all_override(
    monkeypatch: pytest.MonkeyPatch, record: str
) -> None:
    """Mutable all cannot forge malformed SHA-256 or commit hex evidence."""
    with monkeypatch.context() as patched:
        patched.setattr(builtins, "all", lambda values: True)
        with pytest.raises(SourcePinError):
            if record == "commit":
                _ = SourcePin("repo", "g" * 40, ("src",), 1, "0" * 64)
            else:
                _ = SourcePinEvidence(1, "g" * 64)


@pytest.mark.parametrize("roots", [("z", "a"), ("src", "src")])
def test_source_pin_root_order_ignores_late_sorted_and_set_overrides(
    monkeypatch: pytest.MonkeyPatch, roots: tuple[str, ...]
) -> None:
    """Consumer collections cannot replace unique, sorted source labels."""

    class ForgedSet(list[str]):
        def add(self, value: str) -> None:
            self.append(value)

    rejected = False
    with monkeypatch.context() as patched:
        patched.setattr(builtins, "sorted", lambda values, *, key=None: list(values))
        patched.setattr(builtins, "set", lambda values=(): ForgedSet(values))
        try:
            _ = SourcePin("repo", _COMMIT, roots, 1, "0" * 64)
        except SourcePinError:
            rejected = True
    assert rejected, "late collection hooks admitted malformed source-pin roots"


def test_source_pin_rejects_nul_root_before_filesystem_access(
    tmp_path: Path,
) -> None:
    """Path metadata cannot defer embedded NUL failure to host path APIs."""
    nul_root = "src\x00hidden"
    with pytest.raises(SourcePinError, match="unsafe pinned source path"):
        _ = SourcePin("repo", _COMMIT, (nul_root,), 1, "0" * 64)
    with pytest.raises(SourcePinError, match="unsafe pinned source path"):
        _ = source_snapshot_evidence(tmp_path, (nul_root,))


def test_source_pin_rejects_overlapping_roots_before_tree_walk(
    tmp_path: Path,
) -> None:
    """Disjoint pin roots must be admitted without traversing duplicates."""
    roots = ("src", "src/nested")
    with pytest.raises(SourcePinError, match="must not overlap"):
        _ = SourcePin("repo", _COMMIT, roots, 1, "0" * 64)
    with pytest.raises(SourcePinError, match="must not overlap"):
        _ = source_snapshot_evidence(tmp_path, roots)


def test_snapshot_and_pin_public_inputs_fail_typed(tmp_path: Path) -> None:
    """Snapshot APIs validate roots and pins before filesystem dereference."""
    _write(tmp_path, "src/a.c", b"int a;" + bytes((10,)))
    with pytest.raises(SourcePinError, match="pathlib Path"):
        _ = source_snapshot_evidence(cast("Path", object()), ("src",))
    with pytest.raises(SourcePinError, match="immutable tuple"):
        _ = source_snapshot_evidence(
            tmp_path,
            cast("tuple[str, ...]", cast("object", ["src"])),
        )
    with pytest.raises(SourcePinError, match="unique and sorted"):
        _ = source_snapshot_evidence(tmp_path, ())
    with pytest.raises(SourcePinError, match="exact SourcePin"):
        _ = require_source_pin(tmp_path, cast("SourcePin", object()))


@pytest.mark.parametrize("mutation", ["add", "remove"])
def test_source_pin_rejects_file_set_mutation_during_snapshot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mutation: str
) -> None:
    """A matching pin cannot ignore entries changed after initial discovery."""
    _write(tmp_path, "src/a.c", b"first")
    _write(tmp_path, "src/z.c", b"last")
    roots = ("src",)
    original = source_snapshot_evidence(tmp_path, roots)
    pin = SourcePin(
        repository="repo",
        commit=_COMMIT,
        roots=roots,
        file_count=original.file_count,
        snapshot_sha256=original.snapshot_sha256,
    )
    actual_read = cast(
        "Callable[[Path, Path, str], bytes]",
        vars(provenance_module)["_read_pinned_source"],
    )
    changed = False

    def mutate_after_last_read(root: Path, path: Path, relative: str) -> bytes:
        nonlocal changed
        data = actual_read(root, path, relative)
        if relative == "src/z.c" and not changed:
            if mutation == "add":
                _write(tmp_path, "src/new.c", b"undetected extra file")
            else:
                (tmp_path / "src" / "a.c").unlink()
            changed = True
        return data

    monkeypatch.setattr(
        provenance_module, "_read_pinned_source", mutate_after_last_read
    )
    with pytest.raises(SourcePinError, match="changed during snapshot"):
        _ = require_source_pin(tmp_path, pin)
    _expect(changed, "the during-read file-set mutation did not execute")


@pytest.mark.parametrize("mutation", ["rewrite", "replace"])
def test_source_pin_rejects_file_mutation_after_earlier_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mutation: str
) -> None:
    """File identity must survive the entire snapshot, not one read."""
    original_file = tmp_path / "src" / "a.c"
    _write(tmp_path, "src/a.c", b"original")
    _write(tmp_path, "src/z.c", b"last")
    roots = ("src",)
    baseline = source_snapshot_evidence(tmp_path, roots)
    pin = SourcePin(
        "repo", _COMMIT, roots, baseline.file_count, baseline.snapshot_sha256
    )
    timestamp = original_file.stat()
    read_original = cast(
        "Callable[[Path, Path, str], bytes]",
        vars(provenance_module)["_read_pinned_source"],
    )
    changed = False

    def mutate_after_last_read(root: Path, path: Path, relative: str) -> bytes:
        nonlocal changed
        data = read_original(root, path, relative)
        if relative == "src/z.c" and not changed:
            if mutation == "rewrite":
                _ = original_file.write_bytes(b"tampered")
            else:
                replacement = tmp_path / "replacement"
                _ = replacement.write_bytes(b"original")
                _ = replacement.replace(original_file)
            os.utime(
                original_file,
                ns=(timestamp.st_atime_ns, timestamp.st_mtime_ns),
            )
            changed = True
        return data

    monkeypatch.setattr(
        provenance_module, "_read_pinned_source", mutate_after_last_read
    )
    with pytest.raises(SourcePinError, match="changed during snapshot"):
        _ = require_source_pin(tmp_path, pin)
    _expect(changed, "the during-snapshot content mutation did not execute")


def test_pinned_snapshot_ignores_late_sorted_file_drop(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Late sorting hooks cannot silently omit file identities from a pin."""
    _write(tmp_path, "src/a.c", b"one")
    _write(tmp_path, "src/b.c", b"two")
    baseline = source_snapshot_evidence(tmp_path, ("src",))
    with monkeypatch.context() as patched:
        patched.setattr(
            builtins, "sorted", lambda values, *, key=None: list(values)[:1]
        )
        observed = source_snapshot_evidence(tmp_path, ("src",))
    assert observed == baseline, "mutable sorting hook omitted source bytes"


def test_pinned_snapshot_ignores_late_zip_receipt_drop(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Late zip hooks cannot hide changes between file reads and validation."""
    _write(tmp_path, "src/a.c", b"one")
    _write(tmp_path, "src/b.c", b"two")
    baseline = source_snapshot_evidence(tmp_path, ("src",))
    pin = SourcePin(
        "repo", _COMMIT, ("src",), baseline.file_count, baseline.snapshot_sha256
    )
    read_original = cast(
        "Callable[[Path, Path, str], bytes]",
        vars(provenance_module)["_read_pinned_source"],
    )
    changed = False

    def change_after_read(root: Path, path: Path, relative: str) -> bytes:
        nonlocal changed
        data = read_original(root, path, relative)
        if relative == "src/b.c" and not changed:
            _write(tmp_path, "src/a.c", b"modified")
            changed = True
        return data

    with monkeypatch.context() as patched:
        patched.setattr(provenance_module, "_read_pinned_source", change_after_read)
        patched.setattr(builtins, "zip", lambda left, right, *, strict=True: iter(()))
        with pytest.raises(SourcePinError, match="changed during snapshot"):
            _ = require_source_pin(tmp_path, pin)
    assert changed, "the within-snapshot mutation did not execute"


class _ForeignPinRepository(str):
    """A string subclass is not admitted as pinned metadata."""


class _ForeignPinRoots(tuple[str, ...]):
    """A tuple subclass must not evade immutable-root admission."""


@pytest.mark.parametrize(
    ("foreign", "pretend", "field"),
    [
        (_ForeignPinRepository("repo"), str, "repository"),
        (True, int, "file_count"),
        (_ForeignPinRoots(("src",)), tuple, "roots"),
    ],
)
def test_source_pin_late_type_spoof_rejects_foreign_metadata(
    monkeypatch: pytest.MonkeyPatch,
    foreign: object,
    pretend: type,
    field: str,
) -> None:
    """A consumer type hook cannot authorize foreign source-pin records."""
    native_type = type
    rejected = False

    def forged_type(value: object) -> type:
        return pretend if value is foreign else native_type(value)

    with monkeypatch.context() as patch:
        patch.setattr(builtins, "type", forged_type)
        try:
            if field == "repository":
                provenance_module._validate_repository(foreign)
            elif field == "file_count":
                provenance_module._validate_file_count(foreign)
            else:
                provenance_module._validate_roots(foreign)
        except SourcePinError:
            rejected = True
    assert rejected, f"late type hook admitted foreign {field}"


def test_source_pin_late_type_spoof_rejects_path_subclass(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A forged native type cannot call foreign root string hooks."""
    foreign = _ForeignPinnedRoot(tmp_path / "foreign")
    native_type = type
    path_type = type(Path())
    rejected = False

    def forged_type(value: object) -> type:
        return path_type if value is foreign else native_type(value)

    with monkeypatch.context() as patch:
        patch.setattr(builtins, "type", forged_type)
        try:
            provenance_module._validate_root_path(foreign)
        except SourcePinError:
            rejected = True
    assert rejected, "late type hook admitted a foreign source root"


def test_source_pin_late_len_spoof_rejects_short_digest(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Digest widths cannot be forged by late length replacement."""
    malformed = "0" * 63
    native_len = len
    rejected = False

    def forged_len(value: object) -> int:
        return 64 if value is malformed else native_len(cast("Sized", value))

    with monkeypatch.context() as patch:
        patch.setattr(builtins, "len", forged_len)
        try:
            provenance_module._validate_snapshot_sha256(malformed)
        except SourcePinError:
            rejected = True
    assert rejected, "late len hook accepted a short source digest"


def test_source_pin_late_tuple_spoof_rejects_unsorted_roots(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A forged tuple constructor cannot hide unsorted root selection."""
    roots = ("zeta", "alpha")
    rejected = False
    with monkeypatch.context() as patch:
        patch.setattr(builtins, "tuple", lambda _: roots)
        try:
            provenance_module._validate_roots(roots)
        except SourcePinError:
            rejected = True
    assert rejected, "late tuple hook admitted unsorted source roots"


def test_source_pin_late_bool_spoof_rejects_drive_prefix(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A late truth hook cannot erase portable drive-prefix policy."""
    rejected = False
    with monkeypatch.context() as patch:
        patch.setattr(builtins, "bool", lambda _: False)
        try:
            provenance_module._validate_relative_path("C:/source")
        except SourcePinError:
            rejected = True
    assert rejected, "late bool hook admitted a drive-relative root"


def test_source_pin_rejects_late_string_alias_for_foreign_repository(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An imported consumer cannot authorize subclassed repository names."""
    validate_repository = cast(
        "Callable[[object], None]",
        vars(provenance_module)["_validate_repository"],
    )
    rejected = False
    with monkeypatch.context() as patch:
        patch.setattr(builtins, "str", _ForeignPinRepository)
        try:
            validate_repository(_ForeignPinRepository("repo"))
        except SourcePinError as error:
            rejected = _REPOSITORY_ERROR in error.args[0]
    assert rejected, "foreign repository passed late string type alias"


def test_source_pin_rejects_late_integer_alias_for_boolean_file_count(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A Boolean count cannot become native provenance evidence."""
    rejected = False
    with monkeypatch.context() as patch:
        patch.setattr(builtins, "int", bool)
        try:
            _ = SourcePinEvidence(file_count=True, snapshot_sha256="0" * 64)
        except SourcePinError:
            rejected = True
    assert rejected, "Boolean file count passed late integer alias"


def test_source_pin_rejects_late_tuple_alias_for_mutable_roots(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A mutable selected-root list cannot masquerade as tuple evidence."""
    validate_roots = cast(
        "Callable[[object], None]",
        vars(provenance_module)["_validate_roots"],
    )
    rejected = False
    with monkeypatch.context() as patch:
        patch.setattr(builtins, "tuple", list)
        try:
            validate_roots(["src"])
        except SourcePinError as error:
            rejected = _ROOTS_ERROR in error.args[0]
    assert rejected, "mutable selected roots passed late tuple alias"


def test_source_pin_rejects_late_string_alias_for_foreign_digest(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A subclassed digest must never qualify as an exact source pin."""
    rejected = False
    with monkeypatch.context() as patch:
        patch.setattr(builtins, "str", _ForeignPinRepository)
        try:
            _ = SourcePinEvidence(1, _ForeignPinRepository("0" * 64))
        except SourcePinError:
            rejected = True
    assert rejected, "foreign snapshot digest passed late string alias"


def test_source_pin_native_evidence_survives_late_builtin_type_aliases(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Genuine strings, numeric counts and tuple roots remain accepted."""
    with monkeypatch.context() as patch:
        patch.setattr(builtins, "str", _ForeignPinRepository)
        valid = SourcePinEvidence(1, "0" * 64)
        repository_validation = cast(
            "Callable[[object], None]",
            vars(provenance_module)["_validate_repository"],
        )
        repository_validation("repo")
    assert valid.snapshot_sha256 == "0" * 64

    with monkeypatch.context() as patch:
        patch.setattr(builtins, "int", bool)
        native = SourcePinEvidence(1, "0" * 64)
    assert native.file_count == 1

    with monkeypatch.context() as patch:
        patch.setattr(builtins, "tuple", list)
        pin = SourcePin("repo", _COMMIT, ("src",), 1, "0" * 64)
    assert pin.roots == ("src",)


def test_source_pin_host_error_detail_survives_late_string_alias(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Native exception evidence is not hidden by a late string alias."""
    detail = cast(
        "Callable[[BaseException], str]",
        vars(provenance_module)["_host_error_detail"],
    )
    error = ExactTreeError("native pinned file read failed")
    with monkeypatch.context() as patch:
        patch.setattr(builtins, "str", bytes)
        actual = detail(error)
    assert actual == error.args[0]


def test_source_pin_rejects_late_string_alias_for_foreign_root_entry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A subclassed selected root never qualifies as exact path text."""
    validate_roots = cast(
        "Callable[[object], None]",
        vars(provenance_module)["_validate_roots"],
    )
    rejected = False
    with monkeypatch.context() as patch:
        patch.setattr(builtins, "str", _ForeignPinRepository)
        try:
            validate_roots((_ForeignPinRepository("src"),))
        except SourcePinError as error:
            rejected = _ROOT_ENTRY_ERROR in error.args[0]
    assert rejected, "foreign root path passed late string alias"
