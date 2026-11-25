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
//   - Recurrent physical byte checksum with split state and carry.
// - Must-Not:
//   - Admit source-C CFG effects or claim the publication resource bound.
// - Allows:
//   - Inputs: exact current N15 profile.
//   - Outputs: graphical guest and proposed physical effect sites.
//   - Side effects: none; independent VM replay owns acceptance.
// - Split-When:
//   - General recurrent arithmetic allocation replaces fixed geometry.
// - Merge-When:
//   - Source-linked recurrent checksum lowering owns these effects.
// - Summary:
//   - Compose low and high nibble transitions through a real carry.

use std::cmp::Reverse;

use malbolge::{ProfileDescriptor, profile_crazy};

use super::super::super::super::LinearOpcode;
use super::super::super::{BuildError, Emitter, LAYOUT, TapeBounds};
use super::super::relocated_recurrent_access::AccessBlock;
use super::relocated_recurrent_chunk_bootstrap::{
    TargetAnchors, go_target, initialize_chunk_seeds, target_slots,
};
use super::relocated_recurrent_mod4_source::{
    LOOP_RETURN, Mod4Blocks, seed_address,
};
use super::relocated_recurrent_reload_source::main_route;
use super::{
    ALL_ONES, ALL_TWOS, BYTE, BYTE_ROUTE_POINTER, Blocks, CAPTURE, CONSTANTS,
    EOF, INITIAL, MAIN_ROUTE, RelocatedRecurrentCaptureSource, Route, STATES,
    Words, bootstrap, code, immutable_seed_prefix, insert, previous,
};

const BOUNDS: TapeBounds = TapeBounds {
    limit: 7_360_001,
    start: 7_177_001,
};
const CODE_BASE: u32 = 2_308_728;
const TERMINAL: u32 = 2_318_728;
const SOURCE_CELLS: usize = 2_318_854;
const BYTE_ROUTE: u32 = 7_194_000;
const RAW_TABLES: [u32; 2] = [7_208_352, 7_209_081];
const RAW_SEEDS: [u32; 2] = [7_211_000, 7_211_200];
const HIGH_TABLE: u32 = 7_223_661;
const LOW_TABLE: u32 = 7_242_615;
const LOW_SEEDS: u32 = 7_243_100;
const HIGH_SEEDS: u32 = 7_243_400;
const LOW: u32 = 7_175_100;
const HIGH: u32 = 7_175_120;
const POINTERS: [u32; 2] = [7_175_140, 7_175_160];
const SCRATCH: [u32; 2] = [7_180_750, 7_180_760];
// Dedicated constants must not share continuation slots with operands.
const LOAD_RAW: u32 = 7_180_800;
const RECOVER_RAW: [u32; 2] = [7_180_804, 7_180_808];
const LOOKUP_CONSTANTS: [u32; 5] =
    [7_180_812, 7_180_816, 7_180_820, 7_180_824, 7_180_828];
const RESET_CONSTANTS: [u32; 6] = [
    7_180_832, 7_180_836, 7_180_840, 7_180_844, 7_180_848, 7_180_852,
];
// The high state occupies trits 6..8, the carry occupies trit 4.
const CARRY_PLACE: u32 = 81;
const HIGH_ROW: u32 = 729;
const LOW_ROW: u32 = 27;
const PREFIX_PLACE: u32 = 19_683;
const EOF_HIGH_CONSTANT: u32 = 7_175_134;
const EOF_HIGH_TWOS: u32 = 7_175_136;
const EOF_LOW_CONSTANT: u32 = 7_180_890;
const EOF_LOW_TWOS: u32 = 7_175_154;
const EOF_SCRATCH: u32 = 7_180_900;
const HIGH_OUTPUT_RAW: u32 = 17;
const LOW_OUTPUT_OFFSET: u32 = 5;
// Residues on disjoint ternary digit sets (low seven and high eight).
const OUTPUT_HIGH_WORDS: [u32; 16] = [
    7_173_360, 7_175_223, 7_173_909, 7_174_314, 7_173_783, 7_174_674,
    7_175_007, 7_174_440, 7_175_394, 7_173_567, 7_175_187, 7_173_981,
    7_174_629, 7_173_720, 7_174_368, 7_175_376,
];
const OUTPUT_LOW_ACCUMULATORS: [u32; 16] = [
    7_175_546, 4_518_341, 5_994_566, 9_714_653, 2_864_969, 2_313_845,
    3_632_606, 6_171_713, 9_891_800, 1_979_234, 9_399_725, 3_278_312,
    5_285_978, 10_600_388, 1_624_940, 9_045_431,
];
const RAW_RESTORE: [[u32; 2]; 2] =
    [[7_180_872, 7_180_876], [7_180_880, 7_180_884]];

