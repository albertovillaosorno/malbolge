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
#   - Concrete finite semantics for classic-verified-block-search-v1.
# - Must-Not:
#   - Trust search order, claim reusable-block equivalence, or execute unbounded
#     guest work.
# - Allows:
#   - Inputs: one exact candidate index in the complete two-byte graphical
#     corpus.
#   - Outputs: deterministic source bytes, workload hash, or verified quality.
#   - Side effects: none.
# - Split-When:
#   - A second challenge family or reusable internal-block semantics is added.
# - Merge-When:
#   - A shared challenge-corpus owner governs these exact classic semantics.
# - Summary:
#   - Exact two-word no-I/O halt pilot for superoptimization search ordering.
# - Description:
#   - Uses the independent bounded classic analyzer as acceptance authority.
# - Usage:
#   - Supply verified_quality to the preregistered comparison runner.
# - Defaults:
#   - Invalid candidates and unproved/unsafe traces are rejected as no result.
#

"""Concrete classic two-word pilot for the superoptimization research plan."""

from __future__ import annotations

from hashlib import sha256
import json
from typing import Final

from verifier import emitted_malbolge

_GRAPHICAL_START: Final = 33
_GRAPHICAL_VALUES: Final = 94
_SOURCE_WORDS: Final = 2
_STATUS_HALTED: Final = "halted"
_IO_INSTRUCTIONS: Final = frozenset((ord("<"), ord("/")))

CLASSIC_BLOCK_SEARCH_CHALLENGE_ID: Final = "classic-verified-block-search-v1"
CLASSIC_BLOCK_SEARCH_VERIFIER_ID: Final = "classic-two-word-no-io-halt-v1"
CLASSIC_BLOCK_SEARCH_CANDIDATE_ENCODING_ID: Final = (
    "lexicographic-two-graphical-bytes-v1"
)
CLASSIC_BLOCK_SEARCH_CANDIDATE_COUNT: Final = _GRAPHICAL_VALUES**_SOURCE_WORDS
CLASSIC_BLOCK_SEARCH_QUALITY_ID: Final = "semantic-transitions-to-halt-v1"


class InvalidClassicBlockCandidateError(ValueError):
    """Candidate index is outside the complete two-word graphical corpus."""


def candidate_source(candidate_index: int) -> bytes:
    """Return exact two-byte graphical source for one stable candidate index.

    Returns:
        Lexicographic base-94 source bytes spanning `33..126` at each position.

    Raises:
        InvalidClassicBlockCandidateError: If the index is outside the corpus.

    """
    if (
        type(candidate_index) is not int
        or not 0 <= candidate_index < CLASSIC_BLOCK_SEARCH_CANDIDATE_COUNT
    ):
        message = "candidate index must be in the complete two-word corpus"
        raise InvalidClassicBlockCandidateError(message)
    first, second = divmod(candidate_index, _GRAPHICAL_VALUES)
    return bytes((_GRAPHICAL_START + first, _GRAPHICAL_START + second))


def _halt_quality(report: emitted_malbolge.StaticImageReport) -> int | None:
    entry = report.entry_transition
    if not report.admitted_initial_image or entry is None or not entry.accepted:
        return None
    if entry.status == _STATUS_HALTED:
        return 1
    second = report.second_transition
    eligible_second = (
        entry.decoded_byte not in _IO_INSTRUCTIONS
        and second is not None
        and second.accepted
        and second.status == _STATUS_HALTED
    )
    return _SOURCE_WORDS if eligible_second else None


def verified_quality(candidate_index: int) -> int | None:
    """Return exact halt-step quality for one independently verified candidate.

    Returns:
        One for an immediate halt, two for a no-prior-I/O second-step halt, or
        `None` when the candidate is invalid, unresolved, unsafe, non-halting
        within the challenge horizon, or performs input/output before halting.

    """
    report = emitted_malbolge.analyze_source(candidate_source(candidate_index))
    return _halt_quality(report)


def workload_bytes() -> bytes:
    """Return canonical challenge identity bytes for recorded-run provenance.

    Returns:
        Stable UTF-8 JSON bytes with no environment or search-strategy fields.

    """
    document = {
        "candidate_count": CLASSIC_BLOCK_SEARCH_CANDIDATE_COUNT,
        "candidate_encoding": CLASSIC_BLOCK_SEARCH_CANDIDATE_ENCODING_ID,
        "challenge_id": CLASSIC_BLOCK_SEARCH_CHALLENGE_ID,
        "objective": "halt-without-prior-input-or-output",
        "profile": "malbolge-1998",
        "quality": CLASSIC_BLOCK_SEARCH_QUALITY_ID,
        "source_words": _SOURCE_WORDS,
        "verifier": CLASSIC_BLOCK_SEARCH_VERIFIER_ID,
    }
    text = json.dumps(document, sort_keys=True, separators=(",", ":"))
    return text.encode("utf-8")


def workload_sha256() -> str:
    """Return lowercase SHA-256 for the concrete challenge workload identity.

    Returns:
        Hex digest suitable for shared experiment run manifests.

    """
    return sha256(workload_bytes()).hexdigest()
