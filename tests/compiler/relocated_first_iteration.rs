// Copyright:
//   - Copyright © 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - Apache-2.0
// Confidential:
//   - false
// License-File:
//   - LICENSE
// Boundary-Contract:
// - Owns:
//   - Normative replay of first-iteration mask and one phi edge.
// - Must-Not:
//   - Claim complete checksum lowering or source-frame admission.
// - Allows:
//   - Inputs: fixed graphical source and bounded input classes.
//   - Outputs: observed branch, writes, input and terminal output.
//   - Side effects: isolated normative VM execution.
// - Split-When:
//   - General continuation replay owns these controls.
// - Merge-When:
//   - A complete checksum witness subsumes the physical arms.
// - Summary:
//   - Authenticate arithmetic, second input and physical phi copies.

use malbolge::{
    ProfileMachine, ProfileStepTrace, RunOutcome, Termination, TraceInput,
    current_profile, decode_profile_instruction, encrypt_profile_cell,
    historical_profile, profile_crazy,
};

use super::super::layout::{
    RelocatedFirstIterationSource, ZeroCellSourceError,
    build_relocated_first_iteration_source,
};
use super::{at, check_transfer, check_write, word};

const ITERATION_BUDGET: usize = 700_000;

fn iteration_source() -> Result<RelocatedFirstIterationSource, String> {
    build_relocated_first_iteration_source(current_profile())
        .map_err(|error| format!("iteration source: {error:?}"))
}

fn record_iteration(
    guest: &RelocatedFirstIterationSource,
    step: &ProfileStepTrace,
) -> bool {
    let code = step.before.registers.code_pointer;
    step.input.is_some()
        || step.output.is_some()
        || [
            guest.mask_branch_code_address,
            guest.second_branch_code_address,
            guest.header_branch_code_address,
            guest.second_byte_halt_code_address,
            guest.addition.byte_halt_code_address,
            guest.addition.eof_halt_code_address,
            guest.second_eof_output_store_code_address,
        ]
        .contains(&code)
        || guest.mask_store_code_addresses.contains(&code)
        || guest.second_byte_store_code_addresses.contains(&code)
        || guest.second_eof_store_code_addresses.contains(&code)
        || guest.phi_transfer_code_addresses.contains(&code)
        || guest.phi_snapshot_code_addresses.contains(&code)
        || guest.phi_commit_code_addresses.contains(&code)
}

#[expect(
    clippy::panic_in_result_fn,
    reason = "exact physical edge order and word witnesses"
)]
fn check_iteration_edge(
    guest: &RelocatedFirstIterationSource,
    machine: &ProfileMachine,
    trace: &[ProfileStepTrace],
    expected: [u32; 4],
) -> Result<(), String> {
    for (sites, words) in [
        (guest.phi_snapshot_code_addresses, guest.phi_snapshot_words),
        (guest.phi_commit_code_addresses, guest.phi_header_words),
    ] {
        for ((site, address), value) in
            sites.into_iter().zip(words).zip(expected)
        {
            check_write(trace, site, address, value)?;
            assert_eq!(
                word(machine, address)?,
                value,
                "edge destination M{address} must retain its committed word"
            );
        }
    }
    let reached = trace
        .iter()
        .map(|step| step.before.registers.code_pointer)
        .filter(|code| {
            guest.phi_snapshot_code_addresses.contains(code)
                || guest.phi_commit_code_addresses.contains(code)
        })
        .collect::<Vec<_>>();
    assert_eq!(
        reached,
        guest
            .phi_snapshot_code_addresses
            .into_iter()
            .chain(guest.phi_commit_code_addresses)
            .collect::<Vec<_>>(),
        "snapshots must all precede the ordered commits"
    );
    Ok(())
}

