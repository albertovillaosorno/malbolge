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
    ProfileMachine, ProfileMachineError, ProfileStepTrace, RunOutcome,
    Termination, TraceInput, current_profile, decode_profile_instruction,
    historical_profile,
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
    for (position, cell) in source.iter_mut().enumerate().take(67).skip(63) {
        *cell = source_encoding(
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
        assert_fixed_c67_invalid_reentry(&source, &stdin);
    }
}

#[expect(clippy::expect_used, reason = "three finite actual VM cases")]
fn assert_fixed_c67_invalid_reentry(source: &[u8], stdin: &[u8]) {
    let profile = current_profile();
    let mut vm = ProfileMachine::from_source(profile, source, stdin.to_vec())
        .expect("valid graphical VM source");
    let mut trace = Vec::new();
    assert_eq!(
        vm.run_traced(80, &mut |step| trace.push(*step)),
        Err(ProfileMachineError::InvalidEncryptionTarget {
            pointer: 121,
            value: 7_174_404,
        }),
        "stdin={stdin:?}: expected invalid indirect instruction target"
    );
    assert_eq!(
        vm.input_consumed(),
        stdin.len().min(2),
        "stdin={stdin:?} expected both reads"
    );
    assert_eq!(
        trace.last().map(|step| step.decoded),
        Some(Some(b'i')),
        "stdin={stdin:?} expected final indirect branch"
    );
    assert_eq!(
        trace.last().map(|step| step.before.registers.code_pointer),
        Some(67),
        "stdin={stdin:?} expected source-required C67"
    );
    assert_eq!(
        trace
            .last()
            .and_then(|step| step.memory_reads.data)
            .map(|read| (read.address, read.value)),
        Some((150, 121)),
        "stdin={stdin:?} expected expanded-cell target"
    );
    let expected = stdin
        .iter()
        .copied()
        .chain(once(174u8).cycle())
        .take(2)
        .collect::<Vec<_>>();
    assert_eq!(vm.output(), expected, "stdin={stdin:?} physical outputs");
}

// Both stored inputs survive a real j,j,i,i branch to encrypted C35. The
// second execution of C45 rewrites C49 from the *second* input: successful
// bytes select a non-graphical fetch, EOF selects graphical instruction 42.
// Both paths still terminate on non-graphical code, not a valid C23 `if`.
#[test]
#[expect(clippy::expect_used, reason = "bounded graphical N15 source")]
fn eof_fetch_source_preserves_original_two_output_prefix() {
    let profile = current_profile();
    let source = layout::build_c23_two_inputs_eof_fetch_probe_source(profile)
        .expect("physical EOF-dependent code fetch");
    assert_eq!(source.len(), 91);
    assert_eq!(source.get(89..), Some(b"Iy".as_slice()));
    assert_eq!(
        layout::build_c23_two_inputs_eof_fetch_probe_source(
            historical_profile()
        ),
        Err(layout::C23OperandProbeSourceError::UnsupportedProfile)
    );
    layout::admit_c23_probe_graphical_source(&source)
        .expect("strict graphical source admission");
    let baseline =
        layout::build_c23_two_inputs_saved_and_echoed_source(profile)
            .expect("original two-input source");
    assert_eq!(source.get(..63), baseline.get(..63));
    assert_eq!(source.get(66..), baseline.get(66..));
    for (position, opcode) in [(63u32, b'j'), (64, b'j'), (65, b'i')] {
        let encoded = source.get(usize::try_from(position).expect("code site"));
        assert_eq!(
            encoded.and_then(|byte| {
                decode_profile_instruction(u32::from(*byte), position)
            }),
            Some(opcode)
        );
    }
}

