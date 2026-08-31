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
//   - Typed failures for direct emission, selection, and verification.
// - Must-Not:
//   - Bypass canonical object identity or semantic admission.
// - Allows:
//   - Inputs: reviewed direct-native planning and artifact values.
//   - Outputs: deterministic values owned by this direct-native slice.
//   - Side effects: process-local allocation only.
// - Split-When:
//   - The slice exceeds one independently reviewable responsibility.
// - Merge-When:
//   - Another module owns the exact same direct-native authority.
// - Summary:
//   - Typed direct-native failures.
// - Description:
//   - Isolates one direct-native responsibility from the facade.
// - Usage:
//   - Used only through the parent direct-native module.
// - Defaults:
//   - Unsupported values fail closed.
//

//! Typed direct-native failure contracts.

use super::*;

/// Failure while emitting or verifying the direct deoptimization stub.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum DirectDeoptError {
    /// Structural COFF admission rejected the candidate.
    Coff(CoffAdmissionError),
    /// Native artifact identity cannot be constructed from this program.
    Identity(NativeIdentityError),
    /// Object bytes differ from the canonical direct deopt object.
    ObjectBytes,
    /// Target backend/revision/native ABI is not the direct deopt contract.
    TargetBackend,
    /// Direct deopt v4 has no target-specific feature specializations.
    TargetFeatures,
    /// Direct deopt v4 emits Windows COFF only.
    TargetFormat,
}

impl Display for DirectDeoptError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        f.write_str(match self {
            Self::Coff(_error) => "direct deopt COFF structure was rejected",
            Self::Identity(_error) => {
                "direct deopt native identity construction failed"
            },
            Self::ObjectBytes => {
                "direct deopt object differs from canonical bytes"
            },
            Self::TargetBackend => {
                "target does not select direct deopt backend"
            },
            Self::TargetFeatures => {
                "direct deopt backend requires no CPU features"
            },
            Self::TargetFormat => {
                "direct deopt backend currently requires Windows COFF"
            },
        })
    }
}

impl From<CoffAdmissionError> for DirectDeoptError {
    fn from(error: CoffAdmissionError) -> Self {
        Self::Coff(error)
    }
}

impl From<NativeIdentityError> for DirectDeoptError {
    fn from(error: NativeIdentityError) -> Self {
        Self::Identity(error)
    }
}

/// Failure while emitting or verifying v5 guarded initial halt.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum DirectExecutionGeometryInitialHaltError {
    /// Structural COFF admission rejected the candidate.
    Coff(CoffAdmissionError),
    /// Native artifact identity cannot be constructed from this v5 program.
    Identity(NativeIdentityError),
    /// Object bytes differ from the canonical guarded halt object.
    ObjectBytes,
    /// Explicit-geometry IR is outside the guarded initial-halt subset.
    ProgramShape,
    /// Target backend/revision/native ABI is not this v5 contract.
    TargetBackend,
    /// This v5 backend has no target-specific feature specializations.
    TargetFeatures,
    /// This v5 backend currently emits Windows COFF only.
    TargetFormat,
}

impl Display for DirectExecutionGeometryInitialHaltError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        f.write_str(match self {
            Self::Coff(_error) => "v5 initial-halt COFF structure was rejected",
            Self::Identity(_error) => {
                "v5 initial-halt identity construction failed"
            },
            Self::ObjectBytes => {
                "v5 initial-halt object differs from canonical bytes"
            },
            Self::ProgramShape => {
                "explicit-geometry IR is outside v5 initial-halt subset"
            },
            Self::TargetBackend => {
                "target does not select v5 initial-halt backend"
            },
            Self::TargetFeatures => {
                "v5 initial-halt backend requires no CPU features"
            },
            Self::TargetFormat => {
                "v5 initial-halt backend requires Windows COFF"
            },
        })
    }
}

impl From<CoffAdmissionError> for DirectExecutionGeometryInitialHaltError {
    fn from(error: CoffAdmissionError) -> Self {
        Self::Coff(error)
    }
}

