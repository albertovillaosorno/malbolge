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
//   - Independent source loop-phi and physical persistent state witnesses.
// - Must-Not:
//   - Claim complete source-frame placement or executable publication.
// - Allows:
//   - Inputs: canonical checksum wire, guest memory and finite binary stdin.
//   - Outputs: per-read state receipts and negative binding controls.
//   - Side effects: isolated normative VM executions.
// - Split-When:
//   - The general recurrent compiler gate owns source state evidence.
// - Merge-When:
//   - Full source/guest effect verification admits the same physical state.
// - Summary:
//   - Bind real arithmetic stores to each canonical incoming phi value.

use core::array;

use malbolge::{ProfileMachine, current_profile, decode_profile_instruction};

use super::super::super::super::{
    RelocatedRecurrentChecksumSource, build_relocated_recurrent_checksum_source,
};
use super::super::source_recurrent_io_tests::{
    VECTORS, checksum, checksum_wire,
};
use super::super::{MAX_RECURRENT_IO_STEPS, verify_source_recurrent_io};
use super::{
    Error, SourceRecurrentIoProbe, SourceRecurrentStateProbe,
    SourceRecurrentStateProof, StatePlan, TernaryCfgScalarKind, admit_probe,
    project_function, verify_source_recurrent_state,
};

const LOW_TABLE: u32 = 7_242_615;

// With A all twos, independently map data trits 0,1,2 to 0,2,1.
fn low_mask(nibble: u32) -> u32 {
    let mut data = LOW_TABLE.saturating_add(nibble.saturating_mul(27));
    let mut value = 0u32;
    let mut place = 1u32;
    for _ in 0..15u8 {
        let digit = match data.rem_euclid(3) {
            1 => 2u32,
            2 => 1u32,
            _ => 0u32,
        };
        value = value.saturating_add(digit.saturating_mul(place));
        data = data.div_euclid(3);
        place = place.saturating_mul(3);
    }
    value.saturating_add(13)
}

fn encoding() -> [[u32; 16]; 2] {
    [
        array::from_fn(|index| {
            low_mask(u32::try_from(index).unwrap_or(u32::MAX))
        }),
        array::from_fn(|index| {
            14_329_871u32.saturating_add(
                u32::try_from(index).unwrap_or(u32::MAX).saturating_mul(729),
            )
        }),
    ]
}

pub(in super::super) fn proposal<'source>(
    canonical: &'source [u8],
    input: &'source [u8],
    guest: &'source RelocatedRecurrentChecksumSource,
) -> Result<SourceRecurrentStateProbe<'source>, String> {
    let io = SourceRecurrentIoProbe {
        canonical,
        input,
        physical_source: &guest.capture.source,
        step_budget: MAX_RECURRENT_IO_STEPS,
    };
    let cfg = admit_probe(io).map_err(|error| format!("source: {error:?}"))?;
    let [function] = cfg.functions.as_slice() else {
        return Err("one checksum function required".to_owned());
    };
    let phi = function
        .blocks
        .get(1)
        .and_then(|header| {
            header
                .phis
                .iter()
                .find(|phi| phi.type_kind == TernaryCfgScalarKind::U32)
        })
        .ok_or("missing state phi")?;
    Ok(SourceRecurrentStateProbe {
        encoding: encoding(),
        input_address: guest.capture.input,
        io,
        loop_header: 1,
        phi_result: phi.result,
        words: guest.state,
    })
}

fn phi_values(
    probe: &SourceRecurrentStateProbe<'_>,
) -> Result<[u32; 2], String> {
    let cfg =
        admit_probe(probe.io).map_err(|error| format!("source: {error:?}"))?;
    let [function] = cfg.functions.as_slice() else {
        return Err("one checksum function".to_owned());
    };
    let phi = function
        .blocks
        .get(1)
        .and_then(|block| {
            block.phis.iter().find(|phi| phi.result == probe.phi_result)
        })
        .ok_or("missing selected phi")?;
    let [(0, initial), (5, recurrent)] = phi.incoming.as_slice() else {
        return Err("unexpected phi predecessor identity".to_owned());
    };
    Ok([*initial, *recurrent])
}

