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
//   - Real VM proof and adversarial admission of bounded linear code layout.
// - Must-Not:
//   - Treat emitted machine I/O as compiled C or final runtime realization.
// - Allows:
//   - Inputs: immutable canonical target profiles and linear opcode sequences.
//   - Outputs: exact graphical decoding and independent machine-run assertions.
//   - Side effects: bounded ProfileMachine execution only.
// - Split-When:
//   - Nonlinear layout obtains separate complete source/memory fixtures.
// - Merge-When:
//   - Full layout/backend verification reuses these exact linear fixtures.
// - Summary:
//   - Tests the first address-sensitive executable target source slice.
// - Description:
//   - Checks 94 decoder phases, VM I/O, halting and tamper rejection.
// - Usage:
//   - `cargo test --test malbolge_layout` from repository root.
// - Defaults:
//   - No claims about full ternary IR or revisitable mutable code.
//

//! Independent verifier and executable VM evidence for linear Malbolge code.

#[path = "../src/compiler/malbolge-layout/composition/lib.rs"]
pub mod layout;

use layout::{
    LinearLayout, LinearLayoutError, LinearOpcode, LinearProfileIdentity, PaddedCellOrigin,
    PaddedForwardStep, admit_linear_layout, encode_auto_padded_forward_layout,
    encode_linear_layout,
};
use malbolge::{
    ProfileMachine, ProfileRegisters, RunOutcome, current_profile, decode_profile_instruction,
    encrypt_profile_cell, historical_profile, target_profile,
};

fn verify_data_write_witness(
    machine: &ProfileMachine,
    layout: &LinearLayout,
    step: usize,
    trace: &malbolge::ProfileStepTrace,
) -> Result<(), String> {
    let Some(address) = layout
        .data_write_positions()
        .get(step)
        .copied()
        .ok_or("missing planned guest data-write witness")?
    else {
        if trace.memory_delta.data.is_some() {
            return Err(String::from("unexpected guest data write"));
        }
        return Ok(());
    };
    let source_end =
        u32::try_from(layout.source().len()).map_err(|error| format!("source length: {error}"))?;
    if address < source_end {
        return Err(String::from("arithmetic data write aliases source"));
    }
    let read = trace
        .memory_reads
        .data
        .ok_or("missing arithmetic data read")?;
    if read.address != address {
        return Err(String::from("runtime data read address differs from proof"));
    }
    if trace
        .memory_delta
        .data
        .is_some_and(|write| write.address != address || write.before != read.value)
    {
        return Err(String::from("runtime data mutation differs from proof"));
    }
    if trace.memory_delta.data.is_none()
        && machine
            .memory_word(address)
            .map_err(|error| format!("unchanged data word: {error:?}"))?
            != read.value
    {
        return Err(String::from("undisclosed runtime data mutation"));
    }
    Ok(())
}

fn verify_bidirectional_source_map(artifact: &layout::PaddedForwardLayout) -> Result<(), String> {
    if artifact.source_cell_origins().len() != artifact.operations().len() {
        return Err(String::from(
            "source-cell provenance must cover every code cell",
        ));
    }
    for (logical_index, &position) in artifact.logical_code_positions().iter().enumerate() {
        let physical = usize::try_from(position)
            .map_err(|error| format!("mapped source position: {error}"))?;
        if artifact.source_cell_origins().get(physical)
            != Some(&PaddedCellOrigin::Logical(
                u32::try_from(logical_index).map_err(|error| error.to_string())?,
            ))
        {
            return Err(String::from("logical and physical provenance disagree"));
        }
    }
    for (code, origin) in artifact.source_cell_origins().iter().enumerate() {
        let physical = u32::try_from(code).map_err(|error| error.to_string())?;
        let reached = artifact
            .layout()
            .executed_code_positions()
            .binary_search(&physical)
            .is_ok();
        match origin {
            PaddedCellOrigin::Logical(_) if !reached => {
                return Err(String::from("unreachable requested logical step"));
            }
            PaddedCellOrigin::ExecutedPadding if !reached => {
                return Err(String::from("claimed executed but skipped padding"));
            }
            PaddedCellOrigin::SkippedPadding if reached => {
                return Err(String::from("reached an allegedly skipped padding cell"));
            }
            PaddedCellOrigin::Logical(_) => {}
            PaddedCellOrigin::ExecutedPadding | PaddedCellOrigin::SkippedPadding => {
                if artifact.operations().get(code) != Some(&LinearOpcode::NoOperation) {
                    return Err(String::from("noncanonical synthetic padding opcode"));
                }
            }
        }
    }
    Ok(())
}

fn verify_execution_witness(
    machine: &mut ProfileMachine,
    layout: &LinearLayout,
) -> Result<(), String> {
    if layout.data_pointer_positions().len() != layout.executed_code_positions().len()
        || layout.data_write_positions().len() != layout.executed_code_positions().len()
    {
        return Err(String::from("layout data witness cardinality mismatch"));
    }
    for (step, &code) in layout.executed_code_positions().iter().enumerate() {
        if machine.registers().data_pointer
            != *layout
                .data_pointer_positions()
                .get(step)
                .ok_or("missing data witness")?
        {
            return Err(String::from(
                "runtime data pointer differs from layout proof",
            ));
        }
        if machine.registers().code_pointer != code {
            return Err(String::from("runtime code path differs from layout proof"));
        }
        let target = layout.encrypted_code_positions().get(step).copied();
        let before = target
            .map(|address| machine.memory_word(address))
            .transpose()
            .map_err(|error| format!("before encryption: {error:?}"))?;
        let mut observation: Option<malbolge::ProfileStepTrace> = None;
        let _outcome: malbolge::StepOutcome = machine
            .step_traced(&mut |trace| observation = Some(*trace))
            .map_err(|error| format!("layout execution: {error:?}"))?;
        let trace = observation.ok_or("missing normative transition trace")?;
        verify_data_write_witness(machine, layout, step, &trace)?;
        if let (Some(address), Some(value)) = (target, before) {
            let expected =
                encrypt_profile_cell(value).ok_or("encryption source must be graphical")?;
            let actual = machine
                .memory_word(address)
                .map_err(|error| format!("after encryption: {error:?}"))?;
            if actual != expected {
                return Err(String::from("runtime code encryption differs"));
            }
        }
    }
    if machine.termination().is_none() {
        return Err(String::from("layout path failed to terminate"));
    }
    Ok(())
}

