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
//   - Source-C dynamic linking supersedes isolated physical byte conversion.
// - Merge-When:
//   - General physical operand synthesis proves signed byte I/O.
// - Summary:
//   - Loader-valid exact C23 signed-byte emission and physical path evidence.

//! Physical signed-C23 conversion and output, not source-C compilation.

#[path = "../src/compiler/malbolge-layout/composition/lib.rs"]
pub mod layout;

use std::iter::once;

use malbolge::{
    ProfileMachine, ProfileRegisters, RunOutcome, Termination, TraceInput,
    current_profile, decode_profile_instruction, encrypt_profile_cell,
    historical_profile, profile_rotate,
};

const FIRST_ADDRESS: u32 = 283;
const SECOND_ADDRESS: u32 = 284;
const INITIAL_FIRST: u32 = 7_174_404;
const INITIAL_SECOND: u32 = 121;

// The signed C23 converter reaches M95/M96 at C79/C80, but C81 halts.
// This fixed-prefix search probes only the still-virgin late source cells.
// A relocated loader or earlier control layout is outside this finite claim.
struct LocalC23RouteSearch<'memory> {
    authored_code: &'memory [(usize, u32)],
    memory: &'memory [u32],
}

impl LocalC23RouteSearch<'_> {
    fn count_paths(
        &self,
        pointer: u32,
        jumps: u8,
        assignments: &mut Vec<(usize, u32)>,
    ) -> usize {
        if jumps == 0 {
            return usize::from(pointer == 95);
        }
        let Ok(address) = usize::try_from(pointer) else {
            return 0;
        };
        let Some(&loaded) = self.memory.get(address) else {
            return 0;
        };
        let candidates: Vec<u32> = if (82..=88).contains(&address) {
            (33..=126u32)
                .filter(|&word| {
                    decode_profile_instruction(word, pointer)
                        .is_some_and(|op| b"oijp*/<v".contains(&op))
                })
                .collect()
        } else {
            vec![
                self.authored_code
                    .iter()
                    .find(|(position, _)| *position == address)
                    .map_or(loaded, |(_, word)| *word),
            ]
        };
        let mut paths = 0usize;
        for word in candidates {
            if assignments.iter().any(|&(position, previous)| {
                position == address && previous != word
            }) {
                continue;
            }
            assignments.push((address, word));
            if let Some(next) = word.checked_add(1) {
                paths = paths.saturating_add(self.count_paths(
                    next,
                    jumps.saturating_sub(1),
                    assignments,
                ));
            }
            _ = assignments.pop();
        }
        paths
    }
}

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

// Exhaust the graphical C37 edits that might remove the converter's
// discarded first read without changing the rest of its 91-cell source.
// This is a local single-cell obstruction, not a proof that a different
// physical assembler cannot construct a true one-read C23 conversion.
#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "eight graphical replacements and certified VM prefix"
)]
fn one_cell_c37_replacement_cannot_remove_discarded_read_and_keep_c23_operand()
-> Result<(), String> {
    let profile = current_profile();
    let original = layout::build_c23_nine_rotated_signed_output_source(profile)
        .map_err(|error| format!("{error:?}"))?;
    assert_eq!(original[37], 80);
    let mut original_vm =
        ProfileMachine::from_source(profile, &original, Vec::new())
            .map_err(|error| error.to_string())?;
    let mut prefix = Vec::new();
    let _ = original_vm.run_traced(13, &mut |step| prefix.push(*step));
    assert_eq!(prefix.len(), 13);
    assert_eq!(prefix[10].decoded, Some(b'j'));
    assert_eq!(
        prefix[10]
            .memory_reads
            .data
            .map(|read| (read.address, read.value)),
        Some((37, 80))
    );
    assert_eq!(prefix[11].decoded, Some(b'j'));
    assert_eq!(prefix[11].before.registers.data_pointer, 81);
    assert_eq!(prefix[12].decoded, Some(b'*'));
    assert_eq!(prefix[12].before.registers.data_pointer, 95);
    // Before C10 no instruction writes M37 and no instruction fetches it.
    // Changing only source[37] must therefore change its initial value at
    // this mandatory pointer read, not the earlier execution path.
    assert!(prefix[..10].iter().all(|step| {
        step.before.registers.code_pointer != 37
            && step
                .memory_delta
                .data
                .is_none_or(|write| write.address != 37)
            && step
                .memory_delta
                .encryption
                .is_none_or(|write| write.address != 37)
    }));
    let mut candidate_count = 0u32;
    let mut original_path_count = 0u32;
    for glyph in 33..=126u8 {
        if !matches!(
            decode_profile_instruction(u32::from(glyph), 37),
            Some(b'j' | b'i' | b'*' | b'p' | b'o' | b'<' | b'/' | b'v')
        ) {
            continue;
        }
        candidate_count += 1;
        let mut candidate = original.clone();
        candidate[37] = glyph;
        layout::admit_c23_probe_graphical_source(&candidate)
            .map_err(|error| format!("{error:?}"))?;
        // With C10 still reading M37 and C11 still reading the selected
        // source cell, only M37=80 can retain the certified C12/M95 path.
        // This is a *necessary path-identity* check, not a VM replacement
        // or an assertion that alternative source programs are impossible.
        let preserves_c23_operand = glyph == 80;
        if preserves_c23_operand {
            original_path_count += 1;
            assert_eq!(glyph, original[37]);
            assert_eq!(
                decode_profile_instruction(u32::from(glyph), 37),
                Some(b'/')
            );
        } else {
            assert_ne!(glyph, original[37]);
        }
    }
    assert_eq!(candidate_count, 8);
    assert_eq!(original_path_count, 1);
    Ok(())
}

