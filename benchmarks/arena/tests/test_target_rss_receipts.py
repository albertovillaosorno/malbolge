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
#   - Read-only and live tests of v6 linked three-stage RSS receipts.
# - Must-Not:
#   - Treat locally self-reported measurements as historical attestation.
# - Allows:
#   - Inputs: versioned v6 study, canonical trial receipts, pinned real VM.
#   - Outputs: per-stage exact receipt identity and robust mismatch refusal.
#   - Side effects: disposable research studies in the ignored .temp tree.
# - Split-When:
#   - Generic measured execution governs persistent per-stage receipts.
# - Merge-When:
#   - The parent target source-audit boundary subsumes this evidence.
# - Summary:
#   - Bind retained max-RSS claim to three observed stage values and raw row.
# - Description:
#   - Reject missing, changed, additional, swapped and inconsistently linked
#     child RSS receipts, while replaying original source independently.
# - Usage:
#   - pytest benchmarks/arena/tests/test_target_rss_receipts.py.
# - Defaults:
#   - Linux, GNU time, prlimit and built classic emitter + normative VM.
#

"""Auditable three-stage RSS receipts for optional v6 target experiments."""

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

if TYPE_CHECKING:
    from collections.abc import Callable
    from collections.abc import Iterator
    from typing import Any

LEVELS = (1, 4)
STAGES = ("emitter", "primary_vm", "verifier_vm")
RSS_DIR = "rss"
VERIFIER_STAGE = "verifier_vm"
RSS_TABLE = "arena_rss"
MAX_RSS = 1024 * 1024 * 1024
LINUX_PLATFORM = "linux"
TOOL_FAILED = "tool_failed"
ONE_PAIR_ARMS = 2

pytestmark = pytest.mark.skipif(
    sys.platform != LINUX_PLATFORM
    or not producer.DEFAULT_EMITTER.is_file()
    or not producer.DEFAULT_RUNNER.is_file(),
    reason="real Linux with classic Malbolge tools is required",
)


@pytest.fixture
def pinned_tools() -> Iterator[tuple[Path, Path]]:
    """Isolate executable inode identity from concurrent project rebuilds.

    Yields:
        Local pinned source emitter and normative guest VM.

    """
    with tempfile.TemporaryDirectory(
        dir=producer._TEMP, prefix="arena-v6-rss-tools-"
    ) as root:
        emitter = Path(root) / "malbolge_layout"
        runner = Path(root) / "malbolge"
        # Private copies avoid shared executable ctime drift across tests.
        shutil.copy2(producer.DEFAULT_EMITTER, emitter)
        shutil.copy2(producer.DEFAULT_RUNNER, runner)
        yield emitter, runner


def _plan(*, retain: bool = True) -> producer.StudyPlan:
    return producer.StudyPlan(
        LEVELS,
        1,
        producer.PATTERNED_MODE,
        measure_steps=True,
        layout_mode=producer.FORWARD_SKIP_LAYOUT,
        measure_verifier=True,
        verifier_mode=producer.REPLAY_VERIFIER_MODE,
        limit_child_resources=True,
        measure_child_rss=True,
        retain_rss_stages=retain,
    )


def _study(
    tools: tuple[Path, Path],
    *,
    retain: bool = True,
) -> tuple[Path, dict[str, Any], str]:
    if shutil.which("time") is None or shutil.which("prlimit") is None:
        pytest.skip("GNU time and Linux prlimit are required")
    directory, document = producer.run_study(
        _plan(retain=retain), emitter=tools[0], runner=tools[1]
    )
    return (
        directory,
        document,
        (directory / "study.json").relative_to(producer._ROOT).as_posix(),
    )


def _receipt_files(directory: Path) -> list[Path]:
    return sorted((directory / RSS_DIR).iterdir())


def _stem(row: dict[str, Any]) -> str:
    case = row["case"]
    return f"{row["algorithm"]}-pairs-{case["difficulty"]}-trial-{row["trial"]}"


