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
import os
import shutil
import subprocess as sp  # ruff: ignore[suspicious-subprocess-import]
import sys
import tempfile
from hashlib import sha256
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import pytest

from benchmarks.arena import analyze, evidence, target_echo_audit, target_echo_reference
from benchmarks.arena.tests.test_evidence import sample_study

if TYPE_CHECKING:
    from collections.abc import Iterator


RAW_TAMPER = "raw"
STUDY_LEAF = "study.json"
ORIGINAL_TRIAL = "trial = 0"
EXPECTED_OBSERVATIONS = 8
EXPECTED_LEVELS = 2
EXPECTED_TRIALS = 2
SINGLE_PAIRED_TRIAL_ARMS = 2
ARTIFACT_BYTES = "artifact_bytes"
GRAPHICAL_LOW = 33
GRAPHICAL_HIGH = 126
BOOL_TRIAL_ALIAS = True
OUTPUT_ARGUMENT = "--output"
TOOL_FAILED = "tool_failed"
FORGED_COUNT = 999
EXPECTED_STEP_RECEIPT = 3
RUNTIME_STEPS = "runtime_steps"
PATTERNED_LEVEL_COUNT = 4
PATTERNED_MAX_PAIR_COUNT = 64
PATTERNED_DIRECT_BYTES = 131
PATTERNED_PADDED_BYTES = 196


@pytest.mark.skipif(
    not hasattr(os, "mkfifo") or not getattr(os, "O_NONBLOCK", 0),
    reason="FIFO test needs POSIX nonblocking descriptor opens",
)
def test_tool_fingerprint_rejects_fifo_substitution_without_blocking(
    tmp_path: Path,
) -> None:
    """An admitted executable replaced by a FIFO fails before stream reads."""
    emitter = tmp_path / "emitter"
    runner = tmp_path / "runner"
    _ = emitter.write_bytes(b"trusted-emitter")
    _ = runner.write_bytes(b"trusted-runner")
    emitter.unlink()
    mkfifo = getattr(os, "mkfifo", None)
    assert callable(mkfifo)
    mkfifo(emitter)
    with pytest.raises(target_echo_reference.TargetEchoStudyError, match="target echo executable identity changed"):
        target_echo_reference._tool_identity(emitter, runner)


def test_tool_fingerprint_preserves_stable_byte_identity(tmp_path: Path) -> None:
    """Descriptor hashing preserves existing size-prefixed toolchain digests."""
    emitter = tmp_path / "emitter"
    runner = tmp_path / "runner"
    emitter_bytes = b"trusted-emitter"
    runner_bytes = b"trusted-runner"
    _ = emitter.write_bytes(emitter_bytes)
    _ = runner.write_bytes(runner_bytes)
    expected = sha256()
    for data in (emitter_bytes, runner_bytes):
        expected.update(len(data).to_bytes(8, "big"))
        expected.update(data)
    assert target_echo_reference._tool_identity(emitter, runner) == (
        "local-compiler-vm-sha256:" + expected.hexdigest()
    )


def test_tool_fingerprint_rejects_symlink_substitution_after_admission(
    tmp_path: Path,
) -> None:
    """A linked executable cannot impersonate a previously admitted tool."""
    emitter = tmp_path / "emitter"
    runner = tmp_path / "runner"
    foreign = tmp_path / "foreign"
    _ = emitter.write_bytes(b"trusted-emitter")
    _ = runner.write_bytes(b"trusted-runner")
    _ = foreign.write_bytes(b"foreign-emitter")
    assert target_echo_reference._admit_executable(emitter) == emitter
    emitter.unlink()
    emitter.symlink_to(foreign)
    with pytest.raises(target_echo_reference.TargetEchoStudyError, match="target echo executable identity changed"):
        target_echo_reference._tool_identity(emitter, runner)


