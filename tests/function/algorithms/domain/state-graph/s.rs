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
//   - Incremental state reconstruction, collision, and lineage fixtures.
// - Must-Not:
//   - Infer state from private runtime internals or accept digest-only merges.
// - Allows:
//   - Inputs: complete root checkpoints and public current-profile traces.
//   - Outputs: exact oracle equality and collision-safe node identities.
//   - Side effects: test-process allocation only.
// - Split-When:
//   - Split when cross-lineage content-addressed roots gain separate evidence.
// - Merge-When:
//   - Merge when production graph identity owns the same correctness boundary.
// - Summary:
//   - Proves incremental state identity without full-memory hash per
//   - observation.
// - Description:
//   - Replays current traces, forces digest collisions, and rejects foreign
//   - roots.
// - Usage:
//   - Composed by `tests/state_graph_research.rs`.
// - Defaults:
//   - Complete runtime checkpoints remain the independent materialization
//   - oracle.
//

//! Correctness fixtures for incremental exact indexed-state identity.

use malbolge::{
    ProfileMachine, ProfileStepTrace, StepOutcome, current_profile,
    decode_profile_instruction, verify_minimum_initial_halt_profile_width,
    verify_minimum_input_output_halt_profile_width,
    verify_minimum_jump_code_halt_profile_width,
    verify_minimum_jump_code_io_halt_profile_width,
    verify_minimum_straight_line_io_profile_width,
};

use crate::indexed_state::{
    IndexedMachineState, IndexedStateGraph, IndexedStateGraphError,
    constant_indexed_collision_digest,
};

const CURRENT_SOURCE: &[u8] = b"(=%`qL";
const STEP_BUDGET: usize = 8;

fn encoded_profile_instruction(
    decoded: u8,
    position: usize,
) -> Result<u8, String> {
    let pointer = u32::try_from(position)
        .map_err(|error| format!("profile instruction position: {error}"))?;
    (33u8..=126u8)
        .find(|cell| {
            decode_profile_instruction(u32::from(*cell), pointer)
                == Some(decoded)
        })
        .ok_or_else(|| format!("missing encoded {decoded} at {position}"))
}

fn source_backed_jump_code_chain() -> Result<Vec<u8>, String> {
    let first_target = encoded_profile_instruction(b'i', 0)?;
    let mutated_target = encoded_profile_instruction(b'*', 1)?;
    let return_target = encoded_profile_instruction(b'*', 2)?;
    let halt_target = encoded_profile_instruction(b'v', 3)?;
    let second_jump = usize::from(first_target).saturating_add(1);
    let third_jump = usize::from(mutated_target).saturating_add(1);
    let mutated_jump = usize::from(return_target).saturating_add(1);
    let halt_position = usize::from(halt_target).saturating_add(1);
    let source_len = second_jump.saturating_add(1);
    let mut source = Vec::with_capacity(source_len);
    for position in 0..source_len {
        source.push(encoded_profile_instruction(b'o', position)?);
    }
    for (position, value) in [
        (0usize, first_target),
        (1usize, mutated_target),
        (2usize, return_target),
        (3usize, halt_target),
        (
            mutated_jump,
            encoded_profile_instruction(b'j', mutated_jump)?,
        ),
        (third_jump, encoded_profile_instruction(b'i', third_jump)?),
        (
            halt_position,
            encoded_profile_instruction(b'v', halt_position)?,
        ),
        (second_jump, encoded_profile_instruction(b'i', second_jump)?),
    ] {
        let cell = source.get_mut(position).ok_or_else(|| {
            format!("missing shadow jump-code cell {position}")
        })?;
        *cell = value;
    }
    Ok(source)
}

fn source_backed_jump_code_io_chain() -> Result<Vec<u8>, String> {
    let mut source = source_backed_jump_code_chain()?;
    let profile = current_profile();
    for (position, decoded) in [
        (79usize, profile.input_instruction()),
        (80usize, profile.output_instruction()),
        (81usize, profile.input_instruction()),
        (82usize, profile.output_instruction()),
        (83usize, b'v'),
    ] {
        let cell = source.get_mut(position).ok_or_else(|| {
            format!("missing indexed jump-code I/O cell {position}")
        })?;
        *cell = encoded_profile_instruction(decoded, position)?;
    }
    Ok(source)
}

