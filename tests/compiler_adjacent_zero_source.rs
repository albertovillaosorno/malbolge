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
//   - Independent loader census and real N15 adjacent two-word zero writes.
// - Must-Not:
//   - Claim this initial-state source is a mutable C32 allocator or loop.
// - Allows:
//   - Inputs: canonical 15-trit profile and finite graphical source grammar.
//   - Outputs: verified zero pair after physical data reentry and two stores.
//   - Side effects: isolated guest VM, no compiler publication.
// - Split-When:
//   - Reusable source-linked two-word C32 initialization is available.
// - Merge-When:
//   - The real C23 mutable local linker owns its physical initialization.
// - Summary:
//   - Three source-loaded data jumps allow two adjacent actual zero writes.

//! Reproduce adjacent C32 zero data writes with independent ternary arithmetic.

#[path = "../src/compiler/malbolge-layout/composition/lib.rs"]
pub mod layout;

use std::collections::{BTreeSet, HashSet};
use std::fmt::Write as _;

use malbolge::{
    ProfileMachine, ProfileRegisters, RunOutcome, Termination, current_profile,
    decode_profile_instruction, historical_profile,
};

const CODE_CELLS: usize = 60;
const SOURCE_CELLS: usize = 62;
// This is a source-loaded physical raw-input pair, not signed C23 EOF storage.
// It must represent each *successful* getchar byte as [byte, 0] without host
// I/O substitution; EOF must remain distinguishable but is not normalized.
const RAW_PAIR_HEX: &str = concat!(
    "283d3c253a3938217d6c347b3244363534333231302f2e2d2c2b2a292827",
    "262524",
);

const SOURCE_HEX: &str = concat!(
    "44434241403f3e3d3c7d34337a31302f762d3f31302f2e2d2c2b2a292827",
    "2625242322217e7d7c7b7a797877767574737271706f6e6d6c6b6a6968672725",
);

#[expect(
    clippy::arithmetic_side_effects,
    clippy::integer_division_remainder_used,
    clippy::indexing_slicing,
    reason = "independent 15-trit scalar truth table"
)]
fn crazy(mut data: u32, mut accumulator: u32) -> u32 {
    let truth = [[1, 0, 0], [1, 0, 2], [2, 2, 1]];
    let mut result = 0;
    let mut place = 1;
    for _ in 0usize..15 {
        result += truth[usize::try_from(data % 3).unwrap_or(3)]
            [usize::try_from(accumulator % 3).unwrap_or(3)]
            * place;
        data /= 3;
        accumulator /= 3;
        place *= 3;
    }
    result
}

fn encode(opcode: u8, position: usize) -> Result<u8, String> {
    (33..=126u8)
        .find(|byte| {
            decode_profile_instruction(
                u32::from(*byte),
                u32::try_from(position).unwrap_or(u32::MAX),
            ) == Some(opcode)
        })
        .ok_or_else(|| format!("missing source opcode at C{position}"))
}

fn graphical_tail(byte: u8, position: usize) -> bool {
    decode_profile_instruction(
        u32::from(byte),
        u32::try_from(position).unwrap_or(u32::MAX),
    )
    .is_some_and(|opcode| b"ji*p</vo".contains(&opcode))
}

#[expect(
    clippy::arithmetic_side_effects,
    clippy::indexing_slicing,
    clippy::integer_division_remainder_used,
    reason = "independent six-cycle original source loader recurrence"
)]
fn loader_word(source: &[u8], address: usize) -> u32 {
    let mut older = u32::from(source[source.len() - 2]);
    let mut newer = u32::from(source[source.len() - 1]);
    for _ in 0..=((address - source.len()) % 6) {
        let next = crazy(older, newer);
        older = newer;
        newer = next;
    }
    newer
}

#[test]
#[expect(
    clippy::cognitive_complexity,
    clippy::excessive_nesting,
    clippy::indexing_slicing,
    clippy::panic_in_result_fn,
    clippy::too_many_lines,
    reason = "independent 2752-case physical graphical loader census"
)]
fn adjacent_zero_matches_independent_full_source_census() -> Result<(), String>
{
    let mut eligible = 0usize;
    let mut matches = 0usize;
    let mut first = None;
    for prefix in 0..=50usize {
        let mut source = (0..prefix)
            .map(|position| encode(111, position))
            .chain(
                b"jppjpppjpv"
                    .iter()
                    .enumerate()
                    .map(|(index, opcode)| encode(*opcode, prefix + index)),
            )
            .chain(
                ((prefix + 10)..CODE_CELLS)
                    .map(|position| encode(111, position)),
            )
            .collect::<Result<Vec<_>, _>>()?;
        assert_eq!(source.len(), CODE_CELLS);
        let scratch = usize::from(source[prefix]) + 1;
        if scratch <= SOURCE_CELLS + 2 {
            continue;
        }
        for head in 33..=126u8 {
            if !graphical_tail(head, CODE_CELLS) {
                continue;
            }
            source.push(head);
            for tail in 33..=126u8 {
                if !graphical_tail(tail, CODE_CELLS + 1) {
                    continue;
                }
                source.push(tail);
                eligible += 1;
                let first_written = crazy(loader_word(&source, scratch), 0);
                let scratch_zero =
                    crazy(loader_word(&source, scratch + 1), first_written);
                let jump = usize::try_from(loader_word(&source, scratch + 2))
                    .map_err(|error| error.to_string())?
                    + 1;
                if scratch_zero == 0
                    && jump > SOURCE_CELLS
                    && jump + 3 < 14_348_907
                    && !(scratch..=scratch + 2).contains(&jump)
                    && !(jump..=jump + 3).contains(&scratch)
                {
                    let first_relocated =
                        crazy(loader_word(&source, jump), scratch_zero);
                    let high_zero =
                        crazy(loader_word(&source, jump + 1), first_relocated);
                    let third_relocated =
                        crazy(loader_word(&source, jump + 2), high_zero);
                    let low_zero = crazy(first_relocated, third_relocated);
                    if high_zero == 0
                        && low_zero == 0
                        && loader_word(&source, jump + 3) + 1
                            == u32::try_from(jump)
                                .map_err(|error| error.to_string())?
                        && loader_word(&source, jump) != 0
                        && loader_word(&source, jump + 1) != 0
                    {
                        matches += 1;
                        if first.is_none() {
                            first =
                                Some((source.clone(), prefix, scratch, jump));
                        }
                    }
                }
                _ = source.pop();
            }
            _ = source.pop();
        }
    }
    assert_eq!(eligible, 2752);
    assert_eq!(matches, 21);
    let plan = layout::build_adjacent_c32_zero_source(current_profile())
        .map_err(|error| format!("{error:?}"))?;
    let expected = first.ok_or("no independently loadable adjacent zero")?;
    assert_eq!(
        (
            plan.source.clone(),
            usize::try_from(plan.zero_low_code_address)
                .map_err(|error| error.to_string())?
                - 8,
            usize::try_from(plan.scratch_data_address)
                .map_err(|error| error.to_string())?,
            usize::try_from(plan.zero_low_address)
                .map_err(|error| error.to_string())?,
        ),
        expected,
    );
    assert_eq!(expected.1, 9);
    assert_eq!(expected.2, 126);
    assert_eq!(expected.3, 7_174_417);
    let mut hex = String::new();
    for byte in &plan.source {
        write!(&mut hex, "{byte:02x}").map_err(|error| error.to_string())?;
    }
    assert_eq!(hex, SOURCE_HEX);
    assert_eq!(plan.scratch_initial_words, [7_174_416, 37, 7_174_416]);
    assert_eq!(plan.relocated_initial_words, [37, 7_174_416, 37, 7_174_416]);
    assert_eq!(plan.input_code_address, None);
    assert_eq!(plan.zero_high_address, 7_174_418);
    assert_eq!(plan.zero_high_code_address, 14);
    assert_eq!(plan.zero_low_code_address, 17);
    Ok(())
}

