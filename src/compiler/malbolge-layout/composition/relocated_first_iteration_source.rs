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
//   - Canonical mask, second input, and one physical phi edge.
// - Must-Not:
//   - Claim general checksum arithmetic, source-frame admission or a loop.
// - Allows:
//   - Inputs: exact current N15 profile.
//   - Outputs: graphical source and proposed physical effect sites.
//   - Side effects: none; normative replay owns acceptance.
// - Split-When:
//   - General physical continuation allocation replaces fixed addresses.
// - Merge-When:
//   - Complete checksum lowering owns both continuations.
// - Summary:
//   - Emit the first-iteration continuation after the shared adder.

use malbolge::ProfileDescriptor;

use super::super::super::LinearOpcode::{
    CrazyData, Halt, InputWord, NoOperation, OutputByte, RelocateDataPointer,
    RotateData,
};
use super::{
    Adder, BuildError, Emitter, FRAME, Geometry, LAYOUT, ONES,
    RelocatedFirstByteAddSource, TapeBounds, TapePlan, ZERO, before, build,
};

const MASK_COUNT: u32 = 364;
const MASK_SCRATCH: u32 = 7_182_001;
const MASK_BOUNDS: TapeBounds = TapeBounds {
    limit: 7_183_501,
    start: 7_174_801,
};
const STAY: u32 = 7_174_541;
const WRAP: u32 = 7_174_551;
const MASK_JOIN: u32 = 7_174_561;
const OFFSET: u32 = 7_174_565;
const LOW_MASKS: [u32; 2] = [7_174_569, 7_174_573];
const FLAG_MASKS: [u32; 4] = [7_174_577, 7_174_581, 7_174_585, 7_174_589];
const ADJUSTED: [u32; 2] = [7_174_593, 7_174_597];
const FLAG: [u32; 2] = [7_174_613, 7_174_617];
const SELECTED: [u32; 2] = [7_174_621, 7_174_625];
// Original block-5 SSA value 18 (offset 34), not an admitted effect.
const MASKED: [u32; 2] = [7_174_451, 7_174_452];
const MASKED_TEMP: u32 = 7_174_633;
const SECOND_BYTE: u32 = 7_174_645;
const SECOND_EOF: u32 = 7_174_655;
const SECOND_RAW: [u32; 2] = [7_174_665, 7_174_669];
const SECOND_CLASS_MASKS: [u32; 4] =
    [7_174_673, 7_174_677, 7_174_681, 7_174_685];
const SECOND_CLASS: [u32; 2] = [7_174_689, 7_174_693];
const SECOND_OUTPUT_TEMP: u32 = 7_174_697;
const SECOND_PAIR_TEMP: u32 = 7_174_701;
// Original block-5 SSA value 19 (offset 36).
const SECOND_PAIR: [u32; 2] = [7_174_453, 7_174_454];
const OUTPUT: u32 = 7_174_455;
const PHI_JOIN: u32 = 7_174_705;
const PHI_TEMPS: [u32; 8] = [
    7_174_709, 7_174_713, 7_174_717, 7_174_721, 7_174_725, 7_174_729,
    7_174_733, 7_174_737,
];
const PHI_SNAPSHOT: [u32; 4] = [7_174_456, 7_174_457, 7_174_458, 7_174_459];
const PHI_DEST: [u32; 4] = [7_174_431, 7_174_432, 7_174_433, 7_174_434];
const HEADER_RAW: [u32; 2] = [7_174_741, 7_174_745];
const HEADER_MASKS: [u32; 4] = [7_174_749, 7_174_753, 7_174_757, 7_174_761];
const HEADER_FLAG: [u32; 2] = [7_174_765, 7_174_769];
const HEADER_BYTE: u32 = 7_174_773;
const HEADER_EOF: u32 = 7_174_783;