#[test]
fn scalar_eof_fetch_code_class_is_unique() {
    let profile = current_profile();
    let eof_encoded = oracle_crazy(121, profile.eof_word());
    let eof_restored = oracle_crazy(121, eof_encoded);
    assert_eq!(eof_restored, 7_174_574);
    assert_eq!(oracle_crazy(75, eof_restored), 42);
    assert_eq!(decode_profile_instruction(42, 49), Some(b'='));
    let mut distinct = BTreeSet::new();
    for byte in 0..=255u8 {
        let encoded = oracle_crazy(121, u32::from(byte));
        assert!(distinct.insert(encoded));
        assert_eq!(oracle_crazy(121, encoded), u32::from(byte));
        let code = oracle_crazy(75, u32::from(byte));
        assert!(!(33..=126).contains(&code), "byte={byte}");
    }
    assert_eq!(distinct.len(), 256);
    assert!(!distinct.contains(&eof_encoded));
}

#[expect(clippy::expect_used, reason = "bounded real VM trace")]
fn assert_two_input_code_reentry(trace: &[ProfileStepTrace], second: u32) {
    assert!(trace.len() >= 82, "second={second} trace is truncated");
    for (step, code, opcode) in [
        (63, 63, b'j'),
        (64, 64, b'j'),
        (65, 65, b'i'),
        (66, 67, b'i'),
        (77, 45, b'p'),
    ] {
        let observed = trace.get(step).expect("validated physical step");
        assert_eq!(
            observed.before.registers.code_pointer, code,
            "second={second}; unexpected C at step {step}"
        );
        assert_eq!(
            observed.decoded,
            Some(opcode),
            "second={second}; unexpected opcode at step {step}"
        );
    }
    assert_eq!(
        trace.get(65).map(|step| step.before.registers.data_pointer),
        Some(37),
        "second={second} expected input-cell pointer"
    );
    assert_eq!(
        trace.get(67).map(|step| step.before.registers.code_pointer),
        Some(35),
        "second={second} expected encrypted code backedge"
    );
}

#[expect(clippy::expect_used, reason = "bounded real VM trace")]
fn assert_second_input_code_fetch(
    trace: &[ProfileStepTrace],
    second: u32,
    eof_word: u32,
) {
    let eof = second == eof_word;
    let code = oracle_crazy(
        75,
        if eof {
            7_174_574
        } else {
            second
        },
    );
    let write = trace.get(77).and_then(|step| step.memory_delta.data);
    assert_eq!(
        write.map(|value| (value.address, value.before, value.after)),
        Some((49, 75, code)),
        "second={second} expected live guest code rewrite"
    );
    let fetch = trace.get(81).expect("validated C49 fetch");
    assert_eq!(
        fetch.before.registers.code_pointer, 49,
        "second={second} expected C49 code fetch"
    );
    assert_eq!(
        fetch.memory_reads.fetch.map(|read| read.value),
        Some(code),
        "second={second} expected rewritten instruction fetch"
    );
    assert_eq!(
        fetch.decoded,
        if eof {
            Some(b'=')
        } else {
            None
        },
        "second={second} expected EOF-only graphical code"
    );
    if eof {
        let output = trace.get(89).expect("EOF path reached C57");
        assert_eq!(
            (output.before.registers.code_pointer, output.output),
            (57, Some(32)),
            "second={second} expected EOF-only third output"
        );
    }
}

#[expect(
    clippy::expect_used,
    reason = "oracle compares finite byte class"
)]
fn assert_second_input_state(
    vm: &ProfileMachine,
    second: u32,
    eof_word: u32,
    consumed: usize,
) {
    let eof = second == eof_word;
    let mut output = vec![
        3,
        if eof {
            174
        } else {
            u8::try_from(second).expect("finite byte")
        },
    ];
    if eof {
        output.push(32);
    }
    assert_eq!(vm.output(), output, "second={second} guest output");
    assert_eq!(vm.input_consumed(), consumed, "second={second} cursor");
    assert_eq!(
        vm.memory_word(126),
        Ok(oracle_crazy(121, 3)),
        "second={second} first saved word"
    );
    assert_eq!(
        vm.memory_word(138),
        Ok(oracle_crazy(121, second)),
        "second={second} second saved word"
    );
    let code = oracle_crazy(
        75,
        if eof {
            7_174_574
        } else {
            second
        },
    );
    assert_eq!(
        vm.memory_word(49),
        Ok(if eof {
            114
        } else {
            code
        }),
        "second={second} expected exact terminal code cell"
    );
}

