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
//   - Independent source-loaded zero-word synthesis and live N15 VM evidence.
// - Must-Not:
//   - Treat one zero cell as canonical two-cell C32 zero initialization.
// - Allows:
//   - Inputs: 94 graphical phases, all legal tail bytes, initial guest A=0.
//   - Outputs: exhaustive independent loader census and physical zero writes.
//   - Side effects: isolated guest VM state; no target checksum publication.
// - Split-When:
//   - A source-C signed C32 zero initializer reaches executable guest writes.
// - Merge-When:
//   - The physical compiler has verified general local-state initialization.
// - Summary:
//   - A real guest can write a zero word not present in virgin source memory.

//! A source-loaded 15-trit zero word, distinguished from C23 C32 zero pairs.

#[path = "../src/compiler/malbolge-layout/composition/lib.rs"]
pub mod layout;

use std::collections::BTreeSet;

use malbolge::{
    ProfileMachine, ProfileRegisters, RunOutcome, Termination, TraceInput,
    current_profile,
    decode_profile_instruction, historical_profile,
};

const PREFIX_BOUND: usize = 94;
const SOURCE: &[u8] = b"DCBA@?>=<;|32DT";
const MODULUS: u32 = 14_348_907;

#[expect(
    clippy::arithmetic_side_effects,
    clippy::integer_division_remainder_used,
    clippy::indexing_slicing,
    reason = "independent ternary truth table, not production arithmetic"
)]
fn independent_crazy(mut data: u32, mut accumulator: u32) -> u32 {
    let table = [[1u32, 0, 0], [1, 0, 2], [2, 2, 1]];
    let mut result = 0;
    let mut place = 1;
    for _ in 0usize..15 {
        result += table[usize::try_from(data % 3).unwrap_or(3)]
            [usize::try_from(accumulator % 3).unwrap_or(3)]
            * place;
        data /= 3;
        accumulator /= 3;
        place *= 3;
    }
    result
}

fn encode(opcode: u8, position: usize) -> Result<u8, String> {
    (33u8..=126)
        .find(|byte| {
            decode_profile_instruction(
                u32::from(*byte),
                u32::try_from(position).unwrap_or(u32::MAX),
            ) == Some(opcode)
        })
        .ok_or_else(|| format!("missing graphical C{position} opcode {opcode}"))
}

#[expect(
    clippy::arithmetic_side_effects,
    clippy::indexing_slicing,
    clippy::integer_division_remainder_used,
    reason = "independent source-tail recurrence across six exact phases"
)]
fn loader_word(source: &[u8], address: usize) -> u32 {
    let mut older = u32::from(source[source.len() - 2]);
    let mut newer = u32::from(source[source.len() - 1]);
    for _ in 0..=((address - source.len()) % 6) {
        let next = independent_crazy(older, newer);
        older = newer;
        newer = next;
    }
    newer
}

fn graphical_tail(tail: u8, position: usize) -> bool {
    decode_profile_instruction(
        u32::from(tail),
        u32::try_from(position).unwrap_or(u32::MAX),
    )
    .is_some_and(|decoded| b"ji*p</vo".contains(&decoded))
}

