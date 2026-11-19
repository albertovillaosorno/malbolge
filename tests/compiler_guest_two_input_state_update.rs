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
//   - Independent physical proof of one guest cell updated by two stdin reads.
// - Must-Not:
//   - Claim C23 signed conversion, guest checksum state or C CFG lowering.
// - Allows:
//   - Inputs: current N15 loader and bounded EOF/binary input pairs.
//   - Outputs: verified same-address p writes and both physical input events.
//   - Side effects: isolated normative VM traces under a 54-step limit.
// - Split-When:
//   - General mutable input-dependent guest arithmetic replaces this probe.
// - Merge-When:
//   - Typed mutable C state has source-bound physical update witnesses.
// - Summary:
//   - The second guest input updates a word written by the first input.

//! Two distinct physical reads feeding successive writes of one guest word.

#[path = "../src/compiler/malbolge-layout/composition/lib.rs"]
pub mod layout;

use std::collections::BTreeSet;
use std::iter::once;

use malbolge::{
    ProfileMachine, ProfileRegisters, RunOutcome, Termination, TraceInput,
    current_profile, historical_profile,
};

const TARGET: u32 = 95;
const INITIAL_WORD: u32 = 7_174_457;
const BOUNDARIES: [u8; 18] = [
    0, 1, 2, 3, 7, 15, 31, 63, 64, 65, 95, 127, 128, 129, 191, 223, 254, 255,
];

#[expect(
    clippy::arithmetic_side_effects,
    clippy::integer_division,
    clippy::integer_division_remainder_used,
    reason = "frozen independent fifteen-trit scalar rotation oracle"
)]
const fn scalar_rotate(word: u32) -> u32 {
    word / 3 + word % 3 * 4_782_969
}

#[expect(
    clippy::arithmetic_side_effects,
    clippy::integer_division_remainder_used,
    reason = "independent ternary truth table, not the production VM operator"
)]
fn scalar_crazy(mut data: u32, mut accumulator: u32) -> u32 {
    let mut result = 0u32;
    let mut place = 1u32;
    for _ in 0..15usize {
        let trit = match (data % 3, accumulator % 3) {
            (0 | 1, 0) | (2, 2) => 1,
            (1, 2) | (2, 0 | 1) => 2,
            _ => 0,
        };
        result += trit * place;
        data /= 3;
        accumulator /= 3;
        place *= 3;
    }
    result
}

#[test]
fn two_input_mutation_rejects_incompatible_loader_profile() {
    assert_eq!(
        layout::build_seeded_two_input_state_update_source(
            historical_profile(),
            *b",H",
        ),
        Err(layout::RepeatedLoaderRotationError::UnsupportedProfile),
    );
    assert_eq!(
        layout::build_seeded_two_input_state_update_source(
            current_profile(),
            *b"Iy",
        ),
        Err(layout::RepeatedLoaderRotationError::InvalidResetSeed {
            tail: *b"Iy",
        }),
    );
}

