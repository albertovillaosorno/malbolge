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

import errno
import os
from pathlib import Path
import sys
from types import SimpleNamespace
from typing import cast

from algorithms.diff import publication
import pytest

_WINDOWS_OS_NAME = "nt"
_LINUX_PLATFORM = "linux"
_OURS = b"ours"
_FOREIGN = b"foreign"


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

    def record_rename(path: Path, target: Path) -> Path:
        calls.append((path, target))
        return target

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

    monkeypatch.setattr(publication, "_linux_rename_noreplace", record_rename)
    monkeypatch.setattr(
        publication,
        "os",
        SimpleNamespace(name="posix", fsencode=os.fsencode),
    )
    monkeypatch.setattr(
        publication, "sys", SimpleNamespace(platform=_LINUX_PLATFORM)
    )
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
    monkeypatch.setattr(
        publication, "sys", SimpleNamespace(platform="unsupported")
    )
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

    with pytest.raises(
        OSError, match=r"already exists|Cannot create|File exists"
    ):
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


@pytest.mark.parametrize("failure_type", [ValueError, RuntimeError])
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
    with pytest.raises(
        OSError, match="staging directory status failed"
    ) as rejected:
        publication.publish_directory_no_replace(staging, destination)
    assert rejected.value.errno == errno.EINVAL
    assert not rename_calls
    assert not destination.exists()
