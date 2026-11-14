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
//   - Independent guest verification for an alternate terminal search shape.
// - Must-Not:
//   - Treat cached loader tails as proof of emitted machine code.
// - Allows:
//   - Inputs: a source-independent relocated byte-output guest.
//   - Outputs: exact proposed bytes and independently replayed guest source.
//   - Side effects: none.
// - Split-When:
//   - Terminal shape search becomes a separate verified synthesis engine.
// - Merge-When:
//   - The generalized search contract proves all terminal layout shapes.
// - Summary:
//   - A no-op before halt changes expanded memory without changing outputs.

use super::super::{
    ProfileMachine, RunOutcome, encode_linear_layout, pair_source_cells,
    proposed_output_stream,
};
use super::*;

const PREFIX: usize = 8;

struct ReconstructedTerminal {
    expected: [u8; 4],
    operations: Vec<LinearOpcode>,
}

fn seeded_operations(terminal: TerminalSuffix) -> Vec<LinearOpcode> {
    let mut operations = vec![LinearOpcode::NoOperation; PREFIX];
    operations.extend([
        LinearOpcode::RelocateDataPointer,
        LinearOpcode::CrazyData,
        LinearOpcode::OutputByte,
        LinearOpcode::RotateData,
        LinearOpcode::OutputByte,
        LinearOpcode::CrazyData,
        LinearOpcode::OutputByte,
        LinearOpcode::RotateData,
        LinearOpcode::OutputByte,
        terminal.before_halt().0,
        LinearOpcode::Halt,
    ]);
    operations
}

fn reconstructed_terminal(
    terminal: TerminalSuffix,
    cells: &[[u8; 6]],
) -> Result<ReconstructedTerminal, String> {
    let operations = seeded_operations(terminal);
    let expected = proposed_output_stream::<4>(&operations, cells)
        .ok_or_else(|| String::from("seeded guest cannot execute"))?;
    let source_length = operations.len();
    let relocated = usize::from(
        *cells
            .get(PREFIX)
            .and_then(|cell| cell.get(1))
            .ok_or_else(|| String::from("missing relocation cell"))?,
    );
    let (_, slot) = terminal.before_halt();
    let mut pseudo_cells = cells.to_vec();
    for cell in &mut pseudo_cells {
        let encoded = *cell
            .get(slot)
            .ok_or_else(|| String::from("missing trailer encoding"))?;
        *cell
            .get_mut(4)
            .ok_or_else(|| String::from("missing output encoding slot"))? =
            encoded;
    }
    let memory = cached_output_tail(
        &pseudo_cells,
        &mut BTreeMap::new(),
        source_length,
        relocated.saturating_add(source_length),
    )
    .ok_or_else(|| String::from("missing loader memory"))?
    .to_vec();
    let recovered = proposed_geometry(
        cells,
        &SearchGeometry {
            memory: &memory,
            prefix: PREFIX,
            prefix_outputs: 0,
            source_length,
        },
        expected,
        terminal,
    )
    .ok_or_else(|| format!("trailer search missed real guest {expected:?}"))?;
    Ok(ReconstructedTerminal {
        expected,
        operations: recovered,
    })
}

fn verify_terminal(
    terminal: TerminalSuffix,
    cells: &[[u8; 6]],
) -> Result<[u8; 4], String> {
    let profile = malbolge::current_profile();
    let ReconstructedTerminal {
        expected,
        operations: recovered,
    } = reconstructed_terminal(terminal, cells)?;
    let last = [terminal.before_halt().0, LinearOpcode::Halt];
    if recovered.get(recovered.len().saturating_sub(2)..) != Some(&last) {
        return Err(String::from("terminal geometry differs from proposal"));
    }
    let layout =
        verified_output_stream_layout(profile, &recovered, expected, cells)
            .ok_or_else(|| String::from("independent VM rejected candidate"))?;
    if layout.source().len() != recovered.len() {
        return Err(String::from("source length differs from guest"));
    }
    let writes = recovered
        .iter()
        .filter(|op| {
            matches!(op, LinearOpcode::CrazyData | LinearOpcode::RotateData)
        })
        .count();
    if layout.data_write_positions().iter().flatten().count() != writes {
        return Err(String::from("guest write count differs from proposal"));
    }
    let mut forged = expected;
    forged[0] ^= 1;
    if verified_output_stream_layout(profile, &recovered, forged, cells)
        .is_some()
    {
        return Err(String::from("forged expected output was admitted"));
    }
    Ok(expected)
}

#[test]
fn alternate_noop_terminal_reconstructs_real_guest() -> Result<(), String> {
    let profile = malbolge::current_profile();
    let cells = pair_source_cells(profile)
        .ok_or_else(|| String::from("missing positional encodings"))?;
    let expected = verify_terminal(TerminalSuffix::Noop, &cells)?;
    if expected != [92, 63, 17, 66] {
        return Err(format!("unexpected no-op guest output {expected:?}"));
    }
    let searched =
        verified_state_space_output_layout(profile, expected, &cells)
            .ok_or_else(|| {
                format!("full search missed no-op guest {expected:?}")
            })?;
    if searched.data_write_positions().iter().flatten().count() == 0 {
        return Err(String::from("full search omitted guest arithmetic"));
    }
    Ok(())
}

#[test]
fn post_output_arithmetic_terminals_have_independent_guest_witnesses()
-> Result<(), String> {
    let cells = pair_source_cells(malbolge::current_profile())
        .ok_or_else(|| String::from("missing positional encodings"))?;
    for (terminal, expected) in [
        (TerminalSuffix::Crazy, [89, 62, 9, 65]),
        (TerminalSuffix::Rotate, [84, 181, 249, 181]),
    ] {
        let observed = verify_terminal(terminal, &cells)?;
        if observed != expected {
            return Err(format!("unexpected guest output {observed:?}"));
        }
    }
    Ok(())
}

#[test]
fn early_completion_can_pad_before_terminal() -> Result<(), String> {
    let steps = [
        SearchStep {
            operation: LinearOpcode::NoOperation,
            predecessor: 0,
        },
        SearchStep {
            operation: LinearOpcode::OutputByte,
            predecessor: 0,
        },
    ];
    let geometry = SearchGeometry {
        memory: &[],
        prefix: PREFIX,
        prefix_outputs: 0,
        source_length: PREFIX + 6,
    };
    let operations =
        reconstruct_path(&steps, 1, &geometry, TerminalSuffix::Noop)
            .ok_or_else(|| {
                String::from("completed output cannot pad to terminal")
            })?;
    if operations.get(PREFIX + 1..PREFIX + 4)
        != Some(&[
            LinearOpcode::OutputByte,
            LinearOpcode::NoOperation,
            LinearOpcode::NoOperation,
        ])
        || operations.last() != Some(&LinearOpcode::Halt)
    {
        return Err(String::from("early completion changed the output path"));
    }
    Ok(())
}

#[test]
#[ignore = "full current-profile VM replay is expensive; run explicitly"]
fn padded_terminal_guest_replays_after_early_completion() -> Result<(), String>
{
    let profile = malbolge::current_profile();
    let cells = pair_source_cells(profile)
        .ok_or_else(|| String::from("missing positional encodings"))?;
    let mut original = vec![LinearOpcode::NoOperation; PREFIX];
    original.extend([
        LinearOpcode::RelocateDataPointer,
        LinearOpcode::CrazyData,
        LinearOpcode::OutputByte,
        LinearOpcode::NoOperation,
        LinearOpcode::NoOperation,
        LinearOpcode::NoOperation,
        LinearOpcode::NoOperation,
        LinearOpcode::Halt,
    ]);
    let expected = proposed_output_stream::<1>(&original, &cells)
        .ok_or_else(|| String::from("padded source has no guest trace"))?;
    let _original =
        verified_output_stream_layout(profile, &original, expected, &cells)
            .ok_or_else(|| String::from("padded guest failed VM replay"))?;
    let mut preview_cells = cells.clone();
    for cell in &mut preview_cells {
        cell[4] = cell[0];
    }
    let relocation = usize::from(cells[PREFIX][1]);
    let mut tails = BTreeMap::new();
    let memory = cached_output_tail(
        &preview_cells,
        &mut tails,
        original.len(),
        relocation.saturating_add(original.len()),
    )
    .ok_or_else(|| String::from("padded guest has no loader memory"))?;
    let reconstructed = proposed_geometry(
        &cells,
        &SearchGeometry {
            memory,
            prefix: PREFIX,
            prefix_outputs: 0,
            source_length: original.len(),
        },
        expected,
        TerminalSuffix::Noop,
    )
    .ok_or_else(|| String::from("search missed padded guest"))?;
    let last_output = reconstructed
        .iter()
        .rposition(|operation| *operation == LinearOpcode::OutputByte)
        .ok_or_else(|| String::from("reconstructed guest emits no bytes"))?;
    if !reconstructed[last_output + 1..reconstructed.len() - 2]
        .iter()
        .all(|operation| *operation == LinearOpcode::NoOperation)
        || last_output + 1 >= reconstructed.len() - 2
    {
        return Err(String::from("search did not complete before terminal"));
    }
    let _verified = verified_output_stream_layout(
        profile,
        &reconstructed,
        expected,
        &cells,
    )
    .ok_or_else(|| String::from("reconstructed guest failed VM replay"))?;
    Ok(())
}

