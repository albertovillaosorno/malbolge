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

use std::collections::BTreeMap;

use malbolge::{
    ProfileMachine, ProfileStepTrace, RunOutcome, Termination, TraceInput,
    current_profile, decode_profile_instruction, encrypt_profile_cell,
    historical_profile, profile_crazy, profile_rotate,
};

use super::super::crazy as independent_crazy;
use super::super::layout::{
    DirtyPhiCopySites, RelocatedDirtyPhiSource, RelocatedFirstIterationSource,
    RelocatedSecondAddSource, RelocatedSecondEvenMaskSource,
    RelocatedSecondParityAddSource, ScratchResetSite, ZeroCellSourceError,
    build_relocated_dirty_phi_source, build_relocated_first_iteration_source,
    build_relocated_second_add_source, build_relocated_second_even_mask_source,
    build_relocated_second_parity_add_source,
};
use super::{at, check_transfer, check_write, word};

const ITERATION_BUDGET: usize = 700_000;
const SECOND_ADD_BUDGET: usize = 2_600_000;
const SECOND_PARITY_ADD_BUDGET: usize = 4_400_000;
const SECOND_MASK_BUDGET: usize = 3_400_000;

type MaskTraceBuffers<'trace> =
    (&'trace mut Vec<ProfileStepTrace>, &'trace mut ScratchReplay);
type MaskTraceSites<'sites> = (&'sites [u32], &'sites [u32]);

#[derive(Default)]
struct ScratchReplay {
    prior: BTreeMap<u32, u32>,
    resets: Vec<ProfileStepTrace>,
}

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

const fn dirty_sites(copy: DirtyPhiCopySites) -> [u32; 8] {
    let [t1, t2, t3] = copy.temporary_resets;
    let [d1, d2, d3] = copy.destination_resets;
    [
        t1,
        t2,
        t3,
        d1,
        d2,
        d3,
        copy.temporary_store,
        copy.destination_store,
    ]
}

#[expect(
    clippy::panic_in_result_fn,
    reason = "physical reset must read the exact dirty word and constants"
)]
fn check_dirty_reset(
    trace: &[ProfileStepTrace],
    sites: [u32; 3],
    address: u32,
    mut old: u32,
) -> Result<(), String> {
    for (site, accumulator) in sites.into_iter().zip([7_174_453, 14_348_906, 0])
    {
        let step = at(trace, site)?;
        assert_eq!(step.before.registers.accumulator, accumulator, "C{site} A");
        assert_eq!(
            step.memory_reads.data.ok_or("missing reset operand")?.value,
            old,
            "C{site} M{address} reset with A={accumulator}"
        );
        old = independent_crazy(old, accumulator);
        check_write(trace, site, address, old)?;
    }
    assert_eq!(old, 7_174_453, "reset must produce all-one trits");
    Ok(())
}

fn dirty_phi_source() -> Result<RelocatedDirtyPhiSource, String> {
    build_relocated_dirty_phi_source(current_profile())
        .map_err(|error| format!("dirty phi source: {error:?}"))
}

fn check_dirty_copy(
    guest: &RelocatedDirtyPhiSource,
    trace: &[ProfileStepTrace],
    copy: DirtyPhiCopySites,
    expected: [u32; 3],
) -> Result<(), String> {
    let [input, old_destination, old_temporary] = expected;
    check_dirty_reset(
        trace,
        copy.temporary_resets,
        guest.temporary_address,
        old_temporary,
    )?;
    check_dirty_reset(
        trace,
        copy.destination_resets,
        guest.destination_address,
        old_destination,
    )?;
    check_write(
        trace,
        copy.temporary_store,
        guest.temporary_address,
        independent_crazy(7_174_453, input),
    )?;
    check_write(
        trace,
        copy.destination_store,
        guest.destination_address,
        input,
    )
}

#[expect(
    clippy::panic_in_result_fn,
    reason = "final dirty state and preserved operands"
)]
fn check_dirty_result(
    guest: &RelocatedDirtyPhiSource,
    machine: &ProfileMachine,
    trace: &[ProfileStepTrace],
    input: (u8, u8),
) -> Result<(), String> {
    let (first_byte, second_byte) = input;
    let [first, second] = guest.copies;
    let checksum = u32::from(first_byte.wrapping_add(3));
    let current = u32::from(second_byte);
    let encoded_current = independent_crazy(7_174_453, current);
    check_dirty_copy(guest, trace, first, [
        current,
        checksum,
        encoded_current,
    ])?;
    check_dirty_copy(guest, trace, second, [
        checksum,
        current,
        encoded_current,
    ])?;
    assert_eq!(
        word(machine, guest.destination_address)?,
        checksum,
        "checksum must be restored"
    );
    assert_eq!(
        word(machine, guest.temporary_address)?,
        independent_crazy(7_174_453, checksum),
        "reused temporary must hold the second encoding"
    );
    for (address, expected) in
        guest.source_addresses.into_iter().zip([current, checksum])
    {
        assert_eq!(
            word(machine, address)?,
            expected,
            "M{address} source must survive both copies"
        );
    }
    for (address, expected) in guest
        .reset_constants
        .into_iter()
        .zip([7_174_453, 14_348_906, 0])
    {
        assert_eq!(
            word(machine, address)?,
            expected,
            "M{address} reset constant must survive both copies"
        );
    }
    Ok(())
}

