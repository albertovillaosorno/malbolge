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

from algorithms.diff import publication
import pytest

_WINDOWS_OS_NAME = "nt"
_LINUX_PLATFORM = "linux"
_OURS = b"ours"
_FOREIGN = b"foreign"


def test_windows_route_uses_path_rename(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Route Windows publication through the host no-overwrite rename API."""
    staging = Path("staging")
    destination = Path("destination")
    calls: list[tuple[Path, Path]] = []

    def record_rename(path: Path, target: Path) -> Path:
        calls.append((path, target))
        return target

    monkeypatch.setattr(Path, "rename", record_rename)
    publication.publish_directory_no_replace(
        staging, destination, os_name=_WINDOWS_OS_NAME, platform="win32"
    )
    assert calls == [(staging, destination)]


def test_linux_route_uses_renameat2(monkeypatch: pytest.MonkeyPatch) -> None:
    """Route Linux publication through renameat2 with no-replace semantics."""
    staging = Path("staging")
    destination = Path("destination")
    calls: list[tuple[Path, Path]] = []

    def record_rename(source: Path, target: Path) -> None:
        calls.append((source, target))

    monkeypatch.setattr(publication, "_linux_rename_noreplace", record_rename)
    publication.publish_directory_no_replace(
        staging, destination, os_name="posix", platform=_LINUX_PLATFORM
    )
    assert calls == [(staging, destination)]


def test_unsupported_host_fails_closed() -> None:
    """Do not emulate atomic no-replace semantics on an unsupported host."""
    with pytest.raises(OSError, match="unsupported") as caught:
        publication.publish_directory_no_replace(
            Path("staging"),
            Path("destination"),
            os_name="posix",
            platform="unsupported",
        )
    assert caught.value.errno == errno.ENOTSUP


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
