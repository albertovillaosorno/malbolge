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
//   - Deterministic normalized-frontend semantic lowering into typed IR.
// - Must-Not:
//   - Parse frontend JSON, invent unsupported C semantics, or bypass IR
//     admission.
// - Allows:
//   - Inputs: typed normalized frontend projections admitted by the inbound
//     port.
//   - Outputs: fully validated portable typed-IR modules or stable failures.
//   - Side effects: returned compiler-value allocation only.
// - Split-When:
//   - Another frontend semantic family needs independently reviewed lowering.
// - Merge-When:
//   - Frontend adaptation and typed-IR admission become one boundary.
// - Summary:
//   - Lowers supported normalized C semantics without host/native inference.
// - Description:
//   - The initial slice supports defined no-argument i32 constant-return
//     functions.
// - Usage:
//   - Called after serialized frontend artifacts are projected into the inbound
//     port.
// - Defaults:
//   - Unsupported normalized semantics fail closed before publishing IR.
//

//! Deterministic normalized-C semantic lowering into portable typed compiler
//! IR.

use super::control::{BasicBlock, BasicBlockSpec, Terminator};
use super::error::ValidationError;
use super::frontend_semantics::{
    FrontendArtifact, FrontendPosition, FrontendReturnIntegerFunction,
    FrontendSpan,
};
use super::ids::{BlockId, FunctionId, TypeId, ValueId};
use super::instruction::{Instruction, IntegerConstant, LocatedInstruction};
use super::module::{
    Function, FunctionSpec, Module, ModuleSpec, TYPED_IR_VERSION,
};
use super::source::{SourcePosition, SourceSpan};
use super::types::{TypeDef, TypeEntry};
use super::validate::validate_module;

const ABI_ID: &str = "malbolge-c32-v1";
const FRONTEND_ARTIFACT_ID: &str = "malbolge-c-frontend-v1";
const FRONTEND_CLANG_TARGET: &str = "wasm32-unknown-unknown";
const FRONTEND_CLANG_VERSION: &str = "22.1.8";
const FRONTEND_LANGUAGE: &str = "c23";
const FRONTEND_SCHEMA_VERSION: u16 = 1;
const I32_TYPE: TypeId = TypeId::new(0);
const I32_FUNCTION_TYPE: TypeId = TypeId::new(1);
const I32_FUNCTION_SIGNATURE: &str = "fn()->i32";
const I32_FRONTEND_TYPE: &str = "i32";
const REQUIRED_DEFINITION: &str = "definition";
const REQUIRED_LINKAGE: &str = "external";
const REQUIRED_STORAGE_CLASS: &str = "none";
const TARGET_PROFILE: &str = "malbolge-2026";

/// Stable failure categories for normalized frontend semantic lowering.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum FrontendLoweringError {
    /// Frontend artifact identity does not match the reviewed version-one
    /// boundary.
    Identity,
    /// An integer constant is outside the supported normalized i32 domain.
    IntegerConstant,
    /// The normalized semantic shape is not yet supported by this lowering
    /// slice.
    UnsupportedSemantics,
    /// The constructed typed IR failed its own complete admission boundary.
    Validation(ValidationError),
}

impl From<ValidationError> for FrontendLoweringError {
    fn from(error: ValidationError) -> Self {
        Self::Validation(error)
    }
}

/// Lowers one supported normalized frontend projection into validated typed IR.
///
/// # Errors
///
/// Returns a stable [`FrontendLoweringError`] when artifact identity, supported
/// semantics, integer representation, or complete typed-IR admission fails.
pub fn lower_frontend_artifact(
    artifact: &FrontendArtifact,
) -> Result<Module, FrontendLoweringError> {
    validate_identity(artifact)?;
    if artifact.functions().is_empty() {
        return Err(FrontendLoweringError::UnsupportedSemantics);
    }
    let mut functions = Vec::with_capacity(artifact.functions().len());
    for (index, function) in artifact.functions().iter().enumerate() {
        functions.push(lower_function(index, function)?);
    }
    let module = Module::new(ModuleSpec {
        abi_id: String::from(ABI_ID),
        format_version: TYPED_IR_VERSION,
        functions,
        globals: Vec::new(),
        proof_obligations: Vec::new(),
        source_id: String::from(artifact.source_id()),
        source_sha256: *artifact.source_sha256(),
        target_profile: String::from(TARGET_PROFILE),
        types: lowered_types(),
    });
    validate_module(&module)?;
    Ok(module)
}

const fn convert_position(position: FrontendPosition) -> SourcePosition {
    SourcePosition::new(position.byte(), position.line(), position.column())
}

const fn convert_span(span: FrontendSpan) -> SourceSpan {
    SourceSpan::new(
        convert_position(span.begin()),
        convert_position(span.end()),
    )
}

fn lower_function(
    index: usize,
    function: &FrontendReturnIntegerFunction,
) -> Result<Function, FrontendLoweringError> {
    if function.definition() != REQUIRED_DEFINITION
        || function.inline_specified()
        || function.linkage() != REQUIRED_LINKAGE
        || function.signature() != I32_FUNCTION_SIGNATURE
        || function.storage_class() != REQUIRED_STORAGE_CLASS
        || function.value_type() != I32_FRONTEND_TYPE
    {
        return Err(FrontendLoweringError::UnsupportedSemantics);
    }
    let function_id = u32::try_from(index)
        .map(FunctionId::new)
        .map_err(|_error| FrontendLoweringError::UnsupportedSemantics)?;
    let value = function
        .constant_decimal()
        .parse::<i32>()
        .map_err(|_error| FrontendLoweringError::IntegerConstant)?;
    let instruction = LocatedInstruction::new(
        Instruction::ConstantInteger {
            constant: IntegerConstant::new(32, Vec::from(value.to_le_bytes())),
            result: ValueId::new(0),
            type_id: I32_TYPE,
        },
        convert_span(function.value_span()),
    );
    let block = BasicBlock::new(BasicBlockSpec {
        id: BlockId::new(0),
        instructions: vec![instruction],
        phis: Vec::new(),
        span: convert_span(function.body_span()),
        terminator: Terminator::Return {
            value: Some(ValueId::new(0)),
        },
        terminator_span: convert_span(function.return_span()),
    });
    Ok(Function::new(FunctionSpec {
        blocks: vec![block],
        entry: BlockId::new(0),
        id: function_id,
        name: String::from(function.name()),
        parameters: Vec::new(),
        signature: I32_FUNCTION_TYPE,
        span: convert_span(function.function_span()),
    }))
}

fn lowered_types() -> Vec<TypeEntry> {
    vec![
        TypeEntry::new(I32_TYPE, TypeDef::I32),
        TypeEntry::new(
            I32_FUNCTION_TYPE,
            TypeDef::function(Vec::new(), Some(I32_TYPE), false),
        ),
    ]
}

fn validate_identity(
    artifact: &FrontendArtifact,
) -> Result<(), FrontendLoweringError> {
    if artifact.abi_id() != ABI_ID
        || artifact.artifact_id() != FRONTEND_ARTIFACT_ID
        || artifact.clang_target() != FRONTEND_CLANG_TARGET
        || artifact.clang_version() != FRONTEND_CLANG_VERSION
        || artifact.language() != FRONTEND_LANGUAGE
        || artifact.schema_version() != FRONTEND_SCHEMA_VERSION
        || artifact.target_profile() != TARGET_PROFILE
    {
        return Err(FrontendLoweringError::Identity);
    }
    Ok(())
}
