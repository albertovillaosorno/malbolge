// Copyright:
//   - Copyright © 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - Apache-2.0
// Confidential:
//   - false
// License-File:
//   - LICENSE
// Boundary-Contract:
// - Owns:
//   - Finite source parity arm and factored physical transition correspondence.
// - Must-Not:
//   - Authorize the complete SSA frame or relax publication limits.
// - Allows:
//   - Inputs: canonical loop bindings, table geometry, actual normative trace.
//   - Outputs: selected source arm and ordered physical transition receipts.
// - Split-When:
//   - Source control or physical table verification needs another shape.
// - Merge-When:
//   - Full source-frame verification owns recurrent transition semantics.
// - Summary:
//   - Tie the selected source parity and next state to actual table effects.

//! Authenticate a factored byte transition between paired loop reads.

#[path = "source_recurrent_transition_trace.rs"]
mod source_recurrent_transition_trace;

use malbolge::TraceInput;
pub(super) use source_recurrent_transition_trace::TransitionTrace;

use super::super::super::typed_cfg_adapter::ternary::TernaryCfgBlock;
use super::source_recurrent_loop::{compatible, pair_checkpoints};
use super::{
    Effect, Error, GuardPlan, ProjectedIo, ProjectionPlans, ReplayAudits,
    SourceInputWalkState, SourceRecurrentLoopProbe, SourceRecurrentLoopProof,
    StatePlan, TernaryCfgFunction, TernaryCfgScalarKind, TernaryCfgTerminator,
    TernaryOperation, admit_probe, project_function_with_plans, replay_guest,
};

/// Physical factored transition geometry for the paired source loop.
#[derive(Clone, Copy, Debug)]
pub struct SourceRecurrentTransitionProbe<'source> {
    /// Shared physical final crazy store to the low or high carried word.
    pub commit_address: u32,
    /// Crazy-site pairs: raw low, carry, raw high, high result, low result.
    pub lookup: [[u32; 2]; 5],
    /// Same signed guard and unsigned carried-state replay.
    pub loop_probe: SourceRecurrentLoopProbe<'source>,
    /// Record banks in raw-low, low, raw-high and high order.
    pub seeds: [u32; 4],
    /// Index tables in raw-low, low, raw-high and high order.
    pub tables: [u32; 4],
}

/// Actual source and physical effects for one successful byte.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct SourceRecurrentTransitionCheckpoint {
    /// Canonical selected arm's SSA result.
    pub arm_result: u32,
    /// Actual selected arm value before adding three and masking.
    pub arm_value: u32,
    /// Independently derived carry from the low-nibble transition.
    pub carry: u32,
    /// Final low and high stores, in state-word order.
    pub commit_indices: [usize; 2],
    /// Canonical parity predicate SSA identity.
    pub condition: u32,
    /// Actual input index starting the transition.
    pub input_index: usize,
    /// All indexed jumps and immutable pair reads in chronological order.
    pub lookup_indices: Vec<usize>,
    /// Actual subsequent read after both committed state stores.
    pub next_input_index: usize,
    /// Independently evaluated next state.
    pub next_state: u8,
    /// Actual selected parity, zero for addition and one for XOR.
    pub parity: u32,
    /// Independently evaluated state before the read.
    pub prior_state: u8,
    /// The successful source and physical input byte.
    pub raw_byte: u8,
    /// Canonical source parity block.
    pub source_block: u32,
    /// Actual selected source successor.
    pub source_target: u32,
}

/// Finite paired loop proof with the ordered factored byte transitions.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct SourceRecurrentTransitionProof {
    /// Signed/unsigned bindings and one complete I/O and halt receipt.
    pub loop_proof: SourceRecurrentLoopProof,
    /// One actual transition for each successful input; no transition at EOF.
    pub transitions: Vec<SourceRecurrentTransitionCheckpoint>,
}

#[derive(Clone, Copy)]
pub(super) struct SourceTransitionValue {
    arm_checked: bool,
    arm_result: u32,
    arm_value: u32,
    condition: u32,
    next_state: u8,
    parity: u32,
    prior_state: u8,
    raw_byte: u8,
    source_block: u32,
    source_target: u32,
}

#[derive(Clone, Copy)]
struct Arm {
    block: u32,
    merge: u32,
    result: u32,
}

