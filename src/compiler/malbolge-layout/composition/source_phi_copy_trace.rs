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
//   - Necessary physical source-SSA and two-phase phi copy observations.
// - Must-Not:
//   - Claim source branch selection, full arithmetic or a linked C program.
// - Allows:
//   - Inputs: source-locked code placement and finite normative guest trace.
//   - Outputs: actual ordered p/* word-copy evidence and explicit refusals.
//   - Side effects: isolated, bounded current-profile VM execution.
// - Split-When:
//   - A complete source-guest CFG validator subsumes phi copy checking.
// - Merge-When:
//   - Physical source frame tracing checks all operand reads and control.
// - Summary:
//   - Phi snapshots and commits must preserve guest-written SSA values.

//! Necessary physical evidence for source-placed, two-phase phi transfers.
//!
//! An address-reserved `p` or `*` is not a copy merely because it writes a
//! source frame. For every reached snapshot and commit the *actual* VM word
//! must equal the most recent earlier physical source-placed write to its
//! declared source cell. The check does not prove that the instruction read
//! that cell, selected the correct CFG edge or returned source-C results.

use std::collections::BTreeMap;

use malbolge::{
    ProfileMachine, ProfileStepTrace, RunOutcome, Termination, current_profile,
};

use super::typed_cfg_adapter::state_relocation::{
    GuestAddressedCfgPlan, GuestCodeBlockPlacement, GuestCodeControlEdge,
    GuestCodeEdgeKind, GuestCodeEffectAnchor, GuestCodeFunctionEntry,
    GuestCodeOperationAnchor, GuestCodeOperationEffect,
    GuestCodeOperationEffectSite, GuestCodePhiCopyAnchor,
    GuestCodePhiCopyPlacement, GuestCodeProposals, GuestCodeReturnSite,
    GuestPlacedCellCopy,
    bind_source_locked_cfg_code_targets_with_phi_copy_anchors,
};
use super::typed_cfg_adapter::state_storage::GuestFramePlacement;
use super::typed_cfg_adapter::ternary::TernaryCfgScalarKind;

/// Maximum source size for one isolated phi-copy guest witness.
pub const MAX_SOURCE_PHI_TRACE_CELLS: usize = 4096;
/// Maximum committed guest steps for one isolated phi-copy witness.
pub const MAX_SOURCE_PHI_TRACE_STEPS: usize = 512;

/// A physical phi-copy check can refuse without creating an executable C
/// artifact.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum SourcePhiCopyTraceError {
    /// Source, stream or run ceiling exceeded the finite guest study bounds.
    InvalidBound,
    /// A reached source block was entered from an unplaced site or mid-body.
    InvalidBlockEntry,
    /// A reached branch chose an arm inconsistent with its guest Boolean.
    InvalidBranchSelection,
    /// A reached block escaped without a source-placed control edge.
    InvalidControlTransfer,
    /// The actual VM halt did not occur in a source return control suffix.
    InvalidSourceReturn,
    /// Normative VM did not execute a complete, valid bounded guest run.
    InvalidGuestExecution,
    /// A reached phi site did not write the declared destination/value.
    InvalidPhiCopy,
    /// A phi pad was entered without the source predecessor control path.
    InvalidPhiEntry,
    /// A reached phi site was absent, reordered or left mid-transfer.
    InvalidPhiOrder,
    /// A finished phi pad did not physically jump to its source successor.
    InvalidPhiTransfer,
    /// Canonical source and proposed code/SSA placement do not agree.
    InvalidSourcePlacement,
    /// A source-block visit used an incompatible physical effect opcode.
    InvalidBlockEffect,
    /// A source-block visit skipped or reordered a required effect cell.
    MissingBlockEffect,
    /// An effect site executed twice without a new source-block visit.
    RepeatedBlockEffect,
    /// A reached output operand has no earlier guest-authenticated frame write.
    MissingOutputMaterialization,
    /// A real output is not the exact materialized typed U8 source operand.
    InvalidOutputValue,
    /// A reached branch did not materialize its Boolean before departure.
    MissingBranchCondition,
    /// A copy source had no earlier, actual source-placed guest data write.
    MissingSourceMaterialization,
    /// No physical source-placed phi snapshot or commit was reached.
    NoReachedPhiCopy,
    /// A real guest input/output executed outside its source operation site.
    UnexpectedSourceIo,
    /// A frame write or code mutation had no source-placed authorization.
    UnexpectedFrameEffect,
}

/// One physically executed phi copy, not a host-produced state assignment.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct SourcePhiCopyObservation {
    /// Actual guest code position of the reached p/*.
    pub code_address: u32,
    /// Authenticated destination memory cell written.
    pub destination: u32,
    /// Authenticated source/temporary memory cell copied from.
    pub source: u32,
    /// Zero-based bounded VM transition index.
    pub trace_index: usize,
    /// Actual word written by the normative VM.
    pub word: u32,
}

/// Exact reached snapshot/commit observations from a bounded guest run.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct SourcePhiCopyProof {
    /// Number of complete two-phase physical pads observed.
    pub completed_pads: usize,
    /// One record per physical phi copy, in VM transition order.
    pub copies: Vec<SourcePhiCopyObservation>,
}

