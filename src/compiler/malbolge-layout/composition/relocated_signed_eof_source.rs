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
//   - Source-loaded canonical EOF materialization and shared marker tapes.
// - Must-Not:
//   - Claim source-frame admission, checksum arithmetic, or an EOF loop.
// - Allows:
//   - Inputs: the exact current N15 profile and fixed physical branch.
//   - Outputs: graphical code and reached store/return proposals.
//   - Side effects: none; independent normative replay owns acceptance.
// - Split-When:
//   - A general physical C32 operand allocator replaces the tape.
// - Merge-When:
//   - Source-C input lowering owns complete guest frame initialization.
// - Summary:
//   - Normalize true EOF using a branch-selected ternary marker tape.

//! Source-loaded, branch-dependent C32 EOF normalization.
//!
//! The byte arm remains incomplete. No source-level CFG or frame
//! authorization follows from these physical candidate addresses.

#[path = "relocated_eof_parity_source.rs"]
mod relocated_eof_parity_source;
#[path = "relocated_first_byte_add_source.rs"]
mod relocated_first_byte_add_source;
#[path = "relocated_live_parity_source.rs"]
mod relocated_live_parity_source;
#[path = "relocated_reusable_source.rs"]
mod relocated_reusable_source;
use std::array;
use std::sync::OnceLock;

use malbolge::{ProfileDescriptor, current_profile};
pub use relocated_eof_parity_source::{
    RelocatedEofParitySource, build_relocated_eof_parity_source,
};
pub use relocated_first_byte_add_source::{
    DirtyPhiCopySites, OddXorStepSites, RelocatedDirtyPhiSource,
    RelocatedFirstByteAddSource, RelocatedFirstIterationSource,
    RelocatedSecondAddSource, RelocatedSecondCombinedReadSource,
    RelocatedSecondEvenMaskSource, RelocatedSecondEvenReadSource,
    RelocatedSecondOddHalfSource, RelocatedSecondOddReadSource,
    RelocatedSecondOddUpdateSource, RelocatedSecondOddXorSource,
    RelocatedSecondParityAddSource, ScratchResetSite,
    build_relocated_dirty_phi_source, build_relocated_first_byte_add_source,
    build_relocated_first_iteration_source, build_relocated_second_add_source,
    build_relocated_second_combined_read_source,
    build_relocated_second_even_mask_source,
    build_relocated_second_even_read_source,
    build_relocated_second_odd_half_source,
    build_relocated_second_odd_read_source,
    build_relocated_second_odd_update_source,
    build_relocated_second_odd_xor_source,
    build_relocated_second_parity_add_source,
};
pub use relocated_live_parity_source::{
    RelocatedLiveParityBranchSource, RelocatedLiveParitySource,
    build_relocated_live_parity_branch_source,
    build_relocated_live_parity_source,
};
pub use relocated_reusable_source::{
    RelocatedRecurrentCaptureSource, RelocatedRecurrentIndexedSource,
    RelocatedRecurrentMod4Source, RelocatedRecurrentParitySource,
    RelocatedRecurrentReloadSource, RelocatedReusableGuardSource,
    RelocatedReusableSource, build_relocated_recurrent_capture_source,
    build_relocated_recurrent_indexed_source,
    build_relocated_recurrent_mod4_source,
    build_relocated_recurrent_parity_source,
    build_relocated_recurrent_reload_source,
    build_relocated_reusable_guard_source, build_relocated_reusable_source,
};

use super::typed_cfg_adapter::state_storage::encode_i32_cells;
use super::{
    CodeVisitRequirement, LinearOpcode, RelocatedEofBranchSource,
    ZeroCellSourceError, build_relocated_eof_branch_source, encode_code_visits,
    unique_graphical_cell, unwritten_loader_word,
};

const FRAME: u32 = 7_174_417;
const FRAME_RESET: u32 = 7_174_424;
const LAYOUT: BuildError = BuildError::NoLoadableZero;
const BOOT_RETURN: u32 = 7_174_467;
const TAPE_START: u32 = 7_174_501;
const TAPE_LIMIT: u32 = 7_174_957;
const TAPE_ZERO: u32 = 7_174_503;
const TAPE_BOUNDS: TapeBounds = TapeBounds {
    limit: TAPE_LIMIT,
    start: TAPE_START,
};
const SOURCE_CELLS: usize = 6_642;
const DECODE_PHASES: usize = 94;
// Canonical no-ops are profile-independent. Cache the independently checked
// phase encodings instead of scanning the printable alphabet for every walk.
static NOOP_ENCODINGS: OnceLock<[Option<u8>; DECODE_PHASES]> = OnceLock::new();
const ROTATION_ORDER: [u32; 15] =
    [3, 2, 1, 0, 14, 13, 12, 11, 10, 9, 8, 7, 6, 5, 4];

