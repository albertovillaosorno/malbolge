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
//   - Normative guest-origin code-cell phase journals including unchanged
//     writes.
// - Must-Not:
//   - Infer source-C operations or publish code without whole-path proof.
// - Allows:
//   - Inputs: graphical source, binary stream, bounded steps and one code site.
//   - Outputs: authenticated N15/classic site events and final live memory
//     word.
//   - Side effects: isolated normative VM execution only.
// - Split-When:
//   - Whole-source physical linker owns the complete ordered memory journal.
// - Merge-When:
//   - General source-backed CFG execution verifies all code/data alias effects.
// - Summary:
//   - An idempotent guest p or * is still a real data write.

//! Exact bounded source-loaded code-site journaling, not source-C linkage.
//!
//! Changed-cell deltas omit idempotent `p` and `*` writes. Real instruction
//! traces retain the operand read and resulting accumulator even in that case.
//! This verifier uses the normative VM itself, not caller-forged trace events.

use std::collections::BTreeMap;

use malbolge::{
    ProfileDescriptor, ProfileMachine, ProfileStepTrace, RunOutcome,
    StepOutcome, Termination, is_source_whitespace,
};

use super::code_cell_schedule::{
    CodeCellEvent, CodeCellSchedule, CodeCellScheduleError,
    admit_code_cell_schedule,
};
use super::{
    CodeVisitRequirement, MAX_REVISIT_SOURCE_CELLS, MAX_REVISIT_STEPS,
};

/// Bounded code-site verification refusal, distinct from any C23 linkage.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum SourceCodeCellTraceError {
    /// The phase journal disagrees with the actual final VM memory word.
    FinalWordMismatch,
    /// The source, requested site or step budget exceeds the bounded check.
    InvalidBound,
    /// The VM trace does not expose a required data-read/write identity.
    InvalidEffect,
    /// The VM failed to execute the declared bounded prefix.
    InvalidExecution,
    /// The original graphical source is not loader-admitted for this profile.
    InvalidSource,
    /// No actual fetched, written or jump-encrypted effect reaches this site.
    MissingEffect,
    /// The exact chronological site events do not match the source byte.
    Schedule(CodeCellScheduleError),
}

/// One independently replayed, input-specific code-cell phase observation.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct SourceCodeCellTrace {
    /// Observed chronological effects, including idempotent data writes.
    pub events: Vec<CodeCellEvent>,
    /// Exact final source-site word checked against the normative VM.
    pub final_word: u32,
    /// Actual bounded VM termination or step-budget exhaustion.
    pub outcome: RunOutcome,
    /// Source-loaded code-cell plan admitted from actual guest effects.
    pub schedule: CodeCellSchedule,
}

const fn is_active(opcode: u8, profile: &ProfileDescriptor) -> bool {
    matches!(opcode, b'o' | b'i' | b'j' | b'p' | b'*' | b'v')
        || opcode == profile.input_instruction()
        || opcode == profile.output_instruction()
}

