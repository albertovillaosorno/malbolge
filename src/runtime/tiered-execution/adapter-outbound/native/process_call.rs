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
//   - Owned transfer evidence for one process-isolated native entry call.
// - Must-Not:
//   - Spawn processes, allocate executable memory, or admit guest semantics.
// - Allows:
//   - Inputs: one bound native invocation and one untrusted process response.
//   - Outputs: pointer-free request/response snapshots with exact mapping
//     identity.
//   - Side effects: process-local owned allocation only.
// - Split-When:
//   - Binary framing or persistent process transport gains independent policy.
// - Merge-When:
//   - One concrete host-process adapter owns both transfer and transport.
// - Summary:
//   - Removes raw pointers from native call state crossing a process boundary.
// - Description:
//   - Keeps capacities and mapping identity explicit while final semantics stay
//     verified.
// - Usage:
//   - Construct from a bound invocation, exchange externally, then apply once.
// - Defaults:
//   - Mapping, shape, capacity, or pointer-integrity drift fails before
//     mutation.
//

//! Pointer-free process transfer contract for one native region call.

use std::fmt::{Display, Formatter, Result as FormatResult};

use super::lifecycle::NativeExecutableMappingId;

type NativeProcessCallBuffers<'buffer> =
    (&'buffer [u32], &'buffer [u8], &'buffer [u8]);

/// Structural rejection while applying one process-isolated call response.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeProcessCallResponseError {
    /// The response names a different executable mapping.
    MappingIdentity,
    /// Returned guest memory has a different length.
    MemoryLength,
    /// Returned output storage has a different capacity.
    OutputLength,
    /// The child observed mutation of one reconstructed raw pointer.
    PointerIntegrity,
    /// The returned immutable input capacity drifted.
    StateInputLength,
    /// The returned immutable guest-memory capacity drifted.
    StateMemoryWords,
    /// The returned immutable output capacity drifted.
    StateOutputCapacity,
}

/// Pointer-free scalar state transported to or from a native host process.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct NativeProcessCallState {
    accumulator: u32,
    code_pointer: u32,
    data_pointer: u32,
    input_consumed: u64,
    input_len: u64,
    memory_words: u64,
    output_capacity: u64,
    output_len: u64,
    termination_tag: u8,
}

/// Owned native call request suitable for a process transport.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct NativeProcessCallRequest {
    entry_offset: usize,
    input: Box<[u8]>,
    mapping_id: NativeExecutableMappingId,
    memory: Box<[u32]>,
    output: Box<[u8]>,
    state: NativeProcessCallState,
}

/// Owned native call response returned by an untrusted process transport.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct NativeProcessCallResponse {
    mapping_id: NativeExecutableMappingId,
    memory: Box<[u32]>,
    output: Box<[u8]>,
    pointers_unchanged: bool,
    raw_status: i32,
    state: NativeProcessCallState,
}

impl Display for NativeProcessCallResponseError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        f.write_str(match self {
            Self::MappingIdentity => "native process response mapping drifted",
            Self::MemoryLength => {
                "native process response memory length drifted"
            },
            Self::OutputLength => {
                "native process response output length drifted"
            },
            Self::PointerIntegrity => {
                "native process response pointer integrity failed"
            },
            Self::StateInputLength => {
                "native process response input capacity drifted"
            },
            Self::StateMemoryWords => {
                "native process response memory capacity drifted"
            },
            Self::StateOutputCapacity => {
                "native process response output capacity drifted"
            },
        })
    }
}

impl NativeProcessCallRequest {
    /// Returns the verified entry offset within the resident mapping.
    #[must_use]
    pub const fn entry_offset(&self) -> usize {
        self.entry_offset
    }

    /// Returns immutable input bytes copied for the child call.
    #[must_use]
    pub const fn input(&self) -> &[u8] {
        &self.input
    }

    /// Returns the exact resident mapping identity to invoke.
    #[must_use]
    pub const fn mapping_id(&self) -> NativeExecutableMappingId {
        self.mapping_id
    }

    /// Returns guest memory copied for the child call.
    #[must_use]
    pub const fn memory(&self) -> &[u32] {
        &self.memory
    }

    pub(crate) fn new(
        mapping_id: NativeExecutableMappingId,
        state: NativeProcessCallState,
        entry_offset: usize,
        buffers: NativeProcessCallBuffers<'_>,
    ) -> Self {
        let (memory, input, output) = buffers;
        Self {
            entry_offset,
            input: input.into(),
            mapping_id,
            memory: memory.into(),
            output: output.into(),
            state,
        }
    }

    /// Returns the complete mutable output capacity copied for the child call.
    #[must_use]
    pub const fn output(&self) -> &[u8] {
        &self.output
    }

    /// Returns pointer-free scalar ABI state for the child call.
    #[must_use]
    pub const fn state(&self) -> NativeProcessCallState {
        self.state
    }
}