impl From<NativeIdentityError> for DirectExecutionGeometryInitialHaltError {
    fn from(error: NativeIdentityError) -> Self {
        Self::Identity(error)
    }
}

/// Failure while emitting or verifying v5 guarded initial jump-data.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum DirectExecutionGeometryInitialJumpDataError {
    /// Structural COFF admission rejected the candidate.
    Coff(CoffAdmissionError),
    /// Native artifact identity cannot be constructed from this v5 program.
    Identity(NativeIdentityError),
    /// Object bytes differ from the canonical guarded aliasing initial
    /// jump-data object.
    ObjectBytes,
    /// Explicit-geometry IR is outside the guarded aliasing initial jump-data
    /// subset.
    ProgramShape,
    /// Target backend/revision/native ABI is not this v5 contract.
    TargetBackend,
    /// This v5 backend has no target-specific feature specializations.
    TargetFeatures,
    /// This v5 backend currently emits Windows COFF only.
    TargetFormat,
}

impl Display for DirectExecutionGeometryInitialJumpDataError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        f.write_str(match self {
            Self::Coff(_error) => "v5 initial-jump COFF structure was rejected",
            Self::Identity(_error) => {
                "v5 initial jump-data identity construction failed"
            },
            Self::ObjectBytes => {
                "v5 initial-jump object differs from canonical bytes"
            },
            Self::ProgramShape => {
                "explicit-geometry IR is outside v5 initial-jump subset"
            },
            Self::TargetBackend => {
                "target does not select v5 initial jump-data backend"
            },
            Self::TargetFeatures => {
                "v5 initial jump-data backend requires no CPU features"
            },
            Self::TargetFormat => {
                "v5 initial-jump backend requires Windows COFF"
            },
        })
    }
}

impl From<CoffAdmissionError> for DirectExecutionGeometryInitialJumpDataError {
    fn from(error: CoffAdmissionError) -> Self {
        Self::Coff(error)
    }
}

impl From<NativeIdentityError> for DirectExecutionGeometryInitialJumpDataError {
    fn from(error: NativeIdentityError) -> Self {
        Self::Identity(error)
    }
}

/// Failure while emitting or verifying v5 guarded no-operation.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum DirectExecutionGeometryNoOperationError {
    /// Structural COFF admission rejected the candidate.
    Coff(CoffAdmissionError),
    /// Native artifact identity cannot be constructed from this v5 program.
    Identity(NativeIdentityError),
    /// Object bytes differ from the canonical guarded no-operation object.
    ObjectBytes,
    /// Explicit-geometry IR is outside the guarded no-operation subset.
    ProgramShape,
    /// Target backend/revision/native ABI is not this v5 contract.
    TargetBackend,
    /// This v5 backend has no target-specific feature specializations.
    TargetFeatures,
    /// This v5 backend currently emits Windows COFF only.
    TargetFormat,
}

impl Display for DirectExecutionGeometryNoOperationError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        f.write_str(match self {
            Self::Coff(_error) => "v5 no-operation COFF structure was rejected",
            Self::Identity(_error) => {
                "v5 no-operation identity construction failed"
            },
            Self::ObjectBytes => {
                "v5 no-operation object differs from canonical bytes"
            },
            Self::ProgramShape => {
                "explicit-geometry IR is outside v5 no-operation subset"
            },
            Self::TargetBackend => {
                "target does not select v5 no-operation backend"
            },
            Self::TargetFeatures => {
                "v5 no-operation backend requires no CPU features"
            },
            Self::TargetFormat => {
                "v5 no-operation backend requires Windows COFF"
            },
        })
    }
}

impl From<CoffAdmissionError> for DirectExecutionGeometryNoOperationError {
    fn from(error: CoffAdmissionError) -> Self {
        Self::Coff(error)
    }
}

impl From<NativeIdentityError> for DirectExecutionGeometryNoOperationError {
    fn from(error: NativeIdentityError) -> Self {
        Self::Identity(error)
    }
}