/// A finite, source-locked physical guest phi-copy proof request.
///
/// All source and code proposals are untrusted until the source placement
/// verifier rederives their CFG, frame widths, op sites and edge-local pads.
#[derive(Clone, Copy, Debug)]
pub struct SourcePhiCopyProbe<'source> {
    /// Canonical authenticated typed wire, not an arbitrary source CFG.
    pub canonical: &'source [u8],
    /// Explicit anchors for required source operation effects.
    pub effect_anchors: &'source [GuestCodeEffectAnchor],
    /// Base of the disjoint guest source-state frame reservations.
    pub frame_base: u32,
    /// Complete finite binary guest stdin stream.
    pub input: &'source [u8],
    /// Source-authenticated canonical operation start anchors.
    pub operation_anchors: &'source [GuestCodeOperationAnchor],
    /// Actual graphical bytes to execute in the normative current-profile VM.
    pub physical_source: &'source [u8],
    /// Untrusted physical source block and phi-pad placement proposals.
    pub proposals: GuestCodeProposals<'source>,
    /// Exact positive guest step ceiling.
    pub step_budget: usize,
}

#[derive(Clone, Copy, Eq, PartialEq)]
enum PhiTransferPolicy {
    AllEdges,
    CopyOnly,
    Exit,
    Ingress,
}

#[derive(Clone, Copy)]
struct CopySite {
    copy: GuestPlacedCellCopy,
    edge_index: usize,
    ordinal: usize,
}

type PhiCopySites = BTreeMap<u32, CopySite>;
type SourceStoreSites = BTreeMap<(u32, u32), Option<u32>>;

#[derive(Clone, Copy)]
struct PhiTraceContext<'source> {
    edges: &'source [GuestCodeControlEdge],
    effects: &'source [GuestCodeOperationEffectSite],
    frames: &'source [GuestFramePlacement],
}

#[derive(Default)]
struct PhiTraceProgress {
    active_pad: Option<usize>,
    completed_pads: usize,
    completed_visit: bool,
    copies: Vec<SourcePhiCopyObservation>,
    materialized: BTreeMap<u32, u32>,
    pending_transfers: Vec<bool>,
    progress: Vec<usize>,
}

impl PhiTraceProgress {
    fn check_interleaving(
        &self,
        code_address: u32,
        edges: &[GuestCodeControlEdge],
        sites: &PhiCopySites,
    ) -> Result<(), SourcePhiCopyTraceError> {
        // After a snapshot, permit setup instructions *inside that pad*
        // before the next required copy. A jump outside, another pad's
        // copy or a premature exit may never silently complete a transfer.
        // Frame writes in the gaps are checked separately below.
        if self.progress.iter().enumerate().any(|(index, at)| {
            if *at == 0 {
                return false;
            }
            let Some(edge) = edges.get(index) else {
                return true;
            };
            !edge.pad_exit_address.is_some_and(|exit| {
                (edge.entry_address..exit).contains(&code_address)
            }) || sites.get(&code_address).is_some_and(|site| {
                site.edge_index != index || site.ordinal != *at
            })
        }) {
            return Err(SourcePhiCopyTraceError::InvalidPhiOrder);
        }
        Ok(())
    }

    // A completed copy elsewhere must not authorize a later pad visit that
    // executes no copies at all. Track every physical pad entry independently
    // of the partial-copy order already checked by `check_interleaving`.
    fn check_pad_visit(
        &mut self,
        code_address: u32,
        edges: &[GuestCodeControlEdge],
    ) -> Result<(), SourcePhiCopyTraceError> {
        let current = edges.iter().position(|edge| {
            edge.pad_exit_address.is_some_and(|exit| {
                (edge.entry_address..=exit).contains(&code_address)
            })
        });
        if current != self.active_pad {
            if self.active_pad.is_some() && !self.completed_visit {
                return Err(SourcePhiCopyTraceError::InvalidPhiOrder);
            }
            self.active_pad = current;
            self.completed_visit = false;
        }
        Ok(())
    }

    fn check_pending_transfers(
        &mut self,
        step: &ProfileStepTrace,
        edges: &[GuestCodeControlEdge],
        sites: &PhiCopySites,
    ) -> Result<(), SourcePhiCopyTraceError> {
        let code = step.before.registers.code_pointer;
        for (index, pending) in self.pending_transfers.iter_mut().enumerate() {
            if !*pending {
                continue;
            }
            let edge = edges
                .get(index)
                .ok_or(SourcePhiCopyTraceError::InvalidSourcePlacement)?;
            let exit = edge
                .pad_exit_address
                .ok_or(SourcePhiCopyTraceError::InvalidSourcePlacement)?;
            if code == exit
                && (step.decoded != Some(b'i')
                    || step.after.registers.code_pointer != edge.target_address)
            {
                return Err(SourcePhiCopyTraceError::InvalidPhiTransfer);
            }
            if code == exit {
                *pending = false;
                continue;
            }
            if !(edge.entry_address..exit).contains(&code)
                || sites.contains_key(&code)
            {
                // Setup may remain inside the pad, but a second copy or
                // an escape before the reserved exit is not a transfer.
                return Err(SourcePhiCopyTraceError::InvalidPhiTransfer);
            }
        }
        Ok(())
    }

