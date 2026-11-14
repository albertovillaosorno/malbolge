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
//   - Independent original-C Fibonacci prefix and guest loopback evidence.
// - Must-Not:
//   - Substitute host output for guest computation or weaken layout admission.
// - Allows:
//   - Inputs: source-proven unsigned C recurrence and graphical source cells.
//   - Outputs: independently admitted and VM-checked real guest output bytes.
//   - Side effects: bounded normative VM execution only.
// - Split-When:
//   - General source-scratch synthesis subsumes data-write/relocation search.
// - Merge-When:
//   - Complete unmasked C Fibonacci reaches the production guest compiler.
// - Summary:
//   - A real write and live j escape the pristine graphical byte restriction.

use super::super::{ProfileMachine, RunOutcome, encode_linear_layout};
use super::*;

/// Independently evaluate the complete C recurrence, without host output.
fn original_fibonacci_bytes() -> [u8; 12] {
    let (mut a, mut b) = (1u32, 1u32);
    let mut expected = [0u8; 12];
    for output in &mut expected {
        let next = (a + b) & 255;
        *output = (if next & 1 == 0 {
            next
        } else {
            next ^ 0x5a
        }) as u8;
        a = b;
        b = next;
    }
    expected
}

/// Reconstruct reached operations from the independent positional decoder;
/// the original two-byte source is only a search seed, never a guest oracle.
fn decode_prefix_operations(
    source: &[u8],
    jump_target: usize,
) -> Result<Vec<LinearOpcode>, String> {
    let mut operations = Vec::with_capacity(source.len());
    for (address, &byte) in source.iter().enumerate() {
        let operation = if address == 0 {
            LinearOpcode::JumpForward {
                target: u32::try_from(jump_target)
                    .map_err(|error| error.to_string())?,
            }
        } else if address < jump_target {
            LinearOpcode::SkippedDataByte { byte: u32::from(byte) }
        } else {
            match malbolge::decode_profile_instruction(
                u32::from(byte),
                address as u32,
            ) {
                Some(b'o') => LinearOpcode::NoOperation,
                Some(b'p') => LinearOpcode::CrazyData,
                Some(b'*') => LinearOpcode::RotateData,
                Some(b'<') => LinearOpcode::OutputByte,
                Some(b'v') => LinearOpcode::Halt,
                other => {
                    return Err(format!(
                        "unproved reached opcode {other:?} at {address}"
                    ));
                },
            }
        };
        operations.push(operation);
    }
    if operations.pop() != Some(LinearOpcode::Halt) {
        return Err(String::from("two-byte source is not terminated"));
    }
    Ok(operations)
}

#[test]
fn dense_revisited_source_frontier_preserves_early_progress_and_high_words() {
    // Old advanced-first truncation filled the entire cap with states
    // at emitted counts 8 through 5, leaving no candidate at count 3.
    let states = (3usize..9)
        .flat_map(|emitted| {
            (0u32..4_096)
                .map(move |high| ((emitted, high * 256 + 3), high as usize))
        })
        .collect::<BTreeMap<_, _>>();
    assert!(states.len() > 16_384);
    let bounded = bounded_revisit_states(&states, 3, 9, 16_384);
    assert_eq!(bounded.len(), 16_384);
    for emitted in 3..9 {
        assert!(bounded.contains_key(&(emitted, 3)));
        assert!(bounded.contains_key(&(emitted, 4_095 * 256 + 3)));
    }
    // A smaller exact frontier is not subjected to any heuristic beam.
    let sparse = states
        .iter()
        .take(100)
        .map(|(&key, &index)| (key, index))
        .collect::<BTreeMap<_, _>>();
    assert_eq!(bounded_revisit_states(&sparse, 3, 9, 16_384), sparse);
}