#[expect(
    clippy::panic_in_result_fn,
    reason = "arithmetic and canonical word witnesses"
)]
fn check_mask(
    guest: &RelocatedFirstIterationSource,
    machine: &ProfileMachine,
    trace: &[ProfileStepTrace],
    first: u8,
) -> Result<(), String> {
    let sum = u32::from(first) + 3;
    let masked = sum & 255;
    let overflow = u32::from(sum >= 256);
    let addition = &guest.addition;
    let [raw_low, raw_high] = addition.input_pair;
    assert_eq!(
        [word(machine, raw_low)?, word(machine, raw_high)?],
        [u32::from(first), 0],
        "first byte must remain canonical"
    );
    for address in addition.zero_pair {
        assert_eq!(
            word(machine, address)?,
            0,
            "physical word M{address} must match the expected state"
        );
    }
    assert_eq!(
        word(machine, addition.sum_address)?,
        sum,
        "full sum must not be truncated"
    );
    assert_eq!(
        word(machine, guest.overflow_address)?,
        overflow,
        "overflow flag must distinguish 255 and 256"
    );
    assert_eq!(
        word(machine, guest.adjusted_address)?,
        sum.checked_add(473)
            .and_then(|value| value.checked_rem(729))
            .ok_or("offset overflow")?,
        "low six offset trits must match the wrapped candidate"
    );
    let (pointer, landing) = if overflow == 0 {
        (7_174_541, 850_000)
    } else {
        (7_174_551, 860_000)
    };
    check_transfer(trace, guest.mask_branch_code_address, pointer, landing)?;
    for (site, (address, value)) in guest
        .mask_store_code_addresses
        .into_iter()
        .zip(guest.masked_pair.into_iter().zip([masked, 0]))
    {
        check_write(trace, site, address, value)?;
        assert_eq!(
            word(machine, address)?,
            value,
            "physical word M{address} must match the expected state"
        );
    }
    Ok(())
}

#[expect(
    clippy::panic_in_result_fn,
    reason = "terminal continuation effects"
)]
fn check_finish(
    guest: &RelocatedFirstIterationSource,
    machine: &ProfileMachine,
    trace: &[ProfileStepTrace],
    input: (u8, Option<u8>),
) -> Result<(), String> {
    let (first, second) = input;
    let addition = &guest.addition;
    let masked = u32::from(first.wrapping_add(3));
    if second.is_some() {
        assert_eq!(
            machine.input_consumed(),
            2,
            "successful input consumption differs"
        );
        assert!(
            machine.output().is_empty(),
            "unfinished second byte must not emit output"
        );
        assert!(
            at(trace, guest.second_eof_output_code_address).is_err(),
            "byte continuation reached the EOF output"
        );
        assert!(
            at(trace, guest.second_byte_halt_code_address).is_ok(),
            "byte continuation did not reach its halt"
        );
    } else {
        assert_eq!(
            machine.input_consumed(),
            1,
            "successful input consumption differs"
        );
        assert_eq!(
            machine.output(),
            &[first.wrapping_add(3)],
            "EOF output must equal the committed checksum"
        );
        check_write(
            trace,
            guest.second_eof_output_store_code_address,
            7_174_455,
            masked,
        )?;
        assert_eq!(
            at(trace, guest.second_eof_output_code_address)?.output,
            Some(first.wrapping_add(3)),
            "missing physical checksum output"
        );
        assert!(
            at(trace, addition.byte_halt_code_address).is_ok(),
            "second EOF did not reach its halt"
        );
    }
    Ok(())
}

