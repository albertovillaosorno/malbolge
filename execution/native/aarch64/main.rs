// File:
//   - main.rs
// Path:
//   - execution/native/aarch64/main.rs
//
// Copyright:
//   - Copyright (c) 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - MIT
// Confidential:
//   - false
// License-File:
//   - LICENSE
// Path-Rule:
//   - All paths in this header are repository-root relative.
//
// Boundary-Contract:
// - Owns:
//   - Canonical reviewed AArch64 instruction-byte templates for direct native
//   - IR.
// - Must-Not:
//   - Decide IR eligibility, admit artifacts, or define guest semantics.
// - Allows:
//   - Inputs: already selected immediate register values.
//   - Outputs: deterministic AArch64 `.text` byte sequences.
//   - Side effects: process-local allocation only.
// - Split-When:
//   - Split when register allocation/general instruction selection is
//   - introduced.
// - Merge-When:
//   - Merge when one reviewed ISA encoder owns all AArch64 native templates.
// - Summary:
//   - Encodes the currently reviewed direct AArch64 template family.
// - Description:
//   - Supplies bytes only; semantic admission remains in
//   - `execution/native/direct.rs`.
// - Usage:
//   - Called by direct native object generation after exact IR-shape selection.
// - Defaults:
//   - No instruction sequence is selected implicitly by this module.
//
// Related documents:
// - docs/technical/runtime/execution/native-x86-64-and-aarch64-backends.md
//
// Large file:
//   - false
//

//! Reviewed `AArch64` instruction templates for direct native execution.

/// Returns the canonical no-state-change guard-miss stub.
#[must_use]
pub(super) const fn deopt_code() -> &'static [u8] {
    &[0x20, 0x00, 0x80, 0x52, 0xc0, 0x03, 0x5f, 0xd6]
}

/// Encodes exact-register one-step halt preflight and commit.
#[must_use]
pub(super) fn halt_registers_code(
    accumulator: u32,
    code_pointer: u32,
    data_pointer: u32,
) -> Vec<u8> {
    let words = [
        0xb400_0360,
        0xf940_1008,
        0xb500_0328,
        0xf940_1c08,
        0xb500_02e8,
        0xb940_4008,
        movz_w9(accumulator),
        movk_w9_high(accumulator),
        0x6b09_011f,
        0x5400_0241,
        0xb940_4408,
        movz_w9(code_pointer),
        movk_w9_high(code_pointer),
        0x6b09_011f,
        0x5400_01a1,
        0xb940_4808,
        movz_w9(data_pointer),
        movk_w9_high(data_pointer),
        0x6b09_011f,
        0x5400_0101,
        0x3941_3009,
        0xaa00_03e8,
        0x5280_0020,
        0x3500_0069,
        0x3901_3100,
        0x2a1f_03e0,
        0xd65f_03c0,
        0x5280_0020,
        0xd65f_03c0,
    ];
    encode_words(&words)
}

/// Returns the canonical zero-register specialization of halt preflight/commit.
#[must_use]
pub(super) const fn initial_halt_code() -> &'static [u8] {
    &[
        0x60, 0x01, 0x00, 0xb4, 0x08, 0x10, 0x40, 0xf9, 0x28, 0x01, 0x00, 0xb5,
        0x08, 0x1c, 0x40, 0xf9, 0xe8, 0x00, 0x00, 0xb5, 0x08, 0x40, 0x40, 0xb9,
        0xa8, 0x00, 0x00, 0x35, 0x08, 0x44, 0x40, 0xb9, 0x68, 0x00, 0x00, 0x35,
        0x08, 0x48, 0x40, 0xb9, 0x68, 0x00, 0x00, 0x34, 0x20, 0x00, 0x80, 0x52,
        0xc0, 0x03, 0x5f, 0xd6, 0x09, 0x30, 0x41, 0x39, 0xe8, 0x03, 0x00, 0xaa,
        0x20, 0x00, 0x80, 0x52, 0x69, 0x00, 0x00, 0x35, 0x00, 0x31, 0x01, 0x39,
        0xe0, 0x03, 0x1f, 0x2a, 0xc0, 0x03, 0x5f, 0xd6,
    ]
}

fn encode_words(words: &[u32]) -> Vec<u8> {
    let mut bytes = Vec::with_capacity(words.len().saturating_mul(4));
    for word in words {
        bytes.extend_from_slice(&word.to_le_bytes());
    }
    bytes
}

const fn movk_w9_high(value: u32) -> u32 {
    let immediate = (value >> 16u32) & 0xffff;
    0x72a0_0009 | (immediate << 5)
}

const fn movz_w9(value: u32) -> u32 {
    let immediate = value & 0xffff;
    0x5280_0009 | (immediate << 5)
}
