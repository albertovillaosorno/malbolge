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
//   - Classic position-dependent decode and post-step encryption tables.
// - Must-Not:
//   - Execute machine state transitions or select target profiles.
// - Allows:
//   - Inputs: classic/profile-width cells and exact code-pointer positions.
//   - Outputs: decoded instruction bytes and encrypted cell values.
//   - Side effects: none.
// - Split-When:
//   - Split when another instruction alphabet gains independent tables.
// - Merge-When:
//   - Merge when another module owns the same classic translation boundary.
// - Summary:
//   - Domain-local Malbolge instruction translation tables.
// - Description:
//   - Keeps decode and encryption out of the composition root.
// - Usage:
//   - Used by classic loading/execution and profile-driven execution.
// - Defaults:
//   - Non-graphical or out-of-table cells return no translation.
//

//! Domain-local classic Malbolge instruction translation.

use crate::word::Word;

const DECODE_TABLE_LEN: usize = 94;
const GRAPHICAL_START: u32 = 33;
const XLAT1: &[u8; DECODE_TABLE_LEN] =
    b"+b(29e*j1VMEKLyC})8&m#~W>qxdRp0wkrUo[D7,XTcA\"lI\
.v%{gJh4G\\-=O@5`_3i<?Z';FNQuY]szf$!BS/|t:Pn6^Ha";
const XLAT2: &[u8; DECODE_TABLE_LEN] =
    b"5z]&gqtyfr$(we4{WP)H-Zn,[%\\3dL+Q;>U!pJS72FhOA1C\
B6v^=I_0/8|jsb9m<.TVac`uY*MK'X~xDl}REokN:#?G\"i@";

/// Decodes one classic instruction cell at its exact code-pointer position.
///
/// Returns `None` when `cell` is outside graphical ASCII. Graphical cells use
/// the normative position-dependent Malbolge translation table.
#[must_use]
pub fn decode_instruction(cell: Word, code_pointer: Word) -> Option<u8> {
    if !cell.is_graphical() {
        return None;
    }
    let phase = usize::from(code_pointer.value()).rem_euclid(DECODE_TABLE_LEN);
    decode_at_phase(u32::from(cell.value()), phase)
}

fn decode_at_phase(cell: u32, phase: usize) -> Option<u8> {
    let cell_offset =
        usize::try_from(cell.saturating_sub(GRAPHICAL_START)).ok()?;
    let combined = cell_offset.saturating_add(phase);
    let translation = if combined >= DECODE_TABLE_LEN {
        combined.saturating_sub(DECODE_TABLE_LEN)
    } else {
        combined
    };
    XLAT1.get(translation).copied()
}

#[expect(
    clippy::redundant_pub_crate,
    reason = "shared by sibling domain modules through the crate root"
)]
pub(crate) fn decode_profile_value(cell: u32, code_pointer: u32) -> Option<u8> {
    if !(33..=126).contains(&cell) {
        return None;
    }
    let phase = code_pointer.rem_euclid(u32::try_from(DECODE_TABLE_LEN).ok()?);
    decode_at_phase(cell, usize::try_from(phase).ok()?)
}

#[expect(
    clippy::redundant_pub_crate,
    reason = "shared by sibling domain modules through the crate root"
)]
pub(crate) fn encrypt(cell: Word) -> Option<Word> {
    let index =
        usize::try_from(u32::from(cell.value()).checked_sub(GRAPHICAL_START)?)
            .ok()?;
    XLAT2.get(index).copied().map(Word::from_byte)
}

#[expect(
    clippy::redundant_pub_crate,
    reason = "shared by sibling domain modules through the crate root"
)]
pub(crate) fn encrypt_profile_value(cell: u32) -> Option<u32> {
    let index = usize::try_from(cell.checked_sub(GRAPHICAL_START)?).ok()?;
    XLAT2.get(index).copied().map(u32::from)
}
