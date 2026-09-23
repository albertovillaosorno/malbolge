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
//   - Transactional AOT preparation and read-only lookup for register-masked
//     v6.
// - Must-Not:
//   - Trust research types, publish partial sets, or grant invocation
//     authority.
// - Allows:
//   - Inputs: product-owned v6 effect IR, runtime capability, and direct host.
//   - Outputs: verified object-only AOT sets and read-only tier selection.
//   - Side effects: process-local allocation and canonical object emission.
// - Split-When:
//   - Register-masked executable loading or durable storage gains ownership.
// - Merge-When:
//   - General AOT preparation subsumes all portable IR schema generations.
// - Summary:
//   - Bridges verified reduced v6 IR into the native AOT object boundary.
// - Description:
//   - Rechecks semantic admission, emits canonical objects, and seals exact
//     keys.
// - Usage:
//   - Used after independent v6 effect verification and before guest execution.
// - Defaults:
//   - Empty, unsupported, non-Windows, or failed inputs publish no partial set.
//

//! Transactional AOT preparation for register-masked v6 portable effect IR.

use super::{
    Arc, DIRECT_REGISTER_MASKED_CRAZY_BACKEND_ID,
    DIRECT_REGISTER_MASKED_CRAZY_BACKEND_REVISION,
    DIRECT_REGISTER_MASKED_HALT_FETCH_BACKEND_ID,
    DIRECT_REGISTER_MASKED_HALT_FETCH_BACKEND_REVISION,
    DIRECT_REGISTER_MASKED_NO_OPERATION_BACKEND_ID,
    DIRECT_REGISTER_MASKED_NO_OPERATION_BACKEND_REVISION,
    DIRECT_REGISTER_MASKED_NON_GRAPHICAL_BACKEND_ID,
    DIRECT_REGISTER_MASKED_NON_GRAPHICAL_BACKEND_REVISION,
    DIRECT_REGISTER_MASKED_OUTPUT_BACKEND_ID,
    DIRECT_REGISTER_MASKED_OUTPUT_BACKEND_REVISION,
    DIRECT_REGISTER_MASKED_ROTATE_BACKEND_ID,
    DIRECT_REGISTER_MASKED_ROTATE_BACKEND_REVISION, DirectHost,
    DirectNativeKind, DirectRegisterMaskedCrazyError,
    DirectRegisterMaskedHaltFetchError, DirectRegisterMaskedNoOperationError,
    DirectRegisterMaskedNonGraphicalError, DirectRegisterMaskedOutputError,
    DirectRegisterMaskedRotateError, Display, FormatResult, Formatter,
    HostOperatingSystem, NATIVE_REGION_ABI_REVISION, NativeArtifactCache,
    NativeArtifactKey, NativeIdentityError, NativeTargetConfig,
    NativeTargetIdentity, RegisterMaskedDirectAdmissionError,
    RegisterMaskedRegionEffectProgram, RuntimeCapability,
    VerifiedRegisterMaskedCrazyNativeObjectArtifact,
    VerifiedRegisterMaskedDirectAdmission,
    VerifiedRegisterMaskedHaltFetchNativeObjectArtifact,
    VerifiedRegisterMaskedNoOperationNativeObjectArtifact,
    VerifiedRegisterMaskedNonGraphicalNativeObjectArtifact,
    VerifiedRegisterMaskedOutputNativeObjectArtifact,
    VerifiedRegisterMaskedRotateNativeObjectArtifact,
    admit_register_masked_direct_native,
    emit_direct_register_masked_crazy_coff,
    emit_direct_register_masked_halt_fetch_coff,
    emit_direct_register_masked_no_operation_coff,
    emit_direct_register_masked_non_graphical_coff,
    emit_direct_register_masked_output_coff,
    emit_direct_register_masked_rotate_coff,
    verify_direct_register_masked_crazy,
    verify_direct_register_masked_halt_fetch,
    verify_direct_register_masked_no_operation,
    verify_direct_register_masked_non_graphical,
    verify_direct_register_masked_output, verify_direct_register_masked_rotate,
};

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum RegisterMaskedAotKind {
    Crazy,
    HaltFetch,
    NoOperation,
    NonGraphical,
    Output,
    Rotate,
}

