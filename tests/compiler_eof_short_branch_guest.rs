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
//   - Two physically executable signed EOF/byte arms under a bounded VM.
// - Must-Not:
//   - Claim source-C lowering, persistent state, or a repeatable EOF loop.
// - Allows:
//   - Inputs: one graphical N15 program and bounded binary/EOF streams.
//   - Outputs: independently checked arithmetic and normative guest traces.
//   - Side effects: isolated, bounded in-memory VM runs only.
// - Split-When:
//   - A general compiler layout takes ownership of this physical witness.
// - Merge-When:
//   - The C compiler lowers verified dynamic source branches to these arms.
// - Summary:
//   - Both physical arms now read input exactly once across 257 classes.

//! Four writes and two more crazy steps physically branch to byte/EOF arms.
//! The successful-byte arm preserves unread input on its code revisit.

#[path = "../src/compiler/malbolge-layout/composition/lib.rs"]
pub mod layout;

use std::iter::once;

use malbolge::{
    ProfileMachine, ProfileRegisters, RunOutcome, Termination, TraceInput,
    current_profile, decode_profile_instruction,
};

const LENGTH: usize = 132;
const FIRST_OPERAND: u32 = 7_174_341;
const ROTATED_OPERAND: u32 = 3_618;
const THIRD_OPERAND: u32 = 7_174_350;
const FOURTH_OPERAND: u32 = 134;
const SUCCESS_CONTROL: u32 = 125;
const EOF_CONTROL: u32 = 368;

// A physical EOF arm is forward-only, while every byte arm revisits code.
// Batch admission must verify both complete paths for the SAME source, rather
// than silently applying the revisiting-only restriction to the EOF case.
struct OwnedBranchPath {
    input: Vec<u8>,
    input_events: [TraceInput; 1],
    io_events: [layout::BoundedRevisitIoEvent; 2],
    output: [u8; 1],
    path: Vec<u32>,
    writes: Vec<layout::BoundedRevisitDataWrite>,
}

impl OwnedBranchPath {
    fn expectation(&self) -> layout::BoundedRevisitExpectation<'_> {
        layout::BoundedRevisitExpectation {
            input: &self.input,
            code_positions: &self.path,
            output: &self.output,
            input_consumed: usize::from(!self.input.is_empty()),
            input_events: &self.input_events,
            io_events: &self.io_events,
            data_writes: &self.writes,
        }
    }

    fn new(input: Vec<u8>) -> Self {
        let eof = input.is_empty();
        let profile = current_profile();
        let word = input
            .first()
            .map_or_else(|| profile.eof_word(), |byte| u32::from(*byte));
        let read = input
            .first()
            .map_or(TraceInput::EndOfInput, |byte| TraceInput::Byte(*byte));
        let output_byte = if eof {
            30
        } else {
            154
        };
        let mut path = (0..=114u32).collect::<Vec<_>>();
        if eof {
            path.extend(126..=129);
        } else {
            path.extend(45..=104);
        }
        Self {
            input,
            input_events: [read],
            io_events: [
                layout::BoundedRevisitIoEvent {
                    step: 53,
                    effect: layout::BoundedRevisitIoEffect::Input(read),
                },
                layout::BoundedRevisitIoEvent {
                    step: if eof {
                        117
                    } else {
                        127
                    },
                    effect: layout::BoundedRevisitIoEffect::Output(output_byte),
                },
            ],
            output: [output_byte],
            path,
            writes: independent_branch_writes(word, eof),
        }
    }
}

fn encode(opcode: u8, position: usize) -> Result<u8, String> {
    let address = u32::try_from(position)
        .map_err(|error| format!("unrepresentable position: {error}"))?;
    (33..=126u8)
        .find(|byte| {
            decode_profile_instruction(u32::from(*byte), address)
                == Some(opcode)
        })
        .ok_or_else(|| format!("no graphical encoding at {position}"))
}

fn set(source: &mut [u8], position: usize, opcode: u8) -> Result<(), String> {
    let cell = source
        .get_mut(position)
        .ok_or_else(|| format!("source position {position} out of range"))?;
    *cell = encode(opcode, position)?;
    Ok(())
}

fn guest_source() -> Result<Vec<u8>, String> {
    let mut source = (0..LENGTH)
        .map(|position| encode(b'o', position))
        .collect::<Result<Vec<_>, _>>()?;
    set(&mut source, 8, b'j')?;
    for round in 0usize..12 {
        let position = 17usize.saturating_add(round.saturating_mul(3));
        set(&mut source, position, b'*')?;
        set(&mut source, position.saturating_add(1), b'j')?;
        set(&mut source, position.saturating_add(2), b'j')?;
    }
    set(&mut source, 53, current_profile().input_instruction())?;
    // D=135 after the input; one no-op reaches M[137]=125. A genuine j
    // then rewinds D to 126, and eight no-ops reach virgin loader M[134].
    set(&mut source, 55, b'j')?;
    for position in 64..=66 {
        set(&mut source, position, b'p')?;
    }
    // Skip virgin M[137] and M[138] to use M[139]=134 as fourth operand.
    set(&mut source, 69, b'p')?;
    // M[142] -> 7,174,350; M[7,174,351] -> 134. Rewind and then
    // advance D to the written fourth result at M[139].
    set(&mut source, 72, b'j')?;
    set(&mut source, 73, b'j')?;
    set(&mut source, 78, b'i')?;
    // The success control 125 first encrypts this still-graphical cell.
    // Execution then enters the previously skipped success arm at C=126.
    set(&mut source, 126, current_profile().output_instruction())?;
    set(&mut source, 127, b'v')?;
    let tail = source
        .get_mut(130..132)
        .ok_or_else(|| "source has no space for two-byte tail".to_owned())?;
    tail.copy_from_slice(b"-}");
    Ok(source)
}

