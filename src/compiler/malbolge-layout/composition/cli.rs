// Copyright:
//   - Copyright © 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - Apache-2.0
// Confidential:
//   - false
// License-File:
//   - LICENSE
//
// Boundary-Contract:
// - Owns:
//   - Bounded machine/ternary input, VM preflight and artifact publication.
// - Must-Not:
//   - Infer guest semantics from host arguments or publish unverified source.
// - Allows:
//   - Inputs: exact profile, bounded MCTI/MCTR file or stdin, or machine tokens.
//   - Outputs: one complete raw graphical `.malbolge` file.
//   - Side effects: same-directory staging and atomic no-clobber hard link.
// - Split-When:
//   - A full typed-IR machine lowering input/serialization format is admitted.
// - Merge-When:
//   - General backend owns equivalent publication with the same guarantees.
// - Summary:
//   - Publishes only complete executable machine and byte-I/O trace artifacts.
// - Description:
//   - Requires explicit profile, validates admitted source with a real VM.
// - Usage:
//   - `--profile malbolge-2026 --output hello.malbolge -- input output halt`.
// - Defaults:
//   - Never overwrites a target or exposes a partially written target path.
//

//! Closed bounded machine-subset CLI with independently checked target source.

use std::env;
use std::ffi::{OsStr, OsString};
use std::fs::{self, OpenOptions};
use std::io::{self, Read as _, Write as _};
use std::path::{Path, PathBuf};
use std::process::{ExitCode, id};

use malbolge::{ProfileMachine, RunOutcome, build_capsule, parse_capsule, target_profile};

use crate::bridge::{
    encode_initial_zero_outputs, encode_latest_byte_identity_trace, encode_successful_byte_echo,
    encode_successful_latest_byte_trace, encode_zero_prefixed_latest_byte_trace,
    ternary::{TernaryOperation, canonical_ternary_program},
};
use crate::layout::{
    LinearOpcode, LinearProfileIdentity, PaddedForwardStep, admit_linear_layout,
    encode_auto_padded_forward_layout, encode_linear_layout,
};
use crate::typed_adapter::{
    compile_canonical_typed_echo, compile_canonical_typed_identity_byte_trace,
    compile_canonical_typed_initial_zero_outputs, compile_canonical_typed_latest_byte_trace,
    compile_canonical_typed_zero_prefixed_latest_byte_trace,
};

const PROFILE_ARG: &str = "--profile";
const OUTPUT_ARG: &str = "--output";
const DELIMITER_ARG: &str = "--";
const CAPSULE_ARG: &str = "--capsule";
const MAX_OPERATIONS: usize = 4096;
const MAX_CANONICAL_WIRE_BYTES: u64 = 1_048_576;
const TERNARY_FILE_ARG: &str = "--ternary-file";
const LATEST_BYTE_TRACE_ARG: &str = "--latest-byte-trace";
const INITIAL_ZERO_OUTPUT_ARG: &str = "--initial-zero-output";
const ZERO_PREFIXED_BYTE_TRACE_ARG: &str = "--zero-prefixed-byte-trace";
const IDENTITY_BYTE_TRACE_ARG: &str = "--identity-byte-trace";
const TYPED_FILE_ARG: &str = "--typed-file";
const TYPED_STDIN_ARG: &str = "--typed-stdin";
const TERNARY_STDIN_ARG: &str = "--ternary-stdin";
const AUTO_LAYOUT_ARG: &str = "--auto-layout";
const MALBOLGE_EXTENSION: &str = "malbolge";

#[derive(Debug)]
enum SourceSpec {
    AutoLayout(Vec<PaddedForwardStep>),
    CanonicalTernaryFile { path: PathBuf, mode: ByteTraceMode },
    CanonicalTernaryStdin { mode: ByteTraceMode },
    CanonicalTypedFile { path: PathBuf, mode: ByteTraceMode },
    CanonicalTypedStdin { mode: ByteTraceMode },
    MachineOperations(Vec<LinearOpcode>),
}

#[derive(Debug)]
struct CommandSpec {
    capsule: bool,
    output: PathBuf,
    profile: String,
    source: SourceSpec,
}