// A tempting one-byte mutation appears correct for an ASCII witness but
// destroys the real M95/M96 conversion. EOF exposes this false positive.
#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "normative N15 counterexample on byte and true EOF"
)]
fn deleting_first_read_by_changing_c37_must_not_claim_signed_conversion()
-> Result<(), String> {
    let profile = current_profile();
    let mut source =
        layout::build_c23_nine_rotated_signed_output_source(profile)
            .map_err(|error| format!("{error:?}"))?;
    source[37] = 125;
    assert_eq!(
        decode_profile_instruction(u32::from(source[37]), 37),
        Some(b'o')
    );
    let loaded = ProfileMachine::from_source(profile, &source, Vec::new())
        .map_err(|error| error.to_string())?;
    for (input, expected_emitted) in [(vec![0x5a], 0x5au8), (Vec::new(), 89u8)]
    {
        let mut vm = ProfileMachine::from_state(
            profile,
            loaded.memory().to_vec(),
            input.clone(),
            ProfileRegisters::default(),
        )
        .map_err(|error| error.to_string())?;
        let mut trace = Vec::new();
        assert_eq!(
            vm.run_traced(81, &mut |step| trace.push(*step))
                .map_err(|error| error.to_string())?,
            RunOutcome::Terminated {
                reason: Termination::HaltInstruction,
                steps: 81,
            },
        );
        assert_eq!(trace[37].decoded, Some(b'o'));
        assert!(trace[37].input.is_none());
        assert_eq!(trace[66].decoded, Some(b'/'));
        assert_eq!(trace[77].before.registers.data_pointer, 158);
        assert_eq!(trace[78].before.registers.data_pointer, 159);
        assert_eq!(trace[79].output, Some(expected_emitted));
        assert_eq!(vm.output(), &[expected_emitted]);
        assert_ne!(trace[77].before.registers.data_pointer, 95);
        assert_ne!(trace[78].before.registers.data_pointer, 96);
    }
    // Actual EOF output is 89 rather than the C23 unsigned-char 255.
    assert_ne!(89u8, u8::MAX);
    Ok(())
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

// Executable signed C23 output after all nine source-locked rotations.
// Unlike the earlier non-output experiment, this physical path uses an
// earlier second `/` at C66 to leave enough code for both `p` writes and
// a genuine `<` at C79 before the source-required C81 halt. It still
// discards a first read at C37 and does not compile the mutable checksum.
#[test]
#[expect(
    clippy::cognitive_complexity,
    clippy::too_many_lines,
    clippy::panic_in_result_fn,
    clippy::integer_division_remainder_used,
    reason = "257 independent C23 signed conversions and normative VM effects"
)]
fn nine_rotations_emit_every_signed_c23_byte_in_the_real_guest()
-> Result<(), String> {
    let profile = current_profile();
    let source = layout::build_c23_nine_rotated_signed_output_source(profile)
        .map_err(|error| format!("{error:?}"))?;
    let old =
        layout::build_c23_nine_rotated_signed_conversion_without_output_source(
            profile,
        )
        .map_err(|error| format!("{error:?}"))?;
    assert_eq!(source.len(), 91);
    assert_eq!(source.get(89..), Some(b"Iy".as_slice()));
    assert_eq!(source.get(81), Some(&94));
    assert_eq!(source.get(67), Some(&67));
    assert_eq!(source.get(68), Some(&94));
    assert_eq!(layout::admit_c23_probe_graphical_source(&source), Ok(()));
    assert_eq!(
        layout::build_c23_nine_rotated_signed_output_source(
            historical_profile(),
        ),
        Err(layout::C23OperandProbeSourceError::UnsupportedProfile),
    );
    let changed = [66, 69, 74, 75, 77, 78, 79, 80];
    for position in 0..source.len() {
        assert_eq!(
            source[position] != old[position],
            changed.contains(&position),
            "unexpected source/loader modification at C{position}",
        );
    }
    for (position, opcode) in [
        (37usize, profile.input_instruction()),
        (66, profile.input_instruction()),
        (67, b'j'),
        (68, b'o'),
        (69, b'j'),
        (74, b'j'),
        (75, b'o'),
        (76, b'j'),
        (77, b'p'),
        (78, b'p'),
        (79, profile.output_instruction()),
        (80, b'v'),
    ] {
        assert_eq!(
            decode_profile_instruction(
                u32::from(source[position]),
                position as u32
            ),
            Some(opcode),
            "unrecognized physical opcode at C{position}",
        );
    }
    let loaded = ProfileMachine::from_source(profile, &source, Vec::new())
        .map_err(|error| error.to_string())?;
    assert_eq!(loaded.memory_word(95), Ok(INITIAL_FIRST));
    assert_eq!(loaded.memory_word(96), Ok(INITIAL_SECOND));
    let mut count = 0usize;
    for input in once(Vec::new())
        .chain(once(vec![0x5a]))
        .chain((u8::MIN..=u8::MAX).map(|byte| vec![0x5a, byte]))
        .chain(once(vec![0x5a, 0x81, 0x00, 0xff]))
    {
        let first = input.first().copied();
        let second = input.get(1).copied();
        let signed = second.map_or_else(|| profile.eof_word(), u32::from);
        let converted_first = scalar_crazy(7_138_732, signed);
        let converted_second = scalar_crazy(INITIAL_SECOND, converted_first);
        let expected = second.unwrap_or(0xff);
        assert_eq!(converted_second % 256, u32::from(expected));
        let mut vm = ProfileMachine::from_state(
            profile,
            loaded.memory().to_vec(),
            input,
            ProfileRegisters::default(),
        )
        .map_err(|error| error.to_string())?;
        let mut trace = Vec::new();
        let outcome = vm
            .run_traced(81, &mut |step| trace.push(*step))
            .map_err(|error| error.to_string())?;
        assert_eq!(outcome, RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 81,
        });
        assert_eq!(trace.len(), 81);
        for position in [12usize, 18, 24, 30, 36, 44, 51, 58, 65] {
            assert_eq!(trace[position].decoded, Some(b'*'));
            assert_eq!(trace[position].before.registers.data_pointer, 95);
        }
        for (position, value) in [(37usize, first), (66, second)] {
            assert_eq!(
                trace[position].decoded,
                Some(profile.input_instruction())
            );
            assert_eq!(
                trace[position].input,
                Some(value.map_or(TraceInput::EndOfInput, TraceInput::Byte)),
            );
        }
        for (position, before_d, read, after_d) in [
            (67usize, 97u32, INITIAL_FIRST, INITIAL_FIRST + 1),
            (69, INITIAL_FIRST + 2, 157, 158),
            (70, 158, 36, 37),
            (71, 37, 66, 67),
            (72, 67, 85, 86),
            (73, 86, 76, 77),
            (74, 77, 79, 80),
            (76, 81, 94, 95),
        ] {
            let step = &trace[position];
            assert_eq!(step.decoded, Some(b'j'));
            assert_eq!(step.before.registers.data_pointer, before_d);
            assert_eq!(
                step.memory_reads.data.map(|word| word.value),
                Some(read)
            );
            assert_eq!(step.after.registers.data_pointer, after_d);
        }
        assert_eq!(trace[75].decoded, Some(b'o'));
        assert_eq!(trace[75].before.registers.data_pointer, 80);
        for (position, address, original, converted) in [
            (77usize, 95u32, 7_138_732u32, converted_first),
            (78, 96, INITIAL_SECOND, converted_second),
        ] {
            let step = &trace[position];
            assert_eq!(step.decoded, Some(b'p'));
            assert_eq!(step.before.registers.data_pointer, address);
            assert_eq!(
                step.memory_reads.data.map(|read| read.value),
                Some(original)
            );
            assert_eq!(step.after.registers.accumulator, converted);
            assert_eq!(vm.memory_word(address), Ok(converted));
        }
        assert_eq!(trace[79].decoded, Some(profile.output_instruction()));
        assert_eq!(trace[79].before.registers.accumulator, converted_second);
        assert_eq!(trace[79].output, Some(expected));
        assert!(trace[..79].iter().all(|step| step.output.is_none()));
        assert_eq!(trace[80].decoded, Some(b'v'));
        assert_eq!(trace[80].before.registers.code_pointer, 80);
        assert_eq!(vm.output(), &[expected]);
        assert_eq!(
            vm.input_consumed(),
            usize::from(first.is_some()) + usize::from(second.is_some()),
        );
        count += 1;
    }
    assert_eq!(count, 259);
    Ok(())
}

