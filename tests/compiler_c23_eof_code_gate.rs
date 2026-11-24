// Copyright:
//   - Copyright © 2026 Alberto Villa Osorno.
// SPDX-License-Identifier: Apache-2.0
// Confidential:
//   - false
// License-File:
//   - LICENSE
//
// Boundary-Contract:
// - Owns:
//   - Authentic one-revisit N15 input, output, self-encryption and halt.
// - Must-Not:
//   - Claim an EOF conditional, C23 conversion or source-C checksum loop.
// - Allows:
//   - Inputs: exact graphical N15 source and finite binary/EOF streams.
//   - Outputs: reached guest backedge, trace, output and valid halt.
//   - Side effects: isolated normative VM execution only.
// - Split-When:
//   - The guest source-C control linker subsumes this fixed physical route.
// - Merge-When:
//   - A reusable, independently verified guest branch primitive exists.
// - Summary:
//   - Revisit an encrypted input instruction as a legitimate halt.

//! A real guest control backedge returns to a prior encrypted input as `v`.

#[path = "../src/compiler/malbolge-layout/composition/lib.rs"]
pub mod layout;

use std::collections::BTreeSet;
use std::iter::once;

use malbolge::{
    ProfileMachine, RunOutcome, Termination, TraceInput, current_profile,
    decode_profile_instruction, encrypt_profile_cell,
};

fn source_encoding(position: u32, opcode: u8) -> Option<u8> {
    (33..=126u8).find(|byte| {
        decode_profile_instruction(u32::from(*byte), position) == Some(opcode)
    })
}

#[expect(
    clippy::expect_used,
    clippy::indexing_slicing,
    reason = "frozen 101-cell source layout"
)]
fn one_revisit_input_halt_source() -> Vec<u8> {
    let mut source = (0..101u32)
        .map(|position| {
            source_encoding(position, b'o').expect("graphical source no-op")
        })
        .collect::<Vec<_>>();
    for (position, opcode) in [
        (59u32, b'j'),
        (82, b'/'),
        (83, b'<'),
        (84, b'j'),
        (85, b'i'),
    ] {
        source[usize::try_from(position).expect("in-range source position")] =
            source_encoding(position, opcode).expect("graphical opcode");
    }
    // Both pointer words must also be legal source opcodes at their OWN
    // positions, although neither is executed on the successful path.
    // C59 j selects D=75, so C84 j sees virgin M100=93. C85 i then
    // reads virgin M94=81 and enters C82, already encrypted to `v`.
    source[94] = 81;
    source[100] = 93;
    layout::admit_c23_probe_graphical_source(&source)
        .expect("strict source-opcode admission");
    source
}

