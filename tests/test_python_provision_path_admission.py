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
import venv
from dataclasses import replace
from pathlib import Path
from typing import Never

import pytest
from scripts.bootstrap import python_validation

PAYLOAD = b"external-native-python"


def _local_uv(root: Path) -> Path:
    """Return one deterministic checkout-local fake uv executable."""
    return root / "uv"


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


def test_python_validation_layout_anchors_relative_checkout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Validation paths stay bound to their checkout after cwd changes."""
    monkeypatch.chdir(tmp_path)
    layout = python_validation.validation_layout(Path("checkout"))
    assert layout == python_validation.validation_layout(tmp_path / "checkout")
    assert layout.environment.is_absolute()


def test_python_provision_anchors_uv_and_pip_after_cwd_change(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The uv callback must not relocate subsequent pip target paths."""
    checkout = tmp_path / "checkout"
    checkout.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    monkeypatch.chdir(tmp_path)
    layout = python_validation.validation_layout(Path("checkout"))
    layout.scripts.mkdir(parents=True)
    _ = layout.python.write_bytes(PAYLOAD)
    invoked_roots: list[Path] = []
    commands: list[list[str]] = []

    def change_during_uv(root: Path) -> Path:
        invoked_roots.append(root)
        monkeypatch.chdir(outside)
        return checkout / "uv"

    def collect(command: list[str]) -> str:
        commands.append(command)
        return ""

    def no_launchers(
        _layout: python_validation.ValidationEnvironmentLayout,
        *,
        windows: bool,
    ) -> None:
        _ = windows

    def no_aliases(
        _layout: python_validation.ValidationEnvironmentLayout,
        *,
        windows: bool,
    ) -> tuple[tuple[str, Path], ...]:
        _ = windows
        return ()

    monkeypatch.setattr(python_validation, "ensure_uv", change_during_uv)
    monkeypatch.setattr(python_validation, "_run", collect)
    monkeypatch.setattr(python_validation, "write_launchers", no_launchers)
    monkeypatch.setattr(python_validation, "write_jig_tool_aliases", no_aliases)
    python_validation._provision(layout, root=Path("checkout"))  # pyright: ignore[reportPrivateUsage]
    assert invoked_roots == [checkout]
    assert len(commands) == 2
    assert all(command[0] == str(checkout / "uv") for command in commands)
    assert all(str(layout.python) in command for command in commands)
    assert not (outside / "checkout").exists()


