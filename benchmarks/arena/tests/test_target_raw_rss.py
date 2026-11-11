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
#   - Producer-to-auditor raw GNU-time RSS regression evidence for classic v7.
# - Must-Not:
#   - Treat locally retained raw tool bytes as authenticated kernel witnesses.
# - Allows:
#   - Inputs: fixed real Malbolge tools and resource-limited study fixtures.
#   - Outputs: exact parsing/cross-link validation and malformed-raw refusals.
#   - Side effects: ignored disposable trial files in the repository .temp.
# - Split-When:
#   - Physical trusted RSS attestation becomes a separate verifier boundary.
# - Merge-When:
#   - A general source-independent resource verifier replaces classic v7.
# - Summary:
#   - Preserve and reparse raw GNU time output independently of the producer.
# - Description:
#   - All three stage raw KiB lines must explain the recorded bytes and peak.
# - Usage:
#   - pytest benchmarks/arena/tests/test_target_raw_rss.py.
# - Defaults:
#   - Linux, GNU time, prlimit, built classic emitter and VM binaries.
#

"""Retained raw GNU time stage readings and independent classic admission."""

# ruff: file-ignore[assert,private-member-access]

from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
import json
from pathlib import Path
import shutil
import sys
import tempfile
import tomllib
from typing import TYPE_CHECKING
from typing import cast

import pytest

from benchmarks.arena import analyze
from benchmarks.arena import target_echo_audit as audit
from benchmarks.arena import target_echo_reference as producer
from benchmarks.arena import target_process

if TYPE_CHECKING:
    from collections.abc import Iterator
    from typing import Any

LINUX = "linux"
RAW_TABLE = "arena_rss"
RAW_KIB = "raw_kib"
BREAKDOWN = "stage_rss_breakdown"
STAGES = ("emitter", "primary_vm", "verifier_vm")
SOURCE_NAMES = (producer.WALK, producer.SKIP)
CORRECT_VERSION = 2
GIB = target_process.CHILD_VIRTUAL_MEMORY_BYTES
ONE_PAIR_ARMS = 2
TOOL_FAILED = "tool_failed"
EMPTY_STDERR = b""

pytestmark = pytest.mark.skipif(
    sys.platform != LINUX
    or not producer.DEFAULT_EMITTER.is_file()
    or not producer.DEFAULT_RUNNER.is_file(),
    reason="requires a built classic emitter/VM on Linux",
)


@pytest.fixture
def pinned_tools() -> Iterator[tuple[Path, Path]]:
    """Pin executable inodes across simultaneous Rust artifact rebuilds.

    Yields:
        Source emitter and VM executable paths within an ignored directory.

    """
    with tempfile.TemporaryDirectory(
        dir=producer._TEMP, prefix="arena-v7-tool-pins-"
    ) as folder:
        emitter = Path(folder) / "malbolge_layout"
        runner = Path(folder) / "malbolge"
        # Private copies avoid shared executable ctime drift across tests.
        shutil.copy2(producer.DEFAULT_EMITTER, emitter)
        shutil.copy2(producer.DEFAULT_RUNNER, runner)
        yield emitter, runner


def _plan(*, raw: bool = True) -> producer.StudyPlan:
    return producer.StudyPlan(
        (1,),
        1,
        producer.PATTERNED_MODE,
        measure_steps=True,
        layout_mode=producer.FORWARD_SKIP_LAYOUT,
        measure_verifier=True,
        verifier_mode=producer.REPLAY_VERIFIER_MODE,
        limit_child_resources=True,
        measure_child_rss=True,
        retain_rss_stages=True,
        retain_raw_rss=raw,
    )


def _study(
    tools: tuple[Path, Path],
    *,
    raw: bool = True,
) -> tuple[Path, dict[str, Any], str]:
    if shutil.which("time") is None or shutil.which("prlimit") is None:
        pytest.skip("requires GNU time and prlimit")
    folder, study = producer.run_study(
        _plan(raw=raw), emitter=tools[0], runner=tools[1]
    )
    return (
        folder,
        study,
        (folder / "study.json").relative_to(producer._ROOT).as_posix(),
    )