/// Physical recurrent checksum with low and high state and a real EOF arm.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct RelocatedRecurrentChecksumSource {
    /// Actual recurrent capture and dispatch sites.
    pub capture: RelocatedRecurrentCaptureSource,
    /// Two reversible load sites.
    pub load: [u32; 2],
    /// Raw-low, carry, raw-high, high-result and low-result reads.
    pub lookup: [[u32; 2]; 5],
    /// Low and high raw-byte index words.
    pub pointers: [u32; 2],
    /// Low and high temporary state words.
    pub scratch: [u32; 2],
    /// Physical rotation that reloads each dirty temporary.
    pub scratch_rotate: u32,
    /// Low and high dirty state words.
    pub state: [u32; 2],
    /// First physical terminal instruction.
    pub terminal: u32,
}

type AnchorSplit = (u64, usize);
type LookupSites = [[u32; 2]; 5];

fn plus(left: u32, right: u32) -> Result<u32, BuildError> {
    left.checked_add(right).ok_or(LAYOUT)
}

fn times(left: u32, right: u32) -> Result<u32, BuildError> {
    left.checked_mul(right).ok_or(LAYOUT)
}

fn crazy(profile: &ProfileDescriptor, data: u32, acc: u32) -> u32 {
    profile_crazy(data, acc, profile.word_trits())
}

fn low_mask(profile: &ProfileDescriptor, low: u32) -> Result<u32, BuildError> {
    plus(
        crazy(profile, plus(LOW_TABLE, times(low, LOW_ROW)?)?, ALL_TWOS),
        13,
    )
}

fn high_mask(high: u32) -> Result<u32, BuildError> {
    plus(
        ALL_TWOS.checked_sub(19_682).ok_or(LAYOUT)?,
        plus(times(high, HIGH_ROW)?, 647)?,
    )
}

fn raw_mask(profile: &ProfileDescriptor, base: u32) -> Result<u32, BuildError> {
    plus(crazy(profile, base, ALL_TWOS), 364)
}

fn high_raw_selector(
    profile: &ProfileDescriptor,
    high: u32,
    parity: u32,
) -> Result<u32, BuildError> {
    // Two folds preserve the state trits. The first turns the fixed
    // high prefix and raw selector trits into ones. The second writes
    // the actual table prefix, raw high nibble and parity into them.
    let low = crazy(profile, ALL_ONES, plus(high, times(parity, LOW_ROW)?)?);
    let upper = crazy(profile, ALL_ONES, HIGH_TABLE);
    plus(
        plus(
            upper
                .checked_sub(upper.rem_euclid(PREFIX_PLACE))
                .ok_or(LAYOUT)?,
            19_602,
        )?,
        low.rem_euclid(CARRY_PLACE),
    )
}

fn carry_selector(carry: u32) -> Result<u32, BuildError> {
    let column = match carry {
        0 => 1,
        1 => 2,
        2 => 0,
        _ => return Err(LAYOUT),
    };
    ALL_TWOS
        .checked_sub(times(
            2u32.checked_sub(column).ok_or(LAYOUT)?,
            CARRY_PLACE,
        )?)
        .ok_or(LAYOUT)
}

