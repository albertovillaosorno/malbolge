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
//   - Chunked inverse-seed synthesis for recurrent physical layouts.
// - Must-Not:
//   - Admit guest arithmetic or assume proposed writes have executed.
// - Allows:
//   - Inputs: bounded N15 physical data plans.
//   - Outputs: proposed bootstrap operations and route materialization.
//   - Side effects: none; independent VM replay owns acceptance.
// - Split-When:
//   - General physical seed allocation replaces fixed geometry.
// - Merge-When:
//   - Recurrent layouts use a shared compact initializer.
// - Summary:
//   - Synthesize inverse seeds in five reusable three-trit chunks.

use std::collections::{BTreeMap, BTreeSet};
use std::sync::OnceLock;

use malbolge::profile_crazy;

use super::super::super::super::LinearOpcode;
use super::super::super::{BuildError, Emitter, FRAME, LAYOUT};
use super::super::after_store;
use super::{
    ALL_ONES, ALL_TWOS, ANCHOR_END, ANCHOR_START, CAPTURE, EXTRA_SEED_ANCHOR,
    NEAR_ONES, NEAR_TWOS, NEAR_ZERO, SEED_ANCHOR, SEEDS, SeedAccess, SeedPlan,
    Words, crazy, immutable_seed_prefix, plan_seeds_with_pairs, previous,
    rotate, store_anchored,
};

// A compact seed bootstrap reuses one 27-entry mask bank for the
// five three-trit chunks of each N15 word. Scratch rotations bring each
// chunk into the same low-trit position.
// Reuse the source prefix's single trit marker to bootstrap two local
// immutable columns. All six local words precede the ordinary scratch.
const BOOT_SPIKE: u32 = 7_174_427;
const BOOT_ZERO_PREFIX: u32 = 7_174_429;
const BOOT_ZERO_COLUMN: u32 = 7_174_431;
const BOOT_ONE_PREFIX: u32 = 7_174_433;
const BOOT_ONE_COLUMN: u32 = 7_174_435;
const BOOT_WORD: u32 = 7_174_437;
const CHUNK_SCRATCH: u32 = 7_174_441;
const CHUNK_NEXT: u32 = CHUNK_SCRATCH + 1;
const CHUNK_TWOS: u32 = CHUNK_SCRATCH + 2;
const CHUNK_RETURN: u32 = CHUNK_SCRATCH + 4;
// An initialized shortcut avoids the long forward walk from scratch.
const CHUNK_CONSTANTS: u32 = CHUNK_SCRATCH + 6;
const CHUNK_ANCHOR: u32 = ANCHOR_START;
// Seven immutable pointers cover four mask pairs each. They precede
// the mask bank so the bootstrap can still walk to virgin masks before
// installing the pointers. The fast path uses a two-hop page lookup.
const CHUNK_PAGE_BANK: u32 = 7_176_587;
const CHUNK_PAGE_WIDTH: u32 = 4;
const CHUNK_PAGE_COUNT: u32 = 7;
const CHUNK_BANK: u32 = 7_176_601;
const CHUNK_END: u32 = CHUNK_BANK + 111;
const CHUNK_RESET: u32 = 7_174_468;
// Each elementary mask changes at most one of the three low trits.
// The final mask is the initial scratch-return pointer.
const ELEMENTARY_COLUMNS: [u32; 7] = [8, 17, 20, 23, 24, 25, 27];
// The directory is between the immutable chunk-mask bank and the
// operand tape. Its odd pointers leave each even reset word virgin.
const SEED_DIRECTORY: u32 = ANCHOR_START + 2;
const DIRECTORY_BANK: u32 = 7_176_721;
const DIRECTORY_STRIDE: u32 = 48;
// Eight short direct entries into the paired seed bank. The even roots
// are installed last, after the neighboring odd roots stop using them as
// resets.
const HOT_SEED_ROOTS: [(u32, u32); 8] = [
    (7_174_475, SEEDS + 36),
    (7_174_476, SEEDS + 72),
    (7_174_477, SEEDS + 108),
    (7_174_478, SEEDS + 144),
    (7_174_479, SEEDS + 180),
    (7_174_480, SEEDS + 216),
    (7_174_481, SEEDS + 252),
    (7_174_482, SEEDS + 288),
];
const DIRECTORY_END: u32 = 7_176_900;
const TARGET_RETURN: u32 = 7_174_491;
const TARGET_ROOTS: [u32; 12] = [
    TARGET_RETURN,
    7_174_493,
    7_174_495,
    7_174_497,
    7_174_499,
    7_174_501,
    7_174_503,
    7_174_505,
    7_174_507,
    7_174_509,
    7_174_511,
    7_174_513,
];
const TARGET_BANKS: [u32; 12] = [
    7_300_001, 7_300_201, 7_300_401, 7_300_601, 7_300_801, 7_301_001,
    7_301_201, 7_301_401, 7_301_601, 7_301_801, 7_302_001, 7_302_201,
];
const TARGET_PAGE_COUNT: u32 = 24;
const TARGET_DIRECT_START: u32 = 7_174_515;

static PATCH_CHOICES: OnceLock<PatchChoices> = OnceLock::new();

type PatchChoices = BTreeMap<(u32, u32), [u32; 2]>;
type ChunkMasks = Vec<(u32, u32)>;
type ChunkPage = (u32, u32);
type SeedDirectory = Vec<(u32, u32)>;
type SeedPathCost = (SeedPath, u32);

#[derive(Clone, Copy)]
enum SeedPath {
    Direct { root: u32, base: u32 },
    Page { slot: u32, page: u32 },
}

#[derive(Clone, Copy)]
pub(super) enum TargetSlot {
    Direct(u32),
    Page { bank: u32, root: u32, slot: u32 },
}

impl TargetSlot {
    pub(super) fn cost(self) -> u64 {
        match self {
            Self::Direct(anchor) => u64::from(anchor),
            Self::Page { bank, root, slot } => u64::from(root)
                .saturating_add(u64::from(slot.saturating_sub(bank)))
                .saturating_add(1),
        }
    }
}

pub(super) type TargetAnchors = Vec<(TargetSlot, u32)>;

struct SeedRouting<'directory> {
    directory: &'directory [(u32, u32)],
    extra: (u32, u32),
}

#[derive(Clone, Copy)]
enum ChunkSeedAccess {
    // A one-use target receives its inverse directly from scratch.
    Direct,
    Shared(SeedAccess),
}

type ChunkSeedMap = BTreeMap<u32, ChunkSeedAccess>;
type ChunkSeedPlan = (ChunkSeedMap, Vec<(u32, u32)>);
type ClusterPlan = (BTreeSet<u32>, BTreeSet<u32>);
type ClusterSweep<'targets> = (&'targets [u32], &'targets mut BTreeSet<u32>);
type ClusterProtection<'targets> = (&'targets BTreeSet<u32>, (u32, u32));
type ChunkMaterialization<'seeds> = (
    &'seeds ChunkSeedMap,
    SeedRouting<'seeds>,
    &'seeds BTreeSet<u32>,
);

type InitialMaterialization<'plan, 'scratch> = (
    &'plan ChunkSeedMap,
    &'plan SeedRouting<'plan>,
    Vec<(u32, u32)>,
    &'scratch mut ChunkWord,
);

// (address, final word, inverse word). Cache inverses once rather than
// recalculating their fifteen-trit transforms at every selection.
type MaterializationEntry = (u32, u32, u32);

struct ChunkWord {
    value: u32,
}

