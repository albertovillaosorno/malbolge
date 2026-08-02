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
//   - Inputs: selected observations, fetch live-ins, and exact commits.
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

use super::direct::{
    DirectCodeWriteCommit, DirectEntryObservation, DirectFetchedCellGuard,
    DirectJumpCodeGuard, DirectJumpDataGuard,
};

/// Returns the canonical no-state-change guard-miss stub.
#[must_use]
pub(super) const fn deopt_code() -> &'static [u8] {
    &[0xb8, 0x01, 0x00, 0x00, 0x00, 0xc3]
}

/// Encodes exact-observation one-step halt preflight and commit.
#[must_use]
pub(super) fn halt_observation_code(
    observation: DirectEntryObservation,
) -> Option<Vec<u8>> {
    let mut code = Vec::with_capacity(96);
    let mut guard_jumps = Vec::with_capacity(7);
    push_observation_guards(&mut code, &mut guard_jumps, observation);
    code.extend_from_slice(&[0x80, 0x79, 0x4c, 0x00]);
    push_guard_jump(&mut code, &mut guard_jumps, 0x75);
    code.extend_from_slice(&[0xc6, 0x41, 0x4c, 0x01, 0x31, 0xc0, 0xc3]);
    let guard_miss = code.len();
    code.push(0xc3);
    patch_guard_jumps(&mut code, &guard_jumps, guard_miss)?;
    Some(code)
}

fn push_observation_guards(
    code: &mut Vec<u8>,
    guard_jumps: &mut Vec<usize>,
    observation: DirectEntryObservation,
) {
    code.extend_from_slice(&[0xb8, 0x01, 0x00, 0x00, 0x00, 0x48, 0x85, 0xc9]);
    push_guard_jump(code, guard_jumps, 0x74);
    push_u64_guard(code, guard_jumps, 0x20, observation.input_consumed);
    push_u64_guard(code, guard_jumps, 0x38, observation.output_len);
    push_u32_guard(code, guard_jumps, 0x40, observation.accumulator);
    push_u32_guard(code, guard_jumps, 0x44, observation.code_pointer);
    push_u32_guard(code, guard_jumps, 0x48, observation.data_pointer);
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
    termination_tag: u8,
) -> Option<Vec<u8>> {
    let mut code = Vec::with_capacity(128);
    let mut guard_jumps = Vec::with_capacity(11);
    push_fetched_cell_guards(&mut code, &mut guard_jumps, observation, guard);
    code.extend_from_slice(&[
        0xc6,
        0x41,
        0x4c,
        termination_tag,
        0x31,
        0xc0,
        0xc3,
    ]);
    let guard_miss = code.len();
    code.push(0xc3);
    patch_guard_jumps(&mut code, &guard_jumps, guard_miss)?;
    Some(code)
}

/// Encodes one exact non-aliasing jump-code transition.
#[must_use]
pub(super) fn jump_code_code(
    observation: DirectEntryObservation,
    guard: DirectJumpCodeGuard,
    commit: DirectCodeWriteCommit,
) -> Option<Vec<u8>> {
    let code_offset = memory_byte_offset(observation.code_pointer)?;
    let data_offset = memory_byte_offset(observation.data_pointer)?;
    let encryption_offset = memory_byte_offset(commit.encrypted_address)?;
    let mut code = Vec::with_capacity(224);
    let mut guard_jumps = Vec::with_capacity(12);
    push_observation_guards_near(&mut code, &mut guard_jumps, observation);
    code.extend_from_slice(&[0x48, 0x83, 0x39, 0x00]);
    push_near_guard_jump(&mut code, &mut guard_jumps, 0x84);
    code.extend_from_slice(&[0x48, 0x8b, 0x51, 0x08, 0x49, 0xb8]);
    code.extend_from_slice(&guard.required_memory_words.to_le_bytes());
    code.extend_from_slice(&[0x4c, 0x39, 0xc2]);
    push_near_guard_jump(&mut code, &mut guard_jumps, 0x82);
    code.extend_from_slice(&[0x48, 0x8b, 0x11]);
    push_direct_memory_guard_near(
        &mut code,
        &mut guard_jumps,
        code_offset,
        guard.code_live_in,
    );
    push_direct_memory_guard_near(
        &mut code,
        &mut guard_jumps,
        data_offset,
        guard.data_live_in,
    );
    push_direct_memory_guard_near(
        &mut code,
        &mut guard_jumps,
        encryption_offset,
        guard.encryption_live_in,
    );
    code.extend_from_slice(&[0x80, 0x79, 0x4c, 0x00]);
    push_near_guard_jump(&mut code, &mut guard_jumps, 0x85);
    code.extend_from_slice(&[0xc7, 0x82]);
    code.extend_from_slice(&encryption_offset.to_le_bytes());
    code.extend_from_slice(&commit.encrypted_value.to_le_bytes());
    code.extend_from_slice(&[0xc7, 0x41, 0x44]);
    code.extend_from_slice(&commit.next_code_pointer.to_le_bytes());
    code.extend_from_slice(&[0xc7, 0x41, 0x48]);
    code.extend_from_slice(&commit.next_data_pointer.to_le_bytes());
    code.extend_from_slice(&[0x31, 0xc0, 0xc3]);
    let guard_miss = code.len();
    code.push(0xc3);
    patch_near_guard_jumps(&mut code, &guard_jumps, guard_miss)?;
    Some(code)
}

