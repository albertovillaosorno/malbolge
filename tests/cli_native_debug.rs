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
use std::path::Path;
#[cfg(windows)]
use std::path::PathBuf;
use std::process::Command;
#[cfg(windows)]
use std::process::id;

use malbolge as _;

const EXPECTED_OUTPUT: &[u8] = b"Hello, World!\n";

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
fn freestanding_hello_world_debug_run_preserves_exact_bytes()
-> Result<(), String> {
    let root = Path::new(env!("CARGO_MANIFEST_DIR"));
    let source = root
        .join("src/examples/programs/contract/self_host/hello-world/main.c");
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
