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
//   - External-process verified `.malbolge` publishing regression.
// - Must-Not:
//   - Treat machine-op fixture creation as arbitrary C program lowering.
// - Allows:
//   - Inputs: bounded real CLI invocations, exact profiles, temp output paths.
//   - Outputs: independent source-loader and hostile no-clobber evidence.
//   - Side effects: only owned ignored `.temp` per-test directories.
// - Split-When:
//   - Full C program artifact emission has independent regression authority.
// - Merge-When:
//   - End-to-end compiled-C artifact testing subsumes this bounded command.
// - Summary:
//   - Tests real bounded profile-bound graphical code file publication.
// - Description:
//   - Exercises successful VM execution, hostile CLI and atomic publication.
// - Usage:
//   - `cargo test --test malbolge_layout_cli`.
// - Defaults:
//   - No preexisting target file is ever overwritten.
//

//! External-process checks of the first raw graphical `.malbolge` emitter.

use std::ffi::OsString;
use std::fs;
use std::io::Write as _;
use std::iter::{repeat_n, repeat_with};
use std::path::{Path, PathBuf};
use std::process::{Command, Output, Stdio, id};
use std::sync::atomic::{AtomicUsize, Ordering};

use malbolge::{
    ExecutionMachine, ExecutionMode, ProfileMachine, RunOutcome, current_profile,
    decode_profile_instruction, historical_profile, parse_capsule,
};

const EXECUTABLE: &str = env!("CARGO_BIN_EXE_malbolge_layout");
static FIXTURE_SEQUENCE: AtomicUsize = AtomicUsize::new(0);

struct OwnedFixture {
    root: PathBuf,
}

impl OwnedFixture {
    fn new() -> Result<Self, String> {
        let sequence = FIXTURE_SEQUENCE.fetch_add(1, Ordering::Relaxed);
        let root = Path::new(env!("CARGO_MANIFEST_DIR"))
            .join(".temp")
            .join(format!("layout-cli-test-{}-{sequence}", id()));
        #[expect(
            clippy::create_dir,
            reason = "refuse an already-existing test directory to protect others"
        )]
        fs::create_dir(&root).map_err(|error| format!("fixture dir: {error}"))?;
        Ok(Self { root })
    }

    fn path(&self, name: &str) -> PathBuf {
        self.root.join(name)
    }
}

#[expect(
    clippy::missing_trait_methods,
    reason = "Drop::pin_drop is unstable and its default no-op is correct here"
)]
impl Drop for OwnedFixture {
    fn drop(&mut self) {
        drop(fs::remove_dir_all(&self.root));
    }
}

fn emit(profile: &str, target: &Path, opcodes: &[&str]) -> Result<Output, String> {
    let mut command = Command::new(EXECUTABLE);
    let _command = command
        .arg("--profile")
        .arg(profile)
        .arg("--output")
        .arg(target)
        .arg("--")
        .args(opcodes);
    command
        .output()
        .map_err(|error| format!("layout CLI: {error}"))
}

fn emit_capsule(profile: &str, target: &Path, opcodes: &[&str]) -> Result<Output, String> {
    Command::new(EXECUTABLE)
        .arg("--profile")
        .arg(profile)
        .arg("--output")
        .arg(target)
        .arg("--capsule")
        .arg("--")
        .args(opcodes)
        .output()
        .map_err(|error| format!("capsule CLI: {error}"))
}

fn emit_os(args: &[OsString]) -> Result<Output, String> {
    Command::new(EXECUTABLE)
        .args(args)
        .output()
        .map_err(|error| format!("layout CLI: {error}"))
}

