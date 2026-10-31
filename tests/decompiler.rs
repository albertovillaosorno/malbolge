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
//   - Determinism, profile binding, source validation, and C-rendering
//   - fixtures.
// - Must-Not:
//   - Depend on historical third-party program bytes.
// - Allows:
//   - Inputs: project-owned synthetic Malbolge fixtures and canonical profiles.
//   - Outputs: assertions over generated C source.
//   - Side effects: test-local temporary input files and CLI child processes.
// - Split-When:
//   - Split when executable C differential tests need independent toolchain
//   - setup.
// - Merge-When:
//   - Merge when decompiler verification gains a unified product test suite.
// - Summary:
//   - Proves the general C renderer is deterministic and profile-explicit.
// - Description:
//   - Uses only project-owned tiny sources already present in VM conformance.
// - Usage:
//   - Auto-discovered by Cargo test.
// - Defaults:
//   - No museum specimen is embedded in tests.
//

//! Product Malbolge decompiler conformance.

#[path = "../src/tooling/decompiler/domain/analysis.rs"]
pub mod analysis;
#[path = "../src/tooling/decompiler/composition/cli.rs"]
pub mod cli;
#[path = "../src/tooling/decompiler/application/render.rs"]
pub mod decompiler;

use std::env::temp_dir;
use std::fs::{self, File};
use std::io::Read as _;
use std::path::{Path, PathBuf};
use std::process::{Command, Output, id};
use std::time::{SystemTime, UNIX_EPOCH};

use malbolge::{
    ProfileMachine, RunOutcome, Termination, current_profile,
    historical_profile,
};

const ANALYSIS_SOURCE: &[u8] = b"b&&;@L";
const OUTPUT_SOURCE: &[u8] = b"ubO";

type DuplicateCliCase = (&'static [&'static str], &'static str);

fn temporary_cli_inputs() -> Result<PathBuf, String> {
    let nonce = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map_err(|error| format!("timestamp fixture: {error}"))?
        .as_nanos();
    let directory =
        temp_dir().join(format!("malbolge-decompiler-input-{}-{nonce}", id()));
    fs::create_dir_all(&directory)
        .map_err(|error| format!("create input fixture: {error}"))?;
    Ok(directory)
}

fn run_analysis_input(path: &Path) -> Result<Output, String> {
    Command::new(env!("CARGO_BIN_EXE_malbolge_decompile"))
        .args(["--profile", "malbolge-1998"])
        .args(["--representation", "analysis"])
        .arg(path)
        .output()
        .map_err(|error| format!("execute decompiler CLI: {error}"))
}

#[test]
fn cli_rejects_oversized_regular_source_before_rendering() -> Result<(), String>
{
    let directory = temporary_cli_inputs()?;
    let source = directory.join("oversized.malbolge");
    let file = File::create(&source)
        .map_err(|error| format!("create oversized source: {error}"))?;
    file.set_len(1_048_577)
        .map_err(|error| format!("extend sparse source: {error}"))?;
    drop(file);
    let output = run_analysis_input(&source)?;
    fs::remove_dir_all(&directory)
        .map_err(|error| format!("remove source fixture: {error}"))?;
    let diagnostic = String::from_utf8_lossy(&output.stderr);
    if output.status.success()
        || !diagnostic.contains("regular file at most 1 MiB")
        || !output.stdout.is_empty()
    {
        return Err(format!("oversized source admitted: {diagnostic}"));
    }
    Ok(())
}

