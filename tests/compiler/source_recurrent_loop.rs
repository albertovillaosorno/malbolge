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
//   - Combined loop-header state and signed guard regressions.
// - Must-Not:
//   - Authorize source publication or assume full SSA storage.
// - Allows:
//   - Inputs: original typed checksum and actual graphical guest.
//   - Outputs: paired finite receipts and incompatible-binding refusals.
//   - Side effects: isolated normative VM execution.
// - Split-When:
//   - Multiple carried states require independent witness policies.
// - Merge-When:
//   - General source-frame verification subsumes both bindings.
// - Summary:
//   - Test both selected original loop phis against one physical read.

use malbolge::{TraceInput, current_profile};

use super::super::super::super::{
    RelocatedRecurrentChecksumSource, build_relocated_recurrent_checksum_source,
};
use super::super::source_recurrent_guard::source_recurrent_guard_tests;
use super::super::source_recurrent_io_tests::{
    VECTORS, checksum, checksum_wire,
};
use super::super::source_recurrent_state::source_recurrent_state_tests;
use super::{
    Effect, Error, SourceRecurrentGuardProbe, SourceRecurrentLoopProbe,
    SourceRecurrentLoopProof, SourceRecurrentStateProbe, pair_checkpoints,
    verify_source_recurrent_loop,
};

fn proposal<'source>(
    wire: &'source [u8],
    stream: &'source [u8],
    guest: &'source RelocatedRecurrentChecksumSource,
) -> Result<SourceRecurrentLoopProbe<'source>, String> {
    Ok(SourceRecurrentLoopProbe {
        guard: source_recurrent_guard_tests::proposal(wire, stream, guest),
        state: source_recurrent_state_tests::proposal(wire, stream, guest)?,
    })
}

fn check_loop(
    proof: &SourceRecurrentLoopProof,
    stream: &[u8],
    probe: &SourceRecurrentLoopProbe<'_>,
) -> Result<(), String> {
    if proof.signed_phi != 7
        || proof.unsigned_phi != 8
        || proof.loop_header != 1
        || proof.word_addresses != probe.state.words
        || proof.checkpoints.len() != stream.len().saturating_add(1)
        || proof.io.bytes_consumed != stream.len()
    {
        return Err(format!("wrong loop receipt: {proof:?}"));
    }
    let mut state = 0u8;
    let mut last_dispatch = None;
    for (index, (checkpoint, io)) in proof
        .checkpoints
        .iter()
        .zip(&proof.io.observations)
        .enumerate()
    {
        let expected = stream.get(index).copied();
        let (read, target, signed_bits) = expected
            .map_or((TraceInput::EndOfInput, 6, u32::MAX), |byte| {
                (TraceInput::Byte(byte), 2, u32::from(byte))
            });
        if checkpoint.state.value != state
            || checkpoint.guard.signed_bits != signed_bits
            || checkpoint.guard.target != target
            || checkpoint.state.trace_index != checkpoint.guard.input_index
            || checkpoint.state.trace_index != io.trace_index
            || io.effect != Effect::Input(read)
            || checkpoint.state.write_indices.iter().any(|write| {
                *write >= io.trace_index
                    || last_dispatch.is_some_and(|previous| *write <= previous)
            })
        {
            return Err(format!("wrong pair at read {index}: {checkpoint:?}"));
        }
        if let Some(byte) = expected {
            state = checksum(state, byte);
        }
        last_dispatch = Some(checkpoint.guard.guard_index);
    }
    if proof.io.observations.last().map(|event| event.effect)
        != Some(Effect::Output(state))
    {
        return Err("wrong final output".to_owned());
    }
    Ok(())
}

