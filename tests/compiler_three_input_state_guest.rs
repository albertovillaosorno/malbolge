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

// Feed the exact source and independently calculated full-width state
// transitions into the compiler's separate bounded guest-path verifier.
struct ThreeInputOracle {
    code_positions: Vec<u32>,
    data_writes: Vec<layout::BoundedRevisitDataWrite>,
    input: Vec<u8>,
    input_events: [TraceInput; 3],
    instruction_writes: Vec<layout::BoundedRevisitInstructionWrite>,
    io_events: [layout::BoundedRevisitIoEvent; 4],
    output: [u8; 1],
}

impl ThreeInputOracle {
    fn expectation(&self) -> layout::BoundedRevisitExpectation<'_> {
        layout::BoundedRevisitExpectation {
            input: &self.input,
            code_positions: &self.code_positions,
            output: &self.output,
            input_consumed: self.input.len().min(3),
            input_events: &self.input_events,
            io_events: &self.io_events,
            data_writes: &self.data_writes,
        }
    }

    #[expect(
        clippy::arithmetic_side_effects,
        clippy::integer_division_remainder_used,
        clippy::integer_division,
        clippy::too_many_lines,
        reason = "independent exact 15-trit physical seed and I/O oracle"
    )]
    fn new(input: Vec<u8>) -> Result<Self, String> {
        const MODULUS: u32 = 14_348_907;
        let profile = current_profile();
        let words = [
            input.first().copied(),
            input.get(1).copied(),
            input.get(2).copied(),
        ]
        .map(|byte| byte.map_or_else(|| profile.eof_word(), u32::from));
        let mut writes = Vec::new();
        let mut seed = 7_174_489u32;
        for round in 0u32..9 {
            let after = seed / 3 + seed % 3 * (MODULUS / 3);
            writes.push(layout::BoundedRevisitInstructionWrite {
                address: 95,
                after,
                before: seed,
                opcode: b'*',
                step: 3 + 4 * round,
            });
            seed = after;
        }
        if seed != FIRST_SEED {
            return Err("wrong independent rotated first seed".to_owned());
        }
        let first = independent_crazy(FIRST_SEED, words[0]);
        let second = independent_crazy(SECOND_SEED, words[1]);
        let cross = independent_crazy(first, second);
        let third = independent_crazy(SECOND_SEED, words[2]);
        let triple = independent_crazy(cross, third);
        for (step, address, before, after) in [
            (43u32, 95u32, seed, first),
            (53, 97, SECOND_SEED, second),
            (57, 95, first, cross),
            (62, 103, SECOND_SEED, third),
            (69, 95, cross, triple),
        ] {
            writes.push(layout::BoundedRevisitInstructionWrite {
                address,
                after,
                before,
                opcode: b'p',
                step,
            });
        }
        let data_writes = writes
            .iter()
            .filter(|write| write.before != write.after)
            .map(|write| layout::BoundedRevisitDataWrite {
                step: write.step,
                address: write.address,
                before: write.before,
                after: write.after,
            })
            .collect();
        let input_events = [
            input.first().copied(),
            input.get(1).copied(),
            input.get(2).copied(),
        ]
        .map(|byte| byte.map_or(TraceInput::EndOfInput, TraceInput::Byte));
        let output = [
            u8::try_from(triple % 256).map_err(|error| error.to_string())?
        ];
        let io_events = [
            layout::BoundedRevisitIoEvent {
                step: 39,
                effect: layout::BoundedRevisitIoEffect::Input(input_events[0]),
            },
            layout::BoundedRevisitIoEvent {
                step: 47,
                effect: layout::BoundedRevisitIoEffect::Input(input_events[1]),
            },
            layout::BoundedRevisitIoEvent {
                step: 59,
                effect: layout::BoundedRevisitIoEffect::Input(input_events[2]),
            },
            layout::BoundedRevisitIoEvent {
                step: 70,
                effect: layout::BoundedRevisitIoEffect::Output(output[0]),
            },
        ];
        Ok(Self {
            code_positions: (0u32..72).collect(),
            data_writes,
            input,
            input_events,
            instruction_writes: writes,
            io_events,
            output,
        })
    }
}

