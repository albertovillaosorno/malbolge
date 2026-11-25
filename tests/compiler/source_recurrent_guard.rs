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
//   - Independent signed source guard and physical dispatch witness tests.
// - Must-Not:
//   - Admit the full source frame or change the publication ceiling.
// - Allows:
//   - Inputs: frozen source wire, graphical guest and finite byte vectors.
//   - Outputs: chronological guard receipts and fail-closed controls.
//   - Side effects: isolated normative VM execution.
// - Split-When:
//   - General source control requires additional physical witnesses.
// - Merge-When:
//   - Full source-frame verification incorporates signed EOF dispatch.
// - Summary:
//   - Check the source signed phi against real capture and class transfers.

use std::collections::BTreeSet;

use malbolge::{TraceInput, current_profile, decode_profile_instruction};

use super::super::super::super::{
    RelocatedRecurrentChecksumSource, build_relocated_recurrent_checksum_source,
};
use super::super::source_recurrent_io_tests::{VECTORS, checksum_wire};
use super::super::{
    MAX_RECURRENT_IO_STEPS, SourceProjection, verify_source_recurrent_io,
};
use super::{
    Effect, Error, GuardPlan, SourceRecurrentGuardCheckpoint,
    SourceRecurrentGuardProbe, SourceRecurrentGuardProof,
    SourceRecurrentIoProbe, TernaryCfgScalarKind, TernaryCfgTerminator,
    TernaryOperation, admit_probe, project_function_with_guard,
    verify_source_recurrent_guard,
};

const BYTE: u32 = 7_180_651;
const EOF_EVEN: u32 = 7_179_922;
const EOF_ODD: u32 = 7_178_464;

fn proposal<'source>(
    wire: &'source [u8],
    stream: &'source [u8],
    guest: &'source RelocatedRecurrentChecksumSource,
) -> SourceRecurrentGuardProbe<'source> {
    let capture = &guest.capture;
    SourceRecurrentGuardProbe {
        branch_address: capture.branch,
        byte_landing: BYTE,
        capture_word: capture.capture,
        classifier_words: capture.states,
        eof_landings: [EOF_ODD, EOF_EVEN],
        fold_address: capture.crazy,
        input_address: capture.input,
        io: SourceRecurrentIoProbe {
            canonical: wire,
            input: stream,
            physical_source: &capture.source,
            step_budget: MAX_RECURRENT_IO_STEPS,
        },
        source_header: 1,
    }
}

// Independently map raw trits 0 -> 1, 1 -> 0, 2 -> 2. Applying
// the same encoding twice must recover the byte or distinct EOF word.
fn encode(mut raw: u32) -> u32 {
    let mut value = 0u32;
    let mut place = 1u32;
    for _ in 0..15u8 {
        let digit = match raw.rem_euclid(3) {
            0 => 1u32,
            2 => 2u32,
            _ => 0u32,
        };
        value = value.saturating_add(digit.saturating_mul(place));
        raw = raw.div_euclid(3);
        place = place.saturating_mul(3);
    }
    value
}

fn source_checkpoint_values(
    projection: &SourceProjection,
    stream: &[u8],
) -> Result<(), String> {
    let mut expected = stream
        .iter()
        .copied()
        .map(TraceInput::Byte)
        .chain([TraceInput::EndOfInput]);
    for (index, event) in projection.events.iter().enumerate() {
        if let Effect::Input(input) = event.effect {
            let guard = event.guard.ok_or("missing source guard")?;
            let (site, read_result) = if index == 0 {
                ((0, 1), 1)
            } else {
                ((5, 2), 19)
            };
            let (bits, target) = match input {
                TraceInput::Byte(byte) => (u32::from(byte), 2),
                TraceInput::EndOfInput => (u32::MAX, 6),
            };
            if Some(input) != expected.next()
                || (event.block, event.ordinal) != site
                || guard.read_result != read_result
                || guard.signed_bits != bits
                || guard.target != target
                || guard.condition != 9
            {
                return Err("wrong source signed input or branch".to_owned());
            }
        } else if event.guard.is_some() {
            return Err("guard attached to non-input".to_owned());
        }
    }
    if expected.next().is_some() {
        return Err("missing source guard occurrence".to_owned());
    }
    Ok(())
}