const WITH_MASK: Geometry = Geometry {
    bounds: MASK_BOUNDS,
    byte_entry: 160_000,
    cells: 1_129_848,
    count: MASK_COUNT,
    eof_entry: 1_100_000,
    even_entry: 300_000,
    join_entry: 305_000,
    odd_entry: 302_000,
    scratch: MASK_SCRATCH,
};
const STAY_ENTRY: usize = 850_000;
const WRAP_ENTRY: usize = 860_000;
const MASK_JOIN_ENTRY: usize = 870_000;
const PHI_ENTRY: usize = 900_000;
const SECOND_BYTE_ENTRY: usize = 940_000;
const SECOND_EOF_ENTRY: usize = 960_000;
const HEADER_BYTE_ENTRY: usize = 1_000_000;
const HEADER_EOF_ENTRY: usize = 1_010_000;

type ConstantTape = (Vec<u32>, u32, u32);

/// First-iteration probe with canonical masked state and a second read.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct RelocatedFirstIterationSource {
    /// Shared first-read and arithmetic geometry.
    pub addition: RelocatedFirstByteAddSource,
    /// Low six trits of the offset addition.
    pub adjusted_address: u32,
    /// Actual branch on the normalized header current.
    pub header_branch_code_address: u32,
    /// Actual overflow-selected branch.
    pub mask_branch_code_address: u32,
    /// Final canonical low and high store sites, respectively.
    pub mask_store_code_addresses: [u32; 2],
    /// Proposed original mask-result reservation, not a source-frame proof.
    pub masked_pair: [u32; 2],
    /// Scratch overflow Boolean.
    pub overflow_address: u32,
    /// Four actual commit stores in source-edge order.
    pub phi_commit_code_addresses: [u32; 4],
    /// Proposed next-header values (current low/high, checksum low/high).
    pub phi_header_words: [u32; 4],
    /// Four actual snapshot stores in source-edge order.
    pub phi_snapshot_code_addresses: [u32; 4],
    /// Proposed source snapshot reservation.
    pub phi_snapshot_words: [u32; 4],
    /// Backward transfers from the two normalized second-read arms.
    pub phi_transfer_code_addresses: [u32; 2],
    /// Second-byte versus EOF indirect transfer.
    pub second_branch_code_address: u32,
    /// Second successful byte stops before the unfinished second iteration.
    pub second_byte_halt_code_address: u32,
    /// Reached second-byte result stores, low then high.
    pub second_byte_store_code_addresses: [u32; 2],
    /// Actual output after the second EOF.
    pub second_eof_output_code_address: u32,
    /// Actual source output-operand write on second EOF.
    pub second_eof_output_store_code_address: u32,
    /// Reached second-EOF result stores, low then high.
    pub second_eof_store_code_addresses: [u32; 2],
    /// Actual second input.
    pub second_input_code_address: u32,
    /// Proposed source second-result reservation.
    pub second_pair: [u32; 2],
}

#[derive(Clone, Copy)]
struct HeaderSites {
    branch: u32,
    commits: [u32; 4],
    snapshots: [u32; 4],
}

struct InputSites {
    branch: u32,
    input: u32,
}

struct MaskSites {
    branch: u32,
    stores: [u32; 2],
}

struct SecondSites {
    branch: u32,
    byte_halt: u32,
    byte_stores: [u32; 2],
    eof_halt: u32,
    eof_stores: [u32; 2],
    header_branch: u32,
    input: u32,
    output: u32,
    output_store: u32,
    phi_commits: [u32; 4],
    phi_snapshots: [u32; 4],
    phi_transfers: [u32; 2],
}

pub(super) struct IterationSites {
    mask: MaskSites,
    second: SecondSites,
}

pub(super) struct MaskTapes(Vec<ConstantTape>);

