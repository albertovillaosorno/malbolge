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
//   - External Clang invocation for profile-preflighted bootstrap artifacts.
// - Must-Not:
//   - Compile raw unpreflighted IR, admit machine code, or discover toolchains.
// - Allows:
//   - Inputs: compiler path, portable region IR, runtime, and native target.
//   - Outputs: opaque untrusted compiler object bytes bound to source identity.
//   - Side effects: one explicit child process and its standard I/O pipes.
// - Split-When:
//   - Toolchain discovery/version admission or persistent compiler workers
//     arise.
// - Merge-When:
//   - Another native compiler adapter owns this exact bootstrap invocation.
// - Summary:
//   - Compile only profile-preflighted C23 bootstrap source through Clang.
// - Description:
//   - Preflights profile identity/capacity/runtime before any process launch.
// - Usage:
//   - AOT/JIT orchestration supplies an explicit compiler path and target.
// - Defaults:
//   - Compiler output remains untrusted and requires independent admission.
//

//! External Clang process boundary for preflighted native bootstrap artifacts.

use std::fmt::{Display, Formatter, Result as FormatResult};
use std::io::{Read, Result as IoResult, Write as _};
use std::path::Path;
use std::process::{
    Child, ChildStderr, ChildStdin, ChildStdout, Command, ExitStatus, Output,
    Stdio,
};
use std::sync::atomic::{AtomicBool, Ordering};
use std::thread;
use std::time::{Duration, Instant};

use malbolge::{RegionEffectProgram, RuntimeCapability};

use super::{
    BootstrapProfilePreflightError, NativeArtifactError, NativeTargetIdentity,
    UntrustedNativeObjectArtifact, UntrustedNativeSourceArtifact,
    lower_preflighted_clang_c23,
};
use crate::execution_cache::HostIsa;

// Bootstrap Clang emits small relocatable objects; these are explicit host
// safety budgets, not guest-profile capacity or a semantic size limit.
const MAX_BOOTSTRAP_OBJECT_BYTES: usize = 16 * 1024 * 1024;
const MAX_BOOTSTRAP_DIAGNOSTIC_BYTES: usize = 256 * 1024;
const MAX_BOOTSTRAP_COMPILER_MILLIS: u64 = 60_000;

/// Failure while compiling one profile-preflighted bootstrap source artifact.
#[derive(Debug, Eq, PartialEq)]
pub enum BootstrapCompilerError<'requirement> {
    /// Compiler output could not become an untrusted object artifact.
    Artifact(NativeArtifactError),
    /// Compiler returned a non-success process status.
    CompilerFailure {
        /// Platform process exit code when one is available.
        code: Option<i32>,
        /// Exact compiler stderr bytes retained as untrusted diagnostics.
        stderr: Box<[u8]>,
    },
    /// Untrusted compiler exceeded the fixed wall-clock execution ceiling.
    DeadlineExceeded {
        /// Maximum allowed external compiler runtime in milliseconds.
        maximum_ms: u64,
    },
    /// Compiler process could not be launched.
    Launch(Box<str>),
    /// Compiler stdin pipe was unexpectedly unavailable.
    MissingInputPipe,
    /// Untrusted compiler stdout or stderr exceeded its explicit host budget.
    OutputLimit {
        /// Which compiler pipe exceeded the budget.
        stream: &'static str,
        /// Maximum admitted bytes in that pipe.
        maximum_bytes: usize,
    },
    /// Profile-preflighted bootstrap lowering failed before compiler launch.
    Preflight(BootstrapProfilePreflightError<'requirement>),
    /// Bootstrap source could not be written to compiler stdin.
    SourceWrite(Box<str>),
    /// Compiler process could not be joined after source submission.
    Wait(Box<str>),
}

impl Display for BootstrapCompilerError<'_> {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::Artifact(error) => Display::fmt(error, f),
            Self::CompilerFailure { code, stderr } => {
                f.write_str("native Clang failed code=")?;
                match code {
                    Some(value) => write!(f, "{value}")?,
                    None => f.write_str("unavailable")?,
                }
                write!(f, ": {}", String::from_utf8_lossy(stderr))
            },
            Self::OutputLimit { stream, maximum_bytes } => {
                write!(
                    f,
                    "native Clang {stream} exceeded {maximum_bytes} bytes"
                )
            },
            Self::DeadlineExceeded { maximum_ms } => {
                write!(f, "native Clang exceeded {maximum_ms} ms")
            },
            Self::Launch(message) => {
                write!(f, "native Clang launch failed: {message}")
            },
            Self::MissingInputPipe => {
                f.write_str("native Clang stdin pipe is unavailable")
            },
            Self::Preflight(error) => Display::fmt(error, f),
            Self::SourceWrite(message) => {
                write!(f, "native Clang source write failed: {message}")
            },
            Self::Wait(message) => {
                write!(f, "native Clang wait failed: {message}")
            },
        }
    }
}

