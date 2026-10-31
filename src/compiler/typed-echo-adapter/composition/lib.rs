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
use std::collections::BTreeSet;

use bridge::layout::LinearLayout;
use bridge::ternary::{
    InputBlock, InputFunction, InputInstruction, InputScalarType, InputSourcePosition,
    InputSourceSpan, InputTerminator, TernaryLoweringError, TernaryProgramCodecError, TypedIrInput,
    canonical_ternary_bytes, canonical_ternary_program, lower_typed_ir,
};
use typed::{
    CanonicalDecodeError, CastOp, Instruction, Module, SourcePosition, SourceSpan, Terminator,
    TypeDef, TypeId, canonical_module,
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
    IdentityByteBitcast,
    InitialZero,
    LatestRead,
    RotatedLiteral,
    ZeroPrefixedLatest,
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

// An exact source u8 zero needs no materialization instruction: the normative
// guest VM starts with accumulator A=0. This shape never consumes guest input.
fn project_initial_zero_effects(
    module: &Module,
    original: &[typed::LocatedInstruction],
) -> Result<Vec<InputInstruction>, TypedEchoAdapterError> {
    let Some((first, outputs)) = original.split_first() else {
        return Err(TypedEchoAdapterError::UnsupportedTypedIr);
    };
    let Instruction::ConstantInteger {
        constant,
        result,
        type_id,
    } = first.instruction()
    else {
        return Err(TypedEchoAdapterError::UnsupportedTypedIr);
    };
    if !is_byte_type(module, *type_id)
        || constant.bit_width() != 8
        || constant.little_endian() != [0]
        || outputs.is_empty()
        || outputs.len() > 4095
    {
        return Err(TypedEchoAdapterError::UnsupportedTypedIr);
    }
    let mut instructions = Vec::with_capacity(original.len());
    instructions.push(InputInstruction::ConstantInteger {
        bit_width: constant.bit_width(),
        little_endian: constant.little_endian().to_vec(),
        result: result.value(),
        span: project_span(first.span()),
        type_kind: InputScalarType::U8,
    });
    for output in outputs {
        let Instruction::ByteOutput { value } = output.instruction() else {
            return Err(TypedEchoAdapterError::UnsupportedTypedIr);
        };
        if value != result {
            return Err(TypedEchoAdapterError::UnsupportedTypedIr);
        }
        instructions.push(InputInstruction::ByteOutput {
            span: project_span(output.span()),
            value: value.value(),
        });
    }
    Ok(instructions)
}

// The guest computes one exact nonzero u8 with j then *, and can repeatedly
// emit the unchanged accumulator while the proven code/data layout is safe.
fn project_rotated_literal_effects(
    module: &Module,
    original: &[typed::LocatedInstruction],
) -> Result<Vec<InputInstruction>, TypedEchoAdapterError> {
    let Some((source, outputs)) = original.split_first() else {
        return Err(TypedEchoAdapterError::UnsupportedTypedIr);
    };
    let Instruction::ConstantInteger {
        constant,
        result,
        type_id,
    } = source.instruction()
    else {
        return Err(TypedEchoAdapterError::UnsupportedTypedIr);
    };
    if outputs.is_empty()
        || outputs.len() > 11
        || !is_byte_type(module, *type_id)
        || constant.bit_width() != 8
        || constant.little_endian().len() != 1
    {
        return Err(TypedEchoAdapterError::UnsupportedTypedIr);
    }
    let mut instructions = Vec::with_capacity(original.len());
    instructions.push(InputInstruction::ConstantInteger {
        bit_width: constant.bit_width(),
        little_endian: constant.little_endian().to_vec(),
        result: result.value(),
        span: project_span(source.span()),
        type_kind: InputScalarType::U8,
    });
    for output in outputs {
        let Instruction::ByteOutput { value } = output.instruction() else {
            return Err(TypedEchoAdapterError::UnsupportedTypedIr);
        };
        if value != result {
            return Err(TypedEchoAdapterError::UnsupportedTypedIr);
        }
        instructions.push(InputInstruction::ByteOutput {
            span: project_span(output.span()),
            value: value.value(),
        });
    }
    Ok(instructions)
}

// A source zero SSA can be emitted until the first input overwrites VM A.
// Thereafter only outputs naming the latest successful input are executable.
#[expect(
    clippy::too_many_lines,
    reason = "complete source-bound mixed constant and byte-input SSA admission"
)]
fn project_zero_prefixed_effects(
    module: &Module,
    original: &[typed::LocatedInstruction],
) -> Result<Vec<InputInstruction>, TypedEchoAdapterError> {
    let Some((first, effects)) = original.split_first() else {
        return Err(TypedEchoAdapterError::UnsupportedTypedIr);
    };
    let Instruction::ConstantInteger {
        constant,
        result: zero,
        type_id,
    } = first.instruction()
    else {
        return Err(TypedEchoAdapterError::UnsupportedTypedIr);
    };
    if !is_byte_type(module, *type_id)
        || constant.bit_width() != 8
        || constant.little_endian() != [0]
        || effects.len() >= 4096
    {
        return Err(TypedEchoAdapterError::UnsupportedTypedIr);
    }
    let mut instructions = Vec::with_capacity(original.len());
    instructions.push(InputInstruction::ConstantInteger {
        bit_width: constant.bit_width(),
        little_endian: constant.little_endian().to_vec(),
        result: zero.value(),
        span: project_span(first.span()),
        type_kind: InputScalarType::U8,
    });
    let mut latest = None;
    let mut initial_outputs = false;
    let mut subsequent_outputs = false;
    for located in effects {
        if let Instruction::ByteInput {
            result,
            type_id: input_type,
        } = located.instruction()
        {
            if !is_byte_type(module, *input_type) {
                return Err(TypedEchoAdapterError::UnsupportedTypedIr);
            }
            latest = Some(*result);
            instructions.push(InputInstruction::ByteInput {
                result: result.value(),
                span: project_span(located.span()),
                type_kind: InputScalarType::U8,
            });
        } else if let Instruction::ByteOutput { value } = located.instruction() {
            let valid = latest.map_or(value == zero, |last| *value == last);
            if !valid {
                return Err(TypedEchoAdapterError::UnsupportedTypedIr);
            }
            if latest.is_some() {
                subsequent_outputs = true;
            } else {
                initial_outputs = true;
            }
            instructions.push(InputInstruction::ByteOutput {
                span: project_span(located.span()),
                value: value.value(),
            });
        } else {
            return Err(TypedEchoAdapterError::UnsupportedTypedIr);
        }
    }
    if !initial_outputs || latest.is_none() || !subsequent_outputs {
        return Err(TypedEchoAdapterError::UnsupportedTypedIr);
    }
    Ok(instructions)
}

