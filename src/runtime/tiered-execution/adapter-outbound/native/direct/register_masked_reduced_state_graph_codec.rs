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
//   - Canonical durable bytes for replayable dependency-reduced v6 graph
//     provenance.
// - Must-Not:
//   - Serialize verifier authority, trust durable identity/program claims, or
//     reconstruct non-canonical execution geometry from bytes.
// - Allows:
//   - Inputs: verifier-admitted graph claims or untrusted durable bytes.
//   - Outputs: canonical provenance bytes or a freshly replay-verified graph.
//   - Side effects: normative VM replay and process-local allocation only.
// - Split-When:
//   - Durable storage policy, compression, authentication, or migration gains
//     independent ownership.
// - Merge-When:
//   - One general AOT graph artifact codec subsumes reduced graph provenance.
// - Summary:
//   - Persists exact witnesses and rebuilds all reduced authority on load.
// - Description:
//   - The durable format stores only profile-bound checkpoints, step budgets,
//     and topology. Loading reprojects v6 IR and re-derives reduced guards.
// - Usage:
//   - Encode only admitted claims; decode before AOT preparation or dispatch.
// - Defaults:
//   - Malformed, non-canonical, unknown-profile, or unverifiable bytes fail
//     closed without publishing a graph.
//

//! Durable provenance codec for dependency-reduced register-masked v6 graphs.

use std::fmt::{Display, Formatter, Result as FormatResult};
use std::str;

use malbolge::{
    ProfileMachine, ProfileMachineError, ProfileMachineIoState,
    ProfileMachineState, ProfileRegisters, ProfileStepTrace,
    RegisterMaskedRegionEffectProgram, RegisterMaskedRegionProjectionError,
    Termination, target_profile,
};

use super::{
    AheadOfExecutionRegisterMaskedReducedStateGraphError,
    AheadOfExecutionRegisterMaskedReducedStateGraphNodeClaim,
    RegisterMaskedDependencyIdentityClaim,
    UntrustedAheadOfExecutionRegisterMaskedReducedStateGraph,
    VerifiedAheadOfExecutionRegisterMaskedReducedStateGraph,
};

const DURABLE_MAGIC: &[u8; 4] = b"MBRG";
const DURABLE_VERSION: u16 = 1;

/// Failure while encoding or replay-loading one durable reduced v6 graph.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum AheadOfExecutionRegisterMaskedReducedStateGraphCodecError {
    /// A decoded checkpoint failed canonical profile-machine validation.
    Checkpoint(ProfileMachineError),
    /// Rebuilt graph evidence failed ordinary reduced-graph verification.
    Graph(AheadOfExecutionRegisterMaskedReducedStateGraphError),
    /// One host-sized field cannot fit the canonical unsigned 64-bit format.
    LengthOverflow,
    /// Durable bytes did not begin with the reduced-graph format magic.
    Magic,
    /// Stored profile fingerprint disagreed with the canonical descriptor.
    ProfileFingerprint,
    /// One stored profile identity was not valid UTF-8.
    ProfileId,
    /// Replaying one durable witness failed before v6 reprojection.
    Replay {
        /// Zero-based durable node index.
        index: usize,
        /// Exact normative VM failure.
        error: ProfileMachineError,
    },
    /// One node exceeds the caller-owned deterministic replay step limit.
    ReplayStepLimit {
        /// Zero-based durable node index.
        index: usize,
        /// Maximum replay steps accepted for one node.
        limit: usize,
        /// Durable step budget that exceeded the caller-owned limit.
        observed: usize,
    },
    /// Replaying one durable witness could not reproject canonical v6 IR.
    Reprojection {
        /// Zero-based durable node index.
        index: usize,
        /// Exact product-owned v6 projection failure.
        error: RegisterMaskedRegionProjectionError,
    },
    /// Durable bytes contained an unsupported successor tag.
    SuccessorTag,
    /// Durable bytes contained an unsupported termination tag.
    Termination,
    /// Canonical decoding left bytes after the complete graph payload.
    TrailingBytes,
    /// Durable bytes ended before one complete field could be decoded.
    Truncated,
    /// One stored profile identity is not in the canonical profile registry.
    UnknownProfile,
    /// A length/index encoded by the artifact cannot fit this host `usize`.
    UsizeOverflow,
    /// Durable bytes declare a schema version this runtime does not support.
    Version,
}

/// Caller-owned CPU bound for deterministic durable graph replay.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct AheadOfExecutionRegisterMaskedReducedStateGraphDecodeLimits {
    maximum_replay_steps_per_node: usize,
}

