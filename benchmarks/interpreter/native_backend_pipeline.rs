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
//   - Reproducible native backend select/admit/emit/verify pipeline samples.
// - Must-Not:
//   - Claim native execution speed or bypass semantic verification.
// - Allows:
//   - Inputs: one VM-derived two-step workload and both reviewed host ISAs.
//   - Outputs: raw nanosecond samples and explicit completed-work counters.
//   - Side effects: benchmark-process CPU time and stdout only.
// - Split-When:
//   - Native execution becomes measurable through a concrete call boundary.
// - Merge-When:
//   - Another benchmark owns the same backend pipeline workload and evidence.
// - Summary:
//   - Measures equivalent x86-64/AArch64 fused backend pipeline cost.
// - Description:
//   - Times selection through semantic object verification, not execution.
// - Usage:
//   - Run on an identified host/toolchain and retain stdout as raw evidence.
// - Defaults:
//   - Uses 15 samples, one warmup, fixed ISA alternation, and scales 1/2/4.
//

//! Raw fused native backend pipeline measurements for equivalent host targets.

#[path = "../../src/runtime/tiered-execution/adapter-outbound/cache/main.rs"]
pub mod execution_cache;
#[path = "../../src/runtime/tiered-execution/adapter-outbound/native/main.rs"]
pub mod execution_native;

use std::fmt::Display;
use std::hint::black_box;
use std::io::{Error as IoError, Result as IoResult, Write, stdout};
use std::time::Instant;

use malbolge::{
    ProfileMachine, ProfileMachineIoState, ProfileMachineState,
    ProfileRegisters, ProfileStepTrace, RegionEffectProgram, RunOutcome,
    current_profile, decode_profile_instruction, safe_rust_profiled_capability,
};

use crate::execution_cache::{HostIsa, HostOperatingSystem};
use crate::execution_native::{
    admit_fused_direct_sequence, emit_fused_direct_sequence_coff,
    select_verified_direct_sequence, verify_fused_direct_sequence,
};

const SAMPLE_COUNT: u8 = 15;
const SCALES: [u8; 3] = [1, 2, 4];

#[derive(Default)]
struct PipelineMeasurement {
    admission_ns: u128,
    emission_ns: u128,
    object_bytes: usize,
    selection_ns: u128,
    verification_ns: u128,
}

/// Runs the fixed pipeline matrix and emits raw CSV samples.
///
/// # Errors
///
/// Returns an I/O error if the workload cannot be constructed, a backend stage
/// rejects the reviewed workload, or writing samples to stdout fails.
fn run() -> IoResult<()> {
    let programs = rotate_jump_code_programs()?;
    let mut output = stdout().lock();
    writeln!(
        output,
        concat!(
            "benchmark,isa,scale,sample,nanoseconds,selection_ns,",
            "admission_ns,emission_ns,verification_ns,verified_objects,",
            "object_bytes"
        )
    )?;
    for scale in SCALES {
        warm_up(&programs, scale)?;
        emit_scale_samples(&mut output, &programs, scale)?;
    }
    Ok(())
}

fn emit_scale_samples(
    output: &mut impl Write,
    programs: &[RegionEffectProgram],
    scale: u8,
) -> IoResult<()> {
    let mut sample = 0u8;
    while sample < SAMPLE_COUNT {
        let order = if sample.rem_euclid(2) == 0 {
            [HostIsa::X86_64, HostIsa::AArch64]
        } else {
            [HostIsa::AArch64, HostIsa::X86_64]
        };
        for isa in order {
            let start = Instant::now();
            let measurement = run_pipeline(programs, isa, scale)?;
            let nanoseconds = start.elapsed().as_nanos();
            let isa_name = isa_label(isa);
            let PipelineMeasurement {
                admission_ns,
                emission_ns,
                object_bytes,
                selection_ns,
                verification_ns,
            } = measurement;
            writeln!(
                output,
                "native-fused-pipeline,{isa_name},{scale},{sample},\
                 {nanoseconds},{selection_ns},{admission_ns},{emission_ns},\
                 {verification_ns},{scale},{object_bytes}"
            )?;
        }
        sample = sample.saturating_add(1);
    }
    Ok(())
}

fn io_error(context: &str, error: impl Display) -> IoError {
    IoError::other(format!("{context}: {error}"))
}

const fn isa_label(isa: HostIsa) -> &'static str {
    match isa {
        HostIsa::AArch64 => "aarch64",
        HostIsa::X86_64 => "x86_64",
    }
}