#[test]
fn source_recurrent_guard_all_signed_values_at_both_read_sites()
-> Result<(), String> {
    let wire = checksum_wire()?;
    let cfg = super::super::lower_canonical_dynamic_cfg(&wire)
        .map_err(|error| format!("source: {error:?}"))?;
    let [function] = cfg.functions.as_slice() else {
        return Err("one checksum function required".to_owned());
    };
    let plan = GuardPlan::new(function, 1)
        .map_err(|error| format!("guard: {error:?}"))?;
    let signed_phi = function
        .blocks
        .get(1)
        .and_then(|header| {
            header
                .phis
                .iter()
                .find(|phi| phi.type_kind == TernaryCfgScalarKind::I32)
        })
        .ok_or("signed phi missing")?;
    if signed_phi.result != 7 || plan.phi != 7 {
        return Err("wrong signed phi binding".to_owned());
    }
    for byte in u8::MIN..=u8::MAX {
        // The same byte is evaluated as both the first and recurrent read.
        for stream in [vec![byte], vec![0, byte]] {
            let projection = project_function_with_guard(
                function,
                &stream,
                None,
                Some(&plan),
            )
            .map_err(|error| format!("guard source {stream:?}: {error:?}"))?;
            source_checkpoint_values(&projection, &stream)?;
        }
    }
    let empty = project_function_with_guard(function, &[], None, Some(&plan))
        .map_err(|error| format!("empty source: {error:?}"))?;
    source_checkpoint_values(&empty, &[])
}

fn ordered_folds(checkpoint: &SourceRecurrentGuardCheckpoint) -> bool {
    checkpoint
        .fold_indices
        .first()
        .is_some_and(|fold| *fold > checkpoint.input_index)
        && checkpoint
            .fold_indices
            .last()
            .is_some_and(|fold| *fold < checkpoint.guard_index)
        && checkpoint
            .fold_indices
            .windows(2)
            .all(|pair| matches!(pair, [before, after] if before < after))
}

fn check_guest(
    proof: &SourceRecurrentGuardProof,
    stream: &[u8],
    probe: &SourceRecurrentGuardProbe<'_>,
) -> Result<u32, String> {
    if proof.checkpoints.len() != stream.len().saturating_add(1)
        || proof.source_header != probe.source_header
    {
        return Err("incomplete guard receipt".to_owned());
    }
    let mut next_index = None;
    let mut eof_landing = None;
    for (index, (checkpoint, io)) in proof
        .checkpoints
        .iter()
        .zip(&proof.io.observations)
        .enumerate()
    {
        let (bits, raw, target) = stream
            .get(index)
            .map_or((u32::MAX, current_profile().eof_word(), 6), |byte| {
                (u32::from(*byte), u32::from(*byte), 2)
            });
        let valid_landing = if bits == u32::MAX {
            eof_landing = Some(checkpoint.guest_landing);
            probe.eof_landings.contains(&checkpoint.guest_landing)
        } else {
            checkpoint.guest_landing == probe.byte_landing
        };
        if checkpoint.input_index != io.trace_index
            || checkpoint.signed_bits != bits
            || checkpoint.raw_input != raw
            || checkpoint.encoded_input != encode(raw)
            || encode(checkpoint.encoded_input) != raw
            || checkpoint.read_result
                != if index == 0 {
                    1
                } else {
                    19
                }
            || checkpoint.condition != 9
            || checkpoint.target != target
            || !valid_landing
            || checkpoint
                .fold_results
                .last()
                .and_then(|word| word.checked_add(1))
                != Some(checkpoint.guest_landing)
            || !ordered_folds(checkpoint)
            || next_index.is_some_and(|prior| io.trace_index <= prior)
        {
            return Err(format!(
                "incorrect signed guard receipt: {checkpoint:?}"
            ));
        }
        next_index = Some(checkpoint.guard_index);
    }
    if proof.source_phi != 7 {
        return Err("incorrect canonical signed phi".to_owned());
    }
    eof_landing.ok_or_else(|| "missing EOF dispatch".to_owned())
}

#[test]
fn source_recurrent_guard_five_complete_guest_vectors() -> Result<(), String> {
    let wire = checksum_wire()?;
    let guest = build_relocated_recurrent_checksum_source(current_profile())
        .map_err(|error| format!("guest: {error:?}"))?;
    let mut eof_landings = BTreeSet::new();
    for stream in VECTORS {
        let probe = proposal(&wire, stream, &guest);
        let proof = verify_source_recurrent_guard(&probe)
            .map_err(|error| format!("guard {stream:?}: {error:?}"))?;
        let _new = eof_landings.insert(check_guest(&proof, stream, &probe)?);
    }
    if eof_landings != BTreeSet::from([EOF_ODD, EOF_EVEN]) {
        return Err("missing one physical EOF landing".to_owned());
    }
    Ok(())
}

