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
//   - Canonical module topology for pre-layout ternary machine lowering.
// - Must-Not:
//   - Re-own typed IR, target layout, Malbolge encoding, or runtime execution.
// - Allows:
//   - Inputs: explicit inbound typed-IR semantic projection records.
//   - Outputs: one logical Rust surface for ternary lowering and its tests.
//   - Side effects: composition only.
// - Split-When:
//   - The target representation gains independently packaged capabilities.
// - Merge-When:
//   - Another root owns this exact lowering module topology.
// - Summary:
//   - Declares the canonical pre-layout ternary lowering module tree.
// - Description:
//   - Keeps downstream layout/encoding separate from typed semantic lowering.
// - Usage:
//   - Included by compiler lowering integration tests and future composition.
// - Defaults:
//   - Upstream compiler implementation types never cross this function
//     boundary.
//

//! Canonical module topology for pre-layout ternary machine lowering.

#[path = "../port-inbound/typed_ir.rs"]
mod input;
#[path = "../application/lower.rs"]
mod lower;
#[path = "../application/lower_runtime_intrinsic.rs"]
mod lower_runtime_intrinsic;
#[path = "../domain/model.rs"]
mod model;
#[path = "../port-inbound/runtime_intrinsic.rs"]
mod runtime_intrinsic_input;

pub use input::*;
pub use lower::{TernaryLoweringError, lower_typed_ir};
pub use lower_runtime_intrinsic::{
    RuntimeIntrinsicLoweringError, lower_runtime_intrinsic,
};
pub use model::*;
pub use runtime_intrinsic_input::RuntimeIntrinsicRequest;