/// Bootstrap compiler request with explicit toolchain and semantic inputs.
#[derive(Debug)]
pub struct BootstrapCompilerRequest<'requirement> {
    /// Explicit compiler executable, without ambient lookup.
    pub compiler: &'requirement Path,
    /// Preflighted portable region program.
    pub program: &'requirement RegionEffectProgram,
    /// Exact authoritative runtime capability.
    pub runtime: &'static RuntimeCapability,
    /// Exact target ISA and platform ABI.
    pub target: NativeTargetIdentity,
}

struct CompilerDeadline {
    budget: Duration,
    started: Instant,
}

struct CompilerPipes {
    diagnostics: ChildStderr,
    input: ChildStdin,
    output: ChildStdout,
}

#[derive(Default)]
struct CompilerPipeState {
    diagnostics_done: AtomicBool,
    diagnostics_exceeded: AtomicBool,
    input_done: AtomicBool,
    output_done: AtomicBool,
    output_exceeded: AtomicBool,
}

impl CompilerPipeState {
    fn all_finished(&self) -> bool {
        self.diagnostics_done.load(Ordering::Acquire)
            && self.input_done.load(Ordering::Acquire)
            && self.output_done.load(Ordering::Acquire)
    }
}

fn terminate_bootstrap_group(child: &mut Child) {
    #[cfg(target_os = "linux")]
    {
        // A fresh process group also contains ordinary forked pipe holders.
        // POSIX signalling requires a host utility under the safe-Rust policy.
        // The group may already be gone; do not leak utility errors into
        // caller stderr or confuse them with compiler diagnostics.
        let _group_signal = Command::new("/usr/bin/kill")
            .args(["-s", "KILL", "--"])
            .arg(format!("-{}", child.id()))
            .stdout(Stdio::null())
            .stderr(Stdio::null())
            .status();
    }
    let _child_signal = child.kill();
}

fn collect_bounded_pipe(
    mut pipe: impl Read,
    limit: usize,
    exceeded: &AtomicBool,
) -> IoResult<Vec<u8>> {
    let mut result = Vec::new();
    let mut chunk = [0u8; 8192];
    loop {
        let count = pipe.read(&mut chunk)?;
        if count == 0 {
            return Ok(result);
        }
        if result
            .len()
            .checked_add(count)
            .is_none_or(|len| len > limit)
        {
            exceeded.store(true, Ordering::Release);
            return Ok(result);
        }
        if let Some(next) = chunk.get(..count) {
            result.extend_from_slice(next);
        }
    }
}

fn wait_for_bounded_child(
    child: &mut Child,
    pipes: &CompilerPipeState,
    deadline: &CompilerDeadline,
) -> IoResult<Option<ExitStatus>> {
    let mut exit_status = None;
    loop {
        if pipes.output_exceeded.load(Ordering::Acquire)
            || pipes.diagnostics_exceeded.load(Ordering::Acquire)
        {
            terminate_bootstrap_group(child);
            return child.wait().map(Some);
        }
        if deadline.started.elapsed() >= deadline.budget {
            terminate_bootstrap_group(child);
            let _reaped = child.wait()?;
            return Ok(None);
        }
        if exit_status.is_none() {
            match child.try_wait() {
                Ok(status) => exit_status = status,
                Err(error) => {
                    terminate_bootstrap_group(child);
                    drop(child.wait());
                    return Err(error);
                },
            }
        }
        if exit_status.is_some_and(|status| !status.success()) {
            if !pipes.all_finished() {
                // Failed compiler output cannot become a native artifact.
                // Release inherited pipe holders without losing its exit code.
                terminate_bootstrap_group(child);
            }
            return Ok(exit_status);
        }
        if exit_status.is_some() && pipes.all_finished() {
            return Ok(exit_status);
        }
        thread::sleep(Duration::from_millis(5));
    }
}

fn read_joined_pipe(
    task: thread::ScopedJoinHandle<'_, IoResult<Vec<u8>>>,
) -> Result<Vec<u8>, BootstrapCompilerError<'static>> {
    task.join()
        .map_err(|_panic| {
            BootstrapCompilerError::Wait(
                "native compiler pipe reader panicked".into(),
            )
        })?
        .map_err(|error| BootstrapCompilerError::Wait(error.to_string().into()))
}