#[derive(Clone, Copy, Debug)]
enum ByteTraceMode {
    AdjacentEcho,
    IdentityByteBitcast,
    InitialZero,
    LatestRead,
    ZeroPrefixedLatest,
}

#[derive(Clone, Copy, Debug)]
enum SuccessfulByteEffect {
    Input,
    Output,
    ZeroOutput,
}

enum SourceEffectWitness {
    InitialZero { outputs: usize },
    SuccessfulByteTrace(Vec<SuccessfulByteEffect>),
}

struct VerifiedSource {
    effect_witness: Option<SourceEffectWitness>,
    source: Vec<u8>,
    steps: usize,
}

fn parse_operation(token: &str) -> Result<LinearOpcode, String> {
    match token {
        "crazy" => Ok(LinearOpcode::CrazyData),
        "halt" => Ok(LinearOpcode::Halt),
        "input" => Ok(LinearOpcode::InputWord),
        "nop" => Ok(LinearOpcode::NoOperation),
        "output" => Ok(LinearOpcode::OutputByte),
        "relocate" => Ok(LinearOpcode::RelocateDataPointer),
        "rotate" => Ok(LinearOpcode::RotateData),
        _ => {
            let Some(raw) = token.strip_prefix("jump:") else {
                return Err(format!("unsupported machine opcode: {token}"));
            };
            if raw.is_empty() || !raw.bytes().all(|byte| byte.is_ascii_digit()) {
                return Err(String::from(
                    "jump target must be an unsigned decimal address",
                ));
            }
            let target = raw
                .parse::<u32>()
                .map_err(|error| format!("jump target exceeds supported code address: {error}"))?;
            Ok(LinearOpcode::JumpForward { target })
        }
    }
}

fn parse_auto_layout_operation(token: &str) -> Result<PaddedForwardStep, String> {
    match token {
        "jump" => Ok(PaddedForwardStep::Jump),
        "auto-relocate" => Ok(PaddedForwardStep::AutoRelocate),
        _ => {
            let operation = parse_operation(token)?;
            if matches!(operation, LinearOpcode::JumpForward { .. }) {
                Err(String::from(
                    "--auto-layout accepts symbolic jump, not jump:TARGET",
                ))
            } else {
                Ok(PaddedForwardStep::Instruction(operation))
            }
        }
    }
}

fn parse_auto_layout(arguments: &mut impl Iterator<Item = OsString>) -> Result<SourceSpec, String> {
    let mut operations = Vec::new();
    for raw in arguments {
        if operations.len() >= MAX_OPERATIONS {
            return Err(String::from("too many auto-layout operation tokens"));
        }
        let token = raw
            .into_string()
            .map_err(|_error| String::from("auto-layout token must be UTF-8"))?;
        operations.push(parse_auto_layout_operation(&token)?);
    }
    if operations.is_empty() {
        return Err(String::from("missing auto-layout operation tokens"));
    }
    Ok(SourceSpec::AutoLayout(operations))
}

