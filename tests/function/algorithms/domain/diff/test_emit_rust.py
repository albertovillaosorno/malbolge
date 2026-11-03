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

from contextlib import contextmanager
import hashlib
import os
from pathlib import Path
import shutil

# Used only with fixed local argv and shell=False.
import subprocess as sp  # ruff: ignore[suspicious-subprocess-import]
from types import SimpleNamespace
from typing import TYPE_CHECKING
from typing import cast
from typing import override

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
    from collections.abc import Callable
    from collections.abc import Generator
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
_LOCATION_PARENT = "parent"
_SINGLE_CHUNK_NONCE_MARKER = (
    'const NONCE_HEX: &str = concat!("000000000000000000000000",);'
)
_INVALID_BINDING_MARKER = b"invalid generated binding"
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
            match=r"parent must not be linked|regular non-linked file",
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
    original_mkdir = Path.mkdir

    def fail_mkdir(
        path: Path,
        mode: int = 0o777,
        *,
        parents: bool = False,
        exist_ok: bool = False,
    ) -> None:
        if path == parent:
            message = "blocked Rust output parent creation"
            raise failure_type(message)
        original_mkdir(path, mode=mode, parents=parents, exist_ok=exist_ok)

    monkeypatch.setattr(Path, "mkdir", fail_mkdir)
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
    original_replace = Path.replace
    attempted: list[Path] = []

    def reject_replace(path: Path, target: Path) -> Path:
        if target == output:
            attempted.append(path)
            assert path.exists(), "fixture missed staged Rust source"
            message = "blocked Rust output publication"
            raise failure_type(message)
        return original_replace(path, target)

    monkeypatch.setattr(Path, "replace", reject_replace)
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
    original_open = Path.open
    wrote: list[str] = []

    @contextmanager
    def fail_after_open(
        path: Path,
        mode: str = "r",
        *,
        encoding: str | None = None,
        newline: str | None = None,
    ) -> Generator[IO[str] | _BrokenStagedRustWriter]:
        with original_open(
            path, mode, encoding=encoding, newline=newline
        ) as stream:
            if mode == _EXCLUSIVE_CREATE_MODE:
                yield _BrokenStagedRustWriter(
                    cast("IO[str]", stream), failure_type, wrote
                )
            else:
                yield cast("IO[str]", stream)

    monkeypatch.setattr(Path, "open", fail_after_open)
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
    original_open = Path.open

    @contextmanager
    def misreport_staged_write(
        path: Path,
        mode: str = "r",
        *,
        encoding: str | None = None,
        newline: str | None = None,
    ) -> Generator[IO[str] | _MisreportedStagedRustWriter]:
        with original_open(
            path, mode, encoding=encoding, newline=newline
        ) as stream:
            if mode == _EXCLUSIVE_CREATE_MODE:
                yield _MisreportedStagedRustWriter(
                    cast("IO[str]", stream), reported, partial=partial
                )
            else:
                yield cast("IO[str]", stream)

    monkeypatch.setattr(Path, "open", misreport_staged_write)
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
    original_unlink = Path.unlink
    original_replace = Path.replace
    attempted: list[Path] = []

    def reject_replace(path: Path, target: Path) -> Path:
        if target == output:
            attempted.append(path)
            message = "blocked atomic Rust output publication"
            raise RuntimeError(message)
        return original_replace(path, target)

    def reject_cleanup(path: Path, *, missing_ok: bool = False) -> None:
        if path in attempted:
            message = "injected cleanup failure"
            raise cleanup_error(message)
        original_unlink(path, missing_ok=missing_ok)

    with monkeypatch.context() as patch:
        patch.setattr(Path, "replace", reject_replace)
        patch.setattr(Path, "unlink", reject_cleanup)
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
    original_replace = Path.replace

    def fail_replace(path: Path, target: Path) -> Path:
        if target == output:
            raise failure
        return original_replace(path, target)

    monkeypatch.setattr(Path, "replace", fail_replace)
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
    original_replace = Path.replace
    original_unlink = Path.unlink
    attempted: list[Path] = []

    def fail_replace(path: Path, target: Path) -> Path:
        if target == output:
            attempted.append(path)
            message = "primary Rust rename failure"
            raise OSError(message)
        return original_replace(path, target)

    def fail_unlink(path: Path, *, missing_ok: bool = False) -> None:
        if path in attempted:
            message = "hostile Rust cleanup"
            raise _HostileEmissionError(message)
        original_unlink(path, missing_ok=missing_ok)

    with monkeypatch.context() as patch:
        patch.setattr(Path, "replace", fail_replace)
        patch.setattr(Path, "unlink", fail_unlink)
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
    original_open = Path.open
    changed = False

    @contextmanager
    def change_staged_bytes_on_close(
        path: Path,
        mode: str = "r",
        buffering: int = -1,
        *,
        encoding: str | None = None,
        errors: str | None = None,
        newline: str | None = None,
    ) -> Generator[IO[str]]:
        nonlocal changed
        with original_open(
            path,
            mode,
            buffering=buffering,
            encoding=encoding,
            errors=errors,
            newline=newline,
        ) as stream:
            yield cast("IO[str]", stream)
        if mode == _EXCLUSIVE_CREATE_MODE:
            before = path.stat()
            content = path.read_bytes()
            _ = path.write_bytes(b"!" + content[1:])
            os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns))
            changed = True

    with monkeypatch.context() as patch:
        patch.setattr(Path, "open", change_staged_bytes_on_close)
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
    original_replace = Path.replace

    def skip_replace(path: Path, target: Path) -> Path:
        nonlocal attempted
        if target == output:
            attempted = True
            return target
        return original_replace(path, target)

    monkeypatch.setattr(Path, "replace", skip_replace)
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
    original_replace = Path.replace
    modified = False

    def tamper_with_published(path: Path, target: Path) -> Path:
        nonlocal modified
        result = original_replace(path, target)
        if target == output:
            content = target.read_bytes()
            _ = target.write_bytes(b"!" + content[1:])
            modified = True
        return result

    monkeypatch.setattr(Path, "replace", tamper_with_published)
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