impl RegisterMaskedAotKind {
    const fn from_admission(
        admission: &VerifiedRegisterMaskedDirectAdmission,
    ) -> Result<Self, RegisterMaskedDirectAdmissionError<'static>> {
        match admission.kind() {
            DirectNativeKind::Crazy => Ok(Self::Crazy),
            DirectNativeKind::HaltFetch => Ok(Self::HaltFetch),
            DirectNativeKind::NoOperation => Ok(Self::NoOperation),
            DirectNativeKind::NonGraphical => Ok(Self::NonGraphical),
            DirectNativeKind::Output => Ok(Self::Output),
            DirectNativeKind::Rotate => Ok(Self::Rotate),
            DirectNativeKind::Deopt
            | DirectNativeKind::HaltRegisters
            | DirectNativeKind::InitialHalt
            | DirectNativeKind::Input
            | DirectNativeKind::JumpCode
            | DirectNativeKind::JumpData => {
                Err(RegisterMaskedDirectAdmissionError::unsupported_program())
            },
        }
    }
}

/// One verified object-only register-masked v6 AOT artifact.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum VerifiedAheadOfExecutionRegisterMaskedArtifact {
    /// One-step Crazy object.
    Crazy(VerifiedRegisterMaskedCrazyNativeObjectArtifact),
    /// Graphical halt-fetch object.
    HaltFetch(VerifiedRegisterMaskedHaltFetchNativeObjectArtifact),
    /// One-step no-operation object.
    NoOperation(VerifiedRegisterMaskedNoOperationNativeObjectArtifact),
    /// Non-graphical termination object.
    NonGraphical(VerifiedRegisterMaskedNonGraphicalNativeObjectArtifact),
    /// One-step output object.
    Output(VerifiedRegisterMaskedOutputNativeObjectArtifact),
    /// One-step rotate object.
    Rotate(VerifiedRegisterMaskedRotateNativeObjectArtifact),
}

impl VerifiedAheadOfExecutionRegisterMaskedArtifact {
    /// Returns the exact v6 native artifact key.
    #[must_use]
    pub const fn key(&self) -> &NativeArtifactKey {
        match self {
            Self::Crazy(artifact) => artifact.key(),
            Self::HaltFetch(artifact) => artifact.key(),
            Self::NoOperation(artifact) => artifact.key(),
            Self::NonGraphical(artifact) => artifact.key(),
            Self::Output(artifact) => artifact.key(),
            Self::Rotate(artifact) => artifact.key(),
        }
    }

    /// Returns the reviewed semantic kind implemented by this object.
    #[must_use]
    pub const fn kind(&self) -> DirectNativeKind {
        match self {
            Self::Crazy(_artifact) => DirectNativeKind::Crazy,
            Self::HaltFetch(_artifact) => DirectNativeKind::HaltFetch,
            Self::NoOperation(_artifact) => DirectNativeKind::NoOperation,
            Self::NonGraphical(_artifact) => DirectNativeKind::NonGraphical,
            Self::Output(_artifact) => DirectNativeKind::Output,
            Self::Rotate(_artifact) => DirectNativeKind::Rotate,
        }
    }
}

/// Sealed object-only AOT set for independently verified v6 programs.
#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub struct VerifiedAheadOfExecutionRegisterMaskedSet {
    entries: NativeArtifactCache<
        Arc<VerifiedAheadOfExecutionRegisterMaskedArtifact>,
    >,
}

impl VerifiedAheadOfExecutionRegisterMaskedSet {
    /// Reports whether no exact v6 artifacts were prepared.
    #[must_use]
    pub const fn is_empty(&self) -> bool {
        self.entries.is_empty()
    }

    /// Returns the number of unique exact v6 artifact keys.
    #[must_use]
    pub const fn len(&self) -> usize {
        self.entries.len()
    }
}

