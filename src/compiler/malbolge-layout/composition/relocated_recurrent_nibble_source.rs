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
//   - Recurrent physical projected checksum state and EOF output.
// - Must-Not:
//   - Claim complete eight-bit checksum execution or source-C admission.
// - Allows:
//   - Inputs: exact N15 profile and a finite transition table.
//   - Outputs: graphical source and proposed physical effect sites.
//   - Side effects: none; normative VM replay owns acceptance.
// - Split-When:
//   - General recurrent state allocation replaces fixed physical geometry.
// - Merge-When:
//   - Complete recurrent checksum arithmetic subsumes the projection.
// - Summary:
//   - Factor byte selection from bounded recurrent state transitions.

use malbolge::{ProfileDescriptor, profile_crazy};

use super::super::super::{BuildError, LAYOUT, TapeBounds};
use super::super::relocated_recurrent_access::AccessBlock;
use super::relocated_recurrent_mod4_source::{
    BYTE_ROUTE, LOAD_CONSTANT, LOOP_RETURN, Mod4Blocks, RELOAD_CONSTANTS,
    SCRATCH, SCRATCH_CONSTANTS, STATE, STATE_CONSTANTS, data_words,
    emit_terminal, seed_address,
};
use super::relocated_recurrent_reload_source::{main_route, spaced_anchors};
use super::{
    ALL_ONES, ALL_TWOS, BYTE, BYTE_ROUTE_POINTER, Blocks, CAPTURE, CONSTANTS,
    RelocatedRecurrentCaptureSource, Route, STATES, Words, bootstrap, code,
    go_anchored, immutable_seed_prefix, initialize_with_extra_seeds, insert,
    previous,
};

const BOUNDS: TapeBounds = TapeBounds {
    limit: 7_280_001,
    start: 7_201_001,
};
#[derive(Clone, Copy)]
struct Projection {
    code_base: u32,
    terminal: u32,
    source_cells: usize,
    count: u32,
    row: u32,
    state_table: u32,
    state_seeds: u32,
    rotations: u32,
    tape_start: u32,
}
const NIBBLE: Projection = Projection {
    code_base: 4_002_044,
    terminal: 4_012_044,
    source_cells: 4_012_170,
    count: 16,
    row: 27,
    state_table: 7_199_010,
    state_seeds: 7_200_000,
    rotations: 3,
    tape_start: BOUNDS.start,
};
const MOD32: Projection = Projection {
    code_base: 5_600_044,
    terminal: 5_610_044,
    source_cells: 5_610_170,
    count: 32,
    row: 81,
    state_table: 7_207_056,
    state_seeds: 7_209_700,
    rotations: 4,
    tape_start: 7_211_001,
};
// Six complemented low trits select a raw-byte table entry.
// The selected seed transforms the projected byte into complemented trits.
// The state table uses an aligned power-of-three row; its high prefix
// allows EOF to decode the projected state using the matching rotations.
const RAW_TABLE: u32 = 7_195_959;
const RAW_SEEDS: u32 = 7_197_000;
const POINTER: u32 = 7_175_140;
const POINTER_CONSTANTS: [u32; 3] = [7_175_150, 7_175_152, 7_175_154];
const RAW_MASK_SEED: u32 = 7_175_160;
const RAW_MASK_PREFIX: u32 = 7_175_164;
const RAW_LOOKUP_CONSTANT: u32 = 7_175_058;
const STATE_LOOKUP_CONSTANT: u32 = 7_175_176;

/// Recurrent bounded checksum projection through two indexed lookups.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct RelocatedRecurrentProjectionSource {
    /// Actual capture, dispatch, reset and terminal sites.
    pub capture: RelocatedRecurrentCaptureSource,
    /// Two physical recurrent load stores.
    pub load: [u32; 2],
    /// Physical immutable transition prefix and value reads.
    pub lookup: [u32; 2],
    /// Physical raw-byte index word.
    pub pointer: u32,
    /// Physical immutable raw projection prefix and value reads.
    pub raw_lookup: [u32; 2],
    /// Physical scratch word holding the next state during reset.
    pub scratch: u32,
    /// Persistent encoded state and transition index.
    pub state: u32,
    /// First instruction of the EOF decoder.
    pub terminal: u32,
}

