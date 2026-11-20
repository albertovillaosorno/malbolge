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
//   - Normative guest path/effect verification of a physical C23 operand pair.
// - Must-Not:
//   - Claim the unrotated pair converts signed EOF or compiles mutable C.
// - Allows:
//   - Inputs: all 257 signed guest input classes and an unread-suffix case.
//   - Outputs: actual VM p/p writes and independent 15-trit output oracles.
//   - Side effects: isolated VM traces within 169 steps and bounded memory.
// - Split-When:
//   - The complete C23 converter admits nine actual preparatory rotations.
// - Merge-When:
//   - General physical operand synthesis proves signed byte I/O.
// - Summary:
//   - Loader-valid two-crazy guest precursor and real negative C23 evidence.

//! Physical p/p source placement, not executable C23 byte normalization.

#[path = "../src/compiler/malbolge-layout/composition/lib.rs"]
pub mod layout;

use std::iter::once;

use malbolge::{
    ProfileMachine, ProfileRegisters, RunOutcome, Termination, TraceInput,
    current_profile, decode_profile_instruction, historical_profile,
    profile_rotate,
};

const FIRST_ADDRESS: u32 = 283;
const SECOND_ADDRESS: u32 = 284;
const INITIAL_FIRST: u32 = 7_174_404;
const INITIAL_SECOND: u32 = 121;

// Independent digit table instead of calling the production p implementation.
#[expect(
    clippy::arithmetic_side_effects,
    clippy::integer_division_remainder_used,
    reason = "independent 15-trit positional guest arithmetic oracle"
)]
fn scalar_crazy(mut data: u32, mut accumulator: u32) -> u32 {
    let mut result = 0;
    let mut place = 1;
    for _ in 0usize..15 {
        let value = match (data % 3, accumulator % 3) {
            (0 | 1, 0) | (2, 2) => 1,
            (1, 2) | (2, 0 | 1) => 2,
            _ => 0,
        };
        result += value * place;
        data /= 3;
        accumulator /= 3;
        place *= 3;
    }
    result
}

#[test]
#[expect(
    clippy::cognitive_complexity,
    clippy::panic_in_result_fn,
    reason = "bounded loader geometry requires explicit regression assertions"
)]
fn graphical_loader_tail_and_unrealized_rotation_are_distinct()
-> Result<(), String> {
    let profile = current_profile();
    let source = layout::build_c23_operand_probe_source(profile)
        .map_err(|error| format!("{error:?}"))?;
    assert_eq!(source.len(), 279);
    assert_eq!(source.get(277..), Some(b"Iy".as_slice()));
    assert_eq!(
        layout::build_c23_operand_probe_source(historical_profile()),
        Err(layout::C23OperandProbeSourceError::UnsupportedProfile),
    );
    let loaded = ProfileMachine::from_source(profile, &source, vec![])
        .map_err(|error| error.to_string())?;
    let mut previous = u32::from(b'I');
    let mut latest = u32::from(b'y');
    for address in 279..=SECOND_ADDRESS {
        let next = scalar_crazy(previous, latest);
        if address == FIRST_ADDRESS {
            assert_eq!(next, INITIAL_FIRST);
        }
        if address == SECOND_ADDRESS {
            assert_eq!(next, INITIAL_SECOND);
        }
        previous = latest;
        latest = next;
    }
    assert_eq!(loaded.memory_word(FIRST_ADDRESS), Ok(INITIAL_FIRST));
    assert_eq!(loaded.memory_word(SECOND_ADDRESS), Ok(INITIAL_SECOND));
    // The original mathematical converter needs NINE *physical* writes.
    assert_eq!(
        (0usize..9).fold(INITIAL_FIRST, |word, _| {
            profile_rotate(word, profile.word_modulus())
        }),
        7_138_732
    );
    assert_ne!(INITIAL_FIRST, 7_138_732);
    Ok(())
}

