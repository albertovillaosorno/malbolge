// Copyright:
//   - Copyright © 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - Apache-2.0
// Confidential:
//   - false
// License-File:
//   - LICENSE
// Boundary-Contract:
// - Owns:
//   - Exhaustive finite checks for three-trit scratch patch planning.
// - Must-Not:
//   - Substitute emitter costs for normative guest execution evidence.
// - Allows:
//   - Inputs: all 729 chunk transitions and emitted mask paths.
//   - Outputs: independent scalar transition and route-cost checks.
//   - Side effects: none.
// - Split-When:
//   - A different scratch mask width requires separate checks.
// - Merge-When:
//   - The general scratch transformation planner owns these checks.

use malbolge::current_profile;

use super::super::super::super::TapeBounds;
use super::{
    CHUNK_NEXT, Emitter, apply_chunk_column, fast_column_cost,
    fast_patch_columns,
};

fn scalar_column(mut value: u32, mut column: u32) -> u32 {
    let mut result = 0u32;
    let mut place = 1u32;
    for _ in 0..3u32 {
        // The composition of the mask fold and the all-two fold,
        // independently derived from the scalar ternary truth table.
        let digit: u32 = match (value.rem_euclid(3), column.rem_euclid(3)) {
            (0 | 1, 0) | (2, 2) => 2,
            (2, 0 | 1) | (1, 2) => 1,
            _ => 0,
        };
        result = result.saturating_add(digit.saturating_mul(place));
        value = value.div_euclid(3);
        column = column.div_euclid(3);
        place = place.saturating_mul(3);
    }
    result
}

fn emitted_cost(column: u32) -> Result<u32, String> {
    if column == 26 {
        return Ok(0);
    }
    let mut emitter = Emitter {
        data: CHUNK_NEXT,
        profile: current_profile(),
        source: Vec::new(),
        source_cells: 256,
        tape_bounds: TapeBounds {
            limit: 7_176_900,
            start: 7_174_417,
        },
    };
    apply_chunk_column(&mut emitter, column, true)
        .map_err(|error| format!("column {column}: {error:?}"))?;
    if emitter.data != CHUNK_NEXT {
        return Err(format!("column {column} changes scratch endpoint"));
    }
    u32::try_from(emitter.source.len()).map_err(|error| error.to_string())
}

#[test]
fn recurrent_chunk_patch_costs_match_emission() -> Result<(), String> {
    for column in 0..27u32 {
        let emitted = emitted_cost(column)?;
        if fast_column_cost(column) != emitted {
            return Err(format!("column {column} costs {emitted} steps"));
        }
    }
    Ok(())
}

fn verify_patch(before: u32, after: u32) -> Result<(), String> {
    let selected = fast_patch_columns(before, after);
    let [first, second] = selected;
    if scalar_column(scalar_column(before, first), second) != after {
        return Err(format!("invalid patch {before} -> {after}"));
    }
    let selected_cost =
        fast_column_cost(first).saturating_add(fast_column_cost(second));
    for alternative_first in 0..27u32 {
        let middle = scalar_column(before, alternative_first);
        for alternative_second in 0..27u32 {
            if scalar_column(middle, alternative_second) != after {
                continue;
            }
            let cost = fast_column_cost(alternative_first)
                .saturating_add(fast_column_cost(alternative_second));
            if (cost, [alternative_first, alternative_second])
                < (selected_cost, selected)
            {
                return Err(format!("nonminimal patch {before} -> {after}"));
            }
        }
    }
    Ok(())
}

#[test]
fn recurrent_chunk_patch_minimizes_all_two_mask_transitions()
-> Result<(), String> {
    for before in 0..27u32 {
        for after in 0..27u32 {
            verify_patch(before, after)?;
        }
    }
    Ok(())
}
