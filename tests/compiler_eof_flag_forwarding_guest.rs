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
//   - Finite post-EOF-flag code-transfer search on real N15 guest states.
// - Must-Not:
//   - Claim a general guest loop or impossibility beyond this exact layout.
// - Allows:
//   - Inputs: 257 authentic source-loaded input classes and 85 continuations.
//   - Outputs: checked indirect-target viability, not a published program.
//   - Side effects: isolated, bounded VM execution and pure scalar search.
// - Split-When:
//   - An independent physical layout solver handles relocated EOF branches.
// - Merge-When:
//   - Dynamic guest code-transfer verification subsumes this finite search.
// - Summary:
//   - The real EOF flag alone does not imply an executable code backedge.

//! Attempt an actual EOF-flag-to-code transfer before another return fixture.
//!
//! The complete source-C checksum remains the owning goal. This finite search
//! tests the next local physical gap: source cells C27..C30 of the authentic
//! 33-cell N15 EOF flag, with fixed loader seeds C31..C32. Every candidate
//! places zero to three `o/j/p/*` operations and then an `i`. Every one of the
//! 257 input classes supplies an actual 27-step VM state. Pure, independent
//! ternary arithmetic proposes the continuation target; the source cell at
//! that target must remain graphical for the required post-`i` encryption.
//! Failing this local grammar does not rule out new data pointers, code tails,
//! additional code cells, or an independently linked C23 EOF branch.

#[path = "../src/compiler/malbolge-layout/composition/lib.rs"]
pub mod layout;

use std::collections::BTreeMap;

use malbolge::{
    ProfileMachine, ProfileRegisters, RunOutcome, current_profile,
    decode_profile_instruction, encrypt_profile_cell,
};

const PREFIX_STEPS: usize = 27;
const CONTINUATION_START: usize = 27;
const CONTINUATION_END: usize = 30;
const SOURCE_CELLS: usize = 33;
const INPUT_CLASSES: usize = 257;
const OPERATION_CHOICES: [u8; 4] = *b"ojp*";

#[expect(
    clippy::arithmetic_side_effects,
    clippy::integer_division_remainder_used,
    clippy::indexing_slicing,
    reason = "independent finite base-three guest operand oracle"
)]
fn independent_crazy(mut data: u32, mut accumulator: u32) -> u32 {
    const TABLE: [[u32; 3]; 3] = [[1, 0, 0], [1, 0, 2], [2, 2, 1]];
    let mut result = 0u32;
    let mut place = 1u32;
    for _ in 0usize..15 {
        let row = usize::try_from(data % 3).unwrap_or_default();
        let column = usize::try_from(accumulator % 3).unwrap_or_default();
        result += TABLE[row][column] * place;
        place *= 3;
        data /= 3;
        accumulator /= 3;
    }
    result
}

#[expect(
    clippy::arithmetic_side_effects,
    clippy::integer_division_remainder_used,
    clippy::integer_division,
    reason = "independent fixed-width trit rotation"
)]
fn independent_rotate(word: u32) -> u32 {
    const MODULUS: u32 = 14_348_907;
    word / 3 + (word % 3) * (MODULUS / 3)
}

fn graphical_source_op(position: usize, op: u8) -> Option<u8> {
    let address = u32::try_from(position).ok()?;
    (33..=126u8).find(|byte| {
        decode_profile_instruction(u32::from(*byte), address) == Some(op)
    })
}

fn candidates() -> Vec<Vec<u8>> {
    let mut result = Vec::new();
    let mut previous = vec![Vec::new()];
    for _ in 0usize..=3 {
        result.extend(previous.iter().cloned());
        previous = previous
            .into_iter()
            .flat_map(|sequence| {
                OPERATION_CHOICES.into_iter().map(move |op| {
                    let mut next = sequence.clone();
                    next.push(op);
                    next
                })
            })
            .collect();
    }
    result
}

