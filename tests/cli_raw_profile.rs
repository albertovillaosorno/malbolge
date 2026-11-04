// Copyright:
//   - Copyright © 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - LicenseRef-Proprietary
// Confidential:
//   - true
// License-File:
//   - LICENSE
//
// Boundary-Contract:
// - Owns:
//   - End-to-end explicit unframed current-profile runner selection.
// - Must-Not:
//   - Infer profile identity from raw bytes or override capsule identity.
// - Allows:
//   - Inputs: canonical raw guest, binary stdin and selected-profile capsule.
//   - Outputs: exact VM bytes, step receipts and fail-closed diagnostics.
//   - Side effects: temporary test inputs cleaned on drop.
// - Split-When:
//   - A separate raw profile discovery protocol is introduced.
// - Merge-When:
//   - Another CLI test owns explicit raw-profile execution and rejection.
// - Summary:
//   - Raw current-profile guests run only under explicit profile selection.
// - Description:
//   - Proves direct raw execution and preserves capsule authority.
// - Usage:
//   - cargo test --test cli_raw_profile
// - Defaults:
//   - Without --raw-profile, raw Malbolge stays classic.
//

//! Opt-in raw profile dispatch through the public normative Malbolge runner.

use std::fs::{create_dir_all, remove_file, write};
use std::io::Write as _;
use std::path::{Path, PathBuf};
use std::process::{Command, Output, Stdio, id};
use std::time::{SystemTime, UNIX_EPOCH};

use malbolge::{build_capsule, current_profile};

// Independent compatibility fixture: /, <, v under malbolge-2026.
const CURRENT_RAW_SOURCE: &[u8] = b"ubO\n";
const CURRENT_PROFILE_ID: &str = "malbolge-2026";
const CURRENT_EOF_BYTE: u8 = 0x6a;

struct TemporarySource {
    path: PathBuf,
}

impl TemporarySource {
    fn new(label: &str, bytes: &[u8]) -> Result<Self, String> {
        let timestamp = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .map_err(|error| format!("clock unavailable: {error}"))?
            .as_nanos();
        let directory = Path::new(env!("CARGO_MANIFEST_DIR")).join(".temp");
        create_dir_all(&directory).map_err(|error| format!("prepare test directory: {error}"))?;
        let path = directory.join(format!(
            "cli-raw-profile-{}-{timestamp}-{label}.malbolge",
            id(),
        ));
        write(&path, bytes).map_err(|error| format!("write {label} test source: {error}"))?;
        Ok(Self { path })
    }
}

impl Drop for TemporarySource {
    fn drop(&mut self) {
        let _ignored = remove_file(&self.path);
    }
}

fn run_guest(path: &Path, args: &[&str], input: &[u8]) -> Result<Output, String> {
    let mut child = Command::new(env!("CARGO_BIN_EXE_malbolge"))
        .arg(path)
        .args(args)
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|error| format!("start guest VM: {error}"))?;
    let mut stdin = child.stdin.take().ok_or("missing child stdin")?;
    stdin
        .write_all(input)
        .map_err(|error| format!("send guest stdin: {error}"))?;
    drop(stdin);
    child
        .wait_with_output()
        .map_err(|error| format!("wait for guest VM: {error}"))
}

#[test]
fn selected_raw_current_profile_executes_exact_guest_io() -> Result<(), String> {
    let raw = TemporarySource::new("current", CURRENT_RAW_SOURCE)?;
    let eof = run_guest(
        &raw.path,
        &["--raw-profile", CURRENT_PROFILE_ID, "--report-steps"],
        &[],
    )?;
    if !eof.status.success()
        || eof.stdout != [CURRENT_EOF_BYTE]
        || eof.stderr != b"malbolge-steps-v1:3\n"
    {
        return Err(format!("current raw EOF dispatch mismatch: {eof:?}"));
    }
    let binary = run_guest(
        &raw.path,
        &[
            "--report-steps",
            "--input-stdin",
            "--raw-profile",
            CURRENT_PROFILE_ID,
        ],
        &[0xff],
    )?;
    if !binary.status.success()
        || binary.stdout != [0xff]
        || binary.stderr != b"malbolge-steps-v1:3\n"
    {
        return Err(format!("current raw binary dispatch mismatch: {binary:?}"));
    }
    Ok(())
}

#[test]
fn profile_override_never_reinterprets_a_capsule() -> Result<(), String> {
    let frame = build_capsule(current_profile(), CURRENT_RAW_SOURCE)
        .map_err(|error| format!("build current capsule: {error}"))?;
    let capsule = TemporarySource::new("capsule", &frame)?;
    let selected = run_guest(&capsule.path, &["--report-steps"], &[])?;
    if !selected.status.success()
        || selected.stdout != [CURRENT_EOF_BYTE]
        || selected.stderr != b"malbolge-steps-v1:3\n"
    {
        return Err(format!("capsule selection regressed: {selected:?}"));
    }
    let forbidden = run_guest(&capsule.path, &["--raw-profile", CURRENT_PROFILE_ID], &[])?;
    if forbidden.status.success()
        || !forbidden.stdout.is_empty()
        || !String::from_utf8_lossy(&forbidden.stderr)
            .contains("--raw-profile is only valid for unframed raw source")
    {
        return Err(format!(
            "capsule identity could be overridden: {forbidden:?}"
        ));
    }
    Ok(())
}

#[test]
fn raw_profile_arguments_fail_closed() -> Result<(), String> {
    let raw = TemporarySource::new("invalid-options", CURRENT_RAW_SOURCE)?;
    for (args, diagnostic) in [
        (
            vec!["--raw-profile"],
            "--raw-profile requires a canonical profile ID",
        ),
        (
            vec!["--raw-profile", "malbolge-unknown"],
            "unknown canonical raw profile",
        ),
        (
            vec![
                "--raw-profile",
                CURRENT_PROFILE_ID,
                "--raw-profile",
                CURRENT_PROFILE_ID,
            ],
            "at most once each",
        ),
        (
            vec![
                "--raw-profile",
                CURRENT_PROFILE_ID,
                "--input-stdin",
                "--input-stdin",
            ],
            "at most once each",
        ),
    ] {
        let output = run_guest(&raw.path, &args, &[])?;
        if output.status.success()
            || !output.stdout.is_empty()
            || !String::from_utf8_lossy(&output.stderr).contains(diagnostic)
        {
            return Err(format!(
                "invalid raw-profile arguments {args:?}: {output:?}"
            ));
        }
    }
    Ok(())
}
