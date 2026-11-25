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
//   - Lossless recurrent raw-input capture across an actual EOF dispatch.
// - Must-Not:
//   - Claim canonical source storage or checksum arithmetic.
// - Allows:
//   - Inputs: exact current N15 profile.
//   - Outputs: graphical source and proposed physical capture sites.
//   - Side effects: none; normative VM replay owns acceptance.
// - Split-When:
//   - General recurrent operand allocation replaces fixed tape geometry.
// - Merge-When:
//   - Whole checksum lowering owns recurrent source operands.
// - Summary:
//   - Capture the raw word before dirty classification and reset its slot.

#[path = "relocated_recurrent_indexed_source.rs"]
mod relocated_recurrent_indexed_source;
#[path = "relocated_recurrent_mod4_source.rs"]
mod relocated_recurrent_mod4_source;
#[path = "relocated_recurrent_nibble_source.rs"]
mod relocated_recurrent_nibble_source;
#[path = "relocated_recurrent_parity_source.rs"]
mod relocated_recurrent_parity_source;
#[path = "relocated_recurrent_reload_source.rs"]
mod relocated_recurrent_reload_source;

use std::cmp::Reverse;
use std::collections::BTreeMap;

use malbolge::{ProfileDescriptor, profile_crazy};
pub use relocated_recurrent_indexed_source::{
    RelocatedRecurrentIndexedSource, build_relocated_recurrent_indexed_source,
};
pub use relocated_recurrent_mod4_source::{
    RelocatedRecurrentMod4Source, build_relocated_recurrent_mod4_source,
};
pub use relocated_recurrent_nibble_source::{
    RelocatedRecurrentNibbleSource, build_relocated_recurrent_nibble_source,
};
pub use relocated_recurrent_parity_source::{
    RelocatedRecurrentParitySource, build_relocated_recurrent_parity_source,
};
pub use relocated_recurrent_reload_source::{
    RelocatedRecurrentReloadSource, build_relocated_recurrent_reload_source,
};

use super::super::super::{LinearOpcode, unique_graphical_cell};
use super::super::relocated_eof_parity_source::composed_prefix;
use super::super::{
    BOOT_RETURN, BuildError, Emitter, FRAME, LAYOUT, TapeBounds,
};
use super::relocated_recurrent_access::{AccessBlock, AccessShape};
use super::{
    ONES, TWOS, ZERO, after_store, initialize_words_compact,
    initialize_words_with_anchors,
};

const BOUNDS: TapeBounds = TapeBounds {
    limit: 7_240_001,
    start: 7_183_001,
};
const SOURCE_CELLS: usize = 1_660_196;
const CODE_BASE: u32 = 1_649_986;
// These virgin odd cells are outside the prefix's frame and return pair.
const NEAR_ONES: u32 = 7_174_469;
const NEAR_ZERO: u32 = 7_174_471;
const NEAR_TWOS: u32 = 7_174_473;
const SEED_ANCHOR: u32 = 7_174_483;
const EXTRA_SEED_ANCHOR: u32 = 7_174_485;
const ANCHOR_START: u32 = 7_174_487;
const ANCHOR_END: u32 = ONES;
const SEEDS: u32 = 7_174_611;
// Every inverse-seed slot precedes the first recurrent operand.
const SEED_END: u32 = CAPTURE;
// Ten pairs fit in the near seed bank. Use them for the most frequent
// route values; rare values retain the smaller reversible representation.
const IMMUTABLE_PAIRS: usize = 10;
const ANCHORS: [(u32, u32); 7] = [
    (ANCHOR_START, CAPTURE),
    (7_174_491, MAIN_ROUTE),
    (7_174_495, BOOT_ROUTE),
    (7_174_499, RESET_ROUTE),
    (7_174_503, 7_178_464),
    (7_174_507, 7_179_922),
    (7_174_511, 7_180_651),
];
const CAPTURE: u32 = 7_175_000;
const STATES: [u32; 6] = [
    7_175_010, 7_175_012, 7_175_014, 7_175_016, 7_175_018, 7_175_020,
];
const INPUT: u32 = 7_175_030;
const CONSTANTS: [u32; 3] = [7_175_040, 7_175_042, 7_175_044];
const MAIN_ROUTE: u32 = 7_175_200;
const BOOT_ROUTE: u32 = 7_176_200;
const RESET_ROUTE: u32 = 7_177_000;
const BYTE: u32 = 7_180_650;
const BYTE_ROUTE_POINTER: u32 = 7_180_670;
const EOF: [u32; 2] = [7_178_463, 7_179_921];
const TERMINAL: u32 = 1_659_986;
const ALL_ONES: u32 = 7_174_453;
const ALL_TWOS: u32 = 14_348_906;
// The captured raw word swaps 0 and 1, preserving 2. In particular
// trits 6 and 7 are 1 for bytes, 2 for EOF. These six dirty folds
// classify that different representation into the same three landings.
const INITIAL: [u32; 6] = [5_832, 5_103, 0, 14_329_224, 728, 13_122];

