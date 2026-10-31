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
#[cfg(any(target_os = "linux", target_os = "android"))]
use std::fs::OpenOptions;
use std::fs::{self, File, write};
use std::io::{
    Error as IoError, Read as _, Result as IoResult, Write as _, stdout,
};
use std::path::{Path, PathBuf};

use malbolge::target_profile;

use super::decompiler;

const MAX_DECOMPILER_SOURCE_BYTES: u64 = 1_048_576;

const USAGE: &str = concat!(
    "usage: malbolge_decompile --profile ID --representation analysis|c ",
    "INPUT ",
    "[--output FILE]"
);

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum OutputRepresentation {
    Analysis,
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
    let source = read_decompiler_source(&arguments.input)?;
    let rendered = match arguments.representation {
        OutputRepresentation::Analysis => {
            decompiler::render_analysis(profile, &source)
        },
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

// Open an attacker-selected FIFO without waiting for an external writer.
// On platforms without this flag, preflight regular-file metadata first.
#[cfg(any(target_os = "linux", target_os = "android"))]
fn open_decompiler_source(path: &Path) -> IoResult<File> {
    use std::os::unix::fs::OpenOptionsExt as _;

    const LINUX_O_NONBLOCK: i32 = 1 << 11;
    OpenOptions::new()
        .read(true)
        .custom_flags(LINUX_O_NONBLOCK)
        .open(path)
}

#[cfg(not(any(target_os = "linux", target_os = "android")))]
fn open_decompiler_source(path: &Path) -> IoResult<File> {
    if !std::fs::metadata(path)?.is_file() {
        return Err(IoError::other("decompiler source must be a regular file"));
    }
    File::open(path)
}

// A bounded read alone does not ensure a stable source. A different inode
// with the same length or an in-place rewrite can otherwise be decompiled.
#[cfg(unix)]
fn source_metadata_matches(
    before: &fs::Metadata,
    after: &fs::Metadata,
) -> bool {
    use std::os::unix::fs::MetadataExt as _;

    before.is_file()
        && after.is_file()
        && before.dev() == after.dev()
        && before.ino() == after.ino()
        && before.len() == after.len()
        && before.mtime() == after.mtime()
        && before.mtime_nsec() == after.mtime_nsec()
        && before.ctime() == after.ctime()
        && before.ctime_nsec() == after.ctime_nsec()
}

#[cfg(windows)]
fn source_metadata_matches(
    before: &fs::Metadata,
    after: &fs::Metadata,
) -> bool {
    use std::os::windows::fs::MetadataExt as _;

    before.is_file()
        && after.is_file()
        && before.len() == after.len()
        && before.volume_serial_number().is_some()
        && before.volume_serial_number() == after.volume_serial_number()
        && before.file_index().is_some()
        && before.file_index() == after.file_index()
        && before.last_write_time() == after.last_write_time()
        && before.change_time() == after.change_time()
}

#[cfg(not(any(unix, windows)))]
fn source_metadata_matches(
    before: &fs::Metadata,
    after: &fs::Metadata,
) -> bool {
    before.is_file()
        && after.is_file()
        && before.len() == after.len()
        && before.modified().ok().is_some()
        && before.modified().ok() == after.modified().ok()
}

// Metadata does not distinguish two hardlinks to the same inode. Linux
// exposes the opened dentry through /proc, allowing an exact path recheck.
#[cfg(target_os = "linux")]
fn verify_opened_source_path(
    file: &File,
    path: &Path,
    expected: &Path,
) -> IoResult<()> {
    use std::os::fd::AsRawFd as _;

    let descriptor = format!("/proc/self/fd/{}", file.as_raw_fd());
    let opened = fs::read_link(descriptor)?;
    let current = fs::canonicalize(path)?;
    if opened != expected || current != expected {
        return Err(IoError::other("decompiler source changed during read"));
    }
    Ok(())
}

fn read_decompiler_source(path: &Path) -> IoResult<Vec<u8>> {
    read_decompiler_source_with_reader(path, |file, bytes| {
        file.take(MAX_DECOMPILER_SOURCE_BYTES + 1)
            .read_to_end(bytes)
    })
}

pub(crate) fn read_decompiler_source_with_reader(
    path: &Path,
    read: impl FnOnce(&mut File, &mut Vec<u8>) -> IoResult<usize>,
) -> IoResult<Vec<u8>> {
    #[cfg(target_os = "linux")]
    let expected_open_path = fs::canonicalize(path)?;
    let mut file = open_decompiler_source(path)?;
    #[cfg(target_os = "linux")]
    verify_opened_source_path(&file, path, &expected_open_path)?;
    let metadata = file.metadata()?;
    if !metadata.is_file() || metadata.len() > MAX_DECOMPILER_SOURCE_BYTES {
        return Err(IoError::other(
            "decompiler source must be a regular file at most 1 MiB",
        ));
    }
    let named = fs::metadata(path)?;
    if !source_metadata_matches(&metadata, &named) {
        return Err(IoError::other("decompiler source changed during read"));
    }
    // Limit the production reader to one overflow-detection byte; never
    // publish a source whose identity, contents, or size changed during read.
    let mut bytes = Vec::new();
    let _read = read(&mut file, &mut bytes)?;
    if u64::try_from(bytes.len()).map_err(IoError::other)?
        > MAX_DECOMPILER_SOURCE_BYTES
    {
        return Err(IoError::other("decompiler source exceeds 1 MiB"));
    }
    if u64::try_from(bytes.len()).map_err(IoError::other)? != metadata.len()
        || !source_metadata_matches(&metadata, &file.metadata()?)
        || !source_metadata_matches(&metadata, &fs::metadata(path)?)
    {
        return Err(IoError::other("decompiler source changed during read"));
    }
    #[cfg(target_os = "linux")]
    verify_opened_source_path(&file, path, &expected_open_path)?;
    Ok(bytes)
}

fn parse_arguments(raw: &[OsString]) -> IoResult<Option<Arguments>> {
    if requests_help(raw)? {
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
                set_once(&mut profile_id, String::from(value), "--profile")?;
            },
            Some("--representation") => {
                let value = next_utf8(raw, &mut index, "--representation")?;
                set_once(
                    &mut representation,
                    parse_representation(value)?,
                    "--representation",
                )?;
            },
            Some("--output" | "-o") => {
                index = index.saturating_add(1);
                let value = raw.get(index).ok_or_else(|| {
                    IoError::other("--output requires a path")
                })?;
                set_once(&mut output, PathBuf::from(value), "--output")?;
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

fn requests_help(raw: &[OsString]) -> IoResult<bool> {
    let requested = raw
        .iter()
        .any(|argument| argument == "--help" || argument == "-h");
    if requested && raw.len() != 1 {
        return Err(IoError::other(
            "--help cannot be combined with other arguments",
        ));
    }
    Ok(requested)
}

fn set_once<T>(target: &mut Option<T>, value: T, option: &str) -> IoResult<()> {
    if target.is_some() {
        return Err(IoError::other(format!("duplicate {option}")));
    }
    *target = Some(value);
    Ok(())
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
        "analysis" => Ok(OutputRepresentation::Analysis),
        "c" => Ok(OutputRepresentation::CSource),
        _ => Err(IoError::other(format!(
            "unknown output representation: {value}"
        ))),
    }
}
