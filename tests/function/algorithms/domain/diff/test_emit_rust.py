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
#   - Synthetic compile-and-run tests for emitted std-only Rust transforms.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#

"""Synthetic compile-and-run tests for emitted std-only Rust transforms."""

from __future__ import annotations

import builtins
import hashlib
import os
import shutil
import stat

# Used only with fixed local argv and shell=False.
import subprocess as sp  # ruff: ignore[suspicious-subprocess-import]
from collections.abc import Sized
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING, cast, override

import pytest
from algorithms.diff import emit_rust as emit_rust_module
from algorithms.diff.admission import identity_tree
from algorithms.diff.emit_rust import (
    RustEmissionError,
    emit_rust_transform,
    write_rust_transform,
)
from algorithms.diff.exact import build_exact_plan, snapshot_tree
from algorithms.diff.fingerprints import AnchorPolicy
from algorithms.diff.protected import protect_exact_plan
from algorithms.diff.source_binding import (
    SourceBindingError,
    SourceBindingPolicy,
    recover_secret,
    validate_threshold_binding,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Generator
    from typing import IO

    from algorithms.diff.protected import ProtectedExactPlan

_CONTEXT = b"synthetic-rust-emitter-v1"
_PROFILE = "synthetic-rust-emitter-v1"
_BLOCK_COUNT = 48
_RUSTC_ENV = "MALBOLGE_RUSTC"
_WINDOWS_OS_NAME = "nt"
_RUSTC_NAME = "rustc.exe" if os.name == _WINDOWS_OS_NAME else "rustc"
_PINNED_RUSTC = (
    Path(__file__).resolve().parents[5]
    / ".dependencies/rust/1.98.1/bin"
    / _RUSTC_NAME
)
_TARGET_ONLY_TEXT = "TARGET-ONLY"
_NEW_TARGET_TEXT = "new-target-only"
_STD_MARKER = "use std::"
_SENTINEL = b"preserve"
_PASSTHROUGH_AUTHORING = b"authoring-external"
_PASSTHROUGH_RUNTIME = b"runtime-external"
_MAX_GENERATED_LINE_LENGTH = 80
_RUNTIME_TEMPLATE_NAME = "rust_runtime.rs"
_BOUNDARY_HEADER = "// Boundary-Contract:"
_LEGACY_FILE_HEADER = "// File:"
_LEGACY_TEMP = b"legacy-temp"
_FOREIGN_TEMP = b"foreign-temp"
_LINK_TARGET = b"link-target"
_TEMP_COLLISION_ID = "collision-id"
_EXCLUSIVE_CREATE_MODE = "x"
_LATE_OUTPUT_RECHECK = 2
_LOCATION_LEAF = "leaf"
_RUNTIME_ALIAS_EXACT = "exact"
_REALPATH_DENIAL = "deny"
_LOCATION_PARENT = "parent"
_SINGLE_CHUNK_NONCE_MARKER = (
    'const NONCE_HEX: &str = concat!("000000000000000000000000",);'
)
_INVALID_BINDING_MARKER = b"invalid generated binding"
_DUPLICATE_COORDINATE = "coordinate"
_DUPLICATE_ANCHOR = "anchor"
_BINDING_U64_BYTES = 8
_OVERLIMIT_SHARE_COUNT = 256
_OVERSIZED_SHARE_COUNT = (1 << 64) - 1
_INVALID_FRAME_COUNT_MARKER = b"generated count exceeds framed data"
_AAD_DOMAIN = b"source-bound-exact-plan-aad-v2\0"
_SNAPSHOT_COUNT = "snapshot"
_ROOT_COUNT = "roots"
_INSTRUCTION_COUNT = "instructions"
_SEGMENT_COUNT = "segments"
_PRESENT_TAG = 1
_LATE_SOURCE_DRIFT_MARKER = b"source tree changed during materialization"
_LATE_SOURCE_MUTATION = b"late mutation"


class _HostileEmissionError(OSError):
    """Host exception whose string hooks cannot be trusted."""

    @override
    def __str__(self) -> str:
        message = "untrusted Rust host exception formatter executed"
        raise AssertionError(message)


def _expect(condition: object, message: str) -> None:
    if not condition:
        raise AssertionError(message)


class _BrokenStagedRustWriter:
    def __init__(
        self,
        stream: IO[str],
        failure_type: type[Exception],
        written: list[str],
    ) -> None:
        self.stream: IO[str] = stream
        self.failure_type: type[Exception] = failure_type
        self.written: list[str] = written

    def write(self, source: str) -> int:
        _ = self.stream.write(source[:5])
        self.written.append(source[:5])
        message = "blocked Rust staging write"
        raise self.failure_type(message)

    def flush(self) -> None:
        self.stream.flush()


class _MisreportedStagedRustWriter:
    def __init__(
        self,
        stream: IO[str],
        reported: object,
        *,
        partial: bool,
    ) -> None:
        self.stream: IO[str] = stream
        self.reported: object = reported
        self.partial: bool = partial

    def write(self, source: str) -> int:
        written = self.stream.write(source[:5] if self.partial else source)
        return written if self.partial else cast("int", self.reported)

    def flush(self) -> None:
        self.stream.flush()


def _blocks(label: str) -> bytes:
    return b"".join(
        hashlib.sha256(f"{label}:{index}".encode()).digest()
        for index in range(_BLOCK_COUNT)
    )


def _write(root: Path, relative: str, data: bytes) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    _ = path.write_bytes(data)


def _fixture(
    tmp_path: Path,
) -> tuple[Path, Path, dict[str, bytes], ProtectedExactPlan]:
    source = tmp_path / "source"
    oracle = tmp_path / "oracle"
    source_files = {
        "keep.bin": _blocks("keep"),
        "patch.bin": _blocks("patch"),
        "move-from.bin": _blocks("move"),
    }
    for relative, data in source_files.items():
        _write(source, relative, data)
    _write(oracle, "keep.bin", source_files["keep.bin"])
    patch = source_files["patch.bin"]
    _write(
        oracle,
        "patch.bin",
        patch[:311] + _TARGET_ONLY_TEXT.encode() + patch[311:],
    )
    _write(oracle, "move-to.bin", source_files["move-from.bin"])
    _write(
        oracle,
        "new.bin",
        _NEW_TARGET_TEXT.encode() + b"\x00binary\xffpayload",
    )
    _write(source, "external/game.bin", _PASSTHROUGH_AUTHORING)
    _write(oracle, "external/game.bin", _PASSTHROUGH_AUTHORING)
    exact = build_exact_plan(
        source,
        oracle,
        passthrough_roots=("external",),
    )
    policy = SourceBindingPolicy(
        threshold_fraction=0.66,
        maximum_anchors=9,
        minimum_anchor_files=2,
        anchor_policy=AnchorPolicy(window_bytes=16, selection_modulus=1),
    )
    protected = protect_exact_plan(
        exact,
        identity_tree(source_files),
        binding_policy=policy,
        context=_CONTEXT,
    )
    return source, oracle, source_files, protected


def _refuse_late_metadata_read(_record: object) -> object:
    message = "emitter consulted a late metadata class getter"
    raise AssertionError(message)


@pytest.mark.parametrize(
    "field",
    [
        "source",
        "target",
        "instructions",
        "passthrough_roots",
        "context",
        "nonce",
        "payload",
        "binding",
    ],
)
def test_emitter_pins_original_protected_plan_slots(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    field: str,
) -> None:
    """Late plan getters must not rewrite authenticated emitted constants."""
    _, _, _, protected = _fixture(tmp_path)
    baseline = emit_rust_transform(protected, _PROFILE)
    with monkeypatch.context() as patch:
        patch.setattr(
            type(protected), field, property(_refuse_late_metadata_read)
        )
        emitted = emit_rust_transform(protected, _PROFILE)
    _expect(emitted == baseline, "late plan getter changed Rust emission")


@pytest.mark.parametrize(
    "field",
    [
        "context",
        "threshold",
        "minimum_anchor_files",
        "secret_length",
        "secret_commitment",
        "anchor_policy",
        "shares",
    ],
)
def test_emitter_pins_original_threshold_binding_slots(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    field: str,
) -> None:
    """Serialization must use validated binding storage, not new getters."""
    _, _, _, protected = _fixture(tmp_path)
    binding = protected.binding
    baseline = emit_rust_transform(protected, _PROFILE)
    with monkeypatch.context() as patch:
        patch.setattr(
            type(binding), field, property(_refuse_late_metadata_read)
        )
        emitted = emit_rust_transform(protected, _PROFILE)
    _expect(emitted == baseline, "late binding getter changed Rust emission")


@pytest.mark.parametrize(
    "field", ["source_path", "anchor_digest", "x", "masked_share"]
)
def test_emitter_pins_original_bound_share_slots(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    field: str,
) -> None:
    """Share coordinates and masks cannot be forged after validation."""
    _, _, _, protected = _fixture(tmp_path)
    share = protected.binding.shares[0]
    baseline = emit_rust_transform(protected, _PROFILE)
    with monkeypatch.context() as patch:
        patch.setattr(type(share), field, property(_refuse_late_metadata_read))
        emitted = emit_rust_transform(protected, _PROFILE)
    _expect(emitted == baseline, "late share getter changed Rust emission")


@pytest.mark.parametrize("field", ["window_bytes", "selection_modulus"])
def test_emitter_pins_original_anchor_policy_slots(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    field: str,
) -> None:
    """A late anchor-policy getter cannot change runtime recovery rules."""
    _, _, _, protected = _fixture(tmp_path)
    policy = protected.binding.anchor_policy
    baseline = emit_rust_transform(protected, _PROFILE)
    with monkeypatch.context() as patch:
        patch.setattr(type(policy), field, property(_refuse_late_metadata_read))
        emitted = emit_rust_transform(protected, _PROFILE)
    _expect(emitted == baseline, "late anchor policy changed Rust emission")


def _rustc() -> Path:
    configured = os.environ.get(_RUSTC_ENV)
    located = Path(configured) if configured is not None else _PINNED_RUSTC
    if not located.is_file():
        fallback = shutil.which("rustc")
        if fallback is None:
            pytest.skip("repository-pinned rustc is unavailable")
        located = Path(fallback)
    if not located.is_file():
        pytest.skip("configured rustc path is unavailable")
    return located


def _compile(rust_source: Path, executable: Path) -> sp.CompletedProcess[bytes]:
    # Fixed local compiler argv; no shell interpolation.
    return sp.run(  # ruff: ignore[subprocess-without-shell-equals-true]
        [
            str(_rustc()),
            "--edition",
            "2024",
            "-D",
            "warnings",
            str(rust_source),
            "-o",
            str(executable),
        ],
        check=False,
        capture_output=True,
        shell=False,
    )


def _run(
    executable: Path,
    source: Path | str,
    output: Path,
) -> sp.CompletedProcess[bytes]:
    # Generated executable plus explicit paths; no shell interpolation.
    return sp.run(  # ruff: ignore[subprocess-without-shell-equals-true]
        [str(executable), str(source), str(output)],
        check=False,
        capture_output=True,
        shell=False,
    )


def test_emitter_parent_creation_ignores_late_reversed_hook(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A late reversal hook cannot suppress staged parent creation."""
    target = tmp_path / "nested" / "generated" / "main.rs"
    calls = 0
    native_reversed = builtins.reversed

    def skip_parents(values: object) -> object:
        nonlocal calls
        if isinstance(values, list) and str(target.parent) in values:
            calls += 1
            return iter(())
        return native_reversed(cast("list[object]", values))

    with monkeypatch.context() as patched:
        patched.setattr(builtins, "reversed", skip_parents)
        emit_rust_module._output_mkdir(target.parent)
    assert target.parent.is_dir(), "emitter did not create its nested parent"
    assert calls == 0, "mutable reversed hook ran in output path creation"


def test_emitter_rejects_foreign_public_inputs(tmp_path: Path) -> None:
    """Validate plan, profile, and output path before template processing."""
    _, _, _, protected = _fixture(tmp_path)
    with pytest.raises(RustEmissionError, match="exact ProtectedExactPlan"):
        _ = emit_rust_transform(cast("ProtectedExactPlan", object()), _PROFILE)
    boolean_profile: object = True
    with pytest.raises(RustEmissionError, match="non-empty exact string"):
        _ = emit_rust_transform(
            protected,
            cast("str", cast("object", boolean_profile)),
        )
    with pytest.raises(RustEmissionError, match="non-empty exact string"):
        _ = emit_rust_transform(
            protected,
            cast("str", cast("object", bytearray(b"profile"))),
        )
    with pytest.raises(RustEmissionError, match="pathlib Path"):
        _ = emit_rust_transform(
            protected,
            _PROFILE,
            cast("Path", cast("object", "generated/main.rs")),
        )


class _ForeignOutputPath(type(Path())):
    """An overridden filesystem path cannot act as emission authority."""

    @override
    def __fspath__(self) -> str:
        message = "untrusted Rust output filesystem conversion ran"
        raise AssertionError(message)


@pytest.mark.parametrize("write_to_disk", [False, True])
def test_rust_emitter_rejects_foreign_output_paths_before_conversion(
    tmp_path: Path, *, write_to_disk: bool
) -> None:
    """Reject foreign Path overrides before rendering or staging output."""
    _, _, _, protected = _fixture(tmp_path)
    output = tmp_path / "foreign-generated.rs"
    foreign = _ForeignOutputPath(output)
    action = write_rust_transform if write_to_disk else emit_rust_transform
    with pytest.raises(RustEmissionError, match="pathlib Path"):
        _ = action(protected, _PROFILE, foreign)
    assert not output.exists()


@pytest.mark.parametrize("write_to_disk", [False, True])
def test_emitter_rejects_foreign_path_after_late_type_spoof(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    write_to_disk: bool,
) -> None:
    """A late type alias cannot invoke a foreign path's filesystem hook."""
    _, _, _, protected = _fixture(tmp_path)
    destination = tmp_path / "spoofed-output.rs"
    foreign = _ForeignOutputPath(destination)
    native_type = type
    native_path_type = native_type(Path())
    calls = 0

    def forge_type(value: object) -> type[object]:
        nonlocal calls
        if value is foreign:
            calls += 1
            return native_path_type
        return native_type(value)

    action = write_rust_transform if write_to_disk else emit_rust_transform
    rejected = False
    with monkeypatch.context() as patch:
        patch.setattr(builtins, "type", forge_type)
        try:
            _ = action(protected, _PROFILE, foreign)
        except RustEmissionError:
            rejected = True

    _expect(rejected, "foreign output path was accepted under type spoof")
    _expect(calls == 0, "mutable process-global type was consulted")
    _expect(not destination.exists(), "spoofed output path was written")


def test_emitter_rejects_foreign_plan_after_late_type_spoof(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A late type hook cannot promote foreign plan metadata to evidence."""
    _, _, _, protected = _fixture(tmp_path)
    foreign = object()
    native_type = type
    native_plan_type = native_type(protected)
    forged_plan = cast("ProtectedExactPlan", foreign)
    calls = 0

    def forge_type(value: object) -> type[object]:
        nonlocal calls
        if value is foreign:
            calls += 1
            return native_plan_type
        return native_type(value)

    rejected = False
    with monkeypatch.context() as patch:
        patch.setattr(builtins, "type", forge_type)
        try:
            _ = emit_rust_transform(forged_plan, _PROFILE)
        except RustEmissionError:
            rejected = True

    _expect(rejected, "foreign protected plan was accepted under type spoof")
    _expect(calls == 0, "mutable process-global type was consulted")


def test_emitter_rejects_foreign_profile_after_late_type_spoof(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A late type hook cannot admit non-string profile identifiers."""
    _, _, _, protected = _fixture(tmp_path)
    foreign = bytearray(b"synthetic")
    forged_profile = cast("str", cast("object", foreign))
    native_type = type
    calls = 0

    def forge_type(value: object) -> type[object]:
        nonlocal calls
        if value is foreign:
            calls += 1
            return str
        return native_type(value)

    rejected = False
    with monkeypatch.context() as patch:
        patch.setattr(builtins, "type", forge_type)
        try:
            _ = emit_rust_transform(protected, forged_profile)
        except RustEmissionError:
            rejected = True

    _expect(rejected, "foreign profile was accepted under type spoof")
    _expect(calls == 0, "mutable process-global type was consulted")


@pytest.mark.parametrize("write_to_disk", [False, True])
def test_emitter_rejects_nul_path_after_late_path_string_override(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    write_to_disk: bool,
) -> None:
    """Late string hooks must not hide an invalid native output path."""
    _, _, _, protected = _fixture(tmp_path)
    destination = tmp_path / "bad\x00rust.rs"
    native_string = Path.__str__
    calls = 0

    def hide_nul(path: Path) -> str:
        nonlocal calls
        if path is destination:
            calls += 1
            return native_string(path).replace("\x00", "")
        return native_string(path)

    action = write_rust_transform if write_to_disk else emit_rust_transform
    rejected = False
    with monkeypatch.context() as patch:
        patch.setattr(Path, "__str__", hide_nul)
        try:
            _ = action(protected, _PROFILE, destination)
        except RustEmissionError:
            rejected = True

    _expect(rejected, "late string hook admitted a NUL-bearing output")
    _expect(calls == 0, "mutable pathlib string hook was consulted")


class _ForeignEmissionProfile(str):
    """A string subclass cannot be admitted as an exact target profile."""


def test_emitter_rejects_late_str_spoof_of_profile(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Post-import string aliases cannot promote foreign profile metadata."""
    _, _, _, protected = _fixture(tmp_path)
    foreign = _ForeignEmissionProfile(_PROFILE)
    rejected = False
    with monkeypatch.context() as patch:
        patch.setattr(builtins, "str", _ForeignEmissionProfile)
        try:
            _ = emit_rust_transform(protected, foreign)
        except RustEmissionError:
            rejected = True
    assert rejected, "late str alias admitted a foreign profile"


def test_emitter_rejects_late_int_spoof_of_boolean_write_count(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A boolean staged count cannot impersonate a one-character write."""
    class _ForeignCountWriter:
        def write(self, _source: str) -> int:
            return cast("int", True)

    writer = cast("IO[str]", cast("object", _ForeignCountWriter()))
    verify_write = cast(
        "Callable[[IO[str], str], None]",
        vars(emit_rust_module)["_write_complete_staged_source"],
    )
    rejected = False
    with monkeypatch.context() as patch:
        patch.setattr(builtins, "int", bool)
        try:
            verify_write(writer, "x")
        except ValueError:
            rejected = True
    assert rejected, "late int alias admitted boolean write receipt"


def test_emitter_rejects_late_bool_spoof_of_junction_status(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Foreign junction status cannot authorize an output ancestor."""
    target = tmp_path / "output.rs"
    original = cast(
        "Callable[[Path], bool]", vars(emit_rust_module)["_NATIVE_IS_JUNCTION"]
    )
    output_redirects = cast(
        "Callable[[Path, int], bool]",
        vars(emit_rust_module)["_output_redirects"],
    )

    def forged_junction(path: Path) -> object:
        if path == target:
            return 0
        return original(path)

    rejected = False
    with monkeypatch.context() as patch:
        patch.setattr(emit_rust_module, "_NATIVE_IS_JUNCTION", forged_junction)
        patch.setattr(builtins, "bool", int)
        try:
            _ = output_redirects(target, 0)
        except RustEmissionError:
            rejected = True
    assert rejected, "late bool alias admitted foreign junction status"


class _ForeignEmissionDetail(str):
    """A foreign status reason cannot run arbitrary formatting code."""

    @override
    def __str__(self) -> str:
        message = "untrusted Rust status reason formatting executed"
        raise AssertionError(message)


def test_emitter_ignores_late_str_spoof_of_error_detail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Do not return a consumer-defined string subclass as a host reason."""
    foreign = _ForeignEmissionDetail("foreign")
    failure = OSError(foreign)
    safe_detail = cast(
        "Callable[[Exception], str]",
        vars(emit_rust_module)["_safe_emission_error_detail"],
    )
    with monkeypatch.context() as patch:
        patch.setattr(builtins, "str", _ForeignEmissionDetail)
        detail = safe_detail(failure)
    assert detail == "OSError"
    assert type(detail) is str


def test_emitter_error_detail_bypasses_late_native_getter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An exact Rust error cannot execute a later class args accessor."""
    failure = RustEmissionError("trusted emission failure")
    original = RustEmissionError.__getattribute__
    calls = 0

    def reject_args(error: RustEmissionError, name: str) -> object:
        nonlocal calls
        if name == "args":
            calls += 1
            raise AssertionError("late Rust error accessor executed")
        return cast("object", original(error, name))

    with monkeypatch.context() as patch:
        patch.setattr(RustEmissionError, "__getattribute__", reject_args)
        assert (
            emit_rust_module._safe_emission_error_detail(failure)
            == "trusted emission failure"
        )
    assert calls == 0, "native error text called a late class getter"


def test_writer_status_preserves_native_error_without_late_getter(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Rust output failures keep native diagnostics and original causes."""
    _, _, _, protected = _fixture(tmp_path)
    output = tmp_path / "generated.rs"
    failure = RustEmissionError("trusted status failure")
    original_getter = RustEmissionError.__getattribute__
    original_lstat = Path.lstat
    calls = 0

    def fail_lstat(path: Path) -> os.stat_result:
        if path == output:
            raise failure
        return original_lstat(path)

    def reject_args(error: RustEmissionError, name: str) -> object:
        nonlocal calls
        if name == "args":
            calls += 1
            raise AssertionError("late Rust output error getter executed")
        return cast("object", original_getter(error, name))

    with monkeypatch.context() as patch:
        patch.setattr(emit_rust_module, "_NATIVE_PATH_LSTAT", fail_lstat)
        patch.setattr(RustEmissionError, "__getattribute__", reject_args)
        with pytest.raises(
            RustEmissionError, match="trusted status failure"
        ) as caught:
            write_rust_transform(protected, _PROFILE, output)
    assert caught.value.__cause__ is failure
    assert not output.exists()
    assert calls == 0, "Rust output bridge called a late class getter"


def test_emitter_template_error_never_formats_foreign_exception(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failing runtime-template reader cannot execute an error string hook."""
    _, _, _, protected = _fixture(tmp_path)

    def fail_read(_path: Path) -> str:
        raise _HostileEmissionError("native reader failed")

    with monkeypatch.context() as patch:
        patch.setattr(emit_rust_module, "_NATIVE_TEMPLATE_READ", fail_read)
        with pytest.raises(RustEmissionError, match="template read failed"):
            _ = emit_rust_transform(protected, _PROFILE)


def test_emitter_hex_chunks_ignore_late_range_replacement(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Changing process-global range cannot omit protected Rust hex chunks."""
    original_range = range
    original = emit_rust_module._hex_constant("PAYLOAD", bytes(range(80)))
    calls = 0

    def hide_hex_chunks(*arguments: int) -> range:
        nonlocal calls
        if len(arguments) == 3 and arguments[2] == 64:
            calls += 1
            return original_range(0)
        return original_range(*arguments)

    with monkeypatch.context() as patch:
        patch.setattr(builtins, "range", hide_hex_chunks)
        generated = emit_rust_module._hex_constant(
            "PAYLOAD", bytes(original_range(80))
        )

    _expect(generated == original, "hex chunks were omitted")
    _expect(calls == 0, "mutable process-global range was consulted")


def test_emitter_binding_frame_ignores_late_len_replacement(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A later length override cannot forge source-binding share counts."""
    _, _, _, protected = _fixture(tmp_path)
    original = emit_rust_module._binding_bytes(protected.binding)
    original_len = len
    calls = 0

    def erase_share_count(value: Sized) -> int:
        nonlocal calls
        if value is protected.binding.shares:
            calls += 1
            return 0
        return original_len(value)

    with monkeypatch.context() as patch:
        patch.setattr(builtins, "len", erase_share_count)
        generated = emit_rust_module._binding_bytes(protected.binding)

    _expect(generated == original, "source-binding share count was forged")
    _expect(calls == 0, "mutable process-global len was consulted")


@pytest.mark.parametrize("filename", ["bad\x00.rs", "bad\ud800.rs"])
def test_emitter_rejects_unrepresentable_output_path(
    tmp_path: Path,
    filename: str,
) -> None:
    """Host-unrepresentable paths fail before rendering or publication."""
    _, _, _, protected = _fixture(tmp_path)
    output = tmp_path / filename
    with pytest.raises(RustEmissionError, match="Rust transform output path"):
        _ = emit_rust_transform(protected, _PROFILE, output)
    with pytest.raises(RustEmissionError, match="Rust transform output path"):
        write_rust_transform(protected, _PROFILE, output)


def test_emitted_rust_accepts_unicode_and_control_profile(
    tmp_path: Path,
) -> None:
    """A valid Unicode profile must compile with Rust string escaping."""
    _, _, _, protected = _fixture(tmp_path)
    profile = 'Unicode-\u2603-\U0001f40d\b\f\n"\\'
    source = tmp_path / "unicode-profile.rs"
    executable = tmp_path / "unicode-transform"
    _ = source.write_text(
        emit_rust_transform(protected, profile),
        encoding="utf-8",
    )
    compiled = _compile(source, executable)
    _expect(
        compiled.returncode == 0,
        "Unicode profile did not compile as Rust: "
        + compiled.stderr.decode(errors="replace"),
    )


def test_emitter_rejects_surrogate_profile_before_render(
    tmp_path: Path,
) -> None:
    """Non-scalar Unicode cannot be embedded in a Rust string literal."""
    _, _, _, protected = _fixture(tmp_path)
    with pytest.raises(RustEmissionError, match="Unicode scalar"):
        _ = emit_rust_transform(protected, "bad\ud800profile")


def test_emitter_rejects_surrogate_profile_after_late_ord_spoof(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Late Unicode hooks cannot turn invalid Rust scalars into source text."""
    _, _, _, protected = _fixture(tmp_path)
    rejected = False
    with monkeypatch.context() as patched:
        patched.setattr(builtins, "ord", lambda _: 65)
        try:
            _ = emit_rust_transform(protected, "bad\ud800profile")
        except RustEmissionError:
            rejected = True
    assert rejected, "late ord hook admitted a surrogate profile"


def test_emitter_profile_escaping_ignores_late_ord_spoof(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Late Unicode hooks cannot change deterministic Rust string escaping."""
    _, _, _, protected = _fixture(tmp_path)
    profile = "unicode-\u2603-\x08"
    baseline = emit_rust_transform(protected, profile)
    with monkeypatch.context() as patched:
        patched.setattr(builtins, "ord", lambda _: 65)
        observed = emit_rust_transform(protected, profile)
    assert observed == baseline, "late ord hook altered Rust profile escaping"


def test_emitted_rust_is_deterministic_and_hides_plaintext_literals(
    tmp_path: Path,
) -> None:
    """Emit stable standalone Rust without target literal strings."""
    _, _, _, protected = _fixture(tmp_path)

    first = emit_rust_transform(protected, _PROFILE)
    second = emit_rust_transform(protected, _PROFILE)

    _expect(first == second, "repeated Rust emission changed")
    _expect(_TARGET_ONLY_TEXT not in first, "patch literal leaked into Rust")
    _expect(_NEW_TARGET_TEXT not in first, "new-file literal leaked into Rust")
    _expect(
        _SINGLE_CHUNK_NONCE_MARKER in first,
        "single-chunk hex constant is not rustfmt-stable",
    )
    _expect(
        _STD_MARKER in first, "generated runtime lost std-only implementation"
    )
    _expect(first.startswith("// Copyright:\n"), "canonical header missing")
    _expect(_BOUNDARY_HEADER in first, "boundary header missing")
    _expect(first.count("// Copyright:") == 1, "copyright header duplicated")
    _expect(
        first.count(_BOUNDARY_HEADER) == 1,
        "runtime template boundary header leaked into generated Rust",
    )
    _expect(
        _LEGACY_FILE_HEADER not in first,
        "legacy generated file header returned",
    )
    longest = max(len(line) for line in first.splitlines())
    _expect(
        longest <= _MAX_GENERATED_LINE_LENGTH,
        f"generated Rust line length is {longest}",
    )


def test_emitted_rust_compiles_and_materializes_exact_tree(
    tmp_path: Path,
) -> None:
    """Compile emitted Rust and reconstruct the exact synthetic target."""
    source, oracle, _, protected = _fixture(tmp_path)
    rust_source = tmp_path / "generated.rs"
    executable = tmp_path / "transform.exe"
    output = tmp_path / "out"
    _ = rust_source.write_text(
        emit_rust_transform(protected, _PROFILE),
        encoding="utf-8",
        newline="\n",
    )

    compiled = _compile(rust_source, executable)
    _expect(
        compiled.returncode == 0,
        "generated Rust failed to compile: "
        + compiled.stderr.decode(errors="replace"),
    )
    completed = _run(executable, source, output)
    _expect(
        completed.returncode == 0,
        "generated transform failed: "
        + completed.stderr.decode(errors="replace"),
    )
    _expect(
        snapshot_tree(output) == snapshot_tree(oracle), "Rust output changed"
    )


def _lower_embedded_binding_threshold(
    generated: str,
    context: bytes,
) -> str:
    marker = "const BINDING_HEX: &str = concat!("
    begin = generated.index(marker)
    end = generated.index(");", begin) + 2
    declaration = generated[begin:end]
    binding_bytes = bytearray.fromhex(
        "".join(line.split('"')[1] for line in declaration.splitlines()[1:-1])
    )
    offset = 8 + len(context)
    binding_bytes[offset : offset + 8] = (1).to_bytes(8, byteorder="big")
    encoded = binding_bytes.hex()
    replacement = "\n".join((
        marker,
        *(f'    "{encoded[i : i + 64]}",' for i in range(0, len(encoded), 64)),
        ");",
    ))
    return generated.replace(declaration, replacement, 1)


def _replace_embedded_constant(
    generated: str, name: str, data: bytes
) -> str:
    marker = f"const {name}: &str = concat!("
    begin = generated.index(marker)
    end = generated.index(");", begin) + 2
    declaration = generated[begin:end]
    encoded = data.hex()
    replacement = "\n".join((
        marker,
        *(f'    "{encoded[i : i + 64]}",' for i in range(0, len(encoded), 64)),
        ");",
    ))
    return generated.replace(declaration, replacement, 1)


def _duplicate_binding_bytes(
    protected: ProtectedExactPlan, duplicate: str
) -> bytes:
    binding = protected.binding
    _expect(
        len(binding.shares) > binding.threshold,
        "fixture requires unused shares after its recovery quorum",
    )
    first = binding.shares[0]
    last = binding.shares[-1]
    if duplicate == _DUPLICATE_COORDINATE:
        replacement = replace(last, x=first.x)
    else:
        replacement = replace(
            last,
            source_path=first.source_path,
            anchor_digest=first.anchor_digest,
        )
    malformed = replace(binding, shares=(*binding.shares[:-1], replacement))
    with pytest.raises(SourceBindingError, match="unique"):
        _ = validate_threshold_binding(malformed)
    return cast(
        "Callable[[object], bytes]", vars(emit_rust_module)["_binding_bytes"]
    )(malformed)


@pytest.mark.parametrize(
    "duplicate", [_DUPLICATE_COORDINATE, _DUPLICATE_ANCHOR]
)
def test_emitted_rust_rejects_duplicate_binding_shares_before_source_reads(
    tmp_path: Path, *, duplicate: str
) -> None:
    """Reject malformed late shares even if a valid early quorum can unlock."""
    source, _, _, protected = _fixture(tmp_path)
    rust_source = tmp_path / f"duplicate-{duplicate}.rs"
    executable = tmp_path / f"duplicate-{duplicate}"
    output = tmp_path / "out"
    _ = rust_source.write_text(
        _replace_embedded_constant(
            emit_rust_transform(protected, _PROFILE),
            "BINDING_HEX",
            _duplicate_binding_bytes(protected, duplicate),
        ),
        encoding="utf-8",
        newline="\n",
    )
    compiled = _compile(rust_source, executable)
    _expect(
        compiled.returncode == 0,
        "duplicate binding runtime failed to compile: "
        + compiled.stderr.decode(errors="replace"),
    )
    completed = _run(executable, source, output)
    _expect(completed.returncode != 0, "duplicate binding was accepted")
    _expect(
        _INVALID_BINDING_MARKER in completed.stderr,
        "runtime did not reject the malformed binding envelope",
    )
    _expect(not output.exists(), "malformed binding published output")


def _binding_with_share_count(
    protected: ProtectedExactPlan, count: int
) -> bytes:
    binding = protected.binding
    raw_binding = cast(
        "Callable[[object], bytes]", vars(emit_rust_module)["_binding_bytes"]
    )(binding)
    encoded = bytearray(raw_binding)
    fields_before_count = (
        _BINDING_U64_BYTES + len(binding.context)
        + _BINDING_U64_BYTES * 3
        + _BINDING_U64_BYTES + len(binding.secret_commitment)
        + _BINDING_U64_BYTES * 2
    )
    count_end = fields_before_count + _BINDING_U64_BYTES
    _expect(
        int.from_bytes(
            encoded[fields_before_count:count_end], byteorder="big"
        ) == len(binding.shares),
        "source-binding share-count frame moved",
    )
    encoded[fields_before_count:count_end] = count.to_bytes(
        _BINDING_U64_BYTES, byteorder="big"
    )
    return bytes(encoded)


@pytest.mark.parametrize(
    "count", [_OVERLIMIT_SHARE_COUNT, _OVERSIZED_SHARE_COUNT]
)
def test_emitted_rust_rejects_oversized_binding_count_without_panic(
    tmp_path: Path, *, count: int
) -> None:
    """Reject hostile share counts before allocating an unbounded vector."""
    source, _, _, protected = _fixture(tmp_path)
    rust_source = tmp_path / f"share-count-{count}.rs"
    executable = tmp_path / f"share-count-{count}"
    output = tmp_path / "out"
    _ = rust_source.write_text(
        _replace_embedded_constant(
            emit_rust_transform(protected, _PROFILE),
            "BINDING_HEX",
            _binding_with_share_count(protected, count),
        ),
        encoding="utf-8",
        newline="\n",
    )
    compiled = _compile(rust_source, executable)
    _expect(
        compiled.returncode == 0,
        "oversized-binding runtime failed to compile: "
        + compiled.stderr.decode(errors="replace"),
    )
    completed = _run(executable, source, output)
    _expect(completed.returncode != 0, "oversized binding was accepted")
    _expect(
        _INVALID_BINDING_MARKER in completed.stderr,
        "oversized binding failed outside the typed parser boundary",
    )
    _expect(not output.exists(), "oversized binding published output")


def _read_frame_length(data: bytes | bytearray, position: int) -> int:
    return int.from_bytes(
        data[position : position + _BINDING_U64_BYTES], byteorder="big"
    )


def _skip_frame(data: bytes | bytearray, position: int) -> int:
    return position + _BINDING_U64_BYTES + _read_frame_length(data, position)


def _first_instruction_segment_count_position(
    data: bytes | bytearray, cursor: int
) -> int:
    # Kind, output path, SHA-256, source and payload optional fields.
    cursor += 1
    cursor = _skip_frame(data, cursor)
    cursor = _skip_frame(data, cursor)
    if data[cursor] == _PRESENT_TAG:
        cursor = _skip_frame(data, cursor + 1)
    else:
        cursor += 1
    if data[cursor] == _PRESENT_TAG:
        cursor += 1 + 2 * _BINDING_U64_BYTES
    else:
        cursor += 1
    return cursor


def _aad_count_position(data: bytes | bytearray, section: str) -> int:
    cursor = _skip_frame(data, len(_AAD_DOMAIN))
    if section == _SNAPSHOT_COUNT:
        cursor += _BINDING_U64_BYTES
    else:
        cursor = _skip_frame(data, cursor)
        cursor = _skip_frame(data, cursor)
        if section != _ROOT_COUNT:
            root_count = _read_frame_length(data, cursor)
            cursor += _BINDING_U64_BYTES
            for _ in range(root_count):
                cursor = _skip_frame(data, cursor)
            if section == _SEGMENT_COUNT:
                cursor = _first_instruction_segment_count_position(
                    data, cursor + _BINDING_U64_BYTES
                )
    return cursor


def _aad_with_oversized_count(
    generated: str, protected: ProtectedExactPlan, section: str
) -> bytes:
    marker = "const AAD_HEX: &str = concat!("
    begin = generated.index(marker)
    end = generated.index(");", begin) + 2
    encoded = bytearray.fromhex("".join(
        line.split('"')[1] for line in generated[begin:end].splitlines()[1:-1]
    ))
    position = _aad_count_position(encoded, section)
    expected = {
        _SNAPSHOT_COUNT: len(protected.source.files),
        _ROOT_COUNT: len(protected.passthrough_roots),
        _INSTRUCTION_COUNT: len(protected.instructions),
        _SEGMENT_COUNT: len(protected.instructions[0].segments),
    }[section]
    _expect(
        _read_frame_length(encoded, position) == expected,
        "AAD metadata count frame moved",
    )
    encoded[position : position + _BINDING_U64_BYTES] = (
        _OVERSIZED_SHARE_COUNT.to_bytes(_BINDING_U64_BYTES, byteorder="big")
    )
    return bytes(encoded)


@pytest.mark.parametrize(
    "section",
    [_SNAPSHOT_COUNT, _ROOT_COUNT, _INSTRUCTION_COUNT, _SEGMENT_COUNT],
)
def test_emitted_rust_rejects_oversized_metadata_count_without_panic(
    tmp_path: Path, *, section: str
) -> None:
    """Untrusted AAD must not allocate huge vectors before AEAD verification."""
    source, _, _, protected = _fixture(tmp_path)
    generated = emit_rust_transform(protected, _PROFILE)
    rust_source = tmp_path / f"huge-{section}.rs"
    executable = tmp_path / f"huge-{section}"
    output = tmp_path / "out"
    _ = rust_source.write_text(
        _replace_embedded_constant(
            generated, "AAD_HEX",
            _aad_with_oversized_count(generated, protected, section),
        ),
        encoding="utf-8",
        newline="\n",
    )
    compiled = _compile(rust_source, executable)
    _expect(
        compiled.returncode == 0,
        "oversized-metadata runtime failed to compile: "
        + compiled.stderr.decode(errors="replace"),
    )
    completed = _run(executable, source, output)
    _expect(completed.returncode != 0, "oversized metadata was accepted")
    _expect(
        _INVALID_FRAME_COUNT_MARKER in completed.stderr,
        "oversized metadata failed outside the bounded frame parser",
    )
    _expect(not output.exists(), "oversized metadata published output")


def _optional_anchor_fixture(
    tmp_path: Path,
) -> tuple[Path, Path, ProtectedExactPlan]:
    source, oracle, static_files, _ = _fixture(tmp_path)
    optional_path = "external/optional-anchor.bin"
    optional_bytes = _blocks("optional")
    _write(source, optional_path, optional_bytes)
    _write(oracle, optional_path, optional_bytes)
    reference = identity_tree({**static_files, optional_path: optional_bytes})
    exact = build_exact_plan(source, oracle, passthrough_roots=("external",))
    protected = protect_exact_plan(
        exact,
        reference,
        binding_policy=SourceBindingPolicy(
            threshold_fraction=0.5,
            maximum_anchors=9,
            minimum_anchor_files=2,
            anchor_policy=AnchorPolicy(window_bytes=16, selection_modulus=1),
        ),
        context=_CONTEXT,
    )
    _expect(
        any(
            share.source_path == optional_path
            for share in protected.binding.shares
        ),
        "fixture did not bind an optional runtime source",
    )
    (source / optional_path).unlink()
    (oracle / optional_path).unlink()
    _ = recover_secret(protected.binding, identity_tree(static_files))
    return source, oracle, protected


def test_emitted_rust_recovers_when_optional_anchor_file_disappears(
    tmp_path: Path,
) -> None:
    """A missing passthrough anchor must not veto an adequate static quorum."""
    source, oracle, protected = _optional_anchor_fixture(tmp_path)
    rust_source = tmp_path / "optional-anchor.rs"
    executable = tmp_path / "optional-anchor"
    output = tmp_path / "out"
    _ = rust_source.write_text(
        emit_rust_transform(protected, _PROFILE),
        encoding="utf-8",
        newline="\n",
    )
    compiled = _compile(rust_source, executable)
    _expect(
        compiled.returncode == 0,
        "optional-anchor transform failed to compile: "
        + compiled.stderr.decode(errors="replace"),
    )
    completed = _run(executable, source, output)
    _expect(
        completed.returncode == 0,
        "optional anchor blocked a valid threshold: "
        + completed.stderr.decode(errors="replace"),
    )
    _expect(
        snapshot_tree(output) == snapshot_tree(oracle),
        "missing optional anchor changed the target projection",
    )


def test_emitted_rust_rejects_binding_threshold_under_file_minimum(
    tmp_path: Path,
) -> None:
    """Malformed embedded binding metadata fails before key reconstruction."""
    source, _, _, protected = _fixture(tmp_path)
    generated = emit_rust_transform(protected, _PROFILE)
    rust_source = tmp_path / "invalid-binding.rs"
    executable = tmp_path / "invalid-binding"
    output = tmp_path / "out"
    _ = rust_source.write_text(
        _lower_embedded_binding_threshold(generated, protected.binding.context),
        encoding="utf-8",
        newline="\n",
    )
    compiled = _compile(rust_source, executable)
    _expect(
        compiled.returncode == 0,
        "malformed binding fixture failed to compile: "
        + compiled.stderr.decode(errors="replace"),
    )
    completed = _run(executable, source, output)
    _expect(completed.returncode != 0, "malformed binding was accepted")
    _expect(
        _INVALID_BINDING_MARKER in completed.stderr,
        "runtime did not reject invalid binding header",
    )
    _expect(not output.exists(), "invalid binding published output")


def _inject_source_mutation_after_staging(
    generated: str, relative_path: str
) -> str:
    seam = "        .and_then(|()| {\n"
    _expect(generated.count(seam) == 1, "publication seam changed")
    injection = (
        seam
        + (
            "            fs::write("
            f'source.join("{relative_path}"), b"late mutation")\n'
        )
        + (
            "                .map_err(|e| "
            'format!("test mutation failed: {e}"))?;\n'
        )
    )
    return generated.replace(seam, injection, 1)


def test_emitted_rust_rechecks_source_before_final_publication(
    tmp_path: Path,
) -> None:
    """Reject persistent source drift between staging and publication."""
    source, _, _, protected = _fixture(tmp_path)
    generated = emit_rust_transform(protected, _PROFILE)
    rust_source = tmp_path / "late-source.rs"
    executable = tmp_path / "late-source"
    output = tmp_path / "late-out"
    _ = rust_source.write_text(
        _inject_source_mutation_after_staging(generated, "keep.bin"),
        encoding="utf-8",
        newline="\n",
    )
    compiled = _compile(rust_source, executable)
    _expect(
        compiled.returncode == 0,
        "late-mutation runtime failed to compile: "
        + compiled.stderr.decode(errors="replace"),
    )
    completed = _run(executable, source, output)
    _expect(completed.returncode != 0, "late source drift published output")
    _expect(
        _LATE_SOURCE_DRIFT_MARKER in completed.stderr,
        "late source drift did not fail through source verification",
    )
    _expect(not output.exists(), "late source drift published output")
    _expect(
        not (tmp_path / ".late-out.diff-staging").exists(),
        "late source drift left an owned staging directory",
    )


def test_emitted_rust_allows_late_passthrough_change(
    tmp_path: Path,
) -> None:
    """The post-staging static check excludes dynamic passthrough files."""
    source, oracle, _, protected = _fixture(tmp_path)
    rust_source = tmp_path / "late-passthrough.rs"
    executable = tmp_path / "late-passthrough"
    output = tmp_path / "passthrough-out"
    _ = rust_source.write_text(
        _inject_source_mutation_after_staging(
            emit_rust_transform(protected, _PROFILE), "external/game.bin"
        ),
        encoding="utf-8",
        newline="\n",
    )
    compiled = _compile(rust_source, executable)
    _expect(
        compiled.returncode == 0,
        "late passthrough runtime failed to compile: "
        + compiled.stderr.decode(errors="replace"),
    )
    completed = _run(executable, source, output)
    _expect(
        completed.returncode == 0,
        "dynamic passthrough drift was rejected: "
        + completed.stderr.decode(errors="replace"),
    )
    _expect(
        (source / "external/game.bin").read_bytes() == _LATE_SOURCE_MUTATION,
        "late passthrough mutation did not execute",
    )
    _expect(
        snapshot_tree(output) == snapshot_tree(oracle),
        "late dynamic change modified the already-staged output",
    )


def _inject_late_empty_output_collision(generated: str) -> str:
    seam = "        .and_then(|()| {\n"
    _expect(generated.count(seam) == 1, "publication seam changed")
    collision = (
        seam
        + "            fs::create_dir(output)\n"
        + (
            "                .map_err(|e| "
            'format!("test collision failed: {e}"))?;\n'
        )
    )
    return generated.replace(seam, collision, 1)


def test_emitted_rust_preserves_late_empty_output_collision(
    tmp_path: Path,
) -> None:
    """An intervening empty destination cannot be replaced at publication."""
    source, _, _, protected = _fixture(tmp_path)
    rust_source = tmp_path / "late-collision.rs"
    executable = tmp_path / "late-collision"
    output = tmp_path / "late-out"
    _ = rust_source.write_text(
        _inject_late_empty_output_collision(
            emit_rust_transform(protected, _PROFILE)
        ),
        encoding="utf-8",
        newline="\n",
    )
    compiled = _compile(rust_source, executable)
    _expect(
        compiled.returncode == 0,
        "collision runtime failed to compile: "
        + compiled.stderr.decode(errors="replace"),
    )
    completed = _run(executable, source, output)
    _expect(completed.returncode != 0, "late output collision was overwritten")
    _expect(output.is_dir(), "foreign output directory was removed")
    _expect(not any(output.iterdir()), "foreign output contents changed")
    _expect(
        not (tmp_path / ".late-out.diff-staging").exists(),
        "collision left owned staging files",
    )


def test_emitter_ignores_post_import_template_reader_spoof(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A late pathlib reader cannot inject unreviewed Rust source."""
    _, _, _, protected = _fixture(tmp_path)
    trusted = emit_rust_transform(protected, _PROFILE)
    original_read = Path.read_text
    template = cast("Path", vars(emit_rust_module)["_RUNTIME_TEMPLATE"])
    injected = "// UNTRUSTED-RUST-TEMPLATE\n"
    calls = 0

    def forged_read(path: Path, *, encoding: str | None = None) -> str:
        nonlocal calls
        contents = original_read(path, encoding=encoding)
        if path == template:
            calls += 1
            marker = "// BEGIN GENERATED CONSTANTS"
            return contents.replace(marker, injected + marker)
        return contents

    with monkeypatch.context() as patched:
        patched.setattr(Path, "read_text", forged_read)
        generated = emit_rust_transform(protected, _PROFILE)
    assert calls == 0
    assert generated == trusted
    assert injected not in generated


def test_emitter_wraps_runtime_template_read_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Template I/O failures remain inside RustEmissionError."""
    _, _, _, protected = _fixture(tmp_path)
    original_read = Path.read_text

    def fail_template_read(path: Path) -> str:
        if path.name == _RUNTIME_TEMPLATE_NAME:
            message = "blocked runtime template"
            raise PermissionError(message)
        return original_read(path, encoding="utf-8")

    monkeypatch.setattr(
        emit_rust_module, "_NATIVE_TEMPLATE_READ", fail_template_read
    )
    with pytest.raises(RustEmissionError, match="runtime template read failed"):
        _ = emit_rust_transform(protected, _PROFILE)


def test_emitter_output_location_does_not_change_source(tmp_path: Path) -> None:
    """Filesystem destination is publication state, not transform identity."""
    _, _, _, protected = _fixture(tmp_path)
    output = tmp_path / "generated" / "transform.rs"

    default = emit_rust_transform(protected, _PROFILE)
    relocated = emit_rust_transform(protected, _PROFILE, output)

    _expect(relocated == default, "output location changed generated Rust")


@pytest.mark.parametrize("alias", ["exact", "dot-parent"])
def test_writer_never_overwrites_its_runtime_template(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, alias: str
) -> None:
    """A generated file cannot destroy the template used to generate it."""
    _, _, _, protected = _fixture(tmp_path)
    actual_template = cast("Path", vars(emit_rust_module)["_RUNTIME_TEMPLATE"])
    template = tmp_path / "rust_runtime.rs"
    original = actual_template.read_bytes()
    _ = template.write_bytes(original)
    if alias == _RUNTIME_ALIAS_EXACT:
        output = template
    else:
        output = template.parent / "sibling" / ".." / template.name
    with monkeypatch.context() as patch:
        patch.setattr(emit_rust_module, "_RUNTIME_TEMPLATE", template)
        with pytest.raises(RustEmissionError, match="runtime template"):
            write_rust_transform(protected, _PROFILE, output)
    assert template.read_bytes() == original
    assert not list(tmp_path.glob(".rust_runtime.rs.*.tmp"))


@pytest.mark.parametrize("same_path", [True, False])
def test_writer_template_identity_ignores_late_path_equality(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    same_path: bool,
) -> None:
    """A late Path equality override cannot rewrite template identity."""
    template = tmp_path / "rust_runtime.rs"
    destination = template if same_path else tmp_path / "other.rs"
    guard = cast(
        "Callable[[Path], None]",
        vars(emit_rust_module)["_require_output_not_runtime_template"],
    )

    def forged_equality(_left: Path, _right: object) -> bool:
        return not same_path

    with monkeypatch.context() as patch:
        patch.setattr(emit_rust_module, "_RUNTIME_TEMPLATE", template)
        patch.setattr(type(template), "__eq__", forged_equality)
        if same_path:
            with pytest.raises(RustEmissionError, match="runtime template"):
                guard(destination)
        else:
            guard(destination)


@pytest.mark.parametrize("forged_result", ["launder", _REALPATH_DENIAL])
def test_writer_template_resolve_rejects_replaced_host_realpath(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    forged_result: str,
) -> None:
    """The captured Path resolver must not invoke mutable host realpath."""
    template = tmp_path / "rust_runtime.rs"
    guard = cast(
        "Callable[[Path], None]",
        vars(emit_rust_module)["_require_output_not_runtime_template"],
    )
    calls = 0

    def forged_realpath(path: object, *, strict: bool = False) -> str:
        nonlocal calls
        del path, strict
        calls += 1
        if forged_result == _REALPATH_DENIAL:
            message = "untrusted host realpath invoked"
            raise AssertionError(message)
        label = "forged.rs" if calls == 1 else "rust_runtime.rs"
        return str(tmp_path / label)

    with monkeypatch.context() as patch:
        patch.setattr(emit_rust_module, "_RUNTIME_TEMPLATE", template)
        patch.setattr(os.path, "realpath", forged_realpath)
        with pytest.raises(RustEmissionError, match="path resolution"):
            guard(template)
    assert calls == 0


@pytest.mark.parametrize("dependency", ["lstat", "readlink", "getcwd", "islink"])
def test_writer_template_resolution_rejects_late_host_dependencies(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, dependency: str
) -> None:
    """Original realpath still delegates to mutable host path dependencies."""
    template = tmp_path / "rust_runtime.rs"
    guard = cast(
        "Callable[[Path], None]",
        vars(emit_rust_module)["_require_output_not_runtime_template"],
    )
    calls = 0

    def forbidden(*_args: object, **_kwargs: object) -> object:
        nonlocal calls
        calls += 1
        raise AssertionError("untrusted native path hook invoked")

    with monkeypatch.context() as patch:
        patch.setattr(emit_rust_module, "_RUNTIME_TEMPLATE", template)
        if dependency == "islink":
            patch.setattr(stat, "S_ISLNK", forbidden)
        else:
            patch.setattr(os, dependency, forbidden)
        with pytest.raises(RustEmissionError, match="path resolution hooks changed"):
            guard(template)
    assert calls == 0


@pytest.mark.parametrize("helper", ["isinstance", "len"])
def test_writer_template_rejects_late_realpath_builtin_callback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, helper: str
) -> None:
    """Template containment must not call late realpath builtin helpers."""
    output = tmp_path / "output.rs"
    original = cast("Callable[..., object]", getattr(builtins, helper))
    calls = 0

    def watched(*args: object, **kwargs: object) -> object:
        nonlocal calls
        calls += 1
        return original(*args, **kwargs)

    rejected = False
    with monkeypatch.context() as patch:
        patch.setattr(builtins, helper, watched)
        try:
            emit_rust_module._require_output_not_runtime_template(output)
        except RustEmissionError:
            rejected = True
    assert rejected, f"late builtin {helper} was admitted"
    assert calls == 0, f"late builtin {helper} callback was executed"


def test_writer_template_rejects_late_realpath_bytes_alias(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A forged bytes type cannot change output-template resolution."""
    output = tmp_path / "output.rs"
    rejected = False
    with monkeypatch.context() as patch:
        patch.setattr(builtins, "bytes", str)
        try:
            emit_rust_module._require_output_not_runtime_template(output)
        except RustEmissionError:
            rejected = True
    assert rejected, "late bytes alias reached template resolution"


def test_writer_template_rejects_late_host_splitroot_callback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An uncached output must not consult the mutable host path splitter."""
    output = tmp_path / "output.rs"
    original = os.path.splitroot
    calls = 0

    def watched(path: str) -> tuple[str, str, str]:
        nonlocal calls
        calls += 1
        return original(path)

    rejected = False
    with monkeypatch.context() as patch:
        patch.setattr(os.path, "splitroot", watched)
        try:
            emit_rust_module._require_output_not_runtime_template(output)
        except RustEmissionError:
            rejected = True
    assert rejected, "late host splitroot callback was admitted"
    assert calls == 0, "late host splitter was executed"


@pytest.mark.parametrize("guard", ["string", "resolution"])
def test_emitter_path_guards_reject_late_any_suppression(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, guard: str
) -> None:
    """Late any() must not hide a substituted native path dependency."""
    target = tmp_path / "output.rs"
    calls = 0

    def forbidden(*_args: object, **_kwargs: object) -> object:
        nonlocal calls
        calls += 1
        raise AssertionError("untrusted path hook invoked")

    with monkeypatch.context() as patch:
        patch.setattr(builtins, "any", lambda _items: False)
        if guard == "string":
            patch.setattr(Path, "_tail", property(forbidden))
            with pytest.raises(RustEmissionError, match="path hooks changed"):
                _ = emit_rust_module._native_path_string(target)
        else:
            patch.setattr(Path, "with_segments", forbidden)
            with pytest.raises(
                RustEmissionError, match="path resolution hooks changed"
            ):
                emit_rust_module._require_output_not_runtime_template(target)
    assert calls == 0


@pytest.mark.parametrize("hook", ["with_segments", "__new__", "__init__"])
def test_writer_template_resolution_rejects_late_path_factories(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, hook: str
) -> None:
    """A captured Path.resolve must not invoke mutable path constructors."""
    template = tmp_path / "rust_runtime.rs"
    guard = cast(
        "Callable[[Path], None]",
        vars(emit_rust_module)["_require_output_not_runtime_template"],
    )
    calls = 0

    def forbidden(*_args: object, **_kwargs: object) -> object:
        nonlocal calls
        calls += 1
        raise AssertionError("untrusted pathlib factory invoked")

    with monkeypatch.context() as patch:
        patch.setattr(Path, hook, forbidden)
        patch.setattr(emit_rust_module, "_RUNTIME_TEMPLATE", template)
        with pytest.raises(RustEmissionError, match="path resolution hooks changed"):
            guard(template)
    assert calls == 0


def test_writer_template_symlink_alias_rejects_late_readlink(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Host readlink substitution cannot disguise the runtime template alias."""
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    template = runtime / "rust_runtime.rs"
    template.write_text("keep", encoding="utf-8")
    alias = tmp_path / "alias"
    try:
        alias.symlink_to(runtime, target_is_directory=True)
    except OSError:
        pytest.skip("directory symlinks unavailable")
    output = alias / template.name
    guard = cast(
        "Callable[[Path], None]",
        vars(emit_rust_module)["_require_output_not_runtime_template"],
    )
    native_readlink = os.readlink
    calls = 0

    def misdirected_readlink(
        path: str | os.PathLike[str], *args: object, **kwargs: object
    ) -> str:
        nonlocal calls
        if os.fspath(path) == str(alias):
            calls += 1
            return str(tmp_path / "different-directory")
        return native_readlink(path, *args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(emit_rust_module, "_RUNTIME_TEMPLATE", template)
        patch.setattr(os, "readlink", misdirected_readlink)
        with pytest.raises(RustEmissionError, match="path resolution hooks changed"):
            guard(output)
    assert calls == 0
    assert template.read_text(encoding="utf-8") == "keep"


def test_writer_parent_walk_ignores_late_path_equality(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A root ancestor still terminates the walk with a lying class hook."""
    walk = cast(
        "Callable[[Path], None]",
        vars(emit_rust_module)["_validate_output_parent_chain"],
    )
    calls = 0

    def false_equality(_left: Path, _right: object) -> bool:
        nonlocal calls
        calls += 1
        if calls > 20:
            message = "parent traversal consulted mutable Path equality"
            raise AssertionError(message)
        return False

    with monkeypatch.context() as patch:
        patch.setattr(type(tmp_path), "__eq__", false_equality)
        walk(tmp_path)
    _expect(calls == 0, "parent walk relied on late Path equality")


@pytest.mark.parametrize("forged_equal", [True, False])
def test_writer_publishes_without_late_path_equality(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    forged_equal: bool,
) -> None:
    """The writer and receipt check do not trust patched Path comparisons."""
    _, _, _, protected = _fixture(tmp_path)
    expected = emit_rust_transform(protected, _PROFILE)
    output = tmp_path / "generated" / "transform.rs"

    def forged_equality(_left: Path, _right: object) -> bool:
        return forged_equal

    with monkeypatch.context() as patch:
        patch.setattr(type(output), "__eq__", forged_equality)
        write_rust_transform(protected, _PROFILE, output)
    _expect(
        output.read_text(encoding="utf-8") == expected,
        "path equality hook altered generated publication",
    )


def test_writer_rejects_forged_native_template_resolution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Changing the host resolver cannot authorize template self-overwrite."""
    _, _, _, protected = _fixture(tmp_path)
    actual = cast("Path", vars(emit_rust_module)["_RUNTIME_TEMPLATE"])
    template = tmp_path / "rust_runtime.rs"
    original = actual.read_bytes()
    _ = template.write_bytes(original)
    native_resolve = Path.resolve
    checked = 0

    def forged_resolve(path: Path, *, strict: bool = False) -> Path:
        nonlocal checked
        if path == template:
            checked += 1
            if checked == 1:
                return tmp_path / "not-the-template.rs"
        return native_resolve(path, strict=strict)

    with monkeypatch.context() as patch:
        patch.setattr(emit_rust_module, "_RUNTIME_TEMPLATE", template)
        patch.setattr(Path, "resolve", forged_resolve)
        with pytest.raises(RustEmissionError, match="runtime template"):
            write_rust_transform(protected, _PROFILE, template)
    assert checked == 0
    assert template.read_bytes() == original
    assert not list(tmp_path.glob(".rust_runtime.rs.*.tmp"))


def test_writer_rejects_linked_output_file_when_supported(
    tmp_path: Path,
) -> None:
    """Do not publish generated Rust through an output symlink."""
    _, _, _, protected = _fixture(tmp_path)
    target = tmp_path / "target.rs"
    _ = target.write_bytes(_LINK_TARGET)
    output = tmp_path / "generated.rs"
    try:
        output.symlink_to(target)
    except OSError:
        pytest.skip("symlink creation is unavailable on this host")

    with pytest.raises(RustEmissionError, match="regular non-linked file"):
        write_rust_transform(protected, _PROFILE, output)

    assert target.read_bytes() == _LINK_TARGET
    assert output.is_symlink()


def test_writer_rejects_linked_output_parent_when_supported(
    tmp_path: Path,
) -> None:
    """Do not traverse a linked parent while publishing generated Rust."""
    _, _, _, protected = _fixture(tmp_path)
    target_parent = tmp_path / "target-parent"
    target_parent.mkdir()
    linked_parent = tmp_path / "linked-parent"
    try:
        linked_parent.symlink_to(target_parent, target_is_directory=True)
    except OSError:
        pytest.skip("directory symlink creation is unavailable on this host")
    output = linked_parent / "generated.rs"

    with pytest.raises(RustEmissionError, match="parent must not be linked"):
        write_rust_transform(protected, _PROFILE, output)

    assert not (target_parent / "generated.rs").exists()


def _linked_emission_output(
    tmp_path: Path, location: str
) -> tuple[Path, Path, Path, Path]:
    real = tmp_path / "external"
    real.mkdir()
    if location == _LOCATION_PARENT:
        linked = tmp_path / "linked"
        try:
            linked.symlink_to(real, target_is_directory=True)
        except OSError, NotImplementedError:
            pytest.skip("directory symlinks unavailable")
        return linked / "generated.rs", linked, real / "generated.rs", real
    victim = real / "victim.rs"
    _ = victim.write_bytes(_SENTINEL)
    output = tmp_path / "generated.rs"
    try:
        output.symlink_to(victim)
    except OSError, NotImplementedError:
        pytest.skip("symlinks unavailable")
    return output, output, victim, victim


def _assert_emission_link_preserved(
    linked: Path, victim: Path, *, location: str
) -> None:
    assert linked.is_symlink()
    if location == _LOCATION_LEAF:
        assert victim.read_bytes() == _SENTINEL
    else:
        assert not victim.exists()


@pytest.mark.parametrize("location", [_LOCATION_LEAF, _LOCATION_PARENT])
def test_writer_rejects_post_import_path_lstat_spoof(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, location: str
) -> None:
    """A late pathlib hook cannot authorize writing through a linked output."""
    _, _, _, protected = _fixture(tmp_path)
    output, linked, victim, spoof_target = _linked_emission_output(
        tmp_path, location
    )
    native_lstat = Path.lstat
    forged_count = 0

    def forged_lstat(path: Path) -> os.stat_result:
        nonlocal forged_count
        if path == linked:
            forged_count += 1
            return native_lstat(spoof_target)
        return native_lstat(path)

    with monkeypatch.context() as patched:
        patched.setattr(Path, "lstat", forged_lstat)
        with pytest.raises(
            RustEmissionError,
            match=r"parent must not be linked|regular non-linked file",
        ):
            write_rust_transform(protected, _PROFILE, output)
    assert forged_count == 0
    _assert_emission_link_preserved(linked, victim, location=location)


@pytest.mark.parametrize("location", [_LOCATION_LEAF, _LOCATION_PARENT])
def test_writer_rejects_post_import_os_lstat_spoof(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, location: str
) -> None:
    """A late os.lstat hook cannot authorize linked output publication."""
    _, _, _, protected = _fixture(tmp_path)
    output, linked, victim, spoof_target = _linked_emission_output(
        tmp_path, location
    )
    native_lstat = os.lstat

    def forged_lstat(path: str | os.PathLike[str]) -> os.stat_result:
        if Path(path) == linked:
            return native_lstat(spoof_target)
        return native_lstat(path)

    with monkeypatch.context() as patched:
        patched.setattr(os, "lstat", forged_lstat)
        with pytest.raises(
            RustEmissionError,
            match=r"path resolution hooks changed|parent must not be linked|regular non-linked file",
        ):
            write_rust_transform(protected, _PROFILE, output)
    # Other pathlib operations may consult os.lstat; output classification
    # must use only the captured native syscall.
    _assert_emission_link_preserved(linked, victim, location=location)


def test_writer_rejects_directory_output(tmp_path: Path) -> None:
    """An existing output directory cannot be replaced as a generated file."""
    _, _, _, protected = _fixture(tmp_path)
    output = tmp_path / "generated.rs"
    output.mkdir()

    with pytest.raises(RustEmissionError, match="regular non-linked file"):
        write_rust_transform(protected, _PROFILE, output)

    assert output.is_dir()


@pytest.mark.parametrize(
    "failure_type", [PermissionError, ValueError, RuntimeError]
)
def test_writer_wraps_output_status_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure_type: type[Exception],
) -> None:
    """An inaccessible output leaf stays inside RustEmissionError."""
    _, _, _, protected = _fixture(tmp_path)
    output = tmp_path / "generated.rs"
    original_lstat = Path.lstat

    def fail_lstat(path: Path) -> object:
        if path == output:
            message = "blocked Rust output status"
            raise failure_type(message)
        return original_lstat(path)

    monkeypatch.setattr(emit_rust_module, "_NATIVE_PATH_LSTAT", fail_lstat)
    with pytest.raises(RustEmissionError, match="output file status failed"):
        write_rust_transform(protected, _PROFILE, output)


@pytest.mark.parametrize("location", [_LOCATION_LEAF, _LOCATION_PARENT])
def test_writer_rejects_foreign_output_status_before_publication(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    location: str,
) -> None:
    """Foreign file/parent metadata cannot authorize a Rust source write."""
    _, _, _, protected = _fixture(tmp_path)
    output = tmp_path / "generated.rs"
    if location == _LOCATION_LEAF:
        _ = output.write_bytes(_SENTINEL)
    target = output if location == _LOCATION_LEAF else output.parent
    original_lstat = Path.lstat
    native = original_lstat(target)
    foreign = SimpleNamespace(st_mode=native.st_mode)

    def forged_lstat(path: Path) -> os.stat_result:
        if path == target:
            return cast("os.stat_result", cast("object", foreign))
        return original_lstat(path)

    monkeypatch.setattr(emit_rust_module, "_NATIVE_PATH_LSTAT", forged_lstat)
    with pytest.raises(RustEmissionError, match="native filesystem status"):
        write_rust_transform(protected, _PROFILE, output)
    if location == _LOCATION_LEAF:
        assert output.read_bytes() == _SENTINEL
    else:
        assert not output.exists()
    assert not list(tmp_path.glob(".generated.rs.*.tmp"))


@pytest.mark.parametrize("location", [_LOCATION_LEAF, _LOCATION_PARENT])
def test_writer_rejects_foreign_junction_boolean(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, location: str
) -> None:
    """A false-like foreign result must not authorize output publication."""
    _, _, _, protected = _fixture(tmp_path)
    output = tmp_path / "generated.rs"
    if location == _LOCATION_LEAF:
        _ = output.write_bytes(_SENTINEL)
    checked = output if location == _LOCATION_LEAF else tmp_path
    native_is_junction = Path.is_junction
    observed = False

    def forged_is_junction(path: Path) -> object:
        nonlocal observed
        if path == checked:
            observed = True
            return 0
        return native_is_junction(path)

    monkeypatch.setattr(
        emit_rust_module, "_NATIVE_IS_JUNCTION", forged_is_junction
    )
    with pytest.raises(RustEmissionError, match="native boolean"):
        write_rust_transform(protected, _PROFILE, output)
    _expect(observed, "foreign junction result was not observed")
    if location == _LOCATION_LEAF:
        _expect(output.read_bytes() == _SENTINEL, "output was overwritten")
    else:
        _expect(not output.exists(), "foreign junction published output")


@pytest.mark.parametrize("location", [_LOCATION_LEAF, _LOCATION_PARENT])
def test_writer_rejects_foreign_template_resolution_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, location: str
) -> None:
    """A foreign resolved path cannot control runtime-template protection."""
    _, _, _, protected = _fixture(tmp_path)
    output = tmp_path / "generated.rs"
    original_resolve = cast(
        "Callable[[Path], Path]",
        vars(emit_rust_module)["_NATIVE_RESOLVE"],
    )
    observed = False

    def forged_resolve(path: Path) -> Path:
        nonlocal observed
        selected = (
            path == output
            if location == _LOCATION_LEAF
            else path.name == _RUNTIME_TEMPLATE_NAME
        )
        if selected:
            observed = True
            return _ForeignOutputPath(path)
        return original_resolve(path)

    monkeypatch.setattr(emit_rust_module, "_NATIVE_RESOLVE", forged_resolve)
    with pytest.raises(RustEmissionError, match="native Path"):
        write_rust_transform(protected, _PROFILE, output)
    _expect(observed, "foreign resolved path was not observed")
    _expect(not output.exists(), "foreign resolution published output")


@pytest.mark.parametrize("location", [_LOCATION_LEAF, _LOCATION_PARENT])
@pytest.mark.parametrize("failure_type", [OSError, ValueError, RuntimeError])
def test_writer_wraps_output_junction_inspection_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    location: str,
    failure_type: type[Exception],
) -> None:
    """Broken junction checks cannot leak host errors before publication."""
    _, _, _, protected = _fixture(tmp_path)
    output = tmp_path / "generated.rs"
    if location == _LOCATION_LEAF:
        _ = output.write_bytes(_SENTINEL)
    checked_path = output if location == _LOCATION_LEAF else tmp_path
    original_is_junction = Path.is_junction

    def fail_junction(path: Path) -> bool:
        if path == checked_path:
            message = "blocked Rust output junction status"
            raise failure_type(message)
        return original_is_junction(path)

    monkeypatch.setattr(
        emit_rust_module, "_NATIVE_IS_JUNCTION", fail_junction
    )
    with pytest.raises(RustEmissionError, match="junction status failed"):
        write_rust_transform(protected, _PROFILE, output)
    if location == _LOCATION_LEAF:
        assert output.read_bytes() == _SENTINEL
    else:
        assert not output.exists()
    assert not list(tmp_path.glob(".generated.rs.*.tmp"))


@pytest.mark.parametrize(
    "failure_type", [PermissionError, ValueError, RuntimeError]
)
def test_writer_wraps_output_parent_creation_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure_type: type[Exception],
) -> None:
    """Invalid output parent creation fails before temporary publication."""
    _, _, _, protected = _fixture(tmp_path)
    parent = tmp_path / "generated"
    output = parent / "main.rs"
    original_mkdir = emit_rust_module._output_mkdir

    def fail_mkdir(path: Path) -> None:
        if path == parent:
            message = "blocked Rust output parent creation"
            raise failure_type(message)
        original_mkdir(path)

    monkeypatch.setattr(emit_rust_module, "_output_mkdir", fail_mkdir)
    with pytest.raises(
        RustEmissionError, match="output parent creation failed"
    ):
        write_rust_transform(protected, _PROFILE, output)
    assert not parent.exists(), "failed output creation left generated parent"
    assert not output.exists(), "failed output creation published Rust"


def test_writer_cleans_staging_after_late_junction_inspection_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A failed post-staging junction query keeps original output intact."""
    _, _, _, protected = _fixture(tmp_path)
    output = tmp_path / "generated.rs"
    _ = output.write_bytes(_SENTINEL)
    original_is_junction = Path.is_junction
    checked = 0

    def fail_late_junction(path: Path) -> bool:
        nonlocal checked
        if path == output:
            checked += 1
            if checked == _LATE_OUTPUT_RECHECK:
                assert list(tmp_path.glob(".generated.rs.*.tmp"))
                message = "blocked late Rust output junction status"
                raise OSError(message)
        return original_is_junction(path)

    monkeypatch.setattr(
        emit_rust_module, "_NATIVE_IS_JUNCTION", fail_late_junction
    )
    with pytest.raises(RustEmissionError, match="junction status failed"):
        write_rust_transform(protected, _PROFILE, output)
    assert checked == _LATE_OUTPUT_RECHECK
    assert output.read_bytes() == _SENTINEL
    assert not list(tmp_path.glob(".generated.rs.*.tmp"))


def test_writer_cleans_temporary_after_output_recheck_rejects(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A post-write output swap cannot leave an orphaned owned temporary."""
    _, _, _, protected = _fixture(tmp_path)
    output = tmp_path / "generated.rs"
    checks = 0

    def reject_late(path: Path) -> None:
        nonlocal checks
        assert path == output
        checks += 1
        if checks == _LATE_OUTPUT_RECHECK:
            assert list(tmp_path.glob(".generated.rs.*.tmp"))
            message = "Rust output path must not be linked after staging"
            raise RustEmissionError(message)

    monkeypatch.setattr(emit_rust_module, "_validate_output_leaf", reject_late)
    with pytest.raises(RustEmissionError, match="must not be linked"):
        write_rust_transform(protected, _PROFILE, output)
    assert not output.exists()
    assert not list(tmp_path.glob(".generated.rs.*.tmp"))


@pytest.mark.parametrize(
    "failure_type", [PermissionError, ValueError, RuntimeError]
)
def test_writer_cleans_owned_temporary_after_replace_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure_type: type[Exception],
) -> None:
    """Failed publication cannot leave an owned staging file behind."""
    _, _, _, protected = _fixture(tmp_path)
    output = tmp_path / "generated.rs"
    original_replace = emit_rust_module._output_replace
    attempted: list[Path] = []

    def reject_replace(path: Path, target: Path) -> Path:
        if target == output:
            attempted.append(path)
            assert path.exists(), "fixture missed staged Rust source"
            message = "blocked Rust output publication"
            raise failure_type(message)
        return original_replace(path, target)

    monkeypatch.setattr(emit_rust_module, "_output_replace", reject_replace)
    with pytest.raises(RustEmissionError, match="publication failed"):
        write_rust_transform(protected, _PROFILE, output)
    assert attempted, "fixture did not reach atomic publication"
    assert not output.exists(), "failed emission published output"
    assert not list(tmp_path.glob(".generated.rs.*.tmp"))


@pytest.mark.parametrize(
    "failure_type", [PermissionError, ValueError, RuntimeError]
)
def test_writer_cleans_owned_temporary_after_write_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure_type: type[Exception],
) -> None:
    """Post-claim write failures must remove only the owned temporary."""
    _, _, _, protected = _fixture(tmp_path)
    output = tmp_path / "generated.rs"
    template_loader = cast(
        "Callable[[], str]", vars(emit_rust_module)["_runtime_template_text"]
    )
    template = template_loader()
    monkeypatch.setattr(
        emit_rust_module, "_runtime_template_text", lambda: template
    )
    original_open = emit_rust_module._staged_output_open
    wrote: list[str] = []

    @contextmanager
    def fail_after_open(path: Path) -> Generator[_BrokenStagedRustWriter]:
        with original_open(path) as stream:
            yield _BrokenStagedRustWriter(stream, failure_type, wrote)

    monkeypatch.setattr(
        emit_rust_module, "_staged_output_open", fail_after_open
    )
    with pytest.raises(RustEmissionError, match="publication failed"):
        write_rust_transform(protected, _PROFILE, output)
    assert wrote, "fixture did not write to the owned temporary"
    assert not output.exists(), "failed emission published output"
    assert not list(tmp_path.glob(".generated.rs.*.tmp"))


@pytest.mark.parametrize(
    "case",
    [(True, None), (False, None), (False, True), (False, -1), (False, 10**9)],
)
def test_writer_rejects_short_or_invalid_staging_write_count(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    case: tuple[bool, object],
) -> None:
    """A partial or misreported text write cannot publish generated Rust."""
    _, _, _, protected = _fixture(tmp_path)
    output = tmp_path / "generated.rs"
    partial, reported = case
    template_loader = cast(
        "Callable[[], str]", vars(emit_rust_module)["_runtime_template_text"]
    )
    template = template_loader()
    monkeypatch.setattr(
        emit_rust_module, "_runtime_template_text", lambda: template
    )
    original_open = emit_rust_module._staged_output_open

    @contextmanager
    def misreport_staged_write(
        path: Path,
    ) -> Generator[_MisreportedStagedRustWriter]:
        with original_open(path) as stream:
            yield _MisreportedStagedRustWriter(
                stream, reported, partial=partial
            )

    monkeypatch.setattr(
        emit_rust_module, "_staged_output_open", misreport_staged_write
    )
    with pytest.raises(RustEmissionError, match="publication failed"):
        write_rust_transform(protected, _PROFILE, output)
    assert not output.exists()
    assert not list(tmp_path.glob(".generated.rs.*.tmp"))


@pytest.mark.parametrize("cleanup_error", [ValueError, RuntimeError])
def test_writer_preserves_primary_error_after_invalid_cleanup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    cleanup_error: type[Exception],
) -> None:
    """Broken host cleanup cannot mask an already failed publication."""
    _, _, _, protected = _fixture(tmp_path)
    output = tmp_path / "generated.rs"
    original_unlink = emit_rust_module._output_unlink
    original_replace = emit_rust_module._output_replace
    attempted: list[Path] = []

    def reject_replace(path: Path, target: Path) -> Path:
        if target == output:
            attempted.append(path)
            message = "blocked atomic Rust output publication"
            raise RuntimeError(message)
        return original_replace(path, target)

    def reject_cleanup(path: Path) -> None:
        if path in attempted:
            message = "injected cleanup failure"
            raise cleanup_error(message)
        original_unlink(path)

    with monkeypatch.context() as patch:
        patch.setattr(emit_rust_module, "_output_replace", reject_replace)
        patch.setattr(emit_rust_module, "_output_unlink", reject_cleanup)
        with pytest.raises(
            RustEmissionError,
            match=r"publication failed.*temporary cleanup failed",
        ):
            write_rust_transform(protected, _PROFILE, output)
    assert len(attempted) == 1
    assert not output.exists()
    assert attempted[0].is_file()
    attempted[0].unlink()


def test_writer_status_does_not_format_hostile_exception(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Status failure stays typed without executing a host string hook."""
    _, _, _, protected = _fixture(tmp_path)
    output = tmp_path / "generated.rs"
    failure = _HostileEmissionError("hostile output stat")
    original_lstat = Path.lstat

    def fail_lstat(path: Path) -> os.stat_result:
        if path == output:
            raise failure
        return original_lstat(path)

    monkeypatch.setattr(emit_rust_module, "_NATIVE_PATH_LSTAT", fail_lstat)
    with pytest.raises(
        RustEmissionError, match="output file status failed"
    ) as caught:
        write_rust_transform(protected, _PROFILE, output)
    assert caught.value.__cause__ is failure
    assert not output.exists()


def test_writer_replace_does_not_format_hostile_exception(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Rename failure cannot invoke untrusted exception formatters."""
    _, _, _, protected = _fixture(tmp_path)
    output = tmp_path / "generated.rs"
    failure = _HostileEmissionError("hostile rename")
    original_replace = emit_rust_module._output_replace

    def fail_replace(path: Path, target: Path) -> Path:
        if target == output:
            raise failure
        return original_replace(path, target)

    monkeypatch.setattr(emit_rust_module, "_output_replace", fail_replace)
    with pytest.raises(RustEmissionError, match="publication failed") as caught:
        write_rust_transform(protected, _PROFILE, output)
    assert caught.value.__cause__ is failure
    assert not output.exists()
    assert not list(tmp_path.glob(".generated.rs.*.tmp"))


def test_writer_cleanup_does_not_format_hostile_exception(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A hostile secondary cleanup error cannot mask publication failure."""
    _, _, _, protected = _fixture(tmp_path)
    output = tmp_path / "generated.rs"
    original_replace = emit_rust_module._output_replace
    original_unlink = emit_rust_module._output_unlink
    attempted: list[Path] = []

    def fail_replace(path: Path, target: Path) -> Path:
        if target == output:
            attempted.append(path)
            message = "primary Rust rename failure"
            raise OSError(message)
        return original_replace(path, target)

    def fail_unlink(path: Path) -> None:
        if path in attempted:
            message = "hostile Rust cleanup"
            raise _HostileEmissionError(message)
        original_unlink(path)

    with monkeypatch.context() as patch:
        patch.setattr(emit_rust_module, "_output_replace", fail_replace)
        patch.setattr(emit_rust_module, "_output_unlink", fail_unlink)
        with pytest.raises(
            RustEmissionError, match="temporary cleanup failed"
        ) as caught:
            write_rust_transform(protected, _PROFILE, output)
    assert type(caught.value.__cause__) is OSError
    assert not output.exists()
    assert len(attempted) == 1
    attempted[0].unlink()


def test_writer_rejects_staged_bytes_modified_during_stream_close(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A successful text-stream close cannot certify rewritten Rust bytes."""
    _, _, _, protected = _fixture(tmp_path)
    output = tmp_path / "generated.rs"
    original_open = emit_rust_module._staged_output_open
    changed = False

    @contextmanager
    def change_staged_bytes_on_close(path: Path) -> Generator[IO[str]]:
        nonlocal changed
        with original_open(path) as stream:
            yield cast("IO[str]", stream)
        before = path.stat()
        content = path.read_bytes()
        _ = path.write_bytes(b"!" + content[1:])
        os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns))
        changed = True

    with monkeypatch.context() as patch:
        patch.setattr(
            emit_rust_module,
            "_staged_output_open",
            change_staged_bytes_on_close,
        )
        with pytest.raises(RustEmissionError, match="staged Rust source"):
            write_rust_transform(protected, _PROFILE, output)
    assert changed
    assert not output.exists()
    assert not list(tmp_path.glob(".generated.rs.*.tmp"))


@pytest.mark.parametrize("preexisting", [False, True])
def test_writer_rejects_forged_noop_publication(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, preexisting: bool
) -> None:
    """An unconsumed stage cannot pass even if old output matches exactly."""
    _, _, _, protected = _fixture(tmp_path)
    output = tmp_path / "generated.rs"
    if preexisting:
        _ = output.write_text(emit_rust_transform(protected, _PROFILE))
    attempted = False
    original_replace = emit_rust_module._output_replace

    def skip_replace(path: Path, target: Path) -> Path:
        nonlocal attempted
        if target == output:
            attempted = True
            return target
        return original_replace(path, target)

    monkeypatch.setattr(emit_rust_module, "_output_replace", skip_replace)
    with pytest.raises(RustEmissionError, match="published Rust source"):
        write_rust_transform(protected, _PROFILE, output)
    assert attempted
    assert output.exists() is preexisting
    assert not list(tmp_path.glob(".generated.rs.*.tmp"))


def test_writer_rejects_published_bytes_modified_during_replace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A post-rename mutation must not be reported as successful emission."""
    _, _, _, protected = _fixture(tmp_path)
    output = tmp_path / "generated.rs"
    original_replace = emit_rust_module._output_replace
    modified = False

    def tamper_with_published(path: Path, target: Path) -> Path:
        nonlocal modified
        result = original_replace(path, target)
        if target == output:
            content = target.read_bytes()
            _ = target.write_bytes(b"!" + content[1:])
            modified = True
        return result

    monkeypatch.setattr(
        emit_rust_module, "_output_replace", tamper_with_published
    )
    with pytest.raises(RustEmissionError, match="published Rust source"):
        write_rust_transform(protected, _PROFILE, output)
    assert modified
    assert output.is_file()
    assert not list(tmp_path.glob(".generated.rs.*.tmp"))


def test_writer_preserves_legacy_fixed_temporary_file(tmp_path: Path) -> None:
    """A stale legacy temp cannot be deleted by a new Rust emission."""
    _, _, _, protected = _fixture(tmp_path)
    output = tmp_path / "generated" / "transform.rs"
    output.parent.mkdir(parents=True)
    legacy = output.with_name(f".{output.name}.temp")
    _ = legacy.write_bytes(_LEGACY_TEMP)

    write_rust_transform(protected, _PROFILE, output)

    assert output.read_text(encoding="utf-8")
    assert legacy.read_bytes() == _LEGACY_TEMP


def test_writer_preserves_unowned_token_collision(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Exclusive temp claim failure cannot delete another writer's file."""
    _, _, _, protected = _fixture(tmp_path)
    output = tmp_path / "generated" / "transform.rs"
    output.parent.mkdir(parents=True)
    temporary = output.with_name(f".{output.name}.{_TEMP_COLLISION_ID}.tmp")
    _ = temporary.write_bytes(_FOREIGN_TEMP)

    def fixed_temporary_id(_: int | None = None) -> str:
        return _TEMP_COLLISION_ID

    monkeypatch.setattr(
        emit_rust_module,
        "token_hex",
        fixed_temporary_id,
    )

    with pytest.raises(RustEmissionError, match="publication failed"):
        write_rust_transform(protected, _PROFILE, output)

    assert temporary.read_bytes() == _FOREIGN_TEMP
    assert not output.exists()


def test_emitted_rust_rejects_wrong_source_before_output(
    tmp_path: Path,
) -> None:
    """Fail closed when the exact authoring source snapshot changes."""
    source, _, _, protected = _fixture(tmp_path)
    rust_source = tmp_path / "wrong.rs"
    executable = tmp_path / "wrong.exe"
    output = tmp_path / "wrong-out"
    _ = rust_source.write_text(
        emit_rust_transform(protected, _PROFILE),
        encoding="utf-8",
        newline="\n",
    )
    compiled = _compile(rust_source, executable)
    _expect(compiled.returncode == 0, "wrong-source fixture did not compile")
    _write(source, "extra.bin", b"unrelated source mutation")

    completed = _run(executable, source, output)

    _expect(completed.returncode != 0, "wrong exact source was admitted")
    _expect(not output.exists(), "wrong-source output was published")


@pytest.mark.parametrize("root_spelling", ["direct", "dot", "trailing-slash"])
def test_emitted_rust_rejects_linked_source_root(
    tmp_path: Path, root_spelling: str
) -> None:
    """Runtime source admission must reject linked roots and path aliases."""
    source, _, _, protected = _fixture(tmp_path)
    baseline = snapshot_tree(source)
    linked_source = tmp_path / "linked-source"
    try:
        linked_source.symlink_to(source, target_is_directory=True)
    except OSError:
        pytest.skip("directory symlinks unavailable")
    rust_source = tmp_path / "linked-source.rs"
    executable = tmp_path / "linked-source.exe"
    output = tmp_path / "linked-source-out"
    _ = rust_source.write_text(
        emit_rust_transform(protected, _PROFILE),
        encoding="utf-8",
        newline="\n",
    )
    compiled = _compile(rust_source, executable)
    _expect(compiled.returncode == 0, "linked-source fixture did not compile")

    source_arg = (
        linked_source
        if root_spelling == "direct"
        else f"{linked_source}/" + ("." if root_spelling == "dot" else "")
    )
    completed = _run(executable, source_arg, output)

    _expect(completed.returncode != 0, "linked source root was admitted")
    _expect(
        b"tree root must not be linked" in completed.stderr,
        "linked root failed without the no-follow admission diagnosis",
    )
    _expect(not output.exists(), "linked-root output was published")
    _expect(snapshot_tree(source) == baseline, "linked-root source was modified")


@pytest.mark.parametrize("root_spelling", ["dot", "trailing-slash"])
def test_emitted_rust_accepts_real_source_root_with_lexical_suffix(
    tmp_path: Path, root_spelling: str
) -> None:
    """No-follow admission must preserve ordinary directory path spellings."""
    source, oracle, _, protected = _fixture(tmp_path)
    baseline = snapshot_tree(source)
    rust_source = tmp_path / "real-source-alias.rs"
    executable = tmp_path / "real-source-alias.exe"
    output = tmp_path / "real-source-alias-out"
    _ = rust_source.write_text(
        emit_rust_transform(protected, _PROFILE),
        encoding="utf-8",
        newline="\n",
    )
    compiled = _compile(rust_source, executable)
    _expect(compiled.returncode == 0, "real-source fixture did not compile")
    source_arg = f"{source}/" + ("." if root_spelling == "dot" else "")

    completed = _run(executable, source_arg, output)

    _expect(
        completed.returncode == 0,
        "valid source spelling was rejected: "
        + completed.stderr.decode(errors="replace"),
    )
    _expect(snapshot_tree(output) == snapshot_tree(oracle), "target mismatch")
    _expect(snapshot_tree(source) == baseline, "source was modified")


@pytest.mark.parametrize("linked_parent", [False, True])
def test_emitted_rust_does_not_publish_inside_candidate_source(
    tmp_path: Path,
    *,
    linked_parent: bool,
) -> None:
    """Source input must remain unchanged even if output is its descendant."""
    source, _, _, protected = _fixture(tmp_path)
    before = snapshot_tree(source)
    rust_source = tmp_path / "source-boundary.rs"
    executable = tmp_path / "source-boundary.exe"
    parent = source
    if linked_parent:
        parent = tmp_path / "source-link"
        try:
            parent.symlink_to(source, target_is_directory=True)
        except OSError:
            pytest.skip("directory symlinks unavailable")
    output = parent / "nested" / "result"
    _ = rust_source.write_text(
        emit_rust_transform(protected, _PROFILE),
        encoding="utf-8",
        newline="\n",
    )
    compiled = _compile(rust_source, executable)
    _expect(compiled.returncode == 0, "source-boundary fixture did not compile")

    completed = _run(executable, source, output)

    _expect(completed.returncode != 0, "output inside source was admitted")
    _expect(snapshot_tree(source) == before, "runtime mutated its source tree")
    _expect(not output.exists(), "runtime published output under source")


def test_emitted_rust_accepts_bare_relative_output_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A simple relative output name must not require a named parent."""
    source, oracle, _, protected = _fixture(tmp_path)
    rust_source = tmp_path / "relative-output.rs"
    executable = tmp_path / "relative-output.exe"
    _ = rust_source.write_text(
        emit_rust_transform(protected, _PROFILE),
        encoding="utf-8",
        newline="\n",
    )
    compiled = _compile(rust_source, executable)
    _expect(compiled.returncode == 0, "relative-output fixture did not compile")
    monkeypatch.chdir(tmp_path)

    completed = _run(executable, source, Path("relative-out"))

    _expect(
        completed.returncode == 0,
        "bare relative output failed: "
        + completed.stderr.decode(errors="replace"),
    )
    _expect(
        snapshot_tree(tmp_path / "relative-out") == snapshot_tree(oracle),
        "relative generated output differs from oracle",
    )


def test_emitted_rust_rejects_relative_output_inside_source(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The source containment guard must resolve relative CLI destinations."""
    source, _, _, protected = _fixture(tmp_path)
    before = snapshot_tree(source)
    rust_source = tmp_path / "relative-source-boundary.rs"
    executable = tmp_path / "relative-source-boundary.exe"
    _ = rust_source.write_text(
        emit_rust_transform(protected, _PROFILE),
        encoding="utf-8",
        newline="\n",
    )
    compiled = _compile(rust_source, executable)
    _expect(
        compiled.returncode == 0,
        "relative boundary fixture did not compile",
    )
    monkeypatch.chdir(source)

    completed = _run(executable, source, Path("relative-out"))

    _expect(completed.returncode != 0, "relative output inside source admitted")
    _expect(snapshot_tree(source) == before, "relative output mutated source")
    _expect(not (source / "relative-out").exists(), "relative output published")


def test_emitted_rust_rejects_existing_output_root(tmp_path: Path) -> None:
    """Never merge a generated result into an existing output tree."""
    source, _, _, protected = _fixture(tmp_path)
    rust_source = tmp_path / "existing.rs"
    executable = tmp_path / "existing.exe"
    output = tmp_path / "existing-out"
    output.mkdir()
    _write(output, "sentinel.txt", _SENTINEL)
    _ = rust_source.write_text(
        emit_rust_transform(protected, _PROFILE),
        encoding="utf-8",
        newline="\n",
    )
    compiled = _compile(rust_source, executable)
    _expect(compiled.returncode == 0, "existing-output fixture did not compile")

    completed = _run(executable, source, output)

    _expect(completed.returncode != 0, "existing output root was overwritten")
    _expect(
        (output / "sentinel.txt").read_bytes() == _SENTINEL, "output mutated"
    )


def test_emitted_rust_preserves_dynamic_passthrough_root(
    tmp_path: Path,
) -> None:
    """Keep external runtime input outside the exact static source snapshot."""
    source, _, _, protected = _fixture(tmp_path)
    rust_source = tmp_path / "passthrough.rs"
    executable = tmp_path / "passthrough.exe"
    output = tmp_path / "passthrough-out"
    _ = rust_source.write_text(
        emit_rust_transform(protected, _PROFILE),
        encoding="utf-8",
        newline="\n",
    )
    compiled = _compile(rust_source, executable)
    _expect(compiled.returncode == 0, "passthrough fixture did not compile")
    _write(source, "external/game.bin", _PASSTHROUGH_RUNTIME)
    _write(source, "external/extra.bin", b"extra-runtime-input")

    completed = _run(executable, source, output)

    _expect(completed.returncode == 0, "passthrough runtime rejected input")
    _expect(
        (output / "external/game.bin").read_bytes() == _PASSTHROUGH_RUNTIME,
        "generated runtime pinned passthrough bytes",
    )
    _expect(
        (output / "external/extra.bin").is_file(),
        "generated runtime lost passthrough-only file",
    )


def test_writer_ignores_late_path_open_redirect(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A replaced Path.open cannot write the staged Rust source elsewhere."""
    _, _, _, protected = _fixture(tmp_path)
    output = tmp_path / "generated.rs"
    unrelated = tmp_path / "unrelated.rs"
    _ = unrelated.write_bytes(_SENTINEL)
    original_open = Path.open
    intercepted = 0

    def redirected_open(
        path: Path,
        mode: str = "r",
        *,
        encoding: str | None = None,
        newline: str | None = None,
    ) -> IO[str]:
        nonlocal intercepted
        if mode == _EXCLUSIVE_CREATE_MODE:
            intercepted += 1
            return cast(
                "IO[str]",
                original_open(
                    unrelated, "w", encoding=encoding, newline=newline
                ),
            )
        return cast(
            "IO[str]",
            original_open(path, mode, encoding=encoding, newline=newline),
        )

    with monkeypatch.context() as patch:
        patch.setattr(Path, "open", redirected_open)
        write_rust_transform(protected, _PROFILE, output)
    assert intercepted == 0
    assert unrelated.read_bytes() == _SENTINEL
    assert output.read_text(encoding="utf-8") == emit_rust_transform(
        protected, _PROFILE
    )


def test_writer_ignores_late_path_replace_redirect(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A replaced Path.replace cannot publish to an unrelated file."""
    _, _, _, protected = _fixture(tmp_path)
    output = tmp_path / "generated.rs"
    unrelated = tmp_path / "unrelated.rs"
    _ = unrelated.write_bytes(_SENTINEL)
    original_replace = Path.replace
    intercepted = 0

    def redirected_replace(path: Path, target: Path) -> Path:
        nonlocal intercepted
        if target == output:
            intercepted += 1
            return original_replace(path, unrelated)
        return original_replace(path, target)

    with monkeypatch.context() as patch:
        patch.setattr(Path, "replace", redirected_replace)
        write_rust_transform(protected, _PROFILE, output)
    assert intercepted == 0
    assert unrelated.read_bytes() == _SENTINEL
    assert output.read_text(encoding="utf-8") == emit_rust_transform(
        protected, _PROFILE
    )


def test_writer_ignores_late_path_mkdir_redirect(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A class-level mkdir hook cannot create parents outside the output."""
    _, _, _, protected = _fixture(tmp_path)
    output = tmp_path / "generated" / "main.rs"
    unrelated = tmp_path / "redirected"
    original_mkdir = Path.mkdir
    intercepted = 0

    def redirected_mkdir(
        path: Path,
        mode: int = 0o777,
        *,
        parents: bool = False,
        exist_ok: bool = False,
    ) -> None:
        nonlocal intercepted
        if path == output.parent:
            intercepted += 1
            original_mkdir(unrelated, mode=mode, parents=True, exist_ok=True)
            return
        original_mkdir(path, mode=mode, parents=parents, exist_ok=exist_ok)

    with monkeypatch.context() as patch:
        patch.setattr(Path, "mkdir", redirected_mkdir)
        write_rust_transform(protected, _PROFILE, output)
    assert intercepted == 0
    assert not unrelated.exists()
    assert output.read_text(encoding="utf-8") == emit_rust_transform(
        protected, _PROFILE
    )


def test_writer_ignores_late_path_unlink_redirect_on_cleanup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Failed publication cannot delete an unrelated file via Path.unlink."""
    _, _, _, protected = _fixture(tmp_path)
    output = tmp_path / "generated.rs"
    unrelated = tmp_path / "important.bin"
    _ = unrelated.write_bytes(_SENTINEL)
    original_unlink = Path.unlink
    intercepted = 0

    def redirected_unlink(path: Path, *, missing_ok: bool = False) -> None:
        nonlocal intercepted
        if path.name.startswith(".generated.rs."):
            intercepted += 1
            original_unlink(unrelated)
            return
        original_unlink(path, missing_ok=missing_ok)

    def reject_publication(_source: Path, _destination: Path) -> Path:
        message = "injected publication failure"
        raise OSError(message)

    with monkeypatch.context() as patch:
        patch.setattr(Path, "unlink", redirected_unlink)
        patch.setattr(emit_rust_module, "_output_replace", reject_publication)
        with pytest.raises(RustEmissionError, match="publication failed"):
            write_rust_transform(protected, _PROFILE, output)
    assert intercepted == 0
    assert unrelated.read_bytes() == _SENTINEL
    assert not output.exists()
    assert not list(tmp_path.glob(".generated.rs.*.tmp"))


def test_writer_ignores_late_os_mkdir_redirect(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A late os.mkdir hook cannot redirect recursive output setup."""
    _, _, _, protected = _fixture(tmp_path)
    output = tmp_path / "generated" / "nested" / "main.rs"
    unrelated = tmp_path / "redirected"
    original_mkdir = os.mkdir
    intercepted = 0

    def redirected_mkdir(
        path: str | bytes | os.PathLike[str] | os.PathLike[bytes],
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> None:
        nonlocal intercepted
        if os.fspath(path) == str(output.parent):
            intercepted += 1
            original_mkdir(unrelated, mode)
            return
        original_mkdir(path, mode, dir_fd=dir_fd)

    with monkeypatch.context() as patch:
        patch.setattr(os, "mkdir", redirected_mkdir)
        write_rust_transform(protected, _PROFILE, output)
    assert intercepted == 0
    assert not unrelated.exists()
    assert output.read_text(encoding="utf-8") == emit_rust_transform(
        protected, _PROFILE
    )


def test_writer_ignores_late_temporary_with_name_redirect(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Stage creation must ignore late Path.with_name redirection."""
    _, _, _, protected = _fixture(tmp_path)
    output = tmp_path / "generated" / "main.rs"
    outside = tmp_path / "unexpected-stage.rs"
    original_with_name = Path.with_name
    intercepted = 0

    def forged_with_name(path: Path, name: str) -> Path:
        nonlocal intercepted
        if path == output and name.startswith(".main.rs."):
            intercepted += 1
            return outside
        return original_with_name(path, name)

    with monkeypatch.context() as patch:
        patch.setattr(Path, "with_name", forged_with_name)
        write_rust_transform(protected, _PROFILE, output)
    assert intercepted == 0
    assert not outside.exists()
    assert output.read_text(encoding="utf-8") == emit_rust_transform(
        protected, _PROFILE
    )


def test_writer_ignores_late_output_parent_redirect(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A mutated Path.parent cannot create an unrelated output directory."""
    _, _, _, protected = _fixture(tmp_path)
    output = tmp_path / "generated" / "main.rs"
    unrelated = tmp_path / "unexpected-parent"
    original_parent = Path.parent.fget
    assert original_parent is not None
    intercepted = 0

    def forged_parent(path: Path) -> Path:
        nonlocal intercepted
        if path == output:
            intercepted += 1
            return unrelated
        return original_parent(path)

    with monkeypatch.context() as patch:
        patch.setattr(Path, "parent", property(forged_parent))
        write_rust_transform(protected, _PROFILE, output)
    assert intercepted == 0
    assert not unrelated.exists()
    assert output.read_text(encoding="utf-8") == emit_rust_transform(
        protected, _PROFILE
    )


@pytest.mark.parametrize(
    "invalid",
    [
        "binding-threshold", "missing-target", "missing-payload",
        "invalid-context", "invalid-nonce", "foreign-source",
    ],
)
@pytest.mark.parametrize("write_to_disk", [False, True])
def test_rust_emitter_revalidates_exact_native_plan_before_template_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    invalid: str,
    write_to_disk: bool,
) -> None:
    """A constructor-bypassing native plan cannot emit unadmitted Rust bytes."""
    _, _, _, protected = _fixture(tmp_path)
    forged = object.__new__(type(protected))
    for name in (
        "source", "target", "instructions", "passthrough_roots",
        "context", "nonce", "payload", "binding",
    ):
        if invalid == "missing-target" and name == "target":
            continue
        if invalid == "missing-payload" and name == "payload":
            continue
        value = cast("object", getattr(protected, name))
        if invalid == "invalid-context" and name == "context":
            value = b""
        if invalid == "invalid-nonce" and name == "nonce":
            value = b""
        if invalid == "foreign-source" and name == "source":
            value = object()
        object.__setattr__(forged, name, value)
    if invalid == "binding-threshold":
        binding = protected.binding
        forged_binding = object.__new__(type(binding))
        for name in (
            "context", "threshold", "minimum_anchor_files", "secret_length",
            "secret_commitment", "anchor_policy", "shares",
        ):
            value = 0 if name == "threshold" else getattr(binding, name)
            object.__setattr__(forged_binding, name, value)
        object.__setattr__(forged, "binding", forged_binding)
    output = tmp_path / "untrusted.rs"
    called = 0

    def forbidden_template_read(_path: Path) -> str:
        nonlocal called
        called += 1
        raise AssertionError("unadmitted plan reached the runtime template")

    with monkeypatch.context() as patched:
        patched.setattr(emit_rust_module, "_NATIVE_TEMPLATE_READ", forbidden_template_read)
        with pytest.raises(RustEmissionError, match="plan"):
            if write_to_disk:
                write_rust_transform(forged, _PROFILE, output)
            else:
                _ = emit_rust_transform(forged, _PROFILE, output)
    assert called == 0
    assert not output.exists()


def test_rust_emitter_ignores_late_protected_plan_validator_override(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A patched class validator cannot hide malformed protected metadata."""
    _, _, _, protected = _fixture(tmp_path)
    forged = object.__new__(type(protected))
    for name in (
        "source", "target", "instructions", "passthrough_roots",
        "context", "nonce", "payload", "binding",
    ):
        object.__setattr__(forged, name, getattr(protected, name))
    object.__setattr__(forged, "nonce", b"too-short")
    calls = 0

    def accept_everything(_plan: object) -> None:
        nonlocal calls
        calls += 1

    with monkeypatch.context() as patched:
        patched.setattr(type(protected), "__post_init__", accept_everything)
        with pytest.raises(RustEmissionError, match="protected plan"):
            _ = emit_rust_transform(forged, _PROFILE)
        expected = emit_rust_transform(protected, _PROFILE)
    assert calls == 0
    assert "const NONCE_HEX" in expected