/// Failure while emitting or verifying v5 guarded output.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum DirectExecutionGeometryOutputError {
    /// Structural COFF admission rejected the candidate.
    Coff(CoffAdmissionError),
    /// Native artifact identity cannot be constructed from this v5 program.
    Identity(NativeIdentityError),
    /// Object bytes differ from the canonical guarded output object.
    ObjectBytes,
    /// Explicit-geometry IR is outside the guarded output subset.
    ProgramShape,
    /// Target backend/revision/native ABI is not this v5 contract.
    TargetBackend,
    /// This v5 backend has no target-specific feature specializations.
    TargetFeatures,
    /// This v5 backend currently emits Windows COFF only.
    TargetFormat,
}

impl Display for DirectExecutionGeometryOutputError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        f.write_str(match self {
            Self::Coff(_error) => "v5 output COFF structure was rejected",
            Self::Identity(_error) => "v5 output identity construction failed",
            Self::ObjectBytes => {
                "v5 output object differs from canonical bytes"
            },
            Self::ProgramShape => {
                "explicit-geometry IR is outside v5 output subset"
            },
            Self::TargetBackend => "target does not select v5 output backend",
            Self::TargetFeatures => {
                "v5 output backend requires no CPU features"
            },
            Self::TargetFormat => "v5 output backend requires Windows COFF",
        })
    }
}

impl From<CoffAdmissionError> for DirectExecutionGeometryOutputError {
    fn from(error: CoffAdmissionError) -> Self {
        Self::Coff(error)
    }
}

impl From<NativeIdentityError> for DirectExecutionGeometryOutputError {
    fn from(error: NativeIdentityError) -> Self {
        Self::Identity(error)
    }
}

/// Failure while emitting or verifying v5 guarded rotate.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum DirectExecutionGeometryRotateError {
    /// Structural COFF admission rejected the candidate.
    Coff(CoffAdmissionError),
    /// Native artifact identity cannot be constructed from this v5 program.
    Identity(NativeIdentityError),
    /// Object bytes differ from the canonical guarded rotate object.
    ObjectBytes,
    /// Explicit-geometry IR is outside the guarded rotate subset.
    ProgramShape,
    /// Target backend/revision/native ABI is not this v5 contract.
    TargetBackend,
    /// This v5 backend has no target-specific feature specializations.
    TargetFeatures,
    /// This v5 backend currently emits Windows COFF only.
    TargetFormat,
}

impl Display for DirectExecutionGeometryRotateError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        f.write_str(match self {
            Self::Coff(_error) => "v5 rotate COFF structure was rejected",
            Self::Identity(_error) => "v5 rotate identity construction failed",
            Self::ObjectBytes => {
                "v5 rotate object differs from canonical bytes"
            },
            Self::ProgramShape => {
                "explicit-geometry IR is outside v5 rotate subset"
            },
            Self::TargetBackend => "target does not select v5 rotate backend",
            Self::TargetFeatures => {
                "v5 rotate backend requires no CPU features"
            },
            Self::TargetFormat => "v5 rotate backend requires Windows COFF",
        })
    }
}

impl From<CoffAdmissionError> for DirectExecutionGeometryRotateError {
    fn from(error: CoffAdmissionError) -> Self {
        Self::Coff(error)
    }
}

impl From<NativeIdentityError> for DirectExecutionGeometryRotateError {
    fn from(error: NativeIdentityError) -> Self {
        Self::Identity(error)
    }
}

/// Failure while emitting or verifying exact-observation direct halt.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum DirectHaltRegistersError {
    /// Structural COFF admission rejected the candidate.
    Coff(CoffAdmissionError),
    /// Native artifact identity cannot be constructed from this program.
    Identity(NativeIdentityError),
    /// Object bytes differ from the canonical observation-bound halt object.
    ObjectBytes,
    /// Portable IR is outside the exact observation-bound halt subset.
    ProgramShape,
    /// Target backend/revision/native ABI is not the register-halt contract.
    TargetBackend,
    /// Register-halt v5 has no target-specific feature specializations.
    TargetFeatures,
    /// Register-halt v5 emits Windows COFF only.
    TargetFormat,
}

