// Copyright:
//   - Copyright © 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - MIT
// Confidential:
//   - false
// License-File:
//   - LICENSE-MIT
//
// Boundary-Contract:
// - Owns:
//   - Persistent output materialization and exact-branch equality fixtures.
// - Must-Not:
//   - Treat digest equality as output equality or change runtime output
//   - semantics.
// - Allows:
//   - Inputs: initial committed byte prefixes and append-only byte histories.
//   - Outputs: exact materialization/equality evidence for persistent output.
//   - Side effects: test-process allocation only.
// - Split-When:
//   - Split when chunked output strategies gain independent evidence.
// - Merge-When:
//   - Merge when production output storage owns the same persistent contract.
// - Summary:
//   - Proves immutable append histories preserve exact committed output bytes.
// - Description:
//   - Compares shared and independently built branches plus a long history.
// - Usage:
//   - Composed by `tests/state_graph_research.rs`.
// - Defaults:
//   - Materialized bytes remain the independent equality oracle.
//

//! Exact persistent-output fixtures for incremental state identity.

use crate::persistent_output::PersistentOutput;

const LONG_OUTPUT_BYTES: usize = 65_536;

#[test]
fn independent_equal_branches_compare_exactly() -> Result<(), String> {
    let root = PersistentOutput::from_bytes(b"prefix");
    let left = root.append(0x41).append(0x42).append(0x43);
    let right = root.append(0x41).append(0x42).append(0x43);
    if !left.exact_output_eq(&right) {
        return Err(String::from(
            "equal output branches did not compare exactly",
        ));
    }
    if left.materialize() != b"prefixABC" {
        return Err(String::from(
            "equal output branch materialized incorrectly",
        ));
    }
    Ok(())
}

#[test]
fn different_output_branches_remain_distinct() -> Result<(), String> {
    let root = PersistentOutput::from_bytes(b"prefix");
    let left = root.append(0x41);
    let right = root.append(0x42);
    if left.exact_output_eq(&right) {
        Err(String::from("different output branches compared equal"))
    } else {
        Ok(())
    }
}

#[test]
fn long_append_history_materializes_without_prefix_loss() -> Result<(), String>
{
    let root = PersistentOutput::from_bytes(b"seed");
    let mut output = root;
    for raw in 0..LONG_OUTPUT_BYTES {
        let byte = u8::try_from(raw & 0xff).map_err(|error| {
            format!("output byte conversion failed: {error}")
        })?;
        output = output.append(byte);
    }
    let materialized = output.materialize();
    if output.len() != b"seed".len().saturating_add(LONG_OUTPUT_BYTES) {
        return Err(String::from("persistent output length mismatch"));
    }
    if materialized.get(..4) != Some(b"seed".as_slice()) {
        return Err(String::from("persistent output prefix changed"));
    }
    let last = materialized
        .last()
        .copied()
        .ok_or_else(|| String::from("persistent output unexpectedly empty"))?;
    if last != 0xff {
        return Err(String::from("persistent output suffix mismatch"));
    }
    Ok(())
}