#[cfg(target_os = "linux")]
#[test]
fn cli_rejects_fifo_and_fifo_symlink_without_waiting() -> Result<(), String> {
    use std::os::unix::fs::symlink;

    let directory = temporary_cli_inputs()?;
    let fifo = directory.join("blocked-input.fifo");
    let alias = directory.join("blocked-link.fifo");
    let status = Command::new("/usr/bin/mkfifo")
        .arg(&fifo)
        .status()
        .map_err(|error| format!("create FIFO: {error}"))?;
    if !status.success() {
        return Err(format!("mkfifo failed: {status}"));
    }
    symlink(&fifo, &alias)
        .map_err(|error| format!("create FIFO symlink: {error}"))?;
    let mut failures = Vec::new();
    for source in [&fifo, &alias] {
        let output = Command::new("/usr/bin/timeout")
            .arg("2s")
            .arg(env!("CARGO_BIN_EXE_malbolge_decompile"))
            .args(["--profile", "malbolge-1998"])
            .args(["--representation", "analysis"])
            .arg(source)
            .output()
            .map_err(|error| format!("run bounded FIFO CLI: {error}"))?;
        let diagnostic = String::from_utf8_lossy(&output.stderr);
        if output.status.code() == Some(124i32)
            || output.status.success()
            || !diagnostic.contains("regular file at most 1 MiB")
        {
            failures.push(format!("{}: {diagnostic}", source.display()));
        }
    }
    fs::remove_dir_all(&directory)
        .map_err(|error| format!("remove FIFO fixture: {error}"))?;
    if !failures.is_empty() {
        return Err(format!("FIFO acquisition unsafe: {failures:?}"));
    }
    Ok(())
}

#[cfg(unix)]
#[test]
fn cli_rejects_same_length_source_inode_substitution_during_read()
-> Result<(), String> {
    let directory = temporary_cli_inputs()?;
    let source = directory.join("original.malbolge");
    let replacement = directory.join("replacement.malbolge");
    fs::write(&source, OUTPUT_SOURCE).map_err(|error| error.to_string())?;
    fs::write(&replacement, OUTPUT_SOURCE)
        .map_err(|error| error.to_string())?;
    let result =
        cli::read_decompiler_source_with_reader(&source, |opened, bytes| {
            let read = opened.read_to_end(bytes)?;
            fs::rename(&replacement, &source)?;
            Ok(read)
        });
    fs::remove_dir_all(&directory)
        .map_err(|error| format!("remove source fixture: {error}"))?;
    if !result.as_ref().is_err_and(|error| {
        error
            .to_string()
            .contains("decompiler source changed during read")
    }) {
        return Err(format!("source inode swap was admitted: {result:?}"));
    }
    Ok(())
}

#[cfg(unix)]
#[test]
fn cli_rejects_same_length_source_rewrite_during_read() -> Result<(), String> {
    let directory = temporary_cli_inputs()?;
    let source = directory.join("rewritten.malbolge");
    fs::write(&source, OUTPUT_SOURCE).map_err(|error| error.to_string())?;
    let result =
        cli::read_decompiler_source_with_reader(&source, |opened, bytes| {
            let read = opened.read_to_end(bytes)?;
            fs::write(&source, b"ctO")?;
            File::open(&source)?
                .set_times(fs::FileTimes::new().set_modified(UNIX_EPOCH))?;
            Ok(read)
        });
    fs::remove_dir_all(&directory)
        .map_err(|error| format!("remove source fixture: {error}"))?;
    if !result.as_ref().is_err_and(|error| {
        error
            .to_string()
            .contains("decompiler source changed during read")
    }) {
        return Err(format!(
            "in-place source rewrite was admitted: {result:?}"
        ));
    }
    Ok(())
}