fn source_on_success(output: &Output, path: &Path) -> Result<Vec<u8>, String> {
    if !output.status.success() {
        return Err(format!(
            "CLI rejected valid fixture: {}",
            String::from_utf8_lossy(&output.stderr)
        ));
    }
    if !output.stdout.is_empty() {
        return Err(String::from("success CLI leaked non-source stdout"));
    }
    let source = fs::read(path).map_err(|error| format!("emitted source: {error}"))?;
    if !source.iter().all(|byte| (33..=126).contains(byte)) {
        return Err(String::from("emitted source is not fully graphical"));
    }
    Ok(source)
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "end-to-end independent VM execution asserts real target artifact"
)]
fn external_emitter_writes_runnable_profile_specific_source() -> Result<(), String> {
    for (profile_id, profile) in [
        ("malbolge-1998", historical_profile()),
        ("malbolge-2026", current_profile()),
    ] {
        let fixture = OwnedFixture::new()?;
        let target = fixture.path("echo.malbolge");
        let output = emit(profile_id, &target, &["nop", "input", "output", "halt"])?;
        let source = source_on_success(&output, &target)?;
        assert_eq!(source.len(), 4);
        for (position, expected) in [
            b'o',
            profile.input_instruction(),
            profile.output_instruction(),
            b'v',
        ]
        .iter()
        .enumerate()
        {
            let code = u32::try_from(position).map_err(|error| error.to_string())?;
            assert_eq!(
                decode_profile_instruction(
                    u32::from(*source.get(position).ok_or("missing code cell")?),
                    code,
                ),
                Some(*expected)
            );
        }
        let mut machine = ProfileMachine::from_source(profile, &source, vec![b'K'])
            .map_err(|error| format!("external VM loader: {error:?}"))?;
        assert!(matches!(
            machine.run(4),
            Ok(RunOutcome::Terminated { steps: 4, .. })
        ));
        assert_eq!(machine.output(), b"K");
        assert_eq!(machine.input_consumed(), 1);
    }
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "deterministic emission is compared across independent processes"
)]
fn machine_artifact_bytes_are_reproducible_for_the_same_profile() -> Result<(), String> {
    let fixture = OwnedFixture::new()?;
    let first_path = fixture.path("a.malbolge");
    let second_path = fixture.path("b.malbolge");
    let first = emit("malbolge-1998", &first_path, &["input", "output", "halt"])?;
    let second = emit("malbolge-1998", &second_path, &["input", "output", "halt"])?;
    assert_eq!(
        source_on_success(&first, &first_path)?,
        source_on_success(&second, &second_path)?
    );
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "no overwrite is an external security boundary"
)]
fn existing_target_is_not_overwritten_or_replaced() -> Result<(), String> {
    let fixture = OwnedFixture::new()?;
    let path = fixture.path("protected.malbolge");
    let original = b"existing-user-code";
    fs::write(&path, original).map_err(|error| error.to_string())?;
    let result = emit("malbolge-1998", &path, &["input", "output", "halt"])?;
    assert!(!result.status.success());
    assert_eq!(
        fs::read(&path).map_err(|error| error.to_string())?,
        original
    );
    let entries = fs::read_dir(&fixture.root)
        .map_err(|error| error.to_string())?
        .count();
    assert_eq!(entries, 1, "no temporary stages may survive refusal");
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "hostile invalid inputs must not publish artifacts"
)]
fn malformed_profile_opcode_shape_or_path_never_publishes() -> Result<(), String> {
    type InvalidCase<'input> = (&'input str, &'input str, &'input [&'input str]);
    let fixture = OwnedFixture::new()?;
    let cases: &[InvalidCase<'_>] = &[
        (
            "forged-profile",
            "unknown.malbolge",
            &["input", "output", "halt"],
        ),
        ("malbolge-1998", "unknown-op.malbolge", &["system", "halt"]),
        ("malbolge-1998", "bad-target.malbolge", &["jump:1", "halt"]),
        ("malbolge-1998", "unplaced.malbolge", &["crazy", "halt"]),
        ("malbolge-1998", "early-halt.malbolge", &["halt", "halt"]),
        ("malbolge-1998", "wrong-extension.txt", &["nop", "halt"]),
        ("malbolge-1998", "missing-halt.malbolge", &["nop", "nop"]),
        (
            "malbolge-1998",
            "bad-integer.malbolge",
            &["jump:-1", "halt"],
        ),
    ];
    for &(profile, name, operations) in cases {
        let path = fixture.path(name);
        let result = emit(profile, &path, operations)?;
        assert!(!result.status.success(), "unexpected success for {name}");
        assert!(!path.exists(), "invalid candidate published {name}");
        assert!(result.stdout.is_empty());
        assert!(!result.stderr.is_empty());
    }
    assert_eq!(
        fs::read_dir(&fixture.root)
            .map_err(|error| error.to_string())?
            .count(),
        0
    );
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "exact argument grammar and bounds are checked as user input"
)]
fn cli_requires_explicit_arguments_and_bounded_opcode_tokens() -> Result<(), String> {
    let fixture = OwnedFixture::new()?;
    let target = fixture.path("not-published.malbolge");
    let invalid = [
        vec![OsString::from("--profile"), OsString::from("malbolge-1998")],
        vec![
            OsString::from("--output"),
            target.as_os_str().to_os_string(),
        ],
        vec![
            OsString::from("--profile"),
            OsString::from("malbolge-1998"),
            OsString::from("--output"),
            target.as_os_str().to_os_string(),
        ],
    ];
    for args in invalid {
        let result = emit_os(&args)?;
        assert!(!result.status.success());
        assert!(result.stdout.is_empty());
    }
    let mut excessive = vec![
        OsString::from("--profile"),
        OsString::from("malbolge-1998"),
        OsString::from("--output"),
        target.as_os_str().to_os_string(),
        OsString::from("--"),
    ];
    excessive.extend(repeat_with(|| OsString::from("nop")).take(4097));
    let result = emit_os(&excessive)?;
    assert!(!result.status.success());
    assert!(!target.exists());
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "two native writer processes contend for the exact same artifact"
)]
fn concurrent_writers_publish_at_most_one_complete_source() -> Result<(), String> {
    let fixture = OwnedFixture::new()?;
    let path = fixture.path("racing.malbolge");
    let mut left = Command::new(EXECUTABLE);
    let _left = left
        .arg("--profile")
        .arg("malbolge-1998")
        .arg("--output")
        .arg(&path)
        .arg("--")
        .args(["nop", "halt"]);
    let mut right = Command::new(EXECUTABLE);
    let _right = right
        .arg("--profile")
        .arg("malbolge-1998")
        .arg("--output")
        .arg(&path)
        .arg("--")
        .args(["input", "output", "halt"]);
    let first = left
        .spawn()
        .map_err(|error| format!("first writer: {error}"))?;
    let second = right
        .spawn()
        .map_err(|error| format!("second writer: {error}"))?;
    let left_result = first
        .wait_with_output()
        .map_err(|error| error.to_string())?;
    let right_result = second
        .wait_with_output()
        .map_err(|error| error.to_string())?;
    assert_ne!(left_result.status.success(), right_result.status.success());
    let source = fs::read(&path).map_err(|error| error.to_string())?;
    assert!(source.len() == 2 || source.len() == 3);
    let mut machine = ProfileMachine::from_source(historical_profile(), &source, vec![])
        .map_err(|error| format!("racing final source loader: {error:?}"))?;
    assert!(matches!(
        machine.run(source.len()),
        Ok(RunOutcome::Terminated { .. })
    ));
    assert_eq!(
        fs::read_dir(&fixture.root)
            .map_err(|error| error.to_string())?
            .count(),
        1
    );
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "source is executed by an independently constructed profile VM"
)]
fn external_cli_runs_forward_jump_and_relocated_arithmetic() -> Result<(), String> {
    let fixture = OwnedFixture::new()?;
    for (profile_id, profile) in [
        ("malbolge-1998", historical_profile()),
        ("malbolge-2026", current_profile()),
    ] {
        let target = (33u32..=126u32)
            .find(|&byte| decode_profile_instruction(byte, 0) == Some(b'i'))
            .ok_or("missing canonical jump inverse")?
            .saturating_add(1);
        let source_length = usize::try_from(target)
            .map_err(|error| error.to_string())?
            .saturating_add(3);
        let operations = vec!["nop"; source_length];
        let jump_token = format!("jump:{target}");
        let mut dynamic: Vec<String> = operations.iter().map(|token| (*token).to_owned()).collect();
        *dynamic.first_mut().ok_or("jump token")? = jump_token;
        *dynamic
            .get_mut(usize::try_from(target).map_err(|error| error.to_string())?)
            .ok_or("input position")? = String::from("input");
        *dynamic
            .get_mut(
                usize::try_from(target)
                    .map_err(|error| error.to_string())?
                    .saturating_add(1),
            )
            .ok_or("output position")? = String::from("output");
        *dynamic.last_mut().ok_or("halt position")? = String::from("halt");
        let refs: Vec<&str> = dynamic.iter().map(String::as_str).collect();
        let path = fixture.path(&format!("{profile_id}-jump.malbolge"));
        let result = emit(profile_id, &path, &refs)?;
        let source = source_on_success(&result, &path)?;
        let mut machine = ProfileMachine::from_source(profile, &source, vec![b'P'])
            .map_err(|error| format!("external jumped program: {error:?}"))?;
        assert!(matches!(
            machine.run(4),
            Ok(RunOutcome::Terminated { steps: 4, .. })
        ));
        assert_eq!(machine.output(), b"P");

        let arithmetic = fixture.path(&format!("{profile_id}-arithmetic.malbolge"));
        let arithmetic_result = emit(
            profile_id,
            &arithmetic,
            &["relocate", "rotate", "crazy", "halt"],
        )?;
        let arithmetic_source = source_on_success(&arithmetic_result, &arithmetic)?;
        let mut arithmetic_vm =
            ProfileMachine::from_source(profile, &arithmetic_source, Vec::new())
                .map_err(|error| format!("external arithmetic program: {error:?}"))?;
        assert!(matches!(
            arithmetic_vm.run(4),
            Ok(RunOutcome::Terminated { steps: 4, .. })
        ));
    }
    Ok(())
}

