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
    ProfileMachine, RunOutcome, Termination,
    canonicalize_annotated_source, current_profile,
    decode_profile_instruction, historical_profile,
};

const ANALYSIS_SOURCE: &[u8] = b"b&&;@L";
const OUTPUT_SOURCE: &[u8] = b"ubO";
// Three-byte fixture plus one overflow probe through the opened descriptor.
const SOURCE_PROBE_BYTES: u64 = 4;

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
            let read = opened.take(SOURCE_PROBE_BYTES).read_to_end(bytes)?;
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
            let read = opened.take(SOURCE_PROBE_BYTES).read_to_end(bytes)?;
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
    fs::create_dir_all(&original).map_err(|error| error.to_string())?;
    fs::create_dir_all(&alternate).map_err(|error| error.to_string())?;
    let first = original.join("source.malbolge");
    let second = alternate.join("source.malbolge");
    fs::write(&first, OUTPUT_SOURCE).map_err(|error| error.to_string())?;
    fs::hard_link(&first, &second).map_err(|error| error.to_string())?;
    let link = directory.join("current");
    symlink(&original, &link).map_err(|error| error.to_string())?;
    let path = link.join("source.malbolge");
    let result =
        cli::read_decompiler_source_with_reader(&path, |opened, bytes| {
            let read = opened.take(SOURCE_PROBE_BYTES).read_to_end(bytes)?;
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
            opened.take(SOURCE_PROBE_BYTES).read_to_end(bytes)
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
    let cases: [DuplicateCliCase; 4] = [
        (&["--profile", "a", "--profile", "b"], "duplicate --profile"),
        (
            &["--source-format", "raw", "--source-format", "annotated"],
            "duplicate --source-format",
        ),
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
fn annotated_render_round_trips_exact_profile_bytes_and_vm_observations() -> Result<(), String> {
    for profile in [historical_profile(), current_profile()] {
        let raw = b"u\t b\r\nO";
        let rendered =
            decompiler::render_annotated(profile, raw).map_err(|error| error.to_string())?;
        let normalized = canonicalize_annotated_source(rendered.as_bytes())
            .map_err(|error| error.to_string())?;
        if normalized.bytes() != OUTPUT_SOURCE
            || normalized.locations().len() != OUTPUT_SOURCE.len()
            || rendered
                != decompiler::render_annotated(profile, OUTPUT_SOURCE)
                    .map_err(|error| error.to_string())?
            || !rendered.contains("# initial-range=")
            || !rendered.contains("end-control=halt")
            || !rendered.contains("self-modification=invalidates-static-decode")
        {
            return Err(format!("annotated render drifted: {rendered}"));
        }
        for (index, location) in normalized.locations().iter().enumerate() {
            if rendered.as_bytes().get(location.offset()) != OUTPUT_SOURCE.get(index)
                || location.column() == 0
                || location.line() == 0
            {
                return Err(format!("annotated source map drifted at {index}"));
            }
        }
        let mut baseline = ProfileMachine::from_source(profile, OUTPUT_SOURCE, vec![0x41])
            .map_err(|error| error.to_string())?;
        let mut annotated =
            ProfileMachine::from_annotated_source(profile, rendered.as_bytes(), vec![0x41])
                .map_err(|error| error.to_string())?;
        let expected = baseline.run(8).map_err(|error| error.to_string())?;
        let observed = annotated.run(8).map_err(|error| error.to_string())?;
        if observed != expected
            || annotated.output() != baseline.output()
            || annotated.input_consumed() != baseline.input_consumed()
        {
            return Err(format!(
                "annotated VM changed execution for {}",
                profile.id()
            ));
        }
    }
    Ok(())
}

#[test]
fn annotated_render_marks_initial_indirect_and_halt_boundaries() -> Result<(), String> {
    let rendered = decompiler::render_annotated(historical_profile(), ANALYSIS_SOURCE)
        .map_err(|error| error.to_string())?;
    let recovered =
        canonicalize_annotated_source(rendered.as_bytes()).map_err(|error| error.to_string())?;
    if recovered.bytes() != ANALYSIS_SOURCE
        || !rendered.contains("initial-range=0..0")
        || !rendered.contains("end-control=indirect-code-pointer-from-data")
        || !rendered.contains("end-control=halt")
    {
        return Err(format!(
            "initial-state annotation boundaries drifted: {rendered}"
        ));
    }
    if decompiler::render_annotated(historical_profile(), b"not malbolge").is_ok() {
        return Err(String::from("invalid source was annotated"));
    }
    Ok(())
}

#[test]
fn annotated_render_bounded_width_preserves_exact_line_column_map()
-> Result<(), String> {
    let mut canonical = Vec::new();
    for position in 0u32..150 {
        let code = (33u8..=126)
            .find(|&byte| {
                decode_profile_instruction(u32::from(byte), position) == Some(b'o')
            })
            .ok_or_else(|| format!("no graphical no-op at {position}"))?;
        canonical.push(code);
    }
    let rendered = decompiler::render_annotated(historical_profile(), &canonical)
        .map_err(|error| error.to_string())?;
    let recovered = canonicalize_annotated_source(rendered.as_bytes())
        .map_err(|error| error.to_string())?;
    if recovered.bytes() != canonical
        || !rendered.contains("initial-range=0..63")
        || !rendered.contains("initial-range=64..127")
        || !rendered.contains("initial-range=128..149")
        || recovered.locations().len() != canonical.len()
    {
        return Err(String::from("bounded initial-region rendering drifted"));
    }
    for (position, location) in recovered.locations().iter().enumerate() {
        let expected_line = 4 + position.div_euclid(64) * 2;
        let expected_column = position.rem_euclid(64) + 1;
        if location.line() != expected_line
            || location.column() != expected_column
            || rendered.as_bytes().get(location.offset()) != canonical.get(position)
        {
            return Err(format!(
                "annotated map drift at {position}: {location:?}"
            ));
        }
    }
    Ok(())
}

#[test]
fn annotated_render_preserves_line_start_hash_code_after_initial_jump()
-> Result<(), String> {
    let mut source = Vec::new();
    for position in 0u32..128 {
        let byte = (33u8..=126)
            .find(|&cell| {
                decode_profile_instruction(u32::from(cell), position) == Some(b'o')
            })
            .ok_or_else(|| format!("no no-op byte at {position}"))?;
        source.push(byte);
    }
    let hash_position = (2u32..127)
        .find(|&position| {
            matches!(
                decode_profile_instruction(u32::from(b'#'), position),
                Some(b'i' | b'j' | b'*' | b'p' | b'<' | b'/' | b'v' | b'o')
            )
        })
        .ok_or_else(|| String::from("no admitted hash position"))?;
    let previous = hash_position.saturating_sub(1);
    let jump = (33u8..=126)
        .find(|&cell| decode_profile_instruction(u32::from(cell), previous) == Some(b'i'))
        .ok_or_else(|| String::from("no initial indirect predecessor"))?;
    *source.get_mut(usize::try_from(previous).map_err(|error| error.to_string())?)
        .ok_or_else(|| String::from("missing predecessor"))? = jump;
    *source.get_mut(usize::try_from(hash_position).map_err(|error| error.to_string())?)
        .ok_or_else(|| String::from("missing hash code cell"))? = b'#';
    let profile = historical_profile();
    let rendered = decompiler::render_annotated(profile, &source)
        .map_err(|error| error.to_string())?;
    let normalized = canonicalize_annotated_source(rendered.as_bytes())
        .map_err(|error| error.to_string())?;
    let location = normalized.locations()
        .get(usize::try_from(hash_position).map_err(|error| error.to_string())?)
        .ok_or_else(|| String::from("missing hash source location"))?;
    if normalized.bytes() != source
        || location.column() != 1
        || rendered.as_bytes().get(location.offset()) != Some(&b'#')
    {
        return Err(String::from("line-start hash was parsed as a comment"));
    }
    let mut canonical = ProfileMachine::from_source(profile, &source, Vec::new())
        .map_err(|error| error.to_string())?;
    let mut annotated = ProfileMachine::from_annotated_source(
        profile, rendered.as_bytes(), Vec::new(),
    )
    .map_err(|error| error.to_string())?;
    if canonical.run(8) != annotated.run(8)
        || canonical.output() != annotated.output()
    {
        return Err(String::from("line-start hash changed VM execution"));
    }
    Ok(())
}

#[test]
fn annotated_cli_emits_canonicalizable_output_to_stdout_and_file() -> Result<(), String> {
    let directory = temporary_cli_inputs()?;
    let source = directory.join("raw.malbolge");
    let target = directory.join("view.annotated.malbolge");
    fs::write(&source, OUTPUT_SOURCE).map_err(|error| error.to_string())?;
    let executable = env!("CARGO_BIN_EXE_malbolge_decompile");
    let args = [
        "--profile",
        "malbolge-1998",
        "--representation",
        "annotated",
    ];
    let stdout = Command::new(executable)
        .args(args)
        .arg(&source)
        .output()
        .map_err(|error| error.to_string())?;
    let file = Command::new(executable)
        .args(args)
        .arg(&source)
        .arg("--output")
        .arg(&target)
        .output()
        .map_err(|error| error.to_string())?;
    let file_bytes = fs::read(&target).map_err(|error| error.to_string())?;
    fs::remove_dir_all(&directory).map_err(|error| error.to_string())?;
    let recovered =
        canonicalize_annotated_source(&stdout.stdout).map_err(|error| error.to_string())?;
    if !stdout.status.success()
        || !file.status.success()
        || !file.stdout.is_empty()
        || !stdout.stderr.is_empty()
        || !file.stderr.is_empty()
        || stdout.stdout != file_bytes
        || recovered.bytes() != OUTPUT_SOURCE
    {
        return Err(format!("annotated CLI drifted: {stdout:?}; {file:?}"));
    }
    Ok(())
}

#[test]
fn annotated_cli_requires_explicit_input_format_for_annotated_views()
-> Result<(), String> {
    let directory = temporary_cli_inputs()?;
    let raw = directory.join("raw.malbolge");
    let annotated = directory.join("view.annotated.malbolge");
    let malformed = directory.join("invalid.annotated.malbolge");
    fs::write(&raw, OUTPUT_SOURCE).map_err(|error| error.to_string())?;
    let executable = env!("CARGO_BIN_EXE_malbolge_decompile");
    let base = ["--profile", "malbolge-1998", "--representation", "analysis"];
    let render = Command::new(executable)
        .args(["--profile", "malbolge-1998", "--representation", "annotated"])
        .arg(&raw).arg("--output").arg(&annotated).output()
        .map_err(|error| error.to_string())?;
    let baseline = Command::new(executable).args(base).arg(&raw).output()
        .map_err(|error| error.to_string())?;
    let explicitly_annotated = Command::new(executable)
        .args(base).args(["--source-format", "annotated"])
        .arg(&annotated).output().map_err(|error| error.to_string())?;
    let default_raw = Command::new(executable)
        .args(base).arg(&annotated).output()
        .map_err(|error| error.to_string())?;
    let explicit_raw = Command::new(executable)
        .args(base).args(["--source-format", "raw"])
        .arg(&annotated).output().map_err(|error| error.to_string())?;
    fs::write(&malformed, b"# malformed \x80\nubO")
        .map_err(|error| error.to_string())?;
    let rejected_presentation = Command::new(executable)
        .args(base).args(["--source-format", "annotated"])
        .arg(&malformed).output().map_err(|error| error.to_string())?;
    fs::remove_dir_all(&directory)
        .map_err(|error| error.to_string())?;
    if !render.status.success()
        || !baseline.status.success()
        || !explicitly_annotated.status.success()
        || explicitly_annotated.stdout != baseline.stdout
        || default_raw.status.success()
        || explicit_raw.status.success()
        || rejected_presentation.status.success()
        || !String::from_utf8_lossy(&rejected_presentation.stderr)
            .contains("invalid annotated source")
    {
        return Err(format!(
            "annotated input mode violated raw isolation: \
{render:?}; {baseline:?}; {explicitly_annotated:?}; \
{default_raw:?}; {explicit_raw:?}; {rejected_presentation:?}"
        ));
    }
    Ok(())
}

#[test]
fn annotated_cli_preserves_c_and_annotated_output_on_reentry()
-> Result<(), String> {
    let directory = temporary_cli_inputs()?;
    let raw = directory.join("raw.malbolge");
    let annotated = directory.join("view.annotated.malbolge");
    fs::write(&raw, OUTPUT_SOURCE).map_err(|error| error.to_string())?;
    let executable = env!("CARGO_BIN_EXE_malbolge_decompile");
    let render = Command::new(executable)
        .args(["--profile", "malbolge-1998", "--representation", "annotated"])
        .arg(&raw).arg("--output").arg(&annotated).output()
        .map_err(|error| error.to_string())?;
    let raw_c = Command::new(executable)
        .args(["--profile", "malbolge-1998", "--representation", "c"])
        .arg(&raw).output().map_err(|error| error.to_string())?;
    let annotated_c = Command::new(executable)
        .args(["--profile", "malbolge-1998", "--representation", "c"])
        .args(["--source-format", "annotated"])
        .arg(&annotated).output().map_err(|error| error.to_string())?;
    let reannotated = Command::new(executable)
        .args(["--profile", "malbolge-1998", "--representation", "annotated"])
        .args(["--source-format", "annotated"])
        .arg(&annotated).output().map_err(|error| error.to_string())?;
    let generated = fs::read(&annotated).map_err(|error| error.to_string())?;
    fs::remove_dir_all(&directory).map_err(|error| error.to_string())?;
    if !render.status.success()
        || !raw_c.status.success()
        || !annotated_c.status.success()
        || raw_c.stdout != annotated_c.stdout
        || !reannotated.status.success()
        || reannotated.stdout != generated
    {
        return Err(format!(
            "annotated reentry changed C or annotated output: \
{render:?}; {raw_c:?}; {annotated_c:?}; {reannotated:?}"
        ));
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
