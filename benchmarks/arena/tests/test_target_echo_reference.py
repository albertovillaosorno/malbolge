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
#   - Exact real-target reference measurements and source/receipt regressions.
# - Must-Not:
#   - Report target echo microbenchmarks as generalized C compilation.
# - Allows:
#   - Inputs: test-owned ignored target sources and executable stubs.
#   - Outputs: checked Malbolge VM evidence and fail-closed negative records.
#   - Side effects: removed test-owned study directories and process launches.
# - Split-When:
#   - A general compiler candidate study has a larger independent verifier.
# - Merge-When:
#   - A verified target-stage runner owns the same bounded echo baseline.
# - Summary:
#   - Confirms real target code and manifest/raw identity after VM execution.
# - Description:
#   - Tests matched pairs, retained failures and unsupported study requests.
# - Usage:
#   - pytest benchmarks/arena/tests/test_target_echo_reference.py.
# - Defaults:
#   - No real artifact evidence without local built emitter and VM binaries.
#

"""Actual classic Malbolge VM target-echo research pilot tests."""

# ruff: file-ignore[assert,private-member-access]

from __future__ import annotations

import json
import os
import shutil
import subprocess as sp  # ruff: ignore[suspicious-subprocess-import]
import sys
import tempfile
from hashlib import sha256
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import pytest

from benchmarks.arena import (
    analyze,
    evidence,
    report_output,
    target_echo_audit,
    target_echo_reference,
)
from benchmarks.arena.tests.test_evidence import sample_study

if TYPE_CHECKING:
    from collections.abc import Iterator


TARGET_RAW = "raw"
TARGET_RUNS = "runs"
TARGET_RSS = "rss"
TARGET_STUDY = "study"


class _FaultyTargetWriter:
    """Inject one host short write at a selected retained evidence site."""

    def __init__(
        self,
        monkeypatch: pytest.MonkeyPatch,
        root: Path,
        *,
        site: str,
        bad_count: object,
    ) -> None:
        self.site = site
        self.bad_count = bad_count
        self.faults = 0
        self.original_bytes = type(root).write_bytes
        self.original_text = type(root).write_text

        def injected_bytes(path: Path, data: bytes) -> int:
            return self.write_bytes(path, data)

        def injected_text(path: Path, data: str, encoding: str | None = None) -> int:
            return self.write_text(path, data, encoding=encoding)

        monkeypatch.setattr(type(root), "write_bytes", injected_bytes)
        monkeypatch.setattr(type(root), "write_text", injected_text)

    def selected(self, path: Path) -> bool:
        """Match only the retained sidecar under investigation.

        Returns:
            Whether the path belongs to this injected failure site.

        """
        return path.parent.name == self.site or (
            self.site == TARGET_STUDY and path.name == STUDY_LEAF
        )

    def write_bytes(self, path: Path, data: bytes) -> int:
        """Report a malformed byte count after writing one byte.

        Returns:
            Incomplete or forged acknowledgement for selected files.

        """
        if self.selected(path):
            self.faults += 1
            _ = self.original_bytes(path, data[:1])
            return cast("int", self.bad_count)
        return self.original_bytes(path, data)

    def write_text(
        self,
        path: Path,
        data: str,
        encoding: str | None = None,
    ) -> int:
        """Report a malformed text count after writing one character.

        Returns:
            Incomplete or forged acknowledgement for selected files.

        """
        if self.selected(path):
            self.faults += 1
            _ = self.original_text(path, data[:1], encoding=encoding)
            return cast("int", self.bad_count)
        return self.original_text(path, data, encoding=encoding)


def _synthetic_target_context(
    tmp_path: Path, *, site: str
) -> target_echo_reference._Context:
    """Create local directories without running an external compiler or VM.

    Returns:
        Synthetic context with test-owned output directories.

    """
    for name in (TARGET_RAW, TARGET_RUNS, TARGET_RSS, "candidates"):
        (tmp_path / name).mkdir()
    return target_echo_reference._Context(
        tmp_path,
        ".temp/synthetic-target",
        "f" * 64,
        "a" * 40,
        "test-host",
        "test-toolchain",
        tmp_path / "emitter",
        tmp_path / "runner",
        retain_rss_stages=site == TARGET_RSS,
    )


def _invoke_target_rss(context: target_echo_reference._Context) -> object:
    """Write a single synthetic verified RSS receipt.

    Returns:
        Published receipt digest on complete write.

    """
    trial = {
        "algorithm": "direct",
        "outcome": analyze.VERIFIED,
        "case": {"difficulty": 1, "workload_sha256": "f" * 64},
        "trial": 0,
    }
    return target_echo_reference._write_rss_stages(
        context, trial, values=[1024, 2048, 4096]
    )


def _invoke_target_attempt(
    monkeypatch: pytest.MonkeyPatch,
    context: target_echo_reference._Context,
) -> object:
    """Write one synthetic pair of target raw and TOML evidence.

    Returns:
        Reported trial row on complete writes.

    """

    def fake_measure(*args: object, **kwargs: object) -> tuple[str, dict[str, int]]:
        _ = (args, kwargs)
        return analyze.VERIFIED, {"elapsed_ns": 1}

    monkeypatch.setattr(target_echo_reference, "_measure", fake_measure)
    monkeypatch.setattr(target_echo_reference, "_raw_csv", lambda *_: b"test-raw")

    def fake_manifest(*args: object, **kwargs: object) -> str:
        _ = (args, kwargs)
        return "test-manifest"

    monkeypatch.setattr(target_echo_reference, "_manifest", fake_manifest)
    return target_echo_reference._write_attempt(context, 1, 0, algorithm="direct")


def _invoke_target_study(
    monkeypatch: pytest.MonkeyPatch,
    context: target_echo_reference._Context,
) -> object:
    """Attempt study publication without using any external target process.

    Returns:
        Admitted report only if the output write and audit succeed.

    """
    monkeypatch.setattr(target_echo_reference, "_prepare_context", lambda *_: context)

    def fake_attempt(*args: object, **kwargs: object) -> dict[str, Any]:
        _ = (args, kwargs)
        return {}

    monkeypatch.setattr(target_echo_reference, "_write_attempt", fake_attempt)
    monkeypatch.setattr(
        target_echo_reference,
        "_make_document",
        lambda *_: {"schema_version": 1},
    )

    def forbidden(path: Path) -> None:
        _ = path
        pytest.fail("invalid write reached independent source audit")

    monkeypatch.setattr(target_echo_reference, "_audit_retained_study", forbidden)
    return target_echo_reference.run_study(target_echo_reference.StudyPlan((1,), 1))


def _invoke_target_retained_site(
    monkeypatch: pytest.MonkeyPatch,
    context: target_echo_reference._Context,
    *,
    site: str,
) -> object:
    """Select the synthetic retained write under test.

    Returns:
        The successful writer result when publication is complete.

    """
    if site == TARGET_RSS:
        return _invoke_target_rss(context)
    if site == TARGET_STUDY:
        return _invoke_target_study(monkeypatch, context)
    return _invoke_target_attempt(monkeypatch, context)


@pytest.mark.parametrize("site", [TARGET_RAW, TARGET_RUNS, TARGET_RSS, TARGET_STUDY])
@pytest.mark.parametrize("bad_count", [None, True, -1, 1, 1_000_000])
def test_target_retained_output_rejects_invalid_write_acknowledgements(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    *,
    site: str,
    bad_count: object,
) -> None:
    """A short or foreign host write never certifies target trial evidence."""
    context = _synthetic_target_context(tmp_path, site=site)
    faulty = _FaultyTargetWriter(monkeypatch, tmp_path, site=site, bad_count=bad_count)
    with pytest.raises(target_echo_reference.TargetEchoStudyError, match="write count"):
        _ = _invoke_target_retained_site(monkeypatch, context, site=site)
    assert faulty.faults == 1


@pytest.mark.parametrize("site", [TARGET_RAW, TARGET_RUNS, TARGET_RSS, TARGET_STUDY])
@pytest.mark.parametrize("kind", [OSError, IndexError, OverflowError])
def test_target_retained_writer_host_faults_are_typed_without_formatting(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    site: str,
    kind: type[Exception],
) -> None:
    """All four retained writer sites keep foreign errors as typed causes."""
    context = _synthetic_target_context(tmp_path, site=site)

    class HostileWriterFault(kind):
        def __str__(self) -> str:
            raise AssertionError("foreign retained writer formatter executed")

    fault = HostileWriterFault("untrusted host write error")
    original_bytes = type(tmp_path).write_bytes
    original_text = type(tmp_path).write_text
    attempts = 0

    def selected(path: Path) -> bool:
        return path.parent.name == site or (
            site == TARGET_STUDY and path.name == STUDY_LEAF
        )

    def injected_bytes(path: Path, data: bytes) -> int:
        nonlocal attempts
        if selected(path):
            attempts += 1
            raise fault
        return original_bytes(path, data)

    def injected_text(path: Path, data: str, encoding: str | None = None) -> int:
        nonlocal attempts
        if selected(path):
            attempts += 1
            raise fault
        return original_text(path, data, encoding=encoding)

    monkeypatch.setattr(type(tmp_path), "write_bytes", injected_bytes)
    monkeypatch.setattr(type(tmp_path), "write_text", injected_text)
    with pytest.raises(
        target_echo_reference.TargetEchoStudyError, match="write failed"
    ) as caught:
        _ = _invoke_target_retained_site(monkeypatch, context, site=site)
    assert caught.value.__cause__ is fault
    assert attempts == 1


RAW_TAMPER = "raw"
STUDY_LEAF = "study.json"
ORIGINAL_TRIAL = "trial = 0"
EXPECTED_OBSERVATIONS = 8
EXPECTED_LEVELS = 2
EXPECTED_TRIALS = 2
SINGLE_PAIRED_TRIAL_ARMS = 2
ARTIFACT_BYTES = "artifact_bytes"
GRAPHICAL_LOW = 33
GRAPHICAL_HIGH = 126
BOOL_TRIAL_ALIAS = True
OUTPUT_ARGUMENT = "--output"
TOOL_FAILED = "tool_failed"
FORGED_COUNT = 999
EXPECTED_STEP_RECEIPT = 3
RUNTIME_STEPS = "runtime_steps"
PATTERNED_LEVEL_COUNT = 4
PATTERNED_MAX_PAIR_COUNT = 64
PATTERNED_DIRECT_BYTES = 131
PATTERNED_PADDED_BYTES = 196


PROFILE_PREFLIGHT = "profile"
REVISION_PREFLIGHT = "revision"
TOOL_IDENTITY_PREFLIGHT = "tool_identity"
PREFLIGHT_REJECTED = "preflight rejected"


