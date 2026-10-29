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

from contextlib import contextmanager
import json
import sys
from typing import TYPE_CHECKING

import pytest

from benchmarks.arena import analyze
from benchmarks.arena import evidence
from benchmarks.arena import study_file
from benchmarks.arena.tests.test_evidence import sample_study

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path
    from typing import BinaryIO


STABLE_INPUT = "source.json"
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
    with pytest.raises(
        analyze.ArenaError, match="stream read failed"
    ) as result:
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
    not hasattr(study_file.os, "mkfifo")
    or not getattr(study_file.os, "O_NONBLOCK", 0),
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
    with pytest.raises(OSError, match=r".+"):
        analyze.read_input(path)


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
