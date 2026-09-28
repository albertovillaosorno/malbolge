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
