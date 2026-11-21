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
//   - Address-bound mutation-phase admission for one graphical code cell.
// - Must-Not:
//   - Assume a jump encrypts its source, infer off-site effects or publish
//     code.
// - Allows:
//   - Inputs: exact target profile, source byte and ordered fetch/encryption
//     events.
//   - Outputs: checked initial/final code words or a bounded encoding proposal.
//   - Side effects: none; the normative VM must verify every proposed schedule.
// - Split-When:
//   - Full guest memory/version linkage proves all cross-cell mutation events.
// - Merge-When:
//   - A physical source linker independently validates the complete code image.
// - Summary:
//   - Preserves i jump-target encryption separately from fetched-site mutation.

//! Physical code-cell lifecycle planning for a *proposed* ordered guest path.
//!
//! Unlike an all-self-encrypting visit list, an executed `i` encrypts the
//! destination cell, not necessarily its own instruction cell. An explicitly
//! scheduled off-site jump may therefore encrypt a cell without fetching it.
//! A caller must independently establish the actual instruction path, jump
//! targets, data/code aliases and source-loader memory using the normative VM.

use malbolge::{
    ProfileDescriptor, decode_profile_instruction, encrypt_profile_cell,
};

use super::CodeVisitRequirement;

/// At most this many committed fetch/target-encryption events per code cell.
pub const MAX_CODE_CELL_EVENTS: usize = 64;

/// One proposed chronological effect on a single graphical guest code cell.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum CodeCellEvent {
    /// This cell is fetched and executes its decoded instruction.
    /// Normal (non-`i`, non-`v`) instructions self-encrypt afterward.
    Fetch(CodeVisitRequirement),
    /// An `i` executed at some other code site encrypts *this* target cell.
    /// The caller must prove that jump and its exact target independently.
    JumpTargetEncryption,
}

/// Checked code-byte state following an event schedule.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct CodeCellSchedule {
    /// Count of actual proposed fetch events (not external encryptions).
    pub fetches: usize,
    /// Code word after all of the declared events, including final XLAT2.
    pub final_cell: u8,
    /// Loader-valid graphical source byte at this position.
    pub initial: u8,
    /// Count of proposed external jump-target encryptions.
    pub target_encryptions: usize,
}

/// Exact bounded reason a graphical cell/schedule was not admitted.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum CodeCellScheduleError {
    /// The physical code position exceeds the selected target memory.
    AddressOutOfBounds,
    /// The requested fetch does not decode from the evolving cell word.
    DecodeMismatch {
        /// Zero-based physical event index whose requested opcode is wrong.
        event: usize,
    },
    /// No chronological mutation effects were supplied.
    Empty,
    /// A reached `v` stops the VM, so no subsequent effect may be planned.
    EventsAfterHalt {
        /// Zero-based terminal fetch preceding an impossible event.
        event: usize,
    },
    /// A schedule must begin with a reached, source-loader-admitted fetch.
    InvalidFirstEvent,
    /// A source cell is not a printable graphical instruction byte.
    InvalidSourceCell,
    /// No printable initial source byte satisfies the complete schedule.
    NoEncoding,
    /// The bounded single-cell planner permits at most 64 effects.
    TooMany,
}

fn admitted(profile: &ProfileDescriptor, opcode: u8) -> bool {
    matches!(opcode, b'o' | b'i' | b'j' | b'p' | b'*' | b'v')
        || opcode == profile.input_instruction()
        || opcode == profile.output_instruction()
}

