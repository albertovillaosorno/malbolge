# Copyright:
#   - Copyright © 2026 Alberto Villa Osorno.
# SPDX-License-Identifier:
#   - LicenseRef-Proprietary
# Confidential:
#   - true
# License-File:
#   - LICENSE
#
# Boundary-Contract:
# - Owns:
#   - Regression tests for physical Jig alias source and parent admission.
# - Must-Not:
#   - Install or execute native validation tools.
# - Allows:
#   - Inputs: synthetic source files and host status fault injection.
#   - Outputs: fail-closed source admission evidence.
#   - Side effects: temporary pytest paths only.
# - Split-When:
#   - A distinct alias admission responsibility gains its own lifecycle.
# - Merge-When:
#   - Another test suite owns this exact Jig source status boundary.
# - Summary:
#   - Require physical host identity before accepting Jig tool source bytes.
#

"""Physical Jig source path admission regressions."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import cast

import pytest
from scripts.bootstrap import python_validation

BINARY = b"synthetic-native-jig-binary"


@pytest.mark.parametrize("masked", [False, 0])
def test_jig_source_rejects_masked_linked_parent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    masked: object,
) -> None:
    """A linked source parent cannot be admitted through a false host predicate."""
    foreign = tmp_path / "foreign"
    foreign.mkdir()
    _ = (foreign / "tool.bin").write_bytes(BINARY)
    alias = tmp_path / "alias"
    try:
        _ = alias.symlink_to(foreign, target_is_directory=True)
    except (OSError, NotImplementedError) as error:
        pytest.skip(f"symlinks unsupported: {error}")
    native = Path.is_symlink

    def masked_symlink(path: Path) -> bool:
        if path == alias:
            return cast("bool", masked)
        return native(path)

    monkeypatch.setattr(Path, "is_symlink", masked_symlink)
    with pytest.raises(python_validation.ProvisionError, match="redirect|native"):
        _ = python_validation._read_jig_binary_source(  # pyright: ignore[reportPrivateUsage]
            alias / "tool.bin"
        )
    assert (foreign / "tool.bin").read_bytes() == BINARY


class ForeignStatus:
    """A foreign object can mimic a native filesystem stat receipt."""

    def __init__(self, observed: os.stat_result) -> None:
        self.st_mode: int = observed.st_mode
        self.st_nlink: int = observed.st_nlink
        self.st_dev: int = observed.st_dev
        self.st_ino: int = observed.st_ino
        self.st_size: int = observed.st_size
        self.st_mtime_ns: int = observed.st_mtime_ns
        self.st_ctime_ns: int = observed.st_ctime_ns


def test_jig_source_rejects_foreign_leaf_metadata(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A forged stat proxy cannot establish native Jig source identity."""
    source = tmp_path / "tool.bin"
    _ = source.write_bytes(BINARY)
    native = Path.lstat

    def forged_status(path: Path) -> os.stat_result:
        observed = native(path)
        if path == source:
            return cast("os.stat_result", cast("object", ForeignStatus(observed)))
        return observed

    monkeypatch.setattr(Path, "lstat", forged_status)
    with pytest.raises(python_validation.ProvisionError, match="native"):
        _ = python_validation._read_jig_binary_source(  # pyright: ignore[reportPrivateUsage]
            source
        )
    assert source.read_bytes() == BINARY


@pytest.mark.parametrize("predicate", ["is_symlink", "is_junction"])
@pytest.mark.parametrize("component", ["parent", "leaf"])
def test_jig_source_rejects_foreign_link_status(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    predicate: str,
    component: str,
) -> None:
    """A nonboolean link-status receipt cannot certify an alias source."""
    directory = tmp_path / "tools"
    directory.mkdir()
    source = directory / "tool.bin"
    _ = source.write_bytes(BINARY)
    affected = source if component == "leaf" else directory
    native = Path.is_symlink if predicate == "is_symlink" else Path.is_junction

    def forged_status(path: Path) -> bool:
        if path == affected:
            return cast("bool", cast("object", 0))
        return native(path)

    monkeypatch.setattr(Path, predicate, forged_status)
    with pytest.raises(python_validation.ProvisionError, match="native"):
        _ = python_validation._read_jig_binary_source(  # pyright: ignore[reportPrivateUsage]
            source
        )
    assert source.read_bytes() == BINARY