fn check_jump_code_encryption_targets(
    source: &[u8],
    before: &[u32],
    after: &[u32],
) -> Result<(), String> {
    for data_index in 0usize..4 {
        let target =
            usize::from(source.get(data_index).copied().ok_or_else(|| {
                String::from("jump-code data cell is missing")
            })?);
        let before_word = before
            .get(target)
            .copied()
            .ok_or_else(|| String::from("jump-code root target is missing"))?;
        let after_word = after.get(target).copied().ok_or_else(|| {
            String::from("jump-code materialized target missing")
        })?;
        if before_word == after_word {
            return Err(format!(
                "jump-code encryption target {target} did not change"
            ));
        }
    }
    let mutated = after
        .get(38)
        .copied()
        .ok_or_else(|| String::from("jump-code shadow target is missing"))?;
    if decode_profile_instruction(mutated, 38) != Some(b'i') {
        return Err(String::from("jump-code shadow decode was not retained"));
    }
    Ok(())
}

#[test]
fn jump_code_geometry_survives_indexed_self_encryption() -> Result<(), String> {
    let source = source_backed_jump_code_chain()?;
    let verified =
        verify_minimum_jump_code_halt_profile_width(current_profile(), &source)
            .map_err(|error| {
                format!("jump-code width verification failed: {error}")
            })?;
    let mut machine =
        ProfileMachine::from_verified_source(&verified, Vec::new()).map_err(
            |error| format!("jump-code machine load failed: {error}"),
        )?;
    let root = machine.snapshot_state();
    let mut indexed = IndexedMachineState::from_checkpoint(&root)
        .map_err(|error| format!("jump-code indexed root failed: {error:?}"))?;
    for _step in 0u8..4 {
        let mut trace_record = None;
        let outcome = machine
            .step_traced(&mut |trace: &ProfileStepTrace| {
                trace_record = Some(*trace);
            })
            .map_err(|error| format!("jump-code trace step failed: {error}"))?;
        if outcome != StepOutcome::Continued {
            return Err(String::from(
                "jump-code chain halted before four jumps",
            ));
        }
        let trace = trace_record
            .ok_or_else(|| String::from("jump-code trace missing"))?;
        indexed = indexed.apply_trace(&trace).map_err(|error| {
            format!("jump-code indexed apply failed: {error:?}")
        })?;
    }
    let materialized = indexed
        .materialize_checkpoint()
        .map_err(|error| format!("jump-code materialize failed: {error:?}"))?;
    if materialized != machine.snapshot_state()
        || materialized.geometry() != verified.geometry()
    {
        return Err(String::from("jump-code indexed authority drifted"));
    }
    check_jump_code_encryption_targets(
        &source,
        root.memory(),
        materialized.memory(),
    )?;
    if materialized.registers().code_pointer != 79
        || materialized.registers().data_pointer != 4
    {
        return Err(String::from("jump-code indexed registers drifted"));
    }
    Ok(())
}

#[test]
fn jump_code_io_policy_survives_indexed_effects() -> Result<(), String> {
    let source = source_backed_jump_code_io_chain()?;
    let verified = verify_minimum_jump_code_io_halt_profile_width(
        current_profile(),
        &source,
    )
    .map_err(|error| format!("jump-code I/O verification failed: {error}"))?;
    let mut machine =
        ProfileMachine::from_verified_source(&verified, vec![0xa5, 0x3c])
            .map_err(|error| {
                format!("jump-code I/O machine load failed: {error}")
            })?;
    let root = machine.snapshot_state();
    let mut indexed =
        IndexedMachineState::from_checkpoint(&root).map_err(|error| {
            format!("jump-code I/O indexed root failed: {error:?}")
        })?;
    for _step in 0u8..8 {
        let mut trace_record = None;
        let outcome = machine
            .step_traced(&mut |trace: &ProfileStepTrace| {
                trace_record = Some(*trace);
            })
            .map_err(|error| format!("jump-code I/O trace failed: {error}"))?;
        if outcome != StepOutcome::Continued {
            return Err(String::from(
                "jump-code I/O halted before eight effects",
            ));
        }
        let trace = trace_record
            .ok_or_else(|| String::from("jump-code I/O trace missing"))?;
        indexed = indexed.apply_trace(&trace).map_err(|error| {
            format!("jump-code I/O indexed apply failed: {error:?}")
        })?;
    }
    let materialized = indexed.materialize_checkpoint().map_err(|error| {
        format!("jump-code I/O materialize failed: {error:?}")
    })?;
    if materialized != machine.snapshot_state()
        || materialized.geometry() != verified.geometry()
        || materialized.io().input_consumed() != 2
        || materialized.io().output() != [0xa5, 0x3c]
    {
        return Err(String::from("jump-code I/O indexed authority drifted"));
    }
    Ok(())
}

