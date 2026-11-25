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
//   - Composition of the carried source state and signed EOF guard witnesses.
// - Must-Not:
//   - Authorize all original SSA storage, edges or guest publication.
// - Allows:
//   - Inputs: compatible state and guard probes against the same guest.
//   - Outputs: paired source/physical checkpoints in a single actual replay.
// - Split-When:
//   - Multiple carried scalars or branch shapes need independent policies.
// - Merge-When:
//   - Full original source-frame verification owns this correspondence.
// - Summary:
//   - Authenticate both loop-header values at the same physical reads.

//! Coherent finite loop bindings, not a complete source-frame certificate.

use super::source_recurrent_guard::GuardPlan;
use super::source_recurrent_state::{StatePlan, validate_geometry};
use super::{
    Effect, Error, ReplayAudits, SourceRecurrentGuardCheckpoint,
    SourceRecurrentGuardProbe, SourceRecurrentIoProof,
    SourceRecurrentStateCheckpoint, SourceRecurrentStateProbe, admit_probe,
    project_function_with_guard, replay_guest,
};

/// Propose the guard and carried state of the same recurrent loop.
#[derive(Clone, Copy, Debug)]
pub struct SourceRecurrentLoopProbe<'source> {
    /// Signed input and EOF guard placement.
    pub guard: SourceRecurrentGuardProbe<'source>,
    /// Selected unsigned carried-state placement.
    pub state: SourceRecurrentStateProbe<'source>,
}

/// Both independently selected source values at one physical read.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct SourceRecurrentLoopCheckpoint {
    /// Actual capture and class-dependent dispatch after the read.
    pub guard: SourceRecurrentGuardCheckpoint,
    /// Actual carried-state stores and words preceding the same read.
    pub state: SourceRecurrentStateCheckpoint,
}

/// One finite source/guest trace authenticating both selected loop phis.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct SourceRecurrentLoopProof {
    /// Both bindings in chronological order at every matched signed read.
    pub checkpoints: Vec<SourceRecurrentLoopCheckpoint>,
    /// The single shared I/O and termination receipt.
    pub io: SourceRecurrentIoProof,
    /// Canonical source header of both phis.
    pub loop_header: u32,
    /// The signed input phi identity independently selected by the guard.
    pub signed_phi: u32,
    /// The selected unsigned byte-state phi identity.
    pub unsigned_phi: u32,
    /// Low and high state words authenticated by the physical trace.
    pub word_addresses: [u32; 2],
}

pub(super) fn compatible(
    probe: &SourceRecurrentLoopProbe<'_>,
) -> Result<(), Error> {
    let guard = &probe.guard;
    let state = &probe.state;
    let loop_header = state.loop_header;
    if guard.io != state.io
        || guard.input_address != state.input_address
        || guard.source_header != loop_header
        || state.words.iter().any(|word| {
            *word == guard.capture_word
                || guard.classifier_words.contains(word)
                || *word == guard.byte_landing
                || guard.eof_landings.contains(word)
        })
    {
        return Err(Error::InvalidLoopBinding);
    }
    validate_geometry(state)
}

pub(super) fn pair_checkpoints(
    guard: Vec<SourceRecurrentGuardCheckpoint>,
    state: Vec<SourceRecurrentStateCheckpoint>,
    io: &SourceRecurrentIoProof,
) -> Result<Vec<SourceRecurrentLoopCheckpoint>, Error> {
    let reads = io
        .observations
        .iter()
        .filter(|event| matches!(event.effect, Effect::Input(_)));
    if guard.len() != state.len() || guard.len() != reads.clone().count() {
        return Err(Error::GuestLoopMismatch);
    }
    let mut result = Vec::with_capacity(guard.len());
    let mut last_dispatch = None;
    for ((guard_checkpoint, state_checkpoint), read) in
        guard.into_iter().zip(state).zip(reads)
    {
        let read_index = read.trace_index;
        if guard_checkpoint.input_index != read_index
            || state_checkpoint.trace_index != read_index
            || state_checkpoint.block != read.block
            || state_checkpoint.ordinal != read.ordinal
            || state_checkpoint.code_address != read.code_address
            || guard_checkpoint.guard_index <= read_index
            || state_checkpoint.write_indices.iter().any(|write| {
                *write >= read_index
                    || last_dispatch.is_some_and(|previous| *write <= previous)
            })
        {
            return Err(Error::GuestLoopMismatch);
        }
        last_dispatch = Some(guard_checkpoint.guard_index);
        result.push(SourceRecurrentLoopCheckpoint {
            guard: guard_checkpoint,
            state: state_checkpoint,
        });
    }
    Ok(result)
}

/// Independently evaluate both original loop-header phis and authenticate
/// their physical bindings in one complete normative execution.
///
/// Both proposals must refer to exactly the same source wire, guest image,
/// input, budget, loop header and physical signed-read site. Carried-state
/// words cannot alias the capture, classifier words or branch landings.
/// Every paired receipt refers to the very same actual read; after the
/// initial load, both state stores must follow the previous guard dispatch.
///
/// # Errors
///
/// Refuses incompatible placements, ordinary source/guest failures, an
/// invalid state or guard witness, or noncorresponding paired checkpoints.
/// This verifies the two selected bindings, not the complete source frame.
pub fn verify_source_recurrent_loop(
    probe: &SourceRecurrentLoopProbe<'_>,
) -> Result<SourceRecurrentLoopProof, Error> {
    compatible(probe)?;
    let io = probe.guard.io;
    let cfg = admit_probe(io)?;
    let [function] = cfg.functions.as_slice() else {
        return Err(Error::UnsupportedSourceExecution);
    };
    let guard_plan = GuardPlan::new(function, probe.guard.source_header)?;
    let state_plan = StatePlan::new(function, &probe.state)?;
    let projected = project_function_with_guard(
        function,
        io.input,
        Some(&state_plan),
        Some(&guard_plan),
    )?;
    let replay =
        replay_guest(io, &projected, cfg.source_sha256, &ReplayAudits {
            guard: Some(&probe.guard),
            state: Some(&probe.state),
            transition: None,
        })?;
    let guard = replay.guard.ok_or(Error::InvalidLoopBinding)?;
    let state = replay.state.ok_or(Error::InvalidLoopBinding)?;
    let checkpoints =
        pair_checkpoints(guard.checkpoints, state.checkpoints, &replay.io)?;
    Ok(SourceRecurrentLoopProof {
        checkpoints,
        io: replay.io,
        loop_header: probe.guard.source_header,
        signed_phi: guard_plan.phi,
        unsigned_phi: probe.state.phi_result,
        word_addresses: probe.state.words,
    })
}

#[cfg(test)]
#[path = "../../../../tests/compiler/source_recurrent_loop.rs"]
mod source_recurrent_loop_tests;
