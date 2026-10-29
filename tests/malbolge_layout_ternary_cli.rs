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
//   - External-process end-to-end canonical ternary echo artifact evidence.
// - Must-Not:
//   - Claim host callbacks, general C lowering, or EOF equivalence.
// - Allows:
//   - Inputs: canonical MCTR bytes and bounded hostile input wire files.
//   - Outputs: exact profile-bound raw/capsule source admission and VM traces.
//   - Side effects: owned isolated ignored temp file fixtures only.
// - Split-When:
//   - General ternary-to-layout operations require separate semantic proofs.
// - Merge-When:
//   - A complete typed-C compiler integration subsumes this limited bridge.
// - Summary:
//   - Proves ternary wire-to-file-to-VM successful byte I/O end to end.
// - Description:
//   - Tests exact byte I/O, tamper rejection and fail-closed publication.
// - Usage:
//   - `cargo test --test malbolge_layout_ternary_cli`.
// - Defaults:
//   - No guest computation is executed by the host in place of Malbolge.
//
//! Real executable artifact evidence for the bounded ternary byte-echo bridge.

#[path = "../src/compiler/byte-echo-bridge/composition/lib.rs"]
pub mod bridge;

use std::fs::{self, OpenOptions};
use std::path::{Path, PathBuf};
use std::process::{Command, Output, id};
use std::sync::atomic::{AtomicUsize, Ordering};

use bridge::ternary::{
    TernaryFunction, TernaryOperation, TernaryProgram, TernarySourcePosition, TernarySourceSpan,
    canonical_ternary_bytes,
};
use malbolge::{ProfileMachine, RunOutcome, current_profile, parse_capsule};

const EXECUTABLE: &str = env!("CARGO_BIN_EXE_malbolge_layout");
const MAX_WIRE_BYTES: u64 = 1_048_576;
static FIXTURE_SEQUENCE: AtomicUsize = AtomicUsize::new(0);

#[derive(Clone, Copy)]
enum TraceEffect {
    Read(u32),
    Write(u32),
}

type TestResult<T> = Result<T, String>;

struct Fixture {
    root: PathBuf,
}

impl Fixture {
    fn new() -> TestResult<Self> {
        let sequence = FIXTURE_SEQUENCE.fetch_add(1, Ordering::Relaxed);
        let root = Path::new(env!("CARGO_MANIFEST_DIR"))
            .join(".temp")
            .join(format!("layout-ternary-cli-{}-{sequence}", id()));
        #[expect(clippy::create_dir, reason = "do not reuse a pre-existing fixture")]
        fs::create_dir(&root).map_err(|error| format!("fixture create: {error}"))?;
        Ok(Self { root })
    }

    fn path(&self, name: &str) -> PathBuf {
        self.root.join(name)
    }
}

#[expect(clippy::missing_trait_methods, reason = "drop owns fixture cleanup")]
impl Drop for Fixture {
    fn drop(&mut self) {
        drop(fs::remove_dir_all(&self.root));
    }
}

const fn position(byte: u32) -> TernarySourcePosition {
    TernarySourcePosition {
        byte,
        column: byte.saturating_add(1),
        line: 1,
    }
}

const fn span(start: u32, end: u32) -> TernarySourceSpan {
    TernarySourceSpan {
        begin: position(start),
        end: position(end),
    }
}

fn echoed_program(pair_count: usize) -> TestResult<TernaryProgram> {
    let mut operations = Vec::new();
    for index in 0..pair_count {
        let byte = u32::try_from(index.saturating_mul(2))
            .map_err(|error| format!("source position: {error}"))?;
        let result = u32::try_from(index).map_err(|error| format!("result position: {error}"))?;
        operations.push(TernaryOperation::ByteInput {
            result,
            span: span(byte, byte.saturating_add(1)),
        });
        operations.push(TernaryOperation::ByteOutput {
            span: span(byte.saturating_add(1), byte.saturating_add(2)),
            value: result,
        });
    }
    let end = u32::try_from(pair_count.saturating_mul(2).saturating_add(1))
        .map_err(|error| format!("return position: {error}"))?;
    operations.push(TernaryOperation::ReturnVoid {
        span: span(end.saturating_sub(1), end),
    });
    Ok(TernaryProgram {
        abi_id: String::from("malbolge-c32-v1"),
        functions: vec![TernaryFunction {
            id: 0,
            name: String::from("echo"),
            operations,
            span: span(0, end),
        }],
        input_format_version: 1,
        source_id: String::from("fixtures/byte-echo.c"),
        source_sha256: [0x56; 32],
        target_profile: String::from("malbolge-2026"),
    })
}