/// One recurrent physical raw-word capture and EOF guard.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct RelocatedRecurrentCaptureSource {
    /// Actual physical data relocation selecting the branch.
    pub branch: u32,
    /// Losslessly encoded raw input word.
    pub capture: u32,
    /// Code site of the raw-word capture and each classifier fold.
    pub crazy: u32,
    /// Actual physical terminal halt.
    pub halt: u32,
    /// Recurrent physical input instruction.
    pub input: u32,
    /// Actual physical terminal output.
    pub output: u32,
    /// Three distinct physical reset stores sharing the capture word.
    pub reset: [u32; 3],
    /// Recurrent rotation site loading the three reset constants.
    pub rotate: u32,
    /// Complete graphical source including its loader seed.
    pub source: Vec<u8>,
    /// Six dirty classifier words.
    pub states: [u32; 6],
}

type Words = BTreeMap<u32, u32>;
type WordPairs = [(u32, u32)];
type SeedPlan = (BTreeMap<u32, SeedAccess>, Vec<(u32, u32)>);

#[derive(Clone, Copy)]
enum SeedAccess {
    Reversible(u32),
    ImmutablePair(u32),
}
type ExtraSeeds = Option<(u32, u32)>;
type SeedOptions<'words> = (u32, &'words WordPairs, ExtraSeeds);

struct Route<'words> {
    cursor: u32,
    words: &'words mut Words,
}

impl Route<'_> {
    fn call(
        &mut self,
        block: &AccessBlock,
        operand: u32,
        next: Option<u32>,
    ) -> Result<(), BuildError> {
        self.enter(block, operand)?;
        let continuation = operand
            .checked_add(block.after)
            .and_then(|value| value.checked_add(1))
            .ok_or(LAYOUT)?;
        insert(
            self.words,
            continuation,
            previous(next.unwrap_or(self.cursor))?,
        )
    }

    fn call_ready(
        &mut self,
        block: &AccessBlock,
        operand: u32,
    ) -> Result<(), BuildError> {
        self.enter_ready(block, operand)?;
        let continuation = operand
            .checked_add(block.after)
            .and_then(|value| value.checked_add(1))
            .ok_or(LAYOUT)?;
        insert(self.words, continuation, previous(self.cursor)?)?;
        self.prepare(block, false)
    }

    fn enter(
        &mut self,
        block: &AccessBlock,
        operand: u32,
    ) -> Result<(), BuildError> {
        self.prepare(block, false)?;
        self.enter_ready(block, operand)
    }

    fn enter_ready(
        &mut self,
        block: &AccessBlock,
        operand: u32,
    ) -> Result<(), BuildError> {
        insert(self.words, self.cursor, previous(block.start)?)?;
        let pointer = operand
            .checked_sub(block.before)
            .and_then(|value| value.checked_sub(1))
            .ok_or(LAYOUT)?;
        self.cursor = self.cursor.checked_add(1).ok_or(LAYOUT)?;
        insert(self.words, self.cursor, pointer)?;
        self.cursor = self.cursor.checked_add(1).ok_or(LAYOUT)?;
        Ok(())
    }

    fn prepare(
        &mut self,
        block: &AccessBlock,
        bootstrap: bool,
    ) -> Result<(), BuildError> {
        for jump in block.preparation(bootstrap)? {
            insert(self.words, self.cursor, jump.target)?;
            self.cursor = self.cursor.checked_add(jump.words).ok_or(LAYOUT)?;
        }
        Ok(())
    }
}

