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
#   - Regression coverage for exact Python validation tool version banners.
# - Must-Not:
#   - Execute, download or install host validation tools.
# - Allows:
#   - Inputs: synthetic command receipts and local path fixtures.
#   - Outputs: exact version banner admission evidence.
#   - Side effects: pytest-owned temporary files only.
# - Split-When:
#   - Independent tool binary admission needs different fixtures.
# - Merge-When:
#   - Another test module owns exactly this version receipt contract.
# - Summary:
#   - A diagnostic containing the pinned version must not pass verification.
#

"""Exact local Python tool version banner regressions."""

from __future__ import annotations

import subprocess  # ruff: ignore[suspicious-subprocess-import] - synthetic receipts only.
from pathlib import Path

import pytest
from scripts.bootstrap import python_validation


@pytest.mark.parametrize(
    "banner",
    [
        "error: found pytest 9.1.1",
        "another pytest 9.1.1",
        "pytest 9.1.10",
        "pytest 9.1.1forged",
        "pytest 9.1.1-other",
        "pytest 9.1.1\tforged",
        "pytest 9.1.1 \x1b[31mforged",
        "pytest 9.1.1 \rforged",
        "pytest 9.1.1 \u202eforged",
        "pytest 9.1.1 \x7fforged",
    ],
)
def test_python_tool_version_rejects_embedded_expected_banner(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    banner: str,
) -> None:
    """A version substring alone cannot authenticate the installed tool."""
    layout = python_validation.validation_layout(tmp_path)
    layout.scripts.mkdir(parents=True)
    executable = "pytest"
    expected = "pytest 9.1.1"
    executable_path = layout.scripts / executable
    _ = executable_path.write_bytes(b"synthetic-executable")

    def fake_run(command: list[str]) -> str:
        assert command == [str(executable_path), "--version"]
        return banner

    monkeypatch.setattr(python_validation, "_run", fake_run)
    with pytest.raises(python_validation.ProvisionError, match="unexpected"):
        python_validation._verify_tool(  # pyright: ignore[reportPrivateUsage]
            layout, executable, expected
        )


@pytest.mark.parametrize(
    ("expected", "banner"),
    [
        ("pytest 9.1.1", "pytest 9.1.1"),
        ("ruff 0.16.9", "ruff 0.16.9 (build info)"),
        ("Python 3.14.7", "Python 3.14.7\nadditional details"),
    ],
)
def test_python_tool_version_accepts_exact_banner_and_space_suffix(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    expected: str,
    banner: str,
) -> None:
    """The pinned tool/version prefix remains valid with optional metadata."""
    layout = python_validation.validation_layout(tmp_path)
    layout.scripts.mkdir(parents=True)
    executable = "pytest"
    executable_path = layout.scripts / executable
    _ = executable_path.write_bytes(b"synthetic-executable")

    def fake_run(command: list[str]) -> str:
        assert command == [str(executable_path), "--version"]
        return banner

    monkeypatch.setattr(python_validation, "_run", fake_run)
    python_validation._verify_tool(  # pyright: ignore[reportPrivateUsage]
        layout, executable, expected
    )


def test_python_tool_version_rejects_symlinked_executable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A linked local tool cannot delegate the version probe outside checkout."""
    layout = python_validation.validation_layout(tmp_path)
    layout.scripts.mkdir(parents=True)
    foreign = tmp_path / "foreign-pytest"
    _ = foreign.write_bytes(b"foreign-tool")
    executable_path = layout.scripts / "pytest"
    try:
        _ = executable_path.symlink_to(foreign)
    except (OSError, NotImplementedError) as error:
        pytest.skip(f"symlinks unavailable: {error}")
    calls: list[list[str]] = []

    def fake_run(command: list[str]) -> str:
        calls.append(command)
        return "pytest 9.1.1"

    monkeypatch.setattr(python_validation, "_run", fake_run)
    with pytest.raises(python_validation.ProvisionError, match="redirect"):
        python_validation._verify_tool(  # pyright: ignore[reportPrivateUsage]
            layout, "pytest", "pytest 9.1.1"
        )
    assert not calls
    assert foreign.read_bytes() == b"foreign-tool"


def test_python_tool_version_rejects_executable_swapped_during_probe(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A version line cannot authenticate a different post-probe binary."""
    layout = python_validation.validation_layout(tmp_path)
    layout.scripts.mkdir(parents=True)
    executable_path = layout.scripts / "pytest"
    original = b"verified-tool"
    _ = executable_path.write_bytes(original)
    previous = tmp_path / "prior-pytest"
    swapped = False

    def fake_run(command: list[str]) -> str:
        nonlocal swapped
        assert command == [str(executable_path), "--version"]
        _ = executable_path.replace(previous)
        _ = executable_path.write_bytes(b"replaced-tool")
        swapped = True
        return "pytest 9.1.1"

    monkeypatch.setattr(python_validation, "_run", fake_run)
    with pytest.raises(python_validation.ProvisionError, match="changed"):
        python_validation._verify_tool(  # pyright: ignore[reportPrivateUsage]
            layout, "pytest", "pytest 9.1.1"
        )
    assert swapped
    assert previous.read_bytes() == original


