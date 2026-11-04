# Copyright:
#   - Copyright © 2026 Alberto Villa Osorno.
# SPDX-License-Identifier:
#   - LicenseRef-Proprietary
# Confidential:
#   - true
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

import csv
import hashlib
from collections import Counter
from hashlib import sha256
from io import StringIO
from typing import TYPE_CHECKING, Any, Final, Never

if TYPE_CHECKING:
    from collections.abc import Iterator

from benchmarks.arena import analyze, csv_admission

# Retain the native source-digest provider across public alias substitutions.
_NATIVE_SHA256 = sha256
# Compare retained rows with the source-native multiset constructor.
_SOURCE_COUNTER = Counter
_SOURCE_STRING_IO = StringIO
_SOURCE_TYPE = type
_SOURCE_ANY = any
_SOURCE_SET = set
_SOURCE_LEN = len
_SOURCE_TUPLE = tuple
_SOURCE_NEXT = next
_SOURCE_LIST = list
# A replaced csv.reader must not be the authority for the retained source.
_SOURCE_CSV_READER = csv.reader
# Preserve the bounded source column scanner against public substitution.
_SOURCE_COLUMN_LIMIT = csv_admission.within_column_limit

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
METRIC_FIELDS: Final = _SOURCE_TUPLE(sorted(analyze.COST_METRICS - {ENERGY}))
HEADER: Final = (*IDENTITY_FIELDS, *METRIC_FIELDS)
METRIC_FIELDS_2: Final = _SOURCE_TUPLE(sorted(analyze.COST_METRICS))
HEADER_2: Final = (*IDENTITY_FIELDS, *METRIC_FIELDS_2)
# Keep the admitted v1/v2 wire schema and resource limits stable even if
# public format metadata is rebound after this module has been imported.
_SOURCE_RAW_SCHEMA_VERSION = RAW_SCHEMA_VERSION
_SOURCE_RAW_SCHEMA_VERSION_2 = RAW_SCHEMA_VERSION_2
_SOURCE_IDENTITY_FIELDS = IDENTITY_FIELDS
_SOURCE_METRIC_FIELDS = METRIC_FIELDS
_SOURCE_METRIC_FIELDS_2 = METRIC_FIELDS_2
_SOURCE_HEADER = HEADER
_SOURCE_HEADER_2 = HEADER_2
_SOURCE_MAX_RAW_BYTES = MAX_RAW_BYTES
_SOURCE_MAX_CSV_HEADER_CHARS = MAX_CSV_HEADER_CHARS
# Direct raw callers must retain the same required report shape even when
# the separately imported analyzer's public schema sets are mutated.
_SOURCE_OBSERVATION_FIELDS = frozenset(analyze.OBSERVATION_FIELDS)
_SOURCE_CASE_FIELDS = frozenset(analyze.CASE_FIELDS)
_SOURCE_COST_METRICS = analyze.COST_METRICS
_SOURCE_ELAPSED = analyze.ELAPSED
# A direct raw receipt also preserves native outcome/verifier semantics.
_SOURCE_NUL = analyze.NUL
_SOURCE_OUTCOMES = analyze.OUTCOMES
_SOURCE_VERDICTS = frozenset({analyze.ACCEPTED, analyze.REJECTED, analyze.NOT_RUN})
_SOURCE_VERIFIED = analyze.VERIFIED
_SOURCE_VERIFIER_REJECTED = analyze.VERIFIER_REJECTED
_SOURCE_ACCEPTED = analyze.ACCEPTED
_SOURCE_REJECTED = analyze.REJECTED
# Direct raw comparison must not certify an invalid row through a replaced
# analyzer validator or a replaced helper used transitively by that validator.
_SOURCE_SEMANTIC_GETATTR = getattr
_SOURCE_SEMANTIC_ANY = any
_SOURCE_ANALYZER_SEMANTIC_HELPERS = (
    ("_fail", analyze._fail),  # ruff: ignore[private-member-access]
    ("_mapping", analyze._mapping),  # ruff: ignore[private-member-access]
    ("_text", analyze._text),  # ruff: ignore[private-member-access]
    ("_integer", analyze._integer),  # ruff: ignore[private-member-access]
    ("_hash", analyze._hash),  # ruff: ignore[private-member-access]
    ("_relative", analyze._relative),  # ruff: ignore[private-member-access]
    ("_case", analyze._case),  # ruff: ignore[private-member-access]
    ("_verdict", analyze._verdict),  # ruff: ignore[private-member-access]
    ("_metrics_shape", analyze._metrics_shape),  # ruff: ignore[private-member-access]
)
# True native hashes cannot become invalid when public analyzer schema names
# are replaced after raw admission imports its source grammar.
_SOURCE_SHA256_HEX_LENGTH = analyze.SHA256_HEX_LENGTH
_SOURCE_SHA256_ALPHABET = analyze.SHA256_ALPHABET


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
    if not _SOURCE_SET(values) <= _SOURCE_SET(metrics):
        _fail("raw CSV schema cannot omit reported energy_uj metric")
    return (
        *identity,
        *(str(values[name]) if name in values else "" for name in metrics),
    )


