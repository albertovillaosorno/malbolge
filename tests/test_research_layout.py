# Copyright:
#   - Copyright © 2026 Alberto Villa Osorno.
# SPDX-License-Identifier:
#   - MIT
# Confidential:
#   - false
# License-File:
#   - LICENSE-MIT
#
# Boundary-Contract:
# - Owns:
#   - Fail-closed filesystem discovery evidence for research layout projection.
# - Must-Not:
#   - Parse experiment manifests or redefine research identities.
# - Allows:
#   - Inputs: test-local repository roots and injected filesystem failures.
#   - Outputs: deterministic discovery or propagated filesystem errors.
#   - Side effects: test-local filesystem writes only.
# - Split-When:
#   - Another discovery backend gains independent failure semantics.
# - Merge-When:
#   - Research layout discovery moves into another validator.
# - Summary:
#   - Prove research manifest discovery cannot hide inaccessible evidence.
# - Description:
#   - Distinguishes absent manifests from filesystem status failures.
# - Usage:
#   - Run through the repository Python validation suite.
# - Defaults:
#   - Inaccessible manifest status fails closed.
#

"""Fail-closed tests for research experiment layout discovery."""

from pathlib import Path

import pytest
from scripts import research_layout


def _domain_root(root: Path) -> Path:
    return root / "src/research/algorithms/domain/algorithms"


def test_directory_without_manifest_remains_excluded(tmp_path: Path) -> None:
    """A genuinely absent experiment manifest is not a research experiment."""
    directory = _domain_root(tmp_path) / "utility"
    directory.mkdir(parents=True)
    assert research_layout.research_algorithm_directories(tmp_path) == ()


def test_inaccessible_manifest_status_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A status error cannot make one existing research manifest disappear."""
    directory = _domain_root(tmp_path) / "candidate"
    directory.mkdir(parents=True)
    manifest = directory / "experiment.toml"
    _ = manifest.write_text("schema_version = 1\n", encoding="utf-8")
    original_lstat = Path.lstat

    def fail_manifest_status(
        path: Path,
    ) -> object:
        if path == manifest:
            message = "injected research manifest status failure"
            raise PermissionError(message)
        return original_lstat(path)

    monkeypatch.setattr(Path, "lstat", fail_manifest_status)
    with pytest.raises(PermissionError, match="injected research manifest"):
        _ = research_layout.research_algorithm_directories(tmp_path)


def test_redirected_manifest_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Research manifest discovery never follows redirected evidence."""
    directory = _domain_root(tmp_path) / "candidate"
    directory.mkdir(parents=True)
    manifest = directory / "experiment.toml"
    _ = manifest.write_text("schema_version = 1\n", encoding="utf-8")
    original_is_junction = Path.is_junction

    def report_junction(path: Path) -> bool:
        if path == manifest:
            return True
        return original_is_junction(path)

    monkeypatch.setattr(Path, "is_junction", report_junction)
    with pytest.raises(OSError, match="must not redirect"):
        _ = research_layout.research_algorithm_directories(tmp_path)
