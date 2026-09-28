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
//   - Deterministic in-memory ternary lowering values and source provenance.
// - Must-Not:
//   - Encode Malbolge source, choose layout addresses, or import typed-IR
//     types.
// - Allows:
//   - Inputs: exact scalar bit patterns and copied normalized source positions.
//   - Outputs: fixed-width base-three scalars and ordered target operations.
//   - Side effects: none.
// - Split-When:
//   - Layout-specific target operations gain independent invariants.
// - Merge-When:
//   - Another target domain owns the same pre-layout ternary semantics.
// - Summary:
//   - Defines the first pre-layout ternary compiler representation.
// - Description:
//   - Preserves exact C scalar bits and successful byte effects in target
//     state.
// - Usage:
//   - Produced only after validated typed-IR admission and shape checks.
// - Defaults:
//   - Thirty-two-bit scalars use exactly 21 least-significant trits first.
//

//! Deterministic pre-layout ternary compiler representation.

/// Number of trits required to preserve every 32-bit bit pattern.
pub const I32_TERNARY_TRITS: usize = 21;

/// One copied normalized source position.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct TernarySourcePosition {
    /// Zero-based logical source byte offset.
    pub byte: u32,
    /// One-based source column.
    pub column: u32,
    /// One-based source line.
    pub line: u32,
}

/// One copied half-open normalized source span.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct TernarySourceSpan {
    /// Inclusive begin position.
    pub begin: TernarySourcePosition,
    /// Exclusive end position.
    pub end: TernarySourcePosition,
}

/// Exact 32-bit scalar represented as fixed-width least-significant trits.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct TernaryI32Scalar {
    trits: [u8; I32_TERNARY_TRITS],
}

impl TernaryI32Scalar {
    /// Reconstructs the exact original 32-bit bit pattern.
    #[must_use]
    pub fn bits(self) -> u32 {
        let value = self.trits.iter().rev().fold(0u64, |value, trit| {
            value.saturating_mul(3).saturating_add(u64::from(*trit))
        });
        u32::try_from(value).unwrap_or(u32::MAX)
    }

    /// Converts one exact two's-complement bit pattern into 21 base-three
    /// trits.
    #[must_use]
    pub fn from_bits(bits: u32) -> Self {
        let mut remainder = bits;
        let mut trits = [0u8; I32_TERNARY_TRITS];
        for trit in &mut trits {
            let digit = remainder.checked_rem(3).unwrap_or_default();
            *trit = u8::try_from(digit).unwrap_or_default();
            remainder = remainder.checked_div(3).unwrap_or_default();
        }
        debug_assert_eq!(
            remainder, 0,
            "21 ternary digits must preserve every 32-bit pattern",
        );
        Self { trits }
    }

    /// Returns the fixed-width least-significant-trit-first representation.
    #[must_use]
    pub const fn trits(&self) -> &[u8; I32_TERNARY_TRITS] {
        &self.trits
    }
}

/// Declarative semantics for version-one hidden frame validation.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct FrameValidationSemantics {
    /// Required complete-frame alignment in logical bytes.
    pub alignment: u32,
    /// Fixed hidden frame-header size in bytes.
    pub header_bytes: u32,
    /// Runtime status for a null frame pointer.
    pub invalid_argument_status: u32,
    /// Runtime status for malformed frame contents.
    pub invalid_frame_status: u32,
    /// Required version-one flags value.
    pub required_flags: u32,
    /// Runtime status for an admitted frame.
    pub valid_status: u32,
}

/// One admitted call-frame helper represented as declarative semantics.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum FrameHelperOperation {
    /// Validate one hidden version-one call-frame header.
    Validate(FrameValidationSemantics),
}

/// One ordered condition in frame-validator control flow.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum FrameValidationCondition {
    /// Required argument-block pointer is null.
    ArgumentBlockNull,
    /// Flags differ from the required version-one value.
    FlagsNotEqual(u32),
    /// Frame extent is smaller than the hidden header.
    FrameExtentBelow(u32),
    /// Frame extent is not a multiple of the required alignment.
    FrameExtentMisaligned(u32),
    /// Frame header pointer is null.
    FramePointerNull,
    /// No earlier ordered validation condition matched.
    Otherwise,
}

/// One frame-validation branch exit and returned runtime status.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct FrameValidationArm {
    /// Ordered validation condition.
    pub condition: FrameValidationCondition,
    /// Runtime status returned by this branch.
    pub status: u32,
}

/// One call-frame helper after explicit control-flow realization.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum FrameHelperExecutionPlan {
    /// Ordered exits for version-one frame validation.
    Validate {
        /// First matching branch determines the returned status.
        exits: Vec<FrameValidationArm>,
    },
}

/// One ordered compiler-generated startup action.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum StartupAction {
    /// Bind the resolved guest heap exactly once before user code.
    BindHeap {
        /// ABI-encoded object pointer to the first arena byte.
        arena_pointer: u32,
        /// Resolved arena capacity in logical bytes.
        capacity: u32,
    },
    /// Transfer control to the selected user entry function.
    EnterUserCode {
        /// Module-local user entry function identity.
        function: u32,
    },
}

