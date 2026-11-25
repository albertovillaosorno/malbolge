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
//   - Normative replay of one composed EOF and byte parity image.
// - Must-Not:
//   - Claim complete checksum lowering or source-frame admission.
// - Allows:
//   - Inputs: fixed graphical source and all first-input classes.
//   - Outputs: observed branch, writes, input and terminal output.
//   - Side effects: isolated normative VM execution.
// - Split-When:
//   - General continuation replay owns these controls.
// - Merge-When:
//   - A complete checksum witness subsumes the physical arms.
// - Summary:
//   - Authenticate mutually exclusive EOF and byte continuations.

#[path = "relocated_first_iteration.rs"]
mod relocated_first_iteration;

use malbolge::{
    ProfileMachine, ProfileStepTrace, RunOutcome, Termination, TraceInput,
    current_profile, decode_profile_instruction, historical_profile,
};

use super::layout::{
    RelocatedEofParitySource, ZeroCellSourceError,
    build_relocated_eof_parity_source,
};

const BUDGET: usize = 24_000;

fn source() -> Result<RelocatedEofParitySource, String> {
    build_relocated_eof_parity_source(current_profile())
        .map_err(|error| format!("composed source: {error:?}"))
}

fn word(machine: &ProfileMachine, address: u32) -> Result<u32, String> {
    machine
        .memory_word(address)
        .map_err(|error| error.to_string())
}

fn at(
    trace: &[ProfileStepTrace],
    code: u32,
) -> Result<&ProfileStepTrace, String> {
    trace
        .iter()
        .find(|step| step.before.registers.code_pointer == code)
        .ok_or_else(|| format!("missing C{code}"))
}

fn check_write(
    trace: &[ProfileStepTrace],
    code: u32,
    address: u32,
    value: u32,
) -> Result<(), String> {
    let step = at(trace, code)?;
    let read = step.memory_reads.data.ok_or("missing data read")?;
    let change = step
        .memory_delta
        .data
        .map(|write| (write.address, write.after));
    if step.decoded != Some(b'p')
        || read.address != address
        || step.after.registers.accumulator != value
        || change
            != if read.value == value {
                None
            } else {
                Some((address, value))
            }
    {
        return Err(format!("C{code} did not write M{address}={value}"));
    }
    Ok(())
}

fn check_transfer(
    trace: &[ProfileStepTrace],
    code: u32,
    pointer: u32,
    target: u32,
) -> Result<(), String> {
    let step = at(trace, code)?;
    if step.decoded != Some(b'i')
        || step.before.registers.data_pointer != pointer
        || step.after.registers.code_pointer != target
    {
        return Err(format!(
            "C{code} did not transfer through M{pointer} to C{target}"
        ));
    }
    Ok(())
}

#[expect(
    clippy::panic_in_result_fn,
    reason = "freeze composed physical geometry"
)]
#[test]
fn relocated_eof_parity_geometry() -> Result<(), String> {
    let guest = source()?;
    assert_eq!(guest.source.len(), 47_814);
    assert_eq!(guest.continuation_store_code_addresses, [19_581, 20_257]);
    assert_eq!(guest.eof_store_code_addresses, [46_089, 47_472]);
    assert_eq!(
        [
            guest.guard_selector_code_address,
            guest.guard_code_address,
            guest.lookup_code_address,
            guest.parity_store_code_address,
            guest.parity_selector_code_address,
            guest.parity_branch_code_address
        ],
        [20_265, 20_353, 32_840, 32_867, 32_929, 32_944]
    );
    assert_eq!(
        [
            guest.eof_output_store_code_address,
            guest.eof_output_code_address,
            guest.eof_halt_code_address
        ],
        [47_695, 47_696, 47_697]
    );
    assert_eq!(
        build_relocated_eof_parity_source(historical_profile()),
        Err(ZeroCellSourceError::UnsupportedProfile)
    );
    Ok(())
}

