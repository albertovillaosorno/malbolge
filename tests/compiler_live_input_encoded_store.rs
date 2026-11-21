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
//   - Independent loader census and real 257-class-injective N15 input store.
// - Must-Not:
//   - Substitute a raw encoded input word for the source-C32 frame result.
// - Allows:
//   - Inputs: at most 94 no-op prefixes, graphical tail pairs, binary/EOF.
//   - Outputs: exact p memory writes, input effects, bounded halt or refusal.
//   - Side effects: in-memory normative guest VM only.
// - Split-When:
//   - Signed normalization and source-linked mutable C are physically emitted.
// - Merge-When:
//   - General source-C signed input storage supersedes this single write.
// - Summary:
//   - A real guest word can distinguish all bytes plus EOF without host seeds.

//! The first guest `p` after `/` is a genuine full-byte-injective memory write.
//! Its stored value is deliberately *not* canonical signed C23 `getchar`.

#[path = "../src/compiler/malbolge-layout/composition/lib.rs"]
pub mod layout;

use std::collections::BTreeSet;
use std::iter::once;

use malbolge::{
    ProfileMachine, RunOutcome, Termination, TraceInput, current_profile,
    decode_profile_instruction, historical_profile,
};

const INPUT_CLASSES: usize = 257;
const MAX_PREFIX: usize = 94;
const THREE_POW_FIVE: u32 = 243;
const SOURCE: &[u8] = b"DCBA@?>=<;:98765eu,>=<";
const TWO_INPUT_SOURCE: &[u8] = b"DCBA@?>=<;:9876543210/.-,+*Zj!Wg|0\"y";

#[expect(
    clippy::arithmetic_side_effects,
    clippy::integer_division_remainder_used,
    clippy::indexing_slicing,
    reason = "standalone scalar ternary oracle, not production VM arithmetic"
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
        .ok_or_else(|| format!("missing graphical code for C{position}"))
}

#[expect(
    clippy::arithmetic_side_effects,
    clippy::indexing_slicing,
    clippy::integer_division_remainder_used,
    reason = "independent six-phase scalar loader recurrence"
)]
fn loader_word(source: &[u8], address: usize) -> u32 {
    let mut prev = u32::from(source[source.len() - 2]);
    let mut latest = u32::from(source[source.len() - 1]);
    for _ in 0..=((address - source.len()) % 6) {
        let next = independent_crazy(prev, latest);
        prev = latest;
        latest = next;
    }
    latest
}

fn strict_tail(byte: u8, position: usize) -> bool {
    decode_profile_instruction(
        u32::from(byte),
        u32::try_from(position).unwrap_or(u32::MAX),
    )
    .is_some_and(|opcode| b"ji*p</vo".contains(&opcode))
}

fn all_raw_input_words_are_distinct(seed: u32) -> bool {
    let mut results = BTreeSet::new();
    for input in 0..=255u32 {
        if !results.insert(independent_crazy(seed, input)) {
            return false;
        }
    }
    results.insert(independent_crazy(seed, current_profile().eof_word()))
        && results.len() == INPUT_CLASSES
}

#[test]
#[expect(
    clippy::cognitive_complexity,
    clippy::excessive_nesting,
    clippy::indexing_slicing,
    clippy::integer_division_remainder_used,
    clippy::panic_in_result_fn,
    reason = "independent full graphical search and 257-class oracle"
)]
fn source_search_matches_independent_loader_and_257_input_census()
-> Result<(), String> {
    let mut matching = Vec::<(Vec<u8>, u32, u32)>::new();
    let mut searched = 0usize;
    for prefix in 0..MAX_PREFIX {
        let mut source = (0..prefix)
            .map(|position| encode(b"o"[0], position))
            .collect::<Result<Vec<_>, _>>()?;
        for opcode in b"/jpv" {
            source.push(encode(*opcode, source.len())?);
        }
        let data_address = usize::from(source[prefix + 1]) + 1;
        if data_address <= source.len() + 2 {
            continue;
        }
        for first in 33..=126u8 {
            if !strict_tail(first, source.len()) {
                continue;
            }
            source.push(first);
            for last in 33..=126u8 {
                if !strict_tail(last, source.len()) {
                    continue;
                }
                source.push(last);
                searched += 1;
                let seed = loader_word(&source, data_address);
                if all_raw_input_words_are_distinct(seed) {
                    matching.push((
                        source.clone(),
                        u32::try_from(data_address)
                            .map_err(|error| error.to_string())?,
                        seed,
                    ));
                }
                _ = source.pop();
            }
            _ = source.pop();
        }
    }
    assert!(searched > 1_000);
    assert_eq!(matching.len(), 24);
    assert_eq!(matching[0], (SOURCE.to_vec(), 118, 7_174_453));
    let plan =
        layout::build_live_input_injective_store_source(current_profile())
            .map_err(|error| format!("{error:?}"))?;
    assert_eq!(plan.source, matching[0].0);
    assert_eq!(plan.input_code_address, 16);
    assert_eq!(plan.store_code_address, 18);
    assert_eq!(plan.data_address, matching[0].1);
    assert_eq!(plan.initial_data_word, matching[0].2);
    assert_eq!(plan.initial_data_word % THREE_POW_FIVE, 121);
    // No seed above is host-initialized: every candidate is derived from
    // its two actual graphical tail bytes through the loader recurrence.
    Ok(())
}

