// Copyright:
//   - Copyright © 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - MIT
// Confidential:
//   - false
// License-File:
//   - LICENSE-MIT
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
//   - `src/runtime/tiered-execution/adapter-outbound/native/direct/mod.rs`.
// - Usage:
//   - Called by direct native object generation after exact IR-shape selection.
// - Defaults:
//   - No instruction sequence is selected implicitly by this module.
//

//! Reviewed `AArch64` instruction templates for direct native execution.

use super::direct::{
    DirectCodeWriteCommit, DirectCrazyCommit, DirectCrazyGuard,
    DirectEntryObservation, DirectFetchedCellGuard,
    DirectFusedCodeWriteInputTemplate, DirectFusedCrazyNoOperationTemplate,
    DirectFusedCrazyPairTemplate, DirectFusedDataWriteInputTemplate,
    DirectFusedInputCodeWriteTemplate, DirectFusedInputDataWriteTemplate,
    DirectFusedInputOutputTemplate, DirectFusedInputPairTemplate,
    DirectFusedNoOperationCrazyTemplate, DirectFusedNoOperationOutputTemplate,
    DirectFusedNoOperationPairTemplate, DirectFusedNoOperationRotateTemplate,
    DirectFusedOutputPairTemplate, DirectFusedRotateNoOperationTemplate,
    DirectFusedRotateOutputTemplate, DirectFusedRotatePairTemplate,
    DirectInputCommit, DirectInputGuard, DirectJumpCodeGuard,
    DirectJumpDataGuard, DirectOutputCommit, DirectRegisterMaskedCrazyGuard,
    DirectRegisterMaskedNoOperationGuard,
    DirectRegisterMaskedNoOperationHaltTemplate,
    DirectRegisterMaskedNoOperationPairTemplate,
    DirectRegisterMaskedNoOperationRotateTemplate,
    DirectRegisterMaskedOutputGuard, DirectRegisterMaskedRotateGuard,
    DirectRegisterMaskedTerminalGuard, DirectRotateCommit, DirectRotateGuard,
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

/// Encodes v6 halt fetch using only its declared C register dependency.
#[must_use]
pub(super) fn register_masked_halt_fetch_code(
    guard: DirectRegisterMaskedTerminalGuard,
) -> Option<Vec<u8>> {
    register_masked_terminal_code(guard, 1)
}

/// Encodes v6 no-operation using only declared C/D dependencies.
#[must_use]
pub(super) fn register_masked_no_operation_code(
    guard: DirectRegisterMaskedNoOperationGuard,
    commit: DirectCodeWriteCommit,
) -> Option<Vec<u8>> {
    if commit.encrypted_address != guard.code_pointer {
        return None;
    }
    let mut words = Vec::with_capacity(48);
    let mut guard_branches = Vec::with_capacity(7);
    push_guard_branch(&mut words, &mut guard_branches, 0xb400_0000);
    push_u32_guard(
        &mut words,
        &mut guard_branches,
        0xb940_4408,
        guard.code_pointer,
    );
    push_u32_guard(
        &mut words,
        &mut guard_branches,
        0xb940_4808,
        guard.data_pointer,
    );
    words.push(0xf940_0008);
    push_guard_branch(&mut words, &mut guard_branches, 0xb400_0008);
    words.push(0xf940_040a);
    push_u64_x9(&mut words, guard.required_memory_words)?;
    words.push(0xeb09_015f);
    push_guard_branch(&mut words, &mut guard_branches, 0x5400_0003);
    push_indexed_memory_guard(
        &mut words,
        &mut guard_branches,
        guard.code_pointer,
        guard.live_in_value,
    );
    words.push(0x3941_3009);
    push_guard_branch(&mut words, &mut guard_branches, 0x3500_0009);
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

/// Encodes one collapsed v6 no-operation followed by graphical halt.
#[must_use]
pub(super) fn register_masked_no_operation_halt_code(
    template: DirectRegisterMaskedNoOperationHaltTemplate,
) -> Option<Vec<u8>> {
    if template.encrypted_address != template.entry_code_pointer {
        return None;
    }
    let mut words = Vec::with_capacity(60);
    let mut guard_branches = Vec::with_capacity(9);
    push_guard_branch(&mut words, &mut guard_branches, 0xb400_0000);
    push_u32_guard(
        &mut words,
        &mut guard_branches,
        0xb940_4408,
        template.entry_code_pointer,
    );
    push_u32_guard(
        &mut words,
        &mut guard_branches,
        0xb940_4808,
        template.entry_data_pointer,
    );
    words.push(0xf940_0008);
    push_guard_branch(&mut words, &mut guard_branches, 0xb400_0008);
    words.push(0xf940_040a);
    push_u64_x9(&mut words, template.required_memory_words)?;
    words.push(0xeb09_015f);
    push_guard_branch(&mut words, &mut guard_branches, 0x5400_0003);
    push_indexed_memory_guard(
        &mut words,
        &mut guard_branches,
        template.entry_code_pointer,
        template.code_live_in,
    );
    push_indexed_memory_guard(
        &mut words,
        &mut guard_branches,
        template.next_code_pointer,
        template.halt_live_in,
    );
    words.push(0x3941_3009);
    push_guard_branch(&mut words, &mut guard_branches, 0x3500_0009);
    words.extend_from_slice(&[
        movz_w9(template.encrypted_value),
        movk_w9_high(template.encrypted_value),
        0xb900_0149,
        movz_w9(template.next_code_pointer),
        movk_w9_high(template.next_code_pointer),
        0xb900_4409,
        movz_w9(template.next_data_pointer),
        movk_w9_high(template.next_data_pointer),
        0xb900_4809,
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

/// Encodes one collapsed v6 pair of consecutive no-operations.
#[must_use]
pub(super) fn register_masked_no_operation_pair_code(
    template: DirectRegisterMaskedNoOperationPairTemplate,
) -> Option<Vec<u8>> {
    if template.first_encrypted_address != template.entry_code_pointer
        || template.second_encrypted_address != template.second_code_pointer
    {
        return None;
    }
    let mut words = Vec::with_capacity(64);
    let mut guard_branches = Vec::with_capacity(9);
    push_guard_branch(&mut words, &mut guard_branches, 0xb400_0000);
    push_u32_guard(
        &mut words,
        &mut guard_branches,
        0xb940_4408,
        template.entry_code_pointer,
    );
    push_u32_guard(
        &mut words,
        &mut guard_branches,
        0xb940_4808,
        template.entry_data_pointer,
    );
    words.push(0xf940_0008);
    push_guard_branch(&mut words, &mut guard_branches, 0xb400_0008);
    words.push(0xf940_040a);
    push_u64_x9(&mut words, template.required_memory_words)?;
    words.push(0xeb09_015f);
    push_guard_branch(&mut words, &mut guard_branches, 0x5400_0003);
    push_indexed_memory_guard(
        &mut words,
        &mut guard_branches,
        template.entry_code_pointer,
        template.first_live_in,
    );
    push_indexed_memory_guard(
        &mut words,
        &mut guard_branches,
        template.second_code_pointer,
        template.second_live_in,
    );
    words.push(0x3941_3009);
    push_guard_branch(&mut words, &mut guard_branches, 0x3500_0009);
    push_register_masked_no_operation_pair_commit(&mut words, template);
    let guard_miss = words.len();
    words.extend_from_slice(&[0x5280_0020, 0xd65f_03c0]);
    patch_guard_branches(&mut words, &guard_branches, guard_miss)?;
    Some(encode_words(&words))
}

fn push_register_masked_no_operation_pair_commit(
    words: &mut Vec<u32>,
    template: DirectRegisterMaskedNoOperationPairTemplate,
) {
    words.extend_from_slice(&[
        movz_w10(template.first_encrypted_address),
        movk_w10_high(template.first_encrypted_address),
        0x8b0a_090a,
        movz_w9(template.first_encrypted_value),
        movk_w9_high(template.first_encrypted_value),
        0xb900_0149,
        movz_w10(template.second_encrypted_address),
        movk_w10_high(template.second_encrypted_address),
        0x8b0a_090a,
        movz_w9(template.second_encrypted_value),
        movk_w9_high(template.second_encrypted_value),
        0xb900_0149,
        movz_w9(template.next_code_pointer),
        movk_w9_high(template.next_code_pointer),
        0xb900_4409,
        movz_w9(template.next_data_pointer),
        movk_w9_high(template.next_data_pointer),
        0xb900_4809,
        0x2a1f_03e0,
        0xd65f_03c0,
    ]);
}

/// Encodes collapsed v6 no-operation followed by rotate.
#[must_use]
pub(super) fn register_masked_no_operation_rotate_code(
    template: DirectRegisterMaskedNoOperationRotateTemplate,
) -> Option<Vec<u8>> {
    if template.first_encrypted_address != template.entry_code_pointer
        || template.rotate_encrypted_address != template.rotate_code_pointer
        || template.rotate_data_address != template.rotate_data_pointer
    {
        return None;
    }
    let mut words = Vec::with_capacity(80);
    let mut guard_branches = Vec::with_capacity(10);
    push_guard_branch(&mut words, &mut guard_branches, 0xb400_0000);
    push_u32_guard(
        &mut words,
        &mut guard_branches,
        0xb940_4408,
        template.entry_code_pointer,
    );
    push_u32_guard(
        &mut words,
        &mut guard_branches,
        0xb940_4808,
        template.entry_data_pointer,
    );
    words.push(0xf940_0008);
    push_guard_branch(&mut words, &mut guard_branches, 0xb400_0008);
    words.push(0xf940_040a);
    push_u64_x9(&mut words, template.required_memory_words)?;
    words.push(0xeb09_015f);
    push_guard_branch(&mut words, &mut guard_branches, 0x5400_0003);
    for (address, live_in) in [
        (template.entry_code_pointer, template.first_live_in),
        (template.rotate_code_pointer, template.rotate_code_live_in),
        (template.rotate_data_address, template.rotate_data_live_in),
    ] {
        push_indexed_memory_guard(
            &mut words,
            &mut guard_branches,
            address,
            live_in,
        );
    }
    words.push(0x3941_3009);
    push_guard_branch(&mut words, &mut guard_branches, 0x3500_0009);
    push_register_masked_no_operation_rotate_commit(&mut words, template);
    let guard_miss = words.len();
    words.extend_from_slice(&[0x5280_0020, 0xd65f_03c0]);
    patch_guard_branches(&mut words, &guard_branches, guard_miss)?;
    Some(encode_words(&words))
}

fn push_register_masked_no_operation_rotate_commit(
    words: &mut Vec<u32>,
    template: DirectRegisterMaskedNoOperationRotateTemplate,
) {
    for (address, value) in [
        (
            template.first_encrypted_address,
            template.first_encrypted_value,
        ),
        (template.rotate_data_address, template.rotated_value),
        (
            template.rotate_encrypted_address,
            template.rotate_encrypted_value,
        ),
    ] {
        words.extend_from_slice(&[
            movz_w10(address),
            movk_w10_high(address),
            0x8b0a_090a,
            movz_w9(value),
            movk_w9_high(value),
            0xb900_0149,
        ]);
    }
    words.extend_from_slice(&[
        movz_w9(template.rotated_value),
        movk_w9_high(template.rotated_value),
        0xb900_4009,
        movz_w9(template.next_code_pointer),
        movk_w9_high(template.next_code_pointer),
        0xb900_4409,
        movz_w9(template.next_data_pointer),
        movk_w9_high(template.next_data_pointer),
        0xb900_4809,
        0x2a1f_03e0,
        0xd65f_03c0,
    ]);
}

/// Encodes v6 Crazy using its declared A/C/D dependencies.
#[must_use]
pub(super) fn register_masked_crazy_code(
    guard: DirectRegisterMaskedCrazyGuard,
    commit: DirectCrazyCommit,
) -> Option<Vec<u8>> {
    register_masked_data_write_code(
        Some(guard.accumulator),
        DirectRegisterMaskedRotateGuard {
            code_live_in: guard.code_live_in,
            code_pointer: guard.code_pointer,
            data_live_in: guard.data_live_in,
            data_pointer: guard.data_pointer,
            required_memory_words: guard.required_memory_words,
        },
        commit,
    )
}

/// Encodes v6 output without guarding dead input history.
#[must_use]
pub(super) fn register_masked_output_code(
    guard: DirectRegisterMaskedOutputGuard,
    commit: DirectOutputCommit,
) -> Option<Vec<u8>> {
    if commit.encrypted_address != guard.code_pointer
        || commit.output_index != guard.output_len
    {
        return None;
    }
    let mut words = Vec::with_capacity(92);
    let mut guard_branches = Vec::with_capacity(13);
    push_register_masked_output_guards(
        &mut words,
        &mut guard_branches,
        guard,
        commit.output_index,
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
        0xf940_1c0a,
        0x8b0a_016b,
        movz_w9(u32::from(commit.output_byte)),
        0x3900_0169,
    ]);
    push_u64_x9(&mut words, commit.next_output_len)?;
    words.extend_from_slice(&[0xf900_1c09, 0x2a1f_03e0, 0xd65f_03c0]);
    let guard_miss = words.len();
    words.extend_from_slice(&[0x5280_0020, 0xd65f_03c0]);
    patch_guard_branches(&mut words, &guard_branches, guard_miss)?;
    Some(encode_words(&words))
}

fn push_register_masked_output_guards(
    words: &mut Vec<u32>,
    guard_branches: &mut Vec<usize>,
    guard: DirectRegisterMaskedOutputGuard,
    output_index: u64,
) -> Option<()> {
    push_guard_branch(words, guard_branches, 0xb400_0000);
    words.push(0xf940_1c08);
    push_u64_x9(words, guard.output_len)?;
    words.push(0xeb09_011f);
    push_guard_branch(words, guard_branches, 0x5400_0001);
    push_u32_guard(words, guard_branches, 0xb940_4008, guard.accumulator);
    push_u32_guard(words, guard_branches, 0xb940_4408, guard.code_pointer);
    push_u32_guard(words, guard_branches, 0xb940_4808, guard.data_pointer);
    words.push(0xf940_0008);
    push_guard_branch(words, guard_branches, 0xb400_0008);
    words.push(0xf940_040a);
    push_u64_x9(words, guard.required_memory_words)?;
    words.push(0xeb09_015f);
    push_guard_branch(words, guard_branches, 0x5400_0003);
    push_indexed_memory_guard(
        words,
        guard_branches,
        guard.code_pointer,
        guard.code_live_in,
    );
    words.push(0x3941_3009);
    push_guard_branch(words, guard_branches, 0x3500_0009);
    words.push(0xf940_140b);
    push_guard_branch(words, guard_branches, 0xb400_000b);
    words.push(0xf940_180c);
    push_u64_x9(words, output_index)?;
    words.push(0xeb09_019f);
    push_guard_branch(words, guard_branches, 0x5400_0009);
    Some(())
}

/// Encodes v6 rotate using only declared C/D dependencies.
#[must_use]
pub(super) fn register_masked_rotate_code(
    guard: DirectRegisterMaskedRotateGuard,
    commit: DirectRotateCommit,
) -> Option<Vec<u8>> {
    register_masked_data_write_code(None, guard, commit)
}

fn register_masked_data_write_code(
    accumulator: Option<u32>,
    guard: DirectRegisterMaskedRotateGuard,
    commit: DirectRotateCommit,
) -> Option<Vec<u8>> {
    if commit.encrypted_address != guard.code_pointer
        || commit.data_address != guard.data_pointer
    {
        return None;
    }
    let mut words = Vec::with_capacity(80);
    let mut guard_branches = Vec::with_capacity(10);
    push_guard_branch(&mut words, &mut guard_branches, 0xb400_0000);
    if let Some(value) = accumulator {
        push_u32_guard(&mut words, &mut guard_branches, 0xb940_4008, value);
    }
    push_u32_guard(
        &mut words,
        &mut guard_branches,
        0xb940_4408,
        guard.code_pointer,
    );
    push_u32_guard(
        &mut words,
        &mut guard_branches,
        0xb940_4808,
        guard.data_pointer,
    );
    words.push(0xf940_0008);
    push_guard_branch(&mut words, &mut guard_branches, 0xb400_0008);
    words.push(0xf940_040a);
    push_u64_x9(&mut words, guard.required_memory_words)?;
    words.push(0xeb09_015f);
    push_guard_branch(&mut words, &mut guard_branches, 0x5400_0003);
    push_indexed_memory_guard(
        &mut words,
        &mut guard_branches,
        guard.code_pointer,
        guard.code_live_in,
    );
    push_indexed_memory_guard(
        &mut words,
        &mut guard_branches,
        guard.data_pointer,
        guard.data_live_in,
    );
    words.push(0x3941_3009);
    push_guard_branch(&mut words, &mut guard_branches, 0x3500_0009);
    push_register_masked_rotate_commit(&mut words, commit);
    let guard_miss = words.len();
    words.extend_from_slice(&[0x5280_0020, 0xd65f_03c0]);
    patch_guard_branches(&mut words, &guard_branches, guard_miss)?;
    Some(encode_words(&words))
}

fn push_register_masked_rotate_commit(
    words: &mut Vec<u32>,
    commit: DirectRotateCommit,
) {
    words.extend_from_slice(&[
        movz_w10(commit.data_address),
        movk_w10_high(commit.data_address),
        0x8b0a_090a,
        movz_w9(commit.data_value),
        movk_w9_high(commit.data_value),
        0xb900_0149,
        movz_w10(commit.encrypted_address),
        movk_w10_high(commit.encrypted_address),
        0x8b0a_090a,
        movz_w9(commit.encrypted_value),
        movk_w9_high(commit.encrypted_value),
        0xb900_0149,
        movz_w9(commit.accumulator),
        movk_w9_high(commit.accumulator),
        0xb900_4009,
        movz_w9(commit.next_code_pointer),
        movk_w9_high(commit.next_code_pointer),
        0xb900_4409,
        movz_w9(commit.next_data_pointer),
        movk_w9_high(commit.next_data_pointer),
        0xb900_4809,
        0x2a1f_03e0,
        0xd65f_03c0,
    ]);
}

/// Encodes v6 non-graphical fetch using only declared C dependency.
#[must_use]
pub(super) fn register_masked_non_graphical_code(
    guard: DirectRegisterMaskedTerminalGuard,
) -> Option<Vec<u8>> {
    register_masked_terminal_code(guard, 2)
}

fn register_masked_terminal_code(
    guard: DirectRegisterMaskedTerminalGuard,
    termination_tag: u32,
) -> Option<Vec<u8>> {
    let mut words = Vec::with_capacity(40);
    let mut guard_branches = Vec::with_capacity(6);
    push_guard_branch(&mut words, &mut guard_branches, 0xb400_0000);
    push_u32_guard(
        &mut words,
        &mut guard_branches,
        0xb940_4408,
        guard.code_pointer,
    );
    words.push(0xf940_0008);
    push_guard_branch(&mut words, &mut guard_branches, 0xb400_0008);
    words.push(0xf940_040a);
    push_u64_x9(&mut words, guard.required_memory_words)?;
    words.push(0xeb09_015f);
    push_guard_branch(&mut words, &mut guard_branches, 0x5400_0003);
    push_indexed_memory_guard(
        &mut words,
        &mut guard_branches,
        guard.code_pointer,
        guard.live_in_value,
    );
    words.push(0x3941_3009);
    push_guard_branch(&mut words, &mut guard_branches, 0x3500_0009);
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

/// Encodes one exact non-aliasing jump-code transition.
#[must_use]
pub(super) fn jump_code_code(
    observation: DirectEntryObservation,
    guard: DirectJumpCodeGuard,
    commit: DirectCodeWriteCommit,
) -> Option<Vec<u8>> {
    let mut words = Vec::with_capacity(88);
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
    push_indexed_memory_guard(
        &mut words,
        &mut guard_branches,
        commit.encrypted_address,
        guard.encryption_live_in,
    );
    words.push(0x3941_3009);
    push_guard_branch(&mut words, &mut guard_branches, 0x3500_0009);
    words.extend_from_slice(&[
        movz_w10(commit.encrypted_address),
        movk_w10_high(commit.encrypted_address),
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

/// Encodes one exact input transition for a byte or end-of-input.
#[must_use]
pub(super) fn input_code(
    observation: DirectEntryObservation,
    guard: DirectInputGuard,
    commit: DirectInputCommit,
) -> Option<Vec<u8>> {
    let mut words = Vec::with_capacity(104);
    let mut guard_branches = Vec::with_capacity(13);
    push_fetched_cell_guards(
        &mut words,
        &mut guard_branches,
        observation,
        DirectFetchedCellGuard {
            live_in_value: guard.code_live_in,
            required_memory_words: guard.required_memory_words,
        },
    )?;
    push_input_guard(
        &mut words,
        &mut guard_branches,
        guard.input,
        guard.input_index,
    )?;
    words.extend_from_slice(&[
        movz_w9(commit.encrypted_value),
        movk_w9_high(commit.encrypted_value),
        0xb900_0149,
        movz_w9(commit.accumulator),
        movk_w9_high(commit.accumulator),
        0xb900_4009,
        movz_w9(commit.next_code_pointer),
        movk_w9_high(commit.next_code_pointer),
        0xb900_4409,
        movz_w9(commit.next_data_pointer),
        movk_w9_high(commit.next_data_pointer),
        0xb900_4809,
    ]);
    push_u64_x9(&mut words, commit.next_input_consumed)?;
    words.extend_from_slice(&[0xf900_1009, 0x2a1f_03e0, 0xd65f_03c0]);
    let guard_miss = words.len();
    words.extend_from_slice(&[0x5280_0020, 0xd65f_03c0]);
    patch_guard_branches(&mut words, &guard_branches, guard_miss)?;
    Some(encode_words(&words))
}

/// Encodes one exact output transition with an atomic byte append.
#[must_use]
pub(super) fn output_code(
    observation: DirectEntryObservation,
    guard: DirectFetchedCellGuard,
    commit: DirectOutputCommit,
) -> Option<Vec<u8>> {
    let mut words = Vec::with_capacity(96);
    let mut guard_branches = Vec::with_capacity(14);
    push_fetched_cell_guards(
        &mut words,
        &mut guard_branches,
        observation,
        guard,
    )?;
    words.push(0xf940_140b);
    push_guard_branch(&mut words, &mut guard_branches, 0xb400_000b);
    words.push(0xf940_180c);
    push_u64_x9(&mut words, commit.output_index)?;
    words.push(0xeb09_019f);
    push_guard_branch(&mut words, &mut guard_branches, 0x5400_0009);
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
        0xf940_1c0a,
        0x8b0a_016b,
        movz_w9(u32::from(commit.output_byte)),
        0x3900_0169,
    ]);
    push_u64_x9(&mut words, commit.next_output_len)?;
    words.extend_from_slice(&[0xf900_1c09, 0x2a1f_03e0, 0xd65f_03c0]);
    let guard_miss = words.len();
    words.extend_from_slice(&[0x5280_0020, 0xd65f_03c0]);
    patch_guard_branches(&mut words, &guard_branches, guard_miss)?;
    Some(encode_words(&words))
}

/// Encodes one atomic two-step crazy/output fused region.
#[must_use]
pub(super) fn fused_crazy_output_code(
    template: super::direct::DirectFusedCrazyOutputTemplate<'_>,
) -> Option<Vec<u8>> {
    let mut words = Vec::with_capacity(128);
    let mut guard_branches =
        Vec::with_capacity(template.live_ins.len().saturating_add(12));
    push_observation_guards(
        &mut words,
        &mut guard_branches,
        template.observation,
    )?;
    words.push(0xf940_0008);
    push_guard_branch(&mut words, &mut guard_branches, 0xb400_0008);
    words.push(0xf940_040a);
    push_u64_x9(&mut words, template.required_memory_words)?;
    words.push(0xeb09_015f);
    push_guard_branch(&mut words, &mut guard_branches, 0x5400_0003);
    for live_in in template.live_ins {
        push_indexed_memory_guard(
            &mut words,
            &mut guard_branches,
            live_in.address,
            live_in.value,
        );
    }
    words.push(0x3941_3009);
    push_guard_branch(&mut words, &mut guard_branches, 0x3500_0009);
    words.push(0xf940_140b);
    push_guard_branch(&mut words, &mut guard_branches, 0xb400_000b);
    words.push(0xf940_180c);
    push_u64_x9(&mut words, template.output.output_index)?;
    words.push(0xeb09_019f);
    push_guard_branch(&mut words, &mut guard_branches, 0x5400_0009);
    push_fused_crazy_output_commit(&mut words, template)?;
    let guard_miss = words.len();
    words.extend_from_slice(&[0x5280_0020, 0xd65f_03c0]);
    patch_guard_branches(&mut words, &guard_branches, guard_miss)?;
    Some(encode_words(&words))
}

fn push_fused_crazy_output_commit(
    words: &mut Vec<u32>,
    template: super::direct::DirectFusedCrazyOutputTemplate<'_>,
) -> Option<()> {
    words.extend_from_slice(&[
        movz_w10(template.crazy.data_address),
        movk_w10_high(template.crazy.data_address),
        0x8b0a_090a,
        movz_w9(template.crazy.data_value),
        movk_w9_high(template.crazy.data_value),
        0xb900_0149,
        movz_w10(template.crazy.encrypted_address),
        movk_w10_high(template.crazy.encrypted_address),
        0x8b0a_090a,
        movz_w9(template.crazy.encrypted_value),
        movk_w9_high(template.crazy.encrypted_value),
        0xb900_0149,
        movz_w10(template.output.encrypted_address),
        movk_w10_high(template.output.encrypted_address),
        0x8b0a_090a,
        movz_w9(template.output.encrypted_value),
        movk_w9_high(template.output.encrypted_value),
        0xb900_0149,
        movz_w9(template.crazy.accumulator),
        movk_w9_high(template.crazy.accumulator),
        0xb900_4009,
        movz_w9(template.output.next_code_pointer),
        movk_w9_high(template.output.next_code_pointer),
        0xb900_4409,
        movz_w9(template.output.next_data_pointer),
        movk_w9_high(template.output.next_data_pointer),
        0xb900_4809,
        0xf940_1c0a,
        0x8b0a_016b,
        movz_w9(u32::from(template.output.output_byte)),
        0x3900_0169,
    ]);
    push_u64_x9(words, template.output.next_output_len)?;
    words.extend_from_slice(&[0xf900_1c09, 0x2a1f_03e0, 0xd65f_03c0]);
    Some(())
}

/// Encodes one atomic two-step crazy/crazy fused region.
#[must_use]
pub(super) fn fused_crazy_pair_code(
    template: DirectFusedCrazyPairTemplate<'_>,
) -> Option<Vec<u8>> {
    let mut words = Vec::with_capacity(128);
    let mut guard_branches =
        Vec::with_capacity(template.live_ins.len().saturating_add(10));
    push_observation_guards(
        &mut words,
        &mut guard_branches,
        template.observation,
    )?;
    words.push(0xf940_0008);
    push_guard_branch(&mut words, &mut guard_branches, 0xb400_0008);
    words.push(0xf940_040a);
    push_u64_x9(&mut words, template.required_memory_words)?;
    words.push(0xeb09_015f);
    push_guard_branch(&mut words, &mut guard_branches, 0x5400_0003);
    for live_in in template.live_ins {
        push_indexed_memory_guard(
            &mut words,
            &mut guard_branches,
            live_in.address,
            live_in.value,
        );
    }
    words.push(0x3941_3009);
    push_guard_branch(&mut words, &mut guard_branches, 0x3500_0009);
    push_fused_crazy_pair_commit(&mut words, template);
    let guard_miss = words.len();
    words.extend_from_slice(&[0x5280_0020, 0xd65f_03c0]);
    patch_guard_branches(&mut words, &guard_branches, guard_miss)?;
    Some(encode_words(&words))
}

fn push_fused_crazy_pair_commit(
    words: &mut Vec<u32>,
    template: DirectFusedCrazyPairTemplate<'_>,
) {
    for crazy in [template.first, template.second] {
        words.extend_from_slice(&[
            movz_w10(crazy.data_address),
            movk_w10_high(crazy.data_address),
            0x8b0a_090a,
            movz_w9(crazy.data_value),
            movk_w9_high(crazy.data_value),
            0xb900_0149,
            movz_w10(crazy.encrypted_address),
            movk_w10_high(crazy.encrypted_address),
            0x8b0a_090a,
            movz_w9(crazy.encrypted_value),
            movk_w9_high(crazy.encrypted_value),
            0xb900_0149,
        ]);
    }
    words.extend_from_slice(&[
        movz_w9(template.second.accumulator),
        movk_w9_high(template.second.accumulator),
        0xb900_4009,
        movz_w9(template.second.next_code_pointer),
        movk_w9_high(template.second.next_code_pointer),
        0xb900_4409,
        movz_w9(template.second.next_data_pointer),
        movk_w9_high(template.second.next_data_pointer),
        0xb900_4809,
        0x2a1f_03e0,
        0xd65f_03c0,
    ]);
}

/// Encodes one atomic two-step crazy/rotate fused region.
#[must_use]
pub(super) fn fused_crazy_rotate_code(
    template: super::direct::DirectFusedCrazyRotateTemplate<'_>,
) -> Option<Vec<u8>> {
    fused_rotate_pair_code(DirectFusedRotatePairTemplate {
        first: template.crazy,
        live_ins: template.live_ins,
        observation: template.observation,
        required_memory_words: template.required_memory_words,
        second: template.rotate,
    })
}

/// Encodes one atomic two-step crazy/no-operation fused region.
#[must_use]
pub(super) fn fused_crazy_no_operation_code(
    template: DirectFusedCrazyNoOperationTemplate<'_>,
) -> Option<Vec<u8>> {
    let mut words = Vec::with_capacity(112);
    let mut guard_branches =
        Vec::with_capacity(template.live_ins.len().saturating_add(10));
    push_observation_guards(
        &mut words,
        &mut guard_branches,
        template.observation,
    )?;
    words.push(0xf940_0008);
    push_guard_branch(&mut words, &mut guard_branches, 0xb400_0008);
    words.push(0xf940_040a);
    push_u64_x9(&mut words, template.required_memory_words)?;
    words.push(0xeb09_015f);
    push_guard_branch(&mut words, &mut guard_branches, 0x5400_0003);
    for live_in in template.live_ins {
        push_indexed_memory_guard(
            &mut words,
            &mut guard_branches,
            live_in.address,
            live_in.value,
        );
    }
    words.push(0x3941_3009);
    push_guard_branch(&mut words, &mut guard_branches, 0x3500_0009);
    push_fused_crazy_no_operation_commit(&mut words, template);
    let guard_miss = words.len();
    words.extend_from_slice(&[0x5280_0020, 0xd65f_03c0]);
    patch_guard_branches(&mut words, &guard_branches, guard_miss)?;
    Some(encode_words(&words))
}

fn push_fused_crazy_no_operation_commit(
    words: &mut Vec<u32>,
    template: DirectFusedCrazyNoOperationTemplate<'_>,
) {
    words.extend_from_slice(&[
        movz_w10(template.crazy.data_address),
        movk_w10_high(template.crazy.data_address),
        0x8b0a_090a,
        movz_w9(template.crazy.data_value),
        movk_w9_high(template.crazy.data_value),
        0xb900_0149,
        movz_w10(template.crazy.encrypted_address),
        movk_w10_high(template.crazy.encrypted_address),
        0x8b0a_090a,
        movz_w9(template.crazy.encrypted_value),
        movk_w9_high(template.crazy.encrypted_value),
        0xb900_0149,
        movz_w10(template.no_operation.encrypted_address),
        movk_w10_high(template.no_operation.encrypted_address),
        0x8b0a_090a,
        movz_w9(template.no_operation.encrypted_value),
        movk_w9_high(template.no_operation.encrypted_value),
        0xb900_0149,
        movz_w9(template.crazy.accumulator),
        movk_w9_high(template.crazy.accumulator),
        0xb900_4009,
        movz_w9(template.no_operation.next_code_pointer),
        movk_w9_high(template.no_operation.next_code_pointer),
        0xb900_4409,
        movz_w9(template.no_operation.next_data_pointer),
        movk_w9_high(template.no_operation.next_data_pointer),
        0xb900_4809,
        0x2a1f_03e0,
        0xd65f_03c0,
    ]);
}

/// Encodes one atomic two-step no-operation/crazy fused region.
#[must_use]
pub(super) fn fused_no_operation_crazy_code(
    template: DirectFusedNoOperationCrazyTemplate<'_>,
) -> Option<Vec<u8>> {
    let mut words = Vec::with_capacity(112);
    let mut guard_branches =
        Vec::with_capacity(template.live_ins.len().saturating_add(10));
    push_observation_guards(
        &mut words,
        &mut guard_branches,
        template.observation,
    )?;
    words.push(0xf940_0008);
    push_guard_branch(&mut words, &mut guard_branches, 0xb400_0008);
    words.push(0xf940_040a);
    push_u64_x9(&mut words, template.required_memory_words)?;
    words.push(0xeb09_015f);
    push_guard_branch(&mut words, &mut guard_branches, 0x5400_0003);
    for live_in in template.live_ins {
        push_indexed_memory_guard(
            &mut words,
            &mut guard_branches,
            live_in.address,
            live_in.value,
        );
    }
    words.push(0x3941_3009);
    push_guard_branch(&mut words, &mut guard_branches, 0x3500_0009);
    push_fused_no_operation_crazy_commit(&mut words, template);
    let guard_miss = words.len();
    words.extend_from_slice(&[0x5280_0020, 0xd65f_03c0]);
    patch_guard_branches(&mut words, &guard_branches, guard_miss)?;
    Some(encode_words(&words))
}

fn push_fused_no_operation_crazy_commit(
    words: &mut Vec<u32>,
    template: DirectFusedNoOperationCrazyTemplate<'_>,
) {
    words.extend_from_slice(&[
        movz_w10(template.no_operation.encrypted_address),
        movk_w10_high(template.no_operation.encrypted_address),
        0x8b0a_090a,
        movz_w9(template.no_operation.encrypted_value),
        movk_w9_high(template.no_operation.encrypted_value),
        0xb900_0149,
        movz_w10(template.crazy.data_address),
        movk_w10_high(template.crazy.data_address),
        0x8b0a_090a,
        movz_w9(template.crazy.data_value),
        movk_w9_high(template.crazy.data_value),
        0xb900_0149,
        movz_w10(template.crazy.encrypted_address),
        movk_w10_high(template.crazy.encrypted_address),
        0x8b0a_090a,
        movz_w9(template.crazy.encrypted_value),
        movk_w9_high(template.crazy.encrypted_value),
        0xb900_0149,
        movz_w9(template.crazy.accumulator),
        movk_w9_high(template.crazy.accumulator),
        0xb900_4009,
        movz_w9(template.crazy.next_code_pointer),
        movk_w9_high(template.crazy.next_code_pointer),
        0xb900_4409,
        movz_w9(template.crazy.next_data_pointer),
        movk_w9_high(template.crazy.next_data_pointer),
        0xb900_4809,
        0x2a1f_03e0,
        0xd65f_03c0,
    ]);
}

/// Encodes one atomic two-step no-operation/no-operation fused region.
#[must_use]
pub(super) fn fused_no_operation_pair_code(
    template: DirectFusedNoOperationPairTemplate<'_>,
) -> Option<Vec<u8>> {
    let mut words = Vec::with_capacity(96);
    let mut guard_branches =
        Vec::with_capacity(template.live_ins.len().saturating_add(10));
    push_observation_guards(
        &mut words,
        &mut guard_branches,
        template.observation,
    )?;
    words.push(0xf940_0008);
    push_guard_branch(&mut words, &mut guard_branches, 0xb400_0008);
    words.push(0xf940_040a);
    push_u64_x9(&mut words, template.required_memory_words)?;
    words.push(0xeb09_015f);
    push_guard_branch(&mut words, &mut guard_branches, 0x5400_0003);
    for live_in in template.live_ins {
        push_indexed_memory_guard(
            &mut words,
            &mut guard_branches,
            live_in.address,
            live_in.value,
        );
    }
    words.push(0x3941_3009);
    push_guard_branch(&mut words, &mut guard_branches, 0x3500_0009);
    push_fused_no_operation_pair_commit(&mut words, template);
    let guard_miss = words.len();
    words.extend_from_slice(&[0x5280_0020, 0xd65f_03c0]);
    patch_guard_branches(&mut words, &guard_branches, guard_miss)?;
    Some(encode_words(&words))
}

fn push_fused_no_operation_pair_commit(
    words: &mut Vec<u32>,
    template: DirectFusedNoOperationPairTemplate<'_>,
) {
    words.extend_from_slice(&[
        movz_w10(template.first.encrypted_address),
        movk_w10_high(template.first.encrypted_address),
        0x8b0a_090a,
        movz_w9(template.first.encrypted_value),
        movk_w9_high(template.first.encrypted_value),
        0xb900_0149,
        movz_w10(template.second.encrypted_address),
        movk_w10_high(template.second.encrypted_address),
        0x8b0a_090a,
        movz_w9(template.second.encrypted_value),
        movk_w9_high(template.second.encrypted_value),
        0xb900_0149,
        movz_w9(template.second.next_code_pointer),
        movk_w9_high(template.second.next_code_pointer),
        0xb900_4409,
        movz_w9(template.second.next_data_pointer),
        movk_w9_high(template.second.next_data_pointer),
        0xb900_4809,
        0x2a1f_03e0,
        0xd65f_03c0,
    ]);
}

/// Encodes one atomic two-step no-operation/rotate fused region.
#[must_use]
pub(super) fn fused_no_operation_rotate_code(
    template: DirectFusedNoOperationRotateTemplate<'_>,
) -> Option<Vec<u8>> {
    let mut words = Vec::with_capacity(112);
    let mut guard_branches =
        Vec::with_capacity(template.live_ins.len().saturating_add(10));
    push_observation_guards(
        &mut words,
        &mut guard_branches,
        template.observation,
    )?;
    words.push(0xf940_0008);
    push_guard_branch(&mut words, &mut guard_branches, 0xb400_0008);
    words.push(0xf940_040a);
    push_u64_x9(&mut words, template.required_memory_words)?;
    words.push(0xeb09_015f);
    push_guard_branch(&mut words, &mut guard_branches, 0x5400_0003);
    for live_in in template.live_ins {
        push_indexed_memory_guard(
            &mut words,
            &mut guard_branches,
            live_in.address,
            live_in.value,
        );
    }
    words.push(0x3941_3009);
    push_guard_branch(&mut words, &mut guard_branches, 0x3500_0009);
    push_fused_no_operation_rotate_commit(&mut words, template);
    let guard_miss = words.len();
    words.extend_from_slice(&[0x5280_0020, 0xd65f_03c0]);
    patch_guard_branches(&mut words, &guard_branches, guard_miss)?;
    Some(encode_words(&words))
}

fn push_fused_no_operation_rotate_commit(
    words: &mut Vec<u32>,
    template: DirectFusedNoOperationRotateTemplate<'_>,
) {
    words.extend_from_slice(&[
        movz_w10(template.no_operation.encrypted_address),
        movk_w10_high(template.no_operation.encrypted_address),
        0x8b0a_090a,
        movz_w9(template.no_operation.encrypted_value),
        movk_w9_high(template.no_operation.encrypted_value),
        0xb900_0149,
        movz_w10(template.rotate.data_address),
        movk_w10_high(template.rotate.data_address),
        0x8b0a_090a,
        movz_w9(template.rotate.data_value),
        movk_w9_high(template.rotate.data_value),
        0xb900_0149,
        movz_w10(template.rotate.encrypted_address),
        movk_w10_high(template.rotate.encrypted_address),
        0x8b0a_090a,
        movz_w9(template.rotate.encrypted_value),
        movk_w9_high(template.rotate.encrypted_value),
        0xb900_0149,
        movz_w9(template.rotate.accumulator),
        movk_w9_high(template.rotate.accumulator),
        0xb900_4009,
        movz_w9(template.rotate.next_code_pointer),
        movk_w9_high(template.rotate.next_code_pointer),
        0xb900_4409,
        movz_w9(template.rotate.next_data_pointer),
        movk_w9_high(template.rotate.next_data_pointer),
        0xb900_4809,
        0x2a1f_03e0,
        0xd65f_03c0,
    ]);
}

/// Encodes one atomic two-step no-operation/output fused region.
#[must_use]
pub(super) fn fused_no_operation_output_code(
    template: DirectFusedNoOperationOutputTemplate<'_>,
) -> Option<Vec<u8>> {
    let mut words = Vec::with_capacity(112);
    let mut guard_branches =
        Vec::with_capacity(template.live_ins.len().saturating_add(12));
    push_observation_guards(
        &mut words,
        &mut guard_branches,
        template.observation,
    )?;
    words.push(0xf940_0008);
    push_guard_branch(&mut words, &mut guard_branches, 0xb400_0008);
    words.push(0xf940_040a);
    push_u64_x9(&mut words, template.required_memory_words)?;
    words.push(0xeb09_015f);
    push_guard_branch(&mut words, &mut guard_branches, 0x5400_0003);
    for live_in in template.live_ins {
        push_indexed_memory_guard(
            &mut words,
            &mut guard_branches,
            live_in.address,
            live_in.value,
        );
    }
    words.push(0x3941_3009);
    push_guard_branch(&mut words, &mut guard_branches, 0x3500_0009);
    words.push(0xf940_140b);
    push_guard_branch(&mut words, &mut guard_branches, 0xb400_000b);
    words.push(0xf940_180c);
    push_u64_x9(&mut words, template.output.output_index)?;
    words.push(0xeb09_019f);
    push_guard_branch(&mut words, &mut guard_branches, 0x5400_0009);
    push_fused_no_operation_output_commit(&mut words, template)?;
    let guard_miss = words.len();
    words.extend_from_slice(&[0x5280_0020, 0xd65f_03c0]);
    patch_guard_branches(&mut words, &guard_branches, guard_miss)?;
    Some(encode_words(&words))
}

fn push_fused_no_operation_output_commit(
    words: &mut Vec<u32>,
    template: DirectFusedNoOperationOutputTemplate<'_>,
) -> Option<()> {
    words.extend_from_slice(&[
        movz_w10(template.no_operation.encrypted_address),
        movk_w10_high(template.no_operation.encrypted_address),
        0x8b0a_090a,
        movz_w9(template.no_operation.encrypted_value),
        movk_w9_high(template.no_operation.encrypted_value),
        0xb900_0149,
        movz_w10(template.output.encrypted_address),
        movk_w10_high(template.output.encrypted_address),
        0x8b0a_090a,
        movz_w9(template.output.encrypted_value),
        movk_w9_high(template.output.encrypted_value),
        0xb900_0149,
        movz_w9(template.output.next_code_pointer),
        movk_w9_high(template.output.next_code_pointer),
        0xb900_4409,
        movz_w9(template.output.next_data_pointer),
        movk_w9_high(template.output.next_data_pointer),
        0xb900_4809,
        0xf940_1c0a,
        0x8b0a_016b,
        movz_w9(u32::from(template.output.output_byte)),
        0x3900_0169,
    ]);
    push_u64_x9(words, template.output.next_output_len)?;
    words.extend_from_slice(&[0xf900_1c09, 0x2a1f_03e0, 0xd65f_03c0]);
    Some(())
}

fn push_input_guard(
    words: &mut Vec<u32>,
    guard_branches: &mut Vec<usize>,
    input: malbolge::TraceInput,
    input_index: u64,
) -> Option<()> {
    match input {
        malbolge::TraceInput::Byte(byte) => {
            words.push(0xf940_080b);
            push_guard_branch(words, guard_branches, 0xb400_000b);
            words.push(0xf940_0c0c);
            push_u64_x9(words, input_index)?;
            words.push(0xeb09_019f);
            push_guard_branch(words, guard_branches, 0x5400_0009);
            words.extend_from_slice(&[
                0x8b09_016b,
                0x3940_016d,
                movz_w9(u32::from(byte)),
                0x6b09_01bf,
            ]);
            push_guard_branch(words, guard_branches, 0x5400_0001);
        },
        malbolge::TraceInput::EndOfInput => {
            words.push(0xf940_0c0c);
            push_u64_x9(words, input_index)?;
            words.push(0xeb09_019f);
            push_guard_branch(words, guard_branches, 0x5400_0001);
        },
    }
    Some(())
}

/// Encodes one atomic code-write/input fused region.
#[must_use]
pub(super) fn fused_code_write_input_code(
    template: &DirectFusedCodeWriteInputTemplate<'_>,
) -> Option<Vec<u8>> {
    let mut words = Vec::with_capacity(128);
    let mut guard_branches =
        Vec::with_capacity(template.live_ins.len().saturating_add(14));
    push_observation_guards(
        &mut words,
        &mut guard_branches,
        template.observation,
    )?;
    words.push(0xf940_0008);
    push_guard_branch(&mut words, &mut guard_branches, 0xb400_0008);
    words.push(0xf940_040a);
    push_u64_x9(&mut words, template.required_memory_words)?;
    words.push(0xeb09_015f);
    push_guard_branch(&mut words, &mut guard_branches, 0x5400_0003);
    for live_in in template.live_ins {
        push_indexed_memory_guard(
            &mut words,
            &mut guard_branches,
            live_in.address,
            live_in.value,
        );
    }
    words.push(0x3941_3009);
    push_guard_branch(&mut words, &mut guard_branches, 0x3500_0009);
    push_input_guard(
        &mut words,
        &mut guard_branches,
        template.input_evidence,
        template.input_index,
    )?;
    push_fused_code_write_input_commit(&mut words, template)?;
    let guard_miss = words.len();
    words.extend_from_slice(&[0x5280_0020, 0xd65f_03c0]);
    patch_guard_branches(&mut words, &guard_branches, guard_miss)?;
    Some(encode_words(&words))
}

fn push_fused_code_write_input_commit(
    words: &mut Vec<u32>,
    template: &DirectFusedCodeWriteInputTemplate<'_>,
) -> Option<()> {
    for (address, value) in [
        (
            template.first.encrypted_address,
            template.first.encrypted_value,
        ),
        (
            template.input.encrypted_address,
            template.input.encrypted_value,
        ),
    ] {
        words.extend_from_slice(&[
            movz_w10(address),
            movk_w10_high(address),
            0x8b0a_090a,
            movz_w9(value),
            movk_w9_high(value),
            0xb900_0149,
        ]);
    }
    words.extend_from_slice(&[
        movz_w9(template.input.accumulator),
        movk_w9_high(template.input.accumulator),
        0xb900_4009,
        movz_w9(template.input.next_code_pointer),
        movk_w9_high(template.input.next_code_pointer),
        0xb900_4409,
        movz_w9(template.input.next_data_pointer),
        movk_w9_high(template.input.next_data_pointer),
        0xb900_4809,
    ]);
    push_u64_x9(words, template.input.next_input_consumed)?;
    words.extend_from_slice(&[0xf900_1009, 0x2a1f_03e0, 0xd65f_03c0]);
    Some(())
}

/// Encodes one atomic data-write/input fused region.
#[must_use]
pub(super) fn fused_data_write_input_code(
    template: &DirectFusedDataWriteInputTemplate<'_>,
) -> Option<Vec<u8>> {
    let mut words = Vec::with_capacity(144);
    let mut guard_branches =
        Vec::with_capacity(template.live_ins.len().saturating_add(16));
    push_observation_guards(
        &mut words,
        &mut guard_branches,
        template.observation,
    )?;
    words.push(0xf940_0008);
    push_guard_branch(&mut words, &mut guard_branches, 0xb400_0008);
    words.push(0xf940_040a);
    push_u64_x9(&mut words, template.required_memory_words)?;
    words.push(0xeb09_015f);
    push_guard_branch(&mut words, &mut guard_branches, 0x5400_0003);
    for live_in in template.live_ins {
        push_indexed_memory_guard(
            &mut words,
            &mut guard_branches,
            live_in.address,
            live_in.value,
        );
    }
    words.push(0x3941_3009);
    push_guard_branch(&mut words, &mut guard_branches, 0x3500_0009);
    push_input_guard(
        &mut words,
        &mut guard_branches,
        template.input_evidence,
        template.input_index,
    )?;
    push_fused_data_write_input_commit(&mut words, template)?;
    let guard_miss = words.len();
    words.extend_from_slice(&[0x5280_0020, 0xd65f_03c0]);
    patch_guard_branches(&mut words, &guard_branches, guard_miss)?;
    Some(encode_words(&words))
}

fn push_fused_data_write_input_commit(
    words: &mut Vec<u32>,
    template: &DirectFusedDataWriteInputTemplate<'_>,
) -> Option<()> {
    for (address, value) in [
        (template.first.data_address, template.first.data_value),
        (
            template.first.encrypted_address,
            template.first.encrypted_value,
        ),
        (
            template.input.encrypted_address,
            template.input.encrypted_value,
        ),
    ] {
        words.extend_from_slice(&[
            movz_w10(address),
            movk_w10_high(address),
            0x8b0a_090a,
            movz_w9(value),
            movk_w9_high(value),
            0xb900_0149,
        ]);
    }
    words.extend_from_slice(&[
        movz_w9(template.input.accumulator),
        movk_w9_high(template.input.accumulator),
        0xb900_4009,
        movz_w9(template.input.next_code_pointer),
        movk_w9_high(template.input.next_code_pointer),
        0xb900_4409,
        movz_w9(template.input.next_data_pointer),
        movk_w9_high(template.input.next_data_pointer),
        0xb900_4809,
    ]);
    push_u64_x9(words, template.input.next_input_consumed)?;
    words.extend_from_slice(&[0xf900_1009, 0x2a1f_03e0, 0xd65f_03c0]);
    Some(())
}

/// Encodes one atomic input/code-write fused region.
#[must_use]
pub(super) fn fused_input_code_write_code(
    template: &DirectFusedInputCodeWriteTemplate<'_>,
) -> Option<Vec<u8>> {
    let mut words = Vec::with_capacity(128);
    let mut guard_branches =
        Vec::with_capacity(template.live_ins.len().saturating_add(14));
    push_observation_guards(
        &mut words,
        &mut guard_branches,
        template.observation,
    )?;
    words.push(0xf940_0008);
    push_guard_branch(&mut words, &mut guard_branches, 0xb400_0008);
    words.push(0xf940_040a);
    push_u64_x9(&mut words, template.required_memory_words)?;
    words.push(0xeb09_015f);
    push_guard_branch(&mut words, &mut guard_branches, 0x5400_0003);
    for live_in in template.live_ins {
        push_indexed_memory_guard(
            &mut words,
            &mut guard_branches,
            live_in.address,
            live_in.value,
        );
    }
    words.push(0x3941_3009);
    push_guard_branch(&mut words, &mut guard_branches, 0x3500_0009);
    push_input_guard(
        &mut words,
        &mut guard_branches,
        template.input_evidence,
        template.input_index,
    )?;
    push_fused_input_code_write_commit(&mut words, template)?;
    let guard_miss = words.len();
    words.extend_from_slice(&[0x5280_0020, 0xd65f_03c0]);
    patch_guard_branches(&mut words, &guard_branches, guard_miss)?;
    Some(encode_words(&words))
}

fn push_fused_input_code_write_commit(
    words: &mut Vec<u32>,
    template: &DirectFusedInputCodeWriteTemplate<'_>,
) -> Option<()> {
    for (address, value) in [
        (
            template.input.encrypted_address,
            template.input.encrypted_value,
        ),
        (
            template.second.encrypted_address,
            template.second.encrypted_value,
        ),
    ] {
        words.extend_from_slice(&[
            movz_w10(address),
            movk_w10_high(address),
            0x8b0a_090a,
            movz_w9(value),
            movk_w9_high(value),
            0xb900_0149,
        ]);
    }
    words.extend_from_slice(&[
        movz_w9(template.input.accumulator),
        movk_w9_high(template.input.accumulator),
        0xb900_4009,
        movz_w9(template.second.next_code_pointer),
        movk_w9_high(template.second.next_code_pointer),
        0xb900_4409,
        movz_w9(template.second.next_data_pointer),
        movk_w9_high(template.second.next_data_pointer),
        0xb900_4809,
    ]);
    push_u64_x9(words, template.input.next_input_consumed)?;
    words.extend_from_slice(&[0xf900_1009, 0x2a1f_03e0, 0xd65f_03c0]);
    Some(())
}

/// Encodes one atomic input/data-write fused region.
#[must_use]
pub(super) fn fused_input_data_write_code(
    template: &DirectFusedInputDataWriteTemplate<'_>,
) -> Option<Vec<u8>> {
    let mut words = Vec::with_capacity(144);
    let mut guard_branches =
        Vec::with_capacity(template.live_ins.len().saturating_add(16));
    push_observation_guards(
        &mut words,
        &mut guard_branches,
        template.observation,
    )?;
    words.push(0xf940_0008);
    push_guard_branch(&mut words, &mut guard_branches, 0xb400_0008);
    words.push(0xf940_040a);
    push_u64_x9(&mut words, template.required_memory_words)?;
    words.push(0xeb09_015f);
    push_guard_branch(&mut words, &mut guard_branches, 0x5400_0003);
    for live_in in template.live_ins {
        push_indexed_memory_guard(
            &mut words,
            &mut guard_branches,
            live_in.address,
            live_in.value,
        );
    }
    words.push(0x3941_3009);
    push_guard_branch(&mut words, &mut guard_branches, 0x3500_0009);
    push_input_guard(
        &mut words,
        &mut guard_branches,
        template.input_evidence,
        template.input_index,
    )?;
    push_fused_input_data_write_commit(&mut words, template)?;
    let guard_miss = words.len();
    words.extend_from_slice(&[0x5280_0020, 0xd65f_03c0]);
    patch_guard_branches(&mut words, &guard_branches, guard_miss)?;
    Some(encode_words(&words))
}

fn push_fused_input_data_write_commit(
    words: &mut Vec<u32>,
    template: &DirectFusedInputDataWriteTemplate<'_>,
) -> Option<()> {
    for (address, value) in [
        (
            template.input.encrypted_address,
            template.input.encrypted_value,
        ),
        (template.second.data_address, template.second.data_value),
        (
            template.second.encrypted_address,
            template.second.encrypted_value,
        ),
    ] {
        words.extend_from_slice(&[
            movz_w10(address),
            movk_w10_high(address),
            0x8b0a_090a,
            movz_w9(value),
            movk_w9_high(value),
            0xb900_0149,
        ]);
    }
    words.extend_from_slice(&[
        movz_w9(template.second.accumulator),
        movk_w9_high(template.second.accumulator),
        0xb900_4009,
        movz_w9(template.second.next_code_pointer),
        movk_w9_high(template.second.next_code_pointer),
        0xb900_4409,
        movz_w9(template.second.next_data_pointer),
        movk_w9_high(template.second.next_data_pointer),
        0xb900_4809,
    ]);
    push_u64_x9(words, template.input.next_input_consumed)?;
    words.extend_from_slice(&[0xf900_1009, 0x2a1f_03e0, 0xd65f_03c0]);
    Some(())
}

/// Encodes one atomic input/output fused region.
#[must_use]
pub(super) fn fused_input_output_code(
    template: &DirectFusedInputOutputTemplate<'_>,
) -> Option<Vec<u8>> {
    let mut words = Vec::with_capacity(160);
    let mut guard_branches =
        Vec::with_capacity(template.live_ins.len().saturating_add(18));
    push_observation_guards(
        &mut words,
        &mut guard_branches,
        template.observation,
    )?;
    words.push(0xf940_0008);
    push_guard_branch(&mut words, &mut guard_branches, 0xb400_0008);
    words.push(0xf940_040a);
    push_u64_x9(&mut words, template.required_memory_words)?;
    words.push(0xeb09_015f);
    push_guard_branch(&mut words, &mut guard_branches, 0x5400_0003);
    for live_in in template.live_ins {
        push_indexed_memory_guard(
            &mut words,
            &mut guard_branches,
            live_in.address,
            live_in.value,
        );
    }
    words.push(0x3941_3009);
    push_guard_branch(&mut words, &mut guard_branches, 0x3500_0009);
    push_input_guard(
        &mut words,
        &mut guard_branches,
        template.input_evidence,
        template.input_index,
    )?;
    words.push(0xf940_140b);
    push_guard_branch(&mut words, &mut guard_branches, 0xb400_000b);
    words.push(0xf940_180c);
    push_u64_x9(&mut words, template.output.output_index)?;
    words.push(0xeb09_019f);
    push_guard_branch(&mut words, &mut guard_branches, 0x5400_0009);
    push_fused_input_output_commit(&mut words, template)?;
    let guard_miss = words.len();
    words.extend_from_slice(&[0x5280_0020, 0xd65f_03c0]);
    patch_guard_branches(&mut words, &guard_branches, guard_miss)?;
    Some(encode_words(&words))
}

fn push_fused_input_output_commit(
    words: &mut Vec<u32>,
    template: &DirectFusedInputOutputTemplate<'_>,
) -> Option<()> {
    for (address, value) in [
        (
            template.input.encrypted_address,
            template.input.encrypted_value,
        ),
        (
            template.output.encrypted_address,
            template.output.encrypted_value,
        ),
    ] {
        words.extend_from_slice(&[
            movz_w10(address),
            movk_w10_high(address),
            0x8b0a_090a,
            movz_w9(value),
            movk_w9_high(value),
            0xb900_0149,
        ]);
    }
    words.extend_from_slice(&[
        movz_w9(template.input.accumulator),
        movk_w9_high(template.input.accumulator),
        0xb900_4009,
        movz_w9(template.output.next_code_pointer),
        movk_w9_high(template.output.next_code_pointer),
        0xb900_4409,
        movz_w9(template.output.next_data_pointer),
        movk_w9_high(template.output.next_data_pointer),
        0xb900_4809,
    ]);
    push_u64_x9(words, template.input.next_input_consumed)?;
    words.push(0xf900_1009);
    words.push(0xf940_140b);
    push_u64_x9(words, template.output.output_index)?;
    words.extend_from_slice(&[
        0x8b09_016b,
        movz_w9(u32::from(template.output.output_byte)),
        0x3900_0169,
    ]);
    push_u64_x9(words, template.output.next_output_len)?;
    words.extend_from_slice(&[0xf900_1c09, 0x2a1f_03e0, 0xd65f_03c0]);
    Some(())
}

/// Encodes one atomic two-step input/input fused region.
#[must_use]
pub(super) fn fused_input_pair_code(
    template: &DirectFusedInputPairTemplate<'_>,
) -> Option<Vec<u8>> {
    let mut words = Vec::with_capacity(152);
    let mut guard_branches =
        Vec::with_capacity(template.live_ins.len().saturating_add(18));
    push_observation_guards(
        &mut words,
        &mut guard_branches,
        template.observation,
    )?;
    words.push(0xf940_0008);
    push_guard_branch(&mut words, &mut guard_branches, 0xb400_0008);
    words.push(0xf940_040a);
    push_u64_x9(&mut words, template.required_memory_words)?;
    words.push(0xeb09_015f);
    push_guard_branch(&mut words, &mut guard_branches, 0x5400_0003);
    for live_in in template.live_ins {
        push_indexed_memory_guard(
            &mut words,
            &mut guard_branches,
            live_in.address,
            live_in.value,
        );
    }
    words.push(0x3941_3009);
    push_guard_branch(&mut words, &mut guard_branches, 0x3500_0009);
    push_input_guard(
        &mut words,
        &mut guard_branches,
        template.first_input,
        template.first_input_index,
    )?;
    push_input_guard(
        &mut words,
        &mut guard_branches,
        template.second_input,
        template.second_input_index,
    )?;
    push_fused_input_pair_commit(&mut words, template)?;
    let guard_miss = words.len();
    words.extend_from_slice(&[0x5280_0020, 0xd65f_03c0]);
    patch_guard_branches(&mut words, &guard_branches, guard_miss)?;
    Some(encode_words(&words))
}

fn push_fused_input_pair_commit(
    words: &mut Vec<u32>,
    template: &DirectFusedInputPairTemplate<'_>,
) -> Option<()> {
    for input in [template.first, template.second] {
        words.extend_from_slice(&[
            movz_w10(input.encrypted_address),
            movk_w10_high(input.encrypted_address),
            0x8b0a_090a,
            movz_w9(input.encrypted_value),
            movk_w9_high(input.encrypted_value),
            0xb900_0149,
        ]);
    }
    words.extend_from_slice(&[
        movz_w9(template.second.accumulator),
        movk_w9_high(template.second.accumulator),
        0xb900_4009,
        movz_w9(template.second.next_code_pointer),
        movk_w9_high(template.second.next_code_pointer),
        0xb900_4409,
        movz_w9(template.second.next_data_pointer),
        movk_w9_high(template.second.next_data_pointer),
        0xb900_4809,
    ]);
    push_u64_x9(words, template.second.next_input_consumed)?;
    words.extend_from_slice(&[0xf900_1009, 0x2a1f_03e0, 0xd65f_03c0]);
    Some(())
}

/// Encodes one atomic output/no-operation fused region.
#[must_use]
pub(super) fn fused_output_no_operation_code(
    template: DirectFusedNoOperationOutputTemplate<'_>,
) -> Option<Vec<u8>> {
    let mut words = Vec::with_capacity(112);
    let mut guard_branches =
        Vec::with_capacity(template.live_ins.len().saturating_add(12));
    push_observation_guards(
        &mut words,
        &mut guard_branches,
        template.observation,
    )?;
    words.push(0xf940_0008);
    push_guard_branch(&mut words, &mut guard_branches, 0xb400_0008);
    words.push(0xf940_040a);
    push_u64_x9(&mut words, template.required_memory_words)?;
    words.push(0xeb09_015f);
    push_guard_branch(&mut words, &mut guard_branches, 0x5400_0003);
    for live_in in template.live_ins {
        push_indexed_memory_guard(
            &mut words,
            &mut guard_branches,
            live_in.address,
            live_in.value,
        );
    }
    words.push(0x3941_3009);
    push_guard_branch(&mut words, &mut guard_branches, 0x3500_0009);
    words.push(0xf940_140b);
    push_guard_branch(&mut words, &mut guard_branches, 0xb400_000b);
    words.push(0xf940_180c);
    push_u64_x9(&mut words, template.output.output_index)?;
    words.push(0xeb09_019f);
    push_guard_branch(&mut words, &mut guard_branches, 0x5400_0009);
    push_fused_output_no_operation_commit(&mut words, template)?;
    let guard_miss = words.len();
    words.extend_from_slice(&[0x5280_0020, 0xd65f_03c0]);
    patch_guard_branches(&mut words, &guard_branches, guard_miss)?;
    Some(encode_words(&words))
}

fn push_fused_output_no_operation_commit(
    words: &mut Vec<u32>,
    template: DirectFusedNoOperationOutputTemplate<'_>,
) -> Option<()> {
    for (address, value) in [
        (
            template.output.encrypted_address,
            template.output.encrypted_value,
        ),
        (
            template.no_operation.encrypted_address,
            template.no_operation.encrypted_value,
        ),
    ] {
        words.extend_from_slice(&[
            movz_w10(address),
            movk_w10_high(address),
            0x8b0a_090a,
            movz_w9(value),
            movk_w9_high(value),
            0xb900_0149,
        ]);
    }
    words.push(0xf940_140b);
    push_u64_x9(words, template.output.output_index)?;
    words.extend_from_slice(&[
        0x8b09_016b,
        movz_w9(u32::from(template.output.output_byte)),
        0x3900_0169,
    ]);
    push_u64_x9(words, template.output.next_output_len)?;
    words.push(0xf900_1c09);
    words.extend_from_slice(&[
        movz_w9(template.no_operation.next_code_pointer),
        movk_w9_high(template.no_operation.next_code_pointer),
        0xb900_4409,
        movz_w9(template.no_operation.next_data_pointer),
        movk_w9_high(template.no_operation.next_data_pointer),
        0xb900_4809,
        0x2a1f_03e0,
        0xd65f_03c0,
    ]);
    Some(())
}

/// Encodes one atomic output/crazy fused region.
#[must_use]
pub(super) fn fused_output_crazy_code(
    template: super::direct::DirectFusedCrazyOutputTemplate<'_>,
) -> Option<Vec<u8>> {
    let mut words = Vec::with_capacity(128);
    let mut guard_branches =
        Vec::with_capacity(template.live_ins.len().saturating_add(12));
    push_observation_guards(
        &mut words,
        &mut guard_branches,
        template.observation,
    )?;
    words.push(0xf940_0008);
    push_guard_branch(&mut words, &mut guard_branches, 0xb400_0008);
    words.push(0xf940_040a);
    push_u64_x9(&mut words, template.required_memory_words)?;
    words.push(0xeb09_015f);
    push_guard_branch(&mut words, &mut guard_branches, 0x5400_0003);
    for live_in in template.live_ins {
        push_indexed_memory_guard(
            &mut words,
            &mut guard_branches,
            live_in.address,
            live_in.value,
        );
    }
    words.push(0x3941_3009);
    push_guard_branch(&mut words, &mut guard_branches, 0x3500_0009);
    words.push(0xf940_140b);
    push_guard_branch(&mut words, &mut guard_branches, 0xb400_000b);
    words.push(0xf940_180c);
    push_u64_x9(&mut words, template.output.output_index)?;
    words.push(0xeb09_019f);
    push_guard_branch(&mut words, &mut guard_branches, 0x5400_0009);
    push_fused_output_crazy_commit(&mut words, template)?;
    let guard_miss = words.len();
    words.extend_from_slice(&[0x5280_0020, 0xd65f_03c0]);
    patch_guard_branches(&mut words, &guard_branches, guard_miss)?;
    Some(encode_words(&words))
}

fn push_fused_output_crazy_commit(
    words: &mut Vec<u32>,
    template: super::direct::DirectFusedCrazyOutputTemplate<'_>,
) -> Option<()> {
    for (address, value) in [
        (
            template.output.encrypted_address,
            template.output.encrypted_value,
        ),
        (template.crazy.data_address, template.crazy.data_value),
        (
            template.crazy.encrypted_address,
            template.crazy.encrypted_value,
        ),
    ] {
        words.extend_from_slice(&[
            movz_w10(address),
            movk_w10_high(address),
            0x8b0a_090a,
            movz_w9(value),
            movk_w9_high(value),
            0xb900_0149,
        ]);
    }
    words.push(0xf940_140b);
    push_u64_x9(words, template.output.output_index)?;
    words.extend_from_slice(&[
        0x8b09_016b,
        movz_w9(u32::from(template.output.output_byte)),
        0x3900_0169,
    ]);
    push_u64_x9(words, template.output.next_output_len)?;
    words.push(0xf900_1c09);
    words.extend_from_slice(&[
        movz_w9(template.crazy.accumulator),
        movk_w9_high(template.crazy.accumulator),
        0xb900_4009,
        movz_w9(template.crazy.next_code_pointer),
        movk_w9_high(template.crazy.next_code_pointer),
        0xb900_4409,
        movz_w9(template.crazy.next_data_pointer),
        movk_w9_high(template.crazy.next_data_pointer),
        0xb900_4809,
        0x2a1f_03e0,
        0xd65f_03c0,
    ]);
    Some(())
}

/// Encodes one atomic output/rotate fused region.
#[must_use]
pub(super) fn fused_output_rotate_code(
    template: DirectFusedRotateOutputTemplate<'_>,
) -> Option<Vec<u8>> {
    let mut words = Vec::with_capacity(128);
    let mut guard_branches =
        Vec::with_capacity(template.live_ins.len().saturating_add(12));
    push_observation_guards(
        &mut words,
        &mut guard_branches,
        template.observation,
    )?;
    words.push(0xf940_0008);
    push_guard_branch(&mut words, &mut guard_branches, 0xb400_0008);
    words.push(0xf940_040a);
    push_u64_x9(&mut words, template.required_memory_words)?;
    words.push(0xeb09_015f);
    push_guard_branch(&mut words, &mut guard_branches, 0x5400_0003);
    for live_in in template.live_ins {
        push_indexed_memory_guard(
            &mut words,
            &mut guard_branches,
            live_in.address,
            live_in.value,
        );
    }
    words.push(0x3941_3009);
    push_guard_branch(&mut words, &mut guard_branches, 0x3500_0009);
    words.push(0xf940_140b);
    push_guard_branch(&mut words, &mut guard_branches, 0xb400_000b);
    words.push(0xf940_180c);
    push_u64_x9(&mut words, template.output.output_index)?;
    words.push(0xeb09_019f);
    push_guard_branch(&mut words, &mut guard_branches, 0x5400_0009);
    push_fused_output_rotate_commit(&mut words, template)?;
    let guard_miss = words.len();
    words.extend_from_slice(&[0x5280_0020, 0xd65f_03c0]);
    patch_guard_branches(&mut words, &guard_branches, guard_miss)?;
    Some(encode_words(&words))
}

fn push_fused_output_rotate_commit(
    words: &mut Vec<u32>,
    template: DirectFusedRotateOutputTemplate<'_>,
) -> Option<()> {
    for (address, value) in [
        (
            template.output.encrypted_address,
            template.output.encrypted_value,
        ),
        (template.rotate.data_address, template.rotate.data_value),
        (
            template.rotate.encrypted_address,
            template.rotate.encrypted_value,
        ),
    ] {
        words.extend_from_slice(&[
            movz_w10(address),
            movk_w10_high(address),
            0x8b0a_090a,
            movz_w9(value),
            movk_w9_high(value),
            0xb900_0149,
        ]);
    }
    words.push(0xf940_140b);
    push_u64_x9(words, template.output.output_index)?;
    words.extend_from_slice(&[
        0x8b09_016b,
        movz_w9(u32::from(template.output.output_byte)),
        0x3900_0169,
    ]);
    push_u64_x9(words, template.output.next_output_len)?;
    words.push(0xf900_1c09);
    words.extend_from_slice(&[
        movz_w9(template.rotate.accumulator),
        movk_w9_high(template.rotate.accumulator),
        0xb900_4009,
        movz_w9(template.rotate.next_code_pointer),
        movk_w9_high(template.rotate.next_code_pointer),
        0xb900_4409,
        movz_w9(template.rotate.next_data_pointer),
        movk_w9_high(template.rotate.next_data_pointer),
        0xb900_4809,
        0x2a1f_03e0,
        0xd65f_03c0,
    ]);
    Some(())
}

/// Encodes one atomic output/input fused region.
#[must_use]
pub(super) fn fused_output_input_code(
    template: &DirectFusedInputOutputTemplate<'_>,
) -> Option<Vec<u8>> {
    let mut words = Vec::with_capacity(160);
    let mut guard_branches =
        Vec::with_capacity(template.live_ins.len().saturating_add(18));
    push_observation_guards(
        &mut words,
        &mut guard_branches,
        template.observation,
    )?;
    words.push(0xf940_0008);
    push_guard_branch(&mut words, &mut guard_branches, 0xb400_0008);
    words.push(0xf940_040a);
    push_u64_x9(&mut words, template.required_memory_words)?;
    words.push(0xeb09_015f);
    push_guard_branch(&mut words, &mut guard_branches, 0x5400_0003);
    for live_in in template.live_ins {
        push_indexed_memory_guard(
            &mut words,
            &mut guard_branches,
            live_in.address,
            live_in.value,
        );
    }
    words.push(0x3941_3009);
    push_guard_branch(&mut words, &mut guard_branches, 0x3500_0009);
    words.push(0xf940_140b);
    push_guard_branch(&mut words, &mut guard_branches, 0xb400_000b);
    words.push(0xf940_180c);
    push_u64_x9(&mut words, template.output.output_index)?;
    words.push(0xeb09_019f);
    push_guard_branch(&mut words, &mut guard_branches, 0x5400_0009);
    push_input_guard(
        &mut words,
        &mut guard_branches,
        template.input_evidence,
        template.input_index,
    )?;
    push_fused_output_input_commit(&mut words, template)?;
    let guard_miss = words.len();
    words.extend_from_slice(&[0x5280_0020, 0xd65f_03c0]);
    patch_guard_branches(&mut words, &guard_branches, guard_miss)?;
    Some(encode_words(&words))
}

fn push_fused_output_input_commit(
    words: &mut Vec<u32>,
    template: &DirectFusedInputOutputTemplate<'_>,
) -> Option<()> {
    for (address, value) in [
        (
            template.output.encrypted_address,
            template.output.encrypted_value,
        ),
        (
            template.input.encrypted_address,
            template.input.encrypted_value,
        ),
    ] {
        words.extend_from_slice(&[
            movz_w10(address),
            movk_w10_high(address),
            0x8b0a_090a,
            movz_w9(value),
            movk_w9_high(value),
            0xb900_0149,
        ]);
    }
    words.push(0xf940_140b);
    push_u64_x9(words, template.output.output_index)?;
    words.extend_from_slice(&[
        0x8b09_016b,
        movz_w9(u32::from(template.output.output_byte)),
        0x3900_0169,
    ]);
    push_u64_x9(words, template.output.next_output_len)?;
    words.push(0xf900_1c09);
    words.extend_from_slice(&[
        movz_w9(template.input.accumulator),
        movk_w9_high(template.input.accumulator),
        0xb900_4009,
        movz_w9(template.input.next_code_pointer),
        movk_w9_high(template.input.next_code_pointer),
        0xb900_4409,
        movz_w9(template.input.next_data_pointer),
        movk_w9_high(template.input.next_data_pointer),
        0xb900_4809,
    ]);
    push_u64_x9(words, template.input.next_input_consumed)?;
    words.extend_from_slice(&[0xf900_1009, 0x2a1f_03e0, 0xd65f_03c0]);
    Some(())
}

/// Encodes one atomic two-step output/output fused region.
#[must_use]
pub(super) fn fused_output_pair_code(
    template: &DirectFusedOutputPairTemplate<'_>,
) -> Option<Vec<u8>> {
    let mut words = Vec::with_capacity(128);
    let mut guard_branches =
        Vec::with_capacity(template.live_ins.len().saturating_add(12));
    push_observation_guards(
        &mut words,
        &mut guard_branches,
        template.observation,
    )?;
    words.push(0xf940_0008);
    push_guard_branch(&mut words, &mut guard_branches, 0xb400_0008);
    words.push(0xf940_040a);
    push_u64_x9(&mut words, template.required_memory_words)?;
    words.push(0xeb09_015f);
    push_guard_branch(&mut words, &mut guard_branches, 0x5400_0003);
    for live_in in template.live_ins {
        push_indexed_memory_guard(
            &mut words,
            &mut guard_branches,
            live_in.address,
            live_in.value,
        );
    }
    words.push(0x3941_3009);
    push_guard_branch(&mut words, &mut guard_branches, 0x3500_0009);
    words.push(0xf940_140b);
    push_guard_branch(&mut words, &mut guard_branches, 0xb400_000b);
    words.push(0xf940_180c);
    push_u64_x9(&mut words, template.second.output_index)?;
    words.push(0xeb09_019f);
    push_guard_branch(&mut words, &mut guard_branches, 0x5400_0009);
    push_fused_output_pair_commit(&mut words, template)?;
    let guard_miss = words.len();
    words.extend_from_slice(&[0x5280_0020, 0xd65f_03c0]);
    patch_guard_branches(&mut words, &guard_branches, guard_miss)?;
    Some(encode_words(&words))
}

fn push_fused_output_pair_commit(
    words: &mut Vec<u32>,
    template: &DirectFusedOutputPairTemplate<'_>,
) -> Option<()> {
    for output in [template.first, template.second] {
        words.extend_from_slice(&[
            movz_w10(output.encrypted_address),
            movk_w10_high(output.encrypted_address),
            0x8b0a_090a,
            movz_w9(output.encrypted_value),
            movk_w9_high(output.encrypted_value),
            0xb900_0149,
        ]);
    }
    words.extend_from_slice(&[
        movz_w9(template.second.next_code_pointer),
        movk_w9_high(template.second.next_code_pointer),
        0xb900_4409,
        movz_w9(template.second.next_data_pointer),
        movk_w9_high(template.second.next_data_pointer),
        0xb900_4809,
    ]);
    for output in [template.first, template.second] {
        words.push(0xf940_140b);
        push_u64_x9(words, output.output_index)?;
        words.extend_from_slice(&[
            0x8b09_016b,
            movz_w9(u32::from(output.output_byte)),
            0x3900_0169,
        ]);
    }
    push_u64_x9(words, template.second.next_output_len)?;
    words.extend_from_slice(&[0xf900_1c09, 0x2a1f_03e0, 0xd65f_03c0]);
    Some(())
}

/// Encodes one atomic two-step rotate/crazy fused region.
#[must_use]
pub(super) fn fused_rotate_crazy_code(
    template: super::direct::DirectFusedRotateCrazyTemplate<'_>,
) -> Option<Vec<u8>> {
    fused_rotate_pair_code(DirectFusedRotatePairTemplate {
        first: template.rotate,
        live_ins: template.live_ins,
        observation: template.observation,
        required_memory_words: template.required_memory_words,
        second: template.crazy,
    })
}

/// Encodes one atomic two-step rotate/no-operation fused region.
#[must_use]
pub(super) fn fused_rotate_no_operation_code(
    template: DirectFusedRotateNoOperationTemplate<'_>,
) -> Option<Vec<u8>> {
    let mut words = Vec::with_capacity(112);
    let mut guard_branches =
        Vec::with_capacity(template.live_ins.len().saturating_add(10));
    push_observation_guards(
        &mut words,
        &mut guard_branches,
        template.observation,
    )?;
    words.push(0xf940_0008);
    push_guard_branch(&mut words, &mut guard_branches, 0xb400_0008);
    words.push(0xf940_040a);
    push_u64_x9(&mut words, template.required_memory_words)?;
    words.push(0xeb09_015f);
    push_guard_branch(&mut words, &mut guard_branches, 0x5400_0003);
    for live_in in template.live_ins {
        push_indexed_memory_guard(
            &mut words,
            &mut guard_branches,
            live_in.address,
            live_in.value,
        );
    }
    words.push(0x3941_3009);
    push_guard_branch(&mut words, &mut guard_branches, 0x3500_0009);
    push_fused_rotate_no_operation_commit(&mut words, template);
    let guard_miss = words.len();
    words.extend_from_slice(&[0x5280_0020, 0xd65f_03c0]);
    patch_guard_branches(&mut words, &guard_branches, guard_miss)?;
    Some(encode_words(&words))
}

fn push_fused_rotate_no_operation_commit(
    words: &mut Vec<u32>,
    template: DirectFusedRotateNoOperationTemplate<'_>,
) {
    words.extend_from_slice(&[
        movz_w10(template.rotate.data_address),
        movk_w10_high(template.rotate.data_address),
        0x8b0a_090a,
        movz_w9(template.rotate.data_value),
        movk_w9_high(template.rotate.data_value),
        0xb900_0149,
        movz_w10(template.rotate.encrypted_address),
        movk_w10_high(template.rotate.encrypted_address),
        0x8b0a_090a,
        movz_w9(template.rotate.encrypted_value),
        movk_w9_high(template.rotate.encrypted_value),
        0xb900_0149,
        movz_w10(template.no_operation.encrypted_address),
        movk_w10_high(template.no_operation.encrypted_address),
        0x8b0a_090a,
        movz_w9(template.no_operation.encrypted_value),
        movk_w9_high(template.no_operation.encrypted_value),
        0xb900_0149,
        movz_w9(template.rotate.accumulator),
        movk_w9_high(template.rotate.accumulator),
        0xb900_4009,
        movz_w9(template.no_operation.next_code_pointer),
        movk_w9_high(template.no_operation.next_code_pointer),
        0xb900_4409,
        movz_w9(template.no_operation.next_data_pointer),
        movk_w9_high(template.no_operation.next_data_pointer),
        0xb900_4809,
        0x2a1f_03e0,
        0xd65f_03c0,
    ]);
}

/// Encodes one atomic two-step rotate/rotate fused region.
#[must_use]
pub(super) fn fused_rotate_pair_code(
    template: DirectFusedRotatePairTemplate<'_>,
) -> Option<Vec<u8>> {
    let mut words = Vec::with_capacity(128);
    let mut guard_branches =
        Vec::with_capacity(template.live_ins.len().saturating_add(10));
    push_observation_guards(
        &mut words,
        &mut guard_branches,
        template.observation,
    )?;
    words.push(0xf940_0008);
    push_guard_branch(&mut words, &mut guard_branches, 0xb400_0008);
    words.push(0xf940_040a);
    push_u64_x9(&mut words, template.required_memory_words)?;
    words.push(0xeb09_015f);
    push_guard_branch(&mut words, &mut guard_branches, 0x5400_0003);
    for live_in in template.live_ins {
        push_indexed_memory_guard(
            &mut words,
            &mut guard_branches,
            live_in.address,
            live_in.value,
        );
    }
    words.push(0x3941_3009);
    push_guard_branch(&mut words, &mut guard_branches, 0x3500_0009);
    push_fused_rotate_pair_commit(&mut words, template);
    let guard_miss = words.len();
    words.extend_from_slice(&[0x5280_0020, 0xd65f_03c0]);
    patch_guard_branches(&mut words, &guard_branches, guard_miss)?;
    Some(encode_words(&words))
}

fn push_fused_rotate_pair_commit(
    words: &mut Vec<u32>,
    template: DirectFusedRotatePairTemplate<'_>,
) {
    for rotate in [template.first, template.second] {
        words.extend_from_slice(&[
            movz_w10(rotate.data_address),
            movk_w10_high(rotate.data_address),
            0x8b0a_090a,
            movz_w9(rotate.data_value),
            movk_w9_high(rotate.data_value),
            0xb900_0149,
            movz_w10(rotate.encrypted_address),
            movk_w10_high(rotate.encrypted_address),
            0x8b0a_090a,
            movz_w9(rotate.encrypted_value),
            movk_w9_high(rotate.encrypted_value),
            0xb900_0149,
        ]);
    }
    words.extend_from_slice(&[
        movz_w9(template.second.accumulator),
        movk_w9_high(template.second.accumulator),
        0xb900_4009,
        movz_w9(template.second.next_code_pointer),
        movk_w9_high(template.second.next_code_pointer),
        0xb900_4409,
        movz_w9(template.second.next_data_pointer),
        movk_w9_high(template.second.next_data_pointer),
        0xb900_4809,
        0x2a1f_03e0,
        0xd65f_03c0,
    ]);
}

/// Encodes one atomic two-step rotate/output fused region.
#[must_use]
pub(super) fn fused_rotate_output_code(
    template: DirectFusedRotateOutputTemplate<'_>,
) -> Option<Vec<u8>> {
    let mut words = Vec::with_capacity(128);
    let mut guard_branches =
        Vec::with_capacity(template.live_ins.len().saturating_add(12));
    push_observation_guards(
        &mut words,
        &mut guard_branches,
        template.observation,
    )?;
    words.push(0xf940_0008);
    push_guard_branch(&mut words, &mut guard_branches, 0xb400_0008);
    words.push(0xf940_040a);
    push_u64_x9(&mut words, template.required_memory_words)?;
    words.push(0xeb09_015f);
    push_guard_branch(&mut words, &mut guard_branches, 0x5400_0003);
    for live_in in template.live_ins {
        push_indexed_memory_guard(
            &mut words,
            &mut guard_branches,
            live_in.address,
            live_in.value,
        );
    }
    words.push(0x3941_3009);
    push_guard_branch(&mut words, &mut guard_branches, 0x3500_0009);
    words.push(0xf940_140b);
    push_guard_branch(&mut words, &mut guard_branches, 0xb400_000b);
    words.push(0xf940_180c);
    push_u64_x9(&mut words, template.output.output_index)?;
    words.push(0xeb09_019f);
    push_guard_branch(&mut words, &mut guard_branches, 0x5400_0009);
    push_fused_rotate_output_commit(&mut words, template)?;
    let guard_miss = words.len();
    words.extend_from_slice(&[0x5280_0020, 0xd65f_03c0]);
    patch_guard_branches(&mut words, &guard_branches, guard_miss)?;
    Some(encode_words(&words))
}

fn push_fused_rotate_output_commit(
    words: &mut Vec<u32>,
    template: DirectFusedRotateOutputTemplate<'_>,
) -> Option<()> {
    words.extend_from_slice(&[
        movz_w10(template.rotate.data_address),
        movk_w10_high(template.rotate.data_address),
        0x8b0a_090a,
        movz_w9(template.rotate.data_value),
        movk_w9_high(template.rotate.data_value),
        0xb900_0149,
        movz_w10(template.rotate.encrypted_address),
        movk_w10_high(template.rotate.encrypted_address),
        0x8b0a_090a,
        movz_w9(template.rotate.encrypted_value),
        movk_w9_high(template.rotate.encrypted_value),
        0xb900_0149,
        movz_w9(template.rotate.accumulator),
        movk_w9_high(template.rotate.accumulator),
        0xb900_4009,
        movz_w9(template.rotate.next_code_pointer),
        movk_w9_high(template.rotate.next_code_pointer),
        0xb900_4409,
        movz_w9(template.rotate.next_data_pointer),
        movk_w9_high(template.rotate.next_data_pointer),
        0xb900_4809,
        movz_w10(template.output.encrypted_address),
        movk_w10_high(template.output.encrypted_address),
        0x8b0a_090a,
        movz_w9(template.output.encrypted_value),
        movk_w9_high(template.output.encrypted_value),
        0xb900_0149,
        movz_w9(template.output.next_code_pointer),
        movk_w9_high(template.output.next_code_pointer),
        0xb900_4409,
        movz_w9(template.output.next_data_pointer),
        movk_w9_high(template.output.next_data_pointer),
        0xb900_4809,
        0xf940_1c0a,
        0x8b0a_016b,
        movz_w9(u32::from(template.output.output_byte)),
        0x3900_0169,
    ]);
    push_u64_x9(words, template.output.next_output_len)?;
    words.extend_from_slice(&[0xf900_1c09, 0x2a1f_03e0, 0xd65f_03c0]);
    Some(())
}

/// Encodes one exact non-aliasing crazy transition.
#[must_use]
pub(super) fn crazy_code(
    observation: DirectEntryObservation,
    guard: DirectCrazyGuard,
    commit: DirectCrazyCommit,
) -> Option<Vec<u8>> {
    rotate_code(observation, guard, commit)
}

/// Encodes one exact non-aliasing rotate transition.
#[must_use]
pub(super) fn rotate_code(
    observation: DirectEntryObservation,
    guard: DirectRotateGuard,
    commit: DirectRotateCommit,
) -> Option<Vec<u8>> {
    let mut words = Vec::with_capacity(88);
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
        movz_w10(commit.data_address),
        movk_w10_high(commit.data_address),
        0x8b0a_090a,
        movz_w9(commit.data_value),
        movk_w9_high(commit.data_value),
        0xb900_0149,
        movz_w10(commit.encrypted_address),
        movk_w10_high(commit.encrypted_address),
        0x8b0a_090a,
        movz_w9(commit.encrypted_value),
        movk_w9_high(commit.encrypted_value),
        0xb900_0149,
        movz_w9(commit.accumulator),
        movk_w9_high(commit.accumulator),
        0xb900_4009,
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
        movz_w10(commit.encrypted_address),
        movk_w10_high(commit.encrypted_address),
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
