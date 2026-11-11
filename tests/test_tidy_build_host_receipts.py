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

import os
import stat
import subprocess as sp  # ruff: ignore[suspicious-subprocess-import]
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import TextIO, cast, override

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


def _mock_successful_tidy_build(monkeypatch: pytest.MonkeyPatch) -> Path:
    """Skip native compilation, preserving CLI publication semantics."""
    plugin = Path("plugin.so")
    identity = SimpleNamespace(plugin_library=plugin)
    monkeypatch.setattr(tidy_toolchain, "load_identity", lambda **_kw: identity)
    monkeypatch.setattr(tidy_build, "build", lambda _identity: None)
    monkeypatch.setattr(tidy_build, "provision_clang_resources", lambda _identity: None)
    monkeypatch.setattr(tidy_build, "verify_outputs", lambda _identity: None)
    return plugin


@pytest.mark.parametrize(
    "case", ("partial", "foreign-count", "write-fault", "flush-fault", "foreign-flush")
)
def test_tidy_build_cli_requires_delivered_summary(
    monkeypatch: pytest.MonkeyPatch, case: str
) -> None:
    """A complete build does not certify success without delivered output."""

    class FakeOutput:
        def write(self, message: str) -> object:
            if case == "partial":
                return len(message) - 1
            if case == "foreign-count":
                return True
            if case == "write-fault":
                raise OSError("output failed")
            return len(message)

        def flush(self) -> object:
            if case == "flush-fault":
                raise OSError("flush failed")
            if case == "foreign-flush":
                return False
            return None

    _mock_successful_tidy_build(monkeypatch)
    monkeypatch.setattr(sys, "stdout", cast("TextIO", cast("object", FakeOutput())))
    assert tidy_build.main() == 1


def test_tidy_build_cli_flushes_valid_output(monkeypatch: pytest.MonkeyPatch) -> None:
    """Native full output and completed flush admit the ready status."""

    class CapturingOutput:
        messages: list[str]
        flushes: int

        def __init__(self) -> None:
            self.messages = []
            self.flushes = 0

        def write(self, message: str) -> int:
            self.messages.append(message)
            return len(message)

        def flush(self) -> None:
            self.flushes += 1

    plugin = _mock_successful_tidy_build(monkeypatch)
    output = CapturingOutput()
    monkeypatch.setattr(sys, "stdout", cast("TextIO", cast("object", output)))
    assert tidy_build.main() == 0
    assert output.messages == [f"clang-tidy plugin ready: {plugin}\n"]
    assert output.flushes == 1


