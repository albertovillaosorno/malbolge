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

use std::mem;

use malbolge::ProfileDescriptor;

use super::super::super::LinearOpcode::{
    CrazyData, Halt, InputWord, NoOperation, OutputByte, RelocateDataPointer,
    RotateData,
};
use super::super::BOOT_RETURN;
use super::{
    Adder, BuildError, Emitter, FRAME, Geometry, LAYOUT, ONES,
    RelocatedFirstByteAddSource, THREE, TWOS, TapeBounds, TapePlan, ZERO,
    before, build, scratch_address,
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
// Dedicated all-one word initialized by MaskTapes::prepare; unlike ONES,
// the first byte parity lookup never mutates it.
const RESET_ONES: u32 = 7_174_601;
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
const SECOND_PARITY_POINTER: u32 = 7_174_637;
const SECOND_PARITY_NORMALIZER: u32 = 7_174_641;
const SECOND_PARITY_FLAG: u32 = 7_174_777;
const SECOND_PARITY_EVEN: u32 = 7_174_787;
const SECOND_PARITY_ONES: u32 = 7_174_791;
const SECOND_PARITY_ODD: u32 = 7_174_797;
const SECOND_PARITY_WORDS: [u32; 6] = [
    SECOND_PARITY_POINTER,
    SECOND_PARITY_NORMALIZER,
    SECOND_PARITY_FLAG,
    SECOND_PARITY_EVEN,
    SECOND_PARITY_ONES,
    SECOND_PARITY_ODD,
];
// The second high-loader window is displaced by 2 * 3^6. The two
// byte-indexed ranges remain disjoint and retain the same six-word phase.
const SECOND_PARITY_MASK: u32 = 14_347_084;
const SECOND_PARITY_ODD_ENTRY: usize = 1_010_000;
const SECOND_PARITY_EVEN_ENTRY: usize = 1_020_000;

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
const SECOND_ADD_HEADER_EOF_ENTRY: usize = 2_700_000;
const SECOND_ADD_COUNT: u32 = 168;
const SECOND_PARITY_ADD_COUNT: u32 = 336;
const SECOND_PARITY_HEADER_EOF_ENTRY: usize = 4_450_000;
const WITH_SECOND_PARITY_ADD: Geometry = Geometry {
    cells: 4_513_848,
    eof_entry: 4_490_000,
    ..WITH_MASK
};
// The second mask has separate mutable operands and virgin continuations.
// Its scratch bank is reset again; the incremented operand lives beyond it.
const SECOND_MASK_COUNT: u32 = 234;
const SECOND_MASK_STAY: u32 = 7_174_801;
const SECOND_MASK_WRAP: u32 = 7_174_811;
const SECOND_MASK_JOIN: u32 = 7_174_821;
const SECOND_LOW_MASKS: [u32; 2] = [7_174_825, 7_174_829];
const SECOND_FLAG_MASKS: [u32; 4] =
    [7_174_833, 7_174_837, 7_174_841, 7_174_845];
const SECOND_ADJUSTED: [u32; 2] = [7_174_849, 7_174_853];
const SECOND_MASK_FLAG: [u32; 2] = [7_174_857, 7_174_861];
const SECOND_SELECTED: [u32; 2] = [7_174_865, 7_174_869];
const DOUBLE_STAY: u32 = 7_174_873;
const DOUBLE_WRAP: u32 = 7_174_883;
const DOUBLE_JOIN: u32 = 7_174_893;
const DOUBLE_MASKS: [u32; 4] = [7_174_897, 7_174_901, 7_174_905, 7_174_909];
const DOUBLE_FLAG: [u32; 2] = [7_174_913, 7_174_917];
const DOUBLE_SELECTED: [u32; 2] = [7_174_921, 7_174_925];

const SECOND_MASK_STAY_ENTRY: usize = 3_100_000;
const SECOND_MASK_WRAP_ENTRY: usize = 3_115_000;
const SECOND_MASK_JOIN_ENTRY: usize = 3_130_000;
const DOUBLE_STAY_ENTRY: usize = 3_200_000;
const DOUBLE_WRAP_ENTRY: usize = 3_215_000;
const DOUBLE_JOIN_ENTRY: usize = 3_230_000;
const SECOND_MASK_HEADER_EOF_ENTRY: usize = 3_300_000;
const WITH_SECOND_MASK: Geometry = Geometry {
    bounds: TapeBounds {
        limit: 7_184_701,
        start: 7_174_929,
    },
    cells: 3_380_208,
    eof_entry: 3_350_000,
    even_entry: 425_000,
    join_entry: 430_000,
    odd_entry: 427_000,
    scratch: 7_183_201,
    ..WITH_MASK
};
// A fresh continuation, using the same bounded physical data words again.
const THIRD_RAW: [u32; 2] = [7_174_929, 7_174_933];
const THIRD_CLASS_MASKS: [u32; 4] =
    [7_174_937, 7_174_941, 7_174_945, 7_174_949];
const THIRD_CLASS: [u32; 2] = [7_174_953, 7_174_957];
const THIRD_BYTE: u32 = 7_174_961;
const THIRD_EOF: u32 = 7_174_971;
const THIRD_JOIN: u32 = 7_174_981;
const THIRD_HEADER_MASKS: [u32; 4] =
    [7_174_985, 7_174_989, 7_174_993, 7_174_997];
const THIRD_HEADER_RAW: [u32; 2] = [7_175_001, 7_175_005];
const THIRD_HEADER_FLAG: [u32; 2] = [7_175_009, 7_175_013];
const THIRD_HEADER_BYTE: u32 = 7_175_017;
const THIRD_HEADER_EOF: u32 = 7_175_027;
const THIRD_BYTE_ENTRY: usize = 3_900_000;
const THIRD_EOF_ENTRY: usize = 3_940_000;
const THIRD_JOIN_ENTRY: usize = 3_980_000;
const THIRD_HEADER_BYTE_ENTRY: usize = 4_050_000;
const THIRD_HEADER_EOF_ENTRY: usize = 4_090_000;
const WITH_THIRD_READ: Geometry = Geometry {
    bounds: TapeBounds {
        limit: 7_187_001,
        start: 7_175_031,
    },
    byte_entry: 230_000,
    cells: 4_350_006,
    eof_entry: 4_300_000,
    even_entry: 620_000,
    join_entry: 630_000,
    odd_entry: 625_000,
    scratch: 7_185_501,
    ..WITH_MASK
};
// Four folds retain six arbitrary low trits; four more isolate parity.
const HALF_LOW_MASKS: [[u32; 4]; 2] = [
    [7_174_801, 7_174_805, 7_174_809, 7_174_813],
    [7_174_833, 7_174_837, 7_174_841, 7_174_845],
];
const HALF_BIT_MASKS: [[u32; 4]; 2] = [
    [7_174_817, 7_174_821, 7_174_825, 7_174_829],
    [7_174_849, 7_174_853, 7_174_857, 7_174_861],
];
const HALF_COUNT: u32 = 132;
// After each division the maximum input halves. Inclusive prefix parity
// needs only enough stages to cover its remaining ternary digits.
const XOR_PREFIX_COUNTS: [u32; 8] = [3, 3, 2, 2, 2, 1, 1, 0];
const PREFIX_SHIFTS: [u32; 3] = [1, 2, 4];
const BOOL_XOR: &[u8] = b"0sxsysys2psxpppp";
const HALF_QUOTIENT: &[u8] = b"xsxsys2ppp";
const WITH_ODD_HALF: Geometry = Geometry {
    bounds: TapeBounds {
        limit: 7_184_701,
        start: 7_174_865,
    },
    cells: 2_240_082,
    eof_entry: 2_200_000,
    even_entry: 425_000,
    join_entry: 430_000,
    odd_entry: 427_000,
    scratch: 7_183_201,
    ..WITH_MASK
};
// Full decomposition reuses one dirty bank across eight binary positions.
// Table indices use trits 1..=4 with digits 0/2, preserving odd data
// addresses and the virgin reset word immediately after each entry.
const XOR_QUOTIENTS: [u32; 2] = [7_174_865, 7_174_869];
const XOR_COPY_TEMP: u32 = 7_174_873;
const XOR_BITS: [u32; 8] = [
    7_174_877, 7_174_881, 7_174_885, 7_174_889, 7_174_893, 7_174_897,
    7_174_901, 7_174_905,
];
const XOR_TABLE_BASES: [u32; 2] = [7_175_304, 7_175_790];
const XOR_TABLE_BASE_WORDS: [u32; 2] = [7_174_909, 7_174_913];
const XOR_RESULT: u32 = 7_174_933;
const XOR_NIBBLES: [[u32; 2]; 2] =
    [[7_174_917, 7_174_921], [7_174_925, 7_174_929]];
// Immutable complements under the row-one crazy involution. The
// mutable half masks can be reset to ones and restored by one final fold.
const XOR_MASK_RESTORE: [u32; 4] = [7_174_937, 7_174_941, 7_174_945, 7_174_949];
const XOR_MASK_COMPLEMENTS: [u32; 4] =
    [7_174_089, 14_348_178, 7_174_452, 14_348_904];
const XOR_RECONSTRUCTION_COUNT: u32 = 128;
const XOR_SUM_COUNT: u32 = 120;
const XOR_INCREMENT_COUNT: u32 = 92;
// The odd increment overflows precisely for XOR bytes 253, 254 and 255.
const XOR_UPDATE_FLAG: [u32; 2] = [7_174_953, 7_174_957];
const XOR_UPDATE_STAY: u32 = 7_174_963;
const XOR_UPDATE_WRAP: u32 = 7_174_973;
const XOR_UPDATE_JOIN: u32 = 7_174_983;
const XOR_UPDATE_SELECTED: [u32; 2] = [7_174_987, 7_174_991];
const XOR_UPDATE_RESIDUAL: [u32; 2] = [7_174_995, 7_174_999];
const XOR_UPDATE_STAY_ENTRY: usize = 4_570_000;
const XOR_UPDATE_WRAP_ENTRY: usize = 4_590_000;
const XOR_UPDATE_JOIN_ENTRY: usize = 4_610_000;
const XOR_UPDATE_PREDICATE_COUNT: u32 = 76;
const BOOL_AND: &[u8] = b"xsxsxpsys2ppp";
const BOOL_OR: &[u8] = b"xs2psxs2psypp";
const XOR_WRAP_RESIDUAL: &[u8] = b"xsysxs2ppp";
const WITH_ODD_XOR: Geometry = Geometry {
    bounds: TapeBounds {
        limit: 7_192_001,
        start: 7_176_035,
    },
    byte_entry: 200_000,
    cells: 4_750_164,
    eof_entry: 4_725_000,
    even_entry: 930_000,
    join_entry: 935_000,
    odd_entry: 932_000,
    scratch: 7_190_001,
    ..WITH_MASK
};
const WITH_ODD_UPDATE: Geometry = Geometry {
    even_entry: 960_000,
    join_entry: 965_000,
    odd_entry: 962_000,
    ..WITH_ODD_XOR
};
const WITH_ODD_READ: Geometry = Geometry {
    byte_entry: 240_000,
    eof_entry: 4_710_000,
    even_entry: 1_225_000,
    join_entry: 1_230_000,
    odd_entry: 1_227_000,
    ..WITH_ODD_UPDATE
};
// Keep all new writable words beyond the existing XOR lookup tables.
const COMBINED_OFFSET: u32 = 1_240;
const COMBINED_VALUE: [u32; 2] = [7_176_271, 7_176_275];
const COMBINED_INCREMENT: [u32; 2] = [7_176_279, 7_176_283];
const COMBINED_JOIN: u32 = 7_176_287;
const COMBINED_JOIN_ENTRY: usize = 4_750_000;
const COMBINED_INCREMENT_COUNT: u32 = 112;
const COMBINED_EVEN_ENTRY: usize = 4_510_000;
const WITH_COMBINED_READ: Geometry = Geometry {
    bounds: TapeBounds {
        limit: 7_195_001,
        start: 7_176_291,
    },
    byte_entry: 280_000,
    cells: 6_100_098,
    eof_entry: 6_060_000,
    even_entry: 1_610_000,
    join_entry: 1_620_000,
    odd_entry: 1_615_000,
    scratch: 7_193_001,
    ..WITH_MASK
};
const WITH_SECOND_ADD: Geometry = Geometry {
    cells: 2_821_848,
    eof_entry: 2_800_000,
    ..WITH_MASK
};

#[derive(Clone, Copy)]
pub(super) enum IterationMode {
    First,
    SecondAdd,
    SecondCombinedRead,
    SecondEvenMask,
    SecondEvenRead,
    SecondOddHalf,
    SecondOddRead,
    SecondOddUpdate,
    SecondOddXor,
    SecondParityAdd,
}

impl IterationMode {
    fn first_entry(self, entry: usize) -> Result<usize, BuildError> {
        if self.is_combined() {
            entry.checked_add(1_300_000).ok_or(LAYOUT)
        } else if self.has_odd_read() {
            entry.checked_add(895_000).ok_or(LAYOUT)
        } else if self.has_odd_update() {
            entry.checked_add(630_000).ok_or(LAYOUT)
        } else if self.has_odd_xor() {
            entry.checked_add(600_000).ok_or(LAYOUT)
        } else if self.has_third_read() {
            entry.checked_add(300_000).ok_or(LAYOUT)
        } else if self.has_second_mask() || self.has_odd_half() {
            entry.checked_add(90_000).ok_or(LAYOUT)
        } else {
            Ok(entry)
        }
    }

    const fn has_odd_half(self) -> bool {
        matches!(
            self,
            Self::SecondCombinedRead
                | Self::SecondOddHalf
                | Self::SecondOddXor
                | Self::SecondOddUpdate
                | Self::SecondOddRead
        )
    }

    const fn has_odd_xor(self) -> bool {
        matches!(
            self,
            Self::SecondCombinedRead
                | Self::SecondOddXor
                | Self::SecondOddUpdate
                | Self::SecondOddRead
        )
    }

    const fn has_odd_update(self) -> bool {
        matches!(self, Self::SecondOddUpdate | Self::SecondOddRead)
    }

    const fn has_odd_read(self) -> bool {
        matches!(self, Self::SecondOddRead)
    }

    const fn update_entries(self) -> [usize; 3] {
        if self.has_odd_read() {
            [4_370_000, 4_385_000, 4_400_000]
        } else {
            [
                XOR_UPDATE_STAY_ENTRY,
                XOR_UPDATE_WRAP_ENTRY,
                XOR_UPDATE_JOIN_ENTRY,
            ]
        }
    }

    const fn has_second_mask(self) -> bool {
        matches!(
            self,
            Self::SecondCombinedRead
                | Self::SecondEvenMask
                | Self::SecondEvenRead
        )
    }

    const fn has_second_parity(self) -> bool {
        matches!(
            self,
            Self::SecondCombinedRead
                | Self::SecondParityAdd
                | Self::SecondEvenMask
                | Self::SecondEvenRead
                | Self::SecondOddHalf
                | Self::SecondOddRead
                | Self::SecondOddUpdate
                | Self::SecondOddXor
        )
    }

    const fn has_third_read(self) -> bool {
        matches!(self, Self::SecondCombinedRead | Self::SecondEvenRead)
    }

    const fn is_combined(self) -> bool {
        matches!(self, Self::SecondCombinedRead)
    }

    const fn mask_address(self, address: u32) -> u32 {
        if self.is_combined() {
            address.saturating_add(COMBINED_OFFSET)
        } else {
            address
        }
    }

    fn mask_words<const N: usize>(self, addresses: [u32; N]) -> [u32; N] {
        addresses.map(|address| self.mask_address(address))
    }

    const fn third_layout(self) -> ThirdLayout {
        if self.is_combined() {
            ThirdLayout::COMBINED
        } else if self.has_odd_read() {
            ThirdLayout::ODD
        } else {
            ThirdLayout::EVEN
        }
    }

    const fn header_eof_entry(self) -> usize {
        match self {
            Self::First => HEADER_EOF_ENTRY,
            Self::SecondAdd => SECOND_ADD_HEADER_EOF_ENTRY,
            Self::SecondCombinedRead => 6_040_000,
            Self::SecondParityAdd => SECOND_PARITY_HEADER_EOF_ENTRY,
            Self::SecondEvenMask => SECOND_MASK_HEADER_EOF_ENTRY,
            Self::SecondEvenRead => 4_150_000,
            Self::SecondOddHalf => 2_150_000,
            Self::SecondOddXor
            | Self::SecondOddUpdate
            | Self::SecondOddRead => 4_705_000,
        }
    }

    fn second_even_entry(self) -> Result<usize, BuildError> {
        if self.is_combined() {
            Ok(COMBINED_EVEN_ENTRY)
        } else if self.has_odd_xor() {
            Ok(4_685_000)
        } else if self.has_odd_half() {
            Ok(2_100_000)
        } else {
            self.first_entry(SECOND_PARITY_EVEN_ENTRY)
        }
    }

    fn second_mask_entry(self, entry: usize) -> Result<usize, BuildError> {
        if self.is_combined() {
            entry.checked_add(2_550_000).ok_or(LAYOUT)
        } else if self.has_third_read() {
            entry.checked_add(600_000).ok_or(LAYOUT)
        } else {
            Ok(entry)
        }
    }
}

#[derive(Clone, Copy)]
struct ThirdLayout {
    offset: u32,
    entries: [usize; 5],
}

impl ThirdLayout {
    const COMBINED: Self = Self {
        offset: COMBINED_OFFSET,
        entries: [5_850_000, 5_890_000, 5_930_000, 6_000_000, 6_020_000],
    };
    const EVEN: Self = Self {
        offset: 0,
        entries: [
            THIRD_BYTE_ENTRY,
            THIRD_EOF_ENTRY,
            THIRD_JOIN_ENTRY,
            THIRD_HEADER_BYTE_ENTRY,
            THIRD_HEADER_EOF_ENTRY,
        ],
    };
    const ODD: Self = Self {
        offset: 76,
        entries: [4_430_000, 4_450_000, 4_480_000, 4_550_000, 4_590_000],
    };

    const fn address(self, address: u32) -> u32 {
        address + self.offset
    }

    fn words<const N: usize>(self, addresses: [u32; N]) -> [u32; N] {
        addresses.map(|address| self.address(address))
    }
}

type CombinedArithmeticSites = (SecondMaskSites, CombinedSites);
type ConstantSpec = (u32, u32, bool);
type SecondArithmeticSites = (Option<SecondAddSites>, Option<SecondMaskSites>);
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

/// Actual physical sites for a dirty-word reset and copy.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct DirtyPhiCopySites {
    /// Three resets of the destination in execution order.
    pub destination_resets: [u32; 3],
    /// Final destination store.
    pub destination_store: u32,
    /// Three resets of the intermediate word in execution order.
    pub temporary_resets: [u32; 3],
    /// First, encoded store to the intermediate word.
    pub temporary_store: u32,
}

