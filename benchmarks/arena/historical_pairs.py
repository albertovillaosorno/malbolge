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
#   - Read-only adapter for retained paired classic verifier timing studies.
# - Must-Not:
#   - Re-measure historical runs or certify a source-reported verifier result.
# - Allows:
#   - Inputs: bounded, linked research benchmark, manifest and paired CSV.
#   - Outputs: arena comparison with source-byte hashes and evidence limits.
#   - Side effects: read repository-local historical evidence only.
# - Split-When:
#   - Other research measurement formats need distinct source adapters.
# - Merge-When:
#   - A governed generic source-backed experiment importer replaces it.
# - Summary:
#   - Replays retained paired timing evidence through the arena analyzer.
# - Description:
#   - Validates matching source identities and reported quality-map parity.
# - Usage:
#   - `python -B -m benchmarks.arena.historical_pairs SOURCE --root .`.
# - Defaults:
#   - Unsupported, malformed or inconsistent source evidence fails closed.
#

"""Import two retained classic paired timing formats as reported evidence."""

from __future__ import annotations

import argparse
import csv
import json
import string
import sys
from dataclasses import dataclass
from hashlib import sha256
from io import StringIO
from pathlib import Path
from typing import TYPE_CHECKING, Any, Never

import tomllib

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence

from benchmarks.arena import analyze, csv_admission, evidence, report_output
from scripts.validate import benchmark_protocol, experiment_manifest

MAX_SOURCE_BYTES = 4 * 1024 * 1024
MAX_CSV_HEADER_CHARS = 512
MAX_HISTORICAL_REPETITIONS = 4096
ASCII_DIGITS = frozenset(string.digits)
HEX_DIGITS = frozenset(string.hexdigits.lower())
ELAPSED_SOURCE_FIELD = "elapsed_nanoseconds"
DISCHARGED = "structurally_discharged_candidates"
RUN_SUCCEEDED = "success"
CLASSIC_PROFILE = "malbolge-1998"
DETERMINISTIC_KIND = "deterministic"
SECONDS_TO_NS = 1_000_000_000
MIB_TO_BYTES = 1_048_576
EXTENSION_CONFIG = {
    "prefix_decomposition_measurement": (
        "decomposed_strategy",
        "accepted_candidate_count",
        "candidate_count",
        "decomposed_verifier_calls",
    ),
    "verified_block_reuse_measurement": (
        "reuse_strategy",
        "accepted_request_count",
        "request_count",
        "reuse_verifier_calls",
    ),
}
REGISTERED_RAW_COLUMNS = {
    "prefix_decomposition_measurement": frozenset({
        "repetition",
        "strategy_id",
        "candidate_count",
        "independent_verifier_calls",
        "full_candidate_verifications",
        "structurally_discharged_candidates",
        "accepted_candidate_count",
        "best_verified_quality",
        "quality_map_sha256",
        "elapsed_nanoseconds",
    }),
    "verified_block_reuse_measurement": frozenset({
        "repetition",
        "strategy_id",
        "request_count",
        "unique_candidate_count",
        "independent_verifier_calls",
        "reused_request_count",
        "accepted_request_count",
        "best_verified_quality",
        "quality_map_sha256",
        "elapsed_nanoseconds",
    }),
}


class HistoricalEvidenceError(ValueError):
    """Retained paired research evidence has an incompatible identity."""


def _fail(message: str) -> Never:
    raise HistoricalEvidenceError(message)


def _native_error_detail(error: Exception, *trusted: type[Exception]) -> str:
    """Render only exact native errors carrying literal safe arguments."""
    if type(error) in trusted:
        arguments = error.args
        if len(arguments) == 1 and type(arguments[0]) is str:
            if type(error) is KeyError:
                return repr(arguments[0])
            return arguments[0]
        if (
            type(error) in (OSError, FileNotFoundError, PermissionError)
            and len(arguments) == 2
            and type(arguments[0]) is int
            and type(arguments[1]) is str
        ):
            return f"{type(error).__name__}: [Errno {arguments[0]}] {arguments[1]}"
    return type(error).__name__