// A u8/i8 representation bitcast is a new SSA name for the same eight bits.
// Once another input overwrites A, no old alias is realizable without memory.
fn project_identity_bitcast_effects(
    module: &Module,
    original: &[typed::LocatedInstruction],
) -> Result<Vec<InputInstruction>, TypedEchoAdapterError> {
    if original.is_empty() || original.len() > 4096 {
        return Err(TypedEchoAdapterError::UnsupportedTypedIr);
    }
    let mut aliases = BTreeSet::new();
    let mut seen_cast = false;
    let mut seen_output = false;
    let mut instructions = Vec::with_capacity(original.len());
    for located in original {
        if let Instruction::ByteInput { result, type_id } = located.instruction() {
            if !is_byte_type(module, *type_id) {
                return Err(TypedEchoAdapterError::UnsupportedTypedIr);
            }
            aliases.clear();
            _ = aliases.insert(*result);
            instructions.push(InputInstruction::ByteInput {
                result: result.value(),
                span: project_span(located.span()),
                type_kind: InputScalarType::U8,
            });
        } else if let Instruction::ByteOutput { value } = located.instruction() {
            if !aliases.contains(value) {
                return Err(TypedEchoAdapterError::UnsupportedTypedIr);
            }
            seen_output = true;
            instructions.push(InputInstruction::ByteOutput {
                span: project_span(located.span()),
                value: value.value(),
            });
        } else if let Instruction::Cast {
            operation: CastOp::IntegerBitcast,
            result,
            type_id,
            value,
        } = located.instruction()
        {
            if !aliases.contains(value) {
                return Err(TypedEchoAdapterError::UnsupportedTypedIr);
            }
            let kind = byte_bitcast_kind(module, *type_id)?;
            _ = aliases.insert(*result);
            seen_cast = true;
            instructions.push(InputInstruction::IntegerBitcast {
                result: result.value(),
                span: project_span(located.span()),
                type_kind: kind,
                value: value.value(),
            });
        } else {
            return Err(TypedEchoAdapterError::UnsupportedTypedIr);
        }
    }
    if aliases.is_empty() || !seen_cast || !seen_output {
        return Err(TypedEchoAdapterError::UnsupportedTypedIr);
    }
    Ok(instructions)
}

fn byte_bitcast_kind(
    module: &Module,
    id: TypeId,
) -> Result<InputScalarType, TypedEchoAdapterError> {
    for entry in module.types() {
        if entry.id() == id {
            return if entry.definition() == &TypeDef::I8 {
                Ok(InputScalarType::I8)
            } else if entry.definition() == &TypeDef::U8 {
                Ok(InputScalarType::U8)
            } else {
                Err(TypedEchoAdapterError::UnsupportedTypedIr)
            };
        }
    }
    Err(TypedEchoAdapterError::UnsupportedTypedIr)
}