fn parse_canonical_source(
    first: OsString,
    arguments: &mut impl Iterator<Item = OsString>,
) -> Result<SourceSpec, String> {
    let (kind, mode) = if first == OsStr::new(LATEST_BYTE_TRACE_ARG)
        || first == OsStr::new(INITIAL_ZERO_OUTPUT_ARG)
        || first == OsStr::new(ZERO_PREFIXED_BYTE_TRACE_ARG)
        || first == OsStr::new(IDENTITY_BYTE_TRACE_ARG)
    {
        let mode = if first == OsStr::new(INITIAL_ZERO_OUTPUT_ARG) {
            ByteTraceMode::InitialZero
        } else if first == OsStr::new(ZERO_PREFIXED_BYTE_TRACE_ARG) {
            ByteTraceMode::ZeroPrefixedLatest
        } else if first == OsStr::new(IDENTITY_BYTE_TRACE_ARG) {
            ByteTraceMode::IdentityByteBitcast
        } else {
            ByteTraceMode::LatestRead
        };
        (
            arguments
                .next()
                .ok_or("missing canonical wire input mode")?,
            mode,
        )
    } else {
        (first, ByteTraceMode::AdjacentEcho)
    };
    let uses_file = kind == OsStr::new(TERNARY_FILE_ARG) || kind == OsStr::new(TYPED_FILE_ARG);
    let uses_stdin = kind == OsStr::new(TERNARY_STDIN_ARG) || kind == OsStr::new(TYPED_STDIN_ARG);
    if !uses_file && !uses_stdin {
        return Err(String::from(
            "effect mode requires --ternary-file, --typed-file, --ternary-stdin or --typed-stdin",
        ));
    }
    let source = if uses_stdin {
        if arguments.next().is_some() {
            return Err(String::from("canonical stdin mode accepts no input path"));
        }
        if kind == OsStr::new(TERNARY_STDIN_ARG) {
            SourceSpec::CanonicalTernaryStdin { mode }
        } else {
            SourceSpec::CanonicalTypedStdin { mode }
        }
    } else {
        let path = PathBuf::from(arguments.next().ok_or("missing canonical wire path")?);
        if arguments.next().is_some() {
            return Err(String::from(
                "canonical wire mode accepts exactly one input path",
            ));
        }
        if kind == OsStr::new(TERNARY_FILE_ARG) {
            SourceSpec::CanonicalTernaryFile { path, mode }
        } else {
            SourceSpec::CanonicalTypedFile { path, mode }
        }
    };
    Ok(source)
}

fn parse_source(arguments: &mut impl Iterator<Item = OsString>) -> Result<SourceSpec, String> {
    let first = arguments
        .next()
        .ok_or("missing machine operations or canonical wire argument")?;
    let source = if first == OsStr::new(AUTO_LAYOUT_ARG) {
        return parse_auto_layout(arguments);
    } else if first == OsStr::new(TERNARY_FILE_ARG)
        || first == OsStr::new(TYPED_FILE_ARG)
        || first == OsStr::new(TERNARY_STDIN_ARG)
        || first == OsStr::new(TYPED_STDIN_ARG)
        || first == OsStr::new(LATEST_BYTE_TRACE_ARG)
        || first == OsStr::new(INITIAL_ZERO_OUTPUT_ARG)
        || first == OsStr::new(ZERO_PREFIXED_BYTE_TRACE_ARG)
        || first == OsStr::new(IDENTITY_BYTE_TRACE_ARG)
    {
        return parse_canonical_source(first, arguments);
    } else {
        let first_token = first
            .into_string()
            .map_err(|_error| String::from("opcode token must be UTF-8"))?;
        let mut operations = vec![parse_operation(&first_token)?];
        for raw_token in arguments {
            if operations.len() >= MAX_OPERATIONS {
                return Err(String::from("too many machine opcode tokens"));
            }
            let token = raw_token
                .into_string()
                .map_err(|_error| String::from("opcode token must be UTF-8"))?;
            operations.push(parse_operation(&token)?);
        }
        SourceSpec::MachineOperations(operations)
    };
    Ok(source)
}

fn parse_arguments(mut arguments: impl Iterator<Item = OsString>) -> Result<CommandSpec, String> {
    if arguments.next().as_deref() != Some(OsStr::new(PROFILE_ARG)) {
        return Err(String::from("expected --profile <canonical-id>"));
    }
    let profile = arguments
        .next()
        .ok_or("missing target profile")?
        .into_string()
        .map_err(|_error| String::from("profile must be UTF-8"))?;
    if arguments.next().as_deref() != Some(OsStr::new(OUTPUT_ARG)) {
        return Err(String::from("expected --output <path>.malbolge"));
    }
    let output = PathBuf::from(arguments.next().ok_or("missing output path")?);
    let next = arguments.next();
    let capsule = next.as_deref() == Some(OsStr::new(CAPSULE_ARG));
    if (capsule && arguments.next().as_deref() != Some(OsStr::new(DELIMITER_ARG)))
        || (!capsule && next.as_deref() != Some(OsStr::new(DELIMITER_ARG)))
    {
        return Err(String::from(
            "expected optional --capsule then -- before opcode tokens",
        ));
    }
    let source = parse_source(&mut arguments)?;
    Ok(CommandSpec {
        capsule,
        output,
        profile,
        source,
    })
}

