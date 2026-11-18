// Copyright:
//   - Copyright © 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - Apache-2.0
// Confidential:
//   - false
// License-File:
//   - LICENSE
//
// Boundary-Contract:
// - Owns:
//   - Bounded exact-profile path and isolated C-state address admission.
// - Must-Not:
//   - Claim arbitrary input semantics, synthesize C branches, or relax the
//     forward-only layout verifier.
// - Allows:
//   - Inputs: graphical source, one binary input, a complete exact path and
//     independently expected output and input-consumption witnesses.
//   - Outputs: source-bound actual normative guest transition evidence.
//   - Side effects: bounded in-memory VM execution only.
// - Split-When:
//   - A general revisiting layout solver produces independently checked code.
// - Merge-When:
//   - A complete backend admits all nonlinear guest traces under this gate.
// - Summary:
//   - Verifies finite nonlinear paths and unused mutable-state candidates.
// - Description:
//   - Checks a complete finite source path against actual profile VM steps.
// - Usage:
//   - Call `admit_bounded_revisit_layout` with a complete input/path oracle.
// - Defaults:
//   - Rejects unproven paths, profile drift, resource overrun and no revisit.
//

//! Opt-in, input-specific admission of genuine revisiting guest code paths.
//!
//! This is not a source generator, and a successful witness is not a proof
//! for other inputs. The existing linear, forward-only API stays unchanged.

use std::collections::BTreeSet;

use malbolge::{
    ProfileDescriptor, ProfileMachine, StepOutcome, Termination, TraceInput,
    decode_profile_instruction,
};

use super::LinearProfileIdentity;

/// Hard limit for a source candidate at this independent nonlinear boundary.
pub const MAX_REVISIT_SOURCE_CELLS: usize = 4096;
/// Hard limit for one supplied complete execution-path witness.
pub const MAX_REVISIT_STEPS: usize = 512;
/// Maximum independent, distinct binary streams in one finite guest check.
pub const MAX_REVISIT_CASES: usize = 8;
/// Maximum disjoint reserved data intervals in a finite physical-path proof.
pub const MAX_GUEST_DATA_REGIONS: usize = 8;
/// Maximum total words reserved by a finite physical-path proof.
pub const MAX_GUEST_RESERVED_WORDS: u32 = 4096;

/// One committed guest I/O operation, preserving read/write ordering.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum BoundedRevisitIoEffect {
    /// A real VM input instruction, including an attempted read at EOF.
    Input(TraceInput),
    /// An actual output byte committed by the VM.
    Output(u8),
}

/// Zero-based transition index and its committed I/O effect.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct BoundedRevisitIoEvent {
    /// Index into the exact executed code path (including the halt step).
    pub step: u32,
    /// Guest effect observed at that transition.
    pub effect: BoundedRevisitIoEffect,
}

/// One instruction-caused guest memory write, excluding XLAT2 encryption.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct BoundedRevisitDataWrite {
    /// Zero-based transition index that committed the data write.
    pub step: u32,
    /// Exact profile-width data memory address.
    pub address: u32,
    /// Word present before the instruction wrote to guest memory.
    pub before: u32,
    /// Final written word prior to post-instruction code encryption.
    pub after: u32,
}

/// Complete, input-specific oracle: code visits, output, byte reads and EOF.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct BoundedRevisitExpectation<'input> {
    /// Exact binary guest input, including possible empty input.
    pub input: &'input [u8],
    /// Each executed code address in guest execution order, including halt.
    pub code_positions: &'input [u32],
    /// Independently expected bytes written by the guest.
    pub output: &'input [u8],
    /// Exact number of successful guest input bytes consumed before halt.
    pub input_consumed: usize,
    /// All committed input instructions, including attempts at EOF.
    pub input_events: &'input [TraceInput],
    /// Exact source-ordered guest I/O effects, anchored to executed steps.
    pub io_events: &'input [BoundedRevisitIoEvent],
    /// Exact executed arithmetic data writes, with pre/post word witnesses.
    pub data_writes: &'input [BoundedRevisitDataWrite],
}

