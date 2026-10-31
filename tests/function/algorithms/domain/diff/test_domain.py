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
#   - The repository behavior implemented by this source file.
# - Must-Not:
#   - Bypass the contracts or authority boundaries of its owning package.
# - Allows:
#   - Inputs: values admitted by the file's public or internal interface.
#   - Outputs: deterministic values or effects declared by that interface.
#   - Side effects: only those explicitly owned by the implementation.
# - Split-When:
#   - Split when one responsibility gains an independent lifecycle.
# - Merge-When:
#   - Merge when another file owns the exact same responsibility.
# - Summary:
#   - Synthetic validation for consumer-domain module loading.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#

"""Synthetic validation for consumer-domain module loading."""

from __future__ import annotations

from dataclasses import replace
import importlib.util
import os
from pathlib import Path
import sys
from typing import TYPE_CHECKING
from typing import cast

from algorithms.diff.domain import DomainContractError
from algorithms.diff.domain import load_diff_domain
import pytest

if TYPE_CHECKING:
    from collections.abc import Callable

    from algorithms.diff.mapped import MappedView

_POSIX = "posix"
_STAGE_MODULE = "module"
_STAGE_PARENT = "parent"
_STAGE_RESOLVED = "resolved"
_COMPLETE = """def validate_source_provenance(root):
    return None


def validate_authoring_oracle(root):
    return None


def build_identity_tree(root):
    return None


def map_compatible_file(path, data):
    return None


def build_compatible_correction_bindings(plan):
    return ()


def build_behavior_programs():
    return None


def build_behavior_probe_context(source_root, repository_root):
    return None
"""


def _write(path: Path, text: str) -> None:
    _ = path.write_text(text, encoding="utf-8", newline="\n")


def _expect(condition: object, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def test_domain_loader_rejects_foreign_path_before_filesystem() -> None:
    """Require a pathlib path before module status or loading work."""
    with pytest.raises(DomainContractError, match="pathlib Path"):
        _ = load_diff_domain(cast("Path", cast("object", "domain.py")))


@pytest.mark.parametrize("name", ["domain\x00.py", "domain\ud800.py"])
def test_domain_loader_rejects_unrepresentable_module_path(name: str) -> None:
    """Malformed module names cannot leak host path/encoding exceptions."""
    with pytest.raises(DomainContractError, match=r"module path|status failed"):
        _ = load_diff_domain(Path(name))


def test_domain_module_execution_failure_uses_contract_error(
    tmp_path: Path,
) -> None:
    """Contain consumer import failures inside the domain contract boundary."""
    module = tmp_path / "domain.py"
    _write(module, 'raise RuntimeError("consumer boom")' + chr(10))

    with pytest.raises(DomainContractError, match="module execution failed"):
        _ = load_diff_domain(module)


@pytest.mark.parametrize(
    "case",
    [
        (stage, failure_type)
        for stage in ("spec_from_file_location", "module_from_spec")
        for failure_type in (OSError, ValueError, RuntimeError)
    ],
)
def test_domain_import_preparation_errors_are_typed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    case: tuple[str, type[Exception]],
) -> None:
    """Loader errors before execution must stay in the domain boundary."""
    stage, failure_type = case
    module = tmp_path / "domain.py"
    _write(module, _COMPLETE)
    before = frozenset(sys.modules)

    def blocked_import(*args: object, **kwargs: object) -> None:
        _ = args, kwargs
        message = "injected import preparation failure"
        raise failure_type(message)

    monkeypatch.setattr(importlib.util, stage, blocked_import)
    with pytest.raises(DomainContractError, match="import preparation failed"):
        _ = load_diff_domain(module)
    registered = frozenset(sys.modules) - before
    assert not any(
        name.startswith("_malbolge_diff_domain_") for name in registered
    )


def test_complete_domain_module_loads_explicit_hooks(tmp_path: Path) -> None:
    """Turn required consumer names into one validated callable bundle."""
    module = tmp_path / "domain.py"
    _write(module, _COMPLETE)

    domain = load_diff_domain(module)

    _expect(
        callable(domain.validate_source_provenance),
        "source provenance validator is not callable",
    )
    _expect(
        callable(domain.validate_authoring_oracle),
        "oracle validator is not callable",
    )
    _expect(
        callable(domain.build_identity_tree), "identity builder is not callable"
    )
    _expect(
        callable(domain.map_compatible_file),
        "mapped-file adapter is not callable",
    )
    _expect(
        callable(domain.build_compatible_correction_bindings),
        "correction-binding builder is not callable",
    )
    _expect(
        callable(domain.build_behavior_programs),
        "behavior builder is not callable",
    )
    _expect(
        callable(domain.build_behavior_probe_context),
        "probe-context builder is not callable",
    )