type CodecError = AheadOfExecutionRegisterMaskedReducedStateGraphCodecError;
type NodeClaim = AheadOfExecutionRegisterMaskedReducedStateGraphNodeClaim;
type ReducedGraph = VerifiedAheadOfExecutionRegisterMaskedReducedStateGraph;

struct Decoder<'bytes> {
    bytes: &'bytes [u8],
    cursor: usize,
}

impl Display for AheadOfExecutionRegisterMaskedReducedStateGraphCodecError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::Checkpoint(error) => {
                write!(f, "durable reduced graph checkpoint failed: {error}")
            },
            Self::Graph(error) => {
                write!(f, "durable reduced graph verification failed: {error}")
            },
            Self::LengthOverflow => {
                f.write_str("durable reduced graph length exceeds u64")
            },
            Self::Magic => f.write_str("durable reduced graph magic mismatch"),
            Self::ProfileFingerprint => f.write_str(
                "durable reduced graph profile fingerprint mismatched",
            ),
            Self::ProfileId => {
                f.write_str("durable reduced graph profile id is not UTF-8")
            },
            Self::Replay { error, index } => write!(
                f,
                "durable reduced graph node {index} replay failed: {error}"
            ),
            Self::Reprojection { index, .. } => write!(
                f,
                "durable reduced graph node {index} v6 reprojection failed"
            ),
            Self::ReplayStepLimit { index, limit, observed } => {
                write!(f, "durable reduced graph node {index} replay budget ")?;
                write!(f, "{observed} exceeds limit {limit}")
            },
            Self::SuccessorTag => {
                f.write_str("durable reduced graph successor tag is invalid")
            },
            Self::Termination => {
                f.write_str("durable reduced graph termination tag is invalid")
            },
            Self::TrailingBytes => {
                f.write_str("durable reduced graph has trailing bytes")
            },
            Self::Truncated => {
                f.write_str("durable reduced graph is truncated")
            },
            Self::UnknownProfile => {
                f.write_str("durable reduced graph profile is unknown")
            },
            Self::UsizeOverflow => {
                f.write_str("durable reduced graph index exceeds host usize")
            },
            Self::Version => {
                f.write_str("durable reduced graph version is unsupported")
            },
        }
    }
}

impl AheadOfExecutionRegisterMaskedReducedStateGraphDecodeLimits {
    /// Returns the maximum normative replay steps accepted for one node.
    #[must_use]
    pub const fn maximum_replay_steps_per_node(self) -> usize {
        self.maximum_replay_steps_per_node
    }

    /// Constructs one explicit caller-owned replay CPU bound.
    #[must_use]
    pub const fn new(maximum_replay_steps_per_node: usize) -> Self {
        Self {
            maximum_replay_steps_per_node,
        }
    }
}

impl<'bytes> Decoder<'bytes> {
    const fn finish(self) -> Result<(), CodecError> {
        if self.cursor == self.bytes.len() {
            Ok(())
        } else {
            Err(CodecError::TrailingBytes)
        }
    }

    const fn new(bytes: &'bytes [u8]) -> Self {
        Self { bytes, cursor: 0 }
    }

    const fn remaining(&self) -> usize {
        self.bytes.len().saturating_sub(self.cursor)
    }

    fn take(&mut self, length: usize) -> Result<&'bytes [u8], CodecError> {
        let end = self
            .cursor
            .checked_add(length)
            .ok_or(CodecError::UsizeOverflow)?;
        let value = self
            .bytes
            .get(self.cursor..end)
            .ok_or(CodecError::Truncated)?;
        self.cursor = end;
        Ok(value)
    }

    fn u16(&mut self) -> Result<u16, CodecError> {
        let bytes = self.take(size_of::<u16>())?;
        let array = <[u8; size_of::<u16>()]>::try_from(bytes)
            .map_err(|_conversion_error| CodecError::Truncated)?;
        Ok(u16::from_le_bytes(array))
    }

    fn u32(&mut self) -> Result<u32, CodecError> {
        let bytes = self.take(size_of::<u32>())?;
        let array = <[u8; size_of::<u32>()]>::try_from(bytes)
            .map_err(|_conversion_error| CodecError::Truncated)?;
        Ok(u32::from_le_bytes(array))
    }

    fn u64(&mut self) -> Result<u64, CodecError> {
        let bytes = self.take(size_of::<u64>())?;
        let array = <[u8; size_of::<u64>()]>::try_from(bytes)
            .map_err(|_conversion_error| CodecError::Truncated)?;
        Ok(u64::from_le_bytes(array))
    }

    fn u8(&mut self) -> Result<u8, CodecError> {
        self.take(1)?.first().copied().ok_or(CodecError::Truncated)
    }

    fn usize(&mut self) -> Result<usize, CodecError> {
        usize::try_from(self.u64()?)
            .map_err(|_conversion_error| CodecError::UsizeOverflow)
    }
}