#[test]
fn zero_prefix_before_relocation_reconstructs_guest_output()
-> Result<(), String> {
    let profile = malbolge::current_profile();
    let cells = pair_source_cells(profile)
        .ok_or_else(|| String::from("missing positional encodings"))?;
    let mut seeded = vec![LinearOpcode::OutputByte];
    seeded.resize(PREFIX, LinearOpcode::NoOperation);
    seeded.extend([
        LinearOpcode::RelocateDataPointer,
        LinearOpcode::CrazyData,
        LinearOpcode::OutputByte,
        LinearOpcode::RotateData,
        LinearOpcode::OutputByte,
        LinearOpcode::CrazyData,
        LinearOpcode::OutputByte,
        LinearOpcode::NoOperation,
        LinearOpcode::Halt,
    ]);
    let guest = encode_linear_layout(profile, &seeded)
        .map_err(|error| format!("seeded layout failed: {error:?}"))?;
    let mut vm =
        ProfileMachine::from_source(profile, guest.source(), Vec::new())
            .map_err(|error| format!("seeded VM failed: {error:?}"))?;
    if !matches!(vm.run(seeded.len()),
        Ok(RunOutcome::Terminated { steps, .. }) if steps == seeded.len())
    {
        return Err(String::from("seeded guest did not halt"));
    }
    let expected: [u8; 4] = vm
        .output()
        .try_into()
        .map_err(|_error| String::from("seeded VM output length differs"))?;
    if expected[0] != 0 || expected[1..].iter().all(|&byte| byte == 0) {
        return Err(format!(
            "seeded guest lacks distinct output: {expected:?}"
        ));
    }
    if proposed_output_stream::<4>(&seeded, &cells) != Some(expected) {
        return Err(String::from("proposal omitted initial guest zero output"));
    }
    let mut forged = expected;
    forged[0] = 1;
    if verified_output_stream_layout(profile, &seeded, forged, &cells).is_some()
    {
        return Err(String::from("forged initial byte passed guest proof"));
    }
    let recovered =
        verified_state_space_output_layout(profile, expected, &cells)
            .ok_or_else(|| {
                format!("search missed zero-prefixed guest {expected:?}")
            })?;
    let first_output = cells
        .first()
        .and_then(|source_cell| source_cell.get(4))
        .ok_or_else(|| String::from("missing output source encoding"))?;
    if recovered.source().first() != Some(first_output)
        || recovered.source().len() > 94
    {
        return Err(String::from("search missed pre-relocation output"));
    }
    Ok(())
}

#[test]
fn extended_decoder_phase_reconstructs_real_guest() -> Result<(), String> {
    let profile = malbolge::current_profile();
    let cells = pair_source_cells(profile)
        .ok_or_else(|| String::from("missing positional encodings"))?;
    // This complete relocated program crosses the first 94-cell code phase.
    // Its output is obtained from guest operations, not a compiler fixture.
    let mut seeded = vec![LinearOpcode::NoOperation; PREFIX];
    seeded.push(LinearOpcode::RelocateDataPointer);
    for _ in 0..4 {
        seeded.extend([LinearOpcode::CrazyData, LinearOpcode::OutputByte]);
    }
    seeded.resize(99, LinearOpcode::NoOperation);
    seeded.push(LinearOpcode::Halt);
    let expected = proposed_output_stream::<4>(&seeded, &cells)
        .ok_or_else(|| String::from("extended seed has no output"))?;
    if expected != [62, 63, 44, 18] {
        return Err(format!("unexpected extended guest bytes {expected:?}"));
    }
    let relocation = usize::from(cells[PREFIX][1]);
    if relocation < seeded.len() {
        return Err(String::from("extended source aliases relocated data"));
    }
    let mut preview_cells = cells.clone();
    for cell in &mut preview_cells {
        cell[4] = cell[0];
    }
    let memory = cached_output_tail(
        &preview_cells,
        &mut BTreeMap::new(),
        seeded.len(),
        relocation.saturating_add(seeded.len()),
    )
    .ok_or_else(|| String::from("missing extended loader memory"))?
    .to_vec();
    let reconstructed = proposed_geometry(
        &cells,
        &SearchGeometry {
            memory: &memory,
            prefix: PREFIX,
            prefix_outputs: 0,
            source_length: seeded.len(),
        },
        expected,
        TerminalSuffix::Noop,
    )
    .ok_or_else(|| String::from("extended source phase was not recovered"))?;
    let guest = verified_output_stream_layout(
        profile,
        &reconstructed,
        expected,
        &cells,
    )
    .ok_or_else(|| {
        String::from("extended guest failed independent VM replay")
    })?;
    if guest.source().len() != 100 || guest.source().len() <= 94 {
        return Err(String::from("extended source phase was not retained"));
    }
    let mut forged = expected;
    forged[0] ^= 1;
    if verified_output_stream_layout(profile, &reconstructed, forged, &cells)
        .is_some()
    {
        return Err(String::from("forged extended output passed verification"));
    }
    Ok(())
}

#[test]
fn maximum_graphical_relocation_reconstructs_guest() -> Result<(), String> {
    let profile = malbolge::current_profile();
    let cells = pair_source_cells(profile)
        .ok_or_else(|| String::from("missing positional encodings"))?;
    // At position eight, j is encoded as ASCII 126. This is the longest
    // possible disjoint source for a relocation that reads its own cell.
    let relocated = usize::from(cells[PREFIX][1]);
    if relocated != MAX_SOURCE_LENGTH || MAX_SOURCE_LENGTH != 126 {
        return Err(String::from("graphical relocation bound changed"));
    }
    let mut seeded = vec![LinearOpcode::NoOperation; PREFIX];
    seeded.push(LinearOpcode::RelocateDataPointer);
    for _ in 0..4 {
        seeded.extend([LinearOpcode::CrazyData, LinearOpcode::OutputByte]);
    }
    seeded.resize(MAX_SOURCE_LENGTH - 1, LinearOpcode::NoOperation);
    seeded.push(LinearOpcode::Halt);
    let canonical = encode_linear_layout(profile, &seeded)
        .map_err(|error| format!("maximal source refused: {error:?}"))?;
    let mut vm =
        ProfileMachine::from_source(profile, canonical.source(), Vec::new())
            .map_err(|error| {
                format!("maximal guest loader refused: {error:?}")
            })?;
    if !matches!(vm.run(seeded.len()),
        Ok(RunOutcome::Terminated { steps, .. }) if steps == seeded.len())
    {
        return Err(String::from("maximal guest did not halt"));
    }
    let expected: [u8; 4] = vm.output().try_into().map_err(|_error| {
        String::from("maximal guest output length changed")
    })?;
    if proposed_output_stream::<4>(&seeded, &cells) != Some(expected) {
        return Err(String::from("independent guest and preview disagree"));
    }
    let mut preview_cells = cells.clone();
    for cell in &mut preview_cells {
        cell[4] = cell[0];
    }
    let memory = cached_output_tail(
        &preview_cells,
        &mut BTreeMap::new(),
        seeded.len(),
        relocated.saturating_add(seeded.len()),
    )
    .ok_or_else(|| String::from("missing maximal loader memory"))?
    .to_vec();
    let recovered = proposed_geometry(
        &cells,
        &SearchGeometry {
            memory: &memory,
            prefix: PREFIX,
            prefix_outputs: 0,
            source_length: seeded.len(),
        },
        expected,
        TerminalSuffix::Noop,
    )
    .ok_or_else(|| String::from("maximal geometry not reconstructed"))?;
    let verified =
        verified_output_stream_layout(profile, &recovered, expected, &cells)
            .ok_or_else(|| {
                String::from("independent maximal source proof failed")
            })?;
    if verified.source().len() != MAX_SOURCE_LENGTH
        || verified.data_write_positions().iter().flatten().count() < 4
    {
        return Err(String::from("maximal guest lost real writes"));
    }
    let mut forged = expected;
    forged[3] ^= 1;
    if verified_output_stream_layout(profile, &recovered, forged, &cells)
        .is_some()
    {
        return Err(String::from("forged maximal output passed verification"));
    }
    Ok(())
}