#[test]
#[expect(
    clippy::cognitive_complexity,
    clippy::indexing_slicing,
    clippy::panic_in_result_fn,
    reason = "complete independent N15 source prefix and graphical tail census"
)]
fn zero_word_source_matches_independent_complete_prefix_tail_search()
-> Result<(), String> {
    let mut valid = Vec::<(Vec<u8>, u32, u32, u32, u32)>::new();
    let mut checked = 0usize;
    for prefix in 0..PREFIX_BOUND {
        let mut source = (0..prefix)
            .map(|position| encode(b'o', position))
            .collect::<Result<Vec<_>, _>>()?;
        for opcode in b"jppv" {
            source.push(encode(*opcode, source.len())?);
        }
        let data_base = usize::from(source[prefix]) + 1;
        if data_base <= source.len() + 1
            || data_base + 1
                >= usize::try_from(current_profile().memory_words())
                    .map_err(|error| error.to_string())?
        {
            continue;
        }
        for tail in 33..=126u8 {
            if !graphical_tail(tail, source.len()) {
                continue;
            }
            source.push(tail);
            checked += 1;
            let first = loader_word(&source, data_base);
            let second = loader_word(&source, data_base + 1);
            let intermediate = independent_crazy(first, 0);
            if independent_crazy(second, intermediate) == 0 {
                valid.push((
                    source.clone(),
                    u32::try_from(data_base)
                        .map_err(|error| error.to_string())?,
                    first,
                    second,
                    intermediate,
                ));
            }
            _ = source.pop();
        }
    }
    assert_eq!(checked, 520);
    assert_eq!(valid.len(), 43);
    assert_eq!(valid[0], (SOURCE.to_vec(), 125, 7_174_397, 84, 7_174_481),);
    let plan = layout::build_zero_cell_source(current_profile())
        .map_err(|error| format!("{error:?}"))?;
    assert_eq!(
        (
            plan.source,
            plan.first_data_address,
            plan.first_initial_word,
            plan.second_initial_word,
            plan.first_written_word,
        ),
        valid[0],
    );
    assert_eq!(plan.zero_data_address, 126);
    assert_eq!(plan.zero_store_code_address, 12);
    Ok(())
}

#[test]
fn original_graphical_loader_never_supplies_an_initial_zero_word() {
    let mut generated = BTreeSet::new();
    let mut min_generated = MODULUS;
    for first in 33..=126u32 {
        for second in 33..=126u32 {
            let (mut older, mut newer) = (first, second);
            for _ in 0usize..6 {
                let next = independent_crazy(older, newer);
                assert_ne!(next, 0);
                min_generated = min_generated.min(next);
                _ = generated.insert(next);
                (older, newer) = (newer, next);
            }
        }
    }
    assert_eq!(min_generated, 27);
    assert_eq!(generated.len(), 297);
    assert!(!generated.contains(&0));
}

#[test]
#[expect(
    clippy::cognitive_complexity,
    clippy::indexing_slicing,
    clippy::panic_in_result_fn,
    reason = "two genuine data writes and normative N15 guest encryption"
)]
fn real_guest_writes_zero_with_two_source_loaded_crazy_operations()
-> Result<(), String> {
    let profile = current_profile();
    let plan = layout::build_zero_cell_source(profile)
        .map_err(|error| format!("{error:?}"))?;
    let prepared = ProfileMachine::from_source(profile, &plan.source, vec![])
        .map_err(|error| error.to_string())?;
    assert_eq!(prepared.memory_word(plan.first_data_address), Ok(7_174_397));
    assert_eq!(prepared.memory_word(plan.zero_data_address), Ok(84));
    for input in [vec![], vec![0], vec![0xff, 0, 0x80]] {
        let mut guest = ProfileMachine::from_state(
            profile,
            prepared.memory().to_vec(),
            input,
            ProfileRegisters::default(),
        )
        .map_err(|error| error.to_string())?;
        let mut trace = Vec::new();
        let outcome = guest
            .run_traced(14, &mut |step| trace.push(*step))
            .map_err(|error| error.to_string())?;
        assert_eq!(outcome, RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 14,
        });
        assert_eq!(trace.len(), 14);
        for step in trace.iter().take(10) {
            assert_eq!(step.decoded, Some(b'o'));
            assert!(step.memory_delta.encryption.is_some());
        }
        assert_eq!(trace[10].decoded, Some(b'j'));
        assert_eq!(trace[10].after.registers.data_pointer, 125);
        for (position, address, before, after) in [
            (11usize, 125u32, 7_174_397u32, 7_174_481u32),
            (12, 126, 84, 0),
        ] {
            let step = &trace[position];
            assert_eq!(step.decoded, Some(b'p'));
            assert_eq!(step.before.registers.data_pointer, address);
            assert_eq!(
                step.memory_reads
                    .data
                    .map(|read| (read.address, read.value)),
                Some((address, before)),
            );
            assert_eq!(step.after.registers.accumulator, after);
            assert_eq!(
                step.memory_delta
                    .data
                    .map(|write| (write.address, write.after)),
                Some((address, after)),
            );
            assert!(step.memory_delta.encryption.is_some());
            assert_eq!(guest.memory_word(address), Ok(after));
        }
        assert_eq!(trace[13].decoded, Some(b'v'));
        assert_eq!(guest.input_consumed(), 0);
        assert_eq!(guest.output(), &[]);
    }
    Ok(())
}