/// An admitted, input-specific complete guest path; it may revisit cells.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct BoundedRevisitLayout {
    source: Vec<u8>,
    code_positions: Vec<u32>,
    data_positions: Vec<u32>,
    data_read_positions: Vec<Option<u32>>,
    encrypted_positions: Vec<Option<u32>>,
    output: Vec<u8>,
    input_consumed: usize,
    input_events: Vec<TraceInput>,
    io_events: Vec<BoundedRevisitIoEvent>,
    data_writes: Vec<BoundedRevisitDataWrite>,
    memory_words: u32,
    mutation_targets: Vec<u32>,
    profile_fingerprint: &'static str,
    profile_id: &'static str,
}

impl BoundedRevisitLayout {
    /// Exact admitted graphical guest source, without a capsule wrapper.
    #[must_use]
    pub fn source(&self) -> &[u8] {
        &self.source
    }

    /// Actual ordered code addresses, which may repeat.
    #[must_use]
    pub fn code_positions(&self) -> &[u32] {
        &self.code_positions
    }

    /// Actual data-pointer address at entry to each guest transition.
    #[must_use]
    pub fn data_positions(&self) -> &[u32] {
        &self.data_positions
    }

    /// Actual guest data-memory read addresses, absent on steps without a
    /// data-cell read. Unlike the data pointer, these are normative read
    /// events and can establish isolation of a future mutable state frame.
    #[must_use]
    pub fn data_read_positions(&self) -> &[Option<u32>] {
        &self.data_read_positions
    }

    /// Actual code-encryption addresses, or none on the halting step.
    #[must_use]
    pub fn encrypted_positions(&self) -> &[Option<u32>] {
        &self.encrypted_positions
    }

    /// Every reached `p`/`*` destination, even when the guest writes the
    /// word already present and the trace has no changed-value delta.
    #[must_use]
    pub fn mutation_targets(&self) -> &[u32] {
        &self.mutation_targets
    }

    /// Exactly the guest bytes committed before the observed halt.
    #[must_use]
    pub fn output(&self) -> &[u8] {
        &self.output
    }

    /// Successful input bytes actually consumed by the guest.
    #[must_use]
    pub const fn input_consumed(&self) -> usize {
        self.input_consumed
    }

    /// Exact committed guest reads, including EOF attempts without a byte.
    #[must_use]
    pub fn input_events(&self) -> &[TraceInput] {
        &self.input_events
    }

    /// Exact committed I/O order, including the step of each EOF attempt.
    #[must_use]
    pub fn io_events(&self) -> &[BoundedRevisitIoEvent] {
        &self.io_events
    }

    /// Actual guest data writes, distinct from automatic code encryption.
    #[must_use]
    pub fn data_writes(&self) -> &[BoundedRevisitDataWrite] {
        &self.data_writes
    }
}

/// A physical guest-memory interval reserved exclusively for data writes.
///
/// Ranges are half-open and use absolute target-word addresses. Callers must
/// submit intervals in increasing non-overlapping order; code is never data.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct BoundedGuestDataRegion {
    /// First unreserved address immediately after the data interval.
    pub end_exclusive: u32,
    /// Inclusive first reserved guest-memory word.
    pub start: u32,
}

/// A physical-path data footprint did not fit declared isolated reservations.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum BoundedGuestRegionsError {
    /// A reached instruction fetch or post-instruction encryption uses data.
    CodeDataCollision,
    /// Ranges are empty, unordered, overlapping, in code, outside the target,
    /// or exceed the finite interval/word ceilings.
    InvalidRegions,
    /// A reached mutating instruction targets an unreserved data word.
    UnreservedWrite,
    /// A reached helper data read or write touches a reserved state frame.
    StateDataAccessCollision,
    /// No full isolated state frame fits the verified target address space.
    NoStateFrameSpace,
}

