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
//   - Profile-bound, six-crazy literal materialization for two C32 words.
// - Must-Not:
//   - Pretend seeded data operands are source-loaded guest code or a linker.
// - Allows:
//   - Inputs: one exact C32 bit pattern and canonical current N15 profile.
//   - Outputs: six exact guest data operands and two result-step offsets.
//   - Side effects: none.
// - Split-When:
//   - The physical guest instruction linker owns code/data operand placement.
// - Merge-When:
//   - A general independently checked C32 literal writer replaces this plan.
// - Summary:
//   - A constant C32 result does not depend on the previous accumulator.

//! Pre-link literal C32 guest-write recipe, not executable source emission.
//!
//! Every three consecutive physical `p` instructions, with the exact three
//! supplied operands at successive data addresses, force one 15-trit target
//! word regardless of the incoming accumulator. The third data cell becomes
//! that target word *by guest execution*, even if the first two cells change.
//! Two groups force the canonical low/high words of a C32 bit pattern.
//! A separate two-rotate recipe can write the same C32 words *adjacently*,
//! provided the target-specific inverse-rotated data seeds already exist.
//!
//! The linker must still create/verify all six operand cells, arrange the
//! six `p` instructions and their data-pointer entry, and connect branches
//! without overwriting live source data. The result cells are D+2 and D+5,
//! **not contiguous**: a later, separately verified transfer is required to
//! satisfy the source-C32 adjacent two-cell frame contract.

use std::iter::repeat_n;

use malbolge::{ProfileDescriptor, current_profile};

use super::typed_cfg_adapter::state_storage::encode_i32_cells;

const TRITS_PER_WORD: u8 = 15;
const TRIT_RADIX: u32 = 3;
const HIGH_TRIT_WEIGHT: u32 = 4_782_969;

/// An unfulfilled profile precondition for the current N15 C32 encoding.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum C32LiteralCrazyError {
    /// The requested descriptor is not the canonical current N15 profile.
    UnsupportedProfile,
}

/// Six preinitialized data operands for consecutive physical `p` operations.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct C32LiteralCrazyPlan {
    /// Original C32 bits, including the exact signed EOF pattern if requested.
    pub bits: u32,
    /// Six initial N15 operand words, in the same order as the six `p` sites.
    pub operands: [u32; 6],
    /// Offsets from entry D for low/high result words, **not** adjacent.
    pub result_data_offsets: [u32; 2],
    /// Zero-based executed `p` step indices producing low/high C32 results.
    pub result_steps: [usize; 2],
    /// Canonical low/high C32 guest words after those steps.
    pub target_cells: [u32; 2],
}

/// Failure to turn a C32 literal recipe into a fully graphical N15 source.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum C32LiteralLoadedSourceError {
    /// No admitted source tail and graphical no-op prefix supplies the seeds.
    NoLoadableSeed,
    /// Only the canonical current 15-trit profile has this loader geometry.
    UnsupportedProfile,
}

/// Unsupported precondition for literal adjacent rotate materialization.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum C32LiteralRotateError {
    /// The requested descriptor is not canonical current N15.
    UnsupportedProfile,
}

/// The current-profile, seed-dependent adjacent C32 rotate recipe.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct C32LiteralRotatePlan {
    /// Original C32 bits, including the signed EOF bit pattern.
    pub bits: u32,
    /// Required two consecutive preinitialized data words.
    pub initial_data_words: [u32; 2],
    /// Offsets from the incoming D: the two **adjacent** source-frame cells.
    pub result_data_offsets: [u32; 2],
    /// Zero-based positions of the two `*` instructions producing the words.
    pub result_steps: [usize; 2],
    /// Exact low/high N15 words of the canonical C32 representation.
    pub target_cells: [u32; 2],
}

#[derive(Clone, Copy)]
enum LiteralDataOp {
    Crazy,
    Rotate,
}

impl LiteralDataOp {
    const fn opcode(self) -> super::LinearOpcode {
        match self {
            Self::Crazy => super::LinearOpcode::CrazyData,
            Self::Rotate => super::LinearOpcode::RotateData,
        }
    }

    fn result(
        self,
        data: u32,
        accumulator: u32,
        profile: &ProfileDescriptor,
    ) -> u32 {
        match self {
            Self::Crazy => {
                malbolge::profile_crazy(data, accumulator, profile.word_trits())
            },
            Self::Rotate => {
                malbolge::profile_rotate(data, profile.word_modulus())
            },
        }
    }
}