#[cfg(unix)]
#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "symlink no-overwrite is a deliberate external file boundary"
)]
fn output_symlink_is_refused_without_modifying_its_target() -> Result<(), String> {
    use std::os::unix::fs::symlink;

    let fixture = OwnedFixture::new()?;
    let existing = fixture.path("original.txt");
    let symlink_path = fixture.path("redirect.malbolge");
    fs::write(&existing, b"original data").map_err(|error| error.to_string())?;
    symlink(&existing, &symlink_path).map_err(|error| error.to_string())?;
    let result = emit("malbolge-1998", &symlink_path, &["nop", "halt"])?;
    assert!(!result.status.success());
    assert_eq!(
        fs::read(&existing).map_err(|error| error.to_string())?,
        b"original data"
    );
    assert!(symlink_path.is_symlink());
    assert_eq!(
        fs::read_dir(&fixture.root)
            .map_err(|error| error.to_string())?
            .count(),
        2
    );
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "independent profile loader checks published capsule and payload"
)]
#[expect(
    clippy::cognitive_complexity,
    reason = "both canonical profiles, frame fields and real guest I/O are verified"
)]
fn capsule_emission_preserves_profile_and_exact_raw_source() -> Result<(), String> {
    for (profile_id, profile) in [
        ("malbolge-1998", historical_profile()),
        ("malbolge-2026", current_profile()),
    ] {
        let fixture = OwnedFixture::new()?;
        let raw_path = fixture.path("raw.malbolge");
        let capsule_path = fixture.path("capsule.malbolge");
        let operations = &["input", "output", "halt"];
        let source = source_on_success(&emit(profile_id, &raw_path, operations)?, &raw_path)?;
        let result = emit_capsule(profile_id, &capsule_path, operations)?;
        assert!(
            result.status.success(),
            "{}",
            String::from_utf8_lossy(&result.stderr)
        );
        assert!(result.stdout.is_empty());
        let bytes = fs::read(&capsule_path).map_err(|error| error.to_string())?;
        assert!(bytes.starts_with(b"(C<;_\"K"));
        assert!(bytes.len() > source.len());
        let capsule = parse_capsule(&bytes)
            .map_err(|error| format!("capsule parser: {error:?}"))?
            .ok_or("capsule emission lacked an exact versioned sideband")?;
        assert_eq!(capsule.profile().id(), profile.id());
        assert_eq!(capsule.profile().fingerprint(), profile.fingerprint());
        assert_eq!(capsule.payload(), source);
        let mut vm = ProfileMachine::from_source(capsule.profile(), capsule.payload(), vec![b'V'])
            .map_err(|error| format!("capsule profile VM load: {error:?}"))?;
        assert!(matches!(
            vm.run(3),
            Ok(RunOutcome::Terminated { steps: 3, .. })
        ));
        assert_eq!(vm.output(), b"V");
    }
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "real general runner and historical fallback both execute capsule"
)]
fn modern_capsule_runs_through_general_cli_with_classic_fallback() -> Result<(), String> {
    let fixture = OwnedFixture::new()?;
    let path = fixture.path("self-describing.malbolge");
    let result = emit_capsule("malbolge-2026", &path, &["nop", "halt"])?;
    assert!(result.status.success());
    let bytes = fs::read(&path).map_err(|error| error.to_string())?;
    let capsule = parse_capsule(&bytes)
        .map_err(|error| error.to_string())?
        .ok_or("modern capsule missing")?;
    assert_eq!(capsule.profile().id(), current_profile().id());
    let execution = Command::new(env!("CARGO_BIN_EXE_malbolge"))
        .arg(&path)
        .output()
        .map_err(|error| format!("real CLI: {error}"))?;
    assert!(
        execution.status.success(),
        "{}",
        String::from_utf8_lossy(&execution.stderr)
    );
    assert!(execution.stdout.is_empty());
    let mut historical =
        ExecutionMachine::from_source(&bytes, Vec::new(), ExecutionMode::Interpreter)
            .map_err(|error| format!("historical fallback loader: {error}"))?;
    assert!(matches!(
        historical.run(7),
        Ok(RunOutcome::Terminated { steps: 7, .. })
    ));
    assert_eq!(historical.output(), b"!");
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "capsule argument grammar and no-overwrite are safety boundaries"
)]
fn invalid_capsule_request_or_existing_file_never_publishes() -> Result<(), String> {
    let fixture = OwnedFixture::new()?;
    let target = fixture.path("invalid.malbolge");
    let arguments = vec![
        OsString::from("--profile"),
        OsString::from("malbolge-2026"),
        OsString::from("--output"),
        target.as_os_str().to_os_string(),
        OsString::from("--capsule"),
        OsString::from("--capsule"),
        OsString::from("--"),
        OsString::from("nop"),
        OsString::from("halt"),
    ];
    let malformed = emit_os(&arguments)?;
    assert!(!malformed.status.success());
    assert!(!target.exists());
    let unsafe_opcode = emit_capsule("malbolge-2026", &target, &["crazy", "halt"])?;
    assert!(!unsafe_opcode.status.success());
    assert!(!target.exists());
    fs::write(&target, b"existing").map_err(|error| error.to_string())?;
    let occupied = emit_capsule("malbolge-2026", &target, &["nop", "halt"])?;
    assert!(!occupied.status.success());
    assert_eq!(
        fs::read(&target).map_err(|error| error.to_string())?,
        b"existing"
    );
    assert_eq!(
        fs::read_dir(&fixture.root)
            .map_err(|error| error.to_string())?
            .count(),
        1
    );
    Ok(())
}