@pytest.mark.parametrize(
    "receipt",
    ["", "relative/git", "bad\0path", b"/usr/bin/git", False, 7],
    ids=["empty", "relative", "nul", "bytes", "boolean", "integer"],
)
def test_target_echo_commit_rejects_invalid_git_resolver_receipt(
    monkeypatch: pytest.MonkeyPatch,
    receipt: object,
) -> None:
    """Source-commit admission never launches a noncanonical Git executable."""
    monkeypatch.setattr(
        target_echo_reference.shutil,
        "which",
        lambda *_args, **_kwargs: cast("str", receipt),
    )

    def forbidden(*_args: object, **_kwargs: object) -> None:
        pytest.fail("unadmitted Git path reached process execution")

    monkeypatch.setattr(target_echo_reference.sp, "run", forbidden)
    with pytest.raises(target_echo_reference.TargetEchoStudyError, match="Git"):
        target_echo_reference._commit()


@pytest.mark.parametrize("kind", ["missing", "directory", "nonexecutable", "symlink"])
def test_target_echo_commit_rejects_unsafe_git_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
) -> None:
    """A resolver's path receipt must name an actual physical executable."""
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
    monkeypatch.setattr(
        target_echo_reference.shutil, "which", lambda *_args, **_kwargs: str(git)
    )

    def forbidden(*_args: object, **_kwargs: object) -> None:
        pytest.fail("unsafe Git path reached process execution")

    monkeypatch.setattr(target_echo_reference.sp, "run", forbidden)
    with pytest.raises(target_echo_reference.TargetEchoStudyError, match="Git"):
        target_echo_reference._commit()


class _UnexpectedHostFault(Exception):
    """Unclassified host dependency fault with an unsafe string hook."""

    def __str__(self) -> str:
        raise AssertionError("foreign target host exception formatter executed")


@pytest.mark.parametrize(
    "failure",
    [OSError, ValueError, RuntimeError, TypeError, AttributeError, IndexError, _UnexpectedHostFault],
)
def test_target_echo_commit_types_git_resolver_errors(
    monkeypatch: pytest.MonkeyPatch,
    failure: type[Exception],
) -> None:
    """Host lookup faults remain within the typed source-revision boundary."""

    def broken(*_args: object, **_kwargs: object) -> None:
        raise failure("host resolver failed")

    monkeypatch.setattr(target_echo_reference.shutil, "which", broken)
    with pytest.raises(
        target_echo_reference.TargetEchoStudyError, match="revision"
    ) as caught:
        target_echo_reference._commit()
    assert isinstance(caught.value.__cause__, failure)


@pytest.mark.parametrize(
    "failure", [ValueError, RuntimeError, TypeError, AttributeError, IndexError, _UnexpectedHostFault]
)
def test_target_echo_commit_types_git_transport_errors(
    monkeypatch: pytest.MonkeyPatch,
    failure: type[Exception],
) -> None:
    """A trusted executable still cannot leak malformed host subprocess faults."""

    def broken(*_args: object, **_kwargs: object) -> None:
        raise failure("Git subprocess unavailable")

    monkeypatch.setattr(target_echo_reference.sp, "run", broken)
    with pytest.raises(
        target_echo_reference.TargetEchoStudyError, match="revision"
    ) as caught:
        target_echo_reference._commit()
    assert isinstance(caught.value.__cause__, failure)


@pytest.mark.parametrize("site", ["stat", "access"])
@pytest.mark.parametrize("failure", [IndexError, _UnexpectedHostFault])
def test_target_echo_commit_types_unanticipated_git_file_inspection_faults(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    site: str,
    failure: type[Exception],
) -> None:
    """Git tool path metadata failures cannot escape revision preflight."""
    git = tmp_path / "git"
    _ = git.write_bytes(b"#!/bin/sh\nexit 0\n")
    git.chmod(0o700)
    fault = failure("unanticipated Git metadata failure")
    monkeypatch.setattr(
        target_echo_reference.shutil, "which", lambda *_args, **_kwargs: str(git)
    )
    if site == "stat":
        original_lstat = Path.lstat

        def bad_lstat(path: Path) -> os.stat_result:
            if path == git:
                raise fault
            return original_lstat(path)

        monkeypatch.setattr(Path, "lstat", bad_lstat)
    else:
        original_access = os.access

        def bad_access(path: str | bytes | os.PathLike[str] | os.PathLike[bytes], mode: int) -> bool:
            if path == str(git):
                raise fault
            return original_access(path, mode)

        monkeypatch.setattr(target_echo_reference.os, "access", bad_access)
    with pytest.raises(
        target_echo_reference.TargetEchoStudyError, match="Git executable"
    ) as caught:
        target_echo_reference._commit()
    assert caught.value.__cause__ is fault


@pytest.mark.parametrize(
    ("status", "stdout"),
    [(0, None), (0, b"x" * 40), (1, "a" * 40), (True, "a" * 40)],
    ids=["missing-stdout", "byte-stdout", "nonzero-exit", "boolean-exit"],
)
def test_target_echo_commit_rejects_noncanonical_git_receipts(
    monkeypatch: pytest.MonkeyPatch,
    status: object,
    stdout: object,
) -> None:
    """Only an actual successful native Git revision text is reportable."""
    monkeypatch.setattr(
        target_echo_reference.sp,
        "run",
        lambda *_args, **_kwargs: sp.CompletedProcess(
            ["git"], cast("int", status), cast("str", stdout), ""
        ),
    )
    with pytest.raises(
        target_echo_reference.TargetEchoStudyError, match="Git revision"
    ):
        target_echo_reference._commit()


@pytest.mark.parametrize(
    "stage", [PROFILE_PREFLIGHT, REVISION_PREFLIGHT, TOOL_IDENTITY_PREFLIGHT]
)
def test_failed_preflight_does_not_create_retained_target_study(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    stage: str,
) -> None:
    """Rejected setup cannot leave orphan study directories or partial runs."""
    emitter = tmp_path / "emitter"
    runner = tmp_path / "runner"
    _ = emitter.write_bytes(b"emitter")
    _ = runner.write_bytes(b"runner")
    profile = target_echo_reference._ROOT / "malbolge.json"
    _ = (tmp_path / "malbolge.json").write_bytes(profile.read_bytes())
    temp_root = tmp_path / ".temp"
    temp_root.mkdir()
    monkeypatch.setattr(target_echo_reference, "_ROOT", tmp_path)
    monkeypatch.setattr(target_echo_reference, "_TEMP", temp_root)
    monkeypatch.setattr(target_echo_reference, "_commit", lambda: "a" * 40)

    def refuse(*args: object, **kwargs: object) -> None:
        _ = (args, kwargs)
        raise target_echo_reference.TargetEchoStudyError(PREFLIGHT_REJECTED)

    if stage == PROFILE_PREFLIGHT:
        monkeypatch.setattr(
            target_echo_reference.target_profile, "load_document", refuse
        )
    elif stage == REVISION_PREFLIGHT:
        monkeypatch.setattr(target_echo_reference, "_commit", refuse)
    else:
        monkeypatch.setattr(target_echo_reference, "_tool_identity", refuse)

    with pytest.raises(
        target_echo_reference.TargetEchoStudyError, match=PREFLIGHT_REJECTED
    ):
        _ = target_echo_reference._prepare_context(emitter, runner)
    assert not list(temp_root.glob("arena-target-echo-*"))


WORKSPACE_CREATE_STAGE = "create"
WORKSPACE_SUBDIR_STAGE = "subdirectory"
WORKSPACE_ERROR = "study workspace"


@pytest.mark.parametrize(
    "error_type",
    [PermissionError, ValueError, RuntimeError, IndexError, OverflowError, LookupError],
)
@pytest.mark.parametrize("stage", [WORKSPACE_CREATE_STAGE, WORKSPACE_SUBDIR_STAGE])
def test_failed_workspace_setup_is_typed_and_removes_partial_study(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    stage: str,
    error_type: type[Exception],
) -> None:
    """An unusable output folder cannot escape as raw OS failure or orphan."""
    emitter = tmp_path / "emitter"
    runner = tmp_path / "runner"
    _ = emitter.write_bytes(b"emitter")
    _ = runner.write_bytes(b"runner")
    profile = target_echo_reference._ROOT / "malbolge.json"
    _ = (tmp_path / "malbolge.json").write_bytes(profile.read_bytes())
    temp_root = tmp_path / ".temp"
    temp_root.mkdir()
    monkeypatch.setattr(target_echo_reference, "_ROOT", tmp_path)
    monkeypatch.setattr(target_echo_reference, "_TEMP", temp_root)
    monkeypatch.setattr(target_echo_reference, "_commit", lambda: "a" * 40)

    if stage == WORKSPACE_CREATE_STAGE:

        def failed_creation(*args: object, **kwargs: object) -> str:
            _ = (args, kwargs)
            message = "injected workspace creation failure"
            raise error_type(message)

        monkeypatch.setattr(target_echo_reference.tempfile, "mkdtemp", failed_creation)
    else:
        original_mkdir = type(tmp_path).mkdir

        def failed_subdirectory(path: Path, *args: Any, **kwargs: Any) -> None:
            if path.name == "raw" and path.parent.name.startswith("arena-target-echo-"):
                message = "injected workspace subdirectory failure"
                raise error_type(message)
            original_mkdir(path, *args, **kwargs)

        monkeypatch.setattr(type(tmp_path), "mkdir", failed_subdirectory)

    with pytest.raises(
        target_echo_reference.TargetEchoStudyError, match=WORKSPACE_ERROR
    ) as failure:
        _ = target_echo_reference._prepare_context(emitter, runner)
    assert isinstance(failure.value.__cause__, error_type)
    assert not list(temp_root.glob("arena-target-echo-*"))


@pytest.mark.parametrize(
    "error_type", [ValueError, RuntimeError, IndexError, OverflowError]
)
def test_target_echo_workspace_root_host_failures_are_typed(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    error_type: type[Exception],
) -> None:
    """An unexpected root inspection failure cannot leak to callers."""

    def faulty_lstat(path: Path) -> None:
        _ = path
        message = "injected workspace root inspection failure"
        raise error_type(message)

    monkeypatch.setattr(target_echo_reference, "_admit_executable", lambda path: path)
    monkeypatch.setattr(target_echo_reference.Path, "lstat", faulty_lstat)
    monkeypatch.setattr(target_echo_reference, "_TEMP", tmp_path)
    with pytest.raises(
        target_echo_reference.TargetEchoStudyError, match=r"repository \.temp"
    ) as failure:
        _ = target_echo_reference._prepare_context(tmp_path, tmp_path)
    assert isinstance(failure.value.__cause__, error_type)


