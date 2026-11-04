# Copyright:
#   - Copyright © 2026 Alberto Villa Osorno.
# SPDX-License-Identifier:
#   - LicenseRef-Proprietary
# Confidential:
#   - true
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
from typing import TYPE_CHECKING, cast

import pytest

from benchmarks.arena import analyze, evidence, report_output
from benchmarks.arena.tests.test_evidence import sample_study

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator
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


class _NonCanonicalFlushStream(_FakeStream):
    """A writer that returns fabricated flush completion instead of None."""

    def __init__(self, response: object) -> None:
        super().__init__("healthy")
        self.response = response

    def flush(self) -> None:
        """Report a malformed completion result without flushing."""
        return cast("None", self.response)


@pytest.mark.parametrize(
    "response", [False, True, 0, 1, "complete", b"done"]
)
def test_flush_must_have_exact_void_completion_receipt(
    response: object,
) -> None:
    """Streams cannot claim output success with malformed flush receipts."""
    output = _NonCanonicalFlushStream(response)
    with pytest.raises(report_output.ReportOutputError, match="stdout flush"):
        report_output.publish({"status": "reported"}, output)
    assert output.records
    assert not output.flushed


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


@pytest.mark.parametrize(
    "invalid_root",
    [[], (), None, 0, "text", True],
    ids=["list", "tuple", "null", "integer", "text", "boolean"],
)
def test_report_root_requires_exact_native_json_object(
    invalid_root: object,
) -> None:
    """A JSON scalar or array is not an arena report, even when serializable."""
    output = _FakeStream("healthy")
    with pytest.raises(
        report_output.ReportOutputError, match="JSON serialization"
    ) as error:
        report_output.publish(cast("dict[str, object]", invalid_root), output)
    assert isinstance(error.value.__cause__, TypeError)
    assert not output.records
    assert not output.flushed


