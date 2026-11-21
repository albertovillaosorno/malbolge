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
//   - Normative signed-byte conversion followed by real guest state folding.
// - Must-Not:
//   - Treat an encoded M96 word as signed C32 or an EOF checksum compiler.
// - Allows:
//   - Inputs: all 256 signed byte classes plus true EOF, and unread suffix.
//   - Outputs: real input, both conversion writes, final fold and exact output.
//   - Side effects: isolated 82-step profile VM executions only.
// - Split-When:
//   - A general physical typed-C32 arithmetic linker replaces this probe.
// - Merge-When:
//   - Whole source-C checksum is independently VM-verified.
// - Summary:
//   - Distinguishes full converted state from lossy post-output folding.

//! A reached third physical crazy write after correct signed C23 byte output.

#[path = "../src/compiler/malbolge-layout/composition/lib.rs"]
pub mod layout;

use std::collections::BTreeSet;

use malbolge::{
    ProfileMachine, ProfileRegisters, RunOutcome, Termination, TraceInput,
    current_profile, decode_profile_instruction, historical_profile,
};

const ROTATED: u32 = 7_138_732;
const NEXT_SEED: u32 = 121;
const TRIT_SIX: u32 = 729;
const FOLD_SEED: u32 = 157;
const UNTOUCHED_POINTER: u32 = 7_174_404;

// Independent trit table, not the production profile crazy primitive.
#[expect(
    clippy::arithmetic_side_effects,
    clippy::integer_division_remainder_used,
    reason = "independent fixed-width 15-trit arithmetic oracle"
)]
fn scalar_crazy(mut data: u32, mut accumulator: u32) -> u32 {
    const TABLE: [[u32; 3]; 3] = [[1, 0, 0], [1, 0, 2], [2, 2, 1]];
    let mut result = 0;
    let mut place = 1;
    for _ in 0..15 {
        result +=
            TABLE[(data % 3) as usize][(accumulator % 3) as usize] * place;
        data /= 3;
        accumulator /= 3;
        place *= 3;
    }
    result
}

