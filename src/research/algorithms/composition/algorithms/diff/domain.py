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
    digest = hashlib.sha256(os.fsencode(path)).hexdigest()[:16]
    return f"_malbolge_diff_domain_{digest}"


def _require_module_path_without_nul(path: Path) -> None:
    if _NUL in str(path):
        message = "diff domain module path must not contain NUL"
        raise DomainContractError(message)


def _reject_linked_module_ancestors(path: Path) -> None:
    current = path.parent
    while current != current.parent:
        try:
            mode = current.lstat().st_mode
        except (OSError, ValueError) as error:
            message = f"diff domain module parent status failed: {current!r}"
            raise DomainContractError(message) from error
        if S_ISLNK(mode) or current.is_junction():
            message = f"diff domain module has a linked parent: {current!r}"
            raise DomainContractError(message)
        current = current.parent


def _regular_module_path(path: Path) -> Path:
    _require_module_path_without_nul(path)
    try:
        mode = path.lstat().st_mode
    except FileNotFoundError as error:
        message = f"diff domain module is not a regular file: {path}"
        raise DomainContractError(message) from error
    except (OSError, ValueError) as error:
        message = f"diff domain module status failed: {path!r}: {error!r}"
        raise DomainContractError(message) from error
    if S_ISLNK(mode) or path.is_junction() or not S_ISREG(mode):
        message = f"diff domain module is not a regular file: {path}"
        raise DomainContractError(message)
    _reject_linked_module_ancestors(path)
    try:
        return path.resolve(strict=True)
    except (OSError, ValueError) as error:
        message = f"diff domain module resolution failed: {path!r}: {error!r}"
        raise DomainContractError(message) from error


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


def _load_module(path: Path) -> tuple[ModuleType, ModuleType | None]:
    resolved = _regular_module_path(path)
    name = _module_name(resolved)
    spec = importlib.util.spec_from_file_location(name, resolved)
    if spec is None or spec.loader is None:
        message = f"cannot load diff domain module: {resolved}"
        raise DomainContractError(message)
    module = importlib.util.module_from_spec(spec)
    previous = sys.modules.get(name)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except Exception as error:
        _restore_domain_registration(name, module, previous)
        message = f"diff domain module execution failed: {resolved}: {error}"
        raise DomainContractError(message) from error
    return module, previous


def _callable(module: ModuleType, name: str) -> Callable[..., object]:
    value = getattr(module, name, None)
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
    if not isinstance(path, Path):
        message = "diff domain module path must use pathlib Path"
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
