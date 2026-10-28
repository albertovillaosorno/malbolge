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
//   - Product selection between fresh typed IR and verified progress resume.
// - Must-Not:
//   - Parse sidecar JSON, duplicate portable-checkpoint validation, or select
//     repository-local tool paths implicitly.
// - Allows:
//   - Inputs: explicit interpreter, inspector, and progress-sidecar paths.
//   - Outputs: one fully admitted typed-IR module or stable bridge failure.
//   - Side effects: one bounded child process owned by the caller-selected
//     progress inspector.
// - Split-When:
//   - Another durable compiler-state codec needs an independent adapter.
// - Merge-When:
//   - Compiler composition directly owns the progress-sidecar wire contract.
// - Summary:
//   - Selects fresh frontend lowering or verified typed-IR progress state.
// - Description:
//   - Delegates sidecar/envelope validation to the repository inspector and
//     admits only the exact typed-IR codec bytes returned by extraction.
// - Usage:
//   - Compiler composition supplies its explicit progress-inspector command.
// - Defaults:
//   - Launch failure, inspector diagnostics, and invalid typed IR fail closed.
//

//! Verified progress-sidecar composition for typed compiler IR resume.

#[path = "progress_inspector.rs"]
mod inspector_transport;

use std::path::Path;

use inspector_transport::{InspectorFailure, extract_checkpoint};

use super::control::Terminator;
use super::encode::TYPED_IR_CODEC_ID;
use super::frontend_semantics::{
    FrontendArtifact, FrontendPosition, FrontendReturnIntegerFunction,
    FrontendSpan,
};
use super::instruction::Instruction;
use super::lower_frontend::{admit_frontend_function, validate_identity};
use super::module::{Function, Module};
use super::source::{SourcePosition, SourceSpan};
use super::stage::{
    TypedIrStageError, TypedIrStageInput, enter_typed_ir_stage,
};
use super::types::{TypeDef, TypeEntry};

/// Product compiler selection for entering the typed-IR stage.
#[derive(Clone, Copy, Debug)]
pub enum TypedIrCompilerStageInput<'input> {
    /// Lower fresh normalized frontend evidence.
    Fresh(&'input FrontendArtifact),
    /// Restore verified typed IR from one durable progress sidecar.
    Progress {
        /// Explicit interpreter used to run the trusted inspector.
        interpreter: &'input Path,
        /// Explicit trusted progress-sidecar inspector.
        inspector: &'input Path,
        /// Durable progress sidecar selecting the committed checkpoint.
        progress: &'input Path,
    },
    /// Resume only when the admitted checkpoint matches expected frontend
    /// source identity and function provenance.
    ProgressForSource {
        /// Caller-admitted frontend source, not executable checkpoint state.
        expected: &'input FrontendArtifact,
        /// Explicit interpreter used to run the trusted inspector.
        interpreter: &'input Path,
        /// Explicit trusted progress-sidecar inspector.
        inspector: &'input Path,
        /// Durable progress sidecar selecting the committed checkpoint.
        progress: &'input Path,
    },
}

/// Stable product compiler failure while selecting typed-IR stage state.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum TypedIrCompilerStageError {
    /// Fresh frontend lowering failed typed-IR admission.
    Fresh(TypedIrStageError),
    /// Durable progress extraction or checkpoint admission failed.
    Progress(ProgressCheckpointError),
}

/// Stable failure categories for progress-sidecar typed-IR resume adaptation.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ProgressCheckpointError {
    /// Restored module or function provenance differs from expected source.
    IdentityMismatch,
    /// The configured progress inspector could not be launched.
    InspectorLaunch,
    /// The inspector rejected the generation or emitted diagnostics.
    InspectorRejected,
    /// Extracted bytes failed typed-IR checkpoint admission.
    Stage(TypedIrStageError),
}

impl From<TypedIrStageError> for ProgressCheckpointError {
    fn from(error: TypedIrStageError) -> Self {
        Self::Stage(error)
    }
}

/// Restores typed IR directly from one durable progress-sidecar path.
///
/// # Errors
///
/// Returns [`ProgressCheckpointError`] when the inspector cannot launch,
/// rejects the durable generation, emits unexpected diagnostics, or returns
/// bytes that fail complete typed-IR checkpoint admission.
pub fn resume_typed_ir_from_progress(
    interpreter: &Path,
    inspector: &Path,
    progress: &Path,
) -> Result<Module, ProgressCheckpointError> {
    let bytes =
        extract_checkpoint(interpreter, inspector, TYPED_IR_CODEC_ID, progress)
            .map_err(|error| match error {
                InspectorFailure::Launch => {
                    ProgressCheckpointError::InspectorLaunch
                },
                InspectorFailure::Rejected => {
                    ProgressCheckpointError::InspectorRejected
                },
            })?;
    enter_typed_ir_stage(TypedIrStageInput::Checkpoint(&bytes))
        .map_err(Into::into)
}

// These are provenance comparisons, not a re-run of frontend lowering.
// Checkpoints lack Clang invocation identity and cannot attest that the
// supplied source digest was authenticated by the caller.
const fn matches_position(
    saved: SourcePosition,
    expected: FrontendPosition,
) -> bool {
    saved.byte() == expected.byte()
        && saved.line() == expected.line()
        && saved.column() == expected.column()
}