def _source(root: Path, relative: str) -> tuple[str, str]:
    raw = evidence.read_bounded_regular(
        root,
        relative,
        limit=MAX_SOURCE_BYTES,
    )
    # The bounded reader is a dependency, not proof about its own result.
    # Validate its exact receipt before decoding or hashing source evidence.
    if type(raw) is not bytes or not 0 < len(raw) <= MAX_SOURCE_BYTES:
        _fail("historical source requires exact nonempty bounded bytes")
    return raw.decode("utf-8"), sha256(raw).hexdigest()


def _recheck_source_fingerprints(
    root: Path, relative: str, fingerprints: dict[str, str]
) -> None:
    for name, original in fingerprints.items():
        _, current = _source(root, f"{relative}/{name}")
        if current != original:
            _fail(f"historical source changed before report: {name}")


def _integer(text: object, field: str) -> int:
    if not isinstance(text, str) or not text:
        _fail(f"invalid historical numeric field: {field}")
    if not set(text) <= ASCII_DIGITS:
        _fail(f"invalid historical numeric field: {field}")
    value = int(text)
    if str(value) != text:
        _fail(f"noncanonical historical numeric field: {field}")
    return value


def _csv_shape(
    fields: Sequence[str],
    records: list[dict[str, str]],
    *,
    registered_fields: frozenset[str],
) -> None:
    if set(fields) != registered_fields:
        _fail("historical raw CSV columns differ from registered format")
    if len(set(fields)) != len(fields):
        _fail("historical raw CSV header has duplicate columns")
    if not records or any(
        any(key is None for key in row)
        or any(value is None for value in row.values())
        for row in records
    ):
        _fail("historical raw CSV contains incomplete rows")


def _require_bounded_csv_header(text: str) -> None:
    # Preflight the first physical line before DictReader builds fieldnames.
    # An open quoted field may otherwise consume many newline-delimited rows.
    prefix = text[: MAX_CSV_HEADER_CHARS + 1]
    first_line = prefix.split("\n", maxsplit=1)[0].split("\r", maxsplit=1)[0]
    if len(first_line) > MAX_CSV_HEADER_CHARS or first_line.count('"') % 2:
        _fail("historical raw CSV header is invalid or exceeds its bound")


def _bounded_csv_rows(
    reader: Iterator[dict[str, str]], expected_rows: int
) -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    for row in reader:
        if len(records) >= expected_rows:
            _fail("historical raw CSV has more rows than registered trials")
        if type(row) is not dict or any(
            type(name) is not str or (type(value) is not str and value is not None)
            for name, value in row.items()
        ):
            _fail("historical raw CSV parser returned non-native CSV row")
        records.append(row)
    return records


def _csv_rows(
    text: str,
    *,
    registered_fields: frozenset[str],
    expected_rows: int,
) -> list[dict[str, str]]:
    if analyze.NUL in text:
        _fail("historical raw CSV cannot contain NUL")
    _require_bounded_csv_header(text)
    if not csv_admission.within_column_limit(text, len(registered_fields)):
        _fail("historical raw CSV columns exceed registered count")
    try:
        reader = csv.DictReader(StringIO(text, newline=""), strict=True)
        fields = reader.fieldnames
        if fields is None:
            fields = []
        if type(fields) is not list or any(type(field) is not str for field in fields):
            _fail("historical raw CSV parser returned non-native CSV header")
        records = _bounded_csv_rows(reader, expected_rows)
    except HistoricalEvidenceError:
        raise
    except csv.Error as error:
        detail = _native_error_detail(error, csv.Error)
        message = f"malformed historical raw CSV: {detail}"
        raise HistoricalEvidenceError(message) from error
    except Exception as error:
        # Any ordinary CSV dependency failure must remain a typed rejection.
        # The exception class is safe to report; its formatter is not.
        message = f"malformed historical raw CSV parser: {type(error).__name__}"
        raise HistoricalEvidenceError(message) from error
    _csv_shape(fields, records, registered_fields=registered_fields)
    return records


