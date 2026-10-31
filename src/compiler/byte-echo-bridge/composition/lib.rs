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

use malbolge::{ProfileDescriptor, ProfileMachine, RunOutcome, current_profile};
use std::collections::BTreeSet;
use std::iter::repeat_n;

use layout::{LinearLayout, LinearLayoutError, LinearOpcode, encode_linear_layout};
use ternary::{
    TernaryOperation, TernaryProgram, TernaryProgramValidationError, validate_ternary_program,
};

/// Profile-specific `(byte, graphical no-op prefix)` rotation witnesses.
/// Every candidate is independently re-executed by the normative VM.
const ROTATED_BYTE_SEEDS: &[(u8, usize)] = &[
    (4, 23),
    (5, 20),
    (6, 16),
    (9, 7),
    (10, 4),
    (11, 1),
    (18, 24),
    (19, 21),
    (20, 18),
    (21, 6),
    (22, 3),
    (23, 0),
    (251, 22),
    (253, 19),
];

/// Exact two-output witnesses differ because the additional `<` changes
/// both positional encoding and loader-expanded memory. These are not valid
/// single-output seeds, nor a proof for three or more outputs.
const ROTATED_DOUBLE_BYTE_SEEDS: &[(u8, usize)] = &[
    (55, 20),
    (64, 19),
    (65, 22),
    (66, 16),
    (163, 7),
    (164, 1),
    (165, 4),
    (182, 3),
    (183, 0),
    (200, 21),
];

/// Three outputs need their own source-length-sensitive relocation seeds.
/// Each selected value was independently admitted and checked in the VM;
/// these are witnesses, not a claim of exhaustive byte synthesis.
const ROTATED_TRIPLE_BYTE_SEEDS: &[(u8, usize)] = &[
    (3, 23),
    (4, 20),
    (5, 17),
    (6, 14),
    (7, 2),
    (8, 8),
    (9, 5),
    (11, 24),
    (18, 22),
    (19, 19),
    (20, 16),
    (21, 13),
    (22, 7),
    (23, 25),
    (24, 4),
    (25, 1),
    (144, 6),
    (145, 3),
    (146, 0),
    (251, 21),
    (252, 15),
];

/// Four outputs change every preceding source phase and loader data word.
/// Select only one independently witnessed short-phase prefix per byte.
const ROTATED_QUADRUPLE_BYTE_SEEDS: &[(u8, usize)] = &[
    (43, 0),
    (182, 1),
    (168, 2),
    (44, 3),
    (175, 4),
    (162, 5),
    (42, 6),
    (176, 7),
    (161, 8),
    (40, 9),
    (41, 12),
    (178, 13),
    (187, 14),
    (66, 15),
    (192, 16),
    (185, 17),
    (64, 18),
    (191, 19),
    (186, 20),
    (65, 21),
    (196, 22),
    (184, 23),
    (57, 24),
    (201, 25),
];

/// Five outputs have different positional decode and loader-expanded data.
/// This table keeps the first witness for each value from a 26-phase VM scan.
const ROTATED_QUINTUPLE_BYTE_SEEDS: &[(u8, usize)] = &[
    (10, 0),
    (7, 1),
    (24, 2),
    (9, 3),
    (23, 5),
    (8, 7),
    (22, 8),
    (142, 10),
    (21, 11),
    (6, 12),
    (141, 13),
    (140, 16),
    (4, 18),
    (139, 19),
    (12, 21),
    (138, 22),
    (25, 23),
    (137, 25),
];

/// Six-output loader expansion has its own shortest valid VM witnesses.
const ROTATED_SEXTUPLE_BYTE_SEEDS: &[(u8, usize)] = &[
    (47, 0),
    (175, 2),
    (42, 3),
    (41, 4),
    (177, 5),
    (40, 6),
    (176, 8),
    (162, 9),
    (178, 11),
    (66, 13),
    (200, 14),
    (64, 16),
    (65, 19),
    (190, 20),
    (186, 21),
    (63, 22),
    (191, 23),
    (185, 24),
    (61, 25),
];

/// Seven-output loader expansion has its own shortest valid VM witnesses.
const ROTATED_SEPTUPLE_BYTE_SEEDS: &[(u8, usize)] = &[
    (21, 0),
    (9, 1),
    (8, 2),
    (23, 3),
    (22, 6),
    (7, 7),
    (6, 10),
    (20, 12),
    (253, 13),
    (5, 14),
    (19, 15),
    (251, 16),
    (4, 17),
    (18, 18),
    (17, 21),
    (12, 22),
    (16, 24),
    (10, 25),
];

