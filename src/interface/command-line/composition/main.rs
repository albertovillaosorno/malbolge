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
//   - Top-level file execution dispatch for `.malbolge` and debug-only `.c`.
// - Must-Not:
//   - Treat native C execution as Malbolge conformance or performance evidence.
//   - Compile `.malbolge` into a persistent native executable.
// - Allows:
//   - Inputs: one source path and arguments forwarded only to native C debug
//     runs.
//   - Outputs: guest stdout or the directly executed C program's stdout/stderr.
//   - Side effects: temporary native C artifacts removed after execution.
// - Split-When:
//   - Split when interactive Malbolge host capabilities require their own
//     runner.
// - Merge-When:
//   - Merge when another top-level executable owns identical dispatch
//     semantics.
// - Summary:
//   - Portable `malbolge <path>` command-line frontend.
// - Description:
//   - Executes Malbolge through the normative VM and C through a host compiler.
// - Usage:
//   - `malbolge program.malbolge` or `malbolge program.c`.
// - Defaults:
//   - Raw Malbolge uses classic semantics; capsules select their declared
//     profile.
//

//! Portable top-level source runner.

#[path = "../application/c_source.rs"]
pub mod c_source;

use std::env;
use std::ffi::{OsStr, OsString};
use std::fs::{self, DirBuilder};
use std::io::{self, Write as _};
use std::path::{Path, PathBuf};
use std::process::{Command, ExitCode, ExitStatus, Stdio, id};

use c_source::inspect_c_source;
use malbolge::{
    ExecutionMachine, ExecutionMode, ProfileBatchRequest, ProfileMachine,
    ProfileResidentProcessTransport, ProfileResidentTransportBackend,
    RunOutcome, current_profile, execute_profile_batch_with_backend,
    parse_capsule,
};

const C_EXTENSION: &str = "c";
const DOOM_IWAD_NAMES: [&str; 8] = [
    "freedoom1.wad",
    "freedoom2.wad",
    "doom2.wad",
    "doomu.wad",
    "doom.wad",
    "doom1.wad",
    "plutonia.wad",
    "tnt.wad",
];
const C_RUN_PREFIX: &str = "malbolge-c-run";
const LLVM_VERSION: &str = "22.1.8";
const MALBOLGE_EXTENSION: &str = "malbolge";
const PROFILE_WORKER_ARG_COUNT_ENV: &str =
    "MALBOLGE_PROFILE_RESIDENT_WORKER_ARG_COUNT";
const PROFILE_WORKER_CWD_ENV: &str = "MALBOLGE_PROFILE_RESIDENT_WORKER_CWD";
const PROFILE_WORKER_ENV: &str = "MALBOLGE_PROFILE_RESIDENT_WORKER";
const PROFILE_WORKER_MAX_ARGS: usize = 32;
const RUN_CHUNK_STEPS: usize = 1_000_000;
const ZIG_VERSION: &str = "0.16.0";

#[derive(Debug)]
enum CDriver {
    Cc(OsString),
    Zig(OsString),
}

type ConfiguredProfileBackend =
    ProfileResidentTransportBackend<ProfileResidentProcessTransport>;