const fn no_operation_halt() -> [LinearOpcode; 2] {
    [LinearOpcode::NoOperation, LinearOpcode::Halt]
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "test assertions are intentional after fallible setup"
)]
#[expect(
    clippy::cognitive_complexity,
    reason = "exact source, profile and witness regression covers two profiles"
)]
fn layout_encodes_current_and_historical_profiles_exactly() -> Result<(), String> {
    let operations = no_operation_halt();
    for profile in [current_profile(), historical_profile()] {
        let artifact = encode_linear_layout(profile, &operations)
            .map_err(|error| format!("canonical encoding: {error:?}"))?;
        assert_eq!(artifact.profile_id(), profile.id());
        assert_eq!(artifact.profile_fingerprint(), profile.fingerprint());
        assert_eq!(artifact.source().len(), operations.len());
        assert_eq!(artifact.executed_code_positions(), &[0, 1]);
        assert_eq!(artifact.encrypted_code_positions(), &[0]);
        for (position, byte) in artifact.source().iter().enumerate() {
            assert!((33..=126).contains(byte));
            let decoded = decode_profile_instruction(
                u32::from(*byte),
                u32::try_from(position).unwrap_or_default(),
            );
            assert_eq!(decoded, Some(if position == 0 { b'o' } else { b'v' }));
        }
        assert_eq!(
            admit_linear_layout(
                profile,
                &operations,
                artifact.source(),
                LinearProfileIdentity {
                    fingerprint: artifact.profile_fingerprint(),
                    id: artifact.profile_id(),
                },
            ),
            Ok(artifact),
        );
    }
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "test assertions are intentional after fallible setup"
)]
#[expect(
    clippy::excessive_nesting,
    reason = "exhaustive profile/phase/opcode coverage is deliberately nested"
)]
fn all_94_profile_decode_phases_admit_machine_io_and_halt() -> Result<(), String> {
    for profile in [current_profile(), historical_profile()] {
        for phase in 0..94 {
            for opcode in [LinearOpcode::InputWord, LinearOpcode::OutputByte] {
                let mut operations = vec![LinearOpcode::NoOperation; phase + 2];
                *operations.get_mut(phase).ok_or("missing phase")? = opcode;
                *operations.last_mut().ok_or("missing final instruction")? = LinearOpcode::Halt;
                let layout = encode_linear_layout(profile, &operations)
                    .map_err(|error| format!("phase encoding: {error:?}"))?;
                let desired = match opcode {
                    LinearOpcode::CrazyData => b'p',
                    LinearOpcode::RotateData => b'*',
                    LinearOpcode::InputWord => profile.input_instruction(),
                    LinearOpcode::OutputByte => profile.output_instruction(),
                    LinearOpcode::NoOperation
                    | LinearOpcode::Halt
                    | LinearOpcode::RelocateDataPointer
                    | LinearOpcode::JumpForward { .. } => {
                        return Err(String::from("unexpected test case"));
                    }
                };
                assert_eq!(
                    decode_profile_instruction(
                        u32::from(layout.source().get(phase).copied().ok_or("phase cell")?),
                        u32::try_from(phase).unwrap_or_default(),
                    ),
                    Some(desired)
                );
            }
        }
    }
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "test assertions are intentional after fallible setup"
)]
fn emitted_source_runs_on_normative_vm_without_guest_host_callbacks() -> Result<(), String> {
    let operations = [
        LinearOpcode::NoOperation,
        LinearOpcode::InputWord,
        LinearOpcode::OutputByte,
        LinearOpcode::Halt,
    ];
    for profile in [current_profile(), historical_profile()] {
        let layout = encode_linear_layout(profile, &operations)
            .map_err(|error| format!("VM layout: {error:?}"))?;
        assert_eq!(layout.executed_code_positions(), &[0, 1, 2, 3]);
        assert_eq!(layout.encrypted_code_positions(), &[0, 1, 2]);
        assert_eq!(layout.data_write_positions(), &[None; 4]);
        let mut machine = ProfileMachine::from_source(profile, layout.source(), vec![b'Q'])
            .map_err(|error| format!("VM load: {error:?}"))?;
        assert!(matches!(
            machine.run(operations.len()),
            Ok(RunOutcome::Terminated { steps: 4, .. }),
        ));
        assert_eq!(machine.output(), b"Q");
        assert_eq!(machine.input_consumed(), 1);
    }
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "VM execution assertions follow fallible setup"
)]
fn real_rotate_and_crazy_instructions_execute_without_jumps() -> Result<(), String> {
    let operations = [
        LinearOpcode::RelocateDataPointer,
        LinearOpcode::RotateData,
        LinearOpcode::CrazyData,
        LinearOpcode::Halt,
    ];
    for profile in [current_profile(), historical_profile()] {
        let layout = encode_linear_layout(profile, &operations)
            .map_err(|error| format!("arithmetic layout: {error:?}"))?;
        assert_eq!(
            decode_profile_instruction(
                u32::from(layout.source().get(1).copied().ok_or("rotate cell")?),
                1,
            ),
            Some(b'*'),
        );
        assert_eq!(
            decode_profile_instruction(
                u32::from(layout.source().get(2).copied().ok_or("crazy cell")?),
                2,
            ),
            Some(b'p'),
        );
        assert_eq!(layout.executed_code_positions(), &[0, 1, 2, 3]);
        assert_eq!(layout.encrypted_code_positions(), &[0, 1, 2]);
        assert_eq!(
            layout.data_write_positions(),
            &[
                None,
                layout.data_pointer_positions().get(1).copied(),
                layout.data_pointer_positions().get(2).copied(),
                None,
            ]
        );
        let mut machine = ProfileMachine::from_source(profile, layout.source(), vec![])
            .map_err(|error| format!("arithmetic VM load: {error:?}"))?;
        verify_execution_witness(&mut machine, &layout)?;
        let prologue_byte = layout.source().first().copied().ok_or("no prologue")?;
        assert_eq!(
            machine.registers().data_pointer,
            u32::from(prologue_byte).saturating_add(3),
        );
        assert!(machine.output().is_empty());
    }
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "test assertions are intentional after fallible setup"
)]
fn layout_fail_closed_on_unsupported_shapes() -> Result<(), String> {
    let profile = current_profile();
    assert_eq!(
        encode_linear_layout(profile, &[]),
        Err(LinearLayoutError::TooShort)
    );
    assert_eq!(
        encode_linear_layout(profile, &[LinearOpcode::Halt]),
        Err(LinearLayoutError::TooShort),
    );
    assert_eq!(
        encode_linear_layout(profile, &[LinearOpcode::NoOperation; 2]),
        Err(LinearLayoutError::MissingHalt),
    );
    assert_eq!(
        encode_linear_layout(
            profile,
            &[
                LinearOpcode::Halt,
                LinearOpcode::NoOperation,
                LinearOpcode::Halt,
            ]
        ),
        Err(LinearLayoutError::EarlyHalt { position: 0 }),
    );
    let mut oversize = vec![LinearOpcode::NoOperation; 4097];
    *oversize.last_mut().ok_or("missing oversize terminal")? = LinearOpcode::Halt;
    assert_eq!(
        encode_linear_layout(profile, &oversize),
        Err(LinearLayoutError::TooLong),
    );
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "capacity boundary assertions follow fallible VM setup"
)]
fn relocated_data_limit_is_exactly_encoded_code_zero_cell() -> Result<(), String> {
    for profile in [current_profile(), historical_profile()] {
        let probe = encode_linear_layout(
            profile,
            &[LinearOpcode::RelocateDataPointer, LinearOpcode::Halt],
        )
        .map_err(|error| format!("relocation probe: {error:?}"))?;
        let span = usize::from(probe.source().first().copied().ok_or("probe cell")?);
        let mut exact = vec![LinearOpcode::NoOperation; span];
        *exact.first_mut().ok_or("empty exact program")? = LinearOpcode::RelocateDataPointer;
        *exact.get_mut(1).ok_or("missing crazy operation")? = LinearOpcode::CrazyData;
        *exact.last_mut().ok_or("missing final halt")? = LinearOpcode::Halt;
        let valid = encode_linear_layout(profile, &exact)
            .map_err(|error| format!("exact relocation: {error:?}"))?;
        assert_eq!(valid.source().len(), span);
        let mut machine = ProfileMachine::from_source(profile, valid.source(), vec![])
            .map_err(|error| format!("exact VM load: {error:?}"))?;
        assert!(matches!(
            machine.run(span),
            Ok(RunOutcome::Terminated { .. })
        ));
        exact.insert(1, LinearOpcode::NoOperation);
        assert_eq!(
            encode_linear_layout(profile, &exact),
            Err(LinearLayoutError::UnsafeDataPlacement),
        );
    }
    Ok(())
}

#[test]
fn relocation_proofs_reject_aliases_and_unplaced_arithmetic() {
    let profile = current_profile();
    assert_eq!(
        encode_linear_layout(
            profile,
            &[
                LinearOpcode::NoOperation,
                LinearOpcode::RotateData,
                LinearOpcode::Halt,
            ]
        ),
        Err(LinearLayoutError::UnsafeDataPlacement),
    );
    assert_eq!(
        encode_linear_layout(
            profile,
            &[
                LinearOpcode::NoOperation,
                LinearOpcode::CrazyData,
                LinearOpcode::RelocateDataPointer,
                LinearOpcode::Halt,
            ]
        ),
        Err(LinearLayoutError::UnsafeDataPlacement),
    );
    assert_eq!(
        encode_linear_layout(
            profile,
            &[
                LinearOpcode::NoOperation,
                LinearOpcode::RelocateDataPointer,
                LinearOpcode::RelocateDataPointer,
                LinearOpcode::Halt,
            ]
        ),
        Err(LinearLayoutError::UnsafeDataPlacement),
    );
    let mut aliased = vec![LinearOpcode::NoOperation; 130];
    if let Some(first) = aliased.first_mut() {
        *first = LinearOpcode::RelocateDataPointer;
    }
    if let Some(last) = aliased.last_mut() {
        *last = LinearOpcode::Halt;
    }
    assert_eq!(
        encode_linear_layout(profile, &aliased),
        Err(LinearLayoutError::UnsafeDataPlacement),
    );
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "test assertions are intentional after fallible setup"
)]
#[expect(
    clippy::too_many_lines,
    reason = "one tamper suite preserves all profile and byte-field checks"
)]
fn independently_supplied_source_cannot_forge_opcode_or_profile() -> Result<(), String> {
    let profile = current_profile();
    let ops = [
        LinearOpcode::InputWord,
        LinearOpcode::OutputByte,
        LinearOpcode::Halt,
    ];
    let artifact = encode_linear_layout(profile, &ops)
        .map_err(|error| format!("canonical source: {error:?}"))?;
    let check = |source: &[u8], profile_id: &str, fingerprint: &str| {
        admit_linear_layout(
            profile,
            &ops,
            source,
            LinearProfileIdentity {
                fingerprint,
                id: profile_id,
            },
        )
    };
    assert_eq!(
        check(
            artifact.source(),
            "forged-profile",
            artifact.profile_fingerprint(),
        ),
        Err(LinearLayoutError::ProfileMismatch)
    );
    assert_eq!(
        check(
            artifact.source(),
            artifact.profile_id(),
            "forged-fingerprint",
        ),
        Err(LinearLayoutError::ProfileMismatch)
    );
    assert_eq!(
        check(
            artifact.source().get(..2).ok_or("truncated layout")?,
            artifact.profile_id(),
            artifact.profile_fingerprint(),
        ),
        Err(LinearLayoutError::SourceLengthMismatch)
    );
    for position in 0..ops.len() {
        let mut altered = artifact.source().to_vec();
        let altered_cell = altered.get_mut(position).ok_or("missing cell")?;
        *altered_cell = if *altered_cell == 33 { 34 } else { 33 };
        assert_eq!(
            check(
                &altered,
                artifact.profile_id(),
                artifact.profile_fingerprint(),
            ),
            Err(LinearLayoutError::DecodeMismatch { position })
        );
    }
    let extra = [artifact.source(), b"v"].concat();
    assert_eq!(
        check(
            &extra,
            artifact.profile_id(),
            artifact.profile_fingerprint(),
        ),
        Err(LinearLayoutError::SourceLengthMismatch)
    );
    Ok(())
}

