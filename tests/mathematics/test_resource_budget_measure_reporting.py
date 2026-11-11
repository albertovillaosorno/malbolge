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
#   - Deterministic resource-budgeting research report publication regressions.
# - Must-Not:
#   - Require live CUDA hardware or change measured resource-plan authority.
# - Allows:
#   - Inputs: synthetic resource scenarios and injected JSON/output providers.
#   - Outputs: exact report validation and fail-closed delivery assertions.
#   - Side effects: test-local redirected stdout only.
# - Split-When:
#   - A separate resource report protocol gains independent ownership.
# - Merge-When:
#   - Other hardware-free budgeting report output tests have the same owner.
# - Summary:
#   - Require native source-bound resource evidence and complete publication.
# - Description:
#   - Tests JSON forgery and stdout write/flush receipt boundaries.
# - Usage:
#   - Run under the repository pytest configuration on any supported host.
# - Defaults:
#   - No CUDA device is assumed; a faulty serializer or writer fails closed.
#

"""Fail-closed resource-budget measurement report regressions."""

from __future__ import annotations

import json
import sys
from typing import cast

import pytest

from benchmarks.accelerator import resource_budget_measure as measure


@pytest.mark.parametrize("provider", ("writer", "encoder", "joint"))
def test_resource_budget_report_rejects_forged_scenario_json(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    provider: str,
) -> None:
    """Untrusted serializers cannot remove synthetic resource scenarios."""
    forged = '{"device":null,"research_id":"forged","scenarios":[]}'

    class ForgedEncoder:
        def __init__(self, **_options: object) -> None:
            pass

        def encode(self, _document: object) -> str:
            return forged

    def forged_writer(*_args: object, **_kwargs: object) -> str:
        return forged

    with monkeypatch.context() as patch:
        patch.setattr(sys, "argv", ["budget-measure"])
        if provider in ("encoder", "joint"):
            patch.setattr(json, "JSONEncoder", ForgedEncoder)
        if provider in ("writer", "joint"):
            patch.setattr(json, "dumps", forged_writer)
        with pytest.raises(
            ValueError, match="resource-budget JSON writer differs from source"
        ):
            _ = measure.main()
        assert capsys.readouterr().out == ""


@pytest.mark.parametrize("fault", (RuntimeError, OverflowError))
def test_resource_budget_report_wraps_json_writer_failure(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    fault: type[Exception],
) -> None:
    """Foreign serializer failures preserve cause without emitting evidence."""
    failure = fault("invalid public provider")

    def failing_writer(*_args: object, **_kwargs: object) -> str:
        raise failure

    with monkeypatch.context() as patch:
        patch.setattr(sys, "argv", ["budget-measure"])
        patch.setattr(json, "dumps", failing_writer)
        with pytest.raises(ValueError, match="resource-budget JSON writer failed") as caught:
            _ = measure.main()
        assert caught.value.__cause__ is failure
        assert capsys.readouterr().out == ""


@pytest.mark.parametrize("receipt", (False, -1, 0, None, "complete"))
def test_resource_budget_report_requires_exact_native_write_receipt(
    monkeypatch: pytest.MonkeyPatch,
    receipt: object,
) -> None:
    """A short or fabricated stdout acknowledgment is not report success."""
    class FakeStream:
        def __init__(self) -> None:
            self.records: list[str] = []
            self.flushed: bool = False

        def write(self, record: str) -> object:
            self.records.append(record)
            return receipt

        def flush(self) -> None:
            self.flushed = True

    output = FakeStream()
    with monkeypatch.context() as patch:
        patch.setattr(sys, "argv", ["budget-measure"])
        patch.setattr(sys, "stdout", output)
        with pytest.raises(ValueError, match="resource-budget stdout write incomplete"):
            _ = measure.main()
    assert len(output.records) == 1
    assert not output.flushed


@pytest.mark.parametrize("receipt", (False, True, "complete"))
def test_resource_budget_report_rejects_nonvoid_flush_receipt(
    monkeypatch: pytest.MonkeyPatch,
    receipt: object,
) -> None:
    """An unverified flush result does not certify delivered measurements."""
    class FakeStream:
        def __init__(self) -> None:
            self.records: list[str] = []

        def write(self, record: str) -> int:
            self.records.append(record)
            return len(record)

        def flush(self) -> object:
            return receipt

    output = FakeStream()
    with monkeypatch.context() as patch:
        patch.setattr(sys, "argv", ["budget-measure"])
        patch.setattr(sys, "stdout", output)
        with pytest.raises(ValueError, match="resource-budget stdout flush incomplete"):
            _ = measure.main()
    assert len(output.records) == 1