impl MaskTapes {
    pub(super) fn allocate(plan: &mut TapePlan) -> Result<Self, BuildError> {
        let mut mask_tapes = Vec::new();
        // For low six trits, preserve via two row-one folds. The high
        // trits of the offset sum are zero or one: row two then row zero
        // maps either to zero. To extract a single arbitrary trit, the
        // four other-digit rows 0,2,2,0 annihilate all three possibilities.
        for (value, address, baseline_ones) in [
            (before(STAY_ENTRY)?, STAY, true),
            (before(WRAP_ENTRY)?, WRAP, true),
            (before(MASK_JOIN_ENTRY)?, MASK_JOIN, true),
            (473, OFFSET, true),
            (14_348_542, LOW_MASKS[0], false),
            (364, LOW_MASKS[1], true),
            (1, FLAG_MASKS[0], true),
            (14_348_905, FLAG_MASKS[1], false),
            (14_348_905, FLAG_MASKS[2], false),
            (1, FLAG_MASKS[3], true),
            (before(SECOND_BYTE_ENTRY)?, SECOND_BYTE, true),
            (before(SECOND_EOF_ENTRY)?, SECOND_EOF, true),
            (0, SECOND_CLASS_MASKS[0], true),
            (14_348_905, SECOND_CLASS_MASKS[1], false),
            (14_348_905, SECOND_CLASS_MASKS[2], false),
            (1, SECOND_CLASS_MASKS[3], true),
            (before(PHI_ENTRY)?, PHI_JOIN, true),
            (1, HEADER_MASKS[0], true),
            (14_348_905, HEADER_MASKS[1], false),
            (14_348_905, HEADER_MASKS[2], false),
            (1, HEADER_MASKS[3], true),
            (before(HEADER_BYTE_ENTRY)?, HEADER_BYTE, true),
            (before(HEADER_EOF_ENTRY)?, HEADER_EOF, true),
        ] {
            let baseline = if baseline_ones {
                ONES
            } else {
                ZERO
            };
            mask_tapes.push((
                plan.tape(value, baseline_ones)?,
                address,
                baseline,
            ));
        }
        Ok(Self(mask_tapes))
    }

    pub(super) fn prepare(emitter: &mut Emitter<'_>) -> Result<(), BuildError> {
        emitter.prepare_odd_pairs(&[
            STAY,
            WRAP,
            MASK_JOIN,
            OFFSET,
            LOW_MASKS[0],
            LOW_MASKS[1],
            FLAG_MASKS[0],
            FLAG_MASKS[1],
            FLAG_MASKS[2],
            FLAG_MASKS[3],
            ADJUSTED[0],
            ADJUSTED[1],
            7_174_601,
            FLAG[0],
            FLAG[1],
            SELECTED[0],
            SELECTED[1],
            MASKED_TEMP,
            SECOND_BYTE,
            SECOND_EOF,
            SECOND_RAW[0],
            SECOND_RAW[1],
            SECOND_CLASS_MASKS[0],
            SECOND_CLASS_MASKS[1],
            SECOND_CLASS_MASKS[2],
            SECOND_CLASS_MASKS[3],
            SECOND_CLASS[0],
            SECOND_CLASS[1],
            SECOND_OUTPUT_TEMP,
            SECOND_PAIR_TEMP,
            PHI_JOIN,
            PHI_TEMPS[0],
            PHI_TEMPS[1],
            PHI_TEMPS[2],
            PHI_TEMPS[3],
            PHI_TEMPS[4],
            PHI_TEMPS[5],
            PHI_TEMPS[6],
            PHI_TEMPS[7],
            HEADER_RAW[0],
            HEADER_RAW[1],
            HEADER_MASKS[0],
            HEADER_MASKS[1],
            HEADER_MASKS[2],
            HEADER_MASKS[3],
            HEADER_FLAG[0],
            HEADER_FLAG[1],
            HEADER_BYTE,
            HEADER_EOF,
        ])?;
        Ok(())
    }

    pub(super) fn store(
        self,
        emitter: &mut Emitter<'_>,
    ) -> Result<(), BuildError> {
        for (tape, address, baseline) in self.0 {
            let _: u32 = emitter.store_tape(&tape, address, baseline)?;
        }
        Ok(())
    }
}

