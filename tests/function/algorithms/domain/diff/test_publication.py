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

import ctypes
import errno
import os
import platform
import stat
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import cast, override
from unittest.mock import Mock

import pytest
from algorithms.diff import publication

_WINDOWS_OS_NAME = "nt"
_LINUX_PLATFORM = "linux"
_OURS = b"ours"
_FOREIGN = b"foreign"


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

    monkeypatch.setattr(Path, "rename", record_rename)
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

    monkeypatch.setattr(Path, "rename", record_rename)
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

    monkeypatch.setattr(Path, "rename", record_rename)
    monkeypatch.setattr(
        publication,
        "os",
        SimpleNamespace(name=_WINDOWS_OS_NAME, fsencode=os.fsencode),
    )
    monkeypatch.setattr(publication, "sys", SimpleNamespace(platform="win32"))
    publication.publish_directory_no_replace(
        staging, destination, os_name=_WINDOWS_OS_NAME, platform="win32"
    )
    assert calls == [(staging, destination)]


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

    monkeypatch.setattr(Path, "rename", fail_rename)
    monkeypatch.setattr(
        publication,
        "os",
        SimpleNamespace(name="nt", fsencode=os.fsencode),
    )
    monkeypatch.setattr(publication, "sys", SimpleNamespace(platform="win32"))
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

    monkeypatch.setattr(Path, "rename", fail_rename)
    monkeypatch.setattr(
        publication,
        "os",
        SimpleNamespace(name="nt", fsencode=os.fsencode),
    )
    monkeypatch.setattr(publication, "sys", SimpleNamespace(platform="win32"))
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

    monkeypatch.setattr(Path, "lstat", fail_staging_stat)
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

    monkeypatch.setattr(Path, "lstat", forged_staging_stat)
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

    monkeypatch.setattr(Path, "lstat", forged_destination_stat)
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

    monkeypatch.setattr(ctypes, "CDLL", fake_cdll)
    _fake_linux_host(monkeypatch)
    with pytest.raises(OSError, match="invalid status") as rejected:
        publication.publish_directory_no_replace(staging, destination)
    assert rejected.value.errno == errno.EINVAL
    assert native.call_count == 1
    assert staging.is_dir()
    assert not destination.exists()


@pytest.mark.parametrize("failure_type", [ValueError, RuntimeError])
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

    monkeypatch.setattr(ctypes, "CDLL", fail_cdll)
    _fake_linux_host(monkeypatch)
    with pytest.raises(OSError, match="unavailable") as rejected:
        publication.publish_directory_no_replace(staging, destination)
    assert rejected.value.errno == errno.ENOTSUP
    assert staging.is_dir()
    assert not destination.exists()


@pytest.mark.parametrize("failure_type", [ValueError, RuntimeError, TypeError])
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

    monkeypatch.setattr(ctypes, "CDLL", fake_cdll)
    _fake_linux_host(monkeypatch)
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

        monkeypatch.setattr(ctypes, "CDLL", fake_cdll)
        _fake_linux_host(monkeypatch)
        os_name, host_platform = "posix", "linux"
    else:

        def pretend_rename(_source: Path, _target: Path) -> Path:
            return destination

        monkeypatch.setattr(Path, "rename", pretend_rename)
        monkeypatch.setattr(
            publication,
            "os",
            SimpleNamespace(name="nt", fsencode=os.fsencode),
        )
        monkeypatch.setattr(publication, "sys", SimpleNamespace(platform="win32"))
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

    monkeypatch.setattr(ctypes, "CDLL", fake_cdll)
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