def _extension(
    manifest: dict[str, Any],
) -> tuple[dict[str, Any], tuple[str, ...]]:
    if type(manifest) is not dict or any(
        type(key) is not str for key in manifest
    ):
        _fail("historical measurement manifest requires native string keys")
    available = [name for name in EXTENSION_CONFIG if name in manifest]
    if len(available) != 1:
        _fail("unsupported historical paired measurement extension")
    section = manifest[available[0]]
    if type(section) is not dict or any(
        type(key) is not str for key in section
    ):
        _fail("historical measurement extension requires native string keys")
    return section, EXTENSION_CONFIG[available[0]]


def _require(condition: object, message: str) -> None:
    if not condition:
        _fail(message)


def _source_identity(
    manifest: experiment_manifest.ExperimentManifest,
    protocol: benchmark_protocol.BenchmarkProtocolRecord,
    relative: str,
    *,
    source_commit: str,
) -> None:
    run = manifest.run
    _require(run is not None, "historical paired comparison requires a run")
    if run is None:
        return
    _require(
        manifest.record_kind == experiment_manifest.RUN_RECORD_KIND,
        "historical evidence must be a run record",
    )
    _require(
        run.outcome == RUN_SUCCEEDED,
        "historical paired run must report success",
    )
    _require(
        source_commit == run.commit + "\n",
        "historical retained source-commit pin differs from manifest run",
    )
    _require(
        run.accelerator == protocol.accelerator,
        "historical accelerator identity differs",
    )
    _require(run.host == protocol.host, "historical host identity differs")
    _require(
        run.raw_output == f"{relative}/raw.csv",
        "historical experiment raw path differs",
    )
    _require(
        protocol.raw_path == run.raw_output,
        "historical benchmark raw path differs",
    )
    _require(
        protocol.experiment_manifest == f"{relative}/experiment.toml",
        "historical protocol experiment path differs",
    )
    _require(
        protocol.workload_identity == manifest.challenge_family,
        "historical workload family differs",
    )
    _require(
        manifest.challenge_family.endswith("-v1"),
        "historical adapter only supports version-one challenge families",
    )
    _require(
        protocol.kind == DETERMINISTIC_KIND,
        "historical paired study must be deterministic",
    )
    _require(
        manifest.target_profile == CLASSIC_PROFILE,
        "historical paired study requires frozen classic profile",
    )
    _require(
        ELAPSED_SOURCE_FIELD in protocol.metrics,
        "historical protocol did not preregister elapsed time",
    )


def _reported_row(
    source: dict[str, str],
    manifest: experiment_manifest.ExperimentManifest,
    *,
    relative: str,
) -> dict[str, Any]:
    run = manifest.run
    if run is None:
        _fail("historical experiment run identity missing")
    return {
        "algorithm": source["strategy_id"],
        "case": {
            "family": manifest.challenge_family,
            "version": 1,
            "difficulty": manifest.difficulty,
            "seed": manifest.seed,
            "workload_sha256": run.workload_sha256,
        },
        "trial": _integer(source["repetition"], "repetition"),
        "outcome": analyze.VERIFIED,
        "verifier": manifest.oracle,
        "verifier_verdict": analyze.ACCEPTED,
        "experiment_manifest": f"{relative}/experiment.toml",
        "raw_sample": f"{relative}/raw.csv",
        "metrics": {
            "elapsed_ns": _integer(
                source["elapsed_nanoseconds"],
                "elapsed_nanoseconds",
            )
        },
    }


