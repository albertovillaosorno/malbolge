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
#   - Integrity checks for retained secondary-host AVX2 CRAZY evidence.
# - Must-Not:
#   - Treat Linux SIMD timing as product route-selection authority.
# - Allows:
#   - Inputs: tracked raw CSV, metadata, and clean source-commit provenance.
#   - Outputs: exact sample, checksum, median, and paired-win assertions.
#   - Side effects: tracked evidence reads only.
# - Split-When:
#   - Split when another SIMD ISA or primary-host record gains its own identity.
# - Merge-When:
#   - Merge when another test owns this exact retained AVX2 evidence directory.
# - Summary:
#   - Locks N10-N14 AVX2 padded CRAZY evidence from the secondary Linux host.
# - Description:
#   - Recomputes cardinality, checksums, medians, and paired wins from raw CSV.
# - Usage:
#   - Run on every validation host without requiring AVX2 execution.
# - Defaults:
#   - Retained Linux SIMD evidence has no product selection authority.
#

"""Integrity checks for retained secondary Linux AVX2 CRAZY evidence."""

from __future__ import annotations

import csv
from dataclasses import dataclass
import json
from pathlib import Path
from statistics import median
from typing import Final
from typing import cast

EVIDENCE: Final = (
    Path("benchmarks/cpu/evidence")
    / "2026-09-04-profile-crazy-avx2-linux-x86_64"
)
EXPECTED_SOURCE_COMMIT: Final = "e09d51d16ed7eaeee2156899b7d913670a33fd5d"
EXPECTED_BENCHMARK_ID: Final = "cpu-profile-crazy-avx2-v1"
EXPECTED_HOST_CLASS: Final = "secondary-linux-x86_64"
EXPECTED_WIDTHS: Final = (10, 11, 12, 13, 14)
EXPECTED_SAMPLE_COUNT: Final = 15
EXPECTED_ROW_COUNT: Final = 225
EXPECTED_ROUTE_COUNT: Final = 3
EXPECTED_SIMD_ISA: Final = "AVX2"
EXPECTED_SIMD_LANES: Final = 8
EXPECTED_GATHER_COUNT: Final = 3
EXPECTED_CHECKSUMS: Final = {
    10: 27_683_170_464,
    11: 69_793_138_128,
    12: 255_944_874_432,
    13: 590_667_673_872,
    14: 1_594_938_108_864,
}
EXPECTED_PADDED_MEDIANS: Final = {
    10: 6_103_260,
    11: 14_992_499,
    12: 14_391_326,
    13: 15_139_031,
    14: 15_285_523,
}
EXPECTED_AVX2_MEDIANS: Final = {
    10: 4_584_882,
    11: 9_288_631,
    12: 9_240_532,
    13: 9_261_840,
    14: 9_312_114,
}
EXPECTED_AVX2_WINS: Final = {10: 15, 11: 15, 12: 14, 13: 15, 14: 14}


@dataclass(frozen=True, slots=True)
class _Sample:
    benchmark_id: str
    checksum: int
    implementation: str
    nanoseconds: int
    sample: int
    width: int


def _samples() -> tuple[_Sample, ...]:
    with (EVIDENCE / "raw.csv").open(newline="") as handle:
        rows = list(csv.reader(handle))
    expected_header = [
        "benchmark_id",
        "width",
        "implementation",
        "sample",
        "nanoseconds",
        "checksum",
    ]
    if rows[0] != expected_header:
        message = "retained AVX2 CRAZY CSV header drifted"
        raise AssertionError(message)
    return tuple(
        _Sample(
            benchmark_id=row[0],
            width=int(row[1]),
            implementation=row[2],
            sample=int(row[3]),
            nanoseconds=int(row[4]),
            checksum=int(row[5]),
        )
        for row in rows[1:]
    )


def _metadata() -> dict[str, object]:
    return cast(
        "dict[str, object]",
        json.loads((EVIDENCE / "metadata.json").read_text()),
    )


def _route(samples: tuple[_Sample, ...], prefix: str) -> tuple[_Sample, ...]:
    return tuple(
        sample
        for sample in samples
        if sample.implementation.startswith(prefix)
    )


def test_retained_avx2_evidence_is_secondary_clean_source_evidence() -> None:
    """Bind retained SIMD data to clean source without granting selection."""
    metadata = _metadata()
    source = (EVIDENCE / "source-commit.txt").read_text().strip()
    assert source == EXPECTED_SOURCE_COMMIT
    assert metadata["source_commit"] == EXPECTED_SOURCE_COMMIT
    assert metadata["benchmark_id"] == EXPECTED_BENCHMARK_ID
    assert metadata["host_class"] == EXPECTED_HOST_CLASS
    assert metadata["selection_authority"] is False
    assert metadata["simd_isa"] == EXPECTED_SIMD_ISA
    assert metadata["simd_lanes"] == EXPECTED_SIMD_LANES
    codegen = cast("dict[str, int]", metadata["codegen"])
    assert codegen["vpgatherdd_count"] == EXPECTED_GATHER_COUNT


def test_retained_avx2_raw_matrix_has_exact_identity_and_checksums() -> None:
    """All 225 rows preserve workload identity and reviewed scalar semantics."""
    samples = _samples()
    assert len(samples) == EXPECTED_ROW_COUNT
    assert {sample.benchmark_id for sample in samples} == {
        EXPECTED_BENCHMARK_ID
    }
    assert {sample.width for sample in samples} == set(EXPECTED_WIDTHS)
    for width in EXPECTED_WIDTHS:
        width_samples = tuple(
            sample for sample in samples if sample.width == width
        )
        assert len(width_samples) == (
            EXPECTED_SAMPLE_COUNT * EXPECTED_ROUTE_COUNT
        )
        assert {sample.checksum for sample in width_samples} == {
            EXPECTED_CHECKSUMS[width]
        }
        implementations = {sample.implementation for sample in width_samples}
        assert len(implementations) == EXPECTED_ROUTE_COUNT
        for implementation in implementations:
            route = tuple(
                sample
                for sample in width_samples
                if sample.implementation == implementation
            )
            assert tuple(sorted(sample.sample for sample in route)) == tuple(
                range(EXPECTED_SAMPLE_COUNT)
            )


def test_retained_avx2_medians_and_paired_wins_derive_from_raw() -> None:
    """AVX2 beats scalar padded by median at every retained secondary width."""
    samples = _samples()
    for width in EXPECTED_WIDTHS:
        width_samples = tuple(
            sample for sample in samples if sample.width == width
        )
        padded = _route(width_samples, "scalar-padded")
        avx2 = _route(width_samples, "avx2-padded")
        padded_by_sample = sorted(padded, key=lambda sample: sample.sample)
        avx2_by_sample = sorted(avx2, key=lambda sample: sample.sample)
        padded_median = int(median(sample.nanoseconds for sample in padded))
        avx2_median = int(median(sample.nanoseconds for sample in avx2))
        paired_wins = sum(
            avx2_sample.nanoseconds < padded_sample.nanoseconds
            for padded_sample, avx2_sample in zip(
                padded_by_sample,
                avx2_by_sample,
                strict=True,
            )
        )
        assert padded_median == EXPECTED_PADDED_MEDIANS[width]
        assert avx2_median == EXPECTED_AVX2_MEDIANS[width]
        assert avx2_median < padded_median
        assert paired_wins == EXPECTED_AVX2_WINS[width]
