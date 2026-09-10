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
//   - Bounded radix reconstruction and fail-closed index fixtures.
// - Must-Not:
//   - Benchmark the candidate or infer writes from private VM transition plans.
// - Allows:
//   - Inputs: current checkpoints and exact public profile memory deltas.
//   - Outputs: full reconstruction equality and indexed-read evidence.
//   - Side effects: test-process allocation only.
// - Split-When:
//   - Split when generalized profile widths require a new radix geometry.
// - Merge-When:
//   - Merge when runtime indexed memory owns the same correctness contract.
// - Summary:
//   - Proves a four-level sparse overlay reconstructs current memory exactly.
// - Description:
//   - Exercises real traces, 4096 distinct overrides, and forged-before
//   - rejection.
// - Usage:
//   - Composed by `tests/state_graph_research.rs`.
// - Defaults:
//   - Complete checkpoints remain the independent reconstruction oracle.
//

//! Correctness fixtures for the bounded-read persistent radix candidate.

use malbolge::{
    ProfileMachine, ProfileMemoryDelta, ProfileMemoryWrite, ProfileStepTrace,
    StepOutcome, current_profile,
};

use crate::indexed::{IndexedMemoryError, IndexedProfileMemory};

const CURRENT_SOURCE: &[u8] = b"(=%`qL";
const DISTINCT_PATCHES: u32 = 4_096;
const PATCH_BASE: u32 = 1_024;
const ROOT_ONLY_ADDRESS: u32 = 17;
const STEP_BUDGET: usize = 8;

const fn shifted_word(value: u32, offset: u32, modulus: u32) -> u32 {
    let shifted = value.saturating_add(offset);
    if shifted >= modulus {
        shifted.saturating_sub(modulus)
    } else {
        shifted
    }
}

#[test]
fn current_trace_deltas_reconstruct_every_indexed_checkpoint()
-> Result<(), String> {
    let mut machine =
        ProfileMachine::from_source(current_profile(), CURRENT_SOURCE, vec![
            0x41,
        ])
        .map_err(|error| format!("indexed fixture load failed: {error}"))?;
    let root = machine.snapshot_state();
    let mut indexed = IndexedProfileMemory::from_state(&root)
        .map_err(|error| format!("indexed root failed: {error:?}"))?;
    for _step in 0..STEP_BUDGET {
        let mut delta = None;
        let outcome = machine
            .step_traced(&mut |trace: &ProfileStepTrace| {
                delta = Some(trace.memory_delta);
            })
            .map_err(|error| format!("indexed traced step failed: {error}"))?;
        let memory_delta = delta
            .ok_or_else(|| String::from("indexed trace did not emit delta"))?;
        indexed = indexed
            .apply(memory_delta)
            .map_err(|error| format!("indexed patch failed: {error:?}"))?;
        let checkpoint = machine.snapshot_state();
        let reconstructed = indexed.materialize().map_err(|error| {
            format!("indexed materialize failed: {error:?}")
        })?;
        if reconstructed != checkpoint.memory() {
            return Err(String::from(
                "indexed memory diverged from checkpoint",
            ));
        }
        if outcome != StepOutcome::Continued {
            break;
        }
    }
    Ok(())
}

#[test]
fn distinct_overrides_preserve_root_and_latest_reads() -> Result<(), String> {
    let machine =
        ProfileMachine::from_source(current_profile(), b"QP", Vec::new())
            .map_err(|error| {
                format!("indexed distinct fixture failed: {error}")
            })?;
    let state = machine.snapshot_state();
    let expected_root = state
        .memory()
        .get(
            usize::try_from(ROOT_ONLY_ADDRESS)
                .map_err(|error| error.to_string())?,
        )
        .copied()
        .ok_or_else(|| String::from("missing indexed root-only cell"))?;
    let mut indexed = IndexedProfileMemory::from_state(&state)
        .map_err(|error| format!("indexed distinct root failed: {error:?}"))?;
    let mut latest_address = PATCH_BASE;
    let mut latest_value = 0u32;
    for offset in 0..DISTINCT_PATCHES {
        let address = PATCH_BASE.saturating_add(offset);
        let before = indexed.read(address).map_err(|error| {
            format!("indexed before read failed: {error:?}")
        })?;
        let incremented = before.saturating_add(1);
        let after = if incremented == current_profile().word_modulus() {
            0
        } else {
            incremented
        };
        indexed = indexed
            .apply(ProfileMemoryDelta {
                data: Some(ProfileMemoryWrite { address, after, before }),
                encryption: None,
            })
            .map_err(|error| {
                format!("indexed distinct patch failed: {error:?}")
            })?;
        latest_address = address;
        latest_value = after;
    }
    if indexed.patch_count() != usize::try_from(DISTINCT_PATCHES).unwrap_or(0) {
        return Err(String::from("indexed patch count mismatch"));
    }
    let latest = indexed
        .read(latest_address)
        .map_err(|error| format!("indexed latest read failed: {error:?}"))?;
    if latest != latest_value {
        return Err(String::from("indexed latest override mismatch"));
    }
    let root_value = indexed
        .read(ROOT_ONLY_ADDRESS)
        .map_err(|error| format!("indexed root read failed: {error:?}"))?;
    if root_value != expected_root {
        return Err(String::from("indexed root fallback mismatch"));
    }
    Ok(())
}