// Use full actual memory after the real 27-step source prefix. The prefix
// must not read or change the C27..C30 code patch: each candidate's graphical
// bytes therefore change only the future source, not any observed prefix.
// Model those source bytes before overlaying prospective p/* data writes.
fn proposed_target(
    machine: &ProfileMachine,
    original_source: &[u8],
    operations: &[u8],
) -> Result<Option<u32>, String> {
    let mut accumulator = machine.registers().accumulator;
    let mut data_pointer = machine.registers().data_pointer;
    let mut writes = BTreeMap::new();
    let mut patched_source = original_source.to_vec();
    for (offset, operation) in operations.iter().chain([&b'i']).enumerate() {
        let position = CONTINUATION_START.saturating_add(offset);
        *patched_source
            .get_mut(position)
            .ok_or("missing source position")? =
            graphical_source_op(position, *operation)
                .ok_or("missing graphical continuation encoding")?;
    }
    let first =
        u32::try_from(CONTINUATION_START).map_err(|error| error.to_string())?;
    let last =
        u32::try_from(CONTINUATION_END).map_err(|error| error.to_string())?;
    let read = |address: u32, overlay: &BTreeMap<u32, u32>| {
        if let Some(word) = overlay.get(&address) {
            return Ok(*word);
        }
        if (first..=last).contains(&address) {
            let index =
                usize::try_from(address).map_err(|error| error.to_string())?;
            let byte =
                patched_source.get(index).ok_or("missing source word")?;
            return Ok(u32::from(*byte));
        }
        machine
            .memory_word(address)
            .map_err(|error| error.to_string())
    };
    for op in operations {
        let word = read(data_pointer, &writes)?;
        match op {
            b'j' => data_pointer = word.saturating_add(1),
            b'o' => data_pointer = data_pointer.saturating_add(1),
            b'p' | b'*' => {
                accumulator = if *op == b'p' {
                    independent_crazy(word, accumulator)
                } else {
                    independent_rotate(word)
                };
                _ = writes.insert(data_pointer, accumulator);
                data_pointer = data_pointer.saturating_add(1);
            },
            _ => return Err(String::from("operation outside frozen grammar")),
        }
    }
    let target = read(data_pointer, &writes)?;
    // This is deliberately a necessary condition: the jump's post-step
    // encryption requires a graphical code target, but later decoding and
    // control-state correctness are stronger independent obligations.
    let fetched = read(target, &writes)?;
    if encrypt_profile_cell(fetched).is_none() {
        return Ok(None);
    }
    Ok(Some(target.saturating_add(1)))
}