#[test]
#[expect(
    clippy::indexing_slicing,
    clippy::panic_in_result_fn,
    clippy::cognitive_complexity,
    clippy::too_many_lines,
    reason = "actual N15 instruction, data and encryption trace assertions"
)]
fn real_guest_writes_injective_input_state() -> Result<(), String> {
    let profile = current_profile();
    let plan = layout::build_live_input_injective_store_source(profile)
        .map_err(|error| format!("{error:?}"))?;
    // Build the full physical N15 loader memory once. Independent cases
    // resume from exact validated copies of this loader-produced image;
    // no guest word or register is synthesized or host-seeded.
    let prepared = ProfileMachine::from_source(profile, &plan.source, vec![])
        .map_err(|error| error.to_string())?;
    assert_eq!(
        prepared.memory_word(plan.data_address),
        Ok(plan.initial_data_word)
    );
    for input in [
        vec![],
        vec![0],
        vec![2],
        vec![127],
        vec![128],
        vec![255],
        vec![1, 2],
    ] {
        let mut guest = ProfileMachine::from_state(
            profile,
            prepared.memory().to_vec(),
            input.clone(),
            malbolge::ProfileRegisters::default(),
        )
        .map_err(|error| error.to_string())?;
        assert_eq!(
            guest.memory_word(plan.data_address),
            Ok(plan.initial_data_word)
        );
        let mut trace = Vec::new();
        let outcome = guest
            .run_traced(20, &mut |step| trace.push(*step))
            .map_err(|error| error.to_string())?;
        assert_eq!(outcome, RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 20,
        });
        assert_eq!(trace.len(), 20);
        for step in trace.iter().take(16) {
            assert_eq!(step.decoded, Some(b"o"[0]));
            assert!(step.memory_delta.encryption.is_some());
        }
        let raw = input
            .first()
            .map_or_else(|| profile.eof_word(), |byte| u32::from(*byte));
        let expected = independent_crazy(plan.initial_data_word, raw);
        assert_eq!(trace[16].decoded, Some(b"/"[0]));
        assert_eq!(
            trace[16].input,
            Some(input.first().map_or(TraceInput::EndOfInput, |byte| {
                TraceInput::Byte(*byte)
            }),)
        );
        assert_eq!(trace[16].after.registers.accumulator, raw);
        assert_eq!(trace[17].decoded, Some(b"j"[0]));
        assert_eq!(trace[17].after.registers.data_pointer, plan.data_address);
        assert_eq!(trace[18].decoded, Some(b"p"[0]));
        assert_eq!(trace[18].before.registers.data_pointer, plan.data_address);
        assert_eq!(
            trace[18]
                .memory_reads
                .data
                .map(|read| (read.address, read.value)),
            Some((plan.data_address, plan.initial_data_word)),
        );
        // The VM records deltas, not an attempted write that leaves an
        // already-equal word unchanged (raw input 0 is such a case).
        let expected_delta = (expected != plan.initial_data_word)
            .then_some((plan.data_address, expected));
        assert_eq!(
            trace[18]
                .memory_delta
                .data
                .map(|delta| (delta.address, delta.after)),
            expected_delta,
        );
        assert!(trace[18].memory_delta.encryption.is_some());
        assert_eq!(trace[18].after.registers.accumulator, expected);
        assert_eq!(guest.memory_word(plan.data_address), Ok(expected));
        assert_eq!(trace[19].decoded, Some(b"v"[0]));
        assert_eq!(guest.input_consumed(), usize::from(!input.is_empty()));
        assert_eq!(guest.output(), &[]);
    }
    Ok(())
}