fn push_observation_guards_near(
    code: &mut Vec<u8>,
    guard_jumps: &mut Vec<usize>,
    observation: DirectEntryObservation,
) {
    code.extend_from_slice(&[0xb8, 0x01, 0x00, 0x00, 0x00, 0x48, 0x85, 0xc9]);
    push_near_guard_jump(code, guard_jumps, 0x84);
    push_u64_guard_near(code, guard_jumps, 0x20, observation.input_consumed);
    push_u64_guard_near(code, guard_jumps, 0x38, observation.output_len);
    push_u32_guard_near(code, guard_jumps, 0x40, observation.accumulator);
    push_u32_guard_near(code, guard_jumps, 0x44, observation.code_pointer);
    push_u32_guard_near(code, guard_jumps, 0x48, observation.data_pointer);
}

fn push_u32_guard_near(
    code: &mut Vec<u8>,
    guard_jumps: &mut Vec<usize>,
    displacement: u8,
    value: u32,
) {
    code.extend_from_slice(&[0x81, 0x79, displacement]);
    code.extend_from_slice(&value.to_le_bytes());
    push_near_guard_jump(code, guard_jumps, 0x85);
}

fn push_u64_guard_near(
    code: &mut Vec<u8>,
    guard_jumps: &mut Vec<usize>,
    displacement: u8,
    value: u64,
) {
    code.extend_from_slice(&[0x48, 0xba]);
    code.extend_from_slice(&value.to_le_bytes());
    code.extend_from_slice(&[0x48, 0x39, 0x51, displacement]);
    push_near_guard_jump(code, guard_jumps, 0x85);
}

fn push_direct_memory_guard_near(
    code: &mut Vec<u8>,
    guard_jumps: &mut Vec<usize>,
    offset: u32,
    value: u32,
) {
    code.extend_from_slice(&[0x81, 0xba]);
    code.extend_from_slice(&offset.to_le_bytes());
    code.extend_from_slice(&value.to_le_bytes());
    push_near_guard_jump(code, guard_jumps, 0x85);
}

fn push_near_guard_jump(
    code: &mut Vec<u8>,
    guard_jumps: &mut Vec<usize>,
    condition_opcode: u8,
) {
    code.extend_from_slice(&[0x0f, condition_opcode]);
    guard_jumps.push(code.len());
    code.extend_from_slice(&[0; 4]);
}

fn patch_near_guard_jumps(
    code: &mut [u8],
    guard_jumps: &[usize],
    target: usize,
) -> Option<()> {
    for jump in guard_jumps {
        let next = jump.checked_add(4)?;
        let distance = target.checked_sub(next)?;
        let displacement = i32::try_from(distance).ok()?;
        let end = jump.checked_add(4)?;
        code.get_mut(*jump..end)?
            .copy_from_slice(&displacement.to_le_bytes());
    }
    Some(())
}

