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
//   - Inputs: already selected exact register/counter values.
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

use super::direct::DirectHaltObservation;

/// Returns the canonical no-state-change guard-miss stub.
#[must_use]
pub(super) const fn deopt_code() -> &'static [u8] {
    &[0x20, 0x00, 0x80, 0x52, 0xc0, 0x03, 0x5f, 0xd6]
}

/// Encodes exact-observation one-step halt preflight and commit.
#[must_use]
pub(super) fn halt_observation_code(
    observation: DirectHaltObservation,
) -> Option<Vec<u8>> {
    let mut words = Vec::with_capacity(48);
    let mut guard_branches = Vec::with_capacity(7);
    push_guard_branch(&mut words, &mut guard_branches, 0xb400_0000);
    words.push(0xf940_1008);
    push_u64_x9(&mut words, observation.input_consumed)?;
    words.push(0xeb09_011f);
    push_guard_branch(&mut words, &mut guard_branches, 0x5400_0001);
    words.push(0xf940_1c08);
    push_u64_x9(&mut words, observation.output_len)?;
    words.push(0xeb09_011f);
    push_guard_branch(&mut words, &mut guard_branches, 0x5400_0001);
    push_u32_guard(
        &mut words,
        &mut guard_branches,
        0xb940_4008,
        observation.accumulator,
    );
    push_u32_guard(
        &mut words,
        &mut guard_branches,
        0xb940_4408,
        observation.code_pointer,
    );
    push_u32_guard(
        &mut words,
        &mut guard_branches,
        0xb940_4808,
        observation.data_pointer,
    );
    words.push(0x3941_3009);
    push_guard_branch(&mut words, &mut guard_branches, 0x3500_0009);
    words.extend_from_slice(&[
        0x5280_002a,
        0x3901_300a,
        0x2a1f_03e0,
        0xd65f_03c0,
    ]);
    let guard_miss = words.len();
    words.extend_from_slice(&[0x5280_0020, 0xd65f_03c0]);
    patch_guard_branches(&mut words, &guard_branches, guard_miss)?;
    Some(encode_words(&words))
}

fn patch_guard_branches(
    words: &mut [u32],
    branches: &[usize],
    target: usize,
) -> Option<()> {
    for branch in branches {
        let distance = target.checked_sub(*branch)?;
        let immediate = u32::try_from(distance).ok()?;
        if immediate >= (1u32 << 18u32) {
            return None;
        }
        *words.get_mut(*branch)? |= immediate << 5u32;
    }
    Some(())
}

fn push_guard_branch(
    words: &mut Vec<u32>,
    branches: &mut Vec<usize>,
    instruction: u32,
) {
    branches.push(words.len());
    words.push(instruction);
}

fn push_u32_guard(
    words: &mut Vec<u32>,
    branches: &mut Vec<usize>,
    load: u32,
    value: u32,
) {
    words.extend_from_slice(&[
        load,
        movz_w9(value),
        movk_w9_high(value),
        0x6b09_011f,
    ]);
    push_guard_branch(words, branches, 0x5400_0001);
}

fn push_u64_x9(words: &mut Vec<u32>, value: u64) -> Option<()> {
    words.extend_from_slice(&[
        movz_x9(value, 0)?,
        movk_x9(value, 1)?,
        movk_x9(value, 2)?,
        movk_x9(value, 3)?,
    ]);
    Some(())
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

fn movk_x9(value: u64, halfword: u32) -> Option<u32> {
    let shift = halfword.checked_mul(16u32)?;
    let immediate = u32::try_from((value >> shift) & 0xffff).ok()?;
    Some(0xf280_0009 | (halfword << 21) | (immediate << 5))
}

fn movz_x9(value: u64, halfword: u32) -> Option<u32> {
    let shift = halfword.checked_mul(16u32)?;
    let immediate = u32::try_from((value >> shift) & 0xffff).ok()?;
    Some(0xd280_0009 | (halfword << 21) | (immediate << 5))
}

const fn movk_w9_high(value: u32) -> u32 {
    let immediate = (value >> 16u32) & 0xffff;
    0x72a0_0009 | (immediate << 5)
}

const fn movz_w9(value: u32) -> u32 {
    let immediate = value & 0xffff;
    0x5280_0009 | (immediate << 5)
}
