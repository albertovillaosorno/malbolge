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
#   - Pre-holdout execution evidence for model, mapping, schedules, and runner.
# - Must-Not:
#   - Invoke the real four-word holdout verifier or record holdout outcomes.
# - Allows:
#   - Inputs: frozen training labels, holdout mapping, and synthetic callbacks.
#   - Outputs: identity/hash/model/order/fail-closed assertions.
#   - Side effects: training verifier calls during model fitting only.
# - Split-When:
#   - Another learned model or holdout gains independent execution evidence.
# - Merge-When:
#   - One suite owns this exact learned-guidance substrate.
# - Summary:
#   - Validate learned-guidance mechanics without observing holdout results.
# - Description:
#   - Proves training-only fit and deterministic schedule/runner behavior.
# - Usage:
#   - Run before registering and executing the real holdout comparison.
# - Defaults:
#   - Real holdout verifier remains outside this module.
#

"""Pre-execution tests for the learned-guidance comparison substrate."""

from hashlib import sha256
from typing import cast

from algorithms.superoptimization import four_word_holdout as holdout
from algorithms.superoptimization import learned_guidance as guidance
from algorithms.superoptimization import learned_guidance_runner as runner
import pytest

_EXPECTED_SELECTED_SHA = holdout.HOLDOUT_SELECTED_INDEX_SHA256
_EXPECTED_WORKLOAD_SHA = holdout.HOLDOUT_WORKLOAD_SHA256
_EXPECTED_TRAINING_ACCEPTED = 86
_BUDGET = 50_000
_SYNTHETIC_HIT = 7
_SYNTHETIC_QUALITY = 2
_SOURCE_WORDS = 4
_QUALITY_ERROR = "verifier quality is malformed"


def test_holdout_mapping_matches_preregistered_hashes(
) -> None:
    """Selection and workload bytes close before any holdout outcome exists."""
    payload = "".join(
        f"{holdout.raw_candidate_index(i)}\n"
        for i in range(holdout.HOLDOUT_CANDIDATE_COUNT)
    ).encode("ascii")
    assert sha256(payload).hexdigest() == _EXPECTED_SELECTED_SHA
    assert holdout.selected_index_sha256() == _EXPECTED_SELECTED_SHA
    assert holdout.workload_sha256() == _EXPECTED_WORKLOAD_SHA
    assert len(holdout.candidate_source(0)) == _SOURCE_WORDS


def test_model_fit_uses_registered_training_only() -> None:
    """Training labels deterministically produce one finite integer model."""
    model = guidance.fit_model()
    assert model.model_id == guidance.MODEL_ID
    assert model.accepted_candidate_count == _EXPECTED_TRAINING_ACCEPTED
    assert model.training_candidate_count > _BUDGET
    assert model.token_weights
    assert all(weight >= 0 for _, weight in model.token_weights)


def test_static_and_learned_orders_are_unique_fixed_budget() -> None:
    """Both schedules are deterministic unique prefixes of equal cardinality."""
    model = guidance.fit_model()
    static = guidance.static_order()
    learned = guidance.learned_order(model)
    assert len(static) == _BUDGET == len(set(static))
    assert len(learned) == _BUDGET == len(set(learned))
    assert static == guidance.static_order()
    assert learned == guidance.learned_order(model)


class _Clock:
    def __init__(self) -> None:
        self.value: int = 0

    def __call__(self) -> int:
        self.value += 10
        return self.value


def _synthetic_verifier(candidate: int) -> int | None:
    return _SYNTHETIC_QUALITY if candidate == _SYNTHETIC_HIT else None


def test_runner_acceptance_comes_only_from_injected_verifier(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Synthetic schedules can reorder work but never manufacture acceptance."""
    monkeypatch.setattr(guidance, "static_order", lambda: tuple(range(_BUDGET)))

    def learned_order(_model: guidance.LearnedDecodeModel) -> tuple[int, ...]:
        del _model
        return (
            _SYNTHETIC_HIT,
            *range(_SYNTHETIC_HIT),
            *range(_SYNTHETIC_HIT + 1, _BUDGET),
        )

    monkeypatch.setattr(guidance, "learned_order", learned_order)
    baseline = runner.run_static(_synthetic_verifier, _Clock())
    learned = runner.run_learned(_synthetic_verifier, _Clock())
    assert baseline.evaluations == _SYNTHETIC_HIT + 1
    assert learned.evaluations == 1
    assert baseline.quality == learned.quality == _SYNTHETIC_QUALITY


@pytest.mark.parametrize("bad", [-1, 0, 5, True, "1"])
def test_runner_rejects_malformed_quality(
    bad: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Only exact one-through-four quality values can become search success."""
    monkeypatch.setattr(guidance, "static_order", lambda: tuple(range(_BUDGET)))

    def bad_verifier(candidate: int) -> int:
        del candidate
        return cast("int", bad)

    with pytest.raises(
        runner.LearnedGuidanceComparisonError,
        match=_QUALITY_ERROR,
    ):
        _ = runner.run_static(bad_verifier, _Clock())