def _require_native_csv_row(row: object, label: str) -> None:
    # The stdlib csv.reader returns native list[str]. Require that identity
    # before evaluating equality or hashing any parser-provided objects.
    if _SOURCE_TYPE(row) is not _SOURCE_LIST or _SOURCE_ANY(
        _SOURCE_TYPE(field) is not str for field in row
    ):
        _fail(f"{label}: arena raw CSV parser returned non-native CSV row")


def _header_schema(header: list[str] | None, label: str) -> tuple[str, tuple[str, ...]]:
    if header is not None:
        _require_native_csv_row(header, label)
    if header == _SOURCE_LIST(_SOURCE_HEADER):
        return _SOURCE_RAW_SCHEMA_VERSION, _SOURCE_METRIC_FIELDS
    if header == _SOURCE_LIST(_SOURCE_HEADER_2):
        return _SOURCE_RAW_SCHEMA_VERSION_2, _SOURCE_METRIC_FIELDS_2
    _fail(f"{label}: invalid arena-raw-v1/v2 CSV header")


def _require_bounded_csv_header(text: str, label: str) -> None:
    # Preflight the first physical line before csv.reader builds a field list.
    # An open quoted field may otherwise consume many newline-delimited rows.
    prefix = text[: _SOURCE_MAX_CSV_HEADER_CHARS + 1]
    first_line = prefix.split("\n", maxsplit=1)[0].split("\r", maxsplit=1)[0]
    if _SOURCE_LEN(first_line) > _SOURCE_MAX_CSV_HEADER_CHARS or first_line.count('"') % 2:
        _fail(f"{label}: invalid or oversized arena raw CSV header")


def _limited_rows(
    reader: Iterator[list[str]], label: str, expected_rows: int
) -> list[tuple[str, ...]]:
    rows: list[tuple[str, ...]] = []
    for row in reader:
        if _SOURCE_LEN(rows) >= expected_rows:
            _fail(f"{label}: raw CSV has more rows than reported trials")
        _require_native_csv_row(row, label)
        rows.append(_SOURCE_TUPLE(row))
    return rows


def _csv_rows(
    text: str,
    label: str,
    *,
    expected_rows: int,
) -> tuple[str, tuple[str, ...], list[tuple[str, ...]]]:
    _require_bounded_csv_header(text, label)
    try:
        column_receipt = csv_admission.within_column_limit(text, _SOURCE_LEN(_SOURCE_HEADER_2))
    except Exception as error:
        # A substituted preflight dependency cannot leak arbitrary host faults.
        message = f"{label}: arena raw CSV column preflight failed"
        raise RawSampleError(message) from error
    if _SOURCE_TYPE(column_receipt) is not bool:
        _fail(f"{label}: arena raw CSV column preflight returned nonnative verdict")
    if not column_receipt:
        _fail(f"{label}: arena raw CSV columns exceed registered count")
    # A substituted guard can return exact True while concealing a row with
    # thousands of fields. Confirm the source scan before parser allocation.
    try:
        source_receipt = _SOURCE_COLUMN_LIMIT(text, _SOURCE_LEN(_SOURCE_HEADER_2))
    except Exception as error:
        message = f"{label}: arena raw CSV source column preflight failed"
        raise RawSampleError(message) from error
    if _SOURCE_TYPE(source_receipt) is not bool or not source_receipt:
        _fail(f"{label}: arena raw CSV columns exceed registered count")
    try:
        reader = csv.reader(_SOURCE_STRING_IO(text, newline=""), strict=True)
        header = _SOURCE_NEXT(reader, None)
        version, metrics = _header_schema(header, label)
        rows = _limited_rows(reader, label, expected_rows)
        # Exact native list[str] rows do not prove that a replaceable parser
        # actually read the supplied bytes. Reparse the same bounded source
        # through the import-bound stdlib reader before admitting a match.
        source_reader = _SOURCE_CSV_READER(_SOURCE_STRING_IO(text, newline=""), strict=True)
        source_header = _SOURCE_NEXT(source_reader, None)
        if source_header is not None:
            _require_native_csv_row(source_header, label)
        source_rows = _limited_rows(source_reader, label, expected_rows)
        if header != source_header or rows != source_rows:
            _fail(f"{label}: arena raw CSV parser differs from source CSV")
    except RawSampleError as error:
        # Only our own exact rejection type may cross this boundary unchanged.
        # A foreign parser can raise a subclass with hostile format hooks.
        if _SOURCE_TYPE(error) is RawSampleError:
            raise
        message = f"{label}: invalid arena raw CSV parser: {_SOURCE_TYPE(error).__name__}"
        raise RawSampleError(message) from error
    except csv.Error as error:
        # Even an exact native csv.Error can contain caller-owned arguments.
        detail = (
            error.args[0]
            if _SOURCE_TYPE(error) is csv.Error
            and _SOURCE_LEN(error.args) == 1
            and _SOURCE_TYPE(error.args[0]) is str
            else _SOURCE_TYPE(error).__name__
        )
        message = f"{label}: invalid arena raw CSV quotes: {detail}"
        raise RawSampleError(message) from error
    except Exception as error:
        # Unexpected ordinary CSV dependency faults must stay typed and must
        # not invoke a foreign exception formatter while being rejected.
        message = f"{label}: invalid arena raw CSV parser: {_SOURCE_TYPE(error).__name__}"
        raise RawSampleError(message) from error
    return version, metrics, rows


