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
//   - Verify a four-arithmetic-write, three-output proposal against the full
//     model.
// - Must-Not:
//   - Admit source or guest behavior based on the cached preview alone.
// - Allows:
//   - Inputs: bounded source phases, strides and write/output interleavings.
//   - Outputs: deterministic agreement of two independent proposal models.
//   - Side effects: none.
// - Split-When:
//   - A generalized search engine replaces the bounded four-write fallback.
// - Merge-When:
//   - A single verified proposal model subsumes all intermediate caches.
// - Summary:
//   - Prevents cache pruning from dropping valid guest triple candidates.
// - Description:
//   - Checks all four-write operation choices and three output placements.
// - Usage:
//   - cargo test --locked --bin malbolge_layout four_write_preview
// - Defaults:
//   - Current-profile, exact expanded memory and disjoint data writes.

use super::*;

#[test]
fn four_write_preview_matches_full_source_model() -> Result<(), String> {
    let cells = pair_source_cells(current_profile())
        .ok_or_else(|| String::from("missing current-profile encodings"))?;
    let mut cache = BTreeMap::new();
    for padding in 0..12 {
        for strides in [[0, 0, 0, 0], [2, 3, 5, 8], [8, 12, 12, 12]] {
            let geometry =
                [padding, strides[0], strides[1], strides[2], strides[3]];
            for bits in 0usize..16 {
                let mut writes = [LinearOpcode::CrazyData; 4];
                for (bit, operation) in writes.iter_mut().enumerate() {
                    if bits & (1 << bit) != 0 {
                        *operation = LinearOpcode::RotateData;
                    }
                }
                for deferred_output in 0..3 {
                    let operations = four_write_triple_operations(
                        geometry,
                        writes,
                        deferred_output,
                    );
                    let complete =
                        proposed_output_stream::<3>(&operations, &cells);
                    if let Some(expected) = complete {
                        let preview = preview_four_write_triple(
                            &cells,
                            &mut cache,
                            geometry,
                            writes,
                            deferred_output,
                            expected,
                        );
                        if preview != Some(expected) {
                            return Err(format!(
                                "four-write preview mismatch: {geometry:?}, \
                                 {writes:?}, {deferred_output}: \
                                 fast={preview:?}, complete={complete:?}"
                            ));
                        }
                        let mut wrong = expected;
                        wrong[1] ^= 1;
                        assert_eq!(
                            preview_four_write_triple(
                                &cells,
                                &mut cache,
                                geometry,
                                writes,
                                deferred_output,
                                wrong,
                            ),
                            None,
                            "altered output escaped proposal pruning"
                        );
                    }
                }
            }
        }
    }
    Ok(())
}

#[test]
fn four_write_fibonacci_branch_variant_executes_in_guest() -> Result<(), String>
{
    let expected = [2, 3 ^ 0x3d, 5 ^ 0x3d];
    let cells = pair_source_cells(current_profile())
        .ok_or_else(|| String::from("missing current-profile encodings"))?;
    let layout =
        verified_four_write_triple_layout(current_profile(), expected, &cells)
            .ok_or_else(|| {
                String::from("missing four-write source-independent guest")
            })?;
    assert_eq!(
        layout.data_write_positions().iter().flatten().count(),
        4,
        "this guest must require four actual arithmetic writes"
    );
    Ok(())
}