/// Encodes one exact non-aliasing jump-data transition.
#[must_use]
pub(super) fn jump_data_code(
    observation: DirectEntryObservation,
    guard: DirectJumpDataGuard,
    commit: DirectCodeWriteCommit,
) -> Option<Vec<u8>> {
    let code_offset = memory_byte_offset(commit.encrypted_address)?;
    let data_offset = memory_byte_offset(observation.data_pointer)?;
    let mut code = Vec::with_capacity(176);
    let mut guard_jumps = Vec::with_capacity(12);
    push_observation_guards(&mut code, &mut guard_jumps, observation);
    code.extend_from_slice(&[0x48, 0x83, 0x39, 0x00]);
    push_guard_jump(&mut code, &mut guard_jumps, 0x74);
    code.extend_from_slice(&[0x48, 0x8b, 0x51, 0x08, 0x49, 0xb8]);
    code.extend_from_slice(&guard.required_memory_words.to_le_bytes());
    code.extend_from_slice(&[0x4c, 0x39, 0xc2]);
    push_guard_jump(&mut code, &mut guard_jumps, 0x72);
    code.extend_from_slice(&[0x48, 0x8b, 0x11]);
    push_direct_memory_guard(
        &mut code,
        &mut guard_jumps,
        code_offset,
        guard.code_live_in,
    );
    push_direct_memory_guard(
        &mut code,
        &mut guard_jumps,
        data_offset,
        guard.data_live_in,
    );
    code.extend_from_slice(&[0x80, 0x79, 0x4c, 0x00]);
    push_guard_jump(&mut code, &mut guard_jumps, 0x75);
    code.extend_from_slice(&[0xeb, 0x01]);
    let guard_miss = code.len();
    code.push(0xc3);
    code.extend_from_slice(&[0xc7, 0x82]);
    code.extend_from_slice(&code_offset.to_le_bytes());
    code.extend_from_slice(&commit.encrypted_value.to_le_bytes());
    code.extend_from_slice(&[0xc7, 0x41, 0x44]);
    code.extend_from_slice(&commit.next_code_pointer.to_le_bytes());
    code.extend_from_slice(&[0xc7, 0x41, 0x48]);
    code.extend_from_slice(&commit.next_data_pointer.to_le_bytes());
    code.extend_from_slice(&[0x31, 0xc0, 0xc3]);
    patch_guard_jumps(&mut code, &guard_jumps, guard_miss)?;
    Some(code)
}

fn memory_byte_offset(address: u32) -> Option<u32> {
    let offset = address.checked_mul(4)?;
    let _signed_offset = i32::try_from(offset).ok()?;
    Some(offset)
}

fn push_direct_memory_guard(
    code: &mut Vec<u8>,
    guard_jumps: &mut Vec<usize>,
    offset: u32,
    value: u32,
) {
    code.extend_from_slice(&[0x81, 0xba]);
    code.extend_from_slice(&offset.to_le_bytes());
    code.extend_from_slice(&value.to_le_bytes());
    push_guard_jump(code, guard_jumps, 0x75);
}

/// Encodes one exact no-op fetch, encryption, and pointer advance.
#[must_use]
pub(super) fn no_operation_code(
    observation: DirectEntryObservation,
    guard: DirectFetchedCellGuard,
    commit: DirectCodeWriteCommit,
) -> Option<Vec<u8>> {
    let mut code = Vec::with_capacity(160);
    let mut guard_jumps = Vec::with_capacity(11);
    push_fetched_cell_guards(&mut code, &mut guard_jumps, observation, guard);
    code.extend_from_slice(&[0xeb, 0x01]);
    let guard_miss = code.len();
    code.push(0xc3);
    code.extend_from_slice(&[0x42, 0xc7, 0x04, 0x8a]);
    code.extend_from_slice(&commit.encrypted_value.to_le_bytes());
    code.extend_from_slice(&[0xc7, 0x41, 0x44]);
    code.extend_from_slice(&commit.next_code_pointer.to_le_bytes());
    code.extend_from_slice(&[0xc7, 0x41, 0x48]);
    code.extend_from_slice(&commit.next_data_pointer.to_le_bytes());
    code.extend_from_slice(&[0x31, 0xc0, 0xc3]);
    patch_guard_jumps(&mut code, &guard_jumps, guard_miss)?;
    Some(code)
}

fn push_fetched_cell_guards(
    code: &mut Vec<u8>,
    guard_jumps: &mut Vec<usize>,
    observation: DirectEntryObservation,
    guard: DirectFetchedCellGuard,
) {
    push_observation_guards(code, guard_jumps, observation);
    code.extend_from_slice(&[0x48, 0x83, 0x39, 0x00]);
    push_guard_jump(code, guard_jumps, 0x74);
    code.extend_from_slice(&[0x48, 0x8b, 0x51, 0x08, 0x49, 0xb8]);
    code.extend_from_slice(&guard.required_memory_words.to_le_bytes());
    code.extend_from_slice(&[0x4c, 0x39, 0xc2]);
    push_guard_jump(code, guard_jumps, 0x72);
    code.extend_from_slice(&[0x48, 0x8b, 0x11, 0x41, 0xb9]);
    code.extend_from_slice(&observation.code_pointer.to_le_bytes());
    code.extend_from_slice(&[0x42, 0x81, 0x3c, 0x8a]);
    code.extend_from_slice(&guard.live_in_value.to_le_bytes());
    push_guard_jump(code, guard_jumps, 0x75);
    code.extend_from_slice(&[0x80, 0x79, 0x4c, 0x00]);
    push_guard_jump(code, guard_jumps, 0x75);
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
