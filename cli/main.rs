// File:
//   - main.rs
// Path:
//   - cli/main.rs
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
//   - Top-level file execution dispatch for `.malbolge` and debug-only `.c`.
// - Must-Not:
//   - Treat native C execution as Malbolge conformance or performance evidence.
//   - Compile `.malbolge` into a persistent native executable.
// - Allows:
//   - Inputs: one source path and arguments forwarded only to native C debug runs.
//   - Outputs: guest stdout or the directly executed C program's stdout/stderr.
//   - Side effects: temporary native C artifacts removed after execution.
// - Split-When:
//   - Split when interactive Malbolge host capabilities require their own runner.
// - Merge-When:
//   - Merge when another top-level executable owns identical dispatch semantics.
// - Summary:
//   - Portable `malbolge <path>` command-line frontend.
// - Description:
//   - Executes Malbolge through the normative VM and C through a host compiler.
// - Usage:
//   - `malbolge program.malbolge` or `malbolge program.c`.
// - Defaults:
//   - Raw Malbolge uses classic semantics; capsules select their declared profile.
//
// Related documents:
// - cli/README.md
// - docs/technical/runtime/execution/cross-platform-native-capability-runners.md
//
// Large file:
//   - false

//! Portable top-level source runner.

use malbolge::{Machine, ProfileMachine, RunOutcome, parse_capsule};
use std::env;
use std::ffi::{OsStr, OsString};
use std::fs;
use std::io::{self, Write as _};
use std::path::{Path, PathBuf};
use std::process::{Command, ExitCode, ExitStatus, Stdio, id};

const C_EXTENSION: &str = "c";
const C_RUN_PREFIX: &str = "malbolge-c-run";
const MALBOLGE_EXTENSION: &str = "malbolge";
const RUN_CHUNK_STEPS: usize = 1_000_000;
const ZIG_VERSION: &str = "0.16.0";

#[derive(Debug)]
enum CDriver {
    Cc(OsString),
    Zig(OsString),
}

fn cleanup_native_artifacts(executable: &Path) -> Result<(), String> {
    remove_if_present(executable)?;
    remove_if_present(&executable.with_extension("pdb"))?;
    Ok(())
}

fn command_available(executable: &OsStr, version_argument: &str) -> bool {
    Command::new(executable)
        .arg(version_argument)
        .stdin(Stdio::null())
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .status()
        .is_ok_and(|status| status.success())
}

fn compile_c(
    source: &Path,
    executable: &Path,
    driver: &CDriver,
) -> Result<(), String> {
    let mut command = match driver {
        CDriver::Cc(path) => Command::new(path),
        CDriver::Zig(path) => {
            let mut zig = Command::new(path);
            let _configured = zig.arg("cc");
            zig
        },
    };
    let _configured = command
        .arg("-std=c23")
        .arg("-O0")
        .arg("-g")
        .arg(source)
        .arg("-o")
        .arg(executable);
    add_windows_debug_libraries(&mut command);
    let compile_status = command
        .stdin(Stdio::inherit())
        .stdout(Stdio::inherit())
        .stderr(Stdio::inherit())
        .status()
        .map_err(|error| format!("failed to start C compiler: {error}"))?;
    if compile_status.success() {
        Ok(())
    } else {
        Err(format!("C compilation failed with status {compile_status}"))
    }
}

fn c_driver() -> Result<CDriver, String> {
    if let Some(configured) = env::var_os("MALBOLGE_CC") {
        return Ok(driver_from_executable(configured));
    }
    if let Some(repository_zig) = repository_zig() {
        return Ok(CDriver::Zig(repository_zig.into_os_string()));
    }
    let zig = OsString::from("zig");
    if command_available(&zig, "version") {
        return Ok(CDriver::Zig(zig));
    }
    for candidate in ["clang", "cc", "gcc"] {
        let executable = OsString::from(candidate);
        if command_available(&executable, "--version") {
            return Ok(CDriver::Cc(executable));
        }
    }
    Err(String::from(
        "no C compiler found; install Zig or set MALBOLGE_CC",
    ))
}