impl ChunkWord {
    fn synthesize(
        &mut self,
        emitter: &mut Emitter<'_>,
        value: u32,
    ) -> Result<(), BuildError> {
        // Both candidates append to the same physical address and leave
        // the same scratch value in A. Measure their actual emitted
        // walks, not just the number of masks.
        let start = emitter.source.len();
        let data = emitter.data;
        let patch_result = patch_word(emitter, self.value, value);
        let patch_end = emitter.data;
        let patch = emitter.source.split_off(start);
        emitter.data = data;
        let fresh_result = chunk_word(emitter, value, true);
        if patch_result.is_ok()
            && (fresh_result.is_err()
                || patch.len() < emitter.source.len().saturating_sub(start))
        {
            emitter.source.truncate(start);
            emitter.source.extend(patch);
            emitter.data = patch_end;
        } else {
            fresh_result?;
        }
        self.value = value;
        Ok(())
    }
}

pub(super) fn target_slots() -> Result<Vec<TargetSlot>, BuildError> {
    let mut slots = Vec::new();
    for root in (TARGET_DIRECT_START..ANCHOR_END).step_by(2) {
        slots.push(TargetSlot::Direct(root));
    }
    for (root, bank) in TARGET_ROOTS.into_iter().zip(TARGET_BANKS) {
        for offset in 0..TARGET_PAGE_COUNT {
            slots.push(TargetSlot::Page {
                bank,
                root,
                slot: bank
                    .checked_add(offset.checked_mul(2).ok_or(LAYOUT)?)
                    .ok_or(LAYOUT)?,
            });
        }
    }
    slots.sort_by_key(|slot| slot.cost());
    Ok(slots)
}

fn chunk_access(
    emitter: &mut Emitter<'_>,
    address: u32,
    operation: LinearOpcode,
) -> Result<(), BuildError> {
    emitter.go(address)?;
    let _: u32 = emitter.linear(operation)?;
    emitter.walk(CHUNK_RESET)
}

fn reset_chunk_word(
    emitter: &mut Emitter<'_>,
    address: u32,
    fast: bool,
) -> Result<(), BuildError> {
    // An all-one accumulator maps each trit to either zero or two.
    // The second fold uses that same result as both operands.
    chunk_rotate(emitter, NEAR_ONES, fast)?;
    chunk_access(emitter, address, LinearOpcode::CrazyData)?;
    chunk_access(emitter, address, LinearOpcode::CrazyData)
}

fn chunk_page(page: u32) -> Result<ChunkPage, BuildError> {
    if page >= CHUNK_PAGE_COUNT {
        return Err(LAYOUT);
    }
    let slot = CHUNK_PAGE_BANK
        .checked_add(page.checked_mul(2).ok_or(LAYOUT)?)
        .ok_or(LAYOUT)?;
    let base = CHUNK_BANK
        .checked_add(
            page.checked_mul(CHUNK_PAGE_WIDTH)
                .and_then(|value| value.checked_mul(4))
                .ok_or(LAYOUT)?,
        )
        .ok_or(LAYOUT)?;
    Ok((slot, base))
}

fn read_chunk_mask(
    emitter: &mut Emitter<'_>,
    index: u32,
    fast: bool,
) -> Result<(), BuildError> {
    let address = CHUNK_BANK
        .checked_add(index.checked_mul(4).ok_or(LAYOUT)?)
        .ok_or(LAYOUT)?;
    chunk_rotate(emitter, NEAR_ONES, fast)?;
    emitter.go(CHUNK_ANCHOR)?;
    emitter.jump(CHUNK_PAGE_BANK)?;
    if fast {
        let (slot, base) = chunk_page(index.div_euclid(CHUNK_PAGE_WIDTH))?;
        emitter.walk(slot)?;
        emitter.jump(base)?;
    }
    emitter.walk(address)?;
    let _: u32 = emitter.linear(LinearOpcode::CrazyData)?;
    emitter.walk(address.checked_add(2).ok_or(LAYOUT)?)?;
    let _: u32 = emitter.linear(LinearOpcode::CrazyData)?;
    after_store(emitter)
}

fn apply_chunk_column(
    emitter: &mut Emitter<'_>,
    column: u32,
    fast: bool,
) -> Result<(), BuildError> {
    // The two local immutable columns already encode masks 24 and 25.
    // After their second fold, a short forward walk reaches the scratch
    // directly rather than taking a page lookup and an indirect return.
    if fast && matches!(column, 24 | 25) {
        let prefix = if column == 24 {
            BOOT_ZERO_PREFIX
        } else {
            BOOT_ONE_PREFIX
        };
        fast_rotate(emitter, NEAR_ONES)?;
        emitter.go(prefix)?;
        let _: u32 = emitter.linear(LinearOpcode::CrazyData)?;
        emitter.walk(prefix.checked_add(2).ok_or(LAYOUT)?)?;
        let _: u32 = emitter.linear(LinearOpcode::CrazyData)?;
        emitter.walk(CHUNK_SCRATCH)?;
    } else {
        read_chunk_mask(emitter, column, fast)?;
        if fast {
            emitter.jump(CHUNK_SCRATCH)?;
        } else {
            emitter.go(CHUNK_SCRATCH)?;
        }
    }
    let _: u32 = emitter.linear(LinearOpcode::CrazyData)?;
    emitter.walk(CHUNK_TWOS)?;
    let _: u32 = emitter.linear(LinearOpcode::RotateData)?;
    emitter.walk(CHUNK_RETURN)?;
    emitter.jump(CHUNK_SCRATCH)?;
    let _: u32 = emitter.linear(LinearOpcode::CrazyData)?;
    Ok(())
}

fn advance_chunk(emitter: &mut Emitter<'_>) -> Result<(), BuildError> {
    for _ in 0..3u32 {
        if emitter.data != CHUNK_NEXT {
            emitter.go(CHUNK_RETURN)?;
        }
        emitter.jump(CHUNK_SCRATCH)?;
        let _: u32 = emitter.linear(LinearOpcode::RotateData)?;
    }
    Ok(())
}

fn chunk_word(
    emitter: &mut Emitter<'_>,
    mut value: u32,
    fast: bool,
) -> Result<(), BuildError> {
    reset_chunk_word(emitter, CHUNK_SCRATCH, fast)?;
    let mut uniform = true;
    for _ in 0..5u32 {
        // On an all-one low chunk, the first mask fold and the all-two
        // fold produce the requested trits. Everywhere else two
        // all-two folds cancel. An already-one chunk needs neither fold.
        let part = value.rem_euclid(27);
        value = value.div_euclid(27);
        if part != 13 {
            let column =
                profile_crazy(ALL_ONES, profile_crazy(part, ALL_TWOS, 15), 15)
                    .rem_euclid(27);
            apply_chunk_column(emitter, column, fast)?;
            uniform = false;
        }
        if uniform {
            continue;
        }
        // Three rotations expose the next chunk. Rotation of the
        // initial uniform scratch would have no effect.
        advance_chunk(emitter)?;
    }
    emitter.walk(CHUNK_RESET)?;
    if value != 0 {
        return Err(LAYOUT);
    }
    Ok(())
}

// A pair of column folds acts independently on each trit. For the
// two transitions that cannot occur directly, use an intermediate
// trit and a second mask. The remaining trits use column two,
// which is the identity after both folds.
fn patch_columns(mut before: u32, mut after: u32) -> [u32; 2] {
    let mut columns = [0u32; 2];
    let mut place = 1u32;
    for _ in 0..3u32 {
        let digits: [u32; 2] = match (before.rem_euclid(3), after.rem_euclid(3))
        {
            (0, 1) => [0, 0],
            (0 | 1, 2) | (2, 1) => [0, 2],
            (1, 0) => [1, 2],
            (2, 0) => [0, 1],
            _ => [2, 2],
        };
        for (column, digit) in columns.iter_mut().zip(digits) {
            *column = column.saturating_add(digit.saturating_mul(place));
        }
        before = before.div_euclid(3);
        after = after.div_euclid(3);
        place = place.saturating_mul(3);
    }
    columns
}

