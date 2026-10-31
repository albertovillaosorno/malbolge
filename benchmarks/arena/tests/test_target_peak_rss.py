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
#   - Real GNU time child RSS evidence and version-five target audit tests.
# - Must-Not:
#   - Claim aggregate RSS, historical attestation or a distinct VM engine.
# - Allows:
#   - Inputs: pinned local classic emitter and runner, bounded resources.
#   - Outputs: verified reported maximum across three limited child stages.
#   - Side effects: disposable ignored studies and test-owned executable copies.
# - Split-When:
#   - Generic trial measured-RSS execution replaces this classic-only pilot.
# - Merge-When:
#   - Common target resource meter owns measured guest witness admission.
# - Summary:
#   - A fifth Pareto cost must come from real capped emitter and VM processes.
# - Description:
#   - Retains raw rows, rejects false resource witnesses and protocol relabels.
# - Usage:
#   - pytest benchmarks/arena/tests/test_target_peak_rss.py.
# - Defaults:
#   - Linux, util-linux prlimit, GNU time, built classic emitter and VM.
#

"""Real bounded target RSS measurements with fail-closed evidence checks."""

# ruff: file-ignore[assert,private-member-access]

from __future__ import annotations

import copy
import json
import shutil
import sys
import tempfile
from dataclasses import replace
from pathlib import Path
from typing import TYPE_CHECKING, cast

import pytest

from benchmarks.arena import analyze, target_process
from benchmarks.arena import target_echo_audit as audit
from benchmarks.arena import target_echo_reference as producer

if TYPE_CHECKING:
    import subprocess as sp
    from collections.abc import Iterator
    from typing import Any

LINUX_PLATFORM = "linux"
LEVELS = (1, 4, 16, 64)
PAIR_ARMS = 2
MAX_CHILD_RSS_BYTES = target_process.CHILD_VIRTUAL_MEMORY_BYTES
PEAK_RSS = "peak_rss_bytes"
MISSING = "missing"
TOOL_FAILED = "tool_failed"
FIVE_COSTS = (
    "elapsed_ns",
    "artifact_bytes",
    "runtime_steps",
    "verifier_ns",
    "peak_rss_bytes",
)
EXPECTED_SAVING = -98

pytestmark = pytest.mark.skipif(
    sys.platform != LINUX_PLATFORM
    or not producer.DEFAULT_EMITTER.is_file()
    or not producer.DEFAULT_RUNNER.is_file(),
    reason="needs Linux with built classic Malbolge executable tools",
)


@pytest.fixture
def pinned_tools() -> Iterator[tuple[Path, Path]]:
    """Use independently pinned actual executable inodes for one experiment.

    Yields:
        The emitter and normative classic VM.

    """
    with tempfile.TemporaryDirectory(
        dir=producer._TEMP, prefix="arena-v5-rss-tools-"
    ) as path:
        emitter = Path(path) / "malbolge_layout"
        runner = Path(path) / "malbolge"
        # Private copies avoid shared executable ctime drift across tests.
        shutil.copy2(producer.DEFAULT_EMITTER, emitter)
        shutil.copy2(producer.DEFAULT_RUNNER, runner)
        yield emitter, runner


def _plan(*, measured: bool = True) -> producer.StudyPlan:
    return producer.StudyPlan(
        LEVELS,
        1,
        producer.PATTERNED_MODE,
        measure_steps=True,
        layout_mode=producer.FORWARD_SKIP_LAYOUT,
        measure_verifier=True,
        verifier_mode=producer.REPLAY_VERIFIER_MODE,
        limit_child_resources=True,
        measure_child_rss=measured,
    )


def _study(
    tools: tuple[Path, Path], *, measured: bool = True
) -> tuple[Path, dict[str, Any], str]:
    if shutil.which("prlimit") is None or shutil.which("time") is None:
        pytest.skip("missing Linux prlimit or GNU time")
    folder, document = producer.run_study(
        _plan(measured=measured), emitter=tools[0], runner=tools[1]
    )
    return (
        folder,
        document,
        (folder / "study.json").relative_to(producer._ROOT).as_posix(),
    )


