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
#   - Adversarial Linux per-child resource-controls target-study tests.
# - Must-Not:
#   - Conflate RLIMIT_AS with observed resident memory or aggregate budgets.
# - Allows:
#   - Inputs: pinned local target emitter and normative VM executables.
#   - Outputs: exact v4 limited study and independent bounded audit evidence.
#   - Side effects: disposable ignored local studies and test-owned hardlinks.
# - Split-When:
#   - The arena adds reusable cgroup-scoped control or whole-study accounting.
# - Merge-When:
#   - Shared Linux resource policy verification replaces this target slice.
# - Summary:
#   - Bound emitter, primary VM, measured VM verifier and offline VM replay.
# - Description:
#   - No silent unbounded fallback under failed mandatory tool preflight.
# - Usage:
#   - pytest benchmarks/arena/tests/test_target_limited_resources.py.
# - Defaults:
#   - Linux with util-linux prlimit and built classic compiler/VM required.
#

"""Run physically limited real classic study and verify exact audit policy."""

# ruff: file-ignore[assert,private-member-access]

from __future__ import annotations

from collections import Counter
import copy
import json
from pathlib import Path
import shutil
import sys
import tempfile
from typing import TYPE_CHECKING

import pytest

from benchmarks.arena import analyze
from benchmarks.arena import target_echo_audit as audit
from benchmarks.arena import target_echo_reference as producer
from benchmarks.arena import target_process

if TYPE_CHECKING:
    from collections.abc import Iterator
    import subprocess as sp
    from typing import Any

LINUX_PLATFORM = "linux"
LEVELS = (1, 4, 16, 64)
EXPECTED_ARMS = 2
FOUR_COSTS = ("elapsed_ns", "artifact_bytes", "runtime_steps", "verifier_ns")
GUEST_STEPS_SAVED = 98
FIXED_CHILD_AS_BYTES = 1024 * 1024 * 1024
FIXED_CHILD_CPU_SECONDS = 8
FIXED_CHILD_FSIZE_BYTES = 8 * 1024 * 1024

pytestmark = pytest.mark.skipif(
    sys.platform != LINUX_PLATFORM
    or not producer.DEFAULT_EMITTER.is_file()
    or not producer.DEFAULT_RUNNER.is_file(),
    reason="Linux prlimit and built target executable tools required",
)


def test_v4_identity_freezes_limiter_policy_constants() -> None:
    """A changed kernel cap requires a new research protocol identity."""
    assert target_process.CHILD_VIRTUAL_MEMORY_BYTES == FIXED_CHILD_AS_BYTES
    assert target_process.CHILD_CPU_SECONDS == FIXED_CHILD_CPU_SECONDS
    assert target_process.CHILD_OUTPUT_FILE_BYTES == FIXED_CHILD_FSIZE_BYTES


@pytest.fixture
def pinned_tools() -> Iterator[tuple[Path, Path]]:
    """Prevent concurrent Rust rebuilds from changing executable identity.

    Yields:
        Pinned independently built emitter and runner paths.

    """
    with tempfile.TemporaryDirectory(
        dir=producer._TEMP, prefix="arena-v4-child-tools-"
    ) as root:
        emitter = Path(root) / "malbolge_layout"
        runner = Path(root) / "malbolge"
        emitter.hardlink_to(producer.DEFAULT_EMITTER)
        runner.hardlink_to(producer.DEFAULT_RUNNER)
        yield emitter, runner


def _plan(
    *, limited: bool, levels: tuple[int, ...] = LEVELS
) -> producer.StudyPlan:
    return producer.StudyPlan(
        levels,
        1,
        producer.PATTERNED_MODE,
        measure_steps=True,
        layout_mode=producer.FORWARD_SKIP_LAYOUT,
        measure_verifier=True,
        verifier_mode=producer.REPLAY_VERIFIER_MODE,
        limit_child_resources=limited,
    )


