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
//   - Two raw N15 input stores with independently reached physical outputs.
// - Must-Not:
//   - Claim signed-C23 EOF mapping, source-C checksum or executable C CFG.
// - Allows:
//   - Inputs: exact graphical N15 source and finite binary/EOF streams.
//   - Outputs: both actual stores, outputs, scalar parity and bounded halt.
//   - Side effects: isolated normative VM execution only.
// - Split-When:
//   - The source-linked guest input-state writer subsumes the fixed example.
// - Merge-When:
//   - The checksum's loop body implements this reusable physical operation.
// - Summary:
//   - Two live guest inputs each survive a physical state write before echo.

//! Two independently read guest input bytes are stored and echoed physically.

#[path = "../src/compiler/malbolge-layout/composition/lib.rs"]
pub mod layout;

use std::collections::BTreeSet;
use std::iter::once;

use malbolge::{
    ProfileMachine, ProfileMachineError, RunOutcome, Termination, TraceInput,
    current_profile, decode_profile_instruction, historical_profile,
};

#[expect(
    clippy::arithmetic_side_effects,
    clippy::integer_division_remainder_used,
    reason = "independent exhaustive 15-trit truth-table oracle"
)]
fn oracle_crazy(mut data: u32, mut accumulator: u32) -> u32 {
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

fn source_encoding(position: u32, opcode: u8) -> Option<u8> {
    (33..=126u8).find(|byte| {
        decode_profile_instruction(u32::from(*byte), position) == Some(opcode)
    })
}

#[test]
#[expect(
    clippy::expect_used,
    clippy::indexing_slicing,
    clippy::cognitive_complexity,
    clippy::too_many_lines,
    clippy::integer_division_remainder_used,
    reason = "complete real-VM site checks plus bounded negative source changes"
)]
fn independent_inputs_keep_separate_physical_stores_and_outputs() {
    let profile = current_profile();
    let source = layout::build_c23_two_inputs_saved_and_echoed_source(profile)
        .expect("source-loaded two-input state and echo path");
    assert_eq!(
        layout::build_c23_two_inputs_saved_and_echoed_source(
            historical_profile()
        ),
        Err(layout::C23OperandProbeSourceError::UnsupportedProfile)
    );
    assert_eq!(source.len(), 91);
    assert_eq!(source.get(89..), Some(b"Iy".as_slice()));
    layout::admit_c23_probe_graphical_source(&source)
        .expect("exact source loads graphically");
    let first = layout::build_c23_first_input_saved_and_echoed_source(profile)
        .expect("one-input source");
    assert_eq!(source.get(..51), first.get(..51));
    assert_eq!(source.get(64..), first.get(64..));
    for (code, opcode) in [
        (37, b'/'),
        (43, b'p'),
        (49, b'p'),
        (50, b'<'),
        (54, b'/'),
        (55, b'p'),
        (61, b'p'),
        (62, b'<'),
        (63, b'v'),
    ] {
        assert_eq!(
            decode_profile_instruction(
                u32::from(source[code]),
                u32::try_from(code).expect("bounded site")
            ),
            Some(opcode)
        );
    }
    for code in [51usize, 52, 53, 56, 57, 58, 59, 60] {
        assert_eq!(
            decode_profile_instruction(
                u32::from(source[code]),
                u32::try_from(code).expect("bounded site")
            ),
            Some(b'o')
        );
    }

    let mut encoded = BTreeSet::new();
    for raw in (0..=255).chain(once(profile.eof_word())) {
        let saved = oracle_crazy(121, raw);
        assert!(encoded.insert(saved));
        let restored = oracle_crazy(121, saved);
        assert_eq!(
            restored,
            if raw == profile.eof_word() {
                7_174_574
            } else {
                raw
            }
        );
    }
    assert_eq!(encoded.len(), 257);
    let pristine = ProfileMachine::from_source(profile, &source, vec![])
        .expect("the normative VM must admit this source");
    for address in [126, 132, 138, 144] {
        assert_eq!(pristine.memory_word(address), Ok(121));
    }
    for input in [
        vec![],
        vec![0],
        vec![255],
        vec![0, 0],
        vec![0, 255],
        vec![255, 0],
        vec![255, 255],
        vec![1, 2, 3],
        vec![2, 1],
        vec![0x80, 0x7f],
        vec![0x7f, 0x80],
        vec![3, 4],
    ] {
        let mut vm = pristine
            .fork_with_input(input.clone())
            .expect("fresh input");
        let mut trace = Vec::new();
        assert_eq!(
            vm.run_traced(64, &mut |step| trace.push(*step)),
            Ok(RunOutcome::Terminated {
                reason: Termination::HaltInstruction,
                steps: 64,
            }),
            "stdin={input:?}"
        );
        assert_eq!(trace.len(), 64);
        assert_eq!(vm.input_consumed(), input.len().min(2));
        let raw_first = input
            .first()
            .map_or_else(|| profile.eof_word(), |byte| u32::from(*byte));
        let raw_second = input
            .get(1)
            .map_or_else(|| profile.eof_word(), |byte| u32::from(*byte));
        let saved_first = oracle_crazy(121, raw_first);
        let saved_second = oracle_crazy(121, raw_second);
        let echoed_first = oracle_crazy(121, saved_first);
        let echoed_second = oracle_crazy(121, saved_second);
        for (site, word) in [(37, raw_first), (54, raw_second)] {
            assert_eq!(trace[site].decoded, Some(b'/'));
            assert_eq!(trace[site].after.registers.accumulator, word);
        }
        assert_eq!(
            trace[37].input,
            Some(input.first().map_or(TraceInput::EndOfInput, |byte| {
                TraceInput::Byte(*byte)
            }))
        );
        assert_eq!(
            trace[54].input,
            Some(input.get(1).map_or(TraceInput::EndOfInput, |byte| {
                TraceInput::Byte(*byte)
            }))
        );
        assert_eq!(trace.iter().filter(|step| step.input.is_some()).count(), 2);
        for (code, address, result) in [
            (43, 126, saved_first),
            (49, 132, echoed_first),
            (55, 138, saved_second),
            (61, 144, echoed_second),
        ] {
            assert_eq!(trace[code].decoded, Some(b'p'));
            assert_eq!(
                trace[code]
                    .memory_reads
                    .data
                    .map(|read| (read.address, read.value)),
                Some((address, 121))
            );
            assert_eq!(
                trace[code]
                    .memory_delta
                    .data
                    .map(|w| (w.address, w.before, w.after)),
                Some((address, 121, result))
            );
            assert_eq!(vm.memory_word(address), Ok(result));
        }
        for (code, echoed) in [(50, echoed_first), (62, echoed_second)] {
            assert_eq!(trace[code].decoded, Some(b'<'));
            assert_eq!(
                trace[code].output,
                Some(u8::try_from(echoed % 256).expect("low byte"))
            );
        }
        assert_eq!(vm.output(), [
            u8::try_from(echoed_first % 256).expect("low byte"),
            u8::try_from(echoed_second % 256).expect("low byte")
        ]);
        assert_eq!(trace[63].decoded, Some(b'v'));
        assert_eq!(trace[63].memory_delta.encryption, None);
    }
    // Source-valid mutations break only the second input's physical dependency.
    for removed in [54u32, 55, 61] {
        let mut changed = source.clone();
        changed[usize::try_from(removed).expect("bounded site")] =
            source_encoding(removed, b'o').expect("graphical o");
        let mut vm =
            ProfileMachine::from_source(profile, &changed, vec![3, 255])
                .expect("negative source still loads");
        assert_eq!(
            vm.run(64),
            Ok(RunOutcome::Terminated {
                reason: Termination::HaltInstruction,
                steps: 64,
            })
        );
        assert_eq!(vm.output().first(), Some(&3));
        assert_ne!(vm.output().get(1), Some(&255));
    }
}

