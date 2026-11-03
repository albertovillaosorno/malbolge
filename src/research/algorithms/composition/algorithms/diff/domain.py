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
#   - Validated dynamic consumer-domain contract for diff generation.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#

"""Validated dynamic consumer-domain contract for diff generation."""

from __future__ import annotations

import builtins
import hashlib
import importlib.machinery
import importlib.util
import os
import sys
from dataclasses import dataclass
from pathlib import Path, PurePath
from stat import S_ISLNK, S_ISREG
from types import MemberDescriptorType
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from collections.abc import Callable
    from types import ModuleType

    from algorithms.diff.admission import IdentityTree
    from algorithms.diff.behavior_programs import BehaviorPrograms
    from algorithms.diff.compatible import (
        CompatibleAuthoringPlan,
        CompatibleCorrectionBinding,
    )
    from algorithms.diff.mapped import MappedView
    from algorithms.diff.probe_exec import ProbeRunContext
    from algorithms.diff.provenance import SourcePinEvidence

    CorrectionBindingBuilder = Callable[
        [CompatibleAuthoringPlan],
        tuple[CompatibleCorrectionBinding, ...],
    ]


_NUL = "\x00"
# Domain validation must not trust builtins replaced by imported consumers.
_NATIVE_CALLABLE = builtins.callable
_NATIVE_ANY = builtins.any
_NATIVE_TUPLE = tuple
_NATIVE_GETATTR = builtins.getattr
_NATIVE_TYPE = builtins.type
_NATIVE_BOOL_TYPE = builtins.bool
_NATIVE_STAT_RESULT = os.stat_result
_NATIVE_PATH_TYPE = _NATIVE_TYPE(Path())
_NATIVE_PATH_STRING = Path.__str__
_NATIVE_PATH_PARENT = Path.parent
_NATIVE_OS_LSTAT = os.lstat
_NATIVE_OS_REALPATH = os.path.realpath
_NATIVE_OS_FSPATH = os.fspath
_NATIVE_OS_GETCWD = os.getcwd
_NATIVE_OS_READLINK = os.readlink
_NATIVE_OS_IS_JUNCTION = os.path.isjunction
# os.fsencode delegates to mutable os.fspath even when its function is pinned.
_FILESYSTEM_ENCODING = sys.getfilesystemencoding()
_FILESYSTEM_ERRORS = sys.getfilesystemencodeerrors()
_SHA256_FACTORY = hashlib.sha256
# A verified domain file must not be rerouted through import machinery swapped
# by an earlier consumer callback. These are the exact host import entry points
# admitted before any consumer-domain module executes.
_NATIVE_IMPORT_SPEC = importlib.util.spec_from_file_location
_NATIVE_IMPORT_MODULE = importlib.util.module_from_spec
_NATIVE_SOURCE_LOADER_EXEC = importlib.machinery.SourceFileLoader.exec_module
_NATIVE_SOURCE_LOADER_GET_CODE = importlib.machinery.SourceFileLoader.get_code
_NATIVE_SOURCE_LOADER_GET_DATA = importlib.machinery.SourceFileLoader.get_data
_NATIVE_SOURCE_LOADER_GET_FILENAME = importlib.machinery.SourceFileLoader.get_filename
_NATIVE_SOURCE_LOADER_SOURCE_TO_CODE = importlib.machinery.SourceFileLoader.source_to_code
_NATIVE_SOURCE_LOADER_INIT = importlib.machinery.SourceFileLoader.__init__
_NATIVE_SOURCE_LOADER_CREATE_MODULE = importlib.machinery.SourceFileLoader.create_module
_NATIVE_SOURCE_LOADER_PATH_STATS = importlib.machinery.SourceFileLoader.path_stats
_NATIVE_OBJECT_NEW = object.__new__
_NATIVE_OS_PATH_PARSER = os.path
_NATIVE_OS_PATH_JOIN = os.path.join
_NATIVE_OS_PATH_SPLITROOT = os.path.splitroot
_NATIVE_OS_PATH_SPLITDRIVE = os.path.splitdrive
_NATIVE_OS_PATH_SEP = os.path.sep
_NATIVE_OS_PATH_ALTSEP = os.path.altsep
# Original Path.__str__ and Path.parent still dispatch through mutable
# pathlib factories and descriptors. An untrusted module path must not be
# redirected or have linked ancestors hidden by a late class hook.
_PATH_HOOK_NAMES = (
    "__new__",
    "__init__",
    "__getattribute__",
    "__getattr__",
    "__setattr__",
    "_str",
    "_raw_paths",
    "_drv",
    "_root",
    "_tail_cached",
    "_raw_path",
    "_tail",
    "drive",
    "root",
    "_parse_path",
    "_from_parsed_parts",
    "_from_parsed_string",
    "_format_parsed_parts",
    "parser",
)
_NATIVE_PATH_HOOKS = _NATIVE_TUPLE(
    (
        cls,
        _NATIVE_TUPLE((name, cls.__dict__.get(name)) for name in _PATH_HOOK_NAMES),
    )
    for cls in _NATIVE_PATH_TYPE.__mro__
    if issubclass(cls, PurePath)
)


