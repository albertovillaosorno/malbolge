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

use malbolge::{
    ProfileMachine, RunOutcome, Termination, TraceInput, current_profile,
    decode_profile_instruction, historical_profile,
};

const INPUT_CLASSES: u32 = 257;
const MAX_PREFIX: usize = 94;
const THREE_POW_FIVE: u32 = 243;
const SOURCE: &[u8] = b"DCBA@?>=<;:98765eu,>=<";

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
    for _ in 0..15 {
        result +=
            table[(data % 3) as usize][(accumulator % 3) as usize] * place;
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
    let mut seen = BTreeSet::new();
    for input in 0..=255u32 {
        if !seen.insert(independent_crazy(seed, input)) {
            return false;
        }
    }
    seen.insert(independent_crazy(seed, current_profile().eof_word()))
        && seen.len() == INPUT_CLASSES as usize
}

#[test]
#[expect(
    clippy::indexing_slicing,
    clippy::panic_in_result_fn,
    clippy::arithmetic_side_effects,
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
                    matching.push((source.clone(), data_address as u32, seed));
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
    reason = "actual N15 instruction, data and encryption trace assertions"
)]
fn real_guest_writes_injective_input_state() -> Result<(), String> {
    let profile = current_profile();
    let plan = layout::build_live_input_injective_store_source(profile)
        .map_err(|error| format!("{error:?}"))?;
    for input in [
        vec![],
        vec![0],
        vec![2],
        vec![127],
        vec![128],
        vec![255],
        vec![1, 2],
    ] {
        let mut guest =
            ProfileMachine::from_source(profile, &plan.source, input.clone())
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
            .map_or(profile.eof_word(), |byte| u32::from(*byte));
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