def _decode_raw(raw: bytes, label: str) -> str:
    # Hash and parse the same actual bytes; subclass decoders can forge rows.
    if _SOURCE_TYPE(raw) is not bytes:
        _fail(f"{label}: arena raw CSV requires exact bytes")
    if not raw or _SOURCE_LEN(raw) > _SOURCE_MAX_RAW_BYTES:
        _fail(f"{label}: missing or oversized arena raw CSV")
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeError as error:
        message = f"{label}: invalid arena raw CSV UTF-8: {error}"
        raise RawSampleError(message) from error
    if _SOURCE_NUL in text:
        _fail(f"{label}: NUL in arena raw CSV")
    return text


def _require_analyzer_semantic_helpers(label: str) -> None:
    # The public module can be rebound while the raw checker remains loaded.
    # In particular, a replaced _fail would silence downstream source checks.
    if _SOURCE_SEMANTIC_ANY(
        _SOURCE_SEMANTIC_GETATTR(analyze, name) is not retained
        for name, retained in _SOURCE_ANALYZER_SEMANTIC_HELPERS
    ):
        _fail(f"{label}: invalid reported trial semantic validator changed")


def _validate_trial_semantics(row: dict[str, Any], label: str) -> None:
    """Reuse the analyzer's context-free row rules for direct CSV callers.

    The study budget/objectives remain the caller's separate admission job;
    these native trial fields must still be meaningful before a digest is
    returned, even when CSV bytes exactly match a fabricated row.
    """
    where = f"{label}: reported trial"
    try:
        _require_analyzer_semantic_helpers(label)
        analyze._text(row["algorithm"], f"{where}.algorithm")  # ruff: ignore[private-member-access]
        analyze._case(row["case"], where)  # ruff: ignore[private-member-access]
        analyze._integer(row["trial"], f"{where}.trial")  # ruff: ignore[private-member-access]
        analyze._verdict(row, where)  # ruff: ignore[private-member-access]
        analyze._relative(row["experiment_manifest"], f"{where}.experiment_manifest")  # ruff: ignore[private-member-access]
        analyze._relative(row["raw_sample"], f"{where}.raw_sample")  # ruff: ignore[private-member-access]
        analyze._metrics_shape(row["metrics"], where)  # ruff: ignore[private-member-access]
        _require_analyzer_semantic_helpers(label)
    except Exception as error:
        message = f"{label}: invalid reported trial semantics"
        raise RawSampleError(message) from error


