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
#   - Independent per-trial SHA-256 policy-substitution regressions.
# - Must-Not:
#   - Authenticate manifest producers or real file-content provenance.
# - Allows:
#   - Inputs: direct bounded TOML manifests and injected analyzer policy drift.
#   - Outputs: native trial records or typed malformed-digest rejection.
#   - Side effects: test-local monkeypatches only.
# - Split-When:
#   - Different parser policy needs separately governed fixtures.
# - Merge-When:
#   - The arena per-trial manifest parser owns these negative tests.
# - Summary:
#   - Mutable analyzer constants cannot redefine canonical run digests.
# - Description:
#   - Red-first short and uppercase digest policy substitutions.
# - Usage:
#   - `pytest benchmarks/arena/tests/test_trial_runs.py`.
# - Defaults:
#   - Noncanonical SHA-256 digests fail closed.
#

"""Source-stable per-trial run digest policy regressions."""

# ruff: file-ignore[assert]

from __future__ import annotations

import pytest

from benchmarks.arena import analyze, trial_runs


def _manifest(digest: str) -> str:
    return f'[arena_trial]\nschema_version = 1\ntrial = 7\nraw_sha256 = "{digest}"\n'


def test_native_manifest_digest_is_accepted_without_policy_changes() -> None:
    """A canonical digest retains its exact parsed source identity."""
    digest = "a" * 64
    assert trial_runs.parse_trial_run(_manifest(digest)) == trial_runs.TrialRun(
        trial=7, raw_sha256=digest
    )


@pytest.mark.parametrize(
    ("policy", "digest"),
    [("length", "abc"), ("alphabet", "G" * 64)],
)
def test_mutable_analyzer_policy_cannot_admit_noncanonical_run_digest(
    monkeypatch: pytest.MonkeyPatch, policy: str, digest: str
) -> None:
    """A late-bound digest policy must not weaken canonical source admission."""
    with pytest.raises(trial_runs.TrialRunError, match="lowercase SHA-256"):
        _ = trial_runs.parse_trial_run(_manifest(digest))

    with monkeypatch.context() as patch:
        if policy == "length":
            patch.setattr(analyze, "SHA256_HEX_LENGTH", len(digest))
        else:
            patch.setattr(analyze, "SHA256_ALPHABET", frozenset("0123456789abcdefG"))
        with pytest.raises(trial_runs.TrialRunError, match="lowercase SHA-256"):
            _ = trial_runs.parse_trial_run(_manifest(digest))
