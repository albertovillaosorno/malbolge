// File:
//   - p.rs
// Path:
//   - algorithms/self-modification-state-graph-optimizer/tests/p.rs
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
//   - Persistent-memory reconstruction and fail-closed patch fixtures.
// - Must-Not:
//   - Benchmark the representation or infer deltas by private transition plans.
// - Allows:
//   - Inputs: current-profile checkpoints and public trace memory deltas.
//   - Outputs: complete reconstruction equality and mismatch diagnostics.
//   - Side effects: test-process allocation of current-profile oracle images.
// - Split-When:
//   - Split when compaction/indexing strategies gain separate lifecycle
//   - evidence.
// - Merge-When:
//   - Merge when runtime persistent memory owns the same reconstruction
//   - contract.
// - Summary:
//   - Reconstructs current memory exactly from one root plus semantic patches.
// - Description:
//   - Checks every traced step against the runtime's complete checkpoint
//   - memory.
// - Usage:
//   - Composed by `tests/state_graph_research.rs`.
// - Defaults:
//   - Empty deltas add no patch and invalid `before` values fail closed.
//
// Related documents:
// - algorithms/self-modification-state-graph-optimizer/memory.rs
//
// Large file:
//   - false
//

//! Persistent-memory correctness fixtures over exact current-profile trace
//! deltas.

use malbolge::{
    ProfileMachine, ProfileMemoryDelta, ProfileMemoryWrite, ProfileStepTrace,
    StepOutcome, current_profile,
};

use crate::persistent::{PersistentMemoryError, PersistentProfileMemory};

const CURRENT_SOURCE: &[u8] = b"(=%`qL";
const STEP_BUDGET: usize = 8;

#[test]
fn current_trace_patches_reconstruct_every_checkpoint() -> Result<(), String> {
    let mut machine =
        ProfileMachine::from_source(current_profile(), CURRENT_SOURCE, vec![
            0x41,
        ])
        .map_err(|error| format!("persistent fixture load failed: {error}"))?;
    let root = machine.snapshot_state();
    let mut persistent = PersistentProfileMemory::from_state(&root);
    for _step in 0..STEP_BUDGET {
        let mut delta = None;
        let outcome = machine
            .step_traced(&mut |trace: &ProfileStepTrace| {
                delta = Some(trace.memory_delta);
            })
            .map_err(|error| {
                format!("persistent traced step failed: {error}")
            })?;
        let memory_delta = delta.ok_or_else(|| {
            String::from("persistent trace did not emit delta")
        })?;
        persistent = persistent
            .apply(memory_delta)
            .map_err(|error| format!("persistent patch failed: {error:?}"))?;
        let checkpoint = machine.snapshot_state();
        let reconstructed = persistent.materialize().map_err(|error| {
            format!("persistent materialization failed: {error:?}")
        })?;
        if reconstructed != checkpoint.memory() {
            return Err(String::from(
                "persistent memory diverged from checkpoint",
            ));
        }
        if outcome != StepOutcome::Continued {
            break;
        }
    }
    Ok(())
}

#[test]
fn empty_delta_reuses_patch_depth() -> Result<(), String> {
    let machine =
        ProfileMachine::from_source(current_profile(), b"QP", Vec::new())
            .map_err(|error| format!("empty-delta fixture failed: {error}"))?;
    let persistent =
        PersistentProfileMemory::from_state(&machine.snapshot_state());
    let updated = persistent
        .apply(ProfileMemoryDelta::default())
        .map_err(|error| format!("empty delta failed: {error:?}"))?;
    if updated.patch_depth() == persistent.patch_depth() {
        Ok(())
    } else {
        Err(String::from(
            "empty delta unexpectedly increased patch depth",
        ))
    }
}

#[test]
fn mismatched_before_value_fails_closed() -> Result<(), String> {
    let machine = ProfileMachine::from_source(
        current_profile(),
        CURRENT_SOURCE,
        Vec::new(),
    )
    .map_err(|error| format!("mismatch fixture failed: {error}"))?;
    let persistent =
        PersistentProfileMemory::from_state(&machine.snapshot_state());
    let observed = persistent
        .read(0)
        .map_err(|error| format!("root read failed: {error:?}"))?;
    let delta = ProfileMemoryDelta {
        data: Some(ProfileMemoryWrite {
            address: 0,
            after: observed.saturating_add(1),
            before: observed.saturating_add(1),
        }),
        encryption: None,
    };
    let result = persistent.apply(delta);
    match result {
        Err(PersistentMemoryError::BeforeValueMismatch {
            address: 0, ..
        }) => Ok(()),
        other => Err(format!("before mismatch did not fail closed: {other:?}")),
    }
}