#[test]
fn source_recurrent_loop_five_complete_guest_replays() -> Result<(), String> {
    let wire = checksum_wire()?;
    let guest = build_relocated_recurrent_checksum_source(current_profile())
        .map_err(|error| format!("guest: {error:?}"))?;
    for stream in VECTORS {
        let probe = proposal(&wire, stream, &guest)?;
        let proof = verify_source_recurrent_loop(&probe)
            .map_err(|error| format!("loop {stream:?}: {error:?}"))?;
        check_loop(&proof, stream, &probe)?;
    }
    Ok(())
}

fn mismatched_execution<'source>(
    probe: &SourceRecurrentLoopProbe<'source>,
) -> [SourceRecurrentLoopProbe<'source>; 2] {
    let wrong_input = SourceRecurrentStateProbe {
        io: super::super::SourceRecurrentIoProbe {
            input: &[255],
            ..probe.state.io
        },
        ..probe.state
    };
    let wrong_budget = SourceRecurrentGuardProbe {
        io: super::super::SourceRecurrentIoProbe {
            step_budget: probe.guard.io.step_budget.saturating_sub(1),
            ..probe.guard.io
        },
        ..probe.guard
    };
    [
        SourceRecurrentLoopProbe {
            state: wrong_input,
            ..*probe
        },
        SourceRecurrentLoopProbe {
            guard: wrong_budget,
            ..*probe
        },
    ]
}

#[test]
fn source_recurrent_loop_refuses_inconsistent_proposals() -> Result<(), String>
{
    let wire = checksum_wire()?;
    let guest = build_relocated_recurrent_checksum_source(current_profile())
        .map_err(|error| format!("guest: {error:?}"))?;
    let probe = proposal(&wire, &[0], &guest)?;
    let mismatched = [
        SourceRecurrentLoopProbe {
            state: SourceRecurrentStateProbe {
                input_address: probe.guard.fold_address,
                ..probe.state
            },
            ..probe
        },
        SourceRecurrentLoopProbe {
            guard: SourceRecurrentGuardProbe {
                source_header: 2,
                ..probe.guard
            },
            ..probe
        },
        SourceRecurrentLoopProbe {
            guard: SourceRecurrentGuardProbe {
                capture_word: probe.state.words[0],
                ..probe.guard
            },
            ..probe
        },
        SourceRecurrentLoopProbe {
            guard: SourceRecurrentGuardProbe {
                byte_landing: probe.state.words[1],
                ..probe.guard
            },
            ..probe
        },
    ];
    for invalid in mismatched_execution(&probe).into_iter().chain(mismatched) {
        if verify_source_recurrent_loop(&invalid)
            != Err(Error::InvalidLoopBinding)
        {
            return Err("inconsistent loop proposals accepted".to_owned());
        }
    }
    Ok(())
}

#[test]
fn source_recurrent_loop_refuses_reordered_or_forged_receipts()
-> Result<(), String> {
    let wire = checksum_wire()?;
    let guest = build_relocated_recurrent_checksum_source(current_profile())
        .map_err(|error| format!("guest: {error:?}"))?;
    let probe = proposal(&wire, &[255], &guest)?;
    let proof = verify_source_recurrent_loop(&probe)
        .map_err(|error| format!("loop: {error:?}"))?;
    let guard: Vec<_> =
        proof.checkpoints.iter().map(|pair| pair.guard).collect();
    let state: Vec<_> =
        proof.checkpoints.iter().map(|pair| pair.state).collect();
    let mut reversed = guard.clone();
    reversed.reverse();
    let mut forged = state.clone();
    let prior = guard.first().ok_or("missing initial guard")?.guard_index;
    let backedge = forged.get_mut(1).ok_or("missing state backedge")?;
    backedge.write_indices = [prior; 2];
    for (guards, states) in [
        (reversed, state),
        (guard.clone(), forged),
        (guard, Vec::new()),
    ] {
        if pair_checkpoints(guards, states, &proof.io)
            != Err(Error::GuestLoopMismatch)
        {
            return Err("incoherent loop receipt accepted".to_owned());
        }
    }
    Ok(())
}
