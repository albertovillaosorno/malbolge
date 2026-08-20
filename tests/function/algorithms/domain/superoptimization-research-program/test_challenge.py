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
#   - Independent evidence for classic-verified-block-search-v1 semantics.
# - Must-Not:
#   - Use search order as acceptance or claim the pilot generalizes.
# - Allows:
#   - Inputs: every exact two-word graphical candidate index.
#   - Outputs: corpus identity, independent quality parity, and replay digests.
#   - Side effects: dynamic imports with temporary module search paths.
# - Split-When:
#   - Another concrete challenge family gains independent semantics.
# - Merge-When:
#   - A shared challenge-corpus test owns these exact verifier invariants.
# - Summary:
#   - Exhaustively verify the concrete classic superoptimization pilot.
# - Description:
#   - Recomputes admission from low-level classic transfer modules.
# - Usage:
#   - Collected by the research-algorithm Python test surface.
# - Defaults:
#   - Unknown, unsafe, I/O-producing, or non-halting candidates reject.
#

"""Independent exhaustive evidence for the concrete superoptimization pilot."""

from __future__ import annotations

from hashlib import sha256
import importlib
import importlib.util
from pathlib import Path
import sys
from typing import Protocol
from typing import cast

import pytest

_ROOT = Path(__file__).resolve().parents[5]
_CHALLENGE = _ROOT / (
    "src/research/algorithms/composition/algorithms/"
    "superoptimization/challenge.py"
)


class _EntryTransition(Protocol):
    accepted: bool
    status: str
    decoded_byte: int


class _SecondTransition(Protocol):
    accepted: bool
    status: str


class _ClassicModule(Protocol):
    def decode(self, value: int, position: int) -> int | None: ...


class _EntryModule(Protocol):
    def analyze_entry_transition(
        self,
        words: tuple[int, ...],
        decoded_byte: int,
    ) -> _EntryTransition: ...


class _PrefixModule(Protocol):
    def analyze_second_transition(
        self,
        words: tuple[int, ...],
        entry: _EntryTransition,
    ) -> _SecondTransition | None: ...


class _ChallengeModule(Protocol):
    CLASSIC_BLOCK_SEARCH_CANDIDATE_COUNT: int
    InvalidClassicBlockCandidateError: type[ValueError]

    def candidate_source(self, candidate_index: int) -> bytes: ...

    def verified_quality(self, candidate_index: int) -> int | None: ...

    def workload_bytes(self) -> bytes: ...

    def workload_sha256(self) -> str: ...


def _load_challenge() -> _ChallengeModule:
    spec = importlib.util.spec_from_file_location(
        "superoptimization_challenge_test",
        _CHALLENGE,
    )
    if spec is None or spec.loader is None:
        message = "superoptimization challenge module cannot be loaded"
        raise RuntimeError(message)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    sys.path.insert(0, str(_ROOT))
    try:
        spec.loader.exec_module(module)
    finally:
        _ = sys.path.pop(0)
    return cast("_ChallengeModule", cast("object", module))


_CHALLENGE_MODULE = _load_challenge()


def _load_reference_modules() -> tuple[
    _ClassicModule,
    _EntryModule,
    _PrefixModule,
]:
    sys.path.insert(0, str(_ROOT))
    try:
        classic_module = importlib.import_module(
            "verifier.emitted_malbolge_classic"
        )
        entry_module = importlib.import_module(
            "verifier.emitted_malbolge_entry"
        )
        prefix_module = importlib.import_module(
            "verifier.emitted_malbolge_prefix"
        )
    finally:
        _ = sys.path.pop(0)
    return (
        cast("_ClassicModule", cast("object", classic_module)),
        cast("_EntryModule", cast("object", entry_module)),
        cast("_PrefixModule", cast("object", prefix_module)),
    )


_CLASSIC, _ENTRY_TRANSFER, _PREFIX_TRANSFER = _load_reference_modules()

_GRAPHICAL_START = 33
_GRAPHICAL_VALUES = 94
_CANDIDATE_COUNT = 8_836
_ALLOWED_INSTRUCTIONS = frozenset(b"ji*p</vo")
_IO_INSTRUCTIONS = frozenset((ord("<"), ord("/")))
_STATUS_HALTED = "halted"
_ACCEPTED_COUNT = 10
_ONE_STEP_COUNT = 8
_TWO_STEP_COUNT = 2
_ONE_STEP_QUALITY = 1
_TWO_STEP_QUALITY = 2
_ACCEPTED_SHA256 = (
    "5aeb28c81b79e09c598688b289a11fa49e0163f5acb547abd0ec71514dd81529"
)
_WORKLOAD_SHA256 = (
    "eb739238b375fde435e3948896f385e6be9ab5002078b242c2826153ce1810fc"
)
_CANDIDATE_ERROR = "candidate index must be in the complete two-word corpus"
_FIRST_SOURCE = b"!!"
_LAST_FIRST_ROW_SOURCE = b"!~"
_SECOND_ROW_FIRST_SOURCE = b'"!'
_LAST_SOURCE = b"~~"
_CHALLENGE_MARKER = b'"challenge_id":"classic-verified-block-search-v1"'
_COUNT_MARKER = b'"candidate_count":8836'
_FORBIDDEN_WORKLOAD_MARKERS = (b"schedule", b"seed", b"host")


