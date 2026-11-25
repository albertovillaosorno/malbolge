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

use std::collections::BTreeMap;

use malbolge::profile_crazy;

use super::super::super::super::LinearOpcode;
use super::super::super::{BuildError, Emitter, FRAME, LAYOUT};
use super::super::{after_store, initialize_words_compact_extent};
use super::{
    ALL_ONES, ALL_TWOS, ANCHOR_END, ANCHOR_START, CAPTURE, EXTRA_SEED_ANCHOR,
    NEAR_ONES, NEAR_TWOS, NEAR_ZERO, SEED_ANCHOR, SEEDS, SeedAccess, Words,
    crazy, immutable_seed_prefix, plan_seeds_with_pairs,
    prepare_near_constants, previous, rotate, store_anchored,
};

// A compact seed bootstrap reuses one 27-entry mask bank for the
// five three-trit chunks of each N15 word. Scratch rotations bring each
// chunk into the same low-trit position.
const CHUNK_SCRATCH: u32 = 7_174_441;
const CHUNK_TWOS: u32 = CHUNK_SCRATCH + 2;
const CHUNK_RETURN: u32 = CHUNK_SCRATCH + 4;
const CHUNK_ANCHOR: u32 = ANCHOR_START;
const CHUNK_BANK: u32 = 7_176_601;
const CHUNK_RESET: u32 = 7_174_468;
// The directory is between the immutable chunk-mask bank and the
// operand tape. Its odd pointers leave each even reset word virgin.
const SEED_DIRECTORY: u32 = ANCHOR_START + 2;
const DIRECTORY_BANK: u32 = 7_176_721;
const DIRECTORY_STRIDE: u32 = 32;
const DIRECTORY_END: u32 = 7_176_900;
const TARGET_ROOTS: [u32; 2] = [7_174_491, 7_174_493];
const TARGET_BANKS: [u32; 2] = [7_300_001, 7_300_201];
const TARGET_PAGE_COUNT: u32 = 48;
const TARGET_DIRECT_START: u32 = 7_174_495;

type ChunkMasks = Vec<(u32, u32)>;
type SeedDirectory = Vec<(u32, u32)>;

#[derive(Clone, Copy)]
pub(super) enum TargetSlot {
    Direct(u32),
    Page { bank: u32, root: u32, slot: u32 },
}

