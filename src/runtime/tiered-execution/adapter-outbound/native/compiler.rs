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
use std::process::{Child, Command, ExitStatus, Output, Stdio};
use std::sync::atomic::{AtomicBool, Ordering};
use std::thread;
use std::time::Duration;

use malbolge::{RegionEffectProgram, RuntimeCapability};

use super::{
    BootstrapProfilePreflightError, NativeArtifactError, NativeTargetIdentity,
    UntrustedNativeObjectArtifact, lower_preflighted_clang_c23,
};

// Bootstrap Clang emits small relocatable objects; these are explicit host
// safety budgets, not guest-profile capacity or a semantic size limit.
const MAX_BOOTSTRAP_OBJECT_BYTES: usize = 16 * 1024 * 1024;
const MAX_BOOTSTRAP_DIAGNOSTIC_BYTES: usize = 256 * 1024;

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
    object_limit: &AtomicBool,
    diagnostics_limit: &AtomicBool,
) -> IoResult<ExitStatus> {
    loop {
        if object_limit.load(Ordering::Acquire)
            || diagnostics_limit.load(Ordering::Acquire)
        {
            drop(child.kill());
            return child.wait();
        }
        match child.try_wait() {
            Ok(Some(status)) => return Ok(status),
            Ok(None) => thread::sleep(Duration::from_millis(5)),
            Err(error) => {
                drop(child.kill());
                drop(child.wait());
                return Err(error);
            },
        }
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

fn collect_compiler_output<'requirement>(
    mut child: Child,
    source: &str,
) -> Result<Output, BootstrapCompilerError<'requirement>> {
    let stdout_pipe = child.stdout.take().ok_or_else(|| {
        BootstrapCompilerError::Wait("compiler stdout pipe absent".into())
    })?;
    let stderr_pipe = child.stderr.take().ok_or_else(|| {
        BootstrapCompilerError::Wait("compiler stderr pipe absent".into())
    })?;
    let mut stdin = child
        .stdin
        .take()
        .ok_or(BootstrapCompilerError::MissingInputPipe)?;
    let stdout_limit = AtomicBool::new(false);
    let stderr_limit = AtomicBool::new(false);
    thread::scope(|scope| {
        let writer = scope.spawn(|| stdin.write_all(source.as_bytes()));
        let out = scope.spawn(|| {
            collect_bounded_pipe(
                stdout_pipe,
                MAX_BOOTSTRAP_OBJECT_BYTES,
                &stdout_limit,
            )
        });
        let err = scope.spawn(|| {
            collect_bounded_pipe(
                stderr_pipe,
                MAX_BOOTSTRAP_DIAGNOSTIC_BYTES,
                &stderr_limit,
            )
        });
        let status =
            wait_for_bounded_child(&mut child, &stdout_limit, &stderr_limit);
        let write_result = writer.join().map_err(|_panic| {
            BootstrapCompilerError::Wait(
                "compiler source writer panicked".into(),
            )
        })?;
        let stdout = read_joined_pipe(out)?;
        let stderr = read_joined_pipe(err)?;
        if stdout_limit.load(Ordering::Acquire) {
            return Err(BootstrapCompilerError::OutputLimit {
                stream: "stdout",
                maximum_bytes: MAX_BOOTSTRAP_OBJECT_BYTES,
            });
        }
        if stderr_limit.load(Ordering::Acquire) {
            return Err(BootstrapCompilerError::OutputLimit {
                stream: "stderr",
                maximum_bytes: MAX_BOOTSTRAP_DIAGNOSTIC_BYTES,
            });
        }
        write_result.map_err(|error| {
            BootstrapCompilerError::SourceWrite(error.to_string().into())
        })?;
        Ok(Output {
            status: status.map_err(|error| {
                BootstrapCompilerError::Wait(error.to_string().into())
            })?,
            stdout,
            stderr,
        })
    })
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
    compiler: &Path,
    program: &'requirement RegionEffectProgram,
    runtime: &'static RuntimeCapability,
    target: NativeTargetIdentity,
) -> Result<UntrustedNativeObjectArtifact, BootstrapCompilerError<'requirement>>
{
    let source = lower_preflighted_clang_c23(program, runtime, target)
        .map_err(BootstrapCompilerError::Preflight)?;
    // Ambient host include/driver overrides cannot change pinned C23
    // bootstrap sources or the headers used to compile them.
    let child = Command::new(compiler)
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
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|error| {
            BootstrapCompilerError::Launch(error.to_string().into_boxed_str())
        })?;
    let output = collect_compiler_output(child, source.source())?;
    if !output.status.success() {
        return Err(BootstrapCompilerError::CompilerFailure {
            code: output.status.code(),
            stderr: output.stderr.into_boxed_slice(),
        });
    }
    UntrustedNativeObjectArtifact::from_compiler_output(&source, output.stdout)
        .map_err(BootstrapCompilerError::Artifact)
}
