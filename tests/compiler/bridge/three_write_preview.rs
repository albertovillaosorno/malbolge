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
//   - Deterministic agreement of the cached three-write proposal filter.
// - Must-Not:
//   - Treat a preview as guest execution or authorization to publish.
// - Allows:
//   - Inputs: bounded arithmetic sequences and position-encoded source cells.
//   - Outputs: candidate-preview agreement with the complete proposal model.
//   - Side effects: none.
// - Split-When:
//   - The three-write grammar gains a separate reusable search implementation.
// - Merge-When:
//   - A single generalized source-independent proposal verifier replaces it.
// - Summary:
//   - Prevents cached memory tails from incorrectly rejecting guest candidates.
// - Description:
//   - A 384-case matrix compares distinct proposal algorithms before VM proof.
// - Usage:
//   - cargo test --locked --test byte_echo_bridge three_write_preview_matches
// - Defaults:
//   - Current-profile, three disjoint writes, bounded positional phases.

use super::*;

const CRAZY: LinearOpcode = LinearOpcode::CrazyData;
const ROTATE: LinearOpcode = LinearOpcode::RotateData;
const PATTERNS: [[LinearOpcode; 3]; 8] = [
    [CRAZY, CRAZY, CRAZY],
    [CRAZY, CRAZY, ROTATE],
    [CRAZY, ROTATE, CRAZY],
    [CRAZY, ROTATE, ROTATE],
    [ROTATE, CRAZY, CRAZY],
    [ROTATE, CRAZY, ROTATE],
    [ROTATE, ROTATE, CRAZY],
    [ROTATE, ROTATE, ROTATE],
];

fn compare_three_write_candidate(
    cells: &[[u8; 6]],
    cache: &mut BTreeMap<usize, Vec<u32>>,
    geometry: [usize; 4],
    operations: [LinearOpcode; 3],
) -> Result<(), String> {
    let [padding, first, second, third] = geometry;
    let strides = [first, second, third];
    let fast = preview_three_write_suffix(
        cells,
        cache,
        [padding, first, second, third],
        operations,
    );
    let mut source = vec![LinearOpcode::NoOperation; padding];
    source.push(LinearOpcode::RelocateDataPointer);
    for (stride, operation) in strides.into_iter().zip(operations) {
        source.extend(repeat_n(LinearOpcode::NoOperation, stride));
        source.push(operation);
    }
    source.extend([LinearOpcode::OutputByte, LinearOpcode::Halt]);
    let complete =
        proposed_output_stream::<1>(&source, cells).map(|output| output[0]);
    if fast != complete {
        return Err(format!(
            "preview mismatch: padding={padding}, strides={strides:?}, \
             operations={operations:?}, fast={fast:?}, \
             complete={complete:?}"
        ));
    }
    Ok(())
}

#[test]
fn three_write_preview_matches_full_source_model() -> Result<(), String> {
    let cells = pair_source_cells(current_profile())
        .ok_or_else(|| String::from("missing current-profile encodings"))?;
    let mut cache = BTreeMap::new();
    for padding in 0usize..12usize {
        for strides in [[0, 0, 0], [2, 5, 8], [8, 20, 20], [1, 3, 19]] {
            for operations in PATTERNS {
                compare_three_write_candidate(
                    &cells,
                    &mut cache,
                    [padding, strides[0], strides[1], strides[2]],
                    operations,
                )?;
            }
        }
    }
    Ok(())
}