/// Derive a single forward target from the normative inverse decoder.
fn jump_target(position: u32) -> Result<u32, String> {
    let candidates = (33u32..=126u32)
        .filter(|cell| decode_profile_instruction(*cell, position) == Some(b'i'))
        .collect::<Vec<_>>();
    let source_cell = match candidates.as_slice() {
        [one] => *one,
        _ => return Err(String::from("jump decoder has no unique inverse")),
    };
    source_cell
        .checked_add(1)
        .ok_or_else(|| String::from("jump target overflow"))
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "target address and VM execution are independently asserted"
)]
fn forward_jump_skips_padding_and_reaches_exact_output_on_both_vms() -> Result<(), String> {
    for profile in [current_profile(), historical_profile()] {
        let target = jump_target(0)?;
        let stop = usize::try_from(target)
            .map_err(|error| error.to_string())?
            .saturating_add(2);
        let mut ops = vec![LinearOpcode::NoOperation; stop];
        *ops.first_mut().ok_or("missing jump")? = LinearOpcode::JumpForward { target };
        *ops.get_mut(usize::try_from(target).map_err(|error| error.to_string())?)
            .ok_or("missing destination")? = LinearOpcode::OutputByte;
        *ops.last_mut().ok_or("missing halt")? = LinearOpcode::Halt;
        let artifact = encode_linear_layout(profile, &ops)
            .map_err(|error| format!("jump layout: {error:?}"))?;
        assert_eq!(
            u32::from(artifact.source().first().copied().ok_or("no jump source")?) + 1,
            target,
        );
        assert_eq!(
            artifact.executed_code_positions(),
            &[0, target, target.saturating_add(1)],
        );
        assert_eq!(
            artifact.encrypted_code_positions(),
            &[target.saturating_sub(1), target]
        );
        let mut machine = ProfileMachine::from_source(profile, artifact.source(), vec![])
            .map_err(|error| format!("jump VM load: {error:?}"))?;
        assert!(matches!(
            machine.run(3),
            Ok(RunOutcome::Terminated { steps: 3, .. }),
        ));
        assert_eq!(machine.output(), &[0]);
        assert_eq!(machine.registers().code_pointer, target.saturating_add(1));
        // Jump encrypts cell target-1 before entering target, but must not
        // overwrite the output and halt instructions at reachable positions.
        assert_ne!(
            machine
                .memory_word(target.saturating_sub(1))
                .map_err(|error| format!("encryption evidence: {error:?}"))?,
            u32::from(
                artifact
                    .source()
                    .get(
                        usize::try_from(target.saturating_sub(1))
                            .map_err(|error| error.to_string())?
                    )
                    .copied()
                    .ok_or("missing gap")?
            ),
        );
    }
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "adversarial jump arrangements have explicit expected failures"
)]
fn jump_rejects_wrong_target_backward_or_nonpadding_gap() -> Result<(), String> {
    let profile = current_profile();
    let target = jump_target(0)?;
    let len = usize::try_from(target)
        .map_err(|error| error.to_string())?
        .saturating_add(2);
    let mut ops = vec![LinearOpcode::NoOperation; len];
    *ops.first_mut().ok_or("missing jump")? = LinearOpcode::JumpForward { target };
    *ops.last_mut().ok_or("missing final halt")? = LinearOpcode::Halt;
    assert!(encode_linear_layout(profile, &ops).is_ok());
    *ops.first_mut().ok_or("missing jump")? = LinearOpcode::JumpForward {
        target: target.saturating_add(1),
    };
    assert_eq!(
        encode_linear_layout(profile, &ops),
        Err(LinearLayoutError::JumpTargetMismatch { position: 0 }),
    );
    *ops.first_mut().ok_or("missing jump")? = LinearOpcode::JumpForward { target: 0 };
    assert_eq!(
        encode_linear_layout(profile, &ops),
        Err(LinearLayoutError::JumpPathUnsupported),
    );
    *ops.first_mut().ok_or("missing jump")? = LinearOpcode::JumpForward { target };
    *ops.get_mut(1).ok_or("missing padding")? = LinearOpcode::OutputByte;
    assert_eq!(
        encode_linear_layout(profile, &ops),
        Err(LinearLayoutError::JumpPathUnsupported),
    );
    *ops.get_mut(1).ok_or("missing padding")? = LinearOpcode::NoOperation;
    *ops.get_mut(2).ok_or("missing second jump")? = LinearOpcode::JumpForward { target };
    assert_eq!(
        encode_linear_layout(profile, &ops),
        Err(LinearLayoutError::JumpPathUnsupported),
    );
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "forward jump and byte-I/O state are independently checked"
)]
fn forward_jump_after_input_preserves_guest_data_state() -> Result<(), String> {
    let target = jump_target(2)?;
    let end = usize::try_from(target)
        .map_err(|error| error.to_string())?
        .saturating_add(2);
    let mut ops = vec![LinearOpcode::NoOperation; end];
    *ops.get_mut(1).ok_or("missing input instruction")? = LinearOpcode::InputWord;
    *ops.get_mut(2).ok_or("missing jump instruction")? = LinearOpcode::JumpForward { target };
    *ops.get_mut(usize::try_from(target).map_err(|error| error.to_string())?)
        .ok_or("missing output instruction")? = LinearOpcode::OutputByte;
    *ops.last_mut().ok_or("missing final halt")? = LinearOpcode::Halt;
    for profile in [current_profile(), historical_profile()] {
        let layout = encode_linear_layout(profile, &ops)
            .map_err(|error| format!("jump after input layout: {error:?}"))?;
        assert_eq!(
            layout.executed_code_positions(),
            &[0, 1, 2, target, target.saturating_add(1)]
        );
        assert_eq!(
            layout.encrypted_code_positions(),
            &[0, 1, target.saturating_sub(1), target]
        );
        let mut machine = ProfileMachine::from_source(profile, layout.source(), vec![b'Y'])
            .map_err(|error| format!("jump after input VM load: {error:?}"))?;
        verify_execution_witness(&mut machine, &layout)?;
        assert_eq!(machine.input_consumed(), 1);
        assert_eq!(machine.output(), b"Y");
        assert_eq!(machine.registers().accumulator, u32::from(b'Y'));
        assert_eq!(machine.registers().code_pointer, target.saturating_add(1));
    }
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "jump/relocation policy is asserted as an explicit rejection"
)]
fn forward_jump_cannot_mix_with_data_relocation() -> Result<(), String> {
    let target = jump_target(1)?;
    let end = usize::try_from(target)
        .map_err(|error| error.to_string())?
        .saturating_add(1);
    let mut ops = vec![LinearOpcode::NoOperation; end];
    *ops.first_mut().ok_or("missing relocation")? = LinearOpcode::RelocateDataPointer;
    *ops.get_mut(1).ok_or("missing jump")? = LinearOpcode::JumpForward { target };
    *ops.last_mut().ok_or("missing final halt")? = LinearOpcode::Halt;
    assert_eq!(
        encode_linear_layout(current_profile(), &ops),
        Err(LinearLayoutError::JumpPathUnsupported),
    );
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "relocation capacity and complete VM execution are asserted"
)]
fn later_relocation_uses_its_own_code_phase_for_larger_data_safe_layout() -> Result<(), String> {
    for profile in [current_profile(), historical_profile()] {
        let selected = (1u32..94u32)
            .find_map(|position| {
                let byte = (33u32..=126u32)
                    .find(|&byte| decode_profile_instruction(byte, position) == Some(b'j'))?;
                (byte >= 80 && byte > position).then_some((position, byte))
            })
            .ok_or("no later relocation phase with larger code-data separation")?;
        let (position, data_address) = selected;
        let capacity = usize::try_from(data_address).map_err(|error| error.to_string())?;
        let position_usize = usize::try_from(position).map_err(|error| error.to_string())?;
        let mut operations = vec![LinearOpcode::NoOperation; capacity];
        *operations
            .get_mut(position_usize)
            .ok_or("relocation slot")? = LinearOpcode::RelocateDataPointer;
        *operations
            .get_mut(position_usize.saturating_add(1))
            .ok_or("rotate slot")? = LinearOpcode::RotateData;
        *operations
            .get_mut(position_usize.saturating_add(2))
            .ok_or("crazy slot")? = LinearOpcode::CrazyData;
        *operations.last_mut().ok_or("halt slot")? = LinearOpcode::Halt;
        let artifact = encode_linear_layout(profile, &operations)
            .map_err(|error| format!("later data relocation: {error:?}"))?;
        assert_eq!(
            artifact
                .source()
                .get(position_usize)
                .copied()
                .ok_or("source relocation")?,
            u8::try_from(data_address).map_err(|error| error.to_string())?,
        );
        assert!(artifact.source().len() > 40);
        let mut machine = ProfileMachine::from_source(profile, artifact.source(), vec![])
            .map_err(|error| format!("later relocation loader: {error:?}"))?;
        verify_execution_witness(&mut machine, &artifact)?;
        assert!(machine.registers().data_pointer > data_address);
        assert!(machine.output().is_empty());
        // Source position is unchanged, so one more code cell crosses the
        // exact same encoded graphical data base and is rejected.
        operations.insert(position_usize.saturating_add(1), LinearOpcode::NoOperation);
        assert_eq!(
            encode_linear_layout(profile, &operations),
            Err(LinearLayoutError::UnsafeDataPlacement),
        );
    }
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "the profile-decoder phase enumeration is an exhaustive assertion"
)]
#[expect(
    clippy::excessive_nesting,
    reason = "exhaustively enumerate profile, phase, relocation and arithmetic"
)]
fn relocated_arithmetic_encodes_every_safely_addressable_phase() -> Result<(), String> {
    for profile in [current_profile(), historical_profile()] {
        let mut admitted_phases = 0u32;
        for phase in 1usize..94usize {
            let length = phase.saturating_add(2);
            let base = (0usize..phase).find(|&position| {
                (33u32..=126u32).any(|source| {
                    decode_profile_instruction(source, u32::try_from(position).unwrap_or(0))
                        == Some(b'j')
                        && usize::try_from(source).unwrap_or(0) >= length
                })
            });
            let Some(relocation_position) = base else {
                continue;
            };
            admitted_phases = admitted_phases.saturating_add(1);
            for arithmetic in [LinearOpcode::CrazyData, LinearOpcode::RotateData] {
                let mut operations = vec![LinearOpcode::NoOperation; length];
                *operations
                    .get_mut(relocation_position)
                    .ok_or("relocation phase")? = LinearOpcode::RelocateDataPointer;
                *operations.get_mut(phase).ok_or("arithmetic phase")? = arithmetic;
                *operations.last_mut().ok_or("final halt")? = LinearOpcode::Halt;
                let artifact = encode_linear_layout(profile, &operations)
                    .map_err(|error| format!("phase arithmetic layout: {error:?}"))?;
                let expected = match arithmetic {
                    LinearOpcode::CrazyData => b'p',
                    LinearOpcode::RotateData => b'*',
                    LinearOpcode::Halt
                    | LinearOpcode::InputWord
                    | LinearOpcode::JumpForward { .. }
                    | LinearOpcode::NoOperation
                    | LinearOpcode::OutputByte
                    | LinearOpcode::RelocateDataPointer => {
                        return Err(String::from("incorrect arithmetic fixture"));
                    }
                };
                let cell = artifact
                    .source()
                    .get(phase)
                    .copied()
                    .ok_or("phase source")?;
                assert_eq!(
                    decode_profile_instruction(u32::from(cell), u32::try_from(phase).unwrap_or(0)),
                    Some(expected)
                );
                assert_eq!(artifact.executed_code_positions().len(), length);
                assert_eq!(
                    artifact.encrypted_code_positions().len(),
                    length.saturating_sub(1)
                );
            }
        }
        assert!(admitted_phases >= 60);
    }
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "independent phase and witness assertions cover every forward jump"
)]
fn every_addressable_forward_jump_phase_has_exact_static_path() -> Result<(), String> {
    for profile in [current_profile(), historical_profile()] {
        let mut admitted = 0u32;
        for position in 0u32..94u32 {
            let target = jump_target(position)?;
            if target <= position {
                continue;
            }
            admitted = admitted.saturating_add(1);
            let size = usize::try_from(target)
                .map_err(|error| error.to_string())?
                .saturating_add(2);
            let mut operations = vec![LinearOpcode::NoOperation; size];
            *operations
                .get_mut(usize::try_from(position).map_err(|error| error.to_string())?)
                .ok_or("jump slot")? = LinearOpcode::JumpForward { target };
            *operations
                .get_mut(usize::try_from(target).map_err(|error| error.to_string())?)
                .ok_or("target slot")? = LinearOpcode::OutputByte;
            *operations.last_mut().ok_or("terminal halt")? = LinearOpcode::Halt;
            let artifact = encode_linear_layout(profile, &operations)
                .map_err(|error| format!("forward phase layout: {error:?}"))?;
            assert_eq!(
                u32::from(
                    artifact
                        .source()
                        .get(usize::try_from(position).map_err(|error| error.to_string())?)
                        .copied()
                        .ok_or("jump source")?
                )
                .saturating_add(1),
                target,
            );
            let expected_steps = usize::try_from(position)
                .map_err(|error| error.to_string())?
                .saturating_add(3);
            assert_eq!(artifact.executed_code_positions().len(), expected_steps);
            assert_eq!(
                artifact.encrypted_code_positions().len(),
                expected_steps.saturating_sub(1)
            );
            assert_eq!(
                artifact.executed_code_positions().last(),
                Some(&target.saturating_add(1))
            );
            assert!(
                artifact
                    .encrypted_code_positions()
                    .contains(&target.saturating_sub(1))
            );
        }
        assert!(admitted >= 45);
    }
    Ok(())
}