def _require_native_path_hooks() -> None:
    """Reject mutable native pathlib hooks before trusting module selection."""
    # Pinned PurePath methods still read the mutable host parser at runtime.
    # A forged splitroot or separator can redirect an uncached exact Path.
    if (
        os.path is not _NATIVE_OS_PATH_PARSER
        or os.path.splitroot is not _NATIVE_OS_PATH_SPLITROOT
        or os.path.splitdrive is not _NATIVE_OS_PATH_SPLITDRIVE
        or os.path.sep is not _NATIVE_OS_PATH_SEP
        or os.path.altsep is not _NATIVE_OS_PATH_ALTSEP
    ):
        message = "diff domain module path helpers changed"
        raise DomainContractError(message)
    if _NATIVE_ANY(
        cls.__dict__.get(name) is not original
        for cls, hooks in _NATIVE_PATH_HOOKS
        for name, original in hooks
    ):
        message = "diff domain module path hooks changed"
        raise DomainContractError(message)


def _native_path_parent(path: Path) -> Path:
    return _NATIVE_PATH_PARENT.__get__(path, _NATIVE_TYPE(path))


def _native_path_lstat(path: Path) -> os.stat_result:
    return _NATIVE_OS_LSTAT(_NATIVE_PATH_STRING(path))


def _native_path_resolve(path: Path, *, strict: bool = False) -> Path:
    # realpath dynamically consults these process-global helpers even when
    # the outer function is pinned. A changed CWD, lstat, or readlink can
    # redirect an import, including to a hardlink with identical inode data.
    if (
        os.fspath is not _NATIVE_OS_FSPATH
        or os.getcwd is not _NATIVE_OS_GETCWD
        or os.lstat is not _NATIVE_OS_LSTAT
        or os.readlink is not _NATIVE_OS_READLINK
        or os.path.join is not _NATIVE_OS_PATH_JOIN
    ):
        message = "diff domain module resolution requires native path helpers"
        raise DomainContractError(message)
    return Path(_NATIVE_OS_REALPATH(_NATIVE_PATH_STRING(path), strict=strict))


def _native_path_is_junction(path: Path) -> bool:
    return _NATIVE_OS_IS_JUNCTION(_NATIVE_PATH_STRING(path))


_NATIVE_PATH_LSTAT = _native_path_lstat
_NATIVE_PATH_RESOLVE = _native_path_resolve
_NATIVE_PATH_IS_JUNCTION = _native_path_is_junction


class DomainContractError(ValueError):
    """Invalid diff consumer-module contract."""