struct Blocks {
    branch: AccessBlock,
    crazy: AccessBlock,
    input: AccessBlock,
    reset: [AccessBlock; 3],
    rotate: AccessBlock,
}

impl Blocks {
    fn new(profile: &ProfileDescriptor, base: u32) -> Result<Self, BuildError> {
        use LinearOpcode::{
            CrazyData, InputWord, RelocateDataPointer, RotateData,
        };
        Ok(Self {
            branch: access(
                profile,
                (base, 7, 92),
                RelocateDataPointer,
                (0, 0, false),
            )?,
            crazy: access(profile, (base, 2, 58), CrazyData, (1, 0, true))?,
            input: access(profile, (base, 1, 74), InputWord, (0, 0, true))?,
            reset: [
                access(profile, (base, 3, 93), CrazyData, (0, 1, true))?,
                access(profile, (base, 4, 93), CrazyData, (0, 2, true))?,
                access(profile, (base, 5, 93), CrazyData, (0, 3, true))?,
            ],
            rotate: access(profile, (base, 6, 29), RotateData, (0, 0, true))?,
        })
    }

    const fn ordered(&self) -> [&AccessBlock; 7] {
        let [first, second, third] = &self.reset;
        [
            &self.input,
            &self.crazy,
            first,
            second,
            third,
            &self.rotate,
            &self.branch,
        ]
    }
}

fn previous(address: u32) -> Result<u32, BuildError> {
    address.checked_sub(1).ok_or(LAYOUT)
}

fn insert(
    words: &mut Words,
    address: u32,
    value: u32,
) -> Result<(), BuildError> {
    if words.get(&address).is_some_and(|old| *old != value) {
        return Err(LAYOUT);
    }
    let _: Option<u32> = words.insert(address, value);
    Ok(())
}

fn access(
    profile: &ProfileDescriptor,
    placement: (u32, u32, u32),
    opcode: LinearOpcode,
    shape: (u32, u32, bool),
) -> Result<AccessBlock, BuildError> {
    let (base, index, phase) = placement;
    let (before, after, return_to_route) = shape;
    AccessBlock::new(profile, code(base, index, phase)?, opcode, AccessShape {
        after,
        before,
        return_to_route,
    })
}

fn code(base: u32, index: u32, phase: u32) -> Result<u32, BuildError> {
    base.checked_sub(base.rem_euclid(94))
        .and_then(|value| value.checked_add(index.checked_mul(94)?))
        .and_then(|value| value.checked_add(phase))
        .ok_or(LAYOUT)
}

fn routes(blocks: &Blocks) -> Result<Words, BuildError> {
    let mut words = Words::new();
    insert(&mut words, CAPTURE, ALL_ONES)?;
    for (address, value) in STATES.into_iter().zip(INITIAL) {
        insert(&mut words, address, value)?;
    }
    for (address, value) in CONSTANTS.into_iter().zip([ALL_ONES, ALL_TWOS, 0]) {
        insert(&mut words, address, value)?;
    }
    let mut main = Route {
        cursor: MAIN_ROUTE,
        words: &mut words,
    };
    main.call(&blocks.input, INPUT, None)?;
    let after_input = main.cursor;
    main.call(&blocks.crazy, CAPTURE, None)?;
    for address in STATES {
        main.call(&blocks.crazy, address, None)?;
    }
    let [_, _, _, _, _, class] = STATES;
    main.enter(&blocks.branch, class)?;
    if main.cursor >= BOOT_ROUTE {
        return Err(LAYOUT);
    }
    let mut boot = Route {
        cursor: BOOT_ROUTE,
        words: &mut words,
    };
    for block in blocks.ordered() {
        boot.prepare(block, true)?;
    }
    boot.call(&blocks.input, INPUT, Some(after_input))?;
    if boot.cursor >= RESET_ROUTE {
        return Err(LAYOUT);
    }
    byte_route(blocks, &mut words)?;
    for (landing, value) in EOF.into_iter().zip([3, 0]) {
        insert(
            &mut words,
            landing.checked_add(1).ok_or(LAYOUT)?,
            previous(TERMINAL)?,
        )?;
        insert(&mut words, landing.checked_add(2).ok_or(LAYOUT)?, value)?;
    }
    Ok(words)
}