def test_jig_source_types_host_lstat_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Physical source inspection faults remain typed and causal."""
    source = tmp_path / "tool.bin"
    _ = source.write_bytes(BINARY)
    native = Path.lstat
    fault = PermissionError("source lstat denied")

    def denied_status(path: Path) -> os.stat_result:
        if path == source:
            raise fault
        return native(path)

    monkeypatch.setattr(Path, "lstat", denied_status)
    with pytest.raises(python_validation.ProvisionError, match="inspect") as caught:
        _ = python_validation._read_jig_binary_source(  # pyright: ignore[reportPrivateUsage]
            source
        )
    assert caught.value.__cause__ is fault


def test_jig_alias_stage_rejects_foreign_ownership_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A forged stage status cannot authorize a foreign leaf cleanup."""
    stage = tmp_path / "jig.tmp"
    _ = stage.write_bytes(BINARY)
    native = Path.lstat
    recorded = native(stage)

    def forged_status(path: Path) -> os.stat_result:
        if path == stage:
            return cast("os.stat_result", cast("object", ForeignStatus(recorded)))
        return native(path)

    monkeypatch.setattr(Path, "lstat", forged_status)
    assert not python_validation._jig_alias_stage_is_owned(  # pyright: ignore[reportPrivateUsage]
        stage,
        (recorded.st_dev, recorded.st_ino),
        expected_size=len(BINARY),
    )