@pytest.mark.parametrize("stage", ("write", "flush"))
def test_resource_budget_report_wraps_output_exceptions(
    monkeypatch: pytest.MonkeyPatch,
    stage: str,
) -> None:
    """A failing host stream never reports successful JSON delivery."""
    failure = OSError("injected host stream failure")

    class FailingStream:
        def __init__(self) -> None:
            self.records: list[str] = []

        def write(self, record: str) -> int:
            if stage == "write":
                raise failure
            self.records.append(record)
            return len(record)

        def flush(self) -> None:
            raise failure

    output = FailingStream()
    with monkeypatch.context() as patch:
        patch.setattr(sys, "argv", ["budget-measure"])
        patch.setattr(sys, "stdout", output)
        with pytest.raises(
            ValueError, match=f"resource-budget stdout {stage} failed"
        ) as caught:
            _ = measure.main()
        assert caught.value.__cause__ is failure
    assert len(output.records) == (0 if stage == "write" else 1)


def test_resource_budget_report_native_json_replays_exact_scenarios(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A normal report preserves frozen synthetic scenario identities."""
    with monkeypatch.context() as patch:
        patch.setattr(sys, "argv", ["budget-measure"])
        assert measure.main() == 0
    document = cast("dict[str, object]", json.loads(capsys.readouterr().out))
    assert document["device"] is None
    assert document["research_id"] == "adaptive-accelerator-resource-budgeting"
    scenarios = cast("list[dict[str, object]]", document["scenarios"])
    assert tuple(row["label"] for row in scenarios) == tuple(
        row.label for row in measure.synthetic_results()
    )


def test_resource_budget_report_accepts_equivalent_json_encoder(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A native-equivalent encoder preserves the original report identity."""
    native_encoder = json.JSONEncoder

    class EquivalentEncoder(native_encoder):
        pass

    with monkeypatch.context() as patch:
        patch.setattr(sys, "argv", ["budget-measure"])
        patch.setattr(json, "JSONEncoder", EquivalentEncoder)
        assert measure.main() == 0
        result = cast("dict[str, object]", json.loads(capsys.readouterr().out))
        assert result["research_id"] == "adaptive-accelerator-resource-budgeting"


def test_resource_budget_report_optional_cuda_path_keeps_device_provenance(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Optional live-report identity remains intact without CUDA hardware."""
    simulated_device: dict[str, str | int] = {
        "name": "injected-device",
        "free_memory_bytes": 128 * measure.MIB,
    }
    live_record = measure.synthetic_results()[0]

    def simulated_live_results(
    ) -> tuple[dict[str, str | int], tuple[measure.ScenarioResult, ...]]:
        return simulated_device, (live_record,)

    with monkeypatch.context() as patch:
        patch.setattr(sys, "argv", ["budget-measure", measure.CUDA_FLAG])
        patch.setattr(measure, "_cuda_results", simulated_live_results)
        assert measure.main() == 0
    document = cast("dict[str, object]", json.loads(capsys.readouterr().out))
    assert document["device"] == simulated_device
    scenarios = cast("list[dict[str, object]]", document["scenarios"])
    assert len(scenarios) == len(measure.synthetic_results()) + 1
    assert scenarios[-1]["label"] == live_record.label


def test_resource_budget_report_rejects_length_from_foreign_int_subclass(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An exact-valued non-native write count cannot certify publication."""
    class ForeignInt(int):
        pass

    class ForgedReceipt:
        def __init__(self) -> None:
            self.flushed: bool = False

        def write(self, record: str) -> int:
            return ForeignInt(len(record))

        def flush(self) -> None:
            self.flushed = True

    output = ForgedReceipt()
    with monkeypatch.context() as patch:
        patch.setattr(sys, "argv", ["budget-measure"])
        patch.setattr(sys, "stdout", output)
        with pytest.raises(
            measure.ResourceBudgetReportError,
            match="resource-budget stdout write incomplete",
        ):
            _ = measure.main()
    assert not output.flushed