#[expect(
    clippy::panic_in_result_fn,
    reason = "actual dirty phi effect sequence"
)]
fn check_dirty_vector(
    guest: &RelocatedDirtyPhiSource,
    initial: &ProfileMachine,
    first_byte: u8,
    second_byte: u8,
) -> Result<(), String> {
    let wanted = guest
        .copies
        .into_iter()
        .flat_map(dirty_sites)
        .collect::<Vec<_>>();
    let mut machine = initial
        .fork_with_input(vec![first_byte, second_byte, 42])
        .map_err(|error| error.to_string())?;
    let mut trace = Vec::new();
    let outcome = machine
        .run_traced(ITERATION_BUDGET, &mut |step| {
            if wanted.contains(&step.before.registers.code_pointer) {
                trace.push(*step);
            }
        })
        .map_err(|error| error.to_string())?;
    assert!(
        matches!(outcome, RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            ..
        }),
        "{outcome:?}"
    );
    assert_eq!(machine.input_consumed(), 2, "third byte must remain unread");
    assert!(
        machine.output().is_empty(),
        "incomplete second iteration must not output"
    );
    assert_eq!(
        trace
            .iter()
            .map(|step| step.before.registers.code_pointer)
            .collect::<Vec<_>>(),
        wanted,
        "all dirty effects must occur in order exactly once"
    );
    check_dirty_result(guest, &machine, &trace, (first_byte, second_byte))
}

#[expect(
    clippy::panic_in_result_fn,
    reason = "only the reserved second-byte code gap may differ"
)]
#[test]
fn relocated_dirty_phi_copy_restores_live_checksum() -> Result<(), String> {
    let guest = dirty_phi_source()?;
    let old = iteration_source()?;
    let new_source = &guest.iteration.addition.source;
    assert_eq!(
        new_source.len(),
        old.addition.source.len(),
        "source length must remain unchanged"
    );
    assert_eq!(
        new_source.get(..1_000_000),
        old.addition.source.get(..1_000_000),
        "prefix must remain byte-exact"
    );
    assert_eq!(
        new_source.get(1_010_000..),
        old.addition.source.get(1_010_000..),
        "EOF suffix and loader seed must remain byte-exact"
    );
    let initial =
        ProfileMachine::from_source(current_profile(), new_source, vec![])
            .map_err(|error| error.to_string())?;
    for (first_byte, second_byte) in
        [(0u8, 255u8), (255, 0), (253, 128), (1, 254), (80, 80)]
    {
        check_dirty_vector(&guest, &initial, first_byte, second_byte)?;
    }
    Ok(())
}

#[test]
fn relocated_dirty_phi_rejects_omitted_reset_and_store() -> Result<(), String> {
    let guest = dirty_phi_source()?;
    let [_, restoration] = guest.copies;
    let [_, _, reset] = restoration.destination_resets;
    for site in [reset, restoration.destination_store] {
        check_omitted_dirty_site(&guest, restoration, site)?;
    }
    Ok(())
}

#[expect(
    clippy::panic_in_result_fn,
    reason = "mutated physical dirty store"
)]
fn check_omitted_dirty_site(
    guest: &RelocatedDirtyPhiSource,
    restoration: DirtyPhiCopySites,
    site: u32,
) -> Result<(), String> {
    let mut mutated = guest.iteration.addition.source.clone();
    let noop = (33..=126u8)
        .find(|&cell| {
            decode_profile_instruction(u32::from(cell), site) == Some(b'o')
        })
        .ok_or("missing no-op")?;
    let position = usize::try_from(site).map_err(|error| error.to_string())?;
    *mutated.get_mut(position).ok_or("missing dirty store")? = noop;
    let mut machine =
        ProfileMachine::from_source(current_profile(), &mutated, vec![
            0, 255, 42,
        ])
        .map_err(|error| error.to_string())?;
    let mut trace = Vec::new();
    let outcome = machine
        .run_traced(700_000, &mut |step| {
            if dirty_sites(restoration)
                .contains(&step.before.registers.code_pointer)
            {
                trace.push(*step);
            }
        })
        .map_err(|error| error.to_string())?;
    assert!(
        matches!(outcome, RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            ..
        }),
        "omission must still halt"
    );
    assert_eq!(machine.input_consumed(), 2, "third byte must remain unread");
    assert!(
        machine.output().is_empty(),
        "negative control must not output"
    );
    // A reset omission may coincide with the correct final value.
    // Require the physical effect even in that case.
    if site == restoration.destination_store {
        assert_ne!(
            word(&machine, guest.destination_address)?,
            3,
            "omitted final store must corrupt checksum"
        );
    } else {
        assert_eq!(
            word(&machine, guest.destination_address)?,
            3,
            "reset omission deliberately preserves final checksum"
        );
    }
    let expected = if site == restoration.destination_store {
        3
    } else {
        7_174_453
    };
    assert!(
        check_write(&trace, site, guest.destination_address, expected).is_err(),
        "omitted physical effect must be rejected"
    );
    Ok(())
}

