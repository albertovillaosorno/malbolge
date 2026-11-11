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
#   - Offline producer-specific target source and VM replay audit regressions.
# - Must-Not:
#   - Present synthetic tampering as a measured target performance result.
# - Allows:
#   - Inputs: freshly retained local classic echo studies and corruptions.
#   - Outputs: fail-closed source, manifest, corpus and VM replay assertions.
#   - Side effects: test-owned ignored study output and bounded VM children.
# - Split-When:
#   - General target candidate research needs a larger semantic oracle.
# - Merge-When:
#   - One native Malbolge verifier supersedes this fixed echo auditor.
# - Summary:
#   - Detects forged retained source despite consistent raw/manifest records.
# - Description:
#   - Covers exact source decode, producer claims, study populations and replay.
# - Usage:
#   - pytest benchmarks/arena/tests/test_target_echo_audit.py.
# - Defaults:
#   - Fail closed without physical replay rather than infer run authentication.
#

"""Post-run classic Malbolge target evidence and strict replay tests."""

# ruff: file-ignore[assert,private-member-access]

from __future__ import annotations

import copy
import json
import os
import shutil
import subprocess as sp  # ruff: ignore[suspicious-subprocess-import]
import sys
import tempfile
from dataclasses import replace
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any, Never, cast

import pytest
import tomllib

from benchmarks.arena import analyze, evidence, report_output, target_process
from benchmarks.arena import target_echo_audit as audit
from benchmarks.arena import target_echo_reference as producer

if TYPE_CHECKING:
    from collections.abc import Iterator

ROWS = 8
REPLAYED = 8
MAX_PHASE_TRIALS = 2
FRONTIERS = 2
FRONTIER_LEVELS_FORWARD = 4
INVALID_SOURCE = 33
SECOND_INVALID_SOURCE = 34
JUMP_CORRUPTION = "jump"
SKIPPED_CORRUPTION = "skipped-padding"
REACHABLE_CORRUPTION = "reachable-input"
RUNTIME_STEPS = "runtime_steps"
VERIFIER_COST_METRIC = "verifier_ns"
LEGACY_TAMPER = "legacy"
ZERO_TAMPER = "zero"
EXCESS_TAMPER = "exceeds-total"
EXPECTED_GUEST_SAVINGS = 98
ALL_BYTE_VALUES = 256
INPUT_WINDOW_BYTES = 64
DIFFICULTY = 1
FORGED_TRIAL = 999
ELAPSED = "elapsed_ns"
ARTIFACT_BYTES = "artifact_bytes"
EXTRA_ARTIFACT = "extra"
POSIX_PLATFORM = "posix"
NOT_AUTHENTICATED = "not authenticated"
AUDIT_MESSAGE = "target audit"
RSS_RUN_RELATIVE = "run.toml"
BAD_PROFILE_PROVENANCE = 'implementation = "forged/fake_compiler.py"'
REAL_PROFILE_PROVENANCE = 'implementation = "benchmarks/arena/target_echo_reference.py"'


class _ForeignTargetFingerprint(str):
    def __len__(self) -> int:
        raise AssertionError("foreign target digest length hook executed")


@pytest.mark.parametrize(
    "receipt",
    [
        None,
        False,
        1,
        "a" * 63,
        "G" * 64,
        "F" * 64,
        _ForeignTargetFingerprint("a" * 64),
        "a" * 64,
    ],
)
def test_target_source_rejects_invalid_or_forged_hash_receipt(
    monkeypatch: pytest.MonkeyPatch, receipt: object
) -> None:
    """Source hashes must be native, canonical, and bound to actual bytes."""
    monkeypatch.setattr(audit, "_native_regular_bytes", lambda *_args, **_kw: b"source")
    monkeypatch.setattr(audit, "_admit_source_bytes", lambda *_args, **_kw: None)

    class HashReceipt:
        def hexdigest(self) -> object:
            return receipt

    monkeypatch.setattr(audit, "sha256", lambda *_: HashReceipt())
    row = {"algorithm": "direct", "case": {"difficulty": 1}, "trial": 0}
    with pytest.raises(audit.TargetEchoAuditError, match="SHA-256"):
        audit._check_source(row, ".temp/arena-target-echo-test", "eof")


def test_target_source_rejects_jointly_forged_hash_constructors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An agreement between two forged hash providers proves no source bytes."""
    data = b"canonical Malbolge source bytes"
    false_digest = "0" * 64
    assert sha256(data).hexdigest() != false_digest

    class ForgedHash:
        def hexdigest(self) -> str:
            return false_digest

    monkeypatch.setattr(audit, "sha256", lambda _data: ForgedHash())
    monkeypatch.setattr(
        audit,
        "hashlib",
        SimpleNamespace(new=lambda _name, _data: ForgedHash()),
    )
    with pytest.raises(audit.TargetEchoAuditError, match="SHA-256"):
        audit._source_sha256(data)


@pytest.mark.parametrize("stage", ["construct", "digest"])
def test_target_source_hash_fault_is_typed_without_foreign_formatting(
    monkeypatch: pytest.MonkeyPatch, stage: str
) -> None:
    """A failed hash dependency cannot leak its hostile exception formatter."""
    monkeypatch.setattr(audit, "_native_regular_bytes", lambda *_args, **_kw: b"source")
    monkeypatch.setattr(audit, "_admit_source_bytes", lambda *_args, **_kw: None)

    class HashFault(RuntimeError):
        def __str__(self) -> str:
            raise AssertionError("foreign target hash fault formatter executed")

    failure = HashFault("unsafe")

    class HashReceipt:
        def hexdigest(self) -> str:
            raise failure

    def hashed(*_args: object) -> HashReceipt:
        if stage == "construct":
            raise failure
        return HashReceipt()

    monkeypatch.setattr(audit, "sha256", hashed)
    row = {"algorithm": "direct", "case": {"difficulty": 1}, "trial": 0}
    with pytest.raises(audit.TargetEchoAuditError, match="hash") as caught:
        audit._check_source(row, ".temp/arena-target-echo-test", "eof")
    assert caught.value.__cause__ is failure


@pytest.mark.parametrize(
    "foreign", [None, "{}", bytearray(b"{}"), memoryview(b"{}"), object()]
)
def test_target_study_reader_rejects_foreign_byte_receipts(
    monkeypatch: pytest.MonkeyPatch,
    foreign: object,
) -> None:
    """A substituted evidence reader cannot authorize arbitrary source objects."""
    monkeypatch.setattr(
        audit.evidence,
        "read_bounded_regular",
        lambda *_args, **_kwargs: foreign,
    )
    with pytest.raises(audit.TargetEchoAuditError, match="native bounded bytes"):
        audit._document(".temp/arena-target-echo-forged/study.json")


def test_target_study_reader_does_not_run_foreign_decode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Decoding an untrusted bytes subclass can forge the audited study text."""

    class ForgedBytes(bytes):  # ruff: ignore[subclass-builtin]
        def decode(self, *_args: object, **_kwargs: object) -> str:
            raise AssertionError("foreign target study decoder executed")

    monkeypatch.setattr(
        audit.evidence,
        "read_bounded_regular",
        lambda *_args, **_kwargs: ForgedBytes(b"{}"),
    )
    with pytest.raises(audit.TargetEchoAuditError, match="native bounded bytes"):
        audit._document(".temp/arena-target-echo-forged/study.json")


@pytest.mark.parametrize("foreign", [bytearray(b"raw"), memoryview(b"raw")])
def test_target_linked_snapshot_rejects_untrusted_hashable_bytes(
    monkeypatch: pytest.MonkeyPatch,
    foreign: object,
) -> None:
    """A buffer-compatible but foreign receipt cannot certify linked evidence."""
    monkeypatch.setattr(
        audit.evidence,
        "read_bounded_regular",
        lambda *_args, **_kwargs: foreign,
    )
    document: dict[str, Any] = {
        "study": {"id": "unmeasured"},
        "observations": [
            {"experiment_manifest": "runs/a.toml", "raw_sample": "raw/a.csv"}
        ],
    }
    with pytest.raises(audit.TargetEchoAuditError, match="native bounded bytes"):
        audit._snapshot_linked_inputs(
            document, ".temp/arena-target-echo-forged/study.json", "0" * 64
        )


def test_target_evidence_reader_rejects_oversized_native_bytes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The auditor does not trust a substituted bounded reader's size claim."""
    monkeypatch.setattr(
        audit.evidence,
        "read_bounded_regular",
        lambda *_args, **_kwargs: b"x" * 4,
    )
    with pytest.raises(audit.TargetEchoAuditError, match="native bounded bytes"):
        audit._native_regular_bytes(audit._ROOT, "forged", limit=3)


def test_oversized_sparse_tool_rejects_before_auditor_hashing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Read-only replay must refuse unbounded tool hashes on sparse files."""
    emitter = tmp_path / "oversized-emitter"
    runner = tmp_path / "runner"
    _ = emitter.write_bytes(b"x")
    _ = runner.write_bytes(b"runner")
    with emitter.open("r+b") as handle:
        handle.truncate(producer.MAX_TOOL_BYTES)
    assert audit._admit_tool(emitter) == emitter
    with emitter.open("r+b") as handle:
        handle.truncate(producer.MAX_TOOL_BYTES + 1)
    with pytest.raises(audit.TargetEchoAuditError, match="128 MiB"):
        _ = audit._admit_tool(emitter)

    def forbid_open(*args: object, **kwargs: object) -> int:
        _ = (args, kwargs)
        message = "auditor tried to hash an oversized sparse tool"
        raise AssertionError(message)

    monkeypatch.setattr(audit.os, "open", forbid_open)
    with pytest.raises(audit.TargetEchoAuditError, match="128 MiB"):
        _ = audit._tool_identity(emitter, runner)


@pytest.mark.parametrize("folder", ["runs", "raw", "candidates"])
def test_target_audit_inventory_rejects_foreign_entry_before_traversing_rest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    folder: str,
) -> None:
    """A foreign file must fail before an unbounded directory is consumed."""
    prefix = ".temp/arena-target-echo-inventory"
    directory = tmp_path / prefix / folder
    directory.mkdir(parents=True)
    monkeypatch.setattr(audit, "_ROOT", tmp_path)
    stem = "registered-trial"
    registered = (
        f"{stem}.malbolge"
        if folder == "candidates"
        else (f"{stem}.toml" if folder == "runs" else f"{stem}.csv")
    )
    original_iterdir = type(tmp_path).iterdir

    def hostile_directory(path: Path) -> Iterator[Path]:
        if path != directory:
            yield from original_iterdir(path)
            return
        yield directory / registered
        yield directory / "foreign-file"
        message = "auditor traversed foreign directory entries after rejection"
        raise AssertionError(message)

    monkeypatch.setattr(type(tmp_path), "iterdir", hostile_directory)
    with pytest.raises(audit.TargetEchoAuditError, match="unexpected"):
        if folder == "candidates":
            audit._candidate_files(prefix, {stem})
        else:
            audit._check_directory(prefix, folder, {registered})


@pytest.mark.parametrize(
    ("field", "invalid"),
    [
        ("replay_candidates", "false"),
        ("replay_candidates", 0),
        ("require_source_commit_object", "no"),
        ("require_source_commit_object", 1),
        ("stage_rss_breakdown", None),
        ("stage_rss_breakdown", object()),
    ],
)
def test_direct_target_audit_rejects_nonboolean_options_before_access(
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    invalid: object,
) -> None:
    """Forged opt-in values cannot enable replay or publish nonboolean claims."""
    options = replace(audit.AuditOptions(), **{field: invalid})

    def forbidden_prefix(*args: object, **kwargs: object) -> str:
        _ = (args, kwargs)
        message = "invalid options reached path or replay admission"
        raise AssertionError(message)

    monkeypatch.setattr(audit, "_prefix", forbidden_prefix)
    with pytest.raises(audit.TargetEchoAuditError, match="exact booleans"):
        audit.audit(".temp/arena-target-echo-options/study.json", options=options)


@pytest.mark.parametrize("invalid", [None, False, 0, "disabled", object()])
def test_direct_target_audit_rejects_foreign_option_container(
    monkeypatch: pytest.MonkeyPatch,
    invalid: object,
) -> None:
    """Foreign option containers fail before the first file read."""

    def forbidden_prefix(*args: object, **kwargs: object) -> str:
        _ = (args, kwargs)
        message = "foreign options reached path admission"
        raise AssertionError(message)

    monkeypatch.setattr(audit, "_prefix", forbidden_prefix)
    with pytest.raises(audit.TargetEchoAuditError, match="exact booleans"):
        audit.audit(
            ".temp/arena-target-echo-options/study.json",
            options=cast("audit.AuditOptions", invalid),
        )


@pytest.mark.parametrize(
    ("field", "invalid"),
    [
        ("emitter", "/tmp/foreign-emitter"),
        ("emitter", False),
        ("emitter", object()),
        ("runner", "/tmp/foreign-runner"),
        ("runner", 1),
        ("runner", object()),
    ],
)
def test_direct_target_audit_rejects_foreign_tool_locator_before_access(
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    invalid: object,
) -> None:
    """Optional native binary locators require Path or None before any I/O."""
    options = replace(audit.AuditOptions(), **{field: invalid})

    def forbidden_prefix(*args: object, **kwargs: object) -> str:
        _ = (args, kwargs)
        message = "malformed tool locator reached file admission"
        raise AssertionError(message)

    monkeypatch.setattr(audit, "_prefix", forbidden_prefix)
    with pytest.raises(audit.TargetEchoAuditError, match="exact Paths"):
        audit.audit(".temp/arena-target-echo-options/study.json", options=options)


class _UntrustedSource(bytes):  # ruff: ignore[subclass-builtin]
    """A foreign source may replace even its byte count with arbitrary code."""

    def __len__(self) -> int:
        message = "untrusted source length executed"
        raise AssertionError(message)


class _UntrustedPairs(int):  # ruff: ignore[subclass-builtin]
    """A foreign repetition count can intercept arithmetic."""

    def __add__(self, other: object) -> int:
        del other
        message = "untrusted source geometry arithmetic executed"
        raise AssertionError(message)


class _UntrustedAlgorithm(str):  # ruff: ignore[subclass-builtin]
    """A foreign algorithm name can intercept equality checks."""

    def __eq__(self, other: object) -> bool:
        del other
        message = "untrusted algorithm equality executed"
        raise AssertionError(message)


@pytest.mark.parametrize(
    ("source", "pairs", "algorithm"),
    [
        (None, 1, audit.WALK),
        ("a", 1, audit.WALK),
        (bytearray(b"a"), 1, audit.WALK),
        (_UntrustedSource(b"a"), 1, audit.WALK),
        (b"", 1, audit.WALK),
        (b"x" * (producer.MAX_TARGET_BYTES + 1), 1, audit.WALK),
        (b"a", None, audit.WALK),
        (b"a", True, audit.WALK),
        (b"a", 1.0, audit.WALK),
        (b"a", _UntrustedPairs(1), audit.WALK),
        (b"a", 0, audit.WALK),
        (b"a", -1, audit.WALK),
        (b"a", producer.MAX_PAIRS + 1, audit.WALK),
        (b"a", 10**15, audit.WALK),
        (b"a", 1, _UntrustedAlgorithm(audit.WALK)),
        (b"a", 1, object()),
    ],
)
def test_direct_forward_candidate_rejects_foreign_or_unbounded_inputs(
    monkeypatch: pytest.MonkeyPatch,
    source: object,
    pairs: object,
    algorithm: object,
) -> None:
    """Untrusted direct inputs reject before constructing source operations."""

    def forbidden_operations(*args: object, **kwargs: object) -> list[str]:
        _ = (args, kwargs)
        message = "invalid source request attempted operation allocation"
        raise AssertionError(message)

    monkeypatch.setattr(audit, "_expected_operations", forbidden_operations)
    with pytest.raises(audit.TargetEchoAuditError, match="forward source"):
        audit.check_forward_candidate_source(
            cast("bytes", source),
            pairs=cast("int", pairs),
            algorithm=cast("str", algorithm),
        )


class _UntrustedReplayTuple(tuple):  # ruff: ignore[subclass-builtin]
    """Foreign parameter tuple can trap unpacking before read admission."""

    def __iter__(self) -> Any:
        message = "foreign replay tuple iterator executed"
        raise AssertionError(message)


class _UntrustedReplayList(list[bytes]):
    """Reject caller-owned mutable witness containers before iterating."""

    def __iter__(self) -> Any:
        message = "foreign replay list iterator executed"
        raise AssertionError(message)


@pytest.mark.parametrize(
    ("source", "runner", "case", "settings"),
    [
        (None, audit._ROOT / "runner", (1, audit.WALK), (104, False, False, None)),
        (
            Path("relative.malbolge"),
            audit._ROOT / "runner",
            (1, audit.WALK),
            (104, False, False, None),
        ),
        (
            Path("/tmp/outside.malbolge"),
            audit._ROOT / "runner",
            (1, audit.WALK),
            (104, False, False, None),
        ),
        (
            audit._ROOT / "test.malbolge",
            object(),
            (1, audit.WALK),
            (104, False, False, None),
        ),
        (
            audit._ROOT / "test.malbolge",
            Path("relative-runner"),
            (1, audit.WALK),
            (104, False, False, None),
        ),
        (
            audit._ROOT / "test.malbolge",
            audit._ROOT / "runner",
            _UntrustedReplayTuple((1, audit.WALK)),
            (104, False, False, None),
        ),
        (
            audit._ROOT / "test.malbolge",
            audit._ROOT / "runner",
            (1,),
            (104, False, False, None),
        ),
        (
            audit._ROOT / "test.malbolge",
            audit._ROOT / "runner",
            (True, audit.WALK),
            (104, False, False, None),
        ),
        (
            audit._ROOT / "test.malbolge",
            audit._ROOT / "runner",
            (10**16, audit.WALK),
            (104, False, False, None),
        ),
        (
            audit._ROOT / "test.malbolge",
            audit._ROOT / "runner",
            (1, _UntrustedAlgorithm(audit.WALK)),
            (104, False, False, None),
        ),
        (
            audit._ROOT / "test.malbolge",
            audit._ROOT / "runner",
            (1, audit.WALK),
            _UntrustedReplayTuple((104, False, False, None)),
        ),
        (
            audit._ROOT / "test.malbolge",
            audit._ROOT / "runner",
            (1, audit.WALK),
            (104, False, False),
        ),
        (
            audit._ROOT / "test.malbolge",
            audit._ROOT / "runner",
            (1, audit.WALK),
            (104, 1, False, None),
        ),
        (
            audit._ROOT / "test.malbolge",
            audit._ROOT / "runner",
            (1, audit.WALK),
            (104, False, "false", None),
        ),
        (
            audit._ROOT / "test.malbolge",
            audit._ROOT / "runner",
            (1, audit.WALK),
            (True, False, False, None),
        ),
        (
            audit._ROOT / "test.malbolge",
            audit._ROOT / "runner",
            (1, audit.WALK),
            (103, False, False, None),
        ),
        (
            audit._ROOT / "test.malbolge",
            audit._ROOT / "runner",
            (1, audit.WALK),
            (104, False, False, []),
        ),
        (
            audit._ROOT / "test.malbolge",
            audit._ROOT / "runner",
            (1, audit.WALK),
            (104, False, True, []),
        ),
        (
            audit._ROOT / "test.malbolge",
            audit._ROOT / "runner",
            (1, audit.WALK),
            (104, True, True, _UntrustedReplayList([])),
        ),
        (
            audit._ROOT / "test.malbolge",
            audit._ROOT / "runner",
            (1, audit.WALK),
            (104, True, True, [object()]),
        ),
    ],
)
def test_direct_forward_replay_rejects_untrusted_shape_before_io(
    monkeypatch: pytest.MonkeyPatch,
    source: object,
    runner: object,
    case: object,
    settings: object,
) -> None:
    """Direct second-VM replay cannot execute caller hooks or read first."""

    def forbidden_read(*args: object, **kwargs: object) -> bytes:
        _ = (args, kwargs)
        message = "invalid replay options reached retained source reader"
        raise AssertionError(message)

    monkeypatch.setattr(audit.evidence, "read_bounded_regular", forbidden_read)
    with pytest.raises(audit.TargetEchoAuditError, match="target replay"):
        audit.check_forward_vm_replay(
            cast("Path", source),
            cast("Path", runner),
            case=cast("tuple[int, str]", case),
            replay_options=cast(
                "tuple[int | None, bool, bool, list[bytes] | None]", settings
            ),
        )


@pytest.mark.parametrize(
    ("payload", "source_error"),
    [
        (b"parser_probe = " + b"[" * 1000 + b"1" + b"]" * 1000, RecursionError),
        (b"parser_probe = " + b"9" * 5000, ValueError),
    ],
    ids=["array-depth", "integer-digits"],
)
def test_retained_rss_extension_contains_toml_parser_capacity_failure(
    monkeypatch: pytest.MonkeyPatch,
    payload: bytes,
    source_error: type[Exception],
) -> None:
    """Run RSS sidecars cannot leak raw TOML host-capacity exceptions."""
    manifest = b"[arena_rss]\n" + payload

    def read_manifest(root: Path, relative: str, *, limit: int) -> bytes:
        """Supply the adversarial bounded run bytes, not fixture disk state.

        Returns:
            Hostile but below-limit TOML source bytes.

        """
        assert root == audit._ROOT
        assert relative == RSS_RUN_RELATIVE
        assert limit == evidence.MAX_MANIFEST_BYTES
        return manifest

    monkeypatch.setattr(audit.evidence, "read_bounded_regular", read_manifest)
    with pytest.raises(
        audit.TargetEchoAuditError,
        match="target RSS run manifest is invalid TOML",
    ) as error:
        audit._rss_digest({"experiment_manifest": RSS_RUN_RELATIVE}, version=1)
    assert type(error.value.__cause__) is source_error


@pytest.mark.parametrize("case", ["forged_digest", "hidden_link", "bad_source"])
def test_retained_rss_manifest_rejects_substituted_toml_source_receipt(
    monkeypatch: pytest.MonkeyPatch,
    case: str,
) -> None:
    """The run's linked receipt identity must originate in its TOML bytes."""
    pinned = "a" * 64
    manifest = (
        f'[arena_rss]\nschema_version = 1\nsha256 = "{pinned}"\n'.encode()
        if case != "bad_source"
        else b"[arena_rss\nschema_version = 1"
    )
    monkeypatch.setattr(
        audit.evidence, "read_bounded_regular", lambda *_a, **_kw: manifest
    )
    parsed = (
        {"arena_rss": {"schema_version": 1, "sha256": "b" * 64}}
        if case != "hidden_link"
        else {}
    )
    monkeypatch.setattr(audit.tomllib, "loads", lambda *_a, **_kw: parsed)
    version = None if case == "hidden_link" else 1

    with pytest.raises(audit.TargetEchoAuditError, match="source TOML|invalid TOML"):
        audit._rss_digest({"experiment_manifest": RSS_RUN_RELATIVE}, version=version)


