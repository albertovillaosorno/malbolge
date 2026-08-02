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
//   - User-facing argument and filesystem policy for general decompilation.
// - Must-Not:
//   - Reimplement Malbolge semantics or infer a target profile silently.
// - Allows:
//   - Inputs: exact profile ID, explicit representation, local source/output
//   - paths.
//   - Outputs: rendered text on stdout or one selected local file.
//   - Side effects: local filesystem reads/writes and stdout output.
// - Split-When:
//   - Split when another frontend has materially different acquisition policy.
// - Merge-When:
//   - Merge when one CLI framework owns all reverse-engineering commands.
// - Summary:
//   - Explicit-profile, explicit-representation Malbolge decompiler frontend.
// - Description:
//   - Keeps transport/presentation choices separate from semantic rendering.
// - Usage:
//   - Delegated by the `malbolge_decompile` Cargo composition root.
// - Defaults:
//   - No implicit profile or output representation.
//

//! User-facing CLI policy for general Malbolge decompilation.

use std::env;
use std::ffi::OsString;
use std::fs::{read, write};
use std::io::{Error as IoError, Result as IoResult, Write as _, stdout};
use std::path::PathBuf;

use malbolge::target_profile;

use crate::decompiler;

const USAGE: &str = concat!(
    "usage: malbolge_decompile --profile ID --representation c INPUT ",
    "[--output FILE]"
);

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum OutputRepresentation {
    CSource,
}

#[derive(Debug)]
struct Arguments {
    input: PathBuf,
    output: Option<PathBuf>,
    profile_id: String,
    representation: OutputRepresentation,
}

/// Runs the general decompiler command-line frontend.
///
/// # Errors
///
/// Returns an I/O error for malformed arguments, unknown
/// profile/representation, source reads, semantic rendering failures, or output
/// writes.
pub fn run() -> IoResult<()> {
    let raw = env::args_os().skip(1).collect::<Vec<_>>();
    let Some(arguments) = parse_arguments(&raw)? else {
        let mut output = stdout().lock();
        output.write_all(USAGE.as_bytes())?;
        output.write_all(b"\n")?;
        return Ok(());
    };
    let profile = target_profile(&arguments.profile_id).ok_or_else(|| {
        IoError::other(format!("unknown profile: {}", arguments.profile_id))
    })?;
    let source = read(&arguments.input)?;
    let rendered = match arguments.representation {
        OutputRepresentation::CSource => decompiler::render_c(profile, &source),
    }
    .map_err(|error| IoError::other(error.to_string()))?;
    if let Some(path) = arguments.output {
        write(path, rendered.as_bytes())?;
    } else {
        stdout().lock().write_all(rendered.as_bytes())?;
    }
    Ok(())
}

fn parse_arguments(raw: &[OsString]) -> IoResult<Option<Arguments>> {
    if raw
        .iter()
        .any(|argument| argument == "--help" || argument == "-h")
    {
        return Ok(None);
    }
    let mut input = None;
    let mut output = None;
    let mut profile_id = None;
    let mut representation = None;
    let mut index = 0usize;
    while index < raw.len() {
        let argument = raw.get(index).ok_or_else(|| IoError::other(USAGE))?;
        match argument.to_str() {
            Some("--profile") => {
                let value = next_utf8(raw, &mut index, "--profile")?;
                profile_id = Some(String::from(value));
            },
            Some("--representation") => {
                let value = next_utf8(raw, &mut index, "--representation")?;
                representation = Some(parse_representation(value)?);
            },
            Some("--output" | "-o") => {
                index = index.saturating_add(1);
                let value = raw.get(index).ok_or_else(|| {
                    IoError::other("--output requires a path")
                })?;
                output = Some(PathBuf::from(value));
            },
            Some(value) if value.starts_with('-') => {
                return Err(IoError::other(format!(
                    "unknown argument: {value}"
                )));
            },
            _ => {
                if input.is_some() {
                    return Err(IoError::other(
                        "multiple input paths supplied",
                    ));
                }
                input = Some(PathBuf::from(argument));
            },
        }
        index = index.saturating_add(1);
    }
    Ok(Some(Arguments {
        input: input.ok_or_else(|| IoError::other("missing input path"))?,
        output,
        profile_id: profile_id
            .ok_or_else(|| IoError::other("missing --profile"))?,
        representation: representation
            .ok_or_else(|| IoError::other("missing --representation"))?,
    }))
}

fn next_utf8<'input>(
    raw: &'input [OsString],
    index: &mut usize,
    option: &str,
) -> IoResult<&'input str> {
    *index = index.saturating_add(1);
    raw.get(*index)
        .and_then(|item| item.to_str())
        .ok_or_else(|| IoError::other(format!("{option} requires UTF-8 value")))
}

fn parse_representation(value: &str) -> IoResult<OutputRepresentation> {
    match value {
        "c" => Ok(OutputRepresentation::CSource),
        _ => Err(IoError::other(format!(
            "unknown output representation: {value}"
        ))),
    }
}
