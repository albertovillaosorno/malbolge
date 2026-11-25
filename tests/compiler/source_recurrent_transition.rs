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
//   - Canonical parity and physical indexed transition regressions.
// - Must-Not:
//   - Authorize source publication or assume full SSA storage.
// - Allows:
//   - Inputs: original typed checksum and actual graphical guest.
//   - Outputs: finite transition receipts and wrong-geometry refusals.
//   - Side effects: isolated normative VM execution.
// - Split-When:
//   - Multiple carried states require independent witness policies.
// - Merge-When:
//   - General source-frame verification subsumes both bindings.

use core::mem::swap;

use malbolge::{
    ProfileMachine, StepOutcome, current_profile, decode_profile_instruction,
    profile_crazy,
};

use super::super::super::super::{
    RelocatedRecurrentChecksumSource, build_relocated_recurrent_checksum_source,
};
use super::super::source_recurrent_guard::source_recurrent_guard_tests;
use super::super::source_recurrent_io_tests::{
    VECTORS, checksum, checksum_wire,
};
use super::super::source_recurrent_state::source_recurrent_state_tests;
use super::super::verify_source_recurrent_loop;
use super::{
    Error, GuardPlan, ParityPlan, ProjectionPlans, SourceRecurrentLoopProbe,
    SourceRecurrentRouteProbe, SourceRecurrentTransitionCheckpoint,
    SourceRecurrentTransitionProbe, SourceTransitionValue, StatePlan,
    TernaryCfgTerminator, admit_probe, project_function_with_plans,
    verify_source_recurrent_transition,
};

fn proposal<'source>(
    wire: &'source [u8],
    stream: &'source [u8],
    guest: &'source RelocatedRecurrentChecksumSource,
) -> Result<SourceRecurrentTransitionProbe<'source>, String> {
    let [_, _, commit_address] = guest.capture.reset;
    Ok(SourceRecurrentTransitionProbe {
        commit_address,
        lookup: guest.lookup,
        loop_probe: SourceRecurrentLoopProbe {
            guard: source_recurrent_guard_tests::proposal(wire, stream, guest),
            state: source_recurrent_state_tests::proposal(wire, stream, guest)?,
        },
        output_scratch: 7_180_900,
        reset_addresses: [guest.capture.reset[0], guest.capture.reset[1]],
        reset_constants: [[7_180_832, 7_180_840], [7_180_836, 7_180_844]],
        rotate_address: guest.capture.rotate,
        route: SourceRecurrentRouteProbe {
            capture_reset_constant: 7_175_040,
            load_addresses: guest.load,
            load_raw_constant: 7_180_800,
            lookup_constants: [
                7_180_812, 7_180_816, 7_180_820, 7_180_824, 7_180_828,
            ],
            raw_pointers: guest.pointers,
            raw_reset_constants: [7_180_848, 7_180_852],
            raw_restore_words: [[7_180_872, 7_180_876], [7_180_880, 7_180_884]],
            recover_raw_constants: [7_180_804, 7_180_808],
        },
        scratch_rotate_address: guest.scratch_rotate,
        scratch_words: guest.scratch,
        seeds: [7_211_000, 7_243_100, 7_211_200, 7_243_400],
        tables: [7_208_352, 7_242_615, 7_209_081, 7_223_661],
        terminal_address: guest.terminal,
    })
}