@pytest.mark.parametrize(
    "cleanup_type", [ValueError, RuntimeError, IndexError, OverflowError]
)
def test_target_echo_workspace_cleanup_preserves_primary_setup_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    cleanup_type: type[Exception],
) -> None:
    """Unexpected cleanup faults cannot hide an earlier failed mkdir."""

    def faulty_mkdir(path: Path) -> None:
        _ = path
        message = "injected workspace subdirectory failure"
        raise OSError(message)

    def faulty_cleanup(path: Path) -> None:
        _ = path
        message = "injected workspace cleanup failure"
        raise cleanup_type(message)

    monkeypatch.setattr(target_echo_reference.Path, "mkdir", faulty_mkdir)
    monkeypatch.setattr(target_echo_reference.shutil, "rmtree", faulty_cleanup)
    with pytest.raises(
        target_echo_reference.TargetEchoStudyError,
        match="initialization failed",
    ) as failure:
        target_echo_reference._initialize_workspace_folders(tmp_path, ("raw",))
    assert isinstance(failure.value.__cause__, OSError)
    cleanup_note = "cleanup failed"
    assert any(cleanup_note in note for note in failure.value.__cause__.__notes__)


def test_target_echo_workspace_unknown_host_faults_do_not_format_foreign_errors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Both unexpected host errors preserve the primary mkdir rejection."""

    class ForeignHostError(Exception):
        def __str__(self) -> str:
            raise AssertionError("foreign workspace error formatter invoked")

    primary = ForeignHostError("untrusted directory creation fault")
    cleanup = ForeignHostError("untrusted directory removal fault")

    def fail_mkdir(*_args: object, **_kwargs: object) -> None:
        raise primary

    def fail_cleanup(*_args: object, **_kwargs: object) -> None:
        raise cleanup

    monkeypatch.setattr(target_echo_reference.Path, "mkdir", fail_mkdir)
    monkeypatch.setattr(target_echo_reference.shutil, "rmtree", fail_cleanup)
    with pytest.raises(
        target_echo_reference.TargetEchoStudyError, match="initialization failed"
    ) as caught:
        target_echo_reference._initialize_workspace_folders(tmp_path, ("raw",))
    assert caught.value.__cause__ is primary
    assert any("ForeignHostError" in note for note in primary.__notes__)


def _prepare_target_host_identity_test(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Keep all non-host preflight dependencies inert and forbid output."""
    monkeypatch.setattr(target_echo_reference, "_ROOT", tmp_path)
    monkeypatch.setattr(target_echo_reference, "_TEMP", tmp_path)
    monkeypatch.setattr(target_echo_reference, "_admit_executable", lambda path: path)
    monkeypatch.setattr(
        target_echo_reference.target_profile, "load_document", lambda *_: {}
    )
    monkeypatch.setattr(
        target_echo_reference.target_profile,
        "profile_fingerprint",
        lambda *_: "f" * 64,
    )
    monkeypatch.setattr(target_echo_reference, "_commit", lambda: "a" * 40)
    monkeypatch.setattr(target_echo_reference, "_tool_identity", lambda *_: "test-tool")

    def forbidden_workspace(*_args: object, **_kwargs: object) -> None:
        pytest.fail("invalid host identity reached workspace creation")

    monkeypatch.setattr(target_echo_reference.tempfile, "mkdtemp", forbidden_workspace)


@pytest.mark.parametrize("kind", [IndexError, OverflowError, LookupError])
def test_target_echo_platform_host_lookup_failure_is_typed_before_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: type[Exception]
) -> None:
    """An unanticipated host identity lookup never escapes producer preflight."""
    _prepare_target_host_identity_test(tmp_path, monkeypatch)

    class ForeignPlatformFailure(kind):
        def __str__(self) -> str:
            raise AssertionError("foreign host platform error formatter invoked")

    error = ForeignPlatformFailure("untrusted host lookup failure")

    def fail_platform() -> str:
        raise error

    monkeypatch.setattr(target_echo_reference.platform, "platform", fail_platform)
    with pytest.raises(
        target_echo_reference.TargetEchoStudyError, match="host identity lookup"
    ) as caught:
        _ = target_echo_reference._prepare_context(tmp_path, tmp_path)
    assert caught.value.__cause__ is error


@pytest.mark.parametrize(
    "bad_host", [None, 0, True, b"host", "", " ", "host\nlabel", "h" * 257]
)
def test_target_echo_platform_host_rejects_noncanonical_labels_before_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, bad_host: object
) -> None:
    """Only bounded native printable labels may enter retained provenance."""
    _prepare_target_host_identity_test(tmp_path, monkeypatch)
    monkeypatch.setattr(target_echo_reference.platform, "platform", lambda: bad_host)
    with pytest.raises(
        target_echo_reference.TargetEchoStudyError, match="host identity requires"
    ):
        _ = target_echo_reference._prepare_context(tmp_path, tmp_path)


def test_target_echo_platform_host_never_calls_foreign_string_hooks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A string subclass cannot execute its hooks during provenance admission."""
    _prepare_target_host_identity_test(tmp_path, monkeypatch)

    class ForeignHostLabel(str):
        def strip(self, chars: str | None = None) -> str:
            del chars
            raise AssertionError("foreign host identity string hook invoked")

    monkeypatch.setattr(
        target_echo_reference.platform, "platform", lambda: ForeignHostLabel("host")
    )
    with pytest.raises(
        target_echo_reference.TargetEchoStudyError, match="host identity requires"
    ):
        _ = target_echo_reference._prepare_context(tmp_path, tmp_path)


def test_optional_rss_workspace_failure_is_typed_and_cleans_partial_study(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A failed optional receipt directory must not strand a study skeleton."""
    emitter = tmp_path / "emitter"
    runner = tmp_path / "runner"
    _ = emitter.write_bytes(b"emitter")
    _ = runner.write_bytes(b"runner")
    profile = target_echo_reference._ROOT / "malbolge.json"
    _ = (tmp_path / "malbolge.json").write_bytes(profile.read_bytes())
    temp_root = tmp_path / ".temp"
    temp_root.mkdir()
    monkeypatch.setattr(target_echo_reference, "_ROOT", tmp_path)
    monkeypatch.setattr(target_echo_reference, "_TEMP", temp_root)
    monkeypatch.setattr(target_echo_reference, "_commit", lambda: "a" * 40)
    monkeypatch.setattr(
        target_echo_reference.target_process,
        "require_child_rss_measurement",
        lambda: None,
    )
    original_mkdir = type(tmp_path).mkdir

    def refuse_rss(path: Path, *args: Any, **kwargs: Any) -> None:
        if path.name == "rss" and path.parent.name.startswith("arena-target-echo-"):
            message = "injected optional RSS directory failure"
            raise PermissionError(message)
        original_mkdir(path, *args, **kwargs)

    monkeypatch.setattr(type(tmp_path), "mkdir", refuse_rss)
    plan = target_echo_reference.StudyPlan(
        pairs=(1,),
        trials=1,
        input_mode=target_echo_reference.PATTERNED_MODE,
        measure_steps=True,
        layout_mode=target_echo_reference.FORWARD_SKIP_LAYOUT,
        measure_verifier=True,
        verifier_mode=target_echo_reference.REPLAY_VERIFIER_MODE,
        limit_child_resources=True,
        measure_child_rss=True,
        retain_rss_stages=True,
    )
    with pytest.raises(
        target_echo_reference.TargetEchoStudyError, match=WORKSPACE_ERROR
    ) as failure:
        _ = target_echo_reference.run_study(plan, emitter=emitter, runner=runner)
    assert isinstance(failure.value.__cause__, PermissionError)
    assert not list(temp_root.glob("arena-target-echo-*"))


@pytest.mark.skipif(not hasattr(os, "symlink"), reason="requires symlinks")
def test_redirected_study_workspace_parent_refuses_external_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A linked .temp cannot redirect retained evidence outside the checkout."""
    root = tmp_path / "root"
    outside = tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    emitter = root / "emitter"
    runner = root / "runner"
    _ = emitter.write_bytes(b"emitter")
    _ = runner.write_bytes(b"runner")
    profile = target_echo_reference._ROOT / "malbolge.json"
    _ = (root / "malbolge.json").write_bytes(profile.read_bytes())
    linked_temp = root / ".temp"
    linked_temp.symlink_to(outside, target_is_directory=True)
    monkeypatch.setattr(target_echo_reference, "_ROOT", root)
    monkeypatch.setattr(target_echo_reference, "_TEMP", linked_temp)
    monkeypatch.setattr(target_echo_reference, "_commit", lambda: "a" * 40)

    with pytest.raises(
        target_echo_reference.TargetEchoStudyError,
        match=r"repository \.temp directory",
    ):
        _ = target_echo_reference._prepare_context(emitter, runner)
    assert not list(outside.iterdir())


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
        target_echo_reference.TargetEchoStudyError,
        match="target echo executable identity changed",
    ):
        target_echo_reference._tool_identity(emitter, runner)


@pytest.mark.parametrize("operation", ["lstat", "is_file", "is_symlink"])
@pytest.mark.parametrize(
    "error_type", [ValueError, RuntimeError, IndexError, OverflowError, LookupError]
)
def test_target_echo_executable_admission_types_host_inspection_faults(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    *,
    operation: str,
    error_type: type[Exception],
) -> None:
    """Unexpected native path-inspection failures cannot leak raw errors."""
    executable = tmp_path / "target-emitter"
    _ = executable.write_bytes(b"real-compiler")
    original = getattr(Path, operation)

    def faulty(path: Path) -> object:
        if path == executable:
            message = "injected executable path inspection failure"
            raise error_type(message)
        return original(path)

    monkeypatch.setattr(target_echo_reference.Path, operation, faulty)
    with pytest.raises(
        target_echo_reference.TargetEchoStudyError,
        match="executable is missing",
    ) as failure:
        _ = target_echo_reference._admit_executable(executable)
    assert isinstance(failure.value.__cause__, error_type)


def test_target_executable_inspection_never_formats_foreign_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A custom ordinary path dependency failure stays a typed rejection."""
    executable = tmp_path / "target-emitter"
    _ = executable.write_bytes(b"real-compiler")

    class HostilePathFailure(Exception):
        def __str__(self) -> str:
            raise AssertionError("foreign path error formatter executed")

    error = HostilePathFailure("untrusted path inspection failure")
    original = Path.is_file

    def fail_file(path: Path) -> bool:
        if path == executable:
            raise error
        return original(path)

    monkeypatch.setattr(target_echo_reference.Path, "is_file", fail_file)
    with pytest.raises(
        target_echo_reference.TargetEchoStudyError, match="executable is missing"
    ) as caught:
        _ = target_echo_reference._admit_executable(executable)
    assert caught.value.__cause__ is error


