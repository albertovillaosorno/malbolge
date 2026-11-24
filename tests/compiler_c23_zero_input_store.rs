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
//   - A source-loaded zero C32 pair and genuinely input-derived low-cell write.
// - Must-Not:
//   - Claim this lossy write is signed C23 getchar or a linked checksum.
// - Allows:
//   - Inputs: the fixed 62-cell N15 loader and finite byte/EOF streams.
//   - Outputs: exact guest writes with an independent 257-class scalar oracle.
//   - Side effects: isolated bounded normative VM runs only.
// - Split-When:
//   - A real C23 typed SSA store replaces this partial physical continuation.
// - Merge-When:
//   - The original checksum runs its first executable signed source store.

//! First source-loaded P2 zero initializer, read, and revisited data store.

#[path = "../src/compiler/malbolge-layout/composition/lib.rs"]
pub mod layout;

use std::collections::BTreeSet;

use malbolge::{
    ProfileMachine, ProfileRegisters, RunOutcome, Termination, TraceInput,
    current_profile, decode_profile_instruction, historical_profile,
};

// Canonical 62-byte physical zero initializer, not a hand-seeded memory image.
// C14 and C17 make adjacent zero writes before the suffix is patched.
const INITIAL_SOURCE: &str = concat!(
    "44434241403f3e3d3c7d34337a31302f762d3f31302f2e2d2c2b2a292827",
    "2625242322217e7d7c7b7a797877767574737271706f6e6d6c6b6a6968672725",
);
const LOW: u32 = 7_174_417;
const HIGH: u32 = LOW + 1;
const ENCODED: u32 = 7_174_439;
const REENTRY: u32 = ENCODED + 1;
const MODULUS: u32 = 14_348_907;

#[expect(
    clippy::arithmetic_side_effects,
    clippy::integer_division_remainder_used,
    reason = "independent finite 15-trit ternary scalar oracle"
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

fn graphical(position: usize, operation: u8) -> u8 {
    (33..=126u8)
        .find(|byte| {
            decode_profile_instruction(u32::from(*byte), position as u32)
                == Some(operation)
        })
        .expect("every fixed probe operation is graphically representable")
}

fn patched_source() -> Vec<u8> {
    let mut source = INITIAL_SOURCE
        .as_bytes()
        .chunks_exact(2)
        .map(|pair| {
            let hex = std::str::from_utf8(pair).expect("fixed ASCII hex");
            u8::from_str_radix(hex, 16).expect("fixed graphical source")
        })
        .collect::<Vec<_>>();
    assert_eq!(source.len(), 62);
    for (index, operation) in [
        (18usize, b'o'),
        (37, b'/'),
        (38, b'o'),
        (39, b'p'),
        (40, b'j'),
        (41, b'p'),
        (42, b'v'),
    ] {
        source[index] = graphical(index, operation);
    }
    source
}

