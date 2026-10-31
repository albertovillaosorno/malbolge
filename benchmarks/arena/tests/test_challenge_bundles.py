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
#   - Arena-to-parametric-challenge canonical replay regression checks.
# - Must-Not:
#   - Present generated oracle agreement as compiled Malbolge correctness.
# - Allows:
#   - Inputs: synthetic challenge bundles and source-reported trial records.
#   - Outputs: assertions on exact replay, provenance, and fail-closed drift.
#   - Side effects: bounded test-local source/oracle/manifest copies.
# - Split-When:
#   - Different challenge families gain separately governed bundle admission.
# - Merge-When:
#   - The generator's source replay boundary owns these cross-record checks.
# - Summary:
#   - Binds reported arena workloads to exact deterministic challenge bytes.
# - Description:
#   - Regenerates canonical challenges without measuring downstream algorithms.
# - Usage:
#   - `python -B -m pytest benchmarks/arena/tests/test_challenge_bundles.py`.
# - Defaults:
#   - Missing, unsafe, fabricated and incompatible challenge files fail closed.
#

"""Challenge bundle preflight tests, not compiler performance claims."""

# ruff: file-ignore[assert]

from __future__ import annotations

import copy
import csv
from hashlib import sha256
from io import StringIO
import json
import sys
from typing import TYPE_CHECKING
from typing import cast

import pytest

from benchmarks.arena import analyze
from benchmarks.arena import challenge_bundles
from benchmarks.arena import evidence
from benchmarks.arena import raw_samples
from benchmarks.arena.tests.test_evidence import sample_study
from benchmarks.challenges import generate

if TYPE_CHECKING:
    from pathlib import Path
    from typing import Any

FAMILY = "arithmetic-dag"
PROFILE = "malbolge-2026.3"
SEED = 7
NODES = 4
BUNDLE_ROOT = "challenge-bundles"
PREFIX = f"{BUNDLE_ROOT}/{FAMILY}/v1/seed-{SEED}/nodes-{NODES}"
MATCH_SCOPE = "Deterministic challenge bundle replay"
CHALLENGE_MISMATCH = "deterministic regeneration"
ALGORITHM_COUNT = 2
DIFFICULTY_COUNT = 2
BASELINE = "baseline"
VERIFICATION_NOTE = "verification_note"
ORACLE_KIND = "oracle"
LINKED = "symlink"
MISSING = "missing"


def _generated(nodes: int = NODES) -> generate.GeneratedChallenge:
    return generate.generate(
        generate.ChallengeIdentity(
            family=FAMILY,
            version=1,
            seed=SEED,
            profile=PROFILE,
            nodes=nodes,
        )
    )


def _publish(root: Path, nodes: int = NODES) -> str:
    output = f"{BUNDLE_ROOT}/{FAMILY}/v1/seed-{SEED}/nodes-{nodes}"
    directory = root / output
    directory.mkdir(parents=True, exist_ok=True)
    generated = _generated(nodes)
    for name, payload in zip(
        challenge_bundles.BUNDLE_FILES,
        (generated.source, generated.oracle, generated.manifest),
        strict=True,
    ):
        _ = (directory / name).write_bytes(payload)
    return output


def _set_run_case(root: Path, row: dict[str, Any], nodes: int) -> None:
    generated = _generated(nodes)
    identity = json.loads(generated.manifest)["identity"]
    case = row["case"]
    old_difficulty = case["difficulty"]
    old_seed = case["seed"]
    old_workload = case["workload_sha256"]
    case.update({
        "family": FAMILY,
        "version": 1,
        "seed": SEED,
        "difficulty": nodes,
        "workload_sha256": sha256(generated.source).hexdigest(),
    })
    path = root / row["experiment_manifest"]
    text = path.read_text(encoding="utf-8")
    text = text.replace(
        'family = "protocol-fixture-v1"',
        f'family = "{FAMILY}"',
    )
    text = text.replace(
        f"difficulty = {old_difficulty}",
        f"difficulty = {nodes}",
    )
    text = text.replace(f"seed = {old_seed}", f"seed = {SEED}")
    text = text.replace(
        'target_profile = "profile-independent"',
        f'target_profile = "{PROFILE}"\n'
        'target_profile_fingerprint = "'
        + str(identity["target_profile_fingerprint"])
        + '"',
    )
    text = text.replace(
        f'workload_sha256 = "{old_workload}"',
        f'workload_sha256 = "{case["workload_sha256"]}"',
    )
    _ = path.write_text(text, encoding="utf-8")