#[test]
fn source_recurrent_transition_frozen_guest_replays() -> Result<(), String> {
    let wire = checksum_wire()?;
    let guest = build_relocated_recurrent_checksum_source(current_profile())
        .map_err(|error| format!("guest: {error:?}"))?;
    for stream in VECTORS {
        let probe = proposal(&wire, stream, &guest)?;
        let proof = verify_source_recurrent_transition(&probe)
            .map_err(|error| format!("transition {stream:?}: {error:?}"))?;
        if proof.transitions.len() != stream.len()
            || proof.loop_proof.checkpoints.len()
                != stream.len().saturating_add(1)
        {
            return Err("wrong transition count".to_owned());
        }
        let mut prior = 0u8;
        for (receipt, byte) in
            proof.transitions.iter().zip(stream.iter().copied())
        {
            let parity = u32::from(byte & 1);
            let (target, result, value) = if parity == 0 {
                (4, 15, u32::from(prior).saturating_add(u32::from(byte)))
            } else {
                (3, 13, u32::from(prior ^ byte))
            };
            let next = checksum(prior, byte);
            if receipt.raw_byte != byte
                || receipt.prior_state != prior
                || receipt.next_state != next
                || receipt.parity != parity
                || receipt.source_target != target
                || receipt.arm_result != result
                || receipt.arm_value != value
                || receipt.condition != 11
                || receipt.source_block != 2
                || !ordered_scratch_chains(receipt)
                || !ordered_raw_route(receipt)
                || receipt.lookup_indices.len() != 21
                || receipt.lookup_indices.windows(2).any(
                    |pair| matches!(pair, [first, second] if first >= second),
                )
            {
                return Err(format!("wrong transition: {receipt:?}"));
            }
            prior = next;
        }
        let eof = proof.loop_proof.checkpoints.last().ok_or("missing EOF")?;
        if proof.terminal.byte != prior
            || proof.terminal.terminal_index
                != eof.guard.guard_index.saturating_add(2)
            || proof.terminal.output_word.rem_euclid(256) != u32::from(prior)
        {
            return Err("wrong terminal receipt".to_owned());
        }
    }
    Ok(())
}

fn ordered_scratch_chains(
    receipt: &SourceRecurrentTransitionCheckpoint,
) -> bool {
    let [low, high] = receipt.commit_effect_indices;
    let ordered = |indices: &[usize; 9]| {
        indices
            .windows(2)
            .all(|pair| matches!(pair, [first, second] if first < second))
    };
    ordered(&low)
        && ordered(&high)
        && low.get(5).copied() == receipt.commit_indices.first().copied()
        && high.get(5).copied() == receipt.commit_indices.last().copied()
        && receipt.lookup_indices.get(15) < high.first()
        && high.last() < receipt.lookup_indices.get(16)
        && receipt.lookup_indices.last() < low.first()
        && low
            .last()
            .is_some_and(|last| *last < receipt.next_input_index)
}

fn ordered_raw_route(receipt: &SourceRecurrentTransitionCheckpoint) -> bool {
    let route = &receipt.route_effect_indices;
    let lookup = &receipt.lookup_indices;
    let [low_commit, high_commit] = receipt.commit_effect_indices;
    let precedes = |left: Option<&usize>, right: Option<&usize>| {
        left.zip(right)
            .is_some_and(|(earlier, later)| earlier < later)
    };
    route
        .windows(2)
        .all(|pair| matches!(pair, [first, second] if first < second))
        && route
            .first()
            .is_some_and(|first| *first > receipt.input_index)
        && precedes(route.get(3), lookup.first())
        && precedes(lookup.get(3), route.get(4))
        && precedes(route.get(5), lookup.get(4))
        && precedes(lookup.get(7), route.get(6))
        && precedes(route.get(12), lookup.get(8))
        && precedes(lookup.get(11), route.get(13))
        && precedes(route.get(14), lookup.get(12))
        && precedes(high_commit.last(), route.get(15))
        && precedes(route.get(15), lookup.get(16))
        && precedes(low_commit.last(), route.get(16))
        && route
            .last()
            .is_some_and(|last| *last < receipt.next_input_index)
}

#[test]
fn source_recurrent_transition_rejects_raw_route_aliases() -> Result<(), String>
{
    let wire = checksum_wire()?;
    let guest = build_relocated_recurrent_checksum_source(current_profile())
        .map_err(|error| format!("guest: {error:?}"))?;
    let probe = proposal(&wire, &[255], &guest)?;
    let route = probe.route;
    let [low, high] = route.raw_pointers;
    let [first, second] = route.load_addresses;
    for invalid in [
        SourceRecurrentRouteProbe {
            raw_pointers: [low, low],
            ..route
        },
        SourceRecurrentRouteProbe {
            raw_pointers: [probe.loop_probe.state.words[0], high],
            ..route
        },
        SourceRecurrentRouteProbe {
            capture_reset_constant: probe.tables[0].saturating_add(729),
            ..route
        },
        SourceRecurrentRouteProbe {
            load_addresses: [first, first],
            ..route
        },
        SourceRecurrentRouteProbe {
            load_addresses: [probe.commit_address, second],
            ..route
        },
        SourceRecurrentRouteProbe {
            raw_restore_words: [
                [route.raw_reset_constants[0], route.raw_restore_words[0][1]],
                route.raw_restore_words[1],
            ],
            ..route
        },
    ] {
        let candidate =
            SourceRecurrentTransitionProbe { route: invalid, ..probe };
        if verify_source_recurrent_transition(&candidate)
            != Err(Error::InvalidTransitionBinding)
        {
            return Err("aliased raw route accepted".to_owned());
        }
    }
    Ok(())
}

