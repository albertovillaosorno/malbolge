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
//   - IR.
// - Must-Not:
//   - Decide IR eligibility, admit artifacts, or define guest semantics.
// - Allows:
//   - Inputs: already selected exact register/counter values.
//   - Outputs: deterministic x86-64 `.text` byte sequences.
//   - Side effects: process-local allocation only.
// - Split-When:
//   - Split when register allocation/general instruction selection is
//   - introduced.
// - Merge-When:
//   - Merge when one reviewed ISA encoder owns all x86-64 native templates.
// - Summary:
//   - Encodes the currently reviewed direct x86-64 template family.
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

//! Reviewed x86-64 instruction templates for direct native execution.

use super::direct::DirectHaltObservation;

/// Returns the canonical no-state-change guard-miss stub.
#[must_use]
pub(super) const fn deopt_code() -> &'static [u8] {
    &[0xb8, 0x01, 0x00, 0x00, 0x00, 0xc3]
}

/// Encodes exact-observation one-step halt preflight and commit.
#[must_use]
pub(super) fn halt_observation_code(
    observation: DirectHaltObservation,
) -> Option<Vec<u8>> {
    let mut code = Vec::with_capacity(96);
    let mut guard_jumps = Vec::with_capacity(7);
    code.extend_from_slice(&[0xb8, 0x01, 0x00, 0x00, 0x00, 0x48, 0x85, 0xc9]);
    push_guard_jump(&mut code, &mut guard_jumps, 0x74);
    push_u64_guard(
        &mut code,
        &mut guard_jumps,
        0x20,
        observation.input_consumed,
    );
    push_u64_guard(&mut code, &mut guard_jumps, 0x38, observation.output_len);
    push_u32_guard(&mut code, &mut guard_jumps, 0x40, observation.accumulator);
    push_u32_guard(&mut code, &mut guard_jumps, 0x44, observation.code_pointer);
    push_u32_guard(&mut code, &mut guard_jumps, 0x48, observation.data_pointer);
    code.extend_from_slice(&[0x80, 0x79, 0x4c, 0x00]);
    push_guard_jump(&mut code, &mut guard_jumps, 0x75);
    code.extend_from_slice(&[0xc6, 0x41, 0x4c, 0x01, 0x31, 0xc0, 0xc3]);
    let guard_miss = code.len();
    code.push(0xc3);
    patch_guard_jumps(&mut code, &guard_jumps, guard_miss)?;
    Some(code)
}

fn patch_guard_jumps(
    code: &mut [u8],
    jumps: &[usize],
    target: usize,
) -> Option<()> {
    for jump in jumps {
        let next = jump.checked_add(1)?;
        let distance = target.checked_sub(next)?;
        let displacement = i8::try_from(distance).ok()?;
        let [byte] = displacement.to_le_bytes();
        *code.get_mut(*jump)? = byte;
    }
    Some(())
}

fn push_guard_jump(code: &mut Vec<u8>, jumps: &mut Vec<usize>, opcode: u8) {
    code.push(opcode);
    jumps.push(code.len());
    code.push(0);
}

fn push_u32_guard(
    code: &mut Vec<u8>,
    jumps: &mut Vec<usize>,
    displacement: u8,
    value: u32,
) {
    code.extend_from_slice(&[0x81, 0x79, displacement]);
    code.extend_from_slice(&value.to_le_bytes());
    push_guard_jump(code, jumps, 0x75);
}

fn push_u64_guard(
    code: &mut Vec<u8>,
    jumps: &mut Vec<usize>,
    displacement: u8,
    value: u64,
) {
    code.extend_from_slice(&[0x48, 0xba]);
    code.extend_from_slice(&value.to_le_bytes());
    code.extend_from_slice(&[0x48, 0x39, 0x51, displacement]);
    push_guard_jump(code, jumps, 0x75);
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