/// One finite physical branch with normalized signed first-input storage.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct RelocatedSignedEofBranchSource {
    /// Common C118 code transfer.
    pub branch_code_address: u32,
    /// Successful-byte arm's C121 halt, without checksum arithmetic.
    pub byte_halt_code_address: u32,
    /// Successful-byte arm's C120 second read.
    pub byte_input_code_address: u32,
    /// Common C99 class-word write.
    pub class_store_code_address: u32,
    /// EOF-only C126 entry.
    pub eof_arm_code_address: u32,
    /// Physical EOF return after the original output operand is written.
    pub eof_halt_code_address: u32,
    /// Physical EOF output site.
    pub eof_output_code_address: u32,
    /// Physical EOF output-operand store site.
    pub eof_output_store_code_address: u32,
    /// Last physical low/high writes of canonical signed C32 EOF.
    pub eof_store_code_addresses: [u32; 2],
    /// Common C53 first read.
    pub first_input_code_address: u32,
    /// Adjacent input result words, raw before and canonical after EOF arm.
    pub input_pair: [u32; 2],
    /// Physical source output operand address.
    pub output_data_address: u32,
    /// Graphical source and unchanged two-byte loader seed.
    pub source: Vec<u8>,
    /// Physical checksum initializer words.
    pub zero_pair: [u32; 2],
}

type BuildError = ZeroCellSourceError;
type TapeAnchor = Option<(u32, u32)>;

#[derive(Clone, Copy)]
enum Operand {
    Marker,
    Swap,
}

struct MarkerCopy {
    digit: u32,
    intermediate: u32,
    operand: u32,
}

#[derive(Clone, Copy)]
struct TapeBounds {
    limit: u32,
    start: u32,
}

struct TapePlan {
    bounds: TapeBounds,
    copies: Vec<MarkerCopy>,
    next_slot: u32,
}

impl TapePlan {
    fn allocate(&mut self) -> Result<u32, BuildError> {
        let slot = self.next_slot;
        self.next_slot = slot.checked_add(4).ok_or(LAYOUT)?;
        if self.next_slot > self.bounds.limit {
            return Err(LAYOUT);
        }
        Ok(slot)
    }

    fn allocate_operand(
        &mut self,
        digit: u32,
        kind: Operand,
    ) -> Result<u32, BuildError> {
        if matches!(kind, Operand::Marker) {
            let intermediate = self.allocate()?;
            let operand = self.allocate()?;
            self.copies.push(MarkerCopy {
                digit,
                intermediate,
                operand,
            });
            Ok(operand)
        } else {
            self.allocate()
        }
    }

    const fn new() -> Self {
        Self::with_bounds(TAPE_BOUNDS)
    }

    const fn operands_for_digit(
        target_digit: u32,
        baseline_ones: bool,
    ) -> &'static [Operand] {
        use Operand::{Marker, Swap};
        // The final target store swaps zero/one. Build its inverse first.
        match (target_digit, baseline_ones) {
            (0, false) => &[Marker, Swap, Swap, Marker],
            (1, true) => &[Marker, Swap, Marker, Swap],
            (2, _) => &[Marker, Swap],
            _ => &[],
        }
    }

    fn tape(
        &mut self,
        target: u32,
        baseline_ones: bool,
    ) -> Result<Vec<u32>, BuildError> {
        let mut tape = Vec::new();
        for digit in ROTATION_ORDER {
            let trit = target
                .checked_div(3u32.pow(digit))
                .and_then(|value| value.checked_rem(3))
                .ok_or(LAYOUT)?;
            for kind in Self::operands_for_digit(trit, baseline_ones) {
                tape.push(self.allocate_operand(digit, *kind)?);
            }
        }
        Ok(tape)
    }

    const fn with_bounds(bounds: TapeBounds) -> Self {
        Self {
            bounds,
            copies: Vec::new(),
            next_slot: bounds.start,
        }
    }
}