/// Append one real guest step's effects on a single source code site.
///
/// A same-step code/data alias must be represented as one atomic
/// `FetchSelfWrite`: `p` or `*` writes data *after* fetch and *before* XLAT2.
/// Treating the same step as a standalone `Fetch` would encrypt the wrong word.
#[expect(
    clippy::excessive_nesting,
    clippy::too_many_lines,
    reason = "real fetch, self-write, data and XLAT2 journal ordering"
)]
fn append_site_effects(
    profile: &ProfileDescriptor,
    site: u32,
    step: &ProfileStepTrace,
    events: &mut Vec<CodeCellEvent>,
) -> Result<(), SourceCodeCellTraceError> {
    if step.result.is_err() {
        return Err(SourceCodeCellTraceError::InvalidExecution);
    }
    let fetched_site = step.before.registers.code_pointer == site;
    let mut self_write = None;
    if matches!(step.decoded, Some(b'p' | b'*')) {
        let read = step
            .memory_reads
            .data
            .ok_or(SourceCodeCellTraceError::InvalidEffect)?;
        if read.address == site {
            let after = step.after.registers.accumulator;
            if fetched_site {
                // The normative VM reports only the *net* encryption delta
                // for a same-address data write. It never publishes the
                // intermediate p/* write in `memory_delta.data`.
                let encrypted = malbolge::encrypt_profile_cell(after)
                    .ok_or(SourceCodeCellTraceError::InvalidEffect)?;
                let encryption_matches = step.memory_delta.encryption.map_or(
                    encrypted == read.value,
                    |delta| {
                        (delta.address, delta.before, delta.after)
                            == (site, read.value, encrypted)
                    },
                );
                if step.fetched_cell != Some(read.value)
                    || step.memory_delta.data.is_some()
                    || !encryption_matches
                {
                    return Err(SourceCodeCellTraceError::InvalidEffect);
                }
                self_write = Some(after);
            } else {
                if let Some(delta) = step.memory_delta.data {
                    if (delta.address, delta.before, delta.after)
                        != (site, read.value, after)
                    {
                        return Err(SourceCodeCellTraceError::InvalidEffect);
                    }
                } else if read.value != after {
                    return Err(SourceCodeCellTraceError::InvalidEffect);
                }
                events.push(CodeCellEvent::DataWrite {
                    before: read.value,
                    after,
                });
            }
        }
    }
    if fetched_site {
        if step.result
            == Ok(StepOutcome::Terminated(Termination::NonGraphicalCell))
            && step
                .fetched_cell
                .is_some_and(|cell| !(33..=126).contains(&cell))
            && step.decoded.is_none()
        {
            // A physical data/code alias may make a previously loader-valid
            // code cell non-graphical. Its attempted fetch terminates before
            // decode or XLAT2, but is still a real code-site effect.
            events.push(CodeCellEvent::FetchNonGraphicalHalt);
        } else {
            let opcode = step
                .decoded
                .ok_or(SourceCodeCellTraceError::InvalidEffect)?;
            if let Some(after) = self_write {
                events.push(CodeCellEvent::FetchSelfWrite { opcode, after });
            } else {
                let requirement = if is_active(opcode, profile) {
                    CodeVisitRequirement::Decoded(opcode)
                } else {
                    CodeVisitRequirement::Inert
                };
                events.push(CodeCellEvent::Fetch(requirement));
            }
        }
    }
    if step
        .memory_delta
        .encryption
        .is_some_and(|delta| delta.address == site)
        && (!fetched_site || step.decoded == Some(b'i'))
    {
        events.push(CodeCellEvent::JumpTargetEncryption);
    }
    Ok(())
}