def _paired_rows(
    records: list[dict[str, str]],
    baseline: str,
    candidate: str,
    *,
    repetitions: int,
) -> None:
    if len(records) != repetitions * 2 or baseline == candidate:
        _fail("historical paired study has wrong trial population")
    observed: set[tuple[str, int]] = set()
    for row in records:
        strategy = row["strategy_id"]
        repetition = _integer(row["repetition"], "repetition")
        if strategy not in {baseline, candidate} or repetition >= repetitions:
            _fail("historical strategy/repetition is outside the protocol")
        pair_key = (strategy, repetition)
        if pair_key in observed:
            _fail("historical trial is duplicated")
        observed.add(pair_key)


def _registered_count(section: dict[str, Any], name: str) -> int:
    value = section[name]
    if type(value) is not int or value < 0:
        _fail(f"historical registered counter must be nonnegative: {name}")
    return value


def _quality_digest(extension: dict[str, Any]) -> None:
    value = extension["quality_map_sha256"]
    if type(value) is not str or len(value) != analyze.SHA256_HEX_LENGTH:
        _fail("historical quality-map fingerprint is not SHA-256")
    if not set(value) <= HEX_DIGITS:
        _fail("historical quality-map fingerprint is not lowercase SHA-256")


def _quality_row(
    row: dict[str, str],
    extension: dict[str, Any],
    accepted_key: str,
    *,
    size_key: str,
) -> None:
    if row["quality_map_sha256"] != extension["quality_map_sha256"]:
        _fail("historical strategies disagree with registered quality map")
    for key in ("best_verified_quality", accepted_key, size_key):
        if _integer(row[key], key) != _registered_count(extension, key):
            _fail(f"historical registered structural identity drift: {key}")
    _ = _integer(row["independent_verifier_calls"], "verifier calls")
    _ = _integer(row["elapsed_nanoseconds"], "elapsed_nanoseconds")


def _check_structural_fields(
    row: dict[str, str],
    extension: dict[str, Any],
    baseline: str,
) -> None:
    is_baseline = row["strategy_id"] == baseline
    if DISCHARGED in extension:
        expected = (
            0
            if is_baseline
            else _registered_count(
                extension,
                "structurally_discharged_candidates",
            )
        )
        _require(
            _integer(row["structurally_discharged_candidates"], "discharged")
            == expected,
            "historical discharged-candidate accounting disagrees",
        )
        _require(
            _integer(row["full_candidate_verifications"], "full verifier")
            == _integer(row["independent_verifier_calls"], "verifier calls"),
            "historical full verifier accounting disagrees",
        )
    else:
        expected = (
            0
            if is_baseline
            else _registered_count(
                extension,
                "reused_request_count",
            )
        )
        _require(
            _integer(row["reused_request_count"], "reused requests")
            == expected,
            "historical reused-request accounting disagrees",
        )
        _require(
            _integer(row["unique_candidate_count"], "unique candidates")
            == _registered_count(extension, "unique_candidate_count"),
            "historical unique-candidate accounting disagrees",
        )


def _structural_counts(
    records: list[dict[str, str]],
    baseline: str,
    candidate: str,
) -> dict[str, list[int]]:
    return {
        strategy: sorted({
            _integer(row["independent_verifier_calls"], "verifier calls")
            for row in records
            if row["strategy_id"] == strategy
        })
        for strategy in (baseline, candidate)
    }


@dataclass(slots=True)
class _StudySources:
    manifest_data: dict[str, Any]
    benchmark_data: dict[str, Any]
    manifest: experiment_manifest.ExperimentManifest
    protocol: benchmark_protocol.BenchmarkProtocolRecord
    records: list[dict[str, str]]
    fingerprints: dict[str, str]
    source_commit: str


def _admit_benchmark_data(text: str) -> dict[str, Any]:
    """Admit only native benchmark maps after independent protocol parsing."""
    document = tomllib.loads(text)
    if type(document) is not dict or any(
        type(key) is not str for key in document
    ):
        _fail("historical benchmark TOML requires native string keys")
    for name in ("study", "resources"):
        table = document.get(name)
        if type(table) is not dict or any(type(key) is not str for key in table):
            _fail("historical benchmark TOML requires native string keys")
    return document


