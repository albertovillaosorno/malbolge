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
//   - End-to-end capsule dispatch evidence for the top-level CLI.
// - Must-Not:
//   - Rebuild capsule framing or infer profile identity from the payload.
// - Allows:
//   - Inputs: checked-in annual/2026.3 vectors, public capsule builder/profile,
//     and one checksum mutation.
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
use std::fs::{read, remove_file, write};
use std::path::{Path, PathBuf};
use std::process::{Command, id};
use std::str::from_utf8;

use malbolge::{build_capsule, historical_profile};

const ANNUAL_CAPSULE_HEX: &str = include_str!(concat!(
    "compatibility/capsule/",
    "current-profile-capsule.hex",
));
const EXPECTED_EOF_OUTPUT: &[u8] = &[0x78];
const PROFILE_WORKER_ARG_COUNT_ENV: &str =
    "MALBOLGE_PROFILE_RESIDENT_WORKER_ARG_COUNT";
const PROFILE_WORKER_CWD_ENV: &str = "MALBOLGE_PROFILE_RESIDENT_WORKER_CWD";
const PROFILE_WORKER_ENV: &str = "MALBOLGE_PROFILE_RESIDENT_WORKER";
const PROFILE_WORKER_MARKER_ENV: &str = "MALBOLGE_PROFILE_WORKER_MARKER";
const UNAVAILABLE_WORKER: &str = r#"
import os
import sys

sys.stdin.buffer.read()
with open(os.environ["MALBOLGE_PROFILE_WORKER_MARKER"], "wb") as marker:
    marker.write(b"called")
sys.stdout.buffer.write(
    b"MBPRN2\x00\x00"
    + (1).to_bytes(4, "little")
    + (0).to_bytes(4, "little")
)
"#;
const HISTORICAL_OVERSIZED_WORDS: usize = 59_050;
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

struct TemporaryMarker {
    path: PathBuf,
}

impl TemporaryMarker {
    fn new(label: &str) -> Self {
        let path = temp_dir().join(format!(
            "malbolge-cli-profile-worker-{}-{label}.marker",
            id(),
        ));
        let _ignored = remove_file(&path);
        Self { path }
    }
}

