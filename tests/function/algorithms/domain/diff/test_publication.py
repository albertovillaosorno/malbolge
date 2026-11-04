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
#   - Tests for atomic no-replace directory publication.
# - Must-Not:
#   - Bypass the contracts or authority boundaries of its owning package.
# - Allows:
#   - Inputs: synthetic local filesystem fixtures.
#   - Outputs: deterministic assertions about publication routing and
#     collisions.
#   - Side effects: temporary test filesystem state only.
# - Split-When:
#   - Split when one responsibility gains an independent lifecycle.
# - Merge-When:
#   - Merge when another file owns the exact same responsibility.
# - Summary:
#   - Synthetic validation for no-replace directory publication.
# - Description:
#   - Exercises routing, collision preservation, and unsupported-host failure.
# - Usage:
#   - Used by the source-bound diff test suite.
# - Defaults:
#   - Publication collisions fail closed.
#

"""Synthetic validation for no-replace directory publication."""

from __future__ import annotations

import builtins
import ctypes
import errno
import os
import platform
import stat
import subprocess as sp  # ruff: ignore[suspicious-subprocess-import]
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Protocol, cast, override
from unittest.mock import Mock

import pytest
from algorithms.diff import publication

_WINDOWS_OS_NAME = "nt"
_LINUX_PLATFORM = "linux"
_OURS = b"ours"
_FOREIGN = b"foreign"


def _simulate_host(
    monkeypatch: pytest.MonkeyPatch, *, os_name: str, platform: str
) -> None:
    """Inject an internal test host without changing public runtime policy."""
    monkeypatch.setattr(publication, "_HOST_OS_NAME", os_name)
    monkeypatch.setattr(publication, "_HOST_PLATFORM", platform)


class _NativeRenameSignature(Protocol):
    """Inspectable Linux renameat2 call signature in a fake native loader."""

    argtypes: tuple[object, ...]
    restype: object


class _ForeignPath(type(Path())):
    """A path subclass cannot supply independent filesystem evidence."""

    @override
    def __fspath__(self) -> str:
        message = "foreign filesystem path conversion was evaluated"
        raise AssertionError(message)


@pytest.mark.parametrize("foreign_staging", [False, True])
def test_publication_rejects_foreign_path_subclasses_before_host_calls(
    tmp_path: Path, *, foreign_staging: bool
) -> None:
    """An untrusted Path override must not reach a filesystem or C ABI call."""
    staging = tmp_path / "staging"
    destination = tmp_path / "destination"
    staging.mkdir()
    original = staging if foreign_staging else destination
    foreign = _ForeignPath(original)
    candidate_staging = foreign if foreign_staging else staging
    candidate_destination = destination if foreign_staging else foreign
    with pytest.raises(OSError, match="pathlib Path") as invalid:
        publication.publish_directory_no_replace(
            candidate_staging, candidate_destination
        )
    assert invalid.value.errno == errno.EINVAL
    assert staging.is_dir()
    assert not destination.exists()


@pytest.mark.parametrize("foreign_staging", [False, True])
def test_publication_rejects_late_type_spoof_of_foreign_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, foreign_staging: bool
) -> None:
    """Replacing builtins.type cannot admit a custom Path before publishing."""
    staging = tmp_path / "staging"
    destination = tmp_path / "destination"
    staging.mkdir()
    foreign = _ForeignPath(staging if foreign_staging else destination)
    candidate_staging = foreign if foreign_staging else staging
    candidate_destination = destination if foreign_staging else foreign
    native_type = type
    native_path_type = type(Path())
    calls = 0

    def spoof_type(value: object) -> type[object]:
        nonlocal calls
        if value is foreign:
            calls += 1
            return native_path_type
        return native_type(value)

    rejected = False
    with monkeypatch.context() as patched:
        patched.setattr(builtins, "type", spoof_type)
        try:
            publication.publish_directory_no_replace(
                candidate_staging, candidate_destination
            )
        except OSError as error:
            rejected = error.errno == errno.EINVAL
    assert rejected, "late type hook admitted a foreign publication path"
    assert calls == 0, "mutable type hook was consulted for source admission"
    assert staging.is_dir() and not destination.exists()


@pytest.mark.skipif(
    os.name != _WINDOWS_OS_NAME and sys.platform != _LINUX_PLATFORM,
    reason="requires supported native directory publication",
)
def test_publication_ignores_late_path_equality_override(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A consumer cannot make distinct native roots appear identical."""
    staging = tmp_path / "staging"
    destination = tmp_path / "destination"
    staging.mkdir()
    _ = (staging / "payload").write_bytes(_OURS)
    calls = 0

    def forged_path_equality(_left: Path, _right: object) -> bool:
        nonlocal calls
        calls += 1
        return True

    with monkeypatch.context() as patched:
        patched.setattr(Path, "__eq__", forged_path_equality)
        publication.publish_directory_no_replace(staging, destination)

    assert calls == 0, "publication consulted mutable Path equality"
    assert not staging.exists()
    assert (destination / "payload").read_bytes() == _OURS


def test_publication_ignores_false_path_equality_for_aliased_roots(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A late false equality hook cannot authorize the same root twice."""
    staging = tmp_path / "staging"
    status_calls = 0
    equality_calls = 0

    def forged_path_equality(_left: Path, _right: object) -> bool:
        nonlocal equality_calls
        equality_calls += 1
        return False

    def observe_lstat(_path: Path) -> os.stat_result:
        nonlocal status_calls
        status_calls += 1
        raise AssertionError("aliased roots reached filesystem status")

    rejected = False
    with monkeypatch.context() as patched:
        patched.setattr(Path, "__eq__", forged_path_equality)
        patched.setattr(publication, "_NATIVE_PATH_LSTAT", observe_lstat)
        try:
            publication.publish_directory_no_replace(staging, staging)
        except OSError as error:
            rejected = error.errno == errno.EINVAL
    assert rejected, "late equality hook admitted identical roots"
    assert equality_calls == 0
    assert status_calls == 0


@pytest.mark.parametrize("nul_staging", [False, True])
def test_publication_rejects_late_str_spoof_of_nul_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, nul_staging: bool
) -> None:
    """NUL-bearing roots must reject before any filesystem status is read."""
    staging = tmp_path / ("staging\x00extra" if nul_staging else "staging")
    destination = tmp_path / ("output" if nul_staging else "output\x00extra")
    original_str = str
    calls = 0

    def spoof_str(value: object) -> str:
        if value is staging or value is destination:
            return ""
        return original_str(value)

    def fail_lstat(value: Path) -> os.stat_result:
        nonlocal calls
        calls += 1
        raise AssertionError("late str bypass reached filesystem status")

    rejected = False
    with monkeypatch.context() as patched:
        patched.setattr(publication, "_NATIVE_PATH_LSTAT", fail_lstat)
        patched.setattr(builtins, "str", spoof_str)
        try:
            publication.publish_directory_no_replace(staging, destination)
        except OSError as error:
            rejected = (
                error.errno == errno.EINVAL
                and error.strerror
                == "directory publication paths must not contain NUL bytes"
            )
    assert rejected, "late str hook bypassed NUL path preflight"
    assert calls == 0, "filesystem status reached before preflight"


def test_publication_rejects_late_type_spoof_of_stat_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A foreign filesystem status cannot become a trusted inode receipt."""
    status = SimpleNamespace(st_mode=stat.S_IFDIR | 0o755, st_dev=1, st_ino=1)
    native_type = type
    calls = 0

    def spoof_type(value: object) -> type[object]:
        nonlocal calls
        if value is status:
            calls += 1
            return os.stat_result
        return native_type(value)

    rejected = False
    with monkeypatch.context() as patched:
        patched.setattr(publication, "_NATIVE_PATH_LSTAT", lambda path: status)
        patched.setattr(builtins, "type", spoof_type)
        try:
            _ = publication._require_staging_directory(tmp_path / "staging")
        except OSError as error:
            rejected = error.errno == errno.EINVAL
    assert rejected, "late type hook admitted a foreign inode receipt"
    assert calls == 0, "mutable type hook was consulted for receipt admission"


def test_publication_rejects_native_status_spoofed_after_import(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A mutable host status hook cannot publish a regular file as a tree."""
    if os.name == _WINDOWS_OS_NAME or sys.platform != _LINUX_PLATFORM:
        pytest.skip("requires native Linux directory publication")
    staging = tmp_path / "staging"
    destination = tmp_path / "destination"
    _ = staging.write_bytes(_OURS)
    native_lstat = Path.lstat
    status_calls = 0

    def forged_lstat(path: Path) -> os.stat_result:
        nonlocal status_calls
        actual = native_lstat(path)
        if path in {staging, destination}:
            status_calls += 1
            values = list(actual)
            values[stat.ST_MODE] = stat.S_IFDIR | 0o755
            return os.stat_result(values)
        return actual

    with monkeypatch.context() as patched:
        patched.setattr(Path, "lstat", forged_lstat)
        with pytest.raises(OSError, match="staging must be"):
            publication.publish_directory_no_replace(staging, destination)
    assert status_calls == 0
    assert staging.read_bytes() == _OURS
    assert not destination.exists()


