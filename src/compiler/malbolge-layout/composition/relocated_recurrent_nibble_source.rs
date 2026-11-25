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
//   - Recurrent physical four-bit checksum state and EOF output.
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
//   - Factor byte selection from four-bit recurrent state transitions.

use malbolge::{ProfileDescriptor, profile_crazy};

use super::super::super::{BuildError, LAYOUT, TapeBounds};
use super::super::relocated_recurrent_access::AccessBlock;
use super::relocated_recurrent_mod4_source::{
    BYTE_ROUTE, LOAD_CONSTANT, LOOKUP_CONSTANT, LOOP_RETURN, Mod4Blocks,
    RELOAD_CONSTANTS, SCRATCH, SCRATCH_CONSTANTS, STATE, STATE_CONSTANTS,
    data_words, emit_terminal, seed_address, seed_records,
};
use super::relocated_recurrent_reload_source::{
    main_route, reset, spaced_anchors,
};
use super::{
    ALL_ONES, ALL_TWOS, BYTE, BYTE_ROUTE_POINTER, CAPTURE, CONSTANTS,
    RelocatedRecurrentCaptureSource, Route, STATES, Words, bootstrap, code,
    go_anchored, initialize_with_extra_seeds, insert, previous,
};

const BOUNDS: TapeBounds = TapeBounds {
    limit: 7_280_001,
    start: 7_201_001,
};
const CODE_BASE: u32 = 5_600_044;
const TERMINAL: u32 = 5_610_044;
const SOURCE_CELLS: usize = 5_610_170;
// Six complemented low trits select a raw-byte table entry.
// The selected seed transforms the nibble into three complemented trits;
// the state table then uses a 27-cell row. Its aligned high prefix also
// allows EOF to decode the projected state using three rotations.
const RAW_TABLE: u32 = 7_195_959;
const RAW_SEEDS: u32 = 7_197_000;
const STATE_TABLE: u32 = 7_199_010;
const STATE_SEEDS: u32 = 7_200_000;
const POINTER: u32 = 7_175_140;
const POINTER_CONSTANTS: [u32; 3] = [7_175_150, 7_175_152, 7_175_154];
const RAW_MASK_SEED: u32 = 7_175_160;
const POINTER_RELOAD_CONSTANTS: [u32; 2] = [7_175_170, 7_175_172];
const RAW_LOOKUP_CONSTANT: u32 = 7_175_058;

/// Recurrent four-bit checksum projection through two indexed lookups.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct RelocatedRecurrentNibbleSource {
    /// Actual capture, dispatch, reset and terminal sites.
    pub capture: RelocatedRecurrentCaptureSource,
    /// Two physical recurrent load stores.
    pub load: [u32; 2],
    /// Physical first and restoring transition seed stores.
    pub lookup: [u32; 2],
    /// Physical raw-byte index word.
    pub pointer: u32,
    /// Physical first and restoring raw projection seed stores.
    pub raw_lookup: [u32; 2],
    /// Physical rotation of the selected raw record's all-two constant.
    pub raw_seed_rotate: u32,
    /// Physical scratch word holding the next state during reset.
    pub scratch: u32,
    /// Physical rotation of the transition record's all-two constant.
    pub seed_rotate: u32,
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
) -> Result<u32, BuildError> {
    let base = STATE_TABLE
        .checked_add(state.checked_mul(27).ok_or(LAYOUT)?)
        .ok_or(LAYOUT)?;
    profile_crazy(base, ALL_TWOS, profile.word_trits())
        .checked_add(13)
        .ok_or(LAYOUT)
}

fn next_state(state: u32, nibble: u32) -> Result<u32, BuildError> {
    let update = if nibble.is_multiple_of(2) {
        state.checked_add(nibble).ok_or(LAYOUT)?
    } else {
        state ^ nibble
    };
    Ok(update.checked_add(3).ok_or(LAYOUT)? & 15)
}

fn words(profile: &ProfileDescriptor) -> Result<Words, BuildError> {
    let mut words = data_words(state_mask(profile, 0)?, TERMINAL)?;
    let mask = raw_mask(profile)?;
    for (address, value) in [
        (POINTER, mask),
        (
            RAW_MASK_SEED,
            profile_crazy(ALL_ONES, mask, profile.word_trits()),
        ),
        (RAW_LOOKUP_CONSTANT, ALL_TWOS),
    ] {
        insert(&mut words, address, value)?;
    }
    for address in POINTER_RELOAD_CONSTANTS {
        insert(&mut words, address, ALL_TWOS)?;
    }
    for (address, value) in
        POINTER_CONSTANTS.into_iter().zip([ALL_ONES, ALL_TWOS, 0])
    {
        insert(&mut words, address, value)?;
    }
    Ok(words)
}