def _study(root: Path) -> dict[str, Any]:
    document = sample_study(root)
    document["study"]["target_profile"] = PROFILE
    _publish(root)
    for row in document["observations"]:
        _set_run_case(root, row, NODES)
    return document


def _preflight(document: dict[str, Any], root: Path) -> dict[str, Any]:
    admitted = analyze.parse_document(json.dumps(document))
    return evidence.validate_links(
        admitted,
        root,
        policy=evidence.EvidencePolicy(
            challenge_root=BUNDLE_ROOT,
        ),
    )


def _direct_bundle() -> tuple[dict[str, Any], dict[str, bytes]]:
    generated = _generated()
    case = {
        "family": FAMILY,
        "version": 1,
        "difficulty": NODES,
        "seed": SEED,
        "workload_sha256": sha256(generated.source).hexdigest(),
    }
    files: dict[str, bytes] = dict(
        zip(
            challenge_bundles.BUNDLE_FILES,
            (generated.source, generated.oracle, generated.manifest),
            strict=True,
        )
    )
    return case, files


@pytest.mark.parametrize(
    "malformed_case",
    [
        None,
        {},
        {"difficulty": None},
        {"difficulty": False},
        {"difficulty": "4"},
        {"difficulty": float("inf")},
    ],
    ids=[
        "missing-case",
        "empty",
        "missing-fields",
        "boolean",
        "text",
        "infinite",
    ],
)
def test_direct_bundle_replay_rejects_malformed_case_shape(
    malformed_case: object,
) -> None:
    """A direct replay caller cannot escape the bundle's typed admission."""
    _, files = _direct_bundle()
    with pytest.raises(
        challenge_bundles.ChallengeBundleError, match="challenge"
    ):
        challenge_bundles.verify_bundle(
            cast("dict[str, Any]", malformed_case), PROFILE, files
        )


@pytest.mark.parametrize(
    "malformed_files",
    [None, {}, {"oracle.bin": 3}, {"program.c": "not bytes"}],
    ids=["missing-map", "missing-members", "wrong-oracle", "wrong-source"],
)
def test_direct_bundle_replay_rejects_malformed_payload_shape(
    malformed_files: object,
) -> None:
    """Invalid payload maps fail before canonical replay."""
    case, files = _direct_bundle()
    if isinstance(malformed_files, dict) and malformed_files:
        files.update(cast("dict[str, bytes]", malformed_files))
    else:
        files = cast("dict[str, bytes]", malformed_files)
    with pytest.raises(challenge_bundles.ChallengeBundleError, match="bundle"):
        challenge_bundles.verify_bundle(case, PROFILE, files)


@pytest.mark.parametrize(
    ("field", "invalid"),
    [("family", []), ("family", None), ("workload_sha256", [])],
    ids=["family-list", "family-missing", "digest-list"],
)
def test_direct_bundle_rejects_unhashable_identity_fields(
    field: str, invalid: object
) -> None:
    """Forged identity fields cannot reach unhashable host lookup paths."""
    case, files = _direct_bundle()
    case[field] = invalid
    with pytest.raises(
        challenge_bundles.ChallengeBundleError, match="challenge"
    ):
        challenge_bundles.verify_bundle(case, PROFILE, files)


