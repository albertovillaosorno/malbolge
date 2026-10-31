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
from typing import TYPE_CHECKING, Self, cast

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

    def replace_log(*args: object, **kwargs: object) -> sp.CompletedProcess[str]:
        _ = (args, kwargs)
        _ = log.symlink_to(outside)
        return sp.CompletedProcess(
            args=("pdflatex",),
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

    def fake_latex(*args: object, **kwargs: object) -> sp.CompletedProcess[str]:
        _ = (args, kwargs)
        return sp.CompletedProcess(
            args=("pdflatex",),
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

    def fake_latex(*args: object, **kwargs: object) -> sp.CompletedProcess[str]:
        _ = (args, kwargs)
        return sp.CompletedProcess(
            args=("pdflatex",),
            returncode=0,
            stdout=COMPILED_LOG_TEXT,
            stderr="",
        )

    monkeypatch.setattr(sp, "run", fake_latex)
    monkeypatch.setattr(Path, "replace", failing_replace)
    with pytest.raises(PermissionError, match="replacement refused"):
        _compile_math_source(source)
    assert log.read_text(encoding="utf-8") == OUTSIDE_LOG_TEXT
    assert tuple(log.parent.iterdir()) == (log,)