#[test]
#[expect(
    clippy::cognitive_complexity,
    clippy::too_many_lines,
    clippy::indexing_slicing,
    clippy::panic_in_result_fn,
    reason = "finite 257-class oracle and real 43-step source-loaded traces"
)]
fn first_real_c37_read_revisits_zero_low_and_writes_guest_data()
-> Result<(), String> {
    let profile = current_profile();
    let source = patched_source();
    assert_eq!(layout::admit_c23_probe_graphical_source(&source), Ok(()));
    let prepared = ProfileMachine::from_source(profile, &source, Vec::new())
        .map_err(|error| error.to_string())?;
    assert_eq!(prepared.memory_word(LOW), Ok(37));
    assert_eq!(prepared.memory_word(HIGH), Ok(7_174_416));
    assert_eq!(prepared.memory_word(ENCODED), Ok(37));
    assert_eq!(prepared.memory_word(REENTRY), Ok(7_174_416));
    let all_results = (0..=255u32)
        .chain([MODULUS - 1])
        .map(|raw| scalar_crazy(0, scalar_crazy(37, raw)))
        .collect::<Vec<_>>();
    assert_eq!(
        all_results.iter().copied().collect::<BTreeSet<_>>().len(),
        40
    );
    assert_eq!(
        (all_results[0], all_results[255], all_results[256]),
        (0, 255, 7_174_416)
    );
    assert!(!all_results[..256].contains(&all_results[256]));
    // The 40 image classes prove this is NOT a C23 signed/unsigned input
    // representation, even though EOF stays distinguishable from every byte.
    for input in [
        vec![],
        vec![0],
        vec![1],
        vec![2],
        vec![127],
        vec![255],
        vec![255, 4],
    ] {
        let raw = input
            .first()
            .map_or(profile.eof_word(), |byte| u32::from(*byte));
        let mut vm = ProfileMachine::from_state(
            profile,
            prepared.memory().to_vec(),
            input.clone(),
            ProfileRegisters::default(),
        )
        .map_err(|error| error.to_string())?;
        let mut trace = Vec::new();
        let outcome = vm
            .run_traced(43, &mut |step| trace.push(*step))
            .map_err(|error| error.to_string())?;
        assert_eq!(outcome, RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 43,
        });
        assert_eq!(trace.len(), 43);
        assert_eq!(trace[14].decoded, Some(b'p'));
        assert_eq!(trace[17].decoded, Some(b'p'));
        assert_eq!(trace[37].decoded, Some(b'/'));
        assert_eq!(
            trace[37].input,
            Some(
                input
                    .first()
                    .map_or(TraceInput::EndOfInput, |b| TraceInput::Byte(*b))
            )
        );
        assert_eq!(trace[38].decoded, Some(b'o'));
        assert_eq!(trace[39].decoded, Some(b'p'));
        assert_eq!(trace[39].before.registers.data_pointer, ENCODED);
        assert_eq!(trace[39].before.registers.accumulator, raw);
        assert_eq!(trace[39].memory_reads.data.map(|r| r.value), Some(37));
        let intermediate = scalar_crazy(37, raw);
        assert_eq!(trace[39].after.registers.accumulator, intermediate);
        assert_eq!(trace[40].decoded, Some(b'j'));
        assert_eq!(
            trace[40].memory_reads.data.map(|r| (r.address, r.value)),
            Some((REENTRY, LOW - 1))
        );
        assert_eq!(trace[40].after.registers.data_pointer, LOW);
        assert_eq!(trace[41].decoded, Some(b'p'));
        assert_eq!(
            trace[41].memory_reads.data.map(|r| (r.address, r.value)),
            Some((LOW, 0))
        );
        let expected_low = scalar_crazy(0, intermediate);
        assert_eq!(trace[41].after.registers.accumulator, expected_low);
        assert_eq!(vm.memory_word(LOW), Ok(expected_low));
        assert_eq!(vm.memory_word(HIGH), Ok(0));
        assert_eq!(vm.memory_word(ENCODED), Ok(intermediate));
        assert_eq!(trace[42].decoded, Some(b'v'));
        assert_eq!(vm.input_consumed(), usize::from(!input.is_empty()));
        assert!(vm.output().is_empty());
    }
    Ok(())
}

#[test]
fn source_loaded_fold_builder_matches_independent_physical_oracle() {
    let plan = layout::build_adjacent_c32_zero_c37_input_low_fold_source(
        current_profile(),
    )
    .expect("bounded N15 loader admits the input low-cell fold");
    assert_eq!(plan.zero_pair.source, patched_source());
    assert_eq!(plan.zero_pair.zero_high_code_address, 14);
    assert_eq!(plan.zero_pair.zero_low_code_address, 17);
    assert_eq!(plan.zero_pair.input_code_address, Some(37));
    assert_eq!(plan.zero_pair.zero_low_address, LOW);
    assert_eq!(plan.zero_pair.zero_high_address, HIGH);
    assert_eq!(plan.encoded_store_code_address, 39);
    assert_eq!(plan.encoded_data_address, ENCODED);
    assert_eq!(plan.reentry_code_address, 40);
    assert_eq!(plan.low_fold_code_address, 41);
    assert_eq!(plan.halt_code_address, 42);
    assert_eq!(
        layout::build_adjacent_c32_zero_c37_input_low_fold_source(
            historical_profile(),
        ),
        Err(layout::ZeroCellSourceError::UnsupportedProfile),
    );
}

// The original source-loaded zero initializer writes the trit-wise ones
// word at M126 and a zero return pointer at M127. A real data-path search
// found a route to reuse those existing values rather than accepting the
// lossy M7,174,439 scratch fold above.
fn full_raw_input_pair_source() -> Vec<u8> {
    let mut source = patched_source();
    for (site, operation) in [
        (18usize, b'j'),
        (19, b'j'),
        (20, b'j'),
        (21, b'p'),
        (22, b'j'),
        (36, b'j'),
        (37, b'/'),
        (38, b'o'),
        (39, b'p'),
        (40, b'j'),
        (41, b'j'),
        (42, b'j'),
        (43, b'p'),
        (44, b'v'),
    ] {
        source[site] = graphical(site, operation);
    }
    source
}

