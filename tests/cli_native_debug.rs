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
//   - End-to-end evidence for host-only native C debug execution.
// - Must-Not:
//   - Claim C-to-Malbolge lowering or guest-runtime conformance.
// - Allows:
//   - Inputs: the checked-in freestanding Hello World C example.
//   - Outputs: exact inherited stdout bytes and process status assertions.
//   - Side effects: one temporary native executable cleaned by the CLI.
// - Split-When:
//   - Split when another native adapter needs an independent fixture.
// - Merge-When:
//   - Merge when another test owns the same complete CLI debug-run boundary.
// - Summary:
//   - Exact native debug execution for the freestanding guest-output example.
// - Description:
//   - Proves repository-root discovery, adapter linkage, and binary stdout.
// - Usage:
//   - Collected by the repository Cargo test suite.
// - Defaults:
//   - Any compiler, linker, process, or byte mismatch fails closed.
//

//! End-to-end native C debug-run evidence for exact guest byte output.

#[cfg(windows)]
use std::env::temp_dir;
#[cfg(windows)]
use std::fs::{remove_file, write};
#[cfg(target_os = "linux")]
use std::io::Write as _;
use std::path::Path;
#[cfg(windows)]
use std::path::PathBuf;
use std::process::Command;
#[cfg(target_os = "linux")]
use std::process::Stdio;
#[cfg(windows)]
use std::process::id;

use malbolge as _;

const EXPECTED_OUTPUT: &[u8] = b"Hello, World!\n";
const STRESS_FIXTURES: [&str; 5] = [
    "arithmetic_stress.c",
    "control_flow_stress.c",
    "memory_permutation_stress.c",
    "call_chain_stress.c",
    "state_machine_stress.c",
];
const STRESS_OUTPUT: &[u8] = b"OK\n";

#[cfg(windows)]
struct InvalidTemporaryCSource {
    path: PathBuf,
}

#[cfg(windows)]
impl InvalidTemporaryCSource {
    fn create() -> Result<Self, String> {
        let path = temp_dir()
            .join(format!("malbolge-cli-invalid-clang-proof-{}.c", id()));
        write(
            &path,
            b"int main(void) { this is not valid C; }
",
        )
        .map_err(|error| format!("write invalid C proof: {error}"))?;
        Ok(Self { path })
    }
}

#[cfg(windows)]
impl Drop for InvalidTemporaryCSource {
    fn drop(&mut self) {
        let _ignored = remove_file(&self.path);
    }
}

#[test]
fn hello_world_stress_debug_run_preserves_exact_bytes() -> Result<(), String> {
    let root = Path::new(env!("CARGO_MANIFEST_DIR"));
    let source = root
        .join("src/examples/programs/contract/self_host")
        .join("hello-world/hello_world_stress.c");
    let output = Command::new(env!("CARGO_BIN_EXE_malbolge"))
        .current_dir(root)
        .arg(source)
        .output()
        .map_err(|error| format!("failed to run native debug CLI: {error}"))?;

    if !output.status.success() {
        return Err(format!(
            "native debug CLI failed: status={} stderr={}",
            output.status,
            String::from_utf8_lossy(&output.stderr),
        ));
    }
    if output.stdout != EXPECTED_OUTPUT {
        let observed = &output.stdout;
        let expected = EXPECTED_OUTPUT;
        return Err(format!(
            "stdout mismatch: got={observed:?} want={expected:?}"
        ));
    }
    if !output.stderr.is_empty() {
        return Err(format!(
            "native debug stderr was not empty: {}",
            String::from_utf8_lossy(&output.stderr),
        ));
    }
    Ok(())
}

#[test]
fn compact_stress_fixtures_reach_exact_oracles() -> Result<(), String> {
    let root = Path::new(env!("CARGO_MANIFEST_DIR"));
    let directory =
        root.join("src/examples/programs/contract/self_host/stress");

    for fixture in STRESS_FIXTURES {
        let source = directory.join(fixture);
        let output = Command::new(env!("CARGO_BIN_EXE_malbolge"))
            .current_dir(root)
            .arg(&source)
            .output()
            .map_err(|error| format!("failed to run {fixture}: {error}"))?;
        if !output.status.success()
            || output.stdout != STRESS_OUTPUT
            || !output.stderr.is_empty()
        {
            return Err(format!(
                concat!(
                    "stress fixture failed: fixture={} status={} ",
                    "stdout={:?} stderr={}"
                ),
                fixture,
                output.status,
                output.stdout,
                String::from_utf8_lossy(&output.stderr),
            ));
        }
    }
    Ok(())
}

#[cfg(target_os = "linux")]
#[test]
fn snake_script_grows_and_quits_without_hosted_guest_abi() -> Result<(), String>
{
    let root = Path::new(env!("CARGO_MANIFEST_DIR"));
    let source = root
        .join("src/examples/programs/contract/self_host")
        .join("snake/snake_classic.c");
    let mut child = Command::new(env!("CARGO_BIN_EXE_malbolge"))
        .current_dir(root)
        .arg(source)
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|error| format!("failed to start Snake debug run: {error}"))?;
    let mut stdin = child
        .stdin
        .take()
        .ok_or_else(|| String::from("Snake debug stdin was not piped"))?;
    stdin
        .write_all(b"dddssaq\n")
        .map_err(|error| format!("failed to write Snake commands: {error}"))?;
    drop(stdin);
    let output = child.wait_with_output().map_err(|error| {
        format!("failed to wait for Snake debug run: {error}")
    })?;

    if !output.status.success() {
        return Err(format!(
            "Snake debug run failed: status={} stderr={}",
            output.status,
            String::from_utf8_lossy(&output.stderr),
        ));
    }
    if !output.stderr.is_empty() {
        return Err(format!(
            "Snake debug stderr was not empty: {}",
            String::from_utf8_lossy(&output.stderr),
        ));
    }
    if !output.stdout.starts_with(b"\x1b[2J\x1b[HMalbolge Snake")
        || !output.stdout.ends_with(b"Bye. Score: 1 Length: 4\n")
    {
        return Err(format!(
            "Snake scripted output contract failed: stdout={:?}",
            output.stdout,
        ));
    }
    Ok(())
}

#[cfg(windows)]
#[test]
fn repo_clang_is_selected_without_host_compiler_path() -> Result<(), String> {
    let root = Path::new(env!("CARGO_MANIFEST_DIR"));
    let source = InvalidTemporaryCSource::create()?;
    let output = Command::new(env!("CARGO_BIN_EXE_malbolge"))
        .current_dir(root)
        .env_remove("MALBOLGE_CC")
        .env("PATH", "")
        .arg(&source.path)
        .output()
        .map_err(|error| {
            format!("failed to run repository-local C debug CLI: {error}")
        })?;
    let stderr = String::from_utf8_lossy(&output.stderr);
    if output.status.success()
        || !output.stdout.is_empty()
        || !stderr.contains("C compilation failed with status")
        || stderr.contains("no C compiler found")
    {
        return Err(format!(
            concat!(
                "repository-local compiler selection mismatch: status={} ",
                "stdout={:?} stderr={}",
            ),
            output.status, output.stdout, stderr,
        ));
    }
    Ok(())
}
