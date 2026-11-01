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
#   - Host process and CLI receipt regression evidence for the tidy builder.
# - Must-Not:
#   - Require Visual Studio, invoke native compilers, or use ambient LLVM.
# - Allows:
#   - Inputs: synthetic native and foreign process returns and host errors.
#   - Outputs: typed rejection and exact native command evidence.
#   - Side effects: no native build, only test-local monkeypatches.
# - Split-When:
#   - Another build host has an independently versioned subprocess protocol.
# - Merge-When:
#   - All native build entrypoints share one exact receipt verifier.
# - Summary:
#   - Prove Windows clang-tidy subprocess results cannot certify other work.
# - Description:
#   - Exercises captured/uncaptured subprocess and CLI error trust boundaries.
# - Usage:
#   - Collected by the repository Python validation suite.
# - Defaults:
#   - Foreign argv, status, outputs, and error formatting fail closed.
#

"""Native receipt and host-error tests for the Windows tidy build entrypoint."""

from __future__ import annotations

import subprocess as sp  # ruff: ignore[suspicious-subprocess-import]
import sys
from typing import cast, override

import pytest

from scripts.validate import tidy_build, tidy_toolchain


@pytest.mark.parametrize("capture", [False, True])
@pytest.mark.parametrize(
    "receipt_args",
    [
        None,
        "cmake --version",
        ("cmake", "--version"),
        ["other-cmake", "--version"],
        ["cmake", "--build"],
        ["cmake", True],
    ],
)
def test_tidy_build_rejects_wrong_native_command_receipt(
    monkeypatch: pytest.MonkeyPatch,
    capture: bool,
    receipt_args: object,
) -> None:
    """A forged CompletedProcess cannot certify a different host command."""
    argv = ["cmake", "--version"]

    def fake_run(*_args: object, **_kwargs: object) -> sp.CompletedProcess[str]:
        return sp.CompletedProcess(
            cast("list[str]", receipt_args),
            0,
            stdout="ok" if capture else None,
            stderr="" if capture else None,
        )

    monkeypatch.setattr(sp, "run", fake_run)
    with pytest.raises(tidy_build.BuildError, match="process receipt"):
        tidy_build._run(argv, capture=capture)  # pyright: ignore[reportPrivateUsage]


@pytest.mark.parametrize("capture", [False, True])
@pytest.mark.parametrize("returncode", [None, False, True, 0.0, "0", object()])
def test_tidy_build_rejects_non_native_process_exit_status(
    monkeypatch: pytest.MonkeyPatch, capture: bool, returncode: object
) -> None:
    """Only exact integer exit statuses may be trusted for native commands."""
    argv = ["cmake", "--version"]

    def fake_run(*_args: object, **_kwargs: object) -> sp.CompletedProcess[str]:
        return sp.CompletedProcess(
            argv,
            cast("int", returncode),
            stdout="ok" if capture else None,
            stderr="" if capture else None,
        )

    monkeypatch.setattr(sp, "run", fake_run)
    with pytest.raises(tidy_build.BuildError, match="process receipt"):
        tidy_build._run(argv, capture=capture)  # pyright: ignore[reportPrivateUsage]


@pytest.mark.parametrize(
    ("capture", "stdout", "stderr"),
    [
        (True, b"ok", ""),
        (True, "ok", b""),
        (True, None, ""),
        (True, "ok", None),
        (True, "ok", True),
        (False, "ok", None),
        (False, None, ""),
        (False, b"", None),
    ],
)
def test_tidy_build_rejects_wrong_process_output_receipts(
    monkeypatch: pytest.MonkeyPatch,
    capture: bool,
    stdout: object,
    stderr: object,
) -> None:
    """Captured text and uncaptured None are distinct native output modes."""
    argv = ["cmake", "--version"]

    def fake_run(*_args: object, **_kwargs: object) -> sp.CompletedProcess[str]:
        return sp.CompletedProcess(
            argv,
            0,
            stdout=cast("str", stdout),
            stderr=cast("str", stderr),
        )

    monkeypatch.setattr(sp, "run", fake_run)
    with pytest.raises(tidy_build.BuildError, match="process receipt"):
        tidy_build._run(argv, capture=capture)  # pyright: ignore[reportPrivateUsage]


@pytest.mark.parametrize("capture", [False, True])
def test_tidy_build_accepts_exact_native_process_receipts(
    monkeypatch: pytest.MonkeyPatch,
    capture: bool,
) -> None:
    """Valid native CompletedProcess values preserve the requested command."""
    argv = ["cmake", "--version"]

    def fake_run(*_args: object, **_kwargs: object) -> sp.CompletedProcess[str]:
        return sp.CompletedProcess(
            argv,
            0,
            stdout="version" if capture else None,
            stderr="" if capture else None,
        )

    monkeypatch.setattr(sp, "run", fake_run)
    actual = tidy_build._run(argv, capture=capture)  # pyright: ignore[reportPrivateUsage]
    assert actual.args == argv
    assert actual.returncode == 0
    assert actual.stdout == ("version" if capture else None)
    assert actual.stderr == ("" if capture else None)