fn publish_new(path: &Path, bytes: &[u8]) -> Result<(), String> {
    if path.extension() != Some(OsStr::new(MALBOLGE_EXTENSION)) {
        return Err(String::from("output must have a .malbolge extension"));
    }
    let name = path
        .file_name()
        .and_then(OsStr::to_str)
        .ok_or("output needs a UTF-8 filename")?;
    let staged = path.with_file_name(format!(".{name}.stage-{}", id()));
    let mut file = OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(&staged)
        .map_err(|error| format!("cannot open fresh stage: {error}"))?;
    let outcome = (|| {
        file.write_all(bytes)
            .map_err(|error| format!("stage write failed: {error}"))?;
        file.sync_all()
            .map_err(|error| format!("stage sync failed: {error}"))?;
        drop(file);
        if fs::read(&staged).map_err(|error| format!("stage reopen failed: {error}"))? != bytes {
            return Err(String::from("staged output differs from verified source"));
        }
        fs::hard_link(&staged, path)
            .map_err(|error| format!("cannot publish new target: {error}"))?;
        Ok(())
    })();
    drop(fs::remove_file(&staged));
    outcome
}

// On Linux/Android use nonblocking open first, *then* inspect the actual
// opened descriptor. A writerless FIFO (or one substituted for a regular
// symlink) cannot block acquisition; subsequent fstat refuses that handle.
// Ordinary regular-file symlinks remain valid.
#[cfg(any(target_os = "linux", target_os = "android"))]
fn open_canonical_file(path: &Path) -> io::Result<fs::File> {
    use std::os::unix::fs::OpenOptionsExt as _;

    // Linux asm-generic fcntl.h: O_NONBLOCK = 1 << 11. Regular files ignore
    // this status bit for reads; FIFO opens cannot wait for a writer.
    const LINUX_O_NONBLOCK: i32 = 1 << 11;
    OpenOptions::new()
        .read(true)
        .custom_flags(LINUX_O_NONBLOCK)
        .open(path)
}

#[cfg(not(any(target_os = "linux", target_os = "android")))]
fn open_canonical_file(path: &Path) -> io::Result<fs::File> {
    fs::File::open(path)
}

fn read_canonical_wire(path: &Path, kind: &str) -> Result<Vec<u8>, String> {
    // Linux/Android open the descriptor nonblocking and inspect that very
    // handle. Other platforms retain the bounded pre-open pathname guard.
    #[cfg(not(any(target_os = "linux", target_os = "android")))]
    {
        let path_metadata = fs::metadata(path)
            .map_err(|error| format!("cannot inspect canonical {kind} path: {error}"))?;
        if !path_metadata.is_file()
            || path_metadata.len() == 0
            || path_metadata.len() > MAX_CANONICAL_WIRE_BYTES
        {
            return Err(String::from(
                "canonical wire must be a nonempty bounded regular file",
            ));
        }
    }
    let file = open_canonical_file(path)
        .map_err(|error| format!("cannot open canonical {kind} wire: {error}"))?;
    let metadata = file
        .metadata()
        .map_err(|error| format!("cannot inspect canonical {kind} wire: {error}"))?;
    if !metadata.is_file() || metadata.len() == 0 || metadata.len() > MAX_CANONICAL_WIRE_BYTES {
        return Err(String::from(
            "canonical wire must be a nonempty bounded regular file",
        ));
    }
    let mut bytes = Vec::new();
    let _bytes_read = file
        .take(MAX_CANONICAL_WIRE_BYTES.saturating_add(1))
        .read_to_end(&mut bytes)
        .map_err(|error| format!("cannot read canonical {kind} wire: {error}"))?;
    let length = u64::try_from(bytes.len())
        .map_err(|_error| String::from("ternary wire length overflow"))?;
    if length > MAX_CANONICAL_WIRE_BYTES || length != metadata.len() {
        return Err(String::from(
            "ternary wire read length disagrees with bounded file",
        ));
    }
    Ok(bytes)
}