// Independent literal trit table, not the normative runtime implementation.
#[expect(
    clippy::arithmetic_side_effects,
    clippy::integer_division_remainder_used,
    reason = "independent exact 15-trit arithmetic oracle"
)]
fn scalar_crazy(mut data: u32, mut accumulator: u32) -> u32 {
    const TRITS: [[u32; 3]; 3] = [[1, 0, 0], [1, 0, 2], [2, 2, 1]];
    let mut output = 0;
    let mut place = 1;
    for _ in 0usize..15 {
        let row = usize::try_from(data % 3).unwrap_or_default();
        let column = usize::try_from(accumulator % 3).unwrap_or_default();
        let digit = TRITS.get(row).and_then(|values| values.get(column));
        output += digit.copied().unwrap_or_default() * place;
        data /= 3;
        accumulator /= 3;
        place *= 3;
    }
    output
}

#[expect(
    clippy::arithmetic_side_effects,
    clippy::integer_division_remainder_used,
    clippy::integer_division,
    reason = "independent constant-width 15-trit rotation"
)]
const fn scalar_rotate(word: u32) -> u32 {
    word / 3 + (word % 3) * 4_782_969
}

fn control(input: u32) -> u32 {
    let rotated = (0usize..12).fold(134, |word, _| scalar_rotate(word));
    assert_eq!(rotated, ROTATED_OPERAND, "12 source rotations are exact");
    let first = scalar_crazy(FIRST_OPERAND, input);
    let second = scalar_crazy(rotated, first);
    let third = scalar_crazy(THIRD_OPERAND, second);
    scalar_crazy(FOURTH_OPERAND, third)
}

#[test]
fn independent_c23_byte_and_eof_control_words() {
    let profile = current_profile();
    assert_eq!(profile.word_trits(), 15);
    for byte in u8::MIN..=u8::MAX {
        assert_eq!(
            control(u32::from(byte)),
            SUCCESS_CONTROL,
            "successful input byte {byte}"
        );
    }
    assert_eq!(control(profile.eof_word()), EOF_CONTROL);
    assert_ne!(SUCCESS_CONTROL, EOF_CONTROL);
}

#[test]
#[expect(
    clippy::cognitive_complexity,
    clippy::too_many_lines,
    clippy::panic_in_result_fn,
    reason = "bounded normative guest-trace assertion matrix"
)]
fn all_257_signed_inputs_execute_the_correct_branch_boundary()
-> Result<(), String> {
    let profile = current_profile();
    let source = guest_source()?;
    assert_eq!(source.len(), LENGTH);
    assert_eq!(source.get(130..), Some(b"-}".as_slice()));
    for (position, &byte) in source.iter().enumerate() {
        let opcode = decode_profile_instruction(
            u32::from(byte),
            u32::try_from(position).map_err(|error| error.to_string())?,
        );
        if !matches!(
            opcode,
            Some(b'j' | b'i' | b'*' | b'p' | b'o' | b'<' | b'/' | b'v')
        ) {
            return Err(format!("invalid graphical instruction at {position}"));
        }
    }
    // Load the entire N15 image once, then execute each byte and EOF from
    // a fresh VM-validated state. The arithmetic oracle alone is not guest
    // execution evidence for the physical success arm.
    let loaded = ProfileMachine::from_source(profile, &source, Vec::new())
        .map_err(|error| error.to_string())?;
    for input in
        once(Vec::new()).chain((u8::MIN..=u8::MAX).map(|byte| vec![byte]))
    {
        let eof = input.is_empty();
        let word = input
            .first()
            .map_or_else(|| profile.eof_word(), |byte| u32::from(*byte));
        let mut vm = ProfileMachine::from_state(
            profile,
            loaded.memory().to_vec(),
            input.clone(),
            ProfileRegisters::default(),
        )
        .map_err(|error| error.to_string())?;
        let mut trace = vec![];
        let outcome = vm.run_traced(82, &mut |step| trace.push(*step));
        let input_step = trace.get(53).ok_or("missing signed input step")?;
        assert_eq!(input_step.decoded, Some(profile.input_instruction()));
        assert_eq!(
            input_step.input,
            Some(input.first().map_or(TraceInput::EndOfInput, |byte| {
                TraceInput::Byte(*byte)
            }))
        );
        for (position, address, operand) in [
            (64u32, 134u32, FIRST_OPERAND),
            (65, 135, ROTATED_OPERAND),
            (66, 136, THIRD_OPERAND),
            (69, 139, FOURTH_OPERAND),
            (72, 142, THIRD_OPERAND),
            (73, 7_174_351, 134),
        ] {
            let step = trace
                .iter()
                .find(|step| step.before.registers.code_pointer == position)
                .ok_or_else(|| format!("unreached C={position}"))?;
            assert_eq!(
                step.memory_reads
                    .data
                    .map(|read| (read.address, read.value)),
                Some((address, operand)),
                "C={position}"
            );
        }
        let branch = trace
            .iter()
            .find(|step| step.before.registers.code_pointer == 78)
            .ok_or("missing conditional i")?;
        assert_eq!(branch.decoded, Some(b'i'));
        assert_eq!(branch.before.registers.data_pointer, 139);
        assert_eq!(branch.before.registers.accumulator, control(word));
        assert_eq!(
            branch
                .memory_reads
                .data
                .map(|read| (read.address, read.value)),
            Some((139, control(word)))
        );
        if eof {
            // The VM rejects the unplaced EOF encryption target before
            // committing i. This is an explicit unsupported guest path.
            let Err(error) = outcome else {
                return Err("unplaced EOF arm unexpectedly ran".to_owned());
            };
            assert!(
                error.to_string().contains("self-encryption target 368"),
                "{error}"
            );
            assert_eq!(trace.len(), 79);
            assert_eq!(vm.memory_word(139), Ok(EOF_CONTROL));
            assert_eq!(vm.memory_word(368), Ok(7_174_341));
            assert_eq!(vm.output(), []);
            assert_eq!(vm.input_consumed(), 0);
            continue;
        }
        assert_eq!(
            outcome.map_err(|error| error.to_string())?,
            RunOutcome::Terminated {
                reason: Termination::HaltInstruction,
                steps: 81,
            },
            "input {input:?}"
        );
        assert_eq!(vm.memory_word(139), Ok(control(word)));
        assert_eq!(vm.input_consumed(), usize::from(!input.is_empty()));
        assert_eq!(branch.after.registers.code_pointer, 126);
        assert_eq!(trace.last().map(|step| step.decoded), Some(Some(b'v')));
        assert_eq!(vm.output(), b"}", "input {input:?}");
    }
    Ok(())
}

