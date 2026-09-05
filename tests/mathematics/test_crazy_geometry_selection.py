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
#   - Evidence-driven no-promotion decision for resident CRAZY geometry.
# - Must-Not:
#   - Turn benchmark evidence into runtime authority or require CUDA hardware.
# - Allows:
#   - Inputs: retained evidence paths, research decision, and product default.
#   - Outputs: deterministic no-promotion and ownership assertions.
#   - Side effects: repository-local reads only.
# - Split-When:
#   - A later retained result supports a new geometry-promotion decision.
# - Merge-When:
#   - Product selection gains a separately owned evidence decision boundary.
# - Summary:
#   - Lock tritwise while geometry-promotion evidence remains incomplete.
# - Description:
#   - Retains positive lookup timing without granting silent promotion.
# - Usage:
#   - Run with CRAZY geometry mathematics and optimizer regressions.
# - Defaults:
#   - Future promotion needs new evidence and a new decision identity.
#

"""No-promotion decision checks for resident CUDA CRAZY geometry."""

from pathlib import Path
import tomllib
from typing import cast

from accelerator.cuda.resident_kernel import ResidentGeometry
from accelerator.cuda.resident_kernel import resident_kernel_source

_ROOT = Path(__file__).resolve().parents[2]
_DECISION = _ROOT / (
    "src/research/algorithms/domain/algorithms/"
    "malbolge-specific-optimization-mathematics/crazy-geometry-selection.toml"
)
_WIDTHS = [10, 11, 12, 13, 14]
_TRITWISE = "tritwise"
_NO_PROMOTION = "no-promotion"
_SEMANTIC_AUTHORITY = "cpu-reference"
_KERNEL_NAME = "crazy_selection_test"
_TRITWISE_LOOP = "for (unsigned int trit = 0u; trit < WORD_TRITS; ++trit)"
_TABLE_NAME = "CRAZY_CHUNK_TABLE"
_FUTURE_OWNERS = {
    "adaptive-accelerator-resource-budgeting",
    "configurable-accelerator-algorithm-adapters",
    "cuda-exact-vm-adapter",
}


def _document() -> dict[str, object]:
    return cast(
        "dict[str, object]",
        tomllib.loads(_DECISION.read_text(encoding="utf-8")),
    )


def _table(name: str) -> dict[str, object]:
    return cast("dict[str, object]", _document()[name])


def test_no_promotion_selects_tritwise_for_every_supported_width() -> None:
    """Incomplete promotion evidence deterministically keeps tritwise."""
    decision = _table("decision")
    widths = _table("widths")
    assert decision["status"] == _NO_PROMOTION
    assert decision["product_selection"] == _TRITWISE
    assert decision["candidate_evaluator_selection"] == _TRITWISE
    assert decision["native_promoted"] is False
    assert decision["padded_promoted"] is False
    assert widths["supported"] == _WIDTHS
    assert widths["selection"] == [_TRITWISE] * len(_WIDTHS)


def _geometry(word_trits: int) -> ResidentGeometry:
    modulus = 1
    for _ in range(word_trits):
        modulus *= 3
    return ResidentGeometry(
        interpreter_authority=False,
        eof_word=modulus - 1,
        input_instruction=ord("/"),
        memory_words=modulus,
        output_instruction=ord("<"),
        word_modulus=modulus,
        word_trits=word_trits,
    )


def test_product_default_remains_tritwise_without_evidence_reads() -> None:
    """Research records a decision while product code owns its default."""
    source = resident_kernel_source(_geometry(14), _KERNEL_NAME)
    assert _TABLE_NAME not in source
    assert _TRITWISE_LOOP in source
    assert _table("decision")["runtime_reads_benchmark_evidence"] is False


def test_selection_decision_resolves_every_retained_evidence_bundle() -> None:
    """Every cited decision input retains a README and exact source pin."""
    for value in _table("evidence").values():
        evidence = _ROOT / str(value)
        assert evidence.is_dir()
        assert (evidence / "README.md").is_file()
        assert (evidence / "source-commit.txt").is_file()


def test_missing_promotion_evidence_cannot_be_presented_as_measured() -> None:
    """Physical cache counters and primary Windows evidence stay explicit."""
    missing = _table("missing_promotion_evidence")
    assert missing["primary_windows_cpu_simd"] is True
    assert missing["physical_constant_cache_counters"] is True
    assert missing["nsight_compute_available"] is False
    assert missing["cupti_available"] is False
    assert missing["nvperf_available"] is False


def test_future_selection_work_has_explicit_downstream_owners() -> None:
    """No-promotion transfers future hardware policy without losing intent."""
    ownership = _table("future_ownership")
    assert {str(value) for value in ownership.values()} == _FUTURE_OWNERS
    policy = _table("policy")
    assert policy["promotion_requires_new_retained_evidence"] is True
    assert policy["future_promotion_requires_new_decision_identity"] is True
    assert policy["semantic_authority"] == _SEMANTIC_AUTHORITY
    assert policy["accelerator_unavailability_changes_acceptance"] is False
