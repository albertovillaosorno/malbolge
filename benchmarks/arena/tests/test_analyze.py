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
#   - Arena comparison, failure retention, and admission regressions.
# - Must-Not:
#   - Claim synthetic fixture measurements as real performance.
# - Allows:
#   - Inputs: in-memory version-one synthetic study records.
#   - Outputs: assertions about deterministic reported-evidence analysis.
#   - Side effects: temporary CLI input during tests.
# - Split-When:
#   - A dedicated physical benchmark runner needs independent tests.
# - Merge-When:
#   - An owning arena test module replaces the current fixtures.
# - Summary:
#   - Tests exact cohorts, Pareto tradeoffs and fail-closed input.
# - Description:
#   - Covers schema and statistical semantics without a target backend.
# - Usage:
#   - python3.14 -B -m pytest benchmarks/arena/tests/test_analyze.py -q
# - Defaults:
#   - No candidate is considered verified without reported verifier evidence.
#

"""Synthetic, never performance-authoritative arena analysis regressions."""

# Test assertions are intentional (equivalent to tests/**/*.py Ruff policy).
# ruff: file-ignore[assert]

from __future__ import annotations

import copy
import json
import sys
from typing import Any
from typing import Never
from typing import TYPE_CHECKING
from typing import cast

import pytest

from benchmarks.arena import analyze

if TYPE_CHECKING:
    from pathlib import Path

STAGE = "ternary-ir"
CANDIDATE = "candidate"
BASELINE = "baseline"
FIRST_DIFFICULTY = 1
SECOND_DIFFICULTY = 2
SECOND_SEED = 4
FIRST_SEED = 3
PAIRED_TRIAL_COUNT = 2
TIME_DIMENSION = "time"
LARGE_INPUT_DIAGNOSTIC = "exceeds 16 MiB"
NON_FILE_DIAGNOSTIC = "regular file"
HASH_A = "a" * analyze.SHA256_HEX_LENGTH
HASH_B = "b" * analyze.SHA256_HEX_LENGTH
INTERVAL_PAIRS = 10
FAILED_PAIRS = 5
FAILURE_SEED_BOUND = 8
INDEPENDENT_NOTE = "Independent identically distributed"
INTERVAL_POLICY = "median_interval_policy"
INTERVALS_KEY = "median_confidence_intervals_95"
INTERVAL_KEY = "median_confidence_interval_95"
PAIRED_FAILURE_SEED_BOUND = 9
LOW_SIGN_SEED_BOUND = 7
HIGH_SIGN_SEED_BOUND = 11
DISCORDANT_HALVES = 6
NO_ADJUSTMENT = "none"
PAIRED_SIGN_TEST = "paired_sign_test"
VERIFICATION_ASYMMETRY_TEST = "verification_asymmetry_test"
HOLM_METHOD = "Holm-Bonferroni"
HOLM_FIELD = "p_holm_adjusted"
HOLM_ERROR = "requires --paired-exact-tests"
MULTI_HYPOTHESIS_COUNT = 4
SUCCESS_OBSERVED = 5
SUCCESS_ATTEMPTS = 10
SUCCESS_INTERVAL_POLICY_KEY = "verification_success_interval_policy"
SUCCESS_INTERVAL_KEY = "verification_success_probability_interval_95"
UTF8_QUESTION = "évidence"


def _observation(
    algorithm: str,
    difficulty: int,
    trial: int,
    *,
    outcome: str = analyze.VERIFIED,
) -> dict[str, Any]:
    verdict = {
        analyze.VERIFIED: analyze.ACCEPTED,
        analyze.VERIFIER_REJECTED: analyze.REJECTED,
    }.get(outcome, analyze.NOT_RUN)
    return {
        "algorithm": algorithm,
        "case": {
            "family": "arithmetic-dag",
            "version": 1,
            "difficulty": difficulty,
            "seed": trial + 3,
            "workload_sha256": (
                HASH_A if difficulty == FIRST_DIFFICULTY else HASH_B
            ),
        },
        "trial": 0,
        "outcome": outcome,
        "verifier": "independent-canonical-verifier",
        "verifier_verdict": verdict,
        "experiment_manifest": "algorithms/example/experiment.toml",
        "raw_sample": "algorithms/example/out/samples.csv",
        "metrics": (
            {"elapsed_ns": 10, "artifact_bytes": 40}
            if outcome == analyze.VERIFIED
            else {"elapsed_ns": 10}
        ),
    }


def _document() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "study": {
            "id": "synthetic-scaling-v1",
            "question": "Is candidate faster on identical work?",
            "hypothesis": "Candidate median verified time is lower.",
            "baseline": BASELINE,
            "rejection_observation": "Candidate does not improve the frontier.",
            "stage": STAGE,
            "target_profile": "malbolge-2026",
            "host": "synthetic-host",
            "toolchain": "synthetic-toolchain",
            "budget": {"time_ns": 10000, "memory_bytes": 65536},
            "objectives": ["elapsed_ns", "artifact_bytes"],
        },
        "observations": [
            _observation(BASELINE, FIRST_DIFFICULTY, 0),
            _observation(BASELINE, FIRST_DIFFICULTY, 1),
            _observation(CANDIDATE, FIRST_DIFFICULTY, 0),
            _observation(CANDIDATE, FIRST_DIFFICULTY, 1),
            _observation(BASELINE, SECOND_DIFFICULTY, 0),
            _observation(BASELINE, SECOND_DIFFICULTY, 1),
            _observation(CANDIDATE, SECOND_DIFFICULTY, 0),
            _observation(
                CANDIDATE,
                SECOND_DIFFICULTY,
                1,
                outcome=analyze.VERIFIER_REJECTED,
            ),
        ],
    }


def _run(document: dict[str, Any]) -> dict[str, Any]:
    return analyze.analyze(analyze.parse_document(json.dumps(document)))


def _point(report: dict[str, Any], algorithm: str, difficulty: int) -> dict:
    return next(
        row
        for row in report["capacity_curve"]
        if row["algorithm"] == algorithm and row["difficulty"] == difficulty
    )


def test_capacity_and_frontiers_preserve_success_tradeoff() -> None:
    """Conditional Pareto keeps fast/less-reliable candidate visible."""
    document = _document()
    for row in document["observations"]:
        if row["algorithm"] == BASELINE:
            row["metrics"] = {"elapsed_ns": 50, "artifact_bytes": 60}
        elif row["outcome"] == analyze.VERIFIED:
            row["metrics"] = {"elapsed_ns": 30, "artifact_bytes": 40}
    report = _run(document)
    assert report["stage"] == STAGE
    frontiers = report["pareto_frontiers"]
    assert len(frontiers) == SECOND_DIFFICULTY
    assert frontiers[0]["algorithms"] == [CANDIDATE]
    assert frontiers[1]["algorithms"] == [BASELINE, CANDIDATE]
    point = _point(report, CANDIDATE, SECOND_DIFFICULTY)
    assert point["success_fraction"] == [1, 2]
    assert point["outcomes"][analyze.VERIFIER_REJECTED] == 1
    assert point["medians"] == {
        "elapsed_ns": [30, 1],
        "artifact_bytes": [40, 1],
    }
    capacities = report["highest_observed_verified_difficulty"]
    assert [row["algorithm"] for row in capacities] == [BASELINE, CANDIDATE]
    assert all(
        row["highest_observed_verified_difficulty"] == SECOND_DIFFICULTY
        for row in capacities
    )


def test_failed_attempts_remain_but_do_not_enter_pareto() -> None:
    """Resource-exhausted attempts count against the reported success rate."""
    document = _document()
    for row in document["observations"]:
        if (
            row["algorithm"] == CANDIDATE
            and row["case"]["difficulty"] == SECOND_DIFFICULTY
        ):
            row["outcome"] = "resource_exhausted"
            row["verifier_verdict"] = analyze.NOT_RUN
            row["metrics"] = {"elapsed_ns": 90}
    report = _run(document)
    point = _point(report, CANDIDATE, SECOND_DIFFICULTY)
    assert point["success_fraction"] == [0, 2]
    assert point["medians"] == {
        "elapsed_ns": None,
        "artifact_bytes": None,
    }
    assert report["pareto_frontiers"][1][
        "excluded_without_verified_solution"
    ] == [CANDIDATE]
    capacity = report["highest_observed_verified_difficulty"]
    assert (
        capacity[1]["highest_observed_verified_difficulty"] == FIRST_DIFFICULTY
    )


def test_tradeoffs_are_incomparable() -> None:
    """A smaller artifact need not dominate a faster competitor."""
    document = _document()
    for row in document["observations"]:
        if row["algorithm"] == CANDIDATE:
            row["metrics"]["elapsed_ns"] = 8
            if row["outcome"] == analyze.VERIFIED:
                row["metrics"]["artifact_bytes"] = 90
    report = _run(document)
    assert report["pareto_frontiers"][0]["algorithms"] == [BASELINE, CANDIDATE]