/// Prove two true nonconsecutive jumps where the second derives its target
/// from a skipped no-op *data* cell, not from the jump's own source cell.
fn two_forward_jump_fixture() -> Vec<LinearOpcode> {
    (0..128usize)
        .map(|position| match position {
            0 => LinearOpcode::InputWord,
            36 => LinearOpcode::JumpForward { target: 63 },
            63 => LinearOpcode::JumpForward { target: 126 },
            126 => LinearOpcode::OutputByte,
            127 => LinearOpcode::Halt,
            _ => LinearOpcode::NoOperation,
        })
        .collect()
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "two real VM control transfers have exact witness assertions"
)]
#[expect(
    clippy::cognitive_complexity,
    reason = "stepwise code and data pointers, encryption, and I/O are checked"
)]
fn two_forward_jumps_read_evolving_data_pointer_cells_under_both_profiles() -> Result<(), String> {
    let ops = two_forward_jump_fixture();
    for profile in [current_profile(), historical_profile()] {
        let layout = encode_linear_layout(profile, &ops)
            .map_err(|error| format!("two-jump encoding: {error:?}"))?;
        assert_eq!(layout.source().len(), 128);
        assert_eq!(layout.source().get(36).copied(), Some(62));
        assert_eq!(layout.source().get(37).copied(), Some(125));
        assert_ne!(layout.source().get(63).copied(), Some(125));
        let expected_path: Vec<u32> = (0..=36).chain([63, 126, 127]).collect();
        assert_eq!(layout.executed_code_positions(), expected_path);
        assert_eq!(layout.encrypted_code_positions().last(), Some(&126));
        assert!(layout.encrypted_code_positions().contains(&62));
        assert!(layout.encrypted_code_positions().contains(&125));
        let mut vm = ProfileMachine::from_source(profile, layout.source(), vec![0xe7])
            .map_err(|error| format!("two-jump VM load: {error:?}"))?;
        verify_execution_witness(&mut vm, &layout)?;
        assert_eq!(vm.input_consumed(), 1);
        assert_eq!(vm.output(), &[0xe7]);
        assert_eq!(vm.registers().code_pointer, 127);
        assert_eq!(vm.registers().data_pointer, 39);
    }
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "post-encryption data read is checked on both real VMs"
)]
#[expect(
    clippy::cognitive_complexity,
    reason = "two control transfers and operand encryption are checked against the VM"
)]
fn second_forward_jump_reads_previous_encrypted_padding_as_data() -> Result<(), String> {
    let mut operations = vec![LinearOpcode::NoOperation; 127];
    for (position, operation) in operations.iter_mut().enumerate() {
        *operation = match position {
            0 => LinearOpcode::InputWord,
            26 => LinearOpcode::JumpForward { target: 73 },
            118 => LinearOpcode::JumpForward { target: 125 },
            125 => LinearOpcode::OutputByte,
            126 => LinearOpcode::Halt,
            _ => LinearOpcode::NoOperation,
        };
    }
    for profile in [current_profile(), historical_profile()] {
        let artifact = encode_linear_layout(profile, &operations)
            .map_err(|error| format!("encrypted operand: {error:?}"))?;
        assert_eq!(artifact.source().get(72).copied(), Some(90));
        assert_eq!(encrypt_profile_cell(90), Some(124));
        assert_eq!(artifact.data_pointer_positions().get(72), Some(&72));
        assert_eq!(artifact.executed_code_positions().last(), Some(&126));
        assert!(artifact.encrypted_code_positions().contains(&72));
        assert!(artifact.encrypted_code_positions().contains(&124));
        let mut vm = ProfileMachine::from_source(profile, artifact.source(), vec![0x91])
            .map_err(|error| format!("encrypted operand VM load: {error:?}"))?;
        verify_execution_witness(&mut vm, &artifact)?;
        assert_eq!(vm.input_consumed(), 1);
        assert_eq!(vm.output(), &[0x91]);
    }
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "independent source admission must reject forged jump geometry"
)]
#[expect(
    clippy::cognitive_complexity,
    reason = "distinct forged target, effectful gaps, and backward motion reject"
)]
fn second_jump_rejects_forged_data_target_and_effectful_padding() -> Result<(), String> {
    let profile = current_profile();
    let mut operations = two_forward_jump_fixture();
    let original = encode_linear_layout(profile, &operations)
        .map_err(|error| format!("original jump layout: {error:?}"))?;
    let identity = LinearProfileIdentity {
        fingerprint: original.profile_fingerprint(),
        id: original.profile_id(),
    };
    if let Some(operation) = operations.get_mut(63) {
        *operation = LinearOpcode::JumpForward { target: 125 };
    }
    assert_eq!(
        admit_linear_layout(profile, &operations, original.source(), identity),
        Err(LinearLayoutError::JumpTargetMismatch { position: 63 }),
    );
    assert_eq!(
        encode_linear_layout(profile, &operations),
        Err(LinearLayoutError::JumpTargetMismatch { position: 63 }),
    );
    if let Some(operation) = operations.get_mut(63) {
        *operation = LinearOpcode::JumpForward { target: 126 };
    }
    for skipped in [37usize, 100usize, 125usize] {
        if let Some(operation) = operations.get_mut(skipped) {
            *operation = LinearOpcode::OutputByte;
        }
        assert_eq!(
            encode_linear_layout(profile, &operations),
            Err(LinearLayoutError::JumpPathUnsupported),
        );
        if let Some(operation) = operations.get_mut(skipped) {
            *operation = LinearOpcode::NoOperation;
        }
    }
    if let Some(operation) = operations.get_mut(63) {
        *operation = LinearOpcode::JumpForward { target: 62 };
    }
    assert_eq!(
        encode_linear_layout(profile, &operations),
        Err(LinearLayoutError::JumpPathUnsupported),
    );
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "three jumps are validated against actual C/D/memory observations"
)]
#[expect(
    clippy::cognitive_complexity,
    reason = "exact three-jump VM witness and byte-effect assertions"
)]
fn three_forward_jumps_reuse_an_earlier_encrypted_operand() -> Result<(), String> {
    let operations: Vec<LinearOpcode> = (0..127usize)
        .map(|position| match position {
            0 => LinearOpcode::InputWord,
            26 => LinearOpcode::JumpForward { target: 73 },
            102 => LinearOpcode::JumpForward { target: 107 },
            122 => LinearOpcode::JumpForward { target: 125 },
            125 => LinearOpcode::OutputByte,
            126 => LinearOpcode::Halt,
            _ => LinearOpcode::NoOperation,
        })
        .collect();
    for profile in [current_profile(), historical_profile()] {
        let layout = encode_linear_layout(profile, &operations)
            .map_err(|error| format!("three jump layout: {error:?}"))?;
        assert_eq!(layout.source().get(72).copied(), Some(90));
        assert_eq!(encrypt_profile_cell(90), Some(124));
        assert!(layout.encrypted_code_positions().contains(&72));
        assert!(layout.encrypted_code_positions().contains(&106));
        assert!(layout.encrypted_code_positions().contains(&124));
        let third_index = layout
            .executed_code_positions()
            .iter()
            .position(|position| *position == 122)
            .ok_or("missing third jump in witness")?;
        assert_eq!(layout.data_pointer_positions().get(third_index), Some(&72));
        assert_eq!(layout.executed_code_positions().last(), Some(&126));
        let mut vm = ProfileMachine::from_source(profile, layout.source(), vec![0xaf])
            .map_err(|error| format!("three jump VM: {error:?}"))?;
        verify_execution_witness(&mut vm, &layout)?;
        assert_eq!(vm.output(), &[0xaf]);
        assert_eq!(vm.input_consumed(), 1);
    }
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "real VM proves a later jump reads an already executed and encrypted no-op"
)]
fn later_jump_may_read_previously_executed_and_encrypted_code_data() -> Result<(), String> {
    let operations: Vec<LinearOpcode> = (0..127usize)
        .map(|position| match position {
            0 => LinearOpcode::InputWord,
            27 => LinearOpcode::JumpForward { target: 72 },
            116 => LinearOpcode::JumpForward { target: 125 },
            125 => LinearOpcode::OutputByte,
            126 => LinearOpcode::Halt,
            _ => LinearOpcode::NoOperation,
        })
        .collect();
    for profile in [current_profile(), historical_profile()] {
        let layout = encode_linear_layout(profile, &operations)
            .map_err(|error| format!("executed operand encoding: {error:?}"))?;
        assert_eq!(layout.source().get(72).copied(), Some(90));
        assert_eq!(encrypt_profile_cell(90), Some(124));
        let second_jump_index = layout
            .executed_code_positions()
            .iter()
            .position(|position| *position == 116)
            .ok_or("second jump not reached")?;
        assert_eq!(
            layout.data_pointer_positions().get(second_jump_index),
            Some(&72)
        );
        assert!(layout.executed_code_positions().contains(&72));
        assert!(layout.encrypted_code_positions().contains(&72));
        let mut vm = ProfileMachine::from_source(profile, layout.source(), vec![0x80])
            .map_err(|error| format!("executed operand VM: {error:?}"))?;
        verify_execution_witness(&mut vm, &layout)?;
        assert_eq!(vm.input_consumed(), 1);
        assert_eq!(vm.output(), &[0x80]);
    }
    Ok(())
}

