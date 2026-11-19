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
    current_profile, historical_profile, profile_rotate,
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