fn checked_compiler_status(
    result: IoResult<Option<ExitStatus>>,
    budget: Duration,
) -> Result<ExitStatus, BootstrapCompilerError<'static>> {
    result
        .map_err(|error| {
            BootstrapCompilerError::Wait(error.to_string().into())
        })?
        .ok_or_else(|| BootstrapCompilerError::DeadlineExceeded {
            maximum_ms: u64::try_from(budget.as_millis())
                .unwrap_or(MAX_BOOTSTRAP_COMPILER_MILLIS),
        })
}

fn enforce_compiler_pipe_limits(
    stdout_exceeded: &AtomicBool,
    stderr_exceeded: &AtomicBool,
) -> Result<(), BootstrapCompilerError<'static>> {
    if stdout_exceeded.load(Ordering::Acquire) {
        return Err(BootstrapCompilerError::OutputLimit {
            stream: "stdout",
            maximum_bytes: MAX_BOOTSTRAP_OBJECT_BYTES,
        });
    }
    if stderr_exceeded.load(Ordering::Acquire) {
        return Err(BootstrapCompilerError::OutputLimit {
            stream: "stderr",
            maximum_bytes: MAX_BOOTSTRAP_DIAGNOSTIC_BYTES,
        });
    }
    Ok(())
}

fn collect_compiler_output<'requirement>(
    mut child: Child,
    source: &str,
    budget: Duration,
) -> Result<Output, BootstrapCompilerError<'requirement>> {
    let pipes = CompilerPipes {
        diagnostics: child.stderr.take().ok_or_else(|| {
            BootstrapCompilerError::Wait("compiler stderr pipe absent".into())
        })?,
        input: child
            .stdin
            .take()
            .ok_or(BootstrapCompilerError::MissingInputPipe)?,
        output: child.stdout.take().ok_or_else(|| {
            BootstrapCompilerError::Wait("compiler stdout pipe absent".into())
        })?,
    };
    collect_compiler_scoped(&mut child, pipes, source, budget)
}

fn collect_compiler_scoped<'requirement>(
    child: &mut Child,
    pipes: CompilerPipes,
    source: &str,
    budget: Duration,
) -> Result<Output, BootstrapCompilerError<'requirement>> {
    let CompilerPipes {
        diagnostics,
        mut input,
        output,
    } = pipes;
    let state = CompilerPipeState::default();
    let deadline = CompilerDeadline {
        budget,
        started: Instant::now(),
    };
    thread::scope(|scope| {
        let writer = scope.spawn(|| {
            let result = input.write_all(source.as_bytes());
            drop(input);
            state.input_done.store(true, Ordering::Release);
            result
        });
        let out = scope.spawn(|| {
            let bytes = collect_bounded_pipe(
                output,
                MAX_BOOTSTRAP_OBJECT_BYTES,
                &state.output_exceeded,
            );
            state.output_done.store(true, Ordering::Release);
            bytes
        });
        let err = scope.spawn(|| {
            let bytes = collect_bounded_pipe(
                diagnostics,
                MAX_BOOTSTRAP_DIAGNOSTIC_BYTES,
                &state.diagnostics_exceeded,
            );
            state.diagnostics_done.store(true, Ordering::Release);
            bytes
        });
        let status = wait_for_bounded_child(child, &state, &deadline);
        let write_result = writer.join().map_err(|_panic| {
            BootstrapCompilerError::Wait(
                "compiler source writer panicked".into(),
            )
        })?;
        let stdout = read_joined_pipe(out)?;
        let stderr = read_joined_pipe(err)?;
        enforce_compiler_pipe_limits(
            &state.output_exceeded,
            &state.diagnostics_exceeded,
        )?;
        let exit_status = checked_compiler_status(status, budget)?;
        // An early compiler failure may close stdin before the writer ends.
        // Keep its exit code and diagnostic instead of masking it with EPIPE.
        if exit_status.success() {
            write_result.map_err(|error| {
                BootstrapCompilerError::SourceWrite(error.to_string().into())
            })?;
        }
        Ok(Output {
            status: exit_status,
            stdout,
            stderr,
        })
    })
}

