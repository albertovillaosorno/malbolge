// File:
//   - bench.rs
// Path:
//   - algorithms/self-modification-state-graph-optimizer/bench.rs
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
//   - Raw current-profile checkpoint copy/hash/equality benchmark samples.
// - Must-Not:
//   - Claim a reduced-state design or include profile loading in timed regions.
// - Allows:
//   - Inputs: current profile, validated checkpoints, exact profile-state
//     graph.
//   - Outputs: raw nanosecond samples and deterministic checksums on stdout.
//   - Side effects: benchmark-process allocation, CPU time, and stdout only.
// - Split-When:
//   - Split when an admitted reduced-state representation needs comparison.
// - Merge-When:
//   - Merge when one benchmark owns the same checkpoint operations/workload.
// - Summary:
//   - Measures the cost of the conservative scalable checkpoint baseline.
// - Description:
//   - Separates snapshot copy, first exact insert, and exact replay matching.
// - Usage:
//   - Run with `cargo run --release --bin state_graph_benchmark`.
// - Defaults:
//   - Uses 15 samples and the canonical current 14-trit profile.
//
// Related documents:
// - docs/research/algorithms/self-modification-state-graph-optimizer/research.
//   md
// - algorithms/self-modification-state-graph-optimizer/experiment.toml
//
// Large file:
//   - false

//! Raw cost samples for exact current-profile checkpoint graph identity.

use std::hint::black_box;
use std::io::{Error as IoError, Result as IoResult, Write, stdout};
use std::time::Instant;

use malbolge::{
    ProfileMachine, ProfileMachineIoState, ProfileMachineState,
    ProfileMemoryDelta, ProfileRegisters, ProfileStepTrace, current_profile,
};

use crate::persistent::PersistentProfileMemory;
use crate::profile_graph::ProfileStateGraph;

const CURRENT_SOURCE: &[u8] = b"(=%`qL";
const DELTA_BASE_SOURCE: &[u8] = b"QP";
const DELTA_DATA_ADDRESS: u32 = 1;
const DELTA_DATA_INDEX: usize = 1;
const DELTA_ENCRYPTION_INDEX: usize = 2;
const DELTA_ENCRYPTION_TARGET: u32 = 2;
const DELTA_GRAPHICAL_TARGET: u32 = u32::from(b'D');
const DELTA_INSTRUCTION: u32 = u32::from(b'>');
const FNV_OFFSET: u64 = 14_695_981_039_346_656_037;
const FNV_PRIME: u64 = 1_099_511_628_211;
const PERSISTENT_OPERATIONS: usize = 16_384;
const PROFILE_BENCHMARK: &str = "profile-checkpoint";
const SAMPLE_COUNT: u8 = 15;

fn checkpoint_checksum(state: &ProfileMachineState) -> u64 {
    let mut hash = FNV_OFFSET;
    hash = hash_usize(hash, state.memory().len());
    hash = state
        .memory()
        .first()
        .map_or(hash, |word| hash_u32(hash, *word));
    hash = state
        .memory()
        .last()
        .map_or(hash, |word| hash_u32(hash, *word));
    let io = state.io();
    hash = hash_usize(hash, io.input().len());
    hash = hash_usize(hash, io.input_consumed());
    hash = hash_usize(hash, io.output().len());
    let registers = state.registers();
    hash = hash_u32(hash, registers.accumulator);
    hash = hash_u32(hash, registers.code_pointer);
    hash_u32(hash, registers.data_pointer)
}

fn graph_checksum(graph: &ProfileStateGraph, node: u32) -> u64 {
    let mut hash = hash_u32(FNV_OFFSET, node);
    hash = hash_usize(hash, graph.node_count());
    hash = hash_usize(hash, graph.observations());
    hash_usize(hash, graph.deduplicated_observations())
}

fn hash_byte(hash: u64, value: u8) -> u64 {
    (hash ^ u64::from(value)).wrapping_mul(FNV_PRIME)
}