/// Ordered compiler-generated startup plan before target layout/encoding.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct StartupPlan {
    /// Ordered actions; valid plans contain bind then user entry exactly once.
    pub actions: Vec<StartupAction>,
    /// Exact runtime symbol realized by the first startup action.
    pub bind_identity: String,
}

/// Relative ordering of helper and raw intrinsic in one byte-stream wrapper.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ByteStreamWrapperOrder {
    /// Pure byte mapping executes before raw machine output.
    HelperThenIntrinsic,
    /// Raw machine input executes before pure byte/EOF decoding.
    IntrinsicThenHelper,
}

/// Guest-visible return semantics for one public byte-stream wrapper.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ByteStreamWrapperReturn {
    /// Return decoded byte as `i32`, or `-1` for EOF/invalid input.
    DecodedI32OrEof,
    /// Return the emitted unsigned byte widened to guest `int`.
    EmittedByteAsI32,
}

/// Ordered semantic plan for one public guest byte-stream wrapper.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ByteStreamWrapperPlan {
    /// Pure runtime helper semantics used by the wrapper.
    pub helper: RuntimeHelperOperation,
    /// Exact public libc routine identity.
    pub identity: String,
    /// Raw target I/O intrinsic semantics used by the wrapper.
    pub intrinsic: RuntimeIntrinsicOperation,
    /// Relative helper/intrinsic execution order.
    pub order: ByteStreamWrapperOrder,
    /// Guest-visible wrapper return behavior.
    pub return_kind: ByteStreamWrapperReturn,
}

/// One explicit pre-layout public wrapper execution step.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum ByteStreamWrapperExecutionStep {
    /// Initialize the wrapper-local decoded `i32` result storage.
    InitializeI32 {
        /// Exact two's-complement initial bit pattern.
        bits: u32,
    },
    /// Execute one profile-bound raw machine I/O operation.
    MachineIo(MachineIoOperation),
    /// Return the helper-published decoded `i32` value.
    ReturnDecodedI32,
    /// Return the emitted byte widened to guest `int`.
    ReturnEmittedByteAsI32,
    /// Execute one explicit pure runtime-helper plan.
    RuntimeHelper(Box<RuntimeHelperExecutionPlan>),
    /// Continue only for one accepted helper status; otherwise return a value.
    StatusGuard {
        /// Runtime status that continues to the success return.
        accepted_status: u32,
        /// Exact `i32` bits returned when status does not match.
        failure_return_bits: u32,
    },
}

/// One public wrapper after helper and status control flow is explicit.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ByteStreamWrapperExecutionPlan {
    /// Exact public libc routine identity.
    pub identity: String,
    /// Ordered pre-layout execution steps.
    pub steps: Vec<ByteStreamWrapperExecutionStep>,
}

/// Public byte-stream wrapper plan after raw I/O profile realization.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct MachineByteStreamWrapperPlan {
    /// Pure runtime helper semantics used by the wrapper.
    pub helper: RuntimeHelperOperation,
    /// Explicit pre-layout execution plan for the helper semantics.
    pub helper_execution: RuntimeHelperExecutionPlan,
    /// Exact public libc routine identity.
    pub identity: String,
    /// Profile-bound raw machine I/O operation.
    pub machine_io: MachineIoOperation,
    /// Relative helper/machine-I/O execution order.
    pub order: ByteStreamWrapperOrder,
    /// Guest-visible wrapper return behavior.
    pub return_kind: ByteStreamWrapperReturn,
}

/// One graphical source cell encoding a realized machine I/O operation.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct EncodedMachineIo {
    /// Exact code-pointer position used by position-dependent decoding.
    pub code_pointer: u32,
    /// Profile-bound semantic operation represented by the cell.
    pub operation: MachineIoOperation,
    /// Graphical ASCII source cell in the inclusive range 33 through 126.
    pub source_cell: u8,
}

/// Machine I/O effect category after target-profile realization.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum MachineIoKind {
    /// Raw profile input-word effect, including the EOF sentinel.
    InputWord,
    /// Exact guest-byte output effect.
    OutputByte,
}

/// One decoded machine I/O operation bound to an exact target profile.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct MachineIoOperation {
    /// Canonical profile EOF word for input; absent for output.
    pub eof_word: Option<u32>,
    /// Decoded machine instruction byte selected by the profile.
    pub instruction: u8,
    /// Semantic I/O effect category.
    pub kind: MachineIoKind,
}

/// Declarative semantics for profile-word to C-input mapping.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct InputWordDecodeSemantics {
    /// Largest raw word that maps directly to a C byte value.
    pub byte_max: u32,
    /// Exact two's-complement `i32` bits for C `EOF == -1`.
    pub eof_value_bits: u32,
    /// Canonical selected-profile EOF word.
    pub eof_word: u32,
    /// Runtime status for a null result pointer.
    pub invalid_argument_status: u32,
    /// Runtime status for impossible intermediate input words.
    pub invalid_input_status: u32,
    /// Runtime status for byte and EOF mappings.
    pub valid_status: u32,
}

