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
#   - Real second-VM verifier-cost failure and post-execution tests.
# - Must-Not:
#   - Equate a repeat run on one VM with independent engine verification.
# - Allows:
#   - Inputs: bounded pinned classic emitters/runners and injected receipts.
#   - Outputs: fail-closed target verdict and complete linked-run evidence.
#   - Side effects: short-lived own ignored candidate studies.
# - Split-When:
#   - The arena supports more general guest control-flow verifiers.
# - Merge-When:
#   - One independently specified replay-verifier harness owns this protocol.
# - Summary:
#   - A second VM must do real work and reject altered guest outputs/steps.
# - Description:
#   - Failure injection occurs only after one original, correct VM execution.
# - Usage:
#   - pytest benchmarks/arena/tests/test_target_echo_replay_verifier.py.
# - Defaults:
#   - Requires POSIX and built Malbolge emitter and VM executables.
#

"""Real source-and-second-VM replay verification and cost admission tests."""

# ruff: file-ignore[assert,private-member-access]

from __future__ import annotations

from collections import Counter
import json
import os
from pathlib import Path
from shlex import quote
import shutil
import subprocess as sp  # ruff: ignore[suspicious-subprocess-import]
import tempfile
from typing import Any
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator

import pytest

from benchmarks.arena import analyze
from benchmarks.arena import target_echo_audit as audit
from benchmarks.arena import target_echo_reference as producer
from benchmarks.arena import target_process

POSIX = "posix"
WRONG_OUTPUT = "wrong-output"
MISSING_STEPS = "missing-steps"
WRONG_STEPS = "wrong-steps"
BAD_EXIT = "bad-exit"
TIMEOUT = "timeout"
REPLAY_MODES = (WRONG_OUTPUT, MISSING_STEPS, WRONG_STEPS, BAD_EXIT, TIMEOUT)
JUMP_NAME = "jump-skip-padding-echo"
TWO_EXECUTIONS = 2
TRIAL_COUNT = 2
EXACT_DIFFICULTIES = (1, 4, 16, 64)
EXPECTED_SAVING = 98
VERIFIER_COST_METRIC = "verifier_ns"

pytestmark = pytest.mark.skipif(
    os.name != POSIX
    or not producer.DEFAULT_EMITTER.is_file()
    or not producer.DEFAULT_RUNNER.is_file(),
    reason="requires POSIX with built classic emitter and VM",
)


@pytest.fixture
def pinned_tools() -> Iterator[tuple[Path, Path]]:
    """Hold exact actual emitter/VM executable inodes across rebuilds.

    Yields:
        Pinned emitter and runner.

    """
    with tempfile.TemporaryDirectory(
        dir=producer._TEMP, prefix="arena-replay-cost-tool-test-"
    ) as folder:
        emitter = Path(folder) / "malbolge_layout"
        runner = Path(folder) / "malbolge"
        # Private copies avoid shared executable ctime drift across tests.
        shutil.copy2(producer.DEFAULT_EMITTER, emitter)
        shutil.copy2(producer.DEFAULT_RUNNER, runner)
        yield emitter, runner


def _real_study(
    tools: tuple[Path, Path], *, levels: tuple[int, ...] = (1,)
) -> tuple[Path, dict[str, Any], str]:
    directory, document = producer.run_study(
        producer.StudyPlan(
            levels,
            1,
            producer.PATTERNED_MODE,
            measure_steps=True,
            layout_mode=producer.FORWARD_SKIP_LAYOUT,
            measure_verifier=True,
            verifier_mode=producer.REPLAY_VERIFIER_MODE,
        ),
        emitter=tools[0],
        runner=tools[1],
    )
    relative = (directory / "study.json").relative_to(producer._ROOT)
    return directory, document, relative.as_posix()


def _forged_second_result(
    failure: str, result: sp.CompletedProcess[bytes]
) -> sp.CompletedProcess[bytes]:
    status, output, receipt = result.returncode, result.stdout, result.stderr
    if failure == WRONG_OUTPUT:
        output = b"not-the-byte-oracle"
    elif failure == MISSING_STEPS:
        receipt = b""
    elif failure == WRONG_STEPS:
        receipt = b"malbolge-steps-v1:999\n"
    else:
        status = 9
    return sp.CompletedProcess(result.args, status, output, receipt)


@pytest.mark.parametrize("failure", REPLAY_MODES)
def test_second_execution_failure_is_never_reported_as_verified(
    pinned_tools: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
    failure: str,
) -> None:
    """A correct first VM result must not certify a failing second VM."""
    original = target_process.invoke_with_input
    counts: Counter[str] = Counter()

    def patched(
        command: list[str], data: bytes, *, timeout_seconds: float
    ) -> sp.CompletedProcess[bytes]:
        candidate = command[1]
        counts[candidate] += 1
        if JUMP_NAME in candidate and counts[candidate] == TWO_EXECUTIONS:
            if failure == TIMEOUT:
                raise sp.TimeoutExpired(command, timeout_seconds)
            return _forged_second_result(
                failure,
                original(command, data, timeout_seconds=timeout_seconds),
            )
        return original(command, data, timeout_seconds=timeout_seconds)

    monkeypatch.setattr(target_process, "invoke_with_input", patched)
    directory, document, relative = _real_study(pinned_tools)
    try:
        rows = {row["algorithm"]: row for row in document["observations"]}
        expected = (
            analyze.VERIFIER_REJECTED
            if failure == WRONG_OUTPUT
            else "tool_failed"
        )
        assert rows[producer.WALK]["outcome"] == analyze.VERIFIED
        assert rows[producer.SKIP]["outcome"] == expected
        assert rows[producer.SKIP]["metrics"].keys() == {"elapsed_ns"}
        assert sorted(counts.values()) == [TWO_EXECUTIONS] * TRIAL_COUNT
        checked = audit.audit(relative)
        assert checked["verified_target_sources_checked"] == 1
        assert checked["reported_failed_trials_not_replayed"] == 1
    finally:
        shutil.rmtree(directory)