#[expect(
    clippy::panic_in_result_fn,
    reason = "earlier EOF paths must bypass every new dirty store"
)]
#[test]
fn relocated_dirty_phi_preserves_eof_paths() -> Result<(), String> {
    let guest = dirty_phi_source()?;
    let initial = ProfileMachine::from_source(
        current_profile(),
        &guest.iteration.addition.source,
        vec![],
    )
    .map_err(|error| error.to_string())?;
    check_first_eof(&guest.iteration, &initial)?;
    for byte in [0u8, 255] {
        check_iteration(&guest.iteration, &initial, byte, None)?;
    }
    let wanted = guest
        .copies
        .into_iter()
        .flat_map(dirty_sites)
        .collect::<Vec<_>>();
    for data in [vec![], vec![0], vec![255]] {
        let mut machine = initial
            .fork_with_input(data)
            .map_err(|error| error.to_string())?;
        let mut reached = false;
        let outcome = machine
            .run_traced(700_000, &mut |step| {
                reached |= wanted.contains(&step.before.registers.code_pointer);
            })
            .map_err(|error| error.to_string())?;
        assert!(matches!(outcome, RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            ..
        }));
        assert!(!reached, "EOF must bypass dirty storage continuation");
    }
    Ok(())
}

fn second_add_source() -> Result<RelocatedSecondAddSource, String> {
    build_relocated_second_add_source(current_profile())
        .map_err(|error| format!("second addition source: {error:?}"))
}

fn record_second_add(
    guest: &RelocatedSecondAddSource,
    wanted: &[u32],
    replay: &mut ScratchReplay,
    step: &ProfileStepTrace,
) {
    let code = step.before.registers.code_pointer;
    if wanted.get(replay.resets.len()) == Some(&code) {
        replay.resets.push(*step);
    }
    if code < 1_000_000
        && step.decoded == Some(b'p')
        && let Some(read) = step.memory_reads.data
        && guest
            .scratch_resets
            .binary_search_by_key(&read.address, |reset| reset.address)
            .is_ok()
    {
        let _: Option<u32> = replay
            .prior
            .insert(read.address, step.after.registers.accumulator);
    }
}

#[expect(
    clippy::panic_in_result_fn,
    reason = "ordered physical dirty scratch witness"
)]
fn check_scratch_replay(
    resets: &[ScratchResetSite],
    replay: &ScratchReplay,
) -> Result<(), String> {
    let count = resets.len();
    assert_eq!(
        replay.resets.len(),
        count.checked_mul(3).ok_or("reset count overflow")?,
        "all reset effects must be reached in order"
    );
    assert_eq!(
        replay.prior.len(),
        count,
        "all reused words must have been written by the first arithmetic pass"
    );
    assert!(
        replay.prior.values().any(|&value| value != 7_174_453),
        "the reused bank must be dirty"
    );
    for reset in resets {
        let old = *replay
            .prior
            .get(&reset.address)
            .ok_or("missing first-pass scratch store")?;
        check_dirty_reset(
            &replay.resets,
            reset.code_addresses,
            reset.address,
            old,
        )?;
    }
    Ok(())
}

#[expect(
    clippy::panic_in_result_fn,
    reason = "physical second addition witness"
)]
fn check_second_add(
    guest: &RelocatedSecondAddSource,
    initial: &ProfileMachine,
    first: u8,
    second: u8,
) -> Result<(), String> {
    let wanted = guest
        .scratch_resets
        .iter()
        .flat_map(|reset| reset.code_addresses)
        .collect::<Vec<_>>();
    let mut machine = initial
        .fork_with_input(vec![first, second, 42])
        .map_err(|error| error.to_string())?;
    let mut replay = ScratchReplay::default();
    let outcome = machine
        .run_traced(SECOND_ADD_BUDGET, &mut |step| {
            record_second_add(guest, &wanted, &mut replay, step);
        })
        .map_err(|error| error.to_string())?;
    assert!(
        matches!(outcome, RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            ..
        }),
        "{outcome:?}"
    );
    check_scratch_replay(&guest.scratch_resets, &replay)?;
    let checksum = u32::from(first.wrapping_add(3));
    let current = u32::from(second);
    assert_eq!(
        word(&machine, guest.sum_address)?,
        checksum.checked_add(current).ok_or("sum overflow")?,
        "second sum must retain the carry"
    );
    for (address, expected) in guest
        .iteration
        .phi_header_words
        .into_iter()
        .zip([current, 0, checksum, 0])
    {
        assert_eq!(
            word(&machine, address)?,
            expected,
            "header operand M{address} must survive"
        );
    }
    assert_eq!(machine.input_consumed(), 2, "third byte must remain unread");
    assert!(
        machine.output().is_empty(),
        "unfinished second iteration must not output"
    );
    Ok(())
}

#[test]
fn relocated_second_add_reuses_dirty_arithmetic_scratch() -> Result<(), String>
{
    let guest = second_add_source()?;
    if guest.scratch_resets.len() != 168 {
        return Err("six carry rounds must reuse 168 scratch words".into());
    }
    let initial = ProfileMachine::from_source(
        current_profile(),
        &guest.iteration.addition.source,
        vec![],
    )
    .map_err(|error| error.to_string())?;
    for (first, second) in
        [(0, 0), (252, 255), (253, 128), (255, 254), (80, 80)]
    {
        check_second_add(&guest, &initial, first, second)?;
    }
    Ok(())
}