fn check_common(
    guest: &RelocatedEofParitySource,
    machine: &ProfileMachine,
    trace: &[ProfileStepTrace],
    expected: TraceInput,
) -> Result<(), String> {
    let reads = trace
        .iter()
        .filter_map(|step| {
            step.input
                .map(|input| (step.before.registers.code_pointer, input))
        })
        .collect::<Vec<_>>();
    if reads != [(guest.first_input_code_address, expected)] {
        return Err(format!("incorrect input trace: {reads:?}"));
    }
    for address in guest.zero_pair {
        if word(machine, address)? != 0 {
            return Err(format!(
                "checksum initializer M{address} was not preserved"
            ));
        }
    }
    let [byte_store, eof_store] = guest.continuation_store_code_addresses;
    let [byte_pointer, eof_pointer] = guest.continuation_addresses;
    check_write(trace, byte_store, byte_pointer, 29_999)?;
    check_write(trace, eof_store, eof_pointer, 44_999)?;
    Ok(())
}

#[expect(
    clippy::panic_in_result_fn,
    reason = "all byte classes and physical branch effects"
)]
#[test]
fn relocated_eof_parity_all_successful_bytes() -> Result<(), String> {
    let guest = source()?;
    let initial =
        ProfileMachine::from_source(current_profile(), &guest.source, vec![])
            .map_err(|error| error.to_string())?;
    for byte in 0..=u8::MAX {
        let mut machine = initial
            .fork_with_input(vec![byte, 128])
            .map_err(|error| error.to_string())?;
        let mut trace = Vec::new();
        let outcome = machine
            .run_traced(BUDGET, &mut |step| trace.push(*step))
            .map_err(|error| error.to_string())?;
        assert_eq!(outcome, RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 23_293
        });
        assert_eq!(machine.input_consumed(), 1);
        assert!(machine.output().is_empty());
        let [low, high] = guest.input_pair;
        assert_eq!([word(&machine, low)?, word(&machine, high)?], [
            u32::from(byte),
            0
        ]);
        check_common(&guest, &machine, &trace, TraceInput::Byte(byte))?;
        check_transfer(
            &trace,
            guest.guard_code_address,
            7_174_485,
            guest.byte_entry,
        )?;
        let parity = u32::from(byte & 1);
        check_write(
            &trace,
            guest.parity_store_code_address,
            guest.parity_address,
            parity,
        )?;
        let (pointer, halt) = if parity == 0 {
            (114, guest.even_halt_code_address)
        } else {
            (80, guest.odd_halt_code_address)
        };
        check_transfer(
            &trace,
            guest.parity_branch_code_address,
            pointer,
            halt,
        )?;
        assert_eq!(
            trace.last().map(|step| step.before.registers.code_pointer),
            Some(halt)
        );
        assert_eq!(at(&trace, guest.lookup_code_address)?.decoded, Some(b'*'));
        assert!(at(&trace, guest.eof_entry).is_err());
    }
    Ok(())
}

#[expect(
    clippy::panic_in_result_fn,
    reason = "canonical EOF stores and exclusive continuation"
)]
#[test]
fn relocated_eof_parity_true_eof() -> Result<(), String> {
    let guest = source()?;
    let mut machine =
        ProfileMachine::from_source(current_profile(), &guest.source, vec![])
            .map_err(|error| error.to_string())?;
    let mut trace = Vec::new();
    let outcome = machine
        .run_traced(BUDGET, &mut |step| trace.push(*step))
        .map_err(|error| error.to_string())?;
    assert_eq!(outcome, RunOutcome::Terminated {
        reason: Termination::HaltInstruction,
        steps: 23_045
    });
    assert_eq!(machine.input_consumed(), 0);
    assert_eq!(machine.output(), &[0]);
    let [low, high] = guest.input_pair;
    let [low_store, high_store] = guest.eof_store_code_addresses;
    assert_eq!([word(&machine, low)?, word(&machine, high)?], [
        4_644_102, 299
    ]);
    check_common(&guest, &machine, &trace, TraceInput::EndOfInput)?;
    check_transfer(
        &trace,
        guest.guard_code_address,
        7_174_535,
        guest.eof_entry,
    )?;
    check_write(&trace, low_store, low, 4_644_102)?;
    check_write(&trace, high_store, high, 299)?;
    check_write(
        &trace,
        guest.eof_output_store_code_address,
        guest.output_data_address,
        0,
    )?;
    assert_eq!(at(&trace, guest.eof_output_code_address)?.output, Some(0));
    assert!(at(&trace, guest.byte_entry).is_err());
    assert!(at(&trace, guest.parity_branch_code_address).is_err());
    Ok(())
}

