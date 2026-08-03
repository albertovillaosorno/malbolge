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
//   - Portable state-changing execution IR shared by future native tiers.
// - Must-Not:
//   - Verify optimizations, encode host ISA bytes, or define Malbolge
//   - semantics.
// - Allows:
//   - Inputs: canonical profile identity, verified live-ins, and VM trace
//   - effects.
//   - Outputs: architecture-neutral bounded-region effect programs.
//   - Side effects: none.
// - Split-When:
//   - Split when serialization and cache encoding need independent ownership.
// - Merge-When:
//   - Merge when another execution module owns the same portable effect schema.
// - Summary:
//   - Defines the versioned portable IR consumed after deterministic
//   - verification.
// - Description:
//   - Carries only state-changing effects and verifier-bound region metadata.
// - Usage:
//   - Included by execution/research composition roots through explicit paths.
// - Defaults:
//   - IR data is untrusted until a verifier-owned boundary admits it.
//

//! Portable bounded-region effect IR for tiered execution.

use std::collections::BTreeMap;

pub use malbolge::TargetProfileRequirement;
use malbolge::{
    ProfileMachineObservation, ProfileMemoryDelta, ProfileMemoryRead,
    ProfileMemoryWrite, ProfileStepTrace, RunOutcome, StepOutcome, Termination,
    TraceInput,
};

/// Current portable bounded-region effect-IR schema version.
pub const EFFECT_IR_VERSION: u16 = 3;
const IR_MAGIC: &[u8; 4] = b"MBIR";

/// One architecture-neutral state-changing operation from a verified VM step.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct EffectOp {
    /// Exact observable state required after this operation.
    pub after: ProfileMachineObservation,
    /// Exact observable state required before this operation.
    pub before: ProfileMachineObservation,
    /// Deterministic input effect, when this operation performs guest input.
    pub input: Option<TraceInput>,
    /// Exact final changed memory cells for this operation.
    pub memory_delta: ProfileMemoryDelta,
    /// Deterministic output byte, when this operation performs guest output.
    pub output: Option<u8>,
}

/// One verifier-derived entry-memory value required by a portable region.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct MemoryLiveIn {
    /// Profile-width memory address required at region entry.
    pub address: u32,
    /// Exact entry value required at `address`.
    pub value: u32,
}

/// Versioned architecture-neutral bounded-region program.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct RegionEffectProgram {
    /// Ordered compact state-changing operations.
    pub effects: Vec<EffectOp>,
    /// Portable effect-IR schema version.
    pub format_version: u16,
    /// Verifier-derived entry-memory live-ins.
    pub memory_live_ins: Vec<MemoryLiveIn>,
    /// Verified bounded-run outcome.
    pub outcome: RunOutcome,
    /// Canonical target-profile fingerprint.
    pub profile_fingerprint: String,
    /// Exact declared target-profile identity.
    pub profile_id: String,
    /// Canonical geometry and semantic capability requirement.
    pub profile_requirement: TargetProfileRequirement,
    /// Verified semantic-step budget.
    pub step_budget: usize,
}

impl EffectOp {
    /// Projects one normative VM trace to the portable state-changing subset.
    #[must_use]
    pub const fn from_trace(trace: &ProfileStepTrace) -> Self {
        Self {
            after: trace.after,
            before: trace.before,
            input: trace.input,
            memory_delta: trace.memory_delta,
            output: trace.output,
        }
    }
}

/// Failure while rendering one portable program's canonical identity bytes.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum IrEncodingError {
    /// A host-sized length cannot fit the canonical unsigned 64-bit field.
    LengthOverflow,
}

/// Failure while projecting one complete normative step trace to portable IR.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum StepProgramProjectionError {
    /// Two semantic reads claim different values for the same address.
    ConflictingMemoryRead,
    /// The semantic fetch did not read the entry code pointer.
    FetchAddress,
    /// The fetched-cell claim disagrees with the semantic fetch read.
    FetchValue,
    /// A successful step trace omitted its mandatory code-cell fetch.
    MissingFetch,
    /// Public step outcome and after-termination observation disagree.
    Outcome,
    /// The trace records a rejected normative transition.
    RejectedTrace,
    /// Execution was already terminated before the requested step.
    TerminatedEntry,
}