/// One ordered condition in the input-word helper control flow.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum InputDecodeCondition {
    /// No earlier ordered condition matched.
    Otherwise,
    /// Result storage is the null guest pointer.
    ResultPointerNull,
    /// Raw input word is at most the supplied inclusive bound.
    WordAtMost(u32),
    /// Raw input word equals one exact sentinel.
    WordEquals(u32),
}

/// Result publication behavior for one input-helper exit.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum InputDecodeResult {
    /// Publish one exact `i32` bit pattern.
    ConstantI32Bits(u32),
    /// Publish the raw `0..255` input word as exact guest `i32`.
    InputWordAsI32,
    /// Preserve the caller-provided result storage unchanged.
    Unchanged,
}

/// One ordered input-helper branch exit and its publications.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct InputDecodeArm {
    /// Ordered branch condition.
    pub condition: InputDecodeCondition,
    /// Result-storage publication behavior.
    pub result: InputDecodeResult,
    /// Runtime status returned by this branch.
    pub status: u32,
}

/// Explicit pre-layout control flow for raw input-word decoding.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct InputWordDecodeControlFlow {
    /// Ordered branch exits; the first matching condition wins.
    pub exits: Vec<InputDecodeArm>,
}

/// One pure runtime helper after explicit control-flow realization.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum RuntimeHelperExecutionPlan {
    /// Four-way input decoder with explicit result/status publication.
    DecodeInputWord(Box<InputWordDecodeControlFlow>),
    /// Low-eight-bit output mapping before the raw output intrinsic.
    OutputByte {
        /// Exact low-byte mask.
        mask: u32,
    },
}

/// One pure guest-runtime helper represented as declarative target semantics.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum RuntimeHelperOperation {
    /// Map a raw profile input word to byte-or-EOF `i32` plus runtime status.
    DecodeInputWord(Box<InputWordDecodeSemantics>),
    /// Reduce one C `int` value to the emitted low-eight-bit guest byte.
    OutputByte {
        /// Exact low-byte mask.
        mask: u32,
    },
}

/// One declaration-only guest-runtime operation before profile opcode encoding.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum RuntimeIntrinsicOperation {
    /// Read one raw selected-profile input word, including the EOF word.
    InputWord,
    /// Emit one exact guest byte through the selected profile.
    OutputByte,
}

/// One deterministic pre-layout ternary operation.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum TernaryOperation {
    /// Apply exact 32-bit bitwise AND to two previously materialized values.
    AndI32 {
        /// Left upstream SSA value identity.
        left: u32,
        /// Upstream SSA result identity.
        result: u32,
        /// Right upstream SSA value identity.
        right: u32,
        /// Original instruction provenance.
        span: TernarySourceSpan,
    },
    /// Read one successful guest `u8` byte effect.
    ///
    /// This is not the raw profile input word and therefore cannot represent
    /// EOF; guest-runtime mapping remains a later realization concern.
    ByteInput {
        /// Upstream SSA result identity retained until later
        /// allocation/layout.
        result: u32,
        /// Original instruction provenance.
        span: TernarySourceSpan,
    },
    /// Emit one exact guest `u8` byte effect.
    ByteOutput {
        /// Original instruction provenance.
        span: TernarySourceSpan,
        /// Upstream SSA byte value identity retained until later layout.
        value: u32,
    },
    /// Materialize one exact `i32` bit pattern as fixed-width target trits.
    MaterializeI32 {
        /// Upstream SSA result identity retained until later
        /// allocation/layout.
        result: u32,
        /// Exact target ternary scalar.
        scalar: TernaryI32Scalar,
        /// Original instruction provenance.
        span: TernarySourceSpan,
    },
    /// Return one previously materialized scalar value.
    Return {
        /// Upstream SSA value identity retained until later allocation/layout.
        value: u32,
        /// Original terminator provenance.
        span: TernarySourceSpan,
    },
    /// Truncate one exact `i32` value to its low eight bits as `u8`.
    TruncateI32ToU8 {
        /// Upstream SSA result identity.
        result: u32,
        /// Original instruction provenance.
        span: TernarySourceSpan,
        /// Upstream SSA source value identity.
        value: u32,
    },
}

/// One lowered function before target layout and encoding.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct TernaryFunction {
    /// Module-local function identity.
    pub id: u32,
    /// Portable semantic function name.
    pub name: String,
    /// Ordered target operations.
    pub operations: Vec<TernaryOperation>,
    /// Complete original function provenance.
    pub span: TernarySourceSpan,
}

/// One deterministic pre-layout ternary program.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct TernaryProgram {
    /// Exact upstream guest ABI identity.
    pub abi_id: String,
    /// Ordered lowered functions.
    pub functions: Vec<TernaryFunction>,
    /// Exact upstream typed-IR format version.
    pub input_format_version: u16,
    /// Portable logical source identity.
    pub source_id: String,
    /// Exact normalized-source digest bytes.
    pub source_sha256: [u8; 32],
    /// Exact target-profile identity.
    pub target_profile: String,
}
