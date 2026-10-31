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
#   - Deterministic arena input descriptor-substitution regressions.
# - Must-Not:
#   - Claim atomic snapshots or authenticate study producer identity.
# - Allows:
#   - Inputs: temporary JSON files and injected POSIX pathname races.
#   - Outputs: stable byte checks and typed fail-closed CLI admission.
#   - Side effects: test-local ordinary, linked, and FIFO file replacement.
# - Split-When:
#   - A platform-specific study reader needs independent host conformance.
# - Merge-When:
#   - All arena input-file trust tests share one owner.
# - Summary:
#   - Proves descriptor identity and nonblocking FIFO substitution rejection.
# - Description:
#   - Covers pre-open, mid-read, post-read and truncated stream drift.
# - Usage:
#   - `pytest benchmarks/arena/tests/test_study_file.py`.
# - Defaults:
#   - Any detected race yields no admitted report.
#

"""Arena JSON input file read hardening fixtures, not performance evidence."""

# ruff: file-ignore[assert,private-member-access]

from __future__ import annotations

import json
import sys
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any, cast

import pytest

from benchmarks.arena import analyze, evidence, study_file
from benchmarks.arena.tests.test_evidence import sample_study

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path
    from typing import BinaryIO


STABLE_INPUT = "source.json"
STUDY_SAMPLE = b"staged"
INVALID_UTF8 = b"invalid-\xff-utf8"
SUBSTITUTED = "other.json"
CHANGED_OPEN = "changed between path and open"
CHANGED_READ = "changed during read"
SHORT_READ = "ended before declared file size"
SECOND_FSTAT = 2


def _study(path: Path) -> str:
    document = json.dumps(sample_study(path.parent), sort_keys=True)
    _ = path.write_text(document, encoding="utf-8")
    return document


def test_unchanged_regular_study_retains_original_json_bytes(
    tmp_path: Path,
) -> None:
    """The new reader preserves successful legacy input byte-for-byte."""
    path = tmp_path / STABLE_INPUT
    original = _study(path)
    assert analyze.read_input(path) == original
    assert study_file.read_study_bytes(
        path,
        limit=analyze.MAX_INPUT_BYTES,
    ) == original.encode("utf-8")


@pytest.mark.parametrize(
    "invalid_limit",
    [
        0,
        -1,
        False,
        True,
        None,
        "16",
        float("nan"),
        float("inf"),
        16 * 1024 * 1024 + 1,
    ],
)
def test_invalid_direct_study_budget_rejects_before_open(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    invalid_limit: object,
) -> None:
    """Malformed budgets never bypass limits or reach filesystem I/O."""
    attempted_open = False

    def forbidden(*args: object, **kwargs: object) -> object:
        nonlocal attempted_open
        _ = (args, kwargs)
        attempted_open = True
        message = "invalid direct budget reached file admission"
        raise AssertionError(message)

    monkeypatch.setattr(study_file, "_admit_path", forbidden)
    with pytest.raises(study_file.StudyFileError, match="byte limit"):
        _ = study_file.read_study_bytes(
            tmp_path / "does-not-exist", limit=cast("int", invalid_limit)
        )
    assert not attempted_open


def test_exact_declared_study_budget_still_reads_normal_file(
    tmp_path: Path,
) -> None:
    """Positive bounded limits admit exact ordinary byte lengths."""
    path = tmp_path / STABLE_INPUT
    _ = path.write_bytes(STUDY_SAMPLE)
    assert study_file.read_study_bytes(
        path, limit=len(STUDY_SAMPLE)
    ) == STUDY_SAMPLE
    assert study_file.read_study_bytes(
        path, limit=study_file.MAX_STUDY_BYTES
    ) == STUDY_SAMPLE
    with pytest.raises(study_file.StudyFileError, match="exceeds"):
        _ = study_file.read_study_bytes(path, limit=len(STUDY_SAMPLE) - 1)