/// The first jump leaves D at source address 49. The later `j` at C=51
/// relocates from the no-op cell *at D=49*, not its own code character.
fn jump_then_relocation_operations() -> Vec<LinearOpcode> {
    (0..55usize)
        .map(|position| match position {
            0 => LinearOpcode::InputWord,
            48 => LinearOpcode::JumpForward { target: 51 },
            51 => LinearOpcode::RelocateDataPointer,
            52 => LinearOpcode::RotateData,
            53 => LinearOpcode::CrazyData,
            54 => LinearOpcode::Halt,
            _ => LinearOpcode::NoOperation,
        })
        .collect()
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "real VM/code/data witnesses are asserted"
)]
#[expect(
    clippy::cognitive_complexity,
    reason = "profile and jump-relocation invariants"
)]
fn forward_jump_then_relocated_arithmetic_reads_data_not_code() -> Result<(), String> {
    let operations = jump_then_relocation_operations();
    for profile in [current_profile(), historical_profile()] {
        let artifact = encode_linear_layout(profile, &operations)
            .map_err(|error| format!("jump then relocation: {error:?}"))?;
        assert_eq!(artifact.source().len(), 55);
        assert_eq!(artifact.source().get(49).copied(), Some(113));
        assert_ne!(artifact.source().get(51).copied(), Some(113));
        let relocation_step = artifact
            .executed_code_positions()
            .iter()
            .position(|address| *address == 51)
            .ok_or("missing reached j")?;
        assert_eq!(
            artifact.data_pointer_positions().get(relocation_step),
            Some(&49)
        );
        assert_eq!(
            artifact.data_pointer_positions().get(relocation_step + 1),
            Some(&114)
        );
        assert_eq!(artifact.executed_code_positions().last(), Some(&54));
        let mut machine = ProfileMachine::from_source(profile, artifact.source(), vec![0xa9])
            .map_err(|error| format!("jump-then-arithmetic VM: {error:?}"))?;
        verify_execution_witness(&mut machine, &artifact)?;
        assert_eq!(machine.input_consumed(), 1);
        assert!(machine.output().is_empty());
        assert_eq!(machine.registers().data_pointer, 116);
    }
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "XLAT2-mutated relocation base follows actual VM memory"
)]
fn relocation_reads_prior_jump_encrypted_data_word_and_rejects_overlap() -> Result<(), String> {
    let operations: Vec<LinearOpcode> = (0..62usize)
        .map(|position| match position {
            0 => LinearOpcode::InputWord,
            46 => LinearOpcode::JumpForward { target: 53 },
            58 => LinearOpcode::RelocateDataPointer,
            59 => LinearOpcode::RotateData,
            60 => LinearOpcode::CrazyData,
            61 => LinearOpcode::Halt,
            _ => LinearOpcode::NoOperation,
        })
        .collect();
    for profile in [current_profile(), historical_profile()] {
        let artifact = encode_linear_layout(profile, &operations)
            .map_err(|error| format!("encrypted data relocation: {error:?}"))?;
        assert_eq!(artifact.source().get(52).copied(), Some(110));
        assert_eq!(encrypt_profile_cell(110), Some(126));
        let relocation_step = artifact
            .executed_code_positions()
            .iter()
            .position(|address| *address == 58)
            .ok_or("missing reached j")?;
        assert_eq!(
            artifact.data_pointer_positions().get(relocation_step),
            Some(&52)
        );
        assert_eq!(
            artifact.data_pointer_positions().get(relocation_step + 1),
            Some(&127)
        );
        let mut machine = ProfileMachine::from_source(profile, artifact.source(), vec![0x37])
            .map_err(|error| format!("encrypted relocation VM: {error:?}"))?;
        verify_execution_witness(&mut machine, &artifact)?;
        assert_eq!(machine.input_consumed(), 1);
        // Inserting enough no-ops without changing any reached phase means
        // D=52 still holds encrypted 126, now overlapping source length 127.
        let mut too_long = operations.clone();
        *too_long.last_mut().ok_or("missing original halt")? = LinearOpcode::NoOperation;
        too_long.resize(126, LinearOpcode::NoOperation);
        too_long.push(LinearOpcode::Halt);
        assert_eq!(too_long.len(), 127);
        assert_eq!(
            encode_linear_layout(profile, &too_long),
            Err(LinearLayoutError::UnsafeDataPlacement)
        );
    }
    Ok(())
}

