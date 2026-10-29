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
#   - Exact real-target reference measurements and source/receipt regressions.
# - Must-Not:
#   - Report target echo microbenchmarks as generalized C compilation.
# - Allows:
#   - Inputs: test-owned ignored target sources and executable stubs.
#   - Outputs: checked Malbolge VM evidence and fail-closed negative records.
#   - Side effects: removed test-owned study directories and process launches.
# - Split-When:
#   - A general compiler candidate study has a larger independent verifier.
# - Merge-When:
#   - A verified target-stage runner owns the same bounded echo baseline.
# - Summary:
#   - Confirms real target code and manifest/raw identity after VM execution.
# - Description:
#   - Tests matched pairs, retained failures and unsupported study requests.
# - Usage:
#   - pytest benchmarks/arena/tests/test_target_echo_reference.py.
# - Defaults:
#   - No real artifact evidence without local built emitter and VM binaries.
#

"""Actual classic Malbolge VM target-echo research pilot tests."""

# ruff: file-ignore[assert,private-member-access]

from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess as sp  # ruff: ignore[suspicious-subprocess-import]
import sys
import tempfile
from typing import TYPE_CHECKING

import pytest

from benchmarks.arena import analyze
from benchmarks.arena import evidence
from benchmarks.arena import target_echo_reference

if TYPE_CHECKING:
    from collections.abc import Iterator


RAW_TAMPER = "raw"
ORIGINAL_TRIAL = "trial = 0"
EXPECTED_OBSERVATIONS = 8
EXPECTED_LEVELS = 2
EXPECTED_TRIALS = 2
ARTIFACT_BYTES = "artifact_bytes"
GRAPHICAL_LOW = 33
GRAPHICAL_HIGH = 126
BOOL_TRIAL_ALIAS = True
OUTPUT_ARGUMENT = "--output"
TOOL_FAILED = "tool_failed"


@pytest.fixture
def live_echo() -> Iterator[tuple[Path, dict]]:
    """Run a short real target study and remove only its owned evidence.

    Yields:
        Retained study directory and admitted study document.

    """
    with tempfile.TemporaryDirectory(
        dir=target_echo_reference._TEMP,
        prefix="arena-target-test-tools-",
    ) as tool_directory:
        emitter = Path(tool_directory) / "malbolge_layout"
        runner = Path(tool_directory) / "malbolge"
        emitter.hardlink_to(target_echo_reference.DEFAULT_EMITTER)
        runner.hardlink_to(target_echo_reference.DEFAULT_RUNNER)
        directory, document = target_echo_reference.run_study(
            target_echo_reference.StudyPlan((1, 4), 2),
            emitter=emitter,
            runner=runner,
        )
        try:
            yield directory, document
        finally:
            shutil.rmtree(directory)


@pytest.mark.skipif(
    not target_echo_reference.DEFAULT_EMITTER.is_file()
    or not target_echo_reference.DEFAULT_RUNNER.is_file(),
    reason="built Malbolge CLI binaries not present",
)
def test_real_target_programs_produce_complete_paired_arena_evidence(
    live_echo: tuple[Path, dict],
) -> None:
    """Real classic programs pass independently checked VM EOF and raw links."""
    directory, document = live_echo
    rows = document["observations"]
    assert len(rows) == EXPECTED_OBSERVATIONS
    assert all(row["outcome"] == analyze.VERIFIED for row in rows)
    assert all(row["verifier_verdict"] == analyze.ACCEPTED for row in rows)
    assert {row["case"]["difficulty"] for row in rows} == {1, 4}
    assert (directory / "study.json").is_file()
    evidence_check = evidence.validate_links(
        document,
        target_echo_reference._ROOT,
        policy=evidence.EvidencePolicy(
            require_raw_rows=True,
            require_trial_run_identity=True,
            require_budget_agreement=True,
        ),
    )
    assert evidence_check["raw_rows_matched"] == len(rows)
    assert evidence_check["trial_run_links_checked"] == len(rows)
    report = analyze.analyze(document)
    assert len(report["pareto_frontiers"]) == EXPECTED_LEVELS
    assert all(
        pair["paired_trials"] == EXPECTED_TRIALS
        for pair in report["paired_baseline_comparisons"]
    )
    for pair_count in (1, 4):
        direct = next(
            row
            for row in rows
            if row["algorithm"] == target_echo_reference.BASELINE
            and row["case"]["difficulty"] == pair_count
        )
        padded = next(
            row
            for row in rows
            if row["algorithm"] == target_echo_reference.CANDIDATE
            and row["case"]["difficulty"] == pair_count
        )
        assert direct["metrics"]["artifact_bytes"] == 2 * pair_count + 1
        assert padded["metrics"]["artifact_bytes"] == 3 * pair_count + 1
        for row in (direct, padded):
            stem = f"{row["algorithm"]}-pairs-{pair_count}-trial-{row["trial"]}"
            source = (
                directory / "candidates" / f"{stem}.malbolge"
            ).read_bytes()
            assert len(source) == row["metrics"]["artifact_bytes"]
            assert all(
                GRAPHICAL_LOW <= byte <= GRAPHICAL_HIGH for byte in source
            )