// The cost from CHUNK_NEXT includes the accumulator reload, the
// mask lookup, and both scratch folds. The first mask of a patch may
// begin elsewhere, but its reload cost changes equally for every mask.
const fn fast_column_cost(column: u32) -> u32 {
    match column {
        26 => 0,
        24 | 25 => 38,
        _ => 36u32
            .saturating_add(
                2u32.saturating_mul(column.div_euclid(CHUNK_PAGE_WIDTH)),
            )
            .saturating_add(
                4u32.saturating_mul(column.rem_euclid(CHUNK_PAGE_WIDTH)),
            ),
    }
}

const fn pair_cost(pair: [u32; 2]) -> (u32, [u32; 2]) {
    let [first, second] = pair;
    (
        fast_column_cost(first).saturating_add(fast_column_cost(second)),
        pair,
    )
}

fn apply_low_column(value: u32, column: u32) -> u32 {
    profile_crazy(profile_crazy(value, column, 3), 26, 3)
}

fn record_patch_choices(choices: &mut PatchChoices, before: u32, first: u32) {
    let middle = apply_low_column(before, first);
    for second in 0..27u32 {
        let after = apply_low_column(middle, second);
        let pair = [first, second];
        let old = choices.entry((before, after)).or_insert(pair);
        if pair_cost(pair) < pair_cost(*old) {
            *old = pair;
        }
    }
}

fn fast_patch_choices() -> PatchChoices {
    let mut choices = BTreeMap::new();
    for before in 0..27u32 {
        for first in 0..27u32 {
            record_patch_choices(&mut choices, before, first);
        }
    }
    choices
}

fn fast_patch_columns(before: u32, after: u32) -> [u32; 2] {
    PATCH_CHOICES
        .get_or_init(fast_patch_choices)
        .get(&(before, after))
        .copied()
        .unwrap_or_else(|| patch_columns(before, after))
}

fn patch_chunk(
    emitter: &mut Emitter<'_>,
    before: u32,
    after: u32,
) -> Result<(), BuildError> {
    for column in
        fast_patch_columns(before.rem_euclid(27), after.rem_euclid(27))
    {
        if column != 26 {
            apply_chunk_column(emitter, column, true)?;
        }
    }
    Ok(())
}

fn reload_chunk(emitter: &mut Emitter<'_>) -> Result<(), BuildError> {
    // Read and restore the unchanged scratch with two local all-two folds.
    for _ in 0..2u32 {
        emitter.go(CHUNK_TWOS)?;
        let _: u32 = emitter.linear(LinearOpcode::RotateData)?;
        emitter.walk(CHUNK_RETURN)?;
        emitter.jump(CHUNK_SCRATCH)?;
        let _: u32 = emitter.linear(LinearOpcode::CrazyData)?;
    }
    emitter.walk(CHUNK_RESET)
}

fn patch_word(
    emitter: &mut Emitter<'_>,
    mut before: u32,
    mut after: u32,
) -> Result<(), BuildError> {
    // A low-only change already leaves the scratch in its canonical
    // orientation. The final mask fold produces the desired accumulator,
    // so rotating through all fifteen trits would merely reload it.
    if before.div_euclid(27) == after.div_euclid(27) {
        if before == after {
            return reload_chunk(emitter);
        }
        patch_chunk(emitter, before, after)?;
        emitter.walk(CHUNK_RESET)?;
        return Ok(());
    }
    for _ in 0..5u32 {
        patch_chunk(emitter, before, after)?;
        before = before.div_euclid(27);
        after = after.div_euclid(27);
        advance_chunk(emitter)?;
    }
    emitter.walk(CHUNK_RESET)?;
    if before != 0 || after != 0 {
        return Err(LAYOUT);
    }
    Ok(())
}

fn chunk_rotate(
    emitter: &mut Emitter<'_>,
    target: u32,
    fast: bool,
) -> Result<(), BuildError> {
    if fast {
        fast_rotate(emitter, target)
    } else {
        rotate(emitter, target)
    }
}

fn fast_go(emitter: &mut Emitter<'_>, target: u32) -> Result<(), BuildError> {
    if emitter.data > target {
        emitter.reset()?;
    }
    if target >= NEAR_ONES {
        if emitter.data == FRAME {
            emitter.jump(NEAR_ONES)?;
        } else if (CHUNK_NEXT..=CHUNK_CONSTANTS).contains(&emitter.data) {
            emitter.walk(CHUNK_CONSTANTS)?;
            emitter.jump(NEAR_ONES)?;
        }
    }
    emitter.walk(target)
}

fn fast_rotate(
    emitter: &mut Emitter<'_>,
    target: u32,
) -> Result<(), BuildError> {
    fast_go(emitter, target)?;
    let _: u32 = emitter.linear(LinearOpcode::RotateData)?;
    Ok(())
}

pub(super) fn go_target(
    emitter: &mut Emitter<'_>,
    address: u32,
    anchors: &[(TargetSlot, u32)],
) -> Result<(), BuildError> {
    let (path, base) = anchors
        .iter()
        .copied()
        .filter(|&(_, base)| base <= address)
        .min_by_key(|&(slot, base)| {
            slot.cost()
                .saturating_add(u64::from(address.saturating_sub(base)))
        })
        .ok_or(LAYOUT)?;
    match path {
        TargetSlot::Direct(anchor) => fast_go(emitter, anchor)?,
        TargetSlot::Page { bank, root, slot } => {
            fast_go(emitter, root)?;
            emitter.jump(bank)?;
            emitter.walk(slot)?;
        },
    }
    emitter.jump(base)?;
    emitter.walk(address)
}

fn fast_store(
    emitter: &mut Emitter<'_>,
    address: u32,
    anchors: &[(TargetSlot, u32)],
    reset: u32,
) -> Result<(), BuildError> {
    go_target(emitter, address, anchors)?;
    let _: u32 = emitter.linear(LinearOpcode::CrazyData)?;
    emitter.walk(reset)
}

// A sorted-by-value materialization may revisit a lower target. Every
// return must skip the even cells that have already become guest data.
fn target_reset(
    address: u32,
    protected: &BTreeSet<u32>,
    extra: (u32, u32),
    limit: u32,
) -> Result<u32, BuildError> {
    let mut reset = address.checked_add(1).ok_or(LAYOUT)?;
    if !reset.is_multiple_of(2) {
        reset = reset.checked_add(1).ok_or(LAYOUT)?;
    }
    while protected.contains(&reset) {
        reset = reset.checked_add(2).ok_or(LAYOUT)?;
    }
    if reset >= limit
        || (extra.0..=DIRECTORY_END).contains(&reset)
        || reset >= TARGET_BANKS[0]
    {
        return Err(LAYOUT);
    }
    Ok(reset)
}

fn seed_directory(extra: (u32, u32)) -> Result<SeedDirectory, BuildError> {
    let mut directory = Vec::new();
    for (start, end) in [(SEEDS, 7_174_970), extra] {
        for base in (start..end).step_by(
            usize::try_from(DIRECTORY_STRIDE).map_err(|_error| LAYOUT)?,
        ) {
            let address = DIRECTORY_BANK
                .checked_add(
                    u32::try_from(directory.len())
                        .map_err(|_error| LAYOUT)?
                        .checked_mul(2)
                        .ok_or(LAYOUT)?,
                )
                .ok_or(LAYOUT)?;
            if address >= DIRECTORY_END {
                return Err(LAYOUT);
            }
            directory.push((address, base));
        }
    }
    Ok(directory)
}