fn low_update(state: u32, byte: u32) -> Result<u32, BuildError> {
    plus(
        if byte.is_multiple_of(2) {
            plus(state, byte)?
        } else {
            state ^ byte
        },
        3,
    )
}

fn high_update(
    state: u32,
    byte: u32,
    parity: u32,
    carry: u32,
) -> Result<u32, BuildError> {
    Ok(plus(
        if parity == 0 {
            plus(state, byte)?
        } else {
            state ^ byte
        },
        carry,
    )? & 15)
}

fn high_index(
    state: u32,
    raw: u32,
    parity: u32,
    carry: u32,
) -> Result<u32, BuildError> {
    plus(
        HIGH_TABLE,
        plus(
            times(state, HIGH_ROW)?,
            plus(
                486,
                plus(
                    times(carry, CARRY_PLACE)?,
                    plus(times(parity, LOW_ROW)?, raw)?,
                )?,
            )?,
        )?,
    )
}

fn data_words(profile: &ProfileDescriptor) -> Result<Words, BuildError> {
    let [raw_low, raw_high] = RAW_TABLES;
    let [ptr_low, ptr_high] = POINTERS;
    let [scratch_low, scratch_high] = SCRATCH;
    let mut words = Words::new();
    for (address, value) in [
        (CAPTURE, ALL_ONES),
        (LOW, low_mask(profile, 0)?),
        (HIGH, high_mask(0)?),
        (ptr_low, raw_mask(profile, raw_low)?),
        (ptr_high, raw_mask(profile, raw_high)?),
        (scratch_low, ALL_ONES),
        (scratch_high, ALL_ONES),
        (LOAD_RAW, ALL_TWOS),
        (BYTE_ROUTE_POINTER, previous(BYTE_ROUTE)?),
        (LOOP_RETURN, previous(MAIN_ROUTE)?),
    ] {
        insert(&mut words, address, value)?;
    }
    for (address, value) in STATES.into_iter().zip(INITIAL) {
        insert(&mut words, address, value)?;
    }
    for address in RECOVER_RAW {
        insert(&mut words, address, ALL_TWOS)?;
    }
    for address in LOOKUP_CONSTANTS.into_iter().chain(RESET_CONSTANTS) {
        insert(&mut words, address, ALL_ONES)?;
    }
    for (address, value) in CONSTANTS.into_iter().zip([ALL_ONES, ALL_TWOS, 0]) {
        insert(&mut words, address, value)?;
    }
    eof_words(profile, &mut words)?;
    for (base, [prefix, seed]) in RAW_TABLES.into_iter().zip(RAW_RESTORE) {
        let inverse = crazy(profile, ALL_ONES, raw_mask(profile, base)?);
        insert(
            &mut words,
            prefix,
            immutable_seed_prefix(inverse, profile.word_trits())?,
        )?;
        insert(&mut words, seed, inverse)?;
    }
    Ok(words)
}