#[test]
fn historical_profile_cannot_emit_the_n15_input_store() {
    assert_eq!(
        layout::build_live_input_injective_store_source(historical_profile()),
        Err(layout::LiveInputEncodedStoreError::UnsupportedProfile),
    );
}

#[test]
#[expect(
    clippy::cognitive_complexity,
    clippy::excessive_nesting,
    clippy::indexing_slicing,
    clippy::panic_in_result_fn,
    clippy::too_many_lines,
    reason = "independent exhaustive loader and two-input seed oracle"
)]
fn two_input_search_matches_independent_94_phase_loader_census()
-> Result<(), String> {
    let mut matching = Vec::<(Vec<u8>, u32, u32, u32, u32)>::new();
    let mut searched = 0usize;
    for prefix in 0..MAX_PREFIX {
        let mut source = (0..prefix)
            .map(|position| encode(b'o', position))
            .collect::<Result<Vec<_>, _>>()?;
        for opcode in b"/jp/jpv" {
            source.push(encode(*opcode, source.len())?);
        }
        let first_address = usize::from(source[prefix + 1]) + 1;
        if first_address <= source.len() + 2 {
            continue;
        }
        for first in 33..=126u8 {
            if !strict_tail(first, source.len()) {
                continue;
            }
            source.push(first);
            for last in 33..=126u8 {
                if !strict_tail(last, source.len()) {
                    continue;
                }
                source.push(last);
                searched += 1;
                let first_seed = loader_word(&source, first_address);
                if all_raw_input_words_are_distinct(first_seed) {
                    let second_jump = loader_word(&source, first_address + 2);
                    let second_address = usize::try_from(second_jump)
                        .map_err(|error| error.to_string())?
                        + 1;
                    if second_address > source.len() + 2
                        && second_address < 14_348_907
                        && second_address != first_address
                    {
                        let second_seed = loader_word(&source, second_address);
                        if all_raw_input_words_are_distinct(second_seed) {
                            matching.push((
                                source.clone(),
                                u32::try_from(first_address)
                                    .map_err(|error| error.to_string())?,
                                first_seed,
                                u32::try_from(second_address)
                                    .map_err(|error| error.to_string())?,
                                second_seed,
                            ));
                        }
                    }
                }
                _ = source.pop();
            }
            _ = source.pop();
        }
    }
    assert_eq!(searched, 4_032);
    assert_eq!(matching.len(), 7);
    assert_eq!(matching[0], (TWO_INPUT_SOURCE.to_vec(), 107, 121, 125, 121));
    let plan =
        layout::build_live_two_input_injective_store_source(current_profile())
            .map_err(|error| format!("{error:?}"))?;
    assert_eq!(
        (
            plan.source,
            plan.first_data_address,
            plan.first_initial_data_word,
            plan.second_data_address,
            plan.second_initial_data_word,
        ),
        matching[0],
    );
    assert_eq!(
        (
            plan.first_input_code_address,
            plan.first_store_code_address,
            plan.second_input_code_address,
            plan.second_store_code_address,
        ),
        (27, 29, 30, 32),
    );
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "independent 257 squared injectivity of two disjoint input cells"
)]
fn two_retained_input_words_are_pairwise_distinct_for_all_byte_eof_pairs()
-> Result<(), String> {
    let plan =
        layout::build_live_two_input_injective_store_source(current_profile())
            .map_err(|error| format!("{error:?}"))?;
    assert_ne!(plan.first_data_address, plan.second_data_address);
    let raw = (0..=255u32)
        .chain(once(current_profile().eof_word()))
        .collect::<Vec<_>>();
    let first = raw
        .iter()
        .copied()
        .map(|input| independent_crazy(plan.first_initial_data_word, input))
        .collect::<BTreeSet<_>>();
    let second = raw
        .iter()
        .copied()
        .map(|input| independent_crazy(plan.second_initial_data_word, input))
        .collect::<BTreeSet<_>>();
    assert_eq!(first.len(), INPUT_CLASSES);
    assert_eq!(second.len(), INPUT_CLASSES);
    let combined = first
        .iter()
        .flat_map(|first_word| {
            second
                .iter()
                .map(move |second_word| (*first_word, *second_word))
        })
        .collect::<BTreeSet<_>>();
    assert_eq!(combined.len(), INPUT_CLASSES * INPUT_CLASSES);
    Ok(())
}