def test_jig_alias_swap_with_forged_stage_status_preserves_target(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Forged stage metadata must not publish a foreign replacement binary."""
    if not hasattr(os, "fchmod"):
        pytest.skip("descriptor chmod unsupported")
    alias_root = tmp_path / "jig-bin"
    alias_root.mkdir()
    target = alias_root / "ruff.bin"
    original = b"verified-jig-alias"
    _ = target.write_bytes(original)
    unrelated = tmp_path / "unrelated"
    sentinel = b"x" * len(BINARY)
    _ = unrelated.write_bytes(sentinel)
    retained = tmp_path / "retained-stage"
    native_mkstemp = tempfile.mkstemp
    native_lstat = Path.lstat
    native_fchmod = os.fchmod
    stages: list[Path] = []
    stage_statuses: list[os.stat_result] = []
    swapped = False

    def capture_mkstemp(*, prefix: str, dir: Path) -> tuple[int, str]:
        descriptor, pathname = native_mkstemp(prefix=prefix, dir=dir)
        stages.append(Path(pathname))
        stage_statuses.append(native_lstat(stages[0]))
        return descriptor, pathname

    def swapping_chmod(descriptor: int, mode: int) -> None:
        nonlocal swapped
        native_fchmod(descriptor, mode)
        assert stages
        _ = stages[0].replace(retained)
        _ = unrelated.replace(stages[0])
        swapped = True

    def spoofing_lstat(path: Path) -> os.stat_result:
        if swapped and stages and path == stages[0]:
            forged = ForeignStatus(stage_statuses[0])
            forged.st_size = len(BINARY)
            return cast("os.stat_result", cast("object", forged))
        return native_lstat(path)

    with monkeypatch.context() as isolated:
        isolated.setattr(tempfile, "mkstemp", capture_mkstemp)
        isolated.setattr(os, "fchmod", swapping_chmod)
        isolated.setattr(Path, "lstat", spoofing_lstat)
        with pytest.raises(python_validation.ProvisionError, match="temporary changed"):
            python_validation._publish_jig_tool_alias(  # pyright: ignore[reportPrivateUsage]
                target, BINARY, windows=False
            )
    assert swapped
    assert len(stages) == 1
    assert stages[0].read_bytes() == sentinel
    assert retained.read_bytes() == BINARY
    assert target.read_bytes() == original


@pytest.mark.parametrize("receipt", ["descriptor", "path", "both"])
def test_jig_alias_temporary_rejects_foreign_status_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    receipt: str,
) -> None:
    """A forged stat proxy cannot bind one Jig temporary to its descriptor."""
    descriptor, name = tempfile.mkstemp(prefix=".ruff.", dir=tmp_path)
    temporary = Path(name)
    native_fstat = os.fstat
    native_lstat = Path.lstat

    def forged_fstat(fd: int) -> os.stat_result:
        observed = native_fstat(fd)
        if fd == descriptor and receipt in ("descriptor", "both"):
            return cast("os.stat_result", cast("object", ForeignStatus(observed)))
        return observed

    def forged_lstat(path: Path) -> os.stat_result:
        observed = native_lstat(path)
        if path == temporary and receipt in ("path", "both"):
            return cast("os.stat_result", cast("object", ForeignStatus(observed)))
        return observed

    try:
        with monkeypatch.context() as isolated:
            isolated.setattr(os, "fstat", forged_fstat)
            isolated.setattr(Path, "lstat", forged_lstat)
            with pytest.raises(python_validation.ProvisionError, match="native"):
                _ = python_validation._admit_jig_alias_temporary(  # pyright: ignore[reportPrivateUsage]
                    descriptor, name, alias_root=tmp_path, prefix=".ruff."
                )
    finally:
        os.close(descriptor)
        temporary.unlink()


def test_jig_alias_rejects_bytes_changed_during_atomic_replace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The published alias must still equal its pinned staged payload."""
    alias_root = tmp_path / "jig-bin"
    alias_root.mkdir()
    target = alias_root / "ruff.bin"
    _ = target.write_bytes(b"previous-jig-alias")
    native_replace = Path.replace
    mutated = False

    def corrupt_after_replace(stage: Path, destination: Path) -> Path:
        nonlocal mutated
        replaced = native_replace(stage, destination)
        if destination == target:
            with target.open("r+b") as stream:
                assert stream.write(b"!") == 1
            mutated = True
        return replaced

    monkeypatch.setattr(Path, "replace", corrupt_after_replace)
    with pytest.raises(
        python_validation.ProvisionError, match="Jig alias.*bytes"
    ):
        python_validation._publish_jig_tool_alias(  # pyright: ignore[reportPrivateUsage]
            target, BINARY, windows=True
        )
    assert mutated
    assert target.read_bytes() != BINARY


class _UnprintableAliasCreationError(OSError):
    """Host errors must not be formatted on the alias trust boundary."""

    def __str__(self) -> str:
        raise AssertionError("foreign alias creation error formatted")


def test_jig_alias_types_temporary_creation_fault(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Failure to create an alias stage cannot escape as a raw host error."""
    alias_root = tmp_path / "jig-bin"
    alias_root.mkdir()
    target = alias_root / "ruff.bin"
    fault = _UnprintableAliasCreationError("unprintable mkstemp fault")

    def fail_mkstemp(*, prefix: str, dir: Path) -> tuple[int, str]:
        assert prefix == ".ruff.bin."
        assert dir == alias_root
        raise fault

    monkeypatch.setattr(tempfile, "mkstemp", fail_mkstemp)
    with pytest.raises(
        python_validation.ProvisionError, match="Jig alias temporary creation"
    ) as captured:
        python_validation._publish_jig_tool_alias(  # pyright: ignore[reportPrivateUsage]
            target, BINARY, windows=True
        )
    assert captured.value.__cause__ is fault
    assert not target.exists()
    assert list(alias_root.iterdir()) == []


@pytest.mark.parametrize("foreign_descriptor", [False, -1, "not-a-descriptor"])
def test_jig_alias_rejects_nonnative_temporary_handle_without_closing_it(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    foreign_descriptor: object,
) -> None:
    """A forged mkstemp handle cannot redirect an attempted close to stdin."""
    alias_root = tmp_path / "jig-bin"
    alias_root.mkdir()
    target = alias_root / "ruff.bin"
    temporary = alias_root / ".ruff.bin.unowned"
    _ = temporary.write_bytes(BINARY)
    closed: list[object] = []
    native_close = os.close

    def forged_mkstemp(*, prefix: str, dir: Path) -> tuple[int, str]:
        assert prefix == ".ruff.bin."
        assert dir == alias_root
        return cast("int", foreign_descriptor), str(temporary)

    def watch_close(descriptor: int) -> None:
        if descriptor is foreign_descriptor:
            closed.append(descriptor)
            return
        native_close(descriptor)

    monkeypatch.setattr(tempfile, "mkstemp", forged_mkstemp)
    monkeypatch.setattr(os, "close", watch_close)
    with pytest.raises(
        python_validation.ProvisionError, match="Jig alias temporary.*descriptor"
    ):
        python_validation._publish_jig_tool_alias(  # pyright: ignore[reportPrivateUsage]
            target, BINARY, windows=True
        )
    assert not closed
    assert temporary.read_bytes() == BINARY
    assert not target.exists()


class _ForeignJigPayload(bytes):
    """A byte subclass is not an admitted immutable native alias payload."""


@pytest.mark.parametrize("payload", [bytearray(BINARY), _ForeignJigPayload(BINARY)])
def test_jig_alias_rejects_nonnative_payload_before_staging(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    payload: object,
) -> None:
    """Hostile mutable or subclassed payloads cannot reach a stage writer."""
    alias_root = tmp_path / "jig-bin"
    alias_root.mkdir()
    target = alias_root / "ruff.bin"

    def forbidden_mkstemp(*, prefix: str, dir: Path) -> tuple[int, str]:
        raise AssertionError("invalid alias payload reached stage creation")

    monkeypatch.setattr(tempfile, "mkstemp", forbidden_mkstemp)
    with pytest.raises(python_validation.ProvisionError, match="native bytes"):
        python_validation._publish_jig_tool_alias(  # pyright: ignore[reportPrivateUsage]
            target, cast("bytes", payload), windows=True
        )
    assert list(alias_root.iterdir()) == []


def test_jig_alias_rejects_oversized_payload_before_staging(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Oversized alias bytes are not staged even when their type is valid."""
    alias_root = tmp_path / "jig-bin"
    alias_root.mkdir()
    target = alias_root / "ruff.bin"

    def forbidden_mkstemp(*, prefix: str, dir: Path) -> tuple[int, str]:
        raise AssertionError("oversized alias payload reached stage creation")

    monkeypatch.setattr(
        python_validation, "MAX_JIG_TOOL_BINARY_BYTES", len(BINARY) - 1
    )
    monkeypatch.setattr(tempfile, "mkstemp", forbidden_mkstemp)
    with pytest.raises(python_validation.ProvisionError, match="byte limit"):
        python_validation._publish_jig_tool_alias(  # pyright: ignore[reportPrivateUsage]
            target, BINARY, windows=True
        )
    assert list(alias_root.iterdir()) == []


@pytest.mark.skipif(os.name != "posix", reason="POSIX directory descriptor race")
def test_jig_alias_rejects_symlinked_parent_swapped_after_stage_check(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A late parent symlink must not publish into an unrelated directory."""
    alias_root = tmp_path / "jig-bin"
    alias_root.mkdir()
    target = alias_root / "ruff.bin"
    owned = b"original-jig-alias"
    _ = target.write_bytes(owned)
    retained = tmp_path / "retained-jig-bin"
    foreign = tmp_path / "foreign"
    foreign.mkdir()
    foreign_target = foreign / "ruff.bin"
    sentinel = b"foreign-jig-alias"
    _ = foreign_target.write_bytes(sentinel)
    original_verify = (
        python_validation._verify_jig_alias_stage_bytes  # pyright: ignore[reportPrivateUsage]
    )
    swapped = False

    def swap_after_verification(
        stage: Path, identity: tuple[int, int], payload: bytes
    ) -> None:
        nonlocal swapped
        original_verify(stage, identity, payload)
        if not swapped and stage.parent == alias_root:
            _ = alias_root.rename(retained)
            _ = (foreign / stage.name).write_bytes(b"injected-stage")
            _ = alias_root.symlink_to(foreign, target_is_directory=True)
            swapped = True

    monkeypatch.setattr(
        python_validation,
        "_verify_jig_alias_stage_bytes",
        swap_after_verification,
    )
    with pytest.raises(python_validation.ProvisionError):
        python_validation._publish_jig_tool_alias(  # pyright: ignore[reportPrivateUsage]
            target, BINARY, windows=False
        )
    assert swapped
    assert foreign_target.read_bytes() == sentinel
    assert (retained / "ruff.bin").read_bytes() == owned


@pytest.mark.skipif(os.name != "posix", reason="POSIX directory descriptor race")
def test_jig_alias_parent_swap_during_replace_preserves_foreign_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A pinned replacement cannot overwrite a newly substituted parent."""
    alias_root = tmp_path / "jig-bin"
    alias_root.mkdir()
    target = alias_root / "ruff.bin"
    _ = target.write_bytes(b"original-jig-alias")
    retained = tmp_path / "retained-jig-bin"
    foreign = tmp_path / "foreign"
    foreign.mkdir()
    foreign_target = foreign / "ruff.bin"
    sentinel = b"foreign-jig-alias"
    _ = foreign_target.write_bytes(sentinel)
    native_replace = os.replace
    swapped = False

    def swap_during_replace(
        source: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        destination: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        *,
        src_dir_fd: int | None = None,
        dst_dir_fd: int | None = None,
    ) -> None:
        nonlocal swapped
        if not swapped:
            _ = (foreign / Path(os.fsdecode(source)).name).write_bytes(
                b"injected-stage"
            )
            _ = alias_root.rename(retained)
            _ = foreign.rename(alias_root)
            swapped = True
        native_replace(
            source,
            destination,
            src_dir_fd=src_dir_fd,
            dst_dir_fd=dst_dir_fd,
        )

    monkeypatch.setattr(os, "replace", swap_during_replace)
    with pytest.raises(python_validation.ProvisionError):
        python_validation._publish_jig_tool_alias(  # pyright: ignore[reportPrivateUsage]
            target, BINARY, windows=False
        )
    assert swapped
    assert target.read_bytes() == sentinel
    assert (retained / "ruff.bin").read_bytes() == BINARY


@pytest.mark.skipif(os.name != "posix", reason="POSIX pinned publication")
def test_jig_alias_rejects_stage_exchanged_after_byte_verification(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A same-sized substitute stage must not replace an existing alias."""
    alias_root = tmp_path / "jig-bin"
    alias_root.mkdir()
    target = alias_root / "ruff.bin"
    original = b"original-jig-alias"
    _ = target.write_bytes(original)
    retained = tmp_path / "retained-stage"
    rogue = b"x" * len(BINARY)
    original_verify = (
        python_validation._verify_jig_alias_stage_bytes  # pyright: ignore[reportPrivateUsage]
    )
    swapped = False

    def substitute_after_check(
        stage: Path, identity: tuple[int, int], payload: bytes
    ) -> None:
        nonlocal swapped
        original_verify(stage, identity, payload)
        if not swapped and stage.parent == alias_root:
            _ = stage.replace(retained)
            _ = stage.write_bytes(rogue)
            swapped = True

    monkeypatch.setattr(
        python_validation, "_verify_jig_alias_stage_bytes", substitute_after_check
    )
    with pytest.raises(python_validation.ProvisionError, match="stage changed"):
        python_validation._publish_jig_tool_alias(  # pyright: ignore[reportPrivateUsage]
            target, BINARY, windows=False
        )
    assert swapped
    assert target.read_bytes() == original
    assert retained.read_bytes() == BINARY
    stages = list(alias_root.glob(".ruff.bin.*"))
    assert len(stages) == 1
    assert stages[0].read_bytes() == rogue


@pytest.mark.parametrize("windows", [False, True])
@pytest.mark.parametrize("mutation", ["overwrite", "name-swap", "remove"])
def test_jig_alias_rejects_published_mutation_during_final_stage_cleanup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    windows: bool,
    mutation: str,
) -> None:
    """A final cleanup callback cannot approve a changed published Jig tool."""
    alias_root = tmp_path / "jig-bin"
    alias_root.mkdir()
    target = alias_root / "ruff.bin"
    _ = target.write_bytes(b"prior-alias")
    parked = tmp_path / "original-published-alias"
    native_owned = python_validation._jig_alias_stage_is_owned  # pyright: ignore[reportPrivateUsage]
    mutated = False

    def mutate_after_verification(
        temporary: Path,
        identity: tuple[int, int],
        *,
        expected_size: int | None = None,
    ) -> bool:
        nonlocal mutated
        owned = native_owned(temporary, identity, expected_size=expected_size)
        if not mutated and not temporary.exists() and target.exists():
            mutated = True
            if mutation == "overwrite":
                before = target.stat()
                _ = target.write_bytes(b"!" + BINARY[1:])
                os.utime(target, ns=(before.st_atime_ns, before.st_mtime_ns))
            elif mutation == "name-swap":
                _ = target.rename(parked)
                _ = target.write_bytes(b"!" * len(BINARY))
            else:
                target.unlink()
        return owned

    monkeypatch.setattr(
        python_validation, "_jig_alias_stage_is_owned", mutate_after_verification
    )
    with pytest.raises(python_validation.ProvisionError, match="Jig alias"):
        python_validation._publish_jig_tool_alias(  # pyright: ignore[reportPrivateUsage]
            target, BINARY, windows=windows
        )
    assert mutated
    assert not list(alias_root.glob(".ruff.bin.*"))
    if mutation == "name-swap":
        assert parked.read_bytes() == BINARY
    elif mutation == "overwrite":
        assert target.read_bytes() != BINARY
    else:
        assert not target.exists()


@pytest.mark.parametrize("restore_mtime", [False, True])
def test_jig_alias_rejects_last_readback_close_mutation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, restore_mtime: bool
) -> None:
    """A descriptor-close callback cannot rewrite the final verified alias."""
    alias_root = tmp_path / "jig-bin"
    alias_root.mkdir()
    target = alias_root / "ruff.bin"
    _ = target.write_bytes(b"previous-verified-alias")
    native_open = os.open
    native_close = os.close
    target_fds: list[int] = []
    changed = False

    def track_open(
        path: Path | str,
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        descriptor = native_open(path, flags, mode, dir_fd=dir_fd)
        if path == target:
            target_fds.append(descriptor)
        return descriptor

    def mutate_on_last_close(descriptor: int) -> None:
        nonlocal changed
        native_close(descriptor)
        if len(target_fds) == 2 and descriptor == target_fds[1] and not changed:
            before = target.stat()
            _ = target.write_bytes(b"!" + BINARY[1:])
            if restore_mtime:
                os.utime(target, ns=(before.st_atime_ns, before.st_mtime_ns))
            changed = True

    with monkeypatch.context() as isolated:
        isolated.setattr(os, "open", track_open)
        isolated.setattr(os, "close", mutate_on_last_close)
        with pytest.raises(python_validation.ProvisionError, match="Jig alias"):
            python_validation._publish_jig_tool_alias(  # pyright: ignore[reportPrivateUsage]
                target, BINARY, windows=False
            )
    assert changed
    assert len(target_fds) == 2
    assert target.read_bytes() != BINARY