#[cfg(target_os = "linux")]
#[test]
fn cli_rejects_equal_inode_parent_alias_swap_during_read() -> Result<(), String>
{
    use std::os::unix::fs::symlink;

    let directory = temporary_cli_inputs()?;
    let original = directory.join("original");
    let alternate = directory.join("alternate");
    fs::create_dir(&original).map_err(|error| error.to_string())?;
    fs::create_dir(&alternate).map_err(|error| error.to_string())?;
    let first = original.join("source.malbolge");
    let second = alternate.join("source.malbolge");
    fs::write(&first, OUTPUT_SOURCE).map_err(|error| error.to_string())?;
    fs::hard_link(&first, &second).map_err(|error| error.to_string())?;
    let link = directory.join("current");
    symlink(&original, &link).map_err(|error| error.to_string())?;
    let path = link.join("source.malbolge");
    let result =
        cli::read_decompiler_source_with_reader(&path, |opened, bytes| {
            let read = opened.read_to_end(bytes)?;
            fs::remove_file(&link)?;
            symlink(&alternate, &link)?;
            Ok(read)
        });
    fs::remove_dir_all(&directory)
        .map_err(|error| format!("remove source fixture: {error}"))?;
    if !result.as_ref().is_err_and(|error| {
        error
            .to_string()
            .contains("decompiler source changed during read")
    }) {
        return Err(format!(
            "same-inode source alias swap admitted: {result:?}"
        ));
    }
    Ok(())
}

#[cfg(unix)]
#[test]
fn cli_accepts_stable_regular_source_symlink() -> Result<(), String> {
    use std::os::unix::fs::symlink;

    let directory = temporary_cli_inputs()?;
    let source = directory.join("original.malbolge");
    let alias = directory.join("alias.malbolge");
    fs::write(&source, OUTPUT_SOURCE).map_err(|error| error.to_string())?;
    symlink(&source, &alias).map_err(|error| error.to_string())?;
    let result =
        cli::read_decompiler_source_with_reader(&alias, |opened, bytes| {
            opened.read_to_end(bytes)
        });
    fs::remove_dir_all(&directory)
        .map_err(|error| format!("remove source fixture: {error}"))?;
    if !matches!(result.as_deref(), Ok(bytes) if bytes == OUTPUT_SOURCE) {
        return Err(format!(
            "stable regular-file symlink rejected: {result:?}"
        ));
    }
    Ok(())
}

#[test]
fn cli_rejects_duplicate_semantic_options() -> Result<(), String> {
    let cases: [DuplicateCliCase; 3] = [
        (&["--profile", "a", "--profile", "b"], "duplicate --profile"),
        (
            &["--representation", "c", "--representation", "c"],
            "duplicate --representation",
        ),
        (&["--output", "a", "-o", "b"], "duplicate --output"),
    ];
    for (arguments, expected) in cases {
        let output = Command::new(env!("CARGO_BIN_EXE_malbolge_decompile"))
            .args(arguments)
            .output()
            .map_err(|error| format!("run decompiler CLI: {error}"))?;
        if output.status.success() {
            return Err(format!(
                "duplicate CLI option unexpectedly succeeded: {arguments:?}"
            ));
        }
        let stderr = String::from_utf8_lossy(&output.stderr);
        if !stderr.contains(expected) {
            return Err(format!(
                "duplicate CLI diagnostic missing {expected:?}: {stderr}"
            ));
        }
    }
    Ok(())
}

#[test]
fn cli_help_is_exclusive() -> Result<(), String> {
    let help = Command::new(env!("CARGO_BIN_EXE_malbolge_decompile"))
        .arg("--help")
        .output()
        .map_err(|error| format!("run decompiler help: {error}"))?;
    if !help.status.success()
        || !String::from_utf8_lossy(&help.stdout).contains("usage:")
    {
        return Err(String::from("standalone help did not succeed"));
    }
    for arguments in [["--help", "--unknown"], ["--profile", "--help"], [
        "-h",
        "input.malbolge",
    ]] {
        let output = Command::new(env!("CARGO_BIN_EXE_malbolge_decompile"))
            .args(arguments)
            .output()
            .map_err(|error| format!("run combined help: {error}"))?;
        let stderr = String::from_utf8_lossy(&output.stderr);
        if output.status.success()
            || !stderr.contains("--help cannot be combined")
        {
            return Err(format!(
                "combined help did not fail closed: {arguments:?}: {stderr}"
            ));
        }
    }
    Ok(())
}