#[test]
#[expect(
    clippy::cognitive_complexity,
    clippy::too_many_lines,
    clippy::panic_in_result_fn,
    clippy::integer_division_remainder_used,
    reason = "all signed inputs checked against independent memory effects"
)]
fn real_two_crazy_writes_execute_but_do_not_convert_c23() -> Result<(), String>
{
    let profile = current_profile();
    let source = layout::build_c23_operand_probe_source(profile)
        .map_err(|error| format!("{error:?}"))?;
    let loaded = ProfileMachine::from_source(profile, &source, vec![])
        .map_err(|error| error.to_string())?;
    let mut wrong_c23 = 0usize;
    for input in once(Vec::new())
        .chain((u8::MIN..=u8::MAX).map(|byte| vec![byte]))
        .chain(once(vec![42, 99, 11]))
    {
        let first_input = input.first().copied();
        let raw_word =
            first_input.map_or_else(|| profile.eof_word(), u32::from);
        let intermediate = scalar_crazy(INITIAL_FIRST, raw_word);
        let result_word = scalar_crazy(INITIAL_SECOND, intermediate);
        let emitted = u8::try_from(result_word % 256)
            .map_err(|error| error.to_string())?;
        let mut vm = ProfileMachine::from_state(
            profile,
            loaded.memory().to_vec(),
            input.clone(),
            ProfileRegisters::default(),
        )
        .map_err(|error| error.to_string())?;
        let mut trace = Vec::new();
        let result = vm
            .run_traced(169, &mut |step| trace.push(*step))
            .map_err(|error| error.to_string())?;
        assert_eq!(result, RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 169,
        });
        assert_eq!(trace.len(), 169);
        let input_step = trace.get(164).ok_or("missing signed input")?;
        assert_eq!(input_step.before.registers.code_pointer, 164);
        assert_eq!(input_step.before.registers.data_pointer, 282);
        assert_eq!(input_step.decoded, Some(profile.input_instruction()));
        assert_eq!(
            input_step.input,
            Some(first_input.map_or(TraceInput::EndOfInput, TraceInput::Byte))
        );
        for (step, address, before, after) in [
            (165, FIRST_ADDRESS, INITIAL_FIRST, intermediate),
            (166, SECOND_ADDRESS, INITIAL_SECOND, result_word),
        ] {
            let write = trace.get(step).ok_or("missing physical crazy step")?;
            assert_eq!(write.decoded, Some(b'p'));
            assert_eq!(write.before.registers.data_pointer, address);
            assert_eq!(
                write
                    .memory_reads
                    .data
                    .map(|read| (read.address, read.value)),
                Some((address, before))
            );
            assert_eq!(
                write.memory_delta.data.map(|delta| {
                    (delta.address, delta.before, delta.after)
                }),
                (before != after).then_some((address, before, after))
            );
            assert_eq!(write.after.registers.accumulator, after);
            assert_eq!(vm.memory_word(address), Ok(after));
        }
        assert_eq!(trace.get(167).and_then(|step| step.output), Some(emitted));
        assert_eq!(vm.output(), &[emitted]);
        assert_eq!(vm.input_consumed(), usize::from(first_input.is_some()));
        let c23_byte = first_input.unwrap_or(255);
        wrong_c23 += usize::from(emitted != c23_byte);
        if input.is_empty() {
            assert_eq!(emitted, 85);
            assert_ne!(emitted, 255);
        }
    }
    assert!(wrong_c23 > 0, "unrotated pair must not pass C23 conversion");
    Ok(())
}

// Independent cyclic digit rotation, with the target width frozen to N15.
#[expect(
    clippy::arithmetic_side_effects,
    clippy::integer_division,
    clippy::integer_division_remainder_used,
    reason = "independent fixed-width 15-trit arithmetic oracle"
)]
const fn independent_rotate(word: u32) -> u32 {
    word / 3 + (word % 3) * (14_348_907 / 3)
}