#[test]
#[expect(
    clippy::cognitive_complexity,
    clippy::too_many_lines,
    clippy::indexing_slicing,
    clippy::panic_in_result_fn,
    reason = "all 257 input/EOF inverse maps and real 45-step physical routes"
)]
fn guest_recovers_every_raw_input_after_original_zero_pair()
-> Result<(), String> {
    let profile = current_profile();
    let source = full_raw_input_pair_source();
    assert_eq!(layout::admit_c23_probe_graphical_source(&source), Ok(()));
    let ones = 7_174_453;
    for raw in (0..=255u32).chain([profile.eof_word()]) {
        assert_eq!(scalar_crazy(ones, scalar_crazy(ones, raw)), raw);
    }
    let prepared = ProfileMachine::from_source(profile, &source, Vec::new())
        .map_err(|error| error.to_string())?;
    assert_eq!(prepared.memory_word(LOW), Ok(37));
    assert_eq!(prepared.memory_word(HIGH), Ok(7_174_416));
    assert_eq!(prepared.memory_word(126), Ok(7_174_416));
    for input in [
        vec![],
        vec![0],
        vec![1],
        vec![2],
        vec![127],
        vec![128],
        vec![255],
        vec![255, 4],
    ] {
        let raw = input
            .first()
            .map_or(profile.eof_word(), |byte| u32::from(*byte));
        let mut vm = ProfileMachine::from_state(
            profile,
            prepared.memory().to_vec(),
            input.clone(),
            ProfileRegisters::default(),
        )
        .map_err(|error| error.to_string())?;
        let mut trace = Vec::new();
        let outcome = vm
            .run_traced(45, &mut |step| trace.push(*step))
            .map_err(|error| error.to_string())?;
        assert_eq!(outcome, RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 45,
        });
        assert_eq!(trace.len(), 45);
        assert_eq!(
            trace[14].memory_delta.data.map(|w| (w.address, w.after)),
            Some((HIGH, 0))
        );
        assert_eq!(
            trace[17].memory_delta.data.map(|w| (w.address, w.after)),
            Some((LOW, 0))
        );
        assert_eq!(trace[21].decoded, Some(b'p'));
        assert_eq!(trace[21].before.registers.data_pointer, LOW);
        assert_eq!(trace[21].memory_reads.data.map(|r| r.value), Some(0));
        assert_eq!(trace[21].after.registers.accumulator, ones);
        assert_eq!(trace[36].decoded, Some(b'j'));
        assert_eq!(
            trace[36].memory_reads.data.map(|r| (r.address, r.value)),
            Some((14, 123))
        );
        assert_eq!(trace[36].after.registers.data_pointer, 124);
        assert_eq!(trace[37].decoded, Some(b'/'));
        assert_eq!(
            trace[37].input,
            Some(
                input
                    .first()
                    .map_or(TraceInput::EndOfInput, |b| TraceInput::Byte(*b))
            )
        );
        assert_eq!(trace[38].decoded, Some(b'o'));
        assert_eq!(trace[39].decoded, Some(b'p'));
        assert_eq!(
            trace[39].memory_reads.data.map(|r| (r.address, r.value)),
            Some((126, ones))
        );
        let encoded = scalar_crazy(ones, raw);
        assert_eq!(trace[39].after.registers.accumulator, encoded);
        for (step, operand_address, operand_value, target) in
            [(40, 127, 0, 1), (41, 1, 85, 86), (42, 86, LOW - 1, LOW)]
        {
            assert_eq!(trace[step].decoded, Some(b'j'));
            assert_eq!(
                trace[step].memory_reads.data.map(|r| (r.address, r.value)),
                Some((operand_address, operand_value))
            );
            assert_eq!(trace[step].after.registers.data_pointer, target);
        }
        assert_eq!(trace[43].decoded, Some(b'p'));
        assert_eq!(
            trace[43].memory_reads.data.map(|r| (r.address, r.value)),
            Some((LOW, ones))
        );
        assert_eq!(trace[43].after.registers.accumulator, raw);
        assert_eq!(trace[44].decoded, Some(b'v'));
        assert_eq!(vm.memory_word(LOW), Ok(raw));
        assert_eq!(vm.memory_word(HIGH), Ok(0));
        assert_eq!(vm.memory_word(126), Ok(encoded));
        assert_eq!(vm.input_consumed(), usize::from(!input.is_empty()));
        assert!(vm.output().is_empty());
    }
    Ok(())
}