fn eof_words(
    profile: &ProfileDescriptor,
    words: &mut Words,
) -> Result<(), BuildError> {
    // EOF destructively decodes the two committed masks only after
    // the final physical read. No byte-path output can reach this route.
    for landing in EOF {
        for (offset, value) in [
            (1, previous(TERMINAL)?),
            (2, inverse_rotation(carry_selector(0)?)?),
            (3, previous(HIGH)?),
        ] {
            insert(words, plus(landing, offset)?, value)?;
        }
    }
    for (address, value) in [
        (plus(HIGH, 1)?, previous(EOF_HIGH_CONSTANT)?),
        (
            EOF_HIGH_CONSTANT,
            inverse_rotation(high_raw_selector(profile, HIGH_OUTPUT_RAW, 0)?)?,
        ),
        (plus(EOF_HIGH_CONSTANT, 1)?, previous(HIGH)?),
        (EOF_HIGH_TWOS, ALL_TWOS),
        (plus(EOF_HIGH_TWOS, 1)?, previous(HIGH)?),
        (plus(HIGH, 7)?, previous(EOF_HIGH_TWOS)?),
        (EOF_SCRATCH, ALL_ONES),
        (plus(EOF_SCRATCH, 1)?, previous(EOF_LOW_CONSTANT)?),
        (EOF_LOW_CONSTANT, inverse_rotation(ALL_TWOS - 17)?),
        (plus(EOF_LOW_CONSTANT, 1)?, previous(LOW)?),
        (plus(LOW, 1)?, previous(EOF_LOW_TWOS)?),
        (EOF_LOW_TWOS, ALL_TWOS),
        (plus(EOF_LOW_TWOS, 1)?, previous(LOW)?),
    ] {
        insert(words, address, value)?;
    }
    Ok(())
}

fn pair(
    profile: &ProfileDescriptor,
    words: &mut Words,
    address: u32,
    (value, continuation): (u32, u32),
) -> Result<(), BuildError> {
    for (offset, word) in [
        (0, immutable_seed_prefix(value, profile.word_trits())?),
        (1, value),
        (2, continuation),
    ] {
        insert(words, plus(address, offset)?, word)?;
    }
    Ok(())
}

fn raw_lookup(
    profile: &ProfileDescriptor,
    route: &mut Route<'_>,
    block: &AccessBlock,
    index: usize,
) -> Result<(), BuildError> {
    let pointer = *POINTERS.get(index).ok_or(LAYOUT)?;
    let table = *RAW_TABLES.get(index).ok_or(LAYOUT)?;
    let seeds = *RAW_SEEDS.get(index).ok_or(LAYOUT)?;
    route.enter_ready(block, pointer)?;
    let continuation = previous(route.cursor)?;
    let count = if index == 0 {
        16
    } else {
        32
    };
    for value in 0..count {
        let mask = if index == 0 {
            crazy(profile, crazy(profile, ALL_ONES, value), ALL_TWOS)
        } else {
            high_raw_selector(
                profile,
                value.div_euclid(2),
                value.rem_euclid(2),
            )?
        };
        pair(
            profile,
            route.words,
            seed_address(seeds, value)?,
            (mask, continuation),
        )?;
    }
    for byte in 0..=255u32 {
        let value = if index == 0 {
            byte & 15
        } else {
            plus(times(byte >> 4u32, 2)?, byte & 1)?
        };
        let address = plus(table, 729)?.checked_sub(byte).ok_or(LAYOUT)?;
        insert(route.words, address, previous(seed_address(seeds, value)?)?)?;
    }
    route.prepare(block, false)
}

fn low_lookup(
    profile: &ProfileDescriptor,
    route: &mut Route<'_>,
    block: &AccessBlock,
    result: bool,
) -> Result<(), BuildError> {
    route.enter_ready(block, LOW)?;
    let continuation = previous(route.cursor)?;
    for update in 3..=32u32 {
        let seed = seed_address(LOW_SEEDS, update)?;
        let (offset, value) = if result {
            (4, inverse_rotation(low_mask(profile, update & 15)?)?)
        } else {
            insert(route.words, seed, previous(plus(seed, 4)?)?)?;
            (1, carry_selector(update.div_euclid(16))?)
        };
        pair(
            profile,
            route.words,
            plus(seed, offset)?,
            (value, continuation),
        )?;
    }
    if !result {
        for state in 0..16u32 {
            let end = plus(LOW_TABLE, times(plus(state, 1)?, LOW_ROW)?)?;
            for raw in 0..16u32 {
                let update = low_update(state, raw)?;
                insert(
                    route.words,
                    end.checked_sub(raw).ok_or(LAYOUT)?,
                    previous(seed_address(LOW_SEEDS, update)?)?,
                )?;
            }
        }
    }
    route.prepare(block, false)
}

