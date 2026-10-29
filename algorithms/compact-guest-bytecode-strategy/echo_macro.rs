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
//   - A bounded, non-executable echo-run candidate for bytecode research.
// - Must-Not:
//   - Claim a resident Malbolge interpreter, linked bytecode or guest ABI.
// - Allows:
//   - Inputs: independently validated canonical ternary programs and profiles.
//   - Outputs: reproducible candidate bytes and fully checked expansion.
//   - Side effects: in-memory allocation only.
// - Split-When:
//   - The first executable guest interpreter needs an owned runtime contract.
// - Merge-When:
//   - A trusted compiler backend includes this exact verified experiment.
// - Summary:
//   - Measures a lower bound for the compact bytecode code-size hypothesis.
// - Description:
//   - Represents an entire successful input/output trace as a versioned repeat.
// - Usage:
//   - Used by the compact_guest_bytecode_strategy integration test.
// - Defaults:
//   - Expansion is on the host for verification, never guest execution.
//
//! Optimistic structural compression experiment, **not** a VM bytecode runtime.
//!
//! `CEB1` followed by a little-endian u16 repeat count is only a *proposal*.
//! No guest interpreter, code/data placement, loader, source-authenticating
//! envelope, or VM-side dispatch exists. The independent verifier expands the
//! proposal **on the host**, cross-checks the original ternary effect sequence,
//! and invokes the real Malbolge layout verifier for a direct-code baseline.

#[path = "../../src/compiler/byte-echo-bridge/composition/lib.rs"]
pub mod bridge;

use malbolge::ProfileDescriptor;

use bridge::layout::{LinearLayout, LinearLayoutError, LinearOpcode, encode_linear_layout};
use bridge::ternary::{
    TernaryOperation, TernaryProgram, TernaryProgramValidationError, validate_ternary_program,
};

/// A versioned six-byte research-only echo macro descriptor.
pub const ECHO_MACRO_BYTES: usize = 6;
const MAGIC: &[u8; 4] = b"CEB1";
const MAX_ECHO_PAIRS: usize = 2047;

/// Reproducible failures for structural compression and independent expansion.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum EchoMacroError {
    /// The macro is not exactly six bytes or has an invalid count/magic.
    InvalidCandidate,
    /// Reconstructed instructions failed final layout/source admission.
    Layout(LinearLayoutError),
    /// Profile identity differs from canonical source compilation.
    ProfileMismatch,
    /// The original ternary program is not canonical.
    Program(TernaryProgramValidationError),
    /// The source is not one bounded, adjacent, SSA-identical echo trace.
    UnsupportedSource,
}

fn verified_ternary_echo_shape<'program>(
    program: &'program TernaryProgram,
    profile: &'static ProfileDescriptor,
) -> Result<&'program [TernaryOperation], EchoMacroError> {
    validate_ternary_program(program).map_err(EchoMacroError::Program)?;
    if program.target_profile != profile.id() {
        return Err(EchoMacroError::ProfileMismatch);
    }
    let [function] = program.functions.as_slice() else {
        return Err(EchoMacroError::UnsupportedSource);
    };
    let Some((TernaryOperation::ReturnVoid { .. }, instructions)) =
        function.operations.split_last()
    else {
        return Err(EchoMacroError::UnsupportedSource);
    };
    let (pairs, remainder) = instructions.as_chunks::<2>();
    if pairs.is_empty() || pairs.len() > MAX_ECHO_PAIRS || !remainder.is_empty() {
        return Err(EchoMacroError::UnsupportedSource);
    }
    for [input, output] in pairs {
        let (
            TernaryOperation::ByteInput { result, .. },
            TernaryOperation::ByteOutput { value, .. },
        ) = (input, output)
        else {
            return Err(EchoMacroError::UnsupportedSource);
        };
        if result != value {
            return Err(EchoMacroError::UnsupportedSource);
        }
    }
    Ok(instructions)
}