#[test]
fn raw_input_pair_builder_matches_independently_encoded_guest() {
    let plan = layout::build_adjacent_c32_zero_c37_raw_input_pair_source(
        current_profile(),
    )
    .expect("current N15 source has a loader-backed reversible raw input");
    assert_eq!(plan.zero_pair.source, full_raw_input_pair_source());
    assert_eq!(plan.zero_pair.source.len(), 62);
    assert_eq!(plan.zero_pair.input_code_address, Some(37));
    assert_eq!(plan.zero_pair.zero_high_code_address, 14);
    assert_eq!(plan.zero_pair.zero_low_code_address, 17);
    assert_eq!(plan.zero_pair.zero_low_address, LOW);
    assert_eq!(plan.zero_pair.zero_high_address, HIGH);
    assert_eq!(plan.low_prime_code_address, 21);
    assert_eq!(plan.encoded_store_code_address, 39);
    assert_eq!(plan.encoded_data_address, 126);
    assert_eq!(plan.return_code_addresses, [40, 41, 42]);
    assert_eq!(plan.low_store_code_address, 43);
    assert_eq!(plan.halt_code_address, 44);
    assert_eq!(
        layout::build_adjacent_c32_zero_c37_raw_input_pair_source(
            historical_profile(),
        ),
        Err(layout::ZeroCellSourceError::UnsupportedProfile),
    );
}

#[test]
#[expect(
    clippy::indexing_slicing,
    clippy::panic_in_result_fn,
    reason = "one-code-cell physical negative control with authentic input"
)]
fn skipping_real_preinput_one_priming_loses_raw_byte_two() -> Result<(), String>
{
    let profile = current_profile();
    let source = full_raw_input_pair_source();
    let mut removed = source.clone();
    removed[21] = graphical(21, b'o');
    for (physical, expected) in [(source, 2u32), (removed, 0)] {
        let mut guest =
            ProfileMachine::from_source(profile, &physical, vec![2])
                .map_err(|error| error.to_string())?;
        assert_eq!(
            guest.run(45).map_err(|error| error.to_string())?,
            RunOutcome::Terminated {
                reason: Termination::HaltInstruction,
                steps: 45,
            },
        );
        assert_eq!(guest.memory_word(LOW), Ok(expected));
        assert_eq!(guest.memory_word(HIGH), Ok(0));
    }
    Ok(())
}

fn raw_input_pointer_select_source() -> Vec<u8> {
    let mut source = full_raw_input_pair_source();
    for (site, instruction) in [
        (44usize, b'j'),
        (45, b'j'),
        (46, b'j'),
        (47, b'j'),
        (48, b'v'),
    ] {
        source[site] = graphical(site, instruction);
    }
    source
}