pub(super) struct ParityPlan {
    add: Arm,
    block: u32,
    condition: u32,
    signed_phi: u32,
    unsigned_phi: u32,
    xor: Arm,
}

impl ParityPlan {
    pub(super) fn checkpoint(
        &self,
        state: &SourceInputWalkState,
        target: u32,
        events: &mut [ProjectedIo],
    ) -> Result<(), Error> {
        if state.block == self.block {
            return self.select(state, target, events);
        }
        if [self.add.block, self.xor.block].contains(&state.block) {
            let value = events
                .last_mut()
                .and_then(|event| event.transition.as_mut())
                .ok_or(Error::InvalidTransitionBinding)?;
            if value.arm_checked
                || value.source_target != state.block
                || target != self.add.merge
                || state.known.get(&value.arm_result) != Some(&value.arm_value)
            {
                return Err(Error::InvalidTransitionBinding);
            }
            value.arm_checked = true;
        }
        Ok(())
    }

    pub(super) fn finish(events: &[ProjectedIo]) -> Result<(), Error> {
        for (index, event) in events.iter().enumerate() {
            let successful =
                matches!(event.effect, Effect::Input(TraceInput::Byte(_)));
            if successful != event.transition.is_some() {
                return Err(Error::InvalidTransitionBinding);
            }
            if let Some(value) = event.transition {
                let next = events
                    .get(index.saturating_add(1))
                    .ok_or(Error::InvalidTransitionBinding)?;
                validate_source_transition(value, next)?;
            }
        }
        Ok(())
    }

    fn new(
        function: &TernaryCfgFunction,
        loop_probe: &SourceRecurrentLoopProbe<'_>,
        signed_phi: u32,
    ) -> Result<Self, Error> {
        let header = block(function, loop_probe.guard.source_header)?;
        let TernaryCfgTerminator::Branch { true_target, .. } =
            header.terminator
        else {
            return Err(Error::InvalidTransitionBinding);
        };
        let parity = block(function, true_target)?;
        let condition = parity_condition(function, parity, signed_phi)?;
        let TernaryCfgTerminator::Branch {
            false_target,
            true_target: odd,
            ..
        } = parity.terminator
        else {
            return Err(Error::InvalidTransitionBinding);
        };
        let unsigned_phi = loop_probe.state.phi_result;
        let add = source_arm(
            block(function, false_target)?,
            signed_phi,
            unsigned_phi,
            false,
        )?;
        let xor =
            source_arm(block(function, odd)?, signed_phi, unsigned_phi, true)?;
        if add.merge != xor.merge || add.block == xor.block {
            return Err(Error::InvalidTransitionBinding);
        }
        validate_backedge(function, header, unsigned_phi, [add, xor])?;
        Ok(Self {
            add,
            block: parity.id,
            condition,
            signed_phi,
            unsigned_phi,
            xor,
        })
    }

    fn select(
        &self,
        state: &SourceInputWalkState,
        target: u32,
        events: &mut [ProjectedIo],
    ) -> Result<(), Error> {
        let event = events.last_mut().ok_or(Error::InvalidTransitionBinding)?;
        let Effect::Input(TraceInput::Byte(raw_byte)) = event.effect else {
            return Err(Error::InvalidTransitionBinding);
        };
        let prior = event.state.ok_or(Error::InvalidTransitionBinding)?.value;
        let parity = u32::from(raw_byte & 1);
        let arm = if parity == 0 {
            self.add
        } else {
            self.xor
        };
        if event.transition.is_some()
            || event.guard.is_none()
            || state.known.get(&self.signed_phi) != Some(&u32::from(raw_byte))
            || state.known.get(&self.unsigned_phi) != Some(&u32::from(prior))
            || state.known.get(&self.condition) != Some(&parity)
            || target != arm.block
        {
            return Err(Error::InvalidTransitionBinding);
        }
        let arm_value = if parity == 0 {
            u32::from(prior).saturating_add(u32::from(raw_byte))
        } else {
            u32::from(prior ^ raw_byte)
        };
        let next_state = u8::try_from(arm_value.saturating_add(3) & 255)
            .map_err(|_error| Error::InvalidTransitionBinding)?;
        event.transition = Some(SourceTransitionValue {
            arm_checked: false,
            arm_result: arm.result,
            arm_value,
            condition: self.condition,
            next_state,
            parity,
            prior_state: prior,
            raw_byte,
            source_block: self.block,
            source_target: target,
        });
        Ok(())
    }
}