#[expect(
    clippy::panic_in_result_fn,
    clippy::too_many_lines,
    reason = "physical arithmetic, input and edge observations"
)]
fn check_iteration(
    guest: &RelocatedFirstIterationSource,
    initial: &ProfileMachine,
    first: u8,
    second: Option<u8>,
) -> Result<(), String> {
    let input =
        second.map_or_else(|| vec![first], |byte| vec![first, byte, 42]);
    let mut machine = initial
        .fork_with_input(input)
        .map_err(|error| error.to_string())?;
    let mut trace = Vec::new();
    let outcome = machine
        .run_traced(ITERATION_BUDGET, &mut |step| {
            if record_iteration(guest, step) {
                trace.push(*step);
            }
        })
        .map_err(|error| error.to_string())?;
    check_mask(guest, &machine, &trace, first)?;
    let masked = u32::from(first.wrapping_add(3));
    let overflow = u32::from(first >= 253);
    let addition = &guest.addition;
    let (
        expected_input,
        expected_words,
        sites,
        other,
        transfer,
        absent_transfer,
        branch_pointer,
        branch_landing,
        header_pointer,
        header_landing,
        steps,
    ) = second.map_or_else(
        || {
            let [absent, transfer] = guest.phi_transfer_code_addresses;
            (
                TraceInput::EndOfInput,
                [4_644_102, 299],
                guest.second_eof_store_code_addresses,
                guest.second_byte_store_code_addresses,
                transfer,
                absent,
                7_174_655,
                960_000,
                7_174_783,
                1_010_000,
                699_283usize,
            )
        },
        |byte| {
            let [transfer, absent] = guest.phi_transfer_code_addresses;
            (
                TraceInput::Byte(byte),
                [u32::from(byte), 0],
                guest.second_byte_store_code_addresses,
                guest.second_eof_store_code_addresses,
                transfer,
                absent,
                7_174_645,
                940_000,
                7_174_773,
                1_000_000,
                687_936,
            )
        },
    );
    assert_eq!(
        outcome,
        RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: if overflow == 0 {
                steps
            } else {
                steps.checked_sub(1224).ok_or("step count underflow")?
            }
        },
        "unexpected physical termination or step count"
    );
    let reads = trace
        .iter()
        .filter_map(|step| {
            step.input
                .map(|effect| (step.before.registers.code_pointer, effect))
        })
        .collect::<Vec<_>>();
    assert_eq!(
        reads,
        [
            (53, TraceInput::Byte(first)),
            (guest.second_input_code_address, expected_input)
        ],
        "guest must perform exactly the two expected input effects"
    );
    for ((site, address), value) in
        sites.into_iter().zip(guest.second_pair).zip(expected_words)
    {
        check_write(&trace, site, address, value)?;
        assert_eq!(
            word(&machine, address)?,
            value,
            "physical word M{address} must match the expected state"
        );
    }
    for site in other {
        assert!(
            at(&trace, site).is_err(),
            "unselected input normalization store C{site} executed"
        );
    }
    assert!(
        at(&trace, absent_transfer).is_err(),
        "unselected phi transfer executed"
    );
    check_transfer(
        &trace,
        guest.second_branch_code_address,
        branch_pointer,
        branch_landing,
    )?;
    check_transfer(&trace, transfer, 7_174_705, 900_000)?;
    check_iteration_edge(guest, &machine, &trace, [
        expected_words[0],
        expected_words[1],
        masked,
        0,
    ])?;
    check_transfer(
        &trace,
        guest.header_branch_code_address,
        header_pointer,
        header_landing,
    )?;
    check_finish(guest, &machine, &trace, (first, second))?;
    assert!(
        at(&trace, addition.eof_halt_code_address).is_err(),
        "nonempty input reached first EOF halt"
    );
    Ok(())
}

#[expect(
    clippy::panic_in_result_fn,
    reason = "first EOF and physical geometry"
)]
#[test]
fn relocated_first_iteration_boundaries() -> Result<(), String> {
    let guest = iteration_source()?;
    assert_eq!(
        guest.addition.source.len(),
        1_129_848,
        "source geometry changed"
    );
    assert_eq!(
        guest.addition.sum_address, 7_182_621,
        "arithmetic scratch address changed"
    );
    assert_eq!(
        guest.mask_branch_code_address, 780_229,
        "mask branch site changed"
    );
    assert_eq!(
        guest.mask_store_code_addresses,
        [870_505, 870_078],
        "mask store sites changed"
    );
    assert_eq!(
        guest.addition.byte_halt_code_address, 1_010_663,
        "second EOF halt moved"
    );
    assert_eq!(
        guest.addition.eof_halt_code_address, 1_111_281,
        "first EOF halt moved"
    );
    assert_eq!(
        build_relocated_first_iteration_source(historical_profile()),
        Err(ZeroCellSourceError::UnsupportedProfile),
        "unsupported historical profile must refuse"
    );
    let initial = ProfileMachine::from_source(
        current_profile(),
        &guest.addition.source,
        vec![],
    )
    .map_err(|error| error.to_string())?;
    for byte in [0u8, 1, 2, 8, 26, 242, 252, 253, 254, 255] {
        check_iteration(&guest, &initial, byte, None)?;
    }
    for (first, second) in [(0u8, 0u8), (255, 255), (253, 128), (1, 254)] {
        check_iteration(&guest, &initial, first, Some(second))?;
    }
    check_first_eof(&guest, &initial)
}