@pytest.mark.skipif(
    not target_echo_reference.DEFAULT_EMITTER.is_file()
    or not target_echo_reference.DEFAULT_RUNNER.is_file(),
    reason="built Malbolge binaries not available",
)
@pytest.mark.parametrize("tamper", ["raw", "manifest"])
def test_retained_target_evidence_tamper_fails_closed(
    live_echo: tuple[Path, dict],
    tamper: str,
) -> None:
    """Edited trial receipts cannot silently drift from raw links."""
    directory, document = live_echo
    first = document["observations"][0]
    if tamper == RAW_TAMPER:
        name = first["raw_sample"].rsplit("/", maxsplit=1)[-1]
        path = directory / "raw" / name
        path.write_bytes(path.read_bytes() + b"\n")
    else:
        name = first["experiment_manifest"].rsplit("/", maxsplit=1)[-1]
        path = directory / "runs" / name
        content = path.read_text(encoding="utf-8")
        assert ORIGINAL_TRIAL in content
        path.write_text(content.replace(ORIGINAL_TRIAL, "trial = 999"))
    with pytest.raises(
        evidence.EvidenceError, match=r"arena_trial|linked arena evidence"
    ):
        evidence.validate_links(
            document,
            target_echo_reference._ROOT,
            policy=evidence.EvidencePolicy(
                require_raw_rows=True,
                require_trial_run_identity=True,
                require_budget_agreement=True,
            ),
        )