#[test]
#[expect(
    clippy::cognitive_complexity,
    clippy::indexing_slicing,
    clippy::panic_in_result_fn,
    clippy::too_many_lines,
    reason = "real N15 source writes, encryption and physical reentry"
)]
fn real_guest_reenters_to_write_two_adjacent_zero_words() -> Result<(), String>
{
    let profile = current_profile();
    let plan = layout::build_adjacent_c32_zero_source(profile)
        .map_err(|error| format!("{error:?}"))?;
    let prepared = ProfileMachine::from_source(profile, &plan.source, vec![])
        .map_err(|error| error.to_string())?;
    assert_eq!(prepared.memory_word(plan.zero_low_address), Ok(37));
    assert_eq!(prepared.memory_word(plan.zero_high_address), Ok(7_174_416));
    for input in [vec![], vec![0], vec![0xff], vec![0x02, 0xff], vec![0x80, 0]]
    {
        let mut guest = ProfileMachine::from_state(
            profile,
            prepared.memory().to_vec(),
            input,
            ProfileRegisters::default(),
        )
        .map_err(|error| error.to_string())?;
        let mut trace = Vec::new();
        let outcome = guest
            .run_traced(19, &mut |step| trace.push(*step))
            .map_err(|error| error.to_string())?;
        assert_eq!(outcome, RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 19,
        });
        assert_eq!(trace.len(), 19);
        for step in trace.iter().take(9) {
            assert_eq!(step.decoded, Some(111));
            assert!(step.memory_delta.encryption.is_some());
        }
        for (code, read_address, read_value, new_data_pointer) in [
            (9usize, 9u32, 125u32, 126u32),
            (12, 128, 7_174_416, 7_174_417),
            (16, 7_174_420, 7_174_416, 7_174_417),
        ] {
            let step = &trace[code];
            assert_eq!(step.decoded, Some(106));
            assert_eq!(
                step.memory_reads
                    .data
                    .map(|read| (read.address, read.value)),
                Some((read_address, read_value)),
            );
            assert_eq!(step.after.registers.data_pointer, new_data_pointer);
            assert!(step.memory_delta.encryption.is_some());
        }
        for (code, data_address, before, after) in [
            (10usize, 126u32, 7_174_416u32, 7_174_453u32),
            (11, 127, 37, 0),
            (13, 7_174_417, 37, 7_174_453),
            (14, 7_174_418, 7_174_416, 0),
            (15, 7_174_419, 37, 7_174_453),
            (17, 7_174_417, 7_174_453, 0),
        ] {
            let step = &trace[code];
            assert_eq!(step.decoded, Some(112));
            assert_eq!(
                step.memory_reads
                    .data
                    .map(|read| (read.address, read.value)),
                Some((data_address, before)),
            );
            assert_eq!(step.after.registers.accumulator, after);
            assert_eq!(
                step.memory_delta
                    .data
                    .map(|write| (write.address, write.after)),
                Some((data_address, after)),
            );
            assert!(step.memory_delta.encryption.is_some());
        }
        assert_eq!(trace[18].decoded, Some(118));
        assert_eq!(guest.memory_word(plan.zero_low_address), Ok(0));
        assert_eq!(guest.memory_word(plan.zero_high_address), Ok(0));
        assert_eq!(guest.memory_word(127), Ok(0));
        assert_eq!(guest.input_consumed(), 0);
        assert!(guest.output().is_empty());
    }
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "negative nonzero entry accumulator proves scope of zero primitive"
)]
fn nonzero_entry_cannot_initialize_c32_zero() -> Result<(), String> {
    let profile = current_profile();
    let plan = layout::build_adjacent_c32_zero_source(profile)
        .map_err(|error| format!("{error:?}"))?;
    let mut guest = ProfileMachine::from_source(profile, &plan.source, vec![])
        .map_err(|error| error.to_string())?;
    guest = ProfileMachine::from_state(
        profile,
        guest.memory().to_vec(),
        vec![],
        ProfileRegisters {
            accumulator: 3,
            ..ProfileRegisters::default()
        },
    )
    .map_err(|error| error.to_string())?;
    assert_eq!(
        guest.run(19).map_err(|error| error.to_string())?,
        RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 19,
        }
    );
    assert_eq!(guest.memory_word(plan.zero_low_address), Ok(3));
    assert_eq!(guest.memory_word(plan.zero_high_address), Ok(3));
    Ok(())
}

#[test]
fn adjacent_zero_source_rejects_historical_profile() {
    assert_eq!(
        layout::build_adjacent_c32_zero_source(historical_profile()),
        Err(layout::ZeroCellSourceError::UnsupportedProfile),
    );
}

#[test]
#[expect(
    clippy::cognitive_complexity,
    clippy::indexing_slicing,
    clippy::panic_in_result_fn,
    clippy::too_many_lines,
    reason = "guest zero pair survives input and EOF"
)]
fn real_guest_retains_adjacent_zero_pair_after_input() -> Result<(), String> {
    let profile = current_profile();
    let plan = layout::build_adjacent_c32_zero_then_input_source(profile)
        .map_err(|error| format!("{error:?}"))?;
    assert_eq!(plan.source.len(), 33);
    assert_eq!(plan.input_code_address, Some(9));
    assert_eq!(plan.scratch_data_address, 41);
    assert_eq!(plan.zero_low_address, 7_174_418);
    assert_eq!(plan.zero_high_address, 7_174_419);
    let prepared = ProfileMachine::from_source(profile, &plan.source, vec![])
        .map_err(|error| error.to_string())?;
    assert_ne!(prepared.memory_word(plan.zero_low_address), Ok(0));
    assert_ne!(prepared.memory_word(plan.zero_high_address), Ok(0));
    for input in [vec![], vec![0], vec![2], vec![0x80], vec![0xff], vec![1, 2]]
    {
        let mut guest = ProfileMachine::from_state(
            profile,
            prepared.memory().to_vec(),
            input.clone(),
            ProfileRegisters::default(),
        )
        .map_err(|error| error.to_string())?;
        let mut trace = Vec::new();
        let outcome = guest
            .run_traced(11, &mut |step| trace.push(*step))
            .map_err(|error| error.to_string())?;
        assert_eq!(outcome, RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 11,
        });
        assert_eq!(trace.len(), 11);
        for (index, opcode) in b"jppjpppjp/v".iter().enumerate() {
            assert_eq!(trace[index].decoded, Some(*opcode));
            if index < 10 {
                assert!(trace[index].memory_delta.encryption.is_some());
            }
        }
        for (code, address) in
            [(5usize, plan.zero_high_address), (8, plan.zero_low_address)]
        {
            let step = &trace[code];
            assert_eq!(step.before.registers.data_pointer, address);
            assert_eq!(step.after.registers.accumulator, 0);
            assert_eq!(
                step.memory_delta
                    .data
                    .map(|write| (write.address, write.after)),
                Some((address, 0))
            );
        }
        assert_eq!(trace[8].after.registers.accumulator, 0);
        assert_eq!(
            trace[9].input,
            Some(
                input
                    .first()
                    .map_or(malbolge::TraceInput::EndOfInput, |byte| {
                        malbolge::TraceInput::Byte(*byte)
                    },)
            )
        );
        assert_eq!(
            trace[9].after.registers.accumulator,
            input
                .first()
                .map_or_else(|| profile.eof_word(), |byte| u32::from(*byte))
        );
        assert_eq!(guest.memory_word(plan.zero_low_address), Ok(0));
        assert_eq!(guest.memory_word(plan.zero_high_address), Ok(0));
        assert_eq!(guest.input_consumed(), usize::from(!input.is_empty()));
        assert!(guest.output().is_empty());
    }
    assert_eq!(
        layout::build_adjacent_c32_zero_then_input_source(historical_profile()),
        Err(layout::ZeroCellSourceError::UnsupportedProfile),
    );
    Ok(())
}

#[test]
#[expect(
    clippy::cognitive_complexity,
    clippy::excessive_nesting,
    clippy::indexing_slicing,
    clippy::panic_in_result_fn,
    clippy::too_many_lines,
    reason = "independent full finite graphical search for post-zero input"
)]
fn input_after_zero_matches_independent_source_census() -> Result<(), String> {
    const CODE: usize = 31;
    let mut admissible = 0usize;
    let mut matches = Vec::new();
    for prefix in 0..=(CODE - 11) {
        let mut source = (0..prefix)
            .map(|position| encode(111, position))
            .chain(
                b"jppjpppjp/v"
                    .iter()
                    .enumerate()
                    .map(|(index, opcode)| encode(*opcode, prefix + index)),
            )
            .chain(((prefix + 11)..CODE).map(|position| encode(111, position)))
            .collect::<Result<Vec<_>, _>>()?;
        let scratch = usize::from(source[prefix]) + 1;
        if scratch <= CODE + 4 {
            continue;
        }
        for first in 33..=126u8 {
            if !graphical_tail(first, CODE) {
                continue;
            }
            source.push(first);
            for second in 33..=126u8 {
                if !graphical_tail(second, CODE + 1) {
                    continue;
                }
                source.push(second);
                admissible += 1;
                let first_result = crazy(loader_word(&source, scratch), 0);
                let scratch_zero =
                    crazy(loader_word(&source, scratch + 1), first_result);
                let base = usize::try_from(loader_word(&source, scratch + 2))
                    .map_err(|error| error.to_string())?
                    + 1;
                if scratch_zero == 0
                    && base > CODE + 2
                    && base + 3 < 14_348_907
                    && !(scratch..=scratch + 2).contains(&base)
                    && !(base..=base + 3).contains(&scratch)
                {
                    let first_write =
                        crazy(loader_word(&source, base), scratch_zero);
                    let high =
                        crazy(loader_word(&source, base + 1), first_write);
                    let third = crazy(loader_word(&source, base + 2), high);
                    let low = crazy(first_write, third);
                    if high == 0
                        && low == 0
                        && loader_word(&source, base + 3) + 1
                            == u32::try_from(base)
                                .map_err(|error| error.to_string())?
                    {
                        matches.push(source.clone());
                    }
                }
                _ = source.pop();
            }
            _ = source.pop();
        }
    }
    assert_eq!(admissible, 1216);
    assert_eq!(matches.len(), 16);
    let plan =
        layout::build_adjacent_c32_zero_then_input_source(current_profile())
            .map_err(|error| format!("{error:?}"))?;
    assert_eq!(plan.source, matches[0]);
    Ok(())
}

