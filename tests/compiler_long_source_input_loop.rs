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
//   - Bounded source-loaded N15 input revisits and true code-cell mutation.
// - Must-Not:
//   - Claim a reusable source-C loop, signed EOF or checksum publication.
// - Allows:
//   - Inputs: graphical source and finite binary streams including EOF.
//   - Outputs: authentic XLAT2 revisits, reads, stores and exact guest halt.
//   - Side effects: isolated normative VM execution only.
// - Split-When:
//   - Complete C23 CFG linkage owns reusable guest input-loop semantics.
// - Merge-When:
//   - The verified physical guest linker consumes bounded code revisits.
// - Summary:
//   - Twelve actual backward transfers over self-encrypting input code.

//! Real backward guest input control, with an independently checked schedule.

#[path = "../src/compiler/malbolge-layout/composition/lib.rs"]
pub mod layout;

use std::array;
use std::collections::BTreeSet;

use malbolge::{
    ProfileMachine, RunOutcome, Termination, TraceInput, current_profile,
    decode_profile_instruction, encrypt_profile_cell,
};

// This independent scalar table never invokes the product VM's crazy helper.
#[expect(
    clippy::arithmetic_side_effects,
    clippy::integer_division_remainder_used,
    clippy::as_conversions,
    clippy::indexing_slicing,
    reason = "fixed 15-trit reference arithmetic and exact table entries"
)]
fn scalar_crazy(mut left: u32, mut right: u32) -> u32 {
    const TABLE: [[u32; 3]; 3] = [[1, 0, 0], [1, 0, 2], [2, 2, 1]];
    let mut result = 0;
    let mut place = 1;
    for _ in 0u32..15u32 {
        result += TABLE[(left % 3) as usize][(right % 3) as usize] * place;
        left /= 3;
        right /= 3;
        place *= 3;
    }
    result
}