#[test]
#[expect(
    clippy::expect_used,
    clippy::indexing_slicing,
    clippy::integer_division_remainder_used,
    clippy::too_many_lines,
    clippy::cognitive_complexity,
    reason = "complete physical instruction and side-effect trace"
)]
fn genuine_input_backedge_enters_its_encrypted_halt() {
    let profile = current_profile();
    let source = one_revisit_input_halt_source();
    assert_eq!(source.len(), 101);
    assert_eq!(source[59], 75);
    assert_eq!(source[82], 35);
    assert_eq!(source[83], 110);
    assert_eq!(source[84], 50);
    assert_eq!(source[85], 107);
    assert_eq!(source[94], 81);
    assert_eq!(source[100], 93);
    assert_eq!(decode_profile_instruction(81, 94), Some(b'v'));
    assert_eq!(decode_profile_instruction(93, 100), Some(b'<'));
    assert_eq!(encrypt_profile_cell(35), Some(93));
    assert_eq!(decode_profile_instruction(93, 82), Some(b'v'));

    let pristine = ProfileMachine::from_source(profile, &source, vec![])
        .expect("strict normative N15 source loader");
    for input in [
        vec![],
        vec![0],
        vec![255],
        vec![0, 255],
        vec![255, 0],
        vec![0x7f, 0x80],
    ] {
        let mut vm = pristine
            .fork_with_input(input.clone())
            .expect("fresh input");
        let mut trace = Vec::new();
        assert_eq!(
            vm.run_traced(100, &mut |step| trace.push(*step)),
            Ok(RunOutcome::Terminated {
                reason: Termination::HaltInstruction,
                steps: 87,
            }),
            "stdin={input:?}"
        );
        assert_eq!(trace.len(), 87);
        assert_eq!(vm.input_consumed(), usize::from(!input.is_empty()));
        let observed_byte = input.first().copied().unwrap_or_else(|| {
            u8::try_from(profile.eof_word() % 256).expect("N15 EOF low byte")
        });
        assert_eq!(vm.output(), [observed_byte]);
        for (step, code, opcode) in [
            (59, 59, b'j'),
            (82, 82, b'/'),
            (83, 83, b'<'),
            (84, 84, b'j'),
            (85, 85, b'i'),
            (86, 82, b'v'),
        ] {
            assert_eq!(trace[step].before.registers.code_pointer, code);
            assert_eq!(trace[step].decoded, Some(opcode));
        }
        assert_eq!(
            trace[59]
                .memory_reads
                .data
                .map(|read| (read.address, read.value)),
            Some((59, 75))
        );
        assert_eq!(
            trace[84]
                .memory_reads
                .data
                .map(|read| (read.address, read.value)),
            Some((100, 93))
        );
        assert_eq!(
            trace[85]
                .memory_reads
                .data
                .map(|read| (read.address, read.value)),
            Some((94, 81))
        );
        assert_eq!(
            trace[82].input,
            Some(input.first().map_or(TraceInput::EndOfInput, |byte| {
                TraceInput::Byte(*byte)
            }))
        );
        assert_eq!(trace[83].output, Some(observed_byte));
        assert_eq!(
            trace[86]
                .memory_reads
                .fetch
                .map(|read| (read.address, read.value)),
            Some((82, 93))
        );
        assert_eq!(trace[86].memory_delta.encryption, None);
        assert_eq!(vm.memory_word(82), Ok(93));
        assert_eq!(vm.memory_word(94), Ok(81));
        assert_eq!(vm.memory_word(100), Ok(93));
    }
}

#[test]
#[expect(
    clippy::expect_used,
    clippy::integer_division_remainder_used,
    reason = "exhaustive 257-class N15 raw input witness"
)]
fn one_revisit_halt_is_independent_of_byte_and_eof() {
    let profile = current_profile();
    let source = one_revisit_input_halt_source();
    let pristine = ProfileMachine::from_source(profile, &source, vec![])
        .expect("graphical source loader");
    for raw in (0..=255u32).chain(once(profile.eof_word())) {
        let input = if raw == profile.eof_word() {
            vec![]
        } else {
            vec![u8::try_from(raw).expect("byte")]
        };
        let mut vm = pristine.fork_with_input(input).expect("fresh input");
        assert_eq!(
            vm.run(90),
            Ok(RunOutcome::Terminated {
                reason: Termination::HaltInstruction,
                steps: 87,
            }),
            "raw={raw}"
        );
        assert_eq!(vm.output(), [u8::try_from(raw % 256).expect("low byte")]);
    }
}

#[expect(
    clippy::expect_used,
    clippy::indexing_slicing,
    reason = "frozen 135-cell source"
)]
fn two_saved_reads_with_valid_reentry_halt_source() -> Vec<u8> {
    let mut source = one_revisit_input_halt_source();
    source.extend((101..135u32).map(|position| {
        source_encoding(position, b'o').expect("graphical suffix no-op")
    }));
    // C10 reads the first physical byte and C11 outputs it. The C29 j
    // selects D=105, so C30 p writes its lossless representation to
    // virgin, source-valid M106=121. A separate C58 j reads M134=58
    // to return D to C59 for the existing authenticated pointer chain.
    for (position, opcode) in [
        (10u32, b'/'),
        (11, b'<'),
        (29, b'j'),
        (30, b'p'),
        (58, b'j'),
    ] {
        source[usize::try_from(position).expect("small code position")] =
            source_encoding(position, opcode).expect("graphical opcode");
    }
    source[106] = 121;
    source[134] = 58;
    layout::admit_c23_probe_graphical_source(&source)
        .expect("strict 135-cell graphical source");
    source
}