class _HostileVersion:
    """A non-JSON version can execute its formatting hook during rejection."""

    def __str__(self) -> str:
        message = "caller-owned version formatting executed"
        raise AssertionError(message)


@pytest.mark.parametrize(
    ("field", "invalid"),
    [
        ("version", _HostileVersion()),
        ("version", True),
        ("version", 1.0),
        ("seed", True),
        ("seed", 7.0),
    ],
    ids=[
        "hostile-version",
        "boolean-version",
        "floating-version",
        "boolean-seed",
        "floating-seed",
    ],
)
def test_direct_bundle_rejects_foreign_numeric_identity_before_generation(
    field: str, invalid: object,
) -> None:
    """Only exact JSON integers can reach the generator's identity checks."""
    case, files = _direct_bundle()
    case[field] = invalid
    with pytest.raises(
        challenge_bundles.ChallengeBundleError, match="challenge"
    ):
        challenge_bundles.verify_bundle(case, PROFILE, files)


class _HostileKey(str):  # ruff: ignore[subclass-builtin]
    """Foreign dict keys can run equality methods during set comparisons."""

    def __eq__(self, other: object) -> bool:
        del other
        message = "caller-owned mapping key equality executed"
        raise AssertionError(message)

    __hash__ = str.__hash__


@pytest.mark.parametrize("kind", ["case", "bundle"])
def test_direct_bundle_rejects_non_native_mapping_keys_before_comparison(
    kind: str,
) -> None:
    """Native JSON object keys only; never invoke foreign key equality hooks."""
    case, files = _direct_bundle()
    if kind == "case":
        case[_HostileKey("version")] = case.pop("version")
        diagnostic = "challenge"
    else:
        files[_HostileKey("oracle.bin")] = files.pop("oracle.bin")
        diagnostic = "bundle"
    with pytest.raises(challenge_bundles.ChallengeBundleError, match=diagnostic):
        challenge_bundles.verify_bundle(case, PROFILE, files)


@pytest.mark.parametrize(
    ("member", "limit"),
    [
        ("program.c", challenge_bundles.MAX_SOURCE_BYTES),
        ("manifest.json", challenge_bundles.MAX_MANIFEST_BYTES),
    ],
    ids=["source", "manifest"],
)
def test_direct_bundle_replay_rejects_payload_over_budget(
    member: str, limit: int
) -> None:
    """Oversized payloads fail before potentially expensive regeneration."""
    case, files = _direct_bundle()
    files[member] = b"x" * (limit + 1)
    with pytest.raises(
        challenge_bundles.ChallengeBundleError, match="byte limit"
    ):
        challenge_bundles.verify_bundle(case, PROFILE, files)


def test_direct_bundle_replay_accepts_exact_payload() -> None:
    """Defensive admission preserves independently regenerated bytes."""
    case, files = _direct_bundle()
    assert (
        challenge_bundles.verify_bundle(case, PROFILE, files)
        == case["workload_sha256"]
    )


def test_canonical_challenge_bundle_regenerates_without_execution(
    tmp_path: Path,
) -> None:
    """Two algorithms share one exact challenge, not fabricated sample work."""
    document = _study(tmp_path)
    checked = _preflight(document, tmp_path)
    assert checked["regenerated_challenge_bundles"] == 1
    assert checked["challenge_source_sha256"] == {
        PREFIX: sha256(_generated().source).hexdigest(),
    }
    assert checked["reported_trials_checked"] == ALGORITHM_COUNT
    assert MATCH_SCOPE in checked["scope"]


@pytest.mark.parametrize("filename", challenge_bundles.BUNDLE_FILES)
def test_any_mutated_challenge_payload_is_rejected(
    tmp_path: Path,
    filename: str,
) -> None:
    """Changed source, oracle, or manifest bytes fail canonical regeneration."""
    document = _study(tmp_path)
    path = tmp_path / PREFIX / filename
    raw = path.read_bytes()
    _ = path.write_bytes(raw[:-1] + bytes([raw[-1] ^ 1]))
    with pytest.raises(evidence.EvidenceError, match="bundle differs"):
        _preflight(document, tmp_path)


