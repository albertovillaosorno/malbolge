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
//   - Linux x86-64 interpreter and process-backed native timing samples.
// - Must-Not:
//   - Generalize host results or bypass normative/native semantic admission.
// - Allows:
//   - Inputs: one normative VM-derived two-step rotate/output workload.
//   - Outputs: raw interpreter/lifecycle/resident timing and call counters.
//   - Side effects: compile/spawn a temporary tracked POSIX worker and stdout.
// - Split-When:
//   - Another host/ISA gains independently executable benchmark evidence.
// - Merge-When:
//   - One portable host-real benchmark owns equivalent process-call evidence.
// - Summary:
//   - Measures normative interpretation beside concrete process execution.
// - Description:
//   - Compares interpretation, remap-per-call, and resident native execution.
// - Usage:
//   - Run on an identified Linux x86-64 host and retain stdout as raw evidence.
// - Defaults:
//   - Uses 15 samples, one warmup per mode, alternation, and scales 1/2/4.
//

//! Raw interpreter and host-real fused process execution measurements.

#[path = "../../src/runtime/tiered-execution/adapter-outbound/cache/main.rs"]
pub mod execution_cache;
#[path = "../../src/runtime/tiered-execution/adapter-outbound/native/main.rs"]
pub mod execution_native;

use std::fmt::{Debug, Display};
use std::fs;
use std::hint::black_box;
use std::io::{Error as IoError, ErrorKind, Result as IoResult, Write, stdout};
use std::path::{Path, PathBuf};
use std::process::{Command, id as process_id};
use std::time::Instant;

use malbolge::{
    ProfileMachine, ProfileMachineIoState, ProfileMachineState,
    ProfileRegisters, ProfileStepTrace, RegionEffectProgram, RunOutcome,
    current_profile, decode_profile_instruction, safe_rust_profiled_capability,
};

use crate::execution_cache::{HostIsa, HostOperatingSystem};
use crate::execution_native::{
    DirectFusedNativeExecutableOwner, NativeProcessHost,
    NativeProcessSessionConfig, NativeRegionBuffers,
    NativeRegionInvocationOutcome, PreparedDirectFusedInvocation,
    VerifiedDirectFusedSequenceObjectArtifact, admit_fused_direct_sequence,
    emit_fused_direct_sequence_coff,
    execute_verified_direct_fused_native_with_host,
    select_verified_direct_sequence, verify_fused_direct_sequence,
};

const CLANG_ARGS: [&str; 20] = [
    "-std=c23",
    "-Wall",
    "-Wextra",
    "-Wpedantic",
    "-Wconversion",
    "-Wsign-conversion",
    "-Wshadow",
    "-Wformat=2",
    "-Wundef",
    "-Wcast-qual",
    "-Wcast-align",
    "-Wswitch-enum",
    "-Wswitch-default",
    "-Wvla",
    "-Wimplicit-fallthrough",
    "-Wstrict-prototypes",
    "-Wmissing-prototypes",
    "-Wmissing-variable-declarations",
    "-Wnull-dereference",
    "-Werror",
];
const SAMPLE_COUNT: u8 = 15;
const SCALES: [u8; 3] = [1, 2, 4];

#[derive(Clone, Copy)]
enum ExecutionMode {
    Interpreter,
    Lifecycle,
    LoadRelease,
    Preparation,
    Resident,
}

struct ExecutionFixture {
    artifact: VerifiedDirectFusedSequenceObjectArtifact,
    final_memory: Vec<u32>,
    final_output: Vec<u8>,
    initial_memory: Vec<u32>,
    initial_output: Vec<u8>,
    input: Vec<u8>,
    interpreter_entry: ProfileMachineState,
    interpreter_exit: ProfileMachineState,
    programs: Vec<RegionEffectProgram>,
}

struct NativeCallBuffers {
    memory: Vec<u32>,
    output: Vec<u8>,
}

struct ExecutionSample {
    calls: u8,
    mode: ExecutionMode,
    nanoseconds: u128,
    object_bytes: usize,
    retained_mapped_bytes: usize,
    sample: u8,
    scale: u8,
}

fn io_error(context: &str, error: impl Display) -> IoError {
    IoError::other(format!("{context}: {error}"))
}