@pytest.mark.parametrize(
    "receipt",
    [
        b"",
        b"malbolge-steps-v1:\n",
        b"malbolge-steps-v1:01\n",
        b"malbolge-steps-v1:-1\n",
        b"malbolge-steps-v1:1.0\n",
        b"malbolge-steps-v1:1\r\n",
        b"malbolge-steps-v1:3\nmalbolge-steps-v1:4\n",
        b"malbolge-steps-v1:3\nnoise",
        b"malbolge-steps-v1:999999999999999999999\n",
        b"malbolge-steps-v1:\xff\n",
    ],
)
def test_vm_step_receipt_rejects_ambiguous_or_unbounded_counter(
    receipt: bytes,
) -> None:
    """No extra diagnostics or alternate decimal spellings certify steps."""
    with pytest.raises(
        target_echo_reference.TargetEchoStudyError,
        match=r"step receipt|step count",
    ):
        target_echo_reference._parse_step_receipt(receipt)


def test_vm_step_receipt_admits_one_canonical_decimal() -> None:
    """Canonical reporter wire bytes remain reproducible."""
    assert (
        target_echo_reference._parse_step_receipt(b"malbolge-steps-v1:3\n")
        == EXPECTED_STEP_RECEIPT
    )


@pytest.mark.parametrize("tamper_after_audit", [False, True])
def test_publisher_uses_exact_audited_study_bytes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    tamper_after_audit: bool,
) -> None:
    """A later valid JSON rewrite cannot replace independently audited bytes."""
    original = sample_study(tmp_path)
    path = tmp_path / STUDY_LEAF
    raw = (json.dumps(original) + "\n").encode("utf-8")
    _ = path.write_bytes(raw)
    expected_hash = sha256(raw).hexdigest()
    monkeypatch.setattr(target_echo_reference, "_ROOT", tmp_path)

    def fake_audit(relative: str) -> dict[str, Any]:
        assert relative == STUDY_LEAF
        if tamper_after_audit:
            altered = json.loads(raw)
            altered["study"]["id"] = "valid-but-not-audited"
            _ = path.write_text(json.dumps(altered), encoding="utf-8")
        return {"retained_study_sha256": expected_hash}

    monkeypatch.setattr(target_echo_audit, "audit", fake_audit)
    if tamper_after_audit:
        with pytest.raises(
            target_echo_reference.TargetEchoStudyError,
            match="changed after independent audit",
        ):
            target_echo_reference._audit_retained_study(path)
    else:
        assert target_echo_reference._audit_retained_study(path) == original


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
        # Private inodes avoid shared tool ctime churn as other tests create
        # and remove hardlinks, without relaxing production identity checks.
        shutil.copy2(target_echo_reference.DEFAULT_EMITTER, emitter)
        shutil.copy2(target_echo_reference.DEFAULT_RUNNER, runner)
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
def test_missing_counter_with_correct_vm_output_is_instrumentation_failure(
    tmp_path: Path,
) -> None:
    """Failure to report VM steps is tool failure, not a guest rejection."""
    runner = tmp_path / "no-counter-vm"
    runner.write_text(
        f"#!{sys.executable}\n"
        "import sys\n"
        "sys.stdout.buffer.write(bytes([0,168]))\n"
    )
    runner.chmod(0o700)
    with tempfile.TemporaryDirectory(
        dir=target_echo_reference._TEMP, prefix="arena-steps-test-tools-"
    ) as tool_directory:
        emitter = Path(tool_directory) / "malbolge_layout"
        shutil.copy2(target_echo_reference.DEFAULT_EMITTER, emitter)
        directory, document = target_echo_reference.run_study(
            target_echo_reference.StudyPlan(
                (1,),
                1,
                target_echo_reference.PATTERNED_MODE,
                measure_steps=True,
            ),
            emitter=emitter,
            runner=runner,
        )
    try:
        assert all(
            row["outcome"] == TOOL_FAILED for row in document["observations"]
        )
        assert all(
            RUNTIME_STEPS not in row["metrics"]
            for row in document["observations"]
        )
        assert all(
            ARTIFACT_BYTES not in row["metrics"]
            for row in document["observations"]
        )
    finally:
        shutil.rmtree(directory)