fn read_canonical_stdin(kind: &str) -> Result<Vec<u8>, String> {
    // Input must finish (EOF), but memory is bounded even if the writer
    // supplies an unlimited stream. Never publish until canonical admission.
    let mut bytes = Vec::new();
    let _read = io::stdin()
        .lock()
        .take(MAX_CANONICAL_WIRE_BYTES.saturating_add(1))
        .read_to_end(&mut bytes)
        .map_err(|error| format!("cannot read canonical {kind} stdin: {error}"))?;
    if bytes.is_empty()
        || u64::try_from(bytes.len()).map_err(|_error| "canonical stdin length overflow")?
            > MAX_CANONICAL_WIRE_BYTES
    {
        return Err(String::from(
            "canonical stdin must be nonempty and at most 1 MiB",
        ));
    }
    Ok(bytes)
}

fn verified_ternary_bytes(
    bytes: &[u8],
    mode: ByteTraceMode,
    profile: &'static malbolge::ProfileDescriptor,
) -> Result<VerifiedSource, String> {
    let program = canonical_ternary_program(bytes)
        .map_err(|error| format!("canonical ternary wire rejected: {error:?}"))?;
    let layout = match mode {
        ByteTraceMode::AdjacentEcho => encode_successful_byte_echo(&program, profile),
        ByteTraceMode::InitialZero => encode_initial_zero_outputs(&program, profile),
        ByteTraceMode::LatestRead => encode_successful_latest_byte_trace(&program, profile),
        ByteTraceMode::ZeroPrefixedLatest => {
            encode_zero_prefixed_latest_byte_trace(&program, profile)
        }
        ByteTraceMode::IdentityByteBitcast => encode_latest_byte_identity_trace(&program, profile),
    }
    .map_err(|error| format!("ternary byte-trace bridge rejected: {error:?}"))?;
    if layout.profile_id() != profile.id() || layout.profile_fingerprint() != profile.fingerprint()
    {
        return Err(String::from(
            "ternary source profile mismatch after admission",
        ));
    }
    let operations = &program
        .functions
        .first()
        .ok_or("bridge accepted no ternary function")?
        .operations;
    let effect_witness = if matches!(mode, ByteTraceMode::InitialZero) {
        Some(SourceEffectWitness::InitialZero {
            outputs: operations
                .iter()
                .filter(|operation| matches!(operation, TernaryOperation::ByteOutput { .. }))
                .count(),
        })
    } else {
        let effects = operations
            .iter()
            .filter(|operation| {
                matches!(
                    operation,
                    TernaryOperation::ByteInput { .. } | TernaryOperation::ByteOutput { .. }
                )
            })
            .scan(false, |seen_input, operation| {
                if matches!(operation, TernaryOperation::ByteInput { .. }) {
                    *seen_input = true;
                    Some(SuccessfulByteEffect::Input)
                } else if matches!(mode, ByteTraceMode::ZeroPrefixedLatest) && !*seen_input {
                    Some(SuccessfulByteEffect::ZeroOutput)
                } else {
                    Some(SuccessfulByteEffect::Output)
                }
            })
            .collect();
        Some(SourceEffectWitness::SuccessfulByteTrace(effects))
    };
    Ok(VerifiedSource {
        effect_witness,
        source: layout.source().to_vec(),
        steps: layout.executed_code_positions().len(),
    })
}

fn verified_typed_bytes(
    typed_bytes: &[u8],
    mode: ByteTraceMode,
    profile: &'static malbolge::ProfileDescriptor,
) -> Result<VerifiedSource, String> {
    let compiled = match mode {
        ByteTraceMode::AdjacentEcho => compile_canonical_typed_echo(typed_bytes, profile),
        ByteTraceMode::InitialZero => {
            compile_canonical_typed_initial_zero_outputs(typed_bytes, profile)
        }
        ByteTraceMode::LatestRead => {
            compile_canonical_typed_latest_byte_trace(typed_bytes, profile)
        }
        ByteTraceMode::ZeroPrefixedLatest => {
            compile_canonical_typed_zero_prefixed_latest_byte_trace(typed_bytes, profile)
        }
        ByteTraceMode::IdentityByteBitcast => {
            compile_canonical_typed_identity_byte_trace(typed_bytes, profile)
        }
    }
    .map_err(|error| format!("canonical typed byte bridge rejected: {error:?}"))?;
    // The typed adapter proposes an MCTR wire and encoded layout. Re-decode
    // its actual MCTR bytes and re-encode target code through the independent
    // ternary bridge before any guest execution or file publication.
    let admitted = verified_ternary_bytes(compiled.ternary_bytes(), mode, profile)?;
    if admitted.source != compiled.layout().source()
        || admitted.steps != compiled.layout().executed_code_positions().len()
        || compiled.layout().profile_id() != profile.id()
        || compiled.layout().profile_fingerprint() != profile.fingerprint()
    {
        return Err(String::from(
            "independently admitted typed and ternary target source disagree",
        ));
    }
    Ok(admitted)
}

