// Copyright:
//   - Copyright © 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - LicenseRef-Proprietary
// Confidential:
//   - true
// License-File:
//   - LICENSE
//
// Boundary-Contract:
// - Owns:
//   - Source-scratch data writes safely behind forward-only guest code.
// - Must-Not:
//   - Permit writes to pending instructions or falsify output/VM state.
// - Allows:
//   - Inputs: encoded graphical cells and a forward-jump machine trace.
//   - Outputs: exact in-source write positions and actual guest bytes.
//   - Side effects: bounded normative VM replays only.
// - Split-When:
//   - General self-modifying code placement has its own verifier.
// - Merge-When:
//   - A general layout verifier models source/data aliasing completely.
// - Summary:
//   - Writes to skipped, past source cells do not corrupt future code.

use super::*;

fn scratch_guest() -> Result<Vec<LinearOpcode>, String> {
    let target =
        usize::try_from(jump_target(0)?).map_err(|error| error.to_string())?;
    if target <= 5 {
        return Err(String::from("forward jump leaves insufficient scratch"));
    }
    let mut operations = vec![LinearOpcode::NoOperation; target + 5];
    operations[0] = LinearOpcode::JumpForward {
        target: u32::try_from(target).map_err(|error| error.to_string())?,
    };
    operations[target] = LinearOpcode::CrazyData;
    operations[target + 1] = LinearOpcode::OutputByte;
    operations[target + 2] = LinearOpcode::RotateData;
    operations[target + 3] = LinearOpcode::OutputByte;
    operations[target + 4] = LinearOpcode::Halt;
    Ok(operations)
}

#[test]
fn forward_jump_allows_source_scratch_arithmetic_behind_code()
-> Result<(), String> {
    let operations = scratch_guest()?;
    for profile in [current_profile(), historical_profile()] {
        let layout = encode_linear_layout(profile, &operations)
            .map_err(|error| format!("source-scratch layout: {error:?}"))?;
        assert_eq!(layout.data_write_positions()[1], Some(1));
        assert_eq!(layout.data_write_positions()[3], Some(3));
        assert_eq!(layout.executed_code_positions().len(), 6);
        let source = layout.source().to_vec();
        let first = malbolge::profile_crazy(
            u32::from(source[1]),
            0,
            profile.word_trits(),
        );
        let third = u32::from(source[3]);
        let rotated = third / 3
            + (third % 3) * (3u32.pow(u32::from(profile.word_trits()) - 1));
        let expected = [first as u8, rotated as u8];
        for input in [Vec::new(), vec![0, 255, 42]] {
            let mut vm = ProfileMachine::from_source(profile, &source, input)
                .map_err(|error| {
                format!("source-scratch VM load: {error:?}")
            })?;
            assert!(matches!(
                vm.run(6),
                Ok(RunOutcome::Terminated { steps: 6, .. })
            ));
            assert_eq!(vm.output(), expected);
            assert_eq!(vm.input_consumed(), 0);
            assert_ne!(
                vm.memory_word(1)
                    .map_err(|error| format!("scratch write: {error:?}"))?,
                u32::from(source[1])
            );
        }
        let mut forged = source.clone();
        forged[1] ^= 1;
        assert!(matches!(
            admit_linear_layout(
                profile,
                &operations,
                &forged,
                LinearProfileIdentity {
                    id: profile.id(),
                    fingerprint: profile.fingerprint(),
                },
            ),
            Err(LinearLayoutError::DecodeMismatch { position: 1 })
        ));
    }
    Ok(())
}

fn replace_scratch_operation(
    operations: &mut [LinearOpcode],
    index: usize,
    operation: LinearOpcode,
) -> Result<(), String> {
    *operations.get_mut(index).ok_or("missing scratch cell")? = operation;
    Ok(())
}

