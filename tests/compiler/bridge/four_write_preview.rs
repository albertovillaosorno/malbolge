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
