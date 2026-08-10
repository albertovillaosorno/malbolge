// Copyright:
//   - Copyright (c) 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - MIT
// Confidential:
//   - false
// License-File:
//   - LICENSE-MIT
//
// Boundary-Contract:
// - Owns:
//   - End-to-end raw Malbolge CLI semantic-authority evidence.
// - Must-Not:
//   - Treat specification comparison as the default execution route.
// - Allows:
//   - Inputs: the interpreter-authority roundtrip fixture with empty input.
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
use std::path::{Path, PathBuf};
use std::process::{id, Command};

use malbolge as _;

const EXPECTED_EOF_OUTPUT: &[u8] = &[0xa8];

struct TemporarySource {
    path: PathBuf,
}

impl TemporarySource {
    fn oversized() -> Result<Self, String> {
        let path = temp_dir().join(format!("malbolge-cli-oversized-{}.malbolge", id()));
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

#[test]
fn raw_source_uses_interpreter_authority() -> Result<(), String> {
    let root = Path::new(env!("CARGO_MANIFEST_DIR"));
    let source = root
        .join("tests")
        .join("compatibility")
        .join("specification")
        .join("interpreter-io-roundtrip.malbolge");
    let output = Command::new(env!("CARGO_BIN_EXE_malbolge"))
        .current_dir(root)
        .arg(source)
        .output()
        .map_err(|error| format!("run raw Malbolge CLI: {error}"))?;
    if !output.status.success() || output.stdout != EXPECTED_EOF_OUTPUT || !output.stderr.is_empty()
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
