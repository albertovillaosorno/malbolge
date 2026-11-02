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
#   - Regression tests for the Python validation command error boundary.
# - Must-Not:
#   - Run real provisioners, install tools, or modify the repository toolchain.
# - Allows:
#   - Inputs: synthetic bootstrap errors and isolated process output capture.
#   - Outputs: deterministic, typed CLI error handling evidence.
#   - Side effects: pytest-local monkeypatches and stderr capture only.
# - Split-When:
#   - Another independent CLI responsibility needs separate fixtures.
# - Merge-When:
#   - Another test module owns the same Python validation CLI contract.
# - Summary:
#   - Fail closed without formatting foreign exception objects at the CLI.
#

"""Python validation bootstrap CLI host-error regressions."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Never
from typing import override

import pytest
from scripts.bootstrap import python_validation


@pytest.mark.parametrize("category", ["host", "provision", "process"])
def test_python_validation_cli_does_not_format_foreign_errors(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    category: str,
) -> None:
    """An unexpected exception subclass cannot invoke host-defined str hooks."""

    class ForeignHostError(OSError):
        @override
        def __str__(self) -> Never:
            raise AssertionError("host formatter was called")

    class ForeignProvisionError(python_validation.ProvisionError):
        @override
        def __str__(self) -> Never:
            raise AssertionError("provision formatter was called")

    class ForeignProcessError(subprocess.SubprocessError):
        @override
        def __str__(self) -> Never:
            raise AssertionError("process formatter was called")

    errors = {
        "host": ForeignHostError("host is unavailable"),
        "provision": ForeignProvisionError("tool is unavailable"),
        "process": ForeignProcessError("process is unavailable"),
    }
    fault = errors[category]

    def fail_initialize() -> Never:
        raise fault

    monkeypatch.setattr(python_validation, "initialize", fail_initialize)
    assert python_validation.main() == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    expected = {
        "host": "host is unavailable",
        "provision": "tool is unavailable",
        "process": "process is unavailable",
    }
    assert captured.err == f"error: {expected[category]}\n"


def test_python_validation_cli_preserves_owned_failure_details(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Exact locally authored failures still explain the provisioning fault."""
    fault = python_validation.ProvisionError(
        "pinned Python installation failed"
    )

    def fail_initialize() -> Never:
        raise fault

    monkeypatch.setattr(python_validation, "initialize", fail_initialize)
    assert python_validation.main() == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == "error: pinned Python installation failed\n"


def test_python_validation_cli_ignores_overridden_exception_args(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A foreign args property must not replace native exception details."""

    class ForeignArgsError(OSError):
        pass

    def hostile_args(_instance: ForeignArgsError) -> Never:
        raise AssertionError("host args hook was called")

    fault = ForeignArgsError("native host message")
    monkeypatch.setattr(ForeignArgsError, "args", property(hostile_args))

    def fail_initialize() -> Never:
        raise fault

    monkeypatch.setattr(python_validation, "initialize", fail_initialize)
    assert python_validation.main() == 1
    assert capsys.readouterr().err == "error: native host message\n"


def test_python_validation_cli_rejects_nonstring_native_error_payload(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Untrusted payload objects cannot be formatted even by an owned error."""

    class HostilePayload:
        @override
        def __str__(self) -> Never:
            raise AssertionError("payload string hook was called")

        @override
        def __repr__(self) -> Never:
            raise AssertionError("payload representation hook was called")

    fault = python_validation.ProvisionError(HostilePayload())

    def fail_initialize() -> Never:
        raise fault

    monkeypatch.setattr(python_validation, "initialize", fail_initialize)
    assert python_validation.main() == 1
    assert capsys.readouterr().err == "error: ProvisionError\n"


@pytest.mark.parametrize("receipt", ["short", "boolean", "flush"])
def test_python_validation_cli_rejects_incomplete_report_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    receipt: str,
) -> None:
    """Success requires complete and flushed readiness output."""
    layout = python_validation.validation_layout(tmp_path)
    message = (
        f"python validation environment ready: {layout.environment}\n"
    )
    written: list[str] = []

    class BrokenStdout:
        def write(self, value: str) -> int:
            written.append(value)
            if receipt == "short":
                return len(value) - 1
            if receipt == "boolean":
                return True
            return len(value)

        def flush(self) -> None:
            if receipt == "flush":
                raise OSError("cannot flush")

    def fake_initialize() -> python_validation.ValidationEnvironmentLayout:
        return layout

    monkeypatch.setattr(python_validation, "initialize", fake_initialize)
    with monkeypatch.context() as isolated:
        isolated.setattr(sys, "stdout", BrokenStdout())
        assert python_validation.main() == 1
    assert written == [message]
    captured = capsys.readouterr()
    assert "error:" in captured.err


def test_python_validation_cli_flushes_complete_readiness_report(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Successful readiness output must be complete and visibly flushed."""
    layout = python_validation.validation_layout(tmp_path)
    calls: list[str] = []

    class CapturingStdout:
        def write(self, text: str) -> int:
            calls.append(text)
            return len(text)

        def flush(self) -> None:
            calls.append("flush")

    def fake_initialize() -> python_validation.ValidationEnvironmentLayout:
        return layout

    monkeypatch.setattr(python_validation, "initialize", fake_initialize)
    with monkeypatch.context() as isolated:
        isolated.setattr(sys, "stdout", CapturingStdout())
        assert python_validation.main() == 0
    assert calls == [
        f"python validation environment ready: {layout.environment}\n",
        "flush",
    ]
