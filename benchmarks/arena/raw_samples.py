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
#   - Exact versioned arena CSV identity and measurement cross-checks.
# - Must-Not:
#   - Certify raw measurements, execute verifiers, or alter trial outcomes.
# - Allows:
#   - Inputs: bounded retained CSV bytes and admitted JSON observation rows.
#   - Outputs: source-byte SHA-256 and exact row-match evidence.
#   - Side effects: none.
# - Split-When:
#   - Further raw metric vocabularies require independent version admission.
# - Merge-When:
#   - The benchmark protocol owns this exact raw-row schema directly.
# - Summary:
#   - Prevents detached arena metrics from claiming unrelated raw samples.
# - Description:
#   - Binds all reported trials and costs to canonical v1/v2 CSV rows.
# - Usage:
#   - Invoked by the optional arena evidence preflight.
# - Defaults:
#   - Unexpected, duplicate, absent, or mismatched rows fail closed.
#

"""Exact versioned CSV row admission for reported arena measurements."""

from __future__ import annotations

from collections import Counter
import csv
from hashlib import sha256
from io import StringIO
from typing import Any
from typing import Final
from typing import Never
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator

from benchmarks.arena import analyze, csv_admission

RAW_SCHEMA_VERSION: Final = "1"
RAW_SCHEMA_VERSION_2: Final = "2"
ENERGY: Final = "energy_uj"
MAX_RAW_BYTES: Final = 16 * 1024 * 1024
MAX_CSV_HEADER_CHARS: Final = 512
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
# V1 must remain byte-for-byte compatible with retained raw observations.
METRIC_FIELDS: Final = tuple(sorted(analyze.COST_METRICS - {ENERGY}))
HEADER: Final = (*IDENTITY_FIELDS, *METRIC_FIELDS)
METRIC_FIELDS_2: Final = tuple(sorted(analyze.COST_METRICS))
HEADER_2: Final = (*IDENTITY_FIELDS, *METRIC_FIELDS_2)


class RawSampleError(ValueError):
    """Raw CSV evidence does not exactly match admitted arena observations."""


def _fail(message: str) -> Never:
    raise RawSampleError(message)


