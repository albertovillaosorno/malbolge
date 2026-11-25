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
//   - Recurrent physical indexed word loading through initialized tables.
// - Must-Not:
//   - Claim source-C checksum admission or host-computed guest effects.
// - Allows:
//   - Inputs: exact N15 profile and deterministic nibble table.
//   - Outputs: graphical source and proposed physical effect sites.
//   - Side effects: none; normative VM replay owns acceptance.
// - Split-When:
//   - Recurrent checksum lowering owns general table allocation.
// - Merge-When:
//   - A general reusable guest table runtime subsumes the witness.
// - Summary:
//   - Select, reversibly read and restore a data-indexed constant.

use malbolge::{ProfileDescriptor, profile_crazy};

use super::super::super::super::LinearOpcode;
use super::super::super::{BuildError, LAYOUT, TapeBounds};
use super::super::relocated_recurrent_access::AccessBlock;
use super::relocated_recurrent_reload_source::{anchors, main_route, reset};
use super::{
    ALL_ONES, ALL_TWOS, BYTE, BYTE_ROUTE_POINTER, Blocks, CAPTURE, CONSTANTS,
    EOF, INITIAL, MAIN_ROUTE, RelocatedRecurrentCaptureSource, Route, STATES,
    Words, access, bootstrap, code, go_anchored, initialize, insert, previous,
};

const BOUNDS: TapeBounds = TapeBounds {
    limit: 7_280_001,
    start: 7_186_001,
};
const CODE_BASE: u32 = 3_660_000;
const TERMINAL: u32 = 3_670_000;
const SOURCE_CELLS: usize = 3_670_010;
const BYTE_ROUTE: u32 = 7_181_000;
const POINTER: u32 = 7_175_080;
const POINTER_CONSTANTS: [u32; 3] = [7_175_060, 7_175_062, 7_175_064];
const LOAD_CONSTANT: u32 = 7_175_050;
const LOOKUP_CONSTANT: u32 = 7_175_052;
const MASK_CONSTANTS: [u32; 2] = [7_175_054, 7_175_056];
const MASK_SEED: u32 = 7_175_120;
const ECHO_OPERAND: u32 = 7_175_130;
const LOOP_RETURN: u32 = 7_175_090;
// The six low trits of the complemented byte are retained. The
// high trits select a disjoint table above the recurrent route.
const TABLE_BASE: u32 = 7_184_295;
const TABLE_END: u32 = 7_185_024;
const SEED_BASE: u32 = 7_185_500;
const SEED_STRIDE: u32 = 8;

/// Recurrent indexed immutable-word access after real input dispatch.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct RelocatedRecurrentIndexedSource {
    /// Actual recurrent capture, reset and terminal effect sites.
    pub capture: RelocatedRecurrentCaptureSource,
    /// Physical output of each dynamically selected table word.
    pub echo: u32,
    /// Physical first seed store and restoring seed store.
    pub lookup: [u32; 2],
    /// Physical store turning the captured byte into an index.
    pub load: u32,
    /// Physical complemented index pointer.
    pub pointer: u32,
    /// Initial and restored pointer mask.
    pub pointer_mask: u32,
    /// Physical rotation of the selected record's uniform constant.
    pub seed_rotate: u32,
}

struct IndexedBlocks {
    capture: Blocks,
    echo: AccessBlock,
    load: AccessBlock,
    lookup: [AccessBlock; 2],
}

impl IndexedBlocks {
    fn new(profile: &ProfileDescriptor) -> Result<Self, BuildError> {
        use LinearOpcode::{CrazyData, OutputByte};
        Ok(Self {
            capture: Blocks::new(profile, CODE_BASE)?,
            echo: access(
                profile,
                (CODE_BASE, 9, 72),
                OutputByte,
                (0, 0, true),
            )?,
            load: access(profile, (CODE_BASE, 8, 93), CrazyData, (0, 4, true))?,
            lookup: AccessBlock::indexed_load(profile, [
                code(CODE_BASE, 11, 0)?,
                code(CODE_BASE, 12, 0)?,
            ])?,
        })
    }
}

fn mask(profile: &ProfileDescriptor) -> Result<u32, BuildError> {
    // At every high trit the transformed raw capture has digit two.
    // Crazy column two is its own inverse: [0, 2, 1].
    // Low data digits stay one and therefore complement the byte.
    profile_crazy(TABLE_BASE, ALL_TWOS, profile.word_trits())
        .checked_add(364)
        .ok_or(LAYOUT)
}