#[test]
#[expect(
    clippy::cognitive_complexity,
    clippy::excessive_nesting,
    clippy::indexing_slicing,
    clippy::integer_division,
    clippy::integer_division_remainder_used,
    clippy::panic_in_result_fn,
    clippy::too_many_lines,
    reason = "independent full graphical search and 257-class raw C32 witness"
)]
fn guest_byte_c32_pair_matches_independent_source_census() -> Result<(), String>
{
    const CODE: usize = 31;
    const BODY: &[u8] = b"jppjpppj*/pjpv";
    let mut eligible = 0usize;
    let mut matches = Vec::new();
    for prefix in 0..=(CODE - BODY.len()) {
        let mut source = (0..prefix)
            .map(|position| encode(111, position))
            .chain(
                BODY.iter()
                    .enumerate()
                    .map(|(index, opcode)| encode(*opcode, prefix + index)),
            )
            .chain(
                ((prefix + BODY.len())..CODE)
                    .map(|position| encode(111, position)),
            )
            .collect::<Result<Vec<_>, _>>()?;
        let scratch = usize::from(source[prefix]) + 1;
        if scratch <= CODE + 4 {
            continue;
        }
        for head in 33..=126u8 {
            if !graphical_tail(head, CODE) {
                continue;
            }
            source.push(head);
            for tail in 33..=126u8 {
                if !graphical_tail(tail, CODE + 1) {
                    continue;
                }
                source.push(tail);
                eligible += 1;
                let first = crazy(loader_word(&source, scratch), 0);
                let scratch_zero =
                    crazy(loader_word(&source, scratch + 1), first);
                let base = usize::try_from(loader_word(&source, scratch + 2))
                    .map_err(|error| error.to_string())?
                    + 1;
                if scratch_zero == 0
                    && base > source.len()
                    && base + 3 < 14_348_907
                    && !(scratch..=scratch + 2).contains(&base)
                    && !(base..=base + 3).contains(&scratch)
                {
                    let first_relocated = crazy(loader_word(&source, base), 0);
                    let high =
                        crazy(loader_word(&source, base + 1), first_relocated);
                    let third = crazy(loader_word(&source, base + 2), high);
                    let primed_low = (first_relocated / 3)
                        + (first_relocated % 3) * 4_782_969;
                    if high == 0
                        && primed_low == 7_174_453
                        && third == 7_174_453
                        && loader_word(&source, base + 3) + 1
                            == u32::try_from(base)
                                .map_err(|error| error.to_string())?
                    {
                        matches.push(source.clone());
                    }
                }
                _ = source.pop();
            }
            _ = source.pop();
        }
    }
    assert_eq!(eligible, 1024);
    assert_eq!(matches.len(), 13);
    let plan = layout::build_guest_byte_c32_pair_source(current_profile())
        .map_err(|error| format!("{error:?}"))?;
    assert_eq!(plan.source, matches[0]);
    assert_eq!(plan.source.len(), 33);
    let mut hex = String::new();
    for byte in &plan.source {
        write!(&mut hex, "{byte:02x}").map_err(|error| error.to_string())?;
    }
    assert_eq!(hex, RAW_PAIR_HEX);
    assert_eq!(plan.scratch_data_address, 41);
    assert_eq!(plan.scratch_initial_words, [7_174_417, 36, 7_174_417]);
    assert_eq!(plan.relocated_initial_words, [36, 7_174_417, 36, 7_174_417]);
    assert_eq!(plan.pair_low_address, 7_174_418);
    assert_eq!(plan.pair_high_address, 7_174_419);
    assert_eq!(plan.high_zero_code_address, 5);
    assert_eq!(plan.low_prime_code_address, 8);
    assert_eq!(plan.input_code_address, 9);
    assert_eq!(plan.encoded_store_code_address, 10);
    assert_eq!(plan.low_store_code_address, 12);
    let all_input = (0u32..=255).chain([14_348_906]);
    let mut observed = HashSet::new();
    for input in all_input {
        let encoded = crazy(7_174_453, input);
        let decoded = crazy(7_174_453, encoded);
        assert_eq!(decoded, input, "raw input {input}");
        assert!(observed.insert(encoded), "input {input} must be distinct");
    }
    assert_eq!(observed.len(), 257);
    Ok(())
}

#[test]
#[expect(
    clippy::cognitive_complexity,
    clippy::indexing_slicing,
    clippy::panic_in_result_fn,
    clippy::too_many_lines,
    reason = "real input/EOF read, two source-loaded writes and exact C32 pair"
)]
fn real_guest_materializes_raw_byte_in_adjacent_c32_pair() -> Result<(), String>
{
    let profile = current_profile();
    let plan = layout::build_guest_byte_c32_pair_source(profile)
        .map_err(|error| format!("{error:?}"))?;
    let initial = ProfileMachine::from_source(profile, &plan.source, vec![])
        .map_err(|error| error.to_string())?;
    for input in [
        vec![],
        vec![0],
        vec![2],
        vec![0x7f],
        vec![0x80],
        vec![0xff],
        vec![0x01, 0x02],
    ] {
        let raw = input
            .first()
            .map_or_else(|| profile.eof_word(), |byte| u32::from(*byte));
        let encoded = crazy(7_174_453, raw);
        let mut guest = ProfileMachine::from_state(
            profile,
            initial.memory().to_vec(),
            input.clone(),
            ProfileRegisters::default(),
        )
        .map_err(|error| error.to_string())?;
        let mut trace = Vec::new();
        assert_eq!(
            guest
                .run_traced(14, &mut |step| trace.push(*step))
                .map_err(|error| error.to_string())?,
            RunOutcome::Terminated {
                reason: Termination::HaltInstruction,
                steps: 14,
            }
        );
        assert_eq!(trace.len(), 14);
        for (index, opcode) in b"jppjpppj*/pjpv".iter().enumerate() {
            assert_eq!(trace[index].decoded, Some(*opcode));
            if index != 13 {
                assert!(trace[index].memory_delta.encryption.is_some());
            }
        }
        assert_eq!(trace[5].after.registers.accumulator, 0);
        assert_eq!(
            trace[5]
                .memory_delta
                .data
                .map(|write| (write.address, write.after)),
            Some((plan.pair_high_address, 0)),
        );
        assert_eq!(
            trace[8].before.registers.data_pointer,
            plan.pair_low_address
        );
        assert_eq!(trace[8].after.registers.accumulator, 7_174_453);
        assert_eq!(
            trace[9].input,
            Some(
                input
                    .first()
                    .map_or(malbolge::TraceInput::EndOfInput, |byte| {
                        malbolge::TraceInput::Byte(*byte)
                    },)
            )
        );
        assert_eq!(trace[9].after.registers.accumulator, raw);
        assert_eq!(
            trace[10].before.registers.data_pointer,
            plan.pair_low_address + 2
        );
        assert_eq!(
            trace[10]
                .memory_reads
                .data
                .map(|read| (read.address, read.value)),
            Some((plan.pair_low_address + 2, 7_174_453)),
        );
        assert_eq!(trace[10].after.registers.accumulator, encoded);
        assert_eq!(guest.memory_word(plan.pair_low_address + 2), Ok(encoded));
        assert_eq!(
            trace[11]
                .memory_reads
                .data
                .map(|read| (read.address, read.value)),
            Some((plan.pair_low_address + 3, plan.pair_low_address - 1)),
        );
        assert_eq!(
            trace[11].after.registers.data_pointer,
            plan.pair_low_address
        );
        assert_eq!(
            trace[12]
                .memory_reads
                .data
                .map(|read| (read.address, read.value)),
            Some((plan.pair_low_address, 7_174_453)),
        );
        assert_eq!(trace[12].after.registers.accumulator, raw);
        assert_eq!(
            trace[12]
                .memory_delta
                .data
                .map(|write| (write.address, write.after)),
            Some((plan.pair_low_address, raw)),
        );
        assert_eq!(guest.memory_word(plan.pair_low_address), Ok(raw));
        assert_eq!(guest.memory_word(plan.pair_high_address), Ok(0));
        assert_eq!(guest.input_consumed(), usize::from(!input.is_empty()));
        assert!(guest.output().is_empty());
    }
    assert_eq!(
        layout::build_guest_byte_c32_pair_source(historical_profile()),
        Err(layout::ZeroCellSourceError::UnsupportedProfile),
    );
    Ok(())
}

#[test]
#[expect(
    clippy::indexing_slicing,
    clippy::panic_in_result_fn,
    reason = "mutated guest instructions must lose raw C32 parity"
)]
fn raw_c32_pair_refuses_missing_input_or_broken_dataflow() -> Result<(), String>
{
    let profile = current_profile();
    let original = layout::build_guest_byte_c32_pair_source(profile)
        .map_err(|error| format!("{error:?}"))?;
    for (position, opcode) in
        [(9usize, b'o'), (10, b'*'), (11, b'o'), (12, b'*')]
    {
        let mut altered = original.source.clone();
        altered[position] = encode(opcode, position)?;
        let mut guest = ProfileMachine::from_source(profile, &altered, vec![2])
            .map_err(|error| error.to_string())?;
        assert_eq!(
            guest.run(14).map_err(|error| error.to_string())?,
            RunOutcome::Terminated {
                reason: Termination::HaltInstruction,
                steps: 14,
            },
            "mutation at C{position}",
        );
        assert_ne!(
            guest.memory_word(original.pair_low_address),
            Ok(2),
            "mutated opcode C{position} must not pass raw-byte store parity",
        );
        if position == 9 {
            assert_eq!(guest.input_consumed(), 0);
        } else {
            assert_eq!(guest.input_consumed(), 1);
        }
    }
    let mut eof =
        ProfileMachine::from_source(profile, &original.source, vec![])
            .map_err(|error| error.to_string())?;
    assert_eq!(
        eof.run(14).map_err(|error| error.to_string())?,
        RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 14,
        },
    );
    assert_eq!(
        [
            eof.memory_word(original.pair_low_address)
                .map_err(|error| error.to_string())?,
            eof.memory_word(original.pair_high_address)
                .map_err(|error| error.to_string())?,
        ],
        [14_348_906, 0],
    );
    assert_ne!([14_348_906u32, 0u32], [4_644_102u32, 299u32]);
    Ok(())
}