@pytest.mark.parametrize("fault_type", [RuntimeError, TypeError, OverflowError])
def test_retained_rss_manifest_contains_foreign_decoder_faults(
    monkeypatch: pytest.MonkeyPatch,
    fault_type: type[Exception],
) -> None:
    """A public TOML decoder fault must remain typed without formatting it."""
    pinned = "a" * 64
    manifest = f'[arena_rss]\nschema_version = 1\nsha256 = "{pinned}"\n'.encode()
    monkeypatch.setattr(
        audit.evidence, "read_bounded_regular", lambda *_a, **_kw: manifest
    )

    def forbidden_format(_self: Exception) -> str:
        raise AssertionError("foreign decoder exception formatter executed")

    hostile_type = type(
        "HostileTomlFault", (fault_type,), {"__str__": forbidden_format}
    )
    fault = hostile_type("untrusted TOML decoder failure")

    def failing_decoder(_text: str) -> Never:
        raise fault

    monkeypatch.setattr(audit.tomllib, "loads", failing_decoder)
    with pytest.raises(audit.TargetEchoAuditError, match="invalid TOML") as caught:
        audit._rss_digest({"experiment_manifest": RSS_RUN_RELATIVE}, version=1)
    assert caught.value.__cause__ is fault


def test_retained_rss_manifest_accepts_equivalent_toml_decoder_wrapper(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Decoder adapter identity is not itself an evidence mismatch."""
    pinned = "a" * 64
    manifest = f'[arena_rss]\nschema_version = 1\nsha256 = "{pinned}"\n'.encode()
    monkeypatch.setattr(
        audit.evidence, "read_bounded_regular", lambda *_a, **_kw: manifest
    )
    original = audit.tomllib.loads

    def equivalent(text: str) -> dict[str, Any]:
        return original(text)

    monkeypatch.setattr(audit.tomllib, "loads", equivalent)
    assert (
        audit._rss_digest({"experiment_manifest": RSS_RUN_RELATIVE}, version=1)
        == pinned
    )


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
    with pytest.raises(
        audit.TargetEchoAuditError, match="target audit executable identity changed"
    ):
        audit._tool_identity(emitter, runner)


@pytest.mark.parametrize("read_fails", [True, False])
def test_tool_fingerprint_close_error_does_not_hide_read_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    read_fails: bool,
) -> None:
    """Descriptor cleanup must not replace the original hashing failure."""
    emitter = tmp_path / "emitter"
    runner = tmp_path / "runner"
    _ = emitter.write_bytes(b"trusted-emitter")
    _ = runner.write_bytes(b"trusted-runner")
    read_error = OSError("injected original descriptor read failure")
    close_error = OSError("injected secondary descriptor close failure")
    original_read = audit.os.read
    original_close = audit.os.close

    def broken_read(fd: int, size: int) -> bytes:
        if read_fails:
            raise read_error
        return original_read(fd, size)

    def broken_close(fd: int) -> None:
        original_close(fd)
        raise close_error

    with monkeypatch.context() as patch:
        patch.setattr(audit.os, "read", broken_read)
        patch.setattr(audit.os, "close", broken_close)
        with pytest.raises(audit.TargetEchoAuditError) as observed:
            _ = audit._tool_identity(emitter, runner)
    if read_fails:
        assert observed.value.__cause__ is read_error
        assert any("cleanup" in note for note in read_error.__notes__)
    else:
        assert observed.value.__cause__ is close_error


@pytest.mark.parametrize("site", ["lstat", "open", "fstat", "read", "close"])
@pytest.mark.parametrize(
    "failure_type", [ValueError, RuntimeError, TypeError, AttributeError]
)
def test_tool_fingerprint_types_non_oserror_host_faults(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    site: str,
    failure_type: type[Exception],
) -> None:
    """Unexpected host inspection and descriptor errors remain typed."""
    emitter = tmp_path / "emitter"
    runner = tmp_path / "runner"
    _ = emitter.write_bytes(b"trusted-emitter")
    _ = runner.write_bytes(b"trusted-runner")
    fault = failure_type("injected tool descriptor host fault")
    original_close = audit.os.close
    original_lstat = type(emitter).lstat

    def bad_host(*args: object, **kwargs: object) -> object:
        del kwargs
        if site == "close":
            original_close(cast("int", args[0]))
        raise fault

    def bad_lstat(path: Path) -> object:
        if path == emitter:
            return bad_host(path)
        return original_lstat(path)

    with monkeypatch.context() as patch:
        if site == "lstat":
            patch.setattr(type(emitter), "lstat", bad_lstat)
        else:
            patch.setattr(audit.os, site, bad_host)
        with pytest.raises(
            audit.TargetEchoAuditError, match="executable identity"
        ) as caught:
            _ = audit._tool_identity(emitter, runner)
    assert caught.value.__cause__ is fault


class _ForgedToolBytes(bytes):
    """A bytes subtype is not a native os.read result."""


@pytest.mark.parametrize(
    "kind",
    [
        "none",
        "bool",
        "integer",
        "text",
        "bytearray",
        "memoryview",
        "subtype",
        "overlong",
    ],
)
def test_tool_fingerprint_rejects_noncanonical_host_read_chunks(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
) -> None:
    """Only native bounded bytes from an opened inode may be hashed."""
    emitter = tmp_path / "emitter"
    runner = tmp_path / "runner"
    _ = emitter.write_bytes(b"trusted-emitter")
    _ = runner.write_bytes(b"trusted-runner")
    raw = b"trusted-emitter"
    invalid: dict[str, object] = {
        "none": None,
        "bool": False,
        "integer": 0,
        "text": raw.decode("ascii"),
        "bytearray": bytearray(raw),
        "memoryview": memoryview(raw),
        "subtype": _ForgedToolBytes(raw),
        "overlong": raw + b"x",
    }

    def altered_read(fd: int, size: int) -> bytes:
        del fd, size
        return cast("bytes", invalid[kind])

    with monkeypatch.context() as patch:
        patch.setattr(audit.os, "read", altered_read)
        with pytest.raises(audit.TargetEchoAuditError, match="executable identity"):
            _ = audit._tool_identity(emitter, runner)


@pytest.mark.parametrize(
    "trailer", [None, True, b"x", bytearray(), _ForgedToolBytes(b"")]
)
def test_tool_fingerprint_rejects_foreign_trailing_read_result(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    trailer: object,
) -> None:
    """EOF after a complete hash must be an exact empty bytes receipt."""
    emitter = tmp_path / "emitter"
    runner = tmp_path / "runner"
    _ = emitter.write_bytes(b"trusted-emitter")
    _ = runner.write_bytes(b"trusted-runner")
    original_read = audit.os.read

    def altered_read(fd: int, size: int) -> bytes:
        if size == 1:
            return cast("bytes", trailer)
        return original_read(fd, size)

    with monkeypatch.context() as patch:
        patch.setattr(audit.os, "read", altered_read)
        with pytest.raises(audit.TargetEchoAuditError, match="executable identity"):
            _ = audit._tool_identity(emitter, runner)


@pytest.mark.parametrize("failure_type", [ValueError, RuntimeError])
def test_tool_fingerprint_secondary_non_oserror_close_preserves_primary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure_type: type[Exception],
) -> None:
    """A failing close never replaces the fault that interrupted hashing."""
    emitter = tmp_path / "emitter"
    runner = tmp_path / "runner"
    _ = emitter.write_bytes(b"trusted-emitter")
    _ = runner.write_bytes(b"trusted-runner")
    primary = failure_type("primary host read fault")
    secondary = failure_type("secondary descriptor cleanup fault")
    original_close = audit.os.close

    def bad_read(fd: int, size: int) -> bytes:
        del fd, size
        raise primary

    def bad_close(fd: int) -> None:
        original_close(fd)
        raise secondary

    with monkeypatch.context() as patch:
        patch.setattr(audit.os, "read", bad_read)
        patch.setattr(audit.os, "close", bad_close)
        with pytest.raises(
            audit.TargetEchoAuditError, match="executable identity"
        ) as caught:
            _ = audit._tool_identity(emitter, runner)
    assert caught.value.__cause__ is primary
    assert any("cleanup" in note for note in primary.__notes__)


@pytest.mark.parametrize("failure_type", [OSError, ValueError, RuntimeError])
def test_tool_fingerprint_close_does_not_call_foreign_primary_note_hook(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure_type: type[Exception],
) -> None:
    """A secondary close failure cannot run a primary's overridden hook."""
    emitter = tmp_path / "emitter"
    runner = tmp_path / "runner"
    _ = emitter.write_bytes(b"trusted-emitter")
    _ = runner.write_bytes(b"trusted-runner")

    def hostile_add_note(self: BaseException, note: str) -> None:
        del self, note
        raise AssertionError("foreign primary note hook executed")

    foreign_type = type(
        "ForeignPrimaryReadError", (failure_type,), {"add_note": hostile_add_note}
    )
    primary = foreign_type("read failed")
    secondary = OSError("close failed")
    original_close = audit.os.close

    def bad_read(fd: int, size: int) -> bytes:
        del fd, size
        raise primary

    def bad_close(fd: int) -> None:
        original_close(fd)
        raise secondary

    with monkeypatch.context() as patch:
        patch.setattr(audit.os, "read", bad_read)
        patch.setattr(audit.os, "close", bad_close)
        with pytest.raises(
            audit.TargetEchoAuditError, match="executable identity"
        ) as caught:
            _ = audit._tool_identity(emitter, runner)

    assert caught.value.__cause__ is primary
    assert any("cleanup" in note for note in primary.__notes__)


def test_tool_fingerprint_accepts_host_short_read_chunks(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Legitimate partial ordinary-file reads preserve the exact digest."""
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
    original_read = audit.os.read

    def partial_read(fd: int, size: int) -> bytes:
        return original_read(fd, min(size, 3))

    with monkeypatch.context() as patch:
        patch.setattr(audit.os, "read", partial_read)
        actual = audit._tool_identity(emitter, runner)
    assert actual == "local-compiler-vm-sha256:" + expected.hexdigest()


@pytest.mark.parametrize(
    "receipt",
    [None, False, True, -1, 1.5, "3", 1 << 128],
    ids=["none", "false", "true", "negative", "float", "text", "overflow"],
)
def test_tool_fingerprint_rejects_foreign_open_descriptor_before_host_io(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    receipt: object,
) -> None:
    """A forged open result cannot drive fstat/read/close on a caller FD."""
    emitter = tmp_path / "emitter"
    runner = tmp_path / "runner"
    emitter.write_bytes(b"trusted-emitter")
    runner.write_bytes(b"trusted-runner")

    def fail_downstream(*_args: object, **_kwargs: object) -> None:
        pytest.fail("foreign descriptor reached a host descriptor operation")

    with monkeypatch.context() as patch:
        patch.setattr(audit.os, "open", lambda *_args, **_kwargs: receipt)
        patch.setattr(audit.os, "fstat", fail_downstream)
        patch.setattr(audit.os, "read", fail_downstream)
        patch.setattr(audit.os, "close", fail_downstream)
        with pytest.raises(audit.TargetEchoAuditError, match="executable identity"):
            audit._tool_identity(emitter, runner)


@pytest.mark.parametrize("receipt", [False, True, 0, 1, "closed", b"closed"])
def test_tool_fingerprint_requires_native_void_close_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    receipt: object,
) -> None:
    """Hash completion is unconfirmed if descriptor cleanup forges success."""
    emitter = tmp_path / "emitter"
    runner = tmp_path / "runner"
    emitter.write_bytes(b"trusted-emitter")
    runner.write_bytes(b"trusted-runner")
    real_close = audit.os.close
    closed: list[int] = []

    def forged_close(fd: int) -> None:
        real_close(fd)
        closed.append(fd)
        return cast("None", receipt)

    with monkeypatch.context() as patch:
        patch.setattr(audit.os, "close", forged_close)
        with pytest.raises(audit.TargetEchoAuditError, match="executable identity"):
            audit._tool_identity(emitter, runner)
    assert len(closed) == 1


@pytest.mark.parametrize("receipt", [False, 0, "closed"])
def test_tool_fingerprint_forged_close_preserves_primary_read_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    receipt: object,
) -> None:
    """The original read failure prevails over a forged cleanup receipt."""
    emitter = tmp_path / "emitter"
    runner = tmp_path / "runner"
    emitter.write_bytes(b"trusted-emitter")
    runner.write_bytes(b"trusted-runner")
    primary = OSError("primary executable hash read failed")
    real_close = audit.os.close

    def fail_read(_fd: int, _size: int) -> bytes:
        raise primary

    def forged_close(fd: int) -> None:
        real_close(fd)
        return cast("None", receipt)

    with monkeypatch.context() as patch:
        patch.setattr(audit.os, "read", fail_read)
        patch.setattr(audit.os, "close", forged_close)
        with pytest.raises(
            audit.TargetEchoAuditError, match="executable identity"
        ) as caught:
            audit._tool_identity(emitter, runner)
    assert caught.value.__cause__ is primary
    assert any("cleanup" in note for note in primary.__notes__)


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
    assert audit._tool_identity(emitter, runner) == (
        "local-compiler-vm-sha256:" + expected.hexdigest()
    )


class _ForgedToolFingerprint(str):  # ruff: ignore[subclass-builtin]
    """A foreign hash return may impersonate a native digest."""

    def __ne__(self, other: object) -> bool:
        del other
        return False


@pytest.mark.parametrize("receipt", ["wrong", "foreign", "short", "nonnative", "fault"])
def test_tool_fingerprint_rejects_unverified_hash_provider_receipts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    receipt: str,
) -> None:
    """The identity must bind streamed tool bytes, not a forged hash object."""
    emitter = tmp_path / "emitter"
    runner = tmp_path / "runner"
    _ = emitter.write_bytes(b"trusted-emitter")
    _ = runner.write_bytes(b"trusted-runner")
    bad_digest = "0" * 64
    expected = sha256()
    for raw in (b"trusted-emitter", b"trusted-runner"):
        expected.update(len(raw).to_bytes(8, "big"))
        expected.update(raw)
    assert bad_digest != expected.hexdigest()
    failure = RuntimeError("SHA provider failed")

    class ForgedHash:
        def update(self, raw: bytes) -> None:
            del raw

        def hexdigest(self) -> object:
            if receipt == "fault":
                raise failure
            return {
                "wrong": bad_digest,
                "foreign": _ForgedToolFingerprint(bad_digest),
                "short": "0",
                "nonnative": 123,
            }[receipt]

    monkeypatch.setattr(audit, "sha256", lambda: ForgedHash())
    with pytest.raises(
        audit.TargetEchoAuditError, match="SHA-256|executable identity"
    ) as caught:
        audit._tool_identity(emitter, runner)
    if receipt == "fault":
        assert caught.value.__cause__ is failure


def test_target_tool_rejects_jointly_forged_hash_constructors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Two forged digest constructors cannot certify uninspected tool bytes."""
    emitter = tmp_path / "emitter"
    runner = tmp_path / "runner"
    _ = emitter.write_bytes(b"genuine-emitter")
    _ = runner.write_bytes(b"genuine-runner")
    false_digest = "0" * 64
    expected = sha256()
    for contents in (b"genuine-emitter", b"genuine-runner"):
        expected.update(len(contents).to_bytes(8, "big"))
        expected.update(contents)
    assert expected.hexdigest() != false_digest

    class ForgedHash:
        def update(self, _data: bytes) -> None:
            pass

        def hexdigest(self) -> str:
            return false_digest

    monkeypatch.setattr(audit, "sha256", ForgedHash)
    monkeypatch.setattr(
        audit,
        "hashlib",
        SimpleNamespace(new=lambda _name: ForgedHash()),
    )
    with pytest.raises(audit.TargetEchoAuditError, match="SHA-256"):
        audit._tool_identity(emitter, runner)


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
    assert audit._admit_tool(emitter) == emitter
    emitter.unlink()
    emitter.symlink_to(foreign)
    with pytest.raises(
        audit.TargetEchoAuditError, match="target audit executable identity changed"
    ):
        audit._tool_identity(emitter, runner)


@pytest.fixture
def retained(
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[tuple[Path, dict[str, Any], str]]:
    """Create a real target pilot and remove only its own ignored directory.

    Yields:
        Local output root, recorded study and canonical relative path.

    """
    if not producer.DEFAULT_EMITTER.is_file() or not producer.DEFAULT_RUNNER.is_file():
        pytest.skip("repository Malbolge binaries are not built")
    with tempfile.TemporaryDirectory(
        dir=producer._TEMP,
        prefix="arena-target-test-tools-",
    ) as tool_directory:
        emitter = Path(tool_directory) / "malbolge_layout"
        runner = Path(tool_directory) / "malbolge"
        # Private fixture copies cannot change the shared build inode ctime
        # when another test creates or removes its executable hardlinks.
        shutil.copy2(producer.DEFAULT_EMITTER, emitter)
        shutil.copy2(producer.DEFAULT_RUNNER, runner)
        monkeypatch.setattr(producer, "DEFAULT_EMITTER", emitter)
        monkeypatch.setattr(producer, "DEFAULT_RUNNER", runner)
        directory, document = producer.run_study(
            producer.StudyPlan((1, 4), 2),
            emitter=emitter,
            runner=runner,
        )
        relative = (directory / "study.json").relative_to(producer._ROOT)
        try:
            yield directory, document, relative.as_posix()
        finally:
            shutil.rmtree(directory)


@pytest.fixture
def patterned(
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[tuple[Path, dict[str, Any], str]]:
    """Create an independently replayable patterned-input target study.

    Yields:
        Local output root, recorded study and canonical relative path.

    """
    if not producer.DEFAULT_EMITTER.is_file() or not producer.DEFAULT_RUNNER.is_file():
        pytest.skip("repository Malbolge binaries are not built")
    with tempfile.TemporaryDirectory(
        dir=producer._TEMP,
        prefix="arena-patterned-test-tools-",
    ) as tool_directory:
        emitter = Path(tool_directory) / "malbolge_layout"
        runner = Path(tool_directory) / "malbolge"
        shutil.copy2(producer.DEFAULT_EMITTER, emitter)
        shutil.copy2(producer.DEFAULT_RUNNER, runner)
        monkeypatch.setattr(producer, "DEFAULT_EMITTER", emitter)
        monkeypatch.setattr(producer, "DEFAULT_RUNNER", runner)
        directory, document = producer.run_study(
            producer.StudyPlan((1, 4), 2, producer.PATTERNED_MODE),
            emitter=emitter,
            runner=runner,
        )
        relative = (directory / "study.json").relative_to(producer._ROOT)
        try:
            yield directory, document, relative.as_posix()
        finally:
            shutil.rmtree(directory)


@pytest.fixture(params=[producer.EOF_MODE, producer.PATTERNED_MODE])
def counted_study(
    request: pytest.FixtureRequest,
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[tuple[Path, dict[str, Any], str]]:
    """Retain real counted-instruction target studies for two input modes.

    Yields:
        The source root, counted study, and canonical relative path.

    """
    if not producer.DEFAULT_EMITTER.is_file() or not producer.DEFAULT_RUNNER.is_file():
        pytest.skip("built emitter and normative VM required")
    mode = str(request.param)
    with tempfile.TemporaryDirectory(
        dir=producer._TEMP, prefix="arena-counted-test-tools-"
    ) as tool_directory:
        emitter = Path(tool_directory) / "malbolge_layout"
        runner = Path(tool_directory) / "malbolge"
        shutil.copy2(producer.DEFAULT_EMITTER, emitter)
        shutil.copy2(producer.DEFAULT_RUNNER, runner)
        monkeypatch.setattr(producer, "DEFAULT_EMITTER", emitter)
        monkeypatch.setattr(producer, "DEFAULT_RUNNER", runner)
        directory, document = producer.run_study(
            producer.StudyPlan((1, 4), 2, mode, measure_steps=True),
            emitter=emitter,
            runner=runner,
        )
        try:
            relative = (directory / "study.json").relative_to(producer._ROOT)
            yield directory, document, relative.as_posix()
        finally:
            shutil.rmtree(directory)


@pytest.fixture
def forward_skip(
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[tuple[Path, dict[str, Any], str]]:
    """Generate actual same-size jump/step cohorts using pinned tools.

    Yields:
        Local study directory, retained document, canonical study path.

    """
    if not producer.DEFAULT_EMITTER.is_file() or not producer.DEFAULT_RUNNER.is_file():
        pytest.skip("repository Malbolge emitter and VM are not available")
    with tempfile.TemporaryDirectory(
        dir=producer._TEMP, prefix="arena-forward-test-tools-"
    ) as tool_directory:
        emitter = Path(tool_directory) / "malbolge_layout"
        runner = Path(tool_directory) / "malbolge"
        shutil.copy2(producer.DEFAULT_EMITTER, emitter)
        shutil.copy2(producer.DEFAULT_RUNNER, runner)
        monkeypatch.setattr(producer, "DEFAULT_EMITTER", emitter)
        monkeypatch.setattr(producer, "DEFAULT_RUNNER", runner)
        directory, document = producer.run_study(
            producer.StudyPlan(
                (1, 4, 16, 64),
                1,
                producer.PATTERNED_MODE,
                measure_steps=True,
                layout_mode=producer.FORWARD_SKIP_LAYOUT,
            ),
            emitter=emitter,
            runner=runner,
        )
        try:
            relative = (directory / "study.json").relative_to(producer._ROOT)
            yield directory, document, relative.as_posix()
        finally:
            shutil.rmtree(directory)


@pytest.fixture
def timed_forward(
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[tuple[Path, dict[str, Any], str]]:
    """Produce one actual four-objective source verification cohort.

    Yields:
        Retained study directory, canonical document, relative study path.

    """
    if not producer.DEFAULT_EMITTER.is_file() or not producer.DEFAULT_RUNNER.is_file():
        pytest.skip("built layout emitter and VM are required")
    with tempfile.TemporaryDirectory(
        dir=producer._TEMP, prefix="arena-verifier-test-tools-"
    ) as tool_directory:
        emitter = Path(tool_directory) / "malbolge_layout"
        runner = Path(tool_directory) / "malbolge"
        shutil.copy2(producer.DEFAULT_EMITTER, emitter)
        shutil.copy2(producer.DEFAULT_RUNNER, runner)
        monkeypatch.setattr(producer, "DEFAULT_EMITTER", emitter)
        monkeypatch.setattr(producer, "DEFAULT_RUNNER", runner)
        directory, document = producer.run_study(
            producer.StudyPlan(
                (1, 64),
                2,
                producer.PATTERNED_MODE,
                measure_steps=True,
                layout_mode=producer.FORWARD_SKIP_LAYOUT,
                measure_verifier=True,
            ),
            emitter=emitter,
            runner=runner,
        )
        try:
            relative = (directory / "study.json").relative_to(producer._ROOT)
            yield directory, document, relative.as_posix()
        finally:
            shutil.rmtree(directory)


@pytest.fixture
def replay_forward(
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[tuple[Path, dict[str, Any], str]]:
    """Generate an actual source-plus-second-VM verifier-cost study.

    Yields:
        Retained study directory, document and canonical relative location.

    """
    if not producer.DEFAULT_EMITTER.is_file() or not producer.DEFAULT_RUNNER.is_file():
        pytest.skip("built Malbolge emitter and VM required")
    with tempfile.TemporaryDirectory(
        dir=producer._TEMP, prefix="arena-replay-cost-tools-"
    ) as tools:
        emitter = Path(tools) / "malbolge_layout"
        runner = Path(tools) / "malbolge"
        shutil.copy2(producer.DEFAULT_EMITTER, emitter)
        shutil.copy2(producer.DEFAULT_RUNNER, runner)
        monkeypatch.setattr(producer, "DEFAULT_EMITTER", emitter)
        monkeypatch.setattr(producer, "DEFAULT_RUNNER", runner)
        directory, document = producer.run_study(
            producer.StudyPlan(
                (1, 4, 16, 64),
                1,
                producer.PATTERNED_MODE,
                measure_steps=True,
                layout_mode=producer.FORWARD_SKIP_LAYOUT,
                measure_verifier=True,
                verifier_mode=producer.REPLAY_VERIFIER_MODE,
            ),
            emitter=emitter,
            runner=runner,
        )
        try:
            relative = (directory / "study.json").relative_to(producer._ROOT)
            yield directory, document, relative.as_posix()
        finally:
            shutil.rmtree(directory)


def _save(directory: Path, document: dict[str, Any]) -> None:
    (directory / "study.json").write_text(
        json.dumps(document, sort_keys=True),
        encoding="utf-8",
    )


def _first_source(directory: Path, document: dict[str, Any]) -> Path:
    row = document["observations"][0]
    case, trial = row["case"], row["trial"]
    stem = f"{row['algorithm']}-pairs-{case['difficulty']}-trial-{trial}"
    return directory / "candidates" / f"{stem}.malbolge"


def _recheck_generic(document: dict[str, Any]) -> None:
    admitted = analyze.parse_document(json.dumps(document))
    _ = evidence.validate_links(
        admitted,
        producer._ROOT,
        policy=evidence.EvidencePolicy(
            require_raw_rows=True,
            require_trial_run_identity=True,
            require_budget_agreement=True,
        ),
    )


def test_replay_verifier_measures_second_normative_vm_with_true_work_savings(
    replay_forward: tuple[Path, dict[str, Any], str],
) -> None:
    """Second execution measures guest oracle cost, not just static parsing."""
    _, document, relative = replay_forward
    assert document["study"]["id"] == producer.FORWARD_REPLAY_COST_STUDY
    assert document["study"]["objectives"] == [
        ELAPSED,
        ARTIFACT_BYTES,
        RUNTIME_STEPS,
        VERIFIER_COST_METRIC,
    ]
    assert len(document["observations"]) == ROWS
    for row in document["observations"]:
        assert row["outcome"] == analyze.VERIFIED
        assert 0 < row["metrics"][VERIFIER_COST_METRIC] <= row["metrics"][ELAPSED]
    for level in (1, 4, 16, 64):
        rows = {
            row["algorithm"]: row
            for row in document["observations"]
            if row["case"]["difficulty"] == level
        }
        walked, skipped = rows[producer.WALK], rows[producer.SKIP]
        assert walked["metrics"][ARTIFACT_BYTES] == skipped["metrics"][ARTIFACT_BYTES]
        assert (
            walked["metrics"][RUNTIME_STEPS] - skipped["metrics"][RUNTIME_STEPS]
            == EXPECTED_GUEST_SAVINGS
        )
    report = audit.audit(
        relative,
        options=audit.AuditOptions(
            replay_candidates=True,
            require_source_commit_object=True,
        ),
    )
    assert report["target_sources_replayed"] == ROWS
    assert report["source_commit_object_verified"] is True
    assert report["evidence_preflight"]["raw_rows_matched"] == ROWS


@pytest.mark.parametrize(
    "wrong_id", [producer.FORWARD_STUDY, producer.FORWARD_VERIFIER_COST_STUDY]
)
def test_replay_cost_study_cannot_be_renamed_to_earlier_protocol(
    replay_forward: tuple[Path, dict[str, Any], str],
    wrong_id: str,
) -> None:
    """A real replay-cost report cannot silently masquerade as older modes."""
    directory, document, relative = replay_forward
    forged = copy.deepcopy(document)
    forged["study"]["id"] = wrong_id
    if wrong_id == producer.FORWARD_STUDY:
        forged["study"]["objectives"].remove(VERIFIER_COST_METRIC)
    _save(directory, forged)
    if wrong_id == producer.FORWARD_STUDY:
        with pytest.raises(audit.TargetEchoAuditError, match="verifier cost"):
            audit._check_verifier_cost_claims(forged)
    with pytest.raises(
        audit.TargetEchoAuditError, match=r"verifier cost|fixed echo oracle"
    ):
        audit.audit(relative)


def test_timed_source_verifier_retains_four_real_costs_and_replays(
    timed_forward: tuple[Path, dict[str, Any], str],
) -> None:
    """Actual independent decode cost is linked, paired and replayable."""
    _, document, relative = timed_forward
    assert document["study"]["id"] == producer.FORWARD_VERIFIER_COST_STUDY
    assert document["study"]["objectives"] == [
        "elapsed_ns",
        ARTIFACT_BYTES,
        RUNTIME_STEPS,
        "verifier_ns",
    ]
    assert len(document["observations"]) == ROWS
    for row in document["observations"]:
        assert row["outcome"] == analyze.VERIFIED
        assert type(row["metrics"]["verifier_ns"]) is int
        assert row["metrics"]["verifier_ns"] > 0
        assert row["metrics"]["verifier_ns"] <= row["metrics"]["elapsed_ns"]
    pairs = analyze.analyze(document)["paired_baseline_comparisons"]
    assert len(pairs) == FRONTIERS
    assert all(VERIFIER_COST_METRIC in row["cost_differences"] for row in pairs)
    admitted = audit.audit(
        relative,
        options=audit.AuditOptions(
            replay_candidates=True,
            require_source_commit_object=True,
        ),
    )
    assert admitted["target_sources_replayed"] == ROWS
    assert admitted["source_commit_object_verified"] is True
    assert admitted["evidence_preflight"]["raw_rows_matched"] == ROWS


@pytest.mark.parametrize(
    "tamper", ["missing", ZERO_TAMPER, LEGACY_TAMPER, EXCESS_TAMPER]
)
def test_static_audit_rejects_missing_forged_or_unmeasured_verifier_cost(
    timed_forward: tuple[Path, dict[str, Any], str],
    tamper: str,
) -> None:
    """A metric claim cannot move between new and old verifier protocols."""
    directory, document, relative = timed_forward
    forged = copy.deepcopy(document)
    if tamper == LEGACY_TAMPER:
        forged["study"]["id"] = producer.FORWARD_STUDY
        forged["study"]["objectives"].remove("verifier_ns")
    elif tamper == ZERO_TAMPER:
        forged["observations"][0]["metrics"]["verifier_ns"] = 0
    elif tamper == EXCESS_TAMPER:
        row = forged["observations"][0]
        row["metrics"]["verifier_ns"] = row["metrics"]["elapsed_ns"] + 1
    else:
        del forged["observations"][0]["metrics"]["verifier_ns"]
    if tamper == EXCESS_TAMPER:
        with pytest.raises(audit.TargetEchoAuditError, match="verifier timing"):
            audit._check_verifier_cost_claims(forged)
    _save(directory, forged)
    with pytest.raises(audit.TargetEchoAuditError, match=r"verifier|objective|metric"):
        audit.audit(relative)


def test_forward_jump_and_walk_have_equal_code_size_but_distinct_work(
    forward_skip: tuple[Path, dict[str, Any], str],
) -> None:
    """Actual retained programs expose an independently replayable tradeoff."""
    directory, document, relative = forward_skip
    assert document["study"]["id"] == producer.FORWARD_STUDY
    assert document["study"]["baseline"] == producer.WALK
    assert document["study"]["objectives"] == [
        "elapsed_ns",
        ARTIFACT_BYTES,
        "runtime_steps",
    ]
    assert len(document["observations"]) == ROWS
    for pairs in (1, 4, 16, 64):
        level = {
            row["algorithm"]: row
            for row in document["observations"]
            if row["case"]["difficulty"] == pairs
        }
        walked, skipped = level[producer.WALK], level[producer.SKIP]
        assert walked["outcome"] == analyze.VERIFIED
        assert skipped["outcome"] == analyze.VERIFIED
        assert walked["metrics"][ARTIFACT_BYTES] == skipped["metrics"][ARTIFACT_BYTES]
        assert walked["metrics"]["runtime_steps"] == walked["metrics"][ARTIFACT_BYTES]
        assert (
            skipped["metrics"]["runtime_steps"] + producer.SKIPPED_NOOPS
            == (walked["metrics"]["runtime_steps"])
        )
        source = _first_source(directory, {"observations": [skipped]})
        data = source.read_bytes()
        assert data[0] + 1 == producer.SKIPPED_NOOPS + 1
        assert len(data) == skipped["metrics"][ARTIFACT_BYTES]
        assert all(
            audit._decoded_instruction(data[pos], pos) == ord("o")
            for pos in range(1, producer.SKIPPED_NOOPS + 1)
        )
    checked = audit.audit(relative)
    assert checked["verified_target_sources_checked"] == ROWS
    replay = audit.audit(
        relative,
        options=audit.AuditOptions(
            replay_candidates=True,
            require_source_commit_object=True,
        ),
    )
    assert replay["target_sources_replayed"] == ROWS
    assert replay["source_commit_object_verified"] is True


@pytest.mark.skipif(
    os.name != POSIX_PLATFORM,
    reason="bounded guest-input runner requires POSIX",
)
def test_forward_jump_and_walk_accept_every_possible_input_byte(
    forward_skip: tuple[Path, dict[str, Any], str],
) -> None:
    """Four independent 64-byte windows cover all 256 actual input values."""
    directory, document, _ = forward_skip
    for algorithm in (producer.WALK, producer.SKIP):
        row = next(
            row
            for row in document["observations"]
            if row["algorithm"] == algorithm
            and row["case"]["difficulty"] == INPUT_WINDOW_BYTES
        )
        source = _first_source(directory, {"observations": [row]})
        expected_stderr = (
            b"malbolge-steps-v1:"
            + str(row["metrics"][RUNTIME_STEPS]).encode("ascii")
            + b"\n"
        )
        for start in range(0, ALL_BYTE_VALUES, INPUT_WINDOW_BYTES):
            payload = bytes(range(start, start + INPUT_WINDOW_BYTES))
            result = target_process.invoke_with_input(
                [
                    str(producer.DEFAULT_RUNNER),
                    str(source),
                    "--input-stdin",
                    "--report-steps",
                ],
                payload,
                timeout_seconds=producer.TIMEOUT_SECONDS,
            )
            assert result.returncode == 0
            assert result.stdout == payload + bytes([producer.CLASSIC_EOF_BYTE])
            assert result.stderr == expected_stderr


class _FalseReplayBytes(bytes):  # ruff: ignore[subclass-builtin]
    """Pretend that unrelated binary output matches the expected oracle."""

    def __eq__(self, other: object) -> bool:
        del other
        return True

    def __ne__(self, other: object) -> bool:
        del other
        return False


@pytest.mark.parametrize(
    ("field", "forged"),
    [
        ("status", False),
        ("status", 0.0),
        ("stdout", _FalseReplayBytes(b"not the guest payload")),
        ("stderr", _FalseReplayBytes(b"not the step receipt")),
        ("args", object()),
    ],
    ids=[
        "boolean-status",
        "float-status",
        "false-stdout",
        "false-stderr",
        "foreign-args",
    ],
)
def test_direct_forward_replay_rejects_forged_completed_process(
    field: str, forged: object
) -> None:
    """A foreign VM receipt cannot manufacture verified output or steps."""
    payload = b"\x00\xff"
    steps = 9
    values: dict[str, object] = {
        "args": ["runner", "program.malbolge"],
        "status": 0,
        "stdout": payload + bytes([producer.CLASSIC_EOF_BYTE]),
        "stderr": audit.STEPS_REPORT_PREFIX + b"9\n",
    }
    values[field] = forged
    receipt = sp.CompletedProcess(
        cast("Any", values["args"]),
        cast("Any", values["status"]),
        cast("Any", values["stdout"]),
        cast("Any", values["stderr"]),
    )
    with pytest.raises(audit.TargetEchoAuditError, match="replay.*receipt"):
        audit._check_forward_replay_result(
            cast("sp.CompletedProcess[bytes]", receipt), payload, steps
        )


@pytest.mark.parametrize(
    ("family", "steps"),
    [
        ("bounded-classic-eof-echo", False),
        ("bounded-classic-eof-echo", True),
        (audit.PATTERNED_FAMILY, False),
        (audit.PATTERNED_FAMILY, True),
    ],
)
@pytest.mark.parametrize("forgery", ["swapped-runner", "mutated-command"])
def test_retained_vm_replay_binds_native_child_to_invocation(
    monkeypatch: pytest.MonkeyPatch,
    family: str,
    steps: bool,
    forgery: str,
) -> None:
    """A native success receipt from another command cannot certify replay."""
    runner = Path("/tmp/test-runner")
    source = Path("/tmp/test-candidate.malbolge")
    row: dict[str, Any] = {
        "case": {"difficulty": 1, "family": family},
        "metrics": {audit.RUNTIME_STEPS: 2} if steps else {},
    }

    def forged(
        command: list[str], *_args: object, **_kwargs: object
    ) -> sp.CompletedProcess[bytes]:
        if forgery == "mutated-command":
            command[0] = "/foreign/runner"
            receipt = command
        else:
            receipt = ["/foreign/runner", *command[1:]]
        return sp.CompletedProcess(receipt, 0, b"", b"")

    monkeypatch.setattr(
        audit, "_invoke_runner", lambda vm, path: forged([str(vm), str(path)])
    )
    monkeypatch.setattr(audit, "_invoke_runner_command", forged)
    monkeypatch.setattr(audit.target_process, "invoke_with_input", forged)
    monkeypatch.setattr(audit.target_process, "invoke_with_input_limited", forged)
    with pytest.raises(audit.TargetEchoAuditError, match="replay.*command"):
        audit._replay_execution(row, runner, source)


@pytest.mark.parametrize(
    ("family", "steps"),
    [
        ("bounded-classic-eof-echo", False),
        ("bounded-classic-eof-echo", True),
        (audit.PATTERNED_FAMILY, False),
        (audit.PATTERNED_FAMILY, True),
    ],
)
def test_retained_vm_replay_accepts_matching_native_child_command(
    monkeypatch: pytest.MonkeyPatch, family: str, steps: bool
) -> None:
    """The expected command preserves both classic replay input protocols."""
    runner = Path("/tmp/test-runner")
    source = Path("/tmp/test-candidate.malbolge")
    row: dict[str, Any] = {
        "case": {"difficulty": 1, "family": family},
        "metrics": {audit.RUNTIME_STEPS: 2} if steps else {},
    }

    def native(
        command: list[str], *_args: object, **_kwargs: object
    ) -> sp.CompletedProcess[bytes]:
        return sp.CompletedProcess(command, 0, b"", b"")

    monkeypatch.setattr(
        audit, "_invoke_runner", lambda vm, path: native([str(vm), str(path)])
    )
    monkeypatch.setattr(audit, "_invoke_runner_command", native)
    monkeypatch.setattr(audit.target_process, "invoke_with_input", native)
    monkeypatch.setattr(audit.target_process, "invoke_with_input_limited", native)
    result, _ = audit._replay_execution(row, runner, source)
    assert result.args[0] == str(runner)
    assert result.args[1] == str(source)
    assert ("--report-steps" in result.args) is steps
    assert ("--input-stdin" in result.args) is (family == audit.PATTERNED_FAMILY)


@pytest.mark.parametrize(
    "forgery", ["swapped-runner", "mutated-command", "measured-suffix"]
)
def test_direct_forward_vm_replay_binds_native_child_to_invocation(
    monkeypatch: pytest.MonkeyPatch, forgery: str
) -> None:
    """Even a valid byte/step oracle cannot authorize another VM invocation."""
    payload = b"\x00\xff"
    steps = 9
    measured = forgery == "measured-suffix"

    def forged(
        command: list[str],
        _input: bytes,
        *,
        mode: tuple[bool, bool],
        raw_rss: list[bytes] | None = None,
    ) -> tuple[sp.CompletedProcess[bytes], int | None]:
        del mode, raw_rss
        if forgery == "mutated-command":
            command[0] = "/foreign/runner"
            receipt = command
        elif measured:
            receipt = [
                "/usr/bin/time",
                "--",
                "/usr/bin/prlimit",
                "--",
                "/foreign/runner",
                *command[1:],
            ]
        else:
            receipt = ["/foreign/runner", *command[1:]]
        return (
            sp.CompletedProcess(
                receipt,
                0,
                payload + bytes([producer.CLASSIC_EOF_BYTE]),
                audit.STEPS_REPORT_PREFIX + b"9\n",
            ),
            4096 if measured else None,
        )

    monkeypatch.setattr(audit, "_run_forward_guest", forged)
    with pytest.raises(audit.TargetEchoAuditError, match="replay.*command"):
        audit._replay_forward_result(
            (Path("/tmp/test-runner"), Path("/tmp/test-candidate.malbolge")),
            payload,
            steps=steps,
            options=(measured, measured, None),
        )


def test_direct_forward_vm_replay_accepts_measured_wrapper_command_suffix(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """GNU-time/prlimit measured replies still bind the target VM argv."""
    payload = b"\x00\xff"

    def native(
        command: list[str],
        _input: bytes,
        *,
        mode: tuple[bool, bool],
        raw_rss: list[bytes] | None = None,
    ) -> tuple[sp.CompletedProcess[bytes], int]:
        del mode, raw_rss
        receipt = ["/usr/bin/time", "--", "/usr/bin/prlimit", "--", *command]
        return (
            sp.CompletedProcess(
                receipt,
                0,
                payload + bytes([producer.CLASSIC_EOF_BYTE]),
                audit.STEPS_REPORT_PREFIX + b"9\n",
            ),
            4096,
        )

    monkeypatch.setattr(audit, "_run_forward_guest", native)
    assert (
        audit._replay_forward_result(
            (Path("/tmp/test-runner"), Path("/tmp/test-candidate.malbolge")),
            payload,
            steps=9,
            options=(True, True, None),
        )
        == 4096
    )


def test_direct_forward_replay_preserves_native_completed_process() -> None:
    """An ordinary exact subprocess result still verifies the fixed oracle."""
    payload = b"\x00\xff"
    receipt = sp.CompletedProcess(
        ["runner", "program.malbolge"],
        0,
        payload + bytes([producer.CLASSIC_EOF_BYTE]),
        audit.STEPS_REPORT_PREFIX + b"9\n",
    )
    audit._check_forward_replay_result(receipt, payload, 9)


@pytest.mark.parametrize(
    ("field", "forged"),
    [
        ("status", False),
        ("stdout", _FalseReplayBytes(b"not the guest payload")),
        ("stderr", _FalseReplayBytes(b"not the step receipt")),
    ],
    ids=["boolean-status", "false-stdout", "false-stderr"],
)
def test_retained_vm_replay_rejects_forged_completed_process(
    field: str, forged: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The general replay must admit native runner results before comparison."""
    expected = b"oracle bytes"
    metrics = {audit.RUNTIME_STEPS: 9}
    values: dict[str, object] = {
        "status": 0,
        "stdout": expected,
        "stderr": audit.STEPS_REPORT_PREFIX + b"9\n",
    }
    values[field] = forged
    receipt = sp.CompletedProcess(
        ["runner", "program.malbolge"],
        cast("Any", values["status"]),
        cast("Any", values["stdout"]),
        cast("Any", values["stderr"]),
    )
    monkeypatch.setattr(
        audit, "_replay_execution", lambda *_args, **_kwargs: (receipt, expected)
    )
    monkeypatch.setattr(
        audit, "_native_regular_bytes", lambda *_args, **_kwargs: b"source"
    )
    monkeypatch.setattr(audit, "_source_sha256", lambda _raw: "expected digest")
    with pytest.raises(audit.TargetEchoAuditError, match="replay.*receipt"):
        audit._replay_one(
            {"metrics": metrics},
            "candidate.malbolge",
            "expected digest",
            replay_tool=(Path("runner"), False),
        )


def test_retained_vm_replay_rejects_forged_expected_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An untrusted expected-output comparison cannot certify a replay."""
    receipt = sp.CompletedProcess(
        ["runner", "program.malbolge"], 0, b"native oracle", b""
    )
    monkeypatch.setattr(
        audit,
        "_replay_execution",
        lambda *_args, **_kwargs: (receipt, _FalseReplayBytes(b"false oracle")),
    )
    monkeypatch.setattr(
        audit, "_native_regular_bytes", lambda *_args, **_kwargs: b"source"
    )
    monkeypatch.setattr(audit, "_source_sha256", lambda _raw: "expected digest")
    with pytest.raises(audit.TargetEchoAuditError, match="expected output receipt"):
        audit._replay_one(
            {"metrics": {}},
            "candidate.malbolge",
            "expected digest",
            replay_tool=(Path("runner"), False),
        )


def test_forward_jump_paired_costs_retain_runtime_work_advantage(
    forward_skip: tuple[Path, dict[str, Any], str],
) -> None:
    """Matched cost curves preserve code size but exact VM work savings."""
    _, document, _ = forward_skip
    paired = analyze.analyze(document)["paired_baseline_comparisons"]
    assert len(paired) == FRONTIER_LEVELS_FORWARD
    for comparison in paired:
        assert comparison["baseline"] == producer.WALK
        assert comparison["algorithm"] == producer.SKIP
        assert comparison["outcomes"]["both_verified"] == 1
        assert comparison["cost_differences"][ARTIFACT_BYTES][
            "median_candidate_minus_baseline"
        ] == [0, 1]
        assert comparison["cost_differences"][RUNTIME_STEPS][
            "median_candidate_minus_baseline"
        ] == [-EXPECTED_GUEST_SAVINGS, 1]


@pytest.mark.parametrize(
    "corruption", [JUMP_CORRUPTION, SKIPPED_CORRUPTION, REACHABLE_CORRUPTION]
)
def test_forward_skipped_source_tampering_fails_after_valid_raw_links(
    forward_skip: tuple[Path, dict[str, Any], str],
    corruption: str,
) -> None:
    """A same-length graphical source forgery cannot pass source admission."""
    directory, document, relative = forward_skip
    skip_row = next(
        row for row in document["observations"] if row["algorithm"] == producer.SKIP
    )
    source = _first_source(directory, {"observations": [skip_row]})
    forged = bytearray(source.read_bytes())
    if corruption == JUMP_CORRUPTION:
        forged[0] += 1
    else:
        index = (
            producer.SKIPPED_NOOPS // 2
            if corruption == SKIPPED_CORRUPTION
            else producer.SKIPPED_NOOPS + 1
        )
        forged[index] = (
            INVALID_SOURCE if forged[index] != INVALID_SOURCE else SECOND_INVALID_SOURCE
        )
    source.write_bytes(forged)
    _recheck_generic(document)
    with pytest.raises(
        audit.TargetEchoAuditError,
        match=r"jump target|source instruction",
    ):
        audit.audit(relative)


def test_forward_jump_forged_step_savings_rejected_by_static_oracle(
    forward_skip: tuple[Path, dict[str, Any], str],
) -> None:
    """Changed saved VM work cannot get a smaller Pareto cost for free."""
    directory, document, relative = forward_skip
    altered = copy.deepcopy(document)
    jump_row = next(
        row for row in altered["observations"] if row["algorithm"] == producer.SKIP
    )
    jump_row["metrics"]["runtime_steps"] -= 1
    _save(directory, altered)
    with pytest.raises(audit.TargetEchoAuditError, match="runtime step claim"):
        audit.audit(relative)


def test_counted_vm_study_has_three_actual_costs_and_replay(
    counted_study: tuple[Path, dict[str, Any], str],
) -> None:
    """Both input modes report and independently replay exact VM step counts."""
    _, document, relative = counted_study
    assert document["study"]["id"] in {
        producer.EOF_STEPS_STUDY,
        producer.PATTERNED_STEPS_STUDY,
    }
    assert document["study"]["objectives"] == [
        "elapsed_ns",
        ARTIFACT_BYTES,
        "runtime_steps",
    ]
    assert all(row["outcome"] == analyze.VERIFIED for row in document["observations"])
    assert all(
        row["metrics"]["runtime_steps"] == row["metrics"][ARTIFACT_BYTES]
        for row in document["observations"]
    )
    offline = audit.audit(relative)
    assert offline["verified_target_sources_checked"] == ROWS
    replay = audit.audit(
        relative,
        options=audit.AuditOptions(
            replay_candidates=True,
            require_source_commit_object=True,
        ),
    )
    assert replay["target_sources_replayed"] == ROWS
    assert replay["source_commit_object_verified"] is True
    assert len(replay["pareto_frontiers"]) == FRONTIERS


def test_forged_vm_steps_fail_independent_static_admission(
    counted_study: tuple[Path, dict[str, Any], str],
) -> None:
    """A false step counter is not authorized by a plausible study JSON."""
    directory, document, relative = counted_study
    forged = copy.deepcopy(document)
    forged["observations"][0]["metrics"]["runtime_steps"] += 1
    _save(directory, forged)
    with pytest.raises(audit.TargetEchoAuditError, match="runtime step claim"):
        audit.audit(relative)


def test_replay_rejects_changed_vm_receipt_with_correct_guest_stdout(
    counted_study: tuple[Path, dict[str, Any], str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A replayed program must preserve full stderr counter, not just stdout."""
    _, _, relative = counted_study
    original = audit._replay_execution

    def altered(
        row: dict[str, Any], runner: Path, source: Path
    ) -> tuple[sp.CompletedProcess[bytes], bytes]:
        outcome, expected = original(row, runner, source)
        assert outcome.stdout == expected
        return (
            sp.CompletedProcess(
                outcome.args,
                outcome.returncode,
                outcome.stdout,
                b"malbolge-steps-v1:0\n",
            ),
            expected,
        )

    monkeypatch.setattr(audit, "_replay_execution", altered)
    with pytest.raises(audit.TargetEchoAuditError, match="step receipt"):
        audit.audit(relative, options=audit.AuditOptions(replay_candidates=True))


def test_patterned_source_audit_replays_real_input_and_eof(
    patterned: tuple[Path, dict[str, Any], str],
) -> None:
    """Opt-in replay checks the whole patterned byte vector and final EOF."""
    _, study, relative = patterned
    assert study["study"]["id"] == producer.PATTERNED_STUDY
    checked = audit.audit(relative)
    assert checked["verified_target_sources_checked"] == ROWS
    assert checked["target_sources_replayed"] == 0
    replay = audit.audit(
        relative,
        options=audit.AuditOptions(
            replay_candidates=True,
            require_source_commit_object=True,
        ),
    )
    assert replay["target_sources_replayed"] == ROWS
    assert replay["source_commit_object_verified"] is True
    assert replay["source_sha256"] == checked["source_sha256"]
    assert len(replay["pareto_frontiers"]) == FRONTIERS


def test_patterned_claim_switched_to_eof_fails_before_publication(
    patterned: tuple[Path, dict[str, Any], str],
) -> None:
    """A synthetic EOF identity cannot replace a real patterned-input claim."""
    directory, document, relative = patterned
    modified = copy.deepcopy(document)
    modified["study"]["id"] = "classic-eof-echo-geometry-v1"
    _save(directory, modified)
    _recheck_generic(modified)
    with pytest.raises(audit.TargetEchoAuditError, match="producer policy"):
        audit.audit(relative)


def test_patterned_same_length_source_replacement_is_rejected(
    patterned: tuple[Path, dict[str, Any], str],
) -> None:
    """Preserving size and receipts cannot change decoded guest semantics."""
    directory, document, relative = patterned
    source = _first_source(directory, document)
    altered = bytearray(source.read_bytes())
    altered[0] = INVALID_SOURCE if altered[0] != INVALID_SOURCE else 34
    source.write_bytes(altered)
    _recheck_generic(document)
    with pytest.raises(audit.TargetEchoAuditError, match="source instruction"):
        audit.audit(relative)


def test_real_retained_target_study_passes_offline_and_replay(
    retained: tuple[Path, dict[str, Any], str],
) -> None:
    """Static independent instruction decode precedes a real VM rerun."""
    directory, study, relative = retained
    checked = audit.audit(relative)
    assert (
        checked["retained_study_sha256"]
        == sha256((directory / "study.json").read_bytes()).hexdigest()
    )
    assert checked["verified_target_sources_checked"] == ROWS
    assert checked["target_sources_replayed"] == 0
    assert len(checked["source_sha256"]) == ROWS
    assert len(checked["pareto_frontiers"]) == FRONTIERS
    assert checked["evidence_preflight"]["raw_rows_matched"] == ROWS
    assert checked["reported_failed_trials_not_replayed"] == 0
    assert NOT_AUTHENTICATED in checked["scope"]
    replay = audit.audit(relative, options=audit.AuditOptions(replay_candidates=True))
    assert replay["target_sources_replayed"] == REPLAYED
    assert replay["source_sha256"] == checked["source_sha256"]
    assert replay["capacity_curve"] == checked["capacity_curve"]
    assert study["study"]["stage"].startswith("measured-classic")


@pytest.mark.skipif(
    not producer.DEFAULT_EMITTER.is_file() or not producer.DEFAULT_RUNNER.is_file(),
    reason="repository Malbolge binaries are not built",
)
def test_real_64_pair_echo_crosses_two_classic_decode_phases() -> None:
    """The fixed target oracle remains exact across code positions above 94."""
    with tempfile.TemporaryDirectory(
        dir=producer._TEMP,
        prefix="arena-target-phase-tools-",
    ) as tools:
        emitter = Path(tools) / "malbolge_layout"
        runner = Path(tools) / "malbolge"
        shutil.copy2(producer.DEFAULT_EMITTER, emitter)
        shutil.copy2(producer.DEFAULT_RUNNER, runner)
        directory, document = producer.run_study(
            producer.StudyPlan((producer.MAX_PAIRS,), 1),
            emitter=emitter,
            runner=runner,
        )
        try:
            relative = (directory / "study.json").relative_to(producer._ROOT)
            checked = audit.audit(
                relative.as_posix(),
                options=audit.AuditOptions(
                    replay_candidates=True,
                    emitter=emitter,
                    runner=runner,
                ),
            )
            assert checked["verified_target_sources_checked"] == MAX_PHASE_TRIALS
            assert checked["target_sources_replayed"] == MAX_PHASE_TRIALS
            assert {
                row["algorithm"]: row["metrics"][ARTIFACT_BYTES]
                for row in document["observations"]
            } == {producer.BASELINE: 129, producer.CANDIDATE: 193}
        finally:
            shutil.rmtree(directory)


def test_same_length_source_rewrite_passes_generic_but_fails_target_decode(
    retained: tuple[Path, dict[str, Any], str],
) -> None:
    """Self-consistent metrics do not establish original target instructions."""
    directory, document, relative = retained
    path = _first_source(directory, document)
    source = bytearray(path.read_bytes())
    source[0] = INVALID_SOURCE if source[0] != INVALID_SOURCE else INVALID_SOURCE + 1
    path.write_bytes(source)
    _recheck_generic(document)
    with pytest.raises(audit.TargetEchoAuditError, match="source instruction"):
        audit.audit(relative)


def test_missing_verified_source_is_rejected(
    retained: tuple[Path, dict[str, Any], str],
) -> None:
    """A reported verified trial must retain its actual guest source."""
    directory, document, relative = retained
    _first_source(directory, document).unlink()
    with pytest.raises(audit.TargetEchoAuditError, match=r"must be|No such file"):
        audit.audit(relative)


@pytest.mark.parametrize("tamper", ["extra", "link"])
def test_extra_or_linked_candidate_is_rejected(
    retained: tuple[Path, dict[str, Any], str],
    tamper: str,
) -> None:
    """Candidate directory admission checks its complete file inventory."""
    directory, document, relative = retained
    existing = _first_source(directory, document)
    if tamper == EXTRA_ARTIFACT:
        (directory / "candidates" / "foreign.malbolge").write_bytes(
            existing.read_bytes()
        )
    else:
        other = next(
            path for path in (directory / "candidates").iterdir() if path != existing
        )
        existing.unlink()
        existing.symlink_to(other)
    with pytest.raises(audit.TargetEchoAuditError, match=r"unexpected|symlink"):
        audit.audit(relative)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("question", "Did the emitter run at all?"),
        ("hypothesis", "All algorithms behave equally"),
        ("stage", "host-c-reference-not-malbolge"),
        ("rejection_observation", "No difference is ever meaningful"),
    ],
)
def test_foreign_study_claims_pass_generic_but_fail_producer_audit(
    retained: tuple[Path, dict[str, Any], str],
    field: str,
    value: str,
) -> None:
    """Arbitrary research claims cannot impersonate a fixed real producer."""
    directory, document, relative = retained
    modified = copy.deepcopy(document)
    modified["study"][field] = value
    _save(directory, modified)
    _recheck_generic(modified)
    with pytest.raises(audit.TargetEchoAuditError, match="producer policy"):
        audit.audit(relative)


def test_foreign_manifest_provenance_is_rejected(
    retained: tuple[Path, dict[str, Any], str],
) -> None:
    """Generic valid run links cannot claim foreign implementation as native."""
    _, document, relative = retained
    row = document["observations"][0]
    manifest = producer._ROOT / row["experiment_manifest"]
    raw = manifest.read_text(encoding="utf-8")
    assert REAL_PROFILE_PROVENANCE in raw
    manifest.write_text(
        raw.replace(REAL_PROFILE_PROVENANCE, BAD_PROFILE_PROVENANCE),
        encoding="utf-8",
    )
    _recheck_generic(document)
    with pytest.raises(audit.TargetEchoAuditError, match="foreign producer"):
        audit.audit(relative)


def test_unbalanced_population_fails_despite_generic_cohort_agreement(
    retained: tuple[Path, dict[str, Any], str],
) -> None:
    """Each level must retain one identical consecutive repetition plan."""
    directory, document, relative = retained
    modified = copy.deepcopy(document)
    modified["observations"] = [
        row
        for row in modified["observations"]
        if not (row["case"]["difficulty"] == DIFFICULTY and row["trial"] == 1)
    ]
    _save(directory, modified)
    _recheck_generic(modified)
    with pytest.raises(audit.TargetEchoAuditError, match="complete matched"):
        audit.audit(relative)


def test_real_study_profile_binary_digest_required_for_vm_replay(
    retained: tuple[Path, dict[str, Any], str],
) -> None:
    """Replaying with a new binary cannot claim original toolchain identity."""
    directory, document, relative = retained
    modified = copy.deepcopy(document)
    forged = "local-compiler-vm-sha256:" + "f" * 64
    modified["study"]["toolchain"] = forged
    for row in modified["observations"]:
        manifest = producer._ROOT / row["experiment_manifest"]
        original = manifest.read_text(encoding="utf-8")
        manifest.write_text(
            original.replace(document["study"]["toolchain"], forged),
            encoding="utf-8",
        )
    _save(directory, modified)
    _recheck_generic(modified)
    assert audit.audit(relative)["verified_target_sources_checked"] == ROWS
    with pytest.raises(audit.TargetEchoAuditError, match="toolchain differs"):
        audit.audit(relative, options=audit.AuditOptions(replay_candidates=True))


@pytest.mark.parametrize(
    "receipt",
    ["", "relative/git", "bad\0path", b"/usr/bin/git", False, 7],
    ids=["empty", "relative", "nul", "bytes", "boolean", "integer"],
)
def test_target_audit_git_object_rejects_malformed_resolver_receipts(
    monkeypatch: pytest.MonkeyPatch,
    receipt: object,
) -> None:
    """An invalid Git path never reaches source-object subprocess execution."""
    monkeypatch.setattr(
        audit.shutil, "which", lambda *_args, **_kwargs: cast("str", receipt)
    )

    def forbidden(*_args: object, **_kwargs: object) -> None:
        pytest.fail("unadmitted audit Git path reached process execution")

    monkeypatch.setattr(audit.sp, "run", forbidden)
    with pytest.raises(audit.TargetEchoAuditError, match="Git"):
        audit._require_git_commit("a" * 40)


@pytest.mark.parametrize("kind", ["missing", "directory", "nonexecutable", "symlink"])
def test_target_audit_git_object_requires_physical_executable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
) -> None:
    """The source-object resolver cannot return an unexecutable or linked file."""
    git = tmp_path / "git"
    if kind == "directory":
        git.mkdir()
    elif kind == "nonexecutable":
        _ = git.write_bytes(b"not executable")
        git.chmod(0o600)
    elif kind == "symlink":
        target = tmp_path / "real-git"
        _ = target.write_bytes(b"#!/bin/sh\nexit 0\n")
        target.chmod(0o700)
        git.symlink_to(target)
    monkeypatch.setattr(audit.shutil, "which", lambda *_args, **_kwargs: str(git))

    def forbidden(*_args: object, **_kwargs: object) -> None:
        pytest.fail("unsafe audit Git path reached process execution")

    monkeypatch.setattr(audit.sp, "run", forbidden)
    with pytest.raises(audit.TargetEchoAuditError, match="Git"):
        audit._require_git_commit("a" * 40)


@pytest.mark.parametrize(
    "failure", [OSError, ValueError, RuntimeError, TypeError, AttributeError]
)
def test_target_audit_git_object_types_resolver_failures(
    monkeypatch: pytest.MonkeyPatch,
    failure: type[Exception],
) -> None:
    """Resolver faults are typed audit failures with the original cause."""

    def broken(*_args: object, **_kwargs: object) -> None:
        raise failure("host Git resolver unavailable")

    monkeypatch.setattr(audit.shutil, "which", broken)
    with pytest.raises(audit.TargetEchoAuditError, match="Git") as caught:
        audit._require_git_commit("a" * 40)
    assert isinstance(caught.value.__cause__, failure)


@pytest.mark.parametrize(
    "failure", [ValueError, RuntimeError, TypeError, AttributeError]
)
def test_target_audit_git_object_types_transport_failures(
    monkeypatch: pytest.MonkeyPatch,
    failure: type[Exception],
) -> None:
    """Subprocess transport faults cannot leak native host exceptions."""

    def broken(*_args: object, **_kwargs: object) -> None:
        raise failure("Git execution unavailable")

    monkeypatch.setattr(audit.sp, "run", broken)
    with pytest.raises(audit.TargetEchoAuditError, match="Git") as caught:
        audit._require_git_commit("a" * 40)
    assert isinstance(caught.value.__cause__, failure)


@pytest.mark.parametrize(
    ("status", "stdout"),
    [(0, None), (0, "commit"), (1, b"commit"), (True, b"commit"), (0, b"tree")],
    ids=["missing", "text", "failed", "bool-status", "wrong-object"],
)
def test_target_audit_git_object_rejects_noncanonical_process_receipt(
    monkeypatch: pytest.MonkeyPatch,
    status: object,
    stdout: object,
) -> None:
    """Only a successful binary commit-object response passes provenance."""
    monkeypatch.setattr(
        audit.sp,
        "run",
        lambda *_args, **_kwargs: sp.CompletedProcess(
            ["git"], cast("int", status), cast("bytes", stdout), b""
        ),
    )
    with pytest.raises(audit.TargetEchoAuditError, match="Git commit object"):
        audit._require_git_commit("a" * 40)


class _HostileGitCommand(list[str]):
    """Hostile returned arguments cannot define equality for source identity."""

    def __eq__(self, other: object) -> bool:
        raise AssertionError("foreign target Git command equality hook executed")


@pytest.mark.parametrize(
    "argument_kind", ["other", "tuple", "hostile", "string", "missing"]
)
def test_target_audit_git_rejects_forged_child_command_receipt(
    monkeypatch: pytest.MonkeyPatch, argument_kind: str
) -> None:
    """The actual launched local Git command must own the object-type response."""

    def forged(command: list[str], **_kwargs: object) -> object:
        returned: object = (
            ["other-git", "cat-file", "-t", "a" * 40]
            if argument_kind == "other"
            else tuple(command)
            if argument_kind == "tuple"
            else _HostileGitCommand(command)
            if argument_kind == "hostile"
            else "git cat-file"
            if argument_kind == "string"
            else None
        )
        return sp.CompletedProcess(cast("Any", returned), 0, b"commit\n", b"")

    monkeypatch.setattr(audit.sp, "run", forged)
    with pytest.raises(audit.TargetEchoAuditError, match="Git commit object"):
        audit._require_git_commit("a" * 40)


def test_target_audit_git_rejects_copied_successful_command_receipt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A different argv list cannot attest this specific Git child invocation."""

    def forged(command: list[str], **_kwargs: object) -> object:
        return sp.CompletedProcess(command.copy(), 0, b"commit\n", b"")

    monkeypatch.setattr(audit.sp, "run", forged)
    with pytest.raises(audit.TargetEchoAuditError, match="Git commit object"):
        audit._require_git_commit("a" * 40)


@pytest.mark.parametrize(
    "stdout",
    [b"commit", b" commit\n", b"commit\n\n", b"commit \n"],
    ids=["missing-newline", "leading-space", "extra-newline", "trailing-space"],
)
def test_target_audit_git_rejects_noncanonical_object_type_line(
    monkeypatch: pytest.MonkeyPatch, stdout: bytes
) -> None:
    """Malformed but strip-equivalent object-type text is not admissible."""

    def forged(command: list[str], **_kwargs: object) -> object:
        return sp.CompletedProcess(command, 0, stdout, b"")

    monkeypatch.setattr(audit.sp, "run", forged)
    with pytest.raises(audit.TargetEchoAuditError, match="Git commit object"):
        audit._require_git_commit("a" * 40)


class _HostileGitStat:
    """A foreign lstat result cannot authorize a Git executable."""

    @property
    def st_mode(self) -> int:
        pytest.fail("foreign Git stat metadata reached field inspection")


def test_target_audit_git_rejects_foreign_lstat_before_field_access(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Git provenance cannot use fabricated executable metadata."""
    git = tmp_path / "git"
    git.write_bytes(b"executable")
    git.chmod(0o700)
    native_lstat = audit.Path.lstat
    monkeypatch.setattr(audit.shutil, "which", lambda *_a, **_kw: str(git))

    def hostile_lstat(path: Path) -> os.stat_result:
        if path == git:
            return cast("os.stat_result", cast("object", _HostileGitStat()))
        return native_lstat(path)

    monkeypatch.setattr(audit.Path, "lstat", hostile_lstat)
    with pytest.raises(audit.TargetEchoAuditError, match="Git"):
        audit._require_git_commit("a" * 40)


@pytest.mark.parametrize("access", [None, 0, 1, "yes", object()])
def test_target_audit_git_requires_native_executable_access_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, access: object
) -> None:
    """A truthy foreign access result is not proof of executable status."""
    git = tmp_path / "git"
    git.write_bytes(b"executable")
    git.chmod(0o700)
    monkeypatch.setattr(audit.shutil, "which", lambda *_a, **_kw: str(git))
    monkeypatch.setattr(audit.os, "access", lambda *_a, **_kw: access)

    def forbidden(*_args: object, **_kwargs: object) -> None:
        pytest.fail("foreign Git access receipt reached subprocess")

    monkeypatch.setattr(audit.sp, "run", forbidden)
    with pytest.raises(audit.TargetEchoAuditError, match="Git"):
        audit._require_git_commit("a" * 40)


class _HostileGitEnvKey(str):
    """A string subclass can forge a GIT_* exclusion check."""

    def startswith(self, *_args: object, **_kwargs: object) -> bool:
        pytest.fail("foreign Git environment key hook executed")


class _HostileGitEnvValue(str):
    """A nonnative process environment value is not admissible."""


@pytest.mark.parametrize("field", ["key", "value"])
def test_target_audit_git_rejects_foreign_environment_before_child(
    monkeypatch: pytest.MonkeyPatch, field: str
) -> None:
    """Foreign Git selectors cannot redirect local object-store admission."""
    if field == "key":
        foreign: dict[str, str] = {_HostileGitEnvKey("GIT_DIR"): "/elsewhere"}
    else:
        foreign = {"PATH": _HostileGitEnvValue("/untrusted")}
    monkeypatch.setattr(audit.os, "environ", foreign)

    def forbidden(*_args: object, **_kwargs: object) -> None:
        pytest.fail("foreign Git environment reached subprocess")

    monkeypatch.setattr(audit.sp, "run", forbidden)
    with pytest.raises(audit.TargetEchoAuditError, match="Git environment"):
        audit._require_git_commit("a" * 40)


@pytest.mark.parametrize("failure_type", [OSError, RuntimeError, ValueError])
def test_target_audit_git_environment_iteration_faults_stay_typed(
    monkeypatch: pytest.MonkeyPatch, failure_type: type[Exception]
) -> None:
    """Environment inspection faults cannot become untyped Git exceptions."""
    fault = failure_type("injected Git environment iteration failure")

    class BrokenEnvironment(dict[str, str]):
        def items(self):  # type: ignore[override]
            raise fault

    monkeypatch.setattr(audit.os, "environ", BrokenEnvironment())
    with pytest.raises(audit.TargetEchoAuditError, match="Git environment") as caught:
        audit._require_git_commit("a" * 40)
    assert caught.value.__cause__ is fault


@pytest.mark.parametrize("stderr", [None, False, 0, "warning", b"warning"])
def test_target_audit_git_requires_exact_empty_binary_stderr_receipt(
    monkeypatch: pytest.MonkeyPatch, stderr: object
) -> None:
    """A success-looking Git stdout cannot hide a noncanonical error channel."""
    monkeypatch.setattr(
        audit.sp,
        "run",
        lambda *_a, **_kw: sp.CompletedProcess(
            ["git"], 0, b"commit\n", cast("bytes", stderr)
        ),
    )
    with pytest.raises(audit.TargetEchoAuditError, match="Git commit object"):
        audit._require_git_commit("a" * 40)


def test_opt_in_git_object_admission_confirms_real_source_revision(
    retained: tuple[Path, dict[str, Any], str],
) -> None:
    """A recorded local commit is independently resolved only on opt-in."""
    _, _, relative = retained
    result = audit.audit(
        relative,
        options=audit.AuditOptions(require_source_commit_object=True),
    )
    assert result["source_commit_object_verified"] is True


@pytest.mark.parametrize("hostile_name", ["GIT_DIR", "GIT_OBJECT_DIRECTORY"])
def test_source_commit_object_lookup_ignores_hostile_git_environment(
    retained: tuple[Path, dict[str, Any], str],
    monkeypatch: pytest.MonkeyPatch,
    hostile_name: str,
) -> None:
    """Ambient Git overrides cannot replace the project's object database."""
    _, _, relative = retained
    forged = producer._TEMP / "absent-arena-git-object-database"
    monkeypatch.setenv(hostile_name, str(forged))
    result = audit.audit(
        relative,
        options=audit.AuditOptions(require_source_commit_object=True),
    )
    assert result["source_commit_object_verified"] is True


def test_source_commit_opt_in_cli_reports_checked_revision(
    retained: tuple[Path, dict[str, Any], str],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Explicit CLI source-object admission has a visible checked result."""
    _, _, relative = retained
    monkeypatch.setattr(
        sys,
        "argv",
        ["target-echo-audit", relative, "--require-source-commit-object"],
    )
    assert audit.main() == 0
    result = json.loads(capsys.readouterr().out)
    assert result["source_commit_object_verified"] is True
    assert result["verified_target_sources_checked"] == ROWS


def test_forged_consistent_git_commit_is_rejected_when_requested(
    retained: tuple[Path, dict[str, Any], str],
) -> None:
    """Consistent invented source revision cannot claim local Git provenance."""
    _, document, relative = retained
    for row in document["observations"]:
        manifest = producer._ROOT / row["experiment_manifest"]
        original = manifest.read_text(encoding="utf-8")
        previous = tomllib.loads(original)["run"]["commit"]
        updated = original.replace(
            f'commit = "{previous}"',
            'commit = "' + "f" * 40 + '"',
        )
        assert updated != original
        manifest.write_text(updated, encoding="utf-8")
    assert audit.audit(relative)["source_commit_object_verified"] is False
    with pytest.raises(audit.TargetEchoAuditError, match="Git commit object"):
        audit.audit(
            relative,
            options=audit.AuditOptions(require_source_commit_object=True),
        )


def test_mutated_retained_source_during_report_is_rejected(
    retained: tuple[Path, dict[str, Any], str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A new source mutation after initial decode cannot enter the report."""
    directory, document, relative = retained
    target = _first_source(directory, document)
    actual_analyze = analyze.analyze

    def mutate_after_decode(study: dict[str, Any]) -> dict[str, Any]:
        contents = bytearray(target.read_bytes())
        contents[0] = (
            INVALID_SOURCE if contents[0] != INVALID_SOURCE else INVALID_SOURCE + 1
        )
        target.write_bytes(contents)
        return actual_analyze(study)

    monkeypatch.setattr(audit.analyze, "analyze", mutate_after_decode)
    with pytest.raises(audit.TargetEchoAuditError, match="changed before report"):
        audit.audit(relative)


@pytest.mark.parametrize("evidence_kind", ["study", "raw", "run"])
def test_retained_evidence_changed_after_preflight_is_rejected(
    retained: tuple[Path, dict[str, Any], str],
    monkeypatch: pytest.MonkeyPatch,
    evidence_kind: str,
) -> None:
    """Source-stable but changed study/run/raw evidence cannot publish."""
    directory, document, relative = retained
    row = document["observations"][0]
    paths = {
        "study": directory / "study.json",
        "raw": producer._ROOT / row["raw_sample"],
        "run": producer._ROOT / row["experiment_manifest"],
    }
    victim = paths[evidence_kind]
    real_analyze = analyze.analyze

    def mutate_after_preflight(study: dict[str, Any]) -> dict[str, Any]:
        victim.write_bytes(victim.read_bytes() + b"\n")
        return real_analyze(study)

    monkeypatch.setattr(audit.analyze, "analyze", mutate_after_preflight)
    with pytest.raises(audit.TargetEchoAuditError, match="changed before report"):
        audit.audit(relative)


@pytest.mark.parametrize(
    "unreported",
    [
        ("runs", "unreported.toml"),
        ("raw", "unreported.csv"),
        ("candidates", "unreported.malbolge"),
    ],
)
def test_late_unreported_evidence_file_is_rejected(
    retained: tuple[Path, dict[str, Any], str],
    monkeypatch: pytest.MonkeyPatch,
    unreported: tuple[str, str],
) -> None:
    """Post-preflight added trial files cannot enter a complete report."""
    directory, _, relative = retained
    folder, name = unreported
    added = directory / folder / name
    real_analyze = analyze.analyze

    def add_after_preflight(study: dict[str, Any]) -> dict[str, Any]:
        added.write_bytes(b"unreported")
        return real_analyze(study)

    monkeypatch.setattr(audit.analyze, "analyze", add_after_preflight)
    with pytest.raises(
        audit.TargetEchoAuditError,
        match=r"missing or unexpected|unexpected candidate",
    ):
        audit.audit(relative)


@pytest.mark.skipif(
    os.name != POSIX_PLATFORM, reason="bounded subprocess requires POSIX"
)
def test_replay_runner_output_overflow_is_typed_failure(
    tmp_path: Path,
) -> None:
    """VM replay cannot buffer an unbounded successful-output impostor."""
    fake_runner = tmp_path / "flooding-vm"
    fake_runner.write_text(f"#!{sys.executable}\nimport os\nos.write(1,b'Z'*8192)\n")
    fake_runner.chmod(0o700)
    with pytest.raises(target_process.TargetProcessError, match="stdout"):
        audit._invoke_runner(fake_runner, tmp_path / "source.malbolge")


def test_injected_mismatched_vm_replay_fails_closed(
    retained: tuple[Path, dict[str, Any], str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Static source acceptance does not allow forged reexecution output."""
    _, _, relative = retained

    def wrong_output(
        runner: Path,
        source: Path,
    ) -> sp.CompletedProcess[bytes]:
        return sp.CompletedProcess(
            [str(runner), str(source)], 0, stdout=b"wrong", stderr=b""
        )

    monkeypatch.setattr(audit, "_invoke_runner", wrong_output)
    with pytest.raises(audit.TargetEchoAuditError, match="VM replay rejected"):
        audit.audit(relative, options=audit.AuditOptions(replay_candidates=True))


@pytest.mark.parametrize(
    "relative",
    [
        "/etc/passwd",
        "study.json",
        ".temp/arena-host-c-study-evil/study.json",
        ".temp/arena-target-echo-../study.json",
        ".temp/arena-target-echo-abc/other.json",
        ".temp/arena-target-echo-a/b/study.json",
    ],
)
def test_noncanonical_study_path_never_triggers_audit(relative: str) -> None:
    """Offline audit accepts only producer-owned generated study directory."""
    with pytest.raises(audit.TargetEchoAuditError, match="target audit"):
        audit.audit(relative)


def test_audit_cli_rejects_bad_path_without_stdout(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Invalid claims never publish a misleading complete JSON report."""
    monkeypatch.setattr(sys, "argv", ["target-audit", "study.json"])
    with pytest.raises(SystemExit, match="2"):
        audit.main()
    output = capsys.readouterr()
    assert not output.out
    assert AUDIT_MESSAGE in output.err


@pytest.mark.parametrize("stage", ["admission", "report"])
@pytest.mark.parametrize("fault_type", [IndexError, RuntimeError, AssertionError])
def test_target_audit_types_unexpected_dependency_faults(
    monkeypatch: pytest.MonkeyPatch,
    stage: str,
    fault_type: type[Exception],
) -> None:
    """An unknown host or parser failure never escapes the public audit type."""

    class HostileFault(fault_type):
        def __str__(self) -> str:
            raise AssertionError("foreign target audit formatter executed")

    failure = HostileFault("untrusted host details")

    def fail(*_args: object, **_kwargs: object) -> None:
        raise failure

    if stage == "admission":
        monkeypatch.setattr(audit, "_admit_study", fail)
    else:
        monkeypatch.setattr(
            audit,
            "_admit_study",
            lambda *_args, **_kwargs: ({"observations": []}, {}, {}, {}, "commit", 0),
        )
        monkeypatch.setattr(audit, "_checked_report", fail)
    with pytest.raises(
        audit.TargetEchoAuditError,
        match="target echo retained study audit failed: HostileFault",
    ) as caught:
        audit.audit(".temp/arena-target-echo-fault/study.json")
    assert caught.value.__cause__ is failure


@pytest.mark.parametrize("fault_type", [IndexError, RuntimeError, AssertionError])
def test_target_audit_cli_types_unexpected_dependency_faults(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    fault_type: type[Exception],
) -> None:
    """An unknown direct audit failure must yield exit two, never JSON."""

    class HostileFault(fault_type):
        def __str__(self) -> str:
            raise AssertionError("foreign target CLI formatter executed")

    failure = HostileFault("untrusted host details")

    def fail(*_args: object, **_kwargs: object) -> None:
        raise failure

    monkeypatch.setattr(audit, "audit", fail)
    monkeypatch.setattr(
        sys, "argv", ["target-audit", ".temp/arena-target-echo-fault/study.json"]
    )
    with pytest.raises(SystemExit) as caught:
        audit.main()
    assert caught.value.code == 2
    output = capsys.readouterr()
    assert not output.out
    assert "HostileFault" in output.err
    assert "untrusted host details" not in output.err


@pytest.mark.parametrize(
    "fault_type",
    [
        analyze.ArenaError,
        evidence.EvidenceError,
        producer.TargetEchoStudyError,
        OSError,
        UnicodeError,
        sp.SubprocessError,
    ],
)
def test_target_audit_never_formats_foreign_dependency_errors(
    monkeypatch: pytest.MonkeyPatch, fault_type: type[Exception]
) -> None:
    """A foreign study-admission error cannot invoke its own formatter."""

    def unsafe_str(self: Exception) -> str:
        del self
        raise AssertionError("foreign target audit dependency formatter executed")

    foreign = type("ForeignTargetAuditFault", (fault_type,), {"__str__": unsafe_str})
    fault = foreign("unsafe target dependency fault")

    def fail_study(*_args: object, **_kwargs: object) -> None:
        raise fault

    monkeypatch.setattr(audit, "_admit_study", fail_study)
    with pytest.raises(
        audit.TargetEchoAuditError, match="target echo retained study audit failed"
    ) as caught:
        audit.audit(".temp/arena-target-echo-foreign/study.json")
    assert caught.value.__cause__ is fault
    assert "ForeignTargetAuditFault" in str(caught.value)


@pytest.mark.parametrize(
    "fault_type", [audit.TargetEchoAuditError, report_output.ReportOutputError]
)
def test_target_audit_cli_never_formats_foreign_errors(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    fault_type: type[Exception],
) -> None:
    """The operator receives exit two even when a typed error has unsafe text."""

    def unsafe_str(self: Exception) -> str:
        del self
        raise AssertionError("foreign target audit CLI formatter executed")

    foreign = type("ForeignTargetAuditCliFault", (fault_type,), {"__str__": unsafe_str})
    fault = foreign("unsafe target CLI fault")

    def fail_audit(*_args: object, **_kwargs: object) -> None:
        raise fault

    monkeypatch.setattr(audit, "audit", fail_audit)
    monkeypatch.setattr(
        audit.sys,
        "argv",
        ["target-audit", ".temp/arena-target-echo-foreign/study.json"],
    )
    with pytest.raises(SystemExit) as caught:
        audit.main()
    assert caught.value.code == 2
    output = capsys.readouterr()
    assert not output.out
    assert "ForeignTargetAuditCliFault" in output.err


def test_target_audit_native_target_process_error_preserves_safe_detail() -> None:
    """Trusted bounded-process rejection keeps a useful native reason."""
    reason = "bounded target child resource controls require prlimit"
    error = target_process.TargetProcessError(reason)
    assert audit._safe_error_detail(error) == reason


def test_target_audit_native_process_error_never_formats_foreign_argument() -> None:
    """A native exception class does not authenticate foreign message values."""

    class HostileArgument:
        def __str__(self) -> str:
            raise AssertionError("foreign target process argument formatter executed")

    error = target_process.TargetProcessError(HostileArgument())
    assert audit._safe_error_detail(error) == "TargetProcessError"


def test_target_audit_native_error_keeps_detail_and_cause(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Exact native admission failures retain actionable diagnostics."""
    fault = evidence.EvidenceError("retained target fingerprint changed")

    def fail_study(*_args: object, **_kwargs: object) -> None:
        raise fault

    monkeypatch.setattr(audit, "_admit_study", fail_study)
    with pytest.raises(
        audit.TargetEchoAuditError, match="retained target fingerprint changed"
    ) as caught:
        audit.audit(".temp/arena-target-echo-native/study.json")
    assert caught.value.__cause__ is fault


@pytest.mark.parametrize(
    "fault_type",
    [
        audit.TargetEchoAuditError,
        report_output.ReportOutputError,
        evidence.EvidenceError,
        OSError,
        UnicodeError,
        sp.SubprocessError,
    ],
)
def test_target_audit_exact_error_does_not_render_foreign_arguments(
    fault_type: type[Exception],
) -> None:
    """An exact trusted exception type does not make its payload safe."""

    class HostileArgument:
        def __str__(self) -> str:
            raise AssertionError("foreign target audit argument formatter executed")

        def __repr__(self) -> str:
            raise AssertionError("foreign target audit argument repr executed")

    fault = fault_type(HostileArgument())
    assert audit._safe_error_detail(fault) == fault_type.__name__


@pytest.mark.parametrize("scope", ["study", "publish"])
def test_target_audit_foreign_native_argument_keeps_status_two(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    scope: str,
) -> None:
    """A foreign argument cannot mask rejected evidence or broken publication."""

    class HostileArgument:
        def __str__(self) -> str:
            raise AssertionError("foreign target audit diagnostic executed")

    fault = (
        OSError(HostileArgument())
        if scope == "study"
        else report_output.ReportOutputError(HostileArgument())
    )

    def reject(*_args: object, **_kwargs: object) -> None:
        raise fault

    if scope == "study":
        monkeypatch.setattr(audit, "_admit_study", reject)
    else:
        monkeypatch.setattr(audit.report_output, "publish", reject)
        monkeypatch.setattr(audit, "audit", lambda *_args, **_kwargs: {})
    monkeypatch.setattr(
        audit.sys,
        "argv",
        ["target-audit", ".temp/arena-target-echo-foreign/study.json"],
    )
    with pytest.raises(SystemExit) as caught:
        audit.main()
    assert caught.value.code == 2
    output = capsys.readouterr()
    assert not output.out
    assert type(fault).__name__ in output.err


class _ForeignAuditStat:
    """A substituted host stat must not dictate audited executable identity."""

    def __getattribute__(self, name: str) -> object:
        if name.startswith("st_"):
            pytest.fail("foreign target audit stat field was accessed")
        return super().__getattribute__(name)


@pytest.mark.parametrize(
    "phase",
    [
        "admit",
        "identity",
        "path-before",
        "path-after",
        "descriptor-open",
        "descriptor-close",
    ],
)
def test_target_audit_requires_native_executable_metadata_before_field_access(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, phase: str
) -> None:
    """An audit cannot trust path, descriptor or helper identity forgeries."""
    emitter = tmp_path / "emitter"
    runner = tmp_path / "runner"
    emitter.write_bytes(b"emitter")
    runner.write_bytes(b"runner")
    foreign = cast("os.stat_result", cast("object", _ForeignAuditStat()))
    if phase == "identity":
        with pytest.raises(audit.TargetEchoAuditError, match="identity"):
            audit._tool_file_identity(foreign)
        return
    real_lstat = Path.lstat
    real_fstat = audit.os.fstat
    path_calls = 0
    descriptor_calls = 0

    def forged_lstat(path: Path) -> os.stat_result:
        nonlocal path_calls
        if path == emitter:
            path_calls += 1
            if (
                phase == "admit"
                or (phase == "path-before" and path_calls == 1)
                or (phase == "path-after" and path_calls == 2)
            ):
                return foreign
        return real_lstat(path)

    def forged_fstat(descriptor: int) -> os.stat_result:
        nonlocal descriptor_calls
        descriptor_calls += 1
        if (phase == "descriptor-open" and descriptor_calls == 1) or (
            phase == "descriptor-close" and descriptor_calls == 2
        ):
            return foreign
        return real_fstat(descriptor)

    monkeypatch.setattr(Path, "lstat", forged_lstat)
    monkeypatch.setattr(audit.os, "fstat", forged_fstat)
    with pytest.raises(audit.TargetEchoAuditError, match="identity|regular"):
        if phase == "admit":
            audit._admit_tool(emitter)
        else:
            audit._tool_identity(emitter, runner)
    if phase == "path-after":
        assert path_calls == 2
    if phase == "descriptor-close":
        assert descriptor_calls == 2


@pytest.mark.parametrize("mutation", ("executable", "operation", "extra"))
def test_audit_git_rejects_mutated_launch_command(
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
        return audit.sp.CompletedProcess(command, 0, stdout=b"commit\n", stderr=b"")

    monkeypatch.setattr(audit.sp, "run", forged)
    with pytest.raises(audit.TargetEchoAuditError, match="local Git commit object"):
        audit._require_git_commit("a" * 40)  # ruff: ignore[private-member-access]
    assert len(launched) == 1
    assert launched[0][1] in ("rev-parse", "cat-file")


def _synthetic_rss_canonicality_inputs() -> tuple[dict[str, Any], dict[str, Any]]:
    identity = {
        "algorithm": "direct",
        "pairs": 1,
        "trial": 0,
        "workload_sha256": "a" * 64,
    }
    document = {
        "schema_version": 1,
        "identity": identity,
        "stages": {stage: 4096 for stage in audit.RSS_STAGE_NAMES},
    }
    row = {
        "algorithm": "direct",
        "case": {"difficulty": 1, "workload_sha256": "a" * 64},
        "trial": 0,
        "metrics": {audit.PEAK_RSS: 4096},
    }
    return document, row


@pytest.mark.parametrize("provider", ("writer", "encoder", "joint"))
def test_rss_receipt_rejects_forged_canonical_json_writer(
    monkeypatch: pytest.MonkeyPatch,
    provider: str,
) -> None:
    """Injected JSON writers cannot validate altered RSS receipt bytes."""
    document, row = _synthetic_rss_canonicality_inputs()
    forged = json.dumps(document, sort_keys=True, indent=2)
    data = (forged + "\n").encode("utf-8")

    class ForgedEncoder:
        def __init__(self, **_kwargs: object) -> None:
            pass

        def encode(self, _document: object) -> str:
            return forged

    def forged_writer(*_args: object, **_kwargs: object) -> str:
        return forged

    with monkeypatch.context() as patch:
        if provider in ("encoder", "joint"):
            patch.setattr(json, "JSONEncoder", ForgedEncoder)
        if provider in ("writer", "joint"):
            patch.setattr(json, "dumps", forged_writer)
        with pytest.raises(
            audit.TargetEchoAuditError,
            match="RSS receipt JSON writer differs from source",
        ):
            audit._validate_rss_stage_bytes(data, row, raw=False)


def test_rss_receipt_rejects_substituted_json_decoder(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unparseable receipt bytes cannot be laundered by public decoders."""
    document, row = _synthetic_rss_canonicality_inputs()
    forged_data = b"{unparseable\n"

    def forged_decoder(_data: object) -> dict[str, Any]:
        return document

    def forged_writer(*_args: object, **_kwargs: object) -> str:
        return forged_data.decode("utf-8").removesuffix("\n")

    with monkeypatch.context() as patch:
        patch.setattr(json, "loads", forged_decoder)
        patch.setattr(json, "dumps", forged_writer)
        with pytest.raises(
            audit.TargetEchoAuditError,
            match="RSS stage receipt is not canonical JSON",
        ):
            audit._validate_rss_stage_bytes(forged_data, row, raw=False)


def test_rss_receipt_accepts_original_canonical_source_bytes() -> None:
    """A normal synthetic v6 receipt maintains exact RSS byte authority."""
    document, row = _synthetic_rss_canonicality_inputs()
    data = (json.dumps(document, sort_keys=True, separators=(",", ":")) + "\n").encode(
        "utf-8"
    )
    audit._validate_rss_stage_bytes(data, row, raw=False)


@pytest.mark.parametrize(
    ("policy_name", "replacement", "foreign_path"),
    [
        ("ROOT_PART", "other", "other/arena-target-echo-1/study.json"),
        ("RUN_PREFIX", "foreign-", ".temp/foreign-1/study.json"),
        ("STUDY_LEAF", "payload.json", ".temp/arena-target-echo-1/payload.json"),
        ("UNDERSCORE", "-", ".temp/arena-target-echo-a-b/study.json"),
    ],
)
def test_target_audit_path_policy_cannot_be_rebound_by_public_names(
    monkeypatch: pytest.MonkeyPatch,
    policy_name: str,
    replacement: str,
    foreign_path: str,
) -> None:
    """A changed module spelling cannot authorize another evidence namespace."""
    monkeypatch.setattr(audit, policy_name, replacement)
    with pytest.raises(audit.TargetEchoAuditError, match="canonical|directory|study"):
        audit._prefix(foreign_path)
    assert audit._prefix(".temp/arena-target-echo-1/study.json") == (
        ".temp/arena-target-echo-1"
    )


def test_target_audit_study_byte_cap_cannot_be_raised_by_public_policy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A forged read receipt larger than the fixed 16 MiB cap cannot pass."""
    oversized = b"{}" + b" " * (audit.MAX_STUDY_BYTES - 1)
    monkeypatch.setattr(audit, "MAX_STUDY_BYTES", len(oversized))
    monkeypatch.setattr(
        audit.evidence,
        "read_bounded_regular",
        lambda *_args, **_kwargs: oversized,
    )
    monkeypatch.setattr(audit.analyze, "parse_document", lambda _text: {})
    with pytest.raises(audit.TargetEchoAuditError, match="bounded bytes"):
        audit._document(".temp/arena-target-echo-1/study.json")


def _three_cell_target_source() -> tuple[bytes, dict[str, Any]]:
    """Use the frozen classic decode to construct an independently valid trace."""
    operations = ("input", "output", "halt")
    source = bytes(
        next(
            cell
            for cell in range(33, 127)
            if audit.CLASSIC_DECODE[(cell - 33 + position) % 94]
            == {"input": ord("/"), "output": ord("<"), "halt": ord("v")}[token]
        )
        for position, token in enumerate(operations)
    )
    row = {
        "algorithm": producer.BASELINE,
        "case": {"difficulty": 1},
        "metrics": {"artifact_bytes": len(source)},
    }
    return source, row


@pytest.mark.parametrize("policy_name", ["SOURCE_INSTRUCTIONS", "CLASSIC_DECODE"])
def test_target_audit_decoder_cannot_be_rebound_to_accept_corrupt_source(
    monkeypatch: pytest.MonkeyPatch, policy_name: str
) -> None:
    """Corrupted graphical code is not certified by a mutable decode table."""
    source, row = _three_cell_target_source()
    audit._admit_source_bytes(source, row, producer.EOF_MODE)
    wrong_halt = next(
        cell
        for cell in range(33, 127)
        if audit.CLASSIC_DECODE[(cell - 33 + 2) % 94] == ord("o")
    )
    corrupt = source[:-1] + bytes((wrong_halt,))
    if policy_name == "SOURCE_INSTRUCTIONS":
        monkeypatch.setitem(audit.SOURCE_INSTRUCTIONS, "halt", ord("o"))
    else:
        changed_decoder = bytearray(audit.CLASSIC_DECODE)
        changed_decoder[(wrong_halt - 33 + 2) % 94] = ord("v")
        monkeypatch.setattr(audit, "CLASSIC_DECODE", bytes(changed_decoder))
    with pytest.raises(audit.TargetEchoAuditError, match="source instruction"):
        audit._admit_source_bytes(corrupt, row, producer.EOF_MODE)


@pytest.mark.parametrize("limit_name", ["MAX_TARGET_BYTES", "MAX_PAIRS"])
def test_target_forward_input_caps_cannot_be_raised_through_producer(
    monkeypatch: pytest.MonkeyPatch, limit_name: str
) -> None:
    """The direct source gate retains its own immutable size and pair limits."""
    original = getattr(producer, limit_name)
    monkeypatch.setattr(producer, limit_name, original + 1)

    def forbidden_operations(*_args: object, **_kwargs: object) -> Never:
        pytest.fail("forged forward request reached operation allocation")

    monkeypatch.setattr(audit, "_expected_operations", forbidden_operations)
    with pytest.raises(audit.TargetEchoAuditError, match="bounded"):
        audit.check_forward_candidate_source(
            b"x" * (original + 1) if limit_name == "MAX_TARGET_BYTES" else b"x",
            pairs=1 if limit_name == "MAX_TARGET_BYTES" else original + 1,
            algorithm=audit.WALK,
        )


@pytest.mark.parametrize("policy_name", ["MAX_LEVELS", "MAX_PAIRS"])
def test_target_audit_level_policy_cannot_be_raised_through_producer(
    monkeypatch: pytest.MonkeyPatch, policy_name: str
) -> None:
    """Source-bound research capacity is not increased by producer aliases."""
    original = getattr(producer, policy_name)
    monkeypatch.setattr(producer, policy_name, original + 1)
    values = range(1, original + 2) if policy_name == "MAX_LEVELS" else [original + 1]
    rows = [{"case": {"difficulty": value}} for value in values]
    with pytest.raises(audit.TargetEchoAuditError, match="difficulty|pair"):
        audit._check_levels(rows)


def test_target_audit_trial_policy_cannot_be_raised_through_producer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The fixed study cannot silently gain additional repetition indices."""
    trials = producer.MAX_TRIALS + 1
    monkeypatch.setattr(producer, "MAX_TRIALS", trials)
    rows = [{"case": {"difficulty": 1}, "trial": n} for n in range(trials)]
    with pytest.raises(audit.TargetEchoAuditError, match="trial indices"):
        audit._check_plan(rows, algorithm_count=1)


def test_target_audit_rss_budget_cannot_be_raised_through_producer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A reported peak above the original 1 GiB ceiling remains invalid."""
    original = producer.BUDGET_MIB
    monkeypatch.setattr(producer, "BUDGET_MIB", original + 1)
    document = {
        "study": {"id": audit.FORWARD_RSS_STUDY},
        "observations": [
            {
                "outcome": analyze.VERIFIED,
                "metrics": {"peak_rss_bytes": (original + 1) * 1024 * 1024},
            }
        ],
    }
    with pytest.raises(audit.TargetEchoAuditError, match="peak RSS"):
        audit._check_peak_rss_claims(document)


def test_target_audit_tool_size_cap_cannot_be_raised_through_producer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A sparse executable beyond the agreed 128 MiB limit cannot be admitted."""
    tool = tmp_path / "tool"
    original = producer.MAX_TOOL_BYTES
    with tool.open("wb") as file:
        file.truncate(original + 1)
    monkeypatch.setattr(producer, "MAX_TOOL_BYTES", original + 1)
    with pytest.raises(audit.TargetEchoAuditError, match="128 MiB"):
        audit._admit_tool(tool)


def test_target_audit_pattern_oracle_ignores_rebound_public_vector(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A caller cannot replace the expected bytes for fixed patterned trials."""
    original = audit._pattern_bytes(8)
    monkeypatch.setattr(audit, "PATTERN_BYTES", b"\x00" * 8)
    assert audit._pattern_bytes(8) == original


def test_target_audit_eof_oracle_ignores_rebound_producer_byte(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The independent replay oracle still expects the historical EOF byte."""
    monkeypatch.setattr(producer, "CLASSIC_EOF_BYTE", 0)
    command = ["runner", "program.malbolge"]
    monkeypatch.setattr(
        audit,
        "_invoke_runner",
        lambda *_args: sp.CompletedProcess(command, 0, b"\xa8", b""),
    )
    row = {
        "case": {"difficulty": 1, "family": producer.FAMILY},
        "metrics": {},
    }
    result, expected = audit._replay_execution(
        row, Path("runner"), Path("program.malbolge")
    )
    assert result.stdout == expected == b"\xa8"


@pytest.mark.parametrize(
    ("policy_name", "field"),
    [
        ("METHOD_CLASS", "method_class"),
        ("PRODUCER_IMPLEMENTATION", "implementation"),
        ("PRODUCER_CONFIGURATION", "configuration"),
        ("ACCELERATOR", "accelerator"),
    ],
)
def test_target_audit_manifest_provenance_cannot_follow_rebound_policy(
    monkeypatch: pytest.MonkeyPatch, policy_name: str, field: str
) -> None:
    """Audit provenance is independent of caller-mutable expected fields."""
    prefix = ".temp/arena-target-echo-1"
    run = SimpleNamespace(accelerator="none", commit="a" * 40)
    manifest = SimpleNamespace(
        run=run,
        record_kind=audit.experiment_manifest.RUN_RECORD_KIND,
        method_class="benchmarking",
        implementation="benchmarks/arena/target_echo_reference.py",
        configuration="benchmarks/arena/README.md",
        output=prefix,
    )
    monkeypatch.setattr(audit, policy_name, "forged")
    if field == "accelerator":
        run.accelerator = "forged"
    else:
        setattr(manifest, field, "forged")
    monkeypatch.setattr(
        audit, "_native_regular_bytes", lambda *_args, **_kwargs: b"manifest"
    )
    monkeypatch.setattr(
        audit.experiment_manifest, "parse_manifest", lambda _text: manifest
    )
    document = {"observations": [{"experiment_manifest": "runs/1.toml"}]}
    with pytest.raises(audit.TargetEchoAuditError, match="foreign producer provenance"):
        audit._check_provenance(document, prefix)


def test_target_audit_linked_input_caps_do_not_follow_mutable_dependencies(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Retained manifest, raw and RSS input limits stay at original sizes."""
    manifest_cap = audit.evidence.MAX_MANIFEST_BYTES
    raw_cap = audit.raw_samples.MAX_RAW_BYTES
    rss_cap = audit.RSS_REPORT_LIMIT
    monkeypatch.setattr(audit.evidence, "MAX_MANIFEST_BYTES", manifest_cap + 1)
    monkeypatch.setattr(audit.raw_samples, "MAX_RAW_BYTES", raw_cap + 1)
    monkeypatch.setattr(audit, "RSS_REPORT_LIMIT", rss_cap + 1)
    monkeypatch.setattr(audit, "_rss_receipt_paths", lambda *_args: {"rss/sample.json"})
    monkeypatch.setattr(
        audit, "_native_regular_bytes", lambda *_args, **_kwargs: b"same"
    )
    document = {
        "observations": [
            {
                "experiment_manifest": "runs/sample.toml",
                "raw_sample": "raw/sample.csv",
            }
        ],
    }
    retained = audit._snapshot_linked_inputs(
        document, ".temp/arena-target-echo-1/study.json", "study digest"
    )
    assert retained["runs/sample.toml"][1] == manifest_cap
    assert retained["raw/sample.csv"][1] == raw_cap
    assert retained["rss/sample.json"][1] == rss_cap


def _minimal_native_study_bytes() -> bytes:
    """A complete schema-v1 study without invoking a real target producer."""
    source = {
        "schema_version": 1,
        "study": {
            "id": "target-source-parser-control",
            "question": "Does source JSON remain authoritative?",
            "hypothesis": "Public parser substitution is rejected.",
            "baseline": "direct-echo",
            "rejection_observation": "A foreign parser supplies unrelated fields.",
            "stage": "synthetic-audit-control",
            "target_profile": "malbolge-1998",
            "host": "test-host",
            "toolchain": "test-toolchain",
            "budget": {"time_ns": 10, "memory_bytes": 10},
            "objectives": ["elapsed_ns", "artifact_bytes"],
        },
        "observations": [
            {
                "algorithm": "direct-echo",
                "case": {
                    "family": "test-source-family",
                    "version": 1,
                    "difficulty": 1,
                    "seed": 0,
                    "workload_sha256": "a" * 64,
                },
                "trial": 0,
                "outcome": analyze.VERIFIED,
                "verifier": "independent-test-oracle",
                "verifier_verdict": analyze.ACCEPTED,
                "experiment_manifest": "runs/test.toml",
                "raw_sample": "raw/test.csv",
                "metrics": {"elapsed_ns": 1, "artifact_bytes": 1},
            }
        ],
    }
    encoded = json.dumps(source, sort_keys=True).encode("utf-8")
    assert analyze.parse_document(encoded.decode("utf-8")) == source
    return encoded


def test_target_study_uses_source_parser_not_replaced_public_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Retained bytes cannot be reinterpreted by a swapped public parser."""
    raw = _minimal_native_study_bytes()
    source = json.loads(raw)
    forged = copy.deepcopy(source)
    forged["study"]["question"] = "Forged research claim"
    monkeypatch.setattr(audit, "_native_regular_bytes", lambda *_args, **_kwargs: raw)
    monkeypatch.setattr(audit.analyze, "parse_document", lambda _text: forged)
    document, digest = audit._document(".temp/arena-target-echo-test/study.json")
    assert document == source
    assert digest == sha256(raw).hexdigest()


def test_target_study_rejects_invalid_json_even_if_public_parser_forgets_shape(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Malformed source bytes cannot inherit a forged admitted document."""
    monkeypatch.setattr(audit, "_native_regular_bytes", lambda *_args, **_kwargs: b"{}")
    monkeypatch.setattr(
        audit.analyze, "parse_document", lambda _text: {"schema_version": 1}
    )
    with pytest.raises(analyze.ArenaError, match="root"):
        audit._document(".temp/arena-target-echo-test/study.json")


@pytest.mark.parametrize(
    "site",
    ["options", "source_hash", "git_lookup", "outer_audit"],
)
def test_target_audit_retains_original_rejection_class_after_public_rebinding(
    monkeypatch: pytest.MonkeyPatch, site: str
) -> None:
    """Mutable public exceptions cannot redefine native audit failures."""
    original = audit.TargetEchoAuditError
    monkeypatch.setattr(audit, "TargetEchoAuditError", RuntimeError)
    if site == "options":
        action = lambda: audit._admit_options(
            audit.AuditOptions(replay_candidates=cast("Any", "true"))
        )
    elif site == "source_hash":
        monkeypatch.setattr(
            audit, "sha256", lambda _data: (_ for _ in ()).throw(LookupError())
        )
        action = lambda: audit._source_sha256(b"source")
    elif site == "git_lookup":
        monkeypatch.setattr(audit.shutil, "which", lambda *_a, **_k: None)
        action = lambda: audit._require_git_commit("a" * 40)
    else:

        def fail_study(*_args: object, **_kwargs: object) -> Never:
            raise original("original retained-study rejection")

        monkeypatch.setattr(audit, "_admit_study", fail_study)
        action = lambda: audit.audit(".temp/arena-target-echo-test/study.json")
    with pytest.raises(original) as observed:
        action()
    assert type(observed.value) is original
    if site == "outer_audit":
        assert observed.value.args == ("original retained-study rejection",)


@pytest.mark.parametrize("failure", ["exit_code", "step_receipt"])
def test_target_replay_retains_original_tool_error_after_public_rebinding(
    monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    """Replay tool diagnostics retain the original typed exception contract."""
    original = audit.TargetReplayToolError
    monkeypatch.setattr(audit, "TargetReplayToolError", RuntimeError)
    output = b"\xa8"
    stderr = (
        audit.STEPS_REPORT_PREFIX + b"1\n"
        if failure == "exit_code"
        else b"untrusted steps\n"
    )
    receipt = sp.CompletedProcess(["vm"], int(failure == "exit_code"), output, stderr)
    with pytest.raises(original) as observed:
        audit._check_forward_replay_result(receipt, b"", 1)
    assert type(observed.value) is original


def test_target_audit_safe_detail_preserves_original_not_rebound_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Only the original audit class may contribute trusted diagnostic text."""
    original = audit.TargetEchoAuditError

    class ForeignAuditError(Exception):
        pass

    monkeypatch.setattr(audit, "TargetEchoAuditError", ForeignAuditError)
    assert audit._safe_error_detail(original("original safe detail")) == (
        "original safe detail"
    )
    assert audit._safe_error_detail(ForeignAuditError("forged safe detail")) == (
        "ForeignAuditError"
    )


@pytest.mark.parametrize(
    "dependency",
    ["target_process", "report_output", "analyze", "evidence", "producer"],
)
def test_target_audit_preserves_native_dependency_diagnostics_after_rebinding(
    monkeypatch: pytest.MonkeyPatch, dependency: str
) -> None:
    """Late dependency exports cannot rewrite the trusted error whitelist."""
    module, name = {
        "target_process": (target_process, "TargetProcessError"),
        "report_output": (report_output, "ReportOutputError"),
        "analyze": (analyze, "ArenaError"),
        "evidence": (evidence, "EvidenceError"),
        "producer": (producer, "TargetEchoStudyError"),
    }[dependency]
    original = getattr(module, name)

    class ForeignDependencyError(Exception):
        pass

    monkeypatch.setattr(module, name, ForeignDependencyError)
    assert audit._safe_error_detail(original("original dependency detail")) == (
        "original dependency detail"
    )
    assert audit._safe_error_detail(ForeignDependencyError("forged detail")) == (
        "ForeignDependencyError"
    )


@pytest.mark.parametrize("provider", ["type", "any"])
def test_target_audit_options_reject_forged_native_boolean_receipts(
    monkeypatch: pytest.MonkeyPatch, provider: str
) -> None:
    """A public built-in alias cannot convert an invalid replay opt-in."""
    invalid = "yes"
    options = audit.AuditOptions(replay_candidates=cast("Any", invalid))
    if provider == "type":
        native_type = type

        def forged_type(value: object) -> type[object]:
            return bool if value is invalid else native_type(value)

        monkeypatch.setattr(audit, "type", forged_type, raising=False)
    else:
        monkeypatch.setattr(audit, "any", lambda _items: False, raising=False)
    with pytest.raises(audit.TargetEchoAuditError, match="exact booleans"):
        audit._admit_options(options)


def test_target_audit_reader_rejects_forged_native_byte_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Foreign bytes subclasses must not enter the source evidence boundary."""

    class ForeignBytes(bytes):
        pass

    foreign = ForeignBytes(b"forged")
    native_type = type
    monkeypatch.setattr(
        audit,
        "type",
        lambda value: bytes if value is foreign else native_type(value),
        raising=False,
    )
    monkeypatch.setattr(
        audit.evidence, "read_bounded_regular", lambda *_a, **_k: foreign
    )
    with pytest.raises(audit.TargetEchoAuditError, match="native bounded bytes"):
        audit._native_regular_bytes(Path("."), "raw/sample", limit=1024)


@pytest.mark.parametrize("forged_length", [0, 9999])
def test_target_audit_reader_retains_native_length_boundary(
    monkeypatch: pytest.MonkeyPatch, forged_length: int
) -> None:
    """Late length substitution cannot alter the bounded-file decision."""
    source = b"seven!"
    monkeypatch.setattr(
        audit.evidence, "read_bounded_regular", lambda *_a, **_k: source
    )
    monkeypatch.setattr(audit, "len", lambda _value: forged_length, raising=False)
    if forged_length == 0:
        with pytest.raises(audit.TargetEchoAuditError, match="native bounded bytes"):
            audit._native_regular_bytes(Path("."), "raw/sample", limit=5)
    else:
        assert audit._native_regular_bytes(Path("."), "raw/sample", limit=6) == source


def test_target_audit_path_rejects_replaced_full_scan(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The entire canonical label must pass the native character predicate."""
    monkeypatch.setattr(audit, "all", lambda _items: True, raising=False)
    with pytest.raises(audit.TargetEchoAuditError, match="canonical generated"):
        audit._prefix(".temp/arena-target-echo-bad!/study.json")


def test_target_audit_valid_options_ignore_replaced_type(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A forged type lookup cannot reject a valid native audit policy."""
    monkeypatch.setattr(audit, "type", lambda _value: object, raising=False)
    audit._admit_options(audit.AuditOptions())


@pytest.mark.parametrize("native", [False, True], ids=["forged", "original"])
def test_target_audit_options_use_original_class_identity(
    monkeypatch: pytest.MonkeyPatch, native: bool
) -> None:
    """A replaced exported options constructor cannot define admission."""
    original = audit.AuditOptions()

    class ForeignOptions:
        replay_candidates = False
        require_source_commit_object = False
        stage_rss_breakdown = False
        emitter = None
        runner = None

    monkeypatch.setattr(audit, "AuditOptions", ForeignOptions)
    if native:
        audit._admit_options(original)
    else:
        with pytest.raises(audit.TargetEchoAuditError, match="exact booleans"):
            audit._admit_options(cast("Any", ForeignOptions()))


@pytest.mark.parametrize("native", [False, True], ids=["forged", "original"])
def test_target_audit_vm_receipts_use_original_process_class(
    monkeypatch: pytest.MonkeyPatch, native: bool
) -> None:
    """A replaced subprocess class may neither certify nor discard receipts."""
    original = sp.CompletedProcess(["vm"], 0, b"\xa8", b"")

    class ForeignProcess:
        def __init__(self) -> None:
            self.args = ["vm"]
            self.returncode = 0
            self.stdout = b"\xa8"
            self.stderr = b""

    monkeypatch.setattr(audit.sp, "CompletedProcess", ForeignProcess)
    if native:
        assert audit._admit_vm_replay_receipt(original) is original
    else:
        with pytest.raises(audit.TargetEchoAuditError, match="nonnative"):
            audit._admit_vm_replay_receipt(ForeignProcess())


@pytest.mark.parametrize("native", [False, True], ids=["forged", "original"])
def test_target_audit_metadata_uses_original_stat_result_class(
    monkeypatch: pytest.MonkeyPatch, native: bool
) -> None:
    """Native executable metadata cannot follow a replaced os type alias."""
    original = Path(__file__).stat()

    class ForeignStat:
        st_dev = 1
        st_ino = 2
        st_size = 3
        st_mtime_ns = 4
        st_ctime_ns = 5

    monkeypatch.setattr(audit.os, "stat_result", ForeignStat)
    if native:
        assert audit._tool_file_identity(original)[0] == original.st_dev
    else:
        with pytest.raises(audit.TargetEchoAuditError, match="invalid metadata"):
            audit._tool_file_identity(cast("Any", ForeignStat()))


@pytest.mark.parametrize("kind", ["directory", "symlink"])
def test_target_audit_tool_admission_rejects_rebound_regular_mode(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: str
) -> None:
    """A public stat predicate cannot turn a directory/link into an executable."""
    binary = tmp_path / "binary"
    if kind == "directory":
        binary.mkdir()
    else:
        target = tmp_path / "real-binary"
        target.write_bytes(b"valid executable")
        binary.symlink_to(target)
    monkeypatch.setattr(audit, "stat", SimpleNamespace(S_ISREG=lambda _mode: True))
    with pytest.raises(audit.TargetEchoAuditError, match="regular"):
        audit._admit_tool(binary)


def test_target_audit_tool_identity_rejects_rebound_mode_before_open(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Physical descriptor admission must precede potentially unsafe host IO."""
    directory = tmp_path / "directory"
    directory.mkdir()
    runner = tmp_path / "runner"
    runner.write_bytes(b"runner")
    monkeypatch.setattr(audit, "stat", SimpleNamespace(S_ISREG=lambda _mode: True))

    def forbidden(*_args: object, **_kwargs: object) -> Never:
        pytest.fail("nonregular target reached descriptor open")

    monkeypatch.setattr(audit.os, "open", forbidden)
    with pytest.raises(audit.TargetEchoAuditError, match="identity"):
        audit._tool_identity(directory, runner)


@pytest.mark.parametrize("kind", ["directory", "symlink"])
def test_target_audit_git_rejects_rebound_executable_mode(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: str
) -> None:
    """A forged regular-file verdict cannot launch a nonphysical Git tool."""
    executable = tmp_path / "git"
    if kind == "directory":
        executable.mkdir()
    else:
        target = tmp_path / "real-git"
        target.write_bytes(b"#!/bin/sh\nexit 0\n")
        executable.symlink_to(target)
    monkeypatch.setattr(audit.shutil, "which", lambda *_a, **_kw: str(executable))
    monkeypatch.setattr(audit.os, "access", lambda *_a, **_kw: True)
    monkeypatch.setattr(audit, "stat", SimpleNamespace(S_ISREG=lambda _mode: True))

    def forbidden(*_args: object, **_kwargs: object) -> Never:
        pytest.fail("nonphysical Git path reached process execution")

    monkeypatch.setattr(audit.sp, "run", forbidden)
    with pytest.raises(audit.TargetEchoAuditError, match="physical executable"):
        audit._require_git_commit("a" * 40)


def test_target_audit_valid_executables_ignore_rebound_regular_mode(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A later denying stat hook cannot discard original native files."""
    emitter = tmp_path / "emitter"
    runner = tmp_path / "runner"
    emitter.write_bytes(b"emitter")
    runner.write_bytes(b"runner")
    monkeypatch.setattr(audit, "stat", SimpleNamespace(S_ISREG=lambda _mode: False))
    assert audit._admit_tool(emitter) == emitter
    assert audit._tool_identity(emitter, runner).startswith("local-compiler-vm-sha256:")


def test_target_audit_valid_git_ignores_rebound_regular_mode(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Original regular Git executables remain eligible under alias drift."""
    git = tmp_path / "git"
    git.write_bytes(b"#!/bin/sh\nexit 0\n")
    git.chmod(0o700)
    monkeypatch.setattr(audit.shutil, "which", lambda *_a, **_kw: str(git))
    monkeypatch.setattr(audit, "stat", SimpleNamespace(S_ISREG=lambda _mode: False))

    def original_receipt(command: list[str], **_kwargs: object) -> object:
        return sp.CompletedProcess(command, 0, b"commit\n", b"")

    monkeypatch.setattr(audit.sp, "run", original_receipt)
    audit._require_git_commit("a" * 40)