fn normalize_coff_timestamp(object: &mut [u8], isa: HostIsa) {
    // TimeDateStamp is linker bookkeeping, never guest semantics. Preserve
    // truncated and target-mismatched untrusted output byte-for-byte.
    let machine: [u8; 2] = match isa {
        HostIsa::AArch64 => [0x64, 0xaa],
        HostIsa::X86_64 => [0x64, 0x86],
    };
    if object.len() >= 20
        && object.starts_with(&machine)
        && let Some(timestamp) = object.get_mut(4..8)
    {
        timestamp.fill(0);
    }
}

fn normalize_compiler_output(
    source: &UntrustedNativeSourceArtifact,
    mut object: Vec<u8>,
) -> Result<UntrustedNativeObjectArtifact, NativeArtifactError> {
    normalize_coff_timestamp(&mut object, source.key().target().host_isa());
    UntrustedNativeObjectArtifact::from_compiler_output(source, object)
}

/// Compile one portable region only after canonical profile/runtime preflight.
///
/// The source is supplied on stdin and the object is captured from stdout, so
/// this boundary creates no temporary source/object files. Compiler bytes
/// remain explicitly untrusted and still require structural and semantic
/// admission.
///
/// # Errors
///
/// Returns [`BootstrapCompilerError`] when profile preflight/lowering fails,
/// process I/O fails, Clang rejects the source, or no object bytes are
/// produced.
pub fn compile_preflighted_clang_c23<'requirement>(
    compiler: &'requirement Path,
    program: &'requirement RegionEffectProgram,
    runtime: &'static RuntimeCapability,
    target: NativeTargetIdentity,
) -> Result<UntrustedNativeObjectArtifact, BootstrapCompilerError<'requirement>>
{
    compile_preflighted_clang_c23_with_budget(
        BootstrapCompilerRequest {
            compiler,
            program,
            runtime,
            target,
        },
        Duration::from_millis(MAX_BOOTSTRAP_COMPILER_MILLIS),
    )
}

/// Compile preflighted bootstrap source using a caller-owned tighter timeout.
///
/// The budget is capped at the fixed maximum external compiler wall clock.
/// Zero budget fails before lowering or spawning any compiler process.
///
/// # Errors
///
/// Returns [`BootstrapCompilerError`] for deadline, preflight, compiler or
/// output-admission failures; an expired compiler is terminated and reaped.
pub fn compile_preflighted_clang_c23_with_budget(
    request: BootstrapCompilerRequest<'_>,
    requested_budget: Duration,
) -> Result<UntrustedNativeObjectArtifact, BootstrapCompilerError<'_>> {
    let BootstrapCompilerRequest {
        compiler,
        program,
        runtime,
        target,
    } = request;
    let budget = requested_budget
        .min(Duration::from_millis(MAX_BOOTSTRAP_COMPILER_MILLIS));
    if budget.is_zero() {
        return Err(BootstrapCompilerError::DeadlineExceeded { maximum_ms: 0 });
    }
    let source = lower_preflighted_clang_c23(program, runtime, target)
        .map_err(BootstrapCompilerError::Preflight)?;
    // Ambient host include/driver overrides cannot change pinned C23
    // bootstrap sources or the headers used to compile them.
    let mut command = Command::new(compiler);
    let _configured = command
        .args([
            "-x",
            "c",
            "-",
            "-std=c23",
            "-ffreestanding",
            // Keep pinned Clang resource headers, not host system headers.
            "-nostdlibinc",
            "-Wall",
            "-Wextra",
            "-Werror",
            // Shared bootstrap helpers need not all be used by one region.
            "-Wno-unused-function",
            "-O2",
            "-c",
            "-target",
            source.target_triple(),
            "-o",
            "-",
        ])
        .env_remove("CPATH")
        .env_remove("C_INCLUDE_PATH")
        .env_remove("CPLUS_INCLUDE_PATH")
        .env_remove("OBJC_INCLUDE_PATH")
        .env_remove("OBJCPLUS_INCLUDE_PATH")
        .env_remove("INCLUDE")
        .env_remove("CCC_OVERRIDE_OPTIONS")
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped());
    #[cfg(target_os = "linux")]
    {
        use std::os::unix::process::CommandExt as _;
        let _group = command.process_group(0);
    }
    let child = command.spawn().map_err(|error| {
        BootstrapCompilerError::Launch(error.to_string().into_boxed_str())
    })?;
    let output = collect_compiler_output(child, source.source(), budget)?;
    if !output.status.success() {
        return Err(BootstrapCompilerError::CompilerFailure {
            code: output.status.code(),
            stderr: output.stderr.into_boxed_slice(),
        });
    }
    normalize_compiler_output(&source, output.stdout)
        .map_err(BootstrapCompilerError::Artifact)
}