@pytest.mark.parametrize("missing_parent", [False, True])
def test_direct_study_reader_and_analyzer_type_missing_paths(
    tmp_path: Path,
    *,
    missing_parent: bool,
) -> None:
    """Unavailable input cannot leak host path errors to a direct caller."""
    path = tmp_path / "missing"
    if missing_parent:
        path /= STABLE_INPUT
    with pytest.raises(study_file.StudyFileError, match="access") as reader:
        _ = study_file.read_study_bytes(path, limit=1024)
    assert isinstance(reader.value.__cause__, FileNotFoundError)
    with pytest.raises(analyze.ArenaError, match="access") as analyzer:
        _ = analyze.read_input(path)
    assert isinstance(analyzer.value.__cause__, study_file.StudyFileError)


def test_direct_reader_types_invalid_path_argument() -> None:
    """A foreign pathname is rejected through the same admission boundary."""
    with pytest.raises(study_file.StudyFileError, match="access") as result:
        _ = study_file.read_study_bytes(cast("Path", "not-a-path"), limit=1024)
    assert isinstance(result.value.__cause__, AttributeError)


def test_direct_analyzer_types_invalid_utf8_input(tmp_path: Path) -> None:
    """Uninterpretable bytes cannot escape the arena input error type."""
    path = tmp_path / STABLE_INPUT
    _ = path.write_bytes(INVALID_UTF8)
    assert study_file.read_study_bytes(path, limit=1024) == INVALID_UTF8
    with pytest.raises(analyze.ArenaError, match="UTF-8") as result:
        _ = analyze.read_input(path)
    assert isinstance(result.value.__cause__, UnicodeDecodeError)


def _same_length_study_rewrite(path: Path) -> None:
    contents = path.read_text(encoding="utf-8")
    document = json.loads(contents)
    old = document["study"]["id"]
    document["study"]["id"] = ("z" if old[0] != "z" else "y") + old[1:]
    changed = json.dumps(document, sort_keys=True)
    assert len(changed.encode("utf-8")) == len(contents.encode("utf-8"))
    _ = path.write_text(changed, encoding="utf-8")


@pytest.mark.parametrize("cli", ["analyze", "evidence"])
def test_cli_rechecks_study_after_analysis_before_publication(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    cli: str,
) -> None:
    """Same-size study rewrites after completed analysis cannot publish."""
    path = tmp_path / STABLE_INPUT
    _study(path)
    original_analyze = analyze.analyze

    def rewrite_after_analysis(*args: Any, **kwargs: Any) -> dict[str, Any]:
        report = original_analyze(*args, **kwargs)
        _same_length_study_rewrite(path)
        return report

    monkeypatch.setattr(analyze, "analyze", rewrite_after_analysis)
    entry = analyze.main if cli == "analyze" else evidence.main
    args = ["arena", str(path)]
    if cli == "evidence":
        args.extend(("--root", str(tmp_path)))
    monkeypatch.setattr(sys, "argv", args)
    with pytest.raises(SystemExit, match="2"):
        entry()
    output = capsys.readouterr()
    assert not output.out
    assert "study input changed" in output.err


