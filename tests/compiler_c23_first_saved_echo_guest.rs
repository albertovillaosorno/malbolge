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
//   - A real saved first-input word and independently reached byte output.
// - Must-Not:
//   - Claim signed EOF conversion, mutable source C, or an EOF loop.
// - Allows:
//   - Inputs: N15 graphical source and finite binary/EOF input streams.
//   - Outputs: reached store, data-pointer advance, output and halt traces.
//   - Side effects: isolated normative guest VM execution only.
// - Split-When:
//   - A general C23 input-state output linker replaces the fixed witness.
// - Merge-When:
//   - The complete mutable-C guest CFG authenticates these exact effects.
// - Summary:
//   - Saves a real first input before echoing it without another input read.

//! One N15 input is stored, recovered, and echoed through real guest dataflow.

#[path = "../src/compiler/malbolge-layout/composition/lib.rs"]
pub mod layout;

use std::collections::BTreeSet;
use std::iter::once;

use malbolge::{
    ProfileMachine, RunOutcome, Termination, TraceInput, current_profile,
    decode_profile_instruction, historical_profile,
};

#[expect(
    clippy::arithmetic_side_effects,
    clippy::as_conversions,
    clippy::integer_division_remainder_used,
    clippy::indexing_slicing,
    reason = "independent 15-trit crazy scalar oracle"
)]
fn scalar_crazy(mut data: u32, mut accumulator: u32) -> u32 {
    const TABLE: [[u32; 3]; 3] = [[1, 0, 0], [1, 0, 2], [2, 2, 1]];
    let mut word = 0;
    let mut place = 1;
    for _ in 0..15 {
        word += TABLE[(data % 3) as usize][(accumulator % 3) as usize] * place;
        data /= 3;
        accumulator /= 3;
        place *= 3;
    }
    word
}

#[expect(
    clippy::expect_used,
    reason = "known fixed opcode has a graphical source encoding"
)]
fn opcode(position: u32, decoded: u8) -> u8 {
    (33..=126u8)
        .find(|byte| {
            decode_profile_instruction(u32::from(*byte), position)
                == Some(decoded)
        })
        .expect("graphical opcode must exist at this source position")
}

#[test]
#[expect(
    clippy::as_conversions,
    clippy::expect_used,
    clippy::indexing_slicing,
    clippy::too_many_lines,
    clippy::cognitive_complexity,
    clippy::integer_division_remainder_used,
    reason = "physical sites, scalar oracle and negative controls"
)]
fn first_saved_input_reaches_second_fold_and_guest_output() {
    let profile = current_profile();
    let source = layout::build_c23_first_input_saved_and_echoed_source(profile)
        .expect("source-loaded two-fold physical echo must be constructible");
    assert_eq!(
        layout::build_c23_first_input_saved_and_echoed_source(
            historical_profile()
        ),
        Err(layout::C23OperandProbeSourceError::UnsupportedProfile)
    );
    assert_eq!(source.len(), 91);
    assert_eq!(source.get(89..), Some(b"Iy".as_slice()));
    layout::admit_c23_probe_graphical_source(&source)
        .expect("every graphical source cell must be source-loadable");
    for (code, decoded) in
        [(37, b'/'), (43, b'p'), (49, b'p'), (50, b'<'), (51, b'v')]
    {
        assert_eq!(
            decode_profile_instruction(u32::from(source[code]), code as u32),
            Some(decoded),
        );
    }
    for code in 44..49 {
        assert_eq!(
            decode_profile_instruction(u32::from(source[code]), code as u32),
            Some(b'o')
        );
    }
    let before = layout::build_c23_first_input_lossless_store_source(profile)
        .expect("original single input state path");
    assert_eq!(source.get(..44), before.get(..44));
    assert_eq!(source.get(52..), before.get(52..));

    // Independent scalar proof: the two p instructions invert all bytes.
    // EOF survives as a separate class but does not restore the N15 EOF word.
    let mut stored_words = BTreeSet::new();
    for raw in (0..=255).chain(once(profile.eof_word())) {
        let saved = scalar_crazy(121, raw);
        assert!(stored_words.insert(saved));
        assert_eq!(
            scalar_crazy(121, saved),
            if raw == profile.eof_word() {
                7_174_574
            } else {
                raw
            }
        );
    }
    assert_eq!(stored_words.len(), 257);
    assert_eq!(profile.eof_word(), 14_348_906);
    assert_eq!(scalar_crazy(121, profile.eof_word()), 242);
    assert_eq!(scalar_crazy(121, 242), 7_174_574);
    assert_eq!(7_174_574u32 % 256, 174);

    let pristine = ProfileMachine::from_source(profile, &source, vec![])
        .expect("source admitted by the normative N15 loader");
    assert_eq!(pristine.memory_word(126), Ok(121));
    assert_eq!(pristine.memory_word(132), Ok(121));
    // A suffix after the first read must remain unread; only one C37 / runs.
    for input in [
        vec![],
        vec![0],
        vec![1],
        vec![2],
        vec![127],
        vec![128],
        vec![254],
        vec![255],
        vec![0, 255, 128],
        vec![255, 0],
    ] {
        let mut vm = pristine
            .fork_with_input(input.clone())
            .expect("pristine guest may be replayed with new input");
        let mut trace = Vec::new();
        assert_eq!(
            vm.run_traced(52, &mut |step| trace.push(*step)),
            Ok(RunOutcome::Terminated {
                reason: Termination::HaltInstruction,
                steps: 52,
            }),
            "stdin={input:?}",
        );
        assert_eq!(trace.len(), 52);
        assert_eq!(vm.input_consumed(), usize::from(!input.is_empty()));
        let raw = input
            .first()
            .map_or(profile.eof_word(), |byte| u32::from(*byte));
        let saved = scalar_crazy(121, raw);
        let restored = scalar_crazy(121, saved);
        assert_eq!(
            trace[37].input,
            Some(input.first().map_or(TraceInput::EndOfInput, |byte| {
                TraceInput::Byte(*byte)
            }))
        );
        assert_eq!(trace.iter().filter(|step| step.input.is_some()).count(), 1);
        assert_eq!(
            trace[42]
                .memory_reads
                .data
                .map(|read| (read.address, read.value)),
            Some((67, 125))
        );
        assert_eq!(trace[43].decoded, Some(b'p'));
        assert_eq!(
            trace[43].memory_delta.data.map(|write| (
                write.address,
                write.before,
                write.after
            )),
            Some((126, 121, saved))
        );
        assert_eq!(vm.memory_word(126), Ok(saved));
        for position in 44..=48 {
            assert_eq!(trace[position].decoded, Some(b'o'));
            assert_eq!(trace[position].memory_delta.data, None);
        }
        assert_eq!(trace[49].decoded, Some(b'p'));
        assert_eq!(
            trace[49]
                .memory_reads
                .data
                .map(|read| (read.address, read.value)),
            Some((132, 121))
        );
        assert_eq!(
            trace[49].memory_delta.data.map(|write| (
                write.address,
                write.before,
                write.after
            )),
            Some((132, 121, restored))
        );
        assert_eq!(vm.memory_word(132), Ok(restored));
        assert_eq!(trace[50].decoded, Some(b'<'));
        assert_eq!(trace[50].output, Some((restored % 256) as u8));
        assert_eq!(vm.output(), [(restored % 256) as u8]);
        assert_eq!(trace[51].decoded, Some(b'v'));
        assert_eq!(trace[51].memory_delta.encryption, None);
    }

    // Both physical crazy writes are necessary for raw output: changing either
    // to no-op leaves a source-loadable guest but changes its byte result.
    for missing_code in [43u32, 49] {
        let mut mutated = source.clone();
        mutated[missing_code as usize] = opcode(missing_code, b'o');
        let mut vm = ProfileMachine::from_source(profile, &mutated, vec![255])
            .expect("mutated graphical source still passes load admission");
        assert_eq!(
            vm.run(52),
            Ok(RunOutcome::Terminated {
                reason: Termination::HaltInstruction,
                steps: 52,
            })
        );
        assert_ne!(vm.output(), [255]);
        assert_eq!(
            vm.memory_word(126),
            Ok(if missing_code == 43 {
                121
            } else {
                scalar_crazy(121, 255)
            })
        );
    }
}

