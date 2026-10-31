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
#   - Synthetic tests for content-relocatable compatible placement.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#

"""Synthetic tests for content-relocatable compatible placement."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import shutil
from typing import TYPE_CHECKING
from typing import cast

from algorithms.diff import relocatable as relocatable_module
from algorithms.diff.exact import build_exact_plan
from algorithms.diff.model import OracleLiteral
from algorithms.diff.model import SourceSlice
from algorithms.diff.model import TreeModelError
from algorithms.diff.relocatable import RangeLocator
from algorithms.diff.relocatable import RelocatableInstruction
from algorithms.diff.relocatable import RelocatableSourceRange
from algorithms.diff.relocatable import RelocationError
from algorithms.diff.relocatable import build_relocatable_plan
from algorithms.diff.relocatable import materialize_relocatable_plan
import pytest

if TYPE_CHECKING:
    from algorithms.diff.model import ExactAuthoringPlan
    from algorithms.diff.relocatable import RelocatableAuthoringPlan

_BLOCKS = 64
_INSERTION = b"candidate-insertion-preserved"
_TARGET = b"TARGET-ONLY-CORRECTION"
_CREATED = b"created-target"
_FOREIGN_STAGING = b"foreign-writer"
_FOREIGN_OUTPUT = b"foreign-output"
_POSIX = "posix"
_ROOT_TARGET = b"target"


def _expect(condition: object, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _blocks(label: str) -> bytes:
    return b"".join(
        hashlib.sha256(f"{label}:{index}".encode()).digest()
        for index in range(_BLOCKS)
    )


def _write(root: Path, relative: str, data: bytes) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    _ = path.write_bytes(data)


def _fixture(tmp_path: Path) -> tuple[Path, Path, bytes]:
    source = tmp_path / "source"
    oracle = tmp_path / "oracle"
    base = _blocks("base")
    _write(source, "code.bin", base)
    _write(source, "copy.bin", _blocks("copy"))
    _write(oracle, "code.bin", base[:900] + _TARGET + base[900:])
    _write(oracle, "copy.bin", _blocks("copy"))
    _write(oracle, "created.bin", _CREATED)
    return source, oracle, base


def test_candidate_insertion_inside_source_range_is_preserved(
    tmp_path: Path,
) -> None:
    """Relocate source spans around an insertion without absolute offsets."""
    source, oracle, base = _fixture(tmp_path)
    exact = build_exact_plan(source, oracle)
    plan = build_relocatable_plan(source, exact)
    candidate = tmp_path / "candidate"
    insertion_offset = 1400
    _write(
        candidate,
        "code.bin",
        base[:insertion_offset] + _INSERTION + base[insertion_offset:],
    )
    _write(candidate, "copy.bin", _blocks("copy") + b"candidate-tail")
    output = tmp_path / "out"

    materialize_relocatable_plan(candidate, plan, output)

    expected_code = (
        base[:900]
        + _TARGET
        + base[900:insertion_offset]
        + _INSERTION
        + base[insertion_offset:]
    )
    _expect(
        (output / "code.bin").read_bytes() == expected_code, "insertion lost"
    )
    _expect(
        (output / "copy.bin").read_bytes()
        == _blocks("copy") + b"candidate-tail",
        "whole-file candidate difference was not preserved",
    )
    _expect(
        (output / "created.bin").read_bytes() == _CREATED,
        "created target file changed",
    )


def test_relocatable_materialization_wraps_path_resolution_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Keep candidate resolution failures inside relocatable placement."""
    source, oracle, base = _fixture(tmp_path)
    plan = build_relocatable_plan(source, build_exact_plan(source, oracle))
    candidate = tmp_path / "candidate"
    _write(candidate, "code.bin", base)
    _write(candidate, "copy.bin", _blocks("copy"))
    blocked = candidate / "code.bin"
    original_resolve = Path.resolve

    def fail_resolve(path: Path, *, strict: bool = False) -> Path:
        if path == blocked:
            message = "blocked relocatable path"
            raise PermissionError(message)
        return original_resolve(path, strict=strict)

    monkeypatch.setattr(Path, "resolve", fail_resolve)
    output = tmp_path / "out"
    with pytest.raises(RelocationError, match="path resolution failed"):
        materialize_relocatable_plan(candidate, plan, output)
    _expect(not output.exists(), "resolution failure published output")


