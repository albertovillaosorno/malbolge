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
//   - Bounded successful-byte-I/O effect traces between validated ternary IR
//     and independently admitted position-sensitive Malbolge code.
// - Must-Not:
//   - Impersonate EOF, failed byte I/O, general guest computation, or a C ABI.
// - Allows:
//   - Inputs: canonical pre-layout ternary program and selected profile.
//   - Outputs: verified linear source for echo or latest-read byte I/O traces.
//   - Side effects: none.
// - Split-When:
//   - More general guest byte flow requires runtime linkage and allocation.
// - Merge-When:
//   - A complete linker proves this exact sublanguage without special rules.
// - Summary:
//   - Connects a closed typed-IR effect trace to actual executable code.
// - Description:
//   - Proves adjacent byte echoes and latest-successful-read I/O replay traces
//     while retaining the original adjacent-echo admission unchanged.
// - Usage:
//   - First lower typed IR, then call encode_successful_byte_echo.
// - Defaults:
//   - Reject rather than approximate any unproved source semantics.
//
//! Small independently validated ternary-to-Malbolge byte-echo bridge.
//!
//! The resulting program reproduces the projected effect trace **only** when
//! every input succeeds with a byte (not EOF), every output succeeds, and the
//! function's return value and guest ABI are not observed. It is not a
//! general-purpose byte-stream runtime or a C-to-Malbolge compiler.

#[path = "../../malbolge-layout/composition/lib.rs"]
pub mod layout;
#[path = "../../ternary-lowering/composition/lib.rs"]
pub mod ternary;

use malbolge::ProfileDescriptor;

use layout::{LinearLayout, LinearLayoutError, LinearOpcode, encode_linear_layout};
use ternary::{
    TernaryOperation, TernaryProgram, TernaryProgramValidationError, validate_ternary_program,
};

/// A failed pre-layout admission, semantic bridge, or final target admission.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ByteEchoBridgeError {
    /// Canonical pre-layout program semantics or provenance are invalid.
    InvalidProgram(TernaryProgramValidationError),
    /// The independently checked target encoder rejected the selected trace.
    Layout(LinearLayoutError),
    /// The selected VM profile differs from the validated program identity.
    ProfileMismatch,
    /// The function is not a nonempty sequence of adjacent echo pairs with
    /// one final value-free return, or multiple functions are supplied.
    UnsupportedEffectTrace,
}

/// Emits one bounded, source-validated successful-byte-echo trace.
///
/// Each adjacent `ByteInput`/`ByteOutput` pair must use the exact same SSA
/// value, and the final operation must be `ReturnVoid`. The VM itself has no
/// host byte callbacks: source is returned from the separately verified linear
/// layout. The caller must enforce that all projected inputs/outputs succeed;
/// the VM's raw EOF word is **not** the typed successful-byte result.
///
/// # Errors
///
/// Rejects malformed canonical state, profile drift, any unsupported source
/// effect or return, and any address-sensitive layout failure.
pub fn encode_successful_byte_echo(
    program: &TernaryProgram,
    profile: &'static ProfileDescriptor,
) -> Result<LinearLayout, ByteEchoBridgeError> {
    validate_ternary_program(program).map_err(ByteEchoBridgeError::InvalidProgram)?;
    if program.target_profile != profile.id() {
        return Err(ByteEchoBridgeError::ProfileMismatch);
    }
    let [function] = program.functions.as_slice() else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    let Some((TernaryOperation::ReturnVoid { .. }, instructions)) =
        function.operations.split_last()
    else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    let (pairs, remainder) = instructions.as_chunks::<2>();
    if pairs.is_empty() || !remainder.is_empty() {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    }
    let mut operations = Vec::with_capacity(function.operations.len());
    for pair in pairs {
        let [
            TernaryOperation::ByteInput { result, .. },
            TernaryOperation::ByteOutput { value, .. },
        ] = pair
        else {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        };
        if result != value {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        }
        operations.push(LinearOpcode::InputWord);
        operations.push(LinearOpcode::OutputByte);
    }
    operations.push(LinearOpcode::Halt);
    encode_linear_layout(profile, &operations).map_err(ByteEchoBridgeError::Layout)
}