/// Eight outputs have their own verified short-prefix relocation witnesses.
/// Duplicate generated values retain only their first successful phase.
const ROTATED_OCTUPLE_BYTE_SEEDS: &[(u8, usize)] = &[
    (175, 0),
    (163, 1),
    (42, 2),
    (177, 3),
    (161, 4),
    (40, 5),
    (176, 6),
    (162, 7),
    (41, 8),
    (178, 9),
    (66, 10),
    (56, 11),
    (201, 12),
    (64, 13),
    (55, 14),
    (200, 15),
    (65, 16),
    (199, 18),
    (57, 19),
    (198, 21),
    (197, 24),
];

/// Nine outputs require a new positional layout and loader-resident word.
/// Each entry is the first verified phase for its byte in a 26-phase scan.
const ROTATED_NONUPLE_BYTE_SEEDS: &[(u8, usize)] = &[
    (1, 23),
    (2, 20),
    (3, 17),
    (4, 14),
    (5, 11),
    (6, 8),
    (7, 5),
    (9, 2),
    (10, 24),
    (11, 18),
    (18, 16),
    (19, 13),
    (20, 10),
    (21, 7),
    (22, 1),
    (23, 19),
    (142, 6),
    (143, 3),
    (144, 0),
    (251, 15),
    (252, 9),
];

/// Ten-output positions use independently verified loader-expanded data.
const ROTATED_DECUPLE_BYTE_SEEDS: &[(u8, usize)] = &[
    (40, 3),
    (41, 6),
    (42, 0),
    (55, 21),
    (56, 24),
    (57, 18),
    (64, 12),
    (65, 15),
    (66, 9),
    (161, 2),
    (162, 5),
    (176, 1),
    (178, 7),
    (182, 20),
    (183, 23),
    (184, 17),
    (185, 11),
    (186, 14),
    (187, 8),
    (191, 13),
    (192, 10),
    (193, 25),
    (196, 16),
    (200, 22),
    (201, 19),
];

/// Eleven-output positions are witnessed separately on the real guest VM.
/// Keep only the earliest safe phase for each distinct byte.
const ROTATED_UNDECUPLE_BYTE_SEEDS: &[(u8, usize)] = &[
    (4, 12),
    (6, 6),
    (7, 3),
    (8, 1),
    (9, 0),
    (10, 8),
    (12, 15),
    (21, 5),
    (22, 2),
    (24, 23),
    (25, 17),
    (135, 25),
    (136, 22),
    (137, 19),
    (138, 16),
    (139, 13),
    (140, 10),
];

/// Twelve-output positions are independently replayed on the real guest VM.
/// The first safe source phase is the only admitted seed per byte.
const ROTATED_DODECUPLE_BYTE_SEEDS: &[(u8, usize)] = &[
    (40, 0),
    (41, 3),
    (56, 7),
    (60, 25),
    (61, 19),
    (62, 22),
    (63, 16),
    (64, 10),
    (65, 13),
    (66, 6),
    (176, 2),
    (177, 12),
    (178, 5),
    (180, 24),
    (184, 23),
    (185, 18),
    (186, 15),
    (190, 14),
    (191, 17),
    (200, 8),
];

/// Thirteen outputs change the positional decode and loader-expanded data.
/// Only first-phased witnesses re-executed by the normative VM are admitted.
const ROTATED_TREDECUPLE_BYTE_SEEDS: &[(u8, usize)] = &[
    (22, 0),
    (7, 1),
    (21, 3),
    (6, 4),
    (252, 5),
    (20, 6),
    (5, 7),
    (19, 9),
    (251, 10),
    (4, 11),
    (18, 12),
    (9, 13),
    (17, 15),
    (12, 16),
    (8, 17),
    (16, 18),
    (10, 19),
    (15, 21),
    (14, 24),
];

/// Fourteen-output loader-expanded source has independently VM-checked seeds.
const ROTATED_FOURTEEN_BYTE_SEEDS: &[(u8, usize)] = &[
    (176, 0),
    (162, 1),
    (41, 2),
    (178, 3),
    (187, 4),
    (66, 5),
    (192, 6),
    (185, 7),
    (55, 8),
    (200, 9),
    (65, 10),
    (56, 11),
    (199, 12),
    (57, 13),
    (198, 15),
    (64, 17),
    (197, 18),
    (193, 21),
    (51, 22),
    (59, 23),
    (195, 24),
    (49, 25),
];