#[test]
#[expect(
    clippy::cognitive_complexity,
    clippy::indexing_slicing,
    clippy::panic_in_result_fn,
    clippy::too_many_lines,
    reason = "full normative N15 double read and disjoint data-write trace"
)]
fn real_guest_preserves_first_encoded_input_across_second_read_and_store()
-> Result<(), String> {
    let profile = current_profile();
    let plan = layout::build_live_two_input_injective_store_source(profile)
        .map_err(|error| format!("{error:?}"))?;
    let prepared = ProfileMachine::from_source(profile, &plan.source, vec![])
        .map_err(|error| error.to_string())?;
    let second_jump_address = plan.first_data_address + 2;
    let second_jump_word = prepared
        .memory_word(second_jump_address)
        .map_err(|error| error.to_string())?;
    assert_eq!(second_jump_word + 1, plan.second_data_address);
    assert_eq!(prepared.memory_word(plan.first_data_address), Ok(121));
    assert_eq!(prepared.memory_word(plan.second_data_address), Ok(121));
    for input in [
        vec![],
        vec![0],
        vec![255],
        vec![0, 0],
        vec![2, 255],
        vec![255, 2],
        vec![128, 127],
        vec![0, 255, 1],
    ] {
        let mut guest = ProfileMachine::from_state(
            profile,
            prepared.memory().to_vec(),
            input.clone(),
            malbolge::ProfileRegisters::default(),
        )
        .map_err(|error| error.to_string())?;
        let mut trace = Vec::new();
        let outcome = guest
            .run_traced(34, &mut |step| trace.push(*step))
            .map_err(|error| error.to_string())?;
        assert_eq!(outcome, RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 34,
        });
        assert_eq!(trace.len(), 34);
        for step in trace.iter().take(27) {
            assert_eq!(step.decoded, Some(b'o'));
            assert!(step.memory_delta.encryption.is_some());
        }
        let first_raw = input
            .first()
            .map_or_else(|| profile.eof_word(), |byte| u32::from(*byte));
        let second_raw = input
            .get(1)
            .map_or_else(|| profile.eof_word(), |byte| u32::from(*byte));
        let first_stored = independent_crazy(121, first_raw);
        let second_stored = independent_crazy(121, second_raw);
        assert_eq!(trace[27].decoded, Some(b'/'));
        assert_eq!(
            trace[27].input,
            Some(input.first().map_or(TraceInput::EndOfInput, |byte| {
                TraceInput::Byte(*byte)
            },))
        );
        assert_eq!(trace[28].decoded, Some(b'j'));
        assert_eq!(
            trace[28].after.registers.data_pointer,
            plan.first_data_address,
        );
        assert_eq!(trace[29].decoded, Some(b'p'));
        assert_eq!(
            trace[29]
                .memory_reads
                .data
                .map(|read| (read.address, read.value)),
            Some((plan.first_data_address, 121)),
        );
        assert_eq!(trace[29].after.registers.accumulator, first_stored);
        assert_eq!(
            trace[29]
                .memory_delta
                .data
                .map(|delta| (delta.address, delta.after)),
            Some((plan.first_data_address, first_stored)),
        );
        assert_eq!(trace[30].decoded, Some(b'/'));
        assert_eq!(
            trace[30].input,
            Some(input.get(1).map_or(TraceInput::EndOfInput, |byte| {
                TraceInput::Byte(*byte)
            },))
        );
        assert_eq!(trace[31].decoded, Some(b'j'));
        assert_eq!(
            trace[31]
                .memory_reads
                .data
                .map(|read| (read.address, read.value)),
            Some((second_jump_address, second_jump_word)),
        );
        assert_eq!(
            trace[31].after.registers.data_pointer,
            plan.second_data_address,
        );
        assert_eq!(trace[32].decoded, Some(b'p'));
        assert_eq!(
            trace[32]
                .memory_reads
                .data
                .map(|read| (read.address, read.value)),
            Some((plan.second_data_address, 121)),
        );
        assert_eq!(trace[32].after.registers.accumulator, second_stored);
        assert_eq!(
            trace[32]
                .memory_delta
                .data
                .map(|delta| (delta.address, delta.after)),
            Some((plan.second_data_address, second_stored)),
        );
        assert_eq!(trace[33].decoded, Some(b'v'));
        assert_eq!(
            guest.memory_word(plan.first_data_address),
            Ok(first_stored)
        );
        assert_eq!(
            guest.memory_word(plan.second_data_address),
            Ok(second_stored)
        );
        assert_eq!(guest.input_consumed(), input.len().min(2));
        assert_eq!(guest.output(), &[]);
        for step in trace.iter().skip(27).take(6) {
            assert!(step.memory_delta.encryption.is_some());
        }
    }
    Ok(())
}