/// Tracks only proposed straight-line D positions, not guest values or
/// semantic acceptance. Real VM execution must authenticate every jump.
struct Emitter<'profile> {
    data: u32,
    profile: &'profile ProfileDescriptor,
    source: Vec<u8>,
    source_cells: usize,
    tape_bounds: TapeBounds,
}

impl Emitter<'_> {
    fn append(&mut self, op: LinearOpcode) -> Result<u32, BuildError> {
        let position = self.source.len();
        if position >= self.source_cells {
            return Err(LAYOUT);
        }
        let byte = if op == LinearOpcode::NoOperation {
            canonical_noop_cell(self.profile, position)?
        } else {
            unique_graphical_cell(self.profile, op, position)
                .map_err(|_error| LAYOUT)?
        };
        self.source.push(byte);
        u32::try_from(position).map_err(|_error| LAYOUT)
    }

    fn append_indirect(&mut self) -> Result<u32, BuildError> {
        let position = self.source.len();
        if position >= self.source_cells {
            return Err(LAYOUT);
        }
        let address = u32::try_from(position).map_err(|_error| LAYOUT)?;
        let byte = encode_code_visits(self.profile, address, &[
            CodeVisitRequirement::Decoded(b'i'),
        ])
        .map_err(|_error| LAYOUT)?;
        self.source.push(byte);
        Ok(address)
    }

    fn append_route(&mut self, route: &[u8]) -> Result<(), BuildError> {
        for opcode in route {
            let _: u32 = self.append(match opcode {
                b'j' => LinearOpcode::RelocateDataPointer,
                b'o' => LinearOpcode::NoOperation,
                _ => return Err(LAYOUT),
            })?;
        }
        Ok(())
    }

    fn finish(mut self) -> Result<Vec<u8>, BuildError> {
        let tail = self.source_cells.checked_sub(2).ok_or(LAYOUT)?;
        if self.source.len() > tail {
            return Err(LAYOUT);
        }
        while self.source.len() < tail {
            let _: u32 = self.append(LinearOpcode::NoOperation)?;
        }
        for byte in [39, 37] {
            let _: u32 = self.append(LinearOpcode::SkippedDataByte { byte })?;
        }
        for (address, expected) in [
            (FRAME, 37),
            (FRAME_RESET, 7_174_416),
            (self.tape_bounds.start, 37),
            (self.tape_bounds.limit, 37),
        ] {
            let cell = usize::try_from(address).map_err(|_error| LAYOUT)?;
            if unwritten_loader_word(&self.source, cell, self.profile)
                .map_err(|_error| LAYOUT)?
                != expected
            {
                return Err(LAYOUT);
            }
        }
        Ok(self.source)
    }

    fn go(&mut self, target: u32) -> Result<(), BuildError> {
        if self.data > target {
            self.reset()?;
        }
        self.walk(target)
    }

    fn jump(&mut self, landing: u32) -> Result<(), BuildError> {
        let _: u32 = self.append(LinearOpcode::RelocateDataPointer)?;
        self.data = landing;
        Ok(())
    }

    fn linear(&mut self, op: LinearOpcode) -> Result<u32, BuildError> {
        let site = self.append(op)?;
        self.data = self.data.checked_add(1).ok_or(LAYOUT)?;
        Ok(site)
    }

    fn pad_to_entry(
        &mut self,
        entry: usize,
        data: u32,
    ) -> Result<(), BuildError> {
        // The selected indirect transfer encrypts the virgin cell at entry-1.
        if self.source.len() >= entry {
            return Err(LAYOUT);
        }
        while self.source.len() < entry {
            let _: u32 = self.append(LinearOpcode::NoOperation)?;
        }
        self.data = data;
        Ok(())
    }

    fn prepare_odd_pairs(
        &mut self,
        addresses: &[u32],
    ) -> Result<(), BuildError> {
        use LinearOpcode::CrazyData;
        // Starting with A=0, prepare alternating all-one/zero words. All
        // intervening even cells retain their virgin reset pointer.
        for &address in addresses {
            self.walk(address)?;
            let _: u32 = self.linear(CrazyData)?;
            self.walk(address.checked_add(2).ok_or(LAYOUT)?)?;
            let _: u32 = self.linear(CrazyData)?;
        }
        Ok(())
    }

    fn prepare_pair(&mut self) -> Result<(), BuildError> {
        use LinearOpcode::{CrazyData, RotateData};
        // True EOF alone leaves all twos at M7,174,421. Rotating this
        // word preserves it and sets A to all twos. The raw low word
        // then becomes all ones. The high word requires A=0 to do so.
        self.reset()?;
        self.walk(7_174_421)?;
        let _: u32 = self.linear(RotateData)?;
        self.reset()?;
        self.walk(7_174_419)?;
        let _: u32 = self.linear(CrazyData)?;
        let _: u32 = self.linear(CrazyData)?;
        self.reset()?;
        self.walk(7_174_420)?;
        let _: u32 = self.linear(CrazyData)?;
        Ok(())
    }

    fn prepare_tape(&mut self, plan: &TapePlan) -> Result<(), BuildError> {
        use LinearOpcode::{CrazyData, RotateData};
        // Alternate all-one and zero writes to odd virgin loader cells.
        // The intervening even cells remain reusable frame-reset pointers.
        for slot in (plan.bounds.start..plan.next_slot).step_by(4) {
            self.walk(slot)?;
            let _: u32 = self.linear(CrazyData)?;
            self.walk(slot.checked_add(2).ok_or(LAYOUT)?)?;
            let _: u32 = self.linear(CrazyData)?;
        }
        for (rotation, digit) in ROTATION_ORDER.into_iter().enumerate() {
            self.source_marker(if rotation == 0 {
                CrazyData
            } else {
                RotateData
            })?;
            for copy in plan.copies.iter().filter(|copy| copy.digit == digit) {
                self.go(copy.intermediate)?;
                let _: u32 = self.linear(CrazyData)?;
                self.walk(copy.operand)?;
                let _: u32 = self.linear(CrazyData)?;
            }
        }
        Ok(())
    }

    fn reset(&mut self) -> Result<(), BuildError> {
        let reset_cell = if (FRAME..=FRAME_RESET).contains(&self.data) {
            FRAME_RESET
        } else if self.data == BOOT_RETURN {
            7_174_468
        } else if (7_174_468..=self.tape_bounds.limit).contains(&self.data)
            && self.data.is_multiple_of(2)
        {
            self.data
        } else {
            return Err(LAYOUT);
        };
        self.walk(reset_cell)?;
        self.jump(FRAME)
    }

    fn source_marker(&mut self, op: LinearOpcode) -> Result<(), BuildError> {
        // Virgin M7,174,425=37; reached encrypted source cells then route
        // to M121=54, the byte-only halt never fetched in this EOF arm.
        self.reset()?;
        self.walk(7_174_425)?;
        self.jump(38)?;
        self.walk(40)?;
        self.jump(70)?;
        self.jump(116)?;
        self.walk(117)?;
        self.jump(120)?;
        self.walk(121)?;
        let _: u32 = self.linear(op)?;
        // The extended bootstrap wrote M122=7,174,466 before the branch.
        self.jump(BOOT_RETURN)
    }

    fn store_tape(
        &mut self,
        tape: &[u32],
        target: u32,
        baseline: u32,
    ) -> Result<u32, BuildError> {
        self.store_tape_with_anchor(tape, target, (baseline, None))
    }

    fn store_tape_with_anchor(
        &mut self,
        tape: &[u32],
        target: u32,
        (baseline, anchor): (u32, TapeAnchor),
    ) -> Result<u32, BuildError> {
        self.go(baseline)?;
        let _: u32 = self.linear(LinearOpcode::RotateData)?;
        if let Some((address, base)) = anchor {
            self.go(address)?;
            self.jump(base)?;
        }
        for &operand in tape {
            self.walk(operand)?;
            let _: u32 = self.linear(LinearOpcode::CrazyData)?;
        }
        self.go(target)?;
        self.linear(LinearOpcode::CrazyData)
    }

    fn walk(&mut self, target: u32) -> Result<(), BuildError> {
        if target < self.data || target > self.tape_bounds.limit {
            return Err(LAYOUT);
        }
        for _ in self.data..target {
            let _: u32 = self.linear(LinearOpcode::NoOperation)?;
        }
        Ok(())
    }

    fn zero_accumulator(&mut self) -> Result<(), BuildError> {
        self.go(TAPE_ZERO)?;
        let _: u32 = self.linear(LinearOpcode::RotateData)?;
        Ok(())
    }
}