fn byte_route(blocks: &Blocks, words: &mut Words) -> Result<(), BuildError> {
    let mut bridge = Route {
        cursor: BYTE.checked_add(1).ok_or(LAYOUT)?,
        words,
    };
    bridge.enter(&blocks.branch, BYTE_ROUTE_POINTER)?;
    if bridge.cursor >= BYTE_ROUTE_POINTER {
        return Err(LAYOUT);
    }
    insert(words, BYTE_ROUTE_POINTER, previous(RESET_ROUTE)?)?;
    let mut byte = Route {
        cursor: RESET_ROUTE,
        words,
    };
    for (index, (address, block)) in
        CONSTANTS.into_iter().zip(&blocks.reset).enumerate()
    {
        byte.call(&blocks.rotate, address, None)?;
        byte.call(block, CAPTURE, (index == 2).then_some(MAIN_ROUTE))?;
    }
    if byte.cursor >= EOF.into_iter().min().ok_or(LAYOUT)? {
        return Err(LAYOUT);
    }
    Ok(())
}

fn rotate(emitter: &mut Emitter<'_>, address: u32) -> Result<(), BuildError> {
    emitter.go(address)?;
    let _: u32 = emitter.linear(LinearOpcode::RotateData)?;
    Ok(())
}

fn crazy(emitter: &mut Emitter<'_>, address: u32) -> Result<(), BuildError> {
    emitter.go(address)?;
    let _: u32 = emitter.linear(LinearOpcode::CrazyData)?;
    after_store(emitter)
}

// Establish uniform words closer to the frame reset than the original
// marker-tape constants. All intervening even reset pointers stay virgin.
fn prepare_near_constants(emitter: &mut Emitter<'_>) -> Result<(), BuildError> {
    rotate(emitter, ONES)?;
    crazy(emitter, NEAR_ZERO)?;
    rotate(emitter, ZERO)?;
    crazy(emitter, NEAR_TWOS)?;
    rotate(emitter, TWOS)?;
    crazy(emitter, NEAR_TWOS)
}

// Keep one immutable inverse seed per distinct route value. The target
// words are still virgin and have no trit two. Prepare an all-one
// baseline only when the inverse seed cannot write the virgin word
// directly. Two folds with all twos load the seed without changing it.
fn initialize(
    emitter: &mut Emitter<'_>,
    words: &Words,
    anchors: &[(u32, u32)],
    stride: u32,
) -> Result<(), BuildError> {
    initialize_with_dispatch(emitter, words, anchors, (stride, &[]))
}

fn initialize_with_dispatch(
    emitter: &mut Emitter<'_>,
    words: &Words,
    anchors: &[(u32, u32)],
    (stride, dispatch): (u32, &WordPairs),
) -> Result<(), BuildError> {
    initialize_with_extra_seeds(
        emitter,
        words,
        anchors,
        (stride, dispatch, None),
    )
}

