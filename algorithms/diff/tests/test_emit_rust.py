# Copyright (c) 2026 Alberto Villa Osorno.
# SPDX-License-Identifier: MIT
"""Synthetic compile-and-run tests for emitted std-only Rust transforms."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import shutil
import subprocess  # ruff: ignore[suspicious-subprocess-import] - fixed local compiler/executable argv; shell disabled.
from typing import TYPE_CHECKING

import pytest

from algorithms.diff.admission import identity_tree
from algorithms.diff.emit_rust import emit_rust_transform
from algorithms.diff.exact import build_exact_plan
from algorithms.diff.exact import snapshot_tree
from algorithms.diff.fingerprints import AnchorPolicy
from algorithms.diff.protected import protect_exact_plan
from algorithms.diff.source_binding import SourceBindingPolicy

if TYPE_CHECKING:
    from algorithms.diff.protected import ProtectedExactPlan

_CONTEXT = b"synthetic-rust-emitter-v1"
_PROFILE = "synthetic-rust-emitter-v1"
_BLOCK_COUNT = 48
_RUSTC_ENV = "MALBOLGE_RUSTC"
_TARGET_ONLY_TEXT = "TARGET-ONLY"
_NEW_TARGET_TEXT = "new-target-only"
_STD_MARKER = "use std::"
_SENTINEL = b"preserve"
_PASSTHROUGH_AUTHORING = b"authoring-external"
_PASSTHROUGH_RUNTIME = b"runtime-external"
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
    path.write_bytes(data)


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
    located = configured or shutil.which("rustc")
    if located is None:
        pytest.skip("repository-pinned rustc is unavailable")
    path = Path(located)
    if not path.is_file():
        pytest.skip("configured rustc path is unavailable")
    return path


def _compile(
    rust_source: Path, executable: Path
) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(  # ruff: ignore[subprocess-without-shell-equals-true] - explicit rustc argv; no shell.
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
) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(  # ruff: ignore[subprocess-without-shell-equals-true] - generated executable argv; no shell.
        [str(executable), str(source), str(output)],
        check=False,
        capture_output=True,
        shell=False,
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


def test_emitted_rust_compiles_and_materializes_exact_tree(
    tmp_path: Path,
) -> None:
    """Compile emitted Rust and reconstruct the exact synthetic target."""
    source, oracle, _, protected = _fixture(tmp_path)
    rust_source = tmp_path / "generated.rs"
    executable = tmp_path / "transform.exe"
    output = tmp_path / "out"
    rust_source.write_text(
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


def test_emitted_rust_rejects_wrong_source_before_output(
    tmp_path: Path,
) -> None:
    """Fail closed when the exact authoring source snapshot changes."""
    source, _, _, protected = _fixture(tmp_path)
    rust_source = tmp_path / "wrong.rs"
    executable = tmp_path / "wrong.exe"
    output = tmp_path / "wrong-out"
    rust_source.write_text(
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
    rust_source.write_text(
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
    rust_source.write_text(
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