/// Replay real source-loaded VM execution and admit one exact code-site
/// journal.
///
/// An unchanged `p` or `*` still creates a `DataWrite` event, unlike a
/// changed-cell delta-only projection. Source-valid code bytes are checked
/// against chronological guest operations and the final live memory word.
/// Reached same-step `p`/`*` self-aliases are checked in their VM order as
/// one fetch/write/XLAT2 effect. The returned step outcome can be a budget
/// stop and never implies a complete C23 program.
///
/// # Errors
///
/// Rejects oversized sources/budgets, invalid VM code, inconsistent
/// instruction effects and mismatched final physical memory.
#[expect(
    clippy::too_many_arguments,
    reason = "source/profile identity, binary input, budget and physical site"
)]
pub fn verify_source_code_cell_trace(
    profile: &'static ProfileDescriptor,
    source: &[u8],
    input: &[u8],
    steps: usize,
    site: u32,
) -> Result<SourceCodeCellTrace, SourceCodeCellTraceError> {
    let index = usize::try_from(site)
        .ok()
        .ok_or(SourceCodeCellTraceError::InvalidBound)?;
    if steps == 0
        || steps > MAX_REVISIT_STEPS
        || source.len() > MAX_REVISIT_SOURCE_CELLS
    {
        return Err(SourceCodeCellTraceError::InvalidBound);
    }
    // VM source positions count graphical code words, not presentation
    // whitespace. Use the exact shared raw-loader predicate, including VT
    // and FF; annotated-source comment handling does not apply here.
    let initial = source
        .iter()
        .copied()
        .filter(|byte| !is_source_whitespace(*byte))
        .nth(index)
        .ok_or(SourceCodeCellTraceError::InvalidBound)?;
    let mut machine =
        ProfileMachine::from_source(profile, source, input.to_vec())
            .map_err(|_error| SourceCodeCellTraceError::InvalidSource)?;
    let mut events = Vec::new();
    let mut failure = None;
    let outcome = machine
        .run_traced(steps, &mut |step| {
            if failure.is_none()
                && let Err(error) =
                    append_site_effects(profile, site, step, &mut events)
            {
                failure = Some(error);
            }
        })
        .map_err(|_error| SourceCodeCellTraceError::InvalidExecution)?;
    if let Some(error) = failure {
        return Err(error);
    }
    if events.is_empty() {
        return Err(SourceCodeCellTraceError::MissingEffect);
    }
    let schedule = admit_code_cell_schedule(profile, site, initial, &events)
        .map_err(SourceCodeCellTraceError::Schedule)?;
    let final_word = machine
        .memory_word(site)
        .map_err(|_error| SourceCodeCellTraceError::InvalidExecution)?;
    if schedule.final_cell != final_word {
        return Err(SourceCodeCellTraceError::FinalWordMismatch);
    }
    Ok(SourceCodeCellTrace {
        events,
        final_word,
        outcome,
        schedule,
    })
}

/// One source code cell changed, fetched or jump-encrypted by the real guest.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct SourceCodeImageCellTrace {
    /// Code position in loaded, whitespace-stripped source coordinates.
    pub site: u32,
    /// Chronological code/data effects from the single normative replay.
    pub events: Vec<CodeCellEvent>,
    /// Independently checked full-width final word at this code site.
    pub final_word: u32,
    /// Admitted phase transition schedule for this code site.
    pub schedule: CodeCellSchedule,
}

/// Complete bounded source-code image accounting from one guest execution.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct SourceCodeImageTrace {
    /// Physical sites with at least one actual effect, sorted by code address.
    pub touched: Vec<SourceCodeImageCellTrace>,
    /// Count of loader-admitted source cells, excluding raw whitespace.
    pub source_cells: usize,
    /// Normative guest termination or exact step-budget exhaustion.
    pub outcome: RunOutcome,
}

/// Precise bounded whole-source code-image verification refusal.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum SourceCodeImageTraceError {
    /// Source or step budget exceeds the existing finite trace limits.
    InvalidBound,
    /// The normative guest did not commit the requested bounded execution.
    InvalidExecution,
    /// Source bytes were not admitted by the selected normative loader.
    InvalidSource,
    /// This code site's real effects could not be reconciled with its source.
    Cell {
        /// Loaded source code position with inconsistent effects.
        site: u32,
        /// Exact underlying one-site refusal.
        error: SourceCodeCellTraceError,
    },
    /// A source cell changed without any observed fetched/write/XLAT2 effect.
    UntouchedChanged {
        /// Loaded source cell with a missing physical effect.
        site: u32,
    },
}

/// Find all possible source-code sites touched by this physical step.
///
/// The fetched instruction, guest `p`/`*` data operand and encryption target
/// can alias. The caller deduplicates them before reconstructing effects.
fn affected_code_sites(step: &ProfileStepTrace) -> [Option<u32>; 4] {
    let write = if matches!(step.decoded, Some(b'p' | b'*')) {
        step.memory_reads.data.map(|read| read.address)
    } else {
        None
    };
    [
        step.memory_reads.fetch.map(|read| read.address),
        write,
        step.memory_reads.encryption.map(|read| read.address),
        step.memory_delta.encryption.map(|delta| delta.address),
    ]
}