fn block(
    function: &TernaryCfgFunction,
    id: u32,
) -> Result<&TernaryCfgBlock, Error> {
    function
        .blocks
        .iter()
        .find(|candidate| candidate.id == id)
        .ok_or(Error::InvalidTransitionBinding)
}

fn literal(
    function: &TernaryCfgFunction,
    result_id: u32,
    bits: u32,
    signed: bool,
) -> bool {
    function
        .blocks
        .iter()
        .flat_map(|candidate| &candidate.operations)
        .any(|operation| {
            let signed_match = matches!(
                *operation,
                TernaryOperation::MaterializeI32 { result, scalar, .. }
                    if result == result_id && scalar.bits() == bits
            );
            let unsigned_match = matches!(
                *operation,
                TernaryOperation::MaterializeU32 { result, scalar, .. }
                    if result == result_id && scalar.bits() == bits
            );
            (signed && signed_match) || (!signed && unsigned_match)
        })
}

fn parity_condition(
    function: &TernaryCfgFunction,
    parity: &TernaryCfgBlock,
    signed_phi: u32,
) -> Result<u32, Error> {
    let [
        TernaryOperation::AndI32 { left, right, result, .. },
        TernaryOperation::NotEqualI32 {
            left: tested,
            right: zero,
            result: condition,
            ..
        },
    ] = parity.operations.as_slice()
    else {
        return Err(Error::InvalidTransitionBinding);
    };
    if *left != signed_phi
        || tested != result
        || !literal(function, *right, 1, true)
        || !literal(function, *zero, 0, true)
        || !matches!(
            parity.terminator,
            TernaryCfgTerminator::Branch { condition: id, .. }
                if id == *condition
        )
    {
        return Err(Error::InvalidTransitionBinding);
    }
    Ok(*condition)
}

fn source_arm(
    arm: &TernaryCfgBlock,
    signed_phi: u32,
    unsigned_phi: u32,
    odd: bool,
) -> Result<Arm, Error> {
    let [
        TernaryOperation::BitcastI32ToU32 { value, result: cast, .. },
        arithmetic,
    ] = arm.operations.as_slice()
    else {
        return Err(Error::InvalidTransitionBinding);
    };
    let (left, right, result) = if odd {
        let TernaryOperation::XorU32 { left, right, result, .. } = *arithmetic
        else {
            return Err(Error::InvalidTransitionBinding);
        };
        (left, right, result)
    } else {
        let TernaryOperation::AddU32 { left, right, result, .. } = *arithmetic
        else {
            return Err(Error::InvalidTransitionBinding);
        };
        (left, right, result)
    };
    let TernaryCfgTerminator::Jump { target, .. } = arm.terminator else {
        return Err(Error::InvalidTransitionBinding);
    };
    if *value != signed_phi || left != unsigned_phi || right != *cast {
        return Err(Error::InvalidTransitionBinding);
    }
    Ok(Arm {
        block: arm.id,
        merge: target,
        result,
    })
}

fn validate_source_transition(
    value: SourceTransitionValue,
    next: &ProjectedIo,
) -> Result<(), Error> {
    if !value.arm_checked
        || !matches!(next.effect, Effect::Input(_))
        || next.state.map(|state| state.value) != Some(value.next_state)
    {
        return Err(Error::InvalidTransitionBinding);
    }
    Ok(())
}

fn validate_backedge(
    function: &TernaryCfgFunction,
    header: &TernaryCfgBlock,
    unsigned_phi: u32,
    [add, xor]: [Arm; 2],
) -> Result<(), Error> {
    let backedge = block(function, add.merge)?;
    let [merged] = backedge.phis.as_slice() else {
        return Err(Error::InvalidTransitionBinding);
    };
    let [
        TernaryOperation::AddU32 {
            left,
            right: three,
            result: sum,
            ..
        },
        TernaryOperation::AndU32 {
            left: masked,
            right: mask,
            result: update,
            ..
        },
        TernaryOperation::GetcharI32 { .. },
    ] = backedge.operations.as_slice()
    else {
        return Err(Error::InvalidTransitionBinding);
    };
    if merged.type_kind != TernaryCfgScalarKind::U32
        || merged.incoming.as_slice()
            != [(xor.block, xor.result), (add.block, add.result)]
        || *left != merged.result
        || masked != sum
        || !literal(function, *three, 3, false)
        || !literal(function, *mask, 255, false)
        || !matches!(
            backedge.terminator,
            TernaryCfgTerminator::Jump { target, .. }
                if target == header.id
        )
        || !header.phis.iter().any(|phi| {
            phi.result == unsigned_phi
                && phi.incoming.contains(&(backedge.id, *update))
        })
    {
        return Err(Error::InvalidTransitionBinding);
    }
    Ok(())
}

