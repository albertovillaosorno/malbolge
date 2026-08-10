# Copyright:
#   - Copyright (c) 2026 Alberto Villa Osorno.
# SPDX-License-Identifier:
#   - MIT
# Confidential:
#   - false
# License-File:
#   - LICENSE-MIT
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

from pathlib import Path
from typing import cast

from algorithms.diff.domain import DomainContractError
from algorithms.diff.domain import load_diff_domain
import pytest

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


def test_domain_module_execution_failure_uses_contract_error(
    tmp_path: Path,
) -> None:
    """Contain consumer import failures inside the domain contract boundary."""
    module = tmp_path / "domain.py"
    _write(module, 'raise RuntimeError("consumer boom")' + chr(10))

    with pytest.raises(DomainContractError, match="module execution failed"):
        _ = load_diff_domain(module)


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
