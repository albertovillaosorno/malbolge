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
//   - Complete admitted typed-IR-to-ternary projection for one successful-byte
//     echo function, with canonical wire and verified graphical output.
// - Must-Not:
//   - Impersonate a C compiler, EOF/error semantics, or a full guest ABI.
// - Allows:
//   - Inputs: canonical typed-IR bytes and explicit target-profile descriptor.
//   - Outputs: canonical ternary bytes and independently admitted Malbolge code.
//   - Side effects: none.
// - Split-When:
//   - General typed-IR conversion needs a wider typed-IR semantics adapter.
// - Merge-When:
//   - A complete typed-IR-to-ternary compiler owns this exact admitted slice.
// - Summary:
//   - Closes the real typed-IR byte-I/O gap without caller-fabricated projection.
// - Description:
//   - Revalidates canonical typed IR and retains function/SSA/source provenance.
// - Usage:
//   - Call compile_canonical_typed_echo with complete canonical typed-IR bytes.
// - Defaults:
//   - Unsupported typed operations and profiles reject before emission.
//
//! Narrow typed-IR-to-Malbolge bridge for exact successful-byte echo functions.
//!
//! Unlike an external caller-provided projection, every effect originates from
//! the independently validated canonical typed-IR module. The result is only
//! equivalent when all guest reads and writes succeed, with void ABI ignored.

#[path = "../../byte-echo-bridge/composition/lib.rs"]
pub mod bridge;
#[path = "../../typed-ir/composition/lib.rs"]
pub mod typed;

use malbolge::ProfileDescriptor;

use bridge::layout::LinearLayout;
use bridge::ternary::{
    InputBlock, InputFunction, InputInstruction, InputScalarType, InputSourcePosition,
    InputSourceSpan, InputTerminator, TernaryLoweringError, TernaryProgramCodecError, TypedIrInput,
    canonical_ternary_bytes, canonical_ternary_program, lower_typed_ir,
};
use typed::{
    CanonicalDecodeError, Instruction, Module, SourcePosition, SourceSpan, Terminator, TypeDef,
    TypeId, canonical_module,
};

/// A refused canonical typed-IR read, typed subset, ternary state or layout.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum TypedEchoAdapterError {
    /// The produced canonical ternary bytes failed admission.
    InvalidTernary(TernaryProgramCodecError),
    /// The canonical typed-IR decoder independently rejected the input.
    InvalidTypedIr(CanonicalDecodeError),
    /// The verified ternary trace cannot be emitted to executable source.
    Layout(bridge::ByteEchoBridgeError),
    /// Fresh projection was rejected by the canonical ternary lowerer.
    Lowering(TernaryLoweringError),
    /// The complete typed module is outside the supported successful-byte trace.
    UnsupportedTypedIr,
}

/// Both stage identities produced by the accepted typed byte-I/O trace.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct CompiledTypedEcho {
    layout: LinearLayout,
    ternary_bytes: Vec<u8>,
}

impl CompiledTypedEcho {
    /// Returns the independently admitted position-sensitive source.
    #[must_use]
    pub const fn layout(&self) -> &LinearLayout {
        &self.layout
    }

    /// Returns canonical, independently decodable `MCTR` version-one bytes.
    #[must_use]
    pub fn ternary_bytes(&self) -> &[u8] {
        &self.ternary_bytes
    }
}

const fn project_position(position: SourcePosition) -> InputSourcePosition {
    InputSourcePosition {
        byte: position.byte(),
        column: position.column(),
        line: position.line(),
    }
}

const fn project_span(span: SourceSpan) -> InputSourceSpan {
    InputSourceSpan {
        begin: project_position(span.begin()),
        end: project_position(span.end()),
    }
}

fn is_byte_type(module: &Module, id: TypeId) -> bool {
    module
        .types()
        .iter()
        .any(|entry| entry.id() == id && *entry.definition() == TypeDef::U8)
}