/// Materialize a constant target after three `p` instructions with a
/// **preinitialized** consecutive data-word region. This operation is
/// independent of the previous full 15-trit accumulator, by construction.
#[expect(
    clippy::arithmetic_side_effects,
    clippy::integer_division_remainder_used,
    reason = "fixed-width positional ternary operand synthesis"
)]
fn operands_for_word(mut target: u32) -> [u32; 3] {
    let mut middle = 0;
    let mut last = 0;
    let mut place = 1;
    for _ in 0..TRITS_PER_WORD {
        // Independent three-state ternary p truth table, with its first
        // operand always zero. The resulting final digit is constant for
        // each of the three possible incoming accumulator digits.
        let (middle_digit, last_digit) = match target % TRIT_RADIX {
            0 => (2, 0),
            1 => (2, 2),
            _ => (0, 2),
        };
        middle += middle_digit * place;
        last += last_digit * place;
        target /= TRIT_RADIX;
        place *= TRIT_RADIX;
    }
    [0, middle, last]
}

/// Plan exact C32 low/high literals as six consecutive guest crazy writes.
///
/// Successful signed `getchar()` bytes, including `0xff`, are C32 values
/// `0..255`. A true C23 EOF instead uses the distinct bit pattern
/// `u32::MAX`. The caller chooses that source-known value; this planner
/// never guesses which branch of an input-dependent C program executed.
///
/// # Errors
///
/// Refuses any profile other than canonical current N15. A complete target
/// program still needs verified operand data loading and code/control layout.
pub fn plan_c32_literal_crazy_writes(
    profile: &ProfileDescriptor,
    bits: u32,
) -> Result<C32LiteralCrazyPlan, C32LiteralCrazyError> {
    if profile != current_profile() {
        return Err(C32LiteralCrazyError::UnsupportedProfile);
    }
    let target_cells = encode_i32_cells(bits);
    let low = operands_for_word(target_cells[0]);
    let high = operands_for_word(target_cells[1]);
    Ok(C32LiteralCrazyPlan {
        bits,
        operands: [low[0], low[1], low[2], high[0], high[1], high[2]],
        result_data_offsets: [2, 5],
        result_steps: [2, 5],
        target_cells,
    })
}

/// Plan two adjacent guest `*` writes of a literal C32 value.
///
/// Each `*` rotates its own data cell right by one trit, stores that rotated
/// word back to the *same* data cell, and updates A. Because it does not read
/// incoming A, two consecutive operations recover the two target words in
/// adjacent cells regardless of the initial register state. The required
/// initial seeds are the inverse one-trit rotations, not target words.
///
/// The plan **does not allocate or initialize** those full-width guest seeds,
/// encode instructions, select a runtime branch, or link source-C storage.
/// A loader or verified guest precursor must first construct both seeds at
/// precisely the two data addresses where the rotations will execute.
///
/// # Errors
///
/// Noncanonical current N15 profiles are unsupported.
#[expect(
    clippy::arithmetic_side_effects,
    clippy::integer_division_remainder_used,
    reason = "fixed-width one-trit inverse rotation over canonical N15"
)]
pub fn plan_c32_literal_rotate_writes(
    profile: &ProfileDescriptor,
    bits: u32,
) -> Result<C32LiteralRotatePlan, C32LiteralRotateError> {
    if profile != current_profile() {
        return Err(C32LiteralRotateError::UnsupportedProfile);
    }
    let target_cells = encode_i32_cells(bits);
    let undo_rotate = |target: u32| {
        // Output = seed/3 + (seed%3)*3^14; inverse is exact on all 15 trits.
        (target % HIGH_TRIT_WEIGHT) * TRIT_RADIX
            + target.div_euclid(HIGH_TRIT_WEIGHT)
    };
    Ok(C32LiteralRotatePlan {
        bits,
        initial_data_words: [
            undo_rotate(target_cells[0]),
            undo_rotate(target_cells[1]),
        ],
        result_data_offsets: [0, 1],
        result_steps: [0, 1],
        target_cells,
    })
}