#[test]
fn historical_profile_cannot_emit_two_live_input_stores() {
    assert_eq!(
        layout::build_live_two_input_injective_store_source(
            historical_profile()
        ),
        Err(layout::LiveInputEncodedStoreError::UnsupportedProfile),
    );
}

#[expect(
    clippy::arithmetic_side_effects,
    clippy::integer_division,
    clippy::integer_division_remainder_used,
    reason = "independent scalar N15 rotate oracle"
)]
fn independent_rotate(word: u32) -> u32 {
    word / 3 + (word % 3) * (3u32.pow(15) / 3)
}

#[test]
#[expect(
    clippy::cognitive_complexity,
    clippy::panic_in_result_fn,
    clippy::indexing_slicing,
    reason = "exact independent complete 257-class source proof"
)]
fn input_then_zero_source_is_loader_derived_and_retains_all_257_inputs()
-> Result<(), String> {
    let plan = layout::build_live_input_then_zero_source(current_profile())
        .map_err(|error| format!("{error:?}"))?;
    assert_eq!(
        plan.source,
        b"DCBA@?>=<;:9876543210/.-,+*)('&%$#\"!~}|{zyxwIYnWUkji{Py",
    );
    assert_eq!(plan.input_code_address, 44);
    assert_eq!(plan.input_data_address, 90);
    assert_eq!(plan.input_seed, 121);
    assert_eq!(plan.zero_chain_address, 7_174_413);
    assert_eq!(plan.zero_data_address, 7_174_416);
    assert_eq!(plan.zero_chain_seeds, [7_174_372, 161, 7_174_412, 121]);
    assert_eq!(loader_word(&plan.source, 90), plan.input_seed);
    assert_eq!(loader_word(&plan.source, 91) + 1, plan.zero_chain_address);
    for offset in 0..4usize {
        assert_eq!(
            loader_word(
                &plan.source,
                usize::try_from(plan.zero_chain_address)
                    .map_err(|error| error.to_string())?
                    + offset,
            ),
            plan.zero_chain_seeds[offset],
        );
    }
    let mut state = independent_rotate(plan.zero_chain_seeds[0]);
    assert_eq!(state, 7_174_426);
    for (seed, result) in
        plan.zero_chain_seeds[1..].iter().zip([80, 7_174_453, 0])
    {
        state = independent_crazy(*seed, state);
        assert_eq!(state, result);
    }
    let mut distinct = BTreeSet::new();
    for raw in (0..=255u32).chain(once(current_profile().eof_word())) {
        assert!(distinct.insert(independent_crazy(plan.input_seed, raw)));
    }
    assert_eq!(distinct.len(), 257);
    assert_eq!(
        layout::build_live_input_then_zero_source(historical_profile()),
        Err(layout::LiveInputEncodedStoreError::UnsupportedProfile),
    );
    Ok(())
}