fn raw_records(
    profile: &ProfileDescriptor,
    route: &mut Route<'_>,
    raw_lookup: &[AccessBlock; 2],
) -> Result<(), BuildError> {
    let masks = (0..16u32)
        .map(|nibble| {
            let encoded = profile_crazy(ALL_ONES, nibble, profile.word_trits());
            profile_crazy(encoded, ALL_TWOS, profile.word_trits())
        })
        .collect::<Vec<_>>();
    seed_records(route, raw_lookup, (POINTER, RAW_SEEDS), &masks)?;
    for byte in 0..=255u32 {
        let address = RAW_TABLE
            .checked_add(729)
            .and_then(|end| end.checked_sub(byte))
            .ok_or(LAYOUT)?;
        insert(
            route.words,
            address,
            previous(seed_address(RAW_SEEDS, byte & 15)?)?,
        )?;
    }
    Ok(())
}

fn state_records(
    profile: &ProfileDescriptor,
    route: &mut Route<'_>,
    lookup: &[AccessBlock; 2],
) -> Result<(), BuildError> {
    let masks = (0..16u32)
        .map(|state| state_mask(profile, state))
        .collect::<Result<Vec<_>, _>>()?;
    seed_records(route, lookup, (STATE, STATE_SEEDS), &masks)?;
    for state in 0..16u32 {
        let end = STATE_TABLE
            .checked_add(
                27u32
                    .checked_mul(state.checked_add(1).ok_or(LAYOUT)?)
                    .ok_or(LAYOUT)?,
            )
            .ok_or(LAYOUT)?;
        for nibble in 0..16u32 {
            let address = end.checked_sub(nibble).ok_or(LAYOUT)?;
            insert(
                route.words,
                address,
                previous(seed_address(
                    STATE_SEEDS,
                    next_state(state, nibble)?,
                )?)?,
            )?;
        }
    }
    Ok(())
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
    raw_lookup: &[AccessBlock; 2],
    words: &mut Words,
) -> Result<(), BuildError> {
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
    raw_records(profile, &mut route, raw_lookup)?;
    route.call_ready(first, STATE)?;
    route.call_ready(&blocks.capture.rotate, LOOKUP_CONSTANT)?;
    state_records(profile, &mut route, &blocks.lookup)?;
    route.call_ready(&blocks.capture.crazy, SCRATCH)?;
    reset(&mut route, &blocks.capture, STATE, STATE_CONSTANTS)?;
    reset(&mut route, &blocks.capture, CAPTURE, CONSTANTS)?;
    restore(&mut route, blocks, (SCRATCH, STATE), RELOAD_CONSTANTS)?;
    reset(&mut route, &blocks.capture, SCRATCH, SCRATCH_CONSTANTS)?;
    reset(&mut route, &blocks.capture, POINTER, POINTER_CONSTANTS)?;
    restore(
        &mut route,
        blocks,
        (RAW_MASK_SEED, POINTER),
        POINTER_RELOAD_CONSTANTS,
    )?;
    route.enter_ready(&blocks.capture.branch, LOOP_RETURN)?;
    if route.cursor >= RAW_TABLE {
        return Err(LAYOUT);
    }
    Ok(())
}

fn lookup_sites(blocks: &[AccessBlock; 2]) -> Result<[u32; 2], BuildError> {
    let [first, second] = blocks;
    Ok([
        first.start.checked_add(3).ok_or(LAYOUT)?,
        second.start.checked_add(2).ok_or(LAYOUT)?,
    ])
}

/// Execute the low four bits of the mutable checksum until physical EOF.
///
/// Uses 256 raw-byte records and 256 joint nibble transitions.
/// # Errors
/// Refuses unsupported profiles or exhausted physical layout.
pub fn build_relocated_recurrent_nibble_source(
    profile: &ProfileDescriptor,
) -> Result<RelocatedRecurrentNibbleSource, BuildError> {
    let mut emitter = bootstrap(profile, SOURCE_CELLS, BOUNDS)?;
    let blocks = Mod4Blocks::new(profile, CODE_BASE)?;
    let raw_lookup = AccessBlock::indexed_load(profile, [
        code(CODE_BASE, 13, 0)?,
        code(CODE_BASE, 14, 0)?,
    ])?;
    let mut words = words(profile)?;
    let entry = main_route(&blocks.capture, &mut words)?;
    byte_route(profile, &blocks, &raw_lookup, &mut words)?;
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
        .chain(&blocks.lookup)
        .chain(&raw_lookup)
    {
        block.emit(&mut emitter)?;
    }
    let (output, halt) = emit_terminal(&mut emitter, TERMINAL, 3)?;
    let [first, second, third] = &blocks.capture.reset;
    let [load_first, load_second] = &blocks.load;
    let [_, lookup_second] = &blocks.lookup;
    let [_, raw_second] = &raw_lookup;
    Ok(RelocatedRecurrentNibbleSource {
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
        lookup: lookup_sites(&blocks.lookup)?,
        pointer: POINTER,
        raw_lookup: lookup_sites(&raw_lookup)?,
        raw_seed_rotate: raw_second.start,
        scratch: SCRATCH,
        seed_rotate: lookup_second.start,
        state: STATE,
        terminal: TERMINAL,
    })
}