const fn matches_span(saved: SourceSpan, expected: FrontendSpan) -> bool {
    matches_position(saved.begin(), expected.begin())
        && matches_position(saved.end(), expected.end())
}

// The current frontend-lowering slice admits only a no-argument `i32`
// return. Resolve the signature through the independently validated type
// table rather than trusting that a matching name/span implies the ABI.
fn matches_expected_function_signature(
    saved: &Module,
    function: &Function,
    source: &FrontendReturnIntegerFunction,
) -> bool {
    if admit_frontend_function(source).is_err() {
        return false;
    }
    let function_type = saved.types().iter().find(|entry| {
        entry.id() == function.signature()
    });
    let Some(TypeDef::Function {
        parameters,
        result: Some(result),
        variadic: false,
    }) = function_type.map(TypeEntry::definition) else {
        return false;
    };
    parameters.is_empty() && saved.types().iter().any(|entry| {
        entry.id() == *result && matches!(entry.definition(), TypeDef::I32)
    })
}

// Match the exact current single-constant-return frontend slice without
// rebuilding typed IR. The independently admitted checkpoint must retain
// source spans, constant bits, and the constant's returned SSA identity.
fn matches_expected_inner_slice(
    function: &Function,
    source: &FrontendReturnIntegerFunction,
) -> bool {
    let [block] = function.blocks() else {
        return false;
    };
    let [instruction] = block.instructions() else {
        return false;
    };
    let Instruction::ConstantInteger { constant, result, .. } =
        instruction.instruction()
    else {
        return false;
    };
    let Terminator::Return { value: Some(return_value) } = block.terminator()
    else {
        return false;
    };
    let Ok(expected_bits) = source.constant_decimal().parse::<i32>() else {
        return false;
    };
    block.id() == function.entry()
        && block.phis().is_empty()
        && constant.bit_width() == 32
        && constant.little_endian() == expected_bits.to_le_bytes()
        && result == return_value
        && matches_span(block.span(), source.body_span())
        && matches_span(block.terminator_span(), source.return_span())
        && matches_span(instruction.span(), source.value_span())
}

fn matches_expected_frontend(
    saved: &Module,
    expected: &FrontendArtifact,
) -> bool {
    validate_identity(expected).is_ok()
        && !expected.functions().is_empty()
        && saved.globals().is_empty()
        && saved.proof_obligations().is_empty()
        && saved.abi_id() == expected.abi_id()
        && saved.source_id() == expected.source_id()
        && saved.source_sha256() == expected.source_sha256()
        && saved.target_profile() == expected.target_profile()
        && saved.functions().len() == expected.functions().len()
        && saved.functions().iter().zip(expected.functions()).all(
            |(function, source)| {
                function.name() == source.name()
                    && matches_span(function.span(), source.function_span())
                    && matches_expected_function_signature(
                        saved, function, source,
                    )
                    && matches_expected_inner_slice(function, source)
            },
        )
}

/// Restores a typed checkpoint only for the caller's expected frontend source.
///
/// This checks module provenance, admitted return ABI, frontend identity,
/// and exact constant-return instruction bytes and source maps of the current
/// fresh-lowering slice, without rebuilding the IR module.
/// It does not authenticate the source digest or replace toolchain/revision
/// compatibility policy.
///
/// # Errors
///
/// Preserves inspector and typed-stage errors, or reports `IdentityMismatch`
/// when the restored module differs from the caller's source metadata.
pub fn resume_typed_ir_from_progress_for_source(
    interpreter: &Path,
    inspector: &Path,
    progress: &Path,
    expected: &FrontendArtifact,
) -> Result<Module, ProgressCheckpointError> {
    let module =
        resume_typed_ir_from_progress(interpreter, inspector, progress)?;
    if !matches_expected_frontend(&module, expected) {
        return Err(ProgressCheckpointError::IdentityMismatch);
    }
    Ok(module)
}

/// Enters typed IR from either fresh frontend evidence or durable progress.
///
/// # Errors
///
/// Preserves whether fresh lowering or durable progress resume failed.
pub fn enter_typed_ir_compiler_stage(
    input: TypedIrCompilerStageInput<'_>,
) -> Result<Module, TypedIrCompilerStageError> {
    match input {
        TypedIrCompilerStageInput::Fresh(frontend) => {
            enter_typed_ir_stage(TypedIrStageInput::Frontend(frontend))
                .map_err(TypedIrCompilerStageError::Fresh)
        },
        TypedIrCompilerStageInput::Progress {
            inspector,
            interpreter,
            progress,
        } => resume_typed_ir_from_progress(interpreter, inspector, progress)
            .map_err(TypedIrCompilerStageError::Progress),
        TypedIrCompilerStageInput::ProgressForSource {
            expected,
            inspector,
            interpreter,
            progress,
        } => resume_typed_ir_from_progress_for_source(
            interpreter, inspector, progress, expected,
        )
        .map_err(TypedIrCompilerStageError::Progress),
    }
}