// A follow-on experiment reuses the unchanged four physical p writes and
// rotates their input-dependent result in real guest memory. It does not
// yet link either rotated word to executable branch targets.
fn rotated_discriminator_guest() -> Result<Vec<u8>, String> {
    let mut source = guest_source()?;
    set(&mut source, 78, b'*')?;
    set(&mut source, 79, current_profile().output_instruction())?;
    set(&mut source, 80, b'v')?;
    Ok(source)
}

#[test]
#[expect(
    clippy::integer_division,
    clippy::integer_division_remainder_used,
    reason = "independent exact trit-position lower bound"
)]
fn no_fourth_crazy_operand_places_both_controls_inside_the_source() {
    const TRITS: [[u32; 3]; 3] = [[1, 0, 0], [1, 0, 2], [2, 2, 1]];
    let third = |word| {
        scalar_crazy(
            THIRD_OPERAND,
            scalar_crazy(ROTATED_OPERAND, scalar_crazy(FIRST_OPERAND, word)),
        )
    };
    for byte in u8::MIN..=u8::MAX {
        assert_eq!((third(u32::from(byte)) / 243) % 3, 2);
    }
    assert_eq!((third(current_profile().eof_word()) / 243) % 3, 0);
    // Because each crazy trit is independent, every possible operand trit
    // produces a nonzero trit 5 for at least one input class. Therefore
    // one target is >= 243, beyond this source's 132 cells.
    for [zero, _, two] in TRITS {
        assert_ne!((two, zero), (0, 0));
    }
}

#[test]
#[expect(
    clippy::cognitive_complexity,
    clippy::panic_in_result_fn,
    reason = "bounded physical guest arithmetic and I/O trace witness"
)]
fn physical_rotation_moves_the_eof_bit_and_emits_distinct_guest_bytes()
-> Result<(), String> {
    let profile = current_profile();
    let source = rotated_discriminator_guest()?;
    let loaded = ProfileMachine::from_source(profile, &source, Vec::new())
        .map_err(|error| error.to_string())?;
    assert_eq!(source.get(130..), Some(b"-}".as_slice()));
    assert_eq!(loaded.memory_word(139), Ok(FOURTH_OPERAND));

    for input in [vec![], vec![0], vec![1], vec![0x80], vec![0xff]] {
        let word = input
            .first()
            .map_or_else(|| profile.eof_word(), |byte| u32::from(*byte));
        let before = control(word);
        let rotated = scalar_rotate(before);
        let mut vm = ProfileMachine::from_state(
            profile,
            loaded.memory().to_vec(),
            input.clone(),
            ProfileRegisters::default(),
        )
        .map_err(|error| error.to_string())?;
        let mut trace = Vec::new();
        let result = vm
            .run_traced(81, &mut |step| trace.push(*step))
            .map_err(|error| error.to_string())?;
        assert_eq!(result, RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 81,
        });
        let rotation = trace.get(78).ok_or("missing reached rotation")?;
        assert_eq!(rotation.decoded, Some(b'*'));
        assert_eq!(rotation.before.registers.code_pointer, 78);
        assert_eq!(rotation.before.registers.data_pointer, 139);
        assert_eq!(rotation.before.registers.accumulator, before);
        assert_eq!(
            rotation
                .memory_reads
                .data
                .map(|read| (read.address, read.value)),
            Some((139, before))
        );
        assert_eq!(rotation.after.registers.accumulator, rotated);
        assert_eq!(vm.memory_word(139), Ok(rotated));
        assert_eq!(trace.get(79).map(|step| step.decoded), Some(Some(b'<')));
        assert_eq!(trace.get(80).map(|step| step.decoded), Some(Some(b'v')));
        assert_eq!(vm.output(), &[
            u8::try_from(rotated & 255).unwrap_or_default()
        ]);
        assert_eq!(vm.input_consumed(), usize::from(!input.is_empty()));
    }
    assert_eq!(scalar_rotate(SUCCESS_CONTROL), 9_565_979);
    assert_eq!(scalar_rotate(EOF_CONTROL), 9_566_060);
    assert_eq!(scalar_rotate(SUCCESS_CONTROL) & 255, 27);
    assert_eq!(scalar_rotate(EOF_CONTROL) & 255, 108);
    Ok(())
}