def _assert_retained_stages(directory: Path, row: dict[str, Any]) -> None:
    assert row["outcome"] == analyze.VERIFIED
    assert row["verifier"] == producer.FORWARD_RSS_RECEIPTS_VERIFIER
    stem = _stem(row)
    receipt = directory / RSS_DIR / f"{stem}.json"
    values = json.loads(receipt.read_bytes())
    assert values["schema_version"] == 1
    assert values["identity"] == {
        "algorithm": row["algorithm"],
        "pairs": row["case"]["difficulty"],
        "trial": row["trial"],
        "workload_sha256": row["case"]["workload_sha256"],
    }
    assert list(values["stages"]) == list(STAGES)
    assert all(0 < value <= MAX_RSS for value in values["stages"].values())
    assert row["metrics"]["peak_rss_bytes"] == max(values["stages"].values())
    run = tomllib.loads((directory / "runs" / f"{stem}.toml").read_text())
    assert run[RSS_TABLE]["schema_version"] == 1
    assert run[RSS_TABLE]["sha256"] == sha256(receipt.read_bytes()).hexdigest()


def test_real_v6_publishes_three_stage_receipts_and_replays_every_vm(
    pinned_tools: tuple[Path, Path],
) -> None:
    """All source, raw, run and RSS graph inputs pass independent admission."""
    directory, study, relative = _study(pinned_tools)
    try:
        assert study["study"]["id"] == producer.FORWARD_RSS_RECEIPTS_STUDY
        rows = study["observations"]
        assert len(rows) == 2 * len(LEVELS)
        assert len(_receipt_files(directory)) == len(rows)
        for row in rows:
            _assert_retained_stages(directory, row)
        checked = audit.audit(
            relative,
            options=audit.AuditOptions(
                replay_candidates=True,
                require_source_commit_object=True,
                emitter=pinned_tools[0],
                runner=pinned_tools[1],
            ),
        )
        assert checked["target_sources_replayed"] == len(rows)
        assert checked["source_commit_object_verified"] is True
        assert checked["evidence_preflight"]["raw_rows_matched"] == len(rows)
    finally:
        shutil.rmtree(directory)


def _remove_receipt(path: Path) -> None:
    path.unlink()


def _add_receipt(path: Path) -> None:
    (path.parent / "unreported.json").write_bytes(path.read_bytes())


def _symlink_receipt(path: Path) -> None:
    backup = path.parent.parent / "rss-backup.txt"
    backup.write_bytes(path.read_bytes())
    path.unlink()
    path.symlink_to(backup)


@pytest.mark.parametrize(
    "corrupt",
    [_remove_receipt, _add_receipt, _symlink_receipt],
)
def test_v6_rss_receipt_inventory_rejects_unexpected_files(
    pinned_tools: tuple[Path, Path],
    corrupt: Callable[[Path], None],
) -> None:
    """Unexpected or unsafe RSS inventory paths cannot be ignored."""
    directory, _, relative = _study(pinned_tools)
    try:
        corrupt(_receipt_files(directory)[0])
        with pytest.raises(
            audit.TargetEchoAuditError, match=r"rss|RSS|receipt"
        ):
            audit.audit(relative)
    finally:
        shutil.rmtree(directory)


def _relink_receipt_digest(directory: Path, receipt: Path) -> None:
    run = directory / "runs" / receipt.with_suffix(".toml").name
    text = run.read_text()
    old = tomllib.loads(text)[RSS_TABLE]["sha256"]
    replacement = sha256(receipt.read_bytes()).hexdigest()
    assert old != replacement
    run.write_text(
        text.replace(f'sha256 = "{old}"', f'sha256 = "{replacement}"')
    )


@pytest.mark.parametrize(
    "kind",
    [
        "alter-stage",
        "false-peak",
        "missing-stage",
        "extra-stage",
        "wrong-version",
        "alter-identity",
        "bool-trial",
    ],
)
def test_v6_rss_receipt_schema_rejects_even_self_consistent_manifest_hash(
    pinned_tools: tuple[Path, Path],
    kind: str,
) -> None:
    """A refreshed digest does not license fake or foreign stage claims."""
    directory, _, relative = _study(pinned_tools)
    try:
        receipt = _receipt_files(directory)[0]
        original = json.loads(receipt.read_bytes())
        stages = original["stages"]
        without_verifier = {
            k: v for k, v in stages.items() if k != VERIFIER_STAGE
        }
        modifications = {
            "alter-stage": {
                **original,
                "stages": {**stages, "emitter": MAX_RSS},
            },
            "false-peak": {**original, "stages": dict.fromkeys(STAGES, 1024)},
            "missing-stage": {**original, "stages": without_verifier},
            "extra-stage": {**original, "stages": {**stages, "invented": 2048}},
            "wrong-version": {**original, "schema_version": 2},
            "alter-identity": {
                **original,
                "identity": {**original["identity"], "trial": 1},
            },
            "bool-trial": {
                **original,
                "identity": {**original["identity"], "trial": False},
            },
        }
        receipt.write_bytes(
            (
                json.dumps(
                    modifications[kind],
                    sort_keys=True,
                    separators=(",", ":"),
                )
                + "\n"
            ).encode("utf-8")
        )
        _relink_receipt_digest(directory, receipt)
        with pytest.raises(
            audit.TargetEchoAuditError, match=r"rss|RSS|receipt"
        ):
            audit.audit(relative)
    finally:
        shutil.rmtree(directory)


