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
#   - Finite exact semantics for classic-history-residue-search-v1.
# - Must-Not:
#   - Own canonicalization policy, claim performance, or execute guest programs.
# - Allows:
#   - Inputs: one stable candidate index in the frozen history corpus.
#   - Outputs: exact history observation, semantic value, and workload identity.
#   - Side effects: none.
# - Split-When:
#   - Another history challenge gains independent candidate semantics.
# - Merge-When:
#   - A shared research challenge owner governs these exact histories.
# - Summary:
#   - Exact bounded history corpus for canonicalization research.
# - Description:
#   - Covers all graphical encryption starts plus deterministic rotate samples.
# - Usage:
#   - Supply observations and semantic_value to the history comparison runner.
# - Defaults:
#   - Foreign candidate indices and malformed observations fail closed.
#

"""Finite exact classic history corpus for canonicalization research."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Final

from verifier import emitted_malbolge_classic as classic

HISTORY_CHALLENGE_ID: Final = "classic-history-residue-search-v1"
HISTORY_VERIFIER_ID: Final = "classic-history-semantic-value-v1"
HISTORY_CANDIDATE_ENCODING_ID: Final = (
    "encryption-94x70-plus-rotate-171x20-v1"
)
HISTORY_PROFILE_ID: Final = "malbolge-1998"

KIND_ENCRYPTION: Final = "self-encryption"
KIND_ROTATE: Final = "rotate"

_GRAPHICAL_START: Final = 33
_GRAPHICAL_COUNT: Final = 94
_ENCRYPTION_VISITS: Final = 70
_ENCRYPTION_CANDIDATES: Final = _GRAPHICAL_COUNT * _ENCRYPTION_VISITS
_ROTATE_SAMPLE_COUNT: Final = 171
_ROTATE_VISITS: Final = 20
_ROTATE_CANDIDATES: Final = _ROTATE_SAMPLE_COUNT * _ROTATE_VISITS
_CLASSIC_MAX_WORD: Final = 59_048
_ROTATE_SAMPLE_DENOMINATOR: Final = _ROTATE_SAMPLE_COUNT - 1

HISTORY_CANDIDATE_COUNT: Final = _ENCRYPTION_CANDIDATES + _ROTATE_CANDIDATES


class InvalidHistoryChallengeCandidateError(ValueError):
    """Candidate or observation is outside the frozen history challenge."""


@dataclass(frozen=True, slots=True)
class HistoryObservation:
    """One exact repeated-operation history from the frozen finite corpus."""

    kind: str
    subject: int
    visits: int


def _rotate_sample(sample_index: int) -> int:
    return (sample_index * _CLASSIC_MAX_WORD) // _ROTATE_SAMPLE_DENOMINATOR


def candidate_observation(candidate_index: int) -> HistoryObservation:
    """Return one stable history observation from the 10,000-item corpus.

    Returns:
        Encryption observations first, then deterministic rotate observations.

    Raises:
        InvalidHistoryChallengeCandidateError: If the index is not exact or is
            outside the frozen corpus.

    """
    if (
        type(candidate_index) is not int
        or not 0 <= candidate_index < HISTORY_CANDIDATE_COUNT
    ):
        message = "history candidate index must be in the frozen corpus"
        raise InvalidHistoryChallengeCandidateError(message)
    if candidate_index < _ENCRYPTION_CANDIDATES:
        start_offset, visits = divmod(candidate_index, _ENCRYPTION_VISITS)
        return HistoryObservation(
            kind=KIND_ENCRYPTION,
            subject=_GRAPHICAL_START + start_offset,
            visits=visits,
        )
    rotate_index = candidate_index - _ENCRYPTION_CANDIDATES
    sample_index, visits = divmod(rotate_index, _ROTATE_VISITS)
    return HistoryObservation(
        kind=KIND_ROTATE,
        subject=_rotate_sample(sample_index),
        visits=visits,
    )


def encryption_successor(cell: int) -> int | None:
    """Return the repository classic verifier's exact encryption successor.

    Returns:
        Graphical successor, or ``None`` outside the classic table domain.

    """
    return classic.encrypt(cell)


def _validate_observation(observation: HistoryObservation) -> None:
    if type(observation) is not HistoryObservation:
        message = "history observation must use the exact immutable type"
        raise InvalidHistoryChallengeCandidateError(message)
    if observation.kind == KIND_ENCRYPTION:
        valid_subject = _GRAPHICAL_START <= observation.subject < (
            _GRAPHICAL_START + _GRAPHICAL_COUNT
        )
        valid_visits = 0 <= observation.visits < _ENCRYPTION_VISITS
    elif observation.kind == KIND_ROTATE:
        valid_subject = 0 <= observation.subject <= _CLASSIC_MAX_WORD
        valid_visits = 0 <= observation.visits < _ROTATE_VISITS
    else:
        valid_subject = False
        valid_visits = False
    exact_dimensions = (
        type(observation.subject) is int and type(observation.visits) is int
    )
    if not exact_dimensions or not valid_subject or not valid_visits:
        message = "history observation is outside the frozen challenge domain"
        raise InvalidHistoryChallengeCandidateError(message)


def semantic_value(observation: HistoryObservation) -> int:
    """Return the exact value after the observation's committed visit history.

    Returns:
        Final graphical code cell or classic ten-trit data word.

    Raises:
        InvalidHistoryChallengeCandidateError: If the observation is foreign or
            the classic encryption successor unexpectedly leaves its domain.

    """
    _validate_observation(observation)
    value = observation.subject
    if observation.kind == KIND_ENCRYPTION:
        for _ in range(observation.visits):
            following = encryption_successor(value)
            if following is None:
                message = "classic encryption left the graphical domain"
                raise InvalidHistoryChallengeCandidateError(message)
            value = following
        return value
    for _ in range(observation.visits):
        value = classic.rotate(value)
    return value


def workload_bytes() -> bytes:
    """Return canonical workload identity bytes for the frozen history corpus.

    Returns:
        Stable UTF-8 JSON excluding strategy, host, and measurement identity.

    """
    document = {
        "candidate_count": HISTORY_CANDIDATE_COUNT,
        "candidate_encoding": HISTORY_CANDIDATE_ENCODING_ID,
        "challenge_id": HISTORY_CHALLENGE_ID,
        "encryption_starts": _GRAPHICAL_COUNT,
        "encryption_visits_per_start": _ENCRYPTION_VISITS,
        "profile": HISTORY_PROFILE_ID,
        "rotate_sample_count": _ROTATE_SAMPLE_COUNT,
        "rotate_sample_rule": "floor(index*59048/170)",
        "rotate_visits_per_sample": _ROTATE_VISITS,
        "verifier": HISTORY_VERIFIER_ID,
    }
    text = json.dumps(document, sort_keys=True, separators=(",", ":"))
    return text.encode("utf-8")


def workload_sha256() -> str:
    """Return lowercase SHA-256 for the frozen history workload identity.

    Returns:
        Hex digest suitable for preregistered workload binding.

    """
    return sha256(workload_bytes()).hexdigest()