def _first_receipt(folder: Path) -> Path:
    return min((folder / "rss").glob("*.json"))


def _relink_receipt(folder: Path, path: Path) -> None:
    run = folder / "runs" / f"{path.stem}.toml"
    original = run.read_text()
    digest = tomllib.loads(original)[RAW_TABLE]["sha256"]
    changed = sha256(path.read_bytes()).hexdigest()
    assert digest != changed
    run.write_text(
        original.replace(
            f'sha256 = "{digest}"',
            f'sha256 = "{changed}"',
        )
    )


def _write_forged_receipt(
    folder: Path,
    path: Path,
    record: dict[str, Any],
) -> None:
    data = json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n"
    path.write_bytes(data.encode("utf-8"))
    _relink_receipt(folder, path)


def test_raw_tool_receipts_are_exactly_reparsed_and_vm_replayed(
    pinned_tools: tuple[Path, Path],
) -> None:
    """Independent source audit re-parses original tool lines exactly."""
    folder, study, relative = _study(pinned_tools)
    try:
        assert study["study"]["id"] == producer.FORWARD_RAW_RSS_STUDY
        assert {row["algorithm"] for row in study["observations"]} == set(
            SOURCE_NAMES
        )
        for row in study["observations"]:
            assert row["outcome"] == analyze.VERIFIED
            assert row["verifier"] == producer.FORWARD_RAW_RSS_VERIFIER
            name = f"{row["algorithm"]}-pairs-1-trial-0"
            receipt = folder / "rss" / f"{name}.json"
            record = json.loads(receipt.read_bytes())
            assert record["schema_version"] == CORRECT_VERSION
            assert set(record["raw_kib"]) == set(STAGES)
            assert all(
                record["stages"][key]
                == int(record["raw_kib"][key].rstrip("\n"))
                * target_process.KIB_BYTES
                for key in STAGES
            )
            assert (
                max(record["stages"].values())
                == row["metrics"]["peak_rss_bytes"]
            )
            run = tomllib.loads((folder / "runs" / f"{name}.toml").read_text())
            assert run[RAW_TABLE]["schema_version"] == CORRECT_VERSION
            assert (
                run[RAW_TABLE]["sha256"]
                == sha256(receipt.read_bytes()).hexdigest()
            )
        checked = audit.audit(
            relative,
            options=audit.AuditOptions(
                replay_candidates=True,
                require_source_commit_object=True,
                emitter=pinned_tools[0],
                runner=pinned_tools[1],
            ),
        )
        assert checked["target_sources_replayed"] == len(study["observations"])
        assert checked["evidence_preflight"]["raw_rows_matched"] == len(
            study["observations"]
        )
    finally:
        shutil.rmtree(folder)


@pytest.mark.parametrize(
    "invalid",
    [
        "",
        "0\n",
        "-1\n",
        "+1\n",
        "123",
        " 123\n",
        "123\n456\n",
        "1MB\n",
        "999999999999999999999999\n",
        "1\r\n",
        "\u0661\n",
        "1\u00a0\n",
        True,
    ],
)
def test_adversarial_raw_gnu_time_reports_reject_after_forged_digest(
    pinned_tools: tuple[Path, Path],
    invalid: object,
) -> None:
    """Even self-consistently rehashed source-reported tool bytes fail."""
    folder, _, relative = _study(pinned_tools)
    try:
        path = _first_receipt(folder)
        record = json.loads(path.read_bytes())
        record["raw_kib"]["emitter"] = invalid
        _write_forged_receipt(folder, path, record)
        with pytest.raises(
            audit.TargetEchoAuditError, match=r"RSS|GNU time|raw"
        ):
            audit.audit(relative)
    finally:
        shutil.rmtree(folder)