/// Encodes replayable provenance after independently admitting the full claim.
///
/// Identity and v6 program bytes are intentionally omitted because loading must
/// rederive them from the exact witness. This prevents durable bytes from
/// carrying verifier authority across processes.
///
/// # Errors
///
/// Returns graph admission failure for an unverified claim or length overflow
/// when one host-sized field cannot fit the canonical unsigned 64-bit format.
pub fn encode_ahead_of_execution_register_masked_reduced_state_graph(
    claim: &UntrustedAheadOfExecutionRegisterMaskedReducedStateGraph,
) -> Result<Vec<u8>, CodecError> {
    let verified_graph = claim.verify().map_err(CodecError::Graph)?;
    let mut bytes = Vec::new();
    bytes.extend_from_slice(DURABLE_MAGIC);
    push_u16(&mut bytes, DURABLE_VERSION);
    push_usize(&mut bytes, verified_graph.entry())?;
    push_usize(&mut bytes, claim.nodes().len())?;
    for node in claim.nodes() {
        encode_checkpoint(&mut bytes, &node.witness)?;
        push_usize(&mut bytes, node.program.program.step_budget)?;
        encode_successor(&mut bytes, node.successor)?;
    }
    Ok(bytes)
}

/// Decodes durable provenance and rebuilds all reduced authority by VM replay.
///
/// # Errors
///
/// Returns a typed codec, checkpoint, reprojection, replay, or graph-admission
/// failure. `limits` bounds normative CPU replay independently of artifact
/// claims. No partially decoded or unverified graph is published.
pub fn decode_ahead_of_execution_register_masked_reduced_state_graph(
    bytes: &[u8],
    limits: AheadOfExecutionRegisterMaskedReducedStateGraphDecodeLimits,
) -> Result<ReducedGraph, CodecError> {
    let mut decoder = Decoder::new(bytes);
    if decoder.take(DURABLE_MAGIC.len())? != DURABLE_MAGIC {
        return Err(CodecError::Magic);
    }
    if decoder.u16()? != DURABLE_VERSION {
        return Err(CodecError::Version);
    }
    let entry = decoder.usize()?;
    let node_count = decoder.usize()?;
    let mut nodes = Vec::new();
    for index in 0..node_count {
        let witness = decode_checkpoint(&mut decoder)?;
        let step_budget = decoder.usize()?;
        if step_budget > limits.maximum_replay_steps_per_node() {
            return Err(CodecError::ReplayStepLimit {
                index,
                limit: limits.maximum_replay_steps_per_node(),
                observed: step_budget,
            });
        }
        let successor = decode_successor(&mut decoder)?;
        nodes.push(rebuild_claim(index, witness, step_budget, successor)?);
    }
    decoder.finish()?;
    UntrustedAheadOfExecutionRegisterMaskedReducedStateGraph::new(entry, nodes)
        .verify()
        .map_err(CodecError::Graph)
}

fn decode_bytes<'bytes>(
    decoder: &mut Decoder<'bytes>,
) -> Result<&'bytes [u8], CodecError> {
    let length = decoder.usize()?;
    decoder.take(length)
}

fn decode_checkpoint(
    decoder: &mut Decoder<'_>,
) -> Result<ProfileMachineState, CodecError> {
    let profile_bytes = decode_bytes(decoder)?;
    let profile_id = str::from_utf8(profile_bytes)
        .map_err(|_utf8_error| CodecError::ProfileId)?;
    let profile =
        target_profile(profile_id).ok_or(CodecError::UnknownProfile)?;
    let fingerprint = decode_bytes(decoder)?;
    if fingerprint != profile.fingerprint().as_bytes() {
        return Err(CodecError::ProfileFingerprint);
    }
    let memory_count = decoder.usize()?;
    let byte_count = memory_count
        .checked_mul(size_of::<u32>())
        .ok_or(CodecError::UsizeOverflow)?;
    if byte_count > decoder.remaining() {
        return Err(CodecError::Truncated);
    }
    let mut memory = Vec::with_capacity(memory_count);
    for _word in 0..memory_count {
        memory.push(decoder.u32()?);
    }
    let registers = ProfileRegisters {
        accumulator: decoder.u32()?,
        code_pointer: decoder.u32()?,
        data_pointer: decoder.u32()?,
    };
    let input = decode_bytes(decoder)?.to_vec();
    let input_cursor = decoder.usize()?;
    let output = decode_bytes(decoder)?.to_vec();
    let termination = decode_termination(decoder.u8()?)?;
    let io =
        ProfileMachineIoState::new(input, input_cursor, output, termination)
            .map_err(CodecError::Checkpoint)?;
    ProfileMachineState::new(profile, memory, registers, io)
        .map_err(CodecError::Checkpoint)
}

