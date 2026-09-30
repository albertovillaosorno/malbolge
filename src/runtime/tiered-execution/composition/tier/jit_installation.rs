// Copyright:
//   - Copyright © 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - Apache-2.0
// Confidential:
//   - false
// License-File:
//   - LICENSE-APACHE-2.0
//
// Boundary-Contract:
// - Owns:
//   - W^X installation of one semantically admitted scheduled JIT artifact.
// - Must-Not:
//   - Compile, admit candidate semantics, bind guest buffers, or execute code.
// - Allows:
//   - Inputs: completed scheduled admission and executable-memory adapter.
//   - Outputs: AOT bypass, interpreter fallback, or installed verified JIT.
//   - Side effects: executable-memory allocation/copy/protect/sync via adapter.
// - Split-When:
//   - JIT executable caching or dispatch gains independent policy.
// - Merge-When:
//   - Scheduled admission owns installation atomically.
// - Summary:
//   - Installs only verified JIT artifacts through the shared strict W^X
//     loader.
// - Description:
//   - AOT/interpreter routes bypass memory work; install failure preserves
//     verified artifact and exact loader evidence without granting dispatch.
// - Usage:
//   - Apply after scheduled JIT semantic admission and before guest binding.
// - Defaults:
//   - Any image/load failure leaves normative interpreter authority selected.
//

//! W^X installation after scheduled JIT semantic admission.

use std::sync::Arc;

use malbolge::RegionEffectProgram;

use crate::execution_native::{
    NativeExecutableLoadFailure, NativeExecutableMemoryAdapter,
    ReadyNativeExecutable, VerifiedDirectLoadError, VerifiedDirectLoadImage,
    VerifiedDirectNativeArtifact, load_native_executable,
};
use crate::native_tier_jit_admission::{
    NativeTierScheduledJitAdmission, NativeTierScheduledJitAdmissionRejection,
};

/// Installed JIT authority retaining semantic and executable identities.
#[derive(Debug, Eq, PartialEq)]
pub struct NativeTierInstalledJit {
    artifact: Box<VerifiedDirectNativeArtifact>,
    executable: Box<ReadyNativeExecutable>,
    program: Box<RegionEffectProgram>,
}

/// Why a semantically admitted JIT route stayed interpreted during install.
#[derive(Debug, Eq, PartialEq)]
pub enum NativeTierScheduledJitInstallationRejection<'attempt, Error> {
    /// Prior semantic admission already selected interpreter fallback.
    Admission(NativeTierScheduledJitAdmissionRejection<'attempt>),
    /// Verified artifact could not derive a relocation-free strict-W^X image.
    Image {
        /// Exact verified artifact retained for diagnosis/retry policy.
        artifact: Box<VerifiedDirectNativeArtifact>,
        /// Loader-image derivation failure.
        error: VerifiedDirectLoadError,
        /// Exact portable IR retained for later retry/dispatch policy.
        program: Box<RegionEffectProgram>,
    },
    /// Platform/lifecycle loading failed before a ready executable existed.
    Load {
        /// Exact verified artifact retained for diagnosis/retry policy.
        artifact: Box<VerifiedDirectNativeArtifact>,
        /// Exact phase/cause/cleanup evidence from the shared loader.
        error: Box<NativeExecutableLoadFailure<Error>>,
        /// Exact portable IR retained for later retry/dispatch policy.
        program: Box<RegionEffectProgram>,
    },
}

/// Native authority after optional W^X installation of one admitted JIT route.
#[derive(Debug, Eq, PartialEq)]
pub enum NativeTierScheduledJitInstallation<'attempt, Error> {
    /// Reuse the exact precompiled AOT artifact without executable
    /// installation.
    AheadOfExecution(Arc<VerifiedDirectNativeArtifact>),
    /// Verified JIT artifact plus synchronized RX executable mapping.
    InstalledJit(Box<NativeTierInstalledJit>),
    /// Normative interpreter remains authoritative.
    Interpreter {
        /// Admission/install rejection, when one exists.
        rejection: Option<
            NativeTierScheduledJitInstallationRejection<'attempt, Error>,
        >,
    },
}

impl NativeTierInstalledJit {
    /// Returns the exact semantically verified JIT artifact.
    #[must_use]
    pub fn artifact(&self) -> &VerifiedDirectNativeArtifact {
        self.artifact.as_ref()
    }

    /// Returns the exact synchronized RX executable retained by this owner.
    #[must_use]
    pub fn executable(&self) -> &ReadyNativeExecutable {
        self.executable.as_ref()
    }

    /// Returns the exact portable IR retained from the original AOT miss.
    #[must_use]
    pub fn program(&self) -> &RegionEffectProgram {
        self.program.as_ref()
    }
}

/// Installs only the verified JIT branch through the shared strict-W^X loader.
#[must_use]
pub fn install_scheduled_jit<'attempt, Adapter>(
    admission: NativeTierScheduledJitAdmission<'attempt>,
    adapter: &mut Adapter,
) -> NativeTierScheduledJitInstallation<'attempt, Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    match admission {
        NativeTierScheduledJitAdmission::AheadOfExecution(artifact) => {
            NativeTierScheduledJitInstallation::AheadOfExecution(artifact)
        },
        NativeTierScheduledJitAdmission::Interpreter { rejection } => {
            NativeTierScheduledJitInstallation::Interpreter {
                rejection: rejection.map(
                    NativeTierScheduledJitInstallationRejection::Admission,
                ),
            }
        },
        NativeTierScheduledJitAdmission::VerifiedJit { artifact, program } => {
            install_verified_jit(artifact, program, adapter)
        },
    }
}

fn install_verified_jit<'attempt, Adapter>(
    artifact: Box<VerifiedDirectNativeArtifact>,
    program: Box<RegionEffectProgram>,
    adapter: &mut Adapter,
) -> NativeTierScheduledJitInstallation<'attempt, Adapter::Error>
where
    Adapter: NativeExecutableMemoryAdapter,
{
    let image = match VerifiedDirectLoadImage::new(&artifact) {
        Ok(image) => image,
        Err(error) => {
            return NativeTierScheduledJitInstallation::Interpreter {
                rejection: Some(
                    NativeTierScheduledJitInstallationRejection::Image {
                        artifact,
                        error,
                        program,
                    },
                ),
            };
        },
    };
    match load_native_executable(adapter, &image) {
        Ok(executable) => NativeTierScheduledJitInstallation::InstalledJit(
            Box::new(NativeTierInstalledJit {
                artifact,
                executable: Box::new(executable),
                program,
            }),
        ),
        Err(error) => NativeTierScheduledJitInstallation::Interpreter {
            rejection: Some(
                NativeTierScheduledJitInstallationRejection::Load {
                    artifact,
                    error: Box::new(error),
                    program,
                },
            ),
        },
    }
}