#[test]
#[expect(
    clippy::cognitive_complexity,
    clippy::indexing_slicing,
    clippy::too_many_lines,
    clippy::panic_in_result_fn,
    reason = "normative 257-class input-dependent pointer transfer"
)]
fn guest_uses_saved_raw_input_as_257_class_data_pointer() -> Result<(), String>
{
    let profile = current_profile();
    let source = raw_input_pointer_select_source();
    assert_eq!(layout::admit_c23_probe_graphical_source(&source), Ok(()));
    for raw in (0..=255u32).chain([profile.eof_word()]) {
        let pointed = (raw + 1) % profile.memory_words();
        assert_eq!(pointed == 0, raw == profile.eof_word());
    }
    let prepared = ProfileMachine::from_source(profile, &source, Vec::new())
        .map_err(|error| error.to_string())?;
    for input in [
        vec![],
        vec![0],
        vec![1],
        vec![2],
        vec![127],
        vec![128],
        vec![255],
        vec![255, 4],
    ] {
        let raw = input
            .first()
            .map_or(profile.eof_word(), |byte| u32::from(*byte));
        let expected_pointer = (raw + 1) % profile.memory_words();
        let mut guest = ProfileMachine::from_state(
            profile,
            prepared.memory().to_vec(),
            input.clone(),
            ProfileRegisters::default(),
        )
        .map_err(|error| error.to_string())?;
        let mut trace = Vec::new();
        assert_eq!(
            guest
                .run_traced(49, &mut |step| trace.push(*step))
                .map_err(|error| error.to_string())?,
            RunOutcome::Terminated {
                reason: Termination::HaltInstruction,
                steps: 49,
            },
        );
        assert_eq!(trace[43].decoded, Some(b'p'));
        assert_eq!(trace[43].after.registers.accumulator, raw);
        for (index, read_address, read_value, next_pointer) in [
            (44, HIGH, 0, 1),
            (45, 1, 85, 86),
            (46, 86, LOW - 1, LOW),
            (47, LOW, raw, expected_pointer),
        ] {
            assert_eq!(trace[index].decoded, Some(b'j'));
            assert_eq!(
                trace[index].memory_reads.data.map(|r| (r.address, r.value)),
                Some((read_address, read_value))
            );
            assert_eq!(trace[index].after.registers.data_pointer, next_pointer);
        }
        assert_eq!(trace[48].decoded, Some(b'v'));
        assert_eq!(guest.memory_word(LOW), Ok(raw));
        assert_eq!(guest.memory_word(HIGH), Ok(0));
        assert_eq!(guest.input_consumed(), usize::from(!input.is_empty()));
        assert!(guest.output().is_empty());
    }
    Ok(())
}

#[test]
fn raw_pointer_builder_matches_independent_guest_and_refuses_old_profile() {
    let plan = layout::build_adjacent_c32_zero_c37_raw_pointer_source(
        current_profile(),
    )
    .expect("current profile has exact raw-input pointer reentry");
    assert_eq!(
        plan.raw_pair.zero_pair.source,
        raw_input_pointer_select_source()
    );
    assert_eq!(plan.input_pointer_code_address, 47);
    assert_eq!(plan.halt_code_address, 48);
    assert_eq!(plan.raw_pair.low_store_code_address, 43);
    assert_eq!(
        layout::build_adjacent_c32_zero_c37_raw_pointer_source(
            historical_profile(),
        ),
        Err(layout::ZeroCellSourceError::UnsupportedProfile),
    );
}

fn raw_pointer_eof_marker_source() -> Vec<u8> {
    let mut source = raw_input_pointer_select_source();
    for (site, instruction) in [
        (48usize, b'j'),
        (49, b'j'),
        (50, b'o'),
        (51, b'o'),
        (52, b'o'),
        (53, b'*'),
        (54, b'<'),
        (55, b'v'),
    ] {
        source[site] = graphical(site, instruction);
    }
    source
}

#[test]
#[expect(
    clippy::indexing_slicing,
    clippy::panic_in_result_fn,
    reason = "56-step physical EOF marker and bounded binary witnesses"
)]
fn physical_raw_pointer_recovers_eof_only_marker_without_losing_saved_raw()
-> Result<(), String> {
    let profile = current_profile();
    let source = raw_pointer_eof_marker_source();
    assert_eq!(layout::admit_c23_probe_graphical_source(&source), Ok(()));
    let prepared = ProfileMachine::from_source(profile, &source, Vec::new())
        .map_err(|error| error.to_string())?;
    for (input, expected_output) in [
        (vec![], 106u8),
        (vec![0], 176),
        (vec![1], 18),
        (vec![2], 36),
        (vec![4], 176),
        (vec![23], 176),
        (vec![24], 176),
        (vec![34], 145),
        (vec![39], 176),
        (vec![47], 18),
        (vec![48], 176),
        (vec![49], 18),
        (vec![106], 132),
        (vec![125], 18),
        (vec![255], 133),
    ] {
        let mut guest = ProfileMachine::from_state(
            profile,
            prepared.memory().to_vec(),
            input.clone(),
            ProfileRegisters::default(),
        )
        .map_err(|error| error.to_string())?;
        let mut trace = Vec::new();
        let outcome = guest
            .run_traced(56, &mut |step| trace.push(*step))
            .map_err(|error| error.to_string())?;
        assert_eq!(
            outcome,
            RunOutcome::Terminated {
                reason: Termination::HaltInstruction,
                steps: 56,
            },
            "input {input:?}"
        );
        assert_eq!(trace[48].decoded, Some(b'j'));
        assert_eq!(trace[49].decoded, Some(b'j'));
        for position in 50..=52 {
            assert_eq!(trace[position].decoded, Some(b'o'));
        }
        assert_eq!(trace[53].decoded, Some(b'*'));
        assert_eq!(trace[54].decoded, Some(b'<'));
        assert_eq!(trace[55].decoded, Some(b'v'));
        assert_eq!(guest.output(), [expected_output]);
        assert_eq!(expected_output == 106, input.is_empty());
        let raw = input
            .first()
            .map_or(profile.eof_word(), |byte| u32::from(*byte));
        assert_eq!(guest.memory_word(LOW), Ok(raw));
        assert_eq!(guest.memory_word(HIGH), Ok(0));
        assert_eq!(guest.input_consumed(), usize::from(!input.is_empty()));
    }
    Ok(())
}