#[test]
fn input_dependent_source_scratch_runs_in_both_normative_vms()
-> Result<(), String> {
    let target =
        usize::try_from(jump_target(0)?).map_err(|error| error.to_string())?;
    let mut operations = vec![LinearOpcode::NoOperation; target + 4];
    replace_scratch_operation(&mut operations, 0, LinearOpcode::JumpForward {
        target: u32::try_from(target).map_err(|error| error.to_string())?,
    })?;
    replace_scratch_operation(
        &mut operations,
        target,
        LinearOpcode::InputWord,
    )?;
    replace_scratch_operation(
        &mut operations,
        target + 1,
        LinearOpcode::CrazyData,
    )?;
    replace_scratch_operation(
        &mut operations,
        target + 2,
        LinearOpcode::OutputByte,
    )?;
    replace_scratch_operation(&mut operations, target + 3, LinearOpcode::Halt)?;
    for profile in [current_profile(), historical_profile()] {
        let layout = encode_linear_layout(profile, &operations)
            .map_err(|error| format!("input scratch layout: {error:?}"))?;
        if layout.data_write_positions() != [None, None, Some(2), None, None] {
            return Err(String::from("wrong input scratch write address"));
        }
        let source_word =
            u32::from(*layout.source().get(2).ok_or("scratch word")?);
        let mut observed = Vec::new();
        for input in [0u8, 255] {
            let expected = scalar_crazy_reference(
                source_word,
                u32::from(input),
                profile.word_trits(),
            );
            let mut vm =
                ProfileMachine::from_source(profile, layout.source(), vec![
                    input,
                ])
                .map_err(|error| format!("input scratch VM load: {error:?}"))?;
            verify_execution_witness(&mut vm, &layout)?;
            let expected_byte = u8::try_from(expected & 255)
                .map_err(|error| error.to_string())?;
            if vm.input_consumed() != 1
                || vm.output() != [expected_byte]
                || vm.memory_word(2) != Ok(expected)
            {
                return Err(String::from("input scratch VM effects differ"));
            }
            observed.push(expected);
        }
        if observed.first() == observed.get(1) {
            return Err(String::from("different inputs had identical writes"));
        }
    }
    Ok(())
}

// A forward jump after relocation is safe when its operand remains a known
// source cell behind C, even after an input-derived p writes a different cell.
fn post_relocation_jump_operations() -> Result<Vec<LinearOpcode>, String> {
    let target = jump_target(0)?;
    if target != 99 {
        return Err(String::from("unexpected first jump decoder phase"));
    }
    let mut operations = vec![LinearOpcode::NoOperation; 127];
    for (index, operation) in [
        (0, LinearOpcode::JumpForward { target }),
        (2, LinearOpcode::SkippedDataByte { byte: 66 }),
        (68, LinearOpcode::SkippedDataByte { byte: 124 }),
        (99, LinearOpcode::InputWord),
        (100, LinearOpcode::RelocateDataPointer),
        (101, LinearOpcode::CrazyData),
        (102, LinearOpcode::JumpForward { target: 125 }),
        (125, LinearOpcode::OutputByte),
        (126, LinearOpcode::Halt),
    ] {
        replace_scratch_operation(&mut operations, index, operation)?;
    }
    Ok(operations)
}

fn refuse_unproven_post_relocation_jumps(
    profile: &'static malbolge::ProfileDescriptor,
    operations: &[LinearOpcode],
) -> Result<(), String> {
    // Returning D to input-written scratch makes the jump target unknown.
    let mut tainted_jump = operations.to_vec();
    for (index, operation) in [
        (68, LinearOpcode::SkippedDataByte { byte: 66 }),
        (102, LinearOpcode::RelocateDataPointer),
        (103, LinearOpcode::JumpForward { target: 125 }),
    ] {
        replace_scratch_operation(&mut tainted_jump, index, operation)?;
    }
    if encode_linear_layout(profile, &tainted_jump)
        != Err(LinearLayoutError::JumpPathUnsupported)
    {
        return Err(String::from("tainted post-relocation jump admitted"));
    }
    let mut incorrect_target = operations.to_vec();
    replace_scratch_operation(
        &mut incorrect_target,
        102,
        LinearOpcode::JumpForward { target: 124 },
    )?;
    if encode_linear_layout(profile, &incorrect_target)
        != Err(LinearLayoutError::JumpTargetMismatch { position: 102 })
    {
        return Err(String::from("forged post-relocation jump admitted"));
    }
    Ok(())
}