fn io_debug_error(context: &str, error: impl Debug) -> IoError {
    IoError::other(format!("{context}: {error:?}"))
}

fn process_worker_directory() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR"))
        .join(".temp/native_process_execution_benchmark")
        .join(process_id().to_string())
}

fn compile_process_worker(directory: &Path) -> IoResult<PathBuf> {
    let root = Path::new(env!("CARGO_MANIFEST_DIR"));
    let clang = root.join(".dependencies/llvm/22.1.8/jig-bin/clang.bin");
    if !clang.is_file() {
        return Err(IoError::new(
            ErrorKind::NotFound,
            format!("pinned Clang missing: {}", clang.display()),
        ));
    }
    fs::create_dir_all(directory)?;
    let executable = directory.join("native-process-worker-posix");
    let source = root.join(concat!(
        "src/runtime/tiered-execution/adapter-outbound/native/",
        "native_process_worker_posix.c",
    ));
    let include =
        root.join("src/runtime/tiered-execution/adapter-outbound/native");
    let output = Command::new(&clang)
        .current_dir(root)
        .args(CLANG_ARGS)
        .arg(format!("-I{}", include.display()))
        .arg(&source)
        .arg("-o")
        .arg(&executable)
        .output()
        .map_err(|error| io_error("native execution worker compile", error))?;
    if !output.status.success() {
        return Err(IoError::other(format!(
            "native execution worker compilation failed: {}",
            String::from_utf8_lossy(&output.stderr)
        )));
    }
    Ok(executable)
}

fn spawn_process_host(executable: PathBuf) -> IoResult<NativeProcessHost> {
    NativeProcessSessionConfig::new(executable)
        .spawn()
        .map(NativeProcessHost::new)
        .map_err(|error| io_debug_error("native execution worker spawn", error))
}

fn workload_state() -> IoResult<ProfileMachineState> {
    let base =
        ProfileMachine::from_source(current_profile(), b"(=%r_L", Vec::new())
            .map_err(|error| io_error("native execution base load", error))?;
    let mut memory = base.snapshot_state().memory().to_vec();
    *memory.get_mut(5).ok_or_else(|| {
        IoError::other("native execution code cell 5 missing")
    })? = 34;
    let output_cell = (33u32..=126u32)
        .find(|cell| decode_profile_instruction(*cell, 6) == Some(b'<'))
        .ok_or_else(|| IoError::other("phase-six output cell missing"))?;
    *memory.get_mut(6).ok_or_else(|| {
        IoError::other("native execution code cell 6 missing")
    })? = output_cell;
    *memory.get_mut(7).ok_or_else(|| {
        IoError::other("native execution data cell 7 missing")
    })? = 10;
    let io = ProfileMachineIoState::new(Vec::new(), 0, Vec::new(), None)
        .map_err(|error| io_error("native execution IO", error))?;
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
    .map_err(|error| io_error("native execution state", error))
}

fn verified_fused_artifact(
    programs: &[RegionEffectProgram],
) -> IoResult<VerifiedDirectFusedSequenceObjectArtifact> {
    let plan = select_verified_direct_sequence(
        programs,
        safe_rust_profiled_capability(),
        HostOperatingSystem::Windows,
        HostIsa::X86_64,
    )
    .map_err(|error| io_error("native execution select", error))?;
    let admission = admit_fused_direct_sequence(&plan)
        .map_err(|error| io_error("native execution admission", error))?;
    let candidate = emit_fused_direct_sequence_coff(&admission)
        .map_err(|error| io_error("native execution emission", error))?;
    verify_fused_direct_sequence(&candidate, &admission)
        .map_err(|error| io_error("native execution verification", error))
}