fn decode_successor(
    decoder: &mut Decoder<'_>,
) -> Result<Option<usize>, CodecError> {
    match decoder.u8()? {
        0 => Ok(None),
        1 => decoder.usize().map(Some),
        _ => Err(CodecError::SuccessorTag),
    }
}

const fn decode_termination(
    tag: u8,
) -> Result<Option<Termination>, CodecError> {
    match tag {
        0 => Ok(None),
        1 => Ok(Some(Termination::HaltInstruction)),
        2 => Ok(Some(Termination::NonGraphicalCell)),
        _ => Err(CodecError::Termination),
    }
}

fn encode_checkpoint(
    bytes: &mut Vec<u8>,
    witness: &ProfileMachineState,
) -> Result<(), CodecError> {
    push_bytes(bytes, witness.profile().id().as_bytes())?;
    push_bytes(bytes, witness.profile().fingerprint().as_bytes())?;
    push_usize(bytes, witness.memory().len())?;
    for word in witness.memory() {
        push_u32(bytes, *word);
    }
    let registers = witness.registers();
    push_u32(bytes, registers.accumulator);
    push_u32(bytes, registers.code_pointer);
    push_u32(bytes, registers.data_pointer);
    push_bytes(bytes, witness.io().input())?;
    push_usize(bytes, witness.io().input_consumed())?;
    push_bytes(bytes, witness.io().output())?;
    bytes.push(encode_termination(witness.io().termination()));
    Ok(())
}

fn encode_successor(
    bytes: &mut Vec<u8>,
    successor: Option<usize>,
) -> Result<(), CodecError> {
    match successor {
        None => bytes.push(0),
        Some(index) => {
            bytes.push(1);
            push_usize(bytes, index)?;
        },
    }
    Ok(())
}

const fn encode_termination(termination: Option<Termination>) -> u8 {
    match termination {
        None => 0,
        Some(Termination::HaltInstruction) => 1,
        Some(Termination::NonGraphicalCell) => 2,
    }
}

fn push_bytes(bytes: &mut Vec<u8>, value: &[u8]) -> Result<(), CodecError> {
    push_usize(bytes, value.len())?;
    bytes.extend_from_slice(value);
    Ok(())
}

fn push_u16(bytes: &mut Vec<u8>, value: u16) {
    bytes.extend_from_slice(&value.to_le_bytes());
}

fn push_u32(bytes: &mut Vec<u8>, value: u32) {
    bytes.extend_from_slice(&value.to_le_bytes());
}

fn push_usize(bytes: &mut Vec<u8>, value: usize) -> Result<(), CodecError> {
    let encoded = u64::try_from(value)
        .map_err(|_conversion_error| CodecError::LengthOverflow)?;
    bytes.extend_from_slice(&encoded.to_le_bytes());
    Ok(())
}

fn rebuild_claim(
    index: usize,
    witness: ProfileMachineState,
    step_budget: usize,
    successor: Option<usize>,
) -> Result<NodeClaim, CodecError> {
    let mut machine = ProfileMachine::from_snapshot(witness.clone());
    let mut traces = Vec::new();
    let outcome = machine
        .run_traced(step_budget, &mut |trace: &ProfileStepTrace| {
            traces.push(*trace);
        })
        .map_err(|error| CodecError::Replay { index, error })?;
    let program =
        RegisterMaskedRegionEffectProgram::from_profile_region_traces(
            witness.profile(),
            &traces,
            step_budget,
            outcome,
        )
        .map_err(|error| CodecError::Reprojection { index, error })?;
    let identity =
        RegisterMaskedDependencyIdentityClaim::from_witness_and_program(
            &witness, &program,
        );
    Ok(NodeClaim {
        identity,
        program,
        successor,
        witness,
    })
}
