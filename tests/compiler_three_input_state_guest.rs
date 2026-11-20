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
//   - Independent three-read N15 state and cross-input fold VM witness.
// - Must-Not:
//   - Treat disjoint third-word state as C23 checksum arithmetic or EOF loop.
// - Allows:
//   - Inputs: exact physical loader tail, binary/EOF streams.
//   - Outputs: read/write addresses, preserved memory and bounded output.
//   - Side effects: isolated, in-memory normative guest execution only.
// - Split-When:
//   - Full source-C mutable arithmetic and loop linkage subsumes the probe.
// - Merge-When:
//   - A generic physically linked ternary accumulator replaces this source.
// - Summary:
//   - Two-input guest crazy fold survives a subsequent third signed input.

//! The first two live signed guest words cross-fold before an independent
//! third word updates a separate cell; neither a C sum nor EOF loop exists.

use std::collections::BTreeMap;

#[path = "../src/compiler/malbolge-layout/composition/lib.rs"]
pub mod layout;

use malbolge::{
    ProfileMachine, ProfileRegisters, RunOutcome, Termination, TraceInput,
    current_profile, historical_profile,
};

const FIRST_SEED: u32 = 7_200_697;
const SECOND_SEED: u32 = 7_174_453;

#[expect(
    clippy::arithmetic_side_effects,
    clippy::integer_division,
    clippy::integer_division_remainder_used,
    reason = "independent finite 15-trit truth table"
)]
fn independent_crazy(mut data: u32, mut accumulator: u32) -> u32 {
    let mut result = 0;
    let mut place = 1;
    for _ in 0..15 {
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
fn triple_signed_read_rejects_historical_profile() {
    assert_eq!(
        layout::build_cross_fold_followed_by_third_input_source(
            historical_profile()
        ),
        Err(layout::RepeatedLoaderRotationError::UnsupportedProfile),
    );
}

#[test]
#[expect(
    clippy::too_many_lines,
    clippy::cognitive_complexity,
    reason = "each real VM path has independent physical state assertions"
)]
fn third_read_preserves_cross_fold_and_updates_separate_word()
-> Result<(), String> {
    let profile = current_profile();
    let source =
        layout::build_cross_fold_followed_by_third_input_source(profile)
            .map_err(|error| format!("{error:?}"))?;
    assert_eq!(source.len(), 91);
    assert_eq!(source.get(89..), Some(b"IH".as_slice()));
    let loaded = ProfileMachine::from_source(profile, &source, Vec::new())
        .map_err(|error| error.to_string())?;
    assert_eq!(loaded.memory_word(96), Ok(72));
    assert_eq!(loaded.memory_word(97), Ok(SECOND_SEED));
    let cases: &[&[u8]] = &[
        b"",
        b"\x00",
        b"\xff\x1f",
        b"\x00\xff\x00",
        b"\x01\x00\x01",
        b"\x1f\xff\xff\x80",
        b"\x80\x7f\xfe",
        b"\xff\xff\xff",
    ];
    for &stream in cases {
        let words = [
            stream.first().copied(),
            stream.get(1).copied(),
            stream.get(2).copied(),
        ]
        .map(|word| word.map_or_else(|| profile.eof_word(), u32::from));
        let first = independent_crazy(FIRST_SEED, words[0]);
        let second = independent_crazy(SECOND_SEED, words[1]);
        let cross = independent_crazy(first, second);
        let third = independent_crazy(72, words[2]);
        let output =
            u8::try_from(third % 256).map_err(|error| error.to_string())?;
        let mut vm = ProfileMachine::from_state(
            profile,
            loaded.memory().to_vec(),
            stream.to_vec(),
            ProfileRegisters::default(),
        )
        .map_err(|error| error.to_string())?;
        let mut reads = Vec::new();
        let mut writes = Vec::new();
        let mut outputs = Vec::new();
        let outcome = vm
            .run_traced(65, &mut |step| {
                let position = step.before.registers.code_pointer;
                if let Some(value) = step.input {
                    reads.push((position, value));
                }
                if let Some(value) = step.output {
                    outputs.push((position, value));
                }
                if [43, 53, 57, 62].contains(&position) {
                    assert_eq!(step.decoded, Some(b'p'));
                    writes.push((
                        position,
                        step.before.registers.data_pointer,
                        step.after.registers.accumulator,
                    ));
                }
                if (58..=60).contains(&position) {
                    assert_eq!(step.decoded, Some(b'j'));
                    assert_eq!(
                        step.after.registers.data_pointer,
                        match position {
                            58 => 73,
                            59 => 62,
                            _ => 95,
                        }
                    );
                }
            })
            .map_err(|error| error.to_string())?;
        assert_eq!(outcome, RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 65,
        });
        assert_eq!(vm.memory_word(95), Ok(cross));
        assert_eq!(vm.memory_word(96), Ok(third));
        assert_eq!(vm.memory_word(97), Ok(second));
        assert_eq!(writes, [
            (43, 95, first),
            (53, 97, second),
            (57, 95, cross),
            (62, 96, third),
        ]);
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
            (
                61,
                stream
                    .get(2)
                    .copied()
                    .map_or(TraceInput::EndOfInput, TraceInput::Byte)
            ),
        ]);
        assert_eq!(outputs, [(63, output)]);
        assert_eq!(vm.output(), &[output]);
        assert_eq!(vm.input_consumed(), stream.len().min(3));
    }
    // The third 72-seeded cell cannot represent C23 signed input losslessly;
    // these are distinct real input values, but their encoded states alias.
    assert_eq!(independent_crazy(72, 1), independent_crazy(72, 2));
    Ok(())
}