fn initialize_with_extra_seeds(
    emitter: &mut Emitter<'_>,
    words: &Words,
    anchors: &[(u32, u32)],
    (stride, dispatch, extra): SeedOptions<'_>,
) -> Result<(), BuildError> {
    let mut near = vec![(SEED_ANCHOR, previous(SEEDS)?)];
    if let Some((base, end)) = extra {
        if base < CAPTURE
            || base >= end
            || end >= emitter.tape_bounds.start
            || base.is_multiple_of(2)
            || !stride.is_multiple_of(2)
            || stride == 0
            || !end.is_multiple_of(2)
            || words.range(base..=end).next().is_some()
        {
            return Err(LAYOUT);
        }
        near.push((EXTRA_SEED_ANCHOR, previous(base)?));
    }
    for &(anchor, base) in anchors {
        if !(ANCHOR_START..ANCHOR_END).contains(&anchor) {
            return Err(LAYOUT);
        }
        near.push((anchor, previous(base)?));
    }
    let (seed_addresses, seeds) =
        plan_seeds(emitter, words, (stride, dispatch), extra)?;
    if extra.is_some() {
        initialize_words_compact(emitter, &near, &seeds, true)?;
    } else {
        initialize_words_with_anchors(emitter, &near, &seeds)?;
    }
    prepare_near_constants(emitter)?;
    if extra.is_some() {
        rotate(emitter, NEAR_ZERO)?;
        crazy(emitter, NEAR_ONES)?;
    }
    for (&address, &value) in words {
        if !(CAPTURE..emitter.tape_bounds.start).contains(&address) {
            return Err(LAYOUT);
        }
        // The fixed loader tail expands to these alternating words.
        // `finish` checks both phases at the frame before returning.
        let virgin = if address.is_multiple_of(2) {
            7_174_416
        } else {
            37
        };
        let trits = emitter.profile.word_trits();
        let inverse = profile_crazy(ALL_ONES, value, trits);
        let normalized = profile_crazy(virgin, inverse, trits) != value;
        if normalized {
            rotate(emitter, NEAR_ZERO)?;
            store_anchored(emitter, address, anchors)?;
        }
        let seed = *seed_addresses.get(&value).ok_or(LAYOUT)?;
        load_seed(emitter, seed, extra, normalized)?;
        store_anchored(emitter, address, anchors)?;
    }
    for &(address, value) in dispatch {
        for constant in [ONES, NEAR_TWOS, NEAR_ZERO] {
            rotate(emitter, constant)?;
            store_dispatch(emitter, address)?;
        }
        let seed = *seed_addresses.get(&value).ok_or(LAYOUT)?;
        load_seed(emitter, seed, extra, true)?;
        store_dispatch(emitter, address)?;
    }
    Ok(())
}

fn plan_seeds(
    emitter: &Emitter<'_>,
    words: &Words,
    (stride, dispatch): (u32, &WordPairs),
    extra: ExtraSeeds,
) -> Result<SeedPlan, BuildError> {
    let mut frequency = BTreeMap::<u32, usize>::new();
    for value in words
        .values()
        .copied()
        .chain(dispatch.iter().map(|&(_, value)| value))
    {
        let count = frequency.entry(value).or_default();
        *count = count.checked_add(1).ok_or(LAYOUT)?;
    }
    let mut values = frequency.into_iter().collect::<Vec<_>>();
    // Each value is loaded twice per target. Assign the shortest walks
    // to the most frequently loaded seeds, with a stable numeric tie.
    values.sort_unstable_by_key(|&(value, count)| (Reverse(count), value));
    let mut seed_addresses = BTreeMap::new();
    let mut seeds = Vec::new();
    // The compact tape has twelve additional anchors at M7174971..4993.
    let seed_end = if extra.is_some() {
        7_174_970
    } else {
        SEED_END
    };
    let paired_count = if extra.is_some() {
        IMMUTABLE_PAIRS
    } else {
        0
    };
    for (index, (value, _)) in values.into_iter().enumerate() {
        let paired = index < paired_count;
        let offset = u32::try_from(
            index.checked_add(index.min(paired_count)).ok_or(LAYOUT)?,
        )
        .map_err(|_error| LAYOUT)?
        .checked_mul(stride)
        .ok_or(LAYOUT)?;
        let mut address = SEEDS.checked_add(offset).ok_or(LAYOUT)?;
        if address >= seed_end {
            let (base, end) = extra.ok_or(LAYOUT)?;
            let slots = seed_end
                .checked_sub(SEEDS)
                .ok_or(LAYOUT)?
                .checked_add(stride.checked_sub(1).ok_or(LAYOUT)?)
                .ok_or(LAYOUT)?
                .checked_div(stride)
                .ok_or(LAYOUT)?;
            let overflow = offset
                .checked_sub(slots.checked_mul(stride).ok_or(LAYOUT)?)
                .ok_or(LAYOUT)?;
            address = base.checked_add(overflow).ok_or(LAYOUT)?;
            if address >= end {
                return Err(LAYOUT);
            }
        }
        let inverse =
            profile_crazy(ALL_ONES, value, emitter.profile.word_trits());
        let access = if paired {
            let second = address.checked_add(2).ok_or(LAYOUT)?;
            // Adjacent odd slots and their virgin even reset words.
            if stride != 2 || second >= seed_end {
                return Err(LAYOUT);
            }
            seeds.push((
                address,
                immutable_seed_prefix(inverse, emitter.profile.word_trits())?,
            ));
            seeds.push((second, inverse));
            SeedAccess::ImmutablePair(address)
        } else {
            seeds.push((address, inverse));
            SeedAccess::Reversible(address)
        };
        let _: Option<SeedAccess> = seed_addresses.insert(value, access);
    }
    Ok((seed_addresses, seeds))
}