@pytest.mark.skipif(
    not target_echo_reference.DEFAULT_EMITTER.is_file()
    or not target_echo_reference.DEFAULT_RUNNER.is_file(),
    reason="built Malbolge binaries not available",
)
def test_producer_rejects_forged_graphical_source_and_vm_agreement(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A fake source and fake expected stdout cannot claim target emission."""
    directories: list[Path] = []
    real_prepare = target_echo_reference._prepare_context

    def recorded(emitter: Path, runner: Path) -> target_echo_reference._Context:
        context = real_prepare(emitter, runner)
        directories.append(context.directory)
        return context

    def forged(command: list[str]) -> sp.CompletedProcess[bytes]:
        if OUTPUT_ARGUMENT in command:
            output = Path(command[command.index(OUTPUT_ARGUMENT) + 1])
            operations = command[command.index("--") + 1 :]
            output.write_bytes(b"!" * len(operations))
            return sp.CompletedProcess(command, 0, stdout=b"", stderr=b"")
        return sp.CompletedProcess(
            command,
            0,
            stdout=bytes([target_echo_reference.CLASSIC_EOF_BYTE]),
            stderr=b"",
        )

    monkeypatch.setattr(target_echo_reference, "_prepare_context", recorded)
    monkeypatch.setattr(target_echo_reference, "_invoke", forged)
    try:
        with pytest.raises(
            target_echo_reference.TargetEchoStudyError,
            match="source instruction",
        ):
            target_echo_reference.run_study(
                target_echo_reference.StudyPlan((1,), 1)
            )
    finally:
        for directory in directories:
            shutil.rmtree(directory)


@pytest.mark.skipif(
    not target_echo_reference.DEFAULT_EMITTER.is_file(),
    reason="built Malbolge layout emitter missing",
)
def test_flooding_vm_is_recorded_as_tool_failure_not_verified(
    tmp_path: Path,
) -> None:
    """Successful child exit with huge stdout must not certify a trial."""
    script = tmp_path / "flood-runner"
    script.write_text(
        f"#!{sys.executable}\nimport os\nos.write(1, b'Z' * 8192)\n"
    )
    script.chmod(0o700)
    with tempfile.TemporaryDirectory(
        dir=target_echo_reference._TEMP,
        prefix="arena-target-test-tools-",
    ) as tool_directory:
        emitter = Path(tool_directory) / "malbolge_layout"
        emitter.hardlink_to(target_echo_reference.DEFAULT_EMITTER)
        directory, document = target_echo_reference.run_study(
            target_echo_reference.StudyPlan((1,), 1),
            emitter=emitter,
            runner=script,
        )
    try:
        assert all(
            row["outcome"] == TOOL_FAILED for row in document["observations"]
        )
        assert all(
            ARTIFACT_BYTES not in row["metrics"]
            for row in document["observations"]
        )
        assert not analyze.analyze(document)["pareto_frontiers"][0][
            "algorithms"
        ]
    finally:
        shutil.rmtree(directory)


@pytest.mark.parametrize(
    "plan",
    [
        target_echo_reference.StudyPlan((), 1),
        target_echo_reference.StudyPlan((1, 1), 1),
        target_echo_reference.StudyPlan((0,), 1),
        target_echo_reference.StudyPlan((65,), 1),
        target_echo_reference.StudyPlan((1,), 0),
        target_echo_reference.StudyPlan((1,), 4),
        target_echo_reference.StudyPlan((True,), 1),
        target_echo_reference.StudyPlan((1,), BOOL_TRIAL_ALIAS),
    ],
)
def test_invalid_plan_refuses_before_creating_study(
    plan: target_echo_reference.StudyPlan,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unsupported shapes and bool aliases must never launch a target child."""

    def forbidden(*args: object, **kwargs: object) -> None:
        _ = (args, kwargs)
        message = "target study was launched"
        raise AssertionError(message)

    monkeypatch.setattr(target_echo_reference, "_prepare_context", forbidden)
    with pytest.raises(
        target_echo_reference.TargetEchoStudyError, match="target echo"
    ):
        target_echo_reference.run_study(plan)


@pytest.mark.skipif(
    not target_echo_reference.DEFAULT_EMITTER.is_file(),
    reason="built Malbolge layout emitter missing",
)
@pytest.mark.parametrize(
    ("wrong_output", "expected_outcome"),
    [(b"Z", analyze.VERIFIER_REJECTED), (b"", analyze.VERIFIER_REJECTED)],
)
def test_wrong_external_vm_output_retains_failed_trial_not_success(
    tmp_path: Path,
    wrong_output: bytes,
    expected_outcome: str,
) -> None:
    """A forged or missing EOF byte cannot claim a verified Malbolge result."""
    runner = tmp_path / "incorrect-runner"
    _ = runner.write_bytes(b"#!/bin/sh\nprintf '" + wrong_output + b"'\n")
    runner.chmod(0o700)
    with tempfile.TemporaryDirectory(
        dir=target_echo_reference._TEMP,
        prefix="arena-target-test-tools-",
    ) as tool_directory:
        emitter = Path(tool_directory) / "malbolge_layout"
        emitter.hardlink_to(target_echo_reference.DEFAULT_EMITTER)
        directory, document = target_echo_reference.run_study(
            target_echo_reference.StudyPlan((1,), 1),
            emitter=emitter,
            runner=runner,
        )
    try:
        assert all(
            row["outcome"] == expected_outcome
            for row in document["observations"]
        )
        assert all(
            ARTIFACT_BYTES not in row["metrics"]
            for row in document["observations"]
        )
        report = analyze.analyze(document)
        assert report["pareto_frontiers"][0]["algorithms"] == []
        assert json.loads((directory / "study.json").read_text()) == document
    finally:
        shutil.rmtree(directory)
