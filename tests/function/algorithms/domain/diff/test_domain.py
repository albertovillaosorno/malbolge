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

import builtins
import hashlib
import importlib.machinery
import importlib.util
import os
import py_compile
import stat
import subprocess
import sys
from collections.abc import Mapping
from dataclasses import replace
from pathlib import Path, PurePath
from types import CodeType, MemberDescriptorType, ModuleType, SimpleNamespace
from typing import TYPE_CHECKING, cast, override

import pytest
from algorithms.diff import domain as domain_module
from algorithms.diff.domain import DomainContractError, load_diff_domain

if TYPE_CHECKING:
    from collections.abc import Callable

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


def test_domain_loader_rejects_late_native_path_format_redirect(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Late pathlib formatting cannot select a different consumer module."""
    selected = tmp_path / "selected.py"
    redirected = tmp_path / "redirected.py"
    _write(selected, _COMPLETE)
    _write(redirected, _COMPLETE)
    native_format = cast(
        "Callable[[str, str, list[str]], str]",
        PurePath.__dict__["_format_parsed_parts"].__get__(None, PurePath),
    )
    redirected_name = str(redirected)
    calls = 0

    def forged_format(
        cls: type[PurePath], drive: str, root: str, tail: list[str]
    ) -> str:
        nonlocal calls
        if tail and tail[-1] == "selected.py":
            calls += 1
            return redirected_name
        return native_format(drive, root, tail)

    with monkeypatch.context() as patched:
        patched.setattr(
            PurePath, "_format_parsed_parts", classmethod(forged_format)
        )
        with pytest.raises(DomainContractError, match="path hooks changed"):
            _ = load_diff_domain(selected)
    assert calls == 0, "late pathname formatting reached module selection"


def test_domain_loader_rejects_late_native_parent_factory_bypass(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A forged parsed-parent factory cannot conceal linked directories."""
    physical = tmp_path / "physical"
    physical.mkdir()
    _write(physical / "domain.py", _COMPLETE)
    alias = tmp_path / "alias"
    try:
        alias.symlink_to(physical, target_is_directory=True)
    except OSError:
        pytest.skip("directory symlinks unavailable")
    selected = alias / "domain.py"
    native_factory = cast(
        "Callable[[PurePath, str, str, list[str]], PurePath]",
        PurePath.__dict__["_from_parsed_parts"],
    )
    calls = 0

    def forged_factory(
        self: PurePath, drive: str, root: str, tail: list[str]
    ) -> PurePath:
        nonlocal calls
        if self is selected:
            calls += 1
            return tmp_path
        return native_factory(self, drive, root, tail)

    with monkeypatch.context() as patched:
        patched.setattr(PurePath, "_from_parsed_parts", forged_factory)
        with pytest.raises(DomainContractError, match="path hooks changed"):
            _ = load_diff_domain(selected)
    assert calls == 0, "late parent factory skipped symlink admission"


def test_domain_loader_rejects_late_host_splitroot_redirection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An uncached Path cannot import another source through host parsing."""
    admitted = tmp_path / "admitted.py"
    redirected = tmp_path / "redirected.py"
    _write(admitted, _COMPLETE.replace("return None", "return 'admitted'"))
    _write(redirected, _COMPLETE.replace("return None", "return 'redirected'"))
    admitted_label = str(admitted)
    redirected_label = str(redirected)
    selected = Path(admitted_label)  # Keep the native parse cache empty.
    native_splitroot = os.path.splitroot
    calls = 0

    def forged_splitroot(raw: str) -> tuple[str, str, str]:
        nonlocal calls
        if raw == admitted_label:
            calls += 1
            return native_splitroot(redirected_label)
        return native_splitroot(raw)

    with monkeypatch.context() as patched:
        patched.setattr(os.path, "splitroot", forged_splitroot)
        with pytest.raises(DomainContractError, match="path helpers changed"):
            _ = load_diff_domain(selected)
    assert calls == 0, "mutable host splitroot redirected an admitted module"


def test_domain_loader_rejects_late_host_path_separator_override(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A mutable host parser separator cannot control module filenames."""
    selected = tmp_path / "domain.py"
    _write(selected, _COMPLETE)
    with monkeypatch.context() as patched:
        patched.setattr(os.path, "sep", "!")
        with pytest.raises(DomainContractError, match="path helpers changed"):
            _ = load_diff_domain(selected)


@pytest.mark.parametrize(
    ("provider", "helper"),
    [
        ("stat", "S_ISLNK"),
        ("stat", "S_ISDIR"),
        ("builtins", "isinstance"),
        ("builtins", "len"),
    ],
)
def test_domain_loader_rejects_late_realpath_helper_hook(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    provider: str,
    helper: str,
) -> None:
    """The pinned realpath must not invoke mutable host helper callbacks."""
    selected = tmp_path / "domain.py"
    _write(selected, _COMPLETE)
    module = stat if provider == "stat" else builtins
    original = cast("Callable[..., object]", getattr(module, helper))
    calls = 0

    def watched(*args: object, **kwargs: object) -> object:
        nonlocal calls
        calls += 1
        return original(*args, **kwargs)

    rejected = False
    with monkeypatch.context() as patched:
        patched.setattr(module, helper, watched)
        try:
            _ = load_diff_domain(selected)
        except DomainContractError:
            rejected = True
    assert rejected, f"late {provider}.{helper} hook was admitted"
    assert calls == 0, f"late {provider}.{helper} callback was executed"


def test_domain_loader_rejects_late_realpath_bytes_alias(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A forged builtin bytes type must not change realpath dispatch."""
    selected = tmp_path / "domain.py"
    _write(selected, _COMPLETE)
    rejected = False
    with monkeypatch.context() as patched:
        patched.setattr(builtins, "bytes", str)
        try:
            _ = load_diff_domain(selected)
        except DomainContractError:
            rejected = True
    assert rejected, "late bytes alias reached native path resolution"


def test_domain_loader_rejects_path_factory_swap_after_module_execution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A consumer import cannot leave native path factories modified."""
    module = tmp_path / "mutates_pathlib.py"
    _write(
        module,
        _COMPLETE
        + "\nfrom pathlib import PurePath\n"
        + "PurePath._format_parsed_parts = "
        + "classmethod(lambda cls, drive, root, tail: '/')\n",
    )
    original_format = PurePath.__dict__["_format_parsed_parts"]
    before = set(sys.modules)
    with monkeypatch.context() as patched:
        patched.setattr(PurePath, "_format_parsed_parts", original_format)
        with pytest.raises(DomainContractError, match="path hooks changed"):
            _ = load_diff_domain(module)
    new_modules = set(sys.modules) - before
    assert not any(
        name.startswith("_malbolge_diff_domain_") for name in new_modules
    )


def test_domain_path_hook_guard_ignores_late_any_override(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A domain hook cannot suppress the native path hook integrity scan."""
    module = tmp_path / "domain.py"
    _write(module, _COMPLETE)
    original_factory = PurePath.__dict__["_from_parsed_parts"]
    calls = 0

    def forged_factory(
        self: PurePath, drive: str, root: str, tail: list[str]
    ) -> PurePath:
        nonlocal calls
        calls += 1
        return cast("PurePath", original_factory(self, drive, root, tail))

    with monkeypatch.context() as patched:
        patched.setattr(PurePath, "_from_parsed_parts", forged_factory)
        patched.setattr(builtins, "any", lambda values: False)
        with pytest.raises(DomainContractError, match="path hooks changed"):
            _ = load_diff_domain(module)
    assert calls == 0, "mutable any bypassed the native path hook guard"


def test_domain_rejects_late_type_spoofed_module_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Consumer type hooks cannot admit overridable module selectors."""
    foreign = _ForeignDomainModulePath("unsafe-domain.py")
    native_type = type
    native_path_type = type(Path())
    calls = 0

    def forged_type(value: object) -> type[object]:
        nonlocal calls
        if value is foreign:
            calls += 1
            return native_path_type
        return native_type(value)

    rejected = False
    with monkeypatch.context() as patched:
        patched.setattr(builtins, "type", forged_type)
        try:
            _ = load_diff_domain(foreign)
        except DomainContractError as error:
            rejected = error.args == (
                "diff domain module path must use exact pathlib Path",
            )
    assert rejected, "mutable type admitted a foreign consumer path"
    assert calls == 0, "consumer type hook was consulted"


def test_domain_rejects_late_type_spoofed_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A consumer cannot type-launder a foreign filesystem receipt."""
    foreign = SimpleNamespace(st_mode=stat.S_IFREG | 0o644)
    native_type = type
    calls = 0

    def forged_type(value: object) -> type[object]:
        nonlocal calls
        if value is foreign:
            calls += 1
            return os.stat_result
        return native_type(value)

    rejected = False
    with monkeypatch.context() as patched:
        patched.setattr(builtins, "type", forged_type)
        try:
            _ = domain_module._require_native_module_status(foreign, "module")
        except DomainContractError:
            rejected = True
    assert rejected, "mutable type admitted non-native filesystem receipt"
    assert calls == 0, "consumer type hook was consulted"


def test_domain_rejects_late_type_spoofed_resolver(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A foreign resolved path must not gain local module-file authority."""
    foreign = object()
    native_type = type
    native_path_type = type(Path())
    calls = 0

    def forged_type(value: object) -> type[object]:
        nonlocal calls
        if value is foreign:
            calls += 1
            return native_path_type
        return native_type(value)

    rejected = False
    with monkeypatch.context() as patched:
        patched.setattr(
            domain_module, "_NATIVE_PATH_RESOLVE", lambda *a, **k: foreign
        )
        patched.setattr(builtins, "type", forged_type)
        try:
            _ = domain_module._resolved_native_module_path(
                tmp_path / "policy.py"
            )
        except DomainContractError:
            rejected = True
    assert rejected, "mutable type admitted foreign resolved path"
    assert calls == 0, "consumer type hook was consulted"


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


@pytest.mark.parametrize(
    "replacement",
    [
        "spec_from_file_location",
        "module_from_spec",
        "exec_module",
        "get_code",
        "get_data",
        "get_filename",
        "source_to_code",
        "__init__",
        "create_module",
    ],
)
def test_domain_rejects_late_native_import_loader_substitution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    replacement: str,
) -> None:
    """Late import hooks cannot authorize code from an unselected module."""
    trusted = tmp_path / "trusted.py"
    rogue = tmp_path / "rogue.py"
    marker = tmp_path / "rogue-executed"
    _write(trusted, _COMPLETE)
    _write(
        rogue, f"from pathlib import Path\nPath({str(marker)!r}).touch()\n" + _COMPLETE
    )
    original_spec = importlib.util.spec_from_file_location
    original_module = importlib.util.module_from_spec
    original_exec = importlib.machinery.SourceFileLoader.exec_module
    original_data = importlib.machinery.SourceFileLoader.get_data
    original_init = importlib.machinery.SourceFileLoader.__init__
    before = frozenset(sys.modules)

    def forged_spec(
        name: str, location: str
    ) -> importlib.machinery.ModuleSpec | None:
        del location
        return original_spec(name, rogue)

    def forged_module(spec: importlib.machinery.ModuleSpec) -> ModuleType:
        return original_module(spec)

    def forged_exec(
        loader: importlib.machinery.SourceFileLoader, module: ModuleType
    ) -> None:
        rogue_loader = importlib.machinery.SourceFileLoader(module.__name__, str(rogue))
        original_exec(rogue_loader, module)

    def forged_get_code(
        loader: importlib.machinery.SourceFileLoader, fullname: str
    ) -> CodeType:
        del loader, fullname
        return compile(rogue.read_text(encoding="utf-8"), str(rogue), "exec")

    def forged_get_data(
        loader: importlib.machinery.SourceFileLoader, path: str
    ) -> bytes:
        if path == str(trusted):
            return rogue.read_bytes()
        return original_data(loader, path)

    def forged_get_filename(
        loader: importlib.machinery.SourceFileLoader, fullname: str
    ) -> str:
        del loader, fullname
        return str(rogue)

    def forged_source_to_code(
        loader: importlib.machinery.SourceFileLoader,
        data: bytes,
        path: str,
        *,
        _optimize: int = -1,
    ) -> CodeType:
        del loader, data, path, _optimize
        return compile(rogue.read_text(encoding="utf-8"), str(rogue), "exec")

    def forged_init(
        loader: importlib.machinery.SourceFileLoader,
        name: str,
        path: str,
    ) -> None:
        del path
        original_init(loader, name, str(rogue))

    def forged_create_module(
        loader: importlib.machinery.SourceFileLoader,
        spec: importlib.machinery.ModuleSpec,
    ) -> None:
        del loader, spec
        _ = marker.touch()

    with monkeypatch.context() as patched:
        if replacement == "spec_from_file_location":
            patched.setattr(importlib.util, replacement, forged_spec)
        elif replacement == "module_from_spec":
            patched.setattr(importlib.util, replacement, forged_module)
        else:
            loader_methods = {
                "exec_module": forged_exec,
                "get_code": forged_get_code,
                "get_data": forged_get_data,
                "get_filename": forged_get_filename,
                "source_to_code": forged_source_to_code,
                "__init__": forged_init,
                "create_module": forged_create_module,
            }
            patched.setattr(
                importlib.machinery.SourceFileLoader,
                replacement,
                loader_methods[replacement],
            )
        with pytest.raises(DomainContractError):
            _ = load_diff_domain(trusted)
    assert not marker.exists(), "late import hook executed an unselected module"
    registered = frozenset(sys.modules) - before
    assert not any(name.startswith("_malbolge_diff_domain_") for name in registered)


def test_domain_rejects_late_source_loader_cache_metadata_substitution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Forged bytecode-cache status cannot execute an unselected module."""
    admitted = tmp_path / "admitted.py"
    rogue = tmp_path / "rogue.py"
    marker = tmp_path / "rogue-executed"
    _write(admitted, _COMPLETE)
    _write(rogue, f"from pathlib import Path\nPath({str(marker)!r}).touch()\n" + _COMPLETE)
    cached = Path(importlib.util.cache_from_source(str(admitted)))
    cached.parent.mkdir(parents=True, exist_ok=True)
    _ = py_compile.compile(str(rogue), cfile=str(cached), doraise=True)
    native_path_stats = importlib.machinery.SourceFileLoader.path_stats
    before = frozenset(sys.modules)

    def forged_path_stats(
        loader: importlib.machinery.SourceFileLoader, path: str
    ) -> Mapping[str, int | float]:
        if path == str(admitted):
            source_status = rogue.stat()
            return {"mtime": source_status.st_mtime, "size": source_status.st_size}
        return native_path_stats(loader, path)

    with monkeypatch.context() as patched:
        patched.setattr(
            importlib.machinery.SourceFileLoader, "path_stats", forged_path_stats
        )
        with pytest.raises(DomainContractError):
            _ = load_diff_domain(admitted)
    assert not marker.exists(), "unselected cached bytecode was executed"
    added = frozenset(sys.modules) - before
    assert not any(name.startswith("_malbolge_diff_domain_") for name in added)


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


def test_domain_module_identity_ignores_late_os_fspath(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The registration key must hash the actual native module path bytes."""
    module = tmp_path / "domain.py"
    expected = domain_module._module_name(module)
    native_fspath = os.fspath
    module_label = str(module)
    calls = 0

    def forged_fspath(
        value: str | bytes | os.PathLike[str] | os.PathLike[bytes],
    ) -> str | bytes:
        nonlocal calls
        if value == module_label:
            calls += 1
            return "forged-consumer-identity.py"
        return native_fspath(value)

    with monkeypatch.context() as patched:
        patched.setattr(os, "fspath", forged_fspath)
        actual = domain_module._module_name(module)
    assert actual == expected
    assert calls == 0, "domain identity used mutable os.fspath"


def test_domain_loader_rejects_late_os_fspath_module_swap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A late filesystem path hook cannot import a different local module."""
    admitted = tmp_path / "admitted.py"
    redirected = tmp_path / "redirected.py"
    _write(admitted, _COMPLETE.replace("return None", "return 'admitted'"))
    _write(redirected, _COMPLETE.replace("return None", "return 'redirected'"))
    native_fspath = os.fspath
    admitted_label = str(admitted)

    def forged_fspath(
        value: str | bytes | os.PathLike[str] | os.PathLike[bytes],
    ) -> str | bytes:
        if value == admitted_label:
            return str(redirected)
        return native_fspath(value)

    with monkeypatch.context() as patched:
        patched.setattr(os, "fspath", forged_fspath)
        with pytest.raises(DomainContractError, match="module.*resolution"):
            _ = load_diff_domain(admitted)


def test_domain_loader_rejects_late_os_fspath_hardlink_swap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Identical inodes do not license a different import module path."""
    admitted = tmp_path / "admitted.py"
    redirected = tmp_path / "other" / "admitted.py"
    redirected.parent.mkdir()
    _write(admitted, _COMPLETE)
    try:
        os.link(admitted, redirected)
    except OSError:
        pytest.skip("host does not permit regular-file hardlinks")
    native_fspath = os.fspath
    admitted_label = str(admitted)

    def forged_fspath(
        value: str | bytes | os.PathLike[str] | os.PathLike[bytes],
    ) -> str | bytes:
        if value == admitted_label:
            return str(redirected)
        return native_fspath(value)

    with monkeypatch.context() as patched:
        patched.setattr(os, "fspath", forged_fspath)
        with pytest.raises(DomainContractError, match="module.*resolution"):
            _ = load_diff_domain(admitted)


def test_domain_loader_rejects_late_getcwd_hardlink_swap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A replaced process CWD function cannot reroute relative module import."""
    admitted_parent = tmp_path / "admitted"
    redirected_parent = tmp_path / "other"
    admitted_parent.mkdir()
    redirected_parent.mkdir()
    admitted = admitted_parent / "domain.py"
    redirected = redirected_parent / "domain.py"
    _write(admitted, _COMPLETE)
    try:
        os.link(admitted, redirected)
    except OSError:
        pytest.skip("host does not permit regular-file hardlinks")

    with monkeypatch.context() as patched:
        patched.chdir(admitted_parent)
        patched.setattr(os, "getcwd", lambda: str(redirected_parent))
        with pytest.raises(DomainContractError, match="module.*resolution"):
            _ = load_diff_domain(Path("domain.py"))



def test_domain_loader_rejects_late_readlink_hardlink_swap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A forged symlink resolution cannot redirect a regular module file."""
    admitted = tmp_path / "admitted.py"
    redirected = tmp_path / "other" / "admitted.py"
    redirected.parent.mkdir()
    _write(admitted, _COMPLETE)
    try:
        os.link(admitted, redirected)
    except OSError:
        pytest.skip("host does not permit regular-file hardlinks")
    admitted_label = str(admitted)
    native_lstat = os.lstat
    native_readlink = os.readlink
    stat_fields = native_lstat(admitted)
    fake_link = os.stat_result((stat.S_IFLNK | 0o777, *stat_fields[1:]))

    def forged_lstat(path: str | bytes | os.PathLike[str]) -> os.stat_result:
        if path == admitted_label:
            return fake_link
        return native_lstat(path)

    def forged_readlink(path: str | bytes | os.PathLike[str]) -> str:
        if path == admitted_label:
            return str(redirected)
        # Domain module resolution supplies native string paths at this hook.
        result = native_readlink(cast("str", path))
        if isinstance(result, bytes):
            return os.fsdecode(result)
        return result

    with monkeypatch.context() as patched:
        patched.setattr(os, "lstat", forged_lstat)
        patched.setattr(os, "readlink", forged_readlink)
        with pytest.raises(DomainContractError, match="module.*resolution"):
            _ = load_diff_domain(admitted)


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


def test_direct_domain_rejects_late_callable_override(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Consumer overrides cannot convert a non-hook into trusted policy."""
    module = tmp_path / "domain.py"
    _write(module, _COMPLETE)
    domain = load_diff_domain(module)
    rejected = False
    with monkeypatch.context() as patched:
        patched.setattr(builtins, "callable", lambda value: True)
        try:
            _ = replace(
                domain,
                map_compatible_file=cast(
                    "Callable[[str, bytes], MappedView | None]", object()
                ),
            )
        except DomainContractError:
            rejected = True
    assert rejected, "mutable callable admitted a non-callable consumer hook"


def test_domain_hook_resolution_ignores_late_getattr_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A global hook shim cannot inject a missing consumer contract field."""
    module = ModuleType("missing_consumer_hook")
    calls = 0

    def spoof_getattr(obj: object, name: str, default: object = None) -> object:
        nonlocal calls
        calls += 1
        return lambda: None

    rejected = False
    with monkeypatch.context() as patched:
        patched.setattr(builtins, "getattr", spoof_getattr)
        try:
            _ = domain_module._callable(module, "build_behavior_programs")
        except DomainContractError:
            rejected = True
    assert rejected, "mutable getattr admitted a missing consumer hook"
    assert calls == 0, "untrusted global hook lookup was consulted"


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


@pytest.mark.parametrize("stage", ["execution", "hooks", "successful"])
@pytest.mark.parametrize("mutation", ["replace", "delete"])
@pytest.mark.parametrize("reload_existing", [False, True])
def test_rejected_domain_restores_registration_after_self_rebinding(
    tmp_path: Path, stage: str, mutation: str, reload_existing: bool
) -> None:
    """A rejected consumer cannot squat on its original import registry key."""
    module = tmp_path / "self_rebinding.py"
    name = domain_module._module_name(module.resolve())
    assert name not in sys.modules
    previous = None
    try:
        if reload_existing:
            _write(module, _COMPLETE)
            _ = load_diff_domain(module)
            previous = sys.modules[name]

        replacement = (
            "import sys\n"
            "from types import ModuleType\n"
            "sys.modules[__name__] = ModuleType(__name__)\n"
            if mutation == "replace"
            else "import sys\ndel sys.modules[__name__]\n"
        )
        if stage == "execution":
            rejected = replacement + "raise RuntimeError('rejected')\n"
            failure = "module execution failed"
        elif stage == "hooks":
            rejected = _COMPLETE.replace(
                "def build_behavior_programs():", "def invalid_hook():"
            ) + replacement
            failure = "registration changed"
        else:
            rejected = _COMPLETE + replacement
            failure = "registration changed"
        _write(module, rejected)
        with pytest.raises(DomainContractError, match=failure):
            _ = load_diff_domain(module)
        assert sys.modules.get(name) is previous
    finally:
        _ = sys.modules.pop(name, None)


@pytest.mark.parametrize("reload_existing", [False, True])
def test_domain_rejects_registration_swap_during_hook_lookup(
    tmp_path: Path, reload_existing: bool
) -> None:
    """Late hook lookup cannot silently replace a module registration."""
    module = tmp_path / "late_registration.py"
    name = domain_module._module_name(module.resolve())
    assert name not in sys.modules
    previous = None
    try:
        if reload_existing:
            _write(module, _COMPLETE)
            _ = load_diff_domain(module)
            previous = sys.modules[name]

        module_source = _COMPLETE.replace(
            "def build_behavior_programs():\n    return None\n\n", ""
        ) + (
            "def __getattr__(name):\n"
            "    if name == 'build_behavior_programs':\n"
            "        import sys\n"
            "        from types import ModuleType\n"
            "        sys.modules[__name__] = ModuleType(__name__)\n"
            "        return lambda: None\n"
            "    raise AttributeError(name)\n"
        )
        _write(module, module_source)
        with pytest.raises(DomainContractError, match="registration changed"):
            _ = load_diff_domain(module)
        assert sys.modules.get(name) is previous
    finally:
        _ = sys.modules.pop(name, None)


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


@pytest.mark.parametrize("reload_existing", [False, True])
@pytest.mark.parametrize(
    "changed_name", ["__name__ = 'foreign_alias'\n", "__name__ = []\n"]
)
def test_domain_failed_hook_validation_uses_original_registration_key(
    tmp_path: Path,
    changed_name: str,
    reload_existing: bool,
) -> None:
    """Consumer __name__ mutation cannot defeat rejected-module rollback."""
    module = tmp_path / "mutable_name.py"
    name = domain_module._module_name(module.resolve())
    assert name not in sys.modules
    _write(module, _COMPLETE)
    previous = None
    try:
        if reload_existing:
            _ = load_diff_domain(module)
            previous = sys.modules[name]
        missing = _COMPLETE.replace(
            "def build_behavior_programs():", "def invalid_hook():"
        )
        _write(module, missing + changed_name)
        with pytest.raises(
            DomainContractError, match="build_behavior_programs"
        ):
            _ = load_diff_domain(module)
        assert sys.modules.get(name) is previous
    finally:
        _ = sys.modules.pop(name, None)


def test_domain_constructor_cannot_skip_original_hook_validator(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Late post-init replacement must not admit a non-callable domain hook."""
    module = tmp_path / "domain.py"
    _write(module, _COMPLETE)
    valid = load_diff_domain(module)
    calls = 0

    def skip_validation(_domain: object) -> None:
        nonlocal calls
        calls += 1

    with monkeypatch.context() as patched:
        patched.setattr(domain_module.DiffDomain, "__post_init__", skip_validation)
        with pytest.raises(DomainContractError, match="map_compatible_file"):
            _ = replace(
                valid,
                map_compatible_file=cast(
                    "Callable[[str, bytes], MappedView | None]", object()
                ),
            )
    assert calls == 0, "late validator replacement was consulted"


def test_domain_validator_reads_original_hook_storage(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A class getter cannot spoof a non-callable stored consumer hook."""
    module = tmp_path / "domain.py"
    _write(module, _COMPLETE)
    valid = load_diff_domain(module)
    object.__setattr__(valid, "map_compatible_file", object())
    calls = 0

    def spoof_hook(_self: object) -> object:
        nonlocal calls
        calls += 1
        return lambda _path, _data: None

    with monkeypatch.context() as patched:
        patched.setattr(
            domain_module.DiffDomain, "map_compatible_file", property(spoof_hook)
        )
        with pytest.raises(DomainContractError, match="map_compatible_file"):
            domain_module.DiffDomain.__post_init__(valid)
    assert calls == 0, "late class getter hid the original hook"


_DOMAIN_HOOK_NAMES = (
    "validate_source_provenance",
    "validate_authoring_oracle",
    "build_identity_tree",
    "map_compatible_file",
    "build_compatible_correction_bindings",
    "build_behavior_programs",
    "build_behavior_probe_context",
)


@pytest.mark.parametrize("field", _DOMAIN_HOOK_NAMES)
def test_domain_constructor_rejects_forged_hook_setter(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, field: str
) -> None:
    """A substituted class setter cannot launder a non-callable hook."""
    module = tmp_path / "domain.py"
    _write(module, _COMPLETE)
    original = load_diff_domain(module)
    slot = domain_module.DiffDomain.__dict__[field]
    original_hook = getattr(original, field)
    calls = 0

    def sanitize(self: object, _value: object) -> None:
        nonlocal calls
        calls += 1
        slot.__set__(self, original_hook)

    with monkeypatch.context() as patched:
        patched.setattr(domain_module.DiffDomain, field, property(fset=sanitize))
        with pytest.raises(DomainContractError, match=field):
            _ = replace(original, **{field: object()})
    assert calls == 0, "constructor consulted late hook setter"


@pytest.mark.parametrize("field", _DOMAIN_HOOK_NAMES)
def test_domain_constructor_writes_original_hook_slots(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, field: str
) -> None:
    """Valid bundles must not invoke late field setters either."""
    module = tmp_path / "domain.py"
    _write(module, _COMPLETE)
    original = load_diff_domain(module)
    hook = getattr(original, field)
    calls = 0

    def forbidden_setter(_self: object, _value: object) -> None:
        nonlocal calls
        calls += 1
        raise AssertionError("constructor dispatched late hook setter")

    with monkeypatch.context() as patched:
        patched.setattr(
            domain_module.DiffDomain, field, property(fset=forbidden_setter)
        )
        constructed = replace(original, **{field: hook})
    assert type(constructed) is domain_module.DiffDomain
    assert calls == 0, "valid constructor consulted late hook setter"


def test_loaded_domain_ignores_late_initializer_hook(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Loaded consumer hooks cannot be rewritten by class constructor hooks."""
    module = tmp_path / "verified_domain.py"
    _write(module, _COMPLETE)
    identity_slot = cast(
        "MemberDescriptorType", domain_module.DiffDomain.__dict__["build_identity_tree"]
    )
    calls = 0

    def forged_init(self: domain_module.DiffDomain, **_kwargs: object) -> None:
        nonlocal calls
        calls += 1
        def replaced_identity(_root: Path) -> str:
            return "forged identity"
        identity_slot.__set__(self, replaced_identity)

    with monkeypatch.context() as patched:
        patched.setattr(domain_module.DiffDomain, "__init__", forged_init)
        observed = load_diff_domain(module)
    assert observed.build_identity_tree(tmp_path) is None
    assert calls == 0, "late class initializer modified loaded hook bundle"


def test_loaded_domain_ignores_late_allocator_in_isolated_process() -> None:
    """Changing DiffDomain.__new__ cannot redirect validated consumer hooks."""
    script = """
from types import ModuleType
from algorithms.diff.domain import DiffDomain, _validated_domain
module = ModuleType("verified_domain")
names = (
    "validate_source_provenance", "validate_authoring_oracle",
    "build_identity_tree", "map_compatible_file",
    "build_compatible_correction_bindings", "build_behavior_programs",
    "build_behavior_probe_context",
)
for name in names:
    setattr(module, name, lambda *args: None)
def forbidden_new(cls, *args, **kwargs):
    raise AssertionError("late domain __new__ was consulted")
DiffDomain.__new__ = staticmethod(forbidden_new)
observed = _validated_domain(module)
assert observed.build_identity_tree is module.build_identity_tree
"""
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(sys.path)
    result = subprocess.run(
        [sys.executable, "-B", "-c", script],
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
    )
    assert result.returncode == 0, result.stderr