fn execution_fixture() -> IoResult<ExecutionFixture> {
    let state = workload_state()?;
    let full_initial_memory = state.memory().to_vec();
    let input = state.io().input().to_vec();
    let interpreter_entry = state.clone();
    let mut machine = ProfileMachine::from_snapshot(state);
    let mut traces = Vec::new();
    let outcome = machine
        .run_traced(2, &mut |trace: &ProfileStepTrace| traces.push(*trace))
        .map_err(|error| io_error("native execution trace", error))?;
    if outcome != (RunOutcome::BudgetExhausted { steps: 2 }) {
        return Err(IoError::other("two-step benchmark outcome drifted"));
    }
    let programs = traces
        .iter()
        .map(RegionEffectProgram::from_profile_step_trace)
        .collect::<Result<Vec<_>, _>>()
        .map_err(|error| {
            io_debug_error("native execution projection", error)
        })?;
    let artifact = verified_fused_artifact(&programs)?;
    let required =
        usize::try_from(artifact.admission().program().required_memory_words())
            .map_err(|error| {
                io_error("native execution memory footprint", error)
            })?;
    let initial_memory = full_initial_memory
        .get(..required)
        .ok_or_else(|| {
            IoError::other("native execution initial memory too short")
        })?
        .to_vec();
    let final_memory = machine
        .memory()
        .get(..required)
        .ok_or_else(|| {
            IoError::other("native execution final memory too short")
        })?
        .to_vec();
    let interpreter_exit = machine.snapshot_state();
    let output_capacity = machine.output().len().max(1);
    let initial_output = vec![0u8; output_capacity];
    let mut final_output = initial_output.clone();
    final_output
        .get_mut(..machine.output().len())
        .ok_or_else(|| {
            IoError::other("native execution output exceeds capacity")
        })?
        .copy_from_slice(machine.output());
    Ok(ExecutionFixture {
        artifact,
        final_memory,
        final_output,
        initial_memory,
        initial_output,
        input,
        interpreter_entry,
        interpreter_exit,
        programs,
    })
}

fn validate_result(
    fixture: &ExecutionFixture,
    outcome: NativeRegionInvocationOutcome,
    memory: &[u32],
    output: &[u8],
) -> IoResult<()> {
    if matches!(outcome, NativeRegionInvocationOutcome::Applied(_))
        && memory == fixture.final_memory
        && output == fixture.final_output
    {
        Ok(())
    } else {
        Err(IoError::other(
            "native execution benchmark semantic completion drifted",
        ))
    }
}

fn execute_one_shot(
    fixture: &ExecutionFixture,
    host: &mut NativeProcessHost,
) -> IoResult<()> {
    let mut memory = fixture.initial_memory.clone();
    let mut output = fixture.initial_output.clone();
    let prepared = PreparedDirectFusedInvocation::new(
        &fixture.artifact,
        NativeRegionBuffers::new(&mut memory, &fixture.input, &mut output),
    )
    .map_err(|error| io_error("native execution one-shot prepare", error))?;
    let outcome =
        execute_verified_direct_fused_native_with_host(host, prepared)
            .map_err(|error| io_error("native execution one-shot", error))?;
    validate_result(fixture, outcome, &memory, &output)
}

fn execute_resident(
    fixture: &ExecutionFixture,
    host: &mut NativeProcessHost,
    owner: &DirectFusedNativeExecutableOwner,
    buffers: &mut NativeCallBuffers,
) -> IoResult<NativeRegionInvocationOutcome> {
    owner
        .execute(
            host,
            NativeRegionBuffers::new(
                &mut buffers.memory,
                &fixture.input,
                &mut buffers.output,
            ),
        )
        .map_err(|error| io_error("native execution resident call", error))
}

fn native_call_buffers(fixture: &ExecutionFixture) -> NativeCallBuffers {
    NativeCallBuffers {
        memory: fixture.initial_memory.clone(),
        output: fixture.initial_output.clone(),
    }
}

fn validate_interpreter(
    fixture: &ExecutionFixture,
    machine: &ProfileMachine,
) -> IoResult<()> {
    let expected = &fixture.interpreter_exit;
    let expected_io = expected.io();
    if machine.input() == expected_io.input()
        && machine.input_consumed() == expected_io.input_consumed()
        && machine.memory() == expected.memory()
        && machine.output() == expected_io.output()
        && machine.registers() == expected.registers()
        && machine.termination() == expected_io.termination()
    {
        Ok(())
    } else {
        Err(IoError::other(
            "native execution interpreter completion drifted",
        ))
    }
}