// The source C67=125 is an early C42 data-pointer operand; it must remain
// unchanged for the original real M126 store. At its code phase C67 decodes
// to `i`, not `j`. A naive four-no-op fallthrough after the two outputs
// therefore enters an expanded, invalid code target instead of jumping back
// to read M126. This is a local branch-linkage refusal, not an impossibility
// theorem about source-C EOF or an alternate program layout.
#[test]
#[expect(
    clippy::expect_used,
    clippy::indexing_slicing,
    reason = "bounded real source-loader indirect continuation failure"
)]
fn first_state_cannot_be_reentered_via_unchanged_c67_control() {
    let profile = current_profile();
    let mut source =
        layout::build_c23_two_inputs_saved_and_echoed_source(profile)
            .expect("already proven two-input source");
    for position in 63..=66 {
        source[position] = source_encoding(
            u32::try_from(position).expect("bounded code site"),
            b'o',
        )
        .expect("graphical no-op");
    }
    assert_eq!(source[67], 125);
    assert_eq!(decode_profile_instruction(125, 67), Some(b'i'));
    assert_eq!(decode_profile_instruction(157, 122), None);
    layout::admit_c23_probe_graphical_source(&source)
        .expect("modified source remains loader-valid");
    for stdin in [vec![], vec![3, 4], vec![255, 0]] {
        let mut vm =
            ProfileMachine::from_source(profile, &source, stdin.clone())
                .expect("valid graphical VM source");
        let mut trace = Vec::new();
        assert_eq!(
            vm.run_traced(80, &mut |step| trace.push(*step)),
            Err(ProfileMachineError::InvalidEncryptionTarget {
                pointer: 121,
                value: 7_174_404,
            })
        );
        assert_eq!(vm.input_consumed(), stdin.len().min(2));
        assert_eq!(trace.last().map(|step| step.decoded), Some(Some(b'i')));
        assert_eq!(
            trace.last().map(|step| step.before.registers.code_pointer),
            Some(67)
        );
        assert_eq!(
            trace
                .last()
                .and_then(|step| step.memory_reads.data)
                .map(|read| (read.address, read.value)),
            Some((150, 121))
        );
        let expected = stdin
            .iter()
            .map(|byte| *byte)
            .chain(std::iter::repeat_n(174u8, 2))
            .take(2)
            .collect::<Vec<_>>();
        assert_eq!(vm.output(), expected);
    }
}