#[test]
fn post_relocation_jump_uses_unmodified_source_operand_after_guest_write()
-> Result<(), String> {
    let operations = post_relocation_jump_operations()?;
    for profile in [current_profile(), historical_profile()] {
        let layout = encode_linear_layout(profile, &operations)
            .map_err(|error| format!("post-relocation jump: {error:?}"))?;
        if layout.executed_code_positions() != [0, 99, 100, 101, 102, 125, 126]
            || layout.data_write_positions()
                != [None, None, None, Some(67), None, None, None]
        {
            return Err(String::from("incorrect post-relocation witness"));
        }
        let original = u32::from(
            *layout.source().get(67).ok_or("missing scratch operand")?,
        );
        for input in [0u8, 255] {
            let expected = scalar_crazy_reference(
                original,
                u32::from(input),
                profile.word_trits(),
            );
            let mut vm =
                ProfileMachine::from_source(profile, layout.source(), vec![
                    input,
                ])
                .map_err(|error| format!("post-relocation VM: {error:?}"))?;
            verify_execution_witness(&mut vm, &layout)?;
            let expected_byte = u8::try_from(expected & 255)
                .map_err(|error| error.to_string())?;
            if vm.input_consumed() != 1
                || vm.output() != [expected_byte]
                || vm.memory_word(67) != Ok(expected)
                || vm.memory_word(68) != Ok(124)
            {
                return Err(String::from(
                    "post-relocation guest effects differ",
                ));
            }
        }
        refuse_unproven_post_relocation_jumps(profile, &operations)?;
    }
    Ok(())
}

// A reached j at phase eight moves D to address 127, beyond the whole
// 44-cell source. The canonical loader recurrence places word 38 there, so
// the following i must jump to code 39 rather than guess from its own cell.
fn expanded_loader_jump_operations() -> Result<Vec<LinearOpcode>, String> {
    let mut operations = vec![LinearOpcode::NoOperation; 44];
    for (index, operation) in [
        (8, LinearOpcode::RelocateDataPointer),
        (9, LinearOpcode::JumpForward { target: 39 }),
        (39, LinearOpcode::InputWord),
        (40, LinearOpcode::OutputByte),
        (43, LinearOpcode::Halt),
    ] {
        replace_scratch_operation(&mut operations, index, operation)?;
    }
    Ok(operations)
}

#[test]
fn expanded_loader_jump_reads_unmodified_guest_memory() -> Result<(), String> {
    let operations = expanded_loader_jump_operations()?;
    for profile in [current_profile(), historical_profile()] {
        let layout = encode_linear_layout(profile, &operations)
            .map_err(|error| format!("expanded jump layout: {error:?}"))?;
        if layout.source().get(8) != Some(&126)
            || layout.source().get(42..) != Some([120, 38].as_slice())
            || layout.data_pointer_positions().get(9) != Some(&127)
            || layout.executed_code_positions()
                != [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 39, 40, 41, 42, 43]
        {
            return Err(String::from("unexpected expanded jump geometry"));
        }
        // Independently replay the scalar trit recurrence from the exact
        // two graphical tail cells, without using the encoder's shortcut.
        let mut previous =
            u32::from(*layout.source().get(42).ok_or("loader tail first")?);
        let mut latest =
            u32::from(*layout.source().get(43).ok_or("loader tail last")?);
        for _address in 44u32..=127u32 {
            let next =
                scalar_crazy_reference(previous, latest, profile.word_trits());
            previous = latest;
            latest = next;
        }
        if latest != 38 {
            return Err(String::from("scalar loader jump oracle differs"));
        }
        for input in [0u8, 255] {
            let mut vm =
                ProfileMachine::from_source(profile, layout.source(), vec![
                    input,
                ])
                .map_err(|error| format!("expanded jump guest: {error:?}"))?;
            if vm.memory_word(127) != Ok(latest) {
                return Err(String::from(
                    "loader jump word differs from oracle",
                ));
            }
            verify_execution_witness(&mut vm, &layout)?;
            if vm.input_consumed() != 1 || vm.output() != [input] {
                return Err(String::from("expanded jump guest I/O differs"));
            }
        }
        let mut wrong = operations.clone();
        replace_scratch_operation(&mut wrong, 9, LinearOpcode::JumpForward {
            target: 38,
        })?;
        if encode_linear_layout(profile, &wrong)
            != Err(LinearLayoutError::JumpTargetMismatch { position: 9 })
        {
            return Err(String::from("forged expanded target was admitted"));
        }
    }
    Ok(())
}