fn rotate_jump_code_programs() -> IoResult<Vec<RegionEffectProgram>> {
    let mut machine = ProfileMachine::from_snapshot(rotate_jump_code_state()?);
    let mut traces = Vec::new();
    let outcome = machine
        .run_traced(2, &mut |trace: &ProfileStepTrace| traces.push(*trace))
        .map_err(|error| io_error("native benchmark trace", error))?;
    if outcome != (RunOutcome::BudgetExhausted { steps: 2 }) {
        return Err(IoError::other(
            "native benchmark trace did not run 2 steps",
        ));
    }
    traces
        .iter()
        .map(|trace| {
            RegionEffectProgram::from_profile_step_trace(trace).map_err(
                |error| {
                    IoError::other(format!(
                        "native benchmark projection: {error:?}"
                    ))
                },
            )
        })
        .collect()
}

fn rotate_jump_code_state() -> IoResult<ProfileMachineState> {
    let base =
        ProfileMachine::from_source(current_profile(), b"(=%r_L", Vec::new())
            .map_err(|error| io_error("native benchmark base load", error))?;
    let mut memory = base.snapshot_state().memory().to_vec();
    let rotate_cell = (33u32..=126u32)
        .find(|cell| decode_profile_instruction(*cell, 5) == Some(b'*'))
        .ok_or_else(|| IoError::other("phase-five rotate cell missing"))?;
    *memory
        .get_mut(5)
        .ok_or_else(|| IoError::other("benchmark code cell 5 missing"))? =
        rotate_cell;
    let jump_code_cell = (33u32..=126u32)
        .find(|cell| decode_profile_instruction(*cell, 6) == Some(b'i'))
        .ok_or_else(|| IoError::other("phase-six jump-code cell missing"))?;
    *memory
        .get_mut(6)
        .ok_or_else(|| IoError::other("benchmark code cell 6 missing"))? =
        jump_code_cell;
    *memory
        .get_mut(7)
        .ok_or_else(|| IoError::other("benchmark data cell 7 missing"))? = 10;
    *memory
        .get_mut(8)
        .ok_or_else(|| IoError::other("benchmark data cell 8 missing"))? = 10;
    *memory
        .get_mut(10)
        .ok_or_else(|| IoError::other("benchmark target cell 10 missing"))? =
        35;
    let io = ProfileMachineIoState::new(Vec::new(), 0, Vec::new(), None)
        .map_err(|error| io_error("native benchmark IO", error))?;
    ProfileMachineState::new(
        current_profile(),
        memory,
        ProfileRegisters {
            accumulator: 20,
            code_pointer: 5,
            data_pointer: 7,
        },
        io,
    )
    .map_err(|error| io_error("native benchmark state", error))
}

fn run_pipeline(
    programs: &[RegionEffectProgram],
    isa: HostIsa,
    scale: u8,
) -> IoResult<PipelineMeasurement> {
    let mut measurement = PipelineMeasurement::default();
    let mut iteration = 0u8;
    while iteration < scale {
        let selection_start = Instant::now();
        let plan = select_verified_direct_sequence(
            black_box(programs),
            safe_rust_profiled_capability(),
            HostOperatingSystem::Windows,
            isa,
        )
        .map_err(|error| io_error("native benchmark select", error))?;
        measurement.selection_ns = measurement
            .selection_ns
            .saturating_add(selection_start.elapsed().as_nanos());

        let admission_start = Instant::now();
        let admission = admit_fused_direct_sequence(&plan)
            .map_err(|error| io_error("native benchmark admission", error))?;
        measurement.admission_ns = measurement
            .admission_ns
            .saturating_add(admission_start.elapsed().as_nanos());

        let emission_start = Instant::now();
        let candidate = emit_fused_direct_sequence_coff(&admission)
            .map_err(|error| io_error("native benchmark emission", error))?;
        measurement.emission_ns = measurement
            .emission_ns
            .saturating_add(emission_start.elapsed().as_nanos());

        let verification_start = Instant::now();
        let verified = verify_fused_direct_sequence(&candidate, &admission)
            .map_err(|error| {
                io_error("native benchmark verification", error)
            })?;
        measurement.verification_ns = measurement
            .verification_ns
            .saturating_add(verification_start.elapsed().as_nanos());
        measurement.object_bytes = measurement
            .object_bytes
            .saturating_add(black_box(verified.object().len()));
        iteration = iteration.saturating_add(1);
    }
    Ok(measurement)
}

fn warm_up(programs: &[RegionEffectProgram], scale: u8) -> IoResult<()> {
    for isa in [HostIsa::X86_64, HostIsa::AArch64] {
        let _measurement = run_pipeline(programs, isa, scale)?;
    }
    Ok(())
}

fn main() -> IoResult<()> {
    run()
}