#[test]
fn zero_cell_emitter_refuses_historical_profile() {
    assert_eq!(
        layout::build_zero_cell_source(historical_profile()),
        Err(layout::ZeroCellSourceError::UnsupportedProfile),
    );
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "negative entry-register witness must prove the result is nonzero"
)]
fn unknown_entry_accumulator_cannot_use_the_initial_zero_contract()
-> Result<(), String> {
    let profile = current_profile();
    let plan = layout::build_zero_cell_source(profile)
        .map_err(|error| format!("{error:?}"))?;
    let prepared = ProfileMachine::from_source(profile, &plan.source, vec![])
        .map_err(|error| error.to_string())?;
    let mut guest = ProfileMachine::from_state(
        profile,
        prepared.memory().to_vec(),
        vec![],
        ProfileRegisters {
            accumulator: 3,
            ..ProfileRegisters::default()
        },
    )
    .map_err(|error| error.to_string())?;
    assert_eq!(
        guest.run(14).map_err(|error| error.to_string())?,
        RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 14,
        },
    );
    assert_eq!(guest.memory_word(plan.zero_data_address), Ok(3));
    assert_ne!(guest.memory_word(plan.zero_data_address), Ok(0));
    Ok(())
}

#[expect(
    clippy::arithmetic_side_effects,
    clippy::integer_division_remainder_used,
    clippy::integer_division,
    reason = "independent exact 15-trit rotation oracle"
)]
fn independent_rotate(word: u32) -> u32 {
    let modulus = 3u32.pow(15);
    word / 3 + (word % 3) * (modulus / 3)
}

#[test]
#[expect(
    clippy::cognitive_complexity,
    clippy::indexing_slicing,
    clippy::panic_in_result_fn,
    clippy::excessive_nesting,
    clippy::too_many_lines,
    reason = "independent complete 94-phase graphical two-tail zero census"
)]
fn unknown_accumulator_zero_matches_independent_source_census()
-> Result<(), String> {
    let mut matching = Vec::<(Vec<u8>, u32, [u32; 3], [u32; 3])>::new();
    let mut checked = 0usize;
    for prefix in 0..PREFIX_BOUND {
        let mut source = (0..prefix)
            .map(|position| encode(b'o', position))
            .collect::<Result<Vec<_>, _>>()?;
        for opcode in b"j*ppv" {
            source.push(encode(*opcode, source.len())?);
        }
        let first_address = usize::from(source[prefix]) + 1;
        if first_address <= source.len() + 2 {
            continue;
        }
        for first in 33..=126u8 {
            if !graphical_tail(first, source.len()) {
                continue;
            }
            source.push(first);
            for last in 33..=126u8 {
                if !graphical_tail(last, source.len()) {
                    continue;
                }
                source.push(last);
                checked += 1;
                let initial = [
                    loader_word(&source, first_address),
                    loader_word(&source, first_address + 1),
                    loader_word(&source, first_address + 2),
                ];
                let first_result = independent_rotate(initial[0]);
                let second_result = independent_crazy(initial[1], first_result);
                let third_result = independent_crazy(initial[2], second_result);
                if second_result == 0 {
                    matching.push((
                        source.clone(),
                        u32::try_from(first_address)
                            .map_err(|error| error.to_string())?,
                        initial,
                        [first_result, second_result, third_result],
                    ));
                }
                _ = source.pop();
            }
            _ = source.pop();
        }
    }
    assert!(checked > 1_000);
    assert!(matching.len() >= 3);
    assert_eq!(
        matching[0],
        (b"DC&$:9K!6".to_vec(), 39, [7_174_483, 27, 7_174_483], [
            7_174_463, 0, 7_174_483
        ],),
    );
    let plan = layout::build_accumulator_independent_zero_cell_source(
        current_profile(),
    )
    .map_err(|error| format!("{error:?}"))?;
    assert_eq!(
        (
            plan.source,
            plan.first_data_address,
            plan.initial_words,
            plan.written_words,
        ),
        matching[0],
    );
    assert_eq!(plan.zero_store_code_address, 4);
    assert_eq!(plan.input_code_address, None);
    Ok(())
}