#[test]
fn long_zero_output_prefix_reconstructs_exact_guest_geometry()
-> Result<(), String> {
    let profile = malbolge::current_profile();
    let cells = pair_source_cells(profile)
        .ok_or_else(|| String::from("missing positional encodings"))?;
    // Seven source-side outputs need no data writes. The fixed j/p/< /v
    // suffix is four cells: counting all eight outputs as *body*
    // instructions incorrectly excludes this fully valid relocation.
    let mut operations = vec![LinearOpcode::OutputByte; 7];
    operations.extend([
        LinearOpcode::RelocateDataPointer,
        LinearOpcode::CrazyData,
        LinearOpcode::OutputByte,
        LinearOpcode::Halt,
    ]);
    let source = encode_linear_layout(profile, &operations)
        .map_err(|error| format!("zero-prefix seed failed: {error:?}"))?;
    let mut vm =
        ProfileMachine::from_source(profile, source.source(), vec![7, 255, 0])
            .map_err(|error| {
                format!("zero-prefix VM load failed: {error:?}")
            })?;
    if !matches!(vm.run(operations.len()),
        Ok(RunOutcome::Terminated { steps, .. }) if steps == operations.len())
    {
        return Err(String::from("zero-prefix VM did not halt"));
    }
    let expected: [u8; 8] = vm
        .output()
        .try_into()
        .map_err(|_error| String::from("seed did not output eight bytes"))?;
    if expected[..7] != [0; 7] || expected[7] == 0 || vm.input_consumed() != 0 {
        return Err(format!("unexpected zero-prefix guest trace {expected:?}"));
    }
    if proposed_output_stream::<8>(&operations, &cells) != Some(expected) {
        return Err(String::from("proposal disagrees with independent VM"));
    }
    if required_writes(0, &expected) != 1 || operations.len() != 11 {
        return Err(String::from("zero-prefix guest geometry changed"));
    }
    let original = verified_output_stream_layout(
        profile,
        &operations,
        expected,
        &cells,
    )
    .ok_or_else(|| String::from("seed failed independent guest proof"))?;
    if original.source() != source.source() {
        return Err(String::from("independent source bytes differ"));
    }
    // Seven output positions before relocation fit in eleven source
    // cells; the old N+3 prefix cap and N+4 minimum omit this guest.
    let recovered = verified_terminal_layout(
        profile,
        expected,
        &cells,
        TerminalSuffix::Output,
        operations.len(),
        7,
    )
    .ok_or_else(|| String::from("search discarded valid zero prefix"))?;
    if recovered.source().len() != operations.len() {
        return Err(String::from("search added unwanted source cells"));
    }
    let mut replay =
        ProfileMachine::from_source(profile, recovered.source(), Vec::new())
            .map_err(|error| format!("recovered VM load failed: {error:?}"))?;
    if !matches!(
        replay.run(recovered.executed_code_positions().len()),
        Ok(RunOutcome::Terminated { .. })
    ) || replay.output() != expected
    {
        return Err(String::from("recovered guest output disagrees"));
    }
    let mut forged = expected;
    forged[7] ^= 1;
    if verified_output_stream_layout(profile, &operations, forged, &cells)
        .is_some()
    {
        return Err(String::from("forged terminal byte passed VM proof"));
    }
    Ok(())
}

#[test]
fn five_source_bytes_with_initial_zero_are_recovered() -> Result<(), String> {
    let profile = malbolge::current_profile();
    let cells = pair_source_cells(profile)
        .ok_or_else(|| String::from("missing positional encodings"))?;
    let mut operations = vec![LinearOpcode::OutputByte];
    operations.resize(11, LinearOpcode::NoOperation);
    operations.push(LinearOpcode::RelocateDataPointer);
    for _ in 0..4 {
        operations.extend([LinearOpcode::CrazyData, LinearOpcode::OutputByte]);
    }
    operations.push(LinearOpcode::Halt);
    let independent = encode_linear_layout(profile, &operations)
        .map_err(|error| format!("seeded layout failed: {error:?}"))?;
    let mut vm =
        ProfileMachine::from_source(profile, independent.source(), Vec::new())
            .map_err(|error| format!("seeded VM failed: {error:?}"))?;
    if !matches!(vm.run(operations.len()),
        Ok(RunOutcome::Terminated { steps, .. }) if steps == operations.len())
    {
        return Err(String::from("seeded guest did not terminate"));
    }
    let expected: [u8; 5] = vm
        .output()
        .try_into()
        .map_err(|_error| String::from("not five guest bytes"))?;
    assert_eq!(expected[0], 0);
    assert_eq!(expected, *b"\0T=4>");
    let recovered =
        verified_state_space_output_layout(profile, expected, &cells)
            .ok_or_else(|| {
                format!("five-byte search missed guest {expected:?}")
            })?;
    if recovered.data_write_positions().iter().flatten().count() < 4 {
        return Err(String::from("search dropped guest arithmetic effects"));
    }
    let mut guest =
        ProfileMachine::from_source(profile, recovered.source(), vec![
            255, 0, 128,
        ])
        .map_err(|error| format!("recovered VM failed: {error:?}"))?;
    if !matches!(
        guest.run(recovered.executed_code_positions().len()),
        Ok(RunOutcome::Terminated { .. })
    ) || guest.output() != expected
    {
        return Err(String::from("recovered five-byte guest disagreed"));
    }
    Ok(())
}

#[test]
fn straight_write_search_reconstructs_nonfixture_twelve_byte_guest()
-> Result<(), String> {
    let profile = malbolge::current_profile();
    let cells = pair_source_cells(profile)
        .ok_or_else(|| String::from("missing positional encodings"))?;
    let mut operations = vec![LinearOpcode::NoOperation];
    operations.push(LinearOpcode::RelocateDataPointer);
    for index in 0..12 {
        operations.extend([
            if index == 5 {
                LinearOpcode::RotateData
            } else {
                LinearOpcode::CrazyData
            },
            LinearOpcode::OutputByte,
        ]);
    }
    operations.push(LinearOpcode::Halt);
    let seeded = encode_linear_layout(profile, &operations)
        .map_err(|error| format!("seeded twelve layout: {error:?}"))?;
    let mut guest =
        ProfileMachine::from_source(profile, seeded.source(), Vec::new())
            .map_err(|error| format!("seeded twelve load: {error:?}"))?;
    assert!(matches!(
        guest.run(operations.len()),
        Ok(RunOutcome::Terminated { .. })
    ));
    let expected: [u8; 12] = guest
        .output()
        .try_into()
        .map_err(|_error| String::from("seeded output length differs"))?;
    assert_ne!(expected, *b"Q748\xfb\xce\x9f\x98\xb8\xb4\x83\xcd");
    let searched =
        verified_straight_write_output_layout(profile, expected, &cells)
            .ok_or_else(|| format!("search missed guest {expected:?}"))?;
    for input in [Vec::new(), vec![0, 255, 128]] {
        let mut vm =
            ProfileMachine::from_source(profile, searched.source(), input)
                .map_err(|error| format!("searched twelve load: {error:?}"))?;
        assert!(matches!(
            vm.run(searched.executed_code_positions().len()),
            Ok(RunOutcome::Terminated { .. })
        ));
        assert_eq!(vm.input_consumed(), 0);
        assert_eq!(vm.output(), expected);
    }
    Ok(())
}

#[test]
fn twelve_output_interleaved_repeated_guest_is_reconstructed()
-> Result<(), String> {
    let profile = malbolge::current_profile();
    let cells = pair_source_cells(profile)
        .ok_or_else(|| String::from("missing positional encodings"))?;
    let prefix = 8;
    let mut operations = vec![LinearOpcode::NoOperation; prefix];
    operations.push(LinearOpcode::RelocateDataPointer);
    for index in 0..12 {
        if index != 3 {
            operations.push(if index == 2 || index == 5 || index == 9 {
                LinearOpcode::RotateData
            } else {
                LinearOpcode::CrazyData
            });
        }
        operations.push(LinearOpcode::OutputByte);
    }
    operations.extend([LinearOpcode::NoOperation, LinearOpcode::Halt]);
    let expected = proposed_output_stream::<12>(&operations, &cells)
        .ok_or_else(|| String::from("seed guest cannot execute"))?;
    let source =
        verified_output_stream_layout(profile, &operations, expected, &cells)
            .ok_or_else(|| String::from("independent guest rejected seed"))?;
    if source.source().len() != 34 {
        return Err(String::from("source-dependent seed length changed"));
    }
    let relocation = usize::from(cells[prefix][1]);
    let mut altered_cells = cells.clone();
    for cell in &mut altered_cells {
        cell[4] = cell[0];
    }
    let mut tails = BTreeMap::new();
    let memory = cached_output_tail(
        &altered_cells,
        &mut tails,
        operations.len(),
        relocation + operations.len(),
    )
    .ok_or_else(|| String::from("missing guest seed"))?;
    let proposal = proposed_geometry(
        &cells,
        &SearchGeometry {
            memory,
            prefix,
            prefix_outputs: 0,
            source_length: operations.len(),
        },
        expected,
        TerminalSuffix::Noop,
    )
    .ok_or_else(|| String::from("guest search missed proven repeated trace"))?;
    let verified =
        verified_output_stream_layout(profile, &proposal, expected, &cells)
            .ok_or_else(|| {
                String::from("reconstructed trace fails VM proof")
            })?;
    if verified.source().is_empty() {
        return Err(String::from("verified guest is empty"));
    }
    let searched = verified_short_output_layout(profile, expected, &cells)
        .ok_or_else(|| String::from("bounded search missed guest"))?;
    if searched.source().is_empty() {
        return Err(String::from("bounded search returned no guest"));
    }
    Ok(())
}

