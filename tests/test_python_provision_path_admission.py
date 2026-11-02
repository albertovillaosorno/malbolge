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
#   - Regression tests for physical Python venv provisioning admission.
# - Must-Not:
#   - Download tools, run uv pip, or build real Python environments.
# - Allows:
#   - Inputs: synthetic venv files and redirected path fixtures.
#   - Outputs: fail-closed preflight evidence and native success receipts.
#   - Side effects: pytest-owned temporary paths only.
# - Split-When:
#   - Interpreter creation needs a distinct independent lifecycle.
# - Merge-When:
#   - Another suite owns this exact venv path admission boundary.
# - Summary:
#   - Never sync packages to a redirected or multiply linked interpreter.
#

"""Python venv path-admission checks before pinned uv invokes pip sync."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Never

import pytest
from scripts.bootstrap import python_validation

PAYLOAD = b"external-native-python"


def _prepare_provision_stub(
    monkeypatch: pytest.MonkeyPatch, root: Path
) -> list[list[str]]:
    commands: list[list[str]] = []

    def fake_uv(requested_root: Path) -> Path:
        assert requested_root == root
        return root / "uv"

    def block_command(command: list[str]) -> Never:
        commands.append(command)
        raise AssertionError("uv pip reached unadmitted Python environment")

    monkeypatch.setattr(python_validation, "ensure_uv", fake_uv)
    monkeypatch.setattr(python_validation, "_run", block_command)
    return commands


@pytest.mark.parametrize("link", ["interpreter", "environment", "ancestor"])
def test_python_provision_rejects_redirected_environment_before_pip(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    link: str,
) -> None:
    """Neither Python nor any of its parents may redirect uv pip sync."""
    root = tmp_path / "checkout"
    root.mkdir()
    layout = python_validation.validation_layout(root)
    outside = tmp_path / "foreign"
    if link == "interpreter":
        _ = outside.write_bytes(PAYLOAD)
        layout.scripts.mkdir(parents=True)
        redirected = layout.python
        target = outside
    elif link == "environment":
        (outside / "bin").mkdir(parents=True)
        _ = (outside / "bin" / "python").write_bytes(PAYLOAD)
        layout.environment.parent.mkdir(parents=True)
        redirected = layout.environment
        target = outside
    else:
        (outside / "3.14.7" / "bin").mkdir(parents=True)
        _ = (outside / "3.14.7" / "bin" / "python").write_bytes(PAYLOAD)
        layout.environment.parent.parent.mkdir(parents=True)
        redirected = layout.environment.parent
        target = outside
    try:
        _ = redirected.symlink_to(target, target_is_directory=link != "interpreter")
    except (OSError, NotImplementedError) as error:
        pytest.skip(f"symlink creation unsupported: {error}")
    commands = _prepare_provision_stub(monkeypatch, root)
    with pytest.raises(python_validation.ProvisionError, match="redirect"):
        python_validation._provision(layout, root=root)
    assert commands == []
    assert (target / "bin" / "python" if link == "environment" else (
        target / "3.14.7" / "bin" / "python" if link == "ancestor" else target
    )).read_bytes() == PAYLOAD
    assert redirected.is_symlink()


def test_python_provision_rejects_external_hardlinked_interpreter(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Syncing into a shared inode must not mutate a foreign interpreter."""
    root = tmp_path / "checkout"
    root.mkdir()
    layout = python_validation.validation_layout(root)
    layout.scripts.mkdir(parents=True)
    outside = tmp_path / "outside-python"
    _ = outside.write_bytes(PAYLOAD)
    try:
        os.link(outside, layout.python)
    except OSError as error:
        pytest.skip(f"hardlinks unavailable: {error}")
    commands = _prepare_provision_stub(monkeypatch, root)
    with pytest.raises(python_validation.ProvisionError, match="single-link"):
        python_validation._provision(layout, root=root)
    assert commands == []
    assert outside.read_bytes() == PAYLOAD
    assert layout.python.read_bytes() == PAYLOAD


def test_python_provision_accepts_single_link_physical_interpreter(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An already-installed local native Python proceeds to pip sync."""
    root = tmp_path / "checkout"
    root.mkdir()
    layout = python_validation.validation_layout(root)
    layout.scripts.mkdir(parents=True)
    _ = layout.python.write_bytes(PAYLOAD)
    commands = _prepare_provision_stub(monkeypatch, root)
    with pytest.raises(AssertionError, match="uv pip reached unadmitted"):
        python_validation._provision(layout, root=root)
    assert len(commands) == 1
    assert commands[0][0] == str(root / "uv")
    assert commands[0][1:3] == ["pip", "sync"]


def test_python_provision_rejects_nondirectory_venv_before_pip(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An occupied venv pathname cannot be interpreted as a directory."""
    root = tmp_path / "checkout"
    root.mkdir()
    layout = python_validation.validation_layout(root)
    layout.environment.parent.mkdir(parents=True)
    _ = layout.environment.write_bytes(PAYLOAD)
    commands = _prepare_provision_stub(monkeypatch, root)
    with pytest.raises(python_validation.ProvisionError, match="physical regular"):
        python_validation._provision(layout, root=root)
    assert commands == []
    assert layout.environment.read_bytes() == PAYLOAD


def test_python_provision_accepts_missing_venv_before_creation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Physical admission must preserve first-time environment creation."""
    root = tmp_path / "checkout"
    root.mkdir()
    layout = python_validation.validation_layout(root)
    commands = _prepare_provision_stub(monkeypatch, root)
    created: list[Path] = []

    class FakeBuilder:
        def __init__(self, *, with_pip: bool, clear: bool) -> None:
            assert not with_pip
            assert not clear

        def create(self, environment: Path) -> None:
            created.append(environment)
            environment.mkdir(parents=True)

    monkeypatch.setattr(python_validation.venv, "EnvBuilder", FakeBuilder)
    with pytest.raises(AssertionError, match="uv pip reached unadmitted"):
        python_validation._provision(layout, root=root)
    assert created == [layout.environment]
    assert len(commands) == 1
    assert commands[0][1:3] == ["pip", "sync"]