/// AOT-first read-only tier result for one register-masked v6 program.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum AheadOfExecutionRegisterMaskedTier {
    /// One exact precompiled object is retained in the sealed set.
    Direct(Arc<VerifiedAheadOfExecutionRegisterMaskedArtifact>),
    /// This host has no supported direct object format.
    Interpreter,
    /// The host is supported but this exact v6 artifact is absent.
    Uncovered,
}

/// Template-specific failure while preparing one canonical v6 object.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum RegisterMaskedAheadOfExecutionObjectError {
    /// Crazy object emission or verification failed.
    Crazy(DirectRegisterMaskedCrazyError),
    /// Halt-fetch object emission or verification failed.
    HaltFetch(DirectRegisterMaskedHaltFetchError),
    /// No-operation object emission or verification failed.
    NoOperation(DirectRegisterMaskedNoOperationError),
    /// Non-graphical object emission or verification failed.
    NonGraphical(DirectRegisterMaskedNonGraphicalError),
    /// Output object emission or verification failed.
    Output(DirectRegisterMaskedOutputError),
    /// Rotate object emission or verification failed.
    Rotate(DirectRegisterMaskedRotateError),
}

impl Display for RegisterMaskedAheadOfExecutionObjectError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::Crazy(error) => Display::fmt(error, f),
            Self::HaltFetch(error) => Display::fmt(error, f),
            Self::NoOperation(error) => Display::fmt(error, f),
            Self::NonGraphical(error) => Display::fmt(error, f),
            Self::Output(error) => Display::fmt(error, f),
            Self::Rotate(error) => Display::fmt(error, f),
        }
    }
}

/// Failure while transactionally preparing one v6 AOT object set.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum AheadOfExecutionRegisterMaskedPreparationError<'requirement> {
    /// Semantic/profile admission rejected one requested v6 program.
    Admission {
        /// Exact semantic admission failure.
        error: Box<RegisterMaskedDirectAdmissionError<'requirement>>,
        /// Zero-based failing program index.
        index: usize,
    },
    /// At least one v6 program must be supplied.
    Empty,
    /// Exact v6 native identity construction failed unexpectedly.
    Identity {
        /// Exact identity error.
        error: NativeIdentityError,
        /// Zero-based failing program index.
        index: usize,
    },
    /// Canonical object emission or independent verification failed.
    Object {
        /// Template-specific object failure.
        error: RegisterMaskedAheadOfExecutionObjectError,
        /// Zero-based failing program index.
        index: usize,
    },
    /// Register-masked direct objects currently use Windows COFF only.
    TargetFormat,
}

impl Display for AheadOfExecutionRegisterMaskedPreparationError<'_> {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::Admission { error, index } => {
                write!(f, "register-masked AOT variant {index} failed: {error}")
            },
            Self::Empty => f.write_str(
                "register-masked AOT preparation requires at least one variant",
            ),
            Self::Identity { index, .. } => {
                write!(f, "register-masked AOT variant {index} identity failed")
            },
            Self::Object { error, index } => {
                write!(f, "register-masked AOT variant {index} failed: {error}")
            },
            Self::TargetFormat => f.write_str(
                "register-masked AOT preparation currently requires Windows",
            ),
        }
    }
}

/// Failure while performing one read-only v6 AOT lookup.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum AheadOfExecutionRegisterMaskedSelectionError<'requirement> {
    /// Semantic/profile admission rejected the requested v6 program.
    Admission(Box<RegisterMaskedDirectAdmissionError<'requirement>>),
    /// Exact v6 native identity construction failed unexpectedly.
    Identity(Box<NativeIdentityError>),
}

impl Display for AheadOfExecutionRegisterMaskedSelectionError<'_> {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::Admission(error) => Display::fmt(error, f),
            Self::Identity(_error) => {
                f.write_str("register-masked AOT identity construction failed")
            },
        }
    }
}