@pytest.mark.parametrize("kind", ["foreign-os", "native-os", "value", "type"])
def test_tidy_build_normalizes_host_launch_failures_with_cause(
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
) -> None:
    """Host failures preserve native text and never run foreign text hooks."""

    class HostilePermissionError(PermissionError):
        @override
        def __str__(self) -> str:
            raise AssertionError("foreign host formatter invoked")

    errors: dict[str, Exception] = {
        "foreign-os": HostilePermissionError("sensitive detail"),
        "native-os": PermissionError("access denied"),
        "value": ValueError("malformed launcher"),
        "type": TypeError("malformed launcher"),
    }
    error = errors[kind]

    def fake_run(*_args: object, **_kwargs: object) -> None:
        raise error

    monkeypatch.setattr(sp, "run", fake_run)
    expected = type(error).__name__ if kind == "foreign-os" else str(error)
    with pytest.raises(tidy_build.BuildError, match=expected) as failure:
        tidy_build._run(["cmake"], capture=True)  # pyright: ignore[reportPrivateUsage]
    assert failure.value.__cause__ is error


@pytest.mark.parametrize("kind", ["native", "foreign", "foreign-toolchain"])
def test_tidy_build_cli_does_not_format_foreign_build_errors(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    kind: str,
) -> None:
    """CLI errors must not call foreign BuildError or ToolchainError hooks."""

    class HostileBuildError(tidy_build.BuildError):
        @override
        def __str__(self) -> str:
            raise AssertionError("foreign build formatter invoked")

    class HostileToolchainError(tidy_toolchain.ToolchainError):
        @override
        def __str__(self) -> str:
            raise AssertionError("foreign toolchain formatter invoked")

    errors: dict[str, Exception] = {
        "native": tidy_build.BuildError("native build rejected"),
        "foreign": HostileBuildError("untrusted build"),
        "foreign-toolchain": HostileToolchainError("untrusted toolchain"),
    }
    fault = errors[kind]

    def fail_identity(**_kwargs: object) -> None:
        raise fault

    monkeypatch.setattr(tidy_toolchain, "load_identity", fail_identity)
    monkeypatch.setattr(sys, "argv", ["tidy-build"])
    assert tidy_build.main() == 1
    stderr = capsys.readouterr().err
    if kind == "native":
        assert "native build rejected" in stderr
    else:
        assert type(fault).__name__ in stderr


@pytest.mark.parametrize("capture", [False, True])
def test_tidy_build_rejects_foreign_process_wrapper(
    monkeypatch: pytest.MonkeyPatch,
    capture: bool,
) -> None:
    """A custom completion subclass cannot prove a successful build."""

    class ForeignCompletion(sp.CompletedProcess[str]):
        pass

    argv = ["cmake", "--version"]

    def fake_run(*_args: object, **_kwargs: object) -> ForeignCompletion:
        return ForeignCompletion(
            argv,
            0,
            stdout="ok" if capture else None,
            stderr="" if capture else None,
        )

    monkeypatch.setattr(sp, "run", fake_run)
    with pytest.raises(tidy_build.BuildError, match="process receipt"):
        tidy_build._run(argv, capture=capture)  # pyright: ignore[reportPrivateUsage]


@pytest.mark.parametrize("returncode", [0, 7])
def test_tidy_build_checked_output_uses_authenticated_command(
    monkeypatch: pytest.MonkeyPatch, returncode: int
) -> None:
    """Only validated Clang text is returned for exact successful probes."""
    command = ["clang-tidy", "--version"]

    def fake_run(*_args: object, **_kwargs: object) -> sp.CompletedProcess[str]:
        return sp.CompletedProcess(
            command, returncode, stdout="LLVM version 22.1.8", stderr="warning"
        )

    monkeypatch.setattr(sp, "run", fake_run)
    if returncode == 0:
        actual = tidy_build._checked_output(  # pyright: ignore[reportPrivateUsage]
            command, "Clang host"
        )
        assert actual == "LLVM version 22.1.8\nwarning"
    else:
        with pytest.raises(tidy_build.BuildError, match="status 7"):
            tidy_build._checked_output(  # pyright: ignore[reportPrivateUsage]
                command, "Clang host"
            )


@pytest.mark.parametrize("kind", ["native-toolchain", "native-linux", "foreign-linux"])
def test_tidy_build_cli_safely_handles_cross_builder_errors(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    kind: str,
) -> None:
    """The dispatcher prints exact native failures but not foreign hooks."""
    from scripts.validate import tidy_build_linux

    class HostileLinuxBuildError(tidy_build_linux.LinuxBuildError):
        @override
        def __str__(self) -> str:
            raise AssertionError("foreign Linux failure formatted")

    errors: dict[str, Exception] = {
        "native-toolchain": tidy_toolchain.ToolchainError("native toolchain failure"),
        "native-linux": tidy_build_linux.LinuxBuildError("native Linux failure"),
        "foreign-linux": HostileLinuxBuildError("foreign Linux failure"),
    }
    fault = errors[kind]

    def fail_identity(**_kwargs: object) -> None:
        raise fault

    monkeypatch.setattr(tidy_toolchain, "load_identity", fail_identity)
    assert tidy_build.main() == 1
    actual = capsys.readouterr().err
    if kind == "foreign-linux":
        assert "HostileLinuxBuildError" in actual
    else:
        assert str(fault) in actual