/// First-iteration image extended with two dirty copies at the byte arm.
/// Each copy uses the same temporary and destination, but fresh code cells.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct RelocatedDirtyPhiSource {
    /// Physical sites for the overwrite and restoration, respectively.
    pub copies: [DirtyPhiCopySites; 2],
    /// Original header checksum low-word address, overwritten and restored.
    pub destination_address: u32,
    /// Extended first-iteration image; the byte halt moves to the end.
    pub iteration: RelocatedFirstIterationSource,
    /// Exact all-one, all-two and zero constant addresses used for reset.
    pub reset_constants: [u32; 3],
    /// Source addresses for the two copies.
    pub source_addresses: [u32; 2],
    /// Previously written phi-copy temporary, reused by both copies.
    pub temporary_address: u32,
}

/// A reused arithmetic scratch word and its three actual reset sites.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct ScratchResetSite {
    /// Data address of the reused word.
    pub address: u32,
    /// Three physical reset stores in execution order.
    pub code_addresses: [u32; 3],
}

/// Physical unsigned addition after the first committed header.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct RelocatedSecondAddSource {
    /// First iteration and actual second-byte entry, with relocated EOF arms.
    pub iteration: RelocatedFirstIterationSource,
    /// Scratch reset effects, each triple in execution order.
    pub scratch_resets: Vec<ScratchResetSite>,
    /// Actual unmasked sum of the committed checksum and second byte.
    pub sum_address: u32,
}

/// A live second-byte parity branch followed by the actual even addition.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct RelocatedSecondParityAddSource {
    /// The existing second-addition candidate, now reachable only on even
    /// bytes.
    pub addition: RelocatedSecondAddSource,
    /// Reached branch selecting the even or odd byte continuation.
    pub branch_code_address: u32,
    /// First code cell of the even addition arm.
    pub even_entry: u32,
    /// Full even-arm sum plus three, before canonical masking.
    pub incremented_address: u32,
    /// Real rotate of the selected second lookup word.
    pub lookup_code_address: u32,
    /// Odd path halts before the unfinished XOR.
    pub odd_halt_code_address: u32,
    /// Boolean parity data word.
    pub parity_address: u32,
    /// Actual Boolean parity store.
    pub parity_store_code_address: u32,
    /// Data pointer selected from the second high-loader window.
    pub pointer_address: u32,
    /// Real store of the byte-indexed second lookup pointer.
    pub pointer_store_code_address: u32,
}

/// Second even arithmetic with an actual canonical modulo-256 result.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct RelocatedSecondEvenMaskSource {
    /// First wrap branch and the second (double-wrap) branch.
    pub branch_code_addresses: [u32; 2],
    /// Both exact Boolean selectors.
    pub flag_addresses: [u32; 2],
    /// Actual low-word stores for the two selectors.
    pub flag_store_code_addresses: [u32; 2],
    /// Both parity landings and the arithmetic sites. The earlier sum
    /// word is reused during masking; the incremented sum survives.
    pub parity: RelocatedSecondParityAddSource,
    /// Residual after at most one subtraction.
    pub residual_address: u32,
    /// Both final canonical stores, low then high.
    pub result_copies: [DirtyPhiCopySites; 2],
    /// The original mask-result SSA reservation, now written again.
    pub result_pair: [u32; 2],
    /// Dirty arithmetic scratch reset again before the mask.
    pub scratch_resets: Vec<ScratchResetSite>,
}

/// A bounded two-update even-path candidate, with actual third input.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct RelocatedSecondEvenReadSource {
    /// Canonical second checksum and earlier physical sites. The nested
    /// second-byte halt now refers to the unfinished third-byte halt.
    pub mask: RelocatedSecondEvenMaskSource,
    /// The third raw input's actual byte/EOF transfer.
    pub third_branch_code_address: u32,
    /// Final halt on a third successful input, before its arithmetic.
    pub third_byte_halt_code_address: u32,
    /// Actual byte-path normalization stores.
    pub third_byte_stores: [DirtyPhiCopySites; 2],
    /// Actual third-input class Boolean store.
    pub third_class_store: u32,
    /// Halt after the third EOF output.
    pub third_eof_halt_code_address: u32,
    /// Actual terminal output, only after the third read sees EOF.
    pub third_eof_output_code_address: u32,
    /// Actual terminal output operand store.
    pub third_eof_output_store: u32,
    /// Three dirty reset sites for each EOF pair word.
    pub third_eof_resets: [[u32; 3]; 2],
    /// Third-read canonical EOF stores.
    pub third_eof_stores: [u32; 2],
    /// The second dirty header's selector transfer.
    pub third_header_branch_code_address: u32,
    /// The second dirty header's class Boolean store.
    pub third_header_class_store: u32,
    /// Actual third input instruction.
    pub third_input_code_address: u32,
    /// Dirty commit copies in source-edge order.
    pub third_phi_commits: [DirtyPhiCopySites; 4],
    /// Dirty snapshot copies in source-edge order.
    pub third_phi_snapshots: [DirtyPhiCopySites; 4],
    /// Both normalizers' actual transfer to the dirty phi edge.
    pub third_phi_transfers: [u32; 2],
}

/// Both second parity arms converge before one canonical update and read.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct RelocatedSecondCombinedReadSource {
    /// Both physical arithmetic-result stores, even then odd.
    pub arm_stores: [u32; 2],
    /// Both physical transfers to the common increment, even then odd.
    pub arm_transfers: [u32; 2],
    /// Common increment word and physical store site.
    pub increment: (u32, u32),
    /// Shared first-iteration image and its initial EOF paths.
    pub iteration: RelocatedFirstIterationSource,
    /// Shared wrap selection branches, in execution order.
    pub mask_branches: [u32; 2],
    /// Canonical checksum pair writes after shared masking.
    pub mask_copies: [DirtyPhiCopySites; 2],
    /// Both wrap flag stores.
    pub mask_flag_stores: [u32; 2],
    /// Actual second parity selection.
    pub parity_branch: u32,
    /// Actual second parity flag store.
    pub parity_store: u32,
    /// Shared unincremented result word.
    pub result_word: u32,
    /// Third-byte halt before unfinished arithmetic.
    pub third_byte_halt: u32,
    /// Four committed header stores after the third input.
    pub third_commits: [DirtyPhiCopySites; 4],
    /// Shared final EOF output and halt.
    pub third_eof: [u32; 2],
    /// Common third input instruction.
    pub third_input: u32,
    /// Four physical snapshots before the header commits.
    pub third_snapshots: [DirtyPhiCopySites; 4],
}