#[test]
fn c_render_is_deterministic_and_profile_bound() -> Result<(), String> {
    let first = decompiler::render_c(current_profile(), OUTPUT_SOURCE)
        .map_err(|error| error.to_string())?;
    let second = decompiler::render_c(current_profile(), OUTPUT_SOURCE)
        .map_err(|error| error.to_string())?;
    if first != second {
        return Err(String::from("decompiler output is not deterministic"));
    }
    let profile = current_profile();
    let word_trits =
        format!("#define MB_WORD_TRITS UINT32_C({})", profile.word_trits());
    let input_instruction = format!(
        "#define MB_INPUT_INSTRUCTION UINT32_C({})",
        profile.input_instruction(),
    );
    let output_instruction = format!(
        "#define MB_OUTPUT_INSTRUCTION UINT32_C({})",
        profile.output_instruction(),
    );
    if !first.contains(profile.fingerprint())
        || !first.contains(&word_trits)
        || !first.contains(&input_instruction)
        || !first.contains(&output_instruction)
        || !first.contains("#define MB_NON_GRAPHICAL_NO_PROGRESS 0")
        || !first.contains("uint32_t *memory")
        || first.contains("malloc(")
    {
        return Err(String::from("current-profile C metadata is incomplete"));
    }
    Ok(())
}

#[test]
fn c_render_distinguishes_historical_geometry() -> Result<(), String> {
    let current = decompiler::render_c(current_profile(), OUTPUT_SOURCE)
        .map_err(|error| error.to_string())?;
    let historical = decompiler::render_c(historical_profile(), OUTPUT_SOURCE)
        .map_err(|error| error.to_string())?;
    if current == historical {
        return Err(String::from("profile change did not change generated C"));
    }
    if historical.contains("#define MB_WORD_TRITS UINT32_C(10)")
        && historical.contains("#define MB_MEMORY_WORDS UINT32_C(59049)")
        && historical.contains("#define MB_INPUT_INSTRUCTION UINT32_C(47)")
        && historical.contains("#define MB_OUTPUT_INSTRUCTION UINT32_C(60)")
        && historical.contains("#define MB_NON_GRAPHICAL_NO_PROGRESS 1")
    {
        Ok(())
    } else {
        Err(String::from("historical C geometry is missing"))
    }
}

#[test]
fn c_render_ignores_vertical_tab_source_whitespace() -> Result<(), String> {
    let plain = decompiler::render_c(historical_profile(), OUTPUT_SOURCE)
        .map_err(|error| error.to_string())?;
    let spaced =
        decompiler::render_c(historical_profile(), &[b'u', 0x0b, b'b', b'O'])
            .map_err(|error| error.to_string())?;
    if plain == spaced {
        Ok(())
    } else {
        Err(String::from("vertical tab changed generated C"))
    }
}

#[test]
fn c_render_rejects_invalid_source() {
    let observed = decompiler::render_c(historical_profile(), b"not malbolge");
    assert!(observed.is_err(), "invalid source unexpectedly decompiled");
}

#[test]
fn c_render_contains_atomic_post_jump_encryption_logic() -> Result<(), String> {
    let rendered = decompiler::render_c(historical_profile(), OUTPUT_SOURCE)
        .map_err(|error| error.to_string())?;
    let jump = rendered
        .find("next_code_pointer = memory[data_pointer];")
        .ok_or_else(|| String::from("jump lowering missing"))?;
    let target = rendered
        .find("encryption_target = writes_memory")
        .ok_or_else(|| String::from("encryption target lowering missing"))?;
    let commit = rendered
        .find("memory[next_code_pointer] = encrypted;")
        .ok_or_else(|| String::from("encryption commit missing"))?;
    if jump < target && target < commit {
        Ok(())
    } else {
        Err(String::from("post-jump encryption ordering is wrong"))
    }
}

