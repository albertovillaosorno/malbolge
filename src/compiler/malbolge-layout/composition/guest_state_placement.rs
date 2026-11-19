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
//   - Binding canonical typed state to the real physical helper source.
// - Must-Not:
//   - Claim physical C writes, guest arithmetic or executable CFG linkage.
// - Allows:
//   - Inputs: canonical typed CFG, exact source and normative admitted paths.
//   - Outputs: jointly checked physical-source and typed-data reservations.
//   - Side effects: none.
// - Split-When:
//   - Verified physical operand realization and control linkage are present.
// - Merge-When:
//   - The complete guest linker incorporates this independent placement gate.
// - Summary:
//   - Makes source/profile/scratch identity explicit across prelink stages.
//
//! A source-bound *data placement*, not physical guest instruction linkage.
//!
//! The canonical typed CFG comes from upstream source authentication. The
//! physical path witnesses come from normative guest execution and retain
//! their exact source bytes and profile identity. This stage refuses to
//! reserve C locals for one source while reusing another source's trace.
//!
//! No result is executable: literal writes, arithmetic, two-phase phi copies,
//! and dynamic C control still need real guest instructions and VM parity.

use malbolge::{ProfileDescriptor, current_profile};

use super::bounded_revisit::{
    BoundedGuestDataRegion, BoundedGuestRegionsError, BoundedRevisitLayout,
    place_bounded_guest_state_frame,
};
use super::typed_cfg_adapter::state_relocation::{
    GuestRelocatedCfgPlan, relocate_source_locked_cfg,
};
use super::typed_cfg_adapter::{
    TypedCfgAdapterError, prepare_canonical_dynamic_cfg,
};

/// Why a canonical typed frame cannot be placed alongside the admitted helper.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum GuestStatePlacementError {
    /// The typed CFG cannot allocate complete checked scalar/phi frames.
    TypedCfg(TypedCfgAdapterError),
    /// Requested source bytes or path-profile identity differ from evidence.
    SourceMismatch,
    /// The physical helper was not verified under the current N15 profile.
    UnsupportedProfile,
    /// The source-external helper/state intervals are not safely reservable.
    PhysicalRegion(BoundedGuestRegionsError),
    /// The independently relocated typed data footprint differs from the
    /// actual helper-isolated state interval.
    FrameMismatch,
}

/// A checked state-address candidate attached to actual graphical guest code.
///
/// This is an allocation *witness*, not a code generation or publication
/// result. In particular, no admitted helper path mutates these C-state cells.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct GuestStatePlacementCandidate {
    admitted_inputs: Vec<Vec<u8>>,
    helper_regions: Vec<BoundedGuestDataRegion>,
    relocated: GuestRelocatedCfgPlan,
    source: Vec<u8>,
    state_region: BoundedGuestDataRegion,
}

impl GuestStatePlacementCandidate {
    /// Sorted exact input streams covered by the supplied normative paths.
    /// This is finite evidence, not arbitrary-stream guest C semantics.
    #[must_use]
    pub fn admitted_inputs(&self) -> &[Vec<u8>] {
        &self.admitted_inputs
    }

    /// Exact original graphical source used by every admitted helper path.
    #[must_use]
    pub fn source(&self) -> &[u8] {
        &self.source
    }

    /// Full helper-owned scratch intervals, including unvisited words.
    #[must_use]
    pub fn helper_regions(&self) -> &[BoundedGuestDataRegion] {
        &self.helper_regions
    }

    /// Complete typed instruction/branch/phi *data* address obligations.
    #[must_use]
    pub const fn relocated(&self) -> &GuestRelocatedCfgPlan {
        &self.relocated
    }

    /// Isolated, uninitialized C-state interval in the original N15 image.
    #[must_use]
    pub const fn state_region(&self) -> BoundedGuestDataRegion {
        self.state_region
    }
}

/// All independent evidence required to propose one physical C-state frame.
///
/// These are input witnesses, not a promise that the physical source can run
/// the C program. In particular, `canonical` must already be authenticated
/// against the original C source by the upstream compiler.
#[derive(Clone, Copy, Debug)]
pub struct GuestStatePlacementRequest<'evidence> {
    /// The exact source-authenticated canonical typed IR from the frontend.
    pub canonical: &'evidence [u8],
    /// All independently admitted, source-identical normative helper paths.
    pub admitted: &'evidence [BoundedRevisitLayout],
    /// Full physical helper scratch, including unvisited writable words.
    pub helper_regions: &'evidence [BoundedGuestDataRegion],
    /// The exact target profile of the physical source and all its traces.
    pub profile: &'static ProfileDescriptor,
    /// Graphical candidate bytes actually admitted in the normative VM.
    pub source: &'evidence [u8],
}

/// Reserve the complete source-authenticated typed CFG state in one physical
/// N15 image, independently admitted on all supplied input-specific paths.
///
/// `canonical` must come from an upstream source-checked typed-IR stage, not
/// a caller-authored projection. The final guest linker must invalidate this
/// witness if it edits `source` or adds accesses to the isolated state cells.
/// The source's actual size is used rather than a hypothetical final size.
///
/// # Errors
///
/// Rejects any source/profile identity mismatch, untrusted typed frame,
/// missing or overlapping helper scratch, impossible first-fit frame, or
/// disagreement between independently computed relative/absolute footprints.
pub fn place_source_bound_guest_state(
    request: GuestStatePlacementRequest<'_>,
) -> Result<GuestStatePlacementCandidate, GuestStatePlacementError> {
    let GuestStatePlacementRequest {
        canonical,
        admitted,
        helper_regions,
        profile,
        source,
    } = request;
    if profile != current_profile() {
        return Err(GuestStatePlacementError::UnsupportedProfile);
    }
    if admitted.is_empty()
        || admitted.iter().any(|path| {
            path.source() != source
                || path.profile_id() != profile.id()
                || path.profile_fingerprint() != profile.fingerprint()
        })
    {
        return Err(GuestStatePlacementError::SourceMismatch);
    }
    let prelink = prepare_canonical_dynamic_cfg(canonical)
        .map_err(GuestStatePlacementError::TypedCfg)?;
    let required_words = prelink
        .state_frames
        .iter()
        .try_fold(0u32, |words, frame| words.checked_add(frame.total_words))
        .filter(|words| *words > 0)
        .ok_or(GuestStatePlacementError::FrameMismatch)?;
    let state_region = place_bounded_guest_state_frame(
        admitted,
        helper_regions,
        required_words,
    )
    .map_err(GuestStatePlacementError::PhysicalRegion)?;
    let source_cells = u32::try_from(source.len())
        .map_err(|_error| GuestStatePlacementError::FrameMismatch)?;
    let relocated =
        relocate_source_locked_cfg(canonical, source_cells, state_region.start)
            .map_err(GuestStatePlacementError::TypedCfg)?;
    if relocated.prelink != prelink
        || relocated
            .state_placements
            .first()
            .is_none_or(|frame| frame.base != state_region.start)
        || relocated.state_placements.last().is_none_or(|frame| {
            frame.end_exclusive != state_region.end_exclusive
        })
        || relocated
            .state_placements
            .iter()
            .any(|frame| frame.source_cells != source_cells)
    {
        return Err(GuestStatePlacementError::FrameMismatch);
    }
    let mut admitted_inputs = admitted
        .iter()
        .map(|path| path.input().to_vec())
        .collect::<Vec<_>>();
    admitted_inputs.sort_unstable();
    Ok(GuestStatePlacementCandidate {
        admitted_inputs,
        helper_regions: helper_regions.to_vec(),
        relocated,
        source: source.to_vec(),
        state_region,
    })
}
