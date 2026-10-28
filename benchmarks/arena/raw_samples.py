# Copyright:
#   - Copyright © 2026 Alberto Villa Osorno.
# SPDX-License-Identifier:
#   - Apache-2.0
# Confidential:
#   - false
# License-File:
#   - LICENSE
#
# Boundary-Contract:
# - Owns:
#   - Exact arena-raw-v1 CSV identity and measurement cross-checks.
# - Must-Not:
#   - Certify raw measurements, execute verifiers, or alter trial outcomes.
# - Allows:
#   - Inputs: bounded retained CSV bytes and admitted JSON observation rows.
#   - Outputs: source-byte SHA-256 and exact row-match evidence.
#   - Side effects: none.
# - Split-When:
#   - A separately versioned raw evidence format requires new admission.
# - Merge-When:
#   - The benchmark protocol owns this exact raw-row schema directly.
# - Summary:
#   - Prevents detached arena metrics from claiming unrelated raw samples.
# - Description:
#   - Binds all reported trials and costs to canonical version-one CSV rows.
# - Usage:
#   - Invoked by the optional arena evidence preflight.
# - Defaults:
#   - Unexpected, duplicate, absent, or mismatched rows fail closed.
#

"""Exact version-one CSV row admission for reported arena measurements."""

from __future__ import annotations

from collections import Counter
import csv
from hashlib import sha256
from io import StringIO
from typing import Any
from typing import Final
from typing import Never

from benchmarks.arena import analyze

RAW_SCHEMA_VERSION: Final = "1"
MAX_RAW_BYTES: Final = 16 * 1024 * 1024
IDENTITY_FIELDS: Final = (
    "schema_version",
    "algorithm",
    "family",
    "version",
    "difficulty",
    "seed",
    "workload_sha256",
    "trial",
    "outcome",
    "verifier",
    "verifier_verdict",
)
METRIC_FIELDS: Final = tuple(sorted(analyze.COST_METRICS))
HEADER: Final = (*IDENTITY_FIELDS, *METRIC_FIELDS)


class RawSampleError(ValueError):
    """Raw CSV evidence does not exactly match admitted arena observations."""


def _fail(message: str) -> Never:
    raise RawSampleError(message)


def _row_values(observation: dict[str, Any]) -> tuple[str, ...]:
    case = observation["case"]
    identity = (
        RAW_SCHEMA_VERSION,
        observation["algorithm"],
        case["family"],
        str(case["version"]),
        str(case["difficulty"]),
        str(case["seed"]),
        case["workload_sha256"],
        str(observation["trial"]),
        observation["outcome"],
        observation["verifier"],
        observation["verifier_verdict"],
    )
    metrics = observation["metrics"]
    return (
        *identity,
        *(
            str(metrics[name]) if name in metrics else ""
            for name in METRIC_FIELDS
        ),
    )


def _csv_rows(text: str, label: str) -> list[tuple[str, ...]]:
    try:
        reader = csv.reader(StringIO(text, newline=""), strict=True)
        header = next(reader, None)
        if header != list(HEADER):
            _fail(f"{label}: invalid arena-raw-v1 CSV header")
        return [tuple(row) for row in reader]
    except csv.Error as error:
        message = f"{label}: invalid arena raw CSV quotes: {error}"
        raise RawSampleError(message) from error


def _decode_raw(raw: bytes, label: str) -> str:
    if not raw or len(raw) > MAX_RAW_BYTES:
        _fail(f"{label}: missing or oversized arena raw CSV")
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeError as error:
        message = f"{label}: invalid arena raw CSV UTF-8: {error}"
        raise RawSampleError(message) from error
    if analyze.NUL in text:
        _fail(f"{label}: NUL in arena raw CSV")
    return text


def check_rows(
    raw: bytes,
    observations: list[dict[str, Any]],
    label: str,
) -> str:
    """Reject raw CSV that differs from declared trial identities or costs.

    Returns:
        SHA-256 of the exact inspected source bytes for reproducible review.

    """
    text = _decode_raw(raw, label)
    actual_rows = _csv_rows(text, label)
    if any(len(row) != len(HEADER) for row in actual_rows):
        _fail(f"{label}: malformed arena raw CSV row")
    expected = Counter(_row_values(item) for item in observations)
    if Counter(actual_rows) != expected:
        _fail(f"{label}: raw CSV trial/metric rows differ from arena report")
    return sha256(raw).hexdigest()
