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
//   - Fresh-or-resumed entry into the pre-layout ternary compiler stage.
// - Must-Not:
//   - Parse progress sidecars, choose target layout, or bypass program
//     admission.
// - Allows:
//   - Inputs: admitted typed-IR projections or canonical ternary checkpoint
//     bytes.
//   - Outputs: one validated pre-layout ternary program.
//   - Side effects: returned compiler-value allocation only.
// - Split-When:
//   - Another durable lowering stage needs independently versioned semantics.
// - Merge-When:
//   - Projection lowering and checkpoint restoration become indistinguishable.
// - Summary:
//   - Single ternary-stage handoff for fresh and resumed compilation.
// - Description:
//   - Lowers fresh projections or restores canonical ternary checkpoint bytes.
// - Usage:
//   - Compiler composition selects one input mode before later target layout.
// - Defaults:
//   - Invalid projection or checkpoint state fails closed before stage output.
//

//! Fresh-or-resumed pre-layout ternary compiler stage entry.

use super::input::TypedIrInput;
use super::lower::{TernaryLoweringError, lower_typed_ir};
use super::model::TernaryProgram;
use super::program_codec::{
    TernaryProgramCodecError, canonical_ternary_program,
};

/// One admitted source of pre-layout ternary stage state.
#[derive(Clone, Copy, Debug)]
pub enum TernaryStageInput<'input> {
    /// Canonical malbolge-ternary-ir-v1 durable checkpoint bytes.
    Checkpoint(&'input [u8]),
    /// Fresh admitted typed-IR semantic projection.
    Projection(&'input TypedIrInput),
}

/// Stable fail-closed ternary-stage entry failure.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum TernaryStageError {
    /// Canonical checkpoint restoration failed.
    Checkpoint(TernaryProgramCodecError),
    /// Fresh typed-IR projection lowering failed.
    Projection(TernaryLoweringError),
}

impl From<TernaryProgramCodecError> for TernaryStageError {
    fn from(error: TernaryProgramCodecError) -> Self {
        Self::Checkpoint(error)
    }
}

impl From<TernaryLoweringError> for TernaryStageError {
    fn from(error: TernaryLoweringError) -> Self {
        Self::Projection(error)
    }
}

/// Enters the ternary stage from fresh projected semantics or durable state.
///
/// # Errors
///
/// Returns `TernaryStageError` when lowering or canonical checkpoint
/// restoration fails its complete stage admission boundary.
pub fn enter_ternary_stage(
    input: TernaryStageInput<'_>,
) -> Result<TernaryProgram, TernaryStageError> {
    match input {
        TernaryStageInput::Checkpoint(checkpoint) => {
            canonical_ternary_program(checkpoint).map_err(Into::into)
        },
        TernaryStageInput::Projection(projection) => {
            lower_typed_ir(projection).map_err(Into::into)
        },
    }
}