#[test]
fn reject_relocation_before_a_jump_and_inside_a_skipped_gap() {
    let profile = current_profile();
    let mut operations = jump_then_relocation_operations();
    if let Some(slot) = operations.get_mut(49) {
        *slot = LinearOpcode::RelocateDataPointer;
    }
    if let Some(slot) = operations.get_mut(51) {
        *slot = LinearOpcode::NoOperation;
    }
    assert_eq!(
        encode_linear_layout(profile, &operations),
        Err(LinearLayoutError::JumpPathUnsupported)
    );
    let mut reverse = jump_then_relocation_operations();
    if let Some(slot) = reverse.get_mut(48) {
        *slot = LinearOpcode::RelocateDataPointer;
    }
    if let Some(slot) = reverse.get_mut(51) {
        *slot = LinearOpcode::JumpForward { target: 53 };
    }
    assert_eq!(
        encode_linear_layout(profile, &reverse),
        Err(LinearLayoutError::JumpPathUnsupported)
    );
}

/// First jump encrypts cell 50, which supplies the second jump; the ordinary
/// no-op at 51 is encrypted too and supplies the later `j` relocation word.
fn two_jump_then_relocation_operations() -> Vec<LinearOpcode> {
    (0..73usize)
        .map(|position| match position {
            0 => LinearOpcode::InputWord,
            48 => LinearOpcode::JumpForward { target: 51 },
            52 => LinearOpcode::JumpForward { target: 69 },
            69 => LinearOpcode::RelocateDataPointer,
            70 => LinearOpcode::RotateData,
            71 => LinearOpcode::CrazyData,
            72 => LinearOpcode::Halt,
            _ => LinearOpcode::NoOperation,
        })
        .collect()
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "real VM proves chained code/data shadow state"
)]
#[expect(
    clippy::cognitive_complexity,
    reason = "two encrypted jump operands and data mutation"
)]
fn two_forward_jumps_then_relocation_consume_prior_xlat2_data() -> Result<(), String> {
    for profile in [current_profile(), historical_profile()] {
        let operations = two_jump_then_relocation_operations();
        let artifact = encode_linear_layout(profile, &operations)
            .map_err(|error| format!("chained jumps to relocation: {error:?}"))?;
        assert_eq!(artifact.source().get(50).copied(), Some(112));
        assert_eq!(artifact.source().get(51).copied(), Some(111));
        assert_eq!(encrypt_profile_cell(112), Some(68));
        assert_eq!(encrypt_profile_cell(111), Some(120));
        let second_jump = artifact
            .executed_code_positions()
            .iter()
            .position(|address| *address == 52)
            .ok_or("missing second jump")?;
        let relocation = artifact
            .executed_code_positions()
            .iter()
            .position(|address| *address == 69)
            .ok_or("missing relocation")?;
        assert_eq!(
            artifact.data_pointer_positions().get(second_jump),
            Some(&50)
        );
        assert_eq!(artifact.data_pointer_positions().get(relocation), Some(&51));
        assert_eq!(
            artifact.data_pointer_positions().get(relocation + 1),
            Some(&121)
        );
        assert_eq!(artifact.data_write_positions().get(relocation), Some(&None));
        assert_eq!(
            artifact.data_write_positions().get(relocation + 1),
            Some(&Some(121))
        );
        assert_eq!(
            artifact.data_write_positions().get(relocation + 2),
            Some(&Some(122))
        );
        let mut vm = ProfileMachine::from_source(profile, artifact.source(), vec![0x7d])
            .map_err(|error| format!("chained jump-relocation VM: {error:?}"))?;
        verify_execution_witness(&mut vm, &artifact)?;
        assert_eq!(vm.input_consumed(), 1);
        assert!(vm.output().is_empty());
        assert_eq!(vm.registers().data_pointer, 123);
    }
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "automatic destination and skipped no-ops are checked by normative VM"
)]
fn auto_padding_first_forward_jump_produces_exact_vm_jump_path() -> Result<(), String> {
    use PaddedForwardStep::{Instruction, Jump};
    let logical = [
        Jump,
        Instruction(LinearOpcode::InputWord),
        Instruction(LinearOpcode::OutputByte),
        Instruction(LinearOpcode::Halt),
    ];
    for profile in [current_profile(), historical_profile()] {
        let expanded = encode_auto_padded_forward_layout(profile, &logical)
            .map_err(|error| format!("auto first jump: {error:?}"))?;
        verify_bidirectional_source_map(&expanded)?;
        assert_eq!(
            expanded.source_cell_origins().get(1),
            Some(&PaddedCellOrigin::SkippedPadding)
        );
        let dest = jump_target(0)?;
        assert_eq!(
            expanded.logical_code_positions(),
            &[0, dest, dest.saturating_add(1), dest.saturating_add(2)]
        );
        assert_eq!(
            expanded.operations().len(),
            usize::try_from(dest).unwrap_or_default().saturating_add(3)
        );
        assert_eq!(
            expanded.operations().first(),
            Some(&LinearOpcode::JumpForward { target: dest })
        );
        let skipped = expanded
            .operations()
            .get(1..usize::try_from(dest).unwrap_or_default())
            .ok_or("missing auto-generated gap")?;
        assert!(
            skipped
                .iter()
                .all(|operation| *operation == LinearOpcode::NoOperation)
        );
        let independent = encode_linear_layout(profile, expanded.operations())
            .map_err(|error| format!("independent auto re-admission: {error:?}"))?;
        assert_eq!(expanded.layout(), &independent);
        let mut vm = ProfileMachine::from_source(profile, independent.source(), vec![0xe1])
            .map_err(|error| format!("auto first jump VM: {error:?}"))?;
        verify_execution_witness(&mut vm, &independent)?;
        assert_eq!(vm.output(), &[0xe1]);
        assert_eq!(vm.input_consumed(), 1);
    }
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "two jumps and relocated arithmetic are independently checked"
)]
#[expect(
    clippy::cognitive_complexity,
    reason = "multiple code/data transitions require exact physical address assertions"
)]
fn auto_padding_two_hop_jump_then_relocation_matches_manual_vm_source() -> Result<(), String> {
    use PaddedForwardStep::{Instruction, Jump};
    let mut logical = vec![Instruction(LinearOpcode::InputWord)];
    logical.resize(48, Instruction(LinearOpcode::NoOperation));
    logical.extend([
        Jump,
        Instruction(LinearOpcode::NoOperation),
        Jump,
        Instruction(LinearOpcode::RelocateDataPointer),
        Instruction(LinearOpcode::RotateData),
        Instruction(LinearOpcode::CrazyData),
        Instruction(LinearOpcode::Halt),
    ]);
    for profile in [current_profile(), historical_profile()] {
        let expanded = encode_auto_padded_forward_layout(profile, &logical)
            .map_err(|error| format!("two-jump automatic planning: {error:?}"))?;
        verify_bidirectional_source_map(&expanded)?;
        assert_eq!(
            expanded.source_cell_origins().get(49),
            Some(&PaddedCellOrigin::SkippedPadding)
        );
        assert_eq!(expanded.logical_code_positions().get(48), Some(&48));
        assert_eq!(expanded.logical_code_positions().get(49), Some(&51));
        assert_eq!(expanded.logical_code_positions().get(50), Some(&52));
        assert_eq!(expanded.logical_code_positions().get(51), Some(&69));
        assert_eq!(expanded.logical_code_positions().last(), Some(&72));
        assert_eq!(expanded.operations(), two_jump_then_relocation_operations());
        let expected = encode_linear_layout(profile, &two_jump_then_relocation_operations())
            .map_err(|error| format!("manual fixture re-encoding: {error:?}"))?;
        assert_eq!(expanded.layout(), &expected);
        let mut vm = ProfileMachine::from_source(profile, expanded.layout().source(), vec![0x5f])
            .map_err(|error| format!("auto double-jump real VM: {error:?}"))?;
        verify_execution_witness(&mut vm, expanded.layout())?;
        assert_eq!(vm.input_consumed(), 1);
        assert_eq!(vm.registers().data_pointer, 123);
    }
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "self-modified triple-jump source is compared against the real VM"
)]
fn auto_padding_three_hops_reuses_xlat2_encrypted_operands() -> Result<(), String> {
    use PaddedForwardStep::{Instruction, Jump};
    let mut logical = vec![Instruction(LinearOpcode::InputWord)];
    logical.resize(26, Instruction(LinearOpcode::NoOperation));
    logical.push(Jump);
    logical.resize(
        logical.len().saturating_add(29),
        Instruction(LinearOpcode::NoOperation),
    );
    logical.push(Jump);
    logical.resize(
        logical.len().saturating_add(15),
        Instruction(LinearOpcode::NoOperation),
    );
    logical.extend([
        Jump,
        Instruction(LinearOpcode::OutputByte),
        Instruction(LinearOpcode::Halt),
    ]);
    for profile in [current_profile(), historical_profile()] {
        let artifact = encode_auto_padded_forward_layout(profile, &logical)
            .map_err(|error| format!("three jumps auto layout: {error:?}"))?;
        assert_eq!(artifact.operations().len(), 127);
        let explicit = encode_linear_layout(profile, &{
            (0..127usize)
                .map(|position| match position {
                    0 => LinearOpcode::InputWord,
                    26 => LinearOpcode::JumpForward { target: 73 },
                    102 => LinearOpcode::JumpForward { target: 107 },
                    122 => LinearOpcode::JumpForward { target: 125 },
                    125 => LinearOpcode::OutputByte,
                    126 => LinearOpcode::Halt,
                    _ => LinearOpcode::NoOperation,
                })
                .collect::<Vec<_>>()
        })
        .map_err(|error| format!("three-jump manual plan: {error:?}"))?;
        assert_eq!(artifact.layout(), &explicit);
        let mut vm = ProfileMachine::from_source(profile, artifact.layout().source(), vec![0x91])
            .map_err(|error| format!("three-jump auto VM: {error:?}"))?;
        verify_execution_witness(&mut vm, artifact.layout())?;
        assert_eq!(vm.output(), &[0x91]);
    }
    Ok(())
}