#[test]
#[expect(
    clippy::too_many_lines,
    reason = "traced two-profile guest safety witness"
)]
fn input_written_expanded_loader_word_cannot_drive_a_later_jump()
-> Result<(), String> {
    let mut operations = vec![LinearOpcode::NoOperation; 59];
    for (index, operation) in [
        (9, LinearOpcode::RelocateDataPointer),
        (10, LinearOpcode::InputWord),
        (11, LinearOpcode::CrazyData),
        (12, LinearOpcode::RelocateDataPointer),
        (14, LinearOpcode::OutputByte),
        (58, LinearOpcode::Halt),
    ] {
        replace_scratch_operation(&mut operations, index, operation)?;
    }
    for profile in [current_profile(), historical_profile()] {
        let layout = encode_linear_layout(profile, &operations)
            .map_err(|error| format!("expanded scratch layout: {error:?}"))?;
        if layout.source().get(9) != Some(&125)
            || layout.source().get(57..) != Some([105, 117].as_slice())
            || layout.data_pointer_positions().get(11..14)
                != Some([127, 128, 127].as_slice())
            || layout.data_write_positions().get(11) != Some(&Some(127))
        {
            return Err(String::from("incorrect expanded scratch geometry"));
        }
        for input in [0u8, 255] {
            let mut vm =
                ProfileMachine::from_source(profile, layout.source(), vec![
                    input,
                ])
                .map_err(|error| {
                    format!("expanded scratch guest: {error:?}")
                })?;
            let before =
                vm.memory_word(127).map_err(|error| error.to_string())?;
            if vm.memory_word(128) != Ok(126) {
                return Err(String::from(
                    "expanded re-relocation word differs",
                ));
            }
            let expected = scalar_crazy_reference(
                before,
                u32::from(input),
                profile.word_trits(),
            );
            verify_execution_witness(&mut vm, &layout)?;
            let byte = u8::try_from(expected & 255)
                .map_err(|error| error.to_string())?;
            if vm.input_consumed() != 1
                || vm.memory_word(127) != Ok(expected)
                || vm.output() != [byte]
            {
                return Err(String::from("expanded scratch guest differs"));
            }
        }
        let mut tainted = operations.clone();
        replace_scratch_operation(
            &mut tainted,
            13,
            LinearOpcode::JumpForward { target: 50 },
        )?;
        replace_scratch_operation(&mut tainted, 14, LinearOpcode::NoOperation)?;
        if encode_linear_layout(profile, &tainted)
            != Err(LinearLayoutError::JumpPathUnsupported)
        {
            return Err(String::from("input-written expanded jump admitted"));
        }
    }
    Ok(())
}

fn tainted_relocation_operations(
    target: usize,
) -> Result<Vec<LinearOpcode>, String> {
    let mut operations =
        vec![
            LinearOpcode::NoOperation;
            target.checked_add(6).ok_or("source position overflow")?
        ];
    replace_scratch_operation(&mut operations, 0, LinearOpcode::JumpForward {
        target: u32::try_from(target).map_err(|error| error.to_string())?,
    })?;
    // Both skipped graphical cells decode to valid loader instructions.
    // The first j sends D to 67. The input-dependent p writes that cell;
    // a second j returns D to 67, so a third j must not guess its value.
    replace_scratch_operation(
        &mut operations,
        2,
        LinearOpcode::SkippedDataByte { byte: 66 },
    )?;
    replace_scratch_operation(
        &mut operations,
        68,
        LinearOpcode::SkippedDataByte { byte: 66 },
    )?;
    replace_scratch_operation(
        &mut operations,
        target,
        LinearOpcode::InputWord,
    )?;
    replace_scratch_operation(
        &mut operations,
        target.checked_add(1).ok_or("source position overflow")?,
        LinearOpcode::RelocateDataPointer,
    )?;
    replace_scratch_operation(
        &mut operations,
        target.checked_add(2).ok_or("source position overflow")?,
        LinearOpcode::CrazyData,
    )?;
    replace_scratch_operation(
        &mut operations,
        target.checked_add(3).ok_or("source position overflow")?,
        LinearOpcode::RelocateDataPointer,
    )?;
    replace_scratch_operation(
        &mut operations,
        target.checked_add(4).ok_or("source position overflow")?,
        LinearOpcode::RelocateDataPointer,
    )?;
    replace_scratch_operation(
        &mut operations,
        target.checked_add(5).ok_or("source position overflow")?,
        LinearOpcode::Halt,
    )?;
    Ok(operations)
}