@pytest.mark.parametrize("executable", ["pytest", "uv"])
def test_python_version_probe_rejects_success_with_stderr(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    executable: str,
) -> None:
    """A successful exit and pinned stdout cannot conceal host diagnostics."""
    command = [str(tmp_path / executable), "--version"]

    def fake_run(
        argv: list[str],
        **kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        assert argv == command
        assert kwargs == {
            "cwd": python_validation.ROOT,
            "check": True,
            "capture_output": True,
            "shell": False,
            "text": True,
        }
        return subprocess.CompletedProcess(
            argv,
            0,
            f"{executable} 9.1.1\n",
            "error: binary integrity mismatch\n",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)
    with pytest.raises(python_validation.ProvisionError, match="stderr"):
        _ = python_validation._run(command)  # ruff: ignore[private-member-access]  # pyright: ignore[reportPrivateUsage]


def test_python_provision_command_allows_informational_stderr(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Installer progress is not equivalent to a version probe receipt."""
    command = ["uv", "pip", "sync"]
    expected = "installed"

    def fake_run(
        argv: list[str],
        **kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        assert argv == command
        assert kwargs["cwd"] == python_validation.ROOT
        return subprocess.CompletedProcess(
            argv, 0, f"{expected}\n", "Resolved 2 packages\n"
        )

    monkeypatch.setattr(subprocess, "run", fake_run)
    output = python_validation._run(command)  # ruff: ignore[private-member-access]  # pyright: ignore[reportPrivateUsage]
    assert output == expected


@pytest.mark.parametrize(
    "suffix",
    ["\x00suffix", "\x1b[31m", "\x7f", "\tmetadata", "\u202emetadata"],
)
def test_python_fast_jig_alias_rejects_unsafe_version_characters(
    suffix: str,
) -> None:
    """Nonprintable or bidirectional text must not enter a shell alias."""
    version_line = f"pytest 9.1.1{suffix}"
    pv = python_validation
    with pytest.raises(pv.ProvisionError, match="shell-literal safe"):
        _ = pv._posix_jig_tool_alias_text(  # ruff: ignore[private-member-access]  # pyright: ignore[reportPrivateUsage]
            "pytest", version_line
        )


@pytest.mark.parametrize(
    "version_line", ["", "   ", " pytest 9.1.1", "pytest 9.1.1 "]
)
def test_python_fast_jig_alias_rejects_blank_or_padded_version(
    version_line: str,
) -> None:
    """Fast version aliases cannot certify blank or padded authorities."""
    pv = python_validation
    with pytest.raises(pv.ProvisionError, match="shell-literal safe"):
        _ = pv._posix_jig_tool_alias_text(  # ruff: ignore[private-member-access]  # pyright: ignore[reportPrivateUsage]
            "pytest", version_line
        )


@pytest.mark.parametrize(
    "banner",
    [
        " pytest 9.1.1\n",
        "\tpytest 9.1.1\n",
        "\npytest 9.1.1\n",
        "pytest 9.1.1 \n",
        "pytest 9.1.1\n\n",
        "pytest 9.1.1\r",
    ],
)
def test_python_version_probe_rejects_trimmed_stdout(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    banner: str,
) -> None:
    """Whitespace cleanup must not turn a false banner into the exact pin."""
    command = [str(tmp_path / "pytest"), "--version"]

    def fake_run(
        argv: list[str], **kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        assert argv == command
        assert kwargs["cwd"] == python_validation.ROOT
        return subprocess.CompletedProcess(argv, 0, banner, "")

    monkeypatch.setattr(subprocess, "run", fake_run)
    pv = python_validation
    with pytest.raises(pv.ProvisionError, match="stdout"):
        _ = pv._run(command)  # ruff: ignore[private-member-access]  # pyright: ignore[reportPrivateUsage]


@pytest.mark.parametrize(
    "banner", ["pytest 9.1.1", "pytest 9.1.1\n", "pytest 9.1.1\r\n"]
)
def test_python_version_probe_accepts_single_native_line_ending(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    banner: str,
) -> None:
    """A single terminal LF or CRLF is transport, not version metadata."""
    expected = "pytest 9.1.1"
    command = [str(tmp_path / "pytest"), "--version"]

    def fake_run(
        argv: list[str], **kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        assert argv == command
        assert kwargs["cwd"] == python_validation.ROOT
        return subprocess.CompletedProcess(argv, 0, banner, "")

    monkeypatch.setattr(subprocess, "run", fake_run)
    pv = python_validation
    output = pv._run(command)  # ruff: ignore[private-member-access]  # pyright: ignore[reportPrivateUsage]
    assert output == expected


def test_python_command_error_does_not_read_foreign_metaclass_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The subprocess failure boundary must not invoke a class-name hook."""
    class_name_attribute = "__name__"

    class HostileMeta(type):
        def __getattribute__(cls, key: str) -> object:
            if key == class_name_attribute:
                raise AssertionError
            return super().__getattribute__(key)

    class HostileCommandError(OSError, metaclass=HostileMeta):
        pass

    fault = HostileCommandError(object())

    def fake_run(argv: list[str], **kwargs: object) -> None:
        assert argv == ["tool", "--version"]
        assert kwargs["cwd"] == python_validation.ROOT
        raise fault

    monkeypatch.setattr(subprocess, "run", fake_run)
    pv = python_validation
    with pytest.raises(pv.ProvisionError, match="HostileCommandError"):
        _ = pv._run(["tool", "--version"])  # ruff: ignore[private-member-access]  # pyright: ignore[reportPrivateUsage]
