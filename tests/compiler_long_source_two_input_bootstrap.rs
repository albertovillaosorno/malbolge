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
//   - Source-loaded high-memory read/read storage across a source mutation.
// - Must-Not:
//   - Claim C23 signed EOF normalization or a linked mutable checksum loop.
// - Allows:
//   - Inputs: immutable graphical source, N15 binary streams and EOF.
//   - Outputs: exact physical control, two disjoint injective stores.
//   - Side effects: isolated normative VM execution only.
// - Split-When:
//   - Generic compiler SSA frame lowering consumes this high-memory route.
// - Merge-When:
//   - A verified source-C input frame fully replaces this physical probe.
// - Summary:
//   - A real jump skips a mutated code cell to preserve two guest inputs.

//! Two independent input stores following source-backed pointer bootstrap.

#[path = "../src/compiler/malbolge-layout/composition/lib.rs"]
pub mod layout;

use std::collections::BTreeSet;

use malbolge::{
    ProfileMachine, RunOutcome, Termination, TraceInput, current_profile,
};

// The scalar trit oracle deliberately does not invoke the product VM/encoder.
#[expect(
    clippy::arithmetic_side_effects,
    clippy::integer_division_remainder_used,
    clippy::as_conversions,
    clippy::indexing_slicing,
    reason = "finite independent 15-trit N15 acceptance oracle"
)]
fn scalar_crazy(mut data: u32, mut accumulator: u32) -> u32 {
    const TABLE: [[u32; 3]; 3] = [[1, 0, 0], [1, 0, 2], [2, 2, 1]];
    let mut result = 0;
    let mut place = 1;
    for _ in 0_u32..15_u32 {
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
    clippy::expect_used,
    clippy::indexing_slicing,
    clippy::too_many_lines,
    clippy::cognitive_complexity,
    reason = "physical source coordinates and bounded input classes are fixed"
)]
fn code_jump_skips_modified_source_and_writes_two_lossless_inputs() {
    let profile = current_profile();
    let plan = layout::build_long_source_two_input_bootstrap_source(profile)
        .expect("source-backed two-input code continuation must load");
    let first = layout::build_long_source_input_bootstrap_source(profile)
        .expect("original one-input bootstrap must remain unchanged");
    assert_eq!(plan.source.len(), 261);
    assert_eq!(
        (plan.first_input_code_address, plan.first_store_code_address),
        (37, 38)
    );
    assert_eq!((plan.jump_code_address, plan.resume_code_address), (39, 63));
    assert_eq!(
        (
            plan.second_input_code_address,
            plan.second_store_code_address
        ),
        (66, 67)
    );
    assert_eq!(plan.halt_code_address, 68);
    assert_eq!(plan.modified_source_address, 41);
    assert_eq!(plan.source[41], 92);
    assert_eq!(&plan.source[259..], b">>");
    assert_eq!(plan.second_data_address - plan.first_data_address, 6);
    assert_eq!(plan.first_initial_data_word, scalar_crazy(0, 0));
    assert_eq!(plan.second_initial_data_word, scalar_crazy(0, 0));
    for index in 0..261usize {
        if [39, 66, 67, 68].contains(&index) {
            assert_ne!(plan.source[index], first.source[index]);
        } else {
            assert_eq!(plan.source[index], first.source[index]);
        }
    }

    // A raw scalar EOF is not equal to any byte, and each store is injective.
    let mut encodings = BTreeSet::new();
    for raw in (0..=255u32).chain([profile.eof_word()]) {
        let encoded = scalar_crazy(plan.first_initial_data_word, raw);
        assert!(encodings.insert(encoded), "collision at raw input {raw}");
        assert_eq!(scalar_crazy(plan.second_initial_data_word, encoded), raw);
    }
    assert_eq!(encodings.len(), 257);

    let loaded = ProfileMachine::from_source(profile, &plan.source, Vec::new())
        .expect("the graphical source must load without memory overrides");
    assert_eq!(loaded.memory_word(plan.modified_source_address), Ok(92));
    for input in [vec![], vec![0, 255, 123], vec![255, 0], vec![128], vec![
        1, 2,
    ]] {
        let first_raw = input
            .first()
            .map_or_else(|| profile.eof_word(), |byte| u32::from(*byte));
        let second_raw = input
            .get(1)
            .map_or_else(|| profile.eof_word(), |byte| u32::from(*byte));
        let mut vm = loaded
            .fork_with_input(input.clone())
            .expect("fresh unread input");
        let mut steps = Vec::new();
        let outcome = vm.run_traced(46, &mut |step| steps.push(*step));
        assert_eq!(
            outcome,
            Ok(RunOutcome::Terminated {
                reason: Termination::HaltInstruction,
                steps: 46,
            }),
            "input {input:?}"
        );
        assert_eq!(steps.len(), 46);
        assert_eq!(steps[37].decoded, Some(b'/'));
        assert_eq!(
            steps[37].input,
            Some(input.first().map_or(TraceInput::EndOfInput, |byte| {
                TraceInput::Byte(*byte)
            }))
        );
        assert_eq!(steps[38].decoded, Some(b'p'));
        assert_eq!(
            steps[38].before.registers.data_pointer,
            plan.first_data_address
        );
        assert_eq!(steps[39].decoded, Some(b'i'));
        assert_eq!(
            steps[39].memory_reads.data.map(|read| read.value),
            Some(62)
        );
        assert_eq!(steps[40].before.registers.code_pointer, 63);
        assert_eq!(steps[40].decoded, Some(b'o'));
        assert_eq!(steps[41].decoded, Some(b'o'));
        assert_eq!(steps[42].decoded, Some(b'o'));
        assert_eq!(steps[43].decoded, Some(b'/'));
        assert_eq!(
            steps[43].input,
            Some(input.get(1).map_or(TraceInput::EndOfInput, |byte| {
                TraceInput::Byte(*byte)
            }))
        );
        assert_eq!(steps[44].decoded, Some(b'p'));
        assert_eq!(
            steps[44].before.registers.data_pointer,
            plan.second_data_address
        );
        assert_eq!(steps[45].decoded, Some(b'v'));
        assert_eq!(
            vm.memory_word(plan.modified_source_address),
            Ok(scalar_crazy(92, 0))
        );
        assert_eq!(
            vm.memory_word(plan.first_data_address),
            Ok(scalar_crazy(plan.first_initial_data_word, first_raw))
        );
        assert_eq!(
            vm.memory_word(plan.second_data_address),
            Ok(scalar_crazy(plan.second_initial_data_word, second_raw))
        );
        assert_eq!(vm.input_consumed(), input.len().min(2));
        assert_eq!(vm.output(), []);
    }
}

#[test]
#[expect(
    clippy::expect_used,
    reason = "first-stage halt cannot fake a second guest read"
)]
fn early_halt_preserves_second_operand_and_does_not_read_again() {
    let profile = current_profile();
    let plan = layout::build_long_source_two_input_bootstrap_source(profile)
        .expect("continued source must be loadable");
    let first = layout::build_long_source_input_bootstrap_source(profile)
        .expect("first-stage source must be loadable");
    let mut vm =
        ProfileMachine::from_source(profile, &first.source, vec![0, 255])
            .expect("original staged source must pass canonical loading");
    assert_eq!(
        vm.run(40),
        Ok(RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 40,
        })
    );
    assert_eq!(vm.input_consumed(), 1);
    assert_eq!(
        vm.memory_word(plan.second_data_address),
        Ok(plan.second_initial_data_word)
    );
    assert_eq!(
        vm.memory_word(plan.first_data_address),
        Ok(scalar_crazy(plan.first_initial_data_word, 0))
    );
}
