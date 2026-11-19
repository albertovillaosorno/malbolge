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
//   - A finite VM witness for repeated genuine mutations of one guest cell.
// - Must-Not:
//   - Claim C23 scalar updates, a compiled checksum, or a source-linked CFG.
// - Allows:
//   - Inputs: one source-controlled rotated loader and 257 signed inputs.
//   - Outputs: independently checked same-address p/p writes and guest bytes.
//   - Side effects: isolated bounded normative VM traces only.
// - Split-When:
//   - General stateful guest operation linking subsumes this exact probe.
// - Merge-When:
//   - The physical arithmetic linker owns repeated same-cell writes.
// - Summary:
//   - Real input drives two consecutive writes to the same mutable cell.

//! Two real guest `p` writes to one data word, not C32 arithmetic or C codegen.

#[path = "../src/compiler/malbolge-layout/composition/lib.rs"]
pub mod layout;

use std::collections::BTreeSet;
use std::iter::once;

use malbolge::{
    ProfileMachine, ProfileRegisters, RunOutcome, Termination, TraceInput,
    current_profile, historical_profile,
};

const TARGET: u32 = 95;
const LOADER_SEED: u32 = 7_174_457;
#[expect(
    clippy::type_complexity,
    reason = "three fixed code/data/read triples form the checked pointer chain"
)]
const RESET: [(usize, u32, u32); 3] =
    [(44, 96, 72), (45, 73, 61), (46, 62, 94)];

#[expect(
    clippy::arithmetic_side_effects,
    clippy::integer_division,
    clippy::integer_division_remainder_used,
    reason = "independent frozen fifteen-trit oracle, not production VM calls"
)]
const fn scalar_rotate(value: u32) -> u32 {
    value / 3 + (value % 3) * 4_782_969
}

#[expect(
    clippy::arithmetic_side_effects,
    clippy::integer_division_remainder_used,
    reason = "independent trit truth table for actual guest writes"
)]
fn scalar_crazy(mut data: u32, mut accumulator: u32) -> u32 {
    let mut result = 0u32;
    let mut place = 1u32;
    for _ in 0..15usize {
        let digit = match (data % 3, accumulator % 3) {
            (0 | 1, 0) | (2, 2) => 1,
            (1, 2) | (2, 0 | 1) => 2,
            _ => 0,
        };
        result += digit * place;
        data /= 3;
        accumulator /= 3;
        place *= 3;
    }
    result
}

fn source_with_same_cell_reset() -> Result<Vec<u8>, String> {
    layout::build_seeded_repeated_state_write_source(current_profile(), *b",H")
        .map_err(|error| format!("{error:?}"))
}

#[test]
fn repeated_state_source_refuses_invalid_profile_and_reset_seed() {
    assert_eq!(
        layout::build_seeded_repeated_state_write_source(
            historical_profile(),
            *b",H",
        ),
        Err(layout::RepeatedLoaderRotationError::UnsupportedProfile),
    );
    assert_eq!(
        layout::build_seeded_repeated_state_write_source(
            current_profile(),
            *b"Iy",
        ),
        Err(layout::RepeatedLoaderRotationError::InvalidResetSeed {
            tail: *b"Iy",
        }),
    );
}

#[test]
#[expect(
    clippy::cognitive_complexity,
    clippy::too_many_lines,
    clippy::panic_in_result_fn,
    clippy::integer_division_remainder_used,
    reason = "257 complete VM paths with independently checked memory deltas"
)]
fn signed_input_rewrites_one_real_guest_cell_twice() -> Result<(), String> {
    let profile = current_profile();
    let source = source_with_same_cell_reset()?;
    let loaded = ProfileMachine::from_source(profile, &source, vec![])
        .map_err(|error| error.to_string())?;
    assert_eq!(loaded.memory_word(TARGET), Ok(LOADER_SEED));
    let rotated = (0..9usize).fold(LOADER_SEED, |acc, _| scalar_rotate(acc));
    let mut unique_emitted = BTreeSet::new();
    for input in once(Vec::new())
        .chain((u8::MIN..=u8::MAX).map(|byte| vec![byte]))
        .chain(once(vec![42, 111, 255]))
    {
        let selected = input.first().copied();
        let input_word = selected.map_or_else(|| profile.eof_word(), u32::from);
        let first = scalar_crazy(rotated, input_word);
        let second = scalar_crazy(first, first);
        let emitted =
            u8::try_from(second % 256).map_err(|error| error.to_string())?;
        let mut vm = ProfileMachine::from_state(
            profile,
            loaded.memory().to_vec(),
            input,
            ProfileRegisters::default(),
        )
        .map_err(|error| error.to_string())?;
        let mut trace = Vec::new();
        let outcome = vm
            .run_traced(50, &mut |step| trace.push(*step))
            .map_err(|error| error.to_string())?;
        assert_eq!(outcome, RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 50,
        });
        assert_eq!(trace.len(), 50);
        let input_step = trace.get(39).ok_or("missing input step")?;
        assert_eq!(input_step.decoded, Some(profile.input_instruction()));
        assert_eq!(
            input_step.input,
            Some(selected.map_or(TraceInput::EndOfInput, TraceInput::Byte))
        );
        for (position, address, word) in RESET {
            let step = trace.get(position).ok_or("missing reset step")?;
            assert_eq!(step.decoded, Some(b'j'));
            assert_eq!(step.before.registers.data_pointer, address);
            assert_eq!(
                step.memory_reads.data.map(|read| read.value),
                Some(word)
            );
        }
        for (position, before, after) in
            [(43, rotated, first), (47, first, second)]
        {
            let write = trace.get(position).ok_or("missing crazy step")?;
            assert_eq!(write.decoded, Some(b'p'));
            assert_eq!(write.before.registers.data_pointer, TARGET);
            assert_eq!(
                write.memory_reads.data.map(|read| read.value),
                Some(before)
            );
            assert_eq!(write.after.registers.accumulator, after);
            assert_eq!(
                write.memory_delta.data.map(|delta| {
                    (delta.address, delta.before, delta.after)
                }),
                (before != after).then_some((TARGET, before, after))
            );
        }
        assert_eq!(vm.memory_word(TARGET), Ok(second));
        assert_eq!(trace.get(48).and_then(|step| step.output), Some(emitted));
        assert_eq!(vm.output(), &[emitted]);
        assert_eq!(vm.input_consumed(), usize::from(selected.is_some()));
        _ = unique_emitted.insert(emitted);
    }
    assert!(
        unique_emitted.len() > 1,
        "live input must change guest state"
    );
    Ok(())
}