@pytest.mark.parametrize("field", ["emitter", "runner"])
@pytest.mark.parametrize(
    "invalid",
    [None, "/tmp/pretend-tool", 0, False, object()],
)
def test_producer_rejects_non_path_executables_before_file_access(
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    invalid: object,
) -> None:
    """Foreign direct tool arguments do not escape the typed API boundary."""

    def forbidden(*args: object, **kwargs: object) -> None:
        _ = (args, kwargs)
        message = "foreign tool path reached local study setup"
        raise AssertionError(message)

    monkeypatch.setattr(target_echo_reference.tempfile, "mkdtemp", forbidden)
    with pytest.raises(
        target_echo_reference.TargetEchoStudyError, match="exact native Path"
    ):
        if field == "emitter":
            target_echo_reference.run_study(
                target_echo_reference.StudyPlan((1,), 1),
                emitter=cast("Path", invalid),
            )
        else:
            target_echo_reference.run_study(
                target_echo_reference.StudyPlan((1,), 1),
                runner=cast("Path", invalid),
            )


def test_producer_rejects_path_subclass_before_tool_admission(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An overridden path object cannot control which executable is hashed."""

    class SpoofedPath(type(Path())):
        """A caller-owned native path subclass, not a trusted Path."""

    emitter = tmp_path / "real-emitter"
    _ = emitter.write_bytes(b"nonempty-tool")

    def forbidden(*args: object, **kwargs: object) -> None:
        _ = (args, kwargs)
        message = "foreign path subclass reached study setup"
        raise AssertionError(message)

    monkeypatch.setattr(target_echo_reference.tempfile, "mkdtemp", forbidden)
    with pytest.raises(
        target_echo_reference.TargetEchoStudyError, match="exact native Path"
    ):
        target_echo_reference.run_study(
            target_echo_reference.StudyPlan((1,), 1),
            emitter=SpoofedPath(emitter),
        )


def test_oversized_sparse_emitter_rejects_before_tool_identity_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An oversized tool cannot force unbounded producer fingerprint work."""
    emitter = tmp_path / "oversized-emitter"
    runner = tmp_path / "runner"
    _ = emitter.write_bytes(b"x")
    _ = runner.write_bytes(b"runner")
    with emitter.open("r+b") as handle:
        handle.truncate(target_echo_reference.MAX_TOOL_BYTES)
    assert target_echo_reference._admit_executable(emitter) == emitter
    with emitter.open("r+b") as handle:
        handle.truncate(target_echo_reference.MAX_TOOL_BYTES + 1)
    with pytest.raises(target_echo_reference.TargetEchoStudyError, match="128 MiB"):
        _ = target_echo_reference._admit_executable(emitter)

    def forbid_open(*args: object, **kwargs: object) -> int:
        _ = (args, kwargs)
        message = "producer tried to hash an oversized sparse tool"
        raise AssertionError(message)

    monkeypatch.setattr(target_echo_reference.os, "open", forbid_open)
    with pytest.raises(target_echo_reference.TargetEchoStudyError, match="128 MiB"):
        _ = target_echo_reference._tool_identity(emitter, runner)


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
    original_read = target_echo_reference.os.read
    original_close = target_echo_reference.os.close

    def broken_read(fd: int, size: int) -> bytes:
        if read_fails:
            raise read_error
        return original_read(fd, size)

    def broken_close(fd: int) -> None:
        original_close(fd)
        raise close_error

    with monkeypatch.context() as patch:
        patch.setattr(target_echo_reference.os, "read", broken_read)
        patch.setattr(target_echo_reference.os, "close", broken_close)
        with pytest.raises(target_echo_reference.TargetEchoStudyError) as observed:
            _ = target_echo_reference._tool_identity(emitter, runner)
    if read_fails:
        assert observed.value.__cause__ is read_error
        assert any("cleanup" in note for note in read_error.__notes__)
    else:
        assert observed.value.__cause__ is close_error


@pytest.mark.parametrize("site", ["lstat", "open", "fstat", "read", "close"])
@pytest.mark.parametrize(
    "failure_type",
    [ValueError, RuntimeError, TypeError, AttributeError, IndexError, _UnexpectedHostFault],
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
    original_close = target_echo_reference.os.close
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
            patch.setattr(target_echo_reference.os, site, bad_host)
        with pytest.raises(
            target_echo_reference.TargetEchoStudyError, match="executable identity"
        ) as caught:
            _ = target_echo_reference._tool_identity(emitter, runner)
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
        patch.setattr(target_echo_reference.os, "read", altered_read)
        with pytest.raises(
            target_echo_reference.TargetEchoStudyError, match="executable identity"
        ):
            _ = target_echo_reference._tool_identity(emitter, runner)


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
    original_read = target_echo_reference.os.read

    def altered_read(fd: int, size: int) -> bytes:
        if size == 1:
            return cast("bytes", trailer)
        return original_read(fd, size)

    with monkeypatch.context() as patch:
        patch.setattr(target_echo_reference.os, "read", altered_read)
        with pytest.raises(
            target_echo_reference.TargetEchoStudyError, match="executable identity"
        ):
            _ = target_echo_reference._tool_identity(emitter, runner)


@pytest.mark.parametrize("failure_type", [ValueError, RuntimeError, IndexError, _UnexpectedHostFault])
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
    original_close = target_echo_reference.os.close

    def bad_read(fd: int, size: int) -> bytes:
        del fd, size
        raise primary

    def bad_close(fd: int) -> None:
        original_close(fd)
        raise secondary

    with monkeypatch.context() as patch:
        patch.setattr(target_echo_reference.os, "read", bad_read)
        patch.setattr(target_echo_reference.os, "close", bad_close)
        with pytest.raises(
            target_echo_reference.TargetEchoStudyError, match="executable identity"
        ) as caught:
            _ = target_echo_reference._tool_identity(emitter, runner)
    assert caught.value.__cause__ is primary
    assert any("cleanup" in note for note in primary.__notes__)


@pytest.mark.parametrize("failure_type", [OSError, ValueError, RuntimeError])
def test_tool_fingerprint_close_bypasses_foreign_primary_note_hook(
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
    original_close = target_echo_reference.os.close

    def bad_read(fd: int, size: int) -> bytes:
        del fd, size
        raise primary

    def bad_close(fd: int) -> None:
        original_close(fd)
        raise secondary

    with monkeypatch.context() as patch:
        patch.setattr(target_echo_reference.os, "read", bad_read)
        patch.setattr(target_echo_reference.os, "close", bad_close)
        with pytest.raises(
            target_echo_reference.TargetEchoStudyError, match="executable identity"
        ) as caught:
            _ = target_echo_reference._tool_identity(emitter, runner)

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
    original_read = target_echo_reference.os.read

    def partial_read(fd: int, size: int) -> bytes:
        return original_read(fd, min(size, 3))

    with monkeypatch.context() as patch:
        patch.setattr(target_echo_reference.os, "read", partial_read)
        actual = target_echo_reference._tool_identity(emitter, runner)
    assert actual == "local-compiler-vm-sha256:" + expected.hexdigest()


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
    assert target_echo_reference._tool_identity(emitter, runner) == (
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
    assert target_echo_reference._admit_executable(emitter) == emitter
    emitter.unlink()
    emitter.symlink_to(foreign)
    with pytest.raises(
        target_echo_reference.TargetEchoStudyError,
        match="target echo executable identity changed",
    ):
        target_echo_reference._tool_identity(emitter, runner)


@pytest.mark.parametrize(
    "receipt",
    [
        b"",
        b"malbolge-steps-v1:\n",
        b"malbolge-steps-v1:01\n",
        b"malbolge-steps-v1:-1\n",
        b"malbolge-steps-v1:1.0\n",
        b"malbolge-steps-v1:1\r\n",
        b"malbolge-steps-v1:3\nmalbolge-steps-v1:4\n",
        b"malbolge-steps-v1:3\nnoise",
        b"malbolge-steps-v1:999999999999999999999\n",
        b"malbolge-steps-v1:\xff\n",
    ],
)
def test_vm_step_receipt_rejects_ambiguous_or_unbounded_counter(
    receipt: bytes,
) -> None:
    """No extra diagnostics or alternate decimal spellings certify steps."""
    with pytest.raises(
        target_echo_reference.TargetEchoStudyError,
        match=r"step receipt|step count",
    ):
        target_echo_reference._parse_step_receipt(receipt)


def test_vm_step_receipt_admits_one_canonical_decimal() -> None:
    """Canonical reporter wire bytes remain reproducible."""
    assert (
        target_echo_reference._parse_step_receipt(b"malbolge-steps-v1:3\n")
        == EXPECTED_STEP_RECEIPT
    )


def test_emitter_rejects_foreign_source_receipt_before_graphical_check(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A substituted reader cannot forge emitter length or graphical bytes."""

    class ForgedSource(bytes):
        def __len__(self) -> int:
            pytest.fail("foreign emitter source length executed")

    path = tmp_path / "candidate.malbolge"
    _ = path.write_bytes(b"!")
    context = _synthetic_target_context(tmp_path, site="raw")
    monkeypatch.setattr(target_echo_reference, "_ROOT", tmp_path)
    monkeypatch.setattr(
        target_echo_reference,
        "_emit_attempt",
        lambda *_args, **_kwargs: sp.CompletedProcess([], 0, b"", b""),
    )
    monkeypatch.setattr(
        evidence,
        "read_bounded_regular",
        lambda *_args, **_kwargs: ForgedSource(b"!"),
    )
    with pytest.raises(
        target_echo_reference.TargetEchoStudyError,
        match="exact nonempty bounded bytes",
    ):
        target_echo_reference._classify_attempt(path, context, ["input"], pairs=1)


@pytest.mark.parametrize(
    "invalid",
    [None, bytearray(b"!"), b"", b"!" * (target_echo_reference.MAX_TARGET_BYTES + 1)],
    ids=["missing", "mutable", "empty", "oversized"],
)
def test_timed_source_verifier_rejects_reader_receipt_before_auditor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, invalid: object
) -> None:
    """A malformed source receipt cannot be passed to independent verification."""
    monkeypatch.setattr(target_echo_reference, "_ROOT", tmp_path)
    monkeypatch.setattr(
        evidence,
        "read_bounded_regular",
        lambda *_args, **_kwargs: cast("bytes", invalid),
    )

    def forbidden_audit(*_args: object, **_kwargs: object) -> None:
        pytest.fail("unvalidated target source reached the auditor")

    monkeypatch.setattr(
        target_echo_audit, "check_forward_candidate_source", forbidden_audit
    )
    with pytest.raises(
        target_echo_reference.TargetEchoStudyError,
        match="exact nonempty bounded bytes",
    ):
        target_echo_reference._timed_source_verifier(tmp_path / "source.malbolge", 1, "direct")


def test_retained_study_rejects_foreign_bytes_decode_before_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Retained evidence hash parity cannot authorize a foreign decoder hook."""

    class ForgedSource(bytes):
        def decode(self, encoding: str = "utf-8", errors: str = "strict") -> str:
            del encoding, errors
            pytest.fail("foreign retained-study decode executed")

    raw = ForgedSource(json.dumps(sample_study(tmp_path)).encode("utf-8"))
    monkeypatch.setattr(target_echo_reference, "_ROOT", tmp_path)
    monkeypatch.setattr(
        target_echo_audit,
        "audit",
        lambda _relative: {"retained_study_sha256": sha256(raw).hexdigest()},
    )
    monkeypatch.setattr(evidence, "read_bounded_regular", lambda *_a, **_k: raw)
    with pytest.raises(
        target_echo_reference.TargetEchoStudyError,
        match="exact nonempty bounded bytes",
    ):
        target_echo_reference._audit_retained_study(tmp_path / "study.json")


def test_retained_study_rejects_oversized_reader_before_sha256(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An injected reader cannot bypass the retained study's sixteen-MiB cap."""
    monkeypatch.setattr(target_echo_reference, "_ROOT", tmp_path)
    monkeypatch.setattr(
        target_echo_audit,
        "audit",
        lambda _relative: {"retained_study_sha256": "0" * 64},
    )
    monkeypatch.setattr(
        evidence,
        "read_bounded_regular",
        lambda *_args, **_kwargs: b"x" * (target_echo_audit.MAX_STUDY_BYTES + 1),
    )

    def forbidden_hash(_raw: bytes) -> None:
        pytest.fail("oversized target study reached hashing")

    monkeypatch.setattr(target_echo_reference, "sha256", forbidden_hash)
    with pytest.raises(
        target_echo_reference.TargetEchoStudyError,
        match="exact nonempty bounded bytes",
    ):
        target_echo_reference._audit_retained_study(tmp_path / "study.json")


@pytest.mark.parametrize(
    "invalid",
    [None, "digest", {"retained_study_sha256": None}, {"retained_study_sha256": "a" * 63}],
    ids=["missing", "text", "missing-digest", "short-digest"],
)
def test_retained_study_rejects_invalid_audit_receipt_before_reader(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, invalid: object
) -> None:
    """A forged audit result must not authorize a new source read."""
    monkeypatch.setattr(target_echo_reference, "_ROOT", tmp_path)
    monkeypatch.setattr(
        target_echo_audit,
        "audit",
        lambda _relative: cast("dict[str, object]", invalid),
    )

    def forbidden_reader(*_args: object, **_kwargs: object) -> None:
        pytest.fail("invalid audit receipt reached retained source reader")

    monkeypatch.setattr(evidence, "read_bounded_regular", forbidden_reader)
    with pytest.raises(
        target_echo_reference.TargetEchoStudyError,
        match="exact native retained SHA-256",
    ):
        target_echo_reference._audit_retained_study(tmp_path / "study.json")


def test_retained_study_rejects_foreign_audit_mapping_before_item_hooks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Dependency-owned mapping methods cannot impersonate source agreement."""

    class ForeignAudit(dict[str, str]):
        def __getitem__(self, key: str) -> str:
            del key
            pytest.fail("foreign auditor mapping hook executed")

    raw = b'{}'
    monkeypatch.setattr(target_echo_reference, "_ROOT", tmp_path)
    monkeypatch.setattr(
        target_echo_audit,
        "audit",
        lambda _relative: ForeignAudit({"retained_study_sha256": sha256(raw).hexdigest()}),
    )
    monkeypatch.setattr(evidence, "read_bounded_regular", lambda *_a, **_k: raw)
    with pytest.raises(
        target_echo_reference.TargetEchoStudyError,
        match="exact native retained SHA-256",
    ):
        target_echo_reference._audit_retained_study(tmp_path / "study.json")


def test_retained_study_rejects_foreign_audit_digest_before_equality(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A str-subclass digest cannot forge agreement via equality dispatch."""

    class ForeignDigest(str):
        def __eq__(self, other: object) -> bool:
            del other
            pytest.fail("foreign retained digest comparison executed")

        __hash__ = str.__hash__

    raw = b'{}'
    monkeypatch.setattr(target_echo_reference, "_ROOT", tmp_path)
    monkeypatch.setattr(
        target_echo_audit,
        "audit",
        lambda _relative: {"retained_study_sha256": ForeignDigest(sha256(raw).hexdigest())},
    )
    monkeypatch.setattr(evidence, "read_bounded_regular", lambda *_a, **_k: raw)
    with pytest.raises(
        target_echo_reference.TargetEchoStudyError,
        match="exact native retained SHA-256",
    ):
        target_echo_reference._audit_retained_study(tmp_path / "study.json")


@pytest.mark.parametrize("tamper_after_audit", [False, True])
def test_publisher_uses_exact_audited_study_bytes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    tamper_after_audit: bool,
) -> None:
    """A later valid JSON rewrite cannot replace independently audited bytes."""
    original = sample_study(tmp_path)
    path = tmp_path / STUDY_LEAF
    raw = (json.dumps(original) + "\n").encode("utf-8")
    _ = path.write_bytes(raw)
    expected_hash = sha256(raw).hexdigest()
    monkeypatch.setattr(target_echo_reference, "_ROOT", tmp_path)

    def fake_audit(relative: str) -> dict[str, Any]:
        assert relative == STUDY_LEAF
        if tamper_after_audit:
            altered = json.loads(raw)
            altered["study"]["id"] = "valid-but-not-audited"
            _ = path.write_text(json.dumps(altered), encoding="utf-8")
        return {"retained_study_sha256": expected_hash}

    monkeypatch.setattr(target_echo_audit, "audit", fake_audit)
    if tamper_after_audit:
        with pytest.raises(
            target_echo_reference.TargetEchoStudyError,
            match="changed after independent audit",
        ):
            target_echo_reference._audit_retained_study(path)
    else:
        assert target_echo_reference._audit_retained_study(path) == original


@pytest.fixture
def live_echo() -> Iterator[tuple[Path, dict]]:
    """Run a short real target study and remove only its owned evidence.

    Yields:
        Retained study directory and admitted study document.

    """
    with tempfile.TemporaryDirectory(
        dir=target_echo_reference._TEMP,
        prefix="arena-target-test-tools-",
    ) as tool_directory:
        emitter = Path(tool_directory) / "malbolge_layout"
        runner = Path(tool_directory) / "malbolge"
        # Private inodes avoid shared tool ctime churn as other tests create
        # and remove hardlinks, without relaxing production identity checks.
        shutil.copy2(target_echo_reference.DEFAULT_EMITTER, emitter)
        shutil.copy2(target_echo_reference.DEFAULT_RUNNER, runner)
        directory, document = target_echo_reference.run_study(
            target_echo_reference.StudyPlan((1, 4), 2),
            emitter=emitter,
            runner=runner,
        )
        try:
            yield directory, document
        finally:
            shutil.rmtree(directory)


@pytest.mark.skipif(
    not target_echo_reference.DEFAULT_EMITTER.is_file()
    or not target_echo_reference.DEFAULT_RUNNER.is_file(),
    reason="built Malbolge CLI binaries not present",
)
def test_real_target_programs_produce_complete_paired_arena_evidence(
    live_echo: tuple[Path, dict],
) -> None:
    """Real classic programs pass independently checked VM EOF and raw links."""
    directory, document = live_echo
    rows = document["observations"]
    assert len(rows) == EXPECTED_OBSERVATIONS
    assert all(row["outcome"] == analyze.VERIFIED for row in rows)
    assert all(row["verifier_verdict"] == analyze.ACCEPTED for row in rows)
    assert {row["case"]["difficulty"] for row in rows} == {1, 4}
    assert (directory / "study.json").is_file()
    evidence_check = evidence.validate_links(
        document,
        target_echo_reference._ROOT,
        policy=evidence.EvidencePolicy(
            require_raw_rows=True,
            require_trial_run_identity=True,
            require_budget_agreement=True,
        ),
    )
    assert evidence_check["raw_rows_matched"] == len(rows)
    assert evidence_check["trial_run_links_checked"] == len(rows)
    report = analyze.analyze(document)
    assert len(report["pareto_frontiers"]) == EXPECTED_LEVELS
    assert all(
        pair["paired_trials"] == EXPECTED_TRIALS
        for pair in report["paired_baseline_comparisons"]
    )
    for pair_count in (1, 4):
        direct = next(
            row
            for row in rows
            if row["algorithm"] == target_echo_reference.BASELINE
            and row["case"]["difficulty"] == pair_count
        )
        padded = next(
            row
            for row in rows
            if row["algorithm"] == target_echo_reference.CANDIDATE
            and row["case"]["difficulty"] == pair_count
        )
        assert direct["metrics"]["artifact_bytes"] == 2 * pair_count + 1
        assert padded["metrics"]["artifact_bytes"] == 3 * pair_count + 1
        for row in (direct, padded):
            stem = f"{row['algorithm']}-pairs-{pair_count}-trial-{row['trial']}"
            source = (directory / "candidates" / f"{stem}.malbolge").read_bytes()
            assert len(source) == row["metrics"]["artifact_bytes"]
            assert all(GRAPHICAL_LOW <= byte <= GRAPHICAL_HIGH for byte in source)


@pytest.mark.skipif(
    not target_echo_reference.DEFAULT_EMITTER.is_file()
    or not target_echo_reference.DEFAULT_RUNNER.is_file(),
    reason="built Malbolge binaries not available",
)
@pytest.mark.parametrize("tamper", ["raw", "manifest"])
def test_retained_target_evidence_tamper_fails_closed(
    live_echo: tuple[Path, dict],
    tamper: str,
) -> None:
    """Edited trial receipts cannot silently drift from raw links."""
    directory, document = live_echo
    first = document["observations"][0]
    if tamper == RAW_TAMPER:
        name = first["raw_sample"].rsplit("/", maxsplit=1)[-1]
        path = directory / "raw" / name
        path.write_bytes(path.read_bytes() + b"\n")
    else:
        name = first["experiment_manifest"].rsplit("/", maxsplit=1)[-1]
        path = directory / "runs" / name
        content = path.read_text(encoding="utf-8")
        assert ORIGINAL_TRIAL in content
        path.write_text(content.replace(ORIGINAL_TRIAL, "trial = 999"))
    with pytest.raises(
        evidence.EvidenceError, match=r"arena_trial|linked arena evidence"
    ):
        evidence.validate_links(
            document,
            target_echo_reference._ROOT,
            policy=evidence.EvidencePolicy(
                require_raw_rows=True,
                require_trial_run_identity=True,
                require_budget_agreement=True,
            ),
        )


@pytest.mark.skipif(
    not target_echo_reference.DEFAULT_EMITTER.is_file()
    or not target_echo_reference.DEFAULT_RUNNER.is_file(),
    reason="built Malbolge binaries not available",
)
def test_producer_rejects_forged_graphical_source_and_vm_agreement(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A fake source and fake expected stdout cannot claim target emission."""
    directories: list[Path] = []
    real_prepare = target_echo_reference._prepare_context

    def recorded(emitter: Path, runner: Path) -> target_echo_reference._Context:
        context = real_prepare(emitter, runner)
        directories.append(context.directory)
        return context

    def forged(command: list[str]) -> sp.CompletedProcess[bytes]:
        if OUTPUT_ARGUMENT in command:
            output = Path(command[command.index(OUTPUT_ARGUMENT) + 1])
            operations = command[command.index("--") + 1 :]
            output.write_bytes(b"!" * len(operations))
            return sp.CompletedProcess(command, 0, stdout=b"", stderr=b"")
        return sp.CompletedProcess(
            command,
            0,
            stdout=bytes([target_echo_reference.CLASSIC_EOF_BYTE]),
            stderr=b"",
        )

    monkeypatch.setattr(target_echo_reference, "_prepare_context", recorded)
    monkeypatch.setattr(target_echo_reference, "_invoke", forged)
    try:
        with pytest.raises(
            target_echo_reference.TargetEchoStudyError,
            match="source instruction",
        ):
            target_echo_reference.run_study(target_echo_reference.StudyPlan((1,), 1))
    finally:
        for directory in directories:
            shutil.rmtree(directory)


@pytest.mark.skipif(
    not target_echo_reference.DEFAULT_EMITTER.is_file(),
    reason="built Malbolge layout emitter missing",
)
def test_missing_counter_with_correct_vm_output_is_instrumentation_failure(
    tmp_path: Path,
) -> None:
    """Failure to report VM steps is tool failure, not a guest rejection."""
    runner = tmp_path / "no-counter-vm"
    runner.write_text(
        f"#!{sys.executable}\nimport sys\nsys.stdout.buffer.write(bytes([0,168]))\n"
    )
    runner.chmod(0o700)
    with tempfile.TemporaryDirectory(
        dir=target_echo_reference._TEMP, prefix="arena-steps-test-tools-"
    ) as tool_directory:
        emitter = Path(tool_directory) / "malbolge_layout"
        shutil.copy2(target_echo_reference.DEFAULT_EMITTER, emitter)
        directory, document = target_echo_reference.run_study(
            target_echo_reference.StudyPlan(
                (1,),
                1,
                target_echo_reference.PATTERNED_MODE,
                measure_steps=True,
            ),
            emitter=emitter,
            runner=runner,
        )
    try:
        assert all(row["outcome"] == TOOL_FAILED for row in document["observations"])
        assert all(
            RUNTIME_STEPS not in row["metrics"] for row in document["observations"]
        )
        assert all(
            ARTIFACT_BYTES not in row["metrics"] for row in document["observations"]
        )
    finally:
        shutil.rmtree(directory)


@pytest.mark.skipif(
    not target_echo_reference.DEFAULT_EMITTER.is_file(),
    reason="built Malbolge layout emitter missing",
)
def test_wrong_external_vm_step_receipt_does_not_publish_success(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Plausible stdout and consistent reported counters cannot bypass audit."""
    runner = tmp_path / "forged-counter-vm"
    runner.write_text(
        f"#!{sys.executable}\n"
        "import sys\n"
        "sys.stdout.buffer.write(bytes([0,168]))\n"
        "sys.stderr.buffer.write(b'malbolge-steps-v1:999\\n')\n"
    )
    runner.chmod(0o700)
    directories: list[Path] = []
    original = target_echo_reference._prepare_context

    def capture_context(emitter: Path, vm: Path) -> target_echo_reference._Context:
        context = original(emitter, vm)
        directories.append(context.directory)
        return context

    monkeypatch.setattr(target_echo_reference, "_prepare_context", capture_context)
    with tempfile.TemporaryDirectory(
        dir=target_echo_reference._TEMP,
        prefix="arena-steps-test-tools-",
    ) as tool_directory:
        emitter = Path(tool_directory) / "malbolge_layout"
        shutil.copy2(target_echo_reference.DEFAULT_EMITTER, emitter)
        try:
            with pytest.raises(
                target_echo_reference.TargetEchoStudyError,
                match="runtime step claim",
            ):
                target_echo_reference.run_study(
                    target_echo_reference.StudyPlan(
                        (1,),
                        1,
                        target_echo_reference.PATTERNED_MODE,
                        measure_steps=True,
                    ),
                    emitter=emitter,
                    runner=runner,
                )
            assert len(directories) == 1
            rows = json.loads(
                (directories[0] / "study.json").read_text(encoding="utf-8")
            )["observations"]
            assert all(row["outcome"] == analyze.VERIFIED for row in rows)
            assert all(row["metrics"]["runtime_steps"] == FORGED_COUNT for row in rows)
        finally:
            for directory in directories:
                shutil.rmtree(directory)


@pytest.mark.skipif(
    not target_echo_reference.DEFAULT_EMITTER.is_file(),
    reason="built Malbolge layout emitter missing",
)
def test_flooding_vm_is_recorded_as_tool_failure_not_verified(
    tmp_path: Path,
) -> None:
    """Successful child exit with huge stdout must not certify a trial."""
    script = tmp_path / "flood-runner"
    script.write_text(f"#!{sys.executable}\nimport os\nos.write(1, b'Z' * 8192)\n")
    script.chmod(0o700)
    with tempfile.TemporaryDirectory(
        dir=target_echo_reference._TEMP,
        prefix="arena-target-test-tools-",
    ) as tool_directory:
        emitter = Path(tool_directory) / "malbolge_layout"
        shutil.copy2(target_echo_reference.DEFAULT_EMITTER, emitter)
        directory, document = target_echo_reference.run_study(
            target_echo_reference.StudyPlan((1,), 1),
            emitter=emitter,
            runner=script,
        )
    try:
        assert all(row["outcome"] == TOOL_FAILED for row in document["observations"])
        assert all(
            ARTIFACT_BYTES not in row["metrics"] for row in document["observations"]
        )
        assert not analyze.analyze(document)["pareto_frontiers"][0]["algorithms"]
    finally:
        shutil.rmtree(directory)


@pytest.mark.skipif(
    not target_echo_reference.DEFAULT_EMITTER.is_file()
    or not target_echo_reference.DEFAULT_RUNNER.is_file(),
    reason="built Malbolge CLI binaries not available",
)
def test_patterned_mode_records_true_non_eof_input_and_final_eof() -> None:
    """Real target measurements use actual NUL/high-bit input and then EOF."""
    with tempfile.TemporaryDirectory(
        dir=target_echo_reference._TEMP,
        prefix="arena-patterned-test-tools-",
    ) as tool_directory:
        emitter = Path(tool_directory) / "malbolge_layout"
        runner = Path(tool_directory) / "malbolge"
        shutil.copy2(target_echo_reference.DEFAULT_EMITTER, emitter)
        shutil.copy2(target_echo_reference.DEFAULT_RUNNER, runner)
        directory, document = target_echo_reference.run_study(
            target_echo_reference.StudyPlan(
                (1, 4, 16, 64), 1, target_echo_reference.PATTERNED_MODE
            ),
            emitter=emitter,
            runner=runner,
        )
        try:
            rows = document["observations"]
            assert len(rows) == EXPECTED_OBSERVATIONS
            assert all(row["outcome"] == analyze.VERIFIED for row in rows)
            assert all(row["verifier_verdict"] == analyze.ACCEPTED for row in rows)
            assert document["study"]["id"] == target_echo_reference.PATTERNED_STUDY
            assert (
                len(analyze.analyze(document)["pareto_frontiers"])
                == PATTERNED_LEVEL_COUNT
            )
            assert {
                row["algorithm"]: row["metrics"][ARTIFACT_BYTES]
                for row in rows
                if row["case"]["difficulty"] == PATTERNED_MAX_PAIR_COUNT
            } == {
                target_echo_reference.BASELINE: PATTERNED_DIRECT_BYTES,
                target_echo_reference.CANDIDATE: PATTERNED_PADDED_BYTES,
            }
        finally:
            shutil.rmtree(directory)


@pytest.mark.skipif(
    not target_echo_reference.DEFAULT_EMITTER.is_file(),
    reason="built Malbolge layout emitter missing",
)
def test_patterned_vm_that_ignores_input_retains_verifier_rejection(
    tmp_path: Path,
) -> None:
    """EOF-only output must not certify the varied-byte guest program."""
    runner = tmp_path / "eof-only-runner"
    runner.write_bytes(b"#!/bin/sh\nprintf 'Z'\n")
    runner.chmod(0o700)
    with tempfile.TemporaryDirectory(
        dir=target_echo_reference._TEMP,
        prefix="arena-patterned-test-tools-",
    ) as tool_directory:
        emitter = Path(tool_directory) / "malbolge_layout"
        shutil.copy2(target_echo_reference.DEFAULT_EMITTER, emitter)
        directory, document = target_echo_reference.run_study(
            target_echo_reference.StudyPlan(
                (1,), 1, target_echo_reference.PATTERNED_MODE
            ),
            emitter=emitter,
            runner=runner,
        )
    try:
        assert all(
            row["outcome"] == analyze.VERIFIER_REJECTED
            for row in document["observations"]
        )
        assert all(
            ARTIFACT_BYTES not in row["metrics"] for row in document["observations"]
        )
        assert analyze.analyze(document)["pareto_frontiers"][0]["algorithms"] == []
    finally:
        shutil.rmtree(directory)


@pytest.mark.skipif(
    not target_echo_reference.DEFAULT_EMITTER.is_file()
    or not target_echo_reference.DEFAULT_RUNNER.is_file(),
    reason="built Malbolge CLI binaries not available",
)
def test_changed_producer_pattern_fails_independent_oracle_even_if_linked(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Self-consistent producer input drift cannot pass the fixed auditor."""
    original_pattern = target_echo_reference.PATTERN_BYTES
    monkeypatch.setattr(
        target_echo_reference,
        "PATTERN_BYTES",
        (1, *original_pattern[1:]),
    )
    original_prepare = target_echo_reference._prepare_context
    directories: list[Path] = []

    def capture_context(emitter: Path, runner: Path) -> target_echo_reference._Context:
        context = original_prepare(emitter, runner)
        directories.append(context.directory)
        return context

    monkeypatch.setattr(target_echo_reference, "_prepare_context", capture_context)
    with tempfile.TemporaryDirectory(
        dir=target_echo_reference._TEMP,
        prefix="arena-patterned-test-tools-",
    ) as tool_directory:
        emitter = Path(tool_directory) / "malbolge_layout"
        runner = Path(tool_directory) / "malbolge"
        shutil.copy2(target_echo_reference.DEFAULT_EMITTER, emitter)
        shutil.copy2(target_echo_reference.DEFAULT_RUNNER, runner)
        try:
            with pytest.raises(
                target_echo_reference.TargetEchoStudyError,
                match="fixed echo case",
            ):
                target_echo_reference.run_study(
                    target_echo_reference.StudyPlan(
                        (1,), 1, target_echo_reference.PATTERNED_MODE
                    ),
                    emitter=emitter,
                    runner=runner,
                )
            assert len(directories) == 1
            document = analyze.parse_document(
                (directories[0] / "study.json").read_text(encoding="utf-8")
            )
            checked = evidence.validate_links(
                document,
                target_echo_reference._ROOT,
                policy=evidence.EvidencePolicy(
                    require_raw_rows=True,
                    require_trial_run_identity=True,
                    require_budget_agreement=True,
                ),
            )
            assert checked["raw_rows_matched"] == len(document["observations"])
        finally:
            for directory in directories:
                shutil.rmtree(directory)


@pytest.mark.skipif(
    not target_echo_reference.DEFAULT_EMITTER.is_file()
    or not target_echo_reference.DEFAULT_RUNNER.is_file(),
    reason="built Malbolge tools required",
)
@pytest.mark.parametrize("expected", [analyze.VERIFIER_REJECTED, "tool_failed"])
def test_timed_independent_verifier_failure_cannot_record_verified_cost(
    expected: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verification rejection and I/O failure retain distinct outcomes."""
    original = target_echo_reference._timed_source_verifier

    def selective_failure(path: Path, pairs: int, algorithm: str) -> int:
        if algorithm == target_echo_reference.SKIP:
            if expected == analyze.VERIFIER_REJECTED:
                raise target_echo_audit.TargetEchoAuditError
            raise OSError
        return original(path, pairs, algorithm)

    monkeypatch.setattr(
        target_echo_reference, "_timed_source_verifier", selective_failure
    )
    with tempfile.TemporaryDirectory(
        dir=target_echo_reference._TEMP,
        prefix="arena-verifier-failure-test-",
    ) as tools:
        emitter = Path(tools) / "malbolge_layout"
        runner = Path(tools) / "malbolge"
        shutil.copy2(target_echo_reference.DEFAULT_EMITTER, emitter)
        shutil.copy2(target_echo_reference.DEFAULT_RUNNER, runner)
        directory, document = target_echo_reference.run_study(
            target_echo_reference.StudyPlan(
                (1,),
                1,
                target_echo_reference.PATTERNED_MODE,
                measure_steps=True,
                layout_mode=target_echo_reference.FORWARD_SKIP_LAYOUT,
                measure_verifier=True,
            ),
            emitter=emitter,
            runner=runner,
        )
        try:
            outcomes = {row["algorithm"]: row for row in document["observations"]}
            assert outcomes[target_echo_reference.WALK]["outcome"] == analyze.VERIFIED
            assert outcomes[target_echo_reference.SKIP]["outcome"] == expected
            failed = outcomes[target_echo_reference.SKIP]
            assert failed["metrics"].keys() == {"elapsed_ns"}
            assert failed["verifier_verdict"] == (
                analyze.REJECTED
                if expected == analyze.VERIFIER_REJECTED
                else analyze.NOT_RUN
            )
            assert (
                target_echo_audit.audit(
                    (directory / "study.json")
                    .relative_to(target_echo_reference._ROOT)
                    .as_posix()
                )["reported_failed_trials_not_replayed"]
                == 1
            )
        finally:
            shutil.rmtree(directory)


@pytest.mark.skipif(
    not target_echo_reference.DEFAULT_EMITTER.is_file()
    or not target_echo_reference.DEFAULT_RUNNER.is_file(),
    reason="built Malbolge tools required",
)
def test_real_postexecution_source_mutation_is_independently_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Correct VM stdout cannot admit a source changed before verification."""
    original = target_echo_reference._timed_source_verifier

    def mutate_skipped_cell(path: Path, pairs: int, algorithm: str) -> int:
        if algorithm == target_echo_reference.SKIP:
            source = bytearray(path.read_bytes())
            skipped_position = target_echo_reference.SKIPPED_NOOPS // 2
            source[skipped_position] = (
                GRAPHICAL_LOW
                if source[skipped_position] != GRAPHICAL_LOW
                else GRAPHICAL_LOW + 1
            )
            path.write_bytes(source)
        return original(path, pairs, algorithm)

    monkeypatch.setattr(
        target_echo_reference, "_timed_source_verifier", mutate_skipped_cell
    )
    with tempfile.TemporaryDirectory(
        dir=target_echo_reference._TEMP,
        prefix="arena-verifier-mutation-test-",
    ) as tools:
        emitter = Path(tools) / "malbolge_layout"
        runner = Path(tools) / "malbolge"
        shutil.copy2(target_echo_reference.DEFAULT_EMITTER, emitter)
        shutil.copy2(target_echo_reference.DEFAULT_RUNNER, runner)
        directory, document = target_echo_reference.run_study(
            target_echo_reference.StudyPlan(
                (1,),
                1,
                target_echo_reference.PATTERNED_MODE,
                measure_steps=True,
                layout_mode=target_echo_reference.FORWARD_SKIP_LAYOUT,
                measure_verifier=True,
            ),
            emitter=emitter,
            runner=runner,
        )
        try:
            assert [row["outcome"] for row in document["observations"]] == [
                analyze.VERIFIED,
                analyze.VERIFIER_REJECTED,
            ]
            assert document["observations"][1]["metrics"].keys() == {"elapsed_ns"}
            checked = target_echo_audit.audit(
                (directory / "study.json")
                .relative_to(target_echo_reference._ROOT)
                .as_posix()
            )
            assert checked["verified_target_sources_checked"] == 1
            assert checked["reported_failed_trials_not_replayed"] == 1
        finally:
            shutil.rmtree(directory)


@pytest.mark.skipif(
    not target_echo_reference.DEFAULT_EMITTER.is_file()
    or not target_echo_reference.DEFAULT_RUNNER.is_file(),
    reason="built Malbolge tools required",
)
@pytest.mark.parametrize(
    "mode",
    [
        target_echo_reference.SOURCE_VERIFIER_MODE,
        target_echo_reference.REPLAY_VERIFIER_MODE,
    ],
)
def test_cli_opt_in_verifier_cost_publishes_four_objective_study(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    mode: str,
) -> None:
    """Operator flags reach the selected verifier-cost stage and raw audit."""
    original = target_echo_reference.run_study
    generated: list[Path] = []
    with tempfile.TemporaryDirectory(
        dir=target_echo_reference._TEMP, prefix="arena-verifier-cli-tools-"
    ) as tools:
        emitter = Path(tools) / "malbolge_layout"
        runner = Path(tools) / "malbolge"
        shutil.copy2(target_echo_reference.DEFAULT_EMITTER, emitter)
        shutil.copy2(target_echo_reference.DEFAULT_RUNNER, runner)

        def route(
            plan: target_echo_reference.StudyPlan,
        ) -> tuple[Path, dict[str, Any]]:
            result = original(plan, emitter=emitter, runner=runner)
            generated.append(result[0])
            return result

        monkeypatch.setattr(target_echo_reference, "run_study", route)
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
                mode,
            ],
        )
        try:
            assert target_echo_reference.main() == 0
            output = json.loads(capsys.readouterr().out)
            relative = output["study"]
            study = json.loads((target_echo_reference._ROOT / relative).read_text())
            assert study["study"]["id"] == (
                target_echo_reference.FORWARD_REPLAY_COST_STUDY
                if mode == target_echo_reference.REPLAY_VERIFIER_MODE
                else target_echo_reference.FORWARD_VERIFIER_COST_STUDY
            )
            assert all(
                target_echo_reference.VERIFIER_NS in row["metrics"]
                for row in study["observations"]
            )
            checked = target_echo_audit.audit(
                relative,
                options=target_echo_audit.AuditOptions(
                    replay_candidates=True, emitter=emitter, runner=runner
                ),
            )
            assert checked["target_sources_replayed"] == SINGLE_PAIRED_TRIAL_ARMS
        finally:
            for directory in generated:
                shutil.rmtree(directory)


@pytest.mark.parametrize(
    "invalid_pairs",
    [None, 1, "1", [1], ([],), (1, []), ((1,),)],
    ids=[
        "missing",
        "scalar",
        "text",
        "list",
        "unhashable",
        "mixed-unhashable",
        "nested-tuple",
    ],
)
def test_direct_target_plan_rejects_foreign_pair_collections_before_setup(
    monkeypatch: pytest.MonkeyPatch,
    invalid_pairs: object,
) -> None:
    """Malformed collections cannot pass or crash before target setup."""
    plan = target_echo_reference.StudyPlan(cast("tuple[int, ...]", invalid_pairs), 1)

    def forbidden(*args: object, **kwargs: object) -> None:
        _ = (args, kwargs)
        message = "malformed pair collection launched target study"
        raise AssertionError(message)

    monkeypatch.setattr(target_echo_reference, "_prepare_context", forbidden)
    with pytest.raises(target_echo_reference.TargetEchoStudyError, match="exact tuple"):
        target_echo_reference.run_study(plan)


@pytest.mark.parametrize("invalid", [None, False, 0, "plan", object()])
def test_direct_target_study_rejects_foreign_plan_before_setup(
    monkeypatch: pytest.MonkeyPatch,
    invalid: object,
) -> None:
    """Direct producer APIs require an actual StudyPlan before any I/O."""

    def forbidden(*args: object, **kwargs: object) -> None:
        _ = (args, kwargs)
        message = "foreign plan launched target study"
        raise AssertionError(message)

    monkeypatch.setattr(target_echo_reference, "_prepare_context", forbidden)
    with pytest.raises(
        target_echo_reference.TargetEchoStudyError, match="exact StudyPlan"
    ):
        target_echo_reference.run_study(
            cast("target_echo_reference.StudyPlan", invalid)
        )


@pytest.mark.parametrize(
    "plan",
    [
        target_echo_reference.StudyPlan((), 1),
        target_echo_reference.StudyPlan((1, 1), 1),
        target_echo_reference.StudyPlan((0,), 1),
        target_echo_reference.StudyPlan((65,), 1),
        target_echo_reference.StudyPlan((1,), 0),
        target_echo_reference.StudyPlan((1,), 4),
        target_echo_reference.StudyPlan((True,), 1),
        target_echo_reference.StudyPlan((1,), 1, "arbitrary"),
        target_echo_reference.StudyPlan((1,), 1, cast("str", BOOL_TRIAL_ALIAS)),
        target_echo_reference.StudyPlan(
            (1,), 1, target_echo_reference.EOF_MODE, cast("bool", 1)
        ),
        target_echo_reference.StudyPlan(
            (1,),
            1,
            target_echo_reference.EOF_MODE,
            measure_verifier=True,
        ),
        target_echo_reference.StudyPlan(
            (1,),
            1,
            target_echo_reference.PATTERNED_MODE,
            measure_steps=True,
            layout_mode=target_echo_reference.FORWARD_SKIP_LAYOUT,
            measure_verifier=cast("bool", 1),
        ),
        target_echo_reference.StudyPlan(
            (1,),
            1,
            target_echo_reference.PATTERNED_MODE,
            measure_steps=True,
            layout_mode=target_echo_reference.LINEAR_LAYOUT,
            measure_verifier=True,
        ),
        target_echo_reference.StudyPlan(
            (1,),
            1,
            target_echo_reference.PATTERNED_MODE,
            measure_steps=True,
            layout_mode=target_echo_reference.FORWARD_SKIP_LAYOUT,
            verifier_mode=target_echo_reference.REPLAY_VERIFIER_MODE,
        ),
        target_echo_reference.StudyPlan(
            (1,),
            1,
            target_echo_reference.PATTERNED_MODE,
            measure_steps=True,
            layout_mode=target_echo_reference.FORWARD_SKIP_LAYOUT,
            measure_verifier=True,
            verifier_mode="unknown",
        ),
        target_echo_reference.StudyPlan(
            (1,),
            1,
            target_echo_reference.PATTERNED_MODE,
            measure_steps=True,
            layout_mode=target_echo_reference.FORWARD_SKIP_LAYOUT,
            measure_verifier=True,
            verifier_mode=cast("str", BOOL_TRIAL_ALIAS),
        ),
        target_echo_reference.StudyPlan(
            (1,),
            1,
            target_echo_reference.PATTERNED_MODE,
            measure_steps=True,
            layout_mode=target_echo_reference.FORWARD_SKIP_LAYOUT,
            limit_child_resources=True,
        ),
        target_echo_reference.StudyPlan(
            (1,),
            1,
            target_echo_reference.PATTERNED_MODE,
            measure_steps=True,
            layout_mode=target_echo_reference.FORWARD_SKIP_LAYOUT,
            measure_verifier=True,
            limit_child_resources=True,
        ),
        target_echo_reference.StudyPlan(
            (1,),
            1,
            target_echo_reference.PATTERNED_MODE,
            measure_steps=True,
            layout_mode=target_echo_reference.FORWARD_SKIP_LAYOUT,
            measure_verifier=True,
            verifier_mode=target_echo_reference.REPLAY_VERIFIER_MODE,
            limit_child_resources=cast("bool", 1),
        ),
        target_echo_reference.StudyPlan((1,), BOOL_TRIAL_ALIAS),
        target_echo_reference.StudyPlan(
            (1,),
            1,
            target_echo_reference.EOF_MODE,
            measure_steps=True,
            layout_mode=target_echo_reference.FORWARD_SKIP_LAYOUT,
        ),
        target_echo_reference.StudyPlan(
            (1,),
            1,
            target_echo_reference.PATTERNED_MODE,
            layout_mode=target_echo_reference.FORWARD_SKIP_LAYOUT,
        ),
        target_echo_reference.StudyPlan(
            (1,),
            1,
            target_echo_reference.PATTERNED_MODE,
            measure_steps=True,
            layout_mode="unknown",
        ),
    ],
)
def test_invalid_plan_refuses_before_creating_study(
    plan: target_echo_reference.StudyPlan,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unsupported shapes and bool aliases must never launch a target child."""

    def forbidden(*args: object, **kwargs: object) -> None:
        _ = (args, kwargs)
        message = "target study was launched"
        raise AssertionError(message)

    monkeypatch.setattr(target_echo_reference, "_prepare_context", forbidden)
    with pytest.raises(target_echo_reference.TargetEchoStudyError, match="target echo"):
        target_echo_reference.run_study(plan)


@pytest.mark.skipif(
    not target_echo_reference.DEFAULT_EMITTER.is_file(),
    reason="built Malbolge layout emitter missing",
)
@pytest.mark.parametrize(
    ("wrong_output", "expected_outcome"),
    [(b"Z", analyze.VERIFIER_REJECTED), (b"", analyze.VERIFIER_REJECTED)],
)
def test_wrong_external_vm_output_retains_failed_trial_not_success(
    tmp_path: Path,
    wrong_output: bytes,
    expected_outcome: str,
) -> None:
    """A forged or missing EOF byte cannot claim a verified Malbolge result."""
    runner = tmp_path / "incorrect-runner"
    _ = runner.write_bytes(b"#!/bin/sh\nprintf '" + wrong_output + b"'\n")
    runner.chmod(0o700)
    with tempfile.TemporaryDirectory(
        dir=target_echo_reference._TEMP,
        prefix="arena-target-test-tools-",
    ) as tool_directory:
        emitter = Path(tool_directory) / "malbolge_layout"
        shutil.copy2(target_echo_reference.DEFAULT_EMITTER, emitter)
        directory, document = target_echo_reference.run_study(
            target_echo_reference.StudyPlan((1,), 1),
            emitter=emitter,
            runner=runner,
        )
    try:
        assert all(
            row["outcome"] == expected_outcome for row in document["observations"]
        )
        assert all(
            ARTIFACT_BYTES not in row["metrics"] for row in document["observations"]
        )
        report = analyze.analyze(document)
        assert report["pareto_frontiers"][0]["algorithms"] == []
        assert json.loads((directory / "study.json").read_text()) == document
    finally:
        shutil.rmtree(directory)


@pytest.mark.parametrize(
    "fault_type",
    [
        target_echo_reference.TargetEchoStudyError,
        analyze.ArenaError,
        evidence.EvidenceError,
        OSError,
        sp.SubprocessError,
        report_output.ReportOutputError,
    ],
)
def test_target_reference_cli_never_formats_foreign_errors(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    fault_type: type[Exception],
) -> None:
    """Operator failure remains typed even with a malicious error formatter."""

    def unsafe_str(self: Exception) -> str:
        del self
        raise AssertionError("foreign target reference CLI formatter executed")

    foreign = type(
        "ForeignTargetReferenceFault", (fault_type,), {"__str__": unsafe_str}
    )
    fault = foreign("unsafe target reference dependency error")

    def fail_study(*_args: object, **_kwargs: object) -> None:
        raise fault

    monkeypatch.setattr(target_echo_reference, "run_study", fail_study)
    monkeypatch.setattr(sys, "argv", ["target-reference", "--pairs", "1"])
    with pytest.raises(SystemExit) as caught:
        target_echo_reference.main()
    assert caught.value.code == 2
    output = capsys.readouterr()
    assert not output.out
    assert "ForeignTargetReferenceFault" in output.err


def test_target_reference_source_audit_never_formats_foreign_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A retained source audit failure cannot execute a foreign formatter."""

    class ForeignAuditFailure(target_echo_audit.TargetEchoAuditError):
        def __str__(self) -> str:
            raise AssertionError("foreign target source audit formatter executed")

    fault = ForeignAuditFailure("unsafe retained source fault")

    def fail_audit(*_args: object, **_kwargs: object) -> None:
        raise fault

    monkeypatch.setattr(target_echo_reference, "_ROOT", tmp_path)
    monkeypatch.setattr(target_echo_audit, "audit", fail_audit)
    with pytest.raises(
        target_echo_reference.TargetEchoStudyError, match="source admission failed"
    ) as caught:
        target_echo_reference._audit_retained_study(tmp_path / "study.json")
    assert caught.value.__cause__ is fault
    assert "ForeignAuditFailure" in str(caught.value)


def test_target_reference_native_audit_failure_keeps_detail(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An exact native audit failure retains its detail and exception cause."""
    fault = target_echo_audit.TargetEchoAuditError("retained source mismatch")

    def fail_audit(*_args: object, **_kwargs: object) -> None:
        raise fault

    monkeypatch.setattr(target_echo_reference, "_ROOT", tmp_path)
    monkeypatch.setattr(target_echo_audit, "audit", fail_audit)
    with pytest.raises(
        target_echo_reference.TargetEchoStudyError, match="retained source mismatch"
    ) as caught:
        target_echo_reference._audit_retained_study(tmp_path / "study.json")
    assert caught.value.__cause__ is fault


@pytest.mark.parametrize("kind", [OSError, ValueError, RuntimeError])
def test_target_echo_setup_cleanup_bypasses_hostile_primary_note(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    kind: type[Exception],
) -> None:
    """A foreign setup exception cannot replace the typed workspace rejection."""

    class HostilePrimary(kind):
        def add_note(self, note: str) -> None:
            del note
            raise AssertionError("foreign target setup add_note invoked")

    primary = HostilePrimary("primary target workspace failure")
    cleanup = ValueError("native cleanup failure")

    def fail_mkdir(*_args: object, **_kwargs: object) -> None:
        raise primary

    def fail_cleanup(*_args: object, **_kwargs: object) -> None:
        raise cleanup

    monkeypatch.setattr(target_echo_reference.Path, "mkdir", fail_mkdir)
    monkeypatch.setattr(target_echo_reference.shutil, "rmtree", fail_cleanup)
    with pytest.raises(
        target_echo_reference.TargetEchoStudyError, match="initialization failed"
    ) as caught:
        target_echo_reference._initialize_workspace_folders(tmp_path, ("raw",))
    assert caught.value.__cause__ is primary
    assert "native cleanup failure" in primary.__notes__[0]


@pytest.mark.parametrize("kind", [ValueError, RuntimeError, OSError])
def test_target_echo_setup_cleanup_never_formats_foreign_secondary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    kind: type[Exception],
) -> None:
    """Foreign cleanup diagnostics cannot supersede a primary setup error."""

    class HostileCleanup(kind):
        def __str__(self) -> str:
            raise AssertionError("foreign target cleanup formatter invoked")

    primary = OSError("primary target workspace failure")
    cleanup = HostileCleanup("untrusted secondary failure")

    def fail_mkdir(*_args: object, **_kwargs: object) -> None:
        raise primary

    def fail_cleanup(*_args: object, **_kwargs: object) -> None:
        raise cleanup

    monkeypatch.setattr(target_echo_reference.Path, "mkdir", fail_mkdir)
    monkeypatch.setattr(target_echo_reference.shutil, "rmtree", fail_cleanup)
    with pytest.raises(
        target_echo_reference.TargetEchoStudyError, match="initialization failed"
    ) as caught:
        target_echo_reference._initialize_workspace_folders(tmp_path, ("raw",))
    assert caught.value.__cause__ is primary
    assert "cleanup failed" in primary.__notes__[0]


@pytest.mark.parametrize(
    "kind",
    [
        target_echo_reference.TargetEchoStudyError,
        analyze.ArenaError,
        evidence.EvidenceError,
        target_echo_audit.TargetEchoAuditError,
        OSError,
        report_output.ReportOutputError,
    ],
)
def test_target_echo_safe_error_detail_does_not_format_hostile_native_argument(
    kind: type[Exception],
) -> None:
    """An exact native error type does not authenticate its arguments."""

    class HostileArgument:
        def __str__(self) -> str:
            raise AssertionError("foreign target native argument formatter")

    fault = kind(HostileArgument())
    detail = target_echo_reference._safe_error_detail(
        fault, trusted=target_echo_audit.TargetEchoAuditError
    )
    assert detail == kind.__name__