#[test]
#[expect(
    clippy::cognitive_complexity,
    clippy::indexing_slicing,
    clippy::panic_in_result_fn,
    reason = "full 257-case independent guest raw-input state census"
)]
fn all_successful_bytes_and_eof_have_physical_c32_pair_parity()
-> Result<(), String> {
    let profile = current_profile();
    let plan = layout::build_guest_byte_c32_pair_source(profile)
        .map_err(|error| format!("{error:?}"))?;
    let loaded = ProfileMachine::from_source(profile, &plan.source, vec![])
        .map_err(|error| error.to_string())?;
    assert_ne!(loaded.memory_word(plan.pair_low_address), Ok(0));
    assert_ne!(loaded.memory_word(plan.pair_high_address), Ok(0));
    let mut covered = BTreeSet::new();
    for expected in (0..=255u32).chain([profile.eof_word()]) {
        let input = if expected == profile.eof_word() {
            Vec::new()
        } else {
            vec![u8::try_from(expected).map_err(|error| error.to_string())?]
        };
        let mut guest = ProfileMachine::from_state(
            profile,
            loaded.memory().to_vec(),
            input.clone(),
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
        assert_eq!(trace[9].decoded, Some(b'/'));
        assert_eq!(trace[9].after.registers.accumulator, expected);
        assert_eq!(trace[10].decoded, Some(b'p'));
        assert_eq!(trace[11].decoded, Some(b'j'));
        assert_eq!(trace[12].decoded, Some(b'p'));
        assert_eq!(trace[12].after.registers.accumulator, expected);
        assert_eq!(
            trace[12].before.registers.data_pointer,
            plan.pair_low_address
        );
        assert_eq!(guest.memory_word(plan.pair_low_address), Ok(expected));
        assert_eq!(guest.memory_word(plan.pair_high_address), Ok(0));
        assert_eq!(guest.input_consumed(), input.len());
        assert!(guest.output().is_empty());
        assert!(covered.insert(expected));
    }
    assert_eq!(covered.len(), 257);
    Ok(())
}

// Raw byte 0x02 and genuine EOF both enter the low physical word with units
// trit 2; the signed C23 EOF low word instead requires units trit 0. Crazy
// cannot move trits between positions, so constant-operand p chains cannot
// preserve successful byte 0x02 and also repair EOF. Rotations, data-dependent
// routing and earlier alternative encoding are deliberately out of scope.
#[test]
#[expect(
    clippy::indexing_slicing,
    clippy::integer_division_remainder_used,
    clippy::panic_in_result_fn,
    reason = "small exhaustive scalar ternary truth-table closure"
)]
fn fixed_crazy_postfold_cannot_convert_raw_eof_into_signed_c23()
-> Result<(), String> {
    let truth = [[1u8, 0, 0], [1, 0, 2], [2, 2, 1]];
    let mut unary_maps = BTreeSet::from([[0u8, 1, 2]]);
    loop {
        let before = unary_maps.len();
        // Every possible fixed data trit at this coordinate is included,
        // even though only a subset is physically source-loader reachable.
        for current in unary_maps.clone() {
            for row in truth {
                let folded = [
                    row[usize::from(current[0])],
                    row[usize::from(current[1])],
                    row[usize::from(current[2])],
                ];
                _ = unary_maps.insert(folded);
            }
        }
        if unary_maps.len() == before {
            break;
        }
    }
    // The finite closure includes every chain length, not just a test bound.
    assert_eq!(unary_maps.len(), 15);
    let byte_preserving = unary_maps
        .into_iter()
        .filter(|map| *map == [0, 1, 2])
        .collect::<Vec<_>>();
    assert_eq!(byte_preserving, vec![[0, 1, 2]]);
    // Both byte 0x02 and raw N15 EOF have source units trit 2.
    let raw_byte_two_units = 2u8;
    let raw_eof_units = u8::try_from(current_profile().eof_word() % 3)
        .map_err(|error| error.to_string())?;
    let canonical_eof_units =
        u8::try_from(4_644_102u32 % 3).map_err(|error| error.to_string())?;
    assert_eq!(raw_byte_two_units, raw_eof_units);
    assert_ne!(raw_eof_units, canonical_eof_units);
    assert_eq!(byte_preserving[0][usize::from(raw_eof_units)], 2);
    assert_eq!(canonical_eof_units, 0);
    Ok(())
}

#[test]
#[expect(
    clippy::cognitive_complexity,
    clippy::indexing_slicing,
    clippy::integer_division_remainder_used,
    clippy::panic_in_result_fn,
    clippy::too_many_lines,
    reason = "real byte-output trace only after both source-loaded C32 writes"
)]
fn real_guest_echoes_raw_byte_only_after_adjacent_state_writes()
-> Result<(), String> {
    let profile = current_profile();
    let plan = layout::build_guest_byte_c32_pair_echo_source(profile)
        .map_err(|error| format!("{error:?}"))?;
    assert_eq!(plan.pair.source.len(), 33);
    assert_eq!(plan.output_code_address, 13);
    assert_eq!(plan.halt_code_address, 14);
    let raw_plan = layout::build_guest_byte_c32_pair_source(profile)
        .map_err(|error| format!("{error:?}"))?;
    assert_eq!(&plan.pair.source[..13], &raw_plan.source[..13]);
    assert_eq!(&plan.pair.source[15..], &raw_plan.source[15..]);
    let original_loader =
        ProfileMachine::from_source(profile, &plan.pair.source, vec![])
            .map_err(|error| error.to_string())?;
    for stream in [
        vec![],
        vec![0],
        vec![1],
        vec![2],
        vec![0x80],
        vec![0xff],
        vec![0x5a, 0x9a],
    ] {
        let expected_raw = stream
            .first()
            .map_or_else(|| profile.eof_word(), |byte| u32::from(*byte));
        let expected_output = u8::try_from(expected_raw % 256)
            .map_err(|error| error.to_string())?;
        let mut guest = ProfileMachine::from_state(
            profile,
            original_loader.memory().to_vec(),
            stream.clone(),
            ProfileRegisters::default(),
        )
        .map_err(|error| error.to_string())?;
        let mut trace = Vec::new();
        assert_eq!(
            guest
                .run_traced(15, &mut |step| trace.push(*step))
                .map_err(|error| error.to_string())?,
            RunOutcome::Terminated {
                reason: Termination::HaltInstruction,
                steps: 15,
            }
        );
        assert_eq!(trace.len(), 15);
        for (index, opcode) in b"jppjpppj*/pjp<v".iter().enumerate() {
            assert_eq!(trace[index].decoded, Some(*opcode));
        }
        assert_eq!(trace[13].before.registers.accumulator, expected_raw);
        assert_eq!(trace[13].after.registers.accumulator, expected_raw);
        assert_eq!(
            guest.memory_word(plan.pair.pair_low_address),
            Ok(expected_raw)
        );
        assert_eq!(guest.memory_word(plan.pair.pair_high_address), Ok(0));
        assert_eq!(guest.output(), [expected_output]);
        assert_eq!(guest.input_consumed(), usize::from(!stream.is_empty()));
    }
    assert_eq!(
        layout::build_guest_byte_c32_pair_echo_source(historical_profile()),
        Err(layout::ZeroCellSourceError::UnsupportedProfile),
    );
    Ok(())
}

#[test]
#[expect(
    clippy::arithmetic_side_effects,
    clippy::indexing_slicing,
    clippy::integer_division_remainder_used,
    clippy::panic_in_result_fn,
    clippy::too_many_lines,
    reason = "independent trit rotation and genuine guest memory-reload trace"
)]
fn guest_output_reloads_written_low_word_not_input_accumulator()
-> Result<(), String> {
    let profile = current_profile();
    let plan = layout::build_guest_byte_c32_pair_reload_source(profile)
        .map_err(|error| format!("{error:?}"))?;
    let raw = layout::build_guest_byte_c32_pair_source(profile)
        .map_err(|error| format!("{error:?}"))?;
    assert_eq!(plan.pair.source.len(), 33);
    assert_eq!(&plan.pair.source[..13], &raw.source[..13]);
    assert_eq!(&plan.pair.source[31..], &raw.source[31..]);
    assert_eq!(plan.rotation_code_addresses, [16, 20, 24, 28]);
    assert_eq!(plan.output_code_address, 29);
    assert_eq!(plan.halt_code_address, 30);
    let loader =
        ProfileMachine::from_source(profile, &plan.pair.source, vec![])
            .map_err(|error| error.to_string())?;
    for stream in [
        vec![],
        vec![0],
        vec![1],
        vec![2],
        vec![0x7f],
        vec![0x80],
        vec![0xff],
        vec![0x5a, 0x9a],
    ] {
        let raw = stream
            .first()
            .map_or_else(|| profile.eof_word(), |byte| u32::from(*byte));
        let mut expected = raw;
        let mut guest = ProfileMachine::from_state(
            profile,
            loader.memory().to_vec(),
            stream.clone(),
            ProfileRegisters::default(),
        )
        .map_err(|error| error.to_string())?;
        let mut trace = Vec::new();
        assert_eq!(
            guest
                .run_traced(31, &mut |step| trace.push(*step))
                .map_err(|error| error.to_string())?,
            RunOutcome::Terminated {
                reason: Termination::HaltInstruction,
                steps: 31,
            }
        );
        assert_eq!(trace.len(), 31);
        assert_eq!(trace[9].decoded, Some(b'/'));
        assert_eq!(trace[12].decoded, Some(b'p'));
        assert_eq!(
            trace[12].memory_reads.data.map(|read| read.address),
            Some(plan.pair.pair_low_address)
        );
        for rotation in 0..4 {
            for hop in 0..3 {
                let step = &trace[13 + rotation * 4 + hop];
                assert_eq!(step.decoded, Some(b'j'));
                let (data_address, read, next_data) = [
                    (plan.pair.pair_high_address, 0, 1),
                    (1, 100, 101),
                    (101, 7_174_417, plan.pair.pair_low_address),
                ][hop];
                assert_eq!(
                    step.memory_reads
                        .data
                        .map(|read| (read.address, read.value)),
                    Some((data_address, read))
                );
                assert_eq!(step.after.registers.data_pointer, next_data);
                assert!(step.memory_delta.encryption.is_some());
            }
            let step = &trace[16 + rotation * 4];
            assert_eq!(step.decoded, Some(b'*'));
            assert_eq!(
                step.memory_reads
                    .data
                    .map(|read| (read.address, read.value)),
                Some((plan.pair.pair_low_address, expected))
            );
            expected = expected / 3 + (expected % 3) * 4_782_969;
            assert_eq!(step.after.registers.accumulator, expected);
        }
        let emitted =
            u8::try_from(expected % 256).map_err(|error| error.to_string())?;
        assert_eq!(trace[29].decoded, Some(b'<'));
        assert_eq!(trace[29].before.registers.accumulator, expected);
        assert_eq!(guest.output(), [emitted]);
        assert_eq!(guest.memory_word(plan.pair.pair_low_address), Ok(expected));
        assert_eq!(guest.memory_word(plan.pair.pair_high_address), Ok(0));
        assert_eq!(guest.input_consumed(), usize::from(!stream.is_empty()));

        // Perturb only the accumulator at the boundary after the actual
        // input-backed low-word store. The later output must still be read
        // from memory through genuine guest rotations, not the old A value.
        let mut prefix = ProfileMachine::from_state(
            profile,
            loader.memory().to_vec(),
            stream,
            ProfileRegisters::default(),
        )
        .map_err(|error| error.to_string())?;
        assert_eq!(
            prefix.run(13).map_err(|error| error.to_string())?,
            RunOutcome::BudgetExhausted { steps: 13 }
        );
        assert_eq!(prefix.memory_word(plan.pair.pair_low_address), Ok(raw));
        for accumulator in [0, 3, profile.eof_word()] {
            let mut resumed = ProfileMachine::from_state(
                profile,
                prefix.memory().to_vec(),
                vec![],
                ProfileRegisters {
                    accumulator,
                    ..prefix.registers()
                },
            )
            .map_err(|error| error.to_string())?;
            assert_eq!(
                resumed.run(18).map_err(|error| error.to_string())?,
                RunOutcome::Terminated {
                    reason: Termination::HaltInstruction,
                    steps: 18,
                }
            );
            assert_eq!(resumed.output(), [emitted]);
            assert_eq!(
                resumed.memory_word(plan.pair.pair_low_address),
                Ok(expected)
            );
            assert_eq!(resumed.memory_word(plan.pair.pair_high_address), Ok(0));
        }
    }
    assert_eq!(
        layout::build_guest_byte_c32_pair_reload_source(historical_profile()),
        Err(layout::ZeroCellSourceError::UnsupportedProfile)
    );
    Ok(())
}