@pytest.mark.skipif(
    not target_echo_reference.DEFAULT_EMITTER.is_file(),
    reason="built Malbolge layout emitter missing",
)
def test_wrong_external_vm_step_receipt_does_not_publish_success(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Plausible stdout and consistent reported counters cannot bypass audit."""
    runner = tmp_path / "forged-counter-vm"
    runner.write_text(
        f"#!{sys.executable}\n"
        "import sys\n"
        "sys.stdout.buffer.write(bytes([0,168]))\n"
        "sys.stderr.buffer.write(b'malbolge-steps-v1:999\\n')\n"
    )
    runner.chmod(0o700)
    directories: list[Path] = []
    original = target_echo_reference._prepare_context

    def capture_context(
        emitter: Path, vm: Path
    ) -> target_echo_reference._Context:
        context = original(emitter, vm)
        directories.append(context.directory)
        return context

    monkeypatch.setattr(
        target_echo_reference, "_prepare_context", capture_context
    )
    with tempfile.TemporaryDirectory(
        dir=target_echo_reference._TEMP,
        prefix="arena-steps-test-tools-",
    ) as tool_directory:
        emitter = Path(tool_directory) / "malbolge_layout"
        shutil.copy2(target_echo_reference.DEFAULT_EMITTER, emitter)
        try:
            with pytest.raises(
                target_echo_reference.TargetEchoStudyError,
                match="runtime step claim",
            ):
                target_echo_reference.run_study(
                    target_echo_reference.StudyPlan(
                        (1,),
                        1,
                        target_echo_reference.PATTERNED_MODE,
                        measure_steps=True,
                    ),
                    emitter=emitter,
                    runner=runner,
                )
            assert len(directories) == 1
            rows = json.loads(
                (directories[0] / "study.json").read_text(encoding="utf-8")
            )["observations"]
            assert all(row["outcome"] == analyze.VERIFIED for row in rows)
            assert all(
                row["metrics"]["runtime_steps"] == FORGED_COUNT for row in rows
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
        shutil.copy2(target_echo_reference.DEFAULT_EMITTER, emitter)
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


@pytest.mark.skipif(
    not target_echo_reference.DEFAULT_EMITTER.is_file()
    or not target_echo_reference.DEFAULT_RUNNER.is_file(),
    reason="built Malbolge CLI binaries not available",
)
def test_patterned_mode_records_true_non_eof_input_and_final_eof() -> None:
    """Real target measurements use actual NUL/high-bit input and then EOF."""
    with tempfile.TemporaryDirectory(
        dir=target_echo_reference._TEMP,
        prefix="arena-patterned-test-tools-",
    ) as tool_directory:
        emitter = Path(tool_directory) / "malbolge_layout"
        runner = Path(tool_directory) / "malbolge"
        shutil.copy2(target_echo_reference.DEFAULT_EMITTER, emitter)
        shutil.copy2(target_echo_reference.DEFAULT_RUNNER, runner)
        directory, document = target_echo_reference.run_study(
            target_echo_reference.StudyPlan(
                (1, 4, 16, 64), 1, target_echo_reference.PATTERNED_MODE
            ),
            emitter=emitter,
            runner=runner,
        )
        try:
            rows = document["observations"]
            assert len(rows) == EXPECTED_OBSERVATIONS
            assert all(row["outcome"] == analyze.VERIFIED for row in rows)
            assert all(
                row["verifier_verdict"] == analyze.ACCEPTED for row in rows
            )
            assert (
                document["study"]["id"] == target_echo_reference.PATTERNED_STUDY
            )
            assert (
                len(analyze.analyze(document)["pareto_frontiers"])
                == PATTERNED_LEVEL_COUNT
            )
            assert {
                row["algorithm"]: row["metrics"][ARTIFACT_BYTES]
                for row in rows
                if row["case"]["difficulty"] == PATTERNED_MAX_PAIR_COUNT
            } == {
                target_echo_reference.BASELINE: PATTERNED_DIRECT_BYTES,
                target_echo_reference.CANDIDATE: PATTERNED_PADDED_BYTES,
            }
        finally:
            shutil.rmtree(directory)


@pytest.mark.skipif(
    not target_echo_reference.DEFAULT_EMITTER.is_file(),
    reason="built Malbolge layout emitter missing",
)
def test_patterned_vm_that_ignores_input_retains_verifier_rejection(
    tmp_path: Path,
) -> None:
    """EOF-only output must not certify the varied-byte guest program."""
    runner = tmp_path / "eof-only-runner"
    runner.write_bytes(b"#!/bin/sh\nprintf 'Z'\n")
    runner.chmod(0o700)
    with tempfile.TemporaryDirectory(
        dir=target_echo_reference._TEMP,
        prefix="arena-patterned-test-tools-",
    ) as tool_directory:
        emitter = Path(tool_directory) / "malbolge_layout"
        shutil.copy2(target_echo_reference.DEFAULT_EMITTER, emitter)
        directory, document = target_echo_reference.run_study(
            target_echo_reference.StudyPlan(
                (1,), 1, target_echo_reference.PATTERNED_MODE
            ),
            emitter=emitter,
            runner=runner,
        )
    try:
        assert all(
            row["outcome"] == analyze.VERIFIER_REJECTED
            for row in document["observations"]
        )
        assert all(
            ARTIFACT_BYTES not in row["metrics"]
            for row in document["observations"]
        )
        assert (
            analyze.analyze(document)["pareto_frontiers"][0]["algorithms"] == []
        )
    finally:
        shutil.rmtree(directory)


@pytest.mark.skipif(
    not target_echo_reference.DEFAULT_EMITTER.is_file()
    or not target_echo_reference.DEFAULT_RUNNER.is_file(),
    reason="built Malbolge CLI binaries not available",
)
def test_changed_producer_pattern_fails_independent_oracle_even_if_linked(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Self-consistent producer input drift cannot pass the fixed auditor."""
    original_pattern = target_echo_reference.PATTERN_BYTES
    monkeypatch.setattr(
        target_echo_reference,
        "PATTERN_BYTES",
        (1, *original_pattern[1:]),
    )
    original_prepare = target_echo_reference._prepare_context
    directories: list[Path] = []

    def capture_context(
        emitter: Path, runner: Path
    ) -> target_echo_reference._Context:
        context = original_prepare(emitter, runner)
        directories.append(context.directory)
        return context

    monkeypatch.setattr(
        target_echo_reference, "_prepare_context", capture_context
    )
    with tempfile.TemporaryDirectory(
        dir=target_echo_reference._TEMP,
        prefix="arena-patterned-test-tools-",
    ) as tool_directory:
        emitter = Path(tool_directory) / "malbolge_layout"
        runner = Path(tool_directory) / "malbolge"
        shutil.copy2(target_echo_reference.DEFAULT_EMITTER, emitter)
        shutil.copy2(target_echo_reference.DEFAULT_RUNNER, runner)
        try:
            with pytest.raises(
                target_echo_reference.TargetEchoStudyError,
                match="fixed echo case",
            ):
                target_echo_reference.run_study(
                    target_echo_reference.StudyPlan(
                        (1,), 1, target_echo_reference.PATTERNED_MODE
                    ),
                    emitter=emitter,
                    runner=runner,
                )
            assert len(directories) == 1
            document = analyze.parse_document(
                (directories[0] / "study.json").read_text(encoding="utf-8")
            )
            checked = evidence.validate_links(
                document,
                target_echo_reference._ROOT,
                policy=evidence.EvidencePolicy(
                    require_raw_rows=True,
                    require_trial_run_identity=True,
                    require_budget_agreement=True,
                ),
            )
            assert checked["raw_rows_matched"] == len(document["observations"])
        finally:
            for directory in directories:
                shutil.rmtree(directory)


@pytest.mark.skipif(
    not target_echo_reference.DEFAULT_EMITTER.is_file()
    or not target_echo_reference.DEFAULT_RUNNER.is_file(),
    reason="built Malbolge tools required",
)
@pytest.mark.parametrize("expected", [analyze.VERIFIER_REJECTED, "tool_failed"])
def test_timed_independent_verifier_failure_cannot_record_verified_cost(
    expected: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verification rejection and I/O failure retain distinct outcomes."""
    original = target_echo_reference._timed_source_verifier

    def selective_failure(path: Path, pairs: int, algorithm: str) -> int:
        if algorithm == target_echo_reference.SKIP:
            if expected == analyze.VERIFIER_REJECTED:
                raise target_echo_audit.TargetEchoAuditError
            raise OSError
        return original(path, pairs, algorithm)

    monkeypatch.setattr(
        target_echo_reference, "_timed_source_verifier", selective_failure
    )
    with tempfile.TemporaryDirectory(
        dir=target_echo_reference._TEMP,
        prefix="arena-verifier-failure-test-",
    ) as tools:
        emitter = Path(tools) / "malbolge_layout"
        runner = Path(tools) / "malbolge"
        shutil.copy2(target_echo_reference.DEFAULT_EMITTER, emitter)
        shutil.copy2(target_echo_reference.DEFAULT_RUNNER, runner)
        directory, document = target_echo_reference.run_study(
            target_echo_reference.StudyPlan(
                (1,),
                1,
                target_echo_reference.PATTERNED_MODE,
                measure_steps=True,
                layout_mode=target_echo_reference.FORWARD_SKIP_LAYOUT,
                measure_verifier=True,
            ),
            emitter=emitter,
            runner=runner,
        )
        try:
            outcomes = {
                row["algorithm"]: row for row in document["observations"]
            }
            assert (
                outcomes[target_echo_reference.WALK]["outcome"]
                == analyze.VERIFIED
            )
            assert outcomes[target_echo_reference.SKIP]["outcome"] == expected
            failed = outcomes[target_echo_reference.SKIP]
            assert failed["metrics"].keys() == {"elapsed_ns"}
            assert failed["verifier_verdict"] == (
                analyze.REJECTED
                if expected == analyze.VERIFIER_REJECTED
                else analyze.NOT_RUN
            )
            assert (
                target_echo_audit.audit(
                    (directory / "study.json")
                    .relative_to(target_echo_reference._ROOT)
                    .as_posix()
                )["reported_failed_trials_not_replayed"]
                == 1
            )
        finally:
            shutil.rmtree(directory)


@pytest.mark.skipif(
    not target_echo_reference.DEFAULT_EMITTER.is_file()
    or not target_echo_reference.DEFAULT_RUNNER.is_file(),
    reason="built Malbolge tools required",
)
def test_real_postexecution_source_mutation_is_independently_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Correct VM stdout cannot admit a source changed before verification."""
    original = target_echo_reference._timed_source_verifier

    def mutate_skipped_cell(path: Path, pairs: int, algorithm: str) -> int:
        if algorithm == target_echo_reference.SKIP:
            source = bytearray(path.read_bytes())
            skipped_position = target_echo_reference.SKIPPED_NOOPS // 2
            source[skipped_position] = (
                GRAPHICAL_LOW
                if source[skipped_position] != GRAPHICAL_LOW
                else GRAPHICAL_LOW + 1
            )
            path.write_bytes(source)
        return original(path, pairs, algorithm)

    monkeypatch.setattr(
        target_echo_reference, "_timed_source_verifier", mutate_skipped_cell
    )
    with tempfile.TemporaryDirectory(
        dir=target_echo_reference._TEMP,
        prefix="arena-verifier-mutation-test-",
    ) as tools:
        emitter = Path(tools) / "malbolge_layout"
        runner = Path(tools) / "malbolge"
        shutil.copy2(target_echo_reference.DEFAULT_EMITTER, emitter)
        shutil.copy2(target_echo_reference.DEFAULT_RUNNER, runner)
        directory, document = target_echo_reference.run_study(
            target_echo_reference.StudyPlan(
                (1,),
                1,
                target_echo_reference.PATTERNED_MODE,
                measure_steps=True,
                layout_mode=target_echo_reference.FORWARD_SKIP_LAYOUT,
                measure_verifier=True,
            ),
            emitter=emitter,
            runner=runner,
        )
        try:
            assert [row["outcome"] for row in document["observations"]] == [
                analyze.VERIFIED,
                analyze.VERIFIER_REJECTED,
            ]
            assert document["observations"][1]["metrics"].keys() == {
                "elapsed_ns"
            }
            checked = target_echo_audit.audit(
                (directory / "study.json")
                .relative_to(target_echo_reference._ROOT)
                .as_posix()
            )
            assert checked["verified_target_sources_checked"] == 1
            assert checked["reported_failed_trials_not_replayed"] == 1
        finally:
            shutil.rmtree(directory)


@pytest.mark.skipif(
    not target_echo_reference.DEFAULT_EMITTER.is_file()
    or not target_echo_reference.DEFAULT_RUNNER.is_file(),
    reason="built Malbolge tools required",
)
@pytest.mark.parametrize(
    "mode",
    [
        target_echo_reference.SOURCE_VERIFIER_MODE,
        target_echo_reference.REPLAY_VERIFIER_MODE,
    ],
)
def test_cli_opt_in_verifier_cost_publishes_four_objective_study(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    mode: str,
) -> None:
    """Operator flags reach the selected verifier-cost stage and raw audit."""
    original = target_echo_reference.run_study
    generated: list[Path] = []
    with tempfile.TemporaryDirectory(
        dir=target_echo_reference._TEMP, prefix="arena-verifier-cli-tools-"
    ) as tools:
        emitter = Path(tools) / "malbolge_layout"
        runner = Path(tools) / "malbolge"
        shutil.copy2(target_echo_reference.DEFAULT_EMITTER, emitter)
        shutil.copy2(target_echo_reference.DEFAULT_RUNNER, runner)

        def route(
            plan: target_echo_reference.StudyPlan,
        ) -> tuple[Path, dict[str, Any]]:
            result = original(plan, emitter=emitter, runner=runner)
            generated.append(result[0])
            return result

        monkeypatch.setattr(target_echo_reference, "run_study", route)
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "target-echo",
                "--pairs",
                "1",
                "--trials",
                "1",
                "--input-mode",
                "patterned",
                "--measure-steps",
                "--layout-mode",
                "forward-skip",
                "--measure-verifier",
                "--verifier-mode",
                mode,
            ],
        )
        try:
            assert target_echo_reference.main() == 0
            output = json.loads(capsys.readouterr().out)
            relative = output["study"]
            study = json.loads(
                (target_echo_reference._ROOT / relative).read_text()
            )
            assert study["study"]["id"] == (
                target_echo_reference.FORWARD_REPLAY_COST_STUDY
                if mode == target_echo_reference.REPLAY_VERIFIER_MODE
                else target_echo_reference.FORWARD_VERIFIER_COST_STUDY
            )
            assert all(
                target_echo_reference.VERIFIER_NS in row["metrics"]
                for row in study["observations"]
            )
            checked = target_echo_audit.audit(
                relative,
                options=target_echo_audit.AuditOptions(
                    replay_candidates=True, emitter=emitter, runner=runner
                ),
            )
            assert (
                checked["target_sources_replayed"] == SINGLE_PAIRED_TRIAL_ARMS
            )
        finally:
            for directory in generated:
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
        target_echo_reference.StudyPlan((1,), 1, "arbitrary"),
        target_echo_reference.StudyPlan((1,), 1, cast("str", BOOL_TRIAL_ALIAS)),
        target_echo_reference.StudyPlan(
            (1,), 1, target_echo_reference.EOF_MODE, cast("bool", 1)
        ),
        target_echo_reference.StudyPlan(
            (1,),
            1,
            target_echo_reference.EOF_MODE,
            measure_verifier=True,
        ),
        target_echo_reference.StudyPlan(
            (1,),
            1,
            target_echo_reference.PATTERNED_MODE,
            measure_steps=True,
            layout_mode=target_echo_reference.FORWARD_SKIP_LAYOUT,
            measure_verifier=cast("bool", 1),
        ),
        target_echo_reference.StudyPlan(
            (1,),
            1,
            target_echo_reference.PATTERNED_MODE,
            measure_steps=True,
            layout_mode=target_echo_reference.LINEAR_LAYOUT,
            measure_verifier=True,
        ),
        target_echo_reference.StudyPlan(
            (1,),
            1,
            target_echo_reference.PATTERNED_MODE,
            measure_steps=True,
            layout_mode=target_echo_reference.FORWARD_SKIP_LAYOUT,
            verifier_mode=target_echo_reference.REPLAY_VERIFIER_MODE,
        ),
        target_echo_reference.StudyPlan(
            (1,),
            1,
            target_echo_reference.PATTERNED_MODE,
            measure_steps=True,
            layout_mode=target_echo_reference.FORWARD_SKIP_LAYOUT,
            measure_verifier=True,
            verifier_mode="unknown",
        ),
        target_echo_reference.StudyPlan(
            (1,),
            1,
            target_echo_reference.PATTERNED_MODE,
            measure_steps=True,
            layout_mode=target_echo_reference.FORWARD_SKIP_LAYOUT,
            measure_verifier=True,
            verifier_mode=cast("str", BOOL_TRIAL_ALIAS),
        ),
        target_echo_reference.StudyPlan(
            (1,),
            1,
            target_echo_reference.PATTERNED_MODE,
            measure_steps=True,
            layout_mode=target_echo_reference.FORWARD_SKIP_LAYOUT,
            limit_child_resources=True,
        ),
        target_echo_reference.StudyPlan(
            (1,),
            1,
            target_echo_reference.PATTERNED_MODE,
            measure_steps=True,
            layout_mode=target_echo_reference.FORWARD_SKIP_LAYOUT,
            measure_verifier=True,
            limit_child_resources=True,
        ),
        target_echo_reference.StudyPlan(
            (1,),
            1,
            target_echo_reference.PATTERNED_MODE,
            measure_steps=True,
            layout_mode=target_echo_reference.FORWARD_SKIP_LAYOUT,
            measure_verifier=True,
            verifier_mode=target_echo_reference.REPLAY_VERIFIER_MODE,
            limit_child_resources=cast("bool", 1),
        ),
        target_echo_reference.StudyPlan((1,), BOOL_TRIAL_ALIAS),
        target_echo_reference.StudyPlan(
            (1,),
            1,
            target_echo_reference.EOF_MODE,
            measure_steps=True,
            layout_mode=target_echo_reference.FORWARD_SKIP_LAYOUT,
        ),
        target_echo_reference.StudyPlan(
            (1,),
            1,
            target_echo_reference.PATTERNED_MODE,
            layout_mode=target_echo_reference.FORWARD_SKIP_LAYOUT,
        ),
        target_echo_reference.StudyPlan(
            (1,),
            1,
            target_echo_reference.PATTERNED_MODE,
            measure_steps=True,
            layout_mode="unknown",
        ),
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
        shutil.copy2(target_echo_reference.DEFAULT_EMITTER, emitter)
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
