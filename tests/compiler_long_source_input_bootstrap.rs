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
//   - Physical expanded-memory input storage with 261 source code cells.
// - Must-Not:
//   - Claim signed C23 input, linked checksum blocks, or a reusable loop.
// - Allows:
//   - Inputs: one immutable N15 source and all 257 raw input classes.
//   - Outputs: exact source mutation, pointer reentry and injected guest word.
//   - Side effects: bounded, isolated normative VM execution only.
// - Split-When:
//   - Source-C input frame lowering consumes the verified large-source route.
// - Merge-When:
//   - Complete mutable C23 checksum verifies the first SSA input store.
// - Summary:
//   - Loader-independent bootstrap can reach expanded data from long source.

//! Source-resident data-pointer bootstrap and real raw-byte store at C38.

#[path = "../src/compiler/malbolge-layout/composition/lib.rs"]
pub mod layout;

use std::collections::BTreeSet;

use malbolge::{
    ProfileMachine, RunOutcome, Termination, TraceInput, current_profile,
};

// This scalar table is independent of the product encoder and VM
// implementation.
#[expect(
    clippy::arithmetic_side_effects,
    clippy::integer_division_remainder_used,
    clippy::as_conversions,
    clippy::indexing_slicing,
    reason = "frozen 15-trit arithmetic oracle for an actual input store"
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
    clippy::cognitive_complexity,
    clippy::expect_used,
    clippy::indexing_slicing,
    clippy::too_many_lines,
    clippy::unwrap_used,
    reason = "nine physical input cases plus independent 257-class scalar proof"
)]
fn long_source_reaches_expanded_memory_and_retains_all_raw_inputs() {
    let profile = current_profile();
    let plan = layout::build_long_source_input_bootstrap_source(profile)
        .expect("expanded-data bootstrap must load from 256 graphical cells");
    assert_eq!(plan.source.len(), 261);
    assert_eq!((plan.input_code_address, plan.store_code_address), (37, 38));
    assert_eq!(
        (plan.modified_source_address, plan.return_source_address),
        (41, 58)
    );
    assert_eq!(plan.source[41], 92);
    assert_eq!(plan.source[58], 40);
    assert_eq!(&plan.source[259..], b">>");
    let huge_pointer = scalar_crazy(92, 0);
    assert_eq!(plan.high_pointer_word, huge_pointer);
    assert_eq!(plan.data_address, huge_pointer + 19);
    assert_eq!(plan.initial_data_word, scalar_crazy(0, 0));
    assert!(plan.data_address > u32::try_from(plan.source.len()).unwrap());

    let loaded = ProfileMachine::from_source(profile, &plan.source, Vec::new())
        .expect("source loader must derive its own expanded memory");
    assert_eq!(loaded.memory_word(plan.modified_source_address), Ok(92));
    assert_eq!(loaded.memory_word(plan.return_source_address), Ok(40));
    assert_eq!(
        loaded.memory_word(plan.data_address),
        Ok(plan.initial_data_word)
    );
    // The first 256-cell candidate's old M41 byte was never loadable.
    let mut rejected = plan.source.clone();
    rejected[41] = 35;
    assert!(
        ProfileMachine::from_source(profile, &rejected, Vec::new()).is_err(),
        "invalid source opcode at C41 must reject before guest execution"
    );
    let mut observed = BTreeSet::new();
    for raw in (0..=255u32).chain([profile.eof_word()]) {
        let encoded = scalar_crazy(plan.initial_data_word, raw);
        assert!(observed.insert(encoded), "input encoding collision {raw}");
        assert_eq!(scalar_crazy(plan.initial_data_word, encoded), raw);
    }
    assert_eq!(observed.len(), 257);
    for raw in [profile.eof_word(), 0, 1, 2, 3, 127, 128, 254, 255] {
        let input =
            u8::try_from(raw).map_or_else(|_| Vec::new(), |byte| vec![byte]);
        let mut vm = loaded
            .fork_with_input(input.clone())
            .expect("the verified source can fork to any unconsumed input");
        let mut steps = Vec::new();
        let outcome = vm.run_traced(40, &mut |step| steps.push(*step));
        assert_eq!(
            outcome,
            Ok(RunOutcome::Terminated {
                reason: Termination::HaltInstruction,
                steps: 40,
            }),
            "raw class {raw}"
        );
        assert_eq!(steps[0].decoded, Some(b'j'));
        assert_eq!(steps[1].decoded, Some(b'p'));
        assert_eq!(steps[1].before.registers.data_pointer, 41);
        assert_eq!(steps[1].after.registers.accumulator, huge_pointer);
        assert_eq!(steps[2].decoded, Some(b'o'));
        assert_eq!(steps[18].decoded, Some(b'j'));
        assert_eq!(steps[18].after.registers.data_pointer, 41);
        assert_eq!(steps[19].decoded, Some(b'j'));
        assert_eq!(
            steps[19].memory_reads.data.map(|read| read.value),
            Some(huge_pointer)
        );
        assert_eq!(steps[19].after.registers.data_pointer, huge_pointer + 1);
        assert_eq!(steps[37].decoded, Some(b'/'));
        assert_eq!(
            steps[37].input,
            Some(if input.is_empty() {
                TraceInput::EndOfInput
            } else {
                TraceInput::Byte(input[0])
            })
        );
        assert_eq!(steps[38].decoded, Some(b'p'));
        assert_eq!(steps[38].before.registers.data_pointer, plan.data_address);
        assert_eq!(
            steps[38].memory_reads.data.map(|read| read.value),
            Some(plan.initial_data_word)
        );
        let expected = scalar_crazy(plan.initial_data_word, raw);
        assert_eq!(steps[38].after.registers.accumulator, expected);
        assert_eq!(vm.memory_word(plan.data_address), Ok(expected));
        assert_eq!(
            vm.memory_word(plan.modified_source_address),
            Ok(huge_pointer)
        );
        assert_eq!(steps[39].decoded, Some(b'v'));
        assert_eq!(vm.input_consumed(), usize::from(!input.is_empty()));
        assert_eq!(vm.output(), []);
    }
}

#[test]
#[expect(
    clippy::expect_used,
    clippy::unwrap_used,
    clippy::indexing_slicing,
    clippy::missing_asserts_for_indexing,
    clippy::integer_division_remainder_used,
    reason = "fixed 261-cell source tail and independent six-phase oracle"
)]
fn changed_loader_tail_loses_verified_full_input_operand() {
    let profile = current_profile();
    let plan = layout::build_long_source_input_bootstrap_source(profile)
        .expect("canonical long input source");
    let mut mutated = plan.source.clone();
    mutated[259] = 33;
    mutated[260] = 33;
    // Independent scalar expansion: for the one required target address,
    // the six-phase recurrence depends only on the two graphical tail words.
    let scalar_loader = |bytes: &[u8]| {
        let mut previous = u32::from(bytes[259]);
        let mut latest = u32::from(bytes[260]);
        let residue = usize::try_from(plan.data_address).unwrap() - bytes.len();
        for _ in 0..=(residue % 6) {
            let next = scalar_crazy(previous, latest);
            previous = latest;
            latest = next;
        }
        latest
    };
    assert_eq!(scalar_loader(&plan.source), plan.initial_data_word);
    assert_ne!(scalar_loader(&mutated), plan.initial_data_word);
}