fn canonical_noop_cell(
    profile: &ProfileDescriptor,
    position: usize,
) -> Result<u8, BuildError> {
    let encodings = NOOP_ENCODINGS.get_or_init(|| {
        array::from_fn(|phase| {
            unique_graphical_cell(profile, LinearOpcode::NoOperation, phase)
                .ok()
        })
    });
    encodings
        .get(position.rem_euclid(DECODE_PHASES))
        .copied()
        .flatten()
        .ok_or(LAYOUT)
}

fn extended_prefix(
    profile: &ProfileDescriptor,
) -> Result<RelocatedEofBranchSource, BuildError> {
    use LinearOpcode::{CrazyData, Halt, RelocateDataPointer};
    if profile != current_profile() {
        return Err(BuildError::UnsupportedProfile);
    }
    let mut prefix = build_relocated_eof_branch_source(profile)?;
    let source = &mut prefix.source;
    source.truncate(134);
    for (position, opcode) in [
        (0, RelocateDataPointer),
        (1, RelocateDataPointer),
        (8, CrazyData),
        (10, RelocateDataPointer),
        (16, RelocateDataPointer),
        (38, CrazyData),
        (122, Halt),
    ] {
        let byte = unique_graphical_cell(profile, opcode, position)
            .map_err(|_error| LAYOUT)?;
        *source.get_mut(position).ok_or(LAYOUT)? = byte;
    }
    Ok(prefix)
}