def test_even_median_remains_exact_beyond_float_precision() -> None:
    """Large integer median comparisons cannot collapse into float ties."""
    document = _document()
    huge = 2**64
    for row in document["observations"]:
        if row["algorithm"] == BASELINE:
            row["metrics"]["artifact_bytes"] = huge + 2
        elif row["outcome"] == analyze.VERIFIED:
            row["metrics"]["artifact_bytes"] = huge + 1
    report = _run(document)
    assert report["pareto_frontiers"][0]["algorithms"] == [CANDIDATE]
    assert _point(report, CANDIDATE, FIRST_DIFFICULTY)["medians"][
        "artifact_bytes"
    ] == [huge + 1, 1]
    document["observations"][0]["metrics"]["artifact_bytes"] = huge + 3
    report = _run(document)
    assert _point(report, BASELINE, FIRST_DIFFICULTY)["medians"][
        "artifact_bytes"
    ] == [2 * huge + 5, 2]


def test_observation_order_does_not_affect_report() -> None:
    """Input order is not a hidden scoring dimension."""
    document = _document()
    expected = _run(document)
    document["observations"].reverse()
    assert expected == _run(document)


@pytest.mark.parametrize("field", ["seed", "workload_sha256", "trial"])
def test_unmatched_trial_cohorts_fail_closed(field: str) -> None:
    """Algorithms cannot compare different instances or replicate numbers."""
    document = _document()
    row = document["observations"][2]
    changes = {
        "seed": (row["case"], 91),
        "workload_sha256": (row["case"], "c" * analyze.SHA256_HEX_LENGTH),
        "trial": (row, 7),
    }
    mapping, value = changes[field]
    mapping[field] = value
    with pytest.raises(analyze.ArenaError, match="unmatched trial/workload"):
        _run(document)


@pytest.mark.parametrize("identity", ["version", "difficulty"])
@pytest.mark.parametrize(
    ("mismatch", "diagnostic"),
    [
        ("workload", "unmatched trial/workload cohort"),
        ("verifier", "unmatched verifier cohort"),
        ("baseline", "missing declared baseline"),
        ("no-candidate", "no comparison algorithm"),
    ],
)
def test_extreme_native_cohort_identity_cannot_break_error_formatting(
    identity: str,
    mismatch: str,
    diagnostic: str,
) -> None:
    """Failed direct comparisons retain typed errors for enormous identities."""
    document = _document()
    if identity == "difficulty":
        document["observations"] = [
            row
            for row in document["observations"]
            if row["case"]["difficulty"] == FIRST_DIFFICULTY
        ]
    for row in document["observations"]:
        row["case"][identity] = 1 << 50000
    if mismatch == "workload":
        document["observations"][2]["case"]["seed"] = 91
    elif mismatch == "verifier":
        document["observations"][2]["verifier"] = "different-oracle"
    elif mismatch == "baseline":
        document["study"]["baseline"] = "omitted-baseline"
    else:
        document["observations"] = [
            row for row in document["observations"]
            if row["algorithm"] == BASELINE
        ]
    with pytest.raises(analyze.ArenaError, match=diagnostic):
        analyze.analyze(document)


def test_exact_direct_analysis_preserves_large_matched_case_version() -> None:
    """A large valid numeric identity need not lose integer precision."""
    document = _document()
    for row in document["observations"]:
        row["case"]["version"] = 1 << 50000
    report = analyze.analyze(document)
    assert report["capacity_curve"][0]["version"] == 1 << 50000


def test_missing_declared_baseline_rejected() -> None:
    """No study can silently report a candidate-only comparative frontier."""
    document = _document()
    document["study"]["baseline"] = "omitted-baseline"
    with pytest.raises(analyze.ArenaError, match="missing declared baseline"):
        _run(document)


def test_duplicate_trial_and_boolean_integer_fail_closed() -> None:
    """Duplicate, boolean or zero-valued budget identities are malformed."""
    document = _document()
    document["observations"].append(copy.deepcopy(document["observations"][0]))
    with pytest.raises(analyze.ArenaError, match="duplicate"):
        _run(document)
    document = _document()
    document["observations"][0]["metrics"]["elapsed_ns"] = True
    with pytest.raises(analyze.ArenaError, match="integer"):
        _run(document)
    document = _document()
    document["study"]["budget"]["time_ns"] = 0
    with pytest.raises(analyze.ArenaError, match="positive"):
        _run(document)


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("verifier_verdict", analyze.NOT_RUN),
        ("verifier", CANDIDATE),
        ("outcome", "unrecognized"),
        ("outcome", []),
    ],
)
def test_invalid_or_self_certifying_verdict_rejected(
    key: str,
    value: object,
) -> None:
    """A producer cannot self-admit a successful reported candidate."""
    document = _document()
    document["observations"][2][key] = value
    with pytest.raises(analyze.ArenaError, match=r"verifier|outcome"):
        _run(document)


@pytest.mark.parametrize("field", ["missing", "unknown", "relative", "hash"])
def test_missing_cost_unknown_metric_and_invalid_evidence(field: str) -> None:
    """A claimed success must carry exact declared costs and evidence paths."""
    document = _document()
    row = document["observations"][0]
    changes = {
        "missing": lambda: row["metrics"].pop("artifact_bytes"),
        "unknown": lambda: row["metrics"].update({"energy_joules": 3}),
        "relative": lambda: row.update({"raw_sample": "../untrusted.csv"}),
        "hash": lambda: row["case"].update({"workload_sha256": HASH_A.upper()}),
    }
    _ = changes[field]()
    with pytest.raises(
        analyze.ArenaError, match=r"metric|path|SHA-256|objective"
    ):
        _run(document)


@pytest.mark.parametrize(
    "text",
    [
        '{"id": 1, "id": 2}',
        '{"a": NaN}',
        '{"a": Infinity}',
    ],
)
def test_duplicate_keys_and_nonfinite_numbers_fail_closed(text: str) -> None:
    """JSON syntax must not obscure a measurement or study authority."""
    with pytest.raises(analyze.ArenaError, match=r"duplicate|nonfinite"):
        analyze.parse_document(text)


