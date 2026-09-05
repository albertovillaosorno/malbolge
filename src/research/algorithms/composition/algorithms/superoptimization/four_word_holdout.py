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
#   - Frozen four-word holdout mapping and independent bounded verifier.
# - Must-Not:
#   - Define learned/static search order or consume holdout search outcomes.
# - Allows:
#   - Inputs: one ordinal in the preregistered 100,000-candidate holdout.
#   - Outputs: source/raw-index/workload identity or verified halt quality.
#   - Side effects: none.
# - Split-When:
#   - Another holdout selection rule or objective gains independent semantics.
# - Merge-When:
#   - A shared challenge owner governs this exact four-word corpus.
# - Summary:
#   - Deterministic four-word learned-guidance holdout with exact verification.
# - Description:
#   - Excludes only training-positive prefixes before bounded four-step checks.
# - Usage:
#   - Search runners receive verified_quality only after experiment
#     registration.
# - Defaults:
#   - Invalid, unresolved, I/O-prior, or non-halting candidates reject.
#

"""Frozen four-word holdout for training-only learned guidance."""

from __future__ import annotations

from hashlib import sha256
import json
from typing import Final
from typing import cast

from verifier import emitted_malbolge_classic as classic
from verifier import emitted_malbolge_entry as entry_transfer
from verifier import emitted_malbolge_prefix as prefix_transfer

_GRAPHICAL_START: Final = 33
_GRAPHICAL_VALUES: Final = 94
_SOURCE_WORDS: Final = 4
_STATUS_HALTED: Final = "halted"
_ALLOWED_INSTRUCTIONS: Final = frozenset(b"ji*p</vo")
_IO_INSTRUCTIONS: Final = frozenset((ord("<"), ord("/")))
_SELECTION_STRIDE: Final = 104_729
_SELECTION_OFFSET: Final = 0
_FULL_CANDIDATE_COUNT: Final = _GRAPHICAL_VALUES**_SOURCE_WORDS
_OBJECTIVE: Final = "halt-without-prior-input-or-output-within-four-transitions"
_TRAINING_POSITIVE_PREFIXES: Final = frozenset((
    62368, 62462, 64530, 65094, 66274, 66275, 66297, 66303, 66316, 66333,
    66334, 66352, 309870, 312502, 313682, 313683, 313705, 313711, 313724,
    313741, 313742, 313760, 424602, 424603, 424625, 424631, 424644,
    424661, 424662, 424680, 424696, 424697, 424719, 424725, 424738,
    424755, 424756, 424774, 426764, 426765, 426787, 426793, 426806,
    426823, 426824, 426842, 427328, 427329, 427351, 427357, 427370,
    427387, 427388, 427406, 428550, 428551, 428573, 428579, 428592,
    428609, 428610, 428628, 430148, 430149, 430171, 430177, 430190,
    430207, 430208, 430226, 430242, 430243, 430265, 430271, 430284,
    430301, 430302, 430320, 431934, 431935, 431957, 431963, 431976,
    431993, 431994, 432012,
))

HOLDOUT_CHALLENGE_ID: Final = "classic-four-word-learned-guidance-holdout-v1"
HOLDOUT_VERIFIER_ID: Final = "classic-four-word-no-io-halt-v1"
HOLDOUT_ENCODING_ID: Final = (
    "affine-four-graphical-bytes-excluding-training-positive-prefix-v1"
)
HOLDOUT_CANDIDATE_COUNT: Final = 100_000
HOLDOUT_SELECTED_INDEX_SHA256: Final = (
    "28f8e60161e71c364702a2fd3618c333e82aff17df737a9c8709ea97080a99d4"
)
HOLDOUT_WORKLOAD_SHA256: Final = (
    "54edc48898f06d1652150e5defb80ffce9e98a386cf5d07615c8182cdde33fcc"
)
TRAINING_ACCEPTED_SET_SHA256: Final = (
    "35d107f544fbd71b0008d1414fa4c73677e9d3d15c32e6494a09bd89e2667342"
)


class InvalidFourWordHoldoutCandidateError(ValueError):
    """Candidate ordinal is outside the frozen learned-guidance holdout."""


def _selected_raw_indices() -> tuple[int, ...]:
    selected: list[int] = []
    ordinal = 0
    while len(selected) < HOLDOUT_CANDIDATE_COUNT:
        raw_index = (
            _SELECTION_OFFSET + ordinal * _SELECTION_STRIDE
        ) % _FULL_CANDIDATE_COUNT
        training_prefix = raw_index // _GRAPHICAL_VALUES
        if training_prefix not in _TRAINING_POSITIVE_PREFIXES:
            selected.append(raw_index)
        ordinal += 1
    return tuple(selected)


_SELECTED_RAW_INDICES: Final = _selected_raw_indices()


