# Copyright (c) 2026 Alberto Villa Osorno.
# SPDX-License-Identifier: MIT
"""Deterministic std-only Rust emission for protected exact transforms."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from algorithms.diff.protected import ProtectedMetadata
from algorithms.diff.protected import protected_plan_aad

if TYPE_CHECKING:
    from algorithms.diff.protected import ProtectedExactPlan
    from algorithms.diff.source_binding import ThresholdBinding

_RUNTIME_TEMPLATE = Path(__file__).with_name("rust_runtime.rs")
_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_OUTPUT_PATH = Path("generated/main.rs")
_BEGIN = "// BEGIN GENERATED CONSTANTS"
_END = "// END GENERATED CONSTANTS"
_HEX_CHUNK = 64


class RustEmissionError(ValueError):
    """Raised when protected metadata cannot be emitted deterministically."""


def _u64(value: int) -> bytes:
    if value < 0 or value >= (1 << 64):
        message = "Rust transform integer exceeds unsigned 64-bit framing"
        raise RustEmissionError(message)
    return value.to_bytes(8, byteorder="big")


def _frame(value: bytes) -> bytes:
    return _u64(len(value)) + value


def _binding_bytes(binding: ThresholdBinding) -> bytes:
    parts = [
        _frame(binding.context),
        _u64(binding.threshold),
        _u64(binding.minimum_anchor_files),
        _u64(binding.secret_length),
        _frame(binding.secret_commitment),
        _u64(binding.anchor_policy.window_bytes),
        _u64(binding.anchor_policy.selection_modulus),
        _u64(len(binding.shares)),
    ]
    for share in binding.shares:
        parts.extend((
            _frame(share.source_path.encode("utf-8")),
            _frame(share.anchor_digest),
            _u64(share.x),
            _frame(share.masked_share),
        ))
    return b"".join(parts)


def _rust_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=True)


def _hex_constant(name: str, data: bytes) -> str:
    encoded = data.hex()
    if not encoded:
        return f'const {name}: &str = "";'
    chunks = [
        encoded[offset : offset + _HEX_CHUNK]
        for offset in range(0, len(encoded), _HEX_CHUNK)
    ]
    if len(chunks) == 1:
        return f'const {name}: &str = concat!("{chunks[0]}",);'
    lines = [f"const {name}: &str = concat!("]
    lines.extend(f'    "{chunk}",' for chunk in chunks)
    lines.append(");")
    return "\n".join(lines)


def _constants(plan: ProtectedExactPlan, profile: str) -> str:
    metadata = ProtectedMetadata(
        source=plan.source,
        target=plan.target,
        instructions=plan.instructions,
        passthrough_roots=plan.passthrough_roots,
    )
    aad = protected_plan_aad(metadata, context=plan.context)
    return "\n".join((
        _BEGIN,
        f"const PROFILE: &str = {_rust_string(profile)};",
        _hex_constant("AAD_HEX", aad),
        _hex_constant("BINDING_HEX", _binding_bytes(plan.binding)),
        _hex_constant("NONCE_HEX", plan.nonce),
        _hex_constant("CIPHERTEXT_HEX", plan.payload.ciphertext),
        _hex_constant("TAG_HEX", plan.payload.tag),
        _END,
    ))


def _display_path(output_path: Path) -> str:
    if not output_path.is_absolute():
        return output_path.as_posix()
    try:
        return output_path.resolve().relative_to(_REPOSITORY_ROOT).as_posix()
    except ValueError:
        return output_path.name


def _generated_header(output_path: Path) -> str:
    display_path = _display_path(output_path)
    return "\n".join((
        "// File:",
        f"//   - {Path(display_path).name}",
        "// Path:",
        f"//   - {display_path}",
        "//",
        "// Copyright:",
        "//   - Copyright (c) 2026 Alberto Villa Osorno.",
        "// SPDX-License-Identifier:",
        "//   - MIT",
        "// Confidential:",
        "//   - false",
        "// License-File:",
        "//   - LICENSE",
        "// Path-Rule:",
        "//   - All paths in this header are repository-root relative.",
        "//",
        "// Boundary-Contract:",
        "// - Owns:",
        "//   - One generated exact source-bound transformation.",
        "// - Must-Not:",
        "//   - Materialize target bytes without admitted source evidence.",
        "//   - Be hand-edited; regenerate it through the owning recipe.",
        "// - Allows:",
        "//   - Inputs: one admitted source tree and output directory.",
        "//   - Outputs: one authenticated deterministic target tree.",
        "//   - Side effects: transactional target publication.",
        "// - Split-When:",
        "//   - Split when another transform has a distinct source contract.",
        "// - Merge-When:",
        "//   - Merge only when source identity and target semantics match.",
        "// - Summary:",
        "//   - Generated standalone source-bound exact transform.",
        "// - Description:",
        "//   - Recovers protected target bytes from admitted source evidence.",
        "// - Usage:",
        "//   - `<transform> <source-root> <output-root>`.",
        "// - Defaults:",
        "//   - Fails closed before publishing mismatched or partial output.",
        "//",
        "// Related documents:",
        "// - algorithms/diff/README.md",
        "// - docs/technical/tooling/source-bound-diff-generator.md",
        "//",
        "// Large file:",
        "//   - true",
        "",
        "",
    ))


def emit_rust_transform(
    plan: ProtectedExactPlan,
    profile: str,
    output_path: Path = _DEFAULT_OUTPUT_PATH,
) -> str:
    """Render one standalone Rust exact-transform source file.

    Returns:
        Deterministic UTF-8 Rust source with protected metadata embedded as hex.

    Raises:
        RustEmissionError: Profile/template state is invalid.

    """
    if not profile:
        message = "Rust transform profile must be non-empty"
        raise RustEmissionError(message)
    template = _RUNTIME_TEMPLATE.read_text(encoding="utf-8")
    start = template.find(_BEGIN)
    end = template.find(_END)
    if start < 0 or end < start:
        message = "Rust runtime template lost generated-constant markers"
        raise RustEmissionError(message)
    end += len(_END)
    body = template[:start] + _constants(plan, profile) + template[end:]
    rendered = _generated_header(output_path) + body
    return rendered.replace("\r\n", "\n")


def write_rust_transform(
    plan: ProtectedExactPlan,
    profile: str,
    output_path: Path,
) -> None:
    """Write one generated transform atomically."""
    source = emit_rust_transform(plan, profile, output_path)
    parent = output_path.parent
    parent.mkdir(parents=True, exist_ok=True)
    temporary = output_path.with_name(f".{output_path.name}.temp")
    if temporary.exists():
        temporary.unlink()
    temporary.write_text(source, encoding="utf-8", newline="\n")
    temporary.replace(output_path)
