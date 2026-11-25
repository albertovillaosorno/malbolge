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
//   - Normative N15 replay of all first-byte classes and canonical EOF.
// - Must-Not:
//   - Claim a linked source-C CFG, source-frame ownership or checksum loop.
// - Allows:
//   - Inputs: the bounded graphical candidate and finite binary controls.
//   - Outputs: actual guest writes, branch path, and exact terminal I/O.
//   - Side effects: isolated normative VM execution.
// - Split-When:
//   - A general signed-input source lowering verifier owns this boundary.
// - Merge-When:
//   - Whole original source-C checksum translation subsumes this witness.
// - Summary:
//   - True EOF physically becomes signed C32 -1, never successful byte 255.

//! Source-loaded signed C23 EOF storage through real ternary operations.

use malbolge::{
    ProfileMachine, ProfileStepTrace, RunOutcome, Termination, TraceInput,
    current_profile, decode_profile_instruction, historical_profile,
};

use super::layout::{
    AddressSelectedIndirectCase, AddressSelectedIndirectError,
    AddressSelectedIndirectProbe, RelocatedSignedEofBranchSource,
    SourceCodeImageTraceError, SourcePhysicalImageTraceError,
    SourcePhysicalTraceBudget, ZeroCellSourceError,
    build_relocated_signed_eof_source, verify_address_selected_indirect_guest,
    verify_address_selected_indirect_guest_with_budget,
    verify_source_physical_image_trace,
    verify_source_physical_image_trace_with_budget,
};

const FRAME: u32 = 7_174_417;
const INPUT: [u32; 2] = [7_174_419, 7_174_420];
const SIGNED_EOF: [u32; 2] = [4_644_102, 299];
const TAPE_START: u32 = 7_174_501;
const EOF_STEPS: usize = 6_523;
const BYTE_STEPS: usize = 121;
const STEP_BUDGET: usize = 6_600;

fn source() -> Result<RelocatedSignedEofBranchSource, String> {
    build_relocated_signed_eof_source(current_profile())
        .map_err(|error| format!("signed EOF source: {error:?}"))
}

fn word(machine: &ProfileMachine, address: u32) -> Result<u32, String> {
    machine
        .memory_word(address)
        .map_err(|error| error.to_string())
}

fn pair(machine: &ProfileMachine) -> Result<[u32; 2], String> {
    let [low, high] = INPUT;
    Ok([word(machine, low)?, word(machine, high)?])
}

fn raw_machine(source: &[u8]) -> Result<ProfileMachine, String> {
    ProfileMachine::from_source(current_profile(), source, vec![])
        .map_err(|error| error.to_string())
}

fn fork(
    initial: &ProfileMachine,
    input: Vec<u8>,
) -> Result<ProfileMachine, String> {
    initial
        .fork_with_input(input)
        .map_err(|error| error.to_string())
}

#[expect(
    clippy::panic_in_result_fn,
    clippy::cognitive_complexity,
    reason = "freeze canonical graphical layout and C32 bit pattern"
)]
#[test]
fn relocated_signed_eof_geometry_is_canonical() -> Result<(), String> {
    let guest = source()?;
    assert_eq!(guest.source.len(), 6_642);
    assert_eq!(guest.source.get(6_640..), Some(&[39, 37][..]));
    assert_eq!(guest.input_pair, INPUT);
    assert_eq!(guest.zero_pair, [FRAME, 7_174_418]);
    assert_eq!(guest.output_data_address, 7_174_455);
    assert_eq!(
        [
            guest.first_input_code_address,
            guest.class_store_code_address,
            guest.branch_code_address,
            guest.byte_input_code_address,
            guest.byte_halt_code_address,
            guest.eof_arm_code_address
        ],
        [53, 99, 118, 120, 121, 126]
    );
    assert_eq!(guest.eof_store_code_addresses, [5_865, 6_404]);
    assert_eq!(
        [
            guest.eof_output_store_code_address,
            guest.eof_output_code_address,
            guest.eof_halt_code_address
        ],
        [6_527, 6_528, 6_529]
    );
    // Independent ordinary integer reconstruction, not the compiler encoder.
    assert_eq!(
        u64::from(SIGNED_EOF[1]) * 14_348_907 + u64::from(SIGNED_EOF[0]),
        u64::from(u32::MAX)
    );
    assert!(guest.source.iter().enumerate().all(|(position, &cell)| {
        decode_profile_instruction(
            u32::from(cell),
            u32::try_from(position).unwrap_or(u32::MAX),
        )
        .is_some_and(|opcode| b"ji*p</vo".contains(&opcode))
    }));
    assert_eq!(
        build_relocated_signed_eof_source(historical_profile()),
        Err(ZeroCellSourceError::UnsupportedProfile)
    );
    Ok(())
}