def _row_values(
    observation: dict[str, Any],
    version: str,
    metrics: tuple[str, ...],
) -> tuple[str, ...]:
    case = observation["case"]
    identity = (
        version,
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
    values = observation["metrics"]
    if not set(values) <= set(metrics):
        _fail("raw CSV schema cannot omit reported energy_uj metric")
    return (
        *identity,
        *(str(values[name]) if name in values else "" for name in metrics),
    )


def _require_native_csv_row(row: object, label: str) -> None:
    # The stdlib csv.reader returns native list[str]. Require that identity
    # before evaluating equality or hashing any parser-provided objects.
    if type(row) is not list or any(type(field) is not str for field in row):
        _fail(f"{label}: arena raw CSV parser returned non-native CSV row")


def _header_schema(
    header: list[str] | None, label: str
) -> tuple[str, tuple[str, ...]]:
    if header is not None:
        _require_native_csv_row(header, label)
    if header == list(HEADER):
        return RAW_SCHEMA_VERSION, METRIC_FIELDS
    if header == list(HEADER_2):
        return RAW_SCHEMA_VERSION_2, METRIC_FIELDS_2
    _fail(f"{label}: invalid arena-raw-v1/v2 CSV header")


def _require_bounded_csv_header(text: str, label: str) -> None:
    # Preflight the first physical line before csv.reader builds a field list.
    # An open quoted field may otherwise consume many newline-delimited rows.
    prefix = text[: MAX_CSV_HEADER_CHARS + 1]
    first_line = prefix.split("\n", maxsplit=1)[0].split("\r", maxsplit=1)[0]
    if len(first_line) > MAX_CSV_HEADER_CHARS or first_line.count('"') % 2:
        _fail(f"{label}: invalid or oversized arena raw CSV header")


def _limited_rows(
    reader: Iterator[list[str]], label: str, expected_rows: int
) -> list[tuple[str, ...]]:
    rows: list[tuple[str, ...]] = []
    for row in reader:
        if len(rows) >= expected_rows:
            _fail(f"{label}: raw CSV has more rows than reported trials")
        _require_native_csv_row(row, label)
        rows.append(tuple(row))
    return rows


def _csv_rows(
    text: str,
    label: str,
    *,
    expected_rows: int,
) -> tuple[str, tuple[str, ...], list[tuple[str, ...]]]:
    _require_bounded_csv_header(text, label)
    try:
        column_receipt = csv_admission.within_column_limit(text, len(HEADER_2))
    except Exception as error:
        # A substituted preflight dependency cannot leak arbitrary host faults.
        message = f"{label}: arena raw CSV column preflight failed"
        raise RawSampleError(message) from error
    if type(column_receipt) is not bool:
        _fail(f"{label}: arena raw CSV column preflight returned nonnative verdict")
    if not column_receipt:
        _fail(f"{label}: arena raw CSV columns exceed registered count")
    try:
        reader = csv.reader(StringIO(text, newline=""), strict=True)
        header = next(reader, None)
        version, metrics = _header_schema(header, label)
        rows = _limited_rows(reader, label, expected_rows)
    except RawSampleError as error:
        # Only our own exact rejection type may cross this boundary unchanged.
        # A foreign parser can raise a subclass with hostile format hooks.
        if type(error) is RawSampleError:
            raise
        message = f"{label}: invalid arena raw CSV parser: {type(error).__name__}"
        raise RawSampleError(message) from error
    except csv.Error as error:
        # Even an exact native csv.Error can contain caller-owned arguments.
        detail = (
            error.args[0]
            if type(error) is csv.Error
            and len(error.args) == 1
            and type(error.args[0]) is str
            else type(error).__name__
        )
        message = f"{label}: invalid arena raw CSV quotes: {detail}"
        raise RawSampleError(message) from error
    except Exception as error:
        # Unexpected ordinary CSV dependency faults must stay typed and must
        # not invoke a foreign exception formatter while being rejected.
        message = f"{label}: invalid arena raw CSV parser: {type(error).__name__}"
        raise RawSampleError(message) from error
    return version, metrics, rows


def _decode_raw(raw: bytes, label: str) -> str:
    # Hash and parse the same actual bytes; subclass decoders can forge rows.
    if type(raw) is not bytes:
        _fail(f"{label}: arena raw CSV requires exact bytes")
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


def _admit_observation_containers(
    observations: list[dict[str, Any]], label: str
) -> None:
    """Require native pre-admitted row shapes before constructing CSV values."""
    message = f"{label}: raw CSV requires native nonempty observation rows"
    if type(observations) is not list or not observations:
        _fail(message)
    seen_trials: set[tuple[str, str, int, int, int, int]] = set()
    for row in observations:
        if (
            type(row) is not dict
            or any(type(name) is not str for name in row)
            or set(row) != analyze.OBSERVATION_FIELDS
        ):
            _fail(message)
        case = row["case"]
        metrics = row["metrics"]
        if (
            type(case) is not dict
            or any(type(name) is not str for name in case)
            or set(case) != analyze.CASE_FIELDS
            or type(metrics) is not dict
            or any(type(name) is not str for name in metrics)
            or not set(metrics) <= analyze.COST_METRICS
            or analyze.ELAPSED not in metrics
        ):
            _fail(message)
        if (
            any(
                type(row[name]) is not str
                for name in (
                    "algorithm", "outcome", "verifier", "verifier_verdict",
                    "experiment_manifest", "raw_sample",
                )
            )
            or type(row["trial"]) is not int
            or any(type(case[name]) is not str for name in ("family", "workload_sha256"))
            or any(type(case[name]) is not int for name in ("version", "difficulty", "seed"))
            or any(type(quantity) is not int for quantity in metrics.values())
        ):
            _fail(message)
        # A self-consistent repeated CSV/observation pair is still only one
        # reported attempt. Match the analyzer's case/trial uniqueness key.
        trial_key = (
            row["algorithm"],
            case["family"],
            case["version"],
            case["difficulty"],
            case["seed"],
            row["trial"],
        )
        if trial_key in seen_trials:
            _fail(f"{label}: duplicate reported trial identity")
        seen_trials.add(trial_key)


def check_rows(
    raw: bytes,
    observations: list[dict[str, Any]],
    label: str,
) -> str:
    """Reject raw CSV that differs from declared trial identities or costs.

    Returns:
        SHA-256 of the exact inspected source bytes for reproducible review.

    """
    if type(label) is not str:
        _fail("arena raw CSV requires an exact string label")
    text = _decode_raw(raw, label)
    _admit_observation_containers(observations, label)
    version, metrics, actual_rows = _csv_rows(
        text, label, expected_rows=len(observations)
    )
    if any(
        len(row) != len(IDENTITY_FIELDS) + len(metrics) for row in actual_rows
    ):
        _fail(f"{label}: malformed arena raw CSV row")
    try:
        expected = Counter(
            _row_values(item, version, metrics) for item in observations
        )
    except RawSampleError:
        raise
    except ValueError as error:
        # Python may refuse an immense native integer's decimal conversion.
        message = f"{label}: raw CSV integer conversion failed"
        raise RawSampleError(message) from error
    if Counter(actual_rows) != expected:
        _fail(f"{label}: raw CSV trial/metric rows differ from arena report")
    return sha256(raw).hexdigest()
