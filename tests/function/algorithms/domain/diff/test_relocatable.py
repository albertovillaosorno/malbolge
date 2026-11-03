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

import builtins
import hashlib
import ntpath
import os
import shutil
from pathlib import Path
from typing import TYPE_CHECKING, cast, override

import pytest
from algorithms.diff import relocatable as relocatable_module
from algorithms.diff.exact import (
    ExactTreeError,
    build_exact_plan,
    read_exact_regular_file,
)
from algorithms.diff.model import OracleLiteral, SourceSlice, TreeModelError
from algorithms.diff.relocatable import (
    RangeLocator,
    RelocatableInstruction,
    RelocatableSourceRange,
    RelocationError,
    build_relocatable_plan,
    materialize_relocatable_plan,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from algorithms.diff.model import ExactAuthoringPlan
    from algorithms.diff.relocatable import RelocatableAuthoringPlan

_BLOCKS = 64
_INSERTION = b"candidate-insertion-preserved"
_TARGET = b"TARGET-ONLY-CORRECTION"
_CREATED = b"created-target"
_FOREIGN_STAGING = b"foreign-writer"
_FOREIGN_OUTPUT = b"foreign-output"
_SYMLINK_METHOD = "is_symlink"
_POSIX = "posix"
_ROOT_TARGET = b"target"
_SHORT_WRITE = "short"
_EXACT_STRING_TYPE = "exact string type"


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


class _HostileRelocatableError(OSError):
    """Foreign host exceptions may not execute their own display hooks."""

    @override
    def __str__(self) -> str:
        message = "hostile relocatable error formatter executed"
        raise AssertionError(message)

    @override
    def __repr__(self) -> str:
        message = "hostile relocatable error repr executed"
        raise AssertionError(message)


class _HostileRelocatableReadError(ExactTreeError):
    """Delegated exact reads must not format foreign errors."""

    @override
    def __str__(self) -> str:
        message = "hostile exact reader formatter executed"
        raise AssertionError(message)

    @override
    def __getattribute__(self, name: str) -> object:
        if name == "__notes__":
            message = "hostile exact reader notes executed"
            raise AssertionError(message)
        return cast("object", super().__getattribute__(name))


@pytest.mark.parametrize(
    ("operation", "expected"),
    [
        ("status", "staging root status failed"),
        ("creation", "staging root creation failed"),
        ("write", "relocatable output write failed"),
        ("publication", "output publication failed"),
        ("root_resolve", "root resolution failed"),
        ("read", "candidate read failed"),
        ("snapshot", "source snapshot failed"),
    ],
)
def test_relocatable_host_failures_do_not_invoke_foreign_formatters(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    operation: str,
    expected: str,
) -> None:
    """Host callback errors must retain typed failures and never publish."""
    source, oracle, base = _fixture(tmp_path)
    exact = build_exact_plan(source, oracle)
    plan = build_relocatable_plan(source, exact)
    candidate = tmp_path / "candidate"
    _write(candidate, "code.bin", base)
    _write(candidate, "copy.bin", _blocks("copy"))
    staging = tmp_path / ".out.relocatable-staging"
    output = tmp_path / "out"

    if operation == "status":
        native_lstat = Path.lstat

        def fail_status(path: Path) -> os.stat_result:
            if path == staging:
                raise _HostileRelocatableError("foreign status")
            return native_lstat(path)

        monkeypatch.setattr(
            relocatable_module, "_NATIVE_PATH_LSTAT", fail_status
        )
    elif operation == "creation":
        native_mkdir = Path.mkdir

        def fail_mkdir(
            path: Path,
            mode: int = 0o777,
            *,
            parents: bool = False,
            exist_ok: bool = False,
        ) -> None:
            if path == staging:
                raise _HostileRelocatableError("foreign mkdir")
            native_mkdir(path, mode=mode, parents=parents, exist_ok=exist_ok)

        monkeypatch.setattr(Path, "mkdir", fail_mkdir)
    elif operation == "write":
        native_write = Path.write_bytes

        def fail_write(path: Path, data: bytes) -> int:
            if path == staging / "created.bin":
                raise _HostileRelocatableError("foreign write")
            return native_write(path, data)

        monkeypatch.setattr(Path, "write_bytes", fail_write)
    elif operation == "publication":

        def fail_publication(staged: Path, destination: Path) -> None:
            _ = staged, destination
            raise _HostileRelocatableError("foreign publication")

        monkeypatch.setattr(
            relocatable_module, "publish_directory_no_replace", fail_publication
        )
    elif operation == "root_resolve":
        native_resolve = Path.resolve

        def fail_resolve(path: Path, *, strict: bool = False) -> Path:
            if path == candidate:
                raise _HostileRelocatableError("foreign resolution")
            return native_resolve(path, strict=strict)

        monkeypatch.setattr(relocatable_module, "_NATIVE_RESOLVE", fail_resolve)
    elif operation == "read":
        native_read = cast(
            "Callable[[Path, str], bytes]",
            vars(relocatable_module)["read_exact_regular_file"],
        )

        def fail_read(path: Path, context: str) -> bytes:
            if path == candidate / "code.bin":
                raise _HostileRelocatableReadError("foreign read")
            return native_read(path, context)

        monkeypatch.setattr(
            relocatable_module, "read_exact_regular_file", fail_read
        )
    elif operation == "snapshot":

        def fail_snapshot(root: Path, roots: tuple[str, ...]) -> object:
            _ = root, roots
            raise _HostileRelocatableReadError("foreign snapshot")

        monkeypatch.setattr(
            relocatable_module, "snapshot_tree_excluding", fail_snapshot
        )

    with pytest.raises(RelocationError, match=expected):
        if operation == "snapshot":
            _ = build_relocatable_plan(source, exact)
        else:
            materialize_relocatable_plan(candidate, plan, output)
    _expect(not output.exists(), "a foreign host error published output")
    _expect(not staging.exists(), "a foreign host error left owned staging")


@pytest.mark.parametrize(
    "method", ["is_symlink", "is_junction", "resolve"]
)
def test_relocatable_nested_path_errors_do_not_format_foreign_failures(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, method: str
) -> None:
    """Reject hostile nested path inspection and normalization callbacks."""
    candidate = tmp_path / "candidate"
    _write(candidate, "nested/file.bin", b"candidate bytes")
    output = tmp_path / "out"
    plan = relocatable_module.RelocatableAuthoringPlan((
        RelocatableInstruction(
            output_path="copy.bin",
            source_path="nested/file.bin",
            copy_candidate_file=True,
        ),
    ))
    guard = candidate / ("nested/file.bin" if method == "resolve" else "nested")
    original_resolve = Path.resolve
    original_junction = Path.is_junction

    def fail_resolve(path: Path, *, strict: bool = False) -> Path:
        if path == guard:
            raise _HostileRelocatableError("foreign nested resolution")
        return original_resolve(path, strict=strict)

    def fail_symlink(mode: int) -> bool:
        _ = mode
        raise _HostileRelocatableError("foreign symlink status")

    def fail_junction(path: Path) -> bool:
        if path == guard:
            raise _HostileRelocatableError("foreign junction status")
        return original_junction(path)

    replacements = {
        "resolve": ("_NATIVE_RESOLVE", fail_resolve),
        "is_symlink": ("_NATIVE_IS_SYMLINK", fail_symlink),
        "is_junction": ("_NATIVE_IS_JUNCTION", fail_junction),
    }
    hook, failure = replacements[method]
    monkeypatch.setattr(relocatable_module, hook, failure)
    expected = (
        "path resolution failed"
        if method == "resolve"
        else "ancestor inspection failed"
    )
    with pytest.raises(RelocationError, match=expected):
        materialize_relocatable_plan(candidate, plan, output)
    _expect(not output.exists(), "nested path failure published output")
    _expect(
        not (tmp_path / ".out.relocatable-staging").exists(),
        "nested path failure retained staging",
    )


def test_relocatable_cleanup_ignores_post_import_rmtree_hook(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A late shutil hook cannot suppress deletion of owned staging."""
    staging = tmp_path / "owned-staging"
    staging.mkdir()
    _ = (staging / "payload.bin").write_bytes(b"temporary")
    calls = 0

    def forged_rmtree(path: Path) -> None:
        nonlocal calls
        _ = path
        calls += 1

    cleanup = cast(
        "Callable[[Path], str | None]",
        vars(relocatable_module)["_cleanup_relocatable_staging"],
    )
    with monkeypatch.context() as patched:
        patched.setattr(shutil, "rmtree", forged_rmtree)
        detail = cleanup(staging)
    assert detail is None
    assert calls == 0, "late cleanup hook executed"
    assert not staging.exists(), "owned staging remained after cleanup"


@pytest.mark.parametrize("hostile_primary", [False, True])
def test_relocatable_cleanup_preserves_failure_without_foreign_formatter(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    hostile_primary: bool,
) -> None:
    """Secondary failures cannot execute primary or cleanup formatters."""
    source, oracle, base = _fixture(tmp_path)
    plan = build_relocatable_plan(source, build_exact_plan(source, oracle))
    candidate = tmp_path / "candidate"
    _write(candidate, "code.bin", base)
    _write(candidate, "copy.bin", _blocks("copy"))
    staging = tmp_path / ".out.relocatable-staging"
    output = tmp_path / "out"
    native_write = Path.write_bytes

    def fail_write(path: Path, data: bytes) -> int:
        if path == staging / "created.bin":
            if hostile_primary:
                raise _HostileRelocatableError("foreign primary")
            raise PermissionError("primary write failed")
        return native_write(path, data)

    def fail_cleanup(path: Path) -> None:
        _ = path
        if hostile_primary:
            raise PermissionError("cleanup failed")
        raise _HostileRelocatableError("foreign cleanup")

    monkeypatch.setattr(Path, "write_bytes", fail_write)
    monkeypatch.setattr(relocatable_module, "_NATIVE_RMTREE", fail_cleanup)
    with pytest.raises(
        RelocationError, match="staging cleanup failed"
    ) as failure:
        materialize_relocatable_plan(candidate, plan, output)
    _expect(
        type(failure.value.__cause__) is RelocationError,
        "staging cleanup failure did not preserve the original typed error",
    )
    _expect(not output.exists(), "failed cleanup published relocation output")


class _ForeignRelocatableRoot(type(Path())):
    """Overridable root paths cannot authorize relocatable placement."""

    @override
    def __str__(self) -> str:
        message = "foreign relocatable root path conversion executed"
        raise AssertionError(message)


@pytest.mark.parametrize("role", ["source", "candidate", "output"])
def test_relocatable_roots_reject_foreign_path_subclasses_before_methods(
    tmp_path: Path, role: str
) -> None:
    """Reject authoring, candidate, and output hooks before filesystem work."""
    source, oracle, _ = _fixture(tmp_path)
    exact = build_exact_plan(source, oracle)
    plan = build_relocatable_plan(source, exact)
    foreign = _ForeignRelocatableRoot(tmp_path / "untrusted")
    actions = {
        "source": lambda: build_relocatable_plan(foreign, exact),
        "candidate": lambda: materialize_relocatable_plan(
            foreign, plan, tmp_path / "out"
        ),
        "output": lambda: materialize_relocatable_plan(source, plan, foreign),
    }
    with pytest.raises(RelocationError, match="must use exact pathlib Path"):
        _ = actions[role]()
    assert not (tmp_path / "untrusted").exists()


def test_relocatable_rejects_foreign_resolved_output_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A forged resolved Path cannot approve writing inside the candidate."""
    candidate = tmp_path / "candidate"
    _write(candidate, "code.bin", b"original candidate")
    plan = relocatable_module.RelocatableAuthoringPlan((
        RelocatableInstruction(
            output_path="copied.bin",
            source_path="code.bin",
            copy_candidate_file=True,
        ),
    ))
    output = candidate / "out"
    native_resolve = cast(
        "Callable[[Path], Path]",
        vars(relocatable_module)["_NATIVE_RESOLVE"],
    )

    class ForgedResolvedPath(type(Path())):
        @override
        def is_relative_to(self, other: object) -> bool:
            _ = other
            return False

    def forged_resolve(path: Path) -> Path:
        resolved = native_resolve(path)
        if path == output:
            return ForgedResolvedPath(resolved)
        return resolved

    monkeypatch.setattr(relocatable_module, "_NATIVE_RESOLVE", forged_resolve)
    with pytest.raises(RelocationError, match="native resolved Path"):
        materialize_relocatable_plan(candidate, plan, output)
    assert not output.exists()
    assert not (candidate / ".out.relocatable-staging").exists()


@pytest.mark.parametrize("role", ["candidate", "staging"])
def test_relocatable_rejects_foreign_nested_resolution_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, role: str
) -> None:
    """Path containment must not use foreign nested resolution methods."""
    candidate = tmp_path / "candidate"
    _write(candidate, "nested/file.bin", b"native source")
    plan = relocatable_module.RelocatableAuthoringPlan((
        RelocatableInstruction(
            output_path="copied.bin",
            source_path="nested/file.bin",
            copy_candidate_file=True,
        ),
    ))
    output = tmp_path / "out"
    targeted = (
        candidate / "nested/file.bin"
        if role == "candidate"
        else tmp_path / ".out.relocatable-staging"
    )
    native_resolve = Path.resolve

    class ForgedResolvedPath(type(Path())):
        pass

    def forged_resolve(path: Path, *, strict: bool = False) -> Path:
        resolved = native_resolve(path, strict=strict)
        if path == targeted:
            return ForgedResolvedPath(resolved)
        return resolved

    monkeypatch.setattr(relocatable_module, "_NATIVE_RESOLVE", forged_resolve)
    with pytest.raises(RelocationError, match="native resolved Path"):
        materialize_relocatable_plan(candidate, plan, output)
    assert not output.exists()
    assert not (tmp_path / ".out.relocatable-staging").exists()


@pytest.mark.parametrize("linked_output", [False, True])
def test_relocatable_rejects_output_inside_candidate_source(
    tmp_path: Path,
    *,
    linked_output: bool,
) -> None:
    """Reject source-contained publication before creating staging files."""
    source, oracle, base = _fixture(tmp_path)
    plan = build_relocatable_plan(source, build_exact_plan(source, oracle))
    candidate = tmp_path / "candidate"
    _write(candidate, "code.bin", base)
    _write(candidate, "copy.bin", _blocks("copy"))
    output_parent = candidate
    if linked_output:
        output_parent = tmp_path / "candidate-alias"
        try:
            _ = output_parent.symlink_to(candidate, target_is_directory=True)
        except OSError:
            pytest.skip("directory symlinks unavailable")
    output = output_parent / "generated" / "out"

    with pytest.raises(RelocationError, match="inside the candidate source"):
        materialize_relocatable_plan(candidate, plan, output)

    _expect(not output.exists(), "source-contained output was published")
    entries = sorted(
        path.relative_to(candidate).as_posix() for path in candidate.rglob("*")
    )
    _expect(
        entries == ["code.bin", "copy.bin"],
        "relocatable materialization mutated the candidate source tree",
    )


@pytest.mark.parametrize("changed", ["code.bin", "copy.bin"])
def test_relocatable_authoring_rejects_changed_exact_source(
    tmp_path: Path,
    changed: str,
) -> None:
    """Relocation must not author locators against stale exact snapshots."""
    source, oracle, _ = _fixture(tmp_path)
    exact = build_exact_plan(source, oracle)
    previous = (source / changed).read_bytes()
    _write(source, changed, previous + b"late source change")

    with pytest.raises(RelocationError, match="source snapshot"):
        _ = build_relocatable_plan(source, exact)


def test_relocatable_authoring_detects_drift_during_build(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A post-locator snapshot catches source edits during authoring."""
    source, oracle, _ = _fixture(tmp_path)
    exact = build_exact_plan(source, oracle)
    original = read_exact_regular_file
    modified = False

    def change_after_read(path: Path, context: str) -> bytes:
        nonlocal modified
        result = original(path, context)
        if not modified:
            modified = True
            _write(source, "copy.bin", _blocks("copy") + b"late edit")
        return result

    monkeypatch.setattr(
        relocatable_module, "read_exact_regular_file", change_after_read
    )
    with pytest.raises(RelocationError, match="source snapshot"):
        _ = build_relocatable_plan(source, exact)
    _expect(modified, "authoring did not exercise post-read validation")


def test_relocatable_authoring_preserves_exact_passthrough_scope(
    tmp_path: Path,
) -> None:
    """Source snapshot checks exclude exact-authoring passthrough files."""
    source, oracle, _ = _fixture(tmp_path)
    passthrough = "copy.bin"
    exact = build_exact_plan(source, oracle, passthrough_roots=(passthrough,))
    plan = build_relocatable_plan(source, exact)
    _expect(
        passthrough not in (item.output_path for item in plan.instructions),
        "exact passthrough root unexpectedly became a static output",
    )


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

    monkeypatch.setattr(relocatable_module, "_NATIVE_RESOLVE", fail_resolve)
    output = tmp_path / "out"
    with pytest.raises(RelocationError, match="path resolution failed"):
        materialize_relocatable_plan(candidate, plan, output)
    _expect(not output.exists(), "resolution failure published output")


def _forge_relocatable_containment(
    monkeypatch: pytest.MonkeyPatch, output: Path
) -> None:
    native = Path.is_relative_to

    def forged(path: Path, root: Path) -> bool:
        if path == output:
            return False
        return native(path, root)

    monkeypatch.setattr(Path, "is_relative_to", forged)


def _forge_relocatable_resolution(
    monkeypatch: pytest.MonkeyPatch, output: Path, outside: Path
) -> None:
    native = Path.resolve

    def forged(path: Path, *, strict: bool = False) -> Path:
        if path == output:
            return outside
        return native(path, strict=strict)

    monkeypatch.setattr(Path, "resolve", forged)


@pytest.mark.parametrize("forge_resolve", [False, True])
def test_relocatable_nested_output_rejects_host_path_spoof(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    forge_resolve: bool,
) -> None:
    """Host hooks cannot create staging artifacts in candidate input trees."""
    source, oracle, base = _fixture(tmp_path)
    plan = build_relocatable_plan(source, build_exact_plan(source, oracle))
    candidate = tmp_path / "candidate"
    _write(candidate, "code.bin", base)
    _write(candidate, "copy.bin", _blocks("copy"))
    output = candidate / "nested" / "out"
    if forge_resolve:
        _forge_relocatable_resolution(
            monkeypatch, output, tmp_path / "outside"
        )
    else:
        _forge_relocatable_containment(monkeypatch, output)

    with pytest.raises(RelocationError, match="inside the candidate source"):
        materialize_relocatable_plan(candidate, plan, output)
    assert not output.exists()
    entries = sorted(
        path.relative_to(candidate).as_posix()
        for path in candidate.rglob("*")
    )
    assert entries == ["code.bin", "copy.bin"]


@pytest.mark.parametrize("error_type", [ValueError, RuntimeError])
@pytest.mark.parametrize("nested_source", [False, True])
def test_relocatable_materialization_normalizes_resolution_failures(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    error_type: type[Exception],
    *,
    nested_source: bool,
) -> None:
    """Filesystem resolution errors stay typed and cannot publish output."""
    source, oracle, base = _fixture(tmp_path)
    plan = build_relocatable_plan(source, build_exact_plan(source, oracle))
    candidate = tmp_path / "candidate"
    _write(candidate, "code.bin", base)
    _write(candidate, "copy.bin", _blocks("copy"))
    failing = candidate / "code.bin" if nested_source else candidate
    original_resolve = Path.resolve

    def fail_resolve(path: Path, *, strict: bool = False) -> Path:
        if path == failing:
            raise error_type()
        return original_resolve(path, strict=strict)

    monkeypatch.setattr(relocatable_module, "_NATIVE_RESOLVE", fail_resolve)
    output = tmp_path / "out"
    with pytest.raises(RelocationError, match="resolution failed"):
        materialize_relocatable_plan(candidate, plan, output)
    _expect(not output.exists(), "failed resolution published output")
    _expect(
        not (tmp_path / ".out.relocatable-staging").exists(),
        "failed resolution preserved an owned staging tree",
    )


@pytest.mark.parametrize(
    "failure_type", [FileExistsError, ValueError, RuntimeError]
)
def test_relocatable_publication_collision_preserves_foreign_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure_type: type[Exception],
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
        raise failure_type(destination)

    monkeypatch.setattr(
        relocatable_module, "publish_directory_no_replace", collide
    )
    with pytest.raises(RelocationError, match="output publication failed"):
        materialize_relocatable_plan(candidate, plan, output)

    assert (output / "foreign.txt").read_bytes() == _FOREIGN_OUTPUT
    assert not (tmp_path / ".out.relocatable-staging").exists()


@pytest.mark.parametrize(
    "failure_type", [PermissionError, ValueError, RuntimeError]
)
def test_relocatable_cleanup_failure_preserves_primary_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure_type: type[Exception],
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
        raise failure_type(message)

    monkeypatch.setattr(Path, "write_bytes", fail_write)
    monkeypatch.setattr(relocatable_module, "_NATIVE_RMTREE", fail_cleanup)
    with pytest.raises(
        RelocationError,
        match=r"relocatable output write failed.*staging cleanup failed",
    ):
        materialize_relocatable_plan(candidate, plan, output)


@pytest.mark.parametrize(
    "failure_type", [PermissionError, ValueError, RuntimeError]
)
def test_relocatable_staging_status_error_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure_type: type[Exception],
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
            raise failure_type(message)
        return original_lstat(path)

    monkeypatch.setattr(relocatable_module, "_NATIVE_PATH_LSTAT", fail_lstat)
    with pytest.raises(RelocationError, match="staging root status failed"):
        materialize_relocatable_plan(candidate, plan, output)
    _expect(not output.exists(), "status failure published relocatable output")


@pytest.mark.parametrize(
    "failure_type", [PermissionError, ValueError, RuntimeError]
)
def test_relocatable_staging_creation_error_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure_type: type[Exception],
) -> None:
    """Staging mkdir failures do not escape the relocation boundary."""
    source, oracle, base = _fixture(tmp_path)
    plan = build_relocatable_plan(source, build_exact_plan(source, oracle))
    candidate = tmp_path / "candidate"
    _write(candidate, "code.bin", base)
    _write(candidate, "copy.bin", _blocks("copy"))
    output = tmp_path / "out"
    staging = tmp_path / ".out.relocatable-staging"
    original_mkdir = Path.mkdir

    def fail_mkdir(
        path: Path,
        mode: int = 0o777,
        *,
        parents: bool = False,
        exist_ok: bool = False,
    ) -> None:
        if path == staging:
            message = "blocked relocatable staging creation"
            raise failure_type(message)
        original_mkdir(path, mode=mode, parents=parents, exist_ok=exist_ok)

    monkeypatch.setattr(Path, "mkdir", fail_mkdir)
    with pytest.raises(RelocationError, match="staging root creation failed"):
        materialize_relocatable_plan(candidate, plan, output)
    _expect(not output.exists(), "staging creation failure published output")
    _expect(not staging.exists(), "staging creation failure left staging")


@pytest.mark.parametrize(
    "failure_type", [PermissionError, ValueError, RuntimeError]
)
def test_relocatable_output_write_error_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure_type: type[Exception],
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
            raise failure_type(message)
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


@pytest.mark.parametrize(
    "reported",
    [_SHORT_WRITE, None, True, -1, 10**9],
)
def test_relocatable_short_or_invalid_staging_write_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    reported: object,
) -> None:
    """Do not publish incomplete bytes or trust foreign write counts."""
    source, oracle, base = _fixture(tmp_path)
    plan = build_relocatable_plan(source, build_exact_plan(source, oracle))
    candidate = tmp_path / "candidate"
    _write(candidate, "code.bin", base)
    _write(candidate, "copy.bin", _blocks("copy"))
    output = tmp_path / "out"
    blocked = tmp_path / ".out.relocatable-staging" / "created.bin"
    original_write = Path.write_bytes

    def misreported_write(path: Path, data: bytes) -> int:
        if path == blocked and reported == _SHORT_WRITE:
            return original_write(path, data[:1])
        written = original_write(path, data)
        if path == blocked:
            return cast("int", reported)
        return written

    monkeypatch.setattr(Path, "write_bytes", misreported_write)
    with pytest.raises(RelocationError, match="short or invalid byte count"):
        materialize_relocatable_plan(candidate, plan, output)
    assert not output.exists()
    assert not (tmp_path / ".out.relocatable-staging").exists()


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
    with pytest.raises(
        RelocationError, match="relocatable source snapshot failed"
    ):
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
    _ = (source / "tree").rename(source / "actual")
    try:
        _ = (source / "tree").symlink_to(
            source / "actual", target_is_directory=True
        )
    except OSError:
        pytest.skip("directory symlinks unavailable")

    with pytest.raises(
        RelocationError, match="relocatable source snapshot failed"
    ):
        _ = build_relocatable_plan(source, exact)


def _relocatable_safe_path(root: Path, relative: str) -> Path:
    safe_path = cast(
        "Callable[[Path, str], Path]", vars(relocatable_module)["_safe_path"]
    )
    return safe_path(root, relative)


def test_relocatable_path_rejects_post_import_resolver_spoof(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A late resolver cannot hide a source file alias outside its tree."""
    root = tmp_path / "root"
    _write(root, "ordinary.bin", b"internal")
    external = tmp_path / "external.bin"
    _ = external.write_bytes(b"outside")
    alias = root / "alias.bin"
    try:
        alias.symlink_to(external)
    except OSError:
        pytest.skip("file symlinks unavailable")
    original = Path.resolve
    calls = 0

    def forged(path: Path, *, strict: bool = False) -> Path:
        nonlocal calls
        if path == alias:
            calls += 1
            return root / "ordinary.bin"
        return original(path, strict=strict)

    monkeypatch.setattr(Path, "resolve", forged)
    with pytest.raises(RelocationError, match="escapes tree root"):
        _ = _relocatable_safe_path(root, "alias.bin")
    assert calls == 0


def test_relocatable_path_rejects_post_import_containment_spoof(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A late relative_to hook cannot admit an external source file."""
    root = tmp_path / "root"
    root.mkdir()
    external = tmp_path / "external.bin"
    _ = external.write_bytes(b"outside")
    alias = root / "alias.bin"
    try:
        alias.symlink_to(external)
    except OSError:
        pytest.skip("file symlinks unavailable")
    original = Path.relative_to
    calls = 0

    def forged(path: Path, *other: Path) -> Path:
        nonlocal calls
        if path == external and other == (root,):
            calls += 1
            return Path("alias.bin")
        return original(path, *other)

    monkeypatch.setattr(Path, "relative_to", forged)
    with pytest.raises(RelocationError, match="escapes tree root"):
        _ = _relocatable_safe_path(root, "alias.bin")
    assert calls == 0


def _relocatable_linked_ancestor(tmp_path: Path) -> tuple[Path, Path]:
    root = tmp_path / "root"
    _write(root, "real/file.bin", b"inside")
    alias = root / "alias"
    try:
        alias.symlink_to(root / "real", target_is_directory=True)
    except OSError:
        pytest.skip("directory symlinks unavailable")
    return root, alias


def test_relocatable_path_rejects_post_import_link_inspection_spoof(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Late path inspectors cannot hide in-tree linked ancestors."""
    root, alias = _relocatable_linked_ancestor(tmp_path)
    calls = 0

    def forged(path: Path) -> bool:
        nonlocal calls
        if path == alias:
            calls += 1
            return False
        return False

    monkeypatch.setattr(Path, "is_symlink", forged)
    monkeypatch.setattr(Path, "is_junction", forged)
    with pytest.raises(RelocationError, match="linked path component"):
        _ = _relocatable_safe_path(root, "alias/file.bin")
    assert calls == 0


def test_relocatable_path_rejects_post_import_missing_ancestor_spoof(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A late lstat hook cannot hide a linked path component."""
    root, alias = _relocatable_linked_ancestor(tmp_path)
    original = Path.lstat
    calls = 0

    def forged(path: Path) -> os.stat_result:
        nonlocal calls
        if path == alias:
            calls += 1
            raise FileNotFoundError
        return original(path)

    monkeypatch.setattr(Path, "lstat", forged)
    with pytest.raises(RelocationError, match="linked path component"):
        _ = _relocatable_safe_path(root, "alias/file.bin")
    assert calls == 0


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


@pytest.mark.parametrize("method", ["is_symlink", "is_junction"])
@pytest.mark.parametrize("failure", [OSError, ValueError, RuntimeError])
def test_relocatable_ancestor_inspection_errors_are_typed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    method: str,
    failure: type[Exception],
) -> None:
    """Broken host redirect checks must not escape the relocation boundary."""
    candidate = tmp_path / "candidate"
    _write(candidate, "nested/file.bin", b"admitted candidate")
    output = tmp_path / "out"
    plan = relocatable_module.RelocatableAuthoringPlan((
        RelocatableInstruction(
            output_path="copy.bin",
            source_path="nested/file.bin",
            copy_candidate_file=True,
        ),
    ))
    guarded = candidate / "nested"
    hook = (
        "_NATIVE_IS_SYMLINK"
        if method == _SYMLINK_METHOD
        else "_NATIVE_IS_JUNCTION"
    )
    original = cast(
        "Callable[[Path | int], bool]", vars(relocatable_module)[hook]
    )

    def broken_inspection(value: Path | int) -> bool:
        if method == _SYMLINK_METHOD or value == guarded:
            message = "host inspection failed"
            raise failure(message)
        return original(value)

    monkeypatch.setattr(relocatable_module, hook, broken_inspection)
    with pytest.raises(RelocationError, match="ancestor inspection failed"):
        materialize_relocatable_plan(candidate, plan, output)
    _expect(not output.exists(), "failed admission published output")
    _expect(
        not (tmp_path / ".out.relocatable-staging").exists(),
        "failed admission left staging behind",
    )


@pytest.mark.parametrize("method", ["is_symlink", "is_junction"])
def test_relocatable_rejects_nonboolean_ancestor_status(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, method: str
) -> None:
    """False-like foreign host verdicts cannot attest an unlinked directory."""
    candidate = tmp_path / "candidate"
    _write(candidate, "real/file.bin", b"linked candidate bytes")
    nested = candidate / "alias"
    if method == _SYMLINK_METHOD:
        try:
            nested.symlink_to(candidate / "real", target_is_directory=True)
        except OSError:
            pytest.skip("filesystem symlinks unavailable")
    else:
        _write(candidate, "alias/file.bin", b"ordinary candidate bytes")
    plan = relocatable_module.RelocatableAuthoringPlan((
        RelocatableInstruction(
            output_path="copied.bin",
            source_path="alias/file.bin",
            copy_candidate_file=True,
        ),
    ))
    hook = (
        "_NATIVE_IS_SYMLINK"
        if method == _SYMLINK_METHOD
        else "_NATIVE_IS_JUNCTION"
    )
    original = cast(
        "Callable[[Path | int], bool]", vars(relocatable_module)[hook]
    )

    def forged_status(value: Path | int) -> bool:
        if method == _SYMLINK_METHOD or value == nested:
            return cast("bool", cast("object", 0))
        return original(value)

    monkeypatch.setattr(relocatable_module, hook, forged_status)
    output = tmp_path / "out"
    with pytest.raises(RelocationError, match="ancestor inspection failed"):
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
    with pytest.raises(
        RelocationError, match="relocatable source snapshot failed"
    ):
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


def test_relocatable_rejects_forged_process_global_sha256(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Foreign hash hooks cannot relocate source ranges into unrelated bytes."""
    original = b"REFERENCE!"
    unrelated = b"UNRELATED!"
    assert len(original) == len(unrelated)
    digest = hashlib.sha256(original).digest()
    locator = RangeLocator(len(original), len(original), digest)
    plan = relocatable_module.RelocatableAuthoringPlan((
        RelocatableInstruction(
            output_path="result.bin",
            source_path="input.bin",
            copy_candidate_file=False,
            segments=(RelocatableSourceRange(locator),),
        ),
    ))
    candidate = tmp_path / "candidate"
    _write(candidate, "input.bin", unrelated)
    output = tmp_path / "out"

    class ForgedSha256:
        digest_size: int = 32

        def digest(self) -> bytes:
            return digest[: self.digest_size]

    def forged_sha256(data: bytes = b"") -> ForgedSha256:
        _ = data
        return ForgedSha256()

    with monkeypatch.context() as patched:
        patched.setattr(hashlib, "sha256", forged_sha256)
        with pytest.raises(RelocationError, match="boundary is missing"):
            materialize_relocatable_plan(candidate, plan, output)
    assert not output.exists()
    assert not (tmp_path / ".out.relocatable-staging").exists()


def test_relocatable_locator_digest_size_is_not_mutable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A replaced hash factory cannot weaken exact 32-byte locator admission."""

    class ForgedSha256:
        digest_size: int = 1

    def forged_sha256() -> ForgedSha256:
        return ForgedSha256()

    with monkeypatch.context() as patched:
        patched.setattr(hashlib, "sha256", forged_sha256)
        with pytest.raises(RelocationError, match="exact SHA-256 bytes"):
            _ = RangeLocator(1, 1, b"x")


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


def test_relocatable_locator_rejects_late_type_spoof(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Late type hooks cannot admit mutable digests or boolean lengths."""
    foreign = bytearray(b"x" * 32)
    native_type = type
    digest_rejected = False
    count_rejected = False

    def forged_type(value: object) -> type:
        if value is foreign:
            return bytes
        if value is True:
            return int
        return native_type(value)

    with monkeypatch.context() as patched:
        patched.setattr(builtins, "type", forged_type)
        try:
            _ = RangeLocator(
                1, 1, cast("bytes", cast("object", foreign))
            )
        except RelocationError:
            digest_rejected = True
        try:
            _ = RangeLocator(True, 1, b"x" * 32)
        except RelocationError:
            count_rejected = True
    assert digest_rejected, "late type admitted a mutable locator digest"
    assert count_rejected, "late type admitted a boolean locator length"


def test_relocatable_locator_rejects_late_len_spoof(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Short digests cannot acquire a forged SHA-256 byte count."""
    digest = b"x"
    native_len = len
    rejected = False

    def forged_len(value: object) -> int:
        if value is digest:
            return 32
        return native_len(cast("bytes", value))

    with monkeypatch.context() as patched:
        patched.setattr(builtins, "len", forged_len)
        try:
            _ = RangeLocator(1, 1, digest)
        except RelocationError:
            rejected = True
    assert rejected, "late len admitted a truncated locator digest"


def test_relocatable_root_rejects_late_type_spoof(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Public path admission must reject foreign objects before coercion."""
    foreign = object()
    native_type = type
    native_path_type = type(Path())
    rejected = False

    def forged_type(value: object) -> type:
        return native_path_type if value is foreign else native_type(value)

    with monkeypatch.context() as patched:
        patched.setattr(builtins, "type", forged_type)
        try:
            relocatable_module._validate_path(foreign, "relocatable root")
        except RelocationError:
            rejected = True
    assert rejected, "late type admitted a foreign relocatable root"


def test_relocatable_instruction_rejects_late_bool_type_spoof(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A replacement bool class cannot admit an integer copy flag."""
    rejected = False
    with monkeypatch.context() as patched:
        patched.setattr(builtins, "bool", int)
        try:
            _ = RelocatableInstruction(
                "out.bin", "source.bin", cast("bool", cast("object", 1))
            )
        except RelocationError:
            rejected = True
    assert rejected, "late bool admitted an integer relocation copy flag"


def test_relocatable_plan_rejects_late_tuple_type_spoof(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A changed tuple class cannot admit mutable plan instructions."""
    instruction = RelocatableInstruction(
        "out.bin", None, copy_candidate_file=False, literal=b"target"
    )
    foreign = cast(
        "tuple[RelocatableInstruction, ...]", cast("object", [instruction])
    )
    rejected = False
    with monkeypatch.context() as patched:
        patched.setattr(builtins, "tuple", list)
        try:
            _ = relocatable_module.RelocatableAuthoringPlan(foreign)
        except RelocationError:
            rejected = True
    assert rejected, "late tuple admitted mutable relocation instructions"


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


@pytest.mark.parametrize(
    "unsafe_path",
    ["src/\x00.bin", "src/\ud800.bin", "CON", "aux.txt", "src/NUL.bin", "LPT1"],
)
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


def test_relocatable_reserved_paths_reject_host_predicate_swap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A runtime callback cannot reclassify Windows device labels as safe."""

    def forged_isreserved(path: str) -> bool:
        _ = path
        return False

    monkeypatch.setattr(ntpath, "isreserved", forged_isreserved)
    with pytest.raises(RelocationError, match="unsafe relocatable tree path"):
        _ = RelocatableInstruction(
            output_path="src/CON.bin",
            source_path=None,
            copy_candidate_file=False,
            literal=b"target",
        )


@pytest.mark.parametrize("drive_path", ["C:/target", "D:relative"])
def test_relocatable_instruction_rejects_windows_drive_paths(
    drive_path: str,
) -> None:
    """Drive-absolute and drive-relative labels are not portable tree paths."""
    with pytest.raises(RelocationError, match="unsafe relocatable tree path"):
        _ = RelocatableInstruction(
            output_path=drive_path,
            source_path=None,
            copy_candidate_file=False,
            literal=b"target",
        )
    with pytest.raises(RelocationError, match="unsafe relocatable tree path"):
        _ = RelocatableInstruction(
            output_path="out.bin",
            source_path=drive_path,
            copy_candidate_file=True,
        )


def test_relocatable_instruction_rejects_late_sum_form_spoof(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Contradictory copy and segment forms must never pass a forged count."""

    def construct_after_hook_swap() -> RelocatableInstruction:
        with monkeypatch.context() as patch:
            patch.setattr(builtins, "sum", lambda values: 1)
            return RelocatableInstruction(
                output_path="out.bin",
                source_path="src.bin",
                copy_candidate_file=True,
                segments=(OracleLiteral(b"extra"),),
            )

    with pytest.raises(RelocationError, match="exactly one payload form"):
        _ = construct_after_hook_swap()


def test_relocatable_instruction_rejects_late_any_segment_spoof(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A changed process-global any cannot approve foreign output segments."""

    def construct_after_hook_swap() -> RelocatableInstruction:
        with monkeypatch.context() as patch:
            patch.setattr(builtins, "any", lambda values: False)
            return RelocatableInstruction(
                output_path="out.bin",
                source_path="src.bin",
                copy_candidate_file=False,
                segments=(cast("OracleLiteral", object()),),
            )

    with pytest.raises(RelocationError, match="foreign segment"):
        _ = construct_after_hook_swap()


def test_relocatable_plan_rejects_late_set_uniqueness_spoof(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Duplicate output destinations cannot survive a replaced set helper."""
    instruction = RelocatableInstruction(
        output_path="out.bin",
        source_path=None,
        copy_candidate_file=False,
        literal=b"target",
    )

    def construct_after_hook_swap() -> RelocatableAuthoringPlan:
        with monkeypatch.context() as patch:
            patch.setattr(builtins, "set", lambda values: list(values))
            return relocatable_module.RelocatableAuthoringPlan(
                (instruction, instruction)
            )

    with pytest.raises(RelocationError, match="unique output paths"):
        _ = construct_after_hook_swap()


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


def test_relocatable_plan_rejects_file_directory_overlap() -> None:
    """File outputs cannot also be ancestors of another output file."""
    first = RelocatableInstruction(
        output_path="out/item",
        source_path=None,
        copy_candidate_file=False,
        literal=b"parent",
    )
    second = RelocatableInstruction(
        output_path="out/item/child",
        source_path=None,
        copy_candidate_file=False,
        literal=b"child",
    )
    with pytest.raises(RelocationError, match="ancestor"):
        _ = relocatable_module.RelocatableAuthoringPlan((first, second))
    with pytest.raises(RelocationError, match="ancestor"):
        _ = relocatable_module.RelocatableAuthoringPlan((second, first))


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


def test_relocation_locator_rejects_late_integer_alias_for_boolean_widths(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A changed integer class cannot authenticate Boolean source lengths."""
    rejected = False
    with monkeypatch.context() as patch:
        patch.setattr(builtins, "int", bool)
        try:
            _ = RangeLocator(
                source_length=True, window_bytes=True, start_digest=b"x" * 32
            )
        except RelocationError:
            rejected = True
    assert rejected, "Boolean locator dimensions passed late int alias"


def test_relocation_locator_rejects_late_bytes_alias_for_mutable_digest(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A changed bytes class cannot certify mutable range fingerprints."""
    rejected = False
    with monkeypatch.context() as patch:
        patch.setattr(builtins, "bytes", bytearray)
        try:
            _ = RangeLocator(
                1, 1, cast("bytes", cast("object", bytearray(b"x" * 32)))
            )
        except RelocationError:
            rejected = True
    assert rejected, "mutable locator digest passed late bytes alias"


def test_relocation_instruction_rejects_late_bytes_alias_for_mutable_literal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A changed bytes class cannot certify target-only mutable literals."""
    rejected = False
    with monkeypatch.context() as patch:
        patch.setattr(builtins, "bytes", bytearray)
        try:
            _ = RelocatableInstruction(
                output_path="out.bin",
                source_path=None,
                copy_candidate_file=False,
                literal=cast("bytes", cast("object", bytearray(b"oracle"))),
            )
        except RelocationError:
            rejected = True
    assert rejected, "mutable authoring literal passed late bytes alias"


def test_relocation_locator_and_literal_accept_valid_native_after_aliases(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Valid pinned metadata remains accepted under late builtin changes."""
    with monkeypatch.context() as patch:
        patch.setattr(builtins, "int", bool)
        locator = RangeLocator(1, 1, b"x" * 32)
    assert locator.source_length == 1
    with monkeypatch.context() as patch:
        patch.setattr(builtins, "bytes", bytearray)
        instruction = RelocatableInstruction(
            output_path="out.bin",
            source_path=None,
            copy_candidate_file=False,
            literal=_TARGET,
        )
    assert instruction.literal == _TARGET


def test_relocation_writer_rejects_late_integer_alias_for_boolean_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A Boolean write receipt cannot certify even a one-byte target file."""
    write_bytes = cast(
        "Callable[[Path, bytes, str], None]",
        relocatable_module.__dict__["_write_relocatable_bytes"],
    )
    output = tmp_path / "absent.txt"

    def fake_write(_: Path, _data: bytes) -> bool:
        del _data
        return True

    rejected = False
    with monkeypatch.context() as patch:
        patch.setattr(builtins, "int", bool)
        patch.setattr(Path, "write_bytes", fake_write)
        try:
            write_bytes(output, b"x", "relocatable target")
        except RelocationError:
            rejected = True
    assert rejected, "Boolean write receipt certified absent target bytes"
    assert not output.exists()


def test_relocation_writer_accepts_native_receipt_after_integer_alias(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A native one-byte writer remains valid despite a late int alias."""
    write_bytes = cast(
        "Callable[[Path, bytes, str], None]",
        relocatable_module.__dict__["_write_relocatable_bytes"],
    )
    output = tmp_path / "native.txt"
    with monkeypatch.context() as patch:
        patch.setattr(builtins, "int", bool)
        write_bytes(output, _ROOT_TARGET[:1], "relocatable target")
    assert output.read_bytes() == _ROOT_TARGET[:1]


def test_relocation_path_rejects_late_string_alias_with_typed_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Foreign bytes cannot be accepted as exact relative source path text."""
    require_path = cast(
        "Callable[[object], str]",
        relocatable_module.__dict__["_validate_relative_path"],
    )
    rejected = False
    with monkeypatch.context() as patch:
        patch.setattr(builtins, "str", bytes)
        try:
            _ = require_path(b"foreign")
        except RelocationError as error:
            rejected = _EXACT_STRING_TYPE in error.args[0]
    assert rejected, "late string alias bypassed typed relative path rejection"


def test_relocation_host_error_detail_survives_late_string_alias(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Native host diagnostics cannot be erased by late string aliases."""
    host_error_detail = cast(
        "Callable[[BaseException], str]",
        relocatable_module.__dict__["_host_error_detail"],
    )
    error = ExactTreeError("native source read failed")
    with monkeypatch.context() as patch:
        patch.setattr(builtins, "str", bytes)
        detail = host_error_detail(error)
    assert detail == error.args[0]


def test_relocation_path_preflight_rejects_late_string_spoofed_nul(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A consumer text hook must not hide NUL in a native authoring path."""
    validate_path = cast(
        "Callable[[object, str], None]",
        relocatable_module.__dict__["_validate_path"],
    )
    unsafe = Path("unsafe\x00name")

    def forge_safe_text(_: object) -> str:
        return "safe"

    rejected = False
    with monkeypatch.context() as patch:
        patch.setattr(builtins, "str", forge_safe_text)
        try:
            validate_path(unsafe, "authoring root")
        except RelocationError:
            rejected = True
    assert rejected, "late string conversion concealed unsafe source root"


def test_relocation_path_preflight_preserves_native_text_under_string_spoof(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A forged conversion cannot turn a safe native path into a NUL path."""
    validate_path = cast(
        "Callable[[object, str], None]",
        relocatable_module.__dict__["_validate_path"],
    )

    def forge_unsafe_text(_: object) -> str:
        return "unsafe\x00name"

    with monkeypatch.context() as patch:
        patch.setattr(builtins, "str", forge_unsafe_text)
        validate_path(tmp_path, "authoring root")


def test_relocation_range_locator_ignores_late_min(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Consumer hooks cannot shrink authenticated relocation windows."""
    source = b"0123456789" * 4
    native_min = min
    calls = 0

    def forged_min(*values: int) -> int:
        nonlocal calls
        if values == (32, 40):
            calls += 1
            return 1
        return native_min(*values)

    with monkeypatch.context() as patch:
        patch.setattr(builtins, "min", forged_min)
        locator = relocatable_module._range_locator(source, SourceSlice(0, 40))
    assert locator.window_bytes == 32
    assert locator.start_digest == hashlib.sha256(source[:32]).digest()
    assert calls == 0, "consumer min replaced the authenticated window"


def test_relocation_window_index_ignores_late_range(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Duplicate anchors must remain ambiguous despite consumer hooks."""
    locator = RangeLocator(2, 2, hashlib.sha256(b"AB").digest())
    native_range = range
    calls = 0

    def forged_range(*args: int) -> range:
        nonlocal calls
        if args == (3,):
            calls += 1
            return native_range(1)
        return native_range(*args)

    rejected = False
    with monkeypatch.context() as patch:
        patch.setattr(builtins, "range", forged_range)
        try:
            _ = relocatable_module._locate_range(b"ABAB", locator)
        except RelocationError as error:
            rejected = "ambiguous" in error.args[0]
    assert rejected, "consumer range hid a duplicate boundary"
    assert calls == 0, "consumer range was consulted for anchor enumeration"


@pytest.mark.parametrize("operation", ["author", "materialize"])
def test_relocation_literal_dispatch_ignores_late_isinstance(
    monkeypatch: pytest.MonkeyPatch,
    operation: str,
) -> None:
    """Exact literal segments must not consult consumer classification hooks."""
    literal = OracleLiteral(b"target")
    native_isinstance = isinstance
    calls = 0

    def forged_isinstance(value: object, expected: type[object]) -> bool:
        nonlocal calls
        if expected is OracleLiteral:
            calls += 1
            return False
        return native_isinstance(value, expected)

    with monkeypatch.context() as patch:
        patch.setattr(builtins, "isinstance", forged_isinstance)
        if operation == "author":
            result = relocatable_module._relocatable_segment(b"AB", literal)
        else:
            result = relocatable_module._patch_bytes(b"AB", (literal,))
    if operation == "author":
        assert result is literal
    else:
        assert result == b"target"
    assert calls == 0, "consumer classification hook received a literal"