/// Verify every loaded source code cell against one complete physical replay.
///
/// All actual fetches, idempotent and changed data writes, and off-site `i`
/// XLAT2 effects are considered in chronological VM order. Each touched code
/// word is independently checked by the phase scheduler. Every untouched
/// source word is also compared with final VM memory, so missing write effects
/// cannot silently leave a mismatched code image. Only the loaded *source*
/// region is claimed, not arbitrary loader-expanded memory or C23 semantics.
///
/// # Errors
///
/// Rejects invalid source/bounds, VM execution failure, per-site phase
/// mismatches and unexplained final changes to source code memory.
#[expect(
    clippy::too_many_lines,
    reason = "one bounded normative replay and full source-image reconciliation"
)]
pub fn verify_source_code_image_trace(
    profile: &'static ProfileDescriptor,
    source: &[u8],
    input: &[u8],
    steps: usize,
) -> Result<SourceCodeImageTrace, SourceCodeImageTraceError> {
    if steps == 0
        || steps > MAX_REVISIT_STEPS
        || source.len() > MAX_REVISIT_SOURCE_CELLS
    {
        return Err(SourceCodeImageTraceError::InvalidBound);
    }
    let initial = source
        .iter()
        .copied()
        .filter(|byte| !is_source_whitespace(*byte))
        .collect::<Vec<_>>();
    let source_cells = initial.len();
    let mut machine =
        ProfileMachine::from_source(profile, source, input.to_vec())
            .map_err(|_error| SourceCodeImageTraceError::InvalidSource)?;
    let mut per_site = BTreeMap::<u32, Vec<CodeCellEvent>>::new();
    let mut failure = None;
    let outcome = machine
        .run_traced(steps, &mut |step| {
            if failure.is_some() {
                return;
            }
            if step.result.is_err() {
                failure = Some(SourceCodeImageTraceError::InvalidExecution);
                return;
            }
            let mut seen = Vec::with_capacity(4);
            for site in affected_code_sites(step).into_iter().flatten() {
                if usize::try_from(site)
                    .ok()
                    .is_none_or(|index| index >= source_cells)
                    || seen.contains(&site)
                {
                    continue;
                }
                seen.push(site);
                if let Err(error) = append_site_effects(
                    profile,
                    site,
                    step,
                    per_site.entry(site).or_default(),
                ) {
                    failure =
                        Some(SourceCodeImageTraceError::Cell { site, error });
                    break;
                }
            }
        })
        .map_err(|_error| SourceCodeImageTraceError::InvalidExecution)?;
    if let Some(error) = failure {
        return Err(error);
    }
    let mut touched = Vec::with_capacity(per_site.len());
    for (index, source_byte) in initial.into_iter().enumerate() {
        let site = u32::try_from(index)
            .map_err(|_error| SourceCodeImageTraceError::InvalidBound)?;
        let final_word = machine
            .memory_word(site)
            .map_err(|_error| SourceCodeImageTraceError::InvalidExecution)?;
        let Some(events) = per_site.remove(&site) else {
            if final_word != u32::from(source_byte) {
                return Err(SourceCodeImageTraceError::UntouchedChanged {
                    site,
                });
            }
            continue;
        };
        let schedule =
            admit_code_cell_schedule(profile, site, source_byte, &events)
                .map_err(|error| SourceCodeImageTraceError::Cell {
                    site,
                    error: SourceCodeCellTraceError::Schedule(error),
                })?;
        if schedule.final_cell != final_word {
            return Err(SourceCodeImageTraceError::Cell {
                site,
                error: SourceCodeCellTraceError::FinalWordMismatch,
            });
        }
        touched.push(SourceCodeImageCellTrace {
            site,
            events,
            final_word,
            schedule,
        });
    }
    Ok(SourceCodeImageTrace {
        touched,
        source_cells,
        outcome,
    })
}