@dataclass(frozen=True, slots=True, init=False)
class DiffDomain:
    """Callable hooks required by generic domain-aware authoring."""

    validate_source_provenance: Callable[[Path], SourcePinEvidence]
    validate_authoring_oracle: Callable[[Path], None]
    build_identity_tree: Callable[[Path], IdentityTree]
    map_compatible_file: Callable[[str, bytes], MappedView | None]
    build_compatible_correction_bindings: CorrectionBindingBuilder
    build_behavior_programs: Callable[[], BehaviorPrograms]
    build_behavior_probe_context: Callable[[Path, Path], ProbeRunContext]

    def __init__(
        self,
        validate_source_provenance: Callable[[Path], SourcePinEvidence],
        validate_authoring_oracle: Callable[[Path], None],
        build_identity_tree: Callable[[Path], IdentityTree],
        map_compatible_file: Callable[[str, bytes], MappedView | None],
        build_compatible_correction_bindings: CorrectionBindingBuilder,
        build_behavior_programs: Callable[[], BehaviorPrograms],
        build_behavior_probe_context: Callable[[Path, Path], ProbeRunContext],
    ) -> None:
        """Validate native hook slots through the original constructor guard."""
        # Write through captured descriptors; object.__setattr__ dispatches
        # substituted class-property setters, which can launder invalid hooks.
        _DOMAIN_PROVENANCE_SLOT.__set__(self, validate_source_provenance)
        _DOMAIN_ORACLE_SLOT.__set__(self, validate_authoring_oracle)
        _DOMAIN_IDENTITY_SLOT.__set__(self, build_identity_tree)
        _DOMAIN_MAPPING_SLOT.__set__(self, map_compatible_file)
        _DOMAIN_CORRECTIONS_SLOT.__set__(
            self, build_compatible_correction_bindings
        )
        _DOMAIN_PROGRAMS_SLOT.__set__(self, build_behavior_programs)
        _DOMAIN_CONTEXT_SLOT.__set__(
            self, build_behavior_probe_context
        )
        _DIFF_DOMAIN_VALIDATOR(self)

    def __post_init__(self) -> None:
        """Require every trusted consumer hook to remain callable.

        Raises:
            DomainContractError: Any trusted hook is not callable.

        """
        for name, slot in _DIFF_DOMAIN_HOOK_SLOTS:
            if not _NATIVE_CALLABLE(slot.__get__(self, DiffDomain)):
                message = f"diff domain hook must be callable: {name}"
                raise DomainContractError(message)


# Generated dataclass initializers would look up the mutable class validator.
# Keep the constructor guard and original slot descriptors independent of later
# consumer-supplied class getters and validators.
_DIFF_DOMAIN_VALIDATOR = cast(
    "Callable[[DiffDomain], None]", DiffDomain.__dict__["__post_init__"]
)
_DIFF_DOMAIN_INIT = DiffDomain.__init__
_DOMAIN_PROVENANCE_SLOT = cast(
    "MemberDescriptorType", DiffDomain.__dict__["validate_source_provenance"]
)
_DOMAIN_ORACLE_SLOT = cast(
    "MemberDescriptorType", DiffDomain.__dict__["validate_authoring_oracle"]
)
_DOMAIN_IDENTITY_SLOT = cast(
    "MemberDescriptorType", DiffDomain.__dict__["build_identity_tree"]
)
_DOMAIN_MAPPING_SLOT = cast(
    "MemberDescriptorType", DiffDomain.__dict__["map_compatible_file"]
)
_DOMAIN_CORRECTIONS_SLOT = cast(
    "MemberDescriptorType", DiffDomain.__dict__["build_compatible_correction_bindings"]
)
_DOMAIN_PROGRAMS_SLOT = cast(
    "MemberDescriptorType", DiffDomain.__dict__["build_behavior_programs"]
)
_DOMAIN_CONTEXT_SLOT = cast(
    "MemberDescriptorType", DiffDomain.__dict__["build_behavior_probe_context"]
)
_DIFF_DOMAIN_HOOK_SLOTS: tuple[tuple[str, MemberDescriptorType], ...] = (
    ("validate_source_provenance", _DOMAIN_PROVENANCE_SLOT),
    ("validate_authoring_oracle", _DOMAIN_ORACLE_SLOT),
    ("build_identity_tree", _DOMAIN_IDENTITY_SLOT),
    ("map_compatible_file", _DOMAIN_MAPPING_SLOT),
    ("build_compatible_correction_bindings", _DOMAIN_CORRECTIONS_SLOT),
    ("build_behavior_programs", _DOMAIN_PROGRAMS_SLOT),
    ("build_behavior_probe_context", _DOMAIN_CONTEXT_SLOT),
)