fn check_write(
    trace: &[ProfileStepTrace],
    code: u32,
    data: u32,
    value: u32,
) -> Result<(), String> {
    let step = trace
        .iter()
        .find(|step| step.before.registers.code_pointer == code)
        .ok_or_else(|| format!("C{code} was not reached"))?;
    if step.decoded != Some(b'p')
        || step.before.registers.data_pointer != data
        || step.after.registers.accumulator != value
        || step
            .memory_delta
            .data
            .map(|write| (write.address, write.after))
            != Some((data, value))
    {
        return Err(format!("C{code} did not write M{data}={value}"));
    }
    Ok(())
}

#[expect(
    clippy::panic_in_result_fn,
    clippy::cognitive_complexity,
    clippy::too_many_lines,
    reason = "authenticate reached EOF input, store and output transitions"
)]
#[test]
fn relocated_signed_eof_executes_both_canonical_word_stores()
-> Result<(), String> {
    let guest = source()?;
    let mut machine = raw_machine(&guest.source)?;
    let mut trace = Vec::new();
    let outcome = machine
        .run_traced(STEP_BUDGET, &mut |step| trace.push(*step))
        .map_err(|error| error.to_string())?;
    assert_eq!(outcome, RunOutcome::Terminated {
        reason: Termination::HaltInstruction,
        steps: EOF_STEPS
    });
    assert_eq!(machine.output(), &[0]);
    assert_eq!(machine.input_consumed(), 0);
    assert_eq!(pair(&machine)?, SIGNED_EOF);
    for address in guest.zero_pair {
        assert_eq!(word(&machine, address)?, 0);
    }
    assert_eq!(word(&machine, guest.output_data_address)?, 0);
    assert_eq!(word(&machine, 122)?, 7_174_466);
    let [low, high] = guest.eof_store_code_addresses;
    check_write(&trace, low, INPUT[0], SIGNED_EOF[0])?;
    check_write(&trace, high, INPUT[1], SIGNED_EOF[1])?;
    check_write(
        &trace,
        guest.eof_output_store_code_address,
        guest.output_data_address,
        0,
    )?;
    let reads = trace
        .iter()
        .filter_map(|step| {
            step.input
                .map(|input| (step.before.registers.code_pointer, input))
        })
        .collect::<Vec<_>>();
    assert_eq!(reads, [(53, TraceInput::EndOfInput)]);
    let outputs = trace
        .iter()
        .filter_map(|step| {
            step.output
                .map(|byte| (step.before.registers.code_pointer, byte))
        })
        .collect::<Vec<_>>();
    assert_eq!(outputs, [(guest.eof_output_code_address, 0)]);
    let branch = trace.get(118).ok_or("missing physical branch")?;
    assert_eq!(branch.decoded, Some(b'i'));
    assert_eq!(
        branch.after.registers.code_pointer,
        guest.eof_arm_code_address
    );
    // The byte-only halt becomes a physical marker seed after EOF selection.
    check_write(&trace, 689, 121, 7_174_480)?;
    assert_eq!(
        trace
            .iter()
            .filter(|step| step.decoded == Some(b'*')
                && step.before.registers.data_pointer == 121)
            .count(),
        14
    );
    assert!(
        !trace
            .iter()
            .any(|step| step.before.registers.code_pointer == 121)
    );
    Ok(())
}