def test_second_execution_source_rewrite_rejects_after_guest_success(
    pinned_tools: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Post-run source tampering invalidates a correct byte/step receipt."""
    original = target_process.invoke_with_input
    counts: Counter[str] = Counter()

    def rewrite_after_success(
        command: list[str], data: bytes, *, timeout_seconds: float
    ) -> sp.CompletedProcess[bytes]:
        result = original(command, data, timeout_seconds=timeout_seconds)
        candidate = command[1]
        counts[candidate] += 1
        if JUMP_NAME in candidate and counts[candidate] == TWO_EXECUTIONS:
            path = Path(candidate)
            changed = bytearray(path.read_bytes())
            changed[producer.SKIPPED_NOOPS // 2] = ord("!")
            path.write_bytes(changed)
        return result

    monkeypatch.setattr(
        target_process, "invoke_with_input", rewrite_after_success
    )
    directory, document, relative = _real_study(pinned_tools)
    try:
        outcomes = [row["outcome"] for row in document["observations"]]
        assert outcomes == [analyze.VERIFIED, analyze.VERIFIER_REJECTED]
        assert document["observations"][1]["metrics"].keys() == {"elapsed_ns"}
        assert audit.audit(relative)["reported_failed_trials_not_replayed"] == 1
    finally:
        shutil.rmtree(directory)


def test_second_vm_uses_fresh_exec_process_not_in_process_recheck(
    pinned_tools: tuple[Path, Path],
) -> None:
    """A wrapper records distinct OS PIDs for primary and verifier runs."""
    with tempfile.TemporaryDirectory(
        dir=producer._TEMP, prefix="arena-replay-process-proof-"
    ) as folder:
        directory = Path(folder)
        marker = directory / "runner-pids.txt"
        wrapped = directory / "vm-instrumented"
        wrapped.write_text(
            "#!/bin/sh\n"
            f"printf '%s\\n' \"$$\" >> {quote(str(marker))}\n"
            f'exec {quote(str(pinned_tools[1]))} "$@"\n',
            encoding="utf-8",
        )
        wrapped.chmod(0o700)
        retained, document, relative = _real_study((pinned_tools[0], wrapped))
        try:
            assert len(document["observations"]) == TRIAL_COUNT
            assert all(
                row["outcome"] == analyze.VERIFIED
                for row in document["observations"]
            )
            pids = [int(line) for line in marker.read_text().splitlines()]
            assert len(pids) == TWO_EXECUTIONS * TRIAL_COUNT
            assert all(pid > 0 for pid in pids)
            assert len(set(pids)) == len(pids)
            report = audit.audit(relative)
            assert report["verified_target_sources_checked"] == TRIAL_COUNT
        finally:
            shutil.rmtree(retained)


def test_real_second_execution_costs_and_paired_differences(
    pinned_tools: tuple[Path, Path],
) -> None:
    """All tested difficulties retain exact replay cost and guest work."""
    directory, document, relative = _real_study(
        pinned_tools, levels=EXACT_DIFFICULTIES
    )
    try:
        assert (
            len(document["observations"])
            == len(EXACT_DIFFICULTIES) * TRIAL_COUNT
        )
        assert document["study"]["id"] == producer.FORWARD_REPLAY_COST_STUDY
        assert all(
            0
            < row["metrics"][VERIFIER_COST_METRIC]
            <= row["metrics"]["elapsed_ns"]
            for row in document["observations"]
        )
        compared = analyze.analyze(document)["paired_baseline_comparisons"]
        assert len(compared) == len(EXACT_DIFFICULTIES)
        for pair in compared:
            assert pair["cost_differences"]["artifact_bytes"][
                "median_candidate_minus_baseline"
            ] == [0, 1]
            assert pair["cost_differences"]["runtime_steps"][
                "median_candidate_minus_baseline"
            ] == [-EXPECTED_SAVING, 1]
            assert VERIFIER_COST_METRIC in pair["cost_differences"]
        report = audit.audit(
            relative,
            options=audit.AuditOptions(
                replay_candidates=True,
                require_source_commit_object=True,
                emitter=pinned_tools[0],
                runner=pinned_tools[1],
            ),
        )
        assert report["target_sources_replayed"] == len(
            document["observations"]
        )
        assert report["source_commit_object_verified"] is True
        assert json.loads((directory / "study.json").read_text()) == document
    finally:
        shutil.rmtree(directory)