fn invoke(profile: &str, target: &Path, wire: &Path, capsule: bool) -> TestResult<Output> {
    let mut command = Command::new(EXECUTABLE);
    let _args = command
        .arg("--profile")
        .arg(profile)
        .arg("--output")
        .arg(target);
    if capsule {
        let _capsule = command.arg("--capsule");
    }
    command
        .arg("--")
        .arg("--ternary-file")
        .arg(wire)
        .output()
        .map_err(|error| format!("artifact CLI invocation: {error}"))
}

fn save_wire(path: &Path, program: &TernaryProgram) -> TestResult<Vec<u8>> {
    let bytes = canonical_ternary_bytes(program)
        .map_err(|error| format!("canonical ternary source: {error:?}"))?;
    fs::write(path, &bytes).map_err(|error| format!("write test wire: {error}"))?;
    Ok(bytes)
}

#[test]
#[expect(clippy::panic_in_result_fn, reason = "real VM output is asserted")]
#[expect(
    clippy::cognitive_complexity,
    reason = "one external compiler artifact is independently checked in both formats"
)]
fn canonical_ternary_wire_emits_raw_file_and_profile_capsule() -> TestResult<()> {
    let fixture = Fixture::new()?;
    let program = echoed_program(3)?;
    let wire = fixture.path("echo.mctr");
    let _wire_bytes = save_wire(&wire, &program)?;
    let raw = fixture.path("echo-raw.malbolge");
    let capsule_path = fixture.path("echo-capsule.malbolge");
    let raw_result = invoke("malbolge-2026", &raw, &wire, false)?;
    assert!(
        raw_result.status.success(),
        "{}",
        String::from_utf8_lossy(&raw_result.stderr)
    );
    let raw_source = fs::read(&raw).map_err(|error| error.to_string())?;
    assert_eq!(raw_source.len(), 7);
    let capsule_result = invoke("malbolge-2026", &capsule_path, &wire, true)?;
    assert!(
        capsule_result.status.success(),
        "{}",
        String::from_utf8_lossy(&capsule_result.stderr)
    );
    let frame = fs::read(&capsule_path).map_err(|error| error.to_string())?;
    let capsule = parse_capsule(&frame)
        .map_err(|error| format!("independent capsule parse: {error:?}"))?
        .ok_or("missing capsule")?;
    assert_eq!(capsule.profile().id(), current_profile().id());
    assert_eq!(
        capsule.profile().fingerprint(),
        current_profile().fingerprint()
    );
    assert_eq!(capsule.payload(), raw_source);
    let mut vm =
        ProfileMachine::from_source(capsule.profile(), capsule.payload(), vec![0, 173, 255])
            .map_err(|error| format!("independent VM load: {error:?}"))?;
    assert!(matches!(
        vm.run(7),
        Ok(RunOutcome::Terminated { steps: 7, .. })
    ));
    assert_eq!(vm.output(), &[0, 173, 255]);
    assert_eq!(vm.input_consumed(), 3);
    Ok(())
}

