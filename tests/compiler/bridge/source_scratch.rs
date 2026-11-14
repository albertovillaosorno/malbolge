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
fn source_scratch_retries_rejected_completion() -> Result<(), String> {
    // A complete accumulator/output trace is a proposal, not a guest proof.
    // The first terminal geometry can fail positional decoding while a later
    // source length gives a distinct candidate for the checker to admit.
    let cells = pair_source_cells(malbolge::current_profile())
        .ok_or("missing decoder phases")?;
    let mut rejected = None;
    let mut checks = 0;
    let accepted = proposed_source_scratch_with_checker(&cells, [0], |ops| {
        checks += 1;
        if rejected.is_none() {
            rejected = Some(ops.to_vec());
            None
        } else {
            Some(ops.to_vec())
        }
    })
    .ok_or("second completed source-scratch path was abandoned")?;
    assert_eq!(checks, 2);
    assert_ne!(rejected.ok_or("no rejected candidate")?, accepted);
    assert!(matches!(accepted.last(), Some(LinearOpcode::Halt)));
    Ok(())
}

#[test]
fn source_scratch_rejects_all_unverified_completions_with_bounded_work()
-> Result<(), String> {
    let cells = pair_source_cells(malbolge::current_profile())
        .ok_or("missing decoder phases")?;
    let mut checks = 0;
    let rejected: Option<Vec<LinearOpcode>> =
        proposed_source_scratch_with_checker(&cells, [0], |_| {
            checks += 1;
            None
        });
    assert!(rejected.is_none());
    assert_eq!(checks, MAX_COMPLETION_CHECKS_PER_GEOMETRY);
    Ok(())
}

#[test]
fn variable_scratch_retries_rejected_completed_path() -> Result<(), String> {
    // Two distinct full traces can have the same observable output.
    // A failed positional encoding is not a proof against the next trace.
    let profile = malbolge::current_profile();
    let mut first = None;
    let mut attempts = 0;
    let second = proposed_variable_source_scratch_at_jump_with_checker(
        profile,
        [0],
        0,
        0,
        |operations| {
            attempts += 1;
            if first.is_none() {
                first = Some(operations.to_vec());
                None
            } else {
                Some(operations.to_vec())
            }
        },
    )
    .ok_or("lost alternate source-scratch proposal")?;
    assert_eq!(attempts, 2);
    assert_ne!(first.ok_or("missing rejected proposal")?, second);
    Ok(())
}

#[test]
fn variable_scratch_all_rejected_completions_are_bounded() {
    let profile = malbolge::current_profile();
    let mut attempts = 0;
    let rejected: Option<Vec<LinearOpcode>> =
        proposed_variable_source_scratch_at_jump_with_checker(
            profile,
            [0],
            0,
            0,
            |_| {
                attempts += 1;
                None
            },
        );
    assert!(rejected.is_none());
    assert_eq!(attempts, MAX_COMPLETION_CHECKS_PER_GEOMETRY);
}

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
        states.clone(),
        &operand_words,
        scratch_limit,
        None,
    );
    assert_eq!(third_bytes.len(), 205);
    assert!(!third_bytes.contains(&0x5f));
    // The exact finite grammar below includes every forward relocation,
    // not just twelve arithmetic steps after the prior two output effects.
    let (complete, states) = fresh_graphical_scratch_reachability(
        profile,
        &operand_words,
        scratch_limit,
        [2, 89, 95],
    );
    assert_eq!(states, 96_732);
    assert!(!complete);
    // A positive control is independently executed as an 11-step guest in
    // relocated_scratch_guest_executes_three_distinct_bytes.
    let (reachable_control, _) = fresh_graphical_scratch_reachability(
        profile,
        &operand_words,
        scratch_limit,
        [2, 89, 93],
    );
    assert!(reachable_control);
    assert!(third_bytes.contains(&0x5d));
    assert!(third_bytes.contains(&0x79));
    Ok(())
}