fn project_effects(
    module: &Module,
    original: &[typed::LocatedInstruction],
) -> Result<Vec<InputInstruction>, TypedEchoAdapterError> {
    let (pairs, remainder) = original.as_chunks::<2>();
    if pairs.is_empty() || pairs.len() > 2047 || !remainder.is_empty() {
        return Err(TypedEchoAdapterError::UnsupportedTypedIr);
    }
    let mut instructions = Vec::with_capacity(original.len());
    for [read, write] in pairs {
        let (Instruction::ByteInput { result, type_id }, Instruction::ByteOutput { value }) =
            (read.instruction(), write.instruction())
        else {
            return Err(TypedEchoAdapterError::UnsupportedTypedIr);
        };
        if !is_byte_type(module, *type_id) || result != value {
            return Err(TypedEchoAdapterError::UnsupportedTypedIr);
        }
        instructions.push(InputInstruction::ByteInput {
            result: result.value(),
            span: project_span(read.span()),
            type_kind: InputScalarType::U8,
        });
        instructions.push(InputInstruction::ByteOutput {
            span: project_span(write.span()),
            value: value.value(),
        });
    }
    Ok(instructions)
}

fn project_echo(module: &Module) -> Result<TypedIrInput, TypedEchoAdapterError> {
    let [function] = module.functions() else {
        return Err(TypedEchoAdapterError::UnsupportedTypedIr);
    };
    let [block] = function.blocks() else {
        return Err(TypedEchoAdapterError::UnsupportedTypedIr);
    };
    let has_void_signature = module.types().iter().any(|entry| {
        entry.id() == function.signature()
            && matches!(entry.definition(), TypeDef::Function {
                parameters, result: None, variadic: false
            } if parameters.is_empty())
    });
    if !module.globals().is_empty()
        || !module.proof_obligations().is_empty()
        || !has_void_signature
        || !function.parameters().is_empty()
        || function.entry() != block.id()
        || !block.phis().is_empty()
        || !matches!(block.terminator(), Terminator::Return { value: None })
    {
        return Err(TypedEchoAdapterError::UnsupportedTypedIr);
    }
    let instructions = project_effects(module, block.instructions())?;
    Ok(TypedIrInput {
        abi_id: module.abi_id().to_owned(),
        functions: vec![InputFunction {
            blocks: vec![InputBlock {
                id: block.id().value(),
                instructions,
                phi_count: 0,
                terminator: InputTerminator::Return {
                    span: project_span(block.terminator_span()),
                    value: None,
                },
            }],
            entry: function.entry().value(),
            id: function.id().value(),
            name: function.name().to_owned(),
            parameter_count: 0,
            return_kind: InputScalarType::Void,
            span: project_span(function.span()),
        }],
        global_count: 0,
        input_format_version: module.format_version(),
        proof_obligation_count: 0,
        source_id: module.source_id().to_owned(),
        source_sha256: *module.source_sha256(),
        target_profile: module.target_profile().to_owned(),
    })
}

/// Converts a canonical typed-IR byte stream to a fully checked direct source.
///
/// The input must be a single, zero-argument void function containing one block
/// of adjacent `ByteInput`/`ByteOutput` pairs. The exact `u8` result SSA and
/// source positions are copied from the decoded typed program, not a caller's
/// separately fabricated projection. No guest I/O is performed on the host.
///
/// # Errors
///
/// Rejects malformed canonical input, unsupported guest effects or signatures,
/// ternary projection drift, selected profile drift and unsafe graphical layout.
pub fn compile_canonical_typed_echo(
    canonical: &[u8],
    profile: &'static ProfileDescriptor,
) -> Result<CompiledTypedEcho, TypedEchoAdapterError> {
    let module = canonical_module(canonical).map_err(TypedEchoAdapterError::InvalidTypedIr)?;
    let projection = project_echo(&module)?;
    let lowered = lower_typed_ir(&projection).map_err(TypedEchoAdapterError::Lowering)?;
    let ternary_bytes =
        canonical_ternary_bytes(&lowered).map_err(TypedEchoAdapterError::InvalidTernary)?;
    let independently_admitted =
        canonical_ternary_program(&ternary_bytes).map_err(TypedEchoAdapterError::InvalidTernary)?;
    if independently_admitted != lowered {
        return Err(TypedEchoAdapterError::UnsupportedTypedIr);
    }
    let layout = bridge::encode_successful_byte_echo(&independently_admitted, profile)
        .map_err(TypedEchoAdapterError::Layout)?;
    Ok(CompiledTypedEcho {
        layout,
        ternary_bytes,
    })
}