/// Stable reason a bounded, input-specific nonlinear witness was not admitted.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum BoundedRevisitError {
    /// Exact canonical target-profile identity is inconsistent.
    ProfileMismatch,
    /// The raw graphical source is invalid or outside its finite bound.
    InvalidSource,
    /// The caller supplied no complete, resource-bounded path oracle.
    InvalidExpectation,
    /// The normative machine refuses to load this source under the profile.
    GuestLoad,
    /// A guest transition cannot commit successfully.
    GuestStep,
    /// The actual guest path differs from the supplied ordered path oracle.
    PathMismatch,
    /// Guest halts before the expected last step or fails to halt there.
    TerminationMismatch,
    /// The observed path has no repeated code address.
    NotRevisiting,
    /// Guest output differs from the independent output oracle.
    OutputMismatch,
    /// Guest input consumption differs from the independent oracle.
    InputConsumptionMismatch,
    /// Actual byte/EOF input attempts differ from the supplied event sequence.
    InputEventsMismatch,
    /// Guest I/O events occur in a different order or at different steps.
    IoEventsMismatch,
    /// Runtime guest data mutation differs from the independent oracle.
    DataWritesMismatch,
    /// A multi-input check needs 2..8 distinct input streams.
    InvalidBatch,
}

// Apply the same finite, source-external address rules to both physical
// helper scratch and the later C-state frame before examining guest traces.
fn validate_guest_regions(
    admitted: &BoundedRevisitLayout,
    regions: &[BoundedGuestDataRegion],
) -> Result<(), BoundedGuestRegionsError> {
    if regions.is_empty() || regions.len() > MAX_GUEST_DATA_REGIONS {
        return Err(BoundedGuestRegionsError::InvalidRegions);
    }
    let source_cells = u32::try_from(admitted.source.len())
        .map_err(|_error| BoundedGuestRegionsError::InvalidRegions)?;
    let mut last_end = source_cells;
    let mut reserved_words = u32::default();
    for region in regions {
        let words = region
            .end_exclusive
            .checked_sub(region.start)
            .filter(|words| *words > 0)
            .ok_or(BoundedGuestRegionsError::InvalidRegions)?;
        reserved_words = reserved_words
            .checked_add(words)
            .filter(|sum| *sum <= MAX_GUEST_RESERVED_WORDS)
            .ok_or(BoundedGuestRegionsError::InvalidRegions)?;
        if region.start < last_end
            || region.end_exclusive > admitted.memory_words
        {
            return Err(BoundedGuestRegionsError::InvalidRegions);
        }
        last_end = region.end_exclusive;
    }
    Ok(())
}

fn in_guest_regions(regions: &[BoundedGuestDataRegion], address: u32) -> bool {
    regions
        .iter()
        .any(|region| region.start <= address && address < region.end_exclusive)
}

/// Check isolated guest-data reservations against one *normative* path trace.
///
/// All actual data writes must lie inside the declared intervals (including
/// unchanged-value writes), and no executed/encrypted code may touch them.
/// This does not establish that a separate, future mutable C state frame is
/// safe from the helper's data *reads*: use
/// [`verify_bounded_guest_state_isolation`] for that distinct obligation.
///
/// # Errors
///
/// Refuses malformed/over-budget intervals, observed code/data collisions,
/// and any physical data write without an explicit reservation.
pub fn verify_bounded_guest_data_regions(
    admitted: &BoundedRevisitLayout,
    regions: &[BoundedGuestDataRegion],
) -> Result<(), BoundedGuestRegionsError> {
    validate_guest_regions(admitted, regions)?;
    let in_data = |address| in_guest_regions(regions, address);
    if admitted.code_positions.iter().copied().any(in_data)
        || admitted
            .encrypted_positions
            .iter()
            .flatten()
            .copied()
            .any(in_data)
    {
        return Err(BoundedGuestRegionsError::CodeDataCollision);
    }
    if admitted
        .mutation_targets
        .iter()
        .copied()
        .any(|address| !in_data(address))
        || admitted
            .data_writes
            .iter()
            .any(|write| !in_data(write.address))
    {
        return Err(BoundedGuestRegionsError::UnreservedWrite);
    }
    Ok(())
}