#[test]
#[expect(
    clippy::cognitive_complexity,
    clippy::too_many_lines,
    clippy::panic_in_result_fn,
    clippy::integer_division_remainder_used,
    reason = "all signed inputs and exact physical reads and writes are pinned"
)]
fn second_guest_input_mutates_state_left_by_first_guest_input()
-> Result<(), String> {
    let profile = current_profile();
    let source =
        layout::build_seeded_two_input_state_update_source(profile, *b",H")
            .map_err(|error| format!("{error:?}"))?;
    assert_eq!(source.len(), 91);
    let loaded = ProfileMachine::from_source(profile, &source, vec![])
        .map_err(|error| error.to_string())?;
    assert_eq!(loaded.memory_word(TARGET), Ok(INITIAL_WORD));
    let rotated = (0..9usize).fold(INITIAL_WORD, |word, _| scalar_rotate(word));
    let mut varying_first = BTreeSet::new();
    let mut varying_second = BTreeSet::new();
    let inputs = once(Vec::new())
        .chain(once(vec![0x42]))
        .chain(BOUNDARIES.map(|byte| vec![0x42, byte]))
        .chain(BOUNDARIES.map(|byte| vec![byte, 0x81]))
        .chain(once(vec![0x42, 0x81, 0x00, 0xff]));
    let mut cases = 0usize;
    for input in inputs {
        let first = input.first().copied();
        let second = input.get(1).copied();
        let first_word = first.map_or_else(|| profile.eof_word(), u32::from);
        let second_word = second.map_or_else(|| profile.eof_word(), u32::from);
        let first_state = scalar_crazy(rotated, first_word);
        let second_state = scalar_crazy(first_state, second_word);
        let byte = u8::try_from(second_state % 256)
            .map_err(|error| error.to_string())?;
        let mut vm = ProfileMachine::from_state(
            profile,
            loaded.memory().to_vec(),
            input,
            ProfileRegisters::default(),
        )
        .map_err(|error| error.to_string())?;
        let mut trace = Vec::new();
        let outcome = vm
            .run_traced(54, &mut |step| trace.push(*step))
            .map_err(|error| error.to_string())?;
        assert_eq!(outcome, RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 54,
        });
        assert_eq!(trace.len(), 54);
        let mut prepared = INITIAL_WORD;
        for position in [3usize, 7, 11, 15, 19, 23, 27, 31, 35] {
            let step =
                trace.get(position).ok_or("missing physical rotation")?;
            assert_eq!(step.decoded, Some(b'*'));
            assert_eq!(step.before.registers.data_pointer, TARGET);
            assert_eq!(
                step.memory_reads
                    .data
                    .map(|read| (read.address, read.value)),
                Some((TARGET, prepared))
            );
            let next = scalar_rotate(prepared);
            assert_eq!(step.after.registers.accumulator, next);
            assert_eq!(
                step.memory_delta.data.map(|write| {
                    (write.address, write.before, write.after)
                }),
                (prepared != next).then_some((TARGET, prepared, next)),
            );
            prepared = next;
        }
        assert_eq!(prepared, rotated);
        for (position, value) in [(39usize, first), (47, second)] {
            let step = trace.get(position).ok_or("missing guest input")?;
            assert_eq!(step.decoded, Some(profile.input_instruction()));
            assert_eq!(step.before.registers.data_pointer, TARGET);
            assert_eq!(
                step.input,
                Some(value.map_or(TraceInput::EndOfInput, TraceInput::Byte))
            );
        }
        for position in [40usize, 44, 48] {
            for (offset, address, word) in
                [(0, 96u32, 72u32), (1, 73, 61), (2, 62, 94)]
            {
                let step = trace
                    .get(position.saturating_add(offset))
                    .ok_or("missing pointer reset")?;
                assert_eq!(step.decoded, Some(b'j'));
                assert_eq!(step.before.registers.data_pointer, address);
                assert_eq!(
                    step.memory_reads.data.map(|read| read.value),
                    Some(word)
                );
            }
        }
        for (position, before, after) in [
            (43usize, rotated, first_state),
            (51, first_state, second_state),
        ] {
            let step = trace.get(position).ok_or("missing guest update")?;
            assert_eq!(step.decoded, Some(b'p'));
            assert_eq!(step.before.registers.data_pointer, TARGET);
            assert_eq!(
                step.memory_reads.data.map(|read| read.value),
                Some(before)
            );
            assert_eq!(step.after.registers.accumulator, after);
            assert_eq!(
                step.memory_delta.data.map(|write| {
                    (write.address, write.before, write.after)
                }),
                (before != after).then_some((TARGET, before, after)),
            );
        }
        assert_eq!(vm.memory_word(TARGET), Ok(second_state));
        assert_eq!(trace.get(52).and_then(|step| step.output), Some(byte));
        assert_eq!(vm.output(), &[byte]);
        assert_eq!(vm.input_consumed(), input_len(first, second));
        if first == Some(0x42) && second.is_some() {
            _ = varying_second.insert(byte);
        }
        if second == Some(0x81) && first.is_some() {
            _ = varying_first.insert(byte);
        }
        cases = cases.saturating_add(1);
    }
    assert_eq!(cases, 39);
    assert!(
        varying_first.len() > 1,
        "first byte must affect guest output"
    );
    assert!(
        varying_second.len() > 1,
        "second byte must affect guest output"
    );
    Ok(())
}

fn input_len(first: Option<u8>, second: Option<u8>) -> usize {
    usize::from(first.is_some()).saturating_add(usize::from(second.is_some()))
}
