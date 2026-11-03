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
import hashlib
import importlib.machinery
import importlib.util
import os
from pathlib import Path
import sys
from types import SimpleNamespace
from typing import TYPE_CHECKING
from typing import cast
from typing import override

from algorithms.diff import domain as domain_module
from algorithms.diff.domain import DomainContractError
from algorithms.diff.domain import load_diff_domain
import pytest

if TYPE_CHECKING:
    from collections.abc import Callable
    from types import ModuleType

    from algorithms.diff.mapped import MappedView

_HOSTILE_EXCEPTION_SOURCE = (
    "class HostileError(RuntimeError):\n"
    "    def __str__(self):\n"
    "        raise AssertionError('untrusted str hook ran')\n"
)


class _HostileMetadataError(OSError):
    """A synthetic host error with unsafe diagnostic hooks."""

    @override
    def __repr__(self) -> str:
        message = "untrusted repr hook ran"
        raise AssertionError(message)


_HOSTILE_EXCEPTION_NAME = "HostileError"
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


class _ForeignDomainModulePath(type(Path())):
    """A module path override cannot establish domain execution authority."""

    @override
    def __str__(self) -> str:
        message = "foreign domain module path conversion executed"
        raise AssertionError(message)


def test_domain_loader_rejects_foreign_path_subclass_before_methods() -> None:
    """Reject module overrides before module status or import registration."""
    with pytest.raises(
        DomainContractError, match="must use exact pathlib Path"
    ):
        _ = load_diff_domain(_ForeignDomainModulePath("unsafe-domain.py"))


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


def test_domain_execution_does_not_format_foreign_exception(
    tmp_path: Path,
) -> None:
    """Import failure must preserve its typed boundary and undo registration."""
    module = tmp_path / "hostile_exec.py"
    source = _HOSTILE_EXCEPTION_SOURCE + "raise HostileError('bad import')\n"
    _write(module, source)
    previous = frozenset(sys.modules)

    with pytest.raises(
        DomainContractError, match="module execution failed"
    ) as caught:
        _ = load_diff_domain(module)
    assert type(caught.value.__cause__).__name__ == _HOSTILE_EXCEPTION_NAME
    registered = frozenset(sys.modules) - previous
    assert not any(
        name.startswith("_malbolge_diff_domain_") for name in registered
    )


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


def test_domain_hook_lookup_does_not_format_foreign_exception(
    tmp_path: Path,
) -> None:
    """A hostile consumer hook fault cannot run exception string methods."""
    module = tmp_path / "hostile_hook.py"
    missing = _COMPLETE.replace(
        "def build_behavior_programs():\n    return None\n\n", ""
    )
    getter = (
        "def __getattr__(name):\n"
        "    raise HostileError('bad consumer lookup')\n"
    )
    _write(module, missing + _HOSTILE_EXCEPTION_SOURCE + getter)
    previous = frozenset(sys.modules)

    with pytest.raises(
        DomainContractError, match="hook lookup failed"
    ) as caught:
        _ = load_diff_domain(module)
    assert type(caught.value.__cause__).__name__ == _HOSTILE_EXCEPTION_NAME
    registered = frozenset(sys.modules) - previous
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


@pytest.mark.parametrize("linked_role", [_STAGE_MODULE, _STAGE_PARENT])
def test_domain_loader_rejects_symlink_under_post_import_status_spoof(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, linked_role: str
) -> None:
    """A substituted native status cannot authorize executable linked policy."""
    real_parent = tmp_path / "real"
    real_parent.mkdir()
    real_module = real_parent / "domain.py"
    _write(real_module, _COMPLETE)
    alias = tmp_path / "alias"
    linked = alias if linked_role == _STAGE_MODULE else alias / "domain.py"
    target = real_module if linked_role == _STAGE_MODULE else real_parent
    alias.symlink_to(target, target_is_directory=linked_role != _STAGE_MODULE)
    native_lstat = Path.lstat
    native_status = target.stat()
    forged_calls = 0

    def forged_lstat(path: Path) -> os.stat_result:
        nonlocal forged_calls
        if path == alias:
            forged_calls += 1
            return native_status
        return native_lstat(path)

    with monkeypatch.context() as patched:
        patched.setattr(Path, "lstat", forged_lstat)
        with pytest.raises(
            DomainContractError, match=r"regular file|linked parent"
        ):
            _ = load_diff_domain(linked)
    assert forged_calls == 0