#[expect(
    clippy::panic_in_result_fn,
    reason = "earlier EOF arms skip second arithmetic"
)]
#[test]
fn relocated_second_add_preserves_eof_paths() -> Result<(), String> {
    let guest = second_add_source()?;
    assert_eq!(
        build_relocated_second_add_source(historical_profile()),
        Err(ZeroCellSourceError::UnsupportedProfile)
    );
    let initial = ProfileMachine::from_source(
        current_profile(),
        &guest.iteration.addition.source,
        vec![],
    )
    .map_err(|error| error.to_string())?;
    let [reset, _, _] = guest
        .scratch_resets
        .first()
        .ok_or("missing scratch reset")?
        .code_addresses;
    for (input, expected) in
        [(vec![], 0), (vec![0], 3), (vec![252], 255), (vec![255], 2)]
    {
        let count = input.len();
        let mut machine = initial
            .fork_with_input(input)
            .map_err(|error| error.to_string())?;
        let mut reached = false;
        let outcome = machine
            .run_traced(SECOND_ADD_BUDGET, &mut |step| {
                reached |= step.before.registers.code_pointer == reset;
            })
            .map_err(|error| error.to_string())?;
        assert!(
            matches!(outcome, RunOutcome::Terminated {
                reason: Termination::HaltInstruction,
                ..
            }),
            "{outcome:?}"
        );
        assert!(!reached, "EOF must bypass reused arithmetic scratch");
        assert_eq!(machine.input_consumed(), count);
        assert_eq!(machine.output(), &[expected]);
    }
    Ok(())
}

#[expect(
    clippy::panic_in_result_fn,
    reason = "mutated arithmetic scratch reset"
)]
#[test]
fn relocated_second_add_rejects_omitted_scratch_reset() -> Result<(), String> {
    let guest = second_add_source()?;
    let first_reset = guest
        .scratch_resets
        .first()
        .ok_or("missing scratch reset")?;
    let [_, _, site] = first_reset.code_addresses;
    let mut mutated = guest.iteration.addition.source.clone();
    let noop = (33..=126u8)
        .find(|&cell| {
            decode_profile_instruction(u32::from(cell), site) == Some(b'o')
        })
        .ok_or("missing no-op")?;
    let position = usize::try_from(site).map_err(|error| error.to_string())?;
    *mutated.get_mut(position).ok_or("missing scratch store")? = noop;
    let mut machine =
        ProfileMachine::from_source(current_profile(), &mutated, vec![
            252, 254, 42,
        ])
        .map_err(|error| error.to_string())?;
    let wanted = guest
        .scratch_resets
        .iter()
        .flat_map(|reset| reset.code_addresses)
        .collect::<Vec<_>>();
    let mut replay = ScratchReplay::default();
    let outcome = machine
        .run_traced(SECOND_ADD_BUDGET, &mut |step| {
            record_second_add(&guest, &wanted, &mut replay, step);
        })
        .map_err(|error| error.to_string())?;
    assert!(
        matches!(outcome, RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            ..
        }),
        "{outcome:?}"
    );
    assert_eq!(machine.input_consumed(), 2);
    assert!(machine.output().is_empty());
    assert!(
        check_scratch_replay(&guest.scratch_resets, &replay).is_err(),
        "no-op reset must fail physical replay"
    );
    Ok(())
}

fn parity_add_source() -> Result<RelocatedSecondParityAddSource, String> {
    build_relocated_second_parity_add_source(current_profile())
        .map_err(|error| format!("second parity source: {error:?}"))
}

fn check_second_parity_route(
    guest: &RelocatedSecondParityAddSource,
    initial: &ProfileMachine,
    trace: &[ProfileStepTrace],
    second: u8,
) -> Result<(), String> {
    let pointer = 14_346_720u32
        .checked_add(u32::from(second))
        .ok_or("pointer overflow")?;
    let address = pointer.checked_add(1).ok_or("lookup overflow")?;
    let parity = u32::from(second & 1);
    check_write(
        trace,
        guest.pointer_store_code_address,
        guest.pointer_address,
        pointer,
    )?;
    let lookup = at(trace, guest.lookup_code_address)?;
    let read = lookup.memory_reads.data.ok_or("missing lookup read")?;
    let rotated = if parity == 0 {
        4_782_981
    } else {
        2_391_472
    };
    if lookup.decoded != Some(b'*')
        || read.address != address
        || read.value != word(initial, address)?
        || lookup.after.registers.accumulator != rotated
    {
        return Err(format!("invalid second virgin lookup for {second}"));
    }
    check_write(
        trace,
        guest.parity_store_code_address,
        guest.parity_address,
        parity,
    )
}

