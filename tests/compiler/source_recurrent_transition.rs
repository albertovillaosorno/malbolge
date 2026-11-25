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

use core::iter::repeat_with;
use core::mem::swap;

use malbolge::{
    ProfileMachine, ProfileMemoryRead, ProfileMemoryWrite, ProfileStepTrace,
    RunOutcome, StepOutcome, current_profile, decode_profile_instruction,
    profile_crazy,
};

use super::super::super::super::{
    RelocatedRecurrentChecksumSource, build_relocated_recurrent_checksum_source,
};
use super::super::source_recurrent_guard::source_recurrent_guard_tests;
use super::super::source_recurrent_io_tests::{
    VECTORS, checksum, checksum_wire,
};
use super::super::source_recurrent_state::{
    InitialNormalizations, InitialStateTrace, SourceRecurrentStateCheckpoint,
    source_recurrent_state_tests,
};
use super::super::{
    ProjectedIo, ReplayJournal, SourceProjection, verify_source_recurrent_loop,
};
use super::{
    Error, GuardPlan, ParityPlan, ProjectionPlans, SourceRecurrentLoopProbe,
    SourceRecurrentRouteProbe, SourceRecurrentTransitionCheckpoint,
    SourceRecurrentTransitionProbe, SourceRecurrentTransitionProof,
    SourceTransitionValue, StatePlan, TernaryCfgTerminator, TransitionTrace,
    admit_probe, project_function_with_plans,
    verify_source_recurrent_transition,
};

