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
#   - The repository behavior implemented by this source file.
# - Must-Not:
#   - Bypass the contracts or authority boundaries of its owning package.
# - Allows:
#   - Inputs: values admitted by the file's public or internal interface.
#   - Outputs: deterministic values or effects declared by that interface.
#   - Side effects: only those explicitly owned by the implementation.
# - Split-When:
#   - Split when one responsibility gains an independent lifecycle.
# - Merge-When:
#   - Merge when another file owns the exact same responsibility.
# - Summary:
#   - Regression tests for the shared LaTeX mathematics framework.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#

"""Regression tests for the shared LaTeX mathematics framework."""

from __future__ import annotations

import os
import subprocess as sp  # ruff: ignore[suspicious-subprocess-import]
from pathlib import Path
from typing import TYPE_CHECKING, Self, cast, final, override

if TYPE_CHECKING:
    from collections.abc import Callable

import pytest

from scripts.validate import math_specifications as validator

HISTORICAL_TRITS = "N=10"
HISTORICAL_WORDS = "W_{10}=59049"
CURRENT_TRITS = "N=15"
CURRENT_WORDS = "W_{15}=14348907"
CACHE_ROOT_CASE = "cache-root"
NOTATION_CASE = "notation"
MISSING_ROOT_CASE = "root"
SECOND_OBSERVATION = 2
OUTSIDE_LOG_TEXT = "external file must survive"
COMPILED_LOG_TEXT = "built latex stdout"

EXPECTED_DOCUMENTS = (
    # jig-ignore-next-line: indivisible reviewed identifier
    "src/specification/formal-model/math/algorithms/adaptive-accelerator-resource-budgeting.tex",
    # jig-ignore-next-line: indivisible reviewed identifier
    "src/specification/formal-model/math/algorithms/compact-guest-bytecode-strategy.tex",
    # jig-ignore-next-line: indivisible reviewed identifier
    "src/specification/formal-model/math/algorithms/malbolge-specific-optimization-mathematics.tex",
    # jig-ignore-next-line: indivisible reviewed identifier
    "src/specification/formal-model/math/algorithms/pytorch-search-orchestration.tex",
    # jig-ignore-next-line: indivisible reviewed identifier
    "src/specification/formal-model/math/algorithms/search-pruning-and-state-canonicalization.tex",
    # jig-ignore-next-line: indivisible reviewed identifier
    "src/specification/formal-model/math/algorithms/self-modification-state-graph-optimizer.tex",
    # jig-ignore-next-line: indivisible reviewed identifier
    "src/specification/formal-model/math/algorithms/stochastic-and-guided-search.tex",
    "src/specification/formal-model/math/specification/malbolge-1998.tex",
    "src/specification/formal-model/math/specification/profile-model.tex",
)


def _relative_documents() -> tuple[str, ...]:
    return tuple(
        path.relative_to(validator.ROOT).as_posix()
        for path in validator.validate_source_layout()
    )


@pytest.mark.parametrize("fault_type", [OSError, ValueError, RuntimeError])
@pytest.mark.parametrize(
    "operation", ("lstat", "junction", "open", "fdopen", "fstat", "read", "post_lstat")
)
def test_math_tex_source_host_faults_are_typed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault_type: type[Exception],
    operation: str,
) -> None:
    """TeX source inspection and transport reject unexpected host failures."""
    source = _snapshot_fixture(tmp_path, monkeypatch)
    if operation in {"lstat", "post_lstat"}:
        original_lstat = Path.lstat
        observations = 0

        def fail_lstat(path: Path) -> os.stat_result:
            nonlocal observations
            if path == source:
                observations += 1
                if operation == "lstat" or observations >= 3:
                    raise fault_type("injected math lstat failure")
            return original_lstat(path)

        monkeypatch.setattr(Path, "lstat", fail_lstat)
    elif operation == "junction":
        original_junction = Path.is_junction

        def fail_junction(path: Path) -> bool:
            if path == source:
                raise fault_type("injected math junction failure")
            return original_junction(path)

        monkeypatch.setattr(Path, "is_junction", fail_junction)
    elif operation == "open":
        original_open = os.open

        def fail_open(path: Path, flags: int) -> int:
            if path == source:
                raise fault_type("injected math open failure")
            return original_open(path, flags)

        monkeypatch.setattr(os, "open", fail_open)
    elif operation == "fdopen":

        def fail_fdopen(_descriptor: int, _mode: str) -> object:
            raise fault_type("injected math fdopen failure")

        monkeypatch.setattr(os, "fdopen", fail_fdopen)
    elif operation == "fstat":

        def fail_fstat(_descriptor: int) -> os.stat_result:
            raise fault_type("injected math fstat failure")

        monkeypatch.setattr(os, "fstat", fail_fstat)
    else:
        original_fdopen = os.fdopen

        class BadReadStream:
            def __init__(self, descriptor: int) -> None:
                self._stream = original_fdopen(descriptor, "rb")

            def __enter__(self) -> Self:
                return self

            def __exit__(self, *_args: object) -> None:
                self._stream.close()

            def fileno(self) -> int:
                return self._stream.fileno()

            def read(self, _size: int) -> bytes:
                raise fault_type("injected math read failure")

        monkeypatch.setattr(
            os, "fdopen", lambda descriptor, _mode: BadReadStream(descriptor)
        )
    with pytest.raises(validator.MathSpecificationError, match="mathematics source"):
        _ = validator._read_tex(source)


@pytest.mark.parametrize("fault_type", [OSError, ValueError, RuntimeError])
def test_math_tex_fdopen_failure_closes_owned_descriptor(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault_type: type[Exception],
) -> None:
    """TeX stream wrapper failure releases the descriptor from os.open."""
    source = _snapshot_fixture(tmp_path, monkeypatch)
    original_open = os.open
    opened: list[int] = []

    def track_open(path: Path, flags: int) -> int:
        descriptor = original_open(path, flags)
        if path == source:
            opened.append(descriptor)
        return descriptor

    def fail_fdopen(_descriptor: int, _mode: str) -> object:
        raise fault_type("injected math fdopen failure")

    monkeypatch.setattr(os, "open", track_open)
    monkeypatch.setattr(os, "fdopen", fail_fdopen)
    with pytest.raises(validator.MathSpecificationError):
        _ = validator._read_tex(source)
    assert len(opened) == 1
    with pytest.raises(OSError):
        _ = os.fstat(opened[0])


@pytest.mark.parametrize("fault_type", [ValueError, RuntimeError])
def test_math_source_scan_host_faults_are_typed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault_type: type[Exception],
) -> None:
    """TeX discovery errors are typed before any build is attempted."""
    source = _snapshot_fixture(tmp_path, monkeypatch)
    original_walk = Path.walk

    def fail_walk(
        path: Path, *, on_error: Callable[[OSError], object] | None = None
    ) -> object:
        if path == source.parent:
            raise fault_type("injected math scan failure")
        return original_walk(path, on_error=on_error)

    monkeypatch.setattr(Path, "walk", fail_walk)
    with pytest.raises(validator.MathSpecificationError, match="scan"):
        _ = validator.document_sources()


@pytest.mark.parametrize("fault_type", [OSError, ValueError, RuntimeError])
@pytest.mark.parametrize("source_kind", ["root", "notation"])
def test_math_source_preflight_host_faults_are_typed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault_type: type[Exception],
    source_kind: str,
) -> None:
    """Root and notation preflight failures become typed validation errors."""
    source = _snapshot_fixture(tmp_path, monkeypatch)
    notation = source.parent / "malbolge-notation.tex"
    _ = notation.write_text("\n".join(validator.REQUIRED_MACROS), encoding="utf-8")
    monkeypatch.setattr(validator, "NOTATION", notation)
    target = source.parent if source_kind == "root" else notation
    original_lstat = Path.lstat

    def fail_lstat(path: Path) -> os.stat_result:
        if path == target:
            raise fault_type("injected math authority status failure")
        return original_lstat(path)

    monkeypatch.setattr(Path, "lstat", fail_lstat)
    with pytest.raises(validator.MathSpecificationError, match="mathematics"):
        if source_kind == "root":
            _ = validator.document_sources()
        else:
            validator._validate_notation()


def test_all_math_documents_share_one_notation_framework() -> None:
    """Every standalone document imports the shared notation include."""
    assert _relative_documents() == EXPECTED_DOCUMENTS


def test_shared_notation_is_not_a_standalone_document() -> None:
    """The common macro surface cannot accidentally become another paper."""
    text = validator.NOTATION.read_text(encoding="utf-8")
    assert validator.DOCUMENT_MARKER not in text


def test_math_documents_do_not_double_escape_control_words() -> None:
    """LaTeX commands remain commands rather than escaped line-break text."""
    forbidden = (r"\\begin", r"\\binom")
    for source in validator.document_sources():
        text = source.read_text(encoding="utf-8")
        assert not any(token in text for token in forbidden), source


