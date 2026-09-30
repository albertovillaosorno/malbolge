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
//   - Fresh-or-resumed entry into the governed typed compiler IR stage.
// - Must-Not:
//   - Parse progress sidecars, choose later compiler stages, or bypass typed-IR
//     admission.
// - Allows:
//   - Inputs: admitted normalized frontend projections or canonical typed-IR
//     checkpoint bytes.
//   - Outputs: one fully validated portable typed-IR module.
//   - Side effects: returned compiler-value allocation only.
// - Split-When:
//   - Another durable compiler stage needs independently versioned resume
//     semantics.
// - Merge-When:
//   - Frontend lowering and checkpoint restoration become indistinguishable.
// - Summary:
//   - Single typed-IR pipeline handoff for fresh and resumed compilation.
// - Description:
//   - Lowers fresh frontend evidence or restores the exact canonical IR codec.
// - Usage:
//   - Compiler composition selects one input mode before later lowering.
// - Defaults:
//   - Invalid frontend or checkpoint state fails closed before stage output.
//

//! Fresh-or-resumed typed compiler IR stage entry.

use super::decode::{CanonicalDecodeError, canonical_module};
use super::frontend_semantics::FrontendArtifact;
use super::lower_frontend::{FrontendLoweringError, lower_frontend_artifact};
use super::module::Module;

/// One admitted source of typed-IR stage state.
#[derive(Clone, Copy, Debug)]
pub enum TypedIrStageInput<'input> {
    /// Canonical `malbolge-typed-ir-v1` bytes from durable checkpoint state.
    Checkpoint(&'input [u8]),
    /// Fresh normalized frontend evidence to lower into typed IR.
    Frontend(&'input FrontendArtifact),
}

/// Stable fail-closed typed-IR stage entry failure.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum TypedIrStageError {
    /// Canonical checkpoint restoration failed.
    Checkpoint(CanonicalDecodeError),
    /// Fresh normalized frontend lowering failed.
    Frontend(FrontendLoweringError),
}

impl From<CanonicalDecodeError> for TypedIrStageError {
    fn from(error: CanonicalDecodeError) -> Self {
        Self::Checkpoint(error)
    }
}

impl From<FrontendLoweringError> for TypedIrStageError {
    fn from(error: FrontendLoweringError) -> Self {
        Self::Frontend(error)
    }
}

/// Enters the typed-IR compiler stage from fresh or durable state.
///
/// # Errors
///
/// Returns [`TypedIrStageError`] when fresh frontend lowering or canonical
/// checkpoint restoration fails its complete typed-IR admission boundary.
pub fn enter_typed_ir_stage(
    input: TypedIrStageInput<'_>,
) -> Result<Module, TypedIrStageError> {
    match input {
        TypedIrStageInput::Frontend(artifact) => {
            lower_frontend_artifact(artifact).map_err(Into::into)
        },
        TypedIrStageInput::Checkpoint(checkpoint) => {
            canonical_module(checkpoint).map_err(Into::into)
        },
    }
}
