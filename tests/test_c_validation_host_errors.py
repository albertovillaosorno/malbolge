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
#   - Native C validation dispatcher host-failure normalization regressions.
# - Must-Not:
#   - Execute native tools or depend on installed compiler availability.
# - Allows:
#   - Inputs: synthetic subprocess host failures.
#   - Outputs: typed failures with original host causes.
#   - Side effects: pytest monkeypatch state only.
# - Split-When:
#   - Dispatcher behavior gains independent process lifecycle ownership.
# - Merge-When:
#   - Existing native validation tests own the same failure contract.
# - Summary:
#   - Reject foreign host exception formatting in three C validation probes.

"""Fail-closed native C validator subprocess error normalization."""

from __future__ import annotations

from pathlib import Path

# Directly exercises the validator's private subprocess admission functions.
# ruff: file-ignore[private-member-access]
# pyright: reportPrivateUsage=false
import subprocess  # ruff: ignore[suspicious-subprocess-import] - patched only; no processes run.
from typing import Never
from typing import override

import pytest

from scripts.validate import main as validator

PROBE_VERSION = "version"
PROBE_REGISTRATION = "registration"
NATIVE_DETAIL = "synthetic native process error"
FOREIGN_DETAIL = "ForeignProcessError"


class ForeignProcessError(OSError):
    """Injected OSError subtype with untrusted textual formatter."""

    @override
    def __str__(self) -> str:
        """Reject invocation of a foreign exception text formatter.

        Raises:
            AssertionError: The validator invoked an untrusted host hook.

        """
        message = "foreign native C process error formatter executed"
        raise AssertionError(message)


def _execute_probe(probe: str, executable: Path) -> None:
    """Invoke one native C dispatcher subprocess probe without a real tool."""
    if probe == PROBE_VERSION:
        _ = validator._tool_version_output(executable, "Clang")
    elif probe == PROBE_REGISTRATION:
        validator._require_plugin_registration(
            executable, Path("/synthetic/plugin")
        )
    else:
        _ = validator._run([str(executable), "--version"])


@pytest.mark.parametrize("probe", ["version", "registration", "validation"])
@pytest.mark.parametrize("fault_type", [ForeignProcessError, OSError])
def test_native_validator_admits_only_trusted_host_error_text(
    monkeypatch: pytest.MonkeyPatch,
    probe: str,
    fault_type: type[OSError],
) -> None:
    """Typed process faults retain native details but avoid foreign hooks."""
    fault = fault_type(NATIVE_DETAIL)

    def reject_run(*args: object, **kwargs: object) -> Never:
        del args, kwargs
        raise fault

    monkeypatch.setattr(subprocess, "run", reject_run)
    executable = Path("/synthetic/clang")

    with pytest.raises(validator.InputError, match="failed") as caught:
        _execute_probe(probe, executable)
    assert caught.value.__cause__ is fault
    expected = NATIVE_DETAIL if fault_type is OSError else FOREIGN_DETAIL
    assert expected in str(caught.value)
