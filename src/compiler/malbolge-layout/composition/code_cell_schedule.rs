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
    ProfileDescriptor, ProfileKind, decode_profile_instruction,
    encrypt_profile_cell,
};

use super::CodeVisitRequirement;

/// At most this many chronological journal entries per code cell.
/// A `FetchSelfWrite` represents two coupled physical effects in one entry.
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
    /// One fetched `p` or `*` reads and writes its own code cell, then XLAT2
    /// encrypts the just-written word. `after` is the full guest data result.
    FetchSelfWrite {
        /// Actual fetched writer instruction (`p` or `*` only).
        opcode: u8,
        /// Committed data result before the post-instruction encryption.
        after: u32,
    },
    /// A reached `p` or `*` at another code position writes this cell.
    /// The caller must prove the off-site writer and its exact operand.
    DataWrite {
        /// Current full-width guest memory word before the data write.
        before: u32,
        /// Full-width guest memory word produced by the data operation.
        after: u32,
    },
    /// A fetched non-graphical word terminates a modern-profile VM with no
    /// decode or XLAT2. A prior real data write may have made it non-graphical.
    /// The frozen historical profile does not have this termination rule.
    FetchNonGraphicalHalt,
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

/// Replayed effects on a word initialized by the normative profile loader.
///
/// Unlike a graphical source byte, loader-expanded memory can begin with any
/// full-width word. This record is a phase obligation, not proof that the
/// caller's proposed write, fetch or jump actually executes.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct LoadedCodeCellSchedule {
    /// Number of declared physical `p`/`*` writes, even if idempotent.
    pub data_writes: usize,
    /// Number of fetched code cells, including non-graphical terminal fetch.
    pub fetches: usize,
    /// Final live word after all scheduled effects.
    pub final_cell: u32,
    /// Exact source-loaded *memory word*, not a presumed graphical source
    /// byte.
    pub initial_word: u32,
    /// Number of actual off-site `i` target encryptions.
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
    /// The original source byte decodes to a loader-forbidden instruction.
    InvalidFirstEvent,
    /// Initial loader-expanded memory word exceeds the target word geometry.
    InvalidLoadedWord,
    /// A source cell is not a printable graphical instruction byte.
    InvalidSourceCell,
    /// No printable initial source byte satisfies the complete schedule.
    NoEncoding,
    /// The bounded single-cell planner permits at most 64 effects.
    TooMany,
}

const fn admitted(profile: &ProfileDescriptor, opcode: u8) -> bool {
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
/// An off-site `DataWrite` or jump-target encryption may precede the first
/// code fetch. An initial inert `o` fetch is also legal. Every source byte
/// must still decode to a loader-admitted instruction, even if overwritten
/// before its first fetch. Data writes bind exact live `before`/`after` words
/// and may leave non-graphical memory if no subsequent fetch or XLAT2
/// operation requires it. A `FetchSelfWrite` represents a reached `p` or
/// `*` with C == D, where the guest encrypts its *new* data result. All
/// proposed effects still require whole-path VM verification.
///
/// This is a **necessary phase check only**, not independent evidence that
/// any promised jump, input, arithmetic or backedge actually takes place.
///
/// # Errors
///
/// Refuses invalid bytes or words, inconsistent effects, impossible post-halt
/// events, and out-of-budget/address requests.
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
    // A source byte must be loader-admitted before any data write or XLAT2.
    // Loader-expanded memory has no such initial-source requirement.
    if !decode_profile_instruction(u32::from(initial), position)
        .is_some_and(|opcode| admitted(profile, opcode))
    {
        return Err(CodeCellScheduleError::InvalidFirstEvent);
    }
    let loaded = admit_loaded_code_cell_schedule(
        profile,
        position,
        u32::from(initial),
        events,
    )?;
    Ok(CodeCellSchedule {
        data_writes: loaded.data_writes,
        fetches: loaded.fetches,
        final_cell: loaded.final_cell,
        initial,
        target_encryptions: loaded.target_encryptions,
    })
}

/// Check phases of a cell initialized by full-width guest loader expansion.
///
/// This does **not** prove `initial_word` equals the real loader output or
/// that off-site effects execute. Callers must obtain the initial word from
/// a source-loaded normative VM and independently prove the reached effects.
/// Unlike a source byte, an expanded word may start non-graphical and become
/// executable only after a genuine `p`/`*` store. It may also remain data for
/// the entire prefix. Fetch and self-write ordering is identical to source
/// cells, and all full-width word versions are checked in execution order.
///
/// # Errors
///
/// Refuses invalid initial/data words, positions, budgets, fetched opcodes,
/// XLAT2 targets, stale write versions and impossible effects after halt.
#[expect(
    clippy::excessive_nesting,
    clippy::too_many_lines,
    reason = "exact ordered fetch and target-encryption transitions"
)]
pub fn admit_loaded_code_cell_schedule(
    profile: &ProfileDescriptor,
    position: u32,
    initial_word: u32,
    events: &[CodeCellEvent],
) -> Result<LoadedCodeCellSchedule, CodeCellScheduleError> {
    if position >= profile.memory_words() {
        return Err(CodeCellScheduleError::AddressOutOfBounds);
    }
    if events.is_empty() {
        return Err(CodeCellScheduleError::Empty);
    }
    if events.len() > MAX_CODE_CELL_EVENTS {
        return Err(CodeCellScheduleError::TooMany);
    }
    if initial_word >= profile.memory_words() {
        return Err(CodeCellScheduleError::InvalidLoadedWord);
    }
    let mut cell = initial_word;
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
            CodeCellEvent::FetchNonGraphicalHalt => {
                if profile.kind() == ProfileKind::HistoricalConformance
                    || (33..=126).contains(&cell)
                {
                    return Err(CodeCellScheduleError::DecodeMismatch {
                        event: index,
                    });
                }
                if index != events.len().saturating_sub(1) {
                    return Err(CodeCellScheduleError::EventsAfterHalt {
                        event: index,
                    });
                }
                fetches = fetches.saturating_add(1);
            },
            CodeCellEvent::FetchSelfWrite { opcode, after } => {
                if !matches!(*opcode, b'p' | b'*')
                    || decode_profile_instruction(cell, position)
                        != Some(*opcode)
                {
                    return Err(CodeCellScheduleError::DecodeMismatch {
                        event: index,
                    });
                }
                if *after >= profile.memory_words() {
                    return Err(CodeCellScheduleError::InvalidDataWord {
                        event: index,
                    });
                }
                // Normative order: fetch/decode, read old M[D], store the
                // result at C == D, then encrypt that *new* code-cell word.
                cell = encrypt_profile_cell(*after).ok_or(
                    CodeCellScheduleError::InvalidEncryptionTarget {
                        event: index,
                    },
                )?;
                fetches = fetches.saturating_add(1);
                data_writes = data_writes.saturating_add(1);
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
    Ok(LoadedCodeCellSchedule {
        data_writes,
        fetches,
        final_cell: cell,
        initial_word,
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
                | CodeCellScheduleError::DataWriteMismatch { .. }
                | CodeCellScheduleError::InvalidFirstEvent,
            ) => {},
            Err(error) => return Err(error),
        }
    }
    Err(CodeCellScheduleError::NoEncoding)
}
