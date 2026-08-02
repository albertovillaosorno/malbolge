// Copyright:
//   - Copyright (c) 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - MIT
// Confidential:
//   - false
// License-File:
//   - LICENSE-MIT
//
// Boundary-Contract:
// - Owns:
//   - Pure profile-width output and ternary crazy arithmetic helpers.
// - Must-Not:
//   - Own machine state, instruction dispatch, I/O storage, or host policy.
// - Allows:
//   - Inputs: in-domain profile words and explicit ternary widths.
//   - Outputs: deterministic low bytes and profile-width crazy results.
//   - Side effects: none.
// - Split-When:
//   - Another arithmetic family requires independently generated tables.
// - Merge-When:
//   - Profile-machine transitions become the sole arithmetic authority.
// - Summary:
//   - Pure arithmetic shared by profile loading and execution.
// - Description:
//   - Isolates width-dependent arithmetic from mutable machine transitions.
// - Usage:
//   - Called by the profile machine during load and committed execution.
// - Defaults:
//   - Saturating construction preserves deterministic in-domain behavior.
//

//! Pure profile-width arithmetic used by loading and execution.

use crate::{CRAZY_CHUNK_TRITS, crazy_chunk_lookup};

const OUTPUT_MODULUS: u32 = 256;
pub(crate) const TERNARY_RADIX: u32 = 3;

/// Returns the normative output byte for one profile-width word.
///
/// This is the exact unsigned value modulo 256 used by profile execution.
#[must_use]
pub fn profile_low_byte(value: u32) -> u8 {
    let reduced = value.rem_euclid(OUTPUT_MODULUS);
    u8::try_from(reduced).ok().unwrap_or(0)
}

/// Applies the canonical Malbolge crazy operation to two profile words.
///
/// The caller supplies the canonical profile width in ternary digits. Values
/// outside that profile domain are outside this helper's contract.
#[must_use]
pub fn profile_crazy(mut data: u32, mut accumulator: u32, trits: u8) -> u32 {
    let mut place = 1u32;
    let mut remaining_trits = trits;
    let mut result = 0u32;
    while remaining_trits > 0 {
        let chunk_trits = remaining_trits.min(CRAZY_CHUNK_TRITS);
        let chunk_modulus = ternary_modulus(chunk_trits);
        let data_chunk = u16::try_from(data.rem_euclid(chunk_modulus))
            .ok()
            .unwrap_or(0);
        let accumulator_chunk =
            u16::try_from(accumulator.rem_euclid(chunk_modulus))
                .ok()
                .unwrap_or(0);
        let chunk =
            u32::from(crazy_chunk_lookup(data_chunk, accumulator_chunk))
                .rem_euclid(chunk_modulus);
        result = result.saturating_add(chunk.saturating_mul(place));
        data = data.div_euclid(chunk_modulus);
        accumulator = accumulator.div_euclid(chunk_modulus);
        place = place.saturating_mul(chunk_modulus);
        remaining_trits = remaining_trits.saturating_sub(chunk_trits);
    }
    result
}

const fn ternary_modulus(trits: u8) -> u32 {
    let mut value = 1u32;
    let mut index = 0u8;
    while index < trits {
        value = value.saturating_mul(TERNARY_RADIX);
        index = index.saturating_add(1);
    }
    value
}
