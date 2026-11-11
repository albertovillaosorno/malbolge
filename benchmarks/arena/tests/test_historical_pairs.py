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
#   - Source-backed classic paired experiment adapter regression evidence.
# - Must-Not:
#   - Represent retained host timing as newly measured or semantic proof.
# - Allows:
#   - Inputs: existing research source files and test-local tampered copies.
#   - Outputs: assertions over retained timing, identity and fail-closed input.
#   - Side effects: test-local copies of source evidence only.
# - Split-When:
#   - Other historical measurement formats become independently admissible.
# - Merge-When:
#   - Research source import testing gains a shared governed adapter suite.
# - Summary:
#   - Locks existing five-paired timing evidence and rejects source drift.
# - Description:
#   - Replays existing research files without running any semantic verifier.
# - Usage:
#   - `python -B -m pytest benchmarks/arena/tests/test_historical_pairs.py`.
# - Defaults:
#   - Only the two supported classic measurement schemas can be imported.
#

"""Checks historical source-reported timing pairs without new measurements."""

# Test assertions intentionally use pytest policy.
# ruff: file-ignore[assert,private-member-access]

from __future__ import annotations

import csv
import json
import sys
from dataclasses import replace
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any, Self, cast

if TYPE_CHECKING:
    from collections.abc import Iterator
    from io import StringIO

import pytest

from benchmarks.arena import historical_pairs
from scripts.validate import benchmark_protocol

REPO = Path(__file__).resolve().parents[3]
PREFIX = "2026-09-04-classic-prefix-decomposition-linux"
REUSE = "2026-09-04-classic-verified-block-reuse-linux"
BASE = "benchmarks/research/evidence/"
TEMP = BASE + "tampered-classic-pairs"
PAIR_COUNT = 5
PREFIX_BASELINE = "full-candidate-independent-verification-v1"
PREFIX_CANDIDATE = "exact-first-step-prefix-decomposition-v1"
REUSE_BASELINE = "per-request-independent-verification-v1"
REUSE_CANDIDATE = "exact-candidate-verified-result-reuse-v1"
NO_NEW_EXECUTION = "no new execution"
SOURCE_REPORTED = "source-reported-not-reverified"
HISTORICAL_SOURCE_INCONSISTENT = "historical paired source inconsistent"


@pytest.mark.parametrize(
    "providers", ("cached-encoder", "writer", "cached-encoder-and-writer")
)
def test_historical_report_rejects_substituted_json_timing(
    monkeypatch: pytest.MonkeyPatch,
    providers: str,
) -> None:
    """Admitted original historical timing cannot be replaced in JSON."""
    baseline = _result(REUSE)
    assert baseline["study_id"] == "classic-verified-block-reuse-linux-2026-09-04"
    native_encoder = json.JSONEncoder()
    native_dumps = json.dumps

    def changed(value: object) -> object:
        if type(value) is dict and "study" in value and "observations" in value:
            rows = list(value["observations"])
            first = dict(rows[0])
            metrics = dict(first["metrics"])
            metrics["elapsed_ns"] += 100_000_000
            first["metrics"] = metrics
            rows[0] = first
            return {**value, "observations": rows}
        return value

    def altered(value: object, **kwargs: Any) -> str:
        return native_dumps(changed(value), **kwargs)

    class ForgedCachedEncoder:
        def encode(self, value: object) -> str:
            return native_encoder.encode(changed(value))

    with monkeypatch.context() as patch:
        if providers != "writer":
            patch.setattr(json, "_default_encoder", ForgedCachedEncoder())
        if providers != "cached-encoder":
            patch.setattr(json, "dumps", altered)
        with pytest.raises(
            historical_pairs.HistoricalEvidenceError,
            match="JSON serializer disagrees with source",
        ):
            _ = _result(REUSE)


class _ForeignReportJson(str):
    """A substituted receipt cannot define arbitrary equality behavior."""

    def __eq__(self, other: object) -> bool:
        del other
        raise AssertionError("foreign historical JSON equality invoked")

    __hash__ = str.__hash__


@pytest.mark.parametrize("receipt", (None, b"{}", _ForeignReportJson("{}")))
def test_historical_report_rejects_foreign_json_writer_receipt(
    monkeypatch: pytest.MonkeyPatch,
    receipt: object,
) -> None:
    """Only native source-identical text can reach historical analysis."""
    relative = BASE + REUSE
    sources = historical_pairs._load_source(REPO, relative)
    document = historical_pairs._admitted_document(sources, relative)
    with monkeypatch.context() as patch:
        patch.setattr(json, "dumps", lambda *_args, **_kwargs: receipt)
        with pytest.raises(
            historical_pairs.HistoricalEvidenceError,
            match="JSON serializer disagrees with source",
        ):
            _ = historical_pairs._admitted_report_json(document)


def test_historical_report_contains_json_writer_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Foreign serializer errors remain typed with the exact native cause."""
    failure = RuntimeError("untrusted external details")

    def broken(*_args: object, **_kwargs: object) -> str:
        raise failure

    relative = BASE + REUSE
    sources = historical_pairs._load_source(REPO, relative)
    document = historical_pairs._admitted_document(sources, relative)
    with monkeypatch.context() as patch:
        patch.setattr(json, "dumps", broken)
        with pytest.raises(
            historical_pairs.HistoricalEvidenceError,
            match="JSON serializer failed: RuntimeError",
        ) as caught:
            _ = historical_pairs._admitted_report_json(document)
        assert caught.value.__cause__ is failure


@pytest.mark.parametrize("method", ["encode", "iterencode"])
def test_historical_report_rejects_joint_encoder_method_swap(
    monkeypatch: pytest.MonkeyPatch, method: str,
) -> None:
    """Shared late-bound JSONEncoder methods cannot forge report contents."""
    document = {"schema_version": 1, "observations": [{"elapsed_ns": 7}]}
    forged = '{"schema_version": 1, "observations": [{"elapsed_ns": 900}]}'
    assert json.dumps(document) != forged

    def forged_encode(instance: object, value: object) -> str:
        del instance, value
        return forged

    def forged_iterencode(
        instance: object, value: object, **kwargs: object
    ) -> Iterator[str]:
        del instance, value, kwargs
        return iter([forged])

    replacement = {"encode": forged_encode, "iterencode": forged_iterencode}
    with monkeypatch.context() as patch:
        patch.setattr(json.JSONEncoder, method, replacement[method])
        with pytest.raises(
            historical_pairs.HistoricalEvidenceError,
            match="JSON serializer disagrees with source",
        ):
            _ = historical_pairs._admitted_report_json(document)


@pytest.mark.parametrize(
    "provider",
    ["encode_basestring_ascii", "c_make_encoder", "_make_iterencode"],
)
def test_historical_report_rejects_shared_json_factory_swap(
    monkeypatch: pytest.MonkeyPatch, provider: str,
) -> None:
    """Mutable module-global encoder helpers cannot certify source JSON."""
    document = {"observations": [{"elapsed_ns": 7}]}
    original = getattr(json.encoder, provider, None)
    if not callable(original):
        pytest.skip("native JSON encoder provider unavailable")

    def substituted_provider(*args: object, **kwargs: object) -> object:
        return original(*args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(json.encoder, provider, substituted_provider)
        with pytest.raises(
            historical_pairs.HistoricalEvidenceError,
            match="JSON serializer disagrees with source",
        ):
            _ = historical_pairs._admitted_report_json(document)


def test_historical_report_rejects_midcall_json_provider_swap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A writer cannot replace source JSON machinery after the first encode."""
    document = {"observations": [{"elapsed_ns": 7}]}
    native_dumps = json.dumps
    native_factory = getattr(
        json.encoder, historical_pairs._SOURCE_PY_FACTORY_NAME
    )
    with monkeypatch.context() as patch:

        def altered_dumps(value: object) -> str:
            result = native_dumps(value)

            def replaced_factory(*args: object, **kwargs: object) -> object:
                return native_factory(*args, **kwargs)

            patch.setattr(
                json.encoder,
                historical_pairs._SOURCE_PY_FACTORY_NAME,
                replaced_factory,
            )
            return result

        patch.setattr(json, "dumps", altered_dumps)
        with pytest.raises(
            historical_pairs.HistoricalEvidenceError,
            match="JSON serializer disagrees with source",
        ):
            _ = historical_pairs._admitted_report_json(document)


