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
use std::iter::repeat_with;
use std::path::{Path, PathBuf};
use std::process::{Command, Output, id};
use std::sync::atomic::{AtomicUsize, Ordering};

use malbolge::{
    ProfileMachine, RunOutcome, current_profile, decode_profile_instruction, historical_profile,
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
    reason = "the standard Drop implementation owns all safe fixture cleanup"
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