    fn new(edges: &[GuestCodeControlEdge]) -> Self {
        Self {
            pending_transfers: vec![false; edges.len()],
            progress: vec![0; edges.len()],
            ..Self::default()
        }
    }

    #[expect(
        clippy::too_many_arguments,
        reason = "one copy requires exact guest step and source edge"
    )]
    fn record_copy(
        &mut self,
        site: CopySite,
        edge: &GuestCodeControlEdge,
        step: &ProfileStepTrace,
        trace_index: usize,
        require_transfer: bool,
    ) -> Result<(), SourcePhiCopyTraceError> {
        let progress_at = self
            .progress
            .get_mut(site.edge_index)
            .ok_or(SourcePhiCopyTraceError::InvalidSourcePlacement)?;
        if *progress_at != site.ordinal
            || (require_transfer
                && (self.active_pad != Some(site.edge_index)
                    || self.completed_visit))
        {
            return Err(SourcePhiCopyTraceError::InvalidPhiOrder);
        }
        if !matches!(step.decoded, Some(b'p' | b'*'))
            || step.before.registers.data_pointer != site.copy.destination
        {
            return Err(SourcePhiCopyTraceError::InvalidPhiCopy);
        }
        let expected = self
            .materialized
            .get(&site.copy.source)
            .ok_or(SourcePhiCopyTraceError::MissingSourceMaterialization)?;
        let word = step.after.registers.accumulator;
        if word != *expected {
            return Err(SourcePhiCopyTraceError::InvalidPhiCopy);
        }
        let _previous = self.materialized.insert(site.copy.destination, word);
        self.copies.push(SourcePhiCopyObservation {
            code_address: step.before.registers.code_pointer,
            destination: site.copy.destination,
            source: site.copy.source,
            trace_index,
            word,
        });
        *progress_at = progress_at
            .checked_add(1)
            .ok_or(SourcePhiCopyTraceError::InvalidPhiOrder)?;
        let total = edge
            .snapshot_sites
            .len()
            .checked_add(edge.commit_sites.len())
            .ok_or(SourcePhiCopyTraceError::InvalidSourcePlacement)?;
        if *progress_at == total {
            *progress_at = 0;
            if require_transfer {
                self.completed_visit = true;
                let pending =
                    self.pending_transfers.get_mut(site.edge_index).ok_or(
                        SourcePhiCopyTraceError::InvalidSourcePlacement,
                    )?;
                *pending = true;
            }
            self.completed_pads = self
                .completed_pads
                .checked_add(1)
                .ok_or(SourcePhiCopyTraceError::InvalidPhiOrder)?;
        }
        Ok(())
    }

    fn record_source_store(
        &mut self,
        site: (u32, u32),
        word: u32,
        stores: &SourceStoreSites,
    ) -> Result<(), SourcePhiCopyTraceError> {
        let literal = stores
            .get(&site)
            .ok_or(SourcePhiCopyTraceError::UnexpectedFrameEffect)?;
        if literal.is_some_and(|expected| expected != word) {
            return Err(SourcePhiCopyTraceError::UnexpectedFrameEffect);
        }
        let _previous = self.materialized.insert(site.1, word);
        Ok(())
    }
}