#[test]
#[expect(
    clippy::indexing_slicing,
    clippy::cognitive_complexity,
    clippy::too_many_lines,
    clippy::panic_in_result_fn,
    reason = "seven genuine input and multi-region zero-write N15 traces"
)]
fn real_guest_retains_input_word_before_independent_zero_write()
-> Result<(), String> {
    let profile = current_profile();
    let plan = layout::build_live_input_then_zero_source(profile)
        .map_err(|error| format!("{error:?}"))?;
    let prepared = ProfileMachine::from_source(profile, &plan.source, vec![])
        .map_err(|error| error.to_string())?;
    for (input, entry) in [
        (vec![], 0),
        (vec![0], 1),
        (vec![2], 255),
        (vec![0x80], 3),
        (vec![0xff], profile.eof_word()),
        (vec![1, 2], 10),
        (vec![0, 0xff], 2),
    ] {
        let mut machine = ProfileMachine::from_state(
            profile,
            prepared.memory().to_vec(),
            input.clone(),
            malbolge::ProfileRegisters {
                accumulator: entry,
                ..malbolge::ProfileRegisters::default()
            },
        )
        .map_err(|error| error.to_string())?;
        let mut trace = Vec::new();
        let outcome = machine
            .run_traced(53, &mut |step| trace.push(*step))
            .map_err(|error| error.to_string())?;
        assert_eq!(outcome, RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 53,
        });
        assert_eq!(trace.len(), 53);
        assert_eq!(trace[44].decoded, Some(b'/'));
        assert_eq!(
            trace[44].input,
            Some(input.first().map_or(TraceInput::EndOfInput, |byte| {
                TraceInput::Byte(*byte)
            })),
        );
        let raw = input
            .first()
            .map_or_else(|| profile.eof_word(), |byte| u32::from(*byte));
        assert_eq!(trace[44].after.registers.accumulator, raw);
        assert_eq!(trace[45].decoded, Some(b'j'));
        assert_eq!(trace[45].after.registers.data_pointer, 90);
        assert_eq!(trace[46].decoded, Some(b'p'));
        let stored = independent_crazy(plan.input_seed, raw);
        assert_eq!(
            trace[46]
                .memory_reads
                .data
                .map(|read| (read.address, read.value)),
            Some((90, plan.input_seed)),
        );
        assert_eq!(trace[46].after.registers.accumulator, stored);
        assert_eq!(trace[47].decoded, Some(b'j'));
        assert_eq!(
            trace[47].memory_reads.data.map(|read| read.value),
            Some(7_174_412)
        );
        assert_eq!(
            trace[47].after.registers.data_pointer,
            plan.zero_chain_address
        );
        let mut expected = independent_rotate(plan.zero_chain_seeds[0]);
        for (offset, opcode) in b"*ppp".iter().enumerate() {
            let step = &trace[48 + offset];
            let addr = plan.zero_chain_address
                + u32::try_from(offset).map_err(|error| error.to_string())?;
            if offset != 0 {
                expected =
                    independent_crazy(plan.zero_chain_seeds[offset], expected);
            }
            assert_eq!(step.decoded, Some(*opcode));
            assert_eq!(step.before.registers.data_pointer, addr);
            assert_eq!(
                step.memory_reads
                    .data
                    .map(|read| (read.address, read.value)),
                Some((addr, plan.zero_chain_seeds[offset])),
            );
            assert_eq!(step.after.registers.accumulator, expected);
            assert_eq!(machine.memory_word(addr), Ok(expected));
            assert!(step.memory_delta.encryption.is_some());
        }
        assert_eq!(expected, 0);
        assert_eq!(machine.memory_word(90), Ok(stored));
        assert_eq!(machine.memory_word(plan.zero_data_address), Ok(0));
        assert_eq!(trace[52].decoded, Some(b'v'));
        assert_eq!(machine.input_consumed(), usize::from(!input.is_empty()));
        assert_eq!(machine.output(), &[]);
    }
    Ok(())
}