#[test]
#[expect(
    clippy::indexing_slicing,
    clippy::panic_in_result_fn,
    clippy::cognitive_complexity,
    clippy::too_many_lines,
    reason = "real N15 self-encryption and three physical data writes"
)]
fn real_guest_zero_write_survives_unknown_incoming_accumulator()
-> Result<(), String> {
    let profile = current_profile();
    let plan = layout::build_accumulator_independent_zero_cell_source(profile)
        .map_err(|error| format!("{error:?}"))?;
    let prepared = ProfileMachine::from_source(profile, &plan.source, vec![])
        .map_err(|error| error.to_string())?;
    for offset in 0..3u32 {
        assert_eq!(
            prepared.memory_word(plan.first_data_address + offset),
            Ok(plan.initial_words[usize::try_from(offset).map_err(|error| error.to_string())?]),
        );
    }
    for entry in [0, 1, 2, 3, 255, profile.eof_word(), 14_348_906] {
        let mut guest = ProfileMachine::from_state(
            profile,
            prepared.memory().to_vec(),
            vec![0xff, 0],
            ProfileRegisters {
                accumulator: entry,
                ..ProfileRegisters::default()
            },
        )
        .map_err(|error| error.to_string())?;
        let mut trace = Vec::new();
        let outcome = guest
            .run_traced(7, &mut |step| trace.push(*step))
            .map_err(|error| error.to_string())?;
        assert_eq!(outcome, RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 7,
        });
        assert_eq!(trace.len(), 7);
        assert_eq!(trace[0].decoded, Some(b'o'));
        assert_eq!(trace[1].decoded, Some(b'o'));
        assert_eq!(trace[2].decoded, Some(b'j'));
        assert_eq!(
            trace[2].after.registers.data_pointer,
            plan.first_data_address,
        );
        for (index, opcode) in b"*pp".iter().enumerate() {
            let step = &trace[index + 3];
            let address = plan.first_data_address
                + u32::try_from(index).map_err(|error| error.to_string())?;
            assert_eq!(step.decoded, Some(*opcode));
            assert_eq!(step.before.registers.data_pointer, address);
            assert_eq!(
                step.memory_reads
                    .data
                    .map(|read| (read.address, read.value)),
                Some((address, plan.initial_words[index])),
            );
            assert_eq!(
                step.after.registers.accumulator,
                plan.written_words[index],
            );
            // A real p write can leave its loader word numerically
            // unchanged; the VM records deltas, not write attempts.
            let expected_delta = (plan.initial_words[index]
                != plan.written_words[index])
                .then_some((address, plan.written_words[index]));
            assert_eq!(
                step.memory_delta
                    .data
                    .map(|write| (write.address, write.after)),
                expected_delta,
            );
            assert!(step.memory_delta.encryption.is_some());
            assert_eq!(
                guest.memory_word(address),
                Ok(plan.written_words[index])
            );
        }
        assert_eq!(trace[6].decoded, Some(b'v'));
        assert_eq!(trace[4].after.registers.accumulator, 0);
        assert_eq!(guest.input_consumed(), 0);
        assert_eq!(guest.output(), &[]);
    }
    Ok(())
}

