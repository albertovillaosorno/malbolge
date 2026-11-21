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
//!
//! The linker must still create/verify all six operand cells, arrange the
//! six `p` instructions and their data-pointer entry, and connect branches
//! without overwriting live source data. The result cells are D+2 and D+5,
//! **not contiguous**: a later, separately verified transfer is required to
//! satisfy the source-C32 adjacent two-cell frame contract.

use malbolge::{ProfileDescriptor, current_profile};

use super::typed_cfg_adapter::state_storage::encode_i32_cells;

const TRITS_PER_WORD: u8 = 15;
const TRIT_RADIX: u32 = 3;

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
