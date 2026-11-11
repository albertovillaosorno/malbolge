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
#   - Linux normalized C frontend build orchestration regressions.
# - Must-Not:
#   - Use Windows tools, ambient LLVM development paths, or network access.
# - Allows:
#   - Inputs: exact repository-local LLVM runtime/development identity.
#   - Outputs: deterministic Linux CMake/Ninja argv and output path assertions.
#   - Side effects: test-local paths only.
# - Split-When:
#   - Another POSIX frontend host gains an independent native build ABI.
# - Merge-When:
#   - Frontend build protocols become identical across supported platforms.
# - Summary:
#   - Lock the Linux normalized C frontend build boundary.
# - Description:
#   - Proves exact local LLVM roots and neutral compiler/output selection.
# - Usage:
#   - Collected by the repository Python test suite.
# - Defaults:
#   - Unsupported platform or missing exact inputs fails closed.
#

"""Linux normalized C frontend build orchestration regressions."""

from __future__ import annotations

import subprocess as sp  # ruff: ignore[suspicious-subprocess-import] - mocked; no processes run.
import sys
from typing import TYPE_CHECKING, TextIO, cast, override

import pytest

from scripts.validate import c_frontend_build, c_frontend_build_linux, tidy_toolchain

if TYPE_CHECKING:
    from pathlib import Path

LINUX_PLATFORM = "linux-x86_64"
CXX_DRIVER_MODE = "--driver-mode=g++"
WINDOWS_EXECUTABLE_SUFFIX = ".exe"


def test_linux_frontend_configure_uses_exact_local_llvm_roots(
    tmp_path: Path,
) -> None:
    """Linux configure uses neutral Clang and exact local LLVM inputs."""
    identity = tidy_toolchain.load_identity(
        root=tmp_path,
        platform_id=LINUX_PLATFORM,
    )
    tools = c_frontend_build_linux.LinuxFrontendBuildTools(
        cmake=tmp_path / "cmake",
        ninja=tmp_path / "ninja",
    )
    output_root = tmp_path / ".dependencies/compiler-c-frontend/22.1.8"

    command = c_frontend_build_linux.configure_command(
        identity,
        tools,
        output_root=output_root,
    )
    rendered = " ".join(command)

    assert command[0] == str(tools.cmake)
    assert CXX_DRIVER_MODE in rendered
    assert str(identity.clang) in rendered
    assert str(identity.development_root) in rendered
    assert str(identity.runtime_root) in rendered
    assert str(output_root) in rendered
    assert WINDOWS_EXECUTABLE_SUFFIX not in rendered


@pytest.mark.parametrize(
    "path_kind",
    [
        "cache-parent-symlink",
        "cache-leaf-symlink",
        "cache-parent-file",
        "cache-leaf-file",
        "output-parent-symlink",
        "output-leaf-symlink",
        "output-parent-file",
        "output-leaf-file",
    ],
)
def test_linux_frontend_build_rejects_unphysical_output_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    path_kind: str,
) -> None:
    """Never invoke CMake through redirected cache or output ancestors."""
    identity = tidy_toolchain.load_identity(root=tmp_path, platform_id=LINUX_PLATFORM)
    cache = tmp_path / ".cache/compiler-c-frontend/22.1.8/linux-x86_64/build"
    output = tmp_path / ".dependencies/compiler-c-frontend/22.1.8"
    monkeypatch.setattr(c_frontend_build_linux, "BUILD_ROOT", cache)
    selected = cache if path_kind.startswith("cache-") else output
    if "parent" in path_kind:
        selected = tmp_path / (
            ".cache" if path_kind.startswith("cache-") else ".dependencies"
        )
    external = tmp_path / "foreign"
    external.mkdir()
    sentinel = external / "sentinel.txt"
    _ = sentinel.write_bytes(b"foreign data")
    selected.parent.mkdir(parents=True, exist_ok=True)
    if path_kind.endswith("symlink"):
        try:
            selected.symlink_to(external, target_is_directory=True)
        except (OSError, NotImplementedError) as error:
            pytest.skip(f"directory links unavailable: {error}")
    else:
        _ = selected.write_bytes(b"not a directory")
    commands: list[str] = []

    def validate_stub(_identity: tidy_toolchain.ToolchainIdentity) -> None:
        return None

    def run_stub(_command: list[str], label: str) -> None:
        commands.append(label)

    monkeypatch.setattr(tidy_toolchain, "validate_installation", validate_stub)
    monkeypatch.setattr(
        c_frontend_build_linux,
        "linux_build_tools",
        lambda: c_frontend_build_linux.LinuxFrontendBuildTools(
            cmake=tmp_path / "cmake", ninja=tmp_path / "ninja"
        ),
    )
    monkeypatch.setattr(c_frontend_build_linux, "_checked_run", run_stub)
    with pytest.raises(
        c_frontend_build_linux.LinuxFrontendBuildError, match="build|output"
    ):
        c_frontend_build_linux.build(identity, output_root=output)
    assert not commands
    assert sentinel.read_bytes() == b"foreign data"
    assert list(external.iterdir()) == [sentinel]