#[test]
fn derived_width_checkpoint_survives_indexed_state_roundtrip()
-> Result<(), String> {
    let verified =
        verify_minimum_initial_halt_profile_width(current_profile(), b"QP")
            .map_err(|error| {
                format!("derived width verification failed: {error}")
            })?;
    let mut machine =
        ProfileMachine::from_verified_source(&verified, Vec::new())
            .map_err(|error| format!("derived machine load failed: {error}"))?;
    let root = machine.snapshot_state();
    let mut indexed = IndexedMachineState::from_checkpoint(&root)
        .map_err(|error| format!("derived indexed root failed: {error:?}"))?;
    let mut trace_record = None;
    let _outcome = machine
        .step_traced(&mut |trace: &ProfileStepTrace| {
            trace_record = Some(*trace);
        })
        .map_err(|error| format!("derived trace step failed: {error}"))?;
    let trace =
        trace_record.ok_or_else(|| String::from("derived trace missing"))?;
    indexed = indexed
        .apply_trace(&trace)
        .map_err(|error| format!("derived indexed apply failed: {error:?}"))?;
    let materialized = indexed
        .materialize_checkpoint()
        .map_err(|error| format!("derived materialize failed: {error:?}"))?;
    if materialized != machine.snapshot_state() {
        return Err(String::from("derived indexed roundtrip drifted"));
    }
    if materialized.geometry() != verified.geometry() {
        return Err(String::from("derived geometry was not preserved"));
    }
    Ok(())
}

#[test]
fn input_bound_geometry_survives_indexed_state_roundtrip() -> Result<(), String>
{
    let verified = verify_minimum_input_output_halt_profile_width(
        current_profile(),
        b"ubO",
    )
    .map_err(|error| {
        format!("input-bound width verification failed: {error}")
    })?;
    let mut machine =
        ProfileMachine::from_verified_source(&verified, vec![0xa5]).map_err(
            |error| format!("input-bound machine load failed: {error}"),
        )?;
    let root = machine.snapshot_state();
    let mut indexed =
        IndexedMachineState::from_checkpoint(&root).map_err(|error| {
            format!("input-bound indexed root failed: {error:?}")
        })?;
    let mut trace_record = None;
    let _outcome = machine
        .step_traced(&mut |trace: &ProfileStepTrace| {
            trace_record = Some(*trace);
        })
        .map_err(|error| format!("input-bound trace step failed: {error}"))?;
    let trace = trace_record
        .ok_or_else(|| String::from("input-bound trace missing"))?;
    indexed = indexed.apply_trace(&trace).map_err(|error| {
        format!("input-bound indexed apply failed: {error:?}")
    })?;
    let materialized = indexed.materialize_checkpoint().map_err(|error| {
        format!("input-bound materialize failed: {error:?}")
    })?;
    if materialized != machine.snapshot_state()
        || materialized.geometry() != verified.geometry()
    {
        return Err(String::from("input-bound indexed roundtrip drifted"));
    }
    Ok(())
}

#[test]
fn minimum_length_two_geometry_survives_multiple_indexed_effects()
-> Result<(), String> {
    let verified = verify_minimum_straight_line_io_profile_width(
        current_profile(),
        b"uCar_L",
    )
    .map_err(|error| format!("min-two width verification failed: {error}"))?;
    let mut machine =
        ProfileMachine::from_verified_source(&verified, vec![0xa5, 0x3c])
            .map_err(|error| format!("min-two machine load failed: {error}"))?;
    let root = machine.snapshot_state();
    let mut indexed = IndexedMachineState::from_checkpoint(&root)
        .map_err(|error| format!("min-two indexed root failed: {error:?}"))?;
    for _step in 0u8..5 {
        let mut trace_record = None;
        let outcome = machine
            .step_traced(&mut |trace: &ProfileStepTrace| {
                trace_record = Some(*trace);
            })
            .map_err(|error| format!("min-two trace step failed: {error}"))?;
        if outcome != StepOutcome::Continued {
            return Err(String::from(
                "min-two fixture halted before five effects",
            ));
        }
        let trace = trace_record
            .ok_or_else(|| String::from("min-two trace missing"))?;
        indexed = indexed.apply_trace(&trace).map_err(|error| {
            format!("min-two indexed apply failed: {error:?}")
        })?;
    }
    let materialized = indexed
        .materialize_checkpoint()
        .map_err(|error| format!("min-two materialize failed: {error:?}"))?;
    if materialized != machine.snapshot_state()
        || materialized.geometry() != verified.geometry()
    {
        return Err(String::from("min-two indexed authority drifted"));
    }
    if materialized.io().input_consumed() != 2
        || materialized.io().output() != [0xa5, 0x3c]
    {
        return Err(String::from("min-two indexed I/O drifted"));
    }
    Ok(())
}