impl SourcePhiCopyProbe<'_> {
    /// Independently bind source phi sites and replay a finite graphical guest.
    ///
    /// The positive result proves only reached frame-copy value and ordering
    /// necessities. It does *not* assert that every source CFG edge executed,
    /// that the guest selected the correct branch, that a pad transferred to
    /// its successor or that output corresponds to a C function.
    ///
    /// # Errors
    ///
    /// Refuses invalid bounds/placements, failed guest execution,
    /// unmaterialized copy operands, wrong writes and incomplete copy suffixes.
    pub fn verify(self) -> Result<SourcePhiCopyProof, SourcePhiCopyTraceError> {
        self.verify_with_phi_copy_anchors(&[])
    }

    /// Verify all reached source-block exits and entries, physically written
    /// branch Booleans, phi pad ingress, copies, and successor transfers.
    ///
    /// Physical exits must originate in the reserved control suffix, land at
    /// a declared edge entry, and agree with the most recent source-placed
    /// guest Boolean write. This cannot prove how that Boolean was computed
    /// or whether the source expression was evaluated correctly.
    ///
    /// # Errors
    ///
    /// Refuses an unplaced or early source block exit in the bounded VM trace.
    pub fn verify_with_cfg_phi_copy_anchors(
        self,
        phi_anchors: &[GuestCodePhiCopyAnchor],
    ) -> Result<SourcePhiCopyProof, SourcePhiCopyTraceError> {
        self.verify_with_transfer_policy(
            phi_anchors,
            PhiTransferPolicy::AllEdges,
        )
    }

    /// Also require every reached, completed phi pad to execute its reserved
    /// `i` code transfer to the source-bound successor block entry.
    ///
    /// Setup steps may occur between physical copies and the pad exit, but
    /// may not escape, repeat a copy or halt before the exact successor jump.
    /// This does not prove that the predecessor chose the right CFG edge,
    /// that source arithmetic ran, or that the complete C program is linked.
    ///
    /// # Errors
    ///
    /// Refuses a missing, wrong or premature physical successor transfer in
    /// addition to the ordinary source placement and copy errors.
    pub fn verify_with_linked_phi_copy_anchors(
        self,
        phi_anchors: &[GuestCodePhiCopyAnchor],
    ) -> Result<SourcePhiCopyProof, SourcePhiCopyTraceError> {
        self.verify_with_transfer_policy(phi_anchors, PhiTransferPolicy::Exit)
    }

    /// Verify with source-locked, sparse physical phi snapshot/commit sites.
    ///
    /// Every explicitly anchored pad must name every snapshot and commit;
    /// unanchored pads use the original compact right-aligned copy suffix.
    /// Real pad-local setup steps are admitted only between successive
    /// copies, without allowing foreign frame writes or interleaved pads.
    ///
    /// # Errors
    ///
    /// Refuses invalid placements, guest execution and copy chronology.
    pub fn verify_with_phi_copy_anchors(
        self,
        phi_anchors: &[GuestCodePhiCopyAnchor],
    ) -> Result<SourcePhiCopyProof, SourcePhiCopyTraceError> {
        self.verify_with_transfer_policy(
            phi_anchors,
            PhiTransferPolicy::CopyOnly,
        )
    }

    /// Verify that every reached phi pad was *entered* from its owning
    /// predecessor's source-reserved control suffix, then copied and exited.
    ///
    /// This is a stronger physical CFG-linkage prerequisite than checking
    /// copy values and successor jumps alone. It does not prove source
    /// condition truth, source arithmetic or all unreachable CFG edges.
    ///
    /// # Errors
    ///
    /// Refuses wrong/foreign/mid-pad entries and any ordinary phi-copy or
    /// successor transfer failure from the same finite normative VM trace.
    pub fn verify_with_predecessor_phi_copy_anchors(
        self,
        phi_anchors: &[GuestCodePhiCopyAnchor],
    ) -> Result<SourcePhiCopyProof, SourcePhiCopyTraceError> {
        self.verify_with_transfer_policy(
            phi_anchors,
            PhiTransferPolicy::Ingress,
        )
    }

    fn verify_with_transfer_policy(
        self,
        phi_anchors: &[GuestCodePhiCopyAnchor],
        policy: PhiTransferPolicy,
    ) -> Result<SourcePhiCopyProof, SourcePhiCopyTraceError> {
        if self.physical_source.len() < 2
            || self.physical_source.len() > MAX_SOURCE_PHI_TRACE_CELLS
            || !self
                .physical_source
                .iter()
                .all(|byte| (33..=126).contains(byte))
            || self.input.len() > 256
            || !(1..=MAX_SOURCE_PHI_TRACE_STEPS).contains(&self.step_budget)
        {
            return Err(SourcePhiCopyTraceError::InvalidBound);
        }
        let source_cells = u32::try_from(self.physical_source.len())
            .map_err(|_error| SourcePhiCopyTraceError::InvalidBound)?;
        let plan: GuestAddressedCfgPlan =
            bind_source_locked_cfg_code_targets_with_phi_copy_anchors(
                GuestCodePhiCopyPlacement {
                    canonical: self.canonical,
                    source_cells,
                    frame_base: self.frame_base,
                    proposals: self.proposals,
                    operation_anchors: self.operation_anchors,
                    effect_anchors: self.effect_anchors,
                    phi_anchors,
                },
            )
            .map_err(|_error| {
                SourcePhiCopyTraceError::InvalidSourcePlacement
            })?;
        let steps = replay_phi_guest_steps(
            self.physical_source,
            self.input,
            self.step_budget,
        )?;
        if policy == PhiTransferPolicy::AllEdges {
            verify_source_block_exits(
                &plan.code_blocks,
                &plan.control_edges,
                &steps,
            )?;
            verify_source_block_entries(
                &plan.code_blocks,
                &plan.control_edges,
                &plan.function_entries,
                &steps,
            )?;
            verify_source_block_effect_visits(
                &plan.code_blocks,
                &plan.operation_effect_sites,
                &steps,
            )?;
            verify_source_return_sites(
                &plan.code_blocks,
                &plan.return_sites,
                &steps,
            )?;
        }
        if matches!(
            policy,
            PhiTransferPolicy::Ingress | PhiTransferPolicy::AllEdges
        ) {
            verify_predecessor_phi_entries(
                &plan.code_blocks,
                &plan.control_edges,
                &steps,
            )?;
        }
        let proof = verify_traced_phi_copies_with_transfer_policy(
            PhiTraceContext {
                edges: &plan.control_edges,
                effects: &plan.operation_effect_sites,
                frames: &plan.relocated.state_placements,
            },
            &steps,
            policy != PhiTransferPolicy::CopyOnly,
        )?;
        if policy == PhiTransferPolicy::AllEdges {
            verify_source_branch_choices(
                &plan.code_blocks,
                &plan.control_edges,
                &plan.operation_effect_sites,
                &plan.relocated.state_placements,
                &steps,
            )?;
        }
        Ok(proof)
    }
}