@pytest.mark.skipif(
    os.name == _WINDOWS_OS_NAME or sys.platform != _LINUX_PLATFORM,
    reason="requires native Linux directory publication",
)
def test_publication_ignores_post_import_directory_classifier(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A mutated status classifier cannot authorize publication of a file."""
    staging = tmp_path / "staging"
    destination = tmp_path / "destination"
    _ = staging.write_bytes(_OURS)
    calls = 0

    def forged_is_dir(mode: int) -> bool:
        nonlocal calls
        _ = mode
        calls += 1
        return True

    with monkeypatch.context() as patched:
        patched.setattr(stat, "S_ISDIR", forged_is_dir)
        with pytest.raises(OSError, match="staging must be") as rejected:
            publication.publish_directory_no_replace(staging, destination)
    assert rejected.value.errno == errno.ENOTDIR
    assert calls == 0
    assert staging.read_bytes() == _OURS
    assert not destination.exists()


@pytest.mark.skipif(
    os.name == _WINDOWS_OS_NAME or sys.platform != _LINUX_PLATFORM,
    reason="requires native Linux directory publication",
)
def test_publication_ignores_post_import_native_os_lstat_hook(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Pinned Path.lstat must not delegate to a mutated os.lstat hook."""
    staging = tmp_path / "staging"
    destination = tmp_path / "destination"
    _ = staging.write_bytes(_OURS)
    native_lstat = os.lstat
    calls = 0

    def forged_lstat(path: str | bytes | os.PathLike[str]) -> os.stat_result:
        nonlocal calls
        receipt = native_lstat(path)
        if Path(os.fsdecode(path)) in {staging, destination}:
            calls += 1
            fields = list(receipt)
            fields[stat.ST_MODE] = stat.S_IFDIR | 0o755
            return os.stat_result(fields)
        return receipt

    with monkeypatch.context() as patched:
        patched.setattr(os, "lstat", forged_lstat)
        with pytest.raises(OSError, match="staging must be"):
            publication.publish_directory_no_replace(staging, destination)
    assert calls == 0
    assert staging.read_bytes() == _OURS
    assert not destination.exists()


def test_publication_rejects_foreign_or_aliased_inputs() -> None:
    """Validate path and host metadata before any platform rename primitive."""
    staging = Path("staging")
    destination = Path("destination")
    with pytest.raises(OSError, match="pathlib Path") as foreign_path:
        publication.publish_directory_no_replace(
            cast("Path", cast("object", "staging")),
            destination,
        )
    assert foreign_path.value.errno == errno.EINVAL

    boolean_host: object = True
    with pytest.raises(OSError, match="host selectors") as foreign_host:
        publication.publish_directory_no_replace(
            staging,
            destination,
            os_name=cast("str", cast("object", boolean_host)),
        )
    assert foreign_host.value.errno == errno.EINVAL

    with pytest.raises(OSError, match="must differ") as aliased:
        publication.publish_directory_no_replace(staging, staging)
    assert aliased.value.errno == errno.EINVAL


@pytest.mark.parametrize(
    "paths",
    [
        (Path("staging\x00suffix"), Path("destination")),
        (Path("staging"), Path("destination\x00suffix")),
    ],
)
@pytest.mark.parametrize(
    "host",
    [("posix", _LINUX_PLATFORM), (_WINDOWS_OS_NAME, "win32")],
)
def test_nul_paths_fail_before_any_rename(
    monkeypatch: pytest.MonkeyPatch,
    *,
    paths: tuple[Path, Path],
    host: tuple[str, str],
) -> None:
    """A C ABI must not truncate embedded NUL pathnames before publication."""
    staging, destination = paths
    os_name, platform = host
    calls: list[tuple[Path, Path]] = []

    def record_rename(source: Path, target: Path) -> Path:
        calls.append((source, target))
        return target

    monkeypatch.setattr(publication, "_NATIVE_PATH_RENAME", record_rename)
    monkeypatch.setattr(publication, "_linux_rename_noreplace", record_rename)
    with pytest.raises(OSError, match="NUL") as invalid:
        publication.publish_directory_no_replace(
            staging, destination, os_name=os_name, platform=platform
        )
    assert invalid.value.errno == errno.EINVAL
    assert not calls


@pytest.mark.parametrize("bad_staging", [True, False])
@pytest.mark.parametrize(
    "host", [("posix", _LINUX_PLATFORM), (_WINDOWS_OS_NAME, "win32")]
)
def test_unencodable_paths_fail_before_any_rename(
    monkeypatch: pytest.MonkeyPatch,
    *,
    bad_staging: bool,
    host: tuple[str, str],
) -> None:
    """Reject paths the host cannot encode before invoking rename."""
    malformed = "invalid" + chr(0xD800)
    host_encodable = True
    try:
        _ = os.fsencode(malformed)
    except UnicodeError:
        host_encodable = False
    if host_encodable:
        pytest.skip("host filesystem codec accepts the test surrogate")

    staging = Path(malformed) if bad_staging else Path("staging")
    destination = Path("destination") if bad_staging else Path(malformed)
    calls: list[tuple[Path, Path]] = []

    def record_rename(source: Path, target: Path) -> Path:
        calls.append((source, target))
        return target

    monkeypatch.setattr(publication, "_NATIVE_PATH_RENAME", record_rename)
    monkeypatch.setattr(publication, "_linux_rename_noreplace", record_rename)
    os_name, platform = host
    with pytest.raises(OSError, match="filesystem-encodable") as invalid:
        publication.publish_directory_no_replace(
            staging, destination, os_name=os_name, platform=platform
        )
    assert invalid.value.errno == errno.EINVAL
    assert not calls


def test_windows_route_uses_path_rename(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Route Windows publication through the host no-overwrite rename API."""
    staging = tmp_path / "staging"
    staging.mkdir()
    destination = tmp_path / "destination"
    calls: list[tuple[Path, Path]] = []
    native_rename = Path.rename

    def record_rename(path: Path, target: Path) -> Path:
        calls.append((path, target))
        return native_rename(path, target)

    monkeypatch.setattr(publication, "_NATIVE_PATH_RENAME", record_rename)
    monkeypatch.setattr(
        publication,
        "os",
        SimpleNamespace(name=_WINDOWS_OS_NAME, fsencode=os.fsencode),
    )
    monkeypatch.setattr(publication, "sys", SimpleNamespace(platform="win32"))
    _simulate_host(monkeypatch, os_name="nt", platform="win32")
    publication.publish_directory_no_replace(
        staging, destination, os_name=_WINDOWS_OS_NAME, platform="win32"
    )
    assert calls == [(staging, destination)]


def test_windows_publication_ignores_post_import_rename_redirection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A hostile host hook cannot redirect Windows publication."""
    staging = tmp_path / "staging"
    destination = tmp_path / "destination"
    redirected = tmp_path / "redirected"
    staging.mkdir()
    _ = (staging / "payload").write_bytes(_OURS)
    native_rename = Path.rename
    calls = 0

    def forged_rename(path: Path, _target: Path) -> Path:
        nonlocal calls
        _ = _target
        calls += 1
        return native_rename(path, redirected)

    with monkeypatch.context() as patched:
        patched.setattr(Path, "rename", forged_rename)
        patched.setattr(
            publication, "os", SimpleNamespace(name="nt", fsencode=os.fsencode)
        )
        patched.setattr(publication, "sys", SimpleNamespace(platform="win32"))
        patched.setattr(publication, "_HOST_OS_NAME", "nt")
        patched.setattr(publication, "_HOST_PLATFORM", "win32")
        publication.publish_directory_no_replace(
            staging, destination, os_name="nt", platform="win32"
        )
    assert calls == 0
    assert not staging.exists()
    assert (destination / "payload").read_bytes() == _OURS
    assert not redirected.exists()


def test_windows_publication_ignores_post_import_native_os_rename_hook(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Pinned Path.rename must not delegate to a mutated os.rename hook."""
    staging = tmp_path / "staging"
    destination = tmp_path / "destination"
    redirected = tmp_path / "redirected"
    staging.mkdir()
    _ = (staging / "payload").write_bytes(_OURS)
    native_rename = os.rename
    calls = 0

    def forged_rename(source: Path | str, target: Path | str) -> None:
        nonlocal calls
        _ = target
        calls += 1
        native_rename(source, redirected)

    with monkeypatch.context() as patched:
        patched.setattr(os, "rename", forged_rename)
        patched.setattr(publication, "_HOST_OS_NAME", "nt")
        patched.setattr(publication, "_HOST_PLATFORM", "win32")
        publication.publish_directory_no_replace(
            staging, destination, os_name="nt", platform="win32"
        )
    assert calls == 0
    assert not staging.exists()
    assert (destination / "payload").read_bytes() == _OURS
    assert not redirected.exists()


@pytest.mark.parametrize("failure_type", [TypeError, ValueError, RuntimeError])
def test_windows_publication_wraps_unexpected_rename_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure_type: type[Exception],
) -> None:
    """An unexpected host rename failure remains an OSError with a typed cause."""
    staging = tmp_path / "staging"
    destination = tmp_path / "destination"
    staging.mkdir()

    def fail_rename(_source: Path, _target: Path) -> Path:
        message = "unusable host rename"
        raise failure_type(message)

    monkeypatch.setattr(publication, "_NATIVE_PATH_RENAME", fail_rename)
    monkeypatch.setattr(
        publication,
        "os",
        SimpleNamespace(name="nt", fsencode=os.fsencode),
    )
    monkeypatch.setattr(publication, "sys", SimpleNamespace(platform="win32"))
    _simulate_host(monkeypatch, os_name="nt", platform="win32")
    with pytest.raises(OSError, match="Windows directory rename failed") as caught:
        publication.publish_directory_no_replace(
            staging, destination, os_name="nt", platform="win32"
        )
    assert caught.value.errno == errno.EIO
    assert type(caught.value.__cause__) is failure_type
    assert staging.is_dir()
    assert not destination.exists()


def test_windows_publication_preserves_native_collision_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An ordinary host OSError keeps the original collision diagnostics."""
    staging = tmp_path / "staging"
    destination = tmp_path / "destination"
    staging.mkdir()
    native_failure = FileExistsError(errno.EEXIST, "target occupied")

    def fail_rename(_source: Path, _target: Path) -> Path:
        raise native_failure

    monkeypatch.setattr(publication, "_NATIVE_PATH_RENAME", fail_rename)
    monkeypatch.setattr(
        publication,
        "os",
        SimpleNamespace(name="nt", fsencode=os.fsencode),
    )
    monkeypatch.setattr(publication, "sys", SimpleNamespace(platform="win32"))
    _simulate_host(monkeypatch, os_name="nt", platform="win32")
    with pytest.raises(FileExistsError) as caught:
        publication.publish_directory_no_replace(
            staging, destination, os_name="nt", platform="win32"
        )
    assert caught.value is native_failure
    assert staging.is_dir()
    assert not destination.exists()


def test_linux_route_uses_renameat2(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Route Linux publication through renameat2 with no-replace semantics."""
    staging = tmp_path / "staging"
    staging.mkdir()
    destination = tmp_path / "destination"
    calls: list[tuple[Path, Path]] = []

    def record_rename(source: Path, target: Path) -> None:
        calls.append((source, target))
        os.rename(source, target)

    monkeypatch.setattr(publication, "_linux_rename_noreplace", record_rename)
    monkeypatch.setattr(
        publication,
        "os",
        SimpleNamespace(name="posix", fsencode=os.fsencode),
    )
    monkeypatch.setattr(publication, "sys", SimpleNamespace(platform=_LINUX_PLATFORM))
    publication.publish_directory_no_replace(
        staging, destination, os_name="posix", platform=_LINUX_PLATFORM
    )
    assert calls == [(staging, destination)]


@pytest.mark.skipif(
    os.name == _WINDOWS_OS_NAME or sys.platform != _LINUX_PLATFORM,
    reason="requires native Linux renameat2",
)
@pytest.mark.parametrize("hook", ["fsencode", "fspath"])
def test_linux_publication_ignores_mutated_path_encoder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, hook: str
) -> None:
    """A domain may not redirect the C-ABI target through os path hooks."""
    staging = tmp_path / "staging"
    destination = tmp_path / "destination"
    redirected = tmp_path / "redirected"
    staging.mkdir()
    _ = (staging / "payload").write_bytes(_OURS)
    native_encode = os.fsencode
    native_fspath = os.fspath
    calls = 0

    def forged_fsencode(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
    ) -> bytes:
        nonlocal calls
        if path == destination:
            calls += 1
            return native_encode(redirected)
        return native_encode(path)

    def forged_fspath(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
    ) -> str | bytes:
        nonlocal calls
        if path == destination:
            calls += 1
            return str(redirected)
        return native_fspath(path)

    with monkeypatch.context() as patched:
        if hook == "fsencode":
            patched.setattr(os, "fsencode", forged_fsencode)
        else:
            patched.setattr(os, "fspath", forged_fspath)
        publication.publish_directory_no_replace(staging, destination)
    assert calls == 0
    assert not staging.exists()
    assert (destination / "payload").read_bytes() == _OURS
    assert not redirected.exists()


def test_unsupported_host_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Do not emulate atomic no-replace semantics on an unsupported host."""
    staging = tmp_path / "staging"
    staging.mkdir()
    monkeypatch.setattr(
        publication, "os", SimpleNamespace(name="posix", fsencode=os.fsencode)
    )
    monkeypatch.setattr(publication, "sys", SimpleNamespace(platform="unsupported"))
    _simulate_host(monkeypatch, os_name="posix", platform="unsupported")
    with pytest.raises(OSError, match="unsupported") as caught:
        publication.publish_directory_no_replace(
            staging,
            tmp_path / "destination",
            os_name="posix",
            platform="unsupported",
        )
    assert caught.value.errno == errno.ENOTSUP


@pytest.mark.skipif(
    os.name == _WINDOWS_OS_NAME or sys.platform != _LINUX_PLATFORM,
    reason="POSIX rename may replace an existing empty directory",
)
def test_publication_cannot_force_unsafe_foreign_host_rename(
    tmp_path: Path,
) -> None:
    """A caller cannot override the host and replace an existing directory."""
    staging = tmp_path / "staging"
    destination = tmp_path / "destination"
    staging.mkdir()
    destination.mkdir()
    _ = (staging / "ours.txt").write_bytes(_OURS)

    with pytest.raises(OSError, match="host selectors") as rejected:
        publication.publish_directory_no_replace(
            staging,
            destination,
            os_name=_WINDOWS_OS_NAME,
            platform="win32",
        )
    assert rejected.value.errno == errno.EINVAL
    assert (staging / "ours.txt").read_bytes() == _OURS
    assert destination.is_dir()
    assert not (destination / "ours.txt").exists()


@pytest.mark.skipif(
    os.name == _WINDOWS_OS_NAME or sys.platform != _LINUX_PLATFORM,
    reason="requires POSIX overwrite behavior when the host is forged",
)
def test_publication_rejects_post_import_host_selector_spoof(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A fake Windows host cannot bypass Linux no-replace publication."""
    staging = tmp_path / "staging"
    destination = tmp_path / "destination"
    staging.mkdir()
    destination.mkdir()
    _ = (staging / "payload").write_bytes(_OURS)

    with monkeypatch.context() as patched:
        patched.setattr(
            publication, "os", SimpleNamespace(name="nt", fsencode=os.fsencode)
        )
        patched.setattr(publication, "sys", SimpleNamespace(platform="win32"))
        with pytest.raises(OSError, match="host selectors") as rejected:
            publication.publish_directory_no_replace(
                staging, destination, os_name="nt", platform="win32"
            )
    assert rejected.value.errno == errno.EINVAL
    assert (staging / "payload").read_bytes() == _OURS
    assert destination.is_dir()
    assert not (destination / "payload").exists()


def test_host_collision_preserves_both_directories(tmp_path: Path) -> None:
    """A destination race cannot replace or delete either writer's payload."""
    if os.name != _WINDOWS_OS_NAME and sys.platform != _LINUX_PLATFORM:
        pytest.skip("host has no supported no-replace directory primitive")
    staging = tmp_path / "staging"
    destination = tmp_path / "destination"
    staging.mkdir()
    destination.mkdir()
    _ = (staging / "ours.txt").write_bytes(_OURS)
    _ = (destination / "foreign.txt").write_bytes(_FOREIGN)

    with pytest.raises(OSError, match=r"already exists|Cannot create|File exists"):
        publication.publish_directory_no_replace(staging, destination)

    assert (staging / "ours.txt").read_bytes() == _OURS
    assert (destination / "foreign.txt").read_bytes() == _FOREIGN


@pytest.mark.parametrize("staging_is_file", [True, False])
def test_publication_rejects_non_directory_staging(
    tmp_path: Path, *, staging_is_file: bool
) -> None:
    """Never publish a regular file or a symlink as a staged directory."""
    if os.name != _WINDOWS_OS_NAME and sys.platform != _LINUX_PLATFORM:
        pytest.skip("host has no supported no-replace directory primitive")
    staging = tmp_path / "staging"
    destination = tmp_path / "destination"
    if staging_is_file:
        _ = staging.write_bytes(_OURS)
    else:
        directory = tmp_path / "actual-directory"
        directory.mkdir()
        try:
            staging.symlink_to(directory, target_is_directory=True)
        except OSError as error:
            pytest.skip(f"symlink creation unavailable: {error}")

    with pytest.raises(OSError, match=r"staging.*directory") as rejected:
        publication.publish_directory_no_replace(staging, destination)
    assert rejected.value.errno == errno.ENOTDIR
    if staging_is_file:
        assert staging.read_bytes() == _OURS
    else:
        assert staging.is_symlink()
    assert not destination.exists()


@pytest.mark.parametrize("failure_type", [TypeError, ValueError, RuntimeError])
def test_staging_status_errors_fail_closed_as_os_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure_type: type[Exception],
) -> None:
    """Unexpected staging status failures cannot reach a rename primitive."""
    staging = tmp_path / "staging"
    staging.mkdir()
    destination = tmp_path / "destination"
    original_lstat = Path.lstat
    rename_calls: list[tuple[Path, Path]] = []

    def fail_staging_stat(path: Path) -> os.stat_result:
        if path == staging:
            message = "blocked directory status"
            raise failure_type(message)
        return original_lstat(path)

    def record_rename(source: Path, target: Path) -> None:
        rename_calls.append((source, target))

    monkeypatch.setattr(publication, "_NATIVE_PATH_LSTAT", fail_staging_stat)
    monkeypatch.setattr(publication, "_linux_rename_noreplace", record_rename)
    with pytest.raises(OSError, match="staging directory status failed") as rejected:
        publication.publish_directory_no_replace(staging, destination)
    assert rejected.value.errno == errno.EINVAL
    assert not rename_calls
    assert not destination.exists()


def test_publication_rejects_foreign_staging_stat_before_rename(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Forged staging metadata cannot turn a file into a publishable tree."""
    if sys.platform != _LINUX_PLATFORM:
        pytest.skip("Linux no-replace publisher required")
    staging = tmp_path / "staging"
    destination = tmp_path / "destination"
    _ = staging.write_bytes(_OURS)
    original_lstat = Path.lstat
    actual = original_lstat(staging)
    foreign = SimpleNamespace(
        st_mode=stat.S_IFDIR | 0o755,
        st_dev=actual.st_dev,
        st_ino=actual.st_ino,
    )
    calls: list[tuple[Path, Path]] = []

    def forged_staging_stat(path: Path) -> os.stat_result:
        if path == staging:
            return cast("os.stat_result", cast("object", foreign))
        return original_lstat(path)

    def record_rename(source: Path, target: Path) -> None:
        calls.append((source, target))

    monkeypatch.setattr(publication, "_NATIVE_PATH_LSTAT", forged_staging_stat)
    monkeypatch.setattr(publication, "_linux_rename_noreplace", record_rename)
    with pytest.raises(OSError, match="native filesystem status") as rejected:
        publication.publish_directory_no_replace(staging, destination)
    assert rejected.value.errno == errno.EINVAL
    assert not calls
    assert original_lstat(staging).st_ino == actual.st_ino
    assert not destination.exists()


def test_publication_rejects_foreign_destination_attestation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A forged post-rename inode receipt cannot certify publication."""
    if sys.platform != _LINUX_PLATFORM:
        pytest.skip("Linux no-replace publisher required")
    staging = tmp_path / "staging"
    destination = tmp_path / "destination"
    staging.mkdir()
    _ = (staging / "payload").write_bytes(_OURS)
    original_lstat = Path.lstat

    def forged_destination_stat(path: Path) -> os.stat_result:
        native = original_lstat(path)
        if path == destination:
            return cast(
                "os.stat_result",
                cast(
                    "object",
                    SimpleNamespace(
                        st_mode=native.st_mode,
                        st_dev=native.st_dev,
                        st_ino=native.st_ino,
                    ),
                ),
            )
        return native

    monkeypatch.setattr(
        publication,
        "_NATIVE_PATH_LSTAT",
        forged_destination_stat,
    )
    with pytest.raises(OSError, match=r"publication.*not completed") as rejected:
        publication.publish_directory_no_replace(staging, destination)
    assert rejected.value.errno == errno.EIO
    assert not staging.exists()
    assert (destination / "payload").read_bytes() == _OURS


def _fake_linux_host(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        publication, "os", SimpleNamespace(name="posix", fsencode=os.fsencode)
    )
    monkeypatch.setattr(publication, "sys", SimpleNamespace(platform="linux"))


@pytest.mark.skipif(
    os.name == _WINDOWS_OS_NAME or sys.platform != _LINUX_PLATFORM,
    reason="requires native Linux renameat2",
)
def test_linux_publication_ignores_post_import_loader_overwrite_shim(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A replaced global C loader cannot bypass no-replace directory publication."""
    staging = tmp_path / "staging"
    destination = tmp_path / "destination"
    staging.mkdir()
    destination.mkdir()
    _ = (staging / "new").write_bytes(_OURS)
    calls = 0

    def wrong_rename(*args: int | bytes) -> int:
        nonlocal calls
        calls += 1
        source, target = args[1], args[3]
        assert type(source) is bytes and type(target) is bytes
        os.rename(os.fsdecode(source), os.fsdecode(target))
        return 0

    def fake_cdll(_name: object, **_options: bool) -> SimpleNamespace:
        del _name, _options
        return SimpleNamespace(renameat2=Mock(side_effect=wrong_rename))

    with monkeypatch.context() as patched:
        patched.setattr(ctypes, "CDLL", fake_cdll)
        with pytest.raises(FileExistsError):
            publication.publish_directory_no_replace(staging, destination)
    assert calls == 0, "late C loader replaced an existing output directory"
    assert (staging / "new").read_bytes() == _OURS
    assert list(destination.iterdir()) == []


@pytest.mark.parametrize("alias", ["c_int", "c_char_p", "c_uint"])
def test_linux_publication_ignores_post_import_ctypes_abi_aliases(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, alias: str
) -> None:
    """Consumer hooks cannot change the native renameat2 argument ABI."""
    staging = tmp_path / "staging"
    destination = tmp_path / "destination"
    staging.mkdir()
    native = Mock(return_value=-1)
    expected = (
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_uint,
    )

    def fake_cdll(_name: object, **_options: bool) -> SimpleNamespace:
        _ = (_name, _options)
        return SimpleNamespace(renameat2=native)

    monkeypatch.setattr(publication, "_NATIVE_CDLL", fake_cdll)
    _fake_linux_host(monkeypatch)
    _ = ctypes.set_errno(errno.EEXIST)
    try:
        with monkeypatch.context() as patched:
            patched.setattr(ctypes, alias, object())
            with pytest.raises(FileExistsError):
                publication.publish_directory_no_replace(staging, destination)
    finally:
        _ = ctypes.set_errno(0)
    native_abi = cast("_NativeRenameSignature", native)
    assert native_abi.argtypes == expected
    assert native_abi.restype is expected[0]
    assert native.call_count == 1
    assert staging.is_dir() and not destination.exists()


@pytest.mark.parametrize("status", [False, None, "no rename"])
def test_linux_publication_rejects_foreign_native_status(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, status: object
) -> None:
    """A native ABI mismatch must not be treated as a successful rename."""
    staging = tmp_path / "staging"
    destination = tmp_path / "destination"
    staging.mkdir()
    native = Mock(return_value=status)

    def fake_cdll(_name: object, **_options: bool) -> SimpleNamespace:
        _ = (_name, _options)
        return SimpleNamespace(renameat2=native)

    monkeypatch.setattr(publication, "_NATIVE_CDLL", fake_cdll)
    _fake_linux_host(monkeypatch)
    with pytest.raises(OSError, match="invalid status") as rejected:
        publication.publish_directory_no_replace(staging, destination)
    assert rejected.value.errno == errno.EINVAL
    assert native.call_count == 1
    assert staging.is_dir()
    assert not destination.exists()


@pytest.mark.skipif(
    os.name == _WINDOWS_OS_NAME or sys.platform != _LINUX_PLATFORM,
    reason="requires native Linux renameat2 error boundary",
)
@pytest.mark.parametrize("hook", ["get_errno", "strerror"])
def test_linux_publication_ignores_mutated_error_hooks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, hook: str
) -> None:
    """Native rename failure reporting must not execute foreign OS hooks."""
    staging = tmp_path / "staging"
    destination = tmp_path / "destination"
    staging.mkdir()
    native = Mock(return_value=-1)

    def fake_cdll(_name: object, **_options: bool) -> SimpleNamespace:
        _ = (_name, _options)
        return SimpleNamespace(renameat2=native)

    def forged_errno() -> int:
        message = "foreign errno hook executed"
        raise AssertionError(message)

    def forged_strerror(number: int) -> str:
        _ = number
        message = "foreign strerror hook executed"
        raise AssertionError(message)

    expected = errno.EIO if hook == "get_errno" else errno.EEXIST
    _ = ctypes.set_errno(0 if hook == "get_errno" else errno.EEXIST)
    try:
        with monkeypatch.context() as patched:
            patched.setattr(publication, "_NATIVE_CDLL", fake_cdll)
            if hook == "get_errno":
                patched.setattr(ctypes, "get_errno", forged_errno)
            else:
                patched.setattr(os, "strerror", forged_strerror)
            with pytest.raises(OSError) as caught:
                publication.publish_directory_no_replace(staging, destination)
    finally:
        _ = ctypes.set_errno(0)
    assert caught.value.errno == expected
    assert native.call_count == 1
    assert staging.is_dir()
    assert not destination.exists()


@pytest.mark.skipif(
    os.name == _WINDOWS_OS_NAME or sys.platform != _LINUX_PLATFORM,
    reason="requires native Linux renameat2 error boundary",
)
@pytest.mark.parametrize("reported_errno", [0, -1, 4096])
def test_linux_publication_rejects_invalid_native_errno(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, reported_errno: int
) -> None:
    """A failed native call must report a valid Linux errno or fail closed."""
    staging = tmp_path / "staging"
    destination = tmp_path / "destination"
    staging.mkdir()
    native = Mock(return_value=-1)

    def fake_cdll(_name: object, **_options: bool) -> SimpleNamespace:
        _ = (_name, _options)
        return SimpleNamespace(renameat2=native)

    _ = ctypes.set_errno(reported_errno)
    try:
        with monkeypatch.context() as patched:
            patched.setattr(publication, "_NATIVE_CDLL", fake_cdll)
            with pytest.raises(
                OSError, match="invalid errno status"
            ) as rejected:
                publication.publish_directory_no_replace(staging, destination)
    finally:
        _ = ctypes.set_errno(0)
    assert rejected.value.errno == errno.EIO
    assert native.call_count == 1
    assert staging.is_dir()
    assert not destination.exists()


@pytest.mark.parametrize(
    "failure_type", [ValueError, RuntimeError, ctypes.ArgumentError]
)
def test_linux_publication_contains_native_loader_errors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure_type: type[Exception],
) -> None:
    """A broken native loader is an unavailable no-replace primitive."""
    staging = tmp_path / "staging"
    destination = tmp_path / "destination"
    staging.mkdir()

    def fail_cdll(_name: object, **_options: bool) -> object:
        _ = (_name, _options)
        message = "broken native loader"
        raise failure_type(message)

    monkeypatch.setattr(publication, "_NATIVE_CDLL", fail_cdll)
    _fake_linux_host(monkeypatch)
    with pytest.raises(OSError, match="unavailable") as rejected:
        publication.publish_directory_no_replace(staging, destination)
    assert rejected.value.errno == errno.ENOTSUP
    assert staging.is_dir()
    assert not destination.exists()


@pytest.mark.parametrize(
    "failure_type", [ValueError, RuntimeError, TypeError, ctypes.ArgumentError]
)
def test_linux_publication_contains_native_call_errors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure_type: type[Exception],
) -> None:
    """Native invocation exceptions must not escape as host language errors."""
    staging = tmp_path / "staging"
    destination = tmp_path / "destination"
    staging.mkdir()

    def fail_call(*_args: object) -> int:
        _ = _args
        message = "broken native call"
        raise failure_type(message)

    native = Mock(side_effect=fail_call)

    def fake_cdll(_name: object, **_options: bool) -> SimpleNamespace:
        _ = (_name, _options)
        return SimpleNamespace(renameat2=native)

    monkeypatch.setattr(publication, "_NATIVE_CDLL", fake_cdll)
    _fake_linux_host(monkeypatch)
    with pytest.raises(OSError, match="invocation failed") as rejected:
        publication.publish_directory_no_replace(staging, destination)
    assert rejected.value.errno == errno.EINVAL
    assert native.call_count == 1
    assert staging.is_dir()
    assert not destination.exists()


def test_linux_publication_pins_ctypes_argument_error_after_import(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A consumer cannot hide a native argument failure by swapping its alias."""
    staging = tmp_path / "staging"
    destination = tmp_path / "destination"
    staging.mkdir()
    original_argument_error = ctypes.ArgumentError
    native = Mock(side_effect=original_argument_error("invalid native arguments"))

    def fake_cdll(_name: object, **_options: bool) -> SimpleNamespace:
        _ = (_name, _options)
        return SimpleNamespace(renameat2=native)

    monkeypatch.setattr(publication, "_NATIVE_CDLL", fake_cdll)
    _fake_linux_host(monkeypatch)
    with monkeypatch.context() as patched:
        patched.setattr(ctypes, "ArgumentError", LookupError)
        with pytest.raises(OSError, match="invocation failed") as rejected:
            publication.publish_directory_no_replace(staging, destination)
    assert rejected.value.errno == errno.EINVAL
    assert native.call_count == 1
    assert staging.is_dir()
    assert not destination.exists()


@pytest.mark.parametrize("platform", ["linux", "windows"])
def test_publication_rejects_foreign_success_without_rename(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, platform: str
) -> None:
    """A successful-looking host receipt cannot publish an absent output."""
    staging = tmp_path / "staging"
    destination = tmp_path / "destination"
    staging.mkdir()
    _ = (staging / "payload").write_bytes(_OURS)
    if platform == "linux":
        native = Mock(return_value=0)

        def fake_cdll(_name: object, **_options: bool) -> SimpleNamespace:
            _ = (_name, _options)
            return SimpleNamespace(renameat2=native)

        monkeypatch.setattr(publication, "_NATIVE_CDLL", fake_cdll)
        _fake_linux_host(monkeypatch)
        os_name, host_platform = "posix", "linux"
    else:

        def pretend_rename(_source: Path, _target: Path) -> Path:
            return destination

        monkeypatch.setattr(publication, "_NATIVE_PATH_RENAME", pretend_rename)
        monkeypatch.setattr(
            publication,
            "os",
            SimpleNamespace(name="nt", fsencode=os.fsencode),
        )
        monkeypatch.setattr(publication, "sys", SimpleNamespace(platform="win32"))
        _simulate_host(monkeypatch, os_name="nt", platform="win32")
        os_name, host_platform = "nt", "win32"

    with pytest.raises(OSError, match="publication.*not completed"):
        publication.publish_directory_no_replace(
            staging, destination, os_name=os_name, platform=host_platform
        )
    assert (staging / "payload").read_bytes() == _OURS
    assert not destination.exists()


@pytest.mark.parametrize("attack", ["wrong-source", "replaced-source"])
def test_linux_publication_rejects_success_for_different_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, attack: str
) -> None:
    """Publication must bind output inode to the staged directory identity."""
    staging = tmp_path / "staging"
    destination = tmp_path / "destination"
    foreign = tmp_path / "foreign"
    parked = tmp_path / "parked"
    staging.mkdir()
    foreign.mkdir()
    _ = (staging / "payload").write_bytes(_OURS)
    _ = (foreign / "payload").write_bytes(_FOREIGN)

    def foreign_rename(*_args: object) -> int:
        if attack == "replaced-source":
            os.rename(staging, parked)
            os.rename(foreign, staging)
            os.rename(staging, destination)
        else:
            os.rename(foreign, destination)
        return 0

    def fake_cdll(_name: object, **_options: bool) -> SimpleNamespace:
        _ = (_name, _options)
        return SimpleNamespace(renameat2=Mock(side_effect=foreign_rename))

    monkeypatch.setattr(publication, "_NATIVE_CDLL", fake_cdll)
    _fake_linux_host(monkeypatch)
    with pytest.raises(OSError, match="publication.*not completed"):
        publication.publish_directory_no_replace(
            staging, destination, os_name="posix", platform="linux"
        )
    assert (destination / "payload").read_bytes() == _FOREIGN
    if attack == "replaced-source":
        assert (parked / "payload").read_bytes() == _OURS
    else:
        assert (staging / "payload").read_bytes() == _OURS


def test_real_host_publication_attests_moved_directory(tmp_path: Path) -> None:
    """The native no-replace path still publishes a real stage exactly once."""
    if platform.system() not in {"Linux", "Windows"}:
        pytest.skip("no supported atomic directory publisher")
    staging = tmp_path / "staging"
    destination = tmp_path / "destination"
    staging.mkdir()
    _ = (staging / "payload").write_bytes(_OURS)
    publication.publish_directory_no_replace(staging, destination)
    assert not staging.exists()
    assert (destination / "payload").read_bytes() == _OURS


@pytest.mark.skipif(
    os.name != _WINDOWS_OS_NAME and sys.platform != _LINUX_PLATFORM,
    reason="requires supported native directory publication",
)
@pytest.mark.parametrize("cached_destination", [False, True])
def test_publication_rejects_late_path_attribute_redirection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, cached_destination: bool
) -> None:
    """A late Path getter cannot redirect the destination through __str__."""
    staging = tmp_path / "staging"
    destination = tmp_path / "destination"
    redirected = tmp_path / "redirected"
    staging.mkdir()
    _ = (staging / "payload").write_bytes(_OURS)
    if cached_destination:
        _ = str(destination)
    original = Path.__getattribute__
    spoofed = str(redirected)
    calls = 0

    def forged_getattribute(path: Path, name: str) -> object:
        nonlocal calls
        if path is destination and name == "_str":
            calls += 1
            return spoofed
        return original(path, name)

    with monkeypatch.context() as patched:
        patched.setattr(Path, "__getattribute__", forged_getattribute)
        with pytest.raises(OSError, match="path.*hook") as rejected:
            publication.publish_directory_no_replace(staging, destination)
    assert rejected.value.errno == errno.EINVAL
    assert calls == 0
    assert (staging / "payload").read_bytes() == _OURS
    assert not destination.exists() and not redirected.exists()


@pytest.mark.skipif(
    os.name != _WINDOWS_OS_NAME and sys.platform != _LINUX_PLATFORM,
    reason="requires supported native directory publication",
)
def test_publication_rejects_late_native_path_cache_descriptor_swap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Replacing a PurePath storage descriptor cannot spoof a target path."""
    from pathlib import PurePath

    staging = tmp_path / "staging"
    destination = tmp_path / "destination"
    redirected = tmp_path / "redirected"
    staging.mkdir()
    _ = (staging / "payload").write_bytes(_OURS)
    _ = str(destination)
    spoofed = str(redirected)
    original_slot = PurePath.__dict__["_str"]
    calls = 0

    def forged_cached_path(path: PurePath) -> str:
        nonlocal calls
        if path is destination:
            calls += 1
            return spoofed
        return cast("str", original_slot.__get__(path, PurePath))

    with monkeypatch.context() as patched:
        patched.setattr(PurePath, "_str", property(forged_cached_path))
        with pytest.raises(OSError, match="path.*hook") as rejected:
            publication.publish_directory_no_replace(staging, destination)
    assert rejected.value.errno == errno.EINVAL
    assert calls == 0
    assert (staging / "payload").read_bytes() == _OURS
    assert not destination.exists() and not redirected.exists()


@pytest.mark.skipif(
    os.name == _WINDOWS_OS_NAME or sys.platform != _LINUX_PLATFORM,
    reason="requires native POSIX path parsing",
)
def test_publication_ignores_late_raw_path_fspath_redirection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Fresh multi-part paths cannot let late os.fspath select another target."""
    staging = tmp_path / "staging"
    destination = Path(str(tmp_path), "destination")
    redirected = tmp_path / "redirected"
    staging.mkdir()
    _ = (staging / "payload").write_bytes(_OURS)
    native_fspath = os.fspath
    calls = 0

    def forged_fspath(
        value: str | bytes | os.PathLike[str] | os.PathLike[bytes],
    ) -> str | bytes:
        nonlocal calls
        if value == "destination":
            calls += 1
            return "redirected"
        return native_fspath(value)

    with monkeypatch.context() as patched:
        patched.setattr(os, "fspath", forged_fspath)
        publication.publish_directory_no_replace(staging, destination)
    assert calls == 0
    assert not staging.exists()
    assert (destination / "payload").read_bytes() == _OURS
    assert not redirected.exists()


@pytest.mark.skipif(
    os.name == _WINDOWS_OS_NAME,
    reason="native Windows path conversion does not inspect raw part lists",
)
@pytest.mark.parametrize("foreign_list", [tuple, dict])
def test_native_publication_path_parts_ignore_late_builtin_list_alias(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, foreign_list: type[object]
) -> None:
    """The native path parser must not trust a consumer's list type alias."""
    path = tmp_path / "source"
    expected = publication._native_path_string(path)
    with monkeypatch.context() as patched:
        patched.setattr(builtins, "list", foreign_list)
        actual = publication._native_path_string(path)
    assert actual == expected


@pytest.mark.skipif(
    os.name == _WINDOWS_OS_NAME or sys.platform != _LINUX_PLATFORM,
    reason="requires Linux native no-replace publication",
)
def test_linux_publication_ignores_late_builtin_list_alias(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A changed list builtin must not veto valid native directory paths."""
    staging = tmp_path / "staging"
    destination = tmp_path / "destination"
    staging.mkdir()
    _ = (staging / "payload").write_bytes(_OURS)
    with monkeypatch.context() as patched:
        patched.setattr(builtins, "list", tuple)
        publication.publish_directory_no_replace(staging, destination)
    assert not staging.exists()
    assert (destination / "payload").read_bytes() == _OURS


@pytest.mark.skipif(
    os.name == _WINDOWS_OS_NAME or sys.platform != _LINUX_PLATFORM,
    reason="requires native POSIX path parsing",
)
@pytest.mark.parametrize(
    "segments",
    [
        ("",),
        (".",),
        ("a", ".", "b"),
        ("a/./b",),
        ("a", "..", "b"),
        ("a", "/b"),
        ("a", "//b"),
        ("///a", "b"),
        ("//a", "b"),
        ("a", "", "b"),
        ("a//b/",),
        ("/",),
        ("//",),
        ("///",),
    ],
)
def test_native_posix_publication_spelling_preserves_pathlib_lexical_rules(
    segments: tuple[str, ...],
) -> None:
    """Slot-based publication spelling must match the native POSIX Path ABI."""
    path = Path(*segments)
    expected = str(path)
    assert publication._native_path_string(path) == expected


@pytest.mark.skipif(
    os.name == _WINDOWS_OS_NAME or sys.platform != _LINUX_PLATFORM,
    reason="requires native POSIX platform path hierarchy",
)
@pytest.mark.parametrize("class_index", [0, 2])
def test_publication_rejects_platform_specific_path_getter_overrides(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, class_index: int
) -> None:
    """Native PosixPath and PurePosixPath hooks cannot bypass path admission."""
    staging = tmp_path / "staging"
    destination = tmp_path / "destination"
    redirected = tmp_path / "redirected"
    staging.mkdir()
    _ = (staging / "payload").write_bytes(_OURS)
    path_class = type(destination).__mro__[class_index]
    original = Path.__getattribute__
    wrong = str(redirected)
    calls = 0

    def forged_getattribute(path: Path, name: str) -> object:
        nonlocal calls
        if path is destination and name == "_str":
            calls += 1
            return wrong
        return original(path, name)

    with monkeypatch.context() as patched:
        patched.setattr(path_class, "__getattribute__", forged_getattribute)
        with pytest.raises(OSError, match="path.*hook") as rejected:
            publication.publish_directory_no_replace(staging, destination)
    assert rejected.value.errno == errno.EINVAL
    assert calls == 0
    assert (staging / "payload").read_bytes() == _OURS
    assert not destination.exists() and not redirected.exists()


@pytest.mark.skipif(
    os.name == _WINDOWS_OS_NAME or sys.platform != _LINUX_PLATFORM,
    reason="requires native Linux no-replace directory semantics",
)
@pytest.mark.parametrize("hook", ["__getattr__", "__getitem__", "renameat2"])
def test_linux_publication_rejects_late_cdll_class_symbol_redirect(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, hook: str
) -> None:
    """A mutated CDLL class cannot downgrade renameat2 to overwriting rename."""
    staging = tmp_path / "staging"
    destination = tmp_path / "destination"
    staging.mkdir()
    destination.mkdir()
    _ = (staging / "payload").write_bytes(_OURS)
    calls = 0

    def unsafe_rename(*_args: object) -> int:
        nonlocal calls
        calls += 1
        os.rename(staging, destination)
        return 0

    false_symbol = Mock(side_effect=unsafe_rename)

    def forged_getattr(_library: ctypes.CDLL, name: str) -> object:
        assert name == "renameat2"
        return false_symbol

    def forged_getitem(_library: ctypes.CDLL, name: str) -> object:
        assert name == "renameat2"
        return false_symbol

    replacement = (
        forged_getattr
        if hook == "__getattr__"
        else forged_getitem
        if hook == "__getitem__"
        else false_symbol
    )
    with monkeypatch.context() as patched:
        patched.setattr(ctypes.CDLL, hook, replacement, raising=False)
        with pytest.raises(OSError, match="unavailable") as rejected:
            publication.publish_directory_no_replace(staging, destination)
    assert rejected.value.errno == errno.ENOTSUP
    assert calls == 0, "late CDLL class symbol replaced an existing destination"
    assert (staging / "payload").read_bytes() == _OURS
    assert list(destination.iterdir()) == []


@pytest.mark.skipif(
    os.name == _WINDOWS_OS_NAME or sys.platform != _LINUX_PLATFORM,
    reason="requires native Linux renameat2",
)
@pytest.mark.parametrize(
    "hook",
    [
        "__init__",
        "__getattribute__",
        "__setattr__",
        "_load_library",
        "_FuncPtr",
        "_func_flags_",
        "_func_restype_",
    ],
)
def test_linux_publication_rejects_late_cdll_class_dispatch_mutation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, hook: str
) -> None:
    """Constructor, loader, and function-pointer class hooks are immutable ABI."""
    staging = tmp_path / "staging"
    destination = tmp_path / "destination"
    staging.mkdir()
    replacement = Mock(side_effect=AssertionError("foreign CDLL hook executed"))
    with monkeypatch.context() as patched:
        patched.setattr(ctypes.CDLL, hook, replacement)
        with pytest.raises(OSError, match="unavailable") as rejected:
            publication.publish_directory_no_replace(staging, destination)
    assert rejected.value.errno == errno.ENOTSUP
    assert replacement.call_count == 0
    assert staging.is_dir() and not destination.exists()


@pytest.mark.skipif(
    os.name == _WINDOWS_OS_NAME or sys.platform != _LINUX_PLATFORM,
    reason="requires native Linux renameat2",
)
def test_linux_publication_rejects_late_cdll_allocator_overwrite(
    tmp_path: Path,
) -> None:
    """A forged CDLL allocator cannot downgrade no-replace to os.rename."""
    staging = tmp_path / "staging"
    destination = tmp_path / "destination"
    staging.mkdir()
    destination.mkdir()
    _ = (staging / "payload").write_bytes(_OURS)
    # Altering a native Python type's __new__ slot can poison its allocator
    # even after removing the patch. Keep this adversarial test in a child.
    attack = """
import ctypes
import errno
import os
import sys
from pathlib import Path
from algorithms.diff import publication
staging, destination = (Path(part) for part in sys.argv[1:])
calls = []
class UnsafeRename:
    argtypes = ()
    restype = None
    def __call__(self, *_args):
        calls.append("rename")
        os.rename(staging, destination)
        return 0
class ForeignLibrary:
    renameat2 = UnsafeRename()
def forged_new(_cls, *_args, **_kwargs):
    calls.append("allocator")
    return ForeignLibrary()
ctypes.CDLL.__new__ = forged_new
try:
    publication.publish_directory_no_replace(staging, destination)
except OSError as error:
    assert error.errno == errno.ENOTSUP, error
else:
    raise AssertionError("forged native loader bypassed no-replace")
assert calls == [], calls
"""
    environment = os.environ.copy()
    library_root = str(Path(publication.__file__).resolve().parents[2])
    environment["PYTHONPATH"] = (
        library_root + os.pathsep + environment.get("PYTHONPATH", "")
    )
    completed = sp.run(  # ruff: ignore[subprocess-without-shell-equals-true]
        [sys.executable, "-c", attack, str(staging), str(destination)],
        check=False,
        shell=False,
        env=environment,
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert completed.returncode == 0, completed.stderr
    assert (staging / "payload").read_bytes() == _OURS
    assert list(destination.iterdir()) == []


@pytest.mark.skipif(
    os.name == _WINDOWS_OS_NAME or sys.platform != _LINUX_PLATFORM,
    reason="requires native Linux renameat2",
)
def test_linux_publication_rejects_late_ctypes_dlopen_mutation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The CDLL constructor cannot delegate to a replaced module loader."""
    staging = tmp_path / "staging"
    destination = tmp_path / "destination"
    staging.mkdir()
    replacement = Mock(side_effect=AssertionError("foreign dlopen executed"))
    with monkeypatch.context() as patched:
        patched.setattr(ctypes, "_dlopen", replacement)
        with pytest.raises(OSError, match="unavailable") as rejected:
            publication.publish_directory_no_replace(staging, destination)
    assert rejected.value.errno == errno.ENOTSUP
    assert replacement.call_count == 0
    assert staging.is_dir() and not destination.exists()


@pytest.mark.skipif(
    os.name == _WINDOWS_OS_NAME or sys.platform != _LINUX_PLATFORM,
    reason="requires native Linux no-replace directory semantics",
)
def test_linux_publication_rejects_late_ctypes_function_pointer_type(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """CDLL cannot derive its rename function from a replaced base pointer type."""
    staging = tmp_path / "staging"
    destination = tmp_path / "destination"
    staging.mkdir()
    destination.mkdir()
    _ = (staging / "payload").write_bytes(_OURS)
    calls = 0

    class ForeignFunctionPointer:
        def __init__(self, _symbol: object) -> None:
            pass

        def __call__(self, *_args: object) -> int:
            nonlocal calls
            calls += 1
            os.rename(staging, destination)
            return 0

    with monkeypatch.context() as patched:
        patched.setattr(ctypes, "_CFuncPtr", ForeignFunctionPointer)
        with pytest.raises(OSError, match="unavailable") as rejected:
            publication.publish_directory_no_replace(staging, destination)
    assert rejected.value.errno == errno.ENOTSUP
    assert calls == 0, "foreign function pointer replaced an occupied target"
    assert (staging / "payload").read_bytes() == _OURS
    assert list(destination.iterdir()) == []


@pytest.mark.skipif(
    os.name == _WINDOWS_OS_NAME or sys.platform != _LINUX_PLATFORM,
    reason="requires native Linux renameat2",
)
@pytest.mark.parametrize("flag", ["_FUNCFLAG_USE_ERRNO", "_FUNCFLAG_USE_LASTERROR"])
def test_linux_publication_rejects_late_ctypes_function_pointer_flags(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, flag: str
) -> None:
    """A foreign ctypes ABI flag cannot change the loaded function signature."""
    staging = tmp_path / "staging"
    destination = tmp_path / "destination"
    staging.mkdir()
    with monkeypatch.context() as patched:
        patched.setattr(ctypes, flag, object())
        with pytest.raises(OSError, match="unavailable") as rejected:
            publication.publish_directory_no_replace(staging, destination)
    assert rejected.value.errno == errno.ENOTSUP
    assert staging.is_dir() and not destination.exists()


@pytest.mark.skipif(
    os.name == _WINDOWS_OS_NAME or sys.platform != _LINUX_PLATFORM,
    reason="requires native Linux no-replace directory semantics",
)
def test_linux_publication_rejects_cdll_redirect_after_late_any_swap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Changing builtins.any cannot silence the native CDLL integrity gate."""
    staging = tmp_path / "staging"
    destination = tmp_path / "destination"
    staging.mkdir()
    destination.mkdir()
    _ = (staging / "payload").write_bytes(_OURS)
    fake_rename = Mock(return_value=0)
    caught: OSError | None = None

    with monkeypatch.context() as patched:
        patched.setattr(ctypes.CDLL, "renameat2", fake_rename, raising=False)
        patched.setattr(builtins, "any", lambda _items: False)
        try:
            publication.publish_directory_no_replace(staging, destination)
        except OSError as error:
            caught = error

    assert caught is not None and caught.errno == errno.ENOTSUP
    assert fake_rename.call_count == 0, "forged renameat2 symbol reached dispatch"
    assert (staging / "payload").read_bytes() == _OURS
    assert list(destination.iterdir()) == []


@pytest.mark.parametrize("false_or_true", [False, True])
def test_publication_path_guard_ignores_late_any_override(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    false_or_true: bool,
) -> None:
    """Path evidence does not trust a consumer-installed builtin aggregate."""
    from pathlib import PurePath

    path = tmp_path / "target"
    native_path_string = publication._native_path_string  # pyright: ignore[reportPrivateUsage]
    original = cast("property", PurePath.__dict__["_tail"])
    original_text = native_path_string(path)
    with monkeypatch.context() as patched:
        patched.setattr(builtins, "any", lambda _items: false_or_true)
        if not false_or_true:
            patched.setattr(PurePath, "_tail", property(lambda value: original.__get__(value, PurePath)))
        if false_or_true:
            assert native_path_string(path) == original_text
        else:
            with pytest.raises(OSError, match="path hooks changed"):
                _ = native_path_string(path)


@pytest.mark.skipif(
    os.name == _WINDOWS_OS_NAME or sys.platform != _LINUX_PLATFORM,
    reason="requires native Linux no-replace directory semantics",
)
def test_linux_publication_rejects_loader_override_after_late_any_swap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Changing the aggregate builtin cannot hide ctypes ABI substitution."""
    destination = tmp_path / "destination"
    calls = 0

    def foreign_loader(*_args: object, **_kwargs: object) -> object:
        nonlocal calls
        calls += 1
        return object()

    caught: OSError | None = None
    with monkeypatch.context() as patched:
        patched.setattr(ctypes, "_dlopen", foreign_loader)
        patched.setattr(builtins, "any", lambda _items: False)
        try:
            publication._require_native_cdll_dispatch(destination)  # pyright: ignore[reportPrivateUsage]
        except OSError as error:
            caught = error

    assert caught is not None and caught.errno == errno.ENOTSUP
    assert calls == 0, "replaced ctypes loader was consulted"


@pytest.mark.skipif(
    os.name == _WINDOWS_OS_NAME or sys.platform != _LINUX_PLATFORM,
    reason="requires native Linux no-replace directory semantics",
)
@pytest.mark.parametrize("alias", ["setattr", "isinstance", "int", "__build_class__"])
def test_linux_publication_rejects_late_cdll_builtin_dispatch_alias(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, alias: str
) -> None:
    """Late builtin aliases cannot execute while resolving renameat2."""
    staging = tmp_path / "staging"
    destination = tmp_path / "destination"
    staging.mkdir()
    destination.mkdir()
    (staging / "payload").write_bytes(_OURS)
    calls = 0
    original = builtins.__dict__[alias]

    def foreign_builtin(*_args: object, **_kwargs: object) -> object:
        nonlocal calls
        calls += 1
        raise AssertionError("foreign builtin reached native symbol lookup")

    class ForeignIntMeta(type):
        def __instancecheck__(cls, _value: object) -> bool:
            nonlocal calls
            calls += 1
            raise AssertionError("foreign integer class checked a native symbol")

    class ForeignInt(metaclass=ForeignIntMeta):
        pass

    replacement: object = ForeignInt if alias == "int" else foreign_builtin
    caught: OSError | None = None
    with monkeypatch.context() as patched:
        patched.setattr(builtins, alias, replacement)
        try:
            publication.publish_directory_no_replace(staging, destination)
        except OSError as error:
            caught = error
        finally:
            # Restore the interpreter builtin before pytest handles assertions.
            builtins.__dict__[alias] = original

    assert caught is not None and caught.errno == errno.ENOTSUP
    assert calls == 0, "publication reached substituted builtin dispatch"
    assert (staging / "payload").read_bytes() == _OURS
    assert list(destination.iterdir()) == []


@pytest.mark.skipif(
    sys.platform != _LINUX_PLATFORM,
    reason="requires Linux no-replace publication",
)
def test_publication_attestation_rejects_late_missing_file_alias(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A changed missing-file class cannot certify an unmoved directory."""
    staging = tmp_path / "staging"
    destination = tmp_path / "destination"
    staging.mkdir()
    stat_result = os.lstat(staging)
    denied = PermissionError(errno.EACCES, "status denied")
    receipt = Mock(side_effect=[stat_result, stat_result, denied])
    native_missing = builtins.FileNotFoundError
    caught: OSError | None = None
    with monkeypatch.context() as patched:
        patched.setattr(publication, "_NATIVE_PATH_LSTAT", receipt)
        patched.setattr(publication, "_linux_rename_noreplace", Mock())
        patched.setattr(builtins, "FileNotFoundError", PermissionError)
        try:
            publication.publish_directory_no_replace(staging, destination)
        except OSError as error:
            caught = error
        finally:
            builtins.__dict__["FileNotFoundError"] = native_missing
    assert type(caught) is OSError
    assert caught.errno == errno.EIO
    assert caught.__cause__ is denied
    assert staging.is_dir()
    assert not destination.exists()


@pytest.mark.skipif(
    sys.platform != _LINUX_PLATFORM,
    reason="requires Linux no-replace publication",
)
@pytest.mark.parametrize("stage", [False, True])
def test_publication_attestation_wraps_denial_after_oserror_swap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, stage: bool
) -> None:
    """Both post-rename status reads report EIO with the original cause."""
    staging = tmp_path / "staging"
    destination = tmp_path / "destination"
    staging.mkdir()
    stat_result = os.lstat(staging)
    failure = PermissionError(errno.EACCES, "status denied")
    receipt = Mock(
        side_effect=(
            [stat_result, stat_result, failure]
            if stage
            else [stat_result, failure]
        )
    )
    native_oserror = builtins.OSError
    caught: OSError | None = None
    with monkeypatch.context() as patched:
        patched.setattr(publication, "_NATIVE_PATH_LSTAT", receipt)
        patched.setattr(publication, "_linux_rename_noreplace", Mock())
        patched.setattr(builtins, "OSError", LookupError)
        try:
            publication.publish_directory_no_replace(staging, destination)
        except native_oserror as error:
            caught = error
        finally:
            builtins.__dict__["OSError"] = native_oserror
    assert type(caught) is native_oserror
    assert caught.errno == errno.EIO
    assert caught.__cause__ is failure
    assert staging.is_dir()
    assert not destination.exists()


def test_publication_staging_status_wraps_late_typeerror_alias(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Host status TypeError must remain a typed publication error."""
    staging = tmp_path / "staging"
    staging.mkdir()
    failure = TypeError("status reader failed")
    native_typeerror = builtins.TypeError
    caught: OSError | None = None
    with monkeypatch.context() as patched:
        patched.setattr(
            publication, "_NATIVE_PATH_LSTAT", Mock(side_effect=failure)
        )
        patched.setattr(builtins, "TypeError", LookupError)
        try:
            publication.publish_directory_no_replace(
                staging, tmp_path / "destination"
            )
        except OSError as error:
            caught = error
        finally:
            builtins.__dict__["TypeError"] = native_typeerror
    assert type(caught) is OSError
    assert caught.errno == errno.EINVAL
    assert caught.__cause__ is failure


@pytest.mark.skipif(
    sys.platform != _LINUX_PLATFORM,
    reason="requires Linux native loader route",
)
def test_publication_linux_loader_wraps_late_valueerror_alias(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Late error aliases cannot leak a native loader exception."""
    staging = tmp_path / "staging"
    staging.mkdir()
    failure = ValueError("native loader failed")
    native_valueerror = builtins.ValueError
    caught: OSError | None = None
    with monkeypatch.context() as patched:
        patched.setattr(publication, "_NATIVE_CDLL", Mock(side_effect=failure))
        patched.setattr(builtins, "ValueError", LookupError)
        try:
            publication.publish_directory_no_replace(
                staging, tmp_path / "destination"
            )
        except OSError as error:
            caught = error
        finally:
            builtins.__dict__["ValueError"] = native_valueerror
    assert type(caught) is OSError
    assert caught.errno == errno.ENOTSUP
    assert caught.__cause__ is failure


@pytest.mark.skipif(
    os.name == _WINDOWS_OS_NAME, reason="requires POSIX surrogate encoding"
)
def test_publication_unicode_error_wraps_late_unicodeerror_alias(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unencodable paths must report native EINVAL after alias replacement."""
    native_unicodeerror = builtins.UnicodeError
    caught: OSError | None = None
    with monkeypatch.context() as patched:
        patched.setattr(builtins, "UnicodeError", LookupError)
        try:
            publication.publish_directory_no_replace(
                Path("\ud800"), Path("output")
            )
        except OSError as error:
            caught = error
        finally:
            builtins.__dict__["UnicodeError"] = native_unicodeerror
    assert type(caught) is OSError
    assert caught.errno == errno.EINVAL
    assert type(caught.__cause__) is UnicodeEncodeError


def test_publication_rejection_uses_native_oserror_after_alias_swap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Malformed path admission must not raise a substituted error class."""
    native_oserror = builtins.OSError
    caught: OSError | None = None
    with monkeypatch.context() as patched:
        patched.setattr(builtins, "OSError", LookupError)
        try:
            publication.publish_directory_no_replace(
                cast("Path", cast("object", "not a path")), Path("output")
            )
        except native_oserror as error:
            caught = error
        finally:
            builtins.__dict__["OSError"] = native_oserror
    assert type(caught) is native_oserror
    assert caught.errno == errno.EINVAL


@pytest.mark.skipif(
    os.name == _WINDOWS_OS_NAME or sys.platform != _LINUX_PLATFORM,
    reason="requires native Linux no-replace directory semantics",
)
@pytest.mark.parametrize("alias", ["_os", "_sys"])
def test_linux_publication_rejects_late_ctypes_host_module_alias(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, alias: str
) -> None:
    """A substituted ctypes host module cannot run before no-replace rename."""
    staging = tmp_path / "staging"
    destination = tmp_path / "destination"
    staging.mkdir()
    destination.mkdir()
    (staging / "payload").write_bytes(_OURS)
    calls = 0

    class ForeignPlatform:
        def startswith(self, _prefix: str) -> bool:
            nonlocal calls
            calls += 1
            os.rename(staging, destination)
            return False

    forged_module = (
        SimpleNamespace(platform=ForeignPlatform())
        if alias == "_sys"
        else SimpleNamespace()
    )
    caught: OSError | None = None
    with monkeypatch.context() as patched:
        patched.setattr(ctypes, alias, forged_module)
        try:
            publication.publish_directory_no_replace(staging, destination)
        except OSError as error:
            caught = error

    assert caught is not None and caught.errno == errno.ENOTSUP
    assert calls == 0, "foreign ctypes host module executed before no-replace"
    assert (staging / "payload").read_bytes() == _OURS
    assert list(destination.iterdir()) == []


@pytest.mark.skipif(
    os.name == _WINDOWS_OS_NAME or sys.platform != _LINUX_PLATFORM,
    reason="requires native Linux no-replace directory semantics",
)
def test_linux_publication_rejects_mutated_host_platform_before_ctypes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A changed sys.platform cannot execute hooks inside the native loader."""
    staging = tmp_path / "staging"
    destination = tmp_path / "destination"
    staging.mkdir()
    destination.mkdir()
    (staging / "payload").write_bytes(_OURS)
    calls = 0

    class ForeignPlatform:
        def startswith(self, _prefix: str) -> bool:
            nonlocal calls
            calls += 1
            os.rename(staging, destination)
            return False

    caught: OSError | None = None
    with monkeypatch.context() as patched:
        patched.setattr(sys, "platform", ForeignPlatform())
        try:
            publication.publish_directory_no_replace(staging, destination)
        except OSError as error:
            caught = error

    assert caught is not None and caught.errno == errno.ENOTSUP
    assert calls == 0, "mutated host platform executed inside ctypes loader"
    assert (staging / "payload").read_bytes() == _OURS
    assert list(destination.iterdir()) == []
