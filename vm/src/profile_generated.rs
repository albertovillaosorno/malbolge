// File:
//   - profile_generated.rs
// Path:
//   - vm/src/profile_generated.rs
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
//   - Generated Rust projection of canonical Malbolge profiles.
// - Must-Not:
//   - Become an independent profile authority or contain hand edits.
// - Allows:
//   - Inputs: validated repository-root `malbolge.json` only.
//   - Outputs: immutable descriptors for the safe Rust runtime.
//   - Side effects: none after deterministic generation.
// - Split-When:
//   - Split when another language needs an independent projection.
// - Merge-When:
//   - Merge when runtime consumes canonical JSON directly.
// - Summary:
//   - Generated canonical target-profile descriptors for Rust.
// - Description:
//   - Keeps runtime identity synchronized with `malbolge.json`.
// - Usage:
//   - Regenerate through the target-profile validator helpers.
// - Defaults:
//   - Any renderer drift fails the test suite.
//
// Related documents:
// - malbolge.json
// - docs/technical/specification/target-profile.md
//
// Large file:
//   - false

//! Generated canonical target-profile descriptors for Rust.

use super::{ProfileDescriptor, ProfileKind};

pub(super) static CURRENT_PROFILE: &ProfileDescriptor = &PROFILE_2;
pub(super) static HISTORICAL_PROFILE: &ProfileDescriptor = &PROFILE_0;

pub(super) static PROFILE_0: ProfileDescriptor = ProfileDescriptor {
    eof_word: 59_048,
    id: "malbolge-1998",
    kind: ProfileKind::HistoricalConformance,
    memory_words: 59_049,
    version: "1998",
    word_modulus: 59_049,
    word_trits: 10,
};

pub(super) static PROFILE_1: ProfileDescriptor = ProfileDescriptor {
    eof_word: 59_048,
    id: "malbolge-2026.1",
    kind: ProfileKind::Versioned,
    memory_words: 59_049,
    version: "2026.1",
    word_modulus: 59_049,
    word_trits: 10,
};

pub(super) static PROFILE_2: ProfileDescriptor = ProfileDescriptor {
    eof_word: 4_782_968,
    id: "malbolge-2026.2",
    kind: ProfileKind::Current,
    memory_words: 4_782_969,
    version: "2026.2",
    word_modulus: 4_782_969,
    word_trits: 14,
};

pub(super) static PROFILE_DESCRIPTORS: [&ProfileDescriptor; 3] =
    [&PROFILE_0, &PROFILE_1, &PROFILE_2];