#[test]
fn guest_output_write_lower_bound_preserves_repeated_effects() {
    // The accumulator starts at zero; an initial zero needs no write.
    assert_eq!(required_writes(0, &[0, 0, 2, 2, 3]), 2);
    assert_eq!(required_writes(2, &[2, 5, 5, 2]), 2);
    // The compound C acceptance stream changes on every output.
    assert_eq!(required_writes(0, &[2, 89, 95, 8, 87, 79]), 6);
    // One adjacent repeat in the 34-step, 12-output guest.
    let interleaved = [62, 9, 13, 13, 40, 46, 19, 61, 10, 46, 10, 61];
    assert_eq!(required_writes(0, &interleaved), 11);
    // The known 34-cell witness has an eight-cell prefix, j and two
    // terminal cells: exactly 23 body slots for 12 outputs and 11 writes.
    assert!(can_fit_effects(34 - 8 - 3, 0, &interleaved));
    assert!(!can_fit_effects(34 - 9 - 3, 0, &interleaved));
    assert!(!can_fit_effects(4, 0, &[0, 0, 2, 2]));
    assert!(can_fit_effects(5, 0, &[0, 0, 2, 2]));
}

#[test]
fn guest_output_successor_bound_keeps_just_sufficient_capacity() {
    let states = BTreeMap::from([((0, 0u32), 0usize)]);
    let mut steps = vec![SearchStep {
        operation: LinearOpcode::NoOperation,
        predecessor: 0,
    }];
    // Output zero now; seven later output changes need fourteen body
    // instructions (seven p/* writes and seven outputs).
    let viable = append_successors(
        &states,
        &mut steps,
        SearchWord {
            value: 0,
            next_value: 0,
            next_next_value: 0,
            next_next_next_value: 0,
            fourth_future_value: None,
            remaining: 14,
            target_emitted: 8,
        },
        [0, 1, 2, 3, 4, 5, 6, 7],
    );
    assert!(viable.contains_key(&(1, 0)));
    // Thirteen body positions cannot realize seven further changes.
    let impossible = append_successors(
        &states,
        &mut steps,
        SearchWord {
            value: 0,
            next_value: 0,
            next_next_value: 0,
            next_next_next_value: 0,
            fourth_future_value: None,
            remaining: 13,
            target_emitted: 8,
        },
        [0, 1, 2, 3, 4, 5, 6, 7],
    );
    assert!(!impossible.contains_key(&(1, 0)));
}

#[test]
fn guest_output_search_retains_distinct_high_word_continuations() {
    // Equal output bytes do not imply equivalent guest state: the next
    // crazy operation observes all fifteen trits, not just the low byte.
    let states = BTreeMap::from([((0, 3u32), 0usize), ((0, 259u32), 0usize)]);
    let expected = [3, 53, 53, 53, 53, 53, 53, 53];
    let mut steps = vec![SearchStep {
        operation: LinearOpcode::NoOperation,
        predecessor: 0,
    }];
    let after_first = append_successors(
        &states,
        &mut steps,
        SearchWord {
            value: 0,
            next_value: 0,
            next_next_value: 0,
            next_next_next_value: 0,
            fourth_future_value: None,
            remaining: 22,
            target_emitted: 8,
        },
        expected,
    );
    assert!(after_first.contains_key(&(1, 3)));
    assert!(after_first.contains_key(&(1, 259)));

    // The second state reaches 53; the first reaches 50. Dropping the
    // high-word alternative loses an otherwise admissible output path.
    let after_write = append_successors(
        &after_first,
        &mut steps,
        SearchWord {
            value: 0,
            next_value: 0,
            next_next_value: 0,
            next_next_next_value: 0,
            fourth_future_value: None,
            remaining: 21,
            target_emitted: 8,
        },
        expected,
    );
    let second_word = malbolge::profile_crazy(0, 259, 15);
    assert_eq!(second_word & 255, 53);
    assert_eq!(malbolge::profile_crazy(0, 3, 15) & 255, 50);
    assert!(after_write.contains_key(&(1, second_word)));
    let after_second = append_successors(
        &after_write,
        &mut steps,
        SearchWord {
            value: 0,
            next_value: 0,
            next_next_value: 0,
            next_next_next_value: 0,
            fourth_future_value: None,
            remaining: 20,
            target_emitted: 8,
        },
        expected,
    );
    assert!(after_second.contains_key(&(2, second_word)));
}

#[test]
fn guest_output_search_preserves_middle_word_reaching_next_byte() {
    // Three distinct full words all emit 3. The old min/max beam kept
    // 3 and 515 but discarded 259, the only word whose next p emits 53.
    let states = BTreeMap::from([
        ((0, 3u32), 0usize),
        ((0, 259u32), 0usize),
        ((0, 515u32), 0usize),
    ]);
    let mut steps = vec![SearchStep {
        operation: LinearOpcode::NoOperation,
        predecessor: 0,
    }];
    let expected = [3, 53, 53, 53, 53, 53, 53, 53];
    assert_eq!(malbolge::profile_crazy(0, 3, 15) & 255, 50);
    assert_eq!(malbolge::profile_crazy(0, 259, 15) & 255, 53);
    assert_eq!(malbolge::profile_crazy(0, 515, 15) & 255, 38);
    let after_first = append_successors(
        &states,
        &mut steps,
        SearchWord {
            value: 0,
            next_value: 0,
            next_next_value: 0,
            next_next_next_value: 0,
            fourth_future_value: None,
            remaining: 22,
            target_emitted: 8,
        },
        expected,
    );
    assert!(after_first.contains_key(&(1, 259)));
    // If both next loader words differ, neither immediate nor delayed
    // p reaches 53; crazy(2, 259) emits 55 instead.
    assert_eq!(malbolge::profile_crazy(2, 259, 15) & 255, 55);
    let without_match = append_successors(
        &states,
        &mut steps,
        SearchWord {
            value: 0,
            next_value: 2,
            next_next_value: 2,
            next_next_next_value: 2,
            fourth_future_value: None,
            remaining: 22,
            target_emitted: 8,
        },
        expected,
    );
    assert!(without_match.contains_key(&(1, 259)));
    assert_eq!(reachable_next_byte(259, &[2, 2, 2], 22, 53), None);
    let after_write = append_successors(
        &after_first,
        &mut steps,
        SearchWord {
            value: 0,
            next_value: 0,
            next_next_value: 0,
            next_next_next_value: 0,
            fourth_future_value: None,
            remaining: 21,
            target_emitted: 8,
        },
        expected,
    );
    assert!(
        after_write.contains_key(&(1, malbolge::profile_crazy(0, 259, 15),))
    );
}

#[test]
fn guest_output_beam_records_only_retained_predecessors() {
    let states = (0u32..16)
        .map(|high| ((0usize, high * 256), 0usize))
        .collect::<BTreeMap<_, _>>();
    let mut steps = vec![SearchStep {
        operation: LinearOpcode::NoOperation,
        predecessor: 0,
    }];
    let prior_steps = steps.len();
    let successors = append_successors(
        &states,
        &mut steps,
        SearchWord {
            value: 0,
            next_value: 0,
            next_next_value: 0,
            next_next_next_value: 0,
            fourth_future_value: None,
            remaining: 30,
            target_emitted: 8,
        },
        [0; 8],
    );
    assert!(!successors.is_empty());
    // Discarded high-word proposals must not consume the reconstruction
    // history or prematurely exhaust its bounded memory budget.
    assert_eq!(steps.len() - prior_steps, successors.len());
    assert!(successors.values().all(|&index| index < steps.len()));
}

#[test]
fn guest_output_beam_preserves_delayed_crazy_match_after_noop() {
    // The next guest word is 2, so no state reaches byte 53 at that
    // position. A no-op advances D to the following word zero: only
    // the middle word 259 then produces 53, not the extremes 3/515.
    let states = BTreeMap::from([
        ((0, 3u32), 0usize),
        ((0, 259u32), 0usize),
        ((0, 515u32), 0usize),
    ]);
    let expected = [3, 53, 53, 53, 53, 53, 53, 53];
    let mut steps = vec![SearchStep {
        operation: LinearOpcode::NoOperation,
        predecessor: 0,
    }];
    let first = append_successors(
        &states,
        &mut steps,
        SearchWord {
            value: 0,
            next_value: 2,
            next_next_value: 0,
            next_next_next_value: 0,
            fourth_future_value: None,
            remaining: 22,
            target_emitted: 8,
        },
        expected,
    );
    assert_eq!(malbolge::profile_crazy(2, 259, 15) & 255, 55);
    assert_eq!(malbolge::profile_crazy(0, 259, 15) & 255, 53);
    assert_eq!(malbolge::profile_crazy(0, 3, 15) & 255, 50);
    assert_eq!(malbolge::profile_crazy(0, 515, 15) & 255, 38);
    assert!(first.contains_key(&(1, 259)), "lost delayed continuation");
    let after_noop = append_successors(
        &first,
        &mut steps,
        SearchWord {
            value: 2,
            next_value: 0,
            next_next_value: 0,
            next_next_next_value: 0,
            fourth_future_value: None,
            remaining: 21,
            target_emitted: 8,
        },
        expected,
    );
    let after_crazy = append_successors(
        &after_noop,
        &mut steps,
        SearchWord {
            value: 0,
            next_value: 0,
            next_next_value: 0,
            next_next_next_value: 0,
            fourth_future_value: None,
            remaining: 20,
            target_emitted: 8,
        },
        expected,
    );
    assert!(
        after_crazy.contains_key(&(1, malbolge::profile_crazy(0, 259, 15)))
    );

    // A changed future data word must not preserve a false match.
    assert_ne!(malbolge::profile_crazy(2, 259, 15) & 255, 53);
    let negative = append_successors(
        &states,
        &mut steps,
        SearchWord {
            value: 0,
            next_value: 2,
            next_next_value: 2,
            next_next_next_value: 2,
            fourth_future_value: None,
            remaining: 22,
            target_emitted: 8,
        },
        expected,
    );
    assert!(negative.contains_key(&(1, 259)));
    assert_eq!(reachable_next_byte(259, &[2, 2, 2], 22, 53), None);
}