def _load_source(root: Path, relative: str) -> _StudySources:
    names = (
        "experiment.toml",
        "benchmark.toml",
        "raw.csv",
        "source-commit.txt",
    )
    sources = {name: _source(root, f"{relative}/{name}") for name in names}
    manifest_text = sources["experiment.toml"][0]
    benchmark_text = sources["benchmark.toml"][0]
    manifest_data = tomllib.loads(manifest_text)
    _ = _extension(manifest_data)
    extension_name = next(
        name for name in EXTENSION_CONFIG if name in manifest_data
    )
    protocol = benchmark_protocol.parse_protocol(benchmark_text)
    if protocol.repetitions > MAX_HISTORICAL_REPETITIONS:
        _fail("historical registered repetitions exceed bounded study limit")
    return _StudySources(
        manifest_data=manifest_data,
        benchmark_data=_admit_benchmark_data(benchmark_text),
        manifest=experiment_manifest.parse_manifest(manifest_text),
        protocol=protocol,
        records=_csv_rows(
            sources["raw.csv"][0],
            registered_fields=REGISTERED_RAW_COLUMNS[extension_name],
            expected_rows=2 * protocol.repetitions,
        ),
        fingerprints={name: sources[name][1] for name in names},
        source_commit=sources["source-commit.txt"][0],
    )


def _declared_strategies(sources: _StudySources) -> tuple[str, str]:
    (
        extension,
        (
            candidate_key,
            accepted_key,
            size_key,
            candidate_calls_key,
        ),
    ) = _extension(sources.manifest_data)
    baseline = sources.benchmark_data["study"]["baseline"]
    candidate = extension[candidate_key]
    _quality_digest(extension)
    _require(
        baseline == extension["baseline_strategy"],
        "historical baseline disagrees with measurement",
    )
    _require(
        baseline == sources.manifest_data["verification"]["baseline"],
        "historical verification baseline differs",
    )
    _require(
        sources.protocol.repetitions
        == _registered_count(
            extension,
            "repetitions",
        ),
        "historical repetitions differ from preregistration",
    )
    run = sources.manifest.run
    _require(run is not None, "missing historical run")
    if run is not None:
        _require(
            extension["workload_sha256"] == run.workload_sha256,
            "historical measurement workload digest differs from run",
        )
    _paired_rows(
        sources.records,
        baseline,
        candidate,
        repetitions=sources.protocol.repetitions,
    )
    for row in sources.records:
        _quality_row(row, extension, accepted_key, size_key=size_key)
        _check_structural_fields(row, extension, baseline)
        claimed_calls = (
            _registered_count(extension, "baseline_verifier_calls")
            if row["strategy_id"] == baseline
            else _registered_count(extension, candidate_calls_key)
        )
        _require(
            _integer(row["independent_verifier_calls"], "verifier calls")
            == claimed_calls,
            "historical verifier-call counts differ from registered strategy",
        )
    return baseline, candidate


def _admitted_document(
    sources: _StudySources,
    relative: str,
) -> dict[str, Any]:
    run = sources.manifest.run
    if run is None:
        _fail("missing historical run")
    budget = sources.manifest_data["budget"]["memory_mib"]
    seconds = sources.manifest_data["budget"]["seconds"]
    _require(
        budget == sources.benchmark_data["resources"]["memory_mib"],
        "historical memory budget differs from protocol",
    )
    _require(
        type(seconds) is int and seconds > 0,
        "historical run requires positive budget seconds",
    )
    study = sources.benchmark_data["study"]
    return {
        "schema_version": 1,
        "study": {
            "id": study["id"],
            "question": study["question"],
            "hypothesis": study["hypothesis"],
            "baseline": study["baseline"],
            "rejection_observation": study["rejection_observation"],
            "stage": "classic-verified-block-research-paired-strategies",
            "target_profile": sources.manifest.target_profile,
            "host": run.host,
            "toolchain": run.toolchain,
            "budget": {
                "time_ns": seconds * SECONDS_TO_NS,
                "memory_bytes": budget * MIB_TO_BYTES,
            },
            "objectives": ["elapsed_ns"],
        },
        "observations": [
            _reported_row(row, sources.manifest, relative=relative)
            for row in sources.records
        ],
    }