fn verify_pairs(
    loop_proof: &SourceRecurrentLoopProof,
    transitions: &[SourceRecurrentTransitionCheckpoint],
) -> Result<(), Error> {
    if transitions.len() != loop_proof.io.bytes_consumed
        || loop_proof.checkpoints.len() != transitions.len().saturating_add(1)
    {
        return Err(Error::GuestTransitionMismatch);
    }
    for (pair, transition) in loop_proof.checkpoints.windows(2).zip(transitions)
    {
        let [prior, next] = pair else {
            return Err(Error::GuestTransitionMismatch);
        };
        if prior.guard.input_index != transition.input_index
            || prior.guard.signed_bits != u32::from(transition.raw_byte)
            || prior.state.value != transition.prior_state
            || next.state.value != transition.next_state
            || next.state.trace_index != transition.next_input_index
            || next.state.write_indices != transition.commit_indices
            || transition
                .lookup_indices
                .first()
                .is_none_or(|first| *first <= prior.guard.guard_index)
        {
            return Err(Error::GuestTransitionMismatch);
        }
    }
    Ok(())
}

/// Bind the canonical successful-byte parity branch and arithmetic arms to
/// the actual factored lookup and commit sequence in the shared loop replay.
///
/// This is a finite witness, not complete SSA storage or publication authority.
///
/// # Errors
/// Refuses incompatible loop probes, nonmatching source operations, missing,
/// mutated or out-of-order indexed effects and incorrect carried-state commits.
pub fn verify_source_recurrent_transition(
    probe: &SourceRecurrentTransitionProbe<'_>,
) -> Result<SourceRecurrentTransitionProof, Error> {
    let loop_probe = &probe.loop_probe;
    compatible(loop_probe)?;
    let io = loop_probe.guard.io;
    let cfg = admit_probe(io)?;
    let [function] = cfg.functions.as_slice() else {
        return Err(Error::UnsupportedSourceExecution);
    };
    let guard_plan = GuardPlan::new(function, loop_probe.guard.source_header)?;
    let state_plan = StatePlan::new(function, &loop_probe.state)?;
    let parity_plan = ParityPlan::new(function, loop_probe, guard_plan.phi)?;
    let projected =
        project_function_with_plans(function, io.input, &ProjectionPlans {
            guard: Some(&guard_plan),
            state: Some(&state_plan),
            transition: Some(&parity_plan),
        })?;
    let replay =
        replay_guest(io, &projected, cfg.source_sha256, &ReplayAudits {
            guard: Some(&loop_probe.guard),
            state: Some(&loop_probe.state),
            transition: Some(probe),
        })?;
    let guard = replay.guard.ok_or(Error::InvalidLoopBinding)?;
    let state = replay.state.ok_or(Error::InvalidLoopBinding)?;
    let transition =
        replay.transition.ok_or(Error::InvalidTransitionBinding)?;
    let checkpoints =
        pair_checkpoints(guard.checkpoints, state.checkpoints, &replay.io)?;
    let loop_proof = SourceRecurrentLoopProof {
        checkpoints,
        io: replay.io,
        loop_header: loop_probe.guard.source_header,
        signed_phi: guard_plan.phi,
        unsigned_phi: loop_probe.state.phi_result,
        word_addresses: loop_probe.state.words,
    };
    verify_pairs(&loop_proof, &transition.checkpoints)?;
    Ok(SourceRecurrentTransitionProof {
        loop_proof,
        transitions: transition.checkpoints,
    })
}

#[cfg(test)]
#[path = "../../../../tests/compiler/source_recurrent_transition.rs"]
mod source_recurrent_transition_tests;