fn replay_phi_guest_steps(
    source: &[u8],
    input: &[u8],
    budget: usize,
) -> Result<Vec<ProfileStepTrace>, SourcePhiCopyTraceError> {
    let mut machine =
        ProfileMachine::from_source(current_profile(), source, input.to_vec())
            .map_err(|_error| SourcePhiCopyTraceError::InvalidGuestExecution)?;
    let mut steps = Vec::new();
    let result = machine
        .run_traced(budget, &mut |step| steps.push(*step))
        .map_err(|_error| SourcePhiCopyTraceError::InvalidGuestExecution)?;
    if !matches!(result, RunOutcome::Terminated {
        reason: Termination::HaltInstruction,
        ..
    }) {
        return Err(SourcePhiCopyTraceError::InvalidGuestExecution);
    }
    Ok(steps)
}

// A control-suffix jump to the *start* of its own block is an actual source
// backedge. Ordinary intra-block setup loops remain exempt; their control
// does not return through the canonical source block entry.
fn is_same_block_source_backedge(
    block: &GuestCodeBlockPlacement,
    from: u32,
    to: u32,
) -> bool {
    to == block.start
        && (block.control_start..block.end_exclusive).contains(&from)
}

// This is a physical *edge-target* check, not a branch-condition evaluator.
// A real VM can reach an adjacent block by falling through or by jumping;
// either route must leave the source block only from its control suffix and
// land at an entry bound to a canonical source successor. The last step of
// an explicitly returning block is checked by its separate return gate.
fn verify_source_block_exits(
    blocks: &[GuestCodeBlockPlacement],
    edges: &[GuestCodeControlEdge],
    steps: &[ProfileStepTrace],
) -> Result<(), SourcePhiCopyTraceError> {
    for pair in steps.windows(2) {
        let [previous, next] = pair else {
            continue;
        };
        let from = previous.before.registers.code_pointer;
        let to = next.before.registers.code_pointer;
        let Some(block) = blocks
            .iter()
            .find(|block| (block.start..block.end_exclusive).contains(&from))
        else {
            continue;
        };
        if (block.start..block.end_exclusive).contains(&to)
            && !is_same_block_source_backedge(block, from, to)
        {
            continue;
        }
        if from < block.control_start
            || !edges.iter().any(|edge| {
                (edge.function, edge.predecessor, edge.entry_address)
                    == (block.function, block.block, to)
            })
        {
            return Err(SourcePhiCopyTraceError::InvalidControlTransfer);
        }
    }
    Ok(())
}

// Every freshly entered source block must begin at its canonical first code
// cell. A phi-free transfer must come directly from its authenticated source
// predecessor control suffix. A phi-bearing transfer must come from the
// reserved edge-local `i` exit, never from foreign code or a pad interior.
// This does not establish source control truth or intra-block operation order.
fn verify_source_block_entries(
    blocks: &[GuestCodeBlockPlacement],
    edges: &[GuestCodeControlEdge],
    entries: &[GuestCodeFunctionEntry],
    steps: &[ProfileStepTrace],
) -> Result<(), SourcePhiCopyTraceError> {
    let Some(first) = steps.first() else {
        return Err(SourcePhiCopyTraceError::InvalidGuestExecution);
    };
    let initial_code = first.before.registers.code_pointer;
    if blocks.iter().any(|block| {
        (block.start..block.end_exclusive).contains(&initial_code)
            && !entries.iter().any(|entry| {
                (entry.function, entry.block, entry.address)
                    == (block.function, block.block, initial_code)
            })
    }) {
        return Err(SourcePhiCopyTraceError::InvalidBlockEntry);
    }
    for pair in steps.windows(2) {
        let [previous, next] = pair else {
            continue;
        };
        let from = previous.before.registers.code_pointer;
        let to = next.before.registers.code_pointer;
        let Some(block) = blocks
            .iter()
            .find(|block| (block.start..block.end_exclusive).contains(&to))
        else {
            continue;
        };
        if (block.start..block.end_exclusive).contains(&from)
            && !is_same_block_source_backedge(block, from, to)
        {
            continue;
        }
        if to != block.start
            || !edges.iter().any(|edge| {
                if (edge.function, edge.successor, edge.target_address)
                    != (block.function, block.block, to)
                    || previous.after.registers.code_pointer != to
                {
                    return false;
                }
                if let Some(exit) = edge.pad_exit_address {
                    return from == exit && previous.decoded == Some(b'i');
                }
                edge.entry_address == to
                    && blocks.iter().any(|predecessor| {
                        (predecessor.function, predecessor.block)
                            == (edge.function, edge.predecessor)
                            && (predecessor.control_start
                                ..predecessor.end_exclusive)
                                .contains(&from)
                    })
            })
        {
            return Err(SourcePhiCopyTraceError::InvalidBlockEntry);
        }
    }
    Ok(())
}

// A physical store must use the exact source-placed destination and, when
// source-known, write its literal word rather than merely execute p or *.
fn source_store_effect_matches(
    step: &ProfileStepTrace,
    destination: u32,
    literal: Option<u32>,
) -> bool {
    matches!(step.decoded, Some(b'p' | b'*'))
        && step.before.registers.data_pointer == destination
        && literal.is_none_or(|word| step.after.registers.accumulator == word)
}

