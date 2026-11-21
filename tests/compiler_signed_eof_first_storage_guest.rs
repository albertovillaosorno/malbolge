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
//   - Normative source-loaded first-input storage through a second live read.
// - Must-Not:
//   - Claim signed C32 conversion, source control, checksum or a guest loop.
// - Allows:
//   - Inputs: bounded byte/EOF cases and reproducible second bytes.
//   - Outputs: exact guest writes, two input/echo effects and physical reentry.
//   - Side effects: isolated bounded current-profile guest VM execution.
// - Split-When:
//   - A source-linked physical guest-state compiler owns this exact proof.
// - Merge-When:
//   - A generic live-SSA guest reentry checker subsumes the witness.
// - Summary:
//   - First live input controls D after a distinct second input overwrites A.

//! Two real guest reads with physically stored first-input reentry; not C23.

#[path = "../src/compiler/malbolge-layout/composition/lib.rs"]
pub mod layout;

use std::iter::once;

use malbolge::{
    ProfileMachine, ProfileRegisters, ProfileStepTrace, RunOutcome,
    Termination, TraceInput, current_profile, decode_profile_instruction,
    historical_profile,
};

const SOURCE_LEN: usize = 63;
const GUEST_STEPS: usize = 61;
const RAW_IDENTITY_SEED: u32 = 7_174_453;
const RESET_LOADER_WORD: u32 = 72;

type Event = (u32, TraceInput);

fn encode(position: u32, opcode: u8) -> Result<u8, String> {
    (33..=126u8)
        .find(|byte| {
            decode_profile_instruction(u32::from(*byte), position)
                == Some(opcode)
        })
        .ok_or_else(|| format!("no graphical {opcode} at C{position}"))
}

fn expected_raw(input: Option<u8>) -> u32 {
    input.map_or(current_profile().eof_word(), u32::from)
}

fn verify_two_reads(
    guest: &ProfileMachine,
    trace: &[ProfileStepTrace],
    stream: &[u8],
) -> Result<(), String> {
    let profile = current_profile();
    let first = expected_raw(stream.first().copied());
    let second = expected_raw(stream.get(1).copied());
    assert_eq!(trace.len(), GUEST_STEPS);
    assert_eq!(guest.output(), &[first as u8, second as u8]);
    assert_eq!(guest.input_consumed(), stream.len().min(2));
    assert_eq!(guest.memory_word(73), Ok(first));
    assert_eq!(guest.registers().accumulator, second);
    assert_eq!(guest.registers().code_pointer, 60);
    for (position, op) in [
        (13, b'/'),
        (15, b'p'),
        (16, b'j'),
        (17, b'p'),
        (22, b'j'),
        (23, b'o'),
        (24, b'<'),
        (25, b'/'),
        (26, b'<'),
        (28, b'j'),
        (29, b'j'),
        (60, b'v'),
    ] {
        let reached = trace.get(position).ok_or("missing trace step")?;
        assert_eq!(reached.before.registers.code_pointer, position as u32);
        assert_eq!(reached.decoded, Some(op));
    }
    let input_events = trace
        .iter()
        .filter_map(|step| {
            step.input
                .map(|read| (step.before.registers.code_pointer, read))
        })
        .collect::<Vec<_>>();
    let expected_inputs: [Event; 2] = [
        (
            13,
            stream
                .first()
                .copied()
                .map_or(TraceInput::EndOfInput, TraceInput::Byte),
        ),
        (
            25,
            stream
                .get(1)
                .copied()
                .map_or(TraceInput::EndOfInput, TraceInput::Byte),
        ),
    ];
    assert_eq!(input_events, expected_inputs);
    let output_events = trace
        .iter()
        .filter_map(|step| {
            step.output
                .map(|byte| (step.before.registers.code_pointer, byte))
        })
        .collect::<Vec<_>>();
    assert_eq!(output_events, [(24, first as u8), (26, second as u8)]);
    let first_store = trace.get(15).ok_or("missing first store")?;
    let exact_store = trace.get(17).ok_or("missing exact store")?;
    assert_eq!(
        first_store
            .memory_reads
            .data
            .map(|read| (read.address, read.value)),
        Some((121, RAW_IDENTITY_SEED))
    );
    assert_eq!(
        exact_store
            .memory_reads
            .data
            .map(|read| (read.address, read.value)),
        Some((73, RAW_IDENTITY_SEED))
    );
    assert_eq!(
        exact_store
            .memory_delta
            .data
            .map(|write| (write.address, write.after)),
        Some((73, first))
    );
    assert_eq!(
        trace
            .get(28)
            .and_then(|step| step.memory_reads.data)
            .map(|read| (read.address, read.value)),
        Some((78, RESET_LOADER_WORD))
    );
    let reload = trace.get(29).ok_or("missing saved input reload")?;
    assert_eq!(
        reload
            .memory_reads
            .data
            .map(|read| (read.address, read.value)),
        Some((73, first))
    );
    assert_eq!(
        reload.after.registers.data_pointer,
        first.wrapping_add(1) % profile.memory_words()
    );
    assert_eq!(reload.before.registers.accumulator, second);
    // Exactly one input-derived first-word store and no later overwrite.
    assert_eq!(
        trace
            .iter()
            .filter(|step| step
                .memory_delta
                .data
                .is_some_and(|write| write.address == 73))
            .count(),
        1
    );
    Ok(())
}