// Once the C43 source-loader M126=121 crazy has executed, every successful
// input has trits 1 at positions 6..14; EOF has trits 0 there. A second
// *constant* crazy operand cannot use trit 0 or 2 below position five:
// either would irreversibly merge two successful input classes. Position
// five admits only seed 0 or 1 (bytes have input trit 0 or 1). Above five,
// seed trits 0 and 1 behave identically for both successful classes and
// EOF; a seed trit 2 is the only distinguishable alternative. Thus this
// finite 2 * 2^9 search covers every two-p static-operand byte-identity
// candidate, even sources with arbitrary second operand values, not only
// the M132=121 loader operand in the physical guest above.
#[test]
#[expect(
    clippy::arithmetic_side_effects,
    clippy::integer_division_remainder_used,
    reason = "finite exact N15 ternary seed census"
)]
fn no_static_second_crazy_seed_can_echo_bytes_and_normalize_eof() {
    const HIGH_PLACES: [u32; 9] = [
        729, 2_187, 6_561, 19_683, 59_049, 177_147, 531_441, 1_594_323,
        4_782_969,
    ];
    let profile = current_profile();
    let saved = (0..=255u32)
        .map(|byte| scalar_crazy(121, byte))
        .collect::<Vec<_>>();
    let saved_eof = scalar_crazy(121, profile.eof_word());
    let mut candidates = 0usize;
    let mut eof_bytes = BTreeSet::new();
    for mask in 0..512u32 {
        let mut high_seed = 121u32;
        for (index, place) in HIGH_PLACES.iter().enumerate() {
            if mask & (1u32 << index) != 0 {
                high_seed += 2 * place;
            }
        }
        for sixth_trit in 0..=1u32 {
            let seed = high_seed + sixth_trit * 243;
            assert!(seed < profile.word_modulus());
            let retains_all_bytes =
                (0..=255u32).zip(&saved).all(|(byte, saved_byte)| {
                    scalar_crazy(seed, *saved_byte) % 256 == byte
                });
            if retains_all_bytes {
                candidates += 1;
                let eof = scalar_crazy(seed, saved_eof) % 256;
                assert_ne!(
                    eof, 255,
                    "static seed {seed} cannot supply C23 EOF"
                );
                _ = eof_bytes.insert(eof);
            }
        }
    }
    assert_eq!(candidates, 14);
    assert_eq!(eof_bytes, BTreeSet::from([46, 174]));
    // Changing only a static second p operand cannot complete source-C23
    // EOF handling. A guest EOF branch or different live data path is needed.
}