fn data_words(profile: &ProfileDescriptor) -> Result<Words, BuildError> {
    let mut words = Words::new();
    let pointer_mask = mask(profile)?;
    for (address, value) in [
        (CAPTURE, ALL_ONES),
        (POINTER, pointer_mask),
        (LOAD_CONSTANT, ALL_TWOS),
        (LOOKUP_CONSTANT, ALL_TWOS),
        (
            MASK_SEED,
            profile_crazy(ALL_ONES, pointer_mask, profile.word_trits()),
        ),
        (BYTE_ROUTE_POINTER, previous(BYTE_ROUTE)?),
        (LOOP_RETURN, previous(MAIN_ROUTE)?),
    ] {
        insert(&mut words, address, value)?;
    }
    for (address, value) in STATES.into_iter().zip(INITIAL) {
        insert(&mut words, address, value)?;
    }
    for address in MASK_CONSTANTS {
        insert(&mut words, address, ALL_TWOS)?;
    }
    for constants in [CONSTANTS, POINTER_CONSTANTS] {
        for (address, value) in
            constants.into_iter().zip([ALL_ONES, ALL_TWOS, 0])
        {
            insert(&mut words, address, value)?;
        }
    }
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

fn seed_address(nibble: u32) -> Result<u32, BuildError> {
    SEED_BASE
        .checked_add(nibble.checked_mul(SEED_STRIDE).ok_or(LAYOUT)?)
        .ok_or(LAYOUT)
}

fn table_records(
    route: &mut Route<'_>,
    blocks: &IndexedBlocks,
) -> Result<(), BuildError> {
    let [first, second] = &blocks.lookup;
    route.enter_ready(first, POINTER)?;
    let continuation = previous(route.cursor)?;
    for nibble in 0..16u32 {
        let seed = seed_address(nibble)?;
        let transfer = seed.checked_add(4).ok_or(LAYOUT)?;
        for (offset, value) in [
            (0, nibble),
            (1, previous(transfer)?),
            (2, continuation),
            (4, previous(second.start)?),
            (5, ALL_TWOS),
            (6, previous(seed)?),
        ] {
            insert(
                route.words,
                seed.checked_add(offset).ok_or(LAYOUT)?,
                value,
            )?;
        }
    }
    for byte in 0..=255u32 {
        let address = TABLE_END.checked_sub(byte).ok_or(LAYOUT)?;
        insert(route.words, address, previous(seed_address(byte >> 4)?)?)?;
    }
    route.prepare(first, false)?;
    route.prepare(second, false)?;
    Ok(())
}

fn byte_route(
    blocks: &IndexedBlocks,
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
    let mut route = Route {
        cursor: BYTE_ROUTE,
        words,
    };
    route.prepare(&blocks.capture.branch, false)?;
    route.call_ready(&blocks.capture.rotate, LOAD_CONSTANT)?;
    route.call_ready(&blocks.load, CAPTURE)?;
    route.call_ready(&blocks.capture.crazy, POINTER)?;
    route.call_ready(&blocks.capture.rotate, LOOKUP_CONSTANT)?;
    table_records(&mut route, blocks)?;
    route.call_ready(&blocks.echo, ECHO_OPERAND)?;
    reset(&mut route, &blocks.capture, CAPTURE, CONSTANTS)?;
    reset(&mut route, &blocks.capture, POINTER, POINTER_CONSTANTS)?;
    for (address, block) in MASK_CONSTANTS
        .into_iter()
        .zip([&blocks.capture.crazy, &blocks.load])
    {
        route.call_ready(&blocks.capture.rotate, address)?;
        route.call_ready(block, MASK_SEED)?;
    }
    route.call_ready(&blocks.load, POINTER)?;
    route.enter_ready(&blocks.capture.branch, LOOP_RETURN)?;
    if route.cursor >= TABLE_END.checked_sub(255).ok_or(LAYOUT)? {
        return Err(LAYOUT);
    }
    Ok(())
}

/// Decode each successful byte's high binary nibble in a recurrent guest.
///
/// Each selected table record is physically read and restored by two
/// crazy stores, while the lookup itself uses real data relocations.
/// EOF bypasses the lookup and terminates with length parity.
///
/// # Errors
/// Refuses unsupported profiles or exhausted physical route geometry.
pub fn build_relocated_recurrent_indexed_source(
    profile: &ProfileDescriptor,
) -> Result<RelocatedRecurrentIndexedSource, BuildError> {
    let mut emitter = bootstrap(profile, SOURCE_CELLS, BOUNDS)?;
    let blocks = IndexedBlocks::new(profile)?;
    let mut words = data_words(profile)?;
    let entry = main_route(&blocks.capture, &mut words)?;
    byte_route(&blocks, &mut words)?;
    let anchors = anchors(&words)?;
    initialize(&mut emitter, &words, &anchors, 2)?;
    go_anchored(&mut emitter, entry, &anchors)?;
    let _: u32 = emitter.append_indirect()?;
    for block in blocks
        .capture
        .ordered()
        .into_iter()
        .chain([&blocks.load, &blocks.echo])
        .chain(blocks.lookup.iter())
    {
        block.emit(&mut emitter)?;
    }
    emitter
        .pad_to_entry(usize::try_from(TERMINAL).map_err(|_error| LAYOUT)?, 0)?;
    let _: u32 = emitter.append(LinearOpcode::RotateData)?;
    let output = emitter.append(LinearOpcode::OutputByte)?;
    let halt = emitter.append(LinearOpcode::Halt)?;
    let [first, second, third] = &blocks.capture.reset;
    let [lookup_first, lookup_second] = &blocks.lookup;
    Ok(RelocatedRecurrentIndexedSource {
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
        echo: blocks.echo.operation_site()?,
        load: blocks.load.operation_site()?,
        lookup: [
            lookup_first.start.checked_add(3).ok_or(LAYOUT)?,
            lookup_second.start.checked_add(2).ok_or(LAYOUT)?,
        ],
        pointer: POINTER,
        pointer_mask: mask(profile)?,
        seed_rotate: lookup_second.start,
    })
}
