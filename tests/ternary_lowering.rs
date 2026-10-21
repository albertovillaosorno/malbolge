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
//   - Integration evidence for the first typed-IR-to-ternary lowering slice.
// - Must-Not:
//   - Claim layout, Malbolge encoding, or unsupported typed-IR semantics.
// - Allows:
//   - Inputs: tracked canonical typed-IR golden modules.
//   - Outputs: deterministic target-model and fail-closed assertions.
//   - Side effects: fixture reads plus cleaned child-process crash fixtures.
// - Split-When:
//   - Another lowering family needs an independent integration harness.
// - Merge-When:
//   - Another test owns this exact typed-IR-to-ternary evidence.
// - Summary:
//   - Proves exact `i32` constant-return ternary lowering.
// - Description:
//   - Checks projection, bit preservation, provenance, and unsupported
//     rejection.
// - Usage:
//   - Run through Cargo or repository Jig validation.
// - Defaults:
//   - Only the tracked first lowering golden is accepted by this slice.
//

//! Integration tests for the first pre-layout ternary lowering slice.

#[path = "../src/compiler/ternary-lowering/composition/lib.rs"]
pub mod ternary_lowering;
#[path = "../src/compiler/typed-ir/composition/lib.rs"]
pub mod typed_ir;

use std::env::temp_dir;
use std::fs::{
    copy, create_dir_all, read_to_string, remove_dir_all, remove_file, write,
};
use std::path::{Path, PathBuf};
use std::process::{Command, id};
use std::str::from_utf8;
use std::sync::atomic::{AtomicUsize, Ordering};

use malbolge::{current_profile, decode_profile_instruction};
use ternary_lowering::{
    ByteStreamControlFlowError, ByteStreamWrapperExecutionPlan,
    ByteStreamWrapperExecutionStep, ByteStreamWrapperOrder,
    ByteStreamWrapperPlanningError, ByteStreamWrapperRealizationError,
    ByteStreamWrapperRequest, ByteStreamWrapperReturn, FrameCodecExecutionStep,
    FrameField, FrameFieldLayout, FrameHelperExecutionPlan,
    FrameHelperLoweringError, FrameHelperOperation, FrameHelperRequest,
    FrameValidationArm, FrameValidationCondition, FrameValidationSemantics,
    HeapAllocateSemantics, HeapAllocateStep, HeapAllocateZeroedSemantics,
    HeapAllocateZeroedStep, HeapHelperExecutionPlan, HeapHelperLoweringError,
    HeapHelperOperation, HeapHelperRequest, HeapInitSemantics, HeapInitStep,
    HeapReleaseSemantics, HeapReleaseStep, I32_TERNARY_TRITS, InputBlock,
    InputDecodeArm, InputDecodeCondition, InputDecodeResult, InputFunction,
    InputInstruction, InputOrderedComparison, InputScalarType,
    InputSourcePosition, InputSourceSpan, InputTerminator,
    InputWordDecodeControlFlow, InputWordDecodeSemantics,
    MachineIoEncodingError, MachineIoKind, MachineIoOperation,
    ProfileInstructionDecoder, RuntimeHelperExecutionPlan,
    RuntimeHelperLoweringError, RuntimeHelperOperation, RuntimeHelperRequest,
    RuntimeIntrinsicLoweringError, RuntimeIntrinsicOperation,
    RuntimeIntrinsicRequest, RuntimeIoRealizationError, StartupAction,
    StartupPlanningError, StartupRequest, TERNARY_PROGRAM_CODEC_ID,
    TargetProfileIo, TernaryCompilerStageError, TernaryCompilerStageInput,
    TernaryLoweringError, TernaryOperation, TernaryProgramCodecError,
    TernaryProgramValidationError, TernaryProgressCheckpointError,
    TernaryStageError, TernaryStageInput, TypedIrInput,
    canonical_ternary_bytes, canonical_ternary_program, encode_machine_io,
    enter_ternary_compiler_stage, enter_ternary_stage, lower_frame_helper,
    lower_heap_helper, lower_runtime_helper, lower_runtime_intrinsic,
    lower_typed_ir, plan_byte_stream_wrapper, plan_startup,
    realize_byte_stream_control_flow, realize_byte_stream_wrapper,
    realize_frame_helper, realize_heap_helper, realize_runtime_helper,
    realize_runtime_io, resume_ternary_from_progress,
};
use typed_ir::{
    BasicBlock, BasicBlockSpec, BinaryOp, BlockId, CastOp, CompareOp, Function,
    FunctionId, FunctionSpec, Instruction, IntegerConstant, LocatedInstruction,
    Module, ModuleSpec, SourcePosition, SourceSpan, TYPED_IR_CODEC_ID,
    Terminator, TypeDef, TypeEntry, TypeId, ValueId, canonical_bytes,
    canonical_module, validate_module,
};

const RETURN_GOLDEN: &str =
    "tests/compiler/typed-ir/golden/ir-return-constant.hex";
const SELECT_GOLDEN: &str = "tests/compiler/typed-ir/golden/select.hex";
const BYTE_IO_SOURCE_HASH: [u8; 32] = [0x6b; 32];
const LOW_BYTE_SOURCE_HASH: [u8; 32] = [0x7c; 32];
const GUEST_INTRINSICS_HEADER: &str =
    "src/runtime/guest-runtime/contract/guest_intrinsics.h";
const GUEST_RUNTIME_CONTRACT: &str =
    "src/runtime/guest-runtime/contract/guest-runtime-v1.json";
const GUEST_RUNTIME_HEADER: &str =
    "src/runtime/guest-runtime/contract/guest_runtime.h";
const GUEST_BYTE_STREAM_SOURCE: &str =
    "src/runtime/guest-runtime/domain/byte_stream.c";
const GUEST_FRAME_SOURCE: &str = "src/runtime/guest-runtime/domain/frame.c";
const GUEST_HEAP_SOURCE: &str = "src/runtime/guest-runtime/domain/heap.c";
const GUEST_STDIO_SOURCE: &str = "src/runtime/guest-c-library/domain/stdio.c";
const ABI_CONTRACT: &str = "docs/technical/specification/c-abi-v1.json";
const LIBC_CONTRACT: &str = "docs/technical/specification/c-libc-v1.json";

const TERNARY_PROGRESS_FIXTURE_SCRIPT: &str = r#"from hashlib import sha256
from pathlib import Path
import sys

sys.path.insert(0, sys.argv[1])
from scripts import progress_sidecar as progress

directory = Path(sys.argv[2])
payload = Path(sys.argv[3]).read_bytes()
output = directory / "program.malbolge"
source_hash = "sha256:" + ("1" * 64)
toolchain_hash = "sha256:" + ("2" * 64)
profile_hash = "malbolge-profile-v1:sha256:" + ("3" * 64)
revision = "a" * 40
identity = progress.ResumeIdentity(
    algorithm_id="compiler.ternary-lowering",
    algorithm_version="1",
    repository_revision=revision,
    schema=progress.SCHEMA_ID,
    seed=7,
    source_sha256=source_hash,
    target_profile_fingerprint=profile_hash,
    target_profile_id="malbolge-2026",
    toolchain_fingerprint=toolchain_hash,
)
position = progress.PortableCheckpointPosition(
    checkpoint_sequence=1,
    stage="ternary-lowering",
    units_completed=1,
)
checkpoint = progress.encode_portable_checkpoint(
    identity,
    position,
    "malbolge-ternary-ir-v1",
    payload=payload,
)
sidecar = progress.ProgressSidecar(
    active_elapsed_ns=700,
    algorithm_id="compiler.ternary-lowering",
    algorithm_version="1",
    backend="cpu",
    checkpoint_elapsed_ns=30,
    checkpoint_path=str(progress.checkpoint_path(output, 1)),
    checkpoint_sequence=1,
    checkpoint_sha256="sha256:" + sha256(checkpoint).hexdigest(),
    compatibility_fingerprint=(
        progress.resume_compatibility_fingerprint(identity)
    ),
    completed_at=None,
    device=None,
    diagnostic_code=None,
    diagnostic_message=None,
    operation_id="compile-ternary-resume",
    output_path=str(output),
    partial_bytes=None,
    partial_path=None,
    partial_sha256=None,
    paused_elapsed_ns=100,
    progress_path=str(progress.progress_path(output)),
    repository_revision=revision,
    schema=progress.SCHEMA_ID,
    seed=7,
    serialization_elapsed_ns=10,
    source_path="input.c",
    source_sha256=source_hash,
    stage="ternary-lowering",
    started_at="2026-08-06T14:00:00Z",
    status=progress.ProgressStatus.CHECKPOINTED,
    target_profile_fingerprint=profile_hash,
    target_profile_id="malbolge-2026",
    toolchain_fingerprint=toolchain_hash,
    units_completed=1,
    units_total=None,
    updated_at="2026-08-06T14:00:02Z",
    verification_elapsed_ns=30,
    wall_elapsed_ns=870,
)
progress.write_checkpoint_generation(sidecar, checkpoint)
"#;
const TERNARY_CRASH_EXIT: i32 = 73;
const TERNARY_CRASH_BOUNDARIES: [&str; 10] = [
    "before-checkpoint-file-sync",
    "before-checkpoint-publish",
    "after-checkpoint-publish",
    "after-checkpoint-sync",
    "after-checkpoint",
    "before-sidecar-file-sync",
    "before-sidecar-replace",
    "after-sidecar-replace",
    "after-sidecar-sync",
    "before-sidecar",
];
const TERNARY_PROGRESS_CRASH_SCRIPT: &str = r#"from hashlib import sha256
from pathlib import Path
import os
import stat
import sys
from scripts import progress_sidecar as progress

output = Path(sys.argv[1])
first_payload = Path(sys.argv[2]).read_bytes()
second_payload = Path(sys.argv[3]).read_bytes()
exit_code = int(sys.argv[4])
boundary = sys.argv[5]
codec = "malbolge-ternary-ir-v1"
source_hash = "sha256:" + ("1" * 64)
toolchain_hash = "sha256:" + ("2" * 64)
profile_hash = "malbolge-profile-v1:sha256:" + ("3" * 64)
revision = "a" * 40

def digest(payload):
    return "sha256:" + sha256(payload).hexdigest()

identity = progress.ResumeIdentity(
    algorithm_id="compiler.ternary-lowering",
    algorithm_version="1",
    repository_revision=revision,
    schema=progress.SCHEMA_ID,
    seed=7,
    source_sha256=source_hash,
    target_profile_fingerprint=profile_hash,
    target_profile_id="malbolge-2026",
    toolchain_fingerprint=toolchain_hash,
)
compatibility = progress.resume_compatibility_fingerprint(identity)

def generation(sequence, units, updated_at, backend, device, state):
    position = progress.PortableCheckpointPosition(
        checkpoint_sequence=sequence,
        stage="ternary-lowering",
        units_completed=units,
    )
    checkpoint = progress.encode_portable_checkpoint(
        identity,
        position,
        codec,
        payload=state,
    )
    sidecar = progress.ProgressSidecar(
        active_elapsed_ns=sequence * 100,
        algorithm_id=identity.algorithm_id,
        algorithm_version=identity.algorithm_version,
        backend=backend,
        checkpoint_elapsed_ns=sequence * 10,
        checkpoint_path=str(progress.checkpoint_path(output, sequence)),
        checkpoint_sequence=sequence,
        checkpoint_sha256=digest(checkpoint),
        compatibility_fingerprint=compatibility,
        completed_at=None,
        device=device,
        diagnostic_code=None,
        diagnostic_message=None,
        operation_id="compile-ternary-crash-fixture",
        output_path=str(output),
        partial_bytes=None,
        partial_path=None,
        partial_sha256=None,
        paused_elapsed_ns=0,
        progress_path=str(progress.progress_path(output)),
        repository_revision=revision,
        schema=progress.SCHEMA_ID,
        seed=7,
        serialization_elapsed_ns=0,
        source_path="input.c",
        source_sha256=source_hash,
        stage="ternary-lowering",
        started_at="2026-08-06T14:00:00Z",
        status=progress.ProgressStatus.CHECKPOINTED,
        target_profile_fingerprint=profile_hash,
        target_profile_id="malbolge-2026",
        toolchain_fingerprint=toolchain_hash,
        units_completed=units,
        units_total=None,
        updated_at=updated_at,
        verification_elapsed_ns=0,
        wall_elapsed_ns=sequence * 110,
    )
    return sidecar, checkpoint

first, first_checkpoint = generation(
    1,
    1,
    "2026-08-06T14:00:01Z",
    "cpu",
    None,
    first_payload,
)
progress.write_checkpoint_generation(first, first_checkpoint)
second, second_checkpoint = generation(
    2,
    2,
    "2026-08-06T14:00:02Z",
    "cuda",
    "cuda-device-0",
    second_payload,
)

original_write_immutable = progress._write_immutable
original_publish = progress._publish_immutable_payload
original_confirm = progress._confirm_publication_durability
original_fsync = os.fsync
original_replace = Path.replace
publication_count = 0
regular_sync_count = 0

def fsync_then_crash(descriptor):
    global regular_sync_count
    mode = os.fstat(descriptor).st_mode
    if not stat.S_ISREG(mode):
        return original_fsync(descriptor)
    regular_sync_count += 1
    if boundary == "before-checkpoint-file-sync" and regular_sync_count == 1:
        os._exit(exit_code)
    if boundary == "before-sidecar-file-sync" and regular_sync_count == 2:
        os._exit(exit_code)
    return original_fsync(descriptor)

def publish_then_crash(temporary, destination, payload, *, platform):
    global publication_count
    if boundary == "before-checkpoint-publish":
        os._exit(exit_code)
    result = original_publish(
        temporary,
        destination,
        payload,
        platform=platform,
    )
    publication_count = 1
    if boundary == "after-checkpoint-publish":
        os._exit(exit_code)
    return result

def write_then_crash(destination, payload):
    result = original_write_immutable(destination, payload)
    if boundary == "after-checkpoint" and publication_count == 1:
        os._exit(exit_code)
    return result

def confirm_then_crash(published_path, *, context, platform=os.name):
    result = original_confirm(
        published_path,
        context=context,
        platform=platform,
    )
    if context == "immutable progress payload":
        if boundary == "after-checkpoint-sync" and publication_count == 1:
            os._exit(exit_code)
    if context == "progress sidecar" and boundary == "after-sidecar-sync":
        os._exit(exit_code)
    return result

def crash_before_sidecar(_sidecar):
    os._exit(exit_code)

def replace_then_crash(source, destination):
    if boundary == "before-sidecar-replace":
        os._exit(exit_code)
    result = original_replace(source, destination)
    if boundary == "after-sidecar-replace":
        os._exit(exit_code)
    return result

progress._publish_immutable_payload = publish_then_crash
progress._confirm_publication_durability = confirm_then_crash
progress._write_immutable = write_then_crash
os.fsync = fsync_then_crash
if boundary == "before-sidecar":
    progress.write_atomic = crash_before_sidecar
elif boundary in {"before-sidecar-replace", "after-sidecar-replace"}:
    Path.replace = replace_then_crash
progress.write_checkpoint_generation(second, second_checkpoint)
raise SystemExit(93)
"#;
const TERNARY_INSPECTOR_DIAGNOSTIC_SCRIPT: &str = r#"import sys
sys.stderr.write("unexpected diagnostic")
"#;
const TERNARY_INSPECTOR_INVALID_SCRIPT: &str = r#"import sys
sys.stdout.buffer.write(b"bad")
"#;

static NEXT_TERNARY_CRASH_FIXTURE: AtomicUsize = AtomicUsize::new(0);

type TernaryProgressFixture = (PathBuf, PathBuf);
type HalfwordRecordOffsets = (usize, usize);
type LoweredByteFixture = (ternary_lowering::TernaryProgram, TypedIrInput);
type ComparisonOperationTag = (TernaryOperation, u8);
type PromotedWireMutation = (usize, u8, TernaryProgramCodecError);

#[derive(Clone, Copy)]
struct ComparisonFixture {
    alias: bool,
    left: u32,
    operation: CompareOp,
    right: u32,
    signed: bool,
}

type ArithmeticExpected = Result<(TernaryOperation, u8), String>;

struct TernaryCrashPaths {
    directory: PathBuf,
    first: PathBuf,
    second: PathBuf,
}

struct VmProfileInstructionDecoder;

impl ProfileInstructionDecoder for VmProfileInstructionDecoder {
    fn decode(&self, cell: u32, code_pointer: u32) -> Option<u8> {
        decode_profile_instruction(cell, code_pointer)
    }
}

struct AmbiguousInstructionDecoder;

impl ProfileInstructionDecoder for AmbiguousInstructionDecoder {
    fn decode(&self, _cell: u32, _code_pointer: u32) -> Option<u8> {
        Some(current_profile().input_instruction())
    }
}

struct MissingInstructionDecoder;

impl ProfileInstructionDecoder for MissingInstructionDecoder {
    fn decode(&self, _cell: u32, _code_pointer: u32) -> Option<u8> {
        None
    }
}

fn repository_python() -> PathBuf {
    let root = Path::new(env!("CARGO_MANIFEST_DIR"));
    if cfg!(windows) {
        root.join(".dependencies/python/3.14.7/python.exe")
    } else {
        root.join(".dependencies/python/3.14.7/bin/python")
    }
}

fn temporary_ternary_file(
    stem: &str,
    extension: &str,
    bytes: &[u8],
) -> Result<PathBuf, String> {
    let path = temp_dir()
        .join(format!("malbolge-ternary-{stem}-{}.{extension}", id()));
    write(&path, bytes)
        .map_err(|error| format!("write temporary ternary {stem}: {error}"))?;
    Ok(path)
}

fn progress_inspector() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join(
        "src/automation/repository/composition/scripts/progress_sidecar.py",
    )
}

fn publish_ternary_progress_fixture(
    label: &str,
    bytes: &[u8],
) -> Result<TernaryProgressFixture, String> {
    let directory =
        temp_dir().join(format!("malbolge-ternary-progress-{}-{label}", id()));
    if directory.exists() {
        remove_dir_all(&directory).map_err(|error| {
            format!("remove stale ternary fixture: {error}")
        })?;
    }
    create_dir_all(&directory)
        .map_err(|error| format!("create ternary progress fixture: {error}"))?;
    let payload = directory.join("ternary.checkpoint");
    write(&payload, bytes).map_err(|error| {
        format!("write ternary checkpoint payload: {error}")
    })?;
    let root = Path::new(env!("CARGO_MANIFEST_DIR"));
    let module_root = root.join("src/automation/repository/composition");
    let output = Command::new(repository_python())
        .arg("-B")
        .arg("-c")
        .arg(TERNARY_PROGRESS_FIXTURE_SCRIPT)
        .arg(module_root)
        .arg(&directory)
        .arg(&payload)
        .output()
        .map_err(|error| {
            format!("publish ternary progress fixture: {error}")
        })?;
    if !output.status.success() {
        let _cleanup = remove_dir_all(&directory);
        return Err(format!(
            "ternary progress fixture publication failed: {}",
            String::from_utf8_lossy(&output.stderr),
        ));
    }
    Ok((directory.join("program.malbolge.progress.json"), directory))
}

fn ternary_crash_directory(boundary: &str) -> Result<PathBuf, String> {
    let sequence = NEXT_TERNARY_CRASH_FIXTURE.fetch_add(1, Ordering::Relaxed);
    let directory = temp_dir().join(format!(
        "malbolge-ternary-crash-{}-{boundary}-{sequence}",
        id(),
    ));
    if directory.exists() {
        remove_dir_all(&directory).map_err(|error| {
            format!("remove stale ternary crash fixture: {error}")
        })?;
    }
    create_dir_all(&directory)
        .map_err(|error| format!("create ternary crash fixture: {error}"))?;
    Ok(directory)
}

fn write_ternary_crash_states(
    directory: PathBuf,
    first: &ternary_lowering::TernaryProgram,
    second: &ternary_lowering::TernaryProgram,
) -> Result<TernaryCrashPaths, String> {
    let first_path = directory.join("first.ternary");
    let second_path = directory.join("second.ternary");
    let first_bytes = canonical_ternary_bytes(first).map_err(|error| {
        format!("encode first ternary crash state: {error:?}")
    })?;
    let second_bytes = canonical_ternary_bytes(second).map_err(|error| {
        format!("encode second ternary crash state: {error:?}")
    })?;
    write(&first_path, first_bytes)
        .map_err(|error| format!("write first ternary crash state: {error}"))?;
    write(&second_path, second_bytes).map_err(|error| {
        format!("write second ternary crash state: {error}")
    })?;
    Ok(TernaryCrashPaths {
        directory,
        first: first_path,
        second: second_path,
    })
}

fn launch_ternary_crash(
    root: &Path,
    boundary: &str,
    paths: &TernaryCrashPaths,
) -> Result<PathBuf, String> {
    let output = paths.directory.join("program.malbolge");
    let progress =
        PathBuf::from(format!("{}.progress.json", output.to_string_lossy()));
    let crashed = Command::new(repository_python())
        .arg("-B")
        .arg("-c")
        .arg(TERNARY_PROGRESS_CRASH_SCRIPT)
        .arg(&output)
        .arg(&paths.first)
        .arg(&paths.second)
        .arg(TERNARY_CRASH_EXIT.to_string())
        .arg(boundary)
        .env(
            "PYTHONPATH",
            root.join("src/automation/repository/composition"),
        )
        .output()
        .map_err(|error| format!("run ternary crash fixture: {error}"))?;
    if crashed.status.code() != Some(TERNARY_CRASH_EXIT) {
        return Err(format!(
            "ternary crash boundary {boundary} did not terminate: {}",
            String::from_utf8_lossy(&crashed.stderr),
        ));
    }
    Ok(progress)
}

fn run_ternary_crash_boundary(
    boundary: &str,
    first: &ternary_lowering::TernaryProgram,
    second: &ternary_lowering::TernaryProgram,
) -> Result<(), String> {
    let root = Path::new(env!("CARGO_MANIFEST_DIR"));
    let directory = ternary_crash_directory(boundary)?;
    let paths = write_ternary_crash_states(directory, first, second)?;
    let result = (|| {
        let progress = launch_ternary_crash(root, boundary, &paths)?;
        let restored = resume_ternary_from_progress(
            &repository_python(),
            &progress_inspector(),
            &progress,
        )
        .map_err(|error| {
            format!("resume ternary state after {boundary}: {error:?}")
        })?;
        let expected = if matches!(
            boundary,
            "after-sidecar-replace" | "after-sidecar-sync"
        ) {
            second
        } else {
            first
        };
        if &restored != expected {
            return Err(format!(
                "ternary crash boundary {boundary} restored wrong generation",
            ));
        }
        Ok(())
    })();
    let cleanup = remove_dir_all(&paths.directory)
        .map_err(|error| format!("remove ternary crash fixture: {error}"));
    result?;
    cleanup
}

fn valid_startup_request() -> StartupRequest {
    StartupRequest {
        abi_id: String::from("malbolge-c32-v1"),
        arena_pointer: 0x101,
        bind_identity: String::from("malbolge_guest_runtime_bind_heap"),
        capacity: 0x100,
        target_profile: String::from("malbolge-2026"),
        user_entry_function: 7,
    }
}

fn admitted_byte_io_fixture() -> Result<Module, String> {
    let module = byte_io_module();
    validate_module(&module)
        .map_err(|error| format!("validate byte-I/O fixture: {error:?}"))?;
    let bytes = canonical_bytes(&module)
        .map_err(|error| format!("canonicalize byte-I/O fixture: {error:?}"))?;
    let restored = canonical_module(&bytes)
        .map_err(|error| format!("restore byte-I/O fixture: {error:?}"))?;
    if restored != module {
        return Err(String::from("byte-I/O canonical round trip drifted"));
    }
    Ok(restored)
}

fn admitted_low_byte_fixture() -> Result<Module, String> {
    let module = low_byte_module();
    validate_module(&module)
        .map_err(|error| format!("validate low-byte fixture: {error:?}"))?;
    let bytes = canonical_bytes(&module)
        .map_err(|error| format!("canonicalize low-byte fixture: {error:?}"))?;
    let restored = canonical_module(&bytes)
        .map_err(|error| format!("restore low-byte fixture: {error:?}"))?;
    if restored != module {
        return Err(String::from("low-byte canonical round trip drifted"));
    }
    Ok(restored)
}

fn admitted_golden(path: &str) -> Result<Module, String> {
    let bytes = canonical_golden(path)?;
    canonical_module(&bytes)
        .map_err(|error| format!("admit typed IR: {error:?}"))
}

fn assert_byte_io_program(
    module: &Module,
    program: &ternary_lowering::TernaryProgram,
) -> Result<(), String> {
    assert_program_provenance(module, program)?;
    let function = program
        .functions
        .first()
        .ok_or_else(|| String::from("byte-I/O lowering emitted no function"))?;
    if function.operations.len() != 4 {
        return Err(String::from("unexpected byte-I/O operation count"));
    }
    assert_byte_input(function)?;
    assert_byte_output(function)?;
    assert_byte_return_materialization(function)?;
    assert_byte_return(function)
}

fn assert_byte_input(
    function: &ternary_lowering::TernaryFunction,
) -> Result<(), String> {
    let operation = function
        .operations
        .first()
        .ok_or_else(|| String::from("missing byte input operation"))?;
    let TernaryOperation::ByteInput { result, span } = operation else {
        return Err(String::from("first byte-I/O operation is not input"));
    };
    if *result != 0 || *span != output_span(fixture_span(0, 1)) {
        return Err(String::from("byte input lowering drifted"));
    }
    Ok(())
}

fn assert_byte_output(
    function: &ternary_lowering::TernaryFunction,
) -> Result<(), String> {
    let operation = function
        .operations
        .get(1)
        .ok_or_else(|| String::from("missing byte output operation"))?;
    let TernaryOperation::ByteOutput { span, value } = operation else {
        return Err(String::from("second byte-I/O operation is not output"));
    };
    if *value != 0 || *span != output_span(fixture_span(1, 2)) {
        return Err(String::from("byte output lowering drifted"));
    }
    Ok(())
}

fn assert_byte_return(
    function: &ternary_lowering::TernaryFunction,
) -> Result<(), String> {
    let operation = function
        .operations
        .get(3)
        .ok_or_else(|| String::from("missing byte-I/O return"))?;
    let TernaryOperation::Return { span, value } = operation else {
        return Err(String::from("fourth byte-I/O operation is not return"));
    };
    if *value != 1 || *span != output_span(fixture_span(3, 4)) {
        return Err(String::from("byte-I/O return lowering drifted"));
    }
    Ok(())
}

fn assert_byte_return_materialization(
    function: &ternary_lowering::TernaryFunction,
) -> Result<(), String> {
    let operation = function.operations.get(2).ok_or_else(|| {
        String::from("missing byte-I/O return materialization")
    })?;
    let TernaryOperation::MaterializeI32 { result, scalar, span } = operation
    else {
        return Err(String::from(
            "third byte-I/O operation is not i32 materialization",
        ));
    };
    if *result != 1
        || scalar.bits() != 0
        || *span != output_span(fixture_span(2, 3))
    {
        return Err(String::from("byte-I/O return materialization drifted"));
    }
    Ok(())
}

fn assert_constant_return_program(
    module: &Module,
    program: &ternary_lowering::TernaryProgram,
) -> Result<(), String> {
    assert_program_provenance(module, program)?;
    let function = program
        .functions
        .first()
        .ok_or_else(|| String::from("lowering emitted no function"))?;
    if function.operations.len() != 2 {
        return Err(String::from("unexpected ternary operation count"));
    }
    assert_materialize(module, function)?;
    assert_return(module, function)
}

fn assert_materialize(
    module: &Module,
    function: &ternary_lowering::TernaryFunction,
) -> Result<(), String> {
    let materialize = function
        .operations
        .first()
        .ok_or_else(|| String::from("missing ternary materialization"))?;
    let TernaryOperation::MaterializeI32 { result, scalar, span } = materialize
    else {
        return Err(String::from("first operation is not i32 materialization"));
    };
    let input_function = module
        .functions()
        .first()
        .ok_or_else(|| String::from("typed IR has no function"))?;
    let input_instruction = input_function
        .blocks()
        .first()
        .and_then(|block| block.instructions().first())
        .ok_or_else(|| String::from("typed IR has no instruction"))?;
    if *result != 0
        || scalar.bits() != 7
        || scalar.trits().len() != I32_TERNARY_TRITS
        || scalar.trits().first() != Some(&1)
        || scalar.trits().get(1) != Some(&2)
        || scalar.trits().iter().any(|trit| *trit > 2)
        || *span != output_span(input_instruction.span())
    {
        return Err(String::from("i32 ternary materialization drifted"));
    }
    Ok(())
}

fn assert_program_provenance(
    module: &Module,
    program: &ternary_lowering::TernaryProgram,
) -> Result<(), String> {
    let function = program.functions.first();
    let input_function = module.functions().first();
    if program.abi_id != module.abi_id()
        || program.input_format_version != module.format_version()
        || program.source_id != module.source_id()
        || program.source_sha256 != *module.source_sha256()
        || program.target_profile != module.target_profile()
        || program.functions.len() != 1
        || function.map(|value| value.span)
            != input_function.map(|value| output_span(value.span()))
    {
        return Err(String::from("ternary program provenance drifted"));
    }
    Ok(())
}

fn assert_return(
    module: &Module,
    function: &ternary_lowering::TernaryFunction,
) -> Result<(), String> {
    let returned = function
        .operations
        .get(1)
        .ok_or_else(|| String::from("missing ternary return"))?;
    let TernaryOperation::Return { span, value } = returned else {
        return Err(String::from("second operation is not return"));
    };
    let input_span = module
        .functions()
        .first()
        .and_then(|input_function| input_function.blocks().first())
        .map(|block| output_span(block.terminator_span()))
        .ok_or_else(|| String::from("typed IR has no return block"))?;
    if *value != 0 || *span != input_span {
        return Err(String::from(
            "return operation did not use materialized value",
        ));
    }
    Ok(())
}

const fn output_span(span: SourceSpan) -> ternary_lowering::TernarySourceSpan {
    let begin = span.begin();
    let end = span.end();
    ternary_lowering::TernarySourceSpan {
        begin: ternary_lowering::TernarySourcePosition {
            byte: begin.byte(),
            column: begin.column(),
            line: begin.line(),
        },
        end: ternary_lowering::TernarySourcePosition {
            byte: end.byte(),
            column: end.column(),
            line: end.line(),
        },
    }
}

fn byte_io_module() -> Module {
    byte_io_module_with_constant(None)
}

fn byte_source_instruction(
    value: Option<u8>,
    u8_type: TypeId,
) -> LocatedInstruction {
    let source = value.map_or_else(
        || Instruction::ByteInput {
            result: ValueId::new(0),
            type_id: u8_type,
        },
        |byte| Instruction::ConstantInteger {
            constant: IntegerConstant::new(8, vec![byte]),
            result: ValueId::new(0),
            type_id: u8_type,
        },
    );
    LocatedInstruction::new(source, fixture_span(0, 1))
}

fn byte_io_module_with_constant(value: Option<u8>) -> Module {
    byte_io_module_with_return(value, false)
}

fn byte_return_module(value: Option<u8>) -> Module {
    byte_io_module_with_return(value, true)
}

fn byte_function_types(return_byte: bool) -> Vec<TypeEntry> {
    let byte_type = TypeId::new(0);
    let integer_type = TypeId::new(1);
    vec![
        TypeEntry::new(byte_type, TypeDef::U8),
        TypeEntry::new(integer_type, TypeDef::I32),
        TypeEntry::new(
            TypeId::new(2),
            TypeDef::function(
                Vec::new(),
                Some(if return_byte {
                    byte_type
                } else {
                    integer_type
                }),
                false,
            ),
        ),
    ]
}

fn byte_io_module_with_return(value: Option<u8>, return_byte: bool) -> Module {
    let u8_type = TypeId::new(0);
    let i32_type = TypeId::new(1);
    let function_type = TypeId::new(2);
    let block = BasicBlock::new(BasicBlockSpec {
        id: BlockId::new(0),
        instructions: vec![
            byte_source_instruction(value, u8_type),
            LocatedInstruction::new(
                Instruction::ByteOutput { value: ValueId::new(0) },
                fixture_span(1, 2),
            ),
            LocatedInstruction::new(
                Instruction::ConstantInteger {
                    constant: IntegerConstant::new(32, vec![0, 0, 0, 0]),
                    result: ValueId::new(1),
                    type_id: i32_type,
                },
                fixture_span(2, 3),
            ),
        ],
        phis: Vec::new(),
        span: fixture_span(0, 4),
        terminator: Terminator::Return {
            value: Some(ValueId::new(u32::from(!return_byte))),
        },
        terminator_span: fixture_span(3, 4),
    });
    let function = Function::new(FunctionSpec {
        blocks: vec![block],
        entry: BlockId::new(0),
        id: FunctionId::new(0),
        name: String::from("byte_round_trip"),
        parameters: Vec::new(),
        signature: function_type,
        span: fixture_span(0, 4),
    });
    Module::new(ModuleSpec {
        abi_id: String::from("malbolge-c32-v1"),
        format_version: typed_ir::TYPED_IR_VERSION,
        functions: vec![function],
        globals: Vec::new(),
        proof_obligations: Vec::new(),
        source_id: String::from("fixtures/byte-io.c"),
        source_sha256: BYTE_IO_SOURCE_HASH,
        target_profile: String::from("malbolge-2026"),
        types: byte_function_types(return_byte),
    })
}

fn unsigned_module(
    instructions: Vec<LocatedInstruction>,
    returned: u32,
    end: u32,
) -> Module {
    unsigned_module_with_result(instructions, returned, end, false)
}

fn unsigned_module_with_result(
    instructions: Vec<LocatedInstruction>,
    returned: u32,
    end: u32,
    byte_return: bool,
) -> Module {
    let u32_type = TypeId::new(0);
    let u8_type = TypeId::new(2);
    let return_type = if byte_return {
        u8_type
    } else {
        u32_type
    };
    let signature = TypeId::new(1);
    let block = BasicBlock::new(BasicBlockSpec {
        id: BlockId::new(0),
        instructions,
        phis: Vec::new(),
        span: fixture_span(0, end),
        terminator: Terminator::Return {
            value: Some(ValueId::new(returned)),
        },
        terminator_span: fixture_span(end.saturating_sub(1), end),
    });
    let function = Function::new(FunctionSpec {
        blocks: vec![block],
        entry: BlockId::new(0),
        id: FunctionId::new(0),
        name: String::from("unsigned_return"),
        parameters: Vec::new(),
        signature,
        span: fixture_span(0, end),
    });
    Module::new(ModuleSpec {
        abi_id: String::from("malbolge-c32-v1"),
        format_version: typed_ir::TYPED_IR_VERSION,
        functions: vec![function],
        globals: Vec::new(),
        proof_obligations: Vec::new(),
        source_id: String::from("fixtures/unsigned-return.c"),
        source_sha256: [0x8d; 32],
        target_profile: String::from("malbolge-2026"),
        types: vec![
            TypeEntry::new(u32_type, TypeDef::U32),
            TypeEntry::new(
                signature,
                TypeDef::function(Vec::new(), Some(return_type), false),
            ),
            TypeEntry::new(u8_type, TypeDef::U8),
        ],
    })
}

fn integer_bitcast_types(
    source_signed: bool,
    same_kind: bool,
) -> Vec<TypeEntry> {
    let source_kind = if source_signed {
        TypeDef::I32
    } else {
        TypeDef::U32
    };
    let dest_kind = if source_signed == same_kind {
        TypeDef::I32
    } else {
        TypeDef::U32
    };
    vec![
        TypeEntry::new(TypeId::new(0), source_kind),
        TypeEntry::new(
            TypeId::new(1),
            TypeDef::function(Vec::new(), Some(TypeId::new(2)), false),
        ),
        TypeEntry::new(TypeId::new(2), dest_kind),
    ]
}

fn integer_bitcast_module(source_signed: bool, bits: u32) -> Module {
    integer_bitcast_module_with_kind(source_signed, bits, false)
}

fn integer_bitcast_module_with_kind(
    source_signed: bool,
    bits: u32,
    same_kind: bool,
) -> Module {
    let source_type = TypeId::new(0);
    let function_type = TypeId::new(1);
    let destination_type = TypeId::new(2);
    let instructions = vec![
        LocatedInstruction::new(
            Instruction::ConstantInteger {
                constant: IntegerConstant::new(32, bits.to_le_bytes().to_vec()),
                result: ValueId::new(0),
                type_id: source_type,
            },
            fixture_span(0, 1),
        ),
        LocatedInstruction::new(
            Instruction::Cast {
                operation: CastOp::IntegerBitcast,
                result: ValueId::new(1),
                type_id: destination_type,
                value: ValueId::new(0),
            },
            fixture_span(1, 2),
        ),
    ];
    let function = Function::new(FunctionSpec {
        blocks: vec![BasicBlock::new(BasicBlockSpec {
            id: BlockId::new(0),
            instructions,
            phis: Vec::new(),
            span: fixture_span(0, 3),
            terminator: Terminator::Return {
                value: Some(ValueId::new(1)),
            },
            terminator_span: fixture_span(2, 3),
        })],
        entry: BlockId::new(0),
        id: FunctionId::new(0),
        name: String::from("integer_bitcast"),
        parameters: Vec::new(),
        signature: function_type,
        span: fixture_span(0, 3),
    });
    Module::new(ModuleSpec {
        abi_id: String::from("malbolge-c32-v1"),
        format_version: typed_ir::TYPED_IR_VERSION,
        functions: vec![function],
        globals: Vec::new(),
        proof_obligations: Vec::new(),
        source_id: String::from("fixtures/integer-bitcast.c"),
        source_sha256: [0x8e; 32],
        target_profile: String::from("malbolge-2026"),
        types: integer_bitcast_types(source_signed, same_kind),
    })
}

fn unsigned_zero_extend_module(source: Option<u8>) -> Module {
    let u32_type = TypeId::new(0);
    let u8_type = TypeId::new(2);
    let source_instruction = source.map_or_else(
        || Instruction::ByteInput {
            result: ValueId::new(0),
            type_id: u8_type,
        },
        |byte| Instruction::ConstantInteger {
            constant: IntegerConstant::new(8, vec![byte]),
            result: ValueId::new(0),
            type_id: u8_type,
        },
    );
    unsigned_module(
        vec![
            LocatedInstruction::new(source_instruction, fixture_span(0, 1)),
            LocatedInstruction::new(
                Instruction::Cast {
                    operation: CastOp::ZeroExtend,
                    result: ValueId::new(1),
                    type_id: u32_type,
                    value: ValueId::new(0),
                },
                fixture_span(1, 2),
            ),
        ],
        1,
        3,
    )
}

fn unsigned_truncate_module(bits: u32) -> Module {
    let u32_type = TypeId::new(0);
    let u8_type = TypeId::new(2);
    let instructions = vec![
        LocatedInstruction::new(
            Instruction::ConstantInteger {
                constant: IntegerConstant::new(32, bits.to_le_bytes().to_vec()),
                result: ValueId::new(0),
                type_id: u32_type,
            },
            fixture_span(0, 1),
        ),
        LocatedInstruction::new(
            Instruction::Cast {
                operation: CastOp::Truncate,
                result: ValueId::new(1),
                type_id: u8_type,
                value: ValueId::new(0),
            },
            fixture_span(1, 2),
        ),
    ];
    unsigned_module_with_result(instructions, 1, 3, true)
}

fn unsigned_return_module(bits: u32) -> Module {
    unsigned_module(
        vec![LocatedInstruction::new(
            Instruction::ConstantInteger {
                constant: IntegerConstant::new(32, bits.to_le_bytes().to_vec()),
                result: ValueId::new(0),
                type_id: TypeId::new(0),
            },
            fixture_span(0, 1),
        )],
        0,
        2,
    )
}

fn unsigned_bitwise_module(left: u32, right: u32, op: BinaryOp) -> Module {
    let u32_type = TypeId::new(0);
    let mut instructions = Vec::new();
    for (index, bits) in [(0u32, left), (1, right)] {
        instructions.push(LocatedInstruction::new(
            Instruction::ConstantInteger {
                constant: IntegerConstant::new(32, bits.to_le_bytes().to_vec()),
                result: ValueId::new(index),
                type_id: u32_type,
            },
            fixture_span(index, index.saturating_add(1)),
        ));
    }
    instructions.push(LocatedInstruction::new(
        Instruction::Binary {
            left: ValueId::new(0),
            operation: op,
            result: ValueId::new(2),
            right: ValueId::new(1),
            type_id: u32_type,
        },
        fixture_span(2, 3),
    ));
    unsigned_module(instructions, 2, 4)
}

fn unsigned_alias_bitwise_module(bits: u32, operation: BinaryOp) -> Module {
    let u32_type = TypeId::new(0);
    unsigned_module(
        vec![
            LocatedInstruction::new(
                Instruction::ConstantInteger {
                    constant: IntegerConstant::new(
                        32,
                        bits.to_le_bytes().to_vec(),
                    ),
                    result: ValueId::new(0),
                    type_id: u32_type,
                },
                fixture_span(0, 1),
            ),
            LocatedInstruction::new(
                Instruction::Binary {
                    left: ValueId::new(0),
                    operation,
                    result: ValueId::new(1),
                    right: ValueId::new(0),
                    type_id: u32_type,
                },
                fixture_span(1, 2),
            ),
        ],
        1,
        3,
    )
}

fn signed_alias_bitwise_module(bits: u32, operation: BinaryOp) -> Module {
    let integer_type = TypeId::new(0);
    let signature = TypeId::new(1);
    let instructions = vec![
        LocatedInstruction::new(
            Instruction::ConstantInteger {
                constant: IntegerConstant::new(32, bits.to_le_bytes().to_vec()),
                result: ValueId::new(0),
                type_id: integer_type,
            },
            fixture_span(0, 1),
        ),
        LocatedInstruction::new(
            Instruction::Binary {
                left: ValueId::new(0),
                operation,
                result: ValueId::new(1),
                right: ValueId::new(0),
                type_id: integer_type,
            },
            fixture_span(1, 2),
        ),
    ];
    let block = BasicBlock::new(BasicBlockSpec {
        id: BlockId::new(0),
        instructions,
        phis: Vec::new(),
        span: fixture_span(0, 3),
        terminator: Terminator::Return {
            value: Some(ValueId::new(1)),
        },
        terminator_span: fixture_span(2, 3),
    });
    Module::new(ModuleSpec {
        abi_id: String::from("malbolge-c32-v1"),
        format_version: typed_ir::TYPED_IR_VERSION,
        functions: vec![Function::new(FunctionSpec {
            blocks: vec![block],
            entry: BlockId::new(0),
            id: FunctionId::new(0),
            name: String::from("signed_alias"),
            parameters: Vec::new(),
            signature,
            span: fixture_span(0, 3),
        })],
        globals: Vec::new(),
        proof_obligations: Vec::new(),
        source_id: String::from("fixtures/signed-alias.c"),
        source_sha256: [0x8e; 32],
        target_profile: String::from("malbolge-2026"),
        types: vec![
            TypeEntry::new(integer_type, TypeDef::I32),
            TypeEntry::new(
                signature,
                TypeDef::function(Vec::new(), Some(integer_type), false),
            ),
        ],
    })
}

fn chained_bool_conversion_types(
    signed: bool,
) -> (Vec<TypeEntry>, TypeId, TypeId) {
    let mut types = vec![
        TypeEntry::new(
            TypeId::new(0),
            if signed {
                TypeDef::I32
            } else {
                TypeDef::U32
            },
        ),
        TypeEntry::new(TypeId::new(1), TypeDef::Bool),
    ];
    let return_type = if signed {
        TypeId::new(0)
    } else {
        TypeId::new(2)
    };
    if !signed {
        types.push(TypeEntry::new(return_type, TypeDef::I32));
    }
    let signature = TypeId::new(if signed {
        2
    } else {
        3
    });
    types.push(TypeEntry::new(
        signature,
        TypeDef::function(Vec::new(), Some(return_type), false),
    ));
    (types, return_type, signature)
}

fn chained_bool_conversion_module(signed: bool, bits: u32) -> Module {
    let (types, return_type, signature) = chained_bool_conversion_types(signed);
    let instructions = vec![
        low_byte_constant(bits, 0, 0, TypeId::new(0)),
        LocatedInstruction::new(
            Instruction::Cast {
                operation: CastOp::IntegerToBool,
                result: ValueId::new(1),
                type_id: TypeId::new(1),
                value: ValueId::new(0),
            },
            fixture_span(1, 2),
        ),
        LocatedInstruction::new(
            Instruction::Cast {
                operation: CastOp::BoolToSigned,
                result: ValueId::new(2),
                type_id: return_type,
                value: ValueId::new(1),
            },
            fixture_span(2, 3),
        ),
    ];
    Module::new(ModuleSpec {
        abi_id: String::from("malbolge-c32-v1"),
        format_version: typed_ir::TYPED_IR_VERSION,
        functions: vec![Function::new(FunctionSpec {
            blocks: vec![BasicBlock::new(BasicBlockSpec {
                id: BlockId::new(0),
                instructions,
                phis: Vec::new(),
                span: fixture_span(0, 4),
                terminator: Terminator::Return {
                    value: Some(ValueId::new(2)),
                },
                terminator_span: fixture_span(3, 4),
            })],
            entry: BlockId::new(0),
            id: FunctionId::new(0),
            name: String::from("chained_bool_conversion"),
            parameters: Vec::new(),
            signature,
            span: fixture_span(0, 4),
        })],
        globals: Vec::new(),
        proof_obligations: Vec::new(),
        source_id: String::from("fixtures/chained-bool-conversion.c"),
        source_sha256: [0xd7; 32],
        target_profile: String::from("malbolge-2026"),
        types,
    })
}

fn truncated_byte_truth_types() -> Vec<TypeEntry> {
    vec![
        TypeEntry::new(TypeId::new(0), TypeDef::U32),
        TypeEntry::new(TypeId::new(1), TypeDef::U8),
        TypeEntry::new(TypeId::new(2), TypeDef::Bool),
        TypeEntry::new(TypeId::new(3), TypeDef::I32),
        TypeEntry::new(
            TypeId::new(4),
            TypeDef::function(Vec::new(), Some(TypeId::new(3)), false),
        ),
    ]
}

fn truncated_byte_truth_module(bits: u32) -> Module {
    let instructions = vec![
        low_byte_constant(bits, 0, 0, TypeId::new(0)),
        LocatedInstruction::new(
            Instruction::Cast {
                operation: CastOp::Truncate,
                result: ValueId::new(1),
                type_id: TypeId::new(1),
                value: ValueId::new(0),
            },
            fixture_span(1, 2),
        ),
        LocatedInstruction::new(
            Instruction::Cast {
                operation: CastOp::IntegerToBool,
                result: ValueId::new(2),
                type_id: TypeId::new(2),
                value: ValueId::new(1),
            },
            fixture_span(2, 3),
        ),
        LocatedInstruction::new(
            Instruction::Cast {
                operation: CastOp::BoolToSigned,
                result: ValueId::new(3),
                type_id: TypeId::new(3),
                value: ValueId::new(2),
            },
            fixture_span(3, 4),
        ),
    ];
    Module::new(ModuleSpec {
        abi_id: String::from("malbolge-c32-v1"),
        format_version: typed_ir::TYPED_IR_VERSION,
        functions: vec![Function::new(FunctionSpec {
            blocks: vec![BasicBlock::new(BasicBlockSpec {
                id: BlockId::new(0),
                instructions,
                phis: Vec::new(),
                span: fixture_span(0, 5),
                terminator: Terminator::Return {
                    value: Some(ValueId::new(3)),
                },
                terminator_span: fixture_span(4, 5),
            })],
            entry: BlockId::new(0),
            id: FunctionId::new(0),
            name: String::from("truncated_byte_truth"),
            parameters: Vec::new(),
            signature: TypeId::new(4),
            span: fixture_span(0, 5),
        })],
        globals: Vec::new(),
        proof_obligations: Vec::new(),
        source_id: String::from("fixtures/truncated-byte-truth.c"),
        source_sha256: [0xf9; 32],
        target_profile: String::from("malbolge-2026"),
        types: truncated_byte_truth_types(),
    })
}

fn integer_to_bool_module(signed: bool, bits: u32) -> Module {
    let word_type = TypeId::new(0);
    let bool_type = TypeId::new(1);
    let signature = TypeId::new(2);
    let instructions = vec![
        low_byte_constant(bits, 0, 0, word_type),
        LocatedInstruction::new(
            Instruction::Cast {
                operation: CastOp::IntegerToBool,
                result: ValueId::new(1),
                type_id: bool_type,
                value: ValueId::new(0),
            },
            fixture_span(1, 2),
        ),
    ];
    Module::new(ModuleSpec {
        abi_id: String::from("malbolge-c32-v1"),
        format_version: typed_ir::TYPED_IR_VERSION,
        functions: vec![Function::new(FunctionSpec {
            blocks: vec![BasicBlock::new(BasicBlockSpec {
                id: BlockId::new(0),
                instructions,
                phis: Vec::new(),
                span: fixture_span(0, 3),
                terminator: Terminator::Return {
                    value: Some(ValueId::new(1)),
                },
                terminator_span: fixture_span(2, 3),
            })],
            entry: BlockId::new(0),
            id: FunctionId::new(0),
            name: String::from("integer_to_bool"),
            parameters: Vec::new(),
            signature,
            span: fixture_span(0, 3),
        })],
        globals: Vec::new(),
        proof_obligations: Vec::new(),
        source_id: String::from("fixtures/integer-to-bool.c"),
        source_sha256: [0xc7; 32],
        target_profile: String::from("malbolge-2026"),
        types: comparison_types(signed),
    })
}

fn void_function_module(with_io: bool) -> Module {
    let byte_type = TypeId::new(0);
    let signature = TypeId::new(1);
    let instructions = if with_io {
        vec![
            LocatedInstruction::new(
                Instruction::ByteInput {
                    result: ValueId::new(0),
                    type_id: byte_type,
                },
                fixture_span(0, 1),
            ),
            LocatedInstruction::new(
                Instruction::ByteOutput { value: ValueId::new(0) },
                fixture_span(1, 2),
            ),
        ]
    } else {
        Vec::new()
    };
    let end = if with_io {
        3
    } else {
        1
    };
    Module::new(ModuleSpec {
        abi_id: String::from("malbolge-c32-v1"),
        format_version: typed_ir::TYPED_IR_VERSION,
        functions: vec![Function::new(FunctionSpec {
            blocks: vec![BasicBlock::new(BasicBlockSpec {
                id: BlockId::new(0),
                instructions,
                phis: Vec::new(),
                span: fixture_span(0, end),
                terminator: Terminator::Return { value: None },
                terminator_span: fixture_span(end.saturating_sub(1), end),
            })],
            entry: BlockId::new(0),
            id: FunctionId::new(0),
            name: String::from("void_function"),
            parameters: Vec::new(),
            signature,
            span: fixture_span(0, end),
        })],
        globals: Vec::new(),
        proof_obligations: Vec::new(),
        source_id: String::from("fixtures/void-return.c"),
        source_sha256: [0xcf; 32],
        target_profile: String::from("malbolge-2026"),
        types: vec![
            TypeEntry::new(byte_type, TypeDef::U8),
            TypeEntry::new(
                signature,
                TypeDef::function(Vec::new(), None, false),
            ),
        ],
    })
}

fn mixed_void_function(id: u32, with_io: bool) -> Function {
    let start = id.saturating_mul(5);
    let instructions = if with_io {
        vec![
            LocatedInstruction::new(
                Instruction::ByteInput {
                    result: ValueId::new(0),
                    type_id: TypeId::new(0),
                },
                fixture_span(start, start.saturating_add(1)),
            ),
            LocatedInstruction::new(
                Instruction::ByteOutput { value: ValueId::new(0) },
                fixture_span(start.saturating_add(1), start.saturating_add(2)),
            ),
        ]
    } else {
        Vec::new()
    };
    let end = start.saturating_add(if with_io {
        3
    } else {
        1
    });
    Function::new(FunctionSpec {
        blocks: vec![BasicBlock::new(BasicBlockSpec {
            id: BlockId::new(0),
            instructions,
            phis: Vec::new(),
            span: fixture_span(start, end),
            terminator: Terminator::Return { value: None },
            terminator_span: fixture_span(end.saturating_sub(1), end),
        })],
        entry: BlockId::new(0),
        id: FunctionId::new(id),
        name: String::from("void_member"),
        parameters: Vec::new(),
        signature: TypeId::new(2),
        span: fixture_span(start, end),
    })
}

fn mixed_value_function(id: u32) -> Function {
    let start = id.saturating_mul(5);
    let end = start.saturating_add(2);
    Function::new(FunctionSpec {
        blocks: vec![BasicBlock::new(BasicBlockSpec {
            id: BlockId::new(0),
            instructions: vec![low_byte_constant(7, 0, start, TypeId::new(1))],
            phis: Vec::new(),
            span: fixture_span(start, end),
            terminator: Terminator::Return {
                value: Some(ValueId::new(0)),
            },
            terminator_span: fixture_span(end.saturating_sub(1), end),
        })],
        entry: BlockId::new(0),
        id: FunctionId::new(id),
        name: String::from("value_member"),
        parameters: Vec::new(),
        signature: TypeId::new(3),
        span: fixture_span(start, end),
    })
}

fn mixed_return_module(void_first: bool, with_io: bool) -> Module {
    let functions = if void_first {
        vec![mixed_void_function(0, with_io), mixed_value_function(1)]
    } else {
        vec![mixed_value_function(0), mixed_void_function(1, with_io)]
    };
    Module::new(ModuleSpec {
        abi_id: String::from("malbolge-c32-v1"),
        format_version: typed_ir::TYPED_IR_VERSION,
        functions,
        globals: Vec::new(),
        proof_obligations: Vec::new(),
        source_id: String::from("fixtures/mixed-return.c"),
        source_sha256: [0xdc; 32],
        target_profile: String::from("malbolge-2026"),
        types: vec![
            TypeEntry::new(TypeId::new(0), TypeDef::U8),
            TypeEntry::new(TypeId::new(1), TypeDef::I32),
            TypeEntry::new(
                TypeId::new(2),
                TypeDef::function(Vec::new(), None, false),
            ),
            TypeEntry::new(
                TypeId::new(3),
                TypeDef::function(Vec::new(), Some(TypeId::new(1)), false),
            ),
        ],
    })
}

fn halfword_return_module(bits: u16, signed: bool) -> Module {
    let kind = if signed {
        TypeDef::I16
    } else {
        TypeDef::U16
    };
    Module::new(ModuleSpec {
        abi_id: String::from("malbolge-c32-v1"),
        format_version: typed_ir::TYPED_IR_VERSION,
        functions: vec![Function::new(FunctionSpec {
            blocks: vec![BasicBlock::new(BasicBlockSpec {
                id: BlockId::new(0),
                instructions: vec![LocatedInstruction::new(
                    Instruction::ConstantInteger {
                        constant: IntegerConstant::new(
                            16,
                            bits.to_le_bytes().to_vec(),
                        ),
                        result: ValueId::new(0),
                        type_id: TypeId::new(0),
                    },
                    fixture_span(0, 1),
                )],
                phis: Vec::new(),
                span: fixture_span(0, 2),
                terminator: Terminator::Return {
                    value: Some(ValueId::new(0)),
                },
                terminator_span: fixture_span(1, 2),
            })],
            entry: BlockId::new(0),
            id: FunctionId::new(0),
            name: String::from("return_halfword"),
            parameters: Vec::new(),
            signature: TypeId::new(1),
            span: fixture_span(0, 2),
        })],
        globals: Vec::new(),
        proof_obligations: Vec::new(),
        source_id: String::from("fixtures/return-halfword.c"),
        source_sha256: [0x16; 32],
        target_profile: String::from("malbolge-2026"),
        types: vec![
            TypeEntry::new(TypeId::new(0), kind),
            TypeEntry::new(
                TypeId::new(1),
                TypeDef::function(Vec::new(), Some(TypeId::new(0)), false),
            ),
        ],
    })
}

fn lowered_halfword_fixture(
    bits: u16,
    signed: bool,
) -> Result<LoweredByteFixture, String> {
    let module = halfword_return_module(bits, signed);
    validate_module(&module)
        .map_err(|error| format!("admit halfword: {error:?}"))?;
    let encoded = canonical_bytes(&module)
        .map_err(|error| format!("encode halfword typed IR: {error:?}"))?;
    let restored = canonical_module(&encoded)
        .map_err(|error| format!("restore halfword typed IR: {error:?}"))?;
    if restored != module {
        return Err(String::from("halfword typed IR drifted"));
    }
    let projection = project_typed_ir(&restored)?;
    let target = lower_typed_ir(&projection)
        .map_err(|error| format!("lower halfword: {error:?}"))?;
    assert_program_provenance(&restored, &target)?;
    Ok((target, projection))
}

fn halfword_expected_operations(
    bits: u16,
    signed: bool,
) -> Vec<TernaryOperation> {
    let scalar = ternary_lowering::TernaryU16Scalar::from_bits(bits);
    let source_span = output_span(fixture_span(0, 1));
    let return_span = output_span(fixture_span(1, 2));
    if signed {
        vec![
            TernaryOperation::MaterializeI16 {
                result: 0,
                scalar,
                span: source_span,
            },
            TernaryOperation::ReturnI16 {
                value: 0,
                span: return_span,
            },
        ]
    } else {
        vec![
            TernaryOperation::MaterializeU16 {
                result: 0,
                scalar,
                span: source_span,
            },
            TernaryOperation::ReturnU16 {
                value: 0,
                span: return_span,
            },
        ]
    }
}

fn assert_halfword_checkpoint(
    bits: u16,
    signed: bool,
    target: &ternary_lowering::TernaryProgram,
) -> Result<Vec<u8>, String> {
    let expected = halfword_expected_operations(bits, signed);
    let Some(function) = target.functions.first() else {
        return Err(String::from("halfword target function absent"));
    };
    if function.operations != expected {
        return Err(String::from("halfword SSA or source spans drifted"));
    }
    let wire = canonical_ternary_bytes(target)
        .map_err(|error| format!("encode halfword checkpoint: {error:?}"))?;
    let material_tag = if signed {
        61u8
    } else {
        62
    };
    let return_tag = if signed {
        63u8
    } else {
        64
    };
    if !wire
        .windows(5)
        .any(|part| part == [material_tag, 0, 0, 0, 0])
        || wire.get(wire.len().saturating_sub(29)) != Some(&return_tag)
        || canonical_ternary_program(&wire) != Ok(target.clone())
    {
        return Err(String::from("halfword target wire drifted"));
    }
    Ok(wire)
}

#[test]
fn halfword_scalar_covers_all_65536_patterns() -> Result<(), String> {
    for bits in u16::MIN..=u16::MAX {
        let scalar = ternary_lowering::TernaryU16Scalar::from_bits(bits);
        if scalar.bits() != bits || scalar.trits().iter().any(|trit| *trit > 2)
        {
            return Err(format!("16-bit scalar lost pattern {bits:#06x}"));
        }
    }
    Ok(())
}

#[test]
fn halfword_checkpoint_roundtrips_every_lower_byte_pattern()
-> Result<(), String> {
    for low in u8::MIN..=u8::MAX {
        for high in [0u16, 0x7f00, 0x8000, 0xff00] {
            for signed in [true, false] {
                let bits = high | u16::from(low);
                let (target, _) = lowered_halfword_fixture(bits, signed)?;
                let _wire = assert_halfword_checkpoint(bits, signed, &target)?;
            }
        }
    }
    Ok(())
}

fn halfword_record_offsets(
    wire: &[u8],
    signed: bool,
) -> Result<HalfwordRecordOffsets, String> {
    let tag = if signed {
        61u8
    } else {
        62
    };
    let materialize = wire
        .windows(5)
        .position(|part| part == [tag, 0, 0, 0, 0])
        .ok_or_else(|| String::from("halfword scalar record absent"))?;
    let terminator = wire
        .len()
        .checked_sub(29)
        .ok_or_else(|| String::from("halfword return record absent"))?;
    Ok((materialize, terminator))
}

fn reject_halfword_wire_mutation(
    wire: &[u8],
    offset: usize,
    replacement: u8,
    expected: TernaryProgramCodecError,
) -> Result<(), String> {
    let mut forged = wire.to_vec();
    *forged
        .get_mut(offset)
        .ok_or_else(|| String::from("halfword byte offset absent"))? =
        replacement;
    if canonical_ternary_program(&forged) != Err(expected) {
        return Err(format!(
            "halfword wire field {offset}/{replacement} admitted"
        ));
    }
    Ok(())
}

fn reject_halfword_checkpoint(bits: u16, signed: bool) -> Result<(), String> {
    let (target, _) = lowered_halfword_fixture(bits, signed)?;
    let wire = assert_halfword_checkpoint(bits, signed, &target)?;
    let (materialize, terminator) = halfword_record_offsets(&wire, signed)?;
    let foreign_material = if signed {
        62u8
    } else {
        61
    };
    let foreign_return = if signed {
        64u8
    } else {
        63
    };
    let wrong_width = if signed {
        57u8
    } else {
        9
    };
    let invalid = TernaryProgramCodecError::Validation(
        TernaryProgramValidationError::SsaValue,
    );
    for (offset, replacement, failure) in [
        (materialize, foreign_material, invalid),
        (materialize.saturating_add(1), 1, invalid),
        (
            materialize.saturating_add(5),
            3,
            TernaryProgramCodecError::InvalidScalar,
        ),
        (
            materialize.saturating_add(15),
            2,
            TernaryProgramCodecError::InvalidScalar,
        ),
        (terminator, foreign_return, invalid),
        (terminator, wrong_width, invalid),
        (terminator, 84, TernaryProgramCodecError::UnknownTag),
        (wire.len().saturating_sub(1), 99, invalid),
    ] {
        reject_halfword_wire_mutation(&wire, offset, replacement, failure)?;
    }
    let mut truncated = wire;
    let _removed = truncated.pop();
    if canonical_ternary_program(&truncated)
        != Err(TernaryProgramCodecError::Truncated)
    {
        return Err(String::from("truncated halfword return admitted"));
    }
    Ok(())
}

#[test]
fn halfword_decoder_rejects_signedness_and_canonical_digit_forgery()
-> Result<(), String> {
    for bits in [0u16, 1, 0x7fff, 0x8000, 0x8001, u16::MAX] {
        for signed in [true, false] {
            reject_halfword_checkpoint(bits, signed)?;
        }
    }
    Ok(())
}

#[test]
fn halfword_projection_rejects_wrong_category_and_duplicate_ssa()
-> Result<(), String> {
    for signed in [true, false] {
        let (_, projection) = lowered_halfword_fixture(0x8000, signed)?;
        let mut retyped = projection.clone();
        let new_kind = if signed {
            InputScalarType::U16
        } else {
            InputScalarType::I16
        };
        retyped
            .functions
            .first_mut()
            .ok_or_else(|| String::from("halfword function absent"))?
            .return_kind = new_kind;
        if lower_typed_ir(&retyped)
            != Err(TernaryLoweringError::UnsupportedTerminator)
        {
            return Err(String::from("retyped halfword return admitted"));
        }
        let mut duplicate = projection.clone();
        let instructions = &mut duplicate
            .functions
            .first_mut()
            .and_then(|function| function.blocks.first_mut())
            .ok_or_else(|| String::from("halfword input block absent"))?
            .instructions;
        let constant = instructions
            .first()
            .cloned()
            .ok_or_else(|| String::from("halfword constant missing"))?;
        instructions.push(constant);
        if lower_typed_ir(&duplicate)
            != Err(TernaryLoweringError::InvalidProjection)
        {
            return Err(String::from("duplicate halfword SSA admitted"));
        }
    }
    Ok(())
}

#[test]
fn halfword_inspector_restores_both_signedness_kinds() -> Result<(), String> {
    for bits in [0u16, 0x7fff, 0x8000, u16::MAX] {
        for signed in [true, false] {
            let (target, projection) = lowered_halfword_fixture(bits, signed)?;
            let label = if signed {
                "signed-halfword-constant-return"
            } else {
                "unsigned-halfword-constant-return"
            };
            assert_boolean_inspector_convergence(label, &target, &projection)?;
        }
    }
    Ok(())
}

#[test]
fn halfword_crash_publication_preserves_committed_generation()
-> Result<(), String> {
    let previous = lowered_return_fixture()?;
    for bits in [0u16, 0x7fff, 0x8000, u16::MAX] {
        for signed in [true, false] {
            let (target, _) = lowered_halfword_fixture(bits, signed)?;
            assert_boolean_crash_generation(&previous, &target)?;
        }
    }
    Ok(())
}

#[test]
fn halfword_inspector_rejects_signedness_retags_and_unknown_tags()
-> Result<(), String> {
    for signed in [true, false] {
        let (target, _) = lowered_halfword_fixture(0x8000, signed)?;
        let from = if signed {
            61u8
        } else {
            62
        };
        let swapped = if signed {
            62u8
        } else {
            61
        };
        let label = if signed {
            "forged-signed-halfword"
        } else {
            "forged-unsigned-halfword"
        };
        assert_boolean_progress_tag_rejected(
            label,
            &target,
            (from, 0, swapped),
        )?;
        assert_boolean_progress_tag_rejected(
            "halfword-unknown-tag",
            &target,
            (from, 0, 84),
        )?;
    }
    Ok(())
}

#[test]
fn halfword_constant_return_roundtrips_sign_boundary_patterns()
-> Result<(), String> {
    for bits in [0u16, 1, 0x7fff, 0x8000, 0x8001, u16::MAX] {
        for signed in [true, false] {
            let (target, projection) = lowered_halfword_fixture(bits, signed)?;
            let kind = if signed {
                InputScalarType::I16
            } else {
                InputScalarType::U16
            };
            if projection
                .functions
                .first()
                .map(|function| function.return_kind)
                != Some(kind)
            {
                return Err(String::from("halfword return type drifted"));
            }
            let _wire = assert_halfword_checkpoint(bits, signed, &target)?;
        }
    }
    Ok(())
}

fn halfword_truth_instructions(bits: u16) -> Vec<LocatedInstruction> {
    vec![
        LocatedInstruction::new(
            Instruction::ConstantInteger {
                constant: IntegerConstant::new(16, bits.to_le_bytes().to_vec()),
                result: ValueId::new(0),
                type_id: TypeId::new(0),
            },
            fixture_span(0, 1),
        ),
        LocatedInstruction::new(
            Instruction::Cast {
                operation: CastOp::IntegerToBool,
                result: ValueId::new(1),
                type_id: TypeId::new(1),
                value: ValueId::new(0),
            },
            fixture_span(1, 2),
        ),
    ]
}

fn halfword_truth_module(bits: u16, signed: bool) -> Module {
    let kind = if signed {
        TypeDef::I16
    } else {
        TypeDef::U16
    };
    Module::new(ModuleSpec {
        abi_id: String::from("malbolge-c32-v1"),
        format_version: typed_ir::TYPED_IR_VERSION,
        functions: vec![Function::new(FunctionSpec {
            blocks: vec![BasicBlock::new(BasicBlockSpec {
                id: BlockId::new(0),
                instructions: halfword_truth_instructions(bits),
                phis: Vec::new(),
                span: fixture_span(0, 3),
                terminator: Terminator::Return {
                    value: Some(ValueId::new(1)),
                },
                terminator_span: fixture_span(2, 3),
            })],
            entry: BlockId::new(0),
            id: FunctionId::new(0),
            name: String::from("halfword_truth"),
            parameters: Vec::new(),
            signature: TypeId::new(2),
            span: fixture_span(0, 3),
        })],
        globals: Vec::new(),
        proof_obligations: Vec::new(),
        source_id: String::from("fixtures/halfword-truth.c"),
        source_sha256: [0x66; 32],
        target_profile: String::from("malbolge-2026"),
        types: vec![
            TypeEntry::new(TypeId::new(0), kind),
            TypeEntry::new(TypeId::new(1), TypeDef::Bool),
            TypeEntry::new(
                TypeId::new(2),
                TypeDef::function(Vec::new(), Some(TypeId::new(1)), false),
            ),
        ],
    })
}

fn lowered_halfword_truth_fixture(
    bits: u16,
    signed: bool,
) -> Result<LoweredByteFixture, String> {
    let module = halfword_truth_module(bits, signed);
    validate_module(&module)
        .map_err(|error| format!("admit halfword truth: {error:?}"))?;
    let encoded = canonical_bytes(&module)
        .map_err(|error| format!("encode halfword truth: {error:?}"))?;
    let restored = canonical_module(&encoded)
        .map_err(|error| format!("restore halfword truth: {error:?}"))?;
    if restored != module {
        return Err(String::from("halfword truth typed IR drifted"));
    }
    let projection = project_typed_ir(&restored)?;
    let target = lower_typed_ir(&projection)
        .map_err(|error| format!("lower halfword truth: {error:?}"))?;
    assert_program_provenance(&restored, &target)?;
    Ok((target, projection))
}

fn assert_halfword_truth_checkpoint(
    bits: u16,
    signed: bool,
    target: &ternary_lowering::TernaryProgram,
) -> Result<Vec<u8>, String> {
    let scalar = ternary_lowering::TernaryU16Scalar::from_bits(bits);
    let materialize = if signed {
        TernaryOperation::MaterializeI16 {
            result: 0,
            scalar,
            span: output_span(fixture_span(0, 1)),
        }
    } else {
        TernaryOperation::MaterializeU16 {
            result: 0,
            scalar,
            span: output_span(fixture_span(0, 1)),
        }
    };
    let truth = if signed {
        TernaryOperation::I16ToBool {
            result: 1,
            span: output_span(fixture_span(1, 2)),
            value: 0,
        }
    } else {
        TernaryOperation::U16ToBool {
            result: 1,
            span: output_span(fixture_span(1, 2)),
            value: 0,
        }
    };
    let expected = [materialize, truth, TernaryOperation::ReturnBool {
        span: output_span(fixture_span(2, 3)),
        value: 1,
    }];
    let Some(function) = target.functions.first() else {
        return Err(String::from("halfword truth function absent"));
    };
    if function.operations != expected {
        return Err(String::from("halfword Boolean SSA chain drifted"));
    }
    let wire = canonical_ternary_bytes(target)
        .map_err(|error| format!("encode halfword truth target: {error:?}"))?;
    let tag = if signed {
        65u8
    } else {
        66
    };
    if !wire.windows(5).any(|part| part == [tag, 1, 0, 0, 0])
        || canonical_ternary_program(&wire) != Ok(target.clone())
    {
        return Err(String::from("halfword truth checkpoint drifted"));
    }
    Ok(wire)
}

fn verify_halfword_truth_case(bits: u16, signed: bool) -> Result<(), String> {
    let (target, input) = lowered_halfword_truth_fixture(bits, signed)?;
    if input.functions.first().map(|function| function.return_kind)
        != Some(InputScalarType::Bool)
    {
        return Err(String::from("halfword truth return kind drifted"));
    }
    let _wire = assert_halfword_truth_checkpoint(bits, signed, &target)?;
    Ok(())
}

#[test]
fn typed_halfword_truth_covers_every_low_byte_with_sign_boundaries()
-> Result<(), String> {
    for low in u8::MIN..=u8::MAX {
        for high in [0u16, 0x7f00, 0x8000, 0xff00] {
            for signed in [true, false] {
                verify_halfword_truth_case(high | u16::from(low), signed)?;
            }
        }
    }
    Ok(())
}

fn reject_halfword_truth_checkpoint(
    bits: u16,
    signed: bool,
) -> Result<(), String> {
    let (target, _) = lowered_halfword_truth_fixture(bits, signed)?;
    let wire = assert_halfword_truth_checkpoint(bits, signed, &target)?;
    let tag = if signed {
        65u8
    } else {
        66
    };
    let offset = wire
        .windows(5)
        .position(|part| part == [tag, 1, 0, 0, 0])
        .ok_or_else(|| String::from("halfword truth record missing"))?;
    let swapped = if signed {
        66u8
    } else {
        65
    };
    let invalid = TernaryProgramCodecError::Validation(
        TernaryProgramValidationError::SsaValue,
    );
    for (displacement, replacement, expected) in [
        (0usize, swapped, invalid),
        (0, 45, invalid),
        (0, 84, TernaryProgramCodecError::UnknownTag),
        (1, 0, invalid),
        (29, 99, invalid),
    ] {
        let mut forged = wire.clone();
        *forged
            .get_mut(offset.saturating_add(displacement))
            .ok_or_else(|| String::from("halfword truth field missing"))? =
            replacement;
        if canonical_ternary_program(&forged) != Err(expected) {
            return Err(format!(
                "forged halfword truth +{displacement}/{replacement} admitted"
            ));
        }
    }
    let mut truncated = wire;
    let _ignored = truncated.pop();
    if canonical_ternary_program(&truncated)
        != Err(TernaryProgramCodecError::Truncated)
    {
        return Err(String::from(
            "incomplete halfword truth checkpoint admitted",
        ));
    }
    Ok(())
}

#[test]
fn halfword_truth_decoder_rejects_signedness_and_ssa_forgeries()
-> Result<(), String> {
    for bits in [0u16, 1, 0x7fff, 0x8000, u16::MAX] {
        for signed in [true, false] {
            reject_halfword_truth_checkpoint(bits, signed)?;
        }
    }
    Ok(())
}

fn reject_halfword_truth_projection(
    signed: bool,
    variation: u8,
) -> Result<(), String> {
    let (_, mut projection) = lowered_halfword_truth_fixture(0x8000, signed)?;
    let function = projection
        .functions
        .first_mut()
        .ok_or_else(|| String::from("halfword truth function absent"))?;
    let block = function
        .blocks
        .first_mut()
        .ok_or_else(|| String::from("halfword truth block absent"))?;
    let Some(InputInstruction::IntegerToBool {
        result, type_kind, value, ..
    }) = block.instructions.get_mut(1)
    else {
        return Err(String::from("halfword truth cast absent"));
    };
    match variation {
        0 => *type_kind = InputScalarType::I32,
        1 => *value = 99,
        2 => *result = 0,
        _ => return Err(String::from("invalid truth projection case")),
    }
    let expected = if variation == 2 {
        TernaryLoweringError::InvalidProjection
    } else {
        TernaryLoweringError::UnsupportedInstruction
    };
    if lower_typed_ir(&projection) != Err(expected) {
        return Err(format!("halfword truth projection {variation} admitted"));
    }
    Ok(())
}

#[test]
fn halfword_truth_projection_rejects_wrong_type_or_undefined_ssa()
-> Result<(), String> {
    for signed in [true, false] {
        for variation in 0u8..3 {
            reject_halfword_truth_projection(signed, variation)?;
        }
    }
    Ok(())
}

#[test]
fn halfword_truth_inspector_and_crash_restore_exact_ssa() -> Result<(), String>
{
    let previous = lowered_return_fixture()?;
    for bits in [0u16, 1, 0x7fff, 0x8000, u16::MAX] {
        for signed in [true, false] {
            let (target, projection) =
                lowered_halfword_truth_fixture(bits, signed)?;
            let label = if signed {
                "signed-halfword-nonzero"
            } else {
                "unsigned-halfword-nonzero"
            };
            assert_boolean_inspector_convergence(label, &target, &projection)?;
            assert_boolean_crash_generation(&previous, &target)?;
        }
    }
    Ok(())
}

#[test]
fn halfword_truth_inspector_rejects_retagged_signedness() -> Result<(), String>
{
    for signed in [true, false] {
        let (target, _) = lowered_halfword_truth_fixture(0x8000, signed)?;
        let source_tag = if signed {
            65u8
        } else {
            66
        };
        let swapped = if signed {
            66u8
        } else {
            65
        };
        assert_boolean_progress_tag_rejected(
            "halfword-truth-cross-kind",
            &target,
            (source_tag, 1, swapped),
        )?;
        assert_boolean_progress_tag_rejected(
            "halfword-truth-unknown",
            &target,
            (source_tag, 1, 84),
        )?;
    }
    Ok(())
}

fn bool_to_halfword_instructions(
    bit: u8,
    round_trip: bool,
) -> Vec<LocatedInstruction> {
    let mut instructions = vec![
        LocatedInstruction::new(
            Instruction::ConstantInteger {
                constant: IntegerConstant::new(1, vec![bit]),
                result: ValueId::new(0),
                type_id: TypeId::new(0),
            },
            fixture_span(0, 1),
        ),
        LocatedInstruction::new(
            Instruction::Cast {
                operation: CastOp::BoolToSigned,
                result: ValueId::new(1),
                type_id: TypeId::new(1),
                value: ValueId::new(0),
            },
            fixture_span(1, 2),
        ),
    ];
    if round_trip {
        instructions.push(LocatedInstruction::new(
            Instruction::Cast {
                operation: CastOp::IntegerToBool,
                result: ValueId::new(2),
                type_id: TypeId::new(0),
                value: ValueId::new(1),
            },
            fixture_span(2, 3),
        ));
    }
    instructions
}

fn bool_to_halfword_module(bit: u8, round_trip: bool) -> Module {
    let end = if round_trip {
        4
    } else {
        3
    };
    let return_value = if round_trip {
        2
    } else {
        1
    };
    let signature = if round_trip {
        3
    } else {
        2
    };
    Module::new(ModuleSpec {
        abi_id: String::from("malbolge-c32-v1"),
        format_version: typed_ir::TYPED_IR_VERSION,
        functions: vec![Function::new(FunctionSpec {
            blocks: vec![BasicBlock::new(BasicBlockSpec {
                id: BlockId::new(0),
                instructions: bool_to_halfword_instructions(bit, round_trip),
                phis: Vec::new(),
                span: fixture_span(0, end),
                terminator: Terminator::Return {
                    value: Some(ValueId::new(return_value)),
                },
                terminator_span: fixture_span(end.saturating_sub(1), end),
            })],
            entry: BlockId::new(0),
            id: FunctionId::new(0),
            name: String::from("bool_to_halfword"),
            parameters: Vec::new(),
            signature: TypeId::new(signature),
            span: fixture_span(0, end),
        })],
        globals: Vec::new(),
        proof_obligations: Vec::new(),
        source_id: String::from("fixtures/bool-to-halfword.c"),
        source_sha256: [0x67; 32],
        target_profile: String::from("malbolge-2026"),
        types: vec![
            TypeEntry::new(TypeId::new(0), TypeDef::Bool),
            TypeEntry::new(TypeId::new(1), TypeDef::I16),
            TypeEntry::new(
                TypeId::new(2),
                TypeDef::function(Vec::new(), Some(TypeId::new(1)), false),
            ),
            TypeEntry::new(
                TypeId::new(3),
                TypeDef::function(Vec::new(), Some(TypeId::new(0)), false),
            ),
        ],
    })
}

fn lowered_bool_to_halfword_fixture(
    bit: u8,
    round_trip: bool,
) -> Result<LoweredByteFixture, String> {
    let module = bool_to_halfword_module(bit, round_trip);
    validate_module(&module)
        .map_err(|error| format!("admit bool to i16: {error:?}"))?;
    let encoded = canonical_bytes(&module)
        .map_err(|error| format!("encode bool to i16: {error:?}"))?;
    let restored = canonical_module(&encoded)
        .map_err(|error| format!("restore bool to i16: {error:?}"))?;
    if restored != module {
        return Err(String::from("bool to i16 typed IR drifted"));
    }
    let projection = project_typed_ir(&restored)?;
    let target = lower_typed_ir(&projection)
        .map_err(|error| format!("lower bool to i16: {error:?}"))?;
    assert_program_provenance(&restored, &target)?;
    Ok((target, projection))
}

fn expected_bool_to_halfword_operations(
    bit: u8,
    round_trip: bool,
) -> Vec<TernaryOperation> {
    let mut expected = vec![
        TernaryOperation::MaterializeBool {
            result: 0,
            value: bit == 1,
            span: output_span(fixture_span(0, 1)),
        },
        TernaryOperation::BoolToI16 {
            result: 1,
            span: output_span(fixture_span(1, 2)),
            value: 0,
        },
    ];
    if round_trip {
        expected.push(TernaryOperation::I16ToBool {
            result: 2,
            span: output_span(fixture_span(2, 3)),
            value: 1,
        });
        expected.push(TernaryOperation::ReturnBool {
            span: output_span(fixture_span(3, 4)),
            value: 2,
        });
    } else {
        expected.push(TernaryOperation::ReturnI16 {
            span: output_span(fixture_span(2, 3)),
            value: 1,
        });
    }
    expected
}

fn assert_bool_to_halfword_checkpoint(
    bit: u8,
    round_trip: bool,
    target: &ternary_lowering::TernaryProgram,
) -> Result<Vec<u8>, String> {
    let expected = expected_bool_to_halfword_operations(bit, round_trip);
    if target
        .functions
        .first()
        .map(|function| function.operations.as_slice())
        != Some(expected.as_slice())
    {
        return Err(String::from("bool to i16 SSA chain drifted"));
    }
    let wire = canonical_ternary_bytes(target)
        .map_err(|error| format!("encode bool to i16 target: {error:?}"))?;
    if !wire.windows(5).any(|part| part == [67, 1, 0, 0, 0])
        || canonical_ternary_program(&wire) != Ok(target.clone())
    {
        return Err(String::from("bool to i16 checkpoint drifted"));
    }
    Ok(wire)
}

#[test]
fn typed_boolean_to_halfword_preserves_distinct_ssa_and_roundtrip()
-> Result<(), String> {
    for bit in [0u8, 1] {
        for round_trip in [false, true] {
            let (target, projection) =
                lowered_bool_to_halfword_fixture(bit, round_trip)?;
            let expected_kind = if round_trip {
                InputScalarType::Bool
            } else {
                InputScalarType::I16
            };
            if projection
                .functions
                .first()
                .map(|function| function.return_kind)
                != Some(expected_kind)
            {
                return Err(String::from("bool to i16 return kind drifted"));
            }
            let _wire =
                assert_bool_to_halfword_checkpoint(bit, round_trip, &target)?;
        }
    }
    Ok(())
}

fn reject_bool_to_halfword_checkpoint(
    bit: u8,
    round_trip: bool,
) -> Result<(), String> {
    let (target, _) = lowered_bool_to_halfword_fixture(bit, round_trip)?;
    let wire = assert_bool_to_halfword_checkpoint(bit, round_trip, &target)?;
    let offset = wire
        .windows(5)
        .position(|part| part == [67, 1, 0, 0, 0])
        .ok_or_else(|| String::from("bool to i16 cast absent"))?;
    let invalid = TernaryProgramCodecError::Validation(
        TernaryProgramValidationError::SsaValue,
    );
    for (displacement, replacement, expected) in [
        (0usize, 60u8, invalid),
        (0, 65, invalid),
        (0, 84, TernaryProgramCodecError::UnknownTag),
        (1, 0, invalid),
        (29, 99, invalid),
    ] {
        let mut forged = wire.clone();
        *forged
            .get_mut(offset.saturating_add(displacement))
            .ok_or_else(|| String::from("bool to i16 byte offset absent"))? =
            replacement;
        if canonical_ternary_program(&forged) != Err(expected) {
            return Err(format!(
                "bool to i16 {displacement}/{replacement} admitted"
            ));
        }
    }
    Ok(())
}

#[test]
fn bool_to_halfword_decoder_rejects_wrong_type_and_ssa_identity()
-> Result<(), String> {
    for bit in [0u8, 1] {
        for round_trip in [false, true] {
            reject_bool_to_halfword_checkpoint(bit, round_trip)?;
        }
    }
    Ok(())
}

fn reject_bool_to_halfword_projection(
    bit: u8,
    variation: u8,
) -> Result<(), String> {
    let (_, mut projection) = lowered_bool_to_halfword_fixture(bit, false)?;
    let cast = projection
        .functions
        .first_mut()
        .and_then(|function| function.blocks.first_mut())
        .and_then(|block| block.instructions.get_mut(1))
        .ok_or_else(|| String::from("bool to i16 projected cast absent"))?;
    let InputInstruction::BoolToSigned {
        result, type_kind, value, ..
    } = cast
    else {
        return Err(String::from("bool to i16 projection changed shape"));
    };
    match variation {
        0 => *type_kind = InputScalarType::U16,
        1 => *value = 99,
        2 => *result = 0,
        _ => return Err(String::from("invalid bool to i16 forgery")),
    }
    let error = if variation == 2 {
        TernaryLoweringError::InvalidProjection
    } else {
        TernaryLoweringError::UnsupportedInstruction
    };
    if lower_typed_ir(&projection) != Err(error) {
        return Err(format!("bool to i16 projection {variation} admitted"));
    }
    Ok(())
}

#[test]
fn bool_to_halfword_projection_rejects_forged_kinds_and_ssa()
-> Result<(), String> {
    for bit in [0u8, 1] {
        for variation in 0u8..3 {
            reject_bool_to_halfword_projection(bit, variation)?;
        }
    }
    Ok(())
}

#[test]
fn bool_to_halfword_inspector_and_crash_recovery() -> Result<(), String> {
    let previous = lowered_return_fixture()?;
    for bit in [0u8, 1] {
        for round_trip in [false, true] {
            let (target, projection) =
                lowered_bool_to_halfword_fixture(bit, round_trip)?;
            let label = if round_trip {
                "bool-to-i16-back-to-bool"
            } else {
                "bool-to-i16-direct-return"
            };
            assert_boolean_inspector_convergence(label, &target, &projection)?;
            assert_boolean_crash_generation(&previous, &target)?;
        }
    }
    Ok(())
}

#[test]
fn bool_to_halfword_inspector_rejects_wrong_width_and_future_tag()
-> Result<(), String> {
    for bit in [0u8, 1] {
        let (target, _) = lowered_bool_to_halfword_fixture(bit, false)?;
        assert_boolean_progress_tag_rejected(
            "bool-to-i16-forged-byte",
            &target,
            (67, 1, 60),
        )?;
        assert_boolean_progress_tag_rejected(
            "bool-to-i16-future",
            &target,
            (67, 1, 84),
        )?;
    }
    Ok(())
}

fn halfword_widen_instructions(
    bits: u16,
    signed: bool,
) -> Vec<LocatedInstruction> {
    let operation = if signed {
        CastOp::SignExtend
    } else {
        CastOp::ZeroExtend
    };
    vec![
        LocatedInstruction::new(
            Instruction::ConstantInteger {
                constant: IntegerConstant::new(16, bits.to_le_bytes().to_vec()),
                result: ValueId::new(0),
                type_id: TypeId::new(0),
            },
            fixture_span(0, 1),
        ),
        LocatedInstruction::new(
            Instruction::Cast {
                operation,
                result: ValueId::new(1),
                type_id: TypeId::new(1),
                value: ValueId::new(0),
            },
            fixture_span(1, 2),
        ),
    ]
}

fn halfword_widen_module(bits: u16, signed: bool) -> Module {
    let narrow = if signed {
        TypeDef::I16
    } else {
        TypeDef::U16
    };
    let word = if signed {
        TypeDef::I32
    } else {
        TypeDef::U32
    };
    Module::new(ModuleSpec {
        abi_id: String::from("malbolge-c32-v1"),
        format_version: typed_ir::TYPED_IR_VERSION,
        functions: vec![Function::new(FunctionSpec {
            blocks: vec![BasicBlock::new(BasicBlockSpec {
                id: BlockId::new(0),
                instructions: halfword_widen_instructions(bits, signed),
                phis: Vec::new(),
                span: fixture_span(0, 3),
                terminator: Terminator::Return {
                    value: Some(ValueId::new(1)),
                },
                terminator_span: fixture_span(2, 3),
            })],
            entry: BlockId::new(0),
            id: FunctionId::new(0),
            name: String::from("halfword_widen"),
            parameters: Vec::new(),
            signature: TypeId::new(2),
            span: fixture_span(0, 3),
        })],
        globals: Vec::new(),
        proof_obligations: Vec::new(),
        source_id: String::from("fixtures/halfword-widen.c"),
        source_sha256: [0x68; 32],
        target_profile: String::from("malbolge-2026"),
        types: vec![
            TypeEntry::new(TypeId::new(0), narrow),
            TypeEntry::new(TypeId::new(1), word),
            TypeEntry::new(
                TypeId::new(2),
                TypeDef::function(Vec::new(), Some(TypeId::new(1)), false),
            ),
        ],
    })
}

fn lowered_halfword_widen_fixture(
    bits: u16,
    signed: bool,
) -> Result<LoweredByteFixture, String> {
    let module = halfword_widen_module(bits, signed);
    validate_module(&module)
        .map_err(|error| format!("admit 16-bit widening: {error:?}"))?;
    let encoded = canonical_bytes(&module)
        .map_err(|error| format!("encode 16-bit widening: {error:?}"))?;
    let restored = canonical_module(&encoded)
        .map_err(|error| format!("restore 16-bit widening: {error:?}"))?;
    if restored != module {
        return Err(String::from("16-bit widening typed IR drifted"));
    }
    let projection = project_typed_ir(&restored)?;
    let target = lower_typed_ir(&projection)
        .map_err(|error| format!("lower 16-bit widening: {error:?}"))?;
    assert_program_provenance(&restored, &target)?;
    Ok((target, projection))
}

fn expected_halfword_widen_operations(
    bits: u16,
    signed: bool,
) -> Vec<TernaryOperation> {
    let scalar = ternary_lowering::TernaryU16Scalar::from_bits(bits);
    let materialize = if signed {
        TernaryOperation::MaterializeI16 {
            result: 0,
            scalar,
            span: output_span(fixture_span(0, 1)),
        }
    } else {
        TernaryOperation::MaterializeU16 {
            result: 0,
            scalar,
            span: output_span(fixture_span(0, 1)),
        }
    };
    let widen = if signed {
        TernaryOperation::SignExtendI16ToI32 {
            result: 1,
            span: output_span(fixture_span(1, 2)),
            value: 0,
        }
    } else {
        TernaryOperation::ZeroExtendU16ToU32 {
            result: 1,
            span: output_span(fixture_span(1, 2)),
            value: 0,
        }
    };
    let done = if signed {
        TernaryOperation::Return {
            span: output_span(fixture_span(2, 3)),
            value: 1,
        }
    } else {
        TernaryOperation::ReturnU32 {
            span: output_span(fixture_span(2, 3)),
            value: 1,
        }
    };
    vec![materialize, widen, done]
}

fn assert_halfword_widen_checkpoint(
    bits: u16,
    signed: bool,
    target: &ternary_lowering::TernaryProgram,
) -> Result<Vec<u8>, String> {
    let expected = expected_halfword_widen_operations(bits, signed);
    if target
        .functions
        .first()
        .map(|function| function.operations.as_slice())
        != Some(expected.as_slice())
    {
        return Err(String::from("halfword widen SSA or return drifted"));
    }
    let wire = canonical_ternary_bytes(target).map_err(|error| {
        format!("encode halfword widen checkpoint: {error:?}")
    })?;
    let tag = if signed {
        68u8
    } else {
        69
    };
    if !wire.windows(5).any(|part| part == [tag, 1, 0, 0, 0])
        || canonical_ternary_program(&wire) != Ok(target.clone())
    {
        return Err(String::from("halfword widen wire record drifted"));
    }
    Ok(wire)
}

fn verify_halfword_widen_case(bits: u16, signed: bool) -> Result<(), String> {
    let (target, input) = lowered_halfword_widen_fixture(bits, signed)?;
    let kind = if signed {
        InputScalarType::I32
    } else {
        InputScalarType::U32
    };
    if input.functions.first().map(|function| function.return_kind)
        != Some(kind)
    {
        return Err(String::from("halfword widen target return type drifted"));
    }
    let _wire = assert_halfword_widen_checkpoint(bits, signed, &target)?;
    Ok(())
}

#[test]
fn typed_halfword_widening_preserves_sign_boundary_and_every_lower_byte()
-> Result<(), String> {
    for low in u8::MIN..=u8::MAX {
        for high in [0u16, 0x7f00, 0x8000, 0xff00] {
            for signed in [true, false] {
                verify_halfword_widen_case(high | u16::from(low), signed)?;
            }
        }
    }
    Ok(())
}

fn reject_halfword_widen_checkpoint(
    bits: u16,
    signed: bool,
) -> Result<(), String> {
    let (target, _) = lowered_halfword_widen_fixture(bits, signed)?;
    let wire = assert_halfword_widen_checkpoint(bits, signed, &target)?;
    let tag = if signed {
        68u8
    } else {
        69
    };
    let wrong_sign = if signed {
        69u8
    } else {
        68
    };
    let wrong_width = if signed {
        51u8
    } else {
        16
    };
    let index = wire
        .windows(5)
        .position(|part| part == [tag, 1, 0, 0, 0])
        .ok_or_else(|| String::from("halfword widen tag absent"))?;
    let invalid = TernaryProgramCodecError::Validation(
        TernaryProgramValidationError::SsaValue,
    );
    for (offset, replacement, expected) in [
        (0usize, wrong_sign, invalid),
        (0, wrong_width, invalid),
        (0, 84, TernaryProgramCodecError::UnknownTag),
        (1, 0, invalid),
        (29, 99, invalid),
    ] {
        let mut forged = wire.clone();
        *forged
            .get_mut(index.saturating_add(offset))
            .ok_or_else(|| {
                String::from("halfword widen wire field missing")
            })? = replacement;
        if canonical_ternary_program(&forged) != Err(expected) {
            return Err(format!(
                "halfword widen forged {offset}/{replacement} admitted"
            ));
        }
    }
    let mut truncated = wire;
    let _ignored = truncated.pop();
    if canonical_ternary_program(&truncated)
        != Err(TernaryProgramCodecError::Truncated)
    {
        return Err(String::from("halfword widen truncated record admitted"));
    }
    Ok(())
}

#[test]
fn halfword_widen_decoder_rejects_signedness_width_and_ssa_forgery()
-> Result<(), String> {
    for bits in [0u16, 1, 0x7fff, 0x8000, 0x8001, u16::MAX] {
        for signed in [true, false] {
            reject_halfword_widen_checkpoint(bits, signed)?;
        }
    }
    Ok(())
}

fn reject_halfword_widen_projection(
    signed: bool,
    variation: u8,
) -> Result<(), String> {
    let (_, mut projection) = lowered_halfword_widen_fixture(0x8000, signed)?;
    let cast = projection
        .functions
        .first_mut()
        .and_then(|function| function.blocks.first_mut())
        .and_then(|block| block.instructions.get_mut(1))
        .ok_or_else(|| String::from("halfword widen projected cast absent"))?;
    let (InputInstruction::SignExtendI8ToI32 {
        result,
        type_kind: kind,
        value,
        ..
    }
    | InputInstruction::ZeroExtendInteger {
        result,
        type_kind: kind,
        value,
        ..
    }) = cast
    else {
        return Err(String::from("halfword widening projection changed"));
    };
    match variation {
        0 => {
            *kind = if signed {
                InputScalarType::U32
            } else {
                InputScalarType::I32
            }
        },
        1 => *value = 99,
        2 => *result = 0,
        _ => return Err(String::from("invalid halfword widen forgery")),
    }
    let error = if variation == 2 {
        TernaryLoweringError::InvalidProjection
    } else {
        TernaryLoweringError::UnsupportedInstruction
    };
    if lower_typed_ir(&projection) != Err(error) {
        return Err(format!(
            "halfword widening projection {variation} admitted"
        ));
    }
    Ok(())
}

#[test]
fn halfword_widen_projection_rejects_wrong_destination_and_ssa()
-> Result<(), String> {
    for signed in [true, false] {
        for variation in 0u8..3 {
            reject_halfword_widen_projection(signed, variation)?;
        }
    }
    Ok(())
}

#[test]
fn halfword_widen_inspector_recovers_signed_and_unsigned_chains()
-> Result<(), String> {
    for bits in [0u16, 1, 0x7fff, 0x8000, u16::MAX] {
        for signed in [true, false] {
            let (target, input) = lowered_halfword_widen_fixture(bits, signed)?;
            let label = if signed {
                "signed-halfword-to-word"
            } else {
                "unsigned-halfword-to-word"
            };
            assert_boolean_inspector_convergence(label, &target, &input)?;
        }
    }
    Ok(())
}

#[test]
fn halfword_widen_crash_boundaries_preserve_committed_generation()
-> Result<(), String> {
    let previous = lowered_return_fixture()?;
    for bits in [0u16, 0x7fff, 0x8000, u16::MAX] {
        for signed in [true, false] {
            let (target, _) = lowered_halfword_widen_fixture(bits, signed)?;
            assert_boolean_crash_generation(&previous, &target)?;
        }
    }
    Ok(())
}

#[test]
fn halfword_widen_inspector_rejects_retagged_or_unknown_cast()
-> Result<(), String> {
    for signed in [true, false] {
        let (target, _) = lowered_halfword_widen_fixture(0x8000, signed)?;
        let tag = if signed {
            68u8
        } else {
            69
        };
        let wrong = if signed {
            69u8
        } else {
            68
        };
        assert_boolean_progress_tag_rejected(
            "halfword-widen-cross-kind",
            &target,
            (tag, 1, wrong),
        )?;
        assert_boolean_progress_tag_rejected(
            "halfword-widen-future",
            &target,
            (tag, 1, 84),
        )?;
    }
    Ok(())
}

fn halfword_bitcast_instructions(bits: u16) -> Vec<LocatedInstruction> {
    vec![
        LocatedInstruction::new(
            Instruction::ConstantInteger {
                constant: IntegerConstant::new(16, bits.to_le_bytes().to_vec()),
                result: ValueId::new(0),
                type_id: TypeId::new(0),
            },
            fixture_span(0, 1),
        ),
        LocatedInstruction::new(
            Instruction::Cast {
                operation: CastOp::IntegerBitcast,
                result: ValueId::new(1),
                type_id: TypeId::new(1),
                value: ValueId::new(0),
            },
            fixture_span(1, 2),
        ),
    ]
}

fn halfword_bitcast_module(
    bits: u16,
    signed_source: bool,
    signed_target: bool,
) -> Module {
    let origin = if signed_source {
        TypeDef::I16
    } else {
        TypeDef::U16
    };
    let destination = if signed_target {
        TypeDef::I16
    } else {
        TypeDef::U16
    };
    Module::new(ModuleSpec {
        abi_id: String::from("malbolge-c32-v1"),
        format_version: typed_ir::TYPED_IR_VERSION,
        functions: vec![Function::new(FunctionSpec {
            blocks: vec![BasicBlock::new(BasicBlockSpec {
                id: BlockId::new(0),
                instructions: halfword_bitcast_instructions(bits),
                phis: Vec::new(),
                span: fixture_span(0, 3),
                terminator: Terminator::Return {
                    value: Some(ValueId::new(1)),
                },
                terminator_span: fixture_span(2, 3),
            })],
            entry: BlockId::new(0),
            id: FunctionId::new(0),
            name: String::from("halfword_bitcast"),
            parameters: Vec::new(),
            signature: TypeId::new(2),
            span: fixture_span(0, 3),
        })],
        globals: Vec::new(),
        proof_obligations: Vec::new(),
        source_id: String::from("fixtures/halfword-bitcast.c"),
        source_sha256: [0x70; 32],
        target_profile: String::from("malbolge-2026"),
        types: vec![
            TypeEntry::new(TypeId::new(0), origin),
            TypeEntry::new(TypeId::new(1), destination),
            TypeEntry::new(
                TypeId::new(2),
                TypeDef::function(Vec::new(), Some(TypeId::new(1)), false),
            ),
        ],
    })
}

fn lowered_halfword_bitcast_fixture(
    bits: u16,
    signed_source: bool,
    signed_target: bool,
) -> Result<LoweredByteFixture, String> {
    let module = halfword_bitcast_module(bits, signed_source, signed_target);
    validate_module(&module)
        .map_err(|error| format!("admit halfword bitcast: {error:?}"))?;
    let encoded = canonical_bytes(&module)
        .map_err(|error| format!("encode halfword bitcast: {error:?}"))?;
    let restored = canonical_module(&encoded)
        .map_err(|error| format!("restore halfword bitcast: {error:?}"))?;
    if restored != module {
        return Err(String::from("halfword bitcast typed IR drifted"));
    }
    let projection = project_typed_ir(&restored)?;
    let target = lower_typed_ir(&projection)
        .map_err(|error| format!("lower halfword bitcast: {error:?}"))?;
    assert_program_provenance(&restored, &target)?;
    Ok((target, projection))
}

fn expected_halfword_bitcast_operations(
    bits: u16,
    signed_source: bool,
    signed_target: bool,
) -> Vec<TernaryOperation> {
    let scalar = ternary_lowering::TernaryU16Scalar::from_bits(bits);
    let source_span = output_span(fixture_span(0, 1));
    let cast_span = output_span(fixture_span(1, 2));
    let ret_span = output_span(fixture_span(2, 3));
    let first = if signed_source {
        TernaryOperation::MaterializeI16 {
            result: 0,
            scalar,
            span: source_span,
        }
    } else {
        TernaryOperation::MaterializeU16 {
            result: 0,
            scalar,
            span: source_span,
        }
    };
    let cast = match (signed_source, signed_target) {
        (true, true) => TernaryOperation::BitcastI16ToI16 {
            result: 1,
            span: cast_span,
            value: 0,
        },
        (true, false) => TernaryOperation::BitcastI16ToU16 {
            result: 1,
            span: cast_span,
            value: 0,
        },
        (false, true) => TernaryOperation::BitcastU16ToI16 {
            result: 1,
            span: cast_span,
            value: 0,
        },
        (false, false) => TernaryOperation::BitcastU16ToU16 {
            result: 1,
            span: cast_span,
            value: 0,
        },
    };
    let ret = if signed_target {
        TernaryOperation::ReturnI16 { span: ret_span, value: 1 }
    } else {
        TernaryOperation::ReturnU16 { span: ret_span, value: 1 }
    };
    vec![first, cast, ret]
}

const fn halfword_bitcast_tag(signed_source: bool, signed_target: bool) -> u8 {
    match (signed_source, signed_target) {
        (true, true) => 70,
        (true, false) => 71,
        (false, true) => 72,
        (false, false) => 73,
    }
}

fn assert_halfword_bitcast_checkpoint(
    bits: u16,
    signed_source: bool,
    signed_target: bool,
    target: &ternary_lowering::TernaryProgram,
) -> Result<Vec<u8>, String> {
    let expected = expected_halfword_bitcast_operations(
        bits,
        signed_source,
        signed_target,
    );
    if target
        .functions
        .first()
        .map(|function| function.operations.as_slice())
        != Some(expected.as_slice())
    {
        return Err(String::from(
            "halfword bitcast typed SSA or return drifted",
        ));
    }
    let wire = canonical_ternary_bytes(target).map_err(|error| {
        format!("encode halfword bitcast checkpoint: {error:?}")
    })?;
    let tag = halfword_bitcast_tag(signed_source, signed_target);
    if !wire.windows(5).any(|part| part == [tag, 1, 0, 0, 0])
        || canonical_ternary_program(&wire) != Ok(target.clone())
    {
        return Err(String::from("halfword bitcast checkpoint drifted"));
    }
    Ok(wire)
}

fn verify_halfword_bitcast_case(
    bits: u16,
    signed_source: bool,
    signed_target: bool,
) -> Result<(), String> {
    let (target, input) =
        lowered_halfword_bitcast_fixture(bits, signed_source, signed_target)?;
    let kind = if signed_target {
        InputScalarType::I16
    } else {
        InputScalarType::U16
    };
    if input.functions.first().map(|function| function.return_kind)
        != Some(kind)
    {
        return Err(String::from("halfword bitcast return kind drifted"));
    }
    let _wire = assert_halfword_bitcast_checkpoint(
        bits,
        signed_source,
        signed_target,
        &target,
    )?;
    Ok(())
}

fn verify_halfword_bitcast_patterns(bits: u16) -> Result<(), String> {
    for signed_source in [true, false] {
        for signed_target in [true, false] {
            verify_halfword_bitcast_case(bits, signed_source, signed_target)?;
        }
    }
    Ok(())
}

#[test]
fn halfword_bitcasts_preserve_all_signedness_pairs_and_lower_bytes()
-> Result<(), String> {
    for low in u8::MIN..=u8::MAX {
        for high in [0u16, 0x7f00, 0x8000, 0xff00] {
            verify_halfword_bitcast_patterns(high | u16::from(low))?;
        }
    }
    Ok(())
}

fn reject_halfword_bitcast_checkpoint(
    bits: u16,
    signed_source: bool,
    signed_target: bool,
) -> Result<(), String> {
    let (target, _) =
        lowered_halfword_bitcast_fixture(bits, signed_source, signed_target)?;
    let wire = assert_halfword_bitcast_checkpoint(
        bits,
        signed_source,
        signed_target,
        &target,
    )?;
    let tag = halfword_bitcast_tag(signed_source, signed_target);
    let wrong_source = halfword_bitcast_tag(!signed_source, signed_target);
    let wrong_target = halfword_bitcast_tag(signed_source, !signed_target);
    let offset = wire
        .windows(5)
        .position(|part| part == [tag, 1, 0, 0, 0])
        .ok_or_else(|| String::from("halfword bitcast tag absent"))?;
    let invalid = TernaryProgramCodecError::Validation(
        TernaryProgramValidationError::SsaValue,
    );
    for (displacement, replacement, expected) in [
        (0usize, wrong_source, invalid),
        (0, wrong_target, invalid),
        (0, 55, invalid),
        (0, 84, TernaryProgramCodecError::UnknownTag),
        (1, 0, invalid),
        (29, 99, invalid),
    ] {
        let mut forged = wire.clone();
        *forged
            .get_mut(offset.saturating_add(displacement))
            .ok_or_else(|| {
                String::from("halfword bitcast wire field absent")
            })? = replacement;
        if canonical_ternary_program(&forged) != Err(expected) {
            return Err(format!(
                "halfword bitcast forged {displacement}/{replacement} admitted"
            ));
        }
    }
    let mut truncated = wire;
    let _ignored = truncated.pop();
    if canonical_ternary_program(&truncated)
        != Err(TernaryProgramCodecError::Truncated)
    {
        return Err(String::from("halfword bitcast truncated return admitted"));
    }
    Ok(())
}

#[test]
fn halfword_bitcast_decoder_rejects_cross_kind_and_wrong_width()
-> Result<(), String> {
    for bits in [0u16, 1, 0x7fff, 0x8000, u16::MAX] {
        for signed_source in [true, false] {
            for signed_target in [true, false] {
                reject_halfword_bitcast_checkpoint(
                    bits,
                    signed_source,
                    signed_target,
                )?;
            }
        }
    }
    Ok(())
}

fn reject_halfword_bitcast_projection(
    signed_source: bool,
    signed_target: bool,
    variation: u8,
) -> Result<(), String> {
    let (_, mut projection) =
        lowered_halfword_bitcast_fixture(0x8000, signed_source, signed_target)?;
    let cast = projection
        .functions
        .first_mut()
        .and_then(|function| function.blocks.first_mut())
        .and_then(|block| block.instructions.get_mut(1))
        .ok_or_else(|| {
            String::from("halfword bitcast projected cast absent")
        })?;
    let InputInstruction::IntegerBitcast {
        result, type_kind, value, ..
    } = cast
    else {
        return Err(String::from("halfword bitcast projection changed"));
    };
    match variation {
        0 => *type_kind = InputScalarType::U32,
        1 => *value = 99,
        2 => *result = 0,
        _ => return Err(String::from("invalid halfword bitcast case")),
    }
    let expected = if variation == 2 {
        TernaryLoweringError::InvalidProjection
    } else {
        TernaryLoweringError::UnsupportedInstruction
    };
    if lower_typed_ir(&projection) != Err(expected) {
        return Err(format!(
            "halfword bitcast projection {variation} admitted"
        ));
    }
    Ok(())
}

#[test]
fn halfword_bitcast_projection_rejects_forged_source_and_destination()
-> Result<(), String> {
    for signed_source in [true, false] {
        for signed_target in [true, false] {
            for variation in 0u8..3 {
                reject_halfword_bitcast_projection(
                    signed_source,
                    signed_target,
                    variation,
                )?;
            }
        }
    }
    Ok(())
}

#[test]
fn halfword_bitcast_inspector_converges_across_all_signedness_pairs()
-> Result<(), String> {
    for bits in [0u16, 0x7fff, 0x8000, u16::MAX] {
        for signed_source in [true, false] {
            for signed_target in [true, false] {
                let (target, projection) = lowered_halfword_bitcast_fixture(
                    bits,
                    signed_source,
                    signed_target,
                )?;
                assert_boolean_inspector_convergence(
                    "halfword-bitcast",
                    &target,
                    &projection,
                )?;
            }
        }
    }
    Ok(())
}

#[test]
fn halfword_bitcast_crash_publication_preserves_old_generation()
-> Result<(), String> {
    let previous = lowered_return_fixture()?;
    for bits in [0u16, 0x8000, u16::MAX] {
        for signed_source in [true, false] {
            for signed_target in [true, false] {
                let (target, _) = lowered_halfword_bitcast_fixture(
                    bits,
                    signed_source,
                    signed_target,
                )?;
                assert_boolean_crash_generation(&previous, &target)?;
            }
        }
    }
    Ok(())
}

#[test]
fn halfword_bitcast_inspector_rejects_retagging_and_future_tag()
-> Result<(), String> {
    for signed_source in [true, false] {
        for signed_target in [true, false] {
            let (target, _) = lowered_halfword_bitcast_fixture(
                0x8000,
                signed_source,
                signed_target,
            )?;
            let tag = halfword_bitcast_tag(signed_source, signed_target);
            let swapped = halfword_bitcast_tag(!signed_source, signed_target);
            assert_boolean_progress_tag_rejected(
                "halfword-bitcast-retag",
                &target,
                (tag, 1, swapped),
            )?;
            assert_boolean_progress_tag_rejected(
                "halfword-bitcast-unknown",
                &target,
                (tag, 1, 84),
            )?;
        }
    }
    Ok(())
}

fn halfword_truncate_instructions(bits: u32) -> Vec<LocatedInstruction> {
    vec![
        LocatedInstruction::new(
            Instruction::ConstantInteger {
                constant: IntegerConstant::new(32, bits.to_le_bytes().to_vec()),
                result: ValueId::new(0),
                type_id: TypeId::new(0),
            },
            fixture_span(0, 1),
        ),
        LocatedInstruction::new(
            Instruction::Cast {
                operation: CastOp::Truncate,
                result: ValueId::new(1),
                type_id: TypeId::new(1),
                value: ValueId::new(0),
            },
            fixture_span(1, 2),
        ),
    ]
}

fn halfword_truncate_module(
    bits: u32,
    signed_source: bool,
    signed_target: bool,
) -> Module {
    let source = if signed_source {
        TypeDef::I32
    } else {
        TypeDef::U32
    };
    let destination = if signed_target {
        TypeDef::I16
    } else {
        TypeDef::U16
    };
    Module::new(ModuleSpec {
        abi_id: String::from("malbolge-c32-v1"),
        format_version: typed_ir::TYPED_IR_VERSION,
        functions: vec![Function::new(FunctionSpec {
            blocks: vec![BasicBlock::new(BasicBlockSpec {
                id: BlockId::new(0),
                instructions: halfword_truncate_instructions(bits),
                phis: Vec::new(),
                span: fixture_span(0, 3),
                terminator: Terminator::Return {
                    value: Some(ValueId::new(1)),
                },
                terminator_span: fixture_span(2, 3),
            })],
            entry: BlockId::new(0),
            id: FunctionId::new(0),
            name: String::from("halfword_truncate"),
            parameters: Vec::new(),
            signature: TypeId::new(2),
            span: fixture_span(0, 3),
        })],
        globals: Vec::new(),
        proof_obligations: Vec::new(),
        source_id: String::from("fixtures/halfword-truncate.c"),
        source_sha256: [0x74; 32],
        target_profile: String::from("malbolge-2026"),
        types: vec![
            TypeEntry::new(TypeId::new(0), source),
            TypeEntry::new(TypeId::new(1), destination),
            TypeEntry::new(
                TypeId::new(2),
                TypeDef::function(Vec::new(), Some(TypeId::new(1)), false),
            ),
        ],
    })
}

fn lowered_halfword_truncate_fixture(
    bits: u32,
    signed_source: bool,
    signed_target: bool,
) -> Result<LoweredByteFixture, String> {
    let module = halfword_truncate_module(bits, signed_source, signed_target);
    validate_module(&module)
        .map_err(|error| format!("admit halfword truncation: {error:?}"))?;
    let encoded = canonical_bytes(&module)
        .map_err(|error| format!("encode halfword truncation: {error:?}"))?;
    let restored = canonical_module(&encoded)
        .map_err(|error| format!("restore halfword truncation: {error:?}"))?;
    if restored != module {
        return Err(String::from("halfword truncation typed IR drifted"));
    }
    let projection = project_typed_ir(&restored)?;
    let target = lower_typed_ir(&projection)
        .map_err(|error| format!("lower halfword truncation: {error:?}"))?;
    assert_program_provenance(&restored, &target)?;
    Ok((target, projection))
}

fn expected_halfword_truncate_operations(
    bits: u32,
    signed_source: bool,
    signed_target: bool,
) -> Vec<TernaryOperation> {
    let scalar = ternary_lowering::TernaryI32Scalar::from_bits(bits);
    let source_span = output_span(fixture_span(0, 1));
    let cast_span = output_span(fixture_span(1, 2));
    let return_span = output_span(fixture_span(2, 3));
    let materialize = if signed_source {
        TernaryOperation::MaterializeI32 {
            result: 0,
            scalar,
            span: source_span,
        }
    } else {
        TernaryOperation::MaterializeU32 {
            result: 0,
            scalar,
            span: source_span,
        }
    };
    let truncate = match (signed_source, signed_target) {
        (true, true) => TernaryOperation::TruncateI32ToI16 {
            result: 1,
            span: cast_span,
            value: 0,
        },
        (true, false) => TernaryOperation::TruncateI32ToU16 {
            result: 1,
            span: cast_span,
            value: 0,
        },
        (false, true) => TernaryOperation::TruncateU32ToI16 {
            result: 1,
            span: cast_span,
            value: 0,
        },
        (false, false) => TernaryOperation::TruncateU32ToU16 {
            result: 1,
            span: cast_span,
            value: 0,
        },
    };
    let ret = if signed_target {
        TernaryOperation::ReturnI16 {
            span: return_span,
            value: 1,
        }
    } else {
        TernaryOperation::ReturnU16 {
            span: return_span,
            value: 1,
        }
    };
    vec![materialize, truncate, ret]
}

const fn halfword_truncate_tag(signed_source: bool, signed_target: bool) -> u8 {
    match (signed_source, signed_target) {
        (true, true) => 74,
        (true, false) => 75,
        (false, true) => 76,
        (false, false) => 77,
    }
}

fn assert_halfword_truncate_checkpoint(
    bits: u32,
    signed_source: bool,
    signed_target: bool,
    target: &ternary_lowering::TernaryProgram,
) -> Result<Vec<u8>, String> {
    let expected = expected_halfword_truncate_operations(
        bits,
        signed_source,
        signed_target,
    );
    if target
        .functions
        .first()
        .map(|function| function.operations.as_slice())
        != Some(expected.as_slice())
    {
        return Err(String::from("halfword truncation SSA or return drifted"));
    }
    let wire = canonical_ternary_bytes(target).map_err(|error| {
        format!("encode halfword truncated checkpoint: {error:?}")
    })?;
    let tag = halfword_truncate_tag(signed_source, signed_target);
    if !wire.windows(5).any(|part| part == [tag, 1, 0, 0, 0])
        || canonical_ternary_program(&wire) != Ok(target.clone())
    {
        return Err(String::from("halfword truncation wire record drifted"));
    }
    Ok(wire)
}

fn verify_halfword_truncate_case(
    bits: u32,
    signed_source: bool,
    signed_target: bool,
) -> Result<(), String> {
    let (target, input) =
        lowered_halfword_truncate_fixture(bits, signed_source, signed_target)?;
    let kind = if signed_target {
        InputScalarType::I16
    } else {
        InputScalarType::U16
    };
    if input.functions.first().map(|function| function.return_kind)
        != Some(kind)
    {
        return Err(String::from("halfword truncation return kind drifted"));
    }
    let _wire = assert_halfword_truncate_checkpoint(
        bits,
        signed_source,
        signed_target,
        &target,
    )?;
    Ok(())
}

fn verify_halfword_truncate_patterns(bits: u32) -> Result<(), String> {
    for signed_source in [true, false] {
        for signed_target in [true, false] {
            verify_halfword_truncate_case(bits, signed_source, signed_target)?;
        }
    }
    Ok(())
}

#[test]
fn halfword_truncations_preserve_low_bytes_and_high_word_patterns()
-> Result<(), String> {
    for low in u8::MIN..=u8::MAX {
        for high in [0u32, 0x7fff_0000, 0x8000_0000, 0xffff_0000] {
            verify_halfword_truncate_patterns(high | u32::from(low))?;
            verify_halfword_truncate_patterns(high | 0x8000 | u32::from(low))?;
        }
    }
    Ok(())
}

fn reject_halfword_truncate_checkpoint(
    bits: u32,
    signed_source: bool,
    signed_target: bool,
) -> Result<(), String> {
    let (target, _) =
        lowered_halfword_truncate_fixture(bits, signed_source, signed_target)?;
    let wire = assert_halfword_truncate_checkpoint(
        bits,
        signed_source,
        signed_target,
        &target,
    )?;
    let tag = halfword_truncate_tag(signed_source, signed_target);
    let wrong_source = halfword_truncate_tag(!signed_source, signed_target);
    let wrong_target = halfword_truncate_tag(signed_source, !signed_target);
    let offset = wire
        .windows(5)
        .position(|part| part == [tag, 1, 0, 0, 0])
        .ok_or_else(|| String::from("halfword truncation tag absent"))?;
    let invalid = TernaryProgramCodecError::Validation(
        TernaryProgramValidationError::SsaValue,
    );
    for (displacement, replacement, expected) in [
        (0usize, wrong_source, invalid),
        (0, wrong_target, invalid),
        (0, 58, invalid),
        (0, 84, TernaryProgramCodecError::UnknownTag),
        (1, 0, invalid),
        (29, 99, invalid),
    ] {
        let mut forged = wire.clone();
        *forged
            .get_mut(offset.saturating_add(displacement))
            .ok_or_else(|| {
                String::from("halfword truncate wire field absent")
            })? = replacement;
        if canonical_ternary_program(&forged) != Err(expected) {
            return Err(format!(
                "truncation forged {displacement}/{replacement} admitted"
            ));
        }
    }
    let mut truncated = wire;
    let _ignored = truncated.pop();
    if canonical_ternary_program(&truncated)
        != Err(TernaryProgramCodecError::Truncated)
    {
        return Err(String::from(
            "halfword truncate incomplete return admitted",
        ));
    }
    Ok(())
}

#[test]
fn halfword_truncate_decoder_rejects_signedness_and_width_forgery()
-> Result<(), String> {
    for bits in [0u32, 1, 0x7fff, 0x8000, 0xffff, u32::MAX] {
        for signed_source in [true, false] {
            for signed_target in [true, false] {
                reject_halfword_truncate_checkpoint(
                    bits,
                    signed_source,
                    signed_target,
                )?;
            }
        }
    }
    Ok(())
}

fn reject_halfword_truncate_projection(
    signed_source: bool,
    signed_target: bool,
    variation: u8,
) -> Result<(), String> {
    let (_, mut projection) = lowered_halfword_truncate_fixture(
        0x8000_8000,
        signed_source,
        signed_target,
    )?;
    let cast = projection
        .functions
        .first_mut()
        .and_then(|function| function.blocks.first_mut())
        .and_then(|block| block.instructions.get_mut(1))
        .ok_or_else(|| String::from("halfword truncation cast absent"))?;
    let InputInstruction::TruncateInteger {
        result, type_kind, value, ..
    } = cast
    else {
        return Err(String::from("halfword truncate projection changed"));
    };
    match variation {
        0 => *type_kind = InputScalarType::U32,
        1 => *value = 99,
        2 => *result = 0,
        _ => return Err(String::from("invalid halfword truncate forgery")),
    }
    let expected = if variation == 2 {
        TernaryLoweringError::InvalidProjection
    } else {
        TernaryLoweringError::UnsupportedInstruction
    };
    if lower_typed_ir(&projection) != Err(expected) {
        return Err(format!(
            "halfword truncation projection {variation} admitted"
        ));
    }
    Ok(())
}

#[test]
fn halfword_truncate_rejects_bad_projection_ssa() -> Result<(), String> {
    for signed_source in [true, false] {
        for signed_target in [true, false] {
            for variation in 0u8..3 {
                reject_halfword_truncate_projection(
                    signed_source,
                    signed_target,
                    variation,
                )?;
            }
        }
    }
    Ok(())
}

#[test]
fn halfword_truncate_inspector_converges_for_all_signedness_pairs()
-> Result<(), String> {
    for bits in [0u32, 0x7fff, 0x8000, 0xffff, u32::MAX] {
        for signed_source in [true, false] {
            for signed_target in [true, false] {
                let (target, input) = lowered_halfword_truncate_fixture(
                    bits,
                    signed_source,
                    signed_target,
                )?;
                assert_boolean_inspector_convergence(
                    "word-to-halfword-truncation",
                    &target,
                    &input,
                )?;
            }
        }
    }
    Ok(())
}

#[test]
fn halfword_truncate_crash_publication_preserves_old_generation()
-> Result<(), String> {
    let previous = lowered_return_fixture()?;
    for bits in [0u32, 0x8000_8000, u32::MAX] {
        for signed_source in [true, false] {
            for signed_target in [true, false] {
                let (target, _) = lowered_halfword_truncate_fixture(
                    bits,
                    signed_source,
                    signed_target,
                )?;
                assert_boolean_crash_generation(&previous, &target)?;
            }
        }
    }
    Ok(())
}

#[test]
fn halfword_truncate_inspector_rejects_swapped_and_future_tags()
-> Result<(), String> {
    for signed_source in [true, false] {
        for signed_target in [true, false] {
            let (target, _) = lowered_halfword_truncate_fixture(
                0x8000_8000,
                signed_source,
                signed_target,
            )?;
            let tag = halfword_truncate_tag(signed_source, signed_target);
            let swapped = halfword_truncate_tag(!signed_source, signed_target);
            assert_boolean_progress_tag_rejected(
                "halfword-truncate-signedness",
                &target,
                (tag, 1, swapped),
            )?;
            assert_boolean_progress_tag_rejected(
                "halfword-truncate-future",
                &target,
                (tag, 1, 84),
            )?;
        }
    }
    Ok(())
}

fn halfword_to_byte_instructions(bits: u16) -> Vec<LocatedInstruction> {
    vec![
        LocatedInstruction::new(
            Instruction::ConstantInteger {
                constant: IntegerConstant::new(16, bits.to_le_bytes().to_vec()),
                result: ValueId::new(0),
                type_id: TypeId::new(0),
            },
            fixture_span(0, 1),
        ),
        LocatedInstruction::new(
            Instruction::Cast {
                operation: CastOp::Truncate,
                result: ValueId::new(1),
                type_id: TypeId::new(1),
                value: ValueId::new(0),
            },
            fixture_span(1, 2),
        ),
    ]
}

fn halfword_to_byte_module(
    bits: u16,
    signed_source: bool,
    signed_target: bool,
) -> Module {
    let source = if signed_source {
        TypeDef::I16
    } else {
        TypeDef::U16
    };
    let destination = if signed_target {
        TypeDef::I8
    } else {
        TypeDef::U8
    };
    Module::new(ModuleSpec {
        abi_id: String::from("malbolge-c32-v1"),
        format_version: typed_ir::TYPED_IR_VERSION,
        functions: vec![Function::new(FunctionSpec {
            blocks: vec![BasicBlock::new(BasicBlockSpec {
                id: BlockId::new(0),
                instructions: halfword_to_byte_instructions(bits),
                phis: Vec::new(),
                span: fixture_span(0, 3),
                terminator: Terminator::Return {
                    value: Some(ValueId::new(1)),
                },
                terminator_span: fixture_span(2, 3),
            })],
            entry: BlockId::new(0),
            id: FunctionId::new(0),
            name: String::from("halfword_truncate"),
            parameters: Vec::new(),
            signature: TypeId::new(2),
            span: fixture_span(0, 3),
        })],
        globals: Vec::new(),
        proof_obligations: Vec::new(),
        source_id: String::from("fixtures/halfword-truncate.c"),
        source_sha256: [0x78; 32],
        target_profile: String::from("malbolge-2026"),
        types: vec![
            TypeEntry::new(TypeId::new(0), source),
            TypeEntry::new(TypeId::new(1), destination),
            TypeEntry::new(
                TypeId::new(2),
                TypeDef::function(Vec::new(), Some(TypeId::new(1)), false),
            ),
        ],
    })
}

fn lowered_halfword_to_byte_fixture(
    bits: u16,
    signed_source: bool,
    signed_target: bool,
) -> Result<LoweredByteFixture, String> {
    let module = halfword_to_byte_module(bits, signed_source, signed_target);
    validate_module(&module).map_err(|error| {
        format!("admit halfword-to-byte truncation: {error:?}")
    })?;
    let encoded = canonical_bytes(&module).map_err(|error| {
        format!("encode halfword-to-byte truncation: {error:?}")
    })?;
    let restored = canonical_module(&encoded).map_err(|error| {
        format!("restore halfword-to-byte truncation: {error:?}")
    })?;
    if restored != module {
        return Err(String::from(
            "halfword-to-byte truncation typed IR drifted",
        ));
    }
    let projection = project_typed_ir(&restored)?;
    let target = lower_typed_ir(&projection).map_err(|error| {
        format!("lower halfword-to-byte truncation: {error:?}")
    })?;
    assert_program_provenance(&restored, &target)?;
    Ok((target, projection))
}

fn expected_halfword_to_byte_operations(
    bits: u16,
    signed_source: bool,
    signed_target: bool,
) -> Vec<TernaryOperation> {
    let scalar = ternary_lowering::TernaryU16Scalar::from_bits(bits);
    let source_span = output_span(fixture_span(0, 1));
    let cast_span = output_span(fixture_span(1, 2));
    let return_span = output_span(fixture_span(2, 3));
    let materialize = if signed_source {
        TernaryOperation::MaterializeI16 {
            result: 0,
            scalar,
            span: source_span,
        }
    } else {
        TernaryOperation::MaterializeU16 {
            result: 0,
            scalar,
            span: source_span,
        }
    };
    let truncate = match (signed_source, signed_target) {
        (true, true) => TernaryOperation::TruncateI16ToI8 {
            result: 1,
            span: cast_span,
            value: 0,
        },
        (true, false) => TernaryOperation::TruncateI16ToU8 {
            result: 1,
            span: cast_span,
            value: 0,
        },
        (false, true) => TernaryOperation::TruncateU16ToI8 {
            result: 1,
            span: cast_span,
            value: 0,
        },
        (false, false) => TernaryOperation::TruncateU16ToU8 {
            result: 1,
            span: cast_span,
            value: 0,
        },
    };
    let ret = if signed_target {
        TernaryOperation::ReturnI8 {
            span: return_span,
            value: 1,
        }
    } else {
        TernaryOperation::ReturnU8 {
            span: return_span,
            value: 1,
        }
    };
    vec![materialize, truncate, ret]
}

const fn halfword_to_byte_tag(signed_source: bool, signed_target: bool) -> u8 {
    match (signed_source, signed_target) {
        (true, true) => 78,
        (true, false) => 79,
        (false, true) => 80,
        (false, false) => 81,
    }
}

fn assert_halfword_to_byte_checkpoint(
    bits: u16,
    signed_source: bool,
    signed_target: bool,
    target: &ternary_lowering::TernaryProgram,
) -> Result<Vec<u8>, String> {
    let expected = expected_halfword_to_byte_operations(
        bits,
        signed_source,
        signed_target,
    );
    if target
        .functions
        .first()
        .map(|function| function.operations.as_slice())
        != Some(expected.as_slice())
    {
        return Err(String::from(
            "halfword-to-byte truncation SSA or return drifted",
        ));
    }
    let wire = canonical_ternary_bytes(target).map_err(|error| {
        format!("encode halfword truncated checkpoint: {error:?}")
    })?;
    let tag = halfword_to_byte_tag(signed_source, signed_target);
    if !wire.windows(5).any(|part| part == [tag, 1, 0, 0, 0])
        || canonical_ternary_program(&wire) != Ok(target.clone())
    {
        return Err(String::from(
            "halfword-to-byte truncation wire record drifted",
        ));
    }
    Ok(wire)
}

fn verify_halfword_to_byte_case(
    bits: u16,
    signed_source: bool,
    signed_target: bool,
) -> Result<(), String> {
    let (target, input) =
        lowered_halfword_to_byte_fixture(bits, signed_source, signed_target)?;
    let kind = if signed_target {
        InputScalarType::I8
    } else {
        InputScalarType::U8
    };
    if input.functions.first().map(|function| function.return_kind)
        != Some(kind)
    {
        return Err(String::from(
            "halfword-to-byte truncation return kind drifted",
        ));
    }
    let _wire = assert_halfword_to_byte_checkpoint(
        bits,
        signed_source,
        signed_target,
        &target,
    )?;
    Ok(())
}

fn verify_halfword_to_byte_patterns(bits: u16) -> Result<(), String> {
    for signed_source in [true, false] {
        for signed_target in [true, false] {
            verify_halfword_to_byte_case(bits, signed_source, signed_target)?;
        }
    }
    Ok(())
}

#[test]
fn halfword_to_byte_truncations_preserve_all_low_byte_patterns()
-> Result<(), String> {
    for low in u8::MIN..=u8::MAX {
        for high in [0u16, 0x7f00, 0x8000, 0xff00] {
            verify_halfword_to_byte_patterns(high | u16::from(low))?;
        }
    }
    Ok(())
}

fn reject_halfword_to_byte_checkpoint(
    bits: u16,
    signed_source: bool,
    signed_target: bool,
) -> Result<(), String> {
    let (target, _) =
        lowered_halfword_to_byte_fixture(bits, signed_source, signed_target)?;
    let wire = assert_halfword_to_byte_checkpoint(
        bits,
        signed_source,
        signed_target,
        &target,
    )?;
    let tag = halfword_to_byte_tag(signed_source, signed_target);
    let wrong_source = halfword_to_byte_tag(!signed_source, signed_target);
    let wrong_target = halfword_to_byte_tag(signed_source, !signed_target);
    let offset = wire
        .windows(5)
        .position(|part| part == [tag, 1, 0, 0, 0])
        .ok_or_else(|| {
            String::from("halfword-to-byte truncation tag absent")
        })?;
    let invalid = TernaryProgramCodecError::Validation(
        TernaryProgramValidationError::SsaValue,
    );
    for (displacement, replacement, expected) in [
        (0usize, wrong_source, invalid),
        (0, wrong_target, invalid),
        (0, 58, invalid),
        (0, 84, TernaryProgramCodecError::UnknownTag),
        (1, 0, invalid),
        (29, 99, invalid),
    ] {
        let mut forged = wire.clone();
        *forged
            .get_mut(offset.saturating_add(displacement))
            .ok_or_else(|| {
                String::from("halfword-to-byte truncate wire field absent")
            })? = replacement;
        if canonical_ternary_program(&forged) != Err(expected) {
            return Err(format!(
                "truncation forged {displacement}/{replacement} admitted"
            ));
        }
    }
    let mut truncated = wire;
    let _ignored = truncated.pop();
    if canonical_ternary_program(&truncated)
        != Err(TernaryProgramCodecError::Truncated)
    {
        return Err(String::from(
            "halfword-to-byte truncate incomplete return admitted",
        ));
    }
    Ok(())
}

#[test]
fn halfword_to_byte_decoder_rejects_signedness_and_width_forgery()
-> Result<(), String> {
    for bits in [0u16, 1, 0x7f, 0x8000, 0xff, u16::MAX] {
        for signed_source in [true, false] {
            for signed_target in [true, false] {
                reject_halfword_to_byte_checkpoint(
                    bits,
                    signed_source,
                    signed_target,
                )?;
            }
        }
    }
    Ok(())
}

fn reject_halfword_to_byte_projection(
    signed_source: bool,
    signed_target: bool,
    variation: u8,
) -> Result<(), String> {
    let (_, mut projection) =
        lowered_halfword_to_byte_fixture(0x8000, signed_source, signed_target)?;
    let cast = projection
        .functions
        .first_mut()
        .and_then(|function| function.blocks.first_mut())
        .and_then(|block| block.instructions.get_mut(1))
        .ok_or_else(|| {
            String::from("halfword-to-byte truncation cast absent")
        })?;
    let InputInstruction::TruncateInteger {
        result, type_kind, value, ..
    } = cast
    else {
        return Err(String::from(
            "halfword-to-byte truncate projection changed",
        ));
    };
    match variation {
        0 => *type_kind = InputScalarType::U16,
        1 => *value = 99,
        2 => *result = 0,
        _ => {
            return Err(String::from(
                "invalid halfword-to-byte truncate forgery",
            ));
        },
    }
    let expected = if variation == 2 {
        TernaryLoweringError::InvalidProjection
    } else {
        TernaryLoweringError::UnsupportedInstruction
    };
    if lower_typed_ir(&projection) != Err(expected) {
        return Err(format!(
            "halfword-to-byte truncation projection {variation} admitted"
        ));
    }
    Ok(())
}

#[test]
fn halfword_to_byte_rejects_bad_projection_ssa() -> Result<(), String> {
    for signed_source in [true, false] {
        for signed_target in [true, false] {
            for variation in 0u8..3 {
                reject_halfword_to_byte_projection(
                    signed_source,
                    signed_target,
                    variation,
                )?;
            }
        }
    }
    Ok(())
}

#[test]
fn halfword_to_byte_inspector_converges_for_all_signedness_pairs()
-> Result<(), String> {
    for bits in [0u16, 0x7f, 0x8000, 0xff, u16::MAX] {
        for signed_source in [true, false] {
            for signed_target in [true, false] {
                let (target, input) = lowered_halfword_to_byte_fixture(
                    bits,
                    signed_source,
                    signed_target,
                )?;
                assert_boolean_inspector_convergence(
                    "halfword-to-byte-truncation",
                    &target,
                    &input,
                )?;
            }
        }
    }
    Ok(())
}

#[test]
fn halfword_to_byte_crash_publication_preserves_old_generation()
-> Result<(), String> {
    let previous = lowered_return_fixture()?;
    for bits in [0u16, 0x8000, u16::MAX] {
        for signed_source in [true, false] {
            for signed_target in [true, false] {
                let (target, _) = lowered_halfword_to_byte_fixture(
                    bits,
                    signed_source,
                    signed_target,
                )?;
                assert_boolean_crash_generation(&previous, &target)?;
            }
        }
    }
    Ok(())
}

#[test]
fn halfword_to_byte_inspector_rejects_swapped_and_future_tags()
-> Result<(), String> {
    for signed_source in [true, false] {
        for signed_target in [true, false] {
            let (target, _) = lowered_halfword_to_byte_fixture(
                0x8000,
                signed_source,
                signed_target,
            )?;
            let tag = halfword_to_byte_tag(signed_source, signed_target);
            let swapped = halfword_to_byte_tag(!signed_source, signed_target);
            assert_boolean_progress_tag_rejected(
                "halfword-to-byte-signedness",
                &target,
                (tag, 1, swapped),
            )?;
            assert_boolean_progress_tag_rejected(
                "halfword-to-byte-future",
                &target,
                (tag, 1, 84),
            )?;
        }
    }
    Ok(())
}

fn byte_to_halfword_widen_instructions(
    bits: u8,
    signed: bool,
) -> Vec<LocatedInstruction> {
    let operation = if signed {
        CastOp::SignExtend
    } else {
        CastOp::ZeroExtend
    };
    vec![
        LocatedInstruction::new(
            Instruction::ConstantInteger {
                constant: IntegerConstant::new(8, vec![bits]),
                result: ValueId::new(0),
                type_id: TypeId::new(0),
            },
            fixture_span(0, 1),
        ),
        LocatedInstruction::new(
            Instruction::Cast {
                operation,
                result: ValueId::new(1),
                type_id: TypeId::new(1),
                value: ValueId::new(0),
            },
            fixture_span(1, 2),
        ),
    ]
}

fn byte_to_halfword_widen_module(bits: u8, signed: bool) -> Module {
    let narrow = if signed {
        TypeDef::I8
    } else {
        TypeDef::U8
    };
    let word = if signed {
        TypeDef::I16
    } else {
        TypeDef::U16
    };
    Module::new(ModuleSpec {
        abi_id: String::from("malbolge-c32-v1"),
        format_version: typed_ir::TYPED_IR_VERSION,
        functions: vec![Function::new(FunctionSpec {
            blocks: vec![BasicBlock::new(BasicBlockSpec {
                id: BlockId::new(0),
                instructions: byte_to_halfword_widen_instructions(bits, signed),
                phis: Vec::new(),
                span: fixture_span(0, 3),
                terminator: Terminator::Return {
                    value: Some(ValueId::new(1)),
                },
                terminator_span: fixture_span(2, 3),
            })],
            entry: BlockId::new(0),
            id: FunctionId::new(0),
            name: String::from("byte_to_halfword_widen"),
            parameters: Vec::new(),
            signature: TypeId::new(2),
            span: fixture_span(0, 3),
        })],
        globals: Vec::new(),
        proof_obligations: Vec::new(),
        source_id: String::from("fixtures/byte-halfword-widen.c"),
        source_sha256: [0x82; 32],
        target_profile: String::from("malbolge-2026"),
        types: vec![
            TypeEntry::new(TypeId::new(0), narrow),
            TypeEntry::new(TypeId::new(1), word),
            TypeEntry::new(
                TypeId::new(2),
                TypeDef::function(Vec::new(), Some(TypeId::new(1)), false),
            ),
        ],
    })
}

fn lowered_byte_to_halfword_widen_fixture(
    bits: u8,
    signed: bool,
) -> Result<LoweredByteFixture, String> {
    let module = byte_to_halfword_widen_module(bits, signed);
    validate_module(&module)
        .map_err(|error| format!("admit 16-bit widening: {error:?}"))?;
    let encoded = canonical_bytes(&module)
        .map_err(|error| format!("encode 16-bit widening: {error:?}"))?;
    let restored = canonical_module(&encoded)
        .map_err(|error| format!("restore 16-bit widening: {error:?}"))?;
    if restored != module {
        return Err(String::from("16-bit widening typed IR drifted"));
    }
    let projection = project_typed_ir(&restored)?;
    let target = lower_typed_ir(&projection)
        .map_err(|error| format!("lower 16-bit widening: {error:?}"))?;
    assert_program_provenance(&restored, &target)?;
    Ok((target, projection))
}

fn expected_byte_to_halfword_widen_operations(
    bits: u8,
    signed: bool,
) -> Vec<TernaryOperation> {
    let scalar = ternary_lowering::TernaryU8Scalar::from_bits(bits);
    let materialize = if signed {
        TernaryOperation::MaterializeI8 {
            result: 0,
            scalar,
            span: output_span(fixture_span(0, 1)),
        }
    } else {
        TernaryOperation::MaterializeU8 {
            result: 0,
            scalar,
            span: output_span(fixture_span(0, 1)),
        }
    };
    let widen = if signed {
        TernaryOperation::SignExtendI8ToI16 {
            result: 1,
            span: output_span(fixture_span(1, 2)),
            value: 0,
        }
    } else {
        TernaryOperation::ZeroExtendU8ToU16 {
            result: 1,
            span: output_span(fixture_span(1, 2)),
            value: 0,
        }
    };
    let done = if signed {
        TernaryOperation::ReturnI16 {
            span: output_span(fixture_span(2, 3)),
            value: 1,
        }
    } else {
        TernaryOperation::ReturnU16 {
            span: output_span(fixture_span(2, 3)),
            value: 1,
        }
    };
    vec![materialize, widen, done]
}

fn assert_byte_to_halfword_widen_checkpoint(
    bits: u8,
    signed: bool,
    target: &ternary_lowering::TernaryProgram,
) -> Result<Vec<u8>, String> {
    let expected = expected_byte_to_halfword_widen_operations(bits, signed);
    if target
        .functions
        .first()
        .map(|function| function.operations.as_slice())
        != Some(expected.as_slice())
    {
        return Err(String::from("byte-halfword widen SSA or return drifted"));
    }
    let wire = canonical_ternary_bytes(target).map_err(|error| {
        format!("encode byte-halfword widen checkpoint: {error:?}")
    })?;
    let tag = if signed {
        82u8
    } else {
        83
    };
    if !wire.windows(5).any(|part| part == [tag, 1, 0, 0, 0])
        || canonical_ternary_program(&wire) != Ok(target.clone())
    {
        return Err(String::from("byte-halfword widen wire record drifted"));
    }
    Ok(wire)
}

fn verify_byte_to_halfword_widen_case(
    bits: u8,
    signed: bool,
) -> Result<(), String> {
    let (target, input) = lowered_byte_to_halfword_widen_fixture(bits, signed)?;
    let kind = if signed {
        InputScalarType::I16
    } else {
        InputScalarType::U16
    };
    if input.functions.first().map(|function| function.return_kind)
        != Some(kind)
    {
        return Err(String::from(
            "byte-halfword widen target return type drifted",
        ));
    }
    let _wire =
        assert_byte_to_halfword_widen_checkpoint(bits, signed, &target)?;
    Ok(())
}

#[test]
fn typed_byte_to_halfword_widening_preserves_all_byte_patterns()
-> Result<(), String> {
    for bits in u8::MIN..=u8::MAX {
        for signed in [true, false] {
            verify_byte_to_halfword_widen_case(bits, signed)?;
        }
    }
    Ok(())
}

fn reject_byte_to_halfword_widen_checkpoint(
    bits: u8,
    signed: bool,
) -> Result<(), String> {
    let (target, _) = lowered_byte_to_halfword_widen_fixture(bits, signed)?;
    let wire = assert_byte_to_halfword_widen_checkpoint(bits, signed, &target)?;
    let tag = if signed {
        82u8
    } else {
        83
    };
    let wrong_sign = if signed {
        83u8
    } else {
        82
    };
    let wrong_width = if signed {
        51u8
    } else {
        16
    };
    let index = wire
        .windows(5)
        .position(|part| part == [tag, 1, 0, 0, 0])
        .ok_or_else(|| String::from("byte-halfword widen tag absent"))?;
    let invalid = TernaryProgramCodecError::Validation(
        TernaryProgramValidationError::SsaValue,
    );
    for (offset, replacement, expected) in [
        (0usize, wrong_sign, invalid),
        (0, wrong_width, invalid),
        (0, 84, TernaryProgramCodecError::UnknownTag),
        (1, 0, invalid),
        (29, 99, invalid),
    ] {
        let mut forged = wire.clone();
        *forged
            .get_mut(index.saturating_add(offset))
            .ok_or_else(|| {
                String::from("byte-halfword widen wire field missing")
            })? = replacement;
        if canonical_ternary_program(&forged) != Err(expected) {
            return Err(format!(
                "byte-halfword widen forged {offset}/{replacement} admitted"
            ));
        }
    }
    let mut truncated = wire;
    let _ignored = truncated.pop();
    if canonical_ternary_program(&truncated)
        != Err(TernaryProgramCodecError::Truncated)
    {
        return Err(String::from(
            "byte-halfword widen truncated record admitted",
        ));
    }
    Ok(())
}

#[test]
fn byte_to_halfword_widen_decoder_rejects_signedness_width_and_ssa_forgery()
-> Result<(), String> {
    for bits in [0u8, 1, 0x7f, 0x80, 0x81, u8::MAX] {
        for signed in [true, false] {
            reject_byte_to_halfword_widen_checkpoint(bits, signed)?;
        }
    }
    Ok(())
}

fn reject_byte_to_halfword_widen_projection(
    signed: bool,
    variation: u8,
) -> Result<(), String> {
    let (_, mut projection) =
        lowered_byte_to_halfword_widen_fixture(0x80, signed)?;
    let cast = projection
        .functions
        .first_mut()
        .and_then(|function| function.blocks.first_mut())
        .and_then(|block| block.instructions.get_mut(1))
        .ok_or_else(|| {
            String::from("byte-halfword widen projected cast absent")
        })?;
    let (InputInstruction::SignExtendI8ToI32 {
        result,
        type_kind: kind,
        value,
        ..
    }
    | InputInstruction::ZeroExtendInteger {
        result,
        type_kind: kind,
        value,
        ..
    }) = cast
    else {
        return Err(String::from(
            "byte-byte-halfword widening projection changed",
        ));
    };
    match variation {
        0 => {
            *kind = if signed {
                InputScalarType::U16
            } else {
                InputScalarType::I16
            }
        },
        1 => *value = 99,
        2 => *result = 0,
        _ => return Err(String::from("invalid byte-halfword widen forgery")),
    }
    let error = if variation == 2 {
        TernaryLoweringError::InvalidProjection
    } else {
        TernaryLoweringError::UnsupportedInstruction
    };
    if lower_typed_ir(&projection) != Err(error) {
        return Err(format!(
            "byte-byte-halfword widening projection {variation} admitted"
        ));
    }
    Ok(())
}

#[test]
fn byte_to_halfword_widen_projection_rejects_wrong_destination_and_ssa()
-> Result<(), String> {
    for signed in [true, false] {
        for variation in 0u8..3 {
            reject_byte_to_halfword_widen_projection(signed, variation)?;
        }
    }
    Ok(())
}

#[test]
fn byte_to_halfword_widen_inspector_recovers_signed_and_unsigned_chains()
-> Result<(), String> {
    for bits in [0u8, 1, 0x7f, 0x80, u8::MAX] {
        for signed in [true, false] {
            let (target, input) =
                lowered_byte_to_halfword_widen_fixture(bits, signed)?;
            let label = if signed {
                "signed-byte-to-halfword"
            } else {
                "unsigned-byte-to-halfword"
            };
            assert_boolean_inspector_convergence(label, &target, &input)?;
        }
    }
    Ok(())
}

#[test]
fn byte_to_halfword_widen_crash_boundaries_preserve_committed_generation()
-> Result<(), String> {
    let previous = lowered_return_fixture()?;
    for bits in [0u8, 0x7f, 0x80, u8::MAX] {
        for signed in [true, false] {
            let (target, _) =
                lowered_byte_to_halfword_widen_fixture(bits, signed)?;
            assert_boolean_crash_generation(&previous, &target)?;
        }
    }
    Ok(())
}

#[test]
fn byte_to_halfword_widen_inspector_rejects_retagged_or_unknown_cast()
-> Result<(), String> {
    for signed in [true, false] {
        let (target, _) = lowered_byte_to_halfword_widen_fixture(0x80, signed)?;
        let tag = if signed {
            82u8
        } else {
            83
        };
        let wrong = if signed {
            83u8
        } else {
            82
        };
        assert_boolean_progress_tag_rejected(
            "byte-halfword-widen-cross-kind",
            &target,
            (tag, 1, wrong),
        )?;
        assert_boolean_progress_tag_rejected(
            "byte-halfword-widen-future",
            &target,
            (tag, 1, 84),
        )?;
    }
    Ok(())
}

fn promoted_byte_instructions(
    pair: (u8, u8),
    signed: bool,
    equal: bool,
    narrow: Option<bool>,
) -> Vec<LocatedInstruction> {
    let byte_cast = if signed {
        CastOp::SignExtend
    } else {
        CastOp::ZeroExtend
    };
    let mut instructions = Vec::new();
    for (base, bits) in [(0u32, pair.0), (3, pair.1)] {
        instructions.push(LocatedInstruction::new(
            Instruction::ConstantInteger {
                constant: IntegerConstant::new(8, vec![bits]),
                result: ValueId::new(base),
                type_id: TypeId::new(0),
            },
            fixture_span(base, base.saturating_add(1)),
        ));
        for (step, type_id) in [(1u32, 1u32), (2, 2)] {
            instructions.push(LocatedInstruction::new(
                Instruction::Cast {
                    operation: byte_cast,
                    result: ValueId::new(base.saturating_add(step)),
                    type_id: TypeId::new(type_id),
                    value: ValueId::new(
                        base.saturating_add(step.saturating_sub(1)),
                    ),
                },
                fixture_span(
                    base.saturating_add(step),
                    base.saturating_add(step.saturating_add(1)),
                ),
            ));
        }
    }
    let (left_id, right_id) = match narrow {
        Some(true) => (1, 4),
        Some(false) => (0, 3),
        None => (2, 5),
    };
    instructions.push(LocatedInstruction::new(
        Instruction::Compare {
            left: ValueId::new(left_id),
            operation: if equal {
                CompareOp::Equal
            } else {
                CompareOp::NotEqual
            },
            result: ValueId::new(6),
            right: ValueId::new(right_id),
            type_id: TypeId::new(3),
        },
        fixture_span(6, 7),
    ));
    instructions
}

fn promoted_byte_comparison_module(
    pair: (u8, u8),
    signed: bool,
    equal: bool,
) -> Module {
    promoted_byte_comparison_module_at_width(pair, signed, equal, None)
}

fn promoted_byte_comparison_module_at_width(
    pair: (u8, u8),
    signed: bool,
    equal: bool,
    narrow: Option<bool>,
) -> Module {
    let types = if signed {
        [TypeDef::I8, TypeDef::I16, TypeDef::I32]
    } else {
        [TypeDef::U8, TypeDef::U16, TypeDef::U32]
    };
    Module::new(ModuleSpec {
        abi_id: String::from("malbolge-c32-v1"),
        format_version: typed_ir::TYPED_IR_VERSION,
        functions: vec![Function::new(FunctionSpec {
            blocks: vec![BasicBlock::new(BasicBlockSpec {
                id: BlockId::new(0),
                instructions: promoted_byte_instructions(
                    pair, signed, equal, narrow,
                ),
                phis: Vec::new(),
                span: fixture_span(0, 8),
                terminator: Terminator::Return {
                    value: Some(ValueId::new(6)),
                },
                terminator_span: fixture_span(7, 8),
            })],
            entry: BlockId::new(0),
            id: FunctionId::new(0),
            name: String::from("promoted_byte_comparison"),
            parameters: Vec::new(),
            signature: TypeId::new(4),
            span: fixture_span(0, 8),
        })],
        globals: Vec::new(),
        proof_obligations: Vec::new(),
        source_id: String::from("fixtures/promoted-byte-comparison.c"),
        source_sha256: [0x84; 32],
        target_profile: String::from("malbolge-2026"),
        types: vec![
            TypeEntry::new(TypeId::new(0), types[0].clone()),
            TypeEntry::new(TypeId::new(1), types[1].clone()),
            TypeEntry::new(TypeId::new(2), types[2].clone()),
            TypeEntry::new(TypeId::new(3), TypeDef::Bool),
            TypeEntry::new(
                TypeId::new(4),
                TypeDef::function(Vec::new(), Some(TypeId::new(3)), false),
            ),
        ],
    })
}

fn lowered_promoted_byte_comparison_fixture(
    pair: (u8, u8),
    signed: bool,
    equal: bool,
) -> Result<LoweredByteFixture, String> {
    let module = promoted_byte_comparison_module(pair, signed, equal);
    validate_module(&module)
        .map_err(|error| format!("admit promoted comparison: {error:?}"))?;
    let bytes = canonical_bytes(&module)
        .map_err(|error| format!("encode promoted comparison: {error:?}"))?;
    let restored = canonical_module(&bytes)
        .map_err(|error| format!("restore promoted comparison: {error:?}"))?;
    if restored != module {
        return Err(String::from("promoted comparison typed IR drifted"));
    }
    let input = project_typed_ir(&restored)?;
    let target = lower_typed_ir(&input)
        .map_err(|error| format!("lower promoted comparison: {error:?}"))?;
    assert_program_provenance(&restored, &target)?;
    Ok((target, input))
}

fn expected_promoted_byte_steps(
    bits: u8,
    signed: bool,
    base: u32,
) -> Vec<TernaryOperation> {
    let scalar = ternary_lowering::TernaryU8Scalar::from_bits(bits);
    let first_span = output_span(fixture_span(base, base.saturating_add(1)));
    let second_span = output_span(fixture_span(
        base.saturating_add(1),
        base.saturating_add(2),
    ));
    let third_span = output_span(fixture_span(
        base.saturating_add(2),
        base.saturating_add(3),
    ));
    if signed {
        vec![
            TernaryOperation::MaterializeI8 {
                result: base,
                scalar,
                span: first_span,
            },
            TernaryOperation::SignExtendI8ToI16 {
                result: base.saturating_add(1),
                span: second_span,
                value: base,
            },
            TernaryOperation::SignExtendI16ToI32 {
                result: base.saturating_add(2),
                span: third_span,
                value: base.saturating_add(1),
            },
        ]
    } else {
        vec![
            TernaryOperation::MaterializeU8 {
                result: base,
                scalar,
                span: first_span,
            },
            TernaryOperation::ZeroExtendU8ToU16 {
                result: base.saturating_add(1),
                span: second_span,
                value: base,
            },
            TernaryOperation::ZeroExtendU16ToU32 {
                result: base.saturating_add(2),
                span: third_span,
                value: base.saturating_add(1),
            },
        ]
    }
}

fn expected_promoted_byte_comparison(
    pair: (u8, u8),
    signed: bool,
    equal: bool,
) -> Vec<TernaryOperation> {
    let mut operations = expected_promoted_byte_steps(pair.0, signed, 0);
    operations.extend(expected_promoted_byte_steps(pair.1, signed, 3));
    let span = output_span(fixture_span(6, 7));
    operations.push(match (signed, equal) {
        (true, true) => TernaryOperation::EqualI32 {
            left: 2,
            result: 6,
            right: 5,
            span,
        },
        (false, true) => TernaryOperation::EqualU32 {
            left: 2,
            result: 6,
            right: 5,
            span,
        },
        (true, false) => TernaryOperation::NotEqualI32 {
            left: 2,
            result: 6,
            right: 5,
            span,
        },
        (false, false) => TernaryOperation::NotEqualU32 {
            left: 2,
            result: 6,
            right: 5,
            span,
        },
    });
    operations.push(TernaryOperation::ReturnBool {
        span: output_span(fixture_span(7, 8)),
        value: 6,
    });
    operations
}

fn assert_promoted_byte_checkpoint(
    pair: (u8, u8),
    signed: bool,
    equal: bool,
    target: &ternary_lowering::TernaryProgram,
) -> Result<Vec<u8>, String> {
    let expected = expected_promoted_byte_comparison(pair, signed, equal);
    if target
        .functions
        .first()
        .map(|function| function.operations.as_slice())
        != Some(expected.as_slice())
    {
        return Err(String::from("promoted comparison SSA chain drifted"));
    }
    let wire = canonical_ternary_bytes(target)
        .map_err(|error| format!("encode promoted target: {error:?}"))?;
    let narrow_tag = if signed {
        82u8
    } else {
        83
    };
    let wide_tag = if signed {
        68u8
    } else {
        69
    };
    if !wire.windows(5).any(|part| part == [narrow_tag, 1, 0, 0, 0])
        || !wire.windows(5).any(|part| part == [wide_tag, 2, 0, 0, 0])
        || canonical_ternary_program(&wire) != Ok(target.clone())
    {
        return Err(String::from("promoted comparison wire drifted"));
    }
    Ok(wire)
}

fn verify_promoted_byte_case(
    pair: (u8, u8),
    signed: bool,
    equal: bool,
) -> Result<(), String> {
    let (target, input) =
        lowered_promoted_byte_comparison_fixture(pair, signed, equal)?;
    if input.functions.first().map(|function| function.return_kind)
        != Some(InputScalarType::Bool)
    {
        return Err(String::from("promoted comparison return kind drifted"));
    }
    let _wire = assert_promoted_byte_checkpoint(pair, signed, equal, &target)?;
    Ok(())
}

fn verify_promoted_byte_pairs(pair: (u8, u8)) -> Result<(), String> {
    for signed in [true, false] {
        for equal in [true, false] {
            verify_promoted_byte_case(pair, signed, equal)?;
        }
    }
    Ok(())
}

#[test]
fn promoted_byte_comparisons_keep_distinct_ssa() -> Result<(), String> {
    for bits in u8::MIN..=u8::MAX {
        verify_promoted_byte_pairs((bits, bits))?;
        verify_promoted_byte_pairs((bits, bits ^ 1))?;
    }
    Ok(())
}

fn reject_unpromoted_comparison(
    signed: bool,
    equal: bool,
    halfword: bool,
) -> Result<(), String> {
    let module = promoted_byte_comparison_module_at_width(
        (0x80, 0x7f),
        signed,
        equal,
        Some(halfword),
    );
    if validate_module(&module).is_ok() {
        return Err(String::from("unpromoted narrow comparison admitted"));
    }
    Ok(())
}

#[test]
fn promoted_comparison_rejects_unpromoted_bytes_and_halfwords()
-> Result<(), String> {
    for signed in [true, false] {
        for equal in [true, false] {
            for halfword in [true, false] {
                reject_unpromoted_comparison(signed, equal, halfword)?;
            }
        }
    }
    Ok(())
}

fn reject_promoted_comparison_projection(
    signed: bool,
    equal: bool,
    halfword: bool,
) -> Result<(), String> {
    let (_, mut projection) =
        lowered_promoted_byte_comparison_fixture((0x80, 0x7f), signed, equal)?;
    let cmp = projection
        .functions
        .first_mut()
        .and_then(|function| function.blocks.first_mut())
        .and_then(|block| block.instructions.get_mut(6))
        .ok_or_else(|| String::from("promoted comparison projection absent"))?;
    let (InputInstruction::CompareEqual { left, right, .. }
    | InputInstruction::CompareNotEqual { left, right, .. }) = cmp
    else {
        return Err(String::from("projected comparison changed"));
    };
    *left = u32::from(halfword);
    *right = if halfword {
        4
    } else {
        3
    };
    if lower_typed_ir(&projection)
        != Err(TernaryLoweringError::UnsupportedInstruction)
    {
        return Err(String::from("unpromoted projection admitted by lowerer"));
    }
    Ok(())
}

#[test]
fn promoted_comparison_projection_requires_word_operands() -> Result<(), String>
{
    for signed in [true, false] {
        for equal in [true, false] {
            for halfword in [true, false] {
                reject_promoted_comparison_projection(signed, equal, halfword)?;
            }
        }
    }
    Ok(())
}

fn reject_promoted_comparison_checkpoint(
    signed: bool,
    equal: bool,
) -> Result<(), String> {
    let pair = (0x80, 0x7f);
    let (target, _) =
        lowered_promoted_byte_comparison_fixture(pair, signed, equal)?;
    let wire = assert_promoted_byte_checkpoint(pair, signed, equal, &target)?;
    let cmp_tag = match (signed, equal) {
        (true, true) => 35u8,
        (false, true) => 36,
        (true, false) => 37,
        (false, false) => 38,
    };
    let cmp_prefix = [cmp_tag, 2, 0, 0, 0, 6, 0, 0, 0, 5, 0, 0, 0];
    let cmp_offset = wire
        .windows(cmp_prefix.len())
        .position(|part| part == cmp_prefix)
        .ok_or_else(|| String::from("promoted comparison tag absent"))?;
    let cast_tag = if signed {
        82u8
    } else {
        83
    };
    let cast_offset = wire
        .windows(5)
        .position(|part| part == [cast_tag, 1, 0, 0, 0])
        .ok_or_else(|| String::from("promoted halfword tag absent"))?;
    let invalid = TernaryProgramCodecError::Validation(
        TernaryProgramValidationError::SsaValue,
    );
    let mutations = [
        (
            cmp_offset,
            if signed {
                cmp_tag.saturating_add(1)
            } else {
                cmp_tag.saturating_sub(1)
            },
            invalid,
        ),
        (cmp_offset.saturating_add(1), 99, invalid),
        (cmp_offset.saturating_add(5), 1, invalid),
        (
            cast_offset,
            if signed {
                83
            } else {
                82
            },
            invalid,
        ),
        (
            cast_offset,
            if signed {
                51
            } else {
                16
            },
            invalid,
        ),
        (cast_offset, 84, TernaryProgramCodecError::UnknownTag),
    ];
    check_promoted_wire_mutations(&wire, &mutations)
}

fn check_promoted_wire_mutations(
    wire: &[u8],
    mutations: &[PromotedWireMutation],
) -> Result<(), String> {
    for &(offset, replacement, expected) in mutations {
        let mut forged = wire.to_vec();
        *forged
            .get_mut(offset)
            .ok_or_else(|| String::from("forged checkpoint byte absent"))? =
            replacement;
        if canonical_ternary_program(&forged) != Err(expected) {
            return Err(format!(
                "promoted checkpoint forgery {offset} admitted"
            ));
        }
    }
    Ok(())
}

#[test]
fn promoted_comparison_decoder_rejects_width_and_ssa_forgery()
-> Result<(), String> {
    for signed in [true, false] {
        for equal in [true, false] {
            reject_promoted_comparison_checkpoint(signed, equal)?;
        }
    }
    Ok(())
}

#[test]
fn promoted_comparison_inspector_converges_on_boundary_bytes()
-> Result<(), String> {
    for (pair, suffix) in [((0x80u8, 0x7f), "ne"), ((0xff, 0xff), "eq")] {
        for signed in [true, false] {
            let (target, projection) =
                lowered_promoted_byte_comparison_fixture(
                    pair,
                    signed,
                    suffix == "eq",
                )?;
            let label = match (signed, suffix) {
                (true, "eq") => "signed-promotion-equal",
                (true, _) => "signed-promotion-not-equal",
                (false, "eq") => "unsigned-promotion-equal",
                (false, _) => "unsigned-promotion-not-equal",
            };
            assert_boolean_inspector_convergence(label, &target, &projection)?;
        }
    }
    Ok(())
}

#[test]
fn promoted_comparison_crash_boundaries_preserve_generation()
-> Result<(), String> {
    let previous = lowered_return_fixture()?;
    for signed in [true, false] {
        for equal in [true, false] {
            let (target, _) = lowered_promoted_byte_comparison_fixture(
                (0x80, 0x7f),
                signed,
                equal,
            )?;
            assert_boolean_crash_generation(&previous, &target)?;
        }
    }
    Ok(())
}

#[test]
fn promoted_comparison_inspector_rejects_forged_halfword_tag()
-> Result<(), String> {
    for (signed, equal, label) in [
        (true, true, "promoted-halfword-invalid-signed"),
        (false, false, "promoted-halfword-invalid-unsigned"),
    ] {
        let (target, _) = lowered_promoted_byte_comparison_fixture(
            (0x80, 0x7f),
            signed,
            equal,
        )?;
        let cast_tag = if signed {
            82
        } else {
            83
        };
        let reversed = if signed {
            83
        } else {
            82
        };
        assert_boolean_progress_tag_rejected(
            label,
            &target,
            (cast_tag, 1, reversed),
        )?;
    }
    Ok(())
}

fn typed_i8_return_module(bits: u8) -> Module {
    let block = BasicBlock::new(BasicBlockSpec {
        id: BlockId::new(0),
        instructions: vec![LocatedInstruction::new(
            Instruction::ConstantInteger {
                constant: IntegerConstant::new(8, vec![bits]),
                result: ValueId::new(0),
                type_id: TypeId::new(0),
            },
            fixture_span(0, 1),
        )],
        phis: Vec::new(),
        span: fixture_span(0, 2),
        terminator: Terminator::Return {
            value: Some(ValueId::new(0)),
        },
        terminator_span: fixture_span(1, 2),
    });
    let function = Function::new(FunctionSpec {
        blocks: vec![block],
        entry: BlockId::new(0),
        id: FunctionId::new(0),
        name: String::from("return_i8"),
        parameters: Vec::new(),
        signature: TypeId::new(1),
        span: fixture_span(0, 2),
    });
    Module::new(ModuleSpec {
        abi_id: String::from("malbolge-c32-v1"),
        format_version: typed_ir::TYPED_IR_VERSION,
        functions: vec![function],
        globals: Vec::new(),
        proof_obligations: Vec::new(),
        source_id: String::from("fixtures/return-i8.c"),
        source_sha256: [0x91; 32],
        target_profile: String::from("malbolge-2026"),
        types: vec![
            TypeEntry::new(TypeId::new(0), TypeDef::I8),
            TypeEntry::new(
                TypeId::new(1),
                TypeDef::function(Vec::new(), Some(TypeId::new(0)), false),
            ),
        ],
    })
}

#[test]
fn validated_typed_signed_byte_returns_lower_without_promotion()
-> Result<(), String> {
    for bits in u8::MIN..=u8::MAX {
        let module = typed_i8_return_module(bits);
        validate_module(&module)
            .map_err(|error| format!("admit typed i8 return: {error:?}"))?;
        let typed = canonical_bytes(&module)
            .map_err(|error| format!("encode typed i8 return: {error:?}"))?;
        if canonical_module(&typed) != Ok(module.clone()) {
            return Err(String::from("typed i8 return restoration drifted"));
        }
        let input = project_typed_ir(&module)?;
        let target = lower_typed_ir(&input)
            .map_err(|error| format!("lower typed i8 return: {error:?}"))?;
        assert_program_provenance(&module, &target)?;
        if canonical_ternary_program(
            &canonical_ternary_bytes(&target)
                .map_err(|error| format!("encode i8 return: {error:?}"))?,
        ) != Ok(target)
        {
            return Err(String::from("typed signed return checkpoint drifted"));
        }
    }
    Ok(())
}

fn signed_byte_truncate_types(signed: bool) -> Vec<TypeEntry> {
    vec![
        TypeEntry::new(
            TypeId::new(0),
            if signed {
                TypeDef::I32
            } else {
                TypeDef::U32
            },
        ),
        TypeEntry::new(TypeId::new(1), TypeDef::I8),
        TypeEntry::new(
            TypeId::new(2),
            TypeDef::function(Vec::new(), Some(TypeId::new(1)), false),
        ),
    ]
}

fn signed_byte_truncate_module(bits: u32, signed: bool) -> Module {
    let instructions = vec![
        LocatedInstruction::new(
            Instruction::ConstantInteger {
                constant: IntegerConstant::new(32, bits.to_le_bytes().to_vec()),
                result: ValueId::new(0),
                type_id: TypeId::new(0),
            },
            fixture_span(0, 1),
        ),
        LocatedInstruction::new(
            Instruction::Cast {
                operation: CastOp::Truncate,
                result: ValueId::new(1),
                type_id: TypeId::new(1),
                value: ValueId::new(0),
            },
            fixture_span(1, 2),
        ),
    ];
    Module::new(ModuleSpec {
        abi_id: String::from("malbolge-c32-v1"),
        format_version: typed_ir::TYPED_IR_VERSION,
        functions: vec![Function::new(FunctionSpec {
            blocks: vec![BasicBlock::new(BasicBlockSpec {
                id: BlockId::new(0),
                instructions,
                phis: Vec::new(),
                span: fixture_span(0, 3),
                terminator: Terminator::Return {
                    value: Some(ValueId::new(1)),
                },
                terminator_span: fixture_span(2, 3),
            })],
            entry: BlockId::new(0),
            id: FunctionId::new(0),
            name: String::from("truncate_signed_byte"),
            parameters: Vec::new(),
            signature: TypeId::new(2),
            span: fixture_span(0, 3),
        })],
        globals: Vec::new(),
        proof_obligations: Vec::new(),
        source_id: String::from("fixtures/truncate-signed-byte.c"),
        source_sha256: [0xcc; 32],
        target_profile: String::from("malbolge-2026"),
        types: signed_byte_truncate_types(signed),
    })
}

fn lowered_signed_byte_truncate_fixture(
    bits: u32,
    signed: bool,
) -> Result<LoweredByteFixture, String> {
    let module = signed_byte_truncate_module(bits, signed);
    validate_module(&module)
        .map_err(|error| format!("admit signed byte truncation: {error:?}"))?;
    let encoded = canonical_bytes(&module)
        .map_err(|error| format!("encode typed truncation: {error:?}"))?;
    let restored = canonical_module(&encoded)
        .map_err(|error| format!("restore typed truncation: {error:?}"))?;
    if restored != module {
        return Err(String::from("typed signed byte truncation drifted"));
    }
    let projection = project_typed_ir(&restored)?;
    let target = lower_typed_ir(&projection)
        .map_err(|error| format!("lower signed byte truncation: {error:?}"))?;
    assert_program_provenance(&restored, &target)?;
    Ok((target, projection))
}

fn assert_signed_byte_truncate_checkpoint(
    bits: u32,
    signed: bool,
    target: &ternary_lowering::TernaryProgram,
) -> Result<Vec<u8>, String> {
    let scalar = ternary_lowering::TernaryI32Scalar::from_bits(bits);
    let materialize = if signed {
        TernaryOperation::MaterializeI32 {
            result: 0,
            scalar,
            span: output_span(fixture_span(0, 1)),
        }
    } else {
        TernaryOperation::MaterializeU32 {
            result: 0,
            scalar,
            span: output_span(fixture_span(0, 1)),
        }
    };
    let truncate = if signed {
        TernaryOperation::TruncateI32ToI8 {
            result: 1,
            span: output_span(fixture_span(1, 2)),
            value: 0,
        }
    } else {
        TernaryOperation::TruncateU32ToI8 {
            result: 1,
            span: output_span(fixture_span(1, 2)),
            value: 0,
        }
    };
    let expected = [materialize, truncate, TernaryOperation::ReturnI8 {
        span: output_span(fixture_span(2, 3)),
        value: 1,
    }];
    if target
        .functions
        .first()
        .map(|function| function.operations.as_slice())
        != Some(expected.as_slice())
    {
        return Err(String::from("signed truncate SSA or spans drifted"));
    }
    let wire = canonical_ternary_bytes(target)
        .map_err(|error| format!("encode signed truncate: {error:?}"))?;
    let tag = if signed {
        58u8
    } else {
        59
    };
    if !wire.windows(5).any(|part| part == [tag, 1, 0, 0, 0])
        || canonical_ternary_program(&wire) != Ok(target.clone())
    {
        return Err(String::from("signed truncate checkpoint drifted"));
    }
    Ok(wire)
}

fn verify_signed_byte_truncation_case(
    word: u32,
    signed: bool,
) -> Result<(), String> {
    let (target, input) = lowered_signed_byte_truncate_fixture(word, signed)?;
    if input.functions.first().map(|function| function.return_kind)
        != Some(InputScalarType::I8)
    {
        return Err(String::from("signed truncation return drifted"));
    }
    let _wire = assert_signed_byte_truncate_checkpoint(word, signed, &target)?;
    Ok(())
}

#[test]
fn typed_signed_byte_truncation_preserves_all_low_byte_bits()
-> Result<(), String> {
    for bits in u8::MIN..=u8::MAX {
        for upper in [0u32, 0x8000_0000, 0xffff_ff00] {
            for signed in [true, false] {
                verify_signed_byte_truncation_case(
                    upper | u32::from(bits),
                    signed,
                )?;
            }
        }
    }
    Ok(())
}

fn reject_signed_byte_truncation_wire(
    bits: u32,
    signed: bool,
) -> Result<(), String> {
    let (target, _input) = lowered_signed_byte_truncate_fixture(bits, signed)?;
    let wire = assert_signed_byte_truncate_checkpoint(bits, signed, &target)?;
    let tag = if signed {
        58u8
    } else {
        59
    };
    let offset = wire
        .windows(5)
        .position(|part| part == [tag, 1, 0, 0, 0])
        .ok_or_else(|| String::from("truncate tag offset absent"))?;
    let wrong_source = if signed {
        59u8
    } else {
        58
    };
    let wrong_destination = if signed {
        5u8
    } else {
        15
    };
    let invalid_ssa = TernaryProgramCodecError::Validation(
        TernaryProgramValidationError::SsaValue,
    );
    for (displacement, replacement, expected) in [
        (0usize, wrong_source, invalid_ssa),
        (0, wrong_destination, invalid_ssa),
        (0, 84, TernaryProgramCodecError::UnknownTag),
        (1, 0, invalid_ssa),
        (29, 99, invalid_ssa),
    ] {
        let mut forged = wire.clone();
        *forged
            .get_mut(offset.saturating_add(displacement))
            .ok_or_else(|| String::from("truncate wire field absent"))? =
            replacement;
        if canonical_ternary_program(&forged) != Err(expected) {
            return Err(format!(
                "signed truncate {displacement}/{replacement} admitted"
            ));
        }
    }
    let mut truncated = wire;
    let _discarded = truncated.pop();
    if canonical_ternary_program(&truncated)
        != Err(TernaryProgramCodecError::Truncated)
    {
        return Err(String::from("incomplete signed truncation admitted"));
    }
    Ok(())
}

#[test]
fn signed_byte_truncation_decoder_rejects_wrong_source_and_kind()
-> Result<(), String> {
    for bits in [0u32, 0x7f, 0x80, 0xff, 0x8000_0080, u32::MAX] {
        for signed in [true, false] {
            reject_signed_byte_truncation_wire(bits, signed)?;
        }
    }
    Ok(())
}

fn reject_signed_byte_truncation_projection(
    signed: bool,
    variation: u8,
) -> Result<(), String> {
    let (_target, mut projection) =
        lowered_signed_byte_truncate_fixture(0x8000_0080, signed)?;
    let Some(function) = projection.functions.first_mut() else {
        return Err(String::from("truncate projection function absent"));
    };
    let Some(block) = function.blocks.first_mut() else {
        return Err(String::from("truncate projection block absent"));
    };
    let Some(InputInstruction::TruncateInteger {
        result,
        type_kind,
        value,
        ..
    }) = block.instructions.get_mut(1)
    else {
        return Err(String::from("truncate projection instruction absent"));
    };
    match variation {
        0 => *type_kind = InputScalarType::U8,
        1 => *value = 99,
        2 => *result = 0,
        _ => return Err(String::from("invalid truncate projection case")),
    }
    let expected = match variation {
        0 => TernaryLoweringError::UnsupportedTerminator,
        1 => TernaryLoweringError::UnsupportedInstruction,
        _ => TernaryLoweringError::InvalidProjection,
    };
    if lower_typed_ir(&projection) != Err(expected) {
        return Err(format!("forged signed truncate {variation} admitted"));
    }
    Ok(())
}

#[test]
fn signed_byte_truncation_rejects_forged_projection_kinds_and_ssa()
-> Result<(), String> {
    for signed in [true, false] {
        for variation in 0u8..3 {
            reject_signed_byte_truncation_projection(signed, variation)?;
        }
    }
    Ok(())
}

#[test]
fn signed_byte_truncation_inspector_and_crash_recovery() -> Result<(), String> {
    let previous = lowered_return_fixture()?;
    for bits in [0u32, 0x7f, 0x80, 0xff, 0x8000_0080, u32::MAX] {
        for signed in [true, false] {
            let (target, projection) =
                lowered_signed_byte_truncate_fixture(bits, signed)?;
            let label = if signed {
                "signed-word-to-signed-byte"
            } else {
                "unsigned-word-to-signed-byte"
            };
            assert_boolean_inspector_convergence(label, &target, &projection)?;
            assert_boolean_crash_generation(&previous, &target)?;
        }
    }
    Ok(())
}

#[test]
fn signed_byte_truncation_inspector_rejects_cross_kind_and_unknown()
-> Result<(), String> {
    for signed in [true, false] {
        let (target, _projection) =
            lowered_signed_byte_truncate_fixture(0x8000_0080, signed)?;
        let tag = if signed {
            58u8
        } else {
            59
        };
        let foreign = if signed {
            59u8
        } else {
            58
        };
        let label = if signed {
            "forged-signed-word-byte-truncate"
        } else {
            "forged-unsigned-word-byte-truncate"
        };
        assert_boolean_progress_tag_rejected(
            label,
            &target,
            (tag, 1, foreign),
        )?;
        assert_boolean_progress_tag_rejected(
            "unknown-signed-byte-truncate",
            &target,
            (tag, 1, 84),
        )?;
    }
    Ok(())
}

fn signed_byte_extension_types() -> Vec<TypeEntry> {
    vec![
        TypeEntry::new(TypeId::new(0), TypeDef::I8),
        TypeEntry::new(TypeId::new(1), TypeDef::I32),
        TypeEntry::new(
            TypeId::new(2),
            TypeDef::function(Vec::new(), Some(TypeId::new(1)), false),
        ),
    ]
}

fn signed_byte_extension_module(bits: u8) -> Module {
    let instructions = vec![
        LocatedInstruction::new(
            Instruction::ConstantInteger {
                constant: IntegerConstant::new(8, vec![bits]),
                result: ValueId::new(0),
                type_id: TypeId::new(0),
            },
            fixture_span(0, 1),
        ),
        LocatedInstruction::new(
            Instruction::Cast {
                operation: CastOp::SignExtend,
                result: ValueId::new(1),
                type_id: TypeId::new(1),
                value: ValueId::new(0),
            },
            fixture_span(1, 2),
        ),
    ];
    Module::new(ModuleSpec {
        abi_id: String::from("malbolge-c32-v1"),
        format_version: typed_ir::TYPED_IR_VERSION,
        functions: vec![Function::new(FunctionSpec {
            blocks: vec![BasicBlock::new(BasicBlockSpec {
                id: BlockId::new(0),
                instructions,
                phis: Vec::new(),
                span: fixture_span(0, 3),
                terminator: Terminator::Return {
                    value: Some(ValueId::new(1)),
                },
                terminator_span: fixture_span(2, 3),
            })],
            entry: BlockId::new(0),
            id: FunctionId::new(0),
            name: String::from("sign_extend_byte"),
            parameters: Vec::new(),
            signature: TypeId::new(2),
            span: fixture_span(0, 3),
        })],
        globals: Vec::new(),
        proof_obligations: Vec::new(),
        source_id: String::from("fixtures/sign-extend-byte.c"),
        source_sha256: [0xed; 32],
        target_profile: String::from("malbolge-2026"),
        types: signed_byte_extension_types(),
    })
}

fn signed_byte_truth_types() -> Vec<TypeEntry> {
    vec![
        TypeEntry::new(TypeId::new(0), TypeDef::I8),
        TypeEntry::new(TypeId::new(1), TypeDef::Bool),
        TypeEntry::new(
            TypeId::new(2),
            TypeDef::function(Vec::new(), Some(TypeId::new(1)), false),
        ),
    ]
}

fn signed_byte_truth_module(bits: u8) -> Module {
    let instructions = vec![
        LocatedInstruction::new(
            Instruction::ConstantInteger {
                constant: IntegerConstant::new(8, vec![bits]),
                result: ValueId::new(0),
                type_id: TypeId::new(0),
            },
            fixture_span(0, 1),
        ),
        LocatedInstruction::new(
            Instruction::Cast {
                operation: CastOp::IntegerToBool,
                result: ValueId::new(1),
                type_id: TypeId::new(1),
                value: ValueId::new(0),
            },
            fixture_span(1, 2),
        ),
    ];
    Module::new(ModuleSpec {
        abi_id: String::from("malbolge-c32-v1"),
        format_version: typed_ir::TYPED_IR_VERSION,
        functions: vec![Function::new(FunctionSpec {
            blocks: vec![BasicBlock::new(BasicBlockSpec {
                id: BlockId::new(0),
                instructions,
                phis: Vec::new(),
                span: fixture_span(0, 3),
                terminator: Terminator::Return {
                    value: Some(ValueId::new(1)),
                },
                terminator_span: fixture_span(2, 3),
            })],
            entry: BlockId::new(0),
            id: FunctionId::new(0),
            name: String::from("signed_byte_truth"),
            parameters: Vec::new(),
            signature: TypeId::new(2),
            span: fixture_span(0, 3),
        })],
        globals: Vec::new(),
        proof_obligations: Vec::new(),
        source_id: String::from("fixtures/signed-byte-truth.c"),
        source_sha256: [0xef; 32],
        target_profile: String::from("malbolge-2026"),
        types: signed_byte_truth_types(),
    })
}

fn signed_byte_bitcast_types(
    signed_origin: bool,
    same_kind: bool,
) -> Vec<TypeEntry> {
    let return_type = TypeId::new(if signed_origin == same_kind {
        2
    } else {
        3
    });
    vec![
        TypeEntry::new(TypeId::new(0), TypeDef::I8),
        TypeEntry::new(TypeId::new(1), TypeDef::U8),
        TypeEntry::new(TypeId::new(2), TypeDef::I32),
        TypeEntry::new(TypeId::new(3), TypeDef::U32),
        TypeEntry::new(
            TypeId::new(4),
            TypeDef::function(Vec::new(), Some(return_type), false),
        ),
    ]
}

fn signed_byte_bitcast_instructions(
    bits: u8,
    signed_origin: bool,
    same_kind: bool,
) -> Vec<LocatedInstruction> {
    let source_type = TypeId::new(u32::from(!signed_origin));
    let destination_signed = signed_origin == same_kind;
    let middle_type = TypeId::new(u32::from(!destination_signed));
    let extension_type = TypeId::new(if destination_signed {
        2
    } else {
        3
    });
    let extension = if destination_signed {
        CastOp::SignExtend
    } else {
        CastOp::ZeroExtend
    };
    vec![
        LocatedInstruction::new(
            Instruction::ConstantInteger {
                constant: IntegerConstant::new(8, vec![bits]),
                result: ValueId::new(0),
                type_id: source_type,
            },
            fixture_span(0, 1),
        ),
        LocatedInstruction::new(
            Instruction::Cast {
                operation: CastOp::IntegerBitcast,
                result: ValueId::new(1),
                type_id: middle_type,
                value: ValueId::new(0),
            },
            fixture_span(1, 2),
        ),
        LocatedInstruction::new(
            Instruction::Cast {
                operation: extension,
                result: ValueId::new(2),
                type_id: extension_type,
                value: ValueId::new(1),
            },
            fixture_span(2, 3),
        ),
    ]
}

fn signed_byte_bitcast_module(bits: u8, signed_origin: bool) -> Module {
    byte_bitcast_module(bits, signed_origin, false)
}

fn same_kind_byte_bitcast_module(bits: u8, signed_origin: bool) -> Module {
    byte_bitcast_module(bits, signed_origin, true)
}

fn byte_bitcast_module(
    bits: u8,
    signed_origin: bool,
    same_kind: bool,
) -> Module {
    Module::new(ModuleSpec {
        abi_id: String::from("malbolge-c32-v1"),
        format_version: typed_ir::TYPED_IR_VERSION,
        functions: vec![Function::new(FunctionSpec {
            blocks: vec![BasicBlock::new(BasicBlockSpec {
                id: BlockId::new(0),
                instructions: signed_byte_bitcast_instructions(
                    bits,
                    signed_origin,
                    same_kind,
                ),
                phis: Vec::new(),
                span: fixture_span(0, 4),
                terminator: Terminator::Return {
                    value: Some(ValueId::new(2)),
                },
                terminator_span: fixture_span(3, 4),
            })],
            entry: BlockId::new(0),
            id: FunctionId::new(0),
            name: String::from("signed_byte_bitcast"),
            parameters: Vec::new(),
            signature: TypeId::new(4),
            span: fixture_span(0, 4),
        })],
        globals: Vec::new(),
        proof_obligations: Vec::new(),
        source_id: String::from("fixtures/signed-byte-bitcast.c"),
        source_sha256: [0xdb; 32],
        target_profile: String::from("malbolge-2026"),
        types: signed_byte_bitcast_types(signed_origin, same_kind),
    })
}

fn bool_to_signed_byte_instructions(
    bit: u8,
    widen: bool,
) -> Vec<LocatedInstruction> {
    let mut instructions = vec![
        LocatedInstruction::new(
            Instruction::ConstantInteger {
                constant: IntegerConstant::new(1, vec![bit]),
                result: ValueId::new(0),
                type_id: TypeId::new(0),
            },
            fixture_span(0, 1),
        ),
        LocatedInstruction::new(
            Instruction::Cast {
                operation: CastOp::BoolToSigned,
                result: ValueId::new(1),
                type_id: TypeId::new(1),
                value: ValueId::new(0),
            },
            fixture_span(1, 2),
        ),
    ];
    if widen {
        instructions.push(LocatedInstruction::new(
            Instruction::Cast {
                operation: CastOp::SignExtend,
                result: ValueId::new(2),
                type_id: TypeId::new(2),
                value: ValueId::new(1),
            },
            fixture_span(2, 3),
        ));
    }
    instructions
}

fn bool_to_signed_byte_module(bit: u8, widen: bool) -> Module {
    let instructions = bool_to_signed_byte_instructions(bit, widen);
    let (end, return_id, last_begin) = if widen {
        (4, 2, 3)
    } else {
        (3, 1, 2)
    };
    let return_type = if widen {
        TypeId::new(2)
    } else {
        TypeId::new(1)
    };
    Module::new(ModuleSpec {
        abi_id: String::from("malbolge-c32-v1"),
        format_version: typed_ir::TYPED_IR_VERSION,
        functions: vec![Function::new(FunctionSpec {
            blocks: vec![BasicBlock::new(BasicBlockSpec {
                id: BlockId::new(0),
                instructions,
                phis: Vec::new(),
                span: fixture_span(0, end),
                terminator: Terminator::Return {
                    value: Some(ValueId::new(return_id)),
                },
                terminator_span: fixture_span(last_begin, end),
            })],
            entry: BlockId::new(0),
            id: FunctionId::new(0),
            name: String::from("bool_to_signed_byte"),
            parameters: Vec::new(),
            signature: TypeId::new(3),
            span: fixture_span(0, end),
        })],
        globals: Vec::new(),
        proof_obligations: Vec::new(),
        source_id: String::from("fixtures/bool-to-i8.c"),
        source_sha256: [0x60; 32],
        target_profile: String::from("malbolge-2026"),
        types: vec![
            TypeEntry::new(TypeId::new(0), TypeDef::Bool),
            TypeEntry::new(TypeId::new(1), TypeDef::I8),
            TypeEntry::new(TypeId::new(2), TypeDef::I32),
            TypeEntry::new(
                TypeId::new(3),
                TypeDef::function(Vec::new(), Some(return_type), false),
            ),
        ],
    })
}

fn lowered_bool_to_signed_byte_fixture(
    bit: u8,
    widen: bool,
) -> Result<LoweredByteFixture, String> {
    let module = bool_to_signed_byte_module(bit, widen);
    validate_module(&module)
        .map_err(|error| format!("admit bool to i8: {error:?}"))?;
    let encoded = canonical_bytes(&module)
        .map_err(|error| format!("encode bool to i8: {error:?}"))?;
    let restored = canonical_module(&encoded)
        .map_err(|error| format!("decode bool to i8: {error:?}"))?;
    if restored != module {
        return Err(String::from("bool to i8 typed IR drifted"));
    }
    let projection = project_typed_ir(&restored)?;
    let target = lower_typed_ir(&projection)
        .map_err(|error| format!("lower bool to i8: {error:?}"))?;
    assert_program_provenance(&restored, &target)?;
    Ok((target, projection))
}

fn bool_to_i8_expected_operations(
    bit: u8,
    widen: bool,
) -> Vec<TernaryOperation> {
    let mut expected = vec![
        TernaryOperation::MaterializeBool {
            result: 0,
            value: bit == 1,
            span: output_span(fixture_span(0, 1)),
        },
        TernaryOperation::BoolToI8 {
            result: 1,
            value: 0,
            span: output_span(fixture_span(1, 2)),
        },
    ];
    if widen {
        expected.push(TernaryOperation::SignExtendI8ToI32 {
            result: 2,
            value: 1,
            span: output_span(fixture_span(2, 3)),
        });
        expected.push(TernaryOperation::Return {
            span: output_span(fixture_span(3, 4)),
            value: 2,
        });
    } else {
        expected.push(TernaryOperation::ReturnI8 {
            span: output_span(fixture_span(2, 3)),
            value: 1,
        });
    }
    expected
}

fn assert_bool_to_i8_checkpoint(
    bit: u8,
    widen: bool,
    target: &ternary_lowering::TernaryProgram,
) -> Result<Vec<u8>, String> {
    let expected = bool_to_i8_expected_operations(bit, widen);
    if target
        .functions
        .first()
        .map(|function| function.operations.as_slice())
        != Some(expected.as_slice())
    {
        return Err(String::from("bool to signed byte SSA drifted"));
    }
    let wire = canonical_ternary_bytes(target)
        .map_err(|error| format!("encode bool to signed byte: {error:?}"))?;
    if !wire.windows(5).any(|part| part == [60, 1, 0, 0, 0])
        || canonical_ternary_program(&wire) != Ok(target.clone())
    {
        return Err(String::from("bool to i8 checkpoint drifted"));
    }
    Ok(wire)
}

#[test]
fn typed_boolean_constants_cast_to_signed_byte_without_host_values()
-> Result<(), String> {
    for bit in [0u8, 1u8] {
        for widen in [false, true] {
            let (target, input) =
                lowered_bool_to_signed_byte_fixture(bit, widen)?;
            let expected_kind = if widen {
                InputScalarType::I32
            } else {
                InputScalarType::I8
            };
            if input.functions.first().map(|function| function.return_kind)
                != Some(expected_kind)
            {
                return Err(String::from(
                    "bool to signed byte return kind drifted",
                ));
            }
            let _wire = assert_bool_to_i8_checkpoint(bit, widen, &target)?;
        }
    }
    Ok(())
}

fn reject_bool_to_i8_wire_mutations(
    bit: u8,
    widen: bool,
) -> Result<(), String> {
    let (target, _) = lowered_bool_to_signed_byte_fixture(bit, widen)?;
    let wire = assert_bool_to_i8_checkpoint(bit, widen, &target)?;
    let offset = wire
        .windows(5)
        .position(|part| part == [60, 1, 0, 0, 0])
        .ok_or_else(|| String::from("bool to i8 cast record absent"))?;
    let invalid = TernaryProgramCodecError::Validation(
        TernaryProgramValidationError::SsaValue,
    );
    for (displacement, replacement, expected) in [
        (0usize, 44u8, invalid),
        (0, 52, invalid),
        (0, 84, TernaryProgramCodecError::UnknownTag),
        (1, 0, invalid),
        (29, 99, invalid),
    ] {
        let mut forged = wire.clone();
        *forged
            .get_mut(offset.saturating_add(displacement))
            .ok_or_else(|| String::from("bool to i8 field absent"))? =
            replacement;
        if canonical_ternary_program(&forged) != Err(expected) {
            return Err(format!(
                "bool to i8 {displacement}/{replacement} admitted"
            ));
        }
    }
    Ok(())
}

#[test]
fn bool_to_signed_byte_wire_rejects_kind_and_identity_forgery()
-> Result<(), String> {
    for bit in [0u8, 1] {
        for widen in [false, true] {
            reject_bool_to_i8_wire_mutations(bit, widen)?;
        }
    }
    Ok(())
}

fn reject_bool_to_i8_projection(bit: u8, variation: u8) -> Result<(), String> {
    let (_, mut input) = lowered_bool_to_signed_byte_fixture(bit, false)?;
    let cast = input
        .functions
        .first_mut()
        .and_then(|function| function.blocks.first_mut())
        .and_then(|block| block.instructions.get_mut(1))
        .ok_or_else(|| String::from("bool to i8 projection cast absent"))?;
    let InputInstruction::BoolToSigned {
        result, type_kind, value, ..
    } = cast
    else {
        return Err(String::from("bool to i8 cast kind drifted"));
    };
    match variation {
        0 => *type_kind = InputScalarType::U8,
        1 => *value = 99,
        2 => *result = 0,
        _ => return Err(String::from("invalid bool to i8 forgery")),
    }
    let failure = if variation == 2 {
        TernaryLoweringError::InvalidProjection
    } else {
        TernaryLoweringError::UnsupportedInstruction
    };
    if lower_typed_ir(&input) != Err(failure) {
        return Err(format!(
            "forged bool to i8 projection {variation} admitted"
        ));
    }
    Ok(())
}

#[test]
fn bool_to_signed_byte_projection_rejects_undefined_and_retyped_uses()
-> Result<(), String> {
    for bit in [0u8, 1] {
        for variation in 0u8..3 {
            reject_bool_to_i8_projection(bit, variation)?;
        }
    }
    Ok(())
}

#[test]
fn bool_to_signed_byte_inspector_and_crash_restore_exact_ssa()
-> Result<(), String> {
    let previous = lowered_return_fixture()?;
    for bit in [0u8, 1] {
        for widen in [false, true] {
            let (target, input) =
                lowered_bool_to_signed_byte_fixture(bit, widen)?;
            let label = if widen {
                "bool-to-i8-to-i32"
            } else {
                "bool-to-i8-direct"
            };
            assert_boolean_inspector_convergence(label, &target, &input)?;
            assert_boolean_crash_generation(&previous, &target)?;
        }
    }
    Ok(())
}

#[test]
fn bool_to_i8_inspector_rejects_forged_tags() -> Result<(), String> {
    for bit in [0u8, 1] {
        let (target, _input) = lowered_bool_to_signed_byte_fixture(bit, false)?;
        assert_boolean_progress_tag_rejected(
            "bool-to-i8-forged-wide",
            &target,
            (60, 1, 44),
        )?;
        assert_boolean_progress_tag_rejected(
            "bool-to-i8-unknown",
            &target,
            (60, 1, 84),
        )?;
    }
    Ok(())
}

fn comparison_to_i8_types(signed: bool) -> Vec<TypeEntry> {
    vec![
        TypeEntry::new(
            TypeId::new(0),
            if signed {
                TypeDef::I32
            } else {
                TypeDef::U32
            },
        ),
        TypeEntry::new(TypeId::new(1), TypeDef::Bool),
        TypeEntry::new(TypeId::new(2), TypeDef::I8),
        TypeEntry::new(
            TypeId::new(3),
            TypeDef::function(Vec::new(), Some(TypeId::new(2)), false),
        ),
    ]
}

fn comparison_to_i8_instructions(
    pair: (u32, u32),
    equal: bool,
) -> Vec<LocatedInstruction> {
    let (left, right) = pair;
    let comparison = if equal {
        CompareOp::Equal
    } else {
        CompareOp::NotEqual
    };
    vec![
        low_byte_constant(left, 0, 0, TypeId::new(0)),
        low_byte_constant(right, 1, 1, TypeId::new(0)),
        LocatedInstruction::new(
            Instruction::Compare {
                left: ValueId::new(0),
                operation: comparison,
                result: ValueId::new(2),
                right: ValueId::new(1),
                type_id: TypeId::new(1),
            },
            fixture_span(2, 3),
        ),
        LocatedInstruction::new(
            Instruction::Cast {
                operation: CastOp::BoolToSigned,
                result: ValueId::new(3),
                type_id: TypeId::new(2),
                value: ValueId::new(2),
            },
            fixture_span(3, 4),
        ),
    ]
}

fn comparison_to_i8_module(
    signed: bool,
    equal: bool,
    pair: (u32, u32),
) -> Module {
    let instructions = comparison_to_i8_instructions(pair, equal);
    Module::new(ModuleSpec {
        abi_id: String::from("malbolge-c32-v1"),
        format_version: typed_ir::TYPED_IR_VERSION,
        functions: vec![Function::new(FunctionSpec {
            blocks: vec![BasicBlock::new(BasicBlockSpec {
                id: BlockId::new(0),
                instructions,
                phis: Vec::new(),
                span: fixture_span(0, 5),
                terminator: Terminator::Return {
                    value: Some(ValueId::new(3)),
                },
                terminator_span: fixture_span(4, 5),
            })],
            entry: BlockId::new(0),
            id: FunctionId::new(0),
            name: String::from("compare_to_signed_byte"),
            parameters: Vec::new(),
            signature: TypeId::new(3),
            span: fixture_span(0, 5),
        })],
        globals: Vec::new(),
        proof_obligations: Vec::new(),
        source_id: String::from("fixtures/compare-to-i8.c"),
        source_sha256: [0x65; 32],
        target_profile: String::from("malbolge-2026"),
        types: comparison_to_i8_types(signed),
    })
}

fn lowered_comparison_to_i8_fixture(
    signed: bool,
    equal: bool,
    pair: (u32, u32),
) -> Result<LoweredByteFixture, String> {
    let module = comparison_to_i8_module(signed, equal, pair);
    validate_module(&module)
        .map_err(|error| format!("admit compare to i8: {error:?}"))?;
    let encoded = canonical_bytes(&module)
        .map_err(|error| format!("encode compare to i8: {error:?}"))?;
    let restored = canonical_module(&encoded)
        .map_err(|error| format!("restore compare to i8: {error:?}"))?;
    if restored != module {
        return Err(String::from("compare-to-i8 typed IR drifted"));
    }
    let projection = project_typed_ir(&restored)?;
    let target = lower_typed_ir(&projection)
        .map_err(|error| format!("lower compare to i8: {error:?}"))?;
    assert_program_provenance(&restored, &target)?;
    Ok((target, projection))
}

const fn expected_compare_to_i8_operation(
    signed: bool,
    equal: bool,
) -> TernaryOperation {
    let (left, result, right, span) =
        (0, 2, 1, output_span(fixture_span(2, 3)));
    match (signed, equal) {
        (true, true) => TernaryOperation::EqualI32 {
            left,
            result,
            right,
            span,
        },
        (false, true) => TernaryOperation::EqualU32 {
            left,
            result,
            right,
            span,
        },
        (true, false) => TernaryOperation::NotEqualI32 {
            left,
            result,
            right,
            span,
        },
        (false, false) => TernaryOperation::NotEqualU32 {
            left,
            result,
            right,
            span,
        },
    }
}

fn assert_compared_bool_to_i8_checkpoint(
    signed: bool,
    equal: bool,
    target: &ternary_lowering::TernaryProgram,
) -> Result<Vec<u8>, String> {
    let operations = &target
        .functions
        .first()
        .ok_or_else(|| String::from("compare-to-i8 target missing"))?
        .operations;
    if operations.get(2)
        != Some(&expected_compare_to_i8_operation(signed, equal))
        || operations.get(3)
            != Some(&TernaryOperation::BoolToI8 {
                result: 3,
                span: output_span(fixture_span(3, 4)),
                value: 2,
            })
        || operations.last()
            != Some(&TernaryOperation::ReturnI8 {
                span: output_span(fixture_span(4, 5)),
                value: 3,
            })
    {
        return Err(String::from("compare-to-i8 SSA chain drifted"));
    }
    let wire = canonical_ternary_bytes(target)
        .map_err(|error| format!("encode compare-to-i8 target: {error:?}"))?;
    if !wire.windows(5).any(|part| part == [60, 3, 0, 0, 0])
        || canonical_ternary_program(&wire) != Ok(target.clone())
    {
        return Err(String::from("compare-to-i8 canonical wire drifted"));
    }
    Ok(wire)
}

#[test]
fn typed_comparisons_preserve_boolean_to_signed_byte_ssa_chain()
-> Result<(), String> {
    for (signed, equal) in
        [(true, true), (true, false), (false, true), (false, false)]
    {
        for pair in [
            (0u32, 0u32),
            (0, 1),
            (u32::MAX, 0),
            (u32::MAX, u32::MAX),
            (0x8000_0000, u32::MAX),
        ] {
            let (target, input) =
                lowered_comparison_to_i8_fixture(signed, equal, pair)?;
            if input.functions.first().map(|function| function.return_kind)
                != Some(InputScalarType::I8)
            {
                return Err(String::from("compare-to-i8 return kind drifted"));
            }
            let _wire =
                assert_compared_bool_to_i8_checkpoint(signed, equal, &target)?;
        }
    }
    Ok(())
}

fn reject_compared_bool_to_i8_wire_mutations(
    signed: bool,
    equal: bool,
) -> Result<(), String> {
    let (target, _projection) = lowered_comparison_to_i8_fixture(
        signed,
        equal,
        (0x8000_0000, u32::MAX),
    )?;
    let wire = assert_compared_bool_to_i8_checkpoint(signed, equal, &target)?;
    let comparison_tag = match (signed, equal) {
        (true, true) => 35u8,
        (false, true) => 36,
        (true, false) => 37,
        (false, false) => 38,
    };
    let swapped = if signed {
        comparison_tag.saturating_add(1)
    } else {
        comparison_tag.saturating_sub(1)
    };
    let compare_prefix = [comparison_tag, 0, 0, 0, 0, 2, 0, 0, 0, 1, 0, 0, 0];
    let comparison_offset = wire
        .windows(compare_prefix.len())
        .position(|part| part == compare_prefix)
        .ok_or_else(|| String::from("comparison-to-i8 record absent"))?;
    let cast_offset = wire
        .windows(5)
        .position(|part| part == [60, 3, 0, 0, 0])
        .ok_or_else(|| String::from("comparison-to-i8 cast absent"))?;
    let failure = TernaryProgramCodecError::Validation(
        TernaryProgramValidationError::SsaValue,
    );
    for (offset, replacement, expected) in [
        (comparison_offset, swapped, failure),
        (cast_offset, 44, failure),
        (cast_offset, 84, TernaryProgramCodecError::UnknownTag),
        (cast_offset.saturating_add(29), 99, failure),
    ] {
        let mut forged = wire.clone();
        *forged.get_mut(offset).ok_or_else(|| {
            String::from("forged compare-to-i8 offset absent")
        })? = replacement;
        if canonical_ternary_program(&forged) != Err(expected) {
            return Err(format!(
                "compare-to-i8 offset {offset} retag {replacement} admitted"
            ));
        }
    }
    Ok(())
}

#[test]
fn compared_boolean_to_i8_rejects_cross_signedness_and_ssa_forgeries()
-> Result<(), String> {
    for (signed, equal) in
        [(true, true), (true, false), (false, true), (false, false)]
    {
        reject_compared_bool_to_i8_wire_mutations(signed, equal)?;
    }
    Ok(())
}

#[test]
fn compared_boolean_to_i8_inspector_and_crash_recovery() -> Result<(), String> {
    let previous = lowered_return_fixture()?;
    for (signed, equal) in
        [(true, true), (true, false), (false, true), (false, false)]
    {
        for pair in [(0u32, 0u32), (0x8000_0000, u32::MAX)] {
            let (target, projection) =
                lowered_comparison_to_i8_fixture(signed, equal, pair)?;
            let label = if signed {
                "signed-comparison-to-i8"
            } else {
                "unsigned-comparison-to-i8"
            };
            assert_boolean_inspector_convergence(label, &target, &projection)?;
            assert_boolean_crash_generation(&previous, &target)?;
        }
    }
    Ok(())
}

fn boolean_constant_types(return_type: TypeId) -> Vec<TypeEntry> {
    vec![
        TypeEntry::new(TypeId::new(0), TypeDef::Bool),
        TypeEntry::new(TypeId::new(1), TypeDef::I32),
        TypeEntry::new(
            TypeId::new(2),
            TypeDef::function(Vec::new(), Some(return_type), false),
        ),
    ]
}

fn boolean_constant_module(bit: u8, promoted: bool) -> Module {
    let bool_type = TypeId::new(0);
    let signed_type = TypeId::new(1);
    let signature = TypeId::new(2);
    let return_type = if promoted {
        signed_type
    } else {
        bool_type
    };
    let mut instructions = vec![LocatedInstruction::new(
        Instruction::ConstantInteger {
            constant: IntegerConstant::new(1, vec![bit]),
            result: ValueId::new(0),
            type_id: bool_type,
        },
        fixture_span(0, 1),
    )];
    if promoted {
        instructions.push(LocatedInstruction::new(
            Instruction::Cast {
                operation: CastOp::BoolToSigned,
                result: ValueId::new(1),
                type_id: signed_type,
                value: ValueId::new(0),
            },
            fixture_span(1, 2),
        ));
    }
    let end = if promoted {
        3
    } else {
        2
    };
    Module::new(ModuleSpec {
        abi_id: String::from("malbolge-c32-v1"),
        format_version: typed_ir::TYPED_IR_VERSION,
        functions: vec![Function::new(FunctionSpec {
            blocks: vec![BasicBlock::new(BasicBlockSpec {
                id: BlockId::new(0),
                instructions,
                phis: Vec::new(),
                span: fixture_span(0, end),
                terminator: Terminator::Return {
                    value: Some(ValueId::new(u32::from(promoted))),
                },
                terminator_span: fixture_span(end.saturating_sub(1), end),
            })],
            entry: BlockId::new(0),
            id: FunctionId::new(0),
            name: String::from("boolean_constant"),
            parameters: Vec::new(),
            signature,
            span: fixture_span(0, end),
        })],
        globals: Vec::new(),
        proof_obligations: Vec::new(),
        source_id: String::from("fixtures/boolean-constant.c"),
        source_sha256: [0xab; 32],
        target_profile: String::from("malbolge-2026"),
        types: boolean_constant_types(return_type),
    })
}

fn boolean_roundtrip_types() -> Vec<TypeEntry> {
    vec![
        TypeEntry::new(TypeId::new(0), TypeDef::Bool),
        TypeEntry::new(TypeId::new(1), TypeDef::I32),
        TypeEntry::new(TypeId::new(2), TypeDef::U8),
        TypeEntry::new(
            TypeId::new(3),
            TypeDef::function(Vec::new(), Some(TypeId::new(1)), false),
        ),
    ]
}

fn boolean_roundtrip_instructions(bit: u8) -> Vec<LocatedInstruction> {
    vec![
        LocatedInstruction::new(
            Instruction::ConstantInteger {
                constant: IntegerConstant::new(1, vec![bit]),
                result: ValueId::new(0),
                type_id: TypeId::new(0),
            },
            fixture_span(0, 1),
        ),
        LocatedInstruction::new(
            Instruction::Cast {
                operation: CastOp::BoolToSigned,
                result: ValueId::new(1),
                type_id: TypeId::new(1),
                value: ValueId::new(0),
            },
            fixture_span(1, 2),
        ),
        LocatedInstruction::new(
            Instruction::Cast {
                operation: CastOp::Truncate,
                result: ValueId::new(2),
                type_id: TypeId::new(2),
                value: ValueId::new(1),
            },
            fixture_span(2, 3),
        ),
        LocatedInstruction::new(
            Instruction::Cast {
                operation: CastOp::IntegerToBool,
                result: ValueId::new(3),
                type_id: TypeId::new(0),
                value: ValueId::new(2),
            },
            fixture_span(3, 4),
        ),
        LocatedInstruction::new(
            Instruction::Cast {
                operation: CastOp::BoolToSigned,
                result: ValueId::new(4),
                type_id: TypeId::new(1),
                value: ValueId::new(3),
            },
            fixture_span(4, 5),
        ),
    ]
}

fn boolean_roundtrip_module(bit: u8) -> Module {
    let instructions = boolean_roundtrip_instructions(bit);
    Module::new(ModuleSpec {
        abi_id: String::from("malbolge-c32-v1"),
        format_version: typed_ir::TYPED_IR_VERSION,
        functions: vec![Function::new(FunctionSpec {
            blocks: vec![BasicBlock::new(BasicBlockSpec {
                id: BlockId::new(0),
                instructions,
                phis: Vec::new(),
                span: fixture_span(0, 6),
                terminator: Terminator::Return {
                    value: Some(ValueId::new(4)),
                },
                terminator_span: fixture_span(5, 6),
            })],
            entry: BlockId::new(0),
            id: FunctionId::new(0),
            name: String::from("boolean_roundtrip"),
            parameters: Vec::new(),
            signature: TypeId::new(3),
            span: fixture_span(0, 6),
        })],
        globals: Vec::new(),
        proof_obligations: Vec::new(),
        source_id: String::from("fixtures/boolean-roundtrip.c"),
        source_sha256: [0xbc; 32],
        target_profile: String::from("malbolge-2026"),
        types: boolean_roundtrip_types(),
    })
}

fn byte_to_bool_types() -> Vec<TypeEntry> {
    vec![
        TypeEntry::new(TypeId::new(0), TypeDef::U8),
        TypeEntry::new(TypeId::new(1), TypeDef::Bool),
        TypeEntry::new(
            TypeId::new(2),
            TypeDef::function(Vec::new(), Some(TypeId::new(1)), false),
        ),
    ]
}

fn byte_to_bool_module(source: Option<u8>) -> Module {
    let source_instruction = source.map_or_else(
        || Instruction::ByteInput {
            result: ValueId::new(0),
            type_id: TypeId::new(0),
        },
        |byte| Instruction::ConstantInteger {
            constant: IntegerConstant::new(8, vec![byte]),
            result: ValueId::new(0),
            type_id: TypeId::new(0),
        },
    );
    let instructions = vec![
        LocatedInstruction::new(source_instruction, fixture_span(0, 1)),
        LocatedInstruction::new(
            Instruction::Cast {
                operation: CastOp::IntegerToBool,
                result: ValueId::new(1),
                type_id: TypeId::new(1),
                value: ValueId::new(0),
            },
            fixture_span(1, 2),
        ),
    ];
    Module::new(ModuleSpec {
        abi_id: String::from("malbolge-c32-v1"),
        format_version: typed_ir::TYPED_IR_VERSION,
        functions: vec![Function::new(FunctionSpec {
            blocks: vec![BasicBlock::new(BasicBlockSpec {
                id: BlockId::new(0),
                instructions,
                phis: Vec::new(),
                span: fixture_span(0, 3),
                terminator: Terminator::Return {
                    value: Some(ValueId::new(1)),
                },
                terminator_span: fixture_span(2, 3),
            })],
            entry: BlockId::new(0),
            id: FunctionId::new(0),
            name: String::from("byte_to_bool"),
            parameters: Vec::new(),
            signature: TypeId::new(2),
            span: fixture_span(0, 3),
        })],
        globals: Vec::new(),
        proof_obligations: Vec::new(),
        source_id: String::from("fixtures/byte-to-bool.c"),
        source_sha256: [0xe8; 32],
        target_profile: String::from("malbolge-2026"),
        types: byte_to_bool_types(),
    })
}

fn bool_to_signed_types() -> Vec<TypeEntry> {
    let integer_type = TypeId::new(0);
    vec![
        TypeEntry::new(integer_type, TypeDef::I32),
        TypeEntry::new(TypeId::new(1), TypeDef::Bool),
        TypeEntry::new(
            TypeId::new(2),
            TypeDef::function(Vec::new(), Some(integer_type), false),
        ),
    ]
}

fn bool_to_signed_fixture_module(left: u32, right: u32) -> Module {
    let integer_type = TypeId::new(0);
    let bool_type = TypeId::new(1);
    let signature = TypeId::new(2);
    let instructions = vec![
        low_byte_constant(left, 0, 0, integer_type),
        low_byte_constant(right, 1, 1, integer_type),
        LocatedInstruction::new(
            Instruction::Compare {
                left: ValueId::new(0),
                operation: CompareOp::Equal,
                result: ValueId::new(2),
                right: ValueId::new(1),
                type_id: bool_type,
            },
            fixture_span(2, 3),
        ),
        LocatedInstruction::new(
            Instruction::Cast {
                operation: CastOp::BoolToSigned,
                result: ValueId::new(3),
                type_id: integer_type,
                value: ValueId::new(2),
            },
            fixture_span(3, 4),
        ),
    ];
    Module::new(ModuleSpec {
        abi_id: String::from("malbolge-c32-v1"),
        format_version: typed_ir::TYPED_IR_VERSION,
        functions: vec![Function::new(FunctionSpec {
            blocks: vec![BasicBlock::new(BasicBlockSpec {
                id: BlockId::new(0),
                instructions,
                phis: Vec::new(),
                span: fixture_span(0, 5),
                terminator: Terminator::Return {
                    value: Some(ValueId::new(3)),
                },
                terminator_span: fixture_span(4, 5),
            })],
            entry: BlockId::new(0),
            id: FunctionId::new(0),
            name: String::from("bool_to_signed"),
            parameters: Vec::new(),
            signature,
            span: fixture_span(0, 5),
        })],
        globals: Vec::new(),
        proof_obligations: Vec::new(),
        source_id: String::from("fixtures/bool-to-signed.c"),
        source_sha256: [0xb6; 32],
        target_profile: String::from("malbolge-2026"),
        types: bool_to_signed_types(),
    })
}

fn comparison_types(signed: bool) -> Vec<TypeEntry> {
    vec![
        TypeEntry::new(
            TypeId::new(0),
            if signed {
                TypeDef::I32
            } else {
                TypeDef::U32
            },
        ),
        TypeEntry::new(TypeId::new(1), TypeDef::Bool),
        TypeEntry::new(
            TypeId::new(2),
            TypeDef::function(Vec::new(), Some(TypeId::new(1)), false),
        ),
    ]
}

fn integer_comparison_module(case: ComparisonFixture) -> Module {
    let word_type = TypeId::new(0);
    let bool_type = TypeId::new(1);
    let signature = TypeId::new(2);
    let mut instructions = vec![low_byte_constant(case.left, 0, 0, word_type)];
    if !case.alias {
        instructions.push(low_byte_constant(case.right, 1, 1, word_type));
    }
    let result = if case.alias {
        1
    } else {
        2
    };
    instructions.push(LocatedInstruction::new(
        Instruction::Compare {
            left: ValueId::new(0),
            operation: case.operation,
            result: ValueId::new(result),
            right: ValueId::new(u32::from(!case.alias)),
            type_id: bool_type,
        },
        fixture_span(result, result.saturating_add(1)),
    ));
    let end = result.saturating_add(2);
    Module::new(ModuleSpec {
        abi_id: String::from("malbolge-c32-v1"),
        format_version: typed_ir::TYPED_IR_VERSION,
        functions: vec![Function::new(FunctionSpec {
            blocks: vec![BasicBlock::new(BasicBlockSpec {
                id: BlockId::new(0),
                instructions,
                phis: Vec::new(),
                span: fixture_span(0, end),
                terminator: Terminator::Return {
                    value: Some(ValueId::new(result)),
                },
                terminator_span: fixture_span(end.saturating_sub(1), end),
            })],
            entry: BlockId::new(0),
            id: FunctionId::new(0),
            name: String::from("integer_comparison"),
            parameters: Vec::new(),
            signature,
            span: fixture_span(0, end),
        })],
        globals: Vec::new(),
        proof_obligations: Vec::new(),
        source_id: String::from("fixtures/integer-comparison.c"),
        source_sha256: [0xa3; 32],
        target_profile: String::from("malbolge-2026"),
        types: comparison_types(case.signed),
    })
}

fn low_byte_module() -> Module {
    low_byte_module_with_binary(BinaryOp::And)
}

fn low_byte_module_with_binary(operation: BinaryOp) -> Module {
    let operand_bits = if operation == BinaryOp::ShiftLeft {
        (1, 31)
    } else if operation == BinaryOp::ShiftRightArithmetic {
        (0x8000_0000, 31)
    } else {
        (u32::MAX, 0xff)
    };
    low_byte_module_with_bits(operation, operand_bits)
}

fn low_byte_module_with_bits(
    operation: BinaryOp,
    operand_bits: (u32, u32),
) -> Module {
    let u8_type = TypeId::new(0);
    let i32_type = TypeId::new(1);
    let function_type = TypeId::new(2);
    let block = BasicBlock::new(BasicBlockSpec {
        id: BlockId::new(0),
        instructions: low_byte_instructions(
            u8_type,
            i32_type,
            operation,
            operand_bits,
        ),
        phis: Vec::new(),
        span: fixture_span(0, 6),
        terminator: Terminator::Return {
            value: Some(ValueId::new(2)),
        },
        terminator_span: fixture_span(5, 6),
    });
    let function = Function::new(FunctionSpec {
        blocks: vec![block],
        entry: BlockId::new(0),
        id: FunctionId::new(0),
        name: String::from("low_byte"),
        parameters: Vec::new(),
        signature: function_type,
        span: fixture_span(0, 6),
    });
    Module::new(ModuleSpec {
        abi_id: String::from("malbolge-c32-v1"),
        format_version: typed_ir::TYPED_IR_VERSION,
        functions: vec![function],
        globals: Vec::new(),
        proof_obligations: Vec::new(),
        source_id: String::from("fixtures/low-byte.c"),
        source_sha256: LOW_BYTE_SOURCE_HASH,
        target_profile: String::from("malbolge-2026"),
        types: vec![
            TypeEntry::new(u8_type, TypeDef::U8),
            TypeEntry::new(i32_type, TypeDef::I32),
            TypeEntry::new(
                function_type,
                TypeDef::function(Vec::new(), Some(i32_type), false),
            ),
        ],
    })
}

fn low_byte_instructions(
    u8_type: TypeId,
    i32_type: TypeId,
    operation: BinaryOp,
    operand_bits: (u32, u32),
) -> Vec<LocatedInstruction> {
    let (left_bits, count_bits) = operand_bits;
    vec![
        low_byte_constant(left_bits, 0, 0, i32_type),
        low_byte_constant(count_bits, 1, 1, i32_type),
        LocatedInstruction::new(
            Instruction::Binary {
                left: ValueId::new(0),
                operation,
                result: ValueId::new(2),
                right: ValueId::new(1),
                type_id: i32_type,
            },
            fixture_span(2, 3),
        ),
        LocatedInstruction::new(
            Instruction::Cast {
                operation: CastOp::Truncate,
                result: ValueId::new(3),
                type_id: u8_type,
                value: ValueId::new(2),
            },
            fixture_span(3, 4),
        ),
        LocatedInstruction::new(
            Instruction::ByteOutput { value: ValueId::new(3) },
            fixture_span(4, 5),
        ),
    ]
}

fn low_byte_constant(
    bits: u32,
    result: u32,
    span_begin: u32,
    type_id: TypeId,
) -> LocatedInstruction {
    LocatedInstruction::new(
        Instruction::ConstantInteger {
            constant: IntegerConstant::new(32, Vec::from(bits.to_le_bytes())),
            result: ValueId::new(result),
            type_id,
        },
        fixture_span(span_begin, span_begin.saturating_add(1)),
    )
}

const fn fixture_position(byte: u32) -> SourcePosition {
    SourcePosition::new(byte, 1, byte.saturating_add(1))
}

const fn fixture_span(begin: u32, end: u32) -> SourceSpan {
    SourceSpan::new(fixture_position(begin), fixture_position(end))
}

fn canonical_golden(path: &str) -> Result<Vec<u8>, String> {
    let text = read_to_string(path)
        .map_err(|error| format!("read golden: {error}"))?;
    let compact = text.lines().collect::<String>();
    let payload = compact
        .strip_prefix(TYPED_IR_CODEC_ID)
        .and_then(|value| value.strip_prefix(':'))
        .ok_or_else(|| String::from("typed-IR golden prefix mismatch"))?;
    let (pairs, remainder) = payload.as_bytes().as_chunks::<2>();
    if !remainder.is_empty() {
        return Err(String::from("typed-IR golden has odd hex length"));
    }
    pairs
        .iter()
        .map(|pair| {
            from_utf8(pair)
                .map_err(|error| format!("golden UTF-8: {error}"))
                .and_then(|value| {
                    u8::from_str_radix(value, 16)
                        .map_err(|error| format!("golden hex: {error}"))
                })
        })
        .collect()
}

fn input_block(module: &Module, block: &BasicBlock) -> InputBlock {
    InputBlock {
        id: block.id().value(),
        instructions: block
            .instructions()
            .iter()
            .map(|instruction| input_instruction(module, instruction))
            .collect(),
        phi_count: block.phis().len(),
        terminator: input_terminator(block),
    }
}

fn input_function(module: &Module, function: &Function) -> InputFunction {
    let return_kind = usize::try_from(function.signature().value())
        .ok()
        .and_then(|index| module.types().get(index))
        .and_then(|entry| match entry.definition() {
            TypeDef::Function { result: Some(result), .. } => {
                Some(input_scalar_type(module, *result))
            },
            TypeDef::Function { result: None, .. } => {
                Some(InputScalarType::Void)
            },
            TypeDef::Array { .. }
            | TypeDef::Bool
            | TypeDef::Char
            | TypeDef::F128
            | TypeDef::F32
            | TypeDef::F64
            | TypeDef::I16
            | TypeDef::I32
            | TypeDef::I64
            | TypeDef::I8
            | TypeDef::Pointer { .. }
            | TypeDef::Struct { .. }
            | TypeDef::U16
            | TypeDef::U32
            | TypeDef::U64
            | TypeDef::U8
            | TypeDef::Union { .. }
            | TypeDef::Void => None,
        })
        .unwrap_or(InputScalarType::Other);
    InputFunction {
        blocks: function
            .blocks()
            .iter()
            .map(|block| input_block(module, block))
            .collect(),
        entry: function.entry().value(),
        id: function.id().value(),
        name: String::from(function.name()),
        parameter_count: function.parameters().len(),
        return_kind,
        span: input_span(function.span()),
    }
}

fn projected_shift_instruction(
    module: &Module,
    instruction: &LocatedInstruction,
) -> Option<InputInstruction> {
    let Instruction::Binary {
        left,
        operation,
        result,
        right,
        type_id,
    } = instruction.instruction()
    else {
        return None;
    };
    let left_id = left.value();
    let result_id = result.value();
    let right_id = right.value();
    let span = input_span(instruction.span());
    let type_kind = input_scalar_type(module, *type_id);
    if *operation == BinaryOp::ShiftLeft {
        return Some(InputInstruction::BinaryShiftLeft {
            left: left_id,
            result: result_id,
            right: right_id,
            span,
            type_kind,
        });
    }
    if *operation == BinaryOp::ShiftRightArithmetic {
        return Some(InputInstruction::BinaryShiftRightArithmetic {
            left: left_id,
            result: result_id,
            right: right_id,
            span,
            type_kind,
        });
    }
    if *operation == BinaryOp::ShiftRightLogical {
        return Some(InputInstruction::BinaryShiftRightLogical {
            left: left_id,
            result: result_id,
            right: right_id,
            span,
            type_kind,
        });
    }
    None
}

fn projected_divrem_instruction(
    module: &Module,
    instruction: &LocatedInstruction,
) -> Option<InputInstruction> {
    let Instruction::Binary {
        left,
        operation,
        result,
        right,
        type_id,
    } = instruction.instruction()
    else {
        return None;
    };
    let left_id = left.value();
    let result_id = result.value();
    let right_id = right.value();
    let span = input_span(instruction.span());
    let type_kind = input_scalar_type(module, *type_id);
    if *operation == BinaryOp::DivideSigned {
        return Some(InputInstruction::BinaryDivideSigned {
            left: left_id,
            result: result_id,
            right: right_id,
            span,
            type_kind,
        });
    }
    if *operation == BinaryOp::DivideUnsigned {
        return Some(InputInstruction::BinaryDivideUnsigned {
            left: left_id,
            result: result_id,
            right: right_id,
            span,
            type_kind,
        });
    }
    if *operation == BinaryOp::RemainderSigned {
        return Some(InputInstruction::BinaryRemainderSigned {
            left: left_id,
            result: result_id,
            right: right_id,
            span,
            type_kind,
        });
    }
    if *operation == BinaryOp::RemainderUnsigned {
        return Some(InputInstruction::BinaryRemainderUnsigned {
            left: left_id,
            result: result_id,
            right: right_id,
            span,
            type_kind,
        });
    }
    None
}

fn projected_arithmetic_instruction(
    module: &Module,
    instruction: &LocatedInstruction,
) -> Option<InputInstruction> {
    if let Some(divrem) = projected_divrem_instruction(module, instruction) {
        return Some(divrem);
    }
    let Instruction::Binary {
        left,
        operation,
        result,
        right,
        type_id,
    } = instruction.instruction()
    else {
        return None;
    };
    let left_id = left.value();
    let result_id = result.value();
    let right_id = right.value();
    let span = input_span(instruction.span());
    let type_kind = input_scalar_type(module, *type_id);
    if *operation == BinaryOp::Add {
        return Some(InputInstruction::BinaryAdd {
            left: left_id,
            result: result_id,
            right: right_id,
            span,
            type_kind,
        });
    }
    if *operation == BinaryOp::Subtract {
        return Some(InputInstruction::BinarySubtract {
            left: left_id,
            result: result_id,
            right: right_id,
            span,
            type_kind,
        });
    }
    if *operation == BinaryOp::Multiply {
        return Some(InputInstruction::BinaryMultiply {
            left: left_id,
            result: result_id,
            right: right_id,
            span,
            type_kind,
        });
    }
    None
}

fn projected_bitwise_instruction(
    module: &Module,
    instruction: &LocatedInstruction,
) -> Option<InputInstruction> {
    if let Instruction::Binary {
        left,
        operation,
        result,
        right,
        type_id,
    } = instruction.instruction()
    {
        let left_id = left.value();
        let result_id = result.value();
        let right_id = right.value();
        let span = input_span(instruction.span());
        let type_kind = input_scalar_type(module, *type_id);
        match operation {
            BinaryOp::And => {
                return Some(InputInstruction::BinaryAnd {
                    left: left_id,
                    result: result_id,
                    right: right_id,
                    span,
                    type_kind,
                });
            },
            BinaryOp::Or => {
                return Some(InputInstruction::BinaryOr {
                    left: left_id,
                    result: result_id,
                    right: right_id,
                    span,
                    type_kind,
                });
            },
            BinaryOp::Xor => {
                return Some(InputInstruction::BinaryXor {
                    left: left_id,
                    result: result_id,
                    right: right_id,
                    span,
                    type_kind,
                });
            },
            BinaryOp::Add
            | BinaryOp::DivideFloat
            | BinaryOp::DivideSigned
            | BinaryOp::DivideUnsigned
            | BinaryOp::Multiply
            | BinaryOp::RemainderSigned
            | BinaryOp::RemainderUnsigned
            | BinaryOp::ShiftLeft
            | BinaryOp::ShiftRightArithmetic
            | BinaryOp::ShiftRightLogical
            | BinaryOp::Subtract => {},
        }
    }
    None
}

const fn project_sign_extension(
    result: u32,
    span: InputSourceSpan,
    type_kind: InputScalarType,
    value: u32,
) -> InputInstruction {
    InputInstruction::SignExtendI8ToI32 {
        result,
        span,
        type_kind,
        value,
    }
}

fn projected_cast_instruction(
    module: &Module,
    instruction: &LocatedInstruction,
) -> Option<InputInstruction> {
    let Instruction::Cast {
        operation,
        result,
        type_id,
        value,
    } = instruction.instruction()
    else {
        return None;
    };
    let result_id = result.value();
    let span = input_span(instruction.span());
    let type_kind = input_scalar_type(module, *type_id);
    let source_id = value.value();
    if *operation == CastOp::Truncate {
        return Some(InputInstruction::TruncateInteger {
            result: result_id,
            span,
            type_kind,
            value: source_id,
        });
    }
    if *operation == CastOp::SignExtend {
        return Some(project_sign_extension(
            result_id, span, type_kind, source_id,
        ));
    }
    if *operation == CastOp::ZeroExtend {
        return Some(InputInstruction::ZeroExtendInteger {
            result: result_id,
            span,
            type_kind,
            value: source_id,
        });
    }
    if *operation == CastOp::IntegerToBool {
        return Some(InputInstruction::IntegerToBool {
            result: result_id,
            span,
            type_kind,
            value: source_id,
        });
    }
    if *operation == CastOp::BoolToSigned {
        return Some(InputInstruction::BoolToSigned {
            result: result_id,
            span,
            type_kind,
            value: source_id,
        });
    }
    if *operation == CastOp::IntegerBitcast {
        return Some(InputInstruction::IntegerBitcast {
            result: result_id,
            span,
            type_kind,
            value: source_id,
        });
    }
    None
}

const fn projected_ordered_predicate(
    operation: CompareOp,
) -> Option<InputOrderedComparison> {
    match operation {
        CompareOp::LessSigned => Some(InputOrderedComparison::Signed),
        CompareOp::LessSignedEqual => Some(InputOrderedComparison::SignedEqual),
        CompareOp::LessUnsigned => Some(InputOrderedComparison::Unsigned),
        CompareOp::LessUnsignedEqual => {
            Some(InputOrderedComparison::UnsignedEqual)
        },
        CompareOp::Equal
        | CompareOp::NotEqual
        | CompareOp::FloatLess
        | CompareOp::FloatLessEqual => None,
    }
}

fn projected_comparison_instruction(
    module: &Module,
    instruction: &LocatedInstruction,
) -> Option<InputInstruction> {
    let Instruction::Compare {
        left,
        operation,
        result,
        right,
        type_id,
    } = instruction.instruction()
    else {
        return None;
    };
    let span = input_span(instruction.span());
    let type_kind = input_scalar_type(module, *type_id);
    if let Some(ordered) = projected_ordered_predicate(*operation) {
        return Some(InputInstruction::CompareOrdered {
            left: left.value(),
            operation: ordered,
            result: result.value(),
            right: right.value(),
            span,
            type_kind,
        });
    }
    match operation {
        CompareOp::Equal => Some(InputInstruction::CompareEqual {
            left: left.value(),
            result: result.value(),
            right: right.value(),
            span,
            type_kind,
        }),
        CompareOp::NotEqual => Some(InputInstruction::CompareNotEqual {
            left: left.value(),
            result: result.value(),
            right: right.value(),
            span,
            type_kind,
        }),
        CompareOp::FloatLess
        | CompareOp::FloatLessEqual
        | CompareOp::LessSigned
        | CompareOp::LessSignedEqual
        | CompareOp::LessUnsigned
        | CompareOp::LessUnsignedEqual => None,
    }
}

fn input_instruction(
    module: &Module,
    instruction: &LocatedInstruction,
) -> InputInstruction {
    if let Some(comparison) =
        projected_comparison_instruction(module, instruction)
    {
        return comparison;
    }
    if let Some(shift) = projected_shift_instruction(module, instruction) {
        return shift;
    }
    if let Some(arithmetic) =
        projected_arithmetic_instruction(module, instruction)
    {
        return arithmetic;
    }
    if let Some(bitwise) = projected_bitwise_instruction(module, instruction) {
        return bitwise;
    }
    if let Instruction::ByteInput { result, type_id } =
        instruction.instruction()
    {
        return InputInstruction::ByteInput {
            result: result.value(),
            span: input_span(instruction.span()),
            type_kind: input_scalar_type(module, *type_id),
        };
    }
    if let Instruction::ByteOutput { value } = instruction.instruction() {
        return InputInstruction::ByteOutput {
            span: input_span(instruction.span()),
            value: value.value(),
        };
    }
    if let Instruction::ConstantInteger {
        constant,
        result,
        type_id,
    } = instruction.instruction()
    {
        return InputInstruction::ConstantInteger {
            bit_width: constant.bit_width(),
            little_endian: Vec::from(constant.little_endian()),
            result: result.value(),
            span: input_span(instruction.span()),
            type_kind: input_scalar_type(module, *type_id),
        };
    }
    if let Some(cast) = projected_cast_instruction(module, instruction) {
        return cast;
    }
    InputInstruction::Unsupported
}

fn input_scalar_type(module: &Module, type_id: TypeId) -> InputScalarType {
    let Some(index) = usize::try_from(type_id.value()).ok() else {
        return InputScalarType::Other;
    };
    let Some(entry) = module.types().get(index) else {
        return InputScalarType::Other;
    };
    if entry.id() != type_id {
        return InputScalarType::Other;
    }
    match entry.definition() {
        TypeDef::Bool => InputScalarType::Bool,
        TypeDef::I16 => InputScalarType::I16,
        TypeDef::I32 => InputScalarType::I32,
        TypeDef::I8 => InputScalarType::I8,
        TypeDef::U16 => InputScalarType::U16,
        TypeDef::U32 => InputScalarType::U32,
        TypeDef::U8 => InputScalarType::U8,
        TypeDef::Array { .. }
        | TypeDef::Char
        | TypeDef::F128
        | TypeDef::F32
        | TypeDef::F64
        | TypeDef::Function { .. }
        | TypeDef::I64
        | TypeDef::Pointer { .. }
        | TypeDef::Struct { .. }
        | TypeDef::U64
        | TypeDef::Union { .. }
        | TypeDef::Void => InputScalarType::Other,
    }
}

const fn input_span(span: SourceSpan) -> InputSourceSpan {
    let begin = span.begin();
    let end = span.end();
    InputSourceSpan {
        begin: InputSourcePosition {
            byte: begin.byte(),
            column: begin.column(),
            line: begin.line(),
        },
        end: InputSourcePosition {
            byte: end.byte(),
            column: end.column(),
            line: end.line(),
        },
    }
}

fn input_terminator(block: &BasicBlock) -> InputTerminator {
    if let Terminator::Return { value } = block.terminator() {
        return InputTerminator::Return {
            span: input_span(block.terminator_span()),
            value: (*value).map(ValueId::value),
        };
    }
    InputTerminator::Unsupported
}

fn project_typed_ir(module: &Module) -> Result<TypedIrInput, String> {
    validate_module(module).map_err(|error| {
        format!("validate typed IR before projection: {error:?}")
    })?;
    Ok(TypedIrInput {
        abi_id: String::from(module.abi_id()),
        functions: module
            .functions()
            .iter()
            .map(|function| input_function(module, function))
            .collect(),
        global_count: module.globals().len(),
        input_format_version: module.format_version(),
        proof_obligation_count: module.proof_obligations().len(),
        source_id: String::from(module.source_id()),
        source_sha256: *module.source_sha256(),
        target_profile: String::from(module.target_profile()),
    })
}

fn projected_byte_io_fixture() -> Result<TypedIrInput, String> {
    let module = admitted_byte_io_fixture()?;
    project_typed_ir(&module)
}

fn projected_low_byte_fixture() -> Result<TypedIrInput, String> {
    let module = admitted_low_byte_fixture()?;
    project_typed_ir(&module)
}

#[test]
fn byte_input_requires_u8_projection() -> Result<(), String> {
    let mut input = projected_byte_io_fixture()?;
    let instruction = input
        .functions
        .first_mut()
        .and_then(|function| function.blocks.first_mut())
        .and_then(|block| block.instructions.first_mut())
        .ok_or_else(|| String::from("byte-I/O projection has no input"))?;
    let InputInstruction::ByteInput { type_kind, .. } = instruction else {
        return Err(String::from("first projection instruction is not input"));
    };
    *type_kind = InputScalarType::Other;
    if lower_typed_ir(&input)
        != Err(TernaryLoweringError::UnsupportedInstruction)
    {
        return Err(String::from("non-u8 byte input was not rejected"));
    }
    Ok(())
}

#[test]
fn byte_output_requires_prior_byte_definition() -> Result<(), String> {
    let mut input = projected_byte_io_fixture()?;
    let instruction = input
        .functions
        .first_mut()
        .and_then(|function| function.blocks.first_mut())
        .and_then(|block| block.instructions.get_mut(1))
        .ok_or_else(|| String::from("byte-I/O projection has no output"))?;
    let InputInstruction::ByteOutput { value, .. } = instruction else {
        return Err(String::from(
            "second projection instruction is not output",
        ));
    };
    *value = 99;
    if lower_typed_ir(&input)
        != Err(TernaryLoweringError::UnsupportedInstruction)
    {
        return Err(String::from("undefined byte output was not rejected"));
    }
    Ok(())
}

#[test]
fn duplicate_projection_value_ids_fail_closed() -> Result<(), String> {
    let mut input = projected_byte_io_fixture()?;
    let instruction = input
        .functions
        .first_mut()
        .and_then(|function| function.blocks.first_mut())
        .and_then(|block| block.instructions.get_mut(2))
        .ok_or_else(|| String::from("byte-I/O projection has no constant"))?;
    let InputInstruction::ConstantInteger { result, .. } = instruction else {
        return Err(String::from(
            "third projection instruction is not constant",
        ));
    };
    *result = 0;
    if lower_typed_ir(&input) != Err(TernaryLoweringError::InvalidProjection) {
        return Err(String::from(
            "duplicate projection SSA ID was not rejected",
        ));
    }
    Ok(())
}

#[test]
fn low_byte_and_rejects_projection_drift() -> Result<(), String> {
    let input = projected_low_byte_fixture()?;
    let mut wrong_type = input.clone();
    let instruction = wrong_type
        .functions
        .first_mut()
        .and_then(|function| function.blocks.first_mut())
        .and_then(|block| block.instructions.get_mut(2))
        .ok_or_else(|| String::from("low-byte projection has no AND"))?;
    let InputInstruction::BinaryAnd { type_kind, .. } = instruction else {
        return Err(String::from("low-byte projection AND is missing"));
    };
    *type_kind = InputScalarType::Other;
    if lower_typed_ir(&wrong_type)
        != Err(TernaryLoweringError::UnsupportedInstruction)
    {
        return Err(String::from("non-i32 AND projection was not rejected"));
    }
    let mut undefined = input;
    let undefined_instruction = undefined
        .functions
        .first_mut()
        .and_then(|function| function.blocks.first_mut())
        .and_then(|block| block.instructions.get_mut(2))
        .ok_or_else(|| String::from("low-byte projection has no AND"))?;
    let InputInstruction::BinaryAnd { right, .. } = undefined_instruction
    else {
        return Err(String::from("low-byte projection AND is missing"));
    };
    *right = 99;
    if lower_typed_ir(&undefined)
        != Err(TernaryLoweringError::UnsupportedInstruction)
    {
        return Err(String::from("undefined AND operand was not rejected"));
    }
    Ok(())
}

#[test]
fn low_byte_truncate_rejects_projection_drift() -> Result<(), String> {
    let input = projected_low_byte_fixture()?;
    let mut wrong_type = input.clone();
    let instruction = wrong_type
        .functions
        .first_mut()
        .and_then(|function| function.blocks.first_mut())
        .and_then(|block| block.instructions.get_mut(3))
        .ok_or_else(|| String::from("low-byte projection has no truncate"))?;
    let InputInstruction::TruncateInteger { type_kind, .. } = instruction
    else {
        return Err(String::from("low-byte projection truncate is missing"));
    };
    *type_kind = InputScalarType::I32;
    if lower_typed_ir(&wrong_type)
        != Err(TernaryLoweringError::UnsupportedInstruction)
    {
        return Err(String::from("non-u8 truncation result was not rejected"));
    }
    let mut undefined = input;
    let undefined_instruction = undefined
        .functions
        .first_mut()
        .and_then(|function| function.blocks.first_mut())
        .and_then(|block| block.instructions.get_mut(3))
        .ok_or_else(|| String::from("low-byte projection has no truncate"))?;
    let InputInstruction::TruncateInteger { value, .. } = undefined_instruction
    else {
        return Err(String::from("low-byte projection truncate is missing"));
    };
    *value = 99;
    if lower_typed_ir(&undefined)
        != Err(TernaryLoweringError::UnsupportedInstruction)
    {
        return Err(String::from(
            "undefined truncation source was not rejected",
        ));
    }
    Ok(())
}

fn first_function_id_offset(bytes: &[u8]) -> Result<usize, String> {
    let mut offset = 8usize;
    for _ in 0..3usize {
        let raw: [u8; 4] = bytes
            .get(offset..offset.saturating_add(4))
            .ok_or_else(|| {
                String::from("ternary header string length missing")
            })?
            .try_into()
            .map_err(|_error| {
                String::from("ternary header length malformed")
            })?;
        let length = usize::try_from(u32::from_le_bytes(raw))
            .map_err(|_error| String::from("ternary header length overflow"))?;
        offset = offset
            .checked_add(4)
            .and_then(|value| value.checked_add(length))
            .ok_or_else(|| String::from("ternary header offset overflow"))?;
    }
    offset = offset
        .checked_add(32)
        .ok_or_else(|| String::from("ternary digest offset overflow"))?;
    let count_raw: [u8; 4] = bytes
        .get(offset..offset.saturating_add(4))
        .ok_or_else(|| String::from("ternary function count missing"))?
        .try_into()
        .map_err(|_error| String::from("ternary function count malformed"))?;
    if u32::from_le_bytes(count_raw) == 0 {
        return Err(String::from("ternary fixture has no functions"));
    }
    offset
        .checked_add(4)
        .ok_or_else(|| String::from("ternary function offset overflow"))
}

fn materialize_pattern(bits: u32, result: u32) -> Vec<u8> {
    let mut pattern = vec![3];
    pattern.extend_from_slice(&result.to_le_bytes());
    pattern.extend_from_slice(
        ternary_lowering::TernaryI32Scalar::from_bits(bits).trits(),
    );
    pattern
}

fn lowered_return_fixture() -> Result<ternary_lowering::TernaryProgram, String>
{
    let module = admitted_golden(RETURN_GOLDEN)?;
    let input = project_typed_ir(&module)?;
    lower_typed_ir(&input)
        .map_err(|error| format!("lower return fixture: {error:?}"))
}

#[test]
fn canonical_ternary_program_round_trips_exactly() -> Result<(), String> {
    let program = lowered_return_fixture()?;
    let first = canonical_ternary_bytes(&program)
        .map_err(|error| format!("encode ternary program: {error:?}"))?;
    let second = canonical_ternary_bytes(&program)
        .map_err(|error| format!("repeat ternary encoding: {error:?}"))?;
    if TERNARY_PROGRAM_CODEC_ID != "malbolge-ternary-ir-v1"
        || first != second
        || first.get(..6) != Some(&b"MCTR\x01\x00"[..])
    {
        return Err(String::from("ternary canonical identity drifted"));
    }
    let restored = canonical_ternary_program(&first)
        .map_err(|error| format!("restore ternary program: {error:?}"))?;
    if restored != program
        || canonical_ternary_bytes(&restored)
            .map_err(|error| format!("re-encode ternary program: {error:?}"))?
            != first
    {
        return Err(String::from("ternary canonical round trip drifted"));
    }
    Ok(())
}

#[test]
fn ternary_codec_round_trips_all_lowered_operation_tags() -> Result<(), String>
{
    for module in [admitted_byte_io_fixture()?, admitted_low_byte_fixture()?] {
        let program = lower_typed_ir(&project_typed_ir(&module)?)
            .map_err(|error| format!("lower codec fixture: {error:?}"))?;
        let bytes = canonical_ternary_bytes(&program)
            .map_err(|error| format!("encode codec fixture: {error:?}"))?;
        let restored = canonical_ternary_program(&bytes)
            .map_err(|error| format!("restore codec fixture: {error:?}"))?;
        if restored != program {
            return Err(String::from("ternary operation codec drifted"));
        }
    }
    Ok(())
}

#[test]
fn ternary_codec_rejects_invalid_in_memory_program() -> Result<(), String> {
    let program = lowered_return_fixture()?;
    let mut wrong_identity = program.clone();
    wrong_identity.target_profile = String::from("malbolge-1998");
    if canonical_ternary_bytes(&wrong_identity)
        != Err(TernaryProgramCodecError::Validation(
            TernaryProgramValidationError::ProgramIdentity,
        ))
    {
        return Err(String::from("invalid ternary identity was serialized"));
    }
    let mut wrong_function = program.clone();
    wrong_function
        .functions
        .first_mut()
        .ok_or_else(|| String::from("return fixture has no function"))?
        .id = 7;
    if canonical_ternary_bytes(&wrong_function)
        != Err(TernaryProgramCodecError::Validation(
            TernaryProgramValidationError::FunctionIdentity,
        ))
    {
        return Err(String::from("invalid ternary function was serialized"));
    }
    let mut wrong_return = program;
    let last = wrong_return
        .functions
        .first_mut()
        .ok_or_else(|| String::from("return fixture has no function"))?
        .operations
        .last_mut()
        .ok_or_else(|| String::from("return fixture has no operations"))?;
    let TernaryOperation::Return { value, .. } = last else {
        return Err(String::from("return fixture has no final return"));
    };
    *value = 99;
    if canonical_ternary_bytes(&wrong_return)
        != Err(TernaryProgramCodecError::Validation(
            TernaryProgramValidationError::SsaValue,
        ))
    {
        return Err(String::from("undefined ternary return was serialized"));
    }
    Ok(())
}

#[test]
fn ternary_decoder_revalidates_forged_function_identity() -> Result<(), String>
{
    let bytes = canonical_ternary_bytes(&lowered_return_fixture()?)
        .map_err(|error| format!("encode ternary program: {error:?}"))?;
    let offset = first_function_id_offset(&bytes)?;
    let mut forged = bytes;
    forged
        .get_mut(offset..offset.saturating_add(4))
        .ok_or_else(|| String::from("ternary function ID bytes missing"))?
        .copy_from_slice(&1u32.to_le_bytes());
    if canonical_ternary_program(&forged)
        != Err(TernaryProgramCodecError::Validation(
            TernaryProgramValidationError::FunctionIdentity,
        ))
    {
        return Err(String::from("forged ternary function ID was restored"));
    }
    Ok(())
}

#[test]
fn ternary_decoder_rejects_malformed_wire_state() -> Result<(), String> {
    let program = lowered_return_fixture()?;
    let bytes = canonical_ternary_bytes(&program)
        .map_err(|error| format!("encode ternary program: {error:?}"))?;
    let mut magic = bytes.clone();
    *magic
        .first_mut()
        .ok_or_else(|| String::from("ternary magic missing"))? = b'X';
    let mut version = bytes.clone();
    *version
        .get_mut(4)
        .ok_or_else(|| String::from("ternary version missing"))? = 2;
    let mut trailing = bytes;
    trailing.push(0);
    if canonical_ternary_program(&magic)
        != Err(TernaryProgramCodecError::InvalidMagic)
        || canonical_ternary_program(&version)
            != Err(TernaryProgramCodecError::UnsupportedVersion)
        || canonical_ternary_program(&trailing)
            != Err(TernaryProgramCodecError::TrailingBytes)
    {
        return Err(String::from("malformed ternary wire state was accepted"));
    }
    Ok(())
}

#[test]
fn ternary_decoder_rejects_exaggerated_function_count_without_eager_allocation()
-> Result<(), String> {
    let canonical = canonical_ternary_bytes(&lowered_return_fixture()?)
        .map_err(|error| format!("encode ternary program: {error:?}"))?;
    let first_id_offset = first_function_id_offset(&canonical)?;
    let count_offset = first_id_offset
        .checked_sub(4)
        .ok_or_else(|| String::from("ternary count offset underflow"))?;
    let declared_count = 1_000_000u32;
    let mut forged = canonical
        .get(..count_offset)
        .ok_or_else(|| String::from("ternary header missing"))?
        .to_vec();
    forged.extend_from_slice(&declared_count.to_le_bytes());
    // One byte per claimed function passes count preflight, not decoding.
    forged.extend(vec![u8::MAX; 1_000_000]);
    if canonical_ternary_program(&forged)
        != Err(TernaryProgramCodecError::Truncated)
    {
        return Err(String::from("exaggerated function count was admitted"));
    }
    Ok(())
}

#[test]
fn ternary_operation_count_preflight_rejects_short_unknown_tag()
-> Result<(), String> {
    let canonical = canonical_ternary_bytes(&lowered_return_fixture()?)
        .map_err(|error| format!("encode ternary program: {error:?}"))?;
    let pattern = materialize_pattern(7, 0);
    let first_operation = canonical
        .windows(pattern.len())
        .position(|window| window == pattern)
        .ok_or_else(|| String::from("first ternary operation missing"))?;
    let count_offset = first_operation
        .checked_sub(4)
        .ok_or_else(|| String::from("ternary operation count underflow"))?;
    let mut forged = canonical
        .get(..count_offset)
        .ok_or_else(|| String::from("ternary operation header missing"))?
        .to_vec();
    forged.extend_from_slice(&1u32.to_le_bytes());
    // Fewer than 25 bytes for the shortest admitted void-return record,
    // while an obsolete one-byte preflight would inspect the tag first.
    forged.extend_from_slice(&[u8::MAX; 24]);
    if canonical_ternary_program(&forged)
        != Err(TernaryProgramCodecError::Truncated)
    {
        return Err(String::from("short operation record passed preflight"));
    }
    Ok(())
}

#[test]
fn ternary_bitwise_tags_reject_forged_ssa_and_unknown_successor()
-> Result<(), String> {
    for (operation, tag) in [(BinaryOp::Or, 6u8), (BinaryOp::Xor, 7u8)] {
        let module = low_byte_module_with_binary(operation);
        let input = project_typed_ir(&module)?;
        let program = lower_typed_ir(&input)
            .map_err(|error| format!("lower bitwise fixture: {error:?}"))?;
        let bytes = canonical_ternary_bytes(&program)
            .map_err(|error| format!("encode bitwise fixture: {error:?}"))?;
        let original = [tag, 0, 0, 0, 0, 2, 0, 0, 0, 1, 0, 0, 0];
        let offset = bytes
            .windows(original.len())
            .position(|window| window == original)
            .ok_or_else(|| String::from("bitwise wire tag missing"))?;
        for (relative_offset, wrong_identity) in [(5usize, 0u32), (9, 99)] {
            let mut forged = bytes.clone();
            forged
                .get_mut(offset + relative_offset..offset + relative_offset + 4)
                .ok_or_else(|| String::from("bitwise identity bytes missing"))?
                .copy_from_slice(&wrong_identity.to_le_bytes());
            if canonical_ternary_program(&forged)
                != Err(TernaryProgramCodecError::Validation(
                    TernaryProgramValidationError::SsaValue,
                ))
            {
                return Err(String::from("forged bitwise SSA was accepted"));
            }
        }
        let mut unknown_tag = bytes;
        *unknown_tag
            .get_mut(offset)
            .ok_or_else(|| String::from("bitwise tag byte missing"))? = 84;
        if canonical_ternary_program(&unknown_tag)
            != Err(TernaryProgramCodecError::UnknownTag)
        {
            return Err(String::from("unrecognized bitwise tag was accepted"));
        }
    }
    Ok(())
}

#[test]
fn ternary_decoder_rejects_unknown_tag_and_invalid_trit() -> Result<(), String>
{
    let bytes = canonical_ternary_bytes(&lowered_return_fixture()?)
        .map_err(|error| format!("encode ternary program: {error:?}"))?;
    let pattern = materialize_pattern(7, 0);
    let offset = bytes
        .windows(pattern.len())
        .position(|window| window == pattern)
        .ok_or_else(|| String::from("materialize encoding pattern missing"))?;
    let mut unknown_tag = bytes.clone();
    *unknown_tag
        .get_mut(offset)
        .ok_or_else(|| String::from("ternary operation tag missing"))? = 99;
    let mut invalid_trit = bytes;
    *invalid_trit
        .get_mut(offset.saturating_add(5))
        .ok_or_else(|| String::from("ternary scalar trit missing"))? = 3;
    if canonical_ternary_program(&unknown_tag)
        != Err(TernaryProgramCodecError::UnknownTag)
        || canonical_ternary_program(&invalid_trit)
            != Err(TernaryProgramCodecError::InvalidScalar)
    {
        return Err(String::from(
            "invalid ternary operation bytes were accepted",
        ));
    }
    Ok(())
}

#[test]
fn every_truncated_ternary_prefix_fails_closed() -> Result<(), String> {
    let bytes = canonical_ternary_bytes(&lowered_return_fixture()?)
        .map_err(|error| format!("encode ternary program: {error:?}"))?;
    for end in 0..bytes.len() {
        let prefix = bytes
            .get(..end)
            .ok_or_else(|| String::from("ternary prefix range missing"))?;
        if canonical_ternary_program(prefix).is_ok() {
            return Err(format!("truncated ternary prefix {end} was accepted"));
        }
    }
    Ok(())
}

#[test]
fn ternary_compiler_selector_converges() -> Result<(), String> {
    let module = admitted_golden(RETURN_GOLDEN)?;
    let projection = project_typed_ir(&module)?;
    let fresh = enter_ternary_compiler_stage(TernaryCompilerStageInput::Fresh(
        &projection,
    ))
    .map_err(|error| format!("select fresh ternary stage: {error:?}"))?;

    let bytes = canonical_ternary_bytes(&fresh)
        .map_err(|error| format!("encode selector ternary state: {error:?}"))?;
    let (progress, directory) =
        publish_ternary_progress_fixture("selector", &bytes)?;
    let resumed_result =
        enter_ternary_compiler_stage(TernaryCompilerStageInput::Progress {
            inspector: &progress_inspector(),
            interpreter: &repository_python(),
            progress: &progress,
        });
    remove_dir_all(&directory).map_err(|error| {
        format!("remove selector progress fixture: {error}")
    })?;
    let resumed = resumed_result
        .map_err(|error| format!("select resumed ternary: {error:?}"))?;
    if fresh != resumed {
        return Err(String::from(
            "ternary compiler selector paths did not converge",
        ));
    }
    Ok(())
}

#[test]
fn ternary_unsigned_return_selector_converges_through_progress()
-> Result<(), String> {
    let (expected, projection) = lowered_unsigned_return_fixture(u32::MAX)?;
    let fresh = enter_ternary_compiler_stage(TernaryCompilerStageInput::Fresh(
        &projection,
    ))
    .map_err(|error| format!("select unsigned fresh state: {error:?}"))?;
    if fresh != expected {
        return Err(String::from("unsigned fresh compiler projection drifted"));
    }
    let bytes = canonical_ternary_bytes(&fresh).map_err(|error| {
        format!("encode unsigned compiler state: {error:?}")
    })?;
    let (progress, directory) =
        publish_ternary_progress_fixture("unsigned-return-selector", &bytes)?;
    let resumed =
        enter_ternary_compiler_stage(TernaryCompilerStageInput::Progress {
            inspector: &progress_inspector(),
            interpreter: &repository_python(),
            progress: &progress,
        });
    remove_dir_all(&directory)
        .map_err(|error| format!("clean unsigned selector state: {error}"))?;
    if resumed != Ok(expected) {
        return Err(String::from(
            "unsigned progress selector did not converge",
        ));
    }
    Ok(())
}

#[test]
fn ternary_unsigned_progress_rejects_signed_tag() -> Result<(), String> {
    let (target, _projection) = lowered_unsigned_return_fixture(u32::MAX)?;
    let mut bytes = canonical_ternary_bytes(&target)
        .map_err(|error| format!("encode unsigned checkpoint: {error:?}"))?;
    let tag_offset = bytes
        .len()
        .checked_sub(29)
        .ok_or_else(|| String::from("unsigned return terminator missing"))?;
    *bytes
        .get_mut(tag_offset)
        .ok_or_else(|| String::from("unsigned return tag missing"))? = 4;
    let (progress, directory) =
        publish_ternary_progress_fixture("unsigned-return-forged", &bytes)?;
    let rejected = resume_ternary_from_progress(
        &repository_python(),
        &progress_inspector(),
        &progress,
    );
    remove_dir_all(&directory)
        .map_err(|error| format!("clean forged unsigned progress: {error}"))?;
    let expected = Err(TernaryProgressCheckpointError::Stage(
        TernaryStageError::Checkpoint(TernaryProgramCodecError::Validation(
            TernaryProgramValidationError::SsaValue,
        )),
    ));
    if rejected != expected {
        return Err(String::from(
            "signed return tag passed progress admission",
        ));
    }
    Ok(())
}

#[test]
fn ternary_unsigned_crash_resume_recovers_committed_generation()
-> Result<(), String> {
    let previous = lowered_return_fixture()?;
    let (next, _projection) = lowered_unsigned_return_fixture(u32::MAX)?;
    if previous == next {
        return Err(String::from(
            "crash versions must have distinct signedness",
        ));
    }
    for boundary in TERNARY_CRASH_BOUNDARIES {
        run_ternary_crash_boundary(boundary, &previous, &next)?;
    }
    Ok(())
}

const fn arithmetic_cases() -> [(bool, BinaryOp); 10] {
    [
        (true, BinaryOp::Add),
        (false, BinaryOp::Add),
        (true, BinaryOp::DivideSigned),
        (false, BinaryOp::DivideUnsigned),
        (true, BinaryOp::Multiply),
        (false, BinaryOp::Multiply),
        (true, BinaryOp::RemainderSigned),
        (false, BinaryOp::RemainderUnsigned),
        (true, BinaryOp::Subtract),
        (false, BinaryOp::Subtract),
    ]
}

const fn arithmetic_case_label(
    signed: bool,
    operation: BinaryOp,
) -> &'static str {
    match (signed, operation) {
        (true, BinaryOp::Add) => "signed-addition-progress",
        (false, BinaryOp::Add) => "unsigned-addition-progress",
        (true, BinaryOp::DivideSigned) => "signed-division-progress",
        (false, BinaryOp::DivideUnsigned) => "unsigned-division-progress",
        (true, BinaryOp::RemainderSigned) => "signed-remainder-progress",
        (false, BinaryOp::RemainderUnsigned) => "unsigned-remainder-progress",
        (true, BinaryOp::Multiply) => "signed-multiplication-progress",
        (false, BinaryOp::Multiply) => "unsigned-multiplication-progress",
        (true, BinaryOp::Subtract) => "signed-subtraction-progress",
        (false, BinaryOp::Subtract) => "unsigned-subtraction-progress",
        (_, _) => "unsupported-arithmetic-progress",
    }
}

fn inspect_arithmetic_progress_case(
    signed: bool,
    operation: BinaryOp,
) -> Result<(), String> {
    let (expected, projection) = lowered_arithmetic_fixture(signed, operation)?;
    let fresh = enter_ternary_compiler_stage(TernaryCompilerStageInput::Fresh(
        &projection,
    ))
    .map_err(|error| format!("select fresh arithmetic: {error:?}"))?;
    if fresh != expected {
        return Err(String::from("fresh arithmetic projection drifted"));
    }
    let bytes = canonical_ternary_bytes(&expected)
        .map_err(|error| format!("encode arithmetic progress: {error:?}"))?;
    let (progress, directory) = publish_ternary_progress_fixture(
        arithmetic_case_label(signed, operation),
        &bytes,
    )?;
    let resumed =
        enter_ternary_compiler_stage(TernaryCompilerStageInput::Progress {
            inspector: &progress_inspector(),
            interpreter: &repository_python(),
            progress: &progress,
        });
    remove_dir_all(&directory)
        .map_err(|error| format!("clean arithmetic progress: {error}"))?;
    if resumed != Ok(expected) {
        return Err(String::from("arithmetic inspector recovery drifted"));
    }
    Ok(())
}

const fn shift_case_label(signed: bool, operation: BinaryOp) -> &'static str {
    match (signed, operation) {
        (true, BinaryOp::ShiftLeft) => "signed-left-shift",
        (false, BinaryOp::ShiftLeft) => "unsigned-left-shift",
        (true, BinaryOp::ShiftRightArithmetic) => "signed-arithmetic-shift",
        (false, BinaryOp::ShiftRightLogical) => "unsigned-logical-shift",
        _ => "unsupported-shift-case",
    }
}

fn check_shift_progress(
    signed: bool,
    operation: BinaryOp,
) -> Result<(), String> {
    let (expected, projection) = lowered_shift_fixture(signed, operation)?;
    let fresh = enter_ternary_compiler_stage(TernaryCompilerStageInput::Fresh(
        &projection,
    ))
    .map_err(|error| format!("select fresh shift: {error:?}"))?;
    if fresh != expected {
        return Err(String::from("fresh shift selection drifted"));
    }
    let encoded = canonical_ternary_bytes(&fresh)
        .map_err(|error| format!("encode shift progress: {error:?}"))?;
    let (progress, directory) = publish_ternary_progress_fixture(
        shift_case_label(signed, operation),
        &encoded,
    )?;
    let resumed =
        enter_ternary_compiler_stage(TernaryCompilerStageInput::Progress {
            inspector: &progress_inspector(),
            interpreter: &repository_python(),
            progress: &progress,
        });
    remove_dir_all(&directory)
        .map_err(|error| format!("clean shift progress: {error}"))?;
    if resumed != Ok(expected) {
        return Err(String::from("shift inspector recovery drifted"));
    }
    Ok(())
}

#[test]
fn ternary_shift_selector_converges_with_inspector_progress()
-> Result<(), String> {
    for (signed, operation) in shift_cases() {
        check_shift_progress(signed, operation)?;
    }
    Ok(())
}

#[test]
fn ternary_shift_crash_resume_preserves_generation() -> Result<(), String> {
    let previous = lowered_return_fixture()?;
    for (signed, operation) in shift_cases() {
        let (next, _projection) = lowered_shift_fixture(signed, operation)?;
        if previous == next {
            return Err(String::from("shift generation is not distinct"));
        }
        for boundary in TERNARY_CRASH_BOUNDARIES {
            run_ternary_crash_boundary(boundary, &previous, &next)?;
        }
    }
    Ok(())
}

#[test]
fn ternary_arithmetic_selector_converges_with_inspector_progress()
-> Result<(), String> {
    for (signed, operation) in arithmetic_cases() {
        inspect_arithmetic_progress_case(signed, operation)?;
    }
    Ok(())
}

#[test]
fn ternary_arithmetic_progress_rejects_forged_types() -> Result<(), String> {
    for (signed, operation) in arithmetic_cases() {
        check_arithmetic_progress_forgery(signed, operation)?;
    }
    Ok(())
}

const fn arithmetic_forgery_label(
    signed: bool,
    operation: BinaryOp,
) -> &'static str {
    match (signed, operation) {
        (true, BinaryOp::Add) => "forged-signed-addition",
        (false, BinaryOp::Add) => "forged-unsigned-addition",
        (true, BinaryOp::DivideSigned) => "forged-signed-division",
        (false, BinaryOp::DivideUnsigned) => "forged-unsigned-division",
        (true, BinaryOp::RemainderSigned) => "forged-signed-remainder",
        (false, BinaryOp::RemainderUnsigned) => "forged-unsigned-remainder",
        (true, BinaryOp::Multiply) => "forged-signed-multiplication",
        (false, BinaryOp::Multiply) => "forged-unsigned-multiplication",
        (true, BinaryOp::Subtract) => "forged-signed-subtraction",
        (false, BinaryOp::Subtract) => "forged-unsigned-subtraction",
        (_, _) => "forged-unrecognized-arithmetic",
    }
}

fn check_arithmetic_progress_forgery(
    signed: bool,
    operation: BinaryOp,
) -> Result<(), String> {
    let (target, _projection) = lowered_arithmetic_fixture(signed, operation)?;
    let mut bytes = canonical_ternary_bytes(&target)
        .map_err(|error| format!("encode forged arithmetic: {error:?}"))?;
    let (_expected, tag) = arithmetic_target_operation(signed, operation)?;
    let swapped = if signed {
        tag.saturating_add(1)
    } else {
        tag.saturating_sub(1)
    };
    let prefix = [tag, 0, 0, 0, 0, 2, 0, 0, 0, 1, 0, 0, 0];
    let offset = bytes
        .windows(prefix.len())
        .position(|wire| wire == prefix)
        .ok_or_else(|| String::from("arithmetic progress tag missing"))?;
    *bytes
        .get_mut(offset)
        .ok_or_else(|| String::from("arithmetic progress opcode missing"))? =
        swapped;
    let (progress, directory) = publish_ternary_progress_fixture(
        arithmetic_forgery_label(signed, operation),
        &bytes,
    )?;
    let rejected = resume_ternary_from_progress(
        &repository_python(),
        &progress_inspector(),
        &progress,
    );
    remove_dir_all(&directory)
        .map_err(|error| format!("clean forged arithmetic: {error}"))?;
    let expected = Err(TernaryProgressCheckpointError::Stage(
        TernaryStageError::Checkpoint(TernaryProgramCodecError::Validation(
            TernaryProgramValidationError::SsaValue,
        )),
    ));
    if rejected != expected {
        return Err(String::from("forged arithmetic signedness accepted"));
    }
    Ok(())
}

#[test]
fn ternary_arithmetic_crash_resume_preserves_generation() -> Result<(), String>
{
    let previous = lowered_return_fixture()?;
    for (signed, operation) in arithmetic_cases() {
        let (next, _projection) =
            lowered_arithmetic_fixture(signed, operation)?;
        if previous == next {
            return Err(String::from("arithmetic generation is not distinct"));
        }
        for boundary in TERNARY_CRASH_BOUNDARIES {
            run_ternary_crash_boundary(boundary, &previous, &next)?;
        }
    }
    Ok(())
}

const fn same_kind_progress_label(signed: bool) -> &'static str {
    if signed {
        "same-kind-signed-progress"
    } else {
        "same-kind-unsigned-progress"
    }
}

const fn same_kind_forged_label(signed: bool) -> &'static str {
    if signed {
        "forged-same-kind-signed"
    } else {
        "forged-same-kind-unsigned"
    }
}

fn inspect_same_kind_progress(signed: bool) -> Result<(), String> {
    let (expected, projection) =
        lowered_same_kind_bitcast_fixture(signed, 0x8000_0080)?;
    let fresh = enter_ternary_compiler_stage(TernaryCompilerStageInput::Fresh(
        &projection,
    ))
    .map_err(|error| format!("select same-kind fresh: {error:?}"))?;
    if fresh != expected {
        return Err(String::from("same-kind fresh selection drifted"));
    }
    let bytes = canonical_ternary_bytes(&fresh)
        .map_err(|error| format!("encode same-kind progress: {error:?}"))?;
    let (progress, directory) = publish_ternary_progress_fixture(
        same_kind_progress_label(signed),
        &bytes,
    )?;
    let resumed =
        enter_ternary_compiler_stage(TernaryCompilerStageInput::Progress {
            inspector: &progress_inspector(),
            interpreter: &repository_python(),
            progress: &progress,
        });
    remove_dir_all(&directory)
        .map_err(|error| format!("clean same-kind progress: {error}"))?;
    if resumed != Ok(expected) {
        return Err(String::from("same-kind inspector recovery changed SSA"));
    }
    Ok(())
}

#[test]
fn ternary_identity_bitcast_inspector_matches_fresh_compilation()
-> Result<(), String> {
    for signed in [true, false] {
        inspect_same_kind_progress(signed)?;
    }
    Ok(())
}

fn check_same_kind_progress_forgery(signed: bool) -> Result<(), String> {
    let (target, _projection) =
        lowered_same_kind_bitcast_fixture(signed, u32::MAX)?;
    let mut bytes = canonical_ternary_bytes(&target)
        .map_err(|error| format!("encode forged identity state: {error:?}"))?;
    let (_operation, tag) = same_kind_bitcast_operation(signed);
    let switched = if signed {
        34u8
    } else {
        33u8
    };
    let offset = bytes
        .windows(5)
        .position(|wire| wire == [tag, 1, 0, 0, 0])
        .ok_or_else(|| String::from("identity progress cast missing"))?;
    *bytes
        .get_mut(offset)
        .ok_or_else(|| String::from("identity progress opcode missing"))? =
        switched;
    let (progress, directory) = publish_ternary_progress_fixture(
        same_kind_forged_label(signed),
        &bytes,
    )?;
    let rejected = resume_ternary_from_progress(
        &repository_python(),
        &progress_inspector(),
        &progress,
    );
    remove_dir_all(&directory)
        .map_err(|error| format!("clean forged identity progress: {error}"))?;
    let expected = Err(TernaryProgressCheckpointError::Stage(
        TernaryStageError::Checkpoint(TernaryProgramCodecError::Validation(
            TernaryProgramValidationError::SsaValue,
        )),
    ));
    if rejected != expected {
        return Err(String::from("identity checkpoint type swap admitted"));
    }
    Ok(())
}

#[test]
fn ternary_identity_bitcast_inspector_rejects_signedness_forgery()
-> Result<(), String> {
    for signed in [true, false] {
        check_same_kind_progress_forgery(signed)?;
    }
    Ok(())
}

#[test]
fn ternary_identity_bitcast_crashes_preserve_committed_generation()
-> Result<(), String> {
    let previous = lowered_return_fixture()?;
    for signed in [true, false] {
        let (next, _projection) =
            lowered_same_kind_bitcast_fixture(signed, 0x8000_0080)?;
        if previous == next {
            return Err(String::from("identity crash generation unchanged"));
        }
        for boundary in TERNARY_CRASH_BOUNDARIES {
            run_ternary_crash_boundary(boundary, &previous, &next)?;
        }
    }
    Ok(())
}

#[test]
fn ternary_integer_bitcast_selector_matches_inspector_progress()
-> Result<(), String> {
    for (source_signed, label) in [
        (true, "signed-to-unsigned-bitcast"),
        (false, "unsigned-to-signed-bitcast"),
    ] {
        let (expected, projection) =
            lowered_integer_bitcast_fixture(source_signed, 0x8000_0080)?;
        let fresh = enter_ternary_compiler_stage(
            TernaryCompilerStageInput::Fresh(&projection),
        )
        .map_err(|error| format!("select fresh integer bitcast: {error:?}"))?;
        if fresh != expected {
            return Err(String::from("bitcast fresh stage drifted"));
        }
        let bytes = canonical_ternary_bytes(&fresh)
            .map_err(|error| format!("encode bitcast progress: {error:?}"))?;
        let (progress, directory) =
            publish_ternary_progress_fixture(label, &bytes)?;
        let resumed =
            enter_ternary_compiler_stage(TernaryCompilerStageInput::Progress {
                inspector: &progress_inspector(),
                interpreter: &repository_python(),
                progress: &progress,
            });
        remove_dir_all(&directory)
            .map_err(|error| format!("clean bitcast progress: {error}"))?;
        if resumed != Ok(expected) {
            return Err(String::from("bitcast inspector recovery drifted"));
        }
    }
    Ok(())
}

#[test]
fn ternary_integer_bitcast_progress_rejects_direction_forgery()
-> Result<(), String> {
    for (source_signed, label) in [
        (true, "forged-i32-to-u32-bitcast"),
        (false, "forged-u32-to-i32-bitcast"),
    ] {
        let (target, _projection) =
            lowered_integer_bitcast_fixture(source_signed, u32::MAX)?;
        let mut bytes = canonical_ternary_bytes(&target)
            .map_err(|error| format!("encode forged bitcast: {error:?}"))?;
        let tag = if source_signed {
            17u8
        } else {
            18u8
        };
        let flipped = if source_signed {
            18u8
        } else {
            17u8
        };
        let offset = bytes
            .windows(5)
            .position(|wire| wire == [tag, 1, 0, 0, 0])
            .ok_or_else(|| String::from("bitcast progress tag missing"))?;
        *bytes
            .get_mut(offset)
            .ok_or_else(|| String::from("bitcast wire offset missing"))? =
            flipped;
        let (progress, directory) =
            publish_ternary_progress_fixture(label, &bytes)?;
        let rejected = resume_ternary_from_progress(
            &repository_python(),
            &progress_inspector(),
            &progress,
        );
        remove_dir_all(&directory).map_err(|error| {
            format!("clean forged bitcast progress: {error}")
        })?;
        let expected = Err(TernaryProgressCheckpointError::Stage(
            TernaryStageError::Checkpoint(
                TernaryProgramCodecError::Validation(
                    TernaryProgramValidationError::SsaValue,
                ),
            ),
        ));
        if rejected != expected {
            return Err(String::from(
                "forged bitcast direction passed inspector",
            ));
        }
    }
    Ok(())
}

#[test]
fn ternary_integer_bitcast_crashes_preserve_committed_direction()
-> Result<(), String> {
    let previous = lowered_return_fixture()?;
    for source_signed in [true, false] {
        let (next, _projection) =
            lowered_integer_bitcast_fixture(source_signed, 0x8000_0080)?;
        if previous == next {
            return Err(String::from("bitcast generation is not distinct"));
        }
        for boundary in TERNARY_CRASH_BOUNDARIES {
            run_ternary_crash_boundary(boundary, &previous, &next)?;
        }
    }
    Ok(())
}

fn assert_boolean_inspector_convergence(
    label: &str,
    target: &ternary_lowering::TernaryProgram,
    projection: &TypedIrInput,
) -> Result<(), String> {
    let fresh = enter_ternary_compiler_stage(TernaryCompilerStageInput::Fresh(
        projection,
    ))
    .map_err(|error| format!("fresh Boolean stage: {error:?}"))?;
    if &fresh != target {
        return Err(format!("fresh Boolean selector {label} drifted"));
    }
    let encoded = canonical_ternary_bytes(target)
        .map_err(|error| format!("encode Boolean progress: {error:?}"))?;
    let (progress, directory) =
        publish_ternary_progress_fixture(label, &encoded)?;
    let resumed =
        enter_ternary_compiler_stage(TernaryCompilerStageInput::Progress {
            inspector: &progress_inspector(),
            interpreter: &repository_python(),
            progress: &progress,
        });
    remove_dir_all(&directory)
        .map_err(|error| format!("clean Boolean progress: {error}"))?;
    if resumed != Ok(target.clone()) {
        return Err(format!("inspector Boolean selector {label} drifted"));
    }
    Ok(())
}

fn check_boolean_comparison_inspector_cases() -> Result<(), String> {
    for (signed, operation, label) in [
        (true, CompareOp::Equal, "bool-equal-signed"),
        (false, CompareOp::NotEqual, "bool-not-equal-unsigned"),
        (true, CompareOp::LessSigned, "bool-less-signed"),
        (true, CompareOp::LessSignedEqual, "bool-le-signed"),
        (false, CompareOp::LessUnsigned, "bool-less-unsigned"),
        (false, CompareOp::LessUnsignedEqual, "bool-le-unsigned"),
    ] {
        let case = ComparisonFixture {
            alias: false,
            left: 0x8000_0000,
            operation,
            right: u32::MAX,
            signed,
        };
        let (target, projection) = lowered_integer_comparison_fixture(case)?;
        assert_boolean_inspector_convergence(label, &target, &projection)?;
    }
    Ok(())
}

#[test]
fn ternary_boolean_comparisons_and_casts_restore_through_inspector()
-> Result<(), String> {
    for (signed, label) in [
        (true, "bool-to-i32-signed-input"),
        (false, "bool-to-i32-unsigned-input"),
    ] {
        let (target, projection) =
            lowered_integer_to_bool_fixture(signed, u32::MAX)?;
        assert_boolean_inspector_convergence(label, &target, &projection)?;
    }
    for (source, label) in [
        (None, "byte-to-bool-input"),
        (Some(u8::MAX), "byte-to-bool-literal"),
    ] {
        let (target, projection) = lowered_byte_to_bool_fixture(source)?;
        assert_boolean_inspector_convergence(label, &target, &projection)?;
    }
    let (target, projection) = lowered_bool_to_signed_fixture(u32::MAX, 0)?;
    assert_boolean_inspector_convergence(
        "bool-to-signed-conversion",
        &target,
        &projection,
    )?;
    check_boolean_comparison_inspector_cases()
}

fn assert_boolean_progress_tag_rejected(
    label: &str,
    program: &ternary_lowering::TernaryProgram,
    tags: (u8, u32, u8),
) -> Result<(), String> {
    let (tag, result, replacement) = tags;
    let mut bytes = canonical_ternary_bytes(program)
        .map_err(|error| format!("encode forged Boolean state: {error:?}"))?;
    let mut needle = vec![tag];
    if (35..=43).contains(&tag) {
        needle.extend_from_slice(&0u32.to_le_bytes());
    }
    needle.extend_from_slice(&result.to_le_bytes());
    let offset = bytes
        .windows(needle.len())
        .position(|part| part == needle)
        .ok_or_else(|| String::from("Boolean tag absent"))?;
    *bytes
        .get_mut(offset)
        .ok_or_else(|| String::from("Boolean tag offset absent"))? =
        replacement;
    let (progress, directory) =
        publish_ternary_progress_fixture(label, &bytes)?;
    let rejected = resume_ternary_from_progress(
        &repository_python(),
        &progress_inspector(),
        &progress,
    );
    remove_dir_all(&directory)
        .map_err(|error| format!("clean forged Boolean state: {error}"))?;
    let expected = if replacement == 84 {
        TernaryProgramCodecError::UnknownTag
    } else {
        TernaryProgramCodecError::Validation(
            TernaryProgramValidationError::SsaValue,
        )
    };
    if rejected
        != Err(TernaryProgressCheckpointError::Stage(
            TernaryStageError::Checkpoint(expected),
        ))
    {
        return Err(format!("forged Boolean inspector tag {label} admitted"));
    }
    Ok(())
}

fn assert_boolean_crash_generation(
    previous: &ternary_lowering::TernaryProgram,
    next: &ternary_lowering::TernaryProgram,
) -> Result<(), String> {
    if previous == next {
        return Err(String::from("Boolean crash generations coincide"));
    }
    for boundary in TERNARY_CRASH_BOUNDARIES {
        run_ternary_crash_boundary(boundary, previous, next)?;
    }
    Ok(())
}

#[test]
fn boolean_constant_inspector_matches_fresh_stage_and_crash_resume()
-> Result<(), String> {
    let previous = lowered_return_fixture()?;
    for bit in [0u8, 1] {
        for promoted in [false, true] {
            let (target, projection) =
                lowered_boolean_constant_fixture(bit, promoted)?;
            let label = match (bit, promoted) {
                (0, false) => "false-constant-return",
                (0, true) => "false-promoted-return",
                (1, false) => "true-constant-return",
                _ => "true-promoted-return",
            };
            assert_boolean_inspector_convergence(label, &target, &projection)?;
            assert_boolean_crash_generation(&previous, &target)?;
        }
    }
    Ok(())
}

fn assert_boolean_constant_inspector_invalid(
    label: &str,
    bit: u8,
    replacement: u8,
    error: TernaryProgramCodecError,
) -> Result<(), String> {
    let (target, _projection) = lowered_boolean_constant_fixture(bit, false)?;
    let mut encoded = assert_boolean_constant_checkpoint(bit, false, &target)?;
    let offset = encoded
        .windows(6)
        .position(|chunk| chunk == [48, 0, 0, 0, 0, bit])
        .ok_or_else(|| String::from("Boolean constant checkpoint absent"))?;
    let index = if replacement == 84 {
        offset
    } else {
        offset.saturating_add(5)
    };
    *encoded
        .get_mut(index)
        .ok_or_else(|| String::from("Boolean constant mutation absent"))? =
        replacement;
    let (progress, directory) =
        publish_ternary_progress_fixture(label, &encoded)?;
    let restored = resume_ternary_from_progress(
        &repository_python(),
        &progress_inspector(),
        &progress,
    );
    remove_dir_all(&directory)
        .map_err(|failure| format!("clean Boolean forgery: {failure}"))?;
    if restored
        != Err(TernaryProgressCheckpointError::Stage(
            TernaryStageError::Checkpoint(error),
        ))
    {
        return Err(format!("inspector admitted malformed Boolean {label}"));
    }
    Ok(())
}

#[test]
fn boolean_constant_inspector_rejects_invalid_digit_and_opcode()
-> Result<(), String> {
    for bit in [0u8, 1] {
        assert_boolean_constant_inspector_invalid(
            "invalid-boolean-digit",
            bit,
            2,
            TernaryProgramCodecError::InvalidScalar,
        )?;
        assert_boolean_constant_inspector_invalid(
            "unknown-boolean-materialization",
            bit,
            84,
            TernaryProgramCodecError::UnknownTag,
        )?;
    }
    Ok(())
}

#[test]
fn ternary_boolean_cast_crash_resume_keeps_committed_generation()
-> Result<(), String> {
    let previous = lowered_return_fixture()?;
    for source in [None, Some(u8::MAX)] {
        let (next, _input) = lowered_byte_to_bool_fixture(source)?;
        assert_boolean_crash_generation(&previous, &next)?;
    }
    for signed in [true, false] {
        let (next, _input) = lowered_integer_to_bool_fixture(signed, u32::MAX)?;
        assert_boolean_crash_generation(&previous, &next)?;
    }
    let (promoted, _promotion_projection) =
        lowered_bool_to_signed_fixture(u32::MAX, 0)?;
    assert_boolean_crash_generation(&previous, &promoted)?;
    let (truncated, _truncation_projection) =
        lowered_truncated_byte_truth_fixture(0x8000_0080)?;
    assert_boolean_crash_generation(&previous, &truncated)?;
    for (signed, operation) in [
        (true, CompareOp::LessSigned),
        (false, CompareOp::LessUnsigned),
    ] {
        let (compared, _comparison_projection) =
            lowered_integer_comparison_fixture(ComparisonFixture {
                alias: false,
                left: 0x8000_0000,
                operation,
                right: u32::MAX,
                signed,
            })?;
        assert_boolean_crash_generation(&previous, &compared)?;
    }
    Ok(())
}

#[test]
fn ternary_boolean_inspector_rejects_cross_width_and_unknown_tags()
-> Result<(), String> {
    for (signed, tag, swapped, label) in [
        (true, 45u8, 46u8, "forged-signed-truth"),
        (false, 46, 45, "forged-unsigned-truth"),
    ] {
        let (target, _projection) =
            lowered_integer_to_bool_fixture(signed, u32::MAX)?;
        assert_boolean_progress_tag_rejected(
            label,
            &target,
            (tag, 1, swapped),
        )?;
    }
    let (byte, _projection) = lowered_byte_to_bool_fixture(Some(0xff))?;
    assert_boolean_progress_tag_rejected(
        "forged-byte-truth",
        &byte,
        (47, 1, 46),
    )?;
    assert_boolean_progress_tag_rejected(
        "unknown-byte-truth",
        &byte,
        (47, 1, 84),
    )?;
    let (converted, _converted_projection) =
        lowered_bool_to_signed_fixture(0, u32::MAX)?;
    assert_boolean_progress_tag_rejected(
        "forged-bool-to-signed",
        &converted,
        (44, 3, 33),
    )
}

#[test]
fn ternary_truncated_byte_truth_chain_restores_through_inspector()
-> Result<(), String> {
    for (bits, label) in [
        (0u32, "truncated-byte-zero"),
        (1, "truncated-byte-one"),
        (0x100, "truncated-byte-carry-only"),
        (0x8000_0080, "truncated-byte-high-bit"),
        (u32::MAX, "truncated-byte-maximum"),
    ] {
        let (target, input) = lowered_truncated_byte_truth_fixture(bits)?;
        assert_truncated_byte_truth_operations(bits, &target)?;
        assert_boolean_inspector_convergence(label, &target, &input)?;
    }
    Ok(())
}

#[test]
fn ternary_comparison_inspector_rejects_signedness_swap() -> Result<(), String>
{
    for (signed, operation, tag, swapped, label) in [
        (true, CompareOp::Equal, 35u8, 36u8, "forged-signed-equal"),
        (false, CompareOp::Equal, 36, 35, "forged-unsigned-equal"),
        (true, CompareOp::NotEqual, 37, 38, "forged-signed-not-equal"),
        (
            false,
            CompareOp::NotEqual,
            38,
            37,
            "forged-unsigned-not-equal",
        ),
        (true, CompareOp::LessSigned, 40, 42, "forged-signed-less"),
        (
            false,
            CompareOp::LessUnsigned,
            42,
            40,
            "forged-unsigned-less",
        ),
    ] {
        let (target, _input) =
            lowered_integer_comparison_fixture(ComparisonFixture {
                alias: false,
                left: 0x8000_0000,
                operation,
                right: u32::MAX,
                signed,
            })?;
        assert_boolean_progress_tag_rejected(
            label,
            &target,
            (tag, 2, swapped),
        )?;
    }
    Ok(())
}

#[test]
fn ternary_zero_extension_selector_converges_with_progress()
-> Result<(), String> {
    for (source, label) in [
        (None, "zero-extend-byte-input"),
        (Some(255), "zero-extend-byte-literal"),
    ] {
        let (expected, projection) =
            lowered_unsigned_zero_extend_fixture(source)?;
        let fresh = enter_ternary_compiler_stage(
            TernaryCompilerStageInput::Fresh(&projection),
        )
        .map_err(|error| format!("fresh zero-extension stage: {error:?}"))?;
        if fresh != expected {
            return Err(String::from(
                "fresh zero-extension projection drifted",
            ));
        }
        let bytes = canonical_ternary_bytes(&fresh)
            .map_err(|error| format!("encode widening progress: {error:?}"))?;
        let (progress, directory) =
            publish_ternary_progress_fixture(label, &bytes)?;
        let resumed =
            enter_ternary_compiler_stage(TernaryCompilerStageInput::Progress {
                inspector: &progress_inspector(),
                interpreter: &repository_python(),
                progress: &progress,
            });
        remove_dir_all(&directory)
            .map_err(|error| format!("clean widening progress: {error}"))?;
        if resumed != Ok(expected) {
            return Err(String::from("widening inspector recovery drifted"));
        }
    }
    Ok(())
}

#[test]
fn ternary_zero_extension_crash_resume_preserves_signedness()
-> Result<(), String> {
    let previous = lowered_return_fixture()?;
    let (next, _projection) = lowered_unsigned_zero_extend_fixture(Some(255))?;
    if previous == next {
        return Err(String::from("widened and signed checkpoints coincide"));
    }
    for boundary in TERNARY_CRASH_BOUNDARIES {
        run_ternary_crash_boundary(boundary, &previous, &next)?;
    }
    Ok(())
}

#[test]
fn ternary_unsigned_bitwise_selector_converges_with_progress()
-> Result<(), String> {
    for (operation, label) in [
        (BinaryOp::And, "unsigned-bitwise-and-selector"),
        (BinaryOp::Or, "unsigned-bitwise-or-selector"),
        (BinaryOp::Xor, "unsigned-bitwise-xor-selector"),
    ] {
        let (expected, projection) =
            lowered_unsigned_bitwise_fixture(u32::MAX, 0x8000_0000, operation)?;
        let fresh = enter_ternary_compiler_stage(
            TernaryCompilerStageInput::Fresh(&projection),
        )
        .map_err(|error| format!("select fresh unsigned bitwise: {error:?}"))?;
        if fresh != expected {
            return Err(String::from(
                "fresh unsigned bitwise compiler drifted",
            ));
        }
        let bytes = canonical_ternary_bytes(&fresh).map_err(|error| {
            format!("encode unsigned bitwise progress: {error:?}")
        })?;
        let (progress, directory) =
            publish_ternary_progress_fixture(label, &bytes)?;
        let resumed =
            enter_ternary_compiler_stage(TernaryCompilerStageInput::Progress {
                inspector: &progress_inspector(),
                interpreter: &repository_python(),
                progress: &progress,
            });
        remove_dir_all(&directory).map_err(|error| {
            format!("clean unsigned bitwise progress: {error}")
        })?;
        if resumed != Ok(expected) {
            return Err(String::from(
                "unsigned bitwise progress did not converge",
            ));
        }
    }
    Ok(())
}

#[test]
fn ternary_unsigned_bitwise_progress_rejects_signed_opcode()
-> Result<(), String> {
    for (operation, tag, signed_tag, label) in [
        (BinaryOp::And, 12u8, 0u8, "forged-unsigned-and"),
        (BinaryOp::Or, 13u8, 6u8, "forged-unsigned-or"),
        (BinaryOp::Xor, 14u8, 7u8, "forged-unsigned-xor"),
    ] {
        let (program, _projection) =
            lowered_unsigned_bitwise_fixture(u32::MAX, 0x8000_0000, operation)?;
        let mut bytes = canonical_ternary_bytes(&program).map_err(|error| {
            format!("encode forged unsigned bitwise: {error:?}")
        })?;
        let pattern = [tag, 0, 0, 0, 0, 2, 0, 0, 0, 1, 0, 0, 0];
        let offset = bytes
            .windows(pattern.len())
            .position(|window| window == pattern)
            .ok_or_else(|| {
                String::from("unsigned bitwise wire position missing")
            })?;
        *bytes
            .get_mut(offset)
            .ok_or_else(|| String::from("unsigned bitwise tag missing"))? =
            signed_tag;
        let (progress, directory) =
            publish_ternary_progress_fixture(label, &bytes)?;
        let rejected = resume_ternary_from_progress(
            &repository_python(),
            &progress_inspector(),
            &progress,
        );
        remove_dir_all(&directory).map_err(|error| {
            format!("clean forged bitwise progress: {error}")
        })?;
        let expected = Err(TernaryProgressCheckpointError::Stage(
            TernaryStageError::Checkpoint(
                TernaryProgramCodecError::Validation(
                    TernaryProgramValidationError::SsaValue,
                ),
            ),
        ));
        if rejected != expected {
            return Err(String::from(
                "forged signed bitwise tag passed inspector",
            ));
        }
    }
    Ok(())
}

#[test]
fn ternary_unsigned_bitwise_crash_resume_preserves_generation()
-> Result<(), String> {
    let previous = lowered_return_fixture()?;
    let (next, _projection) =
        lowered_unsigned_bitwise_fixture(u32::MAX, 0x8000_0000, BinaryOp::Xor)?;
    if previous == next {
        return Err(String::from("signed and unsigned generations coincide"));
    }
    for boundary in TERNARY_CRASH_BOUNDARIES {
        run_ternary_crash_boundary(boundary, &previous, &next)?;
    }
    Ok(())
}

#[test]
fn ternary_byte_return_compiler_selector_converges_through_progress()
-> Result<(), String> {
    let (expected, projection) = lowered_byte_return_fixture(Some(255))?;
    let fresh = enter_ternary_compiler_stage(TernaryCompilerStageInput::Fresh(
        &projection,
    ))
    .map_err(|error| format!("select byte-return fresh state: {error:?}"))?;
    if fresh != expected {
        return Err(String::from(
            "fresh compiler byte-return selection drifted",
        ));
    }
    let bytes = canonical_ternary_bytes(&fresh).map_err(|error| {
        format!("encode byte-return selector state: {error:?}")
    })?;
    let (progress, directory) =
        publish_ternary_progress_fixture("byte-return-selector", &bytes)?;
    let resumed =
        enter_ternary_compiler_stage(TernaryCompilerStageInput::Progress {
            inspector: &progress_inspector(),
            interpreter: &repository_python(),
            progress: &progress,
        });
    remove_dir_all(&directory).map_err(|error| {
        format!("remove byte-return selector fixture: {error}")
    })?;
    if resumed != Ok(expected) {
        return Err(String::from(
            "byte-return progress selector did not converge",
        ));
    }
    Ok(())
}

#[test]
fn ternary_byte_return_progress_rejects_forged_terminator_kind()
-> Result<(), String> {
    let (program, _projection) = lowered_byte_return_fixture(Some(255))?;
    let mut bytes = canonical_ternary_bytes(&program)
        .map_err(|error| format!("encode byte-return checkpoint: {error:?}"))?;
    let tag_offset = bytes
        .len()
        .checked_sub(29)
        .ok_or_else(|| String::from("byte-return terminator span missing"))?;
    *bytes
        .get_mut(tag_offset)
        .ok_or_else(|| String::from("byte-return terminator tag missing"))? = 4;
    let (progress, directory) =
        publish_ternary_progress_fixture("byte-return-forged", &bytes)?;
    let rejected = resume_ternary_from_progress(
        &repository_python(),
        &progress_inspector(),
        &progress,
    );
    remove_dir_all(&directory).map_err(|error| {
        format!("remove forged byte-return fixture: {error}")
    })?;
    let expected = Err(TernaryProgressCheckpointError::Stage(
        TernaryStageError::Checkpoint(TernaryProgramCodecError::Validation(
            TernaryProgramValidationError::SsaValue,
        )),
    ));
    if rejected != expected {
        return Err(String::from("forged byte-return checkpoint was admitted"));
    }
    Ok(())
}

#[test]
fn ternary_byte_return_crash_resume_recovers_committed_generation()
-> Result<(), String> {
    let previous = lowered_return_fixture()?;
    let (next, _projection) = lowered_byte_return_fixture(None)?;
    if previous == next {
        return Err(String::from(
            "crash generations must have distinct returns",
        ));
    }
    for boundary in TERNARY_CRASH_BOUNDARIES {
        run_ternary_crash_boundary(boundary, &previous, &next)?;
    }
    Ok(())
}

#[test]
fn ternary_compiler_selector_preserves_progress_failure_route() {
    let missing =
        temp_dir().join(format!("malbolge-missing-ternary-selector-{}", id()));
    assert_eq!(
        enter_ternary_compiler_stage(TernaryCompilerStageInput::Progress {
            inspector: &missing,
            interpreter: &missing,
            progress: &missing,
        }),
        Err(TernaryCompilerStageError::Progress(
            TernaryProgressCheckpointError::InspectorLaunch,
        )),
    );
}

#[test]
fn ternary_stage_fresh_and_checkpoint_inputs_converge() -> Result<(), String> {
    let module = admitted_golden(RETURN_GOLDEN)?;
    let projection = project_typed_ir(&module)?;
    let fresh = enter_ternary_stage(TernaryStageInput::Projection(&projection))
        .map_err(|error| format!("enter fresh ternary stage: {error:?}"))?;
    let checkpoint = canonical_ternary_bytes(&fresh)
        .map_err(|error| format!("encode ternary checkpoint: {error:?}"))?;
    let resumed =
        enter_ternary_stage(TernaryStageInput::Checkpoint(&checkpoint))
            .map_err(|error| {
                format!("enter resumed ternary stage: {error:?}")
            })?;
    if fresh != resumed {
        return Err(String::from(
            "fresh and resumed ternary stage outputs diverged",
        ));
    }
    Ok(())
}

#[test]
fn ternary_stage_rejects_malformed_checkpoint() {
    assert_eq!(
        enter_ternary_stage(TernaryStageInput::Checkpoint(b"bad")),
        Err(TernaryStageError::Checkpoint(
            TernaryProgramCodecError::Truncated,
        )),
    );
}

#[test]
fn progress_crash_resume_restores_committed_ternary() -> Result<(), String> {
    let first = lowered_return_fixture()?;
    let second_projection = projected_byte_io_fixture()?;
    let second = lower_typed_ir(&second_projection).map_err(|error| {
        format!("lower second ternary crash state: {error:?}")
    })?;
    if first == second {
        return Err(String::from("ternary crash generations are not distinct"));
    }
    for boundary in TERNARY_CRASH_BOUNDARIES {
        run_ternary_crash_boundary(boundary, &first, &second)?;
    }
    Ok(())
}

#[test]
fn progress_adapter_restores_verified_ternary_state() -> Result<(), String> {
    let program = lowered_return_fixture()?;
    let bytes = canonical_ternary_bytes(&program).map_err(|error| {
        format!("encode ternary progress fixture: {error:?}")
    })?;
    let (progress, directory) =
        publish_ternary_progress_fixture("adapter", &bytes)?;
    let observed = resume_ternary_from_progress(
        &repository_python(),
        &progress_inspector(),
        &progress,
    );
    remove_dir_all(&directory)
        .map_err(|error| format!("remove ternary progress fixture: {error}"))?;
    if observed != Ok(program) {
        return Err(String::from(
            "verified progress checkpoint did not restore ternary state",
        ));
    }
    Ok(())
}

#[test]
fn progress_adapter_rejects_relocated_valid_sidecar() -> Result<(), String> {
    let program = lowered_return_fixture()?;
    let bytes = canonical_ternary_bytes(&program)
        .map_err(|error| format!("encode ternary checkpoint: {error:?}"))?;
    let (progress, directory) =
        publish_ternary_progress_fixture("relocated", &bytes)?;
    let relocated = directory.join("copied-progress.json");
    let _copied = copy(&progress, &relocated)
        .map_err(|error| format!("copy ternary progress pointer: {error}"))?;
    let rejected = resume_ternary_from_progress(
        &repository_python(),
        &progress_inspector(),
        &relocated,
    );
    let accepted = resume_ternary_from_progress(
        &repository_python(),
        &progress_inspector(),
        &progress,
    );
    remove_dir_all(&directory)
        .map_err(|error| format!("remove ternary progress fixture: {error}"))?;
    if rejected != Err(TernaryProgressCheckpointError::InspectorRejected) {
        return Err(String::from("relocated ternary pointer was admitted"));
    }
    if accepted != Ok(program) {
        return Err(String::from("original ternary pointer was rejected"));
    }
    Ok(())
}

#[test]
fn progress_adapter_rejects_inspector_diagnostics() -> Result<(), String> {
    let inspector = temporary_ternary_file(
        "inspector-diagnostic",
        "py",
        TERNARY_INSPECTOR_DIAGNOSTIC_SCRIPT.as_bytes(),
    )?;
    let progress = Path::new(env!("CARGO_MANIFEST_DIR")).join(RETURN_GOLDEN);
    let observed = resume_ternary_from_progress(
        &repository_python(),
        &inspector,
        &progress,
    );
    remove_file(&inspector)
        .map_err(|error| format!("remove ternary inspector: {error}"))?;
    if observed != Err(TernaryProgressCheckpointError::InspectorRejected) {
        return Err(String::from(
            "ternary progress diagnostics were not rejected",
        ));
    }
    Ok(())
}

#[test]
fn progress_adapter_revalidates_ternary_checkpoint_bytes() -> Result<(), String>
{
    let inspector = temporary_ternary_file(
        "inspector-invalid",
        "py",
        TERNARY_INSPECTOR_INVALID_SCRIPT.as_bytes(),
    )?;
    let progress = Path::new(env!("CARGO_MANIFEST_DIR")).join(RETURN_GOLDEN);
    let observed = resume_ternary_from_progress(
        &repository_python(),
        &inspector,
        &progress,
    );
    remove_file(&inspector)
        .map_err(|error| format!("remove ternary inspector: {error}"))?;
    let expected = Err(TernaryProgressCheckpointError::Stage(
        TernaryStageError::Checkpoint(TernaryProgramCodecError::Truncated),
    ));
    if observed != expected {
        return Err(String::from(
            "malformed extracted ternary bytes bypassed stage admission",
        ));
    }
    Ok(())
}

#[test]
fn progress_adapter_reports_ternary_inspector_launch_failure() {
    let missing =
        temp_dir().join(format!("malbolge-missing-ternary-inspector-{}", id()));
    let progress = Path::new(env!("CARGO_MANIFEST_DIR")).join(RETURN_GOLDEN);
    assert_eq!(
        resume_ternary_from_progress(&missing, &missing, &progress),
        Err(TernaryProgressCheckpointError::InspectorLaunch),
    );
}

#[test]
fn i32_constant_return_lowers_to_exact_ternary_bits() -> Result<(), String> {
    let module = admitted_golden(RETURN_GOLDEN)?;
    let input = project_typed_ir(&module)?;
    let first = lower_typed_ir(&input)
        .map_err(|error| format!("lower typed IR projection: {error:?}"))?;
    let second = lower_typed_ir(&input)
        .map_err(|error| format!("repeat typed IR lowering: {error:?}"))?;
    if first != second {
        return Err(String::from("ternary lowering is not deterministic"));
    }
    assert_constant_return_program(&module, &first)
}

fn lowered_byte_constant_fixture(
    byte: u8,
) -> Result<LoweredByteFixture, String> {
    let module = byte_io_module_with_constant(Some(byte));
    validate_module(&module)
        .map_err(|error| format!("validate byte-constant module: {error:?}"))?;
    let typed_bytes = canonical_bytes(&module)
        .map_err(|error| format!("encode byte-constant module: {error:?}"))?;
    let restored = canonical_module(&typed_bytes)
        .map_err(|error| format!("restore byte-constant module: {error:?}"))?;
    if restored != module {
        return Err(String::from("byte-constant typed IR round trip drifted"));
    }
    let input = project_typed_ir(&restored)?;
    let program = lower_typed_ir(&input)
        .map_err(|error| format!("lower byte-constant module: {error:?}"))?;
    assert_program_provenance(&restored, &program)?;
    Ok((program, input))
}

#[test]
fn every_u8_pattern_uses_exactly_six_trits() -> Result<(), String> {
    if 3u32.pow(5) >= 256 || 3u32.pow(6) < 256 {
        return Err(String::from("byte ternary width is not minimal"));
    }
    for bits in u8::MIN..=u8::MAX {
        let scalar = ternary_lowering::TernaryU8Scalar::from_bits(bits);
        if scalar.bits() != bits
            || scalar.trits().len() != ternary_lowering::U8_TERNARY_TRITS
            || scalar.trits().iter().any(|trit| *trit > 2)
        {
            return Err(format!("six-trit byte scalar drifted at {bits}"));
        }
    }
    Ok(())
}

fn lowered_byte_return_fixture(
    literal: Option<u8>,
) -> Result<LoweredByteFixture, String> {
    let module = byte_return_module(literal);
    validate_module(&module)
        .map_err(|error| format!("validate byte-return module: {error:?}"))?;
    let typed_bytes = canonical_bytes(&module)
        .map_err(|error| format!("encode byte-return typed IR: {error:?}"))?;
    let restored = canonical_module(&typed_bytes)
        .map_err(|error| format!("restore byte-return typed IR: {error:?}"))?;
    if restored != module {
        return Err(String::from("byte-return typed-state round trip drift"));
    }
    let input = project_typed_ir(&restored)?;
    let program = lower_typed_ir(&input)
        .map_err(|error| format!("lower byte-return function: {error:?}"))?;
    assert_program_provenance(&restored, &program)?;
    Ok((program, input))
}

fn lowered_unsigned_return_fixture(
    bits: u32,
) -> Result<LoweredByteFixture, String> {
    let module = unsigned_return_module(bits);
    validate_module(&module)
        .map_err(|error| format!("admit unsigned typed IR: {error:?}"))?;
    let bytes = canonical_bytes(&module)
        .map_err(|error| format!("encode unsigned typed IR: {error:?}"))?;
    let restored = canonical_module(&bytes)
        .map_err(|error| format!("decode unsigned typed IR: {error:?}"))?;
    if restored != module {
        return Err(String::from("unsigned typed-IR round trip drifted"));
    }
    let input = project_typed_ir(&restored)?;
    let target = lower_typed_ir(&input)
        .map_err(|error| format!("lower unsigned return: {error:?}"))?;
    assert_program_provenance(&restored, &target)?;
    Ok((target, input))
}

#[test]
fn unsigned_i32_pattern_preserves_unsigned_ssa_and_return_type()
-> Result<(), String> {
    for bits in [0u32, 1, 0x7fff_ffff, 0x8000_0000, u32::MAX] {
        let (target, input) = lowered_unsigned_return_fixture(bits)?;
        if input.functions.first().map(|function| function.return_kind)
            != Some(InputScalarType::U32)
        {
            return Err(String::from("unsigned result signature lost"));
        }
        let function = target
            .functions
            .first()
            .ok_or_else(|| String::from("unsigned target function missing"))?;
        let expected = [
            TernaryOperation::MaterializeU32 {
                result: 0,
                scalar: ternary_lowering::TernaryI32Scalar::from_bits(bits),
                span: output_span(fixture_span(0, 1)),
            },
            TernaryOperation::ReturnU32 {
                span: output_span(fixture_span(1, 2)),
                value: 0,
            },
        ];
        if function.operations.as_slice() != expected {
            return Err(format!("unsigned bits {bits:#x} lost precision/type"));
        }
        let canonical = canonical_ternary_bytes(&target)
            .map_err(|error| format!("encode unsigned target: {error:?}"))?;
        if canonical_ternary_program(&canonical) != Ok(target) {
            return Err(String::from(
                "unsigned target canonical restore drifted",
            ));
        }
    }
    Ok(())
}

fn lowered_arithmetic_fixture(
    signed: bool,
    operation: BinaryOp,
) -> Result<LoweredByteFixture, String> {
    let module = if signed {
        low_byte_module_with_binary(operation)
    } else {
        unsigned_bitwise_module(u32::MAX, 0x8000_0000, operation)
    };
    validate_module(&module)
        .map_err(|error| format!("admit typed arithmetic: {error:?}"))?;
    let encoded = canonical_bytes(&module)
        .map_err(|error| format!("encode typed arithmetic: {error:?}"))?;
    let restored = canonical_module(&encoded)
        .map_err(|error| format!("restore typed arithmetic: {error:?}"))?;
    if restored != module {
        return Err(String::from("typed arithmetic canonical bytes drifted"));
    }
    let input = project_typed_ir(&restored)?;
    let target = lower_typed_ir(&input)
        .map_err(|error| format!("lower typed arithmetic: {error:?}"))?;
    assert_program_provenance(&restored, &target)?;
    Ok((target, input))
}

fn divrem_target_operation(
    signed: bool,
    operation: BinaryOp,
) -> ArithmeticExpected {
    let (left, result, right) = (0, 2, 1);
    let span = output_span(fixture_span(2, 3));
    Ok(match (signed, operation) {
        (true, BinaryOp::DivideSigned) => (
            TernaryOperation::DivideI32 {
                left,
                result,
                right,
                span,
            },
            29,
        ),
        (false, BinaryOp::DivideUnsigned) => (
            TernaryOperation::DivideU32 {
                left,
                result,
                right,
                span,
            },
            30,
        ),
        (true, BinaryOp::RemainderSigned) => (
            TernaryOperation::RemainderI32 {
                left,
                result,
                right,
                span,
            },
            31,
        ),
        (false, BinaryOp::RemainderUnsigned) => (
            TernaryOperation::RemainderU32 {
                left,
                result,
                right,
                span,
            },
            32,
        ),
        _ => {
            return Err(String::from(
                "unsupported division/remainder operator",
            ));
        },
    })
}

const fn multiply_target_operation(signed: bool) -> (TernaryOperation, u8) {
    let (left, result, right) = (0, 2, 1);
    let span = output_span(fixture_span(2, 3));
    if signed {
        (
            TernaryOperation::MultiplyI32 {
                left,
                result,
                right,
                span,
            },
            23,
        )
    } else {
        (
            TernaryOperation::MultiplyU32 {
                left,
                result,
                right,
                span,
            },
            24,
        )
    }
}

fn arithmetic_target_operation(
    signed: bool,
    operation: BinaryOp,
) -> ArithmeticExpected {
    if matches!(
        operation,
        BinaryOp::DivideSigned
            | BinaryOp::DivideUnsigned
            | BinaryOp::RemainderSigned
            | BinaryOp::RemainderUnsigned
    ) {
        return divrem_target_operation(signed, operation);
    }
    if operation == BinaryOp::Multiply {
        return Ok(multiply_target_operation(signed));
    }
    let (left, result, right) = (0, 2, 1);
    let span = output_span(fixture_span(2, 3));
    Ok(match (signed, operation) {
        (true, BinaryOp::Add) => (
            TernaryOperation::AddI32 {
                left,
                result,
                right,
                span,
            },
            19,
        ),
        (false, BinaryOp::Add) => (
            TernaryOperation::AddU32 {
                left,
                result,
                right,
                span,
            },
            20,
        ),
        (true, BinaryOp::Subtract) => (
            TernaryOperation::SubtractI32 {
                left,
                result,
                right,
                span,
            },
            21,
        ),
        (false, BinaryOp::Subtract) => (
            TernaryOperation::SubtractU32 {
                left,
                result,
                right,
                span,
            },
            22,
        ),
        (_, _) => return Err(String::from("invalid arithmetic operator")),
    })
}

fn check_symbolic_divrem_boundaries(
    signed: bool,
    operation: BinaryOp,
    right_bits: u32,
) -> Result<(), String> {
    let left_bits = 0x8000_0000u32;
    let module = if signed {
        low_byte_module_with_bits(operation, (left_bits, right_bits))
    } else {
        unsigned_bitwise_module(left_bits, right_bits, operation)
    };
    validate_module(&module)
        .map_err(|error| format!("admit symbolic divrem IR: {error:?}"))?;
    let typed_bytes = canonical_bytes(&module).map_err(|error| {
        format!("encode symbolic divrem typed IR: {error:?}")
    })?;
    let restored = canonical_module(&typed_bytes)
        .map_err(|error| format!("restore divrem typed IR: {error:?}"))?;
    if restored != module {
        return Err(String::from("division boundary typed-IR drifted"));
    }
    let input = project_typed_ir(&restored)?;
    let target = lower_typed_ir(&input).map_err(|error| {
        format!("lower symbolic divrem boundary: {error:?}")
    })?;
    assert_program_provenance(&restored, &target)?;
    let function = target
        .functions
        .first()
        .ok_or_else(|| String::from("divrem boundary function missing"))?;
    let (expected_operation, tag) =
        arithmetic_target_operation(signed, operation)?;
    if function.operations.get(2) != Some(&expected_operation) {
        return Err(String::from("divrem boundary operation was evaluated"));
    }
    let expected_source =
        ternary_lowering::TernaryI32Scalar::from_bits(right_bits);
    let original_right = if signed {
        TernaryOperation::MaterializeI32 {
            result: 1,
            scalar: expected_source,
            span: output_span(fixture_span(1, 2)),
        }
    } else {
        TernaryOperation::MaterializeU32 {
            result: 1,
            scalar: expected_source,
            span: output_span(fixture_span(1, 2)),
        }
    };
    if function.operations.get(1) != Some(&original_right) {
        return Err(String::from("zero or minus-one divisor was rewritten"));
    }
    let encoded = canonical_ternary_bytes(&target).map_err(|error| {
        format!("encode divrem boundary checkpoint: {error:?}")
    })?;
    if !encoded.windows(5).any(|window| window == [tag, 0, 0, 0, 0])
        || canonical_ternary_program(&encoded) != Ok(target)
    {
        return Err(String::from("divrem boundary checkpoint rejected"));
    }
    Ok(())
}

#[test]
fn division_and_remainder_keep_zero_and_signed_overflow_symbolic()
-> Result<(), String> {
    for (signed, operation) in [
        (true, BinaryOp::DivideSigned),
        (false, BinaryOp::DivideUnsigned),
        (true, BinaryOp::RemainderSigned),
        (false, BinaryOp::RemainderUnsigned),
    ] {
        for right_bits in [0u32, u32::MAX] {
            check_symbolic_divrem_boundaries(signed, operation, right_bits)?;
        }
    }
    Ok(())
}

#[test]
fn typed_arithmetic_preserves_signedness_ssa_and_checkpoint_tags()
-> Result<(), String> {
    for (signed, operation) in arithmetic_cases() {
        let (target, input) = lowered_arithmetic_fixture(signed, operation)?;
        let expected_kind = if signed {
            InputScalarType::I32
        } else {
            InputScalarType::U32
        };
        if input.functions.first().map(|function| function.return_kind)
            != Some(expected_kind)
        {
            return Err(String::from("arithmetic return kind drifted"));
        }
        let (expected, tag) = arithmetic_target_operation(signed, operation)?;
        let function = target
            .functions
            .first()
            .ok_or_else(|| String::from("arithmetic target missing"))?;
        if function.operations.get(2) != Some(&expected) {
            return Err(String::from("typed arithmetic SSA/operand drifted"));
        }
        let encoded = canonical_ternary_bytes(&target)
            .map_err(|error| format!("encode ternary arithmetic: {error:?}"))?;
        let prefix = [tag, 0, 0, 0, 0, 2, 0, 0, 0, 1, 0, 0, 0];
        if !encoded.windows(prefix.len()).any(|wire| wire == prefix)
            || canonical_ternary_program(&encoded) != Ok(target)
        {
            return Err(String::from("arithmetic canonical tag drifted"));
        }
    }
    Ok(())
}

fn mutate_arithmetic_instruction(
    instruction: &mut InputInstruction,
    wrong_type: InputScalarType,
    variation: u8,
) -> Result<(), String> {
    let (InputInstruction::BinaryAdd {
        right, result, type_kind, ..
    }
    | InputInstruction::BinarySubtract {
        right, result, type_kind, ..
    }
    | InputInstruction::BinaryMultiply {
        right, result, type_kind, ..
    }
    | InputInstruction::BinaryDivideSigned {
        right, result, type_kind, ..
    }
    | InputInstruction::BinaryDivideUnsigned {
        right,
        result,
        type_kind,
        ..
    }
    | InputInstruction::BinaryRemainderSigned {
        right,
        result,
        type_kind,
        ..
    }
    | InputInstruction::BinaryRemainderUnsigned {
        right,
        result,
        type_kind,
        ..
    }) = instruction
    else {
        return Err(String::from("arithmetic projection changed"));
    };
    match variation {
        0 => *type_kind = wrong_type,
        1 => *right = 99,
        2 => *result = 0,
        3 => *type_kind = InputScalarType::U8,
        _ => return Err(String::from("unknown arithmetic forgery")),
    }
    Ok(())
}

fn check_arithmetic_projection_forgery(
    signed: bool,
    operation: BinaryOp,
    variation: u8,
) -> Result<(), String> {
    let (_target, mut forged) = lowered_arithmetic_fixture(signed, operation)?;
    let wrong_type = if signed {
        InputScalarType::U32
    } else {
        InputScalarType::I32
    };
    let instruction = forged
        .functions
        .first_mut()
        .and_then(|function| function.blocks.first_mut())
        .and_then(|block| block.instructions.get_mut(2))
        .ok_or_else(|| String::from("arithmetic instruction missing"))?;
    mutate_arithmetic_instruction(instruction, wrong_type, variation)?;
    let expected = if variation == 2 {
        TernaryLoweringError::InvalidProjection
    } else {
        TernaryLoweringError::UnsupportedInstruction
    };
    if lower_typed_ir(&forged) != Err(expected) {
        return Err(format!("arithmetic forgery {variation} admitted"));
    }
    Ok(())
}

#[test]
fn typed_arithmetic_projection_rejects_operand_and_result_forgery()
-> Result<(), String> {
    for (signed, operation) in arithmetic_cases() {
        for variation in 0u8..4u8 {
            check_arithmetic_projection_forgery(signed, operation, variation)?;
        }
    }
    Ok(())
}

fn assert_forged_arithmetic_wire_closed(
    signed: bool,
    operation: BinaryOp,
) -> Result<(), String> {
    let (target, _projection) = lowered_arithmetic_fixture(signed, operation)?;
    let encoded = canonical_ternary_bytes(&target).map_err(|error| {
        format!("encode arithmetic tamper fixture: {error:?}")
    })?;
    let (_expected_operation, tag) =
        arithmetic_target_operation(signed, operation)?;
    let flipped_tag = if signed {
        tag.saturating_add(1)
    } else {
        tag.saturating_sub(1)
    };
    let prefix = [tag, 0, 0, 0, 0, 2, 0, 0, 0, 1, 0, 0, 0];
    let offset = encoded
        .windows(prefix.len())
        .position(|wire| wire == prefix)
        .ok_or_else(|| String::from("arithmetic tag missing"))?;
    let wrong_ssa = TernaryProgramCodecError::Validation(
        TernaryProgramValidationError::SsaValue,
    );
    for (forged_tag, expected) in [
        (flipped_tag, wrong_ssa),
        (84u8, TernaryProgramCodecError::UnknownTag),
    ] {
        let mut forged = encoded.clone();
        *forged
            .get_mut(offset)
            .ok_or_else(|| String::from("arithmetic tag offset missing"))? =
            forged_tag;
        if canonical_ternary_program(&forged) != Err(expected) {
            return Err(format!("forged arithmetic tag {forged_tag} admitted"));
        }
    }
    let mut undefined = encoded;
    let right_offset = offset
        .checked_add(9)
        .ok_or_else(|| String::from("right arithmetic ID offset overflow"))?;
    let right_end = right_offset
        .checked_add(4)
        .ok_or_else(|| String::from("right arithmetic ID extent overflow"))?;
    undefined
        .get_mut(right_offset..right_end)
        .ok_or_else(|| String::from("right arithmetic ID missing"))?
        .copy_from_slice(&99u32.to_le_bytes());
    if canonical_ternary_program(&undefined) != Err(wrong_ssa) {
        return Err(String::from("undefined arithmetic operand admitted"));
    }
    Ok(())
}

#[test]
fn arithmetic_wire_rejects_signedness_swaps_and_future_tags()
-> Result<(), String> {
    for (signed, operation) in arithmetic_cases() {
        assert_forged_arithmetic_wire_closed(signed, operation)?;
    }
    Ok(())
}

fn lowered_shift_fixture(
    signed: bool,
    operation: BinaryOp,
) -> Result<LoweredByteFixture, String> {
    let module = if signed {
        low_byte_module_with_binary(operation)
    } else {
        unsigned_bitwise_module(1, 31, operation)
    };
    validate_module(&module)
        .map_err(|error| format!("admit typed shift IR: {error:?}"))?;
    let bytes = canonical_bytes(&module)
        .map_err(|error| format!("encode typed shift IR: {error:?}"))?;
    let restored = canonical_module(&bytes)
        .map_err(|error| format!("restore typed shift IR: {error:?}"))?;
    if restored != module {
        return Err(String::from("typed shift IR drifted"));
    }
    let input = project_typed_ir(&restored)?;
    let target = lower_typed_ir(&input)
        .map_err(|error| format!("lower typed shift: {error:?}"))?;
    assert_program_provenance(&restored, &target)?;
    Ok((target, input))
}

const fn shift_cases() -> [(bool, BinaryOp); 4] {
    [
        (true, BinaryOp::ShiftLeft),
        (false, BinaryOp::ShiftLeft),
        (true, BinaryOp::ShiftRightArithmetic),
        (false, BinaryOp::ShiftRightLogical),
    ]
}

fn shift_target_operation(
    signed: bool,
    operation: BinaryOp,
) -> ArithmeticExpected {
    let (left, result, right) = (0, 2, 1);
    let span = output_span(fixture_span(2, 3));
    Ok(match (signed, operation) {
        (true, BinaryOp::ShiftLeft) => (
            TernaryOperation::ShiftLeftI32 {
                left,
                result,
                right,
                span,
            },
            25,
        ),
        (false, BinaryOp::ShiftLeft) => (
            TernaryOperation::ShiftLeftU32 {
                left,
                result,
                right,
                span,
            },
            26,
        ),
        (true, BinaryOp::ShiftRightArithmetic) => (
            TernaryOperation::ShiftRightArithmeticI32 {
                left,
                result,
                right,
                span,
            },
            27,
        ),
        (false, BinaryOp::ShiftRightLogical) => (
            TernaryOperation::ShiftRightLogicalU32 {
                left,
                result,
                right,
                span,
            },
            28,
        ),
        _ => return Err(String::from("invalid signed shift combination")),
    })
}

fn check_shift_fixture(
    signed: bool,
    operation: BinaryOp,
) -> Result<(), String> {
    let (target, input) = lowered_shift_fixture(signed, operation)?;
    let expected_kind = if signed {
        InputScalarType::I32
    } else {
        InputScalarType::U32
    };
    if input.functions.first().map(|function| function.return_kind)
        != Some(expected_kind)
    {
        return Err(String::from("shift return signedness changed"));
    }
    let (expected, tag) = shift_target_operation(signed, operation)?;
    if target
        .functions
        .first()
        .and_then(|function| function.operations.get(2))
        != Some(&expected)
    {
        return Err(String::from("shift operand/SSA provenance changed"));
    }
    let encoded = canonical_ternary_bytes(&target)
        .map_err(|error| format!("encode shift target: {error:?}"))?;
    let prefix = [tag, 0, 0, 0, 0, 2, 0, 0, 0, 1, 0, 0, 0];
    if !encoded.windows(prefix.len()).any(|window| window == prefix)
        || canonical_ternary_program(&encoded) != Ok(target)
    {
        return Err(String::from("shift canonical checkpoint drifted"));
    }
    Ok(())
}

#[test]
fn typed_shift_preserves_ssa_signedness_and_canonical_tags()
-> Result<(), String> {
    for (signed, operation) in shift_cases() {
        check_shift_fixture(signed, operation)?;
    }
    Ok(())
}

fn check_shift_forgery(
    signed: bool,
    operation: BinaryOp,
) -> Result<(), String> {
    let (target, _input) = lowered_shift_fixture(signed, operation)?;
    let mut encoded = canonical_ternary_bytes(&target)
        .map_err(|error| format!("encode shift forgery: {error:?}"))?;
    let (_expected, tag) = shift_target_operation(signed, operation)?;
    let swapped = if signed {
        tag.saturating_add(1)
    } else {
        tag.saturating_sub(1)
    };
    let prefix = [tag, 0, 0, 0, 0, 2, 0, 0, 0, 1, 0, 0, 0];
    let offset = encoded
        .windows(prefix.len())
        .position(|window| window == prefix)
        .ok_or_else(|| String::from("shift tag missing"))?;
    let wrong_ssa = TernaryProgramCodecError::Validation(
        TernaryProgramValidationError::SsaValue,
    );
    for (tag_value, failure) in [
        (swapped, wrong_ssa),
        (84u8, TernaryProgramCodecError::UnknownTag),
    ] {
        let mut changed = encoded.clone();
        *changed
            .get_mut(offset)
            .ok_or_else(|| String::from("shift tag byte missing"))? = tag_value;
        if canonical_ternary_program(&changed) != Err(failure) {
            return Err(format!("forged shift tag {tag_value} admitted"));
        }
    }
    let right_start = offset
        .checked_add(9)
        .ok_or_else(|| String::from("shift right operand offset overflow"))?;
    let right_end = right_start
        .checked_add(4)
        .ok_or_else(|| String::from("shift right operand extent overflow"))?;
    encoded
        .get_mut(right_start..right_end)
        .ok_or_else(|| String::from("shift right operand missing"))?
        .copy_from_slice(&99u32.to_le_bytes());
    if canonical_ternary_program(&encoded) != Err(wrong_ssa) {
        return Err(String::from("undefined shift count SSA admitted"));
    }
    Ok(())
}

#[test]
fn shift_decoder_rejects_wrong_direction_and_undefined_operands()
-> Result<(), String> {
    for (signed, operation) in shift_cases() {
        check_shift_forgery(signed, operation)?;
    }
    Ok(())
}

fn lowered_unsigned_bitwise_fixture(
    left: u32,
    right: u32,
    operation: BinaryOp,
) -> Result<LoweredByteFixture, String> {
    let module = unsigned_bitwise_module(left, right, operation);
    validate_module(&module).map_err(|error| {
        format!("unsigned bitwise typed IR admission: {error:?}")
    })?;
    let encoded = canonical_bytes(&module).map_err(|error| {
        format!("encode unsigned bitwise typed IR: {error:?}")
    })?;
    let restored = canonical_module(&encoded).map_err(|error| {
        format!("restore unsigned bitwise typed IR: {error:?}")
    })?;
    if restored != module {
        return Err(String::from("unsigned bitwise typed IR round trip drift"));
    }
    let projected = project_typed_ir(&restored)?;
    let target = lower_typed_ir(&projected)
        .map_err(|error| format!("lower unsigned bitwise: {error:?}"))?;
    assert_program_provenance(&restored, &target)?;
    Ok((target, projected))
}

fn expected_unsigned_bitwise_operation(
    operation: BinaryOp,
) -> TernaryOperation {
    let span = output_span(fixture_span(2, 3));
    if operation == BinaryOp::And {
        TernaryOperation::AndU32 {
            left: 0,
            result: 2,
            right: 1,
            span,
        }
    } else if operation == BinaryOp::Or {
        TernaryOperation::OrU32 {
            left: 0,
            result: 2,
            right: 1,
            span,
        }
    } else {
        TernaryOperation::XorU32 {
            left: 0,
            result: 2,
            right: 1,
            span,
        }
    }
}

#[test]
fn unsigned_bitwise_operations_preserve_typed_ssa_and_canonical_tags()
-> Result<(), String> {
    for (operation, tag) in [
        (BinaryOp::And, 12u8),
        (BinaryOp::Or, 13u8),
        (BinaryOp::Xor, 14u8),
    ] {
        let (target, projected) =
            lowered_unsigned_bitwise_fixture(u32::MAX, 0x8000_0000, operation)?;
        if projected
            .functions
            .first()
            .map(|function| function.return_kind)
            != Some(InputScalarType::U32)
        {
            return Err(String::from("unsigned bitwise return type was lost"));
        }
        let function = target
            .functions
            .first()
            .ok_or_else(|| String::from("missing unsigned bitwise function"))?;
        let actual = function
            .operations
            .get(2)
            .ok_or_else(|| String::from("unsigned bitwise result missing"))?;
        let expected = expected_unsigned_bitwise_operation(operation);
        if *actual != expected {
            return Err(String::from("unsigned bitwise SSA or span changed"));
        }
        let encoded = canonical_ternary_bytes(&target).map_err(|error| {
            format!("encode unsigned bitwise target: {error:?}")
        })?;
        let pattern = [tag, 0, 0, 0, 0, 2, 0, 0, 0, 1, 0, 0, 0];
        if !encoded
            .windows(pattern.len())
            .any(|window| window == pattern)
            || canonical_ternary_program(&encoded) != Ok(target)
        {
            return Err(String::from("unsigned bitwise canonical tag drifted"));
        }
    }
    Ok(())
}

#[test]
fn unsigned_bitwise_projection_rejects_type_and_ssa_forgery()
-> Result<(), String> {
    for operation in [BinaryOp::And, BinaryOp::Or, BinaryOp::Xor] {
        let (_target, projected) =
            lowered_unsigned_bitwise_fixture(u32::MAX, 0x8000_0000, operation)?;
        for variation in 0u8..3u8 {
            let mut forged = projected.clone();
            let instruction = forged
                .functions
                .first_mut()
                .and_then(|function| function.blocks.first_mut())
                .and_then(|block| block.instructions.get_mut(2))
                .ok_or_else(|| {
                    String::from("missing projected unsigned bitwise")
                })?;
            let (InputInstruction::BinaryAnd {
                type_kind, right, result, ..
            }
            | InputInstruction::BinaryOr {
                type_kind, right, result, ..
            }
            | InputInstruction::BinaryXor {
                type_kind, right, result, ..
            }) = instruction
            else {
                return Err(String::from(
                    "unexpected unsigned bitwise projection",
                ));
            };
            match variation {
                0 => *type_kind = InputScalarType::I32,
                1 => *right = 99,
                2 => *result = 0,
                _ => {
                    return Err(String::from(
                        "unknown invalid unsigned bitwise case",
                    ));
                },
            }
            let expected = if variation == 2 {
                TernaryLoweringError::InvalidProjection
            } else {
                TernaryLoweringError::UnsupportedInstruction
            };
            if lower_typed_ir(&forged) != Err(expected) {
                return Err(String::from(
                    "forged unsigned bitwise projection admitted",
                ));
            }
        }
    }
    Ok(())
}

fn expected_unsigned_alias_operation(
    operation: BinaryOp,
    span: ternary_lowering::TernarySourceSpan,
) -> TernaryOperation {
    if operation == BinaryOp::And {
        TernaryOperation::AndU32 {
            left: 0,
            result: 1,
            right: 0,
            span,
        }
    } else if operation == BinaryOp::Or {
        TernaryOperation::OrU32 {
            left: 0,
            result: 1,
            right: 0,
            span,
        }
    } else {
        TernaryOperation::XorU32 {
            left: 0,
            result: 1,
            right: 0,
            span,
        }
    }
}

fn lowered_integer_bitcast_fixture(
    source_signed: bool,
    bits: u32,
) -> Result<LoweredByteFixture, String> {
    let module = integer_bitcast_module(source_signed, bits);
    validate_module(&module)
        .map_err(|error| format!("admit integer bitcast: {error:?}"))?;
    let encoded = canonical_bytes(&module)
        .map_err(|error| format!("encode typed bitcast: {error:?}"))?;
    let restored = canonical_module(&encoded)
        .map_err(|error| format!("restore typed bitcast: {error:?}"))?;
    if restored != module {
        return Err(String::from("typed integer bitcast bytes drifted"));
    }
    let input = project_typed_ir(&restored)?;
    let target = lower_typed_ir(&input)
        .map_err(|error| format!("lower integer bitcast: {error:?}"))?;
    assert_program_provenance(&restored, &target)?;
    Ok((target, input))
}

fn check_bitcast_target(
    source_signed: bool,
    bits: u32,
    target: &ternary_lowering::TernaryProgram,
) -> Result<(), String> {
    let function = target
        .functions
        .first()
        .ok_or_else(|| String::from("missing bitcast target function"))?;
    let expected_scalar = ternary_lowering::TernaryI32Scalar::from_bits(bits);
    let source = if source_signed {
        TernaryOperation::MaterializeI32 {
            result: 0,
            scalar: expected_scalar,
            span: output_span(fixture_span(0, 1)),
        }
    } else {
        TernaryOperation::MaterializeU32 {
            result: 0,
            scalar: expected_scalar,
            span: output_span(fixture_span(0, 1)),
        }
    };
    let expected_cast = if source_signed {
        TernaryOperation::BitcastI32ToU32 {
            result: 1,
            span: output_span(fixture_span(1, 2)),
            value: 0,
        }
    } else {
        TernaryOperation::BitcastU32ToI32 {
            result: 1,
            span: output_span(fixture_span(1, 2)),
            value: 0,
        }
    };
    let expected_return = if source_signed {
        TernaryOperation::ReturnU32 {
            span: output_span(fixture_span(2, 3)),
            value: 1,
        }
    } else {
        TernaryOperation::Return {
            span: output_span(fixture_span(2, 3)),
            value: 1,
        }
    };
    if function.operations.as_slice()
        != [source, expected_cast, expected_return]
    {
        return Err(String::from(
            "integer bitcast SSA/bits/provenance drifted",
        ));
    }
    Ok(())
}

#[test]
fn bitcast_signedness_preserves_all_32_bits_and_canonical_wire()
-> Result<(), String> {
    for source_signed in [true, false] {
        for bits in [0u32, 1, 0x7fff_ffff, 0x8000_0000, u32::MAX] {
            let (target, input) =
                lowered_integer_bitcast_fixture(source_signed, bits)?;
            let destination = if source_signed {
                InputScalarType::U32
            } else {
                InputScalarType::I32
            };
            if input.functions.first().map(|function| function.return_kind)
                != Some(destination)
            {
                return Err(String::from("bitcast return signedness drifted"));
            }
            check_bitcast_target(source_signed, bits, &target)?;
            let encoded =
                canonical_ternary_bytes(&target).map_err(|error| {
                    format!("encode ternary bitcast: {error:?}")
                })?;
            let tag = if source_signed {
                17u8
            } else {
                18u8
            };
            if !encoded.windows(5).any(|wire| wire == [tag, 1, 0, 0, 0])
                || canonical_ternary_program(&encoded) != Ok(target)
            {
                return Err(String::from("integer bitcast checkpoint drifted"));
            }
        }
    }
    Ok(())
}

fn double_integer_bitcast_projection(
    initial_signed: bool,
    bits: u32,
) -> Result<TypedIrInput, String> {
    let (_single, mut projected) =
        lowered_integer_bitcast_fixture(initial_signed, bits)?;
    let function = projected
        .functions
        .first_mut()
        .ok_or_else(|| String::from("bitcast-chain function missing"))?;
    function.return_kind = if initial_signed {
        InputScalarType::I32
    } else {
        InputScalarType::U32
    };
    let block = function
        .blocks
        .first_mut()
        .ok_or_else(|| String::from("bitcast-chain block missing"))?;
    block.instructions.push(InputInstruction::IntegerBitcast {
        result: 2,
        span: input_span(fixture_span(1, 2)),
        type_kind: function.return_kind,
        value: 1,
    });
    block.terminator = InputTerminator::Return {
        span: input_span(fixture_span(2, 3)),
        value: Some(2),
    };
    Ok(projected)
}

#[test]
fn two_integer_bitcasts_restore_original_signedness_and_bits()
-> Result<(), String> {
    for signed in [true, false] {
        for bits in [0u32, 0x7fff_ffff, 0x8000_0000, u32::MAX] {
            let projected = double_integer_bitcast_projection(signed, bits)?;
            let target = lower_typed_ir(&projected)
                .map_err(|error| format!("lower double bitcast: {error:?}"))?;
            let function = target.functions.first().ok_or_else(|| {
                String::from("double bitcast function missing")
            })?;
            let second = if signed {
                TernaryOperation::BitcastU32ToI32 {
                    result: 2,
                    span: output_span(fixture_span(1, 2)),
                    value: 1,
                }
            } else {
                TernaryOperation::BitcastI32ToU32 {
                    result: 2,
                    span: output_span(fixture_span(1, 2)),
                    value: 1,
                }
            };
            let final_return = if signed {
                TernaryOperation::Return {
                    span: output_span(fixture_span(2, 3)),
                    value: 2,
                }
            } else {
                TernaryOperation::ReturnU32 {
                    span: output_span(fixture_span(2, 3)),
                    value: 2,
                }
            };
            if function.operations.get(2) != Some(&second)
                || function.operations.last() != Some(&final_return)
            {
                return Err(String::from("double bitcast signedness was lost"));
            }
            let bytes = canonical_ternary_bytes(&target)
                .map_err(|error| format!("encode double bitcast: {error:?}"))?;
            if canonical_ternary_program(&bytes) != Ok(target) {
                return Err(String::from("double bitcast recovery drifted"));
            }
        }
    }
    Ok(())
}

#[test]
fn chained_integer_bitcast_admits_same_kind_reuse_of_original_source()
-> Result<(), String> {
    for initial_signed in [true, false] {
        let mut projected =
            double_integer_bitcast_projection(initial_signed, u32::MAX)?;
        let last = projected
            .functions
            .first_mut()
            .and_then(|function| function.blocks.first_mut())
            .and_then(|block| block.instructions.get_mut(2))
            .ok_or_else(|| String::from("second bitcast missing"))?;
        let InputInstruction::IntegerBitcast { value, .. } = last else {
            return Err(String::from("second bitcast projection missing"));
        };
        *value = 0;
        let target = lower_typed_ir(&projected).map_err(|error| {
            format!("lower reused original cast source: {error:?}")
        })?;
        let expected = if initial_signed {
            TernaryOperation::BitcastI32ToI32 {
                result: 2,
                span: output_span(fixture_span(1, 2)),
                value: 0,
            }
        } else {
            TernaryOperation::BitcastU32ToU32 {
                result: 2,
                span: output_span(fixture_span(1, 2)),
                value: 0,
            }
        };
        if target
            .functions
            .first()
            .and_then(|function| function.operations.get(2))
            != Some(&expected)
        {
            return Err(String::from(
                "same-kind reinterpreted SSA lost provenance",
            ));
        }
        let bytes = canonical_ternary_bytes(&target).map_err(|error| {
            format!("encode reused bitcast source: {error:?}")
        })?;
        if canonical_ternary_program(&bytes) != Ok(target) {
            return Err(String::from(
                "same-kind reused source checkpoint drifted",
            ));
        }
    }
    Ok(())
}

#[test]
fn integer_bitcast_projection_rejects_invalid_type_and_ssa()
-> Result<(), String> {
    for source_signed in [true, false] {
        let (_target, input) =
            lowered_integer_bitcast_fixture(source_signed, 0x8000_0080)?;
        for variation in 1u8..5u8 {
            let mut forged = input.clone();
            let instruction = forged
                .functions
                .first_mut()
                .and_then(|function| function.blocks.first_mut())
                .and_then(|block| block.instructions.get_mut(1))
                .ok_or_else(|| String::from("bitcast projection missing"))?;
            let InputInstruction::IntegerBitcast {
                result,
                type_kind,
                value,
                ..
            } = instruction
            else {
                return Err(String::from("bitcast projection changed"));
            };
            match variation {
                1 => *value = 99,
                2 => *result = 0,
                3 => *value = 1,
                4 => *type_kind = InputScalarType::U8,
                _ => {
                    return Err(String::from(
                        "unknown integer-bitcast forgery",
                    ));
                },
            }
            let expected = if variation == 2 {
                TernaryLoweringError::InvalidProjection
            } else {
                TernaryLoweringError::UnsupportedInstruction
            };
            if lower_typed_ir(&forged) != Err(expected) {
                return Err(format!(
                    "forged bitcast projection {variation} admitted"
                ));
            }
        }
    }
    Ok(())
}

#[test]
fn integer_bitcast_decoder_rejects_retyped_and_unknown_opcodes()
-> Result<(), String> {
    for source_signed in [true, false] {
        let (target, _projection) =
            lowered_integer_bitcast_fixture(source_signed, u32::MAX)?;
        let bytes = canonical_ternary_bytes(&target)
            .map_err(|error| format!("encode bitcast checkpoint: {error:?}"))?;
        let tag = if source_signed {
            17u8
        } else {
            18u8
        };
        let flipped = if source_signed {
            18u8
        } else {
            17u8
        };
        let pattern = [tag, 1, 0, 0, 0];
        let offset = bytes
            .windows(pattern.len())
            .position(|window| window == pattern)
            .ok_or_else(|| String::from("bitcast opcode missing"))?;
        let wrong_ssa = TernaryProgramCodecError::Validation(
            TernaryProgramValidationError::SsaValue,
        );
        for (forged_tag, expected) in [
            (flipped, wrong_ssa),
            (16u8, wrong_ssa),
            (84u8, TernaryProgramCodecError::UnknownTag),
        ] {
            let mut forged = bytes.clone();
            *forged
                .get_mut(offset)
                .ok_or_else(|| String::from("bitcast tag missing"))? =
                forged_tag;
            if canonical_ternary_program(&forged) != Err(expected) {
                return Err(format!(
                    "forged bitcast tag {forged_tag} admitted"
                ));
            }
        }
        let source_offset = offset
            .checked_add(29)
            .ok_or_else(|| String::from("bitcast source offset overflow"))?;
        let mut missing = bytes;
        missing
            .get_mut(source_offset..source_offset + 4)
            .ok_or_else(|| String::from("bitcast source ID missing"))?
            .copy_from_slice(&99u32.to_le_bytes());
        if canonical_ternary_program(&missing)
            != Err(TernaryProgramCodecError::Validation(
                TernaryProgramValidationError::SsaValue,
            ))
        {
            return Err(String::from("undefined bitcast source admitted"));
        }
    }
    Ok(())
}

fn lowered_same_kind_bitcast_fixture(
    signed: bool,
    bits: u32,
) -> Result<LoweredByteFixture, String> {
    let module = integer_bitcast_module_with_kind(signed, bits, true);
    validate_module(&module)
        .map_err(|error| format!("admit identity bitcast: {error:?}"))?;
    let encoded = canonical_bytes(&module).map_err(|error| {
        format!("encode identity bitcast typed IR: {error:?}")
    })?;
    let restored = canonical_module(&encoded)
        .map_err(|error| format!("restore identity bitcast IR: {error:?}"))?;
    if restored != module {
        return Err(String::from("identity bitcast typed bytes changed"));
    }
    let projection = project_typed_ir(&restored)?;
    let target = lower_typed_ir(&projection)
        .map_err(|error| format!("lower identity bitcast: {error:?}"))?;
    assert_program_provenance(&restored, &target)?;
    Ok((target, projection))
}

const fn same_kind_bitcast_operation(signed: bool) -> (TernaryOperation, u8) {
    let span = output_span(fixture_span(1, 2));
    if signed {
        (
            TernaryOperation::BitcastI32ToI32 {
                result: 1,
                span,
                value: 0,
            },
            33,
        )
    } else {
        (
            TernaryOperation::BitcastU32ToU32 {
                result: 1,
                span,
                value: 0,
            },
            34,
        )
    }
}

#[test]
fn identity_integer_bitcast_keeps_distinct_ssa_with_exact_bits()
-> Result<(), String> {
    for signed in [true, false] {
        for bits in [0u32, 1, 0x7fff_ffff, 0x8000_0000, u32::MAX] {
            let (target, projection) =
                lowered_same_kind_bitcast_fixture(signed, bits)?;
            let return_kind = if signed {
                InputScalarType::I32
            } else {
                InputScalarType::U32
            };
            if projection
                .functions
                .first()
                .map(|function| function.return_kind)
                != Some(return_kind)
            {
                return Err(String::from("same-kind return category changed"));
            }
            let (expected, tag) = same_kind_bitcast_operation(signed);
            let function = target.functions.first().ok_or_else(|| {
                String::from("same-kind target function missing")
            })?;
            if function.operations.get(1) != Some(&expected) {
                return Err(String::from(
                    "same-kind bitcast lost new SSA identity",
                ));
            }
            let scalar = ternary_lowering::TernaryI32Scalar::from_bits(bits);
            let original = if signed {
                TernaryOperation::MaterializeI32 {
                    result: 0,
                    scalar,
                    span: output_span(fixture_span(0, 1)),
                }
            } else {
                TernaryOperation::MaterializeU32 {
                    result: 0,
                    scalar,
                    span: output_span(fixture_span(0, 1)),
                }
            };
            if function.operations.first() != Some(&original) {
                return Err(String::from(
                    "same-kind cast changed original bits",
                ));
            }
            let bytes = canonical_ternary_bytes(&target).map_err(|error| {
                format!("encode same-kind target: {error:?}")
            })?;
            if !bytes.windows(5).any(|wire| wire == [tag, 1, 0, 0, 0])
                || canonical_ternary_program(&bytes) != Ok(target)
            {
                return Err(String::from("same-kind checkpoint drifted"));
            }
        }
    }
    Ok(())
}

fn check_same_kind_projection_forgery(
    projection: &TypedIrInput,
) -> Result<(), String> {
    for variation in 0u8..3u8 {
        let mut forged = projection.clone();
        let instruction = forged
            .functions
            .first_mut()
            .and_then(|function| function.blocks.first_mut())
            .and_then(|block| block.instructions.get_mut(1))
            .ok_or_else(|| {
                String::from("same-kind cast instruction missing")
            })?;
        let InputInstruction::IntegerBitcast {
            result, type_kind, value, ..
        } = instruction
        else {
            return Err(String::from("same-kind cast projection drifted"));
        };
        match variation {
            0 => *value = 99,
            1 => *result = 0,
            2 => *type_kind = InputScalarType::U8,
            _ => return Err(String::from("unexpected cast forgery")),
        }
        let failure = if variation == 1 {
            TernaryLoweringError::InvalidProjection
        } else {
            TernaryLoweringError::UnsupportedInstruction
        };
        if lower_typed_ir(&forged) != Err(failure) {
            return Err(format!("same-kind cast forgery {variation} admitted"));
        }
    }
    Ok(())
}

fn check_same_kind_wire_forgery(
    target: &ternary_lowering::TernaryProgram,
    signed: bool,
) -> Result<(), String> {
    let bytes = canonical_ternary_bytes(target)
        .map_err(|error| format!("encode same-kind forgery: {error:?}"))?;
    let (_operation, tag) = same_kind_bitcast_operation(signed);
    let offset = bytes
        .windows(5)
        .position(|wire| wire == [tag, 1, 0, 0, 0])
        .ok_or_else(|| String::from("same-kind cast tag missing"))?;
    let opposite = if signed {
        34u8
    } else {
        33u8
    };
    let wrong_ssa = TernaryProgramCodecError::Validation(
        TernaryProgramValidationError::SsaValue,
    );
    for (replacement, failure) in [
        (opposite, wrong_ssa),
        (84u8, TernaryProgramCodecError::UnknownTag),
    ] {
        let mut forged = bytes.clone();
        *forged
            .get_mut(offset)
            .ok_or_else(|| String::from("same-kind tag byte missing"))? =
            replacement;
        if canonical_ternary_program(&forged) != Err(failure) {
            return Err(format!(
                "same-kind replacement {replacement} admitted"
            ));
        }
    }
    Ok(())
}

#[test]
fn identity_integer_bitcast_rejects_forged_source_and_kind()
-> Result<(), String> {
    for signed in [true, false] {
        let (target, projection) =
            lowered_same_kind_bitcast_fixture(signed, u32::MAX)?;
        check_same_kind_projection_forgery(&projection)?;
        check_same_kind_wire_forgery(&target, signed)?;
    }
    Ok(())
}

fn lowered_unsigned_zero_extend_fixture(
    source: Option<u8>,
) -> Result<LoweredByteFixture, String> {
    let module = unsigned_zero_extend_module(source);
    validate_module(&module)
        .map_err(|error| format!("admit unsigned widening IR: {error:?}"))?;
    let bytes = canonical_bytes(&module)
        .map_err(|error| format!("encode unsigned widening IR: {error:?}"))?;
    let restored = canonical_module(&bytes)
        .map_err(|error| format!("restore unsigned widening IR: {error:?}"))?;
    if restored != module {
        return Err(String::from("unsigned widening typed-IR drifted"));
    }
    let input = project_typed_ir(&restored)?;
    let target = lower_typed_ir(&input)
        .map_err(|error| format!("lower unsigned widening: {error:?}"))?;
    assert_program_provenance(&restored, &target)?;
    Ok((target, input))
}

#[test]
fn unsigned_zero_extension_lowers_typed_byte_sources() -> Result<(), String> {
    for source in [None, Some(0), Some(1), Some(127), Some(128), Some(255)] {
        let (target, input) = lowered_unsigned_zero_extend_fixture(source)?;
        if input.functions.first().map(|function| function.return_kind)
            != Some(InputScalarType::U32)
        {
            return Err(String::from("zero-extended result type drifted"));
        }
        let function = target
            .functions
            .first()
            .ok_or_else(|| String::from("zero-extended target missing"))?;
        let operation = TernaryOperation::ZeroExtendU8ToU32 {
            result: 1,
            span: output_span(fixture_span(1, 2)),
            value: 0,
        };
        let terminal = TernaryOperation::ReturnU32 {
            span: output_span(fixture_span(2, 3)),
            value: 1,
        };
        if function.operations.get(1) != Some(&operation)
            || function.operations.last() != Some(&terminal)
        {
            return Err(String::from("zero-extended SSA/provenance drifted"));
        }
        let bytes = canonical_ternary_bytes(&target)
            .map_err(|error| format!("encode widened state: {error:?}"))?;
        let tag = [16u8, 1, 0, 0, 0];
        if !bytes.windows(tag.len()).any(|wire| wire == tag)
            || canonical_ternary_program(&bytes) != Ok(target)
        {
            return Err(String::from(
                "zero-extension canonical round trip drifted",
            ));
        }
    }
    Ok(())
}

#[test]
fn unsigned_zero_extension_rejects_projection_forgery() -> Result<(), String> {
    let (_program, input) = lowered_unsigned_zero_extend_fixture(Some(255))?;
    for variation in 0u8..4u8 {
        let mut forged = input.clone();
        let instruction = forged
            .functions
            .first_mut()
            .and_then(|function| function.blocks.first_mut())
            .and_then(|block| block.instructions.get_mut(1))
            .ok_or_else(|| String::from("zero-extension projection missing"))?;
        let InputInstruction::ZeroExtendInteger {
            result,
            type_kind,
            value,
            ..
        } = instruction
        else {
            return Err(String::from("zero-extension projection changed"));
        };
        match variation {
            0 => *type_kind = InputScalarType::I32,
            1 => *value = 99,
            2 => *result = 0,
            3 => *value = 1,
            _ => return Err(String::from("unknown widening forgery")),
        }
        let expected = if variation == 2 {
            TernaryLoweringError::InvalidProjection
        } else {
            TernaryLoweringError::UnsupportedInstruction
        };
        if lower_typed_ir(&forged) != Err(expected) {
            return Err(format!("forged zero-extension {variation} admitted"));
        }
    }
    Ok(())
}

#[test]
fn unsigned_zero_extension_checkpoint_rejects_retyped_source()
-> Result<(), String> {
    let (program, _input) = lowered_unsigned_zero_extend_fixture(Some(255))?;
    let bytes = canonical_ternary_bytes(&program).map_err(|error| {
        format!("encode zero-extension checkpoint: {error:?}")
    })?;
    let prefix = [16u8, 1, 0, 0, 0];
    let offset = bytes
        .windows(prefix.len())
        .position(|wire| wire == prefix)
        .ok_or_else(|| String::from("zero-extension opcode missing"))?;
    for (tag, expected) in [
        (
            5u8,
            TernaryProgramCodecError::Validation(
                TernaryProgramValidationError::SsaValue,
            ),
        ),
        (
            15u8,
            TernaryProgramCodecError::Validation(
                TernaryProgramValidationError::SsaValue,
            ),
        ),
        (84u8, TernaryProgramCodecError::UnknownTag),
    ] {
        let mut forged = bytes.clone();
        *forged
            .get_mut(offset)
            .ok_or_else(|| String::from("zero-extension tag missing"))? = tag;
        if canonical_ternary_program(&forged) != Err(expected) {
            return Err(format!("forged widening opcode {tag} admitted"));
        }
    }
    let mut missing = bytes;
    let source_offset = offset
        .checked_add(29)
        .ok_or_else(|| String::from("widening source offset overflow"))?;
    missing
        .get_mut(source_offset..source_offset + 4)
        .ok_or_else(|| String::from("widening source bytes absent"))?
        .copy_from_slice(&99u32.to_le_bytes());
    if canonical_ternary_program(&missing)
        != Err(TernaryProgramCodecError::Validation(
            TernaryProgramValidationError::SsaValue,
        ))
    {
        return Err(String::from("undefined widening source admitted"));
    }
    Ok(())
}

fn lowered_unsigned_truncate_fixture(
    bits: u32,
) -> Result<LoweredByteFixture, String> {
    let module = unsigned_truncate_module(bits);
    validate_module(&module)
        .map_err(|error| format!("admit unsigned truncation IR: {error:?}"))?;
    let typed_bytes = canonical_bytes(&module)
        .map_err(|error| format!("encode unsigned truncation IR: {error:?}"))?;
    let restored = canonical_module(&typed_bytes).map_err(|error| {
        format!("restore unsigned truncation IR: {error:?}")
    })?;
    if restored != module {
        return Err(String::from("unsigned truncation typed IR drifted"));
    }
    let projected = project_typed_ir(&restored)?;
    let target = lower_typed_ir(&projected)
        .map_err(|error| format!("lower unsigned truncation: {error:?}"))?;
    assert_program_provenance(&restored, &target)?;
    Ok((target, projected))
}

#[test]
fn unsigned_truncation_preserves_exact_low_byte_and_ssa() -> Result<(), String>
{
    for bits in [0u32, 1, 0xff, 0x100, 0x1234_5678, 0x8000_0080, u32::MAX] {
        let (program, input) = lowered_unsigned_truncate_fixture(bits)?;
        if input.functions.first().map(|function| function.return_kind)
            != Some(InputScalarType::U8)
        {
            return Err(String::from("truncated unsigned return type changed"));
        }
        let function = program.functions.first().ok_or_else(|| {
            String::from("unsigned truncate function missing")
        })?;
        if function.operations.get(1)
            != Some(&TernaryOperation::TruncateU32ToU8 {
                result: 1,
                span: output_span(fixture_span(1, 2)),
                value: 0,
            })
            || function.operations.last()
                != Some(&TernaryOperation::ReturnU8 {
                    span: output_span(fixture_span(2, 3)),
                    value: 1,
                })
        {
            return Err(String::from(
                "unsigned truncation SSA/provenance drifted",
            ));
        }
        let actual_low_byte = u8::try_from(bits & 0xff)
            .map_err(|error| format!("convert low byte: {error}"))?;
        if actual_low_byte != bits.to_le_bytes()[0] {
            return Err(String::from("low-byte truncation contract drifted"));
        }
        let encoded = canonical_ternary_bytes(&program)
            .map_err(|error| format!("encode unsigned truncate: {error:?}"))?;
        let prefix = [15u8, 1, 0, 0, 0];
        if !encoded.windows(prefix.len()).any(|window| window == prefix)
            || canonical_ternary_program(&encoded) != Ok(program)
        {
            return Err(String::from(
                "unsigned truncate canonical tag drifted",
            ));
        }
    }
    Ok(())
}

#[test]
fn unsigned_truncation_rejects_wrong_source_and_destination()
-> Result<(), String> {
    let (_program, projected) = lowered_unsigned_truncate_fixture(0xffff_ff80)?;
    for variation in 0u8..4u8 {
        let mut forged = projected.clone();
        let instruction = forged
            .functions
            .first_mut()
            .and_then(|function| function.blocks.first_mut())
            .and_then(|block| block.instructions.get_mut(1))
            .ok_or_else(|| {
                String::from("unsigned truncate projection missing")
            })?;
        let InputInstruction::TruncateInteger {
            result, type_kind, value, ..
        } = instruction
        else {
            return Err(String::from("unsigned truncate projection changed"));
        };
        match variation {
            0 => *type_kind = InputScalarType::I32,
            1 => *value = 99,
            2 => *result = 0,
            3 => *value = 1,
            _ => return Err(String::from("unknown truncate forgery")),
        }
        let expected = if variation == 2 {
            TernaryLoweringError::InvalidProjection
        } else {
            TernaryLoweringError::UnsupportedInstruction
        };
        if lower_typed_ir(&forged) != Err(expected) {
            return Err(format!(
                "forged unsigned truncation {variation} was admitted"
            ));
        }
    }
    Ok(())
}

#[test]
fn unsigned_truncation_checkpoint_rejects_signed_tag_and_undefined_use()
-> Result<(), String> {
    let (program, _input) = lowered_unsigned_truncate_fixture(u32::MAX)?;
    let bytes = canonical_ternary_bytes(&program)
        .map_err(|error| format!("encode unsigned truncate: {error:?}"))?;
    let prefix = [15u8, 1, 0, 0, 0];
    let offset = bytes
        .windows(prefix.len())
        .position(|window| window == prefix)
        .ok_or_else(|| String::from("unsigned truncate opcode missing"))?;
    for (forged_tag, expected) in [
        (
            5u8,
            TernaryProgramCodecError::Validation(
                TernaryProgramValidationError::SsaValue,
            ),
        ),
        (84u8, TernaryProgramCodecError::UnknownTag),
    ] {
        let mut forged = bytes.clone();
        *forged
            .get_mut(offset)
            .ok_or_else(|| String::from("unsigned truncate tag absent"))? =
            forged_tag;
        if canonical_ternary_program(&forged) != Err(expected) {
            return Err(format!("forged truncation tag {forged_tag} admitted"));
        }
    }
    let mut forged = bytes;
    let value_offset = offset.checked_add(29).ok_or_else(|| {
        String::from("unsigned truncate value offset overflow")
    })?;
    forged
        .get_mut(value_offset..value_offset + 4)
        .ok_or_else(|| String::from("unsigned truncate value missing"))?
        .copy_from_slice(&99u32.to_le_bytes());
    if canonical_ternary_program(&forged)
        != Err(TernaryProgramCodecError::Validation(
            TernaryProgramValidationError::SsaValue,
        ))
    {
        return Err(String::from("undefined truncated SSA use was admitted"));
    }
    Ok(())
}

#[test]
fn unsigned_bitwise_accepts_aliased_typed_operands() -> Result<(), String> {
    for operation in [BinaryOp::And, BinaryOp::Or, BinaryOp::Xor] {
        for bits in [0u32, 1, 0x8000_0000, 0x5555_5555, u32::MAX] {
            let module = unsigned_alias_bitwise_module(bits, operation);
            validate_module(&module).map_err(|error| {
                format!("admit aliased unsigned IR: {error:?}")
            })?;
            let typed = canonical_bytes(&module).map_err(|error| {
                format!("encode aliased typed IR: {error:?}")
            })?;
            let restored = canonical_module(&typed).map_err(|error| {
                format!("restore aliased typed IR: {error:?}")
            })?;
            if restored != module {
                return Err(String::from("aliased typed IR drifted"));
            }
            let projected = project_typed_ir(&restored)?;
            let program = lower_typed_ir(&projected).map_err(|error| {
                format!("lower aliased unsigned: {error:?}")
            })?;
            let function = program.functions.first().ok_or_else(|| {
                String::from("aliased target function missing")
            })?;
            let span = output_span(fixture_span(1, 2));
            let expected = expected_unsigned_alias_operation(operation, span);
            if function.operations.get(1) != Some(&expected)
                || function.operations.last()
                    != Some(&TernaryOperation::ReturnU32 {
                        span: output_span(fixture_span(2, 3)),
                        value: 1,
                    })
            {
                return Err(String::from("aliased unsigned operand drifted"));
            }
            let encoded =
                canonical_ternary_bytes(&program).map_err(|error| {
                    format!("encode aliased ternary: {error:?}")
                })?;
            if canonical_ternary_program(&encoded) != Ok(program) {
                return Err(String::from(
                    "aliased unsigned checkpoint drifted",
                ));
            }
        }
    }
    Ok(())
}

fn assert_signed_alias_shape(
    function: &ternary_lowering::TernaryFunction,
    bits: u32,
    operation: BinaryOp,
) -> Result<(), String> {
    let source_span = output_span(fixture_span(0, 1));
    if !matches!(function.operations.first(),
        Some(TernaryOperation::MaterializeI32 { result: 0, scalar, span })
            if scalar.bits() == bits && *span == source_span)
    {
        return Err(String::from("aliased signed input bits drifted"));
    }
    let span = output_span(fixture_span(1, 2));
    let expected = if operation == BinaryOp::And {
        TernaryOperation::AndI32 {
            left: 0,
            result: 1,
            right: 0,
            span,
        }
    } else if operation == BinaryOp::Or {
        TernaryOperation::OrI32 {
            left: 0,
            result: 1,
            right: 0,
            span,
        }
    } else if operation == BinaryOp::Xor {
        TernaryOperation::XorI32 {
            left: 0,
            result: 1,
            right: 0,
            span,
        }
    } else {
        return Err(String::from("unexpected signed bitwise operation"));
    };
    if function.operations.len() != 3
        || function.operations.get(1) != Some(&expected)
        || function.operations.last()
            != Some(&TernaryOperation::Return {
                span: output_span(fixture_span(2, 3)),
                value: 1,
            })
    {
        return Err(String::from("aliased signed SSA or return drifted"));
    }
    Ok(())
}

#[test]
fn signed_bitwise_accepts_aliased_typed_operands() -> Result<(), String> {
    for (operation, tag) in [
        (BinaryOp::And, 0u8),
        (BinaryOp::Or, 6u8),
        (BinaryOp::Xor, 7u8),
    ] {
        for bits in [0u32, 1, 0x8000_0000, 0x5555_5555, u32::MAX] {
            let module = signed_alias_bitwise_module(bits, operation);
            validate_module(&module).map_err(|error| {
                format!("admit aliased signed IR: {error:?}")
            })?;
            let typed = canonical_bytes(&module).map_err(|error| {
                format!("encode aliased signed IR: {error:?}")
            })?;
            let restored = canonical_module(&typed).map_err(|error| {
                format!("restore aliased signed IR: {error:?}")
            })?;
            if restored != module {
                return Err(String::from("aliased signed typed IR drifted"));
            }
            let projected = project_typed_ir(&restored)?;
            let target = lower_typed_ir(&projected).map_err(|error| {
                format!("lower aliased signed IR: {error:?}")
            })?;
            assert_program_provenance(&restored, &target)?;
            if projected
                .functions
                .first()
                .map(|function| function.return_kind)
                != Some(InputScalarType::I32)
            {
                return Err(String::from("aliased signed return kind drifted"));
            }
            let function = target.functions.first().ok_or_else(|| {
                String::from("aliased signed target function missing")
            })?;
            assert_signed_alias_shape(function, bits, operation)?;
            let encoded =
                canonical_ternary_bytes(&target).map_err(|error| {
                    format!("encode aliased signed ternary: {error:?}")
                })?;
            let pattern = [tag, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0];
            if !encoded.windows(pattern.len()).any(|part| part == pattern)
                || canonical_ternary_program(&encoded) != Ok(target)
            {
                return Err(String::from("aliased signed checkpoint drifted"));
            }
        }
    }
    Ok(())
}

fn assert_chain_materialization(
    operations: &[TernaryOperation],
    signed: bool,
    bits: u32,
) -> Result<(), String> {
    let scalar = ternary_lowering::TernaryI32Scalar::from_bits(bits);
    let span = output_span(fixture_span(0, 1));
    let first = if signed {
        TernaryOperation::MaterializeI32 { result: 0, span, scalar }
    } else {
        TernaryOperation::MaterializeU32 { result: 0, span, scalar }
    };
    if operations.first() != Some(&first) {
        return Err(String::from("Boolean chain input bits drifted"));
    }
    Ok(())
}

const fn first_bool_chain_conversion(signed: bool) -> TernaryOperation {
    let span = output_span(fixture_span(1, 2));
    if signed {
        TernaryOperation::I32ToBool {
            result: 1,
            span,
            value: 0,
        }
    } else {
        TernaryOperation::U32ToBool {
            result: 1,
            span,
            value: 0,
        }
    }
}

#[test]
fn typed_integer_boolean_conversion_chain_preserves_distinct_ssa()
-> Result<(), String> {
    for signed in [true, false] {
        for bits in [0u32, 1, 0x8000_0000, u32::MAX] {
            let module = chained_bool_conversion_module(signed, bits);
            validate_module(&module)
                .map_err(|error| format!("admit Boolean chain: {error:?}"))?;
            let encoded = canonical_bytes(&module)
                .map_err(|error| format!("encode Boolean chain: {error:?}"))?;
            let restored = canonical_module(&encoded)
                .map_err(|error| format!("decode Boolean chain: {error:?}"))?;
            if restored != module {
                return Err(String::from("typed Boolean chain drifted"));
            }
            let projected = project_typed_ir(&restored)?;
            let target = lower_typed_ir(&projected)
                .map_err(|error| format!("lower Boolean chain: {error:?}"))?;
            assert_program_provenance(&restored, &target)?;
            let operations = &target
                .functions
                .first()
                .ok_or_else(|| String::from("Boolean chain target absent"))?
                .operations;
            assert_chain_materialization(operations, signed, bits)?;
            let first_conversion = first_bool_chain_conversion(signed);
            let second_conversion = TernaryOperation::BoolToI32 {
                result: 2,
                span: output_span(fixture_span(2, 3)),
                value: 1,
            };
            if operations.get(1) != Some(&first_conversion)
                || operations.get(2) != Some(&second_conversion)
                || operations.last()
                    != Some(&TernaryOperation::Return {
                        span: output_span(fixture_span(3, 4)),
                        value: 2,
                    })
            {
                return Err(String::from(
                    "Boolean conversion SSA chain drifted",
                ));
            }
            let canonical = canonical_ternary_bytes(&target)
                .map_err(|error| format!("encode target chain: {error:?}"))?;
            if canonical_ternary_program(&canonical) != Ok(target) {
                return Err(String::from(
                    "Boolean chain target restoration drifted",
                ));
            }
        }
    }
    Ok(())
}

fn lowered_truncated_byte_truth_fixture(
    bits: u32,
) -> Result<LoweredByteFixture, String> {
    let module = truncated_byte_truth_module(bits);
    validate_module(&module)
        .map_err(|error| format!("admit truncated byte truth: {error:?}"))?;
    let encoded = canonical_bytes(&module)
        .map_err(|error| format!("encode truncated byte truth: {error:?}"))?;
    let restored = canonical_module(&encoded)
        .map_err(|error| format!("restore truncated byte truth: {error:?}"))?;
    if restored != module {
        return Err(String::from("truncated byte truth typed-IR drifted"));
    }
    let projection = project_typed_ir(&restored)?;
    let target = lower_typed_ir(&projection)
        .map_err(|error| format!("lower truncated byte truth: {error:?}"))?;
    assert_program_provenance(&restored, &target)?;
    Ok((target, projection))
}

fn assert_truncated_byte_truth_operations(
    bits: u32,
    target: &ternary_lowering::TernaryProgram,
) -> Result<(), String> {
    let operations = &target
        .functions
        .first()
        .ok_or_else(|| String::from("truncated byte truth target missing"))?
        .operations;
    let expected = [
        TernaryOperation::MaterializeU32 {
            result: 0,
            scalar: ternary_lowering::TernaryI32Scalar::from_bits(bits),
            span: output_span(fixture_span(0, 1)),
        },
        TernaryOperation::TruncateU32ToU8 {
            result: 1,
            span: output_span(fixture_span(1, 2)),
            value: 0,
        },
        TernaryOperation::U8ToBool {
            result: 2,
            span: output_span(fixture_span(2, 3)),
            value: 1,
        },
        TernaryOperation::BoolToI32 {
            result: 3,
            span: output_span(fixture_span(3, 4)),
            value: 2,
        },
        TernaryOperation::Return {
            span: output_span(fixture_span(4, 5)),
            value: 3,
        },
    ];
    if operations.as_slice() != expected {
        return Err(String::from("truncated byte truth operation drifted"));
    }
    let bytes = canonical_ternary_bytes(target)
        .map_err(|error| format!("encode truncated byte truth: {error:?}"))?;
    if canonical_ternary_program(&bytes) != Ok(target.clone()) {
        return Err(String::from("truncated byte truth target drifted"));
    }
    Ok(())
}

#[test]
fn typed_truncated_byte_truth_preserves_three_cast_identities()
-> Result<(), String> {
    for bits in [0u32, 1, 0xff, 0x100, 0x8000_0080, u32::MAX] {
        let (target, _projection) = lowered_truncated_byte_truth_fixture(bits)?;
        assert_truncated_byte_truth_operations(bits, &target)?;
    }
    Ok(())
}

fn assert_mixed_return_members(
    target: &ternary_lowering::TernaryProgram,
    void_first: bool,
    with_io: bool,
) -> Result<(), String> {
    let void_index = usize::from(!void_first);
    let value_index = usize::from(void_first);
    let void = target
        .functions
        .get(void_index)
        .ok_or_else(|| String::from("void member absent"))?;
    let value = target
        .functions
        .get(value_index)
        .ok_or_else(|| String::from("value member absent"))?;
    let void_end = if with_io {
        3
    } else {
        1
    };
    let void_start = u32::try_from(void_index)
        .map_err(|error| format!("void index overflow: {error}"))?
        .saturating_mul(5);
    let void_final = void_start.saturating_add(void_end);
    if void.id != u32::try_from(void_index).unwrap_or(u32::MAX)
        || void.name != "void_member"
        || void.operations.len()
            != if with_io {
                3
            } else {
                1
            }
        || void.operations.last()
            != Some(&TernaryOperation::ReturnVoid {
                span: output_span(fixture_span(
                    void_final.saturating_sub(1),
                    void_final,
                )),
            })
        || value.id != u32::try_from(value_index).unwrap_or(u32::MAX)
        || value.name != "value_member"
        || value.operations.last().is_none_or(|operation| {
            !matches!(operation, TernaryOperation::Return { value: 0, .. })
        })
    {
        return Err(String::from("mixed return order or SSA drifted"));
    }
    Ok(())
}

fn assert_mixed_return_fixture(
    void_first: bool,
    with_io: bool,
) -> Result<(), String> {
    let module = mixed_return_module(void_first, with_io);
    validate_module(&module)
        .map_err(|error| format!("admit mixed returns: {error:?}"))?;
    let typed = canonical_bytes(&module)
        .map_err(|error| format!("encode mixed returns: {error:?}"))?;
    if canonical_module(&typed) != Ok(module.clone()) {
        return Err(String::from("mixed typed functions drifted"));
    }
    let projection = project_typed_ir(&module)?;
    let target = lower_typed_ir(&projection)
        .map_err(|error| format!("lower mixed returns: {error:?}"))?;
    assert_mixed_return_members(&target, void_first, with_io)?;
    let encoded = canonical_ternary_bytes(&target)
        .map_err(|error| format!("encode mixed target: {error:?}"))?;
    if canonical_ternary_program(&encoded) != Ok(target.clone()) {
        return Err(String::from("mixed target restoration drifted"));
    }
    let label = match (void_first, with_io) {
        (true, true) => "mixed-void-first-byte",
        (true, false) => "mixed-void-first-empty",
        (false, true) => "mixed-value-first-byte",
        (false, false) => "mixed-value-first-empty",
    };
    assert_boolean_inspector_convergence(label, &target, &projection)?;
    let previous = lowered_return_fixture()?;
    assert_boolean_crash_generation(&previous, &target)?;
    let mut swapped = target;
    swapped.functions.swap(0, 1);
    if canonical_ternary_bytes(&swapped)
        != Err(TernaryProgramCodecError::Validation(
            TernaryProgramValidationError::FunctionIdentity,
        ))
    {
        return Err(String::from("swapped mixed function order admitted"));
    }
    Ok(())
}

#[test]
fn mixed_void_and_value_functions_preserve_function_local_ssa()
-> Result<(), String> {
    for void_first in [true, false] {
        for with_io in [true, false] {
            assert_mixed_return_fixture(void_first, with_io)?;
        }
    }
    Ok(())
}

fn lowered_void_function_fixture(
    with_io: bool,
) -> Result<LoweredByteFixture, String> {
    let module = void_function_module(with_io);
    validate_module(&module)
        .map_err(|error| format!("admit void function: {error:?}"))?;
    let encoded = canonical_bytes(&module)
        .map_err(|error| format!("encode void typed IR: {error:?}"))?;
    let restored = canonical_module(&encoded)
        .map_err(|error| format!("restore void typed IR: {error:?}"))?;
    if restored != module {
        return Err(String::from("void function typed IR drifted"));
    }
    let projection = project_typed_ir(&restored)?;
    let target = lower_typed_ir(&projection)
        .map_err(|error| format!("lower void function: {error:?}"))?;
    assert_program_provenance(&restored, &target)?;
    Ok((target, projection))
}

fn assert_void_checkpoint(
    target: &ternary_lowering::TernaryProgram,
    with_io: bool,
) -> Result<Vec<u8>, String> {
    let operations = &target
        .functions
        .first()
        .ok_or_else(|| String::from("void function target absent"))?
        .operations;
    let end: u32 = if with_io {
        3
    } else {
        1
    };
    let final_operation = TernaryOperation::ReturnVoid {
        span: output_span(fixture_span(end.saturating_sub(1), end)),
    };
    if operations.last() != Some(&final_operation)
        || operations.len()
            != if with_io {
                3
            } else {
                1
            }
    {
        return Err(String::from("void return operation drifted"));
    }
    if with_io
        && (operations.first()
            != Some(&TernaryOperation::ByteInput {
                result: 0,
                span: output_span(fixture_span(0, 1)),
            })
            || operations.get(1)
                != Some(&TernaryOperation::ByteOutput {
                    span: output_span(fixture_span(1, 2)),
                    value: 0,
                }))
    {
        return Err(String::from("void byte effect order drifted"));
    }
    let wire = canonical_ternary_bytes(target)
        .map_err(|error| format!("encode void target: {error:?}"))?;
    if !wire.windows(25).any(|record| record.first() == Some(&49))
        || canonical_ternary_program(&wire) != Ok(target.clone())
    {
        return Err(String::from("void wire tag/shape drifted"));
    }
    Ok(wire)
}

fn reject_void_projection_forgery(
    projection: &TypedIrInput,
    with_io: bool,
) -> Result<(), String> {
    for variation in 0u8..3u8 {
        let mut forged = projection.clone();
        let function = forged
            .functions
            .first_mut()
            .ok_or_else(|| String::from("void input function missing"))?;
        match variation {
            0 => function.return_kind = InputScalarType::I32,
            1 => function.return_kind = InputScalarType::Other,
            2 => {
                let block = function
                    .blocks
                    .first_mut()
                    .ok_or_else(|| String::from("void block missing"))?;
                block.terminator = InputTerminator::Return {
                    span: input_span(fixture_span(
                        if with_io {
                            2
                        } else {
                            0
                        },
                        if with_io {
                            3
                        } else {
                            1
                        },
                    )),
                    value: Some(0),
                };
            },
            _ => return Err(String::from("unsupported void forgery")),
        }
        if lower_typed_ir(&forged)
            != Err(TernaryLoweringError::UnsupportedTerminator)
        {
            return Err(format!("void forgery {variation} admitted"));
        }
    }
    Ok(())
}

fn reject_void_checkpoint_forgery(
    target: &ternary_lowering::TernaryProgram,
    with_io: bool,
) -> Result<(), String> {
    let wire = assert_void_checkpoint(target, with_io)?;
    let offset = wire
        .len()
        .checked_sub(25)
        .ok_or_else(|| String::from("void operation missing"))?;
    if wire.get(offset) != Some(&49) {
        return Err(String::from("void record not 25-byte trailing opcode"));
    }
    let mut unknown = wire.clone();
    *unknown
        .get_mut(offset)
        .ok_or_else(|| String::from("void opcode absent"))? = 84;
    if canonical_ternary_program(&unknown)
        != Err(TernaryProgramCodecError::UnknownTag)
    {
        return Err(String::from("unknown void opcode admitted"));
    }
    let mut wrong_record = wire.clone();
    *wrong_record
        .get_mut(offset)
        .ok_or_else(|| String::from("void opcode missing"))? = 1;
    if canonical_ternary_program(&wrong_record)
        != Err(TernaryProgramCodecError::Truncated)
    {
        return Err(String::from("short byte-input operation admitted"));
    }
    let mut truncated = wire;
    let _last = truncated.pop();
    if canonical_ternary_program(&truncated)
        != Err(TernaryProgramCodecError::Truncated)
    {
        return Err(String::from("truncated void span admitted"));
    }
    let mut malformed = target.clone();
    let function = malformed
        .functions
        .first_mut()
        .ok_or_else(|| String::from("target void function absent"))?;
    function.operations.insert(0, TernaryOperation::ReturnVoid {
        span: output_span(fixture_span(0, 1)),
    });
    if canonical_ternary_bytes(&malformed)
        != Err(TernaryProgramCodecError::Validation(
            TernaryProgramValidationError::Terminator,
        ))
    {
        return Err(String::from("early void return admitted"));
    }
    Ok(())
}

#[test]
fn void_return_projection_and_checkpoint_reject_malformed_terminators()
-> Result<(), String> {
    for with_io in [false, true] {
        let (target, projection) = lowered_void_function_fixture(with_io)?;
        reject_void_projection_forgery(&projection, with_io)?;
        reject_void_checkpoint_forgery(&target, with_io)?;
    }
    Ok(())
}

#[test]
fn void_return_inspector_and_crash_recovery_preserve_no_value()
-> Result<(), String> {
    let previous = lowered_return_fixture()?;
    for with_io in [false, true] {
        let (target, projection) = lowered_void_function_fixture(with_io)?;
        let _wire = assert_void_checkpoint(&target, with_io)?;
        let label = if with_io {
            "void-byte-echo"
        } else {
            "void-empty"
        };
        assert_boolean_inspector_convergence(label, &target, &projection)?;
        assert_boolean_crash_generation(&previous, &target)?;
    }
    Ok(())
}

#[test]
fn void_return_inspector_rejects_unknown_successor_tag() -> Result<(), String> {
    for with_io in [false, true] {
        let (target, _projection) = lowered_void_function_fixture(with_io)?;
        let mut wire = assert_void_checkpoint(&target, with_io)?;
        let offset = wire
            .len()
            .checked_sub(25)
            .ok_or_else(|| String::from("void checkpoint too short"))?;
        *wire
            .get_mut(offset)
            .ok_or_else(|| String::from("void opcode absent"))? = 84;
        let label = if with_io {
            "void-bad-io"
        } else {
            "void-bad-empty"
        };
        let (progress, directory) =
            publish_ternary_progress_fixture(label, &wire)?;
        let outcome = resume_ternary_from_progress(
            &repository_python(),
            &progress_inspector(),
            &progress,
        );
        remove_dir_all(&directory)
            .map_err(|error| format!("clean void failure: {error}"))?;
        if outcome
            != Err(TernaryProgressCheckpointError::Stage(
                TernaryStageError::Checkpoint(
                    TernaryProgramCodecError::UnknownTag,
                ),
            ))
        {
            return Err(String::from("inspector admitted unknown void opcode"));
        }
    }
    Ok(())
}

#[test]
fn typed_void_functions_preserve_empty_return_without_fake_ssa()
-> Result<(), String> {
    for with_io in [false, true] {
        let (target, projection) = lowered_void_function_fixture(with_io)?;
        if projection
            .functions
            .first()
            .map(|function| function.return_kind)
            != Some(InputScalarType::Void)
        {
            return Err(String::from("void return kind drifted"));
        }
        let _wire = assert_void_checkpoint(&target, with_io)?;
    }
    Ok(())
}

fn lowered_same_kind_byte_bitcast_fixture(
    bits: u8,
    signed: bool,
) -> Result<LoweredByteFixture, String> {
    let module = same_kind_byte_bitcast_module(bits, signed);
    validate_module(&module)
        .map_err(|error| format!("admit same-kind byte bitcast: {error:?}"))?;
    let encoded = canonical_bytes(&module)
        .map_err(|error| format!("encode same-kind byte IR: {error:?}"))?;
    let restored = canonical_module(&encoded)
        .map_err(|error| format!("restore same-kind byte IR: {error:?}"))?;
    if restored != module {
        return Err(String::from("same-kind byte typed IR drifted"));
    }
    let input = project_typed_ir(&restored)?;
    let target = lower_typed_ir(&input)
        .map_err(|error| format!("lower same-kind byte bitcast: {error:?}"))?;
    assert_program_provenance(&restored, &target)?;
    Ok((target, input))
}

fn same_kind_byte_expected_operations(
    bits: u8,
    signed: bool,
) -> Vec<TernaryOperation> {
    let source_span = output_span(fixture_span(0, 1));
    let cast_span = output_span(fixture_span(1, 2));
    let widen_span = output_span(fixture_span(2, 3));
    let return_span = output_span(fixture_span(3, 4));
    let scalar = ternary_lowering::TernaryU8Scalar::from_bits(bits);
    if signed {
        vec![
            TernaryOperation::MaterializeI8 {
                result: 0,
                scalar,
                span: source_span,
            },
            TernaryOperation::BitcastI8ToI8 {
                result: 1,
                span: cast_span,
                value: 0,
            },
            TernaryOperation::SignExtendI8ToI32 {
                result: 2,
                span: widen_span,
                value: 1,
            },
            TernaryOperation::Return {
                span: return_span,
                value: 2,
            },
        ]
    } else {
        vec![
            TernaryOperation::MaterializeU8 {
                result: 0,
                scalar,
                span: source_span,
            },
            TernaryOperation::BitcastU8ToU8 {
                result: 1,
                span: cast_span,
                value: 0,
            },
            TernaryOperation::ZeroExtendU8ToU32 {
                result: 2,
                span: widen_span,
                value: 1,
            },
            TernaryOperation::ReturnU32 {
                span: return_span,
                value: 2,
            },
        ]
    }
}

fn assert_same_kind_byte_checkpoint(
    bits: u8,
    signed: bool,
    target: &ternary_lowering::TernaryProgram,
) -> Result<Vec<u8>, String> {
    let expected = same_kind_byte_expected_operations(bits, signed);
    let operations = &target
        .functions
        .first()
        .ok_or_else(|| String::from("same-kind byte target absent"))?
        .operations;
    if operations != &expected {
        return Err(String::from("same-kind byte SSA or spans drifted"));
    }
    let wire = canonical_ternary_bytes(target)
        .map_err(|error| format!("encode same-kind byte target: {error:?}"))?;
    let tag = if signed {
        55u8
    } else {
        56
    };
    if !wire.windows(5).any(|part| part == [tag, 1, 0, 0, 0])
        || canonical_ternary_program(&wire) != Ok(target.clone())
    {
        return Err(String::from("same-kind byte checkpoint drifted"));
    }
    Ok(wire)
}

fn reject_same_kind_byte_checkpoint(
    bits: u8,
    signed: bool,
    target: &ternary_lowering::TernaryProgram,
) -> Result<(), String> {
    let wire = assert_same_kind_byte_checkpoint(bits, signed, target)?;
    let tag = if signed {
        55u8
    } else {
        56
    };
    let opposite = if signed {
        56u8
    } else {
        55
    };
    let cross_kind = if signed {
        53u8
    } else {
        54
    };
    let offset = wire
        .windows(5)
        .position(|part| part == [tag, 1, 0, 0, 0])
        .ok_or_else(|| String::from("same-kind byte tag not present"))?;
    let failure = TernaryProgramCodecError::Validation(
        TernaryProgramValidationError::SsaValue,
    );
    for mutation in [
        (0usize, opposite, failure),
        (0, cross_kind, failure),
        (0, 84, TernaryProgramCodecError::UnknownTag),
        (1, 0, failure),
        (29, 99, failure),
    ] {
        reject_byte_bitcast_wire_mutation(&wire, offset, mutation)?;
    }
    Ok(())
}

#[test]
fn same_kind_byte_bitcasts_reject_wrong_source_types_and_ssa()
-> Result<(), String> {
    for bits in [0u8, 0x7f, 0x80, u8::MAX] {
        for signed in [true, false] {
            let (target, projection) =
                lowered_same_kind_byte_bitcast_fixture(bits, signed)?;
            reject_same_kind_byte_checkpoint(bits, signed, &target)?;
            for variation in 0u8..3 {
                reject_byte_bitcast_projection(&projection, variation)?;
            }
        }
    }
    Ok(())
}

#[test]
fn same_kind_byte_bitcasts_inspector_and_crash_recovery() -> Result<(), String>
{
    let previous = lowered_return_fixture()?;
    for signed in [true, false] {
        for bits in [0u8, 0x7f, 0x80, u8::MAX] {
            let (target, projection) =
                lowered_same_kind_byte_bitcast_fixture(bits, signed)?;
            let label = if signed {
                "same-signed-byte-bitcast"
            } else {
                "same-unsigned-byte-bitcast"
            };
            assert_boolean_inspector_convergence(label, &target, &projection)?;
            assert_boolean_crash_generation(&previous, &target)?;
        }
    }
    Ok(())
}

#[test]
fn same_kind_byte_bitcast_inspector_rejects_cross_kind_retags()
-> Result<(), String> {
    for signed in [true, false] {
        let (target, _projection) =
            lowered_same_kind_byte_bitcast_fixture(0x80, signed)?;
        let tag = if signed {
            55u8
        } else {
            56
        };
        let foreign = if signed {
            53u8
        } else {
            54
        };
        let label = if signed {
            "same-kind-signed-byte-forged-cross"
        } else {
            "same-kind-unsigned-byte-forged-cross"
        };
        assert_boolean_progress_tag_rejected(
            label,
            &target,
            (tag, 1, foreign),
        )?;
    }
    Ok(())
}

#[test]
fn same_kind_byte_bitcasts_preserve_all_byte_patterns() -> Result<(), String> {
    for bits in u8::MIN..=u8::MAX {
        for signed in [true, false] {
            let (target, input) =
                lowered_same_kind_byte_bitcast_fixture(bits, signed)?;
            if input.functions.first().map(|function| function.return_kind)
                != Some(if signed {
                    InputScalarType::I32
                } else {
                    InputScalarType::U32
                })
            {
                return Err(String::from("same-kind byte return kind drifted"));
            }
            let _wire =
                assert_same_kind_byte_checkpoint(bits, signed, &target)?;
        }
    }
    Ok(())
}

fn lowered_signed_byte_bitcast_fixture(
    bits: u8,
    signed_origin: bool,
) -> Result<LoweredByteFixture, String> {
    let module = signed_byte_bitcast_module(bits, signed_origin);
    validate_module(&module)
        .map_err(|error| format!("admit narrow bitcast: {error:?}"))?;
    let encoded = canonical_bytes(&module)
        .map_err(|error| format!("encode narrow bitcast IR: {error:?}"))?;
    let restored = canonical_module(&encoded)
        .map_err(|error| format!("restore narrow bitcast IR: {error:?}"))?;
    if restored != module {
        return Err(String::from("narrow bitcast typed IR drifted"));
    }
    let projection = project_typed_ir(&restored)?;
    let target = lower_typed_ir(&projection)
        .map_err(|error| format!("lower narrow bitcast: {error:?}"))?;
    assert_program_provenance(&restored, &target)?;
    Ok((target, projection))
}

fn expected_signed_byte_bitcast_operations(
    bits: u8,
    signed_origin: bool,
) -> Vec<TernaryOperation> {
    let byte_span = output_span(fixture_span(0, 1));
    let cast_span = output_span(fixture_span(1, 2));
    let widen_span = output_span(fixture_span(2, 3));
    let return_span = output_span(fixture_span(3, 4));
    let scalar = ternary_lowering::TernaryU8Scalar::from_bits(bits);
    if signed_origin {
        vec![
            TernaryOperation::MaterializeI8 {
                result: 0,
                scalar,
                span: byte_span,
            },
            TernaryOperation::BitcastI8ToU8 {
                result: 1,
                span: cast_span,
                value: 0,
            },
            TernaryOperation::ZeroExtendU8ToU32 {
                result: 2,
                span: widen_span,
                value: 1,
            },
            TernaryOperation::ReturnU32 {
                span: return_span,
                value: 2,
            },
        ]
    } else {
        vec![
            TernaryOperation::MaterializeU8 {
                result: 0,
                scalar,
                span: byte_span,
            },
            TernaryOperation::BitcastU8ToI8 {
                result: 1,
                span: cast_span,
                value: 0,
            },
            TernaryOperation::SignExtendI8ToI32 {
                result: 2,
                span: widen_span,
                value: 1,
            },
            TernaryOperation::Return {
                span: return_span,
                value: 2,
            },
        ]
    }
}

fn assert_signed_byte_bitcast_checkpoint(
    bits: u8,
    signed_origin: bool,
    target: &ternary_lowering::TernaryProgram,
) -> Result<Vec<u8>, String> {
    let expected = expected_signed_byte_bitcast_operations(bits, signed_origin);
    let operations = &target
        .functions
        .first()
        .ok_or_else(|| String::from("narrow bitcast function missing"))?
        .operations;
    if operations != &expected {
        return Err(String::from("narrow bitcast SSA or provenance drifted"));
    }
    let wire = canonical_ternary_bytes(target)
        .map_err(|error| format!("encode narrow bitcast: {error:?}"))?;
    let tag = if signed_origin {
        53u8
    } else {
        54
    };
    if !wire.windows(5).any(|part| part == [tag, 1, 0, 0, 0])
        || canonical_ternary_program(&wire) != Ok(target.clone())
    {
        return Err(String::from(
            "narrow bitcast wire tag or roundtrip drifted",
        ));
    }
    Ok(wire)
}

fn byte_bitcast_tag_offset(
    wire: &[u8],
    signed_origin: bool,
) -> Result<usize, String> {
    let tag = if signed_origin {
        53u8
    } else {
        54
    };
    wire.windows(5)
        .position(|chunk| chunk == [tag, 1, 0, 0, 0])
        .ok_or_else(|| String::from("byte bitcast record absent"))
}

fn reject_byte_bitcast_wire_mutation(
    wire: &[u8],
    offset: usize,
    mutation: (usize, u8, TernaryProgramCodecError),
) -> Result<(), String> {
    let (displacement, replacement, expected) = mutation;
    let mut forged = wire.to_vec();
    *forged
        .get_mut(offset.saturating_add(displacement))
        .ok_or_else(|| String::from("byte bitcast field absent"))? =
        replacement;
    if canonical_ternary_program(&forged) != Err(expected) {
        return Err(format!(
            "narrow cast field {displacement}/{replacement} admitted"
        ));
    }
    Ok(())
}

fn reject_byte_bitcast_checkpoint(
    bits: u8,
    signed_origin: bool,
    target: &ternary_lowering::TernaryProgram,
) -> Result<(), String> {
    let wire =
        assert_signed_byte_bitcast_checkpoint(bits, signed_origin, target)?;
    let offset = byte_bitcast_tag_offset(&wire, signed_origin)?;
    let failure = TernaryProgramCodecError::Validation(
        TernaryProgramValidationError::SsaValue,
    );
    let flip_tag = if signed_origin {
        54u8
    } else {
        53
    };
    for (displacement, replacement, expected) in [
        (0usize, flip_tag, failure),
        (0, 47, failure),
        (0, 84, TernaryProgramCodecError::UnknownTag),
        (1, 0, failure),
        (29, 99, failure),
    ] {
        reject_byte_bitcast_wire_mutation(
            &wire,
            offset,
            (displacement, replacement, expected),
        )?;
    }
    Ok(())
}

fn reject_byte_bitcast_projection(
    projection: &TypedIrInput,
    variation: u8,
) -> Result<(), String> {
    let mut forged = projection.clone();
    let instructions = &mut forged
        .functions
        .first_mut()
        .and_then(|function| function.blocks.first_mut())
        .ok_or_else(|| String::from("byte bitcast projection block missing"))?
        .instructions;
    let Some(InputInstruction::IntegerBitcast {
        result, type_kind, value, ..
    }) = instructions.get_mut(1)
    else {
        return Err(String::from("byte bitcast projection missing"));
    };
    match variation {
        0 => *type_kind = InputScalarType::I32,
        1 => *value = 99,
        2 => *result = 0,
        _ => return Err(String::from("unsupported narrow cast forgery")),
    }
    let expected = if variation == 2 {
        TernaryLoweringError::InvalidProjection
    } else {
        TernaryLoweringError::UnsupportedInstruction
    };
    if lower_typed_ir(&forged) != Err(expected) {
        return Err(format!("narrow bitcast projection {variation} admitted"));
    }
    Ok(())
}

#[test]
fn signed_unsigned_byte_bitcasts_reject_forged_types_and_ssa()
-> Result<(), String> {
    for bits in [0u8, 1, 0x7f, 0x80, u8::MAX] {
        for signed_origin in [true, false] {
            let (target, projection) =
                lowered_signed_byte_bitcast_fixture(bits, signed_origin)?;
            reject_byte_bitcast_checkpoint(bits, signed_origin, &target)?;
            for variation in 0u8..3 {
                reject_byte_bitcast_projection(&projection, variation)?;
            }
        }
    }
    Ok(())
}

#[test]
fn signed_unsigned_byte_bitcasts_restore_inspector_and_crash_generations()
-> Result<(), String> {
    let previous = lowered_return_fixture()?;
    for bits in [0u8, 0x7f, 0x80, u8::MAX] {
        for signed_origin in [true, false] {
            let (target, projection) =
                lowered_signed_byte_bitcast_fixture(bits, signed_origin)?;
            let label = if signed_origin {
                "signed-byte-to-unsigned-bitcast"
            } else {
                "unsigned-byte-to-signed-bitcast"
            };
            assert_boolean_inspector_convergence(label, &target, &projection)?;
            assert_boolean_crash_generation(&previous, &target)?;
        }
    }
    Ok(())
}

#[test]
fn signed_unsigned_byte_bitcast_inspector_rejects_direction_forgery()
-> Result<(), String> {
    for signed_origin in [true, false] {
        let (target, _projection) =
            lowered_signed_byte_bitcast_fixture(0x80, signed_origin)?;
        let tag = if signed_origin {
            53u8
        } else {
            54
        };
        let opposite = if signed_origin {
            54u8
        } else {
            53
        };
        let label = if signed_origin {
            "signed-byte-bitcast-forged-unsigned-source"
        } else {
            "unsigned-byte-bitcast-forged-signed-source"
        };
        assert_boolean_progress_tag_rejected(
            label,
            &target,
            (tag, 1, opposite),
        )?;
    }
    Ok(())
}

#[test]
fn signed_unsigned_byte_bitcasts_preserve_all_byte_patterns()
-> Result<(), String> {
    for bits in u8::MIN..=u8::MAX {
        for signed_origin in [true, false] {
            let (target, projection) =
                lowered_signed_byte_bitcast_fixture(bits, signed_origin)?;
            let expected_return = if signed_origin {
                InputScalarType::U32
            } else {
                InputScalarType::I32
            };
            if projection
                .functions
                .first()
                .map(|function| function.return_kind)
                != Some(expected_return)
            {
                return Err(String::from("narrow bitcast return type drifted"));
            }
            let _wire = assert_signed_byte_bitcast_checkpoint(
                bits,
                signed_origin,
                &target,
            )?;
        }
    }
    Ok(())
}

fn projected_signed_byte_return(
    bits: u8,
    cast: bool,
) -> Result<LoweredByteFixture, String> {
    let (_unused, mut input) = if cast {
        lowered_signed_byte_bitcast_fixture(bits, false)?
    } else {
        lowered_signed_byte_extension_fixture(bits)?
    };
    let function = input
        .functions
        .first_mut()
        .ok_or_else(|| String::from("signed byte fixture absent"))?;
    function.return_kind = InputScalarType::I8;
    let block = function
        .blocks
        .first_mut()
        .ok_or_else(|| String::from("signed byte block absent"))?;
    block.instructions.truncate(if cast {
        2
    } else {
        1
    });
    let InputTerminator::Return { ref mut value, .. } = block.terminator else {
        return Err(String::from("signed byte return absent"));
    };
    *value = Some(u32::from(cast));
    let output = lower_typed_ir(&input)
        .map_err(|error| format!("signed byte return: {error:?}"))?;
    Ok((output, input))
}

#[test]
fn direct_signed_byte_returns_preserve_all_byte_bits() -> Result<(), String> {
    for bits in u8::MIN..=u8::MAX {
        for cast in [false, true] {
            let (target, input) = projected_signed_byte_return(bits, cast)?;
            if input.functions.first().map(|function| function.return_kind)
                != Some(InputScalarType::I8)
            {
                return Err(String::from("signed byte return kind drifted"));
            }
            let operations = &target
                .functions
                .first()
                .ok_or_else(|| String::from("signed byte target missing"))?
                .operations;
            let return_id = u32::from(cast);
            let Some(InputTerminator::Return { .. }) = input
                .functions
                .first()
                .and_then(|function| function.blocks.first())
                .map(|block| &block.terminator)
            else {
                return Err(String::from("signed return span missing"));
            };
            if operations.last()
                != Some(&TernaryOperation::ReturnI8 {
                    span: output_span(fixture_span(
                        2 + u32::from(cast),
                        3 + u32::from(cast),
                    )),
                    value: return_id,
                })
            {
                return Err(String::from("signed byte return SSA drifted"));
            }
            let wire = canonical_ternary_bytes(&target)
                .map_err(|error| format!("encode signed byte: {error:?}"))?;
            if wire.get(wire.len().saturating_sub(29)) != Some(&57u8)
                || canonical_ternary_program(&wire) != Ok(target)
            {
                return Err(String::from("signed byte wire drifted"));
            }
        }
    }
    Ok(())
}

#[test]
fn direct_signed_byte_return_rejects_wrong_wire_tags() -> Result<(), String> {
    for cast in [false, true] {
        let (target, _) = projected_signed_byte_return(0x80, cast)?;
        let wire = canonical_ternary_bytes(&target)
            .map_err(|error| format!("encode signed return: {error:?}"))?;
        let offset = wire.len() - 29;
        let wrong = TernaryProgramCodecError::Validation(
            TernaryProgramValidationError::SsaValue,
        );
        for (tag, failure) in [
            (9u8, wrong),
            (4, wrong),
            (11, wrong),
            (84, TernaryProgramCodecError::UnknownTag),
        ] {
            let mut forged = wire.clone();
            *forged
                .get_mut(offset)
                .ok_or_else(|| String::from("signed return tag missing"))? =
                tag;
            if canonical_ternary_program(&forged) != Err(failure) {
                return Err(format!("signed return retag {tag} accepted"));
            }
        }
    }
    Ok(())
}

#[test]
fn direct_signed_return_rejects_missing_source() -> Result<(), String> {
    let (target, _) = projected_signed_byte_return(0xff, false)?;
    let mut wire = canonical_ternary_bytes(&target)
        .map_err(|error| format!("encode signed return: {error:?}"))?;
    *wire
        .last_mut()
        .ok_or_else(|| String::from("missing operand"))? = 99;
    let failure = TernaryProgramCodecError::Validation(
        TernaryProgramValidationError::SsaValue,
    );
    if canonical_ternary_program(&wire) != Err(failure) {
        return Err(String::from("invalid return source accepted"));
    }
    Ok(())
}

#[test]
fn direct_signed_return_projection_rejects_wrong_type() -> Result<(), String> {
    for cast in [false, true] {
        let (_, mut input) = projected_signed_byte_return(0x80, cast)?;
        input
            .functions
            .first_mut()
            .ok_or_else(|| String::from("signed return function absent"))?
            .return_kind = InputScalarType::U8;
        if lower_typed_ir(&input)
            != Err(TernaryLoweringError::UnsupportedTerminator)
        {
            return Err(String::from("wrong signed return category accepted"));
        }
    }
    Ok(())
}

#[test]
fn direct_signed_return_inspector_restores_checkpoint() -> Result<(), String> {
    for cast in [false, true] {
        for bits in [0u8, 0x7f, 0x80, u8::MAX] {
            let (target, input) = projected_signed_byte_return(bits, cast)?;
            let label = if cast {
                "signed-return-cast"
            } else {
                "signed-return-literal"
            };
            assert_boolean_inspector_convergence(label, &target, &input)?;
        }
    }
    Ok(())
}

#[test]
fn signed_byte_returns_keep_durable_generation() -> Result<(), String> {
    let previous = lowered_return_fixture()?;
    for cast in [false, true] {
        for bits in [0u8, 0x80, u8::MAX] {
            let (target, _) = projected_signed_byte_return(bits, cast)?;
            assert_boolean_crash_generation(&previous, &target)?;
        }
    }
    Ok(())
}

#[test]
fn direct_signed_return_rejects_premature_terminator() -> Result<(), String> {
    let (mut target, _) = projected_signed_byte_return(0x80, true)?;
    let function = target
        .functions
        .first_mut()
        .ok_or_else(|| String::from("signed return target absent"))?;
    function.operations.insert(2, TernaryOperation::ReturnI8 {
        span: output_span(fixture_span(0, 1)),
        value: 1,
    });
    if canonical_ternary_bytes(&target)
        != Err(TernaryProgramCodecError::Validation(
            TernaryProgramValidationError::Terminator,
        ))
    {
        return Err(String::from("early signed return admitted"));
    }
    Ok(())
}

fn check_signed_return_progress_rejection(
    tag: u8,
    expected: TernaryProgramCodecError,
) -> Result<(), String> {
    let (target, _) = projected_signed_byte_return(0x80, false)?;
    let mut wire = canonical_ternary_bytes(&target)
        .map_err(|error| format!("encode return: {error:?}"))?;
    let offset = wire
        .len()
        .checked_sub(29)
        .ok_or_else(|| String::from("signed return record short"))?;
    *wire
        .get_mut(offset)
        .ok_or_else(|| String::from("tag absent"))? = tag;
    let (progress, directory) =
        publish_ternary_progress_fixture("invalid-signed-byte-return", &wire)?;
    let restored = resume_ternary_from_progress(
        &repository_python(),
        &progress_inspector(),
        &progress,
    );
    remove_dir_all(&directory)
        .map_err(|error| format!("clean signed progress: {error}"))?;
    if restored
        != Err(TernaryProgressCheckpointError::Stage(
            TernaryStageError::Checkpoint(expected),
        ))
    {
        return Err(String::from("inspector accepted invalid signed return"));
    }
    Ok(())
}

#[test]
fn signed_return_inspector_rejects_retyping_and_unknown_tag()
-> Result<(), String> {
    let wrong_kind = TernaryProgramCodecError::Validation(
        TernaryProgramValidationError::SsaValue,
    );
    check_signed_return_progress_rejection(9, wrong_kind)?;
    check_signed_return_progress_rejection(
        84,
        TernaryProgramCodecError::UnknownTag,
    )?;
    Ok(())
}

fn lowered_signed_byte_extension_fixture(
    bits: u8,
) -> Result<LoweredByteFixture, String> {
    let module = signed_byte_extension_module(bits);
    validate_module(&module)
        .map_err(|error| format!("admit signed-byte extension: {error:?}"))?;
    let encoded = canonical_bytes(&module)
        .map_err(|error| format!("encode signed-byte IR: {error:?}"))?;
    let restored = canonical_module(&encoded)
        .map_err(|error| format!("restore signed-byte IR: {error:?}"))?;
    if restored != module {
        return Err(String::from("signed-byte typed IR drifted"));
    }
    let projection = project_typed_ir(&restored)?;
    let target = lower_typed_ir(&projection)
        .map_err(|error| format!("lower signed-byte extension: {error:?}"))?;
    assert_program_provenance(&restored, &target)?;
    Ok((target, projection))
}

fn lowered_signed_byte_truth_fixture(
    bits: u8,
) -> Result<LoweredByteFixture, String> {
    let module = signed_byte_truth_module(bits);
    validate_module(&module)
        .map_err(|error| format!("admit signed-byte truth: {error:?}"))?;
    let encoded = canonical_bytes(&module)
        .map_err(|error| format!("encode signed-byte truth IR: {error:?}"))?;
    let restored = canonical_module(&encoded)
        .map_err(|error| format!("restore signed-byte truth IR: {error:?}"))?;
    if restored != module {
        return Err(String::from("signed-byte typed IR drifted"));
    }
    let projection = project_typed_ir(&restored)?;
    let target = lower_typed_ir(&projection)
        .map_err(|error| format!("lower signed-byte truth: {error:?}"))?;
    assert_program_provenance(&restored, &target)?;
    Ok((target, projection))
}

fn assert_signed_byte_truth_checkpoint(
    bits: u8,
    target: &ternary_lowering::TernaryProgram,
) -> Result<Vec<u8>, String> {
    let operations = &target
        .functions
        .first()
        .ok_or_else(|| String::from("signed-byte truth target missing"))?
        .operations;
    let expected = [
        TernaryOperation::MaterializeI8 {
            result: 0,
            scalar: ternary_lowering::TernaryU8Scalar::from_bits(bits),
            span: output_span(fixture_span(0, 1)),
        },
        TernaryOperation::I8ToBool {
            result: 1,
            value: 0,
            span: output_span(fixture_span(1, 2)),
        },
        TernaryOperation::ReturnBool {
            span: output_span(fixture_span(2, 3)),
            value: 1,
        },
    ];
    if operations.as_slice() != expected {
        return Err(String::from("signed-byte truth SSA drifted"));
    }
    let wire = canonical_ternary_bytes(target)
        .map_err(|error| format!("encode signed-byte truth: {error:?}"))?;
    if !wire.windows(5).any(|part| part == [50, 0, 0, 0, 0])
        || !wire.windows(5).any(|part| part == [52, 1, 0, 0, 0])
        || canonical_ternary_program(&wire) != Ok(target.clone())
    {
        return Err(String::from("signed-byte truth canonical drifted"));
    }
    Ok(wire)
}

#[test]
fn typed_signed_byte_truth_preserves_boolean_ssa() -> Result<(), String> {
    for bits in u8::MIN..=u8::MAX {
        let (target, input) = lowered_signed_byte_truth_fixture(bits)?;
        if input.functions.first().map(|function| function.return_kind)
            != Some(InputScalarType::Bool)
        {
            return Err(String::from("signed-byte truth return kind drifted"));
        }
        let _wire = assert_signed_byte_truth_checkpoint(bits, &target)?;
    }
    Ok(())
}

fn reject_signed_byte_truth_wire_forgery(
    bits: u8,
    target: &ternary_lowering::TernaryProgram,
) -> Result<(), String> {
    let wire = assert_signed_byte_truth_checkpoint(bits, target)?;
    let failure = TernaryProgramCodecError::Validation(
        TernaryProgramValidationError::SsaValue,
    );
    for (tag, replacement, expected) in [
        (50u8, 8u8, failure),
        (52, 47, failure),
        (52, 45, failure),
        (52, 84, TernaryProgramCodecError::UnknownTag),
    ] {
        assert_signed_byte_forged_tag_rejected(
            &wire,
            tag,
            replacement,
            expected,
        )?;
    }
    Ok(())
}

#[test]
fn signed_byte_truth_inspector_and_crash_retain_signed_source()
-> Result<(), String> {
    let previous = lowered_return_fixture()?;
    for (bits, label) in [
        (0u8, "signed-truth-zero"),
        (0x7f, "signed-truth-positive"),
        (0x80, "signed-truth-negative"),
        (u8::MAX, "signed-truth-minus-one"),
    ] {
        let (target, projection) = lowered_signed_byte_truth_fixture(bits)?;
        let _wire = assert_signed_byte_truth_checkpoint(bits, &target)?;
        assert_boolean_inspector_convergence(label, &target, &projection)?;
        assert_boolean_crash_generation(&previous, &target)?;
    }
    Ok(())
}

#[test]
fn signed_byte_truth_inspector_rejects_cross_signedness() -> Result<(), String>
{
    let (target, _projection) = lowered_signed_byte_truth_fixture(0x80)?;
    for (label, tags) in [
        ("forged-signed-truth-materialize", (50u8, 0u32, 8u8)),
        ("forged-signed-truth-unsigned", (52, 1, 47)),
        ("forged-signed-truth-future", (52, 1, 84)),
    ] {
        assert_boolean_progress_tag_rejected(label, &target, tags)?;
    }
    Ok(())
}

fn reject_signed_byte_truth_projection(
    projection: &TypedIrInput,
    variation: u8,
) -> Result<(), String> {
    let mut forged = projection.clone();
    let Some(InputInstruction::IntegerToBool {
        result, type_kind, value, ..
    }) = forged
        .functions
        .first_mut()
        .and_then(|function| function.blocks.first_mut())
        .and_then(|block| block.instructions.get_mut(1))
    else {
        return Err(String::from("signed-byte truth projection absent"));
    };
    match variation {
        0 => *type_kind = InputScalarType::I32,
        1 => *value = 99,
        2 => *result = 0,
        _ => return Err(String::from("invalid truth projection variation")),
    }
    let expected = if variation == 2 {
        TernaryLoweringError::InvalidProjection
    } else {
        TernaryLoweringError::UnsupportedInstruction
    };
    if lower_typed_ir(&forged) != Err(expected) {
        return Err(format!(
            "forged signed truth projection {variation} admitted"
        ));
    }
    Ok(())
}

#[test]
fn signed_byte_truth_projection_rejects_wrong_type_and_undefined_ssa()
-> Result<(), String> {
    let (_target, projection) = lowered_signed_byte_truth_fixture(u8::MAX)?;
    for variation in 0u8..3 {
        reject_signed_byte_truth_projection(&projection, variation)?;
    }
    Ok(())
}

#[test]
fn signed_byte_truth_rejects_unsigned_retags_and_unknown_opcode()
-> Result<(), String> {
    for bits in [0u8, 0x7f, 0x80, u8::MAX] {
        let (target, _input) = lowered_signed_byte_truth_fixture(bits)?;
        reject_signed_byte_truth_wire_forgery(bits, &target)?;
    }
    Ok(())
}

fn assert_signed_byte_extension_checkpoint(
    bits: u8,
    target: &ternary_lowering::TernaryProgram,
) -> Result<Vec<u8>, String> {
    let operations = &target
        .functions
        .first()
        .ok_or_else(|| String::from("signed-byte target missing"))?
        .operations;
    let expected = [
        TernaryOperation::MaterializeI8 {
            result: 0,
            scalar: ternary_lowering::TernaryU8Scalar::from_bits(bits),
            span: output_span(fixture_span(0, 1)),
        },
        TernaryOperation::SignExtendI8ToI32 {
            result: 1,
            value: 0,
            span: output_span(fixture_span(1, 2)),
        },
        TernaryOperation::Return {
            span: output_span(fixture_span(2, 3)),
            value: 1,
        },
    ];
    if operations.as_slice() != expected {
        return Err(String::from(
            "signed-byte SSA or source provenance drifted",
        ));
    }
    let wire = canonical_ternary_bytes(target)
        .map_err(|error| format!("encode signed-byte target: {error:?}"))?;
    if !wire.windows(5).any(|part| part == [50, 0, 0, 0, 0])
        || !wire.windows(5).any(|part| part == [51, 1, 0, 0, 0])
        || canonical_ternary_program(&wire) != Ok(target.clone())
    {
        return Err(String::from("signed-byte canonical wire drifted"));
    }
    Ok(wire)
}

fn assert_signed_byte_forged_tag_rejected(
    wire: &[u8],
    tag: u8,
    replacement: u8,
    expected: TernaryProgramCodecError,
) -> Result<(), String> {
    let needle = [tag, u8::from(tag == 51 || tag == 52), 0, 0, 0];
    let offset = wire
        .windows(needle.len())
        .position(|part| part == needle)
        .ok_or_else(|| format!("signed-byte tag {tag} absent"))?;
    let mut forged = wire.to_vec();
    *forged
        .get_mut(offset)
        .ok_or_else(|| String::from("signed-byte tag offset absent"))? =
        replacement;
    if canonical_ternary_program(&forged) != Err(expected) {
        return Err(format!("signed-byte tag {tag}->{replacement} admitted"));
    }
    Ok(())
}

fn assert_signed_byte_projection_rejected(
    projection: &TypedIrInput,
    variation: u8,
) -> Result<(), String> {
    let mut forged = projection.clone();
    let instructions = &mut forged
        .functions
        .first_mut()
        .and_then(|function| function.blocks.first_mut())
        .ok_or_else(|| String::from("signed-byte block missing"))?
        .instructions;
    if variation == 0 {
        let Some(InputInstruction::ConstantInteger { type_kind, .. }) =
            instructions.first_mut()
        else {
            return Err(String::from("signed-byte constant missing"));
        };
        *type_kind = InputScalarType::U8;
    } else {
        let Some(InputInstruction::SignExtendI8ToI32 {
            result,
            value,
            type_kind,
            ..
        }) = instructions.get_mut(1)
        else {
            return Err(String::from("signed-byte cast missing"));
        };
        match variation {
            1 => *type_kind = InputScalarType::U32,
            2 => *value = 99,
            3 => *result = 0,
            _ => return Err(String::from("unknown sign extension forgery")),
        }
    }
    let expected = if variation == 3 {
        TernaryLoweringError::InvalidProjection
    } else {
        TernaryLoweringError::UnsupportedInstruction
    };
    if lower_typed_ir(&forged) != Err(expected) {
        return Err(format!(
            "signed-byte projection forgery {variation} admitted"
        ));
    }
    Ok(())
}

#[test]
fn signed_byte_rejects_cross_width_tags_and_ssa() -> Result<(), String> {
    let failure = TernaryProgramCodecError::Validation(
        TernaryProgramValidationError::SsaValue,
    );
    for bits in [0u8, 1, 0x7f, 0x80, u8::MAX] {
        let (target, projection) = lowered_signed_byte_extension_fixture(bits)?;
        let wire = assert_signed_byte_extension_checkpoint(bits, &target)?;
        for (tag, replacement, expected) in [
            (50u8, 8u8, failure),
            (51, 16, failure),
            (51, 17, failure),
            (51, 84, TernaryProgramCodecError::UnknownTag),
        ] {
            assert_signed_byte_forged_tag_rejected(
                &wire,
                tag,
                replacement,
                expected,
            )?;
        }
        for variation in 0u8..4 {
            assert_signed_byte_projection_rejected(&projection, variation)?;
        }
    }
    Ok(())
}

#[test]
fn signed_byte_extension_inspector_and_crash_restore_signed_ssa()
-> Result<(), String> {
    let previous = lowered_return_fixture()?;
    for (bits, label) in [
        (0u8, "signed-byte-zero"),
        (1, "signed-byte-one"),
        (0x7f, "signed-byte-maximum-positive"),
        (0x80, "signed-byte-minimum-negative"),
        (u8::MAX, "signed-byte-minus-one"),
    ] {
        let (target, projection) = lowered_signed_byte_extension_fixture(bits)?;
        let _wire = assert_signed_byte_extension_checkpoint(bits, &target)?;
        assert_boolean_inspector_convergence(label, &target, &projection)?;
        assert_boolean_crash_generation(&previous, &target)?;
    }
    Ok(())
}

#[test]
fn signed_byte_extension_inspector_rejects_cross_kind_tags()
-> Result<(), String> {
    let (target, _projection) = lowered_signed_byte_extension_fixture(0x80)?;
    assert_boolean_progress_tag_rejected(
        "signed-byte-forged-unsigned",
        &target,
        (50, 0, 8),
    )?;
    assert_boolean_progress_tag_rejected(
        "signed-byte-forged-zero-extend",
        &target,
        (51, 1, 16),
    )?;
    assert_boolean_progress_tag_rejected(
        "signed-byte-unknown-extension",
        &target,
        (51, 1, 84),
    )?;
    Ok(())
}

#[test]
fn typed_signed_byte_extension_keeps_exact_two_complement_bits()
-> Result<(), String> {
    for bits in u8::MIN..=u8::MAX {
        let (target, projection) = lowered_signed_byte_extension_fixture(bits)?;
        if projection
            .functions
            .first()
            .map(|function| function.return_kind)
            != Some(InputScalarType::I32)
        {
            return Err(String::from("signed-byte return type drifted"));
        }
        let _wire = assert_signed_byte_extension_checkpoint(bits, &target)?;
    }
    Ok(())
}

fn lowered_boolean_roundtrip_fixture(
    bit: u8,
) -> Result<LoweredByteFixture, String> {
    let module = boolean_roundtrip_module(bit);
    validate_module(&module)
        .map_err(|error| format!("admit Boolean roundtrip: {error:?}"))?;
    let typed = canonical_bytes(&module)
        .map_err(|error| format!("encode Boolean roundtrip IR: {error:?}"))?;
    let restored = canonical_module(&typed)
        .map_err(|error| format!("restore Boolean roundtrip IR: {error:?}"))?;
    if restored != module {
        return Err(String::from("Boolean roundtrip typed IR drifted"));
    }
    let projection = project_typed_ir(&restored)?;
    let target = lower_typed_ir(&projection)
        .map_err(|error| format!("lower Boolean roundtrip: {error:?}"))?;
    assert_program_provenance(&restored, &target)?;
    Ok((target, projection))
}

fn assert_boolean_roundtrip_state(
    bit: u8,
    target: &ternary_lowering::TernaryProgram,
) -> Result<Vec<u8>, String> {
    let operations = &target
        .functions
        .first()
        .ok_or_else(|| String::from("Boolean roundtrip target absent"))?
        .operations;
    let expected = [
        TernaryOperation::MaterializeBool {
            result: 0,
            value: bit == 1,
            span: output_span(fixture_span(0, 1)),
        },
        TernaryOperation::BoolToI32 {
            result: 1,
            value: 0,
            span: output_span(fixture_span(1, 2)),
        },
        TernaryOperation::TruncateI32ToU8 {
            result: 2,
            value: 1,
            span: output_span(fixture_span(2, 3)),
        },
        TernaryOperation::U8ToBool {
            result: 3,
            value: 2,
            span: output_span(fixture_span(3, 4)),
        },
        TernaryOperation::BoolToI32 {
            result: 4,
            value: 3,
            span: output_span(fixture_span(4, 5)),
        },
        TernaryOperation::Return {
            value: 4,
            span: output_span(fixture_span(5, 6)),
        },
    ];
    if operations.as_slice() != expected {
        return Err(String::from("Boolean roundtrip SSA/provenance drifted"));
    }
    let wire = canonical_ternary_bytes(target).map_err(|error| {
        format!("encode Boolean roundtrip target: {error:?}")
    })?;
    if canonical_ternary_program(&wire) != Ok(target.clone()) {
        return Err(String::from("Boolean roundtrip checkpoint drifted"));
    }
    Ok(wire)
}

fn reject_boolean_roundtrip_cast_forgery(
    wire: &[u8],
    cast: (u8, u32, u8),
) -> Result<(), String> {
    let (tag, result, forged_tag) = cast;
    let mut pattern = vec![tag];
    pattern.extend_from_slice(&result.to_le_bytes());
    let offset = wire
        .windows(pattern.len())
        .position(|window| window == pattern)
        .ok_or_else(|| String::from("Boolean cast opcode missing"))?;
    let mut forged = wire.to_vec();
    *forged
        .get_mut(offset)
        .ok_or_else(|| String::from("Boolean cast tag absent"))? = forged_tag;
    if canonical_ternary_program(&forged)
        != Err(TernaryProgramCodecError::Validation(
            TernaryProgramValidationError::SsaValue,
        ))
    {
        return Err(format!(
            "forged Boolean cast {tag} -> {forged_tag} admitted"
        ));
    }
    Ok(())
}

#[test]
fn boolean_constant_conversion_chain_rejects_cross_width_retags()
-> Result<(), String> {
    for bit in [0u8, 1] {
        let (target, _projection) = lowered_boolean_roundtrip_fixture(bit)?;
        let wire = assert_boolean_roundtrip_state(bit, &target)?;
        for cast in [(5u8, 2u32, 15u8), (47, 3, 45), (44, 4, 33)] {
            reject_boolean_roundtrip_cast_forgery(&wire, cast)?;
        }
        let prefix = [47, 3, 0, 0, 0];
        let offset = wire
            .windows(prefix.len())
            .position(|window| window == prefix)
            .ok_or_else(|| String::from("roundtrip truth conversion absent"))?;
        let mut undefined = wire;
        *undefined
            .get_mut(offset.saturating_add(29))
            .ok_or_else(|| String::from("roundtrip byte source absent"))? = 99;
        if canonical_ternary_program(&undefined)
            != Err(TernaryProgramCodecError::Validation(
                TernaryProgramValidationError::SsaValue,
            ))
        {
            return Err(String::from("undefined Boolean chain byte admitted"));
        }
        assert_boolean_progress_tag_rejected(
            "forged-roundtrip-byte-conversion",
            &target,
            (47, 3, 45),
        )?;
    }
    Ok(())
}

#[test]
fn boolean_constant_conversion_chain_preserves_five_distinct_ssa()
-> Result<(), String> {
    let previous = lowered_return_fixture()?;
    for bit in [0u8, 1] {
        let (target, projection) = lowered_boolean_roundtrip_fixture(bit)?;
        let _wire = assert_boolean_roundtrip_state(bit, &target)?;
        let label = if bit == 0 {
            "false-byte-boolean-roundtrip"
        } else {
            "true-byte-boolean-roundtrip"
        };
        assert_boolean_inspector_convergence(label, &target, &projection)?;
        assert_boolean_crash_generation(&previous, &target)?;
    }
    Ok(())
}

fn lowered_boolean_constant_fixture(
    bit: u8,
    promoted: bool,
) -> Result<LoweredByteFixture, String> {
    let module = boolean_constant_module(bit, promoted);
    validate_module(&module)
        .map_err(|error| format!("admit Boolean constant: {error:?}"))?;
    let encoded = canonical_bytes(&module)
        .map_err(|error| format!("encode Boolean constant IR: {error:?}"))?;
    let restored = canonical_module(&encoded)
        .map_err(|error| format!("restore Boolean constant IR: {error:?}"))?;
    if restored != module {
        return Err(String::from("Boolean constant typed IR drifted"));
    }
    let projection = project_typed_ir(&restored)?;
    let target = lower_typed_ir(&projection)
        .map_err(|error| format!("lower Boolean constant: {error:?}"))?;
    assert_program_provenance(&restored, &target)?;
    Ok((target, projection))
}

fn assert_boolean_constant_checkpoint(
    bit: u8,
    promoted: bool,
    target: &ternary_lowering::TernaryProgram,
) -> Result<Vec<u8>, String> {
    let operations = &target
        .functions
        .first()
        .ok_or_else(|| String::from("Boolean constant target absent"))?
        .operations;
    let first = TernaryOperation::MaterializeBool {
        result: 0,
        value: bit == 1,
        span: output_span(fixture_span(0, 1)),
    };
    let last = if promoted {
        TernaryOperation::Return {
            span: output_span(fixture_span(2, 3)),
            value: 1,
        }
    } else {
        TernaryOperation::ReturnBool {
            span: output_span(fixture_span(1, 2)),
            value: 0,
        }
    };
    if operations.first() != Some(&first) || operations.last() != Some(&last) {
        return Err(String::from("Boolean constant target SSA drifted"));
    }
    if promoted
        && operations.get(1)
            != Some(&TernaryOperation::BoolToI32 {
                result: 1,
                span: output_span(fixture_span(1, 2)),
                value: 0,
            })
    {
        return Err(String::from("Boolean constant promotion drifted"));
    }
    let wire = canonical_ternary_bytes(target).map_err(|error| {
        format!("encode Boolean constant target: {error:?}")
    })?;
    if !wire.windows(6).any(|chunk| chunk == [48, 0, 0, 0, 0, bit])
        || canonical_ternary_program(&wire) != Ok(target.clone())
    {
        return Err(String::from("Boolean constant canonical wire drifted"));
    }
    Ok(wire)
}

fn reject_boolean_constant_wire_forgery(
    bit: u8,
    promoted: bool,
    target: &ternary_lowering::TernaryProgram,
) -> Result<(), String> {
    let wire = assert_boolean_constant_checkpoint(bit, promoted, target)?;
    let offset = wire
        .windows(6)
        .position(|chunk| chunk == [48, 0, 0, 0, 0, bit])
        .ok_or_else(|| String::from("Boolean materialization absent"))?;
    let mut malformed_scalar = wire.clone();
    *malformed_scalar
        .get_mut(offset.saturating_add(5))
        .ok_or_else(|| String::from("Boolean scalar byte absent"))? = 2;
    if canonical_ternary_program(&malformed_scalar)
        != Err(TernaryProgramCodecError::InvalidScalar)
    {
        return Err(String::from("noncanonical Boolean scalar admitted"));
    }
    let mut unknown = wire.clone();
    *unknown
        .get_mut(offset)
        .ok_or_else(|| String::from("Boolean opcode absent"))? = 84;
    if canonical_ternary_program(&unknown)
        != Err(TernaryProgramCodecError::UnknownTag)
    {
        return Err(String::from("unknown Boolean scalar tag admitted"));
    }
    let mut undefined = wire.clone();
    *undefined
        .get_mut(offset.saturating_add(1))
        .ok_or_else(|| String::from("Boolean result SSA absent"))? = 7;
    if canonical_ternary_program(&undefined)
        != Err(TernaryProgramCodecError::Validation(
            TernaryProgramValidationError::SsaValue,
        ))
    {
        return Err(String::from("undefined Boolean return SSA admitted"));
    }
    let mut wrong_return = wire;
    let ret_offset = wrong_return
        .len()
        .checked_sub(29)
        .ok_or_else(|| String::from("Boolean return record absent"))?;
    *wrong_return
        .get_mut(ret_offset)
        .ok_or_else(|| String::from("Boolean return tag absent"))? = 11;
    if canonical_ternary_program(&wrong_return)
        != Err(TernaryProgramCodecError::Validation(
            TernaryProgramValidationError::SsaValue,
        ))
    {
        return Err(String::from("wrong Boolean return kind admitted"));
    }
    Ok(())
}

fn check_canonical_boolean_digit(
    digit: u8,
    wire: &[u8],
    offset: usize,
) -> Result<(), String> {
    let mut forged = wire.to_vec();
    *forged
        .get_mut(offset.saturating_add(5))
        .ok_or_else(|| String::from("Boolean digit absent"))? = digit;
    let restored = canonical_ternary_program(&forged);
    if digit > 1 {
        if restored != Err(TernaryProgramCodecError::InvalidScalar) {
            return Err(format!("non-Boolean digit {digit} admitted"));
        }
        return Ok(());
    }
    let recovered = restored.map_err(|error| {
        format!("Boolean digit {digit} rejected: {error:?}")
    })?;
    let expected = TernaryOperation::MaterializeBool {
        result: 0,
        value: digit == 1,
        span: output_span(fixture_span(0, 1)),
    };
    if recovered
        .functions
        .first()
        .and_then(|function| function.operations.first())
        != Some(&expected)
        || canonical_ternary_bytes(&recovered) != Ok(forged)
    {
        return Err(format!("Boolean digit {digit} changed identity"));
    }
    Ok(())
}

#[test]
fn boolean_checkpoint_decoder_exhaustively_checks_all_encoded_digits()
-> Result<(), String> {
    for bit in [0u8, 1] {
        let (target, _projection) =
            lowered_boolean_constant_fixture(bit, false)?;
        let wire = assert_boolean_constant_checkpoint(bit, false, &target)?;
        let offset = wire
            .windows(6)
            .position(|chunk| chunk == [48, 0, 0, 0, 0, bit])
            .ok_or_else(|| String::from("Boolean constant record absent"))?;
        for digit in u8::MIN..=u8::MAX {
            check_canonical_boolean_digit(digit, &wire, offset)?;
        }
    }
    Ok(())
}

#[test]
fn boolean_constant_codec_rejects_noncanonical_value_and_ssa()
-> Result<(), String> {
    for bit in [0u8, 1] {
        for promoted in [false, true] {
            let (target, _input) =
                lowered_boolean_constant_fixture(bit, promoted)?;
            reject_boolean_constant_wire_forgery(bit, promoted, &target)?;
        }
    }
    Ok(())
}

fn reject_boolean_constant_projection_forgery(
    input: &TypedIrInput,
) -> Result<(), String> {
    for variation in 0u8..4u8 {
        let mut forged = input.clone();
        let constant = forged
            .functions
            .first_mut()
            .and_then(|function| function.blocks.first_mut())
            .and_then(|block| block.instructions.first_mut())
            .ok_or_else(|| String::from("projected Boolean constant absent"))?;
        let InputInstruction::ConstantInteger {
            bit_width,
            little_endian,
            result,
            type_kind,
            ..
        } = constant
        else {
            return Err(String::from("projected Boolean instruction drifted"));
        };
        match variation {
            0 => *bit_width = 8,
            1 => *little_endian = vec![2],
            2 => *type_kind = InputScalarType::U8,
            3 => *result = 99,
            _ => return Err(String::from("unknown Boolean projection case")),
        }
        let expected = if variation == 3 {
            TernaryLoweringError::UnsupportedTerminator
        } else {
            TernaryLoweringError::UnsupportedInstruction
        };
        if lower_typed_ir(&forged) != Err(expected) {
            return Err(format!(
                "Boolean constant forgery {variation} admitted"
            ));
        }
    }
    Ok(())
}

#[test]
fn boolean_constant_projection_rejects_wrong_bits_and_category()
-> Result<(), String> {
    let (_target, input) = lowered_boolean_constant_fixture(1, false)?;
    reject_boolean_constant_projection_forgery(&input)?;
    let forged_typed = boolean_constant_module(2, false);
    if validate_module(&forged_typed).is_ok() {
        return Err(String::from("typed Boolean bit pattern 2 admitted"));
    }
    Ok(())
}

#[test]
fn typed_boolean_constants_round_trip_without_integer_promotion()
-> Result<(), String> {
    for bit in [0u8, 1] {
        for promoted in [false, true] {
            let (target, input) =
                lowered_boolean_constant_fixture(bit, promoted)?;
            let expected_type = if promoted {
                InputScalarType::I32
            } else {
                InputScalarType::Bool
            };
            if input.functions.first().map(|function| function.return_kind)
                != Some(expected_type)
            {
                return Err(String::from(
                    "Boolean constant return type drifted",
                ));
            }
            let _wire =
                assert_boolean_constant_checkpoint(bit, promoted, &target)?;
        }
    }
    Ok(())
}

fn lowered_byte_to_bool_fixture(
    source: Option<u8>,
) -> Result<LoweredByteFixture, String> {
    let module = byte_to_bool_module(source);
    validate_module(&module)
        .map_err(|error| format!("admit byte truth: {error:?}"))?;
    let canonical = canonical_bytes(&module)
        .map_err(|error| format!("encode byte truth: {error:?}"))?;
    let restored = canonical_module(&canonical)
        .map_err(|error| format!("decode byte truth: {error:?}"))?;
    if restored != module {
        return Err(String::from("byte truth typed-IR drifted"));
    }
    let input = project_typed_ir(&restored)?;
    let target = lower_typed_ir(&input)
        .map_err(|error| format!("lower byte truth: {error:?}"))?;
    assert_program_provenance(&restored, &target)?;
    Ok((target, input))
}

fn assert_byte_to_bool_checkpoint(
    target: &ternary_lowering::TernaryProgram,
    source: Option<u8>,
) -> Result<Vec<u8>, String> {
    let operations = &target
        .functions
        .first()
        .ok_or_else(|| String::from("byte truth target absent"))?
        .operations;
    let first = source.map_or(
        TernaryOperation::ByteInput {
            result: 0,
            span: output_span(fixture_span(0, 1)),
        },
        |byte| TernaryOperation::MaterializeU8 {
            result: 0,
            scalar: ternary_lowering::TernaryU8Scalar::from_bits(byte),
            span: output_span(fixture_span(0, 1)),
        },
    );
    let expected = [
        first,
        TernaryOperation::U8ToBool {
            result: 1,
            span: output_span(fixture_span(1, 2)),
            value: 0,
        },
        TernaryOperation::ReturnBool {
            span: output_span(fixture_span(2, 3)),
            value: 1,
        },
    ];
    if operations.as_slice() != expected {
        return Err(String::from("byte truth operations drifted"));
    }
    let bytes = canonical_ternary_bytes(target)
        .map_err(|error| format!("encode byte truth target: {error:?}"))?;
    if !bytes.windows(5).any(|part| part == [47, 1, 0, 0, 0])
        || canonical_ternary_program(&bytes) != Ok(target.clone())
    {
        return Err(String::from("byte truth canonical tag drifted"));
    }
    Ok(bytes)
}

fn reject_byte_truth_wire_forgery(
    source: Option<u8>,
    target: &ternary_lowering::TernaryProgram,
) -> Result<(), String> {
    let bytes = assert_byte_to_bool_checkpoint(target, source)?;
    let offset = bytes
        .windows(5)
        .position(|part| part == [47, 1, 0, 0, 0])
        .ok_or_else(|| String::from("byte truth opcode absent"))?;
    for (delta, replacement) in [(0usize, 45u8), (0, 46), (1, 0), (29, 99)] {
        let mut forged = bytes.clone();
        *forged
            .get_mut(offset.saturating_add(delta))
            .ok_or_else(|| String::from("byte truth field missing"))? =
            replacement;
        if canonical_ternary_program(&forged)
            != Err(TernaryProgramCodecError::Validation(
                TernaryProgramValidationError::SsaValue,
            ))
        {
            return Err(format!("forged byte truth field {delta} admitted"));
        }
    }
    let mut future = bytes;
    *future
        .get_mut(offset)
        .ok_or_else(|| String::from("byte truth tag missing"))? = 84;
    if canonical_ternary_program(&future)
        != Err(TernaryProgramCodecError::UnknownTag)
    {
        return Err(String::from("next unknown byte truth tag admitted"));
    }
    Ok(())
}

fn reject_byte_truth_projection_forgery(
    input: &TypedIrInput,
) -> Result<(), String> {
    for variation in 0u8..3u8 {
        let mut forged = input.clone();
        let cast = forged
            .functions
            .first_mut()
            .and_then(|function| function.blocks.first_mut())
            .and_then(|block| block.instructions.get_mut(1))
            .ok_or_else(|| String::from("byte truth cast missing"))?;
        let InputInstruction::IntegerToBool {
            result, type_kind, value, ..
        } = cast
        else {
            return Err(String::from("byte truth projection changed"));
        };
        match variation {
            0 => *type_kind = InputScalarType::U8,
            1 => *value = 99,
            2 => *result = 0,
            _ => return Err(String::from("unknown byte truth forgery")),
        }
        let expected = if variation == 2 {
            TernaryLoweringError::InvalidProjection
        } else {
            TernaryLoweringError::UnsupportedInstruction
        };
        if lower_typed_ir(&forged) != Err(expected) {
            return Err(format!(
                "forged byte truth projection {variation} admitted"
            ));
        }
    }
    Ok(())
}

#[test]
fn byte_truth_rejects_cross_width_tags_and_forged_ssa() -> Result<(), String> {
    for source in [Some(0u8), Some(u8::MAX), None] {
        let (target, input) = lowered_byte_to_bool_fixture(source)?;
        reject_byte_truth_wire_forgery(source, &target)?;
        reject_byte_truth_projection_forgery(&input)?;
    }
    Ok(())
}

#[test]
fn typed_byte_to_bool_keeps_constant_and_input_byte_truth_symbolic()
-> Result<(), String> {
    for source in [
        Some(0u8),
        Some(1),
        Some(0x7f),
        Some(0x80),
        Some(u8::MAX),
        None,
    ] {
        let (target, input) = lowered_byte_to_bool_fixture(source)?;
        if input.functions.first().map(|func| func.return_kind)
            != Some(InputScalarType::Bool)
        {
            return Err(String::from("byte truth return kind drifted"));
        }
        let _wire = assert_byte_to_bool_checkpoint(&target, source)?;
    }
    Ok(())
}

fn lowered_integer_to_bool_fixture(
    signed: bool,
    bits: u32,
) -> Result<LoweredByteFixture, String> {
    let module = integer_to_bool_module(signed, bits);
    validate_module(&module)
        .map_err(|error| format!("admit integer-to-bool: {error:?}"))?;
    let typed = canonical_bytes(&module)
        .map_err(|error| format!("encode integer-to-bool: {error:?}"))?;
    let restored = canonical_module(&typed)
        .map_err(|error| format!("restore integer-to-bool: {error:?}"))?;
    if restored != module {
        return Err(String::from("integer-to-bool typed IR drifted"));
    }
    let input = project_typed_ir(&restored)?;
    let target = lower_typed_ir(&input)
        .map_err(|error| format!("lower integer-to-bool: {error:?}"))?;
    assert_program_provenance(&restored, &target)?;
    Ok((target, input))
}

fn assert_integer_to_bool_checkpoint(
    signed: bool,
    bits: u32,
    target: &ternary_lowering::TernaryProgram,
) -> Result<Vec<u8>, String> {
    let operations = &target
        .functions
        .first()
        .ok_or_else(|| String::from("integer-to-bool function missing"))?
        .operations;
    let scalar = ternary_lowering::TernaryI32Scalar::from_bits(bits);
    let span = output_span(fixture_span(1, 2));
    let first = if signed {
        TernaryOperation::MaterializeI32 {
            result: 0,
            span: output_span(fixture_span(0, 1)),
            scalar,
        }
    } else {
        TernaryOperation::MaterializeU32 {
            result: 0,
            span: output_span(fixture_span(0, 1)),
            scalar,
        }
    };
    let (second, tag) = if signed {
        (
            TernaryOperation::I32ToBool {
                result: 1,
                span,
                value: 0,
            },
            45u8,
        )
    } else {
        (
            TernaryOperation::U32ToBool {
                result: 1,
                span,
                value: 0,
            },
            46u8,
        )
    };
    let last = TernaryOperation::ReturnBool {
        span: output_span(fixture_span(2, 3)),
        value: 1,
    };
    if operations.as_slice() != [first, second, last] {
        return Err(String::from("integer-to-bool SSA/provenance drifted"));
    }
    let wire = canonical_ternary_bytes(target)
        .map_err(|error| format!("encode integer-to-bool target: {error:?}"))?;
    if !wire.windows(5).any(|part| part == [tag, 1, 0, 0, 0])
        || canonical_ternary_program(&wire) != Ok(target.clone())
    {
        return Err(String::from("integer-to-bool canonical wire drifted"));
    }
    Ok(wire)
}

fn reject_integer_to_bool_wire_forgery(
    signed: bool,
    wire: Vec<u8>,
) -> Result<(), String> {
    let tag = if signed {
        45u8
    } else {
        46u8
    };
    let opposite = if signed {
        46u8
    } else {
        45u8
    };
    let offset = wire
        .windows(5)
        .position(|part| part == [tag, 1, 0, 0, 0])
        .ok_or_else(|| String::from("integer-to-bool tag missing"))?;
    for (delta, replacement) in [(0usize, opposite), (1, 0), (29, 1)] {
        let mut forged = wire.clone();
        *forged
            .get_mut(offset.saturating_add(delta))
            .ok_or_else(|| String::from("cast field missing"))? = replacement;
        if canonical_ternary_program(&forged)
            != Err(TernaryProgramCodecError::Validation(
                TernaryProgramValidationError::SsaValue,
            ))
        {
            return Err(format!("forged integer-to-bool {delta} admitted"));
        }
    }
    let mut future = wire;
    *future
        .get_mut(offset)
        .ok_or_else(|| String::from("integer-to-bool opcode missing"))? = 84;
    if canonical_ternary_program(&future)
        != Err(TernaryProgramCodecError::UnknownTag)
    {
        return Err(String::from("future integer-to-bool tag admitted"));
    }
    Ok(())
}

fn reject_integer_to_bool_projection_forgery(
    input: &TypedIrInput,
) -> Result<(), String> {
    for variation in 0u8..3u8 {
        let mut forged = input.clone();
        let cast = forged
            .functions
            .first_mut()
            .and_then(|function| function.blocks.first_mut())
            .and_then(|block| block.instructions.get_mut(1))
            .ok_or_else(|| String::from("integer-to-bool input absent"))?;
        let InputInstruction::IntegerToBool {
            result, type_kind, value, ..
        } = cast
        else {
            return Err(String::from("integer-to-bool input drifted"));
        };
        match variation {
            0 => *type_kind = InputScalarType::I32,
            1 => *value = 20,
            2 => *result = 0,
            _ => return Err(String::from("unexpected cast forgery")),
        }
        let expected = if variation == 2 {
            TernaryLoweringError::InvalidProjection
        } else {
            TernaryLoweringError::UnsupportedInstruction
        };
        if lower_typed_ir(&forged) != Err(expected) {
            return Err(format!(
                "integer-to-bool projection {variation} admitted"
            ));
        }
    }
    Ok(())
}

#[test]
fn integer_to_bool_rejects_wrong_signedness_and_undefined_ssa()
-> Result<(), String> {
    for signed in [true, false] {
        let (target, input) =
            lowered_integer_to_bool_fixture(signed, u32::MAX)?;
        let wire =
            assert_integer_to_bool_checkpoint(signed, u32::MAX, &target)?;
        reject_integer_to_bool_wire_forgery(signed, wire)?;
        reject_integer_to_bool_projection_forgery(&input)?;
    }
    Ok(())
}

#[test]
fn typed_integer_to_bool_preserves_nonzero_truth_symbolically()
-> Result<(), String> {
    for signed in [true, false] {
        for bits in [0u32, 1, 0x7fff_ffff, 0x8000_0000, u32::MAX] {
            let (target, input) =
                lowered_integer_to_bool_fixture(signed, bits)?;
            if input.functions.first().map(|func| func.return_kind)
                != Some(InputScalarType::Bool)
            {
                return Err(String::from(
                    "integer-to-bool result kind drifted",
                ));
            }
            let _wire =
                assert_integer_to_bool_checkpoint(signed, bits, &target)?;
        }
    }
    Ok(())
}

fn lowered_bool_to_signed_fixture(
    left: u32,
    right: u32,
) -> Result<LoweredByteFixture, String> {
    let module = bool_to_signed_fixture_module(left, right);
    validate_module(&module)
        .map_err(|error| format!("admit bool-to-signed: {error:?}"))?;
    let typed = canonical_bytes(&module)
        .map_err(|error| format!("encode bool-to-signed: {error:?}"))?;
    let restored = canonical_module(&typed)
        .map_err(|error| format!("restore bool-to-signed: {error:?}"))?;
    if restored != module {
        return Err(String::from("bool-to-signed typed IR drifted"));
    }
    let input = project_typed_ir(&restored)?;
    let target = lower_typed_ir(&input)
        .map_err(|error| format!("lower bool-to-signed: {error:?}"))?;
    assert_program_provenance(&restored, &target)?;
    Ok((target, input))
}

fn assert_bool_to_signed_checkpoint(
    target: &ternary_lowering::TernaryProgram,
) -> Result<Vec<u8>, String> {
    let function = target
        .functions
        .first()
        .ok_or_else(|| String::from("bool-to-signed target missing"))?;
    if function.operations.get(3)
        != Some(&TernaryOperation::BoolToI32 {
            result: 3,
            span: output_span(fixture_span(3, 4)),
            value: 2,
        })
        || function.operations.last()
            != Some(&TernaryOperation::Return {
                span: output_span(fixture_span(4, 5)),
                value: 3,
            })
    {
        return Err(String::from("bool-to-signed SSA/provenance drifted"));
    }
    let bytes = canonical_ternary_bytes(target)
        .map_err(|error| format!("encode bool-to-signed target: {error:?}"))?;
    let tag = [44u8, 3, 0, 0, 0];
    if !bytes.windows(tag.len()).any(|window| window == tag)
        || canonical_ternary_program(&bytes) != Ok(target.clone())
    {
        return Err(String::from("bool-to-signed wire tag drifted"));
    }
    Ok(bytes)
}

#[test]
fn bool_to_signed_lowers_validated_comparison_without_host_evaluation()
-> Result<(), String> {
    for (left, right) in [
        (0u32, 0u32),
        (0, 1),
        (u32::MAX, 0),
        (u32::MAX, u32::MAX),
        (0x8000_0000, u32::MAX),
    ] {
        let (target, input) = lowered_bool_to_signed_fixture(left, right)?;
        if input.functions.first().map(|function| function.return_kind)
            != Some(InputScalarType::I32)
        {
            return Err(String::from("bool-to-signed return type drifted"));
        }
        let _wire = assert_bool_to_signed_checkpoint(&target)?;
    }
    Ok(())
}

#[test]
fn bool_to_signed_rejects_forged_source_type_and_wire_tags()
-> Result<(), String> {
    let (target, input) = lowered_bool_to_signed_fixture(u32::MAX, 0)?;
    let bytes = assert_bool_to_signed_checkpoint(&target)?;
    let offset = bytes
        .windows(5)
        .position(|wire| wire == [44, 3, 0, 0, 0])
        .ok_or_else(|| String::from("bool-to-signed tag missing"))?;
    for (delta, replacement) in [(0usize, 33u8), (29, 0)] {
        let mut forged = bytes.clone();
        *forged
            .get_mut(offset.saturating_add(delta))
            .ok_or_else(|| String::from("bool-to-signed field missing"))? =
            replacement;
        if canonical_ternary_program(&forged)
            != Err(TernaryProgramCodecError::Validation(
                TernaryProgramValidationError::SsaValue,
            ))
        {
            return Err(String::from("forged bool-to-signed target admitted"));
        }
    }
    let mut unknown = bytes;
    *unknown
        .get_mut(offset)
        .ok_or_else(|| String::from("bool-to-signed opcode absent"))? = 84;
    if canonical_ternary_program(&unknown)
        != Err(TernaryProgramCodecError::UnknownTag)
    {
        return Err(String::from("unknown bool-to-signed tag admitted"));
    }
    for variation in 0u8..3u8 {
        let mut forged = input.clone();
        let cast = forged
            .functions
            .first_mut()
            .and_then(|function| function.blocks.first_mut())
            .and_then(|block| block.instructions.get_mut(3))
            .ok_or_else(|| String::from("bool-to-signed projection missing"))?;
        let InputInstruction::BoolToSigned {
            result, type_kind, value, ..
        } = cast
        else {
            return Err(String::from("wrong bool-to-signed projection"));
        };
        match variation {
            0 => *type_kind = InputScalarType::U32,
            1 => *value = 0,
            2 => *result = 2,
            _ => return Err(String::from("unknown bool-to-signed forgery")),
        }
        let expected = if variation == 2 {
            TernaryLoweringError::InvalidProjection
        } else {
            TernaryLoweringError::UnsupportedInstruction
        };
        if lower_typed_ir(&forged) != Err(expected) {
            return Err(format!("bool-to-signed forgery {variation} admitted"));
        }
    }
    Ok(())
}

fn lowered_integer_comparison_fixture(
    case: ComparisonFixture,
) -> Result<LoweredByteFixture, String> {
    let module = integer_comparison_module(case);
    validate_module(&module)
        .map_err(|error| format!("admit integer comparison: {error:?}"))?;
    let typed = canonical_bytes(&module)
        .map_err(|error| format!("encode integer comparison: {error:?}"))?;
    let restored = canonical_module(&typed)
        .map_err(|error| format!("restore integer comparison: {error:?}"))?;
    if restored != module {
        return Err(String::from("typed integer comparison drifted"));
    }
    let input = project_typed_ir(&restored)?;
    let target = lower_typed_ir(&input)
        .map_err(|error| format!("lower integer comparison: {error:?}"))?;
    assert_program_provenance(&restored, &target)?;
    Ok((target, input))
}

fn expected_comparison_operation(
    signed: bool,
    operation: CompareOp,
    result: u32,
) -> Result<ComparisonOperationTag, String> {
    let (left, right, span) = (
        0,
        u32::from(result != 1),
        output_span(fixture_span(result, result.saturating_add(1))),
    );
    Ok(match (signed, operation) {
        (true, CompareOp::Equal) => (
            TernaryOperation::EqualI32 {
                left,
                result,
                right,
                span,
            },
            35,
        ),
        (false, CompareOp::Equal) => (
            TernaryOperation::EqualU32 {
                left,
                result,
                right,
                span,
            },
            36,
        ),
        (true, CompareOp::NotEqual) => (
            TernaryOperation::NotEqualI32 {
                left,
                result,
                right,
                span,
            },
            37,
        ),
        (false, CompareOp::NotEqual) => (
            TernaryOperation::NotEqualU32 {
                left,
                result,
                right,
                span,
            },
            38,
        ),
        (_, _) => return Err(String::from("unsupported comparison fixture")),
    })
}

fn expected_ordered_comparison_operation(
    operation: CompareOp,
    result: u32,
) -> Result<ComparisonOperationTag, String> {
    let left = 0;
    let right = u32::from(result != 1);
    let span = output_span(fixture_span(result, result.saturating_add(1)));
    Ok(match operation {
        CompareOp::LessSigned => (
            TernaryOperation::LessSignedI32 {
                left,
                result,
                right,
                span,
            },
            40,
        ),
        CompareOp::LessSignedEqual => (
            TernaryOperation::LessSignedEqualI32 {
                left,
                result,
                right,
                span,
            },
            41,
        ),
        CompareOp::LessUnsigned => (
            TernaryOperation::LessUnsignedU32 {
                left,
                result,
                right,
                span,
            },
            42,
        ),
        CompareOp::LessUnsignedEqual => (
            TernaryOperation::LessUnsignedEqualU32 {
                left,
                result,
                right,
                span,
            },
            43,
        ),
        CompareOp::Equal
        | CompareOp::NotEqual
        | CompareOp::FloatLess
        | CompareOp::FloatLessEqual => {
            return Err(String::from(
                "unexpected ordered comparison predicate",
            ));
        },
    })
}

fn assert_comparison_checkpoint(
    program: &ternary_lowering::TernaryProgram,
    expected: TernaryOperation,
    tag: u8,
    result: u32,
) -> Result<(), String> {
    let function = program
        .functions
        .first()
        .ok_or_else(|| String::from("comparison function missing"))?;
    if function
        .operations
        .get(usize::try_from(result).unwrap_or_default())
        != Some(&expected)
        || function.operations.last()
            != Some(&TernaryOperation::ReturnBool {
                span: output_span(fixture_span(
                    result.saturating_add(1),
                    result.saturating_add(2),
                )),
                value: result,
            })
    {
        return Err(String::from("comparison SSA or return drifted"));
    }
    let encoded = canonical_ternary_bytes(program)
        .map_err(|error| format!("encode comparison target: {error:?}"))?;
    let left = 0u32.to_le_bytes();
    let result_bytes = result.to_le_bytes();
    let right = u32::from(result != 1).to_le_bytes();
    let pattern = [[tag].as_slice(), &left, &result_bytes, &right].concat();
    if !encoded.windows(pattern.len()).any(|part| part == pattern)
        || canonical_ternary_program(&encoded) != Ok(program.clone())
    {
        return Err(String::from("comparison canonical tag drifted"));
    }
    Ok(())
}

fn assert_comparison_operand_patterns(
    case: ComparisonFixture,
    target: &ternary_lowering::TernaryProgram,
) -> Result<(), String> {
    let function = target
        .functions
        .first()
        .ok_or_else(|| String::from("comparison target absent"))?;
    let first = function.operations.first();
    let matching_first = match first {
        Some(TernaryOperation::MaterializeI32 { scalar, .. })
            if case.signed =>
        {
            scalar.bits() == case.left
        },
        Some(TernaryOperation::MaterializeU32 { scalar, .. })
            if !case.signed =>
        {
            scalar.bits() == case.left
        },
        Some(_) | None => false,
    };
    if !matching_first {
        return Err(String::from("comparison source bits drifted"));
    }
    if !case.alias {
        let second = function.operations.get(1);
        let matching_second = match second {
            Some(TernaryOperation::MaterializeI32 { scalar, .. })
                if case.signed =>
            {
                scalar.bits() == case.right
            },
            Some(TernaryOperation::MaterializeU32 { scalar, .. })
                if !case.signed =>
            {
                scalar.bits() == case.right
            },
            Some(_) | None => false,
        };
        if !matching_second {
            return Err(String::from("comparison right bits drifted"));
        }
    }
    Ok(())
}

fn verify_integer_comparison_case(
    case: ComparisonFixture,
) -> Result<(), String> {
    let (target, input) = lowered_integer_comparison_fixture(case)?;
    if input.functions.first().map(|item| item.return_kind)
        != Some(InputScalarType::Bool)
    {
        return Err(String::from("boolean return kind drifted"));
    }
    assert_comparison_operand_patterns(case, &target)?;
    let result = if case.alias {
        1
    } else {
        2
    };
    let (expected, tag) =
        if matches!(case.operation, CompareOp::Equal | CompareOp::NotEqual) {
            expected_comparison_operation(case.signed, case.operation, result)?
        } else {
            expected_ordered_comparison_operation(case.operation, result)?
        };
    assert_comparison_checkpoint(&target, expected, tag, result)
}

#[test]
fn typed_integer_comparisons_preserve_boolean_ssa_and_wire()
-> Result<(), String> {
    for (signed, operation) in [
        (true, CompareOp::Equal),
        (false, CompareOp::Equal),
        (true, CompareOp::NotEqual),
        (false, CompareOp::NotEqual),
    ] {
        for (left, right, alias) in [
            (0u32, 0u32, false),
            (0, 0, true),
            (0, 1, false),
            (0, 1, true),
            (0x8000_0000, u32::MAX, false),
            (0x8000_0000, u32::MAX, true),
            (0x5555_5555, 0xaaaa_aaaa, false),
            (0x5555_5555, 0xaaaa_aaaa, true),
            (u32::MAX, u32::MAX, false),
            (u32::MAX, u32::MAX, true),
        ] {
            verify_integer_comparison_case(ComparisonFixture {
                alias,
                left,
                operation,
                right,
                signed,
            })?;
        }
    }
    Ok(())
}

#[test]
fn ordered_integer_comparisons_keep_boundary_bits_and_boolean_ssa()
-> Result<(), String> {
    for (signed, operation) in [
        (true, CompareOp::LessSigned),
        (true, CompareOp::LessSignedEqual),
        (false, CompareOp::LessUnsigned),
        (false, CompareOp::LessUnsignedEqual),
    ] {
        for (left, right, alias) in [
            (0u32, 0u32, true),
            (0, 1, false),
            (u32::MAX, 0, false),
            (0x8000_0000, 1, false),
            (0x7fff_ffff, 0x8000_0000, false),
            (0x8000_0000, u32::MAX, false),
            (u32::MAX, u32::MAX, true),
        ] {
            verify_integer_comparison_case(ComparisonFixture {
                alias,
                left,
                operation,
                right,
                signed,
            })?;
        }
    }
    Ok(())
}

fn assert_comparison_forgery(
    signed: bool,
    operation: CompareOp,
) -> Result<(), String> {
    let case = ComparisonFixture {
        alias: false,
        left: u32::MAX,
        operation,
        right: 0x8000_0000,
        signed,
    };
    let (target, input) = lowered_integer_comparison_fixture(case)?;
    let (expected, tag) = expected_comparison_operation(signed, operation, 2)?;
    assert_comparison_checkpoint(&target, expected, tag, 2)?;
    let bytes = canonical_ternary_bytes(&target)
        .map_err(|error| format!("encode comparison forgery: {error:?}"))?;
    let offset = bytes
        .windows(5)
        .position(|window| window == [tag, 0, 0, 0, 0])
        .ok_or_else(|| String::from("comparison opcode not found"))?;
    let opposite = if signed {
        tag.saturating_add(1)
    } else {
        tag.saturating_sub(1)
    };
    for (replacement, expected_error) in [
        (
            opposite,
            TernaryProgramCodecError::Validation(
                TernaryProgramValidationError::SsaValue,
            ),
        ),
        (84u8, TernaryProgramCodecError::UnknownTag),
    ] {
        let mut forged = bytes.clone();
        *forged
            .get_mut(offset)
            .ok_or_else(|| String::from("comparison tag absent"))? =
            replacement;
        if canonical_ternary_program(&forged) != Err(expected_error) {
            return Err(format!(
                "forged comparison tag {replacement} admitted"
            ));
        }
    }
    for (wire_offset, replacement) in [
        (offset.saturating_add(5), 0u32),
        (offset.saturating_add(9), 99u32),
    ] {
        let mut forged = bytes.clone();
        forged
            .get_mut(wire_offset..wire_offset.saturating_add(4))
            .ok_or_else(|| String::from("comparison SSA bytes absent"))?
            .copy_from_slice(&replacement.to_le_bytes());
        if canonical_ternary_program(&forged)
            != Err(TernaryProgramCodecError::Validation(
                TernaryProgramValidationError::SsaValue,
            ))
        {
            return Err(String::from("forged comparison SSA admitted"));
        }
    }
    assert_invalid_comparison_projection(input)
}

fn assert_invalid_comparison_projection(
    input: TypedIrInput,
) -> Result<(), String> {
    for variation in 0u8..4u8 {
        let mut forged = input.clone();
        let instruction = forged
            .functions
            .first_mut()
            .and_then(|item| item.blocks.first_mut())
            .and_then(|block| block.instructions.get_mut(2))
            .ok_or_else(|| String::from("comparison projection missing"))?;
        let (InputInstruction::CompareEqual {
            type_kind, right, result, ..
        }
        | InputInstruction::CompareNotEqual {
            type_kind,
            right,
            result,
            ..
        }) = instruction
        else {
            return Err(String::from("comparison projection drifted"));
        };
        match variation {
            0 => *type_kind = InputScalarType::I32,
            1 => *right = 99,
            2 => *result = 0,
            3 => *right = 2,
            _ => return Err(String::from("unknown comparison forgery")),
        }
        let expected_error = if variation == 2 {
            TernaryLoweringError::InvalidProjection
        } else {
            TernaryLoweringError::UnsupportedInstruction
        };
        if lower_typed_ir(&forged) != Err(expected_error) {
            return Err(format!("comparison projection {variation} admitted"));
        }
    }
    let mut wrong_return = input;
    let function = wrong_return
        .functions
        .first_mut()
        .ok_or_else(|| String::from("comparison function missing"))?;
    function.return_kind = InputScalarType::U32;
    if lower_typed_ir(&wrong_return)
        != Err(TernaryLoweringError::UnsupportedTerminator)
    {
        return Err(String::from("forged comparison return admitted"));
    }
    Ok(())
}

fn assert_ordered_projection_forgery(
    input: &TypedIrInput,
    signed: bool,
) -> Result<(), String> {
    for variation in 0u8..5u8 {
        let mut forged = input.clone();
        let instruction = forged
            .functions
            .first_mut()
            .and_then(|function| function.blocks.first_mut())
            .and_then(|block| block.instructions.get_mut(2))
            .ok_or_else(|| String::from("ordered projection missing"))?;
        let InputInstruction::CompareOrdered {
            left,
            operation,
            result,
            right,
            type_kind,
            ..
        } = instruction
        else {
            return Err(String::from("ordered projection variant drifted"));
        };
        match variation {
            0 => *type_kind = InputScalarType::U32,
            1 => *right = 99,
            2 => *result = 0,
            3 => {
                *operation = if signed {
                    InputOrderedComparison::Unsigned
                } else {
                    InputOrderedComparison::Signed
                }
            },
            4 => *left = 2,
            _ => {
                return Err(String::from("unknown ordered projection forgery"));
            },
        }
        let expected = if variation == 2 {
            TernaryLoweringError::InvalidProjection
        } else {
            TernaryLoweringError::UnsupportedInstruction
        };
        if lower_typed_ir(&forged) != Err(expected) {
            return Err(format!(
                "ordered projection forgery {variation} admitted"
            ));
        }
    }
    Ok(())
}

fn assert_ordered_wire_forgery(
    case: ComparisonFixture,
    substitute: u8,
) -> Result<(), String> {
    let (target, input) = lowered_integer_comparison_fixture(case)?;
    let (_expected, tag) =
        expected_ordered_comparison_operation(case.operation, 2)?;
    let bytes = canonical_ternary_bytes(&target)
        .map_err(|error| format!("encode ordered comparison: {error:?}"))?;
    let offset = bytes
        .windows(5)
        .position(|wire| wire == [tag, 0, 0, 0, 0])
        .ok_or_else(|| String::from("ordered tag missing"))?;
    let failure = TernaryProgramCodecError::Validation(
        TernaryProgramValidationError::SsaValue,
    );
    for (offset_delta, replacement) in
        [(0usize, u32::from(substitute)), (5, 0), (9, 99)]
    {
        let mut forged = bytes.clone();
        let at = offset.saturating_add(offset_delta);
        let width = if offset_delta == 0 {
            1
        } else {
            4
        };
        let span = forged
            .get_mut(at..at.saturating_add(width))
            .ok_or_else(|| String::from("forged ordered field missing"))?;
        let replacement_bytes = replacement.to_le_bytes();
        let field = replacement_bytes
            .get(..width)
            .ok_or_else(|| String::from("ordered replacement field absent"))?;
        span.copy_from_slice(field);
        if canonical_ternary_program(&forged) != Err(failure) {
            return Err(String::from("forged ordered operand or tag admitted"));
        }
    }
    let mut unknown = bytes;
    *unknown
        .get_mut(offset)
        .ok_or_else(|| String::from("ordered tag byte missing"))? = 84;
    if canonical_ternary_program(&unknown)
        != Err(TernaryProgramCodecError::UnknownTag)
    {
        return Err(String::from("next unassigned ordered tag admitted"));
    }
    assert_ordered_projection_forgery(&input, case.signed)
}

#[test]
fn ordered_comparisons_reject_cross_signedness_and_invalid_ssa()
-> Result<(), String> {
    for (signed, operation, substitute) in [
        (true, CompareOp::LessSigned, 42u8),
        (true, CompareOp::LessSignedEqual, 43),
        (false, CompareOp::LessUnsigned, 40),
        (false, CompareOp::LessUnsignedEqual, 41),
    ] {
        let case = ComparisonFixture {
            alias: false,
            left: 0x8000_0000,
            operation,
            right: u32::MAX,
            signed,
        };
        assert_ordered_wire_forgery(case, substitute)?;
    }
    Ok(())
}

#[test]
fn ordered_comparisons_reject_wrong_signed_typed_ir() -> Result<(), String> {
    for (signed, operation) in [
        (true, CompareOp::LessUnsigned),
        (true, CompareOp::LessUnsignedEqual),
        (false, CompareOp::LessSigned),
        (false, CompareOp::LessSignedEqual),
    ] {
        let module = integer_comparison_module(ComparisonFixture {
            alias: false,
            left: 1,
            operation,
            right: 2,
            signed,
        });
        if validate_module(&module).is_ok() {
            return Err(String::from(
                "invalid comparison admitted by typed IR",
            ));
        }
    }
    Ok(())
}

#[test]
fn integer_comparison_rejects_signedness_and_ssa_forgery() -> Result<(), String>
{
    for signed in [true, false] {
        for operation in [CompareOp::Equal, CompareOp::NotEqual] {
            assert_comparison_forgery(signed, operation)?;
        }
    }
    Ok(())
}

#[test]
fn bool_return_rejects_non_boolean_tags() -> Result<(), String> {
    let (target, _input) =
        lowered_integer_comparison_fixture(ComparisonFixture {
            alias: true,
            left: 0,
            operation: CompareOp::Equal,
            right: 0,
            signed: true,
        })?;
    let bytes = canonical_ternary_bytes(&target)
        .map_err(|error| format!("encode boolean return: {error:?}"))?;
    let offset = bytes
        .windows(5)
        .position(|wire| wire == [39, 2, 0, 0, 0])
        .ok_or_else(|| String::from("boolean return tag missing"))?;
    for tag in [4u8, 9, 11] {
        let mut forged = bytes.clone();
        *forged
            .get_mut(offset)
            .ok_or_else(|| String::from("boolean return tag absent"))? = tag;
        if canonical_ternary_program(&forged)
            != Err(TernaryProgramCodecError::Validation(
                TernaryProgramValidationError::SsaValue,
            ))
        {
            return Err(format!("forged boolean return tag {tag} admitted"));
        }
    }
    Ok(())
}

#[test]
fn unsigned_bitwise_decoder_rejects_signed_opcodes_and_unknown_tag()
-> Result<(), String> {
    for (operation, tag, signed_tag) in [
        (BinaryOp::And, 12u8, 0u8),
        (BinaryOp::Or, 13u8, 6u8),
        (BinaryOp::Xor, 14u8, 7u8),
    ] {
        let (target, _projection) =
            lowered_unsigned_bitwise_fixture(u32::MAX, 0x8000_0000, operation)?;
        let bytes = canonical_ternary_bytes(&target).map_err(|error| {
            format!("encode unsigned forged fixture: {error:?}")
        })?;
        let pattern = [tag, 0, 0, 0, 0, 2, 0, 0, 0, 1, 0, 0, 0];
        let offset = bytes
            .windows(pattern.len())
            .position(|window| window == pattern)
            .ok_or_else(|| {
                String::from("unsigned operation wire tag missing")
            })?;
        for (mutated_tag, expected) in [
            (
                signed_tag,
                TernaryProgramCodecError::Validation(
                    TernaryProgramValidationError::SsaValue,
                ),
            ),
            (84u8, TernaryProgramCodecError::UnknownTag),
        ] {
            let mut forged = bytes.clone();
            *forged
                .get_mut(offset)
                .ok_or_else(|| String::from("unsigned tag byte missing"))? =
                mutated_tag;
            if canonical_ternary_program(&forged) != Err(expected) {
                return Err(String::from(
                    "forged unsigned operation tag admitted",
                ));
            }
        }
        let mut wrong_operand = bytes;
        wrong_operand
            .get_mut(offset + 9..offset + 13)
            .ok_or_else(|| String::from("unsigned operand bytes missing"))?
            .copy_from_slice(&99u32.to_le_bytes());
        if canonical_ternary_program(&wrong_operand)
            != Err(TernaryProgramCodecError::Validation(
                TernaryProgramValidationError::SsaValue,
            ))
        {
            return Err(String::from("undefined unsigned operand admitted"));
        }
    }
    Ok(())
}

#[test]
fn unsigned_decoder_rejects_signedness_forgery_and_closed_tag()
-> Result<(), String> {
    let (target, _input) = lowered_unsigned_return_fixture(u32::MAX)?;
    let encoded = canonical_ternary_bytes(&target)
        .map_err(|error| format!("encode unsigned state: {error:?}"))?;
    let materialization = [10u8, 0, 0, 0, 0];
    let materialize_offset = encoded
        .windows(materialization.len())
        .position(|window| window == materialization)
        .ok_or_else(|| String::from("unsigned constant wire missing"))?;
    let return_offset = encoded
        .len()
        .checked_sub(29)
        .ok_or_else(|| String::from("unsigned return wire missing"))?;
    for (position, tag, expected) in [
        (
            materialize_offset,
            3u8,
            TernaryProgramCodecError::Validation(
                TernaryProgramValidationError::SsaValue,
            ),
        ),
        (
            return_offset,
            4u8,
            TernaryProgramCodecError::Validation(
                TernaryProgramValidationError::SsaValue,
            ),
        ),
        (
            materialize_offset,
            84u8,
            TernaryProgramCodecError::UnknownTag,
        ),
        (return_offset, 84u8, TernaryProgramCodecError::UnknownTag),
    ] {
        let mut forged = encoded.clone();
        *forged.get_mut(position).ok_or_else(|| {
            String::from("unsigned opcode position missing")
        })? = tag;
        if canonical_ternary_program(&forged) != Err(expected) {
            return Err(format!("unsigned forged tag {tag} admitted"));
        }
    }
    Ok(())
}

#[test]
fn unsigned_decoder_rejects_valid_trits_above_u32_max() -> Result<(), String> {
    let (target, _input) = lowered_unsigned_return_fixture(u32::MAX)?;
    let encoded = canonical_ternary_bytes(&target)
        .map_err(|error| format!("encode max unsigned state: {error:?}"))?;
    let prefix = [10u8, 0, 0, 0, 0];
    let trit_offset = encoded
        .windows(prefix.len())
        .position(|window| window == prefix)
        .and_then(|index| index.checked_add(prefix.len()))
        .ok_or_else(|| String::from("unsigned trit position missing"))?;
    let mut oversized = u64::from(u32::MAX).saturating_add(1);
    let mut trits = [0u8; I32_TERNARY_TRITS];
    for digit in &mut trits {
        *digit = u8::try_from(oversized.checked_rem(3).unwrap_or_default())
            .map_err(|error| format!("convert oversized trit: {error}"))?;
        oversized = oversized.checked_div(3).unwrap_or_default();
    }
    let end = trit_offset
        .checked_add(trits.len())
        .ok_or_else(|| String::from("trit extent overflow"))?;
    let mut forged = encoded;
    forged
        .get_mut(trit_offset..end)
        .ok_or_else(|| String::from("unsigned scalar bytes missing"))?
        .copy_from_slice(&trits);
    if canonical_ternary_program(&forged)
        != Err(TernaryProgramCodecError::InvalidScalar)
    {
        return Err(String::from("out-of-range ternary scalar admitted"));
    }
    Ok(())
}

#[test]
fn unsigned_projection_rejects_forged_signedness_or_scalar_width()
-> Result<(), String> {
    let (_target, input) = lowered_unsigned_return_fixture(u32::MAX)?;
    for variant in 0u8..4u8 {
        let mut forged = input.clone();
        let function = forged
            .functions
            .first_mut()
            .ok_or_else(|| String::from("unsigned function missing"))?;
        if variant == 0 {
            function.return_kind = InputScalarType::I32;
        } else {
            let instruction = function
                .blocks
                .first_mut()
                .and_then(|block| block.instructions.first_mut())
                .ok_or_else(|| String::from("unsigned constant missing"))?;
            let InputInstruction::ConstantInteger {
                bit_width,
                little_endian,
                type_kind,
                ..
            } = instruction
            else {
                return Err(String::from("unsigned projection changed shape"));
            };
            match variant {
                1 => *type_kind = InputScalarType::I32,
                2 => *bit_width = 8,
                3 => {
                    let _dropped = little_endian.pop();
                },
                _ => return Err(String::from("unknown signedness fixture")),
            }
        }
        let actual = lower_typed_ir(&forged);
        let expected = if variant == 0 || variant == 1 {
            TernaryLoweringError::UnsupportedTerminator
        } else {
            TernaryLoweringError::UnsupportedInstruction
        };
        if actual != Err(expected) {
            return Err(format!(
                "forged unsigned projection {variant} accepted"
            ));
        }
    }
    Ok(())
}

#[test]
fn admitted_byte_return_preserves_signature_and_canonical_target_tag()
-> Result<(), String> {
    for literal in [None, Some(0), Some(255)] {
        let (program, input) = lowered_byte_return_fixture(literal)?;
        if input.functions.first().map(|function| function.return_kind)
            != Some(InputScalarType::U8)
        {
            return Err(String::from("typed byte result type was lost"));
        }
        let function = program
            .functions
            .first()
            .ok_or_else(|| String::from("byte return has no function"))?;
        let expected = TernaryOperation::ReturnU8 {
            span: output_span(fixture_span(3, 4)),
            value: 0,
        };
        if function.operations.last() != Some(&expected) {
            return Err(String::from(
                "byte return lowered with wrong SSA/type",
            ));
        }
        let bytes = canonical_ternary_bytes(&program)
            .map_err(|error| format!("encode byte-return target: {error:?}"))?;
        let Some(&9) = bytes.get(bytes.len().saturating_sub(29)) else {
            return Err(String::from("new byte return wire tag missing"));
        };
        if canonical_ternary_program(&bytes) != Ok(program) {
            return Err(String::from("byte return target round trip drifted"));
        }
    }
    Ok(())
}

#[test]
fn byte_return_projection_rejects_wrong_declared_type_or_return_value()
-> Result<(), String> {
    let (_program, input) = lowered_byte_return_fixture(Some(255))?;
    for wrong in [InputScalarType::I32, InputScalarType::Other] {
        let mut forged = input.clone();
        let function = forged
            .functions
            .first_mut()
            .ok_or_else(|| String::from("missing byte return function"))?;
        function.return_kind = wrong;
        if lower_typed_ir(&forged)
            != Err(TernaryLoweringError::UnsupportedTerminator)
        {
            return Err(String::from("forged return type admitted"));
        }
    }
    let mut wrong_value = input;
    let block = wrong_value
        .functions
        .first_mut()
        .and_then(|function| function.blocks.first_mut())
        .ok_or_else(|| String::from("missing byte-return block"))?;
    let InputTerminator::Return { value, .. } = &mut block.terminator else {
        return Err(String::from("missing byte-return terminator"));
    };
    *value = Some(1);
    if lower_typed_ir(&wrong_value)
        != Err(TernaryLoweringError::UnsupportedTerminator)
    {
        return Err(String::from("i32 SSA returned from byte function"));
    }
    Ok(())
}

#[test]
fn byte_return_checkpoint_rejects_forged_source_and_closed_tag()
-> Result<(), String> {
    let (program, _input) = lowered_byte_return_fixture(Some(255))?;
    let bytes = canonical_ternary_bytes(&program)
        .map_err(|error| format!("encode byte return: {error:?}"))?;
    let tag_offset = bytes
        .len()
        .checked_sub(29)
        .ok_or_else(|| String::from("byte-return wire too short"))?;
    for forged_tag in [4u8, 84u8] {
        let mut forged = bytes.clone();
        *forged
            .get_mut(tag_offset)
            .ok_or_else(|| String::from("byte-return tag missing"))? =
            forged_tag;
        let expected = if forged_tag == 4 {
            Err(TernaryProgramCodecError::Validation(
                TernaryProgramValidationError::SsaValue,
            ))
        } else {
            Err(TernaryProgramCodecError::UnknownTag)
        };
        if canonical_ternary_program(&forged) != expected {
            return Err(String::from("forged return tag admitted"));
        }
    }
    let mut forged = bytes;
    let offset = forged
        .len()
        .checked_sub(4)
        .ok_or_else(|| String::from("byte-return value missing"))?;
    forged
        .get_mut(offset..)
        .ok_or_else(|| String::from("byte-return value span missing"))?
        .copy_from_slice(&1u32.to_le_bytes());
    if canonical_ternary_program(&forged)
        != Err(TernaryProgramCodecError::Validation(
            TernaryProgramValidationError::SsaValue,
        ))
    {
        return Err(String::from("i32 use in byte-return checkpoint admitted"));
    }
    Ok(())
}

fn large_byte_projection(value_count: u32) -> Result<TypedIrInput, String> {
    let mut input = project_typed_ir(&byte_return_module(Some(0)))?;
    let block = input
        .functions
        .first_mut()
        .and_then(|function| function.blocks.first_mut())
        .ok_or_else(|| String::from("missing large-projection block"))?;
    let last = value_count
        .checked_sub(1)
        .ok_or_else(|| String::from("empty large-byte projection"))?;
    for result in 2..value_count {
        block.instructions.push(InputInstruction::ConstantInteger {
            bit_width: 8,
            little_endian: vec![
                u8::try_from(result.checked_rem(256).unwrap_or_default())
                    .map_err(|error| {
                        format!("convert fixture byte: {error}")
                    })?,
            ],
            result,
            span: input_span(fixture_span(2, 3)),
            type_kind: InputScalarType::U8,
        });
    }
    block.instructions.push(InputInstruction::ByteOutput {
        span: input_span(fixture_span(2, 3)),
        value: last,
    });
    block.terminator = InputTerminator::Return {
        span: input_span(fixture_span(3, 4)),
        value: Some(last),
    };
    Ok(input)
}

#[test]
fn large_typed_byte_projection_lowers_deterministically_without_linear_scans()
-> Result<(), String> {
    let count = 16_384u32;
    let input = large_byte_projection(count)?;
    let first = lower_typed_ir(&input)
        .map_err(|error| format!("lower large-byte projection: {error:?}"))?;
    let second = lower_typed_ir(&input)
        .map_err(|error| format!("repeat large-byte projection: {error:?}"))?;
    if first != second {
        return Err(String::from("large SSA lowering was nondeterministic"));
    }
    let function = first
        .functions
        .first()
        .ok_or_else(|| String::from("missing large SSA function"))?;
    let expected_count = usize::try_from(count)
        .unwrap_or_default()
        .checked_add(3)
        .ok_or_else(|| String::from("projection length overflow"))?;
    if function.operations.len() != expected_count
        || function.operations.last()
            != Some(&TernaryOperation::ReturnU8 {
                span: output_span(fixture_span(3, 4)),
                value: count.saturating_sub(1),
            })
    {
        return Err(String::from("large SSA lowering lost value or return"));
    }
    let encoded = canonical_ternary_bytes(&first)
        .map_err(|error| format!("encode large SSA: {error:?}"))?;
    if canonical_ternary_program(&encoded) != Ok(first) {
        return Err(String::from("large SSA checkpoint admission drifted"));
    }
    Ok(())
}

#[test]
fn large_typed_byte_projection_rejects_late_duplicate_definition()
-> Result<(), String> {
    let mut input = large_byte_projection(8_192)?;
    let block = input
        .functions
        .first_mut()
        .and_then(|function| function.blocks.first_mut())
        .ok_or_else(|| String::from("missing duplicate-projection block"))?;
    let instruction = block
        .instructions
        .iter_mut()
        .rev()
        .find(|instruction| {
            matches!(instruction, InputInstruction::ConstantInteger { .. })
        })
        .ok_or_else(|| String::from("missing late byte constant"))?;
    let InputInstruction::ConstantInteger { result, .. } = instruction else {
        return Err(String::from("last SSA definition is not a byte constant"));
    };
    *result = 0;
    if lower_typed_ir(&input) != Err(TernaryLoweringError::InvalidProjection) {
        return Err(String::from("late duplicated SSA result was admitted"));
    }
    Ok(())
}

#[test]
fn byte_constant_lowers_to_canonical_byte_output() -> Result<(), String> {
    for bits in [0u8, 1, 127, 243, 255] {
        let (program, _input) = lowered_byte_constant_fixture(bits)?;
        let function = program
            .functions
            .first()
            .ok_or_else(|| String::from("missing byte-constant function"))?;
        let scalar = ternary_lowering::TernaryU8Scalar::from_bits(bits);
        let expected = TernaryOperation::MaterializeU8 {
            result: 0,
            scalar,
            span: output_span(fixture_span(0, 1)),
        };
        if function.operations.first() != Some(&expected)
            || function.operations.get(1)
                != Some(&TernaryOperation::ByteOutput {
                    span: output_span(fixture_span(1, 2)),
                    value: 0,
                })
        {
            return Err(String::from("byte literal did not drive byte output"));
        }
        let bytes = canonical_ternary_bytes(&program).map_err(|error| {
            format!("encode byte-constant state: {error:?}")
        })?;
        let mut pattern = vec![8, 0, 0, 0, 0];
        pattern.extend_from_slice(scalar.trits());
        if !bytes.windows(pattern.len()).any(|window| window == pattern)
            || canonical_ternary_program(&bytes) != Ok(program)
        {
            return Err(String::from(
                "byte-constant canonical encoding drifted",
            ));
        }
    }
    Ok(())
}

#[test]
fn malformed_byte_constant_projection_fails_closed() -> Result<(), String> {
    let (_program, input) = lowered_byte_constant_fixture(255)?;
    for variant in 0u8..4u8 {
        let mut malformed = input.clone();
        let instruction = malformed
            .functions
            .first_mut()
            .and_then(|function| function.blocks.first_mut())
            .and_then(|block| block.instructions.first_mut())
            .ok_or_else(|| String::from("missing byte-constant instruction"))?;
        let InputInstruction::ConstantInteger {
            bit_width,
            little_endian,
            result,
            type_kind,
            ..
        } = instruction
        else {
            return Err(String::from("missing projected byte literal"));
        };
        match variant {
            0 => *bit_width = 32,
            1 => *little_endian = vec![255, 0],
            2 => *type_kind = InputScalarType::I32,
            3 => *result = 1,
            _ => return Err(String::from("unknown byte-constant test case")),
        }
        if lower_typed_ir(&malformed)
            != Err(TernaryLoweringError::UnsupportedInstruction)
        {
            return Err(format!(
                "malformed byte-constant variant {variant} lowered"
            ));
        }
    }
    Ok(())
}

#[test]
fn byte_constant_decoder_rejects_invalid_ternary_scalar() -> Result<(), String>
{
    let (program, _input) = lowered_byte_constant_fixture(255)?;
    let encoded = canonical_ternary_bytes(&program)
        .map_err(|error| format!("encode byte-constant state: {error:?}"))?;
    let mut needle = vec![8, 0, 0, 0, 0];
    needle.extend_from_slice(
        ternary_lowering::TernaryU8Scalar::from_bits(255).trits(),
    );
    let offset = encoded
        .windows(needle.len())
        .position(|window| window == needle)
        .ok_or_else(|| String::from("byte-scalar wire tag not found"))?;
    for corrupted in [[3u8, 0, 0, 0, 0, 0], [1, 1, 1, 0, 0, 1]] {
        let mut forged = encoded.clone();
        forged
            .get_mut(offset + 5..offset + 11)
            .ok_or_else(|| String::from("byte-scalar wire span missing"))?
            .copy_from_slice(&corrupted);
        if canonical_ternary_program(&forged)
            != Err(TernaryProgramCodecError::InvalidScalar)
        {
            return Err(String::from("forged six-trit scalar was admitted"));
        }
    }
    let mut forged = encoded;
    *forged
        .get_mut(offset)
        .ok_or_else(|| String::from("byte opcode missing"))? = 84;
    if canonical_ternary_program(&forged)
        != Err(TernaryProgramCodecError::UnknownTag)
    {
        return Err(String::from("next unknown byte opcode was admitted"));
    }
    Ok(())
}

#[test]
fn six_trit_checkpoint_decoder_accepts_exact_byte_domain() -> Result<(), String>
{
    let (program, _input) = lowered_byte_constant_fixture(255)?;
    let canonical = canonical_ternary_bytes(&program)
        .map_err(|error| format!("encode byte scalar: {error:?}"))?;
    let mut pattern = vec![8u8, 0, 0, 0, 0];
    pattern.extend_from_slice(
        ternary_lowering::TernaryU8Scalar::from_bits(255).trits(),
    );
    let scalar_offset = canonical
        .windows(pattern.len())
        .position(|window| window == pattern)
        .and_then(|offset| offset.checked_add(5))
        .ok_or_else(|| String::from("byte scalar wire position missing"))?;
    for bits in 0u16..729u16 {
        let mut value = bits;
        let mut trits = [0u8; ternary_lowering::U8_TERNARY_TRITS];
        for trit in &mut trits {
            *trit = u8::try_from(value.checked_rem(3).unwrap_or_default())
                .map_err(|error| format!("encode trit: {error}"))?;
            value = value.checked_div(3).unwrap_or_default();
        }
        let mut forged = canonical.clone();
        forged
            .get_mut(scalar_offset..scalar_offset + trits.len())
            .ok_or_else(|| String::from("six-trit wire span truncated"))?
            .copy_from_slice(&trits);
        let observed = canonical_ternary_program(&forged);
        if let Ok(admitted_bits) = u8::try_from(bits) {
            let decoded = observed.map_err(|error| {
                format!("valid byte {bits} rejected: {error:?}")
            })?;
            let expected =
                ternary_lowering::TernaryU8Scalar::from_bits(admitted_bits);
            let first = decoded
                .functions
                .first()
                .and_then(|function| function.operations.first());
            let admitted = matches!(
                first,
                Some(TernaryOperation::MaterializeU8 { scalar, .. })
                    if *scalar == expected
            );
            if !admitted || canonical_ternary_bytes(&decoded) != Ok(forged) {
                return Err(format!("six-trit byte {bits} drifted"));
            }
        } else if observed != Err(TernaryProgramCodecError::InvalidScalar) {
            return Err(format!("out-of-range six-trit value {bits} admitted"));
        }
    }
    Ok(())
}

#[test]
fn byte_constant_checkpoint_rejects_forged_output_ssa() -> Result<(), String> {
    let (program, _input) = lowered_byte_constant_fixture(255)?;
    let canonical = canonical_ternary_bytes(&program)
        .map_err(|error| format!("encode byte scalar: {error:?}"))?;
    let source = [8u8, 0, 0, 0, 0];
    let tag_offset = canonical
        .windows(source.len())
        .position(|window| window == source)
        .ok_or_else(|| String::from("byte-constant tag missing"))?;
    let mut wrong_result = canonical;
    wrong_result
        .get_mut(tag_offset + 1..tag_offset + 5)
        .ok_or_else(|| String::from("byte-constant result missing"))?
        .copy_from_slice(&1u32.to_le_bytes());
    let expected = Err(TernaryProgramCodecError::Validation(
        TernaryProgramValidationError::SsaValue,
    ));
    if canonical_ternary_program(&wrong_result) != expected {
        return Err(String::from("forged byte definition was admitted"));
    }
    let mut wrong_output = program;
    let operation = wrong_output
        .functions
        .first_mut()
        .and_then(|function| function.operations.get_mut(1))
        .ok_or_else(|| String::from("byte-output operation missing"))?;
    let TernaryOperation::ByteOutput { value, .. } = operation else {
        return Err(String::from("byte-output operation type changed"));
    };
    *value = 1;
    if ternary_lowering::validate_ternary_program(&wrong_output)
        != Err(TernaryProgramValidationError::SsaValue)
    {
        return Err(String::from("byte-output read from i32 was admitted"));
    }
    Ok(())
}

#[test]
fn byte_io_effects_lower_after_canonical_typed_ir_round_trip()
-> Result<(), String> {
    let module = admitted_byte_io_fixture()?;
    let input = project_typed_ir(&module)?;
    let first = lower_typed_ir(&input)
        .map_err(|error| format!("lower byte-I/O projection: {error:?}"))?;
    let second = lower_typed_ir(&input)
        .map_err(|error| format!("repeat byte-I/O lowering: {error:?}"))?;
    if first != second {
        return Err(String::from("byte-I/O lowering is not deterministic"));
    }
    assert_byte_io_program(&module, &first)
}

fn assert_low_byte_and(
    function: &ternary_lowering::TernaryFunction,
) -> Result<(), String> {
    let operation = function
        .operations
        .get(2)
        .ok_or_else(|| String::from("missing low-byte AND"))?;
    let TernaryOperation::AndI32 {
        left,
        result,
        right,
        span,
    } = operation
    else {
        return Err(String::from("low-byte path did not lower bitwise AND"));
    };
    if (*left, *result, *right) != (0, 2, 1)
        || *span != output_span(fixture_span(2, 3))
    {
        return Err(String::from("low-byte AND operands drifted"));
    }
    Ok(())
}

fn assert_low_byte_output(
    function: &ternary_lowering::TernaryFunction,
) -> Result<(), String> {
    let operation = function
        .operations
        .get(4)
        .ok_or_else(|| String::from("missing low-byte output"))?;
    if *operation
        != (TernaryOperation::ByteOutput {
            span: output_span(fixture_span(4, 5)),
            value: 3,
        })
    {
        return Err(String::from("low-byte output did not consume u8 result"));
    }
    Ok(())
}

fn assert_low_byte_truncate(
    function: &ternary_lowering::TernaryFunction,
) -> Result<(), String> {
    let operation = function
        .operations
        .get(3)
        .ok_or_else(|| String::from("missing low-byte truncation"))?;
    let TernaryOperation::TruncateI32ToU8 {
        result: truncate_result,
        span: truncate_span,
        value: truncate_value,
    } = operation
    else {
        return Err(String::from("low-byte path did not lower truncation"));
    };
    if (*truncate_result, *truncate_value) != (3, 2)
        || *truncate_span != output_span(fixture_span(3, 4))
    {
        return Err(String::from("low-byte truncation operands drifted"));
    }
    Ok(())
}

fn assert_bitwise_projection_rejections(
    input: TypedIrInput,
) -> Result<(), String> {
    let mut wrong_type = input.clone();
    let wrong_instruction = wrong_type
        .functions
        .first_mut()
        .and_then(|item| item.blocks.first_mut())
        .and_then(|block| block.instructions.get_mut(2))
        .ok_or_else(|| String::from("missing projected bitwise instruction"))?;
    let (InputInstruction::BinaryOr { type_kind, .. }
    | InputInstruction::BinaryXor { type_kind, .. }) = wrong_instruction
    else {
        return Err(String::from("missing projected bitwise variant"));
    };
    *type_kind = InputScalarType::Other;
    if lower_typed_ir(&wrong_type)
        != Err(TernaryLoweringError::UnsupportedInstruction)
    {
        return Err(String::from("invalid bitwise scalar type was lowered"));
    }
    let mut undefined = input;
    let undefined_instruction = undefined
        .functions
        .first_mut()
        .and_then(|item| item.blocks.first_mut())
        .and_then(|block| block.instructions.get_mut(2))
        .ok_or_else(|| String::from("missing projected bitwise instruction"))?;
    let (InputInstruction::BinaryOr { right, .. }
    | InputInstruction::BinaryXor { right, .. }) = undefined_instruction
    else {
        return Err(String::from("missing projected bitwise variant"));
    };
    *right = 99;
    if lower_typed_ir(&undefined)
        != Err(TernaryLoweringError::UnsupportedInstruction)
    {
        return Err(String::from("undefined bitwise SSA operand was lowered"));
    }
    Ok(())
}

#[test]
fn i32_or_xor_lower_from_canonical_typed_ir_with_closed_wire_tags()
-> Result<(), String> {
    for (operation, target_tag) in [(BinaryOp::Or, 6u8), (BinaryOp::Xor, 7u8)] {
        let module = low_byte_module_with_binary(operation);
        validate_module(&module)
            .map_err(|error| format!("bitwise typed admission: {error:?}"))?;
        let typed_bytes = canonical_bytes(&module)
            .map_err(|error| format!("encode typed bitwise: {error:?}"))?;
        let restored = canonical_module(&typed_bytes)
            .map_err(|error| format!("restore typed bitwise: {error:?}"))?;
        if restored != module {
            return Err(String::from("bitwise typed state round trip drifted"));
        }
        let input = project_typed_ir(&restored)?;
        let ternary = lower_typed_ir(&input)
            .map_err(|error| format!("lower bitwise: {error:?}"))?;
        assert_program_provenance(&restored, &ternary)?;
        let function = ternary
            .functions
            .first()
            .ok_or_else(|| String::from("missing lowered function"))?;
        let actual = function
            .operations
            .get(2)
            .ok_or_else(|| String::from("missing lowered bitwise operation"))?;
        let expected = if operation == BinaryOp::Or {
            TernaryOperation::OrI32 {
                left: 0,
                result: 2,
                right: 1,
                span: output_span(fixture_span(2, 3)),
            }
        } else {
            TernaryOperation::XorI32 {
                left: 0,
                result: 2,
                right: 1,
                span: output_span(fixture_span(2, 3)),
            }
        };
        if *actual != expected {
            return Err(String::from("lowered bitwise SSA/provenance drifted"));
        }
        let encoded = canonical_ternary_bytes(&ternary)
            .map_err(|error| format!("encode bitwise ternary: {error:?}"))?;
        let pattern = [target_tag, 0, 0, 0, 0, 2, 0, 0, 0, 1, 0, 0, 0];
        if !encoded
            .windows(pattern.len())
            .any(|window| window == pattern)
        {
            return Err(String::from("bitwise target opcode encoding drifted"));
        }
        let decoded = canonical_ternary_program(&encoded)
            .map_err(|error| format!("decode bitwise ternary: {error:?}"))?;
        if decoded != ternary {
            return Err(String::from(
                "bitwise ternary canonical round trip drifted",
            ));
        }
        assert_bitwise_projection_rejections(input)?;
    }
    Ok(())
}

#[test]
fn low_byte_helper_path_round_trips_and_lowers() -> Result<(), String> {
    let module = admitted_low_byte_fixture()?;
    let input = project_typed_ir(&module)?;
    let program = lower_typed_ir(&input)
        .map_err(|error| format!("lower low-byte projection: {error:?}"))?;
    assert_program_provenance(&module, &program)?;
    let function = program
        .functions
        .first()
        .ok_or_else(|| String::from("low-byte lowering emitted no function"))?;
    if function.operations.len() != 6 {
        return Err(String::from("unexpected low-byte operation count"));
    }
    assert_low_byte_and(function)?;
    assert_low_byte_truncate(function)?;
    assert_low_byte_output(function)
}

#[test]
fn i32_ternary_scalar_width_is_minimal() -> Result<(), String> {
    let patterns = 1u64 << 32u32;
    if 3u64.pow(20) >= patterns || 3u64.pow(21) < patterns {
        return Err(String::from(
            "21 trits is not the minimal complete 32-bit scalar width",
        ));
    }
    Ok(())
}

#[test]
fn i32_ternary_scalars_preserve_extreme_bit_patterns() -> Result<(), String> {
    for bits in [0u32, 1, 0x7fff_ffff, 0x8000_0000, u32::MAX] {
        let scalar = ternary_lowering::TernaryI32Scalar::from_bits(bits);
        if scalar.bits() != bits || scalar.trits().iter().any(|trit| *trit > 2)
        {
            return Err(format!("ternary scalar round trip failed for {bits}"));
        }
    }
    Ok(())
}

#[test]
fn malformed_constant_projection_fails_closed() -> Result<(), String> {
    let module = admitted_golden(RETURN_GOLDEN)?;
    let mut input = project_typed_ir(&module)?;
    let Some(function) = input.functions.first_mut() else {
        return Err(String::from("projection has no function"));
    };
    let Some(block) = function.blocks.first_mut() else {
        return Err(String::from("projection has no block"));
    };
    let Some(instruction) = block.instructions.first_mut() else {
        return Err(String::from("projection has no instruction"));
    };
    let InputInstruction::ConstantInteger { little_endian, .. } = instruction
    else {
        return Err(String::from("projection constant is missing"));
    };
    let _: Option<u8> = little_endian.pop();
    if lower_typed_ir(&input)
        != Err(TernaryLoweringError::UnsupportedInstruction)
    {
        return Err(String::from("truncated constant was not rejected"));
    }
    Ok(())
}

#[test]
fn projection_identity_drift_fails_closed() -> Result<(), String> {
    let module = admitted_golden(RETURN_GOLDEN)?;
    let mut input = project_typed_ir(&module)?;
    input.target_profile = String::from("other-profile");
    if lower_typed_ir(&input) != Err(TernaryLoweringError::InvalidProjection) {
        return Err(String::from("target profile drift was not rejected"));
    }
    Ok(())
}

#[test]
fn startup_plan_binds_heap_before_user_entry() -> Result<(), String> {
    let request = valid_startup_request();
    let first = plan_startup(&request)
        .map_err(|error| format!("plan startup: {error:?}"))?;
    let second = plan_startup(&request)
        .map_err(|error| format!("repeat startup plan: {error:?}"))?;
    if first != second
        || first.bind_identity != "malbolge_guest_runtime_bind_heap"
        || first.actions
            != vec![
                StartupAction::BindHeap {
                    arena_pointer: 0x101,
                    capacity: 0x100,
                },
                StartupAction::EnterUserCode { function: 7 },
            ]
    {
        return Err(String::from("startup bind-before-entry plan drifted"));
    }
    Ok(())
}

#[test]
fn startup_plan_rejects_identity_drift() -> Result<(), String> {
    for mutate in 0u8..3u8 {
        let mut request = valid_startup_request();
        match mutate {
            0 => request.abi_id = String::from("host-abi"),
            1 => request.bind_identity = String::from("malloc"),
            _ => request.target_profile = String::from("malbolge-2026.3"),
        }
        if plan_startup(&request) != Err(StartupPlanningError::InvalidIdentity)
        {
            return Err(format!(
                "startup identity drift {mutate} was accepted"
            ));
        }
    }
    Ok(())
}

#[test]
fn startup_plan_rejects_invalid_heap_layout() -> Result<(), String> {
    for (arena_pointer, capacity) in [
        (0u32, 0x100u32),
        (0x102, 0x100),
        (0x101, 16),
        (0x101, 33),
        (0xffff_fff1, 32),
    ] {
        let mut request = valid_startup_request();
        request.arena_pointer = arena_pointer;
        request.capacity = capacity;
        if plan_startup(&request) != Err(StartupPlanningError::InvalidLayout) {
            return Err(format!(
                "invalid heap layout {arena_pointer:#x}/{capacity} accepted",
            ));
        }
    }
    Ok(())
}

#[test]
fn startup_authority_matches_guest_runtime_contract() -> Result<(), String> {
    let contract = read_to_string(GUEST_RUNTIME_CONTRACT)
        .map_err(|error| format!("read guest-runtime contract: {error}"))?;
    let header = read_to_string(GUEST_RUNTIME_HEADER)
        .map_err(|error| format!("read guest-runtime header: {error}"))?;
    for expected in [
        "\"heap_binding\": \"one-shot\"",
        "\"alignment\": 16",
        "\"header_bytes\": 16",
    ] {
        if !contract.contains(expected) {
            return Err(format!(
                "runtime startup authority missing {expected}"
            ));
        }
    }
    if !header.contains("malbolge_guest_runtime_bind_heap")
        || !header.contains("MALBOLGE_GUEST_HEAP_ALIGNMENT UINT32_C(16)")
        || !header.contains("MALBOLGE_GUEST_HEAP_HEADER_SIZE UINT32_C(16)")
    {
        return Err(String::from("guest-runtime startup header drifted"));
    }
    Ok(())
}

#[test]
fn runtime_intrinsic_identities_match_guest_runtime_authority()
-> Result<(), String> {
    let contract = read_to_string(GUEST_RUNTIME_CONTRACT)
        .map_err(|error| format!("read guest-runtime contract: {error}"))?;
    let header = read_to_string(GUEST_INTRINSICS_HEADER)
        .map_err(|error| format!("read guest intrinsic header: {error}"))?;
    for expected in [
        "malbolge_guest_intrinsic_input_word",
        "malbolge_guest_intrinsic_output_byte",
    ] {
        if !contract.contains(expected) || !header.contains(expected) {
            return Err(format!(
                "runtime intrinsic authority missing {expected}"
            ));
        }
    }
    if !contract.contains("\"target_profile\": \"malbolge-2026\"") {
        return Err(String::from("guest-runtime target profile drifted"));
    }
    Ok(())
}

#[test]
fn frame_helper_authority_matches_abi_and_runtime() -> Result<(), String> {
    let abi = read_to_string(ABI_CONTRACT)
        .map_err(|error| format!("read ABI contract: {error}"))?;
    let header = read_to_string(GUEST_RUNTIME_HEADER)
        .map_err(|error| format!("read guest-runtime header: {error}"))?;
    let source = read_to_string(GUEST_FRAME_SOURCE)
        .map_err(|error| format!("read guest frame source: {error}"))?;
    for expected in [
        "malbolge_guest_frame_decode",
        "malbolge_guest_frame_encode",
        "malbolge_guest_frame_validate",
        "FRAME_ALIGNMENT UINT32_C(16)",
        "copy_wire(wire, encoded)",
        "frame->previous_frame = decoded.previous_frame",
    ] {
        if !source.contains(expected) {
            return Err(format!("frame source authority missing {expected}"));
        }
    }
    for expected in [
        "MALBOLGE_GUEST_FRAME_HEADER_SIZE UINT32_C(32)",
        "MALBOLGE_GUEST_RUNTIME_VALID = 0",
        "MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT = 1",
        "MALBOLGE_GUEST_RUNTIME_INVALID_FRAME = 5",
    ] {
        if !header.contains(expected) {
            return Err(format!("frame header authority missing {expected}"));
        }
    }
    for expected in [
        "\"frame_header_bytes\": 32",
        "\"name\": \"argument_block\"",
        "\"name\": \"flags\"",
    ] {
        if !abi.contains(expected) {
            return Err(format!("frame ABI authority missing {expected}"));
        }
    }
    Ok(())
}

#[test]
fn frame_validator_realizes_exact_control_flow() -> Result<(), String> {
    let operation = lower_frame_helper(&FrameHelperRequest {
        abi_id: String::from("malbolge-c32-v1"),
        identity: String::from("malbolge_guest_frame_validate"),
        runtime_id: String::from("malbolge-guest-runtime-v1"),
    })
    .map_err(|error| format!("lower frame helper: {error:?}"))?;
    let expected_semantics = FrameValidationSemantics {
        alignment: 16,
        header_bytes: 32,
        invalid_argument_status: 1,
        invalid_frame_status: 5,
        required_flags: 0,
        valid_status: 0,
    };
    if operation != FrameHelperOperation::Validate(expected_semantics) {
        return Err(String::from("frame validation semantics drifted"));
    }
    let expected = FrameHelperExecutionPlan::Validate {
        exits: vec![
            FrameValidationArm {
                condition: FrameValidationCondition::FramePointerNull,
                status: 1,
            },
            FrameValidationArm {
                condition: FrameValidationCondition::FrameExtentBelow(32),
                status: 5,
            },
            FrameValidationArm {
                condition: FrameValidationCondition::FrameExtentMisaligned(16),
                status: 5,
            },
            FrameValidationArm {
                condition: FrameValidationCondition::ArgumentBlockNull,
                status: 5,
            },
            FrameValidationArm {
                condition: FrameValidationCondition::FlagsNotEqual(0),
                status: 5,
            },
            FrameValidationArm {
                condition: FrameValidationCondition::Otherwise,
                status: 0,
            },
        ],
    };
    if realize_frame_helper(operation) != expected {
        return Err(String::from("frame validator control flow drifted"));
    }
    Ok(())
}

const fn expected_frame_fields() -> [FrameFieldLayout; 8] {
    [
        FrameFieldLayout {
            field: FrameField::PreviousFrame,
            offset: 0,
        },
        FrameFieldLayout {
            field: FrameField::ContinuationId,
            offset: 4,
        },
        FrameFieldLayout {
            field: FrameField::FunctionId,
            offset: 8,
        },
        FrameFieldLayout {
            field: FrameField::FrameExtent,
            offset: 12,
        },
        FrameFieldLayout {
            field: FrameField::ArgumentBlock,
            offset: 16,
        },
        FrameFieldLayout {
            field: FrameField::ResultBlock,
            offset: 20,
        },
        FrameFieldLayout {
            field: FrameField::VariadicBegin,
            offset: 24,
        },
        FrameFieldLayout {
            field: FrameField::Flags,
            offset: 28,
        },
    ]
}

fn frame_validation_plan() -> FrameHelperExecutionPlan {
    FrameHelperExecutionPlan::Validate {
        exits: vec![
            FrameValidationArm {
                condition: FrameValidationCondition::FramePointerNull,
                status: 1,
            },
            FrameValidationArm {
                condition: FrameValidationCondition::FrameExtentBelow(32),
                status: 5,
            },
            FrameValidationArm {
                condition: FrameValidationCondition::FrameExtentMisaligned(16),
                status: 5,
            },
            FrameValidationArm {
                condition: FrameValidationCondition::ArgumentBlockNull,
                status: 5,
            },
            FrameValidationArm {
                condition: FrameValidationCondition::FlagsNotEqual(0),
                status: 5,
            },
            FrameValidationArm {
                condition: FrameValidationCondition::Otherwise,
                status: 0,
            },
        ],
    }
}

#[test]
fn frame_encode_defers_wire_publication_until_validation() -> Result<(), String>
{
    let operation = lower_frame_helper(&FrameHelperRequest {
        abi_id: String::from("malbolge-c32-v1"),
        identity: String::from("malbolge_guest_frame_encode"),
        runtime_id: String::from("malbolge-guest-runtime-v1"),
    })
    .map_err(|error| format!("lower frame encode: {error:?}"))?;
    let observed = realize_frame_helper(operation);
    let mut expected_steps = vec![
        FrameCodecExecutionStep::GuardWirePointerNonNull { failure_status: 1 },
        FrameCodecExecutionStep::GuardWireSizeExact {
            bytes: 32,
            failure_status: 1,
        },
        FrameCodecExecutionStep::ValidateFrameOrReturn(Box::new(
            frame_validation_plan(),
        )),
    ];
    expected_steps.extend(
        expected_frame_fields()
            .into_iter()
            .map(FrameCodecExecutionStep::EncodeFieldLittleEndian),
    );
    expected_steps.push(FrameCodecExecutionStep::PublishEncodedWireAtomically);
    expected_steps.push(FrameCodecExecutionStep::ReturnStatus(0));
    let expected = FrameHelperExecutionPlan::Encode { steps: expected_steps };
    if observed != expected {
        return Err(String::from("frame encode execution plan drifted"));
    }
    Ok(())
}

#[test]
fn frame_decode_defers_publication_until_validation() -> Result<(), String> {
    let operation = lower_frame_helper(&FrameHelperRequest {
        abi_id: String::from("malbolge-c32-v1"),
        identity: String::from("malbolge_guest_frame_decode"),
        runtime_id: String::from("malbolge-guest-runtime-v1"),
    })
    .map_err(|error| format!("lower frame decode: {error:?}"))?;
    let observed = realize_frame_helper(operation);
    let mut expected_steps = vec![
        FrameCodecExecutionStep::GuardWirePointerNonNull { failure_status: 1 },
        FrameCodecExecutionStep::GuardFramePointerNonNull { failure_status: 1 },
        FrameCodecExecutionStep::GuardWireSizeExact {
            bytes: 32,
            failure_status: 1,
        },
    ];
    expected_steps.extend(
        expected_frame_fields()
            .into_iter()
            .map(FrameCodecExecutionStep::DecodeFieldLittleEndian),
    );
    expected_steps.push(FrameCodecExecutionStep::ValidateFrameOrReturn(
        Box::new(frame_validation_plan()),
    ));
    expected_steps.push(FrameCodecExecutionStep::PublishDecodedFrameAtomically);
    expected_steps.push(FrameCodecExecutionStep::ReturnStatus(0));
    let expected = FrameHelperExecutionPlan::Decode { steps: expected_steps };
    if observed != expected {
        return Err(String::from("frame decode execution plan drifted"));
    }
    Ok(())
}

#[test]
fn frame_helper_identity_drift_fails_closed() -> Result<(), String> {
    let base = FrameHelperRequest {
        abi_id: String::from("malbolge-c32-v1"),
        identity: String::from("malbolge_guest_frame_validate"),
        runtime_id: String::from("malbolge-guest-runtime-v1"),
    };
    let mut wrong_abi = base.clone();
    wrong_abi.abi_id = String::from("host-abi");
    let mut wrong_runtime = base.clone();
    wrong_runtime.runtime_id = String::from("malbolge-guest-runtime-v2");
    let mut wrong_helper = base;
    wrong_helper.identity = String::from("malbolge_guest_frame_unknown");
    if lower_frame_helper(&wrong_abi)
        != Err(FrameHelperLoweringError::InvalidAuthority)
        || lower_frame_helper(&wrong_runtime)
            != Err(FrameHelperLoweringError::InvalidAuthority)
        || lower_frame_helper(&wrong_helper)
            != Err(FrameHelperLoweringError::UnsupportedIdentity)
    {
        return Err(String::from("frame-helper authority drift was accepted"));
    }
    Ok(())
}

#[test]
fn heap_init_authority_matches_guest_runtime() -> Result<(), String> {
    let contract = read_to_string(GUEST_RUNTIME_CONTRACT)
        .map_err(|error| format!("read guest-runtime contract: {error}"))?;
    let header = read_to_string(GUEST_RUNTIME_HEADER)
        .map_err(|error| format!("read guest-runtime header: {error}"))?;
    let source = read_to_string(GUEST_HEAP_SOURCE)
        .map_err(|error| format!("read guest heap source: {error}"))?;
    for expected in [
        "malbolge_guest_heap_init",
        "MIN_BLOCK_SPAN UINT32_C(32)",
        "heap->arena = (uint8_t *)arena",
        "heap->capacity = capacity",
        "heap->used = UINT32_C(0)",
        "heap->arena[index] = UINT8_C(0)",
    ] {
        if !source.contains(expected) {
            return Err(format!(
                "heap-init source authority missing {expected}"
            ));
        }
    }
    for expected in [
        "MALBOLGE_GUEST_HEAP_ALIGNMENT UINT32_C(16)",
        "MALBOLGE_GUEST_HEAP_HEADER_SIZE UINT32_C(16)",
        "MALBOLGE_GUEST_RUNTIME_VALID = 0",
        "MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT = 1",
    ] {
        if !header.contains(expected) {
            return Err(format!(
                "heap-init header authority missing {expected}"
            ));
        }
    }
    for expected in [
        "\"alignment\": 16",
        "\"header_bytes\": 16",
        "\"extent_domain\": \"u32-logical-bytes\"",
    ] {
        if !contract.contains(expected) {
            return Err(format!(
                "heap-init contract authority missing {expected}"
            ));
        }
    }
    Ok(())
}

#[test]
fn heap_init_realizes_exact_guard_and_mutation_order() -> Result<(), String> {
    let operation = lower_heap_helper(&HeapHelperRequest {
        abi_id: String::from("malbolge-c32-v1"),
        identity: String::from("malbolge_guest_heap_init"),
        runtime_id: String::from("malbolge-guest-runtime-v1"),
    })
    .map_err(|error| format!("lower heap init: {error:?}"))?;
    if operation
        != HeapHelperOperation::Initialize(HeapInitSemantics {
            alignment: 16,
            invalid_argument_status: 1,
            minimum_capacity: 32,
            valid_status: 0,
        })
    {
        return Err(String::from("heap-init semantics drifted"));
    }
    let expected = HeapHelperExecutionPlan::Initialize {
        steps: vec![
            HeapInitStep::GuardHeapPointerNonNull { failure_status: 1 },
            HeapInitStep::GuardArenaPointerNonNull { failure_status: 1 },
            HeapInitStep::GuardCapacityAtLeast {
                failure_status: 1,
                minimum: 32,
            },
            HeapInitStep::GuardCapacityAligned {
                alignment: 16,
                failure_status: 1,
            },
            HeapInitStep::GuardArenaPointerAligned {
                alignment: 16,
                failure_status: 1,
            },
            HeapInitStep::PublishArenaPointer,
            HeapInitStep::PublishCapacity,
            HeapInitStep::PublishUsedZero,
            HeapInitStep::ZeroArenaCapacityBytes,
            HeapInitStep::ReturnStatus(0),
        ],
    };
    if realize_heap_helper(operation) != expected {
        return Err(String::from("heap-init execution plan drifted"));
    }
    Ok(())
}

fn expected_heap_allocate_plan() -> HeapHelperExecutionPlan {
    HeapHelperExecutionPlan::Allocate {
        steps: vec![
            HeapAllocateStep::GuardResultPointerNonNull { failure_status: 1 },
            HeapAllocateStep::GuardHeapShape { failure_status: 1 },
            HeapAllocateStep::PublishResultNull,
            HeapAllocateStep::ValidateHeapChain { failure_status: 3 },
            HeapAllocateStep::ReturnIfSizeZero { status: 0 },
            HeapAllocateStep::ComputeRequiredSpan {
                alignment: 16,
                header_bytes: 16,
                overflow_status: 2,
            },
            HeapAllocateStep::ScanFirstFitFreeBlock {
                free_state: 0,
                on_match: vec![
                    HeapAllocateStep::SplitOrClaimFreeBlock {
                        allocated_state: 1,
                        minimum_remainder: 32,
                        reserved_value: 0,
                    },
                    HeapAllocateStep::PublishResultFromBlock {
                        header_bytes: 16,
                    },
                    HeapAllocateStep::ReturnStatus(0),
                ],
                read_failure_status: 3,
            },
            HeapAllocateStep::GuardTailExtentFits { failure_status: 2 },
            HeapAllocateStep::WriteAllocatedTailBlock {
                allocated_state: 1,
                reserved_value: 0,
            },
            HeapAllocateStep::PublishResultFromTail { header_bytes: 16 },
            HeapAllocateStep::PublishTailUsed,
            HeapAllocateStep::ReturnStatus(0),
        ],
    }
}

#[test]
fn heap_allocate_realizes_first_fit_and_tail_paths() -> Result<(), String> {
    let operation = lower_heap_helper(&HeapHelperRequest {
        abi_id: String::from("malbolge-c32-v1"),
        identity: String::from("malbolge_guest_heap_allocate"),
        runtime_id: String::from("malbolge-guest-runtime-v1"),
    })
    .map_err(|error| format!("lower heap allocate: {error:?}"))?;
    let semantics = HeapAllocateSemantics {
        alignment: 16,
        allocated_state: 1,
        corrupt_state_status: 3,
        header_bytes: 16,
        invalid_argument_status: 1,
        minimum_block_span: 32,
        out_of_memory_status: 2,
        reserved_value: 0,
        valid_status: 0,
    };
    if operation != HeapHelperOperation::Allocate(semantics) {
        return Err(String::from("heap-allocate semantics drifted"));
    }
    let expected = expected_heap_allocate_plan();
    if realize_heap_helper(operation) != expected {
        return Err(String::from("heap-allocate execution plan drifted"));
    }
    Ok(())
}

#[test]
fn heap_allocate_authority_matches_runtime_policy() -> Result<(), String> {
    let contract = read_to_string(GUEST_RUNTIME_CONTRACT)
        .map_err(|error| format!("read guest-runtime contract: {error}"))?;
    let header = read_to_string(GUEST_RUNTIME_HEADER)
        .map_err(|error| format!("read guest-runtime header: {error}"))?;
    let source = read_to_string(GUEST_HEAP_SOURCE)
        .map_err(|error| format!("read guest heap source: {error}"))?;
    for expected in [
        "malbolge_guest_heap_allocate",
        "*result = NULL",
        "if (!heap_chain_valid(heap))",
        "if (size == UINT32_C(0))",
        "split_or_claim(heap, block, required, size)",
        "heap->used = new_used",
    ] {
        if !source.contains(expected) {
            return Err(format!(
                "heap-allocate source authority missing {expected}"
            ));
        }
    }
    for expected in [
        "MALBOLGE_GUEST_HEAP_ALIGNMENT UINT32_C(16)",
        "MALBOLGE_GUEST_HEAP_HEADER_SIZE UINT32_C(16)",
        "MALBOLGE_GUEST_RUNTIME_OUT_OF_MEMORY = 2",
        "MALBOLGE_GUEST_RUNTIME_CORRUPT_STATE = 3",
    ] {
        if !header.contains(expected) {
            return Err(format!(
                "heap-allocate header authority missing {expected}"
            ));
        }
    }
    for expected in [
        "\"policy\": \"first-fit-split-coalesce-tail-trim\"",
        "\"zero_size_allocation\": \"null-success\"",
        "\"corrupt_chain\": \"reject-before-mutation-or-result-publication\"",
    ] {
        if !contract.contains(expected) {
            return Err(format!(
                "heap-allocate contract authority missing {expected}"
            ));
        }
    }
    Ok(())
}

#[test]
fn heap_allocate_zeroed_preserves_delegation_and_zeroing_order()
-> Result<(), String> {
    let operation = lower_heap_helper(&HeapHelperRequest {
        abi_id: String::from("malbolge-c32-v1"),
        identity: String::from("malbolge_guest_heap_allocate_zeroed"),
        runtime_id: String::from("malbolge-guest-runtime-v1"),
    })
    .map_err(|error| format!("lower heap allocate-zeroed: {error:?}"))?;
    let allocation = HeapAllocateSemantics {
        alignment: 16,
        allocated_state: 1,
        corrupt_state_status: 3,
        header_bytes: 16,
        invalid_argument_status: 1,
        minimum_block_span: 32,
        out_of_memory_status: 2,
        reserved_value: 0,
        valid_status: 0,
    };
    let semantics = HeapAllocateZeroedSemantics {
        allocation,
        invalid_argument_status: 1,
        out_of_memory_status: 2,
        valid_status: 0,
    };
    if operation != HeapHelperOperation::AllocateZeroed(semantics) {
        return Err(String::from("heap allocate-zeroed semantics drifted"));
    }
    let nested = expected_heap_allocate_plan();
    let expected = HeapHelperExecutionPlan::AllocateZeroed {
        steps: vec![
            HeapAllocateZeroedStep::GuardResultPointerNonNull {
                failure_status: 1,
            },
            HeapAllocateZeroedStep::PublishResultNull,
            HeapAllocateZeroedStep::DelegateZeroSizeAllocation(Box::new(
                nested.clone(),
            )),
            HeapAllocateZeroedStep::GuardProductFitsU32 { failure_status: 2 },
            HeapAllocateZeroedStep::AllocateTotalOrReturn(Box::new(nested)),
            HeapAllocateZeroedStep::ReturnUnlessAllocatedNonNull {
                valid_status: 0,
            },
            HeapAllocateZeroedStep::ZeroAllocatedPayloadBytes,
            HeapAllocateZeroedStep::ReturnStatus(0),
        ],
    };
    if realize_heap_helper(operation) != expected {
        return Err(String::from("heap allocate-zeroed execution drifted"));
    }
    Ok(())
}

#[test]
fn heap_allocate_zeroed_authority_matches_runtime_source() -> Result<(), String>
{
    let source = read_to_string(GUEST_HEAP_SOURCE)
        .map_err(|error| format!("read guest heap source: {error}"))?;
    for expected in [
        "malbolge_guest_heap_allocate_zeroed",
        "if (result == NULL)",
        "*result = NULL",
        "count == UINT32_C(0) || size == UINT32_C(0)",
        "count > UINT32_MAX / size",
        "total = count * size",
        "malbolge_guest_heap_allocate(heap, total, result)",
        "status != MALBOLGE_GUEST_RUNTIME_VALID || *result == NULL",
        "bytes[index] = UINT8_C(0)",
    ] {
        if !source.contains(expected) {
            return Err(format!(
                "heap allocate-zeroed source authority missing {expected}"
            ));
        }
    }
    Ok(())
}

#[test]
fn heap_release_realizes_preflight_coalesce_and_trim_order()
-> Result<(), String> {
    let operation = lower_heap_helper(&HeapHelperRequest {
        abi_id: String::from("malbolge-c32-v1"),
        identity: String::from("malbolge_guest_heap_release"),
        runtime_id: String::from("malbolge-guest-runtime-v1"),
    })
    .map_err(|error| format!("lower heap release: {error:?}"))?;
    let semantics = HeapReleaseSemantics {
        allocated_state: 1,
        corrupt_state_status: 3,
        free_state: 0,
        header_bytes: 16,
        invalid_argument_status: 1,
        valid_status: 0,
        zero_metadata_value: 0,
    };
    if operation != HeapHelperOperation::Release(semantics) {
        return Err(String::from("heap-release semantics drifted"));
    }
    let expected = HeapHelperExecutionPlan::Release {
        steps: vec![
            HeapReleaseStep::GuardHeapShape { failure_status: 1 },
            HeapReleaseStep::ValidateHeapChain { failure_status: 3 },
            HeapReleaseStep::ReturnIfPointerNull { status: 0 },
            HeapReleaseStep::FindAllocatedBlockOrReturn {
                allocated_state: 1,
                corrupt_status: 3,
                header_bytes: 16,
                invalid_argument_status: 1,
            },
            HeapReleaseStep::WriteLocatedBlockFree {
                free_state: 0,
                zero_metadata_value: 0,
            },
            HeapReleaseStep::CoalesceFreeBlocksOrReturn {
                corrupt_status: 3,
                free_state: 0,
            },
            HeapReleaseStep::TrimFreeTailOrReturn {
                corrupt_status: 3,
                free_state: 0,
                valid_status: 0,
            },
        ],
    };
    if realize_heap_helper(operation) != expected {
        return Err(String::from("heap-release execution plan drifted"));
    }
    Ok(())
}

#[test]
fn heap_release_authority_matches_runtime_source() -> Result<(), String> {
    let source = read_to_string(GUEST_HEAP_SOURCE)
        .map_err(|error| format!("read guest heap source: {error}"))?;
    for expected in [
        "malbolge_guest_heap_release",
        "if (!heap_shape_valid(heap))",
        "if (!heap_chain_valid(heap))",
        "if (pointer == NULL)",
        "find_allocated_block(heap, pointer, &block)",
        "write_block(heap->arena + block.offset, block.span, UINT32_C(0)",
        "status = coalesce_free_blocks(heap)",
        "return trim_free_tail(heap)",
    ] {
        if !source.contains(expected) {
            return Err(format!(
                "heap-release source authority missing {expected}"
            ));
        }
    }
    Ok(())
}

#[test]
fn heap_helper_identity_drift_fails_closed() -> Result<(), String> {
    let base = HeapHelperRequest {
        abi_id: String::from("malbolge-c32-v1"),
        identity: String::from("malbolge_guest_heap_init"),
        runtime_id: String::from("malbolge-guest-runtime-v1"),
    };
    let mut wrong_abi = base.clone();
    wrong_abi.abi_id = String::from("host-abi");
    let mut wrong_runtime = base.clone();
    wrong_runtime.runtime_id = String::from("malbolge-guest-runtime-v2");
    let mut wrong_helper = base;
    wrong_helper.identity = String::from("malbolge_guest_heap_resize");
    if lower_heap_helper(&wrong_abi)
        != Err(HeapHelperLoweringError::InvalidAuthority)
        || lower_heap_helper(&wrong_runtime)
            != Err(HeapHelperLoweringError::InvalidAuthority)
        || lower_heap_helper(&wrong_helper)
            != Err(HeapHelperLoweringError::UnsupportedIdentity)
    {
        return Err(String::from("heap-helper authority drift was accepted"));
    }
    Ok(())
}

#[test]
fn runtime_helper_authority_matches_guest_runtime() -> Result<(), String> {
    let contract = read_to_string(GUEST_RUNTIME_CONTRACT)
        .map_err(|error| format!("read guest-runtime contract: {error}"))?;
    let header = read_to_string(GUEST_RUNTIME_HEADER)
        .map_err(|error| format!("read guest-runtime header: {error}"))?;
    let source = read_to_string(GUEST_BYTE_STREAM_SOURCE)
        .map_err(|error| format!("read byte-stream source: {error}"))?;
    for expected in [
        "malbolge_guest_decode_input_word",
        "malbolge_guest_output_byte",
    ] {
        if !header.contains(expected) || !source.contains(expected) {
            return Err(format!("runtime helper authority missing {expected}"));
        }
    }
    for expected in [
        "profile-byte-word-or-eof-to-int32-byte-or-minus-one",
        "low-eight-bits",
        "forbidden",
    ] {
        if !contract.contains(expected) {
            return Err(format!("runtime helper contract missing {expected}"));
        }
    }
    for expected in [
        "MALBOLGE_GUEST_RUNTIME_VALID = 0",
        "MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT = 1",
        "MALBOLGE_GUEST_RUNTIME_INVALID_INPUT_WORD = 4",
    ] {
        if !header.contains(expected) {
            return Err(format!("runtime helper status missing {expected}"));
        }
    }
    Ok(())
}

#[test]
fn pure_byte_stream_helpers_lower_to_declarative_semantics()
-> Result<(), String> {
    let profile = current_profile_io();
    let input = RuntimeHelperRequest {
        identity: String::from("malbolge_guest_decode_input_word"),
        target_profile: String::from("malbolge-2026"),
    };
    let output = RuntimeHelperRequest {
        identity: String::from("malbolge_guest_output_byte"),
        target_profile: String::from("malbolge-2026"),
    };
    if lower_runtime_helper(&input, &profile)
        != Ok(RuntimeHelperOperation::DecodeInputWord(Box::new(
            InputWordDecodeSemantics {
                byte_max: 255,
                eof_value_bits: u32::MAX,
                eof_word: current_profile().eof_word(),
                invalid_argument_status: 1,
                invalid_input_status: 4,
                valid_status: 0,
            },
        )))
        || lower_runtime_helper(&output, &profile)
            != Ok(RuntimeHelperOperation::OutputByte { mask: 255 })
    {
        return Err(String::from("pure runtime-helper semantics drifted"));
    }
    Ok(())
}

#[test]
fn input_helper_control_flow_publishes_exact_exits() -> Result<(), String> {
    let profile = current_profile_io();
    let operation = lower_runtime_helper(
        &RuntimeHelperRequest {
            identity: String::from("malbolge_guest_decode_input_word"),
            target_profile: String::from("malbolge-2026"),
        },
        &profile,
    )
    .map_err(|error| format!("lower input helper: {error:?}"))?;
    let observed = realize_runtime_helper(&operation);
    let expected = RuntimeHelperExecutionPlan::DecodeInputWord(Box::new(
        InputWordDecodeControlFlow {
            exits: vec![
                InputDecodeArm {
                    condition: InputDecodeCondition::ResultPointerNull,
                    result: InputDecodeResult::Unchanged,
                    status: 1,
                },
                InputDecodeArm {
                    condition: InputDecodeCondition::WordAtMost(255),
                    result: InputDecodeResult::InputWordAsI32,
                    status: 0,
                },
                InputDecodeArm {
                    condition: InputDecodeCondition::WordEquals(
                        current_profile().eof_word(),
                    ),
                    result: InputDecodeResult::ConstantI32Bits(u32::MAX),
                    status: 0,
                },
                InputDecodeArm {
                    condition: InputDecodeCondition::Otherwise,
                    result: InputDecodeResult::Unchanged,
                    status: 4,
                },
            ],
        },
    ));
    if observed != expected {
        return Err(String::from("input-helper control flow drifted"));
    }
    Ok(())
}

#[test]
fn output_helper_execution_preserves_low_byte_mask() -> Result<(), String> {
    let operation = lower_runtime_helper(
        &RuntimeHelperRequest {
            identity: String::from("malbolge_guest_output_byte"),
            target_profile: String::from("malbolge-2026"),
        },
        &current_profile_io(),
    )
    .map_err(|error| format!("lower output helper: {error:?}"))?;
    if realize_runtime_helper(&operation)
        != (RuntimeHelperExecutionPlan::OutputByte { mask: 255 })
    {
        return Err(String::from("output-helper execution mask drifted"));
    }
    Ok(())
}

#[test]
fn runtime_helper_identity_or_profile_drift_fails_closed() -> Result<(), String>
{
    let profile = current_profile_io();
    let unknown = RuntimeHelperRequest {
        identity: String::from("host_getchar"),
        target_profile: String::from("malbolge-2026"),
    };
    let wrong_profile = RuntimeHelperRequest {
        identity: String::from("malbolge_guest_decode_input_word"),
        target_profile: String::from("malbolge-1998"),
    };
    let mut drifted_projection = profile.clone();
    drifted_projection.profile_id = String::from("malbolge-2026.3");
    let mut ambiguous_eof = profile.clone();
    ambiguous_eof.eof_word = 255;
    if lower_runtime_helper(&unknown, &profile)
        != Err(RuntimeHelperLoweringError::UnsupportedIdentity)
        || lower_runtime_helper(&wrong_profile, &profile)
            != Err(RuntimeHelperLoweringError::UnsupportedProfile)
        || lower_runtime_helper(
            &RuntimeHelperRequest {
                identity: String::from("malbolge_guest_output_byte"),
                target_profile: String::from("malbolge-2026"),
            },
            &drifted_projection,
        ) != Err(RuntimeHelperLoweringError::UnsupportedProfile)
        || lower_runtime_helper(
            &RuntimeHelperRequest {
                identity: String::from("malbolge_guest_decode_input_word"),
                target_profile: String::from("malbolge-2026"),
            },
            &ambiguous_eof,
        ) != Err(RuntimeHelperLoweringError::UnsupportedProfile)
    {
        return Err(String::from("runtime-helper drift was not rejected"));
    }
    Ok(())
}

#[test]
fn byte_stream_wrapper_authority_matches_libc_source() -> Result<(), String> {
    let libc = read_to_string(LIBC_CONTRACT)
        .map_err(|error| format!("read libc contract: {error}"))?;
    let source = read_to_string(GUEST_STDIO_SOURCE)
        .map_err(|error| format!("read guest stdio source: {error}"))?;
    for expected in [
        "\"name\": \"getchar\"",
        "\"name\": \"putchar\"",
        "guest-byte-input-or-minus-one-eof",
        "guest-low-eight-bit-output-or-minus-one-failure",
    ] {
        if !libc.contains(expected) {
            return Err(format!(
                "libc byte-stream authority missing {expected}"
            ));
        }
    }
    let input_intrinsic = source
        .find("malbolge_guest_intrinsic_input_word")
        .ok_or_else(|| String::from("getchar input intrinsic missing"))?;
    let input_helper = source
        .find("malbolge_guest_decode_input_word")
        .ok_or_else(|| String::from("getchar decode helper missing"))?;
    let output_helper = source
        .find("malbolge_guest_output_byte")
        .ok_or_else(|| String::from("putchar output helper missing"))?;
    let output_intrinsic = source
        .find("malbolge_guest_intrinsic_output_byte")
        .ok_or_else(|| String::from("putchar output intrinsic missing"))?;
    if input_intrinsic >= input_helper || output_helper >= output_intrinsic {
        return Err(String::from("guest stdio wrapper order drifted"));
    }
    Ok(())
}

#[test]
fn byte_stream_wrapper_plans_preserve_guest_order() -> Result<(), String> {
    let profile = current_profile_io();
    let getchar = plan_byte_stream_wrapper(
        &ByteStreamWrapperRequest {
            identity: String::from("getchar"),
            target_profile: String::from("malbolge-2026"),
        },
        &profile,
    )
    .map_err(|error| format!("plan getchar: {error:?}"))?;
    if getchar.identity != "getchar"
        || getchar.intrinsic != RuntimeIntrinsicOperation::InputWord
        || getchar.order != ByteStreamWrapperOrder::IntrinsicThenHelper
        || getchar.return_kind != ByteStreamWrapperReturn::DecodedI32OrEof
        || getchar.helper
            != RuntimeHelperOperation::DecodeInputWord(Box::new(
                InputWordDecodeSemantics {
                    byte_max: 255,
                    eof_value_bits: u32::MAX,
                    eof_word: current_profile().eof_word(),
                    invalid_argument_status: 1,
                    invalid_input_status: 4,
                    valid_status: 0,
                },
            ))
    {
        return Err(String::from("getchar semantic plan drifted"));
    }
    let putchar = plan_byte_stream_wrapper(
        &ByteStreamWrapperRequest {
            identity: String::from("putchar"),
            target_profile: String::from("malbolge-2026"),
        },
        &profile,
    )
    .map_err(|error| format!("plan putchar: {error:?}"))?;
    if putchar.identity != "putchar"
        || putchar.helper != (RuntimeHelperOperation::OutputByte { mask: 255 })
        || putchar.intrinsic != RuntimeIntrinsicOperation::OutputByte
        || putchar.order != ByteStreamWrapperOrder::HelperThenIntrinsic
        || putchar.return_kind != ByteStreamWrapperReturn::EmittedByteAsI32
    {
        return Err(String::from("putchar semantic plan drifted"));
    }
    Ok(())
}

#[test]
fn byte_stream_wrapper_plan_rejects_drift() -> Result<(), String> {
    let profile = current_profile_io();
    let unknown = ByteStreamWrapperRequest {
        identity: String::from("host_getchar"),
        target_profile: String::from("malbolge-2026"),
    };
    let wrong_profile = ByteStreamWrapperRequest {
        identity: String::from("getchar"),
        target_profile: String::from("malbolge-1998"),
    };
    let mut ambiguous_eof = profile.clone();
    ambiguous_eof.eof_word = 255;
    if plan_byte_stream_wrapper(&unknown, &profile)
        != Err(ByteStreamWrapperPlanningError::UnsupportedIdentity)
        || plan_byte_stream_wrapper(&wrong_profile, &profile)
            != Err(ByteStreamWrapperPlanningError::UnsupportedProfile)
        || plan_byte_stream_wrapper(
            &ByteStreamWrapperRequest {
                identity: String::from("getchar"),
                target_profile: String::from("malbolge-2026"),
            },
            &ambiguous_eof,
        ) != Err(ByteStreamWrapperPlanningError::InvalidProfileProjection)
    {
        return Err(String::from("byte-stream wrapper drift was not rejected"));
    }
    Ok(())
}

#[test]
fn byte_stream_wrapper_machine_io_uses_current_profile() -> Result<(), String> {
    let profile = current_profile_io();
    let getchar = plan_byte_stream_wrapper(
        &ByteStreamWrapperRequest {
            identity: String::from("getchar"),
            target_profile: String::from("malbolge-2026"),
        },
        &profile,
    )
    .map_err(|error| format!("plan getchar: {error:?}"))?;
    let realized_getchar = realize_byte_stream_wrapper(&getchar, &profile)
        .map_err(|error| format!("realize getchar: {error:?}"))?;
    if realized_getchar.helper != getchar.helper
        || realized_getchar.helper_execution
            != realize_runtime_helper(&getchar.helper)
        || realized_getchar.identity != getchar.identity
        || realized_getchar.order != getchar.order
        || realized_getchar.return_kind != getchar.return_kind
        || realized_getchar.machine_io
            != (MachineIoOperation {
                eof_word: Some(current_profile().eof_word()),
                instruction: current_profile().input_instruction(),
                kind: MachineIoKind::InputWord,
            })
    {
        return Err(String::from("getchar machine-I/O realization drifted"));
    }
    let putchar = plan_byte_stream_wrapper(
        &ByteStreamWrapperRequest {
            identity: String::from("putchar"),
            target_profile: String::from("malbolge-2026"),
        },
        &profile,
    )
    .map_err(|error| format!("plan putchar: {error:?}"))?;
    let realized_putchar = realize_byte_stream_wrapper(&putchar, &profile)
        .map_err(|error| format!("realize putchar: {error:?}"))?;
    if realized_putchar.helper != putchar.helper
        || realized_putchar.helper_execution
            != realize_runtime_helper(&putchar.helper)
        || realized_putchar.identity != putchar.identity
        || realized_putchar.order != putchar.order
        || realized_putchar.return_kind != putchar.return_kind
        || realized_putchar.machine_io
            != (MachineIoOperation {
                eof_word: None,
                instruction: current_profile().output_instruction(),
                kind: MachineIoKind::OutputByte,
            })
    {
        return Err(String::from("putchar machine-I/O realization drifted"));
    }
    Ok(())
}

#[test]
fn getchar_control_flow_is_explicit() -> Result<(), String> {
    let profile = current_profile_io();
    let semantic = plan_byte_stream_wrapper(
        &ByteStreamWrapperRequest {
            identity: String::from("getchar"),
            target_profile: String::from("malbolge-2026"),
        },
        &profile,
    )
    .map_err(|error| format!("plan getchar: {error:?}"))?;
    let machine = realize_byte_stream_wrapper(&semantic, &profile)
        .map_err(|error| format!("realize getchar: {error:?}"))?;
    let observed = realize_byte_stream_control_flow(&machine, &profile)
        .map_err(|error| format!("realize getchar control flow: {error:?}"))?;
    let expected = ByteStreamWrapperExecutionPlan {
        identity: String::from("getchar"),
        steps: vec![
            ByteStreamWrapperExecutionStep::InitializeI32 { bits: u32::MAX },
            ByteStreamWrapperExecutionStep::MachineIo(machine.machine_io),
            ByteStreamWrapperExecutionStep::RuntimeHelper(Box::new(
                machine.helper_execution,
            )),
            ByteStreamWrapperExecutionStep::StatusGuard {
                accepted_status: 0,
                failure_return_bits: u32::MAX,
            },
            ByteStreamWrapperExecutionStep::ReturnDecodedI32,
        ],
    };
    if observed != expected {
        return Err(String::from("getchar control-flow plan drifted"));
    }
    Ok(())
}

#[test]
fn putchar_control_flow_is_explicit() -> Result<(), String> {
    let profile = current_profile_io();
    let semantic = plan_byte_stream_wrapper(
        &ByteStreamWrapperRequest {
            identity: String::from("putchar"),
            target_profile: String::from("malbolge-2026"),
        },
        &profile,
    )
    .map_err(|error| format!("plan putchar: {error:?}"))?;
    let machine = realize_byte_stream_wrapper(&semantic, &profile)
        .map_err(|error| format!("realize putchar: {error:?}"))?;
    let observed = realize_byte_stream_control_flow(&machine, &profile)
        .map_err(|error| format!("realize putchar control flow: {error:?}"))?;
    let expected = ByteStreamWrapperExecutionPlan {
        identity: String::from("putchar"),
        steps: vec![
            ByteStreamWrapperExecutionStep::RuntimeHelper(Box::new(
                machine.helper_execution,
            )),
            ByteStreamWrapperExecutionStep::MachineIo(machine.machine_io),
            ByteStreamWrapperExecutionStep::ReturnEmittedByteAsI32,
        ],
    };
    if observed != expected {
        return Err(String::from("putchar control-flow plan drifted"));
    }
    Ok(())
}

#[test]
fn byte_stream_wrapper_control_flow_rejects_forgery() -> Result<(), String> {
    let profile = current_profile_io();
    let semantic = plan_byte_stream_wrapper(
        &ByteStreamWrapperRequest {
            identity: String::from("getchar"),
            target_profile: String::from("malbolge-2026"),
        },
        &profile,
    )
    .map_err(|error| format!("plan getchar: {error:?}"))?;
    let machine = realize_byte_stream_wrapper(&semantic, &profile)
        .map_err(|error| format!("realize getchar: {error:?}"))?;
    let mut forged = machine.clone();
    forged.helper_execution =
        RuntimeHelperExecutionPlan::OutputByte { mask: 255 };
    if realize_byte_stream_control_flow(&forged, &profile)
        != Err(ByteStreamControlFlowError::InvalidPlan)
    {
        return Err(String::from("forged helper execution was not rejected"));
    }
    let mut wrong_profile = profile;
    wrong_profile.profile_id = String::from("malbolge-1998");
    if realize_byte_stream_control_flow(&machine, &wrong_profile)
        != Err(ByteStreamControlFlowError::InvalidProfile)
    {
        return Err(String::from(
            "wrapper control-flow profile drift accepted",
        ));
    }
    Ok(())
}

#[test]
fn byte_stream_wrapper_machine_io_rejects_forgery() -> Result<(), String> {
    let profile = current_profile_io();
    let mut forged = plan_byte_stream_wrapper(
        &ByteStreamWrapperRequest {
            identity: String::from("getchar"),
            target_profile: String::from("malbolge-2026"),
        },
        &profile,
    )
    .map_err(|error| format!("plan getchar: {error:?}"))?;
    forged.order = ByteStreamWrapperOrder::HelperThenIntrinsic;
    if realize_byte_stream_wrapper(&forged, &profile)
        != Err(ByteStreamWrapperRealizationError::InvalidPlan)
    {
        return Err(String::from("forged wrapper order was not rejected"));
    }
    let valid = plan_byte_stream_wrapper(
        &ByteStreamWrapperRequest {
            identity: String::from("getchar"),
            target_profile: String::from("malbolge-2026"),
        },
        &profile,
    )
    .map_err(|error| format!("re-plan getchar: {error:?}"))?;
    let mut colliding = profile;
    colliding.output_instruction = colliding.input_instruction;
    if realize_byte_stream_wrapper(&valid, &colliding)
        != Err(ByteStreamWrapperRealizationError::InvalidProfile)
    {
        return Err(String::from("colliding wrapper profile was not rejected"));
    }
    Ok(())
}

fn current_profile_io() -> TargetProfileIo {
    let profile = current_profile();
    TargetProfileIo {
        eof_word: profile.eof_word(),
        input_instruction: profile.input_instruction(),
        output_instruction: profile.output_instruction(),
        profile_id: String::from(profile.id()),
    }
}

#[test]
fn machine_io_cells_round_trip_every_decode_phase() -> Result<(), String> {
    let projection = current_profile_io();
    let decoder = VmProfileInstructionDecoder;
    for code_pointer in 0u32..94u32 {
        for semantic in [
            RuntimeIntrinsicOperation::InputWord,
            RuntimeIntrinsicOperation::OutputByte,
        ] {
            let operation = realize_runtime_io(semantic, &projection)
                .map_err(|error| format!("realize machine I/O: {error:?}"))?;
            let encoded = encode_machine_io(operation, code_pointer, &decoder)
                .map_err(|error| format!("encode machine I/O: {error:?}"))?;
            if !(33..=126).contains(&encoded.source_cell)
                || encoded.code_pointer != code_pointer
                || encoded.operation != operation
                || decoder.decode(u32::from(encoded.source_cell), code_pointer)
                    != Some(operation.instruction)
            {
                return Err(format!(
                    "machine I/O round trip drifted at phase {code_pointer}",
                ));
            }
        }
    }
    Ok(())
}

#[test]
fn machine_io_encoder_rejects_broken_decoder_ports() -> Result<(), String> {
    let operation = realize_runtime_io(
        RuntimeIntrinsicOperation::InputWord,
        &current_profile_io(),
    )
    .map_err(|error| format!("realize machine I/O: {error:?}"))?;
    if encode_machine_io(operation, 0, &MissingInstructionDecoder)
        != Err(MachineIoEncodingError::MissingEncoding)
    {
        return Err(String::from("missing inverse encoding was not rejected"));
    }
    if encode_machine_io(operation, 0, &AmbiguousInstructionDecoder)
        != Err(MachineIoEncodingError::AmbiguousEncoding)
    {
        return Err(String::from(
            "ambiguous inverse encoding was not rejected",
        ));
    }
    Ok(())
}

#[test]
fn current_profile_realizes_runtime_io_from_authority() -> Result<(), String> {
    let profile = current_profile();
    let projection = current_profile_io();
    let input =
        realize_runtime_io(RuntimeIntrinsicOperation::InputWord, &projection)
            .map_err(|error| format!("realize input word: {error:?}"))?;
    let output =
        realize_runtime_io(RuntimeIntrinsicOperation::OutputByte, &projection)
            .map_err(|error| format!("realize output byte: {error:?}"))?;
    if input
        != (MachineIoOperation {
            eof_word: Some(profile.eof_word()),
            instruction: profile.input_instruction(),
            kind: MachineIoKind::InputWord,
        })
        || output
            != (MachineIoOperation {
                eof_word: None,
                instruction: profile.output_instruction(),
                kind: MachineIoKind::OutputByte,
            })
    {
        return Err(String::from(
            "profile-derived machine I/O realization drifted",
        ));
    }
    Ok(())
}

#[test]
fn malformed_profile_io_projection_fails_closed() -> Result<(), String> {
    let mut projection = current_profile_io();
    projection.output_instruction = projection.input_instruction;
    if realize_runtime_io(RuntimeIntrinsicOperation::InputWord, &projection)
        != Err(RuntimeIoRealizationError::InvalidProjection)
    {
        return Err(String::from(
            "colliding profile opcodes were not rejected",
        ));
    }
    projection = current_profile_io();
    projection.profile_id = String::from("malbolge-1998");
    if realize_runtime_io(RuntimeIntrinsicOperation::OutputByte, &projection)
        != Err(RuntimeIoRealizationError::UnsupportedProfile)
    {
        return Err(String::from("profile identity drift was not rejected"));
    }
    Ok(())
}

#[test]
fn raw_byte_io_intrinsic_identities_lower_exactly() -> Result<(), String> {
    let input = RuntimeIntrinsicRequest {
        identity: String::from("malbolge_guest_intrinsic_input_word"),
        target_profile: String::from("malbolge-2026"),
    };
    let output = RuntimeIntrinsicRequest {
        identity: String::from("malbolge_guest_intrinsic_output_byte"),
        target_profile: String::from("malbolge-2026"),
    };
    if lower_runtime_intrinsic(&input)
        != Ok(RuntimeIntrinsicOperation::InputWord)
        || lower_runtime_intrinsic(&output)
            != Ok(RuntimeIntrinsicOperation::OutputByte)
    {
        return Err(String::from(
            "runtime intrinsic identity lowering drifted",
        ));
    }
    Ok(())
}

#[test]
fn raw_intrinsic_identity_or_profile_drift_fails_closed() -> Result<(), String>
{
    let unknown = RuntimeIntrinsicRequest {
        identity: String::from("host_getchar"),
        target_profile: String::from("malbolge-2026"),
    };
    let wrong_profile = RuntimeIntrinsicRequest {
        identity: String::from("malbolge_guest_intrinsic_input_word"),
        target_profile: String::from("malbolge-1998"),
    };
    if lower_runtime_intrinsic(&unknown)
        != Err(RuntimeIntrinsicLoweringError::UnsupportedIdentity)
        || lower_runtime_intrinsic(&wrong_profile)
            != Err(RuntimeIntrinsicLoweringError::UnsupportedProfile)
    {
        return Err(String::from("runtime intrinsic drift was not rejected"));
    }
    Ok(())
}

#[test]
fn returning_byte_value_as_i32_fails_closed() -> Result<(), String> {
    let mut input = projected_byte_io_fixture()?;
    let block = input
        .functions
        .first_mut()
        .and_then(|function| function.blocks.first_mut())
        .ok_or_else(|| String::from("byte-I/O projection has no block"))?;
    let InputTerminator::Return { value, .. } = &mut block.terminator else {
        return Err(String::from("byte-I/O projection has no return"));
    };
    *value = Some(0);
    if lower_typed_ir(&input)
        != Err(TernaryLoweringError::UnsupportedTerminator)
    {
        return Err(String::from("byte value return was not rejected"));
    }
    Ok(())
}

#[test]
fn unsupported_typed_ir_shape_fails_closed() -> Result<(), String> {
    let module = admitted_golden(SELECT_GOLDEN)?;
    let input = project_typed_ir(&module)?;
    let observed = lower_typed_ir(&input);
    if !matches!(
        observed,
        Err(TernaryLoweringError::UnsupportedFunction
            | TernaryLoweringError::UnsupportedInstruction
            | TernaryLoweringError::UnsupportedModule)
    ) {
        return Err(format!(
            "unsupported typed IR was not rejected: {observed:?}"
        ));
    }
    Ok(())
}
