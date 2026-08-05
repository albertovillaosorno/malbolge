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
//   - End-to-end capsule dispatch evidence for the top-level CLI.
// - Must-Not:
//   - Rebuild capsule framing or infer profile identity from the payload.
// - Allows:
//   - Inputs: checked-in annual/2026.3 vectors and one checksum mutation.
//   - Outputs: exact status, EOF byte, and diagnostic assertions.
//   - Side effects: temporary capsule files removed after each invocation.
// - Split-When:
//   - Split when another capsule version needs independent dispatch policy.
// - Merge-When:
//   - Merge when the CLI owns direct capsule parser unit tests.
// - Summary:
//   - Published capsules dispatch and checksum tampering fails closed.
// - Description:
//   - Proves capsule dispatch and checksum rejection precede classic fallback.
// - Usage:
//   - Collected by the repository Cargo test suite.
// - Defaults:
//   - Valid frames emit profile EOF; malformed frames emit nothing.
//

//! End-to-end CLI capsule dispatch evidence.

use std::env::temp_dir;
use std::fs::{remove_file, write};
use std::path::PathBuf;
use std::process::{Command, id};
use std::str::from_utf8;

use malbolge as _;

const ANNUAL_CAPSULE_HEX: &str = include_str!(concat!(
    "compatibility/capsule/",
    "current-profile-capsule.hex",
));
const EXPECTED_EOF_OUTPUT: &[u8] = &[0x78];
const VERSIONED_CAPSULE_HEX: &str = include_str!(concat!(
    "compatibility/capsule/",
    "malbolge-2026.3-capsule.hex",
));

struct TemporaryCapsule {
    path: PathBuf,
}

impl TemporaryCapsule {
    fn from_bytes(label: &str, source: &[u8]) -> Result<Self, String> {
        let path = temp_dir()
            .join(format!("malbolge-cli-capsule-{}-{label}.malbolge", id()));
        write(&path, source)
            .map_err(|error| format!("write capsule fixture: {error}"))?;
        Ok(Self { path })
    }

    fn new(label: &str, source: &str) -> Result<Self, String> {
        Self::from_bytes(label, &decode_hex(source)?)
    }
}

impl Drop for TemporaryCapsule {
    fn drop(&mut self) {
        let _ignored = remove_file(&self.path);
    }
}

fn decode_hex(source: &str) -> Result<Vec<u8>, String> {
    let digits = source
        .bytes()
        .filter(|byte| !byte.is_ascii_whitespace())
        .collect::<Vec<_>>();
    let (pairs, remainder) = digits.as_chunks::<2>();
    if !remainder.is_empty() {
        return Err(String::from("capsule fixture has an odd hex digit count"));
    }
    pairs
        .iter()
        .map(|pair| {
            let text = from_utf8(pair).map_err(|error| {
                format!("capsule hex is not ASCII: {error}")
            })?;
            u8::from_str_radix(text, 16).map_err(|error| {
                format!("capsule hex byte is invalid: {error}")
            })
        })
        .collect()
}

fn assert_capsule_dispatch(label: &str, source: &str) -> Result<(), String> {
    let capsule = TemporaryCapsule::new(label, source)?;
    let output = Command::new(env!("CARGO_BIN_EXE_malbolge"))
        .arg(&capsule.path)
        .output()
        .map_err(|error| format!("run capsule CLI: {error}"))?;
    if output.status.success()
        && output.stdout == EXPECTED_EOF_OUTPUT
        && output.stderr.is_empty()
    {
        Ok(())
    } else {
        Err(format!(
            concat!(
                "capsule dispatch mismatch for {}: status={} ",
                "stdout={:?} stderr={}",
            ),
            label,
            output.status,
            output.stdout,
            String::from_utf8_lossy(&output.stderr),
        ))
    }
}

#[test]
fn published_capsules_dispatch_before_classic_fallback() -> Result<(), String> {
    assert_capsule_dispatch("annual", ANNUAL_CAPSULE_HEX)?;
    assert_capsule_dispatch("2026-3", VERSIONED_CAPSULE_HEX)
}

#[test]
fn tampered_capsule_fails_before_classic_fallback() -> Result<(), String> {
    let mut bytes = decode_hex(ANNUAL_CAPSULE_HEX)?;
    let checksum_byte = bytes
        .last_mut()
        .ok_or_else(|| String::from("annual capsule fixture is empty"))?;
    *checksum_byte = match *checksum_byte {
        b' ' => 9,
        9 => b' ',
        other => {
            return Err(format!(
                "capsule transport ended with non-whitespace byte {other}",
            ));
        },
    };
    let capsule = TemporaryCapsule::from_bytes("tampered", &bytes)?;
    let output = Command::new(env!("CARGO_BIN_EXE_malbolge"))
        .arg(&capsule.path)
        .output()
        .map_err(|error| format!("run tampered capsule CLI: {error}"))?;
    let stderr = String::from_utf8_lossy(&output.stderr);
    if !output.status.success()
        && output.stdout.is_empty()
        && stderr.contains("Malbolge capsule parsing failed")
    {
        Ok(())
    } else {
        Err(format!(
            concat!(
                "tampered capsule did not fail closed: status={} ",
                "stdout={:?} stderr={}",
            ),
            output.status, output.stdout, stderr,
        ))
    }
}
