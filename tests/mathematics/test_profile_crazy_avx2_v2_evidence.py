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
#   - Integrity checks for retained secondary-host AVX2 CRAZY v2 evidence.
# - Must-Not:
#   - Admit N15 as a runtime profile or grant Linux product-selection authority.
# - Allows:
#   - Inputs: tracked raw CSV, metadata, README, and clean source pin.
#   - Outputs: exact matrix, checksum, median, paired-win, and boundary checks.
#   - Side effects: tracked evidence reads only.
# - Split-When:
#   - Split when another benchmark version or primary-host run gains evidence.
# - Merge-When:
#   - Merge when another test owns this exact retained v2 evidence directory.
# - Summary:
#   - Locks N10-N15 AVX2 CRAZY arithmetic evidence from secondary Linux.
# - Description:
#   - Recomputes all retained statistics and N15 non-admission from raw data.
# - Usage:
#   - Run on every validation host without requiring AVX2 execution.
# - Defaults:
#   - N15 remains arithmetic-only and retained timing has no selection
#     authority.
#

"""Integrity checks for retained secondary Linux AVX2 CRAZY v2 evidence."""

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
    / "2026-09-04-profile-crazy-avx2-v2-linux-x86_64"
)
EXPECTED_SOURCE_COMMIT: Final = "76104c08990994ce88bc58570607f1f18d7f3bc4"
EXPECTED_BENCHMARK_ID: Final = "cpu-profile-crazy-avx2-v2"
EXPECTED_HOST_CLASS: Final = "secondary-linux-x86_64"
EXPECTED_WIDTHS: Final = (10, 11, 12, 13, 14, 15)
EXPECTED_SAMPLE_COUNT: Final = 15
EXPECTED_ROUTE_COUNT: Final = 3
EXPECTED_ROW_COUNT: Final = 270
EXPECTED_SIMD_ISA: Final = "AVX2"
EXPECTED_GATHER_COUNT: Final = 3
EXPECTED_CHECKSUMS: Final = {
    10: 27_683_170_464,
    11: 69_793_138_128,
    12: 255_944_874_432,
    13: 590_667_673_872,
    14: 1_594_938_108_864,
    15: 4_726_060_935_024,
}
EXPECTED_LOOKUP_MEDIANS: Final = {
    10: 6_272_158,
    11: 15_904_580,
    12: 15_970_617,
    13: 15_820_432,
    14: 15_825_825,
    15: 11_547_865,
}
EXPECTED_AVX2_MEDIANS: Final = {
    10: 4_702_211,
    11: 9_384_736,
    12: 9_386_911,
    13: 9_383_050,
    14: 9_342_688,
    15: 5_756_478,
}
EXPECTED_AVX2_WINS: Final = dict.fromkeys(EXPECTED_WIDTHS, 15)
SCALAR_TRITWISE: Final = "scalar-tritwise"
EXPECTED_N15_ROUTES: Final = {
    "avx2-full-5+5+5",
    "scalar-full-5+5+5",
    "scalar-tritwise",
}


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
    assert rows[0] == expected_header
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


def _width_samples(
    samples: tuple[_Sample, ...],
    width: int,
) -> tuple[_Sample, ...]:
    return tuple(sample for sample in samples if sample.width == width)


def _lookup_route(
    samples: tuple[_Sample, ...],
    prefix: str,
) -> tuple[_Sample, ...]:
    return tuple(
        sample
        for sample in samples
        if sample.implementation.startswith(prefix)
        and sample.implementation != SCALAR_TRITWISE
    )


def test_retained_v2_evidence_is_clean_secondary_arithmetic_evidence() -> None:
    """Bind v2 data to its clean source without admitting N15 or selection."""
    metadata = _metadata()
    source = (EVIDENCE / "source-commit.txt").read_text().strip()
    assert source == EXPECTED_SOURCE_COMMIT
    assert metadata["source_commit"] == EXPECTED_SOURCE_COMMIT
    assert metadata["benchmark_id"] == EXPECTED_BENCHMARK_ID
    assert metadata["host_class"] == EXPECTED_HOST_CLASS
    assert metadata["selection_authority"] is False
    assert metadata["n15_runtime_profile_admitted"] is False
    assert metadata["simd_isa"] == EXPECTED_SIMD_ISA
    codegen = cast("dict[str, int]", metadata["codegen"])
    assert codegen["vpgatherdd_count"] == EXPECTED_GATHER_COUNT


def test_retained_v2_raw_matrix_has_all_widths_and_exact_checksums() -> None:
    """All 270 rows preserve exact route cardinality and scalar semantics."""
    samples = _samples()
    assert len(samples) == EXPECTED_ROW_COUNT
    assert {sample.benchmark_id for sample in samples} == {
        EXPECTED_BENCHMARK_ID
    }
    assert {sample.width for sample in samples} == set(EXPECTED_WIDTHS)
    for width in EXPECTED_WIDTHS:
        width_samples = _width_samples(samples, width)
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


def test_retained_v2_n15_is_named_as_three_full_chunks() -> None:
    """The measured boundary records full chunks, not padded semantics."""
    n15 = _width_samples(_samples(), 15)
    assert {sample.implementation for sample in n15} == EXPECTED_N15_ROUTES
    assert {sample.checksum for sample in n15} == {EXPECTED_CHECKSUMS[15]}


def test_retained_v2_medians_and_paired_wins_derive_from_raw() -> None:
    """AVX2 beats the scalar lookup route at every retained arithmetic width."""
    samples = _samples()
    for width in EXPECTED_WIDTHS:
        width_samples = _width_samples(samples, width)
        scalar = _lookup_route(width_samples, "scalar-")
        avx2 = _lookup_route(width_samples, "avx2-")
        scalar_by_sample = sorted(scalar, key=lambda sample: sample.sample)
        avx2_by_sample = sorted(avx2, key=lambda sample: sample.sample)
        scalar_median = int(median(sample.nanoseconds for sample in scalar))
        avx2_median = int(median(sample.nanoseconds for sample in avx2))
        paired_wins = sum(
            avx2_sample.nanoseconds < scalar_sample.nanoseconds
            for scalar_sample, avx2_sample in zip(
                scalar_by_sample,
                avx2_by_sample,
                strict=True,
            )
        )
        assert scalar_median == EXPECTED_LOOKUP_MEDIANS[width]
        assert avx2_median == EXPECTED_AVX2_MEDIANS[width]
        assert avx2_median < scalar_median
        assert paired_wins == EXPECTED_AVX2_WINS[width]