#[expect(
    clippy::panic_in_result_fn,
    reason = "exact parity-selected arithmetic and halt"
)]
fn check_second_parity_result(
    guest: &RelocatedSecondParityAddSource,
    machine: &ProfileMachine,
    trace: &[ProfileStepTrace],
    input: [u8; 2],
) -> Result<(), String> {
    let [first, second] = input;
    if second & 1 == 0 {
        check_transfer(
            trace,
            guest.branch_code_address,
            7_174_787,
            guest.even_entry,
        )?;
        assert!(
            at(trace, guest.odd_halt_code_address).is_err(),
            "even path must bypass odd halt"
        );
        let sum = u32::from(first.wrapping_add(3))
            .checked_add(u32::from(second))
            .ok_or("sum overflow")?;
        assert_eq!(
            word(machine, guest.addition.sum_address)?,
            sum,
            "actual even sum must match both committed operands"
        );
        assert_eq!(
            word(machine, guest.incremented_address)?,
            sum.checked_add(3).ok_or("increment overflow")?,
            "full incremented sum before masking"
        );
    } else {
        check_transfer(
            trace,
            guest.branch_code_address,
            7_174_797,
            guest.odd_halt_code_address,
        )?;
        assert!(
            at(
                trace,
                guest.addition.iteration.second_byte_halt_code_address
            )
            .is_err(),
            "odd path must bypass even halt"
        );
    }
    check_second_parity_preserved(guest, machine, input)
}

#[expect(
    clippy::panic_in_result_fn,
    reason = "second parity preserves first lookup and header operands"
)]
fn check_second_parity_preserved(
    guest: &RelocatedSecondParityAddSource,
    machine: &ProfileMachine,
    input: [u8; 2],
) -> Result<(), String> {
    let [first, second] = input;
    let first_lookup = 14_348_179u32
        .checked_add(u32::from(first))
        .ok_or("first pointer overflow")?;
    let expected = if first & 1 == 0 {
        4_782_981
    } else {
        2_391_472
    };
    assert_eq!(
        word(machine, first_lookup)?,
        expected,
        "second lookup must not rotate first lookup word again"
    );
    for (address, value) in guest
        .addition
        .iteration
        .phi_header_words
        .into_iter()
        .zip([u32::from(second), 0, u32::from(first.wrapping_add(3)), 0])
    {
        assert_eq!(
            word(machine, address)?,
            value,
            "committed operand must survive"
        );
    }
    Ok(())
}

#[expect(
    clippy::panic_in_result_fn,
    reason = "live parity and ordered reused arithmetic"
)]
fn check_second_parity_add(
    guest: &RelocatedSecondParityAddSource,
    initial: &ProfileMachine,
    first: u8,
    second: u8,
) -> Result<(), String> {
    let mut machine = initial
        .fork_with_input(vec![first, second, 42])
        .map_err(|error| error.to_string())?;
    let wanted = [
        guest.pointer_store_code_address,
        guest.lookup_code_address,
        guest.parity_store_code_address,
        guest.branch_code_address,
        guest.odd_halt_code_address,
        guest.addition.iteration.second_byte_halt_code_address,
    ];
    let reset_sites = guest
        .addition
        .scratch_resets
        .iter()
        .flat_map(|reset| reset.code_addresses)
        .collect::<Vec<_>>();
    let mut replay = ScratchReplay::default();
    let mut trace = Vec::new();
    let outcome = machine
        .run_traced(SECOND_PARITY_ADD_BUDGET, &mut |step| {
            if wanted.contains(&step.before.registers.code_pointer) {
                trace.push(*step);
            }
            record_second_add(&guest.addition, &reset_sites, &mut replay, step);
        })
        .map_err(|error| error.to_string())?;
    assert!(
        matches!(outcome, RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            ..
        }),
        "first={first} second={second} {outcome:?}"
    );
    check_second_parity_route(guest, initial, &trace, second)?;
    check_second_parity_result(guest, &machine, &trace, [first, second])?;
    if second & 1 == 0 {
        check_scratch_replay(&guest.addition.scratch_resets, &replay)?;
    } else {
        assert!(
            replay.resets.is_empty(),
            "odd arm must not reset even arithmetic scratch"
        );
    }
    assert_eq!(machine.input_consumed(), 2, "third byte must remain unread");
    assert!(
        machine.output().is_empty(),
        "unfinished paths must not output"
    );
    Ok(())
}

#[test]
fn relocated_second_parity_selects_actual_even_add() -> Result<(), String> {
    let guest = parity_add_source()?;
    if guest.addition.scratch_resets.len() != 336 {
        return Err("twelve carry rounds must reuse 336 scratch words".into());
    }
    let initial = ProfileMachine::from_source(
        current_profile(),
        &guest.addition.iteration.addition.source,
        vec![],
    )
    .map_err(|error| error.to_string())?;
    for (first, second) in
        [(0, 0), (0, 1), (1, 1), (252, 254), (255, 255), (253, 128)]
    {
        check_second_parity_add(&guest, &initial, first, second)?;
    }
    Ok(())
}

#[expect(
    clippy::panic_in_result_fn,
    reason = "earlier EOF bypasses both second parity arms"
)]
#[test]
fn relocated_second_parity_preserves_eof() -> Result<(), String> {
    let guest = parity_add_source()?;
    assert_eq!(
        build_relocated_second_parity_add_source(historical_profile()),
        Err(ZeroCellSourceError::UnsupportedProfile)
    );
    let initial = ProfileMachine::from_source(
        current_profile(),
        &guest.addition.iteration.addition.source,
        vec![],
    )
    .map_err(|error| error.to_string())?;
    for (input, expected) in [(vec![], 0), (vec![252], 255), (vec![255], 2)] {
        let count = input.len();
        let mut machine = initial
            .fork_with_input(input)
            .map_err(|error| error.to_string())?;
        let mut reached = false;
        let outcome = machine
            .run_traced(SECOND_PARITY_ADD_BUDGET, &mut |step| {
                reached |= step.before.registers.code_pointer
                    == guest.lookup_code_address;
            })
            .map_err(|error| error.to_string())?;
        assert!(
            matches!(outcome, RunOutcome::Terminated {
                reason: Termination::HaltInstruction,
                ..
            }),
            "{outcome:?}"
        );
        assert!(!reached, "EOF must bypass second parity lookup");
        assert_eq!(machine.input_consumed(), count);
        assert_eq!(machine.output(), &[expected]);
    }
    Ok(())
}