#[test]
fn c_render_checks_output_capacity_at_emission() -> Result<(), String> {
    let rendered = decompiler::render_c(current_profile(), OUTPUT_SOURCE)
        .map_err(|error| error.to_string())?;
    if rendered.contains("output_capacity < step_budget")
        || rendered.contains("step_budget != 0 && output == NULL")
    {
        return Err(String::from(
            "generated C retains budget-sized output precondition",
        ));
    }
    let capacity = rendered
        .find("if (emits_output && output_len >= output_capacity)")
        .ok_or_else(|| String::from("dynamic output capacity check missing"))?;
    let commit = rendered
        .find("memory[next_code_pointer] = encrypted;")
        .ok_or_else(|| String::from("encryption commit missing"))?;
    if rendered.contains("MB_STATUS_OUTPUT_EXHAUSTED = 5")
        && rendered.contains("output_capacity != 0 && output == NULL")
        && capacity < commit
    {
        Ok(())
    } else {
        Err(String::from(
            "output capacity rejection is not explicit and atomic",
        ))
    }
}

#[test]
fn initial_listing_uses_normative_translation_table() -> Result<(), String> {
    let rendered = decompiler::render_c(historical_profile(), OUTPUT_SOURCE)
        .map_err(|error| error.to_string())?;
    for expected in [
        "0: 117 -> /  input byte into A",
        "1:  98 -> <  output low byte of A",
        "2:  79 -> v  halt",
    ] {
        if !rendered.contains(expected) {
            return Err(format!(
                "missing translated listing entry: {expected}"
            ));
        }
    }
    Ok(())
}

#[test]
fn synthetic_roundtrip_fixture_matches_normative_vm() -> Result<(), String> {
    let mut machine =
        ProfileMachine::from_source(historical_profile(), OUTPUT_SOURCE, vec![
            0x41,
        ])
        .map_err(|error| error.to_string())?;
    let outcome = machine.run(8).map_err(|error| error.to_string())?;
    if outcome
        != (RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 3,
        })
        || machine.output() != b"A"
        || machine.input_consumed() != 1
    {
        return Err(String::from("synthetic roundtrip VM baseline changed"));
    }
    Ok(())
}

#[test]
fn analysis_report_classifies_initial_state_without_guessing()
-> Result<(), String> {
    let rendered =
        decompiler::render_analysis(historical_profile(), ANALYSIS_SOURCE)
            .map_err(|error| error.to_string())?;
    for expected in [
        "profile_id=malbolge-1998",
        "indirect-targets=unresolved",
        concat!(
            "cell position=0 raw=98 decoded=i ",
            "control=indirect-code-pointer-from-data data=read-data-cell ",
            "accumulator=none post_step_encryption=yes"
        ),
        concat!(
            "cell position=1 raw=38 decoded=* control=sequential ",
            "data=read-write-data-cell accumulator=write ",
            "post_step_encryption=yes"
        ),
        concat!(
            "cell position=5 raw=76 decoded=v control=halt data=none ",
            "accumulator=none post_step_encryption=no"
        ),
    ] {
        if !rendered.contains(expected) {
            return Err(format!("analysis report missing: {expected}"));
        }
    }
    Ok(())
}

#[test]
fn cli_emits_analysis_representation() -> Result<(), String> {
    let source = concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/tests/compatibility/specification/interpreter-io-roundtrip.malbolge"
    );
    let output = Command::new(env!("CARGO_BIN_EXE_malbolge_decompile"))
        .args([
            "--profile",
            "malbolge-1998",
            "--representation",
            "analysis",
            source,
        ])
        .output()
        .map_err(|error| format!("run analysis CLI: {error}"))?;
    let stdout = String::from_utf8_lossy(&output.stdout);
    if !output.status.success()
        || !stdout.contains("Malbolge initial-state analysis")
        || !stdout.contains("profile_id=malbolge-1998")
        || !stdout.contains("decoded=/")
        || !stdout.contains("decoded=<")
        || !stdout.contains("decoded=v")
    {
        return Err(format!(
            "analysis CLI did not emit expected report: {stdout}"
        ));
    }
    Ok(())
}