def test_python_initialize_keeps_relative_checkout_identity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An intervening provisioning callback cannot move the validation root."""
    checkout = tmp_path / "checkout"
    checkout.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    provisioned: list[Path] = []
    verified: list[Path] = []

    def change_during_provision(
        layout: python_validation.ValidationEnvironmentLayout,
        *,
        root: Path,
    ) -> None:
        provisioned.append(root)
        assert layout.environment.is_absolute()
        monkeypatch.chdir(outside)

    def verify(layout: python_validation.ValidationEnvironmentLayout) -> None:
        verified.append(layout.environment)

    monkeypatch.setattr(python_validation, "_check_host_python", lambda: None)
    monkeypatch.setattr(python_validation, "_provision", change_during_provision)
    monkeypatch.setattr(python_validation, "_verify", verify)
    monkeypatch.chdir(tmp_path)
    result = python_validation.initialize(Path("checkout"))
    assert provisioned == [checkout]
    assert result == python_validation.validation_layout(checkout)
    assert verified == [result.environment]


@pytest.mark.parametrize(
    "mutation",
    ["linked_interpreter", "hardlinked_interpreter", "new_interpreter", "linked_bin"],
)
def test_python_provision_rechecks_interpreter_after_uv_callback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mutation: str
) -> None:
    """A uv callback cannot redirect pip to a new or externally owned Python."""
    root = tmp_path / "checkout"
    root.mkdir()
    layout = python_validation.validation_layout(root)
    layout.scripts.mkdir(parents=True)
    _ = layout.python.write_bytes(PAYLOAD)
    foreign = tmp_path / "outside"
    foreign.mkdir()
    external_python = foreign / "python"
    _ = external_python.write_bytes(PAYLOAD)
    original = tmp_path / "original-python"
    pip_commands: list[list[str]] = []

    def mutate_during_uv(requested_root: Path) -> Path:
        assert requested_root == root
        if mutation == "linked_bin":
            _ = layout.scripts.rename(tmp_path / "old-bin")
            _ = layout.scripts.symlink_to(foreign, target_is_directory=True)
        else:
            _ = layout.python.rename(original)
            if mutation == "linked_interpreter":
                _ = layout.python.symlink_to(external_python)
            elif mutation == "hardlinked_interpreter":
                os.link(external_python, layout.python)
            else:
                _ = layout.python.write_bytes(PAYLOAD)
        return root / "uv"

    def reject_pip(command: list[str]) -> Never:
        pip_commands.append(command)
        raise AssertionError("uv pip reached changed interpreter")

    monkeypatch.setattr(python_validation, "ensure_uv", mutate_during_uv)
    monkeypatch.setattr(python_validation, "_run", reject_pip)
    with pytest.raises(python_validation.ProvisionError, match="interpreter|redirect"):
        python_validation._provision(layout, root=root)  # pyright: ignore[reportPrivateUsage]
    assert pip_commands == []
    assert external_python.read_bytes() == PAYLOAD


@pytest.mark.parametrize("mutation", ["symlink", "hardlink", "replacement"])
def test_python_provision_rechecks_interpreter_between_pip_commands(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mutation: str
) -> None:
    """A pip sync callback cannot redirect the subsequent uninstall target."""
    root = tmp_path / "checkout"
    root.mkdir()
    layout = python_validation.validation_layout(root)
    layout.scripts.mkdir(parents=True)
    _ = layout.python.write_bytes(PAYLOAD)
    outside = tmp_path / "outside-python"
    _ = outside.write_bytes(PAYLOAD)
    pip_commands: list[list[str]] = []

    def sync_then_substitute(command: list[str]) -> str:
        pip_commands.append(command)
        if len(pip_commands) > 1:
            raise AssertionError("uv uninstall reached changed Python")
        _ = layout.python.unlink()
        if mutation == "symlink":
            _ = layout.python.symlink_to(outside)
        elif mutation == "hardlink":
            os.link(outside, layout.python)
        else:
            _ = layout.python.write_bytes(PAYLOAD)
        return ""

    monkeypatch.setattr(python_validation, "ensure_uv", _local_uv)
    monkeypatch.setattr(python_validation, "_run", sync_then_substitute)
    with pytest.raises(python_validation.ProvisionError, match="interpreter|redirect"):
        python_validation._provision(layout, root=root)  # pyright: ignore[reportPrivateUsage]
    assert len(pip_commands) == 1
    assert pip_commands[0][1:3] == ["pip", "sync"]
    assert outside.read_bytes() == PAYLOAD


def test_python_provision_rejects_builder_introduced_link_before_pip(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A venv builder cannot supply a redirected Python to the pip runner."""
    root = tmp_path / "checkout"
    root.mkdir()
    layout = python_validation.validation_layout(root)
    foreign = tmp_path / "foreign-python"
    _ = foreign.write_bytes(PAYLOAD)
    reached_pip = False

    class LinkedBuilder:
        def __init__(self, *, with_pip: bool, clear: bool) -> None:
            assert not with_pip and not clear

        def create(self, environment: Path) -> None:
            assert environment == layout.environment
            layout.scripts.mkdir(parents=True)
            _ = layout.python.symlink_to(foreign)

    def forbidden_pip(_command: list[str]) -> Never:
        nonlocal reached_pip
        reached_pip = True
        raise AssertionError("redirected builder Python reached pip")

    monkeypatch.setattr(python_validation, "ensure_uv", _local_uv)
    monkeypatch.setattr(venv, "EnvBuilder", LinkedBuilder)
    monkeypatch.setattr(python_validation, "_run", forbidden_pip)
    with pytest.raises(python_validation.ProvisionError, match="redirect"):
        python_validation._provision(layout, root=root)  # pyright: ignore[reportPrivateUsage]
    assert not reached_pip
    assert foreign.read_bytes() == PAYLOAD