#[test]
fn source_recurrent_transition_rejects_wrong_raw_route() -> Result<(), String> {
    let wire = checksum_wire()?;
    let guest = build_relocated_recurrent_checksum_source(current_profile())
        .map_err(|error| format!("guest: {error:?}"))?;
    let probe = proposal(&wire, &[255], &guest)?;
    let route = probe.route;
    let [low, high] = route.raw_pointers;
    let [first, second] = route.load_addresses;
    let [low_restore, high_restore] = route.raw_restore_words;
    for wrong in [
        SourceRecurrentRouteProbe {
            raw_pointers: [high, low],
            ..route
        },
        SourceRecurrentRouteProbe {
            load_addresses: [second, first],
            ..route
        },
        SourceRecurrentRouteProbe {
            raw_restore_words: [high_restore, low_restore],
            ..route
        },
    ] {
        let candidate =
            SourceRecurrentTransitionProbe { route: wrong, ..probe };
        if verify_source_recurrent_transition(&candidate)
            != Err(Error::GuestTransitionMismatch)
        {
            return Err("wrong executed raw route accepted".to_owned());
        }
    }
    Ok(())
}

#[test]
fn source_recurrent_transition_rejects_wrong_scratch_geometry()
-> Result<(), String> {
    let wire = checksum_wire()?;
    let guest = build_relocated_recurrent_checksum_source(current_profile())
        .map_err(|error| format!("guest: {error:?}"))?;
    let probe = proposal(&wire, &[255], &guest)?;
    let [low, high] = probe.scratch_words;
    for invalid in [
        SourceRecurrentTransitionProbe {
            scratch_words: [low, low],
            ..probe
        },
        SourceRecurrentTransitionProbe {
            scratch_words: [low, probe.output_scratch],
            ..probe
        },
        SourceRecurrentTransitionProbe {
            scratch_words: [probe.tables[0].saturating_add(729), high],
            ..probe
        },
        SourceRecurrentTransitionProbe {
            scratch_rotate_address: probe.rotate_address,
            ..probe
        },
    ] {
        if verify_source_recurrent_transition(&invalid)
            != Err(Error::InvalidTransitionBinding)
        {
            return Err("aliased scratch geometry accepted".to_owned());
        }
    }
    let [low_constants, high_constants] = probe.reset_constants;
    for invalid in [
        SourceRecurrentTransitionProbe {
            scratch_words: [high, low],
            ..probe
        },
        SourceRecurrentTransitionProbe {
            reset_constants: [high_constants, low_constants],
            ..probe
        },
        SourceRecurrentTransitionProbe {
            scratch_rotate_address: guest.terminal,
            ..probe
        },
    ] {
        if verify_source_recurrent_transition(&invalid)
            != Err(Error::GuestTransitionMismatch)
        {
            return Err("wrong actual scratch route accepted".to_owned());
        }
    }
    Ok(())
}

#[test]
fn source_recurrent_transition_rejects_omitted_scratch_rotation()
-> Result<(), String> {
    let wire = checksum_wire()?;
    let mut guest =
        build_relocated_recurrent_checksum_source(current_profile())
            .map_err(|error| format!("guest: {error:?}"))?;
    let address = guest.scratch_rotate;
    let noop = (33u8..=126)
        .find(|cell| {
            decode_profile_instruction(u32::from(*cell), address) == Some(b'o')
        })
        .ok_or("no noop encoding")?;
    *guest
        .capture
        .source
        .get_mut(usize::try_from(address).map_err(|error| error.to_string())?)
        .ok_or("missing scratch rotation")? = noop;
    let probe = proposal(&wire, &[255], &guest)?;
    if verify_source_recurrent_transition(&probe)
        != Err(Error::InvalidTransitionBinding)
    {
        return Err("omitted physical scratch rotation accepted".to_owned());
    }
    Ok(())
}