fn raw_mask(profile: &ProfileDescriptor) -> Result<u32, BuildError> {
    profile_crazy(RAW_TABLE, ALL_TWOS, profile.word_trits())
        .checked_add(364)
        .ok_or(LAYOUT)
}

fn state_mask(
    profile: &ProfileDescriptor,
    state: u32,
    projection: Projection,
) -> Result<u32, BuildError> {
    let base = projection
        .state_table
        .checked_add(state.checked_mul(projection.row).ok_or(LAYOUT)?)
        .ok_or(LAYOUT)?;
    profile_crazy(base, ALL_TWOS, profile.word_trits())
        .checked_add(
            projection
                .row
                .checked_sub(1)
                .and_then(|value| value.checked_div(2))
                .ok_or(LAYOUT)?,
        )
        .ok_or(LAYOUT)
}

fn next_state(state: u32, low: u32, mask: u32) -> Result<u32, BuildError> {
    let update = if low.is_multiple_of(2) {
        state.checked_add(low).ok_or(LAYOUT)?
    } else {
        state ^ low
    };
    Ok(update.checked_add(3).ok_or(LAYOUT)? & mask)
}

fn words(
    profile: &ProfileDescriptor,
    projection: Projection,
) -> Result<Words, BuildError> {
    let mut words =
        data_words(state_mask(profile, 0, projection)?, projection.terminal)?;
    let mask = raw_mask(profile)?;
    for (address, value) in [
        (POINTER, mask),
        (
            RAW_MASK_SEED,
            profile_crazy(ALL_ONES, mask, profile.word_trits()),
        ),
        (RAW_LOOKUP_CONSTANT, ALL_ONES),
        (STATE_LOOKUP_CONSTANT, ALL_ONES),
    ] {
        insert(&mut words, address, value)?;
    }
    let inverse = profile_crazy(ALL_ONES, mask, profile.word_trits());
    insert(
        &mut words,
        RAW_MASK_PREFIX,
        immutable_seed_prefix(inverse, profile.word_trits())?,
    )?;
    let [ones, _, _] = POINTER_CONSTANTS;
    insert(&mut words, ones, ALL_ONES)?;
    Ok(words)
}

fn immutable_records(
    profile: &ProfileDescriptor,
    route: &mut Route<'_>,
    lookup: &AccessBlock,
    (pointer, base): (u32, u32),
    values: &[u32],
) -> Result<(), BuildError> {
    route.enter_ready(lookup, pointer)?;
    let continuation = previous(route.cursor)?;
    for (index, &value) in values.iter().enumerate() {
        let seed =
            seed_address(base, u32::try_from(index).map_err(|_error| LAYOUT)?)?;
        let prefix = immutable_seed_prefix(value, profile.word_trits())?;
        for (offset, word) in [(0, prefix), (1, value), (2, continuation)] {
            insert(route.words, seed.checked_add(offset).ok_or(LAYOUT)?, word)?;
        }
    }
    route.prepare(lookup, false)
}

fn raw_records(
    profile: &ProfileDescriptor,
    route: &mut Route<'_>,
    raw_lookup: &AccessBlock,
    projection: Projection,
) -> Result<(), BuildError> {
    let masks = (0..projection.count)
        .map(|low| {
            let encoded = profile_crazy(ALL_ONES, low, profile.word_trits());
            profile_crazy(encoded, ALL_TWOS, profile.word_trits())
        })
        .collect::<Vec<_>>();
    immutable_records(
        profile,
        route,
        raw_lookup,
        (POINTER, RAW_SEEDS),
        &masks,
    )?;
    for byte in 0..=255u32 {
        let address = RAW_TABLE
            .checked_add(729)
            .and_then(|end| end.checked_sub(byte))
            .ok_or(LAYOUT)?;
        insert(
            route.words,
            address,
            previous(seed_address(
                RAW_SEEDS,
                byte & projection.count.checked_sub(1).ok_or(LAYOUT)?,
            )?)?,
        )?;
    }
    Ok(())
}