#[test]
fn unresolved_input_written_scratch_cannot_be_a_later_relocation_operand()
-> Result<(), String> {
    let target =
        usize::try_from(jump_target(0)?).map_err(|error| error.to_string())?;
    let operations = tainted_relocation_operations(target)?;
    for profile in [current_profile(), historical_profile()] {
        if encode_linear_layout(profile, &operations)
            != Err(LinearLayoutError::UnsafeDataPlacement)
        {
            return Err(String::from("unresolved j operand accepted"));
        }
        let mut known = operations.clone();
        replace_scratch_operation(
            &mut known,
            target,
            LinearOpcode::NoOperation,
        )?;
        let admitted = encode_linear_layout(profile, &known)
            .map_err(|error| format!("known scratch operand: {error:?}"))?;
        if admitted.data_write_positions().get(3) != Some(&Some(67)) {
            return Err(String::from("known relocation writes elsewhere"));
        }
        let original =
            u32::from(*admitted.source().get(67).ok_or("source operand")?);
        let expected =
            scalar_crazy_reference(original, 0, profile.word_trits());
        let mut vm =
            ProfileMachine::from_source(profile, admitted.source(), Vec::new())
                .map_err(|error| format!("known scratch guest: {error:?}"))?;
        verify_execution_witness(&mut vm, &admitted)?;
        if vm.memory_word(67) != Ok(expected) {
            return Err(String::from("known relocation VM differs"));
        }
    }
    Ok(())
}

#[test]
fn source_scratch_refuses_writes_at_pending_code() {
    let profile = current_profile();
    let operations = [
        LinearOpcode::NoOperation,
        LinearOpcode::CrazyData,
        LinearOpcode::OutputByte,
        LinearOpcode::Halt,
    ];
    assert_eq!(
        encode_linear_layout(profile, &operations),
        Err(LinearLayoutError::UnsafeDataPlacement)
    );
}

#[test]
fn jump_encrypted_skip_cell_is_a_real_guest_operand() -> Result<(), String> {
    let profile = current_profile();
    let target =
        usize::try_from(jump_target(0)?).map_err(|error| error.to_string())?;
    let mut operations = vec![LinearOpcode::NoOperation; target + target + 1];
    operations[0] = LinearOpcode::JumpForward {
        target: u32::try_from(target).map_err(|error| error.to_string())?,
    };
    operations[target + target - 2] = LinearOpcode::RotateData;
    operations[target + target - 1] = LinearOpcode::OutputByte;
    operations[target + target] = LinearOpcode::Halt;
    let layout = encode_linear_layout(profile, &operations)
        .map_err(|error| format!("encrypted scratch layout: {error:?}"))?;
    let cell = u32::from(layout.source()[target - 1]);
    let encrypted =
        encrypt_profile_cell(cell).ok_or("missing jump encryption")?;
    let expected = malbolge::profile_rotate(encrypted, profile.memory_words());
    assert_eq!(
        layout.data_write_positions().iter().flatten().last(),
        Some(&(target as u32 - 1))
    );
    for input in [Vec::new(), vec![255, 0, 128]] {
        let mut vm =
            ProfileMachine::from_source(profile, layout.source(), input)
                .map_err(|error| format!("guest load: {error:?}"))?;
        assert!(matches!(
            vm.run(layout.executed_code_positions().len()),
            Ok(RunOutcome::Terminated { .. })
        ));
        assert_eq!(vm.output(), [expected as u8]);
        assert_eq!(
            vm.memory_word(target as u32 - 1)
                .map_err(|error| format!("guest scratch: {error:?}"))?,
            expected
        );
    }
    Ok(())
}

