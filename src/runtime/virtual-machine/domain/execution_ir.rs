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
//   - Imported from the public `malbolge` domain surface.
// - Defaults:
//   - IR data is untrusted until a verifier-owned boundary admits it.
//

//! Portable bounded-region effect IR for tiered execution.

use std::collections::BTreeMap;
use std::fmt::{Display, Formatter, Result as FormatResult};

use crate::machine::{RunOutcome, StepOutcome, Termination};
use crate::profile::{ProfileDescriptor, TargetProfileRequirement};
use crate::profile_trace::{
    ProfileMachineObservation, ProfileMemoryDelta, ProfileMemoryRead,
    ProfileMemoryWrite, ProfileStepTrace,
};
use crate::profile_width::ProfileExecutionGeometry;
use crate::semantic_width::SEMANTIC_WIDTH_MINIMUM_TRITS;
use crate::trace::TraceInput;

/// Frozen narrow-profile portable effect-IR schema version.
pub const EFFECT_IR_VERSION: u16 = 3;
/// Portable effect-IR schema with a 64-bit profile-capacity field.
pub const EFFECT_IR_WIDE_PROFILE_VERSION: u16 = 4;
/// Portable effect-IR schema carrying explicit verified execution geometry.
pub const EFFECT_IR_EXECUTION_GEOMETRY_VERSION: u16 = 5;
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

/// Portable declarative execution geometry carried without verifier authority.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct ProfileExecutionGeometryRequirement {
    memory_words: u32,
    word_trits: u8,
}

/// Failure while validating one declarative execution geometry.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ProfileExecutionGeometryRequirementError {
    /// The declared memory length is not exactly `3^word_trits`.
    MemoryWords,
    /// The declared word width cannot be represented by the current `u32`
    /// execution-geometry envelope.
    WordWidth,
}

impl Display for ProfileExecutionGeometryRequirementError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::MemoryWords => f.write_str(
                "execution geometry memory is not the exact ternary capacity",
            ),
            Self::WordWidth => f.write_str(
                "execution geometry width exceeds the u32 capacity envelope",
            ),
        }
    }
}

impl ProfileExecutionGeometryRequirement {
    /// Returns the derived all-two-trit EOF value.
    #[must_use]
    pub const fn eof_word(self) -> u32 {
        self.memory_words.saturating_sub(1)
    }

    /// Projects visible geometry from one opaque trusted execution token.
    #[must_use]
    pub const fn from_execution_geometry(
        geometry: ProfileExecutionGeometry,
    ) -> Self {
        Self {
            memory_words: geometry.memory_words(),
            word_trits: geometry.word_trits(),
        }
    }

    /// Returns whether this declaration equals one canonical profile geometry.
    #[must_use]
    pub const fn is_canonical_for(self, profile: &ProfileDescriptor) -> bool {
        self.word_trits == profile.word_trits()
            && self.memory_words == profile.memory_words()
    }

    /// Returns the exact declared resident memory length.
    #[must_use]
    pub const fn memory_words(self) -> u32 {
        self.memory_words
    }

    /// Validates one portable declarative ternary execution geometry.
    ///
    /// This value is not proof authority. It can describe geometry carried by
    /// portable IR, while trusted runtime construction still requires an opaque
    /// [`ProfileExecutionGeometry`] emitted by independent verification.
    ///
    /// # Errors
    ///
    /// Returns [`ProfileExecutionGeometryRequirementError`] when `3^N` exceeds
    /// `u32` or the supplied memory length is not exactly `3^N`.
    pub fn new(
        word_trits: u8,
        memory_words: u32,
    ) -> Result<Self, ProfileExecutionGeometryRequirementError> {
        if usize::from(word_trits) < SEMANTIC_WIDTH_MINIMUM_TRITS {
            return Err(ProfileExecutionGeometryRequirementError::WordWidth);
        }
        let Some(expected) = ternary_memory_words(word_trits) else {
            return Err(ProfileExecutionGeometryRequirementError::WordWidth);
        };
        if memory_words != expected {
            return Err(ProfileExecutionGeometryRequirementError::MemoryWords);
        }
        Ok(Self { memory_words, word_trits })
    }

    /// Returns the exact declared ternary word modulus.
    #[must_use]
    pub const fn word_modulus(self) -> u32 {
        self.memory_words
    }

    /// Returns the declared ternary word width.
    #[must_use]
    pub const fn word_trits(self) -> u8 {
        self.word_trits
    }
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

/// V5 portable program that binds explicit execution geometry to ordinary IR.
///
/// The embedded geometry is declarative evidence, not verifier authority.
/// Native consumers continue to accept only [`RegionEffectProgram`] v3/v4 until
/// they independently verify and preserve derived-geometry proof constraints.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ExecutionGeometryRegionEffectProgram {
    execution_geometry: ProfileExecutionGeometryRequirement,
    program: RegionEffectProgram,
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
    /// IR v3 cannot encode a profile capacity wider than its unsigned 32-bit
    /// field.
    ProfileMemoryWordsOverflow,
    /// The declared effect-IR format version has no canonical encoder.
    UnsupportedFormatVersion,
}

