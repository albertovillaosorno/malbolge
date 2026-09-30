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
//   - Narrow semantic projection accepted from validated typed compiler IR.
// - Must-Not:
//   - Import upstream compiler implementation types or parse serialized IR.
// - Allows:
//   - Inputs: copied module provenance, function shape, scalars, byte effects,
//     and returns.
//   - Outputs: immutable lowering input records owned by this capability.
//   - Side effects: none.
// - Split-When:
//   - Another upstream IR family needs independent adaptation semantics.
// - Merge-When:
//   - Another port owns the same typed semantic projection.
// - Summary:
//   - Defines the explicit inbound boundary for ternary lowering.
// - Description:
//   - Keeps upstream typed-IR implementation details outside this function.
// - Usage:
//   - Compiler composition validates typed IR, then copies semantics here.
// - Defaults:
//   - Unsupported operations remain explicit rather than being approximated.
//

//! Inbound typed-IR semantic projection for ternary lowering.

/// One normalized source position copied from admitted typed IR.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct InputSourcePosition {
    /// Zero-based logical source byte offset.
    pub byte: u32,
    /// One-based source column.
    pub column: u32,
    /// One-based source line.
    pub line: u32,
}

/// One half-open normalized source span copied from admitted typed IR.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct InputSourceSpan {
    /// Inclusive begin position.
    pub begin: InputSourcePosition,
    /// Exclusive end position.
    pub end: InputSourcePosition,
}

/// Input scalar type categories required by the first lowering slice.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum InputScalarType {
    /// Exact signed 32-bit C integer semantics.
    I32,
    /// Any other already-admitted typed-IR type.
    Other,
    /// Exact unsigned 8-bit byte semantics.
    U8,
}

/// One projected non-terminating typed-IR instruction.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum InputInstruction {
    /// Apply bitwise AND to two previously defined exact `i32` values.
    BinaryAnd {
        /// Left upstream SSA operand identity.
        left: u32,
        /// Upstream SSA result identity.
        result: u32,
        /// Right upstream SSA operand identity.
        right: u32,
        /// Exact normalized source provenance.
        span: InputSourceSpan,
        /// Admitted scalar type category.
        type_kind: InputScalarType,
    },
    /// Read one deterministic successful guest byte effect.
    ByteInput {
        /// Upstream SSA result identity.
        result: u32,
        /// Exact normalized source provenance.
        span: InputSourceSpan,
        /// Admitted scalar type category.
        type_kind: InputScalarType,
    },
    /// Emit one deterministic guest byte effect.
    ByteOutput {
        /// Exact normalized source provenance.
        span: InputSourceSpan,
        /// Upstream SSA byte value identity.
        value: u32,
    },
    /// Exact integer constant bits plus typed result identity.
    ConstantInteger {
        /// Meaningful source bit width.
        bit_width: u16,
        /// Exact least-significant-byte-first bit representation.
        little_endian: Vec<u8>,
        /// Upstream SSA result identity.
        result: u32,
        /// Exact normalized source provenance.
        span: InputSourceSpan,
        /// Admitted scalar type category.
        type_kind: InputScalarType,
    },
    /// Truncate one previously defined exact `i32` value to `u8`.
    TruncateInteger {
        /// Upstream SSA result identity.
        result: u32,
        /// Exact normalized source provenance.
        span: InputSourceSpan,
        /// Admitted destination scalar type category.
        type_kind: InputScalarType,
        /// Upstream SSA source value identity.
        value: u32,
    },
    /// An admitted typed-IR instruction not implemented by this lowering slice.
    Unsupported,
}

/// One projected typed-IR block terminator.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum InputTerminator {
    /// Return an optional upstream SSA value.
    Return {
        /// Exact terminator provenance.
        span: InputSourceSpan,
        /// Optional returned value identity.
        value: Option<u32>,
    },
    /// An admitted typed-IR terminator not implemented by this lowering slice.
    Unsupported,
}

/// One projected typed-IR basic block.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct InputBlock {
    /// Upstream block identity.
    pub id: u32,
    /// Ordered projected instructions.
    pub instructions: Vec<InputInstruction>,
    /// Number of admitted phi nodes.
    pub phi_count: usize,
    /// Final projected control operation.
    pub terminator: InputTerminator,
}

/// One projected typed-IR function.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct InputFunction {
    /// Ordered projected basic blocks.
    pub blocks: Vec<InputBlock>,
    /// Upstream entry block identity.
    pub entry: u32,
    /// Upstream function identity.
    pub id: u32,
    /// Portable semantic function name.
    pub name: String,
    /// Number of admitted parameters.
    pub parameter_count: usize,
    /// Complete normalized source provenance.
    pub span: InputSourceSpan,
}

/// One complete validated typed-IR semantic projection.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct TypedIrInput {
    /// Exact guest ABI identity.
    pub abi_id: String,
    /// Ordered projected functions.
    pub functions: Vec<InputFunction>,
    /// Number of admitted globals.
    pub global_count: usize,
    /// Exact upstream typed-IR format version.
    pub input_format_version: u16,
    /// Number of retained verifier-visible proof obligations.
    pub proof_obligation_count: usize,
    /// Portable logical source identity.
    pub source_id: String,
    /// Exact normalized-source digest bytes.
    pub source_sha256: [u8; 32],
    /// Exact target-profile identity.
    pub target_profile: String,
}
