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
//   - Closed typed instruction and exact integer-constant vocabulary.
// - Must-Not:
//   - Encode control-flow terminators, LLVM opcodes, or host arithmetic modes.
// - Allows:
//   - Inputs: explicit typed SSA operands/results and direct/indirect callees.
//   - Outputs: portable allocation, arithmetic, memory, call, cast, and
//     byte-I/O operations.
//   - Side effects: none.
// - Split-When:
//   - An instruction family gains independently versioned semantic policy.
// - Merge-When:
//   - Instruction and control-flow vocabularies no longer need separate review.
// - Summary:
//   - Defines version-one non-terminating typed compiler IR operations.
// - Description:
//   - Exact integer bits avoid host integer width/sign-extension behavior.
// - Usage:
//   - Stored in basic blocks and validated before canonical serialization.
// - Defaults:
//   - Every value-producing operation names its result and result type.
//

//! Closed non-terminating instruction vocabulary for typed compiler IR.

use super::ids::{FunctionId, TypeId, ValueId};

/// Closed binary operation vocabulary.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum BinaryOp {
    /// Addition.
    Add,
    /// Bitwise AND.
    And,
    /// Floating-point division.
    DivideFloat,
    /// Signed division.
    DivideSigned,
    /// Unsigned division.
    DivideUnsigned,
    /// Multiplication.
    Multiply,
    /// Bitwise OR.
    Or,
    /// Signed remainder.
    RemainderSigned,
    /// Unsigned remainder.
    RemainderUnsigned,
    /// Left shift.
    ShiftLeft,
    /// Arithmetic right shift.
    ShiftRightArithmetic,
    /// Logical right shift.
    ShiftRightLogical,
    /// Subtraction.
    Subtract,
    /// Bitwise XOR.
    Xor,
}

/// Closed typed cast vocabulary.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum CastOp {
    /// Preserve representation while changing admitted pointer type view.
    Bitcast,
    /// Boolean zero/one value to signed integer.
    BoolToSigned,
    /// Floating-point scalar to C truth value.
    FloatToBool,
    /// Floating-point widening or narrowing.
    FloatToFloat,
    /// Floating-point to signed integer.
    FloatToSigned,
    /// Floating-point to unsigned integer excluding boolean.
    FloatToUnsigned,
    /// Equal-width non-boolean integer representation conversion.
    IntegerBitcast,
    /// Non-boolean integer scalar to C truth value.
    IntegerToBool,
    /// Canonical guest integer encoding to object pointer.
    IntegerToPointer,
    /// Guest pointer to C truth value.
    PointerToBool,
    /// Canonical guest object-pointer encoding to non-boolean integer.
    PointerToInteger,
    /// Signed integer extension.
    SignExtend,
    /// Signed integer to floating-point.
    SignedToFloat,
    /// Integer truncation.
    Truncate,
    /// Unsigned integer to floating-point.
    UnsignedToFloat,
    /// Unsigned integer extension.
    ZeroExtend,
}

/// Closed comparison operation vocabulary.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum CompareOp {
    /// Equal for integer, pointer, or floating-point operands.
    Equal,
    /// Ordered floating-point less-than.
    FloatLess,
    /// Ordered floating-point less-than-or-equal.
    FloatLessEqual,
    /// Signed less-than.
    LessSigned,
    /// Signed less-than-or-equal.
    LessSignedEqual,
    /// Unsigned less-than.
    LessUnsigned,
    /// Unsigned less-than-or-equal.
    LessUnsignedEqual,
    /// Not equal.
    NotEqual,
}

/// Exact little-endian integer constant bits.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct IntegerConstant {
    bit_width: u16,
    little_endian: Vec<u8>,
}

impl IntegerConstant {
    /// Returns the declared meaningful bit width.
    #[must_use]
    pub const fn bit_width(&self) -> u16 {
        self.bit_width
    }

    /// Returns exact least-significant-byte-first representation bytes.
    #[must_use]
    pub fn little_endian(&self) -> &[u8] {
        &self.little_endian
    }

    /// Creates one exact integer bit pattern.
    #[must_use]
    pub const fn new(bit_width: u16, little_endian: Vec<u8>) -> Self {
        Self { bit_width, little_endian }
    }
}

