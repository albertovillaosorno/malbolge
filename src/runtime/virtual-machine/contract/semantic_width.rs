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
//   - Rust projection of the canonical semantic-width arithmetic model.
// - Must-Not:
//   - Define target-profile identities, execution limits, or host capacities.
// - Allows:
//   - Inputs: deterministic constants generated from canonical `malbolge.json`.
//   - Outputs: radix, minimum, chunk geometry, and optional semantic maximum.
//   - Side effects: none.
// - Split-When:
//   - Split when another semantic-width encoding needs independent authority.
// - Merge-When:
//   - Merge when the runtime consumes canonical JSON directly.
// - Summary:
//   - Canonical semantic-width constants for product Rust contracts.
// - Description:
//   - Keeps value arithmetic separate from profile identity and backend limits.
// - Usage:
//   - Consumed by width-generic words and exported for compatibility evidence.
// - Defaults:
//   - Current canonical model has no semantic maximum width.
//

//! Canonical semantic-width arithmetic constants projected into Rust.

#[path = "semantic_width_generated.rs"]
mod generated;

/// Canonical arithmetic chunk cardinality projected from `malbolge.json`.
pub const SEMANTIC_WIDTH_CHUNK_CARDINALITY: u16 = generated::CHUNK_CARDINALITY;
/// Canonical arithmetic chunk width projected from `malbolge.json`.
pub const SEMANTIC_WIDTH_CHUNK_TRITS: usize = generated::CHUNK_TRITS;
/// Optional semantic maximum projected from `malbolge.json` (`None` today).
pub const SEMANTIC_WIDTH_MAXIMUM_TRITS: Option<usize> =
    generated::MAXIMUM_TRITS;
/// Canonical minimum semantic word width projected from `malbolge.json`.
pub const SEMANTIC_WIDTH_MINIMUM_TRITS: usize = generated::MINIMUM_TRITS;
/// Canonical semantic radix projected from `malbolge.json`.
pub const SEMANTIC_WIDTH_RADIX: u8 = generated::RADIX;