@pytest.mark.parametrize("linked_role", [_STAGE_MODULE, _STAGE_PARENT])
def test_domain_loader_rejects_symlink_under_post_import_os_lstat_spoof(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, linked_role: str
) -> None:
    """A replaced OS syscall cannot certify a linked local policy module."""
    real_parent = tmp_path / "real"
    real_parent.mkdir()
    real_module = real_parent / "domain.py"
    _write(real_module, _COMPLETE)
    alias = tmp_path / "alias"
    linked = alias if linked_role == _STAGE_MODULE else alias / "domain.py"
    target = real_module if linked_role == _STAGE_MODULE else real_parent
    alias.symlink_to(target, target_is_directory=linked_role != _STAGE_MODULE)
    native_status = target.stat()
    native_lstat = os.lstat
    forged_calls = 0

    def forged_lstat(
        path: Path | str | bytes, *args: object, **kwargs: object
    ) -> os.stat_result:
        nonlocal forged_calls
        if path == alias:
            forged_calls += 1
            return native_status
        return native_lstat(path, *args, **kwargs)

    with monkeypatch.context() as patched:
        patched.setattr(os, "lstat", forged_lstat)
        with pytest.raises(
            DomainContractError, match=r"regular file|linked parent"
        ):
            _ = load_diff_domain(linked)
    assert forged_calls == 0


@pytest.mark.parametrize("linked_role", [_STAGE_MODULE, _STAGE_PARENT])
def test_domain_loader_rejects_linked_input_after_fspath_status_spoof(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, linked_role: str
) -> None:
    """Late native-path conversion must not certify an executable symlink."""
    real_parent = tmp_path / "real"
    real_parent.mkdir()
    real_module = real_parent / "domain.py"
    _write(real_module, _COMPLETE)
    alias = tmp_path / "alias"
    linked = alias if linked_role == _STAGE_MODULE else alias / "domain.py"
    target = real_module if linked_role == _STAGE_MODULE else real_parent
    try:
        alias.symlink_to(target, target_is_directory=linked_role != _STAGE_MODULE)
    except OSError:
        pytest.skip("symlinks unavailable")
    native_fspath = Path.__fspath__
    forged_calls = 0

    def forged_fspath(path: Path) -> str:
        nonlocal forged_calls
        if path == alias:
            forged_calls += 1
            if forged_calls == 1:
                return native_fspath(target)
        return native_fspath(path)

    with monkeypatch.context() as patched:
        patched.setattr(Path, "__fspath__", forged_fspath)
        with pytest.raises(
            DomainContractError, match=r"regular file|linked parent"
        ):
            _ = load_diff_domain(linked)
    assert forged_calls == 0


def test_domain_loader_ignores_post_import_fspath_import_redirection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A validated module cannot be replaced at import via Path conversion."""
    admitted = tmp_path / "admitted.py"
    redirected = tmp_path / "redirected.py"
    _write(admitted, _COMPLETE.replace("return None", "return 'admitted'"))
    _write(redirected, _COMPLETE.replace("return None", "return 'redirected'"))
    native_fspath = Path.__fspath__
    forged_calls = 0

    def forged_fspath(path: Path) -> str:
        nonlocal forged_calls
        if path == admitted:
            forged_calls += 1
            return native_fspath(redirected)
        return native_fspath(path)

    with monkeypatch.context() as patched:
        patched.setattr(Path, "__fspath__", forged_fspath)
        domain = load_diff_domain(admitted)
    assert forged_calls == 0
    assert domain.build_behavior_programs() == "admitted"


def test_domain_loader_rejects_link_after_late_str_status_spoof(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A late Path.__str__ hook cannot certify a linked input as regular."""
    regular = tmp_path / "regular.py"
    _write(regular, _COMPLETE)
    linked = tmp_path / "linked.py"
    try:
        linked.symlink_to(regular)
    except OSError:
        pytest.skip("symlinks unavailable")
    native_string = Path.__str__
    linked_label = native_string(linked)
    forged_calls = 0

    def forged_string(path: Path) -> str:
        nonlocal forged_calls
        if native_string(path) == linked_label:
            forged_calls += 1
            return native_string(regular)
        return native_string(path)

    with monkeypatch.context() as patched:
        patched.setattr(Path, "__str__", forged_string)
        with pytest.raises(DomainContractError, match="regular file"):
            _ = load_diff_domain(linked)
    assert forged_calls == 0