def _admit_observation_containers(
    observations: list[dict[str, Any]], label: str
) -> None:
    """Require native pre-admitted row shapes before constructing CSV values."""
    message = f"{label}: raw CSV requires native nonempty observation rows"
    if _SOURCE_TYPE(observations) is not _SOURCE_LIST or not observations:
        _fail(message)
    seen_trials: set[tuple[str, str, int, int, int, int]] = _SOURCE_SET()
    for row in observations:
        if (
            _SOURCE_TYPE(row) is not dict
            or _SOURCE_ANY(_SOURCE_TYPE(name) is not str for name in row)
            or _SOURCE_SET(row) != _SOURCE_OBSERVATION_FIELDS
        ):
            _fail(message)
        case = row["case"]
        metrics = row["metrics"]
        if (
            _SOURCE_TYPE(case) is not dict
            or _SOURCE_ANY(_SOURCE_TYPE(name) is not str for name in case)
            or _SOURCE_SET(case) != _SOURCE_CASE_FIELDS
            or _SOURCE_TYPE(metrics) is not dict
            or _SOURCE_ANY(_SOURCE_TYPE(name) is not str for name in metrics)
            or not _SOURCE_SET(metrics) <= _SOURCE_COST_METRICS
            or _SOURCE_ELAPSED not in metrics
        ):
            _fail(message)
        if (
            _SOURCE_ANY(
                _SOURCE_TYPE(row[name]) is not str
                for name in (
                    "algorithm",
                    "outcome",
                    "verifier",
                    "verifier_verdict",
                    "experiment_manifest",
                    "raw_sample",
                )
            )
            or _SOURCE_TYPE(row["trial"]) is not int
            or _SOURCE_ANY(
                _SOURCE_TYPE(case[name]) is not str
                for name in ("family", "workload_sha256")
            )
            or _SOURCE_ANY(
                _SOURCE_TYPE(case[name]) is not int
                for name in ("version", "difficulty", "seed")
            )
            or _SOURCE_ANY(
                _SOURCE_TYPE(quantity) is not int for quantity in metrics.values()
            )
        ):
            _fail(message)
        # The imported analyzer's public symbols may be replaced by an
        # optimizer caller; independent verifier verdicts remain fixed here.
        outcome = row["outcome"]
        verdict = row["verifier_verdict"]
        if (
            outcome not in _SOURCE_OUTCOMES
            or verdict not in _SOURCE_VERDICTS
            or (outcome == _SOURCE_VERIFIED) != (verdict == _SOURCE_ACCEPTED)
            or (outcome == _SOURCE_VERIFIER_REJECTED) != (verdict == _SOURCE_REJECTED)
            or (outcome == _SOURCE_VERIFIED and row["verifier"] == row["algorithm"])
        ):
            _fail(f"{label}: invalid reported trial semantics")
        _validate_trial_semantics(row, label)
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


def _checked_sha256(raw: bytes) -> str:
    """Bind raw source bytes to an independently corroborated native digest.

    The caller-selected hash provider cannot certify a different source by
    returning a plausible constant or a foreign equality-controlled string.
    This checks hash output integrity, not authenticity of the source itself.
    """
    if _SOURCE_TYPE(raw) is not bytes:
        _fail("arena raw CSV SHA-256 requires exact bytes")
    try:
        reported = sha256(raw).hexdigest()
        # Keep the cross-check on a separate provider entrypoint: the module
        # attribute hashlib.sha256 can be replaced alongside the bound alias.
        independent = hashlib.new("sha256", raw).hexdigest()
        source_bound = _NATIVE_SHA256(raw).hexdigest()
    except Exception as error:
        message = "arena raw CSV SHA-256 dependency failed"
        raise RawSampleError(message) from error
    if (
        _SOURCE_TYPE(reported) is not str
        or _SOURCE_TYPE(independent) is not str
        or _SOURCE_TYPE(source_bound) is not str
        or _SOURCE_LEN(source_bound) != _SOURCE_SHA256_HEX_LENGTH
        or _SOURCE_LEN(reported) != _SOURCE_SHA256_HEX_LENGTH
        or _SOURCE_LEN(independent) != _SOURCE_SHA256_HEX_LENGTH
        or not _SOURCE_SET(reported) <= _SOURCE_SHA256_ALPHABET
        or reported != source_bound
        or independent != source_bound
    ):
        _fail("arena raw CSV SHA-256 receipt differs from source bytes")
    return reported


def check_rows(
    raw: bytes,
    observations: list[dict[str, Any]],
    label: str,
) -> str:
    """Reject raw CSV that differs from declared trial identities or costs.

    Returns:
        SHA-256 of the exact inspected source bytes for reproducible review.

    """
    if _SOURCE_TYPE(label) is not str:
        _fail("arena raw CSV requires an exact string label")
    text = _decode_raw(raw, label)
    _admit_observation_containers(observations, label)
    version, metrics, actual_rows = _csv_rows(
        text, label, expected_rows=_SOURCE_LEN(observations)
    )
    if _SOURCE_ANY(
        _SOURCE_LEN(row) != _SOURCE_LEN(_SOURCE_IDENTITY_FIELDS) + _SOURCE_LEN(metrics) for row in actual_rows
    ):
        _fail(f"{label}: malformed arena raw CSV row")
    try:
        expected = _SOURCE_COUNTER(
            _row_values(item, version, metrics) for item in observations
        )
    except RawSampleError:
        raise
    except ValueError as error:
        # Python may refuse an immense native integer's decimal conversion.
        message = f"{label}: raw CSV integer conversion failed"
        raise RawSampleError(message) from error
    if _SOURCE_COUNTER(actual_rows) != expected:
        _fail(f"{label}: raw CSV trial/metric rows differ from arena report")
    return _checked_sha256(raw)