def _reference_source(candidate_index: int) -> bytes:
    first, second = divmod(candidate_index, _GRAPHICAL_VALUES)
    return bytes((_GRAPHICAL_START + first, _GRAPHICAL_START + second))


def _reference_quality(candidate_index: int) -> int | None:
    source = _reference_source(candidate_index)
    decoded = tuple(
        _CLASSIC.decode(source[position], position) for position in range(2)
    )
    if any(item not in _ALLOWED_INSTRUCTIONS for item in decoded):
        return None
    first = cast("int", decoded[0])
    entry = _ENTRY_TRANSFER.analyze_entry_transition(tuple(source), first)
    quality: int | None = None
    if entry.accepted:
        if entry.status == _STATUS_HALTED:
            quality = _ONE_STEP_QUALITY
        else:
            second = _PREFIX_TRANSFER.analyze_second_transition(
                tuple(source), entry
            )
            eligible_second = (
                entry.decoded_byte not in _IO_INSTRUCTIONS
                and second is not None
                and second.accepted
                and second.status == _STATUS_HALTED
            )
            if eligible_second:
                quality = _TWO_STEP_QUALITY
    return quality


def _accepted_results() -> tuple[tuple[int, int], ...]:
    accepted: list[tuple[int, int]] = []
    for candidate_index in range(_CANDIDATE_COUNT):
        observed = _CHALLENGE_MODULE.verified_quality(candidate_index)
        expected = _reference_quality(candidate_index)
        assert observed == expected
        if observed is not None:
            accepted.append((candidate_index, observed))
    return tuple(accepted)


def _accepted_digest(accepted: tuple[tuple[int, int], ...]) -> str:
    payload = "".join(
        f"{candidate_index}:{quality}\n"
        for candidate_index, quality in accepted
    ).encode("ascii")
    return sha256(payload).hexdigest()


def test_challenge_spans_complete_two_word_graphical_corpus() -> None:
    """Candidate encoding is a complete lexicographic 94-by-94 bijection."""
    assert (
        _CHALLENGE_MODULE.CLASSIC_BLOCK_SEARCH_CANDIDATE_COUNT
        == _CANDIDATE_COUNT
    )
    assert _CHALLENGE_MODULE.candidate_source(0) == _FIRST_SOURCE
    assert (
        _CHALLENGE_MODULE.candidate_source(_GRAPHICAL_VALUES - 1)
        == _LAST_FIRST_ROW_SOURCE
    )
    assert (
        _CHALLENGE_MODULE.candidate_source(_GRAPHICAL_VALUES)
        == _SECOND_ROW_FIRST_SOURCE
    )
    assert (
        _CHALLENGE_MODULE.candidate_source(_CANDIDATE_COUNT - 1)
        == _LAST_SOURCE
    )


@pytest.mark.parametrize("candidate_index", [-1, _CANDIDATE_COUNT, True])
def test_challenge_rejects_foreign_or_out_of_range_indices(
    candidate_index: object,
) -> None:
    """Candidate admission is exact and never wraps or accepts bool."""
    with pytest.raises(
        _CHALLENGE_MODULE.InvalidClassicBlockCandidateError,
        match=_CANDIDATE_ERROR,
    ):
        _ = _CHALLENGE_MODULE.candidate_source(cast("int", candidate_index))


def test_challenge_matches_independent_transfer_for_every_candidate() -> None:
    """Public quality agrees with independent transfer on the full corpus."""
    accepted = _accepted_results()
    assert len(accepted) == _ACCEPTED_COUNT
    assert (
        sum(quality == _ONE_STEP_QUALITY for _, quality in accepted)
        == _ONE_STEP_COUNT
    )
    assert (
        sum(quality == _TWO_STEP_QUALITY for _, quality in accepted)
        == _TWO_STEP_COUNT
    )
    assert _accepted_digest(accepted) == _ACCEPTED_SHA256


def test_workload_identity_is_canonical_and_search_order_independent() -> None:
    """Workload provenance excludes schedule, seed, and host identity."""
    payload = _CHALLENGE_MODULE.workload_bytes()
    assert _CHALLENGE_MODULE.workload_sha256() == _WORKLOAD_SHA256
    assert sha256(payload).hexdigest() == _WORKLOAD_SHA256
    assert _CHALLENGE_MARKER in payload
    assert _COUNT_MARKER in payload
    assert all(marker not in payload for marker in _FORBIDDEN_WORKLOAD_MARKERS)
