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
#   - Independent semantic evidence for the crazy-preimage structural runner.
# - Must-Not:
#   - Interpret timing or use production crazy semantics as verifier authority.
# - Allows:
#   - Inputs: runner plus one independently implemented classic one-trit table.
# - Outputs: exact set equality, work-count, identity, and failure assertions.
# - Side effects: CPU reference search evaluation only.
# - Split-When:
#   - Timed measurement gains a separately preregistered protocol.
# - Merge-When:
#   - Shared comparison tests own this exact runner identity.
# - Summary:
#   - Verify exact-preimage pruning against complete independent enumeration.
# - Description:
#   - Injects independent classic crazy semantics into the frozen comparison.
# - Usage:
#   - Collected by the research-algorithm Python test surface.
# - Defaults:
#   - No clock or retained-result interpretation is allowed.
#

"""Independent tests for structural classic crazy preimage comparison."""

from algorithms.superoptimization import crazy_preimage_runner as runner
import pytest

_RUNNER_ID = "classic-crazy-preimage-structural-comparison-v1"
_BASELINE_ID = "classic-crazy-full-domain-data-enumeration-v1"
_TECHNIQUE_ID = "classic-crazy-digitwise-exact-preimage-v1"
_CHALLENGE_ID = "classic-crazy-preimage-cardinality-span-v1"
_WORKLOAD_SHA256 = (
    "2b0c969c46511a67fae4b977fdfa6cb0b6019740ed81c018d6150b03d8387d15"
)
_EXPECTED_CARDINALITIES = (0, 1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024)
_BASELINE_EVALUATIONS = 708_588
_EXACT_EVALUATIONS = 2_047
_SHA256_HEX_LENGTH = 64
_BASELINE_DRIFT_MESSAGE = (
    "independent baseline differs from declared challenge cardinality"
)
_RADIX = 3
_TRIT_COUNT = 10
_ONE_TRIT_TABLE = (
    (1, 0, 0),
    (1, 0, 2),
    (2, 2, 1),
)


def _crazy(data: int, accumulator: int) -> int:
    value = 0
    place = 1
    data_word = data
    accumulator_word = accumulator
    for _ in range(_TRIT_COUNT):
        data_trit = data_word % _RADIX
        accumulator_trit = accumulator_word % _RADIX
        value += _ONE_TRIT_TABLE[data_trit][accumulator_trit] * place
        data_word //= _RADIX
        accumulator_word //= _RADIX
        place *= _RADIX
    return value


def _forged_crazy(data: int, accumulator: int) -> int:
    _ = data
    _ = accumulator
    return 0


def test_crazy_preimage_runner_matches_every_independent_preimage_set() -> None:
    """Every projected set matches complete independent enumeration."""
    result = runner.run_comparison(_crazy)

    assert result.runner_id == _RUNNER_ID
    assert result.baseline_id == _BASELINE_ID
    assert result.technique_id == _TECHNIQUE_ID
    assert result.challenge_id == _CHALLENGE_ID
    assert result.workload_sha256 == _WORKLOAD_SHA256
    assert result.baseline_evaluations == _BASELINE_EVALUATIONS
    assert result.exact_evaluations == _EXACT_EVALUATIONS
    assert tuple(item.expected_preimages for item in result.results) == (
        _EXPECTED_CARDINALITIES
    )
    assert tuple(item.exact_evaluations for item in result.results) == (
        _EXPECTED_CARDINALITIES
    )
    assert all(
        len(item.preimage_sha256) == _SHA256_HEX_LENGTH
        for item in result.results
    )


def test_crazy_preimage_runner_rejects_independent_semantic_drift() -> None:
    """A forged semantic oracle cannot turn structural work into evidence."""
    with pytest.raises(
        runner.CrazyPreimageComparisonError,
        match=_BASELINE_DRIFT_MESSAGE,
    ):
        _ = runner.run_comparison(_forged_crazy)