// A real output of the *raw* second input at C74 must preserve A and D.
// The converted result is still held in guest memory, not emitted as C23
// putchar output. This checks the exact order for all 257 signed outcomes.
#[test]
#[expect(
    clippy::cognitive_complexity,
    clippy::too_many_lines,
    clippy::panic_in_result_fn,
    clippy::integer_division_remainder_used,
    reason = "all signed raw output checkpoints precede two physical p writes"
)]
fn live_signed_input_checkpoint_precedes_unmodified_conversion()
-> Result<(), String> {
    let profile = current_profile();
    let source =
        layout::build_c23_nine_rotated_input_checkpoint_source(profile)
            .map_err(|error| format!("{error:?}"))?;
    let plain =
        layout::build_c23_nine_rotated_signed_conversion_without_output_source(
            profile,
        )
        .map_err(|error| format!("{error:?}"))?;
    assert_eq!(source.len(), 91);
    assert_eq!(source.get(89..), Some(b"Iy".as_slice()));
    assert_eq!(layout::admit_c23_probe_graphical_source(&source), Ok(()));
    assert_eq!(
        layout::build_c23_nine_rotated_input_checkpoint_source(
            historical_profile(),
        ),
        Err(layout::C23OperandProbeSourceError::UnsupportedProfile),
    );
    for position in 0..source.len() {
        if position != 74 {
            assert_eq!(source[position], plain[position], "C={position}");
        }
    }
    assert_eq!(
        decode_profile_instruction(u32::from(source[74]), 74),
        Some(profile.output_instruction()),
    );
    let loaded = ProfileMachine::from_source(profile, &source, vec![])
        .map_err(|error| error.to_string())?;
    let mut cases = 0usize;
    for input in once(Vec::new())
        .chain(once(vec![0x5a]))
        .chain((u8::MIN..=u8::MAX).map(|byte| vec![0x5a, byte]))
        .chain(once(vec![0x5a, 0x81, 0x00, 0xff]))
    {
        let first = input.first().copied();
        let second = input.get(1).copied();
        let raw = second.map_or_else(|| profile.eof_word(), u32::from);
        let after_first = scalar_crazy(7_138_732, raw);
        let converted = scalar_crazy(INITIAL_SECOND, after_first);
        let raw_byte =
            u8::try_from(raw % 256).map_err(|error| error.to_string())?;
        assert_eq!(converted % 256, u32::from(second.unwrap_or(255)));
        let mut vm = ProfileMachine::from_state(
            profile,
            loaded.memory().to_vec(),
            input,
            ProfileRegisters::default(),
        )
        .map_err(|error| error.to_string())?;
        let mut trace = Vec::new();
        assert_eq!(
            vm.run_traced(82, &mut |step| trace.push(*step))
                .map_err(|error| error.to_string())?,
            RunOutcome::Terminated {
                reason: Termination::HaltInstruction,
                steps: 82,
            }
        );
        let first_read = trace.get(37).ok_or("missing mandatory first read")?;
        let live_read = trace.get(69).ok_or("missing second read")?;
        assert_eq!(
            first_read.input,
            Some(first.map_or(TraceInput::EndOfInput, TraceInput::Byte))
        );
        assert_eq!(
            live_read.input,
            Some(second.map_or(TraceInput::EndOfInput, TraceInput::Byte))
        );
        assert_eq!(live_read.after.registers.accumulator, raw);
        let checkpoint = trace.get(74).ok_or("missing raw checkpoint")?;
        assert_eq!(checkpoint.decoded, Some(profile.output_instruction()));
        assert_eq!(checkpoint.before.registers.data_pointer, 86);
        assert_eq!(checkpoint.before.registers.accumulator, raw);
        assert_eq!(checkpoint.after.registers.accumulator, raw);
        assert_eq!(checkpoint.output, Some(raw_byte));
        assert!(trace[..74].iter().all(|step| step.output.is_none()));
        assert!(trace[75..].iter().all(|step| step.output.is_none()));
        assert_eq!(vm.output(), &[raw_byte]);
        for (position, address, before, after) in [
            (79usize, 95u32, 7_138_732u32, after_first),
            (80, 96, INITIAL_SECOND, converted),
        ] {
            let write =
                trace.get(position).ok_or("missing guest conversion")?;
            assert_eq!(write.decoded, Some(b'p'));
            assert_eq!(write.before.registers.data_pointer, address);
            assert_eq!(
                write.memory_reads.data.map(|read| read.value),
                Some(before)
            );
            assert_eq!(write.after.registers.accumulator, after);
            assert_eq!(vm.memory_word(address), Ok(after));
        }
        assert_eq!(trace.get(81).and_then(|step| step.decoded), Some(b'v'));
        assert_eq!(
            vm.input_consumed(),
            usize::from(first.is_some()) + usize::from(second.is_some()),
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

fn assert_c23_tail_is_virgin(trace: &[malbolge::ProfileStepTrace]) {
    for position in (74..=80u32).chain(82..=88) {
        assert!(
            trace.iter().all(|step| {
                step.before.registers.code_pointer != position
                    && step
                        .memory_reads
                        .data
                        .is_none_or(|read| read.address != position)
                    && step
                        .memory_delta
                        .data
                        .is_none_or(|write| write.address != position)
            }),
            "early use of C{position} forbids a late-only edit"
        );
    }
}

#[expect(
    clippy::panic_in_result_fn,
    reason = "normative VM state establishes the late data-cell search prefix"
)]
fn checked_c23_prefix_vm() -> Result<ProfileMachine, String> {
    let profile = current_profile();
    let source =
        layout::build_c23_nine_rotated_signed_conversion_without_output_source(
            profile,
        )
        .map_err(|error| format!("{error:?}"))?;
    let mut vm =
        ProfileMachine::from_source(profile, &source, vec![0x5a, 0x81])
            .map_err(|error| error.to_string())?;
    let mut trace = Vec::new();
    assert_eq!(
        vm.run_traced(74, &mut |step| trace.push(*step))
            .map_err(|error| error.to_string())?,
        RunOutcome::BudgetExhausted { steps: 74 },
        "C23 converter must stay live through its first 74 steps",
    );
    assert_eq!(trace.len(), 74, "complete C23 prefix trace");
    assert_eq!(
        trace
            .get(73)
            .ok_or("missing last prefix step")?
            .after
            .registers
            .data_pointer,
        86,
        "D must point at first late data cell",
    );
    assert_eq!(vm.memory_word(95), Ok(7_138_732), "nine rotations");
    assert_eq!(vm.memory_word(96), Ok(121), "second C23 operand");
    assert!(
        trace.iter().any(|step| {
            step.memory_reads
                .data
                .is_some_and(|read| read.address == 81 && read.value == 94)
        }),
        "C81 pointer word must have been read before the tail"
    );
    assert_c23_tail_is_virgin(&trace);
    // Source-required M81=94 was already consumed as a pointer operand.
    assert_eq!(source.get(81), Some(&94), "source-fixed pointer word");
    assert_ne!(
        decode_profile_instruction(94, 81),
        Some(profile.output_instruction()),
        "mandatory pointer word must not decode to output",
    );
    Ok(vm)
}

fn c23_graphical_opcode(position: usize, opcode: u8) -> Result<u32, String> {
    (33..=126u32)
        .find(|&word| {
            decode_profile_instruction(
                word,
                u32::try_from(position).unwrap_or(u32::MAX),
            ) == Some(opcode)
        })
        .ok_or_else(|| format!("no source glyph for {opcode} at C{position}"))
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "finite guest pointer route search with VM positive control"
)]
fn fixed_c23_prefix_has_no_one_jump_shorter_graphical_output_return()
-> Result<(), String> {
    let vm = checked_c23_prefix_vm()?;
    let mut original = Vec::new();
    for position in 75..=78 {
        original.push((position, c23_graphical_opcode(position, b'j')?));
    }
    for position in 79..=80 {
        original.push((position, c23_graphical_opcode(position, b'p')?));
    }
    // The existing four-jump path must be reachable as a positive control.
    let original_paths = LocalC23RouteSearch {
        authored_code: &original,
        memory: vm.memory(),
    };
    assert!(
        original_paths.count_paths(87, 4, &mut Vec::new()) > 0,
        "existing four-jump return must be reachable"
    );

    let mut shortened = Vec::new();
    for position in 75..=77 {
        shortened.push((position, c23_graphical_opcode(position, b'j')?));
    }
    shortened.push((78, c23_graphical_opcode(78, b'p')?));
    shortened.push((79, c23_graphical_opcode(79, b'p')?));
    shortened.push((80, c23_graphical_opcode(80, b'<')?));
    let search = LocalC23RouteSearch {
        authored_code: &shortened,
        memory: vm.memory(),
    };
    // All graphical C82..C88 alternatives fail to reach M95 before C78.
    assert_eq!(
        search.count_paths(87, 3, &mut Vec::new()),
        0,
        "three jumps must not reach M95 from M87"
    );
    shortened.push((74, c23_graphical_opcode(74, b'j')?));
    let early_search = LocalC23RouteSearch {
        authored_code: &shortened,
        memory: vm.memory(),
    };
    assert_eq!(
        early_search.count_paths(86, 4, &mut Vec::new()),
        0,
        "four jumps must not reach M95 from M86"
    );
    Ok(())
}