#[test]
#[expect(clippy::panic_in_result_fn, reason = "canonical wire tamper rejection")]
fn forged_wire_and_target_profile_cannot_publish() -> TestResult<()> {
    let fixture = Fixture::new()?;
    let program = echoed_program(2)?;
    let wire = fixture.path("echo.mctr");
    let original = save_wire(&wire, &program)?;
    let target = fixture.path("should-not-exist.malbolge");
    let wrong_profile = invoke("malbolge-1998", &target, &wire, false)?;
    assert!(!wrong_profile.status.success());
    assert!(!target.exists());
    let mut altered = original;
    if let Some(last) = altered.last_mut() {
        *last ^= 0x80;
    }
    fs::write(&wire, &altered).map_err(|error| error.to_string())?;
    let invalid = invoke("malbolge-2026", &target, &wire, true)?;
    assert!(!invalid.status.success());
    assert!(!target.exists());
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "effect rejection precedes publication"
)]
fn valid_but_unsupported_ternary_operation_is_rejected() -> TestResult<()> {
    let fixture = Fixture::new()?;
    let mut program = echoed_program(2)?;
    let function = program.functions.first_mut().ok_or("missing function")?;
    let output = function
        .operations
        .get_mut(3)
        .ok_or("missing second output")?;
    if let TernaryOperation::ByteOutput { value, .. } = output {
        *value = 0;
    }
    // The earlier SSA byte is defined and correctly typed, so the canonical
    // decoder accepts it; only the narrower adjacent-echo bridge rejects it.
    let wire = fixture.path("unsupported.mctr");
    let _bytes = save_wire(&wire, &program)?;
    let target = fixture.path("unsupported.malbolge");
    let refused = invoke("malbolge-2026", &target, &wire, false)?;
    assert!(!refused.status.success());
    assert!(!target.exists());
    assert!(String::from_utf8_lossy(&refused.stderr).contains("UnsupportedEffectTrace"));
    Ok(())
}

#[test]
#[expect(clippy::panic_in_result_fn, reason = "hard byte bound and path guard")]
fn oversized_ternary_wire_is_rejected_without_creating_output() -> TestResult<()> {
    let fixture = Fixture::new()?;
    let wire = fixture.path("oversized.mctr");
    let file = OpenOptions::new()
        .create_new(true)
        .write(true)
        .open(&wire)
        .map_err(|error| error.to_string())?;
    file.set_len(MAX_WIRE_BYTES.saturating_add(1))
        .map_err(|error| error.to_string())?;
    let target = fixture.path("missing.malbolge");
    let refused = invoke("malbolge-2026", &target, &wire, true)?;
    assert!(!refused.status.success());
    assert!(!target.exists());
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "real CLI refusal preserves owned target"
)]
fn missing_empty_extra_argument_and_existing_target_fail_closed() -> TestResult<()> {
    let fixture = Fixture::new()?;
    let wire = fixture.path("valid.mctr");
    let _bytes = save_wire(&wire, &echoed_program(1)?)?;
    let missing = fixture.path("missing.mctr");
    let new_target = fixture.path("new.malbolge");
    let absent = invoke("malbolge-2026", &new_target, &missing, true)?;
    assert!(!absent.status.success());
    assert!(!new_target.exists());

    let empty = fixture.path("empty.mctr");
    fs::write(&empty, b"").map_err(|error| error.to_string())?;
    let empty_result = invoke("malbolge-2026", &new_target, &empty, false)?;
    assert!(!empty_result.status.success());
    assert!(!new_target.exists());

    let extra = Command::new(EXECUTABLE)
        .arg("--profile")
        .arg("malbolge-2026")
        .arg("--output")
        .arg(&new_target)
        .arg("--")
        .arg("--ternary-file")
        .arg(&wire)
        .arg("nop")
        .output()
        .map_err(|error| error.to_string())?;
    assert!(!extra.status.success());
    assert!(!new_target.exists());

    let protected = fixture.path("existing.malbolge");
    let sentinel = b"owner-existing-artifact";
    fs::write(&protected, sentinel).map_err(|error| error.to_string())?;
    let result = invoke("malbolge-2026", &protected, &wire, true)?;
    assert!(!result.status.success());
    assert_eq!(
        fs::read(&protected).map_err(|error| error.to_string())?,
        sentinel
    );
    assert_eq!(
        fs::read_dir(&fixture.root)
            .map_err(|error| error.to_string())?
            .count(),
        3
    );
    Ok(())
}