// The original C23 loader operand is physically prepared for *five*
// rotations, then both input-dependent crazy operations execute. This
// preserves genuine input provenance, unlike host-emitted byte fixtures.
// The output still differs from C23, so the complete checksum stays blocked.
#[test]
#[expect(
    clippy::cognitive_complexity,
    clippy::too_many_lines,
    clippy::panic_in_result_fn,
    clippy::integer_division_remainder_used,
    reason = "257 complete physical paths with independent trit arithmetic"
)]
fn five_real_rotations_feed_two_live_signed_crazy_writes() -> Result<(), String>
{
    const ROTATED_FIRST: u32 = 4_281_052;
    let profile = current_profile();
    let source = layout::build_c23_five_rotated_signed_crazy_source(profile)
        .map_err(|error| format!("{error:?}"))?;
    assert_eq!(source.len(), 91);
    assert_eq!(source.get(89..), Some(b"Iy".as_slice()));
    let rejected = layout::build_c23_five_rotated_signed_crazy_source(
        historical_profile(),
    );
    assert_eq!(
        rejected,
        Err(layout::C23OperandProbeSourceError::UnsupportedProfile),
    );
    let loaded = ProfileMachine::from_source(profile, &source, vec![])
        .map_err(|error| error.to_string())?;
    assert_eq!(loaded.memory_word(95), Ok(INITIAL_FIRST));
    assert_eq!(loaded.memory_word(96), Ok(INITIAL_SECOND));
    assert_eq!(loaded.memory_word(67), Ok(67));
    assert_eq!(loaded.memory_word(68), Ok(94));
    assert_eq!(
        (0usize..5).fold(INITIAL_FIRST, |word, _| independent_rotate(word)),
        ROTATED_FIRST,
    );
    for input in once(Vec::new())
        .chain((u8::MIN..=u8::MAX).map(|byte| vec![byte]))
        .chain(once(vec![17, 99, 31]))
    {
        let first_input = input.first().copied();
        let raw = first_input.map_or_else(|| profile.eof_word(), u32::from);
        let first_crazy = scalar_crazy(ROTATED_FIRST, raw);
        let second_crazy = scalar_crazy(INITIAL_SECOND, first_crazy);
        let expected = u8::try_from(second_crazy % 256)
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
            .run_traced(48, &mut |step| trace.push(*step))
            .map_err(|error| error.to_string())?;
        assert_eq!(outcome, RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 48,
        });
        assert_eq!(trace.len(), 48);
        let mut word = INITIAL_FIRST;
        for position in [12, 18, 24, 30, 36] {
            let operation =
                trace.get(position).ok_or("missing guest operation")?;
            assert_eq!(operation.decoded, Some(b'*'));
            assert_eq!(operation.before.registers.data_pointer, 95);
            assert_eq!(
                operation.memory_reads.data.map(|read| read.value),
                Some(word),
            );
            word = independent_rotate(word);
            assert_eq!(operation.after.registers.accumulator, word);
        }
        assert_eq!(word, ROTATED_FIRST);
        let input_step = trace.get(37).ok_or("missing guest input")?;
        assert_eq!(input_step.decoded, Some(profile.input_instruction()));
        assert_eq!(input_step.before.registers.data_pointer, 96);
        assert_eq!(
            input_step.input,
            Some(first_input.map_or(TraceInput::EndOfInput, TraceInput::Byte)),
        );
        for (position, address, value) in [
            (39, 98, 157),
            (40, 158, 36),
            (41, 37, 66),
            (42, 67, 67),
            (43, 68, 94),
        ] {
            let reset = trace.get(position).ok_or("missing guest operation")?;
            assert_eq!(reset.decoded, Some(b'j'));
            assert_eq!(reset.before.registers.data_pointer, address);
            assert_eq!(
                reset.memory_reads.data.map(|read| read.value),
                Some(value),
            );
        }
        for (position, address, before, after) in [
            (44, 95, ROTATED_FIRST, first_crazy),
            (45, 96, INITIAL_SECOND, second_crazy),
        ] {
            let step = trace.get(position).ok_or("missing guest operation")?;
            assert_eq!(step.decoded, Some(b'p'));
            assert_eq!(step.before.registers.data_pointer, address);
            assert_eq!(
                step.memory_reads.data.map(|read| read.value),
                Some(before),
            );
            assert_eq!(step.after.registers.accumulator, after);
            assert_eq!(
                step.memory_delta.data.map(|delta| {
                    (delta.address, delta.before, delta.after)
                }),
                (before != after).then_some((address, before, after)),
            );
            assert_eq!(vm.memory_word(address), Ok(after));
        }
        assert_eq!(trace.get(46).and_then(|step| step.output), Some(expected));
        assert_eq!(vm.output(), &[expected]);
        assert_eq!(vm.input_consumed(), usize::from(first_input.is_some()));
        if let Some(byte) = first_input {
            assert_eq!(expected, byte, "all 256 successful bytes must echo");
        } else {
            assert_eq!(expected, 0x0f, "EOF still differs from C23 0xff");
        }
    }
    Ok(())
}