#[test]
#[expect(
    clippy::too_many_lines,
    clippy::indexing_slicing,
    clippy::panic_in_result_fn,
    clippy::cognitive_complexity,
    clippy::excessive_nesting,
    reason = "257-class authentic guest state and finite 85-candidate search"
)]
fn real_eof_flag_has_no_short_graphical_two_arm_code_transfer()
-> Result<(), String> {
    let profile = current_profile();
    let plan = layout::build_guest_byte_c32_pair_eof_flag_source(profile)
        .map_err(|error| format!("{error:?}"))?;
    assert_eq!(plan.pair.source.len(), SOURCE_CELLS);
    let proposals = candidates();
    assert_eq!(proposals.len(), 85);
    for proposed in &proposals {
        for (offset, op) in proposed.iter().chain([&b'i']).enumerate() {
            assert!(
                graphical_source_op(CONTINUATION_START + offset, *op).is_some()
            );
        }
    }
    let prepared =
        ProfileMachine::from_source(profile, &plan.pair.source, Vec::new())
            .map_err(|error| error.to_string())?;
    let patch_begin =
        u32::try_from(CONTINUATION_START).map_err(|error| error.to_string())?;
    let patch_end =
        u32::try_from(CONTINUATION_END).map_err(|error| error.to_string())?;
    let mut byte_targets = vec![None::<u32>; proposals.len()];
    let mut all_byte_targets = vec![true; proposals.len()];
    let mut graphical_counts = vec![0usize; proposals.len()];
    let mut eof_targets = vec![None::<u32>; proposals.len()];
    for input_index in 0..INPUT_CLASSES {
        let input = u8::try_from(input_index)
            .map_or_else(|_error| Vec::new(), |byte| vec![byte]);
        let mut machine = ProfileMachine::from_state(
            profile,
            prepared.memory().to_vec(),
            input.clone(),
            ProfileRegisters::default(),
        )
        .map_err(|error| error.to_string())?;
        let mut touched_future_code = false;
        let result = machine.run_traced(PREFIX_STEPS, &mut |step| {
            for address in [
                Some(step.before.registers.code_pointer),
                step.memory_reads.data.map(|read| read.address),
                step.memory_delta.data.map(|write| write.address),
                step.memory_delta.encryption.map(|write| write.address),
            ]
            .into_iter()
            .flatten()
            {
                if (patch_begin..=patch_end).contains(&address) {
                    touched_future_code = true;
                }
            }
        });
        assert!(
            !touched_future_code,
            "candidate edits changed the 27-step prefix"
        );
        assert_eq!(
            result.map_err(|error| error.to_string())?,
            RunOutcome::BudgetExhausted { steps: PREFIX_STEPS }
        );
        assert_eq!(machine.input_consumed(), input.len());
        assert_eq!(
            machine.registers().accumulator,
            if input.is_empty() {
                15
            } else {
                0
            }
        );
        for (index, proposal) in proposals.iter().enumerate() {
            let target =
                proposed_target(&machine, &plan.pair.source, proposal)?;
            if input.is_empty() {
                eof_targets[index] = target;
            } else {
                graphical_counts[index] += usize::from(target.is_some());
                if input_index == 0 {
                    byte_targets[index] = target;
                } else if byte_targets[index] != target {
                    all_byte_targets[index] = false;
                }
            }
        }
    }
    let all_graphical = graphical_counts
        .iter()
        .filter(|&&count| count == 256)
        .count();
    let true_two_arm = proposals
        .iter()
        .enumerate()
        .filter(|(index, _)| {
            graphical_counts[*index] == 256
                && all_byte_targets[*index]
                && eof_targets[*index].is_some()
                && byte_targets[*index] != eof_targets[*index]
        })
        .count();
    assert_eq!(all_graphical, 0);
    assert_eq!(true_two_arm, 0);
    assert!(graphical_counts.iter().any(|count| *count > 0));
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    clippy::indexing_slicing,
    clippy::too_many_lines,
    reason = "independent scalar branch proposal checked against executed N15 i"
)]
fn sampled_continuations_match_actual_guest_jump_admission()
-> Result<(), String> {
    let profile = current_profile();
    let plan = layout::build_guest_byte_c32_pair_eof_flag_source(profile)
        .map_err(|error| format!("{error:?}"))?;
    // These cases cover zero-length code, pointer jumps, multiple sequential
    // pointer advances, and prospective data writes before a real i.
    for operations in
        [&b""[..], &b"j"[..], &b"jo"[..], &b"joo"[..], &b"p*j"[..]]
    {
        let mut source = plan.pair.source.clone();
        for (offset, &operation) in operations.iter().chain([&b'i']).enumerate()
        {
            let address = CONTINUATION_START + offset;
            source[address] = graphical_source_op(address, operation)
                .ok_or("unencodable physical continuation")?;
        }
        let loaded = ProfileMachine::from_source(profile, &source, Vec::new())
            .map_err(|error| error.to_string())?;
        for input in [Vec::new(), vec![0], vec![1], vec![31], vec![255]] {
            let mut vm = ProfileMachine::from_state(
                profile,
                loaded.memory().to_vec(),
                input.clone(),
                ProfileRegisters::default(),
            )
            .map_err(|error| error.to_string())?;
            assert_eq!(
                vm.run(PREFIX_STEPS).map_err(|error| error.to_string())?,
                RunOutcome::BudgetExhausted { steps: PREFIX_STEPS }
            );
            let predicted =
                proposed_target(&vm, &plan.pair.source, operations)?;
            let mut reached = Vec::new();
            let actual = vm.run_traced(operations.len() + 1, &mut |step| {
                reached
                    .push((step.before.registers.code_pointer, step.decoded));
            });
            assert_eq!(
                reached,
                operations
                    .iter()
                    .chain([&b'i'])
                    .enumerate()
                    .map(|(offset, op)| {
                        (
                            u32::try_from(CONTINUATION_START + offset)
                                .unwrap_or_default(),
                            Some(*op),
                        )
                    })
                    .collect::<Vec<_>>(),
                "physical decoder differs for {operations:?}, {input:?}"
            );
            assert_eq!(
                actual.is_ok(),
                predicted.is_some(),
                "scalar jump admission differs: {operations:?} {input:?}"
            );
            if let Some(code_pointer) = predicted {
                assert_eq!(vm.registers().code_pointer, code_pointer);
            }
        }
    }
    Ok(())
}