def test_domain_loader_ignores_post_import_native_resolver_redirection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A mutable host resolver cannot redirect a verified local policy."""
    admitted = tmp_path / "admitted.py"
    redirected = tmp_path / "redirected.py"
    expected = "admitted"
    _write(admitted, _COMPLETE.replace("return None", f"return {expected!r}"))
    _write(redirected, _COMPLETE.replace("return None", "return 'redirected'"))
    native_resolve = Path.resolve
    calls = 0

    def forged_resolve(path: Path, *, strict: bool = False) -> Path:
        nonlocal calls
        if path == admitted and strict:
            calls += 1
            return native_resolve(redirected, strict=True)
        return native_resolve(path, strict=strict)

    with monkeypatch.context() as patched:
        patched.setattr(Path, "resolve", forged_resolve)
        domain = load_diff_domain(admitted)
    assert calls == 0
    assert domain.build_behavior_programs() == expected


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


def test_domain_loader_rejects_linked_parent_after_path_parent_spoof(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Late Path.parent must not remove linked ancestors from module admission."""
    real_parent = tmp_path / "real"
    real_parent.mkdir()
    module = real_parent / "domain.py"
    _write(module, _COMPLETE)
    alias = tmp_path / "alias"
    try:
        alias.symlink_to(real_parent, target_is_directory=True)
    except OSError:
        pytest.skip("directory symlinks unavailable")
    linked_module = alias / "domain.py"
    native_parent = Path.parent
    forged_calls = 0

    def forged_parent(path: Path) -> Path:
        nonlocal forged_calls
        if path == linked_module:
            forged_calls += 1
            return tmp_path
        return native_parent.__get__(path, type(path))

    with monkeypatch.context() as patched:
        patched.setattr(Path, "parent", property(forged_parent))
        with pytest.raises(DomainContractError, match="linked parent"):
            _ = load_diff_domain(linked_module)
    assert forged_calls == 0