fn dispatch(path: &Path, arguments: &[OsString]) -> Result<ExitCode, String> {
    let extension = path
        .extension()
        .and_then(OsStr::to_str)
        .map(str::to_ascii_lowercase)
        .ok_or_else(|| {
            String::from("source path has no supported extension")
        })?;
    match extension.as_str() {
        C_EXTENSION => run_c(path, arguments),
        MALBOLGE_EXTENSION => {
            if arguments.is_empty() {
                run_malbolge(path)
            } else {
                Err(String::from(
                    "arguments after a .malbolge path are not implemented yet",
                ))
            }
        },
        _ => Err(format!(
            "unsupported source extension '.{extension}'; expected .c or .malbolge",
        )),
    }
}

fn driver_from_executable(executable: OsString) -> CDriver {
    let looks_like_zig = Path::new(&executable)
        .file_stem()
        .and_then(OsStr::to_str)
        .is_some_and(|stem| stem.eq_ignore_ascii_case("zig"));
    if looks_like_zig {
        CDriver::Zig(executable)
    } else {
        CDriver::Cc(executable)
    }
}

fn exit_code(status: ExitStatus) -> ExitCode {
    match status.code().and_then(|code| u8::try_from(code).ok()) {
        Some(code) => ExitCode::from(code),
        None if status.success() => ExitCode::SUCCESS,
        None => ExitCode::FAILURE,
    }
}

fn flush_new_output(output: &[u8], emitted: &mut usize) -> Result<(), String> {
    let new_output = output.get(*emitted..).ok_or_else(|| {
        String::from("VM output cursor exceeded output length")
    })?;
    let mut stdout = io::stdout().lock();
    stdout
        .write_all(new_output)
        .and_then(|()| stdout.flush())
        .map_err(|error| format!("failed to write guest output: {error}"))?;
    *emitted = output.len();
    Ok(())
}

fn main() -> ExitCode {
    match run() {
        Ok(code) => code,
        Err(message) => {
            write_diagnostic(&message);
            ExitCode::FAILURE
        },
    }
}

fn native_executable_path() -> PathBuf {
    let file_name = if cfg!(windows) {
        format!("{C_RUN_PREFIX}-{}.exe", id())
    } else {
        format!("{C_RUN_PREFIX}-{}", id())
    };
    env::temp_dir().join(file_name)
}

fn remove_if_present(path: &Path) -> Result<(), String> {
    match fs::remove_file(path) {
        Ok(()) => Ok(()),
        Err(error) if error.kind() == io::ErrorKind::NotFound => Ok(()),
        Err(error) => Err(format!(
            "failed to remove temporary artifact '{}': {error}",
            path.display(),
        )),
    }
}

fn repository_root() -> Option<PathBuf> {
    if let Some(configured) = env::var_os("MALBOLGE_ROOT") {
        return Some(PathBuf::from(configured));
    }
    let executable = env::current_exe().ok()?;
    let binary_directory = executable.parent()?;
    let cli_directory = binary_directory.parent()?;
    cli_directory.parent().map(Path::to_path_buf)
}

fn repository_zig() -> Option<PathBuf> {
    let executable_name = if cfg!(windows) {
        "zig.exe"
    } else {
        "zig"
    };
    let candidate = repository_root()?
        .join(".dependencies")
        .join("zig")
        .join(ZIG_VERSION)
        .join(executable_name);
    candidate.is_file().then_some(candidate)
}

fn run() -> Result<ExitCode, String> {
    let mut arguments = env::args_os().skip(1);
    let Some(first_argument) = arguments.next() else {
        write_usage()?;
        return Ok(ExitCode::FAILURE);
    };
    if first_argument == OsStr::new("--help")
        || first_argument == OsStr::new("-h")
    {
        write_usage()?;
        return Ok(ExitCode::SUCCESS);
    }
    let canonical = PathBuf::from(first_argument)
        .canonicalize()
        .map_err(|error| format!("cannot open source path: {error}"))?;
    let forwarded = arguments.collect::<Vec<_>>();
    dispatch(&canonical, &forwarded)
}

