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
//   - Inputs: reviewed VM-derived two-step workloads and both host ISAs.
//   - Outputs: raw nanosecond samples and explicit completed-work counters.
//   - Side effects: benchmark-process CPU time and stdout only.
// - Split-When:
//   - Native execution becomes measurable through a concrete call boundary.
// - Merge-When:
//   - Another benchmark owns the same backend pipeline workload and evidence.
// - Summary:
//   - Measures equivalent x86-64/AArch64 fused backend pipeline cost.
// - Description:
//   - Compares cold uncached and warm exact-cache preparation, not execution.
// - Usage:
//   - Run on an identified host/toolchain and retain stdout as raw evidence.
// - Defaults:
//   - Uses 15 samples, one warmup per mode, alternation, and scales 1/2/4.
//

//! Raw fused native backend pipeline measurements for reviewed host targets.

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
    current_profile, decode_profile_instruction,
    profile_cell_decodes_to_no_operation, safe_rust_profiled_capability,
};

use crate::execution_cache::{HostIsa, HostOperatingSystem};
use crate::execution_native::{
    DirectFusedSequenceAdmission, DirectHost, VerifiedDirectNativeCache,
    admit_cached_fused_direct_sequence, admit_fused_direct_sequence,
    emit_fused_direct_sequence_coff, select_cached_verified_direct_sequence,
    select_verified_direct_sequence, verify_fused_direct_sequence,
};

const SAMPLE_COUNT: u8 = 15;
const SCALES: [u8; 3] = [1, 2, 4];

#[derive(Clone, Copy)]
enum PipelineMode {
    Cold,
    Warm,
}

#[derive(Clone, Copy)]
enum Workload {
    CrazyPair,
    NoOperationOutput,
    RotateJumpCode,
}

#[derive(Clone, Copy)]
struct PipelineCase {
    isa: HostIsa,
    mode: PipelineMode,
    scale: u8,
    workload: Workload,
}

struct PipelineSample {
    case: PipelineCase,
    measurement: PipelineMeasurement,
    nanoseconds: u128,
    sample: u8,
}

#[derive(Default)]
struct PipelineMeasurement {
    admission_ns: u128,
    cache_hits: usize,
    cache_insertions: usize,
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
    let workloads = [
        (Workload::CrazyPair, crazy_pair_programs()?),
        (Workload::NoOperationOutput, no_operation_output_programs()?),
        (Workload::RotateJumpCode, rotate_jump_code_programs()?),
    ];
    let mut output = stdout().lock();
    writeln!(
        output,
        concat!(
            "benchmark,workload,mode,isa,scale,sample,nanoseconds,",
            "selection_ns,admission_ns,emission_ns,verification_ns,",
            "cache_hits,cache_insertions,verified_objects,object_bytes"
        )
    )?;
    for (workload, programs) in workloads {
        for scale in SCALES {
            warm_up(&programs, workload, scale)?;
            emit_scale_samples(&mut output, &programs, workload, scale)?;
        }
    }
    Ok(())
}

fn emit_scale_samples(
    output: &mut impl Write,
    programs: &[RegionEffectProgram],
    workload: Workload,
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
            let modes = if sample.rem_euclid(2) == 0 {
                [PipelineMode::Cold, PipelineMode::Warm]
            } else {
                [PipelineMode::Warm, PipelineMode::Cold]
            };
            for mode in modes {
                let case = PipelineCase {
                    isa,
                    mode,
                    scale,
                    workload,
                };
                let mut cache = prepare_cache(programs, case)?;
                let start = Instant::now();
                let measurement = run_pipeline(programs, case, &mut cache)?;
                let result = PipelineSample {
                    case,
                    measurement,
                    nanoseconds: start.elapsed().as_nanos(),
                    sample,
                };
                emit_sample(output, &result)?;
            }
        }
        sample = sample.saturating_add(1);
    }
    Ok(())
}