#[expect(
    clippy::too_many_lines,
    reason = "complete canonical typed bridge admission"
)]
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
        ByteTraceMode::InitialZero => project_initial_zero_effects(module, block.instructions())?,
        ByteTraceMode::LatestRead => project_latest_effects(module, block.instructions())?,
        ByteTraceMode::ZeroPrefixedLatest => {
            project_zero_prefixed_effects(module, block.instructions())?
        }
        ByteTraceMode::IdentityByteBitcast => {
            project_identity_bitcast_effects(module, block.instructions())?
        }
        ByteTraceMode::RotatedLiteral => {
            project_rotated_literal_effects(module, block.instructions())?
        }
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
        ByteTraceMode::InitialZero => {
            bridge::encode_initial_zero_outputs(&independently_admitted, profile)
        }
        ByteTraceMode::LatestRead => {
            bridge::encode_successful_latest_byte_trace(&independently_admitted, profile)
        }
        ByteTraceMode::ZeroPrefixedLatest => {
            bridge::encode_zero_prefixed_latest_byte_trace(&independently_admitted, profile)
        }
        ByteTraceMode::IdentityByteBitcast => {
            bridge::encode_latest_byte_identity_trace(&independently_admitted, profile)
        }
        ByteTraceMode::RotatedLiteral => {
            bridge::encode_rotated_byte_literal(&independently_admitted, profile)
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

/// Compiles canonical typed-IR initial-zero outputs to real guest instructions.
///
/// The complete canonical module must contain exactly one zero-argument void
/// function with one phi-free block and no global state/proof obligations. Its
/// instructions are exactly one `u8` constant of value zero, then one or more
/// `ByteOutput`s using that precise SSA value. The canonical MCTR is independently
/// decoded and the actual Malbolge code is independently admitted by layout.
/// No host byte emulation, arbitrary constants, EOF or guest ABI is implemented.
///
/// # Errors
///
/// Rejects invalid typed/MCTR data, profile mismatch, unsupported SSA flow
/// or target source beyond the 4096-cell positional layout bound.
pub fn compile_canonical_typed_initial_zero_outputs(
    canonical: &[u8],
    profile: &'static ProfileDescriptor,
) -> Result<CompiledTypedEcho, TypedEchoAdapterError> {
    compile_byte_trace(canonical, profile, ByteTraceMode::InitialZero)
}

/// Lowers canonical typed zero-output prefix followed by successful-byte I/O.
///
/// One `u8 ConstantInteger(0)` SSA definition must be followed by at least
/// one output of that SSA byte, then at least one successful input and one
/// output of the latest input. Reads overwrite the VM accumulator, so any
/// later zero-SSA replay and stale input SSA replay fail closed. Actual
/// guest instructions perform every I/O effect; return/ABI and EOF are absent.
///
/// # Errors
///
/// Rejects malformed or unsupported typed semantics, mismatched profile,
/// canonical MCTR drift or unadmitted/oversized address-sensitive layout.
pub fn compile_canonical_typed_zero_prefixed_latest_byte_trace(
    canonical: &[u8],
    profile: &'static ProfileDescriptor,
) -> Result<CompiledTypedEcho, TypedEchoAdapterError> {
    compile_byte_trace(canonical, profile, ByteTraceMode::ZeroPrefixedLatest)
}

/// Lowers an admitted canonical byte I/O trace with exact eight-bit SSA casts.
///
/// `IntegerBitcast` operations between `u8` and `i8` are representation-only
/// and create new aliases of A, without emitting guest instructions. Every
/// output must reference a still-live unsigned-byte alias of the most recent
/// successful input; later input invalidates all earlier aliases. No EOF,
/// general computation, byte storage, or guest return/ABI claim is made.
///
/// # Errors
///
/// Rejects unsupported effects/casts/SSA, invalid canonical MCTI/MCTR,
/// profile drift, and unadmitted address-sensitive target source.
pub fn compile_canonical_typed_identity_byte_trace(
    canonical: &[u8],
    profile: &'static ProfileDescriptor,
) -> Result<CompiledTypedEcho, TypedEchoAdapterError> {
    compile_byte_trace(canonical, profile, ByteTraceMode::IdentityByteBitcast)
}

/// Compile one current-profile `u8` constant and one to eleven outputs via rotation.
///
/// Unlike initial-zero, only a finite verified set of nonzero values has
/// safe `j`, `*`, `<`, `v` source layouts. The independent bridge executes
/// the produced source in the normative VM and checks exact output bits.
/// No EOF, guest arithmetic, additional source effects or ABI is claimed.
///
/// # Errors
///
/// Rejects malformed MCTI/MCTR, unsupported literal values, forged source
/// semantics, wrong profiles, or unadmitted guest output.
pub fn compile_canonical_typed_rotated_byte_literal(
    canonical: &[u8],
    profile: &'static ProfileDescriptor,
) -> Result<CompiledTypedEcho, TypedEchoAdapterError> {
    compile_byte_trace(canonical, profile, ByteTraceMode::RotatedLiteral)
}