#[test]
#[expect(
    clippy::indexing_slicing,
    clippy::panic_in_result_fn,
    reason = "physical negative control proves raw EOF low byte is not a marker"
)]
fn skipping_selected_rotate_misclassifies_successful_byte_106_as_eof()
-> Result<(), String> {
    let profile = current_profile();
    let full = raw_pointer_eof_marker_source();
    let mut without_rotation = full.clone();
    without_rotation[53] = graphical(53, b'o');
    for (source, byte_output) in [(full, 132), (without_rotation, 106)] {
        let mut byte_guest =
            ProfileMachine::from_source(profile, &source, vec![106])
                .map_err(|error| error.to_string())?;
        assert_eq!(
            byte_guest.run(56).map_err(|error| error.to_string())?,
            RunOutcome::Terminated {
                reason: Termination::HaltInstruction,
                steps: 56,
            },
        );
        assert_eq!(byte_guest.output(), [byte_output]);
        assert_eq!(byte_guest.memory_word(LOW), Ok(106));
        assert_eq!(byte_guest.memory_word(HIGH), Ok(0));
        let mut eof_guest =
            ProfileMachine::from_source(profile, &source, Vec::new())
                .map_err(|error| error.to_string())?;
        assert_eq!(
            eof_guest.run(56).map_err(|error| error.to_string())?,
            RunOutcome::Terminated {
                reason: Termination::HaltInstruction,
                steps: 56,
            },
        );
        assert_eq!(eof_guest.output(), [106]);
    }
    Ok(())
}

#[test]
fn eof_marker_builder_matches_independent_layout_and_refuses_old_profile() {
    let plan = layout::build_adjacent_c32_zero_c37_raw_eof_marker_source(
        current_profile(),
    )
    .expect("current N15 graphical source supports real EOF-only marker");
    assert_eq!(
        plan.raw_pointer.raw_pair.zero_pair.source,
        raw_pointer_eof_marker_source()
    );
    assert_eq!(plan.raw_pointer.input_pointer_code_address, 47);
    assert_eq!(plan.marker_rotate_code_address, 53);
    assert_eq!(plan.marker_output_code_address, 54);
    assert_eq!(plan.halt_code_address, 55);
    assert_eq!(
        layout::build_adjacent_c32_zero_c37_raw_eof_marker_source(
            historical_profile(),
        ),
        Err(layout::ZeroCellSourceError::UnsupportedProfile),
    );
}

