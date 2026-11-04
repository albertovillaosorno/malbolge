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
#   - Live host-C reference pilot and retained-evidence integration checks.
# - Must-Not:
#   - Claim that real host-C timing measures Malbolge candidate performance.
# - Allows:
#   - Inputs: bounded generated C challenge families and injected run failures.
#   - Outputs: paired cross-difficulty raw/manifests and accepted-stage checks.
#   - Side effects: session-local ignored native executable and CSV samples.
# - Split-When:
#   - Product compiler measurements require separately trusted verifier tests.
# - Merge-When:
#   - Research reference measurement tests become a governed runner suite.
# - Summary:
#   - Tests real measured host stages and fail-closed retained trial outcomes.
# - Description:
#   - Uses pinned Clang and the original canonical challenge oracle.
# - Usage:
#   - `pytest benchmarks/arena/tests/test_reference_study.py`.
# - Defaults:
#   - A source-reported host result is never Malbolge compiler evidence.
#

"""Bounded real host-C pilot studies, not Malbolge candidate measurements."""

# ruff: file-ignore[assert]

from __future__ import annotations

import json
import shutil
import sys
from hashlib import sha256
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any, cast

import pytest

from benchmarks.arena import (
    analyze,
    evidence,
    host_c_oracle,
    reference_study,
    report_output,
)

if TYPE_CHECKING:
    from pathlib import Path

    from benchmarks.challenges import generate

REPETITIONS = 2
CAPACITY_POINTS = 4
OPTIMIZED_MODE = "-O2"
FAILED = "tool_failed"
ARTIFACT_METRIC = "artifact_bytes"
EXPECTED_ROWS = 8
FAMILY = "arithmetic-dag"
OUTPUT_FAULT = "injected short stdout write"


@pytest.mark.parametrize(
    "providers",
    ("cached-encoder-only", "writer-only", "cached-encoder-and-writer"),
)
def test_host_reference_quoted_provenance_rejects_forged_json_provider(
    monkeypatch: pytest.MonkeyPatch,
    providers: str,
) -> None:
    """JSON provider substitution cannot relabel retained TOML provenance."""
    source = "actual-git-revision"
    forged = json.dumps("forged-git-revision")
    assert forged != json.dumps(source)

    class ForgedEncoder:
        def __init__(self, **_kwargs: object) -> None:
            pass

        def encode(self, _value: object) -> str:
            return forged

    with monkeypatch.context() as patch:
        if providers != "writer-only":
            # json.dumps on simple strings consults its cached default
            # encoder, not the mutable public JSONEncoder class.
            patch.setattr(json, "_default_encoder", ForgedEncoder())
        if providers != "cached-encoder-only":
            patch.setattr(json, "dumps", lambda *_args, **_kwargs: forged)
        assert json.dumps(source, ensure_ascii=True) == forged
        with pytest.raises(
            reference_study.ReferenceStudyError,
            match="JSON quote serializer disagrees with source",
        ):
            _ = reference_study._quote(source)  # ruff: ignore[private-member-access]


JSON_QUOTE_WRITER = "_quote"


@pytest.mark.parametrize("method", ["encode", "iterencode"])
@pytest.mark.parametrize(
    "case",
    [
        ("_quote", "real-host-commit", '"forged-commit"', "JSON quote"),
        (
            "_retained_json_text",
            {"observations": [{"elapsed_ns": 7}]},
            '{"observations": [{"elapsed_ns": 900}]}',
            "retained JSON",
        ),
    ],
)
def test_host_reference_rejects_shared_encoder_method_forgery(
    monkeypatch: pytest.MonkeyPatch,
    method: str,
    case: tuple[str, object, str, str],
) -> None:
    """Both host-C serializers must reject a shared native method forgery."""
    writer_name, source, forged, diagnostic = case
    writer = getattr(reference_study, writer_name)
    assert writer(source) != forged

    def fake_encode(*args: object, **kwargs: object) -> str:
        del args, kwargs
        return forged

    def fake_iterencode(*args: object, **kwargs: object) -> list[str]:
        del args, kwargs
        return [forged]

    replacement = {"encode": fake_encode, "iterencode": fake_iterencode}
    with monkeypatch.context() as patch:
        patch.setattr(json.JSONEncoder, method, replacement[method])
        with pytest.raises(
            reference_study.ReferenceStudyError, match=diagnostic
        ):
            _ = writer(source)