def _build_report(root: Path, relative: str) -> dict[str, Any]:
    sources = _load_source(root, relative)
    _source_identity(
        sources.manifest,
        sources.protocol,
        relative,
        source_commit=sources.source_commit,
    )
    baseline, candidate = _declared_strategies(sources)
    document = _admitted_document(sources, relative)
    report = analyze.analyze(analyze.parse_document(json.dumps(document)))
    report["historical_evidence"] = {
        "source": relative,
        "evidence_status": "source-reported-not-reverified",
        "source_sha256": sources.fingerprints,
        "reported_verifier_calls": _structural_counts(
            sources.records,
            baseline,
            candidate,
        ),
        "scope": (
            "Retained source-reported host measurements and quality-map "
            "parity; no new execution or independent verifier replay."
        ),
    }
    _recheck_source_fingerprints(root, relative, sources.fingerprints)
    return report


def build_report(root: Path, relative: str) -> dict[str, Any]:
    """Regenerate source-backed comparisons without new measurements.

    Returns:
        Arena report with source fingerprints and reported verifier caveats.

    Raises:
        HistoricalEvidenceError: An imported source disagrees with its plan.

    """
    if type(root) is not type(Path()):
        _fail("historical paired root requires an exact native Path")
    if type(relative) is not str:
        _fail("historical paired source requires an exact string")
    if not relative.startswith("benchmarks/research/evidence/"):
        _fail("historical paired source must be under research evidence")
    try:
        return _build_report(root, relative)
    except OSError:
        # Preserve distinct filesystem failures for operator I/O diagnostics.
        raise
    except Exception as error:
        # Foreign exception subtypes may run arbitrary code in __str__.
        # Preserve useful diagnostics for exact native parser errors only.
        native_parser_errors = (
            KeyError,
            TypeError,
            ValueError,
            RecursionError,
            csv.Error,
            tomllib.TOMLDecodeError,
            HistoricalEvidenceError,
            evidence.EvidenceError,
            analyze.ArenaError,
            experiment_manifest.ExperimentManifestError,
            benchmark_protocol.BenchmarkProtocolError,
        )
        diagnostic = _native_error_detail(error, *native_parser_errors)
        message = f"historical paired source inconsistent: {diagnostic}"
        raise HistoricalEvidenceError(message) from error


def main() -> int:
    """Read a retained paired research study and print an arena report.

    Returns:
        Zero for a matched source, two for a rejected source.

    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source")
    parser.add_argument("--root", type=Path, default=Path(__file__).parents[2])
    args = parser.parse_args()
    try:
        report = build_report(args.root, args.source)
        report_output.publish(report, sys.stdout)
    except (
        HistoricalEvidenceError,
        experiment_manifest.ExperimentManifestError,
        benchmark_protocol.BenchmarkProtocolError,
        report_output.ReportOutputError,
        OSError,
        UnicodeError,
    ) as error:
        detail = _native_error_detail(
            error,
            HistoricalEvidenceError,
            experiment_manifest.ExperimentManifestError,
            benchmark_protocol.BenchmarkProtocolError,
            report_output.ReportOutputError,
            OSError,
            FileNotFoundError,
            PermissionError,
            IsADirectoryError,
            NotADirectoryError,
            UnicodeError,
            UnicodeDecodeError,
            UnicodeEncodeError,
        )
        parser.exit(2, f"arena historical evidence: {detail}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