impl Drop for TemporaryMarker {
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

fn clean_cli_command() -> Command {
    let mut command = Command::new(env!("CARGO_BIN_EXE_malbolge"));
    let _clean = command
        .env_remove(PROFILE_WORKER_ENV)
        .env_remove(PROFILE_WORKER_ARG_COUNT_ENV)
        .env_remove(PROFILE_WORKER_CWD_ENV);
    for index in 0usize..32 {
        let _removed = command.env_remove(format!(
            "MALBOLGE_PROFILE_RESIDENT_WORKER_ARG_{index}"
        ));
    }
    command
}

fn configured_worker_command(marker: &Path) -> Command {
    let root = Path::new(env!("CARGO_MANIFEST_DIR"));
    let mut command = clean_cli_command();
    let _configured = command
        .env(PROFILE_WORKER_ENV, validation_python(root))
        .env(PROFILE_WORKER_ARG_COUNT_ENV, "2")
        .env("MALBOLGE_PROFILE_RESIDENT_WORKER_ARG_0", "-c")
        .env("MALBOLGE_PROFILE_RESIDENT_WORKER_ARG_1", UNAVAILABLE_WORKER)
        .env(PROFILE_WORKER_MARKER_ENV, marker);
    command
}

fn validation_python(root: &Path) -> PathBuf {
    if cfg!(windows) {
        root.join(".dependencies/python/3.14.6/Scripts/python-jig.cmd")
    } else {
        root.join(".dependencies/python/3.14.6/bin/python-jig")
    }
}

fn assert_capsule_dispatch(label: &str, source: &str) -> Result<(), String> {
    let capsule = TemporaryCapsule::new(label, source)?;
    let output = clean_cli_command()
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
fn configured_worker_is_not_used_for_historical_profile() -> Result<(), String>
{
    let root = Path::new(env!("CARGO_MANIFEST_DIR"));
    let source = read(root.join(
        "tests/compatibility/specification/interpreter-io-roundtrip.malbolge",
    ))
    .map_err(|error| format!("read historical CLI fixture: {error}"))?;
    let bytes = build_capsule(historical_profile(), &source)
        .map_err(|error| format!("build historical CLI capsule: {error}"))?;
    let capsule = TemporaryCapsule::from_bytes("historical-worker", &bytes)?;
    let baseline = clean_cli_command()
        .arg(&capsule.path)
        .output()
        .map_err(|error| format!("run historical CLI baseline: {error}"))?;
    let marker = TemporaryMarker::new("historical");
    let configured = configured_worker_command(&marker.path)
        .arg(&capsule.path)
        .output()
        .map_err(|error| format!("run configured historical CLI: {error}"))?;
    if configured.status != baseline.status
        || configured.stdout != baseline.stdout
        || configured.stderr != baseline.stderr
        || marker.path.exists()
    {
        return Err(format!(
            concat!(
                "historical worker isolation mismatch: ",
                "baseline={:?}/{:?}/{:?} configured={:?}/{:?}/{:?} marker={}",
            ),
            baseline.status,
            baseline.stdout,
            baseline.stderr,
            configured.status,
            configured.stdout,
            configured.stderr,
            marker.path.exists(),
        ));
    }
    Ok(())
}

#[test]
fn current_capsule_uses_configured_worker_with_safe_fallback()
-> Result<(), String> {
    let capsule =
        TemporaryCapsule::new("configured-worker", ANNUAL_CAPSULE_HEX)?;
    let marker = TemporaryMarker::new("current");
    let output = configured_worker_command(&marker.path)
        .arg(&capsule.path)
        .output()
        .map_err(|error| format!("run configured current CLI: {error}"))?;
    if output.status.success()
        && output.stdout == EXPECTED_EOF_OUTPUT
        && output.stderr.is_empty()
        && marker.path.is_file()
    {
        Ok(())
    } else {
        Err(format!(
            concat!(
                "configured current worker mismatch: status={} stdout={:?} ",
                "stderr={} marker={}",
            ),
            output.status,
            output.stdout,
            String::from_utf8_lossy(&output.stderr),
            marker.path.exists(),
        ))
    }
}

#[test]
fn current_capsule_rejects_invalid_worker_argument_count() -> Result<(), String>
{
    let capsule = TemporaryCapsule::new("invalid-worker", ANNUAL_CAPSULE_HEX)?;
    let root = Path::new(env!("CARGO_MANIFEST_DIR"));
    let output = clean_cli_command()
        .env(PROFILE_WORKER_ENV, validation_python(root))
        .env(PROFILE_WORKER_ARG_COUNT_ENV, "33")
        .arg(&capsule.path)
        .output()
        .map_err(|error| {
            format!("run invalid configured current CLI: {error}")
        })?;
    let stderr = String::from_utf8_lossy(&output.stderr);
    if !output.status.success()
        && output.stdout.is_empty()
        && stderr.contains(PROFILE_WORKER_ARG_COUNT_ENV)
        && stderr.contains("exceeds 32")
    {
        Ok(())
    } else {
        Err(format!(
            concat!(
                "invalid worker count did not fail closed: status={} ",
                "stdout={:?} stderr={}",
            ),
            output.status, output.stdout, stderr,
        ))
    }
}

#[test]
fn historical_capsule_capacity_uses_profile_diagnostic() -> Result<(), String> {
    let payload = vec![b'!'; HISTORICAL_OVERSIZED_WORDS];
    let bytes =
        build_capsule(historical_profile(), &payload).map_err(|error| {
            format!("build historical overflow capsule: {error}")
        })?;
    let capsule = TemporaryCapsule::from_bytes("historical-overflow", &bytes)?;
    let output =
        clean_cli_command()
            .arg(&capsule.path)
            .output()
            .map_err(|error| {
                format!("run historical overflow capsule CLI: {error}")
            })?;
    let stderr = String::from_utf8_lossy(&output.stderr);
    if output.status.success()
        || !output.stdout.is_empty()
        || !stderr.contains("MALBOLGE-PROFILE-002")
        || !stderr.contains("constraint=historical-profile-ceiling")
        || !stderr.contains("required_memory_words=59050")
    {
        return Err(format!(
            concat!(
                "historical capsule capacity diagnostic mismatch: status={} ",
                "stdout={:?} stderr={}",
            ),
            output.status, output.stdout, stderr,
        ));
    }
    Ok(())
}

#[test]
fn malformed_capsule_fails_before_classic_fallback() -> Result<(), String> {
    let mut bytes = decode_hex(ANNUAL_CAPSULE_HEX)?;
    let symbol = bytes.get_mut(7 + 64).ok_or_else(|| {
        String::from("annual capsule lacks post-magic framing")
    })?;
    *symbol = b'X';
    let capsule = TemporaryCapsule::from_bytes("malformed-symbol", &bytes)?;
    let output = clean_cli_command()
        .arg(&capsule.path)
        .output()
        .map_err(|error| format!("run malformed capsule CLI: {error}"))?;
    let stderr = String::from_utf8_lossy(&output.stderr);
    if !output.status.success()
        && output.stdout.is_empty()
        && stderr.contains("MALBOLGE-CAPSULE-001")
    {
        Ok(())
    } else {
        Err(format!(
            concat!(
                "malformed capsule fell through: status={} ",
                "stdout={:?} stderr={}",
            ),
            output.status, output.stdout, stderr,
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
    let output = clean_cli_command()
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
