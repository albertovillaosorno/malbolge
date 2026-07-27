// File:
//   - property_verification.rs
// Path:
//   - tests/property_verification.rs
//
// Copyright:
//   - Copyright (c) 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - MIT
// Confidential:
//   - false
// License-File:
//   - LICENSE
// Path-Rule:
//   - All paths in this header are repository-root relative.
//
// Boundary-Contract:
// - Owns:
//   - Cargo composition for deterministic property/exhaustive verification.
// - Must-Not:
//   - Encode VM semantics or nondeterministic fuzz scheduling.
// - Allows:
//   - Inputs: responsibility-owned verification modules below `tests/`.
//   - Outputs: one Cargo-discoverable integration-test target.
//   - Side effects: test module composition only.
// - Split-When:
//   - Split when a verification family needs an independent Cargo lifecycle.
// - Merge-When:
//   - Merge when property verification no longer needs nested responsibilities.
// - Summary:
//   - Composes deterministic fuzz, differential, and exhaustive VM evidence.
// - Description:
//   - Keeps replay/shrink generation separate from semantic comparison logic.
// - Usage:
//   - Auto-discovered by Cargo during workspace tests.
// - Defaults:
//   - Contains no executable property logic of its own.
//
// Related documents:
// - docs/technical/verification/property-fuzz-and-exhaustive-testing.md
//
// Large file:
//   - false

//! Cargo composition root for deterministic property verification.

#[path = "fuzz/cases.rs"]
pub mod cases;
#[path = "differential/classic_profile.rs"]
mod classic_profile;
#[path = "exhaustive/loader_boundaries.rs"]
mod loader_boundaries;
#[path = "exhaustive/math_correspondence.rs"]
mod math_correspondence;