fn io_error(context: &str, error: impl Display) -> IoError {
    IoError::other(format!("{context}: {error}"))
}

fn emit_sample(
    output: &mut impl Write,
    result: &PipelineSample,
) -> IoResult<()> {
    let PipelineMeasurement {
        admission_ns,
        cache_hits,
        cache_insertions,
        emission_ns,
        object_bytes,
        selection_ns,
        verification_ns,
    } = &result.measurement;
    let PipelineCase {
        isa,
        mode,
        scale,
        workload,
    } = result.case;
    let nanoseconds = result.nanoseconds;
    let sample = result.sample;
    writeln!(
        output,
        "native-fused-pipeline,{},{},{},{scale},{sample},{nanoseconds},\
         {selection_ns},{admission_ns},{emission_ns},{verification_ns},\
         {cache_hits},{cache_insertions},{scale},{object_bytes}",
        workload_label(workload),
        mode_label(mode),
        isa_label(isa),
    )
}

const fn workload_label(workload: Workload) -> &'static str {
    match workload {
        Workload::CrazyPair => "crazy-pair",
        Workload::NoOperationOutput => "no-operation-output",
        Workload::RotateJumpCode => "rotate-jump-code",
    }
}

const fn mode_label(mode: PipelineMode) -> &'static str {
    match mode {
        PipelineMode::Cold => "cold-uncached",
        PipelineMode::Warm => "warm-exact-cache",
    }
}

const fn isa_label(isa: HostIsa) -> &'static str {
    match isa {
        HostIsa::AArch64 => "aarch64",
        HostIsa::X86_64 => "x86_64",
    }
}

fn crazy_pair_programs() -> IoResult<Vec<RegionEffectProgram>> {
    let mut machine = ProfileMachine::from_snapshot(crazy_pair_state()?);
    let mut traces = Vec::new();
    let outcome = machine
        .run_traced(2, &mut |trace: &ProfileStepTrace| traces.push(*trace))
        .map_err(|error| io_error("crazy pair benchmark trace", error))?;
    if outcome != (RunOutcome::BudgetExhausted { steps: 2 }) {
        return Err(IoError::other(
            "crazy pair benchmark trace did not run 2 steps",
        ));
    }
    traces
        .iter()
        .map(|trace| {
            RegionEffectProgram::from_profile_step_trace(trace).map_err(
                |error| {
                    IoError::other(format!(
                        "crazy pair benchmark projection: {error:?}"
                    ))
                },
            )
        })
        .collect()
}

fn crazy_pair_state() -> IoResult<ProfileMachineState> {
    let base =
        ProfileMachine::from_source(current_profile(), b"(=%r_L", Vec::new())
            .map_err(|error| io_error("crazy pair benchmark load", error))?;
    let mut memory = base.snapshot_state().memory().to_vec();
    for code_pointer in [5u32, 6u32] {
        let cell = (33u32..=126u32)
            .find(|cell| {
                decode_profile_instruction(*cell, code_pointer) == Some(b'p')
            })
            .ok_or_else(|| IoError::other("crazy pair code cell missing"))?;
        let index = usize::try_from(code_pointer)
            .map_err(|error| io_error("crazy pair code index", error))?;
        *memory.get_mut(index).ok_or_else(|| {
            IoError::other("crazy pair code address missing")
        })? = cell;
    }
    *memory
        .get_mut(7)
        .ok_or_else(|| IoError::other("crazy pair data cell 7 missing"))? = 10;
    *memory
        .get_mut(8)
        .ok_or_else(|| IoError::other("crazy pair data cell 8 missing"))? = 20;
    let io = ProfileMachineIoState::new(Vec::new(), 0, Vec::new(), None)
        .map_err(|error| io_error("crazy pair benchmark IO", error))?;
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
    .map_err(|error| io_error("crazy pair benchmark state", error))
}