def test_wrong_reported_digest_rejected_even_when_files_are_consistent(
    tmp_path: Path,
) -> None:
    """Producer-declared workload SHA cannot differ from regenerated C."""
    document = _study(tmp_path)
    wrong = "f" * analyze.SHA256_HEX_LENGTH
    for row in document["observations"]:
        original = row["case"]["workload_sha256"]
        row["case"]["workload_sha256"] = wrong
        path = tmp_path / row["experiment_manifest"]
        _ = path.write_text(
            path.read_text(encoding="utf-8").replace(original, wrong),
            encoding="utf-8",
        )
    with pytest.raises(evidence.EvidenceError, match="workload SHA-256"):
        _preflight(document, tmp_path)


@pytest.mark.parametrize("kind", ["symlink", "missing", "extra"])
def test_bundle_requires_exact_ordinary_files(
    tmp_path: Path, kind: str
) -> None:
    """Missing and linked files are never trusted challenge provenance."""
    document = _study(tmp_path)
    source = tmp_path / PREFIX / "program.c"
    if kind == LINKED:
        source.unlink()
        source.symlink_to(tmp_path / PREFIX / "oracle.bin")
    elif kind == MISSING:
        source.unlink()
    else:
        with source.open("ab") as stream:
            _ = stream.write(b"x")
    with pytest.raises(
        evidence.EvidenceError, match=r"bundle|symlink|FileNotFound"
    ):
        _preflight(document, tmp_path)


def test_bounded_replay_rejects_excessive_challenge_difficulty(
    tmp_path: Path,
) -> None:
    """No unbounded regeneration is triggered by producer-controlled nodes."""
    document = _study(tmp_path)
    over = challenge_bundles.MAX_BUNDLE_NODES + 1
    for row in document["observations"]:
        row["case"]["difficulty"] = over
        path = tmp_path / row["experiment_manifest"]
        _ = path.write_text(
            path.read_text(encoding="utf-8").replace(
                f"difficulty = {NODES}",
                f"difficulty = {over}",
            ),
            encoding="utf-8",
        )
    with pytest.raises(evidence.EvidenceError, match=r"bundle|4096-node"):
        _preflight(document, tmp_path)


def test_challenge_bundle_root_cannot_escape_or_follow_links(
    tmp_path: Path,
) -> None:
    """Even an opt-in direct API caller cannot select a parent directory."""
    document = _study(tmp_path)
    admitted = analyze.parse_document(json.dumps(document))
    with pytest.raises(evidence.EvidenceError, match="canonical relative"):
        evidence.validate_links(
            admitted,
            tmp_path,
            policy=evidence.EvidencePolicy(
                challenge_root="../untrusted",
            ),
        )
    root_link = tmp_path / "linked-challenge"
    root_link.symlink_to(tmp_path / BUNDLE_ROOT)
    with pytest.raises(evidence.EvidenceError, match="symlink"):
        evidence.validate_links(
            admitted,
            tmp_path,
            policy=evidence.EvidencePolicy(
                challenge_root="linked-challenge",
            ),
        )