#[expect(
    clippy::panic_in_result_fn,
    clippy::cognitive_complexity,
    reason = "finite 256-class byte/EOF distinction and independent VM traces"
)]
#[test]
fn relocated_signed_eof_preserves_every_successful_first_byte()
-> Result<(), String> {
    let guest = source()?;
    let initial = raw_machine(&guest.source)?;
    for first in u8::MIN..=u8::MAX {
        let mut machine = fork(&initial, vec![first, 0x80, 0x01])?;
        let mut inputs = Vec::new();
        let mut branch_landing = None;
        let outcome = machine
            .run_traced(STEP_BUDGET, &mut |step| {
                if let Some(input) = step.input {
                    inputs.push((step.before.registers.code_pointer, input));
                }
                if step.before.registers.code_pointer == 118 {
                    branch_landing = Some(step.after.registers.code_pointer);
                }
            })
            .map_err(|error| error.to_string())?;
        assert_eq!(
            outcome,
            RunOutcome::Terminated {
                reason: Termination::HaltInstruction,
                steps: BYTE_STEPS
            },
            "byte {first}"
        );
        assert_eq!(branch_landing, Some(120), "byte {first}");
        assert_eq!(inputs, [
            (53, TraceInput::Byte(first)),
            (120, TraceInput::Byte(0x80))
        ]);
        assert_eq!(machine.input_consumed(), 2);
        assert!(machine.output().is_empty());
        assert_eq!(pair(&machine)?, [u32::from(first), 0]);
        assert_eq!(
            word(&machine, TAPE_START)?,
            37,
            "EOF tape must not execute"
        );
    }
    // The byte arm's second read may itself be genuine EOF. It must not
    // normalize the prior successful first input to the signed EOF pair.
    for first in [0, 255] {
        let mut machine = fork(&initial, vec![first])?;
        let mut inputs = Vec::new();
        let outcome = machine
            .run_traced(STEP_BUDGET, &mut |step| {
                if let Some(input) = step.input {
                    inputs.push(input);
                }
            })
            .map_err(|error| error.to_string())?;
        assert_eq!(outcome, RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: BYTE_STEPS
        });
        assert_eq!(inputs, [TraceInput::Byte(first), TraceInput::EndOfInput]);
        assert_eq!(pair(&machine)?, [u32::from(first), 0]);
    }
    Ok(())
}

fn replace_with_noop(source: &mut [u8], position: u32) -> Result<(), String> {
    let byte = (33..=126u8)
        .find(|&cell| {
            decode_profile_instruction(u32::from(cell), position) == Some(b'o')
        })
        .ok_or("no graphical no-op")?;
    let index = usize::try_from(position).map_err(|error| error.to_string())?;
    *source.get_mut(index).ok_or("missing mutation site")? = byte;
    Ok(())
}

#[expect(
    clippy::panic_in_result_fn,
    reason = "omitted real result writes must not pass on output alone"
)]
#[test]
fn relocated_signed_eof_refuses_output_only_counterfeits() -> Result<(), String>
{
    let guest = source()?;
    for store in guest.eof_store_code_addresses {
        let mut mutated = guest.source.clone();
        replace_with_noop(&mut mutated, store)?;
        let mut machine = raw_machine(&mutated)?;
        let outcome = machine
            .run(STEP_BUDGET)
            .map_err(|error| error.to_string())?;
        assert_eq!(outcome, RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: EOF_STEPS
        });
        assert_eq!(machine.output(), &[0]);
        assert_ne!(
            pair(&machine)?,
            SIGNED_EOF,
            "omitted C{store} produced a false signed EOF"
        );
    }
    Ok(())
}