#[test]
#[expect(
    clippy::cognitive_complexity,
    clippy::excessive_nesting,
    clippy::too_many_lines,
    clippy::indexing_slicing,
    clippy::panic_in_result_fn,
    reason = "independent exhaustive guest input reentry loader census"
)]
fn input_reentry_source_matches_independent_bounded_search()
-> Result<(), String> {
    let mut matches = Vec::new();
    let mut backtracks = 0usize;
    for padding in 0..=14usize {
        for prefix in 0..MAX_PREFIX {
            let mut source = (0..prefix)
                .map(|i| encode(b'o', i))
                .collect::<Result<Vec<_>, _>>()?;
            for opcode in b"/jp" {
                source.push(encode(*opcode, source.len())?);
            }
            for _ in 0..padding {
                source.push(encode(b'o', source.len())?);
            }
            for opcode in b"jjv" {
                source.push(encode(*opcode, source.len())?);
            }
            let data_address = usize::from(source[prefix + 1]) + 1;
            let return_address = data_address + 1 + padding;
            if data_address <= source.len() + 2
                || return_address <= source.len() + 2
            {
                continue;
            }
            for first in 33..=126u8 {
                if !strict_tail(first, source.len()) {
                    continue;
                }
                source.push(first);
                for last in 33..=126u8 {
                    if !strict_tail(last, source.len()) {
                        continue;
                    }
                    source.push(last);
                    if loader_word(&source, return_address)
                        == u32::try_from(data_address - 1)
                            .map_err(|error| error.to_string())?
                    {
                        backtracks += 1;
                        let seed = loader_word(&source, data_address);
                        if all_raw_input_words_are_distinct(seed) {
                            matches.push((
                                source.clone(),
                                padding,
                                data_address,
                                return_address,
                                seed,
                            ));
                        }
                    }
                    _ = source.pop();
                }
                _ = source.pop();
            }
        }
    }
    assert_eq!(backtracks, 127);
    assert_eq!(matches.len(), 2);
    let plan = layout::build_live_input_reentry_source(current_profile())
        .map_err(|error| format!("{error:?}"))?;
    assert_eq!(
        (
            plan.source.as_slice(),
            plan.return_padding,
            plan.store_data_address,
            plan.return_data_address,
            plan.store_initial_word,
        ),
        (
            matches[0].0.as_slice(),
            matches[0].1,
            u32::try_from(matches[0].2).map_err(|error| error.to_string())?,
            u32::try_from(matches[0].3).map_err(|error| error.to_string())?,
            matches[0].4,
        )
    );
    assert_eq!(plan.source, b"u'<A@?>=<;:987654ut>NN");
    assert_eq!(
        (
            plan.input_code_address,
            plan.store_code_address,
            plan.return_code_address,
            plan.input_reentry_code_address,
            plan.store_data_address,
            plan.return_data_address,
            plan.return_initial_word,
            plan.return_padding,
        ),
        (0, 2, 17, 18, 40, 55, 39, 14),
    );
    assert_eq!(
        layout::build_live_input_reentry_source(historical_profile()),
        Err(layout::LiveInputEncodedStoreError::UnsupportedProfile),
    );
    Ok(())
}

#[test]
#[expect(
    clippy::cognitive_complexity,
    clippy::indexing_slicing,
    clippy::integer_division_remainder_used,
    clippy::panic_in_result_fn,
    clippy::too_many_lines,
    reason = "complete guest data-dependent jump and independent N15 oracle"
)]
fn real_guest_rereads_physically_stored_input_as_data_pointer()
-> Result<(), String> {
    let profile = current_profile();
    let plan = layout::build_live_input_reentry_source(profile)
        .map_err(|error| format!("{error:?}"))?;
    let prepared = ProfileMachine::from_source(profile, &plan.source, vec![])
        .map_err(|error| error.to_string())?;
    assert_eq!(
        prepared.memory_word(plan.store_data_address),
        Ok(plan.store_initial_word),
    );
    assert_eq!(
        prepared.memory_word(plan.return_data_address),
        Ok(plan.return_initial_word),
    );
    let mut pointer_classes = BTreeSet::new();
    for raw in (0..=255u32).chain(once(profile.eof_word())) {
        let written = independent_crazy(plan.store_initial_word, raw);
        let destination = (written + 1) % profile.memory_words();
        assert!(pointer_classes.insert(destination));
    }
    assert_eq!(pointer_classes.len(), 257);

    for input in [
        vec![],
        vec![0],
        vec![2],
        vec![0x7f],
        vec![0x80],
        vec![0xff],
        vec![0x01, 0xff],
    ] {
        let mut guest = ProfileMachine::from_state(
            profile,
            prepared.memory().to_vec(),
            input.clone(),
            malbolge::ProfileRegisters::default(),
        )
        .map_err(|error| error.to_string())?;
        let mut trace = Vec::new();
        let outcome = guest
            .run_traced(20, &mut |step| trace.push(*step))
            .map_err(|error| error.to_string())?;
        assert_eq!(outcome, RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 20,
        });
        assert_eq!(trace.len(), 20);
        let raw = input
            .first()
            .map_or_else(|| profile.eof_word(), |byte| u32::from(*byte));
        let written = independent_crazy(plan.store_initial_word, raw);
        assert_eq!(trace[0].decoded, Some(b'/'));
        assert_eq!(
            trace[0].input,
            Some(input.first().map_or(TraceInput::EndOfInput, |byte| {
                TraceInput::Byte(*byte)
            })),
        );
        assert_eq!(trace[1].decoded, Some(b'j'));
        assert_eq!(
            trace[1].after.registers.data_pointer,
            plan.store_data_address
        );
        assert_eq!(trace[2].decoded, Some(b'p'));
        assert_eq!(
            trace[2]
                .memory_reads
                .data
                .map(|read| (read.address, read.value)),
            Some((plan.store_data_address, plan.store_initial_word)),
        );
        assert_eq!(trace[2].after.registers.accumulator, written);
        for step in trace.iter().skip(3).take(14) {
            assert_eq!(step.decoded, Some(b'o'));
        }
        assert_eq!(trace[17].decoded, Some(b'j'));
        assert_eq!(
            trace[17]
                .memory_reads
                .data
                .map(|read| (read.address, read.value)),
            Some((plan.return_data_address, plan.return_initial_word)),
        );
        assert_eq!(
            trace[17].after.registers.data_pointer,
            plan.store_data_address
        );
        assert_eq!(trace[18].decoded, Some(b'j'));
        assert_eq!(
            trace[18]
                .memory_reads
                .data
                .map(|read| (read.address, read.value)),
            Some((plan.store_data_address, written)),
        );
        assert_eq!(
            trace[18].after.registers.data_pointer,
            (written + 1) % profile.memory_words(),
        );
        assert_eq!(trace[19].decoded, Some(b'v'));
        assert_eq!(guest.memory_word(plan.store_data_address), Ok(written));
        assert_eq!(guest.input_consumed(), usize::from(!input.is_empty()));
        assert!(guest.output().is_empty());
        for step in trace.iter().take(19) {
            assert!(step.memory_delta.encryption.is_some());
        }
    }
    Ok(())
}

