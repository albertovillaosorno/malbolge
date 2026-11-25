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
//   - Normative VM replay of guarded byte parity.
// - Must-Not:
//   - Claim a linked checksum or source-frame authorization.
// - Allows:
//   - Inputs: graphical source and finite binary controls.
//   - Outputs: observed parity, pointer selection, input and halt.
//   - Side effects: isolated normative VM execution.
// - Split-When:
//   - General physical predicate replay replaces this probe.
// - Merge-When:
//   - A complete checksum witness subsumes these controls.
// - Summary:
//   - Check all byte classes and exclude EOF before the tape.

//! Normative replay of the live byte predicate.

use malbolge::{
    ProfileMachine, ProfileStepTrace, RunOutcome, Termination, TraceInput,
    current_profile, historical_profile,
};

use super::layout::{
    RelocatedLiveParityBranchSource, RelocatedLiveParitySource,
    ZeroCellSourceError, build_relocated_live_parity_branch_source,
    build_relocated_live_parity_source,
};

fn source() -> Result<RelocatedLiveParitySource, String> {
    build_relocated_live_parity_source(current_profile())
        .map_err(|error| format!("parity source: {error:?}"))
}

fn word(machine: &ProfileMachine, address: u32) -> Result<u32, String> {
    machine
        .memory_word(address)
        .map_err(|error| error.to_string())
}

fn check_route(
    trace: &[ProfileStepTrace],
    guest: &RelocatedLiveParitySource,
    byte: u8,
) -> Result<(), String> {
    let at = |code| {
        trace
            .iter()
            .find(|step| step.before.registers.code_pointer == code)
            .ok_or_else(|| format!("missing C{code}"))
    };
    let pointer = 14_348_178u32
        .checked_add(u32::from(byte))
        .ok_or("pointer overflow")?;
    let lookup_address = pointer.checked_add(1).ok_or("lookup overflow")?;
    let store = at(guest.pointer_store_code_address)?;
    let jump = at(guest.pointer_jump_code_address)?;
    let lookup = at(guest.lookup_code_address)?;
    let parity = at(guest.parity_store_code_address)?;
    let expected = u32::from(byte & 1);
    if store.decoded != Some(b'p')
        || store.before.registers.data_pointer != guest.pointer_address
        || store.after.registers.accumulator != pointer
        || jump.decoded != Some(b'j')
        || jump.after.registers.data_pointer != lookup_address
        || lookup.decoded != Some(b'*')
        || lookup.before.registers.data_pointer != lookup_address
        || lookup.after.registers.accumulator
            != if expected == 0 {
                4_782_981
            } else {
                2_391_472
            }
        || parity.decoded != Some(b'p')
        || parity.before.registers.data_pointer != guest.parity_address
        || parity.after.registers.accumulator != expected
    {
        return Err(format!("invalid physical parity route for byte {byte}"));
    }
    Ok(())
}

#[expect(
    clippy::panic_in_result_fn,
    reason = "freeze physical geometry and unsupported profile rejection"
)]
#[test]
fn relocated_live_parity_geometry() -> Result<(), String> {
    let guest = source()?;
    assert_eq!(guest.source.len(), 5_796);
    assert_eq!(guest.input_pair, [7_174_419, 7_174_420]);
    assert_eq!(
        [
            guest.first_input_code_address,
            guest.branch_code_address,
            guest.eof_halt_code_address,
            guest.byte_arm_code_address
        ],
        [53, 118, 120, 126]
    );
    assert_eq!(
        [
            guest.pointer_store_code_address,
            guest.pointer_jump_code_address,
            guest.lookup_code_address,
            guest.parity_store_code_address,
            guest.output_code_address,
            guest.byte_halt_code_address
        ],
        [5_501, 5_555, 5_556, 5_582, 5_583, 5_584]
    );
    assert_eq!(
        build_relocated_live_parity_source(historical_profile()),
        Err(ZeroCellSourceError::UnsupportedProfile)
    );
    Ok(())
}

#[expect(
    clippy::panic_in_result_fn,
    clippy::cognitive_complexity,
    reason = "exhaustively authenticate actual byte parity and EOF exclusion"
)]
#[test]
fn relocated_live_parity_all_bytes_and_true_eof() -> Result<(), String> {
    let guest = source()?;
    let mut initial =
        ProfileMachine::from_source(current_profile(), &guest.source, vec![])
            .map_err(|error| error.to_string())?;
    for byte in 0..=u8::MAX {
        let mut machine = initial
            .fork_with_input(vec![byte, 0x80])
            .map_err(|error| error.to_string())?;
        let mut trace = Vec::new();
        let outcome = machine
            .run_traced(5_700, &mut |step| trace.push(*step))
            .map_err(|error| error.to_string())?;
        assert_eq!(outcome, RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 5_578
        });
        assert_eq!(machine.input_consumed(), 1);
        assert_eq!(machine.output(), &[byte & 1]);
        let [low, high] = guest.input_pair;
        assert_eq!(word(&machine, low)?, u32::from(byte));
        assert_eq!(word(&machine, high)?, 0);
        assert_eq!(word(&machine, guest.parity_address)?, u32::from(byte & 1));
        assert_eq!(
            word(&machine, guest.pointer_address)?,
            14_348_178 + u32::from(byte)
        );
        check_route(&trace, &guest, byte)?;
    }
    let mut trace = Vec::new();
    let outcome = initial
        .run_traced(5_700, &mut |step| trace.push(*step))
        .map_err(|error| error.to_string())?;
    assert_eq!(outcome, RunOutcome::Terminated {
        reason: Termination::HaltInstruction,
        steps: 120
    });
    assert_eq!(initial.input_consumed(), 0);
    assert!(initial.output().is_empty());
    assert_eq!(word(&initial, guest.parity_address)?, 37);
    assert!(
        trace
            .iter()
            .any(|step| step.input == Some(TraceInput::EndOfInput))
    );
    assert!(!trace.iter().any(|step| step.before.registers.code_pointer
        == guest.byte_arm_code_address));
    Ok(())
}

