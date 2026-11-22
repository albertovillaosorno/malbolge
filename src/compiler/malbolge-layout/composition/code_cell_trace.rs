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