// With A=all ones, a prefix trit of two is stable exactly where the
// inverse seed is zero. A prefix trit of zero is stable elsewhere.
// The following crazy fold reads the inverse without changing it.
fn immutable_seed_prefix(
    mut inverse: u32,
    trits: u8,
) -> Result<u32, BuildError> {
    let mut prefix = 0u32;
    for digit in 0..u32::from(trits) {
        if inverse.rem_euclid(3) == 0 {
            prefix = prefix
                .checked_add(2u32.checked_mul(3u32.pow(digit)).ok_or(LAYOUT)?)
                .ok_or(LAYOUT)?;
        }
        inverse = inverse.div_euclid(3);
    }
    if inverse != 0 {
        return Err(LAYOUT);
    }
    Ok(prefix)
}

fn load_seed(
    emitter: &mut Emitter<'_>,
    access: SeedAccess,
    extra: ExtraSeeds,
    accumulator_ones: bool,
) -> Result<(), BuildError> {
    let seed = match access {
        SeedAccess::Reversible(seed) => seed,
        SeedAccess::ImmutablePair(prefix) => {
            if !accumulator_ones {
                rotate(emitter, NEAR_ONES)?;
            }
            emitter.go(SEED_ANCHOR)?;
            emitter.jump(SEEDS)?;
            emitter.walk(prefix)?;
            let _: u32 = emitter.linear(LinearOpcode::CrazyData)?;
            emitter.walk(prefix.checked_add(2).ok_or(LAYOUT)?)?;
            let _: u32 = emitter.linear(LinearOpcode::CrazyData)?;
            return after_store(emitter);
        },
    };
    // Rare values use two all-two folds to read and restore one seed.
    let (anchor, base) = if let Some((base, _)) =
        extra.filter(|(base, end)| (*base..*end).contains(&seed))
    {
        (EXTRA_SEED_ANCHOR, base)
    } else {
        (SEED_ANCHOR, SEEDS)
    };
    for _ in 0..2u8 {
        rotate(emitter, NEAR_TWOS)?;
        emitter.go(anchor)?;
        emitter.jump(base)?;
        emitter.walk(seed)?;
        let _: u32 = emitter.linear(LinearOpcode::CrazyData)?;
        after_store(emitter)?;
    }
    Ok(())
}

// These three cells have already been executed or initialized by the prefix.
// The marker return path is retained until all ordinary route stores finish.
fn store_dispatch(
    emitter: &mut Emitter<'_>,
    address: u32,
) -> Result<(), BuildError> {
    match address {
        0 => {
            emitter.go(NEAR_TWOS)?;
            emitter.jump(0)?;
        },
        38 => {
            emitter.go(7_174_425)?;
            emitter.jump(38)?;
        },
        FRAME => {
            emitter.go(FRAME)?;
        },
        _ => return Err(LAYOUT),
    }
    let _: u32 = emitter.linear(LinearOpcode::CrazyData)?;
    if address != FRAME {
        emitter.walk(40)?;
        emitter.jump(70)?;
        emitter.jump(116)?;
        emitter.walk(117)?;
        emitter.jump(120)?;
        emitter.walk(122)?;
        emitter.jump(BOOT_RETURN)?;
    }
    Ok(())
}