fn verified_source(
    spec: &SourceSpec,
    profile: &'static malbolge::ProfileDescriptor,
) -> Result<VerifiedSource, String> {
    match spec {
        SourceSpec::AutoLayout(logical) => {
            let proposed = encode_auto_padded_forward_layout(profile, logical)
                .map_err(|error| format!("auto-layout rejected: {error:?}"))?;
            let artifact = admit_linear_layout(
                profile,
                proposed.operations(),
                proposed.layout().source(),
                LinearProfileIdentity {
                    fingerprint: proposed.layout().profile_fingerprint(),
                    id: proposed.layout().profile_id(),
                },
            )
            .map_err(|error| format!("auto-layout independent admission failed: {error:?}"))?;
            Ok(VerifiedSource {
                effect_witness: None,
                source: artifact.source().to_vec(),
                steps: artifact.executed_code_positions().len(),
            })
        }
        SourceSpec::MachineOperations(operations) => {
            let artifact = encode_linear_layout(profile, operations)
                .map_err(|error| format!("layout rejected: {error:?}"))?;
            let admitted = admit_linear_layout(
                profile,
                operations,
                artifact.source(),
                LinearProfileIdentity {
                    fingerprint: artifact.profile_fingerprint(),
                    id: artifact.profile_id(),
                },
            )
            .map_err(|error| format!("source admission failed: {error:?}"))?;
            Ok(VerifiedSource {
                effect_witness: None,
                source: admitted.source().to_vec(),
                steps: admitted.executed_code_positions().len(),
            })
        }
        SourceSpec::CanonicalTernaryFile { path, mode } => {
            verified_ternary_bytes(&read_canonical_wire(path, "ternary")?, *mode, profile)
        }
        SourceSpec::CanonicalTypedFile { path, mode } => {
            verified_typed_bytes(&read_canonical_wire(path, "typed")?, *mode, profile)
        }
        SourceSpec::CanonicalTernaryStdin { mode } => {
            verified_ternary_bytes(&read_canonical_stdin("ternary")?, *mode, profile)
        }
        SourceSpec::CanonicalTypedStdin { mode } => {
            verified_typed_bytes(&read_canonical_stdin("typed")?, *mode, profile)
        }
    }
}

fn verify_successful_byte_trace(
    profile: &'static malbolge::ProfileDescriptor,
    artifact: &VerifiedSource,
    effects: &[SuccessfulByteEffect],
) -> Result<(), String> {
    let patterns: [[u8; 8]; 2] = [
        [0, 255, 173, 128, 1, 254, 10, 65],
        [255, 0, 82, 127, 254, 1, 42, 13],
    ];
    let reads = effects
        .iter()
        .filter(|effect| matches!(effect, SuccessfulByteEffect::Input))
        .count();
    if reads == 0 || effects.len().checked_add(1) != Some(artifact.steps) {
        return Err(String::from(
            "ternary bridge emitted an unexpected effect geometry",
        ));
    }
    for pattern in patterns {
        let input: Vec<u8> = pattern.into_iter().cycle().take(reads).collect();
        let mut consumed = 0;
        let mut latest = None;
        let mut expected_output = Vec::new();
        for effect in effects {
            match effect {
                SuccessfulByteEffect::Input => {
                    latest = input.get(consumed).copied();
                    consumed = consumed.checked_add(1).ok_or("byte input count overflow")?;
                }
                SuccessfulByteEffect::Output => {
                    expected_output.push(latest.ok_or("output before successful input")?);
                }
                SuccessfulByteEffect::ZeroOutput if latest.is_none() => {
                    expected_output.push(0);
                }
                SuccessfulByteEffect::ZeroOutput => {
                    return Err(String::from("zero output after accumulator overwrite"));
                }
            }
        }
        let mut vm = ProfileMachine::from_source(profile, &artifact.source, input)
            .map_err(|error| format!("successful-byte VM load failed: {error:?}"))?;
        if !matches!(vm.run(artifact.steps),
            Ok(RunOutcome::Terminated { steps: count, .. }) if count == artifact.steps)
        {
            return Err(String::from("successful-byte VM trace did not terminate"));
        }
        if vm.output() != expected_output || vm.input_consumed() != reads {
            return Err(String::from("successful-byte VM trace mismatch"));
        }
    }
    Ok(())
}

