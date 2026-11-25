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
//   - Finite coalesced source/guest I/O correspondence evidence.
// - Must-Not:
//   - Mistake observable replay for source-state or publication proof.
// - Allows:
//   - Inputs: frozen canonical C23 wire and actual graphical guests.
//   - Outputs: exact logical/physical effects and refusal regressions.
//   - Side effects: isolated normative VM executions.
// - Split-When:
//   - Recurrent source-state verification supersedes observational replay.
// - Merge-When:
//   - General translation verification covers the same obligations.
// - Summary:
//   - Check exact EOF chronology and independently selected source effects.

use std::str;

use malbolge::{TraceInput, current_profile, decode_profile_instruction};

use super::super::super::build_relocated_recurrent_checksum_source;
use super::{
    Effect, Error, MAX_RECURRENT_IO_STEPS, SourceProjection,
    SourceRecurrentIoProbe, lower_canonical_dynamic_cfg, project_function,
    verify_source_recurrent_io,
};

const WIRE: &str = include_str!("typed-ir/golden/mutable-eof-checksum.hex");
pub(super) const VECTORS: [&[u8]; 5] =
    [&[], &[0], &[255], &[1, 0, 128, 254], &[5, 0, 129]];

pub(super) fn checksum_wire() -> Result<Vec<u8>, String> {
    let hex = WIRE
        .trim_end()
        .strip_prefix("malbolge-typed-ir-v1:")
        .ok_or("canonical fixture header")?;
    let (pairs, remainder) = hex.as_bytes().as_chunks::<2>();
    if !remainder.is_empty() {
        return Err("odd canonical wire length".to_owned());
    }
    pairs
        .iter()
        .map(|pair| {
            let text =
                str::from_utf8(pair).map_err(|error| error.to_string())?;
            u8::from_str_radix(text, 16).map_err(|error| error.to_string())
        })
        .collect()
}

pub(super) const fn checksum(state: u8, byte: u8) -> u8 {
    let result = if byte & 1 == 0 {
        state.wrapping_add(byte)
    } else {
        state ^ byte
    };
    result.wrapping_add(3)
}

fn check_projection(
    projected: &SourceProjection,
    input: &[u8],
    expected: u8,
) -> Result<(), String> {
    if projected.return_block != 6
        || projected.function != 0
        || projected.bytes_consumed != input.len()
        || projected.events.len() != input.len().saturating_add(2)
    {
        return Err("incorrect complete source projection".to_owned());
    }
    let mut expected_inputs = input
        .iter()
        .copied()
        .map(TraceInput::Byte)
        .chain([TraceInput::EndOfInput]);
    let reads = projected
        .events
        .iter()
        .take(projected.events.len().saturating_sub(1));
    for (index, (observed, expected_input)) in
        reads.zip(&mut expected_inputs).enumerate()
    {
        let site = if index == 0 {
            (0, 1)
        } else {
            (5, 2)
        };
        if observed.effect != Effect::Input(expected_input)
            || (observed.block, observed.ordinal) != site
        {
            return Err(format!("wrong logical input occurrence {index}"));
        }
    }
    if expected_inputs.next().is_some()
        || projected.events.last().map(|event| event.effect)
            != Some(Effect::Output(expected))
        || projected.events.last().map(|event| event.block) != Some(6)
    {
        return Err("incorrect final source output".to_owned());
    }
    Ok(())
}

// From zero, the first update maps the entire byte domain bijectively
// onto every possible committed state. Each two-byte stream therefore
// visits one of the 65,536 state/byte transitions of the real typed CFG.
#[test]
fn source_recurrent_io_all_source_state_transitions() -> Result<(), String> {
    let wire = checksum_wire()?;
    let cfg = lower_canonical_dynamic_cfg(&wire)
        .map_err(|error| format!("canonical checksum: {error:?}"))?;
    let [function] = cfg.functions.as_slice() else {
        return Err("expected one checksum function".to_owned());
    };
    for first in u8::MIN..=u8::MAX {
        let prior = checksum(0, first);
        let eof = project_function(function, &[first], None)
            .map_err(|error| format!("source EOF after {first}: {error:?}"))?;
        check_projection(&eof, &[first], prior)?;
        for second in u8::MIN..=u8::MAX {
            let stream = [first, second];
            let projected = project_function(function, &stream, None)
                .map_err(|error| format!("source {stream:?}: {error:?}"))?;
            check_projection(&projected, &stream, checksum(prior, second))?;
        }
    }
    Ok(())
}