def test_build_outputs_are_cache_only_and_source_specific() -> None:
    """Map LaTeX artifacts beneath cache, never beside source."""
    for source in validator.document_sources():
        output = validator.output_directory(source)
        assert output.is_relative_to(validator.CACHE_ROOT)
        assert output.name == source.stem


def test_generic_profile_math_names_historical_and_current_widths() -> None:
    """Specialize the generic model to both canonical widths."""
    path = validator.MATH_ROOT / "specification" / "profile-model.tex"
    text = path.read_text(encoding="utf-8")
    assert HISTORICAL_TRITS in text
    assert HISTORICAL_WORDS in text
    assert CURRENT_TRITS in text
    assert CURRENT_WORDS in text


def _missing_compiler(name: str) -> None:
    _ = name


def test_missing_latex_compiler_fails_with_stable_diagnostic() -> None:
    """Direct validation names the missing tool instead of leaking WinError."""
    with pytest.raises(
        validator.MathSpecificationError,
        match="LaTeX compiler not found: pdflatex",
    ):
        _ = validator.latex_compiler(_missing_compiler)


@pytest.mark.parametrize(
    "redirected",
    ["notation", "document", "document-parent", "math-root"],
)
def test_math_source_layout_rejects_redirected_inputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    redirected: str,
) -> None:
    """TeX evidence must be physical under the configured mathematics root."""
    math_root = tmp_path / "math"
    document_root = math_root / "specification"
    document_root.mkdir(parents=True)
    notation = math_root / "malbolge-notation.tex"
    _ = notation.write_text("\n".join(validator.REQUIRED_MACROS), encoding="utf-8")
    document = document_root / "proof.tex"
    _ = document.write_text(
        validator.DOCUMENT_MARKER + "{article}\n" + validator.NOTATION_INCLUDE,
        encoding="utf-8",
    )
    monkeypatch.setattr(validator, "ROOT", tmp_path)
    monkeypatch.setattr(validator, "MATH_ROOT", math_root)
    monkeypatch.setattr(validator, "NOTATION", notation)
    assert validator.validate_source_layout() == (document,)

    victim = {
        "notation": notation,
        "document": document,
        "document-parent": document_root,
        "math-root": math_root,
    }[redirected]
    external = tmp_path / "external"
    external.mkdir()
    outside = external / victim.name
    _ = victim.rename(outside)
    victim.symlink_to(outside, target_is_directory=outside.is_dir())
    with pytest.raises(validator.MathSpecificationError, match="redirect"):
        _ = validator.validate_source_layout()


