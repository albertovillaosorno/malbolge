// File:
//   - main.rs
// Path:
//   - execution/ir/main.rs
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
//   - Portable state-changing execution IR shared by future native tiers.
// - Must-Not:
//   - Verify optimizations, encode host ISA bytes, or define Malbolge
//     semantics.
// - Allows:
//   - Inputs: canonical profile identity, verified live-ins, and VM trace
//     effects.
//   - Outputs: architecture-neutral bounded-region effect programs.
//   - Side effects: none.
// - Split-When:
//   - Split when serialization and cache encoding need independent ownership.
// - Merge-When:
//   - Merge when another execution module owns the same portable effect schema.
// - Summary:
//   - Defines the versioned portable IR consumed after deterministic
//     verification.
// - Description:
//   - Carries only state-changing effects and verifier-bound region metadata.
// - Usage:
//   - Included by execution/research composition roots through explicit paths.
// - Defaults:
//   - IR data is untrusted until a verifier-owned boundary admits it.
//
// Related documents:
// - docs/technical/adr/tiered-native-execution.md
// - docs/technical/adr/verification-trust-boundary.md
//
// Large file:
//   - false

//! Portable bounded-region effect IR for tiered execution.

use malbolge::{
    ProfileMachineObservation, ProfileMemoryDelta, ProfileStepTrace,
    RunOutcome, TraceInput,
};

/// First portable bounded-region effect-IR schema version.
pub const EFFECT_IR_VERSION: u16 = 1;

/// One architecture-neutral state-changing operation from a verified VM step.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct EffectOp {
    /// Exact observable state required after this operation.
    pub after: ProfileMachineObservation,
    /// Exact observable state required before this operation.
    pub before: ProfileMachineObservation,
    /// Deterministic input effect, when this operation performs guest input.
    pub input: Option<TraceInput>,
    /// Exact final changed memory cells for this operation.
    pub memory_delta: ProfileMemoryDelta,
    /// Deterministic output byte, when this operation performs guest output.
    pub output: Option<u8>,
}

/// One verifier-derived entry-memory value required by a portable region.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct MemoryLiveIn {
    /// Profile-width memory address required at region entry.
    pub address: u32,
    /// Exact entry value required at `address`.
    pub value: u32,
}

/// Versioned architecture-neutral bounded-region program.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct RegionEffectProgram {
    /// Ordered compact state-changing operations.
    pub effects: Vec<EffectOp>,
    /// Portable effect-IR schema version.
    pub format_version: u16,
    /// Verifier-derived entry-memory live-ins.
    pub memory_live_ins: Vec<MemoryLiveIn>,
    /// Verified bounded-run outcome.
    pub outcome: RunOutcome,
    /// Canonical target-profile fingerprint.
    pub profile_fingerprint: String,
    /// Verified semantic-step budget.
    pub step_budget: usize,
}

impl EffectOp {
    /// Projects one normative VM trace to the portable state-changing subset.
    #[must_use]
    pub const fn from_trace(trace: &ProfileStepTrace) -> Self {
        Self {
            after: trace.after,
            before: trace.before,
            input: trace.input,
            memory_delta: trace.memory_delta,
            output: trace.output,
        }
    }
}