#[derive(Debug)]
struct CRunPlan {
    arguments: Vec<OsString>,
    compiler_arguments: Vec<OsString>,
    environment: Vec<(OsString, OsString)>,
    extra_sources: Vec<PathBuf>,
    needs_windows_libraries: bool,
    working_directory: Option<PathBuf>,
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
    plan: &CRunPlan,
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
        .args(&plan.compiler_arguments)
        .arg(source)
        .args(&plan.extra_sources)
        .arg("-o")
        .arg(executable);
    if plan.needs_windows_libraries {
        add_windows_debug_libraries(&mut command);
    }
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

fn build_c_run_plan(
    source: &Path,
    arguments: &[OsString],
) -> Result<CRunPlan, String> {
    let bytes = fs::read(source)
        .map_err(|error| format!("failed to inspect C source: {error}"))?;
    let adapters = inspect_c_source(&bytes);
    let mut plan = if adapters.doom_host() {
        build_doom_run_plan(source, arguments)?
    } else {
        plain_c_run_plan(arguments)
    };
    if adapters.guest_output() {
        add_guest_output_adapter(&mut plan)?;
    }
    Ok(plan)
}

fn plain_c_run_plan(arguments: &[OsString]) -> CRunPlan {
    CRunPlan {
        arguments: arguments.to_vec(),
        compiler_arguments: Vec::new(),
        environment: Vec::new(),
        extra_sources: Vec::new(),
        needs_windows_libraries: false,
        working_directory: None,
    }
}

fn add_guest_output_adapter(plan: &mut CRunPlan) -> Result<(), String> {
    let root = repository_root().ok_or_else(|| {
        String::from("cannot locate repository root for guest output adapter")
    })?;
    let adapter = root.join(
        "src/interface/command-line/adapter-outbound/adapters/guest/output.c",
    );
    if !adapter.is_file() {
        return Err(format!(
            "guest output adapter is missing: {}",
            adapter.display(),
        ));
    }
    plan.extra_sources.push(adapter);
    Ok(())
}

fn build_doom_run_plan(
    source: &Path,
    arguments: &[OsString],
) -> Result<CRunPlan, String> {
    if !cfg!(windows) {
        return Err(String::from(
            "native doom.c debugging currently has only a Windows adapter",
        ));
    }
    let root = repository_root().ok_or_else(|| {
        String::from("cannot locate repository root for DOOM debug adapter")
    })?;
    let adapter = root.join(
        "src/interface/command-line/adapter-outbound/adapters/doom/windows.c",
    );
    if !adapter.is_file() {
        return Err(format!(
            "DOOM debug adapter is missing: {}",
            adapter.display(),
        ));
    }
    let working_directory = source
        .parent()
        .ok_or_else(|| String::from("doom.c has no parent directory"))?
        .to_path_buf();
    DirBuilder::new()
        .recursive(true)
        .create(&working_directory)
        .map_err(|error| {
            format!("cannot create DOOM run directory: {error}")
        })?;
    let resolved_arguments = doom_arguments(arguments)?;
    let mut environment = Vec::new();
    if let Some(path) = discover_doom_iwad(&root, &working_directory) {
        environment.push((
            OsString::from("MALBOLGE_DOOM_FALLBACK_IWAD"),
            path.into_os_string(),
        ));
    }
    let source_name = source
        .file_name()
        .ok_or_else(|| String::from("doom.c has no file name"))?;
    environment.push((
        OsString::from("MALBOLGE_DOOM_EXECUTION_SOURCE"),
        source_name.to_os_string(),
    ));
    Ok(CRunPlan {
        arguments: resolved_arguments,
        compiler_arguments: vec![OsString::from("-Dmain=DoomGuestMain")],
        environment,
        extra_sources: vec![adapter],
        needs_windows_libraries: true,
        working_directory: Some(working_directory),
    })
}

fn discover_doom_iwad(root: &Path, source_directory: &Path) -> Option<PathBuf> {
    if let Some(configured) = env::var_os("MALBOLGE_DOOM_IWAD") {
        let configured_path = PathBuf::from(configured);
        if let Ok(canonical) = configured_path.canonicalize()
            && canonical.is_file()
        {
            return Some(canonical);
        }
    }
    let directories = [
        source_directory.to_path_buf(),
        source_directory.join("data/wad"),
        root.join("doom/data/wad"),
        root.join("src/research/algorithms/domain/algorithms/doom")
            .join("quality/out/doom_fixed/data/wad"),
    ];
    for directory in directories {
        for name in DOOM_IWAD_NAMES {
            let candidate = directory.join(name);
            if let Ok(canonical) = candidate.canonicalize()
                && canonical.is_file()
            {
                return Some(canonical);
            }
        }
    }
    None
}

fn doom_arguments(arguments: &[OsString]) -> Result<Vec<OsString>, String> {
    let mut resolved = arguments.to_vec();
    let iwad_index = resolved
        .iter()
        .position(|argument| argument == OsStr::new("-iwad"));
    if let Some(index) = iwad_index {
        let path_index = index.saturating_add(1);
        let path = resolved
            .get(path_index)
            .ok_or_else(|| String::from("-iwad requires a path"))?;
        let canonical = PathBuf::from(path)
            .canonicalize()
            .map_err(|error| format!("cannot open IWAD: {error}"))?;
        let path_slot = resolved
            .get_mut(path_index)
            .ok_or_else(|| String::from("-iwad requires a path"))?;
        *path_slot = canonical.into_os_string();
    }
    Ok(resolved)
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
    if let Some(repository_clang) = repository_clang() {
        return Ok(CDriver::Cc(repository_clang.into_os_string()));
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
            concat!(
                "unsupported source extension '.{}'; ",
                "expected .c or .malbolge",
            ),
            extension,
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
    env::current_dir()
        .ok()
        .as_deref()
        .and_then(find_repository_root)
        .or_else(|| {
            env::current_exe()
                .ok()
                .as_deref()
                .and_then(find_repository_root)
        })
}

fn find_repository_root(start: &Path) -> Option<PathBuf> {
    start.ancestors().find_map(|candidate| {
        let manifest = candidate.join("Cargo.toml");
        let adapters = candidate
            .join("src/interface/command-line/adapter-outbound/adapters");
        (manifest.is_file() && adapters.is_dir())
            .then(|| candidate.to_path_buf())
    })
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

fn repository_clang() -> Option<PathBuf> {
    let candidate = repository_root()?
        .join(".dependencies")
        .join("llvm")
        .join(LLVM_VERSION)
        .join("jig-bin")
        .join("clang.bin");
    candidate.is_file().then_some(candidate)
}

fn run() -> Result<ExitCode, String> {
    let mut arguments = env::args_os().skip(1);
    let Some(first_argument) = arguments.next() else {
        return Err(String::from("expected source path; use --help for usage"));
    };
    if first_argument == OsStr::new("--help")
        || first_argument == OsStr::new("-h")
    {
        if arguments.next().is_some() {
            return Err(String::from(
                "--help cannot be combined with other arguments",
            ));
        }
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
    let plan = build_c_run_plan(source, arguments)?;
    let executable = native_executable_path();
    cleanup_native_artifacts(&executable)?;
    if let Err(error) = compile_c(source, &executable, &driver, &plan) {
        cleanup_native_artifacts(&executable)?;
        return Err(error);
    }
    let mut command = Command::new(&executable);
    let _configured = command
        .args(&plan.arguments)
        .envs(plan.environment.iter().cloned())
        .stdin(Stdio::inherit())
        .stdout(Stdio::inherit())
        .stderr(Stdio::inherit());
    if let Some(directory) = &plan.working_directory {
        let _working_directory = command.current_dir(directory);
    }
    let run_status = command.status().map_err(|error| {
        format!("failed to execute compiled C program: {error}")
    });
    let cleanup_result = cleanup_native_artifacts(&executable);
    let status = run_status?;
    cleanup_result?;
    Ok(exit_code(status))
}

fn run_classic(source: &[u8]) -> Result<(), String> {
    let mut machine = ExecutionMachine::from_source(
        source,
        Vec::new(),
        ExecutionMode::Interpreter,
    )
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

fn configured_profile_backend(
    profile: &'static malbolge::ProfileDescriptor,
) -> Result<Option<ConfiguredProfileBackend>, String> {
    if profile != current_profile() {
        return Ok(None);
    }
    let Some(program) = env::var_os(PROFILE_WORKER_ENV) else {
        return Ok(None);
    };
    if program.is_empty() {
        return Err(format!("{PROFILE_WORKER_ENV} cannot be empty"));
    }
    let argument_count = configured_profile_worker_argument_count()?;
    let mut transport =
        ProfileResidentProcessTransport::new(PathBuf::from(program));
    for index in 0..argument_count {
        let name = profile_worker_argument_name(index);
        let argument = env::var_os(&name).ok_or_else(|| {
            format!("{name} is required by {PROFILE_WORKER_ARG_COUNT_ENV}")
        })?;
        transport = transport.argument(argument);
    }
    if let Some(directory) = env::var_os(PROFILE_WORKER_CWD_ENV) {
        if directory.is_empty() {
            return Err(format!("{PROFILE_WORKER_CWD_ENV} cannot be empty"));
        }
        transport = transport.working_directory(PathBuf::from(directory));
    }
    Ok(Some(ProfileResidentTransportBackend::new(transport)))
}

fn configured_profile_worker_argument_count() -> Result<usize, String> {
    let Some(value) = env::var_os(PROFILE_WORKER_ARG_COUNT_ENV) else {
        return Ok(0);
    };
    let text = value.to_str().ok_or_else(|| {
        format!("{PROFILE_WORKER_ARG_COUNT_ENV} must be ASCII decimal")
    })?;
    let count = text.parse::<usize>().map_err(|error| {
        format!("invalid {PROFILE_WORKER_ARG_COUNT_ENV}: {error}")
    })?;
    if count > PROFILE_WORKER_MAX_ARGS {
        return Err(format!(
            "{PROFILE_WORKER_ARG_COUNT_ENV} exceeds {PROFILE_WORKER_MAX_ARGS}"
        ));
    }
    Ok(count)
}

fn profile_worker_argument_name(index: usize) -> String {
    format!("MALBOLGE_PROFILE_RESIDENT_WORKER_ARG_{index}")
}

fn run_profile(
    profile: &'static malbolge::ProfileDescriptor,
    source: &[u8],
) -> Result<(), String> {
    let machine = ProfileMachine::from_source(profile, source, Vec::new())
        .map_err(|error| format!("profile Malbolge load failed: {error}"))?;
    let mut backend = configured_profile_backend(profile)?;
    match backend.as_mut() {
        Some(selected) => run_profile_with_backend(machine, selected),
        None => run_profile_direct(machine),
    }
}

fn run_profile_direct(mut machine: ProfileMachine) -> Result<(), String> {
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

fn run_profile_with_backend(
    mut machine: ProfileMachine,
    backend: &mut dyn malbolge::ProfileBatchExecutionBackend,
) -> Result<(), String> {
    let mut emitted = 0usize;
    loop {
        let request =
            ProfileBatchRequest::from_machine(machine, RUN_CHUNK_STEPS);
        let mut results =
            execute_profile_batch_with_backend(vec![request], backend);
        let result = results.pop().ok_or_else(|| {
            String::from("profile backend returned no batch result")
        })?;
        let outcome = result.outcome().ok_or_else(|| {
            result.error().map_or_else(
                || String::from("profile backend result has no outcome"),
                |error| format!("profile Malbolge execution failed: {error}"),
            )
        })?;
        machine = result.into_machine().map_err(|error| {
            format!("profile Malbolge execution failed: {error}")
        })?;
        flush_new_output(machine.output(), &mut emitted)?;
        if !matches!(outcome, RunOutcome::BudgetExhausted { .. }) {
            return Ok(());
        }
    }
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
        "Usage: malbolge <program.malbolge>\n",
        "       malbolge <program.c> [program args...]\n",
        "\n",
        "  .malbolge  Execute the Malbolge program in the normative VM.\n",
        "  .c         Debug-run C directly on the host via a ",
        "temporary binary.\n",
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
const fn add_windows_debug_libraries(_command: &mut Command) {}