def test_relocatable_publication_collision_preserves_foreign_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A late destination race cannot be replaced by relocatable output."""
    source, oracle, base = _fixture(tmp_path)
    plan = build_relocatable_plan(source, build_exact_plan(source, oracle))
    candidate = tmp_path / "candidate"
    _write(candidate, "code.bin", base)
    _write(candidate, "copy.bin", _blocks("copy"))
    output = tmp_path / "out"

    def collide(staging: Path, destination: Path) -> None:
        _ = staging
        destination.mkdir()
        _ = (destination / "foreign.txt").write_bytes(_FOREIGN_OUTPUT)
        raise FileExistsError(destination)

    monkeypatch.setattr(
        relocatable_module, "publish_directory_no_replace", collide
    )
    with pytest.raises(RelocationError, match="output publication failed"):
        materialize_relocatable_plan(candidate, plan, output)

    assert (output / "foreign.txt").read_bytes() == _FOREIGN_OUTPUT
    assert not (tmp_path / ".out.relocatable-staging").exists()


def test_relocatable_cleanup_failure_preserves_primary_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Cleanup failure augments rather than replaces the staging write error."""
    source, oracle, base = _fixture(tmp_path)
    plan = build_relocatable_plan(source, build_exact_plan(source, oracle))
    candidate = tmp_path / "candidate"
    _write(candidate, "code.bin", base)
    _write(candidate, "copy.bin", _blocks("copy"))
    output = tmp_path / "out"
    blocked = tmp_path / ".out.relocatable-staging" / "created.bin"
    original_write = Path.write_bytes

    def fail_write(path: Path, data: bytes) -> int:
        if path == blocked:
            message = "blocked relocatable write"
            raise PermissionError(message)
        return original_write(path, data)

    def fail_cleanup(path: Path) -> None:
        _ = path
        message = "blocked relocatable cleanup"
        raise PermissionError(message)

    monkeypatch.setattr(Path, "write_bytes", fail_write)
    monkeypatch.setattr(shutil, "rmtree", fail_cleanup)
    with pytest.raises(
        RelocationError,
        match=r"relocatable output write failed.*staging cleanup failed",
    ):
        materialize_relocatable_plan(candidate, plan, output)


def test_relocatable_staging_status_error_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An inaccessible staging path cannot masquerade as absent."""
    source, oracle, _ = _fixture(tmp_path)
    plan = build_relocatable_plan(source, build_exact_plan(source, oracle))
    candidate = tmp_path / "candidate"
    _write(candidate, "code.bin", _blocks("base"))
    _write(candidate, "copy.bin", _blocks("copy"))
    output = tmp_path / "out"
    staging = tmp_path / ".out.relocatable-staging"
    original_lstat = Path.lstat

    def fail_lstat(path: Path) -> object:
        if path == staging:
            message = "blocked relocatable staging status"
            raise PermissionError(message)
        return original_lstat(path)

    monkeypatch.setattr(Path, "lstat", fail_lstat)
    with pytest.raises(RelocationError, match="staging root status failed"):
        materialize_relocatable_plan(candidate, plan, output)
    _expect(not output.exists(), "status failure published relocatable output")


def test_relocatable_output_write_error_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A staging write failure remains inside RelocationError."""
    source, oracle, base = _fixture(tmp_path)
    plan = build_relocatable_plan(source, build_exact_plan(source, oracle))
    candidate = tmp_path / "candidate"
    _write(candidate, "code.bin", base)
    _write(candidate, "copy.bin", _blocks("copy"))
    output = tmp_path / "out"
    blocked = tmp_path / ".out.relocatable-staging" / "created.bin"
    original_write = Path.write_bytes

    def fail_write(path: Path, data: bytes) -> int:
        if path == blocked:
            message = "blocked relocatable output write"
            raise PermissionError(message)
        return original_write(path, data)

    monkeypatch.setattr(Path, "write_bytes", fail_write)
    with pytest.raises(
        RelocationError, match="relocatable output write failed"
    ):
        materialize_relocatable_plan(candidate, plan, output)
    _expect(not output.exists(), "write failure published relocatable output")
    _expect(
        not (tmp_path / ".out.relocatable-staging").exists(),
        "relocatable staging survived write failure",
    )


def test_byte_boundary_change_remains_fail_closed(tmp_path: Path) -> None:
    """Document why semantic token placement is the next compatibility layer."""
    source, oracle, base = _fixture(tmp_path)
    plan = build_relocatable_plan(source, build_exact_plan(source, oracle))
    candidate = tmp_path / "candidate"
    _write(candidate, "code.bin", b"X" + base[1:])
    _write(candidate, "copy.bin", _blocks("copy"))
    output = tmp_path / "out"

    with pytest.raises(RelocationError, match="boundary"):
        materialize_relocatable_plan(candidate, plan, output)
    _expect(not output.exists(), "byte-changed boundary published output")