/// This chain's third jump reads the encrypted data word at source address
/// 72, not the original no-op cell (or the third jump's code character).
fn multi_jump_tokens() -> Vec<&'static str> {
    (0..127usize)
        .map(|position| match position {
            0 => "input",
            26 => "jump:73",
            102 => "jump:107",
            122 => "jump:125",
            125 => "output",
            126 => "halt",
            _ => "nop",
        })
        .collect()
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "independent serialized target VM execution and hostile CLI rejection"
)]
#[expect(
    clippy::cognitive_complexity,
    reason = "two profiles and both published file forms are checked end to end"
)]
fn multi_jump_raw_and_capsule_files_preserve_encrypted_operand_branching() -> Result<(), String> {
    let fixture = OwnedFixture::new()?;
    let tokens = multi_jump_tokens();
    for (profile_id, profile) in [
        ("malbolge-1998", historical_profile()),
        ("malbolge-2026", current_profile()),
    ] {
        let raw_path = fixture.path(&format!("{profile_id}-three-jumps.malbolge"));
        let capsule_path = fixture.path(&format!("{profile_id}-three-jumps-capsule.malbolge"));
        let raw_result = emit(profile_id, &raw_path, &tokens)?;
        let raw = source_on_success(&raw_result, &raw_path)?;
        assert_eq!(raw.len(), 127);
        assert_eq!(raw.get(72).copied(), Some(90));
        let capsule_result = emit_capsule(profile_id, &capsule_path, &tokens)?;
        assert!(
            capsule_result.status.success(),
            "{}",
            String::from_utf8_lossy(&capsule_result.stderr)
        );
        let capsule_file = fs::read(&capsule_path).map_err(|error| error.to_string())?;
        let capsule = parse_capsule(&capsule_file)
            .map_err(|error| format!("capsule decode: {error:?}"))?
            .ok_or("three-jump capsule not recognized")?;
        assert_eq!(capsule.profile().id(), profile.id());
        assert_eq!(capsule.payload(), raw);
        let mut machine = ProfileMachine::from_source(profile, &raw, vec![0xf3])
            .map_err(|error| format!("three-jump VM loader: {error:?}"))?;
        assert!(matches!(
            machine.run(75),
            Ok(RunOutcome::Terminated { steps: 75, .. })
        ));
        assert_eq!(machine.output(), &[0xf3]);
        assert_eq!(machine.input_consumed(), 1);
        assert_eq!(
            machine
                .memory_word(72)
                .map_err(|error| format!("encrypted operand read: {error:?}"))?,
            124
        );
        assert_eq!(machine.registers().code_pointer, 126);
        assert_eq!(machine.registers().data_pointer, 74);
    }
    let profile_id = "malbolge-2026";
    let mut forged = tokens;
    if let Some(third) = forged.get_mut(122) {
        *third = "jump:124";
    }
    let refused_path = fixture.path("forged-third-jump.malbolge");
    let refused = emit_capsule(profile_id, &refused_path, &forged)?;
    assert!(!refused.status.success());
    assert!(!refused_path.exists());
    assert!(String::from_utf8_lossy(&refused.stderr).contains("JumpTargetMismatch"));
    Ok(())
}