#[test]
#[expect(
    clippy::cognitive_complexity,
    clippy::indexing_slicing,
    clippy::integer_division_remainder_used,
    clippy::panic_in_result_fn,
    clippy::too_many_lines,
    reason = "real physical input-dependent arithmetic and guest effects"
)]
fn real_guest_input_reentry_drives_followup_crazy_data_operation()
-> Result<(), String> {
    let profile = current_profile();
    let source = b"u'<A@?>=<;:{z1C/.-,+NN";
    let prepared = ProfileMachine::from_source(profile, source, vec![])
        .map_err(|error| error.to_string())?;
    for input in [
        vec![],
        vec![0],
        vec![2],
        vec![0x7f],
        vec![0x80],
        vec![0xff],
        vec![1, 2],
    ] {
        let mut guest = ProfileMachine::from_state(
            profile,
            prepared.memory().to_vec(),
            input.clone(),
            malbolge::ProfileRegisters::default(),
        )
        .map_err(|error| error.to_string())?;
        let mut trace = Vec::new();
        let outcome = guest
            .run_traced(15, &mut |step| trace.push(*step))
            .map_err(|error| error.to_string())?;
        assert_eq!(outcome, RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 15,
        });
        let raw = input
            .first()
            .map_or_else(|| profile.eof_word(), |byte| u32::from(*byte));
        let written = independent_crazy(7_174_453, raw);
        assert_eq!(trace[0].decoded, Some(b'/'));
        assert_eq!(trace[1].decoded, Some(b'j'));
        assert_eq!(trace[2].decoded, Some(b'p'));
        assert_eq!(
            trace[2]
                .memory_reads
                .data
                .map(|read| (read.address, read.value)),
            Some((40, 7_174_453))
        );
        assert_eq!(trace[2].after.registers.accumulator, written);
        assert_eq!(trace[11].decoded, Some(b'j'));
        assert_eq!(
            trace[11]
                .memory_reads
                .data
                .map(|read| (read.address, read.value)),
            Some((49, 39))
        );
        assert_eq!(trace[11].after.registers.data_pointer, 40);
        assert_eq!(trace[12].decoded, Some(b'j'));
        assert_eq!(
            trace[12]
                .memory_reads
                .data
                .map(|read| (read.address, read.value)),
            Some((40, written))
        );
        let dest = (written + 1) % profile.memory_words();
        assert_eq!(trace[12].after.registers.data_pointer, dest);
        assert_eq!(trace[13].decoded, Some(b'p'));
        let prior = trace[13]
            .memory_reads
            .data
            .ok_or("missing physical post-reentry operand")?;
        assert_eq!(prior.address, dest);
        let expected = independent_crazy(prior.value, written);
        assert_eq!(trace[13].after.registers.accumulator, expected);
        assert_eq!(guest.memory_word(dest), Ok(expected));
        assert_eq!(trace[14].decoded, Some(b'v'));
        for step in trace.iter().take(14) {
            assert!(step.memory_delta.encryption.is_some());
        }
        assert_eq!(guest.input_consumed(), usize::from(!input.is_empty()));
        assert_eq!(guest.output(), &[]);
    }
    Ok(())
}