// The source-authentic Iy pointer word M81=94 must halt when reached as
// code. A reached i at C79 can skip it, but self-encryption belongs to the
// indirect *target* C82 rather than the i instruction's original C79.
// This positive terminated path is a control primitive, not C23 output.
#[test]
#[expect(
    clippy::cognitive_complexity,
    clippy::too_many_lines,
    clippy::panic_in_result_fn,
    reason = "normative input and indirect-code-pointer traces"
)]
fn physical_indirect_jump_bypasses_the_source_locked_halt()
-> Result<(), String> {
    let profile = current_profile();
    let source =
        layout::build_c23_nine_rotated_indirect_halt_probe_source(profile)
            .map_err(|error| format!("{error:?}"))?;
    assert_eq!(source.len(), 91);
    assert_eq!(source.get(89..), Some(b"Iy".as_slice()));
    assert_eq!(source.get(81), Some(&94));
    assert_eq!(source.get(80), Some(&82));
    assert_eq!(source.get(82), Some(&80));
    assert_eq!(layout::admit_c23_probe_graphical_source(&source), Ok(()));
    assert_eq!(
        layout::build_c23_nine_rotated_indirect_halt_probe_source(
            historical_profile(),
        ),
        Err(layout::C23OperandProbeSourceError::UnsupportedProfile),
    );
    let loaded = ProfileMachine::from_source(profile, &source, vec![])
        .map_err(|error| error.to_string())?;
    assert_eq!(loaded.memory_word(95), Ok(INITIAL_FIRST));
    assert_eq!(loaded.memory_word(96), Ok(INITIAL_SECOND));
    let mut cases = 0usize;
    for input in once(Vec::new())
        .chain(once(vec![0x5a]))
        .chain((u8::MIN..=u8::MAX).map(|byte| vec![0x5a, byte]))
        .chain(once(vec![0x5a, 0x81, 0x00, 0xff]))
    {
        let first = input.first().copied();
        let second = input.get(1).copied();
        let mut vm = ProfileMachine::from_state(
            profile,
            loaded.memory().to_vec(),
            input,
            ProfileRegisters::default(),
        )
        .map_err(|error| error.to_string())?;
        let mut trace = Vec::new();
        assert_eq!(
            vm.run_traced(82, &mut |step| trace.push(*step))
                .map_err(|error| error.to_string())?,
            RunOutcome::Terminated {
                reason: Termination::HaltInstruction,
                steps: 82,
            },
        );
        assert_eq!(trace.len(), 82);
        for (position, byte) in [(37usize, first), (69, second)] {
            assert_eq!(
                trace[position].input,
                Some(byte.map_or(TraceInput::EndOfInput, TraceInput::Byte))
            );
        }
        for (position, data, value) in
            [(75usize, 87u32, 69u32), (76, 70, 81), (78, 83, 79)]
        {
            let step = &trace[position];
            assert_eq!(step.decoded, Some(b'j'));
            assert_eq!(step.before.registers.data_pointer, data);
            assert_eq!(
                step.memory_reads.data.map(|read| read.value),
                Some(value)
            );
        }
        let indirect = &trace[79];
        assert_eq!(indirect.before.registers.code_pointer, 79);
        assert_eq!(indirect.before.registers.data_pointer, 80);
        assert_eq!(indirect.decoded, Some(b'i'));
        assert_eq!(
            indirect
                .memory_reads
                .data
                .map(|read| (read.address, read.value)),
            Some((80, 82)),
        );
        assert_eq!(indirect.after.registers.code_pointer, 83);
        assert_eq!(indirect.after.registers.data_pointer, 81);
        assert_eq!(trace[80].before.registers.code_pointer, 83);
        assert_eq!(trace[80].decoded, Some(b'o'));
        assert_eq!(trace[81].before.registers.code_pointer, 84);
        assert_eq!(trace[81].decoded, Some(b'v'));
        assert_eq!(vm.memory_word(82), Ok(66));
        assert_eq!(vm.memory_word(80), Ok(82));
        assert_eq!(vm.memory_word(81), Ok(94));
        assert_eq!(vm.memory_word(95), Ok(7_138_732));
        assert_eq!(vm.memory_word(96), Ok(INITIAL_SECOND));
        assert_eq!(vm.output(), &[]);
        assert_eq!(
            vm.input_consumed(),
            usize::from(first.is_some()) + usize::from(second.is_some())
        );
        cases = cases.saturating_add(1);
    }
    assert_eq!(cases, 259);
    Ok(())
}