@pytest.mark.parametrize("target_kind", ["cache", "output"])
def test_linux_frontend_rejects_path_swap_after_configure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    target_kind: str,
) -> None:
    """Native build must not run after configure redirects the build sink."""
    identity = tidy_toolchain.load_identity(root=tmp_path, platform_id=LINUX_PLATFORM)
    cache = tmp_path / ".cache/compiler-c-frontend/22.1.8/linux-x86_64/build"
    output = tmp_path / ".dependencies/compiler-c-frontend/22.1.8"
    monkeypatch.setattr(c_frontend_build_linux, "BUILD_ROOT", cache)
    external = tmp_path / "foreign"
    external.mkdir()
    probe = tmp_path / "link-capability-probe"
    try:
        probe.symlink_to(external, target_is_directory=True)
    except (OSError, NotImplementedError) as error:
        pytest.skip(f"directory links unavailable: {error}")
    probe.unlink()
    sentinel = external / "sentinel.txt"
    _ = sentinel.write_bytes(b"foreign data")
    calls: list[str] = []

    def validate_stub(_identity: tidy_toolchain.ToolchainIdentity) -> None:
        return None

    def run_stub(_command: list[str], label: str) -> None:
        calls.append(label)
        if label == "CMake configure":
            target = cache if target_kind == "cache" else output
            target.rmdir()
            target.symlink_to(external, target_is_directory=True)

    monkeypatch.setattr(tidy_toolchain, "validate_installation", validate_stub)
    monkeypatch.setattr(
        c_frontend_build_linux,
        "linux_build_tools",
        lambda: c_frontend_build_linux.LinuxFrontendBuildTools(
            cmake=tmp_path / "cmake", ninja=tmp_path / "ninja"
        ),
    )
    monkeypatch.setattr(c_frontend_build_linux, "_checked_run", run_stub)
    with pytest.raises(
        c_frontend_build_linux.LinuxFrontendBuildError, match="redirect"
    ):
        c_frontend_build_linux.build(identity, output_root=output)
    assert calls == ["CMake configure"]
    assert sentinel.read_bytes() == b"foreign data"
    assert list(external.iterdir()) == [sentinel]


@pytest.mark.parametrize(
    "receipt_kind",
    ["wrong_args", "tuple_args", "foreign_args", "foreign_token"],
)
def test_linux_frontend_refuses_forged_cmake_command_receipts(
    monkeypatch: pytest.MonkeyPatch,
    receipt_kind: str,
) -> None:
    """Native CMake success must attest to the exact launched argument list."""

    class ForeignArgs(list[str]):
        def __eq__(self, _other: object) -> bool:
            raise AssertionError("foreign CMake argv equality hook executed")

    class ForeignToken(str):
        def __eq__(self, _other: object) -> bool:
            raise AssertionError("foreign CMake token equality hook executed")

    def forged_run(args: list[str], **_kwargs: object) -> object:
        malformed: object = {
            "wrong_args": [*args, "--forged"],
            "tuple_args": tuple(args),
            "foreign_args": ForeignArgs(args),
            "foreign_token": [ForeignToken(args[0]), *args[1:]],
        }[receipt_kind]
        return sp.CompletedProcess(
            cast("list[str]", cast("object", malformed)),
            0,
            stdout="",
            stderr="",
        )

    monkeypatch.setattr(c_frontend_build_linux.sp, "run", forged_run)
    with pytest.raises(
        c_frontend_build_linux.LinuxFrontendBuildError, match="process receipt"
    ):
        c_frontend_build_linux._checked_run(["cmake", "--version"], "CMake")