#[test]
fn source_recurrent_guard_rejects_invalid_source_or_geometry()
-> Result<(), String> {
    let wire = checksum_wire()?;
    let guest = build_relocated_recurrent_checksum_source(current_profile())
        .map_err(|error| format!("guest: {error:?}"))?;
    let probe = proposal(&wire, &[], &guest);
    for invalid in [
        SourceRecurrentGuardProbe {
            source_header: 0,
            ..probe
        },
        SourceRecurrentGuardProbe {
            source_header: 2,
            ..probe
        },
        SourceRecurrentGuardProbe {
            fold_address: probe.input_address,
            ..probe
        },
        SourceRecurrentGuardProbe {
            capture_word: probe.input_address,
            ..probe
        },
        SourceRecurrentGuardProbe {
            classifier_words: [probe.capture_word; 6],
            ..probe
        },
        SourceRecurrentGuardProbe {
            eof_landings: [BYTE, EOF_ODD],
            ..probe
        },
    ] {
        if verify_source_recurrent_guard(&invalid)
            != Err(Error::InvalidGuardBinding)
        {
            return Err("invalid source or guard placement accepted".to_owned());
        }
    }

    let cfg =
        admit_probe(probe.io).map_err(|error| format!("source: {error:?}"))?;
    let [function] = cfg.functions.as_slice() else {
        return Err("expected one source function".to_owned());
    };
    let mut changed = function.clone();
    let header = changed.blocks.get_mut(1).ok_or("source header")?;
    let TernaryCfgTerminator::Branch { condition, .. } = header.terminator
    else {
        return Err("source branch missing".to_owned());
    };
    for operation in &mut header.operations {
        if let TernaryOperation::NotEqualI32 { result, .. } = operation
            && *result == condition
        {
            *result = u32::MAX;
        }
    }
    if GuardPlan::new(&changed, 1).is_ok() {
        return Err("unbound source predicate accepted".to_owned());
    }
    Ok(())
}

#[test]
fn source_recurrent_guard_refuses_false_binding_despite_correct_io()
-> Result<(), String> {
    let wire = checksum_wire()?;
    let guest = build_relocated_recurrent_checksum_source(current_profile())
        .map_err(|error| format!("guest: {error:?}"))?;
    let probe = proposal(&wire, &[255], &guest);
    let _io = verify_source_recurrent_io(probe.io)
        .map_err(|error| format!("ordinary I/O: {error:?}"))?;
    let mut reordered = probe.classifier_words;
    reordered.swap(0, 1);
    for invalid in [
        SourceRecurrentGuardProbe {
            classifier_words: reordered,
            ..probe
        },
        SourceRecurrentGuardProbe {
            byte_landing: BYTE.saturating_add(1),
            ..probe
        },
        SourceRecurrentGuardProbe {
            eof_landings: [
                EOF_ODD.saturating_add(1),
                EOF_EVEN.saturating_add(1),
            ],
            ..probe
        },
        SourceRecurrentGuardProbe {
            fold_address: guest.capture.rotate,
            ..probe
        },
    ] {
        if verify_source_recurrent_guard(&invalid)
            != Err(Error::GuestGuardMismatch)
        {
            return Err("false physical guard binding accepted".to_owned());
        }
    }
    Ok(())
}

#[test]
fn source_recurrent_guard_refuses_omitted_classifier_effect()
-> Result<(), String> {
    let wire = checksum_wire()?;
    let guest = build_relocated_recurrent_checksum_source(current_profile())
        .map_err(|error| format!("guest: {error:?}"))?;
    let probe = proposal(&wire, &[0], &guest);
    let mut changed = guest.capture.source.clone();
    let index = usize::try_from(probe.fold_address)
        .map_err(|error| error.to_string())?;
    let word = changed.get_mut(index).ok_or("fold site outside image")?;
    if decode_profile_instruction(u32::from(*word), probe.fold_address)
        != Some(b'p')
    {
        return Err("unexpected capture instruction".to_owned());
    }
    *word = (33..=126u8)
        .find(|byte| {
            decode_profile_instruction(u32::from(*byte), probe.fold_address)
                == Some(b'o')
        })
        .ok_or("missing no-op encoding")?;
    let modified = SourceRecurrentGuardProbe {
        io: SourceRecurrentIoProbe {
            physical_source: &changed,
            ..probe.io
        },
        ..probe
    };
    if verify_source_recurrent_guard(&modified).is_ok() {
        return Err(
            "omitted capture/classifier instruction accepted".to_owned()
        );
    }
    Ok(())
}