fn state_records(
    profile: &ProfileDescriptor,
    route: &mut Route<'_>,
    lookup: &AccessBlock,
    projection: Projection,
) -> Result<(), BuildError> {
    let masks = (0..projection.count)
        .map(|state| state_mask(profile, state, projection))
        .collect::<Result<Vec<_>, _>>()?;
    immutable_records(
        profile,
        route,
        lookup,
        (STATE, projection.state_seeds),
        &masks,
    )?;
    for state in 0..projection.count {
        let end = projection
            .state_table
            .checked_add(
                projection
                    .row
                    .checked_mul(state.checked_add(1).ok_or(LAYOUT)?)
                    .ok_or(LAYOUT)?,
            )
            .ok_or(LAYOUT)?;
        for low in 0..projection.count {
            let address = end.checked_sub(low).ok_or(LAYOUT)?;
            insert(
                route.words,
                address,
                previous(seed_address(
                    projection.state_seeds,
                    next_state(
                        state,
                        low,
                        projection.count.checked_sub(1).ok_or(LAYOUT)?,
                    )?,
                )?)?,
            )?;
        }
    }
    Ok(())
}

// The column-one fold maps every trit to zero or two. On the
// diagonal, both zero and two map to one. Preserve A between folds.
fn reset(
    route: &mut Route<'_>,
    blocks: &Blocks,
    operand: u32,
    [ones, _, _]: [u32; 3],
) -> Result<(), BuildError> {
    let [first, second, _] = &blocks.reset;
    route.call_ready(&blocks.rotate, ones)?;
    route.call_ready(first, operand)?;
    route.call_ready(second, operand)
}

fn restore(
    route: &mut Route<'_>,
    blocks: &Mod4Blocks,
    (seed, destination): (u32, u32),
    constants: [u32; 2],
) -> Result<(), BuildError> {
    for (address, block) in constants.into_iter().zip(&blocks.load) {
        route.call_ready(&blocks.capture.rotate, address)?;
        route.call_ready(block, seed)?;
    }
    let [_, second] = &blocks.load;
    route.call_ready(second, destination)
}

fn byte_route(
    profile: &ProfileDescriptor,
    blocks: &Mod4Blocks,
    lookups: [&AccessBlock; 2],
    words: &mut Words,
    projection: Projection,
) -> Result<(), BuildError> {
    let [raw_lookup, state_lookup] = lookups;
    let mut bridge = Route {
        cursor: BYTE.checked_add(1).ok_or(LAYOUT)?,
        words,
    };
    bridge.prepare(&blocks.capture.branch, false)?;
    bridge.enter_ready(&blocks.capture.branch, BYTE_ROUTE_POINTER)?;
    if bridge.cursor >= BYTE_ROUTE_POINTER {
        return Err(LAYOUT);
    }
    let [first, _] = &blocks.load;
    let mut route = Route {
        cursor: BYTE_ROUTE,
        words,
    };
    route.prepare(&blocks.capture.branch, false)?;
    route.call_ready(&blocks.capture.rotate, LOAD_CONSTANT)?;
    route.call_ready(first, CAPTURE)?;
    route.call_ready(first, POINTER)?;
    route.call_ready(&blocks.capture.rotate, RAW_LOOKUP_CONSTANT)?;
    raw_records(profile, &mut route, raw_lookup, projection)?;
    route.call_ready(first, STATE)?;
    route.call_ready(&blocks.capture.rotate, STATE_LOOKUP_CONSTANT)?;
    state_records(profile, &mut route, state_lookup, projection)?;
    route.call_ready(&blocks.capture.crazy, SCRATCH)?;
    reset(&mut route, &blocks.capture, STATE, STATE_CONSTANTS)?;
    reset(&mut route, &blocks.capture, CAPTURE, CONSTANTS)?;
    restore(&mut route, blocks, (SCRATCH, STATE), RELOAD_CONSTANTS)?;
    reset(&mut route, &blocks.capture, SCRATCH, SCRATCH_CONSTANTS)?;
    reset(&mut route, &blocks.capture, POINTER, POINTER_CONSTANTS)?;
    // The reset leaves A all ones. Both constant words are fixed
    // points, and the final fold restores the raw index mask.
    for address in [RAW_MASK_PREFIX, RAW_MASK_SEED, POINTER] {
        route.call_ready(&blocks.capture.crazy, address)?;
    }
    route.enter_ready(&blocks.capture.branch, LOOP_RETURN)?;
    if route.cursor >= RAW_TABLE.min(projection.state_table) {
        return Err(LAYOUT);
    }
    Ok(())
}