fn seed_path(
    address: u32,
    routing: &SeedRouting<'_>,
) -> Result<SeedPathCost, BuildError> {
    let extra = routing.extra;
    let (mut root, mut base) = if (extra.0..extra.1).contains(&address) {
        (EXTRA_SEED_ANCHOR, extra.0)
    } else {
        (SEED_ANCHOR, SEEDS)
    };
    let (slot, page) = routing
        .directory
        .iter()
        .copied()
        .rev()
        .find(|&(_, page)| page <= address)
        .ok_or(LAYOUT)?;
    let mut direct = root
        .checked_add(address.checked_sub(base).ok_or(LAYOUT)?)
        .ok_or(LAYOUT)?;
    if !(extra.0..extra.1).contains(&address) {
        for (candidate_root, candidate_base) in HOT_SEED_ROOTS {
            if candidate_base > address {
                continue;
            }
            let cost = candidate_root
                .checked_add(address.checked_sub(candidate_base).ok_or(LAYOUT)?)
                .ok_or(LAYOUT)?;
            if cost < direct {
                direct = cost;
                root = candidate_root;
                base = candidate_base;
            }
        }
    }
    let indirect = SEED_DIRECTORY
        .checked_add(slot.checked_sub(DIRECTORY_BANK).ok_or(LAYOUT)?)
        .and_then(|value| value.checked_add(1))
        .and_then(|value| value.checked_add(address.checked_sub(page)?))
        .ok_or(LAYOUT)?;
    if indirect < direct {
        Ok((SeedPath::Page { slot, page }, indirect))
    } else {
        Ok((SeedPath::Direct { root, base }, direct))
    }
}

fn go_seed(
    emitter: &mut Emitter<'_>,
    address: u32,
    routing: &SeedRouting<'_>,
) -> Result<(), BuildError> {
    let (path, _) = seed_path(address, routing)?;
    match path {
        SeedPath::Page { slot, page } => {
            fast_go(emitter, SEED_DIRECTORY)?;
            emitter.jump(DIRECTORY_BANK)?;
            emitter.walk(slot)?;
            emitter.jump(page)?;
        },
        SeedPath::Direct { root, base } => {
            fast_go(emitter, root)?;
            emitter.jump(base)?;
        },
    }
    emitter.walk(address)
}

fn reorder_seed_group(
    entries: &mut [(u32, u32)],
    routing: &SeedRouting<'_>,
    plan: &mut ChunkSeedPlan,
    (paired, single_use): (bool, &BTreeSet<u32>),
) -> Result<(), BuildError> {
    entries.sort_unstable_by_key(|&(address, _)| address);
    let mut slots = entries
        .iter()
        .map(|&(address, _)| {
            seed_path(address, routing).map(|(_, cost)| (cost, address))
        })
        .collect::<Result<Vec<_>, _>>()?;
    slots.sort_unstable();
    for (&(_, value), (_, address)) in entries.iter().zip(slots) {
        let inverse = profile_crazy(ALL_ONES, value, 15);
        let access = if paired {
            plan.1.push((address, immutable_seed_prefix(inverse, 15)?));
            plan.1
                .push((address.checked_add(2).ok_or(LAYOUT)?, inverse));
            ChunkSeedAccess::Shared(SeedAccess::ImmutablePair(address))
        } else if single_use.contains(&value) {
            ChunkSeedAccess::Direct
        } else {
            plan.1.push((address, inverse));
            ChunkSeedAccess::Shared(SeedAccess::Reversible(address))
        };
        let _old = plan.0.insert(value, access);
    }
    Ok(())
}

// The original planner ranks values by frequency, assigning the first
// 80 to pairs and the remainder to single-word slots. Preserve that
// partition but reorder each group by actual minimum route cost.
fn reorder_seed_slots(
    (addresses, _): SeedPlan,
    routing: &SeedRouting<'_>,
    single_use: &BTreeSet<u32>,
) -> Result<ChunkSeedPlan, BuildError> {
    let mut pairs = Vec::new();
    let mut singles = Vec::new();
    for (value, access) in addresses {
        match access {
            SeedAccess::ImmutablePair(address) => pairs.push((address, value)),
            SeedAccess::Reversible(address) => singles.push((address, value)),
        }
    }
    let mut plan = (BTreeMap::new(), Vec::new());
    reorder_seed_group(&mut pairs, routing, &mut plan, (true, single_use))?;
    reorder_seed_group(&mut singles, routing, &mut plan, (false, single_use))?;
    Ok(plan)
}

fn store_seed(
    emitter: &mut Emitter<'_>,
    address: u32,
    routing: &SeedRouting<'_>,
) -> Result<(), BuildError> {
    go_seed(emitter, address, routing)?;
    let _: u32 = emitter.linear(LinearOpcode::CrazyData)?;
    after_store(emitter)
}

fn fast_load(
    emitter: &mut Emitter<'_>,
    seed: ChunkSeedAccess,
    (inverse, accumulator): (u32, Option<u32>),
    routing: &SeedRouting<'_>,
) -> Result<(), BuildError> {
    // The preceding target's final store produces its exact value in A.
    // When that value is known, use a fold only if it preserves the
    // selected seed (or its immutable prefix) and produces the inverse.
    if let ChunkSeedAccess::Shared(SeedAccess::ImmutablePair(prefix)) = seed {
        let operand = prefix.checked_add(2).ok_or(LAYOUT)?;
        if accumulator
            .is_some_and(|acc| profile_crazy(inverse, acc, 15) == inverse)
        {
            go_seed(emitter, operand, routing)?;
        } else {
            let prefix_word = immutable_seed_prefix(inverse, 15)?;
            if !accumulator.is_some_and(|acc| {
                profile_crazy(prefix_word, acc, 15) == prefix_word
            }) {
                fast_rotate(emitter, NEAR_ONES)?;
            }
            go_seed(emitter, prefix, routing)?;
            let _: u32 = emitter.linear(LinearOpcode::CrazyData)?;
            emitter.walk(operand)?;
        }
        let _: u32 = emitter.linear(LinearOpcode::CrazyData)?;
        // Every paired seed has a dedicated target-directory return in
        // the following even word. This preserves A and avoids the frame
        // reset and the walk past the uniform constants for each target.
        return emitter.jump(TARGET_RETURN);
    }
    let address = match seed {
        ChunkSeedAccess::Direct => return Err(LAYOUT),
        ChunkSeedAccess::Shared(SeedAccess::Reversible(address)) => address,
        ChunkSeedAccess::Shared(SeedAccess::ImmutablePair(_)) => {
            return Err(LAYOUT);
        },
    };
    if accumulator.is_some_and(|acc| profile_crazy(inverse, acc, 15) == inverse)
    {
        go_seed(emitter, address, routing)?;
        let _: u32 = emitter.linear(LinearOpcode::CrazyData)?;
        return after_store(emitter);
    }
    for pass in 0..2u32 {
        if pass != 0 || accumulator != Some(ALL_TWOS) {
            fast_rotate(emitter, NEAR_TWOS)?;
        }
        go_seed(emitter, address, routing)?;
        let _: u32 = emitter.linear(LinearOpcode::CrazyData)?;
        after_store(emitter)?;
    }
    Ok(())
}