/// Check that a proposed mutable state frame is entirely untouched by this
/// independently admitted, complete helper path. Unlike the helper's own
/// scratch reservations, state words must not be read *or* written by helper
/// instructions: reading an initially harmless loader word would become a
/// mutable-state dependency once the C program updates that address.
///
/// The check uses real traced data reads, including `i`/`j` pointer reads,
/// not speculative accesses from the data-pointer register. It separately
/// rejects fetched/encrypted code and all mutating `p`/`*` destinations,
/// including idempotent writes. Only this one input/path is covered: a
/// complete compiler must repeat the check for every admitted path and prove
/// any subsequent guest code that intentionally accesses the state frame.
///
/// # Errors
///
/// Rejects invalid intervals, code/encryption collisions and any reached
/// physical helper data read or write inside a proposed mutable state frame.
pub fn verify_bounded_guest_state_isolation(
    admitted: &BoundedRevisitLayout,
    state_regions: &[BoundedGuestDataRegion],
) -> Result<(), BoundedGuestRegionsError> {
    validate_guest_regions(admitted, state_regions)?;
    let in_state = |address| in_guest_regions(state_regions, address);
    if admitted.code_positions.iter().copied().any(in_state)
        || admitted
            .encrypted_positions
            .iter()
            .flatten()
            .copied()
            .any(in_state)
    {
        return Err(BoundedGuestRegionsError::CodeDataCollision);
    }
    if admitted
        .data_read_positions
        .iter()
        .flatten()
        .copied()
        .any(in_state)
        || admitted.mutation_targets.iter().copied().any(in_state)
        || admitted
            .data_writes
            .iter()
            .any(|write| in_state(write.address))
    {
        return Err(BoundedGuestRegionsError::StateDataAccessCollision);
    }
    Ok(())
}

/// Find the lowest-addressed candidate frame that avoids the exact memory
/// access footprints of all supplied, independently admitted helper paths.
///
/// The search is finite and source-bound: it excludes every graphical source
/// cell and every observed fetch, encryption, data read and `p`/`*` write,
/// including unchanged-value writes. Only complete traces from the same
/// source and target geometry may be combined. Different inputs can take
/// different paths; the result is safe only for those supplied paths.
///
/// This produces an *uninitialized* frame reservation. It does not initialize
/// C variables, realize phi transfers, authorize new guest instructions, or
/// prove an unbounded EOF loop. A later linker must independently check all
/// executable operations and the final source bytes.
///
/// # Errors
///
/// Refuses absent or excessive path evidence, different source/target
/// identities, invalid frame widths, or exhaustion of N15 address space.
pub fn place_bounded_guest_state_frame(
    admitted: &[BoundedRevisitLayout],
    required_words: u32,
) -> Result<BoundedGuestDataRegion, BoundedGuestRegionsError> {
    if admitted.is_empty()
        || admitted.len() > MAX_REVISIT_CASES
        || required_words == 0
        || required_words > MAX_GUEST_RESERVED_WORDS
    {
        return Err(BoundedGuestRegionsError::InvalidRegions);
    }
    let first = &admitted[0];
    if admitted.iter().skip(1).any(|path| {
        path.source != first.source
            || path.memory_words != first.memory_words
            || path.profile_id != first.profile_id
            || path.profile_fingerprint != first.profile_fingerprint
    }) {
        return Err(BoundedGuestRegionsError::InvalidRegions);
    }
    let source_end = u32::try_from(first.source.len())
        .map_err(|_error| BoundedGuestRegionsError::InvalidRegions)?;
    let mut occupied = BTreeSet::new();
    for path in admitted {
        occupied.extend(path.code_positions.iter().copied());
        occupied.extend(path.encrypted_positions.iter().flatten().copied());
        occupied.extend(path.data_read_positions.iter().flatten().copied());
        occupied.extend(path.mutation_targets.iter().copied());
        occupied.extend(path.data_writes.iter().map(|write| write.address));
    }
    let end_for = |start: u32| {
        start
            .checked_add(required_words)
            .filter(|end| *end <= first.memory_words)
            .ok_or(BoundedGuestRegionsError::NoStateFrameSpace)
    };
    let mut start = source_end;
    for busy in occupied {
        if busy < start {
            continue;
        }
        if busy >= end_for(start)? {
            break;
        }
        start = busy
            .checked_add(1)
            .ok_or(BoundedGuestRegionsError::NoStateFrameSpace)?;
    }
    let frame = BoundedGuestDataRegion {
        start,
        end_exclusive: end_for(start)?,
    };
    for path in admitted {
        verify_bounded_guest_state_isolation(path, &[frame])?;
    }
    Ok(frame)
}

