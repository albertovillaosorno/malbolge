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

//! Generated canonical target-profile descriptors for Rust.

use super::{ProfileDescriptor, ProfileKind};

pub(super) const CURRENT_PROFILE: &ProfileDescriptor = &PROFILE_1;
pub(super) const HISTORICAL_PROFILE: &ProfileDescriptor = &PROFILE_0;

pub(super) const PROFILE_0: ProfileDescriptor = ProfileDescriptor {
    eof_word: 59_048,
    fingerprint: concat!(
        "malbolge-profile-v1:sha256:",
        "8b8689e5e3daef745d58681efe78106070736abb2ffa0895511fac5150b5b73e",
    ),
    id: "malbolge-1998",
    input_instruction: b'/',
    kind: ProfileKind::HistoricalConformance,
    memory_words: 59_049,
    output_instruction: b'<',
    version: "1998",
    word_modulus: 59_049,
    word_trits: 10,
};

pub(super) const PROFILE_1: ProfileDescriptor = ProfileDescriptor {
    eof_word: 14_348_906,
    fingerprint: concat!(
        "malbolge-profile-v1:sha256:",
        "8a93ad8fee1d3be48c432c23a74cff5ed50d85e07444dcecece103e4fe22c16e",
    ),
    id: "malbolge-2026",
    input_instruction: b'/',
    kind: ProfileKind::Current,
    memory_words: 14_348_907,
    output_instruction: b'<',
    version: "2026",
    word_modulus: 14_348_907,
    word_trits: 15,
};

pub(super) const PROFILE_2: ProfileDescriptor = ProfileDescriptor {
    eof_word: 59_048,
    fingerprint: concat!(
        "malbolge-profile-v1:sha256:",
        "e72da529edefea13c4855b83decf61593d3ad64e5231c4911a2391cbd7567204",
    ),
    id: "malbolge-2026.1",
    input_instruction: b'<',
    kind: ProfileKind::Versioned,
    memory_words: 59_049,
    output_instruction: b'/',
    version: "2026.1",
    word_modulus: 59_049,
    word_trits: 10,
};

pub(super) const PROFILE_3: ProfileDescriptor = ProfileDescriptor {
    eof_word: 4_782_968,
    fingerprint: concat!(
        "malbolge-profile-v1:sha256:",
        "e33e1488162dffdc8bad9102df8eed3f8aac294d057b4f7ad7a389906963fc50",
    ),
    id: "malbolge-2026.2",
    input_instruction: b'<',
    kind: ProfileKind::Versioned,
    memory_words: 4_782_969,
    output_instruction: b'/',
    version: "2026.2",
    word_modulus: 4_782_969,
    word_trits: 14,
};

pub(super) const PROFILE_4: ProfileDescriptor = ProfileDescriptor {
    eof_word: 4_782_968,
    fingerprint: concat!(
        "malbolge-profile-v1:sha256:",
        "14de1b012b349930ca3e8c01b37b126c4e7f274c1bbcacd31b4b82523e0f4230",
    ),
    id: "malbolge-2026.3",
    input_instruction: b'/',
    kind: ProfileKind::Versioned,
    memory_words: 4_782_969,
    output_instruction: b'<',
    version: "2026.3",
    word_modulus: 4_782_969,
    word_trits: 14,
};

pub(super) const PROFILE_DESCRIPTORS: [&ProfileDescriptor; 5] =
    [&PROFILE_0, &PROFILE_1, &PROFILE_2, &PROFILE_3, &PROFILE_4];