def _module_name(path: Path) -> str:
    digest = _SHA256_FACTORY(
        _NATIVE_PATH_STRING(path).encode(
            _FILESYSTEM_ENCODING, _FILESYSTEM_ERRORS
        )
    ).hexdigest()[:16]
    return f"_malbolge_diff_domain_{digest}"


def _require_module_path_without_nul(path: Path) -> None:
    if _NUL in _NATIVE_PATH_STRING(path):
        message = "diff domain module path must not contain NUL"
        raise DomainContractError(message)


def _module_is_junction(path: Path) -> bool:
    try:
        verdict = _NATIVE_PATH_IS_JUNCTION(path)
    except (OSError, ValueError, RuntimeError) as error:
        message = (
            "diff domain module junction status failed: "
            f"{_NATIVE_PATH_STRING(path)!r}"
        )
        raise DomainContractError(message) from error
    if _NATIVE_TYPE(verdict) is not _NATIVE_BOOL_TYPE:
        message = "diff domain module junction status requires native boolean"
        raise DomainContractError(message)
    return verdict


def _require_native_module_status(
    receipt: object, description: str
) -> os.stat_result:
    """Reject foreign filesystem metadata before consumer code executes.

    Returns:
        The exact native host status receipt.

    Raises:
        DomainContractError: Status is not an exact host record.

    """
    if _NATIVE_TYPE(receipt) is not _NATIVE_STAT_RESULT:
        message = f"diff domain {description} requires native filesystem status"
        raise DomainContractError(message)
    return receipt


def _reject_linked_module_ancestors(path: Path) -> None:
    current = _native_path_parent(path)
    while _NATIVE_PATH_STRING(current) != _NATIVE_PATH_STRING(
        _native_path_parent(current)
    ):
        try:
            receipt = _NATIVE_PATH_LSTAT(current)
        except (OSError, ValueError, RuntimeError) as error:
            message = (
                "diff domain module parent status failed: "
                f"{_NATIVE_PATH_STRING(current)!r}"
            )
            raise DomainContractError(message) from error
        receipt = _require_native_module_status(receipt, "parent")
        if S_ISLNK(receipt.st_mode) or _module_is_junction(current):
            message = (
                "diff domain module has a linked parent: "
                f"{_NATIVE_PATH_STRING(current)!r}"
            )
            raise DomainContractError(message)
        current = _native_path_parent(current)


def _resolved_native_module_path(
    path: Path, admitted: os.stat_result | None = None
) -> Path:
    """Require a native canonical path before import machinery receives it.

    Returns:
        The native resolved filesystem path.

    Raises:
        DomainContractError: Resolution fails or provides a foreign path.

    """
    try:
        resolved = _NATIVE_PATH_RESOLVE(path, strict=True)
    except (OSError, ValueError, RuntimeError) as error:
        message = f"diff domain module resolution failed: {_NATIVE_PATH_STRING(path)!r}"
        raise DomainContractError(message) from error
    if _NATIVE_TYPE(resolved) is not _NATIVE_PATH_TYPE:
        message = "diff domain module resolution requires native Path"
        raise DomainContractError(message)
    # os.path.realpath itself consults mutable os.fspath. A late consumer
    # hook can redirect a path even though the outer function is pinned.
    # Require the resolved module to be the same physical file admitted above.
    try:
        original = (
            _require_native_module_status(_NATIVE_PATH_LSTAT(path), "module")
            if admitted is None
            else admitted
        )
        resolved_status = _require_native_module_status(
            _NATIVE_PATH_LSTAT(resolved), "resolved module"
        )
    except (OSError, ValueError, RuntimeError) as error:
        message = "diff domain module resolution status failed"
        raise DomainContractError(message) from error
    if (
        original.st_dev != resolved_status.st_dev
        or original.st_ino != resolved_status.st_ino
        or not S_ISREG(resolved_status.st_mode)
    ):
        message = "diff domain module resolution changed file identity"
        raise DomainContractError(message)
    return resolved


