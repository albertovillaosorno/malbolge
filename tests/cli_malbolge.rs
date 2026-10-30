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
//   - End-to-end raw Malbolge CLI semantic-authority evidence.
// - Must-Not:
//   - Treat specification comparison as the default execution route.
// - Allows:
//   - Inputs: the roundtrip fixture, exact binary stdin and oversized input.
//   - Outputs: exact EOF byte, status, and diagnostic assertions.
//   - Side effects: child process execution only.
// - Split-When:
//   - Split when capsule dispatch needs an independent CLI test surface.
// - Merge-When:
//   - Merge when another test owns raw CLI execution authority.
// - Summary:
//   - Raw source executes with interpreter-authority byte I/O.
// - Description:
//   - Proves slash input and less-than output through the installed binary.
// - Usage:
//   - Collected by the repository Cargo test suite.
// - Defaults:
//   - Empty input produces the historical EOF low byte.
//

//! End-to-end raw Malbolge CLI authority evidence.

use std::env::temp_dir;
use std::fs::{remove_file, write};
use std::io::Write as _;
use std::iter::once;
use std::path::{Path, PathBuf};
use std::process::{Command, Output, Stdio, id};

use malbolge as _;

const EXPECTED_EOF_OUTPUT: &[u8] = &[0xa8];
const MAX_STDIN_BYTES: usize = 256;
const OVERSIZED_STDIN_BYTES: usize = MAX_STDIN_BYTES + 1;
const ARBITRARY_INPUT_BYTE: &[u8] = &[0xff];
const EOF_BYTE: u8 = 0xa8;
const FOUR: usize = 4;

struct TemporarySource {
    path: PathBuf,
}

impl TemporarySource {
    fn echo_pairs(pairs: usize) -> Result<Self, String> {
        let path = temp_dir()
            .join(format!("malbolge-cli-echo-{}-{pairs}.malbolge", id()));
        let mut command = Command::new(env!("CARGO_BIN_EXE_malbolge_layout"));
        let _configured = command
            .args(["--profile", "malbolge-1998", "--output"])
            .arg(&path)
            .arg("--");
        for _ in 0..pairs {
            let _appended = command.args(["input", "output"]);
        }
        let output = command
            .arg("halt")
            .output()
            .map_err(|error| format!("emit classic echo source: {error}"))?;
        if !output.status.success() || !output.stdout.is_empty() {
            return Err(format!("classic echo emission rejected: {output:?}"));
        }
        Ok(Self { path })
    }

    fn oversized() -> Result<Self, String> {
        let path = temp_dir()
            .join(format!("malbolge-cli-oversized-{}.malbolge", id()));
        write(&path, vec![b'!'; 59_050])
            .map_err(|error| format!("write oversized source: {error}"))?;
        Ok(Self { path })
    }
}

impl Drop for TemporarySource {
    fn drop(&mut self) {
        let _ignored = remove_file(&self.path);
    }
}

fn roundtrip_fixture() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("tests")
        .join("compatibility")
        .join("specification")
        .join("interpreter-io-roundtrip.malbolge")
}

fn run_with_stdin(source: &Path, input: &[u8]) -> Result<Output, String> {
    let mut child = Command::new(env!("CARGO_BIN_EXE_malbolge"))
        .arg(source)
        .arg("--input-stdin")
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|error| format!("spawn binary-input CLI: {error}"))?;
    let mut stdin = child.stdin.take().ok_or("missing CLI stdin pipe")?;
    stdin
        .write_all(input)
        .map_err(|error| format!("send CLI bytes: {error}"))?;
    drop(stdin);
    child
        .wait_with_output()
        .map_err(|error| format!("receive binary-input CLI result: {error}"))
}

#[test]
fn explicit_guest_stdin_reads_exact_binary_byte() -> Result<(), String> {
    let output = run_with_stdin(&roundtrip_fixture(), ARBITRARY_INPUT_BYTE)?;
    if !output.status.success()
        || output.stdout != ARBITRARY_INPUT_BYTE
        || !output.stderr.is_empty()
    {
        return Err(format!("classic binary-input CLI mismatch: {output:?}"));
    }
    Ok(())
}

#[test]
fn explicit_empty_stdin_retains_historical_eof() -> Result<(), String> {
    let output = run_with_stdin(&roundtrip_fixture(), &[])?;
    if !output.status.success()
        || output.stdout != EXPECTED_EOF_OUTPUT
        || !output.stderr.is_empty()
    {
        return Err(format!("classic explicit EOF mismatch: {output:?}"));
    }
    Ok(())
}

#[test]
fn opt_in_guest_step_receipt_counts_classic_executed_instructions()
-> Result<(), String> {
    let source = TemporarySource::echo_pairs(4)?;
    let output = Command::new(env!("CARGO_BIN_EXE_malbolge"))
        .arg(&source.path)
        .arg("--report-steps")
        .output()
        .map_err(|error| format!("execute classic step receipt: {error}"))?;
    if !output.status.success()
        || output.stdout != vec![EOF_BYTE; FOUR]
        || output.stderr != b"malbolge-steps-v1:9\n"
    {
        return Err(format!("classic run step receipt mismatch: {output:?}"));
    }
    Ok(())
}