fn trace_program(effects: &[TraceEffect]) -> TestResult<TernaryProgram> {
    let mut program = echoed_program(1)?;
    let end = u32::try_from(effects.len().saturating_add(1))
        .map_err(|error| format!("trace source length: {error}"))?;
    let mut operations = Vec::with_capacity(effects.len().saturating_add(1));
    for (index, effect) in effects.iter().enumerate() {
        let begin = u32::try_from(index).map_err(|error| format!("trace span: {error}"))?;
        let span = span(begin, begin.saturating_add(1));
        operations.push(match effect {
            TraceEffect::Read(result) => TernaryOperation::ByteInput {
                result: *result,
                span,
            },
            TraceEffect::Write(value) => TernaryOperation::ByteOutput {
                value: *value,
                span,
            },
        });
    }
    operations.push(TernaryOperation::ReturnVoid {
        span: span(end.saturating_sub(1), end),
    });
    let function = program
        .functions
        .first_mut()
        .ok_or("missing trace function")?;
    function.operations = operations;
    function.span = span(0, end);
    Ok(program)
}

fn invoke_latest(profile: &str, target: &Path, wire: &Path, capsule: bool) -> TestResult<Output> {
    let mut command = Command::new(EXECUTABLE);
    let _args = command
        .arg("--profile")
        .arg(profile)
        .arg("--output")
        .arg(target);
    if capsule {
        let _capsule = command.arg("--capsule");
    }
    command
        .arg("--")
        .arg("--latest-byte-trace")
        .arg("--ternary-file")
        .arg(wire)
        .output()
        .map_err(|error| format!("latest-byte CLI invocation: {error}"))
}

#[test]
#[expect(
    clippy::cognitive_complexity,
    reason = "raw/capsule output and independent VM trace are checked together"
)]
#[expect(
    clippy::panic_in_result_fn,
    reason = "independent raw/capsule successful-byte VM witness is asserted"
)]
fn latest_read_trace_publishes_raw_and_capsule_with_exact_guest_effects() -> TestResult<()> {
    let fixture = Fixture::new()?;
    let program = trace_program(&[
        TraceEffect::Read(0),
        TraceEffect::Write(0),
        TraceEffect::Write(0),
        TraceEffect::Read(1), // consumed but never output
        TraceEffect::Read(2),
        TraceEffect::Write(2),
        TraceEffect::Read(3),
        TraceEffect::Write(3),
        TraceEffect::Write(3),
    ])?;
    let wire = fixture.path("latest.mctr");
    let _bytes = save_wire(&wire, &program)?;
    let strict_target = fixture.path("strict-rejected.malbolge");
    let strict = invoke("malbolge-2026", &strict_target, &wire, false)?;
    assert!(!strict.status.success());
    assert!(!strict_target.exists());

    let raw_path = fixture.path("latest-raw.malbolge");
    let raw = invoke_latest("malbolge-2026", &raw_path, &wire, false)?;
    assert!(
        raw.status.success(),
        "{}",
        String::from_utf8_lossy(&raw.stderr)
    );
    let source = fs::read(&raw_path).map_err(|error| error.to_string())?;
    assert_eq!(source.len(), 10);
    let bridge_layout = bridge::encode_successful_latest_byte_trace(&program, current_profile())
        .map_err(|error| format!("independent trace layout: {error:?}"))?;
    assert_eq!(source, bridge_layout.source());

    let capsule_path = fixture.path("latest-capsule.malbolge");
    let framed = invoke_latest("malbolge-2026", &capsule_path, &wire, true)?;
    assert!(
        framed.status.success(),
        "{}",
        String::from_utf8_lossy(&framed.stderr)
    );
    let capsule_bytes = fs::read(&capsule_path).map_err(|error| error.to_string())?;
    let capsule = parse_capsule(&capsule_bytes)
        .map_err(|error| format!("capsule decode: {error:?}"))?
        .ok_or("missing latest-byte capsule")?;
    assert_eq!(capsule.profile(), current_profile());
    assert_eq!(capsule.payload(), source);
    for (input, output) in [
        (vec![0, 255, 173, 128], vec![0, 0, 173, 128, 128]),
        (vec![255, 0, 128, 1], vec![255, 255, 128, 1, 1]),
    ] {
        let mut vm = ProfileMachine::from_source(capsule.profile(), capsule.payload(), input)
            .map_err(|error| format!("independent VM load: {error:?}"))?;
        assert!(matches!(
            vm.run(10),
            Ok(RunOutcome::Terminated { steps: 10, .. })
        ));
        assert_eq!(vm.input_consumed(), 4);
        assert_eq!(vm.output(), output);
    }
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "compatibility and output identity"
)]
fn latest_read_opt_in_does_not_change_existing_adjacent_echo_artifacts() -> TestResult<()> {
    let fixture = Fixture::new()?;
    let program = echoed_program(3)?;
    let wire = fixture.path("echo.mctr");
    let _wire = save_wire(&wire, &program)?;
    for capsule in [false, true] {
        let old_path = fixture.path(if capsule {
            "old-cap.malbolge"
        } else {
            "old-raw.malbolge"
        });
        let new_path = fixture.path(if capsule {
            "new-cap.malbolge"
        } else {
            "new-raw.malbolge"
        });
        let old = invoke("malbolge-2026", &old_path, &wire, capsule)?;
        let new = invoke_latest("malbolge-2026", &new_path, &wire, capsule)?;
        assert!(
            old.status.success(),
            "{}",
            String::from_utf8_lossy(&old.stderr)
        );
        assert!(
            new.status.success(),
            "{}",
            String::from_utf8_lossy(&new.stderr)
        );
        assert_eq!(
            fs::read(old_path).map_err(|error| error.to_string())?,
            fs::read(new_path).map_err(|error| error.to_string())?
        );
    }
    Ok(())
}