#[test]
fn revisited_frontier_history_keeps_only_surviving_predecessors() {
    // The first speculative layer has more than the 16,384-state beam cap.
    // Discarded candidates must not accumulate permanent history entries,
    // nor may a second layer lose its retained predecessor indices.
    let candidates = (3usize..9)
        .flat_map(|emitted| {
            (0u32..4_096)
                .map(move |high| ((emitted, high * 256 + 3), high as usize))
        })
        .collect::<BTreeMap<_, _>>();
    let mut history = vec![usize::MAX];
    let first = append_revisit_links(&mut history, candidates, 3, 9, 16_384);
    assert_eq!(first.len(), 16_384);
    assert_eq!(history.len(), 1 + 16_384);
    for (&(_, accumulator), &link) in &first {
        assert_eq!(history[link], (accumulator / 256) as usize);
    }

    let next = first
        .iter()
        .map(|(&key, &predecessor)| (key, predecessor))
        .collect::<BTreeMap<_, _>>();
    let second = append_revisit_links(&mut history, next, 3, 9, 16_384);
    assert_eq!(second.len(), 16_384);
    assert_eq!(history.len(), 1 + 2 * 16_384);
    let first_links = first.values().copied().collect::<BTreeSet<_>>();
    for &link in second.values() {
        let predecessor = history[link];
        assert!(first_links.contains(&predecessor));
    }
}

#[test]
fn completed_revisit_stream_survives_dense_beam_for_later_halt() {
    // All outputs can precede the first position-encodable final halt.
    // A failed early layout must not discard completed search states.
    let candidates = (3usize..=9)
        .flat_map(|emitted| {
            (0u32..4_096)
                .map(move |high| ((emitted, high * 256 + 3), high as usize))
        })
        .collect::<BTreeMap<_, _>>();
    assert!(candidates.len() > 16_384);
    let mut history = vec![usize::MAX];
    let retained = append_revisit_links(&mut history, candidates, 3, 9, 16_384);
    assert_eq!(retained.len(), 16_384);
    for accumulator in [3, 259, 4_095 * 256 + 3] {
        assert!(
            retained.contains_key(&(9, accumulator)),
            "lost completed guest accumulator {accumulator}",
        );
    }
    // A padding no-op must retain the completed path and its predecessor.
    let next = retained
        .iter()
        .map(|(&key, &predecessor)| (key, predecessor))
        .collect::<BTreeMap<_, _>>();
    let padded = append_revisit_links(&mut history, next, 3, 9, 16_384);
    let link = padded[&(9, 259)];
    assert_eq!(history[link], retained[&(9, 259)]);
}

#[test]
fn dense_revisited_frontier_retains_middle_word_at_earlier_progress() {
    // The real crazy transition from high word 259 to byte 53 remains
    // useful even when other paths have already emitted more bytes.
    // Advanced-first filling formerly left only the extremes at count 3.
    let states = (3usize..9)
        .flat_map(|emitted| {
            (0u32..4_096)
                .map(move |high| ((emitted, high * 256 + 3), high as usize))
        })
        .collect::<BTreeMap<_, _>>();
    assert!(states.len() > 16_384);
    let changed = malbolge::profile_crazy(0, 259, 15);
    assert_eq!(changed & 255, 53);
    let bounded = bounded_revisit_states(&states, 3, 9, 16_384);
    assert_eq!(bounded.len(), 16_384);
    for emitted in 3..9 {
        assert!(
            bounded.contains_key(&(emitted, 259)),
            "lost middle full-word continuation at output count {emitted}",
        );
    }
}