#[test]
fn source_recurrent_io_frozen_guest_vectors_and_coalesced_sites()
-> Result<(), String> {
    let wire = checksum_wire()?;
    let cfg = lower_canonical_dynamic_cfg(&wire)
        .map_err(|error| format!("canonical checksum: {error:?}"))?;
    let guest = build_relocated_recurrent_checksum_source(current_profile())
        .map_err(|error| format!("recurrent guest: {error:?}"))?;
    for stream in VECTORS {
        let proof = verify_source_recurrent_io(SourceRecurrentIoProbe {
            canonical: &wire,
            input: stream,
            physical_source: &guest.capture.source,
            step_budget: MAX_RECURRENT_IO_STEPS,
        })
        .map_err(|error| format!("guest {stream:?}: {error:?}"))?;
        if proof.source_sha256 != cfg.source_sha256
            || proof.source_return_block != 6
            || proof.bytes_consumed != stream.len()
            || proof.observations.len() != stream.len().saturating_add(2)
            || proof.guest_steps <= 100_000
            || proof.guest_halt_address != guest.capture.halt
            || proof.observations.windows(2).any(|window| {
                let [first, second] = window else {
                    return true;
                };
                first.trace_index >= second.trace_index
            })
        {
            return Err(format!("invalid coalesced receipt: {stream:?}"));
        }
        check_guest_effects(
            &proof.observations,
            stream,
            guest.capture.input,
            guest.capture.output,
        )?;
    }
    Ok(())
}

fn check_guest_effects(
    observations: &[super::SourceRecurrentIoObservation],
    stream: &[u8],
    input_address: u32,
    output_address: u32,
) -> Result<(), String> {
    let inputs = stream
        .iter()
        .copied()
        .map(TraceInput::Byte)
        .chain([TraceInput::EndOfInput]);
    for (index, (actual, input)) in observations.iter().zip(inputs).enumerate()
    {
        let site = if index == 0 {
            (0, 1)
        } else {
            (5, 2)
        };
        if actual.function != 0
            || (actual.block, actual.ordinal) != site
            || actual.code_address != input_address
            || actual.effect != Effect::Input(input)
            || actual.raw_accumulator
                != match input {
                    TraceInput::Byte(byte) => u32::from(byte),
                    TraceInput::EndOfInput => current_profile().eof_word(),
                }
        {
            return Err(format!("wrong shared input site: {actual:?}"));
        }
    }
    let expected = stream.iter().copied().fold(0u8, checksum);
    let output = observations.last().ok_or("missing real output")?;
    if output.effect != Effect::Output(expected)
        || output.block != 6
        || output.code_address != output_address
        || output.raw_accumulator.rem_euclid(256) != u32::from(expected)
    {
        return Err(format!("wrong shared output: {output:?}"));
    }
    Ok(())
}

fn graphical(opcodes: &[u8]) -> Result<Vec<u8>, String> {
    opcodes
        .iter()
        .copied()
        .enumerate()
        .map(|(position, opcode)| {
            let address =
                u32::try_from(position).map_err(|error| error.to_string())?;
            (33..=126u8)
                .find(|cell| {
                    decode_profile_instruction(u32::from(*cell), address)
                        == Some(opcode)
                })
                .ok_or_else(|| format!("cannot encode {opcode} at {position}"))
        })
        .collect()
}

#[test]
fn source_recurrent_io_rejects_missing_reordered_and_wrong_guest_io()
-> Result<(), String> {
    let wire = checksum_wire()?;
    for opcodes in [
        b"/ov".as_slice(), // missing output after true EOF
        b"</v".as_slice(), // correct zero output, but before EOF
        b"//v".as_slice(), // extra true EOF
        b"/<v".as_slice(), // raw EOF residue is not the C output zero
    ] {
        let physical = graphical(opcodes)?;
        if verify_source_recurrent_io(SourceRecurrentIoProbe {
            canonical: &wire,
            input: &[],
            physical_source: &physical,
            step_budget: 8,
        }) != Err(Error::GuestIoMismatch)
        {
            return Err(format!("unexpected acceptance: {opcodes:?}"));
        }
    }
    Ok(())
}

#[test]
fn source_recurrent_io_preserves_explicit_limits_and_source_admission()
-> Result<(), String> {
    let wire = checksum_wire()?;
    let physical = graphical(b"/ov")?;
    let probe = SourceRecurrentIoProbe {
        canonical: &wire,
        input: &[],
        physical_source: &physical,
        step_budget: 1,
    };
    for step_budget in [0, MAX_RECURRENT_IO_STEPS.saturating_add(1)] {
        if verify_source_recurrent_io(SourceRecurrentIoProbe {
            step_budget,
            ..probe
        }) != Err(Error::InvalidProbeBound)
        {
            return Err("invalid ceiling accepted".to_owned());
        }
    }
    if verify_source_recurrent_io(probe) != Err(Error::GuestBudgetExhausted) {
        return Err("short guest budget accepted".to_owned());
    }
    let corrupt = b"not canonical";
    if verify_source_recurrent_io(SourceRecurrentIoProbe {
        canonical: corrupt,
        ..probe
    }) != Err(Error::InvalidCanonicalSource)
    {
        return Err("noncanonical source accepted".to_owned());
    }
    let guest = build_relocated_recurrent_checksum_source(current_profile())
        .map_err(|error| format!("recurrent guest: {error:?}"))?;
    if verify_source_recurrent_io(SourceRecurrentIoProbe {
        physical_source: &guest.capture.source,
        step_budget: 100_000,
        ..probe
    }) != Err(Error::GuestBudgetExhausted)
    {
        return Err(
            "experimental replay weakened the publication limit".to_owned()
        );
    }
    Ok(())
}