/// Emits a bounded successful-byte I/O trace using the VM accumulator itself.
///
/// Every source operation is one successful `ByteInput` or `ByteOutput`, with
/// one final `ReturnVoid`. An output must name **exactly the most recent**
/// successful input's SSA result; the input may be output repeatedly or not
/// at all. Reading a later byte overwrites the accumulator, so an earlier
/// byte's SSA identity cannot be replayed after that read. No guest work is
/// delegated to a host callback; the linear code contains only raw VM input,
/// output and halt instructions.
///
/// This is deliberately distinct from [`encode_successful_byte_echo`]: the
/// old API retains its strict adjacent-pair contract. The caller must enforce
/// successful byte reads (never EOF) and successful writes. Return/ABI state
/// is unobserved. This function does not realize arbitrary byte dataflow,
/// constants, arithmetic, guest heap or control-flow operations.
///
/// # Errors
///
/// Rejects malformed or profile-mismatched ternary state, absent successful
/// input, any non-I/O effect, stale/undefined SSA output and unsafe layout.
pub fn encode_successful_latest_byte_trace(
    program: &TernaryProgram,
    profile: &'static ProfileDescriptor,
) -> Result<LinearLayout, ByteEchoBridgeError> {
    validate_ternary_program(program).map_err(ByteEchoBridgeError::InvalidProgram)?;
    if program.target_profile != profile.id() {
        return Err(ByteEchoBridgeError::ProfileMismatch);
    }
    let [function] = program.functions.as_slice() else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    let Some((TernaryOperation::ReturnVoid { .. }, instructions)) =
        function.operations.split_last()
    else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    let mut last_input = None;
    let mut operations = Vec::with_capacity(function.operations.len());
    for instruction in instructions {
        if let TernaryOperation::ByteInput { result, .. } = instruction {
            last_input = Some(*result);
            operations.push(LinearOpcode::InputWord);
        } else if let TernaryOperation::ByteOutput { value, .. } = instruction {
            if last_input != Some(*value) {
                return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
            }
            operations.push(LinearOpcode::OutputByte);
        } else {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        }
    }
    if last_input.is_none() {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    }
    operations.push(LinearOpcode::Halt);
    encode_linear_layout(profile, &operations).map_err(ByteEchoBridgeError::Layout)
}

/// Emits an exact nonempty zero-byte output trace using the VM's initial A=0.
///
/// The source is one verified `MaterializeU8(0)` SSA definition, followed by
/// one or more outputs of **that same** SSA byte and a final `ReturnVoid`.
/// `MaterializeU8(0)` needs no guest instruction because the normative VM
/// initializes its accumulator to zero. Each output is still a real guest
/// `<` instruction, followed by one guest halt. Neither a host print nor a
/// fabricated guest byte register is involved. No byte input is consumed.
///
/// This opt-in bridge does **not** alter strict echo or latest-read semantics.
/// Only the original initial zero constant is admitted: a nonzero scalar,
/// rewritten value, older SSA identity, additional constant or other target
/// operation needs separate executable dataflow proof. Source provenance
/// remains in the canonical ternary input; code slots only cover guest work.
///
/// # Errors
///
/// Rejects invalid/profile-mismatched ternary source, unsupported or absent
/// zero output, and target code longer than the linear layout capacity.
pub fn encode_initial_zero_outputs(
    program: &TernaryProgram,
    profile: &'static ProfileDescriptor,
) -> Result<LinearLayout, ByteEchoBridgeError> {
    validate_ternary_program(program).map_err(ByteEchoBridgeError::InvalidProgram)?;
    if program.target_profile != profile.id() {
        return Err(ByteEchoBridgeError::ProfileMismatch);
    }
    let [function] = program.functions.as_slice() else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    let Some((TernaryOperation::ReturnVoid { .. }, instructions)) =
        function.operations.split_last()
    else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    let Some((TernaryOperation::MaterializeU8 { result, scalar, .. }, writes)) =
        instructions.split_first()
    else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    if scalar.bits() != 0 || writes.is_empty() {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    }
    let mut operations = Vec::with_capacity(writes.len().saturating_add(1));
    for write in writes {
        let TernaryOperation::ByteOutput { value, .. } = write else {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        };
        if value != result {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        }
        operations.push(LinearOpcode::OutputByte);
    }
    operations.push(LinearOpcode::Halt);
    encode_linear_layout(profile, &operations).map_err(ByteEchoBridgeError::Layout)
}