def test_math_output_path_rejects_parent_segment_escape(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A direct build request cannot use a parent segment in its cache path."""
    monkeypatch.setattr(validator, "MATH_ROOT", tmp_path / "math")
    with pytest.raises(validator.MathSpecificationError, match="escape"):
        _ = validator.output_directory(validator.MATH_ROOT / ".." / "outside.tex")


@pytest.mark.parametrize("redirected", ["cache-root", "cache-parent"])
def test_math_compilation_rejects_redirected_cache_without_writing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    redirected: str,
) -> None:
    """A cache alias cannot redirect TeX compiler side effects out of cache."""
    math_root = tmp_path / "math"
    source = math_root / "specification" / "proof.tex"
    source.parent.mkdir(parents=True)
    _ = source.write_text(r"\documentclass{article}", encoding="utf-8")
    cache_root = tmp_path / ".cache" / "latex"
    cache_root.parent.mkdir()
    outside = tmp_path / "external"
    outside.mkdir()
    if redirected == CACHE_ROOT_CASE:
        cache_root.symlink_to(outside, target_is_directory=True)
    else:
        cache_root.mkdir()
        (cache_root / "specification").symlink_to(outside, target_is_directory=True)
    monkeypatch.setattr(validator, "ROOT", tmp_path)
    monkeypatch.setattr(validator, "MATH_ROOT", math_root)
    monkeypatch.setattr(validator, "CACHE_ROOT", cache_root)
    monkeypatch.setattr(validator, "validate_source_layout", lambda: (source,))
    with pytest.raises(validator.MathSpecificationError, match=r"cache.*redirect"):
        _ = validator.build_documents()
    assert not (outside / "proof").exists()


@pytest.mark.parametrize("bad_input", ["notation", "document"])
def test_math_invalid_utf8_is_typed_validation_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    bad_input: str,
) -> None:
    """Malformed TeX never escapes through an uncaught Unicode exception."""
    math_root = tmp_path / "math"
    math_root.mkdir()
    notation = math_root / "malbolge-notation.tex"
    _ = notation.write_text("\n".join(validator.REQUIRED_MACROS), encoding="utf-8")
    document = math_root / "proof.tex"
    _ = document.write_text(
        validator.DOCUMENT_MARKER + "{article}\n" + validator.NOTATION_INCLUDE,
        encoding="utf-8",
    )
    monkeypatch.setattr(validator, "ROOT", tmp_path)
    monkeypatch.setattr(validator, "MATH_ROOT", math_root)
    monkeypatch.setattr(validator, "NOTATION", notation)
    victim = notation if bad_input == NOTATION_CASE else document
    _ = victim.write_bytes(b"\xff")
    with pytest.raises(validator.MathSpecificationError, match="UTF-8"):
        _ = validator.validate_source_layout()


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="FIFO fixture needs POSIX")
def test_math_discovery_rejects_fifo_before_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An untrusted TeX pipe is rejected without blocking the validator."""
    math_root = tmp_path / "math"
    math_root.mkdir()
    mkfifo = cast("Callable[[Path], None]", vars(os)["mkfifo"])
    mkfifo(math_root / "untrusted.tex")
    monkeypatch.setattr(validator, "ROOT", tmp_path)
    monkeypatch.setattr(validator, "MATH_ROOT", math_root)
    with pytest.raises(validator.MathSpecificationError, match="physical regular"):
        _ = validator.document_sources()


@pytest.mark.parametrize("missing", ["root", "notation"])
def test_math_missing_inputs_retain_explicit_diagnostics(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    missing: str,
) -> None:
    """A missing root/include stays distinguishable from a redirect."""
    math_root = tmp_path / "math"
    if missing != MISSING_ROOT_CASE:
        math_root.mkdir()
    monkeypatch.setattr(validator, "ROOT", tmp_path)
    monkeypatch.setattr(validator, "MATH_ROOT", math_root)
    monkeypatch.setattr(validator, "NOTATION", math_root / "malbolge-notation.tex")
    if missing == MISSING_ROOT_CASE:
        with pytest.raises(validator.MathSpecificationError, match="root not found"):
            _ = validator.document_sources()
    else:
        with pytest.raises(
            validator.MathSpecificationError, match="notation file is missing"
        ):
            _ = validator.validate_source_layout()


def _snapshot_fixture(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    math_root = tmp_path / "math"
    math_root.mkdir()
    source = math_root / "proof.tex"
    _ = source.write_text(r"\documentclass{article}", encoding="utf-8")
    monkeypatch.setattr(validator, "ROOT", tmp_path)
    monkeypatch.setattr(validator, "MATH_ROOT", math_root)
    return source


def test_math_source_read_rejects_oversized_input(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """TeX admission bounds file size even for physically regular inputs."""
    source = _snapshot_fixture(tmp_path, monkeypatch)
    with source.open("wb") as stream:
        _ = stream.truncate(1_048_577)
    with pytest.raises(validator.MathSpecificationError, match="byte limit"):
        _ = validator.document_sources()


def test_math_source_read_rejects_swap_between_status_and_open(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A byte-identical inode swap cannot pass as the admitted source."""
    source = _snapshot_fixture(tmp_path, monkeypatch)
    replacement = tmp_path / "replacement.tex"
    _ = replacement.write_bytes(source.read_bytes())
    original_open = os.open

    def swapping_open(path: str | os.PathLike[str], flags: int) -> int:
        if Path(path) == source:
            _ = replacement.replace(source)
        return original_open(path, flags)

    monkeypatch.setattr(os, "open", swapping_open)
    with pytest.raises(validator.MathSpecificationError, match="changed"):
        _ = validator.document_sources()


def test_math_source_read_rejects_swap_after_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Byte-identical replacement after reading invalidates identity."""
    source = _snapshot_fixture(tmp_path, monkeypatch)
    replacement = tmp_path / "replacement.tex"
    _ = replacement.write_bytes(source.read_bytes())
    original_lstat = Path.lstat
    original_open = os.open
    opened = False
    swapped = False

    def observing_open(path: str | os.PathLike[str], flags: int) -> int:
        nonlocal opened
        descriptor = original_open(path, flags)
        if Path(path) == source:
            opened = True
        return descriptor

    def swapping_lstat(path: Path) -> os.stat_result:
        nonlocal swapped
        if path == source and opened and not swapped:
            swapped = True
            _ = replacement.replace(source)
        return original_lstat(path)

    monkeypatch.setattr(os, "open", observing_open)
    monkeypatch.setattr(Path, "lstat", swapping_lstat)
    with pytest.raises(validator.MathSpecificationError, match="changed"):
        _ = validator.document_sources()


def test_math_source_read_rejects_parent_redirect_after_open(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Repointing a parent after admission invalidates otherwise same bytes."""
    source = _snapshot_fixture(tmp_path, monkeypatch)
    original = tmp_path / "original"
    original_open = os.open

    def redirecting_open(path: str | os.PathLike[str], flags: int) -> int:
        if Path(path) == source:
            _ = source.parent.rename(original)
            source.parent.symlink_to(original, target_is_directory=True)
        return original_open(path, flags)

    monkeypatch.setattr(os, "open", redirecting_open)
    with pytest.raises(validator.MathSpecificationError, match="redirect"):
        _ = validator.document_sources()


def test_math_source_read_rejects_inplace_mutation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Changed inodes and changed bytes are both excluded from snapshots."""
    source = _snapshot_fixture(tmp_path, monkeypatch)
    original_fstat = os.fstat
    observations = 0

    def mutating_fstat(fd: int) -> os.stat_result:
        nonlocal observations
        observations += 1
        if observations == SECOND_OBSERVATION:
            _ = source.write_bytes(b"changed")
        return original_fstat(fd)

    monkeypatch.setattr(os, "fstat", mutating_fstat)
    with pytest.raises(validator.MathSpecificationError, match="changed"):
        _ = validator.document_sources()


def _math_log_fixture(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[Path, Path]:
    math_root = tmp_path / "math"
    math_root.mkdir()
    source = math_root / "proof.tex"
    _ = source.write_text(r"\documentclass{article}", encoding="ascii")
    cache_root = tmp_path / ".cache" / "latex"
    output = cache_root / "proof"
    output.mkdir(parents=True)
    monkeypatch.setattr(validator, "ROOT", tmp_path)
    monkeypatch.setattr(validator, "MATH_ROOT", math_root)
    monkeypatch.setattr(validator, "CACHE_ROOT", cache_root)
    monkeypatch.setattr(validator, "latex_compiler", lambda: "pdflatex")
    return source, output / "build.stdout.txt"


def _compile_math_source(source: Path) -> None:
    compilation = cast("Callable[[Path], None]", vars(validator)["_compile_document"])
    compilation(source)


@pytest.mark.parametrize("fault_type", [OSError, ValueError, RuntimeError])
@pytest.mark.parametrize("operation", ["lstat", "junction"])
def test_math_cache_parent_host_status_faults_are_typed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault_type: type[Exception],
    operation: str,
) -> None:
    """Cache parent status failures cannot redirect build log publication."""
    _source, log = _math_log_fixture(tmp_path, monkeypatch)
    _ = log.write_text(OUTSIDE_LOG_TEXT, encoding="utf-8")
    if operation == "lstat":
        original_lstat = Path.lstat

        def fail_lstat(path: Path) -> os.stat_result:
            if path == log.parent:
                raise fault_type("injected log parent lstat failure")
            return original_lstat(path)

        monkeypatch.setattr(Path, "lstat", fail_lstat)
    else:
        original_junction = Path.is_junction

        def fail_junction(path: Path) -> bool:
            if path == log.parent:
                raise fault_type("injected log parent junction failure")
            return original_junction(path)

        monkeypatch.setattr(Path, "is_junction", fail_junction)
    with pytest.raises(validator.MathSpecificationError, match="cache"):
        validator._write_math_build_log(log, COMPILED_LOG_TEXT)
    assert log.read_text(encoding="utf-8") == OUTSIDE_LOG_TEXT


@pytest.mark.parametrize("fault_type", [OSError, ValueError, RuntimeError])
@pytest.mark.parametrize("operation", ["lstat", "symlink", "junction"])
def test_math_log_leaf_host_status_faults_are_typed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault_type: type[Exception],
    operation: str,
) -> None:
    """A broken retained-log leaf stat or redirect probe rejects publication."""
    _source, log = _math_log_fixture(tmp_path, monkeypatch)
    _ = log.write_text(OUTSIDE_LOG_TEXT, encoding="utf-8")
    if operation == "lstat":
        original_lstat = Path.lstat

        def fail_lstat(path: Path) -> os.stat_result:
            if path == log:
                raise fault_type("injected log leaf lstat failure")
            return original_lstat(path)

        monkeypatch.setattr(Path, "lstat", fail_lstat)
    else:
        method = "is_symlink" if operation == "symlink" else "is_junction"
        original_status = getattr(Path, method)

        def fail_status(path: Path) -> bool:
            if path == log:
                raise fault_type("injected log leaf redirect failure")
            return original_status(path)

        monkeypatch.setattr(Path, method, fail_status)
    with pytest.raises(validator.MathSpecificationError, match="log"):
        validator._write_math_build_log(log, COMPILED_LOG_TEXT)
    assert log.read_text(encoding="utf-8") == OUTSIDE_LOG_TEXT


@pytest.mark.parametrize("fault_type", [OSError, ValueError, RuntimeError])
def test_math_log_temporary_creation_host_faults_are_typed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault_type: type[Exception],
) -> None:
    """Temporary allocation failure is not an uncaught host exception."""
    _source, log = _math_log_fixture(tmp_path, monkeypatch)
    _ = log.write_text(OUTSIDE_LOG_TEXT, encoding="utf-8")

    def fail_mkstemp(*_args: object, **_kwargs: object) -> tuple[int, str]:
        raise fault_type("injected mkstemp failure")

    monkeypatch.setattr(validator.tempfile, "mkstemp", fail_mkstemp)
    with pytest.raises(validator.MathSpecificationError, match="log"):
        validator._write_math_build_log(log, COMPILED_LOG_TEXT)
    assert log.read_text(encoding="utf-8") == OUTSIDE_LOG_TEXT
    assert tuple(log.parent.iterdir()) == (log,)


@pytest.mark.parametrize("forgery", ("foreign-parent", "foreign-name", "foreign-inode"))
def test_math_log_rejects_forged_temporary_path_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    forgery: str,
) -> None:
    """A forged temporary name cannot replace or remove an unrelated file."""
    _source, log = _math_log_fixture(tmp_path, monkeypatch)
    _ = log.write_text(OUTSIDE_LOG_TEXT, encoding="utf-8")
    foreign = (
        tmp_path / "foreign" / ".build.stdout.abcdefgh"
        if forgery == "foreign-parent"
        else log.parent
        / ("unrelated.txt" if forgery == "foreign-name" else ".build.stdout.abcdefgh")
    )
    foreign.parent.mkdir(parents=True, exist_ok=True)
    _ = foreign.write_text(OUTSIDE_LOG_TEXT, encoding="utf-8")
    original_mkstemp = validator.tempfile.mkstemp
    allocated: list[tuple[int, Path]] = []

    def forged_mkstemp(*, dir: Path, prefix: str) -> tuple[int, str]:
        descriptor, stage = original_mkstemp(dir=dir, prefix=prefix)
        allocated.append((descriptor, Path(stage)))
        return descriptor, str(foreign)

    monkeypatch.setattr(validator.tempfile, "mkstemp", forged_mkstemp)
    try:
        with pytest.raises(validator.MathSpecificationError, match="temporary path"):
            validator._write_math_build_log(log, COMPILED_LOG_TEXT)
        for descriptor, _stage in allocated:
            with pytest.raises(OSError):
                _ = os.fstat(descriptor)
        assert foreign.read_text(encoding="utf-8") == OUTSIDE_LOG_TEXT
        assert log.read_text(encoding="utf-8") == OUTSIDE_LOG_TEXT
    finally:
        for _descriptor, stage in allocated:
            stage.unlink(missing_ok=True)


def test_math_log_does_not_unlink_replaced_staging_inode(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A changed staging name must not delete a foreign inode in cleanup."""
    _source, log = _math_log_fixture(tmp_path, monkeypatch)
    _ = log.write_text(OUTSIDE_LOG_TEXT, encoding="utf-8")
    original_check = validator._check_math_log_temporary_identity
    replaced: list[Path] = []

    def swap_before_check(path: Path, identity: tuple[int, int]) -> None:
        foreign = path.parent / "foreign-owned-file.txt"
        _ = foreign.write_text(OUTSIDE_LOG_TEXT, encoding="utf-8")
        path.unlink()
        foreign.rename(path)
        replaced.append(path)
        original_check(path, identity)

    monkeypatch.setattr(
        validator, "_check_math_log_temporary_identity", swap_before_check
    )
    with pytest.raises(
        validator.MathSpecificationError, match="temporary inode changed"
    ):
        validator._write_math_build_log(log, COMPILED_LOG_TEXT)
    assert len(replaced) == 1
    assert replaced[0].read_text(encoding="utf-8") == OUTSIDE_LOG_TEXT
    assert log.read_text(encoding="utf-8") == OUTSIDE_LOG_TEXT


@pytest.mark.parametrize("fault_type", [OSError, ValueError, RuntimeError])
def test_math_log_wrapper_failure_releases_owned_descriptor(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault_type: type[Exception],
) -> None:
    """An unwrapped temporary log descriptor cannot remain owned or linked."""
    _source, log = _math_log_fixture(tmp_path, monkeypatch)
    _ = log.write_text(OUTSIDE_LOG_TEXT, encoding="utf-8")
    owned: list[int] = []

    def fail_fdopen(descriptor: int, *_args: object, **_kwargs: object) -> object:
        owned.append(descriptor)
        raise fault_type("injected log wrapper failure")

    monkeypatch.setattr(os, "fdopen", fail_fdopen)
    with pytest.raises(validator.MathSpecificationError, match="log"):
        validator._write_math_build_log(log, COMPILED_LOG_TEXT)
    assert len(owned) == 1
    with pytest.raises(OSError):
        _ = os.fstat(owned[0])
    assert log.read_text(encoding="utf-8") == OUTSIDE_LOG_TEXT
    assert tuple(log.parent.iterdir()) == (log,)


@pytest.mark.parametrize("fault_type", [OSError, ValueError, RuntimeError])
def test_math_log_write_failure_preserves_prior_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault_type: type[Exception],
) -> None:
    """Stream writes that fail do not replace the previous build log."""
    _source, log = _math_log_fixture(tmp_path, monkeypatch)
    _ = log.write_text(OUTSIDE_LOG_TEXT, encoding="utf-8")
    original_fdopen = os.fdopen

    class FailingWriteStream:
        def __init__(self, descriptor: int) -> None:
            self.stream = original_fdopen(
                descriptor, "w", encoding="utf-8", newline="\n"
            )

        def __enter__(self) -> Self:
            return self

        def __exit__(self, *_args: object) -> None:
            self.stream.close()

        def write(self, _text: str) -> int:
            raise fault_type("injected math log write failure")

        def flush(self) -> None:
            self.stream.flush()

    monkeypatch.setattr(
        os,
        "fdopen",
        lambda descriptor, *_args, **_kwargs: FailingWriteStream(descriptor),
    )
    with pytest.raises(validator.MathSpecificationError, match="log"):
        validator._write_math_build_log(log, COMPILED_LOG_TEXT)
    assert log.read_text(encoding="utf-8") == OUTSIDE_LOG_TEXT
    assert tuple(log.parent.iterdir()) == (log,)


@pytest.mark.parametrize("reported", [None, True, 1.0, "1"])
def test_math_log_rejects_noninteger_write_receipts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    reported: object,
) -> None:
    """A forged length receipt cannot publish an empty or truncated log."""
    _source, log = _math_log_fixture(tmp_path, monkeypatch)
    _ = log.write_text(OUTSIDE_LOG_TEXT, encoding="utf-8")
    original_fdopen = os.fdopen

    class ForgedWriteStream:
        def __init__(self, descriptor: int) -> None:
            self.stream = original_fdopen(
                descriptor, "w", encoding="utf-8", newline="\n"
            )

        def __enter__(self) -> Self:
            return self

        def __exit__(self, *_args: object) -> None:
            self.stream.close()

        def write(self, _text: str) -> object:
            return reported

        def flush(self) -> None:
            self.stream.flush()

    monkeypatch.setattr(
        os,
        "fdopen",
        lambda descriptor, *_args, **_kwargs: ForgedWriteStream(descriptor),
    )
    with pytest.raises(validator.MathSpecificationError, match="log"):
        validator._write_math_build_log(log, "x")
    assert log.read_text(encoding="utf-8") == OUTSIDE_LOG_TEXT
    assert tuple(log.parent.iterdir()) == (log,)


@pytest.mark.parametrize("fault_type", [OSError, ValueError, RuntimeError])
def test_math_log_flush_failure_preserves_prior_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault_type: type[Exception],
) -> None:
    """A failed explicit flush cannot publish an unpersisted build receipt."""
    _source, log = _math_log_fixture(tmp_path, monkeypatch)
    _ = log.write_text(OUTSIDE_LOG_TEXT, encoding="utf-8")
    original_fdopen = os.fdopen

    class FailingFlushStream:
        def __init__(self, descriptor: int) -> None:
            self.stream = original_fdopen(
                descriptor, "w", encoding="utf-8", newline="\n"
            )

        def __enter__(self) -> Self:
            return self

        def __exit__(self, *_args: object) -> None:
            self.stream.close()

        def write(self, text: str) -> int:
            return self.stream.write(text)

        def flush(self) -> None:
            raise fault_type("injected math log flush failure")

    monkeypatch.setattr(
        os,
        "fdopen",
        lambda descriptor, *_args, **_kwargs: FailingFlushStream(descriptor),
    )
    with pytest.raises(validator.MathSpecificationError, match="log"):
        validator._write_math_build_log(log, COMPILED_LOG_TEXT)
    assert log.read_text(encoding="utf-8") == OUTSIDE_LOG_TEXT
    assert tuple(log.parent.iterdir()) == (log,)


@pytest.mark.parametrize("fault_type", [OSError, ValueError, RuntimeError])
def test_math_latex_subprocess_host_faults_are_typed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault_type: type[Exception],
) -> None:
    """TeX process transport failure never publishes a successful log."""
    source, log = _math_log_fixture(tmp_path, monkeypatch)

    def fail_run(*_args: object, **_kwargs: object) -> object:
        raise fault_type("injected LaTeX runner fault")

    monkeypatch.setattr(sp, "run", fail_run)
    with pytest.raises(validator.MathSpecificationError, match="LaTeX"):
        _compile_math_source(source)
    assert not log.exists()


@pytest.mark.parametrize("field", ["returncode", "stdout", "stderr"])
@pytest.mark.parametrize("malformed", [None, False, b"bytes"])
def test_math_latex_malformed_process_receipts_fail_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    malformed: object,
) -> None:
    """A malformed successful exit or nontext log cannot count as a build."""
    source, log = _math_log_fixture(tmp_path, monkeypatch)
    parts: dict[str, object] = {"returncode": 0, "stdout": "ok", "stderr": ""}
    parts[field] = malformed
    monkeypatch.setattr(
        sp,
        "run",
        lambda command, **_kwargs: sp.CompletedProcess(
            args=command,
            returncode=cast("int", parts["returncode"]),
            stdout=parts["stdout"],
            stderr=parts["stderr"],
        ),
    )
    with pytest.raises(validator.MathSpecificationError, match="LaTeX"):
        _compile_math_source(source)
    assert not log.exists()


@pytest.mark.parametrize("fault_type", [OSError, ValueError, RuntimeError])
def test_math_latex_compiler_lookup_host_faults_are_typed(
    fault_type: type[Exception],
) -> None:
    """An unexpected PATH resolver fault is a controlled tooling error."""

    def fail_lookup(_name: str) -> str | None:
        raise fault_type("injected pdflatex lookup fault")

    with pytest.raises(validator.MathSpecificationError, match="LaTeX"):
        _ = validator.latex_compiler(fail_lookup)


def test_math_latex_compiler_accepts_existing_absolute_executable() -> None:
    """A validated absolute executable retains its PATH resolver identity."""
    import sys

    assert validator.latex_compiler(lambda _name: sys.executable) == sys.executable


def test_math_latex_compiler_rejects_nonexecutable_file(
    tmp_path: Path,
) -> None:
    """An absolute but nonexecutable file is not a compiler authority."""
    candidate = tmp_path / "pdflatex"
    _ = candidate.write_text("not executable", encoding="utf-8")
    with pytest.raises(validator.MathSpecificationError, match="executable"):
        _ = validator.latex_compiler(lambda _name: str(candidate))


def test_math_latex_nonzero_exit_retains_diagnostics(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A real integer failure status publishes only its failure diagnostics."""
    source, log = _math_log_fixture(tmp_path, monkeypatch)
    monkeypatch.setattr(
        sp,
        "run",
        lambda command, **_kwargs: sp.CompletedProcess(
            args=command, returncode=12, stdout="failure out", stderr=" ERR"
        ),
    )
    with pytest.raises(validator.MathSpecificationError, match="exit=12"):
        _compile_math_source(source)
    assert log.read_text(encoding="utf-8") == "failure out ERR"


@pytest.mark.parametrize("malformed", ["", "pdflatex", 7, b"/tmp/pdflatex"])
def test_math_latex_compiler_rejects_malformed_resolver_path(
    malformed: object,
) -> None:
    """Resolver receipts must identify an actual absolute executable file."""
    with pytest.raises(validator.MathSpecificationError, match="LaTeX"):
        _ = validator.latex_compiler(lambda _name: cast("str", malformed))


def test_math_log_rejects_existing_link_before_compiler(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A preexisting linked log cannot redirect compiler diagnostics outside."""
    source, log = _math_log_fixture(tmp_path, monkeypatch)
    outside = tmp_path / "outside.txt"
    _ = outside.write_text(OUTSIDE_LOG_TEXT, encoding="utf-8")
    try:
        _ = log.symlink_to(outside)
    except (OSError, NotImplementedError) as error:
        pytest.skip(f"symlinks unavailable: {error}")

    def never_run(*args: object, **kwargs: object) -> None:
        _ = (args, kwargs)
        pytest.fail("LaTeX compiler ran despite redirected output")

    monkeypatch.setattr(sp, "run", never_run)
    with pytest.raises(validator.MathSpecificationError, match="redirect"):
        _compile_math_source(source)
    assert outside.read_text(encoding="utf-8") == OUTSIDE_LOG_TEXT


def test_math_log_rejects_link_planted_by_compiler(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A compiler process cannot substitute a linked stdout-log pathname."""
    source, log = _math_log_fixture(tmp_path, monkeypatch)
    outside = tmp_path / "outside.txt"
    _ = outside.write_text(OUTSIDE_LOG_TEXT, encoding="utf-8")

    def replace_log(
        command: list[str], **kwargs: object
    ) -> sp.CompletedProcess[str]:
        _ = kwargs
        _ = log.symlink_to(outside)
        return sp.CompletedProcess(
            args=command,
            returncode=0,
            stdout=COMPILED_LOG_TEXT,
            stderr="",
        )

    monkeypatch.setattr(sp, "run", replace_log)
    with pytest.raises(validator.MathSpecificationError, match="redirect"):
        _compile_math_source(source)
    assert outside.read_text(encoding="utf-8") == OUTSIDE_LOG_TEXT


def test_math_log_replaces_regular_output_atomically(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ordinary consecutive builds replace the retained physical stdout log."""
    source, log = _math_log_fixture(tmp_path, monkeypatch)
    _ = log.write_text(OUTSIDE_LOG_TEXT, encoding="utf-8")

    def fake_latex(
        command: list[str], **kwargs: object
    ) -> sp.CompletedProcess[str]:
        _ = kwargs
        return sp.CompletedProcess(
            args=command,
            returncode=0,
            stdout=COMPILED_LOG_TEXT,
            stderr="",
        )

    monkeypatch.setattr(sp, "run", fake_latex)
    _compile_math_source(source)
    assert log.read_text(encoding="utf-8") == COMPILED_LOG_TEXT
    _compile_math_source(source)
    assert log.read_text(encoding="utf-8") == COMPILED_LOG_TEXT
    assert tuple(log.parent.iterdir()) == (log,)


def test_math_log_rejects_nonregular_existing_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Existing directories at the captured log leaf fail before execution."""
    source, log = _math_log_fixture(tmp_path, monkeypatch)
    log.mkdir()
    with pytest.raises(validator.MathSpecificationError, match="regular"):
        _compile_math_source(source)
    assert log.is_dir()


def test_math_log_failed_atomic_replace_preserves_original(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failed replace leaves prior diagnostics intact and no private temp."""
    source, log = _math_log_fixture(tmp_path, monkeypatch)
    _ = log.write_text(OUTSIDE_LOG_TEXT, encoding="utf-8")
    original_replace = Path.replace

    def failing_replace(path: Path, target: Path) -> Path:
        if target == log:
            message = "replacement refused"
            raise PermissionError(message)
        return original_replace(path, target)

    def fake_latex(
        command: list[str], **kwargs: object
    ) -> sp.CompletedProcess[str]:
        _ = kwargs
        return sp.CompletedProcess(
            args=command,
            returncode=0,
            stdout=COMPILED_LOG_TEXT,
            stderr="",
        )

    monkeypatch.setattr(sp, "run", fake_latex)
    monkeypatch.setattr(Path, "replace", failing_replace)
    with pytest.raises(
        validator.MathSpecificationError, match="replace failed"
    ) as caught:
        _compile_math_source(source)
    assert isinstance(caught.value.__cause__, PermissionError)
    assert "replacement refused" in str(caught.value)
    assert log.read_text(encoding="utf-8") == OUTSIDE_LOG_TEXT
    assert tuple(log.parent.iterdir()) == (log,)


@pytest.mark.parametrize(
    "boundary",
    (
        "source-status",
        "source-redirect",
        "source-read",
        "source-scan",
        "source-walk-callback",
        "root-status",
        "notation-status",
        "cache-status",
        "log-status",
        "log-create",
        "latex-lookup",
        "latex-status",
        "latex-run",
    ),
)
@pytest.mark.parametrize("fault_type", [OSError, ValueError, TypeError, RuntimeError])
def test_math_host_failures_do_not_format_foreign_exceptions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    boundary: str,
    fault_type: type[Exception],
) -> None:
    """Host faults remain typed and causal without calling foreign __str__."""

    def unsafe_str(self: Exception) -> str:
        del self
        raise AssertionError("foreign mathematics exception formatter executed")

    foreign = type("ForeignMathHostFault", (fault_type,), {"__str__": unsafe_str})
    fault = foreign("host failure")
    real_latex_compiler = validator.latex_compiler
    source, log = _math_log_fixture(tmp_path, monkeypatch)
    original_lstat = Path.lstat
    original_junction = Path.is_junction
    if boundary in {
        "source-status",
        "root-status",
        "notation-status",
        "cache-status",
        "log-status",
    }:
        affected = {
            "source-status": source,
            "root-status": source.parent,
            "notation-status": source,
            "cache-status": log.parent,
            "log-status": log,
        }[boundary]
        if boundary == "log-status":
            _ = log.write_text("previous", encoding="utf-8")
        if boundary == "notation-status":
            monkeypatch.setattr(validator, "NOTATION", source)

        def failing_lstat(path: Path) -> os.stat_result:
            if path == affected:
                raise fault
            return original_lstat(path)

        monkeypatch.setattr(Path, "lstat", failing_lstat)
    elif boundary == "source-redirect":

        def failing_junction(path: Path) -> bool:
            if path == source:
                raise fault
            return original_junction(path)

        monkeypatch.setattr(Path, "is_junction", failing_junction)
    elif boundary == "source-read":
        original_open = os.open

        def failing_open(path: Path, flags: int) -> int:
            if path == source:
                raise fault
            return original_open(path, flags)

        monkeypatch.setattr(os, "open", failing_open)
    elif boundary in {"source-scan", "source-walk-callback"}:

        def failing_walk(
            path: Path, *, on_error: Callable[[OSError], object] | None = None
        ) -> object:
            del path
            if boundary == "source-walk-callback":
                assert on_error is not None
                on_error(cast("OSError", fault))
                return iter(())
            raise fault

        monkeypatch.setattr(Path, "walk", failing_walk)
    elif boundary == "log-create":
        monkeypatch.setattr(
            validator.tempfile,
            "mkstemp",
            lambda **_kwargs: (_ for _ in ()).throw(fault),
        )
    elif boundary == "latex-run":
        monkeypatch.setattr(
            sp, "run", lambda *_args, **_kwargs: (_ for _ in ()).throw(fault)
        )
    elif boundary == "latex-status":
        import sys

        def failing_access(_path: str, _mode: int) -> bool:
            raise fault

        monkeypatch.setattr(os, "access", failing_access)
        with pytest.raises(validator.MathSpecificationError) as caught:
            _ = real_latex_compiler(lambda _name: sys.executable)
        assert caught.value.__cause__ is fault
        return

    with pytest.raises(validator.MathSpecificationError) as caught:
        if boundary in {"source-status", "source-redirect", "source-read"}:
            _ = validator._read_tex(source)
        elif boundary in {"source-scan", "source-walk-callback"}:
            _ = validator._discovered_tex_paths()
        elif boundary == "root-status":
            _ = validator.document_sources()
        elif boundary == "notation-status":
            validator._validate_notation()
        elif boundary in {"cache-status", "log-status", "log-create"}:
            validator._write_math_build_log(log, "new data")
        elif boundary == "latex-run":
            _compile_math_source(source)
        else:
            _ = real_latex_compiler(lambda _name: (_ for _ in ()).throw(fault))
    assert caught.value.__cause__ is fault


def test_math_native_host_error_keeps_detail_and_cause(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ordinary native failures retain useful system diagnostics."""
    source = _snapshot_fixture(tmp_path, monkeypatch)
    failure = OSError("read permission denied")
    original_open = os.open

    def failing_open(path: Path, flags: int) -> int:
        if path == source:
            raise failure
        return original_open(path, flags)

    monkeypatch.setattr(os, "open", failing_open)
    with pytest.raises(
        validator.MathSpecificationError, match="read permission denied"
    ) as caught:
        _ = validator._read_tex(source)
    assert caught.value.__cause__ is failure


@pytest.mark.parametrize("fault_type", [OSError, ValueError, TypeError, RuntimeError])
def test_math_log_foreign_replace_failure_is_typed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault_type: type[Exception],
) -> None:
    """Failed atomic publication must not invoke a foreign error formatter."""
    _source, log = _math_log_fixture(tmp_path, monkeypatch)
    _ = log.write_text(OUTSIDE_LOG_TEXT, encoding="utf-8")

    def unsafe_str(self: Exception) -> str:
        del self
        raise AssertionError("foreign mathematics replace formatter executed")

    foreign = type("ForeignMathReplaceFault", (fault_type,), {"__str__": unsafe_str})
    fault = foreign("replace rejected")
    original_replace = Path.replace

    def fail_replace(path: Path, target: Path) -> Path:
        if target == log:
            raise fault
        return original_replace(path, target)

    monkeypatch.setattr(Path, "replace", fail_replace)
    with pytest.raises(
        validator.MathSpecificationError, match="replace failed"
    ) as caught:
        validator._write_math_build_log(log, "new data")
    assert caught.value.__cause__ is fault
    assert log.read_text(encoding="utf-8") == OUTSIDE_LOG_TEXT
    assert tuple(log.parent.iterdir()) == (log,)


def test_math_log_cleanup_failure_does_not_mask_primary_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Cleanup diagnostics cannot supersede a failed atomic replacement."""
    _source, log = _math_log_fixture(tmp_path, monkeypatch)
    _ = log.write_text(OUTSIDE_LOG_TEXT, encoding="utf-8")
    primary = PermissionError("replace rejected")

    class ForeignCleanupError(OSError):
        def __str__(self) -> str:
            raise AssertionError("foreign mathematics cleanup formatter executed")

    cleanup = ForeignCleanupError("cleanup rejected")
    original_unlink = Path.unlink
    original_replace = Path.replace

    def fail_replace(path: Path, target: Path) -> Path:
        if target == log:
            raise primary
        return original_replace(path, target)

    def fail_cleanup(path: Path, *, missing_ok: bool = False) -> None:
        if path.parent == log.parent and path.name.startswith(".build.stdout."):
            raise cleanup
        original_unlink(path, missing_ok=missing_ok)

    monkeypatch.setattr(Path, "replace", fail_replace)
    monkeypatch.setattr(Path, "unlink", fail_cleanup)
    try:
        with pytest.raises(
            validator.MathSpecificationError, match="replace failed"
        ) as caught:
            validator._write_math_build_log(log, "new data")
        assert caught.value.__cause__ is primary
        assert any("ForeignCleanupError" in note for note in caught.value.__notes__)
        assert log.read_text(encoding="utf-8") == OUTSIDE_LOG_TEXT
    finally:
        monkeypatch.setattr(Path, "unlink", original_unlink)
        for artifact in log.parent.iterdir():
            if artifact.name.startswith(".build.stdout."):
                artifact.unlink()


def test_math_log_cleanup_only_failure_is_typed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A cleanup fault after publication still has a typed diagnostic."""
    _source, log = _math_log_fixture(tmp_path, monkeypatch)

    class ForeignCleanupError(RuntimeError):
        def __str__(self) -> str:
            raise AssertionError("foreign mathematics cleanup formatter executed")

    cleanup = ForeignCleanupError("cleanup rejected")
    original_unlink = Path.unlink

    def fail_cleanup(path: Path, *, missing_ok: bool = False) -> None:
        if path.parent == log.parent and path.name.startswith(".build.stdout."):
            raise cleanup
        original_unlink(path, missing_ok=missing_ok)

    monkeypatch.setattr(Path, "unlink", fail_cleanup)
    with pytest.raises(
        validator.MathSpecificationError, match="cleanup failed"
    ) as caught:
        validator._write_math_build_log(log, "new data")
    assert caught.value.__cause__ is cleanup
    assert log.read_text(encoding="utf-8") == "new data"


@pytest.mark.parametrize("payload_kind", ["foreign-bytes", "bytearray", "memoryview"])
def test_math_tex_read_rejects_foreign_byte_receipts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, payload_kind: str
) -> None:
    """A source stream must return real bytes before length/decoder hooks."""
    source = _snapshot_fixture(tmp_path, monkeypatch)
    original_fdopen = os.fdopen

    class ForeignBytes(bytes):
        def __len__(self) -> int:
            raise AssertionError("foreign TeX byte length hook executed")

    class ForeignStream:
        def __init__(self, descriptor: int) -> None:
            self.stream = original_fdopen(descriptor, "rb")

        def __enter__(self) -> Self:
            return self

        def __exit__(self, *_args: object) -> None:
            self.stream.close()

        def fileno(self) -> int:
            return self.stream.fileno()

        def read(self, _size: int) -> object:
            data = source.read_bytes()
            if payload_kind == "foreign-bytes":
                return ForeignBytes(data)
            if payload_kind == "bytearray":
                return bytearray(data)
            return memoryview(data)

    monkeypatch.setattr(
        os, "fdopen", lambda descriptor, _mode: ForeignStream(descriptor)
    )
    with pytest.raises(validator.MathSpecificationError, match="byte receipt"):
        _ = validator._read_tex(source)


@pytest.mark.parametrize(
    "receipt_kind", ["foreign-result", "foreign-stdout", "foreign-stderr"]
)
def test_math_latex_rejects_foreign_process_receipts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, receipt_kind: str
) -> None:
    """Untrusted subprocess result objects and strings have no execution hooks."""
    source, log = _math_log_fixture(tmp_path, monkeypatch)

    class ForeignText(str):
        def __add__(self, _other: object) -> str:
            raise AssertionError("foreign LaTeX stdout formatter executed")

        def __len__(self) -> int:
            raise AssertionError("foreign LaTeX text length hook executed")

    class ForeignResult:
        def __getattribute__(self, _name: str) -> object:
            raise AssertionError("foreign LaTeX process receipt hook executed")

    forged: object
    if receipt_kind == "foreign-result":
        forged = ForeignResult()
    else:
        forged = sp.CompletedProcess(
            args=["pdflatex"],
            returncode=0,
            stdout=ForeignText("stdout") if receipt_kind == "foreign-stdout" else "",
            stderr=ForeignText("stderr") if receipt_kind == "foreign-stderr" else "",
        )
    monkeypatch.setattr(sp, "run", lambda *_args, **_kwargs: forged)
    with pytest.raises(validator.MathSpecificationError, match="malformed LaTeX"):
        _compile_math_source(source)
    assert not log.exists()


def test_math_log_rejects_foreign_text_before_writing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Direct log publishing refuses custom text length and writer hooks."""
    _source, log = _math_log_fixture(tmp_path, monkeypatch)
    _ = log.write_text(OUTSIDE_LOG_TEXT, encoding="utf-8")

    class ForeignText(str):
        def __len__(self) -> int:
            raise AssertionError("foreign mathematics log length hook executed")

    with pytest.raises(validator.MathSpecificationError, match="log text"):
        validator._write_math_build_log(log, ForeignText("new data"))
    assert log.read_text(encoding="utf-8") == OUTSIDE_LOG_TEXT
    assert tuple(log.parent.iterdir()) == (log,)


def test_math_tex_invalid_utf8_retains_decoder_cause(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An invalid TeX encoding preserves native byte-offset diagnostics."""
    source = _snapshot_fixture(tmp_path, monkeypatch)
    _ = source.write_bytes(b"\xff")
    with pytest.raises(
        validator.MathSpecificationError, match="invalid mathematics source UTF-8"
    ) as caught:
        _ = validator._read_tex(source)
    assert type(caught.value.__cause__) is UnicodeDecodeError
    assert "position 0" in str(caught.value)


def test_math_tex_rejects_foreign_unicode_formatter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A foreign Unicode failure cannot execute hostile text formatters."""

    class ForeignUnicodeError(UnicodeDecodeError):
        def __str__(self) -> str:
            raise AssertionError("foreign mathematics decoder formatter executed")

    fault = ForeignUnicodeError("utf-8", b"\xff", 0, 1, "decoder failure")

    class FaultyBytes(bytes):
        def decode(self, encoding: str = "utf-8", errors: str = "strict") -> str:
            del encoding, errors
            raise fault

    monkeypatch.setattr(
        validator, "_stable_tex_source_bytes", lambda _path: FaultyBytes(b"data")
    )
    with pytest.raises(
        validator.MathSpecificationError, match="invalid mathematics source UTF-8"
    ) as caught:
        _ = validator._read_tex(Path("untrusted.tex"))
    assert caught.value.__cause__ is fault


@pytest.mark.parametrize("fault_type", [OSError, validator.MathSpecificationError])
def test_math_cli_never_formats_foreign_errors(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    fault_type: type[Exception],
) -> None:
    """CLI failures remain stable even when an exception has hostile __str__."""

    def unsafe_str(self: Exception) -> str:
        del self
        raise AssertionError("foreign mathematics CLI formatter executed")

    foreign = type("ForeignMathCliFault", (fault_type,), {"__str__": unsafe_str})
    fault = foreign("untrusted data")

    def fail_build() -> tuple[Path, ...]:
        raise fault

    monkeypatch.setattr(validator, "build_documents", fail_build)
    assert validator.main() == 1
    output = capsys.readouterr()
    assert "ForeignMathCliFault" in output.err
    assert not output.out


SYMLINK_METHOD = "is_symlink"


def _read_math_snapshot(source: Path) -> str:
    reader = cast("Callable[[Path], str]", vars(validator)["_read_tex"])
    return reader(source)


def _publish_math_log(log: Path, text: str) -> None:
    publisher = cast(
        "Callable[[Path, str], None]", vars(validator)["_write_math_build_log"]
    )
    publisher(log, text)


def _admit_math_temporary(log: Path, descriptor: int, name: str) -> None:
    admission = cast(
        "Callable[[Path, int, str], object]",
        vars(validator)["_admit_math_log_temporary"],
    )
    _ = admission(log, descriptor, name)


class _ForeignReceipt:
    """A foreign host receipt must not run attribute or truth-value hooks."""

    @override
    def __getattribute__(self, name: str) -> object:
        if name.startswith("st_"):
            message = "foreign host receipt attribute accessed"
            raise AssertionError(message)
        return cast("object", object.__getattribute__(self, name))

    def __bool__(self) -> bool:
        message = "foreign host receipt coerced to bool"
        raise AssertionError(message)


@pytest.mark.parametrize("parent", [True, False])
def test_math_tex_rejects_foreign_path_stat_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, parent: bool
) -> None:
    """Source admission must not inspect untrusted stat-shaped properties."""
    source = _snapshot_fixture(tmp_path, monkeypatch)
    victim = source.parent if parent else source
    native_lstat = Path.lstat

    def forged_lstat(path: Path) -> os.stat_result:
        if path == victim:
            return cast("os.stat_result", cast("object", _ForeignReceipt()))
        return native_lstat(path)

    monkeypatch.setattr(Path, "lstat", forged_lstat)
    with pytest.raises(validator.MathSpecificationError, match="native stat"):
        _ = _read_math_snapshot(source)


@pytest.mark.parametrize("receipt", [0, 1, _ForeignReceipt()])
def test_math_tex_rejects_foreign_junction_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, receipt: object
) -> None:
    """Redirect decisions require actual native booleans, not truthiness."""
    source = _snapshot_fixture(tmp_path, monkeypatch)
    native_junction = Path.is_junction

    def forged_junction(path: Path) -> bool:
        if path == source:
            return cast("bool", receipt)
        return native_junction(path)

    monkeypatch.setattr(Path, "is_junction", forged_junction)
    with pytest.raises(
        validator.MathSpecificationError, match="native junction"
    ):
        _ = _read_math_snapshot(source)


def test_math_tex_rejects_foreign_descriptor_stat_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Descriptor identity cannot consult caller-controlled stat attributes."""
    source = _snapshot_fixture(tmp_path, monkeypatch)

    def forged_fstat(descriptor: int) -> os.stat_result:
        del descriptor
        return cast("os.stat_result", cast("object", _ForeignReceipt()))

    monkeypatch.setattr(os, "fstat", forged_fstat)
    with pytest.raises(validator.MathSpecificationError, match="native stat"):
        _ = _read_math_snapshot(source)


@pytest.mark.parametrize("receipt", [True, -1])
def test_math_tex_rejects_foreign_open_descriptor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, receipt: object
) -> None:
    """A fake descriptor must not be wrapped or close an unrelated host fd."""
    source = _snapshot_fixture(tmp_path, monkeypatch)
    native_open = os.open

    def forged_open(path: Path, flags: int) -> int:
        if path == source:
            return cast("int", receipt)
        return native_open(path, flags)

    def unsafe_fdopen(descriptor: int, mode: str) -> object:
        del descriptor, mode
        message = "foreign descriptor was wrapped"
        raise AssertionError(message)

    monkeypatch.setattr(os, "open", forged_open)
    monkeypatch.setattr(os, "fdopen", unsafe_fdopen)
    with pytest.raises(
        validator.MathSpecificationError, match="native descriptor"
    ):
        _ = _read_math_snapshot(source)


@pytest.mark.parametrize("receipt", [0, _ForeignReceipt()])
def test_math_cache_rejects_foreign_junction_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, receipt: object
) -> None:
    """A fake cache-directory redirect verdict cannot admit log writes."""
    _, log = _math_log_fixture(tmp_path, monkeypatch)
    _ = log.write_text(OUTSIDE_LOG_TEXT, encoding="utf-8")
    native_junction = Path.is_junction

    def forged_junction(path: Path) -> bool:
        if path == log.parent:
            return cast("bool", receipt)
        return native_junction(path)

    monkeypatch.setattr(Path, "is_junction", forged_junction)
    with pytest.raises(
        validator.MathSpecificationError, match="native junction"
    ):
        _publish_math_log(log, COMPILED_LOG_TEXT)
    assert log.read_text(encoding="utf-8") == OUTSIDE_LOG_TEXT


def test_math_cache_rejects_foreign_stat_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A fake cache-directory stat cannot certify an output location."""
    _, log = _math_log_fixture(tmp_path, monkeypatch)
    _ = log.write_text(OUTSIDE_LOG_TEXT, encoding="utf-8")
    native_lstat = Path.lstat

    def forged_lstat(path: Path) -> os.stat_result:
        if path == log.parent:
            return cast("os.stat_result", cast("object", _ForeignReceipt()))
        return native_lstat(path)

    monkeypatch.setattr(Path, "lstat", forged_lstat)
    with pytest.raises(validator.MathSpecificationError, match="native stat"):
        _publish_math_log(log, COMPILED_LOG_TEXT)
    assert log.read_text(encoding="utf-8") == OUTSIDE_LOG_TEXT


@pytest.mark.parametrize("method", ["is_symlink", "is_junction"])
@pytest.mark.parametrize("receipt", [0, _ForeignReceipt()])
def test_math_log_leaf_rejects_foreign_redirect_verdict(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    method: str,
    receipt: object,
) -> None:
    """Log-leaf admission must not coerce custom redirect truthiness."""
    _, log = _math_log_fixture(tmp_path, monkeypatch)
    _ = log.write_text(OUTSIDE_LOG_TEXT, encoding="utf-8")
    native_method = (
        Path.is_symlink if method == SYMLINK_METHOD else Path.is_junction
    )

    def forged_redirect(path: Path) -> bool:
        if path == log:
            return cast("bool", receipt)
        return native_method(path)

    monkeypatch.setattr(Path, method, forged_redirect)
    with pytest.raises(
        validator.MathSpecificationError, match=r"native .* receipt"
    ):
        _publish_math_log(log, COMPILED_LOG_TEXT)
    assert log.read_text(encoding="utf-8") == OUTSIDE_LOG_TEXT


def test_math_log_leaf_rejects_foreign_stat_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An existing log cannot be authenticated by custom stat properties."""
    _, log = _math_log_fixture(tmp_path, monkeypatch)
    _ = log.write_text(OUTSIDE_LOG_TEXT, encoding="utf-8")
    native_lstat = Path.lstat

    def forged_lstat(path: Path) -> os.stat_result:
        if path == log:
            return cast("os.stat_result", cast("object", _ForeignReceipt()))
        return native_lstat(path)

    monkeypatch.setattr(Path, "lstat", forged_lstat)
    with pytest.raises(validator.MathSpecificationError, match="native stat"):
        _publish_math_log(log, COMPILED_LOG_TEXT)
    assert log.read_text(encoding="utf-8") == OUTSIDE_LOG_TEXT


@pytest.mark.parametrize("receipt", [1, _ForeignReceipt()])
def test_math_latex_rejects_foreign_file_status(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, receipt: object
) -> None:
    """An absolute compiler path needs a native file status verdict."""
    binary = tmp_path / "pdflatex"
    _ = binary.write_bytes(b"fake executable")
    binary.chmod(0o755)
    native_is_file = Path.is_file

    def forged_is_file(path: Path) -> bool:
        if path == binary:
            return cast("bool", receipt)
        return native_is_file(path)

    monkeypatch.setattr(Path, "is_file", forged_is_file)
    with pytest.raises(validator.MathSpecificationError, match="native"):
        _ = validator.latex_compiler(lambda name: str(binary) if name else None)


@pytest.mark.parametrize("receipt", [1, _ForeignReceipt()])
def test_math_latex_rejects_foreign_access_status(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, receipt: object
) -> None:
    """A real compiler pathname still needs native execute permission."""
    binary = tmp_path / "pdflatex"
    _ = binary.write_bytes(b"fake executable")
    binary.chmod(0o755)
    native_access = os.access

    def forged_access(path: str | bytes, mode: int) -> bool:
        if path == str(binary):
            return cast("bool", receipt)
        return native_access(path, mode)

    monkeypatch.setattr(os, "access", forged_access)
    with pytest.raises(validator.MathSpecificationError, match="native"):
        _ = validator.latex_compiler(lambda name: str(binary) if name else None)


@pytest.mark.parametrize("receipt", [True, -1])
def test_math_log_rejects_foreign_temporary_descriptor_before_host_calls(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    receipt: object,
) -> None:
    """A fake temporary descriptor must never close stdin/stdout or open fds."""
    _, log = _math_log_fixture(tmp_path, monkeypatch)

    def unsafe_fstat(descriptor: int) -> os.stat_result:
        del descriptor
        message = "non-native temporary descriptor probed"
        raise AssertionError(message)

    def unsafe_close(descriptor: int) -> None:
        del descriptor
        message = "non-native temporary descriptor closed"
        raise AssertionError(message)

    monkeypatch.setattr(os, "fstat", unsafe_fstat)
    monkeypatch.setattr(os, "close", unsafe_close)
    with pytest.raises(
        validator.MathSpecificationError, match="native descriptor"
    ):
        _ = _admit_math_temporary(log, cast("int", receipt), "fake")


@pytest.mark.parametrize("receipt", [0, _ForeignReceipt()])
def test_math_scan_rejects_non_native_symlink_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, receipt: object
) -> None:
    """A non-TeX discovered entry needs an authentic link-status verdict."""
    source = _snapshot_fixture(tmp_path, monkeypatch)
    ignored = source.parent / "ignored.txt"
    _ = ignored.write_text("unrelated", encoding="utf-8")
    native_symlink = Path.is_symlink

    def forged_symlink(path: Path) -> bool:
        if path == ignored:
            return cast("bool", receipt)
        return native_symlink(path)

    monkeypatch.setattr(Path, "is_symlink", forged_symlink)
    with pytest.raises(
        validator.MathSpecificationError, match="native symlink"
    ):
        _ = validator.document_sources()


