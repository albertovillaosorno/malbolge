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
//   - Bounded CLI decoding, VM preflight and no-overwrite artifact publication.
// - Must-Not:
//   - Infer guest semantics from host arguments or publish unverified source.
// - Allows:
//   - Inputs: exact canonical profile ID, file path and closed opcode tokens.
//   - Outputs: one complete raw graphical `.malbolge` file.
//   - Side effects: same-directory staging and atomic no-clobber hard link.
// - Split-When:
//   - A full typed-IR machine lowering input/serialization format is admitted.
// - Merge-When:
//   - General backend owns equivalent publication with the same guarantees.
// - Summary:
//   - Publishes only complete executable machine-subset source artifacts.
// - Description:
//   - Requires explicit profile, validates admitted source with a real VM.
// - Usage:
//   - `--profile malbolge-2026 --output hello.malbolge -- input output halt`.
// - Defaults:
//   - Never overwrites a target or exposes a partially written target path.
//

//! Closed bounded machine-subset CLI with independently checked target source.

use std::env;
use std::ffi::{OsStr, OsString};
use std::fs::{self, OpenOptions};
use std::io::{self, Write as _};
use std::path::{Path, PathBuf};
use std::process::{ExitCode, id};

use malbolge::{ProfileMachine, RunOutcome, target_profile};

use crate::layout::{
    LinearOpcode, LinearProfileIdentity, admit_linear_layout, encode_linear_layout,
};

const PROFILE_ARG: &str = "--profile";
const OUTPUT_ARG: &str = "--output";
const DELIMITER_ARG: &str = "--";
const MAX_OPERATIONS: usize = 4096;
const MALBOLGE_EXTENSION: &str = "malbolge";

#[derive(Debug)]
struct CommandSpec {
    operations: Vec<LinearOpcode>,
    output: PathBuf,
    profile: String,
}

fn parse_operation(token: &str) -> Result<LinearOpcode, String> {
    match token {
        "crazy" => Ok(LinearOpcode::CrazyData),
        "halt" => Ok(LinearOpcode::Halt),
        "input" => Ok(LinearOpcode::InputWord),
        "nop" => Ok(LinearOpcode::NoOperation),
        "output" => Ok(LinearOpcode::OutputByte),
        "relocate" => Ok(LinearOpcode::RelocateDataPointer),
        "rotate" => Ok(LinearOpcode::RotateData),
        _ => {
            let Some(raw) = token.strip_prefix("jump:") else {
                return Err(format!("unsupported machine opcode: {token}"));
            };
            if raw.is_empty() || !raw.bytes().all(|byte| byte.is_ascii_digit()) {
                return Err(String::from(
                    "jump target must be an unsigned decimal address",
                ));
            }
            let target = raw
                .parse::<u32>()
                .map_err(|error| format!("jump target exceeds supported code address: {error}"))?;
            Ok(LinearOpcode::JumpForward { target })
        }
    }
}

fn parse_arguments(mut arguments: impl Iterator<Item = OsString>) -> Result<CommandSpec, String> {
    if arguments.next().as_deref() != Some(OsStr::new(PROFILE_ARG)) {
        return Err(String::from("expected --profile <canonical-id>"));
    }
    let profile = arguments
        .next()
        .ok_or("missing target profile")?
        .into_string()
        .map_err(|_error| String::from("profile must be UTF-8"))?;
    if arguments.next().as_deref() != Some(OsStr::new(OUTPUT_ARG)) {
        return Err(String::from("expected --output <path>.malbolge"));
    }
    let output = PathBuf::from(arguments.next().ok_or("missing output path")?);
    if arguments.next().as_deref() != Some(OsStr::new(DELIMITER_ARG)) {
        return Err(String::from("expected -- before opcode tokens"));
    }
    let mut operations = Vec::new();
    for raw_token in arguments {
        if operations.len() >= MAX_OPERATIONS {
            return Err(String::from("too many machine opcode tokens"));
        }
        let token = raw_token
            .into_string()
            .map_err(|_error| String::from("opcode token must be UTF-8"))?;
        operations.push(parse_operation(&token)?);
    }
    Ok(CommandSpec {
        operations,
        output,
        profile,
    })
}

fn publish_new(path: &Path, bytes: &[u8]) -> Result<(), String> {
    if path.extension() != Some(OsStr::new(MALBOLGE_EXTENSION)) {
        return Err(String::from("output must have a .malbolge extension"));
    }
    let name = path
        .file_name()
        .and_then(OsStr::to_str)
        .ok_or("output needs a UTF-8 filename")?;
    let staged = path.with_file_name(format!(".{name}.stage-{}", id()));
    let mut file = OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(&staged)
        .map_err(|error| format!("cannot open fresh stage: {error}"))?;
    let outcome = (|| {
        file.write_all(bytes)
            .map_err(|error| format!("stage write failed: {error}"))?;
        file.sync_all()
            .map_err(|error| format!("stage sync failed: {error}"))?;
        drop(file);
        if fs::read(&staged).map_err(|error| format!("stage reopen failed: {error}"))? != bytes {
            return Err(String::from("staged output differs from verified source"));
        }
        fs::hard_link(&staged, path)
            .map_err(|error| format!("cannot publish new target: {error}"))?;
        Ok(())
    })();
    drop(fs::remove_file(&staged));
    outcome
}

fn execute(spec: &CommandSpec) -> Result<(), String> {
    let profile = target_profile(&spec.profile).ok_or("unknown canonical target profile")?;
    let artifact = encode_linear_layout(profile, &spec.operations)
        .map_err(|error| format!("layout rejected: {error:?}"))?;
    let admitted = admit_linear_layout(
        profile,
        &spec.operations,
        artifact.source(),
        LinearProfileIdentity {
            fingerprint: artifact.profile_fingerprint(),
            id: artifact.profile_id(),
        },
    )
    .map_err(|error| format!("independent source admission failed: {error:?}"))?;
    let mut vm = ProfileMachine::from_source(profile, admitted.source(), Vec::new())
        .map_err(|error| format!("normative VM rejected source: {error:?}"))?;
    let steps = admitted.executed_code_positions().len();
    if !matches!(vm.run(steps), Ok(RunOutcome::Terminated { steps: count, .. }) if count == steps) {
        return Err(String::from(
            "normative VM did not halt at the proven code step",
        ));
    }
    publish_new(&spec.output, admitted.source())?;
    let notice = format!(
        "emitted {} graphical bytes for {} ({steps} VM steps)\n",
        admitted.source().len(),
        admitted.profile_id(),
    );
    drop(io::stderr().lock().write_all(notice.as_bytes()));
    Ok(())
}

/// Executes the closed validated layout CLI and returns a failure exit code
/// without publishing partial target artifacts.
#[must_use]
pub fn run() -> ExitCode {
    match parse_arguments(env::args_os().skip(1)).and_then(|spec| execute(&spec)) {
        Ok(()) => ExitCode::SUCCESS,
        Err(error) => {
            let notice = format!("malbolge_layout: {error}\n");
            drop(io::stderr().lock().write_all(notice.as_bytes()));
            ExitCode::FAILURE
        }
    }
}