#[test]
fn binary_guest_steps_include_final_eof_and_are_order_independent()
-> Result<(), String> {
    let source = TemporarySource::echo_pairs(3)?;
    for flags in [["--input-stdin", "--report-steps"], [
        "--report-steps",
        "--input-stdin",
    ]] {
        let mut child = Command::new(env!("CARGO_BIN_EXE_malbolge"))
            .arg(&source.path)
            .args(flags)
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .spawn()
            .map_err(|error| format!("launch binary step receipt: {error}"))?;
        let mut stdin = child.stdin.take().ok_or("missing CLI stdin pipe")?;
        stdin
            .write_all(&[0x00, 0xff])
            .map_err(|error| format!("send guest binary bytes: {error}"))?;
        drop(stdin);
        let output = child.wait_with_output().map_err(|error| {
            format!("read binary guest step receipt: {error}")
        })?;
        if !output.status.success()
            || output.stdout != [0x00, 0xff, EOF_BYTE]
            || output.stderr != b"malbolge-steps-v1:7\n"
        {
            return Err(format!("binary step receipt mismatch: {output:?}"));
        }
    }
    Ok(())
}

#[test]
fn oversized_guest_stdin_fails_without_guest_execution() -> Result<(), String> {
    let oversized = vec![b'Z'; OVERSIZED_STDIN_BYTES];
    let output = run_with_stdin(&roundtrip_fixture(), &oversized)?;
    if output.status.success()
        || !output.stdout.is_empty()
        || !String::from_utf8_lossy(&output.stderr)
            .contains("guest stdin exceeds 256 byte limit")
    {
        return Err(format!("oversized stdin was admitted: {output:?}"));
    }
    Ok(())
}

#[test]
fn real_classic_vm_echoes_all_256_input_values_then_eof() -> Result<(), String>
{
    let source = TemporarySource::echo_pairs(OVERSIZED_STDIN_BYTES)?;
    let input = u8::MIN..=u8::MAX;
    let eof = EXPECTED_EOF_OUTPUT
        .first()
        .copied()
        .ok_or("missing EOF byte")?;
    let expected = input.chain(once(eof)).collect::<Vec<_>>();
    let input_slice = expected
        .get(..MAX_STDIN_BYTES)
        .ok_or("missing exact 256-byte input prefix")?;
    let output = run_with_stdin(&source.path, input_slice)?;
    if !output.status.success()
        || output.stdout != expected
        || !output.stderr.is_empty()
    {
        return Err(format!(
            "256-byte classic VM input/EOF mismatch: {output:?}"
        ));
    }
    Ok(())
}

#[test]
fn ambiguous_guest_input_flags_fail_before_vm_execution() -> Result<(), String>
{
    let output = Command::new(env!("CARGO_BIN_EXE_malbolge"))
        .arg(roundtrip_fixture())
        .args(["--input-stdin", "--input-stdin"])
        .output()
        .map_err(|error| format!("reject duplicate input flag: {error}"))?;
    if output.status.success()
        || !output.stdout.is_empty()
        || !String::from_utf8_lossy(&output.stderr)
            .contains("accepts --input-stdin and --report-steps")
    {
        return Err(format!("duplicate stdin flag admitted: {output:?}"));
    }
    Ok(())
}

#[test]
fn raw_source_uses_interpreter_authority() -> Result<(), String> {
    let root = Path::new(env!("CARGO_MANIFEST_DIR"));
    let source = roundtrip_fixture();
    let output = Command::new(env!("CARGO_BIN_EXE_malbolge"))
        .current_dir(root)
        .arg(source)
        .output()
        .map_err(|error| format!("run raw Malbolge CLI: {error}"))?;
    if !output.status.success()
        || output.stdout != EXPECTED_EOF_OUTPUT
        || !output.stderr.is_empty()
    {
        return Err(format!(
            concat!(
                "raw CLI authority mismatch: status={} ",
                "stdout={:?} stderr={}",
            ),
            output.status,
            output.stdout,
            String::from_utf8_lossy(&output.stderr),
        ));
    }
    Ok(())
}

#[test]
fn raw_source_capacity_uses_profile_diagnostic() -> Result<(), String> {
    let source = TemporarySource::oversized()?;
    let output = Command::new(env!("CARGO_BIN_EXE_malbolge"))
        .arg(&source.path)
        .output()
        .map_err(|error| format!("run oversized raw Malbolge CLI: {error}"))?;
    let stderr = String::from_utf8_lossy(&output.stderr);
    if output.status.success()
        || !output.stdout.is_empty()
        || !stderr.contains("MALBOLGE-PROFILE-002")
        || !stderr.contains("constraint=historical-profile-ceiling")
        || !stderr.contains("required_memory_words=59050")
    {
        return Err(format!(
            concat!(
                "raw source capacity diagnostic mismatch: status={} ",
                "stdout={:?} stderr={}",
            ),
            output.status, output.stdout, stderr,
        ));
    }
    Ok(())
}
