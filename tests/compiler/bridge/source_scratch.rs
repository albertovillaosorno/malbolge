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
//   - Source-scratch proposal for an actual Fibonacci C output prefix.
// - Must-Not:
//   - Publish a host-computed byte trace without real guest VM output.
// - Allows:
//   - Inputs: independent unsigned recurrence bytes and code phases.
//   - Outputs: a verified forward-jump source and two real guest effects.
//   - Side effects: bounded normative VM replay only.
// - Split-When:
//   - General source-scratch linker work has separate ownership.
// - Merge-When:
//   - A general guest layout synthesizer proves this geometry.
// - Summary:
//   - A forward jump permits scratch writes to past code cells.

use super::super::{ProfileMachine, RunOutcome, pair_source_cells};
use super::*;

type GraphicalScratchStates = BTreeSet<(usize, u32)>;
type GraphicalScratchResult = (GraphicalScratchStates, BTreeSet<u8>);

#[test]
fn fibonacci_prefix_uses_source_scratch_not_host_output() -> Result<(), String>
{
    let mut previous = 1u32;
    let mut current = 1u32;
    let mut expected = [0u8; 2];
    for byte in &mut expected {
        let next = (previous + current) & 255;
        *byte = u8::try_from(if next & 1 == 0 {
            next
        } else {
            next ^ 0x5a
        })
        .map_err(|error| error.to_string())?;
        previous = current;
        current = next;
    }
    assert_eq!(expected, [0x02, 0x59]);
    let profile = malbolge::current_profile();
    let cells = pair_source_cells(profile).ok_or("missing decoder phases")?;
    let layout =
        verified_source_scratch_output_layout(profile, expected, &cells)
            .ok_or("source-scratch prefix proposal missed real C effects")?;
    assert!(layout.source().len() > 99);
    assert!(
        layout
            .data_write_positions()
            .iter()
            .flatten()
            .any(|&address| {
                usize::try_from(address)
                    .is_ok_and(|value| value < layout.source().len())
            })
    );
    for input in [Vec::new(), vec![0, 255, 128]] {
        let mut vm =
            ProfileMachine::from_source(profile, layout.source(), input)
                .map_err(|error| format!("guest load: {error:?}"))?;
        assert!(matches!(
            vm.run(layout.executed_code_positions().len()),
            Ok(RunOutcome::Terminated { .. })
        ));
        assert_eq!(vm.output(), expected);
        assert_eq!(vm.input_consumed(), 0);
    }
    Ok(())
}

#[test]
fn scratch_emits_third_byte_after_jump() -> Result<(), String> {
    let expected = [0x02, 0x59, 0x1b];
    let profile = malbolge::current_profile();
    let cells = pair_source_cells(profile).ok_or("missing decoder phases")?;
    let layout =
        verified_source_scratch_output_layout(profile, expected, &cells)
            .ok_or("missing third guest effect")?;
    for input in [Vec::new(), vec![0, 255, 128]] {
        let mut vm =
            ProfileMachine::from_source(profile, layout.source(), input)
                .map_err(|error| format!("guest load: {error:?}"))?;
        assert!(matches!(
            vm.run(layout.executed_code_positions().len()),
            Ok(RunOutcome::Terminated { .. })
        ));
        assert_eq!(vm.output(), expected);
    }
    Ok(())
}

#[test]
fn variable_source_scratch_emits_masked_twelve_fibonacci_bytes()
-> Result<(), String> {
    let expected = [
        0x02, 0x19, 0x1f, 0x08, 0x17, 0x0f, 0x02, 0x0d, 0x03, 0x10, 0x13, 0x03,
    ];
    let profile = malbolge::current_profile();
    let layout = verified_variable_source_scratch_layout(profile, expected)
        .ok_or("missing twelve real masked Fibonacci effects")?;
    assert!(layout.source().len() > layout.executed_code_positions().len());
    assert!(
        layout
            .data_write_positions()
            .iter()
            .flatten()
            .any(|&write| write < layout.source().len() as u32)
    );
    for input in [Vec::new(), vec![255, 0, 128]] {
        let mut vm =
            ProfileMachine::from_source(profile, layout.source(), input)
                .map_err(|error| format!("guest load: {error:?}"))?;
        assert!(matches!(
            vm.run(layout.executed_code_positions().len()),
            Ok(RunOutcome::Terminated { .. })
        ));
        assert_eq!(vm.output(), expected);
    }
    Ok(())
}

