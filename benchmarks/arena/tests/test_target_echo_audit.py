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
from typing import TYPE_CHECKING, Any, cast

import pytest
import tomllib

from benchmarks.arena import analyze, evidence, target_process
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
REAL_PROFILE_PROVENANCE = (
    'implementation = "benchmarks/arena/target_echo_reference.py"'
)


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
    registered = f"{stem}.malbolge" if folder == "candidates" else (
        f"{stem}.toml" if folder == "runs" else f"{stem}.csv"
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
    with pytest.raises(audit.TargetEchoAuditError, match="target audit executable identity changed"):
        audit._tool_identity(emitter, runner)


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
    with pytest.raises(audit.TargetEchoAuditError, match="target audit executable identity changed"):
        audit._tool_identity(emitter, runner)


@pytest.fixture
def retained(
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[tuple[Path, dict[str, Any], str]]:
    """Create a real target pilot and remove only its own ignored directory.

    Yields:
        Local output root, recorded study and canonical relative path.

    """
    if (
        not producer.DEFAULT_EMITTER.is_file()
        or not producer.DEFAULT_RUNNER.is_file()
    ):
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
    if (
        not producer.DEFAULT_EMITTER.is_file()
        or not producer.DEFAULT_RUNNER.is_file()
    ):
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
    if (
        not producer.DEFAULT_EMITTER.is_file()
        or not producer.DEFAULT_RUNNER.is_file()
    ):
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
    if (
        not producer.DEFAULT_EMITTER.is_file()
        or not producer.DEFAULT_RUNNER.is_file()
    ):
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
    if (
        not producer.DEFAULT_EMITTER.is_file()
        or not producer.DEFAULT_RUNNER.is_file()
    ):
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
    if (
        not producer.DEFAULT_EMITTER.is_file()
        or not producer.DEFAULT_RUNNER.is_file()
    ):
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
    stem = f"{row["algorithm"]}-pairs-{case["difficulty"]}-trial-{trial}"
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
        assert (
            0 < row["metrics"][VERIFIER_COST_METRIC] <= row["metrics"][ELAPSED]
        )
    for level in (1, 4, 16, 64):
        rows = {
            row["algorithm"]: row
            for row in document["observations"]
            if row["case"]["difficulty"] == level
        }
        walked, skipped = rows[producer.WALK], rows[producer.SKIP]
        assert (
            walked["metrics"][ARTIFACT_BYTES]
            == skipped["metrics"][ARTIFACT_BYTES]
        )
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
    with pytest.raises(
        audit.TargetEchoAuditError, match=r"verifier|objective|metric"
    ):
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
        assert (
            walked["metrics"][ARTIFACT_BYTES]
            == skipped["metrics"][ARTIFACT_BYTES]
        )
        assert (
            walked["metrics"]["runtime_steps"]
            == walked["metrics"][ARTIFACT_BYTES]
        )
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
        row
        for row in document["observations"]
        if row["algorithm"] == producer.SKIP
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
            INVALID_SOURCE
            if forged[index] != INVALID_SOURCE
            else SECOND_INVALID_SOURCE
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
        row
        for row in altered["observations"]
        if row["algorithm"] == producer.SKIP
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
    assert all(
        row["outcome"] == analyze.VERIFIED for row in document["observations"]
    )
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
        audit.audit(
            relative, options=audit.AuditOptions(replay_candidates=True)
        )


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
    assert checked["retained_study_sha256"] == sha256(
        (directory / "study.json").read_bytes()
    ).hexdigest()
    assert checked["verified_target_sources_checked"] == ROWS
    assert checked["target_sources_replayed"] == 0
    assert len(checked["source_sha256"]) == ROWS
    assert len(checked["pareto_frontiers"]) == FRONTIERS
    assert checked["evidence_preflight"]["raw_rows_matched"] == ROWS
    assert checked["reported_failed_trials_not_replayed"] == 0
    assert NOT_AUTHENTICATED in checked["scope"]
    replay = audit.audit(
        relative, options=audit.AuditOptions(replay_candidates=True)
    )
    assert replay["target_sources_replayed"] == REPLAYED
    assert replay["source_sha256"] == checked["source_sha256"]
    assert replay["capacity_curve"] == checked["capacity_curve"]
    assert study["study"]["stage"].startswith("measured-classic")


@pytest.mark.skipif(
    not producer.DEFAULT_EMITTER.is_file()
    or not producer.DEFAULT_RUNNER.is_file(),
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
            assert (
                checked["verified_target_sources_checked"] == MAX_PHASE_TRIALS
            )
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
    source[0] = (
        INVALID_SOURCE if source[0] != INVALID_SOURCE else INVALID_SOURCE + 1
    )
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
    with pytest.raises(
        audit.TargetEchoAuditError, match=r"must be|No such file"
    ):
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
            path
            for path in (directory / "candidates").iterdir()
            if path != existing
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
        audit.audit(
            relative, options=audit.AuditOptions(replay_candidates=True)
        )


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
            INVALID_SOURCE
            if contents[0] != INVALID_SOURCE
            else INVALID_SOURCE + 1
        )
        target.write_bytes(contents)
        return actual_analyze(study)

    monkeypatch.setattr(audit.analyze, "analyze", mutate_after_decode)
    with pytest.raises(
        audit.TargetEchoAuditError, match="changed before report"
    ):
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
    with pytest.raises(
        audit.TargetEchoAuditError, match="changed before report"
    ):
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
    fake_runner.write_text(
        f"#!{sys.executable}\nimport os\nos.write(1,b'Z'*8192)\n"
    )
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
        _ = (runner, source)
        return sp.CompletedProcess(["fake-vm"], 0, stdout=b"wrong", stderr=b"")

    monkeypatch.setattr(audit, "_invoke_runner", wrong_output)
    with pytest.raises(audit.TargetEchoAuditError, match="VM replay rejected"):
        audit.audit(
            relative, options=audit.AuditOptions(replay_candidates=True)
        )


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