def test_python_provision_rechecks_after_pip_uninstall_before_launchers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Uninstall cannot hand a substituted interpreter to launchers."""
    root = tmp_path / "checkout"
    root.mkdir()
    layout = python_validation.validation_layout(root)
    layout.scripts.mkdir(parents=True)
    _ = layout.python.write_bytes(PAYLOAD)
    foreign = tmp_path / "foreign-python"
    _ = foreign.write_bytes(PAYLOAD)
    commands: list[list[str]] = []
    launched = False

    def change_after_uninstall(command: list[str]) -> str:
        commands.append(command)
        if command[1:3] == ["pip", "uninstall"]:
            _ = layout.python.unlink()
            _ = layout.python.symlink_to(foreign)
        return ""

    def forbidden_launchers(
        _layout: python_validation.ValidationEnvironmentLayout,
        *,
        windows: bool,
    ) -> None:
        nonlocal launched
        _ = windows
        launched = True
        raise AssertionError("uninstall mutation reached launcher publication")

    monkeypatch.setattr(python_validation, "ensure_uv", _local_uv)
    monkeypatch.setattr(python_validation, "_run", change_after_uninstall)
    monkeypatch.setattr(python_validation, "write_launchers", forbidden_launchers)
    with pytest.raises(python_validation.ProvisionError, match="redirect"):
        python_validation._provision(layout, root=root)  # pyright: ignore[reportPrivateUsage]
    assert [command[1:3] for command in commands] == [
        ["pip", "sync"], ["pip", "uninstall"]
    ]
    assert not launched
    assert foreign.read_bytes() == PAYLOAD


@pytest.mark.parametrize("stage", ["launchers", "aliases"])
def test_python_provision_rechecks_interpreter_after_publication_callbacks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, stage: str
) -> None:
    """No publishing callback can leave a redirected Python as ready."""
    root = tmp_path / "checkout"
    root.mkdir()
    layout = python_validation.validation_layout(root)
    layout.scripts.mkdir(parents=True)
    _ = layout.python.write_bytes(PAYLOAD)
    outside = tmp_path / "outside-python"
    _ = outside.write_bytes(PAYLOAD)
    invocations: list[str] = []

    def swap_interpreter() -> None:
        _ = layout.python.unlink()
        _ = layout.python.symlink_to(outside)

    def write_launchers(
        _layout: python_validation.ValidationEnvironmentLayout,
        *,
        windows: bool,
    ) -> None:
        _ = windows
        invocations.append("launchers")
        if stage == "launchers":
            swap_interpreter()

    def write_aliases(
        _layout: python_validation.ValidationEnvironmentLayout,
        *,
        windows: bool,
    ) -> tuple[tuple[str, Path], ...]:
        _ = windows
        invocations.append("aliases")
        if stage == "launchers":
            raise AssertionError("aliases reached substituted Python")
        swap_interpreter()
        return ()

    def fake_command(_command: list[str]) -> str:
        return ""

    monkeypatch.setattr(python_validation, "ensure_uv", _local_uv)
    monkeypatch.setattr(python_validation, "_run", fake_command)
    monkeypatch.setattr(python_validation, "write_launchers", write_launchers)
    monkeypatch.setattr(python_validation, "write_jig_tool_aliases", write_aliases)
    with pytest.raises(python_validation.ProvisionError, match="redirect"):
        python_validation._provision(  # pyright: ignore[reportPrivateUsage]
            layout, root=root
        )
    expected = ["launchers"] if stage == "launchers" else ["launchers", "aliases"]
    assert invocations == expected
    assert outside.read_bytes() == PAYLOAD


def test_python_provision_rejects_late_installed_interpreter_before_builder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When no Python exists at preflight, uv cannot insert one before venv."""
    root = tmp_path / "checkout"
    root.mkdir()
    layout = python_validation.validation_layout(root)
    foreign = tmp_path / "outside-python"
    _ = foreign.write_bytes(PAYLOAD)
    builder_created = False

    def late_link(requested_root: Path) -> Path:
        assert requested_root == root
        layout.scripts.mkdir(parents=True)
        _ = layout.python.symlink_to(foreign)
        return root / "uv"

    class ForbiddenBuilder:
        def __init__(self, *, with_pip: bool, clear: bool) -> None:
            _ = (with_pip, clear)

        def create(self, _environment: Path) -> None:
            nonlocal builder_created
            builder_created = True
            raise AssertionError("venv builder reached late interpreter")

    monkeypatch.setattr(python_validation, "ensure_uv", late_link)
    monkeypatch.setattr(venv, "EnvBuilder", ForbiddenBuilder)
    with pytest.raises(python_validation.ProvisionError, match="interpreter|redirect"):
        python_validation._provision(layout, root=root)  # pyright: ignore[reportPrivateUsage]
    assert not builder_created
    assert foreign.read_bytes() == PAYLOAD


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
    assert (
        target / "bin" / "python"
        if link == "environment"
        else (target / "3.14.7" / "bin" / "python" if link == "ancestor" else target)
    ).read_bytes() == PAYLOAD
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
            layout.scripts.mkdir(parents=True)
            _ = layout.python.write_bytes(PAYLOAD)

    monkeypatch.setattr(venv, "EnvBuilder", FakeBuilder)
    with pytest.raises(AssertionError, match="uv pip reached unadmitted"):
        python_validation._provision(layout, root=root)
    assert created == [layout.environment]
    assert len(commands) == 1
    assert commands[0][1:3] == ["pip", "sync"]