@pytest.mark.parametrize("writer_name", ["_quote", "_retained_json_text"])
@pytest.mark.parametrize(
    "provider",
    ["encode_basestring_ascii", "c_make_encoder", "_make_iterencode"],
)
def test_host_reference_rejects_shared_json_factory_substitution(
    monkeypatch: pytest.MonkeyPatch, writer_name: str, provider: str,
) -> None:
    """Matching mutable JSON factory receipts do not authenticate values."""
    original = getattr(json.encoder, provider, None)
    if not callable(original):
        pytest.skip("native JSON encoder provider unavailable")
    value = (
        "source-commit" if writer_name == JSON_QUOTE_WRITER else {"reported": 7}
    )
    writer = getattr(reference_study, writer_name)

    def replacement(*args: object, **kwargs: object) -> object:
        return original(*args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(json.encoder, provider, replacement)
        with pytest.raises(reference_study.ReferenceStudyError, match="source"):
            _ = writer(value)


@pytest.mark.parametrize("writer_name", ["_quote", "_retained_json_text"])
def test_host_reference_rejects_midcall_json_factory_swap(
    monkeypatch: pytest.MonkeyPatch, writer_name: str,
) -> None:
    """A public writer cannot swap source factories after its own call."""
    native_dumps = json.dumps
    factory_name = "_make_iterencode"
    native_factory = getattr(json.encoder, factory_name)
    value = (
        "real-source" if writer_name == JSON_QUOTE_WRITER else {"elapsed_ns": 7}
    )
    writer = getattr(reference_study, writer_name)
    with monkeypatch.context() as patch:

        def swapped_dumps(*args: object, **kwargs: object) -> str:
            receipt = native_dumps(*args, **kwargs)

            def replacement(
                *factory_args: object, **factory_kwargs: object
            ) -> object:
                return native_factory(*factory_args, **factory_kwargs)

            patch.setattr(json.encoder, factory_name, replacement)
            return receipt

        patch.setattr(json, "dumps", swapped_dumps)
        with pytest.raises(reference_study.ReferenceStudyError, match="source"):
            _ = writer(value)


class _ForeignQuote(str):
    """A hostile writer receipt cannot supply equality hooks."""

    def __eq__(self, other: object) -> bool:
        del other
        raise AssertionError("foreign TOML quote comparison invoked")

    __hash__ = str.__hash__


@pytest.mark.parametrize("receipt", (None, b'"forged"', _ForeignQuote('"forged"')))
def test_host_reference_quoted_provenance_rejects_foreign_receipt(
    monkeypatch: pytest.MonkeyPatch,
    receipt: object,
) -> None:
    """Only native exact JSON strings may become TOML provenance."""
    with monkeypatch.context() as patch:
        patch.setattr(json, "dumps", lambda *_args, **_kwargs: receipt)
        with pytest.raises(
            reference_study.ReferenceStudyError,
            match="JSON quote serializer disagrees with source",
        ):
            _ = reference_study._quote("actual-commit")  # ruff: ignore[private-member-access]


def test_host_reference_quoted_provenance_contains_writer_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Publisher JSON faults remain typed without foreign error text."""
    failure = RuntimeError("forged external writer failure")

    def broken_writer(*_args: object, **_kwargs: object) -> str:
        raise failure

    with monkeypatch.context() as patch:
        patch.setattr(json, "dumps", broken_writer)
        with pytest.raises(
            reference_study.ReferenceStudyError,
            match="JSON quote serializer failed: RuntimeError",
        ) as caught:
            _ = reference_study._quote("actual-commit")  # ruff: ignore[private-member-access]
        assert caught.value.__cause__ is failure


def test_host_reference_quoted_provenance_accepts_equivalent_json_encoder(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Equivalent public encoders preserve canonical retained quote bytes."""
    encoder = json.JSONEncoder
    native_dumps = json.dumps
    text = "a-path\nwith-escapes"
    expected = native_dumps(text, ensure_ascii=True)

    class EquivalentEncoder(encoder):
        pass

    with monkeypatch.context() as patch:
        patch.setattr(json, "JSONEncoder", EquivalentEncoder)
        patch.setattr(json, "dumps", lambda *a, **kw: native_dumps(*a, **kw))
        assert reference_study._quote(text) == expected  # ruff: ignore[private-member-access]


@pytest.mark.parametrize(
    "text",
    (
        "actual-git-revision",
        'path\\with "quotes"',
        "unicode-\u00e9\nnewline",
        "\tbackslash\\tab",
    ),
)
def test_host_reference_quoted_provenance_preserves_exact_text(text: str) -> None:
    """Canonical TOML quote bytes retain all escaped source characters."""
    quoted = reference_study._quote(text)  # ruff: ignore[private-member-access]
    assert json.loads(quoted) == text


def test_host_reference_quoted_provenance_accepts_equivalent_cached_encoder(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An equivalent cached default encoder retains native TOML quoting."""
    text = 'commit\nwith "quotes"'
    expected = reference_study._quote(text)  # ruff: ignore[private-member-access]
    with monkeypatch.context() as patch:
        patch.setattr(json, "_default_encoder", json.JSONEncoder(ensure_ascii=True))
        assert reference_study._quote(text) == expected  # ruff: ignore[private-member-access]


def _is_retained_json_payload(payload: object, filename: str) -> bool:
    """Distinguish the four final study receipts without real child work."""
    if type(payload) is not dict:
        return False
    if filename == "failures.json":
        return payload.get("schema_version") == 1 and "failures" in payload
    if filename == "resource-controls.json":
        return payload.get("schema_version") == 2 and "limiter" in payload
    if filename == "artifacts.json":
        return payload == {}
    return "study" in payload and "observations" in payload


@pytest.mark.parametrize(
    "filename",
    ("failures.json", "resource-controls.json", "artifacts.json", "study.json"),
)
@pytest.mark.parametrize("provider", ("writer", "encoder", "joint"))
def test_host_reference_retained_json_rejects_forged_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    filename: str,
    provider: str,
) -> None:
    """Native trial receipts cannot be rewritten after provenance checks."""
    root = tmp_path / "study"
    root.mkdir()
    monkeypatch.setattr(reference_study, "_ROOT", tmp_path)
    monkeypatch.setattr(reference_study, "_write_case", lambda *_args: ([], {}))
    monkeypatch.setattr(reference_study, "_verify_report", lambda *_args: None)
    monkeypatch.setattr(reference_study, "check_retained_artifacts", lambda *_args: 0)
    monkeypatch.setattr(reference_study, "check_retained_failures", lambda *_args: 0)
    native_dumps = json.dumps
    native_encoder = json.JSONEncoder
    forged = '{"forged_verified_evidence":true}'

    class ForgedEncoder(native_encoder):
        def encode(self, o: Any) -> str:
            if _is_retained_json_payload(o, filename):
                return forged
            return super().encode(o)

    def forged_writer(payload: object, **options: Any) -> str:
        if _is_retained_json_payload(payload, filename):
            return forged
        return native_dumps(payload, **options)

    with monkeypatch.context() as patch:
        if provider in ("encoder", "joint"):
            patch.setattr(json, "JSONEncoder", ForgedEncoder)
        if provider in ("writer", "joint"):
            patch.setattr(json, "dumps", forged_writer)
        with pytest.raises(
            reference_study.ReferenceStudyError,
            match="retained JSON serializer disagrees with source",
        ):
            _ = reference_study._run_study(  # ruff: ignore[private-member-access]
                root, reference_study.StudyPlan(FAMILY, (4,), 7, 1), commit="a" * 40
            )
    assert not (root / filename).exists()


def test_host_reference_retained_json_rejects_writer_mutating_report(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Identical returned JSON is not permission to rewrite checked costs."""
    payload = {"observations": [{"metrics": {"elapsed_ns": 19}}]}
    before = json.dumps(payload, sort_keys=True, indent=2)
    native_dumps = json.dumps

    def mutating_writer(document: object, **options: Any) -> str:
        original = native_dumps(document, **options)
        payload["observations"][0]["metrics"]["elapsed_ns"] = 1
        return original

    with monkeypatch.context() as patch:
        patch.setattr(json, "dumps", mutating_writer)
        with pytest.raises(
            reference_study.ReferenceStudyError,
            match="retained JSON serializer disagrees with source",
        ):
            _ = reference_study._retained_json_text(payload)  # ruff: ignore[private-member-access]
    assert json.dumps(payload, sort_keys=True, indent=2) != before


def test_host_reference_retained_json_types_writer_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Serializer faults retain their cause without a forged sidecar."""
    failure = RuntimeError("foreign encoder error")

    def broken_writer(*_args: object, **_kwargs: object) -> str:
        raise failure

    with monkeypatch.context() as patch:
        patch.setattr(json, "dumps", broken_writer)
        with pytest.raises(
            reference_study.ReferenceStudyError,
            match="retained JSON serializer failed: RuntimeError",
        ) as caught:
            _ = reference_study._retained_json_text({"report": "actual"})  # ruff: ignore[private-member-access]
        assert caught.value.__cause__ is failure


def test_host_reference_retained_json_accepts_equivalent_public_encoder(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Equivalent JSON providers retain exact newline-terminated bytes."""
    native_encoder = json.JSONEncoder
    payload = {"observations": [0, "\u00e9"], "metadata": {"version": 2}}
    expected = json.dumps(payload, sort_keys=True, indent=2) + "\n"

    class EquivalentEncoder(native_encoder):
        pass

    with monkeypatch.context() as patch:
        patch.setattr(json, "JSONEncoder", EquivalentEncoder)
        assert reference_study._retained_json_text(payload) == expected  # ruff: ignore[private-member-access]


class _UnexpectedHostFault(IndexError):
    """Unexpected dependency errors cannot control study diagnostics."""

    def __str__(self) -> str:
        raise AssertionError("foreign dependency exception was formatted")


class _HostilePlatformName(str):
    def __format__(self, format_spec: str) -> str:
        del format_spec
        raise AssertionError("foreign host identity formatter executed")


@pytest.mark.parametrize("field", ["system", "machine", "node"])
@pytest.mark.parametrize(
    "invalid",
    [
        None,
        0,
        b"bad",
        "",
        " ",
        "host\nspoof",
        "a" * 257,
        _HostilePlatformName("bad"),
    ],
)
def test_reference_host_identity_rejects_invalid_platform_receipt_before_measurement(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    field: str,
    invalid: object,
) -> None:
    """Untrusted machine identity cannot enter a retained study record."""
    root = tmp_path / "study"
    root.mkdir()

    def forbidden(*args: object, **kwargs: object) -> None:
        del args, kwargs
        pytest.fail("invalid platform identity reached host-C measurement")

    monkeypatch.setattr(reference_study, "_ROOT", tmp_path)
    monkeypatch.setattr(reference_study, "_write_case", forbidden)
    monkeypatch.setattr(reference_study.platform, field, lambda: invalid)
    with pytest.raises(reference_study.ReferenceStudyError, match="host identity"):
        reference_study._run_study(  # ruff: ignore[private-member-access]
            root, reference_study.StudyPlan(FAMILY, (4,), 7, 1), commit="a" * 40
        )


def test_reference_host_identity_preserves_valid_native_components(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An ordinary platform identity retains all three host provenance fields."""
    monkeypatch.setattr(reference_study.platform, "system", lambda: "Linux")
    monkeypatch.setattr(reference_study.platform, "machine", lambda: "x86_64")
    monkeypatch.setattr(reference_study.platform, "node", lambda: "build-host")
    observed = reference_study._host_identity()  # ruff: ignore[private-member-access]
    assert observed == "Linux-x86_64-build-host"


@pytest.mark.parametrize("field", ["system", "machine", "node"])
def test_reference_host_identity_types_unexpected_platform_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    field: str,
) -> None:
    """Foreign host probes remain typed without invoking their formatter."""
    fault = _UnexpectedHostFault("foreign platform failure")
    root = tmp_path / "study"
    root.mkdir()

    def fail_probe() -> None:
        raise fault

    def forbidden(*args: object, **kwargs: object) -> None:
        del args, kwargs
        pytest.fail("failed platform probe reached measurement")

    monkeypatch.setattr(reference_study, "_ROOT", tmp_path)
    monkeypatch.setattr(reference_study, "_write_case", forbidden)
    monkeypatch.setattr(reference_study.platform, field, fail_probe)
    with pytest.raises(reference_study.ReferenceStudyError, match="host identity") as caught:
        reference_study._run_study(  # ruff: ignore[private-member-access]
            root, reference_study.StudyPlan(FAMILY, (4,), 7, 1), commit="a" * 40
        )
    assert caught.value.__cause__ is fault


def _pilot() -> tuple[Path, dict[str, Any]]:
    path, document = reference_study.run_study(
        reference_study.StudyPlan(FAMILY, (4, 8), 7, REPETITIONS),
    )
    return path, document


@pytest.mark.skipif(
    not host_c_oracle._PINNED_CLANG.is_file(),  # ruff: ignore[private-member-access]
    reason="repository pinned native Clang is unavailable",
)
def test_real_host_c_reference_pilot_links_all_trial_evidence() -> None:
    """Two real difficulty levels retain paired observed stage evidence."""
    path, document = _pilot()
    try:
        rows = document["observations"]
        assert len(rows) == EXPECTED_ROWS
        assert {row["case"]["difficulty"] for row in rows} == {4, 8}
        assert all(row["outcome"] == analyze.VERIFIED for row in rows)
        assert all(row["metrics"]["elapsed_ns"] > 0 for row in rows)
        assert all(row["metrics"]["peak_rss_bytes"] > 0 for row in rows)
        assert document["study"]["objectives"] == [
            "elapsed_ns",
            "artifact_bytes",
            "peak_rss_bytes",
        ]
        report = analyze.analyze(analyze.parse_document(json.dumps(document)))
        assert len(report["capacity_curve"]) == CAPACITY_POINTS
        linked = evidence.validate_links(
            analyze.parse_document(json.dumps(document)),
            reference_study._ROOT,  # ruff: ignore[private-member-access]
            policy=evidence.EvidencePolicy(
                require_trial_run_identity=True,
                require_budget_agreement=True,
                challenge_root=f"{path.relative_to(reference_study._ROOT)}/bundles",  # ruff: ignore[private-member-access]
                require_host_c_challenge_oracle=True,
            ),
        )
        assert linked["raw_rows_matched"] == EXPECTED_ROWS
        assert linked["trial_run_links_checked"] == EXPECTED_ROWS
        assert linked["regenerated_challenge_bundles"] == REPETITIONS
        assert linked["host_c_challenge_oracles_replayed"] == REPETITIONS
        artifacts = json.loads((path / "artifacts.json").read_text())
        assert len(artifacts) == EXPECTED_ROWS
        for artifact in artifacts.values():
            executable = reference_study._ROOT / artifact["path"]  # ruff: ignore[private-member-access]
            assert (
                sha256(executable.read_bytes()).hexdigest()
                == artifact["sha256"]
            )
    finally:
        shutil.rmtree(path)


@pytest.mark.parametrize(
    "sidecar",
    ["failures.json", "resource-controls.json", "artifacts.json", "study.json"],
)
@pytest.mark.parametrize("bad_count", [None, True, -1, 1, 1_000_000])
def test_reference_retained_sidecars_reject_incomplete_write_acknowledgement(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    *,
    sidecar: str,
    bad_count: object,
) -> None:
    """A short or foreign host write cannot publish a successful study."""
    root = tmp_path / "study"
    root.mkdir()
    original_write = type(root).write_text

    def faulty_write(
        path: Path,
        content: str,
        encoding: str | None = None,
    ) -> int:
        if path.name == sidecar:
            _ = original_write(path, content[:1], encoding=encoding)
            return cast("int", bad_count)
        return original_write(path, content, encoding=encoding)

    monkeypatch.setattr(reference_study, "_ROOT", tmp_path)
    monkeypatch.setattr(type(root), "write_text", faulty_write)
    monkeypatch.setattr(reference_study, "_write_case", lambda *_: ([], {}))
    monkeypatch.setattr(reference_study, "_verify_report", lambda *_: None)
    monkeypatch.setattr(
        reference_study, "check_retained_artifacts", lambda *_: 0
    )
    monkeypatch.setattr(
        reference_study, "check_retained_failures", lambda *_: 0
    )
    with pytest.raises(
        reference_study.ReferenceStudyError, match="write count"
    ):
        _ = reference_study._run_study(  # ruff: ignore[private-member-access]
            root,
            reference_study.StudyPlan(FAMILY, (4,), 7, 1),
            commit="0" * 40,
        )


class _HostileHostWriteArgument:
    def __str__(self) -> str:
        raise AssertionError("foreign native-error argument was formatted")


@pytest.mark.parametrize("kind", ["binary", "text"])
@pytest.mark.parametrize(
    "fault",
    [
        OSError("native host write denied"),
        OSError(_HostileHostWriteArgument()),
        _UnexpectedHostFault("foreign host write"),
    ],
    ids=["native-os", "hostile-os-argument", "unexpected-foreign"],
)
def test_retained_host_c_writer_errors_are_typed_and_preserve_causes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
    fault: Exception,
) -> None:
    """Writer faults cannot leave direct callers with untyped foreign errors."""
    path = tmp_path / "retained"

    def fail_write(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise fault

    if kind == "binary":
        monkeypatch.setattr(reference_study.Path, "write_bytes", fail_write)
    else:
        monkeypatch.setattr(reference_study.Path, "write_text", fail_write)
    with pytest.raises(reference_study.ReferenceStudyError, match="write failed") as caught:
        if kind == "binary":
            reference_study._write_retained_bytes(  # ruff: ignore[private-member-access]
                path, b"binary evidence"
            )
        else:
            reference_study._write_retained_text(  # ruff: ignore[private-member-access]
                path, "text evidence"
            )
    assert caught.value.__cause__ is fault
    if type(fault) is OSError and type(fault.args[0]) is str:
        assert "native host write denied" in str(caught.value)
    else:
        assert str(caught.value) == "host-C retained retained write failed"


@pytest.mark.parametrize("kind", ["binary", "text"])
@pytest.mark.parametrize("fault", ["missing", "altered"])
def test_retained_writer_does_not_trust_complete_count_without_matching_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
    fault: str,
) -> None:
    """Exact host write counts cannot certify a missing or corrupted sidecar."""
    path = tmp_path / "study.json"
    payload = b"original study evidence" if kind == "binary" else "study Ω evidence"
    actual = b"X" * len(payload) if kind == "binary" else "X" * len(payload)
    original_write_bytes = type(tmp_path).write_bytes
    original_write_text = type(tmp_path).write_text

    def fake_bytes(target: Path, content: bytes) -> int:
        if fault == "altered":
            _ = original_write_bytes(target, cast("bytes", actual))
        return len(content)

    def fake_text(
        target: Path, content: str, encoding: str | None = None
    ) -> int:
        if fault == "altered":
            _ = original_write_text(target, cast("str", actual), encoding=encoding)
        return len(content)

    if kind == "binary":
        monkeypatch.setattr(type(tmp_path), "write_bytes", fake_bytes)
    else:
        monkeypatch.setattr(type(tmp_path), "write_text", fake_text)
    with pytest.raises(reference_study.ReferenceStudyError, match="retained"):
        if kind == "binary":
            reference_study._write_retained_bytes(  # ruff: ignore[private-member-access]
                path, cast("bytes", payload)
            )
        else:
            reference_study._write_retained_text(  # ruff: ignore[private-member-access]
                path, cast("str", payload)
            )


class _ForeignRetainedBytes(bytes):  # ruff: ignore[subclass-builtin]
    """A subclass must not control size or equality after publication."""


class _ForeignRetainedText(str):  # ruff: ignore[subclass-builtin]
    """A string subclass must not bypass admission before host writes."""


@pytest.mark.parametrize(
    ("kind", "payload"),
    [
        ("binary", b""),
        ("binary", bytearray(b"mutable")),
        ("binary", _ForeignRetainedBytes(b"foreign")),
        ("binary", b"x" * (evidence.MAX_EVIDENCE_BYTES + 1)),
        ("text", ""),
        ("text", b"not Unicode text"),
        ("text", _ForeignRetainedText("foreign")),
        ("text", "\ud800"),
        ("text", "x" * (evidence.MAX_EVIDENCE_BYTES + 1)),
    ],
    ids=[
        "empty-binary",
        "mutable-binary",
        "subclass-binary",
        "oversized-binary",
        "empty-text",
        "binary-as-text",
        "subclass-text",
        "surrogate-text",
        "oversized-text",
    ],
)
def test_retained_writers_reject_invalid_payload_before_host_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
    payload: object,
) -> None:
    """Unadmitted content must never reach an observable filesystem write."""
    path = tmp_path / "untrusted-record"
    attempted: list[object] = []

    def writing(_target: Path, content: object, **_kwargs: object) -> int:
        attempted.append(content)
        return len(cast("Any", content))

    if kind == "binary":
        monkeypatch.setattr(type(path), "write_bytes", writing)
        writer = reference_study._write_retained_bytes
    else:
        monkeypatch.setattr(type(path), "write_text", writing)
        writer = reference_study._write_retained_text
    with pytest.raises(reference_study.ReferenceStudyError, match="bounded|UTF-8"):
        writer(path, cast("Any", payload))
    assert attempted == []
    assert not path.exists()


def test_retained_writer_rejects_expanded_utf8_before_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A short Unicode string can exceed the bounded byte budget after encoding."""
    path = tmp_path / "utf8-record"
    monkeypatch.setattr(evidence, "MAX_EVIDENCE_BYTES", 8)
    attempted: list[str] = []

    def writing(
        _path: Path, content: str, *, encoding: str | None = None
    ) -> int:
        attempted.append(content)
        assert encoding == "utf-8"
        return len(content)

    monkeypatch.setattr(type(path), "write_text", writing)
    with pytest.raises(reference_study.ReferenceStudyError, match="bounded UTF-8"):
        reference_study._write_retained_text(path, "🦉🦉🦉")
    assert attempted == []
    assert not path.exists()


@pytest.mark.parametrize("kind", ["binary", "text"])
def test_retained_writer_accepts_exact_file_bytes(
    tmp_path: Path,
    kind: str,
) -> None:
    """A real completed write remains usable, including non-ASCII UTF-8."""
    path = tmp_path / "study.json"
    if kind == "binary":
        reference_study._write_retained_bytes(  # ruff: ignore[private-member-access]
            path, b"\x00\xff completed artifact"
        )
        assert path.read_bytes() == b"\x00\xff completed artifact"
    else:
        reference_study._write_retained_text(  # ruff: ignore[private-member-access]
            path, "completed Ω 🦉 record"
        )
        assert path.read_bytes() == "completed Ω 🦉 record".encode()


@pytest.mark.parametrize(
    "sidecar",
    ["failures.json", "resource-controls.json", "artifacts.json", "study.json"],
)
@pytest.mark.parametrize("fault", ["missing", "altered"])
def test_host_c_study_never_completes_after_forged_sidecar_write_count(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    sidecar: str,
    fault: str,
) -> None:
    """A terminal study sidecar needs real byte agreement before publication."""
    root = tmp_path / "study"
    root.mkdir()
    original_write = type(root).write_text
    attempted = 0

    def fake_write(
        path: Path, content: str, encoding: str | None = None
    ) -> int:
        nonlocal attempted
        if path.name == sidecar:
            attempted += 1
            if fault == "altered":
                _ = original_write(path, "X" * len(content), encoding=encoding)
            return len(content)
        return original_write(path, content, encoding=encoding)

    monkeypatch.setattr(reference_study, "_ROOT", tmp_path)
    monkeypatch.setattr(type(root), "write_text", fake_write)
    monkeypatch.setattr(reference_study, "_write_case", lambda *_: ([], {}))
    monkeypatch.setattr(reference_study, "_verify_report", lambda *_: None)
    monkeypatch.setattr(reference_study, "check_retained_artifacts", lambda *_: 0)
    monkeypatch.setattr(reference_study, "check_retained_failures", lambda *_: 0)
    with pytest.raises(reference_study.ReferenceStudyError, match="retained"):
        _ = reference_study._run_study(  # ruff: ignore[private-member-access]
            root,
            reference_study.StudyPlan(FAMILY, (4,), 7, 1),
            commit="0" * 40,
        )
    assert attempted == 1


def test_retained_host_c_writer_bounds_native_diagnostic_text(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Native error detail remains printable and bounded on a failed write."""
    path = tmp_path / "retained"
    fault = OSError("disk\n" + "x" * 1000)

    def fail_write(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise fault

    monkeypatch.setattr(reference_study.Path, "write_bytes", fail_write)
    with pytest.raises(reference_study.ReferenceStudyError) as caught:
        reference_study._write_retained_bytes(  # ruff: ignore[private-member-access]
            path, b"bounded evidence"
        )
    message = str(caught.value)
    assert caught.value.__cause__ is fault
    assert message.startswith("host-C retained retained write failed: disk?xxx")
    assert "\n" not in message
    assert len(message) <= len("host-C retained retained write failed: ") + 256


@pytest.mark.parametrize(
    "filename",
    [
        "program.c",
        "oracle.bin",
        "manifest.json",
        "host-clang-O0-nodes-4-trial-0",
        "host-clang-O0-nodes-4-trial-0.csv",
        "host-clang-O0-nodes-4-trial-0.toml",
    ],
)
@pytest.mark.parametrize("bad_count", [None, True, -1, 1, 1_000_000])
def test_reference_evidence_rejects_incomplete_write_acknowledgement(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    *,
    filename: str,
    bad_count: object,
) -> None:
    """No incomplete retained evidence write may be a verified trial."""
    original_bytes = type(tmp_path).write_bytes
    original_text = type(tmp_path).write_text
    matched = 0

    def faulty_bytes(path: Path, payload: bytes) -> int:
        nonlocal matched
        if path.name == filename:
            matched += 1
            _ = original_bytes(path, payload[:1])
            return cast("int", bad_count)
        return original_bytes(path, payload)

    def faulty_text(
        path: Path,
        payload: str,
        encoding: str | None = None,
    ) -> int:
        nonlocal matched
        if path.name == filename:
            matched += 1
            _ = original_text(path, payload[:1], encoding=encoding)
            return cast("int", bad_count)
        return original_text(path, payload, encoding=encoding)

    monkeypatch.setattr(reference_study, "_ROOT", tmp_path)
    monkeypatch.setattr(reference_study, "_LOCAL", tmp_path)
    monkeypatch.setattr(reference_study, "_commit", lambda: "0" * 40)
    monkeypatch.setattr(
        host_c_oracle, "require_child_resource_controls", lambda: None
    )
    monkeypatch.setattr(
        host_c_oracle,
        "measure_reference",
        lambda *_: host_c_oracle.ReferenceMeasurement(
            10, b"fake-executable", 1024
        ),
    )
    monkeypatch.setattr(type(tmp_path), "write_bytes", faulty_bytes)
    monkeypatch.setattr(type(tmp_path), "write_text", faulty_text)
    with pytest.raises(
        reference_study.ReferenceStudyError, match="write count"
    ):
        _ = reference_study.run_study(
            reference_study.StudyPlan(FAMILY, (4,), 7, 1)
        )
    assert matched == 1


@pytest.mark.parametrize(
    "plan",
    [
        reference_study.StudyPlan(FAMILY, (), 7, 1),
        reference_study.StudyPlan(FAMILY, (4, 4), 7, 1),
        reference_study.StudyPlan(FAMILY, (1, 2, 3, 4, 5), 7, 1),
        reference_study.StudyPlan(FAMILY, (4,), 7, 0),
        reference_study.StudyPlan(FAMILY, (4,), 7, 6),
        reference_study.StudyPlan(FAMILY, (513,), 7, 1),
    ],
)
def test_invalid_study_plan_fails_before_creating_output(
    plan: reference_study.StudyPlan,
) -> None:
    """Rejected setup does not create an empty published study directory."""
    with pytest.raises((reference_study.ReferenceStudyError, ValueError)):
        reference_study.run_study(plan)


@pytest.mark.parametrize(
    "foreign",
    [None, {}, object()],
)
def test_direct_host_reference_rejects_foreign_plan_before_native_probe(
    foreign: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Direct callers cannot use a foreign plan to reach host tools."""

    def forbidden_probe() -> None:
        pytest.fail("foreign plan reached native resource admission")

    monkeypatch.setattr(
        host_c_oracle, "require_child_resource_controls", forbidden_probe
    )
    with pytest.raises(reference_study.ReferenceStudyError, match="exact StudyPlan"):
        reference_study.run_study(cast("reference_study.StudyPlan", foreign))


@pytest.mark.parametrize(
    "foreign",
    [None, 3, [4], ("4",), (True,), ([4],), (object(),)],
)
def test_direct_host_reference_rejects_foreign_difficulties_before_native_probe(
    foreign: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Malformed and unhashable difficulty collections fail as typed errors."""

    def forbidden_probe() -> None:
        pytest.fail("foreign difficulties reached native resource admission")

    monkeypatch.setattr(
        host_c_oracle, "require_child_resource_controls", forbidden_probe
    )
    plan = reference_study.StudyPlan(
        FAMILY, cast("tuple[int, ...]", foreign), 7, 1
    )
    with pytest.raises(reference_study.ReferenceStudyError, match="integer tuple"):
        reference_study.run_study(plan)


@pytest.mark.parametrize(
    ("family", "seed", "difficulties"),
    [
        (None, 7, (4,)),
        ("invalid-family", 7, (4,)),
        (FAMILY, -1, (4,)),
        (FAMILY, True, (4,)),
        (FAMILY, 7, (513,)),
    ],
)
def test_invalid_host_reference_identity_rejects_before_native_probe(
    family: object,
    seed: object,
    difficulties: tuple[int, ...],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Invalid generated workloads never trigger host resource discovery."""

    def forbidden_probe() -> None:
        pytest.fail("invalid challenge identity reached native resource admission")

    monkeypatch.setattr(
        host_c_oracle, "require_child_resource_controls", forbidden_probe
    )
    plan = reference_study.StudyPlan(
        cast("str", family), difficulties, cast("int", seed), 1
    )
    with pytest.raises(ValueError):
        reference_study.run_study(plan)


@pytest.mark.parametrize("trial_count", [True, 1.5, "2", None])
def test_noninteger_trial_count_rejects_before_native_or_output_setup(
    trial_count: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A foreign trial count must never probe resource tools or create a run."""

    def forbid_resource_probe() -> None:
        pytest.fail("malformed trial count reached native resource admission")

    monkeypatch.setattr(
        host_c_oracle, "require_child_resource_controls", forbid_resource_probe
    )
    with pytest.raises(reference_study.ReferenceStudyError, match="trial count"):
        reference_study.run_study(
            reference_study.StudyPlan(FAMILY, (4,), 7, cast("int", trial_count))
        )


@pytest.mark.parametrize(
    "invalid",
    [True, 0, b"/usr/bin/git", "", "git", "../git", "/usr/bin/git\0bad", "\ud800"],
    ids=[
        "boolean",
        "integer",
        "bytes",
        "empty",
        "relative",
        "parent",
        "nul",
        "unicode",
    ],
)
def test_reference_git_resolver_rejects_invalid_executable_before_launch(
    monkeypatch: pytest.MonkeyPatch, invalid: object
) -> None:
    """Host Git identity must use an absolute, exact, encodable path."""

    def forbidden(*args: object, **kwargs: object) -> None:
        del args, kwargs
        pytest.fail("invalid Git resolver output launched subprocess")

    monkeypatch.setattr(
        reference_study.shutil, "which", lambda *_args, **_kwargs: invalid
    )
    monkeypatch.setattr(reference_study.sp, "run", forbidden)
    with pytest.raises(reference_study.ReferenceStudyError, match="Git executable"):
        reference_study._commit()  # ruff: ignore[private-member-access]


@pytest.mark.parametrize("kind", ["symlink", "directory", "non-executable", "missing"])
def test_reference_git_rejects_nonphysical_executable_before_launch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: str
) -> None:
    """Source provenance must not execute a linked or nonregular Git tool."""
    path = tmp_path / "git"
    if kind == "symlink":
        target = tmp_path / "genuine-git"
        _ = target.write_bytes(b"bin")
        target.chmod(0o700)
        path.symlink_to(target)
    elif kind == "directory":
        path.mkdir()
    elif kind == "non-executable":
        _ = path.write_bytes(b"bin")
        path.chmod(0o600)

    def forbidden(*args: object, **kwargs: object) -> object:
        del args, kwargs
        pytest.fail("untrusted physical Git executable reached child launch")

    monkeypatch.setattr(reference_study.shutil, "which", lambda *_args, **_kw: str(path))
    monkeypatch.setattr(reference_study.sp, "run", forbidden)
    with pytest.raises(reference_study.ReferenceStudyError, match="Git executable") as error:
        reference_study._commit()  # ruff: ignore[private-member-access]
    if kind == "missing":
        assert isinstance(error.value.__cause__, FileNotFoundError)


@pytest.mark.parametrize("access_result", [False, None, True, 1, "yes", object()])
def test_reference_git_requires_native_positive_executable_access(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, access_result: object
) -> None:
    """Only a literal successful OS executable-access receipt permits Git."""
    path = tmp_path / "git"
    _ = path.write_bytes(b"bin")
    path.chmod(0o700)
    monkeypatch.setattr(reference_study.shutil, "which", lambda *_args, **_kw: str(path))
    monkeypatch.setattr(reference_study.os, "access", lambda *_args: access_result)
    if access_result is True:
        monkeypatch.setattr(
            reference_study.sp,
            "run",
            lambda command, **_kw: reference_study.sp.CompletedProcess(
                command, 0, stdout="a" * 40 + "\n", stderr=""
            ),
        )
        assert reference_study._commit() == "a" * 40  # ruff: ignore[private-member-access]
    else:
        def forbidden(*args: object, **kwargs: object) -> object:
            del args, kwargs
            pytest.fail("invalid Git execute receipt reached child launch")

        monkeypatch.setattr(reference_study.sp, "run", forbidden)
        with pytest.raises(reference_study.ReferenceStudyError, match="Git executable"):
            reference_study._commit()  # ruff: ignore[private-member-access]


@pytest.mark.parametrize(
    "fault_type",
    [
        OSError,
        ValueError,
        RuntimeError,
        TypeError,
        AttributeError,
        _UnexpectedHostFault,
    ],
)
@pytest.mark.parametrize("site", ["status", "access"])
def test_reference_git_physical_preflight_faults_are_typed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault_type: type[Exception],
    site: str,
) -> None:
    """Host executable inspection faults preserve the original typed cause."""
    path = tmp_path / "git"
    _ = path.write_bytes(b"bin")
    path.chmod(0o700)
    monkeypatch.setattr(reference_study.shutil, "which", lambda *_args, **_kw: str(path))

    def broken(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise fault_type("injected host Git inspection fault")

    if site == "status":
        original_lstat = type(path).lstat

        def injected_lstat(candidate: Path) -> object:
            if candidate == path:
                return broken()
            return original_lstat(candidate)

        monkeypatch.setattr(type(path), "lstat", injected_lstat)
    else:
        monkeypatch.setattr(reference_study.os, "access", broken)
    with pytest.raises(reference_study.ReferenceStudyError, match="Git executable") as caught:
        reference_study._commit()  # ruff: ignore[private-member-access]
    assert type(caught.value.__cause__) is fault_type


@pytest.mark.parametrize(
    "failure_type",
    [
        OSError,
        ValueError,
        RuntimeError,
        TypeError,
        AttributeError,
        _UnexpectedHostFault,
    ],
)
def test_reference_git_resolver_fault_preserves_typed_source_error(
    monkeypatch: pytest.MonkeyPatch, failure_type: type[Exception]
) -> None:
    """Host tool selection faults must not escape source identity admission."""
    message = "injected Git resolver failure"

    def broken(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise failure_type(message)

    monkeypatch.setattr(reference_study.shutil, "which", broken)
    with pytest.raises(
        reference_study.ReferenceStudyError, match="Git lookup"
    ) as captured:
        reference_study._commit()  # ruff: ignore[private-member-access]
    assert type(captured.value.__cause__) is failure_type


class _HostileGitEnvironmentKey(str):
    def startswith(self, prefix: str | tuple[str, ...], *args: object) -> bool:
        del prefix, args
        raise AssertionError("foreign Git environment key method called")


@pytest.mark.parametrize("scenario", ["read-fault", "foreign-key", "foreign-value"])
def test_reference_git_environment_admission_precedes_child_launch(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    scenario: str,
) -> None:
    """Host environment failures and foreign keys fail before Git is invoked."""
    executable = tmp_path / "git"
    executable.write_bytes(b"native executable")
    executable.chmod(0o700)
    fault = _UnexpectedHostFault("environment snapshot failed")

    class ForeignEnvironment(dict[str, str]):
        def items(self) -> Any:
            if scenario == "read-fault":
                raise fault
            if scenario == "foreign-key":
                return [(_HostileGitEnvironmentKey("GIT_DIR"), "redirected")]
            return [("PATH", object())]

    def forbidden(*args: object, **kwargs: object) -> None:
        del args, kwargs
        pytest.fail("invalid Git environment reached child launch")

    monkeypatch.setattr(reference_study.shutil, "which", lambda *_a, **_k: str(executable))
    monkeypatch.setattr(reference_study.os, "environ", ForeignEnvironment())
    monkeypatch.setattr(reference_study.sp, "run", forbidden)
    with pytest.raises(reference_study.ReferenceStudyError, match="Git environment") as caught:
        reference_study._commit()  # ruff: ignore[private-member-access]
    if scenario == "read-fault":
        assert caught.value.__cause__ is fault


def test_reference_git_environment_sanitizer_preserves_native_values(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Native environment fields survive while Git selectors are removed."""
    executable = tmp_path / "git"
    executable.write_bytes(b"native executable")
    executable.chmod(0o700)

    class NativeEnvironment(dict[str, str]):
        def items(self) -> Any:
            return [("GIT_DIR", "/malicious-redirect"), ("PATH", "/usr/bin")]

    def fake_git(command: list[str], **kwargs: object) -> object:
        assert kwargs["env"] == {"PATH": "/usr/bin"}
        return reference_study.sp.CompletedProcess(
            command, 0, stdout="a" * 40 + "\n", stderr=""
        )

    monkeypatch.setattr(reference_study.shutil, "which", lambda *_a, **_k: str(executable))
    monkeypatch.setattr(reference_study.os, "environ", NativeEnvironment())
    monkeypatch.setattr(reference_study.sp, "run", fake_git)
    assert reference_study._commit() == "a" * 40  # ruff: ignore[private-member-access]


@pytest.mark.parametrize("bad_output", [None, True, b"0" * 40, "missing"])
def test_reference_git_rejects_nontext_revision_receipts(
    monkeypatch: pytest.MonkeyPatch, bad_output: object
) -> None:
    """A fake subprocess's malformed receipt cannot authorize producer output."""

    def fake_run(*args: object, **kwargs: object) -> object:
        del args, kwargs
        if bad_output == "missing":
            return object()
        return type("FakeCompleted", (), {"stdout": bad_output})()

    monkeypatch.setattr(reference_study.sp, "run", fake_run)
    with pytest.raises(reference_study.ReferenceStudyError, match="source commit"):
        reference_study._commit()  # ruff: ignore[private-member-access]


@pytest.mark.parametrize("exit_status", [None, False, True, "0", 1, -1, float("nan")])
def test_reference_git_rejects_malformed_or_failed_exit_receipts(
    monkeypatch: pytest.MonkeyPatch, exit_status: object
) -> None:
    """A commit-shaped stdout string never overrides child exit failure."""
    expected = "a" * 40

    def fake_run(*args: object, **kwargs: object) -> object:
        del args, kwargs
        return reference_study.sp.CompletedProcess(
            ["git", "rev-parse", "HEAD"],
            cast("int", exit_status),
            stdout=expected + "\n",
        )

    monkeypatch.setattr(reference_study.sp, "run", fake_run)
    with pytest.raises(reference_study.ReferenceStudyError, match="source commit exit"):
        reference_study._commit()  # ruff: ignore[private-member-access]


def test_reference_git_accepts_exact_zero_exit_and_revision(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Valid subprocess completion still records the exact source commit."""
    expected = "a" * 40

    def fake_run(command: list[str], **kwargs: object) -> object:
        assert kwargs["check"] is True
        assert kwargs["shell"] is False
        return reference_study.sp.CompletedProcess(
            command, 0, stdout=expected + "\n", stderr=""
        )

    monkeypatch.setattr(reference_study.sp, "run", fake_run)
    assert reference_study._commit() == expected  # ruff: ignore[private-member-access]


def test_reference_git_rejects_copied_successful_command_receipt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A copied Git completion argv cannot impersonate the launched request."""

    def forged(command: list[str], **_kwargs: object) -> object:
        return reference_study.sp.CompletedProcess(
            command.copy(), 0, stdout="a" * 40 + "\n", stderr=""
        )

    monkeypatch.setattr(reference_study.sp, "run", forged)
    with pytest.raises(reference_study.ReferenceStudyError, match="Git completion"):
        reference_study._commit()  # ruff: ignore[private-member-access]


class _HostileGitArgumentList(list[str]):
    """Foreign command collection cannot supply its own equality semantics."""

    def __eq__(self, other: object) -> bool:
        raise AssertionError("foreign Git command equality hook executed")


class _HostileGitStderr(str):
    """A foreign stderr string must be rejected before equality hooks."""

    def __eq__(self, other: object) -> bool:
        raise AssertionError("foreign Git stderr comparison executed")


@pytest.mark.parametrize(
    ("args_kind", "stderr_receipt"),
    [
        ("correct", "Git warning\n"),
        ("correct", b""),
        ("correct", None),
        ("correct", _HostileGitStderr("")),
        ("foreign", ""),
        ("tuple", ""),
        ("subclass", ""),
    ],
    ids=[
        "warning-stderr",
        "binary-stderr",
        "missing-stderr",
        "hostile-stderr",
        "foreign-command",
        "tuple-command",
        "hostile-command",
    ],
)
def test_reference_git_rejects_forged_process_completion(
    monkeypatch: pytest.MonkeyPatch, args_kind: str, stderr_receipt: object
) -> None:
    """Only the launched native Git process with empty native stderr can bind HEAD."""

    def forged(command: list[str], **_kwargs: object) -> object:
        recorded: object = (
            ["not-the-invoked-git", "rev-parse", "HEAD"]
            if args_kind == "foreign"
            else tuple(command)
            if args_kind == "tuple"
            else _HostileGitArgumentList(command)
            if args_kind == "subclass"
            else command
        )
        return reference_study.sp.CompletedProcess(
            recorded, 0, stdout="a" * 40 + "\n", stderr=stderr_receipt
        )

    monkeypatch.setattr(reference_study.sp, "run", forged)
    with pytest.raises(reference_study.ReferenceStudyError, match="Git completion"):
        reference_study._commit()  # ruff: ignore[private-member-access]


@pytest.mark.parametrize(
    "stdout",
    [" " + "a" * 40 + "\n", "a" * 40 + "\n\n", "a" * 40],
    ids=["leading-whitespace", "extra-newline", "missing-newline"],
)
def test_reference_git_rejects_noncanonical_revision_line(
    monkeypatch: pytest.MonkeyPatch, stdout: str
) -> None:
    """A merely strip-equivalent revision is not an exact Git stdout receipt."""

    def forged(command: list[str], **_kwargs: object) -> object:
        return reference_study.sp.CompletedProcess(
            command, 0, stdout=stdout, stderr=""
        )

    monkeypatch.setattr(reference_study.sp, "run", forged)
    with pytest.raises(reference_study.ReferenceStudyError, match="source commit"):
        reference_study._commit()  # ruff: ignore[private-member-access]


def test_reference_git_rejects_foreign_file_metadata_before_field_hooks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A returned foreign object must not manufacture native Git file metadata."""
    path = tmp_path / "git"
    path.write_bytes(b"native Git executable")
    path.chmod(0o700)
    monkeypatch.setattr(reference_study.shutil, "which", lambda *_a, **_kw: str(path))
    native_lstat = type(path).lstat

    class ForeignStat:
        @property
        def st_mode(self) -> int:
            pytest.fail("foreign metadata field hook executed")
            return 0

    def forged(candidate: Path) -> object:
        if candidate == path:
            return ForeignStat()
        return native_lstat(candidate)

    monkeypatch.setattr(type(path), "lstat", forged)
    with pytest.raises(reference_study.ReferenceStudyError, match="Git executable"):
        reference_study._commit()  # ruff: ignore[private-member-access]


@pytest.mark.parametrize(
    "failure_type",
    [
        OSError,
        ValueError,
        RuntimeError,
        TypeError,
        AttributeError,
        reference_study.sp.SubprocessError,
        _UnexpectedHostFault,
    ],
)
def test_reference_git_process_fault_preserves_typed_source_error(
    monkeypatch: pytest.MonkeyPatch, failure_type: type[Exception]
) -> None:
    """A host runner fault must not escape as an untyped producer failure."""

    def broken(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise failure_type("injected Git execution failure")

    monkeypatch.setattr(reference_study.sp, "run", broken)
    with pytest.raises(
        reference_study.ReferenceStudyError, match="cannot identify source commit"
    ) as captured:
        reference_study._commit()  # ruff: ignore[private-member-access]
    assert type(captured.value.__cause__) is failure_type


def test_host_reference_source_commit_preflight_does_not_orphan_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An unavailable source revision must reject before allocating evidence."""

    def rejected_commit() -> str:
        raise reference_study.ReferenceStudyError("source commit unavailable")

    def forbidden_workspace(*args: object, **kwargs: object) -> None:
        _ = (args, kwargs)
        pytest.fail("source identity failure allocated a study directory")

    monkeypatch.setattr(reference_study, "_validate_plan", lambda plan: None)
    monkeypatch.setattr(reference_study, "_commit", rejected_commit)
    monkeypatch.setattr(reference_study.tempfile, "mkdtemp", forbidden_workspace)
    with pytest.raises(
        reference_study.ReferenceStudyError, match="source commit unavailable"
    ):
        reference_study.run_study(reference_study.StudyPlan(FAMILY, (4,), 7, 1))


def test_host_reference_refuses_redirected_evidence_root_before_allocation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """A symlinked .temp cannot redirect retained host-C output outside the tree."""
    outside = tmp_path / "external"
    outside.mkdir()
    link = tmp_path / "redirected-root"
    link.symlink_to(outside, target_is_directory=True)

    def forbidden_workspace(*args: object, **kwargs: object) -> None:
        _ = (args, kwargs)
        pytest.fail("redirected root reached workspace allocation")

    monkeypatch.setattr(reference_study, "_validate_plan", lambda plan: None)
    monkeypatch.setattr(reference_study, "_commit", lambda: "0" * 40)
    monkeypatch.setattr(reference_study, "_LOCAL", link)
    monkeypatch.setattr(reference_study.tempfile, "mkdtemp", forbidden_workspace)
    with pytest.raises(reference_study.ReferenceStudyError, match="physical"):
        reference_study.run_study(reference_study.StudyPlan(FAMILY, (4,), 7, 1))
    assert list(outside.iterdir()) == []


@pytest.mark.parametrize("kind", ["missing", "regular-file"])
def test_host_reference_requires_an_existing_directory_for_output(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    kind: str,
) -> None:
    """Absent and non-directory .temp roots fail before any child is created."""
    root = tmp_path / "non-directory"
    if kind == "regular-file":
        root.write_bytes(b"not a directory")

    def forbidden_workspace(*args: object, **kwargs: object) -> None:
        _ = (args, kwargs)
        pytest.fail("invalid evidence root reached workspace allocation")

    monkeypatch.setattr(reference_study, "_validate_plan", lambda plan: None)
    monkeypatch.setattr(reference_study, "_commit", lambda: "0" * 40)
    monkeypatch.setattr(reference_study, "_LOCAL", root)
    monkeypatch.setattr(reference_study.tempfile, "mkdtemp", forbidden_workspace)
    with pytest.raises(reference_study.ReferenceStudyError, match="workspace"):
        reference_study.run_study(reference_study.StudyPlan(FAMILY, (4,), 7, 1))


@pytest.mark.parametrize("error_type", [ValueError, RuntimeError, _UnexpectedHostFault])
def test_host_reference_types_workspace_root_inspection_failures(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    error_type: type[Exception],
) -> None:
    """A host path-inspection error cannot escape the reference boundary."""

    def broken_lstat(path: Path) -> None:
        _ = path
        message = "injected host path inspection error"
        raise error_type(message)

    def forbidden_allocate(*args: object, **kwargs: object) -> None:
        _ = (args, kwargs)
        pytest.fail("failed root inspection allocated an output directory")

    monkeypatch.setattr(reference_study, "_validate_plan", lambda _: None)
    monkeypatch.setattr(reference_study, "_commit", lambda: "0" * 40)
    monkeypatch.setattr(reference_study, "_LOCAL", tmp_path)
    monkeypatch.setattr(reference_study.Path, "lstat", broken_lstat)
    monkeypatch.setattr(reference_study.tempfile, "mkdtemp", forbidden_allocate)
    with pytest.raises(
        reference_study.ReferenceStudyError, match="workspace root"
    ) as error:
        _ = reference_study.run_study(
            reference_study.StudyPlan(FAMILY, (4,), 7, 1)
        )
    assert isinstance(error.value.__cause__, error_type)


class _ForgedWorkspaceRootStat:
    """A dependency can falsely label a symlink as a physical directory."""

    st_mode = 0o040700


def test_host_reference_rejects_forged_workspace_root_metadata_before_allocation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """A foreign lstat receipt cannot make a linked local root authoritative."""
    outside = tmp_path / "outside"
    outside.mkdir()
    root = tmp_path / "linked"
    root.symlink_to(outside, target_is_directory=True)
    native_lstat = reference_study.Path.lstat
    allocated: list[str] = []

    def forged_stat(path: Path) -> object:
        if path == root:
            return _ForgedWorkspaceRootStat()
        return native_lstat(path)

    def forbid_allocate(**kwargs: object) -> str:
        del kwargs
        allocated.append("called")
        raise AssertionError("forged root metadata allocated host-C workspace")

    monkeypatch.setattr(reference_study, "_validate_plan", lambda _: None)
    monkeypatch.setattr(reference_study, "_commit", lambda: "0" * 40)
    monkeypatch.setattr(reference_study, "_LOCAL", root)
    monkeypatch.setattr(reference_study.Path, "lstat", forged_stat)
    monkeypatch.setattr(reference_study.tempfile, "mkdtemp", forbid_allocate)
    with pytest.raises(reference_study.ReferenceStudyError, match="workspace root"):
        reference_study.run_study(reference_study.StudyPlan(FAMILY, (4,), 7, 1))
    assert not allocated
    assert list(outside.iterdir()) == []


@pytest.mark.parametrize("forgery", ["suppressed", "redirected", "bad-close"])
def test_host_reference_workspace_scandir_cannot_certify_unsafe_entry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    forgery: str,
) -> None:
    """Untrusted scandir context hooks must not certify occupied workspaces."""
    folder = tmp_path / "arena-host-c-study-foreign"
    folder.mkdir()
    marker = folder / "preserve.txt"
    marker.write_bytes(b"untouched")
    closed: list[str] = []

    class ForgedScan:
        def __enter__(self) -> object:
            return iter(()) if forgery == "redirected" else self

        def __exit__(self, *_args: object) -> bool:
            return True

        def __iter__(self) -> ForgedScan:
            return self

        def __next__(self) -> object:
            if forgery == "suppressed":
                raise OSError("untrusted directory scan failed")
            if forgery == "bad-close":
                raise StopIteration
            return object()

        def close(self) -> object:
            closed.append("closed")
            return True if forgery == "bad-close" else None

    monkeypatch.setattr(reference_study, "_LOCAL", tmp_path)
    with monkeypatch.context() as scoped:
        scoped.setattr(reference_study.os, "scandir", lambda _directory: ForgedScan())
        with pytest.raises(reference_study.ReferenceStudyError, match="workspace"):
            reference_study._admit_study_workspace(str(folder))
    assert closed == ["closed"]
    assert marker.read_bytes() == b"untouched"


def test_host_reference_workspace_rejects_forged_empty_scandir_inventory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A foreign empty iterator cannot certify an occupied workspace."""
    folder = tmp_path / "arena-host-c-study-foreign"
    folder.mkdir()
    marker = folder / "preserve.txt"
    marker.write_bytes(b"untouched")
    closed = False

    class FalseEmptyScan:
        def __iter__(self) -> FalseEmptyScan:
            return self

        def __next__(self) -> object:
            raise StopIteration

        def close(self) -> None:
            nonlocal closed
            closed = True

    monkeypatch.setattr(reference_study, "_LOCAL", tmp_path)
    with monkeypatch.context() as scoped:
        scoped.setattr(reference_study.os, "scandir", lambda _folder: FalseEmptyScan())
        with pytest.raises(reference_study.ReferenceStudyError, match="workspace"):
            reference_study._admit_study_workspace(str(folder))
    assert closed
    assert marker.read_bytes() == b"untouched"


def test_host_reference_workspace_rejects_redirected_native_scandir_inventory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A real iterator over a different empty directory cannot certify ours."""
    folder = tmp_path / "arena-host-c-study-foreign"
    folder.mkdir()
    marker = folder / "preserve.txt"
    marker.write_bytes(b"untouched")
    decoy = tmp_path / "empty-decoy"
    decoy.mkdir()
    native_scandir = reference_study.os.scandir

    monkeypatch.setattr(reference_study, "_LOCAL", tmp_path)
    with monkeypatch.context() as scoped:
        scoped.setattr(
            reference_study.os, "scandir", lambda _folder: native_scandir(decoy)
        )
        with pytest.raises(reference_study.ReferenceStudyError, match="workspace"):
            reference_study._admit_study_workspace(str(folder))
    assert marker.read_bytes() == b"untouched"


class _ForgedWorkspaceName(str):
    """A foreign tempfile text receipt must not redirect output or cleanup."""


@pytest.mark.parametrize(
    "kind",
    [
        "parent-root",
        "outside-root",
        "symlink",
        "regular-file",
        "foreign-text",
        "foreign-type",
        "occupied-prefix",
        "relative-path",
    ],
)
def test_host_reference_rejects_unowned_workspace_before_writes_or_cleanup(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    kind: str,
) -> None:
    """A forged allocator return cannot target an existing foreign directory."""
    workspace_root = tmp_path / "workspaces"
    workspace_root.mkdir()
    outer = tmp_path / "other"
    outer.mkdir()
    target = workspace_root / "arena-host-c-study-unowned"
    if kind == "parent-root":
        target = workspace_root
    elif kind == "outside-root":
        target = outer
    elif kind == "symlink":
        target.symlink_to(outer, target_is_directory=True)
    elif kind == "regular-file":
        target.write_bytes(b"original")
    elif kind in ("foreign-text", "occupied-prefix"):
        target.mkdir()
        if kind == "occupied-prefix":
            (target / "original.txt").write_text("preserve")
    receipt: object = str(target)
    if kind == "foreign-text":
        receipt = _ForgedWorkspaceName(str(target))
    elif kind == "foreign-type":
        receipt = target
    elif kind == "relative-path":
        receipt = target.name
    attempted: list[str] = []

    def forged_allocate(**kwargs: object) -> object:
        del kwargs
        return receipt

    def forbidden_mkdir(*args: object, **kwargs: object) -> None:
        del args, kwargs
        attempted.append("mkdir")
        raise OSError("unadmitted workspace reached a write")

    def forbidden_cleanup(*args: object, **kwargs: object) -> None:
        del args, kwargs
        attempted.append("rmtree")

    monkeypatch.setattr(reference_study, "_LOCAL", workspace_root)
    monkeypatch.setattr(reference_study, "_validate_plan", lambda _: None)
    monkeypatch.setattr(reference_study, "_commit", lambda: "0" * 40)
    monkeypatch.setattr(reference_study.tempfile, "mkdtemp", forged_allocate)
    monkeypatch.setattr(reference_study.Path, "mkdir", forbidden_mkdir)
    monkeypatch.setattr(reference_study.shutil, "rmtree", forbidden_cleanup)
    with pytest.raises(reference_study.ReferenceStudyError, match="workspace"):
        reference_study.run_study(reference_study.StudyPlan(FAMILY, (4,), 7, 1))
    assert not attempted
    assert outer.is_dir()
    if kind == "regular-file":
        assert target.read_bytes() == b"original"
    if kind == "occupied-prefix":
        assert (target / "original.txt").read_text() == "preserve"


@pytest.mark.parametrize(
    "error_type", [OSError, ValueError, RuntimeError, _UnexpectedHostFault]
)
@pytest.mark.parametrize("failed_stage", ["allocate", "raw", "runs", "candidates"])
def test_host_reference_workspace_failures_are_typed_and_cleanup_own_output(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    *,
    failed_stage: str,
    error_type: type[Exception],
) -> None:
    """Failed setup cannot leak host errors or an incomplete local study."""
    directory = tmp_path / "arena-host-c-study-setup"
    original_mkdir = reference_study.Path.mkdir

    def faulty_mkdtemp(*, prefix: str, dir: Path) -> str:
        assert prefix == "arena-host-c-study-"
        assert dir == reference_study._LOCAL  # ruff: ignore[private-member-access]
        if failed_stage == "allocate":
            raise error_type("injected workspace allocation failure")
        original_mkdir(directory)
        return str(directory)

    def faulty_mkdir(
        path: Path, mode: int = 0o777, parents: bool = False, exist_ok: bool = False
    ) -> None:
        if path.parent == directory and path.name == failed_stage:
            raise error_type("injected workspace child failure")
        original_mkdir(path, mode=mode, parents=parents, exist_ok=exist_ok)

    def forbidden_measurement(*args: object, **kwargs: object) -> None:
        _ = (args, kwargs)
        pytest.fail("uninitialized workspace started host-C measurements")

    monkeypatch.setattr(reference_study, "_validate_plan", lambda plan: None)
    monkeypatch.setattr(reference_study, "_commit", lambda: "0" * 40)
    monkeypatch.setattr(reference_study, "_LOCAL", tmp_path)
    monkeypatch.setattr(reference_study.tempfile, "mkdtemp", faulty_mkdtemp)
    monkeypatch.setattr(reference_study.Path, "mkdir", faulty_mkdir)
    monkeypatch.setattr(reference_study, "_run_study", forbidden_measurement)
    with pytest.raises(reference_study.ReferenceStudyError, match="workspace") as error:
        reference_study.run_study(reference_study.StudyPlan(FAMILY, (4,), 7, 1))
    assert isinstance(error.value.__cause__, error_type)
    assert not directory.exists()


class _UnsafeWorkspaceCleanupError(ValueError):
    def __str__(self) -> str:
        raise AssertionError("workspace cleanup exception must not be formatted")


class _UnsafeWorkspaceCleanupArgument:
    def __str__(self) -> str:
        raise AssertionError("workspace cleanup argument must not be formatted")


@pytest.mark.parametrize(
    "cleanup_error",
    [
        ValueError("injected cleanup error"),
        RuntimeError("injected cleanup error"),
        _UnsafeWorkspaceCleanupError("foreign cleanup"),
        ValueError(_UnsafeWorkspaceCleanupArgument()),
        _UnexpectedHostFault("unanticipated cleanup"),
    ],
    ids=[
        "native-value",
        "native-runtime",
        "foreign-subclass",
        "foreign-argument",
        "unexpected",
    ],
)
def test_host_reference_setup_cleanup_failure_preserves_original_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    cleanup_error: Exception,
) -> None:
    """Unexpected cleanup faults cannot hide the failed workspace setup."""
    directory = tmp_path / "arena-host-c-study-allocated"
    directory.mkdir()

    def fake_mkdtemp(**kwargs: object) -> str:
        _ = kwargs
        return str(directory)

    def broken_mkdir(path: Path) -> None:
        _ = path
        message = "injected primary workspace creation failure"
        raise OSError(message)

    def broken_cleanup(path: Path) -> None:
        _ = path
        raise cleanup_error

    monkeypatch.setattr(reference_study, "_validate_plan", lambda _: None)
    monkeypatch.setattr(reference_study, "_commit", lambda: "0" * 40)
    monkeypatch.setattr(reference_study, "_LOCAL", tmp_path)
    monkeypatch.setattr(reference_study.tempfile, "mkdtemp", fake_mkdtemp)
    monkeypatch.setattr(reference_study.Path, "mkdir", broken_mkdir)
    monkeypatch.setattr(reference_study.shutil, "rmtree", broken_cleanup)
    with pytest.raises(
        reference_study.ReferenceStudyError, match="workspace setup"
    ) as error:
        _ = reference_study.run_study(
            reference_study.StudyPlan(FAMILY, (4,), 7, 1)
        )
    original = error.value.__cause__
    assert isinstance(original, OSError)
    note = "host-C workspace cleanup also failed"
    if type(cleanup_error) in (ValueError, RuntimeError) and (
        type(cleanup_error.args[0]) is str
    ):
        note += ": injected cleanup error"
    assert original.__notes__ == [note]


class _UnsafeHostOracleError(host_c_oracle.HostOracleError):
    def __str__(self) -> str:
        raise AssertionError("foreign host-C error must not be formatted")


@pytest.mark.parametrize(
    "oracle_failure",
    [
        _UnsafeHostOracleError("foreign host-C failure"),
        host_c_oracle.HostOracleError(_UnsafeWorkspaceCleanupArgument()),
    ],
    ids=["foreign-host-error", "host-error-with-foreign-argument"],
)
def test_host_reference_failed_arm_keeps_tool_failure_on_hostile_diagnostic(
    monkeypatch: pytest.MonkeyPatch,
    oracle_failure: host_c_oracle.HostOracleError,
) -> None:
    """Unsafe host error formatting cannot hide a failed compiler stage."""

    def reject_measurement(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise oracle_failure

    monkeypatch.setattr(reference_study, "_successful", reject_measurement)
    case = {"family": FAMILY, "version": 1, "seed": 7, "difficulty": 4}
    row, artifact, diagnostic = reference_study._measure(
        reference_study._ROOT / ".temp" / "host-C-failure-probe",
        case,
        trial=0,
        arm=(reference_study.CANDIDATE, OPTIMIZED_MODE),
    )
    assert row["outcome"] == FAILED
    assert row["verifier_verdict"] == analyze.NOT_RUN
    assert ARTIFACT_METRIC not in row["metrics"]
    assert artifact == {}
    assert diagnostic == "host-C reference failed without diagnostic"


@pytest.mark.parametrize(
    "oracle_failure",
    [
        _UnsafeHostOracleError("foreign host-C failure"),
        host_c_oracle.HostOracleError(_UnsafeWorkspaceCleanupArgument()),
    ],
    ids=["foreign-host-error", "host-error-with-foreign-argument"],
)
def test_host_reference_resource_preflight_types_hostile_oracle_error(
    monkeypatch: pytest.MonkeyPatch,
    oracle_failure: host_c_oracle.HostOracleError,
) -> None:
    """Preflight rejection preserves the cause without unsafe conversion."""

    def reject_resources() -> None:
        raise oracle_failure

    monkeypatch.setattr(
        host_c_oracle, "require_child_resource_controls", reject_resources
    )
    with pytest.raises(
        reference_study.ReferenceStudyError, match="child limits"
    ) as error:
        reference_study._validate_plan(
            reference_study.StudyPlan(FAMILY, (4,), 7, 1)
        )
    assert error.value.__cause__ is oracle_failure


@pytest.mark.skipif(
    not host_c_oracle._PINNED_CLANG.is_file(),  # ruff: ignore[private-member-access]
    reason="repository pinned native Clang is unavailable",
)
def test_failed_reference_arm_retains_failure_not_fabricated_cost(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Source-reported failed O2 stage remains visible to a paired study."""
    original = host_c_oracle.measure_reference

    def reject_o2(
        identity: generate.ChallengeIdentity, mode: str
    ) -> host_c_oracle.ReferenceMeasurement:
        if mode == OPTIMIZED_MODE:
            message = "injected compiler failure"
            raise host_c_oracle.HostOracleError(message)
        return original(identity, mode)

    monkeypatch.setattr(host_c_oracle, "measure_reference", reject_o2)
    path, document = reference_study.run_study(
        reference_study.StudyPlan(FAMILY, (4,), 7, 1),
    )
    try:
        rows = document["observations"]
        failed = next(
            row for row in rows if row["algorithm"] == reference_study.CANDIDATE
        )
        assert failed["outcome"] == FAILED
        assert failed["verifier_verdict"] == analyze.NOT_RUN
        assert ARTIFACT_METRIC not in failed["metrics"]
        result = analyze.analyze(analyze.parse_document(json.dumps(document)))
        assert result["capacity_curve"][1]["verified"] == 0
    finally:
        shutil.rmtree(path)


TAMPER_BYTES = "bytes"
TAMPER_SIZE = "size"
TAMPER_PATH = "path"
TAMPER_MISSING = "missing"
TAMPER_EXTRA = "extra"
TAMPER_SYMLINK = "symlink"


def _tamper_size(document: dict[str, Any], manifest: str) -> None:
    for row in document["observations"]:
        if row["experiment_manifest"] == manifest:
            row["metrics"][ARTIFACT_METRIC] += 1


def _tamper_record(
    tamper: str,
    document: dict[str, Any],
    reference: dict[str, str],
    *,
    manifest: str,
) -> None:
    executable = reference_study._ROOT / reference["path"]  # ruff: ignore[private-member-access]
    if tamper == TAMPER_BYTES:
        original = executable.read_bytes()
        _ = executable.write_bytes(original[:-1] + bytes([original[-1] ^ 1]))
    elif tamper == TAMPER_SIZE:
        _tamper_size(document, manifest)
    elif tamper == TAMPER_PATH:
        reference["path"] = ".temp/unrelated-executable"
    elif tamper == TAMPER_SYMLINK:
        other = executable.parent / "alternate-file"
        _ = other.write_bytes(executable.read_bytes())
        executable.unlink()
        executable.symlink_to(other)


def _tamper(
    tamper: str,
    document: dict[str, Any],
    artifacts: dict[str, dict[str, str]],
) -> None:
    name = next(iter(artifacts))
    if tamper == TAMPER_MISSING:
        _ = artifacts.pop(name)
    elif tamper == TAMPER_EXTRA:
        artifacts["extra-trial"] = artifacts[name].copy()
    else:
        _tamper_record(tamper, document, artifacts[name], manifest=name)


@pytest.mark.parametrize("check", ["artifacts", "failures"])
@pytest.mark.parametrize(
    "document",
    [
        None,
        {},
        {"observations": [None]},
        {"observations": [{"outcome": "unexpected", "experiment_manifest": "runs/a.toml"}]},
        {"observations": [{"outcome": "verified", "experiment_manifest": object()}]},
    ],
    ids=[
        "missing-document",
        "missing-observations",
        "foreign-row",
        "unsupported-outcome",
        "foreign-manifest",
    ],
)
def test_direct_retained_checks_reject_unadmitted_trial_rows(
    check: str,
    document: object,
) -> None:
    """Direct checks must reject malformed trial maps as typed failures."""
    checker = (
        reference_study.check_retained_artifacts
        if check == "artifacts"
        else reference_study.check_retained_failures
    )
    with pytest.raises(reference_study.ReferenceStudyError):
        _ = checker(cast("dict[str, Any]", document), {})


class _ForgedTrialKey(str):  # ruff: ignore[subclass-builtin]
    """Foreign dictionary keys can run attacker-defined equality methods."""

    def __eq__(self, other: object) -> bool:
        del other
        message = "retained trial key equality hook executed"
        raise AssertionError(message)

    __hash__ = str.__hash__


@pytest.mark.parametrize("check", ["artifacts", "failures"])
def test_direct_retained_checks_reject_foreign_observation_keys(
    check: str,
) -> None:
    """Reject foreign keys before accessing the observations dictionary."""
    document: dict[str, Any] = {
        _ForgedTrialKey("observations"): [],
    }
    checker = (
        reference_study.check_retained_artifacts
        if check == "artifacts"
        else reference_study.check_retained_failures
    )
    with pytest.raises(reference_study.ReferenceStudyError):
        _ = checker(document, {})


@pytest.mark.parametrize("check", ["artifacts", "failures"])
def test_direct_retained_checks_reject_foreign_sidecar_container(check: str) -> None:
    """An empty list cannot substitute for an empty retained metadata map."""
    checker = (
        reference_study.check_retained_artifacts
        if check == "artifacts"
        else reference_study.check_retained_failures
    )
    with pytest.raises(reference_study.ReferenceStudyError):
        _ = checker({"observations": []}, cast("Any", []))


@pytest.mark.parametrize("check", ["artifacts", "failures"])
def test_direct_retained_checks_reject_sidecar_foreign_keys(check: str) -> None:
    """Retained sidecars must not execute caller-defined key equality."""
    manifest = "runs/forged.toml"
    outcome = analyze.VERIFIED if check == "artifacts" else FAILED
    document = {"observations": [
        {"outcome": outcome, "experiment_manifest": manifest},
    ]}
    payload: object = {"path": "unused", "sha256": "unused"}
    if check == "failures":
        payload = "compiler rejected"
    sidecar = {_ForgedTrialKey(manifest): payload}
    checker = (
        reference_study.check_retained_artifacts
        if check == "artifacts"
        else reference_study.check_retained_failures
    )
    with pytest.raises(reference_study.ReferenceStudyError):
        _ = checker(document, cast("Any", sidecar))


def test_direct_retained_artifacts_reject_non_mapping_artifact_entry() -> None:
    """An artifact leaf must be a native metadata map before I/O."""
    manifest = "runs/missing-metadata.toml"
    document = {"observations": [{
        "outcome": analyze.VERIFIED,
        "experiment_manifest": manifest,
    }]}
    with pytest.raises(reference_study.ReferenceStudyError):
        _ = reference_study.check_retained_artifacts(
            document, cast("Any", {manifest: []})
        )


@pytest.mark.parametrize(
    "metrics",
    [None, {}, {"artifact_bytes": True}, {"artifact_bytes": "1"}],
    ids=["missing", "no-size", "boolean-size", "text-size"],
)
def test_direct_retained_artifacts_preflight_verified_metrics_before_io(
    monkeypatch: pytest.MonkeyPatch,
    metrics: object,
) -> None:
    """Unadmitted metrics cannot trigger retained artifact filesystem access."""
    manifest = ".temp/arena-host-c-study-check/runs/one.toml"
    row: dict[str, Any] = {
        "experiment_manifest": manifest,
        "outcome": analyze.VERIFIED,
        "metrics": metrics,
    }

    def forbidden(*args: object, **kwargs: object) -> None:
        del args, kwargs
        pytest.fail("unadmitted metrics reached artifact byte inspection")

    monkeypatch.setattr(reference_study, "_checked_artifact", forbidden)
    with pytest.raises(reference_study.ReferenceStudyError, match="metrics"):
        _ = reference_study.check_retained_artifacts(
            {"observations": [row]},
            {manifest: {"path": "unused", "sha256": "unused"}},
        )


def test_retained_artifact_check_rejects_duplicate_verified_manifests(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A direct map check cannot collapse two successes into one file claim."""
    manifest = "runs/duplicate.toml"
    row = {"experiment_manifest": manifest, "outcome": analyze.VERIFIED}

    def forbidden(*args: object, **kwargs: object) -> None:
        del args, kwargs
        pytest.fail("duplicate manifest reached artifact filesystem verification")

    monkeypatch.setattr(reference_study, "_checked_artifact", forbidden)
    with pytest.raises(reference_study.ReferenceStudyError, match="duplicate"):
        reference_study.check_retained_artifacts(
            {"observations": [row, row.copy()]},
            {manifest: {"path": "not-checked", "sha256": "not-checked"}},
        )


def test_retained_failures_reject_duplicate_failure_manifests() -> None:
    """One diagnostic entry cannot stand in for two reported failed trials."""
    manifest = "runs/duplicate.toml"
    row = {"experiment_manifest": manifest, "outcome": FAILED}
    with pytest.raises(reference_study.ReferenceStudyError, match="duplicate"):
        reference_study.check_retained_failures(
            {"observations": [row, row.copy()]},
            {manifest: "compiler exited without output"},
        )


@pytest.mark.skipif(
    not host_c_oracle._PINNED_CLANG.is_file(),  # ruff: ignore[private-member-access]
    reason="repository pinned native Clang is unavailable",
)
@pytest.mark.parametrize(
    "tamper",
    [
        TAMPER_BYTES,
        TAMPER_SIZE,
        TAMPER_PATH,
        TAMPER_MISSING,
        TAMPER_EXTRA,
        TAMPER_SYMLINK,
    ],
)
def test_reference_artifact_audit_rejects_retained_drift(tamper: str) -> None:
    """Source-reported native hashes and sizes reject mutated binaries."""
    path, document = reference_study.run_study(
        reference_study.StudyPlan(FAMILY, (4,), 7, 1),
    )
    try:
        artifacts = json.loads((path / "artifacts.json").read_text())
        assert (
            reference_study.check_retained_artifacts(document, artifacts)
            == REPETITIONS
        )
        _tamper(tamper, document, artifacts)
        with pytest.raises(reference_study.ReferenceStudyError, match="host-C"):
            reference_study.check_retained_artifacts(document, artifacts)
    finally:
        shutil.rmtree(path)


class _UnsafeArtifactEvidenceError(evidence.EvidenceError):
    def __str__(self) -> str:
        raise AssertionError("artifact error formatting is untrusted")


@pytest.mark.parametrize(
    "failure",
    [
        _UnsafeArtifactEvidenceError("foreign evidence"),
        OSError(_UnsafeWorkspaceCleanupArgument()),
        evidence.EvidenceError("native evidence read failure"),
    ],
    ids=[
        "foreign-evidence-error",
        "native-os-error-with-foreign-argument",
        "native-evidence-message",
    ],
)
def test_direct_artifact_failure_never_formats_foreign_exception(
    monkeypatch: pytest.MonkeyPatch,
    failure: evidence.EvidenceError | OSError,
) -> None:
    """An evidence read error remains a typed artifact rejection."""

    def reject_read(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise failure

    monkeypatch.setattr(evidence, "read_bounded_regular", reject_read)
    row = {
        "experiment_manifest": ".temp/probe/runs/candidate.toml",
        "metrics": {"artifact_bytes": 1},
    }
    entry = {
        "path": ".temp/probe/candidates/candidate",
        "sha256": "a" * analyze.SHA256_HEX_LENGTH,
    }
    with pytest.raises(
        reference_study.ReferenceStudyError, match="cannot be admitted"
    ) as caught:
        reference_study._checked_artifact(row, entry)
    assert caught.value.__cause__ is failure
    if type(failure) is evidence.EvidenceError:
        assert str(caught.value).endswith(": native evidence read failure")


@pytest.mark.parametrize(
    "fault_type", [ValueError, RuntimeError, TypeError, _UnexpectedHostFault]
)
def test_retained_artifact_types_unexpected_reader_dependency_faults(
    monkeypatch: pytest.MonkeyPatch,
    fault_type: type[Exception],
) -> None:
    """Unexpected reader faults remain typed without foreign formatting."""
    fault = fault_type("unanticipated retained artifact read failure")

    def fail_read(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise fault

    monkeypatch.setattr(evidence, "read_bounded_regular", fail_read)
    row = {
        "experiment_manifest": ".temp/probe/runs/candidate.toml",
        "metrics": {"artifact_bytes": 1},
    }
    entry = {
        "path": ".temp/probe/candidates/candidate",
        "sha256": "a" * analyze.SHA256_HEX_LENGTH,
    }
    with pytest.raises(
        reference_study.ReferenceStudyError, match="cannot be admitted"
    ) as caught:
        reference_study._checked_artifact(row, entry)
    assert caught.value.__cause__ is fault


class _UnsafeCliStudyError(reference_study.ReferenceStudyError):
    def __str__(self) -> str:
        raise AssertionError("CLI study exception formatting is untrusted")


class _UnsafeCliReportError(report_output.ReportOutputError):
    def __str__(self) -> str:
        raise AssertionError("CLI report exception formatting is untrusted")


@pytest.mark.parametrize(
    ("stage", "failure"),
    [
        ("study", _UnsafeCliStudyError("foreign study")),
        (
            "study",
            reference_study.ReferenceStudyError(_UnsafeWorkspaceCleanupArgument()),
        ),
        ("study", reference_study.ReferenceStudyError("native study failure")),
        ("publish", _UnsafeCliReportError("foreign report")),
        (
            "publish",
            report_output.ReportOutputError(_UnsafeWorkspaceCleanupArgument()),
        ),
    ],
    ids=[
        "foreign-study",
        "native-study-argument",
        "native-study-message",
        "foreign-publish",
        "native-publish-argument",
    ],
)
def test_reference_cli_never_formats_foreign_errors(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    stage: str,
    failure: Exception,
) -> None:
    """Both CLI error boundaries exit 2 without running untrusted hooks."""

    def reject(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise failure

    monkeypatch.setattr(sys, "argv", ["reference-study", FAMILY])
    if stage == "study":
        monkeypatch.setattr(reference_study, "run_study", reject)
    else:
        monkeypatch.setattr(reference_study, "run_study", _fake_study_for_stdout)
        monkeypatch.setattr(report_output, "publish", reject)
    with pytest.raises(SystemExit) as caught:
        reference_study.main()
    assert caught.value.code == 2
    output = capsys.readouterr()
    assert output.out == ""
    assert "host-C reference study:" in output.err
    if type(failure) is reference_study.ReferenceStudyError and (
        type(failure.args[0]) is str
    ):
        assert "native study failure" in output.err


class _UnexpectedCliDependencyFault(Exception):
    def __str__(self) -> str:
        raise AssertionError("unexpected dependency fault cannot be formatted")


@pytest.mark.parametrize("stage", ["study", "publish"])
@pytest.mark.parametrize(
    "failure",
    [
        RuntimeError("unexpected runtime dependency"),
        TypeError("unexpected type dependency"),
        _UnexpectedCliDependencyFault("opaque dependency fault"),
    ],
    ids=["runtime", "type", "foreign-format-hook"],
)
def test_reference_cli_unexpected_dependency_fault_is_status_two_without_stdout(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    stage: str,
    failure: Exception,
) -> None:
    """Unknown ordinary dependency errors must not escape the operator gate."""

    def reject(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise failure

    monkeypatch.setattr(sys, "argv", ["reference-study", FAMILY])
    if stage == "study":
        monkeypatch.setattr(reference_study, "run_study", reject)
    else:
        monkeypatch.setattr(reference_study, "run_study", _fake_study_for_stdout)
        monkeypatch.setattr(report_output, "publish", reject)
    with pytest.raises(SystemExit) as caught:
        reference_study.main()
    assert caught.value.code == 2
    output = capsys.readouterr()
    assert not output.out
    assert output.err == "host-C reference study: error details unavailable\n"


def _fake_study_for_stdout(
    plan: reference_study.StudyPlan,
) -> tuple[Path, dict[str, Any]]:
    """Avoid rerunning native Clang for an unrelated stdout framing check.

    Returns:
        A path and documented observation count for the operator summary.

    """
    _ = plan
    return (
        reference_study._ROOT / ".temp" / "host-c-output-probe",  # ruff: ignore[private-member-access]
        {"observations": [{"trial": 0}, {"trial": 1}]},
    )


def test_reference_cli_output_is_checked_and_complete(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A healthy operator stream emits exactly one complete JSON object."""
    monkeypatch.setattr(reference_study, "run_study", _fake_study_for_stdout)
    monkeypatch.setattr(sys, "argv", ["reference-study", FAMILY])
    assert reference_study.main() == 0
    observed = json.loads(capsys.readouterr().out)
    assert observed["observations"] == REPETITIONS
    assert observed["study"].endswith("/host-c-output-probe/study.json")


def test_reference_cli_rejects_unflushed_or_truncated_operator_report(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Publishing failure cannot be reported as a successful command."""
    monkeypatch.setattr(reference_study, "run_study", _fake_study_for_stdout)
    monkeypatch.setattr(sys, "argv", ["reference-study", FAMILY])

    def broken_publisher(
        report: dict[str, Any],
        stream: report_output.TextReportStream,
    ) -> None:
        _ = (report, stream)
        message = OUTPUT_FAULT
        raise report_output.ReportOutputError(message)

    monkeypatch.setattr(report_output, "publish", broken_publisher)
    with pytest.raises(SystemExit, match="2"):
        reference_study.main()
    result = capsys.readouterr()
    assert not result.out
    assert OUTPUT_FAULT in result.err


def test_reference_study_refuses_missing_kernel_limit_launcher(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No purportedly protected host study can start without prlimit."""
    monkeypatch.setattr(
        host_c_oracle.shutil, "which", lambda *_args, **_kwargs: None
    )
    with pytest.raises(
        reference_study.ReferenceStudyError, match="child limits"
    ):
        reference_study.run_study(
            reference_study.StudyPlan(FAMILY, (4,), 7, 1),
        )


def test_reference_resource_admission_types_unexpected_dependency_fault(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A foreign host-resource probe fault must not escape direct admission."""
    fault = _UnexpectedHostFault("unexpected child resource probe fault")

    def fail_probe() -> None:
        raise fault

    monkeypatch.setattr(host_c_oracle, "require_child_resource_controls", fail_probe)
    with pytest.raises(reference_study.ReferenceStudyError, match="child limits") as caught:
        reference_study._validate_plan(  # ruff: ignore[private-member-access]
            reference_study.StudyPlan(FAMILY, (4,), 7, 1)
        )
    assert caught.value.__cause__ is fault


@pytest.mark.parametrize("fault_type", [OSError, ValueError, RuntimeError])
def test_host_reference_workspace_cleanup_never_dispatches_primary_add_note(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    fault_type: type[Exception],
) -> None:
    """Foreign primary hooks cannot conceal a failed workspace setup."""
    directory = tmp_path / "arena-host-c-study-allocated"
    directory.mkdir()

    class HostilePrimary(fault_type):
        def add_note(self, note: str) -> None:
            del note
            raise AssertionError("foreign primary error add_note hook invoked")

    primary = HostilePrimary("primary workspace setup fault")
    cleanup = ValueError("cleanup failed")

    def fake_mkdtemp(**kwargs: object) -> str:
        del kwargs
        return str(directory)

    def broken_mkdir(path: Path) -> None:
        del path
        raise primary

    def broken_cleanup(path: Path) -> None:
        del path
        raise cleanup

    monkeypatch.setattr(reference_study, "_validate_plan", lambda _: None)
    monkeypatch.setattr(reference_study, "_commit", lambda: "0" * 40)
    monkeypatch.setattr(reference_study, "_LOCAL", tmp_path)
    monkeypatch.setattr(reference_study.tempfile, "mkdtemp", fake_mkdtemp)
    monkeypatch.setattr(reference_study.Path, "mkdir", broken_mkdir)
    monkeypatch.setattr(reference_study.shutil, "rmtree", broken_cleanup)
    with pytest.raises(
        reference_study.ReferenceStudyError, match="workspace setup"
    ) as caught:
        reference_study.run_study(reference_study.StudyPlan(FAMILY, (4,), 7, 1))
    assert caught.value.__cause__ is primary
    assert primary.__notes__ == ["host-C workspace cleanup also failed: cleanup failed"]


class _ForgedArtifactLength(bytes):
    """Foreign bytes may lie about their native buffer length."""

    def __len__(self) -> int:
        return 1


@pytest.mark.parametrize("receipt_type", ["forged-length", "oversized"])
def test_retained_artifact_rejects_foreign_or_oversized_evidence_receipt(
    monkeypatch: pytest.MonkeyPatch, receipt_type: str
) -> None:
    """A replaced bounded reader cannot authenticate fabricated artifact sizes."""
    monkeypatch.setattr(reference_study, "MAX_ARTIFACT_BYTES", 4)
    actual = (
        _ForgedArtifactLength(b"forged")
        if receipt_type == "forged-length"
        else b"longer"
    )
    claimed_size = 1 if receipt_type == "forged-length" else len(actual)
    row = {
        "experiment_manifest": ".temp/probe/runs/candidate.toml",
        "metrics": {"artifact_bytes": claimed_size},
    }
    entry = {
        "path": ".temp/probe/candidates/candidate",
        "sha256": sha256(actual).hexdigest(),
    }
    monkeypatch.setattr(
        evidence, "read_bounded_regular", lambda *_args, **_kwargs: actual
    )
    with pytest.raises(
        reference_study.ReferenceStudyError, match="exact bounded bytes"
    ):
        reference_study._checked_artifact(row, entry)


class _ForeignHashText(str):  # ruff: ignore[subclass-builtin]
    """A foreign hash result can forge any comparison against a stored digest."""

    def __ne__(self, other: object) -> bool:
        del other
        return False


@pytest.mark.parametrize(
    "receipt",
    ["recorded", "foreign", "nontext", "wrong-length", "raised"],
)
def test_retained_artifact_never_trusts_unverified_hash_receipt(
    monkeypatch: pytest.MonkeyPatch,
    receipt: str,
) -> None:
    """A substituted hashing provider cannot certify altered retained bytes."""
    original = b"original native executable"
    altered = b"tampered native executable"
    claimed_digest = sha256(original).hexdigest()
    manifest = ".temp/probe/runs/candidate.toml"
    document = {
        "observations": [
            {
                "experiment_manifest": manifest,
                "outcome": analyze.VERIFIED,
                "metrics": {"artifact_bytes": len(altered)},
            }
        ],
    }
    artifacts = {
        manifest: {
            "path": ".temp/probe/candidates/candidate",
            "sha256": claimed_digest,
        },
    }
    monkeypatch.setattr(
        evidence, "read_bounded_regular", lambda *_args, **_kwargs: altered
    )
    fault = _UnexpectedHostFault("hashing dependency failed")

    class ForgedHash:
        def hexdigest(self) -> object:
            if receipt == "raised":
                raise fault
            return {
                "recorded": claimed_digest,
                "foreign": _ForeignHashText(claimed_digest),
                "nontext": 12,
                "wrong-length": "0",
            }[receipt]

    monkeypatch.setattr(reference_study, "sha256", lambda _raw: ForgedHash())
    with pytest.raises(reference_study.ReferenceStudyError, match="SHA-256") as caught:
        _ = reference_study.check_retained_artifacts(document, artifacts)
    if receipt == "raised":
        assert caught.value.__cause__ is fault


def test_host_c_reference_rejects_jointly_substituted_sha256_providers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Aliases of one forged hash provider cannot certify producer bytes."""
    raw = b"real native retained bytes"
    forged = "0" * analyze.SHA256_HEX_LENGTH
    assert forged != sha256(raw).hexdigest()

    class ForgedHash:
        def hexdigest(self) -> str:
            return forged

    def fake_hash(_raw: bytes) -> ForgedHash:
        return ForgedHash()

    monkeypatch.setattr(reference_study, "sha256", fake_hash)
    monkeypatch.setattr(
        reference_study,
        "hashlib",
        SimpleNamespace(sha256=fake_hash, new=reference_study.hashlib.new),
    )
    with pytest.raises(
        reference_study.ReferenceStudyError, match="SHA-256 receipt differs"
    ):
        reference_study._checked_sha256(raw)


def test_reference_study_rejects_jointly_forged_hash_constructors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Mutually forged source digests cannot enter retained artifact metadata."""
    raw = b"true binary reference artifact"
    false_digest = "0" * analyze.SHA256_HEX_LENGTH
    assert sha256(raw).hexdigest() != false_digest

    class ForgedHash:
        def hexdigest(self) -> str:
            return false_digest

    monkeypatch.setattr(reference_study, "sha256", lambda _raw: ForgedHash())
    monkeypatch.setattr(
        reference_study,
        "hashlib",
        SimpleNamespace(new=lambda _algorithm, _raw: ForgedHash()),
    )
    with pytest.raises(reference_study.ReferenceStudyError, match="SHA-256"):
        reference_study._checked_sha256(raw)


@pytest.mark.parametrize("stage", ["bundle", "binary", "raw"])
def test_producer_hash_receipts_cannot_mislabel_generated_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    stage: str,
) -> None:
    """Do not retain fake source, executable or raw-file digests as evidence."""
    monkeypatch.setattr(reference_study, "_ROOT", tmp_path)
    monkeypatch.setattr(reference_study, "sha256", lambda _raw: _FixedHash())
    monkeypatch.setattr(reference_study, "_write_retained_bytes", lambda *_args: None)
    monkeypatch.setattr(reference_study, "_write_retained_text", lambda *_args: None)
    root = tmp_path / "study"
    root.mkdir()
    with pytest.raises(reference_study.ReferenceStudyError, match="SHA-256"):
        if stage == "bundle":
            _ = reference_study._generate_bundle(root, FAMILY, 4, seed=7)
        elif stage == "binary":
            monkeypatch.setattr(
                host_c_oracle,
                "measure_reference",
                lambda *_args: host_c_oracle.ReferenceMeasurement(10, b"compiled", 1024),
            )
            _ = reference_study._successful(
                root,
                cast("generate.ChallengeIdentity", object()),
                "candidate",
                mode="-O0",
            )
        else:
            monkeypatch.setattr(reference_study, "_raw_csv", lambda _row: b"raw")
            monkeypatch.setattr(reference_study, "_manifest", lambda *_args: "run")
            monkeypatch.setattr(
                reference_study,
                "_measure",
                lambda *_args, **_kwargs: (
                    {
                        "experiment_manifest": "study/runs/attempt.toml",
                        "raw_sample": "study/raw/attempt.csv",
                    },
                    {},
                    None,
                ),
            )
            environment = reference_study._Env(
                root,
                reference_study.StudyPlan(FAMILY, (4,), 7, 1),
                "0" * 40,
                "host",
                "toolchain",
                "study",
            )
            _ = reference_study._write_attempt(
                environment,
                ({"family": FAMILY, "difficulty": 4}, "0" * 64),
                trial=0,
                arm=(reference_study.BASELINE, "-O0"),
            )


class _FixedHash:
    """Attacker-controlled hex output always claims the all-zero source."""

    def hexdigest(self) -> str:
        return "0" * analyze.SHA256_HEX_LENGTH


def test_retained_artifact_native_bounded_reader_receipt_remains_admissible(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A genuine byte string retains its normal digest and size identity."""
    raw = b"valid"
    monkeypatch.setattr(reference_study, "MAX_ARTIFACT_BYTES", len(raw))
    monkeypatch.setattr(
        evidence, "read_bounded_regular", lambda *_args, **_kwargs: raw
    )
    reference_study._checked_artifact(
        {
            "experiment_manifest": ".temp/probe/runs/candidate.toml",
            "metrics": {"artifact_bytes": len(raw)},
        },
        {
            "path": ".temp/probe/candidates/candidate",
            "sha256": sha256(raw).hexdigest(),
        },
    )


class _ForeignReferenceInteger(int):
    """Numeric subclasses must not decide whether a measurement is successful."""

    def __gt__(self, other: object) -> bool:
        del other
        raise AssertionError("foreign host-C elapsed comparison executed")


class _ForeignExecutableBytes(bytes):
    """Artifact subclasses must not forge the recorded compiled size."""

    def __len__(self) -> int:
        return 1


@pytest.mark.parametrize(
    "measurement",
    [
        object(),
        host_c_oracle.ReferenceMeasurement(_ForeignReferenceInteger(1), b"C", 1024),
        host_c_oracle.ReferenceMeasurement(0, b"C", 1024),
        host_c_oracle.ReferenceMeasurement(
            reference_study.BUDGET_SECONDS * 1_000_000_000 + 1, b"C", 1024
        ),
        host_c_oracle.ReferenceMeasurement(1, b"C", 0),
        host_c_oracle.ReferenceMeasurement(
            1, b"C", reference_study.BUDGET_MEMORY_MIB * 1_048_576 + 1
        ),
        host_c_oracle.ReferenceMeasurement(1, b"C", True),
        host_c_oracle.ReferenceMeasurement(1, b"", 1024),
        host_c_oracle.ReferenceMeasurement(1, _ForeignExecutableBytes(b"forged"), 1024),
        host_c_oracle.ReferenceMeasurement(1, b"longer", 1024),
    ],
)
def test_host_c_measurement_receipt_rejects_foreign_or_invalid_data_before_write(
    monkeypatch: pytest.MonkeyPatch, measurement: object
) -> None:
    """Never publish artifacts or report costs from untrusted native measurements."""
    monkeypatch.setattr(reference_study, "MAX_ARTIFACT_BYTES", 4)
    monkeypatch.setattr(host_c_oracle, "measure_reference", lambda *_args: measurement)

    def forbid_write(*_args: object, **_kwargs: object) -> None:
        pytest.fail("invalid measurement reached artifact publication")

    monkeypatch.setattr(reference_study, "_write_retained_bytes", forbid_write)
    with pytest.raises(reference_study.ReferenceStudyError, match="measurement receipt"):
        reference_study._successful(
            reference_study._ROOT,
            cast("generate.ChallengeIdentity", object()),
            "candidate",
            mode="-O0",
        )


def test_host_c_measurement_receipt_accepts_exact_bounded_native_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Valid native measurement receipts retain cost and binary identities."""
    receipt = host_c_oracle.ReferenceMeasurement(10, b"good", 1024)
    captured: list[bytes] = []
    monkeypatch.setattr(reference_study, "MAX_ARTIFACT_BYTES", len(receipt.executable))
    monkeypatch.setattr(host_c_oracle, "measure_reference", lambda *_args: receipt)
    monkeypatch.setattr(
        reference_study,
        "_write_retained_bytes",
        lambda _path, payload: captured.append(payload),
    )
    metrics, artifact = reference_study._successful(
        reference_study._ROOT,
        cast("generate.ChallengeIdentity", object()),
        "candidate",
        mode="-O0",
    )
    assert captured == [b"good"]
    assert metrics == {"elapsed_ns": 10, "artifact_bytes": 4, "peak_rss_bytes": 1024}
    assert artifact["sha256"] == sha256(b"good").hexdigest()


@pytest.mark.parametrize("mutation", ("executable", "operation", "extra"))
def test_reference_study_git_rejects_mutated_launch_command(
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
) -> None:
    """In-place subprocess argv mutation cannot forge matching Git evidence."""
    launched: list[list[str]] = []

    def forged(command: list[str], **_kwargs: object) -> object:
        expected = command.copy()
        if mutation == "executable":
            command[0] = "/unexpected/git"
        elif mutation == "operation":
            command[1] = "status"
        else:
            command.append("--unexpected")
        launched.append(expected)
        return reference_study.sp.CompletedProcess(
            command, 0, stdout="a" * 40 + "\n", stderr=""
        )

    monkeypatch.setattr(reference_study.sp, "run", forged)
    with pytest.raises(reference_study.ReferenceStudyError, match="Git completion receipt"):
        reference_study._commit()  # ruff: ignore[private-member-access]
    assert len(launched) == 1
    assert launched[0][1] in ("rev-parse", "cat-file")


@pytest.mark.parametrize("tamper", ["forged_digest", "invalid_source", "nonnative_digest"])
def test_host_c_bundle_fingerprint_rejects_substituted_json_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    tamper: str,
) -> None:
    """A forged decoder cannot relabel the retained bundle profile fingerprint."""
    expected = (
        reference_study.target_profile.PROFILE_FINGERPRINT_PREFIX
        + "a" * analyze.SHA256_HEX_LENGTH
    )
    actual = {"identity": {"target_profile_fingerprint": expected}}
    manifest = json.dumps(actual).encode() if tamper != "invalid_source" else b"not JSON"
    bundle = reference_study.generate.GeneratedChallenge(b"source", b"oracle", manifest)
    monkeypatch.setattr(reference_study.generate, "generate", lambda _identity: bundle)
    monkeypatch.setattr(reference_study, "_write_retained_bytes", lambda *_a: None)
    receipt = {
        "identity": {
            "target_profile_fingerprint": (
                reference_study.target_profile.PROFILE_FINGERPRINT_PREFIX
                + "b" * analyze.SHA256_HEX_LENGTH
            )
        }
    }
    if tamper == "nonnative_digest":
        class ForeignFingerprint(str):
            def __eq__(self, _other: object) -> bool:
                raise AssertionError("foreign fingerprint comparison hook executed")
        receipt["identity"]["target_profile_fingerprint"] = ForeignFingerprint(expected)
    monkeypatch.setattr(reference_study.json, "loads", lambda *_a, **_kw: receipt)
    with pytest.raises(reference_study.ReferenceStudyError, match="manifest|fingerprint"):
        reference_study._generate_bundle(tmp_path, FAMILY, 4, seed=7)
    assert not (tmp_path / "bundles").exists()


@pytest.mark.parametrize("source_kind", ("forged", "invalid-source"))
def test_host_c_bundle_fingerprint_rejects_replaced_cached_decoder(
    monkeypatch: pytest.MonkeyPatch, source_kind: str
) -> None:
    """A saved loads function still consults a mutable cached decoder."""
    prefix = reference_study.target_profile.PROFILE_FINGERPRINT_PREFIX
    actual = prefix + "a" * analyze.SHA256_HEX_LENGTH
    fabricated = prefix + "b" * analyze.SHA256_HEX_LENGTH
    manifest = (
        json.dumps({"identity": {"target_profile_fingerprint": actual}}).encode()
        if source_kind == "forged"
        else b"invalid generated challenge manifest"
    )

    class ForgedCachedDecoder:
        def decode(self, _source: str) -> dict[str, object]:
            return {"identity": {"target_profile_fingerprint": fabricated}}

    with monkeypatch.context() as patch:
        patch.setattr(json, "_default_decoder", ForgedCachedDecoder())
        # This really forges the captured json.loads function used before
        # source-class corroboration; a JSONDecoder-class-only patch does not.
        assert json.loads(manifest)["identity"]["target_profile_fingerprint"] == fabricated
        with pytest.raises(
            reference_study.ReferenceStudyError,
            match="bundle fingerprint differs from source|manifest source JSON is invalid",
        ):
            reference_study._profile_fingerprint_from_bundle_manifest(manifest)


@pytest.mark.parametrize("method", ["decode", "raw_decode"])
def test_host_c_bundle_fingerprint_rejects_shared_decoder_method_forgery(
    monkeypatch: pytest.MonkeyPatch, method: str,
) -> None:
    """Two agreeing cached and source decoders cannot forge a fingerprint."""
    prefix = reference_study.target_profile.PROFILE_FINGERPRINT_PREFIX
    original = prefix + "a" * analyze.SHA256_HEX_LENGTH
    forged = prefix + "b" * analyze.SHA256_HEX_LENGTH
    manifest = json.dumps(
        {"identity": {"target_profile_fingerprint": original}}
    ).encode()
    fake: dict[str, object] = {
        "identity": {"target_profile_fingerprint": forged}
    }

    def replaced_decode(instance: object, text: str) -> dict[str, object]:
        del instance, text
        return fake

    def replaced_raw_decode(
        instance: object, text: str, idx: int = 0
    ) -> tuple[dict[str, object], int]:
        del instance, idx
        return fake, len(text)

    providers = {"decode": replaced_decode, "raw_decode": replaced_raw_decode}
    with monkeypatch.context() as patch:
        patch.setattr(json.JSONDecoder, method, providers[method])
        assert (
            json.loads(manifest)["identity"]["target_profile_fingerprint"]
            == forged
        )
        reader_name = "_profile_fingerprint_from_bundle_manifest"
        reader = getattr(reference_study, reader_name)
        with pytest.raises(
            reference_study.ReferenceStudyError,
            match="bundle fingerprint differs from source",
        ):
            _ = reader(manifest)


def test_host_c_bundle_fingerprint_rejects_replaced_scanner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A changed JSON scanner cannot authorize a generated profile identity."""
    prefix = reference_study.target_profile.PROFILE_FINGERPRINT_PREFIX
    original = prefix + "a" * analyze.SHA256_HEX_LENGTH
    manifest = json.dumps(
        {"identity": {"target_profile_fingerprint": original}}
    ).encode()
    scanner_name = "scanner"
    scanner_module = getattr(json, scanner_name)
    scanner_factory = scanner_module.make_scanner

    def altered_factory(*args: object, **kwargs: object) -> object:
        return scanner_factory(*args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(scanner_module, "make_scanner", altered_factory)
        reader_name = "_profile_fingerprint_from_bundle_manifest"
        reader = getattr(reference_study, reader_name)
        with pytest.raises(
            reference_study.ReferenceStudyError,
            match="bundle fingerprint differs from source JSON decoder",
        ):
            _ = reader(manifest)


def test_host_c_bundle_fingerprint_accepts_equivalent_json_decoder(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The canonical source fingerprint survives a source-equivalent wrapper."""
    expected = (
        reference_study.target_profile.PROFILE_FINGERPRINT_PREFIX
        + "a" * analyze.SHA256_HEX_LENGTH
    )
    manifest = json.dumps({"identity": {"target_profile_fingerprint": expected}}).encode()
    bundle = reference_study.generate.GeneratedChallenge(b"source", b"oracle", manifest)
    monkeypatch.setattr(reference_study.generate, "generate", lambda _identity: bundle)
    monkeypatch.setattr(reference_study, "_write_retained_bytes", lambda *_a: None)
    original = reference_study.json.loads
    monkeypatch.setattr(reference_study.json, "loads", lambda data: original(data))
    case, fingerprint = reference_study._generate_bundle(tmp_path, FAMILY, 4, seed=7)
    assert case["family"] == FAMILY
    assert fingerprint == expected