impl Display for DirectHaltRegistersError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        f.write_str(match self {
            Self::Coff(_error) => {
                "direct register-halt COFF structure was rejected"
            },
            Self::Identity(_error) => {
                "direct register-halt identity construction failed"
            },
            Self::ObjectBytes => {
                "direct register-halt object differs from canonical bytes"
            },
            Self::ProgramShape => {
                "portable IR is outside direct register-halt subset"
            },
            Self::TargetBackend => {
                "target does not select direct register-halt backend"
            },
            Self::TargetFeatures => {
                "direct register-halt backend requires no CPU features"
            },
            Self::TargetFormat => {
                "direct register-halt backend requires Windows COFF"
            },
        })
    }
}

impl From<CoffAdmissionError> for DirectHaltRegistersError {
    fn from(error: CoffAdmissionError) -> Self {
        Self::Coff(error)
    }
}

impl From<NativeIdentityError> for DirectHaltRegistersError {
    fn from(error: NativeIdentityError) -> Self {
        Self::Identity(error)
    }
}

/// Failure while emitting or verifying exact graphical halt fetch.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum DirectHaltFetchError {
    /// Structural COFF admission rejected the candidate.
    Coff(CoffAdmissionError),
    /// Native artifact identity cannot be constructed from this program.
    Identity(NativeIdentityError),
    /// Object bytes differ from the canonical halt-fetch object.
    ObjectBytes,
    /// Portable IR is outside the exact halt-fetch subset.
    ProgramShape,
    /// Target backend/revision/native ABI is not this contract.
    TargetBackend,
    /// Halt-fetch v2 has no target-specific feature specializations.
    TargetFeatures,
    /// Direct halt-fetch currently emits Windows COFF only.
    TargetFormat,
}

impl Display for DirectHaltFetchError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        f.write_str(match self {
            Self::Coff(_error) => {
                "direct halt-fetch COFF structure was rejected"
            },
            Self::Identity(_error) => {
                "direct halt-fetch identity construction failed"
            },
            Self::ObjectBytes => {
                "direct halt-fetch object differs from canonical bytes"
            },
            Self::ProgramShape => {
                "portable IR is outside direct halt-fetch subset"
            },
            Self::TargetBackend => {
                "target does not select direct halt-fetch backend"
            },
            Self::TargetFeatures => {
                "direct halt-fetch backend requires no CPU features"
            },
            Self::TargetFormat => {
                "direct halt-fetch backend requires Windows COFF"
            },
        })
    }
}

impl From<CoffAdmissionError> for DirectHaltFetchError {
    fn from(error: CoffAdmissionError) -> Self {
        Self::Coff(error)
    }
}

impl From<NativeIdentityError> for DirectHaltFetchError {
    fn from(error: NativeIdentityError) -> Self {
        Self::Identity(error)
    }
}

/// Failure while emitting or verifying direct non-graphical termination.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum DirectNonGraphicalError {
    /// Structural COFF admission rejected the candidate.
    Coff(CoffAdmissionError),
    /// Native artifact identity cannot be constructed from this program.
    Identity(NativeIdentityError),
    /// Object bytes differ from the canonical non-graphical object.
    ObjectBytes,
    /// Portable IR is outside the exact non-graphical subset.
    ProgramShape,
    /// Target backend/revision/native ABI is not this contract.
    TargetBackend,
    /// Non-graphical v2 has no target-specific feature specializations.
    TargetFeatures,
    /// Direct non-graphical currently emits Windows COFF only.
    TargetFormat,
}

impl Display for DirectNonGraphicalError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        f.write_str(match self {
            Self::Coff(_error) => {
                "direct non-graphical COFF structure was rejected"
            },
            Self::Identity(_error) => {
                "direct non-graphical identity construction failed"
            },
            Self::ObjectBytes => {
                "direct non-graphical object differs from canonical bytes"
            },
            Self::ProgramShape => {
                "portable IR is outside direct non-graphical subset"
            },
            Self::TargetBackend => {
                "target does not select direct non-graphical backend"
            },
            Self::TargetFeatures => {
                "direct non-graphical backend requires no CPU features"
            },
            Self::TargetFormat => {
                "direct non-graphical backend requires Windows COFF"
            },
        })
    }
}