fn check_checkpoints(
    proof: &SourceRecurrentStateProof,
    stream: &[u8],
    probe: &SourceRecurrentStateProbe<'_>,
) -> Result<(), String> {
    if proof.checkpoints.len() != stream.len().saturating_add(1)
        || proof.loop_header != probe.loop_header
        || proof.phi_result != probe.phi_result
        || proof.word_addresses != probe.words
    {
        return Err("incomplete source state receipt".to_owned());
    }
    let [initial, recurrent] = phi_values(probe)?;
    let mut state = 0u8;
    let mut previous = None;
    for (index, (checkpoint, io)) in proof
        .checkpoints
        .iter()
        .zip(&proof.io.observations)
        .enumerate()
    {
        let (block, ordinal) = if index == 0 {
            (0, 1)
        } else {
            (5, 2)
        };
        let expected_words = [
            low_mask(u32::from(state & 15)),
            14_329_871u32
                .saturating_add(u32::from(state >> 4u32).saturating_mul(729)),
        ];
        if (checkpoint.block, checkpoint.ordinal) != (block, ordinal)
            || checkpoint.code_address != probe.input_address
            || checkpoint.trace_index != io.trace_index
            || checkpoint.source_value
                != if index == 0 {
                    initial
                } else {
                    recurrent
                }
            || checkpoint.value != state
            || checkpoint.words != expected_words
            || checkpoint.write_indices.iter().any(|write| {
                *write >= checkpoint.trace_index
                    || previous.is_some_and(|prior| *write <= prior)
            })
        {
            return Err(format!(
                "incorrect physical phi checkpoint: {checkpoint:?}"
            ));
        }
        if let Some(byte) = stream.get(index) {
            state = checksum(state, *byte);
        }
        previous = Some(checkpoint.trace_index);
    }
    Ok(())
}

#[test]
fn source_recurrent_state_all_source_phi_transitions() -> Result<(), String> {
    let wire = checksum_wire()?;
    let guest = build_relocated_recurrent_checksum_source(current_profile())
        .map_err(|error| format!("guest: {error:?}"))?;
    let probe = proposal(&wire, &[], &guest)?;
    let cfg =
        admit_probe(probe.io).map_err(|error| format!("source: {error:?}"))?;
    let [function] = cfg.functions.as_slice() else {
        return Err("one checksum function required".to_owned());
    };
    let plan = StatePlan::new(function, &probe)
        .map_err(|error| format!("phi plan: {error:?}"))?;
    let [initial, recurrent] = phi_values(&probe)?;
    for first in u8::MIN..=u8::MAX {
        for second in u8::MIN..=u8::MAX {
            let source =
                project_function(function, &[first, second], Some(&plan))
                    .map_err(|error| {
                        format!("source [{first},{second}]: {error:?}")
                    })?;
            let actual = source
                .events
                .iter()
                .filter_map(|event| {
                    event.state.map(|state| (state.source_value, state.value))
                })
                .collect::<Vec<_>>();
            let prior = checksum(0, first);
            if actual
                != [
                    (initial, 0),
                    (recurrent, prior),
                    (recurrent, checksum(prior, second)),
                ]
            {
                return Err(format!(
                    "incorrect source phi recurrence: {actual:?}"
                ));
            }
        }
    }
    Ok(())
}

#[test]
fn source_recurrent_state_five_complete_guest_runs() -> Result<(), String> {
    let wire = checksum_wire()?;
    let guest = build_relocated_recurrent_checksum_source(current_profile())
        .map_err(|error| format!("guest: {error:?}"))?;
    for stream in VECTORS {
        let probe = proposal(&wire, stream, &guest)?;
        let proof = verify_source_recurrent_state(&probe)
            .map_err(|error| format!("state {stream:?}: {error:?}"))?;
        check_checkpoints(&proof, stream, &probe)?;
    }
    Ok(())
}