fn jump_then_relocated_arithmetic_tokens() -> Vec<&'static str> {
    (0..55usize)
        .map(|position| match position {
            0 => "input",
            48 => "jump:51",
            51 => "relocate",
            52 => "rotate",
            53 => "crazy",
            54 => "halt",
            _ => "nop",
        })
        .collect()
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "real process output is independently loaded and executed"
)]
#[expect(
    clippy::cognitive_complexity,
    reason = "raw and capsule source identity across both canonical VMs"
)]
fn jump_then_data_relocation_publishes_real_safe_arithmetic_artifacts() -> Result<(), String> {
    let fixture = OwnedFixture::new()?;
    let tokens = jump_then_relocated_arithmetic_tokens();
    for (profile_id, profile) in [
        ("malbolge-1998", historical_profile()),
        ("malbolge-2026", current_profile()),
    ] {
        let raw_path = fixture.path(&format!("{profile_id}-jump-relocation.malbolge"));
        let capsule_path = fixture.path(&format!("{profile_id}-jump-relocation-cap.malbolge"));
        let raw = source_on_success(&emit(profile_id, &raw_path, &tokens)?, &raw_path)?;
        assert_eq!(raw.len(), 55);
        assert_eq!(raw.get(49).copied(), Some(113));
        let result = emit_capsule(profile_id, &capsule_path, &tokens)?;
        assert!(
            result.status.success(),
            "{}",
            String::from_utf8_lossy(&result.stderr)
        );
        let bytes = fs::read(&capsule_path).map_err(|error| error.to_string())?;
        let capsule = parse_capsule(&bytes)
            .map_err(|error| format!("capsule parse: {error:?}"))?
            .ok_or("jump-relocation capsule is not recognized")?;
        assert_eq!(capsule.profile().fingerprint(), profile.fingerprint());
        assert_eq!(capsule.payload(), raw);
        let mut vm = ProfileMachine::from_source(profile, &raw, vec![0x92])
            .map_err(|error| format!("jump-relocation VM loader: {error:?}"))?;
        let initial_rotate_word = vm
            .memory_word(114)
            .map_err(|error| format!("initial data word: {error:?}"))?;
        assert!(matches!(
            vm.run(53),
            Ok(RunOutcome::Terminated { steps: 53, .. })
        ));
        assert_eq!(vm.registers().data_pointer, 116);
        assert_eq!(vm.registers().code_pointer, 54);
        assert_eq!(vm.input_consumed(), 1);
        assert_ne!(
            vm.memory_word(114)
                .map_err(|error| format!("rotated data word: {error:?}"))?,
            initial_rotate_word,
            "rotate must perform actual guest data work"
        );
    }
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "XLAT2-derived relocation capacity must fail before publication"
)]
fn prior_encrypted_relocation_operand_rejects_overlapping_source_file() -> Result<(), String> {
    let fixture = OwnedFixture::new()?;
    let operations: Vec<&str> = (0..62usize)
        .map(|position| match position {
            0 => "input",
            46 => "jump:53",
            58 => "relocate",
            59 => "rotate",
            60 => "crazy",
            61 => "halt",
            _ => "nop",
        })
        .collect();
    let safe = fixture.path("encrypted-relocation.malbolge");
    let source = source_on_success(&emit("malbolge-2026", &safe, &operations)?, &safe)?;
    assert_eq!(source.get(52).copied(), Some(110));
    let mut vm = ProfileMachine::from_source(current_profile(), &source, Vec::new())
        .map_err(|error| format!("encrypted j VM loader: {error:?}"))?;
    assert!(matches!(
        vm.run(56),
        Ok(RunOutcome::Terminated { steps: 56, .. })
    ));
    assert_eq!(vm.registers().data_pointer, 129);
    let mut oversized = operations;
    *oversized.last_mut().ok_or("missing terminal halt")? = "nop";
    oversized.resize(127, "nop");
    *oversized.last_mut().ok_or("oversized terminal")? = "halt";
    let rejected = fixture.path("aliasing-relocation.malbolge");
    let failed = emit_capsule("malbolge-2026", &rejected, &oversized)?;
    assert!(!failed.status.success());
    assert!(String::from_utf8_lossy(&failed.stderr).contains("UnsafeDataPlacement"));
    assert!(!rejected.exists());
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "two real jumps and relocated arithmetic must survive file publication"
)]
#[expect(
    clippy::cognitive_complexity,
    reason = "cross-profile raw/capsule decode and guest code/data mutations"
)]
fn two_jumps_then_data_relocation_publishes_replayable_source() -> Result<(), String> {
    let fixture = OwnedFixture::new()?;
    let operations: Vec<&str> = (0..73usize)
        .map(|position| match position {
            0 => "input",
            48 => "jump:51",
            52 => "jump:69",
            69 => "relocate",
            70 => "rotate",
            71 => "crazy",
            72 => "halt",
            _ => "nop",
        })
        .collect();
    for (profile_id, profile) in [
        ("malbolge-1998", historical_profile()),
        ("malbolge-2026", current_profile()),
    ] {
        let raw_path = fixture.path(&format!("{profile_id}-two-jumps-then-j.malbolge"));
        let capsule_path = fixture.path(&format!("{profile_id}-two-jumps-then-j-cap.malbolge"));
        let source = source_on_success(&emit(profile_id, &raw_path, &operations)?, &raw_path)?;
        assert_eq!(source.get(50).copied(), Some(112));
        assert_eq!(source.get(51).copied(), Some(111));
        let result = emit_capsule(profile_id, &capsule_path, &operations)?;
        assert!(
            result.status.success(),
            "{}",
            String::from_utf8_lossy(&result.stderr)
        );
        let capsule_bytes = fs::read(&capsule_path).map_err(|error| error.to_string())?;
        let capsule = parse_capsule(&capsule_bytes)
            .map_err(|error| format!("capsule read: {error:?}"))?
            .ok_or("multi-jump relocation capsule not recognized")?;
        assert_eq!(capsule.profile().id(), profile.id());
        assert_eq!(capsule.payload(), source);
        let mut vm = ProfileMachine::from_source(profile, &source, vec![0x5e])
            .map_err(|error| format!("multi-jump relocation VM: {error:?}"))?;
        assert!(matches!(
            vm.run(55),
            Ok(RunOutcome::Terminated { steps: 55, .. })
        ));
        assert_eq!(vm.input_consumed(), 1);
        assert_eq!(vm.registers().data_pointer, 123);
        assert_eq!(
            vm.memory_word(50)
                .map_err(|error| format!("first data operand: {error:?}"))?,
            68
        );
        assert_eq!(
            vm.memory_word(51)
                .map_err(|error| format!("second data operand: {error:?}"))?,
            120
        );
    }
    Ok(())
}