// Once a source block is reached, each source-authenticated effect address
// must physically execute exactly once, in canonical order, per block visit.
// Intra-block setup may loop, but cannot repeat source operations. A canonical
// control-suffix backedge starts a new visit even though it remains within the
// same block interval. Reached addresses alone cannot prove source semantics.
fn verify_source_block_effect_visits(
    blocks: &[GuestCodeBlockPlacement],
    effects: &[GuestCodeOperationEffectSite],
    steps: &[ProfileStepTrace],
) -> Result<(), SourcePhiCopyTraceError> {
    // Every physical I/O opcode is guest-observable, including instructions
    // hidden in setup gaps, phi pads or otherwise unreserved code. Checking
    // only the declared effect sites would miss such extra reads/writes.
    for step in steps {
        let code = step.before.registers.code_pointer;
        let sourced = match step.decoded {
            Some(b'/') => effects.iter().any(|effect| {
                effect.code_address == code
                    && matches!(
                        effect.effect,
                        GuestCodeOperationEffect::Input { .. }
                    )
            }),
            Some(b'<') => effects.iter().any(|effect| {
                effect.code_address == code
                    && matches!(
                        effect.effect,
                        GuestCodeOperationEffect::Output { .. }
                    )
            }),
            _ => true,
        };
        if !sourced {
            return Err(SourcePhiCopyTraceError::UnexpectedSourceIo);
        }
    }
    let mut index = 0;
    while let Some(step) = steps.get(index) {
        let code = step.before.registers.code_pointer;
        let Some(block) = blocks
            .iter()
            .find(|block| (block.start..block.end_exclusive).contains(&code))
        else {
            index += 1;
            continue;
        };
        let visit_start = index;
        let mut previous = code;
        index += 1;
        while steps.get(index).is_some_and(|next| {
            let next_code = next.before.registers.code_pointer;
            (block.start..block.end_exclusive).contains(&next_code)
                && !is_same_block_source_backedge(block, previous, next_code)
        }) {
            previous = steps
                .get(index)
                .ok_or(SourcePhiCopyTraceError::InvalidGuestExecution)?
                .before
                .registers
                .code_pointer;
            index += 1;
        }
        let visit = steps
            .get(visit_start..index)
            .ok_or(SourcePhiCopyTraceError::InvalidGuestExecution)?;
        let mut required = effects.iter().filter(|effect| {
            (effect.function, effect.block) == (block.function, block.block)
        });
        for reached in visit {
            let site = reached.before.registers.code_pointer;
            if !effects.iter().any(|effect| {
                (effect.function, effect.block, effect.code_address)
                    == (block.function, block.block, site)
            }) {
                continue;
            }
            let effect = required
                .next()
                .ok_or(SourcePhiCopyTraceError::RepeatedBlockEffect)?;
            if site != effect.code_address {
                return Err(SourcePhiCopyTraceError::MissingBlockEffect);
            }
            let correct_effect = match effect.effect {
                GuestCodeOperationEffect::Input { .. } => {
                    reached.decoded == Some(b'/')
                },
                GuestCodeOperationEffect::Output { .. } => {
                    reached.decoded == Some(b'<')
                },
                GuestCodeOperationEffect::Store { destination, literal } => {
                    source_store_effect_matches(reached, destination, literal)
                },
                GuestCodeOperationEffect::Compute => true,
            };
            if !correct_effect {
                return Err(SourcePhiCopyTraceError::InvalidBlockEffect);
            }
        }
        if required.next().is_some() {
            return Err(SourcePhiCopyTraceError::MissingBlockEffect);
        }
    }
    Ok(())
}

// The bounded normative VM's `v` is not a source-C return merely because
// an earlier source block chose legal edges or emitted its required effects.
// The actual terminal instruction must be in the control suffix of an
// authenticated Return block. This is only physical terminal provenance:
// it does not prove the source return value or preceding C computations.
fn verify_source_return_sites(
    blocks: &[GuestCodeBlockPlacement],
    returns: &[GuestCodeReturnSite],
    steps: &[ProfileStepTrace],
) -> Result<(), SourcePhiCopyTraceError> {
    let last = steps
        .last()
        .ok_or(SourcePhiCopyTraceError::InvalidGuestExecution)?;
    if last.decoded != Some(b'v') {
        return Err(SourcePhiCopyTraceError::InvalidGuestExecution);
    }
    let code = last.before.registers.code_pointer;
    if !returns.iter().any(|site| {
        blocks.iter().any(|block| {
            (site.function, site.block) == (block.function, block.block)
                && site.address == block.control_start
                && (block.control_start..block.end_exclusive).contains(&code)
        })
    }) {
        return Err(SourcePhiCopyTraceError::InvalidSourceReturn);
    }
    Ok(())
}