impl NativeProcessCallResponse {
    /// Returns the mapping identity reported by the child process.
    #[must_use]
    pub const fn mapping_id(&self) -> NativeExecutableMappingId {
        self.mapping_id
    }

    /// Returns guest memory after the child call.
    #[must_use]
    pub const fn memory(&self) -> &[u32] {
        &self.memory
    }

    /// Constructs one complete process-call result for structural admission.
    #[must_use]
    pub fn new<Memory, Output>(
        mapping_id: NativeExecutableMappingId,
        state: NativeProcessCallState,
        buffers: (Memory, Output),
        result: (i32, bool),
    ) -> Self
    where
        Memory: Into<Box<[u32]>>,
        Output: Into<Box<[u8]>>,
    {
        let (memory, output) = buffers;
        let (raw_status, pointers_unchanged) = result;
        Self {
            mapping_id,
            memory: memory.into(),
            output: output.into(),
            pointers_unchanged,
            raw_status,
            state,
        }
    }

    /// Returns output storage after the child call.
    #[must_use]
    pub const fn output(&self) -> &[u8] {
        &self.output
    }

    /// Reports whether reconstructed child pointers retained exact identity.
    #[must_use]
    pub const fn pointers_unchanged(&self) -> bool {
        self.pointers_unchanged
    }

    /// Returns the raw native status produced by the child entrypoint.
    #[must_use]
    pub const fn raw_status(&self) -> i32 {
        self.raw_status
    }

    /// Returns pointer-free scalar ABI state after the child call.
    #[must_use]
    pub const fn state(&self) -> NativeProcessCallState {
        self.state
    }
}

impl NativeProcessCallState {
    /// Returns the accumulator field.
    #[must_use]
    pub const fn accumulator(self) -> u32 {
        self.accumulator
    }

    /// Returns the code-pointer field.
    #[must_use]
    pub const fn code_pointer(self) -> u32 {
        self.code_pointer
    }

    /// Returns the data-pointer field.
    #[must_use]
    pub const fn data_pointer(self) -> u32 {
        self.data_pointer
    }

    pub(crate) const fn from_raw(
        capacities: [u64; 3],
        progress: [u64; 2],
        registers: [u32; 3],
        termination_tag: u8,
    ) -> Self {
        let [memory_words, input_len, output_capacity] = capacities;
        let [input_consumed, output_len] = progress;
        let [accumulator, code_pointer, data_pointer] = registers;
        Self {
            accumulator,
            code_pointer,
            data_pointer,
            input_consumed,
            input_len,
            memory_words,
            output_capacity,
            output_len,
            termination_tag,
        }
    }

    /// Returns the committed input cursor.
    #[must_use]
    pub const fn input_consumed(self) -> u64 {
        self.input_consumed
    }

    /// Returns the immutable input capacity.
    #[must_use]
    pub const fn input_len(self) -> u64 {
        self.input_len
    }

    /// Returns the immutable guest-memory capacity.
    #[must_use]
    pub const fn memory_words(self) -> u64 {
        self.memory_words
    }

    /// Returns the immutable output capacity.
    #[must_use]
    pub const fn output_capacity(self) -> u64 {
        self.output_capacity
    }

    /// Returns the committed output length.
    #[must_use]
    pub const fn output_len(self) -> u64 {
        self.output_len
    }

    /// Returns the raw termination byte.
    #[must_use]
    pub const fn termination_tag(self) -> u8 {
        self.termination_tag
    }

    /// Replaces only the transported accumulator field.
    #[must_use]
    pub const fn with_accumulator(mut self, value: u32) -> Self {
        self.accumulator = value;
        self
    }

    /// Replaces only the transported code-pointer field.
    #[must_use]
    pub const fn with_code_pointer(mut self, value: u32) -> Self {
        self.code_pointer = value;
        self
    }

    /// Replaces only the transported data-pointer field.
    #[must_use]
    pub const fn with_data_pointer(mut self, value: u32) -> Self {
        self.data_pointer = value;
        self
    }

    /// Replaces only the transported input cursor.
    #[must_use]
    pub const fn with_input_consumed(mut self, value: u64) -> Self {
        self.input_consumed = value;
        self
    }

    /// Replaces only the transported immutable input capacity.
    #[must_use]
    pub const fn with_input_len(mut self, value: u64) -> Self {
        self.input_len = value;
        self
    }

    /// Replaces only the transported immutable memory capacity.
    #[must_use]
    pub const fn with_memory_words(mut self, value: u64) -> Self {
        self.memory_words = value;
        self
    }

    /// Replaces only the transported immutable output capacity.
    #[must_use]
    pub const fn with_output_capacity(mut self, value: u64) -> Self {
        self.output_capacity = value;
        self
    }

    /// Replaces only the transported committed output length.
    #[must_use]
    pub const fn with_output_len(mut self, value: u64) -> Self {
        self.output_len = value;
        self
    }

    /// Replaces only the transported raw termination byte.
    #[must_use]
    pub const fn with_termination_tag(mut self, value: u8) -> Self {
        self.termination_tag = value;
        self
    }
}
