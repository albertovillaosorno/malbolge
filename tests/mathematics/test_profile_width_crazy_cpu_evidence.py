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
#   - Integrity checks for retained secondary-host CPU CRAZY geometry evidence.
# - Must-Not:
#   - Treat Linux timing as primary Windows or SIMD selection authority.
# - Allows:
#   - Inputs: tracked raw CSV, metadata, and clean source-commit provenance.
#   - Outputs: deterministic sample, checksum, and median assertions.
#   - Side effects: tracked evidence reads only.
# - Split-When:
#   - Split when primary-host or genuine SIMD evidence gains another identity.
# - Merge-When:
#   - Merge when another test owns this exact retained CPU evidence directory.
# - Summary:
#   - Locks the N10-N14 scalar/native/padded secondary Linux CPU baseline.
# - Description:
#   - Recomputes cardinality, checksum equality, and medians from raw samples.
# - Usage:
#   - Run on every validation host without executing the benchmark.
# - Defaults:
#   - This secondary-host evidence has no product route-selection authority.
#

"""Integrity checks for retained secondary Linux CPU CRAZY geometry evidence."""

from __future__ import annotations

import csv
from dataclasses import dataclass
import json
from pathlib import Path
from statistics import median
from typing import Final
from typing import cast

EVIDENCE: Final = (
    Path("benchmarks/interpreter/evidence")
    / "2026-09-04-profile-crazy-geometry-linux-x86_64"
)
EXPECTED_SOURCE_COMMIT: Final = "fe06b1eead6adbb2b281fa7c5bf7cac566385083"
EXPECTED_WIDTHS: Final = (10, 11, 12, 13, 14)
EXPECTED_SAMPLE_COUNT: Final = 15
EXPECTED_HOST_CLASS: Final = "secondary-linux-x86_64"
EXPECTED_IMPLEMENTATIONS: Final = {
    10: ("native-5+5", "padded-5+5", "scalar-tritwise"),
    11: ("native-5+5+1", "padded-5+5+5", "scalar-tritwise"),
    12: ("native-5+5+2", "padded-5+5+5", "scalar-tritwise"),
    13: ("native-5+5+3", "padded-5+5+5", "scalar-tritwise"),
    14: ("native-5+5+4", "padded-5+5+5", "scalar-tritwise"),
}
EXPECTED_MEDIANS: Final = {
    (10, "native-5+5"): 68_638_975,
    (10, "padded-5+5"): 82_851_139,
    (10, "scalar-tritwise"): 127_513_279,
    (11, "native-5+5+1"): 92_840_228,
    (11, "padded-5+5+5"): 124_393_578,
    (11, "scalar-tritwise"): 140_311_051,
    (12, "native-5+5+2"): 92_488_900,
    (12, "padded-5+5+5"): 123_592_919,
    (12, "scalar-tritwise"): 150_706_130,
    (13, "native-5+5+3"): 94_132_729,
    (13, "padded-5+5+5"): 123_403_223,
    (13, "scalar-tritwise"): 162_991_674,
    (14, "native-5+5+4"): 97_199_554,
    (14, "padded-5+5+5"): 123_557_926,
    (14, "scalar-tritwise"): 174_351_208,
}


@dataclass(frozen=True, slots=True)
class _Sample:
    benchmark: str
    checksum: int
    implementation: str
    nanoseconds: int
    sample: int


def _samples() -> tuple[_Sample, ...]:
    with (EVIDENCE / "raw.csv").open(newline="") as handle:
        rows = list(csv.reader(handle))
    header = rows[0]
    if header != [
        "benchmark",
        "implementation",
        "sample",
        "nanoseconds",
        "checksum",
    ]:
        message = "retained CPU CRAZY CSV header drifted"
        raise AssertionError(message)
    return tuple(
        _Sample(
            benchmark=row[0],
            implementation=row[1],
            sample=int(row[2]),
            nanoseconds=int(row[3]),
            checksum=int(row[4]),
        )
        for row in rows[1:]
    )


def _metadata() -> dict[str, object]:
    return cast(
        "dict[str, object]",
        json.loads((EVIDENCE / "metadata.json").read_text()),
    )


def _width(benchmark: str) -> int:
    return int(benchmark.rsplit("-", maxsplit=1)[1])


def test_retained_cpu_crazy_evidence_is_secondary_and_complete() -> None:
    """Retained rows remain clean-source secondary evidence, not selection."""
    metadata = _metadata()
    source = (EVIDENCE / "source-commit.txt").read_text().strip()
    assert source == EXPECTED_SOURCE_COMMIT
    assert metadata["source_commit"] == EXPECTED_SOURCE_COMMIT
    assert metadata["host_class"] == EXPECTED_HOST_CLASS
    assert metadata["selection_authority"] is False
    assert metadata["simd_variant_present"] is False
    assert len(_samples()) == (
        len(EXPECTED_WIDTHS)
        * len(next(iter(EXPECTED_IMPLEMENTATIONS.values())))
        * EXPECTED_SAMPLE_COUNT
    )


def test_retained_cpu_crazy_raw_samples_recompute_documented_medians() -> None:
    """Every route has 15 samples, common semantics, and exact raw medians."""
    samples = _samples()
    for width in EXPECTED_WIDTHS:
        width_samples = tuple(
            sample for sample in samples if _width(sample.benchmark) == width
        )
        assert len({sample.checksum for sample in width_samples}) == 1
        medians: dict[str, int] = {}
        for implementation in EXPECTED_IMPLEMENTATIONS[width]:
            route = tuple(
                sample
                for sample in width_samples
                if sample.implementation == implementation
            )
            assert tuple(sorted(sample.sample for sample in route)) == tuple(
                range(EXPECTED_SAMPLE_COUNT)
            )
            observed = int(median(sample.nanoseconds for sample in route))
            assert observed == EXPECTED_MEDIANS[width, implementation]
            medians[implementation] = observed
        native, padded, scalar = EXPECTED_IMPLEMENTATIONS[width]
        assert medians[native] < medians[padded] < medians[scalar]
