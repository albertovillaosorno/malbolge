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
#   - Concrete finite semantics for classic-three-word-verified-block-search-v1.
# - Must-Not:
#   - Define heuristic ordering, inspect search results, or execute unbounded
#     guest work.
# - Allows:
#   - Inputs: one exact candidate index in the complete three-byte graphical
#     corpus.
#   - Outputs: deterministic source bytes, workload identity, or verified
#     one-to-three-transition halt quality.
#   - Side effects: none.
# - Split-When:
#   - A different holdout language or objective gains independent semantics.
# - Merge-When:
#   - A shared challenge-corpus owner governs these exact classic semantics.
# - Summary:
#   - Exact three-word no-prior-I/O halt holdout for heuristic search.
# - Description:
#   - Uses low-level independent classic transfer as acceptance authority.
# - Usage:
#   - Supply verified_quality to the preregistered heuristic comparison only.
# - Defaults:
#   - Invalid, unresolved, unsafe, I/O-prior, or non-halting candidates reject.
#

"""Concrete three-word classic holdout for heuristic superoptimization."""

from __future__ import annotations

from hashlib import sha256
import json
from typing import Final

from verifier import emitted_malbolge_classic as classic
from verifier import emitted_malbolge_entry as entry_transfer
from verifier import emitted_malbolge_prefix as prefix_transfer

_GRAPHICAL_START: Final = 33
_GRAPHICAL_VALUES: Final = 94
_SOURCE_WORDS: Final = 3
_STATUS_HALTED: Final = "halted"
_ALLOWED_INSTRUCTIONS: Final = frozenset(b"ji*p</vo")
_IO_INSTRUCTIONS: Final = frozenset((ord("<"), ord("/")))
_OBJECTIVE: Final = (
    "halt-without-prior-input-or-output-within-three-transitions"
)

THREE_WORD_CHALLENGE_ID: Final = "classic-three-word-verified-block-search-v1"
THREE_WORD_VERIFIER_ID: Final = "classic-three-word-no-io-halt-v1"
THREE_WORD_CANDIDATE_ENCODING_ID: Final = (
    "lexicographic-three-graphical-bytes-v1"
)
THREE_WORD_CANDIDATE_COUNT: Final = _GRAPHICAL_VALUES**_SOURCE_WORDS
THREE_WORD_QUALITY_ID: Final = "semantic-transitions-to-halt-v1"
THREE_WORD_WORKLOAD_SHA256: Final = (
    "03276bbed2b81d90553fa9ddca6046602108f992c48520554651638c626409d4"
)


class InvalidThreeWordCandidateError(ValueError):
    """Candidate index is outside the complete three-word graphical corpus."""


def candidate_source(candidate_index: int) -> bytes:
    """Return exact three-byte graphical source for one stable candidate index.

    Returns:
        Lexicographic base-94 source bytes spanning `33..126` at each position.

    Raises:
        InvalidThreeWordCandidateError: If the index is outside the corpus.

    """
    if (
        type(candidate_index) is not int
        or not 0 <= candidate_index < THREE_WORD_CANDIDATE_COUNT
    ):
        message = "candidate index must be in the complete three-word corpus"
        raise InvalidThreeWordCandidateError(message)
    prefix, third = divmod(candidate_index, _GRAPHICAL_VALUES)
    first, second = divmod(prefix, _GRAPHICAL_VALUES)
    return bytes((
        _GRAPHICAL_START + first,
        _GRAPHICAL_START + second,
        _GRAPHICAL_START + third,
    ))


def _initial_decodes(source: bytes) -> tuple[int, int, int] | None:
    decoded = tuple(
        classic.decode(value, position) for position, value in enumerate(source)
    )
    if any(value not in _ALLOWED_INSTRUCTIONS for value in decoded):
        return None
    first, second, third = decoded
    if first is None or second is None or third is None:
        return None
    return first, second, third


def _continued_without_io(decoded_byte: int | None) -> bool:
    return decoded_byte is not None and decoded_byte not in _IO_INSTRUCTIONS


def _third_step_quality(
    words: tuple[int, ...],
    entry: entry_transfer.EntryTransition,
    second: prefix_transfer.SecondTransition,
) -> int | None:
    quality: int | None = None
    if _continued_without_io(second.decoded_byte):
        third = prefix_transfer.analyze_third_transition(words, entry, second)
        if (
            third is not None
            and third.accepted
            and third.status == _STATUS_HALTED
        ):
            quality = 3
    return quality


def _continuation_quality(
    words: tuple[int, ...],
    entry: entry_transfer.EntryTransition,
) -> int | None:
    quality: int | None = None
    second = prefix_transfer.analyze_second_transition(words, entry)
    if second is not None and second.accepted:
        if second.status == _STATUS_HALTED:
            quality = 2
        else:
            quality = _third_step_quality(words, entry, second)
    return quality


def verified_quality(candidate_index: int) -> int | None:
    """Return exact halt quality up to three transitions with no prior I/O.

    Returns:
        One, two, or three for an exact halt with no earlier input/output, or
        `None` when load admission or bounded transfer cannot prove that result.

    """
    quality: int | None = None
    source = candidate_source(candidate_index)
    decoded = _initial_decodes(source)
    if decoded is not None:
        words = tuple(source)
        entry = entry_transfer.analyze_entry_transition(words, decoded[0])
        if entry.accepted:
            if entry.status == _STATUS_HALTED:
                quality = 1
            elif _continued_without_io(entry.decoded_byte):
                quality = _continuation_quality(words, entry)
    return quality


def workload_bytes() -> bytes:
    """Return canonical workload identity bytes for the three-word holdout.

    Returns:
        Stable UTF-8 JSON with no heuristic, accepted-set, or host information.

    """
    document = {
        "candidate_count": THREE_WORD_CANDIDATE_COUNT,
        "candidate_encoding": THREE_WORD_CANDIDATE_ENCODING_ID,
        "challenge_id": THREE_WORD_CHALLENGE_ID,
        "objective": _OBJECTIVE,
        "profile": "malbolge-1998",
        "quality": THREE_WORD_QUALITY_ID,
        "source_words": _SOURCE_WORDS,
        "verifier": THREE_WORD_VERIFIER_ID,
    }
    text = json.dumps(document, sort_keys=True, separators=(",", ":"))
    return text.encode("utf-8")


def workload_sha256() -> str:
    """Return lowercase SHA-256 for the frozen three-word workload.

    Returns:
        Workload digest preregistered before holdout execution.

    """
    return sha256(workload_bytes()).hexdigest()