// All nine correct Iy rotations, followed by another real signed read and
// two physical crazy writes, reveal a code-encryption pointer trap. The
// second read is genuine but the operands are *not* the C23 converter pair.
#[test]
#[expect(
    clippy::cognitive_complexity,
    clippy::too_many_lines,
    clippy::panic_in_result_fn,
    clippy::integer_division_remainder_used,
    reason = "257 independent two-input, 79-step physical guest paths"
)]
fn nine_rotations_feed_crazy_after_second_input_but_not_c23()
-> Result<(), String> {
    const ROTATED_FIRST: u32 = 7_138_732;
    const REACHED_FIRST: u32 = 104;
    const REACHED_SECOND: u32 = 104;
    let profile = current_profile();
    let source =
        layout::build_c23_nine_rotated_second_input_crazy_probe_source(profile)
            .map_err(|error| format!("{error:?}"))?;
    assert_eq!(source.len(), 91);
    assert_eq!(source.get(89..), Some(b"Iy".as_slice()));
    assert_eq!(
        [
            source.get(37).copied(),
            source.get(67).copied(),
            source.get(68).copied(),
        ],
        [Some(80), Some(67), Some(94)],
    );
    assert_eq!(
        layout::build_c23_nine_rotated_second_input_crazy_probe_source(
            historical_profile(),
        ),
        Err(layout::C23OperandProbeSourceError::UnsupportedProfile),
    );
    let loaded = ProfileMachine::from_source(profile, &source, vec![])
        .map_err(|error| error.to_string())?;
    assert_eq!(loaded.memory_word(95), Ok(INITIAL_FIRST));
    assert_eq!(loaded.memory_word(96), Ok(INITIAL_SECOND));
    let mut c23_mismatches = 0usize;
    for input in once(Vec::new())
        .chain(once(vec![0x5a]))
        .chain((u8::MIN..=u8::MAX).map(|second| vec![0x5a, second]))
        .chain(once(vec![0x5a, 0xfe, 0x07, 0x09]))
    {
        let first = input.first().copied();
        let second = input.get(1).copied();
        let raw = second.map_or_else(|| profile.eof_word(), u32::from);
        let first_crazy = scalar_crazy(REACHED_FIRST, raw);
        let second_crazy = scalar_crazy(REACHED_SECOND, first_crazy);
        let output = u8::try_from(second_crazy % 256)
            .map_err(|error| error.to_string())?;
        c23_mismatches += usize::from(output != second.unwrap_or(255));
        let mut vm = ProfileMachine::from_state(
            profile,
            loaded.memory().to_vec(),
            input,
            ProfileRegisters::default(),
        )
        .map_err(|error| error.to_string())?;
        let mut trace = Vec::new();
        let outcome = vm
            .run_traced(79, &mut |step| trace.push(*step))
            .map_err(|error| error.to_string())?;
        assert_eq!(outcome, RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 79,
        });
        assert_eq!(trace.len(), 79);
        let mut rotated = INITIAL_FIRST;
        for position in [12usize, 18, 24, 30, 36, 44, 51, 58, 65] {
            let step = trace.get(position).ok_or("missing guest operation")?;
            assert_eq!(step.decoded, Some(b'*'));
            assert_eq!(step.before.registers.data_pointer, 95);
            assert_eq!(
                step.memory_reads.data.map(|read| read.value),
                Some(rotated),
            );
            rotated = independent_rotate(rotated);
            assert_eq!(step.after.registers.accumulator, rotated);
        }
        assert_eq!(rotated, ROTATED_FIRST);
        for (position, expected_input) in [(37usize, first), (73, second)] {
            let step = trace.get(position).ok_or("missing guest operation")?;
            assert_eq!(step.decoded, Some(profile.input_instruction()));
            assert_eq!(
                step.input,
                Some(
                    expected_input
                        .map_or(TraceInput::EndOfInput, TraceInput::Byte,)
                ),
            );
        }
        for (position, address, value) in [
            (66usize, 96u32, 121u32),
            (67, 122, 157),
            (70, 160, 157),
            (71, 158, 36),
            (72, 37, 66),
            (74, 68, 57),
        ] {
            let step = trace.get(position).ok_or("missing guest operation")?;
            assert_eq!(step.decoded, Some(b'j'));
            assert_eq!(step.before.registers.data_pointer, address);
            assert_eq!(
                step.memory_reads.data.map(|read| read.value),
                Some(value)
            );
        }
        assert_eq!(trace.get(68).and_then(|step| step.decoded), Some(b'o'));
        assert_eq!(trace.get(69).and_then(|step| step.decoded), Some(b'o'));
        for (position, address, before, after) in [
            (75usize, 58u32, REACHED_FIRST, first_crazy),
            (76, 59, REACHED_SECOND, second_crazy),
        ] {
            let step = trace.get(position).ok_or("missing guest operation")?;
            assert_eq!(step.decoded, Some(b'p'));
            assert_eq!(step.before.registers.data_pointer, address);
            assert_eq!(
                step.memory_reads.data.map(|read| read.value),
                Some(before)
            );
            assert_eq!(step.after.registers.accumulator, after);
            assert_eq!(vm.memory_word(address), Ok(after));
        }
        assert_eq!(trace.get(77).and_then(|step| step.output), Some(output));
        assert_eq!(vm.output(), &[output]);
        assert_eq!(vm.memory_word(95), Ok(ROTATED_FIRST));
        assert_eq!(vm.memory_word(96), Ok(INITIAL_SECOND));
        assert_eq!(
            vm.input_consumed(),
            usize::from(first.is_some()) + usize::from(second.is_some()),
        );
    }
    assert!(c23_mismatches > 0, "encrypted M68 does not reach C23 data");
    Ok(())
}