fn hash_u32(mut hash: u64, value: u32) -> u64 {
    for byte in value.to_le_bytes() {
        hash = hash_byte(hash, byte);
    }
    hash
}

fn hash_u64(mut hash: u64, value: u64) -> u64 {
    for byte in value.to_le_bytes() {
        hash = hash_byte(hash, byte);
    }
    hash
}

fn hash_usize(mut hash: u64, value: usize) -> u64 {
    for byte in value.to_le_bytes() {
        hash = hash_byte(hash, byte);
    }
    hash
}

fn insert_checkpoint(
    (mut graph, checkpoint): (ProfileStateGraph, ProfileMachineState),
) -> u64 {
    match graph.observe(checkpoint) {
        Ok(node) => graph_checksum(&graph, node.value()),
        Err(_error) => u64::MAX,
    }
}

fn apply_persistent(
    (memory, delta, address): (
        PersistentProfileMemory,
        ProfileMemoryDelta,
        u32,
    ),
) -> u64 {
    match memory.apply(delta) {
        Ok(updated) => match updated.read(address) {
            Ok(value) => {
                let hash = hash_usize(FNV_OFFSET, updated.patch_depth());
                hash_u32(hash, value)
            },
            Err(_error) => u64::MAX,
        },
        Err(_error) => u64::MAX,
    }
}

fn persistent_fixture()
-> IoResult<(PersistentProfileMemory, ProfileMemoryDelta, u32)> {
    let base_machine = ProfileMachine::from_source(
        current_profile(),
        DELTA_BASE_SOURCE,
        Vec::new(),
    )
    .map_err(|error| IoError::other(format!("delta base load: {error}")))?;
    let base_state = base_machine.snapshot_state();
    let mut memory = base_state.memory().to_vec();
    let instruction = memory
        .get_mut(0)
        .ok_or_else(|| IoError::other("missing delta instruction cell"))?;
    *instruction = DELTA_INSTRUCTION;
    let data = memory
        .get_mut(DELTA_DATA_INDEX)
        .ok_or_else(|| IoError::other("missing delta data cell"))?;
    *data = 2;
    let target = memory
        .get_mut(DELTA_ENCRYPTION_INDEX)
        .ok_or_else(|| IoError::other("missing delta encryption cell"))?;
    *target = DELTA_GRAPHICAL_TARGET;
    let state = ProfileMachineState::new(
        current_profile(),
        memory,
        ProfileRegisters {
            accumulator: 7,
            code_pointer: 0,
            data_pointer: DELTA_DATA_ADDRESS,
        },
        ProfileMachineIoState::new(Vec::new(), 0, Vec::new(), None).map_err(
            |error| IoError::other(format!("delta IO state: {error}")),
        )?,
    )
    .map_err(|error| IoError::other(format!("delta state: {error}")))?;
    let root = PersistentProfileMemory::from_state(&state);
    let mut machine = ProfileMachine::from_snapshot(state);
    let mut delta = None;
    machine
        .step_traced(&mut |trace: &ProfileStepTrace| {
            delta = Some(trace.memory_delta);
        })
        .map_err(|error| {
            IoError::other(format!("delta traced step: {error}"))
        })?;
    let memory_delta =
        delta.ok_or_else(|| IoError::other("missing trace delta"))?;
    if memory_delta.changed_cells() != 2 {
        return Err(IoError::other(
            "benchmark delta is not a two-cell witness",
        ));
    }
    let address = memory_delta
        .data
        .map(|write| write.address)
        .ok_or_else(|| IoError::other("benchmark delta has no data write"))?;
    Ok((root, memory_delta, address))
}

fn read_persistent((memory, address): (PersistentProfileMemory, u32)) -> u64 {
    match memory.read(address) {
        Ok(value) => hash_u32(FNV_OFFSET, value),
        Err(_error) => u64::MAX,
    }
}

fn replay_checkpoint(
    (mut graph, checkpoint): (ProfileStateGraph, ProfileMachineState),
) -> u64 {
    match graph.observe(checkpoint) {
        Ok(node) => graph_checksum(&graph, node.value()),
        Err(_error) => u64::MAX,
    }
}