/// Transactionally prepares canonical object-only AOT artifacts for v6 IR.
///
/// Duplicate exact keys emit once. No caller-visible set exists until every
/// requested program passes semantic admission, object emission, and
/// independent canonical-byte verification. The returned objects deliberately
/// grant no executable-memory or invocation authority.
///
/// # Errors
///
/// Returns a typed preparation failure for empty input, unsupported hosts,
/// semantic admission, identity construction, emission, or verification.
pub fn prepare_ahead_of_execution_register_masked_set<'requirement>(
    programs: &'requirement [RegisterMaskedRegionEffectProgram],
    runtime: &'static RuntimeCapability,
    host: DirectHost,
) -> Result<
    VerifiedAheadOfExecutionRegisterMaskedSet,
    AheadOfExecutionRegisterMaskedPreparationError<'requirement>,
> {
    prepare_register_masked_set_iter(programs.iter(), runtime, host)
}

pub(super) fn prepare_register_masked_set_iter<'requirement, Programs>(
    programs: Programs,
    runtime: &'static RuntimeCapability,
    host: DirectHost,
) -> Result<
    VerifiedAheadOfExecutionRegisterMaskedSet,
    AheadOfExecutionRegisterMaskedPreparationError<'requirement>,
>
where
    Programs:
        IntoIterator<Item = &'requirement RegisterMaskedRegionEffectProgram>,
{
    let mut indexed_programs = programs.into_iter().enumerate().peekable();
    if indexed_programs.peek().is_none() {
        return Err(AheadOfExecutionRegisterMaskedPreparationError::Empty);
    }
    if host.operating_system != HostOperatingSystem::Windows {
        return Err(
            AheadOfExecutionRegisterMaskedPreparationError::TargetFormat,
        );
    }

    let mut entries = NativeArtifactCache::default();
    for (index, program) in indexed_programs {
        let admission = admit_register_masked_direct_native(program, runtime)
            .map_err(|error| {
            AheadOfExecutionRegisterMaskedPreparationError::Admission {
                error: Box::new(error),
                index,
            }
        })?;
        let kind = RegisterMaskedAotKind::from_admission(&admission).map_err(
            |error| AheadOfExecutionRegisterMaskedPreparationError::Admission {
                error: Box::new(error),
                index,
            },
        )?;
        let target = register_masked_target(kind, host);
        let key =
            NativeArtifactKey::new_register_masked(program, target.clone())
                .map_err(|error| {
                    AheadOfExecutionRegisterMaskedPreparationError::Identity {
                        error,
                        index,
                    }
                })?;
        if entries.get(&key).is_some() {
            continue;
        }
        let artifact = emit_verified_register_masked(program, kind, target)
            .map_err(|error| {
                AheadOfExecutionRegisterMaskedPreparationError::Object {
                    error,
                    index,
                }
            })?;
        let _replaced = entries.insert(key, Arc::new(artifact));
    }
    Ok(VerifiedAheadOfExecutionRegisterMaskedSet { entries })
}

/// Performs one read-only AOT-first lookup for register-masked v6 IR.
///
/// A miss never emits or inserts an object. Unsupported host formats select the
/// interpreter tier after semantic/profile admission, matching ordinary AOT
/// lookup fail-closed behavior.
///
/// # Errors
///
/// Returns a typed failure when semantic admission or exact identity
/// construction rejects the requested program.
pub fn select_ahead_of_execution_register_masked_tier<'requirement>(
    program: &'requirement RegisterMaskedRegionEffectProgram,
    runtime: &'static RuntimeCapability,
    host: DirectHost,
    aot: &VerifiedAheadOfExecutionRegisterMaskedSet,
) -> Result<
    AheadOfExecutionRegisterMaskedTier,
    AheadOfExecutionRegisterMaskedSelectionError<'requirement>,