/// Admits only one *complete*, exact-profile, bounded path with a genuine
/// repeated code address. All guest effects and self-encryption run in the
/// normative VM, never a host-simulated substitute. The complete path,
/// output and consumed-input witnesses must agree exactly. A positive result
/// is input-specific and makes no claim about arbitrary stdin, C local state,
/// or general backward-branch synthesis.
///
/// # Errors
///
/// Refuses source/profile drift, malformed/budget-exceeding witnesses,
/// incomplete paths, transition failures, nonrevisiting control flow,
/// and independent output/input-event/input-consumption discrepancies.
pub fn admit_bounded_revisit_layout(
    profile: &'static ProfileDescriptor,
    source: &[u8],
    identity: LinearProfileIdentity<'_>,
    expected: BoundedRevisitExpectation<'_>,
) -> Result<BoundedRevisitLayout, BoundedRevisitError> {
    admit_bounded_guest_path_impl(profile, source, identity, expected, true)
}

/// Verify one complete finite guest path, including straight-line EOF arms.
///
/// Uses the same normative VM, exact source/profile binding, and independent
/// path, I/O and data-write oracles as the stricter revisiting entrypoint.
/// Unlike `admit_bounded_revisit_layout`, a genuine forward-only terminal
/// path is admitted; the caller must still provide every executed step.
/// This is input-specific evidence, not an arbitrary-input proof or linker.
///
/// # Errors
///
/// Rejects source/profile drift, incomplete or forged witnesses, transition
/// errors and every observable guest mismatch under the same finite budget.
pub fn admit_bounded_guest_path(
    profile: &'static ProfileDescriptor,
    source: &[u8],
    identity: LinearProfileIdentity<'_>,
    expected: BoundedRevisitExpectation<'_>,
) -> Result<BoundedRevisitLayout, BoundedRevisitError> {
    admit_bounded_guest_path_impl(profile, source, identity, expected, false)
}