impl RegionEffectProgram {
    /// Renders the versioned architecture-neutral canonical byte
    /// representation.
    ///
    /// The encoding is independent from Rust struct layout and host pointer
    /// width. Integer fields use fixed-width little-endian representation;
    /// variable-length byte sequences use an unsigned 64-bit length prefix.
    ///
    /// # Errors
    ///
    /// Returns [`IrEncodingError::LengthOverflow`] when a host-sized length
    /// cannot fit the canonical unsigned 64-bit representation.
    pub fn canonical_bytes(&self) -> Result<Vec<u8>, IrEncodingError> {
        let mut bytes = Vec::new();
        bytes.extend_from_slice(IR_MAGIC);
        push_u16(&mut bytes, self.format_version);
        push_bytes(&mut bytes, self.profile_id.as_bytes())?;
        push_bytes(&mut bytes, self.profile_fingerprint.as_bytes())?;
        push_profile_requirement(&mut bytes, &self.profile_requirement)?;
        push_usize(&mut bytes, self.step_budget)?;
        push_run_outcome(&mut bytes, self.outcome)?;
        push_usize(&mut bytes, self.memory_live_ins.len())?;
        for live_in in &self.memory_live_ins {
            push_u32(&mut bytes, live_in.address);
            push_u32(&mut bytes, live_in.value);
        }
        push_usize(&mut bytes, self.effects.len())?;
        for effect in &self.effects {
            push_effect(&mut bytes, *effect)?;
        }
        Ok(bytes)
    }

    /// Reports whether every addressed word fits the declared profile capacity.
    #[must_use]
    pub fn fits_declared_profile_capacity(&self) -> bool {
        self.required_memory_words()
            <= u64::from(self.profile_requirement.memory_words)
    }

    /// Projects one successful normative step trace to exact one-step IR.
    ///
    /// Semantic memory reads become sorted, deduplicated live-ins. The returned
    /// program remains ordinary portable IR and must still pass the selected
    /// backend's independent semantic admission.
    ///
    /// # Errors
    ///
    /// Returns [`StepProgramProjectionError`] when the trace was rejected or
    /// its fetch, outcome, or repeated-read evidence is internally
    /// inconsistent.
    pub fn from_profile_step_trace(
        trace: &ProfileStepTrace,
    ) -> Result<Self, StepProgramProjectionError> {
        if trace.before.termination.is_some() {
            return Err(StepProgramProjectionError::TerminatedEntry);
        }
        let fetch = trace
            .memory_reads
            .fetch
            .ok_or(StepProgramProjectionError::MissingFetch)?;
        if fetch.address != trace.before.registers.code_pointer {
            return Err(StepProgramProjectionError::FetchAddress);
        }
        if trace.fetched_cell != Some(fetch.value) {
            return Err(StepProgramProjectionError::FetchValue);
        }
        let outcome = match trace.result {
            Ok(StepOutcome::Continued) if trace.after.termination.is_none() => {
                RunOutcome::BudgetExhausted { steps: 1 }
            },
            Ok(StepOutcome::Terminated(reason))
                if trace.after.termination == Some(reason) =>
            {
                RunOutcome::Terminated { reason, steps: 1 }
            },
            Ok(StepOutcome::Continued | StepOutcome::Terminated(_)) => {
                return Err(StepProgramProjectionError::Outcome);
            },
            Err(_error) => {
                return Err(StepProgramProjectionError::RejectedTrace);
            },
        };
        let mut live_ins = BTreeMap::new();
        for read in [
            Some(fetch),
            trace.memory_reads.data,
            trace.memory_reads.encryption,
        ]
        .into_iter()
        .flatten()
        {
            insert_trace_read(&mut live_ins, read)?;
        }
        Ok(Self {
            effects: vec![EffectOp::from_trace(trace)],
            format_version: EFFECT_IR_VERSION,
            memory_live_ins: live_ins
                .into_iter()
                .map(|(address, value)| MemoryLiveIn { address, value })
                .collect(),
            outcome,
            profile_fingerprint: String::from(trace.profile.fingerprint()),
            profile_id: String::from(trace.profile.id()),
            profile_requirement: TargetProfileRequirement::from_descriptor(
                trace.profile,
            ),
            step_budget: 1,
        })
    }

    /// Returns the minimum directly addressed memory required by this region.
    ///
    /// The requirement includes code/data pointers in every observation,
    /// verifier live-ins, and every data/encryption write address. The result
    /// is `u64` so address `u32::MAX` is represented exactly as
    /// 4,294,967,296 words.
    #[must_use]
    pub fn required_memory_words(&self) -> u64 {
        let from_live_ins =
            self.memory_live_ins.iter().fold(0u64, |required, item| {
                required.max(words_through_address(item.address))
            });
        self.effects
            .iter()
            .copied()
            .fold(from_live_ins, |required, effect| {
                required.max(effect_required_memory_words(effect))
            })
    }
}

fn insert_trace_read(
    live_ins: &mut BTreeMap<u32, u32>,
    read: ProfileMemoryRead,
) -> Result<(), StepProgramProjectionError> {
    match live_ins.get(&read.address) {
        Some(value) if *value != read.value => {
            Err(StepProgramProjectionError::ConflictingMemoryRead)
        },
        Some(_value) => Ok(()),
        None => {
            let _previous = live_ins.insert(read.address, read.value);
            Ok(())
        },
    }
}