/// Exhaust the fresh graphical scratch gap after a phase-zero code jump.
///
/// The exact accumulator and next output index are keyed by the data pointer.
/// Source cells are independently selected from all eight loader-valid bytes
/// for their decoder phases. Any number of strictly forward `j` relocations
/// may skip untouched operands; D always increases, so the graph is acyclic.
/// Writes to past cells do occur, but no rewritten operand can be revisited.
/// Backward relocation, a different jump geometry and expanded memory remain
/// excluded. This is a complete result only for that finite guest grammar.
fn fresh_graphical_scratch_reachability(
    profile: &ProfileDescriptor,
    operands: &[Vec<u32>],
    scratch_limit: usize,
    expected: [u8; 3],
) -> (bool, usize) {
    let mut layers = vec![BTreeSet::<(u32, usize)>::new(); scratch_limit + 2];
    _ = layers[1].insert((0, 0));
    let mut explored = 0usize;
    let mut completed = false;
    for at in 1..=scratch_limit {
        let states = std::mem::take(&mut layers[at]);
        explored += states.len();
        for (accumulator, emitted) in states {
            if emitted == expected.len() {
                completed = true;
                continue;
            }
            if u8::try_from(accumulator & 255).ok() == Some(expected[emitted]) {
                _ = layers[at + 1].insert((accumulator, emitted + 1));
            }
            if at == scratch_limit {
                continue;
            }
            _ = layers[at + 1].insert((accumulator, emitted));
            for &word in &operands[at] {
                _ = layers[at + 1].insert((
                    malbolge::profile_crazy(
                        word,
                        accumulator,
                        profile.word_trits(),
                    ),
                    emitted,
                ));
                _ = layers[at + 1].insert((
                    malbolge::profile_rotate(word, profile.memory_words()),
                    emitted,
                ));
                let destination = word as usize + 1;
                if destination > at + 1 && destination <= scratch_limit {
                    _ = layers[destination].insert((accumulator, emitted));
                }
            }
        }
    }
    completed |= layers[scratch_limit + 1]
        .iter()
        .any(|&(_, emitted)| emitted == expected.len());
    (completed, explored)
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
    assert_eq!(layout.source().len(), 109);
    assert_eq!(layout.executed_code_positions().len(), 11);
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

#[test]
fn scratch_written_pointer_reaches_loader_expansion() -> Result<(), String> {
    let profile = malbolge::current_profile();
    let cells = pair_source_cells(profile).ok_or("missing decoder cells")?;
    let prefix =
        verified_source_scratch_output_layout(profile, [2, 89], &cells)
            .ok_or("missing source-proven Fibonacci prefix")?;
    let target = usize::try_from(prefix.executed_code_positions()[1])
        .map_err(|error| error.to_string())?;
    let mut operations = vec![LinearOpcode::NoOperation; target];
    operations[0] = LinearOpcode::JumpForward {
        target: u32::try_from(target).map_err(|error| error.to_string())?,
    };
    for (index, &source_byte) in
        prefix.source().iter().enumerate().take(target).skip(1)
    {
        operations[index] = LinearOpcode::SkippedDataByte {
            byte: u32::from(source_byte),
        };
    }
    let reached = prefix.executed_code_positions();
    for &code in &reached[1..reached.len() - 1] {
        let source_byte = prefix.source()[code as usize];
        let decoded =
            malbolge::decode_profile_instruction(u32::from(source_byte), code)
                .ok_or("missing reached decoder")?;
        operations.push(match decoded {
            b'o' => LinearOpcode::NoOperation,
            b'p' => LinearOpcode::CrazyData,
            b'*' => LinearOpcode::RotateData,
            output if output == profile.output_instruction() => {
                LinearOpcode::OutputByte
            },
            _ => return Err(format!("unexpected reached opcode {decoded}")),
        });
    }
    // The final original output leaves D=84. A genuine rotate at D=85
    // writes a 15-trit value into skipped graphical source memory. The
    // source-backed j at D=91 reads graphical 84 and moves back to D=85;
    // a second j reads the *changed* word and enters expanded memory.
    assert_eq!(prefix.data_pointer_positions().last(), Some(&84));
    operations[91] = LinearOpcode::SkippedDataByte { byte: 84 };
    for at in 84..91 {
        operations.push(if at == 85 {
            LinearOpcode::RotateData
        } else {
            LinearOpcode::NoOperation
        });
    }
    operations.extend([
        LinearOpcode::RelocateDataPointer,
        LinearOpcode::RelocateDataPointer,
        LinearOpcode::OutputByte,
        LinearOpcode::Halt,
    ]);
    let layout = super::super::encode_linear_layout(profile, &operations)
        .map_err(|error| format!("scratch relocation: {error:?}"))?;
    assert_eq!(layout.source().len(), 193);
    let pointers = layout.data_pointer_positions();
    assert_eq!(&pointers[pointers.len() - 4..], &[
        91, 85, 9_565_964, 9_565_965
    ]);
    assert!(9_565_964 > layout.source().len());
    assert!(
        layout
            .data_write_positions()
            .iter()
            .flatten()
            .any(|&at| at == 85)
    );
    for input in [Vec::new(), vec![255, 0, 128]] {
        let mut vm =
            ProfileMachine::from_source(profile, layout.source(), input)
                .map_err(|error| format!("guest load: {error:?}"))?;
        assert!(matches!(
            vm.run(layout.executed_code_positions().len()),
            Ok(RunOutcome::Terminated { steps: 95, .. })
        ));
        assert_eq!(vm.output(), [2, 89, 11]);
        assert_eq!(vm.input_consumed(), 0);
    }
    // An output immediately after the second j only observes A left by
    // the scratch write. Prove genuine arithmetic *after* that relocation:
    // p writes a loader-expanded operand and * reads another disjoint word.
    // Neither effect is a host-precomputed suffix or source-byte write.
    let mut expanded_operations = operations;
    expanded_operations.truncate(expanded_operations.len() - 2);
    expanded_operations.extend([
        LinearOpcode::CrazyData,
        LinearOpcode::OutputByte,
        LinearOpcode::RotateData,
        LinearOpcode::OutputByte,
        LinearOpcode::Halt,
    ]);
    let expanded =
        super::super::encode_linear_layout(profile, &expanded_operations)
            .map_err(|error| {
                format!("expanded scratch arithmetic: {error:?}")
            })?;
    let pointers = expanded.data_pointer_positions();
    let first = pointers[pointers.len() - 5];
    let second = pointers[pointers.len() - 3];
    assert_eq!(second, first + 2);
    assert!(first > expanded.source().len() as u32);
    let writes = expanded
        .data_write_positions()
        .iter()
        .flatten()
        .copied()
        .collect::<BTreeSet<_>>();
    let earlier_writes = layout
        .data_write_positions()
        .iter()
        .flatten()
        .copied()
        .collect::<BTreeSet<_>>();
    assert_eq!(writes.len(), earlier_writes.len() + 2);
    assert!(writes.contains(&85));
    assert!(writes.contains(&first));
    assert!(writes.contains(&second));
    let first_word = super::super::layout::unwritten_loader_word(
        expanded.source(),
        first as usize,
        profile,
    )
    .map_err(|error| format!("first loader word: {error:?}"))?;
    let second_word = super::super::layout::unwritten_loader_word(
        expanded.source(),
        second as usize,
        profile,
    )
    .map_err(|error| format!("second loader word: {error:?}"))?;
    let seed = malbolge::profile_rotate(
        u32::from(expanded.source()[85]),
        profile.memory_words(),
    );
    let third = malbolge::profile_crazy(first_word, seed, 15) as u8;
    let fourth =
        malbolge::profile_rotate(second_word, profile.memory_words()) as u8;
    assert_ne!(third, 11);
    let expected = [2, 89, third, fourth];
    assert_eq!(expected, [2, 89, 185, 182]);
    for input in [Vec::new(), vec![255, 0, 128]] {
        let mut vm =
            ProfileMachine::from_source(profile, expanded.source(), input)
                .map_err(|error| format!("expanded guest load: {error:?}"))?;
        assert!(matches!(
            vm.run(expanded.executed_code_positions().len()),
            Ok(RunOutcome::Terminated { steps: 98, .. })
        ));
        assert_eq!(vm.output(), expected);
        assert_eq!(vm.input_consumed(), 0);
    }
    // Negative bound for the original unmasked C recurrence's third byte.
    // The initial [2, 89] is an independently executed guest prefix above.
    // Search untouched expanded loader words, allowing up to two more live
    // data relocations and twelve no-op/arithmetic/relocation instructions.
    // The scalar graph deliberately overapproximates guest admission: it does
    // not reject paths that reread written cells or unsafe final operations.
    // Thus absence below rules out this fresh-word grammar, not arbitrary
    // source mutations, graphical writes, or general Malbolge execution.
    let base_length = expanded_operations.len() - 5;
    let data_start =
        usize::try_from(first).map_err(|error| error.to_string())?;
    let memory_words = usize::try_from(profile.memory_words())
        .map_err(|error| error.to_string())?;
    let mut reachable_bytes = BTreeSet::new();
    for terminal in [b'o', b'p', b'*', b'j'] {
        for length in 0..=12usize {
            let source_length = base_length + length + 3;
            let tail = [
                (33u8..=126)
                    .find(|&byte| {
                        malbolge::decode_profile_instruction(
                            u32::from(byte),
                            u32::try_from(source_length - 2)
                                .unwrap_or(u32::MAX),
                        ) == Some(terminal)
                    })
                    .ok_or("missing final guest instruction")?,
                (33u8..=126)
                    .find(|&byte| {
                        malbolge::decode_profile_instruction(
                            u32::from(byte),
                            u32::try_from(source_length - 1)
                                .unwrap_or(u32::MAX),
                        ) == Some(b'v')
                    })
                    .ok_or("missing guest halt encoding")?,
            ];
            let mut frontier = BTreeSet::from([(data_start, seed, 0u8)]);
            for _ in 0..length {
                let mut next = BTreeSet::new();
                for (pointer, accumulator, relocations) in frontier {
                    if pointer < source_length || pointer >= memory_words {
                        continue;
                    }
                    let word = super::super::layout::unwritten_loader_word(
                        &tail,
                        2 + ((pointer - source_length) % 6),
                        profile,
                    )
                    .map_err(|error| format!("loader recurrence: {error:?}"))?;
                    let choices = [
                        (pointer + 1, accumulator, relocations),
                        (
                            pointer + 1,
                            malbolge::profile_crazy(word, accumulator, 15),
                            relocations,
                        ),
                        (
                            pointer + 1,
                            malbolge::profile_rotate(
                                word,
                                profile.memory_words(),
                            ),
                            relocations,
                        ),
                        (
                            (usize::try_from(word)
                                .map_err(|error| error.to_string())?
                                + 1)
                                % memory_words,
                            accumulator,
                            relocations + 1,
                        ),
                    ];
                    for (index, (pointer, accumulator, used)) in
                        choices.into_iter().enumerate()
                    {
                        if (index == 3 && relocations == 2)
                            || pointer < source_length
                        {
                            continue;
                        }
                        _ = next.insert((pointer, accumulator, used));
                    }
                }
                frontier = next;
            }
            reachable_bytes.extend(frontier.into_iter().map(
                |(_, accumulator, _)| {
                    u8::try_from(accumulator & 255).unwrap_or(0)
                },
            ));
        }
    }
    assert!(reachable_bytes.len() > 20);
    assert!(!reachable_bytes.contains(&0x5f));
    Ok(())
}