#[test]
fn guest_output_beam_preserves_two_consecutive_crazy_writes() {
    // Words 3, 259 and 515 all emit byte 3. The middle full word is
    // needed to reach 255 through p(2, A), p(0, A), then output;
    // neither extreme nor one p after a no-op reaches that byte.
    let states = BTreeMap::from([
        ((0, 3u32), 0usize),
        ((0, 259u32), 0usize),
        ((0, 515u32), 0usize),
    ]);
    let expected = [3, 255, 255, 255, 255, 255, 255, 255];
    let mut steps = vec![SearchStep {
        operation: LinearOpcode::NoOperation,
        predecessor: 0,
    }];
    let first = append_successors(
        &states,
        &mut steps,
        SearchWord {
            value: 0,
            next_value: 2,
            next_next_value: 0,
            next_next_next_value: 0,
            fourth_future_value: None,
            remaining: 22,
            target_emitted: 8,
        },
        expected,
    );
    let first_write = malbolge::profile_crazy(2, 259, 15);
    let second_write = malbolge::profile_crazy(0, first_write, 15);
    assert_eq!(first_write & 255, 55);
    assert_eq!(second_write & 255, 255);
    for other in [3, 515] {
        assert_ne!(
            malbolge::profile_crazy(
                0,
                malbolge::profile_crazy(2, other, 15),
                15,
            ) & 255,
            255,
        );
    }
    assert!(first.contains_key(&(1, 259)), "lost two-write path");
    let after_first_write = append_successors(
        &first,
        &mut steps,
        SearchWord {
            value: 2,
            next_value: 0,
            next_next_value: 0,
            next_next_next_value: 0,
            fourth_future_value: None,
            remaining: 21,
            target_emitted: 8,
        },
        expected,
    );
    let after_second_write = append_successors(
        &after_first_write,
        &mut steps,
        SearchWord {
            value: 0,
            next_value: 0,
            next_next_value: 0,
            next_next_next_value: 0,
            fourth_future_value: None,
            remaining: 20,
            target_emitted: 8,
        },
        expected,
    );
    assert!(after_second_write.contains_key(&(1, second_write)));

    // Changing the second real loader word changes p/p semantics.
    assert_ne!(malbolge::profile_crazy(2, first_write, 15) & 255, 255,);
    let negative = append_successors(
        &states,
        &mut steps,
        SearchWord {
            value: 0,
            next_value: 2,
            next_next_value: 2,
            next_next_next_value: 1,
            fourth_future_value: None,
            remaining: 22,
            target_emitted: 8,
        },
        expected,
    );
    assert!(negative.contains_key(&(1, 259)));
    assert_eq!(reachable_next_byte(259, &[2, 2, 1], 22, 255), None);
}

#[test]
fn guest_output_beam_preserves_three_step_guest_byte_reachability() {
    // Three states with the same current byte can agree on every short
    // continuation but differ after three consecutive real crazy writes.
    // For future loader words [1, 2, 2], only the middle state reaches 54.
    let states = BTreeMap::from([
        ((0, 3u32), 0usize),
        ((0, 259u32), 0usize),
        ((0, 515u32), 0usize),
    ]);
    let mut steps = vec![SearchStep {
        operation: LinearOpcode::NoOperation,
        predecessor: 0,
    }];
    let expected = [3, 54, 54, 54, 54, 54, 54, 54];
    let first = append_successors(
        &states,
        &mut steps,
        SearchWord {
            value: 0,
            next_value: 1,
            next_next_value: 2,
            next_next_next_value: 2,
            fourth_future_value: None,
            remaining: 22,
            target_emitted: 8,
        },
        expected,
    );
    assert!(first.contains_key(&(1, 259)), "lost three-step path");
    let first_write = malbolge::profile_crazy(1, 259, 15);
    let second_write = malbolge::profile_crazy(2, first_write, 15);
    let third_write = malbolge::profile_crazy(2, second_write, 15);
    assert_eq!(third_write & 255, 54);
    let second = append_successors(
        &first,
        &mut steps,
        SearchWord {
            value: 1,
            next_value: 2,
            next_next_value: 2,
            next_next_next_value: 0,
            fourth_future_value: None,
            remaining: 21,
            target_emitted: 8,
        },
        expected,
    );
    assert!(second.contains_key(&(1, first_write)));
    let third = append_successors(
        &second,
        &mut steps,
        SearchWord {
            value: 2,
            next_value: 2,
            next_next_value: 0,
            next_next_next_value: 0,
            fourth_future_value: None,
            remaining: 20,
            target_emitted: 8,
        },
        expected,
    );
    assert!(third.contains_key(&(1, second_write)));
    let fourth = append_successors(
        &third,
        &mut steps,
        SearchWord {
            value: 2,
            next_value: 0,
            next_next_value: 0,
            next_next_next_value: 0,
            fourth_future_value: None,
            remaining: 19,
            target_emitted: 8,
        },
        expected,
    );
    assert!(fourth.contains_key(&(1, third_write)));

    // The changed third loader word has no matching short continuation.
    let negative = append_successors(
        &states,
        &mut steps,
        SearchWord {
            value: 0,
            next_value: 1,
            next_next_value: 2,
            next_next_next_value: 0,
            fourth_future_value: None,
            remaining: 22,
            target_emitted: 8,
        },
        expected,
    );
    assert!(negative.contains_key(&(1, 259)));
    assert_eq!(reachable_next_byte(259, &[1, 2, 0], 22, 54), None);
    // Three writes still need a fourth instruction for the actual output.
    assert_eq!(reachable_next_byte(259, &[1, 2, 2], 4, 54), Some(3));
    assert_eq!(reachable_next_byte(259, &[1, 2, 2], 3, 54), None);
}

#[test]
fn dense_guest_frontier_still_prunes_to_a_bounded_budget() {
    // A large frontier is not eligible for exact retention. The beam must
    // continue to discard redundant proposals before writing history.
    let states = (0u32..8_192)
        .map(|high| ((0usize, high * 256), 0usize))
        .collect::<BTreeMap<_, _>>();
    let mut steps = vec![SearchStep {
        operation: LinearOpcode::NoOperation,
        predecessor: 0,
    }];
    let survivors = append_successors(
        &states,
        &mut steps,
        SearchWord {
            value: 0,
            next_value: 0,
            next_next_value: 0,
            next_next_next_value: 0,
            fourth_future_value: None,
            remaining: 30,
            target_emitted: 8,
        },
        [0; 8],
    );
    assert!(!survivors.is_empty());
    assert!(survivors.len() < MAX_STATES_PER_POSITION);
    assert_eq!(steps.len(), survivors.len() + 1);
}