impl From<CoffAdmissionError> for DirectNonGraphicalError {
    fn from(error: CoffAdmissionError) -> Self {
        Self::Coff(error)
    }
}

impl From<NativeIdentityError> for DirectNonGraphicalError {
    fn from(error: NativeIdentityError) -> Self {
        Self::Identity(error)
    }
}

/// Failure while emitting or verifying exact non-aliasing jump-code.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum DirectJumpCodeError {
    /// Structural COFF admission rejected the candidate.
    Coff(CoffAdmissionError),
    /// Native artifact identity cannot be constructed from this program.
    Identity(NativeIdentityError),
    /// Object bytes differ from the canonical jump-code object.
    ObjectBytes,
    /// Portable IR is outside the exact jump-code subset.
    ProgramShape,
    /// Target backend/revision/native ABI is not this contract.
    TargetBackend,
    /// Jump-code v1 has no target-specific feature specializations.
    TargetFeatures,
    /// Direct jump-code currently emits Windows COFF only.
    TargetFormat,
}

impl Display for DirectJumpCodeError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        f.write_str(match self {
            Self::Coff(_error) => {
                "direct jump-code COFF structure was rejected"
            },
            Self::Identity(_error) => {
                "direct jump-code identity construction failed"
            },
            Self::ObjectBytes => {
                "direct jump-code object differs from canonical bytes"
            },
            Self::ProgramShape => {
                "portable IR is outside direct jump-code subset"
            },
            Self::TargetBackend => {
                "target does not select direct jump-code backend"
            },
            Self::TargetFeatures => {
                "direct jump-code backend requires no CPU features"
            },
            Self::TargetFormat => {
                "direct jump-code backend requires Windows COFF"
            },
        })
    }
}

impl From<CoffAdmissionError> for DirectJumpCodeError {
    fn from(error: CoffAdmissionError) -> Self {
        Self::Coff(error)
    }
}

impl From<NativeIdentityError> for DirectJumpCodeError {
    fn from(error: NativeIdentityError) -> Self {
        Self::Identity(error)
    }
}

/// Failure while emitting or verifying exact non-aliasing jump-data.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum DirectJumpDataError {
    /// Structural COFF admission rejected the candidate.
    Coff(CoffAdmissionError),
    /// Native artifact identity cannot be constructed from this program.
    Identity(NativeIdentityError),
    /// Object bytes differ from the canonical jump-data object.
    ObjectBytes,
    /// Portable IR is outside the exact jump-data subset.
    ProgramShape,
    /// Target backend/revision/native ABI is not this contract.
    TargetBackend,
    /// Jump-data v1 has no target-specific feature specializations.
    TargetFeatures,
    /// Direct jump-data currently emits Windows COFF only.
    TargetFormat,
}

impl Display for DirectJumpDataError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        f.write_str(match self {
            Self::Coff(_error) => {
                "direct jump-data COFF structure was rejected"
            },
            Self::Identity(_error) => {
                "direct jump-data identity construction failed"
            },
            Self::ObjectBytes => {
                "direct jump-data object differs from canonical bytes"
            },
            Self::ProgramShape => {
                "portable IR is outside direct jump-data subset"
            },
            Self::TargetBackend => {
                "target does not select direct jump-data backend"
            },
            Self::TargetFeatures => {
                "direct jump-data backend requires no CPU features"
            },
            Self::TargetFormat => {
                "direct jump-data backend requires Windows COFF"
            },
        })
    }
}

impl From<CoffAdmissionError> for DirectJumpDataError {
    fn from(error: CoffAdmissionError) -> Self {
        Self::Coff(error)
    }
}

impl From<NativeIdentityError> for DirectJumpDataError {
    fn from(error: NativeIdentityError) -> Self {
        Self::Identity(error)
    }
}