#[test]
fn original_fibonacci_third_byte_reaches_real_guest_through_written_source()
-> Result<(), String> {
    let expected = original_fibonacci_bytes();
    assert_eq!(expected, [2, 89, 95, 8, 87, 79, 34, 109, 3, 144, 179, 35]);
    let profile = malbolge::current_profile();
    let prefix = verified_variable_source_scratch_at_jump(
        profile,
        [expected[0], expected[1]],
        0,
        0,
    )
    .ok_or("no original C two-byte guest prefix")?;
    let mut machine =
        ProfileMachine::from_source(profile, prefix.source(), Vec::new())
            .map_err(|error| format!("prefix load: {error:?}"))?;
    let _prefix_run = machine
        .run(prefix.executed_code_positions().len() - 1)
        .map_err(|error| format!("prefix execute: {error:?}"))?;
    if machine.output() != &expected[..2] {
        return Err(String::from("C prefix did not execute on actual VM"));
    }
    // D is 6 before the seed's final halt. A no-op advances D one cell;
    // this intentionally moves it to the previously skipped source at 67.
    let initial_data_pointer =
        usize::try_from(machine.registers().data_pointer)
            .map_err(|error| error.to_string())?;
    let scratch = 67usize;
    if initial_data_pointer != 6 || prefix.source().len() != 105 {
        return Err(String::from("source-scratch prefix geometry drifted"));
    }
    let mut operations = decode_prefix_operations(prefix.source(), 99)?;
    // The first guest * replaces a graphical word with a full rotated word.
    // The following j reads source[68] == 66 and returns D to source[67].
    // The second * and real p operations now consume guest-evolved data.
    for (address, byte) in
        [(67usize, 95u32), (68, 66), (69, 93), (70, 92), (71, 104)]
    {
        operations[address] = LinearOpcode::SkippedDataByte { byte };
    }
    operations.extend(repeat_n(
        LinearOpcode::NoOperation,
        scratch - initial_data_pointer,
    ));
    operations.extend([
        LinearOpcode::RotateData,
        LinearOpcode::RelocateDataPointer,
        LinearOpcode::RotateData,
        LinearOpcode::CrazyData,
        LinearOpcode::CrazyData,
        LinearOpcode::CrazyData,
        LinearOpcode::CrazyData,
        LinearOpcode::OutputByte,
        LinearOpcode::Halt,
    ]);
    let guest =
        encode_linear_layout(profile, &operations).map_err(|error| {
            format!("independent source/relocation admission: {error:?}")
        })?;
    assert_eq!(guest.source().len(), operations.len());
    assert_eq!(guest.data_write_positions().iter().flatten().count(), 9);
    for input in [Vec::new(), vec![255, 0, 128]] {
        let mut vm =
            ProfileMachine::from_source(profile, guest.source(), input)
                .map_err(|error| format!("normative VM load: {error:?}"))?;
        let outcome = vm
            .run(guest.executed_code_positions().len())
            .map_err(|error| format!("normative VM replay: {error:?}"))?;
        if !matches!(outcome, RunOutcome::Terminated { steps, .. }
            if steps == guest.executed_code_positions().len())
            || vm.output() != &expected[..3]
            || vm.input_consumed() != 0
        {
            return Err(format!("real C prefix guest diverged: {outcome:?}"));
        }
    }
    Ok(())
}

#[test]
fn original_fibonacci_third_byte_is_found_by_bounded_revisit_search()
-> Result<(), String> {
    let profile = malbolge::current_profile();
    let expected = original_fibonacci_bytes();
    let triple = [expected[0], expected[1], expected[2]];
    let layout = verified_revisited_source_scratch_triple(profile, triple)
        .ok_or("source-scratch revisit search missed full-width guest")?;
    assert!(layout.source().len() > 105);
    assert_eq!(
        layout
            .data_write_positions()
            .iter()
            .flatten()
            .copied()
            .collect::<BTreeSet<_>>()
            .len(),
        layout.data_write_positions().iter().flatten().count() - 1,
        "one already-written guest source cell must be revisited",
    );
    let writes = layout.data_write_positions();
    let repeated = writes
        .iter()
        .flatten()
        .find(|&&address| {
            writes
                .iter()
                .filter(|&&write| write == Some(address))
                .count()
                == 2
        })
        .copied()
        .ok_or("missing repeated guest source write")?;
    let repeated_steps = writes
        .iter()
        .enumerate()
        .filter_map(|(step, &write)| (write == Some(repeated)).then_some(step))
        .collect::<Vec<_>>();
    assert_eq!(repeated_steps.len(), 2);
    assert!(
        usize::try_from(repeated)
            .ok()
            .is_some_and(|at| { at < usize::from(layout.source()[0]) + 1 })
    );
    for &step in &repeated_steps {
        let code = layout.executed_code_positions()[step];
        assert_eq!(
            malbolge::decode_profile_instruction(
                u32::from(layout.source()[code as usize]),
                code,
            ),
            Some(b'*'),
            "both source-cell writes must be real rotations",
        );
    }
    let relocation = layout.executed_code_positions()[repeated_steps[1] - 1];
    assert_eq!(
        malbolge::decode_profile_instruction(
            u32::from(layout.source()[relocation as usize]),
            relocation,
        ),
        Some(b'j'),
        "the second rotation must follow a real D relocation",
    );
    for input in [Vec::new(), vec![0, 255, 128]] {
        let mut guest =
            ProfileMachine::from_source(profile, layout.source(), input)
                .map_err(|error| format!("guest loading: {error:?}"))?;
        let result = guest
            .run(layout.executed_code_positions().len())
            .map_err(|error| format!("guest execution: {error:?}"))?;
        assert!(matches!(
            result,
            RunOutcome::Terminated { steps, .. }
                if steps == layout.executed_code_positions().len()
        ));
        assert_eq!(guest.output(), triple);
        assert_eq!(guest.input_consumed(), 0);
    }
    Ok(())
}