#[test]
fn dense_guest_frontier_retains_future_change_after_repeated_output() {
    // Every candidate begins with byte 3; the next output repeats it.
    // Accumulator 259 is necessary for a later p(0, A) to emit 53,
    // even though the immediately pending byte already matches 3.
    let states = (0u32..8_192)
        .map(|high| ((0usize, high * 256 + 3), 0usize))
        .collect::<BTreeMap<_, _>>();
    let expected = [3, 3, 53, 53, 53, 53, 53, 53];
    let mut steps = vec![SearchStep {
        operation: LinearOpcode::NoOperation,
        predecessor: 0,
    }];
    assert_eq!(malbolge::profile_crazy(0, 259, 15) & 255, 53);
    let retained = append_successors(
        &states,
        &mut steps,
        SearchWord {
            value: 0,
            next_value: 0,
            next_next_value: 0,
            next_next_next_value: 0,
            fourth_future_value: None,
            remaining: 30,
            target_emitted: 8,
        },
        expected,
    );
    assert!(retained.len() < MAX_STATES_PER_POSITION);
    assert!(
        retained.contains_key(&(1, 259)),
        "lost repeated-byte continuation"
    );
    let repeated = append_successors(
        &retained,
        &mut steps,
        SearchWord {
            value: 0,
            next_value: 0,
            next_next_value: 0,
            next_next_next_value: 0,
            fourth_future_value: None,
            remaining: 29,
            target_emitted: 8,
        },
        expected,
    );
    assert!(repeated.contains_key(&(2, 259)));
    let changed_word = malbolge::profile_crazy(0, 259, 15);
    let written = append_successors(
        &repeated,
        &mut steps,
        SearchWord {
            value: 0,
            next_value: 0,
            next_next_value: 0,
            next_next_next_value: 0,
            fourth_future_value: None,
            remaining: 28,
            target_emitted: 8,
        },
        expected,
    );
    assert!(written.contains_key(&(2, changed_word)));
    let output = append_successors(
        &written,
        &mut steps,
        SearchWord {
            value: 0,
            next_value: 0,
            next_next_value: 0,
            next_next_next_value: 0,
            fourth_future_value: None,
            remaining: 27,
            target_emitted: 8,
        },
        expected,
    );
    assert!(output.contains_key(&(3, changed_word)));

    // The hint must depend on the real following loader word, not a
    // coincidental equality of the current and next output bytes.
    assert_eq!(reachable_next_byte(259, &[2, 2, 2], 30, 53), None);
    let changed = append_successors(
        &states,
        &mut steps,
        SearchWord {
            value: 0,
            next_value: 2,
            next_next_value: 2,
            next_next_next_value: 2,
            fourth_future_value: None,
            remaining: 30,
            target_emitted: 8,
        },
        expected,
    );
    assert!(!changed.contains_key(&(1, 259)));
}

#[test]
fn dense_guest_frontier_preserves_fourth_word_continuation() {
    // All states emit 3, but only a non-extreme full word can reach 1
    // through the fourth future loader cell. A dense frontier must not
    // discard it solely because the three-cell heuristic sees no match.
    let states = (0u32..8_192)
        .map(|high| ((0usize, high * 256 + 3), 0usize))
        .collect::<BTreeMap<_, _>>();
    let mut steps = vec![SearchStep {
        operation: LinearOpcode::NoOperation,
        predecessor: 0,
    }];
    let expected = [3, 1, 1, 1, 1, 1, 1, 1];
    let survivors = append_successors(
        &states,
        &mut steps,
        SearchWord {
            value: 0,
            next_value: 0,
            next_next_value: 0,
            next_next_next_value: 0,
            fourth_future_value: Some(2),
            remaining: 22,
            target_emitted: 8,
        },
        expected,
    );
    let after_first_write = malbolge::profile_crazy(0, 259, 15);
    let final_word = malbolge::profile_crazy(2, after_first_write, 15);
    assert_eq!(final_word & 255, 1);
    assert_eq!(reachable_next_byte(259, &[0, 0, 0, 2], 22, 1), Some(4));
    assert_eq!(reachable_next_byte(259, &[0, 0, 0, 1], 22, 1), None);
    assert_eq!(reachable_next_byte(259, &[0, 0, 0, 2], 4, 1), None);
    assert!(survivors.len() < MAX_STATES_PER_POSITION);
    assert!(
        survivors.contains_key(&(1, 259)),
        "dense beam dropped the four-cell future byte path"
    );
    // Follow the actual ordered data operations through the chosen full
    // word; the new beam witness must not be a dead-end hint.
    let mut continuation = BTreeMap::from([(
        (1, 259u32),
        *survivors.get(&(1, 259)).expect("retained predecessor"),
    )]);
    for (index, word) in [0, 0, 0, 2].into_iter().enumerate() {
        continuation = append_successors(
            &continuation,
            &mut steps,
            SearchWord {
                value: word,
                next_value: 0,
                next_next_value: 0,
                next_next_next_value: 0,
                fourth_future_value: None,
                remaining: 21 - index,
                target_emitted: 8,
            },
            expected,
        );
    }
    assert!(continuation.contains_key(&(1, final_word)));
    let output = append_successors(
        &continuation,
        &mut steps,
        SearchWord {
            value: 0,
            next_value: 0,
            next_next_value: 0,
            next_next_next_value: 0,
            fourth_future_value: None,
            remaining: 16,
            target_emitted: 8,
        },
        expected,
    );
    assert!(output.contains_key(&(2, final_word)));

    // A changed fourth operand does not manufacture a false witness.
    let forged = append_successors(
        &states,
        &mut steps,
        SearchWord {
            value: 0,
            next_value: 0,
            next_next_value: 0,
            next_next_next_value: 0,
            fourth_future_value: Some(1),
            remaining: 22,
            target_emitted: 8,
        },
        expected,
    );
    assert!(!forged.contains_key(&(1, 259)));
    // Keep the pending output-cell capacity check: four writes/no-ops
    // without a fifth cell for < cannot produce the requested byte.
    let insufficient = append_successors(
        &states,
        &mut steps,
        SearchWord {
            value: 0,
            next_value: 0,
            next_next_value: 0,
            next_next_next_value: 0,
            fourth_future_value: Some(2),
            remaining: 4,
            target_emitted: 8,
        },
        expected,
    );
    assert!(insufficient.is_empty());
}

#[test]
fn sparse_guest_frontier_preserves_fourth_word_continuation() {
    // Only the middle full accumulator reaches byte 1 after a later
    // loader word. Three-word lookahead cannot see this legitimate path.
    let states = BTreeMap::from([
        ((0, 3u32), 0usize),
        ((0, 259u32), 0usize),
        ((0, 515u32), 0usize),
    ]);
    let expected = [3, 1, 1, 1, 1, 1, 1, 1];
    let mut steps = vec![SearchStep {
        operation: LinearOpcode::NoOperation,
        predecessor: 0,
    }];
    let first = append_successors(
        &states,
        &mut steps,
        SearchWord {
            value: 0,
            next_value: 0,
            next_next_value: 0,
            next_next_next_value: 0,
            fourth_future_value: None,
            remaining: 22,
            target_emitted: 8,
        },
        expected,
    );
    assert!(
        first.contains_key(&(1, 259)),
        "exact sparse frontier discarded fourth-word continuation"
    );
    let mut current = first;
    for (index, word) in [0, 0, 0, 2].into_iter().enumerate() {
        current = append_successors(
            &current,
            &mut steps,
            SearchWord {
                value: word,
                next_value: 0,
                next_next_value: 0,
                next_next_next_value: 0,
                fourth_future_value: None,
                remaining: 21 - index,
                target_emitted: 8,
            },
            expected,
        );
    }
    let reached =
        malbolge::profile_crazy(2, malbolge::profile_crazy(0, 259, 15), 15);
    assert_eq!(reached & 255, 1);
    assert!(current.contains_key(&(1, reached)));
    let output = append_successors(
        &current,
        &mut steps,
        SearchWord {
            value: 0,
            next_value: 0,
            next_next_value: 0,
            next_next_next_value: 0,
            fourth_future_value: None,
            remaining: 16,
            target_emitted: 8,
        },
        expected,
    );
    assert!(output.contains_key(&(2, reached)));
    // Changing the fourth future loader word to 1 cannot synthesize that
    // byte, although the sparse initial state must still survive.
    let mut altered = BTreeMap::from([((1, 259u32), 0usize)]);
    for (index, word) in [0, 0, 0, 1].into_iter().enumerate() {
        altered = append_successors(
            &altered,
            &mut steps,
            SearchWord {
                value: word,
                next_value: 0,
                next_next_value: 0,
                next_next_next_value: 0,
                fourth_future_value: None,
                remaining: 21 - index,
                target_emitted: 8,
            },
            expected,
        );
    }
    assert!(altered.keys().all(|&(emitted, accumulator)| {
        emitted < 2 && accumulator & 255 != 1
    }));
}

#[test]
fn twelve_output_crazy_terminal_requires_its_own_loader_seed()
-> Result<(), String> {
    let profile = malbolge::current_profile();
    let cells = pair_source_cells(profile)
        .ok_or_else(|| String::from("missing positional source cells"))?;
    let mut operations = vec![LinearOpcode::NoOperation; 8];
    operations.push(LinearOpcode::RelocateDataPointer);
    for index in 0..12 {
        if index != 3 {
            operations.push(if index == 2 || index == 5 || index == 9 {
                LinearOpcode::RotateData
            } else {
                LinearOpcode::CrazyData
            });
        }
        operations.push(LinearOpcode::OutputByte);
    }
    operations.extend([LinearOpcode::CrazyData, LinearOpcode::Halt]);
    let expected = proposed_output_stream::<12>(&operations, &cells)
        .ok_or_else(|| String::from("seeded source cannot emit"))?;
    let mut wrong_tail = operations.clone();
    wrong_tail[operations.len() - 2] = LinearOpcode::NoOperation;
    assert_ne!(
        proposed_output_stream::<12>(&wrong_tail, &cells),
        Some(expected),
        "changing the source tail cannot reuse its loader seed",
    );
    let seeded =
        verified_output_stream_layout(profile, &operations, expected, &cells)
            .ok_or_else(|| String::from("seeded source lacks VM proof"))?;
    assert_eq!(seeded.source().len(), 34);
    let recovered = verified_terminal_layout(
        profile,
        expected,
        &cells,
        TerminalSuffix::Crazy,
        34,
        8,
    )
    .ok_or_else(|| String::from("search missed valid crazy terminal"))?;
    assert_eq!(recovered.source().len(), 34);
    // The public bounded search previously locked its source tail to a no-op.
    let public = verified_short_output_layout(profile, expected, &cells)
        .ok_or_else(|| String::from("public search omitted crazy terminal"))?;
    assert_eq!(public.source().len(), 34);
    Ok(())
}

