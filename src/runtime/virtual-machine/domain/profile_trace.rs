// Copyright:
//   - Copyright (c) 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - MIT
// Confidential:
//   - false
// License-File:
//   - LICENSE-MIT
//
// Boundary-Contract:
// - Owns:
//   - Immutable observation records for profile-driven VM transitions.
// - Must-Not:
//   - Perform logging, scheduling, serialization, or mutate guest execution.
// - Allows:
//   - Inputs: profile identity, profile-width state, decoded bytes, and
//   - effects.
//   - Outputs: deterministic trace records for verification and future tiers.
//   - Side effects: none.
// - Split-When:
//   - Split when persistent profile-trace serialization gains its own contract.
// - Merge-When:
//   - Merge when classic and profiled trace state share one width-safe type.
// - Summary:
//   - Observes every requested profile-driven step without changing semantics.
// - Description:
//   - Carries exact canonical profile identity and u32 profile-width state.
// - Usage:
//   - Emitted by `ProfileMachine::step_traced` and `run_traced` observers.
// - Defaults:
//   - Profile tracing is specification-only; legacy behavior stays
//   - classic-only.
//

//! Immutable trace evidence for profile-driven safe Rust execution.

use crate::{
    ProfileDescriptor, ProfileMachineError, ProfileRegisters, StepOutcome,
    Termination, TraceInput,
};

/// Observable profile-driven machine state at one trace boundary.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct ProfileMachineObservation {
    /// Number of input bytes consumed by committed transitions.
    pub input_consumed: usize,
    /// Number of output bytes emitted by committed transitions.
    pub output_len: usize,
    /// Profile-width register values at this boundary.
    pub registers: ProfileRegisters,
    /// Stable termination reason, when execution has terminated.
    pub termination: Option<Termination>,
}

/// One actual semantic profile-memory read performed by the step engine.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct ProfileMemoryRead {
    /// Profile-width address read by the normative transition.
    pub address: u32,
    /// Exact word returned by that semantic read.
    pub value: u32,
}

/// Fixed-role semantic memory reads performed by one requested profile step.
#[derive(Clone, Copy, Debug, Default, Eq, PartialEq)]
pub struct ProfileMemoryReads {
    /// Instruction data-pointer read, when the decoded instruction requires
    /// it.
    pub data: Option<ProfileMemoryRead>,
    /// Self-encryption target read when no same-address planned write supplies
    /// it.
    pub encryption: Option<ProfileMemoryRead>,
    /// Current code-cell fetch performed before decode.
    pub fetch: Option<ProfileMemoryRead>,
}

impl ProfileMemoryReads {
    /// Returns the number of semantic read operations represented by this step.
    #[must_use]
    pub const fn read_count(self) -> usize {
        let data = match self.data {
            Some(_read) => 1usize,
            None => 0usize,
        };
        let encryption = match self.encryption {
            Some(_read) => 1usize,
            None => 0usize,
        };
        let fetch = match self.fetch {
            Some(_read) => 1usize,
            None => 0usize,
        };
        data.saturating_add(encryption).saturating_add(fetch)
    }
}

/// Actual changed memory cells committed by one profile-driven step.
#[derive(Clone, Copy, Debug, Default, Eq, PartialEq)]
pub struct ProfileMemoryDelta {
    /// Instruction-specific data-cell change when distinct from encryption.
    pub data: Option<ProfileMemoryWrite>,
    /// Final self-encryption cell change.
    pub encryption: Option<ProfileMemoryWrite>,
}

impl ProfileMemoryDelta {
    /// Returns the number of distinct memory cells changed by this step.
    #[must_use]
    pub const fn changed_cells(self) -> usize {
        let data = match self.data {
            Some(_write) => 1usize,
            None => 0usize,
        };
        let encryption = match self.encryption {
            Some(_write) => 1usize,
            None => 0usize,
        };
        data.saturating_add(encryption)
    }
}

/// One actual profile-width memory-cell change committed by a step.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct ProfileMemoryWrite {
    /// Profile-width address whose final value changed.
    pub address: u32,
    /// Final committed word after the step.
    pub after: u32,
    /// Word observed before the step committed.
    pub before: u32,
}

/// Deterministic evidence emitted for one requested profile-driven step.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct ProfileStepTrace {
    /// Observable machine state after the requested step returns.
    pub after: ProfileMachineObservation,
    /// Observable machine state before the requested step begins.
    pub before: ProfileMachineObservation,
    /// Decoded normative instruction byte, when decode was reached.
    pub decoded: Option<u8>,
    /// Current profile-width code cell fetched for this request.
    pub fetched_cell: Option<u32>,
    /// Input effect selected by a successfully planned input instruction.
    pub input: Option<TraceInput>,
    /// Actual committed memory changes for this requested step.
    pub memory_delta: ProfileMemoryDelta,
    /// Semantic memory reads performed by the real transition engine.
    pub memory_reads: ProfileMemoryReads,
    /// Output byte emitted by a successfully committed output instruction.
    pub output: Option<u8>,
    /// Exact canonical profile identity for the observed machine.
    pub profile: &'static ProfileDescriptor,
    /// Exact public result returned by the requested step.
    pub result: Result<StepOutcome, ProfileMachineError>,
}