// Source placement already authenticates all block and edge intervals. The
// physical trace must still demonstrate *how* each phi pad was reached: a
// genuine executed instruction in the predecessor's control suffix, with
// its actual post-step C pointing at the pad's first cell. Checking every
// fresh entry also catches jumps into the middle of the pad, even if a
// later copy happens to produce the right word.
fn verify_predecessor_phi_entries(
    blocks: &[GuestCodeBlockPlacement],
    edges: &[GuestCodeControlEdge],
    steps: &[ProfileStepTrace],
) -> Result<(), SourcePhiCopyTraceError> {
    for (index, step) in steps.iter().enumerate() {
        let code = step.before.registers.code_pointer;
        for edge in edges {
            let Some(exit) = edge.pad_exit_address else {
                continue;
            };
            let pad = edge.entry_address..=exit;
            if !pad.contains(&code) {
                continue;
            }
            let predecessor = index.checked_sub(1).and_then(|at| steps.get(at));
            if predecessor.is_some_and(|previous| {
                pad.contains(&previous.before.registers.code_pointer)
            }) {
                continue;
            }
            let previous =
                predecessor.ok_or(SourcePhiCopyTraceError::InvalidPhiEntry)?;
            let block = blocks
                .iter()
                .find(|block| {
                    (block.function, block.block)
                        == (edge.function, edge.predecessor)
                })
                .ok_or(SourcePhiCopyTraceError::InvalidSourcePlacement)?;
            let from = previous.before.registers.code_pointer;
            if code != edge.entry_address
                || !(edge.control_address..block.end_exclusive).contains(&from)
                || previous.after.registers.code_pointer != edge.entry_address
            {
                return Err(SourcePhiCopyTraceError::InvalidPhiEntry);
            }
        }
    }
    Ok(())
}

// A source `<` site is necessary but not enough: the real A word must be
// equal to the live, guest-written typed U8 operand, not only its low byte.
fn verify_source_output_operand(
    step: &ProfileStepTrace,
    effects: &[GuestCodeOperationEffectSite],
    materialized: &BTreeMap<u32, u32>,
) -> Result<(), SourcePhiCopyTraceError> {
    if step.decoded != Some(b'<') {
        return Ok(());
    }
    let code = step.before.registers.code_pointer;
    let source_operand = effects
        .iter()
        .filter(|effect| effect.code_address == code)
        .find_map(|effect| match effect.effect {
            GuestCodeOperationEffect::Output { source } => Some(source),
            GuestCodeOperationEffect::Input { .. }
            | GuestCodeOperationEffect::Store { .. }
            | GuestCodeOperationEffect::Compute => None,
        });
    let Some(operand) = source_operand else {
        // The preceding source effect-visit check rejects unplaced I/O.
        return Ok(());
    };
    let value = materialized
        .get(&operand.address)
        .ok_or(SourcePhiCopyTraceError::MissingOutputMaterialization)?;
    if step.before.registers.accumulator != *value
        || u8::try_from(*value).ok() != step.output
    {
        return Err(SourcePhiCopyTraceError::InvalidOutputValue);
    }
    Ok(())
}

// A reached conditional edge must agree with the most recent *physical*
// write of its source-authenticated Boolean SSA cell. A source output must
// likewise match the exact most recent physical U8 operand word and the guest
// accumulator. The source frame/phi gate checks write sites and values first.
// Loader-seeded state is no proof of a source computation or operand read.
fn verify_source_branch_choices(
    blocks: &[GuestCodeBlockPlacement],
    edges: &[GuestCodeControlEdge],
    effects: &[GuestCodeOperationEffectSite],
    frames: &[GuestFramePlacement],
    steps: &[ProfileStepTrace],
) -> Result<(), SourcePhiCopyTraceError> {
    let stores = source_store_sites(effects)?;
    let copies = phi_copy_sites(edges)?;
    let mut materialized = BTreeMap::new();
    for (index, previous) in steps.iter().enumerate() {
        let from = previous.before.registers.code_pointer;
        let data = previous.before.registers.data_pointer;
        if matches!(previous.decoded, Some(b'p' | b'*'))
            && in_frame(data, frames)
        {
            if !stores.contains_key(&(from, data))
                && !copies
                    .get(&from)
                    .is_some_and(|site| site.copy.destination == data)
            {
                return Err(SourcePhiCopyTraceError::UnexpectedFrameEffect);
            }
            let _old =
                materialized.insert(data, previous.after.registers.accumulator);
        }
        verify_source_output_operand(previous, effects, &materialized)?;
        let Some(next) = steps.get(index + 1) else {
            continue;
        };
        let to = next.before.registers.code_pointer;
        let Some(block) = blocks
            .iter()
            .find(|block| (block.start..block.end_exclusive).contains(&from))
        else {
            continue;
        };
        if (block.start..block.end_exclusive).contains(&to)
            && !is_same_block_source_backedge(block, from, to)
        {
            continue;
        }
        let selected = edges.iter().filter(|edge| {
            (edge.function, edge.predecessor, edge.entry_address)
                == (block.function, block.block, to)
        });
        let mut saw_missing = false;
        let mut saw_invalid = false;
        let mut matches_arm = false;
        for edge in selected {
            let expected = match edge.kind {
                GuestCodeEdgeKind::Jump => {
                    matches_arm = true;
                    break;
                },
                GuestCodeEdgeKind::WhenFalse => 0,
                GuestCodeEdgeKind::WhenTrue => 1,
            };
            let Some(condition) = edge.condition else {
                return Err(SourcePhiCopyTraceError::InvalidSourcePlacement);
            };
            if condition.words != 1
                || condition.type_kind != TernaryCfgScalarKind::Bool
            {
                return Err(SourcePhiCopyTraceError::InvalidSourcePlacement);
            }
            match materialized.get(&condition.address) {
                Some(&value) if value == expected => {
                    matches_arm = true;
                    break;
                },
                Some(&_value) => saw_invalid = true,
                None => saw_missing = true,
            }
        }
        if !matches_arm {
            return Err(if saw_invalid {
                SourcePhiCopyTraceError::InvalidBranchSelection
            } else if saw_missing {
                SourcePhiCopyTraceError::MissingBranchCondition
            } else {
                SourcePhiCopyTraceError::InvalidControlTransfer
            });
        }
    }
    Ok(())
}