#[expect(
    clippy::panic_in_result_fn,
    clippy::too_many_lines,
    reason = "opaque paired proof under explicit composed bounds"
)]
#[test]
fn relocated_eof_parity_composed_guard_proof() -> Result<(), String> {
    use super::layout::{
        AddressSelectedIndirectCase, AddressSelectedIndirectError,
        AddressSelectedIndirectProbe, SourcePhysicalTraceBudget,
        verify_address_selected_indirect_guest_with_budget,
    };
    let guest = source()?;
    let probe = AddressSelectedIndirectProbe {
        cases: [
            AddressSelectedIndirectCase {
                input: &[255, 128],
                landing_address: guest.byte_entry,
                pointer_cell: 7_174_485,
            },
            AddressSelectedIndirectCase {
                input: &[],
                landing_address: guest.eof_entry,
                pointer_cell: 7_174_535,
            },
        ],
        indirect_code_cell: guest.guard_code_address,
        input_code_cell: guest.first_input_code_address,
        selector_cell: guest.class_address,
        selector_code_cell: guest.guard_selector_code_address,
        selector_store_code_cell: guest.class_store_code_address,
        source: &guest.source,
        step_budget: BUDGET,
    };
    for budget in [
        SourcePhysicalTraceBudget::Short,
        SourcePhysicalTraceBudget::MarkerTape,
    ] {
        assert_eq!(
            verify_address_selected_indirect_guest_with_budget(
                current_profile(),
                probe,
                budget
            ),
            Err(AddressSelectedIndirectError::InvalidBound)
        );
    }
    let proof = verify_address_selected_indirect_guest_with_budget(
        current_profile(),
        probe,
        SourcePhysicalTraceBudget::ComposedMarkerTape,
    )
    .map_err(|error| format!("guard proof: {error:?}"))?;
    assert_eq!(
        proof.budget(),
        SourcePhysicalTraceBudget::ComposedMarkerTape
    );
    let [byte, eof] = proof.cases();
    assert_eq!(
        (byte.selector_write().after, eof.selector_write().after),
        (6_554_439, 13_108_878)
    );
    assert_eq!(
        (byte.transfer().value, eof.transfer().value),
        (29_999, 44_999)
    );
    let mut forged = probe;
    forged.cases[0].landing_address = guest.eof_entry;
    assert_eq!(
        verify_address_selected_indirect_guest_with_budget(
            current_profile(),
            forged,
            SourcePhysicalTraceBudget::ComposedMarkerTape,
        ),
        Err(AddressSelectedIndirectError::InvalidTransfer)
    );
    Ok(())
}

#[expect(
    clippy::panic_in_result_fn,
    reason = "paired parity proof on the composed image"
)]
#[test]
fn relocated_eof_parity_composed_parity_proof() -> Result<(), String> {
    use super::layout::{
        AddressSelectedIndirectCase, AddressSelectedIndirectProbe,
        SourcePhysicalTraceBudget,
        verify_address_selected_indirect_guest_with_budget,
    };
    let guest = source()?;
    let probe = AddressSelectedIndirectProbe {
        cases: [
            AddressSelectedIndirectCase {
                input: &[254, 128],
                landing_address: guest.even_halt_code_address,
                pointer_cell: 114,
            },
            AddressSelectedIndirectCase {
                input: &[255, 128],
                landing_address: guest.odd_halt_code_address,
                pointer_cell: 80,
            },
        ],
        indirect_code_cell: guest.parity_branch_code_address,
        input_code_cell: guest.first_input_code_address,
        selector_cell: guest.parity_address,
        selector_code_cell: guest.parity_selector_code_address,
        selector_store_code_cell: guest.parity_store_code_address,
        source: &guest.source,
        step_budget: BUDGET,
    };
    let proof = verify_address_selected_indirect_guest_with_budget(
        current_profile(),
        probe,
        SourcePhysicalTraceBudget::ComposedMarkerTape,
    )
    .map_err(|error| format!("parity proof: {error:?}"))?;
    assert_eq!(
        proof.budget(),
        SourcePhysicalTraceBudget::ComposedMarkerTape
    );
    let [even, odd] = proof.cases();
    assert_eq!(
        (even.selector_write().after, odd.selector_write().after),
        (0, 1)
    );
    assert_eq!((even.transfer().value, odd.transfer().value), (123, 118));
    Ok(())
}