#[test]
#[expect(
    clippy::cognitive_complexity,
    clippy::too_many_lines,
    clippy::panic_in_result_fn,
    reason = "exact guest effect and 257-class state parity assertions"
)]
fn signed_c23_conversion_preserves_state_through_post_output_guest_fold()
-> Result<(), String> {
    let profile = current_profile();
    let source =
        layout::build_c23_signed_output_with_post_conversion_fold_source(
            profile,
        )
        .map_err(|error| format!("{error:?}"))?;
    let original = layout::build_c23_nine_rotated_signed_output_source(profile)
        .map_err(|error| format!("{error:?}"))?;
    assert_eq!(source.len(), 91);
    assert_eq!(&source[89..], b"Iy");
    assert_eq!(source[81], 94);
    assert_eq!(layout::admit_c23_probe_graphical_source(&source), Ok(()));
    assert_eq!(
        layout::build_c23_signed_output_with_post_conversion_fold_source(
            historical_profile(),
        ),
        Err(layout::C23OperandProbeSourceError::UnsupportedProfile)
    );
    assert_eq!(
        source
            .iter()
            .zip(&original)
            .enumerate()
            .filter(|(_, (after, before))| after != before)
            .map(|(index, _)| index)
            .collect::<Vec<_>>(),
        vec![80]
    );
    assert_eq!(
        decode_profile_instruction(u32::from(source[80]), 80),
        Some(b'p')
    );

    let loaded = ProfileMachine::from_source(profile, &source, vec![])
        .map_err(|error| error.to_string())?;
    assert_eq!(loaded.memory_word(96), Ok(NEXT_SEED));
    assert_eq!(loaded.memory_word(98), Ok(FOLD_SEED));
    assert_eq!(loaded.memory_word(97), Ok(UNTOUCHED_POINTER));
    let mut all_converted = BTreeSet::new();
    let mut all_folded = BTreeSet::new();
    let all_inputs = (0u8..=255).map(Some).chain(std::iter::once(None));
    for second in all_inputs {
        let raw = second.map_or(profile.eof_word(), u32::from);
        let converted = scalar_crazy(NEXT_SEED, scalar_crazy(ROTATED, raw));
        assert_eq!(converted % 256, u32::from(second.unwrap_or(255)));
        match second {
            Some(byte) => {
                // Correct full-word successful-byte normalization, not
                // merely output modulo 256.
                assert_eq!(converted, u32::from(byte));
                assert_eq!((converted / TRIT_SIX) % 3, 0);
            },
            None => {
                // EOF is a distinct *encoded* word, not C23 -1.
                assert_eq!(converted, 62_207);
                assert_eq!((converted / TRIT_SIX) % 3, 1);
            },
        }
        _ = all_converted.insert(converted);
        _ = all_folded.insert(scalar_crazy(FOLD_SEED, converted));
    }
    // Byte 0xff and true EOF emit the same low byte, but require different
    // persistent guest state; a byte-only approximation loses source meaning.
    let high = scalar_crazy(NEXT_SEED, scalar_crazy(ROTATED, 255));
    let eof =
        scalar_crazy(NEXT_SEED, scalar_crazy(ROTATED, profile.eof_word()));
    assert_eq!((high % 256, eof % 256), (255, 255));
    assert_ne!(high, eof);
    // The seventh ternary digit alone separates all successful bytes
    // from encoded EOF before or after the additional physical crazy.
    assert_eq!((high / TRIT_SIX) % 3, 0);
    assert_eq!((eof / TRIT_SIX) % 3, 1);
    assert_eq!((scalar_crazy(FOLD_SEED, high) / TRIT_SIX) % 3, 1);
    assert_eq!((scalar_crazy(FOLD_SEED, eof) / TRIT_SIX) % 3, 0);
    let eof_folded = scalar_crazy(FOLD_SEED, eof);
    assert_eq!(eof_folded, 7_112_573);
    assert!((0..=255).all(|byte| {
        let converted = scalar_crazy(NEXT_SEED, scalar_crazy(ROTATED, byte));
        scalar_crazy(FOLD_SEED, converted) != eof_folded
    }));
    // Pin independent algebra for all 257 classes; run a finite set of
    // distinct input/EOF cases on the costly 14M-word normative guest VM.
    for second in [
        None,
        Some(0),
        Some(1),
        Some(2),
        Some(0x7f),
        Some(0x80),
        Some(0xfe),
        Some(0xff),
    ] {
        let mut input = vec![0x5a];
        if let Some(byte) = second {
            input.extend_from_slice(&[byte, 0x39]);
        }
        let raw = second.map_or(profile.eof_word(), u32::from);
        let after_first = scalar_crazy(ROTATED, raw);
        let converted = scalar_crazy(NEXT_SEED, after_first);
        let folded = scalar_crazy(FOLD_SEED, converted);
        let expected = second.unwrap_or(0xff);
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
        assert_eq!(trace[37].input, Some(TraceInput::Byte(0x5a)));
        assert_eq!(
            trace[66].input,
            Some(second.map_or(TraceInput::EndOfInput, TraceInput::Byte))
        );
        for (position, address, before, after) in [
            (77, 95, ROTATED, after_first),
            (78, 96, NEXT_SEED, converted),
            (80, 98, FOLD_SEED, folded),
        ] {
            let step = &trace[position];
            assert_eq!(step.decoded, Some(b'p'));
            assert_eq!(step.before.registers.data_pointer, address);
            assert_eq!(
                step.memory_reads
                    .data
                    .map(|read| (read.address, read.value)),
                Some((address, before))
            );
            assert_eq!(step.after.registers.accumulator, after);
            assert_eq!(
                step.memory_delta.data.map(|delta| {
                    (delta.address, delta.before, delta.after)
                }),
                (before != after).then_some((address, before, after))
            );
            assert_eq!(vm.memory_word(address), Ok(after));
        }
        assert_eq!(trace[79].output, Some(expected));
        assert_eq!(trace[80].before.registers.accumulator, converted);
        assert_eq!(trace[81].decoded, Some(b'v'));
        assert_eq!(vm.output(), &[expected]);
        assert_eq!(vm.memory_word(97), Ok(UNTOUCHED_POINTER));
        assert_eq!(vm.input_consumed(), 1 + usize::from(second.is_some()));
    }
    // The converted physical word in M96 retains byte-plus-EOF state, but
    // the new M98 crazy fold cannot replace signed C23 scalar storage.
    assert_eq!(all_converted.len(), 257);
    assert_eq!(all_folded.len(), 118);
    Ok(())
}