#[expect(
    clippy::panic_in_result_fn,
    reason = "second parity omitted-lookup negative control"
)]
#[test]
fn relocated_second_parity_rejects_omitted_lookup() -> Result<(), String> {
    let guest = parity_add_source()?;
    let mut source = guest.addition.iteration.addition.source.clone();
    let site = guest.lookup_code_address;
    let noop = (33..=126u8)
        .find(|&cell| {
            decode_profile_instruction(u32::from(cell), site) == Some(b'o')
        })
        .ok_or("missing no-op")?;
    let position = usize::try_from(site).map_err(|error| error.to_string())?;
    *source.get_mut(position).ok_or("missing lookup cell")? = noop;
    let initial =
        ProfileMachine::from_source(current_profile(), &source, vec![])
            .map_err(|error| error.to_string())?;
    let mut machine = initial
        .fork_with_input(vec![255, 255, 42])
        .map_err(|error| error.to_string())?;
    let mut trace = Vec::new();
    let outcome = machine
        .run_traced(SECOND_PARITY_ADD_BUDGET, &mut |step| {
            if [
                guest.pointer_store_code_address,
                guest.lookup_code_address,
                guest.parity_store_code_address,
            ]
            .contains(&step.before.registers.code_pointer)
            {
                trace.push(*step);
            }
        })
        .map_err(|error| error.to_string())?;
    assert_eq!(
        at(&trace, site)?.decoded,
        Some(b'o'),
        "negative control must reach the replaced lookup"
    );
    assert!(
        check_second_parity_route(&guest, &initial, &trace, 255).is_err(),
        "missing physical rotate must fail parity witness: {outcome:?}"
    );
    Ok(())
}

// Four crazy gates implement tritwise Boolean AND on 0/1 words.
fn boolean_word_and(left: u32, right: u32) -> u32 {
    independent_crazy(
        left,
        independent_crazy(
            independent_crazy(left, left),
            independent_crazy(right, 14_348_906),
        ),
    )
}

// On 0..=256 only, the one trits at positions 0, 1, 2, and 5
// identify 256: their place values already sum to 256. This avoids
// a second general carry circuit, but is not yet emitted guest code.
fn second_wrap_flag(value: u32) -> u32 {
    let matches_one = independent_crazy(0, independent_crazy(7_174_453, value));
    let mut aligned = matches_one;
    let mut conjunction = matches_one;
    for shift in 1u32..=5 {
        aligned = profile_rotate(aligned, 14_348_907);
        if matches!(shift, 1 | 2 | 5) {
            conjunction = boolean_word_and(conjunction, aligned);
        }
    }
    [1, 14_348_905, 14_348_905, 1]
        .into_iter()
        .fold(conjunction, |accumulator, data| {
            independent_crazy(data, accumulator)
        })
}

#[test]
fn second_wrap_flag_covers_exact_single_wrap_domain() {
    for value in 0..=256 {
        assert_eq!(
            second_wrap_flag(value),
            u32::from(value == 256),
            "exact N15 Boolean for once-wrapped {value}"
        );
    }
}

#[expect(
    clippy::panic_in_result_fn,
    reason = "exhaustive even-byte C arithmetic domain"
)]
#[test]
fn second_even_mask_needs_exactly_one_double_wrap_case() -> Result<(), String> {
    let mut double_wrap = Vec::new();
    for first in 0..=u8::MAX {
        for second in (0..=254u8).step_by(2) {
            let total = u32::from(first.wrapping_add(3))
                .checked_add(u32::from(second))
                .and_then(|sum| sum.checked_add(3))
                .ok_or("sum overflow")?;
            let once = if total >= 256 {
                total.checked_sub(256).ok_or("wrap underflow")?
            } else {
                total
            };
            let result = if second_wrap_flag(once) == 1 {
                double_wrap.push((first, second));
                0
            } else {
                once
            };
            assert_eq!(result, total & 255, "mask after {first}, {second}");
        }
    }
    assert_eq!(
        double_wrap,
        [(252, 254)],
        "one-subtraction mask fails only at the maximum even sum"
    );
    Ok(())
}

fn second_mask_source() -> Result<RelocatedSecondEvenMaskSource, String> {
    build_relocated_second_even_mask_source(current_profile())
        .map_err(|error| format!("second even mask source: {error:?}"))
}