#[expect(
    clippy::panic_in_result_fn,
    reason = "matching output cannot hide omitted canonical stores"
)]
#[test]
fn relocated_eof_parity_omitted_signed_stores() -> Result<(), String> {
    let guest = source()?;
    for site in guest.eof_store_code_addresses {
        let mut mutated = guest.source.clone();
        let noop = (33..=126u8)
            .find(|&cell| {
                decode_profile_instruction(u32::from(cell), site) == Some(b'o')
            })
            .ok_or("missing no-op")?;
        let position =
            usize::try_from(site).map_err(|error| error.to_string())?;
        *mutated.get_mut(position).ok_or("missing store")? = noop;
        let mut machine =
            ProfileMachine::from_source(current_profile(), &mutated, vec![])
                .map_err(|error| error.to_string())?;
        let outcome = machine
            .run_traced(BUDGET, &mut |_step| {})
            .map_err(|error| error.to_string())?;
        assert_eq!(outcome, RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 23_045
        });
        assert_eq!(machine.output(), &[0]);
        let [low, high] = guest.input_pair;
        assert_ne!([word(&machine, low)?, word(&machine, high)?], [
            4_644_102, 299
        ]);
    }
    Ok(())
}

#[expect(
    clippy::panic_in_result_fn,
    clippy::cognitive_complexity,
    clippy::too_many_lines,
    reason = "physical arithmetic and branch boundary assertions"
)]
#[test]
fn relocated_first_byte_add_boundaries() -> Result<(), String> {
    let guest =
        super::layout::build_relocated_first_byte_add_source(current_profile())
            .map_err(|error| format!("{error:?}"))?;
    assert_eq!(guest.source.len(), 355_194);
    assert_eq!(guest.sum_address, 7_177_621);
    assert_eq!(guest.arm_store_code_addresses, [80_263, 82_263]);
    assert_eq!(guest.parity_branch_code_address, 62_477);
    assert_eq!(guest.byte_halt_code_address, 199_481);
    assert_eq!(guest.eof_halt_code_address, 354_977);
    let initial =
        ProfileMachine::from_source(current_profile(), &guest.source, vec![])
            .map_err(|error| error.to_string())?;
    let [low, high] = guest.input_pair;
    for byte in [0u8, 1, 2, 8, 26, 242, 253, 254, 255] {
        let mut machine = initial
            .fork_with_input(vec![byte, 128])
            .map_err(|error| error.to_string())?;
        let mut trace = Vec::new();
        let outcome = machine
            .run_traced(166_000, &mut |step| {
                if [
                    guest.parity_branch_code_address,
                    guest.byte_halt_code_address,
                    guest.eof_halt_code_address,
                ]
                .contains(&step.before.registers.code_pointer)
                    || guest
                        .arm_store_code_addresses
                        .contains(&step.before.registers.code_pointer)
                {
                    trace.push(*step);
                }
            })
            .map_err(|error| error.to_string())?;
        assert_eq!(outcome, RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 165_467
        });
        assert_eq!(machine.input_consumed(), 1);
        assert_eq!(machine.output(), &[byte.wrapping_add(3)]);
        assert_eq!(word(&machine, guest.sum_address)?, u32::from(byte) + 3);
        assert_eq!(word(&machine, low)?, u32::from(byte));
        assert_eq!(word(&machine, high)?, 0);
        assert_eq!(word(&machine, guest.merged_address)?, u32::from(byte));
        let (pointer, target, selected, other) = if byte & 1 == 0 {
            (7_174_501, 80_000, 80_263, 82_263)
        } else {
            (7_174_511, 82_000, 82_263, 80_263)
        };
        check_transfer(
            &trace,
            guest.parity_branch_code_address,
            pointer,
            target,
        )?;
        check_write(&trace, selected, guest.merged_address, u32::from(byte))?;
        assert!(at(&trace, other).is_err());
        assert!(at(&trace, guest.eof_halt_code_address).is_err());
        for address in guest.zero_pair {
            assert_eq!(word(&machine, address)?, 0);
        }
    }
    let mut machine = initial
        .fork_with_input(vec![])
        .map_err(|error| error.to_string())?;
    let outcome = machine
        .run_traced(166_000, &mut |_| {})
        .map_err(|error| error.to_string())?;
    assert_eq!(outcome, RunOutcome::Terminated {
        reason: Termination::HaltInstruction,
        steps: 43_121
    });
    assert_eq!(machine.output(), &[0]);
    assert_eq!(machine.input_consumed(), 0);
    assert_eq!([word(&machine, low)?, word(&machine, high)?], [
        4_644_102, 299
    ]);
    Ok(())
}