#[expect(
    clippy::arithmetic_side_effects,
    clippy::integer_division_remainder_used,
    reason = "independent 15-trit scalar crazy witness"
)]
fn independent_crazy(mut data: u32, mut accumulator: u32) -> u32 {
    let mut value = 0u32;
    let mut place = 1u32;
    for _ in 0..15u8 {
        let digit = match (data % 3, accumulator % 3) {
            (0 | 1, 0) | (2, 2) => 1,
            (1, 2) | (2, 0 | 1) => 2,
            _ => 0,
        };
        value += digit * place;
        data /= 3;
        accumulator /= 3;
        place *= 3;
    }
    value
}

#[test]
#[expect(
    clippy::expect_used,
    clippy::indexing_slicing,
    clippy::integer_division_remainder_used,
    clippy::too_many_lines,
    clippy::cognitive_complexity,
    reason = "two signed input VM traces and physical saved-state oracle"
)]
fn two_real_inputs_preserve_first_store_through_valid_reentry_halt() {
    let profile = current_profile();
    let source = two_saved_reads_with_valid_reentry_halt_source();
    assert_eq!(source.len(), 135);
    for (position, code, opcode) in [
        (10, source[10], b'/'),
        (11, source[11], b'<'),
        (29, 105, b'j'),
        (30, source[30], b'p'),
        (58, source[58], b'j'),
        (59, 75, b'j'),
        (82, 35, b'/'),
        (83, 110, b'<'),
        (84, 50, b'j'),
        (85, 107, b'i'),
        (94, 81, b'v'),
        (100, 93, b'<'),
        (106, 121, b'*'),
        (134, 58, b'i'),
    ] {
        assert_eq!(source[position], code);
        assert_eq!(
            decode_profile_instruction(
                u32::from(code),
                u32::try_from(position).expect("bounded")
            ),
            Some(opcode)
        );
    }
    let pristine = ProfileMachine::from_source(profile, &source, vec![])
        .expect("normative N15 loader");
    assert_eq!(pristine.memory_word(106), Ok(121));
    assert_eq!(pristine.memory_word(134), Ok(58));

    for input in [
        vec![],
        vec![0],
        vec![255],
        vec![0, 0],
        vec![0, 255],
        vec![255, 0],
        vec![255, 255],
        vec![3, 4, 5],
        vec![0x80, 0x7f],
        vec![0x7f, 0x80],
    ] {
        let mut vm = pristine
            .fork_with_input(input.clone())
            .expect("fresh input");
        let mut trace = Vec::new();
        assert_eq!(
            vm.run_traced(90, &mut |step| trace.push(*step)),
            Ok(RunOutcome::Terminated {
                reason: Termination::HaltInstruction,
                steps: 87,
            }),
            "stdin={input:?}"
        );
        assert_eq!(vm.input_consumed(), input.len().min(2));
        let first = input
            .first()
            .map_or_else(|| profile.eof_word(), |byte| u32::from(*byte));
        let second = input
            .get(1)
            .map_or_else(|| profile.eof_word(), |byte| u32::from(*byte));
        assert_eq!(vm.output(), [
            u8::try_from(first % 256).expect("byte"),
            u8::try_from(second % 256).expect("byte"),
        ]);
        for (step, code, opcode) in [
            (10, 10, b'/'),
            (11, 11, b'<'),
            (29, 29, b'j'),
            (30, 30, b'p'),
            (58, 58, b'j'),
            (59, 59, b'j'),
            (82, 82, b'/'),
            (83, 83, b'<'),
            (84, 84, b'j'),
            (85, 85, b'i'),
            (86, 82, b'v'),
        ] {
            assert_eq!(trace[step].before.registers.code_pointer, code);
            assert_eq!(trace[step].decoded, Some(opcode));
        }
        assert_eq!(
            trace[10].input,
            Some(input.first().map_or(TraceInput::EndOfInput, |byte| {
                TraceInput::Byte(*byte)
            }))
        );
        assert_eq!(
            trace[82].input,
            Some(input.get(1).map_or(TraceInput::EndOfInput, |byte| {
                TraceInput::Byte(*byte)
            }))
        );
        assert_eq!(
            trace[30]
                .memory_reads
                .data
                .map(|read| (read.address, read.value)),
            Some((106, 121))
        );
        assert_eq!(
            trace[30]
                .memory_delta
                .data
                .map(|w| (w.address, w.before, w.after)),
            Some((106, 121, independent_crazy(121, first)))
        );
        for (step, address, value) in [
            (29, 29, 105),
            (58, 134, 58),
            (59, 59, 75),
            (84, 100, 93),
            (85, 94, 81),
        ] {
            assert_eq!(
                trace[step]
                    .memory_reads
                    .data
                    .map(|read| (read.address, read.value)),
                Some((address, value))
            );
        }
        assert_eq!(vm.memory_word(106), Ok(independent_crazy(121, first)));
        assert_eq!(
            trace[86]
                .memory_reads
                .fetch
                .map(|read| (read.address, read.value)),
            Some((82, 93))
        );
        assert_eq!(trace[86].memory_delta.encryption, None);
    }
}

