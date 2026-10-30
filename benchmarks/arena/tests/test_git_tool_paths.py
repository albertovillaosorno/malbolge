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
#   - Hostile search path tests for offline research Git provenance.
# - Must-Not:
#   - Confuse local Git object presence with historic execution attestation.
# - Allows:
#   - Inputs: temporary fake Git programs and the local system Git repository.
#   - Outputs: rejection of forged commits and original local source identity.
#   - Side effects: temporary fake executable, real read-only Git invocations.
# - Split-When:
#   - Git provenance helpers gain a shared executable resolution adapter.
# - Merge-When:
#   - All research producers use independently authenticated source provenance.
# - Summary:
#   - Prevents fake PATH git tools from forging revision and object evidence.
# - Description:
#   - Exercises two source producers and two local commit-object audit gates.
# - Usage:
#   - pytest benchmarks/arena/tests/test_git_tool_paths.py.
# - Defaults:
#   - Only system-path Git can establish a local object existence claim.
#

"""A caller-controlled PATH cannot impersonate Git source revision evidence."""

# ruff: file-ignore[assert,private-member-access]

from __future__ import annotations

import os
import shutil
import subprocess as sp  # ruff: ignore[suspicious-subprocess-import]
from pathlib import Path

import pytest

from benchmarks.arena import (
    reference_audit,
    reference_study,
    target_echo_audit,
    target_echo_reference,
)

FORGED_SHA1 = "a" * 40


@pytest.fixture
def poisoned_git_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Supply an executable that claims any Git revision or object exists."""
    fake = tmp_path / "git"
    fake.write_text(
        "#!/bin/sh\n"
        "case \"$1\" in\n"
        f"  rev-parse) printf '{FORGED_SHA1}\\n';;\n"
        "  cat-file) printf 'commit\\n';;\n"
        "esac\n",
        encoding="ascii",
    )
    fake.chmod(0o700)
    monkeypatch.setenv("PATH", str(tmp_path))


@pytest.mark.skipif(
    shutil.which("git", path=os.defpath) is None,
    reason="requires a system-path Git executable",
)
def test_producers_ignore_fake_git_revision(poisoned_git_path: None) -> None:
    """Recorded source SHA-1 must come from the real local repo HEAD."""
    _ = poisoned_git_path
    git = shutil.which("git", path=os.defpath)
    assert git is not None
    expected = sp.run(
        [git, "rev-parse", "HEAD"],
        cwd=reference_study._ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert expected != FORGED_SHA1
    assert reference_study._commit() == expected
    assert target_echo_reference._commit() == expected


@pytest.mark.skipif(
    shutil.which("git", path=os.defpath) is None,
    reason="requires a system-path Git executable",
)
def test_audits_refuse_fake_git_commit_object(poisoned_git_path: None) -> None:
    """An invented object cannot become 'commit' via a PATH impostor."""
    _ = poisoned_git_path
    with pytest.raises(reference_audit.ReferenceAuditError, match="not a local Git"):
        reference_audit._require_git_commit(FORGED_SHA1)
    with pytest.raises(target_echo_audit.TargetEchoAuditError, match="not a local Git"):
        target_echo_audit._require_git_commit(FORGED_SHA1)
    actual = reference_study._commit()
    reference_audit._require_git_commit(actual)
    target_echo_audit._require_git_commit(actual)
