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
#   - Host exception handling for native Linux plugin and C frontend builders.
# - Must-Not:
#   - Execute native tools or change checkout build outputs.
# - Allows:
#   - Inputs: deterministic injected process exceptions.
#   - Outputs: typed build errors retaining exact original causes.
#   - Side effects: monkeypatch state only.
# - Split-When:
#   - Linux native build implementations no longer share a process contract.
# - Merge-When:
#   - Another suite owns the same native builder exception boundary.
# - Summary:
#   - Reject hostile host exception string hooks for native subprocesses.

"""Fail-closed Linux plugin and frontend subprocess fault regressions."""

from __future__ import annotations

# These tests intentionally invoke private builder admission helpers.
# ruff: file-ignore[private-member-access]
# pyright: reportPrivateUsage=false
import subprocess as sp  # ruff: ignore[suspicious-subprocess-import] - patched; no processes run.
from typing import Never
from typing import override

import pytest

from scripts.validate import c_frontend_build_linux
from scripts.validate import tidy_build_linux

NATIVE_DETAIL = "synthetic native build failure"
FOREIGN_DETAIL = "ForeignNativeBuildError"
PLUGIN = "plugin"


class ForeignNativeBuildError(OSError):
    """Foreign OSError subtype with unsafe text formatting."""

    @override
    def __str__(self) -> str:
        """Refuse foreign native builder exception formatting.

        Raises:
            AssertionError: A caller invoked an untrusted formatter.

        """
        message = "foreign Linux build host formatter executed"
        raise AssertionError(message)


def _run_builder(kind: str) -> None:
    """Invoke the chosen Linux builder through its subprocess boundary."""
    if kind == PLUGIN:
        tidy_build_linux._checked_run(["cmake", "--version"], "CMake")
    else:
        c_frontend_build_linux._checked_run(["cmake", "--version"], "CMake")


class ForeignDiscoveryError(tidy_build_linux.LinuxBuildError):
    """A native tool-discovery exception with an unsafe string formatter."""

    @override
    def __str__(self) -> str:
        """Refuse to execute foreign native tool discovery formatters.

        Raises:
            AssertionError: The frontend invoked an untrusted formatter.

        """
        message = "foreign native tool discovery formatter executed"
        raise AssertionError(message)


@pytest.mark.parametrize("kind", [PLUGIN, "frontend"])
@pytest.mark.parametrize("fault_type", [ForeignNativeBuildError, OSError])
def test_linux_native_build_process_errors_are_typed_without_foreign_formatting(
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
    fault_type: type[OSError],
) -> None:
    """Both builders preserve native details without invoking foreign hooks."""
    fault = fault_type(NATIVE_DETAIL)

    def fail_process(*args: object, **kwargs: object) -> Never:
        del args, kwargs
        raise fault

    monkeypatch.setattr(sp, "run", fail_process)
    expected_type = (
        tidy_build_linux.LinuxBuildError
        if kind == PLUGIN
        else c_frontend_build_linux.LinuxFrontendBuildError
    )
    with pytest.raises(expected_type, match="failed to execute") as caught:
        _run_builder(kind)
    assert caught.value.__cause__ is fault
    expected = NATIVE_DETAIL if fault_type is OSError else FOREIGN_DETAIL
    assert expected in str(caught.value)


@pytest.mark.parametrize(
    "fault_type", [tidy_build_linux.LinuxBuildError, ForeignDiscoveryError]
)
def test_frontend_tool_discovery_preserves_trusted_native_build_errors(
    monkeypatch: pytest.MonkeyPatch,
    fault_type: type[tidy_build_linux.LinuxBuildError],
) -> None:
    """Shared CMake/Ninja discovery cannot execute untrusted error hooks."""
    fault = fault_type(NATIVE_DETAIL)

    def fail_tool_discovery() -> Never:
        raise fault

    monkeypatch.setattr(
        tidy_build_linux, "linux_build_tools", fail_tool_discovery
    )
    with pytest.raises(
        c_frontend_build_linux.LinuxFrontendBuildError,
        match=r"native|Foreign",
    ) as caught:
        _ = c_frontend_build_linux.linux_build_tools()
    assert caught.value.__cause__ is fault
    expected = (
        NATIVE_DETAIL
        if fault_type is tidy_build_linux.LinuxBuildError
        else "ForeignDiscoveryError"
    )
    assert expected in str(caught.value)