#[expect(
    clippy::panic_in_result_fn,
    reason = "check opaque paired proof and exact predicate scratch"
)]
#[test]
fn relocated_live_parity_extended_branch_proof() -> Result<(), String> {
    use super::layout::{
        AddressSelectedIndirectCase, AddressSelectedIndirectProbe,
        SourcePhysicalTraceBudget,
        verify_address_selected_indirect_guest_with_budget,
    };
    let guest = source()?;
    let probe = AddressSelectedIndirectProbe {
        cases: [
            AddressSelectedIndirectCase {
                input: &[255, 128],
                landing_address: 126,
                pointer_cell: 48,
            },
            AddressSelectedIndirectCase {
                input: &[],
                landing_address: 120,
                pointer_cell: 117,
            },
        ],
        indirect_code_cell: 118,
        input_code_cell: 53,
        selector_cell: 7_174_423,
        selector_code_cell: 107,
        selector_store_code_cell: 99,
        source: &guest.source,
        step_budget: 5_700,
    };
    let proof = verify_address_selected_indirect_guest_with_budget(
        current_profile(),
        probe,
        SourcePhysicalTraceBudget::MarkerTape,
    )
    .map_err(|error| format!("parity proof: {error:?}"))?;
    let [byte, eof] = proof.cases();
    let parity = byte
        .journal()
        .expanded
        .iter()
        .find(|cell| cell.site == guest.parity_address)
        .ok_or("missing physical parity scratch")?;
    assert_eq!(parity.final_word, 1);
    assert!(
        !eof.journal()
            .expanded
            .iter()
            .any(|cell| cell.site == guest.parity_address)
    );
    Ok(())
}

#[expect(
    clippy::panic_in_result_fn,
    reason = "omitting the dynamic lookup cannot establish parity"
)]
#[test]
fn relocated_live_parity_omitted_lookup_fails() -> Result<(), String> {
    use malbolge::decode_profile_instruction;
    let mut guest = source()?;
    let site = guest.lookup_code_address;
    let noop = (33..=126u8)
        .find(|&cell| {
            decode_profile_instruction(u32::from(cell), site) == Some(b'o')
        })
        .ok_or("missing graphical no-op")?;
    *guest
        .source
        .get_mut(usize::try_from(site).map_err(|error| error.to_string())?)
        .ok_or("missing lookup site")? = noop;
    let mut machine =
        ProfileMachine::from_source(current_profile(), &guest.source, vec![1])
            .map_err(|error| error.to_string())?;
    let mut trace = Vec::new();
    let _outcome = machine
        .run_traced(5_700, &mut |step| trace.push(*step))
        .map_err(|error| error.to_string())?;
    assert!(check_route(&trace, &guest, 1).is_err());
    // This counterfeit still emits the expected byte; physical replay
    // distinguishes it from the real loader-word lookup.
    assert_eq!(machine.output(), &[1]);
    Ok(())
}

fn branch_source() -> Result<RelocatedLiveParityBranchSource, String> {
    build_relocated_live_parity_branch_source(current_profile())
        .map_err(|error| format!("parity branch: {error:?}"))
}

fn check_branch_trace(
    trace: &[ProfileStepTrace],
    guest: &RelocatedLiveParityBranchSource,
    machine: &ProfileMachine,
    byte: u8,
) -> Result<(), String> {
    let bit = u32::from(byte & 1);
    let (pointer, landing) = if bit == 0 {
        (20, guest.even_halt_code_address)
    } else {
        (80, guest.odd_halt_code_address)
    };
    let at = |code| {
        trace
            .iter()
            .find(|step| step.before.registers.code_pointer == code)
            .ok_or_else(|| format!("missing C{code}"))
    };
    let transfer = at(guest.branch_code_address)?;
    let selector = at(guest.selector_code_address)?;
    let [low, high] = guest.input_pair;
    if (
        transfer.decoded,
        transfer.before.registers.data_pointer,
        transfer.after.registers.code_pointer,
        trace
            .last()
            .map(|step| (step.before.registers.code_pointer, step.decoded)),
    ) != (Some(b'i'), pointer, landing, Some((landing, Some(b'v'))))
        || (
            selector.decoded,
            selector.before.registers.data_pointer,
            selector.after.registers.data_pointer,
        ) != (Some(b'j'), guest.parity_address, bit + 1)
        || (
            word(machine, low)?,
            word(machine, high)?,
            word(machine, guest.parity_address)?,
        ) != (u32::from(byte), 0, bit)
    {
        return Err(format!("wrong physical parity route for {byte}"));
    }
    Ok(())
}