#[test]
fn rotated_tail_recovers_independently_proved_twelve_byte_guest()
-> Result<(), String> {
    let profile = malbolge::current_profile();
    let cells = pair_source_cells(profile)
        .ok_or_else(|| String::from("missing positional encodings"))?;
    let mut operations = vec![LinearOpcode::NoOperation; 4];
    operations.push(LinearOpcode::RelocateDataPointer);
    for index in 0..12 {
        if index != 0 && index % 2 == 0 {
            operations.push(LinearOpcode::NoOperation);
        }
        operations.extend([
            if index % 3 == 0 {
                LinearOpcode::RotateData
            } else {
                LinearOpcode::CrazyData
            },
            LinearOpcode::OutputByte,
        ]);
    }
    operations.extend([LinearOpcode::RotateData, LinearOpcode::Halt]);
    assert_eq!(operations.len(), 36);
    let expected = proposed_output_stream::<12>(&operations, &cells)
        .ok_or_else(|| String::from("source cannot produce twelve bytes"))?;
    assert_eq!(expected, [
        136, 176, 133, 182, 139, 188, 182, 136, 176, 136, 200, 136
    ],);
    let _independent =
        verified_output_stream_layout(profile, &operations, expected, &cells)
            .ok_or_else(|| String::from("original guest failed normative VM"))?;
    let recovered = verified_short_output_layout(profile, expected, &cells)
        .ok_or_else(|| {
            String::from("short search missed valid rotated-tail guest")
        })?;
    if recovered.data_write_positions().iter().flatten().count() == 0 {
        return Err(String::from("reconstructed guest omitted writes"));
    }
    let mut altered = expected;
    altered[0] ^= 1;
    assert!(
        verified_output_stream_layout(profile, &operations, altered, &cells)
            .is_none(),
        "altered byte was accepted against independent guest",
    );
    Ok(())
}

#[test]
fn differing_final_output_can_follow_a_guest_write() -> Result<(), String> {
    let profile = malbolge::current_profile();
    let cells = pair_source_cells(profile)
        .ok_or_else(|| String::from("missing positional encodings"))?;
    let mut operations = vec![LinearOpcode::NoOperation; 8];
    operations.push(LinearOpcode::RelocateDataPointer);
    for _ in 0..11 {
        operations.extend([LinearOpcode::CrazyData, LinearOpcode::OutputByte]);
    }
    operations.extend([
        LinearOpcode::CrazyData,
        LinearOpcode::OutputByte,
        LinearOpcode::Halt,
    ]);
    assert_eq!(operations.len(), 34);
    let expected = proposed_output_stream::<12>(&operations, &cells)
        .ok_or_else(|| String::from("seeded guest cannot output"))?;
    assert_eq!(expected, [89, 63, 44, 72, 80, 27, 89, 63, 44, 72, 80, 27],);
    assert_ne!(expected[10], expected[11]);
    let original =
        verified_output_stream_layout(profile, &operations, expected, &cells)
            .ok_or_else(|| String::from("independent VM rejected seed"))?;
    assert_eq!(original.source().len(), 34);
    let recovered = verified_terminal_layout(
        profile,
        expected,
        &cells,
        TerminalSuffix::Output,
        34,
        8,
    )
    .ok_or_else(|| {
        format!("output terminal missed valid guest {expected:?}")
    })?;
    assert_eq!(recovered.source().len(), 34);
    assert_eq!(recovered.source().get(32), cells[32].get(4));
    assert!(recovered.data_write_positions().iter().flatten().count() >= 12);
    let public = verified_short_output_layout(profile, expected, &cells)
        .ok_or_else(|| {
            format!("bounded search missed output-tail guest {expected:?}")
        })?;
    assert!(public.source().len() <= 36);
    Ok(())
}

#[test]
fn final_relocation_loader_seed_admits_independent_guest() -> Result<(), String>
{
    let profile = malbolge::current_profile();
    let cells = pair_source_cells(profile)
        .ok_or_else(|| String::from("missing positional encodings"))?;
    let mut operations = vec![LinearOpcode::NoOperation; 8];
    operations.push(LinearOpcode::RelocateDataPointer);
    for _ in 0..12 {
        operations.extend([LinearOpcode::CrazyData, LinearOpcode::OutputByte]);
    }
    operations.extend([LinearOpcode::RelocateDataPointer, LinearOpcode::Halt]);
    assert_eq!(operations.len(), 35);
    // Construct source independently of the linear-layout checker, which
    // historically rejected all second data-pointer relocations.
    let source = operations
        .iter()
        .enumerate()
        .map(|(position, &operation)| {
            let slot = super::super::pair_opcode_slot(operation)?;
            cells.get(position).and_then(|cell| cell.get(slot)).copied()
        })
        .collect::<Option<Vec<u8>>>()
        .ok_or_else(|| String::from("missing encoded guest cell"))?;
    let mut vm = ProfileMachine::from_source(profile, &source, Vec::new())
        .map_err(|error| format!("seeded guest load: {error:?}"))?;
    assert!(matches!(
        vm.run(operations.len()),
        Ok(RunOutcome::Terminated { steps, .. }) if steps == operations.len()
    ));
    let expected: [u8; 12] = vm
        .output()
        .try_into()
        .map_err(|_error| String::from("seeded guest output length"))?;
    assert_eq!(expected, [63, 10, 43, 20, 53, 0, 63, 10, 43, 20, 53, 0]);
    let proved =
        verified_output_stream_layout(profile, &operations, expected, &cells)
            .ok_or_else(|| {
            format!("terminal relocate guest failed proof {expected:?}")
        })?;
    assert_eq!(proved.source(), source);
    assert_eq!(proved.data_write_positions().iter().flatten().count(), 12);
    let reconstructed = verified_terminal_layout(
        profile,
        expected,
        &cells,
        TerminalSuffix::Relocate,
        35,
        8,
    )
    .ok_or_else(|| String::from("terminal j seed missed complete guest"))?;
    let tail_position = reconstructed.source().len() - 2;
    assert_eq!(
        reconstructed.source().get(tail_position),
        cells.get(tail_position).and_then(|cell| cell.get(1))
    );
    let public = verified_short_output_layout(profile, expected, &cells)
        .ok_or_else(|| {
            String::from("bounded production missed terminal j guest")
        })?;
    assert!(public.source().len() <= 36);
    let mut forged = expected;
    forged[0] ^= 1;
    assert!(
        verified_output_stream_layout(profile, &operations, forged, &cells)
            .is_none()
    );
    Ok(())
}

#[test]
fn longer_relocated_guest_exposes_wider_source_geometry() -> Result<(), String>
{
    let profile = malbolge::current_profile();
    let cells = pair_source_cells(profile)
        .ok_or_else(|| String::from("missing positional source cells"))?;
    let mut operations = vec![LinearOpcode::NoOperation; 8];
    operations.push(LinearOpcode::RelocateDataPointer);
    for index in 0..12 {
        if [1, 3, 5, 7, 9].contains(&index) {
            operations.push(LinearOpcode::NoOperation);
        }
        operations.extend([
            if index % 4 == 0 {
                LinearOpcode::RotateData
            } else {
                LinearOpcode::CrazyData
            },
            LinearOpcode::OutputByte,
        ]);
    }
    operations.push(LinearOpcode::Halt);
    assert_eq!(operations.len(), 39);
    let expected = proposed_output_stream::<12>(&operations, &cells)
        .ok_or_else(|| String::from("seeded guest has no output"))?;
    assert_eq!(expected, [181, 79, 66, 61, 51, 8, 80, 35, 180, 77, 93, 49]);
    let original =
        verified_output_stream_layout(profile, &operations, expected, &cells)
            .ok_or_else(|| {
            String::from("seeded source lacks independent VM proof")
        })?;
    assert_eq!(original.data_write_positions().iter().flatten().count(), 12);
    let recovered = verified_short_output_layout(profile, expected, &cells)
        .ok_or_else(|| String::from("bounded search missed long guest"))?;
    assert!((37..=39).contains(&recovered.source().len()));
    assert_eq!(
        recovered.data_write_positions().iter().flatten().count(),
        12
    );
    let mut forged = expected;
    forged[0] ^= 1;
    assert!(
        verified_output_stream_layout(profile, &operations, forged, &cells,)
            .is_none()
    );
    Ok(())
}

