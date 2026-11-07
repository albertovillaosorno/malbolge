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

use super::super::{pair_source_cells, proposed_output_stream};
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
