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
//   - Complete fail-closed admission ordering for portable typed compiler IR
//     v1.
// - Must-Not:
//   - Repair malformed IR, parse C, discharge proofs, or lower target code.
// - Allows:
//   - Inputs: one constructed typed-IR module.
//   - Outputs: validated success or one stable version-one rejection category.
//   - Side effects: temporary ordered symbol/value maps only.
// - Split-When:
//   - Another IR version requires independently ordered admission semantics.
// - Merge-When:
//   - One lower-level validator owns the complete module lifecycle.
// - Summary:
//   - Orders profile, type, symbol, SSA, CFG, semantic, and proof admission.
// - Description:
//   - No canonical serialization is trusted before this function succeeds.
// - Usage:
//   - Public typed-IR admission entrypoint for tests and future compiler
//     stages.
// - Defaults:
//   - Validation returns the first deterministic failure category.
//

//! Complete fail-closed admission for typed compiler IR version one.

use std::collections::{BTreeMap, BTreeSet};

use super::cfg::analyze_cfg;
use super::control::Phi;
use super::error::ValidationError;
use super::instruction::LocatedInstruction;
use super::instructions::validate_function_semantics;
use super::layout::{object_layout, validate_object_layouts};
use super::module::{Function, Global, Module, TYPED_IR_VERSION};
use super::proofs::validate_proofs;
use super::source::{SourcePosition, SourceSpan};
use super::type_validation::{is_object_type, validate_type_table};
use super::values::{ValueTable, collect_values};

const ABI_ID: &str = "malbolge-c32-v1";
const TARGET_PROFILE: &str = "malbolge-2026";

/// Validates one complete portable typed compiler IR module.
///
/// # Errors
///
/// Returns the first stable [`ValidationError`] category for malformed or
/// unsupported version-one semantics.
pub fn validate_module(module: &Module) -> Result<(), ValidationError> {
    validate_profile(module)?;
    validate_type_table(module.types())?;
    validate_object_layouts(module.types())?;
    let symbols = validate_globals(module)?;
    let mut value_tables = BTreeMap::new();
    let mut function_symbols = symbols;
    for (index, function) in module.functions().iter().enumerate() {
        validate_function_identity(function, index, &mut function_symbols)?;
        let values = collect_values(function)?;
        validate_value_types(module, &values)?;
        let flow = analyze_cfg(function, &values)?;
        validate_function_semantics(module, function, &values, &flow)?;
        let _previous = value_tables.insert(function.id(), values);
    }
    validate_proofs(module, &value_tables)
}

fn valid_name(name: &str) -> bool {
    !name.is_empty() && !name.contains('\0')
}

const fn valid_position(position: SourcePosition) -> bool {
    position.line() != 0 && position.column() != 0
}

fn valid_source_id(source_id: &str) -> bool {
    !source_id.is_empty()
        && !source_id.starts_with('/')
        && !source_id.contains(char::from(92))
        && !source_id.contains(':')
        && !source_id.contains(char::from(0))
        && !source_id
            .split('/')
            .any(|part| part.is_empty() || part == "." || part == "..")
}

const fn valid_span(span: SourceSpan) -> bool {
    let begin = span.begin();
    let end = span.end();
    if !valid_position(begin)
        || !valid_position(end)
        || begin.byte() > end.byte()
    {
        return false;
    }
    if begin.byte() == end.byte() {
        return begin.line() == end.line() && begin.column() == end.column();
    }
    begin.line() < end.line()
        || (begin.line() == end.line() && begin.column() <= end.column())
}

const fn span_contains(parent: SourceSpan, child: SourceSpan) -> bool {
    parent.begin().byte() <= child.begin().byte()
        && child.end().byte() <= parent.end().byte()
}

fn validate_function_identity(
    function: &Function,
    index: usize,
    symbols: &mut BTreeSet<String>,
) -> Result<(), ValidationError> {
    let expected = u32::try_from(index)
        .map_err(|_error| ValidationError::FunctionIdentity)?;
    if function.id().value() != expected
        || !valid_name(function.name())
        || !symbols.insert(String::from(function.name()))
        || !valid_span(function.span())
    {
        return Err(ValidationError::FunctionIdentity);
    }
    validate_function_spans(function)
}

fn validate_function_spans(function: &Function) -> Result<(), ValidationError> {
    for block in function.blocks() {
        if !valid_span(block.span())
            || !span_contains(function.span(), block.span())
        {
            return Err(ValidationError::SourceProvenance);
        }
        if !valid_span(block.terminator_span())
            || !span_contains(block.span(), block.terminator_span())
        {
            return Err(ValidationError::SourceProvenance);
        }
        for phi in block.phis() {
            validate_phi_span(block.span(), phi)?;
        }
        for instruction in block.instructions() {
            validate_instruction_span(block.span(), instruction)?;
        }
    }
    Ok(())
}

fn validate_globals(
    module: &Module,
) -> Result<BTreeSet<String>, ValidationError> {
    let mut symbols = BTreeSet::new();
    for (index, global) in module.globals().iter().enumerate() {
        validate_global(module, global, index, &mut symbols)?;
    }
    Ok(symbols)
}

fn validate_global(
    module: &Module,
    global: &Global,
    index: usize,
    symbols: &mut BTreeSet<String>,
) -> Result<(), ValidationError> {
    let expected = u32::try_from(index)
        .map_err(|_error| ValidationError::GlobalIdentity)?;
    if global.id().value() != expected
        || !valid_name(global.name())
        || !symbols.insert(String::from(global.name()))
        || !valid_span(global.span())
        || !is_object_type(module.types(), global.type_id())
    {
        return Err(ValidationError::GlobalIdentity);
    }
    if let Some(initializer) = global.initializer() {
        let layout = object_layout(module.types(), global.type_id())?;
        let expected_size = usize::try_from(layout.size)
            .map_err(|_error| ValidationError::GlobalIdentity)?;
        if initializer.len() != expected_size {
            return Err(ValidationError::GlobalIdentity);
        }
    }
    Ok(())
}

const fn validate_instruction_span(
    block_span: SourceSpan,
    instruction: &LocatedInstruction,
) -> Result<(), ValidationError> {
    if !valid_span(instruction.span())
        || !span_contains(block_span, instruction.span())
    {
        return Err(ValidationError::SourceProvenance);
    }
    Ok(())
}

const fn validate_phi_span(
    block_span: SourceSpan,
    phi: &Phi,
) -> Result<(), ValidationError> {
    if !valid_span(phi.span()) || !span_contains(block_span, phi.span()) {
        return Err(ValidationError::SourceProvenance);
    }
    Ok(())
}

fn validate_profile(module: &Module) -> Result<(), ValidationError> {
    if module.format_version() != TYPED_IR_VERSION
        || module.abi_id() != ABI_ID
        || module.target_profile() != TARGET_PROFILE
    {
        return Err(ValidationError::ProfileIdentity);
    }
    if !valid_source_id(module.source_id()) {
        return Err(ValidationError::SourceProvenance);
    }
    Ok(())
}

fn validate_value_types(
    module: &Module,
    values: &ValueTable,
) -> Result<(), ValidationError> {
    for info in values.values() {
        if !is_object_type(module.types(), info.type_id) {
            return Err(ValidationError::OperandType);
        }
    }
    Ok(())
}
