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
    GuestAddressedCfgPlan, GuestCodeControlEdge, GuestCodeEffectAnchor,
    GuestCodeOperationAnchor, GuestCodeOperationEffect,
    GuestCodeOperationEffectSite, GuestCodeProposals, GuestPlacedCellCopy,
    bind_source_locked_cfg_code_targets_with_effect_anchors,
};
use super::typed_cfg_adapter::state_storage::GuestFramePlacement;

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
    /// Normative VM did not execute a complete, valid bounded guest run.
    InvalidGuestExecution,
    /// A reached phi site did not write the declared destination/value.
    InvalidPhiCopy,
    /// A reached phi site was absent, reordered or left mid-transfer.
    InvalidPhiOrder,
    /// Canonical source and proposed code/SSA placement do not agree.
    InvalidSourcePlacement,
    /// A copy source had no earlier, actual source-placed guest data write.
    MissingSourceMaterialization,
    /// No physical source-placed phi snapshot or commit was reached.
    NoReachedPhiCopy,
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

#[derive(Clone, Copy)]
struct CopySite {
    copy: GuestPlacedCellCopy,
    edge_index: usize,
    ordinal: usize,
}

type PhiCopySites = BTreeMap<u32, CopySite>;
type SourceStoreSites = BTreeMap<(u32, u32), Option<u32>>;

#[derive(Default)]
struct PhiTraceProgress {
    completed_pads: usize,
    copies: Vec<SourcePhiCopyObservation>,
    materialized: BTreeMap<u32, u32>,
    progress: Vec<usize>,
}

impl PhiTraceProgress {
    fn check_interleaving(
        &self,
        code_address: u32,
        sites: &PhiCopySites,
    ) -> Result<(), SourcePhiCopyTraceError> {
        // Copy suffixes cannot interleave with setup, another pad or a
        // different physical copy. A revisited *completed* pad is allowed.
        if self.progress.iter().enumerate().any(|(index, at)| {
            *at > 0
                && sites.get(&code_address).is_none_or(|site| {
                    site.edge_index != index || site.ordinal != *at
                })
        }) {
            return Err(SourcePhiCopyTraceError::InvalidPhiOrder);
        }
        Ok(())
    }

    fn new(edges: &[GuestCodeControlEdge]) -> Self {
        Self {
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
    ) -> Result<(), SourcePhiCopyTraceError> {
        let progress_at = self
            .progress
            .get_mut(site.edge_index)
            .ok_or(SourcePhiCopyTraceError::InvalidSourcePlacement)?;
        if *progress_at != site.ordinal {
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
            bind_source_locked_cfg_code_targets_with_effect_anchors(
                self.canonical,
                source_cells,
                self.frame_base,
                self.proposals,
                self.operation_anchors,
                self.effect_anchors,
            )
            .map_err(|_error| {
                SourcePhiCopyTraceError::InvalidSourcePlacement
            })?;
        let mut machine = ProfileMachine::from_source(
            current_profile(),
            self.physical_source,
            self.input.to_vec(),
        )
        .map_err(|_error| SourcePhiCopyTraceError::InvalidGuestExecution)?;
        let mut steps = Vec::new();
        let result = machine
            .run_traced(self.step_budget, &mut |step| steps.push(*step))
            .map_err(|_error| SourcePhiCopyTraceError::InvalidGuestExecution)?;
        if !matches!(result, RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            ..
        }) {
            return Err(SourcePhiCopyTraceError::InvalidGuestExecution);
        }
        verify_traced_phi_copies(
            &plan.control_edges,
            &plan.operation_effect_sites,
            &plan.relocated.state_placements,
            &steps,
        )
    }
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
fn verify_traced_phi_copies(
    edges: &[GuestCodeControlEdge],
    effects: &[GuestCodeOperationEffectSite],
    frames: &[GuestFramePlacement],
    steps: &[ProfileStepTrace],
) -> Result<SourcePhiCopyProof, SourcePhiCopyTraceError> {
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
        progress.check_interleaving(code_address, &copies_by_code)?;
        if let Some(site) = copies_by_code.get(&code_address) {
            let edge = edges
                .get(site.edge_index)
                .ok_or(SourcePhiCopyTraceError::InvalidSourcePlacement)?;
            progress.record_copy(*site, edge, step, trace_index)?;
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
    if progress.progress.iter().any(|at| *at != 0) {
        return Err(SourcePhiCopyTraceError::InvalidPhiOrder);
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