def _regular_module_path(path: Path) -> Path:
    _require_module_path_without_nul(path)
    try:
        receipt = _NATIVE_PATH_LSTAT(path)
    except FileNotFoundError as error:
        message = (
            "diff domain module is not a regular file: "
            f"{_NATIVE_PATH_STRING(path)}"
        )
        raise DomainContractError(message) from error
    except (OSError, ValueError, RuntimeError) as error:
        message = f"diff domain module status failed: {_NATIVE_PATH_STRING(path)!r}"
        raise DomainContractError(message) from error
    receipt = _require_native_module_status(receipt, "module")
    if (
        S_ISLNK(receipt.st_mode)
        or _module_is_junction(path)
        or not S_ISREG(receipt.st_mode)
    ):
        message = (
            "diff domain module is not a regular file: "
            f"{_NATIVE_PATH_STRING(path)}"
        )
        raise DomainContractError(message)
    _reject_linked_module_ancestors(path)
    return _resolved_native_module_path(path, receipt)


def _restore_domain_registration(
    name: str, previous: ModuleType | None
) -> None:
    """Restore the last accepted module even after consumer key rebinding."""
    if previous is None:
        _ = sys.modules.pop(name, None)
    else:
        sys.modules[name] = previous


def _prepare_module(
    resolved: Path, name: str
) -> tuple[ModuleType, Callable[[ModuleType], object]]:
    """Build a loader-bound module before publishing any registration.

    Returns:
        The unexecuted module and native loader entry point.

    Raises:
        DomainContractError: The import spec or module is unusable.

    """
    if (
        importlib.util.spec_from_file_location is not _NATIVE_IMPORT_SPEC
        or importlib.util.module_from_spec is not _NATIVE_IMPORT_MODULE
    ):
        message = "diff domain import preparation failed: native import hooks changed"
        raise DomainContractError(message)
    if (
        importlib.machinery.SourceFileLoader.exec_module
        is not _NATIVE_SOURCE_LOADER_EXEC
        or importlib.machinery.SourceFileLoader.get_code
        is not _NATIVE_SOURCE_LOADER_GET_CODE
        or importlib.machinery.SourceFileLoader.get_data
        is not _NATIVE_SOURCE_LOADER_GET_DATA
        or importlib.machinery.SourceFileLoader.get_filename
        is not _NATIVE_SOURCE_LOADER_GET_FILENAME
        or importlib.machinery.SourceFileLoader.source_to_code
        is not _NATIVE_SOURCE_LOADER_SOURCE_TO_CODE
        or importlib.machinery.SourceFileLoader.__init__
        is not _NATIVE_SOURCE_LOADER_INIT
        or importlib.machinery.SourceFileLoader.create_module
        is not _NATIVE_SOURCE_LOADER_CREATE_MODULE
        or importlib.machinery.SourceFileLoader.path_stats
        is not _NATIVE_SOURCE_LOADER_PATH_STATS
    ):
        message = "diff domain module execution reported non-native completion"
        raise DomainContractError(message)
    try:
        spec = _NATIVE_IMPORT_SPEC(name, _NATIVE_PATH_STRING(resolved))
        loader = spec.loader if spec is not None else None
    except Exception as error:
        message = (
            "diff domain import preparation failed: "
            f"{_NATIVE_PATH_STRING(resolved)}"
        )
        raise DomainContractError(message) from error
    if spec is None or loader is None:
        message = f"cannot load diff domain module: {_NATIVE_PATH_STRING(resolved)}"
        raise DomainContractError(message)
    try:
        module = _NATIVE_IMPORT_MODULE(spec)
    except Exception as error:
        message = (
            "diff domain import preparation failed: "
            f"{_NATIVE_PATH_STRING(resolved)}"
        )
        raise DomainContractError(message) from error
    return module, loader.exec_module