def _run(
    tools: tuple[Path, Path],
    *,
    limited: bool,
    levels: tuple[int, ...] = LEVELS,
) -> tuple[Path, dict[str, Any], str]:
    if limited and shutil.which("prlimit") is None:
        pytest.skip("util-linux prlimit is not available")
    directory, document = producer.run_study(
        _plan(limited=limited, levels=levels),
        emitter=tools[0],
        runner=tools[1],
    )
    path = (directory / "study.json").relative_to(producer._ROOT)
    return directory, document, path.as_posix()


def test_actual_limited_target_study_replays_every_normative_guest_byte(
    pinned_tools: tuple[Path, Path],
) -> None:
    """All 8 bounded target programs satisfy the full independent audit."""
    directory, study, path = _run(pinned_tools, limited=True)
    try:
        assert study["study"]["id"] == producer.FORWARD_LIMITED_REPLAY_STUDY
        assert tuple(study["study"]["objectives"]) == FOUR_COSTS
        assert len(study["observations"]) == len(LEVELS) * EXPECTED_ARMS
        for row in study["observations"]:
            assert row["outcome"] == analyze.VERIFIED
            assert row["verifier"] == producer.FORWARD_LIMITED_REPLAY_VERIFIER
            metrics = row["metrics"]
            assert 0 < metrics["verifier_ns"] <= metrics["elapsed_ns"]
        compared = analyze.analyze(study)["paired_baseline_comparisons"]
        assert len(compared) == len(LEVELS)
        for pair in compared:
            assert pair["cost_differences"]["runtime_steps"][
                "median_candidate_minus_baseline"
            ] == [-GUEST_STEPS_SAVED, 1]
        checked = audit.audit(
            path,
            options=audit.AuditOptions(
                replay_candidates=True,
                require_source_commit_object=True,
                emitter=pinned_tools[0],
                runner=pinned_tools[1],
            ),
        )
        assert checked["target_sources_replayed"] == len(study["observations"])
        assert checked["source_commit_object_verified"] is True
        assert checked["evidence_preflight"]["raw_rows_matched"] == len(
            study["observations"]
        )
    finally:
        shutil.rmtree(directory)