#[test]
#[expect(
    clippy::integer_division,
    clippy::integer_division_remainder_used,
    reason = "exact ternary-position bound, separate from guest execution"
)]
fn two_post_rotation_crazy_words_have_short_scalar_targets() {
    const HIGH_PLACE: u32 = 4_782_969;
    const POST_ROTATION_OPERANDS: [u32; 2] = [HIGH_PLACE, 0];
    // The real rotation leaves both classes with trit 13 equal to zero.
    // Every first crazy operand maps input trit zero to one or two, so
    // one additional crazy cannot produce a short control word.
    for word in [SUCCESS_CONTROL, EOF_CONTROL] {
        let rotated = scalar_rotate(word);
        assert_eq!((rotated / 1_594_323) % 3, 0);
    }
    for operand_trit in 0..3u32 {
        let first = scalar_crazy(
            operand_trit * 1_594_323,
            scalar_rotate(SUCCESS_CONTROL),
        );
        assert_ne!((first / 1_594_323) % 3, 0);
    }
    let project = |word| {
        let rotated = scalar_rotate(control(word));
        let first = scalar_crazy(POST_ROTATION_OPERANDS[0], rotated);
        scalar_crazy(POST_ROTATION_OPERANDS[1], first)
    };
    for byte in u8::MIN..=u8::MAX {
        assert_eq!(project(u32::from(byte)), 40);
    }
    assert_eq!(project(current_profile().eof_word()), 121);
    // These are only hypothetical i controls: the actual source's C=41
    // is already encrypted by the time it reaches C=78. Both future
    // operands and valid executable arm entries need separate guest work.
    assert!(41 < u32::try_from(LENGTH).unwrap_or_default());
    assert!(122 < u32::try_from(LENGTH).unwrap_or_default());
}

// A reset through virgin M[148] avoids all input-dependent data words,
// including the earlier failure at M[135]. Move the fourth p away from C=69:
// its encrypted second-pass / had consumed an unrelated second input byte.
fn post_rotation_physical_branch_source() -> Result<Vec<u8>, String> {
    layout::build_signed_eof_branch_source(current_profile())
        .map_err(|error| format!("signed EOF source: {error:?}"))
}

#[test]
fn branch_candidate_requires_exact_current_profile() {
    assert_eq!(
        layout::build_signed_eof_branch_source(malbolge::historical_profile()),
        Err(layout::SignedEofBranchSourceError::UnsupportedProfile),
    );
}

fn independent_post_rotation_control(word: u32) -> u32 {
    let third = scalar_crazy(
        THIRD_OPERAND,
        scalar_crazy(ROTATED_OPERAND, scalar_crazy(FIRST_OPERAND, word)),
    );
    let rotated = scalar_rotate(scalar_crazy(125, third));
    let first = scalar_crazy(7_174_341, rotated);
    scalar_crazy(125, first)
}

#[test]
fn physical_post_rotation_scalar_oracle_covers_all_signed_inputs() {
    let profile = current_profile();
    for byte in u8::MIN..=u8::MAX {
        assert_eq!(independent_post_rotation_control(u32::from(byte)), 44);
    }
    assert_eq!(independent_post_rotation_control(profile.eof_word()), 125);
    assert_eq!(
        scalar_crazy(
            125,
            scalar_crazy(
                THIRD_OPERAND,
                scalar_crazy(ROTATED_OPERAND, scalar_crazy(FIRST_OPERAND, 0)),
            )
        ),
        134
    );
    assert_eq!(scalar_rotate(7_174_350) & 255, 154);
    assert_eq!(scalar_rotate(134) & 255, 30);
}