impl IterationSites {
    pub(super) const fn eof_halt(&self) -> u32 {
        self.second.eof_halt
    }
}

struct IterationEmitter<'borrow, 'emitter, 'profile> {
    adder: &'borrow mut Adder<'emitter, 'profile>,
}

impl IterationEmitter<'_, '_, '_> {
    fn classify_second(&mut self) -> Result<InputSites, BuildError> {
        self.adder.go(SECOND_RAW[0].checked_sub(1).ok_or(LAYOUT)?)?;
        let input = self.adder.emitter.linear(InputWord)?;
        let _: u32 = self.copy_to(SECOND_RAW)?;
        // The top trit is zero for all bytes and two for real N15 EOF.
        // Rotate it down, reduce it to 0/1, then restore the raw word.
        for _ in 0u32..14 {
            self.adder.go(SECOND_RAW[1])?;
            let _: u32 = self.adder.emitter.linear(RotateData)?;
        }
        self.fold(&SECOND_CLASS_MASKS)?;
        let _: u32 = self.copy_to(SECOND_CLASS)?;
        self.adder.go(SECOND_RAW[1])?;
        let _: u32 = self.adder.emitter.linear(RotateData)?;
        let branch = self.select(SECOND_CLASS[1], 188)?;

        Ok(InputSites { branch, input })
    }

    fn copy_frame_word(
        &mut self,
        source: u32,
        dest: u32,
        temp: u32,
    ) -> Result<u32, BuildError> {
        self.adder.load(ZERO)?;
        self.adder.go(dest)?;
        let _: u32 = self.adder.emitter.linear(CrazyData)?;
        self.adder.load(source)?;
        self.copy_to([temp, dest])
    }

    fn copy_to(&mut self, cells: [u32; 2]) -> Result<u32, BuildError> {
        self.adder.go(cells[0])?;
        let _: u32 = self.adder.emitter.linear(CrazyData)?;
        self.adder.go(cells[1])?;
        self.adder.emitter.linear(CrazyData)
    }

    fn fold(&mut self, masks: &[u32]) -> Result<(), BuildError> {
        for &address in masks {
            self.adder.go(address)?;
            let _: u32 = self.adder.emitter.linear(CrazyData)?;
        }
        Ok(())
    }

    fn header(&mut self) -> Result<HeaderSites, BuildError> {
        let mut snapshots = [0; 4];
        let mut commits = [0; 4];
        for ((site, source), (dest, temp)) in snapshots
            .iter_mut()
            .zip([SECOND_PAIR[0], SECOND_PAIR[1], MASKED[0], MASKED[1]])
            .zip(PHI_SNAPSHOT.into_iter().zip(PHI_TEMPS))
        {
            *site = self.copy_frame_word(source, dest, temp)?;
        }
        for ((site, source), (dest, temp)) in commits
            .iter_mut()
            .zip(PHI_SNAPSHOT)
            .zip(PHI_DEST.into_iter().zip(PHI_TEMPS.into_iter().skip(4)))
        {
            *site = self.copy_frame_word(source, dest, temp)?;
        }
        // Canonical getchar high words are 0 (byte) or 299 (EOF).
        // Trit five distinguishes these two admitted classes.
        self.adder.load(PHI_DEST[1])?;
        let _: u32 = self.copy_to(HEADER_RAW)?;
        for _ in 0u32..5 {
            self.adder.go(HEADER_RAW[1])?;
            let _: u32 = self.adder.emitter.linear(RotateData)?;
        }
        self.fold(&HEADER_MASKS)?;
        let _: u32 = self.copy_to(HEADER_FLAG)?;
        let branch = self.select(HEADER_FLAG[1], 316)?;
        Ok(HeaderSites {
            branch,
            commits,
            snapshots,
        })
    }

    fn mask(&mut self, sum: u32) -> Result<MaskSites, BuildError> {
        // Adding 3^6 - 256 makes trit six the overflow flag for sums
        // in 0..=511. Its low six trits are sum - 256 on overflow.
        let adjusted = self.adder.add(sum, OFFSET, 7)?;
        self.fold(&LOW_MASKS)?;
        let _: u32 = self.copy_to(ADJUSTED)?;
        for _ in 0u32..6 {
            self.adder.go(adjusted)?;
            let _: u32 = self.adder.emitter.linear(RotateData)?;
        }
        self.fold(&FLAG_MASKS)?;
        let _: u32 = self.copy_to(FLAG)?;
        let branch = self.select(FLAG[1], 84)?;
        self.mask_arm(STAY_ENTRY, STAY, sum)?;
        self.mask_arm(WRAP_ENTRY, WRAP, ADJUSTED[1])?;
        self.adder
            .emitter
            .pad_to_entry(MASK_JOIN_ENTRY, 7_174_562)?;
        let high = self.prepare_byte_pair(MASKED)?;
        self.adder.load(SELECTED[1])?;
        let low = self.copy_to([MASKED_TEMP, MASKED[0]])?;
        Ok(MaskSites {
            branch,
            stores: [low, high],
        })
    }

    fn mask_arm(
        &mut self,
        entry: usize,
        pointer: u32,
        value: u32,
    ) -> Result<(), BuildError> {
        self.adder
            .emitter
            .pad_to_entry(entry, pointer.checked_add(1).ok_or(LAYOUT)?)?;
        self.adder.load(value)?;
        let _: u32 = self.copy_to(SELECTED)?;
        self.adder.go(MASK_JOIN)?;
        let _: u32 = self.adder.emitter.append_indirect()?;
        Ok(())
    }

    fn prepare_byte_pair(&mut self, pair: [u32; 2]) -> Result<u32, BuildError> {
        // The virgin odd/even words contain only zero/one trits. A=0
        // initializes the low word to ones, then A=ones clears high.
        self.adder.load(ZERO)?;
        self.adder.go(pair[0])?;
        let _: u32 = self.adder.emitter.linear(CrazyData)?;
        self.adder.go(pair[1])?;
        self.adder.emitter.linear(CrazyData)
    }

    fn prepare_eof_pair(&mut self, pair: [u32; 2]) -> Result<(), BuildError> {
        for address in pair {
            self.adder.load(ZERO)?;
            self.adder.go(address)?;
            let _: u32 = self.adder.emitter.linear(CrazyData)?;
        }
        Ok(())
    }

    fn second_read(
        &mut self,
        eof_low: &[u32],
        eof_high: &[u32],
    ) -> Result<SecondSites, BuildError> {
        let InputSites { branch, input } = self.classify_second()?;

        self.adder.emitter.pad_to_entry(PHI_ENTRY, 7_174_706)?;
        let HeaderSites {
            branch: header_branch,
            commits: phi_commits,
            snapshots: phi_snapshots,
        } = self.header()?;
        self.adder
            .emitter
            .pad_to_entry(SECOND_BYTE_ENTRY, 7_174_646)?;
        let high = self.prepare_byte_pair(SECOND_PAIR)?;
        self.adder.load(SECOND_RAW[1])?;
        let low = self.copy_to([SECOND_PAIR_TEMP, SECOND_PAIR[0]])?;
        self.adder.go(PHI_JOIN)?;
        let byte_transfer = self.adder.emitter.append_indirect()?;

        self.adder
            .emitter
            .pad_to_entry(SECOND_EOF_ENTRY, 7_174_656)?;
        self.prepare_eof_pair(SECOND_PAIR)?;
        let eof_low_store =
            self.adder
                .emitter
                .store_tape(eof_low, SECOND_PAIR[0], ZERO)?;
        let eof_high_store =
            self.adder
                .emitter
                .store_tape(eof_high, SECOND_PAIR[1], ZERO)?;
        self.adder.go(PHI_JOIN)?;
        let eof_transfer = self.adder.emitter.append_indirect()?;
        self.adder
            .emitter
            .pad_to_entry(HEADER_BYTE_ENTRY, 7_174_774)?;
        let byte_halt = self.adder.emitter.append(Halt)?;
        self.adder
            .emitter
            .pad_to_entry(HEADER_EOF_ENTRY, 7_174_784)?;
        // Read the actual committed checksum phi, not its predecessor.
        self.adder.load(ZERO)?;
        self.adder.go(OUTPUT)?;
        let _: u32 = self.adder.emitter.linear(CrazyData)?;
        self.adder.load(PHI_DEST[2])?;
        let output_store = self.copy_to([SECOND_OUTPUT_TEMP, OUTPUT])?;
        let output = self.adder.emitter.linear(OutputByte)?;
        let eof_halt = self.adder.emitter.append(Halt)?;
        Ok(SecondSites {
            branch,
            byte_halt,
            byte_stores: [low, high],
            eof_halt,
            eof_stores: [eof_low_store, eof_high_store],
            header_branch,
            input,
            output,
            output_store,
            phi_commits,
            phi_snapshots,
            phi_transfers: [byte_transfer, eof_transfer],
        })
    }

    fn select(&mut self, flag: u32, tail: u32) -> Result<u32, BuildError> {
        // Both paths start at D=1/2 and select immutable continuation
        // words ten addresses apart. The flag itself remains intact.
        self.adder.emitter.jump(FRAME)?;
        self.adder.emitter.walk(flag)?;
        let _: u32 = self.adder.emitter.append(RelocateDataPointer)?;
        self.adder
            .emitter
            .append_route(b"oooojojojoooooooooooooooooooooooj")?;
        for _ in 0..tail {
            let _: u32 = self.adder.emitter.append(NoOperation)?;
        }
        self.adder.emitter.append_indirect()
    }
}