def test_syntactically_valid_raw_rss_that_does_not_match_peak_is_rejected(
    pinned_tools: tuple[Path, Path],
) -> None:
    """A different valid original KiB reading cannot explain fixed cost."""
    folder, _, relative = _study(pinned_tools)
    try:
        path = _first_receipt(folder)
        record = json.loads(path.read_bytes())
        record["raw_kib"]["emitter"] = "1\n"
        _write_forged_receipt(folder, path, record)
        with pytest.raises(audit.TargetEchoAuditError, match=r"RSS|GNU time"):
            audit.audit(relative)
    finally:
        shutil.rmtree(folder)


def test_v6_legacy_receipts_keep_exact_original_version_and_fields(
    pinned_tools: tuple[Path, Path],
) -> None:
    """The historical v6 identity never gains raw GNU time output."""
    folder, study, relative = _study(pinned_tools, raw=False)
    try:
        assert study["study"]["id"] == producer.FORWARD_RSS_RECEIPTS_STUDY
        for path in (folder / "rss").glob("*.json"):
            record = json.loads(path.read_bytes())
            assert RAW_KIB not in record
            assert record["schema_version"] == 1
            manifest = tomllib.loads(
                (folder / "runs" / f"{path.stem}.toml").read_text()
            )
            assert manifest[RAW_TABLE]["schema_version"] == 1
        assert audit.audit(relative)["verified_target_sources_checked"] == len(
            study["observations"]
        )
    finally:
        shutil.rmtree(folder)


def test_raw_rss_opt_in_cannot_silently_skip_required_stage_retention(
    pinned_tools: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Invalid v7 options fail before study output setup or any VM execution."""

    def forbidden(*args: object, **kwargs: object) -> None:
        _ = (args, kwargs)
        message = "invalid v7 plan started a target study"
        raise AssertionError(message)

    monkeypatch.setattr(producer, "_prepare_context", forbidden)
    for plan in (
        replace(_plan(), retain_rss_stages=False),
        replace(_plan(), retain_raw_rss=cast("bool", 1)),
    ):
        with pytest.raises(producer.TargetEchoStudyError, match=r"raw RSS"):
            producer.run_study(
                plan, emitter=pinned_tools[0], runner=pinned_tools[1]
            )


def test_read_only_auditor_rejects_producer_wrong_rss_conversion(
    pinned_tools: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A producer byte-conversion bug fails independent raw KiB admission."""
    original_parser = target_process._parse_rss_report
    original_context = producer._prepare_context
    folders: list[Path] = []

    def inflated(raw: bytes) -> int:
        return original_parser(raw) + target_process.KIB_BYTES

    def capture(emitter: Path, runner: Path) -> producer._Context:
        context = original_context(emitter, runner)
        folders.append(context.directory)
        return context

    monkeypatch.setattr(target_process, "_parse_rss_report", inflated)
    monkeypatch.setattr(producer, "_prepare_context", capture)
    try:
        with pytest.raises(
            producer.TargetEchoStudyError, match=r"RSS|raw|source admission"
        ):
            producer.run_study(
                _plan(), emitter=pinned_tools[0], runner=pinned_tools[1]
            )
        assert len(folders) == 1
        assert (folders[0] / "study.json").is_file()
    finally:
        for folder in folders:
            shutil.rmtree(folder)


def test_failed_v7_vm_cannot_publish_partial_gnu_time_receipts(
    pinned_tools: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A lost measured third stage never receives a verified raw RSS cost."""

    def lost_vm_receipt(
        path: Path,
        context: producer._Context,
        case: tuple[int, str],
        *,
        steps: int | None,
    ) -> int:
        _ = (path, context, case, steps)
        return 1

    monkeypatch.setattr(producer, "_timed_replay_verifier", lost_vm_receipt)
    folder, study, relative = _study(pinned_tools)
    try:
        assert list((folder / "rss").iterdir()) == []
        for row in study["observations"]:
            assert row["outcome"] == TOOL_FAILED
            assert set(row["metrics"]) == {"elapsed_ns"}
            name = f"{row["algorithm"]}-pairs-1-trial-0"
            run = tomllib.loads((folder / "runs" / f"{name}.toml").read_text())
            assert RAW_TABLE not in run
        assert audit.audit(relative)[
            "reported_failed_trials_not_replayed"
        ] == len(study["observations"])
    finally:
        shutil.rmtree(folder)


def test_cli_exactly_selects_version_seven_without_changing_earlier_modes(
    pinned_tools: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The public CLI publishes the distinct, versioned raw-tool protocol."""
    original_run = producer.run_study
    retained: list[Path] = []

    def with_tools(plan: producer.StudyPlan) -> tuple[Path, dict[str, Any]]:
        assert plan.retain_raw_rss is True
        folder, study = original_run(
            plan, emitter=pinned_tools[0], runner=pinned_tools[1]
        )
        retained.append(folder)
        return folder, study

    monkeypatch.setattr(producer, "run_study", with_tools)
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
            "--retain-rss-stages",
            "--retain-raw-rss",
        ],
    )
    try:
        assert producer.main() == 0
        result = json.loads(capsys.readouterr().out)
        document = json.loads((producer._ROOT / result["study"]).read_text())
        assert document["study"]["id"] == producer.FORWARD_RAW_RSS_STUDY
        assert result["observations"] == len(document["observations"])
        assert audit.audit(result["study"])[
            "verified_target_sources_checked"
        ] == len(document["observations"])
    finally:
        for folder in retained:
            shutil.rmtree(folder)


