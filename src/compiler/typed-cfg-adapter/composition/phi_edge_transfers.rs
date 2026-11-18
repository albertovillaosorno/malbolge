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
//   - Canonical CFG predecessor-specific, parallel phi transfer planning.
// - Must-Not:
//   - Mutate SSA state on the host, choose a branch or emit guest instructions.
// - Allows:
//   - Inputs: freshly validated symbolic ternary CFG from canonical typed IR.
//   - Outputs: ordered, source-typed parallel transfers for reached edges.
//   - Side effects: none.
// - Split-When:
//   - Physical guest slot allocation determines a copy scheduling policy.
// - Merge-When:
//   - A verified CFG linker realizes these parallel copies at guest edges.
// - Summary:
//   - Retains the simultaneous semantics of incoming phi values per edge.
// - Description:
//   - Carries each actual CFG predecessor and successor unchanged, with no
//     sequential copy order or branch value chosen by the host.
// - Usage:
//   - Call through `prepare_canonical_dynamic_cfg` in the parent module.
// - Defaults:
//   - An invalid edge or missing incoming value fails closed.
//

//! Pre-layout phi edge transfers; still no physical guest memory locations.

use super::TypedCfgAdapterError;
use super::ternary::{
    TernaryCfgPlan, TernaryCfgScalarKind, TernaryCfgTerminator,
    TernaryLoweringError,
};

/// One *parallel*, not sequential, SSA phi transfer for a reached edge.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct PhiEdgeMove {
    /// Target phi value, to be materialized simultaneously with other moves.
    pub result: u32,
    /// The value selected solely by the taken predecessor edge.
    pub source: u32,
    /// Exact scalar category required for future physical storage.
    pub type_kind: TernaryCfgScalarKind,
}

/// Phi transfers to apply on a particular directed control-flow edge.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct PhiEdgeTransfers {
    /// Function identity from the canonical typed source.
    pub function: u32,
    /// Static predecessor, never a host-selected runtime branch.
    pub predecessor: u32,
    /// Parallel assignment set, in the target block's canonical phi order.
    pub simultaneous: Vec<PhiEdgeMove>,
    /// Destination block carrying these phi merges.
    pub successor: u32,
}

/// A source-backed CFG with frame-relative cell reservations and phi copies.
/// Neither the frame base nor guest code has been physically linked.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct PrelinkCfgPlan {
    /// Two-phase word copies for each parallel phi assignment edge.
    pub cell_edges: Vec<super::state_storage::GuestCellEdge>,
    /// Original independently validated and lowered control graph.
    pub cfg: TernaryCfgPlan,
    /// All predecessor-sensitive, simultaneous phi writes.
    pub phi_edges: Vec<PhiEdgeTransfers>,
    /// Frame-relative data slots for the current 15-trit profile.
    pub state_frames: Vec<super::state_storage::GuestStateFrame>,
}

/// Extract the exact phi semantics on every static CFG edge. The caller
/// must provide the result of `lower_canonical_dynamic_cfg`, which validates
/// all SSA definitions, predecessor sets and type constraints first.
pub(super) fn plan_phi_edges(
    cfg: &TernaryCfgPlan,
) -> Result<Vec<PhiEdgeTransfers>, TypedCfgAdapterError> {
    let mut transfers = Vec::new();
    for function in &cfg.functions {
        for predecessor in &function.blocks {
            let mut targets = match predecessor.terminator {
                TernaryCfgTerminator::Branch {
                    false_target,
                    true_target,
                    ..
                } => vec![false_target, true_target],
                TernaryCfgTerminator::Jump { target, .. } => vec![target],
                TernaryCfgTerminator::Return(_) => Vec::new(),
            };
            targets.sort_unstable();
            targets.dedup();
            for successor in targets {
                let block = function
                    .blocks
                    .iter()
                    .find(|block| block.id == successor)
                    .ok_or(TypedCfgAdapterError::Lowering(
                        TernaryLoweringError::InvalidProjection,
                    ))?;
                if block.phis.is_empty() {
                    continue;
                }
                let mut simultaneous = Vec::with_capacity(block.phis.len());
                for phi in &block.phis {
                    let source = phi
                        .incoming
                        .iter()
                        .find(|(incoming_block, _)| {
                            *incoming_block == predecessor.id
                        })
                        .map(|(_, value)| *value)
                        .ok_or(TypedCfgAdapterError::Lowering(
                            TernaryLoweringError::InvalidProjection,
                        ))?;
                    simultaneous.push(PhiEdgeMove {
                        result: phi.result,
                        source,
                        type_kind: phi.type_kind,
                    });
                }
                transfers.push(PhiEdgeTransfers {
                    function: function.id,
                    predecessor: predecessor.id,
                    successor,
                    simultaneous,
                });
            }
        }
    }
    Ok(transfers)
}