def raw_candidate_index(candidate_ordinal: int) -> int:
    """Return the full 94^4 raw index for one frozen holdout ordinal.

    Returns:
        Full-corpus raw candidate index.

    Raises:
        InvalidFourWordHoldoutCandidateError: If ordinal is outside holdout.

    """
    if (
        type(candidate_ordinal) is not int
        or not 0 <= candidate_ordinal < HOLDOUT_CANDIDATE_COUNT
    ):
        message = "candidate ordinal must be in the frozen four-word holdout"
        raise InvalidFourWordHoldoutCandidateError(message)
    return _SELECTED_RAW_INDICES[candidate_ordinal]


def candidate_source(candidate_ordinal: int) -> bytes:
    """Return exact four-byte graphical source for one holdout ordinal.

    Returns:
        Four graphical classic source bytes.

    """
    raw = raw_candidate_index(candidate_ordinal)
    prefix, fourth = divmod(raw, _GRAPHICAL_VALUES)
    prefix, third = divmod(prefix, _GRAPHICAL_VALUES)
    first, second = divmod(prefix, _GRAPHICAL_VALUES)
    return bytes((
        _GRAPHICAL_START + first,
        _GRAPHICAL_START + second,
        _GRAPHICAL_START + third,
        _GRAPHICAL_START + fourth,
    ))


def _initial_decodes(source: bytes) -> tuple[int, int, int, int] | None:
    decoded = tuple(
        classic.decode(value, position) for position, value in enumerate(source)
    )
    if any(value not in _ALLOWED_INSTRUCTIONS for value in decoded):
        return None
    if any(item is None for item in decoded):
        return None
    return cast("tuple[int, int, int, int]", decoded)


def _continued_without_io(decoded_byte: int | None) -> bool:
    return decoded_byte is not None and decoded_byte not in _IO_INSTRUCTIONS


def _fourth_quality(
    words: tuple[int, ...],
    entry: entry_transfer.EntryTransition,
    second: prefix_transfer.SecondTransition,
    *,
    third: prefix_transfer.SecondTransition,
) -> int | None:
    if not _continued_without_io(third.decoded_byte):
        return None
    fourth = prefix_transfer.analyze_fourth_transition(
        words,
        entry,
        second,
        third=third,
    )
    if (
        fourth is not None
        and fourth.accepted
        and fourth.status == _STATUS_HALTED
    ):
        return 4
    return None


def _third_or_fourth_quality(
    words: tuple[int, ...],
    entry: entry_transfer.EntryTransition,
    second: prefix_transfer.SecondTransition,
) -> int | None:
    quality: int | None = None
    if _continued_without_io(second.decoded_byte):
        third = prefix_transfer.analyze_third_transition(words, entry, second)
        if third is not None and third.accepted:
            if third.status == _STATUS_HALTED:
                quality = 3
            else:
                quality = _fourth_quality(
                    words,
                    entry,
                    second,
                    third=third,
                )
    return quality


def _continuation_quality(
    words: tuple[int, ...],
    entry: entry_transfer.EntryTransition,
) -> int | None:
    second = prefix_transfer.analyze_second_transition(words, entry)
    if second is None or not second.accepted:
        return None
    if second.status == _STATUS_HALTED:
        return 2
    return _third_or_fourth_quality(words, entry, second)


def verified_quality(candidate_ordinal: int) -> int | None:
    """Return one-to-four-step halt quality with no prior input/output.

    Returns:
        Exact transition count to halt, or ``None`` when not proved eligible.

    """
    quality: int | None = None
    source = candidate_source(candidate_ordinal)
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


def selected_index_sha256() -> str:
    """Return exact SHA-256 of newline-delimited selected raw indices.

    Returns:
        Lowercase selected-index digest.

    """
    payload = "".join(f"{index}\n" for index in _SELECTED_RAW_INDICES)
    return sha256(payload.encode("ascii")).hexdigest()


def workload_bytes() -> bytes:
    """Return canonical workload bytes without holdout outcomes.

    Returns:
        Stable JSON workload identity bytes.

    """
    document = {
        "candidate_encoding": HOLDOUT_ENCODING_ID,
        "challenge_id": HOLDOUT_CHALLENGE_ID,
        "full_candidate_count": _FULL_CANDIDATE_COUNT,
        "holdout_candidate_count": HOLDOUT_CANDIDATE_COUNT,
        "objective": _OBJECTIVE,
        "profile": "malbolge-1998",
        "quality": "semantic-transitions-to-halt-v1",
        "selected_index_sha256": HOLDOUT_SELECTED_INDEX_SHA256,
        "selection_offset": _SELECTION_OFFSET,
        "selection_stride": _SELECTION_STRIDE,
        "source_words": _SOURCE_WORDS,
        "training_accepted_set_sha256": TRAINING_ACCEPTED_SET_SHA256,
        "training_challenge_id": "classic-three-word-verified-block-search-v1",
        "verifier": HOLDOUT_VERIFIER_ID,
    }
    return json.dumps(document, sort_keys=True, separators=(",", ":")).encode()


def workload_sha256() -> str:
    """Return exact preregistered holdout workload digest.

    Returns:
        Lowercase SHA-256 workload identity.

    """
    return sha256(workload_bytes()).hexdigest()