#[test]
fn longer_relocated_guest_with_crazy_terminal_is_recovered()
-> Result<(), String> {
    let profile = malbolge::current_profile();
    let cells = pair_source_cells(profile)
        .ok_or_else(|| String::from("missing positional source cells"))?;
    let mut operations = vec![LinearOpcode::NoOperation; 8];
    operations.push(LinearOpcode::RelocateDataPointer);
    for index in 0..12 {
        if [1, 3, 5, 7].contains(&index) {
            operations.push(LinearOpcode::NoOperation);
        }
        operations.extend([
            if index % 4 == 0 {
                LinearOpcode::RotateData
            } else {
                LinearOpcode::CrazyData
            },
            LinearOpcode::OutputByte,
        ]);
    }
    operations.extend([LinearOpcode::CrazyData, LinearOpcode::Halt]);
    assert_eq!(operations.len(), 39);
    let original = encode_linear_layout(profile, &operations)
        .map_err(|error| format!("independent guest encoding: {error:?}"))?;
    let mut vm =
        ProfileMachine::from_source(profile, original.source(), Vec::new())
            .map_err(|error| format!("normative load: {error:?}"))?;
    assert!(matches!(
        vm.run(operations.len()),
        Ok(RunOutcome::Terminated { steps, .. }) if steps == operations.len()
    ));
    let expected: [u8; 12] = vm
        .output()
        .try_into()
        .map_err(|_error| String::from("guest did not emit twelve bytes"))?;
    assert_eq!(expected, [
        161, 17, 44, 11, 40, 16, 45, 10, 161, 255, 163, 255
    ]);
    let mut nonempty =
        ProfileMachine::from_source(profile, original.source(), vec![
            0, 255, 1,
        ])
        .map_err(|error| format!("nonempty input: {error:?}"))?;
    assert!(matches!(
        nonempty.run(operations.len()),
        Ok(RunOutcome::Terminated { steps, .. }) if steps == operations.len()
    ));
    assert_eq!(nonempty.output(), expected);
    assert_eq!(
        verified_output_stream_layout(profile, &operations, expected, &cells)
            .as_ref()
            .map(LinearLayout::source),
        Some(original.source()),
    );
    let recovered = verified_short_output_layout(profile, expected, &cells)
        .ok_or_else(|| {
            format!("bounded search missed long crazy seed: {expected:?}")
        })?;
    assert!((37..=39).contains(&recovered.source().len()));
    assert!(
        recovered.data_write_positions().iter().flatten().count() >= 13,
        "twelve changing outputs and a terminal crazy write need data writes",
    );
    assert_eq!(
        recovered.source().get(recovered.source().len() - 2),
        cells
            .get(recovered.source().len() - 2)
            .and_then(|cell| cell.get(2)),
    );
    let mut forged = expected;
    forged[0] ^= 1;
    assert!(
        verified_output_stream_layout(profile, &operations, forged, &cells)
            .is_none()
    );
    Ok(())
}

#[test]
fn longer_relocated_guest_with_rotate_terminal_is_recovered()
-> Result<(), String> {
    let profile = malbolge::current_profile();
    let cells = pair_source_cells(profile)
        .ok_or_else(|| String::from("missing positional source cells"))?;
    let mut operations = vec![LinearOpcode::NoOperation; 8];
    operations.push(LinearOpcode::RelocateDataPointer);
    for index in 0..12 {
        if [1, 3, 5, 7].contains(&index) {
            operations.push(LinearOpcode::NoOperation);
        }
        operations.extend([
            if index % 4 == 0 {
                LinearOpcode::RotateData
            } else {
                LinearOpcode::CrazyData
            },
            LinearOpcode::OutputByte,
        ]);
    }
    operations.extend([LinearOpcode::RotateData, LinearOpcode::Halt]);
    assert_eq!(operations.len(), 39);
    let original = encode_linear_layout(profile, &operations)
        .map_err(|error| format!("rotate-tail encoding: {error:?}"))?;
    let mut vm =
        ProfileMachine::from_source(profile, original.source(), Vec::new())
            .map_err(|error| format!("rotate-tail load: {error:?}"))?;
    assert!(matches!(
        vm.run(operations.len()),
        Ok(RunOutcome::Terminated { steps, .. }) if steps == operations.len()
    ));
    let expected: [u8; 12] = vm
        .output()
        .try_into()
        .map_err(|_error| String::from("guest output count changed"))?;
    assert_eq!(expected, [
        177, 138, 183, 136, 177, 138, 180, 136, 176, 136, 179, 130,
    ]);
    let mut wrong_tail = operations.clone();
    wrong_tail[operations.len() - 2] = LinearOpcode::NoOperation;
    assert_ne!(
        proposed_output_stream::<12>(&wrong_tail, &cells),
        Some(expected),
        "changing the rotated source tail reused the loader seed",
    );
    let mut nonempty =
        ProfileMachine::from_source(profile, original.source(), vec![
            0, 255, 1,
        ])
        .map_err(|error| format!("rotate-tail nonempty load: {error:?}"))?;
    assert!(matches!(
        nonempty.run(operations.len()),
        Ok(RunOutcome::Terminated { steps, .. }) if steps == operations.len()
    ));
    assert_eq!(nonempty.output(), expected);
    assert_eq!(nonempty.input_consumed(), 0);
    assert_eq!(
        verified_output_stream_layout(profile, &operations, expected, &cells)
            .as_ref()
            .map(LinearLayout::source),
        Some(original.source()),
    );
    let recovered = verified_short_output_layout(profile, expected, &cells)
        .ok_or_else(|| {
            format!("bounded search missed long rotate seed: {expected:?}")
        })?;
    assert!((37..=39).contains(&recovered.source().len()));
    assert_eq!(
        recovered.data_write_positions().iter().flatten().count(),
        13,
    );
    assert_eq!(
        recovered.source().get(recovered.source().len() - 2),
        cells
            .get(recovered.source().len() - 2)
            .and_then(|cell| cell.get(3)),
    );
    let mut forged = expected;
    forged[0] ^= 1;
    assert!(
        verified_output_stream_layout(profile, &operations, forged, &cells)
            .is_none()
    );
    Ok(())
}

#[test]
fn long_noop_tail_reconstructs_twelve_byte_guest() -> Result<(), String> {
    let profile = malbolge::current_profile();
    let cells = pair_source_cells(profile)
        .ok_or_else(|| String::from("missing positional source cells"))?;
    let mut operations = vec![LinearOpcode::NoOperation; 8];
    operations.push(LinearOpcode::RelocateDataPointer);
    for index in 0..12 {
        if [1, 3, 5, 7].contains(&index) {
            operations.push(LinearOpcode::NoOperation);
        }
        operations.extend([
            if index % 4 == 0 {
                LinearOpcode::RotateData
            } else {
                LinearOpcode::CrazyData
            },
            LinearOpcode::OutputByte,
        ]);
    }
    operations.extend([LinearOpcode::NoOperation, LinearOpcode::Halt]);
    assert_eq!(operations.len(), 39);
    let original = encode_linear_layout(profile, &operations)
        .map_err(|error| format!("no-op terminal encoding: {error:?}"))?;
    let mut vm =
        ProfileMachine::from_source(profile, original.source(), Vec::new())
            .map_err(|error| format!("no-op terminal load: {error:?}"))?;
    assert!(matches!(
        vm.run(operations.len()),
        Ok(RunOutcome::Terminated { steps, .. }) if steps == operations.len()
    ));
    let expected: [u8; 12] = vm
        .output()
        .try_into()
        .map_err(|_error| String::from("guest output count changed"))?;
    assert_eq!(expected, [
        163, 16, 48, 16, 42, 17, 44, 17, 162, 1, 166, 252,
    ]);
    let mut nonempty =
        ProfileMachine::from_source(profile, original.source(), vec![
            0, 255, 1,
        ])
        .map_err(|error| format!("no-op terminal nonempty load: {error:?}"))?;
    assert!(matches!(
        nonempty.run(operations.len()),
        Ok(RunOutcome::Terminated { steps, .. }) if steps == operations.len()
    ));
    assert_eq!(nonempty.output(), expected);
    assert_eq!(nonempty.input_consumed(), 0);
    assert_eq!(original.data_write_positions().iter().flatten().count(), 12);
    let mut changed_tail = operations.clone();
    changed_tail[operations.len() - 2] = LinearOpcode::RotateData;
    assert_ne!(
        proposed_output_stream::<12>(&changed_tail, &cells),
        Some(expected),
        "changing the source tail reused the no-op loader seed",
    );
    assert_eq!(
        verified_output_stream_layout(profile, &operations, expected, &cells)
            .as_ref()
            .map(LinearLayout::source),
        Some(original.source()),
    );
    let recovered = verified_short_output_layout(profile, expected, &cells)
        .ok_or_else(|| {
            format!("bounded search missed no-op tail: {expected:?}")
        })?;
    assert!((37..=39).contains(&recovered.source().len()));
    assert_eq!(
        recovered.source().get(recovered.source().len() - 2),
        cells
            .get(recovered.source().len() - 2)
            .and_then(|cell| cell.get(0)),
    );
    let mut forged = expected;
    forged[0] ^= 1;
    assert!(
        verified_output_stream_layout(profile, &operations, forged, &cells)
            .is_none()
    );
    Ok(())
}