type IndexedEntry = (usize, [ProfileStepTrace; 3]);
type InitialEntryTrace = (usize, [ProfileStepTrace; 4]);
type InitialStores = Vec<(usize, ProfileStepTrace)>;
type LoadedState = ([u32; 2], InitialStores);

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
        output_constants: [[7_180_890, 7_175_154], [7_175_134, 7_175_136]],
        output_scratch: 7_180_900,
        reset_addresses: [guest.capture.reset[0], guest.capture.reset[1]],
        reset_constants: [[7_180_832, 7_180_840], [7_180_836, 7_180_844]],
        rotate_address: guest.capture.rotate,
        route: SourceRecurrentRouteProbe {
            byte_bridge_word: 7_180_670,
            byte_route: 7_194_000,
            capture_reset_constant: 7_175_040,
            input_word: 7_175_030,
            load_addresses: guest.load,
            load_raw_constant: 7_180_800,
            lookup_constants: [
                7_180_812, 7_180_816, 7_180_820, 7_180_824, 7_180_828,
            ],
            loop_return_word: 7_175_090,
            main_entry: 7_175_207,
            main_route: 7_175_200,
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

fn check_control_counts(
    proof: &SourceRecurrentTransitionProof,
    bytes: usize,
) -> Result<(), String> {
    let first_input = proof
        .loop_proof
        .checkpoints
        .first()
        .ok_or("missing first input")?
        .guard
        .input_index;
    let first = proof
        .loop_proof
        .checkpoints
        .first()
        .ok_or("missing initial state")?;
    let [None, Some(normalization)] = proof.initial_normalization_indices
    else {
        return Err("wrong initial normalization receipt".to_owned());
    };
    if first
        .state
        .write_indices
        .iter()
        .any(|index| *index >= first_input)
        || normalization >= first.state.write_indices[1]
    {
        return Err("wrong initial state order".to_owned());
    }
    if proof.bootstrap_code_words != 144
        || proof.bootstrap_auxiliary_words != 37
        || proof.bootstrap_frame_words != 12
        || proof.bootstrap_table_words != 2_514
        || proof.bootstrap_route_words != 4_716
        || proof.bootstrap_unreachable_words != 256
        || proof.bootstrap_table_last_store_index >= first_input
        || proof.initial_entry_indices
            != [first_input.saturating_sub(2), first_input.saturating_sub(1)]
        || proof.control_calls != bytes.saturating_mul(65).saturating_add(9)
        || proof.preparation_jumps == 0
        || proof.preparation_jumps >= proof.post_input_steps
        || proof.post_input_steps
            != proof.loop_proof.io.guest_steps.saturating_sub(first_input)
        || proof.transitions.len() != bytes
        || proof.loop_proof.checkpoints.len() != bytes.saturating_add(1)
    {
        return Err(format!(
            "wrong counts: route={}, calls={}, preparations={}, steps={}",
            proof.bootstrap_route_words,
            proof.control_calls,
            proof.preparation_jumps,
            proof.post_input_steps
        ));
    }
    Ok(())
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
        check_control_counts(&proof, stream.len())?;
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

// Reuse one actual source-loaded bootstrap, never manufacture a terminal
// register or memory state. A fork has independent memory and has consumed
// no input, so both physical EOF landing phases remain reachable.
fn terminal_boot(
    guest: &RelocatedRecurrentChecksumSource,
) -> Result<ProfileMachine, String> {
    let mut vm = ProfileMachine::from_source(
        current_profile(),
        &guest.capture.source,
        Vec::new(),
    )
    .map_err(|error| error.to_string())?;
    for _ in 0..1_950_000usize {
        if vm.registers().code_pointer == guest.capture.input {
            if vm.input_consumed() != 0 || !vm.output().is_empty() {
                return Err("bootstrap performed I/O".to_owned());
            }
            return Ok(vm);
        }
        if vm.step().map_err(|error| error.to_string())?
            != StepOutcome::Continued
        {
            return Err("bootstrap terminated".to_owned());
        }
    }
    Err("bootstrap exhausted budget".to_owned())
}

fn verify_terminal_fork(
    boot: &ProfileMachine,
    probe: &SourceRecurrentTransitionProbe<'_>,
    projected: &SourceProjection,
    source_sha256: [u8; 32],
) -> Result<u8, String> {
    let stream = probe.loop_probe.guard.io.input;
    let audit = TransitionTrace::new(probe)
        .map_err(|error| format!("geometry: {error:?}"))?;
    let mut journal =
        ReplayJournal::new(None, None, source_sha256, Some(audit));
    let mut vm = boot
        .fork_with_input(stream.to_vec())
        .map_err(|error| error.to_string())?;
    let outcome = vm
        .run_traced(27_000, &mut |trace| {
            journal.observe(trace, projected);
        })
        .map_err(|error| error.to_string())?;
    let replay = journal
        .finish(outcome, projected, &vm)
        .map_err(|error| format!("terminal {stream:?}: {error:?}"))?;
    let transition = replay.transition.ok_or("missing audit")?;
    let receipt = transition
        .terminal
        .receipt()
        .map_err(|error| format!("terminal receipt: {error:?}"))?;
    let (calls, preparations, steps) = transition
        .control_receipt()
        .map_err(|error| format!("control receipt: {error:?}"))?;
    if transition.initial_entry() != Err(Error::GuestTransitionMismatch)
        || calls != stream.len().saturating_mul(65).saturating_add(9)
        || preparations == 0
        || steps != replay.io.guest_steps
        || transition.checkpoints.len() != stream.len()
        || receipt.halt_index.saturating_add(1) != replay.io.guest_steps
        || receipt.scratch_indices
            != [
                receipt.terminal_index.saturating_add(19),
                receipt.terminal_index.saturating_add(30),
            ]
        || receipt.output_word.rem_euclid(256) != u32::from(receipt.byte)
        || vm.output() != [receipt.byte]
    {
        return Err(format!("wrong terminal receipt for {stream:?}"));
    }
    Ok(receipt.byte)
}

#[test]
fn source_recurrent_transition_all_terminal_nibbles_and_phases()
-> Result<(), String> {
    let wire = checksum_wire()?;
    let guest = build_relocated_recurrent_checksum_source(current_profile())
        .map_err(|error| format!("guest: {error:?}"))?;
    let base = proposal(&wire, &[], &guest)?;
    let cfg = admit_probe(base.loop_probe.guard.io)
        .map_err(|error| format!("source: {error:?}"))?;
    let [function] = cfg.functions.as_slice() else {
        return Err("one checksum function required".to_owned());
    };
    let guard = GuardPlan::new(function, base.loop_probe.guard.source_header)
        .map_err(|error| format!("guard: {error:?}"))?;
    let state = StatePlan::new(function, &base.loop_probe.state)
        .map_err(|error| format!("state: {error:?}"))?;
    let parity = ParityPlan::new(function, &base.loop_probe, guard.phi)
        .map_err(|error| format!("parity: {error:?}"))?;
    let plans = ProjectionPlans {
        guard: Some(&guard),
        state: Some(&state),
        transition: Some(&parity),
    };
    let boot = terminal_boot(&guest)?;
    for byte in u8::MIN..=u8::MAX {
        // 253 returns the zero checksum to zero, toggling the input phase.
        let input = byte.wrapping_sub(3);
        for stream in [&[input][..], &[253, input][..]] {
            let probe = proposal(&wire, stream, &guest)?;
            let projected =
                project_function_with_plans(function, stream, &plans)
                    .map_err(|error| format!("source {stream:?}: {error:?}"))?;
            if verify_terminal_fork(
                &boot,
                &probe,
                &projected,
                cfg.source_sha256,
            )? != byte
            {
                return Err(format!("wrong source byte for {stream:?}"));
            }
        }
    }
    Ok(())
}

#[test]
fn source_recurrent_transition_rejects_control_geometry() -> Result<(), String>
{
    let wire = checksum_wire()?;
    let guest = build_relocated_recurrent_checksum_source(current_profile())
        .map_err(|error| format!("guest: {error:?}"))?;
    let probe = proposal(&wire, &[255], &guest)?;
    let route = probe.route;
    let _weaker = verify_source_recurrent_loop(&probe.loop_probe)
        .map_err(|error| format!("loop: {error:?}"))?;
    for wrong in [
        SourceRecurrentRouteProbe {
            byte_bridge_word: route.byte_bridge_word.saturating_add(1),
            ..route
        },
        SourceRecurrentRouteProbe {
            byte_route: route.byte_route.saturating_add(1),
            ..route
        },
        SourceRecurrentRouteProbe {
            input_word: route.input_word.saturating_add(1),
            ..route
        },
        SourceRecurrentRouteProbe {
            loop_return_word: route.loop_return_word.saturating_add(1),
            ..route
        },
        SourceRecurrentRouteProbe {
            main_entry: route.main_entry.saturating_add(1),
            ..route
        },
        SourceRecurrentRouteProbe {
            main_route: route.main_route.saturating_add(1),
            ..route
        },
    ] {
        let candidate =
            SourceRecurrentTransitionProbe { route: wrong, ..probe };
        if verify_source_recurrent_transition(&candidate)
            != Err(Error::GuestTransitionMismatch)
        {
            return Err(format!("false control binding: {wrong:?}"));
        }
    }
    Ok(())
}

fn refuse_control_trace(
    probe: &SourceRecurrentTransitionProbe<'_>,
    projected: &SourceProjection,
    traces: &[ProfileStepTrace],
    (index, replacement): (usize, ProfileStepTrace),
) -> Result<(), String> {
    let audit = TransitionTrace::new(probe)
        .map_err(|error| format!("geometry: {error:?}"))?;
    let mut journal = ReplayJournal::new(None, None, [0; 32], Some(audit));
    for trace in traces.get(..index).ok_or("bad mutation index")? {
        journal.observe(trace, projected);
        if let Some(error) = journal.failed {
            return Err(format!("unmodified prefix: {error:?}"));
        }
    }
    if journal.reconcile(&replacement, projected)
        != Err(Error::GuestTransitionMismatch)
    {
        return Err(format!("wrong control trace accepted at {index}"));
    }
    Ok(())
}

fn check_control_mutations(
    probe: &SourceRecurrentTransitionProbe<'_>,
    projected: &SourceProjection,
    traces: &[ProfileStepTrace],
) -> Result<(), String> {
    // Use a real indirect jump that encrypts an envelope interior and
    // executes an inert suffix, not an artificial arithmetic operation.
    let (index, jump) = traces
        .iter()
        .copied()
        .enumerate()
        .find(|(_, step)| {
            step.decoded == Some(b'i')
                && step.before.registers.code_pointer
                    > step.after.registers.code_pointer
                && step
                    .before
                    .registers
                    .code_pointer
                    .saturating_sub(step.after.registers.code_pointer)
                    < 8
                && step.memory_delta.encryption.is_some()
        })
        .ok_or("missing actual preparation jump")?;
    let next = *traces
        .get(index.saturating_add(1))
        .ok_or("missing suffix")?;
    let mut missing_encryption = jump;
    missing_encryption.memory_delta.encryption = None;
    refuse_control_trace(
        probe,
        projected,
        traces,
        (index, missing_encryption),
    )?;
    refuse_control_trace(probe, projected, traces, (index, next))?;
    // Leave the VM's effects and output untouched; only corrupt the
    // evidence of the control-data operand at this actual transfer.
    let mut wrong_operand = jump;
    let read = wrong_operand
        .memory_reads
        .data
        .as_mut()
        .ok_or("missing jump operand")?;
    read.value = read.value.saturating_add(1);
    refuse_control_trace(probe, projected, traces, (index, wrong_operand))
}

fn first_entry_trace(
    guest: &RelocatedRecurrentChecksumSource,
) -> Result<InitialEntryTrace, String> {
    let mut vm = ProfileMachine::from_source(
        current_profile(),
        &guest.capture.source,
        vec![255],
    )
    .map_err(|error| error.to_string())?;
    let mut last = [None; 4];
    for index in 0..1_950_001usize {
        if vm
            .step_traced(&mut |trace| {
                let [_, oldest, earlier, recent] = last;
                last = [oldest, earlier, recent, Some(*trace)];
            })
            .map_err(|error| error.to_string())?
            != StepOutcome::Continued
        {
            return Err("bootstrap terminated before input".to_owned());
        }
        if vm.input_consumed() == 1 {
            let [Some(prior), Some(indirect), Some(entry), Some(input)] = last
            else {
                return Err("incomplete entry trace".to_owned());
            };
            return Ok((index, [prior, indirect, entry, input]));
        }
    }
    Err("first input trace budget exhausted".to_owned())
}

fn observe_first_entry(
    probe: &SourceRecurrentTransitionProbe<'_>,
    event: ProjectedIo,
    (index, [indirect, entry, input]): IndexedEntry,
    omit_indirect: bool,
) -> Result<[usize; 2], Error> {
    let mut audit = TransitionTrace::new(probe)?;
    if !omit_indirect {
        audit.observe(&indirect, index.saturating_sub(2), None)?;
    }
    audit.observe(&entry, index.saturating_sub(1), None)?;
    audit.observe(&input, index, Some(event))?;
    audit.initial_entry()
}

fn check_initial_entry_mutations(
    guest: &RelocatedRecurrentChecksumSource,
    probe: &SourceRecurrentTransitionProbe<'_>,
    projected: &SourceProjection,
) -> Result<(), String> {
    let first = *projected.events.first().ok_or("missing projected input")?;
    let (index, [_, indirect, entry, input]) = first_entry_trace(guest)?;
    let actual = (index, [indirect, entry, input]);
    if observe_first_entry(probe, first, actual, false)
        != Ok([index.saturating_sub(2), index.saturating_sub(1)])
    {
        return Err("actual first entry refused".to_owned());
    }
    if observe_first_entry(probe, first, actual, true)
        != Err(Error::GuestTransitionMismatch)
    {
        return Err("missing initial indirect jump accepted".to_owned());
    }
    let mut wrong = indirect;
    let read = wrong
        .memory_reads
        .data
        .as_mut()
        .ok_or("missing first-entry pointer")?;
    read.value = read.value.saturating_add(1);
    let mut unencrypted = entry;
    unencrypted.memory_delta.encryption = None;
    for traces in [[wrong, entry, input], [indirect, unencrypted, input]] {
        if observe_first_entry(probe, first, (index, traces), false)
            != Err(Error::GuestTransitionMismatch)
        {
            return Err("corrupt first entry accepted".to_owned());
        }
    }
    Ok(())
}

// Alter an earlier, otherwise ignored pre-entry trace, not either of
// the two already authenticated initial transfer instructions.
fn forbidden_bootstrap_accesses(
    probe: &SourceRecurrentTransitionProbe<'_>,
    (index, prior): (usize, ProfileStepTrace),
    address: u32,
) -> Result<(), String> {
    let value = probe
        .loop_probe
        .guard
        .io
        .physical_source
        .get(usize::try_from(address).map_err(|error| error.to_string())?)
        .copied()
        .map(u32::from)
        .ok_or("missing reserved source word")?;
    let read = Some(ProfileMemoryRead { address, value });
    let write = Some(ProfileMemoryWrite {
        address,
        before: value,
        after: value.saturating_add(1),
    });
    let mut mutations = [prior; 5];
    let [data, fetch, encryption, data_write, encryption_write] =
        &mut mutations;
    data.memory_reads.data = read;
    fetch.memory_reads.fetch = read;
    encryption.memory_reads.encryption = read;
    data_write.memory_delta.data = write;
    encryption_write.memory_delta.encryption = write;
    for mutation in mutations {
        let mut audit = TransitionTrace::new(probe)
            .map_err(|error| format!("geometry: {error:?}"))?;
        if audit.observe(&mutation, index, None)
            != Err(Error::GuestTransitionMismatch)
        {
            return Err(format!("accepted bootstrap access to M{address}"));
        }
    }
    Ok(())
}

#[test]
fn source_recurrent_transition_rejects_bootstrap_code_trace_mutations()
-> Result<(), String> {
    let wire = checksum_wire()?;
    let guest = build_relocated_recurrent_checksum_source(current_profile())
        .map_err(|error| format!("guest: {error:?}"))?;
    let probe = proposal(&wire, &[255], &guest)?;
    let (index, [prior, _, _, _]) = first_entry_trace(&guest)?;
    let prior_index = index.saturating_sub(3);
    let mut audit = TransitionTrace::new(&probe)
        .map_err(|error| format!("geometry: {error:?}"))?;
    audit
        .observe(&prior, prior_index, None)
        .map_err(|error| format!("actual bootstrap trace: {error:?}"))?;
    // Include a byte-only lookup, its entry predecessor, and terminal
    // code. These are distinct from the authentic initial input entry.
    let [low_result, _] = probe.lookup[4];
    for address in [
        low_result,
        low_result.saturating_sub(5),
        probe.terminal_address.saturating_add(32),
    ] {
        forbidden_bootstrap_accesses(&probe, (prior_index, prior), address)?;
    }
    Ok(())
}

fn extra_read_controls(
    probe: &SourceRecurrentTransitionProbe<'_>,
    boot: &ProfileMachine,
) -> Result<Vec<ProfileMemoryRead>, String> {
    let unused_route = probe
        .loop_probe
        .guard
        .eof_landings
        .into_iter()
        .min()
        .ok_or("missing EOF landing")?
        .saturating_sub(1);
    [
        current_profile().memory_words().saturating_sub(1),
        probe.tables[3].saturating_add(676),
        unused_route,
    ]
    .into_iter()
    .map(|address| {
        boot.memory_word(address)
            .map(|value| ProfileMemoryRead { address, value })
            .map_err(|error| error.to_string())
    })
    .collect::<Result<Vec<_>, _>>()
}

fn replay_extra_reads(
    guest: &RelocatedRecurrentChecksumSource,
    probe: &SourceRecurrentTransitionProbe<'_>,
    projected: &SourceProjection,
    source_sha256: [u8; 32],
) -> Result<(), String> {
    let boot = terminal_boot(guest)?;
    let reads = extra_read_controls(probe, &boot)?;
    let mut vm = ProfileMachine::from_source(
        current_profile(),
        &guest.capture.source,
        Vec::new(),
    )
    .map_err(|error| error.to_string())?;
    let mut journals = repeat_with(|| {
        let audit = TransitionTrace::with_bootstrap(probe, &vm)
            .map_err(|error| format!("geometry: {error:?}"))?;
        Ok(ReplayJournal::new(None, None, source_sha256, Some(audit)))
    })
    .take(reads.len().saturating_add(1))
    .collect::<Result<Vec<_>, String>>()?;
    let mut started = false;
    let mut mutated = false;
    let outcome = vm
        .run_traced(2_000_000, &mut |trace| {
            started |= trace.input.is_some();
            if started && !mutated && trace.decoded == Some(b'o') {
                for (journal, read) in journals.iter_mut().skip(1).zip(&reads) {
                    let mut altered = *trace;
                    altered.memory_reads.data = Some(*read);
                    journal.observe(&altered, projected);
                }
                if let Some(baseline) = journals.first_mut() {
                    baseline.observe(trace, projected);
                }
                mutated = true;
            } else {
                for journal in &mut journals {
                    journal.observe(trace, projected);
                }
            }
        })
        .map_err(|error| error.to_string())?;
    if !mutated {
        return Err("missing post-input no-op for mutation".to_owned());
    }
    verify_extra_reads(journals, outcome, projected, &vm)
}

fn verify_extra_reads(
    journals: Vec<ReplayJournal>,
    outcome: RunOutcome,
    projected: &SourceProjection,
    vm: &ProfileMachine,
) -> Result<(), String> {
    let mut results = journals.into_iter();
    let baseline = results.next().ok_or("missing baseline")?;
    let _proof = baseline
        .finish(outcome, projected, vm)
        .map_err(|error| format!("actual trace: {error:?}"))?;
    for (index, journal) in results.enumerate() {
        // The first two reads fail immediately. An unused route-tape word
        // is in the broad candidate range, but not in the admitted route.
        let expected = if index == 2 {
            None
        } else {
            Some(Error::GuestTransitionMismatch)
        };
        if journal.failed != expected {
            return Err(format!("wrong immediate result for control {index}"));
        }
        if !matches!(
            journal.finish(outcome, projected, vm),
            Err(Error::GuestTransitionMismatch)
        ) {
            return Err(format!("accepted extra read control {index}"));
        }
    }
    Ok(())
}

#[test]
fn source_recurrent_transition_rejects_extra_data_reads() -> Result<(), String>
{
    let wire = checksum_wire()?;
    let guest = build_relocated_recurrent_checksum_source(current_profile())
        .map_err(|error| format!("guest: {error:?}"))?;
    let stream = [];
    let probe = proposal(&wire, &stream, &guest)?;
    let cfg = admit_probe(probe.loop_probe.guard.io)
        .map_err(|error| format!("source: {error:?}"))?;
    let [function] = cfg.functions.as_slice() else {
        return Err("one checksum function required".to_owned());
    };
    let guard = GuardPlan::new(function, probe.loop_probe.guard.source_header)
        .map_err(|error| format!("guard: {error:?}"))?;
    let state = StatePlan::new(function, &probe.loop_probe.state)
        .map_err(|error| format!("state: {error:?}"))?;
    let parity = ParityPlan::new(function, &probe.loop_probe, guard.phi)
        .map_err(|error| format!("parity: {error:?}"))?;
    let projected =
        project_function_with_plans(function, &stream, &ProjectionPlans {
            guard: Some(&guard),
            state: Some(&state),
            transition: Some(&parity),
        })
        .map_err(|error| format!("source: {error:?}"))?;
    replay_extra_reads(&guest, &probe, &projected, cfg.source_sha256)
}

#[test]
fn source_recurrent_transition_rejects_control_trace_mutations()
-> Result<(), String> {
    let wire = checksum_wire()?;
    let guest = build_relocated_recurrent_checksum_source(current_profile())
        .map_err(|error| format!("guest: {error:?}"))?;
    let stream = [255];
    let probe = proposal(&wire, &stream, &guest)?;
    let cfg = admit_probe(probe.loop_probe.guard.io)
        .map_err(|error| format!("source: {error:?}"))?;
    let [function] = cfg.functions.as_slice() else {
        return Err("one checksum function required".to_owned());
    };
    let guard = GuardPlan::new(function, probe.loop_probe.guard.source_header)
        .map_err(|error| format!("guard: {error:?}"))?;
    let state = StatePlan::new(function, &probe.loop_probe.state)
        .map_err(|error| format!("state: {error:?}"))?;
    let parity = ParityPlan::new(function, &probe.loop_probe, guard.phi)
        .map_err(|error| format!("parity: {error:?}"))?;
    let projected =
        project_function_with_plans(function, &stream, &ProjectionPlans {
            guard: Some(&guard),
            state: Some(&state),
            transition: Some(&parity),
        })
        .map_err(|error| format!("source: {error:?}"))?;
    let boot = terminal_boot(&guest)?;
    let mut vm = boot
        .fork_with_input(stream.to_vec())
        .map_err(|error| error.to_string())?;
    let audit = TransitionTrace::new(&probe)
        .map_err(|error| format!("geometry: {error:?}"))?;
    let mut journal =
        ReplayJournal::new(None, None, cfg.source_sha256, Some(audit));
    let mut traces = Vec::new();
    let outcome = vm
        .run_traced(27_000, &mut |trace| {
            journal.observe(trace, &projected);
            traces.push(*trace);
        })
        .map_err(|error| error.to_string())?;
    let _proof = journal
        .finish(outcome, &projected, &vm)
        .map_err(|error| format!("unmodified control: {error:?}"))?;
    check_control_mutations(&probe, &projected, &traces)?;
    check_initial_entry_mutations(&guest, &probe, &projected)
}

#[test]
fn source_recurrent_transition_rejects_terminal_geometry() -> Result<(), String>
{
    let wire = checksum_wire()?;
    let guest = build_relocated_recurrent_checksum_source(current_profile())
        .map_err(|error| format!("guest: {error:?}"))?;
    let probe = proposal(&wire, &[], &guest)?;
    let [[low, low_twos], [high, high_twos]] = probe.output_constants;
    let [_, high_state] = probe.loop_probe.state.words;
    for constant in [
        low,
        high.saturating_add(1),
        high_state.saturating_add(7),
        probe.output_scratch.saturating_add(1),
        probe.tables[1].saturating_add(5),
        probe.seeds[1],
        0,
        current_profile().memory_words(),
    ] {
        let invalid = SourceRecurrentTransitionProbe {
            output_constants: [[low, constant], [high, high_twos]],
            ..probe
        };
        if verify_source_recurrent_transition(&invalid)
            != Err(Error::InvalidTransitionBinding)
        {
            return Err(format!("aliased terminal constant: {constant}"));
        }
    }
    // A non-overlapping but false selector address must fail against the
    // real physical route, rather than merely trusting the same final byte.
    let wrong = SourceRecurrentTransitionProbe {
        output_constants: [[low.saturating_add(100), low_twos], [
            high, high_twos,
        ]],
        ..probe
    };
    if verify_source_recurrent_transition(&wrong)
        != Err(Error::GuestTransitionMismatch)
    {
        return Err("wrong terminal selector route accepted".to_owned());
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
    // The two load envelopes have different inert suffix lengths; swapping
    // them is now a static envelope error rather than a late route error.
    let swapped = SourceRecurrentTransitionProbe {
        route: SourceRecurrentRouteProbe {
            load_addresses: [second, first],
            ..route
        },
        ..probe
    };
    if verify_source_recurrent_transition(&swapped)
        != Err(Error::InvalidTransitionBinding)
    {
        return Err("swapped load envelopes accepted".to_owned());
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
    ] {
        if verify_source_recurrent_transition(&invalid)
            != Err(Error::GuestTransitionMismatch)
        {
            return Err("wrong actual scratch route accepted".to_owned());
        }
    }
    if verify_source_recurrent_transition(&SourceRecurrentTransitionProbe {
        scratch_rotate_address: guest.terminal,
        ..probe
    }) != Err(Error::InvalidTransitionBinding)
    {
        return Err("terminal code accepted as scratch envelope".to_owned());
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

fn omitted_table_store(
    guest: &RelocatedRecurrentChecksumSource,
    wire: &[u8],
    target: (u32, u32),
) -> Result<(), String> {
    let site = materialization_site(guest, target)?;
    let noop = (33u8..=126)
        .find(|cell| {
            decode_profile_instruction(u32::from(*cell), site) == Some(b'o')
        })
        .ok_or("no noop encoding")?;
    let mut mutated = guest.clone();
    *mutated
        .capture
        .source
        .get_mut(usize::try_from(site).map_err(|error| error.to_string())?)
        .ok_or("missing table store")? = noop;
    let probe = proposal(wire, &[], &mutated)?;
    let _loop_only = verify_source_recurrent_loop(&probe.loop_probe)
        .map_err(|error| format!("empty control: {target:?}: {error:?}"))?;
    if verify_source_recurrent_transition(&probe)
        != Err(Error::GuestTransitionMismatch)
    {
        return Err(format!("unvisited table store accepted: {target:?}"));
    }
    Ok(())
}

#[test]
fn source_recurrent_transition_rejects_unvisited_table_store()
-> Result<(), String> {
    let wire = checksum_wire()?;
    let guest = build_relocated_recurrent_checksum_source(current_profile())
        .map_err(|error| format!("guest: {error:?}"))?;
    let probe = proposal(&wire, &[], &guest)?;
    let profile = current_profile();
    let twos = profile.eof_word();
    let ones = twos.div_euclid(2);
    let raw_seed = profile_crazy(
        profile_crazy(ones, 15, profile.word_trits()),
        twos,
        profile.word_trits(),
    );
    let low_link = probe.seeds[1].saturating_add(24);
    let unused_return = probe.seeds[0].saturating_add(122);
    let boot = terminal_boot(&guest)?;
    let continuation = boot
        .memory_word(unused_return)
        .map_err(|error| error.to_string())?;
    let unused_main = probe.route.main_route;
    let main_target = boot
        .memory_word(unused_main)
        .map_err(|error| error.to_string())?;
    let unused_bridge = probe.loop_probe.guard.byte_landing;
    let bridge_target = boot
        .memory_word(unused_bridge)
        .map_err(|error| error.to_string())?;
    // None of these independent record effects is used on empty input.
    for target in [
        (
            probe.tables[3].saturating_add(487),
            probe.seeds[3].saturating_sub(1),
        ),
        (probe.seeds[0].saturating_add(121), raw_seed),
        (low_link, low_link.saturating_add(3)),
        (unused_return, continuation),
        (unused_main, main_target),
        (unused_bridge, bridge_target),
    ] {
        omitted_table_store(&guest, &wire, target)?;
    }
    Ok(())
}

#[test]
fn source_recurrent_transition_rejects_unvisited_output_contribution()
-> Result<(), String> {
    let wire = checksum_wire()?;
    let guest = build_relocated_recurrent_checksum_source(current_profile())
        .map_err(|error| format!("guest: {error:?}"))?;
    let probe = proposal(&wire, &[], &guest)?;
    let boot = terminal_boot(&guest)?;
    let high = probe.tables[3]
        .saturating_add(504)
        .saturating_add(10_935u32);
    let low = probe.tables[1].saturating_add(5).saturating_add(405u32);
    for address in [high, low, low.saturating_add(1)] {
        let value = boot
            .memory_word(address)
            .map_err(|error| error.to_string())?;
        omitted_table_store(&guest, &wire, (address, value))?;
    }
    Ok(())
}

#[test]
fn source_recurrent_transition_rejects_unvisited_auxiliary_words()
-> Result<(), String> {
    let wire = checksum_wire()?;
    let guest = build_relocated_recurrent_checksum_source(current_profile())
        .map_err(|error| format!("guest: {error:?}"))?;
    let probe = proposal(&wire, &[], &guest)?;
    let loop_proof = verify_source_recurrent_loop(&probe.loop_probe)
        .map_err(|error| format!("empty loop: {error:?}"))?;
    let selected = loop_proof
        .checkpoints
        .first()
        .ok_or("missing EOF")?
        .guard
        .guest_landing;
    let unused = probe
        .loop_probe
        .guard
        .eof_landings
        .into_iter()
        .find(|landing| *landing != selected)
        .ok_or("missing alternate EOF")?;
    let boot = terminal_boot(&guest)?;
    for address in [
        unused,
        unused.saturating_add(1),
        unused.saturating_add(2),
        probe.route.raw_restore_words[1][1],
        probe.route.lookup_constants[4],
    ] {
        let value = boot
            .memory_word(address)
            .map_err(|error| error.to_string())?;
        omitted_table_store(&guest, &wire, (address, value))?;
    }
    Ok(())
}

#[test]
fn source_recurrent_transition_rejects_unvisited_frame_store()
-> Result<(), String> {
    let wire = checksum_wire()?;
    let guest = build_relocated_recurrent_checksum_source(current_profile())
        .map_err(|error| format!("guest: {error:?}"))?;
    let probe = proposal(&wire, &[], &guest)?;
    let boot = terminal_boot(&guest)?;
    for address in probe
        .route
        .raw_pointers
        .into_iter()
        .chain(probe.scratch_words)
    {
        let value = boot
            .memory_word(address)
            .map_err(|error| error.to_string())?;
        omitted_table_store(&guest, &wire, (address, value))?;
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

fn initial_stores(
    guest: &RelocatedRecurrentChecksumSource,
) -> Result<LoadedState, String> {
    let mut vm = ProfileMachine::from_source(
        current_profile(),
        &guest.capture.source,
        Vec::new(),
    )
    .map_err(|error| error.to_string())?;
    let [low, high] = guest.state;
    let loaded = [
        vm.memory_word(low).map_err(|error| error.to_string())?,
        vm.memory_word(high).map_err(|error| error.to_string())?,
    ];
    let mut stores = Vec::new();
    for index in 0..1_595_000usize {
        if vm.registers().code_pointer == guest.capture.input {
            return Ok((loaded, stores));
        }
        let outcome = vm
            .step_traced(&mut |trace| {
                if guest.state.contains(&trace.before.registers.data_pointer)
                    && matches!(trace.decoded, Some(b'p' | b'*'))
                {
                    stores.push((index, *trace));
                }
            })
            .map_err(|error| error.to_string())?;
        if outcome != StepOutcome::Continued {
            return Err("initial-state bootstrap terminated".to_owned());
        }
    }
    Err("missing initial-state input".to_owned())
}

fn initial_receipt(
    guest: &RelocatedRecurrentChecksumSource,
    checkpoint: &SourceRecurrentStateCheckpoint,
    loaded: [u32; 2],
    stores: &[(usize, ProfileStepTrace)],
) -> Result<InitialNormalizations, Error> {
    let mut audit = InitialStateTrace::new(guest.state, loaded);
    for (index, trace) in stores {
        audit.observe(trace, *index);
    }
    audit.receipt(checkpoint, &guest.capture.source)
}

#[test]
fn source_recurrent_transition_refuses_initial_store_mutations()
-> Result<(), String> {
    let wire = checksum_wire()?;
    let guest = build_relocated_recurrent_checksum_source(current_profile())
        .map_err(|error| format!("guest: {error:?}"))?;
    let probe = proposal(&wire, &[], &guest)?;
    let proof = verify_source_recurrent_transition(&probe)
        .map_err(|error| format!("initial proof: {error:?}"))?;
    let checkpoint = &proof
        .loop_proof
        .checkpoints
        .first()
        .ok_or("missing first checkpoint")?
        .state;
    let (loaded, stores) = initial_stores(&guest)?;
    let [low, normalization, high] = stores.as_slice() else {
        return Err("expected three observed state stores".to_owned());
    };
    if initial_receipt(&guest, checkpoint, loaded, &stores)
        != Ok(proof.initial_normalization_indices)
    {
        return Err("actual initialization refused".to_owned());
    }
    let mut wrong_operand = *high;
    wrong_operand.1.memory_reads.data = None;
    let mut missing_encryption = *low;
    missing_encryption.1.memory_delta.encryption = None;
    let mut missing_write = *high;
    missing_write.1.memory_delta.data = None;
    for mutated in [
        vec![*low, *high],
        vec![*normalization, *low, *high],
        vec![*low, *high, *normalization],
        vec![*low, *normalization, wrong_operand],
        vec![missing_encryption, *normalization, *high],
        vec![*low, *normalization, missing_write],
        vec![*low, *normalization, *normalization, *high],
    ] {
        if initial_receipt(&guest, checkpoint, loaded, &mutated).is_ok() {
            return Err("corrupt initial state receipt accepted".to_owned());
        }
    }
    let mut wrong_checkpoint = *checkpoint;
    wrong_checkpoint.write_indices[0] = low.0.saturating_add(1);
    if initial_receipt(&guest, &wrong_checkpoint, loaded, &stores).is_ok() {
        return Err("unbound source checkpoint accepted".to_owned());
    }
    Ok(())
}