#[test]
#[expect(
    clippy::cognitive_complexity,
    reason = "all hostile wire and parser cases must fail before publication"
)]
#[expect(clippy::panic_in_result_fn, reason = "hostile source and mode grammar")]
fn latest_read_mode_rejects_stale_ssa_invalid_wire_profile_and_arguments() -> TestResult<()> {
    let fixture = Fixture::new()?;
    let wire = fixture.path("latest.mctr");
    let target = fixture.path("never-created.malbolge");
    let stale = trace_program(&[
        TraceEffect::Read(0),
        TraceEffect::Read(1),
        TraceEffect::Write(0),
    ])?;
    let _bytes = save_wire(&wire, &stale)?;
    let rejected = invoke_latest("malbolge-2026", &target, &wire, true)?;
    assert!(!rejected.status.success());
    assert!(String::from_utf8_lossy(&rejected.stderr).contains("UnsupportedEffectTrace"));
    assert!(!target.exists());

    let supported = trace_program(&[TraceEffect::Read(0), TraceEffect::Write(0)])?;
    let original = save_wire(&wire, &supported)?;
    let wrong_profile = invoke_latest("malbolge-1998", &target, &wire, false)?;
    assert!(!wrong_profile.status.success());
    assert!(!target.exists());
    let mut corrupted = original.clone();
    if let Some(last) = corrupted.last_mut() {
        *last ^= 0x80;
    }
    fs::write(&wire, corrupted).map_err(|error| error.to_string())?;
    let bad_wire = invoke_latest("malbolge-2026", &target, &wire, true)?;
    assert!(!bad_wire.status.success());
    assert!(!target.exists());
    fs::write(&wire, original).map_err(|error| error.to_string())?;

    for suffix in [
        vec!["--latest-byte-trace", "input", "output", "halt"],
        vec!["--latest-byte-trace", "--ternary-file"],
        vec![
            "--latest-byte-trace",
            "--ternary-file",
            "latest.mctr",
            "nop",
        ],
        vec!["--ternary-file", "latest.mctr", "--latest-byte-trace"],
    ] {
        let invalid = Command::new(EXECUTABLE)
            .arg("--profile")
            .arg("malbolge-2026")
            .arg("--output")
            .arg(&target)
            .arg("--")
            .args(suffix)
            .output()
            .map_err(|error| error.to_string())?;
        assert!(!invalid.status.success());
        assert!(!target.exists());
    }
    Ok(())
}
