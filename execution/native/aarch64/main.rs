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
//   - Inputs: selected observations, fetch live-ins, and exact commits.
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

use super::direct::{
    DirectCodeWriteCommit, DirectEntryObservation, DirectFetchedCellGuard,
    DirectJumpDataGuard,
};

/// Returns the canonical no-state-change guard-miss stub.
#[must_use]
pub(super) const fn deopt_code() -> &'static [u8] {
    &[0x20, 0x00, 0x80, 0x52, 0xc0, 0x03, 0x5f, 0xd6]
}

/// Encodes exact-observation one-step halt preflight and commit.
#[must_use]
pub(super) fn halt_observation_code(
    observation: DirectEntryObservation,
) -> Option<Vec<u8>> {
    let mut words = Vec::with_capacity(48);
    let mut guard_branches = Vec::with_capacity(7);
    push_observation_guards(&mut words, &mut guard_branches, observation)?;
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

fn push_observation_guards(
    words: &mut Vec<u32>,
    guard_branches: &mut Vec<usize>,
    observation: DirectEntryObservation,
) -> Option<()> {
    push_guard_branch(words, guard_branches, 0xb400_0000);
    words.push(0xf940_1008);
    push_u64_x9(words, observation.input_consumed)?;
    words.push(0xeb09_011f);
    push_guard_branch(words, guard_branches, 0x5400_0001);
    words.push(0xf940_1c08);
    push_u64_x9(words, observation.output_len)?;
    words.push(0xeb09_011f);
    push_guard_branch(words, guard_branches, 0x5400_0001);
    push_u32_guard(words, guard_branches, 0xb940_4008, observation.accumulator);
    push_u32_guard(
        words,
        guard_branches,
        0xb940_4408,
        observation.code_pointer,
    );
    push_u32_guard(
        words,
        guard_branches,
        0xb940_4808,
        observation.data_pointer,
    );
    Some(())
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

/// Encodes exact graphical halt-fetch preflight and termination commit.
#[must_use]
pub(super) fn halt_fetch_code(
    observation: DirectEntryObservation,
    guard: DirectFetchedCellGuard,
) -> Option<Vec<u8>> {
    fetched_termination_code(observation, guard, 1)
}

/// Encodes exact non-graphical fetch preflight and termination commit.
#[must_use]
pub(super) fn non_graphical_code(
    observation: DirectEntryObservation,
    guard: DirectFetchedCellGuard,
) -> Option<Vec<u8>> {
    fetched_termination_code(observation, guard, 2)
}

fn fetched_termination_code(
    observation: DirectEntryObservation,
    guard: DirectFetchedCellGuard,
    termination_tag: u32,
) -> Option<Vec<u8>> {
    let mut words = Vec::with_capacity(56);
    let mut guard_branches = Vec::with_capacity(11);
    push_fetched_cell_guards(
        &mut words,
        &mut guard_branches,
        observation,
        guard,
    )?;
    words.extend_from_slice(&[
        movz_w10(termination_tag),
        0x3901_300a,
        0x2a1f_03e0,
        0xd65f_03c0,
    ]);
    let guard_miss = words.len();
    words.extend_from_slice(&[0x5280_0020, 0xd65f_03c0]);
    patch_guard_branches(&mut words, &guard_branches, guard_miss)?;
    Some(encode_words(&words))
}

/// Encodes one exact non-aliasing jump-data transition.
#[must_use]
pub(super) fn jump_data_code(
    observation: DirectEntryObservation,
    guard: DirectJumpDataGuard,
    commit: DirectCodeWriteCommit,
) -> Option<Vec<u8>> {
    let mut words = Vec::with_capacity(72);
    let mut guard_branches = Vec::with_capacity(12);
    push_observation_guards(&mut words, &mut guard_branches, observation)?;
    words.push(0xf940_0008);
    push_guard_branch(&mut words, &mut guard_branches, 0xb400_0008);
    words.push(0xf940_040a);
    push_u64_x9(&mut words, guard.required_memory_words)?;
    words.push(0xeb09_015f);
    push_guard_branch(&mut words, &mut guard_branches, 0x5400_0003);
    push_indexed_memory_guard(
        &mut words,
        &mut guard_branches,
        observation.code_pointer,
        guard.code_live_in,
    );
    push_indexed_memory_guard(
        &mut words,
        &mut guard_branches,
        observation.data_pointer,
        guard.data_live_in,
    );
    words.push(0x3941_3009);
    push_guard_branch(&mut words, &mut guard_branches, 0x3500_0009);
    words.extend_from_slice(&[
        movz_w10(observation.code_pointer),
        movk_w10_high(observation.code_pointer),
        0x8b0a_090a,
        movz_w9(commit.encrypted_value),
        movk_w9_high(commit.encrypted_value),
        0xb900_0149,
        movz_w9(commit.next_code_pointer),
        movk_w9_high(commit.next_code_pointer),
        0xb900_4409,
        movz_w9(commit.next_data_pointer),
        movk_w9_high(commit.next_data_pointer),
        0xb900_4809,
        0x2a1f_03e0,
        0xd65f_03c0,
    ]);
    let guard_miss = words.len();
    words.extend_from_slice(&[0x5280_0020, 0xd65f_03c0]);
    patch_guard_branches(&mut words, &guard_branches, guard_miss)?;
    Some(encode_words(&words))
}

fn push_indexed_memory_guard(
    words: &mut Vec<u32>,
    guard_branches: &mut Vec<usize>,
    address: u32,
    value: u32,
) {
    words.extend_from_slice(&[
        movz_w10(address),
        movk_w10_high(address),
        0x8b0a_090a,
        0xb940_014b,
        movz_w9(value),
        movk_w9_high(value),
        0x6b09_017f,
    ]);
    push_guard_branch(words, guard_branches, 0x5400_0001);
}

/// Encodes one exact no-op fetch, encryption, and pointer advance.
#[must_use]
pub(super) fn no_operation_code(
    observation: DirectEntryObservation,
    guard: DirectFetchedCellGuard,
    commit: DirectCodeWriteCommit,
) -> Option<Vec<u8>> {
    let mut words = Vec::with_capacity(64);
    let mut guard_branches = Vec::with_capacity(11);
    push_fetched_cell_guards(
        &mut words,
        &mut guard_branches,
        observation,
        guard,
    )?;
    words.extend_from_slice(&[
        movz_w9(commit.encrypted_value),
        movk_w9_high(commit.encrypted_value),
        0xb900_0149,
        movz_w9(commit.next_code_pointer),
        movk_w9_high(commit.next_code_pointer),
        0xb900_4409,
        movz_w9(commit.next_data_pointer),
        movk_w9_high(commit.next_data_pointer),
        0xb900_4809,
        0x2a1f_03e0,
        0xd65f_03c0,
    ]);
    let guard_miss = words.len();
    words.extend_from_slice(&[0x5280_0020, 0xd65f_03c0]);
    patch_guard_branches(&mut words, &guard_branches, guard_miss)?;
    Some(encode_words(&words))
}

fn push_fetched_cell_guards(
    words: &mut Vec<u32>,
    guard_branches: &mut Vec<usize>,
    observation: DirectEntryObservation,
    guard: DirectFetchedCellGuard,
) -> Option<()> {
    push_observation_guards(words, guard_branches, observation)?;
    words.push(0xf940_0008);
    push_guard_branch(words, guard_branches, 0xb400_0008);
    words.push(0xf940_040a);
    push_u64_x9(words, guard.required_memory_words)?;
    words.push(0xeb09_015f);
    push_guard_branch(words, guard_branches, 0x5400_0003);
    words.extend_from_slice(&[
        movz_w10(observation.code_pointer),
        movk_w10_high(observation.code_pointer),
        0x8b0a_090a,
        0xb940_014b,
        movz_w9(guard.live_in_value),
        movk_w9_high(guard.live_in_value),
        0x6b09_017f,
    ]);
    push_guard_branch(words, guard_branches, 0x5400_0001);
    words.push(0x3941_3009);
    push_guard_branch(words, guard_branches, 0x3500_0009);
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

const fn movk_w10_high(value: u32) -> u32 {
    let immediate = (value >> 16u32) & 0xffff;
    0x72a0_000a | (immediate << 5)
}

const fn movz_w10(value: u32) -> u32 {
    let immediate = value & 0xffff;
    0x5280_000a | (immediate << 5)
}

const fn movk_w9_high(value: u32) -> u32 {
    let immediate = (value >> 16u32) & 0xffff;
    0x72a0_0009 | (immediate << 5)
}

const fn movz_w9(value: u32) -> u32 {
    let immediate = value & 0xffff;
    0x5280_0009 | (immediate << 5)
}