def test_v7_report_cannot_be_relabelled_as_v6_or_reverse(
    pinned_tools: tuple[Path, Path],
) -> None:
    """Five equal objectives cannot make two different oracles equivalent."""
    for raw, other in (
        (True, producer.FORWARD_RSS_RECEIPTS_STUDY),
        (False, producer.FORWARD_RAW_RSS_STUDY),
    ):
        folder, study, relative = _study(pinned_tools, raw=raw)
        try:
            study["study"]["id"] = other
            (folder / "study.json").write_text(
                json.dumps(study), encoding="utf-8"
            )
            with pytest.raises(
                audit.TargetEchoAuditError, match=r"RSS|oracle|schema"
            ):
                audit.audit(relative)
        finally:
            shutil.rmtree(folder)


def test_v7_rejects_raw_report_swapped_between_two_traces(
    pinned_tools: tuple[Path, Path],
) -> None:
    """Cross-trial raw text cannot replace the original matching stage line."""
    folder, _, relative = _study(pinned_tools)
    try:
        files = sorted((folder / "rss").glob("*.json"))
        one = json.loads(files[0].read_bytes())
        other = json.loads(files[1].read_bytes())
        swapped = other["raw_kib"]["primary_vm"]
        if swapped == one["raw_kib"]["primary_vm"]:
            swapped = "1\n"
        one["raw_kib"]["primary_vm"] = swapped
        _write_forged_receipt(folder, files[0], one)
        with pytest.raises(
            audit.TargetEchoAuditError, match=r"raw GNU time|RSS"
        ):
            audit.audit(relative)
    finally:
        shutil.rmtree(folder)


@pytest.mark.skipif(
    sys.platform != LINUX,
    reason="GNU time with Linux resource limits is required",
)
def test_measured_child_exposes_original_gnu_time_bytes_without_loss() -> None:
    """The child transport returns actual bounded bytes from GNU time file."""
    input_bytes = bytes(range(target_process.MAX_STDIN_BYTES))
    result, peak, raw = target_process.invoke_with_input_limited_measured_raw(
        [
            sys.executable,
            "-c",
            "import sys;sys.stdout.buffer.write(sys.stdin.buffer.read())",
        ],
        input_bytes,
    )
    assert result.returncode == 0
    assert result.stdout == input_bytes
    assert result.stderr == EMPTY_STDERR
    assert raw.endswith(b"\n")
    assert raw[:-1].isdigit()
    assert target_process.KIB_BYTES * int(raw[:-1]) == peak
    assert 0 < peak <= target_process.CHILD_VIRTUAL_MEMORY_BYTES