fn admit_bounded_guest_path_impl(
    profile: &'static ProfileDescriptor,
    source: &[u8],
    identity: LinearProfileIdentity<'_>,
    expected: BoundedRevisitExpectation<'_>,
    require_revisit: bool,
) -> Result<BoundedRevisitLayout, BoundedRevisitError> {
    if identity.id != profile.id()
        || identity.fingerprint != profile.fingerprint()
    {
        return Err(BoundedRevisitError::ProfileMismatch);
    }
    if !(2..=MAX_REVISIT_SOURCE_CELLS).contains(&source.len())
        || source.iter().enumerate().any(|(position, &cell)| {
            !matches!(
                decode_profile_instruction(
                    u32::from(cell),
                    u32::try_from(position).unwrap_or(u32::MAX),
                ),
                Some(b'j' | b'i' | b'*' | b'p' | b'<' | b'/' | b'v' | b'o')
            )
        })
    {
        return Err(BoundedRevisitError::InvalidSource);
    }
    if expected.input.len() > MAX_REVISIT_STEPS
        || expected.code_positions.is_empty()
        || expected.code_positions.len() > MAX_REVISIT_STEPS
        || expected.output.len() > MAX_REVISIT_STEPS
        || expected.input_consumed > expected.input.len()
        || expected.input_events.len() > MAX_REVISIT_STEPS
        || expected.io_events.len() > expected.code_positions.len()
        || expected.data_writes.len() > expected.code_positions.len()
        || expected
            .io_events
            .windows(2)
            .any(|pair| pair[0].step >= pair[1].step)
        || expected.io_events.last().is_some_and(|event| {
            usize::try_from(event.step).unwrap_or(usize::MAX)
                >= expected.code_positions.len()
        })
        || expected
            .data_writes
            .windows(2)
            .any(|pair| pair[0].step >= pair[1].step)
        || expected.data_writes.last().is_some_and(|event| {
            usize::try_from(event.step).unwrap_or(usize::MAX)
                >= expected.code_positions.len()
        })
    {
        return Err(BoundedRevisitError::InvalidExpectation);
    }
    let mut machine =
        ProfileMachine::from_source(profile, source, expected.input.to_vec())
            .map_err(|_error| BoundedRevisitError::GuestLoad)?;
    let mut visited = BTreeSet::new();
    let mut revisited = false;
    let mut code_positions = Vec::with_capacity(expected.code_positions.len());
    let mut data_positions = Vec::with_capacity(expected.code_positions.len());
    let mut data_read_positions =
        Vec::with_capacity(expected.code_positions.len());
    let mut encrypted_positions =
        Vec::with_capacity(expected.code_positions.len());
    let mut input_events = Vec::with_capacity(expected.input_events.len());
    let mut io_events = Vec::with_capacity(expected.io_events.len());
    let mut data_writes = Vec::with_capacity(expected.data_writes.len());
    let mut mutation_targets = Vec::new();
    for (index, &code) in expected.code_positions.iter().enumerate() {
        let before = machine.registers();
        if before.code_pointer != code {
            return Err(BoundedRevisitError::PathMismatch);
        }
        if !visited.insert(code) {
            revisited = true;
        }
        let mut trace = None;
        let outcome = machine
            .step_traced(&mut |observed| trace = Some(*observed))
            .map_err(|_error| BoundedRevisitError::GuestStep)?;
        let observed = trace.ok_or(BoundedRevisitError::GuestStep)?;
        if observed.before.registers != before
            || observed.memory_reads.fetch.map(|read| read.address)
                != Some(code)
        {
            return Err(BoundedRevisitError::GuestStep);
        }
        if let Some(input_event) = observed.input {
            input_events.push(input_event);
            io_events.push(BoundedRevisitIoEvent {
                step: u32::try_from(index).unwrap_or(u32::MAX),
                effect: BoundedRevisitIoEffect::Input(input_event),
            });
        }
        if let Some(output_byte) = observed.output {
            io_events.push(BoundedRevisitIoEvent {
                step: u32::try_from(index).unwrap_or(u32::MAX),
                effect: BoundedRevisitIoEffect::Output(output_byte),
            });
        }
        // The VM's memory delta excludes idempotent writes, so preserve the
        // decoded mutating instruction's operand address separately.
        if matches!(observed.decoded, Some(b'p' | b'*')) {
            mutation_targets.push(before.data_pointer);
        }
        if let Some(data) = observed.memory_delta.data {
            data_writes.push(BoundedRevisitDataWrite {
                step: u32::try_from(index).unwrap_or(u32::MAX),
                address: data.address,
                before: data.before,
                after: data.after,
            });
        }
        code_positions.push(code);
        data_positions.push(before.data_pointer);
        data_read_positions
            .push(observed.memory_reads.data.map(|read| read.address));
        encrypted_positions.push(
            observed
                .memory_delta
                .encryption
                .map(|change| change.address),
        );
        let is_last = index + 1 == expected.code_positions.len();
        match outcome {
            StepOutcome::Continued if !is_last => {},
            StepOutcome::Terminated(Termination::HaltInstruction)
                if is_last => {},
            _ => return Err(BoundedRevisitError::TerminationMismatch),
        }
    }
    if require_revisit && !revisited {
        return Err(BoundedRevisitError::NotRevisiting);
    }
    if machine.output() != expected.output {
        return Err(BoundedRevisitError::OutputMismatch);
    }
    if machine.input_consumed() != expected.input_consumed {
        return Err(BoundedRevisitError::InputConsumptionMismatch);
    }
    if input_events != expected.input_events {
        return Err(BoundedRevisitError::InputEventsMismatch);
    }
    if io_events != expected.io_events {
        return Err(BoundedRevisitError::IoEventsMismatch);
    }
    if data_writes != expected.data_writes {
        return Err(BoundedRevisitError::DataWritesMismatch);
    }
    Ok(BoundedRevisitLayout {
        source: source.to_vec(),
        code_positions,
        data_positions,
        data_read_positions,
        encrypted_positions,
        output: machine.output().to_vec(),
        input_consumed: machine.input_consumed(),
        input_events,
        io_events,
        data_writes,
        memory_words: profile.memory_words(),
        mutation_targets,
        profile_fingerprint: profile.fingerprint(),
        profile_id: profile.id(),
    })
}