#[test]
#[expect(
    clippy::cognitive_complexity,
    clippy::too_many_lines,
    clippy::panic_in_result_fn,
    reason = "bounded exhaustive guest trace and one input instruction"
)]
fn all_257_signed_inputs_reach_both_arms_with_one_read() -> Result<(), String> {
    let profile = current_profile();
    let source = post_rotation_physical_branch_source()?;
    assert_eq!(source.len(), LENGTH);
    assert_eq!(source.get(130..), Some(b"-}".as_slice()));
    let loaded = ProfileMachine::from_source(profile, &source, vec![])
        .map_err(|error| error.to_string())?;
    for (address, operand) in [
        (137, 125),
        (140, 7_174_341),
        (143, 125),
        (145, 134),
        (148, 7_174_350),
        (7_174_351, 134),
        (7_174_356, 7_174_350),
        (7_174_357, 134),
    ] {
        assert_eq!(loaded.memory_word(address), Ok(operand));
    }

    // Every signed-input class actually executes in the profile VM.
    // Multi-byte vectors reject a hidden encrypted-code second read.
    let inputs = once(Vec::new())
        .chain((u8::MIN..=u8::MAX).map(|byte| vec![byte]))
        .chain([vec![0, 1, 2], vec![3, 4, 5]]);
    for input in inputs {
        let eof = input.is_empty();
        let input_word = input
            .first()
            .map_or_else(|| profile.eof_word(), |byte| u32::from(*byte));
        let mut vm = ProfileMachine::from_state(
            profile,
            loaded.memory().to_vec(),
            input.clone(),
            ProfileRegisters::default(),
        )
        .map_err(|error| error.to_string())?;
        let mut trace = vec![];
        let outcome = vm
            .run_traced(176, &mut |step| trace.push(*step))
            .map_err(|error| format!("input {input:?}: {error}"))?;
        let steps = if eof {
            119
        } else {
            175
        };
        assert_eq!(
            outcome,
            RunOutcome::Terminated {
                reason: Termination::HaltInstruction,
                steps,
            },
            "input {input:?}"
        );
        assert_eq!(trace.len(), steps);
        assert_eq!(
            vm.output(),
            if eof {
                &[30][..]
            } else {
                &[154][..]
            }
        );
        assert_eq!(vm.input_consumed(), input.len().min(1));
        let input_reads = trace
            .iter()
            .filter(|step| step.decoded == Some(profile.input_instruction()))
            .map(|step| step.before.registers.code_pointer)
            .collect::<Vec<_>>();
        assert_eq!(input_reads, &[53][..]);

        for (code, address, operand) in [
            (67, 137, 125),
            (
                76,
                137,
                if eof {
                    377
                } else {
                    134
                },
            ),
            (79, 140, 7_174_341),
            (82, 143, 125),
            (83, 144, 7_174_350),
            (84, 7_174_351, 134),
            (98, 148, 7_174_350),
            (104, 7_174_356, 7_174_350),
            (105, 7_174_357, 134),
        ] {
            let step = trace
                .iter()
                .find(|step| step.before.registers.code_pointer == code)
                .ok_or_else(|| {
                    format!("input {input:?}: unreached C={code}")
                })?;
            assert_eq!(
                step.memory_reads
                    .data
                    .map(|read| (read.address, read.value)),
                Some((address, operand)),
                "input {input:?}, C={code}"
            );
        }
        // The earlier counterexample at byte 0x03 is now an ordinary
        // real guest success path: no read of mutated M[135] is needed.
        assert!(!trace.iter().any(|step| {
            step.decoded == Some(b'j')
                && step
                    .memory_reads
                    .data
                    .is_some_and(|read| read.address == 135)
                && step.before.registers.code_pointer >= 83
                && step.before.registers.code_pointer <= 114
        }));
        let branch = trace
            .iter()
            .find(|step| step.before.registers.code_pointer == 114)
            .ok_or("missing physical conditional i")?;
        assert_eq!(branch.decoded, Some(b'i'));
        assert_eq!(branch.before.registers.data_pointer, 143);
        assert_eq!(
            branch
                .memory_reads
                .data
                .map(|read| (read.address, read.value)),
            Some((143, independent_post_rotation_control(input_word)))
        );
        assert_eq!(
            branch.after.registers.code_pointer,
            if eof {
                126
            } else {
                45
            }
        );
        assert_eq!(
            trace
                .last()
                .map(
                    |step| (step.before.registers.code_pointer, step.decoded,)
                ),
            Some(if eof {
                (129, Some(b'v'))
            } else {
                (104, Some(b'v'))
            })
        );
    }
    Ok(())
}

// The nonlinear layout admission is separate from executable source assembly.
// It uses an independent trit oracle for every arithmetic memory write, plus
// frozen code paths and I/O positions; no expected trace is copied from the VM.
fn independent_branch_writes(
    input_word: u32,
    eof: bool,
) -> Vec<layout::BoundedRevisitDataWrite> {
    let mut writes = Vec::new();
    let mut add = |step, address, before, after| {
        if before != after {
            writes.push(layout::BoundedRevisitDataWrite {
                step,
                address,
                before,
                after,
            });
        }
    };
    let mut rotated_seed = 134;
    for round in 0u32..12 {
        let after = scalar_rotate(rotated_seed);
        add(
            17u32.saturating_add(round.saturating_mul(3)),
            135,
            rotated_seed,
            after,
        );
        rotated_seed = after;
    }
    assert_eq!(rotated_seed, ROTATED_OPERAND);
    let first = scalar_crazy(FIRST_OPERAND, input_word);
    let second = scalar_crazy(rotated_seed, first);
    let third = scalar_crazy(THIRD_OPERAND, second);
    let fourth = scalar_crazy(125, third);
    let rotated = scalar_rotate(fourth);
    let fifth = scalar_crazy(FIRST_OPERAND, rotated);
    let sixth = scalar_crazy(125, fifth);
    add(64, 134, FIRST_OPERAND, first);
    add(65, 135, rotated_seed, second);
    add(66, 136, THIRD_OPERAND, third);
    add(67, 137, 125, fourth);
    add(76, 137, fourth, rotated);
    add(79, 140, FIRST_OPERAND, fifth);
    add(82, 143, 125, sixth);
    add(104, 7_174_356, THIRD_OPERAND, scalar_rotate(THIRD_OPERAND));
    if eof {
        add(116, 145, 134, scalar_rotate(134));
    } else {
        let revisited_rotated = scalar_rotate(THIRD_OPERAND);
        let revisited_crazy = scalar_crazy(THIRD_OPERAND, revisited_rotated);
        add(126, 7_174_344, THIRD_OPERAND, revisited_rotated);
        add(130, 7_174_348, THIRD_OPERAND, revisited_crazy);
        add(167, 7_174_385, 125, scalar_crazy(125, revisited_crazy));
    }
    writes
}