#[test]
fn original_fibonacci_fourth_byte_follows_a_written_source_revisit()
-> Result<(), String> {
    let expected = original_fibonacci_bytes();
    let four = [expected[0], expected[1], expected[2], expected[3]];
    let profile = malbolge::current_profile();
    let layout = verified_revisited_source_scratch_quad(profile, four)
        .ok_or("cannot extend source-revisited guest with a fourth byte")?;
    assert_eq!(four, [2, 89, 95, 8]);
    assert!(layout.source().len() > 105);
    assert_eq!(
        layout
            .data_write_positions()
            .iter()
            .flatten()
            .copied()
            .collect::<BTreeSet<_>>()
            .len()
            + 1,
        layout.data_write_positions().iter().flatten().count(),
        "the source-revisit write remains a real alias",
    );
    for supplied in [Vec::new(), vec![0, 255, 128]] {
        let mut vm =
            ProfileMachine::from_source(profile, layout.source(), supplied)
                .map_err(|error| {
                    format!("four-output guest load: {error:?}")
                })?;
        let result = vm
            .run(layout.executed_code_positions().len())
            .map_err(|error| format!("four-output guest run: {error:?}"))?;
        assert!(matches!(
            result,
            RunOutcome::Terminated { steps, .. }
                if steps == layout.executed_code_positions().len()
        ));
        assert_eq!(vm.output(), four);
        assert_eq!(vm.input_consumed(), 0);
    }
    Ok(())
}

#[test]
fn original_fibonacci_complete_stream_from_relocated_source_scratch()
-> Result<(), String> {
    let expected = original_fibonacci_bytes();
    let profile = malbolge::current_profile();
    let layout = verified_revisited_source_scratch_stream(profile, expected)
        .ok_or("complete original guest stream not found")?;
    let relocations = layout
        .executed_code_positions()
        .iter()
        .filter(|&&position| {
            malbolge::decode_profile_instruction(
                u32::from(layout.source()[position as usize]),
                position,
            ) == Some(b'j')
        })
        .count();
    assert_eq!(relocations, 2, "guest must execute both real D relocations");
    let writes = layout
        .data_write_positions()
        .iter()
        .flatten()
        .copied()
        .collect::<Vec<_>>();
    assert!(
        writes.len() > writes.iter().copied().collect::<BTreeSet<_>>().len(),
        "the guest must compute through a previously written source cell"
    );
    for supplied in [Vec::new(), vec![255, 0, 128]] {
        let mut vm =
            ProfileMachine::from_source(profile, layout.source(), supplied)
                .map_err(|error| format!("complete guest load: {error:?}"))?;
        let result = vm
            .run(layout.executed_code_positions().len())
            .map_err(|error| format!("complete guest run: {error:?}"))?;
        assert!(matches!(result, RunOutcome::Terminated { steps, .. }
            if steps == layout.executed_code_positions().len()));
        assert_eq!(vm.output(), expected);
        assert_eq!(vm.input_consumed(), 0);
    }
    Ok(())
}

#[test]
fn dense_revisited_frontier_preserves_middle_words_across_byte_classes() {
    // With many output-byte classes, the per-count quota fills with low
    // accumulator words. A middle full word from a later class can be the
    // only one of its three representatives that reaches the next byte.
    let middle = 32 * 256 + 3;
    assert_eq!(malbolge::profile_crazy(0, 3, 15) & 255, 50);
    assert_eq!(malbolge::profile_crazy(0, middle, 15) & 255, 93);
    assert_eq!(malbolge::profile_crazy(0, 64 * 256 + 3, 15) & 255, 223);
    let states = (3usize..9)
        .flat_map(|emitted| {
            (0u32..=64).flat_map(move |high| {
                (0u32..=255).map(move |byte| {
                    ((emitted, high * 256 + byte), high as usize)
                })
            })
        })
        .collect::<BTreeMap<_, _>>();
    assert!(states.len() > 16_384);
    let bounded = bounded_revisit_states(&states, 3, 9, 16_384);
    assert_eq!(bounded.len(), 16_384);
    for emitted in 3..9 {
        assert!(
            bounded.contains_key(&(emitted, middle)),
            "lost full-word crazy continuation at output count {emitted}",
        );
        for byte in 0..=255 {
            assert!(
                bounded.contains_key(&(emitted, 32 * 256 + byte)),
                "lost midpoint for progress/byte {emitted}/{byte}",
            );
        }
    }
}