// Independent scalar state enumeration for one finite guest grammar, not
// arbitrary byte synthesis: pristine graphical operands behind one jump.
fn advance_graphical_scratch_states(
    frontier: &GraphicalScratchStates,
    operand_words: &[Vec<u32>],
    scratch_limit: usize,
) -> GraphicalScratchStates {
    let mut next = BTreeSet::new();
    for &(length, accumulator) in frontier {
        if length.saturating_add(2) > scratch_limit {
            continue;
        }
        let address = length.saturating_add(1);
        _ = next.insert((address, accumulator));
        let Some(words) = operand_words.get(address) else {
            continue;
        };
        for &word in words {
            let crazy = malbolge::profile_crazy(word, accumulator, 15);
            let rotated = malbolge::profile_rotate(
                word,
                malbolge::current_profile().memory_words(),
            );
            _ = next.insert((address, crazy));
            _ = next.insert((address, rotated));
        }
    }
    next
}

fn bounded_graphical_scratch_reachability(
    initial: GraphicalScratchStates,
    operand_words: &[Vec<u32>],
    scratch_limit: usize,
    target: Option<u8>,
) -> GraphicalScratchResult {
    let mut frontier = initial;
    let mut output_states = BTreeSet::new();
    let mut reachable_bytes = BTreeSet::new();
    for depth in 0usize..=12usize {
        for &(length, accumulator) in &frontier {
            if length >= scratch_limit {
                continue;
            }
            let Some(low_byte) = u8::try_from(accumulator & 255).ok() else {
                continue;
            };
            _ = reachable_bytes.insert(low_byte);
            if target == Some(low_byte) {
                _ = output_states
                    .insert((length.saturating_add(1), accumulator));
            }
        }
        if depth == 12usize {
            break;
        }
        frontier = advance_graphical_scratch_states(
            &frontier,
            operand_words,
            scratch_limit,
        );
    }
    (output_states, reachable_bytes)
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "assert exact scalar reachability bounds for original C oracle"
)]
fn original_fibonacci_third_byte_exceeds_graphical_scratch_grammar()
-> Result<(), String> {
    let profile = malbolge::current_profile();
    let first = (33u8..=126)
        .find(|&word| {
            malbolge::decode_profile_instruction(u32::from(word), 0)
                == Some(b'i')
        })
        .ok_or("no first jump")?;
    let target = usize::from(first) + 1;
    let scratch_limit = target.checked_sub(2).ok_or("short scratch")?;
    let operand_words = (0..target)
        .map(|address| {
            (33u8..=126)
                .filter(|&word| {
                    matches!(
                        u32::try_from(address).ok().and_then(|phase| {
                            malbolge::decode_profile_instruction(
                                u32::from(word), phase,
                            )
                        }),
                        Some(opcode) if [
                            b'o', b'j', b'p', b'*', b'i', b'v',
                            profile.input_instruction(),
                            profile.output_instruction(),
                        ].contains(&opcode)
                    )
                })
                .map(u32::from)
                .collect::<Vec<_>>()
        })
        .collect::<Vec<_>>();
    let mut states = BTreeSet::from([(0, 0u32)]);
    for byte in [0x02, 0x59] {
        let (completed, _) = bounded_graphical_scratch_reachability(
            states,
            &operand_words,
            scratch_limit,
            Some(byte),
        );
        if completed.is_empty() {
            return Err(format!("source-scratch prefix stopped at {byte:02x}"));
        }
        states = completed;
    }
    let (_, third_bytes) = bounded_graphical_scratch_reachability(
        states,
        &operand_words,
        scratch_limit,
        None,
    );
    assert_eq!(third_bytes.len(), 205);
    assert!(!third_bytes.contains(&0x5f));
    assert!(third_bytes.contains(&0x5d));
    assert!(third_bytes.contains(&0x79));
    Ok(())
}