/// Fifteen-output witnesses omit the unsupported phase 20; no phase extrapolation.
const ROTATED_FIFTEEN_BYTE_SEEDS: &[(u8, usize)] = &[
    (142, 0),
    (21, 1),
    (6, 2),
    (141, 3),
    (10, 4),
    (140, 6),
    (4, 8),
    (251, 9),
    (18, 10),
    (3, 11),
    (11, 12),
    (23, 13),
    (2, 14),
    (22, 16),
    (1, 17),
    (8, 21),
    (255, 23),
];

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

type RotatedByteSeedTable = &'static [(u8, usize)];

// Each output count has a distinct positional decode and loader-expanded
// memory witness. The closed selector prevents a seed from leaking across
// source lengths before independent guest execution verifies the candidate.
const fn rotated_byte_seeds(outputs: usize) -> Option<RotatedByteSeedTable> {
    match outputs {
        1 => Some(ROTATED_BYTE_SEEDS),
        2 => Some(ROTATED_DOUBLE_BYTE_SEEDS),
        3 => Some(ROTATED_TRIPLE_BYTE_SEEDS),
        4 => Some(ROTATED_QUADRUPLE_BYTE_SEEDS),
        5 => Some(ROTATED_QUINTUPLE_BYTE_SEEDS),
        6 => Some(ROTATED_SEXTUPLE_BYTE_SEEDS),
        7 => Some(ROTATED_SEPTUPLE_BYTE_SEEDS),
        8 => Some(ROTATED_OCTUPLE_BYTE_SEEDS),
        9 => Some(ROTATED_NONUPLE_BYTE_SEEDS),
        10 => Some(ROTATED_DECUPLE_BYTE_SEEDS),
        11 => Some(ROTATED_UNDECUPLE_BYTE_SEEDS),
        12 => Some(ROTATED_DODECUPLE_BYTE_SEEDS),
        13 => Some(ROTATED_TREDECUPLE_BYTE_SEEDS),
        14 => Some(ROTATED_FOURTEEN_BYTE_SEEDS),
        15 => Some(ROTATED_FIFTEEN_BYTE_SEEDS),
        _ => None,
    }
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

/// Emits verified guest code for zero outputs followed by latest-byte I/O.
///
/// The sole source function must begin with one `MaterializeU8(0)` and at
/// least one output of that SSA byte before the first successful input.
/// Once any input executes, the accumulator changes and every subsequent
/// output must name exactly the *latest* input SSA result. At least one input
/// and an output of an input are required; the last operation is `ReturnVoid`.
/// The zero materialization is proven by initial A=0, not host computation;
/// each output and input is a real guest instruction. EOF, failures, memory,
/// arithmetic, and guest ABI state remain outside this bounded contract.
///
/// # Errors
///
/// Rejects malformed source, wrong profile, stale SSA, unsupported effects,
/// and unsafe or excessively long address-sensitive source.
pub fn encode_zero_prefixed_latest_byte_trace(
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
    let Some((TernaryOperation::MaterializeU8 { result, scalar, .. }, effects)) =
        instructions.split_first()
    else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    if scalar.bits() != 0 {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    }
    let mut last_input = None;
    let mut initial_outputs = false;
    let mut subsequent_outputs = false;
    let mut operations = Vec::with_capacity(effects.len().saturating_add(1));
    for effect in effects {
        if let TernaryOperation::ByteInput { result: latest, .. } = effect {
            last_input = Some(*latest);
            operations.push(LinearOpcode::InputWord);
        } else if let TernaryOperation::ByteOutput { value, .. } = effect {
            let valid = last_input.map_or(value == result, |latest| *value == latest);
            if !valid {
                return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
            }
            if last_input.is_some() {
                subsequent_outputs = true;
            } else {
                initial_outputs = true;
            }
            operations.push(LinearOpcode::OutputByte);
        } else {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        }
    }
    if !initial_outputs || last_input.is_none() || !subsequent_outputs {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    }
    operations.push(LinearOpcode::Halt);
    encode_linear_layout(profile, &operations).map_err(ByteEchoBridgeError::Layout)
}

/// Emits guest I/O while proving exact byte-bitcast SSA aliases remain live.
///
/// Only eight-bit signed/unsigned representation-preserving casts are allowed.
/// Every new input invalidates previous aliases; casts emit no guest code.
/// The trace needs at least one input, cast and output, and final void return.
///
/// # Errors
/// Rejects noncanonical operations, stale aliases, other effects or bad layout.
pub fn encode_latest_byte_identity_trace(
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
    let Some((TernaryOperation::ReturnVoid { .. }, effects)) = function.operations.split_last()
    else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    if effects.len() > 4096 {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    }
    let mut aliases = BTreeSet::new();
    let mut seen_cast = false;
    let mut seen_output = false;
    let mut operations = Vec::with_capacity(effects.len().saturating_add(1));
    for effect in effects {
        if let TernaryOperation::ByteInput { result, .. } = effect {
            aliases.clear();
            _ = aliases.insert(*result);
            operations.push(LinearOpcode::InputWord);
        } else if let TernaryOperation::ByteOutput { value, .. } = effect {
            if !aliases.contains(value) {
                return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
            }
            seen_output = true;
            operations.push(LinearOpcode::OutputByte);
        } else if let Some((result, value)) = byte_bitcast_operands(effect) {
            if !aliases.contains(&value) {
                return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
            }
            _ = aliases.insert(result);
            seen_cast = true;
        } else {
            return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
        }
    }
    if aliases.is_empty() || !seen_cast || !seen_output {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    }
    operations.push(LinearOpcode::Halt);
    encode_linear_layout(profile, &operations).map_err(ByteEchoBridgeError::Layout)
}

const fn byte_bitcast_operands(operation: &TernaryOperation) -> Option<(u32, u32)> {
    let (TernaryOperation::BitcastI8ToI8 { result, value, .. }
    | TernaryOperation::BitcastI8ToU8 { result, value, .. }
    | TernaryOperation::BitcastU8ToI8 { result, value, .. }
    | TernaryOperation::BitcastU8ToU8 { result, value, .. }) = operation
    else {
        return None;
    };
    Some((*result, *value))
}

/// Emits a nonzero `u8` one to twelve times using guest data rotation.
///
/// Accepts one `MaterializeU8` with one to twelve same-SSA `ByteOutput`s and
/// `ReturnVoid` for the current profile. A bounded source-address-specific
/// sequence of no-ops, `j`, `*`, `<`, and `v` selects a loader-expanded
/// memory word; the guest `*` changes its own accumulator, not the host.
/// This admits only the witness values above and checks every proposed
/// result against independent VM execution before returning a source.
///
/// # Errors
///
/// Refuses invalid shape/provenance, foreign profiles, unsupported literals,
/// overlapping data/code, wrong output, guest input, or nontermination.
pub fn encode_rotated_byte_literal(
    program: &TernaryProgram,
    profile: &'static ProfileDescriptor,
) -> Result<LinearLayout, ByteEchoBridgeError> {
    validate_ternary_program(program).map_err(ByteEchoBridgeError::InvalidProgram)?;
    if program.target_profile != profile.id()
        || profile.id() != current_profile().id()
        || profile.fingerprint() != current_profile().fingerprint()
    {
        return Err(ByteEchoBridgeError::ProfileMismatch);
    }
    let [function] = program.functions.as_slice() else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    let Some((TernaryOperation::ReturnVoid { .. }, effects)) = function.operations.split_last()
    else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    let Some((TernaryOperation::MaterializeU8 { result, scalar, .. }, outputs)) =
        effects.split_first()
    else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    if outputs.is_empty()
        || outputs.iter().any(|effect| {
            !matches!(effect, TernaryOperation::ByteOutput { value, .. } if value == result)
        })
    {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    }
    let Some(seeds) = rotated_byte_seeds(outputs.len()) else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    let Some((byte, padding)) = seeds
        .iter()
        .copied()
        .find(|(byte, _)| *byte == scalar.bits())
    else {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    };
    let mut operations = vec![LinearOpcode::NoOperation; padding];
    operations.extend([LinearOpcode::RelocateDataPointer, LinearOpcode::RotateData]);
    operations.extend(repeat_n(LinearOpcode::OutputByte, outputs.len()));
    operations.push(LinearOpcode::Halt);
    let layout = encode_linear_layout(profile, &operations).map_err(ByteEchoBridgeError::Layout)?;
    let mut vm = ProfileMachine::from_source(profile, layout.source(), Vec::new())
        .map_err(|_error| ByteEchoBridgeError::UnsupportedEffectTrace)?;
    if !matches!(vm.run(operations.len()),
        Ok(RunOutcome::Terminated { steps, .. }) if steps == operations.len())
        || vm.input_consumed() != 0
        || vm.output().len() != outputs.len()
        || vm.output().iter().any(|actual| *actual != byte)
    {
        return Err(ByteEchoBridgeError::UnsupportedEffectTrace);
    }
    Ok(layout)
}