def test_historical_report_accepts_equivalent_cached_json_encoder(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Equivalent cached encoders retain original source-backed values."""
    baseline = _result(REUSE)
    with monkeypatch.context() as patch:
        patch.setattr(json, "_default_encoder", json.JSONEncoder())
        assert _result(REUSE) == baseline


def _result(name: str) -> dict:
    return historical_pairs.build_report(REPO, BASE + name)


@pytest.mark.parametrize(
    "invalid",
    [None, b"", bytearray(b"evidence"), memoryview(b"evidence"), "evidence", 7],
    ids=["missing", "empty", "mutable", "view", "text", "integer"],
)
def test_historical_source_rejects_non_native_reader_receipts(
    monkeypatch: pytest.MonkeyPatch,
    invalid: object,
) -> None:
    """Substituted bounded readers cannot certify foreign evidence objects."""
    monkeypatch.setattr(
        historical_pairs.evidence,
        "read_bounded_regular",
        lambda *_args, **_kwargs: cast("bytes", invalid),
    )
    with pytest.raises(
        historical_pairs.HistoricalEvidenceError, match="exact nonempty bounded bytes"
    ):
        historical_pairs._source(REPO, BASE + PREFIX + "/raw.csv")


def test_historical_source_rejects_bytes_subclass_before_decode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A bytes subclass must not manufacture decoded historical evidence."""

    class ForeignBytes(bytes):
        def decode(self, encoding: str = "utf-8", errors: str = "strict") -> str:
            del encoding, errors
            pytest.fail("foreign historical source decode executed")

    monkeypatch.setattr(
        historical_pairs.evidence,
        "read_bounded_regular",
        lambda *_args, **_kwargs: ForeignBytes(b"false evidence"),
    )
    with pytest.raises(
        historical_pairs.HistoricalEvidenceError, match="exact nonempty bounded bytes"
    ):
        historical_pairs._source(REPO, BASE + PREFIX + "/raw.csv")


def test_historical_source_rejects_oversized_reader_receipt_before_hash(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An injected reader cannot skip the source's four-MiB budget."""
    receipt = b"x" * (historical_pairs.MAX_SOURCE_BYTES + 1)
    monkeypatch.setattr(
        historical_pairs.evidence,
        "read_bounded_regular",
        lambda *_args, **_kwargs: receipt,
    )

    def forbidden_hash(_value: bytes) -> None:
        pytest.fail("oversized historical source reached hash")

    monkeypatch.setattr(historical_pairs, "sha256", forbidden_hash)
    with pytest.raises(
        historical_pairs.HistoricalEvidenceError, match="exact nonempty bounded bytes"
    ):
        historical_pairs._source(REPO, BASE + PREFIX + "/raw.csv")


@pytest.mark.parametrize(
    "receipt", [1, "true", object(), [1]],
    ids=["integer", "text", "object", "list"],
)
def test_historical_assertion_rejects_non_boolean_truthy_receipts(
    receipt: object,
) -> None:
    """A malformed dependency comparison must not claim an admitted match."""
    with pytest.raises(historical_pairs.HistoricalEvidenceError, match="native check"):
        historical_pairs._require(receipt, "native check")


def test_historical_assertion_does_not_invoke_foreign_truthiness() -> None:
    """Reject a forged boolean receipt before its caller-owned hook can run."""

    class HostileTruth:
        def __bool__(self) -> bool:
            pytest.fail("foreign historical comparison truthiness executed")

    with pytest.raises(historical_pairs.HistoricalEvidenceError, match="native check"):
        historical_pairs._require(HostileTruth(), "native check")


def test_historical_assertion_preserves_native_truth_values() -> None:
    """Canonical true accepts and canonical false rejects source evidence."""
    historical_pairs._require(True, "native check")
    with pytest.raises(historical_pairs.HistoricalEvidenceError, match="native check"):
        historical_pairs._require(False, "native check")


def test_historical_quality_digest_rejects_foreign_string_before_hooks() -> None:
    """Source-reported digest validation cannot invoke subclass iterators."""

    class ForgedDigest(str):
        def __len__(self) -> int:
            pytest.fail("historical digest subclass length hook executed")

        def __iter__(self) -> Iterator[str]:
            pytest.fail("historical digest subclass iteration executed")

    with pytest.raises(
        historical_pairs.HistoricalEvidenceError, match="not SHA-256"
    ):
        historical_pairs._quality_digest({"quality_map_sha256": ForgedDigest("0" * 64)})


def test_historical_quality_digest_accepts_native_lowercase_sha256() -> None:
    """Native lowercase identity remains accepted without a parser shortcut."""
    historical_pairs._quality_digest({"quality_map_sha256": "c" * 64})


def test_historical_source_preserves_native_bounded_bytes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ordinary evidence preserves the exact decoded text and fingerprint."""
    receipt = b"source-reported\n"
    monkeypatch.setattr(
        historical_pairs.evidence,
        "read_bounded_regular",
        lambda *_args, **_kwargs: receipt,
    )
    assert historical_pairs._source(REPO, BASE + PREFIX + "/raw.csv") == (
        receipt.decode("utf-8"),
        sha256(receipt).hexdigest(),
    )



class _ForgedHistoricalDigest(str):
    """An injected hash receipt must not get to inspect its own text."""

    def __len__(self) -> int:
        raise AssertionError("foreign historical hash length hook executed")

    def __iter__(self) -> Iterator[str]:
        raise AssertionError("foreign historical hash iterator executed")


@pytest.mark.parametrize(
    "receipt",
    [None, 1, False, "a" * 63, "G" * 64, "F" * 64, _ForgedHistoricalDigest("a" * 64)],
)
def test_historical_source_rejects_untrusted_hash_receipts(
    monkeypatch: pytest.MonkeyPatch, receipt: object
) -> None:
    """Reported source fingerprints must be exact native lowercase SHA-256."""
    monkeypatch.setattr(
        historical_pairs.evidence, "read_bounded_regular", lambda *_args, **_kw: b"source"
    )

    class HashReceipt:
        def hexdigest(self) -> object:
            return receipt

    monkeypatch.setattr(historical_pairs, "sha256", lambda *_: HashReceipt())
    with pytest.raises(historical_pairs.HistoricalEvidenceError, match="SHA-256"):
        historical_pairs._source(REPO, BASE + PREFIX + "/raw.csv")


def test_historical_source_rejects_plausible_but_wrong_hash_receipt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A canonical-looking digest cannot describe unrelated source bytes."""
    monkeypatch.setattr(
        historical_pairs.evidence, "read_bounded_regular", lambda *_args, **_kw: b"source"
    )

    class WrongHash:
        def hexdigest(self) -> str:
            return "a" * 64

    monkeypatch.setattr(historical_pairs, "sha256", lambda *_: WrongHash())
    with pytest.raises(historical_pairs.HistoricalEvidenceError, match="SHA-256"):
        historical_pairs._source(REPO, BASE + PREFIX + "/raw.csv")


def test_historical_source_rejects_jointly_forged_hash_constructors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Two agreeing forged digest providers cannot identify historical bytes."""
    original = b"historical source evidence\n"
    false_digest = "0" * 64
    assert sha256(original).hexdigest() != false_digest
    monkeypatch.setattr(
        historical_pairs.evidence,
        "read_bounded_regular",
        lambda *_args, **_kwargs: original,
    )

    class ForgedHash:
        def hexdigest(self) -> str:
            return false_digest

    monkeypatch.setattr(historical_pairs, "sha256", lambda _raw: ForgedHash())
    monkeypatch.setattr(
        historical_pairs,
        "hashlib",
        SimpleNamespace(new=lambda _name, _raw: ForgedHash()),
    )
    with pytest.raises(historical_pairs.HistoricalEvidenceError, match="SHA-256"):
        historical_pairs._source(REPO, BASE + PREFIX + "/raw.csv")


@pytest.mark.parametrize("stage", ["construct", "digest"])
def test_historical_source_types_untrusted_hash_dependency_fault(
    monkeypatch: pytest.MonkeyPatch, stage: str
) -> None:
    """An unexpected ordinary hash failure stays typed without its formatter."""
    monkeypatch.setattr(
        historical_pairs.evidence, "read_bounded_regular", lambda *_args, **_kw: b"source"
    )

    class ForeignHashFault(RuntimeError):
        def __str__(self) -> str:
            raise AssertionError("foreign historical hash exception formatter executed")

    fault = ForeignHashFault("host failed")

    class HashReceipt:
        def hexdigest(self) -> str:
            raise fault

    def hashed(*_args: object) -> HashReceipt:
        if stage == "construct":
            raise fault
        return HashReceipt()

    monkeypatch.setattr(historical_pairs, "sha256", hashed)
    with pytest.raises(historical_pairs.HistoricalEvidenceError, match="hash") as caught:
        historical_pairs._source(REPO, BASE + PREFIX + "/raw.csv")
    assert caught.value.__cause__ is fault


def _copy_source(tmp_path: Path, name: str) -> Path:
    directory = tmp_path / TEMP
    directory.mkdir(parents=True)
    for filename in (
        "experiment.toml",
        "benchmark.toml",
        "raw.csv",
        "source-commit.txt",
    ):
        original = REPO / BASE / name / filename
        destination = directory / filename
        contents = original.read_bytes().replace(
            (BASE + name).encode(),
            TEMP.encode(),
        )
        _ = destination.write_bytes(contents)
    return directory


def _alter(directory: Path, filename: str, *, before: str, after: str) -> None:
    path = directory / filename
    source = path.read_text(encoding="utf-8")
    assert before in source
    _ = path.write_text(source.replace(before, after, 1), encoding="utf-8")


def test_prefix_source_is_retained_null_timing_result() -> None:
    """Recorded prefix verification reduction does not imply lower runtime."""
    report = _result(PREFIX)
    source = report["historical_evidence"]
    assert source["reported_verifier_calls"] == {
        PREFIX_BASELINE: [8836],
        PREFIX_CANDIDATE: [8742],
    }
    pairs = report["paired_baseline_comparisons"]
    assert len(pairs) == 1
    assert pairs[0]["paired_trials"] == PAIR_COUNT
    assert pairs[0]["outcomes"]["both_verified"] == PAIR_COUNT
    assert pairs[0]["cost_differences"]["elapsed_ns"] == {
        "candidate_lower": 2,
        "candidate_equal": 0,
        "candidate_higher": 3,
        "median_candidate_minus_baseline": [25205409, 1],
    }
    assert report["pareto_frontiers"][0]["algorithms"] == [PREFIX_BASELINE]
    results = {point["algorithm"]: point for point in report["capacity_curve"]}
    assert results[PREFIX_BASELINE]["medians"]["elapsed_ns"] == [831921051, 1]
    assert results[PREFIX_CANDIDATE]["medians"]["elapsed_ns"] == [835180632, 1]
    assert NO_NEW_EXECUTION in source["scope"]
    assert source["evidence_status"] == SOURCE_REPORTED


def test_verified_result_reuse_source_preserves_paired_speedup() -> None:
    """Existing reported five-pair reuse win stays separated from proof."""
    report = _result(REUSE)
    source = report["historical_evidence"]
    assert source["reported_verifier_calls"] == {
        REUSE_BASELINE: [17672],
        REUSE_CANDIDATE: [8836],
    }
    pair = report["paired_baseline_comparisons"][0]
    assert pair["paired_trials"] == PAIR_COUNT
    assert pair["outcomes"]["both_verified"] == PAIR_COUNT
    assert pair["cost_differences"]["elapsed_ns"] == {
        "candidate_lower": PAIR_COUNT,
        "candidate_equal": 0,
        "candidate_higher": 0,
        "median_candidate_minus_baseline": [-792780699, 1],
    }
    assert report["pareto_frontiers"][0]["algorithms"] == [REUSE_CANDIDATE]
    medians = {
        p["algorithm"]: p["medians"]["elapsed_ns"]
        for p in report["capacity_curve"]
    }
    assert medians[REUSE_BASELINE] == [1617672749, 1]
    assert medians[REUSE_CANDIDATE] == [851323429, 1]


@pytest.mark.parametrize("name", [PREFIX, REUSE])
def test_exact_source_fingerprints_reproduce(name: str) -> None:
    """Inspect the same retained raw and manifest bytes as the report."""
    reported = _result(name)["historical_evidence"]["source_sha256"]
    assert reported == {
        filename: sha256(
            (REPO / BASE / name / filename).read_bytes()
        ).hexdigest()
        for filename in (
            "benchmark.toml",
            "experiment.toml",
            "raw.csv",
            "source-commit.txt",
        )
    }


@pytest.mark.parametrize(
    "case",
    [
        (PREFIX, "raw.csv", "831921051", "9999999999999999999", "budget"),
        (PREFIX, "raw.csv", "33d23f934b", "3333333333", "quality map"),
        (PREFIX, "raw.csv", "0,full-candidate", "0,unregistered", "strategy"),
        (
            PREFIX,
            "raw.csv",
            "1,full-candidate",
            "0,full-candidate",
            "duplicated",
        ),
        (
            PREFIX,
            "benchmark.toml",
            "equivalent = true",
            "equivalent = false",
            "equivalent_workload",
        ),
        (
            PREFIX,
            "benchmark.toml",
            "repetitions = 5",
            "repetitions = 6",
            "repetition",
        ),
        (
            PREFIX,
            "experiment.toml",
            'outcome = "success"',
            'outcome = "no-solution"',
            "success",
        ),
        (
            PREFIX,
            "raw.csv",
            "full_candidate_verifications,",
            "unregistered_verification_field,",
            "columns differ",
        ),
        (
            REUSE,
            "raw.csv",
            "unique_candidate_count,",
            "unknown_candidate_column,",
            "columns differ",
        ),
        (REUSE, "raw.csv", "9dfe349bf", "1111111111", "quality map"),
        (
            PREFIX,
            "source-commit.txt",
            "ed6825af65aa",
            "000000000000",
            "source-commit pin",
        ),
        (
            PREFIX,
            "raw.csv",
            "8836,8836,8836",
            "8836,8835,8836",
            "full verifier accounting",
        ),
        (
            PREFIX,
            "raw.csv",
            "8742,8742,94",
            "8742,8742,93",
            "discharged-candidate",
        ),
        (REUSE, "raw.csv", "8836,8836,20", "8836,8835,20", "reused-request"),
        (
            REUSE,
            "experiment.toml",
            "baseline_verifier_calls = 17672",
            "baseline_verifier_calls = 17673",
            "verifier-call counts",
        ),
        (
            PREFIX,
            "experiment.toml",
            "best_verified_quality = 1",
            "best_verified_quality = true",
            "registered counter",
        ),
        (
            PREFIX,
            "experiment.toml",
            "candidate_count = 8836",
            "candidate_count = 8835",
            "structural identity drift",
        ),
    ],
)
def test_source_drift_rejected(
    tmp_path: Path,
    case: tuple[str, str, str, str, str],
) -> None:
    """An altered raw row or preregistration never becomes trusted evidence."""
    source, filename, before, after, reason = case
    directory = _copy_source(tmp_path, source)
    _alter(directory, filename, before=before, after=after)
    with pytest.raises(historical_pairs.HistoricalEvidenceError, match=reason):
        historical_pairs.build_report(tmp_path, TEMP)


@pytest.mark.parametrize(
    "raw",
    [b"," * 10_000 + b"\n", b'"unterminated\n' + b"a,\n" * 10_000],
    ids=["column-flood", "multiline-header"],
)
def test_historical_csv_header_rejected_before_dict_reader(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    raw: bytes,
) -> None:
    """Registered CSV headers cannot expand into huge field lists."""
    directory = _copy_source(tmp_path, PREFIX)
    _ = (directory / "raw.csv").write_bytes(raw)

    def forbidden_reader(
        source: StringIO, *, strict: bool
    ) -> Iterator[dict[str, str]]:
        assert source is not None
        assert strict
        pytest.fail("historical parser admitted an oversized logical header")

    monkeypatch.setattr(historical_pairs.csv, "DictReader", forbidden_reader)
    with pytest.raises(historical_pairs.HistoricalEvidenceError, match="CSV header"):
        historical_pairs.build_report(tmp_path, TEMP)


def test_historical_csv_direct_text_rejects_subclass_before_hooks() -> None:
    """Direct callers cannot run foreign text methods ahead of preflight."""

    class HostileText(str):
        def __contains__(self, other: object) -> bool:
            del other
            raise AssertionError("foreign historical text contains hook executed")

        def __getitem__(self, other: object) -> str:
            del other
            raise AssertionError("foreign historical text slicing hook executed")

    with pytest.raises(
        historical_pairs.HistoricalEvidenceError, match="exact bounded text"
    ):
        historical_pairs._csv_rows(
            HostileText("repetition,strategy_id\n0,baseline\n"),
            registered_fields=historical_pairs.REGISTERED_RAW_COLUMNS[
                "prefix_decomposition_measurement"
            ],
            expected_rows=1,
        )


def test_historical_csv_direct_text_rejects_multibyte_overflow(
    monkeypatch: pytest.MonkeyPatch
) -> None:
    """A Unicode text can be shorter in characters than its UTF-8 byte size."""
    content = "é" * (historical_pairs.MAX_SOURCE_BYTES // 2 + 1)
    assert len(content) <= historical_pairs.MAX_SOURCE_BYTES
    assert len(content.encode("utf-8")) > historical_pairs.MAX_SOURCE_BYTES
    monkeypatch.setattr(
        historical_pairs.csv,
        "DictReader",
        lambda *_args, **_kwargs: pytest.fail("oversized source reached CSV reader"),
    )
    with pytest.raises(
        historical_pairs.HistoricalEvidenceError, match="exact bounded text"
    ):
        historical_pairs._csv_rows(
            content,
            registered_fields=historical_pairs.REGISTERED_RAW_COLUMNS[
                "prefix_decomposition_measurement"
            ],
            expected_rows=1,
        )


def test_historical_csv_direct_text_rejects_unpaired_surrogate() -> None:
    """Direct malformed Unicode stays a typed rejection before CSV parsing."""
    with pytest.raises(
        historical_pairs.HistoricalEvidenceError, match="strict UTF-8 text"
    ) as caught:
        historical_pairs._csv_rows(
            "bad\ud800text",
            registered_fields=historical_pairs.REGISTERED_RAW_COLUMNS[
                "prefix_decomposition_measurement"
            ],
            expected_rows=1,
        )
    assert type(caught.value.__cause__) is UnicodeEncodeError


class _HostileHistoricalCSVVerdict:
    """A forged guard result must not run its truthiness hook."""

    def __bool__(self) -> bool:
        raise AssertionError("foreign historical CSV preflight bool executed")


@pytest.mark.parametrize(
    "receipt", [1, 0, "admitted", [], object(), _HostileHistoricalCSVVerdict()]
)
def test_historical_csv_preflight_rejects_nonboolean_receipts_before_reader(
    monkeypatch: pytest.MonkeyPatch, receipt: object
) -> None:
    """Only a native boolean may authorize CSV column allocation."""
    columns = historical_pairs.REGISTERED_RAW_COLUMNS[
        "prefix_decomposition_measurement"
    ]
    called: list[str] = []

    def forged_guard(_text: str, _limit: int) -> object:
        return receipt

    def forbidden_reader(*_args: object, **_kwargs: object) -> None:
        called.append("parser")
        raise AssertionError("forged preflight reached historical CSV parser")

    monkeypatch.setattr(
        historical_pairs.csv_admission, "within_column_limit", forged_guard
    )
    monkeypatch.setattr(historical_pairs.csv, "DictReader", forbidden_reader)
    with pytest.raises(
        historical_pairs.HistoricalEvidenceError, match="preflight.*nonnative"
    ):
        historical_pairs._csv_rows(
            "repetition,strategy_id\n0,baseline\n",
            registered_fields=columns,
            expected_rows=1,
        )
    assert not called


@pytest.mark.parametrize("kind", [ValueError, TypeError, RuntimeError, IndexError])
def test_historical_csv_preflight_types_unexpected_host_fault(
    monkeypatch: pytest.MonkeyPatch, kind: type[Exception]
) -> None:
    """Preflight crashes are typed failures without formatting foreign hooks."""

    class HostileFault(kind):
        def __str__(self) -> str:
            raise AssertionError("foreign historical CSV fault was formatted")

    fault = HostileFault("broken dependency")

    def failed_guard(_text: str, _limit: int) -> bool:
        raise fault

    monkeypatch.setattr(
        historical_pairs.csv_admission, "within_column_limit", failed_guard
    )
    with pytest.raises(
        historical_pairs.HistoricalEvidenceError, match="column preflight failed"
    ) as caught:
        historical_pairs._csv_rows(
            "repetition,strategy_id\n0,baseline\n",
            registered_fields=historical_pairs.REGISTERED_RAW_COLUMNS[
                "prefix_decomposition_measurement"
            ],
            expected_rows=1,
        )
    assert caught.value.__cause__ is fault


def test_excessive_historical_data_columns_reject_before_parser(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A normal header cannot conceal an unbounded number of row columns."""
    directory = _copy_source(tmp_path, PREFIX)
    path = directory / "raw.csv"
    header = path.read_bytes().split(b"\n", maxsplit=1)[0]
    _ = path.write_bytes(header + b"\n" + b"," * 10_000 + b"\n")

    def forbidden_reader(
        source: StringIO, *, strict: bool
    ) -> Iterator[dict[str, str]]:
        assert source is not None
        assert strict
        pytest.fail("parsed an oversized historical data row")

    monkeypatch.setattr(historical_pairs.csv, "DictReader", forbidden_reader)
    with pytest.raises(historical_pairs.HistoricalEvidenceError, match="CSV columns"):
        historical_pairs.build_report(tmp_path, TEMP)


@pytest.mark.parametrize("source", [PREFIX, REUSE])
def test_historical_raw_rows_stop_at_first_unregistered_trial(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    source: str,
) -> None:
    """A 4 MiB CSV limit cannot hide unlimited row-object expansion."""
    directory = _copy_source(tmp_path, source)
    raw_file = directory / "raw.csv"
    _ = raw_file.write_bytes(raw_file.read_bytes() + b",\n" * 100_000)
    real_reader = historical_pairs.csv.DictReader
    consumed = 0
    first_unregistered = 2 * PAIR_COUNT + 1

    class CountedReader:
        def __init__(self, text: StringIO, *, strict: bool) -> None:
            self.actual = real_reader(text, strict=strict)
            self.fieldnames = self.actual.fieldnames

        def __iter__(self) -> Self:
            return self

        def __next__(self) -> dict[str, str | None]:
            nonlocal consumed
            item = next(self.actual)
            consumed += 1
            if consumed > first_unregistered:
                pytest.fail("historical parser consumed unregistered CSV rows")
            return item

    monkeypatch.setattr(historical_pairs.csv, "DictReader", CountedReader)
    with pytest.raises(
        historical_pairs.HistoricalEvidenceError, match="more rows"
    ):
        historical_pairs.build_report(tmp_path, TEMP)
    assert consumed == first_unregistered


@pytest.mark.parametrize("source", [PREFIX, REUSE])
def test_preregistered_repetitions_exceeding_admission_limit_rejected(
    tmp_path: Path, source: str
) -> None:
    """An absurd registered count cannot defeat the CSV row-object cap."""
    directory = _copy_source(tmp_path, source)
    _alter(
        directory,
        "benchmark.toml",
        before="repetitions = 5",
        after=f"repetitions = {historical_pairs.MAX_HISTORICAL_REPETITIONS + 1}",
    )
    with pytest.raises(
        historical_pairs.HistoricalEvidenceError, match="bounded study limit"
    ):
        historical_pairs.build_report(tmp_path, TEMP)


@pytest.mark.parametrize("source", [PREFIX, REUSE])
@pytest.mark.parametrize(
    "filename", ["experiment.toml", "benchmark.toml", "raw.csv", "source-commit.txt"]
)
def test_historical_source_changes_during_report_are_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    source: str,
    filename: str,
) -> None:
    """A reported source SHA cannot describe a file replaced after admission."""
    directory = _copy_source(tmp_path, source)
    original = historical_pairs._admitted_document

    def rewritten(
        sources: historical_pairs._StudySources, relative: str
    ) -> dict[str, Any]:
        document = original(sources, relative)
        target = directory / filename
        _ = target.write_bytes(target.read_bytes() + b"\n")
        return document

    monkeypatch.setattr(historical_pairs, "_admitted_document", rewritten)
    with pytest.raises(
        historical_pairs.HistoricalEvidenceError, match="changed before report"
    ):
        historical_pairs.build_report(tmp_path, TEMP)


@pytest.mark.parametrize(
    "error_type",
    [
        ValueError,
        TypeError,
        KeyError,
        RecursionError,
        historical_pairs.HistoricalEvidenceError,
        IndexError,
        OverflowError,
        Exception,
    ],
)
def test_historical_parser_fault_rejects_hostile_exception_formatters(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    error_type: type[Exception],
) -> None:
    """A foreign parser exception cannot execute its formatter on rejection."""

    def dangerous_str(self: Exception) -> str:
        del self
        message = "foreign parser exception formatter executed"
        raise AssertionError(message)

    hostile_type = type("HostileHistoricalFault", (error_type,), {"__str__": dangerous_str})
    fault = hostile_type("untrusted source exception")

    def broken(root: Path, relative: str) -> dict[str, Any]:
        del root, relative
        raise fault

    monkeypatch.setattr(historical_pairs, "_build_report", broken)
    with pytest.raises(
        historical_pairs.HistoricalEvidenceError,
        match=HISTORICAL_SOURCE_INCONSISTENT,
    ) as caught:
        historical_pairs.build_report(tmp_path, BASE + PREFIX)
    assert caught.value.__cause__ is fault


@pytest.mark.parametrize("fault_type", [OSError, FileNotFoundError])
def test_historical_import_preserves_direct_filesystem_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault_type: type[OSError],
) -> None:
    """Physical I/O failures retain their existing operator-facing boundary."""
    fault = fault_type("unable to read historical input")

    def broken(root: Path, relative: str) -> dict[str, Any]:
        del root, relative
        raise fault

    monkeypatch.setattr(historical_pairs, "_build_report", broken)
    with pytest.raises(fault_type, match="unable to read historical") as caught:
        historical_pairs.build_report(tmp_path, BASE + PREFIX)
    assert caught.value is fault