def test_tidy_build_cli_failed_stderr_keeps_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A diagnostic sink failure cannot promote failed native build status."""

    class FailingStderr:
        def write(self, _message: str) -> None:
            raise OSError("diagnostics failed")

    def fail_identity(**_kwargs: object) -> None:
        raise tidy_build.BuildError("native build rejected")

    monkeypatch.setattr(tidy_toolchain, "load_identity", fail_identity)
    monkeypatch.setattr(sys, "stderr", cast("TextIO", cast("object", FailingStderr())))
    assert tidy_build.main() == 1


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


@pytest.mark.parametrize("method", ["is_symlink", "is_junction", "exists", "is_dir"])
@pytest.mark.parametrize("receipt", [None, 0, 1, "yes"])
def test_tidy_rejects_foreign_build_directory_status(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, method: str, receipt: object
) -> None:
    """Reject non-native directory status evidence on the Windows builder."""
    target = tmp_path / "build"
    target.mkdir()
    original = getattr(Path, method)

    def fake_status(self: Path) -> object:
        return receipt if self == target else original(self)

    monkeypatch.setattr(Path, method, fake_status)
    with pytest.raises(tidy_build.BuildError, match="status receipt"):
        tidy_build._require_physical_directory(  # pyright: ignore[reportPrivateUsage]
            target, "build cache"
        )


@pytest.mark.parametrize("receipt", [None, 1, "directory", object()])
def test_tidy_rejects_foreign_build_directory_stat(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, receipt: object
) -> None:
    """An lstat object from an unknown provider cannot prove directory mode."""
    target = tmp_path / "build"
    target.mkdir()
    original = Path.lstat

    def fake_lstat(self: Path, *args: object, **kwargs: object) -> object:
        return receipt if self == target else original(self, *args, **kwargs)

    monkeypatch.setattr(Path, "lstat", fake_lstat)
    with pytest.raises(tidy_build.BuildError, match="stat receipt"):
        tidy_build._require_physical_directory(  # pyright: ignore[reportPrivateUsage]
            target, "build cache"
        )


@pytest.mark.parametrize("mode", [None, True, 1.5, "directory"])
def test_tidy_rejects_foreign_build_directory_mode(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mode: object
) -> None:
    """Reject forged mode values even in a native stat_result container."""
    target = tmp_path / "build"
    target.mkdir()
    original = Path.lstat
    forged = os.stat_result((cast("int", mode), 0, 0, 1, 0, 0, 0, 0, 0, 0))

    def fake_lstat(self: Path, *args: object, **kwargs: object) -> object:
        return forged if self == target else original(self, *args, **kwargs)

    monkeypatch.setattr(Path, "lstat", fake_lstat)
    with pytest.raises(tidy_build.BuildError, match="stat receipt"):
        tidy_build._require_physical_directory(  # pyright: ignore[reportPrivateUsage]
            target, "build cache"
        )


@pytest.mark.parametrize("receipt", [None, 0, 1, "yes"])
def test_tidy_rejects_foreign_file_verdict(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, receipt: object
) -> None:
    """Require native file-status booleans for pinned host inputs."""
    target = tmp_path / "host.exe"
    _ = target.write_bytes(b"host")
    original = Path.is_file

    def fake_file(self: Path) -> object:
        return receipt if self == target else original(self)

    monkeypatch.setattr(Path, "is_file", fake_file)
    with pytest.raises(tidy_build.BuildError, match="status receipt"):
        tidy_build._require_file(target, "host")  # pyright: ignore[reportPrivateUsage]


@pytest.mark.parametrize("count", [None, True, 1.5, "1"])
def test_tidy_rejects_foreign_script_link_count(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, count: object
) -> None:
    """Only native link counts admit replacement of a cached build script."""
    target = tmp_path / "build.cmd"
    _ = target.write_text("@echo off")
    original = Path.lstat
    forged = os.stat_result(
        (stat.S_IFREG | 0o644, 0, 0, cast("int", count), 0, 0, 0, 0, 0, 0)
    )

    def fake_stat(self: Path, *args: object, **kwargs: object) -> object:
        return forged if self == target else original(self, *args, **kwargs)

    monkeypatch.setattr(Path, "lstat", fake_stat)
    with pytest.raises(tidy_build.BuildError, match="stat receipt"):
        tidy_build._require_unlinked_build_script(  # pyright: ignore[reportPrivateUsage]
            target
        )


def test_tidy_rejects_linked_host_file(tmp_path: Path) -> None:
    """A symlink is not a physical pinned build-tool executable."""
    native = tmp_path / "native.exe"
    _ = native.write_bytes(b"mock")
    alias = tmp_path / "alias.exe"
    try:
        alias.symlink_to(native)
    except (OSError, NotImplementedError) as error:
        pytest.skip(f"links unavailable: {error}")
    with pytest.raises(tidy_build.BuildError, match="redirect"):
        tidy_build._require_file(alias, "host")  # pyright: ignore[reportPrivateUsage]


def test_tidy_accepts_native_regular_build_inputs(tmp_path: Path) -> None:
    """Physical executable and singly linked script receipts remain valid."""
    native = tmp_path / "native.exe"
    _ = native.write_bytes(b"mock")
    script = tmp_path / "build.cmd"
    _ = script.write_text("@echo off")
    assert (
        tidy_build._require_file(  # pyright: ignore[reportPrivateUsage]
            native, "host"
        )
        == native
    )
    tidy_build._require_unlinked_build_script(  # pyright: ignore[reportPrivateUsage]
        script
    )
    tidy_build._require_unlinked_build_script(  # pyright: ignore[reportPrivateUsage]
        tmp_path / "not-created.cmd"
    )


@pytest.mark.parametrize("capture", [False, True])
@pytest.mark.parametrize("mutation", ["executable", "argument", "append"])
def test_tidy_build_rejects_mutated_launch_command(
    monkeypatch: pytest.MonkeyPatch,
    capture: bool,
    mutation: str,
) -> None:
    """A subprocess hook cannot rewrite expected argv and its own receipt."""
    command = ["cmake", "--version"]

    def mutate_run(args: list[str], **_kwargs: object) -> sp.CompletedProcess[str]:
        if mutation == "executable":
            args[0] = "/foreign/cmake"
        elif mutation == "argument":
            args[1] = "--build"
        else:
            args.append("--forged")
        return sp.CompletedProcess(
            args,
            0,
            stdout="ok" if capture else None,
            stderr="" if capture else None,
        )

    monkeypatch.setattr(sp, "run", mutate_run)
    with pytest.raises(tidy_build.BuildError, match="process receipt"):
        tidy_build._run(command, capture=capture)  # pyright: ignore[reportPrivateUsage]
    assert command == ["cmake", "--version"]
