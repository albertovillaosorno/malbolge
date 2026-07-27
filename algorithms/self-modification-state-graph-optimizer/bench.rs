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

use malbolge::{ProfileMachine, ProfileMachineState, current_profile};

use crate::profile_graph::ProfileStateGraph;

const CURRENT_SOURCE: &[u8] = b"(=%`qL";
const FNV_OFFSET: u64 = 14_695_981_039_346_656_037;
const FNV_PRIME: u64 = 1_099_511_628_211;
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
        "benchmark,implementation,sample,nanoseconds,checksum"
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