/// Emit a first-byte addition, live modulo-256 selection and second read.
///
/// A second EOF returns the stored first-iteration result. A second byte
/// stores its signed input pair but stops before the next iteration. No
/// source effect admission or reusable loop is established. Both arms copy
/// the original backedge words into a separate, first-visit header.
///
/// # Errors
/// Refuses unsupported profiles and exhausted physical layouts.
pub fn build_relocated_first_iteration_source(
    profile: &ProfileDescriptor,
) -> Result<RelocatedFirstIterationSource, BuildError> {
    let (addition, candidate) = build(profile, WITH_MASK, true)?;
    let sites = candidate.ok_or(LAYOUT)?;
    Ok(RelocatedFirstIterationSource {
        addition,
        adjusted_address: ADJUSTED[1],
        header_branch_code_address: sites.second.header_branch,
        mask_branch_code_address: sites.mask.branch,
        mask_store_code_addresses: sites.mask.stores,
        masked_pair: MASKED,
        overflow_address: FLAG[1],
        phi_commit_code_addresses: sites.second.phi_commits,
        phi_header_words: PHI_DEST,
        phi_snapshot_code_addresses: sites.second.phi_snapshots,
        phi_snapshot_words: PHI_SNAPSHOT,
        phi_transfer_code_addresses: sites.second.phi_transfers,
        second_branch_code_address: sites.second.branch,
        second_byte_halt_code_address: sites.second.byte_halt,
        second_byte_store_code_addresses: sites.second.byte_stores,
        second_eof_output_code_address: sites.second.output,
        second_eof_output_store_code_address: sites.second.output_store,
        second_eof_store_code_addresses: sites.second.eof_stores,
        second_input_code_address: sites.second.input,
        second_pair: SECOND_PAIR,
    })
}

pub(super) fn emit_iteration(
    adder: &mut Adder<'_, '_>,
    sum: u32,
    eof_low: &[u32],
    eof_high: &[u32],
) -> Result<IterationSites, BuildError> {
    let mut emitter = IterationEmitter { adder };
    let mask = emitter.mask(sum)?;
    let second = emitter.second_read(eof_low, eof_high)?;
    Ok(IterationSites { mask, second })
}