#[test]
fn delayed_forward_jump_keeps_scratch_writes_behind_code() -> Result<(), String>
{
    let profile = malbolge::current_profile();
    // An initial no-op advances C and D before the source-backed jump. The
    // jump target depends on its actual decoder phase, not phase zero.
    for jump_position in [1usize, 2, 3] {
        let phase = u32::try_from(jump_position).map_err(|e| e.to_string())?;
        let jump_cell = (33u8..=126)
            .find(|&byte| {
                malbolge::decode_profile_instruction(u32::from(byte), phase)
                    == Some(b'i')
            })
            .ok_or("missing delayed jump encoding")?;
        let target = usize::from(jump_cell) + 1;
        let mut operations = vec![LinearOpcode::NoOperation; target];
        operations[jump_position] = LinearOpcode::JumpForward {
            target: u32::try_from(target).map_err(|e| e.to_string())?,
        };
        operations.extend([
            LinearOpcode::CrazyData,
            LinearOpcode::OutputByte,
            LinearOpcode::RotateData,
            LinearOpcode::OutputByte,
            LinearOpcode::Halt,
        ]);
        let layout =
            super::super::encode_linear_layout(profile, &operations)
                .map_err(|error| format!("delayed jump layout: {error:?}"))?;
        assert_eq!(layout.executed_code_positions()[jump_position], phase);
        assert_eq!(
            layout.executed_code_positions()[jump_position + 1],
            target as u32
        );
        let writes: Vec<_> = layout
            .executed_code_positions()
            .iter()
            .zip(layout.data_write_positions())
            .filter_map(|(&code, write)| write.map(|address| (code, address)))
            .collect();
        assert_eq!(writes.len(), 2);
        assert!(writes.iter().all(|&(code, address)| {
            address < code && address < layout.source().len() as u32
        }));
        let mut oracle = None;
        for input in [Vec::new(), vec![255, 0, 128]] {
            let mut vm =
                ProfileMachine::from_source(profile, layout.source(), input)
                    .map_err(|error| format!("guest load: {error:?}"))?;
            assert!(matches!(
                vm.run(layout.executed_code_positions().len()),
                Ok(RunOutcome::Terminated { .. })
            ));
            assert_eq!(vm.input_consumed(), 0);
            assert_eq!(vm.output().len(), 2);
            if let Some(bytes) = &oracle {
                assert_eq!(vm.output(), bytes);
            } else {
                oracle = Some(vm.output().to_vec());
            }
        }
    }
    Ok(())
}

#[test]
fn skipped_jump_and_input_codes_are_inert_guest_data() -> Result<(), String> {
    let profile = malbolge::current_profile();
    let first_jump = (33u8..=126)
        .find(|&byte| {
            malbolge::decode_profile_instruction(u32::from(byte), 0)
                == Some(b'i')
        })
        .ok_or("missing first jump")?;
    let target = u32::from(first_jump) + 1;
    for opcode in [b'i', profile.input_instruction()] {
        let operand = (33u8..=126)
            .find(|&byte| {
                malbolge::decode_profile_instruction(u32::from(byte), 1)
                    == Some(opcode)
            })
            .ok_or("missing loader-valid scratch word")?;
        let mut operations = vec![LinearOpcode::NoOperation; target as usize];
        operations[0] = LinearOpcode::JumpForward { target };
        operations[1] =
            LinearOpcode::SkippedDataByte { byte: u32::from(operand) };
        operations.extend([
            LinearOpcode::CrazyData,
            LinearOpcode::OutputByte,
            LinearOpcode::Halt,
        ]);
        let layout = super::super::encode_linear_layout(profile, &operations)
            .map_err(|error| format!("scratch layout: {error:?}"))?;
        assert_eq!(
            layout
                .data_write_positions()
                .iter()
                .flatten()
                .copied()
                .collect::<Vec<_>>(),
            [1]
        );
        let result = malbolge::profile_crazy(u32::from(operand), 0, 15) as u8;
        for input in [Vec::new(), vec![255, 0, 128]] {
            let mut vm =
                ProfileMachine::from_source(profile, layout.source(), input)
                    .map_err(|error| format!("guest load: {error:?}"))?;
            assert!(matches!(
                vm.run(layout.executed_code_positions().len()),
                Ok(RunOutcome::Terminated { .. })
            ));
            assert_eq!(vm.output(), [result]);
            assert_eq!(vm.input_consumed(), 0);
        }
    }
    Ok(())
}