/// Physical third-read continuation for the completed odd second-byte arm.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct RelocatedSecondOddReadSource {
    /// Bounded odd checksum update and earlier input evidence.
    pub update: RelocatedSecondOddUpdateSource,
    /// Third input and physical normalized-class dispatch.
    pub third_input_code_address: u32,
    /// Actual raw input class store.
    pub third_class_store: u32,
    /// Actual byte/EOF dispatch.
    pub third_branch_code_address: u32,
    /// Byte normalization dirty copies.
    pub third_byte_stores: [DirtyPhiCopySites; 2],
    /// EOF normalization resets.
    pub third_eof_resets: [[u32; 3]; 2],
    /// EOF normalization stores.
    pub third_eof_stores: [u32; 2],
    /// Both phi transfers.
    pub third_phi_transfers: [u32; 2],
    /// Four dirty phi snapshots.
    pub third_phi_snapshots: [DirtyPhiCopySites; 4],
    /// Four dirty phi commits.
    pub third_phi_commits: [DirtyPhiCopySites; 4],
    /// Committed-header class store.
    pub third_header_class_store: u32,
    /// Committed-header class dispatch.
    pub third_header_branch_code_address: u32,
    /// Terminal output operand store.
    pub third_eof_output_store: u32,
    /// Terminal EOF output instruction.
    pub third_eof_output_code_address: u32,
    /// Third EOF halt.
    pub third_eof_halt_code_address: u32,
    /// Third byte halt before arithmetic.
    pub third_byte_halt_code_address: u32,
}

struct ThirdByteSites {
    stores: [DirtyPhiCopySites; 2],
    transfer: u32,
}

struct ThirdEofSites {
    resets: [[u32; 3]; 2],
    stores: [u32; 2],
    transfer: u32,
}

struct ThirdHeaderSites {
    branch: u32,
    class_store: u32,
    commits: [DirtyPhiCopySites; 4],
    snapshots: [DirtyPhiCopySites; 4],
}

struct ThirdSites {
    branch: u32,
    byte_halt: u32,
    byte_stores: [DirtyPhiCopySites; 2],
    class_store: u32,
    eof: ThirdEofSites,
    eof_halt: u32,
    header: ThirdHeaderSites,
    input: u32,
    output: u32,
    output_store: u32,
    transfers: [u32; 2],
}

/// Odd-second path: one genuine binary decomposition step on both bytes.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct RelocatedSecondOddHalfSource {
    /// Actual parity branch selecting the odd computation.
    pub branch_code_address: u32,
    /// First-iteration image, including earlier EOF and even bypass.
    pub iteration: RelocatedFirstIterationSource,
    /// Low binary XOR bit of the committed checksum and current byte.
    pub low_xor_address: u32,
    /// Physical halt after the odd computation.
    pub odd_halt_code_address: u32,
    /// Both quotients (checksum, current) after division by two.
    pub quotient_addresses: [u32; 2],
    /// Both canonical remainders (checksum, current).
    pub remainder_addresses: [u32; 2],
    /// Final copy stores: checksum quotient/remainder, byte
    /// quotient/remainder, XOR bit.
    pub result_store_code_addresses: [u32; 5],
    /// All reused scratch words and ordered reset effects.
    pub scratch_resets: Vec<ScratchResetSite>,
}

type HalfMasks = ([u32; 4], [u32; 4]);
type ResultCopy = (u32, u32);
type HalfCopies = [ResultCopy; 2];

/// One physical division/remainder and bit-preservation stage.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct OddXorStepSites {
    /// Binary XOR bit store, preserved before scratch reuse.
    pub bit_copy: DirtyPhiCopySites,
    /// Both binary quotients copied to persistent words.
    pub quotient_copies: [DirtyPhiCopySites; 2],
    /// Mask resets and restored constant stores before the division.
    pub mask_restores: Vec<(ScratchResetSite, u32)>,
    /// All five intermediate result addresses and reached stores.
    pub result_words: [(u32, u32); 5],
    /// Actual reset effects before this arithmetic stage.
    pub scratch_resets: Vec<ScratchResetSite>,
}

/// Full physical odd-arm XOR, prior to increment and mask.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct RelocatedSecondOddXorSource {
    /// Actual parity branch selecting the odd computation.
    pub branch_code_address: u32,
    /// First-iteration image including the earlier bypasses.
    pub iteration: RelocatedFirstIterationSource,
    /// Eight persistent XOR bit words, in increasing binary significance.
    pub bit_addresses: [u32; 8],
    /// Physical halt on the odd path, after any selected update.
    pub odd_halt_code_address: u32,
    /// Two lookup-site pairs (the second store restores the table word).
    pub table_lookups: [[u32; 2]; 2],
    /// Two physical nibble result addresses and stores.
    pub nibble_results: [(u32, u32); 2],
    /// Reused temporary for dirty quotient and bit copies.
    pub copy_temporary_address: u32,
    /// Both persistent quotient words.
    pub quotient_addresses: [u32; 2],
    /// Resets for packed nibble reconstruction and the final sum.
    pub reconstruction_resets: Vec<ScratchResetSite>,
    /// Eight successive stages of real quotient/remainder computation.
    pub steps: Vec<OddXorStepSites>,
    /// Final reconstructed XOR word.
    pub xor_address: u32,
    /// Dirty reset/copy sites for the reconstructed XOR word.
    pub xor_copy: DirtyPhiCopySites,
    /// Resets before the final nibble sum.
    pub sum_resets: Vec<ScratchResetSite>,
}

/// Odd second-byte XOR, increment, and canonical masked storage.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct RelocatedSecondOddUpdateSource {
    /// The actual eight-bit XOR computation before the update.
    pub xor: RelocatedSecondOddXorSource,
    /// All resets before evaluating the overflow predicate.
    pub predicate_resets: Vec<ScratchResetSite>,
    /// All resets before adding three.
    pub increment_resets: Vec<ScratchResetSite>,
    /// Actual Boolean overflow address and final store.
    pub flag: (u32, u32),
    /// Actual overflow-selected branch.
    pub branch_code_address: u32,
    /// Candidate residual address and actual store.
    pub residual: (u32, u32),
    /// Incremented, still-unmasked checksum word.
    pub incremented_address: u32,
    /// Canonical source mask pair.
    pub result_pair: [u32; 2],
    /// The actual dirty copies to the canonical low and high words.
    pub result_copies: [DirtyPhiCopySites; 2],
}

struct OddUpdateSites {
    branch: u32,
    flag: u32,
    incremented: u32,
    increment_resets: Vec<ScratchResetSite>,
    predicate_resets: Vec<ScratchResetSite>,
    residual: u32,
    result_copies: [DirtyPhiCopySites; 2],
}

struct OddXorSites {
    lookups: [[u32; 2]; 2],
    nibbles: [(u32, u32); 2],
    reconstruction_resets: Vec<ScratchResetSite>,
    steps: Vec<OddXorStepSites>,
    sum_resets: Vec<ScratchResetSite>,
    xor: u32,
    xor_copy: DirtyPhiCopySites,
}

struct OddHalfSites {
    low_xor: u32,
    quotients: [u32; 2],
    remainders: [u32; 2],
    resets: Vec<ScratchResetSite>,
    result_stores: [u32; 5],
}

struct SecondMaskSites {
    branches: [u32; 2],
    copies: [DirtyPhiCopySites; 2],
    flag_stores: [u32; 2],
    resets: Vec<ScratchResetSite>,
}

struct CombinedArmSites {
    store: u32,
    transfer: u32,
}

struct CombinedSites {
    even: CombinedArmSites,
    increment_store: u32,
}

struct SecondParitySites {
    branch: u32,
    combined_odd: Option<CombinedArmSites>,
    half: Option<OddHalfSites>,
    xor: Option<OddXorSites>,
    update: Option<OddUpdateSites>,
    lookup: u32,
    odd_halt: Option<u32>,
    parity_store: u32,
    pointer_store: u32,
}

struct SecondAddSites {
    incremented: Option<u32>,
    scratch_resets: Vec<ScratchResetSite>,
    sum_address: u32,
}

#[derive(Clone, Copy)]
struct HeaderSites {
    branch: u32,
    commits: [u32; 4],
    snapshots: [u32; 4],
}

struct InputSites {
    branch: u32,
    class_store: u32,
    input: u32,
}

struct MaskSites {
    branch: u32,
    stores: [u32; 2],
}

struct SecondSites {
    addition: Option<SecondAddSites>,
    branch: u32,
    byte_halt: u32,
    byte_stores: [u32; 2],
    combined: Option<CombinedSites>,
    eof_halt: u32,
    eof_stores: [u32; 2],
    header_branch: u32,
    input: u32,
    mask: Option<SecondMaskSites>,
    output: u32,
    output_store: u32,
    parity: Option<SecondParitySites>,
    phi_commits: [u32; 4],
    phi_snapshots: [u32; 4],
    phi_transfers: [u32; 2],
    third: Option<ThirdSites>,
}

pub(super) struct IterationSites {
    mask: MaskSites,
    second: SecondSites,
}

pub(super) struct MaskTapes(Vec<ConstantTape>);