def test_different_difficulty_bundles_have_distinct_verified_source_hashes(
    tmp_path: Path,
) -> None:
    """One study may cite two real difficulties without pooling them."""
    document = _study(tmp_path)
    next_nodes = NODES + 1
    _publish(tmp_path, nodes=next_nodes)
    for row in tuple(document["observations"]):
        new_row = copy.deepcopy(row)
        old_path = tmp_path / row["experiment_manifest"]
        new_relative = row["experiment_manifest"].replace(".toml", "-next.toml")
        _ = (tmp_path / new_relative).write_bytes(old_path.read_bytes())
        new_row["experiment_manifest"] = new_relative
        _set_run_case(tmp_path, new_row, next_nodes)
        new_row["raw_sample"] = row["raw_sample"]
        document["observations"].append(new_row)
    # Reassign each new run's raw path identity unchanged; each trial uses the
    # same retained sample file but different challenge source and run manifest.
    checked = _preflight(document, tmp_path)
    assert checked["regenerated_challenge_bundles"] == DIFFICULTY_COUNT
    assert set(checked["challenge_source_sha256"].values()) == {
        sha256(_generated(NODES).source).hexdigest(),
        sha256(_generated(next_nodes).source).hexdigest(),
    }


def test_challenge_bundle_cli_never_emits_partial_report_after_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The operator receives a complete report or no published capacity data."""
    document = _study(tmp_path)
    input_path = tmp_path / "study.json"
    _ = input_path.write_text(json.dumps(document), encoding="utf-8")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "arena-evidence",
            str(input_path),
            "--root",
            str(tmp_path),
            "--challenge-root",
            BUNDLE_ROOT,
        ],
    )
    assert evidence.main() == 0
    result = json.loads(capsys.readouterr().out)
    assert result["evidence_preflight"]["regenerated_challenge_bundles"] == 1
    source = tmp_path / PREFIX / "program.c"
    _ = source.write_bytes(source.read_bytes() + b"untrusted")
    with pytest.raises(SystemExit, match="2"):
        evidence.main()
    failure = capsys.readouterr()
    assert not failure.out
    assert CHALLENGE_MISMATCH in failure.err


@pytest.mark.parametrize("filename", challenge_bundles.BUNDLE_FILES)
def test_challenge_bundle_rechecks_mutation_after_report_assembly(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    filename: str,
) -> None:
    """An accepted bundle cannot drift while the preflight report is built."""
    document = _study(tmp_path)
    admitted = analyze.parse_document(json.dumps(document))
    original_report = evidence._report_links

    def mutate_after_report(*args: Any, **kwargs: Any) -> dict[str, Any]:
        report = original_report(*args, **kwargs)
        path = tmp_path / PREFIX / filename
        previous = path.read_bytes()
        _ = path.write_bytes(previous[:-1] + bytes([previous[-1] ^ 1]))
        return report

    monkeypatch.setattr(evidence, "_report_links", mutate_after_report)
    with pytest.raises(evidence.EvidenceError, match="challenge bundle changed"):
        evidence.validate_links(
            admitted,
            tmp_path,
            policy=evidence.EvidencePolicy(challenge_root=BUNDLE_ROOT),
        )


@pytest.mark.parametrize("filename", challenge_bundles.BUNDLE_FILES)
def test_challenge_bundle_rechecks_during_host_c_replay(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    filename: str,
) -> None:
    """Later host-C replay cannot certify bytes altered after generation."""
    document = _study(tmp_path)
    admitted = analyze.parse_document(json.dumps(document))

    def mutate_during_replay(
        _document: dict[str, Any],
        _sources: dict[str, str],
        _root: str,
    ) -> dict[str, str]:
        path = tmp_path / PREFIX / filename
        previous = path.read_bytes()
        _ = path.write_bytes(previous[:-1] + bytes([previous[-1] ^ 1]))
        return {}

    monkeypatch.setattr(evidence, "_replay_host_c_challenges", mutate_during_replay)
    with pytest.raises(evidence.EvidenceError, match="challenge bundle changed"):
        evidence.validate_links(
            admitted,
            tmp_path,
            policy=evidence.EvidencePolicy(
                challenge_root=BUNDLE_ROOT,
                require_host_c_challenge_oracle=True,
            ),
        )


def test_evidence_cli_rechecks_bundle_mutated_after_preflight(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """An analyzed report cannot outlive changed challenge oracle bytes."""
    document = _study(tmp_path)
    source = tmp_path / "study.json"
    _ = source.write_text(json.dumps(document), encoding="utf-8")
    original_analyze = analyze.analyze

    def rewrite_during_analysis(*args: Any, **kwargs: Any) -> dict[str, Any]:
        report = original_analyze(*args, **kwargs)
        path = tmp_path / PREFIX / "oracle.bin"
        original = path.read_bytes()
        _ = path.write_bytes(original[:-1] + bytes([original[-1] ^ 1]))
        return report

    monkeypatch.setattr(analyze, "analyze", rewrite_during_analysis)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "arena-evidence",
            str(source),
            "--root",
            str(tmp_path),
            "--challenge-root",
            BUNDLE_ROOT,
        ],
    )
    with pytest.raises(SystemExit, match="2"):
        evidence.main()
    failure = capsys.readouterr()
    assert not failure.out
    assert "challenge bundle changed" in failure.err


def test_post_analysis_recheck_does_not_repeat_host_c_oracle(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Retained hashes are rechecked without expensive second host-C replay."""
    document = _study(tmp_path)
    source = tmp_path / "study.json"
    _ = source.write_text(json.dumps(document), encoding="utf-8")
    calls = 0

    def replay_once(*args: Any, **kwargs: Any) -> dict[str, str]:
        nonlocal calls
        _ = (args, kwargs)
        calls += 1
        return {}

    monkeypatch.setattr(evidence, "_replay_host_c_challenges", replay_once)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "arena-evidence",
            str(source),
            "--root",
            str(tmp_path),
            "--challenge-root",
            BUNDLE_ROOT,
            "--require-host-c-challenge-oracle",
        ],
    )
    assert evidence.main() == 0
    assert calls == 1
    reported = json.loads(capsys.readouterr().out)
    assert reported["evidence_preflight"]["regenerated_challenge_bundles"] == 1