fn chunk_masks() -> Result<ChunkMasks, BuildError> {
    let mut masks = Vec::new();
    for index in 0..28u32 {
        let value = if index == 27 {
            profile_crazy(ALL_ONES, previous(CHUNK_SCRATCH)?, 15)
        } else {
            ALL_TWOS
                .checked_sub(26)
                .and_then(|base| base.checked_add(index))
                .ok_or(LAYOUT)?
        };
        let address = CHUNK_BANK
            .checked_add(index.checked_mul(4).ok_or(LAYOUT)?)
            .ok_or(LAYOUT)?;
        masks.push((address, immutable_seed_prefix(value, 15)?));
        masks.push((address.checked_add(2).ok_or(LAYOUT)?, value));
    }
    Ok(masks)
}

fn elementary_mask(address: u32) -> bool {
    let column = address.saturating_sub(CHUNK_BANK).div_euclid(4);
    ELEMENTARY_COLUMNS.contains(&column)
}

// The six single-trit columns suffice to synthesize every other
// three-trit mask, starting from a uniform high prefix. The local
// one-trit columns need only bootstrap the seven elementary pairs.
fn synthesize_mask_word(
    emitter: &mut Emitter<'_>,
    value: u32,
) -> Result<(), BuildError> {
    let base = if value.div_euclid(27) == ALL_ONES.div_euclid(27) {
        ALL_ONES
    } else if value.div_euclid(27) == ALL_TWOS.div_euclid(27) {
        ALL_TWOS
    } else {
        return Err(LAYOUT);
    };
    reset_chunk_word(emitter, CHUNK_SCRATCH, false)?;
    if base == ALL_TWOS {
        rotate(emitter, NEAR_TWOS)?;
        chunk_access(emitter, CHUNK_SCRATCH, LinearOpcode::CrazyData)?;
    }
    for mut column in patch_columns(base.rem_euclid(27), value.rem_euclid(27)) {
        for place in [1u32, 3, 9] {
            let digit = column.rem_euclid(3);
            column = column.div_euclid(3);
            if digit == 2 {
                continue;
            }
            let elementary = 26u32
                .checked_sub(
                    2u32.checked_sub(digit)
                        .ok_or(LAYOUT)?
                        .checked_mul(place)
                        .ok_or(LAYOUT)?,
                )
                .ok_or(LAYOUT)?;
            if !ELEMENTARY_COLUMNS.contains(&elementary) {
                return Err(LAYOUT);
            }
            apply_chunk_column(emitter, elementary, false)?;
        }
    }
    Ok(())
}

fn initialize_chunk_masks(
    emitter: &mut Emitter<'_>,
    masks: &[(u32, u32)],
) -> Result<(), BuildError> {
    let anchors = [(CHUNK_ANCHOR, CHUNK_PAGE_BANK)];
    for &(address, value) in masks {
        if elementary_mask(address) {
            continue;
        }
        rotate(emitter, NEAR_ZERO)?;
        store_anchored(emitter, address, &anchors)?;
        synthesize_mask_word(emitter, profile_crazy(ALL_ONES, value, 15))?;
        store_anchored(emitter, address, &anchors)?;
    }
    Ok(())
}

// Install an immutable direct scratch return after each mask pair, only
// after the frame's fast reset has been initialized. The special
// pointer seed at index 27 retains its virgin reset, as do the even
// cells after each prefix.
fn initialize_chunk_returns(
    emitter: &mut Emitter<'_>,
) -> Result<(), BuildError> {
    let anchor = [(CHUNK_ANCHOR, CHUNK_PAGE_BANK)];
    for index in 0..27u32 {
        let address = CHUNK_BANK
            .checked_add(index.checked_mul(4).ok_or(LAYOUT)?)
            .and_then(|base| base.checked_add(3))
            .ok_or(LAYOUT)?;
        fast_rotate(emitter, NEAR_ZERO)?;
        store_anchored(emitter, address, &anchor)?;
        read_chunk_mask(emitter, 27, true)?;
        store_anchored(emitter, address, &anchor)?;
    }
    Ok(())
}

fn initialize_seed_directory(
    emitter: &mut Emitter<'_>,
    extra: (u32, u32),
    scratch: &mut ChunkWord,
) -> Result<SeedDirectory, BuildError> {
    let directory = seed_directory(extra)?;
    let directory_anchor = [(SEED_DIRECTORY, DIRECTORY_BANK)];
    for &(address, base) in &directory {
        rotate(emitter, NEAR_ZERO)?;
        store_anchored(emitter, address, &directory_anchor)?;
        scratch.synthesize(
            emitter,
            profile_crazy(ALL_ONES, previous(base)?, 15),
        )?;
        store_anchored(emitter, address, &directory_anchor)?;
    }
    Ok(directory)
}

// Install these returns only after the seed bank is complete: ordinary
// bootstrap stores still use the virgin even reset words until then.
fn initialize_seed_returns(
    emitter: &mut Emitter<'_>,
    seeds: &ChunkSeedMap,
    routing: &SeedRouting<'_>,
    scratch: &mut ChunkWord,
) -> Result<(), BuildError> {
    let mut returns = seeds
        .values()
        .filter_map(|seed| match seed {
            ChunkSeedAccess::Shared(SeedAccess::ImmutablePair(prefix)) => {
                Some(prefix.checked_add(3).ok_or(LAYOUT))
            },
            ChunkSeedAccess::Shared(SeedAccess::Reversible(_))
            | ChunkSeedAccess::Direct => None,
        })
        .collect::<Result<Vec<_>, _>>()?;
    returns.sort_unstable();
    let value = previous(TARGET_RETURN)?;
    let inverse = profile_crazy(ALL_ONES, value, 15);
    let normalize = profile_crazy(7_174_416, inverse, 15) != value;
    for address in returns {
        if !address.is_multiple_of(2) || !(SEEDS..7_174_970).contains(&address)
        {
            return Err(LAYOUT);
        }
        if normalize {
            fast_rotate(emitter, NEAR_ZERO)?;
            store_seed(emitter, address, routing)?;
        }
        scratch.synthesize(emitter, inverse)?;
        store_seed(emitter, address, routing)?;
    }
    Ok(())
}

fn initialize_target_pages(
    emitter: &mut Emitter<'_>,
    anchors: &[(TargetSlot, u32)],
    scratch: &mut ChunkWord,
) -> Result<(), BuildError> {
    let mut pages = anchors
        .iter()
        .filter_map(|&(path, base)| {
            if let TargetSlot::Page { bank, root, slot } = path {
                Some((slot, bank, root, base))
            } else {
                None
            }
        })
        .collect::<Vec<_>>();
    // Each bank consists of odd virgin cells separated by untouched
    // even reset cells. Alternating stores from A=0 normalize every
    // other slot, leaving zeros for a strictly smaller next sweep.
    for (root, bank) in TARGET_ROOTS.into_iter().zip(TARGET_BANKS) {
        let mut pending = pages
            .iter()
            .filter_map(|&(slot, page, _, _)| (page == bank).then_some(slot))
            .collect::<Vec<_>>();
        pending.sort_unstable();
        normalize_page_bank(emitter, (root, bank), pending)?;
    }
    pages.sort_unstable_by_key(|&(_, _, _, base)| base);
    for (slot, bank, root, base) in pages {
        let anchor = [(root, bank)];
        scratch.synthesize(
            emitter,
            profile_crazy(ALL_ONES, previous(base)?, 15),
        )?;
        store_anchored(emitter, slot, &anchor)?;
    }
    Ok(())
}

fn normalize_page_bank(
    emitter: &mut Emitter<'_>,
    (root, bank): (u32, u32),
    mut pending: Vec<u32>,
) -> Result<(), BuildError> {
    while !pending.is_empty() {
        rotate(emitter, NEAR_ZERO)?;
        emitter.go(root)?;
        emitter.jump(bank)?;
        for &slot in &pending {
            emitter.walk(slot)?;
            let _: u32 = emitter.linear(LinearOpcode::CrazyData)?;
        }
        after_store(emitter)?;
        pending = pending.into_iter().skip(1).step_by(2).collect();
    }
    Ok(())
}