def test_analyzer_cli_rejects_nonobject_analysis_without_stdout(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A corrupted analyzer cannot complete a CLI with top-level JSON null."""
    document = sample_study(tmp_path)
    path = tmp_path / "study.json"
    _ = path.write_text(json.dumps(document), encoding="utf-8")

    def invalid_analysis(*args: object, **kwargs: object) -> dict[str, object]:
        del args, kwargs
        return cast("dict[str, object]", None)

    monkeypatch.setattr(analyze, "analyze", invalid_analysis)
    monkeypatch.setattr(analyze.sys, "argv", ["arena", str(path)])
    with pytest.raises(SystemExit, match="2"):
        analyze.main()
    result = capsys.readouterr()
    assert not result.out
    assert "arena report JSON serialization failed" in result.err


@pytest.mark.parametrize("nonfinite", [float("nan"), float("inf"), -float("inf")])
def test_nonfinite_nested_costs_fail_before_any_stdout(
    nonfinite: float,
) -> None:
    """A formally successful arena report must be standards-compliant JSON."""
    output = _FakeStream("healthy")
    with pytest.raises(
        report_output.ReportOutputError, match="JSON serialization"
    ) as error:
        report_output.publish({"curves": [{"costs": [nonfinite]}]}, output)
    assert isinstance(error.value.__cause__, ValueError)
    assert output.records == []
    assert not output.flushed


@pytest.mark.parametrize("invalid_kind", ["cycle", "unsupported"])
def test_unrenderable_report_fails_as_typed_prepublication_error(
    invalid_kind: str,
) -> None:
    """Corrupted analysis objects cannot escape typed operator failure."""
    output = _FakeStream("healthy")
    if invalid_kind == "cycle":
        values: list[object] = []
        values.append(values)
        report = {"results": values}
    else:
        report = {"results": object()}
    with pytest.raises(
        report_output.ReportOutputError, match="JSON serialization"
    ) as error:
        report_output.publish(report, output)
    assert isinstance(error.value.__cause__, (ValueError, TypeError))
    assert output.records == []
    assert not output.flushed


def test_both_arena_clis_reject_nonfinite_report_without_stdout(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A malformed analyzed result must produce a nonzero CLI status."""
    document = sample_study(tmp_path)
    path = tmp_path / "study.json"
    _ = path.write_text(json.dumps(document), encoding="utf-8")

    def invalid_analysis(*args: object, **kwargs: object) -> dict[str, object]:
        del args, kwargs
        return {"costs": [{"time_ns": float("nan")}]}

    monkeypatch.setattr(analyze, "analyze", invalid_analysis)
    for arguments, entry in (
        (["arena", str(path)], analyze.main),
        (["arena-evidence", str(path), "--root", str(tmp_path)], evidence.main),
    ):
        monkeypatch.setattr(analyze.sys, "argv", arguments)
        with pytest.raises(SystemExit, match="2"):
            entry()
        captured = capsys.readouterr()
        assert not captured.out
        assert "arena report JSON serialization failed" in captured.err


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


class _HostileList(list[object]):
    """A JSON list subclass can replace serialization iteration with code."""

    def __iter__(self):  # type: ignore[override]
        message = "caller-owned list iterator ran"
        raise AssertionError(message)


class _HostileDict(dict[str, object]):
    """A JSON mapping subclass can replace serialization item iteration."""

    def items(self):  # type: ignore[override]
        message = "caller-owned mapping items ran"
        raise AssertionError(message)


class _HostileKey(str):
    """A string subclass can run a comparison when JSON keys are sorted."""

    def __lt__(self, other: object) -> bool:
        message = "caller-owned string comparison ran"
        raise AssertionError(message)


@pytest.mark.parametrize(
    "report",
    [
        _HostileDict({"status": "ready"}),
        {"values": _HostileList([1, 2])},
        {_HostileKey("first"): 1, _HostileKey("second"): 2},
        {"values": (_HostileKey("value"),)},
        {"values": [{"field": _HostileList([1])}]},
    ],
    ids=["mapping-subclass", "list-subclass", "key-subclass", "nested-text", "nested-list"],
)
def test_foreign_json_subclasses_fail_before_serialization_or_stdout(
    report: dict[str, object],
) -> None:
    """Direct publication cannot execute caller-owned container methods."""
    output = _FakeStream("healthy")
    with pytest.raises(
        report_output.ReportOutputError, match="JSON serialization"
    ) as error:
        report_output.publish(report, output)
    assert isinstance(error.value.__cause__, TypeError)
    assert not output.records
    assert not output.flushed


def test_native_json_tuple_and_scalars_remain_publishable() -> None:
    """Existing standard JSON-compatible records retain their wire bytes."""
    output = _FakeStream("healthy")
    report = {"values": (True, None, 2, 1.5, "okay", [0])}
    report_output.publish(report, output)
    assert output.records == [json.dumps(report, sort_keys=True, indent=2) + "\n"]
    assert output.flushed


class _HostileEncoderError(TypeError):
    """A serializer exception with a dangerous diagnostic formatter."""

    def __str__(self) -> str:
        raise AssertionError("foreign JSON error formatting executed")


class _ForgedJsonText(str):
    """A foreign encoder string can intercept newline record formation."""

    def __add__(self, _other: object) -> str:
        raise AssertionError("foreign JSON string concatenation executed")


@pytest.mark.parametrize(
    "fault",
    [
        KeyError("missing encoder state"),
        OSError("encoder backing store failed"),
        RuntimeError("encoder unavailable"),
        _HostileEncoderError("unsafe encoder diagnostic"),
    ],
    ids=["key-error", "host-io", "runtime", "hostile-formatter"],
)
def test_json_encoder_host_failure_is_typed_without_formatting(
    monkeypatch: pytest.MonkeyPatch,
    fault: Exception,
) -> None:
    """A failed JSON encoder cannot run exception hooks or write stdout."""
    output = _FakeStream("healthy")

    def fail_encoder(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise fault

    monkeypatch.setattr(report_output.json, "dumps", fail_encoder)
    with pytest.raises(report_output.ReportOutputError, match="JSON serialization") as caught:
        report_output.publish({"status": "ready"}, output)
    assert caught.value.__cause__ is fault
    assert not output.records
    assert not output.flushed


@pytest.mark.parametrize(
    "forged", [None, True, 7, b"{}", _ForgedJsonText("{}")],
    ids=["none", "boolean", "integer", "bytes", "foreign-string"],
)
def test_json_encoder_requires_native_complete_text_before_publication(
    monkeypatch: pytest.MonkeyPatch,
    forged: object,
) -> None:
    """A fabricated encoder result cannot claim complete JSON publication."""
    output = _FakeStream("healthy")
    monkeypatch.setattr(report_output.json, "dumps", lambda *_a, **_kw: forged)
    with pytest.raises(report_output.ReportOutputError, match="JSON serialization"):
        report_output.publish({"status": "ready"}, output)
    assert not output.records
    assert not output.flushed


@pytest.mark.parametrize(
    "forged",
    [
        "not-json",
        "{}",
        '{"status": "tampered"}',
        '["reported"]',
        '{"status":"ready"}',
    ],
    ids=["malformed", "empty", "wrong-value", "wrong-root", "noncanonical"],
)
def test_native_json_encoder_cannot_publish_fabricated_record(
    monkeypatch: pytest.MonkeyPatch,
    forged: str,
) -> None:
    """An exact string receipt cannot replace the requested canonical JSON."""
    output = _FakeStream("healthy")
    monkeypatch.setattr(report_output.json, "dumps", lambda *_a, **_kw: forged)
    with pytest.raises(report_output.ReportOutputError, match="JSON serialization"):
        report_output.publish({"status": "ready"}, output)
    assert not output.records
    assert not output.flushed


@pytest.mark.parametrize(
    "forged",
    [None, False, 5, _ForgedJsonText('{"status": "ready"}'), "{}"],
    ids=["null", "bool", "integer", "foreign-text", "wrong-json"],
)
def test_canonical_encoder_requires_native_matching_text(
    monkeypatch: pytest.MonkeyPatch,
    forged: object,
) -> None:
    """An invalid canonical cross-check cannot authorize output publication."""
    output = _FakeStream("healthy")
    report = {"status": "ready"}
    correct = json.dumps(report, sort_keys=True, indent=2, allow_nan=False)

    class ForgedEncoder:
        def encode(self, _report: object) -> object:
            return forged

    monkeypatch.setattr(report_output.json, "dumps", lambda *_a, **_kw: correct)
    monkeypatch.setattr(
        report_output.json, "JSONEncoder", lambda **_kw: ForgedEncoder()
    )
    with pytest.raises(report_output.ReportOutputError, match="JSON serialization"):
        report_output.publish(report, output)
    assert not output.records
    assert not output.flushed


def test_canonical_encoder_fault_preserves_cause_without_stdout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An unexpected second encoder failure cannot pass a good first receipt."""
    output = _FakeStream("healthy")
    report = {"status": "ready"}
    correct = json.dumps(report, sort_keys=True, indent=2, allow_nan=False)
    fault = _HostileEncoderError("untrusted encoder fault")

    class ForgedEncoder:
        def encode(self, _report: object) -> str:
            raise fault

    monkeypatch.setattr(report_output.json, "dumps", lambda *_a, **_kw: correct)
    monkeypatch.setattr(
        report_output.json, "JSONEncoder", lambda **_kw: ForgedEncoder()
    )
    with pytest.raises(
        report_output.ReportOutputError, match="JSON serialization"
    ) as caught:
        report_output.publish(report, output)
    assert caught.value.__cause__ is fault
    assert not output.records
    assert not output.flushed


@pytest.mark.parametrize("cli", ["analyze", "evidence"])
def test_fabricated_native_json_encoder_rejects_both_cli_routes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    cli: str,
) -> None:
    """A fabricated native JSON string must not reach either operator sink."""
    document = sample_study(tmp_path)
    source = tmp_path / "study.json"
    _ = source.write_text(json.dumps(document), encoding="utf-8")
    monkeypatch.setattr(report_output.json, "dumps", lambda *_a, **_kw: "{}")
    arguments = ["arena", str(source)]
    if cli == "evidence":
        arguments += ["--root", str(tmp_path)]
    monkeypatch.setattr(analyze.sys, "argv", arguments)
    with pytest.raises(SystemExit, match="2"):
        (analyze.main if cli == "analyze" else evidence.main)()
    output = capsys.readouterr()
    assert not output.out
    assert "arena report JSON serialization failed" in output.err


class _UnsafeStreamError(RuntimeError):
    """A stream exception whose diagnostic formatting executes foreign code."""

    def __str__(self) -> str:
        message = "caller-owned exception formatting executed"
        raise AssertionError(message)


class _UnexpectedStream(_FakeStream):
    """One writer/flush implementation that raises a caller-owned exception."""

    def __init__(self, phase: str, fault: Exception) -> None:
        super().__init__("healthy")
        self.phase = phase
        self.fault = fault

    def write(self, record: str, /) -> int:
        """Raise before publication when configured for the writer phase."""
        if self.phase == "write":
            raise self.fault
        return super().write(record)

    def flush(self) -> None:
        """Raise after an accepted record when configured for flush."""
        if self.phase == "flush":
            raise self.fault
        super().flush()


@pytest.mark.parametrize("phase", ["write", "flush"])
@pytest.mark.parametrize(
    "fault", [KeyError("missing sink state"), _UnsafeStreamError()],
    ids=["unexpected-exception-class", "unsafe-exception-formatting"],
)
def test_caller_owned_stream_failure_is_typed_without_formatting(
    phase: str, fault: Exception,
) -> None:
    """Any ordinary stream exception remains the cause of typed failure."""
    output = _UnexpectedStream(phase, fault)
    with pytest.raises(
        report_output.ReportOutputError, match=f"stdout {phase} failed"
    ) as error:
        report_output.publish({"status": "reported"}, output)
    assert error.value.__cause__ is fault
    assert bool(output.records) is (phase == "flush")
    assert not output.flushed


class _ForeignMetaclass(type):
    """Caller-defined type equality must never run during native admission."""

    def __eq__(cls, other: object) -> bool:
        message = "caller-owned metaclass equality executed"
        raise AssertionError(message)


class _ForeignMetaclassValue(metaclass=_ForeignMetaclass):
    """An unsupported report value with an overridable runtime type."""


class _ForeignMetaclassDict(dict[str, object], metaclass=_ForeignMetaclass):
    """A dict subclass whose metaclass replaces equality checks."""


class _ForeignMetaclassString(str, metaclass=_ForeignMetaclass):
    """A string subclass whose type equality is a caller-controlled hook."""


@pytest.mark.parametrize(
    "report",
    [
        {"data": _ForeignMetaclassValue()},
        {"data": _ForeignMetaclassDict({"valid": "text"})},
        {"data": _ForeignMetaclassString("value")},
    ],
    ids=["foreign-type", "dict-subclass-type", "string-subclass-type"],
)
def test_native_json_admission_never_calls_custom_metaclass_equality(
    report: dict[str, object],
) -> None:
    """Even runtime type comparisons cannot invoke foreign equality hooks."""
    output = _FakeStream("healthy")
    with pytest.raises(
        report_output.ReportOutputError, match="JSON serialization"
    ) as error:
        report_output.publish(report, output)
    assert isinstance(error.value.__cause__, TypeError)
    assert not output.records
    assert not output.flushed


@pytest.mark.parametrize(
    "forged",
    ['{"status":"tampered"}', '{"status":"ready"}', "not-json"],
    ids=["wrong-value", "noncanonical-format", "invalid-json"],
)
def test_shared_json_encoder_substitution_cannot_publish_forged_record(
    monkeypatch: pytest.MonkeyPatch, forged: str
) -> None:
    """The two encoder calls must not both trust a substituted class."""
    output = _FakeStream("healthy")

    class ForgedEncoder:
        def __init__(self, **_options: object) -> None:
            pass

        def encode(self, _report: object) -> str:
            return forged

    monkeypatch.setattr(report_output.json, "JSONEncoder", ForgedEncoder)
    with pytest.raises(report_output.ReportOutputError, match="JSON serialization"):
        report_output.publish({"status": "ready"}, output)
    assert not output.records
    assert not output.flushed


def test_mutated_shared_encoder_method_cannot_publish_wrong_report(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Even an in-place encoder method replacement must be rejected."""
    output = _FakeStream("healthy")
    monkeypatch.setattr(
        report_output.json.encoder.JSONEncoder,
        "encode",
        lambda _self, _report: '{"status": "tampered"}',
    )
    with pytest.raises(report_output.ReportOutputError, match="JSON serialization"):
        report_output.publish({"status": "ready"}, output)
    assert not output.records
    assert not output.flushed


def test_mutated_shared_encoder_iterator_cannot_publish_wrong_report(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The canonical encoder must survive an in-place iterator replacement."""
    output = _FakeStream("healthy")
    monkeypatch.setattr(
        report_output.json.encoder.JSONEncoder,
        "iterencode",
        lambda _self, _report, _one_shot=False: iter(['{"status": "tampered"}']),
    )
    with pytest.raises(report_output.ReportOutputError, match="JSON serialization"):
        report_output.publish({"status": "ready"}, output)
    assert not output.records
    assert not output.flushed


def test_shared_json_iterator_factory_cannot_publish_wrong_report(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A forged iterator factory must not change the report value on stdout."""
    output = _FakeStream("healthy")
    monkeypatch.setattr(
        report_output.json.encoder,
        "_make_iterencode",
        lambda *_args, **_kw: lambda _report, _indent: iter(
            ['{"status": "tampered"}']
        ),
    )
    with pytest.raises(report_output.ReportOutputError, match="JSON serialization"):
        report_output.publish({"status": "ready"}, output)
    assert not output.records
    assert not output.flushed


@pytest.mark.parametrize(
    ("original", "forged"),
    [("ready", "tampered"), ("caf\u00e9", "other")],
    ids=["ascii-value", "unicode-value"],
)
def test_shared_json_string_escaper_cannot_publish_forged_values(
    monkeypatch: pytest.MonkeyPatch, original: str, forged: str
) -> None:
    """The two JSON encoders share one mutable string-escape provider."""
    output = _FakeStream("healthy")
    source_encoder = json.encoder.encode_basestring_ascii

    def substituted_encoder(value: str) -> str:
        return source_encoder(forged if value == original else value)

    monkeypatch.setattr(
        report_output.json.encoder, "encode_basestring_ascii", substituted_encoder
    )
    with pytest.raises(report_output.ReportOutputError, match="JSON serialization"):
        report_output.publish({"status": original}, output)
    assert not output.records
    assert not output.flushed


@pytest.mark.skipif(
    getattr(json.encoder, "c_make_encoder", None) is None,
    reason="host JSON C encoder is unavailable",
)
def test_joint_json_factory_substitution_cannot_forge_report(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A forged native and Python iterator cannot jointly certify wrong JSON."""
    output = _FakeStream("healthy")
    wrong = '{"status": "forged"}'

    def substituted_c_factory(*_args: object, **_kwargs: object):
        return lambda _report, _indent: [wrong]

    def substituted_python_factory(*_args: object, **_kwargs: object):
        return lambda _report, _indent: iter([wrong])

    monkeypatch.setattr(
        report_output.json.encoder, "c_make_encoder", substituted_c_factory
    )
    monkeypatch.setattr(
        report_output.json.encoder, "_make_iterencode", substituted_python_factory
    )
    with pytest.raises(report_output.ReportOutputError, match="JSON serialization"):
        report_output.publish({"status": "ready"}, output)
    assert not output.records
    assert not output.flushed


@pytest.mark.skipif(
    getattr(json.encoder, "c_make_encoder", None) is None,
    reason="host JSON C encoder is unavailable",
)
def test_midcall_joint_json_factory_swap_cannot_forge_report(  # ruff: ignore[complex-structure]
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The first serializer cannot replace the later source proof."""
    output = _FakeStream("healthy")
    wrong = '{"status": "forged"}'

    def substituted_c_iterator(report: object, indent: int) -> list[str]:
        del report, indent
        return [wrong]

    def substituted_python_iterator(
        report: object, indent: int
    ) -> Iterator[str]:
        del report, indent
        return iter([wrong])

    def substituted_c_factory(
        *args: object, **kwargs: object
    ) -> Callable[[object, int], list[str]]:
        del args, kwargs
        return substituted_c_iterator

    def substituted_python_factory(
        *args: object, **kwargs: object
    ) -> Callable[[object, int], Iterator[str]]:
        del args, kwargs
        return substituted_python_iterator

    with monkeypatch.context() as context:

        def substituted_dumps(*_args: object, **_kwargs: object) -> str:
            del _args, _kwargs
            context.setattr(
                report_output.json.encoder, "c_make_encoder",
                substituted_c_factory,
            )
            context.setattr(
                report_output.json.encoder, "_make_iterencode",
                substituted_python_factory,
            )
            return wrong

        context.setattr(report_output.json, "dumps", substituted_dumps)
        with pytest.raises(
            report_output.ReportOutputError, match="JSON serialization"
        ):
            report_output.publish({"status": "ready"}, output)
    assert not output.records
    assert not output.flushed


def test_midcall_json_escaper_swap_cannot_forge_report(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A replaced string escaper cannot outlive the first serializer."""
    output = _FakeStream("healthy")
    wrong = json.dumps(
        {"status": "forged"}, sort_keys=True, indent=2, allow_nan=False
    )
    native_escape = json.encoder.encode_basestring_ascii
    original = "ready"

    def substituted_escape(value: str) -> str:
        return native_escape("forged" if value == original else value)

    with monkeypatch.context() as context:

        def substituted_dumps(*_args: object, **_kwargs: object) -> str:
            del _args, _kwargs
            context.setattr(
                report_output.json.encoder, "encode_basestring_ascii",
                substituted_escape,
            )
            return wrong

        context.setattr(report_output.json, "dumps", substituted_dumps)
        with pytest.raises(
            report_output.ReportOutputError, match="JSON serialization"
        ):
            report_output.publish({"status": "ready"}, output)
    assert not output.records
    assert not output.flushed


@pytest.mark.parametrize(
    "report",
    [
        {"identity": "\ud800"},
        {"\udfff": 1},
        {"nested": ["ok", {"value": "\udc00"}]},
        {"nested": ("\ud83d\ude00",)},
    ],
    ids=["high-surrogate", "surrogate-key", "nested-low", "escaped-pair"],
)
def test_report_rejects_unpaired_unicode_scalar_values_before_stdout(
    report: dict[str, object],
) -> None:
    """JSON escapes of invalid Unicode scalars are not evidence identities."""
    output = _FakeStream("healthy")
    with pytest.raises(report_output.ReportOutputError, match="JSON serialization"):
        report_output.publish(report, output)
    assert not output.records
    assert not output.flushed


def test_report_accepts_valid_non_bmp_unicode_scalar() -> None:
    """An actual Unicode scalar remains a normal JSON string value."""
    output = _FakeStream("healthy")
    record = {"identity": "\U0001f600"}
    report_output.publish(record, output)
    assert output.records == [json.dumps(record, sort_keys=True, indent=2) + "\n"]
    assert output.flushed


@pytest.mark.parametrize(
    "mutation",
    ["replace-scalar", "append-nested-item", "add-field", "remove-field"],
)
def test_mutating_public_json_dumps_cannot_rewrite_report_before_publication(
    monkeypatch: pytest.MonkeyPatch, mutation: str
) -> None:
    """Source-bound JSON must describe the report before untrusted encoding."""
    output = _FakeStream("healthy")
    report: dict[str, object] = {"status": "ready", "rows": [1]}
    native_dumps = json.dumps

    def substituted_dumps(_value: object, **_options: object) -> str:
        if mutation == "replace-scalar":
            report["status"] = "forged"
        elif mutation == "append-nested-item":
            rows = report["rows"]
            assert type(rows) is list
            rows.append(2)
        elif mutation == "add-field":
            report["extra"] = "forged"
        else:
            del report["rows"]
        return native_dumps(report, sort_keys=True, indent=2, allow_nan=False)

    monkeypatch.setattr(report_output.json, "dumps", substituted_dumps)
    with pytest.raises(report_output.ReportOutputError, match="JSON serialization"):
        report_output.publish(report, output)
    assert not output.records
    assert not output.flushed


def test_replaced_length_lookup_cannot_certify_short_stdout_write(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A substituted report-length provider cannot attest a partial record."""
    output = _FakeStream(SHORT_MODE)
    source_length = len
    monkeypatch.setattr(
        report_output,
        "len",
        lambda record: source_length(record) // 2,
        raising=False,
    )
    with pytest.raises(report_output.ReportOutputError, match=BAD_LENGTH):
        report_output.publish({"status": "reported"}, output)
    assert output.records
    assert not output.flushed


def test_replaced_length_lookup_cannot_reject_complete_stdout_write(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A narrower runtime hint cannot invalidate an exact successful write."""
    output = _FakeStream("healthy")
    monkeypatch.setattr(report_output, "len", lambda _record: 0, raising=False)
    report_output.publish({"status": "reported"}, output)
    assert output.flushed
    assert len(output.records) == 1


def test_replaced_unicode_scanner_cannot_admit_lone_surrogate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A false scanner result cannot admit non-scalar evidence identifiers."""
    output = _FakeStream("healthy")
    monkeypatch.setattr(report_output, "any", lambda _values: False, raising=False)
    with pytest.raises(report_output.ReportOutputError, match="JSON serialization"):
        report_output.publish({"identity": "\ud800"}, output)
    assert not output.records
    assert not output.flushed


def test_replaced_unicode_scanner_cannot_reject_valid_scalar(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A true scanner hint cannot reject an otherwise valid JSON report."""
    output = _FakeStream("healthy")
    monkeypatch.setattr(report_output, "any", lambda _values: True, raising=False)
    report_output.publish({"identity": "\U0001f600"}, output)
    assert output.flushed
    assert len(output.records) == 1


@pytest.mark.parametrize("provider", ["set", "id"])
def test_nested_json_cannot_skip_source_unicode_preflight(
    monkeypatch: pytest.MonkeyPatch, provider: str
) -> None:
    """A replaced traversal identity cannot skip nested Unicode checks."""
    output = _FakeStream("healthy")
    report = {"outer": {"identity": "\ud800"}}

    if provider == "set":

        class AlwaysSeen(set[int]):
            def __contains__(self, _value: object) -> bool:
                return True

        monkeypatch.setattr(report_output, "set", AlwaysSeen, raising=False)
    else:
        monkeypatch.setattr(report_output, "id", lambda _value: 1, raising=False)

    with pytest.raises(report_output.ReportOutputError, match="JSON serialization"):
        report_output.publish(report, output)
    assert not output.records
    assert not output.flushed


@pytest.mark.parametrize(
    ("value", "fake_ordinal", "should_accept"),
    [("\ud800", 65, False), ("\U0001f600", 0xD800, True)],
)
def test_unicode_ordinal_provider_must_match_native_scanner(
    monkeypatch: pytest.MonkeyPatch,
    value: str,
    fake_ordinal: int,
    should_accept: bool,
) -> None:
    """Unicode validation cannot depend on a replaced character ordinal."""
    output = _FakeStream("healthy")
    monkeypatch.setattr(
        report_output, "ord", lambda _character: fake_ordinal, raising=False
    )
    if should_accept:
        report_output.publish({"identity": value}, output)
        assert output.flushed
        assert len(output.records) == 1
    else:
        with pytest.raises(report_output.ReportOutputError, match="JSON serialization"):
            report_output.publish({"identity": value}, output)
        assert not output.records
        assert not output.flushed
