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
    /// Exact C boolean value (zero or one).
    Bool,
    /// Exact signed 32-bit C integer semantics.
    I32,
    /// Exact signed 8-bit C integer bit pattern.
    I8,
    /// Any other already-admitted typed-IR type.
    Other,
    /// Exact unsigned 32-bit C integer semantics.
    U32,
    /// Exact unsigned 8-bit byte semantics.
    U8,
    /// No returned scalar value (typed-IR void function).
    Void,
}

/// Admitted ordered comparisons of exact promoted 32-bit operands.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum InputOrderedComparison {
    /// Signed less-than.
    Signed,
    /// Signed less-than-or-equal.
    SignedEqual,
    /// Unsigned less-than.
    Unsigned,
    /// Unsigned less-than-or-equal.
    UnsignedEqual,
}

/// One projected non-terminating typed-IR instruction.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum InputInstruction {
    /// Preserve admitted 32-bit add semantics before target realization.
    BinaryAdd {
        /// Left upstream SSA operand identity.
        left: u32,
        /// Upstream SSA result identity.
        result: u32,
        /// Right upstream SSA operand identity.
        right: u32,
        /// Exact normalized source provenance.
        span: InputSourceSpan,
        /// Admitted signed or unsigned 32-bit type category.
        type_kind: InputScalarType,
    },
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
    /// Preserve admitted 32-bit signed division before target realization.
    BinaryDivideSigned {
        /// Left upstream SSA operand identity.
        left: u32,
        /// Upstream SSA result identity.
        result: u32,
        /// Right upstream SSA operand identity.
        right: u32,
        /// Exact normalized source provenance.
        span: InputSourceSpan,
        /// Admitted 32-bit scalar category.
        type_kind: InputScalarType,
    },
    /// Preserve admitted 32-bit unsigned division before target realization.
    BinaryDivideUnsigned {
        /// Left upstream SSA operand identity.
        left: u32,
        /// Upstream SSA result identity.
        result: u32,
        /// Right upstream SSA operand identity.
        right: u32,
        /// Exact normalized source provenance.
        span: InputSourceSpan,
        /// Admitted 32-bit scalar category.
        type_kind: InputScalarType,
    },
    /// Preserve admitted promoted 32-bit multiplication before realization.
    BinaryMultiply {
        /// Left upstream SSA operand identity.
        left: u32,
        /// Upstream SSA result identity.
        result: u32,
        /// Right upstream SSA operand identity.
        right: u32,
        /// Exact normalized source provenance.
        span: InputSourceSpan,
        /// Admitted signed or unsigned 32-bit type category.
        type_kind: InputScalarType,
    },
    /// Apply bitwise OR to two previously defined exact `i32` values.
    BinaryOr {
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
    /// Preserve admitted 32-bit signed remainder before target realization.
    BinaryRemainderSigned {
        /// Left upstream SSA operand identity.
        left: u32,
        /// Upstream SSA result identity.
        result: u32,
        /// Right upstream SSA operand identity.
        right: u32,
        /// Exact normalized source provenance.
        span: InputSourceSpan,
        /// Admitted 32-bit scalar category.
        type_kind: InputScalarType,
    },
    /// Preserve admitted 32-bit unsigned remainder before target realization.
    BinaryRemainderUnsigned {
        /// Left upstream SSA operand identity.
        left: u32,
        /// Upstream SSA result identity.
        result: u32,
        /// Right upstream SSA operand identity.
        right: u32,
        /// Exact normalized source provenance.
        span: InputSourceSpan,
        /// Admitted 32-bit scalar category.
        type_kind: InputScalarType,
    },
    /// Preserve admitted 32-bit left shift semantics for later realization.
    BinaryShiftLeft {
        /// Left upstream SSA operand identity.
        left: u32,
        /// Upstream SSA result identity.
        result: u32,
        /// Right upstream SSA operand identity.
        right: u32,
        /// Exact normalized source provenance.
        span: InputSourceSpan,
        /// Admitted signed or unsigned 32-bit type category.
        type_kind: InputScalarType,
    },
    /// Preserve admitted 32-bit arithmetic right shift semantics for later
    /// realization.
    BinaryShiftRightArithmetic {
        /// Left upstream SSA operand identity.
        left: u32,
        /// Upstream SSA result identity.
        result: u32,
        /// Right upstream SSA operand identity.
        right: u32,
        /// Exact normalized source provenance.
        span: InputSourceSpan,
        /// Admitted signed or unsigned 32-bit type category.
        type_kind: InputScalarType,
    },
    /// Preserve admitted 32-bit logical right shift semantics for later
    /// realization.
    BinaryShiftRightLogical {
        /// Left upstream SSA operand identity.
        left: u32,
        /// Upstream SSA result identity.
        result: u32,
        /// Right upstream SSA operand identity.
        right: u32,
        /// Exact normalized source provenance.
        span: InputSourceSpan,
        /// Admitted signed or unsigned 32-bit type category.
        type_kind: InputScalarType,
    },
    /// Preserve admitted 32-bit subtract semantics before target realization.
    BinarySubtract {
        /// Left upstream SSA operand identity.
        left: u32,
        /// Upstream SSA result identity.
        result: u32,
        /// Right upstream SSA operand identity.
        right: u32,
        /// Exact normalized source provenance.
        span: InputSourceSpan,
        /// Admitted signed or unsigned 32-bit type category.
        type_kind: InputScalarType,
    },
    /// Apply bitwise XOR to two previously defined exact `i32` values.
    BinaryXor {
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
    /// Promote a defined Boolean SSA value to signed 32-bit zero/one.
    BoolToSigned {
        /// New signed 32-bit SSA result identity.
        result: u32,
        /// Exact normalized source provenance.
        span: InputSourceSpan,
        /// Signed destination scalar type category.
        type_kind: InputScalarType,
        /// Previously defined Boolean SSA source.
        value: u32,
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
    /// Compare exact 32-bit SSA operands for equality without host evaluation.
    CompareEqual {
        /// Left input SSA value.
        left: u32,
        /// Boolean result SSA identity.
        result: u32,
        /// Right input SSA value.
        right: u32,
        /// Original source provenance.
        span: InputSourceSpan,
        /// Boolean result type from admitted typed IR.
        type_kind: InputScalarType,
    },
    /// Compare exact 32-bit SSA operands for inequality without host
    /// evaluation.
    CompareNotEqual {
        /// Left input SSA value.
        left: u32,
        /// Boolean result SSA identity.
        result: u32,
        /// Right input SSA value.
        right: u32,
        /// Original source provenance.
        span: InputSourceSpan,
        /// Boolean result type from admitted typed IR.
        type_kind: InputScalarType,
    },
    /// Preserve ordered 32-bit comparison with a distinct Boolean result.
    CompareOrdered {
        /// Left operand SSA identity.
        left: u32,
        /// Admitted signedness and ordering predicate.
        operation: InputOrderedComparison,
        /// Distinct Boolean SSA result.
        result: u32,
        /// Right operand SSA identity.
        right: u32,
        /// Original source provenance.
        span: InputSourceSpan,
        /// The explicitly admitted Boolean result kind.
        type_kind: InputScalarType,
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
    /// Reinterpret an exact 32-bit integer without changing its bits.
    IntegerBitcast {
        /// Upstream SSA result identity.
        result: u32,
        /// Exact normalized source provenance.
        span: InputSourceSpan,
        /// Destination signedness category copied from validated typed IR.
        type_kind: InputScalarType,
        /// Upstream SSA source identity.
        value: u32,
    },
    /// Convert one admitted 32-bit integer or successful byte to Boolean.
    IntegerToBool {
        /// New Boolean SSA definition.
        result: u32,
        /// Exact typed-IR source span.
        span: InputSourceSpan,
        /// Required Boolean destination type.
        type_kind: InputScalarType,
        /// Defined signed/unsigned word or successful unsigned byte source.
        value: u32,
    },
    /// Sign-extend a separately defined exact signed byte to `i32`.
    SignExtendI8ToI32 {
        /// Newly defined signed 32-bit SSA identity.
        result: u32,
        /// Original typed-IR cast provenance.
        span: InputSourceSpan,
        /// Required signed 32-bit result kind.
        type_kind: InputScalarType,
        /// Defined signed 8-bit source SSA identity.
        value: u32,
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
    /// Zero-extend a successful byte to an unsigned 32-bit SSA value.
    ZeroExtendInteger {
        /// Upstream SSA result identity.
        result: u32,
        /// Exact normalized source provenance.
        span: InputSourceSpan,
        /// Admitted destination scalar category.
        type_kind: InputScalarType,
        /// Previously defined byte-valued source SSA identity.
        value: u32,
    },
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
    /// Declared result type copied from the validated function signature.
    pub return_kind: InputScalarType,
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