fn no_operation_output_programs() -> IoResult<Vec<RegionEffectProgram>> {
    let mut machine =
        ProfileMachine::from_snapshot(no_operation_output_state()?);
    let mut traces = Vec::new();
    let outcome = machine
        .run_traced(2, &mut |trace: &ProfileStepTrace| traces.push(*trace))
        .map_err(|error| io_error("no-op/output benchmark trace", error))?;
    if outcome != (RunOutcome::BudgetExhausted { steps: 2 }) {
        return Err(IoError::other(
            "no-op/output benchmark trace did not run 2 steps",
        ));
    }
    traces
        .iter()
        .map(|trace| {
            RegionEffectProgram::from_profile_step_trace(trace).map_err(
                |error| {
                    IoError::other(format!(
                        "no-op/output benchmark projection: {error:?}"
                    ))
                },
            )
        })
        .collect()
}

fn no_operation_output_state() -> IoResult<ProfileMachineState> {
    let base =
        ProfileMachine::from_source(current_profile(), b"(=%r_L", Vec::new())
            .map_err(|error| io_error("no-op/output benchmark load", error))?;
    let mut memory = base.snapshot_state().memory().to_vec();
    let no_operation_cell = (33u32..=126u32)
        .find(|cell| profile_cell_decodes_to_no_operation(*cell, 5))
        .ok_or_else(|| {
            IoError::other("phase-five no-operation cell missing")
        })?;
    *memory
        .get_mut(5)
        .ok_or_else(|| IoError::other("no-op/output code cell 5 missing"))? =
        no_operation_cell;
    let output_cell = (33u32..=126u32)
        .find(|cell| decode_profile_instruction(*cell, 6) == Some(b'<'))
        .ok_or_else(|| IoError::other("phase-six output cell missing"))?;
    *memory
        .get_mut(6)
        .ok_or_else(|| IoError::other("no-op/output code cell 6 missing"))? =
        output_cell;
    let io = ProfileMachineIoState::new(Vec::new(), 0, Vec::new(), None)
        .map_err(|error| io_error("no-op/output benchmark IO", error))?;
    ProfileMachineState::new(
        current_profile(),
        memory,
        ProfileRegisters {
            accumulator: 0x00ab_cdef,
            code_pointer: 5,
            data_pointer: 7,
        },
        io,
    )
    .map_err(|error| io_error("no-op/output benchmark state", error))
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
    case: PipelineCase,
    cache: &mut VerifiedDirectNativeCache,
) -> IoResult<PipelineMeasurement> {
    let mut measurement = PipelineMeasurement::default();
    let mut iteration = 0u8;
    while iteration < case.scale {
        let admission = match case.mode {
            PipelineMode::Cold => {
                select_admit_cold(programs, case.isa, &mut measurement)?
            },
            PipelineMode::Warm => {
                select_admit_warm(programs, case.isa, cache, &mut measurement)?
            },
        };
        emit_verify(&admission, &mut measurement)?;
        iteration = iteration.saturating_add(1);
    }
    validate_cache_activity(case.mode, case.scale, &measurement)?;
    Ok(measurement)
}

fn select_admit_cold(
    programs: &[RegionEffectProgram],
    isa: HostIsa,
    measurement: &mut PipelineMeasurement,
) -> IoResult<DirectFusedSequenceAdmission> {
    let selection_start = Instant::now();
    let plan = select_verified_direct_sequence(
        black_box(programs),
        safe_rust_profiled_capability(),
        HostOperatingSystem::Windows,
        isa,
    )
    .map_err(|error| io_error("native benchmark cold select", error))?;
    measurement.selection_ns = measurement
        .selection_ns
        .saturating_add(selection_start.elapsed().as_nanos());
    let admission_start = Instant::now();
    let admission = admit_fused_direct_sequence(&plan)
        .map_err(|error| io_error("native benchmark cold admission", error))?;
    measurement.admission_ns = measurement
        .admission_ns
        .saturating_add(admission_start.elapsed().as_nanos());
    Ok(admission)
}