fn target_roots(
    words: &Words,
    anchors: &[(TargetSlot, u32)],
    limit: u32,
) -> Result<SeedDirectory, BuildError> {
    let mut roots = BTreeMap::new();
    for &(path, base) in anchors {
        if !words.contains_key(&base) {
            return Err(LAYOUT);
        }
        let (root, landing) = match path {
            TargetSlot::Direct(root) => (root, base),
            TargetSlot::Page { bank, root, slot } => {
                let reset = slot.checked_add(1).ok_or(LAYOUT)?;
                if reset >= limit
                    || slot.is_multiple_of(2)
                    || words.contains_key(&slot)
                    || words.contains_key(&reset)
                {
                    return Err(LAYOUT);
                }
                (root, bank)
            },
        };
        if root <= SEED_DIRECTORY
            || root >= ANCHOR_END
            || roots
                .insert(root, previous(landing)?)
                .is_some_and(|old| old != landing.saturating_sub(1))
        {
            return Err(LAYOUT);
        }
    }
    Ok(roots.into_iter().collect())
}

// The prefix finishes with A=0 and a virgin odd loader cell at BOOT_SPIKE.
// One source marker makes a single ternary two; it is never used as code.
fn bootstrap_spike(emitter: &mut Emitter<'_>) -> Result<(), BuildError> {
    chunk_access(emitter, BOOT_SPIKE, LinearOpcode::CrazyData)?;
    rotate(emitter, FRAME)?;
    emitter.source_marker(LinearOpcode::CrazyData)?;
    chunk_access(emitter, BOOT_SPIKE, LinearOpcode::CrazyData)?;
    // Alternating folds of the two virgin loader phases establish
    // all ones, all zeroes, and an initial all-one target for the spikes.
    rotate(emitter, FRAME)?;
    for target in [NEAR_ONES, NEAR_ZERO, NEAR_TWOS] {
        crazy(emitter, target)?;
    }
    // With zeroes elsewhere, each rotated spike leaves the previously
    // written twos invariant and changes one more one to two.
    for _ in 0..15u32 {
        chunk_access(emitter, BOOT_SPIKE, LinearOpcode::RotateData)?;
        crazy(emitter, NEAR_TWOS)?;
    }
    Ok(())
}

fn bootstrap_columns(emitter: &mut Emitter<'_>) -> Result<(), BuildError> {
    bootstrap_spike(emitter)?;
    for address in [
        BOOT_ZERO_PREFIX,
        BOOT_ZERO_COLUMN,
        BOOT_ONE_COLUMN,
        BOOT_WORD,
    ] {
        rotate(emitter, NEAR_ZERO)?;
        chunk_access(emitter, address, LinearOpcode::CrazyData)?;
    }
    rotate(emitter, NEAR_ONES)?;
    chunk_access(emitter, BOOT_ONE_PREFIX, LinearOpcode::CrazyData)?;
    rotate(emitter, NEAR_TWOS)?;
    chunk_access(emitter, BOOT_ONE_COLUMN, LinearOpcode::CrazyData)?;
    // The source marker started in digit three. Move the two to digit zero
    // and turn an all-two word into the all-two-except-one column. Its
    // inverse under the all-one target is the all-two-except-zero column.
    for _ in 0..3u32 {
        chunk_access(emitter, BOOT_SPIKE, LinearOpcode::RotateData)?;
    }
    chunk_access(emitter, BOOT_ONE_COLUMN, LinearOpcode::CrazyData)?;
    chunk_access(emitter, BOOT_ZERO_COLUMN, LinearOpcode::CrazyData)?;
    // The zero column needs a two only in its zero position. Copy the
    // spike through the all-one scratch into its all-one prefix.
    for _ in 0..15u32 {
        chunk_access(emitter, BOOT_SPIKE, LinearOpcode::RotateData)?;
    }
    chunk_access(emitter, BOOT_WORD, LinearOpcode::CrazyData)?;
    chunk_access(emitter, BOOT_ZERO_PREFIX, LinearOpcode::CrazyData)?;
    Ok(())
}

fn boot_read_column(
    emitter: &mut Emitter<'_>,
    digit: u32,
) -> Result<(), BuildError> {
    let (prefix, column) = match digit {
        0 => (BOOT_ONE_PREFIX, BOOT_ONE_COLUMN),
        2 => (BOOT_ZERO_PREFIX, BOOT_ZERO_COLUMN),
        _ => return Err(LAYOUT),
    };
    rotate(emitter, NEAR_ONES)?;
    emitter.go(prefix)?;
    let _: u32 = emitter.linear(LinearOpcode::CrazyData)?;
    emitter.walk(column)?;
    let _: u32 = emitter.linear(LinearOpcode::CrazyData)?;
    emitter.walk(CHUNK_RESET)
}

// Each two-fold column updates one trit, leaving the other fourteen
// unchanged. Fifteen rotations return the word to its original orientation.
fn boot_word(
    emitter: &mut Emitter<'_>,
    mut value: u32,
) -> Result<(), BuildError> {
    reset_chunk_word(emitter, BOOT_WORD, false)?;
    for _ in 0..15u32 {
        let digit = value.rem_euclid(3);
        value = value.div_euclid(3);
        if digit != 1 {
            boot_read_column(emitter, digit)?;
            chunk_access(emitter, BOOT_WORD, LinearOpcode::CrazyData)?;
            rotate(emitter, NEAR_TWOS)?;
            chunk_access(emitter, BOOT_WORD, LinearOpcode::CrazyData)?;
        }
        chunk_access(emitter, BOOT_WORD, LinearOpcode::RotateData)?;
    }
    if value != 0 {
        return Err(LAYOUT);
    }
    Ok(())
}

fn prepare_elementary_masks(
    emitter: &mut Emitter<'_>,
    near: &[(u32, u32)],
    masks: &[(u32, u32)],
) -> Result<(), BuildError> {
    bootstrap_columns(emitter)?;
    for &(address, value) in near {
        rotate(emitter, NEAR_ZERO)?;
        crazy(emitter, address)?;
        if address >= CHUNK_ANCHOR {
            // The composed prefix writes both following even reset cells.
            emitter.walk(7_174_492)?;
        }
        boot_word(emitter, profile_crazy(ALL_ONES, value, 15))?;
        crazy(emitter, address)?;
        if address >= CHUNK_ANCHOR {
            // The composed prefix writes both following even reset cells.
            emitter.walk(7_174_492)?;
        }
    }
    let anchors = [(CHUNK_ANCHOR, CHUNK_PAGE_BANK)];
    for &(address, value) in masks {
        if !elementary_mask(address) {
            continue;
        }
        rotate(emitter, NEAR_ZERO)?;
        store_anchored(emitter, address, &anchors)?;
        boot_word(emitter, profile_crazy(ALL_ONES, value, 15))?;
        store_anchored(emitter, address, &anchors)?;
    }
    Ok(())
}