fn high_lookup(
    profile: &ProfileDescriptor,
    route: &mut Route<'_>,
    block: &AccessBlock,
) -> Result<(), BuildError> {
    route.enter_ready(block, HIGH)?;
    let continuation = previous(route.cursor)?;
    for state in 0..16u32 {
        pair(
            profile,
            route.words,
            seed_address(HIGH_SEEDS, state)?,
            (inverse_rotation(high_mask(state)?)?, continuation),
        )?;
        high_row(route.words, state)?;
    }
    route.prepare(block, false)
}

fn high_row(words: &mut Words, state: u32) -> Result<(), BuildError> {
    for raw in 0..16u32 {
        for parity in 0..2 {
            // XOR of two nibbles is at most 15; adding three cannot
            // produce a carry of two. Even-byte addition can reach 32.
            let carry_count = if parity == 0 {
                3
            } else {
                2
            };
            for carry in 0..carry_count {
                let next = high_update(state, raw, parity, carry)?;
                insert(
                    words,
                    plus(high_index(state, raw, parity, carry)?, 1)?,
                    previous(seed_address(HIGH_SEEDS, next)?)?,
                )?;
            }
        }
    }
    Ok(())
}

fn inverse_rotation(value: u32) -> Result<u32, BuildError> {
    plus(
        times(value.rem_euclid(4_782_969), 3)?,
        value.div_euclid(4_782_969),
    )
}

fn output_table(
    profile: &ProfileDescriptor,
    words: &mut Words,
) -> Result<(), BuildError> {
    for (index, (high, low)) in OUTPUT_HIGH_WORDS
        .into_iter()
        .zip(OUTPUT_LOW_ACCUMULATORS)
        .enumerate()
    {
        let nibble = u32::try_from(index).map_err(|_error| LAYOUT)?;
        let high_address = plus(high_index(nibble, HIGH_OUTPUT_RAW, 0, 0)?, 1)?;
        let low_address =
            plus(plus(LOW_TABLE, times(nibble, LOW_ROW)?)?, LOW_OUTPUT_OFFSET)?;
        insert(
            words,
            high_address,
            crazy(profile, crazy(profile, ALL_ONES, high), ALL_TWOS),
        )?;
        insert(words, plus(high_address, 1)?, previous(EOF_SCRATCH)?)?;
        insert(words, low_address, crazy(profile, low, ALL_TWOS))?;
        insert(words, plus(low_address, 1)?, previous(EOF_SCRATCH)?)?;
    }
    Ok(())
}

fn reset(
    route: &mut Route<'_>,
    blocks: &Blocks,
    address: u32,
    constant: u32,
) -> Result<(), BuildError> {
    let [first, second, _] = &blocks.reset;
    route.call_ready(&blocks.rotate, constant)?;
    route.call_ready(first, address)?;
    route.call_ready(second, address)
}

fn commit(
    route: &mut Route<'_>,
    (blocks, scratch_rotate): (&Mod4Blocks, &AccessBlock),
    (state, scratch): (u32, u32),
    resets: [u32; 2],
) -> Result<(), BuildError> {
    let capture = &blocks.capture;
    let [reset_state, reset_scratch] = resets;
    let [_, _, commit] = &capture.reset;
    route.call_ready(&capture.crazy, scratch)?;
    reset(route, capture, state, reset_state)?;
    route.call_ready(scratch_rotate, scratch)?;
    route.call_ready(commit, state)?;
    reset(route, capture, scratch, reset_scratch)
}