def _forged_repetition(
    root: Path,
    original: dict[str, Any],
    *,
    trial: int,
    digest: str,
) -> dict[str, Any]:
    copied = copy.deepcopy(original)
    copied["trial"] = trial
    copied["case"]["workload_sha256"] = digest
    old_manifest = root / original["experiment_manifest"]
    new_path = original["experiment_manifest"].replace(
        ".toml",
        "-second.toml",
    )
    _ = (root / new_path).write_text(
        old_manifest.read_text(encoding="utf-8").replace(
            original["case"]["workload_sha256"],
            digest,
        ),
        encoding="utf-8",
    )
    copied["experiment_manifest"] = new_path
    return copied


def test_challenge_replay_cannot_reuse_digest_for_changed_trial_source(
    tmp_path: Path,
) -> None:
    """Regenerated C binds every trial even if its case label is unchanged."""
    document = _study(tmp_path)
    fake_digest = "f" * analyze.SHA256_HEX_LENGTH
    for original in tuple(document["observations"]):
        document["observations"].append(
            _forged_repetition(tmp_path, original, trial=1, digest=fake_digest),
        )
    with pytest.raises(evidence.EvidenceError, match="repeated challenge case"):
        _preflight(document, tmp_path)


def test_challenge_root_with_embedded_nul_is_typed_rejection(
    tmp_path: Path,
) -> None:
    """Malformed policy roots must not leak operating-system path exceptions."""
    document = _study(tmp_path)
    admitted = analyze.parse_document(json.dumps(document))
    with pytest.raises(evidence.EvidenceError, match="canonical relative"):
        evidence.validate_links(
            admitted,
            tmp_path,
            policy=evidence.EvidencePolicy(challenge_root="bundle\x00escape"),
        )