fn materialization_site(
    guest: &RelocatedRecurrentChecksumSource,
    (address, expected): (u32, u32),
) -> Result<u32, String> {
    let mut vm = ProfileMachine::from_source(
        current_profile(),
        &guest.capture.source,
        Vec::new(),
    )
    .map_err(|error| error.to_string())?;
    for _ in 0usize..2_000_000 {
        let before = vm.registers();
        let candidate = before.data_pointer == address
            && decode_profile_instruction(
                vm.memory_word(before.code_pointer)
                    .map_err(|error| error.to_string())?,
                before.code_pointer,
            ) == Some(b'p')
            && vm.memory_word(address).map_err(|error| error.to_string())?
                != expected;
        if vm.step().map_err(|error| error.to_string())?
            != StepOutcome::Continued
        {
            return Err("unexpected halt during materialization".to_owned());
        }
        if candidate
            && vm.memory_word(address).map_err(|error| error.to_string())?
                == expected
        {
            return Ok(before.code_pointer);
        }
    }
    Err("restore seed never materialized".to_owned())
}

#[test]
fn source_recurrent_transition_rejects_missing_restore_seed()
-> Result<(), String> {
    let wire = checksum_wire()?;
    let mut guest =
        build_relocated_recurrent_checksum_source(current_profile())
            .map_err(|error| format!("guest: {error:?}"))?;
    let probe = proposal(&wire, &[255], &guest)?;
    let profile = current_profile();
    let mask = profile_crazy(
        probe.tables[0],
        profile.eof_word(),
        profile.word_trits(),
    )
    .saturating_add(364);
    let seed = profile_crazy(
        profile.eof_word().div_euclid(2),
        mask,
        profile.word_trits(),
    );
    let address = probe.route.raw_restore_words[0][1];
    let site = materialization_site(&guest, (address, seed))?;
    let noop = (33u8..=126)
        .find(|cell| {
            decode_profile_instruction(u32::from(*cell), site) == Some(b'o')
        })
        .ok_or("no noop encoding")?;
    *guest
        .capture
        .source
        .get_mut(usize::try_from(site).map_err(|error| error.to_string())?)
        .ok_or("missing seed store")? = noop;
    let mutated_probe = proposal(&wire, &[255], &guest)?;
    // A one-byte input followed by EOF does not use the restored raw pointer.
    // The older proof observes the same source state, guard and output.
    let _loop_only = verify_source_recurrent_loop(&mutated_probe.loop_probe)
        .map_err(|error| {
            format!("restore seed control did not preserve I/O: {error:?}")
        })?;
    let refusal = verify_source_recurrent_transition(&mutated_probe);
    if refusal != Err(Error::GuestTransitionMismatch) {
        return Err(format!("missing restore seed: {refusal:?}"));
    }
    Ok(())
}

#[test]
fn source_recurrent_transition_rejects_wrong_lookup_geometry()
-> Result<(), String> {
    let wire = checksum_wire()?;
    let guest = build_relocated_recurrent_checksum_source(current_profile())
        .map_err(|error| format!("guest: {error:?}"))?;
    let mut probe = proposal(&wire, &[255], &guest)?;
    let bad_scratch = SourceRecurrentTransitionProbe {
        output_scratch: probe
            .loop_probe
            .state
            .words
            .first()
            .copied()
            .ok_or("missing state word")?,
        ..probe
    };
    if verify_source_recurrent_transition(&bad_scratch)
        != Err(Error::InvalidTransitionBinding)
    {
        return Err("aliased EOF scratch accepted".to_owned());
    }
    let [raw_low, low, raw_high, high] = probe.tables;
    probe.tables = [raw_low.saturating_add(1), low, raw_high, high];
    if verify_source_recurrent_transition(&probe)
        != Err(Error::GuestTransitionMismatch)
    {
        return Err("wrong table accepted or wrong refusal".to_owned());
    }
    Ok(())
}

