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
//   - End-to-end argument-policy evidence for the top-level CLI.
// - Must-Not:
//   - Compile or execute guest programs.
// - Allows:
//   - Inputs: standalone and combined help arguments.
//   - Outputs: exact status and diagnostic assertions.
//   - Side effects: child process execution only.
// - Split-When:
//   - Split when another argument family gains independent policy.
// - Merge-When:
//   - Merge when the CLI composition owns direct parser unit tests.
// - Summary:
//   - Fail-closed help argument regression evidence.
// - Description:
//   - Proves help cannot mask malformed or contradictory arguments.
// - Usage:
//   - Collected by the repository Cargo test suite.
// - Defaults:
//   - Only standalone help succeeds.
//

//! End-to-end top-level CLI argument-policy evidence.

use std::process::Command;

use malbolge as _;

#[test]
fn help_is_accepted_only_as_the_sole_argument() -> Result<(), String> {
    for help in ["--help", "-h"] {
        let output = Command::new(env!("CARGO_BIN_EXE_malbolge"))
            .arg(help)
            .output()
            .map_err(|error| format!("run standalone help: {error}"))?;
        if !output.status.success()
            || !String::from_utf8_lossy(&output.stdout)
                .contains("Usage: malbolge <program.c|program.malbolge>")
            || !output.stderr.is_empty()
        {
            return Err(format!(
                concat!(
                    "standalone help failed: {}: status={} ",
                    "stdout={} stderr={}",
                ),
                help,
                output.status,
                String::from_utf8_lossy(&output.stdout),
                String::from_utf8_lossy(&output.stderr),
            ));
        }
    }
    for arguments in [["--help", "unexpected"], ["-h", "source.c"]] {
        let output = Command::new(env!("CARGO_BIN_EXE_malbolge"))
            .args(arguments)
            .output()
            .map_err(|error| format!("run combined help: {error}"))?;
        let stderr = String::from_utf8_lossy(&output.stderr);
        if output.status.success()
            || !output.stdout.is_empty()
            || !stderr.contains("--help cannot be combined")
        {
            return Err(format!(
                concat!(
                    "combined help did not fail closed: {:?}: ",
                    "status={} stdout={} stderr={}",
                ),
                arguments,
                output.status,
                String::from_utf8_lossy(&output.stdout),
                stderr,
            ));
        }
    }
    Ok(())
}

#[test]
fn missing_source_is_a_diagnostic_not_help() -> Result<(), String> {
    let output = Command::new(env!("CARGO_BIN_EXE_malbolge"))
        .output()
        .map_err(|error| format!("run CLI without arguments: {error}"))?;
    let stderr = String::from_utf8_lossy(&output.stderr);
    if !output.status.success()
        && output.stdout.is_empty()
        && stderr.contains("expected source path; use --help for usage")
    {
        Ok(())
    } else {
        Err(format!(
            concat!(
                "missing-source policy mismatch: status={} ",
                "stdout={} stderr={}",
            ),
            output.status,
            String::from_utf8_lossy(&output.stdout),
            stderr,
        ))
    }
}
