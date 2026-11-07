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