// Constant-zero emission has no successful input effects: the selected VM
// must emit each zero from initial A=0 while ignoring any supplied guest stdin.
fn verify_initial_zero_outputs(
    profile: &'static malbolge::ProfileDescriptor,
    artifact: &VerifiedSource,
    outputs: usize,
) -> Result<(), String> {
    if outputs == 0 || outputs.checked_add(1) != Some(artifact.steps) {
        return Err(String::from("initial-zero guest output geometry disagrees"));
    }
    for input in [Vec::new(), vec![255, 0, 128]] {
        let mut vm = ProfileMachine::from_source(profile, &artifact.source, input)
            .map_err(|error| format!("initial-zero guest VM load failed: {error:?}"))?;
        if !matches!(vm.run(artifact.steps),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == artifact.steps)
            || vm.input_consumed() != 0
            || vm.output().len() != outputs
            || vm.output().iter().any(|byte| *byte != 0)
        {
            return Err(String::from("initial-zero guest VM output mismatch"));
        }
    }
    Ok(())
}

fn execute(spec: &CommandSpec) -> Result<(), String> {
    let profile = target_profile(&spec.profile).ok_or("unknown canonical target profile")?;
    let artifact = verified_source(&spec.source, profile)?;
    let mut vm = ProfileMachine::from_source(profile, &artifact.source, Vec::new())
        .map_err(|error| format!("normative VM rejected source: {error:?}"))?;
    if !matches!(vm.run(artifact.steps), Ok(RunOutcome::Terminated { steps: count, .. }) if count == artifact.steps)
    {
        return Err(String::from(
            "normative VM did not halt at the proven code step",
        ));
    }
    match &artifact.effect_witness {
        Some(SourceEffectWitness::SuccessfulByteTrace(effects)) => {
            verify_successful_byte_trace(profile, &artifact, effects)?;
        }
        Some(SourceEffectWitness::InitialZero { outputs }) => {
            verify_initial_zero_outputs(profile, &artifact, *outputs)?;
        }
        None => {}
    }
    let publication = if spec.capsule {
        let bytes = build_capsule(profile, &artifact.source)
            .map_err(|error| format!("capsule build rejected: {error}"))?;
        let parsed = parse_capsule(&bytes)
            .map_err(|error| format!("capsule independent parse rejected: {error}"))?
            .ok_or("capsule marker missing after framing")?;
        if parsed.profile() != profile || parsed.payload() != artifact.source {
            return Err(String::from("capsule profile or source payload disagrees"));
        }
        bytes
    } else {
        artifact.source
    };
    publish_new(&spec.output, &publication)?;
    let notice = format!(
        "emitted {} bytes for {} ({} VM steps)\n",
        publication.len(),
        profile.id(),
        artifact.steps,
    );
    drop(io::stderr().lock().write_all(notice.as_bytes()));
    Ok(())
}

/// Executes the closed validated layout CLI and returns a failure exit code
/// without publishing partial target artifacts.
#[must_use]
pub fn run() -> ExitCode {
    match parse_arguments(env::args_os().skip(1)).and_then(|spec| execute(&spec)) {
        Ok(()) => ExitCode::SUCCESS,
        Err(error) => {
            let notice = format!("malbolge_layout: {error}\n");
            drop(io::stderr().lock().write_all(notice.as_bytes()));
            ExitCode::FAILURE
        }
    }
}