#[test]
fn current_trace_reconstructs_and_replay_deduplicates() -> Result<(), String> {
    let mut machine =
        ProfileMachine::from_source(current_profile(), CURRENT_SOURCE, vec![
            0x41,
        ])
        .map_err(|error| {
            format!("indexed state fixture load failed: {error}")
        })?;
    let checkpoint = machine.snapshot_state();
    let mut state = IndexedMachineState::from_checkpoint(&checkpoint)
        .map_err(|error| format!("indexed state root failed: {error:?}"))?;
    let mut graph = IndexedStateGraph::new(state.clone());
    for _step in 0..STEP_BUDGET {
        let mut trace_record = None;
        let outcome = machine
            .step_traced(&mut |trace: &ProfileStepTrace| {
                trace_record = Some(*trace);
            })
            .map_err(|error| format!("indexed state step failed: {error}"))?;
        let trace = trace_record
            .ok_or_else(|| String::from("indexed state trace missing"))?;
        state = state.apply_trace(&trace).map_err(|error| {
            format!("indexed state apply failed: {error:?}")
        })?;
        let materialized = state.materialize_checkpoint().map_err(|error| {
            format!("indexed state materialize failed: {error:?}")
        })?;
        if materialized != machine.snapshot_state() {
            return Err(String::from(
                "incremental state diverged from runtime",
            ));
        }
        let first = graph.observe(state.clone()).map_err(|error| {
            format!("indexed state observe failed: {error:?}")
        })?;
        let replay = graph.observe(state.clone()).map_err(|error| {
            format!("indexed state replay failed: {error:?}")
        })?;
        if first != replay {
            return Err(String::from(
                "exact incremental replay did not deduplicate",
            ));
        }
        if outcome != StepOutcome::Continued {
            break;
        }
    }
    if graph.deduplicated_observations() == 0 {
        return Err(String::from(
            "incremental graph recorded no deduplication",
        ));
    }
    Ok(())
}

#[test]
fn forced_digest_collision_never_merges_distinct_states() -> Result<(), String>
{
    let mut machine =
        ProfileMachine::from_source(current_profile(), CURRENT_SOURCE, vec![
            0x41,
        ])
        .map_err(|error| {
            format!("indexed collision fixture failed: {error}")
        })?;
    let seed = IndexedMachineState::from_checkpoint(&machine.snapshot_state())
        .map_err(|error| format!("indexed collision root failed: {error:?}"))?;
    let mut graph = IndexedStateGraph::with_digest(
        seed.clone(),
        constant_indexed_collision_digest,
    );
    let mut trace_record = None;
    let _outcome = machine
        .step_traced(&mut |trace: &ProfileStepTrace| {
            trace_record = Some(*trace);
        })
        .map_err(|error| format!("indexed collision step failed: {error}"))?;
    let trace = trace_record
        .ok_or_else(|| String::from("indexed collision trace missing"))?;
    let next = seed.apply_trace(&trace).map_err(|error| {
        format!("indexed collision apply failed: {error:?}")
    })?;
    let next_id = graph.observe(next).map_err(|error| {
        format!("indexed collision observe failed: {error:?}")
    })?;
    if next_id.value() == 0 || graph.node_count() != 2 {
        return Err(String::from(
            "forced digest collision merged distinct states",
        ));
    }
    Ok(())
}

#[test]
fn independently_constructed_root_is_foreign_lineage() -> Result<(), String> {
    let machine = ProfileMachine::from_source(
        current_profile(),
        CURRENT_SOURCE,
        Vec::new(),
    )
    .map_err(|error| format!("indexed lineage fixture failed: {error}"))?;
    let checkpoint = machine.snapshot_state();
    let seed = IndexedMachineState::from_checkpoint(&checkpoint)
        .map_err(|error| format!("indexed lineage seed failed: {error:?}"))?;
    let foreign =
        IndexedMachineState::from_checkpoint(&checkpoint).map_err(|error| {
            format!("indexed lineage foreign failed: {error:?}")
        })?;
    let mut graph = IndexedStateGraph::new(seed);
    let result = graph.observe(foreign);
    if result == Err(IndexedStateGraphError::ForeignLineage) {
        Ok(())
    } else {
        Err(format!("foreign lineage was not rejected: {result:?}"))
    }
}