/// Emit a distinct source-loaded signed-EOF branch candidate.
///
/// The bootstrap uses unreachable M122 as a high-memory pointer instead
/// of relying on the old 156-cell source boundary. The EOF arm creates
/// ternary marker operands from M121=54 and virgin loader cells. Every
/// marker copy, trit operation and final adjacent result store executes
/// as a genuine guest instruction. The other arm retains the byte pair
/// and reads again, without implementing a checksum iteration.
///
/// # Errors
///
/// Refuses a noncurrent profile or changed bounded source/tape geometry.
pub fn build_relocated_signed_eof_source(
    profile: &ProfileDescriptor,
) -> Result<RelocatedSignedEofBranchSource, BuildError> {
    use LinearOpcode::{CrazyData, Halt, OutputByte};
    let prefix = extended_prefix(profile)?;
    let mut emitter = Emitter {
        data: 7_174_418,
        profile,
        source: prefix.source,
        source_cells: SOURCE_CELLS,
        tape_bounds: TAPE_BOUNDS,
    };
    let mut tape = TapePlan::new();
    let [low_word, high_word] = encode_i32_cells(u32::MAX);
    let low = tape.tape(low_word, false)?;
    let high = tape.tape(high_word, false)?;
    emitter.prepare_tape(&tape)?;
    emitter.prepare_pair()?;
    let [low_address, high_address] = prefix.input_pair;
    let low_store = emitter.store_tape(&low, low_address, TAPE_ZERO)?;
    let high_store = emitter.store_tape(&high, high_address, TAPE_ZERO)?;
    emitter.zero_accumulator()?;
    emitter.reset()?;
    emitter.walk(7_174_454)?;
    let _site = emitter.linear(CrazyData)?;
    let eof_output_store_code_address = emitter.linear(CrazyData)?;
    let eof_output_code_address = emitter.linear(OutputByte)?;
    let eof_halt_code_address = emitter.append(Halt)?;
    Ok(RelocatedSignedEofBranchSource {
        branch_code_address: prefix.branch_code_address,
        byte_halt_code_address: prefix.byte_halt_code_address,
        byte_input_code_address: prefix.byte_input_code_address,
        class_store_code_address: prefix.class_store_code_address,
        eof_arm_code_address: prefix.eof_arm_code_address,
        eof_halt_code_address,
        eof_output_code_address,
        eof_output_store_code_address,
        eof_store_code_addresses: [low_store, high_store],
        first_input_code_address: prefix.first_input_code_address,
        input_pair: prefix.input_pair,
        output_data_address: prefix.output_data_address,
        source: emitter.finish()?,
        zero_pair: prefix.zero_pair,
    })
}