@pytest.mark.skipif(os.name != _POSIX, reason="requires raw POSIX path bytes")
def test_domain_loader_accepts_surrogateescaped_module_name(
    tmp_path: Path,
) -> None:
    """Hash real filesystem bytes rather than strict UTF-8 module names."""
    module = tmp_path / os.fsdecode(b"domain-\xff.py")
    _write(module, _COMPLETE)

    loaded = load_diff_domain(module)

    assert callable(loaded.build_identity_tree)


def test_direct_domain_bundle_rejects_foreign_hook(tmp_path: Path) -> None:
    """Do not let direct dataclass construction bypass callable admission."""
    module = tmp_path / "domain.py"
    _write(module, _COMPLETE)
    domain = load_diff_domain(module)

    with pytest.raises(DomainContractError, match="map_compatible_file"):
        _ = replace(
            domain,
            map_compatible_file=cast(
                "Callable[[str, bytes], MappedView | None]", object()
            ),
        )


def test_rejected_domain_module_is_not_left_registered(tmp_path: Path) -> None:
    """A rejected hook bundle cannot persist as an importable module."""
    module = tmp_path / "incomplete.py"
    _write(
        module,
        _COMPLETE.replace("def build_behavior_programs():", "def other():"),
    )
    before = frozenset(sys.modules)

    with pytest.raises(DomainContractError, match="build_behavior_programs"):
        _ = load_diff_domain(module)

    registered = frozenset(sys.modules) - before
    assert not any(
        name.startswith("_malbolge_diff_domain_") for name in registered
    )


def test_domain_hook_lookup_exception_uses_contract_error(
    tmp_path: Path,
) -> None:
    """A faulty module hook resolver cannot leak its own exception type."""
    module = tmp_path / "dynamic.py"
    missing = _COMPLETE.replace(
        "def build_behavior_programs():\n    return None\n\n", ""
    )
    getter = (
        "def __getattr__(name):\n"
        "    raise RuntimeError('consumer lookup failed')\n"
    )
    _write(module, missing + getter)
    before = frozenset(sys.modules)
    with pytest.raises(DomainContractError, match="hook lookup failed"):
        _ = load_diff_domain(module)
    registered = frozenset(sys.modules) - before
    assert not any(
        name.startswith("_malbolge_diff_domain_") for name in registered
    )


def test_rejected_domain_reload_preserves_previous_registration(
    tmp_path: Path,
) -> None:
    """A failed update cannot discard a previously admitted module."""
    module = tmp_path / "reload.py"
    _write(module, _COMPLETE)
    before = frozenset(sys.modules)
    _ = load_diff_domain(module)
    names = frozenset(sys.modules) - before
    loaded = tuple(
        name for name in names if name.startswith("_malbolge_diff_domain_")
    )
    assert len(loaded) == 1
    name = loaded[0]
    accepted_module = sys.modules[name]

    _write(
        module,
        _COMPLETE.replace("def build_behavior_programs():", "def other():"),
    )
    with pytest.raises(DomainContractError, match="build_behavior_programs"):
        _ = load_diff_domain(module)

    assert sys.modules.get(name) is accepted_module
    _write(module, 'raise RuntimeError("rejected replacement")\n')
    with pytest.raises(DomainContractError, match="module execution failed"):
        _ = load_diff_domain(module)
    assert sys.modules.get(name) is accepted_module
    _ = sys.modules.pop(name, None)


def test_missing_required_hook_fails_closed(tmp_path: Path) -> None:
    """Reject partial consumer policy before compatible authoring."""
    module = tmp_path / "domain.py"
    _write(
        module,
        _COMPLETE.replace(
            "def map_compatible_file(path, data):\n    return None\n\n", ""
        ),
    )

    with pytest.raises(DomainContractError, match="map_compatible_file"):
        _ = load_diff_domain(module)


def test_missing_correction_binding_hook_fails_closed(tmp_path: Path) -> None:
    """Require explicit consumer ownership of conditional semantic edits."""
    module = tmp_path / "domain.py"
    newline = chr(10)
    missing_hook = (
        "def build_compatible_correction_bindings(plan):"
        + newline
        + "    return ()"
        + newline
        + newline
    )
    _write(module, _COMPLETE.replace(missing_hook, ""))

    with pytest.raises(
        DomainContractError, match="build_compatible_correction_bindings"
    ):
        _ = load_diff_domain(module)


def test_missing_or_symlinked_domain_file_fails_closed(tmp_path: Path) -> None:
    """Require a concrete regular authoring-policy module."""
    missing = tmp_path / "missing.py"
    with pytest.raises(DomainContractError, match="regular file"):
        _ = load_diff_domain(missing)

    target = tmp_path / "target.py"
    _write(target, _COMPLETE)
    link = tmp_path / "link.py"
    try:
        link.symlink_to(target)
    except OSError:
        pytest.skip("symlink creation is unavailable")
    with pytest.raises(DomainContractError, match="regular file"):
        _ = load_diff_domain(link)