#[test]
fn auto_padding_rejects_nonforward_and_hostile_logical_plans() {
    use PaddedForwardStep::{Instruction, Jump};
    let profile = current_profile();
    assert_eq!(
        encode_auto_padded_forward_layout(profile, &[Jump]),
        Err(LinearLayoutError::TooShort)
    );
    assert_eq!(
        encode_auto_padded_forward_layout(profile, &[Instruction(LinearOpcode::InputWord), Jump,]),
        Err(LinearLayoutError::MissingHalt)
    );
    assert_eq!(
        encode_auto_padded_forward_layout(
            profile,
            &[
                Instruction(LinearOpcode::JumpForward { target: 100 }),
                Instruction(LinearOpcode::Halt),
            ]
        ),
        Err(LinearLayoutError::JumpPathUnsupported)
    );
    assert_eq!(
        encode_auto_padded_forward_layout(
            profile,
            &[
                Instruction(LinearOpcode::RelocateDataPointer),
                Jump,
                Instruction(LinearOpcode::Halt),
            ]
        ),
        Err(LinearLayoutError::JumpPathUnsupported)
    );
    assert_eq!(
        encode_auto_padded_forward_layout(
            profile,
            &[
                Instruction(LinearOpcode::Halt),
                Instruction(LinearOpcode::NoOperation),
                Instruction(LinearOpcode::Halt),
            ]
        ),
        Err(LinearLayoutError::EarlyHalt { position: 0 })
    );
    let mut plan = vec![Instruction(LinearOpcode::NoOperation); 127];
    plan.extend([Jump, Instruction(LinearOpcode::Halt)]);
    assert_eq!(
        encode_auto_padded_forward_layout(profile, &plan),
        Err(LinearLayoutError::JumpPathUnsupported)
    );
    let oversized = vec![Instruction(LinearOpcode::NoOperation); 4097];
    assert_eq!(
        encode_auto_padded_forward_layout(profile, &oversized),
        Err(LinearLayoutError::TooLong)
    );
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "all 94 graphical phases are independently inverted and checked"
)]
#[expect(
    clippy::cognitive_complexity,
    reason = "exhaustive expected success/failure and re-admission matrix"
)]
fn auto_padding_matches_all_first_jump_decoder_phases() -> Result<(), String> {
    use PaddedForwardStep::{Instruction, Jump};
    for profile in [current_profile(), historical_profile()] {
        let mut admitted = 0usize;
        let mut rejected = 0usize;
        for phase in 0..94usize {
            let mut logical = vec![Instruction(LinearOpcode::NoOperation); phase];
            logical.extend([
                Jump,
                Instruction(LinearOpcode::OutputByte),
                Instruction(LinearOpcode::Halt),
            ]);
            let jump_pos = u32::try_from(phase).map_err(|error| error.to_string())?;
            let target = jump_target(jump_pos)?;
            let result = encode_auto_padded_forward_layout(profile, &logical);
            if target <= jump_pos.saturating_add(1) {
                assert_eq!(result, Err(LinearLayoutError::JumpPathUnsupported));
                rejected = rejected.saturating_add(1);
                continue;
            }
            let admitted_layout =
                result.map_err(|error| format!("expected phase {phase} to admit: {error:?}"))?;
            assert_eq!(
                admitted_layout.logical_code_positions().get(phase),
                Some(&jump_pos)
            );
            assert_eq!(
                admitted_layout.logical_code_positions().get(phase + 1),
                Some(&target)
            );
            assert_eq!(
                admitted_layout.logical_code_positions().last(),
                Some(&target.saturating_add(1))
            );
            assert_eq!(
                admitted_layout.layout(),
                &encode_linear_layout(profile, admitted_layout.operations())
                    .map_err(|error| format!("phase {phase} admission: {error:?}"))?
            );
            admitted = admitted.saturating_add(1);
        }
        assert!(admitted > 0);
        assert!(rejected > 0);
        assert_eq!(admitted.saturating_add(rejected), 94);
    }
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "auto-chosen safe relocation and real data mutations are independently checked"
)]
#[expect(
    clippy::cognitive_complexity,
    reason = "VM data changes and exact origins must hold under both profiles"
)]
fn auto_relocation_finds_first_safe_decoder_phase_for_long_tail() -> Result<(), String> {
    use PaddedForwardStep::{AutoRelocate, Instruction};
    let mut logical = vec![AutoRelocate];
    logical.resize(45, Instruction(LinearOpcode::NoOperation));
    logical.extend([
        Instruction(LinearOpcode::RotateData),
        Instruction(LinearOpcode::CrazyData),
        Instruction(LinearOpcode::Halt),
    ]);
    for profile in [current_profile(), historical_profile()] {
        let artifact = encode_auto_padded_forward_layout(profile, &logical)
            .map_err(|error| format!("automatic data relocation: {error:?}"))?;
        verify_bidirectional_source_map(&artifact)?;
        assert!(
            artifact
                .source_cell_origins()
                .get(..8)
                .ok_or("auto relocation prefix missing")?
                .iter()
                .all(|origin| *origin == PaddedCellOrigin::ExecutedPadding)
        );
        assert_eq!(artifact.logical_code_positions().first(), Some(&8));
        assert_eq!(artifact.logical_code_positions().last(), Some(&55));
        assert_eq!(artifact.operations().len(), 56);
        assert!(
            artifact
                .operations()
                .get(..8)
                .ok_or("missing prefix")?
                .iter()
                .all(|operation| *operation == LinearOpcode::NoOperation)
        );
        assert_eq!(
            artifact.operations().get(8),
            Some(&LinearOpcode::RelocateDataPointer)
        );
        assert_eq!(artifact.layout().source().get(8).copied(), Some(126));
        assert_eq!(
            artifact
                .layout()
                .data_write_positions()
                .iter()
                .filter(|address| address.is_some())
                .count(),
            2
        );
        let manual = encode_linear_layout(profile, artifact.operations())
            .map_err(|error| format!("manual relocation re-admission: {error:?}"))?;
        assert_eq!(artifact.layout(), &manual);
        let mut vm = ProfileMachine::from_source(profile, manual.source(), Vec::new())
            .map_err(|error| format!("real auto relocation loader: {error:?}"))?;
        verify_execution_witness(&mut vm, &manual)?;
    }
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "auto relocation after two self-modifying jumps exactly matches VM"
)]
fn auto_relocation_after_two_jumps_uses_modified_data_operand() -> Result<(), String> {
    use PaddedForwardStep::{AutoRelocate, Instruction, Jump};
    let mut logical = vec![Instruction(LinearOpcode::InputWord)];
    logical.resize(48, Instruction(LinearOpcode::NoOperation));
    logical.extend([
        Jump,
        Instruction(LinearOpcode::NoOperation),
        Jump,
        AutoRelocate,
        Instruction(LinearOpcode::RotateData),
        Instruction(LinearOpcode::CrazyData),
        Instruction(LinearOpcode::Halt),
    ]);
    for profile in [current_profile(), historical_profile()] {
        let artifact = encode_auto_padded_forward_layout(profile, &logical)
            .map_err(|error| format!("automatic jump+relocation: {error:?}"))?;
        verify_bidirectional_source_map(&artifact)?;
        assert_eq!(artifact.logical_code_positions().get(51), Some(&69));
        let explicit = encode_linear_layout(profile, &two_jump_then_relocation_operations())
            .map_err(|error| format!("manual two jump relocate: {error:?}"))?;
        assert_eq!(artifact.layout(), &explicit);
        let mut vm = ProfileMachine::from_source(profile, artifact.layout().source(), vec![0x5a])
            .map_err(|error| format!("auto jump+relocation VM: {error:?}"))?;
        verify_execution_witness(&mut vm, artifact.layout())?;
        assert_eq!(vm.input_consumed(), 1);
    }
    Ok(())
}