// Physically correct C23 signed conversion, still blocked at output linkage.
// The first input is consumed at C37 before the final four rotations.
// The second input drives p/p on the prepared M95/M96 pair at C79/C80;
// M81=94 remains a mandatory halt cell, so no guest output is published.
#[test]
#[expect(
    clippy::cognitive_complexity,
    clippy::too_many_lines,
    clippy::panic_in_result_fn,
    clippy::integer_division_remainder_used,
    reason = "257 independent signed-input conversion paths in the real VM"
)]
fn nine_real_rotations_convert_second_signed_input_without_output()
-> Result<(), String> {
    let profile = current_profile();
    let source =
        layout::build_c23_nine_rotated_signed_conversion_without_output_source(
            profile,
        )
        .map_err(|error| format!("{error:?}"))?;
    assert_eq!(source.len(), 91);
    assert_eq!(source.get(89..), Some(b"Iy".as_slice()));
    assert_eq!(source.get(81), Some(&94));
    assert_eq!(source.get(87), Some(&69));
    assert_eq!(
        layout::build_c23_nine_rotated_signed_conversion_without_output_source(
            historical_profile(),
        ),
        Err(layout::C23OperandProbeSourceError::UnsupportedProfile),
    );
    let loaded = ProfileMachine::from_source(profile, &source, vec![])
        .map_err(|error| error.to_string())?;
    assert_eq!(loaded.memory_word(95), Ok(INITIAL_FIRST));
    assert_eq!(loaded.memory_word(96), Ok(INITIAL_SECOND));
    let mut cases: usize = 0;
    for input in once(Vec::new())
        .chain(once(vec![0x5a]))
        .chain((u8::MIN..=u8::MAX).map(|byte| vec![0x5a, byte]))
        .chain(once(vec![0x5a, 0x81, 0x00, 0xff]))
    {
        let first = input.first().copied();
        let second = input.get(1).copied();
        let raw = second.map_or_else(|| profile.eof_word(), u32::from);
        let converted_first = scalar_crazy(7_138_732, raw);
        let converted_second = scalar_crazy(INITIAL_SECOND, converted_first);
        assert_eq!(converted_second % 256, u32::from(second.unwrap_or(255)));
        let mut vm = ProfileMachine::from_state(
            profile,
            loaded.memory().to_vec(),
            input,
            ProfileRegisters::default(),
        )
        .map_err(|error| error.to_string())?;
        let mut trace = Vec::new();
        let outcome = vm
            .run_traced(82, &mut |step| trace.push(*step))
            .map_err(|error| error.to_string())?;
        assert_eq!(outcome, RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 82,
        });
        assert_eq!(trace.len(), 82);
        let mut rotated = INITIAL_FIRST;
        for position in [12usize, 18, 24, 30, 36, 44, 51, 58, 65] {
            let step = trace.get(position).ok_or("missing rotation")?;
            assert_eq!(step.decoded, Some(b'*'));
            assert_eq!(step.before.registers.data_pointer, 95);
            assert_eq!(
                step.memory_reads.data.map(|read| read.value),
                Some(rotated)
            );
            rotated = independent_rotate(rotated);
            assert_eq!(step.after.registers.accumulator, rotated);
        }
        assert_eq!(rotated, 7_138_732);
        for (position, expected) in [(37usize, first), (69, second)] {
            let step = trace.get(position).ok_or("missing real signed read")?;
            assert_eq!(step.decoded, Some(profile.input_instruction()));
            assert_eq!(
                step.input,
                Some(expected.map_or(TraceInput::EndOfInput, TraceInput::Byte))
            );
        }
        for (position, address, value) in [
            (66usize, 96u32, 121u32),
            (67, 122, 157),
            (70, 160, 157),
            (71, 158, 36),
            (72, 37, 66),
            (73, 67, 85),
            (75, 87, 69),
            (76, 70, 81),
            (77, 82, 80),
            (78, 81, 94),
        ] {
            let step =
                trace.get(position).ok_or("missing physical pointer jump")?;
            assert_eq!(step.decoded, Some(b'j'));
            assert_eq!(step.before.registers.data_pointer, address);
            assert_eq!(
                step.memory_reads.data.map(|read| read.value),
                Some(value)
            );
        }
        for (position, address, before, after) in [
            (79usize, 95u32, 7_138_732u32, converted_first),
            (80, 96, INITIAL_SECOND, converted_second),
        ] {
            let step = trace
                .get(position)
                .ok_or("missing signed conversion write")?;
            assert_eq!(step.decoded, Some(b'p'));
            assert_eq!(step.before.registers.data_pointer, address);
            assert_eq!(
                step.memory_reads.data.map(|read| read.value),
                Some(before)
            );
            assert_eq!(step.after.registers.accumulator, after);
            assert_eq!(vm.memory_word(address), Ok(after));
        }
        assert_eq!(trace.get(81).and_then(|step| step.decoded), Some(b'v'));
        assert!(trace.iter().all(|step| step.output.is_none()));
        assert!(vm.output().is_empty());
        assert_eq!(
            vm.input_consumed(),
            usize::from(first.is_some()) + usize::from(second.is_some())
        );
        cases = cases.saturating_add(1);
    }
    assert_eq!(cases, 259);
    Ok(())
}