/// Failure while projecting one complete normative step trace to portable IR.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum StepProgramProjectionError {
    /// Two semantic reads claim different values for the same address.
    ConflictingMemoryRead,
    /// The trace requires explicit-geometry v5 rather than legacy v3.
    ExecutionGeometry,
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

type ProfileStepProjection = (Vec<MemoryLiveIn>, RunOutcome);

impl ExecutionGeometryRegionEffectProgram {
    /// Renders canonical v5 bytes with explicit execution geometry.
    ///
    /// The canonical profile identity/requirement remains unchanged. Explicit
    /// execution width and capacity follow that profile requirement, so a
    /// derived geometry cannot masquerade as a different canonical profile.
    ///
    /// # Errors
    ///
    /// Returns [`IrEncodingError`] when a host-sized count cannot be encoded.
    pub fn canonical_bytes(&self) -> Result<Vec<u8>, IrEncodingError> {
        let mut bytes = Vec::new();
        bytes.extend_from_slice(IR_MAGIC);
        push_u16(&mut bytes, EFFECT_IR_EXECUTION_GEOMETRY_VERSION);
        push_bytes(&mut bytes, self.program.profile_id.as_bytes())?;
        push_bytes(&mut bytes, self.program.profile_fingerprint.as_bytes())?;
        push_profile_requirement(
            &mut bytes,
            &self.program.profile_requirement,
            EFFECT_IR_EXECUTION_GEOMETRY_VERSION,
        )?;
        push_execution_geometry(&mut bytes, self.execution_geometry);
        push_usize(&mut bytes, self.program.step_budget)?;
        push_run_outcome(&mut bytes, self.program.outcome)?;
        push_usize(&mut bytes, self.program.memory_live_ins.len())?;
        for live_in in &self.program.memory_live_ins {
            push_u32(&mut bytes, live_in.address);
            push_u32(&mut bytes, live_in.value);
        }
        push_usize(&mut bytes, self.program.effects.len())?;
        for effect in &self.program.effects {
            push_effect(&mut bytes, *effect)?;
        }
        Ok(bytes)
    }

    /// Returns the exact declarative execution geometry bound into v5.
    #[must_use]
    pub const fn execution_geometry(
        &self,
    ) -> ProfileExecutionGeometryRequirement {
        self.execution_geometry
    }

    /// Reports whether every directly addressed word fits execution geometry.
    #[must_use]
    pub fn fits_execution_geometry_capacity(&self) -> bool {
        self.required_memory_words()
            <= u64::from(self.execution_geometry.memory_words())
    }

    /// Reports whether every directly addressed word fits canonical capacity.
    #[must_use]
    pub fn fits_profile_capacity(&self) -> bool {
        self.required_memory_words()
            <= self.program.profile_requirement.memory_words
    }

    /// Returns the fixed explicit-geometry IR schema version.
    #[must_use]
    pub const fn format_version(&self) -> u16 {
        self.program.format_version
    }

    /// Projects one complete normative step trace to explicit-geometry v5 IR.
    ///
    /// Unlike [`RegionEffectProgram::from_profile_step_trace`], this projection
    /// preserves derived execution geometry. The canonical profile requirement
    /// remains canonical, and the result is still untrusted until a consumer
    /// independently admits the geometry/proof domain.
    ///
    /// # Errors
    ///
    /// Returns [`StepProgramProjectionError`] for rejected or internally
    /// inconsistent trace evidence.
    pub fn from_profile_step_trace(
        trace: &ProfileStepTrace,
    ) -> Result<Self, StepProgramProjectionError> {
        let (memory_live_ins, outcome) = project_profile_step_trace(trace)?;
        Ok(Self {
            execution_geometry:
                ProfileExecutionGeometryRequirement::from_execution_geometry(
                    trace.geometry,
                ),
            program: RegionEffectProgram {
                effects: vec![EffectOp::from_trace(trace)],
                format_version: EFFECT_IR_EXECUTION_GEOMETRY_VERSION,
                memory_live_ins,
                outcome,
                profile_fingerprint: String::from(trace.profile.fingerprint()),
                profile_id: String::from(trace.profile.id()),
                profile_requirement: TargetProfileRequirement::from_descriptor(
                    trace.profile,
                ),
                step_budget: 1,
            },
        })
    }

    /// Returns verifier-derived entry-memory live-ins.
    #[must_use]
    pub fn memory_live_ins(&self) -> &[MemoryLiveIn] {
        &self.program.memory_live_ins
    }

    /// Returns the verified bounded-run outcome.
    #[must_use]
    pub const fn outcome(&self) -> RunOutcome {
        self.program.outcome
    }

    /// Returns the canonical target-profile fingerprint.
    #[must_use]
    pub fn profile_fingerprint(&self) -> &str {
        &self.program.profile_fingerprint
    }

    /// Returns the exact declared canonical target-profile identity.
    #[must_use]
    pub fn profile_id(&self) -> &str {
        &self.program.profile_id
    }