fn prepare_chunk_bank(
    emitter: &mut Emitter<'_>,
    near: &[(u32, u32)],
) -> Result<(), BuildError> {
    let masks = chunk_masks()?;
    prepare_elementary_masks(emitter, near, &masks)?;
    reset_chunk_word(emitter, CHUNK_TWOS, false)?;
    rotate(emitter, NEAR_TWOS)?;
    chunk_access(emitter, CHUNK_TWOS, LinearOpcode::CrazyData)?;
    reset_chunk_word(emitter, CHUNK_RETURN, false)?;
    read_chunk_mask(emitter, 27, false)?;
    chunk_access(emitter, CHUNK_RETURN, LinearOpcode::CrazyData)?;
    // The adjacent even loader word is reserved for direct scratch
    // revisits. Every ordinary reset still uses a different virgin cell.
    rotate(emitter, NEAR_ZERO)?;
    chunk_access(emitter, CHUNK_NEXT, LinearOpcode::CrazyData)?;
    read_chunk_mask(emitter, 27, false)?;
    chunk_access(emitter, CHUNK_NEXT, LinearOpcode::CrazyData)?;
    initialize_chunk_masks(emitter, &masks)?;
    initialize_chunk_pages(emitter)
}

fn initialize_chunk_pages(emitter: &mut Emitter<'_>) -> Result<(), BuildError> {
    let anchors = [(CHUNK_ANCHOR, CHUNK_PAGE_BANK)];
    for page in 0..CHUNK_PAGE_COUNT {
        let (address, landing) = chunk_page(page)?;
        rotate(emitter, NEAR_ZERO)?;
        store_anchored(emitter, address, &anchors)?;
        chunk_word(
            emitter,
            profile_crazy(ALL_ONES, previous(landing)?, 15),
            false,
        )?;
        store_anchored(emitter, address, &anchors)?;
    }
    Ok(())
}

fn initialize_chunk_roots(
    emitter: &mut Emitter<'_>,
    roots: SeedDirectory,
) -> Result<ChunkWord, BuildError> {
    reset_chunk_word(emitter, FRAME, false)?;
    let frame_seed = profile_crazy(ALL_ONES, previous(NEAR_ONES)?, 15);
    chunk_word(emitter, frame_seed, false)?;
    emitter.go(FRAME)?;
    let _: u32 = emitter.linear(LinearOpcode::CrazyData)?;
    emitter.walk(CHUNK_RESET)?;
    // The frame and the new shortcut share the same predecessor word.
    // The inverse remains in scratch after the frame commit. Reload it
    // without changing scratch and initialize the virgin odd slot.
    rotate(emitter, NEAR_ZERO)?;
    chunk_access(emitter, CHUNK_CONSTANTS, LinearOpcode::CrazyData)?;
    reload_chunk(emitter)?;
    chunk_access(emitter, CHUNK_CONSTANTS, LinearOpcode::CrazyData)?;
    initialize_chunk_returns(emitter)?;
    let mut scratch = ChunkWord { value: frame_seed };
    for (address, value) in roots {
        fast_rotate(emitter, NEAR_ZERO)?;
        fast_go(emitter, address)?;
        let _: u32 = emitter.linear(LinearOpcode::CrazyData)?;
        after_store(emitter)?;
        scratch.synthesize(emitter, profile_crazy(ALL_ONES, value, 15))?;
        fast_go(emitter, address)?;
        let _: u32 = emitter.linear(LinearOpcode::CrazyData)?;
        after_store(emitter)?;
    }
    Ok(scratch)
}

fn initialize_late_seed_roots(
    emitter: &mut Emitter<'_>,
    scratch: &mut ChunkWord,
) -> Result<(), BuildError> {
    for (address, landing) in HOT_SEED_ROOTS {
        if !address.is_multiple_of(2) {
            continue;
        }
        fast_rotate(emitter, NEAR_ZERO)?;
        fast_go(emitter, address)?;
        let _: u32 = emitter.linear(LinearOpcode::CrazyData)?;
        // Do not reset through any of the just-retired near even cells.
        emitter.walk(7_174_484)?;
        scratch.synthesize(
            emitter,
            profile_crazy(ALL_ONES, previous(landing)?, 15),
        )?;
        fast_go(emitter, address)?;
        let _: u32 = emitter.linear(LinearOpcode::CrazyData)?;
        emitter.walk(7_174_484)?;
    }
    Ok(())
}

fn plan_nonuniform_seeds(
    emitter: &Emitter<'_>,
    words: &Words,
    extra: (u32, u32),
) -> Result<SeedPlan, BuildError> {
    // Uniform inverses already have immutable rotate operands near the
    // frame. Reserve paired and reversible seed slots for other values.
    let seed_words = words
        .iter()
        .filter(|(_, value)| !matches!(**value, 0 | ALL_ONES | ALL_TWOS))
        .map(|(&address, &value)| (address, value))
        .collect();
    plan_seeds_with_pairs(emitter, &seed_words, (2, &[]), (Some(extra), 80))
}

pub(super) fn initialize_chunk_seeds(
    emitter: &mut Emitter<'_>,
    words: &Words,
    anchors: &[(TargetSlot, u32)],
    extra: (u32, u32),
) -> Result<(), BuildError> {
    let near = [
        (SEED_ANCHOR, previous(SEEDS)?),
        (EXTRA_SEED_ANCHOR, previous(extra.0)?),
        (CHUNK_ANCHOR, previous(CHUNK_PAGE_BANK)?),
        (SEED_DIRECTORY, previous(DIRECTORY_BANK)?),
    ];
    let mut roots = target_roots(words, anchors, emitter.tape_bounds.limit)?;
    for (address, landing) in HOT_SEED_ROOTS {
        if !address.is_multiple_of(2) {
            roots.push((address, previous(landing)?));
        }
    }
    roots.sort_unstable_by_key(|&(_, value)| value);
    if words
        .keys()
        .any(|address| !(CAPTURE..emitter.tape_bounds.limit).contains(address))
        || words.range(extra.0..=extra.1).next().is_some()
        || words.range(CHUNK_PAGE_BANK..=CHUNK_END).next().is_some()
        || words.range(DIRECTORY_BANK..=DIRECTORY_END).next().is_some()
        || extra.1 >= CHUNK_PAGE_BANK
        || DIRECTORY_END >= emitter.tape_bounds.start
    {
        return Err(LAYOUT);
    }
    let seed_plan = plan_nonuniform_seeds(emitter, words, extra)?;
    prepare_chunk_bank(emitter, &near)?;
    let mut scratch = initialize_chunk_roots(emitter, roots)?;
    initialize_late_seed_roots(emitter, &mut scratch)?;
    let directory = initialize_seed_directory(emitter, extra, &mut scratch)?;
    let mut seen = BTreeSet::new();
    let mut repeated = BTreeSet::new();
    for &value in words.values() {
        if !seen.insert(value) {
            let _inserted = repeated.insert(value);
        }
    }
    let single_use = seen.difference(&repeated).copied().collect();
    let routing = SeedRouting {
        directory: &directory,
        extra,
    };
    let (seed_addresses, seeds) =
        reorder_seed_slots(seed_plan, &routing, &single_use)?;
    initialize_target_pages(emitter, anchors, &mut scratch)?;
    let direct = initialize_materialization(
        emitter,
        words,
        anchors,
        (&seed_addresses, &routing, seeds, &mut scratch),
    )?;
    initialize_seed_returns(emitter, &seed_addresses, &routing, &mut scratch)?;
    materialize_chunk_words(
        emitter,
        words,
        anchors,
        (&seed_addresses, routing, &direct),
    )
}

// Approximate the walk cost of a patch by the actual mask-page distance
// and the full rotation cycle required for changes above the low chunk.
// The fixed fold weight is a heuristic, not an execution bound: scratch
// synthesis still compares the two emitted candidates at every store.
fn patch_distance(mut before: u32, mut after: u32) -> u32 {
    let mut cost: u32 = if before.div_euclid(27) == after.div_euclid(27) {
        0
    } else {
        30
    };
    for _ in 0..5u32 {
        let pair =
            fast_patch_columns(before.rem_euclid(27), after.rem_euclid(27));
        cost = cost.saturating_add(pair_cost(pair).0);
        before = before.div_euclid(27);
        after = after.div_euclid(27);
    }
    cost
}