fn verify_source_value(
    value: SourceTransitionValue,
    prior: u8,
    byte: u8,
) -> Result<(), String> {
    let parity = u32::from(byte & 1);
    let (target, result, arm_value) = if parity == 0 {
        (4, 15, u32::from(prior).saturating_add(u32::from(byte)))
    } else {
        (3, 13, u32::from(prior ^ byte))
    };
    if !value.arm_checked
        || value.arm_result != result
        || value.arm_value != arm_value
        || value.condition != 11
        || value.source_block != 2
        || value.source_target != target
        || value.parity != parity
        || value.prior_state != prior
        || value.raw_byte != byte
        || value.next_state != checksum(prior, byte)
    {
        return Err(format!("wrong source arm for {prior}, {byte}"));
    }
    Ok(())
}

#[test]
fn source_recurrent_transition_all_two_byte_source_paths() -> Result<(), String>
{
    let wire = checksum_wire()?;
    let guest = build_relocated_recurrent_checksum_source(current_profile())
        .map_err(|error| format!("guest: {error:?}"))?;
    let probe = proposal(&wire, &[], &guest)?;
    let loop_probe = &probe.loop_probe;
    let cfg = admit_probe(loop_probe.guard.io)
        .map_err(|error| format!("source: {error:?}"))?;
    let [function] = cfg.functions.as_slice() else {
        return Err("one checksum function required".to_owned());
    };
    let guard = GuardPlan::new(function, loop_probe.guard.source_header)
        .map_err(|error| format!("guard: {error:?}"))?;
    let state = StatePlan::new(function, &loop_probe.state)
        .map_err(|error| format!("state: {error:?}"))?;
    let parity = ParityPlan::new(function, loop_probe, guard.phi)
        .map_err(|error| format!("parity: {error:?}"))?;
    let plans = ProjectionPlans {
        guard: Some(&guard),
        state: Some(&state),
        transition: Some(&parity),
    };
    for first in u8::MIN..=u8::MAX {
        for second in u8::MIN..=u8::MAX {
            let source =
                project_function_with_plans(function, &[first, second], &plans)
                    .map_err(|error| {
                        format!("source [{first},{second}]: {error:?}")
                    })?;
            let mut actual =
                source.events.iter().filter_map(|event| event.transition);
            let initial = actual.next().ok_or("missing first transition")?;
            let recurrent = actual.next().ok_or("missing second transition")?;
            verify_source_value(initial, 0, first)?;
            verify_source_value(recurrent, checksum(0, first), second)?;
            if actual.next().is_some() {
                return Err("extra transition at EOF".to_owned());
            }
        }
    }
    Ok(())
}

#[test]
fn source_recurrent_transition_refuses_alias_and_swapped_arms()
-> Result<(), String> {
    let wire = checksum_wire()?;
    let guest = build_relocated_recurrent_checksum_source(current_profile())
        .map_err(|error| format!("guest: {error:?}"))?;
    let probe = proposal(&wire, &[], &guest)?;
    let [raw_low, low, _, high] = probe.tables;
    let invalid = SourceRecurrentTransitionProbe {
        tables: [raw_low, low, raw_low, high],
        ..probe
    };
    if verify_source_recurrent_transition(&invalid)
        != Err(Error::InvalidTransitionBinding)
    {
        return Err("aliased tables accepted".to_owned());
    }
    let cfg = admit_probe(probe.loop_probe.guard.io)
        .map_err(|error| format!("source: {error:?}"))?;
    let [function] = cfg.functions.as_slice() else {
        return Err("one checksum function required".to_owned());
    };
    let mut swapped = function.clone();
    let parity = swapped
        .blocks
        .iter_mut()
        .find(|block| block.id == 2)
        .ok_or("missing parity block")?;
    let TernaryCfgTerminator::Branch {
        false_target,
        true_target,
        ..
    } = &mut parity.terminator
    else {
        return Err("expected branch".to_owned());
    };
    swap(false_target, true_target);
    if !matches!(
        ParityPlan::new(&swapped, &probe.loop_probe, 7),
        Err(Error::InvalidTransitionBinding)
    ) {
        return Err("swapped source arms accepted".to_owned());
    }
    Ok(())
}
