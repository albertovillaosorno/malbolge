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
//   - Independent normative guest proof of an arithmetic fold over two saved
//     inputs.
// - Must-Not:
//   - Equate a ternary crazy fold with C23 addition, XOR, or a checksum.
// - Allows:
//   - Inputs: two actual signed reads with all byte/EOF classes for each
//     operand.
//   - Outputs: physical writes, memory persistence, one folded output and halt.
//   - Side effects: isolated in-memory guest machines only.
// - Split-When:
//   - Source-authenticated C32 arithmetic lowering consumes a generic fold.
// - Merge-When:
//   - A verified source-C stateful arithmetic linker supersedes this probe.
// - Summary:
//   - Both stored guest inputs participate in one later physical binary fold.

//! Two independent saved words feed a later guest arithmetic operation.

#[path = "../src/compiler/malbolge-layout/composition/lib.rs"]
pub mod layout;

use std::collections::BTreeSet;
use std::iter::once;

use malbolge::{
    ProfileMachine, ProfileRegisters, RunOutcome, Termination, TraceInput,
    current_profile, historical_profile,
};

const FIRST_SEED: u32 = 7_200_697;
const SECOND_SEED: u32 = 7_174_453;

#[expect(
    clippy::arithmetic_side_effects,
    clippy::integer_division_remainder_used,
    reason = "independent finite 15-trit oracle for guest crazy arithmetic"
)]
fn independent_crazy(mut data: u32, mut accumulator: u32) -> u32 {
    let mut result = 0;
    let mut place = 1;
    for _ in 0usize..15 {
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
fn cross_input_fold_rejects_historical_guest_profile() {
    assert_eq!(
        layout::build_two_retained_inputs_cross_fold_source(
            historical_profile()
        ),
        Err(layout::RepeatedLoaderRotationError::UnsupportedProfile),
    );
}

#[test]
#[expect(
    clippy::cognitive_complexity,
    clippy::too_many_lines,
    clippy::panic_in_result_fn,
    clippy::integer_division_remainder_used,
    reason = "bounded normative two-input state and arithmetic trace admission"
)]
fn two_stored_signed_words_reach_a_later_real_crazy_operation()
-> Result<(), String> {
    let profile = current_profile();
    let source = layout::build_two_retained_inputs_cross_fold_source(profile)
        .map_err(|error| format!("{error:?}"))?;
    assert_eq!(source.len(), 91);
    assert_eq!(source.get(89..), Some(b"IH".as_slice()));
    let loaded = ProfileMachine::from_source(profile, &source, Vec::new())
        .map_err(|error| error.to_string())?;
    assert_eq!(loaded.memory_word(95), Ok(7_174_489));
    assert_eq!(loaded.memory_word(97), Ok(SECOND_SEED));

    // Exhaustively prove each storage seed is byte-plus-EOF injective.
    for seed in [FIRST_SEED, SECOND_SEED] {
        let words = (u8::MIN..=u8::MAX)
            .map(|byte| independent_crazy(seed, u32::from(byte)))
            .collect::<BTreeSet<_>>();
        assert_eq!(words.len(), 256);
        assert!(!words.contains(&independent_crazy(seed, profile.eof_word())));
    }

    // A finite real-VM witness per operand, with the other fixed.
    // Include EOF attempts, edge bytes and unread trailing input.
    let boundary = [0u8, 1, 2, 31, 32, 63, 64, 127, 128, 191, 254, 255, 42];
    let cases = once(Vec::new())
        .chain(boundary.into_iter().map(|first| vec![first, 42]))
        .chain(boundary.into_iter().map(|second| vec![42, second]))
        .chain(once(vec![42]))
        .chain(once(vec![255, 0, 128, 31]));
    let mut count = 0usize;
    for stream in cases {
        let first = stream
            .first()
            .copied()
            .map_or_else(|| profile.eof_word(), u32::from);
        let second = stream
            .get(1)
            .copied()
            .map_or_else(|| profile.eof_word(), u32::from);
        let retained_first = independent_crazy(FIRST_SEED, first);
        let retained_second = independent_crazy(SECOND_SEED, second);
        let combined = independent_crazy(retained_first, retained_second);
        let output =
            u8::try_from(combined % 256).map_err(|error| error.to_string())?;
        let mut vm = ProfileMachine::from_state(
            profile,
            loaded.memory().to_vec(),
            stream.clone(),
            ProfileRegisters::default(),
        )
        .map_err(|error| error.to_string())?;
        let mut reads = Vec::new();
        let mut writes = Vec::new();
        let mut outputs = Vec::new();
        let outcome = vm
            .run_traced(60, &mut |trace| {
                let address = trace.before.registers.code_pointer;
                if let Some(input) = trace.input {
                    reads.push((address, input));
                }
                if let Some(value) = trace.output {
                    outputs.push((address, value));
                }
                if [43, 53, 57].contains(&address) {
                    assert_eq!(trace.decoded, Some(b'p'));
                    let target = trace.before.registers.data_pointer;
                    writes.push((
                        address,
                        target,
                        trace.after.registers.accumulator,
                    ));
                }
                if address == 43 {
                    assert_eq!(trace.decoded, Some(b'p'));
                    assert_eq!(trace.before.registers.data_pointer, 95);
                    assert_eq!(
                        trace.after.registers.accumulator,
                        retained_first
                    );
                }
                if address == 53 {
                    assert_eq!(trace.decoded, Some(b'p'));
                    assert_eq!(trace.before.registers.data_pointer, 97);
                    assert_eq!(
                        trace.after.registers.accumulator,
                        retained_second
                    );
                }
                if (54..=56).contains(&address) {
                    assert_eq!(trace.decoded, Some(b'j'));
                    let (before, after) = match address {
                        54 => (98, 73),
                        55 => (73, 62),
                        56 => (62, 95),
                        _ => (u32::MAX, u32::MAX),
                    };
                    assert_eq!(trace.before.registers.data_pointer, before);
                    assert_eq!(trace.after.registers.data_pointer, after);
                }
                if address == 57 {
                    assert_eq!(trace.decoded, Some(b'p'));
                    assert_eq!(trace.before.registers.data_pointer, 95);
                    assert_eq!(
                        trace.memory_reads.data.map(|read| read.value),
                        Some(retained_first)
                    );
                    assert_eq!(
                        trace.before.registers.accumulator,
                        retained_second
                    );
                    assert_eq!(trace.after.registers.accumulator, combined);
                }
            })
            .map_err(|error| error.to_string())?;
        assert_eq!(outcome, RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 60,
        });
        assert_eq!(vm.memory_word(95), Ok(combined));
        assert_eq!(vm.memory_word(97), Ok(retained_second));
        assert_eq!(reads, [
            (
                39,
                stream
                    .first()
                    .copied()
                    .map_or(TraceInput::EndOfInput, TraceInput::Byte)
            ),
            (
                47,
                stream
                    .get(1)
                    .copied()
                    .map_or(TraceInput::EndOfInput, TraceInput::Byte)
            ),
        ]);
        assert_eq!(outputs, [(58, output)]);
        assert_eq!(vm.output(), &[output]);
        assert_eq!(vm.input_consumed(), stream.len().min(2));
        assert_eq!(writes, [
            (43, 95, retained_first),
            (53, 97, retained_second),
            (57, 95, combined),
        ]);
        count += 1usize;
    }
    assert_eq!(count, 29usize);
    Ok(())
}
