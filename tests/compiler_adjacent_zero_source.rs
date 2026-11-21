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

use std::fmt::Write as _;

use malbolge::{
    ProfileMachine, ProfileRegisters, RunOutcome, Termination, current_profile,
    decode_profile_instruction, historical_profile,
};

const CODE_CELLS: usize = 60;
const SOURCE_CELLS: usize = 62;
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