def _load_module(path: Path) -> tuple[ModuleType, ModuleType | None, str]:
    resolved = _regular_module_path(path)
    name = _module_name(resolved)
    module, exec_module = _prepare_module(resolved, name)
    previous = sys.modules.get(name)
    sys.modules[name] = module
    try:
        completion = exec_module(module)
    except Exception as error:
        _restore_domain_registration(name, previous)
        message = (
            "diff domain module execution failed: "
            f"{_NATIVE_PATH_STRING(resolved)}"
        )
        raise DomainContractError(message) from error
    try:
        _require_native_path_hooks()
    except DomainContractError:
        _restore_domain_registration(name, previous)
        raise
    if completion is not None:
        _restore_domain_registration(name, previous)
        message = (
            "diff domain module execution reported non-native completion: "
            f"{_NATIVE_PATH_STRING(resolved)}"
        )
        raise DomainContractError(message)
    if sys.modules.get(name) is not module:
        _restore_domain_registration(name, previous)
        message = "diff domain module registration changed during execution"
        raise DomainContractError(message)
    return module, previous, name


def _callable(module: ModuleType, name: str) -> Callable[..., object]:
    try:
        value = _NATIVE_GETATTR(module, name, None)
    except Exception as error:
        message = f"diff domain hook lookup failed for {name!r}"
        raise DomainContractError(message) from error
    if not _NATIVE_CALLABLE(value):
        message = f"diff domain module requires callable {name!r}"
        raise DomainContractError(message)
    return value


def load_diff_domain(path: object) -> DiffDomain:
    """Load and validate the trusted local consumer module used for authoring.

    Returns:
        Explicit diff-domain hook bundle.

    Raises:
        DomainContractError: Module path or execution is invalid.

    """
    # Loading a module executes code; never admit overridable Path methods.
    if _NATIVE_TYPE(path) is not _NATIVE_PATH_TYPE:
        message = "diff domain module path must use exact pathlib Path"
        raise DomainContractError(message)
    _require_native_path_hooks()
    module, previous, name = _load_module(path)
    try:
        domain = _validated_domain(module)
        _require_native_path_hooks()
        if sys.modules.get(name) is not module:
            message = (
                "diff domain module registration changed during validation"
            )
            raise DomainContractError(message)
        return domain
    except Exception:
        _restore_domain_registration(name, previous)
        raise


def _validated_domain(module: ModuleType) -> DiffDomain:
    """Require a fully valid hook bundle before retaining a loaded module.

    Returns:
        Validated domain hooks ready for use.

    """
    domain = _NATIVE_OBJECT_NEW(DiffDomain)
    _DIFF_DOMAIN_INIT(
        domain,
        validate_source_provenance=cast(
            "Callable[[Path], SourcePinEvidence]",
            _callable(module, "validate_source_provenance"),
        ),
        validate_authoring_oracle=cast(
            "Callable[[Path], None]",
            _callable(module, "validate_authoring_oracle"),
        ),
        build_identity_tree=cast(
            "Callable[[Path], IdentityTree]",
            _callable(module, "build_identity_tree"),
        ),
        map_compatible_file=cast(
            "Callable[[str, bytes], MappedView | None]",
            _callable(module, "map_compatible_file"),
        ),
        build_compatible_correction_bindings=cast(
            "CorrectionBindingBuilder",
            _callable(module, "build_compatible_correction_bindings"),
        ),
        build_behavior_programs=cast(
            "Callable[[], BehaviorPrograms]",
            _callable(module, "build_behavior_programs"),
        ),
        build_behavior_probe_context=cast(
            "Callable[[Path, Path], ProbeRunContext]",
            _callable(module, "build_behavior_probe_context"),
        ),
    )
    return domain