@pytest.mark.parametrize(
    "fault_type",
    [
        csv.Error,
        TypeError,
        ValueError,
        RuntimeError,
        RecursionError,
        IndexError,
        OverflowError,
        Exception,
    ],
)
def test_historical_raw_csv_direct_parser_fault_never_formats_foreign_error(
    monkeypatch: pytest.MonkeyPatch,
    fault_type: type[Exception],
) -> None:
    """The CSV adapter itself must not interpolate foreign parser errors."""

    def forbidden_str(self: Exception) -> str:
        del self
        raise AssertionError("foreign historical CSV parser exception formatted")

    hostile = type(
        "ForeignHistoricalCSVFault", (fault_type,), {"__str__": forbidden_str}
    )
    fault = hostile("foreign CSV failure")

    def bad_reader(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise fault

    monkeypatch.setattr(historical_pairs.csv, "DictReader", bad_reader)
    fields = historical_pairs.REGISTERED_RAW_COLUMNS[
        "prefix_decomposition_measurement"
    ]
    with pytest.raises(
        historical_pairs.HistoricalEvidenceError, match="historical raw CSV"
    ) as caught:
        historical_pairs._csv_rows(
            "repetition,strategy_id\n0,baseline\n",
            registered_fields=fields,
            expected_rows=1,
        )
    assert caught.value.__cause__ is fault


@pytest.mark.parametrize(
    "variant", ["header-container", "header-cell", "row-container", "row-cell"]
)
def test_historical_csv_parser_foreign_record_objects_reject_without_dispatch(
    monkeypatch: pytest.MonkeyPatch,
    variant: str,
) -> None:
    """Substituted parser rows cannot invoke caller-defined comparison methods."""
    native_fields = sorted(
        historical_pairs.REGISTERED_RAW_COLUMNS[
            "prefix_decomposition_measurement"
        ]
    )

    class HostileHeader(list[str]):
        def __iter__(self) -> Iterator[str]:
            raise AssertionError("foreign CSV header iteration executed")

    class HostileField(str):
        def __hash__(self) -> int:
            raise AssertionError("foreign CSV field hashing executed")

    class HostileRow(dict[str, str]):
        def values(self) -> Any:
            raise AssertionError("foreign CSV row iteration executed")

    class HostileValue(str):
        def __eq__(self, other: object) -> bool:
            del other
            raise AssertionError("foreign CSV value equality executed")

    header: list[str] = native_fields
    row: dict[str, str] = dict.fromkeys(native_fields, "0")
    if variant == "header-container":
        header = HostileHeader(native_fields)
    elif variant == "header-cell":
        header = [HostileField("repetition"), *native_fields[1:]]
    elif variant == "row-container":
        row = HostileRow(row)
    else:
        row["repetition"] = HostileValue("0")

    class FakeReader:
        fieldnames = header

        def __iter__(self) -> Iterator[dict[str, str]]:
            return iter([row])

    def substitute(*args: object, **kwargs: object) -> FakeReader:
        del args, kwargs
        return FakeReader()

    monkeypatch.setattr(historical_pairs.csv, "DictReader", substitute)
    with pytest.raises(historical_pairs.HistoricalEvidenceError, match="native CSV"):
        historical_pairs._csv_rows(
            ",".join(native_fields) + "\n" + ",".join(["0"] * len(native_fields)),
            registered_fields=frozenset(native_fields),
            expected_rows=1,
        )


def test_historical_raw_csv_native_parser_error_retains_detail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Real CSV syntax diagnostics remain distinguishable from host faults."""
    fault = csv.Error("unexpected end of data")

    def bad_reader(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise fault

    monkeypatch.setattr(historical_pairs.csv, "DictReader", bad_reader)
    fields = historical_pairs.REGISTERED_RAW_COLUMNS[
        "prefix_decomposition_measurement"
    ]
    with pytest.raises(
        historical_pairs.HistoricalEvidenceError, match="unexpected end of data"
    ) as caught:
        historical_pairs._csv_rows(
            "repetition,strategy_id\n0,baseline\n",
            registered_fields=fields,
            expected_rows=1,
        )
    assert caught.value.__cause__ is fault


@pytest.mark.parametrize(
    "error",
    [
        ValueError("native syntax failure"),
        historical_pairs.HistoricalEvidenceError("missing trial"),
    ],
)
def test_historical_native_parser_fault_retains_useful_diagnostic(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    error: Exception,
) -> None:
    """Known built-in and project exceptions retain the original reason."""

    def broken(root: Path, relative: str) -> dict[str, Any]:
        del root, relative
        raise error

    monkeypatch.setattr(historical_pairs, "_build_report", broken)
    with pytest.raises(historical_pairs.HistoricalEvidenceError, match=str(error)) as caught:
        historical_pairs.build_report(tmp_path, BASE + PREFIX)
    assert caught.value.__cause__ is error


@pytest.mark.parametrize(
    ("filename", "source_error"),
    [
        ("experiment.toml", RecursionError),
        ("benchmark.toml", benchmark_protocol.BenchmarkProtocolError),
    ],
)
def test_nested_historical_toml_capacity_failure_is_typed(
    tmp_path: Path,
    filename: str,
    source_error: type[Exception],
) -> None:
    """A bounded source TOML cannot leak parser recursion into the operator."""
    root = _copy_source(tmp_path, PREFIX)
    source = root / filename
    malformed = "\nrecursion_probe = " + "[" * 1000 + "1" + "]" * 1000
    _ = source.write_text(
        source.read_text(encoding="utf-8") + malformed,
        encoding="utf-8",
    )
    with pytest.raises(
        historical_pairs.HistoricalEvidenceError,
        match=HISTORICAL_SOURCE_INCONSISTENT,
    ) as error:
        historical_pairs.build_report(tmp_path, TEMP)
    assert isinstance(error.value.__cause__, source_error)


def test_historical_cli_rejects_deep_toml_without_partial_stdout(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Operator returns a typed failure rather than leaking parser recursion."""
    root = _copy_source(tmp_path, REUSE)
    source = root / "benchmark.toml"
    _ = source.write_text(
        source.read_text(encoding="utf-8")
        + "\nrecursion_probe = "
        + "[" * 1000
        + "1"
        + "]" * 1000,
        encoding="utf-8",
    )
    monkeypatch.setattr(
        sys,
        "argv",
        ["historical-pairs", TEMP, "--root", str(tmp_path)],
    )
    with pytest.raises(SystemExit, match="2"):
        historical_pairs.main()
    rejected = capsys.readouterr()
    assert not rejected.out
    assert HISTORICAL_SOURCE_INCONSISTENT in rejected.err


def test_missing_and_linked_historical_source_rejected(tmp_path: Path) -> None:
    """Versioned import never follows an absent or redirected source file."""
    directory = _copy_source(tmp_path, PREFIX)
    raw_path = directory / "raw.csv"
    raw_path.unlink()
    with pytest.raises(FileNotFoundError, match=r"raw\.csv"):
        historical_pairs.build_report(tmp_path, TEMP)
    raw_path.symlink_to(REPO / BASE / PREFIX / "raw.csv")
    with pytest.raises(
        historical_pairs.HistoricalEvidenceError, match="symlink"
    ):
        historical_pairs.build_report(tmp_path, TEMP)


@pytest.mark.parametrize(
    "invalid_relative", [None, False, b"benchmarks/research/evidence/a", [], 3]
)
def test_historical_import_rejects_nonstring_source_before_access(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    invalid_relative: object,
) -> None:
    """Malformed direct source identifiers cannot execute importer I/O."""

    def forbid_import(*args: object, **kwargs: object) -> dict[str, object]:
        _ = (args, kwargs)
        message = "untyped historical source reached import"
        raise AssertionError(message)

    monkeypatch.setattr(historical_pairs, "_build_report", forbid_import)
    with pytest.raises(historical_pairs.HistoricalEvidenceError, match="exact"):
        historical_pairs.build_report(tmp_path, cast("str", invalid_relative))


def test_historical_import_rejects_forged_string_subclass(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A purported relative string cannot override its prefix check."""

    class ForgedSource(str):  # ruff: ignore[subclass-builtin]
        def startswith(self, *args: object, **kwargs: object) -> bool:
            _ = (args, kwargs)
            message = "untrusted startswith executed"
            raise AssertionError(message)

    def forbid_import(*args: object, **kwargs: object) -> dict[str, object]:
        _ = (args, kwargs)
        message = "forged relative source reached import"
        raise AssertionError(message)

    monkeypatch.setattr(historical_pairs, "_build_report", forbid_import)
    with pytest.raises(historical_pairs.HistoricalEvidenceError, match="exact"):
        historical_pairs.build_report(
            tmp_path, ForgedSource(BASE + PREFIX)
        )


@pytest.mark.parametrize("invalid_root", [None, "not-a-path", False])
def test_historical_import_rejects_nonnative_root_before_access(
    monkeypatch: pytest.MonkeyPatch,
    invalid_root: object,
) -> None:
    """An invalid root never reaches imported source filesystem resolution."""

    def forbid_import(*args: object, **kwargs: object) -> dict[str, object]:
        _ = (args, kwargs)
        message = "invalid source root reached import"
        raise AssertionError(message)

    monkeypatch.setattr(historical_pairs, "_build_report", forbid_import)
    with pytest.raises(historical_pairs.HistoricalEvidenceError, match="native Path"):
        historical_pairs.build_report(cast("Path", invalid_root), BASE + PREFIX)


def test_historical_import_rejects_redirected_root_subclass(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The source root cannot masquerade as another physical filesystem path."""

    class RedirectedRoot(type(tmp_path)):
        def __fspath__(self) -> str:
            return str(tmp_path / "outside")

    forged = RedirectedRoot(tmp_path)
    assert str(forged) == str(tmp_path)

    def forbid_import(*args: object, **kwargs: object) -> dict[str, object]:
        _ = (args, kwargs)
        message = "foreign root reached import"
        raise AssertionError(message)

    monkeypatch.setattr(historical_pairs, "_build_report", forbid_import)
    with pytest.raises(historical_pairs.HistoricalEvidenceError, match="native Path"):
        historical_pairs.build_report(forged, BASE + PREFIX)


def test_unsupported_source_root_rejected(tmp_path: Path) -> None:
    """Callers cannot import unrelated data paths into a performance claim."""
    with pytest.raises(
        historical_pairs.HistoricalEvidenceError, match="research evidence"
    ):
        historical_pairs.build_report(tmp_path, "untrusted/samples")


def test_incomplete_quality_fingerprint_rejected(tmp_path: Path) -> None:
    """A matching row is insufficient without valid registered SHA-256."""
    directory = _copy_source(tmp_path, PREFIX)
    source = (directory / "experiment.toml").read_text(encoding="utf-8")
    section = source.split("[prefix_decomposition_measurement]", 1)
    original = section[1]
    fingerprint = original.split('quality_map_sha256 = "', 1)[1].split('"', 1)[
        0
    ]
    original = original.replace(
        'quality_map_sha256 = "' + fingerprint + '"',
        'quality_map_sha256 = "not-a-digest"',
    )
    _ = (directory / "experiment.toml").write_text(
        section[0] + "[prefix_decomposition_measurement]" + original,
        encoding="utf-8",
    )
    with pytest.raises(
        historical_pairs.HistoricalEvidenceError,
        match="quality-map fingerprint",
    ):
        historical_pairs.build_report(tmp_path, TEMP)


def test_historical_cli_prints_no_partial_result_on_bad_source(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Historical replay prints an entire arena report or no JSON at all."""
    directory = _copy_source(tmp_path, PREFIX)
    monkeypatch.setattr(
        sys,
        "argv",
        ["historical-pairs", TEMP, "--root", str(tmp_path)],
    )
    assert historical_pairs.main() == 0
    result = json.loads(capsys.readouterr().out)
    assert result["historical_evidence"]["evidence_status"] == SOURCE_REPORTED
    _alter(
        directory,
        "raw.csv",
        before="831921051",
        after="9999999999999999999",
    )
    with pytest.raises(SystemExit, match="2"):
        historical_pairs.main()
    rejected = capsys.readouterr()
    assert not rejected.out
    assert rejected.err.startswith("arena historical evidence:")


class _BrokenReportStream:
    """Simulate text-stream completion claims independently of the importer."""

    def __init__(self, mode: str) -> None:
        self.mode = mode
        self.written: list[str] = []
        self.flushed = False

    def write(self, record: str) -> int:
        """Accept a record prefix or report an untrustworthy write count."""
        if self.mode == "write-error":
            raise OSError("injected historical stdout failure")
        accepted = len(record) // 2 if self.mode == "short" else len(record)
        self.written.append(record[:accepted])
        if self.mode == "boolean":
            return True
        return accepted

    def flush(self) -> None:
        """Record successful flushing or inject a late stream failure."""
        if self.mode == "flush-error":
            raise RuntimeError("injected historical flush failure")
        self.flushed = True


@pytest.mark.parametrize("mode", ["short", "boolean", "write-error", "flush-error"])
def test_historical_cli_requires_confirmed_report_output(
    mode: str,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A valid imported study cannot produce a zero exit on a failed writer."""
    output = _BrokenReportStream(mode)
    monkeypatch.setattr(
        sys, "argv", ["historical-pairs", BASE + PREFIX, "--root", str(REPO)]
    )
    monkeypatch.setattr(historical_pairs.sys, "stdout", output)
    with pytest.raises(SystemExit, match="2"):
        historical_pairs.main()
    assert not output.flushed
    diagnostic = capsys.readouterr().err
    assert "arena historical evidence:" in diagnostic
    assert "stdout" in diagnostic


@pytest.mark.parametrize("kind", [csv.Error, ValueError, KeyError])
def test_historical_native_parser_arguments_are_not_formatted(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    kind: type[Exception],
) -> None:
    """Exact parser errors may still carry an untrusted diagnostic object."""

    class HostileArgument:
        def __str__(self) -> str:
            raise AssertionError("foreign historical parser argument formatter")

    fault = kind(HostileArgument())

    def fail(*_args: object, **_kwargs: object) -> None:
        raise fault

    if kind is csv.Error:
        monkeypatch.setattr(historical_pairs.csv, "DictReader", fail)
        with pytest.raises(historical_pairs.HistoricalEvidenceError) as caught:
            historical_pairs._csv_rows(
                "repetition,strategy_id\n0,baseline\n",
                registered_fields=historical_pairs.REGISTERED_RAW_COLUMNS[
                    "prefix_decomposition_measurement"
                ],
                expected_rows=1,
            )
    else:
        monkeypatch.setattr(historical_pairs, "_build_report", fail)
        with pytest.raises(historical_pairs.HistoricalEvidenceError) as caught:
            historical_pairs.build_report(tmp_path, BASE + PREFIX)
    assert caught.value.__cause__ is fault


@pytest.mark.parametrize(
    "kind",
    [
        historical_pairs.HistoricalEvidenceError,
        historical_pairs.experiment_manifest.ExperimentManifestError,
        historical_pairs.benchmark_protocol.BenchmarkProtocolError,
        historical_pairs.report_output.ReportOutputError,
        OSError,
        UnicodeError,
    ],
)
@pytest.mark.parametrize("hostile_class", [True, False])
def test_historical_cli_rejects_hostile_error_diagnostics(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    kind: type[Exception],
    hostile_class: bool,
) -> None:
    """Foreign exception subclasses and exact class hostile args keep exit two."""

    class HostileArgument:
        def __str__(self) -> str:
            raise AssertionError("hostile native argument formatter executed")

    class HostileClass(kind):
        def __str__(self) -> str:
            raise AssertionError("hostile exception subclass formatter executed")

    fault = (
        HostileClass("untrusted detail")
        if hostile_class
        else kind(HostileArgument())
    )

    def fail(*_args: object, **_kwargs: object) -> None:
        raise fault

    monkeypatch.setattr(historical_pairs, "build_report", fail)
    monkeypatch.setattr(sys, "argv", ["historical-pairs", BASE + PREFIX])
    with pytest.raises(SystemExit) as caught:
        historical_pairs.main()
    assert caught.value.code == 2
    captured = capsys.readouterr()
    assert captured.err.startswith("arena historical evidence:")
    assert not captured.out


def test_historical_cli_keeps_exact_native_failure_text(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A literal local failure retains its information for operators."""

    def fail(*_args: object, **_kwargs: object) -> None:
        raise historical_pairs.HistoricalEvidenceError("exact local source rejection")

    monkeypatch.setattr(historical_pairs, "build_report", fail)
    monkeypatch.setattr(sys, "argv", ["historical-pairs", BASE + PREFIX])
    with pytest.raises(SystemExit, match="2"):
        historical_pairs.main()
    assert "exact local source rejection" in capsys.readouterr().err


@pytest.mark.parametrize("phase", ["build", "publish"])
@pytest.mark.parametrize("hostile_class", [False, True])
def test_historical_cli_types_unexpected_dependency_failures(
    phase: str,
    hostile_class: bool,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Unexpected importer or publisher faults cannot leak or claim success."""

    class HostileArgument:
        def __str__(self) -> str:
            raise AssertionError("unexpected failure argument was formatted")

    class HostileRuntimeError(RuntimeError):
        def __str__(self) -> str:
            raise AssertionError("unexpected failure subtype was formatted")

    fault = (
        HostileRuntimeError("foreign fault")
        if hostile_class
        else RuntimeError(HostileArgument())
    )

    def fail(*_args: object, **_kwargs: object) -> None:
        raise fault

    monkeypatch.setattr(sys, "argv", ["historical-pairs", BASE + PREFIX])
    if phase == "build":
        monkeypatch.setattr(historical_pairs, "build_report", fail)
        monkeypatch.setattr(
            historical_pairs.report_output,
            "publish",
            lambda *_args, **_kwargs: pytest.fail("published failed build"),
        )
    else:
        monkeypatch.setattr(
            historical_pairs, "build_report", lambda *_args, **_kwargs: {}
        )
        monkeypatch.setattr(historical_pairs.report_output, "publish", fail)
    with pytest.raises(SystemExit) as caught:
        historical_pairs.main()
    assert caught.value.code == 2
    captured = capsys.readouterr()
    assert not captured.out
    assert captured.err.startswith("arena historical evidence:")
    assert "RuntimeError" in captured.err


@pytest.mark.parametrize("scope", ["manifest", "measurement"])
def test_historical_extension_rejects_foreign_toml_keys_before_lookup(
    scope: str,
) -> None:
    """A dependency-owned TOML key must not execute equality during admission."""

    class CollidingKey:
        def __hash__(self) -> int:
            return hash(
                "prefix_decomposition_measurement"
                if scope == "manifest"
                else "baseline_strategy"
            )

        def __eq__(self, other: object) -> bool:
            del other
            raise AssertionError("foreign historical TOML key comparison executed")

    if scope == "manifest":
        result: dict[object, object] = {CollidingKey(): {}}
    else:
        result = {"prefix_decomposition_measurement": {CollidingKey(): "baseline"}}
    with pytest.raises(
        historical_pairs.HistoricalEvidenceError, match="native string keys"
    ):
        historical_pairs._extension(cast("dict[str, Any]", result))


@pytest.mark.parametrize("scope", ["root", "study", "resources"])
def test_historical_benchmark_reparse_admits_native_mapping_keys(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, scope: str
) -> None:
    """Reparsed benchmark TOML cannot dispatch foreign mapping equality hooks."""
    directory = _copy_source(tmp_path, PREFIX)
    benchmark_text = (directory / "benchmark.toml").read_text(encoding="utf-8")
    native_loads = historical_pairs.tomllib.loads
    benchmark_reads = 0
    key_name = (
        "study"
        if scope == "root"
        else ("baseline" if scope == "study" else "memory_mib")
    )

    class CollidingKey:
        def __hash__(self) -> int:
            return hash(key_name)

        def __eq__(self, other: object) -> bool:
            del other
            raise AssertionError("untrusted benchmark TOML equality executed")

    def inject(text: str) -> dict[str, Any]:
        nonlocal benchmark_reads
        result = native_loads(text)
        if text != benchmark_text:
            return result
        benchmark_reads += 1
        if benchmark_reads != 2:
            return result
        if scope == "root":
            del result["study"]
            cast("dict[object, Any]", result)[CollidingKey()] = {}
        else:
            table = result[scope]
            del table[key_name]
            cast("dict[object, Any]", table)[CollidingKey()] = (
                "baseline" if scope == "study" else 512
            )
        return result

    monkeypatch.setattr(historical_pairs.tomllib, "loads", inject)
    with pytest.raises(
        historical_pairs.HistoricalEvidenceError, match="native string keys"
    ):
        historical_pairs.build_report(tmp_path, TEMP)
    assert benchmark_reads == 2


@pytest.mark.parametrize("field", ["study", "resources"])
def test_historical_benchmark_rejects_substituted_native_source_values(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    field: str,
) -> None:
    """Native benchmark values must reflect the original retained TOML."""
    root = _copy_source(tmp_path, PREFIX)
    original = (root / "benchmark.toml").read_text(encoding="utf-8")
    native = historical_pairs.tomllib.loads
    forged = native(original)
    if field == "study":
        forged["study"]["id"] = "forged-history"
    else:
        forged["resources"]["memory_mib"] += 1
    monkeypatch.setattr(historical_pairs.tomllib, "loads", lambda *_a: forged)
    with pytest.raises(historical_pairs.HistoricalEvidenceError, match="source TOML"):
        historical_pairs._admit_benchmark_data(original)


@pytest.mark.parametrize("field", ["baseline", "budget"])
def test_historical_manifest_rejects_substituted_native_source_values(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    field: str,
) -> None:
    """The historical manifest extension and limits require source values."""
    _copy_source(tmp_path, PREFIX)
    name = TEMP + "/experiment.toml"
    original = (tmp_path / name).read_text(encoding="utf-8")
    native = historical_pairs.tomllib.loads
    forged = native(original)
    if field == "baseline":
        forged["prefix_decomposition_measurement"]["baseline_strategy"] = "forged"
    else:
        forged["budget"]["seconds"] += 1

    def tamper(text: str) -> dict[str, Any]:
        return forged if text == original else native(text)

    monkeypatch.setattr(historical_pairs.tomllib, "loads", tamper)
    with pytest.raises(historical_pairs.HistoricalEvidenceError, match="source TOML"):
        historical_pairs._load_source(tmp_path, TEMP)


def test_historical_benchmark_source_preserves_equivalent_loader_wrapper(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A decoder with equivalent native values remains allowed."""
    root = _copy_source(tmp_path, PREFIX)
    original = (root / "benchmark.toml").read_text(encoding="utf-8")
    native = historical_pairs.tomllib.loads
    monkeypatch.setattr(
        historical_pairs.tomllib, "loads", lambda text: native(text)
    )
    assert historical_pairs._admit_benchmark_data(original) == native(original)


@pytest.mark.parametrize("kind", ["benchmark", "manifest"])
def test_historical_equivalent_loader_cannot_mutate_admitted_toml(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
) -> None:
    """Source-matched maps cannot retain aliases owned by a wrapper decoder."""
    root = _copy_source(tmp_path, PREFIX)
    leaf = "benchmark.toml" if kind == "benchmark" else "experiment.toml"
    original = (root / leaf).read_text(encoding="utf-8")
    native = historical_pairs.tomllib.loads
    returned: list[dict[str, Any]] = []

    def delegated(text: str) -> dict[str, Any]:
        receipt = native(text)
        if text == original:
            returned.append(receipt)
            if kind == "manifest":
                # Later core manifest decoding requires the original provider.
                monkeypatch.setattr(historical_pairs.tomllib, "loads", native)
        return receipt

    monkeypatch.setattr(historical_pairs.tomllib, "loads", delegated)
    if kind == "benchmark":
        admitted = historical_pairs._admit_benchmark_data(original)
        field, key, forged = "study", "id", "forged-history"
    else:
        admitted = historical_pairs._load_source(tmp_path, TEMP).manifest_data
        field, key, forged = "budget", "seconds", 999
    assert returned
    assert admitted == returned[0]
    assert admitted is not returned[0]
    foreign_nested = cast("dict[str, Any]", returned[0][field])
    foreign_nested[key] = forged
    assert admitted[field][key] != forged


@pytest.mark.parametrize("raw", ["true", "1.0"])
def test_historical_benchmark_rejects_equal_but_nonnative_source_number(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    raw: str,
) -> None:
    """A forged 1 must not match source bool or float under Python ==."""
    root = _copy_source(tmp_path, PREFIX)
    original = (root / "benchmark.toml").read_text(encoding="utf-8")
    source = original + f"\n[unchecked_integer_test]\nvalue = {raw}\n"
    native = historical_pairs.tomllib.loads
    forged = native(source)
    forged["unchecked_integer_test"]["value"] = 1
    monkeypatch.setattr(historical_pairs.tomllib, "loads", lambda *_a: forged)
    with pytest.raises(historical_pairs.HistoricalEvidenceError, match="source TOML"):
        historical_pairs._admit_benchmark_data(source)


def test_historical_import_cli_rejects_forged_manifest_without_stdout(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """No historical comparison is published from substituted run limits."""
    root = _copy_source(tmp_path, PREFIX)
    manifest = (root / "experiment.toml").read_text(encoding="utf-8")
    native = historical_pairs.tomllib.loads

    def forged(text: str) -> dict[str, Any]:
        document = native(text)
        if text == manifest:
            document["budget"]["seconds"] += 1
        return document

    monkeypatch.setattr(historical_pairs.tomllib, "loads", forged)
    monkeypatch.setattr(
        sys,
        "argv",
        ["historical-pairs", TEMP, "--root", str(tmp_path)],
    )
    with pytest.raises(SystemExit, match="2"):
        historical_pairs.main()
    captured = capsys.readouterr()
    assert not captured.out
    assert "source TOML" in captured.err


def test_historical_native_toml_comparator_rejects_foreign_nested_key() -> None:
    """Nested adversarial key equality must not be invoked during matching."""

    class HostileKey:
        def __hash__(self) -> int:
            return hash("identity")

        def __eq__(self, _other: object) -> bool:
            raise AssertionError("foreign historical TOML key equality executed")

    expected = {"measurements": [{"identity": "v1"}]}
    observed = {"measurements": [{HostileKey(): "v1"}]}
    assert not historical_pairs._same_native_toml(observed, expected)


@pytest.mark.parametrize("path", ["reader", "direct-csv"])
def test_historical_source_byte_limit_ignores_mutable_public_cap(
    monkeypatch: pytest.MonkeyPatch,
    path: str,
) -> None:
    """A changed public cap must not admit more than four MiB of evidence."""
    oversized = b"x" * (4 * 1024 * 1024 + 1)
    monkeypatch.setattr(historical_pairs, "MAX_SOURCE_BYTES", len(oversized) + 1)
    if path == "reader":
        monkeypatch.setattr(
            historical_pairs.evidence,
            "read_bounded_regular",
            lambda *_args, **_kwargs: oversized,
        )
        with pytest.raises(
            historical_pairs.HistoricalEvidenceError, match="bounded bytes"
        ):
            historical_pairs._source(REPO, BASE + PREFIX + "/raw.csv")
    else:
        with pytest.raises(
            historical_pairs.HistoricalEvidenceError, match="bounded text"
        ):
            historical_pairs._admit_csv_text(oversized.decode("ascii"))


def test_historical_header_limit_ignores_mutable_public_cap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A forged size policy cannot admit an oversized first CSV line."""
    monkeypatch.setattr(historical_pairs, "MAX_CSV_HEADER_CHARS", 8192)
    with pytest.raises(historical_pairs.HistoricalEvidenceError, match="CSV header"):
        historical_pairs._require_bounded_csv_header("x" * 513 + "\n")


def test_historical_repetitions_limit_ignores_mutable_public_cap(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A substituted repetition budget cannot admit a huge protocol."""
    directory = _copy_source(tmp_path, PREFIX)
    _alter(
        directory,
        "benchmark.toml",
        before="repetitions = 5",
        after="repetitions = 4097",
    )
    monkeypatch.setattr(historical_pairs, "MAX_HISTORICAL_REPETITIONS", 8192)
    with pytest.raises(
        historical_pairs.HistoricalEvidenceError, match="bounded study limit"
    ):
        historical_pairs._load_source(tmp_path, TEMP)


@pytest.mark.parametrize("factor", ["SECONDS_TO_NS", "MIB_TO_BYTES"])
def test_historical_budget_units_ignore_mutable_public_factors(
    monkeypatch: pytest.MonkeyPatch, factor: str
) -> None:
    """An imported study's exact budgets cannot change after source admission."""
    relative = BASE + PREFIX
    sources = historical_pairs._load_source(REPO, relative)
    original = historical_pairs._admitted_document(sources, relative)
    monkeypatch.setattr(historical_pairs, factor, 2)
    document = historical_pairs._admitted_document(sources, relative)
    assert document["study"]["budget"] == original["study"]["budget"]


@pytest.mark.parametrize("negative", ["-1", "-12"])
def test_historical_paired_repetitions_reject_rebound_signed_digits(
    monkeypatch: pytest.MonkeyPatch,
    negative: str,
) -> None:
    """Changing public digits cannot certify a negative source trial index."""
    records = [
        {"strategy_id": "baseline", "repetition": negative},
        {"strategy_id": "candidate", "repetition": negative},
    ]
    monkeypatch.setattr(historical_pairs, "ASCII_DIGITS", frozenset("0123456789-"))
    with pytest.raises(historical_pairs.HistoricalEvidenceError, match="numeric field"):
        historical_pairs._paired_rows(records, "baseline", "candidate", repetitions=1)


def test_historical_structural_counts_reject_rebound_signed_digits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A mutable digit policy cannot admit negative verifier-call samples."""
    records = [
        {"strategy_id": "baseline", "independent_verifier_calls": "-3"},
        {"strategy_id": "candidate", "independent_verifier_calls": "4"},
    ]
    monkeypatch.setattr(historical_pairs, "ASCII_DIGITS", frozenset("0123456789-"))
    with pytest.raises(historical_pairs.HistoricalEvidenceError, match="numeric field"):
        historical_pairs._structural_counts(records, "baseline", "candidate")


def test_historical_number_rejects_foreign_str_iterator() -> None:
    """A str subclass cannot falsify its character stream to admit a sign."""

    class ForgedDigits(str):
        def __iter__(self) -> Iterator[str]:
            return iter("1")

    with pytest.raises(historical_pairs.HistoricalEvidenceError, match="numeric field"):
        historical_pairs._integer(ForgedDigits("-1"), "repetition")


def test_historical_native_numeric_inputs_ignore_reduced_public_digits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Valid native decimal data must not depend on a replaced public alias."""
    monkeypatch.setattr(historical_pairs, "ASCII_DIGITS", frozenset("-"))
    assert historical_pairs._integer("12", "verifier calls") == 12


def test_historical_quality_digest_ignores_mutable_hex_alphabet(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Changing an exported hex policy cannot admit uppercase digest text."""
    monkeypatch.setattr(
        historical_pairs, "HEX_DIGITS", frozenset("0123456789abcdefABCDEF")
    )
    with pytest.raises(
        historical_pairs.HistoricalEvidenceError, match="lowercase SHA-256"
    ):
        historical_pairs._quality_digest({"quality_map_sha256": "F" * 64})


def test_historical_quality_digest_ignores_mutable_sha256_length(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A changed analyzer digest length cannot admit an arbitrary short token."""
    monkeypatch.setattr(historical_pairs.analyze, "SHA256_HEX_LENGTH", 3)
    with pytest.raises(historical_pairs.HistoricalEvidenceError, match="not SHA-256"):
        historical_pairs._quality_digest({"quality_map_sha256": "abc"})


def test_historical_csv_nul_guard_ignores_mutable_analyzer_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A policy alias cannot turn NUL-containing CSV into ordinary evidence."""
    monkeypatch.setattr(historical_pairs.analyze, "NUL", "not-a-nul")
    with pytest.raises(historical_pairs.HistoricalEvidenceError, match="contain NUL"):
        historical_pairs._csv_rows(
            "repetition,strategy_id\n0,base\x00line\n",
            registered_fields=frozenset({"repetition", "strategy_id"}),
            expected_rows=1,
        )


def test_historical_lowered_public_caps_preserve_native_inputs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Only the original cap, not a subsequently lowered alias, is enforced."""
    monkeypatch.setattr(historical_pairs, "MAX_SOURCE_BYTES", 1)
    monkeypatch.setattr(historical_pairs, "MAX_CSV_HEADER_CHARS", 1)
    monkeypatch.setattr(historical_pairs, "MAX_HISTORICAL_REPETITIONS", 1)
    raw = historical_pairs._source(REPO, BASE + PREFIX + "/raw.csv")
    assert raw[0].startswith("repetition,")
    historical_pairs._require_bounded_csv_header(raw[0])
    sources = historical_pairs._load_source(REPO, BASE + PREFIX)
    assert sources.protocol.repetitions == PAIR_COUNT


@pytest.mark.parametrize("forgery", ["timing", "header"])
def test_historical_csv_parser_cannot_invent_native_source_receipts(
    monkeypatch: pytest.MonkeyPatch,
    forgery: str,
) -> None:
    """A plausible CSV parser receipt must match the actual native CSV text."""
    source = (REPO / BASE / PREFIX / "raw.csv").read_text(encoding="utf-8")
    fields = historical_pairs.REGISTERED_RAW_COLUMNS[
        "prefix_decomposition_measurement"
    ]
    native_reader = csv.DictReader

    class ForgedReader:
        def __init__(self, stream: Any, *, strict: bool) -> None:
            self.native = native_reader(stream, strict=strict)
            native_fields = self.native.fieldnames
            assert native_fields is not None
            self.fieldnames = (
                list(reversed(native_fields)) if forgery == "header" else native_fields
            )

        def __iter__(self) -> Self:
            return self

        def __next__(self) -> dict[str, str]:
            row = next(self.native)
            if forgery == "timing":
                row["elapsed_nanoseconds"] = str(int(row["elapsed_nanoseconds"]) + 1)
            return row

    monkeypatch.setattr(historical_pairs.csv, "DictReader", ForgedReader)
    with pytest.raises(
        historical_pairs.HistoricalEvidenceError, match="CSV.*source"
    ):
        historical_pairs._csv_rows(
            source, registered_fields=fields, expected_rows=2 * PAIR_COUNT
        )


@pytest.mark.parametrize("source", [PREFIX, REUSE])
def test_historical_build_report_rejects_parser_forged_elapsed_timing(
    monkeypatch: pytest.MonkeyPatch,
    source: str,
) -> None:
    """A source-timing forgery must not enter either published paired study."""
    native_reader = csv.DictReader

    class AlteredTimingReader(native_reader):
        def __next__(self) -> dict[str, str | None]:
            row = super().__next__()
            original = row["elapsed_nanoseconds"]
            assert type(original) is str
            row["elapsed_nanoseconds"] = str(int(original) + 1)
            return row

    monkeypatch.setattr(historical_pairs.csv, "DictReader", AlteredTimingReader)
    with pytest.raises(
        historical_pairs.HistoricalEvidenceError, match="CSV.*source"
    ):
        historical_pairs.build_report(REPO, BASE + source)


def test_historical_canonical_csv_reader_preserves_blank_physical_lines() -> None:
    """Original CSV reader and DictReader both skip trailing blank records."""
    source = (REPO / BASE / PREFIX / "raw.csv").read_text(encoding="utf-8")
    fields = historical_pairs.REGISTERED_RAW_COLUMNS[
        "prefix_decomposition_measurement"
    ]
    original = historical_pairs._csv_rows(
        source, registered_fields=fields, expected_rows=2 * PAIR_COUNT
    )
    assert historical_pairs._csv_rows(
        source + "\n", registered_fields=fields, expected_rows=2 * PAIR_COUNT
    ) == original


@pytest.mark.parametrize("kind", ["outcome", "profile", "kind", "metric"])
def test_historical_identity_ignores_mutable_semantic_labels(
    monkeypatch: pytest.MonkeyPatch, kind: str
) -> None:
    """A mutable label cannot reinterpret nonclassic or failed source runs."""
    relative = BASE + PREFIX
    sources = historical_pairs._load_source(REPO, relative)
    manifest = sources.manifest
    protocol = sources.protocol
    if kind == "outcome":
        assert manifest.run is not None
        manifest = replace(manifest, run=replace(manifest.run, outcome="rejected"))
        monkeypatch.setattr(historical_pairs, "RUN_SUCCEEDED", "rejected")
    elif kind == "profile":
        manifest = replace(manifest, target_profile="malbolge-2026")
        monkeypatch.setattr(historical_pairs, "CLASSIC_PROFILE", "malbolge-2026")
    elif kind == "kind":
        protocol = replace(protocol, kind="stochastic")
        monkeypatch.setattr(historical_pairs, "DETERMINISTIC_KIND", "stochastic")
    else:
        protocol = replace(
            protocol,
            metrics=tuple(m for m in protocol.metrics if m != "elapsed_nanoseconds"),
        )
        monkeypatch.setattr(
            historical_pairs, "ELAPSED_SOURCE_FIELD", "independent_verifier_calls"
        )
    with pytest.raises(historical_pairs.HistoricalEvidenceError):
        historical_pairs._source_identity(
            manifest,
            protocol,
            relative,
            source_commit=sources.source_commit,
        )


def test_historical_extension_ignores_mutable_public_registration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An unsupported extension cannot become registered by dictionary edits."""
    updated = dict(historical_pairs.EXTENSION_CONFIG)
    updated["foreign_measurement"] = ("candidate", "accepted", "size", "calls")
    monkeypatch.setattr(historical_pairs, "EXTENSION_CONFIG", updated)
    with pytest.raises(
        historical_pairs.HistoricalEvidenceError, match="unsupported"
    ):
        historical_pairs._extension({"foreign_measurement": {}})


def test_historical_csv_schema_ignores_mutable_public_registration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An added CSV field is not source-registered by a mutable field map."""
    directory = _copy_source(tmp_path, PREFIX)
    raw_path = directory / "raw.csv"
    raw = raw_path.read_text(encoding="utf-8")
    raw_path.write_text(
        "\n".join(f"{row},foreign" for row in raw.splitlines()) + "\n",
        encoding="utf-8",
    )
    updated = dict(historical_pairs.REGISTERED_RAW_COLUMNS)
    original = updated["prefix_decomposition_measurement"]
    updated["prefix_decomposition_measurement"] = original | {"foreign"}
    monkeypatch.setattr(historical_pairs, "REGISTERED_RAW_COLUMNS", updated)
    with pytest.raises(historical_pairs.HistoricalEvidenceError, match="CSV columns"):
        historical_pairs.build_report(tmp_path, TEMP)


@pytest.mark.parametrize("field", ["VERIFIED", "ACCEPTED"])
def test_historical_reported_outcome_ignores_mutable_analyzer_labels(
    monkeypatch: pytest.MonkeyPatch,
    field: str,
) -> None:
    """The retained success outcome cannot become a caller-invented verdict."""
    relative = BASE + PREFIX
    sources = historical_pairs._load_source(REPO, relative)
    original = historical_pairs._reported_row(
        sources.records[0], sources.manifest, relative=relative
    )
    monkeypatch.setattr(historical_pairs.analyze, field, "forged-success")
    observed = historical_pairs._reported_row(
        sources.records[0], sources.manifest, relative=relative
    )
    assert observed["outcome"] == original["outcome"]
    assert observed["verifier_verdict"] == original["verifier_verdict"]


def test_historical_schema_registration_ignores_inplace_config_edits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Mutation of the original exported map cannot change a source registry."""
    original = historical_pairs._extension(
        {"prefix_decomposition_measurement": {}}
    )[1]
    monkeypatch.setitem(
        historical_pairs.EXTENSION_CONFIG,
        "prefix_decomposition_measurement",
        ("forged", "metadata", "not", "source"),
    )
    assert historical_pairs._extension(
        {"prefix_decomposition_measurement": {}}
    )[1] == original


def test_historical_csv_forged_true_preflight_cannot_allocate_excess_columns(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An altered pre-parser verdict cannot reach a massive CSV row parser."""
    columns = frozenset({"repetition", "strategy_id"})
    text = "repetition,strategy_id\n0,baseline" + ",filler" * 10_000 + "\n"
    assert not historical_pairs.csv_admission.within_column_limit(text, 2)

    def forbidden_reader(*_args: object, **_kwargs: object) -> None:
        pytest.fail("oversized CSV reached the allocating DictReader")

    monkeypatch.setattr(
        historical_pairs.csv_admission,
        "within_column_limit",
        lambda *_args: True,
    )
    monkeypatch.setattr(historical_pairs.csv, "DictReader", forbidden_reader)
    with pytest.raises(
        historical_pairs.HistoricalEvidenceError, match="columns exceed"
    ):
        historical_pairs._csv_rows(text, registered_fields=columns, expected_rows=1)


def test_historical_source_column_preflight_preserves_quoted_commas() -> None:
    """Commas inside a quoted cell are not extra allocated CSV columns."""
    text = 'repetition,strategy_id\n0,"left,right"\n'
    assert historical_pairs._csv_rows(
        text,
        registered_fields=frozenset({"repetition", "strategy_id"}),
        expected_rows=1,
    ) == [{"repetition": "0", "strategy_id": "left,right"}]


class _ForgedHistoricalNumber:
    """A forged integer whose string projection mimics source decimal text."""

    def __str__(self) -> str:
        return "7"


@pytest.mark.parametrize("provider", ["set", "str", "int", "type"])
def test_historical_integer_rejects_mutated_numeric_admission_provider(
    monkeypatch: pytest.MonkeyPatch, provider: str
) -> None:
    """Original decimal source, not mutable module hooks, owns run counts."""
    if provider == "set":
        source: str = "-2"
        monkeypatch.setattr(
            historical_pairs, "set", lambda _value: set(), raising=False
        )
    elif provider == "str":
        source = "007"
        monkeypatch.setattr(
            historical_pairs, "str", lambda _value: source, raising=False
        )
    elif provider == "int":
        source = "007"
        monkeypatch.setattr(
            historical_pairs,
            "int",
            lambda _value: _ForgedHistoricalNumber(),
            raising=False,
        )
        monkeypatch.setattr(
            historical_pairs, "str", lambda _value: source, raising=False
        )
    else:
        class ForeignDigits(str):
            def __iter__(self) -> Iterator[str]:
                return iter("1")

        source = ForeignDigits("-1")
        native_type = type
        monkeypatch.setattr(
            historical_pairs,
            "type",
            lambda value: str if value is source else native_type(value),
            raising=False,
        )
    with pytest.raises(historical_pairs.HistoricalEvidenceError):
        historical_pairs._integer(source, "repetition")


@pytest.mark.parametrize("provider", ["set", "str", "int", "type"])
def test_historical_integer_preserves_valid_source_under_alias_mutation(
    monkeypatch: pytest.MonkeyPatch, provider: str
) -> None:
    """A valid numeric field survives late replacement of native aliases."""
    replacements: dict[str, object] = {
        "set": lambda _value: {"-"},
        "str": lambda _value: "forged",
        "int": lambda _value: 99,
        "type": lambda _value: object,
    }
    monkeypatch.setattr(
        historical_pairs, provider, replacements[provider], raising=False
    )
    assert historical_pairs._integer("12", "repetition") == 12


@pytest.mark.parametrize("replacement", [object(), RuntimeError])
@pytest.mark.parametrize(
    ("stage", "diagnostic"),
    [
        ("fail", "native historical rejection"),
        ("number", "invalid historical numeric field"),
        ("utf8", "strict UTF-8 text"),
        ("csv-reader", "malformed historical raw CSV: invalid source CSV"),
        ("csv-preflight", "column preflight failed"),
        ("json-writer", "JSON serializer failed: OSError"),
        ("source-hash", "source hash computation failed"),
        ("build", "historical paired source inconsistent: original failure"),
    ],
)
def test_historical_error_alias_preserves_native_rejection(
    monkeypatch: pytest.MonkeyPatch,
    replacement: object,
    stage: str,
    diagnostic: str,
) -> None:
    """Native retained-evidence errors keep their type and diagnostic."""
    original_error = historical_pairs.HistoricalEvidenceError
    fields = historical_pairs.REGISTERED_RAW_COLUMNS[
        "prefix_decomposition_measurement"
    ]
    with monkeypatch.context() as patched:
        patched.setattr(historical_pairs, "HistoricalEvidenceError", replacement)
        if stage == "csv-reader":
            def malformed(*_args: object, **_kwargs: object) -> None:
                raise csv.Error("invalid source CSV")
            patched.setattr(historical_pairs.csv, "DictReader", malformed)
        elif stage == "csv-preflight":
            def unavailable(*_args: object, **_kwargs: object) -> None:
                raise OSError("preflight unavailable")
            patched.setattr(
                historical_pairs.csv_admission, "within_column_limit", unavailable
            )
        elif stage == "json-writer":
            def failed_json(*_args: object, **_kwargs: object) -> None:
                raise OSError("writer unavailable")
            patched.setattr(historical_pairs.json, "dumps", failed_json)
        elif stage == "source-hash":
            patched.setattr(
                historical_pairs.evidence,
                "read_bounded_regular",
                lambda *_args, **_kwargs: b"source contents",
            )
            def unavailable_hash(_raw: bytes) -> None:
                raise OSError("hash unavailable")
            patched.setattr(historical_pairs, "sha256", unavailable_hash)
        elif stage == "build":
            def missing_run(*_args: object, **_kwargs: object) -> None:
                raise original_error("original failure")
            patched.setattr(historical_pairs, "_build_report", missing_run)
        with pytest.raises(original_error, match=diagnostic):
            if stage == "fail":
                historical_pairs._fail("native historical rejection")
            elif stage == "number":
                historical_pairs._integer("NaN", "cost")
            elif stage == "utf8":
                historical_pairs._admit_csv_text("\ud800")
            elif stage in ("csv-reader", "csv-preflight"):
                historical_pairs._csv_rows(
                    "repetition,strategy_id\n0,baseline\n",
                    registered_fields=fields,
                    expected_rows=1,
                )
            elif stage == "json-writer":
                historical_pairs._admitted_report_json({"status": "reported"})
            elif stage == "source-hash":
                historical_pairs._source(REPO, BASE + PREFIX)
            else:
                historical_pairs.build_report(REPO, BASE + PREFIX)


@pytest.mark.parametrize("replacement", [object(), RuntimeError])
def test_historical_error_alias_preserves_cli_native_detail(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    replacement: object,
) -> None:
    """CLI still reports the original bounded native importer error."""
    native_error = historical_pairs.HistoricalEvidenceError
    def failed_report(*_args: object, **_kwargs: object) -> None:
        raise native_error("exact retained source error")
    with monkeypatch.context() as patched:
        patched.setattr(historical_pairs, "HistoricalEvidenceError", replacement)
        patched.setattr(historical_pairs, "build_report", failed_report)
        patched.setattr(sys, "argv", ["historical-pairs", BASE + PREFIX])
        with pytest.raises(SystemExit, match="2"):
            historical_pairs.main()
    captured = capsys.readouterr()
    assert not captured.out
    assert "exact retained source error" in captured.err


@pytest.mark.parametrize("replacement", [object(), RuntimeError])
def test_historical_error_alias_preserves_valid_replay(
    monkeypatch: pytest.MonkeyPatch, replacement: object
) -> None:
    """Valid retained research evidence still imports under a late error alias."""
    expected = _result(REUSE)
    with monkeypatch.context() as patched:
        patched.setattr(historical_pairs, "HistoricalEvidenceError", replacement)
        assert _result(REUSE) == expected