#[test]
fn auto_relocation_rejects_unsafe_capacity_and_duplicate_data_moves() {
    use PaddedForwardStep::{AutoRelocate, Instruction, Jump};
    let profile = current_profile();
    let mut insufficient = vec![AutoRelocate];
    insufficient.resize(127, Instruction(LinearOpcode::NoOperation));
    insufficient.push(Instruction(LinearOpcode::Halt));
    assert_eq!(
        encode_auto_padded_forward_layout(profile, &insufficient),
        Err(LinearLayoutError::UnsafeDataPlacement)
    );
    assert_eq!(
        encode_auto_padded_forward_layout(
            profile,
            &[
                Instruction(LinearOpcode::RelocateDataPointer),
                AutoRelocate,
                Instruction(LinearOpcode::Halt),
            ]
        ),
        Err(LinearLayoutError::UnsafeDataPlacement)
    );
    assert_eq!(
        encode_auto_padded_forward_layout(
            profile,
            &[AutoRelocate, Jump, Instruction(LinearOpcode::Halt),]
        ),
        Err(LinearLayoutError::JumpPathUnsupported)
    );
}

/// An independent scalar trit-table oracle for the guest `p` operation.
/// Keep this deliberately separate from the VM's chunked crazy lookup.
#[expect(
    clippy::integer_division_remainder_used,
    reason = "base-three quotient and remainder are the independent scalar trit oracle"
)]
fn scalar_crazy_reference(mut data: u32, mut accumulator: u32, trits: u8) -> u32 {
    const CRAZY: [[u32; 3]; 3] = [[1, 0, 0], [1, 0, 2], [2, 2, 1]];
    let mut place = 1u32;
    let mut result = 0u32;
    for _trit in 0..trits {
        let data_digit = usize::try_from(data % 3).unwrap_or_default();
        let acc_digit = usize::try_from(accumulator % 3).unwrap_or_default();
        let digit = CRAZY
            .get(data_digit)
            .and_then(|row| row.get(acc_digit))
            .copied()
            .unwrap_or_default();
        result = result.saturating_add(digit.saturating_mul(place));
        place = place.saturating_mul(3);
        data /= 3;
        accumulator /= 3;
    }
    result
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "the target VM must perform both real data operations for each input"
)]
#[expect(
    clippy::integer_division,
    clippy::integer_division_remainder_used,
    reason = "independent ternary rotate and low-byte oracle requires exact integer math"
)]
#[expect(
    clippy::too_many_lines,
    reason = "exact VM/data/byte outputs are compared across both profiles and 40 inputs"
)]
fn auto_relocation_guest_crazy_and_rotate_compute_independent_output() -> Result<(), String> {
    use PaddedForwardStep::{AutoRelocate, Instruction};
    let logical = [
        Instruction(LinearOpcode::InputWord),
        AutoRelocate,
        Instruction(LinearOpcode::CrazyData),
        Instruction(LinearOpcode::OutputByte),
        Instruction(LinearOpcode::RotateData),
        Instruction(LinearOpcode::OutputByte),
        Instruction(LinearOpcode::Halt),
    ];
    for profile in [current_profile(), historical_profile()] {
        let artifact = encode_auto_padded_forward_layout(profile, &logical)
            .map_err(|error| format!("guest ternary arithmetic layout: {error:?}"))?;
        verify_bidirectional_source_map(&artifact)?;
        let layout = artifact.layout();
        assert_eq!(artifact.logical_code_positions(), &[0, 1, 2, 3, 4, 5, 6]);
        assert_eq!(
            layout.data_write_positions(),
            &[None, None, Some(40), None, Some(42), None, None,]
        );
        let pristine = ProfileMachine::from_source(profile, layout.source(), Vec::new())
            .map_err(|error| format!("guest ternary VM initial load: {error:?}"))?;
        // A canonical source image is input-independent. Rebuild each fresh
        // VM through its checked full-state constructor rather than repeat
        // the large ternary memory recurrence for each input byte.
        // Exercise the low five bits exhaustively and both sides of the
        // byte sign/high-bit boundaries without 512 full-state VM rebuilds.
        let cases = (0u8..=31).chain([63, 64, 127, 128, 191, 192, 254, 255]);
        for input in cases {
            let mut vm = ProfileMachine::from_state(
                profile,
                pristine.memory().to_vec(),
                vec![input],
                ProfileRegisters::default(),
            )
            .map_err(|error| format!("guest ternary VM state load: {error:?}"))?;
            let initial_crazy_word = vm
                .memory_word(40)
                .map_err(|error| format!("initial crazy data: {error:?}"))?;
            let initial_rotate_word = vm
                .memory_word(42)
                .map_err(|error| format!("initial rotate data: {error:?}"))?;
            let expected_crazy =
                scalar_crazy_reference(initial_crazy_word, u32::from(input), profile.word_trits());
            let expected_rotate =
                initial_rotate_word / 3 + (initial_rotate_word % 3) * (profile.word_modulus() / 3);
            verify_execution_witness(&mut vm, layout)?;
            assert_eq!(vm.input_consumed(), 1);
            assert_eq!(
                vm.output(),
                &[
                    u8::try_from(expected_crazy % 256).map_err(|error| error.to_string())?,
                    u8::try_from(expected_rotate % 256).map_err(|error| error.to_string())?,
                ]
            );
            assert_eq!(
                vm.memory_word(40)
                    .map_err(|error| format!("crazy memory result: {error:?}"))?,
                expected_crazy
            );
            assert_eq!(
                vm.memory_word(42)
                    .map_err(|error| format!("rotated memory result: {error:?}"))?,
                expected_rotate
            );
        }
    }
    Ok(())
}

/// Independent first-fit oracle for one `j` whose D remains equal to C.
/// For an unchanged NOP prefix, the instruction reads its own graphical
/// byte, which must exceed the **complete** final code boundary.
fn expected_auto_relocation_phase(suffix_nops: usize) -> Result<Option<usize>, String> {
    for phase in 0..94usize {
        let address = u32::try_from(phase).map_err(|error| error.to_string())?;
        let byte = (33u8..=126)
            .find(|byte| decode_profile_instruction(u32::from(*byte), address) == Some(b'j'))
            .ok_or("missing normative j decoder phase")?;
        let full_length = phase.saturating_add(suffix_nops).saturating_add(2);
        if usize::from(byte) >= full_length {
            return Ok(Some(phase));
        }
    }
    Ok(None)
}

#[expect(
    clippy::panic_in_result_fn,
    reason = "test helper intentionally asserts each first-fit source-map invariant"
)]
fn assert_auto_relocation_suffix(
    profile: &'static malbolge::ProfileDescriptor,
    suffix_nops: usize,
) -> Result<bool, String> {
    use PaddedForwardStep::{AutoRelocate, Instruction};
    let mut logical = vec![AutoRelocate];
    logical.resize(
        suffix_nops.saturating_add(1),
        Instruction(LinearOpcode::NoOperation),
    );
    logical.push(Instruction(LinearOpcode::Halt));
    let expected = expected_auto_relocation_phase(suffix_nops)?;
    let result = encode_auto_padded_forward_layout(profile, &logical);
    let Some(phase) = expected else {
        assert_eq!(
            result,
            Err(LinearLayoutError::UnsafeDataPlacement),
            "impossible relocation must refuse source overlap"
        );
        return Ok(false);
    };
    let layout = result.map_err(|error| {
        format!(
            "{} with {suffix_nops} source nop cells: {error:?}",
            profile.id(),
        )
    })?;
    let code = u32::try_from(phase).map_err(|error| error.to_string())?;
    assert_eq!(
        layout.logical_code_positions().first(),
        Some(&code),
        "symbolic relocation target is not the earliest safe decoder phase"
    );
    assert_eq!(
        layout.source_cell_origins().get(phase),
        Some(&PaddedCellOrigin::Logical(0)),
        "source cell origin lost the logical relocation",
    );
    assert_eq!(
        layout.operations().get(phase),
        Some(&LinearOpcode::RelocateDataPointer),
        "selected source phase does not contain the requested relocation",
    );
    assert_eq!(
        layout.operations().len(),
        phase.saturating_add(suffix_nops).saturating_add(2),
        "emitter did not account for the entire post-relocation source",
    );
    assert_eq!(
        layout.layout().data_pointer_positions().get(phase),
        Some(&code),
        "D must equal C before the first explicit relocation",
    );
    Ok(true)
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "all accepted and impossible placement boundaries are asserted"
)]
fn auto_relocate_first_fit_matches_all_profile_decoder_phases_and_suffix_sizes()
-> Result<(), String> {
    let profiles = [
        historical_profile(),
        current_profile(),
        target_profile("malbolge-2026.1").ok_or("missing 2026.1")?,
        target_profile("malbolge-2026.2").ok_or("missing 2026.2")?,
        target_profile("malbolge-2026.3").ok_or("missing 2026.3")?,
    ];
    let mut accepted = 0usize;
    let mut rejected = 0usize;
    for profile in profiles {
        for suffix_nops in 0..=130usize {
            if assert_auto_relocation_suffix(profile, suffix_nops)? {
                accepted = accepted.saturating_add(1);
            } else {
                rejected = rejected.saturating_add(1);
            }
        }
    }
    assert!(accepted > 0);
    assert!(rejected > 0);
    assert_eq!(accepted.saturating_add(rejected), 655);
    Ok(())
}