def test_v7_receipt_added_during_vm_replay_cannot_escape_final_inventory(
    pinned_tools: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Late unreported raw evidence is rejected at final inventory recheck."""
    folder, _, relative = _study(pinned_tools)
    try:
        extra = folder / "rss" / "unexpected.json"

        def inject(*args: object, **kwargs: object) -> int:
            _ = (args, kwargs)
            extra.write_bytes(_first_receipt(folder).read_bytes())
            return 0

        monkeypatch.setattr(audit, "_replay", inject)
        with pytest.raises(
            audit.TargetEchoAuditError, match=r"unexpected|RSS|receipt"
        ):
            audit.audit(
                relative, options=audit.AuditOptions(replay_candidates=True)
            )
    finally:
        shutil.rmtree(folder)


def test_v7_raw_tool_file_changed_during_vm_replay_is_not_accepted(
    pinned_tools: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A same-source replay cannot hide late raw evidence byte mutations."""
    folder, _, relative = _study(pinned_tools)
    try:
        receipt = _first_receipt(folder)

        def mutate(*args: object, **kwargs: object) -> int:
            _ = (args, kwargs)
            receipt.write_bytes(receipt.read_bytes() + b" ")
            return 0

        monkeypatch.setattr(audit, "_replay", mutate)
        with pytest.raises(
            audit.TargetEchoAuditError, match=r"linked|RSS|receipt"
        ):
            audit.audit(
                relative, options=audit.AuditOptions(replay_candidates=True)
            )
    finally:
        shutil.rmtree(folder)


def test_unreported_raw_third_vm_line_is_a_failed_trial_not_study_crash(
    pinned_tools: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Omitted raw observation cannot earn a resource cost or abort evidence."""
    original = audit.check_forward_vm_replay

    def lost_original_line(
        source: Path,
        runner: Path,
        *,
        case: tuple[int, str],
        replay_options: tuple[int | None, bool, bool, list[bytes] | None],
    ) -> int | None:
        # The VM genuinely executes, but instrumentation omits the raw line.
        options = (*replay_options[:3], None)
        return original(source, runner, case=case, replay_options=options)

    monkeypatch.setattr(audit, "check_forward_vm_replay", lost_original_line)
    folder, study, relative = _study(pinned_tools)
    try:
        assert list((folder / "rss").iterdir()) == []
        for row in study["observations"]:
            assert row["outcome"] == TOOL_FAILED
            assert set(row["metrics"]) == {"elapsed_ns"}
        assert audit.audit(relative)[
            "reported_failed_trials_not_replayed"
        ] == len(study["observations"])
    finally:
        shutil.rmtree(folder)


def test_opt_in_stage_breakdown_reports_verified_stage_costs_and_pairs(
    pinned_tools: tuple[Path, Path],
) -> None:
    """Audited separate emitter and two VM peaks retain paired comparison."""
    folder, study, relative = _study(pinned_tools)
    try:
        assert BREAKDOWN not in audit.audit(relative)
        checked = audit.audit(
            relative, options=audit.AuditOptions(stage_rss_breakdown=True)
        )
        report = checked["stage_rss_breakdown"]
        assert len(report["groups"]) == len(SOURCE_NAMES)
        assert len(report["paired"]) == 1
        assert report["paired"][0]["both_verified"] == 1
        assert set(report["paired"][0]["median_skip_minus_walk_bytes"]) == set(
            STAGES
        )
        for group in report["groups"]:
            assert group["attempts"] == group["verified"] == 1
            assert group["not_verified"] == 0
            row = next(
                row
                for row in study["observations"]
                if row["algorithm"] == group["algorithm"]
            )
            for name in STAGES:
                assert group[name]["median_bytes"] > 0
                assert (
                    group[name]["range_bytes"]
                    == [group[name]["median_bytes"]] * 2
                )
            assert (
                max(group[name]["median_bytes"] for name in STAGES)
                == row["metrics"]["peak_rss_bytes"]
            )
    finally:
        shutil.rmtree(folder)


def test_stage_breakdown_works_for_v6_without_original_tool_text(
    pinned_tools: tuple[Path, Path],
) -> None:
    """A v6 receipt can expose its reported stage data without v7 strings."""
    folder, _, relative = _study(pinned_tools, raw=False)
    try:
        checked = audit.audit(
            relative, options=audit.AuditOptions(stage_rss_breakdown=True)
        )
        assert len(checked[BREAKDOWN]["groups"]) == ONE_PAIR_ARMS
        assert checked["stage_rss_breakdown"]["paired"][0]["both_verified"] == 1
    finally:
        shutil.rmtree(folder)


def test_stage_breakdown_rejects_old_unmeasured_studies(
    pinned_tools: tuple[Path, Path],
) -> None:
    """An old echo study cannot fabricate an unreported stage RSS breakdown."""
    folder, _ = producer.run_study(
        producer.StudyPlan((1,), 1),
        emitter=pinned_tools[0],
        runner=pinned_tools[1],
    )
    try:
        relative = (
            (folder / "study.json").relative_to(producer._ROOT).as_posix()
        )
        with pytest.raises(audit.TargetEchoAuditError, match=r"stage RSS"):
            audit.audit(
                relative, options=audit.AuditOptions(stage_rss_breakdown=True)
            )
    finally:
        shutil.rmtree(folder)


def test_stage_breakdown_counts_failed_trials_without_fabricated_memory_cost(
    pinned_tools: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Only verified outcomes enter median and paired memory summaries."""

    def no_verifier(
        path: Path,
        context: producer._Context,
        case: tuple[int, str],
        *,
        steps: int | None,
    ) -> int:
        _ = (path, context, case, steps)
        return 1

    monkeypatch.setattr(producer, "_timed_replay_verifier", no_verifier)
    folder, _, relative = _study(pinned_tools)
    try:
        report = audit.audit(
            relative, options=audit.AuditOptions(stage_rss_breakdown=True)
        )["stage_rss_breakdown"]
        for group in report["groups"]:
            assert group["verified"] == 0
            assert group["not_verified"] == group["attempts"] == 1
            assert not set(group).intersection(STAGES)
        assert report["paired"][0]["both_verified"] == 0
        assert report["paired"][0]["median_skip_minus_walk_bytes"] == {}
    finally:
        shutil.rmtree(folder)


def test_paired_stage_rss_median_matches_trials_not_separate_arm_medians() -> (
    None
):
    """The paired RSS metric must not subtract independent arm medians."""
    kib = target_process.KIB_BYTES

    def stage_values(value: int) -> dict[str, int]:
        return dict.fromkeys(STAGES, value * kib)

    walk = [
        {"trial": trial, "stages": stage_values(value)}
        for trial, value in enumerate((10, 10, 110))
    ]
    skip = [
        {"trial": trial, "stages": stage_values(value)}
        for trial, value in enumerate((110, 11, 111))
    ]
    rows = {(1, audit.WALK): walk, (1, audit.SKIP): skip}
    summary = audit._stage_rss_pairs(rows)[0]
    assert summary["both_verified"] == len(walk)
    assert set(summary["median_skip_minus_walk_bytes"]) == set(STAGES)
    for name in STAGES:
        assert summary["median_skip_minus_walk_bytes"][name] == kib
        # The medians of the two arms differ by 100 KiB, not 1 KiB.
        assert summary["median_skip_minus_walk_bytes"][name] != 100 * kib

    # If one candidate fails, its baseline cannot contribute to paired costs.
    skip[0]["stages"] = None
    summary = audit._stage_rss_pairs(rows)[0]
    assert summary["both_verified"] == len(walk) - 1
    assert all(
        summary["median_skip_minus_walk_bytes"][name] == kib for name in STAGES
    )