fn effect_required_memory_words(effect: EffectOp) -> u64 {
    let observations = observation_required_memory_words(effect.before)
        .max(observation_required_memory_words(effect.after));
    observations.max(memory_delta_required_memory_words(effect.memory_delta))
}

fn memory_delta_required_memory_words(delta: ProfileMemoryDelta) -> u64 {
    memory_write_required_memory_words(delta.data)
        .max(memory_write_required_memory_words(delta.encryption))
}

fn memory_write_required_memory_words(
    write: Option<ProfileMemoryWrite>,
) -> u64 {
    write.map_or(0, |change| words_through_address(change.address))
}

fn observation_required_memory_words(
    observation: ProfileMachineObservation,
) -> u64 {
    words_through_address(observation.registers.code_pointer)
        .max(words_through_address(observation.registers.data_pointer))
}

fn words_through_address(address: u32) -> u64 {
    u64::from(address).saturating_add(1)
}

fn push_bytes(
    output: &mut Vec<u8>,
    value: &[u8],
) -> Result<(), IrEncodingError> {
    push_usize(output, value.len())?;
    output.extend_from_slice(value);
    Ok(())
}

fn push_effect(
    output: &mut Vec<u8>,
    effect: EffectOp,
) -> Result<(), IrEncodingError> {
    push_observation(output, effect.before)?;
    push_observation(output, effect.after)?;
    match effect.input {
        None => output.push(0),
        Some(TraceInput::Byte(value)) => {
            output.push(1);
            output.push(value);
        },
        Some(TraceInput::EndOfInput) => output.push(2),
    }
    match effect.output {
        None => output.push(0),
        Some(value) => {
            output.push(1);
            output.push(value);
        },
    }
    push_memory_delta(output, effect.memory_delta);
    Ok(())
}

fn push_memory_delta(output: &mut Vec<u8>, delta: ProfileMemoryDelta) {
    push_memory_write(output, delta.data);
    push_memory_write(output, delta.encryption);
}

fn push_memory_write(output: &mut Vec<u8>, write: Option<ProfileMemoryWrite>) {
    match write {
        None => output.push(0),
        Some(change) => {
            output.push(1);
            push_u32(output, change.address);
            push_u32(output, change.before);
            push_u32(output, change.after);
        },
    }
}

fn push_observation(
    output: &mut Vec<u8>,
    observation: ProfileMachineObservation,
) -> Result<(), IrEncodingError> {
    push_usize(output, observation.input_consumed)?;
    push_usize(output, observation.output_len)?;
    push_u32(output, observation.registers.accumulator);
    push_u32(output, observation.registers.code_pointer);
    push_u32(output, observation.registers.data_pointer);
    push_termination(output, observation.termination);
    Ok(())
}

fn push_profile_requirement(
    output: &mut Vec<u8>,
    requirement: &TargetProfileRequirement,
) -> Result<(), IrEncodingError> {
    push_bytes(output, requirement.version.as_bytes())?;
    push_usize(output, requirement.features.len())?;
    for feature in &requirement.features {
        push_bytes(output, feature.as_bytes())?;
    }
    output.push(requirement.word_trits);
    push_u32(output, requirement.memory_words);
    Ok(())
}

fn push_run_outcome(
    output: &mut Vec<u8>,
    outcome: RunOutcome,
) -> Result<(), IrEncodingError> {
    match outcome {
        RunOutcome::BudgetExhausted { steps } => {
            output.push(0);
            push_usize(output, steps)?;
        },
        RunOutcome::Terminated { reason, steps } => {
            output.push(1);
            push_termination(output, Some(reason));
            push_usize(output, steps)?;
        },
    }
    Ok(())
}

fn push_termination(output: &mut Vec<u8>, termination: Option<Termination>) {
    output.push(match termination {
        None => 0,
        Some(Termination::HaltInstruction) => 1,
        Some(Termination::NonGraphicalCell) => 2,
    });
}

fn push_u16(output: &mut Vec<u8>, value: u16) {
    output.extend_from_slice(&value.to_le_bytes());
}

fn push_u32(output: &mut Vec<u8>, value: u32) {
    output.extend_from_slice(&value.to_le_bytes());
}

fn push_u64(output: &mut Vec<u8>, value: u64) {
    output.extend_from_slice(&value.to_le_bytes());
}

fn push_usize(
    output: &mut Vec<u8>,
    value: usize,
) -> Result<(), IrEncodingError> {
    let canonical = u64::try_from(value)
        .map_err(|_error| IrEncodingError::LengthOverflow)?;
    push_u64(output, canonical);
    Ok(())
}