fn in_frame(address: u32, frames: &[GuestFramePlacement]) -> bool {
    frames
        .iter()
        .any(|frame| frame.base <= address && address < frame.end_exclusive)
}

fn phi_copy_sites(
    edges: &[GuestCodeControlEdge],
) -> Result<PhiCopySites, SourcePhiCopyTraceError> {
    let mut sites = BTreeMap::new();
    for (edge_index, edge) in edges.iter().enumerate() {
        for (ordinal, site) in edge
            .snapshot_sites
            .iter()
            .chain(&edge.commit_sites)
            .enumerate()
        {
            if sites
                .insert(site.code_address, CopySite {
                    copy: site.copy,
                    edge_index,
                    ordinal,
                })
                .is_some()
            {
                return Err(SourcePhiCopyTraceError::InvalidSourcePlacement);
            }
        }
    }
    Ok(sites)
}

fn source_store_sites(
    effects: &[GuestCodeOperationEffectSite],
) -> Result<SourceStoreSites, SourcePhiCopyTraceError> {
    let mut sites = BTreeMap::new();
    for site in effects {
        if let GuestCodeOperationEffect::Store { destination, literal } =
            site.effect
            && sites
                .insert((site.code_address, destination), literal)
                .is_some()
        {
            return Err(SourcePhiCopyTraceError::InvalidSourcePlacement);
        }
    }
    Ok(sites)
}

// Trusted callers pass the source-locked plan and the normative VM's trace.
// Do not accept a mere final memory value or an unexecuted placement proposal.
#[cfg(test)]
fn verify_traced_phi_copies(
    edges: &[GuestCodeControlEdge],
    effects: &[GuestCodeOperationEffectSite],
    frames: &[GuestFramePlacement],
    steps: &[ProfileStepTrace],
) -> Result<SourcePhiCopyProof, SourcePhiCopyTraceError> {
    verify_traced_phi_copies_with_transfer_policy(
        PhiTraceContext { edges, effects, frames },
        steps,
        false,
    )
}

fn verify_traced_phi_copies_with_transfer_policy(
    context: PhiTraceContext<'_>,
    steps: &[ProfileStepTrace],
    require_transfer: bool,
) -> Result<SourcePhiCopyProof, SourcePhiCopyTraceError> {
    let PhiTraceContext { edges, effects, frames } = context;
    let copies_by_code = phi_copy_sites(edges)?;
    let stores_by_site = source_store_sites(effects)?;
    let mut progress = PhiTraceProgress::new(edges);
    for (trace_index, step) in steps.iter().enumerate() {
        if step.result.is_err() {
            return Err(SourcePhiCopyTraceError::InvalidGuestExecution);
        }
        let code_address = step.before.registers.code_pointer;
        let data_address = step.before.registers.data_pointer;
        if in_frame(code_address, frames)
            || step
                .memory_reads
                .encryption
                .is_some_and(|read| in_frame(read.address, frames))
            || step
                .memory_delta
                .encryption
                .is_some_and(|write| in_frame(write.address, frames))
        {
            return Err(SourcePhiCopyTraceError::UnexpectedFrameEffect);
        }
        if require_transfer {
            progress.check_pending_transfers(step, edges, &copies_by_code)?;
            progress.check_pad_visit(code_address, edges)?;
        }
        progress.check_interleaving(code_address, edges, &copies_by_code)?;
        if let Some(site) = copies_by_code.get(&code_address) {
            let edge = edges
                .get(site.edge_index)
                .ok_or(SourcePhiCopyTraceError::InvalidSourcePlacement)?;
            progress.record_copy(
                *site,
                edge,
                step,
                trace_index,
                require_transfer,
            )?;
        } else if matches!(step.decoded, Some(b'p' | b'*'))
            && in_frame(data_address, frames)
        {
            progress.record_source_store(
                (code_address, data_address),
                step.after.registers.accumulator,
                &stores_by_site,
            )?;
        }
    }
    if progress.progress.iter().any(|at| *at != 0)
        || (require_transfer
            && progress.active_pad.is_some()
            && !progress.completed_visit)
    {
        return Err(SourcePhiCopyTraceError::InvalidPhiOrder);
    }
    if require_transfer && progress.pending_transfers.contains(&true) {
        return Err(SourcePhiCopyTraceError::InvalidPhiTransfer);
    }
    if progress.copies.is_empty() {
        return Err(SourcePhiCopyTraceError::NoReachedPhiCopy);
    }
    Ok(SourcePhiCopyProof {
        completed_pads: progress.completed_pads,
        copies: progress.copies,
    })
}

#[cfg(test)]
#[path = "../../../../tests/compiler/source_phi_copy_trace.rs"]
mod tests;
