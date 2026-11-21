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
//   - Address-bound fetch, XLAT2 and data-write phases for one code cell.
// - Must-Not:
//   - Assume a jump encrypts its source, infer off-site effects or publish
//     code.
// - Allows:
//   - Inputs: profile, initial source byte, ordered fetch/write/encryption
//     events.
//   - Outputs: checked initial/final code words or a bounded encoding proposal.
//   - Side effects: none; the normative VM must verify every proposed schedule.
// - Split-When:
//   - Full guest memory/version linkage proves all cross-cell mutation events.
// - Merge-When:
//   - A physical source linker independently validates the complete code image.
// - Summary:
//   - Models external guest data writes and i-target XLAT2 before code fetch.

//! Physical code-cell lifecycle planning for a *proposed* ordered guest path.
//!
//! Unlike an all-self-encrypting visit list, an executed `i` encrypts the
//! destination cell, not necessarily its own instruction cell. An explicitly
//! scheduled off-site jump may therefore encrypt a cell without fetching it.
//! A caller must independently establish the actual instruction path, jump
//! targets, data/code aliases and source-loader memory using the normative VM.
//! Source-code cells may be overwritten by `p` or `*` before their first fetch;
//! the resulting guest-width word must be decoded at the actual code position.

use malbolge::{
    ProfileDescriptor, decode_profile_instruction, encrypt_profile_cell,
};

use super::CodeVisitRequirement;

/// At most this many chronological effects per code cell.
pub const MAX_CODE_CELL_EVENTS: usize = 64;

/// One proposed chronological effect on a source-backed guest code cell.
/// A fixed-width tag keeps the two-word write payload in a compact enum.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
#[repr(u32)]
pub enum CodeCellEvent {
    /// This cell is fetched and executes its decoded instruction.
    /// Normal (non-`i`, non-`v`) instructions self-encrypt afterward.
    Fetch(CodeVisitRequirement),
    /// An `i` executed at some other code site encrypts *this* target cell.
    /// The caller must prove that jump and its exact target independently.
    JumpTargetEncryption,
    /// A reached `p` or `*` at another code position writes this cell.
    /// The caller must prove the off-site writer and its exact operand.
    DataWrite {
        /// Current full-width guest memory word before the data write.
        before: u32,
        /// Full-width guest memory word produced by the data operation.
        after: u32,
    },
}

/// Checked full-width code-memory state following an event schedule.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct CodeCellSchedule {
    /// Number of declared guest data-write effects on this code cell.
    pub data_writes: usize,
    /// Count of actual proposed fetch events (not external encryptions).
    pub fetches: usize,
    /// Full-width code word after all declared effects, including XLAT2.
    pub final_cell: u32,
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
    /// Guest data-write expected a different live memory version.
    DataWriteMismatch {
        /// Zero-based physical event index with the mismatched live word.
        event: usize,
    },
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
    /// A data write supplied a word beyond the profile memory geometry.
    InvalidDataWord {
        /// Zero-based physical event index with the out-of-range word.
        event: usize,
    },
    /// An XLAT2 target was no longer a graphical code word.
    InvalidEncryptionTarget {
        /// Zero-based physical event index that cannot encrypt.
        event: usize,
    },
    /// The initial fetch or pre-fetch write needs a loader-admitted byte.
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

/// Check a source cell against ordered fetch, data and XLAT2 effects.
///
/// A reached `i` does **not** encrypt its fetched source position; any
/// resulting encryption of this same cell must be represented separately as
/// `JumpTargetEncryption`. Other non-halting fetches encrypt their own cell
/// exactly once. A reached `v` halts and never encrypts itself. An event can
/// claim an exact opcode or an inert decoded symbol, including explicit `o`.
/// An off-site `DataWrite` may precede the first code fetch. It binds exact
/// live `before`/`after` guest words and may leave non-graphical memory if no
/// subsequent fetch or XLAT2 operation requires it. Same-step self-aliases
/// and other cross-cell effects still need whole-path VM verification.
///
/// This is a **necessary phase check only**, not independent evidence that
/// any promised jump, input, arithmetic or backedge actually takes place.
///
/// # Errors
///
/// Refuses invalid bytes or words, inconsistent effects, impossible post-halt
/// events, and out-of-budget/address requests.
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
    match events.first() {
        Some(CodeCellEvent::Fetch(CodeVisitRequirement::Decoded(first)))
            if admitted(profile, *first) => {},
        Some(CodeCellEvent::DataWrite { .. })
            if decode_profile_instruction(u32::from(initial), position)
                .is_some_and(|opcode| admitted(profile, opcode)) => {},
        _ => return Err(CodeCellScheduleError::InvalidFirstEvent),
    }
    let mut cell = u32::from(initial);
    let mut fetches = 0usize;
    let mut data_writes = 0usize;
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
                    cell = encrypt_profile_cell(cell).ok_or(
                        CodeCellScheduleError::InvalidEncryptionTarget {
                            event: index,
                        },
                    )?;
                }
            },
            CodeCellEvent::JumpTargetEncryption => {
                target_encryptions = target_encryptions.saturating_add(1);
                cell = encrypt_profile_cell(cell).ok_or(
                    CodeCellScheduleError::InvalidEncryptionTarget {
                        event: index,
                    },
                )?;
            },
            CodeCellEvent::DataWrite { before, after } => {
                if *before != cell {
                    return Err(CodeCellScheduleError::DataWriteMismatch {
                        event: index,
                    });
                }
                if *after >= profile.memory_words() {
                    return Err(CodeCellScheduleError::InvalidDataWord {
                        event: index,
                    });
                }
                data_writes = data_writes.saturating_add(1);
                cell = *after;
            },
        }
    }
    Ok(CodeCellSchedule {
        data_writes,
        fetches,
        final_cell: cell,
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
            Err(
                CodeCellScheduleError::DecodeMismatch { .. }
                | CodeCellScheduleError::DataWriteMismatch { .. },
            ) => {},
            Err(CodeCellScheduleError::InvalidFirstEvent)
                if matches!(
                    events.first(),
                    Some(CodeCellEvent::DataWrite { .. })
                ) => {},
            Err(error) => return Err(error),
        }
    }
    Err(CodeCellScheduleError::NoEncoding)
}