fn byte_route(
    profile: &ProfileDescriptor,
    blocks: &Mod4Blocks,
    (lookups, scratch_rotate): (&[AccessBlock; 5], &AccessBlock),
    words: &mut Words,
) -> Result<(), BuildError> {
    let capture = &blocks.capture;
    let [raw_low, carry, raw_high, high_result, low_result] = lookups;
    let [first, second] = &blocks.load;
    let [_, _, third] = &capture.reset;
    let [ptr_low, ptr_high] = POINTERS;
    let [scratch_low, scratch_high] = SCRATCH;
    let [raw_low_c, carry_c, raw_high_c, high_c, low_c] = LOOKUP_CONSTANTS;
    let [recover_a, recover_b] = RECOVER_RAW;
    let [state_l, state_h, scratch_l, scratch_h, pointer_l, pointer_h] =
        RESET_CONSTANTS;
    let mut bridge = Route {
        cursor: plus(BYTE, 1)?,
        words,
    };
    bridge.prepare(&capture.branch, false)?;
    bridge.enter_ready(&capture.branch, BYTE_ROUTE_POINTER)?;
    if bridge.cursor >= BYTE_ROUTE_POINTER {
        return Err(LAYOUT);
    }
    let mut route = Route {
        cursor: BYTE_ROUTE,
        words,
    };
    route.prepare(&capture.branch, false)?;
    route.call_ready(&capture.rotate, LOAD_RAW)?;
    route.call_ready(first, CAPTURE)?;
    route.call_ready(first, ptr_low)?;
    route.call_ready(&capture.rotate, raw_low_c)?;
    raw_lookup(profile, &mut route, raw_low, 0)?;
    route.call_ready(first, LOW)?;
    route.call_ready(&capture.rotate, carry_c)?;
    low_lookup(profile, &mut route, carry, false)?;
    route.call_ready(first, HIGH)?;
    route.call_ready(&capture.rotate, recover_a)?;
    route.call_ready(third, CAPTURE)?;
    route.call_ready(&capture.rotate, recover_b)?;
    route.call_ready(second, CAPTURE)?;
    route.call_ready(first, ptr_high)?;
    route.call_ready(&capture.rotate, raw_high_c)?;
    raw_lookup(profile, &mut route, raw_high, 1)?;
    route.call_ready(second, HIGH)?;
    route.call_ready(&capture.rotate, high_c)?;
    high_lookup(profile, &mut route, high_result)?;
    commit(
        &mut route,
        (blocks, scratch_rotate),
        (HIGH, scratch_high),
        [state_h, scratch_h],
    )?;
    route.call_ready(&capture.rotate, low_c)?;
    low_lookup(profile, &mut route, low_result, true)?;
    commit(&mut route, (blocks, scratch_rotate), (LOW, scratch_low), [
        state_l, scratch_l,
    ])?;
    finish_byte_route(&mut route, capture, [pointer_l, pointer_h])
}

fn finish_byte_route(
    route: &mut Route<'_>,
    capture: &Blocks,
    pointer_resets: [u32; 2],
) -> Result<(), BuildError> {
    let [capture_reset, _, _] = CONSTANTS;
    reset(route, capture, CAPTURE, capture_reset)?;
    for ((pointer, constant), [prefix, seed]) in
        POINTERS.into_iter().zip(pointer_resets).zip(RAW_RESTORE)
    {
        reset(route, capture, pointer, constant)?;
        for address in [prefix, seed, pointer] {
            route.call_ready(&capture.crazy, address)?;
        }
    }
    route.enter_ready(&capture.branch, LOOP_RETURN)?;
    let [first_table, _] = RAW_TABLES;
    if route.cursor >= first_table {
        return Err(LAYOUT);
    }
    Ok(())
}