/// Failure while emitting or verifying exact non-aliasing crazy.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum DirectCrazyError {
    /// Structural COFF admission rejected the candidate.
    Coff(CoffAdmissionError),
    /// Native artifact identity cannot be constructed from this program.
    Identity(NativeIdentityError),
    /// Object bytes differ from the canonical crazy object.
    ObjectBytes,
    /// Portable IR is outside the exact crazy subset.
    ProgramShape,
    /// Target backend/revision/native ABI is not this contract.
    TargetBackend,
    /// Crazy v1 has no target-specific feature specializations.
    TargetFeatures,
    /// Direct crazy currently emits Windows COFF only.
    TargetFormat,
}

impl Display for DirectCrazyError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        f.write_str(match self {
            Self::Coff(_error) => "direct crazy COFF structure was rejected",
            Self::Identity(_error) => {
                "direct crazy identity construction failed"
            },
            Self::ObjectBytes => {
                "direct crazy object differs from canonical bytes"
            },
            Self::ProgramShape => "portable IR is outside direct crazy subset",
            Self::TargetBackend => {
                "target does not select direct crazy backend"
            },
            Self::TargetFeatures => {
                "direct crazy backend requires no CPU features"
            },
            Self::TargetFormat => "direct crazy backend requires Windows COFF",
        })
    }
}

impl From<CoffAdmissionError> for DirectCrazyError {
    fn from(error: CoffAdmissionError) -> Self {
        Self::Coff(error)
    }
}

impl From<NativeIdentityError> for DirectCrazyError {
    fn from(error: NativeIdentityError) -> Self {
        Self::Identity(error)
    }
}

/// Failure while emitting or verifying exact one-step input.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum DirectInputError {
    /// Structural COFF admission rejected the candidate.
    Coff(CoffAdmissionError),
    /// Native artifact identity cannot be constructed from this program.
    Identity(NativeIdentityError),
    /// Object bytes differ from the canonical input object.
    ObjectBytes,
    /// Portable IR is outside the exact input subset.
    ProgramShape,
    /// Target backend/revision/native ABI is not this contract.
    TargetBackend,
    /// Input v1 has no target-specific feature specializations.
    TargetFeatures,
    /// Direct input currently emits Windows COFF only.
    TargetFormat,
}

impl Display for DirectInputError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        f.write_str(match self {
            Self::Coff(_error) => "direct input COFF structure was rejected",
            Self::Identity(_error) => {
                "direct input identity construction failed"
            },
            Self::ObjectBytes => {
                "direct input object differs from canonical bytes"
            },
            Self::ProgramShape => "portable IR is outside direct input subset",
            Self::TargetBackend => {
                "target does not select direct input backend"
            },
            Self::TargetFeatures => {
                "direct input backend requires no CPU features"
            },
            Self::TargetFormat => "direct input backend requires Windows COFF",
        })
    }
}

impl From<CoffAdmissionError> for DirectInputError {
    fn from(error: CoffAdmissionError) -> Self {
        Self::Coff(error)
    }
}

impl From<NativeIdentityError> for DirectInputError {
    fn from(error: NativeIdentityError) -> Self {
        Self::Identity(error)
    }
}

/// Failure while emitting or verifying exact one-step output.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum DirectOutputError {
    /// Structural COFF admission rejected the candidate.
    Coff(CoffAdmissionError),
    /// Native artifact identity cannot be constructed from this program.
    Identity(NativeIdentityError),
    /// Object bytes differ from the canonical output object.
    ObjectBytes,
    /// Portable IR is outside the exact output subset.
    ProgramShape,
    /// Target backend/revision/native ABI is not this contract.
    TargetBackend,
    /// Output v1 has no target-specific feature specializations.
    TargetFeatures,
    /// Direct output currently emits Windows COFF only.
    TargetFormat,
}

impl Display for DirectOutputError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        f.write_str(match self {
            Self::Coff(_error) => "direct output COFF structure was rejected",
            Self::Identity(_error) => {
                "direct output identity construction failed"
            },
            Self::ObjectBytes => {
                "direct output object differs from canonical bytes"
            },
            Self::ProgramShape => "portable IR is outside direct output subset",
            Self::TargetBackend => {
                "target does not select direct output backend"
            },
            Self::TargetFeatures => {
                "direct output backend requires no CPU features"
            },
            Self::TargetFormat => "direct output backend requires Windows COFF",
        })
    }
}