@pytest.mark.parametrize(
    "fault_type",
    [
        analyze.ArenaError,
        ValueError,
        TypeError,
        RecursionError,
        RuntimeError,
        IndexError,
        OverflowError,
        Exception,
    ],
)
def test_direct_json_parser_types_foreign_exception_without_formatting(
    monkeypatch: pytest.MonkeyPatch,
    fault_type: type[Exception],
) -> None:
    """Foreign decoder faults cannot replace evidence rejection via __str__."""
    source = json.dumps(_document())

    def hostile_str(self: Exception) -> str:
        del self
        raise AssertionError("foreign JSON exception formatter executed")

    hostile_type = type("ForeignJSONFault", (fault_type,), {"__str__": hostile_str})
    fault = hostile_type("untrusted decoder detail")

    def broken_loader(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise fault

    monkeypatch.setattr(analyze.json, "loads", broken_loader)
    with pytest.raises(analyze.ArenaError, match="invalid arena JSON") as caught:
        analyze.parse_document(source)
    assert caught.value.__cause__ is fault


def test_direct_json_syntax_error_retains_native_decoder_diagnostic() -> None:
    """Exact stdlib parser errors keep useful ordinary syntax positions."""
    with pytest.raises(analyze.ArenaError, match="Extra data") as caught:
        analyze.parse_document("{} trailing")
    assert type(caught.value.__cause__) is json.JSONDecodeError


def test_direct_json_duplicate_field_preserves_project_rejection() -> None:
    """Schema hooks do not rewrap the existing typed rejection as a parser fault."""
    with pytest.raises(analyze.ArenaError, match="duplicate JSON field") as caught:
        analyze.parse_document('{"a":1,"a":2}')
    assert caught.value.__cause__ is None


@pytest.mark.parametrize(
    "foreign",
    [
        b"{}",
        bytearray(b"{}"),
        None,
        {},
        1,
    ],
)
def test_direct_json_parser_requires_exact_text(foreign: object) -> None:
    """A direct parser must not silently decode byte-like foreign records."""
    with pytest.raises(analyze.ArenaError, match="exact string"):
        _ = analyze.parse_document(cast("str", foreign))


@pytest.mark.parametrize(
    "oversized",
    [
        " " * (analyze.MAX_INPUT_BYTES + 1),
        "é" * (analyze.MAX_INPUT_BYTES // 2 + 1),
    ],
)
def test_direct_json_parser_rejects_over_budget_before_decode(
    monkeypatch: pytest.MonkeyPatch,
    oversized: str,
) -> None:
    """Byte budget applies before JSON parser allocation or deep recursion."""
    called = False

    def forbidden(*args: object, **kwargs: object) -> None:
        nonlocal called
        _ = (args, kwargs)
        called = True
        message = "overlong direct JSON reached decoder"
        raise AssertionError(message)

    monkeypatch.setattr(analyze.json, "loads", forbidden)
    with pytest.raises(analyze.ArenaError, match=LARGE_INPUT_DIAGNOSTIC):
        _ = analyze.parse_document(oversized)
    assert not called


def test_direct_json_parser_rejects_unencodable_text() -> None:
    """Lone host surrogate characters cannot become a UTF-8 study wire."""
    with pytest.raises(analyze.ArenaError, match="UTF-8") as rejection:
        _ = analyze.parse_document("\ud800")
    assert isinstance(rejection.value.__cause__, UnicodeEncodeError)


@pytest.mark.parametrize(
    ("path", "invalid_value"),
    [
        (("study", "id"), "escaped-\ud800"),
        (("study", "question"), "escaped-\udfff"),
        (("observations", 0, "algorithm"), "escaped-\ud800"),
        (("observations", 0, "verifier"), "escaped-\udfff"),
        (("observations", 0, "case", "family"), "escaped-\ud800"),
        (("observations", 0, "raw_sample"), "algorithms/\udfff/raw.csv"),
    ],
)
def test_escaped_unpaired_surrogates_never_enter_arena_identity(
    path: tuple[str | int, ...],
    invalid_value: str,
) -> None:
    """A JSON escape cannot launder a non-Unicode-scalar identity or path."""
    document = _document()
    target: Any = document
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = invalid_value
    serialized = json.dumps(document)
    with pytest.raises(analyze.ArenaError, match="surrogate"):
        _ = analyze.parse_document(serialized)
    with pytest.raises(analyze.ArenaError, match="surrogate"):
        _ = analyze.admit_document(document)


def test_escaped_valid_astral_unicode_is_not_rejected() -> None:
    """Paired UTF-16 escapes that decode to one scalar remain ordinary text."""
    identity = "astral-🌌"
    raw_path = "algorithms/🌌/raw.csv"
    document = _document()
    document["study"]["id"] = identity
    document["observations"][0]["raw_sample"] = raw_path
    admitted = analyze.parse_document(json.dumps(document))
    assert admitted["study"]["id"] == identity
    assert admitted["observations"][0]["raw_sample"] == raw_path


def test_direct_json_parser_admits_exact_utf8_byte_ceiling() -> None:
    """The direct parser accepts the same full-size ordinary-file budget."""
    document = _document()
    document["study"]["question"] = UTF8_QUESTION
    original = json.dumps(document, ensure_ascii=False)
    admitted = analyze.parse_document(
        original
        + " " * (analyze.MAX_INPUT_BYTES - len(original.encode("utf-8")))
    )
    assert admitted["study"]["question"] == UTF8_QUESTION


def test_cli_prints_json_and_rejects_invalid_input(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """CLI output is machine-readable and failures publish no partial JSON."""
    path = tmp_path / "samples.json"
    _ = path.write_text(json.dumps(_document()), encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["arena", str(path)])
    assert analyze.main() == 0
    output = capsys.readouterr()
    assert json.loads(output.out) == _run(_document())
    _ = path.write_text('{"schema_version": false}', encoding="utf-8")
    with pytest.raises(SystemExit, match="2"):
        analyze.main()
    failed = capsys.readouterr()
    assert not failed.out
    assert failed.err.startswith("arena:")


@pytest.mark.parametrize("field", ["outcome", "verifier_verdict"])
def test_unhashable_claimed_verdict_is_typed_error(field: str) -> None:
    """Untrusted JSON arrays must not cause an untyped host exception."""
    document = _document()
    document["observations"][0][field] = []
    with pytest.raises(analyze.ArenaError, match=r"verdict|outcome"):
        _run(document)


@pytest.mark.parametrize("dimension", ["time", "memory"])
def test_over_budget_verified_evidence_rejected(dimension: str) -> None:
    """A claimed verified run cannot exceed its stated fixed budget."""
    document = _document()
    metrics = document["observations"][0]["metrics"]
    if dimension == TIME_DIMENSION:
        metrics["elapsed_ns"] = document["study"]["budget"]["time_ns"] + 1
    else:
        metrics["peak_rss_bytes"] = (
            document["study"]["budget"]["memory_bytes"] + 1
        )
    with pytest.raises(analyze.ArenaError, match=r"exceeds study budget"):
        _run(document)


def test_single_algorithm_is_not_a_multi_algorithm_comparison() -> None:
    """A declared baseline cannot create a Pareto frontier by itself."""
    document = _document()
    document["observations"] = [
        item
        for item in document["observations"]
        if item["algorithm"] == BASELINE
    ]
    with pytest.raises(analyze.ArenaError, match="no comparison algorithm"):
        _run(document)


@pytest.mark.parametrize(
    "objectives",
    [
        ["energy_joules"],
        [3],
        [{"name": "elapsed_ns"}],
        ["elapsed_ns", "elapsed_ns"],
        [],
    ],
)
def test_unsupported_objective_fails_closed(objectives: list[object]) -> None:
    """Unregistered and unhashable objectives cannot become Pareto authority."""
    document = _document()
    document["study"]["objectives"] = objectives
    with pytest.raises(analyze.ArenaError, match=r"study\.objectives"):
        _run(document)


def test_cli_rejects_large_and_linked_input(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """External inputs cannot redirect or force unbounded memory reads."""
    original = tmp_path / "input.json"
    with original.open("wb") as stream:
        _ = stream.seek(analyze.MAX_INPUT_BYTES)
        _ = stream.write(b"a")
    monkeypatch.setattr(sys, "argv", ["arena", str(original)])
    with pytest.raises(SystemExit, match="2"):
        analyze.main()
    first = capsys.readouterr()
    assert LARGE_INPUT_DIAGNOSTIC in first.err
    assert not first.out
    linked = tmp_path / "linked.json"
    try:
        linked.symlink_to(original)
    except (NotImplementedError, OSError) as error:
        pytest.skip(f"host has no symlink support: {error}")
    monkeypatch.setattr(sys, "argv", ["arena", str(linked)])
    with pytest.raises(SystemExit, match="2"):
        analyze.main()
    second = capsys.readouterr()
    assert NON_FILE_DIAGNOSTIC in second.err
    assert not second.out


def test_exact_even_sample_dispersion_and_failure_inclusive_elapsed() -> None:
    """All-attempt time exposes failure cost ignored by successful medians."""
    document = _document()
    for row in document["observations"]:
        if row["algorithm"] == BASELINE and row["case"]["difficulty"] == 1:
            row["metrics"]["elapsed_ns"] = 10 + row["case"]["seed"] - 3
    candidate = next(
        row
        for row in document["observations"]
        if row["algorithm"] == CANDIDATE
        and row["case"]["difficulty"] == SECOND_DIFFICULTY
        and row["outcome"] != analyze.VERIFIED
    )
    candidate["metrics"]["elapsed_ns"] = 110
    report = _run(document)
    baseline = _point(report, BASELINE, FIRST_DIFFICULTY)
    assert baseline["medians"]["elapsed_ns"] == [21, 2]
    assert baseline["median_absolute_deviation"]["elapsed_ns"] == [1, 2]
    assert baseline["successful_range"]["elapsed_ns"] == [10, 11]
    point = _point(report, CANDIDATE, SECOND_DIFFICULTY)
    assert point["medians"]["elapsed_ns"] == [10, 1]
    assert point["median_absolute_deviation"]["elapsed_ns"] == [0, 1]
    assert point["successful_range"]["elapsed_ns"] == [10, 10]
    assert point["all_attempt_elapsed_ns"] == {
        "median": [60, 1],
        "median_absolute_deviation": [50, 1],
        "range": [10, 110],
    }


def test_zero_success_still_reports_all_attempt_dispersion() -> None:
    """Null conditional statistics never discard unsuccessful elapsed time."""
    document = _document()
    failures = [
        row
        for row in document["observations"]
        if row["algorithm"] == CANDIDATE
        and row["case"]["difficulty"] == SECOND_DIFFICULTY
    ]
    for index, row in enumerate(failures):
        row["outcome"] = "resource_exhausted"
        row["verifier_verdict"] = analyze.NOT_RUN
        row["metrics"] = {"elapsed_ns": 90 + index * 10}
    point = _point(_run(document), CANDIDATE, SECOND_DIFFICULTY)
    assert point["medians"]["elapsed_ns"] is None
    assert point["median_absolute_deviation"]["elapsed_ns"] is None
    assert point["successful_range"]["elapsed_ns"] is None
    assert point["all_attempt_elapsed_ns"] == {
        "median": [95, 1],
        "median_absolute_deviation": [5, 1],
        "range": [90, 100],
    }


def test_exact_dispersion_does_not_round_large_costs() -> None:
    """A half-unit MAD remains visible above the IEEE-754 integer range."""
    document = _document()
    huge = 2**80
    for row in document["observations"]:
        if row["algorithm"] == BASELINE:
            row["metrics"]["artifact_bytes"] = huge + row["case"]["seed"] - 3
    point = _point(_run(document), BASELINE, FIRST_DIFFICULTY)
    assert point["medians"]["artifact_bytes"] == [2 * huge + 1, 2]
    assert point["median_absolute_deviation"]["artifact_bytes"] == [1, 2]
    assert point["successful_range"]["artifact_bytes"] == [huge, huge + 1]


def test_oracle_identity_drift_rejects_matched_algorithm_comparison() -> None:
    """Matching inputs are not comparable under different verifier versions."""
    document = _document()
    document["observations"][2]["verifier"] = "different-oracle"
    with pytest.raises(analyze.ArenaError, match="verifier cohort"):
        _run(document)


def test_distinct_per_instance_oracles_are_allowed_when_matched() -> None:
    """One verifier per case is required, not one for the whole difficulty."""
    document = _document()
    for row in document["observations"]:
        if row["case"]["seed"] == SECOND_SEED:
            row["verifier"] = "oracle-for-second-instance"
    report = _run(document)
    assert report["pareto_frontiers"][0]["algorithms"] == [BASELINE, CANDIDATE]


def test_paired_comparison_retains_wins_losses_and_time_differences() -> None:
    """Matched observations expose paired costs obscured by simple medians."""
    document = _document()
    for row in document["observations"]:
        if row["algorithm"] == CANDIDATE and row["case"]["difficulty"] == 1:
            row["metrics"]["elapsed_ns"] = (
                8 if row["case"]["seed"] == FIRST_SEED else 15
            )
    report = _run(document)
    pairs = report["paired_baseline_comparisons"]
    assert len(pairs) == PAIRED_TRIAL_COUNT
    easy = pairs[0]
    assert easy["baseline"] == BASELINE
    assert easy["algorithm"] == CANDIDATE
    assert easy["paired_trials"] == PAIRED_TRIAL_COUNT
    assert easy["outcomes"] == {
        "both_verified": 2,
        "baseline_only_verified": 0,
        "candidate_only_verified": 0,
        "neither_verified": 0,
    }
    assert easy["cost_differences"]["elapsed_ns"] == {
        "candidate_lower": 1,
        "candidate_equal": 0,
        "candidate_higher": 1,
        "median_candidate_minus_baseline": [3, 2],
    }
    assert pairs[1]["outcomes"]["baseline_only_verified"] == 1
    assert pairs[1]["outcomes"]["both_verified"] == 1


def test_unpaired_failures_do_not_create_fake_cost_differences() -> None:
    """Paired metrics stay null when no trial was verified by both sides."""
    document = _document()
    for row in document["observations"]:
        if (
            row["algorithm"] == BASELINE
            and row["case"]["difficulty"] == SECOND_DIFFICULTY
            and row["case"]["seed"] == FIRST_SEED
        ):
            row["outcome"] = "no_solution"
            row["verifier_verdict"] = analyze.NOT_RUN
            row["metrics"] = {"elapsed_ns": 75}
    report = _run(document)
    hard = report["paired_baseline_comparisons"][1]
    assert hard["outcomes"] == {
        "both_verified": 0,
        "baseline_only_verified": 1,
        "candidate_only_verified": 1,
        "neither_verified": 0,
    }
    assert hard["cost_differences"]["elapsed_ns"] == {
        "candidate_lower": 0,
        "candidate_equal": 0,
        "candidate_higher": 0,
        "median_candidate_minus_baseline": None,
    }


def test_pairing_keeps_neither_verified_trials_in_outcome_population() -> None:
    """A failed pair is not dropped from the denominator of comparisons."""
    document = _document()
    for row in document["observations"]:
        if (
            row["case"]["difficulty"] == SECOND_DIFFICULTY
            and row["case"]["seed"] == SECOND_SEED
        ):
            row["outcome"] = "resource_exhausted"
            row["verifier_verdict"] = analyze.NOT_RUN
            row["metrics"] = {"elapsed_ns": 75}
    paired = _run(document)["paired_baseline_comparisons"][1]
    assert paired["outcomes"]["both_verified"] == 1
    assert paired["outcomes"]["neither_verified"] == 1
    assert paired["paired_trials"] == PAIRED_TRIAL_COUNT
    assert paired["cost_differences"]["artifact_bytes"][
        "median_candidate_minus_baseline"
    ] == [0, 1]


def test_multiple_candidates_are_compared_to_same_declared_baseline() -> None:
    """Adding one candidate never changes the reference for earlier results."""
    document = _document()
    extra = [
        copy.deepcopy(row)
        for row in document["observations"]
        if row["algorithm"] == CANDIDATE
    ]
    for row in extra:
        row["algorithm"] = "additional-algorithm"
        row["metrics"]["elapsed_ns"] = 9
    document["observations"].extend(extra)
    report = _run(document)
    paired = report["paired_baseline_comparisons"]
    assert len(paired) == 2 * PAIRED_TRIAL_COUNT
    assert all(pair["baseline"] == BASELINE for pair in paired)
    assert [pair["algorithm"] for pair in paired[:2]] == [
        "additional-algorithm",
        CANDIDATE,
    ]
    assert [pair["algorithm"] for pair in paired[2:]] == [
        "additional-algorithm",
        CANDIDATE,
    ]


def _repeated_success_study(sample_count: int) -> dict[str, Any]:
    """Build independent-label synthetic pairs for statistical shape tests.

    Returns:
        Report-only samples; no physical independence or timing is asserted.

    """
    document = _document()
    rows = []
    for trial in range(sample_count):
        for algorithm in (BASELINE, CANDIDATE):
            row = _observation(algorithm, FIRST_DIFFICULTY, trial)
            row["metrics"]["elapsed_ns"] = (
                100 + trial if algorithm == BASELINE else 90 + trial
            )
            rows.append(row)
    document["observations"] = rows
    return document


def _interval_report(document: dict[str, Any]) -> dict[str, Any]:
    admitted = analyze.parse_document(json.dumps(document))
    return analyze.analyze(admitted, median_intervals_95=True)


def test_opt_in_median_intervals_report_exact_ranks_and_paired_deltas() -> None:
    """Exact coverage extends descriptive data without changing its frontier."""
    document = _repeated_success_study(10)
    base_report = _run(document)
    report = _interval_report(document)
    assert report["pareto_frontiers"] == base_report["pareto_frontiers"]
    assert (
        report["highest_observed_verified_difficulty"]
        == (base_report["highest_observed_verified_difficulty"])
    )
    baseline = _point(report, BASELINE, FIRST_DIFFICULTY)
    candidate = _point(report, CANDIDATE, FIRST_DIFFICULTY)
    assert baseline["median_confidence_intervals_95"]["elapsed_ns"] == {
        "lower": 101,
        "upper": 108,
        "coverage": [501, 512],
        "sample_count": 10,
    }
    assert candidate["median_confidence_intervals_95"]["elapsed_ns"] == {
        "lower": 91,
        "upper": 98,
        "coverage": [501, 512],
        "sample_count": 10,
    }
    assert (
        candidate["all_attempt_elapsed_ns"]["median_confidence_interval_95"][
            "sample_count"
        ]
        == INTERVAL_PAIRS
    )
    pair = report["paired_baseline_comparisons"][0]
    assert pair["cost_differences"]["elapsed_ns"][
        "median_confidence_interval_95"
    ] == {
        "lower": -10,
        "upper": -10,
        "coverage": [501, 512],
        "sample_count": 10,
    }
    policy = report["median_interval_policy"]
    assert policy["requested_confidence"] == [19, 20]
    assert not policy["pareto_uses_intervals"]
    assert INDEPENDENT_NOTE in policy["assumptions"]


def test_failed_pairs_have_conditional_null_but_all_attempt_interval() -> None:
    """Failed results never create imaginary successful costs or paired wins."""
    document = _repeated_success_study(10)
    for row in document["observations"]:
        if (
            row["algorithm"] == CANDIDATE
            and row["case"]["seed"] < FAILURE_SEED_BOUND
        ):
            row["outcome"] = "resource_exhausted"
            row["verifier_verdict"] = analyze.NOT_RUN
            row["metrics"] = {"elapsed_ns": 90}
    report = _interval_report(document)
    point = _point(report, CANDIDATE, FIRST_DIFFICULTY)
    assert point["verified"] == FAILED_PAIRS
    assert point["median_confidence_intervals_95"]["elapsed_ns"] is None
    assert point["all_attempt_elapsed_ns"]["median_confidence_interval_95"]
    comparison = report["paired_baseline_comparisons"][0]
    assert comparison["outcomes"]["both_verified"] == FAILED_PAIRS
    assert (
        comparison["cost_differences"]["elapsed_ns"][
            "median_confidence_interval_95"
        ]
        is None
    )
    assert comparison["cost_differences"]["elapsed_ns"][
        "median_candidate_minus_baseline"
    ] == [-10, 1]


def test_opt_in_statistical_shape_order_invariant_and_default_unchanged() -> (
    None
):
    """No flag means exact legacy JSON; row shuffling changes no intervals."""
    document = _repeated_success_study(10)
    without = _run(document)
    assert INTERVAL_POLICY not in without
    for point in without["capacity_curve"]:
        assert INTERVALS_KEY not in point
        assert INTERVAL_KEY not in point["all_attempt_elapsed_ns"]
    for comparison in without["paired_baseline_comparisons"]:
        for metric in comparison["cost_differences"].values():
            assert INTERVAL_KEY not in metric
    expected = _interval_report(document)
    document["observations"].reverse()
    assert _run(document) == without
    assert _interval_report(document) == expected


def test_cli_opt_in_intervals_and_default_json_compatibility(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Statistical uncertainty is opt-in and both CLI routes are stable."""
    document = _repeated_success_study(10)
    path = tmp_path / "samples.json"
    _ = path.write_text(json.dumps(document), encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["arena", str(path)])
    assert analyze.main() == 0
    assert json.loads(capsys.readouterr().out) == _run(document)
    monkeypatch.setattr(
        sys,
        "argv",
        ["arena", str(path), "--median-intervals-95"],
    )
    assert analyze.main() == 0
    assert json.loads(capsys.readouterr().out) == _interval_report(document)


def _paired_exact_report(document: dict[str, Any]) -> dict[str, Any]:
    admitted = analyze.parse_document(json.dumps(document))
    return analyze.analyze(admitted, paired_exact_tests_enabled=True)


def test_paired_exact_cost_signs_are_distinct_from_outcome_asymmetry() -> None:
    """All pairs verified gives no McNemar test but a cost sign test."""
    document = _repeated_success_study(12)
    legacy = _run(document)
    report = _paired_exact_report(document)
    assert report["pareto_frontiers"] == legacy["pareto_frontiers"]
    comparison = report["paired_baseline_comparisons"][0]
    assert comparison["verification_asymmetry_test"] is None
    assert comparison["cost_differences"]["elapsed_ns"]["paired_sign_test"] == {
        "discordant_pairs": 12,
        "p_two_sided": [1, 2048],
    }
    assert (
        comparison["cost_differences"]["artifact_bytes"]["paired_sign_test"]
        is None
    )
    policy = report["paired_exact_test_policy"]
    assert policy["multiple_testing_adjustment"] == NO_ADJUSTMENT
    assert not policy["pareto_uses_tests"]


def test_paired_exact_tests_retain_failures_without_fake_cost_wins() -> None:
    """Six candidate failures yield separate exact outcome and cost tests."""
    document = _repeated_success_study(12)
    for row in document["observations"]:
        if (
            row["algorithm"] == CANDIDATE
            and row["case"]["seed"] < PAIRED_FAILURE_SEED_BOUND
        ):
            row["outcome"] = "resource_exhausted"
            row["verifier_verdict"] = analyze.NOT_RUN
            row["metrics"] = {"elapsed_ns": 90}
    report = _paired_exact_report(document)
    comparison = report["paired_baseline_comparisons"][0]
    assert comparison["outcomes"]["baseline_only_verified"] == DISCORDANT_HALVES
    assert comparison["outcomes"]["both_verified"] == DISCORDANT_HALVES
    assert comparison["verification_asymmetry_test"] == {
        "discordant_pairs": 6,
        "p_two_sided": [1, 32],
    }
    assert comparison["cost_differences"]["elapsed_ns"]["paired_sign_test"] == {
        "discordant_pairs": 6,
        "p_two_sided": [1, 32],
    }


def test_disjoint_verified_arms_have_no_cost_sign_evidence() -> None:
    """Opposite successful arms are balanced but have no shared cost sample."""
    document = _repeated_success_study(12)
    for row in document["observations"]:
        is_baseline = row["algorithm"] == BASELINE
        first_half = row["case"]["seed"] < PAIRED_FAILURE_SEED_BOUND
        if is_baseline != first_half:
            row["outcome"] = "no_solution"
            row["verifier_verdict"] = analyze.NOT_RUN
            row["metrics"] = {"elapsed_ns": 90}
    report = _paired_exact_report(document)
    comparison = report["paired_baseline_comparisons"][0]
    assert comparison["outcomes"]["both_verified"] == 0
    assert comparison["outcomes"]["baseline_only_verified"] == DISCORDANT_HALVES
    assert (
        comparison["outcomes"]["candidate_only_verified"] == DISCORDANT_HALVES
    )
    assert comparison["verification_asymmetry_test"] == {
        "discordant_pairs": 12,
        "p_two_sided": [1, 1],
    }
    assert (
        comparison["cost_differences"]["elapsed_ns"]["paired_sign_test"] is None
    )
    assert (
        comparison["cost_differences"]["elapsed_ns"][
            "median_candidate_minus_baseline"
        ]
        is None
    )


def test_paired_cost_sign_test_ignores_exact_cost_ties() -> None:
    """Four wins per arm plus four ties use only eight nontied pairs."""
    document = _repeated_success_study(12)
    for row in document["observations"]:
        if row["algorithm"] == CANDIDATE:
            seed = row["case"]["seed"]
            original = 100 + seed - 3
            delta = (
                -3
                if seed < LOW_SIGN_SEED_BOUND
                else (3 if seed < HIGH_SIGN_SEED_BOUND else 0)
            )
            row["metrics"]["elapsed_ns"] = original + delta
    report = _paired_exact_report(document)
    comparison = report["paired_baseline_comparisons"][0]
    assert comparison["cost_differences"]["elapsed_ns"]["paired_sign_test"] == {
        "discordant_pairs": 8,
        "p_two_sided": [1, 1],
    }


def test_paired_exact_opt_in_keeps_default_and_order_stable() -> None:
    """Both inferential tools compose without affecting descriptive ranking."""
    document = _repeated_success_study(12)
    default = _run(document)
    for pair in default["paired_baseline_comparisons"]:
        assert VERIFICATION_ASYMMETRY_TEST not in pair
        for cost in pair["cost_differences"].values():
            assert PAIRED_SIGN_TEST not in cost
    admitted = analyze.parse_document(json.dumps(document))
    combined = analyze.analyze(
        admitted,
        median_intervals_95=True,
        paired_exact_tests_enabled=True,
    )
    assert combined["pareto_frontiers"] == default["pareto_frontiers"]
    assert combined["capacity_curve"][0]["median_confidence_intervals_95"]
    assert combined["paired_baseline_comparisons"][0]["cost_differences"][
        "elapsed_ns"
    ]["paired_sign_test"]
    document["observations"].reverse()
    assert _run(document) == default
    assert _paired_exact_report(document) == _paired_exact_report({
        **document,
        "observations": list(reversed(document["observations"])),
    })


def test_standalone_cli_accepts_paired_exact_test_option(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Operator output contains the optional exact test only when requested."""
    document = _repeated_success_study(12)
    path = tmp_path / "study.json"
    _ = path.write_text(json.dumps(document), encoding="utf-8")
    monkeypatch.setattr(
        sys, "argv", ["arena", str(path), "--paired-exact-tests"]
    )
    assert analyze.main() == 0
    report = json.loads(capsys.readouterr().out)
    assert report == _paired_exact_report(document)


def _adjusted_paired_report(document: dict[str, Any]) -> dict[str, Any]:
    admitted = analyze.parse_document(json.dumps(document))
    return analyze.analyze(
        admitted,
        paired_exact_tests_enabled=True,
        adjust_paired_tests=True,
    )


def test_holm_correction_applies_to_all_available_tests_in_one_study() -> None:
    """Even simple single-cohort costs require family-wise multiplicity."""
    document = _repeated_success_study(12)
    ordinary = _paired_exact_report(document)
    adjusted = _adjusted_paired_report(document)
    assert adjusted["pareto_frontiers"] == ordinary["pareto_frontiers"]
    policy = adjusted["paired_exact_test_policy"]
    assert policy["multiple_testing_adjustment"] == HOLM_METHOD
    assert policy["adjustment_family_size"] == 1
    assert not policy["adjusted_p_values_are_significance_decisions"]
    comparison = adjusted["paired_baseline_comparisons"][0]
    cost = comparison["cost_differences"]["elapsed_ns"]["paired_sign_test"]
    assert cost["p_two_sided"] == [1, 2048]
    assert cost["p_holm_adjusted"] == [1, 2048]
    assert comparison["verification_asymmetry_test"] is None
    assert (
        comparison["cost_differences"]["artifact_bytes"]["paired_sign_test"]
        is None
    )
    assert (
        HOLM_FIELD
        not in ordinary["paired_baseline_comparisons"][0]["cost_differences"][
            "elapsed_ns"
        ]["paired_sign_test"]
    )


def _two_difficulty_cost_study() -> dict[str, Any]:
    document = _repeated_success_study(12)
    new_rows = []
    for row in document["observations"]:
        other = copy.deepcopy(row)
        other["case"]["difficulty"] = SECOND_DIFFICULTY
        other["case"]["workload_sha256"] = HASH_B
        new_rows.append(other)
    document["observations"].extend(new_rows)
    for row in document["observations"]:
        if row["algorithm"] == CANDIDATE:
            row["metrics"]["artifact_bytes"] = 30
    return document


def test_holm_correction_spans_difficulty_levels_and_cost_objectives() -> None:
    """Global family size is not silently reset per cohort or cost metric."""
    adjusted = _adjusted_paired_report(_two_difficulty_cost_study())
    policy = adjusted["paired_exact_test_policy"]
    assert policy["adjustment_family_size"] == MULTI_HYPOTHESIS_COUNT
    for comparison in adjusted["paired_baseline_comparisons"]:
        assert comparison["verification_asymmetry_test"] is None
        for name in ("elapsed_ns", "artifact_bytes"):
            test = comparison["cost_differences"][name]["paired_sign_test"]
            assert test["p_two_sided"] == [1, 2048]
            assert test["p_holm_adjusted"] == [1, 512]


def test_empty_paired_family_emits_zero_adjusted_tests() -> None:
    """All tied results produce no p-values and no invented adjustments."""
    document = _repeated_success_study(12)
    for row in document["observations"]:
        row["metrics"]["elapsed_ns"] = 100
    report = _adjusted_paired_report(document)
    assert report["paired_exact_test_policy"]["adjustment_family_size"] == 0
    comparison = report["paired_baseline_comparisons"][0]
    assert comparison["verification_asymmetry_test"] is None
    for test in comparison["cost_differences"].values():
        assert test["paired_sign_test"] is None


@pytest.mark.parametrize(
    ("violation", "message"),
    [
        ("duplicate", "duplicate algorithm/case/trial"),
        ("schema", "unsupported arena schema version"),
        ("verdict", "inconsistent independent verifier evidence"),
        ("budget", "verified elapsed time exceeds study budget"),
        ("extra", "root: expected fields"),
    ],
)
def test_direct_analyzer_rejects_unadmitted_records_before_ranking(
    violation: str,
    message: str,
) -> None:
    """In-memory calls cannot inflate capacity by skipping wire admission."""
    document = _document()
    first = document["observations"][0]
    if violation == "duplicate":
        document["observations"].extend(
            [first.copy(), document["observations"][2].copy()]
        )
    elif violation == "schema":
        document["schema_version"] = 2
    elif violation == "verdict":
        first["verifier_verdict"] = analyze.NOT_RUN
    elif violation == "budget":
        first["metrics"]["elapsed_ns"] = (
            document["study"]["budget"]["time_ns"] + 1
        )
    elif violation == "extra":
        document["unreviewed_metadata"] = "not an admitted schema field"
    with pytest.raises(analyze.ArenaError, match=message):
        _ = analyze.analyze(document)


@pytest.mark.parametrize("foreign", [None, [], "report", 1])
def test_direct_analyzer_rejects_foreign_document_before_grouping(
    monkeypatch: pytest.MonkeyPatch,
    foreign: object,
) -> None:
    """Malformed in-memory documents fail as typed errors, not key errors."""

    def forbidden_key(*args: object, **kwargs: object) -> None:
        _ = (args, kwargs)
        message = "foreign document entered cohort analysis"
        raise AssertionError(message)

    monkeypatch.setattr(analyze, "_case_key", forbidden_key)
    with pytest.raises(analyze.ArenaError, match="root: expected fields"):
        _ = analyze.analyze(cast("dict[str, Any]", foreign))


class _HostileMap(dict[str, Any]):
    """A caller-owned mapping can lie when admission iterates its keys."""

    def __iter__(self) -> Any:
        """Never allow untrusted mapping hooks to run before type admission."""
        message = "caller-owned mapping iterator executed"
        raise AssertionError(message)


class _HostileList(list[Any]):
    """A caller-owned array can replace observation values during parsing."""

    def __iter__(self) -> Any:
        """Never allow untrusted list hooks to run before type admission."""
        message = "caller-owned list iterator executed"
        raise AssertionError(message)


class _HostileText(str):  # ruff: ignore[subclass-builtin]
    """Text subclasses may override normalization methods."""

    def strip(self, chars: str | None = None) -> str:
        """The exact text-type guard must reject before calling strip."""
        del chars
        message = "caller-owned text normalization executed"
        raise AssertionError(message)


class _HostileKey(str):  # ruff: ignore[subclass-builtin]
    """Caller-supplied dict keys can run code when rehashed."""

    armed = False

    def __hash__(self) -> int:
        """Reject key inspection after construction unless type admission runs first.

        Returns:
            Original string hash while the fixture constructs its dictionary.

        """
        if self.armed:
            message = "caller-owned key hash executed"
            raise AssertionError(message)
        return str.__hash__(self)


@pytest.mark.parametrize("kind", ["root", "metrics"])
def test_direct_analyzer_rejects_custom_key_hash_before_rehash(kind: str) -> None:
    """Mutable in-memory records cannot run key hooks inside schema admission."""
    document = _document()
    source: dict[str, Any] = (
        document if kind == "root" else document["observations"][0]["metrics"]
    )
    key = "study" if kind == "root" else "elapsed_ns"
    val = source.pop(key)
    source[_HostileKey(key)] = val
    _HostileKey.armed = True
    try:
        with pytest.raises(analyze.ArenaError, match="expected fields|unknown metric"):
            _ = analyze.analyze(document)
    finally:
        _HostileKey.armed = False


@pytest.mark.parametrize(
    ("kind", "diagnostic"),
    [
        ("root", "root: expected fields"),
        ("study", "study: expected fields"),
        ("observation", r"observations\[0\]: expected fields"),
        ("metrics", "metrics: unknown metric"),
        ("objectives", "study.objectives: expected nonempty list"),
        ("observations", "observations: expected nonempty array"),
        ("text", "study.question: expected nonempty"),
    ],
)
def test_direct_analyzer_rejects_spoofed_nested_json_types_before_hooks(
    kind: str, diagnostic: str,
) -> None:
    """Native JSON shapes, not caller-controlled method overrides, enter ranking."""
    document = _document()
    if kind == "root":
        document = _HostileMap(document)
    elif kind == "study":
        document["study"] = _HostileMap(document["study"])
    elif kind == "observation":
        document["observations"][0] = _HostileMap(document["observations"][0])
    elif kind == "metrics":
        row = document["observations"][0]
        row["metrics"] = _HostileMap(row["metrics"])
    elif kind == "objectives":
        study = document["study"]
        study["objectives"] = _HostileList(study["objectives"])
    elif kind == "observations":
        document["observations"] = _HostileList(document["observations"])
    elif kind == "text":
        study = document["study"]
        study["question"] = _HostileText(study["question"])
    with pytest.raises(analyze.ArenaError, match=diagnostic):
        _ = analyze.analyze(document)


@pytest.mark.parametrize(
    ("field", "invalid"),
    [
        ("median_intervals_95", "false"),
        ("median_intervals_95", 1),
        ("median_intervals_95", None),
        ("paired_exact_tests_enabled", "no"),
        ("paired_exact_tests_enabled", 0),
        ("paired_exact_tests_enabled", object()),
        ("adjust_paired_tests", "false"),
        ("adjust_paired_tests", 1),
        ("adjust_paired_tests", None),
    ],
)
def test_direct_analyzer_rejects_nonboolean_inference_options_before_analysis(
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    invalid: object,
) -> None:
    """Direct callers cannot enable inferential claims with a truthy string."""

    def forbidden_group(*args: object, **kwargs: object) -> None:
        _ = (args, kwargs)
        message = "invalid statistical option entered cohort analysis"
        raise AssertionError(message)

    monkeypatch.setattr(analyze, "_case_key", forbidden_group)
    options: dict[str, Any] = {field: invalid}
    with pytest.raises(analyze.ArenaError, match="exact booleans"):
        _ = analyze.analyze(_document(), **options)


def test_adjustment_without_paired_tests_is_rejected_before_report() -> None:
    """A caller cannot silently enable a different inferential policy."""
    document = _repeated_success_study(12)
    admitted = analyze.parse_document(json.dumps(document))
    with pytest.raises(
        analyze.ArenaError, match="requires --paired-exact-tests"
    ):
        analyze.analyze(admitted, adjust_paired_tests=True)


def test_holm_cli_rejects_missing_requirement_and_outputs_no_json(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Strong inference is explicit and misconfigured options fail closed."""
    document = _repeated_success_study(12)
    path = tmp_path / "samples.json"
    _ = path.write_text(json.dumps(document), encoding="utf-8")
    monkeypatch.setattr(
        sys,
        "argv",
        ["arena", str(path), "--adjust-paired-tests"],
    )
    with pytest.raises(SystemExit, match="2"):
        analyze.main()
    result = capsys.readouterr()
    assert not result.out
    assert HOLM_ERROR in result.err
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "arena",
            str(path),
            "--paired-exact-tests",
            "--adjust-paired-tests",
        ],
    )
    assert analyze.main() == 0
    assert json.loads(capsys.readouterr().out) == _adjusted_paired_report(
        document
    )


def _success_report(document: dict[str, Any]) -> dict[str, Any]:
    report = _run(document)
    analyze.annotate_success_intervals(report)
    return report


@pytest.mark.parametrize(
    "kind",
    ["root-map", "capacity-list", "point-map", "point-key"],
)
def test_success_annotation_rejects_foreign_shapes_before_hooks(kind: str) -> None:
    """A direct caller cannot inject container hooks into inference output."""
    report = _run(_document())
    point = report["capacity_curve"][0]
    if kind == "root-map":
        report = _HostileMap(report)
    elif kind == "capacity-list":
        report["capacity_curve"] = _HostileList(report["capacity_curve"])
    elif kind == "point-map":
        report["capacity_curve"][1] = _HostileMap(report["capacity_curve"][1])
    else:
        target = report["capacity_curve"][1]
        target[_HostileKey("foreign")] = None
    _HostileKey.armed = True
    try:
        with pytest.raises(analyze.ArenaError, match="success interval"):
            analyze.annotate_success_intervals(report)
    finally:
        _HostileKey.armed = False
    assert SUCCESS_INTERVAL_KEY not in point
    assert SUCCESS_INTERVAL_POLICY_KEY not in report


@pytest.mark.parametrize(
    ("field", "invalid"),
    [
        ("verified", True),
        ("verified", "1"),
        ("verified", -1),
        ("verified", 3),
        ("attempts", False),
        ("attempts", "2"),
        ("attempts", 0),
        ("attempts", -1),
        ("attempts", 2.0),
    ],
)
def test_success_annotation_rejects_invalid_counts_atomically(
    field: str,
    invalid: object,
) -> None:
    """A late invalid point cannot leave a partially annotated report."""
    report = _run(_document())
    first, second = report["capacity_curve"][:2]
    second[field] = invalid
    with pytest.raises(analyze.ArenaError, match="success interval"):
        analyze.annotate_success_intervals(report)
    assert SUCCESS_INTERVAL_KEY not in first
    assert SUCCESS_INTERVAL_KEY not in second
    assert SUCCESS_INTERVAL_POLICY_KEY not in report


def test_success_annotation_rejects_missing_counts_before_mutation() -> None:
    """Missing success counts fail through the typed analyzer boundary."""
    report = _run(_document())
    first, second = report["capacity_curve"][:2]
    del second["verified"]
    with pytest.raises(analyze.ArenaError, match="success interval"):
        analyze.annotate_success_intervals(report)
    assert SUCCESS_INTERVAL_KEY not in first
    assert SUCCESS_INTERVAL_POLICY_KEY not in report


def test_success_interval_covers_all_attempts() -> None:
    """A reported success probability includes failed attempts."""
    document = _repeated_success_study(10)
    for row in document["observations"]:
        if (
            row["algorithm"] == CANDIDATE
            and row["case"]["seed"] < FAILURE_SEED_BOUND
        ):
            row["outcome"] = "no_solution"
            row["verifier_verdict"] = analyze.NOT_RUN
            row["metrics"] = {"elapsed_ns": 90}
    report = _success_report(document)
    points = report["capacity_curve"]
    candidate = next(
        point for point in points if point["algorithm"] == CANDIDATE
    )
    baseline = next(point for point in points if point["algorithm"] == BASELINE)
    assert candidate["verified"] == SUCCESS_OBSERVED
    assert candidate["attempts"] == SUCCESS_ATTEMPTS
    interval = candidate["verification_success_probability_interval_95"]
    assert interval is not None
    assert interval["verified"] == SUCCESS_OBSERVED
    assert interval["sample_count"] == SUCCESS_ATTEMPTS
    assert interval["lower"] == [383, 2048]
    assert interval["upper"] == [1665, 2048]
    assert baseline["verification_success_probability_interval_95"][
        "upper"
    ] == [1, 1]
    policy = report["verification_success_interval_policy"]
    assert policy["requested_confidence"] == [19, 20]
    assert not policy["pareto_uses_intervals"]
    assert INDEPENDENT_NOTE in policy["assumptions"]


def test_zero_verified_trials_have_no_invented_probability() -> None:
    """An all-failure cohort retains zero as observation, not proof of p=0."""
    document = _repeated_success_study(10)
    for row in document["observations"]:
        if row["algorithm"] == CANDIDATE:
            row["outcome"] = "tool_failed"
            row["verifier_verdict"] = analyze.NOT_RUN
            row["metrics"] = {"elapsed_ns": 90}
    point = next(
        p
        for p in _success_report(document)["capacity_curve"]
        if p["algorithm"] == CANDIDATE
    )
    interval = point["verification_success_probability_interval_95"]
    assert interval is not None
    assert interval["lower"] == [0, 1]
    assert interval["upper"] == [79, 256]


def test_default_report_and_pareto_are_unchanged_by_success_intervals() -> None:
    """The inference annotation cannot alter baseline decisions or counts."""
    document = _repeated_success_study(10)
    without = _run(document)
    report = _success_report(document)
    assert SUCCESS_INTERVAL_POLICY_KEY not in without
    assert report["pareto_frontiers"] == without["pareto_frontiers"]
    assert (
        report["highest_observed_verified_difficulty"]
        == (without["highest_observed_verified_difficulty"])
    )
    assert all(
        SUCCESS_INTERVAL_KEY not in point for point in without["capacity_curve"]
    )
    document["observations"].reverse()
    assert _success_report(document) == report


def test_standalone_cli_success_intervals_are_explicitly_optional(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """No statistical fields appear unless the operator requests them."""
    document = _repeated_success_study(10)
    path = tmp_path / "study.json"
    _ = path.write_text(json.dumps(document), encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["arena", str(path)])
    assert analyze.main() == 0
    assert json.loads(capsys.readouterr().out) == _run(document)
    monkeypatch.setattr(
        sys,
        "argv",
        ["arena", str(path), "--success-intervals-95"],
    )
    assert analyze.main() == 0
    assert json.loads(capsys.readouterr().out) == _success_report(document)


@pytest.mark.parametrize("kind", [ValueError, RuntimeError])
def test_read_input_does_not_format_foreign_study_file_error(
    monkeypatch: pytest.MonkeyPatch,
    kind: type[Exception],
) -> None:
    """Foreign reader diagnostics cannot conceal a typed input rejection."""

    class HostileStudyFileError(analyze.study_file.StudyFileError, kind):
        def __str__(self) -> str:
            raise AssertionError("foreign study file formatter invoked")

    failure = HostileStudyFileError("unsafe reader message")

    def fail_read(*_args: object, **_kwargs: object) -> bytes:
        raise failure

    monkeypatch.setattr(analyze.study_file, "read_study_bytes", fail_read)
    with pytest.raises(
        analyze.ArenaError, match="arena study input rejected"
    ) as caught:
        _ = analyze.read_input(cast("Path", "ignored.json"))
    assert caught.value.__cause__ is failure


@pytest.mark.parametrize(
    ("phase", "kind"),
    [
        ("input", analyze.ArenaError),
        ("input", OSError),
        ("input", UnicodeError),
        ("input", IndexError),
        ("input", Exception),
        ("output", analyze.report_output.ReportOutputError),
        ("output", IndexError),
        ("output", Exception),
    ],
)
def test_cli_does_not_format_foreign_boundary_failures(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    phase: str,
    kind: type[Exception],
) -> None:
    """Foreign input/output faults cannot replace the operator exit status."""

    class HostileBoundaryError(kind):
        def __str__(self) -> str:
            raise AssertionError("foreign operator diagnostic formatter invoked")

    failure = HostileBoundaryError("unsafe operator message")

    def fail_boundary(*_args: object, **_kwargs: object) -> Never:
        raise failure

    path = tmp_path / "study.json"
    _ = path.write_text(json.dumps(_document()), encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["arena", str(path)])
    monkeypatch.setattr(
        analyze if phase == "input" else analyze.report_output,
        "read_input" if phase == "input" else "publish",
        fail_boundary,
    )
    with pytest.raises(SystemExit) as caught:
        analyze.main()
    assert caught.value.code == 2
    output = capsys.readouterr()
    assert not output.out
    assert output.err.startswith("arena:")
    assert "unsafe operator message" not in output.err


def test_cli_preserves_exact_native_input_and_output_diagnostics(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Local error details remain useful when their types are trustworthy."""
    path = tmp_path / "study.json"
    _ = path.write_text(json.dumps(_document()), encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["arena", str(path)])

    def reject_input(_path: Path) -> Never:
        raise analyze.ArenaError("exact local study failure")

    with monkeypatch.context() as context:
        context.setattr(analyze, "read_input", reject_input)
        with pytest.raises(SystemExit, match="2"):
            analyze.main()
    assert "exact local study failure" in capsys.readouterr().err

    def reject_output(*_args: object) -> Never:
        raise analyze.report_output.ReportOutputError("exact local output failure")

    with monkeypatch.context() as context:
        context.setattr(analyze.report_output, "publish", reject_output)
        with pytest.raises(SystemExit, match="2"):
            analyze.main()
    assert "exact local output failure" in capsys.readouterr().err


@pytest.mark.parametrize(
    ("boundary", "kind"),
    [
        ("decoder", analyze.ArenaError),
        ("decoder", ValueError),
        ("decoder", TypeError),
        ("decoder", RecursionError),
        ("study", analyze.study_file.StudyFileError),
        ("cli", analyze.ArenaError),
        ("cli", OSError),
        ("cli", UnicodeError),
        ("output", analyze.report_output.ReportOutputError),
    ],
)
def test_exact_native_failure_with_foreign_argument_is_not_formatted(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    boundary: str,
    kind: type[Exception],
) -> None:
    """An exact exception type cannot launder caller-owned formatter hooks."""

    class HostileArgument:
        def __str__(self) -> str:
            raise AssertionError("native error invoked foreign argument formatter")

    failure = kind(HostileArgument())

    def fail(*_args: object, **_kwargs: object) -> Never:
        raise failure

    if boundary == "decoder":
        monkeypatch.setattr(analyze.json, "loads", fail)
        with pytest.raises(analyze.ArenaError, match="invalid arena JSON") as caught:
            _ = analyze.parse_document("{}")
        assert caught.value.__cause__ is failure
        return
    if boundary == "study":
        monkeypatch.setattr(analyze.study_file, "read_study_bytes", fail)
        with pytest.raises(analyze.ArenaError) as caught:
            _ = analyze.read_input(cast("Path", "ignored.json"))
        assert caught.value.__cause__ is failure
        return

    path = tmp_path / "study.json"
    _ = path.write_text(json.dumps(_document()), encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["arena", str(path)])
    if boundary == "cli":
        monkeypatch.setattr(analyze, "read_input", fail)
    else:
        monkeypatch.setattr(analyze.report_output, "publish", fail)
    with pytest.raises(SystemExit) as caught:
        analyze.main()
    assert caught.value.code == 2
    output = capsys.readouterr()
    assert output.err.startswith("arena:")
    assert not output.out


@pytest.mark.parametrize(
    "dependency", ["parse_document", "analyze", "require_unchanged_study_input"]
)
@pytest.mark.parametrize("fault_type", [IndexError, Exception])
def test_cli_rejects_unanticipated_analysis_dependency_faults_without_json(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    dependency: str,
    fault_type: type[Exception],
) -> None:
    """Unexpected parser, analyzer or recheck faults cannot publish a report."""
    path = tmp_path / "study.json"
    _ = path.write_text(json.dumps(_document()), encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["arena", str(path)])

    class HostileAnalysisError(fault_type):
        def __str__(self) -> str:
            raise AssertionError("unanticipated analysis formatter invoked")

    primary = HostileAnalysisError("untrusted analysis diagnostic")

    def fail_analysis(*_args: object, **_kwargs: object) -> Never:
        raise primary

    monkeypatch.setattr(analyze, dependency, fail_analysis)
    with pytest.raises(SystemExit) as caught:
        analyze.main()
    assert caught.value.code == 2
    result = capsys.readouterr()
    assert result.err.startswith("arena:")
    assert "untrusted analysis diagnostic" not in result.err
    assert not result.out


@pytest.mark.parametrize(
    "foreign_bytes", [None, "{}", object(), bytearray(b"{}"), True]
)
def test_direct_input_reader_rejects_nonnative_byte_receipts(
    monkeypatch: pytest.MonkeyPatch,
    foreign_bytes: object,
) -> None:
    """A substitute bounded reader cannot launder nonbytes into trusted JSON."""
    monkeypatch.setattr(
        analyze.study_file,
        "read_study_bytes",
        lambda *_args, **_kwargs: foreign_bytes,
    )
    with pytest.raises(analyze.ArenaError, match="nonnative bytes"):
        analyze.read_input(cast("Path", "ignored.json"))


def test_direct_input_reader_does_not_dispatch_foreign_decode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A bytes subclass must not fake an admitted source through decode()."""

    class ForgedBytes(bytes):  # ruff: ignore[subclass-builtin]
        def decode(self, *_args: object, **_kwargs: object) -> str:
            raise AssertionError("foreign source decoder invoked")

    monkeypatch.setattr(
        analyze.study_file,
        "read_study_bytes",
        lambda *_args, **_kwargs: ForgedBytes(b"{}"),
    )
    with pytest.raises(analyze.ArenaError, match="nonnative bytes"):
        analyze.read_input(cast("Path", "ignored.json"))


def test_direct_input_reader_rejects_oversized_dependency_receipt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Even a substituted reader cannot enlarge the public byte budget."""
    monkeypatch.setattr(
        analyze.study_file,
        "read_study_bytes",
        lambda *_args, **_kwargs: b" " * (analyze.MAX_INPUT_BYTES + 1),
    )
    with pytest.raises(analyze.ArenaError, match="exceeds 16 MiB"):
        analyze.read_input(cast("Path", "ignored.json"))


def test_late_recheck_rejects_foreign_source_without_comparing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A source subclass cannot falsely certify a changed file with __ne__."""

    class ForgedOriginal(str):  # ruff: ignore[subclass-builtin]
        def __ne__(self, _other: object) -> bool:
            raise AssertionError("foreign late-source comparison invoked")

    def forbidden_read(*_args: object, **_kwargs: object) -> Never:
        raise AssertionError("foreign original reached file admission")

    monkeypatch.setattr(analyze, "read_input", forbidden_read)
    with pytest.raises(analyze.ArenaError, match="exact native source text"):
        analyze.require_unchanged_study_input(
            cast("Path", "ignored.json"), ForgedOriginal("source")
        )


def test_late_recheck_rejects_forged_equality_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A caller-defined comparison must never suppress observed source drift."""

    class ForgedOriginal(str):  # ruff: ignore[subclass-builtin]
        def __ne__(self, _other: object) -> bool:
            return False

    monkeypatch.setattr(analyze, "read_input", lambda _path: "changed")
    with pytest.raises(analyze.ArenaError, match="exact native source text"):
        analyze.require_unchanged_study_input(
            cast("Path", "ignored.json"), ForgedOriginal("original")
        )


@pytest.mark.parametrize("fault_type", [IndexError, Exception])
def test_direct_input_reader_types_unanticipated_dependency_fault(
    monkeypatch: pytest.MonkeyPatch,
    fault_type: type[Exception],
) -> None:
    """Unexpected bounded-reader faults stay typed and do not format hooks."""

    class HostileReaderError(fault_type):
        def __str__(self) -> str:
            raise AssertionError("foreign input reader formatter invoked")

    failure = HostileReaderError("untrusted reader fault")

    def fail_read(*_args: object, **_kwargs: object) -> Never:
        raise failure

    monkeypatch.setattr(analyze.study_file, "read_study_bytes", fail_read)
    with pytest.raises(analyze.ArenaError, match="arena study input rejected") as caught:
        analyze.read_input(cast("Path", "ignored.json"))
    assert caught.value.__cause__ is failure
