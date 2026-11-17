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
//   - Bounded exact-profile admission of source paths revisiting code cells.
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
//   - Admits finite backward-jump witnesses including re-encrypted code.
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
    ProfileDescriptor, ProfileMachine, StepOutcome, Termination,
    decode_profile_instruction,
};

use super::LinearProfileIdentity;

/// Hard limit for a source candidate at this independent nonlinear boundary.
pub const MAX_REVISIT_SOURCE_CELLS: usize = 4096;
/// Hard limit for one supplied complete execution-path witness.
pub const MAX_REVISIT_STEPS: usize = 512;

/// One complete, input-specific oracle: source visits, output and input reads.
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
}

/// An admitted, input-specific guest path with at least one revisited cell.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct BoundedRevisitLayout {
    source: Vec<u8>,
    code_positions: Vec<u32>,
    data_positions: Vec<u32>,
    encrypted_positions: Vec<Option<u32>>,
    output: Vec<u8>,
    input_consumed: usize,
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

    /// Actual code-encryption addresses, or none on the halting step.
    #[must_use]
    pub fn encrypted_positions(&self) -> &[Option<u32>] {
        &self.encrypted_positions
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
/// and independent output/input-consumption discrepancies.
pub fn admit_bounded_revisit_layout(
    profile: &'static ProfileDescriptor,
    source: &[u8],
    identity: LinearProfileIdentity<'_>,
    expected: BoundedRevisitExpectation<'_>,
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
    let mut encrypted_positions =
        Vec::with_capacity(expected.code_positions.len());
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
        code_positions.push(code);
        data_positions.push(before.data_pointer);
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
    if !revisited {
        return Err(BoundedRevisitError::NotRevisiting);
    }
    if machine.output() != expected.output {
        return Err(BoundedRevisitError::OutputMismatch);
    }
    if machine.input_consumed() != expected.input_consumed {
        return Err(BoundedRevisitError::InputConsumptionMismatch);
    }
    Ok(BoundedRevisitLayout {
        source: source.to_vec(),
        code_positions,
        data_positions,
        encrypted_positions,
        output: machine.output().to_vec(),
        input_consumed: machine.input_consumed(),
    })
}