#[expect(
    clippy::panic_in_result_fn,
    reason = "exact first and second wrap branches and dirty C32 stores"
)]
fn check_second_mask_result(
    guest: &RelocatedSecondEvenMaskSource,
    machine: &ProfileMachine,
    trace: &[ProfileStepTrace],
    input: [u8; 2],
) -> Result<(), String> {
    let [first, second] = input;
    let checksum = u32::from(first.wrapping_add(3));
    let sum = checksum
        .checked_add(u32::from(second))
        .and_then(|value| value.checked_add(3))
        .ok_or("second sum overflow")?;
    let residual = if sum >= 256 {
        sum.checked_sub(256).ok_or("wrap underflow")?
    } else {
        sum
    };
    let expected = sum & 255;
    let first_wrap = sum >= 256;
    let double_wrap = residual == 256;
    let [first_branch, double_branch] = guest.branch_code_addresses;
    let [first_flag, double_flag] = guest.flag_addresses;
    let [first_store, double_store] = guest.flag_store_code_addresses;
    check_write(trace, first_store, first_flag, u32::from(first_wrap))?;
    check_write(trace, double_store, double_flag, u32::from(double_wrap))?;
    let (first_ptr, first_entry) = if first_wrap {
        (7_174_811, 3_115_000)
    } else {
        (7_174_801, 3_100_000)
    };
    let (double_ptr, double_entry) = if double_wrap {
        (7_174_883, 3_215_000)
    } else {
        (7_174_873, 3_200_000)
    };
    check_transfer(trace, first_branch, first_ptr, first_entry)?;
    check_transfer(trace, double_branch, double_ptr, double_entry)?;
    assert_eq!(
        word(machine, guest.residual_address)?,
        residual,
        "once-wrap"
    );
    assert_eq!(
        word(machine, guest.parity.incremented_address)?,
        sum,
        "incremented input must survive reuse"
    );
    check_second_mask_stores(guest, machine, trace, [checksum, expected])?;
    check_second_parity_preserved(&guest.parity, machine, input)
}

#[expect(
    clippy::panic_in_result_fn,
    reason = "exact dirty result pair"
)]
fn check_second_mask_stores(
    guest: &RelocatedSecondEvenMaskSource,
    machine: &ProfileMachine,
    trace: &[ProfileStepTrace],
    values: [u32; 2],
) -> Result<(), String> {
    let [checksum, expected] = values;
    let [low, high] = guest.result_pair;
    let [low_copy, high_copy] = guest.result_copies;
    let temp = 7_174_633;
    check_dirty_reset(
        trace,
        low_copy.temporary_resets,
        temp,
        independent_crazy(7_174_453, checksum),
    )?;
    check_dirty_reset(trace, low_copy.destination_resets, low, checksum)?;
    check_write(
        trace,
        low_copy.temporary_store,
        temp,
        independent_crazy(7_174_453, expected),
    )?;
    check_write(trace, low_copy.destination_store, low, expected)?;
    check_dirty_reset(
        trace,
        high_copy.temporary_resets,
        temp,
        independent_crazy(7_174_453, expected),
    )?;
    check_dirty_reset(trace, high_copy.destination_resets, high, 0)?;
    check_write(trace, high_copy.temporary_store, temp, 7_174_453)?;
    check_write(trace, high_copy.destination_store, high, 0)?;
    assert_eq!(
        [word(machine, low)?, word(machine, high)?],
        [expected, 0],
        "canonical second checksum"
    );
    Ok(())
}

fn record_second_mask(
    guest: &RelocatedSecondEvenMaskSource,
    sites: MaskTraceSites<'_>,
    traces: MaskTraceBuffers<'_>,
    step: &ProfileStepTrace,
) {
    let (wanted, reset_sites) = sites;
    let (trace, replay) = traces;
    let code = step.before.registers.code_pointer;
    if wanted.contains(&code) {
        trace.push(*step);
    }
    if reset_sites.get(replay.resets.len()) == Some(&code) {
        replay.resets.push(*step);
    }
    if code >= guest.parity.even_entry
        && reset_sites.first().is_some_and(|&first| code < first)
        && matches!(step.decoded, Some(b'p' | b'*'))
        && let Some(read) = step.memory_reads.data
        && guest
            .scratch_resets
            .binary_search_by_key(&read.address, |reset| reset.address)
            .is_ok()
    {
        let _: Option<u32> = replay
            .prior
            .insert(read.address, step.after.registers.accumulator);
    }
}

fn second_mask_sites(guest: &RelocatedSecondEvenMaskSource) -> Vec<u32> {
    guest
        .branch_code_addresses
        .into_iter()
        .chain(guest.flag_store_code_addresses)
        .chain(guest.result_copies.into_iter().flat_map(dirty_sites))
        .collect()
}