/// Prove all distinct third-word classes independently of the guest VM.
/// Each representative then executes as a complete 65-step physical guest.
#[test]
#[expect(
    clippy::too_many_lines,
    reason = "independent complete byte-class and signed-EOF guest witnesses"
)]
fn third_state_classes_and_true_eof_have_complete_guest_paths()
-> Result<(), String> {
    let profile = current_profile();
    let mut classes = BTreeMap::new();
    for byte in u8::MIN..=u8::MAX {
        let _representative = classes
            .entry(independent_crazy(72, u32::from(byte)))
            .or_insert(byte);
    }
    // With this exact M96 seed the ternary map is not C23 storage: 256
    // bytes merge into 36 classes. The real EOF word is a separate class.
    assert_eq!(classes.len(), 36);
    let eof = independent_crazy(72, profile.eof_word());
    assert!(!classes.contains_key(&eof));
    assert_eq!(independent_crazy(72, 1), independent_crazy(72, 2));

    let source =
        layout::build_cross_fold_followed_by_third_input_source(profile)
            .map_err(|error| format!("{error:?}"))?;
    let loaded = ProfileMachine::from_source(profile, &source, Vec::new())
        .map_err(|error| error.to_string())?;
    let first = independent_crazy(FIRST_SEED, 42);
    let second = independent_crazy(SECOND_SEED, 53);
    let cross = independent_crazy(first, second);
    for third in classes.values().copied().map(Some).chain([None]) {
        let third_word = third.map_or_else(|| profile.eof_word(), u32::from);
        let state = independent_crazy(72, third_word);
        let mut stream = vec![42, 53];
        if let Some(byte) = third {
            stream.push(byte);
            // The trailing sentinel is deliberately not consumed.
            stream.push(77);
        }
        let mut vm = ProfileMachine::from_state(
            profile,
            loaded.memory().to_vec(),
            stream,
            ProfileRegisters::default(),
        )
        .map_err(|error| error.to_string())?;
        let mut reads = Vec::new();
        let outcome = vm
            .run_traced(65, &mut |step| {
                if let Some(input) = step.input {
                    reads.push((step.before.registers.code_pointer, input));
                }
            })
            .map_err(|error| error.to_string())?;
        assert_eq!(outcome, RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 65,
        });
        assert_eq!(reads, [
            (39, TraceInput::Byte(42)),
            (47, TraceInput::Byte(53)),
            (61, third.map_or(TraceInput::EndOfInput, TraceInput::Byte),),
        ]);
        assert_eq!(vm.memory_word(95), Ok(cross));
        assert_eq!(vm.memory_word(96), Ok(state));
        assert_eq!(vm.memory_word(97), Ok(second));
        assert_eq!(vm.output(), &[
            u8::try_from(state % 256).map_err(|error| error.to_string())?
        ]);
        assert_eq!(
            vm.input_consumed(),
            if third.is_some() {
                3
            } else {
                2
            }
        );
    }
    Ok(())
}