fn run_c(source: &Path, arguments: &[OsString]) -> Result<ExitCode, String> {
    let driver = c_driver()?;
    let executable = native_executable_path();
    cleanup_native_artifacts(&executable)?;
    if let Err(error) = compile_c(source, &executable, &driver) {
        cleanup_native_artifacts(&executable)?;
        return Err(error);
    }
    let run_status = Command::new(&executable)
        .args(arguments)
        .stdin(Stdio::inherit())
        .stdout(Stdio::inherit())
        .stderr(Stdio::inherit())
        .status()
        .map_err(|error| {
            format!("failed to execute compiled C program: {error}")
        });
    let cleanup_result = cleanup_native_artifacts(&executable);
    let status = run_status?;
    cleanup_result?;
    Ok(exit_code(status))
}

fn run_classic(source: &[u8]) -> Result<(), String> {
    let mut machine = Machine::from_source(source, Vec::new())
        .map_err(|error| format!("classic Malbolge load failed: {error}"))?;
    let mut emitted = 0usize;
    let mut outcome = machine.run(RUN_CHUNK_STEPS).map_err(|error| {
        format!("classic Malbolge execution failed: {error}")
    })?;
    flush_new_output(machine.output(), &mut emitted)?;
    while matches!(outcome, RunOutcome::BudgetExhausted { .. }) {
        outcome = machine.run(RUN_CHUNK_STEPS).map_err(|error| {
            format!("classic Malbolge execution failed: {error}")
        })?;
        flush_new_output(machine.output(), &mut emitted)?;
    }
    Ok(())
}

fn run_malbolge(source_path: &Path) -> Result<ExitCode, String> {
    let source = fs::read(source_path)
        .map_err(|error| format!("failed to read Malbolge source: {error}"))?;
    match parse_capsule(&source)
        .map_err(|error| format!("Malbolge capsule parsing failed: {error}"))?
    {
        Some(capsule) => run_profile(capsule.profile(), capsule.payload())?,
        None => run_classic(&source)?,
    }
    Ok(ExitCode::SUCCESS)
}

fn run_profile(
    profile: &'static malbolge::ProfileDescriptor,
    source: &[u8],
) -> Result<(), String> {
    let mut machine = ProfileMachine::from_source(profile, source, Vec::new())
        .map_err(|error| format!("profile Malbolge load failed: {error}"))?;
    let mut emitted = 0usize;
    let mut outcome = machine.run(RUN_CHUNK_STEPS).map_err(|error| {
        format!("profile Malbolge execution failed: {error}")
    })?;
    flush_new_output(machine.output(), &mut emitted)?;
    while matches!(outcome, RunOutcome::BudgetExhausted { .. }) {
        outcome = machine.run(RUN_CHUNK_STEPS).map_err(|error| {
            format!("profile Malbolge execution failed: {error}")
        })?;
        flush_new_output(machine.output(), &mut emitted)?;
    }
    Ok(())
}

fn write_diagnostic(message: &str) {
    let mut stderr = io::stderr().lock();
    if stderr.write_all(b"malbolge: ").is_ok()
        && stderr.write_all(message.as_bytes()).is_ok()
    {
        let _ignored = stderr.write_all(b"\n");
    }
}

fn write_usage() -> Result<(), String> {
    let usage = concat!(
        "Usage: malbolge <program.c|program.malbolge> [program args...]\n",
        "\n",
        "  .malbolge  Execute the Malbolge program in the normative VM.\n",
        "  .c         Debug-run C directly on the host via a temporary binary.\n",
    );
    io::stdout()
        .lock()
        .write_all(usage.as_bytes())
        .map_err(|error| format!("failed to write usage: {error}"))
}

#[cfg(windows)]
fn add_windows_debug_libraries(command: &mut Command) {
    let _configured = command.args([
        "-luser32",
        "-lgdi32",
        "-lwinmm",
        "-lws2_32",
        "-lole32",
        "-luuid",
        "-ldsound",
        "-ldxguid",
        "-lshell32",
    ]);
}

#[cfg(not(windows))]
fn add_windows_debug_libraries(_command: &mut Command) {}