/// Return an exact source-loaded adjacent-C32 constant write for a fixed
/// pair of executable data operations. All output values are calculated
/// from the known loader and the initial zero accumulator, never from C
/// input or a seeded VM memory snapshot.
#[expect(
    clippy::too_many_lines,
    clippy::excessive_nesting,
    reason = "bounded graphical decoder and loader precondition search"
)]
fn build_loader_ops(
    profile: &ProfileDescriptor,
    bits: u32,
    operations: [LiteralDataOp; 2],
    live_input: bool,
) -> Result<Vec<u8>, C32LiteralLoadedSourceError> {
    use super::LinearOpcode as Opcode;
    if profile != current_profile() {
        return Err(C32LiteralLoadedSourceError::UnsupportedProfile);
    }
    if live_input && !matches!(operations[0], LiteralDataOp::Rotate) {
        return Err(C32LiteralLoadedSourceError::NoLoadableSeed);
    }
    let targets = encode_i32_cells(bits);
    for noops in 0..94usize {
        let mut source = Vec::with_capacity(
            noops.saturating_add(5 + usize::from(live_input)),
        );
        let mut admissible = true;
        for operation in repeat_n(Opcode::NoOperation, noops)
            .chain(live_input.then_some(Opcode::InputWord))
            .chain([
                Opcode::RelocateDataPointer,
                operations[0].opcode(),
                operations[1].opcode(),
                Opcode::Halt,
            ])
        {
            match super::unique_graphical_cell(profile, operation, source.len())
            {
                Ok(byte) => source.push(byte),
                Err(_error) => {
                    admissible = false;
                    break;
                },
            }
        }
        if !admissible {
            continue;
        }
        let Some(&jump_byte) = source.get(noops + usize::from(live_input))
        else {
            continue;
        };
        let data_base = usize::from(jump_byte).saturating_add(1);
        if data_base <= source.len()
            || data_base.saturating_add(1)
                >= usize::try_from(profile.memory_words()).unwrap_or(0)
        {
            continue;
        }
        for last in 33..=126u8 {
            if super::unique_graphical_cell(
                profile,
                Opcode::SkippedDataByte { byte: u32::from(last) },
                source.len(),
            ) != Ok(last)
            {
                continue;
            }
            source.push(last);
            let first_seed =
                super::unwritten_loader_word(&source, data_base, profile);
            let second_seed = super::unwritten_loader_word(
                &source,
                data_base.saturating_add(1),
                profile,
            );
            if let (Ok(first), Ok(second)) = (first_seed, second_seed) {
                // A reached `*` erases an unknown input accumulator;
                // the checked precondition forbids `p` in that slot.
                let first_result = operations[0].result(first, 0, profile);
                let second_result =
                    operations[1].result(second, first_result, profile);
                if [first_result, second_result] == targets {
                    return Ok(source);
                }
            }
            _ = source.pop();
        }
    }
    Err(C32LiteralLoadedSourceError::NoLoadableSeed)
}

/// Construct a bounded source-loaded `o*; j; *; *; v` C32 literal write.
///
/// Tries 0..93 reached no-op positions and one graphical data suffix.
/// Both adjacent seeds must arise from the actual six-phase loader.
/// The source is only a candidate; normative VM acceptance remains mandatory.
///
/// # Errors
///
/// Refuses other profiles or any literal unrepresentable by the fixed
/// source-loaded two-rotate grammar.
pub fn build_c32_literal_loader_rotate_source(
    profile: &ProfileDescriptor,
    bits: u32,
) -> Result<Vec<u8>, C32LiteralLoadedSourceError> {
    build_loader_ops(
        profile,
        bits,
        [LiteralDataOp::Rotate, LiteralDataOp::Rotate],
        false,
    )
}

/// Construct a bounded adjacent C32 literal from two real `p`/`*` writes.
///
/// Tries exact `**`, `p*`, `*p`, then `pp` instruction templates, each under
/// the same 94-prefix and 94-tail bound as the pure rotate emitter. Every
/// physical data operand is derived solely from the graphical source loader;
/// `p` uses the actual evolving accumulator, initially zero. The candidate
/// does not read input, select C branches, write C SSA state, or perform a
/// checksum. Independent guest-VM verification is required before any
/// compiled-program linker may accept it.
///
/// # Errors
///
/// Refuses other profiles and any target not constructible in the closed
/// four-template grammar. In particular signed EOF is not synthesized here.
pub fn build_c32_literal_loader_arithmetic_source(
    profile: &ProfileDescriptor,
    bits: u32,
) -> Result<Vec<u8>, C32LiteralLoadedSourceError> {
    use LiteralDataOp::{Crazy, Rotate};
    if profile != current_profile() {
        return Err(C32LiteralLoadedSourceError::UnsupportedProfile);
    }
    for operations in [[Rotate, Rotate], [Crazy, Rotate], [Rotate, Crazy], [
        Crazy, Crazy,
    ]] {
        if let Ok(source) = build_loader_ops(profile, bits, operations, false) {
            return Ok(source);
        }
    }
    Err(C32LiteralLoadedSourceError::NoLoadableSeed)
}

/// Source-load two adjacent C32 literal words after a real guest input.
///
/// The reached `/` changes A to a byte or the target-profile EOF sentinel.
/// The first data operation must be `*`, which overwrites A independently
/// of that input; the second may be `*` or `p` using the new known A. Both
/// cells come from the actual graphical loader and are written in guest
/// memory after a `j` relocation. This is a bounded constant-state building
/// block, not C23 signed input conversion, source-C operation linkage, or
/// a checksum implementation. The input itself is consumed but not stored.
///
/// # Errors
///
/// Refuses noncanonical N15 profiles or literals outside the exact two-
/// template, 94-prefix and 94-tail physical-source grammar.
pub fn build_c32_literal_after_input_source(
    profile: &ProfileDescriptor,
    bits: u32,
) -> Result<Vec<u8>, C32LiteralLoadedSourceError> {
    use LiteralDataOp::{Crazy, Rotate};
    if profile != current_profile() {
        return Err(C32LiteralLoadedSourceError::UnsupportedProfile);
    }
    for operations in [[Rotate, Rotate], [Rotate, Crazy]] {
        if let Ok(source) = build_loader_ops(profile, bits, operations, true) {
            return Ok(source);
        }
    }
    Err(C32LiteralLoadedSourceError::NoLoadableSeed)
}