// Each anchor is a guest-materialized predecessor of a route segment.
// The immutable near-frame pointer replaces a long linear D walk.
fn go_anchored(
    emitter: &mut Emitter<'_>,
    address: u32,
    anchors: &[(u32, u32)],
) -> Result<(), BuildError> {
    let (anchor, base) = anchors
        .iter()
        .copied()
        .rev()
        .find(|(_, base)| *base <= address)
        .ok_or(LAYOUT)?;
    emitter.go(anchor)?;
    emitter.jump(base)?;
    emitter.walk(address)
}

fn store_anchored(
    emitter: &mut Emitter<'_>,
    address: u32,
    anchors: &[(u32, u32)],
) -> Result<(), BuildError> {
    go_anchored(emitter, address, anchors)?;
    let _: u32 = emitter.linear(LinearOpcode::CrazyData)?;
    after_store(emitter)
}

fn bootstrap(
    profile: &ProfileDescriptor,
    source_cells: usize,
    tape_bounds: TapeBounds,
) -> Result<Emitter<'_>, BuildError> {
    if source_cells > 6_554_440 {
        return Err(LAYOUT);
    }
    let mut prefix = composed_prefix(profile)?;
    let bootstrap_input = usize::try_from(prefix.first_input_code_address)
        .map_err(|_error| LAYOUT)?;
    *prefix.source.get_mut(bootstrap_input).ok_or(LAYOUT)? =
        unique_graphical_cell(
            profile,
            LinearOpcode::NoOperation,
            bootstrap_input,
        )
        .map_err(|_error| LAYOUT)?;
    let mut emitter = Emitter {
        data: 7_174_418,
        profile,
        source: prefix.source,
        source_cells,
        tape_bounds,
    };
    // Use the prepared bootstrap return instead of depending on the
    // distant loader return word at M4,782,982.
    emitter.source.truncate(126);
    emitter.data = 49;
    emitter.walk(76)?;
    let _: u32 = emitter.linear(LinearOpcode::RotateData)?;
    emitter.walk(122)?;
    emitter.jump(BOOT_RETURN)?;
    emitter.walk(7_174_468)?;
    emitter.jump(FRAME)?;
    let _: u32 = emitter.linear(LinearOpcode::RotateData)?;
    Ok(emitter)
}

/// Construct a recurrent raw-input capture across real EOF dispatch.
///
/// A bounded phase-restoration route permits four distinct physical
/// accesses to one dirty operand. The byte arm resets that word; EOF
/// leaves the captured encoding intact and emits length parity.
///
/// # Errors
/// Refuses unsupported profiles and exhausted physical route geometry.
pub fn build_relocated_recurrent_capture_source(
    profile: &ProfileDescriptor,
) -> Result<RelocatedRecurrentCaptureSource, BuildError> {
    let mut emitter = bootstrap(profile, SOURCE_CELLS, BOUNDS)?;
    let blocks = Blocks::new(profile, CODE_BASE)?;
    let words = routes(&blocks)?;
    initialize(&mut emitter, &words, &ANCHORS, 4)?;
    go_anchored(&mut emitter, BOOT_ROUTE, &ANCHORS)?;
    let _: u32 = emitter.append_indirect()?;
    for block in blocks.ordered() {
        block.emit(&mut emitter)?;
    }
    emitter
        .pad_to_entry(usize::try_from(TERMINAL).map_err(|_error| LAYOUT)?, 0)?;
    let _: u32 = emitter.append(LinearOpcode::RotateData)?;
    let output = emitter.append(LinearOpcode::OutputByte)?;
    let halt = emitter.append(LinearOpcode::Halt)?;
    let [first, second, third] = &blocks.reset;
    Ok(RelocatedRecurrentCaptureSource {
        branch: blocks.branch.operation_site()?,
        capture: CAPTURE,
        crazy: blocks.crazy.operation_site()?,
        halt,
        input: blocks.input.operation_site()?,
        output,
        reset: [
            first.operation_site()?,
            second.operation_site()?,
            third.operation_site()?,
        ],
        rotate: blocks.rotate.operation_site()?,
        source: emitter.finish()?,
        states: STATES,
    })
}