#[expect(
    clippy::panic_in_result_fn,
    clippy::cognitive_complexity,
    reason = "freeze exhaustive physical parity-transfer evidence"
)]
#[test]
fn relocated_live_parity_selects_real_code_for_all_bytes() -> Result<(), String>
{
    let guest = branch_source()?;
    assert_eq!(guest.source.len(), 5_796);
    assert_eq!(
        [
            guest.guard_code_address,
            guest.parity_store_code_address,
            guest.selector_code_address,
            guest.branch_code_address,
            guest.even_halt_code_address,
            guest.odd_halt_code_address,
            guest.eof_halt_code_address
        ],
        [118, 5_582, 5_644, 5_686, 124, 119, 120]
    );
    let mut initial =
        ProfileMachine::from_source(current_profile(), &guest.source, vec![])
            .map_err(|error| error.to_string())?;
    for byte in 0..=u8::MAX {
        let mut machine = initial
            .fork_with_input(vec![byte, 0x80])
            .map_err(|error| error.to_string())?;
        let mut trace = Vec::new();
        let outcome = machine
            .run_traced(5_700, &mut |step| trace.push(*step))
            .map_err(|error| error.to_string())?;
        assert_eq!(outcome, RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 5_681
        });
        check_branch_trace(&trace, &guest, &machine, byte)?;
        assert_eq!(machine.input_consumed(), 1);
        assert!(machine.output().is_empty());
    }
    let mut trace = Vec::new();
    let outcome = initial
        .run_traced(5_700, &mut |step| trace.push(*step))
        .map_err(|error| error.to_string())?;
    assert_eq!(outcome, RunOutcome::Terminated {
        reason: Termination::HaltInstruction,
        steps: 120
    });
    assert_eq!(
        trace
            .last()
            .map(|step| (step.before.registers.code_pointer, step.decoded)),
        Some((guest.eof_halt_code_address, Some(b'v')))
    );
    assert!(!trace.iter().any(|step| step.before.registers.code_pointer
        == guest.parity_store_code_address));
    assert!(
        !trace.iter().any(|step| step.before.registers.code_pointer
            == guest.branch_code_address)
    );
    assert!(initial.output().is_empty());
    assert_eq!(initial.input_consumed(), 0);
    Ok(())
}

#[expect(
    clippy::panic_in_result_fn,
    reason = "verify the actual parity-dependent pointer histories"
)]
#[test]
fn relocated_live_parity_paired_code_transfer() -> Result<(), String> {
    use super::layout::{
        AddressSelectedIndirectCase, AddressSelectedIndirectProbe,
        SourcePhysicalTraceBudget,
        verify_address_selected_indirect_guest_with_budget,
    };
    let guest = branch_source()?;
    for (even, odd) in [(0, 1), (254, 255)] {
        let input_even = [even, 128];
        let input_odd = [odd, 128];
        let probe = AddressSelectedIndirectProbe {
            cases: [
                AddressSelectedIndirectCase {
                    input: &input_even,
                    landing_address: guest.even_halt_code_address,
                    pointer_cell: 20,
                },
                AddressSelectedIndirectCase {
                    input: &input_odd,
                    landing_address: guest.odd_halt_code_address,
                    pointer_cell: 80,
                },
            ],
            indirect_code_cell: guest.branch_code_address,
            input_code_cell: guest.first_input_code_address,
            selector_cell: guest.parity_address,
            selector_code_cell: guest.selector_code_address,
            selector_store_code_cell: guest.parity_store_code_address,
            source: &guest.source,
            step_budget: 5_700,
        };
        let proof = verify_address_selected_indirect_guest_with_budget(
            current_profile(),
            probe,
            SourcePhysicalTraceBudget::MarkerTape,
        )
        .map_err(|error| format!("parity transfer proof: {error:?}"))?;
        let [even_proof, odd_proof] = proof.cases();
        assert_eq!(even_proof.selector_write().after, 0);
        assert_eq!(odd_proof.selector_write().after, 1);
        assert_eq!(even_proof.transfer().value, 123);
        assert_eq!(odd_proof.transfer().value, 118);
        assert_eq!(even_proof.landing_address(), guest.even_halt_code_address);
        assert_eq!(odd_proof.landing_address(), guest.odd_halt_code_address);
        let mut false_probe = probe;
        false_probe.cases[0].landing_address = guest.odd_halt_code_address;
        assert!(
            verify_address_selected_indirect_guest_with_budget(
                current_profile(),
                false_probe,
                SourcePhysicalTraceBudget::MarkerTape,
            )
            .is_err()
        );
    }
    Ok(())
}