def test_actual_fifth_pareto_rss_cost_replays_all_classic_sources(
    pinned_tools: tuple[Path, Path],
) -> None:
    """Every arm records a real resource cost and independent guest replay."""
    folder, study, relative = _study(pinned_tools)
    try:
        assert study["study"]["id"] == producer.FORWARD_RSS_STUDY
        assert tuple(study["study"]["objectives"]) == FIVE_COSTS
        assert len(study["observations"]) == len(LEVELS) * PAIR_ARMS
        for row in study["observations"]:
            assert row["verifier"] == producer.FORWARD_RSS_VERIFIER
            assert row["outcome"] == analyze.VERIFIED
            costs = row["metrics"]
            assert 0 < costs["peak_rss_bytes"] <= MAX_CHILD_RSS_BYTES
            assert costs["peak_rss_bytes"] % target_process.KIB_BYTES == 0
            assert 0 < costs["verifier_ns"] <= costs["elapsed_ns"]
        pairs = analyze.analyze(study)["paired_baseline_comparisons"]
        assert len(pairs) == len(LEVELS)
        for pair in pairs:
            assert PEAK_RSS in pair["cost_differences"]
            assert pair["cost_differences"]["runtime_steps"][
                "median_candidate_minus_baseline"
            ] == [EXPECTED_SAVING, 1]
        report = audit.audit(
            relative,
            options=audit.AuditOptions(
                replay_candidates=True,
                require_source_commit_object=True,
                emitter=pinned_tools[0],
                runner=pinned_tools[1],
            ),
        )
        assert report["target_sources_replayed"] == len(study["observations"])
        assert report["source_commit_object_verified"] is True
        assert report["evidence_preflight"]["raw_rows_matched"] == len(
            study["observations"]
        )
    finally:
        shutil.rmtree(folder)