def test_limited_producer_and_offline_auditor_always_use_resource_wrapper(
    pinned_tools: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """None of the three actual executable stages may use plain transport."""
    counts: Counter[str] = Counter()
    original_limited = target_process.invoke_limited
    original_input = target_process.invoke_with_input_limited

    def limited_emitter(
        command: list[str],
        *,
        timeout_seconds: float = target_process.DEFAULT_TIMEOUT_SECONDS,
        stdout_limit: int = target_process.DEFAULT_STDOUT_LIMIT,
        stderr_limit: int = target_process.DEFAULT_STDERR_LIMIT,
    ) -> sp.CompletedProcess[bytes]:
        counts["emitter"] += 1
        return original_limited(
            command,
            timeout_seconds=timeout_seconds,
            stdout_limit=stdout_limit,
            stderr_limit=stderr_limit,
        )

    def limited_vm(
        command: list[str],
        data: bytes,
        *,
        timeout_seconds: float = target_process.DEFAULT_TIMEOUT_SECONDS,
    ) -> sp.CompletedProcess[bytes]:
        counts["vm"] += 1
        return original_input(command, data, timeout_seconds=timeout_seconds)

    def forbidden(*args: object, **kwargs: object) -> None:
        _ = (args, kwargs)
        message = "v4 must not silently execute unbounded target children"
        raise AssertionError(message)

    monkeypatch.setattr(target_process, "invoke_limited", limited_emitter)
    monkeypatch.setattr(target_process, "invoke_with_input_limited", limited_vm)
    for name in ("invoke", "invoke_with_input"):
        monkeypatch.setattr(target_process, name, forbidden)
    directory, study, path = _run(pinned_tools, limited=True, levels=(1, 4))
    try:
        assert counts["emitter"] == len(study["observations"])
        assert counts["vm"] == 2 * 2 * EXPECTED_ARMS
        checked = audit.audit(
            path,
            options=audit.AuditOptions(
                replay_candidates=True,
                emitter=pinned_tools[0],
                runner=pinned_tools[1],
            ),
        )
        assert checked["target_sources_replayed"] == 2 * EXPECTED_ARMS
        assert counts["vm"] == 3 * 2 * EXPECTED_ARMS
    finally:
        shutil.rmtree(directory)


@pytest.mark.parametrize(
    "other_mode",
    [
        producer.FORWARD_REPLAY_COST_STUDY,
        producer.FORWARD_VERIFIER_COST_STUDY,
    ],
)
def test_limited_study_cannot_be_relabelled_as_unlimited(
    pinned_tools: tuple[Path, Path],
    other_mode: str,
) -> None:
    """A different trial ID cannot authorize the limited verifier oracle."""
    directory, study, path = _run(pinned_tools, limited=True, levels=(1,))
    try:
        forged = copy.deepcopy(study)
        forged["study"]["id"] = other_mode
        (directory / "study.json").write_text(
            json.dumps(forged, sort_keys=True), encoding="utf-8"
        )
        with pytest.raises(audit.TargetEchoAuditError, match="oracle"):
            audit.audit(path)
    finally:
        shutil.rmtree(directory)


def test_missing_limiter_prevents_preparation_or_candidate_emission(
    pinned_tools: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Preflight rejects before allocating local evidence study folders."""

    def unavailable(name: str) -> None:
        _ = name

    def forbidden(*args: object, **kwargs: object) -> None:
        _ = (args, kwargs)
        message = "preparation was reached without Linux limiter"
        raise AssertionError(message)

    monkeypatch.setattr(target_process.shutil, "which", unavailable)
    monkeypatch.setattr(producer, "_prepare_context", forbidden)
    with pytest.raises(target_process.TargetProcessError, match="prlimit"):
        producer.run_study(
            _plan(limited=True), emitter=pinned_tools[0], runner=pinned_tools[1]
        )


def test_limited_audit_static_history_allowed_but_replay_needs_limiter(
    pinned_tools: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Static evidence is readable offline; dynamic replay fails without cap."""
    directory, _, path = _run(pinned_tools, limited=True, levels=(1,))
    try:
        assert (
            audit.audit(path)["verified_target_sources_checked"]
            == EXPECTED_ARMS
        )

        def unavailable(name: str) -> None:
            _ = name

        monkeypatch.setattr(target_process.shutil, "which", unavailable)
        with pytest.raises(audit.TargetEchoAuditError, match="prlimit"):
            audit.audit(
                path,
                options=audit.AuditOptions(
                    replay_candidates=True,
                    emitter=pinned_tools[0],
                    runner=pinned_tools[1],
                ),
            )
    finally:
        shutil.rmtree(directory)


def test_operator_cli_selects_physical_limited_study_without_relabelling(
    pinned_tools: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The documented operator CLI selects the exact bounded v4 protocol."""
    if shutil.which("prlimit") is None:
        pytest.skip("util-linux prlimit is not available")
    actual = producer.run_study
    generated: list[Path] = []

    def pinned(plan: producer.StudyPlan) -> tuple[Path, dict[str, Any]]:
        assert plan.limit_child_resources is True
        assert plan.verifier_mode == producer.REPLAY_VERIFIER_MODE
        result = actual(plan, emitter=pinned_tools[0], runner=pinned_tools[1])
        generated.append(result[0])
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
        ],
    )
    try:
        assert producer.main() == 0
        result = json.loads(capsys.readouterr().out)
        assert result["observations"] == EXPECTED_ARMS
        document = json.loads((producer._ROOT / result["study"]).read_text())
        assert document["study"]["id"] == producer.FORWARD_LIMITED_REPLAY_STUDY
        assert all(
            row["outcome"] == analyze.VERIFIED
            for row in document["observations"]
        )
        assert (
            audit.audit(result["study"])["verified_target_sources_checked"]
            == EXPECTED_ARMS
        )
    finally:
        for directory in generated:
            shutil.rmtree(directory)