/// Produces only a structural research candidate, not an executable bytecode.
///
/// A future product format must *also* bind source identity, profile identity,
/// and code/data residency. These six bytes deliberately omit that overhead.
///
/// # Errors
///
/// Rejects malformed, unsupported, overlarge or profile-mismatched programs.
pub fn encode_echo_macro(
    program: &TernaryProgram,
    profile: &'static ProfileDescriptor,
) -> Result<[u8; ECHO_MACRO_BYTES], EchoMacroError> {
    let instructions = verified_ternary_echo_shape(program, profile)?;
    // One pair contributes exactly one input operation; the count is computed
    // without trusting an unverified encoded candidate.
    let count = instructions
        .iter()
        .filter(|op| matches!(op, TernaryOperation::ByteInput { .. }))
        .count();
    let encoded_count = u16::try_from(count).map_err(|_error| EchoMacroError::UnsupportedSource)?;
    let [lo, hi] = encoded_count.to_le_bytes();
    Ok([MAGIC[0], MAGIC[1], MAGIC[2], MAGIC[3], lo, hi])
}

/// Independently reconstructs *direct* source after comparing each SSA effect.
///
/// This is host-side verification, not interpreter execution in Malbolge. The
/// caller must provide the original canonical ternary program, since the
/// research descriptor does not authenticate that program by itself.
///
/// # Errors
///
/// Rejects forged count, source shape, profile, and final layout. A candidate
/// from another equal-length source is not independently source-bound.
pub fn admit_echo_macro(
    program: &TernaryProgram,
    profile: &'static ProfileDescriptor,
    candidate: &[u8],
) -> Result<LinearLayout, EchoMacroError> {
    let instructions = verified_ternary_echo_shape(program, profile)?;
    let [b'C', b'E', b'B', b'1', lo, hi] = candidate else {
        return Err(EchoMacroError::InvalidCandidate);
    };
    let count = usize::from(u16::from_le_bytes([*lo, *hi]));
    if count == 0 || count > MAX_ECHO_PAIRS {
        return Err(EchoMacroError::InvalidCandidate);
    }
    let (pairs, remainder) = instructions.as_chunks::<2>();
    if !remainder.is_empty() || pairs.len() != count {
        return Err(EchoMacroError::InvalidCandidate);
    }
    let mut operations = Vec::with_capacity(instructions.len().saturating_add(1));
    for pair in pairs {
        let [
            TernaryOperation::ByteInput { result, .. },
            TernaryOperation::ByteOutput { value, .. },
        ] = pair
        else {
            return Err(EchoMacroError::UnsupportedSource);
        };
        if result != value {
            return Err(EchoMacroError::UnsupportedSource);
        }
        operations.push(LinearOpcode::InputWord);
        operations.push(LinearOpcode::OutputByte);
    }
    operations.push(LinearOpcode::Halt);
    encode_linear_layout(profile, &operations).map_err(EchoMacroError::Layout)
}

/// Optimistic **upper bound** on absent interpreter/packaging code cells.
///
/// This calculation unrealistically assumes one candidate byte costs one
/// Malbolge memory cell and a reusable interpreter is paid for just once.
/// The result is *not* a measured compilation benefit or proof of runtime
/// viability; a future real guest interpreter may exceed this allowance.
#[must_use]
pub const fn maximum_runtime_cells_for_strict_size_win(direct_cells: usize) -> Option<usize> {
    maximum_runtime_cells_with_binding(direct_cells, 0)
}

/// Optimistic code-cell allowance after an *additional* binding footprint.
///
/// `binding_cells` is an explicitly hypothetical data-placement cost. A
/// 32-cell scenario is useful for testing sensitivity to source identity, but
/// 32 bytes of any unimplemented digest do **not** yet authenticate a source.
///
/// Returns `None` if even a zero-cost interpreter cannot strictly win, or if
/// computing the hypothetical overhead exceeds the host's integer range.
#[must_use]
pub const fn maximum_runtime_cells_with_binding(
    direct_cells: usize,
    binding_cells: usize,
) -> Option<usize> {
    let Some(total) = ECHO_MACRO_BYTES.checked_add(binding_cells) else {
        return None;
    };
    let Some(overhead) = total.checked_add(1) else {
        return None;
    };
    direct_cells.checked_sub(overhead)
}
