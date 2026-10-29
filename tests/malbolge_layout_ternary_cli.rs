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

#[expect(
    clippy::too_many_lines,
    reason = "pre-existing canonical ternary codec is reused, not duplicated"
)]
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
