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
use std::io::Write as _;
use std::path::Path;
use std::process::{Command, Stdio};

use malbolge::{RegionEffectProgram, RuntimeCapability};

use super::{
    BootstrapProfilePreflightError, NativeArtifactError, NativeTargetIdentity,
    UntrustedNativeObjectArtifact, lower_preflighted_clang_c23,
};

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
    let mut child = Command::new(compiler)
        .args([
            "-x",
            "c",
            "-",
            "-std=c23",
            "-ffreestanding",
            "-nostdinc",
            "-Wall",
            "-Wextra",
            "-Werror",
            "-O2",
            "-c",
            "-target",
            source.target_triple(),
            "-o",
            "-",
        ])
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|error| {
            BootstrapCompilerError::Launch(error.to_string().into_boxed_str())
        })?;
    let mut input = child
        .stdin
        .take()
        .ok_or(BootstrapCompilerError::MissingInputPipe)?;
    input
        .write_all(source.source().as_bytes())
        .map_err(|error| {
            BootstrapCompilerError::SourceWrite(
                error.to_string().into_boxed_str(),
            )
        })?;
    drop(input);
    let output = child.wait_with_output().map_err(|error| {
        BootstrapCompilerError::Wait(error.to_string().into_boxed_str())
    })?;
    if !output.status.success() {
        return Err(BootstrapCompilerError::CompilerFailure {
            code: output.status.code(),
            stderr: output.stderr.into_boxed_slice(),
        });
    }
    UntrustedNativeObjectArtifact::from_compiler_output(&source, output.stdout)
        .map_err(BootstrapCompilerError::Artifact)
}