#[test]
fn skipped_graphical_data_requires_valid_loader_opcode_and_unreachable_cell()
-> Result<(), String> {
    let profile = current_profile();
    let target =
        usize::try_from(jump_target(0)?).map_err(|error| error.to_string())?;
    let mut operations = vec![LinearOpcode::NoOperation; target + 2];
    operations[0] = LinearOpcode::JumpForward {
        target: u32::try_from(target).map_err(|error| error.to_string())?,
    };
    operations[target] = LinearOpcode::OutputByte;
    operations[target + 1] = LinearOpcode::Halt;
    // ASCII '2' is graphical at address one but does not decode to a
    // legal source instruction. Never publish a guest the VM cannot load.
    operations[1] = LinearOpcode::SkippedDataByte { byte: 50 };
    assert_eq!(
        encode_linear_layout(profile, &operations),
        Err(LinearLayoutError::NoEncoding { position: 1 })
    );
    // Position one is not unreachable when no forward jump skips over it.
    let reachable = [
        LinearOpcode::NoOperation,
        LinearOpcode::SkippedDataByte { byte: 50 },
        LinearOpcode::Halt,
    ];
    assert_eq!(
        encode_linear_layout(profile, &reachable),
        Err(LinearLayoutError::JumpPathUnsupported)
    );
    Ok(())
}

#[test]
fn forward_jump_then_data_relocation_reuses_only_past_source_scratch()
-> Result<(), String> {
    let target =
        usize::try_from(jump_target(0)?).map_err(|error| error.to_string())?;
    let operand = (33u8..=126)
        .find(|&byte| {
            decode_profile_instruction(u32::from(byte), 1) == Some(b'o')
                && usize::from(byte).saturating_add(1) < target
        })
        .ok_or("no backwards graphical scratch operand")?;
    let scratch_address = usize::from(operand) + 1;
    let mut operations = vec![LinearOpcode::NoOperation; target + 4];
    operations[0] = LinearOpcode::JumpForward {
        target: u32::try_from(target).map_err(|error| error.to_string())?,
    };
    operations[1] = LinearOpcode::SkippedDataByte { byte: u32::from(operand) };
    operations[target] = LinearOpcode::RelocateDataPointer;
    operations[target + 1] = LinearOpcode::CrazyData;
    operations[target + 2] = LinearOpcode::OutputByte;
    operations[target + 3] = LinearOpcode::Halt;
    for profile in [current_profile(), historical_profile()] {
        let layout = encode_linear_layout(profile, &operations)
            .map_err(|error| format!("past-source relocation: {error:?}"))?;
        assert_eq!(layout.executed_code_positions(), [
            0,
            target as u32,
            target as u32 + 1,
            target as u32 + 2,
            target as u32 + 3
        ],);
        assert_eq!(layout.data_write_positions(), [
            None,
            None,
            Some(scratch_address as u32),
            None,
            None
        ],);
        assert!(scratch_address < target);
        let expected_word = malbolge::profile_crazy(
            u32::from(layout.source()[scratch_address]),
            0,
            profile.word_trits(),
        );
        for input in [Vec::new(), vec![255, 0, 128]] {
            let mut vm =
                ProfileMachine::from_source(profile, layout.source(), input)
                    .map_err(|error| {
                        format!("past-source VM load: {error:?}")
                    })?;
            assert!(matches!(
                vm.run(5),
                Ok(RunOutcome::Terminated { steps: 5, .. })
            ));
            assert_eq!(vm.output(), [expected_word as u8]);
            assert_eq!(vm.input_consumed(), 0);
            assert_eq!(
                vm.memory_word(scratch_address as u32)
                    .map_err(|error| format!("scratch memory: {error:?}"))?,
                expected_word,
            );
        }
        let mut forged = layout.source().to_vec();
        forged[1] ^= 1;
        assert!(matches!(
            admit_linear_layout(
                profile,
                &operations,
                &forged,
                LinearProfileIdentity {
                    id: profile.id(),
                    fingerprint: profile.fingerprint(),
                },
            ),
            Err(LinearLayoutError::DecodeMismatch { position: 1 })
        ));
    }
    Ok(())
}