#[expect(
    clippy::panic_in_result_fn,
    reason = "first EOF must bypass second-input edge"
)]
fn check_first_eof(
    guest: &RelocatedFirstIterationSource,
    initial: &ProfileMachine,
) -> Result<(), String> {
    let mut machine = initial
        .fork_with_input(vec![])
        .map_err(|error| error.to_string())?;
    let mut trace = Vec::new();
    let outcome = machine
        .run_traced(ITERATION_BUDGET, &mut |step| {
            if record_iteration(guest, step) {
                trace.push(*step);
            }
        })
        .map_err(|error| error.to_string())?;
    assert_eq!(
        outcome,
        RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 100_749
        },
        "unexpected physical termination or step count"
    );
    assert_eq!(
        machine.output(),
        &[0],
        "EOF output must equal the committed checksum"
    );
    assert_eq!(
        machine.input_consumed(),
        0,
        "successful input consumption differs"
    );
    let [low, high] = guest.addition.input_pair;
    assert_eq!(
        [word(&machine, low)?, word(&machine, high)?],
        [4_644_102, 299],
        "first EOF must normalize to signed minus one"
    );
    assert!(
        at(&trace, guest.second_input_code_address).is_err(),
        "first EOF must not read again"
    );
    assert!(
        at(&trace, guest.header_branch_code_address).is_err(),
        "first EOF must not take the backedge"
    );
    Ok(())
}

#[expect(
    clippy::panic_in_result_fn,
    reason = "output parity cannot admit omitted edge stores"
)]
#[test]
fn relocated_first_iteration_omitted_phi_stores() -> Result<(), String> {
    let guest = iteration_source()?;
    let [_, _, _, snapshot] = guest.phi_snapshot_code_addresses;
    let [_, _, _, commit] = guest.phi_commit_code_addresses;
    for site in [snapshot, commit] {
        let mut mutated = guest.addition.source.clone();
        let noop = (33..=126u8)
            .find(|&cell| {
                decode_profile_instruction(u32::from(cell), site) == Some(b'o')
            })
            .ok_or("missing no-op")?;
        let position =
            usize::try_from(site).map_err(|error| error.to_string())?;
        *mutated.get_mut(position).ok_or("missing phi store")? = noop;
        let mut machine =
            ProfileMachine::from_source(current_profile(), &mutated, vec![1])
                .map_err(|error| error.to_string())?;
        let mut trace = Vec::new();
        let outcome = machine
            .run_traced(ITERATION_BUDGET, &mut |step| {
                if record_iteration(&guest, step) {
                    trace.push(*step);
                }
            })
            .map_err(|error| error.to_string())?;
        assert!(
            matches!(outcome, RunOutcome::Terminated {
                reason: Termination::HaltInstruction,
                ..
            }),
            "omission must reach the same return path"
        );
        assert_eq!(
            machine.output(),
            &[4],
            "omission is deliberately invisible to output parity"
        );
        assert!(
            check_iteration_edge(&guest, &machine, &trace, [
                4_644_102, 299, 4, 0
            ])
            .is_err(),
            "missing store C{site} must fail physical edge checks"
        );
    }
    Ok(())
}

#[expect(
    clippy::panic_in_result_fn,
    reason = "bounded full byte marginal census"
)]
fn check_census(
    guest: &RelocatedFirstIterationSource,
    initial: &ProfileMachine,
    first: u8,
    second: Option<u8>,
) -> Result<(), String> {
    let mut machine = initial
        .fork_with_input(
            second.map_or_else(|| vec![first], |byte| vec![first, byte, 42]),
        )
        .map_err(|error| error.to_string())?;
    let outcome = machine
        .run(ITERATION_BUDGET)
        .map_err(|error| error.to_string())?;
    assert!(
        matches!(outcome, RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            ..
        }),
        "byte census must reach a bounded halt"
    );
    let mask = first.wrapping_add(3);
    let [low, high] =
        second.map_or([4_644_102, 299], |byte| [u32::from(byte), 0]);
    for (address, value) in
        guest
            .phi_header_words
            .into_iter()
            .zip([low, high, u32::from(mask), 0])
    {
        assert_eq!(
            word(&machine, address)?,
            value,
            "census header mismatch at M{address}"
        );
    }
    if second.is_some() {
        assert_eq!(
            machine.input_consumed(),
            2,
            "third input must remain unread"
        );
        assert!(
            machine.output().is_empty(),
            "unfinished byte path must not output"
        );
    } else {
        assert_eq!(machine.input_consumed(), 1, "EOF is not a consumed byte");
        assert_eq!(
            machine.output(),
            &[mask],
            "first-iteration checksum differs"
        );
    }
    Ok(())
}