#[test]
#[expect(
    clippy::cognitive_complexity,
    clippy::too_many_lines,
    clippy::panic_in_result_fn,
    reason = "independent arithmetic and path oracle for guest"
)]
fn assembled_eof_branch_passes_independent_nonlinear_admission()
-> Result<(), String> {
    let profile = current_profile();
    let source = post_rotation_physical_branch_source()?;
    let identity = layout::LinearProfileIdentity {
        id: profile.id(),
        fingerprint: profile.fingerprint(),
    };
    for input in [vec![], vec![0], vec![3, 4, 5], vec![0xff]] {
        let eof = input.is_empty();
        let input_event = input
            .first()
            .map_or(TraceInput::EndOfInput, |byte| TraceInput::Byte(*byte));
        let output_byte = if eof {
            30
        } else {
            154
        };
        let output = [output_byte];
        let input_events = [input_event];
        let io_events = [
            layout::BoundedRevisitIoEvent {
                step: 53,
                effect: layout::BoundedRevisitIoEffect::Input(input_event),
            },
            layout::BoundedRevisitIoEvent {
                step: if eof {
                    117
                } else {
                    127
                },
                effect: layout::BoundedRevisitIoEffect::Output(output_byte),
            },
        ];
        let mut path = (0..=114u32).collect::<Vec<_>>();
        if eof {
            path.extend(126..=129);
        } else {
            path.extend(45..=104);
        }
        let input_word = input
            .first()
            .map_or_else(|| profile.eof_word(), |byte| u32::from(*byte));
        let data_writes = independent_branch_writes(input_word, eof);
        let admitted = layout::admit_bounded_guest_path(
            profile,
            &source,
            identity,
            layout::BoundedRevisitExpectation {
                input: &input,
                code_positions: &path,
                output: &output,
                input_consumed: usize::from(!eof),
                input_events: &input_events,
                io_events: &io_events,
                data_writes: &data_writes,
            },
        )
        .map_err(|error| {
            format!("independent admission for {input:?}: {error:?}")
        })?;
        assert_eq!(admitted.code_positions(), path);
        assert_eq!(admitted.data_writes(), data_writes);
        assert_eq!(admitted.io_events(), io_events);
        assert_eq!(admitted.input_consumed(), usize::from(!eof));
        assert_eq!(admitted.output(), output);
        if eof {
            let forged_output = [output_byte ^ 1];
            assert_eq!(
                layout::admit_bounded_guest_path(
                    profile,
                    &source,
                    identity,
                    layout::BoundedRevisitExpectation {
                        input: &input,
                        code_positions: &path,
                        output: &forged_output,
                        input_consumed: 0,
                        input_events: &input_events,
                        io_events: &io_events,
                        data_writes: &data_writes,
                    },
                ),
                Err(layout::BoundedRevisitError::OutputMismatch),
            );
            let mut forged_path = path.clone();
            if let Some(destination) = forged_path.last_mut() {
                *destination = 128;
            }
            assert_eq!(
                layout::admit_bounded_guest_path(
                    profile,
                    &source,
                    identity,
                    layout::BoundedRevisitExpectation {
                        input: &input,
                        code_positions: &forged_path,
                        output: &output,
                        input_consumed: 0,
                        input_events: &input_events,
                        io_events: &io_events,
                        data_writes: &data_writes,
                    },
                ),
                Err(layout::BoundedRevisitError::PathMismatch),
            );
            assert_eq!(
                layout::admit_bounded_revisit_layout(
                    profile,
                    &source,
                    identity,
                    layout::BoundedRevisitExpectation {
                        input: &input,
                        code_positions: &path,
                        output: &output,
                        input_consumed: 0,
                        input_events: &input_events,
                        io_events: &io_events,
                        data_writes: &data_writes,
                    },
                ),
                Err(layout::BoundedRevisitError::NotRevisiting),
            );
        }
    }
    Ok(())
}