#[expect(
    clippy::panic_in_result_fn,
    reason = "bounded live arithmetic and exact guest trace"
)]
fn check_second_mask_vector(
    guest: &RelocatedSecondEvenMaskSource,
    initial: &ProfileMachine,
    first: u8,
    second: u8,
) -> Result<(), String> {
    let mut machine = initial
        .fork_with_input(vec![first, second, 42])
        .map_err(|error| error.to_string())?;
    let mut wanted = second_mask_sites(guest);
    wanted.extend([
        guest.parity.pointer_store_code_address,
        guest.parity.lookup_code_address,
        guest.parity.parity_store_code_address,
        guest.parity.branch_code_address,
        guest
            .parity
            .addition
            .iteration
            .second_byte_halt_code_address,
    ]);
    let reset_sites = guest
        .scratch_resets
        .iter()
        .flat_map(|reset| reset.code_addresses)
        .collect::<Vec<_>>();
    let mut trace = Vec::new();
    let mut replay = ScratchReplay::default();
    let outcome = machine
        .run_traced(SECOND_MASK_BUDGET, &mut |step| {
            record_second_mask(
                guest,
                (&wanted, &reset_sites),
                (&mut trace, &mut replay),
                step,
            );
        })
        .map_err(|error| error.to_string())?;
    assert!(
        matches!(outcome, RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            ..
        }),
        "first={first} second={second} {outcome:?}"
    );
    check_second_parity_route(&guest.parity, initial, &trace, second)?;
    check_transfer(
        &trace,
        guest.parity.branch_code_address,
        7_174_787,
        guest.parity.even_entry,
    )?;
    check_scratch_replay(&guest.scratch_resets, &replay)?;
    check_second_mask_result(guest, &machine, &trace, [first, second])?;
    assert_eq!(machine.input_consumed(), 2, "third byte must remain unread");
    assert!(
        machine.output().is_empty(),
        "unfinished branch cannot output"
    );
    Ok(())
}

#[expect(
    clippy::panic_in_result_fn,
    reason = "freeze finite second-even physical mask geometry"
)]
#[test]
fn relocated_second_even_mask_boundaries() -> Result<(), String> {
    let guest = second_mask_source()?;
    assert_eq!(
        guest.parity.addition.iteration.addition.source.len(),
        3_380_208,
        "bounded geometry must preserve virgin bootstrap operands"
    );
    assert_eq!(
        guest.scratch_resets.len(),
        234,
        "seven carry rounds and four-trit predicate"
    );
    assert_eq!(
        build_relocated_second_even_mask_source(historical_profile()),
        Err(ZeroCellSourceError::UnsupportedProfile),
        "current N15 only"
    );
    let initial = ProfileMachine::from_source(
        current_profile(),
        &guest.parity.addition.iteration.addition.source,
        vec![],
    )
    .map_err(|error| error.to_string())?;
    for (first, second) in [
        (0, 0),
        (0, 248),
        (0, 250),
        (0, 252),
        (251, 254),
        (252, 254),
        (253, 0),
        (255, 254),
    ] {
        check_second_mask_vector(&guest, &initial, first, second)?;
    }
    Ok(())
}

#[expect(
    clippy::panic_in_result_fn,
    reason = "earlier EOF and odd branches must not execute even mask"
)]
#[test]
fn relocated_second_even_mask_preserves_bypass_paths() -> Result<(), String> {
    let guest = second_mask_source()?;
    let initial = ProfileMachine::from_source(
        current_profile(),
        &guest.parity.addition.iteration.addition.source,
        vec![],
    )
    .map_err(|error| error.to_string())?;
    let sites = second_mask_sites(&guest);
    for (input, expected) in [
        (vec![], vec![0]),
        (vec![252], vec![255]),
        (vec![255], vec![2]),
        (vec![0, 1, 42], vec![]),
        (vec![255, 255, 42], vec![]),
    ] {
        let read_count = input.len().min(2);
        let mut machine = initial
            .fork_with_input(input)
            .map_err(|error| error.to_string())?;
        let mut reached = false;
        let outcome = machine
            .run_traced(SECOND_MASK_BUDGET, &mut |step| {
                reached |= sites.contains(&step.before.registers.code_pointer);
            })
            .map_err(|error| error.to_string())?;
        assert!(
            matches!(outcome, RunOutcome::Terminated {
                reason: Termination::HaltInstruction,
                ..
            }),
            "{outcome:?}"
        );
        assert!(!reached, "earlier EOF/odd paths bypass even mask");
        assert_eq!(machine.input_consumed(), read_count, "exact input");
        assert_eq!(machine.output(), expected, "preserved output");
    }
    Ok(())
}

#[expect(
    clippy::panic_in_result_fn,
    reason = "physical flag and canonical store omission negatives"
)]
#[test]
fn relocated_second_even_mask_rejects_omitted_effects() -> Result<(), String> {
    let guest = second_mask_source()?;
    let sites = second_mask_sites(&guest);
    for site in [
        guest.flag_store_code_addresses[1],
        guest.result_copies[1].destination_store,
    ] {
        let mut source =
            guest.parity.addition.iteration.addition.source.clone();
        let noop = (33..=126u8)
            .find(|&byte| {
                decode_profile_instruction(u32::from(byte), site) == Some(b'o')
            })
            .ok_or("missing no-op")?;
        let position =
            usize::try_from(site).map_err(|error| error.to_string())?;
        *source.get_mut(position).ok_or("missing code cell")? = noop;
        let mut machine =
            ProfileMachine::from_source(current_profile(), &source, vec![
                252, 254, 42,
            ])
            .map_err(|error| error.to_string())?;
        let mut trace = Vec::new();
        let outcome = machine
            .run_traced(SECOND_MASK_BUDGET, &mut |step| {
                if sites.contains(&step.before.registers.code_pointer) {
                    trace.push(*step);
                }
            })
            .map_err(|error| error.to_string())?;
        assert_eq!(at(&trace, site)?.decoded, Some(b'o'), "mutation reached");
        assert!(
            check_second_mask_result(&guest, &machine, &trace, [252, 254])
                .is_err(),
            "omitted C{site} accepted: {outcome:?}"
        );
    }
    Ok(())
}