/// Exact acceptance witness for every successful byte and raw N15 EOF.
/// Run explicitly: each source-loaded N15 memory image has 14,348,907 words.
#[test]
#[ignore = "257 N15 images, 56 steps each; opt-in physical acceptance witness"]
#[expect(
    clippy::indexing_slicing,
    clippy::integer_division_remainder_used,
    clippy::arithmetic_side_effects,
    reason = "257 real N15 images and exact output sentinel"
)]
fn exhaustive_real_vm_raw_pair_preserved_with_eof_only_marker()
-> Result<(), String> {
    let profile = current_profile();
    let source = raw_pointer_eof_marker_source();
    assert_eq!(layout::admit_c23_probe_graphical_source(&source), Ok(()));
    let prepared = ProfileMachine::from_source(profile, &source, Vec::new())
        .map_err(|error| error.to_string())?;
    let mut finite_markers = BTreeSet::new();
    for raw in (0..=255u32).chain([profile.eof_word()]) {
        let input = if raw == profile.eof_word() {
            Vec::new()
        } else {
            vec![u8::try_from(raw).map_err(|error| error.to_string())?]
        };
        let mut vm = ProfileMachine::from_state(
            profile,
            prepared.memory().to_vec(),
            input.clone(),
            ProfileRegisters::default(),
        )
        .map_err(|error| error.to_string())?;
        assert_eq!(
            vm.run(56).map_err(|error| error.to_string())?,
            RunOutcome::Terminated {
                reason: Termination::HaltInstruction,
                steps: 56,
            },
            "raw {raw}"
        );
        assert_eq!(vm.memory_word(LOW), Ok(raw), "raw {raw}");
        assert_eq!(vm.memory_word(HIGH), Ok(0), "raw {raw}");
        assert_eq!(vm.output().len(), 1, "raw {raw}");
        assert_eq!(vm.input_consumed(), input.len(), "raw {raw}");
        let marker = vm.output()[0];
        if raw == profile.eof_word() {
            assert_eq!(marker, 0x6a, "EOF marker");
        } else {
            assert_ne!(marker, 0x6a, "false EOF for raw {raw}");
            _ = finite_markers.insert(marker);
        }
    }
    assert!(!finite_markers.is_empty());
    assert!(!finite_markers.contains(&0x6a));
    Ok(())
}

fn raw_pointer_eof_zero_source() -> Vec<u8> {
    let mut source = raw_pointer_eof_marker_source();
    for (site, opcode) in [(54, b'p'), (55, b'<'), (56, b'v')] {
        source[site] = graphical(site, opcode);
    }
    source
}

#[test]
fn physical_raw_pair_produces_true_eof_zero_word_without_destroying_input()
-> Result<(), String> {
    let profile = current_profile();
    let source = raw_pointer_eof_zero_source();
    assert_eq!(layout::admit_c23_probe_graphical_source(&source), Ok(()));
    let prepared = ProfileMachine::from_source(profile, &source, Vec::new())
        .map_err(|error| error.to_string())?;
    for input in [
        vec![],
        vec![0],
        vec![1],
        vec![2],
        vec![34],
        vec![37],
        vec![53],
        vec![59],
        vec![123],
        vec![127],
        vec![255],
        vec![255, 9],
    ] {
        let raw = input.first().map_or(profile.eof_word(), |b| u32::from(*b));
        let mut guest = ProfileMachine::from_state(
            profile,
            prepared.memory().to_vec(),
            input.clone(),
            ProfileRegisters::default(),
        )
        .map_err(|error| error.to_string())?;
        let mut trace = Vec::new();
        assert_eq!(
            guest
                .run_traced(57, &mut |step| trace.push(*step))
                .map_err(|error| error.to_string())?,
            RunOutcome::Terminated {
                reason: Termination::HaltInstruction,
                steps: 57,
            },
            "input {input:?}",
        );
        assert_eq!(trace[53].decoded, Some(b'*'));
        assert_eq!(trace[54].decoded, Some(b'p'));
        assert_eq!(trace[55].decoded, Some(b'<'));
        assert_eq!(trace[56].decoded, Some(b'v'));
        let predicate = trace[54].after.registers.accumulator;
        let data_word = trace[54]
            .memory_reads
            .data
            .ok_or("C54 must read a physical data operand")?;
        assert_eq!(
            predicate,
            scalar_crazy(
                data_word.value,
                trace[53].after.registers.accumulator
            ),
            "independent ternary oracle for input {input:?}",
        );
        assert_eq!(predicate == 0, input.is_empty(), "input {input:?}");
        let store_address = trace[54].before.registers.data_pointer;
        assert_eq!(
            trace[54].memory_reads.data.map(|read| read.address),
            Some(store_address),
            "input {input:?}",
        );
        assert_eq!(guest.memory_word(store_address), Ok(predicate));
        if !input.is_empty() {
            assert_eq!(
                trace[54].memory_delta.data.map(|write| write.after),
                Some(predicate),
                "input {input:?}",
            );
        }
        assert_eq!(guest.output(), [
            u8::try_from(predicate % 256).map_err(|error| error.to_string())?
        ]);
        assert_eq!(guest.output()[0] == 0, input.is_empty());
        assert_eq!(guest.memory_word(LOW), Ok(raw));
        assert_eq!(guest.memory_word(HIGH), Ok(0));
        assert_eq!(guest.input_consumed(), usize::from(!input.is_empty()));
    }
    Ok(())
}