#[expect(
    clippy::panic_in_result_fn,
    clippy::too_many_lines,
    reason = "long tape must not relax short replay ceilings"
)]
#[test]
fn relocated_signed_eof_requires_explicit_marker_tape_budget()
-> Result<(), String> {
    let guest = source()?;
    let probe = AddressSelectedIndirectProbe {
        cases: [
            AddressSelectedIndirectCase {
                input: &[255, 128],
                landing_address: 120,
                pointer_cell: 117,
            },
            AddressSelectedIndirectCase {
                input: &[],
                landing_address: 126,
                pointer_cell: 48,
            },
        ],
        indirect_code_cell: 118,
        input_code_cell: 53,
        selector_cell: 7_174_423,
        selector_code_cell: 107,
        selector_store_code_cell: 99,
        source: &guest.source,
        step_budget: STEP_BUDGET,
    };
    assert_eq!(
        verify_address_selected_indirect_guest(current_profile(), probe),
        Err(AddressSelectedIndirectError::InvalidBound)
    );
    assert_eq!(
        verify_source_physical_image_trace(
            current_profile(),
            &guest.source,
            &[],
            STEP_BUDGET,
        ),
        Err(SourcePhysicalImageTraceError::Source(
            SourceCodeImageTraceError::InvalidBound
        ))
    );
    let proof = verify_address_selected_indirect_guest_with_budget(
        current_profile(),
        probe,
        SourcePhysicalTraceBudget::MarkerTape,
    )
    .map_err(|error| format!("extended pair: {error:?}"))?;
    assert_eq!(proof.budget(), SourcePhysicalTraceBudget::MarkerTape);
    let [byte, eof] = proof.cases();
    assert_eq!(byte.journal().source.outcome, RunOutcome::Terminated {
        reason: Termination::HaltInstruction,
        steps: BYTE_STEPS,
    });
    assert_eq!(eof.journal().source.outcome, RunOutcome::Terminated {
        reason: Termination::HaltInstruction,
        steps: EOF_STEPS,
    });
    assert!(eof.journal().expanded.len() > 128);
    for (address, expected) in INPUT.into_iter().zip(SIGNED_EOF) {
        let entry = eof
            .journal()
            .expanded
            .iter()
            .find(|cell| cell.site == address)
            .ok_or_else(|| format!("missing physical cell M{address}"))?;
        assert_eq!(entry.final_word, expected);
    }
    Ok(())
}

#[expect(
    clippy::panic_in_result_fn,
    reason = "bounded resource-class and execution failure controls"
)]
#[test]
fn relocated_signed_eof_long_replay_still_refuses_overbudget()
-> Result<(), String> {
    let guest = source()?;
    let too_long = verify_source_physical_image_trace_with_budget(
        current_profile(),
        &guest.source,
        &[],
        8193,
        SourcePhysicalTraceBudget::MarkerTape,
    );
    assert_eq!(
        too_long,
        Err(SourcePhysicalImageTraceError::Source(
            SourceCodeImageTraceError::InvalidBound
        ))
    );
    let overlong_source = vec![b'o'; 8193];
    assert_eq!(
        verify_source_physical_image_trace_with_budget(
            current_profile(),
            &overlong_source,
            &[],
            1,
            SourcePhysicalTraceBudget::MarkerTape,
        ),
        Err(SourcePhysicalImageTraceError::Source(
            SourceCodeImageTraceError::InvalidBound
        ))
    );
    let prefix = verify_source_physical_image_trace_with_budget(
        current_profile(),
        &guest.source,
        &[],
        512,
        SourcePhysicalTraceBudget::MarkerTape,
    )
    .map_err(|error| format!("bounded prefix: {error:?}"))?;
    assert!(matches!(
        prefix.source.outcome,
        RunOutcome::BudgetExhausted { steps: 512 }
    ));
    Ok(())
}