#[test]
fn four_write_quad_preview_matches_full_source_model() -> Result<(), String> {
    let cells = pair_source_cells(current_profile())
        .ok_or_else(|| String::from("missing current-profile encodings"))?;
    let mut cache = BTreeMap::new();
    let strides = [[0, 0, 0, 0], [2, 3, 5, 8], [6, 5, 8, 7]];
    for candidate in 0..(12 * 3 * 16) {
        let padding = candidate / (3 * 16);
        let selected = strides[(candidate / 16) % 3];
        let bits = candidate % 16;
        let geometry =
            [padding, selected[0], selected[1], selected[2], selected[3]];
        let mut writes = [LinearOpcode::CrazyData; 4];
        for (bit, operation) in writes.iter_mut().enumerate() {
            if bits & (1 << bit) != 0 {
                *operation = LinearOpcode::RotateData;
            }
        }
        let operations = four_write_quad_operations(geometry, writes);
        if let Some(expected) = proposed_output_stream::<4>(&operations, &cells)
        {
            assert_eq!(
                preview_four_write_quad(
                    &cells,
                    &mut cache,
                    FourWriteQuadProposal {
                        geometry,
                        writes,
                        expected
                    },
                ),
                Some(expected),
                "quad preview disagrees: {geometry:?}, {writes:?}",
            );
            let mut wrong = expected;
            wrong[2] ^= 1;
            assert_eq!(
                preview_four_write_quad(
                    &cells,
                    &mut cache,
                    FourWriteQuadProposal {
                        geometry,
                        writes,
                        expected: wrong,
                    },
                ),
                None,
                "altered quad escaped proposal pruning",
            );
        }
    }
    Ok(())
}

#[test]
fn four_write_quad_masked_fibonacci_executes_in_guest() -> Result<(), String> {
    let expected = [0x02 ^ 0x1a, 0x03 ^ 0x3d, 0x05 ^ 0x3d, 0x08 ^ 0x1a];
    let cells = pair_source_cells(current_profile())
        .ok_or_else(|| String::from("missing current-profile encodings"))?;
    let layout =
        verified_four_write_quad_layout(current_profile(), expected, &cells)
            .ok_or_else(|| String::from("missing four-output real guest"))?;
    assert_eq!(layout.data_write_positions().iter().flatten().count(), 4);
    Ok(())
}

#[test]
fn state_space_search_finds_independent_masked_fibonacci() -> Result<(), String>
{
    let expected = [0x02 ^ 0x1a, 0x03 ^ 0x3d, 0x05 ^ 0x3d, 0x08 ^ 0x1a];
    let cells = pair_source_cells(current_profile())
        .ok_or_else(|| String::from("missing current-profile encodings"))?;
    let layout = search_output_stream::verified_state_space_output_layout(
        current_profile(),
        expected,
        &cells,
    )
    .ok_or_else(|| String::from("state-space search missed known guest"))?;
    if layout.data_write_positions().is_empty() {
        return Err(String::from("state-space guest has no real writes"));
    }
    Ok(())
}

#[test]
fn state_space_admits_five_written_outputs() -> Result<(), String> {
    let profile = current_profile();
    let cells = pair_source_cells(profile)
        .ok_or_else(|| String::from("missing current-profile encodings"))?;
    // A complete real-VM candidate with a write between the first two
    // output effects: not expressible by the older four-write grammar.
    let operations = [
        LinearOpcode::RelocateDataPointer,
        LinearOpcode::CrazyData,
        LinearOpcode::OutputByte,
        LinearOpcode::RotateData,
        LinearOpcode::CrazyData,
        LinearOpcode::OutputByte,
        LinearOpcode::RotateData,
        LinearOpcode::OutputByte,
        LinearOpcode::CrazyData,
        LinearOpcode::OutputByte,
        LinearOpcode::Halt,
    ];
    let expected = proposed_output_stream::<4>(&operations, &cells)
        .ok_or_else(|| String::from("proposal does not fit memory"))?;
    if expected != [0x35, 0xc0, 0x09, 0xe3] {
        return Err(format!("unexpected five-write guest: {expected:?}"));
    }
    let original = verified_output_stream_layout(
        profile,
        &operations,
        expected,
        &cells,
    )
    .ok_or_else(|| String::from("candidate failed normative VM proof"))?;
    if original.data_write_positions().iter().flatten().count() != 5 {
        return Err(String::from("guest performed the wrong write count"));
    }
    if verified_four_write_quad_layout(profile, expected, &cells).is_some() {
        return Err(String::from(
            "old four-write grammar already realizes guest",
        ));
    }
    let recovered = search_output_stream::verified_state_space_output_layout(
        profile, expected, &cells,
    )
    .ok_or_else(|| format!("search missed five-write trace {expected:?}"))?;
    if recovered.data_write_positions().iter().flatten().count() < 4 {
        return Err(String::from("recovered guest omitted required writes"));
    }
    Ok(())
}