/// Check a source cell against ordered fetch and jump-target mutation effects.
///
/// A reached `i` does **not** encrypt its fetched source position; any
/// resulting encryption of this same cell must be represented separately as
/// `JumpTargetEncryption`. Other non-halting fetches encrypt their own cell
/// exactly once. A reached `v` halts and never encrypts itself. An event can
/// claim an exact opcode or an inert decoded symbol, including explicit `o`.
/// No data instruction may overwrite this code cell between these events;
/// that requires a more general code/data alias planner.
///
/// This is a **necessary phase check only**, not independent evidence that
/// any promised jump, input, arithmetic or backedge actually takes place.
///
/// # Errors
///
/// Refuses an invalid byte, incompatible opcode phase, impossible post-halt
/// event or out-of-budget/address request.
#[expect(
    clippy::excessive_nesting,
    clippy::too_many_lines,
    reason = "exact ordered fetch and target-encryption transitions"
)]
pub fn admit_code_cell_schedule(
    profile: &ProfileDescriptor,
    position: u32,
    initial: u8,
    events: &[CodeCellEvent],
) -> Result<CodeCellSchedule, CodeCellScheduleError> {
    if position >= profile.memory_words() {
        return Err(CodeCellScheduleError::AddressOutOfBounds);
    }
    if events.is_empty() {
        return Err(CodeCellScheduleError::Empty);
    }
    if events.len() > MAX_CODE_CELL_EVENTS {
        return Err(CodeCellScheduleError::TooMany);
    }
    if !(33..=126).contains(&initial) {
        return Err(CodeCellScheduleError::InvalidSourceCell);
    }
    let Some(CodeCellEvent::Fetch(CodeVisitRequirement::Decoded(first))) =
        events.first()
    else {
        return Err(CodeCellScheduleError::InvalidFirstEvent);
    };
    if !admitted(profile, *first) {
        return Err(CodeCellScheduleError::InvalidFirstEvent);
    }
    let mut cell = u32::from(initial);
    let mut fetches = 0usize;
    let mut target_encryptions = 0usize;
    for (index, event) in events.iter().enumerate() {
        match event {
            CodeCellEvent::Fetch(requirement) => {
                let decoded = decode_profile_instruction(cell, position);
                let matching = match requirement {
                    CodeVisitRequirement::Decoded(opcode) => {
                        decoded == Some(*opcode)
                    },
                    CodeVisitRequirement::Inert => {
                        decoded.is_some_and(|opcode| {
                            opcode == b'o' || !admitted(profile, opcode)
                        })
                    },
                };
                if !matching {
                    return Err(CodeCellScheduleError::DecodeMismatch {
                        event: index,
                    });
                }
                fetches = fetches.saturating_add(1);
                if decoded == Some(b'v') {
                    if index != events.len().saturating_sub(1) {
                        return Err(CodeCellScheduleError::EventsAfterHalt {
                            event: index,
                        });
                    }
                } else if decoded != Some(b'i') {
                    cell = encrypt_profile_cell(cell)
                        .ok_or(CodeCellScheduleError::InvalidSourceCell)?;
                }
            },
            CodeCellEvent::JumpTargetEncryption => {
                target_encryptions = target_encryptions.saturating_add(1);
                cell = encrypt_profile_cell(cell)
                    .ok_or(CodeCellScheduleError::InvalidSourceCell)?;
            },
        }
    }
    Ok(CodeCellSchedule {
        fetches,
        final_cell: u8::try_from(cell)
            .map_err(|_error| CodeCellScheduleError::InvalidSourceCell)?,
        initial,
        target_encryptions,
    })
}

/// Propose a graphical byte for one ordered code-cell phase schedule.
///
/// Candidates are tried in ascending loader-byte order. This cannot prove
/// that caller-supplied off-site `i` events are ever reached; a completed
/// guest path must independently validate their target/encryption effects.
///
/// # Errors
///
/// Rejects malformed schedules, missing legal encodings and invalid address.
pub fn encode_code_cell_schedule(
    profile: &ProfileDescriptor,
    position: u32,
    events: &[CodeCellEvent],
) -> Result<CodeCellSchedule, CodeCellScheduleError> {
    for initial in 33..=126u8 {
        match admit_code_cell_schedule(profile, position, initial, events) {
            Ok(schedule) => return Ok(schedule),
            Err(CodeCellScheduleError::DecodeMismatch { .. }) => {},
            Err(error) => return Err(error),
        }
    }
    Err(CodeCellScheduleError::NoEncoding)
}