def test_python_provision_rejects_builder_missing_interpreter_before_pip(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A successful builder return without Python cannot authorize uv pip."""
    root = tmp_path / "checkout"
    root.mkdir()
    layout = python_validation.validation_layout(root)
    commands = _prepare_provision_stub(monkeypatch, root)
    created: list[Path] = []

    class IncompleteBuilder:
        def __init__(self, *, with_pip: bool, clear: bool) -> None:
            assert not with_pip and not clear

        def create(self, environment: Path) -> None:
            created.append(environment)
            layout.scripts.mkdir(parents=True)

    monkeypatch.setattr(venv, "EnvBuilder", IncompleteBuilder)
    with pytest.raises(python_validation.ProvisionError, match="interpreter|missing"):
        python_validation._provision(layout, root=root)  # pyright: ignore[reportPrivateUsage]
    assert created == [layout.environment]
    assert not commands
    assert not layout.python.exists()


@pytest.mark.parametrize(
    "mutation", ["other_checkout", "other_authority", "other_launcher"]
)
def test_python_provision_rejects_layout_from_other_checkout_or_authority(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mutation: str
) -> None:
    """The selected uv checkout must bind the entire interpreter/tool layout."""
    root = tmp_path / "checkout"
    root.mkdir()
    other = tmp_path / "foreign-checkout"
    other.mkdir()
    layout = python_validation.validation_layout(root)
    if mutation == "other_checkout":
        layout = python_validation.validation_layout(other)
    elif mutation == "other_authority":
        layout = replace(layout, expected_tools=(("pytest", "pytest fake"),))
    else:
        layout = replace(layout, python_launcher=other / "out-of-checkout")
    layout.scripts.mkdir(parents=True)
    _ = layout.python.write_bytes(PAYLOAD)
    commands = _prepare_provision_stub(monkeypatch, root)
    with pytest.raises(python_validation.ProvisionError, match="selected checkout"):
        python_validation._provision(layout, root=root)
    assert commands == []
    assert layout.python.read_bytes() == PAYLOAD