#[test]
fn unknown_accumulator_zero_emitter_refuses_historical_profile() {
    assert_eq!(
        layout::build_accumulator_independent_zero_cell_source(
            historical_profile(),
        ),
        Err(layout::ZeroCellSourceError::UnsupportedProfile),
    );
}

#[test]
#[expect(
    clippy::indexing_slicing,
    clippy::panic_in_result_fn,
    clippy::cognitive_complexity,
    clippy::too_many_lines,
    reason = "real raw input effects followed by a loader-derived zero write"
)]
fn real_input_before_zero_preserves_physical_input_and_zero_effects()
-> Result<(), String> {
    let profile = current_profile();
    let plan = layout::build_input_then_zero_cell_source(profile)
        .map_err(|error| format!("{error:?}"))?;
    assert_eq!(plan.source, b"Dt&$:9K!6");
    assert_eq!(plan.input_code_address, Some(1));
    assert_eq!(plan.first_data_address, 39);
    assert_eq!(plan.written_words, [7_174_463, 0, 7_174_483]);
    let prepared = ProfileMachine::from_source(profile, &plan.source, vec![])
        .map_err(|error| error.to_string())?;
    for (bytes, accumulator) in [
        (vec![], 0),
        (vec![0], 1),
        (vec![2], 0),
        (vec![0x80], 255),
        (vec![0xff], profile.eof_word()),
        (vec![1, 2], 2),
    ] {
        let mut guest = ProfileMachine::from_state(
            profile,
            prepared.memory().to_vec(),
            bytes.clone(),
            ProfileRegisters {
                accumulator,
                ..ProfileRegisters::default()
            },
        )
        .map_err(|error| error.to_string())?;
        let mut trace = Vec::new();
        let outcome = guest
            .run_traced(7, &mut |step| trace.push(*step))
            .map_err(|error| error.to_string())?;
        assert_eq!(outcome, RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 7,
        });
        assert_eq!(trace.len(), 7);
        assert_eq!(trace[1].decoded, Some(b'/'));
        assert_eq!(
            trace[1].input,
            Some(bytes.first().map_or(TraceInput::EndOfInput, |byte| {
                TraceInput::Byte(*byte)
            })),
        );
        assert_eq!(
            trace[1].after.registers.accumulator,
            bytes.first().map_or_else(|| profile.eof_word(), |byte| u32::from(*byte)),
        );
        assert_eq!(trace[2].decoded, Some(b'j'));
        assert_eq!(trace[2].after.registers.data_pointer, 39);
        for (offset, opcode) in b"*pp".iter().enumerate() {
            let step = &trace[offset + 3];
            let address = plan.first_data_address
                + u32::try_from(offset).map_err(|error| error.to_string())?;
            assert_eq!(step.decoded, Some(*opcode));
            assert_eq!(
                step.memory_reads
                    .data
                    .map(|read| (read.address, read.value)),
                Some((address, plan.initial_words[offset])),
            );
            assert_eq!(step.after.registers.accumulator, plan.written_words[offset]);
            assert_eq!(guest.memory_word(address), Ok(plan.written_words[offset]));
            assert!(step.memory_delta.encryption.is_some());
        }
        assert_eq!(trace[6].decoded, Some(b'v'));
        assert_eq!(guest.input_consumed(), usize::from(!bytes.is_empty()));
        assert_eq!(guest.output(), &[]);
    }
    assert_eq!(
        layout::build_input_then_zero_cell_source(historical_profile()),
        Err(layout::ZeroCellSourceError::UnsupportedProfile),
    );
    Ok(())
}