impl From<CoffAdmissionError> for DirectOutputError {
    fn from(error: CoffAdmissionError) -> Self {
        Self::Coff(error)
    }
}

impl From<NativeIdentityError> for DirectOutputError {
    fn from(error: NativeIdentityError) -> Self {
        Self::Identity(error)
    }
}

/// Failure while emitting or verifying exact non-aliasing rotate.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum DirectRotateError {
    /// Structural COFF admission rejected the candidate.
    Coff(CoffAdmissionError),
    /// Native artifact identity cannot be constructed from this program.
    Identity(NativeIdentityError),
    /// Object bytes differ from the canonical rotate object.
    ObjectBytes,
    /// Portable IR is outside the exact rotate subset.
    ProgramShape,
    /// Target backend/revision/native ABI is not this contract.
    TargetBackend,
    /// Rotate v1 has no target-specific feature specializations.
    TargetFeatures,
    /// Direct rotate currently emits Windows COFF only.
    TargetFormat,
}

impl Display for DirectRotateError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        f.write_str(match self {
            Self::Coff(_error) => "direct rotate COFF structure was rejected",
            Self::Identity(_error) => {
                "direct rotate identity construction failed"
            },
            Self::ObjectBytes => {
                "direct rotate object differs from canonical bytes"
            },
            Self::ProgramShape => "portable IR is outside direct rotate subset",
            Self::TargetBackend => {
                "target does not select direct rotate backend"
            },
            Self::TargetFeatures => {
                "direct rotate backend requires no CPU features"
            },
            Self::TargetFormat => "direct rotate backend requires Windows COFF",
        })
    }
}

impl From<CoffAdmissionError> for DirectRotateError {
    fn from(error: CoffAdmissionError) -> Self {
        Self::Coff(error)
    }
}

impl From<NativeIdentityError> for DirectRotateError {
    fn from(error: NativeIdentityError) -> Self {
        Self::Identity(error)
    }
}

/// Failure while emitting or verifying exact one-step no-operation.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum DirectNoOperationError {
    /// Structural COFF admission rejected the candidate.
    Coff(CoffAdmissionError),
    /// Native artifact identity cannot be constructed from this program.
    Identity(NativeIdentityError),
    /// Object bytes differ from the canonical no-operation object.
    ObjectBytes,
    /// Portable IR is outside the exact no-operation subset.
    ProgramShape,
    /// Target backend/revision/native ABI is not this contract.
    TargetBackend,
    /// No-operation v2 has no target-specific feature specializations.
    TargetFeatures,
    /// Direct no-operation currently emits Windows COFF only.
    TargetFormat,
}

impl Display for DirectNoOperationError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        f.write_str(match self {
            Self::Coff(_error) => {
                "direct no-operation COFF structure was rejected"
            },
            Self::Identity(_error) => {
                "direct no-operation identity construction failed"
            },
            Self::ObjectBytes => {
                "direct no-operation object differs from canonical bytes"
            },
            Self::ProgramShape => {
                "portable IR is outside direct no-operation subset"
            },
            Self::TargetBackend => {
                "target does not select direct no-operation backend"
            },
            Self::TargetFeatures => {
                "direct no-operation backend requires no CPU features"
            },
            Self::TargetFormat => {
                "direct no-operation backend requires Windows COFF"
            },
        })
    }
}

impl From<CoffAdmissionError> for DirectNoOperationError {
    fn from(error: CoffAdmissionError) -> Self {
        Self::Coff(error)
    }
}

impl From<NativeIdentityError> for DirectNoOperationError {
    fn from(error: NativeIdentityError) -> Self {
        Self::Identity(error)
    }
}

/// Failure while emitting or verifying the direct initial-halt fast path.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum DirectInitialHaltError {
    /// Structural COFF admission rejected the candidate.
    Coff(CoffAdmissionError),
    /// Native artifact identity cannot be constructed from this program.
    Identity(NativeIdentityError),
    /// Object bytes differ from the canonical direct initial-halt object.
    ObjectBytes,
    /// Portable IR is outside the exact initial-halt subset.
    ProgramShape,
    /// Target backend/revision/native ABI is not the initial-halt contract.
    TargetBackend,
    /// Direct initial-halt v4 has no target-specific feature specializations.
    TargetFeatures,
    /// Direct initial-halt v4 emits Windows COFF only.
    TargetFormat,
}