// Split the most expensive linear walk at each iteration. This keeps
// the finite set of near-frame anchors useful across sparse table rows.
fn route_anchors(
    profile: &ProfileDescriptor,
    words: &Words,
) -> Result<TargetAnchors, BuildError> {
    let addresses = words
        .iter()
        .map(|(&address, &value)| {
            let virgin = if address.is_multiple_of(2) {
                7_174_416
            } else {
                37
            };
            let inverse = crazy(profile, ALL_ONES, value);
            let weight = 1u64.saturating_add(u64::from(
                crazy(profile, virgin, inverse) != value,
            ));
            (address, weight)
        })
        .collect::<Vec<_>>();
    let mut cuts = vec![0usize, addresses.len()];
    let slots = target_slots()?;
    let count = slots.len();
    for _ in 1..count {
        let mut best = (0u64, 0usize);
        for endpoints in cuts.windows(2) {
            let [start, end] = endpoints else {
                return Err(LAYOUT);
            };
            let candidate = best_anchor_split(&addresses, (*start, *end))?;
            if candidate.0 > best.0 {
                best = candidate;
            }
        }
        if best.0 == 0 {
            break;
        }
        cuts.push(best.1);
        cuts.sort_unstable();
    }
    // Give densely used partitions the shortest near-frame walk. The
    // target lookup compares every eligible anchor by total walk cost.
    let mut partitions = Vec::new();
    for endpoints in cuts.windows(2) {
        let [start, end] = endpoints else {
            return Err(LAYOUT);
        };
        partitions.push((
            addresses
                .get(*start..*end)
                .ok_or(LAYOUT)?
                .iter()
                .map(|&(_, weight)| weight)
                .sum::<u64>(),
            addresses.get(*start).ok_or(LAYOUT)?.0,
        ));
    }
    partitions.sort_unstable_by_key(|&(size, base)| (Reverse(size), base));
    let anchors = slots
        .into_iter()
        .zip(partitions.into_iter().map(|(_, base)| base))
        .collect();
    Ok(anchors)
}

fn best_anchor_split(
    addresses: &[(u32, u64)],
    (start, end): (usize, usize),
) -> Result<AnchorSplit, BuildError> {
    let mut best = (0u64, 0usize);
    let base = addresses.get(start).ok_or(LAYOUT)?.0;
    let mut suffix_weight = 0u64;
    for index in (start.checked_add(1).ok_or(LAYOUT)?..end).rev() {
        let &(address, weight) = addresses.get(index).ok_or(LAYOUT)?;
        suffix_weight = suffix_weight.checked_add(weight).ok_or(LAYOUT)?;
        let distance = address.checked_sub(base).ok_or(LAYOUT)?;
        let benefit = u64::from(distance)
            .checked_mul(suffix_weight)
            .ok_or(LAYOUT)?;
        if benefit > best.0 {
            best = (benefit, index);
        }
    }
    Ok(best)
}

fn terminal(emitter: &mut Emitter<'_>) -> Result<[u32; 2], BuildError> {
    use LinearOpcode::{
        CrazyData, Halt, NoOperation, OutputByte, RelocateDataPointer,
        RotateData,
    };
    emitter
        .pad_to_entry(usize::try_from(TERMINAL).map_err(|_error| LAYOUT)?, 0)?;
    // Select the high output word using the same split-state index.
    for op in [
        RotateData,
        RelocateDataPointer,
        CrazyData,
        RelocateDataPointer,
        RotateData,
        RelocateDataPointer,
        CrazyData,
    ] {
        let _: u32 = emitter.append(op)?;
    }
    for _ in 0..6u32 {
        let _: u32 = emitter.append(NoOperation)?;
    }
    // Load high contribution, stage it, and then select low contribution.
    for op in [
        RelocateDataPointer,
        RotateData,
        RelocateDataPointer,
        RelocateDataPointer,
        CrazyData,
        RelocateDataPointer,
        CrazyData,
        RelocateDataPointer,
        RotateData,
        RelocateDataPointer,
        CrazyData,
        RelocateDataPointer,
        RotateData,
        RelocateDataPointer,
        RelocateDataPointer,
        CrazyData,
        RelocateDataPointer,
        CrazyData,
    ] {
        let _: u32 = emitter.append(op)?;
    }
    Ok([emitter.append(OutputByte)?, emitter.append(Halt)?])
}