fn emit_auto(
    profile: &str,
    target: &Path,
    tokens: &[&str],
    capsule: bool,
) -> Result<Output, String> {
    let mut command = Command::new(EXECUTABLE);
    let _arguments = command
        .arg("--profile")
        .arg(profile)
        .arg("--output")
        .arg(target);
    if capsule {
        let _capsule = command.arg("--capsule");
    }
    command
        .arg("--")
        .arg("--auto-layout")
        .args(tokens)
        .output()
        .map_err(|error| format!("automatic layout CLI: {error}"))
}

#[test]
#[expect(
    clippy::cognitive_complexity,
    reason = "raw, capsule and legacy source are independently cross-checked"
)]
#[expect(
    clippy::panic_in_result_fn,
    reason = "the independent normative VM must replay the published jump"
)]
fn automatic_symbolic_jump_publishes_runnable_raw_and_capsule() -> Result<(), String> {
    let fixture = OwnedFixture::new()?;
    for (profile_id, profile) in [
        ("malbolge-1998", historical_profile()),
        ("malbolge-2026", current_profile()),
    ] {
        let raw = fixture.path(&format!("{profile_id}-auto-jump.malbolge"));
        let framed = fixture.path(&format!("{profile_id}-auto-jump-cap.malbolge"));
        let tokens = ["jump", "input", "output", "halt"];
        let source = source_on_success(&emit_auto(profile_id, &raw, &tokens, false)?, &raw)?;
        let target = usize::from(*source.first().ok_or("missing graphical jump")?) + 1;
        assert_eq!(source.len(), target.saturating_add(3));
        assert!(source.len() > tokens.len());
        let mut concrete = vec![format!("jump:{target}")];
        concrete.extend(repeat_n(String::from("nop"), target.saturating_sub(1)));
        concrete.extend([
            String::from("input"),
            String::from("output"),
            String::from("halt"),
        ]);
        let old_tokens: Vec<&str> = concrete.iter().map(String::as_str).collect();
        let explicit = fixture.path(&format!("{profile_id}-explicit-jump.malbolge"));
        let manual = source_on_success(&emit(profile_id, &explicit, &old_tokens)?, &explicit)?;
        assert_eq!(source, manual);

        let published = emit_auto(profile_id, &framed, &tokens, true)?;
        assert!(
            published.status.success(),
            "{}",
            String::from_utf8_lossy(&published.stderr)
        );
        let frame = fs::read(framed).map_err(|error| error.to_string())?;
        let capsule = parse_capsule(&frame)
            .map_err(|error| format!("independent capsule parser: {error:?}"))?
            .ok_or("missing version-one capsule")?;
        assert_eq!(capsule.profile().id(), profile.id());
        assert_eq!(capsule.payload(), source);
        let mut vm = ProfileMachine::from_source(profile, capsule.payload(), vec![0xe1])
            .map_err(|error| format!("published symbolic VM load: {error:?}"))?;
        assert!(matches!(
            vm.run(4),
            Ok(RunOutcome::Terminated { steps: 4, .. })
        ));
        assert_eq!(vm.input_consumed(), 1);
        assert_eq!(vm.output(), &[0xe1]);
    }
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "the real CLI must preserve data relocation and self-modification"
)]
fn automatic_relocation_publishes_same_source_as_explicit_safe_layout() -> Result<(), String> {
    let fixture = OwnedFixture::new()?;
    let mut logical = vec!["auto-relocate"];
    logical.extend(["nop"].repeat(44));
    logical.extend(["rotate", "crazy", "halt"]);
    let mut concrete = vec!["nop"; 8];
    concrete.push("relocate");
    concrete.extend(["nop"].repeat(44));
    concrete.extend(["rotate", "crazy", "halt"]);
    for (profile_id, profile) in [
        ("malbolge-1998", historical_profile()),
        ("malbolge-2026", current_profile()),
    ] {
        let path = fixture.path(&format!("{profile_id}-auto-reloc.malbolge"));
        let baseline_path = fixture.path(&format!("{profile_id}-manual-reloc.malbolge"));
        let source = source_on_success(&emit_auto(profile_id, &path, &logical, false)?, &path)?;
        let baseline = source_on_success(
            &emit(profile_id, &baseline_path, &concrete)?,
            &baseline_path,
        )?;
        assert_eq!(source, baseline);
        assert_eq!(source.len(), 56);
        let mut vm = ProfileMachine::from_source(profile, &source, Vec::new())
            .map_err(|error| format!("auto relocation VM load: {error:?}"))?;
        assert!(matches!(
            vm.run(56),
            Ok(RunOutcome::Terminated { steps: 56, .. })
        ));
        assert!(usize::try_from(vm.registers().data_pointer).unwrap_or_default() > source.len());
    }
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "semantic source equality is cross-checked with existing concrete publishing"
)]
fn symbolic_two_jumps_and_auto_relocation_publish_exact_file() -> Result<(), String> {
    let fixture = OwnedFixture::new()?;
    let mut tokens = vec!["input"];
    tokens.extend(["nop"].repeat(47));
    tokens.extend([
        "jump",
        "nop",
        "jump",
        "auto-relocate",
        "rotate",
        "crazy",
        "halt",
    ]);
    let original: Vec<&str> = (0..73usize)
        .map(|position| match position {
            0 => "input",
            48 => "jump:51",
            52 => "jump:69",
            69 => "relocate",
            70 => "rotate",
            71 => "crazy",
            72 => "halt",
            _ => "nop",
        })
        .collect();
    for (profile_id, profile) in [
        ("malbolge-1998", historical_profile()),
        ("malbolge-2026", current_profile()),
    ] {
        let target = fixture.path(&format!("{profile_id}-two-auto.malbolge"));
        let manual_path = fixture.path(&format!("{profile_id}-two-manual.malbolge"));
        let result = emit_auto(profile_id, &target, &tokens, true)?;
        assert!(
            result.status.success(),
            "{}",
            String::from_utf8_lossy(&result.stderr)
        );
        let bytes = fs::read(target).map_err(|error| error.to_string())?;
        let capsule = parse_capsule(&bytes)
            .map_err(|error| format!("read checked source capsule: {error:?}"))?
            .ok_or("symbolic jump capsule absent")?;
        assert_eq!(capsule.profile().id(), profile.id());
        let baseline =
            source_on_success(&emit(profile_id, &manual_path, &original)?, &manual_path)?;
        assert_eq!(capsule.payload(), baseline);
        let mut vm = ProfileMachine::from_source(profile, capsule.payload(), vec![0x5e])
            .map_err(|error| format!("published multi-hop VM: {error:?}"))?;
        assert!(matches!(
            vm.run(55),
            Ok(RunOutcome::Terminated { steps: 55, .. })
        ));
        assert_eq!(vm.input_consumed(), 1);
        assert_eq!(vm.registers().data_pointer, 123);
    }
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "all malformed requests must fail closed"
)]
fn automatic_layout_mode_rejects_hostile_grammar_and_unsafe_plans() -> Result<(), String> {
    let fixture = OwnedFixture::new()?;
    let target = fixture.path("never-created.malbolge");
    for tokens in [
        vec![],
        vec!["jump:42", "halt"],
        vec!["--ternary-file", "data.mctr"],
        vec!["auto-relocate", "auto-relocate", "halt"],
        vec!["auto-relocate", "jump", "halt"],
        vec!["jump"],
        vec!["auto-relocate", "rotate", "halt", "nop"],
    ] {
        let refused = emit_auto("malbolge-1998", &target, &tokens, true)?;
        assert!(
            !refused.status.success(),
            "unexpected acceptance: {tokens:?}"
        );
        assert!(!target.exists());
    }
    let oversized = vec!["nop"; 4097];
    let refused_overflow = emit_auto("malbolge-1998", &target, &oversized, false)?;
    assert!(!refused_overflow.status.success());
    assert!(!target.exists());
    let refused = emit("malbolge-1998", &target, &["jump", "halt"])?;
    assert!(!refused.status.success());
    assert!(!target.exists());
    let sentinel = b"existing artifact protected";
    fs::write(&target, sentinel).map_err(|error| error.to_string())?;
    let protected = emit_auto(
        "malbolge-1998",
        &target,
        &["jump", "input", "output", "halt"],
        false,
    )?;
    assert!(!protected.status.success());
    assert_eq!(
        fs::read(target).map_err(|error| error.to_string())?,
        sentinel
    );
    Ok(())
}