impl TargetSlot {
    fn cost(self) -> u64 {
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

type ChunkMaterialization<'seeds> =
    (u32, &'seeds BTreeMap<u32, SeedAccess>, SeedRouting<'seeds>);

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
) -> Result<(), BuildError> {
    for constant in [NEAR_ONES, NEAR_TWOS, NEAR_ZERO] {
        rotate(emitter, constant)?;
        chunk_access(emitter, address, LinearOpcode::CrazyData)?;
    }
    Ok(())
}

fn read_chunk_mask(
    emitter: &mut Emitter<'_>,
    index: u32,
) -> Result<(), BuildError> {
    let address = CHUNK_BANK
        .checked_add(index.checked_mul(4).ok_or(LAYOUT)?)
        .ok_or(LAYOUT)?;
    rotate(emitter, NEAR_ONES)?;
    emitter.go(CHUNK_ANCHOR)?;
    emitter.jump(CHUNK_BANK)?;
    emitter.walk(address)?;
    let _: u32 = emitter.linear(LinearOpcode::CrazyData)?;
    emitter.walk(address.checked_add(2).ok_or(LAYOUT)?)?;
    let _: u32 = emitter.linear(LinearOpcode::CrazyData)?;
    after_store(emitter)
}

fn chunk_word(
    emitter: &mut Emitter<'_>,
    mut value: u32,
) -> Result<(), BuildError> {
    reset_chunk_word(emitter, CHUNK_SCRATCH)?;
    for _ in 0..5u32 {
        // On an all-one low chunk, the first mask fold and the all-two
        // fold produce the requested trits. Everywhere else two
        // all-two folds cancel. Three rotations expose the next chunk.
        let part = value.rem_euclid(27);
        let column =
            profile_crazy(ALL_ONES, profile_crazy(part, ALL_TWOS, 15), 15)
                .rem_euclid(27);
        read_chunk_mask(emitter, column)?;
        emitter.go(CHUNK_SCRATCH)?;
        let _: u32 = emitter.linear(LinearOpcode::CrazyData)?;
        emitter.walk(CHUNK_TWOS)?;
        let _: u32 = emitter.linear(LinearOpcode::RotateData)?;
        emitter.walk(CHUNK_RETURN)?;
        emitter.jump(CHUNK_SCRATCH)?;
        let _: u32 = emitter.linear(LinearOpcode::CrazyData)?;
        for _ in 0..3u32 {
            emitter.walk(CHUNK_RETURN)?;
            emitter.jump(CHUNK_SCRATCH)?;
            let _: u32 = emitter.linear(LinearOpcode::RotateData)?;
        }
        emitter.walk(CHUNK_RESET)?;
        value = value.div_euclid(27);
    }
    if value != 0 {
        return Err(LAYOUT);
    }
    Ok(())
}

fn fast_go(emitter: &mut Emitter<'_>, target: u32) -> Result<(), BuildError> {
    if emitter.data > target {
        emitter.reset()?;
    }
    if emitter.data == FRAME && target >= NEAR_ONES {
        emitter.jump(NEAR_ONES)?;
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
) -> Result<(), BuildError> {
    go_target(emitter, address, anchors)?;
    let _: u32 = emitter.linear(LinearOpcode::CrazyData)?;
    after_store(emitter)
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

fn go_seed(
    emitter: &mut Emitter<'_>,
    address: u32,
    routing: &SeedRouting<'_>,
) -> Result<(), BuildError> {
    let extra = routing.extra;
    let (root, base) = if (extra.0..extra.1).contains(&address) {
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
    let direct = root
        .checked_add(address.checked_sub(base).ok_or(LAYOUT)?)
        .ok_or(LAYOUT)?;
    let indirect = SEED_DIRECTORY
        .checked_add(slot.checked_sub(DIRECTORY_BANK).ok_or(LAYOUT)?)
        .and_then(|value| value.checked_add(1))
        .and_then(|value| value.checked_add(address.checked_sub(page)?))
        .ok_or(LAYOUT)?;
    if indirect < direct {
        fast_go(emitter, SEED_DIRECTORY)?;
        emitter.jump(DIRECTORY_BANK)?;
        emitter.walk(slot)?;
        emitter.jump(page)?;
    } else {
        fast_go(emitter, root)?;
        emitter.jump(base)?;
    }
    emitter.walk(address)
}

fn fast_load(
    emitter: &mut Emitter<'_>,
    seed: SeedAccess,
    accumulator_ones: bool,
    routing: &SeedRouting<'_>,
) -> Result<(), BuildError> {
    if let SeedAccess::ImmutablePair(prefix) = seed {
        if !accumulator_ones {
            fast_rotate(emitter, NEAR_ONES)?;
        }
        go_seed(emitter, prefix, routing)?;
        let _: u32 = emitter.linear(LinearOpcode::CrazyData)?;
        emitter.walk(prefix.checked_add(2).ok_or(LAYOUT)?)?;
        let _: u32 = emitter.linear(LinearOpcode::CrazyData)?;
        return after_store(emitter);
    }
    let SeedAccess::Reversible(address) = seed else {
        return Err(LAYOUT);
    };
    for _ in 0..2u32 {
        fast_rotate(emitter, NEAR_TWOS)?;
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

fn initialize_seed_directory(
    emitter: &mut Emitter<'_>,
    extra: (u32, u32),
) -> Result<SeedDirectory, BuildError> {
    let directory = seed_directory(extra)?;
    let directory_anchor = [(SEED_DIRECTORY, DIRECTORY_BANK)];
    for &(address, base) in &directory {
        rotate(emitter, NEAR_ZERO)?;
        store_anchored(emitter, address, &directory_anchor)?;
        chunk_word(emitter, profile_crazy(ALL_ONES, previous(base)?, 15))?;
        store_anchored(emitter, address, &directory_anchor)?;
    }
    Ok(directory)
}

fn initialize_target_pages(
    emitter: &mut Emitter<'_>,
    anchors: &[(TargetSlot, u32)],
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
    pages.sort_unstable();
    for (slot, bank, root, base) in pages {
        let anchor = [(root, bank)];
        rotate(emitter, NEAR_ZERO)?;
        store_anchored(emitter, slot, &anchor)?;
        chunk_word(emitter, profile_crazy(ALL_ONES, previous(base)?, 15))?;
        store_anchored(emitter, slot, &anchor)?;
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

pub(super) fn initialize_chunk_seeds(
    emitter: &mut Emitter<'_>,
    words: &Words,
    anchors: &[(TargetSlot, u32)],
    extra: (u32, u32),
) -> Result<(), BuildError> {
    let mut near = vec![
        (SEED_ANCHOR, previous(SEEDS)?),
        (EXTRA_SEED_ANCHOR, previous(extra.0)?),
        (CHUNK_ANCHOR, previous(CHUNK_BANK)?),
        (SEED_DIRECTORY, previous(DIRECTORY_BANK)?),
    ];
    near.extend(target_roots(words, anchors, emitter.tape_bounds.limit)?);
    near.sort_unstable_by_key(|&(address, _)| address);
    if words.range(extra.0..=extra.1).next().is_some()
        || words.range(CHUNK_BANK..=CHUNK_BANK + 111).next().is_some()
        || words.range(DIRECTORY_BANK..=DIRECTORY_END).next().is_some()
        || extra.1 >= CHUNK_BANK
        || DIRECTORY_END >= emitter.tape_bounds.start
    {
        return Err(LAYOUT);
    }
    let (seed_addresses, seeds) =
        plan_seeds_with_pairs(emitter, words, (2, &[]), (Some(extra), 80))?;
    let masks = chunk_masks()?;
    let tape_end =
        initialize_words_compact_extent(emitter, &near, &masks, true)?;
    if tape_end >= *TARGET_BANKS.first().ok_or(LAYOUT)? {
        return Err(LAYOUT);
    }
    prepare_near_constants(emitter)?;
    rotate(emitter, NEAR_ZERO)?;
    crazy(emitter, NEAR_ONES)?;
    reset_chunk_word(emitter, CHUNK_TWOS)?;
    rotate(emitter, NEAR_TWOS)?;
    chunk_access(emitter, CHUNK_TWOS, LinearOpcode::CrazyData)?;
    reset_chunk_word(emitter, CHUNK_RETURN)?;
    read_chunk_mask(emitter, 27)?;
    chunk_access(emitter, CHUNK_RETURN, LinearOpcode::CrazyData)?;

    let seed_anchors = [(SEED_ANCHOR, SEEDS), (EXTRA_SEED_ANCHOR, extra.0)];
    for (address, value) in seeds {
        rotate(emitter, NEAR_ZERO)?;
        store_anchored(emitter, address, &seed_anchors)?;
        chunk_word(emitter, profile_crazy(ALL_ONES, value, 15))?;
        store_anchored(emitter, address, &seed_anchors)?;
    }
    let directory = initialize_seed_directory(emitter, extra)?;
    initialize_target_pages(emitter, anchors)?;
    reset_chunk_word(emitter, FRAME)?;
    chunk_word(emitter, profile_crazy(ALL_ONES, previous(NEAR_ONES)?, 15))?;
    emitter.go(FRAME)?;
    let _: u32 = emitter.linear(LinearOpcode::CrazyData)?;
    emitter.walk(CHUNK_RESET)?;
    materialize_chunk_words(
        emitter,
        words,
        anchors,
        (tape_end, &seed_addresses, SeedRouting {
            directory: &directory,
            extra,
        }),
    )
}

fn materialize_chunk_words(
    emitter: &mut Emitter<'_>,
    words: &Words,
    anchors: &[(TargetSlot, u32)],
    (tape_end, seed_addresses, routing): ChunkMaterialization<'_>,
) -> Result<(), BuildError> {
    for (&address, &value) in words {
        if !(CAPTURE..emitter.tape_bounds.limit).contains(&address) {
            return Err(LAYOUT);
        }
        let virgin = if address.is_multiple_of(2) {
            7_174_416
        } else {
            37
        };
        let inverse = profile_crazy(ALL_ONES, value, 15);
        let dirty = (emitter.tape_bounds.start..tape_end).contains(&address)
            && !address.is_multiple_of(2);
        let normalized = dirty || profile_crazy(virgin, inverse, 15) != value;
        if dirty {
            for constant in [NEAR_ONES, NEAR_TWOS, NEAR_ZERO] {
                fast_rotate(emitter, constant)?;
                fast_store(emitter, address, anchors)?;
            }
        } else if normalized {
            fast_rotate(emitter, NEAR_ZERO)?;
            fast_store(emitter, address, anchors)?;
        }
        let seed = *seed_addresses.get(&value).ok_or(LAYOUT)?;
        fast_load(emitter, seed, normalized, &routing)?;
        fast_store(emitter, address, anchors)?;
    }
    Ok(())
}