#[test]
#[expect(
    clippy::cognitive_complexity,
    clippy::too_many_lines,
    clippy::panic_in_result_fn,
    reason = "finite source-bound full-path and tamper matrix"
)]
fn source_bound_mixed_eof_and_byte_batch_requires_exact_path_oracles()
-> Result<(), String> {
    use layout::{
        BoundedGuestDataRegion as Region,
        BoundedGuestRegionsError as RegionsError,
    };
    const CHECKSUM_STATE_WORDS: u32 = 43;

    let profile = current_profile();
    let source = post_rotation_physical_branch_source()?;
    let identity = layout::LinearProfileIdentity {
        fingerprint: profile.fingerprint(),
        id: profile.id(),
    };
    let cases = [vec![], vec![0], vec![255], vec![3, 4, 5], vec![128]]
        .into_iter()
        .map(OwnedBranchPath::new)
        .collect::<Vec<_>>();
    let expected = cases
        .iter()
        .map(OwnedBranchPath::expectation)
        .collect::<Vec<_>>();
    let [eof, nul, high, mixed, _other] = expected.as_slice() else {
        return Err(String::from("wrong test vector count"));
    };
    let [_empty_case, _nul_case, high_case, mixed_case, _other_case] =
        cases.as_slice()
    else {
        return Err(String::from("wrong source case count"));
    };
    assert_eq!(
        layout::admit_bounded_revisit_batch(
            profile, &source, identity, &expected
        ),
        Err(layout::BoundedRevisitError::NotRevisiting),
    );
    let admitted = layout::admit_bounded_guest_path_batch(
        profile, &source, identity, &expected,
    )
    .map_err(|error| format!("mixed guest batch: {error:?}"))?;
    assert_eq!(admitted.len(), cases.len());
    // Declare the physical helper's entire scratch footprint *before*
    // selecting source-C state, including reserved but unvisited cells.
    let helper_regions = [
        Region {
            end_exclusive: 146,
            start: 132,
        },
        Region {
            end_exclusive: 7_174_386,
            start: 7_174_344,
        },
    ];
    // The original source-locked CFG independently reserves a 43-word
    // SSA/phi frame. Search around the actual helper, not invented free space.
    let state_frame = layout::place_bounded_guest_state_frame(
        &admitted,
        &helper_regions,
        CHECKSUM_STATE_WORDS,
    )
    .map_err(|error| format!("guest frame search: {error:?}"))?;
    assert_eq!(
        state_frame.end_exclusive - state_frame.start,
        CHECKSUM_STATE_WORDS
    );
    assert!(state_frame.start >= 132);
    assert!(state_frame.end_exclusive <= profile.memory_words());
    assert!(helper_regions.iter().all(|scratch| {
        state_frame.end_exclusive <= scratch.start
            || scratch.end_exclusive <= state_frame.start
    }));
    assert_eq!(
        layout::place_bounded_guest_state_frame(
            &admitted.iter().rev().cloned().collect::<Vec<_>>(),
            &helper_regions,
            CHECKSUM_STATE_WORDS
        ),
        Ok(state_frame),
    );
    assert_eq!(
        layout::place_bounded_guest_state_frame(&admitted, &helper_regions, 0),
        Err(RegionsError::InvalidRegions),
    );
    assert_eq!(
        layout::place_bounded_guest_state_frame(
            &admitted,
            &helper_regions,
            layout::MAX_GUEST_RESERVED_WORDS + 1
        ),
        Err(RegionsError::InvalidRegions),
    );
    // Every smaller candidate must collide with a helper access OR a
    // declared scratch word, even one that this finite batch never touched.
    for base in 132..state_frame.start {
        let candidate = Region {
            end_exclusive: base + CHECKSUM_STATE_WORDS,
            start: base,
        };
        assert!(
            admitted.iter().any(|path| {
                layout::verify_bounded_guest_state_isolation(path, &[candidate])
                    .is_err()
            }) || helper_regions.iter().any(|scratch| {
                candidate.start < scratch.end_exclusive
                    && scratch.start < candidate.end_exclusive
            })
        );
    }
    // An otherwise untouched, declared helper-owned word must never be
    // repurposed as a future C local merely because the selected inputs
    // happened not to visit it. The reservation shifts deterministically.
    let supplementary = [
        helper_regions[0],
        Region {
            end_exclusive: state_frame.end_exclusive,
            start: 146,
        },
        helper_regions[1],
    ];
    let shifted = layout::place_bounded_guest_state_frame(
        &admitted,
        &supplementary,
        CHECKSUM_STATE_WORDS,
    )
    .map_err(|error| format!("supplementary scratch: {error:?}"))?;
    assert!(shifted.start >= state_frame.end_exclusive);
    // Helper scratch alone fits the finite ceiling, but adding the C frame
    // crosses it. The two banks cannot spend the same memory budget twice.
    let near_limit_scratch = [
        helper_regions[0],
        Region {
            end_exclusive: 4170,
            start: 146,
        },
        helper_regions[1],
    ];
    assert_eq!(
        layout::place_bounded_guest_state_frame(
            &admitted,
            &near_limit_scratch,
            CHECKSUM_STATE_WORDS,
        ),
        Err(RegionsError::InvalidRegions),
    );
    assert_eq!(
        layout::place_bounded_guest_state_frame(
            &admitted,
            &helper_regions[..1],
            CHECKSUM_STATE_WORDS,
        ),
        Err(RegionsError::UnreservedWrite),
    );
    assert_eq!(
        layout::place_bounded_guest_state_frame(
            &admitted,
            &[helper_regions[1], helper_regions[0]],
            CHECKSUM_STATE_WORDS,
        ),
        Err(RegionsError::InvalidRegions),
    );
    // No physical C-state initialization, guest arithmetic, or phi copy is
    // linked just because this strict frame/scratch reservation succeeds.
    for path in &admitted {
        assert_eq!(
            path.mutation_targets().len(),
            12 + 6
                + 1
                + 1
                + if path.input_consumed() == 0 {
                    1
                } else {
                    3
                },
        );
        assert_eq!(
            layout::verify_bounded_guest_data_regions(path, &helper_regions),
            Ok(())
        );
        // The 43-word checksum SSA frame is a separate future writable bank.
        // Prove the *physical* helper cannot read, write or execute that bank.
        let checksum_frame = Region {
            start: 4096,
            end_exclusive: 4139,
        };
        assert_eq!(
            layout::verify_bounded_guest_state_isolation(path, &[
                checksum_frame
            ]),
            Ok(())
        );
        // M[148] is read by the real pointer-reset sequence, but never
        // mutated. Checking writes alone would wrongly admit this frame.
        assert!(path.data_read_positions().contains(&Some(148)));
        assert!(!path.mutation_targets().contains(&148));
        assert_eq!(
            layout::verify_bounded_guest_state_isolation(path, &[Region {
                start: 148,
                end_exclusive: 191,
            }]),
            Err(RegionsError::StateDataAccessCollision),
        );
        assert_eq!(
            layout::verify_bounded_guest_state_isolation(path, &[Region {
                start: 139,
                end_exclusive: 182,
            }]),
            Err(RegionsError::StateDataAccessCollision),
        );
        assert_eq!(
            layout::verify_bounded_guest_data_regions(
                path,
                &helper_regions[..1]
            ),
            Err(RegionsError::UnreservedWrite),
        );
        assert_eq!(
            layout::verify_bounded_guest_data_regions(path, &[
                Region {
                    start: 0,
                    end_exclusive: 132
                },
                helper_regions[0],
            ]),
            Err(RegionsError::InvalidRegions),
        );
        assert_eq!(
            layout::verify_bounded_guest_data_regions(path, &[
                helper_regions[0],
                Region {
                    start: 145,
                    end_exclusive: 148
                },
            ]),
            Err(RegionsError::InvalidRegions),
        );
        assert_eq!(
            layout::verify_bounded_guest_data_regions(path, &[
                helper_regions[0],
                Region {
                    start: profile.memory_words() - 1,
                    end_exclusive: profile.memory_words() + 1
                },
            ]),
            Err(RegionsError::InvalidRegions),
        );
        assert_eq!(
            layout::verify_bounded_guest_data_regions(path, &[
                helper_regions[0],
                Region {
                    start: helper_regions[1].start,
                    end_exclusive: helper_regions[1].start
                },
            ]),
            Err(RegionsError::InvalidRegions),
        );
        assert_eq!(
            layout::verify_bounded_guest_data_regions(path, &[Region {
                start: 132,
                end_exclusive: 132 + layout::MAX_GUEST_RESERVED_WORDS + 1
            },]),
            Err(RegionsError::InvalidRegions),
        );
        assert_eq!(
            layout::verify_bounded_guest_data_regions(path, &[
                helper_regions[1],
                helper_regions[0],
            ]),
            Err(RegionsError::InvalidRegions),
        );
        let over_budget =
            [helper_regions[0]; layout::MAX_GUEST_DATA_REGIONS + 1];
        assert_eq!(
            layout::verify_bounded_guest_data_regions(path, &over_budget),
            Err(RegionsError::InvalidRegions),
        );
    }
    for (actual, case) in admitted.iter().zip(&cases) {
        assert_eq!(actual.code_positions(), case.path);
        assert_eq!(actual.io_events(), case.io_events);
        assert_eq!(actual.data_writes(), case.writes);
        assert_eq!(actual.output(), case.output);
    }
    assert_eq!(
        layout::admit_bounded_guest_path_batch(profile, &source, identity, &[
            *eof, *eof
        ]),
        Err(layout::BoundedRevisitError::InvalidBatch),
    );
    let forged_output = [31];
    let forged = layout::BoundedRevisitExpectation {
        output: &forged_output,
        ..*eof
    };
    assert_eq!(
        layout::admit_bounded_guest_path_batch(profile, &source, identity, &[
            forged, *nul
        ]),
        Err(layout::BoundedRevisitError::OutputMismatch),
    );
    let mut forged_path = high_case.path.clone();
    *forged_path.last_mut().ok_or("missing byte path")? = 103;
    let wrong_path = layout::BoundedRevisitExpectation {
        code_positions: &forged_path,
        ..*high
    };
    assert_eq!(
        layout::admit_bounded_guest_path_batch(profile, &source, identity, &[
            *eof, wrong_path
        ]),
        Err(layout::BoundedRevisitError::PathMismatch),
    );
    let mut forged_writes = mixed_case.writes.clone();
    let first = forged_writes.first_mut().ok_or("missing guest write")?;
    first.after ^= 1;
    let wrong_data = layout::BoundedRevisitExpectation {
        data_writes: &forged_writes,
        ..*mixed
    };
    assert_eq!(
        layout::admit_bounded_guest_path_batch(profile, &source, identity, &[
            *eof, wrong_data
        ]),
        Err(layout::BoundedRevisitError::DataWritesMismatch),
    );
    assert_eq!(
        layout::admit_bounded_guest_path_batch(profile, &source, identity, &[]),
        Err(layout::BoundedRevisitError::InvalidBatch),
    );
    assert_eq!(
        layout::admit_bounded_guest_path_batch(
            profile,
            &source,
            identity,
            expected.get(..1).ok_or("missing first path")?
        ),
        Err(layout::BoundedRevisitError::InvalidBatch),
    );
    let over_budget = vec![*eof; layout::MAX_REVISIT_CASES + 1];
    assert_eq!(
        layout::admit_bounded_guest_path_batch(
            profile,
            &source,
            identity,
            &over_budget
        ),
        Err(layout::BoundedRevisitError::InvalidBatch),
    );
    Ok(())
}