fn measure_interpreter(
    fixture: &ExecutionFixture,
    scale: u8,
) -> IoResult<(u128, usize)> {
    let mut machines = Vec::with_capacity(usize::from(scale));
    for _index in 0..scale {
        machines.push(ProfileMachine::from_snapshot(
            fixture.interpreter_entry.clone(),
        ));
    }
    let start = Instant::now();
    for machine in &mut machines {
        let outcome = machine
            .run(2)
            .map_err(|error| io_error("native execution interpreter", error))?;
        if outcome != (RunOutcome::BudgetExhausted { steps: 2 }) {
            return Err(IoError::other(
                "native execution interpreter outcome drifted",
            ));
        }
    }
    let nanoseconds = start.elapsed().as_nanos();
    for machine in &machines {
        validate_interpreter(fixture, machine)?;
    }
    Ok((nanoseconds, 0))
}

fn measure_lifecycle(
    fixture: &ExecutionFixture,
    host: &mut NativeProcessHost,
    scale: u8,
) -> IoResult<(u128, usize)> {
    let start = Instant::now();
    let mut call = 0u8;
    while call < scale {
        execute_one_shot(black_box(fixture), host)?;
        call = call.saturating_add(1);
    }
    Ok((start.elapsed().as_nanos(), 0))
}

fn measure_load_release(
    fixture: &ExecutionFixture,
    host: &mut NativeProcessHost,
    scale: u8,
) -> IoResult<(u128, usize)> {
    let start = Instant::now();
    let mut cycle = 0u8;
    while cycle < scale {
        let owner =
            DirectFusedNativeExecutableOwner::load(host, &fixture.artifact)
                .map_err(|error| {
                    io_error("native execution load-only load", error)
                })?;
        owner.release(host).map_err(|error| {
            io_error("native execution load-only release", error)
        })?;
        cycle = cycle.saturating_add(1);
    }
    Ok((start.elapsed().as_nanos(), 0))
}

fn measure_preparation(
    fixture: &ExecutionFixture,
    scale: u8,
) -> IoResult<(u128, usize)> {
    let start = Instant::now();
    let mut prepared = Vec::with_capacity(usize::from(scale));
    let mut cycle = 0u8;
    while cycle < scale {
        prepared.push(verified_fused_artifact(black_box(&fixture.programs))?);
        cycle = cycle.saturating_add(1);
    }
    let nanoseconds = start.elapsed().as_nanos();
    if prepared.iter().all(|artifact| {
        artifact.object() == fixture.artifact.object()
            && artifact.key() == fixture.artifact.key()
    }) {
        Ok((nanoseconds, 0))
    } else {
        Err(IoError::other(
            "native execution preparation artifact drifted",
        ))
    }
}

fn measure_resident(
    fixture: &ExecutionFixture,
    host: &mut NativeProcessHost,
    scale: u8,
) -> IoResult<(u128, usize)> {
    let owner = DirectFusedNativeExecutableOwner::load(host, &fixture.artifact)
        .map_err(|error| io_error("native execution resident load", error))?;
    let mapped_bytes = owner.resident_weight().mapped_bytes();
    let mut buffers = Vec::with_capacity(usize::from(scale));
    for _index in 0..scale {
        buffers.push(native_call_buffers(fixture));
    }
    let mut outcomes = Vec::with_capacity(usize::from(scale));
    let start = Instant::now();
    let result = (|| -> IoResult<()> {
        for call_buffers in &mut buffers {
            outcomes.push(execute_resident(
                black_box(fixture),
                host,
                &owner,
                call_buffers,
            )?);
        }
        Ok(())
    })();
    let nanoseconds = start.elapsed().as_nanos();
    for (outcome, call_buffers) in outcomes.into_iter().zip(&buffers) {
        validate_result(
            fixture,
            outcome,
            &call_buffers.memory,
            &call_buffers.output,
        )?;
    }
    let release = owner
        .release(host)
        .map_err(|error| io_error("native execution resident release", error));
    result?;
    release?;
    Ok((nanoseconds, mapped_bytes))
}

fn measure(
    fixture: &ExecutionFixture,
    host: &mut NativeProcessHost,
    mode: ExecutionMode,
    scale: u8,
) -> IoResult<(u128, usize)> {
    match mode {
        ExecutionMode::Interpreter => measure_interpreter(fixture, scale),
        ExecutionMode::Lifecycle => measure_lifecycle(fixture, host, scale),
        ExecutionMode::LoadRelease => {
            measure_load_release(fixture, host, scale)
        },
        ExecutionMode::Preparation => measure_preparation(fixture, scale),
        ExecutionMode::Resident => measure_resident(fixture, host, scale),
    }
}