#[test]
#[expect(
    clippy::arithmetic_side_effects,
    clippy::indexing_slicing,
    clippy::integer_division_remainder_used,
    clippy::panic_in_result_fn,
    clippy::too_many_lines,
    reason = "257-case scalar EOF separation plus real guest nonlocal p"
)]
fn real_guest_nonlocal_crazy_separates_raw_eof_without_c23_conversion()
-> Result<(), String> {
    let profile = current_profile();
    let plan =
        layout::build_guest_byte_c32_pair_eof_distinguish_source(profile)
            .map_err(|error| format!("{error:?}"))?;
    let original = layout::build_guest_byte_c32_pair_source(profile)
        .map_err(|error| format!("{error:?}"))?;
    assert_eq!(plan.pair.source.len(), 33);
    assert_eq!(&plan.pair.source[..13], &original.source[..13]);
    assert_eq!(&plan.pair.source[19..], &original.source[19..]);
    assert_eq!(plan.encoded_rotation_code_address, 14);
    assert_eq!(plan.mixed_store_code_address, 16);
    assert_eq!(plan.output_code_address, 17);
    assert_eq!(plan.halt_code_address, 18);
    let ones = 7_174_453u32;
    let transform = |raw: u32| {
        let encoded = crazy(ones, raw);
        let rotated = encoded / 3 + (encoded % 3) * 4_782_969;
        (encoded, rotated, crazy(raw, rotated))
    };
    let eof_state = transform(profile.eof_word()).2;
    assert_eq!(eof_state, ones);
    let bytes = (0u32..=255).map(|raw| transform(raw).2).collect::<Vec<_>>();
    assert_eq!(bytes.len(), 256);
    assert!(!bytes.contains(&eof_state));
    assert_ne!(transform(0).2, eof_state);
    assert_ne!(transform(2).2, eof_state);
    // This nonlocal store does not implement an identity byte-preserving
    // source local, and its output is not C23 EOF-aware putchar.
    assert_ne!(transform(1).2, 1);
    let virgin =
        ProfileMachine::from_source(profile, &plan.pair.source, vec![])
            .map_err(|error| error.to_string())?;
    for input in [
        vec![],
        vec![0],
        vec![1],
        vec![2],
        vec![0x7f],
        vec![0x80],
        vec![0xff],
        vec![0x5a, 0x9a],
    ] {
        let raw = input
            .first()
            .map_or_else(|| profile.eof_word(), |byte| u32::from(*byte));
        let (encoded, rotated, mixed) = transform(raw);
        let mut guest = ProfileMachine::from_state(
            profile,
            virgin.memory().to_vec(),
            input.clone(),
            ProfileRegisters::default(),
        )
        .map_err(|error| error.to_string())?;
        let mut trace = Vec::new();
        assert_eq!(
            guest
                .run_traced(19, &mut |step| trace.push(*step))
                .map_err(|error| error.to_string())?,
            RunOutcome::Terminated {
                reason: Termination::HaltInstruction,
                steps: 19,
            }
        );
        assert_eq!(trace.len(), 19);
        assert_eq!(
            &trace[..13].iter().map(|s| s.decoded).collect::<Vec<_>>(),
            &b"jppjpppj*/pjp"
                .iter()
                .copied()
                .map(Some)
                .collect::<Vec<_>>()
        );
        assert_eq!(trace[13].decoded, Some(b'o'));
        assert_eq!(trace[14].decoded, Some(b'*'));
        assert_eq!(
            trace[14]
                .memory_reads
                .data
                .map(|read| (read.address, read.value)),
            Some((plan.pair.pair_low_address + 2, encoded))
        );
        assert_eq!(trace[14].after.registers.accumulator, rotated);
        assert_eq!(trace[15].decoded, Some(b'j'));
        assert_eq!(
            trace[15]
                .memory_reads
                .data
                .map(|read| (read.address, read.value)),
            Some((
                plan.pair.pair_low_address + 3,
                plan.pair.pair_low_address - 1
            ))
        );
        assert_eq!(
            trace[15].after.registers.data_pointer,
            plan.pair.pair_low_address
        );
        assert_eq!(trace[16].decoded, Some(b'p'));
        assert_eq!(
            trace[16]
                .memory_reads
                .data
                .map(|read| (read.address, read.value)),
            Some((plan.pair.pair_low_address, raw))
        );
        assert_eq!(trace[16].after.registers.accumulator, mixed);
        assert_eq!(trace[17].decoded, Some(b'<'));
        assert_eq!(trace[18].decoded, Some(b'v'));
        assert_eq!(guest.memory_word(plan.pair.pair_low_address), Ok(mixed));
        assert_eq!(guest.memory_word(plan.pair.pair_high_address), Ok(0));
        let byte =
            u8::try_from(mixed % 256).map_err(|error| error.to_string())?;
        assert_eq!(guest.output(), [byte]);
        assert_eq!(guest.input_consumed(), usize::from(!input.is_empty()));
    }
    assert_eq!(
        layout::build_guest_byte_c32_pair_eof_distinguish_source(
            historical_profile()
        ),
        Err(layout::ZeroCellSourceError::UnsupportedProfile)
    );
    Ok(())
}