def test_domain_loader_rejects_linked_parent_directory(
    tmp_path: Path,
) -> None:
    """Trusted local consumer policy cannot load through directory links."""
    module = tmp_path / "real" / "domain.py"
    module.parent.mkdir()
    _write(module, _COMPLETE)
    alias = tmp_path / "alias"
    try:
        alias.symlink_to(module.parent, target_is_directory=True)
    except OSError:
        pytest.skip("directory symlinks unavailable")

    with pytest.raises(DomainContractError, match="linked parent"):
        _ = load_diff_domain(alias / "domain.py")


def test_domain_module_parent_status_error_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Do not ignore inaccessible ancestors of a trusted consumer module."""
    module = tmp_path / "policy" / "domain.py"
    module.parent.mkdir()
    _write(module, _COMPLETE)
    original_lstat = Path.lstat

    def fail_parent_status(path: Path) -> object:
        if path == module.parent:
            message = "blocked consumer directory"
            raise PermissionError(message)
        return original_lstat(path)

    monkeypatch.setattr(Path, "lstat", fail_parent_status)
    with pytest.raises(DomainContractError, match="parent status failed"):
        _ = load_diff_domain(module)


def test_domain_file_status_error_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Preserve an inaccessible module as a status failure, not absence."""
    module = tmp_path / "domain.py"
    _write(module, _COMPLETE)
    original_lstat = Path.lstat

    def fail_lstat(path: Path) -> object:
        if path == module:
            message = "blocked domain module"
            raise PermissionError(message)
        return original_lstat(path)

    monkeypatch.setattr(Path, "lstat", fail_lstat)
    with pytest.raises(DomainContractError, match="status failed"):
        _ = load_diff_domain(module)


@pytest.mark.parametrize(
    "case",
    [
        (stage, failure_type)
        for stage in (_STAGE_MODULE, _STAGE_PARENT, _STAGE_RESOLVED)
        for failure_type in (ValueError, RuntimeError)
    ],
)
def test_domain_module_metadata_failures_are_typed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    case: tuple[str, type[Exception]],
) -> None:
    """Malformed host metadata fails before trusted consumer code executes."""
    stage, failure_type = case
    module = tmp_path / "domain.py"
    _write(module, _COMPLETE)
    original_lstat = Path.lstat
    original_resolve = Path.resolve
    blocked_path = {
        _STAGE_MODULE: module,
        _STAGE_PARENT: module.parent,
    }.get(stage)

    def blocked_lstat(path: Path) -> os.stat_result:
        if path == blocked_path:
            message = "injected metadata exception"
            raise failure_type(message)
        return original_lstat(path)

    def blocked_resolve(path: Path, *, strict: bool = False) -> Path:
        if stage == _STAGE_RESOLVED and path == module and strict:
            message = "injected resolution exception"
            raise failure_type(message)
        return original_resolve(path, strict=strict)

    monkeypatch.setattr(Path, "lstat", blocked_lstat)
    monkeypatch.setattr(Path, "resolve", blocked_resolve)
    with pytest.raises(
        DomainContractError, match=r"status failed|resolution failed"
    ):
        _ = load_diff_domain(module)


@pytest.mark.parametrize(
    "case",
    [
        (stage, failure_type)
        for stage in (_STAGE_MODULE, _STAGE_PARENT)
        for failure_type in (ValueError, RuntimeError)
    ],
)
def test_domain_junction_status_failures_are_typed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    case: tuple[str, type[Exception]],
) -> None:
    """Junction inspection cannot leak host metadata failures."""
    stage, failure_type = case
    module = tmp_path / "domain.py"
    _write(module, _COMPLETE)
    target = module if stage == _STAGE_MODULE else module.parent
    original_is_junction = Path.is_junction

    def blocked_is_junction(path: Path) -> bool:
        if path == target:
            message = "host junction check unavailable"
            raise failure_type(message)
        return original_is_junction(path)

    monkeypatch.setattr(Path, "is_junction", blocked_is_junction)
    with pytest.raises(DomainContractError, match="junction status failed"):
        _ = load_diff_domain(module)


def test_domain_file_resolution_error_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Preserve a post-admission resolution race as a domain error."""
    module = tmp_path / "domain.py"
    _write(module, _COMPLETE)
    original_resolve = Path.resolve

    def fail_resolve(path: Path, *, strict: bool = False) -> Path:
        if path == module and strict:
            message = "domain module disappeared"
            raise FileNotFoundError(message)
        return original_resolve(path, strict=strict)

    monkeypatch.setattr(Path, "resolve", fail_resolve)
    with pytest.raises(DomainContractError, match="resolution failed"):
        _ = load_diff_domain(module)