#[test]
#[ignore = "exhaustive bounded native VM census; run explicitly"]
fn relocated_first_iteration_first_byte_census() -> Result<(), String> {
    let guest = iteration_source()?;
    let initial = ProfileMachine::from_source(
        current_profile(),
        &guest.addition.source,
        vec![],
    )
    .map_err(|error| error.to_string())?;
    for byte in 0..=u8::MAX {
        check_census(&guest, &initial, byte, None)?;
    }
    Ok(())
}

#[test]
#[ignore = "exhaustive bounded native VM census; run explicitly"]
fn relocated_first_iteration_second_byte_census() -> Result<(), String> {
    let guest = iteration_source()?;
    let initial = ProfileMachine::from_source(
        current_profile(),
        &guest.addition.source,
        vec![],
    )
    .map_err(|error| error.to_string())?;
    // A fixed wrapping first input isolates the second-input marginal.
    for byte in 0..=u8::MAX {
        check_census(&guest, &initial, 255, Some(byte))?;
    }
    Ok(())
}

fn reset_to_ones(word: u32, ones: u32, twos: u32, trits: u8) -> u32 {
    [ones, twos, 0].into_iter().fold(word, |data, accumulator| {
        profile_crazy(data, accumulator, trits)
    })
}

// This checks the digitwise arithmetic prerequisite only; it does not
// execute a reset or a second visit to the physical header in the guest.
#[test]
fn reusable_copy_algebra_handles_dirty_destinations() {
    // The crazy operation acts independently at each ternary position.
    // Exhaust the old temporary, destination and source digit domains.
    for old_temp in 0..3 {
        for old_dest in 0..3 {
            for source in 0..3 {
                let temp = reset_to_ones(old_temp, 1, 2, 1);
                let dest = reset_to_ones(old_dest, 1, 2, 1);
                assert_eq!(temp, 1);
                assert_eq!(dest, 1);
                let encoded = profile_crazy(temp, source, 1);
                assert_eq!(profile_crazy(dest, encoded, 1), source);
            }
        }
    }
}

#[test]
fn reusable_copy_algebra_handles_n15_words() {
    // Check the N15 word-scale composition, including signed EOF words.
    let words = [0, 1, 255, 299, 4_644_102, 7_174_453, 14_348_906];
    for old_word in words {
        for source in words {
            let reset = reset_to_ones(old_word, 7_174_453, 14_348_906, 15);
            assert_eq!(reset, 7_174_453);
            let encoded = profile_crazy(reset, source, 15);
            assert_eq!(profile_crazy(reset, encoded, 15), source);
        }
    }
}

#[expect(
    clippy::panic_in_result_fn,
    reason = "exact one-shot code-cell encryption limitation"
)]
#[test]
fn existing_phi_store_code_requires_reentry_restoration() -> Result<(), String>
{
    let guest = iteration_source()?;
    let sites = guest
        .phi_snapshot_code_addresses
        .into_iter()
        .chain(guest.phi_commit_code_addresses);
    let mut changed = false;
    for site in sites {
        let index = usize::try_from(site).map_err(|error| error.to_string())?;
        let cell = u32::from(
            *guest
                .addition
                .source
                .get(index)
                .ok_or("missing code cell")?,
        );
        assert_eq!(decode_profile_instruction(cell, site), Some(b'p'));
        let encrypted =
            encrypt_profile_cell(cell).ok_or("missing encryption")?;
        changed |= decode_profile_instruction(encrypted, site) != Some(b'p');
    }
    assert!(
        changed,
        "direct header replay must not be presumed reusable"
    );
    Ok(())
}