@pytest.mark.parametrize("location", ["parent", "leaf"])
@pytest.mark.parametrize("method", ["is_symlink", "is_junction", "exists", "is_dir"])
@pytest.mark.parametrize("receipt", [0, None])
def test_linux_frontend_refuses_non_native_output_directory_status(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    location: str,
    method: str,
    receipt: object,
) -> None:
    """Every physical output ancestor requires exact native boolean status."""
    parent = tmp_path / "cache"
    leaf = parent / "build"
    leaf.mkdir(parents=True)
    target = parent if location == "parent" else leaf
    native = getattr(type(leaf), method)

    def forged_status(path: Path) -> object:
        return receipt if path == target else native(path)

    with monkeypatch.context() as isolated:
        isolated.setattr(type(leaf), method, forged_status)
        with pytest.raises(
            c_frontend_build_linux.LinuxFrontendBuildError, match="status receipt"
        ):
            c_frontend_build_linux._require_physical_build_directory(leaf, "test")


def test_linux_frontend_native_cmake_receipt_preserves_success_and_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Exact CMake subprocess evidence retains native nonzero exit outcomes."""

    def run(args: list[str], **_kwargs: object) -> sp.CompletedProcess[str]:
        return sp.CompletedProcess(args, 0, stdout="configured", stderr="")

    monkeypatch.setattr(c_frontend_build_linux.sp, "run", run)
    c_frontend_build_linux._checked_run(["cmake", "--version"], "CMake")

    def failing(args: list[str], **_kwargs: object) -> sp.CompletedProcess[str]:
        return sp.CompletedProcess(args, 9, stdout="", stderr="native failure")

    monkeypatch.setattr(c_frontend_build_linux.sp, "run", failing)
    with pytest.raises(
        c_frontend_build_linux.LinuxFrontendBuildError,
        match="status 9: native failure",
    ):
        c_frontend_build_linux._checked_run(["cmake", "--version"], "CMake")


@pytest.mark.parametrize(
    "case", ("partial", "foreign-count", "write-fault", "flush-fault", "foreign-flush")
)
def test_frontend_build_cli_requires_output_receipt(
    monkeypatch: pytest.MonkeyPatch, case: str
) -> None:
    """Successful build execution cannot override an incomplete output stream."""

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

    monkeypatch.setattr(c_frontend_build, "build", lambda: None)
    monkeypatch.setattr(sys, "stdout", cast("TextIO", cast("object", FakeOutput())))
    assert c_frontend_build.main() == 1


def test_frontend_build_cli_delivers_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A complete record must be flushed before reporting a ready binary."""

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

    output = CapturingOutput()
    monkeypatch.setattr(c_frontend_build, "build", lambda: None)
    monkeypatch.setattr(sys, "stdout", cast("TextIO", cast("object", output)))
    assert c_frontend_build.main() == 0
    assert output.messages == [
        f"C frontend ready: {c_frontend_build.EXECUTABLE}\n"
    ]
    assert output.flushes == 1