// Data-only control placement must not be mistaken for an actual dynamic C23
// EOF branch. The preceding VM test authenticates the input word at M96;
// this test proves a later two-p selector over that exact value space.
#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "exact independent finite expected bytes and EOF scalar result"
)]
fn iy_converted_guest_word_has_source_specific_eof_selector()
-> Result<(), String> {
    use layout::{
        C23EofControlWordError, CURRENT_IY_CONVERTED_EOF_CONTROL_WORDS,
        CURRENT_IY_CONVERTED_EOF_TARGET_WORDS,
        admit_c23_iy_converted_eof_control_word_plan,
    };

    let profile = current_profile();
    let control = CURRENT_IY_CONVERTED_EOF_CONTROL_WORDS;
    let targets = CURRENT_IY_CONVERTED_EOF_TARGET_WORDS;
    let plan =
        admit_c23_iy_converted_eof_control_word_plan(profile, control, targets)
            .map_err(|error| format!("{error:?}"))?;
    assert_eq!(plan.operands(), [14_348_097, 80]);
    assert_eq!(plan.targets(), [80, 809]);
    assert_eq!(plan.next_code_addresses(), [81, 810]);
    assert_eq!(plan.mandatory_runtime_operand_writes(), [true, false]);
    // The same targets are NOT a valid selector on raw guest input.
    // Skipping the real converter must never be silently authorized.
    assert!(
        layout::admit_c23_eof_control_word_plan(profile, control, targets)
            .is_err()
    );
    assert!(
        admit_c23_iy_converted_eof_control_word_plan(
            profile,
            layout::CURRENT_C23_EOF_CONTROL_WORDS,
            layout::CURRENT_C23_EOF_TARGET_WORDS,
        )
        .is_err()
    );
    for raw in (0..=255).chain(std::iter::once(profile.eof_word())) {
        let converted = scalar_crazy(NEXT_SEED, scalar_crazy(ROTATED, raw));
        let actual =
            scalar_crazy(control[1], scalar_crazy(control[0], converted));
        assert_eq!(
            actual,
            if raw == profile.eof_word() {
                809
            } else {
                80
            },
            "raw N15 input class {raw}"
        );
    }
    assert_eq!(
        admit_c23_iy_converted_eof_control_word_plan(
            historical_profile(),
            control,
            targets,
        ),
        Err(C23EofControlWordError::UnsupportedProfile)
    );
    assert_eq!(
        admit_c23_iy_converted_eof_control_word_plan(
            profile,
            [profile.word_modulus(), control[1]],
            targets,
        ),
        Err(C23EofControlWordError::InvalidOperand)
    );
    assert_eq!(
        admit_c23_iy_converted_eof_control_word_plan(profile, control, [
            80, 80
        ],),
        Err(C23EofControlWordError::IndistinguishableTargets)
    );
    assert_eq!(
        admit_c23_iy_converted_eof_control_word_plan(profile, control, [
            80, 810
        ],),
        Err(C23EofControlWordError::EofMismatch { actual: 809 })
    );
    assert!(
        admit_c23_iy_converted_eof_control_word_plan(
            profile,
            [control[0] - 1, control[1]],
            targets,
        )
        .is_err()
    );
    // Hypothetical landing pad C810 lies beyond the physical 91-cell Iy
    // source. A future target linker must actually synthesize the huge
    // first operand, place both p sites, skip C81 and prove the i branch.
    Ok(())
}

// For the converted guest representation, every low-six-trit value of EOF
// occurs in a successful byte at that same digit. A ternary crazy cascade
// never moves information between trit columns. Consequently any selector
// that collapses all 256 byte results to one word must preserve the same
// six least-significant target trits for EOF. Distinct jump words must be
// separated by a multiple of 3^6=729, not by one nearby code position.
#[test]
#[expect(
    clippy::integer_division_remainder_used,
    clippy::arithmetic_side_effects,
    reason = "finite base-three independent local lower-bound proof"
)]
fn converted_eof_trit_local_branch_requires_distant_jump_targets() {
    const EOF_CONVERTED: u32 = 62_207;
    let trit = |data: u32, input: u32| -> u32 {
        match (data, input) {
            (0 | 1, 0) | (2, 2) => 1,
            (1, 2) | (2, 0 | 1) => 2,
            _ => 0,
        }
    };
    for exponent in 0..6 {
        let place = 3u32.pow(exponent);
        let successful_digits = (0..=255)
            .map(|byte| (byte / place) % 3)
            .collect::<BTreeSet<_>>();
        let eof_digit = (EOF_CONVERTED / place) % 3;
        assert!(successful_digits.contains(&eof_digit));
        for first in 0..3 {
            for second in 0..3 {
                let mapped_bytes = successful_digits
                    .iter()
                    .map(|byte| trit(second, trit(first, *byte)))
                    .collect::<BTreeSet<_>>();
                if mapped_bytes.len() == 1 {
                    assert!(
                        mapped_bytes
                            .contains(&trit(second, trit(first, eof_digit),))
                    );
                }
            }
        }
    }
    let targets = layout::CURRENT_IY_CONVERTED_EOF_TARGET_WORDS;
    assert_eq!(targets[0] % TRIT_SIX, targets[1] % TRIT_SIX);
    assert_eq!(targets[1] - targets[0], TRIT_SIX);
}
