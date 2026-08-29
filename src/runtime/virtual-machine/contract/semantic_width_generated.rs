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
//   - Generated Rust projection of semantic-width arithmetic.
// - Must-Not:
//   - Become independent authority or contain hand edits.
// - Allows:
//   - Inputs: validated repository-root `malbolge.json` only.
//   - Outputs: immutable semantic-width constants for Rust.
//   - Side effects: none after deterministic generation.
// - Split-When:
//   - Split when another encoding needs independent constants.
// - Merge-When:
//   - Merge when runtime consumes canonical JSON directly.
// - Summary:
//   - Generated canonical semantic-width constants for Rust.
// - Description:
//   - Keeps chunk arithmetic synchronized with `malbolge.json`.
// - Usage:
//   - Regenerate through the target-profile validator helpers.
// - Defaults:
//   - Any renderer drift fails the test suite.
//

//! Generated canonical semantic-width constants for Rust.

pub(super) const CHUNK_CARDINALITY: u16 = 243;
pub(super) const CHUNK_TRITS: usize = 5;
pub(super) const MAXIMUM_TRITS: Option<usize> = None;
pub(super) const MINIMUM_TRITS: usize = 10;
pub(super) const RADIX: u8 = 3;