def _integrated_csv(row: dict[str, Any]) -> bytes:
    case = row["case"]
    values = {
        "schema_version": "2",
        "algorithm": row["algorithm"],
        "family": case["family"],
        "version": str(case["version"]),
        "difficulty": str(case["difficulty"]),
        "seed": str(case["seed"]),
        "workload_sha256": case["workload_sha256"],
        "trial": str(row["trial"]),
        "outcome": row["outcome"],
        "verifier": row["verifier"],
        "verifier_verdict": row["verifier_verdict"],
        **{key: str(value) for key, value in row["metrics"].items()},
    }
    output = StringIO(newline="")
    writer = csv.DictWriter(
        output,
        raw_samples.HEADER_2,
        lineterminator="\n",
    )
    writer.writeheader()
    writer.writerow(values)
    return output.getvalue().encode("utf-8")


def _integrated_study(root: Path) -> dict[str, Any]:
    """Build a fully linked synthetic v2 study from a real source generator.

    Returns:
        Two synthetic reported runs with canonical challenge provenance.

    """
    document = _study(root)
    document["study"]["budget"] = {
        "time_ns": 1_000_000_000,
        "memory_bytes": 128 * 1_048_576,
    }
    document["study"]["objectives"].append("energy_uj")
    for row in document["observations"]:
        candidate = row["algorithm"] != BASELINE
        row["metrics"]["energy_uj"] = 20 if candidate else 10
        row["metrics"]["elapsed_ns"] = 8 if candidate else 10
        raw = _integrated_csv(row)
        _ = (root / row["raw_sample"]).write_bytes(raw)
        manifest = root / row["experiment_manifest"]
        content = manifest.read_text(encoding="utf-8").replace(
            "seconds = 1",
            "seconds = 1\nmemory_mib = 128",
        )
        content += (
            "\n[arena_trial]\nschema_version = 1\ntrial = 0\n"
            f'raw_sha256 = "{sha256(raw).hexdigest()}"\n'
        )
        _ = manifest.write_text(content, encoding="utf-8")
    return document


def _all_policy() -> evidence.EvidencePolicy:
    return evidence.EvidencePolicy(
        challenge_root=BUNDLE_ROOT,
        require_raw_rows=True,
        require_trial_run_identity=True,
        require_budget_agreement=True,
        require_matched_accelerator=True,
    )


def test_all_opt_in_evidence_checks_compose_without_measurement_claim(
    tmp_path: Path,
) -> None:
    """One reproducible generated workload exercises all strict interfaces."""
    document = _integrated_study(tmp_path)
    admitted = analyze.parse_document(json.dumps(document))
    checked = evidence.validate_links(admitted, tmp_path, policy=_all_policy())
    assert checked["regenerated_challenge_bundles"] == 1
    assert checked["raw_rows_matched"] == ALGORITHM_COUNT
    assert checked["trial_run_links_checked"] == ALGORITHM_COUNT
    assert checked["run_budget_links_checked"] == ALGORITHM_COUNT
    assert len(checked["declared_run_accelerators"]) == ALGORITHM_COUNT
    report = analyze.analyze(admitted)
    assert report["pareto_frontiers"][0]["algorithms"] == [
        "baseline",
        "candidate",
    ]
    assert VERIFICATION_NOTE in report


@pytest.mark.parametrize("tamper", ["oracle", "raw"])
def test_full_evidence_pipeline_rejects_oracle_or_raw_drift(
    tmp_path: Path,
    tamper: str,
) -> None:
    """Neither an oracle change nor a CSV change bypasses strict preflight."""
    document = _integrated_study(tmp_path)
    if tamper == ORACLE_KIND:
        oracle = tmp_path / PREFIX / "oracle.bin"
        _ = oracle.write_bytes(b"xxxx")
    else:
        row = document["observations"][0]
        raw = tmp_path / row["raw_sample"]
        row["metrics"]["energy_uj"] += 1
        _ = raw.write_bytes(_integrated_csv(row))
    admitted = analyze.parse_document(json.dumps(document))
    with pytest.raises(evidence.EvidenceError, match=r"bundle|raw SHA-256"):
        evidence.validate_links(admitted, tmp_path, policy=_all_policy())