#[test]
fn delayed_jump_replays_complete_source_fibonacci() -> Result<(), String> {
    // This unsigned-C recurrence is independent of the guest proposal.
    let mut previous = 1u32;
    let mut current = 1u32;
    let mut expected = [0u8; 12];
    for output in &mut expected {
        let next = previous.wrapping_add(current) & 255;
        *output = u8::try_from(
            (if next & 1 == 0 {
                next
            } else {
                next ^ 0x1a
            }) & 31,
        )
        .map_err(|error| error.to_string())?;
        previous = current;
        current = next;
    }
    assert_eq!(expected, [
        0x02, 0x19, 0x1f, 0x08, 0x17, 0x0f, 0x02, 0x0d, 0x03, 0x10, 0x13, 0x03,
    ]);
    let profile = malbolge::current_profile();
    let layout =
        verified_variable_source_scratch_at_jump(profile, expected, 1, 0)
            .ok_or("missing delayed guest scratch proof")?;
    assert_eq!(layout.executed_code_positions()[..2], [0, 1]);
    assert!(layout.executed_code_positions()[2] > 2);
    assert_eq!(layout.executed_code_positions().len(), 47);
    assert!(
        layout
            .data_write_positions()
            .iter()
            .flatten()
            .all(|&write| { write < layout.source().len() as u32 })
    );
    for input in [Vec::new(), vec![255, 0, 128]] {
        let mut vm =
            ProfileMachine::from_source(profile, layout.source(), input)
                .map_err(|error| format!("guest load: {error:?}"))?;
        assert!(matches!(
            vm.run(47),
            Ok(RunOutcome::Terminated { steps: 47, .. })
        ));
        assert_eq!(vm.output(), expected);
        assert_eq!(vm.input_consumed(), 0);
    }
    assert!(
        verified_variable_source_scratch_at_jump(
            profile,
            [0x02, 0x59, 0x5f],
            1,
            0,
        )
        .is_none()
    );
    Ok(())
}

#[test]
fn leading_zero_outputs_precede_real_scratch_jump() -> Result<(), String> {
    // A source statement can emit an initial NUL before a bounded C loop.
    // It is an actual reached guest output instruction, not a host prefix.
    let expected = [0, 0, 2, 25, 31, 8, 23, 15, 2, 13, 3, 16];
    let profile = malbolge::current_profile();
    let layout =
        verified_variable_source_scratch_at_jump(profile, expected, 2, 2)
            .ok_or("missing two source-proven NUL effects")?;
    assert_eq!(layout.executed_code_positions()[..3], [0, 1, 2]);
    assert!(layout.executed_code_positions()[3] > 3);
    for input in [Vec::new(), vec![0, 255, 128]] {
        let mut vm =
            ProfileMachine::from_source(profile, layout.source(), input)
                .map_err(|error| format!("guest load: {error:?}"))?;
        assert!(matches!(
            vm.run(layout.executed_code_positions().len()),
            Ok(RunOutcome::Terminated { .. })
        ));
        assert_eq!(vm.output(), expected);
        assert_eq!(vm.input_consumed(), 0);
    }
    assert!(
        verified_variable_source_scratch_at_jump(profile, expected, 2, 3,)
            .is_none()
    );
    assert!(
        verified_variable_source_scratch_at_jump(profile, [2, 0, 2], 2, 1,)
            .is_none()
    );
    Ok(())
}

#[test]
fn relocated_scratch_guest_executes_three_distinct_bytes() -> Result<(), String>
{
    let profile = malbolge::current_profile();
    let expected = [0x02, 0x59, 0x5d];
    let layout =
        verified_relocated_source_scratch_at_jump(profile, expected, 0)
            .ok_or("missing relocated scratch guest witness")?;
    let points = layout.data_pointer_positions();
    assert!(points.windows(2).any(|pair| pair[1] > pair[0] + 1));
    assert!(
        layout
            .data_write_positions()
            .iter()
            .flatten()
            .all(|&write| { write < layout.source().len() as u32 })
    );
    for input in [Vec::new(), vec![255, 0, 128]] {
        let mut vm =
            ProfileMachine::from_source(profile, layout.source(), input)
                .map_err(|error| format!("VM load: {error:?}"))?;
        assert!(matches!(
            vm.run(layout.executed_code_positions().len()),
            Ok(RunOutcome::Terminated { .. })
        ));
        assert_eq!(vm.output(), expected);
        assert_eq!(vm.input_consumed(), 0);
    }
    Ok(())
}