def test_frontend_build_cli_rejects_foreign_error_formatting(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Build-error subclasses cannot execute caller-owned string hooks."""

    class ForeignBuildError(c_frontend_build.FrontendBuildError):
        def __str__(self) -> str:
            raise AssertionError("foreign build formatter invoked")

    def fail_build() -> None:
        raise ForeignBuildError("opaque")

    monkeypatch.setattr(c_frontend_build, "build", fail_build)
    assert c_frontend_build.main() == 1
    assert "ForeignBuildError" in capsys.readouterr().err


def test_frontend_build_cli_failed_diagnostics_retain_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An invalid build remains a failure even if diagnostics cannot write."""

    class BrokenStderr:
        def write(self, _message: str) -> None:
            raise OSError("diagnostic failed")

    def fail_build() -> None:
        raise c_frontend_build.FrontendBuildError("build invalid")

    monkeypatch.setattr(c_frontend_build, "build", fail_build)
    monkeypatch.setattr(sys, "stderr", cast("TextIO", cast("object", BrokenStderr())))
    assert c_frontend_build.main() == 1


@pytest.mark.parametrize("mutation", ("executable", "append", "remove"))
def test_linux_frontend_rejects_mutated_cmake_launch_command(
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
) -> None:
    """A launcher cannot mutate the expected argv along with its CMake receipt."""
    command = ["cmake", "--version"]

    def mutating_run(args: list[str], **_kwargs: object) -> sp.CompletedProcess[str]:
        if mutation == "executable":
            args[0] = "/foreign/cmake"
        elif mutation == "append":
            args.append("--unexpected")
        else:
            _ = args.pop()
        return sp.CompletedProcess(args, 0, stdout="", stderr="")

    monkeypatch.setattr(c_frontend_build_linux.sp, "run", mutating_run)
    with pytest.raises(
        c_frontend_build_linux.LinuxFrontendBuildError, match="process receipt"
    ):
        c_frontend_build_linux._checked_run(command, "CMake")
    assert command == ["cmake", "--version"]


@pytest.mark.parametrize("capture", (False, True))
@pytest.mark.parametrize(
    "receipt",
    ("wrong-argv", "false-exit", "invalid-output", "foreign-process", "mutated-argv"),
)
def test_frontend_launcher_rejects_forged_process_receipt(
    monkeypatch: pytest.MonkeyPatch,
    capture: bool,
    receipt: str,
) -> None:
    """Windows build and version probes require native immutable command evidence."""
    command = ["frontend", "--version"]

    class ForeignCompletion(sp.CompletedProcess[str]):
        pass

    def run(args: list[str], **_kwargs: object) -> sp.CompletedProcess[str]:
        if receipt == "mutated-argv":
            args[0] = "/foreign/frontend"
        received = [*args, "--forged"] if receipt == "wrong-argv" else args
        status = cast("int", False) if receipt == "false-exit" else 0
        stdout = "expected" if capture else None
        stderr = "" if capture else None
        if receipt == "invalid-output":
            stdout = cast("str", cast("object", b"unexpected"))
        if receipt == "foreign-process":
            return ForeignCompletion(received, status, stdout=stdout, stderr=stderr)
        return sp.CompletedProcess(received, status, stdout=stdout, stderr=stderr)

    monkeypatch.setattr(sp, "run", run)
    with pytest.raises(c_frontend_build.FrontendBuildError, match="process receipt"):
        _ = c_frontend_build._run(command, capture=capture)  # pyright: ignore[reportPrivateUsage]
    assert command == ["frontend", "--version"]


@pytest.mark.parametrize("capture", (False, True))
def test_frontend_launcher_accepts_native_process_receipt(
    monkeypatch: pytest.MonkeyPatch,
    capture: bool,
) -> None:
    """Authentic build and version receipts retain both capture modes."""
    command = ["frontend", "--version"]

    def run(args: list[str], **_kwargs: object) -> sp.CompletedProcess[str]:
        return sp.CompletedProcess(
            args, 0, stdout="expected" if capture else None,
            stderr="" if capture else None,
        )

    monkeypatch.setattr(sp, "run", run)
    result = c_frontend_build._run(command, capture=capture)  # pyright: ignore[reportPrivateUsage]
    assert result.args == command
    assert result.returncode == 0
    assert result.stdout == ("expected" if capture else None)
    assert result.stderr == ("" if capture else None)


@pytest.mark.parametrize("fault", ("os", "foreign-os", "value", "type", "runtime"))
def test_frontend_launcher_types_host_failures_without_foreign_formatters(
    monkeypatch: pytest.MonkeyPatch,
    fault: str,
) -> None:
    """Host launch exceptions cannot bypass build diagnostics or run hooks."""

    class ForeignOSError(OSError):
        @override
        def __str__(self) -> str:
            raise AssertionError("foreign host error formatter invoked")

    failures: dict[str, Exception] = {
        "os": OSError("native host failure"),
        "foreign-os": ForeignOSError("hostile"),
        "value": ValueError("invalid launch"),
        "type": TypeError("invalid argv"),
        "runtime": RuntimeError("invalid runner"),
    }
    expected = failures[fault]

    def raise_host_error(_args: list[str], **_kwargs: object) -> None:
        raise expected

    monkeypatch.setattr(sp, "run", raise_host_error)
    with pytest.raises(
        c_frontend_build.FrontendBuildError, match="failed to execute frontend"
    ) as caught:
        _ = c_frontend_build._run(["frontend"], capture=True)  # pyright: ignore[reportPrivateUsage]
    assert caught.value.__cause__ is expected
    assert ("ForeignOSError" in str(caught.value)) == (fault == "foreign-os")