def test_v6_rss_manifest_digest_corruption_is_rejected(
    pinned_tools: tuple[Path, Path],
) -> None:
    """An inexact run-manifest digest is not a measured RSS witness."""
    directory, _, relative = _study(pinned_tools)
    try:
        receipt = _receipt_files(directory)[0]
        run = directory / "runs" / receipt.with_suffix(".toml").name
        original = run.read_text()
        table = tomllib.loads(original)[RSS_TABLE]
        wrong = "0" * len(table["sha256"])
        run.write_text(
            original.replace(
                f'sha256 = "{table["sha256"]}"',
                f'sha256 = "{wrong}"',
            )
        )
        with pytest.raises(
            audit.TargetEchoAuditError, match=r"rss|RSS|receipt"
        ):
            audit.audit(relative)
    finally:
        shutil.rmtree(directory)


def test_earlier_v5_study_retains_original_bytes_and_no_rss_receipt_folder(
    pinned_tools: tuple[Path, Path],
) -> None:
    """The new evidence directory and manifest table are opt-in only."""
    directory, study, relative = _study(pinned_tools, retain=False)
    try:
        assert study["study"]["id"] == producer.FORWARD_RSS_STUDY
        assert not (directory / RSS_DIR).exists()
        for row in study["observations"]:
            run = directory / "runs" / f"{_stem(row)}.toml"
            assert RSS_TABLE not in tomllib.loads(run.read_text())
        assert audit.audit(relative)["verified_target_sources_checked"] == len(
            study["observations"]
        )
    finally:
        shutil.rmtree(directory)


def test_invalid_v6_rss_manifest_toml_rejects_with_typed_audit_error(
    pinned_tools: tuple[Path, Path],
) -> None:
    """Invalid TOML never bubbles an unhandled parser exception."""
    directory, _, relative = _study(pinned_tools)
    try:
        receipt = _receipt_files(directory)[0]
        run = directory / "runs" / receipt.with_suffix(".toml").name
        run.write_bytes(run.read_bytes() + b"\n[broken\n")
        with pytest.raises(audit.TargetEchoAuditError, match=r"RSS|run|TOML"):
            audit.audit(relative)
    finally:
        shutil.rmtree(directory)


