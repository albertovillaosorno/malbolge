// File:
//   - main.rs
// Path:
//   - execution/native/x86_64/main.rs
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
//   - Canonical reviewed x86-64 instruction-byte templates for direct native
//     IR.
// - Must-Not:
//   - Decide IR eligibility, admit artifacts, or define guest semantics.
// - Allows:
//   - Inputs: already selected immediate register values.
//   - Outputs: deterministic x86-64 `.text` byte sequences.
//   - Side effects: process-local allocation only.
// - Split-When:
//   - Split when register allocation/general instruction selection is
//     introduced.
// - Merge-When:
//   - Merge when one reviewed ISA encoder owns all x86-64 native templates.
// - Summary:
//   - Encodes the currently reviewed direct x86-64 template family.
// - Description:
//   - Supplies bytes only; semantic admission remains in
//     `execution/native/direct.rs`.
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

//! Reviewed x86-64 instruction templates for direct native execution.

/// Returns the canonical no-state-change guard-miss stub.
#[must_use]
pub(super) const fn deopt_code() -> &'static [u8] {
    &[0xb8, 0x01, 0x00, 0x00, 0x00, 0xc3]
}

/// Encodes exact-register one-step halt preflight and commit.
#[must_use]
pub(super) fn halt_registers_code(
    accumulator: u32,
    code_pointer: u32,
    data_pointer: u32,
) -> Vec<u8> {
    let mut code = Vec::with_capacity(65);
    code.extend_from_slice(&[
        0xb8, 0x01, 0x00, 0x00, 0x00, 0x48, 0x85, 0xc9, 0x74, 0x07, 0x48, 0x83,
        0x79, 0x20, 0x00, 0x74, 0x01, 0xc3, 0x48, 0x83, 0x79, 0x38, 0x00, 0x75,
        0xf8, 0x81, 0x79, 0x40,
    ]);
    code.extend_from_slice(&accumulator.to_le_bytes());
    code.extend_from_slice(&[0x75, 0xef, 0x81, 0x79, 0x44]);
    code.extend_from_slice(&code_pointer.to_le_bytes());
    code.extend_from_slice(&[0x75, 0xe6, 0x81, 0x79, 0x48]);
    code.extend_from_slice(&data_pointer.to_le_bytes());
    code.extend_from_slice(&[
        0x75, 0xdd, 0x80, 0x79, 0x4c, 0x00, 0x75, 0xd7, 0xc6, 0x41, 0x4c, 0x01,
        0x31, 0xc0, 0xc3,
    ]);
    code
}

/// Returns the canonical zero-register specialization of halt preflight/commit.
#[must_use]
pub(super) const fn initial_halt_code() -> &'static [u8] {
    &[
        0xb8, 0x01, 0x00, 0x00, 0x00, 0x48, 0x85, 0xc9, 0x74, 0x07, 0x48, 0x83,
        0x79, 0x20, 0x00, 0x74, 0x01, 0xc3, 0x48, 0x83, 0x79, 0x38, 0x00, 0x75,
        0xf8, 0x83, 0x79, 0x40, 0x00, 0x75, 0xf2, 0x83, 0x79, 0x44, 0x00, 0x75,
        0xec, 0x83, 0x79, 0x48, 0x00, 0x75, 0xe6, 0x80, 0x79, 0x4c, 0x00, 0x75,
        0xe0, 0xc6, 0x41, 0x4c, 0x01, 0x31, 0xc0, 0xc3,
    ]
}
