# Copyright:
#   - Copyright (c) 2026 Alberto Villa Osorno.
# SPDX-License-Identifier:
#   - MIT
# Confidential:
#   - false
# License-File:
#   - LICENSE-MIT
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

import hashlib
import os
from pathlib import Path
import shutil

# Used only with fixed local argv and shell=False.
import subprocess as sp  # ruff: ignore[suspicious-subprocess-import]
from typing import TYPE_CHECKING
from typing import cast

from algorithms.diff import emit_rust as emit_rust_module
from algorithms.diff.admission import identity_tree
from algorithms.diff.emit_rust import RustEmissionError
from algorithms.diff.emit_rust import emit_rust_transform
from algorithms.diff.emit_rust import write_rust_transform
from algorithms.diff.exact import build_exact_plan
from algorithms.diff.exact import snapshot_tree
from algorithms.diff.fingerprints import AnchorPolicy
from algorithms.diff.protected import protect_exact_plan
from algorithms.diff.source_binding import SourceBindingPolicy
import pytest

if TYPE_CHECKING:
    from algorithms.diff.protected import ProtectedExactPlan

_CONTEXT = b"synthetic-rust-emitter-v1"
_PROFILE = "synthetic-rust-emitter-v1"
_BLOCK_COUNT = 48
_RUSTC_ENV = "MALBOLGE_RUSTC"
_PINNED_RUSTC = (
    Path(__file__).resolve().parents[5]
    / ".dependencies/jig/source/.dependencies/rust"
    / "stable-1.97.1-x86_64-pc-windows-gnu/bin/rustc.exe"
)
_TARGET_ONLY_TEXT = "TARGET-ONLY"
_NEW_TARGET_TEXT = "new-target-only"
_STD_MARKER = "use std::"
_SENTINEL = b"preserve"
_PASSTHROUGH_AUTHORING = b"authoring-external"
_PASSTHROUGH_RUNTIME = b"runtime-external"
_MAX_GENERATED_LINE_LENGTH = 80
_GENERATED_PATH = "generated/main.rs"
_RUNTIME_TEMPLATE_NAME = "rust_runtime.rs"
_BOUNDARY_HEADER = "// Boundary-Contract:"
_LARGE_FILE_HEADER = "// Large file:\n//   - true"
_LEGACY_TEMP = b"legacy-temp"
_FOREIGN_TEMP = b"foreign-temp"
_LINK_TARGET = b"link-target"
_TEMP_COLLISION_ID = "collision-id"
_SINGLE_CHUNK_NONCE_MARKER = (
    'const NONCE_HEX: &str = concat!("000000000000000000000000",);'
)


def _expect(condition: object, message: str) -> None:
    if not condition:
        raise AssertionError(message)


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
    source: Path,
    output: Path,
) -> sp.CompletedProcess[bytes]:
    # Generated executable plus explicit paths; no shell interpolation.
    return sp.run(  # ruff: ignore[subprocess-without-shell-equals-true]
        [str(executable), str(source), str(output)],
        check=False,
        capture_output=True,
        shell=False,
    )


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
    _expect(first.startswith("// File:\n//   - main.rs\n"), "header missing")
    _expect(
        f"//   - {_GENERATED_PATH}" in first,
        "generated header path is incorrect",
    )
    _expect(_BOUNDARY_HEADER in first, "boundary header missing")
    _expect(_LARGE_FILE_HEADER in first, "large-file flag missing")
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


def test_emitter_wraps_runtime_template_read_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Template I/O failures remain inside RustEmissionError."""
    _, _, _, protected = _fixture(tmp_path)
    original_read = Path.read_text

    def fail_template_read(
        path: Path,
        *,
        encoding: str | None = None,
        errors: str | None = None,
        newline: str | None = None,
    ) -> str:
        if path.name == _RUNTIME_TEMPLATE_NAME:
            message = "blocked runtime template"
            raise PermissionError(message)
        return original_read(
            path,
            encoding=encoding,
            errors=errors,
            newline=newline,
        )

    monkeypatch.setattr(Path, "read_text", fail_template_read)
    with pytest.raises(RustEmissionError, match="runtime template read failed"):
        _ = emit_rust_transform(protected, _PROFILE)


def test_emitter_wraps_absolute_display_path_resolution_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Header path rendering cannot leak a host resolution exception."""
    _, _, _, protected = _fixture(tmp_path)
    output = tmp_path / "generated" / "transform.rs"
    original_resolve = Path.resolve

    def fail_resolve(path: Path, *, strict: bool = False) -> Path:
        if path == output:
            message = "blocked generated display path"
            raise PermissionError(message)
        return original_resolve(path, strict=strict)

    monkeypatch.setattr(Path, "resolve", fail_resolve)
    with pytest.raises(
        RustEmissionError, match="display path resolution failed"
    ):
        _ = emit_rust_transform(protected, _PROFILE, output)


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


def test_writer_rejects_directory_output(tmp_path: Path) -> None:
    """An existing output directory cannot be replaced as a generated file."""
    _, _, _, protected = _fixture(tmp_path)
    output = tmp_path / "generated.rs"
    output.mkdir()

    with pytest.raises(RustEmissionError, match="regular non-linked file"):
        write_rust_transform(protected, _PROFILE, output)

    assert output.is_dir()


def test_writer_wraps_output_status_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An inaccessible output leaf stays inside RustEmissionError."""
    _, _, _, protected = _fixture(tmp_path)
    output = tmp_path / "generated.rs"
    original_lstat = Path.lstat

    def fail_lstat(path: Path) -> object:
        if path == output:
            message = "blocked Rust output status"
            raise PermissionError(message)
        return original_lstat(path)

    monkeypatch.setattr(Path, "lstat", fail_lstat)
    with pytest.raises(RustEmissionError, match="output file status failed"):
        write_rust_transform(protected, _PROFILE, output)


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