#[test]
#[expect(
    clippy::too_many_lines,
    clippy::cognitive_complexity,
    reason = "full source-identical guest verifier and forged-state controls"
)]
fn bounded_verifier_admits_lossless_three_input_arithmetic()
-> Result<(), String> {
    let profile = current_profile();
    let source = layout::build_three_input_cross_fold_source(profile)
        .map_err(|error| format!("{error:?}"))?;
    let identity = layout::LinearProfileIdentity {
        fingerprint: profile.fingerprint(),
        id: profile.id(),
    };
    let cases = [
        vec![],
        vec![0],
        vec![0, 0],
        vec![255, 128, 1],
        vec![3, 4, 5, 9],
        vec![255, 0, 128],
    ]
    .into_iter()
    .map(ThreeInputOracle::new)
    .collect::<Result<Vec<_>, _>>()?;
    let expectations = cases
        .iter()
        .map(ThreeInputOracle::expectation)
        .collect::<Vec<_>>();
    let verified = layout::admit_bounded_guest_path_batch(
        profile,
        &source,
        identity,
        &expectations,
    )
    .map_err(|error| format!("three-word verifier: {error:?}"))?;
    assert_eq!(verified.len(), cases.len());
    for (path, oracle) in verified.iter().zip(cases.iter()) {
        assert_eq!(path.source(), source);
        assert_eq!(path.input_events(), oracle.input_events);
        assert_eq!(path.io_events(), oracle.io_events);
        assert_eq!(path.data_writes(), oracle.data_writes);
        assert_eq!(path.output(), oracle.output);
        assert_eq!(path.code_positions(), oracle.code_positions);
        assert_eq!(
            layout::verify_bounded_guest_instruction_writes(
                path,
                &oracle.instruction_writes,
            ),
            Ok(())
        );
        assert_eq!(path.mutation_targets().len(), 14);
    }
    let first_path = verified.first().ok_or("missing accepted path")?;
    let first_case = cases.first().ok_or("missing oracle")?;
    let mut forged = first_case.instruction_writes.clone();
    let final_write = forged.last_mut().ok_or("missing third input fold")?;
    final_write.after ^= 1;
    assert_eq!(
        layout::verify_bounded_guest_instruction_writes(first_path, &forged),
        Err(layout::BoundedRevisitError::InstructionWritesMismatch),
    );
    let second_case = cases.get(1).ok_or("missing second oracle")?;
    let mut forged_output = second_case.output;
    forged_output[0] ^= 1;
    assert_eq!(
        layout::admit_bounded_guest_path(
            profile,
            &source,
            identity,
            layout::BoundedRevisitExpectation {
                output: &forged_output,
                ..second_case.expectation()
            },
        ),
        Err(layout::BoundedRevisitError::OutputMismatch),
    );
    Ok(())
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

/// The source C62 literal is encrypted by its own reached `p`.
/// Preserve the third word in virgin M103 before following the actual
/// encrypted M62/M58 pointer chain back to the two-input cross-fold.
#[test]
#[expect(
    clippy::too_many_lines,
    reason = "full VM paths and an independent 257-class third-word oracle"
)]
fn three_way_fold_restores_pointer_after_self_encryption() -> Result<(), String>
{
    let profile = current_profile();
    let source = layout::build_three_input_cross_fold_source(profile)
        .map_err(|error| format!("{error:?}"))?;
    assert_eq!(source.len(), 91);
    assert_eq!(source[74], 101);
    assert_eq!(source[81], 94);
    assert_eq!(source.get(89..), Some(b"IH".as_slice()));
    let loaded = ProfileMachine::from_source(profile, &source, Vec::new())
        .map_err(|error| error.to_string())?;
    assert_eq!(loaded.memory_word(74), Ok(101));
    assert_eq!(loaded.memory_word(81), Ok(94));
    assert_eq!(loaded.memory_word(103), Ok(SECOND_SEED));
    assert_eq!(loaded.memory_word(104), Ok(72));

    // The third *stored* full word distinguishes every byte and EOF;
    // unlike the old M96=72 fold, values 1 and 2 do not alias.
    let distinct = (u8::MIN..=u8::MAX)
        .map(|byte| independent_crazy(SECOND_SEED, u32::from(byte)))
        .collect::<std::collections::BTreeSet<_>>();
    assert_eq!(distinct.len(), 256);
    assert!(
        !distinct
            .contains(&independent_crazy(SECOND_SEED, profile.eof_word(),))
    );
    assert_ne!(
        independent_crazy(SECOND_SEED, 1),
        independent_crazy(SECOND_SEED, 2),
    );
    let cases: &[&[u8]] = &[
        b"",
        b"\x00",
        b"\xff\x1f",
        b"\x00\xff\x00",
        b"\x01\x00\x01",
        b"\x1f\xff\xff\x80",
        b"\x80\x7f\xfe",
        b"\xff\xff\xff",
        b"\x2a\x35\x42\x00",
        b"\x2a\x35\x00",
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
        let third = independent_crazy(SECOND_SEED, words[2]);
        let triple = independent_crazy(cross, third);
        let output =
            u8::try_from(triple % 256).map_err(|error| error.to_string())?;
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
        let mut jumps = Vec::new();
        let outcome = vm
            .run_traced(72, &mut |step| {
                let position = step.before.registers.code_pointer;
                if let Some(value) = step.input {
                    reads.push((position, value));
                }
                if let Some(value) = step.output {
                    outputs.push((position, value));
                }
                if [43, 53, 57, 62, 69].contains(&position) {
                    assert_eq!(step.decoded, Some(b'p'));
                    writes.push((
                        position,
                        step.before.registers.data_pointer,
                        step.after.registers.accumulator,
                    ));
                }
                if [58, 60, 63, 64, 65, 66, 68].contains(&position) {
                    assert_eq!(step.decoded, Some(b'j'));
                    jumps.push((position, step.after.registers.data_pointer));
                }
                if [61, 67].contains(&position) {
                    assert_eq!(step.decoded, Some(b'o'));
                    assert_eq!(
                        step.after.registers.data_pointer,
                        if position == 61 {
                            103
                        } else {
                            81
                        }
                    );
                }
            })
            .map_err(|error| error.to_string())?;
        assert_eq!(outcome, RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 72,
        });
        assert_eq!(vm.memory_word(95), Ok(triple));
        assert_eq!(vm.memory_word(96), Ok(72));
        assert_eq!(vm.memory_word(97), Ok(second));
        assert_eq!(vm.memory_word(103), Ok(third));
        assert_eq!(vm.memory_word(74), Ok(101));
        assert_eq!(vm.memory_word(81), Ok(94));
        assert_eq!(writes, [
            (43, 95, first),
            (53, 97, second),
            (57, 95, cross),
            (62, 103, third),
            (69, 95, triple),
        ]);
        assert_eq!(jumps, [
            (58, 73),
            (60, 102),
            (63, 73),
            (64, 62),
            (65, 58),
            (66, 80),
            (68, 95),
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
                59,
                stream
                    .get(2)
                    .copied()
                    .map_or(TraceInput::EndOfInput, TraceInput::Byte)
            ),
        ]);
        assert_eq!(outputs, [(70, output)]);
        assert_eq!(vm.output(), &[output]);
        assert_eq!(vm.input_consumed(), stream.len().min(3));
    }
    Ok(())
}

