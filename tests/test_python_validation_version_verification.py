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