#[test]
#[expect(
    clippy::cognitive_complexity,
    clippy::indexing_slicing,
    clippy::integer_division,
    clippy::integer_division_remainder_used,
    clippy::panic_in_result_fn,
    clippy::too_many_lines,
    reason = "257-case EOF oracle and actual N15 pointer selection"
)]
fn real_guest_eof_zero_word_selects_data_pointer() -> Result<(), String> {
    let profile = current_profile();
    let plan =
        layout::build_guest_byte_c32_pair_eof_zero_pointer_source(profile)
            .map_err(|error| format!("{error:?}"))?;
    assert_eq!(plan.zero_store_code_address, 20);
    assert_eq!(plan.selected_pointer_code_address, 24);
    assert_eq!(plan.data_rotation_code_address, 25);
    assert_eq!(plan.output_code_address, 26);
    assert_eq!(plan.halt_code_address, 27);
    let eof = profile.eof_word();
    let ones = 7_174_453;
    let rotated = |word: u32| word / 3 + (word % 3) * 4_782_969;
    let classify = |raw: u32| {
        let encoded = crazy(ones, raw);
        let mixed = crazy(raw, rotated(encoded));
        crazy(mixed, mixed)
    };
    assert_eq!(classify(eof), 0);
    let virgin =
        ProfileMachine::from_source(profile, &plan.pair.source, vec![])
            .map_err(|error| error.to_string())?;
    let mut word_values = HashSet::new();
    let mut expected_bytes = BTreeSet::new();
    for raw in 0u32..=255 {
        let word = classify(raw);
        assert_ne!(word, 0, "byte {raw} matched raw EOF");
        assert!(word >= 2_391_400 && word < profile.memory_words());
        _ = word_values.insert(word);
        let destination = word + 1;
        let value = if destination == plan.pair.pair_low_address {
            word
        } else {
            virgin
                .memory_word(destination)
                .map_err(|error| error.to_string())?
        };
        let emitted = u8::try_from(rotated(value) % 256)
            .map_err(|error| error.to_string())?;
        _ = expected_bytes.insert(emitted);
        assert!([12, 41].contains(&emitted), "byte {raw}: {emitted}");
    }
    assert_eq!(word_values.len(), 39);
    assert_eq!(expected_bytes, BTreeSet::from([12, 41]));
    for input in [
        vec![],
        vec![0],
        vec![1],
        vec![2],
        vec![0x7f],
        vec![0x80],
        vec![0xff],
        vec![0x5a, 0x9a],
    ] {
        let raw = input
            .first()
            .map_or_else(|| profile.eof_word(), |byte| u32::from(*byte));
        let word = classify(raw);
        let selected_address = word + 1;
        let mut guest = ProfileMachine::from_state(
            profile,
            virgin.memory().to_vec(),
            input.clone(),
            ProfileRegisters::default(),
        )
        .map_err(|error| error.to_string())?;
        let mut trace = Vec::new();
        assert_eq!(
            guest
                .run_traced(28, &mut |step| trace.push(*step))
                .map_err(|error| error.to_string())?,
            RunOutcome::Terminated {
                reason: Termination::HaltInstruction,
                steps: 28,
            }
        );
        assert_eq!(trace.len(), 28);
        assert_eq!(trace[20].decoded, Some(b'p'));
        assert_eq!(trace[20].after.registers.accumulator, word);
        assert_eq!(
            trace[20]
                .memory_reads
                .data
                .map(|read| (read.address, read.value)),
            Some((
                plan.pair.pair_low_address,
                trace[16].after.registers.accumulator
            ))
        );
        assert_eq!(
            trace[20]
                .memory_delta
                .data
                .map(|write| (write.address, write.after)),
            Some((plan.pair.pair_low_address, word))
        );
        for (site, target) in [
            (17usize, 1u32),
            (18, 101),
            (19, plan.pair.pair_low_address),
            (21, 1),
            (22, 101),
            (23, plan.pair.pair_low_address),
        ] {
            assert_eq!(trace[site].decoded, Some(b'j'));
            assert_eq!(trace[site].after.registers.data_pointer, target);
        }
        assert_eq!(trace[24].decoded, Some(b'j'));
        assert_eq!(trace[24].after.registers.data_pointer, selected_address);
        assert_eq!(trace[25].decoded, Some(b'*'));
        assert_eq!(
            trace[25].memory_reads.data.map(|read| read.address),
            Some(selected_address)
        );
        assert_eq!(trace[26].decoded, Some(b'<'));
        assert_eq!(trace[27].decoded, Some(b'v'));
        assert_eq!(guest.memory_word(plan.pair.pair_high_address), Ok(0));
        assert_eq!(guest.input_consumed(), usize::from(!input.is_empty()));
        let byte = u8::try_from(trace[25].after.registers.accumulator % 256)
            .map_err(|error| error.to_string())?;
        assert_eq!(guest.output(), [byte]);
        if input.is_empty() {
            assert_eq!(selected_address, 1);
            assert_eq!(byte, 154);
        } else {
            assert!(selected_address > 2_391_400);
            assert!([12, 41].contains(&byte));
        }
    }
    assert_eq!(
        layout::build_guest_byte_c32_pair_eof_zero_pointer_source(
            historical_profile()
        ),
        Err(layout::ZeroCellSourceError::UnsupportedProfile)
    );
    Ok(())
}

#[test]
#[expect(
    clippy::cognitive_complexity,
    clippy::indexing_slicing,
    clippy::panic_in_result_fn,
    reason = "negative guest EOF-zero store mutation"
)]
fn missing_eof_zero_store_changes_guest_data_selection() -> Result<(), String> {
    let profile = current_profile();
    let original =
        layout::build_guest_byte_c32_pair_eof_zero_pointer_source(profile)
            .map_err(|error| format!("{error:?}"))?;
    let mut tampered = original.pair.source.clone();
    tampered[20] = encode(b'o', 20)?;
    for (input, expected_selected, changed_selected) in
        [(vec![], 1u32, 7_174_454u32), (vec![0], 7_174_454, 1)]
    {
        let mut correct = ProfileMachine::from_source(
            profile,
            &original.pair.source,
            input.clone(),
        )
        .map_err(|error| error.to_string())?;
        let mut changed =
            ProfileMachine::from_source(profile, &tampered, input)
                .map_err(|error| error.to_string())?;
        let mut correct_steps = Vec::new();
        let mut changed_steps = Vec::new();
        assert_eq!(
            correct
                .run_traced(28, &mut |step| correct_steps.push(*step))
                .map_err(|error| error.to_string())?,
            RunOutcome::Terminated {
                reason: Termination::HaltInstruction,
                steps: 28,
            }
        );
        assert_eq!(
            changed
                .run_traced(28, &mut |step| changed_steps.push(*step))
                .map_err(|error| error.to_string())?,
            RunOutcome::Terminated {
                reason: Termination::HaltInstruction,
                steps: 28,
            }
        );
        assert_eq!(correct_steps[20].decoded, Some(b'p'));
        assert_eq!(changed_steps[20].decoded, Some(b'o'));
        assert!(correct_steps[20].memory_delta.data.is_some());
        assert!(changed_steps[20].memory_delta.data.is_none());
        assert_eq!(
            correct_steps[24].after.registers.data_pointer,
            expected_selected
        );
        assert_eq!(
            changed_steps[24].after.registers.data_pointer,
            changed_selected
        );
        assert_ne!(correct.output(), changed.output());
    }
    Ok(())
}

#[test]
#[expect(
    clippy::arithmetic_side_effects,
    clippy::indexing_slicing,
    clippy::integer_division_remainder_used,
    clippy::panic_in_result_fn,
    reason = "red-first real 257-class N15 EOF classifier experiment"
)]
fn eof_zero_data_pointer_physically_classifies_all_257_inputs()
-> Result<(), String> {
    let profile = current_profile();
    let plan =
        layout::build_guest_byte_c32_pair_eof_zero_pointer_source(profile)
            .map_err(|error| format!("{error:?}"))?;
    // This is deliberately built independently of any proposed publisher.
    // C21 * rotates the actual high-zero word to A=0; C22 o advances
    // to virgin low+3; C23 j returns to the input-backed predicate;
    // C24 j selects a word and C25 p folds it into a byte classifier.
    let mut source = plan.pair.source.clone();
    for (site, opcode) in [(21usize, b'*'), (22, b'o'), (25, b'p')] {
        source[site] = encode(opcode, site)?;
    }
    let published =
        layout::build_guest_byte_c32_pair_eof_classify_source(profile)
            .map_err(|error| format!("{error:?}"))?;
    assert_eq!(published.pair.source, source);
    assert_eq!(published.accumulator_clear_code_address, 21);
    assert_eq!(published.selected_pointer_code_address, 24);
    assert_eq!(published.classified_store_code_address, 25);
    assert_eq!(published.output_code_address, 26);
    assert_eq!(published.halt_code_address, 27);
    assert_eq!(
        layout::build_guest_byte_c32_pair_eof_classify_source(
            historical_profile()
        ),
        Err(layout::ZeroCellSourceError::UnsupportedProfile)
    );
    let virgin = ProfileMachine::from_source(profile, &source, vec![])
        .map_err(|error| error.to_string())?;
    let mut observed = BTreeSet::new();
    for input_word in 0u32..=256 {
        let input = if input_word == 256 {
            vec![]
        } else {
            vec![u8::try_from(input_word).map_err(|error| error.to_string())?]
        };
        let mut guest = ProfileMachine::from_state(
            profile,
            virgin.memory().to_vec(),
            input.clone(),
            ProfileRegisters::default(),
        )
        .map_err(|error| error.to_string())?;
        let mut steps = Vec::new();
        assert_eq!(
            guest
                .run_traced(28, &mut |step| steps.push(*step))
                .map_err(|error| error.to_string())?,
            RunOutcome::Terminated {
                reason: Termination::HaltInstruction,
                steps: 28,
            }
        );
        assert_eq!(steps[20].decoded, Some(b'p'));
        assert_eq!(steps[21].decoded, Some(b'*'));
        assert_eq!(steps[22].decoded, Some(b'o'));
        assert_eq!(steps[23].decoded, Some(b'j'));
        assert_eq!(steps[24].decoded, Some(b'j'));
        assert_eq!(steps[25].decoded, Some(b'p'));
        assert_eq!(steps[26].decoded, Some(b'<'));
        assert_eq!(steps[27].decoded, Some(b'v'));
        let selected = steps[24].after.registers.data_pointer;
        let destination = steps[25]
            .memory_delta
            .data
            .ok_or_else(|| "classifier p must write data".to_owned())?;
        assert_eq!(destination.address, selected);
        assert_eq!(guest.memory_word(plan.pair.pair_high_address), Ok(0));
        assert_eq!(guest.input_consumed(), usize::from(!input.is_empty()));
        let expected = if input.is_empty() {
            62u8
        } else {
            53u8
        };
        assert_eq!(guest.output(), [expected], "input {input_word}");
        _ = observed.insert((expected, selected == 1));
    }
    assert_eq!(observed, BTreeSet::from([(53, false), (62, true)]));
    Ok(())
}

