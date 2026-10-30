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
//   - Exact admitted typed-IR-to-ternary byte-I/O projections for one void
//     function, with canonical wire and verified graphical output.
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
//   - Call the strict echo or opt-in latest-read trace compiler with MCTI bytes.
// - Defaults:
//   - Unsupported typed operations and profiles reject before emission.
//
//! Narrow typed-IR-to-Malbolge bridge for successful-byte I/O traces.
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

#[derive(Clone, Copy)]
enum ByteTraceMode {
    AdjacentEcho,
    LatestRead,
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

fn project_latest_effects(
    module: &Module,
    original: &[typed::LocatedInstruction],
) -> Result<Vec<InputInstruction>, TypedEchoAdapterError> {
    if original.is_empty() || original.len() >= 4096 {
        return Err(TypedEchoAdapterError::UnsupportedTypedIr);
    }
    let mut last_input = None;
    let mut instructions = Vec::with_capacity(original.len());
    for located in original {
        if let Instruction::ByteInput { result, type_id } = located.instruction() {
            if !is_byte_type(module, *type_id) {
                return Err(TypedEchoAdapterError::UnsupportedTypedIr);
            }
            last_input = Some(*result);
            instructions.push(InputInstruction::ByteInput {
                result: result.value(),
                span: project_span(located.span()),
                type_kind: InputScalarType::U8,
            });
        } else if let Instruction::ByteOutput { value } = located.instruction() {
            if last_input != Some(*value) {
                return Err(TypedEchoAdapterError::UnsupportedTypedIr);
            }
            instructions.push(InputInstruction::ByteOutput {
                span: project_span(located.span()),
                value: value.value(),
            });
        } else {
            return Err(TypedEchoAdapterError::UnsupportedTypedIr);
        }
    }
    if last_input.is_none() {
        return Err(TypedEchoAdapterError::UnsupportedTypedIr);
    }
    Ok(instructions)
}

fn project_byte_trace(
    module: &Module,
    mode: ByteTraceMode,
) -> Result<TypedIrInput, TypedEchoAdapterError> {
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
    let instructions = match mode {
        ByteTraceMode::AdjacentEcho => project_effects(module, block.instructions())?,
        ByteTraceMode::LatestRead => project_latest_effects(module, block.instructions())?,
    };
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

// Both opt-in modes consume the exact canonical typed module, preserve every
// admitted source/SSA identity, and independently re-admit MCTR and layout.
// The private composition never falls back to host I/O execution.
fn compile_byte_trace(
    canonical: &[u8],
    profile: &'static ProfileDescriptor,
    mode: ByteTraceMode,
) -> Result<CompiledTypedEcho, TypedEchoAdapterError> {
    let module = canonical_module(canonical).map_err(TypedEchoAdapterError::InvalidTypedIr)?;
    // A canonical source-target identity is admission evidence, not a hint.
    // Refuse profile drift before allocating/lowering an entire effect trace.
    if module.target_profile() != profile.id() {
        return Err(TypedEchoAdapterError::Layout(
            bridge::ByteEchoBridgeError::ProfileMismatch,
        ));
    }
    let projection = project_byte_trace(&module, mode)?;
    let lowered = lower_typed_ir(&projection).map_err(TypedEchoAdapterError::Lowering)?;
    let ternary_bytes =
        canonical_ternary_bytes(&lowered).map_err(TypedEchoAdapterError::InvalidTernary)?;
    let independently_admitted =
        canonical_ternary_program(&ternary_bytes).map_err(TypedEchoAdapterError::InvalidTernary)?;
    if independently_admitted != lowered {
        return Err(TypedEchoAdapterError::UnsupportedTypedIr);
    }
    let layout = match mode {
        ByteTraceMode::AdjacentEcho => {
            bridge::encode_successful_byte_echo(&independently_admitted, profile)
        }
        ByteTraceMode::LatestRead => {
            bridge::encode_successful_latest_byte_trace(&independently_admitted, profile)
        }
    }
    .map_err(TypedEchoAdapterError::Layout)?;
    Ok(CompiledTypedEcho {
        layout,
        ternary_bytes,
    })
}

/// Lowers the **original** strict canonical typed-IR echo sublanguage.
///
/// Every input must be immediately followed by one output of that exact
/// result. This entrypoint is intentionally unaffected by the broader
/// latest-read byte-I/O trace mode.
///
/// # Errors
///
/// Rejects unsupported typed source, profile drift, malformed canonical IR
/// and independently unadmitted Malbolge layout.
pub fn compile_canonical_typed_echo(
    canonical: &[u8],
    profile: &'static ProfileDescriptor,
) -> Result<CompiledTypedEcho, TypedEchoAdapterError> {
    compile_byte_trace(canonical, profile, ByteTraceMode::AdjacentEcho)
}

/// Lowers an admitted canonical typed-IR **latest successful byte** trace.
///
/// Each output must refer to the most recent successful input's SSA byte.
/// Multiple outputs of that value and unused intervening input values are
/// supported, but outputting an older result after another input is forbidden
/// without guest memory. The caller must guarantee all reads/writes succeed;
/// EOF, ABI returns, heap storage and arbitrary typed computations are absent.
///
/// # Errors
///
/// Rejects unsupported module, function, instruction, or SSA flow; invalid
/// canonical source, profile drift or address-sensitive target-layout failure.
pub fn compile_canonical_typed_latest_byte_trace(
    canonical: &[u8],
    profile: &'static ProfileDescriptor,
) -> Result<CompiledTypedEcho, TypedEchoAdapterError> {
    compile_byte_trace(canonical, profile, ByteTraceMode::LatestRead)
}
