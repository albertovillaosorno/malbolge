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
#   - Training-only pooled decode model and static/learned holdout schedules.
# - Must-Not:
#   - Call the four-word holdout verifier or consume holdout outcomes.
# - Allows:
#   - Inputs: registered three-word training labels and holdout source bytes.
#   - Outputs: deterministic model weights and candidate orders.
#   - Side effects: invokes only the registered training verifier during fit.
# - Split-When:
#   - Another learned feature/model family gains independent policy.
# - Merge-When:
#   - A shared guidance owner governs this exact model and schedule pair.
# - Summary:
#   - Fit pooled initial-decode acceptance weights on training only.
# - Description:
#   - Compare learned token weights with the existing static halt feature.
# - Usage:
#   - Runners fit from scratch before learned holdout search.
# - Defaults:
#   - Integer smoothing and ordinal tie-breaks keep ordering deterministic.
#

"""Training-only learned guidance for the preregistered four-word holdout."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Final

from algorithms.superoptimization import four_word_holdout as holdout
from algorithms.superoptimization import three_word_challenge as training

from verifier import emitted_malbolge_classic as classic

MODEL_ID: Final = "laplace-pooled-initial-decode-guidance-v1"
LEARNED_ORDER_ID: Final = "laplace-pooled-initial-decode-guidance-order-v1"
STATIC_ORDER_ID: Final = "four-word-static-initial-decode-order-v1"
EVALUATION_BUDGET: Final = 50_000
_INVALID_TOKEN: Final = -1
_SCALE: Final = 1_000_000
_HALT: Final = ord("v")


@dataclass(frozen=True, slots=True)
class LearnedDecodeModel:
    """Exact integer token weights learned from the three-word training set."""

    model_id: str
    token_weights: tuple[tuple[int, int], ...]
    training_candidate_count: int
    accepted_candidate_count: int

    def weight(self, token: int) -> int:
        """Return the fitted weight for one initial-decode token.

        Returns:
            Deterministic scaled integer acceptance weight.

        """
        return dict(self.token_weights)[token]


def _decode_token(value: int, position: int) -> int:
    decoded = classic.decode(value, position)
    return _INVALID_TOKEN if decoded is None else decoded


def fit_model() -> LearnedDecodeModel:
    """Fit preregistered Laplace-smoothed pooled token weights from training.

    Returns:
        Deterministic training-only integer decode model.

    """
    total: Counter[int] = Counter()
    accepted: Counter[int] = Counter()
    accepted_candidates = 0
    for candidate in range(training.THREE_WORD_CANDIDATE_COUNT):
        source = training.candidate_source(candidate)
        tokens = tuple(
            _decode_token(value, position)
            for position, value in enumerate(source)
        )
        total.update(tokens)
        if training.verified_quality(candidate) is not None:
            accepted_candidates += 1
            accepted.update(tokens)
    weights = tuple(sorted(
        (
            token,
            ((accepted[token] + 1) * _SCALE) // (count + 2),
        )
        for token, count in total.items()
    ))
    return LearnedDecodeModel(
        MODEL_ID,
        weights,
        training.THREE_WORD_CANDIDATE_COUNT,
        accepted_candidates,
    )


def _holdout_tokens(candidate: int) -> tuple[int, ...]:
    source = holdout.candidate_source(candidate)
    return tuple(
        _decode_token(value, position) for position, value in enumerate(source)
    )


def learned_score(candidate: int, model: LearnedDecodeModel) -> int:
    """Return summed learned token weight for one holdout candidate.

    Returns:
        Sum of fitted token weights across four initial decodes.

    """
    return sum(model.weight(token) for token in _holdout_tokens(candidate))


def static_score(candidate: int) -> int:
    """Return earliest initial halt-decode position, or four when absent.

    Returns:
        Zero through three for earliest halt token, otherwise four.

    """
    score = 4
    for position, token in enumerate(_holdout_tokens(candidate)):
        if token == _HALT:
            score = position
            break
    return score


def static_order() -> tuple[int, ...]:
    """Return the best registered non-learned static holdout prefix.

    Returns:
        Fixed-budget candidate ordinals sorted by static score then ordinal.

    """
    return tuple(sorted(
        range(holdout.HOLDOUT_CANDIDATE_COUNT),
        key=lambda candidate: (static_score(candidate), candidate),
    )[:EVALUATION_BUDGET])


def learned_order(model: LearnedDecodeModel) -> tuple[int, ...]:
    """Return training-only learned holdout prefix by descending score.

    Returns:
        Fixed-budget candidate ordinals sorted by learned score then ordinal.

    """
    return tuple(sorted(
        range(holdout.HOLDOUT_CANDIDATE_COUNT),
        key=lambda candidate: (-learned_score(candidate, model), candidate),
    )[:EVALUATION_BUDGET])