def test_missing_boundary_fails_before_publishing_output(
    tmp_path: Path,
) -> None:
    """Reject a candidate that destroys required source placement evidence."""
    source, oracle, _ = _fixture(tmp_path)
    plan = build_relocatable_plan(source, build_exact_plan(source, oracle))
    candidate = tmp_path / "candidate"
    _write(candidate, "code.bin", _blocks("unrelated"))
    _write(candidate, "copy.bin", _blocks("copy"))
    output = tmp_path / "out"

    with pytest.raises(RelocationError, match="boundary"):
        materialize_relocatable_plan(candidate, plan, output)
    _expect(not output.exists(), "rejected relocatable output was published")


def test_ambiguous_boundary_fails_closed(tmp_path: Path) -> None:
    """Reject duplicate boundary windows instead of guessing a placement."""
    source, oracle, base = _fixture(tmp_path)
    plan = build_relocatable_plan(source, build_exact_plan(source, oracle))
    candidate = tmp_path / "candidate"
    duplicated = base + base
    _write(candidate, "code.bin", duplicated)
    _write(candidate, "copy.bin", _blocks("copy"))
    output = tmp_path / "out"

    with pytest.raises(RelocationError, match="ambiguous"):
        materialize_relocatable_plan(candidate, plan, output)
    _expect(not output.exists(), "ambiguous relocatable output was published")


def test_relocatable_authoring_rejects_linked_source_after_exact_plan(
    tmp_path: Path,
) -> None:
    """An in-tree link cannot impersonate an admitted source span."""
    source, oracle, _ = _fixture(tmp_path)
    exact = build_exact_plan(source, oracle)
    code = source / "code.bin"
    shadow = source / "shadow.bin"
    _ = shadow.write_bytes(code.read_bytes())
    code.unlink()
    try:
        code.symlink_to(shadow)
    except OSError:
        pytest.skip("filesystem symlinks unavailable")
    with pytest.raises(RelocationError, match="relocatable source read failed"):
        _ = build_relocatable_plan(source, exact)


def test_relocatable_materialization_rejects_linked_candidate(
    tmp_path: Path,
) -> None:
    """A linked in-tree candidate cannot impersonate its admitted span."""
    source, oracle, base = _fixture(tmp_path)
    plan = build_relocatable_plan(source, build_exact_plan(source, oracle))
    candidate = tmp_path / "candidate"
    _write(candidate, "shadow.bin", base)
    _write(candidate, "copy.bin", _blocks("copy"))
    try:
        (candidate / "code.bin").symlink_to(candidate / "shadow.bin")
    except OSError:
        pytest.skip("filesystem symlinks unavailable")
    output = tmp_path / "out"
    with pytest.raises(
        RelocationError, match="relocatable candidate read failed"
    ):
        materialize_relocatable_plan(candidate, plan, output)
    _expect(not output.exists(), "linked candidate was published")
    _expect(
        not (tmp_path / ".out.relocatable-staging").exists(),
        "linked candidate left owned staging",
    )


def test_relocatable_rejects_linked_authoring_directory(
    tmp_path: Path,
) -> None:
    """An in-tree directory alias cannot replace a pinned authoring subtree."""
    source = tmp_path / "source"
    oracle = tmp_path / "oracle"
    content = _blocks("source")
    _write(source, "tree/file.bin", content)
    _write(oracle, "tree/file.bin", content[:900] + _TARGET + content[900:])
    exact = build_exact_plan(source, oracle)
    (source / "tree").rename(source / "actual")
    try:
        (source / "tree").symlink_to(
            source / "actual", target_is_directory=True
        )
    except OSError:
        pytest.skip("directory symlinks unavailable")

    with pytest.raises(RelocationError, match="linked path component"):
        _ = build_relocatable_plan(source, exact)


def test_relocatable_rejects_linked_candidate_directory(
    tmp_path: Path,
) -> None:
    """In-tree directory aliases cannot masquerade as admitted source paths."""
    candidate = tmp_path / "candidate"
    _write(candidate, "real/file.bin", b"ordinary source bytes")
    try:
        (candidate / "alias").symlink_to(
            candidate / "real", target_is_directory=True
        )
    except OSError:
        pytest.skip("directory symlinks unavailable")
    plan = relocatable_module.RelocatableAuthoringPlan((
        RelocatableInstruction(
            output_path="copy.bin",
            source_path="alias/file.bin",
            copy_candidate_file=True,
        ),
    ))
    output = tmp_path / "out"

    with pytest.raises(RelocationError, match="linked path component"):
        materialize_relocatable_plan(candidate, plan, output)
    assert not output.exists()
    assert not (tmp_path / ".out.relocatable-staging").exists()