@pytest.mark.parametrize("receipt", [0, _ForeignReceipt()])
def test_math_scan_rejects_non_native_directory_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, receipt: object
) -> None:
    """Symlink directory admission cannot trust a coerced directory verdict."""
    source = _snapshot_fixture(tmp_path, monkeypatch)
    ignored = source.parent / "ignored.txt"
    _ = ignored.symlink_to(source.parent, target_is_directory=True)
    native_is_dir = Path.is_dir

    def forged_is_dir(path: Path) -> bool:
        if path == ignored:
            return cast("bool", receipt)
        return native_is_dir(path)

    monkeypatch.setattr(Path, "is_dir", forged_is_dir)
    with pytest.raises(
        validator.MathSpecificationError, match="native directory"
    ):
        _ = validator.document_sources()


@pytest.mark.parametrize(
    "wrong_args", ["pdflatex", ("pdflatex",), [], ["wrong-program"]]
)
def test_math_latex_rejects_unbound_process_command_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    wrong_args: object,
) -> None:
    """A successful process receipt must bind the actual invoked TeX argv."""
    source, log = _math_log_fixture(tmp_path, monkeypatch)

    def forged_run(
        command: list[str], **kwargs: object
    ) -> sp.CompletedProcess[str]:
        del command, kwargs
        return sp.CompletedProcess(
            args=cast("list[str]", wrong_args),
            returncode=0,
            stdout=COMPILED_LOG_TEXT,
            stderr="",
        )

    monkeypatch.setattr(sp, "run", forged_run)
    with pytest.raises(
        validator.MathSpecificationError, match="command receipt"
    ):
        _compile_math_source(source)
    assert not log.exists()