def test_domain_loader_rejects_linked_parent_after_path_equality_spoof(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A late Path equality override cannot terminate the ancestor walk."""
    real_parent = tmp_path / "real"
    real_parent.mkdir()
    _write(real_parent / "domain.py", _COMPLETE)
    alias = tmp_path / "alias"
    try:
        alias.symlink_to(real_parent, target_is_directory=True)
    except OSError:
        pytest.skip("directory symlinks unavailable")
    linked_module = alias / "domain.py"

    def forged_equal(_: object, __: object) -> bool:
        return True

    with monkeypatch.context() as patched:
        patched.setattr(Path, "__eq__", forged_equal)
        with pytest.raises(DomainContractError, match="linked parent"):
            _ = load_diff_domain(linked_module)


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

    monkeypatch.setattr(domain_module, "_NATIVE_PATH_LSTAT", fail_parent_status)
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

    monkeypatch.setattr(domain_module, "_NATIVE_PATH_LSTAT", fail_lstat)
    with pytest.raises(DomainContractError, match="status failed"):
        _ = load_diff_domain(module)


@pytest.mark.parametrize("stage", [_STAGE_MODULE, _STAGE_PARENT])
def test_domain_rejects_foreign_status_before_module_execution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    stage: str,
) -> None:
    """Only native status receipts may authorize a consumer module import."""
    module = tmp_path / "domain.py"
    _write(module, _COMPLETE)
    target = module if stage == _STAGE_MODULE else module.parent
    original_lstat = Path.lstat
    native = original_lstat(target)
    foreign = SimpleNamespace(st_mode=native.st_mode)
    previous = frozenset(sys.modules)

    def foreign_lstat(path: Path) -> os.stat_result:
        if path == target:
            return cast("os.stat_result", cast("object", foreign))
        return original_lstat(path)

    monkeypatch.setattr(domain_module, "_NATIVE_PATH_LSTAT", foreign_lstat)
    with pytest.raises(DomainContractError, match="native filesystem status"):
        _ = load_diff_domain(module)
    registered = frozenset(sys.modules) - previous
    assert not any(
        name.startswith("_malbolge_diff_domain_") for name in registered
    )


@pytest.mark.parametrize("stage", [_STAGE_MODULE, _STAGE_RESOLVED])
def test_domain_metadata_fault_does_not_format_foreign_exception(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    stage: str,
) -> None:
    """Host status and resolution faults cannot escape through repr hooks."""
    module = tmp_path / "domain.py"
    _write(module, _COMPLETE)
    failure = _HostileMetadataError("untrusted host diagnostic")
    original_lstat = Path.lstat
    original_resolve = Path.resolve

    def fail_lstat(path: Path) -> os.stat_result:
        if stage == _STAGE_MODULE and path == module:
            raise failure
        return original_lstat(path)

    def fail_resolve(path: Path, *, strict: bool = False) -> Path:
        if stage == _STAGE_RESOLVED and path == module and strict:
            raise failure
        return original_resolve(path, strict=strict)

    monkeypatch.setattr(domain_module, "_NATIVE_PATH_LSTAT", fail_lstat)
    monkeypatch.setattr(domain_module, "_NATIVE_PATH_RESOLVE", fail_resolve)
    with pytest.raises(
        DomainContractError, match=r"status failed|resolution failed"
    ) as caught:
        _ = load_diff_domain(module)
    assert caught.value.__cause__ is failure


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

    monkeypatch.setattr(domain_module, "_NATIVE_PATH_LSTAT", blocked_lstat)
    monkeypatch.setattr(domain_module, "_NATIVE_PATH_RESOLVE", blocked_resolve)
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

    monkeypatch.setattr(
        domain_module, "_NATIVE_PATH_IS_JUNCTION", blocked_is_junction
    )
    with pytest.raises(DomainContractError, match="junction status failed"):
        _ = load_diff_domain(module)


@pytest.mark.parametrize("stage", [_STAGE_MODULE, _STAGE_PARENT])
def test_domain_junction_requires_exact_native_boolean(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, stage: str
) -> None:
    """Foreign false-like junction reports cannot authorize module loading."""
    module = tmp_path / "domain.py"
    _write(module, _COMPLETE)
    target = module if stage == _STAGE_MODULE else module.parent
    native_is_junction = Path.is_junction
    observed = False

    def forged_junction(path: Path) -> object:
        nonlocal observed
        if path == target:
            observed = True
            return 0
        return native_is_junction(path)

    monkeypatch.setattr(
        domain_module, "_NATIVE_PATH_IS_JUNCTION", forged_junction
    )
    with pytest.raises(DomainContractError, match="native boolean"):
        _ = load_diff_domain(module)
    _expect(observed, "foreign junction receipt was not reached")


class _ForeignResolvedDomainPath(type(Path())):
    """A synthetic resolved path must never reach import machinery."""

    @override
    def __fspath__(self) -> str:
        message = "foreign resolved domain path conversion executed"
        raise AssertionError(message)


def test_domain_resolved_path_must_be_native(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Reject a foreign resolution result before it controls imports."""
    module = tmp_path / "domain.py"
    _write(module, _COMPLETE)
    native_resolve = Path.resolve
    observed = False

    def forged_resolve(path: Path, *, strict: bool = False) -> Path:
        nonlocal observed
        if path == module and strict:
            observed = True
            return _ForeignResolvedDomainPath(path)
        return native_resolve(path, strict=strict)

    monkeypatch.setattr(domain_module, "_NATIVE_PATH_RESOLVE", forged_resolve)
    with pytest.raises(DomainContractError, match="native Path"):
        _ = load_diff_domain(module)
    _expect(observed, "foreign resolved path was not consumed")


class _ForgedModuleNamespaceDigest:
    """All module paths become one identical host-supplied digest."""

    @staticmethod
    def hexdigest() -> str:
        """Return one forged digest.

        Returns:
            A constant all-zero digest string.

        """
        return "0" * 64


def test_domain_import_names_resist_post_import_hash_swap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Different local policies cannot collide via mutable hash callbacks."""
    first = tmp_path / "first.py"
    second = tmp_path / "second.py"
    _write(first, _COMPLETE)
    _write(second, _COMPLETE)
    genuine_hash = hashlib.sha256

    def forged_hash(data: bytes = b"") -> _ForgedModuleNamespaceDigest:
        del data
        return _ForgedModuleNamespaceDigest()

    with monkeypatch.context() as patch:
        patch.setattr(hashlib, "sha256", forged_hash)
        first_domain = load_diff_domain(first)
        second_domain = load_diff_domain(second)
    first_name = first_domain.validate_authoring_oracle.__module__
    second_name = second_domain.validate_authoring_oracle.__module__
    _expect(
        first_name != second_name, "foreign digest merged module identities"
    )
    _expect(
        genuine_hash(str(first).encode()).digest()
        != genuine_hash(str(second).encode()).digest(),
        "two module paths unexpectedly shared native hash identity",
    )


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

    monkeypatch.setattr(domain_module, "_NATIVE_PATH_RESOLVE", fail_resolve)
    with pytest.raises(DomainContractError, match="resolution failed"):
        _ = load_diff_domain(module)


@pytest.mark.parametrize("receipt", [False, 1, "executed"])
def test_domain_loader_rejects_foreign_exec_completion(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, receipt: object
) -> None:
    """A loader may not attest a policy module with a forged completion."""
    module = tmp_path / "native_receipt.py"
    _write(module, _COMPLETE)
    previous_names = frozenset(sys.modules)
    native_exec = importlib.machinery.SourceFileLoader.exec_module

    def forged_exec(
        loader: importlib.machinery.SourceFileLoader, selected: ModuleType
    ) -> object:
        native_exec(loader, selected)
        return receipt

    monkeypatch.setattr(
        importlib.machinery.SourceFileLoader, "exec_module", forged_exec
    )
    with pytest.raises(DomainContractError, match="non-native completion"):
        _ = load_diff_domain(module)
    added = frozenset(sys.modules) - previous_names
    assert not any(name.startswith("_malbolge_diff_domain_") for name in added)