#[test]
#[expect(
    clippy::expect_used,
    clippy::integer_division_remainder_used,
    clippy::cognitive_complexity,
    reason = "257-class input sweeps"
)]
fn two_saved_reads_prove_both_input_marginals_and_injectivity() {
    let profile = current_profile();
    let source = two_saved_reads_with_valid_reentry_halt_source();
    let pristine = ProfileMachine::from_source(profile, &source, vec![])
        .expect("normative N15 source loader");
    let mut distinct = BTreeSet::new();
    for raw in (0..=255u32).chain(once(profile.eof_word())) {
        let first = if raw == profile.eof_word() {
            vec![]
        } else {
            vec![u8::try_from(raw).expect("byte")]
        };
        let mut vm = pristine.fork_with_input(first).expect("first-input case");
        assert_eq!(
            vm.run(90),
            Ok(RunOutcome::Terminated {
                reason: Termination::HaltInstruction,
                steps: 87
            })
        );
        assert_eq!(vm.output(), [
            u8::try_from(raw % 256).expect("byte"),
            u8::try_from(profile.eof_word() % 256).expect("raw EOF low byte")
        ]);
        let saved = vm.memory_word(106).expect("saved first input");
        assert_eq!(saved, independent_crazy(121, raw));
        assert!(
            distinct.insert(saved),
            "raw={raw} maps to a duplicate saved word"
        );
        let second = if raw == profile.eof_word() {
            vec![3]
        } else {
            vec![3, u8::try_from(raw).expect("byte")]
        };
        let mut second_vm =
            pristine.fork_with_input(second).expect("second-input case");
        assert_eq!(
            second_vm.run(90),
            Ok(RunOutcome::Terminated {
                reason: Termination::HaltInstruction,
                steps: 87
            })
        );
        assert_eq!(second_vm.output(), [
            3,
            u8::try_from(raw % 256).expect("byte")
        ]);
        assert_eq!(second_vm.memory_word(106), Ok(independent_crazy(121, 3)));
    }
    assert_eq!(distinct.len(), 257);
}

// A code cell and each of the three later pointer operands are separately
// necessary. All mutations retain strict graphical source admission. They
// must not be misreported as either C23 state support or a valid guest loop.
#[test]
#[expect(
    clippy::expect_used,
    clippy::indexing_slicing,
    reason = "14 source-valid guest mutations"
)]
fn removing_any_required_transfer_read_store_or_pointer_breaks_witness() {
    let profile = current_profile();
    let original = two_saved_reads_with_valid_reentry_halt_source();
    let expected_store = independent_crazy(121, 3);
    for position in [
        10usize, 11, 29, 30, 58, 59, 82, 83, 84, 85, 94, 100, 106, 134,
    ] {
        let mut changed = original.clone();
        changed[position] = source_encoding(
            u32::try_from(position).expect("bounded position"),
            b'o',
        )
        .expect("replacement no-op remains source-valid");
        layout::admit_c23_probe_graphical_source(&changed)
            .expect("mutation remains admitted to the N15 loader");
        let mut vm = ProfileMachine::from_source(profile, &changed, vec![3, 4])
            .expect("source-valid mutation loads");
        let result = vm.run(100);
        assert!(
            result
                != Ok(RunOutcome::Terminated {
                    reason: Termination::HaltInstruction,
                    steps: 87,
                })
                || vm.output() != [3, 4]
                || vm.input_consumed() != 2
                || vm.memory_word(106) != Ok(expected_store),
            "removing C{position} falsely preserves the complete guest witness"
        );
    }
}
