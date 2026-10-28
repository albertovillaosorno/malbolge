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
#   - Deterministic arena operator JSON write-completion regressions.
# - Must-Not:
#   - Claim rollback of bytes already written on a failed text stream.
# - Allows:
#   - Inputs: synthetic reports and deterministic injected text writers.
#   - Outputs: assertions on counts, flush, and command failure status.
#   - Side effects: test-local mocked stdout only.
# - Split-When:
#   - A framed durable report transport needs its own integration tests.
# - Merge-When:
#   - One arena CLI test owner covers all operator stream failures.
# - Summary:
#   - Prevents false command success after short writes and flush faults.
# - Description:
#   - Checks exact output identity and all declared untrusted writer returns.
# - Usage:
#   - `pytest benchmarks/arena/tests/test_report_output.py`.
# - Defaults:
#   - Report bytes already emitted cannot be recalled after an error.
#

"""Checked JSON report output tests without simulated atomic stdout."""

# ruff: file-ignore[assert]

from __future__ import annotations

import json
from typing import TYPE_CHECKING
from typing import cast

import pytest

from benchmarks.arena import analyze
from benchmarks.arena import evidence
from benchmarks.arena import report_output
from benchmarks.arena.tests.test_evidence import sample_study

if TYPE_CHECKING:
    from pathlib import Path

WRITE_FAILURE = "stdout write"
FLUSH_FAILURE = "stdout flush"
BAD_LENGTH = "did not accept exact text length"
WRITE_FAULT_MODE = "write-failure"
FLUSH_FAULT_MODE = "flush-failure"
SHORT_MODE = "short"
INJECTED_OUTPUT_ERROR = "injected output writer failure"


class _FakeStream:
    """One programmable text writer whose reports may contradict its output."""

    def __init__(self, mode: str) -> None:
        self.mode = mode
        self.records: list[str] = []
        self.flushed = False

    def write(self, record: str, /) -> int:
        """Write a test prefix and optionally lie about the character count.

        Returns:
            The test-controlled count, including deliberately malformed values.

        Raises:
            OSError: The test requests a writer fault.

        """
        if self.mode == WRITE_FAULT_MODE:
            message = "simulated broken writer"
            raise OSError(message)
        accepted = len(record) // 2 if self.mode == SHORT_MODE else len(record)
        self.records.append(record[:accepted])
        responses = {
            "over": len(record) + 1,
            "bool": cast("int", bool(1)),
            "none": cast("int", None),
            "negative": -1,
        }
        return responses.get(self.mode, accepted)

    def flush(self) -> None:
        """Record a flush or deliberately reject the final publication.

        Raises:
            RuntimeError: The test requests a flush failure.

        """
        if self.mode == FLUSH_FAULT_MODE:
            message = "simulated flush error"
            raise RuntimeError(message)
        self.flushed = True


def test_report_publisher_preserves_byte_exact_default_json() -> None:
    """A successful writer emits exactly one newline-terminated JSON object."""
    output = _FakeStream("healthy")
    report = {"sample": [1, 2], "status": "reported"}
    report_output.publish(report, output)
    assert output.flushed
    assert output.records == [
        json.dumps(report, sort_keys=True, indent=2) + "\n"
    ]


@pytest.mark.parametrize("mode", ["short", "over", "bool", "none", "negative"])
def test_noncanonical_write_count_fails_without_claiming_completion(
    mode: str,
) -> None:
    """Text write counts cannot be partial, missing, false or inflated."""
    output = _FakeStream(mode)
    with pytest.raises(report_output.ReportOutputError, match=BAD_LENGTH):
        report_output.publish({"status": "reported"}, output)
    assert not output.flushed
    assert output.records


@pytest.mark.parametrize(
    ("mode", "diagnostic"),
    [("write-failure", WRITE_FAILURE), ("flush-failure", FLUSH_FAILURE)],
)
def test_writer_and_flush_exceptions_are_typed_failures(
    mode: str,
    diagnostic: str,
) -> None:
    """Output failures cannot impersonate successful report publication."""
    output = _FakeStream(mode)
    with pytest.raises(report_output.ReportOutputError, match=diagnostic):
        report_output.publish({"status": "reported"}, output)
    if mode == WRITE_FAULT_MODE:
        assert not output.records
    else:
        assert output.records
    assert not output.flushed


def test_partial_stream_output_cannot_be_recalled_after_failure() -> None:
    """A shortened record may already have reached a broken stdout sink."""
    output = _FakeStream("short")
    with pytest.raises(report_output.ReportOutputError, match=BAD_LENGTH):
        report_output.publish({"status": "reported"}, output)
    assert output.records[0].startswith("{")
    assert not output.records[0].endswith("\n")


def test_both_clis_return_nonzero_when_report_publisher_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Analysis success is not command success if final publication fails."""
    document = sample_study(tmp_path)
    path = tmp_path / "study.json"
    _ = path.write_text(json.dumps(document), encoding="utf-8")

    def broken_publisher(
        report: dict[str, object],
        stream: report_output.TextReportStream,
    ) -> None:
        _ = (report, stream)
        raise report_output.ReportOutputError(INJECTED_OUTPUT_ERROR)

    monkeypatch.setattr(report_output, "publish", broken_publisher)
    for args, entry in (
        (["arena", str(path)], analyze.main),
        (["arena-evidence", str(path), "--root", str(tmp_path)], evidence.main),
    ):
        monkeypatch.setattr(analyze.sys, "argv", args)
        with pytest.raises(SystemExit, match="2"):
            entry()
        result = capsys.readouterr()
        assert not result.out
        assert INJECTED_OUTPUT_ERROR in result.err