// The C79 indirect bypass executes C83=o and advances D to M82. A single
// C84 j would need the *encrypted* M82 to equal 94, returning D to M95.
// The sole predecessor encrypting to 94 is 83, which the source loader
// rejects at C82. This does not exclude longer or relocated pointer routes.
#[test]
fn c23_indirect_one_jump_reset_cannot_use_a_graphical_target_cell() {
    let profile = current_profile();
    let mut source =
        layout::build_c23_nine_rotated_indirect_halt_probe_source(profile)
            .expect("validated physical indirect prefix");
    assert_eq!(source.get(82), Some(&80));
    assert_eq!(encrypt_profile_cell(80), Some(66));
    assert_eq!(source.get(83), Some(&79));
    assert_eq!(decode_profile_instruction(79, 83), Some(b'o'));

    let loader_valid = (33..=126u32)
        .filter(|&byte| {
            decode_profile_instruction(byte, 82)
                .is_some_and(|opcode| b"oijp*/<v".contains(&opcode))
        })
        .collect::<Vec<_>>();
    assert_eq!(loader_valid.len(), 8);
    assert!(
        loader_valid
            .iter()
            .all(|&byte| encrypt_profile_cell(byte) != Some(94))
    );
    assert_eq!(
        (33..=126u32)
            .filter(|&byte| encrypt_profile_cell(byte) == Some(94))
            .collect::<Vec<_>>(),
        vec![83],
    );
    assert_eq!(decode_profile_instruction(83, 82), Some(b'7'));
    source[82] = 83;
    assert_eq!(
        layout::admit_c23_probe_graphical_source(&source),
        Err(
            layout::C23OperandProbeSourceError::InvalidGraphicalSourceCell {
                position: 82,
                byte: 83,
            }
        ),
    );
}