#[test]
fn source_data_relocation_refuses_pending_code_writes() -> Result<(), String> {
    let target =
        usize::try_from(jump_target(0)?).map_err(|error| error.to_string())?;
    let operand = (33u8..=126)
        .filter(|&byte| {
            decode_profile_instruction(u32::from(byte), 1).is_some_and(|op| {
                matches!(
                    op,
                    b'o' | b'j' | b'i' | b'*' | b'p' | b'v' | b'<' | b'/'
                )
            }) && usize::from(byte) + 1 >= target
        })
        .max()
        .ok_or("no forward-looking graphical operand")?;
    let length = usize::from(operand) + 6;
    let mut operations = vec![LinearOpcode::NoOperation; length];
    operations[0] = LinearOpcode::JumpForward {
        target: u32::try_from(target).map_err(|error| error.to_string())?,
    };
    operations[1] = LinearOpcode::SkippedDataByte { byte: u32::from(operand) };
    operations[target] = LinearOpcode::RelocateDataPointer;
    operations[target + 1] = LinearOpcode::CrazyData;
    operations[length - 1] = LinearOpcode::Halt;
    assert_eq!(
        encode_linear_layout(current_profile(), &operations),
        Err(LinearLayoutError::UnsafeDataPlacement)
    );
    Ok(())
}

fn verify_auto_source_scratch_guest(
    profile: &'static malbolge::ProfileDescriptor,
    layout: &LinearLayout,
    scratch: u32,
    expected_word: u32,
) -> Result<(), String> {
    let output_byte =
        u8::try_from(expected_word & 255).map_err(|error| error.to_string())?;
    for input in [Vec::new(), vec![0, 255, 42]] {
        let mut vm =
            ProfileMachine::from_source(profile, layout.source(), input)
                .map_err(|error| {
                    format!("auto scratch guest load: {error:?}")
                })?;
        if !matches!(
            vm.run(layout.executed_code_positions().len()),
            Ok(RunOutcome::Terminated { .. })
        ) || vm.output() != [output_byte]
            || vm
                .memory_word(scratch)
                .map_err(|error| format!("auto scratch memory: {error:?}"))?
                != expected_word
        {
            return Err(String::from("auto scratch guest effects differ"));
        }
    }
    Ok(())
}

#[test]
fn auto_relocation_uses_source_scratch_after_a_forward_jump()
-> Result<(), String> {
    use PaddedForwardStep::{AutoRelocate, Instruction, Jump};
    let target =
        usize::try_from(jump_target(0)?).map_err(|error| error.to_string())?;
    let target_word =
        u32::try_from(target).map_err(|error| error.to_string())?;
    let mut operations = vec![LinearOpcode::NoOperation; target];
    *operations.get_mut(0).ok_or("missing jump cell")? =
        LinearOpcode::JumpForward { target: target_word };
    operations.extend([
        LinearOpcode::RelocateDataPointer,
        LinearOpcode::CrazyData,
        LinearOpcode::OutputByte,
        LinearOpcode::Halt,
    ]);
    let logical = [
        Jump,
        AutoRelocate,
        Instruction(LinearOpcode::CrazyData),
        Instruction(LinearOpcode::OutputByte),
        Instruction(LinearOpcode::Halt),
    ];
    for profile in [current_profile(), historical_profile()] {
        let manual = encode_linear_layout(profile, &operations)
            .map_err(|error| format!("manual scratch layout: {error:?}"))?;
        let scratch = *manual
            .data_write_positions()
            .iter()
            .flatten()
            .next()
            .ok_or("no scratch write")?;
        let scratch_address =
            usize::try_from(scratch).map_err(|error| error.to_string())?;
        let padded = encode_auto_padded_forward_layout(profile, &logical)
            .map_err(|error| format!("auto scratch layout: {error:?}"))?;
        if scratch_address >= target
            || padded.logical_code_positions().get(1) != Some(&target_word)
            || padded.layout() != &manual
            || padded.source_cell_origins().get(1)
                != Some(&PaddedCellOrigin::SkippedPadding)
        {
            return Err(String::from("automatic source-scratch path differs"));
        }
        let operand = *manual
            .source()
            .get(scratch_address)
            .ok_or("scratch operand missing")?;
        let expected_word =
            scalar_crazy_reference(u32::from(operand), 0, profile.word_trits());
        verify_auto_source_scratch_guest(
            profile,
            padded.layout(),
            scratch,
            expected_word,
        )?;
    }
    Ok(())
}