#[test]
fn automatic_layout_preserves_ordinary_machine_source_bytes() -> Result<(), String> {
    let fixture = OwnedFixture::new()?;
    let normal_path = fixture.path("concrete.malbolge");
    let automatic_path = fixture.path("automatic.malbolge");
    let tokens = ["nop", "input", "output", "halt"];
    let concrete = source_on_success(&emit("malbolge-1998", &normal_path, &tokens)?, &normal_path)?;
    let automatic = source_on_success(
        &emit_auto("malbolge-1998", &automatic_path, &tokens, false)?,
        &automatic_path,
    )?;
    if concrete != automatic {
        return Err(String::from(
            "opt-in planner changed non-symbolic machine source",
        ));
    }
    Ok(())
}

#[test]
fn automatic_layout_artifacts_execute_binary_stdin_in_general_runner() -> Result<(), String> {
    let fixture = OwnedFixture::new()?;
    let tokens = ["jump", "input", "output", "input", "output", "halt"];
    for (profile_id, capsule) in [("malbolge-1998", false), ("malbolge-2026", true)] {
        let target = fixture.path(&format!("{profile_id}-general-runner.malbolge"));
        let result = emit_auto(profile_id, &target, &tokens, capsule)?;
        if !result.status.success() {
            return Err(format!(
                "symbolic input artifact refused: {}",
                String::from_utf8_lossy(&result.stderr)
            ));
        }
        let mut child = Command::new(env!("CARGO_BIN_EXE_malbolge"))
            .arg(&target)
            .arg("--input-stdin")
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .spawn()
            .map_err(|error| format!("launch general Malbolge runner: {error}"))?;
        let mut stdin = child
            .stdin
            .take()
            .ok_or("general runner lacks stdin pipe")?;
        stdin
            .write_all(&[0, 255])
            .map_err(|error| format!("feed binary guest stdin: {error}"))?;
        drop(stdin);
        let execution = child
            .wait_with_output()
            .map_err(|error| format!("collect guest execution: {error}"))?;
        if !execution.status.success()
            || execution.stdout != [0, 255]
            || !execution.stderr.is_empty()
        {
            return Err(format!(
                "auto-generated {profile_id} artifact execution mismatch: {execution:?}"
            ));
        }
    }
    Ok(())
}