// The tempting direct 87 -> 95 pointer shortcut is not a source-valid
// Malbolge instruction. Reject it during generation, not after publication.
#[test]
fn c23_short_output_pointer_shortcut_fails_loader_admission()
-> Result<(), String> {
    let profile = current_profile();
    let mut source =
        layout::build_c23_nine_rotated_signed_conversion_without_output_source(
            profile,
        )
        .map_err(|error| format!("{error:?}"))?;
    assert_eq!(layout::admit_c23_probe_graphical_source(&source), Ok(()));
    // C75 j would directly return D=95 if virgin M87 were 94, saving three
    // operations and leaving space for p/p/<. But source byte 94 at C87
    // does not decode to any recognized opcode under the strict loader.
    source[87] = 94;
    assert_eq!(
        layout::admit_c23_probe_graphical_source(&source),
        Err(
            layout::C23OperandProbeSourceError::InvalidGraphicalSourceCell {
                position: 87,
                byte: 94,
            }
        ),
    );
    assert!(ProfileMachine::from_source(profile, &source, vec![]).is_err());
    source[87] = 0;
    assert_eq!(
        layout::admit_c23_probe_graphical_source(&source),
        Err(
            layout::C23OperandProbeSourceError::InvalidGraphicalSourceCell {
                position: 87,
                byte: 0,
            }
        ),
    );
    // The alternative three-jump route via M82=94 also fails source
    // admission; it cannot replace the existing four-jump path to M95.
    let mut alternate =
        layout::build_c23_nine_rotated_signed_conversion_without_output_source(
            profile,
        )
        .map_err(|error| format!("{error:?}"))?;
    alternate[82] = 94;
    assert_eq!(
        layout::admit_c23_probe_graphical_source(&alternate),
        Err(
            layout::C23OperandProbeSourceError::InvalidGraphicalSourceCell {
                position: 82,
                byte: 94,
            }
        ),
    );
    assert!(ProfileMachine::from_source(profile, &alternate, vec![]).is_err());
    // These are exact source-admission obstructions, not assertions that
    // no other code/data relocation can ever perform C23 conversion.
    Ok(())
}

