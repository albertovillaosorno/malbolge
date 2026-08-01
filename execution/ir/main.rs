// File:
//   - main.rs
// Path:
//   - execution/ir/main.rs
//
// Copyright:
//   - Copyright (c) 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - MIT
// Confidential:
//   - false
// License-File:
//   - LICENSE
// Path-Rule:
//   - All paths in this header are repository-root relative.
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
// Related documents:
// - docs/technical/adr/tiered-native-execution.md
// - docs/technical/adr/verification-trust-boundary.md
//
// Large file:
//   - false
//

//! Portable bounded-region effect IR for tiered execution.

use malbolge::{
    ProfileMachineObservation, ProfileMemoryDelta, ProfileMemoryWrite,
    ProfileStepTrace, RunOutcome, Termination, TraceInput,
};

/// First portable bounded-region effect-IR schema version.
pub const EFFECT_IR_VERSION: u16 = 2;
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