#[test]
#[expect(
    clippy::indexing_slicing,
    clippy::panic_in_result_fn,
    reason = "physical EOF classifier negative code and data-write controls"
)]
fn eof_data_classification_refuses_a_missing_selected_crazy_write()
-> Result<(), String> {
    let profile = current_profile();
    let plan = layout::build_guest_byte_c32_pair_eof_classify_source(profile)
        .map_err(|error| format!("{error:?}"))?;
    let mut without_classification = plan.pair.source.clone();
    // C25 must be a real data-write operation, not a dead no-op before output.
    without_classification[25] = encode(b'o', 25)?;
    let mut without_clear = plan.pair.source.clone();
    // C21 must really clear A from the adjacent high-zero store.
    without_clear[21] = encode(b'o', 21)?;
    for (input, expected) in [(vec![], 62u8), (vec![0], 53)] {
        let mut actual = ProfileMachine::from_source(
            profile,
            &plan.pair.source,
            input.clone(),
        )
        .map_err(|error| error.to_string())?;
        let mut missing_write = ProfileMachine::from_source(
            profile,
            &without_classification,
            input.clone(),
        )
        .map_err(|error| error.to_string())?;
        let mut missing_clear =
            ProfileMachine::from_source(profile, &without_clear, input)
                .map_err(|error| error.to_string())?;
        for guest in [&mut actual, &mut missing_write, &mut missing_clear] {
            assert_eq!(
                guest.run(28).map_err(|error| error.to_string())?,
                RunOutcome::Terminated {
                    reason: Termination::HaltInstruction,
                    steps: 28,
                }
            );
        }
        assert_eq!(actual.output(), [expected]);
        assert_ne!(missing_write.output(), actual.output());
        // EOF enters with A=0 already; the clear is necessary on bytes.
        if expected == 53 {
            assert_ne!(missing_clear.output(), actual.output());
        }
    }
    Ok(())
}

#[test]
#[expect(
    clippy::indexing_slicing,
    clippy::panic_in_result_fn,
    reason = "independent full-word physical EOF flag experiment"
)]
fn red_first_eof_data_path_produces_small_full_word_flag() -> Result<(), String>
{
    let profile = current_profile();
    let classifier =
        layout::build_guest_byte_c32_pair_eof_classify_source(profile)
            .map_err(|error| format!("{error:?}"))?;
    let mut source = classifier.pair.source.clone();
    // C25 p returns the same full word for every successful byte, but a
    // distinct one for EOF. The next genuine p uses the already-incremented
    // D, not the just-written cell. On bytes its loader operand is 36 or
    // 7,174,417; on EOF it reads the encrypted C2 word 51.
    for (site, operation) in [(26usize, b'p'), (27, b'<'), (28, b'v')] {
        source[site] = encode(operation, site)?;
    }
    let built = layout::build_guest_byte_c32_pair_eof_flag_source(profile)
        .map_err(|error| format!("{error:?}"))?;
    assert_eq!(built.pair.source, source);
    assert_eq!(built.flag_store_code_address, 26);
    assert_eq!(built.output_code_address, 27);
    assert_eq!(built.halt_code_address, 28);
    assert_eq!(
        layout::build_guest_byte_c32_pair_eof_flag_source(historical_profile()),
        Err(layout::ZeroCellSourceError::UnsupportedProfile),
    );
    let loaded = ProfileMachine::from_source(profile, &source, vec![])
        .map_err(|error| error.to_string())?;
    let mut observed = BTreeSet::new();
    for input_word in 0u32..=256 {
        let input = if input_word == 256 {
            vec![]
        } else {
            vec![u8::try_from(input_word).map_err(|error| error.to_string())?]
        };
        let mut guest = ProfileMachine::from_state(
            profile,
            loaded.memory().to_vec(),
            input.clone(),
            ProfileRegisters::default(),
        )
        .map_err(|error| error.to_string())?;
        let mut trace = Vec::new();
        assert_eq!(
            guest
                .run_traced(29, &mut |step| trace.push(*step))
                .map_err(|error| error.to_string())?,
            RunOutcome::Terminated {
                reason: Termination::HaltInstruction,
                steps: 29,
            },
        );
        assert_eq!(trace[25].decoded, Some(b'p'));
        let classified = if input.is_empty() {
            7_174_462
        } else {
            7_174_453
        };
        assert_eq!(trace[25].after.registers.accumulator, classified);
        assert_eq!(trace[26].decoded, Some(b'p'));
        assert_eq!(trace[27].decoded, Some(b'<'));
        assert_eq!(trace[28].decoded, Some(b'v'));
        let expected = if input.is_empty() {
            15
        } else {
            0
        };
        assert_eq!(trace[26].after.registers.accumulator, expected);
        let flag_address = trace[26].before.registers.data_pointer;
        assert_eq!(
            trace[26].memory_reads.data.map(|read| read.address),
            Some(flag_address),
        );
        assert_eq!(guest.memory_word(flag_address), Ok(expected));
        // An unchanged p write is correctly absent from the VM delta.
        if let Some(write) = trace[26].memory_delta.data {
            assert_eq!((write.address, write.after), (flag_address, expected));
        }
        assert_eq!(guest.output(), [u8::try_from(expected).unwrap_or(255)]);
        assert_eq!(guest.input_consumed(), usize::from(!input.is_empty()));
        assert_eq!(guest.memory_word(classifier.pair.pair_high_address), Ok(0));
        _ = observed.insert((input.is_empty(), expected));
    }
    assert_eq!(observed, BTreeSet::from([(false, 0), (true, 15)]));
    Ok(())
}

#[test]
#[expect(
    clippy::indexing_slicing,
    clippy::panic_in_result_fn,
    reason = "negative physical EOF flag mutation on actual N15 VM"
)]
fn eof_full_word_flag_refuses_a_missing_second_crazy_write()
-> Result<(), String> {
    let profile = current_profile();
    let original = layout::build_guest_byte_c32_pair_eof_flag_source(profile)
        .map_err(|error| format!("{error:?}"))?;
    let mut tampered = original.pair.source.clone();
    tampered[26] = encode(b'o', 26)?;
    for (input, expected, incorrect) in
        [(vec![], 15u8, 62u8), (vec![0], 0, 53), (vec![0xff], 0, 53)]
    {
        let mut valid = ProfileMachine::from_source(
            profile,
            &original.pair.source,
            input.clone(),
        )
        .map_err(|error| error.to_string())?;
        let mut invalid =
            ProfileMachine::from_source(profile, &tampered, input)
                .map_err(|error| error.to_string())?;
        for guest in [&mut valid, &mut invalid] {
            assert_eq!(
                guest.run(29).map_err(|error| error.to_string())?,
                RunOutcome::Terminated {
                    reason: Termination::HaltInstruction,
                    steps: 29,
                }
            );
        }
        assert_eq!(valid.output(), [expected]);
        assert_eq!(invalid.output(), [incorrect]);
        assert_ne!(valid.output(), invalid.output());
    }
    Ok(())
}

// The unchanged source-C23 checksum starts with a two-word zero and then its
// first getchar. This is a real guest *prefix* with matching code positions,
// not the missing signed conversion, SSA write or source-C EOF loop.
#[test]
#[expect(
    clippy::indexing_slicing,
    clippy::panic_in_result_fn,
    reason = "39 exact reached VM transitions on four binary/EOF input streams"
)]
fn physical_zero_pair_then_c37_getchar_has_genuine_input_and_data_effects()
-> Result<(), String> {
    let profile = current_profile();
    let baseline = layout::build_adjacent_c32_zero_source(profile)
        .map_err(|error| format!("{error:?}"))?;
    let plan = layout::build_adjacent_c32_zero_then_c37_input_source(profile)
        .map_err(|error| format!("{error:?}"))?;
    assert_eq!(plan.source.len(), 62);
    assert_eq!(plan.input_code_address, Some(37));
    assert_eq!(plan.zero_high_code_address, 14);
    assert_eq!(plan.zero_low_code_address, 17);
    for (site, opcode) in [(18usize, b'o'), (37, b'/'), (38, b'v')] {
        assert_eq!(plan.source[site], encode(opcode, site)?);
    }
    assert_eq!(plan.zero_high_address, baseline.zero_high_address);
    assert_eq!(plan.zero_low_address, baseline.zero_low_address);
    assert!(plan.source.iter().enumerate().all(|(site, byte)| {
        [18, 37, 38].contains(&site) || *byte == baseline.source[site]
    }));
    for input in [vec![], vec![0], vec![255], vec![1, 222]] {
        let mut guest =
            ProfileMachine::from_source(profile, &plan.source, input.clone())
                .map_err(|error| error.to_string())?;
        let mut trace = Vec::new();
        let result = guest
            .run_traced(39, &mut |step| trace.push(*step))
            .map_err(|error| error.to_string())?;
        assert_eq!(result, RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 39,
        });
        assert_eq!(trace.len(), 39);
        assert_eq!(trace[14].decoded, Some(b'p'));
        assert_eq!(trace[17].decoded, Some(b'p'));
        assert_eq!(trace[18].decoded, Some(b'o'));
        assert_eq!(trace[37].decoded, Some(b'/'));
        assert_eq!(trace[38].decoded, Some(b'v'));
        assert_eq!(
            trace[14]
                .memory_delta
                .data
                .map(|write| (write.address, write.after)),
            Some((plan.zero_high_address, 0))
        );
        assert_eq!(
            trace[17]
                .memory_delta
                .data
                .map(|write| (write.address, write.after)),
            Some((plan.zero_low_address, 0))
        );
        let expected = input
            .first()
            .map_or(malbolge::TraceInput::EndOfInput, |value| {
                malbolge::TraceInput::Byte(*value)
            });
        assert_eq!(trace[37].input, Some(expected));
        assert_eq!(guest.input_consumed(), usize::from(!input.is_empty()));
        assert_eq!(guest.memory_word(plan.zero_low_address), Ok(0));
        assert_eq!(guest.memory_word(plan.zero_high_address), Ok(0));
        assert!(guest.output().is_empty());
    }
    Ok(())
}