def test_v6_resource_receipt_flag_requires_v5_measurement(
    pinned_tools: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No output tree is created for a receipt flag without physical RSS."""

    def forbidden(*args: object, **kwargs: object) -> None:
        _ = (args, kwargs)
        message = "invalid v6 plan reached study output setup"
        raise AssertionError(message)

    monkeypatch.setattr(producer, "_prepare_context", forbidden)
    for invalid in (
        replace(_plan(), measure_child_rss=False),
        replace(_plan(), retain_rss_stages=cast("bool", 1)),
    ):
        with pytest.raises(producer.TargetEchoStudyError, match=r"RSS|rss"):
            producer.run_study(
                invalid, emitter=pinned_tools[0], runner=pinned_tools[1]
            )


def test_rss_receipt_drift_during_audit_replay_is_rejected(
    pinned_tools: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A source-stable VM replay cannot hide late RSS evidence substitution."""
    directory, _, relative = _study(pinned_tools)
    try:
        receipt = _receipt_files(directory)[0]

        def change_receipt(*args: object, **kwargs: object) -> int:
            _ = (args, kwargs)
            receipt.write_bytes(receipt.read_bytes() + b" ")
            return 0

        monkeypatch.setattr(audit, "_replay", change_receipt)
        with pytest.raises(audit.TargetEchoAuditError, match=r"RSS|rss|linked"):
            audit.audit(
                relative,
                options=audit.AuditOptions(replay_candidates=True),
            )
    finally:
        shutil.rmtree(directory)


def test_failed_v6_verifier_never_retains_partial_rss_receipts(
    pinned_tools: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A failed verifier may not create an incomplete linked RSS receipt."""

    def missing_verifier(
        path: Path,
        context: producer._Context,
        case: tuple[int, str],
        *,
        steps: int | None,
    ) -> int:
        _ = (path, context, case, steps)
        return 1

    monkeypatch.setattr(producer, "_timed_replay_verifier", missing_verifier)
    directory, study, relative = _study(pinned_tools)
    try:
        assert _receipt_files(directory) == []
        for row in study["observations"]:
            assert row["outcome"] == TOOL_FAILED
            assert set(row["metrics"]) == {"elapsed_ns"}
            manifest = directory / "runs" / f"{_stem(row)}.toml"
            assert RSS_TABLE not in tomllib.loads(manifest.read_text())
        checked = audit.audit(relative)
        assert checked["reported_failed_trials_not_replayed"] == len(
            study["observations"]
        )
    finally:
        shutil.rmtree(directory)


def test_rss_receipt_study_cannot_be_relabelled_as_earlier_v5(
    pinned_tools: tuple[Path, Path],
) -> None:
    """Equal objective lists do not make the v5/v6 evidence interchangeable."""
    directory, study, relative = _study(pinned_tools)
    try:
        study["study"]["id"] = producer.FORWARD_RSS_STUDY
        (directory / "study.json").write_text(
            json.dumps(study), encoding="utf-8"
        )
        with pytest.raises(audit.TargetEchoAuditError, match=r"oracle|RSS|rss"):
            audit.audit(relative)
    finally:
        shutil.rmtree(directory)


def test_v5_run_cannot_disguise_unexpected_v6_receipt_extension(
    pinned_tools: tuple[Path, Path],
) -> None:
    """An older study must not silently accept a foreign resource table."""
    directory, study, relative = _study(pinned_tools, retain=False)
    try:
        row = study["observations"][0]
        run = directory / "runs" / f"{_stem(row)}.toml"
        with run.open("a", encoding="utf-8") as stream:
            _ = stream.write(
                '\n[arena_rss]\nschema_version = 1\nsha256 = "'
                + "0" * 64
                + '"\n'
            )
        with pytest.raises(
            audit.TargetEchoAuditError, match=r"RSS|rss|receipt"
        ):
            audit.audit(relative)
    finally:
        shutil.rmtree(directory)


def test_unreported_rss_file_added_during_replay_fails_inventory_recheck(
    pinned_tools: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Late extra RSS artifacts cannot outlive the audit's evidence snapshot."""
    directory, _, relative = _study(pinned_tools)
    try:
        extra = directory / RSS_DIR / "late-unreported.json"

        def add_unreported(*args: object, **kwargs: object) -> int:
            _ = (args, kwargs)
            extra.write_bytes(_receipt_files(directory)[0].read_bytes())
            return 0

        monkeypatch.setattr(audit, "_replay", add_unreported)
        with pytest.raises(
            audit.TargetEchoAuditError, match=r"rss|RSS|unexpected"
        ):
            audit.audit(
                relative,
                options=audit.AuditOptions(replay_candidates=True),
            )
    finally:
        shutil.rmtree(directory)


def test_operator_cli_selects_v6_retain_rss_option(
    pinned_tools: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The opt-in CLI emits v6 receipt-linked evidence, not v5 metadata."""
    original = producer.run_study
    generated: list[Path] = []

    def pinned(plan: producer.StudyPlan) -> tuple[Path, dict[str, Any]]:
        assert plan.retain_rss_stages is True
        result = original(plan, emitter=pinned_tools[0], runner=pinned_tools[1])
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
            "--measure-child-rss",
            "--retain-rss-stages",
        ],
    )
    try:
        assert producer.main() == 0
        output = json.loads(capsys.readouterr().out)
        document = json.loads((producer._ROOT / output["study"]).read_text())
        assert document["study"]["id"] == producer.FORWARD_RSS_RECEIPTS_STUDY
        assert output["observations"] == ONE_PAIR_ARMS
        assert len(_receipt_files(generated[0])) == output["observations"]
        assert (
            audit.audit(output["study"])["verified_target_sources_checked"]
            == ONE_PAIR_ARMS
        )
    finally:
        for directory in generated:
            shutil.rmtree(directory)