> {
    let admission = admit_register_masked_direct_native(program, runtime)
        .map_err(|error| {
            AheadOfExecutionRegisterMaskedSelectionError::Admission(Box::new(
                error,
            ))
        })?;
    let kind =
        RegisterMaskedAotKind::from_admission(&admission).map_err(|error| {
            AheadOfExecutionRegisterMaskedSelectionError::Admission(Box::new(
                error,
            ))
        })?;
    if host.operating_system != HostOperatingSystem::Windows {
        return Ok(AheadOfExecutionRegisterMaskedTier::Interpreter);
    }
    let target = register_masked_target(kind, host);
    let key = NativeArtifactKey::new_register_masked(program, target).map_err(
        |error| {
            AheadOfExecutionRegisterMaskedSelectionError::Identity(Box::new(
                error,
            ))
        },
    )?;
    Ok(aot.entries.get(&key).map_or(
        AheadOfExecutionRegisterMaskedTier::Uncovered,
        |artifact| {
            AheadOfExecutionRegisterMaskedTier::Direct(Arc::clone(artifact))
        },
    ))
}

fn register_masked_target(
    kind: RegisterMaskedAotKind,
    host: DirectHost,
) -> NativeTargetIdentity {
    let (backend_id, backend_revision) = match kind {
        RegisterMaskedAotKind::Crazy => (
            DIRECT_REGISTER_MASKED_CRAZY_BACKEND_ID,
            DIRECT_REGISTER_MASKED_CRAZY_BACKEND_REVISION,
        ),
        RegisterMaskedAotKind::HaltFetch => (
            DIRECT_REGISTER_MASKED_HALT_FETCH_BACKEND_ID,
            DIRECT_REGISTER_MASKED_HALT_FETCH_BACKEND_REVISION,
        ),
        RegisterMaskedAotKind::NoOperation => (
            DIRECT_REGISTER_MASKED_NO_OPERATION_BACKEND_ID,
            DIRECT_REGISTER_MASKED_NO_OPERATION_BACKEND_REVISION,
        ),
        RegisterMaskedAotKind::NonGraphical => (
            DIRECT_REGISTER_MASKED_NON_GRAPHICAL_BACKEND_ID,
            DIRECT_REGISTER_MASKED_NON_GRAPHICAL_BACKEND_REVISION,
        ),
        RegisterMaskedAotKind::Output => (
            DIRECT_REGISTER_MASKED_OUTPUT_BACKEND_ID,
            DIRECT_REGISTER_MASKED_OUTPUT_BACKEND_REVISION,
        ),
        RegisterMaskedAotKind::Rotate => (
            DIRECT_REGISTER_MASKED_ROTATE_BACKEND_ID,
            DIRECT_REGISTER_MASKED_ROTATE_BACKEND_REVISION,
        ),
    };
    NativeTargetIdentity::new(NativeTargetConfig {
        backend_id: String::from(backend_id),
        backend_revision,
        host_isa: host.isa,
        host_os: host.operating_system,
        native_abi_revision: NATIVE_REGION_ABI_REVISION,
        required_features: Vec::new(),
    })
}

fn emit_verified_register_masked(
    program: &RegisterMaskedRegionEffectProgram,
    kind: RegisterMaskedAotKind,
    target: NativeTargetIdentity,
) -> Result<
    VerifiedAheadOfExecutionRegisterMaskedArtifact,
    RegisterMaskedAheadOfExecutionObjectError,
> {
    match kind {
        RegisterMaskedAotKind::Crazy => emit_verified_crazy(program, target),
        RegisterMaskedAotKind::HaltFetch => {
            emit_verified_halt_fetch(program, target)
        },
        RegisterMaskedAotKind::NoOperation => {
            emit_verified_no_operation(program, target)
        },
        RegisterMaskedAotKind::NonGraphical => {
            emit_verified_non_graphical(program, target)
        },
        RegisterMaskedAotKind::Output => emit_verified_output(program, target),
        RegisterMaskedAotKind::Rotate => emit_verified_rotate(program, target),
    }
}

fn emit_verified_crazy(
    program: &RegisterMaskedRegionEffectProgram,
    target: NativeTargetIdentity,
) -> Result<
    VerifiedAheadOfExecutionRegisterMaskedArtifact,
    RegisterMaskedAheadOfExecutionObjectError,