#[test]
#[expect(
    clippy::expect_used,
    clippy::indexing_slicing,
    clippy::too_many_lines,
    clippy::cognitive_complexity,
    clippy::excessive_nesting,
    reason = "fixed 115-step physical code and oracle proof"
)]
fn real_twelve_backedge_input_loop_self_encrypts_to_a_true_halt() {
    const READ_STEPS: [usize; 5] = [37, 43, 73, 96, 103];
    let profile = current_profile();
    let plan = layout::build_long_source_finite_input_loop_source(profile)
        .expect("source loaded, loader-derived input-loop backedge");
    let original =
        layout::build_long_source_two_input_bootstrap_source(profile)
            .expect("original source is the exact one-site control baseline");
    assert_eq!(plan.source.len(), 261);
    assert_eq!(plan.loop_entry_code_address, 63);
    assert_eq!(plan.backedge_code_address, 68);
    assert_eq!(plan.final_halt_code_address, 65);
    assert_eq!(plan.first_data_address, original.first_data_address);
    assert_eq!(plan.second_data_address, original.second_data_address);
    assert_eq!(plan.initial_data_word, original.first_initial_data_word);
    assert_eq!(plan.initial_data_word, original.second_initial_data_word);
    for (index, (&actual, &baseline)) in
        plan.source.iter().zip(&original.source).enumerate()
    {
        if index == 68 {
            assert_ne!(actual, baseline);
        } else {
            assert_eq!(actual, baseline, "unexpected source edit at {index}");
        }
    }

    // Five N15 reads can observe independent byte/EOF values, even though
    // their C65/C66 positions are self-encrypted between loop iterations.
    let loaded = ProfileMachine::from_source(profile, &plan.source, Vec::new())
        .expect("all 261 bytes must load under normative N15 rules");
    for input in [
        vec![],
        vec![0],
        vec![255, 0],
        vec![1, 2, 3, 4, 5, 6, 7],
        vec![128, 0, 255, 0, 128],
    ] {
        let mut vm = loaded
            .fork_with_input(input.clone())
            .expect("fresh input on a verified unchanged source checkpoint");
        let mut steps = Vec::new();
        let outcome = vm.run_traced(115, &mut |step| steps.push(*step));
        assert_eq!(
            outcome,
            Ok(RunOutcome::Terminated {
                reason: Termination::HaltInstruction,
                steps: 115,
            }),
            "guest loop must halt with exact physical v for {input:?}"
        );
        assert_eq!(steps.len(), 115);
        assert_eq!(vm.input_consumed(), input.len().min(5));
        assert_eq!(vm.output(), []);
        assert_eq!(steps[39].decoded, Some(b'i'));
        assert_eq!(steps[39].before.registers.code_pointer, 39);
        assert_eq!(steps[40].before.registers.code_pointer, 63);

        let mut observed_reads = Vec::new();
        for (index, step) in steps.iter().enumerate() {
            if let Some(read) = step.input {
                observed_reads.push(index);
                let input_index = READ_STEPS
                    .iter()
                    .position(|&expected| expected == index)
                    .expect("no unanchored input in the revisited source");
                let expected = input
                    .get(input_index)
                    .map_or(TraceInput::EndOfInput, |byte| {
                        TraceInput::Byte(*byte)
                    });
                assert_eq!(read, expected);
                assert_eq!(step.decoded, Some(b'/'));
            }
        }
        assert_eq!(observed_reads, READ_STEPS);

        // This scalar XLAT2 oracle replays actual graphical source bytes at
        // each visited C63..C67. The indirect jump encrypts physical
        // C62 before incrementing to C63; C63 is encrypted on its own visit.
        let mut code: [u32; 5] =
            array::from_fn(|slot| u32::from(plan.source[63 + slot]));
        assert_eq!(
            steps[39].memory_delta.encryption.map(|write| write.address),
            Some(62)
        );
        for iteration in 0..12usize {
            for (slot, cell) in code.iter_mut().enumerate() {
                let index = 40 + 6 * iteration + slot;
                let address =
                    u32::try_from(63 + slot).expect("five source slots");
                let trace = &steps[index];
                assert_eq!(trace.before.registers.code_pointer, address);
                assert_eq!(
                    trace.fetched_cell,
                    Some(*cell),
                    "iteration {iteration} slot {slot} trace index {index}"
                );
                assert_eq!(
                    trace.decoded,
                    decode_profile_instruction(*cell, address)
                );
                *cell = encrypt_profile_cell(*cell)
                    .expect("each nonterminal visit self-encrypts");
            }
            let index = 45 + 6 * iteration;
            let jump = &steps[index];
            assert_eq!(jump.before.registers.code_pointer, 68);
            assert_eq!(jump.decoded, Some(b'i'));
            assert_eq!(
                jump.before.registers.data_pointer,
                plan.second_data_address
                    .checked_add(
                        1 + 6 * u32::try_from(iteration)
                            .expect("twelve iterations fit a u32")
                    )
                    .expect("bounded pointer stride fits N15")
            );
            assert_eq!(jump.memory_reads.data.map(|read| read.value), Some(62));
            assert_eq!(jump.after.registers.code_pointer, 63);
            assert_eq!(
                jump.memory_delta.encryption.map(|write| write.address),
                Some(62)
            );
        }
        for (slot, cell) in code.iter().enumerate().take(3) {
            let index = 112 + slot;
            let address = u32::try_from(63 + slot).expect("final source slots");
            assert_eq!(steps[index].before.registers.code_pointer, address);
            assert_eq!(steps[index].fetched_cell, Some(*cell));
            assert_eq!(
                steps[index].decoded,
                decode_profile_instruction(*cell, address)
            );
        }
        assert_eq!(steps[114].decoded, Some(b'v'));
        assert!(steps[114].memory_delta.encryption.is_none());

        let first_raw = input
            .first()
            .map_or_else(|| profile.eof_word(), |byte| u32::from(*byte));
        let second_raw = input
            .get(1)
            .map_or_else(|| profile.eof_word(), |byte| u32::from(*byte));
        assert_eq!(
            vm.memory_word(plan.first_data_address),
            Ok(scalar_crazy(plan.initial_data_word, first_raw))
        );
        assert_eq!(
            vm.memory_word(plan.second_data_address),
            Ok(scalar_crazy(plan.initial_data_word, second_raw))
        );
        assert_eq!(vm.memory_word(41), Ok(scalar_crazy(92, 0)));
    }

    // Preserve all 257 raw N15 input images at both written cells.
    let images = (0..=255u32)
        .chain([profile.eof_word()])
        .map(|raw| scalar_crazy(plan.initial_data_word, raw))
        .collect::<BTreeSet<_>>();
    assert_eq!(images.len(), 257);
}

#[test]
#[expect(
    clippy::expect_used,
    reason = "the single-cell change must distinguish backedge from old halt"
)]
fn unchanged_two_read_source_stops_before_revisiting_input_code() {
    let profile = current_profile();
    let original =
        layout::build_long_source_two_input_bootstrap_source(profile)
            .expect("original two-input source");
    let extended = layout::build_long_source_finite_input_loop_source(profile)
        .expect("repeat source must remain valid");
    assert_ne!(original.source.get(68), extended.source.get(68));
    let mut vm = ProfileMachine::from_source(profile, &original.source, vec![
        1, 2, 3, 4, 5, 6,
    ])
    .expect("original source loads");
    assert_eq!(
        vm.run(115),
        Ok(RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 46,
        })
    );
    assert_eq!(vm.input_consumed(), 2);
}
