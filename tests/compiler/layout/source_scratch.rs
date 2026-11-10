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

// A symbolic forward jump can be proven from untouched expanded loader
// memory if its as-yet-unknown gap can be solved against the final fixed
// graphical source tail. This must produce the same guest as the independent
// concrete target, including its binary input and every executed address.
#[test]
fn auto_padding_jump_uses_proven_expanded_loader_word() -> Result<(), String> {
    use PaddedForwardStep::{AutoRelocate, Instruction, Jump};
    let mut logical = vec![Instruction(LinearOpcode::NoOperation); 8];
    logical.extend([
        AutoRelocate,
        Jump,
        Instruction(LinearOpcode::InputWord),
        Instruction(LinearOpcode::OutputByte),
        Instruction(LinearOpcode::NoOperation),
        Instruction(LinearOpcode::NoOperation),
        Instruction(LinearOpcode::Halt),
    ]);
    let operations = expanded_loader_jump_operations()?;
    for profile in [current_profile(), historical_profile()] {
        let independent = encode_linear_layout(profile, &operations)
            .map_err(|error| format!("concrete loader jump: {error:?}"))?;
        let artifact = encode_auto_padded_forward_layout(profile, &logical)
            .map_err(|error| format!("automatic loader jump: {error:?}"))?;
        if artifact.layout() != &independent
            || artifact.logical_code_positions().get(8..)
                != Some([8, 9, 39, 40, 41, 42, 43].as_slice())
        {
            return Err(String::from("automatic loader jump differs"));
        }
        verify_bidirectional_source_map(&artifact)?;
        for byte in [0u8, 255] {
            let mut vm = ProfileMachine::from_source(
                profile,
                independent.source(),
                vec![byte],
            )
            .map_err(|error| format!("automatic loader guest: {error:?}"))?;
            verify_execution_witness(&mut vm, &independent)?;
            if vm.input_consumed() != 1 || vm.output() != [byte] {
                return Err(String::from("automatic loader guest I/O differs"));
            }
        }
        let mut unfixed_tail = logical.clone();
        *unfixed_tail.get_mut(12).ok_or("missing fixed suffix")? = Jump;
        if encode_auto_padded_forward_layout(profile, &unfixed_tail)
            != Err(LinearLayoutError::JumpPathUnsupported)
        {
            return Err(String::from("unproven future jump gap admitted"));
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

fn replay_deterministic_expanded_guest(
    profile: &'static malbolge::ProfileDescriptor,
    admitted: &LinearLayout,
    original: u32,
    result: u32,
) -> Result<(), String> {
    for input in [Vec::new(), vec![0, 255, 42]] {
        let mut vm =
            ProfileMachine::from_source(profile, admitted.source(), input)
                .map_err(|error| format!("expanded write guest: {error:?}"))?;
        if vm.memory_word(127) != Ok(original) {
            return Err(String::from("original expanded word differs"));
        }
        verify_execution_witness(&mut vm, admitted)?;
        if vm.output()
            != [u8::try_from(result & 255)
                .map_err(|error| error.to_string())?]
            || vm.memory_word(127) != Ok(result)
            || vm.input_consumed() != 0
        {
            return Err(String::from("expanded control VM differs"));
        }
    }
    Ok(())
}

// The most recent write wins: input-dependent p invalidates a value already
// proven by a preceding expanded-memory arithmetic instruction.
fn refuse_overwritten_expanded_control(
    profile: &'static malbolge::ProfileDescriptor,
    operations: &[LinearOpcode],
) -> Result<(), String> {
    let mut overwritten = operations.to_vec();
    for (index, operation) in [
        (13, LinearOpcode::InputWord),
        (14, LinearOpcode::RelocateDataPointer),
        (15, LinearOpcode::CrazyData),
        (16, LinearOpcode::RelocateDataPointer),
        (17, LinearOpcode::RelocateDataPointer),
    ] {
        replace_scratch_operation(&mut overwritten, index, operation)?;
    }
    let mut safe_prefix = overwritten.clone();
    replace_scratch_operation(&mut safe_prefix, 17, LinearOpcode::NoOperation)?;
    let proven_prefix = encode_linear_layout(profile, &safe_prefix)
        .map_err(|error| format!("expanded overwrite prefix: {error:?}"))?;
    if proven_prefix.data_write_positions().get(15) != Some(&Some(127))
        || proven_prefix.data_pointer_positions().get(17) != Some(&127)
        || encode_linear_layout(profile, &overwritten)
            != Err(LinearLayoutError::UnsafeDataPlacement)
    {
        return Err(String::from("stale expanded write used for j"));
    }
    Ok(())
}

fn scalar_expanded_word_127(
    source: &[u8],
    profile: &malbolge::ProfileDescriptor,
) -> Result<u32, String> {
    let [.., before, last] = source else {
        return Err(String::from("missing final source tail"));
    };
    let mut previous = u32::from(*before);
    let mut latest = u32::from(*last);
    for _address in 59u32..=127 {
        let next =
            scalar_crazy_reference(previous, latest, profile.word_trits());
        previous = latest;
        latest = next;
    }
    Ok(latest)
}

// Deterministic guest arithmetic changes loader-expanded memory. A later j
// must read the updated word, not the original expansion or a guessed value.
#[test]
fn deterministic_expanded_arithmetic_drives_later_relocation()
-> Result<(), String> {
    for arithmetic in [LinearOpcode::RotateData, LinearOpcode::CrazyData] {
        let mut operations = vec![LinearOpcode::NoOperation; 59];
        for (index, operation) in [
            (9, LinearOpcode::RelocateDataPointer),
            (11, arithmetic),
            (12, LinearOpcode::RelocateDataPointer),
            (13, LinearOpcode::RelocateDataPointer),
            (14, LinearOpcode::OutputByte),
            (58, LinearOpcode::Halt),
        ] {
            replace_scratch_operation(&mut operations, index, operation)?;
        }
        for profile in [current_profile(), historical_profile()] {
            let admitted = encode_linear_layout(profile, &operations).map_err(
                |error| format!("expanded written control: {error:?}"),
            )?;
            // Independent scalar loader expansion from the final source tail.
            let latest = scalar_expanded_word_127(admitted.source(), profile)?;
            let result = if arithmetic == LinearOpcode::RotateData {
                malbolge::profile_rotate(latest, profile.memory_words())
            } else {
                scalar_crazy_reference(latest, 0, profile.word_trits())
            };
            if admitted.data_write_positions().get(11) != Some(&Some(127))
                || admitted.data_pointer_positions().get(11..15)
                    != Some([127, 128, 127, result + 1].as_slice())
            {
                return Err(String::from("wrong known expanded relocation"));
            }
            replay_deterministic_expanded_guest(
                profile, &admitted, latest, result,
            )?;
            let mut tainted = operations.clone();
            replace_scratch_operation(
                &mut tainted,
                8,
                LinearOpcode::InputWord,
            )?;
            replace_scratch_operation(
                &mut tainted,
                11,
                LinearOpcode::CrazyData,
            )?;
            if encode_linear_layout(profile, &tainted)
                != Err(LinearLayoutError::UnsafeDataPlacement)
            {
                return Err(String::from("input-tainted expanded j admitted"));
            }
            refuse_overwritten_expanded_control(profile, &operations)?;
        }
    }
    Ok(())
}

fn refuse_tainted_expanded_symbolic_control(
    profile: &'static malbolge::ProfileDescriptor,
    logical: &[PaddedForwardStep],
    operations: &[LinearOpcode],
) -> Result<(), String> {
    use PaddedForwardStep::Instruction;
    let mut tainted = logical.to_vec();
    *tainted.get_mut(8).ok_or("missing input slot")? =
        Instruction(LinearOpcode::InputWord);
    *tainted.get_mut(11).ok_or("missing p slot")? =
        Instruction(LinearOpcode::CrazyData);
    if encode_auto_padded_forward_layout(profile, &tainted)
        != Err(LinearLayoutError::UnsafeDataPlacement)
    {
        return Err(String::from("tainted expanded word admitted"));
    }
    let mut overwritten = operations.to_vec();
    for (index, operation) in [
        (13, LinearOpcode::InputWord),
        (14, LinearOpcode::RelocateDataPointer),
        (15, LinearOpcode::CrazyData),
        (16, LinearOpcode::RelocateDataPointer),
        (17, LinearOpcode::RelocateDataPointer),
    ] {
        replace_scratch_operation(&mut overwritten, index, operation)?;
    }
    let overwritten_logical: Vec<_> =
        overwritten.into_iter().map(Instruction).collect();
    if encode_auto_padded_forward_layout(profile, &overwritten_logical)
        != Err(LinearLayoutError::UnsafeDataPlacement)
    {
        return Err(String::from("stale expanded word admitted"));
    }
    Ok(())
}

// The independent encoder already proves a loader-expanded write and two
// subsequent j operands. The symbolic plan must preserve that known write,
// rather than re-reading the original loader value or refusing fixed code.
#[test]
fn fixed_tail_expanded_written_word_drives_symbolic_relocation()
-> Result<(), String> {
    use PaddedForwardStep::Instruction;
    for arithmetic in [LinearOpcode::RotateData, LinearOpcode::CrazyData] {
        let mut operations = vec![LinearOpcode::NoOperation; 59];
        for (index, operation) in [
            (9, LinearOpcode::RelocateDataPointer),
            (11, arithmetic),
            (12, LinearOpcode::RelocateDataPointer),
            (13, LinearOpcode::RelocateDataPointer),
            (14, LinearOpcode::OutputByte),
            (58, LinearOpcode::Halt),
        ] {
            replace_scratch_operation(&mut operations, index, operation)?;
        }
        let logical: Vec<_> =
            operations.iter().copied().map(Instruction).collect();
        for profile in [current_profile(), historical_profile()] {
            let independent = encode_linear_layout(profile, &operations)
                .map_err(|error| {
                    format!("known expanded independent: {error:?}")
                })?;
            let proposed = encode_auto_padded_forward_layout(profile, &logical)
                .map_err(|error| {
                    format!("known expanded proposal: {error:?}")
                })?;
            if proposed.layout() != &independent
                || proposed.logical_code_positions()
                    != (0..59u32).collect::<Vec<_>>()
            {
                return Err(String::from("written expanded proposal diverged"));
            }
            verify_bidirectional_source_map(&proposed)?;
            let original =
                scalar_expanded_word_127(independent.source(), profile)?;
            let written = if arithmetic == LinearOpcode::RotateData {
                malbolge::profile_rotate(original, profile.memory_words())
            } else {
                scalar_crazy_reference(original, 0, profile.word_trits())
            };
            replay_deterministic_expanded_guest(
                profile,
                proposed.layout(),
                original,
                written,
            )?;
            refuse_tainted_expanded_symbolic_control(profile, &logical, &operations)?;
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

#[test]
fn auto_padding_jumps_after_source_scratch_relocation()
-> Result<(), String> {
    use PaddedForwardStep::{AutoRelocate, Instruction, Jump};
    let mut logical = vec![Instruction(LinearOpcode::NoOperation); 4];
    logical.extend([
        Jump,
        AutoRelocate,
        Jump,
        Instruction(LinearOpcode::InputWord),
        Instruction(LinearOpcode::OutputByte),
        Instruction(LinearOpcode::Halt),
    ]);
    for profile in [current_profile(), historical_profile()] {
        let expanded = encode_auto_padded_forward_layout(profile, &logical)
            .map_err(|error| format!("post-relocation auto jump: {error:?}"))?;
        if expanded.logical_code_positions()
            != [0, 1, 2, 3, 4, 95, 96, 99, 100, 101]
            || expanded.layout().data_pointer_positions()
                != [0, 1, 2, 3, 4, 5, 64, 65, 66, 67]
            || expanded.layout().source().get(64) != Some(&98)
        {
            return Err(String::from("post-relocation auto jump geometry differs"));
        }
        verify_bidirectional_source_map(&expanded)?;
        let independent = encode_linear_layout(profile, expanded.operations())
            .map_err(|error| format!("independent post-relocation layout: {error:?}"))?;
        if expanded.layout() != &independent {
            return Err(String::from("post-relocation independent proof differs"));
        }
        for byte in [0x00, 0xff] {
            let mut vm = ProfileMachine::from_source(
                profile,
                independent.source(),
                vec![byte],
            )
            .map_err(|error| format!("post-relocation guest load: {error:?}"))?;
            verify_execution_witness(&mut vm, &independent)?;
            if vm.input_consumed() != 1 || vm.output() != [byte] {
                return Err(String::from("post-relocation guest byte parity differs"));
            }
        }
    }
    Ok(())
}

#[test]
fn auto_padding_jump_reads_previously_encrypted_source_after_relocation()
-> Result<(), String> {
    use PaddedForwardStep::{AutoRelocate, Instruction, Jump};
    let mut logical = vec![Instruction(LinearOpcode::NoOperation); 90];
    logical.extend([
        Jump,
        AutoRelocate,
        Jump,
        Instruction(LinearOpcode::InputWord),
        Instruction(LinearOpcode::OutputByte),
        Instruction(LinearOpcode::Halt),
    ]);
    for profile in [current_profile(), historical_profile()] {
        let artifact = encode_auto_padded_forward_layout(profile, &logical)
            .map_err(|error| format!("encrypted auto jump: {error:?}"))?;
        verify_bidirectional_source_map(&artifact)?;
        let positions = artifact.logical_code_positions();
        let tail = positions
            .get(90..)
            .ok_or("missing post-relocation logical steps")?;
        if tail != [90, 103, 104, 125, 126, 127]
            || artifact.layout().data_pointer_positions().get(92)
                != Some(&72)
            || artifact.layout().source().get(72).and_then(|source_byte| {
                encrypt_profile_cell(u32::from(*source_byte))
            }) != Some(124)
        {
            return Err(String::from("encrypted auto operand geometry differs"));
        }
        let mut wrong_target = artifact.operations().to_vec();
        replace_scratch_operation(
            &mut wrong_target,
            104,
            LinearOpcode::JumpForward { target: 124 },
        )?;
        if encode_linear_layout(profile, &wrong_target)
            != Err(LinearLayoutError::JumpTargetMismatch { position: 104 })
        {
            return Err(String::from("forged encrypted jump target admitted"));
        }
        for input in [0x00, 0xff] {
            let mut vm = ProfileMachine::from_source(
                profile,
                artifact.layout().source(),
                vec![input],
            )
            .map_err(|error| format!("encrypted auto jump VM: {error:?}"))?;
            verify_execution_witness(&mut vm, artifact.layout())?;
            if vm.input_consumed() != 1 || vm.output() != [input] {
                return Err(String::from("encrypted auto jump byte parity differs"));
            }
        }
    }
    Ok(())
}

#[test]
fn auto_padding_jump_skips_past_input_written_scratch()
-> Result<(), String> {
    use PaddedForwardStep::{AutoRelocate, Instruction, Jump};
    let mut logical = vec![Instruction(LinearOpcode::NoOperation); 6];
    logical.extend([
        Jump,
        AutoRelocate,
        Instruction(LinearOpcode::InputWord),
        Instruction(LinearOpcode::CrazyData),
        Jump,
        Instruction(LinearOpcode::OutputByte),
        Instruction(LinearOpcode::Halt),
    ]);
    for profile in [current_profile(), historical_profile()] {
        let artifact = encode_auto_padded_forward_layout(profile, &logical)
            .map_err(|error| format!("source-write auto jump: {error:?}"))?;
        verify_bidirectional_source_map(&artifact)?;
        if artifact.logical_code_positions().get(6..)
            != Some(&[6, 93, 94, 95, 96, 99, 100][..])
            || artifact.layout().data_write_positions().get(9)
                != Some(&Some(63))
        {
            return Err(String::from("source-write auto jump path differs"));
        }
        let original = *artifact
            .layout()
            .source()
            .get(63)
            .ok_or("missing source-write operand")?;
        for input in [0x00, 0xff] {
            let expected = scalar_crazy_reference(
                u32::from(original),
                u32::from(input),
                profile.word_trits(),
            );
            let mut vm = ProfileMachine::from_source(
                profile,
                artifact.layout().source(),
                vec![input],
            )
            .map_err(|error| format!("source-write auto jump VM: {error:?}"))?;
            verify_execution_witness(&mut vm, artifact.layout())?;
            let expected_byte = u8::try_from(expected & 255)
                .map_err(|error| error.to_string())?;
            if vm.input_consumed() != 1
                || vm.output() != [expected_byte]
                || vm.memory_word(63) != Ok(expected)
            {
                return Err(String::from("source-write auto jump VM parity differs"));
            }
        }
    }
    Ok(())
}

#[test]
fn auto_padding_relocates_twice_using_known_source_after_input_scratch()
-> Result<(), String> {
    use PaddedForwardStep::{AutoRelocate, Instruction, Jump};
    let mut logical = vec![Instruction(LinearOpcode::NoOperation); 6];
    logical.extend([
        Jump,
        AutoRelocate,
        Instruction(LinearOpcode::InputWord),
        Instruction(LinearOpcode::CrazyData),
        AutoRelocate,
        Instruction(LinearOpcode::OutputByte),
        Instruction(LinearOpcode::Halt),
    ]);
    for profile in [current_profile(), historical_profile()] {
        // Without the two reached filler phases, the second j would point
        // D into code that has not been executed and must be refused.
        let mut premature = logical.clone();
        *premature.get_mut(10).ok_or("missing second relocation")? =
            Instruction(LinearOpcode::RelocateDataPointer);
        if encode_auto_padded_forward_layout(profile, &premature)
            != Err(LinearLayoutError::UnsafeDataPlacement)
        {
            return Err(String::from("unsafe early second j was admitted"));
        }
        let artifact = encode_auto_padded_forward_layout(profile, &logical)
            .map_err(|error| format!("second source relocation: {error:?}"))?;
        verify_bidirectional_source_map(&artifact)?;
        let relocation_positions: Vec<_> = artifact
            .layout()
            .executed_code_positions()
            .iter()
            .copied()
            .filter(|&address| {
                artifact
                    .operations()
                    .get(usize::try_from(address).unwrap_or_default())
                    == Some(&LinearOpcode::RelocateDataPointer)
            })
            .collect();
        if relocation_positions.len() != 2 {
            return Err(String::from("expected two reached data relocations"));
        }
        // The selected second j also has an explicit address-sensitive plan.
        // Only reached no-ops are inserted, so both must encode identically.
        let mut explicit = vec![Instruction(LinearOpcode::NoOperation); 6];
        explicit.extend([
            Jump,
            AutoRelocate,
            Instruction(LinearOpcode::InputWord),
            Instruction(LinearOpcode::CrazyData),
            Instruction(LinearOpcode::NoOperation),
            Instruction(LinearOpcode::NoOperation),
            Instruction(LinearOpcode::RelocateDataPointer),
            Instruction(LinearOpcode::OutputByte),
            Instruction(LinearOpcode::Halt),
        ]);
        let explicit = encode_auto_padded_forward_layout(profile, &explicit)
            .map_err(|error| {
                format!("explicit second relocation: {error:?}")
            })?;
        if explicit.layout() != artifact.layout()
            || artifact.logical_code_positions().get(10) != Some(&98)
        {
            return Err(String::from("symbolic and explicit second j differ"));
        }
        let write_address = artifact
            .layout()
            .data_write_positions()
            .iter()
            .flatten()
            .copied()
            .next()
            .ok_or("missing source scratch write")?;
        let operand = u32::from(
            *artifact
                .layout()
                .source()
                .get(
                    usize::try_from(write_address)
                        .map_err(|error| error.to_string())?,
                )
                .ok_or("missing source scratch operand")?,
        );
        for input in [0x00u8, 0xff] {
            let expected = scalar_crazy_reference(
                operand,
                u32::from(input),
                profile.word_trits(),
            );
            let mut vm = ProfileMachine::from_source(
                profile,
                artifact.layout().source(),
                vec![input],
            )
            .map_err(|error| {
                format!("repeated relocation VM load: {error:?}")
            })?;
            verify_execution_witness(&mut vm, artifact.layout())?;
            if vm.input_consumed() != 1
                || vm.output()
                    != [u8::try_from(expected & 255)
                        .map_err(|error| error.to_string())?]
                || vm.memory_word(write_address) != Ok(expected)
            {
                return Err(String::from(
                    "repeated relocation guest parity differs",
                ));
            }
        }
    }
    Ok(())
}
#[test]
fn automatic_third_relocation_reads_deterministically_rotated_scratch()
-> Result<(), String> {
    use PaddedForwardStep::{AutoRelocate, Instruction, Jump};
    // The initial forward jump leaves its own source cell (81) behind C.
    // A first j returns D to that cell, * rotates it from 111 to 37, and
    // a second j returns D to 81. The third j must read the rotated word,
    // not the original graphical source or an assumed unknown operand.
    let mut prefix = vec![Instruction(LinearOpcode::NoOperation); 81];
    *prefix.get_mut(0).ok_or("missing initial input")? =
        Instruction(LinearOpcode::InputWord);
    prefix.extend([
        Jump,
        AutoRelocate,
        Instruction(LinearOpcode::RotateData),
        AutoRelocate,
        Instruction(LinearOpcode::OutputByte),
        Instruction(LinearOpcode::Halt),
    ]);
    for profile in [current_profile(), historical_profile()] {
        let baseline = encode_auto_padded_forward_layout(profile, &prefix)
            .map_err(|error| format!("known rotation baseline: {error:?}"))?;
        if baseline.layout().source().get(81) != Some(&111)
            || baseline
                .layout()
                .data_write_positions()
                .iter()
                .flatten()
                .copied()
                .collect::<Vec<_>>()
                != [81]
            || baseline.layout().data_pointer_positions().last() != Some(&82)
        {
            return Err(String::from(
                "unexpected deterministic rotation geometry",
            ));
        }
        let mut manual = baseline.operations().to_vec();
        *manual.get_mut(115).ok_or("missing manual third j")? =
            LinearOpcode::RelocateDataPointer;
        *manual.get_mut(116).ok_or("missing manual output")? =
            LinearOpcode::OutputByte;
        manual.push(LinearOpcode::Halt);
        let independent = encode_linear_layout(profile, &manual)
            .map_err(|error| format!("third j independent proof: {error:?}"))?;
        if independent.data_pointer_positions().get(85..)
            != Some([81, 38, 39].as_slice())
        {
            return Err(String::from(
                "third j did not read rotated source word",
            ));
        }
        let mut logical = prefix.clone();
        logical.insert(
            logical.len() - 2,
            Instruction(LinearOpcode::RelocateDataPointer),
        );
        let artifact = encode_auto_padded_forward_layout(profile, &logical)
            .map_err(|error| format!("third j auto proof: {error:?}"))?;
        if artifact.layout() != &independent {
            return Err(String::from("auto and independent third j differ"));
        }
        verify_bidirectional_source_map(&artifact)?;
        // A preceding real input makes A unknown, but * depends only on D.
        // A p at the same point would remain input-tainted and its value
        // must not be used by this third relocation.
        let mut unresolved = logical.clone();
        *unresolved.get_mut(83).ok_or("missing unresolved p")? =
            Instruction(LinearOpcode::CrazyData);
        if encode_auto_padded_forward_layout(profile, &unresolved)
            != Err(LinearLayoutError::UnsafeDataPlacement)
        {
            return Err(String::from("input-tainted third j was admitted"));
        }
        let mut tainted_manual = manual.clone();
        *tainted_manual.get_mut(113).ok_or("missing manual p")? =
            LinearOpcode::CrazyData;
        if encode_linear_layout(profile, &tainted_manual)
            != Err(LinearLayoutError::UnsafeDataPlacement)
        {
            return Err(String::from("independent tainted third j admitted"));
        }
        for input in [Vec::new(), vec![0xff, 0x00]] {
            let consumed = usize::from(!input.is_empty());
            let mut vm = ProfileMachine::from_source(
                profile,
                independent.source(),
                input,
            )
            .map_err(|error| format!("third j guest load: {error:?}"))?;
            verify_execution_witness(&mut vm, &independent)?;
            if vm.output() != [37]
                || vm.memory_word(81) != Ok(37)
                || vm.input_consumed() != consumed
            {
                return Err(String::from(
                    "third j guest output or scratch differs",
                ));
            }
        }
    }
    Ok(())
}

fn replay_expanded_second_relocation_guest(
    profile: &'static malbolge::ProfileDescriptor,
    independent: &LinearLayout,
) -> Result<(), String> {
    // Compute the target cell independently from the actual final tail,
    // without reusing the layout checker's six-step loader shortcut.
    let [.., before, last] = independent.source() else {
        return Err(String::from("missing source tail"));
    };
    let mut previous = u32::from(*before);
    let mut latest = u32::from(*last);
    for _address in 98u32..=101u32 {
        let next =
            scalar_crazy_reference(previous, latest, profile.word_trits());
        previous = latest;
        latest = next;
    }
    let rotated = malbolge::profile_rotate(latest, profile.memory_words());
    for input in [Vec::new(), vec![0x00, 0xff]] {
        let mut vm = ProfileMachine::from_source(
            profile,
            independent.source(),
            input,
        )
        .map_err(|error| format!("expanded second j guest: {error:?}"))?;
        verify_execution_witness(&mut vm, independent)?;
        let byte = u8::try_from(rotated & 255)
            .map_err(|error| error.to_string())?;
        if vm.output() != [byte]
            || vm.memory_word(101) != Ok(rotated)
            || vm.input_consumed() != 0
        {
            return Err(String::from("expanded second j VM differs"));
        }
    }
    Ok(())
}

// A past graphical source operand can relocate D into expanded memory even
// after an earlier j relocated D into source scratch. The complete future
// source must still end before the second destination.
#[test]
fn auto_second_relocation_uses_proven_source_to_reach_expanded_memory()
-> Result<(), String> {
    use PaddedForwardStep::{AutoRelocate, Instruction, Jump};
    let mut logical = vec![Instruction(LinearOpcode::NoOperation); 6];
    logical.extend([
        Jump,
        AutoRelocate,
        AutoRelocate,
        Instruction(LinearOpcode::RotateData),
        Instruction(LinearOpcode::OutputByte),
        Instruction(LinearOpcode::Halt),
    ]);
    let mut explicit = vec![LinearOpcode::NoOperation; 98];
    for (index, operation) in [
        (6, LinearOpcode::JumpForward { target: 93 }),
        (93, LinearOpcode::RelocateDataPointer),
        (94, LinearOpcode::RelocateDataPointer),
        (95, LinearOpcode::RotateData),
        (96, LinearOpcode::OutputByte),
        (97, LinearOpcode::Halt),
    ] {
        replace_scratch_operation(&mut explicit, index, operation)?;
    }
    for profile in [current_profile(), historical_profile()] {
        let independent =
            encode_linear_layout(profile, &explicit).map_err(|error| {
                format!("explicit expanded second j: {error:?}")
            })?;
        if independent.data_pointer_positions().get(7..)
            != Some([7, 62, 101, 102, 103].as_slice())
            || independent.data_write_positions().get(9) != Some(&Some(101))
            || independent.source().get(62) != Some(&100)
        {
            return Err(String::from("incorrect expanded second j witness"));
        }
        let artifact = encode_auto_padded_forward_layout(profile, &logical)
            .map_err(|error| {
                format!("automatic expanded second j: {error:?}")
            })?;
        if artifact.layout() != &independent
            || artifact.logical_code_positions().get(6..)
                != Some([6, 93, 94, 95, 96, 97].as_slice())
        {
            return Err(String::from("explicit/automatic expanded j differs"));
        }
        verify_bidirectional_source_map(&artifact)?;
        replay_expanded_second_relocation_guest(profile, &independent)?;
        let mut source_overlap = explicit.clone();
        let _inserted = source_overlap
            .splice(97..97, [LinearOpcode::NoOperation; 4])
            .collect::<Vec<_>>();
        if encode_linear_layout(profile, &source_overlap)
            != Err(LinearLayoutError::UnsafeDataPlacement)
        {
            return Err(String::from("source-overlapping second j admitted"));
        }
    }
    Ok(())
}

#[test]
fn auto_relocation_reads_untouched_expanded_loader_operand()
-> Result<(), String> {
    use PaddedForwardStep::{AutoRelocate, Instruction, Jump};
    // Two source-backed relocations place D in expanded loader memory.
    // A third j reads the untouched expanded word. The final static suffix
    // gives the planner the exact loader seed without guessing guest input.
    let mut logical = vec![Instruction(LinearOpcode::NoOperation); 6];
    logical.extend([
        Jump,
        AutoRelocate,
        AutoRelocate,
        AutoRelocate,
        Instruction(LinearOpcode::RotateData),
        Instruction(LinearOpcode::OutputByte),
        Instruction(LinearOpcode::Halt),
    ]);
    let mut explicit = vec![LinearOpcode::NoOperation; 99];
    for (index, operation) in [
        (6, LinearOpcode::JumpForward { target: 93 }),
        (93, LinearOpcode::RelocateDataPointer),
        (94, LinearOpcode::RelocateDataPointer),
        (95, LinearOpcode::RelocateDataPointer),
        (96, LinearOpcode::RotateData),
        (97, LinearOpcode::OutputByte),
        (98, LinearOpcode::Halt),
    ] {
        replace_scratch_operation(&mut explicit, index, operation)?;
    }
    for profile in [current_profile(), historical_profile()] {
        let independent = encode_linear_layout(profile, &explicit)
            .map_err(|error| format!("explicit expanded third j: {error:?}"))?;
        if independent.data_pointer_positions().get(7..10)
            != Some([7, 62, 101].as_slice())
        {
            return Err(String::from("unexpected expanded third-j setup"));
        }
        let artifact = encode_auto_padded_forward_layout(profile, &logical)
            .map_err(|error| format!("expanded third auto j: {error:?}"))?;
        if artifact.layout() != &independent
            || artifact.logical_code_positions().get(6..)
                != Some([6, 93, 94, 95, 96, 97, 98].as_slice())
        {
            return Err(String::from(
                "explicit and expanded-auto layout differ",
            ));
        }
        verify_bidirectional_source_map(&artifact)?;
        // Independently expand the final two original source words to find
        // the control operand, then the fourth region's rotated data word.
        let source = independent.source();
        let scalar_loader = |address: usize| -> Result<u32, String> {
            if address < source.len() {
                return Err(String::from("scalar expanded address in source"));
            }
            let mut previous = u32::from(source[source.len() - 2]);
            let mut latest = u32::from(source[source.len() - 1]);
            for _ in 0..=((address - source.len()) % 6) {
                let next = scalar_crazy_reference(
                    previous,
                    latest,
                    profile.word_trits(),
                );
                previous = latest;
                latest = next;
            }
            Ok(latest)
        };
        let third_operand = scalar_loader(101)?;
        let rotated_address = (third_operand + 1) % profile.memory_words();
        let expected_word = malbolge::profile_rotate(
            scalar_loader(rotated_address as usize)?,
            profile.memory_words(),
        );
        if independent.data_pointer_positions().get(10)
            != Some(&rotated_address)
            || independent.data_write_positions().get(10)
                != Some(&Some(rotated_address))
        {
            return Err(String::from("expanded j did not read scalar control"));
        }
        for input in [Vec::new(), vec![0, 255]] {
            let mut vm = ProfileMachine::from_source(
                profile,
                independent.source(),
                input,
            )
            .map_err(|error| format!("expanded third-j VM load: {error:?}"))?;
            verify_execution_witness(&mut vm, &independent)?;
            if vm.input_consumed() != 0
                || vm.output() != [expected_word as u8]
                || vm.memory_word(rotated_address) != Ok(expected_word)
            {
                return Err(String::from("expanded third-j VM parity differs"));
            }
        }
        let mut unknown_tail = logical.clone();
        *unknown_tail.get_mut(11).ok_or("missing suffix opcode")? = Jump;
        if encode_auto_padded_forward_layout(profile, &unknown_tail)
            != Err(LinearLayoutError::UnsafeDataPlacement)
        {
            return Err(String::from("unresolved future loader tail admitted"));
        }
    }
    Ok(())
}

// An untouched expanded loader word can relocate D back into skipped
// graphical source scratch behind the executing C. Its origin need not be
// another source cell: the independent VM still proves the same write.
#[test]
fn auto_expanded_relocation_into_past_source_scratch() -> Result<(), String> {
    use PaddedForwardStep::{AutoRelocate, Instruction, Jump};
    let mut logical = vec![Instruction(LinearOpcode::NoOperation); 6];
    logical.extend([
        Jump,
        AutoRelocate,
        AutoRelocate,
        AutoRelocate,
        Instruction(LinearOpcode::RotateData),
        Instruction(LinearOpcode::OutputByte),
        Instruction(LinearOpcode::NoOperation),
        Instruction(LinearOpcode::Halt),
    ]);
    let mut explicit = vec![LinearOpcode::NoOperation; 100];
    for (position, operation) in [
        (6, LinearOpcode::JumpForward { target: 93 }),
        (93, LinearOpcode::RelocateDataPointer),
        (94, LinearOpcode::RelocateDataPointer),
        (95, LinearOpcode::RelocateDataPointer),
        (96, LinearOpcode::RotateData),
        (97, LinearOpcode::OutputByte),
        (99, LinearOpcode::Halt),
    ] {
        replace_scratch_operation(&mut explicit, position, operation)?;
    }
    for profile in [current_profile(), historical_profile()] {
        let independent =
            encode_linear_layout(profile, &explicit).map_err(|error| {
                format!("expanded-to-source encoder: {error:?}")
            })?;
        let artifact = encode_auto_padded_forward_layout(profile, &logical)
            .map_err(|error| {
                format!("expanded-to-source planner: {error:?}")
            })?;
        if artifact.layout() != &independent
            || artifact.logical_code_positions().get(6..)
                != Some([6, 93, 94, 95, 96, 97, 98, 99].as_slice())
            || independent.data_pointer_positions().get(7..11)
                != Some([7, 62, 101, 68].as_slice())
            || independent.data_write_positions().get(10) != Some(&Some(68))
        {
            return Err(String::from(
                "expanded source-scratch geometry differs",
            ));
        }
        verify_bidirectional_source_map(&artifact)?;
        // Enlarging the source makes the second j's address 101 into
        // future source code instead of verified expanded loader memory.
        let mut aliased_source = explicit.clone();
        replace_scratch_operation(
            &mut aliased_source,
            99,
            LinearOpcode::NoOperation,
        )?;
        aliased_source.extend(vec![LinearOpcode::NoOperation; 39]);
        aliased_source.push(LinearOpcode::Halt);
        if encode_linear_layout(profile, &aliased_source)
            != Err(LinearLayoutError::UnsafeDataPlacement)
        {
            return Err(String::from("future source operand was admitted"));
        }
        let source = independent.source();
        let mut older = u32::from(*source.get(98).ok_or("tail older")?);
        let mut latest = u32::from(*source.get(99).ok_or("tail newest")?);
        for _address in 100..=101 {
            let next =
                scalar_crazy_reference(older, latest, profile.word_trits());
            older = latest;
            latest = next;
        }
        if latest != 67 {
            return Err(String::from("expanded source-scratch loader differs"));
        }
        let original_word = u32::from(*source.get(68).ok_or("source word")?);
        let rotated =
            malbolge::profile_rotate(original_word, profile.memory_words());
        for input in [Vec::new(), vec![0, 255]] {
            let mut vm = ProfileMachine::from_source(profile, source, input)
                .map_err(|error| {
                    format!("expanded source-scratch VM: {error:?}")
                })?;
            if vm.memory_word(101) != Ok(latest) {
                return Err(String::from("initial expanded operand differs"));
            }
            verify_execution_witness(&mut vm, &independent)?;
            if vm.input_consumed() != 0
                || vm.memory_word(68) != Ok(rotated)
                || vm.output() != [rotated as u8]
            {
                return Err(String::from(
                    "expanded source-scratch guest differs",
                ));
            }
        }
    }
    Ok(())
}

// A deterministic expanded word can be transformed by * and p, then reused
// as a later i operand after j restores D. The eventual jump gap fixes the
// loader tail; a partial prefix alone cannot prove the write or relocation.
#[test]
fn symbolic_jump_uses_written_expanded_word_with_fixed_final_tail()
-> Result<(), String> {
    use PaddedForwardStep::{Instruction, Jump};
    let mut explicit = vec![LinearOpcode::NoOperation; 59];
    for (position, operation) in [
        (9, LinearOpcode::RelocateDataPointer),
        (11, LinearOpcode::RotateData),
        (12, LinearOpcode::RelocateDataPointer),
        (13, LinearOpcode::CrazyData),
        (14, LinearOpcode::RelocateDataPointer),
        (15, LinearOpcode::JumpForward { target: 38 }),
        (38, LinearOpcode::OutputByte),
        (58, LinearOpcode::Halt),
    ] {
        replace_scratch_operation(&mut explicit, position, operation)?;
    }
    let mut logical: Vec<_> =
        explicit[..15].iter().copied().map(Instruction).collect();
    logical.push(Jump);
    logical.extend(explicit[38..].iter().copied().map(Instruction));
    for profile in [current_profile(), historical_profile()] {
        let independent = encode_linear_layout(profile, &explicit)
            .map_err(|error| format!("independent expanded i: {error:?}"))?;
        if independent.data_pointer_positions().get(11..17)
            != Some([127, 128, 127, 128, 127, 128].as_slice())
            || independent.executed_code_positions().get(16) != Some(&38)
        {
            return Err(String::from("incorrect expanded i witness"));
        }
        let mut wrong_target = explicit.clone();
        replace_scratch_operation(
            &mut wrong_target,
            15,
            LinearOpcode::JumpForward { target: 39 },
        )?;
        if encode_linear_layout(profile, &wrong_target)
            != Err(LinearLayoutError::JumpPathUnsupported)
        {
            return Err(String::from("forged written control jump admitted"));
        }
        let mut tainted = explicit.clone();
        replace_scratch_operation(&mut tainted, 11, LinearOpcode::InputWord)?;
        if encode_linear_layout(profile, &tainted)
            != Err(LinearLayoutError::JumpPathUnsupported)
        {
            return Err(String::from("input-derived expanded jump admitted"));
        }
        let mut tainted_logical = logical.clone();
        *tainted_logical.get_mut(11).ok_or("missing taint slot")? =
            Instruction(LinearOpcode::InputWord);
        if encode_auto_padded_forward_layout(profile, &tainted_logical)
            != Err(LinearLayoutError::UnsafeDataPlacement)
        {
            return Err(String::from(
                "unproven expanded jump proposal admitted",
            ));
        }
        let mut overlapping = explicit.clone();
        replace_scratch_operation(
            &mut overlapping,
            58,
            LinearOpcode::NoOperation,
        )?;
        overlapping.extend([LinearOpcode::NoOperation; 70]);
        overlapping.push(LinearOpcode::Halt);
        if encode_linear_layout(profile, &overlapping)
            != Err(LinearLayoutError::UnsafeDataPlacement)
        {
            return Err(String::from(
                "expanded write overlaps extended source",
            ));
        }
        let automatic = encode_auto_padded_forward_layout(profile, &logical)
            .map_err(|error| format!("symbolic expanded i: {error:?}"))?;
        if automatic.layout() != &independent
            || automatic.logical_code_positions().get(15) != Some(&15)
            || automatic.logical_code_positions().get(16) != Some(&38)
        {
            return Err(String::from("symbolic expanded i layout differs"));
        }
        verify_bidirectional_source_map(&automatic)?;
        let original = scalar_expanded_word_127(independent.source(), profile)?;
        let rotated =
            malbolge::profile_rotate(original, profile.memory_words());
        let written =
            scalar_crazy_reference(rotated, rotated, profile.word_trits());
        if written != 37 {
            return Err(String::from("independent expanded scalar differs"));
        }
        for input in [Vec::new(), vec![0, 255]] {
            let mut vm = ProfileMachine::from_source(
                profile,
                automatic.layout().source(),
                input,
            )
            .map_err(|error| format!("expanded i VM load: {error:?}"))?;
            if vm.memory_word(128) != Ok(126)
                || vm.memory_word(127) != Ok(original)
            {
                return Err(String::from("expanded i loader differs"));
            }
            verify_execution_witness(&mut vm, automatic.layout())?;
            if vm.output() != [37]
                || vm.memory_word(127) != Ok(37)
                || vm.input_consumed() != 0
            {
                return Err(String::from("expanded i guest effects differ"));
            }
        }
    }
    Ok(())
}