#[test]
fn forged_before_value_is_rejected_by_index() -> Result<(), String> {
    let machine = ProfileMachine::from_source(
        current_profile(),
        CURRENT_SOURCE,
        Vec::new(),
    )
    .map_err(|error| format!("indexed mismatch fixture failed: {error}"))?;
    let indexed = IndexedProfileMemory::from_state(&machine.snapshot_state())
        .map_err(|error| {
        format!("indexed mismatch root failed: {error:?}")
    })?;
    let observed = indexed
        .read(0)
        .map_err(|error| format!("indexed mismatch read failed: {error:?}"))?;
    let forged = observed.saturating_add(1);
    let result = indexed.apply(ProfileMemoryDelta {
        data: Some(ProfileMemoryWrite {
            address: 0,
            after: forged,
            before: forged,
        }),
        encryption: None,
    });
    match result {
        Err(IndexedMemoryError::BeforeValueMismatch { address: 0, .. }) => {
            Ok(())
        },
        other => Err(format!("indexed forged before was accepted: {other:?}")),
    }
}

#[test]
fn reverted_override_returns_to_canonical_root_identity() -> Result<(), String>
{
    let machine =
        ProfileMachine::from_source(current_profile(), b"QP", Vec::new())
            .map_err(|error| {
                format!("indexed revert fixture failed: {error}")
            })?;
    let state = machine.snapshot_state();
    let root = IndexedProfileMemory::from_state(&state)
        .map_err(|error| format!("indexed revert root failed: {error:?}"))?;
    let address = PATCH_BASE;
    let before = root.read(address).map_err(|error| {
        format!("indexed revert root read failed: {error:?}")
    })?;
    let changed = u32::from(before == 0);
    let modified = root
        .apply(ProfileMemoryDelta {
            data: Some(ProfileMemoryWrite {
                address,
                after: changed,
                before,
            }),
            encryption: None,
        })
        .map_err(|error| format!("indexed change failed: {error:?}"))?;
    if modified.overlay_digest() == root.overlay_digest() {
        return Err(String::from(
            "indexed change did not alter overlay digest",
        ));
    }
    let reverted = modified
        .apply(ProfileMemoryDelta {
            data: Some(ProfileMemoryWrite {
                address,
                after: before,
                before: changed,
            }),
            encryption: None,
        })
        .map_err(|error| format!("indexed revert failed: {error:?}"))?;
    if reverted.overlay_digest() != root.overlay_digest() {
        return Err(String::from("indexed revert digest is not canonical"));
    }
    if !reverted.exact_memory_eq(&root) {
        return Err(String::from("indexed reverted memory is not exact root"));
    }
    Ok(())
}

fn apply_indexed_writes<const N: usize>(
    mut memory: IndexedProfileMemory,
    writes: [(u32, u32); N],
) -> Result<IndexedProfileMemory, String> {
    for (address, after) in writes {
        let before = memory.read(address).map_err(|error| {
            format!("indexed history read failed: {error:?}")
        })?;
        memory = memory
            .apply(ProfileMemoryDelta {
                data: Some(ProfileMemoryWrite { address, after, before }),
                encryption: None,
            })
            .map_err(|error| {
                format!("indexed history write failed: {error:?}")
            })?;
    }
    Ok(memory)
}

#[test]
fn divergent_write_histories_converge_to_exact_indexed_memory()
-> Result<(), String> {
    let machine =
        ProfileMachine::from_source(current_profile(), b"QP", Vec::new())
            .map_err(|error| {
                format!("indexed history fixture failed: {error}")
            })?;
    let root = IndexedProfileMemory::from_state(&machine.snapshot_state())
        .map_err(|error| format!("indexed history root failed: {error:?}"))?;
    let first_address = PATCH_BASE;
    let second_address = PATCH_BASE.saturating_add(1);
    let first_base = root.read(first_address).map_err(|error| {
        format!("indexed first history read failed: {error:?}")
    })?;
    let second_base = root.read(second_address).map_err(|error| {
        format!("indexed second history read failed: {error:?}")
    })?;
    let modulus = current_profile().word_modulus();
    let first_mid = shifted_word(first_base, 1, modulus);
    let first_final = shifted_word(first_base, 2, modulus);
    let second_mid = shifted_word(second_base, 1, modulus);
    let second_final = shifted_word(second_base, 2, modulus);
    let direct = apply_indexed_writes(root.clone(), [
        (first_address, first_final),
        (second_address, second_final),
    ])?;
    let staged = apply_indexed_writes(root, [
        (second_address, second_mid),
        (first_address, first_mid),
        (second_address, second_final),
        (first_address, first_final),
    ])?;
    if direct.patch_count() != 2 || staged.patch_count() != 4 {
        return Err(String::from("indexed histories did not remain distinct"));
    }
    if direct.overlay_digest() != staged.overlay_digest()
        || !direct.exact_memory_eq(&staged)
        || direct
            .materialize()
            .map_err(|error| format!("direct materialize: {error:?}"))?
            != staged
                .materialize()
                .map_err(|error| format!("staged materialize: {error:?}"))?
    {
        return Err(String::from(
            "divergent indexed histories did not converge exactly",
        ));
    }
    Ok(())
}
