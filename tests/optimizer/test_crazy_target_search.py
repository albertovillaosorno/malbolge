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
#   - Exact multi-position crazy-target strategy evidence.
# - Must-Not:
#   - Claim heuristic filtering, speedup, or backend acceptance authority.
# - Allows:
#   - Inputs: canonical fixed-accumulator target corpora and exact adapters.
#   - Outputs: format, subset, proposal, verifier, and live CUDA assertions.
#   - Side effects: scoped live CUDA allocations when available.
# - Split-When:
#   - Split when ticket or benchmark evidence gains an independent lifecycle.
# - Merge-When:
#   - Merge when another test owns this exact crazy-target strategy contract.
# - Summary:
#   - Correctness evidence for exact multiposition crazy-target search.
# - Description:
#   - Proves 1,024 algebraic preimages over the complete classic domain.
# - Usage:
#   - Collected by the optimizer suite; live tests skip without CUDA.
# - Defaults:
#   - Full membership and trusted CPU admission remain authoritative.
#

"""Correctness evidence for exact multiposition crazy-target search."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from typing import cast
from typing import override
from unittest import SkipTest

from accelerator.cuda import CudaExactPrimitiveAdapter
from accelerator.exact_primitives import AcceleratorCapability
from accelerator.exact_primitives import AcceleratorUnavailableError
from accelerator.exact_primitives import CRAZY_TRIT_TABLE
from accelerator.exact_primitives import ExactPrimitiveAdapter
from accelerator.exact_primitives import MAX_WORD
from accelerator.exact_primitives import PrimitiveResult
from accelerator.primitive_candidates import encode_crazy_candidate
from accelerator.work_ports import CandidateProposal
from accelerator.work_ports import IndexedCandidateWorkItems
from accelerator.work_ports import InvalidAcceleratorResultError
from accelerator.work_ports import InvalidAcceleratorWorkError
from accelerator.work_ports import SearchRequest
from accelerator.work_ports import admit_search_result
from optimizer.crazy_target import CRAZY_TARGET_ALGORITHM_ID
from optimizer.crazy_target import CrazyAccumulatorClass
from optimizer.crazy_target import CrazyPreimagePairClass
from optimizer.crazy_target import CrazyTargetProblem
from optimizer.crazy_target import CrazyTargetVerifier
from optimizer.crazy_target import InvalidCrazyTargetProblemError
from optimizer.crazy_target import PreparedCrazyTargetSelection
from optimizer.crazy_target import build_crazy_target_batch
from optimizer.crazy_target import count_prepared_crazy_target_positions
from optimizer.crazy_target import cpu_crazy_target_search_adapter
from optimizer.crazy_target import crazy_target_batch_builder_id
from optimizer.crazy_target import crazy_target_full_domain_accumulator_classes
from optimizer.crazy_target import crazy_target_full_domain_max_preimage_count
from optimizer.crazy_target import (
    crazy_target_full_domain_pairs_exceeding_preimage_budget,
)
from optimizer.crazy_target import crazy_target_full_domain_preimage_count
from optimizer.crazy_target import (
    crazy_target_full_domain_preimage_pair_classes,
)
from optimizer.crazy_target import crazy_target_full_domain_reachable_pair_count
from optimizer.crazy_target import (
    crazy_target_full_domain_reachable_target_count,
)
from optimizer.crazy_target import (
    crazy_target_full_domain_unreachable_pair_count,
)
from optimizer.crazy_target import crazy_target_projected_evaluation_id
from optimizer.crazy_target import crazy_target_search_adapter
from optimizer.crazy_target import crazy_target_selection_preparer_id
import pytest

if TYPE_CHECKING:
    from collections.abc import Callable

    from accelerator.exact_primitives import PreparedPrimitiveBatch
    from accelerator.exact_primitives import PrimitiveBatch

ALL_ONES = MAX_WORD // 2
BAD_CAPABILITY = AcceleratorCapability(
    backend_id="bad-crazy-search",
    device_arch="bad",
    device_name="bad",
)
CPU_BACKEND = "cpu-reference"
CUDA_BACKEND = "cuda"
EXPECTED_BATCH_BUILDER_ID = (
    "classic-crazy-u32le-bitset-first-representatives-v1"
)
EXPECTED_PROJECTED_EVALUATION_ID = "classic-crazy-preimage-position-subset-v1"
EXPECTED_SELECTION_PREPARER_ID = "classic-crazy-digitwise-exact-preimage-v1"
FULL_DOMAIN_COUNT = MAX_WORD + 1
MULTI_PREIMAGE_COUNT = 1 << 10
ROTATION_PIVOT = 2
FIRST_LOGICAL_ID = "corpus-0"
_MAX_ADMITTED_PROFILE_TRITS = 14
_PAIR_DOMAIN_PER_TRIT = 9


def _request(
    problem: CrazyTargetProblem,
    *,
    budget: int | None = None,
    seed: int = 0,
) -> SearchRequest:
    return SearchRequest(
        algorithm_id=CRAZY_TARGET_ALGORITHM_ID,
        evaluation_budget=(
            len(problem.candidates) if budget is None else budget
        ),
        problem=problem.encode(),
        seed=seed,
    )


def _cuda() -> CudaExactPrimitiveAdapter:
    try:
        return CudaExactPrimitiveAdapter()
    except AcceleratorUnavailableError as error:
        message = f"CUDA unavailable: {error}"
        raise SkipTest(message) from error


def _expect_problem_error(
    message: str,
    action: Callable[[], object],
) -> None:
    with pytest.raises(InvalidCrazyTargetProblemError, match=message):
        _ = action()


@dataclass(frozen=True, slots=True)
class _ExplodingPrimitiveAdapter(ExactPrimitiveAdapter):
    @override
    def capability(self) -> AcceleratorCapability:
        return BAD_CAPABILITY

    @override
    def evaluate(self, batch: PrimitiveBatch) -> PrimitiveResult:
        _ = batch
        message = "empty crazy projection unexpectedly invoked evaluation"
        raise AssertionError(message)

    @override
    def evaluate_prepared(
        self,
        prepared: PreparedPrimitiveBatch,
    ) -> PrimitiveResult:
        _ = prepared
        message = "empty crazy projection unexpectedly invoked evaluation"
        raise AssertionError(message)


@dataclass(frozen=True, slots=True)
class _ZeroPrimitiveAdapter(ExactPrimitiveAdapter):
    @override
    def capability(self) -> AcceleratorCapability:
        return BAD_CAPABILITY

    @override
    def evaluate(self, batch: PrimitiveBatch) -> PrimitiveResult:
        validated = batch.validated()
        return PrimitiveResult(
            capability=BAD_CAPABILITY,
            values=(0,) * len(validated.data),
        )

    @override
    def evaluate_prepared(
        self,
        prepared: PreparedPrimitiveBatch,
    ) -> PrimitiveResult:
        return self.evaluate(prepared.validated_batch())


def test_normative_crazy_table_is_hardware_neutral() -> None:
    """CPU and selector import one shared normative ternary relation."""
    assert CRAZY_TRIT_TABLE == (
        (1, 0, 0),
        (1, 0, 2),
        (2, 2, 1),
    )


_INDEPENDENT_CRAZY_TRIT = (
    (1, 0, 0),
    (1, 0, 2),
    (2, 2, 1),
)
_RADIX = 3
_TWO_TRIT = 2
_REACHABLE_PAIRS_PER_TRIT = 7
_TRIT_COUNT = 10
_MIXED_PREIMAGE_CASES = (
    (7_654, 12_345),
    (MAX_WORD, ALL_ONES),
)


def _independent_crazy(data: int, accumulator: int) -> int:
    result = 0
    place = 1
    for _ in range(10):
        result += (
            _INDEPENDENT_CRAZY_TRIT[data % _RADIX][accumulator % _RADIX]
            * place
        )
        data //= _RADIX
        accumulator //= _RADIX
        place *= _RADIX
    return result


def _brute_preimage_count(target: int, accumulator: int) -> int:
    return sum(
        _independent_crazy(data, accumulator) == target
        for data in range(FULL_DOMAIN_COUNT)
    )


def test_full_domain_preimage_count_matches_independent_relation() -> None:
    """Digitwise cardinality equals brute force on homogeneous trit pairs."""
    assert CRAZY_TRIT_TABLE == _INDEPENDENT_CRAZY_TRIT
    for accumulator_trit in range(_RADIX):
        accumulator = accumulator_trit * ALL_ONES
        for target_trit in range(_RADIX):
            target = target_trit * ALL_ONES
            observed = crazy_target_full_domain_preimage_count(
                target,
                accumulator,
            )
            assert observed == _brute_preimage_count(target, accumulator)
    for target, accumulator in _MIXED_PREIMAGE_CASES:
        observed = crazy_target_full_domain_preimage_count(target, accumulator)
        assert observed == _brute_preimage_count(target, accumulator)


def test_full_domain_preimage_count_exposes_exact_search_bounds() -> None:
    """Known all-one and impossible targets expose exact finite search sizes."""
    assert (
        crazy_target_full_domain_preimage_count(ALL_ONES, 0)
        == MULTI_PREIMAGE_COUNT
    )
    assert crazy_target_full_domain_preimage_count(0, 0) == 0
    foreign_value: object = MAX_WORD >= 0
    foreign_target = cast("int", foreign_value)
    with pytest.raises(
        InvalidCrazyTargetProblemError,
        match="target must use the exact integer type",
    ):
        _ = crazy_target_full_domain_preimage_count(foreign_target, 0)


def _independent_max_preimage_count(accumulator: int) -> int:
    count = 1
    for _ in range(10):
        accumulator_trit = accumulator % _RADIX
        multiplicities = (
            sum(
                row[accumulator_trit] == target_trit
                for row in _INDEPENDENT_CRAZY_TRIT
            )
            for target_trit in range(_RADIX)
        )
        count *= max(multiplicities)
        accumulator //= _RADIX
    return count


def test_full_domain_preimage_count_has_tight_global_bound() -> None:
    """Every classic fixed crazy target has at most 1,024 data preimages."""
    observed_maximum = 0
    for accumulator in range(FULL_DOMAIN_COUNT):
        maximum = _independent_max_preimage_count(accumulator)
        assert maximum <= MULTI_PREIMAGE_COUNT
        observed_maximum = max(observed_maximum, maximum)
    assert observed_maximum == MULTI_PREIMAGE_COUNT
    assert (
        crazy_target_full_domain_preimage_count(ALL_ONES, 0)
        == observed_maximum
    )


def _independent_preimage_spectrum(accumulator: int) -> set[int]:
    spectrum = {1}
    for _ in range(10):
        accumulator_trit = accumulator % _RADIX
        multiplicities = {
            sum(
                row[accumulator_trit] == target_trit
                for row in _INDEPENDENT_CRAZY_TRIT
            )
            for target_trit in range(_RADIX)
        }
        spectrum = {
            prefix * multiplicity
            for prefix in spectrum
            for multiplicity in multiplicities
        }
        accumulator //= _RADIX
    return spectrum


def _independent_maximizing_target(accumulator: int) -> tuple[int, int]:
    target = 0
    place = 1
    doubled_positions = 0
    for _ in range(10):
        accumulator_trit = accumulator % _RADIX
        if accumulator_trit == 0:
            target += place
            doubled_positions += 1
        elif accumulator_trit == 1:
            doubled_positions += 1
        accumulator //= _RADIX
        place *= _RADIX
    return (target, doubled_positions)


def test_full_domain_preimage_counts_have_exact_power_of_two_spectrum() -> None:
    """Nonzero classic preimage counts are powers of two through 1,024."""
    expected = {0, *(1 << exponent for exponent in range(11))}
    observed: set[int] = set()
    for accumulator in range(FULL_DOMAIN_COUNT):
        spectrum = _independent_preimage_spectrum(accumulator)
        assert spectrum <= expected
        observed.update(spectrum)
    assert observed == expected


def _independent_reachable_target_count(accumulator: int) -> int:
    count = 1
    for _ in range(10):
        accumulator_trit = accumulator % _RADIX
        multiplicities = tuple(
            sum(
                row[accumulator_trit] == target_trit
                for row in _INDEPENDENT_CRAZY_TRIT
            )
            for target_trit in range(_RADIX)
        )
        count *= sum(multiplicity > 0 for multiplicity in multiplicities)
        accumulator //= _RADIX
    return count


def _count_accumulator_two_trits(accumulator: int) -> int:
    count = 0
    for _ in range(10):
        count += accumulator % _RADIX == _TWO_TRIT
        accumulator //= _RADIX
    return count


def test_maximum_preimage_count_is_accumulator_specific() -> None:
    """Each accumulator has an exact worst-target power-of-two bound."""
    for accumulator in range(FULL_DOMAIN_COUNT):
        target, doubled_positions = _independent_maximizing_target(accumulator)
        expected = 1 << doubled_positions
        assert _independent_max_preimage_count(accumulator) == expected
        assert (
            crazy_target_full_domain_preimage_count(target, accumulator)
            == expected
        )


def test_accumulator_planning_bounds_match_independent_relation() -> None:
    """Public state-level bounds match every independent classic accumulator."""
    for accumulator in range(FULL_DOMAIN_COUNT):
        two_trits = _count_accumulator_two_trits(accumulator)
        doubled = 10 - two_trits
        expected_max = 1 << doubled
        expected_reachable = expected_max
        for _ in range(two_trits):
            expected_reachable *= _RADIX
        assert (
            crazy_target_full_domain_max_preimage_count(accumulator)
            == _independent_max_preimage_count(accumulator)
            == expected_max
        )
        assert (
            crazy_target_full_domain_reachable_target_count(accumulator)
            == _independent_reachable_target_count(accumulator)
            == expected_reachable
        )


def _independent_accumulator_class_histogram() -> tuple[int, ...]:
    counts = [0] * (10 + 1)
    for accumulator in range(FULL_DOMAIN_COUNT):
        counts[_count_accumulator_two_trits(accumulator)] += 1
    return tuple(counts)


def _independent_trit_preimage_class_counts() -> tuple[tuple[int, int], ...]:
    counts: dict[int, int] = {}
    for accumulator_trit in range(_RADIX):
        for target_trit in range(_RADIX):
            multiplicity = sum(
                _INDEPENDENT_CRAZY_TRIT[data_trit][accumulator_trit]
                == target_trit
                for data_trit in range(_RADIX)
            )
            if multiplicity == 0:
                continue
            counts[multiplicity] = counts.get(multiplicity, 0) + 1
    return tuple(sorted(counts.items()))


def _expand_independent_preimage_pair_histogram(
    histogram: dict[int, int],
    per_trit: tuple[tuple[int, int], ...],
) -> dict[int, int]:
    expanded: dict[int, int] = {}
    for preimage_count, pair_count in histogram.items():
        for multiplicity, trit_pair_count in per_trit:
            combined = preimage_count * multiplicity
            expanded[combined] = (
                expanded.get(combined, 0) + pair_count * trit_pair_count
            )
    return expanded


def _independent_preimage_pair_histogram(
    trit_count: int = _TRIT_COUNT,
) -> dict[int, int]:
    per_trit = _independent_trit_preimage_class_counts()
    histogram = {1: 1}
    for _ in range(trit_count):
        histogram = _expand_independent_preimage_pair_histogram(
            histogram,
            per_trit,
        )
    return histogram


def test_global_preimage_pair_classes_match_independent_relation() -> None:
    """Reachable pair counts are exact for every nonzero preimage class."""
    classes = crazy_target_full_domain_preimage_pair_classes()
    histogram = _independent_preimage_pair_histogram()
    assert all(isinstance(item, CrazyPreimagePairClass) for item in classes)
    assert tuple(item.preimage_count for item in classes) == tuple(
        1 << exponent for exponent in range(_TRIT_COUNT + 1)
    )
    observed = {item.preimage_count: item.pair_count for item in classes}
    assert observed == histogram
    for exponent, item in enumerate(classes):
        expected = _independent_binomial(_TRIT_COUNT, exponent)
        for _ in range(exponent):
            expected *= 2
        for _ in range(_TRIT_COUNT - exponent):
            expected *= 5
        assert item.pair_count == expected
    assert sum(item.pair_count for item in classes) == (
        crazy_target_full_domain_reachable_pair_count()
    )
    assert sum(
        item.preimage_count * item.pair_count for item in classes
    ) == FULL_DOMAIN_COUNT * FULL_DOMAIN_COUNT


def _independent_integer_power(base: int, exponent: int) -> int:
    result = 1
    for _ in range(exponent):
        result *= base
    return result


def test_profile_width_preimage_pair_distribution_matches_closed_form() -> None:
    """Widths one through fourteen match the exact digitwise closed form."""
    for trit_count in range(1, _MAX_ADMITTED_PROFILE_TRITS + 1):
        histogram = _independent_preimage_pair_histogram(trit_count)
        for exponent in range(trit_count + 1):
            expected = _independent_binomial(trit_count, exponent)
            expected *= _independent_integer_power(2, exponent)
            expected *= _independent_integer_power(
                5, trit_count - exponent
            )
            assert histogram[1 << exponent] == expected
        reachable = _independent_integer_power(
            _REACHABLE_PAIRS_PER_TRIT, trit_count
        )
        pair_domain = _independent_integer_power(
            _PAIR_DOMAIN_PER_TRIT, trit_count
        )
        assert sum(histogram.values()) == reachable
        assert sum(
            preimages * pairs for preimages, pairs in histogram.items()
        ) == pair_domain
        assert pair_domain - reachable >= 0


def test_preimage_budget_pair_count_matches_independent_histogram() -> None:
    """Budget thresholds exactly count reachable pairs they cannot cover."""
    histogram = _independent_preimage_pair_histogram()
    budgets = (0, 1, 2, 3, 31, 32, 511, 512, 1023, 1024, 2048)
    for budget in budgets:
        expected = sum(
            pair_count
            for preimage_count, pair_count in histogram.items()
            if preimage_count > budget
        )
        assert (
            crazy_target_full_domain_pairs_exceeding_preimage_budget(budget)
            == expected
        )
    assert crazy_target_full_domain_pairs_exceeding_preimage_budget(0) == (
        crazy_target_full_domain_reachable_pair_count()
    )
    assert crazy_target_full_domain_pairs_exceeding_preimage_budget(1024) == 0


def test_preimage_budget_pair_count_rejects_invalid_budget() -> None:
    """Planning-budget admission is fail-closed before class accounting."""
    for invalid in (-1, True):
        with pytest.raises(
            InvalidCrazyTargetProblemError,
            match="preimage budget must be a nonnegative exact integer",
        ):
            _ = crazy_target_full_domain_pairs_exceeding_preimage_budget(
                cast("int", invalid)
            )


def test_unreachable_accumulator_target_pair_count_is_exact() -> None:
    """Impossible global pairs are the exact complement of reachable pairs."""
    reachable = crazy_target_full_domain_reachable_pair_count()
    total_pairs = FULL_DOMAIN_COUNT * FULL_DOMAIN_COUNT
    observed = crazy_target_full_domain_unreachable_pair_count()
    assert observed == total_pairs - reachable
    assert observed + reachable == total_pairs


def test_reachable_accumulator_target_pair_count_is_exact() -> None:
    """Global reachable pair count matches independent state/class sums."""
    expected_per_trit = 0
    for accumulator_trit in range(_RADIX):
        multiplicities = tuple(
            sum(
                _INDEPENDENT_CRAZY_TRIT[data_trit][accumulator_trit]
                == target_trit
                for data_trit in range(_RADIX)
            )
            for target_trit in range(_RADIX)
        )
        expected_per_trit += sum(value > 0 for value in multiplicities)
    expected = 1
    for _ in range(_TRIT_COUNT):
        expected *= expected_per_trit
    state_sum = sum(
        crazy_target_full_domain_reachable_target_count(accumulator)
        for accumulator in range(FULL_DOMAIN_COUNT)
    )
    class_sum = sum(
        item.accumulator_count * item.reachable_target_count
        for item in crazy_target_full_domain_accumulator_classes()
    )
    assert expected_per_trit == _REACHABLE_PAIRS_PER_TRIT
    assert crazy_target_full_domain_reachable_pair_count() == expected
    assert state_sum == expected
    assert class_sum == expected


def test_accumulator_classes_partition_complete_classic_domain() -> None:
    """Class counts independently partition all classic accumulators."""
    classes = crazy_target_full_domain_accumulator_classes()
    histogram = _independent_accumulator_class_histogram()
    assert tuple(item.accumulator_count for item in classes) == histogram
    assert sum(histogram) == FULL_DOMAIN_COUNT
    assert tuple(item.two_trits for item in classes) == tuple(range(11))


def _independent_binomial(total: int, selected: int) -> int:
    numerator = 1
    denominator = 1
    for offset in range(selected):
        numerator *= total - offset
        denominator *= offset + 1
    return numerator // denominator


def test_accumulator_class_cardinality_matches_closed_form() -> None:
    """Each sufficient-statistic class has the exact binomial cardinality."""
    classes = crazy_target_full_domain_accumulator_classes()
    non_two_choices = _RADIX - 1
    for item in classes:
        expected = _independent_binomial(_TRIT_COUNT, item.two_trits)
        for _ in range(_TRIT_COUNT - item.two_trits):
            expected *= non_two_choices
        assert item.accumulator_count == expected


def test_accumulator_classes_match_every_state_level_planning_bound() -> None:
    """All accumulators in one class share both exact planning cardinalities."""
    classes = crazy_target_full_domain_accumulator_classes()
    for accumulator in range(FULL_DOMAIN_COUNT):
        two_trits = _count_accumulator_two_trits(accumulator)
        item = classes[two_trits]
        assert isinstance(item, CrazyAccumulatorClass)
        assert (
            crazy_target_full_domain_max_preimage_count(accumulator)
            == item.max_preimage_count
        )
        assert (
            crazy_target_full_domain_reachable_target_count(accumulator)
            == item.reachable_target_count
        )


def test_accumulator_planning_bounds_reject_foreign_words() -> None:
    """Planning helpers preserve exact classic-word admission."""
    foreign: object = True
    for operation in (
        crazy_target_full_domain_max_preimage_count,
        crazy_target_full_domain_reachable_target_count,
    ):
        with pytest.raises(
            InvalidCrazyTargetProblemError,
            match="accumulator must use the exact integer type",
        ):
            _ = operation(cast("int", foreign))


def test_crazy_target_strategy_identities_are_stable() -> None:
    """Batch, selector, and multiposition projection identities are explicit."""
    assert crazy_target_batch_builder_id() == EXPECTED_BATCH_BUILDER_ID
    assert (
        crazy_target_selection_preparer_id() == EXPECTED_SELECTION_PREPARER_ID
    )
    assert (
        crazy_target_projected_evaluation_id()
        == EXPECTED_PROJECTED_EVALUATION_ID
    )


def test_crazy_target_problem_roundtrips_canonically() -> None:
    """Target, accumulator, and candidate corpus retain canonical identity."""
    problem = CrazyTargetProblem(
        accumulator=7,
        target=ALL_ONES,
        candidates=(0, 1, 2, 1, MAX_WORD),
    )

    encoded = problem.encode()
    decoded = CrazyTargetProblem.decode(encoded)

    assert decoded == problem
    assert decoded.encode() == encoded
    assert CrazyTargetProblem.decode_parameters(encoded) == (ALL_ONES, 7)


def test_problem_rejects_invalid_domain_and_encoding() -> None:
    """Malformed target, accumulator, corpus, and bytes fail before work."""
    _expect_problem_error(
        "crazy target outside classic domain",
        lambda: CrazyTargetProblem(
            accumulator=0,
            target=MAX_WORD + 1,
            candidates=(),
        ).validated(),
    )
    _expect_problem_error(
        "crazy accumulator outside classic domain",
        lambda: CrazyTargetProblem(
            accumulator=MAX_WORD + 1,
            target=0,
            candidates=(),
        ).validated(),
    )
    _expect_problem_error(
        "crazy candidate outside classic domain",
        lambda: CrazyTargetProblem(
            accumulator=0,
            target=0,
            candidates=(MAX_WORD + 1,),
        ).validated(),
    )
    _expect_problem_error(
        "invalid magic",
        lambda: CrazyTargetProblem.decode(b"wrong"),
    )
    valid = CrazyTargetProblem(
        accumulator=0,
        target=ALL_ONES,
        candidates=(1,),
    ).encode()
    _expect_problem_error(
        "invalid candidate byte length",
        lambda: CrazyTargetProblem.decode(valid[:-1]),
    )


def test_batch_rotates_distinct_data_and_retains_fixed_accumulator() -> None:
    """Seed/budget rotate stable data representatives in packed storage."""
    request = _request(
        CrazyTargetProblem(
            accumulator=7,
            target=ALL_ONES,
            candidates=(7, 1, 7, 4, 1, 9),
        ),
        budget=3,
        seed=2,
    )

    batch = build_crazy_target_batch(request).validated()

    assert isinstance(batch.items, IndexedCandidateWorkItems)
    assert batch.items.logical_rotation_pivot == ROTATION_PIVOT
    assert tuple(batch.items.logical_index_at(index) for index in range(3)) == (
        3,
        5,
        0,
    )
    assert tuple(
        (
            int.from_bytes(batch.items.payload_at(index)[:4], "little"),
            int.from_bytes(batch.items.payload_at(index)[4:], "little"),
        )
        for index in range(3)
    ) == ((4, 7), (9, 7), (7, 7))


def test_cpu_search_prunes_duplicates_and_finds_all_small_preimages() -> None:
    """Non-invertible exact search returns every retained matching position."""
    problem = CrazyTargetProblem(
        accumulator=0,
        target=ALL_ONES,
        candidates=(0, 1, 2, 3, 4, 1),
    )
    result = cpu_crazy_target_search_adapter().search(_request(problem))

    assert result.capability.backend_id == CPU_BACKEND
    assert tuple(proposal.logical_id for proposal in result.proposals) == (
        "corpus-0",
        "corpus-1",
        "corpus-3",
        "corpus-4",
    )
    assert tuple(
        int.from_bytes(proposal.payload[:4], "little")
        for proposal in result.proposals
    ) == (0, 1, 3, 4)


def test_seed_and_budget_bound_multiposition_search_order() -> None:
    """Budget follows exact stable-first deduplication and seed rotation."""
    problem = CrazyTargetProblem(
        accumulator=0,
        target=ALL_ONES,
        candidates=(0, 1, 2, 3, 4, 1),
    )
    adapter = cpu_crazy_target_search_adapter()

    result = adapter.search(_request(problem, budget=3, seed=2))

    assert tuple(proposal.logical_id for proposal in result.proposals) == (
        "corpus-3",
        "corpus-4",
    )


def test_full_domain_preparation_supplies_exact_1024_position_subset() -> None:
    """Complete classic membership projects to every digitwise preimage."""
    problem = CrazyTargetProblem(
        accumulator=0,
        target=ALL_ONES,
        candidates=tuple(range(FULL_DOMAIN_COUNT)),
    )
    request = _request(problem)
    adapter = cpu_crazy_target_search_adapter()

    prepared = adapter.prepare(request)
    result = adapter.search_prepared(prepared)

    assert adapter.prepared_membership_count(prepared) == FULL_DOMAIN_COUNT
    assert (
        adapter.prepared_candidate_state_count(prepared) == MULTI_PREIMAGE_COUNT
    )
    assert adapter.prepared_selection_count(prepared) == MULTI_PREIMAGE_COUNT
    assert len(result.proposals) == MULTI_PREIMAGE_COUNT
    assert result.proposals[0].logical_id == FIRST_LOGICAL_ID
    assert result.proposals[-1].logical_id == f"corpus-{ALL_ONES}"
    assert all(
        CrazyTargetVerifier(ALL_ONES, 0).accepts(proposal, None)
        for proposal in result.proposals
    )


def test_full_domain_prepared_and_ordinary_search_are_identical() -> None:
    """Projection changes capacity only; full ordinary semantics stay exact."""
    problem = CrazyTargetProblem(
        accumulator=0,
        target=ALL_ONES,
        candidates=tuple(range(FULL_DOMAIN_COUNT)),
    )
    request = _request(problem)
    adapter = cpu_crazy_target_search_adapter()
    prepared = adapter.prepare(request)

    assert adapter.search_prepared(prepared) == adapter.search(request)


def test_empty_projection_skips_primitive_backend() -> None:
    """An impossible target yields empty evidence without backend execution."""
    problem = CrazyTargetProblem(
        accumulator=0,
        target=0,
        candidates=tuple(range(257)),
    )
    request = _request(problem)
    adapter = crazy_target_search_adapter(_ExplodingPrimitiveAdapter())

    prepared = adapter.prepare(request)
    result = adapter.search_prepared(prepared)

    assert adapter.prepared_candidate_state_count(prepared) == 0
    assert adapter.prepared_selection_count(prepared) == 0
    assert result.proposals == ()


def test_prepared_search_rejects_wrong_exact_backend_evidence() -> None:
    """Projected candidates still require proof-bound CPU-reference equality."""
    problem = CrazyTargetProblem(
        accumulator=0,
        target=ALL_ONES,
        candidates=(0, 2),
    )
    adapter = crazy_target_search_adapter(_ZeroPrimitiveAdapter())
    prepared = adapter.prepare(_request(problem))

    assert adapter.prepared_selection_count(prepared) == 1
    with pytest.raises(
        InvalidAcceleratorResultError, match="trusted CPU reference"
    ):
        _ = adapter.search_prepared(prepared)


def test_prepared_selection_rejects_forged_state() -> None:
    """Raw selector-state construction cannot forge exact position authority."""
    request = _request(
        CrazyTargetProblem(
            accumulator=0,
            target=ALL_ONES,
            candidates=(0,),
        )
    )
    batch = build_crazy_target_batch(request)
    forged = PreparedCrazyTargetSelection(
        accumulator=0,
        batch=batch,
        positions=(0,),
        request=request,
        target=ALL_ONES,
        _proof=object(),
    )

    with pytest.raises(
        InvalidAcceleratorWorkError,
        match="prepared crazy selection state is forged",
    ):
        _ = count_prepared_crazy_target_positions(forged)
    with pytest.raises(
        InvalidAcceleratorWorkError,
        match="prepared crazy selection state has wrong type",
    ):
        _ = count_prepared_crazy_target_positions(object())


def test_trusted_verifier_recomputes_and_binds_accumulator() -> None:
    """Admission rejects malformed or cross-accumulator proposals."""
    verifier = CrazyTargetVerifier(ALL_ONES, 0)
    valid = CandidateProposal(
        logical_id="valid",
        payload=encode_crazy_candidate(0, 0),
    )
    wrong_accumulator = CandidateProposal(
        logical_id="wrong-accumulator",
        payload=encode_crazy_candidate(0, 1),
    )
    malformed = CandidateProposal(logical_id="malformed", payload=b"bad")

    assert verifier.accepts(valid, None)
    assert not verifier.accepts(wrong_accumulator, None)
    assert not verifier.accepts(malformed, None)


def test_prepared_cpu_state_executes_1024_positions_on_live_cuda() -> None:
    """Live CUDA consumes the exact multiposition proof and matches CPU."""
    problem = CrazyTargetProblem(
        accumulator=0,
        target=ALL_ONES,
        candidates=tuple(range(FULL_DOMAIN_COUNT)),
    )
    request = _request(problem)
    reference = cpu_crazy_target_search_adapter()
    prepared = reference.prepare(request)
    expected = reference.search_prepared(prepared)

    with _cuda() as cuda:
        observed = crazy_target_search_adapter(cuda).search_prepared(prepared)
        stats = cuda.prepared_stats()

    assert stats.builds == 1
    assert stats.evaluations == 1
    assert stats.packed_evaluations == 1
    assert stats.resident_count == MULTI_PREIMAGE_COUNT
    assert stats.reuses == 0
    assert observed.capability.backend_id == CUDA_BACKEND
    assert observed.proposals == expected.proposals
    assert (
        admit_search_result(observed, CrazyTargetVerifier(ALL_ONES, 0))
        == observed.proposals
    )


def test_crazy_problem_requires_exact_immutable_runtime_types() -> None:
    """Direct crazy problems reject bools, floats, lists, and mutable bytes."""
    for foreign_word in (False, 1.0):
        word: object = foreign_word
        _expect_problem_error(
            "target must use the exact integer type",
            lambda word=word: CrazyTargetProblem(
                accumulator=0,
                target=cast("int", word),
                candidates=(),
            ).validated(),
        )
        _expect_problem_error(
            "candidate must use the exact integer type",
            lambda word=word: CrazyTargetProblem(
                accumulator=0,
                target=0,
                candidates=(cast("int", word),),
            ).validated(),
        )
    mutable_candidates: object = [0]
    mutable_payload: object = bytearray(
        CrazyTargetProblem(
            accumulator=0,
            target=0,
            candidates=(),
        ).encode()
    )
    _expect_problem_error(
        "candidates must use an immutable tuple",
        lambda: CrazyTargetProblem(
            accumulator=0,
            target=0,
            candidates=cast(
                "tuple[int, ...]",
                cast("object", mutable_candidates),
            ),
        ).validated(),
    )
    _expect_problem_error(
        "problem must use immutable bytes",
        lambda: CrazyTargetProblem.decode(
            cast("bytes", cast("object", mutable_payload))
        ),
    )