fn checksum_lookup_blocks(
    profile: &ProfileDescriptor,
) -> Result<[AccessBlock; 5], BuildError> {
    Ok([
        AccessBlock::indexed_immutable_load(profile, code(CODE_BASE, 11, 0)?)?,
        AccessBlock::indexed_immutable_field(
            profile,
            code(CODE_BASE, 13, 0)?,
            false,
        )?,
        AccessBlock::indexed_immutable_load(profile, code(CODE_BASE, 15, 0)?)?,
        AccessBlock::indexed_immutable_load(profile, code(CODE_BASE, 17, 0)?)?,
        AccessBlock::indexed_immutable_field(
            profile,
            code(CODE_BASE, 19, 0)?,
            true,
        )?,
    ])
}

fn checksum_lookup_sites(
    lookups: &[AccessBlock; 5],
) -> Result<LookupSites, BuildError> {
    let mut sites = [[0; 2]; 5];
    for (index, (site, block)) in sites.iter_mut().zip(lookups).enumerate() {
        let offset = if index == 1 || index == 4 {
            4
        } else {
            3
        };
        *site = [
            plus(block.start, offset)?,
            plus(block.start, plus(offset, 1)?)?,
        ];
    }
    Ok(sites)
}

/// Execute the full byte checksum recurrence through genuine guest EOF.
///
/// The low transition emits a carry of zero, one or two. The high
/// transition consumes that carry and the same raw byte's parity.
/// # Errors
/// Refuses unsupported profiles or exhausted physical geometry.
pub fn build_relocated_recurrent_checksum_source(
    profile: &ProfileDescriptor,
) -> Result<RelocatedRecurrentChecksumSource, BuildError> {
    let mut emitter = bootstrap(profile, SOURCE_CELLS, BOUNDS)?;
    let blocks = Mod4Blocks::new(profile, CODE_BASE)?;
    let lookups = checksum_lookup_blocks(profile)?;
    let mut words = data_words(profile)?;
    let entry = main_route(&blocks.capture, &mut words)?;
    let scratch_rotate =
        AccessBlock::rotated_scratch(profile, code(CODE_BASE, 21, 0)?)?;
    byte_route(profile, &blocks, (&lookups, &scratch_rotate), &mut words)?;
    output_table(profile, &mut words)?;
    let anchors = route_anchors(profile, &words)?;
    initialize_chunk_seeds(
        &mut emitter,
        &words,
        &anchors,
        (7_175_601, 7_176_600),
    )?;
    go_target(&mut emitter, entry, &anchors)?;
    let _: u32 = emitter.append_indirect()?;
    for block in blocks
        .capture
        .ordered()
        .into_iter()
        .chain(&blocks.load)
        .chain(&lookups)
        .chain([&scratch_rotate])
    {
        block.emit(&mut emitter)?;
    }
    let [output, halt] = terminal(&mut emitter)?;
    let [first, second, third] = &blocks.capture.reset;
    let [load_first, load_second] = &blocks.load;
    let sites = checksum_lookup_sites(&lookups)?;
    Ok(RelocatedRecurrentChecksumSource {
        capture: RelocatedRecurrentCaptureSource {
            branch: blocks.capture.branch.operation_site()?,
            capture: CAPTURE,
            crazy: blocks.capture.crazy.operation_site()?,
            halt,
            input: blocks.capture.input.operation_site()?,
            output,
            reset: [
                first.operation_site()?,
                second.operation_site()?,
                third.operation_site()?,
            ],
            rotate: blocks.capture.rotate.operation_site()?,
            source: emitter.finish()?,
            states: STATES,
        },
        load: [load_first.operation_site()?, load_second.operation_site()?],
        lookup: sites,
        pointers: POINTERS,
        scratch: SCRATCH,
        scratch_rotate: scratch_rotate.operation_site()?,
        state: [LOW, HIGH],
        terminal: TERMINAL,
    })
}
