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
#   - Independent construction evidence for the crazy-preimage challenge.
# - Must-Not:
#   - Reuse production crazy-target search or treat challenge shape as a result.
# - Allows:
#   - Inputs: versioned challenge and independently written one-trit relation.
#   - Outputs: exact cardinality, coverage, replay, and workload-hash
#     assertions.
#   - Side effects: none.
# - Split-When:
#   - Another challenge version needs a distinct cardinality construction.
# - Merge-When:
#   - Shared challenge tests own this exact finite corpus identity.
# - Summary:
#   - Verify the frozen crazy-preimage cardinality span independently.
# - Description:
#   - Recomputes each full-word cardinality from a local one-trit relation.
# - Usage:
#   - Collected by the research-algorithm Python test surface.
# - Defaults:
#   - No production preparer or primitive adapter is imported.
#

"""Independent tests for the classic crazy-preimage challenge."""

import importlib.util
from pathlib import Path
import sys
from typing import Protocol
from typing import cast

_ROOT = Path(__file__).resolve().parents[5]
_CHALLENGE_MODULE = _ROOT / (
    "src/research/algorithms/composition/algorithms/superoptimization/"
    "crazy_preimage_challenge.py"
)

_CHALLENGE_ID = "classic-crazy-preimage-cardinality-span-v1"
_VERIFIER_ID = "classic-crazy-independent-table-v1"
_EXPECTED_CARDINALITIES = (0, 1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024)
_EXPECTED_PROBLEM_COUNT = len(_EXPECTED_CARDINALITIES)
_EXPECTED_WORKLOAD_SHA256 = (
    "2b0c969c46511a67fae4b977fdfa6cb0b6019740ed81c018d6150b03d8387d15"
)
_RADIX = 3
_TRIT_COUNT = 10
_ONE_TRIT_TABLE = (
    (1, 0, 0),
    (1, 0, 2),
    (2, 2, 1),
)


class _Problem(Protocol):
    accumulator: int
    target: int
    expected_preimages: int


class _Challenge(Protocol):
    challenge_id: str
    verifier_id: str
    problems: tuple[_Problem, ...]
    workload_sha256: str


class _ChallengeModule(Protocol):
    def challenge(self) -> _Challenge:
        """Return the frozen challenge."""
        ...


def _load_challenge_module() -> _ChallengeModule:
    spec = importlib.util.spec_from_file_location(
        "crazy_preimage_challenge_primary_test",
        _CHALLENGE_MODULE,
    )
    if spec is None or spec.loader is None:
        message = "crazy preimage challenge module cannot be loaded"
        raise RuntimeError(message)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return cast("_ChallengeModule", cast("object", module))


challenge_module = _load_challenge_module()


def _preimage_count(target: int, accumulator: int) -> int:
    count = 1
    target_word = target
    accumulator_word = accumulator
    for _ in range(_TRIT_COUNT):
        target_trit = target_word % _RADIX
        accumulator_trit = accumulator_word % _RADIX
        multiplicity = sum(
            _ONE_TRIT_TABLE[data_trit][accumulator_trit] == target_trit
            for data_trit in range(_RADIX)
        )
        count *= multiplicity
        target_word //= _RADIX
        accumulator_word //= _RADIX
    return count


def _challenge() -> _Challenge:
    return cast("_Challenge", cast("object", challenge_module.challenge()))


def test_crazy_preimage_challenge_replays_exactly() -> None:
    """Repeated construction retains versioned identities and workload bytes."""
    first = _challenge()
    second = _challenge()

    assert first == second
    assert first.challenge_id == _CHALLENGE_ID
    assert first.verifier_id == _VERIFIER_ID
    assert first.workload_sha256 == _EXPECTED_WORKLOAD_SHA256
    assert len(first.problems) == _EXPECTED_PROBLEM_COUNT


def test_crazy_preimage_challenge_spans_every_exact_cardinality() -> None:
    """Independent trit accounting recovers every cardinality class."""
    observed = tuple(
        _preimage_count(problem.target, problem.accumulator)
        for problem in _challenge().problems
    )
    declared = tuple(
        problem.expected_preimages for problem in _challenge().problems
    )

    assert observed == _EXPECTED_CARDINALITIES
    assert declared == _EXPECTED_CARDINALITIES


def test_crazy_preimage_reachable_targets_use_zero_accumulator() -> None:
    """Only target multiplicity varies across the finite corpus."""
    problems = _challenge().problems
    assert all(problem.accumulator == 0 for problem in problems)
    assert problems[0].target == 0
    assert all(problem.target > 0 for problem in problems[1:])