/// A pair of physical all-ones crazy writes reverses the signed input
/// encoding without substituting a host byte for either guest operation.
#[test]
#[expect(
    clippy::too_many_lines,
    reason = "byte/EOF and physical word-oracle execution traces"
)]
fn encoded_third_signed_input_roundtrips_to_original_full_guest_word()
-> Result<(), String> {
    let profile = current_profile();
    let source = layout::build_three_input_signed_roundtrip_source(profile)
        .map_err(|error| format!("{error:?}"))?;
    assert_eq!(source.len(), 91);
    let loaded = ProfileMachine::from_source(profile, &source, Vec::new())
        .map_err(|error| error.to_string())?;
    assert_eq!(loaded.memory_word(103), Ok(SECOND_SEED));
    assert_eq!(loaded.memory_word(109), Ok(SECOND_SEED));
    for value in (u8::MIN..=u8::MAX)
        .map(u32::from)
        .chain([profile.eof_word()])
    {
        assert_eq!(
            independent_crazy(
                SECOND_SEED,
                independent_crazy(SECOND_SEED, value),
            ),
            value,
        );
    }
    let cases: &[&[u8]] = &[
        b"",
        b"\x00",
        b"\xff",
        b"\x00\xff",
        b"\x00\xff\x01",
        b"\x00\xff\x02\x7a",
        b"\x00\xff\x80",
        b"\xff\x80\xff",
        b"\x01\x02\x03\x04",
        b"\x2a\x35\x64",
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
        let third_encoded = independent_crazy(SECOND_SEED, words[2]);
        let expected_output =
            u8::try_from(words[2] % 256).map_err(|error| error.to_string())?;
        let mut vm = ProfileMachine::from_state(
            profile,
            loaded.memory().to_vec(),
            stream.to_vec(),
            ProfileRegisters::default(),
        )
        .map_err(|error| error.to_string())?;
        let mut reads = Vec::new();
        let mut writes = Vec::new();
        let outcome = vm
            .run_traced(71, &mut |step| {
                let position = step.before.registers.code_pointer;
                if let Some(input) = step.input {
                    reads.push((position, input));
                }
                if [43, 53, 57, 62, 68].contains(&position) {
                    assert_eq!(step.decoded, Some(b'p'));
                    writes.push((
                        position,
                        step.before.registers.data_pointer,
                        step.after.registers.accumulator,
                    ));
                }
            })
            .map_err(|error| error.to_string())?;
        assert_eq!(outcome, RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 71,
        });
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
                59,
                stream
                    .get(2)
                    .copied()
                    .map_or(TraceInput::EndOfInput, TraceInput::Byte)
            ),
        ]);
        assert_eq!(writes, [
            (43, 95, first),
            (53, 97, second),
            (57, 95, cross),
            (62, 103, third_encoded),
            (68, 109, words[2]),
        ]);
        assert_eq!(vm.memory_word(95), Ok(cross));
        assert_eq!(vm.memory_word(97), Ok(second));
        assert_eq!(vm.memory_word(103), Ok(third_encoded));
        assert_eq!(vm.memory_word(109), Ok(words[2]));
        assert_eq!(vm.output(), &[expected_output]);
        assert_eq!(vm.input_consumed(), stream.len().min(3));
    }
    Ok(())
}