def test_relocatable_authoring_read_error_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An authoring source read failure remains inside RelocationError."""
    source, oracle, _ = _fixture(tmp_path)
    exact = build_exact_plan(source, oracle)
    blocked = source / "code.bin"
    original_open = os.open

    def fail_open(
        file: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        if os.fspath(file) == os.fspath(blocked):
            message = "blocked relocatable authoring read"
            raise PermissionError(message)
        return original_open(file, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(os, "open", fail_open)
    with pytest.raises(RelocationError, match="relocatable source read failed"):
        _ = build_relocatable_plan(source, exact)


def test_relocatable_plan_is_deterministic(tmp_path: Path) -> None:
    """Author the same hash-only placement metadata repeatedly."""
    source, oracle, _ = _fixture(tmp_path)
    exact = build_exact_plan(source, oracle)

    first = build_relocatable_plan(source, exact)
    second = build_relocatable_plan(source, exact)

    _expect(first == second, "relocatable authoring changed across runs")


def test_exact_model_rejects_boolean_and_foreign_segment_metadata() -> None:
    """Exact source ranges and literals require exact immutable value types."""
    with pytest.raises(TreeModelError, match="exact integers"):
        _ = SourceSlice(offset=True, length=1)
    with pytest.raises(TreeModelError, match="exact integers"):
        _ = SourceSlice(offset=0, length=True)
    with pytest.raises(TreeModelError, match="exact bytes"):
        _ = OracleLiteral(cast("bytes", cast("object", bytearray(b"x"))))


def test_relocatable_locator_requires_exact_boundary_shape() -> None:
    """Incomplete or redundant end boundaries cannot admit source ranges."""
    digest = hashlib.sha256(b"x").digest()
    with pytest.raises(RelocationError, match="end boundary digest"):
        _ = RangeLocator(source_length=2, window_bytes=1, start_digest=digest)
    with pytest.raises(RelocationError, match="end boundary digest"):
        _ = RangeLocator(
            source_length=1,
            window_bytes=1,
            start_digest=digest,
            end_digest=digest,
        )


def test_relocatable_metadata_rejects_boolean_and_foreign_records() -> None:
    """Range locators and instructions cannot rely on Python coercions."""
    digest = b"x" * 32
    with pytest.raises(RelocationError, match="positive integer"):
        _ = RangeLocator(
            source_length=True, window_bytes=1, start_digest=digest
        )
    with pytest.raises(RelocationError, match="valid integer"):
        _ = RangeLocator(
            source_length=1, window_bytes=True, start_digest=digest
        )
    with pytest.raises(RelocationError, match="exact SHA-256 bytes"):
        _ = RangeLocator(1, 1, cast("bytes", object()))
    locator = RangeLocator(1, 1, digest)
    with pytest.raises(RelocationError, match="exact locator"):
        _ = RelocatableSourceRange(cast("RangeLocator", object()))
    with pytest.raises(RelocationError, match="exact boolean"):
        _ = RelocatableInstruction(
            "out", "src", cast("bool", cast("object", 1))
        )
    with pytest.raises(RelocationError, match="immutable tuple"):
        _ = RelocatableInstruction(
            "out",
            "src",
            copy_candidate_file=False,
            segments=cast(
                "tuple[RelocatableSourceRange | OracleLiteral, ...]",
                cast("object", [RelocatableSourceRange(locator)]),
            ),
        )
    with pytest.raises(RelocationError, match="foreign segment"):
        _ = RelocatableInstruction(
            "out",
            "src",
            copy_candidate_file=False,
            segments=(cast("RelocatableSourceRange", object()),),
        )


@pytest.mark.parametrize("unsafe_path", ["src/\x00.bin", "src/\ud800.bin"])
def test_relocatable_instruction_rejects_nonportable_paths(
    unsafe_path: str,
) -> None:
    """Both source and output paths must be usable as canonical UTF-8."""
    with pytest.raises(RelocationError, match="unsafe relocatable tree path"):
        _ = RelocatableInstruction(
            output_path=unsafe_path,
            source_path=None,
            copy_candidate_file=False,
            literal=b"target",
        )
    with pytest.raises(RelocationError, match="unsafe relocatable tree path"):
        _ = RelocatableInstruction(
            output_path="output.bin",
            source_path=unsafe_path,
            copy_candidate_file=True,
        )


def test_relocatable_plan_rejects_duplicate_output_destinations() -> None:
    """A staged file must have exactly one authorized output instruction."""
    first = RelocatableInstruction(
        output_path="out.bin",
        source_path=None,
        copy_candidate_file=False,
        literal=b"first",
    )
    second = RelocatableInstruction(
        output_path="out.bin",
        source_path=None,
        copy_candidate_file=False,
        literal=b"second",
    )
    with pytest.raises(RelocationError, match="unique output paths"):
        _ = relocatable_module.RelocatableAuthoringPlan((first, second))


def test_existing_relocatable_staging_is_preserved(tmp_path: Path) -> None:
    """Never delete a staging tree that may belong to another writer."""
    source, oracle, base = _fixture(tmp_path)
    plan = build_relocatable_plan(source, build_exact_plan(source, oracle))
    candidate = tmp_path / "candidate"
    _write(candidate, "code.bin", base)
    _write(candidate, "copy.bin", _blocks("copy"))
    output = tmp_path / "out"
    staging = tmp_path / ".out.relocatable-staging"
    _write(staging, "owner.txt", _FOREIGN_STAGING)

    with pytest.raises(RelocationError, match="staging root already exists"):
        materialize_relocatable_plan(candidate, plan, output)
    _expect(
        (staging / "owner.txt").read_bytes() == _FOREIGN_STAGING,
        "preexisting relocatable staging was modified",
    )
    _expect(not output.exists(), "staging conflict published output")


@pytest.mark.parametrize("bad_suffix", ["\x00", "\ud800"])
def test_relocatable_root_paths_reject_nonfilesystem_text(
    tmp_path: Path, bad_suffix: str
) -> None:
    """Reject unrepresentable roots before staging or source-file reads."""
    source, oracle, _ = _fixture(tmp_path)
    exact = build_exact_plan(source, oracle)
    plan = build_relocatable_plan(source, exact)
    invalid_root = tmp_path / f"invalid{bad_suffix}"
    output = tmp_path / "out"

    with pytest.raises(RelocationError, match="filesystem path"):
        _ = build_relocatable_plan(invalid_root, exact)
    with pytest.raises(RelocationError, match="filesystem path"):
        materialize_relocatable_plan(invalid_root, plan, output)
    with pytest.raises(RelocationError, match="filesystem path"):
        materialize_relocatable_plan(source, plan, invalid_root)
    assert not output.exists()
    assert not (tmp_path / ".out.relocatable-staging").exists()


@pytest.mark.skipif(
    os.name != _POSIX, reason="requires POSIX raw-byte pathnames"
)
def test_relocatable_root_accepts_surrogateescaped_filesystem_name(
    tmp_path: Path,
) -> None:
    """Admit real POSIX root bytes even when the display name is not UTF-8."""
    raw_root = os.fsencode(tmp_path) + b"/source-\xff"
    source = Path(os.fsdecode(raw_root))
    source.mkdir()
    oracle = tmp_path / "oracle"
    _write(source, "code.bin", b"source")
    _write(oracle, "code.bin", _ROOT_TARGET)
    plan = build_relocatable_plan(source, build_exact_plan(source, oracle))

    output = tmp_path / "out"
    materialize_relocatable_plan(source, plan, output)
    assert (output / "code.bin").read_bytes() == _ROOT_TARGET


def test_relocatable_public_boundaries_reject_foreign_inputs(
    tmp_path: Path,
) -> None:
    """Build/materialize validate roots and plans before filesystem work."""
    source, oracle, _ = _fixture(tmp_path)
    exact = build_exact_plan(source, oracle)
    with pytest.raises(RelocationError, match="pathlib Path"):
        _ = build_relocatable_plan(cast("Path", object()), exact)
    with pytest.raises(RelocationError, match="exact authoring-plan"):
        _ = build_relocatable_plan(source, cast("ExactAuthoringPlan", object()))
    plan = build_relocatable_plan(source, exact)
    output = tmp_path / "invalid-out"
    with pytest.raises(RelocationError, match="pathlib Path"):
        materialize_relocatable_plan(cast("Path", object()), plan, output)
    with pytest.raises(RelocationError, match="exact plan type"):
        materialize_relocatable_plan(
            source, cast("RelocatableAuthoringPlan", object()), output
        )
    _expect(not output.exists(), "invalid public input published output")
