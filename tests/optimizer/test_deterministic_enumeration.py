# Copyright (c) 2026 Alberto Villa Osorno.
# SPDX-License-Identifier: MIT
"""Correctness evidence for deterministic finite-corpus CPU enumeration."""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import final
from typing import override

from accelerator.search_selection import CPU_REFERENCE_BACKEND
from accelerator.search_selection import SearchAdapterBinding
from accelerator.search_selection import SearchSelection
from accelerator.search_selection import resolve_search_execution
from accelerator.work_ports import CandidateProposal
from accelerator.work_ports import SearchRequest
from accelerator.work_ports import TrustedCandidateVerifier
from optimizer import ENUMERATIVE_ALGORITHM_ID
from optimizer import EnumerationProblem
from optimizer import cpu_enumerative_adapter
from optimizer import enumerate_candidates
from optimizer import search_and_verify
from optimizer.enumerative import InvalidEnumerationProblemError

if TYPE_CHECKING:
    from collections.abc import Callable

    from accelerator.work_ports import VerificationHint

CANDIDATES = (b"alpha", b"beta", b"gamma")


@final
class _SuffixVerifier(TrustedCandidateVerifier):
    @override
    def accepts(
        self,
        candidate: CandidateProposal,
        hint: VerificationHint | None,
    ) -> bool:
        return candidate.payload.endswith(b"-ok") and hint is None


def _expect_problem_error(
    message: str,
    action: Callable[[], object],
) -> None:
    try:
        _ = action()
    except InvalidEnumerationProblemError as error:
        if message not in str(error):
            raise AssertionError from error
        return
    raise AssertionError


def _request(
    problem: EnumerationProblem,
    *,
    budget: int,
    seed: int,
) -> SearchRequest:
    return SearchRequest(
        algorithm_id=ENUMERATIVE_ALGORITHM_ID,
        evaluation_budget=budget,
        problem=problem.encode(),
        seed=seed,
    )


def test_problem_encoding_roundtrips_canonically() -> None:
    """Finite corpus encoding is deterministic and byte-exact on roundtrip."""
    problem = EnumerationProblem(candidates=CANDIDATES)

    encoded = problem.encode()
    decoded = EnumerationProblem.decode(encoded)

    assert decoded == problem
    assert decoded.encode() == encoded


def test_seed_rotates_deterministic_corpus_order() -> None:
    """Seed changes only the deterministic starting ordinal."""
    problem = EnumerationProblem(candidates=CANDIDATES)

    proposals = enumerate_candidates(_request(problem, budget=3, seed=1))

    assert tuple(item.logical_id for item in proposals) == (
        "corpus-1",
        "corpus-2",
        "corpus-0",
    )
    assert tuple(item.payload for item in proposals) == (
        b"beta",
        b"gamma",
        b"alpha",
    )


def test_budget_caps_search_without_duplicate_wraparound() -> None:
    """Budget larger than the corpus still evaluates each candidate once."""
    problem = EnumerationProblem(candidates=CANDIDATES)

    proposals = enumerate_candidates(_request(problem, budget=99, seed=2))

    assert len(proposals) == len(CANDIDATES)
    assert len({item.logical_id for item in proposals}) == len(CANDIDATES)


def test_duplicate_candidates_roundtrip_and_prune_before_identity() -> None:
    """Exact duplicates preserve input replay but consume one evaluation."""
    problem = EnumerationProblem(
        candidates=(b"same", b"other", b"same", b"third", b"other"),
    )

    encoded = problem.encode()
    decoded = EnumerationProblem.decode(encoded)
    proposals = enumerate_candidates(_request(decoded, budget=99, seed=0))

    assert decoded == problem
    assert tuple(item.logical_id for item in proposals) == (
        "corpus-0",
        "corpus-1",
        "corpus-3",
    )
    assert tuple(item.payload for item in proposals) == (
        b"same",
        b"other",
        b"third",
    )


def test_seed_rotates_over_exact_representatives_not_duplicates() -> None:
    """Seed ordering is defined over retained first representatives."""
    problem = EnumerationProblem(
        candidates=(b"a", b"a", b"b", b"c", b"b"),
    )

    proposals = enumerate_candidates(_request(problem, budget=2, seed=1))

    assert tuple(item.logical_id for item in proposals) == (
        "corpus-2",
        "corpus-3",
    )
    assert tuple(item.payload for item in proposals) == (b"b", b"c")


def test_one_byte_difference_survives_production_pruning() -> None:
    """Production search preserves byte-distinct near matches."""
    problem = EnumerationProblem(
        candidates=(b"prefix-A", b"prefix-B", b"prefix-A"),
    )

    proposals = enumerate_candidates(_request(problem, budget=99, seed=0))

    assert tuple(item.logical_id for item in proposals) == (
        "corpus-0",
        "corpus-1",
    )
    assert tuple(item.payload for item in proposals) == (
        b"prefix-A",
        b"prefix-B",
    )


def test_malformed_problem_bytes_fail_closed() -> None:
    """Malformed problem encodings never become candidates."""
    valid = EnumerationProblem(candidates=(b"one",)).encode()
    cases = (
        (b"wrong", "invalid magic"),
        (valid[:-1], "candidate payload is truncated"),
        (valid + b"x", "trailing bytes"),
    )
    for payload, message in cases:
        _expect_problem_error(
            message,
            lambda payload=payload: EnumerationProblem.decode(payload),
        )


def test_cpu_only_search_admits_only_trusted_verifier_results() -> None:
    """Only trusted verification accepts CPU search candidates."""
    problem = EnumerationProblem(
        candidates=(b"bad", b"good-ok", b"also-bad"),
    )

    accepted = search_and_verify(problem, 3, _SuffixVerifier())

    assert accepted == (
        CandidateProposal(logical_id="corpus-1", payload=b"good-ok"),
    )


def test_enumerative_strategy_uses_generic_search_selection() -> None:
    """CPU enumeration plugs into the generic search registry."""
    binding = SearchAdapterBinding(
        adapter=cpu_enumerative_adapter(),
        algorithm_id=ENUMERATIVE_ALGORITHM_ID,
    )
    plan = resolve_search_execution(
        (binding,),
        SearchSelection(
            algorithm_id=ENUMERATIVE_ALGORITHM_ID,
            backend_id=CPU_REFERENCE_BACKEND,
        ),
    )
    problem = EnumerationProblem(candidates=CANDIDATES)

    record = plan.run(_request(problem, budget=2, seed=0))

    assert record.identity.actual_backend_id == CPU_REFERENCE_BACKEND
    assert (
        tuple(item.payload for item in record.result.proposals)
        == CANDIDATES[:2]
    )