impl Display for DirectInitialHaltError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        f.write_str(match self {
            Self::Coff(_error) => {
                "direct initial-halt COFF structure was rejected"
            },
            Self::Identity(_error) => {
                "direct initial-halt identity construction failed"
            },
            Self::ObjectBytes => {
                "direct initial-halt object differs from canonical bytes"
            },
            Self::ProgramShape => {
                "portable IR is outside direct initial-halt subset"
            },
            Self::TargetBackend => {
                "target does not select direct initial-halt backend"
            },
            Self::TargetFeatures => {
                "direct initial-halt backend requires no CPU features"
            },
            Self::TargetFormat => {
                "direct initial-halt backend requires Windows COFF"
            },
        })
    }
}

impl From<CoffAdmissionError> for DirectInitialHaltError {
    fn from(error: CoffAdmissionError) -> Self {
        Self::Coff(error)
    }
}

impl From<NativeIdentityError> for DirectInitialHaltError {
    fn from(error: NativeIdentityError) -> Self {
        Self::Identity(error)
    }
}
/// Failure while selecting/emitting/verifying one direct native template.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum DirectSelectionError<'requirement> {
    /// Crazy artifact emission or admission failed.
    Crazy(Box<DirectCrazyError>),
    /// Deoptimization artifact emission or admission failed.
    Deopt(Box<DirectDeoptError>),
    /// Graphical halt-fetch artifact emission or admission failed.
    HaltFetch(Box<DirectHaltFetchError>),
    /// Arbitrary-register halt artifact emission or admission failed.
    HaltRegisters(Box<DirectHaltRegistersError>),
    /// Initial-halt artifact emission or admission failed.
    InitialHalt(Box<DirectInitialHaltError>),
    /// Input artifact emission or admission failed.
    Input(Box<DirectInputError>),
    /// Jump-code artifact emission or admission failed.
    JumpCode(Box<DirectJumpCodeError>),
    /// Jump-data artifact emission or admission failed.
    JumpData(Box<DirectJumpDataError>),
    /// No-operation artifact emission or admission failed.
    NoOperation(Box<DirectNoOperationError>),
    /// Non-graphical artifact emission or admission failed.
    NonGraphical(Box<DirectNonGraphicalError>),
    /// Output artifact emission or admission failed.
    Output(Box<DirectOutputError>),
    /// Selected runtime cannot implement the admitted profile requirement.
    Profile(Box<PortableProfileRequirementError<'requirement>>),
    /// Portable profile envelope is not canonical for its declared identity.
    ProfileRequirement,
    /// Rotate artifact emission or admission failed.
    Rotate(Box<DirectRotateError>),
    /// Direct native templates currently emit Windows COFF only.
    TargetFormat,
}

impl Display for DirectSelectionError<'_> {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::Crazy(error) => Display::fmt(error, f),
            Self::Deopt(error) => Display::fmt(error, f),
            Self::HaltRegisters(error) => Display::fmt(error, f),
            Self::HaltFetch(error) => Display::fmt(error, f),
            Self::InitialHalt(error) => Display::fmt(error, f),
            Self::Input(error) => Display::fmt(error, f),
            Self::JumpCode(error) => Display::fmt(error, f),
            Self::JumpData(error) => Display::fmt(error, f),
            Self::NonGraphical(error) => Display::fmt(error, f),
            Self::NoOperation(error) => Display::fmt(error, f),
            Self::Output(error) => Display::fmt(error, f),
            Self::Profile(error) => Display::fmt(error, f),
            Self::ProfileRequirement => {
                f.write_str("portable IR profile requirement is not canonical")
            },
            Self::Rotate(error) => Display::fmt(error, f),
            Self::TargetFormat => f.write_str(
                "direct native selection currently requires Windows",
            ),
        }
    }
}