// Graphical code-cell admission must enforce the VM's loader *length*
// prerequisite too: no operand probe can load with zero or one source word.
#[test]
fn c23_probe_source_checker_rejects_incomplete_loader_recurrence()
-> Result<(), String> {
    let source = layout::build_c23_operand_probe_source(current_profile())
        .map_err(|error| format!("{error:?}"))?;
    for length in [0usize, 1] {
        let incomplete = &source[..length];
        assert_eq!(
            layout::admit_c23_probe_graphical_source(incomplete),
            Err(
                layout::C23OperandProbeSourceError::InsufficientSourceCells {
                    cells: length,
                }
            ),
        );
        assert!(matches!(
            ProfileMachine::from_source(current_profile(), incomplete, vec![]),
            Err(malbolge::ProfileMachineError::Load(
                malbolge::ProfileLoadError::InsufficientRecurrenceBase,
            )),
        ));
    }
    assert_eq!(
        layout::admit_c23_probe_graphical_source(&source[..2]),
        Ok(())
    );
    let limit = current_profile().word_modulus();
    let too_long = vec![0_u8; usize::try_from(limit).unwrap() + 1];
    assert_eq!(
        layout::admit_c23_probe_graphical_source(&too_long),
        Err(layout::C23OperandProbeSourceError::SourceExceedsMemory {
            cells: too_long.len(),
            limit,
        }),
    );
    Ok(())
}