/// Runs the current-profile checkpoint cost matrix and emits raw CSV samples.
///
/// # Errors
///
/// Returns an I/O error when benchmark output cannot be written.
pub fn run() -> IoResult<()> {
    let machine =
        ProfileMachine::from_source(current_profile(), CURRENT_SOURCE, vec![
            0x41,
        ])
        .map_err(|error| IoError::other(format!("benchmark load: {error}")))?;
    let mut output = stdout().lock();
    writeln!(
        output,
        "benchmark,implementation,sample,operations,nanoseconds,checksum"
    )?;
    emit_samples(
        &mut output,
        "snapshot",
        || (),
        |()| checkpoint_checksum(&black_box(machine.snapshot_state())),
    )?;
    emit_samples(
        &mut output,
        "insert-exact",
        || (ProfileStateGraph::new(), machine.snapshot_state()),
        insert_checkpoint,
    )?;
    emit_samples(
        &mut output,
        "replay-exact",
        || {
            let mut graph = ProfileStateGraph::new();
            let seed = machine.snapshot_state();
            let _seed_result = black_box(graph.observe(seed));
            (graph, machine.snapshot_state())
        },
        replay_checkpoint,
    )?;
    let (persistent, delta, address) = persistent_fixture()?;
    emit_repeated_samples(
        &mut output,
        "persistent-apply-two-cell",
        PERSISTENT_OPERATIONS,
        || (persistent.clone(), delta, address),
        apply_persistent,
    )?;
    let patched = persistent.apply(delta).map_err(|error| {
        IoError::other(format!("persistent seed: {error:?}"))
    })?;
    emit_repeated_samples(
        &mut output,
        "persistent-read-latest",
        PERSISTENT_OPERATIONS,
        || (patched.clone(), address),
        read_persistent,
    )?;
    Ok(())
}

fn emit_repeated_samples<Prepare, Input, Run>(
    output: &mut impl Write,
    implementation: &str,
    operations: usize,
    mut prepare: Prepare,
    mut run: Run,
) -> IoResult<()>
where
    Prepare: FnMut() -> Input,
    Run: FnMut(Input) -> u64,
{
    let warmup_input = black_box(prepare());
    let warmup_checksum = black_box(run(warmup_input));
    let _warmup_sink = black_box(warmup_checksum);
    let mut sample = 0u8;
    while sample < SAMPLE_COUNT {
        let inputs = std::iter::repeat_with(&mut prepare)
            .take(operations)
            .map(black_box)
            .collect::<Vec<_>>();
        let start = Instant::now();
        let mut checksum = FNV_OFFSET;
        for input in inputs {
            checksum = hash_u64(checksum, black_box(run(input)));
        }
        let nanoseconds = start.elapsed().as_nanos();
        let checksum = black_box(checksum);
        write!(
            output,
            "{PROFILE_BENCHMARK},{implementation},{sample},{operations},"
        )?;
        writeln!(output, "{nanoseconds},{checksum}")?;
        sample = sample.saturating_add(1);
    }
    Ok(())
}

fn emit_samples<Prepare, Input, Run>(
    output: &mut impl Write,
    implementation: &str,
    mut prepare: Prepare,
    mut run: Run,
) -> IoResult<()>
where
    Prepare: FnMut() -> Input,
    Run: FnMut(Input) -> u64,
{
    let warmup_input = black_box(prepare());
    let warmup_checksum = black_box(run(warmup_input));
    let _warmup_sink = black_box(warmup_checksum);
    let mut sample = 0u8;
    while sample < SAMPLE_COUNT {
        let input = black_box(prepare());
        let start = Instant::now();
        let checksum = black_box(run(input));
        let nanoseconds = start.elapsed().as_nanos();
        write!(output, "{PROFILE_BENCHMARK},{implementation},{sample},")?;
        writeln!(output, "{nanoseconds},{checksum}")?;
        sample = sample.saturating_add(1);
    }
    Ok(())
}
