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

from dataclasses import dataclass
import hashlib
import importlib.util
import os
from pathlib import Path
from stat import S_ISLNK
from stat import S_ISREG
import sys
from typing import TYPE_CHECKING
from typing import cast

if TYPE_CHECKING:
    from collections.abc import Callable
    from types import ModuleType

    from algorithms.diff.admission import IdentityTree
    from algorithms.diff.behavior_programs import BehaviorPrograms
    from algorithms.diff.compatible import CompatibleAuthoringPlan
    from algorithms.diff.compatible import CompatibleCorrectionBinding
    from algorithms.diff.mapped import MappedView
    from algorithms.diff.probe_exec import ProbeRunContext
    from algorithms.diff.provenance import SourcePinEvidence

    CorrectionBindingBuilder = Callable[
        [CompatibleAuthoringPlan],
        tuple[CompatibleCorrectionBinding, ...],
    ]


_NUL = "\x00"
_NATIVE_STAT_RESULT = os.stat_result
_NATIVE_PATH_TYPE = type(Path())
_NATIVE_PATH_STRING = Path.__str__
_NATIVE_PATH_PARENT = Path.parent
_NATIVE_OS_LSTAT = os.lstat
_NATIVE_OS_REALPATH = os.path.realpath
_NATIVE_OS_IS_JUNCTION = os.path.isjunction
_NATIVE_OS_FSENCODE = os.fsencode
_SHA256_FACTORY = hashlib.sha256


def _native_path_parent(path: Path) -> Path:
    return _NATIVE_PATH_PARENT.__get__(path, type(path))


def _native_path_lstat(path: Path) -> os.stat_result:
    return _NATIVE_OS_LSTAT(_NATIVE_PATH_STRING(path))


def _native_path_resolve(path: Path, *, strict: bool = False) -> Path:
    return Path(_NATIVE_OS_REALPATH(_NATIVE_PATH_STRING(path), strict=strict))


def _native_path_is_junction(path: Path) -> bool:
    return _NATIVE_OS_IS_JUNCTION(_NATIVE_PATH_STRING(path))


_NATIVE_PATH_LSTAT = _native_path_lstat
_NATIVE_PATH_RESOLVE = _native_path_resolve
_NATIVE_PATH_IS_JUNCTION = _native_path_is_junction


class DomainContractError(ValueError):
    """Invalid diff consumer-module contract."""


@dataclass(frozen=True, slots=True)
class DiffDomain:
    """Callable hooks required by generic domain-aware authoring."""

    validate_source_provenance: Callable[[Path], SourcePinEvidence]
    validate_authoring_oracle: Callable[[Path], None]
    build_identity_tree: Callable[[Path], IdentityTree]
    map_compatible_file: Callable[[str, bytes], MappedView | None]
    build_compatible_correction_bindings: CorrectionBindingBuilder
    build_behavior_programs: Callable[[], BehaviorPrograms]
    build_behavior_probe_context: Callable[[Path, Path], ProbeRunContext]

    def __post_init__(self) -> None:
        """Require every trusted consumer hook to remain callable.

        Raises:
            DomainContractError: Any trusted hook is not callable.

        """
        hooks = (
            ("validate_source_provenance", self.validate_source_provenance),
            ("validate_authoring_oracle", self.validate_authoring_oracle),
            ("build_identity_tree", self.build_identity_tree),
            ("map_compatible_file", self.map_compatible_file),
            (
                "build_compatible_correction_bindings",
                self.build_compatible_correction_bindings,
            ),
            ("build_behavior_programs", self.build_behavior_programs),
            (
                "build_behavior_probe_context",
                self.build_behavior_probe_context,
            ),
        )
        for name, hook in hooks:
            if not callable(hook):
                message = f"diff domain hook must be callable: {name}"
                raise DomainContractError(message)


def _module_name(path: Path) -> str:
    digest = _SHA256_FACTORY(
        _NATIVE_OS_FSENCODE(_NATIVE_PATH_STRING(path))
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
    if type(verdict) is not bool:
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
    if type(receipt) is not _NATIVE_STAT_RESULT:
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


def _resolved_native_module_path(path: Path) -> Path:
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
    if type(resolved) is not _NATIVE_PATH_TYPE:
        message = "diff domain module resolution requires native Path"
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
    return _resolved_native_module_path(path)


def _restore_domain_registration(
    name: str,
    attempted: ModuleType,
    previous: ModuleType | None,
) -> None:
    """Restore the last accepted module when a replacement load fails."""
    if sys.modules.get(name) is not attempted:
        return
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
    try:
        spec = importlib.util.spec_from_file_location(
            name, _NATIVE_PATH_STRING(resolved)
        )
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
        module = importlib.util.module_from_spec(spec)
    except Exception as error:
        message = (
            "diff domain import preparation failed: "
            f"{_NATIVE_PATH_STRING(resolved)}"
        )
        raise DomainContractError(message) from error
    return module, loader.exec_module


def _load_module(path: Path) -> tuple[ModuleType, ModuleType | None]:
    resolved = _regular_module_path(path)
    name = _module_name(resolved)
    module, exec_module = _prepare_module(resolved, name)
    previous = sys.modules.get(name)
    sys.modules[name] = module
    try:
        completion = exec_module(module)
    except Exception as error:
        _restore_domain_registration(name, module, previous)
        message = (
            "diff domain module execution failed: "
            f"{_NATIVE_PATH_STRING(resolved)}"
        )
        raise DomainContractError(message) from error
    if completion is not None:
        _restore_domain_registration(name, module, previous)
        message = (
            "diff domain module execution reported non-native completion: "
            f"{_NATIVE_PATH_STRING(resolved)}"
        )
        raise DomainContractError(message)
    return module, previous


def _callable(module: ModuleType, name: str) -> Callable[..., object]:
    try:
        value = getattr(module, name, None)
    except Exception as error:
        message = f"diff domain hook lookup failed for {name!r}"
        raise DomainContractError(message) from error
    if not callable(value):
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
    if type(path) is not type(Path()):
        message = "diff domain module path must use exact pathlib Path"
        raise DomainContractError(message)
    module, previous = _load_module(path)
    try:
        return _validated_domain(module)
    except Exception:
        _restore_domain_registration(module.__name__, module, previous)
        raise


def _validated_domain(module: ModuleType) -> DiffDomain:
    """Require a fully valid hook bundle before retaining a loaded module.

    Returns:
        Validated domain hooks ready for use.

    """
    return DiffDomain(
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