#[test]
#[expect(
    clippy::too_many_lines,
    reason = "one three-hop source is verified against concrete source and general runner"
)]
fn symbolic_three_jump_artifacts_replay_encrypted_operands_in_general_runner() -> Result<(), String>
{
    let fixture = OwnedFixture::new()?;
    let mut logical = vec!["input"];
    logical.extend(["nop"].repeat(25));
    logical.push("jump");
    logical.extend(["nop"].repeat(29));
    logical.push("jump");
    logical.extend(["nop"].repeat(15));
    logical.extend(["jump", "output", "halt"]);

    for (profile_id, profile, capsule, input) in [
        ("malbolge-1998", historical_profile(), false, 0u8),
        ("malbolge-2026", current_profile(), true, 255u8),
    ] {
        let target = fixture.path(&format!("{profile_id}-three-auto.malbolge"));
        let manual_path = fixture.path(&format!("{profile_id}-three-concrete.malbolge"));
        let result = emit_auto(profile_id, &target, &logical, capsule)?;
        if !result.status.success() {
            return Err(format!(
                "three-hop auto-layout rejected: {}",
                String::from_utf8_lossy(&result.stderr)
            ));
        }
        let artifact = fs::read(&target).map_err(|error| error.to_string())?;
        let source = if capsule {
            let restored = parse_capsule(&artifact)
                .map_err(|error| format!("three-hop capsule parser: {error:?}"))?
                .ok_or("three-hop capsule marker absent")?;
            if restored.profile().id() != profile.id() {
                return Err(String::from("three-hop profile changed"));
            }
            restored.payload().to_vec()
        } else {
            artifact
        };
        let explicit = source_on_success(
            &emit(profile_id, &manual_path, &multi_jump_tokens())?,
            &manual_path,
        )?;
        if source != explicit || source.len() != 127 || source.get(72).copied() != Some(90) {
            return Err(String::from(
                "three-hop source differs from concrete profile layout",
            ));
        }
        let mut vm = ProfileMachine::from_source(profile, &source, vec![input])
            .map_err(|error| format!("three-hop source load: {error:?}"))?;
        if !matches!(vm.run(75), Ok(RunOutcome::Terminated { steps: 75, .. }))
            || vm.output() != [input]
            || vm
                .memory_word(72)
                .map_err(|error| format!("operand: {error:?}"))?
                != 124
        {
            return Err(String::from("three-hop VM cipher/operand witness mismatch"));
        }
        let mut child = Command::new(env!("CARGO_BIN_EXE_malbolge"))
            .arg(&target)
            .arg("--input-stdin")
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .spawn()
            .map_err(|error| format!("three-hop general runner launch: {error}"))?;
        let mut stdin = child
            .stdin
            .take()
            .ok_or("missing stdin for three-hop runner")?;
        stdin
            .write_all(&[input])
            .map_err(|error| format!("three-hop binary input: {error}"))?;
        drop(stdin);
        let output = child
            .wait_with_output()
            .map_err(|error| format!("three-hop runner result: {error}"))?;
        if !output.status.success() || output.stdout != [input] || !output.stderr.is_empty() {
            return Err(format!("real three-hop runner mismatch: {output:?}"));
        }
    }
    Ok(())
}
