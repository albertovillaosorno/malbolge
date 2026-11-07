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

#[test]
fn alternate_noop_terminal_reconstructs_real_guest() -> Result<(), String> {
    let profile = malbolge::current_profile();
    let cells = pair_source_cells(profile)
        .ok_or_else(|| String::from("missing positional encodings"))?;
    let prefix = 8;
    let mut operations = vec![LinearOpcode::NoOperation; prefix];
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
        LinearOpcode::NoOperation,
        LinearOpcode::Halt,
    ]);
    let expected = proposed_output_stream::<4>(&operations, &cells)
        .ok_or_else(|| String::from("seeded guest cannot execute"))?;
    let source_length = operations.len();
    let relocated = usize::from(cells[prefix][1]);
    let mut pseudo_cells = cells.clone();
    for cell in &mut pseudo_cells {
        cell[4] = cell[0];
    }
    let memory = cached_output_tail(
        &pseudo_cells,
        &mut BTreeMap::new(),
        source_length,
        relocated + source_length,
    )
    .ok_or_else(|| String::from("missing loader memory"))?
    .to_vec();
    let recovered = proposed_geometry(
        &cells,
        &SearchGeometry {
            memory: &memory,
            prefix,
            source_length,
        },
        expected,
        TerminalPair::NoopHalt,
    )
    .ok_or_else(|| String::from("no-op trailer search missed real guest"))?;
    assert_eq!(&recovered[recovered.len() - 2..], &[
        LinearOpcode::NoOperation,
        LinearOpcode::Halt
    ],);
    let layout =
        verified_output_stream_layout(profile, &recovered, expected, &cells)
            .ok_or_else(|| String::from("independent VM rejected candidate"))?;
    assert_eq!(layout.source().len(), source_length);
    assert_eq!(expected, [92, 63, 17, 66]);
    let mut forged = expected;
    forged[2] ^= 1;
    assert!(
        verified_output_stream_layout(profile, &recovered, forged, &cells,)
            .is_none()
    );
    let searched =
        verified_state_space_output_layout(profile, expected, &cells)
            .ok_or_else(|| {
                format!("full search missed no-op guest {expected:?}")
            })?;
    assert!(searched.data_write_positions().iter().flatten().count() > 0);
    Ok(())
}