// The bypassed C81 pointer/halt cannot itself emit output, but the reached
// C84..C88 path can perform a real input-dependent crazy, output and halt.
// This is *not* the C23 conversion: the actual operands are 85 and 123.
#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "source-locked VM traces establish every guest effect"
)]
fn indirect_crazy_output_preserves_live_input_and_self_modification()
-> Result<(), String> {
    let profile = current_profile();
    let source =
        layout::build_c23_nine_rotated_indirect_crazy_output_source(profile)
            .map_err(|error| format!("{error:?}"))?;
    let halted =
        layout::build_c23_nine_rotated_indirect_halt_probe_source(profile)
            .map_err(|error| format!("{error:?}"))?;
    assert_eq!(source.len(), 91);
    assert_eq!(source.get(89..), Some(b"Iy".as_slice()));
    assert_eq!(source.get(81), Some(&94));
    assert_eq!(source.get(82), Some(&80));
    assert_eq!(source.get(83), Some(&79));
    assert_eq!(source.get(87), Some(&69));
    assert_eq!(layout::admit_c23_probe_graphical_source(&source), Ok(()));
    assert_eq!(
        layout::build_c23_nine_rotated_indirect_crazy_output_source(
            historical_profile(),
        ),
        Err(layout::C23OperandProbeSourceError::UnsupportedProfile),
    );
    for position in 0..source.len() {
        if ![84, 85, 86, 88].contains(&position) {
            assert_eq!(source[position], halted[position], "C={position}");
        }
    }
    let loaded = ProfileMachine::from_source(profile, &source, vec![])
        .map_err(|error| error.to_string())?;
    assert_eq!(loaded.memory_word(95), Ok(INITIAL_FIRST));
    assert_eq!(loaded.memory_word(96), Ok(INITIAL_SECOND));
    let inputs = [
        vec![],
        vec![0x5a],
        vec![0x5a, 0x00],
        vec![0x5a, 0x01],
        vec![0x5a, 0x7f],
        vec![0x5a, 0x80],
        vec![0x5a, 0xff],
        vec![0x5a, 0x81, 0x00, 0xff],
    ];
    for input in inputs {
        let first = input.first().copied();
        let second = input.get(1).copied();
        let raw = second.map_or_else(|| profile.eof_word(), u32::from);
        let expected_first = scalar_crazy(85, raw);
        let expected_second = scalar_crazy(123, expected_first);
        let expected_byte = u8::try_from(expected_first % 256)
            .map_err(|error| error.to_string())?;
        let mut vm = ProfileMachine::from_state(
            profile,
            loaded.memory().to_vec(),
            input,
            ProfileRegisters::default(),
        )
        .map_err(|error| error.to_string())?;
        let mut trace = Vec::new();
        assert_eq!(
            vm.run_traced(86, &mut |step| trace.push(*step))
                .map_err(|error| error.to_string())?,
            RunOutcome::Terminated {
                reason: Termination::HaltInstruction,
                steps: 86,
            }
        );
        assert_eq!(trace.len(), 86);
        assert_eq!(vm.output(), &[expected_byte]);
        assert_eq!(vm.memory_word(82), Ok(66));
        assert_eq!(vm.memory_word(67), Ok(expected_first));
        assert_eq!(vm.memory_word(69), Ok(expected_second));
        assert_eq!(vm.memory_word(95), Ok(7_138_732));
        assert_eq!(vm.memory_word(96), Ok(INITIAL_SECOND));
        for (position, value) in [(37usize, first), (69, second)] {
            assert_eq!(
                trace[position].input,
                Some(value.map_or(TraceInput::EndOfInput, TraceInput::Byte)),
            );
        }
        assert_eq!(trace[79].decoded, Some(b'i'));
        assert_eq!(trace[79].before.registers.data_pointer, 80);
        assert_eq!(
            trace[79].memory_reads.data.map(|read| read.value),
            Some(82),
        );
        assert_eq!(trace[79].after.registers.code_pointer, 83);
        assert_eq!(trace[80].before.registers.code_pointer, 83);
        assert_eq!(trace[80].decoded, Some(b'o'));
        assert_eq!(trace[81].before.registers.code_pointer, 84);
        assert_eq!(trace[81].decoded, Some(b'j'));
        assert_eq!(
            trace[81].memory_reads.data.map(|read| read.value),
            Some(66),
        );
        for (index, code, address, before, after) in [
            (82usize, 85u32, 67u32, 85u32, expected_first),
            (84, 87, 69, 123, expected_second),
        ] {
            let step = &trace[index];
            assert_eq!(step.before.registers.code_pointer, code);
            assert_eq!(step.decoded, Some(b'p'));
            assert_eq!(step.before.registers.data_pointer, address);
            assert_eq!(
                step.memory_reads.data.map(|read| read.value),
                Some(before),
            );
            assert_eq!(step.after.registers.accumulator, after);
        }
        assert_eq!(trace[83].before.registers.code_pointer, 86);
        assert_eq!(trace[83].decoded, Some(profile.output_instruction()));
        assert_eq!(trace[83].output, Some(expected_byte));
        assert_eq!(trace[85].before.registers.code_pointer, 88);
        assert_eq!(trace[85].decoded, Some(b'v'));
        assert_eq!(
            vm.input_consumed(),
            usize::from(first.is_some()) + usize::from(second.is_some()),
        );
    }
    Ok(())
}