/// One direct or SSA-valued function call target.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum CallTarget {
    /// Module-local function identity.
    Direct(FunctionId),
    /// SSA value whose type is a pointer to the invoked function signature.
    Indirect(ValueId),
}

/// One non-terminating typed SSA instruction.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum Instruction {
    /// Compute a byte offset from one guest object pointer.
    AddressOffset {
        /// Integer byte displacement.
        byte_offset: ValueId,
        /// Source pointer.
        pointer: ValueId,
        /// Result pointer value.
        result: ValueId,
        /// Result/source pointer type.
        type_id: TypeId,
    },
    /// Allocate automatic-lifetime guest memory in the active function frame.
    AutomaticAllocate {
        /// Required ABI alignment in bytes.
        alignment: u8,
        /// Explicit ABI `u32` byte count.
        byte_count: ValueId,
        /// Result guest object pointer.
        result: ValueId,
        /// Result pointer type.
        type_id: TypeId,
    },
    /// Apply one binary operation to same-typed operands.
    Binary {
        /// Left operand.
        left: ValueId,
        /// Operation.
        operation: BinaryOp,
        /// Result value.
        result: ValueId,
        /// Right operand.
        right: ValueId,
        /// Shared operand/result type.
        type_id: TypeId,
    },
    /// Read one deterministic successful guest byte effect.
    ByteInput {
        /// Result value.
        result: ValueId,
        /// Unsigned byte result type.
        type_id: TypeId,
    },
    /// Emit one deterministic guest byte.
    ByteOutput {
        /// Integer byte operand.
        value: ValueId,
    },
    /// Invoke one direct or SSA-valued function target.
    Call {
        /// Ordered call arguments.
        arguments: Vec<ValueId>,
        /// Direct or indirect callee identity.
        callee: CallTarget,
        /// Optional typed result.
        result: Option<(ValueId, TypeId)>,
    },
    /// Convert one value under an explicit cast operation.
    Cast {
        /// Cast operation.
        operation: CastOp,
        /// Result value.
        result: ValueId,
        /// Destination type.
        type_id: TypeId,
        /// Source value.
        value: ValueId,
    },
    /// Compare two same-typed operands and produce boolean.
    Compare {
        /// Left operand.
        left: ValueId,
        /// Comparison operation.
        operation: CompareOp,
        /// Boolean result value.
        result: ValueId,
        /// Explicit boolean result type.
        type_id: TypeId,
        /// Right operand.
        right: ValueId,
    },
    /// Materialize one exact integer constant.
    ConstantInteger {
        /// Exact bit representation.
        constant: IntegerConstant,
        /// Result value.
        result: ValueId,
        /// Integer result type.
        type_id: TypeId,
    },
    /// Materialize one module-local function address.
    FunctionAddress {
        /// Module-local function identity.
        function: FunctionId,
        /// Result function-pointer value.
        result: ValueId,
        /// Result pointer-to-function type.
        type_id: TypeId,
    },
    /// Load one object through a guest pointer.
    Load {
        /// Required ABI alignment in bytes.
        alignment: u8,
        /// Pointer operand.
        pointer: ValueId,
        /// Loaded result value.
        result: ValueId,
        /// Loaded object type.
        type_id: TypeId,
    },
    /// Store one object through a guest pointer.
    Store {
        /// Required ABI alignment in bytes.
        alignment: u8,
        /// Pointer operand.
        pointer: ValueId,
        /// Stored value.
        value: ValueId,
    },
}

/// One non-terminating instruction plus exact normalized source provenance.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct LocatedInstruction {
    instruction: Instruction,
    span: super::source::SourceSpan,
}

impl LocatedInstruction {
    /// Returns the typed instruction semantics.
    #[must_use]
    pub const fn instruction(&self) -> &Instruction {
        &self.instruction
    }

    /// Creates one source-located typed instruction.
    #[must_use]
    pub const fn new(
        instruction: Instruction,
        span: super::source::SourceSpan,
    ) -> Self {
        Self { instruction, span }
    }

    /// Returns exact normalized source provenance.
    #[must_use]
    pub const fn span(&self) -> super::source::SourceSpan {
        self.span
    }
}
