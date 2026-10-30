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


@pytest.fixture
def foreign_git_commit(tmp_path: Path) -> tuple[Path, str]:
    """Create an unrelated valid commit in a test-local Git object database.

    Returns:
        Its Git directory and SHA-1 commit identity.

    """
    git = shutil.which("git", path=os.defpath)
    assert git is not None
    foreign = tmp_path / "unrelated-repository"
    sp.run(
        [git, "-c", "init.defaultBranch=main", "init", "-q", str(foreign)],
        check=True,
        capture_output=True,
        timeout=5,
    )
    sp.run(
        [
            git,
            "-C",
            str(foreign),
            "-c",
            "commit.gpgsign=false",
            "-c",
            "user.name=Arena Test",
            "-c",
            "user.email=arena-test@example.invalid",
            "commit",
            "--allow-empty",
            "-qm",
            "unrelated commit",
        ],
        check=True,
        capture_output=True,
        timeout=5,
    )
    commit = sp.run(
        [git, "-C", str(foreign), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
        timeout=5,
    ).stdout.strip()
    assert len(commit) == 40
    return foreign / ".git", commit


@pytest.mark.skipif(
    shutil.which("git", path=os.defpath) is None,
    reason="requires a system-path Git executable",
)
def test_producers_ignore_ambient_git_directory(
    foreign_git_commit: tuple[Path, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Git revision provenance must not switch to the caller's foreign repo."""
    git_dir, foreign = foreign_git_commit
    git = shutil.which("git", path=os.defpath)
    assert git is not None
    expected = sp.run(
        [git, "rev-parse", "HEAD"],
        cwd=reference_study._ROOT,
        check=True,
        capture_output=True,
        text=True,
        timeout=5,
    ).stdout.strip()
    assert foreign != expected
    monkeypatch.setenv("GIT_DIR", str(git_dir))
    monkeypatch.setenv("GIT_WORK_TREE", str(git_dir.parent))
    assert reference_study._commit() == expected
    assert target_echo_reference._commit() == expected


@pytest.mark.parametrize("selector", ["GIT_DIR", "GIT_ALTERNATE_OBJECT_DIRECTORIES"])
@pytest.mark.skipif(
    shutil.which("git", path=os.defpath) is None,
    reason="requires a system-path Git executable",
)
def test_audits_refuse_ambient_foreign_git_objects(
    foreign_git_commit: tuple[Path, str],
    monkeypatch: pytest.MonkeyPatch,
    selector: str,
) -> None:
    """Repository and object-store selectors cannot forge local presence."""
    git_dir, foreign = foreign_git_commit
    source = git_dir if selector == "GIT_DIR" else git_dir / "objects"
    monkeypatch.setenv(selector, str(source))
    with pytest.raises(reference_audit.ReferenceAuditError, match="not a local Git"):
        reference_audit._require_git_commit(foreign)
    with pytest.raises(target_echo_audit.TargetEchoAuditError, match="not a local Git"):
        target_echo_audit._require_git_commit(foreign)