def test_evidence_cli_rechecks_study_mutated_during_preflight(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Slow evidence validation cannot reattribute a replaced study."""
    path = tmp_path / STABLE_INPUT
    _study(path)
    original_validate = evidence.validate_links

    def rewrite_after_preflight(*args: Any, **kwargs: Any) -> dict[str, Any]:
        result = original_validate(*args, **kwargs)
        _same_length_study_rewrite(path)
        return result

    monkeypatch.setattr(evidence, "validate_links", rewrite_after_preflight)
    monkeypatch.setattr(
        sys, "argv", ["arena-evidence", str(path), "--root", str(tmp_path)]
    )
    with pytest.raises(SystemExit, match="2"):
        evidence.main()
    output = capsys.readouterr()
    assert not output.out
    assert "study input changed" in output.err


@pytest.mark.parametrize("cli", ["analyze", "evidence"])
@pytest.mark.parametrize("tamper", ["missing", "symlink"])
def test_cli_rechecks_study_path_after_analysis(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    cli: str,
    tamper: str,
) -> None:
    """Late missing and linked study paths cannot publish a stale report."""
    path = tmp_path / STABLE_INPUT
    original_bytes = _study(path).encode("utf-8")
    original_analyze = analyze.analyze

    def tamper_after_analysis(*args: Any, **kwargs: Any) -> dict[str, Any]:
        report = original_analyze(*args, **kwargs)
        path.unlink()
        if tamper == "symlink":
            target = tmp_path / SUBSTITUTED
            _ = target.write_bytes(original_bytes)
            path.symlink_to(target)
        return report

    monkeypatch.setattr(analyze, "analyze", tamper_after_analysis)
    entry = analyze.main if cli == "analyze" else evidence.main
    args = ["arena", str(path)]
    if cli == "evidence":
        args.extend(("--root", str(tmp_path)))
    monkeypatch.setattr(sys, "argv", args)
    with pytest.raises(SystemExit, match="2"):
        entry()
    output = capsys.readouterr()
    assert not output.out
    assert "arena" in output.err


class _FragmentedStudyStream:
    def __init__(self, stream: BinaryIO, *, premature_eof: bool) -> None:
        self.stream = stream
        self.premature_eof = premature_eof
        self.read_calls = 0

    def fileno(self) -> int:
        return self.stream.fileno()

    def read(self, count: int) -> bytes:
        self.read_calls += 1
        if self.premature_eof and self.read_calls > 1:
            return b""
        return self.stream.read(min(count, 7))


@pytest.mark.parametrize("premature_eof", [False, True])
def test_fragmented_study_reads_are_complete_or_fail_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    premature_eof: bool,
) -> None:
    """An ordinary short read cannot become a silently truncated study."""
    path = tmp_path / STABLE_INPUT
    expected = _study(path)
    original_open = study_file._open_study

    @contextmanager
    def fragmented_open(target: Path) -> Iterator[_FragmentedStudyStream]:
        with original_open(target) as stream:
            yield _FragmentedStudyStream(stream, premature_eof=premature_eof)

    monkeypatch.setattr(study_file, "_open_study", fragmented_open)
    if premature_eof:
        with pytest.raises(analyze.ArenaError, match=SHORT_READ):
            analyze.read_input(path)
    else:
        assert analyze.read_input(path) == expected


class _FaultyStudyStream:
    def __init__(
        self,
        stream: BinaryIO,
        *,
        error: type[Exception] | None,
        invalid: str | None,
    ) -> None:
        self.stream = stream
        self.error = error
        self.invalid = invalid

    def fileno(self) -> int:
        return self.stream.fileno()

    def read(self, count: int) -> object:
        if self.error is not None:
            message = "injected stream fault"
            raise self.error(message)
        if self.invalid == NONBINARY_CHUNK:
            return "forged text bytes"
        return b"x" * (count + 1)


NONBINARY_CHUNK = "text"


@pytest.mark.parametrize(
    "fault",
    [OSError, ValueError, RuntimeError, TypeError, AttributeError],
)
def test_study_stream_read_fault_preserves_typed_failure_and_cause(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault: type[Exception],
) -> None:
    """A broken descriptor stream cannot escape arena's typed input boundary."""
    path = tmp_path / STABLE_INPUT
    _study(path)
    original_open = study_file._open_study

    @contextmanager
    def faulty_open(target: Path) -> Iterator[_FaultyStudyStream]:
        with original_open(target) as stream:
            yield _FaultyStudyStream(stream, error=fault, invalid=None)

    monkeypatch.setattr(study_file, "_open_study", faulty_open)
    with pytest.raises(analyze.ArenaError, match="stream read failed") as result:
        analyze.read_input(path)
    assert isinstance(result.value.__cause__, study_file.StudyFileError)
    assert isinstance(result.value.__cause__.__cause__, fault)


@pytest.mark.parametrize("invalid", [NONBINARY_CHUNK, "oversized"])
def test_study_reader_rejects_nonbyte_or_overlong_chunks(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    invalid: str,
) -> None:
    """A malicious reader cannot exceed its requested count or forge bytes."""
    path = tmp_path / STABLE_INPUT
    _study(path)
    original_open = study_file._open_study

    @contextmanager
    def invalid_open(target: Path) -> Iterator[_FaultyStudyStream]:
        with original_open(target) as stream:
            yield _FaultyStudyStream(stream, error=None, invalid=invalid)

    monkeypatch.setattr(study_file, "_open_study", invalid_open)
    with pytest.raises(analyze.ArenaError, match="invalid bytes"):
        analyze.read_input(path)


@pytest.mark.skipif(
    sys.platform != "linux",
    reason="Linux opened-descriptor path provenance is required",
)
def test_study_reader_rejects_transient_symlink_parent_equal_inode(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A restored parent symlink cannot authorize an outside hard-link open."""
    root = tmp_path / "root"
    directory = root / "study"
    directory.mkdir(parents=True)
    path = directory / STABLE_INPUT
    original = b'{"schema_version": 1}'
    _ = path.write_bytes(original)
    outside = tmp_path / "outside-root"
    outside.mkdir()
    _ = study_file.os.link(path, outside / STABLE_INPUT)
    parked = root / "parked-study"
    actual_open = study_file.os.open
    swapped = False

    def redirect_parent_on_open(target: Path, flags: int) -> int:
        nonlocal swapped
        if target != path:
            return actual_open(target, flags)
        swapped = True
        directory.rename(parked)
        directory.symlink_to(outside, target_is_directory=True)
        try:
            return actual_open(target, flags)
        finally:
            directory.unlink()
            parked.rename(directory)

    monkeypatch.setattr(study_file.os, "open", redirect_parent_on_open)
    with pytest.raises(study_file.StudyFileError, match="opened path changed"):
        study_file.read_study_bytes(path, limit=1024)
    assert swapped
    assert path.read_bytes() == original
    assert (outside / STABLE_INPUT).read_bytes() == original


@pytest.mark.skipif(
    sys.platform != "linux",
    reason="Linux opened-descriptor path provenance is required",
)
def test_study_reader_rejects_post_read_same_inode_parent_alias(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Post-open parent redirection must not pass same-inode lstat checks."""
    directory = tmp_path / "original"
    directory.mkdir()
    source = directory / STABLE_INPUT
    original = b'{"schema_version": 1}'
    _ = source.write_bytes(original)
    foreign = tmp_path / "foreign"
    foreign.mkdir()
    _ = study_file.os.link(source, foreign / STABLE_INPUT)
    parked = tmp_path / "parked"
    original_read = study_file._read_complete
    swapped = False

    def redirect_after_read(stream: BinaryIO, *, size: int) -> bytes:
        nonlocal swapped
        content = original_read(stream, size=size)
        directory.rename(parked)
        directory.symlink_to(foreign, target_is_directory=True)
        swapped = True
        return content

    monkeypatch.setattr(study_file, "_read_complete", redirect_after_read)
    try:
        with pytest.raises(
            study_file.StudyFileError, match="arena input parent path changed"
        ):
            study_file.read_study_bytes(source, limit=1024)
    finally:
        if swapped:
            directory.unlink()
            parked.rename(directory)
    assert swapped
    assert source.read_bytes() == original
    assert (foreign / STABLE_INPUT).read_bytes() == original


@pytest.mark.skipif(
    sys.platform != "linux",
    reason="Linux opened-descriptor path provenance is required",
)
def test_study_reader_rejects_parent_directory_swap_with_same_inode_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A different directory at the same path must not authorize the old file."""
    directory = tmp_path / "original"
    directory.mkdir()
    source = directory / STABLE_INPUT
    original = b'{"schema_version": 1}'
    _ = source.write_bytes(original)
    foreign = tmp_path / "foreign"
    foreign.mkdir()
    _ = study_file.os.link(source, foreign / STABLE_INPUT)
    parked = tmp_path / "parked"
    original_read = study_file._read_complete
    swapped = False

    def redirect_after_read(stream: BinaryIO, *, size: int) -> bytes:
        nonlocal swapped
        content = original_read(stream, size=size)
        directory.rename(parked)
        foreign.rename(directory)
        swapped = True
        return content

    monkeypatch.setattr(study_file, "_read_complete", redirect_after_read)
    try:
        with pytest.raises(
            study_file.StudyFileError, match="arena input parent directory changed"
        ):
            study_file.read_study_bytes(source, limit=1024)
    finally:
        if swapped:
            directory.rename(foreign)
            parked.rename(directory)
    assert swapped
    assert source.read_bytes() == original
    assert (foreign / STABLE_INPUT).read_bytes() == original


@pytest.mark.skipif(
    sys.platform != "linux",
    reason="Linux descriptor path preflight is required",
)
def test_study_reader_preserves_stable_parent_symlink(
    tmp_path: Path,
) -> None:
    """A stable source reached through a symlinked parent remains readable."""
    directory = tmp_path / "actual"
    directory.mkdir()
    source = directory / STABLE_INPUT
    _ = source.write_bytes(b'{"schema_version":1}')
    parent = tmp_path / "alias"
    parent.symlink_to(directory, target_is_directory=True)
    assert study_file.read_study_bytes(parent / STABLE_INPUT, limit=1024) == (
        source.read_bytes()
    )


@pytest.mark.skipif(
    sys.platform != "linux",
    reason="Linux opened-descriptor path provenance is required",
)
def test_study_reader_rejects_missing_fd_path_without_descriptor_leak(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A missing procfs descriptor path must fail closed and release the fd."""
    path = tmp_path / STABLE_INPUT
    _ = path.write_bytes(b'{"schema_version":1}')
    actual_open = study_file.os.open
    actual_readlink = study_file.os.readlink
    opened: list[int] = []

    def capture_open(target: Path, flags: int) -> int:
        descriptor = actual_open(target, flags)
        opened.append(descriptor)
        return descriptor

    def reject_descriptor_path(target: str) -> str:
        if target.startswith("/proc/self/fd/"):
            raise OSError("simulated unavailable procfs")
        return actual_readlink(target)

    with monkeypatch.context() as context:
        context.setattr(study_file.os, "open", capture_open)
        context.setattr(study_file.os, "readlink", reject_descriptor_path)
        with pytest.raises(
            study_file.StudyFileError, match="stream construction failed"
        ) as failure:
            study_file.read_study_bytes(path, limit=1024)
    assert len(opened) == 1
    with pytest.raises(OSError):
        _ = study_file.os.fstat(opened[0])
    assert isinstance(failure.value.__cause__, OSError)


def test_file_replaced_between_lstat_and_descriptor_open_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ordinary same-length replacement cannot impersonate admitted inode."""
    path = tmp_path / STABLE_INPUT
    _study(path)
    staged = tmp_path / SUBSTITUTED
    _ = staged.write_bytes(path.read_bytes())
    real_open = study_file._open_study

    def replace_before_open(target: Path) -> BinaryIO:
        if target == path:
            _ = staged.replace(path)
        return real_open(target)

    monkeypatch.setattr(study_file, "_open_study", replace_before_open)
    with pytest.raises(analyze.ArenaError, match=CHANGED_OPEN):
        analyze.read_input(path)


@pytest.mark.skipif(
    not hasattr(study_file.os, "mkfifo") or not getattr(study_file.os, "O_NONBLOCK", 0),
    reason="FIFO injection needs POSIX nonblocking file opens",
)
def test_raced_fifo_never_blocks_study_reader(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Substituted named pipes are rejected after nonblocking open."""
    path = tmp_path / STABLE_INPUT
    _study(path)
    original_open = study_file._open_study

    def substitute_fifo(target: Path) -> BinaryIO:
        if target == path:
            target.unlink()
            mkfifo = getattr(study_file.os, "mkfifo", None)
            assert callable(mkfifo)
            mkfifo(path)
        return original_open(target)

    monkeypatch.setattr(study_file, "_open_study", substitute_fifo)
    with pytest.raises(analyze.ArenaError, match=CHANGED_OPEN):
        analyze.read_input(path)


def test_raced_symlink_is_rejected_by_no_follow_descriptor_open(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A linked leaf cannot bypass the regular-file gate."""
    path = tmp_path / STABLE_INPUT
    _study(path)
    link_target = tmp_path / SUBSTITUTED
    _ = link_target.write_bytes(path.read_bytes())
    original_open = study_file._open_study

    def substitute_link(target: Path) -> BinaryIO:
        if target == path:
            target.unlink()
            target.symlink_to(link_target)
        return original_open(target)

    monkeypatch.setattr(study_file, "_open_study", substitute_link)
    with pytest.raises(analyze.ArenaError, match="stream access failed") as error:
        analyze.read_input(path)
    assert isinstance(error.value.__cause__, study_file.StudyFileError)
    assert isinstance(error.value.__cause__.__cause__, OSError)


def test_in_place_rewrite_during_descriptor_read_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An observed file-length increase cannot become a trusted JSON prefix."""
    path = tmp_path / STABLE_INPUT
    _study(path)
    original_fstat = study_file.os.fstat
    calls = 0

    def write_before_final_stat(fd: int) -> study_file.os.stat_result:
        nonlocal calls
        calls += 1
        if calls == SECOND_FSTAT:
            with path.open("ab") as stream:
                _ = stream.write(b" ")
        return original_fstat(fd)

    monkeypatch.setattr(study_file.os, "fstat", write_before_final_stat)
    with pytest.raises(analyze.ArenaError, match=CHANGED_READ):
        analyze.read_input(path)


def test_reader_rejects_short_bytes_even_if_stat_claims_stable_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Short input streams cannot silently supply a valid JSON prefix."""
    path = tmp_path / STABLE_INPUT
    _study(path)
    actual_read = study_file._read_descriptor

    def truncate_result(
        target: Path,
        before: study_file.os.stat_result,
        *,
        limit: int,
    ) -> tuple[bytes, study_file.os.stat_result]:
        contents, status = actual_read(target, before, limit=limit)
        return contents[:-1], status

    monkeypatch.setattr(study_file, "_read_descriptor", truncate_result)
    with pytest.raises(analyze.ArenaError, match=SHORT_READ):
        analyze.read_input(path)


def test_standalone_and_evidence_cli_reject_raced_file_without_stdout(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Both CLI entrypoints refuse a substituted read before reporting."""
    path = tmp_path / STABLE_INPUT
    _ = path.write_text(json.dumps(sample_study(tmp_path)), encoding="utf-8")
    real_open = study_file._open_study
    attempts = 0

    def swap_before_open(target: Path) -> BinaryIO:
        nonlocal attempts
        if target == path:
            attempts += 1
            replacement = tmp_path / f"alternate-{attempts}.json"
            _ = replacement.write_bytes(path.read_bytes())
            _ = replacement.replace(path)
        return real_open(target)

    monkeypatch.setattr(study_file, "_open_study", swap_before_open)
    for arguments, entry in (
        (["arena", str(path)], analyze.main),
        (["arena-evidence", str(path), "--root", str(tmp_path)], evidence.main),
    ):
        monkeypatch.setattr(sys, "argv", arguments)
        with pytest.raises(SystemExit, match="2"):
            entry()
        output = capsys.readouterr()
        assert not output.out
        assert CHANGED_OPEN in output.err


@pytest.mark.parametrize(
    "fault", [OSError, ValueError, RuntimeError, TypeError, AttributeError]
)
def test_study_stream_construction_failure_closes_raw_descriptor(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault: type[Exception],
) -> None:
    """An untrusted fdopen failure must be typed and release its raw fd."""
    path = tmp_path / STABLE_INPUT
    _study(path)
    opened: list[int] = []
    actual_open = study_file.os.open

    def capture_open(target: Path, flags: int) -> int:
        fd = actual_open(target, flags)
        opened.append(fd)
        return fd

    def reject_stream(*args: object, **kwargs: object) -> BinaryIO:
        del args, kwargs
        raise fault("injected stream constructor fault")

    with monkeypatch.context() as context:
        context.setattr(study_file.os, "open", capture_open)
        context.setattr(study_file.os, "fdopen", reject_stream)
        with pytest.raises(
            analyze.ArenaError, match="arena input stream construction failed"
        ) as captured:
            _ = analyze.read_input(path)
    assert len(opened) == 1
    with pytest.raises(OSError):
        _ = study_file.os.fstat(opened[0])
    assert isinstance(captured.value.__cause__, study_file.StudyFileError)
    assert type(captured.value.__cause__.__cause__) is fault


def test_study_stream_construction_preserves_primary_when_close_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A failed raw-fd close adds evidence without masking a failed open."""
    path = tmp_path / STABLE_INPUT
    _study(path)
    actual_close = study_file.os.close
    closed: list[int] = []

    def reject_stream(*args: object, **kwargs: object) -> BinaryIO:
        del args, kwargs
        raise RuntimeError("primary fdopen error")

    def fail_after_closing(descriptor: int) -> None:
        actual_close(descriptor)
        closed.append(descriptor)
        raise ValueError("secondary descriptor close error")

    with monkeypatch.context() as context:
        context.setattr(study_file.os, "fdopen", reject_stream)
        context.setattr(study_file.os, "close", fail_after_closing)
        with pytest.raises(
            analyze.ArenaError, match="arena input stream construction failed"
        ) as captured:
            _ = analyze.read_input(path)
    assert len(closed) == 1
    with pytest.raises(OSError):
        _ = study_file.os.fstat(closed[0])
    admitted_error = captured.value.__cause__
    assert isinstance(admitted_error, study_file.StudyFileError)
    primary = admitted_error.__cause__
    assert isinstance(primary, RuntimeError)
    assert str(primary) == "primary fdopen error"
    assert primary.__notes__ == [
        "arena input descriptor cleanup also failed: secondary descriptor close error"
    ]


@pytest.mark.parametrize(
    "fault", [OSError, ValueError, RuntimeError, TypeError, AttributeError]
)
def test_study_stream_close_failure_is_typed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault: type[Exception],
) -> None:
    """Read-complete stream cleanup failures cannot escape typed admission."""
    path = tmp_path / STABLE_INPUT
    _study(path)
    original_open = study_file._open_study

    @contextmanager
    def fail_close(target: Path) -> Iterator[BinaryIO]:
        with original_open(target) as stream:
            yield stream
        raise fault("injected study stream close failure")

    monkeypatch.setattr(study_file, "_open_study", fail_close)
    with pytest.raises(study_file.StudyFileError, match="stream access failed") as error:
        study_file.read_study_bytes(path, limit=analyze.MAX_INPUT_BYTES)
    assert type(error.value.__cause__) is fault


def test_study_stream_close_does_not_hide_primary_read_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A simultaneous read and close fault must retain primary rejection."""
    path = tmp_path / STABLE_INPUT
    _study(path)
    original_open = study_file._open_study

    @contextmanager
    def fail_close(target: Path) -> Iterator[BinaryIO]:
        try:
            with original_open(target) as stream:
                yield stream
        finally:
            raise ValueError("secondary study stream close error")

    def fail_read(stream: BinaryIO, *, size: int) -> bytes:
        _ = stream, size
        raise study_file.StudyFileError("primary study read failure")

    monkeypatch.setattr(study_file, "_open_study", fail_close)
    monkeypatch.setattr(study_file, "_read_complete", fail_read)
    with pytest.raises(study_file.StudyFileError, match="primary study read failure") as error:
        study_file.read_study_bytes(path, limit=analyze.MAX_INPUT_BYTES)
    assert error.value.__notes__ == [
        "arena input stream cleanup also failed: secondary study stream close error"
    ]


def test_study_stream_constructor_failure_rejects_both_cli_routes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Neither operator may publish a report after stream setup fails."""
    path = tmp_path / STABLE_INPUT
    _study(path)

    def reject_stream(*args: object, **kwargs: object) -> BinaryIO:
        del args, kwargs
        raise RuntimeError("injected stream constructor fault")

    with monkeypatch.context() as context:
        context.setattr(study_file.os, "fdopen", reject_stream)
        for arguments, entry in (
            (["arena", str(path)], analyze.main),
            (["arena-evidence", str(path), "--root", str(tmp_path)], evidence.main),
        ):
            context.setattr(sys, "argv", arguments)
            with pytest.raises(SystemExit, match="2"):
                entry()
            output = capsys.readouterr()
            assert not output.out
            assert "arena input stream construction failed" in output.err