    /// Returns the unchanged canonical target-profile requirement.
    #[must_use]
    pub const fn profile_requirement(&self) -> &TargetProfileRequirement {
        &self.program.profile_requirement
    }

    /// Returns the minimum directly addressed memory required by this region.
    #[must_use]
    pub fn required_memory_words(&self) -> u64 {
        required_memory_words(
            &self.program.memory_live_ins,
            &self.program.effects,
        )
    }

    /// Returns the verified semantic-step budget.
    #[must_use]
    pub const fn step_budget(&self) -> usize {
        self.program.step_budget
    }
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
    /// cannot fit the canonical unsigned 64-bit representation, or
    /// [`IrEncodingError::ProfileMemoryWordsOverflow`] when an envelope exceeds
    /// the frozen IR-v3 unsigned 32-bit profile-capacity field, or
    /// [`IrEncodingError::UnsupportedFormatVersion`] for an unknown schema.
    pub fn canonical_bytes(&self) -> Result<Vec<u8>, IrEncodingError> {
        if !is_canonical_effect_ir_version(self.format_version) {
            return Err(IrEncodingError::UnsupportedFormatVersion);
        }
        let mut bytes = Vec::new();
        bytes.extend_from_slice(IR_MAGIC);
        push_u16(&mut bytes, self.format_version);
        push_bytes(&mut bytes, self.profile_id.as_bytes())?;
        push_bytes(&mut bytes, self.profile_fingerprint.as_bytes())?;
        push_profile_requirement(
            &mut bytes,
            &self.profile_requirement,
            self.format_version,
        )?;
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
        self.required_memory_words() <= self.profile_requirement.memory_words
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
        if !trace_uses_canonical_geometry(trace) {
            return Err(StepProgramProjectionError::ExecutionGeometry);
        }
        let (memory_live_ins, outcome) = project_profile_step_trace(trace)?;
        Ok(Self {
            effects: vec![EffectOp::from_trace(trace)],
            format_version: EFFECT_IR_VERSION,
            memory_live_ins,
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
        required_memory_words(&self.memory_live_ins, &self.effects)
    }
}

fn project_profile_step_trace(
    trace: &ProfileStepTrace,
) -> Result<ProfileStepProjection, StepProgramProjectionError> {
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
    Ok((
        live_ins
            .into_iter()
            .map(|(address, value)| MemoryLiveIn { address, value })
            .collect(),
        outcome,
    ))
}

const fn trace_uses_canonical_geometry(trace: &ProfileStepTrace) -> bool {
    trace.geometry.word_trits() == trace.profile.word_trits()
        && trace.geometry.word_modulus() == trace.profile.word_modulus()
        && trace.geometry.memory_words() == trace.profile.memory_words()
        && trace.geometry.eof_word() == trace.profile.eof_word()
}

/// Reports whether the portable effect-IR schema has a canonical encoder.
#[must_use]
pub const fn is_canonical_effect_ir_version(format_version: u16) -> bool {
    matches!(
        format_version,
        EFFECT_IR_VERSION | EFFECT_IR_WIDE_PROFILE_VERSION
    )
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

fn required_memory_words(
    memory_live_ins: &[MemoryLiveIn],
    effects: &[EffectOp],
) -> u64 {
    let from_live_ins = memory_live_ins.iter().fold(0u64, |required, item| {
        required.max(words_through_address(item.address))
    });
    effects
        .iter()
        .copied()
        .fold(from_live_ins, |required, effect| {
            required.max(effect_required_memory_words(effect))
        })
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

const fn ternary_memory_words(word_trits: u8) -> Option<u32> {
    let mut value = 1u32;
    let mut index = 0u8;
    while index < word_trits {
        let Some(next) = value.checked_mul(3) else {
            return None;
        };
        value = next;
        index = index.saturating_add(1);
    }
    Some(value)
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

fn push_execution_geometry(
    output: &mut Vec<u8>,
    geometry: ProfileExecutionGeometryRequirement,
) {
    output.push(geometry.word_trits());
    push_u32(output, geometry.memory_words());
}

fn push_profile_requirement(
    output: &mut Vec<u8>,
    requirement: &TargetProfileRequirement,
    format_version: u16,
) -> Result<(), IrEncodingError> {
    push_bytes(output, requirement.version.as_bytes())?;
    push_usize(output, requirement.features.len())?;
    for feature in &requirement.features {
        push_bytes(output, feature.as_bytes())?;
    }
    output.push(requirement.word_trits);
    match format_version {
        EFFECT_IR_VERSION => {
            let memory_words = u32::try_from(requirement.memory_words)
                .map_err(|_error| {
                    IrEncodingError::ProfileMemoryWordsOverflow
                })?;
            push_u32(output, memory_words);
        },
        EFFECT_IR_WIDE_PROFILE_VERSION
        | EFFECT_IR_EXECUTION_GEOMETRY_VERSION => {
            push_u64(output, requirement.memory_words);
        },
        _ => return Err(IrEncodingError::UnsupportedFormatVersion),
    }
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