impl MaskTapes {
    pub(super) fn allocate(
        plan: &mut TapePlan,
        mode: IterationMode,
    ) -> Result<Self, BuildError> {
        let mut constants = Self::first_mask_constants(mode)?;
        if mode.has_second_parity() {
            constants.extend(Self::second_parity_constants(mode)?);
        }
        if mode.has_second_mask() {
            constants.extend(Self::second_mask_constants(mode)?);
        }
        if mode.has_third_read() || mode.has_odd_read() {
            constants.extend(Self::third_constants(mode.third_layout())?);
        }
        if mode.is_combined() {
            constants.push((before(COMBINED_JOIN_ENTRY)?, COMBINED_JOIN, true));
        }
        if mode.has_odd_half() {
            constants.extend(Self::half_constants());
        }
        if mode.has_odd_xor() {
            constants.extend(Self::xor_constants()?);
        }
        if mode.has_odd_update() {
            let [stay, wrap, join] = mode.update_entries();
            constants.extend([
                (before(stay)?, XOR_UPDATE_STAY, true),
                (before(wrap)?, XOR_UPDATE_WRAP, true),
                (before(join)?, XOR_UPDATE_JOIN, true),
            ]);
        }
        let mut mask_tapes = Vec::new();
        for (value, address, baseline_ones) in constants {
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

    fn extend_second_mask_addresses(
        addresses: &mut Vec<u32>,
        mode: IterationMode,
    ) {
        let start = addresses.len();
        addresses.extend([
            SECOND_MASK_STAY,
            SECOND_MASK_WRAP,
            SECOND_MASK_JOIN,
        ]);
        addresses.extend(SECOND_LOW_MASKS);
        addresses.extend(SECOND_FLAG_MASKS);
        addresses.extend(SECOND_ADJUSTED);
        addresses.extend(SECOND_MASK_FLAG);
        addresses.extend(SECOND_SELECTED);
        addresses.extend([DOUBLE_STAY, DOUBLE_WRAP, DOUBLE_JOIN]);
        addresses.extend(DOUBLE_MASKS);
        addresses.extend(DOUBLE_FLAG);
        addresses.extend(DOUBLE_SELECTED);
        for address in addresses.iter_mut().skip(start) {
            *address = mode.mask_address(*address);
        }
    }

    fn extend_third_addresses(addresses: &mut Vec<u32>, layout: ThirdLayout) {
        addresses.extend(layout.words(THIRD_RAW));
        addresses.extend(layout.words(THIRD_CLASS_MASKS));
        addresses.extend(layout.words(THIRD_CLASS));
        addresses.extend(layout.words([THIRD_BYTE, THIRD_EOF, THIRD_JOIN]));
        addresses.extend(layout.words(THIRD_HEADER_MASKS));
        addresses.extend(layout.words(THIRD_HEADER_RAW));
        addresses.extend(layout.words(THIRD_HEADER_FLAG));
        addresses.extend(layout.words([THIRD_HEADER_BYTE, THIRD_HEADER_EOF]));
    }

    fn first_mask_addresses() -> Vec<u32> {
        let mut addresses = vec![STAY, WRAP, MASK_JOIN, OFFSET];
        addresses.extend(LOW_MASKS);
        addresses.extend(FLAG_MASKS);
        addresses.extend(ADJUSTED);
        addresses.push(RESET_ONES);
        addresses.extend(FLAG);
        addresses.extend(SELECTED);
        addresses.extend([MASKED_TEMP, SECOND_BYTE, SECOND_EOF]);
        addresses.extend(SECOND_RAW);
        addresses.extend(SECOND_CLASS_MASKS);
        addresses.extend(SECOND_CLASS);
        addresses.extend([SECOND_OUTPUT_TEMP, SECOND_PAIR_TEMP, PHI_JOIN]);
        addresses.extend(PHI_TEMPS);
        addresses.extend(HEADER_RAW);
        addresses.extend(HEADER_MASKS);
        addresses.extend(HEADER_FLAG);
        addresses.extend([HEADER_BYTE, HEADER_EOF]);
        addresses
    }

    fn first_mask_constants(
        mode: IterationMode,
    ) -> Result<Vec<ConstantSpec>, BuildError> {
        // For low six trits, preserve via two row-one folds. The high
        // trits of the offset sum are zero or one: row two then row zero
        // maps either to zero. To extract a single arbitrary trit, the
        // four other-digit rows 0,2,2,0 annihilate all three possibilities.
        Ok(vec![
            (before(mode.first_entry(STAY_ENTRY)?)?, STAY, true),
            (before(mode.first_entry(WRAP_ENTRY)?)?, WRAP, true),
            (before(mode.first_entry(MASK_JOIN_ENTRY)?)?, MASK_JOIN, true),
            (473, OFFSET, true),
            (14_348_542, LOW_MASKS[0], false),
            (364, LOW_MASKS[1], true),
            (1, FLAG_MASKS[0], true),
            (14_348_905, FLAG_MASKS[1], false),
            (14_348_905, FLAG_MASKS[2], false),
            (1, FLAG_MASKS[3], true),
            (
                before(mode.first_entry(SECOND_BYTE_ENTRY)?)?,
                SECOND_BYTE,
                true,
            ),
            (
                before(mode.first_entry(SECOND_EOF_ENTRY)?)?,
                SECOND_EOF,
                true,
            ),
            (0, SECOND_CLASS_MASKS[0], true),
            (14_348_905, SECOND_CLASS_MASKS[1], false),
            (14_348_905, SECOND_CLASS_MASKS[2], false),
            (1, SECOND_CLASS_MASKS[3], true),
            (before(mode.first_entry(PHI_ENTRY)?)?, PHI_JOIN, true),
            (1, HEADER_MASKS[0], true),
            (14_348_905, HEADER_MASKS[1], false),
            (14_348_905, HEADER_MASKS[2], false),
            (1, HEADER_MASKS[3], true),
            (
                before(mode.first_entry(HEADER_BYTE_ENTRY)?)?,
                HEADER_BYTE,
                true,
            ),
            (before(mode.header_eof_entry())?, HEADER_EOF, true),
        ])
    }

    fn half_constants() -> Vec<ConstantSpec> {
        let mut constants = Vec::new();
        for (low, bit) in HALF_LOW_MASKS.into_iter().zip(HALF_BIT_MASKS) {
            constants.extend(
                [364, 14_348_542, 14_348_542, 364]
                    .into_iter()
                    .zip(low)
                    .zip([true, false, false, true])
                    .map(|((value, address), ones)| (value, address, ones)),
            );
            constants.extend(
                [1, 14_348_905, 14_348_905, 1]
                    .into_iter()
                    .zip(bit)
                    .zip([true, false, false, true])
                    .map(|((value, address), ones)| (value, address, ones)),
            );
        }
        constants
    }

    fn xor_constants() -> Result<Vec<ConstantSpec>, BuildError> {
        let mut constants = XOR_MASK_COMPLEMENTS
            .into_iter()
            .zip(XOR_MASK_RESTORE)
            .map(|(value, address)| (value, address, true))
            .collect::<Vec<_>>();
        for (index, (base, word)) in XOR_TABLE_BASES
            .into_iter()
            .zip(XOR_TABLE_BASE_WORDS)
            .enumerate()
        {
            constants.push((base, word, true));
            let weight = if index == 0 {
                1
            } else {
                16
            };
            for nibble in 0..16u32 {
                constants.push((
                    nibble.checked_mul(weight).ok_or(LAYOUT)?,
                    xor_table_address(base, nibble)?,
                    true,
                ));
            }
        }
        Ok(constants)
    }

    pub(super) fn prepare(
        emitter: &mut Emitter<'_>,
        mode: IterationMode,
    ) -> Result<(), BuildError> {
        let mut addresses = Self::first_mask_addresses();
        if mode.has_second_parity() {
            addresses.extend(SECOND_PARITY_WORDS);
            addresses.sort_unstable();
        }
        if mode.has_second_mask() {
            Self::extend_second_mask_addresses(&mut addresses, mode);
        }
        if mode.has_third_read() || mode.has_odd_read() {
            Self::extend_third_addresses(&mut addresses, mode.third_layout());
        }
        if mode.is_combined() {
            addresses.extend(COMBINED_VALUE);
            addresses.extend(COMBINED_INCREMENT);
            addresses.push(COMBINED_JOIN);
        }
        if mode.has_odd_half() {
            for (low, bit) in HALF_LOW_MASKS.into_iter().zip(HALF_BIT_MASKS) {
                addresses.extend(low);
                addresses.extend(bit);
            }
        }
        if mode.has_odd_xor() {
            addresses.extend(XOR_QUOTIENTS);
            addresses.push(XOR_COPY_TEMP);
            addresses.extend(XOR_BITS);
            addresses.extend(XOR_TABLE_BASE_WORDS);
            addresses.extend(XOR_NIBBLES.into_iter().flatten());
            addresses.push(XOR_RESULT);
            addresses.extend(XOR_MASK_RESTORE);
            for base in XOR_TABLE_BASES {
                for nibble in 0..16u32 {
                    addresses.push(xor_table_address(base, nibble)?);
                }
            }
            addresses.sort_unstable();
        }
        if mode.has_odd_update() {
            addresses.extend(XOR_UPDATE_FLAG);
            addresses.extend([
                XOR_UPDATE_STAY,
                XOR_UPDATE_WRAP,
                XOR_UPDATE_JOIN,
            ]);
            addresses.extend(XOR_UPDATE_SELECTED);
            addresses.extend(XOR_UPDATE_RESIDUAL);
            addresses.sort_unstable();
        }
        emitter.prepare_odd_pairs(&addresses)
    }

    fn second_mask_constants(
        mode: IterationMode,
    ) -> Result<[ConstantSpec; 16], BuildError> {
        Ok([
            (
                before(mode.second_mask_entry(SECOND_MASK_STAY_ENTRY)?)?,
                SECOND_MASK_STAY,
                true,
            ),
            (
                before(mode.second_mask_entry(SECOND_MASK_WRAP_ENTRY)?)?,
                SECOND_MASK_WRAP,
                true,
            ),
            (
                before(mode.second_mask_entry(SECOND_MASK_JOIN_ENTRY)?)?,
                SECOND_MASK_JOIN,
                true,
            ),
            (14_348_542, SECOND_LOW_MASKS[0], false),
            (364, SECOND_LOW_MASKS[1], true),
            (1, SECOND_FLAG_MASKS[0], true),
            (14_348_905, SECOND_FLAG_MASKS[1], false),
            (14_348_905, SECOND_FLAG_MASKS[2], false),
            (1, SECOND_FLAG_MASKS[3], true),
            (
                before(mode.second_mask_entry(DOUBLE_STAY_ENTRY)?)?,
                DOUBLE_STAY,
                true,
            ),
            (
                before(mode.second_mask_entry(DOUBLE_WRAP_ENTRY)?)?,
                DOUBLE_WRAP,
                true,
            ),
            (
                before(mode.second_mask_entry(DOUBLE_JOIN_ENTRY)?)?,
                DOUBLE_JOIN,
                true,
            ),
            (1, DOUBLE_MASKS[0], true),
            (14_348_905, DOUBLE_MASKS[1], false),
            (14_348_905, DOUBLE_MASKS[2], false),
            (1, DOUBLE_MASKS[3], true),
        ]
        .map(|(value, address, ones)| {
            (value, mode.mask_address(address), ones)
        }))
    }

    fn second_parity_constants(
        mode: IterationMode,
    ) -> Result<[ConstantSpec; 5], BuildError> {
        Ok([
            (SECOND_PARITY_MASK, SECOND_PARITY_POINTER, false),
            (14_348_905, SECOND_PARITY_NORMALIZER, false),
            (1, SECOND_PARITY_FLAG, true),
            (before(mode.second_even_entry()?)?, SECOND_PARITY_EVEN, true),
            (
                before(mode.first_entry(SECOND_PARITY_ODD_ENTRY)?)?,
                SECOND_PARITY_ODD,
                true,
            ),
        ])
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

    fn third_constants(
        layout: ThirdLayout,
    ) -> Result<[ConstantSpec; 13], BuildError> {
        let [byte, eof, join, header_byte, header_eof] = layout.entries;
        Ok([
            (0, layout.address(THIRD_CLASS_MASKS[0]), true),
            (14_348_905, layout.address(THIRD_CLASS_MASKS[1]), false),
            (14_348_905, layout.address(THIRD_CLASS_MASKS[2]), false),
            (1, layout.address(THIRD_CLASS_MASKS[3]), true),
            (before(byte)?, layout.address(THIRD_BYTE), true),
            (before(eof)?, layout.address(THIRD_EOF), true),
            (before(join)?, layout.address(THIRD_JOIN), true),
            (1, layout.address(THIRD_HEADER_MASKS[0]), true),
            (14_348_905, layout.address(THIRD_HEADER_MASKS[1]), false),
            (14_348_905, layout.address(THIRD_HEADER_MASKS[2]), false),
            (1, layout.address(THIRD_HEADER_MASKS[3]), true),
            (
                before(header_byte)?,
                layout.address(THIRD_HEADER_BYTE),
                true,
            ),
            (before(header_eof)?, layout.address(THIRD_HEADER_EOF), true),
        ])
    }
}

fn xor_table_address(base: u32, nibble: u32) -> Result<u32, BuildError> {
    let mut address = base.checked_add(1).ok_or(LAYOUT)?;
    for position in 0..4u32 {
        if nibble & (1u32 << position) != 0 {
            address = address
                .checked_add(2 * 3u32.pow(position + 1))
                .ok_or(LAYOUT)?;
        }
    }
    Ok(address)
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
    fn classify_input(
        &mut self,
        raw: [u32; 2],
        masks: &[u32; 4],
        class: ([u32; 2], u32),
    ) -> Result<InputSites, BuildError> {
        let (flag, tail) = class;
        self.adder.go(raw[0].checked_sub(1).ok_or(LAYOUT)?)?;
        let input = self.adder.emitter.linear(InputWord)?;
        let _: u32 = self.copy_to(raw)?;
        // The top trit is zero for all bytes and two for real N15 EOF.
        // Rotate it down, reduce it to 0/1, then restore the raw word.
        for _ in 0u32..14 {
            self.adder.go(raw[1])?;
            let _: u32 = self.adder.emitter.linear(RotateData)?;
        }
        self.fold(masks)?;
        let class_store = self.copy_to(flag)?;
        self.adder.go(raw[1])?;
        let _: u32 = self.adder.emitter.linear(RotateData)?;
        let branch = self.select(flag[1], tail)?;

        Ok(InputSites {
            branch,
            class_store,
            input,
        })
    }

    fn classify_second(&mut self) -> Result<InputSites, BuildError> {
        self.classify_input(
            SECOND_RAW,
            &SECOND_CLASS_MASKS,
            (SECOND_CLASS, 188),
        )
    }

    fn combined_arithmetic(
        &mut self,
        mode: IterationMode,
    ) -> Result<CombinedArithmeticSites, BuildError> {
        let mut even = Adder {
            count: XOR_SUM_COUNT,
            cursor: 0,
            emitter: self.adder.emitter,
            scratch: self.adder.scratch,
        };
        let _even_resets = IterationEmitter { adder: &mut even }
            .reset_scratch(XOR_SUM_COUNT)?;
        let sum = even.add_bounded(PHI_DEST[2], PHI_DEST[0], 6, false)?;
        even.finish()?;
        let even_sites = self.combined_arm(sum)?;
        self.adder.emitter.pad_to_entry(
            COMBINED_JOIN_ENTRY,
            COMBINED_JOIN.checked_add(1).ok_or(LAYOUT)?,
        )?;
        let mut increment = Adder {
            count: COMBINED_INCREMENT_COUNT,
            cursor: 0,
            emitter: self.adder.emitter,
            scratch: self.adder.scratch,
        };
        let mut shared = IterationEmitter { adder: &mut increment };
        let _increment_resets =
            shared.reset_scratch(COMBINED_INCREMENT_COUNT)?;
        let _sum =
            shared
                .adder
                .add_bounded(COMBINED_VALUE[1], THREE, 6, true)?;
        let increment_store = shared.copy_to(COMBINED_INCREMENT)?;
        increment.finish()?;
        let mask = self.second_mask(COMBINED_INCREMENT[1], mode)?;
        Ok((mask, CombinedSites {
            even: even_sites,
            increment_store,
        }))
    }

    fn combined_arm(
        &mut self,
        value: u32,
    ) -> Result<CombinedArmSites, BuildError> {
        self.adder.load(value)?;
        let store = self.copy_to(COMBINED_VALUE)?;
        self.adder.go(COMBINED_JOIN)?;
        let transfer = self.adder.emitter.append_indirect()?;
        Ok(CombinedArmSites { store, transfer })
    }

    fn copy_dirty_word(
        &mut self,
        source: u32,
        dest: u32,
        temp: u32,
    ) -> Result<DirtyPhiCopySites, BuildError> {
        let temporary_resets = self.reset_dirty_word(temp)?;
        let destination_resets = self.reset_dirty_word(dest)?;
        self.adder.load(source)?;
        self.adder.go(temp)?;
        let temporary_store = self.adder.emitter.linear(CrazyData)?;
        self.adder.go(dest)?;
        let destination_store = self.adder.emitter.linear(CrazyData)?;
        Ok(DirtyPhiCopySites {
            destination_resets,
            destination_store,
            temporary_resets,
            temporary_store,
        })
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

    fn copy_result(&mut self) -> Result<ResultCopy, BuildError> {
        let address = self.adder.copy()?;
        let position = self
            .adder
            .emitter
            .source
            .len()
            .checked_sub(1)
            .ok_or(LAYOUT)?;
        let site = u32::try_from(position).map_err(|_error| LAYOUT)?;
        Ok((address, site))
    }

    fn copy_to(&mut self, cells: [u32; 2]) -> Result<u32, BuildError> {
        self.adder.go(cells[0])?;
        let _: u32 = self.adder.emitter.linear(CrazyData)?;
        self.adder.go(cells[1])?;
        self.adder.emitter.linear(CrazyData)
    }

    fn double_wrap(
        &mut self,
        mode: IterationMode,
    ) -> Result<[u32; 2], BuildError> {
        // Each digit is one iff the corresponding residual trit is one.
        // The required places 0,1,2,5 sum to 256, the maximum residual.
        self.adder.evaluate(
            b"0sxsypp",
            RESET_ONES,
            mode.mask_address(SECOND_SELECTED[1]),
        )?;
        let mut conjunction = self.adder.copy()?;
        let aligned = self.adder.copy()?;
        for shift in 1u32..=5 {
            self.adder.go(aligned)?;
            let _: u32 = self.adder.emitter.linear(RotateData)?;
            if matches!(shift, 1 | 2 | 5) {
                self.adder
                    .evaluate(b"xsxsxpsys2ppp", conjunction, aligned)?;
                conjunction = self.adder.copy()?;
            }
        }
        self.fold(&mode.mask_words(DOUBLE_MASKS))?;
        let flag_store = self.copy_to(mode.mask_words(DOUBLE_FLAG))?;
        let branch = self.select(
            mode.mask_address(DOUBLE_FLAG[1]),
            mode.mask_address(416),
        )?;
        self.selected_arm(
            (
                mode.second_mask_entry(DOUBLE_STAY_ENTRY)?,
                mode.mask_address(DOUBLE_STAY),
            ),
            mode.mask_address(SECOND_SELECTED[1]),
            (
                mode.mask_words(DOUBLE_SELECTED),
                mode.mask_address(DOUBLE_JOIN),
            ),
        )?;
        self.selected_arm(
            (
                mode.second_mask_entry(DOUBLE_WRAP_ENTRY)?,
                mode.mask_address(DOUBLE_WRAP),
            ),
            ZERO,
            (
                mode.mask_words(DOUBLE_SELECTED),
                mode.mask_address(DOUBLE_JOIN),
            ),
        )?;
        self.adder.emitter.pad_to_entry(
            mode.second_mask_entry(DOUBLE_JOIN_ENTRY)?,
            mode.mask_address(DOUBLE_JOIN)
                .checked_add(1)
                .ok_or(LAYOUT)?,
        )?;
        Ok([branch, flag_store])
    }

    fn fold(&mut self, masks: &[u32]) -> Result<(), BuildError> {
        for &address in masks {
            self.adder.go(address)?;
            let _: u32 = self.adder.emitter.linear(CrazyData)?;
        }
        Ok(())
    }

    fn halve(
        &mut self,
        value: u32,
        masks: HalfMasks,
        prefix_count: u32,
    ) -> Result<HalfCopies, BuildError> {
        let (low_masks, bit_masks) = masks;
        // Boolean trits for exactly the odd ternary digits.
        self.adder.evaluate(b"0sxsypp", RESET_ONES, value)?;
        let mut prefix = self.adder.copy()?;
        for shift in PREFIX_SHIFTS
            .into_iter()
            .take(usize::try_from(prefix_count).map_err(|_| LAYOUT)?)
        {
            let aligned = self.rotated_copy(prefix, shift)?;
            self.adder.evaluate(BOOL_XOR, prefix, aligned)?;
            prefix = self.adder.copy()?;
        }
        // Exclusive high-prefix parity is the incoming long-division bit.
        let carry = self.rotated_copy(prefix, 1)?;
        self.adder.evaluate(HALF_QUOTIENT, value, carry)?;
        self.fold(&low_masks)?;
        let quotient = self.copy_result()?;
        self.adder.load(prefix)?;
        self.fold(&bit_masks)?;
        let remainder = self.copy_result()?;
        Ok([quotient, remainder])
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

    fn mask(
        &mut self,
        sum: u32,
        mode: IterationMode,
    ) -> Result<MaskSites, BuildError> {
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
        self.mask_arm(mode.first_entry(STAY_ENTRY)?, STAY, sum)?;
        self.mask_arm(mode.first_entry(WRAP_ENTRY)?, WRAP, ADJUSTED[1])?;
        self.adder
            .emitter
            .pad_to_entry(mode.first_entry(MASK_JOIN_ENTRY)?, 7_174_562)?;
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
        self.selected_arm((entry, pointer), value, (SELECTED, MASK_JOIN))
    }

    fn odd_half(&mut self) -> Result<OddHalfSites, BuildError> {
        self.odd_half_values([PHI_DEST[2], PHI_DEST[0]], 3)
    }

    fn odd_half_values(
        &mut self,
        values: [u32; 2],
        prefix_count: u32,
    ) -> Result<OddHalfSites, BuildError> {
        let skipped = 3u32.checked_sub(prefix_count).ok_or(LAYOUT)?;
        let count = HALF_COUNT.checked_sub(28 * skipped).ok_or(LAYOUT)?;
        let mut adder = Adder {
            count,
            cursor: 0,
            emitter: self.adder.emitter,
            scratch: self.adder.scratch,
        };
        let mut half = IterationEmitter { adder: &mut adder };
        let resets = half.reset_scratch(count)?;
        let [left_low, right_low] = HALF_LOW_MASKS;
        let [left_bit, right_bit] = HALF_BIT_MASKS;
        let [
            (left_q, checksum_quotient_site),
            (left_r, checksum_bit_site),
        ] = half.halve(values[0], (left_low, left_bit), prefix_count)?;
        let [(right_q, byte_quotient_site), (right_r, byte_bit_site)] =
            half.halve(values[1], (right_low, right_bit), prefix_count)?;
        half.adder.evaluate(BOOL_XOR, left_r, right_r)?;
        let (low_xor, xor_store) = half.copy_result()?;
        adder.finish()?;
        Ok(OddHalfSites {
            low_xor,
            quotients: [left_q, right_q],
            remainders: [left_r, right_r],
            resets,
            result_stores: [
                checksum_quotient_site,
                checksum_bit_site,
                byte_quotient_site,
                byte_bit_site,
                xor_store,
            ],
        })
    }

    fn odd_xor_step(
        &mut self,
        values: [u32; 2],
        bit: u32,
        restore: bool,
        prefix_count: u32,
    ) -> Result<OddXorStepSites, BuildError> {
        let mask_restores = if restore {
            self.restore_half_masks()?
        } else {
            Vec::new()
        };
        let half = self.odd_half_values(values, prefix_count)?;
        let [left_q, right_q] = half.quotients;
        let [left_r, right_r] = half.remainders;
        let quotient_copies = [
            self.copy_dirty_word(left_q, XOR_QUOTIENTS[0], XOR_COPY_TEMP)?,
            self.copy_dirty_word(right_q, XOR_QUOTIENTS[1], XOR_COPY_TEMP)?,
        ];
        let bit_copy =
            self.copy_dirty_word(half.low_xor, bit, XOR_COPY_TEMP)?;
        let [lq, lr, rq, rr, bx] = half.result_stores;
        Ok(OddXorStepSites {
            bit_copy,
            quotient_copies,
            mask_restores,
            result_words: [
                (left_q, lq),
                (left_r, lr),
                (right_q, rq),
                (right_r, rr),
                (half.low_xor, bx),
            ],
            scratch_resets: half.resets,
        })
    }

    fn restore_half_masks(
        &mut self,
    ) -> Result<Vec<(ScratchResetSite, u32)>, BuildError> {
        let mut restores = Vec::new();
        let [low, high, bit_low, bit_high] = XOR_MASK_RESTORE;
        for (low_masks, bit_masks) in
            HALF_LOW_MASKS.into_iter().zip(HALF_BIT_MASKS)
        {
            for (address, complement) in
                low_masks.into_iter().chain(bit_masks).zip([
                    low, high, high, low, bit_low, bit_high, bit_high, bit_low,
                ])
            {
                let code_addresses = self.reset_dirty_word(address)?;
                self.adder.load(complement)?;
                self.adder.go(address)?;
                let store = self.adder.emitter.linear(CrazyData)?;
                restores.push((
                    ScratchResetSite { address, code_addresses },
                    store,
                ));
            }
        }
        Ok(restores)
    }

    fn lookup_xor_table(
        &mut self,
        pointer: u32,
    ) -> Result<[u32; 2], BuildError> {
        let mut sites = [0; 2];
        // Every selected table cell is odd and is followed by an untouched
        // even loader word that jumps back to FRAME. The two all-two
        // folds restore the table value exactly, just like Adder::load.
        for site in &mut sites {
            self.adder.load(TWOS)?;
            self.adder.go(pointer)?;
            let _: u32 = self.adder.emitter.append(RelocateDataPointer)?;
            *site = self.adder.emitter.append(CrazyData)?;
            self.adder.emitter.jump(FRAME)?;
        }
        Ok(sites)
    }

    fn reconstruct_nibble(
        &mut self,
        bits: [u32; 4],
        base: u32,
        result: [u32; 2],
    ) -> Result<([u32; 2], u32), BuildError> {
        // Disjoint Boolean trits encode a nibble in the table's address.
        let [b0, b1, b2, b3] = bits;
        let mut packed = self.rotated_copy(b0, 14)?;
        for (bit, shift) in [(b1, 13), (b2, 12), (b3, 11)] {
            let aligned = self.rotated_copy(bit, shift)?;
            self.adder.evaluate(BOOL_XOR, packed, aligned)?;
            packed = self.adder.copy()?;
        }
        // 0/1 -> 0/2. Since base is a multiple of 3^5, there is no
        // ternary carry and a single SUM circuit produces base+index.
        self.adder.evaluate(b"xs2p", packed, ZERO)?;
        let encoded = self.adder.copy()?;
        self.adder.evaluate(super::SUM, encoded, base)?;
        let pointer = self.adder.copy()?;
        let sites = self.lookup_xor_table(pointer)?;
        let store = self.copy_to(result)?;
        Ok((sites, store))
    }

    fn odd_xor(&mut self) -> Result<OddXorSites, BuildError> {
        let mut steps = Vec::new();
        let mut values = [PHI_DEST[2], PHI_DEST[0]];
        for (bit, count) in XOR_BITS.into_iter().zip(XOR_PREFIX_COUNTS) {
            steps.push(self.odd_xor_step(
                values,
                bit,
                !steps.is_empty(),
                count,
            )?);
            values = XOR_QUOTIENTS;
        }
        let mut adder = Adder {
            count: XOR_RECONSTRUCTION_COUNT,
            cursor: 0,
            emitter: self.adder.emitter,
            scratch: self.adder.scratch,
        };
        let mut reconstruct = IterationEmitter { adder: &mut adder };
        let reconstruction_resets =
            reconstruct.reset_scratch(XOR_RECONSTRUCTION_COUNT)?;
        let [b0, b1, b2, b3, b4, b5, b6, b7] = XOR_BITS;
        let (low, low_store) = reconstruct.reconstruct_nibble(
            [b0, b1, b2, b3],
            XOR_TABLE_BASE_WORDS[0],
            XOR_NIBBLES[0],
        )?;
        let (high, high_store) = reconstruct.reconstruct_nibble(
            [b4, b5, b6, b7],
            XOR_TABLE_BASE_WORDS[1],
            XOR_NIBBLES[1],
        )?;
        adder.finish()?;
        let mut sum = Adder {
            count: XOR_SUM_COUNT,
            cursor: 0,
            emitter: self.adder.emitter,
            scratch: self.adder.scratch,
        };
        let sum_resets = IterationEmitter { adder: &mut sum }
            .reset_scratch(XOR_SUM_COUNT)?;
        let xor =
            sum.add_bounded(XOR_NIBBLES[0][1], XOR_NIBBLES[1][1], 6, false)?;
        // Persist the true result at a separate traced word.
        let xor_copy = IterationEmitter { adder: &mut sum }.copy_dirty_word(
            xor,
            XOR_RESULT,
            XOR_COPY_TEMP,
        )?;
        sum.finish()?;
        Ok(OddXorSites {
            lookups: [low, high],
            nibbles: [
                (XOR_NIBBLES[0][1], low_store),
                (XOR_NIBBLES[1][1], high_store),
            ],
            reconstruction_resets,
            steps,
            sum_resets,
            xor: XOR_RESULT,
            xor_copy,
        })
    }

    fn odd_update_predicate(&mut self) -> Result<(u32, u32), BuildError> {
        let [b0, b1, b2, b3, b4, b5, b6, b7] = XOR_BITS;
        // XOR >= 253 iff all six high bits are set and at least one
        // low bit is set. The entire predicate remains a Boolean word.
        self.adder.evaluate(BOOL_OR, b0, b1)?;
        let mut overflow = self.adder.copy()?;
        for bit in [b2, b3, b4, b5, b6, b7] {
            self.adder.evaluate(BOOL_AND, overflow, bit)?;
            overflow = self.adder.copy()?;
        }
        let flag = self.copy_to(XOR_UPDATE_FLAG)?;
        // For overflow values 253..255, the wrapped byte is 0, 1 or 2.
        // The circuit on the low bits produces 0, 0, 1, 2 and clears
        // all high trits (the unused 00 input also maps to zero).
        self.adder.evaluate(XOR_WRAP_RESIDUAL, b1, b0)?;
        let residual = self.copy_to(XOR_UPDATE_RESIDUAL)?;
        Ok((flag, residual))
    }

    fn odd_update(
        &mut self,
        mode: IterationMode,
    ) -> Result<OddUpdateSites, BuildError> {
        let [stay, wrap, join] = mode.update_entries();
        let mut predicate = Adder {
            count: XOR_UPDATE_PREDICATE_COUNT,
            cursor: 0,
            emitter: self.adder.emitter,
            scratch: self.adder.scratch,
        };
        let mut emitter = IterationEmitter { adder: &mut predicate };
        let predicate_resets =
            emitter.reset_scratch(XOR_UPDATE_PREDICATE_COUNT)?;
        let (flag, residual) = emitter.odd_update_predicate()?;
        predicate.finish()?;
        let mut increment = Adder {
            count: XOR_INCREMENT_COUNT,
            cursor: 0,
            emitter: self.adder.emitter,
            scratch: self.adder.scratch,
        };
        let increment_resets = IterationEmitter { adder: &mut increment }
            .reset_scratch(XOR_INCREMENT_COUNT)?;
        let incremented = increment.add_bounded(XOR_RESULT, THREE, 5, true)?;
        increment.finish()?;
        let branch = self.select(XOR_UPDATE_FLAG[1], 506)?;
        self.selected_arm(
            (stay, XOR_UPDATE_STAY),
            incremented,
            (XOR_UPDATE_SELECTED, XOR_UPDATE_JOIN),
        )?;
        self.selected_arm(
            (wrap, XOR_UPDATE_WRAP),
            XOR_UPDATE_RESIDUAL[1],
            (XOR_UPDATE_SELECTED, XOR_UPDATE_JOIN),
        )?;
        self.adder.emitter.pad_to_entry(
            join,
            XOR_UPDATE_JOIN.checked_add(1).ok_or(LAYOUT)?,
        )?;
        let result_copies = [
            self.copy_dirty_word(
                XOR_UPDATE_SELECTED[1],
                MASKED[0],
                MASKED_TEMP,
            )?,
            self.copy_dirty_word(ZERO, MASKED[1], MASKED_TEMP)?,
        ];
        Ok(OddUpdateSites {
            branch,
            flag,
            incremented,
            increment_resets,
            predicate_resets,
            residual,
            result_copies,
        })
    }

    fn once_wrapped(
        &mut self,
        sum: u32,
        mode: IterationMode,
    ) -> Result<[u32; 2], BuildError> {
        let adjusted = self.adder.add(sum, OFFSET, 7)?;
        self.fold(&mode.mask_words(SECOND_LOW_MASKS))?;
        let _: u32 = self.copy_to(mode.mask_words(SECOND_ADJUSTED))?;
        for _ in 0u32..6 {
            self.adder.go(adjusted)?;
            let _: u32 = self.adder.emitter.linear(RotateData)?;
        }
        self.fold(&mode.mask_words(SECOND_FLAG_MASKS))?;
        let flag_store = self.copy_to(mode.mask_words(SECOND_MASK_FLAG))?;
        let branch = self.select(
            mode.mask_address(SECOND_MASK_FLAG[1]),
            mode.mask_address(344),
        )?;
        self.selected_arm(
            (
                mode.second_mask_entry(SECOND_MASK_STAY_ENTRY)?,
                mode.mask_address(SECOND_MASK_STAY),
            ),
            sum,
            (
                mode.mask_words(SECOND_SELECTED),
                mode.mask_address(SECOND_MASK_JOIN),
            ),
        )?;
        self.selected_arm(
            (
                mode.second_mask_entry(SECOND_MASK_WRAP_ENTRY)?,
                mode.mask_address(SECOND_MASK_WRAP),
            ),
            mode.mask_address(SECOND_ADJUSTED[1]),
            (
                mode.mask_words(SECOND_SELECTED),
                mode.mask_address(SECOND_MASK_JOIN),
            ),
        )?;
        self.adder.emitter.pad_to_entry(
            mode.second_mask_entry(SECOND_MASK_JOIN_ENTRY)?,
            mode.mask_address(SECOND_MASK_JOIN)
                .checked_add(1)
                .ok_or(LAYOUT)?,
        )?;
        Ok([branch, flag_store])
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

    fn reset_dirty_word(
        &mut self,
        address: u32,
    ) -> Result<[u32; 3], BuildError> {
        let mut sites = [0; 3];
        for (site, constant) in sites.iter_mut().zip([RESET_ONES, TWOS, ZERO]) {
            self.adder.go(constant)?;
            let _: u32 = self.adder.emitter.linear(RotateData)?;
            if constant == TWOS && address < TWOS {
                // M7174490 holds a scratch pointer, not a frame reset.
                self.adder.emitter.walk(7_174_492)?;
                self.adder.emitter.jump(FRAME)?;
            }
            self.adder.go(address)?;
            *site = self.adder.emitter.linear(CrazyData)?;
        }
        Ok(sites)
    }

    fn reset_scratch(
        &mut self,
        count: u32,
    ) -> Result<Vec<ScratchResetSite>, BuildError> {
        let mut resets = Vec::new();
        for slot in 0..count {
            let address = scratch_address(self.adder.scratch, slot)?;
            resets.push(ScratchResetSite {
                address,
                code_addresses: self.reset_dirty_word(address)?,
            });
        }
        Ok(resets)
    }

    fn rotated_copy(
        &mut self,
        source: u32,
        shifts: u32,
    ) -> Result<u32, BuildError> {
        self.adder.load(source)?;
        let aligned = self.adder.copy()?;
        for _ in 0..shifts {
            self.adder.go(aligned)?;
            let _: u32 = self.adder.emitter.linear(RotateData)?;
        }
        Ok(aligned)
    }

    fn second_add(
        &mut self,
        mode: IterationMode,
    ) -> Result<SecondAddSites, BuildError> {
        let count = match mode {
            IterationMode::First
            | IterationMode::SecondCombinedRead
            | IterationMode::SecondOddHalf
            | IterationMode::SecondOddRead
            | IterationMode::SecondOddUpdate
            | IterationMode::SecondOddXor => {
                return Err(LAYOUT);
            },
            IterationMode::SecondAdd => SECOND_ADD_COUNT,
            IterationMode::SecondParityAdd
            | IterationMode::SecondEvenMask
            | IterationMode::SecondEvenRead => SECOND_PARITY_ADD_COUNT,
        };
        let mut adder = Adder {
            count,
            cursor: 0,
            emitter: self.adder.emitter,
            scratch: self.adder.scratch,
        };
        let scratch_resets =
            IterationEmitter { adder: &mut adder }.reset_scratch(count)?;
        let sum_address = adder.add(PHI_DEST[2], PHI_DEST[0], 6)?;
        let incremented = if mode.has_second_parity() {
            Some(adder.add(sum_address, THREE, 6)?)
        } else {
            None
        };
        adder.finish()?;
        Ok(SecondAddSites {
            incremented,
            scratch_resets,
            sum_address,
        })
    }

    fn second_arithmetic(
        &mut self,
        mode: IterationMode,
    ) -> Result<SecondArithmeticSites, BuildError> {
        let addition = match mode {
            IterationMode::First
            | IterationMode::SecondCombinedRead
            | IterationMode::SecondOddHalf
            | IterationMode::SecondOddRead
            | IterationMode::SecondOddUpdate
            | IterationMode::SecondOddXor => None,
            IterationMode::SecondAdd
            | IterationMode::SecondParityAdd
            | IterationMode::SecondEvenMask
            | IterationMode::SecondEvenRead => Some(self.second_add(mode)?),
        };
        let mask = if mode.has_second_mask() {
            let sum = addition
                .as_ref()
                .and_then(|sites| sites.incremented)
                .ok_or(LAYOUT)?;
            Some(self.second_mask(sum, mode)?)
        } else {
            None
        };
        Ok((addition, mask))
    }

    fn second_byte_arm(
        &mut self,
        mode: IterationMode,
    ) -> Result<[u32; 3], BuildError> {
        self.adder
            .emitter
            .pad_to_entry(mode.first_entry(SECOND_BYTE_ENTRY)?, 7_174_646)?;
        let high = self.prepare_byte_pair(SECOND_PAIR)?;
        self.adder.load(SECOND_RAW[1])?;
        let low = self.copy_to([SECOND_PAIR_TEMP, SECOND_PAIR[0]])?;
        self.adder.go(PHI_JOIN)?;
        let byte_transfer = self.adder.emitter.append_indirect()?;

        Ok([low, high, byte_transfer])
    }

    fn second_eof_arm(
        &mut self,
        eof_low: &[u32],
        eof_high: &[u32],
        mode: IterationMode,
    ) -> Result<[u32; 3], BuildError> {
        self.adder
            .emitter
            .pad_to_entry(mode.first_entry(SECOND_EOF_ENTRY)?, 7_174_656)?;
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
        Ok([eof_low_store, eof_high_store, eof_transfer])
    }

    fn second_eof_output(&mut self) -> Result<[u32; 3], BuildError> {
        // Read the actual committed checksum phi, not its predecessor.
        self.adder.load(ZERO)?;
        self.adder.go(OUTPUT)?;
        let _: u32 = self.adder.emitter.linear(CrazyData)?;
        self.adder.load(PHI_DEST[2])?;
        let store = self.copy_to([SECOND_OUTPUT_TEMP, OUTPUT])?;
        let output = self.adder.emitter.linear(OutputByte)?;
        let halt = self.adder.emitter.append(Halt)?;
        Ok([store, output, halt])
    }

    fn second_mask(
        &mut self,
        sum: u32,
        mode: IterationMode,
    ) -> Result<SecondMaskSites, BuildError> {
        let mut adder = Adder {
            count: SECOND_MASK_COUNT,
            cursor: 0,
            emitter: self.adder.emitter,
            scratch: self.adder.scratch,
        };
        let mut mask = IterationEmitter { adder: &mut adder };
        let resets = mask.reset_scratch(SECOND_MASK_COUNT)?;
        let [first, first_store] = mask.once_wrapped(sum, mode)?;
        let [double, double_store] = mask.double_wrap(mode)?;
        let copies = [
            mask.copy_dirty_word(
                mode.mask_address(DOUBLE_SELECTED[1]),
                MASKED[0],
                MASKED_TEMP,
            )?,
            mask.copy_dirty_word(ZERO, MASKED[1], MASKED_TEMP)?,
        ];
        adder.finish()?;
        Ok(SecondMaskSites {
            branches: [first, double],
            copies,
            flag_stores: [first_store, double_store],
            resets,
        })
    }

    fn second_parity(
        &mut self,
        mode: IterationMode,
        eof_low: &[u32],
        eof_high: &[u32],
    ) -> Result<(SecondParitySites, Option<ThirdSites>), BuildError> {
        self.adder.load(PHI_DEST[0])?;
        self.adder.go(SECOND_PARITY_ONES)?;
        let _: u32 = self.adder.emitter.linear(CrazyData)?;
        self.adder.go(SECOND_PARITY_POINTER)?;
        let pointer_store = self.adder.emitter.linear(CrazyData)?;
        self.adder.go(SECOND_PARITY_POINTER)?;
        let _: u32 = self.adder.emitter.append(RelocateDataPointer)?;
        let lookup = self.adder.emitter.append(RotateData)?;
        let _: u32 = self.adder.emitter.append(RelocateDataPointer)?;
        self.adder.emitter.append_route(b"ojojoojjjjoojoj")?;
        self.adder.emitter.data = BOOT_RETURN;
        self.adder.go(SECOND_PARITY_NORMALIZER)?;
        let _: u32 = self.adder.emitter.linear(CrazyData)?;
        self.adder.go(SECOND_PARITY_FLAG)?;
        let parity_store = self.adder.emitter.linear(CrazyData)?;
        let branch = self.select(SECOND_PARITY_FLAG, 330)?;
        self.adder.emitter.pad_to_entry(
            mode.first_entry(SECOND_PARITY_ODD_ENTRY)?,
            SECOND_PARITY_ODD.checked_add(1).ok_or(LAYOUT)?,
        )?;
        let xor = if mode.has_odd_xor() {
            Some(self.odd_xor()?)
        } else {
            None
        };
        let half = if mode.has_odd_half() && !mode.has_odd_xor() {
            Some(self.odd_half()?)
        } else {
            None
        };
        let update = if mode.has_odd_update() {
            Some(self.odd_update(mode)?)
        } else {
            None
        };
        let third = if mode.has_odd_read() {
            Some(self.third_read(eof_low, eof_high, ThirdLayout::ODD)?)
        } else {
            None
        };
        let combined_odd = if mode.is_combined() {
            Some(self.combined_arm(XOR_RESULT)?)
        } else {
            None
        };
        let odd_halt = if let Some(sites) = &third {
            Some(sites.byte_halt)
        } else if mode.is_combined() {
            None
        } else {
            Some(self.adder.emitter.append(Halt)?)
        };
        self.adder.emitter.pad_to_entry(
            mode.second_even_entry()?,
            SECOND_PARITY_EVEN.checked_add(1).ok_or(LAYOUT)?,
        )?;
        Ok((
            SecondParitySites {
                branch,
                combined_odd,
                half,
                xor,
                update,
                lookup,
                odd_halt,
                parity_store,
                pointer_store,
            },
            third,
        ))
    }

    fn second_read(
        &mut self,
        eof_low: &[u32],
        eof_high: &[u32],
        mode: IterationMode,
    ) -> Result<SecondSites, BuildError> {
        let InputSites { branch, input, .. } = self.classify_second()?;

        self.adder
            .emitter
            .pad_to_entry(mode.first_entry(PHI_ENTRY)?, 7_174_706)?;
        let HeaderSites {
            branch: header_branch,
            commits: phi_commits,
            snapshots: phi_snapshots,
        } = self.header()?;
        let [low, high, byte_transfer] = self.second_byte_arm(mode)?;

        let [eof_low_store, eof_high_store, eof_transfer] =
            self.second_eof_arm(eof_low, eof_high, mode)?;
        self.adder
            .emitter
            .pad_to_entry(mode.first_entry(HEADER_BYTE_ENTRY)?, 7_174_774)?;
        let (parity, odd_third) = if mode.has_second_parity() {
            let (parity, third) =
                self.second_parity(mode, eof_low, eof_high)?;
            (Some(parity), third)
        } else {
            (None, None)
        };
        let (addition, mask, combined) = if mode.is_combined() {
            let (mask, combined) = self.combined_arithmetic(mode)?;
            (None, Some(mask), Some(combined))
        } else {
            let (addition, mask) = self.second_arithmetic(mode)?;
            (addition, mask, None)
        };
        let third = if mode.has_third_read() {
            Some(self.third_read(eof_low, eof_high, mode.third_layout())?)
        } else {
            odd_third
        };
        let byte_halt = if mode.has_third_read() {
            third.as_ref().ok_or(LAYOUT)?.byte_halt
        } else {
            self.adder.emitter.append(Halt)?
        };
        self.adder
            .emitter
            .pad_to_entry(mode.header_eof_entry(), 7_174_784)?;
        let [output_store, output, eof_halt] = self.second_eof_output()?;
        Ok(SecondSites {
            addition,
            branch,
            byte_halt,
            byte_stores: [low, high],
            combined,
            eof_halt,
            eof_stores: [eof_low_store, eof_high_store],
            header_branch,
            input,
            mask,
            output,
            output_store,
            parity,
            phi_commits,
            phi_snapshots,
            phi_transfers: [byte_transfer, eof_transfer],
            third,
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

    fn selected_arm(
        &mut self,
        landing: (usize, u32),
        value: u32,
        destination: ([u32; 2], u32),
    ) -> Result<(), BuildError> {
        let (entry, pointer) = landing;
        let (selected, join) = destination;
        self.adder
            .emitter
            .pad_to_entry(entry, pointer.checked_add(1).ok_or(LAYOUT)?)?;
        self.adder.load(value)?;
        let _: u32 = self.copy_to(selected)?;
        self.adder.go(join)?;
        let _: u32 = self.adder.emitter.append_indirect()?;
        Ok(())
    }

    fn third_byte_arm(
        &mut self,
        layout: ThirdLayout,
    ) -> Result<ThirdByteSites, BuildError> {
        let [entry, ..] = layout.entries;
        self.adder
            .emitter
            .pad_to_entry(entry, layout.address(7_174_962))?;
        let stores = [
            self.copy_dirty_word(
                layout.address(THIRD_RAW[1]),
                SECOND_PAIR[0],
                SECOND_PAIR_TEMP,
            )?,
            self.copy_dirty_word(ZERO, SECOND_PAIR[1], SECOND_PAIR_TEMP)?,
        ];
        self.adder.go(layout.address(THIRD_JOIN))?;
        let transfer = self.adder.emitter.append_indirect()?;
        Ok(ThirdByteSites { stores, transfer })
    }

    fn third_eof_arm(
        &mut self,
        eof_low: &[u32],
        eof_high: &[u32],
        layout: ThirdLayout,
    ) -> Result<ThirdEofSites, BuildError> {
        let [_, entry, ..] = layout.entries;
        self.adder
            .emitter
            .pad_to_entry(entry, layout.address(7_174_972))?;
        let resets = [
            self.reset_dirty_word(SECOND_PAIR[0])?,
            self.reset_dirty_word(SECOND_PAIR[1])?,
        ];
        let low =
            self.adder
                .emitter
                .store_tape(eof_low, SECOND_PAIR[0], ZERO)?;
        let high =
            self.adder
                .emitter
                .store_tape(eof_high, SECOND_PAIR[1], ZERO)?;
        self.adder.go(layout.address(THIRD_JOIN))?;
        let transfer = self.adder.emitter.append_indirect()?;
        Ok(ThirdEofSites {
            resets,
            stores: [low, high],
            transfer,
        })
    }

    fn third_header(
        &mut self,
        layout: ThirdLayout,
    ) -> Result<ThirdHeaderSites, BuildError> {
        let [_, _, entry, ..] = layout.entries;
        self.adder
            .emitter
            .pad_to_entry(entry, layout.address(7_174_982))?;
        let [s0, s1, s2, s3] = PHI_SNAPSHOT;
        let [d0, d1, d2, d3] = PHI_DEST;
        let [t0, t1, t2, t3, t4, t5, t6, t7] = PHI_TEMPS;
        let snapshots = [
            self.copy_dirty_word(SECOND_PAIR[0], s0, t0)?,
            self.copy_dirty_word(SECOND_PAIR[1], s1, t1)?,
            self.copy_dirty_word(MASKED[0], s2, t2)?,
            self.copy_dirty_word(MASKED[1], s3, t3)?,
        ];
        let commits = [
            self.copy_dirty_word(s0, d0, t4)?,
            self.copy_dirty_word(s1, d1, t5)?,
            self.copy_dirty_word(s2, d2, t6)?,
            self.copy_dirty_word(s3, d3, t7)?,
        ];
        self.adder.load(d1)?;
        let _: u32 = self.copy_to(layout.words(THIRD_HEADER_RAW))?;
        for _ in 0u32..5 {
            self.adder.go(layout.address(THIRD_HEADER_RAW[1]))?;
            let _: u32 = self.adder.emitter.linear(RotateData)?;
        }
        self.fold(&layout.words(THIRD_HEADER_MASKS))?;
        let class_store = self.copy_to(layout.words(THIRD_HEADER_FLAG))?;
        let branch = self.select(
            layout.address(THIRD_HEADER_FLAG[1]),
            layout.address(560),
        )?;
        Ok(ThirdHeaderSites {
            branch,
            class_store,
            commits,
            snapshots,
        })
    }

    fn third_read(
        &mut self,
        eof_low: &[u32],
        eof_high: &[u32],
        layout: ThirdLayout,
    ) -> Result<ThirdSites, BuildError> {
        let [_, _, _, header_byte, header_eof] = layout.entries;
        let InputSites {
            branch,
            class_store,
            input,
        } = self.classify_input(
            layout.words(THIRD_RAW),
            &layout.words(THIRD_CLASS_MASKS),
            (layout.words(THIRD_CLASS), layout.address(504)),
        )?;
        let byte = self.third_byte_arm(layout)?;
        let eof = self.third_eof_arm(eof_low, eof_high, layout)?;
        let eof_transfer = eof.transfer;
        let header = self.third_header(layout)?;
        self.adder
            .emitter
            .pad_to_entry(header_byte, layout.address(7_175_018))?;
        let byte_halt = self.adder.emitter.append(Halt)?;
        self.adder
            .emitter
            .pad_to_entry(header_eof, layout.address(7_175_028))?;
        let [output_store, output, eof_halt] = self.second_eof_output()?;
        Ok(ThirdSites {
            branch,
            byte_halt,
            byte_stores: byte.stores,
            class_store,
            eof,
            eof_halt,
            header,
            input,
            output,
            output_store,
            transfers: [byte.transfer, eof_transfer],
        })
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
    let (addition, candidate) =
        build(profile, WITH_MASK, Some(IterationMode::First))?;
    let sites = candidate.ok_or(LAYOUT)?;
    Ok(iteration_from_sites(addition, &sites))
}

const fn iteration_from_sites(
    addition: RelocatedFirstByteAddSource,
    sites: &IterationSites,
) -> RelocatedFirstIterationSource {
    RelocatedFirstIterationSource {
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
    }
}

/// Extend the second successful-byte arm with real dirty phi storage copies.
///
/// First copy the current byte over the old checksum, then restore the old
/// checksum from its edge snapshot. This is a storage experiment, not a
/// checksum update or a reusable code-cell schedule. The first- and second-EOF
/// code paths remain unchanged.
///
/// # Errors
/// Refuses unsupported profiles or a continuation exceeding the reserved gap.
pub fn build_relocated_dirty_phi_source(
    profile: &ProfileDescriptor,
) -> Result<RelocatedDirtyPhiSource, BuildError> {
    let mut iteration = build_relocated_first_iteration_source(profile)?;
    let source = mem::take(&mut iteration.addition.source);
    let mut emitter = Emitter {
        data: HEADER_BYTE.checked_add(1).ok_or(LAYOUT)?,
        profile,
        source: source.get(..HEADER_BYTE_ENTRY).ok_or(LAYOUT)?.to_vec(),
        source_cells: source.len(),
        tape_bounds: MASK_BOUNDS,
    };
    let mut adder = Adder {
        count: 0,
        cursor: 0,
        emitter: &mut emitter,
        scratch: MASK_SCRATCH,
    };
    let mut continuation = IterationEmitter { adder: &mut adder };
    let temporary_address = PHI_TEMPS[4];
    let destination_address = PHI_DEST[2];
    let source_addresses = [PHI_DEST[0], PHI_SNAPSHOT[2]];
    let copies = [
        continuation.copy_dirty_word(
            source_addresses[0],
            destination_address,
            temporary_address,
        )?,
        continuation.copy_dirty_word(
            source_addresses[1],
            destination_address,
            temporary_address,
        )?,
    ];
    iteration.second_byte_halt_code_address = emitter.append(Halt)?;
    let end = emitter.source.len();
    if end > HEADER_EOF_ENTRY {
        return Err(LAYOUT);
    }
    emitter
        .source
        .extend_from_slice(source.get(end..).ok_or(LAYOUT)?);
    iteration.addition.source = emitter.source;
    Ok(RelocatedDirtyPhiSource {
        copies,
        destination_address,
        iteration,
        reset_constants: [RESET_ONES, TWOS, ZERO],
        source_addresses,
        temporary_address,
    })
}

/// Execute a second addition using both committed header words and dirty
/// scratch.
///
/// This probes the unsigned addition operation on all successful second bytes,
/// not the parity selection or the full second checksum iteration. It does not
/// read a third byte or emit a checksum on the second successful-byte path.
///
/// # Errors
/// Refuses unsupported profiles and exhausted physical layouts.
pub fn build_relocated_second_add_source(
    profile: &ProfileDescriptor,
) -> Result<RelocatedSecondAddSource, BuildError> {
    let (addition, candidate) =
        build(profile, WITH_SECOND_ADD, Some(IterationMode::SecondAdd))?;
    let mut sites = candidate.ok_or(LAYOUT)?;
    let second = sites.second.addition.take().ok_or(LAYOUT)?;
    Ok(RelocatedSecondAddSource {
        iteration: iteration_from_sites(addition, &sites),
        scratch_resets: second.scratch_resets,
        sum_address: second.sum_address,
    })
}

/// Branch on the second byte's live parity and compute the even sum plus three.
///
/// The second lookup uses a disjoint virgin loader window. Odd bytes halt
/// before XOR; even bytes halt before canonical masking. This is not a complete
/// second iteration or an admitted reusable loop.
///
/// # Errors
/// Refuses unsupported profiles or exhausted bounded geometry.
pub fn build_relocated_second_parity_add_source(
    profile: &ProfileDescriptor,
) -> Result<RelocatedSecondParityAddSource, BuildError> {
    let (addition, candidate) = build(
        profile,
        WITH_SECOND_PARITY_ADD,
        Some(IterationMode::SecondParityAdd),
    )?;
    let mut sites = candidate.ok_or(LAYOUT)?;
    parity_from_sites(addition, &mut sites, IterationMode::SecondParityAdd)
}

fn parity_from_sites(
    addition: RelocatedFirstByteAddSource,
    sites: &mut IterationSites,
    mode: IterationMode,
) -> Result<RelocatedSecondParityAddSource, BuildError> {
    let second = sites.second.addition.take().ok_or(LAYOUT)?;
    let parity = sites.second.parity.take().ok_or(LAYOUT)?;
    Ok(RelocatedSecondParityAddSource {
        addition: RelocatedSecondAddSource {
            iteration: iteration_from_sites(addition, sites),
            scratch_resets: second.scratch_resets,
            sum_address: second.sum_address,
        },
        branch_code_address: parity.branch,
        even_entry: u32::try_from(mode.first_entry(SECOND_PARITY_EVEN_ENTRY)?)
            .map_err(|_error| LAYOUT)?,
        incremented_address: second.incremented.ok_or(LAYOUT)?,
        lookup_code_address: parity.lookup,
        odd_halt_code_address: parity.odd_halt.ok_or(LAYOUT)?,
        parity_address: SECOND_PARITY_FLAG,
        parity_store_code_address: parity.parity_store,
        pointer_address: SECOND_PARITY_POINTER,
        pointer_store_code_address: parity.pointer_store,
    })
}

/// Canonically mask the second even sum, including the 512 boundary.
///
/// Odd second bytes still halt before XOR; neither path reads a third byte.
/// This is an executable physical mask probe, not complete C lowering.
///
/// # Errors
/// Refuses unsupported profiles or exhausted bounded geometry.
pub fn build_relocated_second_even_mask_source(
    profile: &ProfileDescriptor,
) -> Result<RelocatedSecondEvenMaskSource, BuildError> {
    let (addition, candidate) = build(
        profile,
        WITH_SECOND_MASK,
        Some(IterationMode::SecondEvenMask),
    )?;
    let mut sites = candidate.ok_or(LAYOUT)?;
    mask_from_sites(addition, &mut sites, IterationMode::SecondEvenMask)
}

fn mask_from_sites(
    addition: RelocatedFirstByteAddSource,
    sites: &mut IterationSites,
    mode: IterationMode,
) -> Result<RelocatedSecondEvenMaskSource, BuildError> {
    let mask = sites.second.mask.take().ok_or(LAYOUT)?;
    Ok(RelocatedSecondEvenMaskSource {
        branch_code_addresses: mask.branches,
        flag_addresses: [SECOND_MASK_FLAG[1], DOUBLE_FLAG[1]],
        flag_store_code_addresses: mask.flag_stores,
        parity: parity_from_sites(addition, sites, mode)?,
        residual_address: SECOND_SELECTED[1],
        result_copies: mask.copies,
        result_pair: MASKED,
        scratch_resets: mask.resets,
    })
}

/// Continue a second even update through a real third read and dirty phi edge.
///
/// Third EOF returns the actual committed checksum; a byte halts before
/// arithmetic. This does not admit the odd second arm or a reusable loop.
///
/// # Errors
/// Refuses unsupported profiles or exhausted bounded geometry.
pub fn build_relocated_second_even_read_source(
    profile: &ProfileDescriptor,
) -> Result<RelocatedSecondEvenReadSource, BuildError> {
    let mode = IterationMode::SecondEvenRead;
    let (addition, candidate) = build(profile, WITH_THIRD_READ, Some(mode))?;
    let mut sites = candidate.ok_or(LAYOUT)?;
    let third = sites.second.third.take().ok_or(LAYOUT)?;
    Ok(RelocatedSecondEvenReadSource {
        mask: mask_from_sites(addition, &mut sites, mode)?,
        third_branch_code_address: third.branch,
        third_byte_halt_code_address: third.byte_halt,
        third_byte_stores: third.byte_stores,
        third_class_store: third.class_store,
        third_eof_halt_code_address: third.eof_halt,
        third_eof_output_code_address: third.output,
        third_eof_output_store: third.output_store,
        third_eof_resets: third.eof.resets,
        third_eof_stores: third.eof.stores,
        third_header_branch_code_address: third.header.branch,
        third_header_class_store: third.header.class_store,
        third_input_code_address: third.input,
        third_phi_commits: third.header.commits,
        third_phi_snapshots: third.header.snapshots,
        third_phi_transfers: third.transfers,
    })
}

/// Execute one physical binary decomposition step on the odd second path.
///
/// Both committed byte operands are divided by two; their remainders
/// produce the lowest XOR bit. This is not a complete XOR or second update.
///
/// # Errors
/// Refuses unsupported profiles and exhausted physical layouts.
pub fn build_relocated_second_odd_half_source(
    profile: &ProfileDescriptor,
) -> Result<RelocatedSecondOddHalfSource, BuildError> {
    let (addition, candidate) =
        build(profile, WITH_ODD_HALF, Some(IterationMode::SecondOddHalf))?;
    let mut sites = candidate.ok_or(LAYOUT)?;
    let mut parity = sites.second.parity.take().ok_or(LAYOUT)?;
    let half = parity.half.take().ok_or(LAYOUT)?;
    Ok(RelocatedSecondOddHalfSource {
        branch_code_address: parity.branch,
        iteration: iteration_from_sites(addition, &sites),
        low_xor_address: half.low_xor,
        odd_halt_code_address: parity.odd_halt.ok_or(LAYOUT)?,
        quotient_addresses: half.quotients,
        remainder_addresses: half.remainders,
        result_store_code_addresses: half.result_stores,
        scratch_resets: half.resets,
    })
}

/// Compute a complete physical binary XOR on the odd second-byte path.
/// The result is not yet incremented or committed to the source frame.
///
/// # Errors
/// Refuses unsupported profiles and exhausted physical layouts.
pub fn build_relocated_second_odd_xor_source(
    profile: &ProfileDescriptor,
) -> Result<RelocatedSecondOddXorSource, BuildError> {
    let mode = IterationMode::SecondOddXor;
    let (addition, candidate) = build(profile, WITH_ODD_XOR, Some(mode))?;
    let mut sites = candidate.ok_or(LAYOUT)?;
    odd_xor_from_sites(addition, &mut sites)
}

/// Execute the odd second-byte update through the canonical checksum pair.
/// This is still a bounded one-shot guest, not a reusable loop.
///
/// # Errors
/// Refuses unsupported profiles and exhausted physical layouts.
pub fn build_relocated_second_odd_update_source(
    profile: &ProfileDescriptor,
) -> Result<RelocatedSecondOddUpdateSource, BuildError> {
    let (addition, candidate) = build(
        profile,
        WITH_ODD_UPDATE,
        Some(IterationMode::SecondOddUpdate),
    )?;
    let mut sites = candidate.ok_or(LAYOUT)?;
    odd_update_from_sites(addition, &mut sites)
}

/// Execute both second parity arms, a shared mask, and a real third input.
/// The third successful byte still halts before arithmetic.
/// # Errors
/// Refuses unsupported profiles and exhausted physical layouts.
pub fn build_relocated_second_combined_read_source(
    profile: &ProfileDescriptor,
) -> Result<RelocatedSecondCombinedReadSource, BuildError> {
    let (addition, candidate) = build(
        profile,
        WITH_COMBINED_READ,
        Some(IterationMode::SecondCombinedRead),
    )?;
    let mut sites = candidate.ok_or(LAYOUT)?;
    let combined = sites.second.combined.take().ok_or(LAYOUT)?;
    let mask = sites.second.mask.take().ok_or(LAYOUT)?;
    let third = sites.second.third.take().ok_or(LAYOUT)?;
    let parity = sites.second.parity.take().ok_or(LAYOUT)?;
    let odd = parity.combined_odd.ok_or(LAYOUT)?;
    Ok(RelocatedSecondCombinedReadSource {
        arm_stores: [combined.even.store, odd.store],
        arm_transfers: [combined.even.transfer, odd.transfer],
        increment: (COMBINED_INCREMENT[1], combined.increment_store),
        iteration: iteration_from_sites(addition, &sites),
        mask_branches: mask.branches,
        mask_copies: mask.copies,
        mask_flag_stores: mask.flag_stores,
        parity_branch: parity.branch,
        parity_store: parity.parity_store,
        result_word: COMBINED_VALUE[1],
        third_byte_halt: third.byte_halt,
        third_commits: third.header.commits,
        third_eof: [third.output, third.eof_halt],
        third_input: third.input,
        third_snapshots: third.header.snapshots,
    })
}

/// Execute a real third input after the canonical odd second-byte update.
/// A third EOF returns the committed checksum; a byte halts before arithmetic.
///
/// # Errors
/// Refuses unsupported profiles and exhausted physical layouts.
pub fn build_relocated_second_odd_read_source(
    profile: &ProfileDescriptor,
) -> Result<RelocatedSecondOddReadSource, BuildError> {
    let (addition, candidate) =
        build(profile, WITH_ODD_READ, Some(IterationMode::SecondOddRead))?;
    let mut sites = candidate.ok_or(LAYOUT)?;
    let third = sites.second.third.take().ok_or(LAYOUT)?;
    Ok(RelocatedSecondOddReadSource {
        update: odd_update_from_sites(addition, &mut sites)?,
        third_branch_code_address: third.branch,
        third_byte_halt_code_address: third.byte_halt,
        third_byte_stores: third.byte_stores,
        third_class_store: third.class_store,
        third_eof_halt_code_address: third.eof_halt,
        third_eof_output_code_address: third.output,
        third_eof_output_store: third.output_store,
        third_eof_resets: third.eof.resets,
        third_eof_stores: third.eof.stores,
        third_header_branch_code_address: third.header.branch,
        third_header_class_store: third.header.class_store,
        third_input_code_address: third.input,
        third_phi_commits: third.header.commits,
        third_phi_snapshots: third.header.snapshots,
        third_phi_transfers: third.transfers,
    })
}

fn odd_update_from_sites(
    addition: RelocatedFirstByteAddSource,
    sites: &mut IterationSites,
) -> Result<RelocatedSecondOddUpdateSource, BuildError> {
    let update = sites
        .second
        .parity
        .as_mut()
        .and_then(|parity| parity.update.take())
        .ok_or(LAYOUT)?;
    Ok(RelocatedSecondOddUpdateSource {
        xor: odd_xor_from_sites(addition, sites)?,
        predicate_resets: update.predicate_resets,
        increment_resets: update.increment_resets,
        flag: (XOR_UPDATE_FLAG[1], update.flag),
        branch_code_address: update.branch,
        residual: (XOR_UPDATE_RESIDUAL[1], update.residual),
        incremented_address: update.incremented,
        result_pair: MASKED,
        result_copies: update.result_copies,
    })
}

fn odd_xor_from_sites(
    addition: RelocatedFirstByteAddSource,
    sites: &mut IterationSites,
) -> Result<RelocatedSecondOddXorSource, BuildError> {
    let mut parity = sites.second.parity.take().ok_or(LAYOUT)?;
    let xor = parity.xor.take().ok_or(LAYOUT)?;
    Ok(RelocatedSecondOddXorSource {
        branch_code_address: parity.branch,
        iteration: iteration_from_sites(addition, sites),
        bit_addresses: XOR_BITS,
        copy_temporary_address: XOR_COPY_TEMP,
        odd_halt_code_address: parity.odd_halt.ok_or(LAYOUT)?,
        table_lookups: xor.lookups,
        nibble_results: xor.nibbles,
        quotient_addresses: XOR_QUOTIENTS,
        reconstruction_resets: xor.reconstruction_resets,
        steps: xor.steps,
        sum_resets: xor.sum_resets,
        xor_address: xor.xor,
        xor_copy: xor.xor_copy,
    })
}

pub(super) fn emit_iteration(
    adder: &mut Adder<'_, '_>,
    sum: u32,
    eof: [&[u32]; 2],
    mode: IterationMode,
) -> Result<IterationSites, BuildError> {
    let [eof_low, eof_high] = eof;
    let mut emitter = IterationEmitter { adder };
    let mask = emitter.mask(sum, mode)?;
    let second = emitter.second_read(eof_low, eof_high, mode)?;
    Ok(IterationSites { mask, second })
}