#[test]
fn eof_zero_builder_matches_independent_source_and_rejects_classic_profile() {
    let plan = layout::build_adjacent_c32_zero_c37_raw_eof_zero_source(
        current_profile(),
    )
    .expect("source-loaded N15 EOF-zero predicate");
    assert_eq!(
        plan.raw_pointer.raw_pair.zero_pair.source,
        raw_pointer_eof_zero_source()
    );
    assert_eq!(plan.rotate_code_address, 53);
    assert_eq!(plan.zero_store_code_address, 54);
    assert_eq!(plan.output_code_address, 55);
    assert_eq!(plan.halt_code_address, 56);
    assert_eq!(
        layout::build_adjacent_c32_zero_c37_raw_eof_zero_source(
            historical_profile(),
        ),
        Err(layout::ZeroCellSourceError::UnsupportedProfile)
    );
}

#[test]
fn removing_real_eof_zero_store_exposes_raw_eof_low_byte() -> Result<(), String>
{
    let profile = current_profile();
    let source = raw_pointer_eof_zero_source();
    let mut missing_store = source.clone();
    missing_store[54] = graphical(54, b'o');
    for (candidate, expected) in [(source, 0u8), (missing_store, 106u8)] {
        let mut guest =
            ProfileMachine::from_source(profile, &candidate, Vec::new())
                .map_err(|error| error.to_string())?;
        assert_eq!(
            guest.run(57).map_err(|error| error.to_string())?,
            RunOutcome::Terminated {
                reason: Termination::HaltInstruction,
                steps: 57,
            },
        );
        assert_eq!(guest.output(), [expected]);
        assert_eq!(guest.memory_word(LOW), Ok(profile.eof_word()));
        assert_eq!(guest.memory_word(HIGH), Ok(0));
    }
    Ok(())
}

#[test]
#[ignore = "257 N15 images, 57 steps each; opt-in physical acceptance witness"]
fn exhaustive_real_vm_preserves_raw_and_eof_zero() -> Result<(), String> {
    let profile = current_profile();
    let source = raw_pointer_eof_zero_source();
    assert_eq!(layout::admit_c23_probe_graphical_source(&source), Ok(()));
    let prepared = ProfileMachine::from_source(profile, &source, Vec::new())
        .map_err(|error| error.to_string())?;
    for raw in (0..=255u32).chain([profile.eof_word()]) {
        let input = if raw == profile.eof_word() {
            Vec::new()
        } else {
            vec![u8::try_from(raw).map_err(|error| error.to_string())?]
        };
        let mut guest = ProfileMachine::from_state(
            profile,
            prepared.memory().to_vec(),
            input.clone(),
            ProfileRegisters::default(),
        )
        .map_err(|error| error.to_string())?;
        let mut trace = Vec::new();
        assert_eq!(
            guest
                .run_traced(57, &mut |step| trace.push(*step))
                .map_err(|error| error.to_string())?,
            RunOutcome::Terminated {
                reason: Termination::HaltInstruction,
                steps: 57,
            },
            "raw {raw}"
        );
        assert_eq!(trace[54].decoded, Some(b'p'), "raw {raw}");
        let predicate = trace[54].after.registers.accumulator;
        let data_word = trace[54]
            .memory_reads
            .data
            .ok_or("C54 must read a physical data operand")?;
        assert_eq!(
            predicate,
            scalar_crazy(
                data_word.value,
                trace[53].after.registers.accumulator
            ),
            "independent ternary oracle for raw {raw}",
        );
        assert_eq!(predicate == 0, raw == profile.eof_word(), "raw {raw}");
        assert_eq!(guest.output().len(), 1, "raw {raw}");
        assert_eq!(
            guest.output()[0] == 0,
            raw == profile.eof_word(),
            "raw {raw}"
        );
        let store_address = trace[54].before.registers.data_pointer;
        assert_eq!(
            trace[54].memory_reads.data.map(|read| read.address),
            Some(store_address),
            "raw {raw}",
        );
        assert_eq!(guest.memory_word(store_address), Ok(predicate));
        assert_eq!(guest.memory_word(LOW), Ok(raw), "raw {raw}");
        assert_eq!(guest.memory_word(HIGH), Ok(0), "raw {raw}");
        assert_eq!(guest.input_consumed(), input.len(), "raw {raw}");
    }
    Ok(())
}