fn lookup_sites(block: &AccessBlock) -> Result<[u32; 2], BuildError> {
    Ok([
        block.start.checked_add(3).ok_or(LAYOUT)?,
        block.start.checked_add(4).ok_or(LAYOUT)?,
    ])
}

/// Execute the low four bits of the mutable checksum until physical EOF.
///
/// Uses 256 raw-byte records and 256 joint nibble transitions.
/// # Errors
/// Refuses unsupported profiles or exhausted physical layout.
pub fn build_relocated_recurrent_nibble_source(
    profile: &ProfileDescriptor,
) -> Result<RelocatedRecurrentProjectionSource, BuildError> {
    build_projection(profile, NIBBLE)
}

/// Execute the low five bits of the mutable checksum until physical EOF.
///
/// Uses 256 raw-byte records and 1,024 joint projected transitions.
/// # Errors
/// Refuses unsupported profiles or exhausted physical layout.
pub fn build_relocated_recurrent_mod32_source(
    profile: &ProfileDescriptor,
) -> Result<RelocatedRecurrentProjectionSource, BuildError> {
    build_projection(profile, MOD32)
}

fn build_projection(
    profile: &ProfileDescriptor,
    projection: Projection,
) -> Result<RelocatedRecurrentProjectionSource, BuildError> {
    let bounds = TapeBounds {
        start: projection.tape_start,
        ..BOUNDS
    };
    let mut emitter = bootstrap(profile, projection.source_cells, bounds)?;
    let blocks = Mod4Blocks::new(profile, projection.code_base)?;
    let state_lookup = AccessBlock::indexed_immutable_load(
        profile,
        code(projection.code_base, 11, 0)?,
    )?;
    let raw_lookup = AccessBlock::indexed_immutable_load(
        profile,
        code(projection.code_base, 13, 0)?,
    )?;
    let mut words = words(profile, projection)?;
    let entry = main_route(&blocks.capture, &mut words)?;
    byte_route(
        profile,
        &blocks,
        [&raw_lookup, &state_lookup],
        &mut words,
        projection,
    )?;
    let anchors = spaced_anchors(&words, 224)?;
    initialize_with_extra_seeds(
        &mut emitter,
        &words,
        &anchors,
        (2, &[], Some((7_175_601, 7_176_000))),
    )?;
    go_anchored(&mut emitter, entry, &anchors)?;
    let _: u32 = emitter.append_indirect()?;
    for block in blocks
        .capture
        .ordered()
        .into_iter()
        .chain(&blocks.load)
        .chain([&state_lookup, &raw_lookup])
    {
        block.emit(&mut emitter)?;
    }
    let (output, halt) =
        emit_terminal(&mut emitter, projection.terminal, projection.rotations)?;
    let [first, second, third] = &blocks.capture.reset;
    let [load_first, load_second] = &blocks.load;
    Ok(RelocatedRecurrentProjectionSource {
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
        lookup: lookup_sites(&state_lookup)?,
        pointer: POINTER,
        raw_lookup: lookup_sites(&raw_lookup)?,
        scratch: SCRATCH,
        state: STATE,
        terminal: projection.terminal,
    })
}