// The two-jump C84/C85 return suggested by the indirect bypass must
// start at encrypted M82, then read M[encrypted M82 + 1]. None of the
// eight graphical C82 cells can land on D95 before C86. This does not
// constrain changes to the earlier prefix or code/data relocation.
#[test]
fn fixed_indirect_c23_tail_has_no_two_jump_converter_return()
-> Result<(), String> {
    let profile = current_profile();
    let source =
        layout::build_c23_nine_rotated_indirect_halt_probe_source(profile)
            .map_err(|error| format!("{error:?}"))?;
    let mut vm =
        ProfileMachine::from_source(profile, &source, vec![0x5a, 0x81])
            .map_err(|error| error.to_string())?;
    assert_eq!(
        vm.run(79).map_err(|error| error.to_string())?,
        RunOutcome::BudgetExhausted { steps: 79 },
    );
    assert_eq!(vm.registers().code_pointer, 79);
    assert_eq!(vm.registers().data_pointer, 80);
    assert_eq!(vm.memory_word(95), Ok(7_138_732));
    assert_eq!(vm.memory_word(96), Ok(121));
    let mut candidates = Vec::new();
    for word in 33..=126u32 {
        if !decode_profile_instruction(word, 82)
            .is_some_and(|opcode| b"oijp*/<v".contains(&opcode))
        {
            continue;
        }
        let encrypted = encrypt_profile_cell(word)
            .ok_or("accepted graphical cell cannot encrypt")?;
        let second_address = encrypted + 1;
        let second_word = vm
            .memory_word(second_address)
            .map_err(|error| error.to_string())?;
        candidates.push((word, second_address, second_word));
        assert_ne!(second_word, 94, "no two-jump return to M95");
    }
    assert_eq!(candidates, [
        (35, 94, 7_174_489),
        (51, 42, 115),
        (52, 73, 100),
        (74, 71, 43),
        (80, 67, 85),
        (93, 99, 7_174_368),
        (110, 127, 7_174_404),
        (111, 121, 7_174_404),
    ],);
    Ok(())
}

// The complete C23 converter consumes its first `/` at C37 before the
// converted second read at C66. C37 is not an erasable discarded read:
// its raw source byte is a loader/pointer word before execution, and
// execution later encrypts that code word for repeated pointer restores.
// Check *every* other one-cell legal opcode at C37 against the strict
// single-getchar C23 effect. This bounds only one-cell C37 replacement,
// not relocated code, a saved first input, or a general guest linker.
#[test]
#[expect(
    clippy::cognitive_complexity,
    clippy::too_many_lines,
    clippy::panic_in_result_fn,
    clippy::excessive_nesting,
    reason = "complete finite guest opcode search and native C23 parity controls"
)]
fn signed_c23_single_read_cannot_replace_only_the_first_input_opcode()
-> Result<(), String> {
    let profile = current_profile();
    let original = layout::build_c23_nine_rotated_signed_output_source(profile)
        .map_err(|error| format!("{error:?}"))?;
    assert_eq!(original.len(), 91);
    assert_eq!(original.get(37), Some(&80));
    let mut baseline =
        ProfileMachine::from_source(profile, &original, vec![0x7b, 2])
            .map_err(|error| error.to_string())?;
    assert_eq!(
        baseline.run(90).map_err(|error| error.to_string())?,
        RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 81,
        }
    );
    assert_eq!(baseline.input_consumed(), 2);
    assert_eq!(baseline.output(), [2]);

    let mut enumerated = 0usize;
    for opcode in b"oijp*<v" {
        let source_byte = (33..=126u8)
            .find(|byte| {
                decode_profile_instruction(u32::from(*byte), 37)
                    == Some(*opcode)
            })
            .ok_or("missing graphical C37 opcode")?;
        let mut candidate = original.clone();
        *candidate.get_mut(37).ok_or("missing C37 source cell")? = source_byte;
        assert_eq!(
            layout::admit_c23_probe_graphical_source(&candidate),
            Ok(())
        );
        assert_ne!(candidate.get(37), original.get(37));
        let loaded =
            ProfileMachine::from_source(profile, &candidate, Vec::new())
                .map_err(|error| error.to_string())?;
        for (input, expected) in [(vec![2], 2u8), (vec![], 255u8)] {
            let mut machine = ProfileMachine::from_state(
                profile,
                loaded.memory().to_vec(),
                input.clone(),
                ProfileRegisters::default(),
            )
            .map_err(|error| error.to_string())?;
            let mut reads = Vec::new();
            let outcome = machine
                .run_traced(90, &mut |step| {
                    if step.input.is_some() {
                        reads.push(step.before.registers.code_pointer);
                    }
                })
                .map_err(|error| error.to_string())?;
            assert!(!reads.contains(&37), "C37 must not read, opcode {opcode}");
            let linked_single_read =
                matches!(outcome, RunOutcome::Terminated {
                    reason: Termination::HaltInstruction,
                    ..
                }) && reads.len() == 1
                    && machine.input_consumed() == input.len()
                    && machine.output() == [expected];
            assert!(
                !linked_single_read,
                "C37 opcode {opcode} incorrectly passed C23 single-read parity"
            );
        }
        enumerated += 1;
    }
    assert_eq!(enumerated, 7);
    Ok(())
}