/// Recheck a *single* graphical guest source against several independent,
/// distinct binary input/path/effect oracles. Each input reinitializes and
/// executes the real profile VM. No case inherits output or control evidence
/// from another; this finite matrix makes no claim about all possible inputs.
///
/// # Errors
///
/// Refuses an empty, singleton, oversized or repeated-input matrix, or the
/// first individually unsupported execution. No partial matrix is returned.
pub fn admit_bounded_revisit_batch(
    profile: &'static ProfileDescriptor,
    source: &[u8],
    identity: LinearProfileIdentity<'_>,
    expected: &[BoundedRevisitExpectation<'_>],
) -> Result<Vec<BoundedRevisitLayout>, BoundedRevisitError> {
    admit_bounded_batch_impl(profile, source, identity, expected, true)
}

/// Admit a finite set of distinct binary streams with complete guest oracles.
///
/// Unlike the revisiting-only batch, this also admits a forward-only EOF arm
/// alongside revisiting byte paths.
///
/// Each path is executed independently under the same source/profile with a
/// fresh normative guest machine.
///
/// A successful batch proves only the supplied finite streams, not arbitrary
/// input, general branching or source-C parity.
///
/// # Errors
///
/// Refuses a singleton, duplicate or over-budget matrix and propagates the
/// first failing individual normative guest path admission without publishing
/// partial results.
pub fn admit_bounded_guest_path_batch(
    profile: &'static ProfileDescriptor,
    source: &[u8],
    identity: LinearProfileIdentity<'_>,
    expected: &[BoundedRevisitExpectation<'_>],
) -> Result<Vec<BoundedRevisitLayout>, BoundedRevisitError> {
    admit_bounded_batch_impl(profile, source, identity, expected, false)
}

#[expect(
    clippy::too_many_arguments,
    reason = "shared internal gate retains the public batch inputs and mode"
)]
fn admit_bounded_batch_impl(
    profile: &'static ProfileDescriptor,
    source: &[u8],
    identity: LinearProfileIdentity<'_>,
    expected: &[BoundedRevisitExpectation<'_>],
    require_revisit: bool,
) -> Result<Vec<BoundedRevisitLayout>, BoundedRevisitError> {
    if !(2..=MAX_REVISIT_CASES).contains(&expected.len()) {
        return Err(BoundedRevisitError::InvalidBatch);
    }
    let mut inputs = BTreeSet::new();
    if expected.iter().any(|case| !inputs.insert(case.input)) {
        return Err(BoundedRevisitError::InvalidBatch);
    }
    let mut admitted = Vec::with_capacity(expected.len());
    for case in expected {
        admitted.push(admit_bounded_guest_path_impl(
            profile,
            source,
            identity,
            *case,
            require_revisit,
        )?);
    }
    Ok(admitted)
}
