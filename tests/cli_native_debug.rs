// File:
//   - cli_native_debug.rs
// Path:
//   - tests/cli_native_debug.rs
//
// Copyright:
//   - Copyright (c) 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - MIT
// Confidential:
//   - false
// License-File:
//   - LICENSE
// Path-Rule:
//   - All paths in this header are repository-root relative.
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
// Related documents:
// - cli/README.md
// - examples/self_host/hello-world/README.md
//
// Large file:
//   - false
//

//! End-to-end native C debug-run evidence for exact guest byte output.

use std::path::Path;
use std::process::Command;

use malbolge as _;

const EXPECTED_OUTPUT: &[u8] = b"Hello, World!\n";

#[test]
fn freestanding_hello_world_debug_run_preserves_exact_bytes()
-> Result<(), String> {
    let root = Path::new(env!("CARGO_MANIFEST_DIR"));
    let source = root.join("examples/self_host/hello-world/main.c");
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