#[test]
fn source_recurrent_state_rejects_aliases_wrong_phi_and_encoding()
-> Result<(), String> {
    let wire = checksum_wire()?;
    let guest = build_relocated_recurrent_checksum_source(current_profile())
        .map_err(|error| format!("guest: {error:?}"))?;
    let probe = proposal(&wire, &[], &guest)?;
    let [low, high] = probe.words;
    let [low_encoding, high_encoding] = probe.encoding;
    for invalid in [
        SourceRecurrentStateProbe {
            words: [low, low],
            ..probe
        },
        SourceRecurrentStateProbe {
            words: [probe.input_address, high],
            ..probe
        },
        SourceRecurrentStateProbe {
            phi_result: u32::MAX,
            ..probe
        },
        SourceRecurrentStateProbe { loop_header: 0, ..probe },
        SourceRecurrentStateProbe {
            encoding: [low_encoding, [0; 16]],
            ..probe
        },
    ] {
        if verify_source_recurrent_state(&invalid)
            != Err(Error::InvalidStateBinding)
        {
            return Err("invalid source state binding accepted".to_owned());
        }
    }
    let mut wrong_low = low_encoding;
    wrong_low.swap(0, 1);
    if verify_source_recurrent_state(&SourceRecurrentStateProbe {
        encoding: [wrong_low, high_encoding],
        ..probe
    }) != Err(Error::GuestStateMismatch)
    {
        return Err("wrong source state encoding accepted".to_owned());
    }
    Ok(())
}

fn loader_encoding(word: u32) -> [u32; 16] {
    array::from_fn(|index| {
        if index == 0 {
            return word;
        }
        let small = u32::try_from(index).unwrap_or(u32::MAX);
        small.saturating_add(u32::from(small >= word))
    })
}

// The actual empty-input guest has correct observable I/O. A forged mapping
// whose zero-state words happen to equal untouched loader cells must not
// certify a source-state effect without a physical arithmetic store.
#[test]
fn source_recurrent_state_refuses_loader_only_match() -> Result<(), String> {
    let wire = checksum_wire()?;
    let guest = build_relocated_recurrent_checksum_source(current_profile())
        .map_err(|error| format!("guest: {error:?}"))?;
    let probe = proposal(&wire, &[], &guest)?;
    let vm = ProfileMachine::from_source(
        current_profile(),
        &guest.capture.source,
        Vec::new(),
    )
    .map_err(|error| error.to_string())?;
    let words = [14_348_900, 14_348_901];
    let [low, high] = words;
    let initial = [
        vm.memory_word(low).map_err(|error| error.to_string())?,
        vm.memory_word(high).map_err(|error| error.to_string())?,
    ];
    let encoding = initial.map(loader_encoding);
    let _io = verify_source_recurrent_io(probe.io)
        .map_err(|error| format!("ordinary guest I/O: {error:?}"))?;
    if verify_source_recurrent_state(&SourceRecurrentStateProbe {
        encoding,
        words,
        ..probe
    }) != Err(Error::MissingGuestStateStore)
    {
        return Err(
            "untouched loader cells accepted as state stores".to_owned()
        );
    }
    Ok(())
}

#[test]
fn source_recurrent_state_rejects_omitted_physical_initialization()
-> Result<(), String> {
    let wire = checksum_wire()?;
    let guest = build_relocated_recurrent_checksum_source(current_profile())
        .map_err(|error| format!("guest: {error:?}"))?;
    let probe = proposal(&wire, &[], &guest)?;
    let proof = verify_source_recurrent_state(&probe)
        .map_err(|error| format!("state: {error:?}"))?;
    let initial = proof.checkpoints.first().ok_or("missing initial state")?;
    for site in initial.write_sites {
        let index = usize::try_from(site).map_err(|error| error.to_string())?;
        let mut changed = guest.capture.source.clone();
        let cell = changed.get_mut(index).ok_or("write site outside image")?;
        if !matches!(
            decode_profile_instruction(u32::from(*cell), site),
            Some(b'p' | b'*')
        ) {
            return Err(format!("unexpected initial write opcode at {site}"));
        }
        *cell = (33..=126u8)
            .find(|byte| {
                decode_profile_instruction(u32::from(*byte), site) == Some(b'o')
            })
            .ok_or("no noop encoding")?;
        let modified = SourceRecurrentStateProbe {
            io: SourceRecurrentIoProbe {
                physical_source: &changed,
                ..probe.io
            },
            ..probe
        };
        if verify_source_recurrent_state(&modified).is_ok() {
            return Err(format!(
                "omitted initialization store accepted at {site}"
            ));
        }
    }
    Ok(())
}