const fn mode_label(mode: ExecutionMode) -> &'static str {
    match mode {
        ExecutionMode::Interpreter => "interpreter",
        ExecutionMode::Lifecycle => "one-shot-lifecycle",
        ExecutionMode::LoadRelease => "load-release",
        ExecutionMode::Preparation => "object-preparation",
        ExecutionMode::Resident => "resident-call",
    }
}

const fn completed_calls(mode: ExecutionMode, scale: u8) -> u8 {
    match mode {
        ExecutionMode::Interpreter
        | ExecutionMode::Lifecycle
        | ExecutionMode::Resident => scale,
        ExecutionMode::LoadRelease | ExecutionMode::Preparation => 0,
    }
}

fn emit_sample(
    output: &mut impl Write,
    sample: &ExecutionSample,
) -> IoResult<()> {
    writeln!(
        output,
        "native-fused-process-execution,{},{},{},{},{},{},{},{}",
        mode_label(sample.mode),
        sample.scale,
        sample.sample,
        sample.nanoseconds,
        sample.calls,
        sample.object_bytes,
        sample.retained_mapped_bytes,
        sample.calls
    )
}

fn warm_up(
    fixture: &ExecutionFixture,
    host: &mut NativeProcessHost,
    scale: u8,
) -> IoResult<()> {
    for mode in [
        ExecutionMode::Interpreter,
        ExecutionMode::Lifecycle,
        ExecutionMode::LoadRelease,
        ExecutionMode::Preparation,
        ExecutionMode::Resident,
    ] {
        let _measurement = measure(fixture, host, mode, scale)?;
    }
    Ok(())
}

fn emit_scale_samples(
    output: &mut impl Write,
    fixture: &ExecutionFixture,
    host: &mut NativeProcessHost,
    scale: u8,
) -> IoResult<()> {
    let mut sample = 0u8;
    while sample < SAMPLE_COUNT {
        let order = if sample.rem_euclid(2) == 0 {
            [
                ExecutionMode::Interpreter,
                ExecutionMode::Preparation,
                ExecutionMode::LoadRelease,
                ExecutionMode::Lifecycle,
                ExecutionMode::Resident,
            ]
        } else {
            [
                ExecutionMode::Resident,
                ExecutionMode::Lifecycle,
                ExecutionMode::LoadRelease,
                ExecutionMode::Preparation,
                ExecutionMode::Interpreter,
            ]
        };
        for mode in order {
            let (nanoseconds, retained_mapped_bytes) =
                measure(fixture, host, mode, scale)?;
            emit_sample(output, &ExecutionSample {
                calls: completed_calls(mode, scale),
                mode,
                nanoseconds,
                object_bytes: fixture.artifact.object().len(),
                retained_mapped_bytes,
                sample,
                scale,
            })?;
        }
        sample = sample.saturating_add(1);
    }
    Ok(())
}

fn run() -> IoResult<()> {
    if !cfg!(all(target_os = "linux", target_arch = "x86_64")) {
        return Err(IoError::other(
            "native process execution benchmark requires Linux x86-64",
        ));
    }
    let directory = process_worker_directory();
    match fs::remove_dir_all(&directory) {
        Ok(()) => {},
        Err(error) if error.kind() == ErrorKind::NotFound => {},
        Err(error) => return Err(error),
    }
    let result = (|| -> IoResult<()> {
        let executable = compile_process_worker(&directory)?;
        let fixture = execution_fixture()?;
        let mut host = spawn_process_host(executable)?;
        let mut output = stdout().lock();
        writeln!(
            output,
            concat!(
                "benchmark,mode,scale,sample,nanoseconds,calls,object_bytes,",
                "retained_mapped_bytes,completed_calls"
            )
        )?;
        for scale in SCALES {
            warm_up(&fixture, &mut host, scale)?;
            emit_scale_samples(&mut output, &fixture, &mut host, scale)?;
        }
        if host.session_poisoned() {
            return Err(IoError::other(
                "native execution benchmark process session was poisoned",
            ));
        }
        Ok(())
    })();
    let cleanup = fs::remove_dir_all(&directory);
    result?;
    cleanup
}

fn main() -> IoResult<()> {
    run()
}