fn order_materialization(
    mut remaining: &mut [MaterializationEntry],
    mut current: u32,
) {
    // The order changes only scratch synthesis, never the destinations or
    // their protected reset cells. Numeric ties make it reproducible.
    while let Some((offset, &(_, _, inverse))) = remaining
        .iter()
        .enumerate()
        .min_by_key(|&(_, &(address, value, inverse))| {
            (patch_distance(current, inverse), value, address)
        })
    {
        remaining.swap(0, offset);
        current = inverse;
        let Some((_, rest)) = remaining.split_first_mut() else {
            break;
        };
        remaining = rest;
    }
}

fn initialize_materialization(
    emitter: &mut Emitter<'_>,
    words: &Words,
    anchors: &[(TargetSlot, u32)],
    (seed_addresses, routing, seeds, scratch): InitialMaterialization<'_, '_>,
) -> Result<BTreeSet<u32>, BuildError> {
    let protected = words.keys().copied().collect::<BTreeSet<_>>();
    let direct = words
        .iter()
        .filter_map(|(&address, value)| {
            matches!(seed_addresses.get(value), Some(ChunkSeedAccess::Direct))
                .then_some(address)
        })
        .collect::<BTreeSet<_>>();
    let mut schedule = seeds;
    schedule.extend(
        words
            .iter()
            .filter(|(address, _)| direct.contains(address))
            .map(|(&address, &value)| (address, value)),
    );
    let mut entries = schedule
        .into_iter()
        .map(|(address, value)| {
            (address, value, profile_crazy(ALL_ONES, value, 15))
        })
        .collect::<Vec<_>>();
    order_materialization(&mut entries, scratch.value);
    for (address, value, inverse) in entries {
        if direct.contains(&address) {
            let reset = target_reset(
                address,
                &protected,
                routing.extra,
                emitter.tape_bounds.limit,
            )?;
            if needs_normalization(address, inverse, value) {
                fast_rotate(emitter, NEAR_ZERO)?;
                fast_store(emitter, address, anchors, reset)?;
            }
            scratch.synthesize(emitter, inverse)?;
            fast_store(emitter, address, anchors, reset)?;
        } else {
            fast_rotate(emitter, NEAR_ZERO)?;
            store_seed(emitter, address, routing)?;
            scratch.synthesize(emitter, inverse)?;
            store_seed(emitter, address, routing)?;
        }
    }
    Ok(direct)
}

fn needs_normalization(address: u32, inverse: u32, value: u32) -> bool {
    let virgin = if address.is_multiple_of(2) {
        7_174_416
    } else {
        37
    };
    profile_crazy(virgin, inverse, 15) != value
}

// Nearby targets can share one zero reload and one anchor route.
// Virgin words contain only zero/one trits, so alternating crazy stores
// leave every other target normalized. The other targets become zero and
// can participate in another sweep before their ordinary normalization.
// Reserve an even cell after three consecutive protected cells. The
// forward shared commit order can reuse reserved cells until their own
// initialization; never jump through a pre-touched even target.
fn normalize_target_clusters(
    emitter: &mut Emitter<'_>,
    words: &Words,
    anchors: &[(TargetSlot, u32)],
    protection: ClusterProtection<'_>,
) -> Result<ClusterPlan, BuildError> {
    let mut candidates = words
        .iter()
        .filter_map(|(&address, &value)| {
            (!protection.0.contains(&address)
                && needs_normalization(
                    address,
                    profile_crazy(ALL_ONES, value, 15),
                    value,
                ))
            .then_some(address)
        })
        .collect::<Vec<_>>();
    let mut protected = protection.0.clone();
    // Select only even targets with a nearby unprotected predecessor.
    // Include direct targets and every selected even candidate in the
    // protection set, even if a short cluster is ultimately skipped.
    candidates.retain(|&address| {
        if !address.is_multiple_of(2) {
            return true;
        }
        if [2u32, 4, 6].into_iter().all(|distance| {
            protected.contains(&address.saturating_sub(distance))
        }) {
            return false;
        }
        let _added = protected.insert(address);
        true
    });
    let mut normalized = BTreeSet::new();
    for _ in 0..3u32 {
        candidates = normalize_target_sweep(
            emitter,
            anchors,
            (&protected, protection.1),
            (&candidates, &mut normalized),
        )?;
    }
    Ok((normalized, protected))
}

fn normalize_target_sweep(
    emitter: &mut Emitter<'_>,
    anchors: &[(TargetSlot, u32)],
    (protected, extra): ClusterProtection<'_>,
    (candidates, normalized): ClusterSweep<'_>,
) -> Result<Vec<u32>, BuildError> {
    let mut zeroed = Vec::new();
    for cluster in
        candidates.chunk_by(|&left, &right| right.saturating_sub(left) <= 16)
    {
        if cluster.len() < 3 {
            continue;
        }
        let first = *cluster.first().ok_or(LAYOUT)?;
        let last = *cluster.last().ok_or(LAYOUT)?;
        fast_rotate(emitter, NEAR_ZERO)?;
        go_target(emitter, first, anchors)?;
        for (index, &address) in cluster.iter().enumerate() {
            emitter.walk(address)?;
            let _: u32 = emitter.linear(LinearOpcode::CrazyData)?;
            if index.is_multiple_of(2) {
                let _inserted = normalized.insert(address);
            } else {
                zeroed.push(address);
            }
        }
        let reset =
            target_reset(last, protected, extra, emitter.tape_bounds.limit)?;
        emitter.walk(reset)?;
    }
    Ok(zeroed)
}

fn materialize_chunk_words(
    emitter: &mut Emitter<'_>,
    words: &Words,
    anchors: &[(TargetSlot, u32)],
    (seed_addresses, routing, direct): ChunkMaterialization<'_>,
) -> Result<(), BuildError> {
    let (pre_normalized, protected) = normalize_target_clusters(
        emitter,
        words,
        anchors,
        (direct, routing.extra),
    )?;
    // The preceding cluster sweep need not leave a known accumulator.
    // Each subsequent normalization or final store establishes it again.
    let mut accumulator = None;
    for (&address, &value) in words {
        if !(CAPTURE..emitter.tape_bounds.limit).contains(&address) {
            return Err(LAYOUT);
        }
        if direct.contains(&address) {
            continue;
        }
        let reset = target_reset(
            address,
            &protected,
            routing.extra,
            emitter.tape_bounds.limit,
        )?;
        let inverse = profile_crazy(ALL_ONES, value, 15);
        let normalized = needs_normalization(address, inverse, value)
            && !pre_normalized.contains(&address);
        if normalized {
            fast_rotate(emitter, NEAR_ZERO)?;
            fast_store(emitter, address, anchors, reset)?;
            accumulator = Some(ALL_ONES);
        }
        if accumulator != Some(inverse) {
            let constant = match inverse {
                0 => Some(NEAR_ZERO),
                ALL_ONES => Some(NEAR_ONES),
                ALL_TWOS => Some(NEAR_TWOS),
                _ => None,
            };
            if let Some(operand) = constant {
                fast_rotate(emitter, operand)?;
            } else {
                let seed = *seed_addresses.get(&value).ok_or(LAYOUT)?;
                fast_load(emitter, seed, (inverse, accumulator), &routing)?;
            }
        }
        fast_store(emitter, address, anchors, reset)?;
        accumulator = Some(value);
    }
    Ok(())
}

#[cfg(test)]
#[path = "../../../../tests/compiler/recurrent_chunk_patch.rs"]
mod tests;