#[test]
#[expect(
    clippy::expect_used,
    reason = "257 physical N15 input classes"
)]
fn second_input_selects_exact_guest_code_fetch_in_all_257_classes() {
    let profile = current_profile();
    let source = layout::build_c23_two_inputs_eof_fetch_probe_source(profile)
        .expect("source construction");
    let pristine = ProfileMachine::from_source(profile, &source, vec![])
        .expect("normative source loader");
    for second in (0..=255u32).chain(once(profile.eof_word())) {
        let eof = second == profile.eof_word();
        let input = if eof {
            vec![3]
        } else {
            vec![3, u8::try_from(second).expect("finite byte")]
        };
        let mut vm = pristine.fork_with_input(input.clone()).expect("VM fork");
        let mut trace = Vec::new();
        let expected_steps = if eof {
            93
        } else {
            82
        };
        assert_eq!(
            vm.run_traced(100, &mut |step| trace.push(*step)),
            Ok(RunOutcome::Terminated {
                reason: Termination::NonGraphicalCell,
                steps: expected_steps,
            }),
            "second={second}"
        );
        assert_eq!(trace.len(), expected_steps);
        assert_second_input_state(&vm, second, profile.eof_word(), input.len());
        assert_two_input_code_reentry(&trace, second);
        assert_second_input_code_fetch(&trace, second, profile.eof_word());
    }
}

#[test]
#[expect(
    clippy::expect_used,
    reason = "257 physical N15 first-input classes"
)]
fn every_first_input_retains_the_second_eof_code_path() {
    let profile = current_profile();
    let source = layout::build_c23_two_inputs_eof_fetch_probe_source(profile)
        .expect("source construction");
    let pristine = ProfileMachine::from_source(profile, &source, vec![])
        .expect("normative source loader");
    for first in (0..=255u32).chain(once(profile.eof_word())) {
        let input = if first == profile.eof_word() {
            vec![]
        } else {
            vec![u8::try_from(first).expect("finite byte")]
        };
        let mut vm = pristine.fork_with_input(input.clone()).expect("VM fork");
        let mut trace = Vec::new();
        assert_eq!(
            vm.run_traced(100, &mut |step| trace.push(*step)),
            Ok(RunOutcome::Terminated {
                reason: Termination::NonGraphicalCell,
                steps: 93,
            }),
            "first={first}"
        );
        let output_first = if first == profile.eof_word() {
            174
        } else {
            u8::try_from(first).expect("finite byte")
        };
        assert_eq!(vm.output(), [output_first, 174, 32]);
        assert_eq!(vm.input_consumed(), input.len());
        assert_eq!(vm.memory_word(126), Ok(oracle_crazy(121, first)));
        assert_eq!(
            vm.memory_word(138),
            Ok(oracle_crazy(121, profile.eof_word()))
        );
        assert_two_input_code_reentry(&trace, profile.eof_word());
        assert_second_input_code_fetch(
            &trace,
            profile.eof_word(),
            profile.eof_word(),
        );
    }
}

#[test]
#[expect(
    clippy::expect_used,
    reason = "bounded real N15 mutation controls"
)]
fn changing_reentry_jumps_refuses_the_eof_code_path() {
    let profile = current_profile();
    let source = layout::build_c23_two_inputs_eof_fetch_probe_source(profile)
        .expect("source construction");
    for position in [63u32, 64] {
        let mut changed = source.clone();
        let site = usize::try_from(position).expect("bounded code site");
        *changed.get_mut(site).expect("valid source code site") =
            source_encoding(position, b'o').expect("graphical negative code");
        let mut vm = ProfileMachine::from_source(profile, &changed, vec![3])
            .expect("negative source still loads");
        assert_ne!(
            vm.run(100),
            Ok(RunOutcome::Terminated {
                reason: Termination::NonGraphicalCell,
                steps: 93,
            }),
            "invalid transfer cannot select the EOF code fetch"
        );
        assert_eq!(vm.output().get(..2), Some([3, 174].as_slice()));
    }
}