fn select_admit_warm(
    programs: &[RegionEffectProgram],
    isa: HostIsa,
    cache: &mut VerifiedDirectNativeCache,
    measurement: &mut PipelineMeasurement,
) -> IoResult<DirectFusedSequenceAdmission> {
    let selection_start = Instant::now();
    let plan = select_cached_verified_direct_sequence(
        black_box(programs),
        safe_rust_profiled_capability(),
        DirectHost::new(HostOperatingSystem::Windows, isa),
        cache,
    )
    .map_err(|error| io_error("native benchmark warm select", error))?;
    measurement.selection_ns = measurement
        .selection_ns
        .saturating_add(selection_start.elapsed().as_nanos());
    measurement.cache_hits =
        measurement.cache_hits.saturating_add(plan.cache_hits());
    measurement.cache_insertions = measurement
        .cache_insertions
        .saturating_add(plan.cache_insertions());
    let admission_start = Instant::now();
    let admission = admit_cached_fused_direct_sequence(&plan)
        .map_err(|error| io_error("native benchmark warm admission", error))?;
    measurement.admission_ns = measurement
        .admission_ns
        .saturating_add(admission_start.elapsed().as_nanos());
    Ok(admission)
}

fn emit_verify(
    admission: &DirectFusedSequenceAdmission,
    measurement: &mut PipelineMeasurement,
) -> IoResult<()> {
    let emission_start = Instant::now();
    let candidate = emit_fused_direct_sequence_coff(admission)
        .map_err(|error| io_error("native benchmark emission", error))?;
    measurement.emission_ns = measurement
        .emission_ns
        .saturating_add(emission_start.elapsed().as_nanos());
    let verification_start = Instant::now();
    let verified = verify_fused_direct_sequence(&candidate, admission)
        .map_err(|error| io_error("native benchmark verification", error))?;
    measurement.verification_ns = measurement
        .verification_ns
        .saturating_add(verification_start.elapsed().as_nanos());
    measurement.object_bytes = measurement
        .object_bytes
        .saturating_add(black_box(verified.object().len()));
    Ok(())
}

fn prepare_cache(
    programs: &[RegionEffectProgram],
    case: PipelineCase,
) -> IoResult<VerifiedDirectNativeCache> {
    let mut cache = VerifiedDirectNativeCache::default();
    if matches!(case.mode, PipelineMode::Warm) {
        let seeded = select_cached_verified_direct_sequence(
            programs,
            safe_rust_profiled_capability(),
            DirectHost::new(HostOperatingSystem::Windows, case.isa),
            &mut cache,
        )
        .map_err(|error| io_error("native benchmark cache seed", error))?;
        if seeded.cache_hits() != 0 || seeded.cache_insertions() != 2 {
            return Err(IoError::other("native benchmark cache seed drifted"));
        }
    }
    Ok(cache)
}

fn validate_cache_activity(
    mode: PipelineMode,
    scale: u8,
    measurement: &PipelineMeasurement,
) -> IoResult<()> {
    let expected_hits = match mode {
        PipelineMode::Cold => 0,
        PipelineMode::Warm => usize::from(scale).saturating_mul(2),
    };
    if measurement.cache_hits != expected_hits
        || measurement.cache_insertions != 0
    {
        return Err(IoError::other(
            "native benchmark timed cache activity drifted",
        ));
    }
    Ok(())
}

fn warm_up(
    programs: &[RegionEffectProgram],
    workload: Workload,
    scale: u8,
) -> IoResult<()> {
    for isa in [HostIsa::X86_64, HostIsa::AArch64] {
        for mode in [PipelineMode::Cold, PipelineMode::Warm] {
            let case = PipelineCase {
                isa,
                mode,
                scale,
                workload,
            };
            let mut cache = prepare_cache(programs, case)?;
            let _measurement = run_pipeline(programs, case, &mut cache)?;
        }
    }
    Ok(())
}

fn main() -> IoResult<()> {
    run()
}