// The existing two-read converter's C38 runs immediately after the first
// genuine C37 input, with D pointing at the loader's M97=7,174,404. A
// one-cell `p` save there would be a real guest data write, but its
// transformation cannot preserve every signed input: raw bytes 1 and 2
// become the same memory word. Later code cannot reconstruct which arrived.
// This is a bound on *that* early M97 storage route, not on all possible
// single-read C23 conversion or relocated pointer geometry.
#[test]
fn first_signed_read_cannot_be_saved_losslessly_by_one_c38_p()
-> Result<(), String> {
    use std::collections::BTreeSet;

    let profile = current_profile();
    let original = layout::build_c23_nine_rotated_signed_output_source(profile)
        .map_err(|error| format!("{error:?}"))?;
    assert_eq!(original.get(37), Some(&80));
    let mut candidate = original.clone();
    let save_opcode = (33..=126u8)
        .find(|byte| {
            decode_profile_instruction(u32::from(*byte), 38) == Some(b'p')
        })
        .ok_or("C38 lacks graphical p")?;
    *candidate.get_mut(38).ok_or("missing C38")? = save_opcode;
    assert_eq!(layout::admit_c23_probe_graphical_source(&candidate), Ok(()));
    let loaded = ProfileMachine::from_source(profile, &candidate, Vec::new())
        .map_err(|error| error.to_string())?;
    let original_word =
        loaded.memory_word(97).map_err(|error| error.to_string())?;
    assert_eq!(original_word, 7_174_404);

    let distinct_images = (0..=255u32)
        .chain(once(profile.eof_word()))
        .map(|raw| scalar_crazy(original_word, raw))
        .collect::<BTreeSet<_>>();
    assert_eq!(distinct_images.len(), 37, "257 inputs lose identity");
    // A different loader-derived word is injective on the same 257 classes.
    // This is a candidate for future pointer relocation, NOT an executed
    // C38 save or proof that the converter can reach M102.
    let alternate_word =
        loaded.memory_word(102).map_err(|error| error.to_string())?;
    assert_eq!(alternate_word, 121);
    let distinct_alternate = (0..=255u32)
        .chain(once(profile.eof_word()))
        .map(|raw| scalar_crazy(alternate_word, raw))
        .collect::<BTreeSet<_>>();
    assert_eq!(distinct_alternate.len(), 257);

    let mut stored = Vec::new();
    for byte in [1u8, 2] {
        let mut vm = ProfileMachine::from_state(
            profile,
            loaded.memory().to_vec(),
            vec![byte],
            ProfileRegisters::default(),
        )
        .map_err(|error| error.to_string())?;
        let mut trace = Vec::new();
        let outcome = vm
            .run_traced(39, &mut |step| trace.push(*step))
            .map_err(|error| error.to_string())?;
        assert_eq!(outcome, RunOutcome::BudgetExhausted { steps: 39 });
        assert_eq!(trace.len(), 39);
        let read = trace.get(37).ok_or("missing original first read")?;
        assert_eq!(read.before.registers.code_pointer, 37);
        assert_eq!(read.decoded, Some(profile.input_instruction()));
        assert_eq!(read.input, Some(TraceInput::Byte(byte)));
        let write = trace.get(38).ok_or("missing physical p save")?;
        assert_eq!(write.before.registers.code_pointer, 38);
        assert_eq!(write.before.registers.data_pointer, 97);
        assert_eq!(write.decoded, Some(b'p'));
        assert_eq!(
            write
                .memory_reads
                .data
                .map(|read| (read.address, read.value)),
            Some((97, original_word))
        );
        let saved = scalar_crazy(original_word, u32::from(byte));
        assert_eq!(
            write
                .memory_delta
                .data
                .map(|delta| { (delta.address, delta.before, delta.after) }),
            (original_word != saved).then_some((97, original_word, saved))
        );
        assert_eq!(vm.memory_word(97), Ok(saved));
        assert_eq!(vm.input_consumed(), 1);
        stored.push(saved);
    }
    assert_eq!(stored.len(), 2);
    assert_eq!(stored[0], stored[1], "guest save aliases bytes 1 and 2");
    Ok(())
}
