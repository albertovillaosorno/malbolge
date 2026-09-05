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
#   - Independent characterization of the preregistered three-word holdout.
# - Must-Not:
#   - Define heuristic order or treat characterization as search evidence.
# - Allows:
#   - Inputs: every candidate plus the high-level bounded static analyzer.
#   - Outputs: encoding, workload, accepted-set, and quality parity evidence.
#   - Side effects: none.
# - Split-When:
#   - A new holdout verifier needs independent characterization.
# - Merge-When:
#   - One test owns this exact three-word challenge identity.
# - Summary:
#   - Characterize the holdout only after its experiment was preregistered.
# - Description:
#   - Cross-checks every load-admitted source against bounded static analysis.
# - Usage:
#   - Run after preregistration commit f92a6ef4 or later descendants.
# - Defaults:
#   - Search ordering is never consulted by this characterization.
#

"""Independent evidence for the preregistered three-word classic holdout."""

from hashlib import sha256
from typing import cast

from algorithms.superoptimization import three_word_challenge as challenge
import pytest

from verifier import emitted_malbolge
from verifier import emitted_malbolge_classic as classic

_GRAPHICAL_START = 33
_GRAPHICAL_VALUES = 94
_CANDIDATES = 830_584
_ALLOWED = frozenset(b"ji*p</vo")
_IO = frozenset((ord("<"), ord("/")))
_HALTED = "halted"
_WORKLOAD_SHA256 = (
    "03276bbed2b81d90553fa9ddca6046602108f992c48520554651638c626409d4"
)
_ACCEPTED_COUNT = 86
_QUALITY_COUNTS = {1: 64, 2: 16, 3: 6}
_ACCEPTED_SHA256 = (
    "35d107f544fbd71b0008d1414fa4c73677e9d3d15c32e6494a09bd89e2667342"
)
_FIRST_SOURCE = b"!!!"
_LAST_FIRST_ROW_SOURCE = b"!!~"
_SECOND_ROW_FIRST_SOURCE = b'!"!'
_LAST_SOURCE = b"~~~"
_CANDIDATE_ERROR = "candidate index must be in the complete three-word corpus"


def _source(index: int) -> bytes:
    prefix, third = divmod(index, _GRAPHICAL_VALUES)
    first, second = divmod(prefix, _GRAPHICAL_VALUES)
    return bytes((
        _GRAPHICAL_START + first,
        _GRAPHICAL_START + second,
        _GRAPHICAL_START + third,
    ))


def _initially_admitted(source: bytes) -> bool:
    return all(
        classic.decode(value, position) in _ALLOWED
        for position, value in enumerate(source)
    )


def _report_third_quality(
    report: emitted_malbolge.StaticImageReport,
) -> int | None:
    quality: int | None = None
    third = report.third_transition
    if third is not None and third.accepted and third.status == _HALTED:
        quality = 3
    return quality


def _report_continuation_quality(
    report: emitted_malbolge.StaticImageReport,
) -> int | None:
    quality: int | None = None
    second = report.second_transition
    if second is not None and second.accepted:
        if second.status == _HALTED:
            quality = 2
        elif second.decoded_byte not in _IO:
            quality = _report_third_quality(report)
    return quality


def _report_quality(source: bytes) -> int | None:
    quality: int | None = None
    report = emitted_malbolge.analyze_source(source, transition_limit=3)
    entry = report.entry_transition
    if report.admitted_initial_image and entry is not None:
        if entry.status == _HALTED:
            quality = 1
        elif entry.decoded_byte not in _IO:
            quality = _report_continuation_quality(report)
    return quality


def _accepted() -> tuple[tuple[int, int], ...]:
    accepted: list[tuple[int, int]] = []
    for index in range(_CANDIDATES):
        source = _source(index)
        quality = challenge.verified_quality(index)
        if _initially_admitted(source):
            assert quality == _report_quality(source)
        else:
            assert quality is None
        if quality is not None:
            accepted.append((index, quality))
    return tuple(accepted)


def _digest(accepted: tuple[tuple[int, int], ...]) -> str:
    payload = "".join(
        f"{index}:{quality}\n" for index, quality in accepted
    ).encode("ascii")
    return sha256(payload).hexdigest()


def test_three_word_candidate_encoding_is_complete_lexicographic_bijection(
) -> None:
    """Stable base-94 indexing covers all and only graphical triples."""
    assert challenge.THREE_WORD_CANDIDATE_COUNT == _CANDIDATES
    assert challenge.candidate_source(0) == _FIRST_SOURCE
    assert (
        challenge.candidate_source(_GRAPHICAL_VALUES - 1)
        == _LAST_FIRST_ROW_SOURCE
    )
    assert (
        challenge.candidate_source(_GRAPHICAL_VALUES)
        == _SECOND_ROW_FIRST_SOURCE
    )
    assert challenge.candidate_source(_CANDIDATES - 1) == _LAST_SOURCE


@pytest.mark.parametrize("index", [-1, _CANDIDATES, True])
def test_three_word_candidate_encoding_rejects_foreign_indices(
    index: object,
) -> None:
    """Index admission neither wraps nor admits bool or out-of-range values."""
    with pytest.raises(
        challenge.InvalidThreeWordCandidateError,
        match=_CANDIDATE_ERROR,
    ):
        _ = challenge.candidate_source(cast("int", index))


def test_three_word_workload_matches_preregistered_identity() -> None:
    """Implementation cannot drift from the pre-execution workload digest."""
    assert challenge.workload_sha256() == _WORKLOAD_SHA256
    assert sha256(challenge.workload_bytes()).hexdigest() == _WORKLOAD_SHA256


def test_three_word_holdout_matches_independent_bounded_static_analysis(
) -> None:
    """Characterize every holdout candidate only after preregistration."""
    accepted = _accepted()
    assert len(accepted) == _ACCEPTED_COUNT
    counts = dict.fromkeys(_QUALITY_COUNTS, 0)
    for _, quality in accepted:
        counts[quality] += 1
    assert counts == _QUALITY_COUNTS
    assert _digest(accepted) == _ACCEPTED_SHA256