def test_all_three_limited_child_stages_have_distinct_real_rss_receipts(
    pinned_tools: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Observed trial RSS is the max emitter, primary and replay child RSS."""
    observed: list[int] = []
    original_emitter = target_process.invoke_limited_measured
    original_guest = target_process.invoke_with_input_limited_measured

    def emitter(
        command: list[str],
        *,
        timeout_seconds: float = target_process.DEFAULT_TIMEOUT_SECONDS,
    ) -> tuple[sp.CompletedProcess[bytes], int]:
        result, peak = original_emitter(
            command, timeout_seconds=timeout_seconds
        )
        observed.append(peak)
        return result, peak

    def guest(
        command: list[str],
        data: bytes,
        *,
        timeout_seconds: float = target_process.DEFAULT_TIMEOUT_SECONDS,
    ) -> tuple[sp.CompletedProcess[bytes], int]:
        result, peak = original_guest(
            command, data, timeout_seconds=timeout_seconds
        )
        observed.append(peak)
        return result, peak

    monkeypatch.setattr(target_process, "invoke_limited_measured", emitter)
    monkeypatch.setattr(
        target_process, "invoke_with_input_limited_measured", guest
    )
    folder, study, _ = _study(pinned_tools)
    try:
        rows = study["observations"]
        assert len(observed) == len(rows) * producer.RSS_MEASURED_STAGES
        assert all(
            row["metrics"]["peak_rss_bytes"] == max(observed[index : index + 3])
            for row_index, row in enumerate(rows)
            for index in [row_index * producer.RSS_MEASURED_STAGES]
        )
    finally:
        shutil.rmtree(folder)


@pytest.mark.parametrize(
    "older",
    [
        producer.FORWARD_LIMITED_REPLAY_STUDY,
        producer.FORWARD_REPLAY_COST_STUDY,
    ],
)
def test_rss_study_identity_cannot_be_relabelled_to_old_protocol(
    pinned_tools: tuple[Path, Path],
    older: str,
) -> None:
    """Study and oracle identity prevent silently mixing RSS and non-RSS."""
    folder, document, path = _study(pinned_tools)
    try:
        forged = copy.deepcopy(document)
        forged["study"]["id"] = older
        (folder / "study.json").write_text(json.dumps(forged), encoding="utf-8")
        with pytest.raises(
            audit.TargetEchoAuditError, match=r"cost|oracle|RSS|producer policy"
        ):
            audit.audit(path)
    finally:
        shutil.rmtree(folder)


@pytest.mark.parametrize(
    "field", ["missing", "zero", "non-integral", "over-budget"]
)
def test_rss_cost_forgery_is_rejected_even_with_valid_guest_code(
    pinned_tools: tuple[Path, Path],
    field: str,
) -> None:
    """A successful guest byte oracle cannot certify forged RSS metrics."""
    folder, document, path = _study(pinned_tools)
    try:
        forged = copy.deepcopy(document)
        costs = forged["observations"][0]["metrics"]
        if field == MISSING:
            del costs["peak_rss_bytes"]
        else:
            costs["peak_rss_bytes"] = {
                "zero": 0,
                "non-integral": 123,
                "over-budget": MAX_CHILD_RSS_BYTES + 1024,
            }[field]
        (folder / "study.json").write_text(json.dumps(forged), encoding="utf-8")
        with pytest.raises(
            audit.TargetEchoAuditError, match=r"RSS|raw|missing|resident memory"
        ):
            audit.audit(path)
    finally:
        shutil.rmtree(folder)


def test_missing_rss_tool_refuses_before_study_is_created(
    pinned_tools: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The user may not claim an observed RSS cost without GNU time."""
    original = target_process.shutil.which

    def missing(name: str, *, path: str | None = None) -> str | None:
        return None if name == target_process.RSS_TOOL else original(name, path=path)

    def forbidden(*args: object, **kwargs: object) -> None:
        _ = (args, kwargs)
        message = "RSS study prepared without a measurement tool"
        raise AssertionError(message)

    monkeypatch.setattr(target_process.shutil, "which", missing)
    monkeypatch.setattr(producer, "_prepare_context", forbidden)
    with pytest.raises(target_process.TargetProcessError, match="GNU time"):
        producer.run_study(
            _plan(), emitter=pinned_tools[0], runner=pinned_tools[1]
        )


def test_operator_cli_selects_v5_measured_resource_mode(
    pinned_tools: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Documented v5 CLI flags preserve exact measured objective identity."""
    original = producer.run_study
    retained: list[Path] = []

    def pinned(plan: producer.StudyPlan) -> tuple[Path, dict[str, Any]]:
        assert plan.measure_child_rss is True
        result = original(plan, emitter=pinned_tools[0], runner=pinned_tools[1])
        retained.append(result[0])
        return result

    monkeypatch.setattr(producer, "run_study", pinned)
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
            "replay",
            "--limit-child-resources",
            "--measure-child-rss",
        ],
    )
    try:
        assert producer.main() == 0
        report = json.loads(capsys.readouterr().out)
        document = json.loads((producer._ROOT / report["study"]).read_text())
        assert document["study"]["id"] == producer.FORWARD_RSS_STUDY
        assert report["observations"] == PAIR_ARMS
        assert (
            audit.audit(report["study"])["verified_target_sources_checked"]
            == PAIR_ARMS
        )
    finally:
        for folder in retained:
            shutil.rmtree(folder)


def test_lost_third_stage_rss_cannot_credit_verified_run(
    pinned_tools: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Exact first output and steps alone cannot certify missing replay RSS."""

    def unmetered_replay(
        path: Path,
        context: producer._Context,
        case: tuple[int, str],
        *,
        steps: int | None,
    ) -> int:
        _ = (path, context, case, steps)
        return 1

    monkeypatch.setattr(producer, "_timed_replay_verifier", unmetered_replay)
    folder, document, relative = _study(pinned_tools)
    try:
        assert all(
            row["outcome"] == TOOL_FAILED for row in document["observations"]
        )
        assert all(
            set(row["metrics"]) == {"elapsed_ns"}
            for row in document["observations"]
        )
        assert audit.audit(relative)[
            "reported_failed_trials_not_replayed"
        ] == len(document["observations"])
    finally:
        shutil.rmtree(folder)


@pytest.mark.parametrize(
    "invalid",
    [
        b"",
        b"0\\n",
        b"-1\\n",
        b"123MB\\n",
        b"12\\n34\\n",
        b"999999999999999999999999999999999\\n",
        b"1048577\\n",
        b"12",
        b" 12\\n",
    ],
)
def test_malformed_gnu_time_rss_reports_are_never_admitted(
    invalid: bytes,
    tmp_path: Path,
) -> None:
    """No parsed maximum on missing, zero, over-budget or malformed data."""
    report = tmp_path / "rss.txt"
    report.write_bytes(invalid)
    with pytest.raises(target_process.TargetProcessError, match="RSS"):
        target_process._rss_report(report)


def test_rss_verifier_is_required_by_plan_before_any_child_is_launched(
    pinned_tools: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Boolean aliases or absent physical child limits cannot claim v5."""

    def forbidden(*args: object, **kwargs: object) -> None:
        _ = (args, kwargs)
        message = "invalid RSS plan launched a candidate"
        raise AssertionError(message)

    monkeypatch.setattr(producer, "_prepare_context", forbidden)
    for plan in (
        replace(_plan(), limit_child_resources=False),
        replace(_plan(), measure_verifier=False),
        replace(_plan(), verifier_mode=producer.SOURCE_VERIFIER_MODE),
        replace(_plan(), measure_child_rss=cast("bool", 1)),
    ):
        with pytest.raises(producer.TargetEchoStudyError, match="target echo"):
            producer.run_study(
                plan, emitter=pinned_tools[0], runner=pinned_tools[1]
            )


def test_symlinked_gnu_time_rss_receipt_is_not_admitted(
    tmp_path: Path,
) -> None:
    """An RSS oracle may not follow an observed measurement-file symlink."""
    real = tmp_path / "original.txt"
    real.write_bytes(b"1024\n")
    alias = tmp_path / "rss.txt"
    alias.symlink_to(real)
    with pytest.raises(target_process.TargetProcessError, match="RSS"):
        target_process._rss_report(alias)


def test_fifo_gnu_time_rss_receipt_cannot_block_parent(
    tmp_path: Path,
) -> None:
    """A measurement FIFO is rejected without blocking on its open call."""
    import os  # ruff: ignore[import-outside-top-level]

    pipe = tmp_path / "rss.txt"
    os.mkfifo(pipe)  # pyright: ignore[reportAttributeAccessIssue]
    with pytest.raises(target_process.TargetProcessError, match="RSS"):
        target_process._rss_report(pipe)


def test_second_verifier_missing_rss_report_is_tool_failure(
    pinned_tools: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A valid-looking second VM cannot certify a missing RSS measurement."""

    def no_observation(*args: object, **kwargs: object) -> None:
        _ = (args, kwargs)

    monkeypatch.setattr(audit, "check_forward_vm_replay", no_observation)
    folder, document, relative = _study(pinned_tools)
    try:
        assert all(
            row["outcome"] == TOOL_FAILED for row in document["observations"]
        )
        assert all(
            set(row["metrics"]) == {"elapsed_ns"}
            for row in document["observations"]
        )
        assert audit.audit(relative)[
            "reported_failed_trials_not_replayed"
        ] == len(document["observations"])
    finally:
        shutil.rmtree(folder)


def test_inflated_first_stage_rss_does_not_publish_successful_cost(
    pinned_tools: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Impossible per-stage usage is rejected instead of entering raw Pareto."""
    original = target_process.invoke_limited_measured

    def invalid_peak(
        command: list[str],
        *,
        timeout_seconds: float = target_process.DEFAULT_TIMEOUT_SECONDS,
    ) -> tuple[sp.CompletedProcess[bytes], int]:
        result, _ = original(command, timeout_seconds=timeout_seconds)
        return result, MAX_CHILD_RSS_BYTES + target_process.KIB_BYTES

    monkeypatch.setattr(target_process, "invoke_limited_measured", invalid_peak)
    folder, document, relative = _study(pinned_tools)
    try:
        assert all(
            row["outcome"] == TOOL_FAILED for row in document["observations"]
        )
        assert all(
            set(row["metrics"]) == {"elapsed_ns"}
            for row in document["observations"]
        )
        assert audit.audit(relative)[
            "reported_failed_trials_not_replayed"
        ] == len(document["observations"])
    finally:
        shutil.rmtree(folder)