// An earlier return from C74 appears to leave enough source positions for
// p/p/< before C81 halts. Enumerate every loader-admissible source value at
// M86 (the actual C74 jump operand). None puts D at M95 by C76. The
// unchanged loader recurrence after source[90] makes it safe to share the
// independently loaded image while patching these two virgin source cells.
#[test]
#[expect(
    clippy::arithmetic_side_effects,
    clippy::indexing_slicing,
    clippy::panic_in_result_fn,
    reason = "finite eight-case graphical pointer relocation proof"
)]
fn every_graphical_c74_early_return_misses_first_c23_operand()
-> Result<(), String> {
    let profile = current_profile();
    let base =
        layout::build_c23_nine_rotated_signed_conversion_without_output_source(
            profile,
        )
        .map_err(|error| format!("{error:?}"))?;
    let loaded = ProfileMachine::from_source(profile, &base, vec![])
        .map_err(|error| error.to_string())?;
    let mut baseline = ProfileMachine::from_state(
        profile,
        loaded.memory().to_vec(),
        vec![0x5a, 0x12],
        ProfileRegisters::default(),
    )
    .map_err(|error| error.to_string())?;
    let mut baseline_trace = Vec::new();
    _ = baseline
        .run_traced(82, &mut |step| baseline_trace.push(*step))
        .map_err(|error| error.to_string())?;
    assert_eq!(baseline_trace.len(), 82);
    let jump = (33..=126u8)
        .find(|byte| {
            decode_profile_instruction(u32::from(*byte), 74) == Some(b'j')
        })
        .ok_or("no graphical C74 jump")?;
    assert_eq!(jump, 60);
    assert_eq!(base.get(89..), Some(b"Iy".as_slice()));
    let expected = [
        (47, 95),
        (48, 73),
        (70, 43),
        (76, 57),
        (89, 121),
        (106, 7_174_404),
        (107, 121),
        (125, 121),
    ];
    let mut cases = 0;
    for byte in 33..=126u8 {
        if !decode_profile_instruction(u32::from(byte), 86)
            .is_some_and(|opcode| b"oijp*/<v".contains(&opcode))
        {
            continue;
        }
        let mut candidate = base.clone();
        candidate[74] = jump;
        candidate[86] = byte;
        layout::admit_c23_probe_graphical_source(&candidate)
            .map_err(|error| format!("{error:?}"))?;
        let (expected_byte, expected_read) = expected
            .get(cases)
            .copied()
            .ok_or("unexpected graphical M86 candidate")?;
        assert_eq!(byte, expected_byte);
        let mut memory = loaded.memory().to_vec();
        // C74 and C86 have not been written or read by earlier operations.
        // Source[89..91] stays fixed, so all expanded loader cells are exact.
        memory[74] = u32::from(jump);
        memory[86] = u32::from(byte);
        let mut vm = ProfileMachine::from_state(
            profile,
            memory,
            vec![0x5a, 0x12],
            ProfileRegisters::default(),
        )
        .map_err(|error| error.to_string())?;
        let mut trace = Vec::new();
        let result = vm
            .run_traced(82, &mut |step| trace.push(*step))
            .map_err(|error| error.to_string())?;
        assert_eq!(result, RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 82,
        });
        assert_eq!(trace.len(), 82);
        // Neither patched source word can disturb earlier executions:
        // all nine physical rotations and both input events are identical.
        assert_eq!(&trace[..74], &baseline_trace[..74]);
        assert_eq!(trace[69].input, Some(TraceInput::Byte(0x12)));
        assert_eq!(trace[74].decoded, Some(b'j'));
        assert_eq!(trace[74].before.registers.data_pointer, 86);
        assert_eq!(
            trace[74].memory_reads.data.map(|read| read.value),
            Some(u32::from(byte))
        );
        assert_eq!(trace[75].decoded, Some(b'j'));
        assert_eq!(
            trace[75].before.registers.data_pointer,
            u32::from(byte) + 1
        );
        assert_eq!(
            trace[75].memory_reads.data.map(|read| read.value),
            Some(expected_read)
        );
        assert_eq!(trace[76].before.registers.data_pointer, expected_read + 1);
        assert_ne!(trace[76].before.registers.data_pointer, 95);
        assert_eq!(vm.output(), &[]);
        cases += 1;
    }
    assert_eq!(cases, expected.len());
    Ok(())
}