> {
    let candidate = emit_direct_register_masked_crazy_coff(program, target)
        .map_err(RegisterMaskedAheadOfExecutionObjectError::Crazy)?;
    verify_direct_register_masked_crazy(&candidate, program)
        .map(VerifiedAheadOfExecutionRegisterMaskedArtifact::Crazy)
        .map_err(RegisterMaskedAheadOfExecutionObjectError::Crazy)
}

fn emit_verified_halt_fetch(
    program: &RegisterMaskedRegionEffectProgram,
    target: NativeTargetIdentity,
) -> Result<
    VerifiedAheadOfExecutionRegisterMaskedArtifact,
    RegisterMaskedAheadOfExecutionObjectError,
> {
    let candidate =
        emit_direct_register_masked_halt_fetch_coff(program, target)
            .map_err(RegisterMaskedAheadOfExecutionObjectError::HaltFetch)?;
    verify_direct_register_masked_halt_fetch(&candidate, program)
        .map(VerifiedAheadOfExecutionRegisterMaskedArtifact::HaltFetch)
        .map_err(RegisterMaskedAheadOfExecutionObjectError::HaltFetch)
}

fn emit_verified_no_operation(
    program: &RegisterMaskedRegionEffectProgram,
    target: NativeTargetIdentity,
) -> Result<
    VerifiedAheadOfExecutionRegisterMaskedArtifact,
    RegisterMaskedAheadOfExecutionObjectError,
> {
    let candidate =
        emit_direct_register_masked_no_operation_coff(program, target)
            .map_err(RegisterMaskedAheadOfExecutionObjectError::NoOperation)?;
    verify_direct_register_masked_no_operation(&candidate, program)
        .map(VerifiedAheadOfExecutionRegisterMaskedArtifact::NoOperation)
        .map_err(RegisterMaskedAheadOfExecutionObjectError::NoOperation)
}

fn emit_verified_non_graphical(
    program: &RegisterMaskedRegionEffectProgram,
    target: NativeTargetIdentity,
) -> Result<
    VerifiedAheadOfExecutionRegisterMaskedArtifact,
    RegisterMaskedAheadOfExecutionObjectError,
> {
    let candidate =
        emit_direct_register_masked_non_graphical_coff(program, target)
            .map_err(RegisterMaskedAheadOfExecutionObjectError::NonGraphical)?;
    let verified =
        verify_direct_register_masked_non_graphical(&candidate, program)
            .map_err(RegisterMaskedAheadOfExecutionObjectError::NonGraphical)?;
    Ok(VerifiedAheadOfExecutionRegisterMaskedArtifact::NonGraphical(verified))
}

fn emit_verified_output(
    program: &RegisterMaskedRegionEffectProgram,
    target: NativeTargetIdentity,
) -> Result<
    VerifiedAheadOfExecutionRegisterMaskedArtifact,
    RegisterMaskedAheadOfExecutionObjectError,
> {
    let candidate = emit_direct_register_masked_output_coff(program, target)
        .map_err(RegisterMaskedAheadOfExecutionObjectError::Output)?;
    verify_direct_register_masked_output(&candidate, program)
        .map(VerifiedAheadOfExecutionRegisterMaskedArtifact::Output)
        .map_err(RegisterMaskedAheadOfExecutionObjectError::Output)
}

fn emit_verified_rotate(
    program: &RegisterMaskedRegionEffectProgram,
    target: NativeTargetIdentity,
) -> Result<
    VerifiedAheadOfExecutionRegisterMaskedArtifact,
    RegisterMaskedAheadOfExecutionObjectError,
> {
    let candidate = emit_direct_register_masked_rotate_coff(program, target)
        .map_err(RegisterMaskedAheadOfExecutionObjectError::Rotate)?;
    verify_direct_register_masked_rotate(&candidate, program)
        .map(VerifiedAheadOfExecutionRegisterMaskedArtifact::Rotate)
        .map_err(RegisterMaskedAheadOfExecutionObjectError::Rotate)
}