#[test]
fn graphical_two_read_source_retains_original_identity_loader_and_geometry()
-> Result<(), String> {
    let profile = current_profile();
    let plan = layout::build_byte_exact_two_input_reentry_source(profile)
        .map_err(|error| format!("{error:?}"))?;
    assert_eq!(plan.source.len(), SOURCE_LEN);
    assert_eq!(plan.source.get(61..), Some(b"%H".as_slice()));
    assert_eq!(
        (
            plan.first_input_data_address,
            plan.second_input_code_address,
            plan.reset_code_address,
            plan.reload_code_address,
            plan.halt_code_address
        ),
        (73, 25, 28, 29, 60)
    );
    let original = layout::build_byte_exact_input_reentry_source(profile)
        .map_err(|error| format!("{error:?}"))?;
    assert_eq!(plan.source.get(..23), original.store.source.get(..23));
    for (position, byte) in plan.source.iter().copied().enumerate() {
        let decoded =
            decode_profile_instruction(u32::from(byte), position as u32);
        assert!(
            matches!(
                decoded,
                Some(b'j' | b'i' | b'*' | b'p' | b'o' | b'<' | b'/' | b'v')
            ),
            "bad original source encoding C{position}: {decoded:?}"
        );
    }
    let loaded = ProfileMachine::from_source(profile, &plan.source, Vec::new())
        .map_err(|error| error.to_string())?;
    for (address, value) in [
        (73, RAW_IDENTITY_SEED),
        (78, RESET_LOADER_WORD),
        (121, RAW_IDENTITY_SEED),
    ] {
        assert_eq!(loaded.memory_word(address), Ok(value));
    }
    assert_eq!(
        layout::build_byte_exact_two_input_reentry_source(historical_profile()),
        Err(layout::ByteExactInputStoreError::UnsupportedProfile),
    );
    Ok(())
}

#[test]
#[expect(
    clippy::too_many_lines,
    clippy::panic_in_result_fn,
    reason = "bounded representative input and EOF checks"
)]
fn first_input_state_reenters_after_two_real_reads() -> Result<(), String> {
    let profile = current_profile();
    let source = layout::build_byte_exact_two_input_reentry_source(profile)
        .map_err(|error| format!("{error:?}"))?
        .source;
    // One fresh real source loader is reused unchanged. Every trial starts
    // from its actual virgin memory; no input-dependent host injection.
    let loaded = ProfileMachine::from_source(profile, &source, Vec::new())
        .map_err(|error| error.to_string())?;
    let streams = once(Vec::new())
        .chain(
            [0u8, 1, 2, 3, 10, 29, 30, 31, 61, 83, 128, 255]
                .into_iter()
                .map(|byte| vec![byte, byte.wrapping_mul(73).wrapping_add(19)]),
        )
        .chain([vec![0], vec![1], vec![61], vec![83], vec![128], vec![255]])
        .chain(
            [vec![0, 255, 128], vec![255, 0, 13], vec![61, 83, 99], vec![
                83, 61, 0,
            ]],
        );
    let mut cases = 0usize;
    for stream in streams {
        let mut guest = ProfileMachine::from_state(
            profile,
            loaded.memory().to_vec(),
            stream.clone(),
            ProfileRegisters::default(),
        )
        .map_err(|error| error.to_string())?;
        let mut trace = Vec::new();
        let outcome = guest
            .run_traced(GUEST_STEPS, &mut |step| trace.push(*step))
            .map_err(|error| format!("stream {stream:?}: {error}"))?;
        assert_eq!(
            outcome,
            RunOutcome::Terminated {
                reason: Termination::HaltInstruction,
                steps: GUEST_STEPS,
            },
            "stream {stream:?}"
        );
        verify_two_reads(&guest, &trace, &stream)?;
        cases += 1;
    }
    assert_eq!(cases, 23);
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "physical source mutations are negative oracles"
)]
fn exact_first_store_and_later_reload_are_both_necessary() -> Result<(), String>
{
    let profile = current_profile();
    let plan = layout::build_byte_exact_two_input_reentry_source(profile)
        .map_err(|error| format!("{error:?}"))?;
    for (mutation_position, original_opcode, replacement) in
        [(17usize, b'p', b'o'), (28, b'j', b'o'), (29, b'j', b'o')]
    {
        let mut mutated = plan.source.clone();
        assert_eq!(
            decode_profile_instruction(
                u32::from(
                    *mutated.get(mutation_position).ok_or("missing cell")?
                ),
                mutation_position as u32,
            ),
            Some(original_opcode)
        );
        *mutated.get_mut(mutation_position).ok_or("missing cell")? =
            encode(mutation_position as u32, replacement)?;
        let mut vm =
            ProfileMachine::from_source(profile, &mutated, vec![61, 83])
                .map_err(|error| error.to_string())?;
        let mut trace = Vec::new();
        let outcome = vm
            .run_traced(GUEST_STEPS, &mut |step| trace.push(*step))
            .map_err(|error| error.to_string())?;
        assert_eq!(outcome, RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: GUEST_STEPS,
        });
        // Removing the exact p changes the first echo. Removing either
        // reload j leaves both echoes intact but loses stateful reentry.
        assert_eq!(
            vm.output(),
            if mutation_position == 17 {
                &[82, 83][..]
            } else {
                &[61, 83][..]
            }
        );
        assert_eq!(vm.input_consumed(), 2);
        assert_ne!(
            trace
                .get(29)
                .and_then(|step| step.memory_reads.data)
                .map(|read| (read.address, read.value)),
            Some((73, 61))
        );
        if mutation_position == 17 {
            assert_eq!(vm.memory_word(73), Ok(RAW_IDENTITY_SEED));
        } else {
            assert_eq!(vm.memory_word(73), Ok(61));
        }
    }
    Ok(())
}