// The unchanged seven-block source-C checksum is the authority for the
// first two literal result cells and the first input opcode, not the N15
// builder's internal labels. This still does not link C23 result storage,
// the remaining operations, branches or its EOF loop.
#[test]
#[expect(
    clippy::cognitive_complexity,
    clippy::indexing_slicing,
    clippy::panic_in_result_fn,
    clippy::too_many_lines,
    reason = "finite original-C23 source/guest zero and input witness"
)]
fn original_checksum_first_literal_and_input_have_physical_guest_sites()
-> Result<(), String> {
    use std::str;

    use layout::typed_cfg_adapter::state_relocation::{
        GuestCodeEffectAnchor, GuestCodeFunctionEntryAnchor,
        GuestCodeFunctionEntryPlacement, GuestCodeInputSemantics,
        GuestCodeOperationAnchor, GuestCodeOperationEffect,
        plan_source_locked_cfg_with_function_entry_anchors,
    };

    const FROZEN: &str =
        include_str!("compiler/typed-ir/golden/mutable-eof-checksum.hex");
    let digits = FROZEN
        .trim_end()
        .strip_prefix("malbolge-typed-ir-v1:")
        .ok_or("missing original C23 checksum wire prefix")?;
    let (pairs, remainder) = digits.as_bytes().as_chunks::<2>();
    if !remainder.is_empty() {
        return Err("odd number of checksum wire hex digits".into());
    }
    let wire = pairs
        .iter()
        .map(|bytes| {
            let hex =
                str::from_utf8(bytes).map_err(|error| error.to_string())?;
            u8::from_str_radix(hex, 16).map_err(|error| error.to_string())
        })
        .collect::<Result<Vec<_>, _>>()?;

    let profile = current_profile();
    let guest = layout::build_adjacent_c32_zero_then_c37_input_source(profile)
        .map_err(|error| format!("real zero source: {error:?}"))?;
    let physical = ProfileMachine::from_source(profile, &guest.source, vec![])
        .map_err(|error| format!("source load: {error:?}"))?;
    let frame_base = guest.zero_low_address;
    let effects = [
        GuestCodeEffectAnchor {
            block: 0,
            code_address: guest.zero_low_code_address,
            effect_index: 0,
            function: 0,
            ordinal: 0,
        },
        GuestCodeEffectAnchor {
            block: 0,
            code_address: guest.zero_high_code_address,
            effect_index: 1,
            function: 0,
            ordinal: 0,
        },
    ];
    let entries = [GuestCodeFunctionEntryAnchor {
        block: 0,
        code_address: 0,
        function: 0,
    }];
    let input_anchor = GuestCodeOperationAnchor {
        block: 0,
        code_address: 37,
        function: 0,
        ordinal: 1,
    };
    let plan = plan_source_locked_cfg_with_function_entry_anchors(
        &GuestCodeFunctionEntryPlacement {
            canonical: &wire,
            control_anchors: &[],
            effect_anchors: &effects,
            frame_base,
            function_entries: &entries,
            operation_anchors: &[input_anchor],
            phi_anchors: &[],
            phi_entries: &[],
            phi_exits: &[],
            source_cells: 256,
        },
    )
    .map_err(|error| format!("checksum source placement: {error:?}"))?;
    let initializer = plan
        .operation_effect_sites
        .iter()
        .filter(|site| (site.function, site.block, site.ordinal) == (0, 0, 0))
        .collect::<Vec<_>>();
    assert_eq!(initializer.len(), 2);
    let inputs = plan
        .operation_effect_sites
        .iter()
        .filter(|site| (site.function, site.block, site.ordinal) == (0, 0, 1))
        .filter(|site| {
            matches!(site.effect, GuestCodeOperationEffect::Input { .. })
        })
        .collect::<Vec<_>>();
    let [input_effect] = inputs.as_slice() else {
        return Err("first source getchar has no unique input site".into());
    };
    assert_eq!(input_effect.code_address, 37);
    assert!(matches!(
        input_effect.effect,
        GuestCodeOperationEffect::Input {
            semantics: GuestCodeInputSemantics::SignedC23 { .. },
            ..
        }
    ));
    let input_stores = plan
        .operation_effect_sites
        .iter()
        .filter(|site| (site.function, site.block, site.ordinal) == (0, 0, 1))
        .filter(|site| {
            matches!(site.effect, GuestCodeOperationEffect::Store { .. })
        })
        .collect::<Vec<_>>();
    assert_eq!(
        input_stores.len(),
        2,
        "C23 requires two signed getchar words"
    );
    assert_eq!(plan.code_blocks[0].start, 0);
    assert_eq!(plan.operation_sites[0].start, guest.zero_high_code_address);
    assert_eq!(plan.relocated.state_placements[0].base, frame_base);

    // Replay the entire initially graphical source with the normative N15 VM.
    // Four stdin vectors exercise the source-anchored raw guest input site.
    for input in [vec![], vec![0], vec![255], vec![0x80, 0]] {
        let mut machine = ProfileMachine::from_state(
            profile,
            physical.memory().to_vec(),
            input.clone(),
            ProfileRegisters::default(),
        )
        .map_err(|error| format!("VM state: {error:?}"))?;
        let mut steps = Vec::new();
        assert_eq!(
            machine
                .run_traced(39, &mut |step| steps.push(*step))
                .map_err(|error| format!("VM replay: {error:?}"))?,
            RunOutcome::Terminated {
                reason: Termination::HaltInstruction,
                steps: 39,
            }
        );
        for effect in &initializer {
            let GuestCodeOperationEffect::Store {
                destination,
                literal: Some(0),
            } = effect.effect
            else {
                return Err(
                    "first C23 instruction is not a literal zero".into()
                );
            };
            let reached = steps
                .iter()
                .find(|step| {
                    step.before.registers.code_pointer == effect.code_address
                })
                .ok_or("source literal effect was not reached")?;
            assert_eq!(reached.decoded, Some(b'p'));
            assert_eq!(reached.before.registers.data_pointer, destination);
            assert_eq!(reached.after.registers.accumulator, 0);
            assert_eq!(
                reached
                    .memory_delta
                    .data
                    .map(|write| (write.address, write.after)),
                Some((destination, 0)),
                "source literal must be a committed physical memory write",
            );
            assert_ne!(
                reached.memory_delta.data.map(|write| write.before),
                Some(0),
                "source C32 initializer must replace a nonzero loader word",
            );
            assert_eq!(machine.memory_word(destination), Ok(0));
        }
        let read = steps
            .iter()
            .find(|step| {
                step.before.registers.code_pointer == input_effect.code_address
            })
            .ok_or("source first input site was skipped")?;
        assert_eq!(read.decoded, Some(b'/'));
        assert!(read.memory_delta.data.is_none());
        assert_eq!(
            read.input,
            Some(input.first().copied().map_or(
                malbolge::TraceInput::EndOfInput,
                malbolge::TraceInput::Byte,
            ))
        );
        assert_eq!(machine.input_consumed(), usize::from(!input.is_empty()));
        // Neither C38's physical halt nor the unvisited C39 can stand in
        // for the two required signed C23 result stores, even on EOF.
        for site in &input_stores {
            let GuestCodeOperationEffect::Store { destination, .. } =
                site.effect
            else {
                return Err("source getchar result is not a store".into());
            };
            assert!(!steps.iter().any(|step| {
                step.before.registers.code_pointer == site.code_address
                    && matches!(step.decoded, Some(b'p' | b'*'))
                    && step.before.registers.data_pointer == destination
            }));
        }
        assert_eq!(initializer[0].code_address, guest.zero_high_code_address);
        assert_eq!(initializer[1].code_address, guest.zero_low_code_address);
    }
    // A graphical no-op at the original C17 low-store site preserves source
    // admission and real termination but cannot implement the C23 literal.
    let mut broken_source = guest.source.clone();
    let last_store = usize::try_from(guest.zero_low_code_address)
        .map_err(|error| error.to_string())?;
    broken_source[last_store] = encode(b'o', last_store)?;
    let mut broken =
        ProfileMachine::from_source(profile, &broken_source, vec![])
            .map_err(|error| format!("mutant source load: {error:?}"))?;
    let mut broken_steps = Vec::new();
    assert_eq!(
        broken
            .run_traced(39, &mut |step| broken_steps.push(*step))
            .map_err(|error| format!("mutant guest replay: {error:?}"))?,
        RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 39,
        }
    );
    assert_eq!(broken_steps[last_store].decoded, Some(b'o'));
    assert_ne!(broken.memory_word(guest.zero_low_address), Ok(0));
    assert_eq!(broken.memory_word(guest.zero_high_address), Ok(0));
    // Replacing the authentic C37 '/' with a graphical no-op preserves the
    // earlier C32 initializer but can no longer discharge source getchar.
    let mut no_input = guest.source.clone();
    no_input[37] = encode(b'o', 37)?;
    let mut missing =
        ProfileMachine::from_source(profile, &no_input, vec![0xff])
            .map_err(|error| format!("missing-input source load: {error:?}"))?;
    let mut missing_steps = Vec::new();
    assert_eq!(
        missing
            .run_traced(39, &mut |step| missing_steps.push(*step))
            .map_err(|error| format!("missing input replay: {error:?}"))?,
        RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 39,
        }
    );
    assert_eq!(missing_steps[37].decoded, Some(b'o'));
    assert_eq!(missing_steps[37].input, None);
    assert_eq!(missing.input_consumed(), 0);
    assert_eq!(missing.memory_word(guest.zero_low_address), Ok(0));
    assert_eq!(missing.memory_word(guest.zero_high_address), Ok(0));
    Ok(())
}
