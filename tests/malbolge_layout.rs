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
//   - No claims about full ternary IR, jumps, or live self-modifying code.
//

//! Independent verifier and executable VM evidence for linear Malbolge code.

#[path = "../src/compiler/malbolge-layout/composition/lib.rs"]
pub mod layout;

use layout::{
    LinearLayout, LinearLayoutError, LinearOpcode, LinearProfileIdentity, admit_linear_layout,
    encode_linear_layout,
};
use malbolge::{
    ProfileMachine, RunOutcome, current_profile, decode_profile_instruction, encrypt_profile_cell,
    historical_profile,
};

fn verify_execution_witness(
    machine: &mut ProfileMachine,
    layout: &LinearLayout,
) -> Result<(), String> {
    for (step, &code) in layout.executed_code_positions().iter().enumerate() {
        if machine.registers().code_pointer != code {
            return Err(String::from("runtime code path differs from layout proof"));
        }
        let target = layout.encrypted_code_positions().get(step).copied();
        let before = target
            .map(|address| machine.memory_word(address))
            .transpose()
            .map_err(|error| format!("before encryption: {error:?}"))?;
        let _outcome: malbolge::StepOutcome = machine
            .step()
            .map_err(|error| format!("layout execution: {error:?}"))?;
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