def test_math_latex_rejects_foreign_argument_equality(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A string subclass cannot execute custom equality during argv matching."""
    source, log = _math_log_fixture(tmp_path, monkeypatch)

    @final
    class ForeignArg(str):  # ruff: ignore[subclass-builtin] - tests native type gate.
        __slots__ = ()
        __hash__ = str.__hash__

        @override
        def __eq__(self, other: object) -> bool:
            del other
            message = "foreign command equality hook executed"
            raise AssertionError(message)

    def forged_run(
        command: list[str], **kwargs: object
    ) -> sp.CompletedProcess[str]:
        del kwargs
        args = list(command)
        args[-1] = ForeignArg(args[-1])
        return sp.CompletedProcess(
            args=args, returncode=0, stdout=COMPILED_LOG_TEXT, stderr=""
        )

    monkeypatch.setattr(sp, "run", forged_run)
    with pytest.raises(
        validator.MathSpecificationError, match="command receipt"
    ):
        _compile_math_source(source)
    assert not log.exists()


def test_math_latex_execution_has_a_bounded_timeout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """TeX execution cannot wait indefinitely on pathological source files."""
    source, log = _math_log_fixture(tmp_path, monkeypatch)

    def capture_run(
        command: list[str], **kwargs: object
    ) -> sp.CompletedProcess[str]:
        assert kwargs["timeout"] == validator.LATEX_TIMEOUT_SECONDS
        assert kwargs["shell"] is False
        return sp.CompletedProcess(
            args=command, returncode=0, stdout=COMPILED_LOG_TEXT, stderr=""
        )

    monkeypatch.setattr(sp, "run", capture_run)
    _compile_math_source(source)
    assert log.read_text(encoding="utf-8") == COMPILED_LOG_TEXT


def test_math_latex_timeout_is_typed_and_preserves_cause(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A subprocess timeout retains its host cause and publishes no success."""
    source, log = _math_log_fixture(tmp_path, monkeypatch)
    fault = sp.TimeoutExpired(cmd=["pdflatex"], timeout=1)

    def timed_out(
        command: list[str], **kwargs: object
    ) -> sp.CompletedProcess[str]:
        del command, kwargs
        raise fault

    monkeypatch.setattr(sp, "run", timed_out)
    with pytest.raises(
        validator.MathSpecificationError, match="timed out"
    ) as caught:
        _compile_math_source(source)
    assert caught.value.__cause__ is fault
    assert not log.exists()


BAD_PROGRAM_RECEIPT = "mismatched-program"


@pytest.mark.parametrize("kind", [BAD_PROGRAM_RECEIPT, "foreign-list"])
def test_math_latex_rejects_malformed_successful_argv(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: str
) -> None:
    """Even same-length native argv and custom lists fail command provenance."""
    source, log = _math_log_fixture(tmp_path, monkeypatch)

    @final
    class ForeignList(list[str]):  # ruff: ignore[subclass-builtin] - adversarial receipt.
        __hash__ = None

        @override
        def __eq__(self, other: object) -> bool:
            del other
            message = "foreign command list equality executed"
            raise AssertionError(message)

    def forged_run(
        command: list[str], **kwargs: object
    ) -> sp.CompletedProcess[str]:
        del kwargs
        args = list(command)
        if kind == BAD_PROGRAM_RECEIPT:
            args[0] = "wrong-compiler"
        else:
            args = ForeignList(args)
        return sp.CompletedProcess(
            args=args, returncode=0, stdout=COMPILED_LOG_TEXT, stderr=""
        )

    monkeypatch.setattr(sp, "run", forged_run)
    with pytest.raises(
        validator.MathSpecificationError, match="command receipt"
    ):
        _compile_math_source(source)
    assert not log.exists()


def test_math_latex_timeout_never_formats_foreign_host_exception(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A foreign timeout formatter cannot execute at the process boundary."""
    source, log = _math_log_fixture(tmp_path, monkeypatch)

    @final
    class ForeignTimeout(sp.TimeoutExpired):
        @override
        def __str__(self) -> str:
            message = "foreign timeout formatter executed"
            raise AssertionError(message)

    fault = ForeignTimeout(cmd=["pdflatex"], timeout=1)

    def timed_out(
        command: list[str], **kwargs: object
    ) -> sp.CompletedProcess[str]:
        del command, kwargs
        raise fault

    monkeypatch.setattr(sp, "run", timed_out)
    with pytest.raises(
        validator.MathSpecificationError, match="timed out"
    ) as caught:
        _compile_math_source(source)
    assert caught.value.__cause__ is fault
    assert not log.exists()
