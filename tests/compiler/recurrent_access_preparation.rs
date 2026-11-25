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
//   - Finite inert-suffix lower bounds for recurrent access restoration.
// - Must-Not:
//   - Replace normative guest replay or general source-frame admission.
// - Allows:
//   - Inputs: canonical checksum access shapes and all 94 code phases.
//   - Outputs: independent minimum jump and instruction counts.
//   - Side effects: none.
// - Split-When:
//   - A new recurrent restoration strategy needs different invariants.
// - Merge-When:
//   - General physical envelope scheduling owns the same finite proof.

use malbolge::{
    current_profile, decode_profile_instruction, encrypt_profile_cell,
};

use super::{AccessBlock, LinearOpcode, MAX_JUMPS};

type RestorationCost = (usize, usize);
type ShapePhase = (&'static [LinearOpcode], u32);

// The first count is the number of stored route pointers; the second
// is the number of executed route instructions (including transfers).
// Each earlier suffix jump must consume a distinct inert phase of the
// current cell. Additional jumps targeting this cell are unconstrained
// by its opcode, but the final encrypted character must equal the
// original. This gives an independent lower bound, without constructing
// a jump schedule or using the recursive production scheduler.
fn minimum_cell_count(
    original: u32,
    address: u32,
    prefix_count: usize,
) -> Option<usize> {
    let mut current = encrypt_profile_cell(original)?;
    let mut inert = 0usize;
    for count in 0..=MAX_JUMPS {
        if current == original && inert >= prefix_count {
            return Some(count);
        }
        let decoded = decode_profile_instruction(current, address)?;
        if !b"ji*p/<v".contains(&decoded) {
            inert = inert.saturating_add(1);
        }
        current = encrypt_profile_cell(current)?;
    }
    None
}

fn minimum_restoration(block: &AccessBlock) -> Option<RestorationCost> {
    let mut prefix = 0usize;
    let mut words = 0usize;
    for (offset, &cell) in block.cells.iter().enumerate() {
        let address = block.start.checked_add(u32::try_from(offset).ok()?)?;
        prefix = minimum_cell_count(u32::from(cell), address, prefix)?;
        words = words.checked_add(prefix)?;
    }
    Some((prefix, words))
}

fn emitted_restoration(block: &AccessBlock) -> Option<RestorationCost> {
    let jumps = block.preparation(false).ok()?;
    let words = jumps.iter().try_fold(0usize, |sum, jump| {
        sum.checked_add(usize::try_from(jump.words).ok()?)
    })?;
    Some((jumps.len(), words))
}

fn check_phases(
    operations: &[LinearOpcode],
    selected: u32,
) -> Result<(), String> {
    let mut best = usize::MAX;
    let mut retained = None;
    for phase in 0..94u32 {
        let block = AccessBlock::from_operations(
            current_profile(),
            phase,
            (0, 0),
            operations,
        )
        .map_err(|error| format!("phase {phase}: {error:?}"))?;
        let minimum = minimum_restoration(&block);
        let emitted = emitted_restoration(&block);
        if minimum != emitted {
            return Err(format!(
                "phase {phase} cost {emitted:?}, lower bound {minimum:?}"
            ));
        }
        if let Some((_, words)) = minimum {
            best = best.min(words);
            if phase == selected {
                retained = Some(words);
            }
        }
    }
    if retained != Some(best) {
        return Err(format!(
            "phase {selected} costs {retained:?}, minimum is {best}"
        ));
    }
    Ok(())
}

#[test]
fn recurrent_access_restoration_meets_inert_suffix_lower_bound()
-> Result<(), String> {
    use LinearOpcode::{
        CrazyData as Crazy, InputWord as Input, NoOperation as Noop,
        RelocateDataPointer as Relocate, RotateData as Rotate,
    };
    let shapes: [ShapePhase; 13] = [
        (&[Relocate, Relocate], 92),
        (&[Relocate, Input, Relocate], 74),
        (&[Relocate, Noop, Crazy, Relocate], 58),
        (&[Relocate, Crazy, Noop, Relocate], 93),
        (&[Relocate, Crazy, Noop, Noop, Relocate], 93),
        (&[Relocate, Crazy, Noop, Noop, Noop, Relocate], 93),
        (&[Relocate, Rotate, Relocate], 29),
        (&[Relocate, Crazy, Noop, Noop, Noop, Noop, Relocate], 93),
        (
            &[Relocate, Crazy, Noop, Noop, Noop, Noop, Noop, Relocate],
            93,
        ),
        (&[Relocate, Relocate, Relocate, Crazy, Crazy, Relocate], 67),
        (
            &[Relocate, Relocate, Relocate, Noop, Crazy, Crazy, Relocate],
            83,
        ),
        (
            &[
                Relocate, Relocate, Relocate, Relocate, Crazy, Crazy, Relocate,
            ],
            72,
        ),
        (&[Relocate, Rotate, Noop, Noop, Noop, Relocate], 29),
    ];
    for (operations, selected) in shapes {
        check_phases(operations, selected)?;
    }
    Ok(())
}
