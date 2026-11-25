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
//   - Physical input-dependent recurrent selection and parity state.
// - Must-Not:
//   - Claim C source admission or general checksum arithmetic.
// - Allows:
//   - Inputs: exact current N15 profile.
//   - Outputs: graphical source and proposed physical effect sites.
//   - Side effects: none; independent VM replay owns acceptance.
// - Split-When:
//   - General recurrent operand allocation replaces fixed geometry.
// - Merge-When:
//   - Whole checksum lowering owns recurrent arithmetic.
// - Summary:
//   - Select a guest parity update through an unmodified loader lookup.

use malbolge::ProfileDescriptor;

use super::super::super::super::LinearOpcode;
use super::super::super::{BuildError, FRAME, LAYOUT, TapeBounds};
use super::super::relocated_recurrent_access::AccessBlock;
use super::relocated_recurrent_reload_source::{anchors, main_route, reset};
use super::{
    ALL_ONES, ALL_TWOS, BYTE, BYTE_ROUTE_POINTER, Blocks, CAPTURE, CONSTANTS,
    EOF, INITIAL, MAIN_ROUTE, RelocatedRecurrentCaptureSource, Route, STATES,
    Words, access, bootstrap, code, go_anchored, initialize_with_dispatch,
    insert, previous,
};

const BOUNDS: TapeBounds = TapeBounds {
    limit: 7_280_001,
    start: 7_186_001,
};
const CODE_BASE: u32 = 6_400_000;
const TERMINAL: u32 = 6_420_000;
const SOURCE_CELLS: usize = 6_420_168;
const BYTE_ROUTE: u32 = 7_181_000;
const EVEN_ROUTE: u32 = 7_181_820;
const ODD_ROUTE: u32 = 7_181_800;
const COMMON_ROUTE: u32 = 7_182_100;
const POINTER: u32 = 7_175_080;
const POINTER_CONSTANTS: [u32; 3] = [7_175_060, 7_175_062, 7_175_064];
const LOAD_CONSTANT: u32 = 7_175_050;
const UPDATE_CONSTANT: u32 = 7_175_052;
const PARITY_STATE: u32 = 7_175_100;
// Column two exchanges 334080 and 462339. Rotation produces respectively
// 111360 and 154113, whose normative output bytes are 0 and 1.
const INITIAL_PARITY: u32 = 334_080;
const EVEN_RETURN: u32 = 7_175_110;
const ODD_RETURN: u32 = 7_175_112;
const LOOP_RETURN: u32 = 7_175_090;

/// Recurrent guest selection of a mutable parity update.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct RelocatedRecurrentParitySource {
    /// Actual input, EOF guard, reset and terminal effect sites.
    pub capture: RelocatedRecurrentCaptureSource,
    /// Crazy store transforming the captured encoding.
    pub load: u32,
    /// Physical complement pointer.
    pub pointer: u32,
    /// Three dependent relocations after selecting the pointer.
    pub selector: [u32; 3],
    /// Persistent parity state, rotated once on EOF.
    pub state: u32,
}

struct ParityBlocks {
    capture: Blocks,
    load: AccessBlock,
    selector: AccessBlock,
}

impl ParityBlocks {
    fn new(profile: &ProfileDescriptor) -> Result<Self, BuildError> {
        Ok(Self {
            capture: Blocks::new(profile, CODE_BASE)?,
            load: access(
                profile,
                (CODE_BASE, 8, 93),
                LinearOpcode::CrazyData,
                (0, 4, true),
            )?,
            selector: AccessBlock::selector(profile, code(CODE_BASE, 9, 92)?)?,
        })
    }
}

fn data_words() -> Result<Words, BuildError> {
    let mut words = Words::new();
    for (address, value) in [
        (CAPTURE, ALL_ONES),
        (POINTER, ALL_ONES),
        (PARITY_STATE, INITIAL_PARITY),
        (LOAD_CONSTANT, ALL_TWOS),
        (UPDATE_CONSTANT, ALL_TWOS),
        (BYTE_ROUTE_POINTER, previous(BYTE_ROUTE)?),
        (EVEN_RETURN, previous(COMMON_ROUTE)?),
        (ODD_RETURN, previous(COMMON_ROUTE)?),
        (LOOP_RETURN, previous(MAIN_ROUTE)?),
    ] {
        insert(&mut words, address, value)?;
    }
    for (address, value) in STATES.into_iter().zip(INITIAL) {
        insert(&mut words, address, value)?;
    }
    for constants in [CONSTANTS, POINTER_CONSTANTS] {
        for (address, value) in
            constants.into_iter().zip([ALL_ONES, ALL_TWOS, 0])
        {
            insert(&mut words, address, value)?;
        }
    }
    for landing in EOF {
        insert(
            &mut words,
            landing.checked_add(1).ok_or(LAYOUT)?,
            previous(TERMINAL)?,
        )?;
        insert(
            &mut words,
            landing.checked_add(2).ok_or(LAYOUT)?,
            previous(PARITY_STATE)?,
        )?;
    }
    Ok(words)
}

fn byte_route(
    blocks: &ParityBlocks,
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
    route.enter_ready(&blocks.selector, POINTER)?;
    if route.cursor >= ODD_ROUTE {
        return Err(LAYOUT);
    }
    Ok(())
}

fn parity_routes(
    blocks: &ParityBlocks,
    words: &mut Words,
) -> Result<(), BuildError> {
    let mut odd = Route { cursor: ODD_ROUTE, words };
    odd.enter_ready(&blocks.capture.branch, ODD_RETURN)?;
    if odd.cursor >= EVEN_ROUTE {
        return Err(LAYOUT);
    }
    let mut even = Route {
        cursor: EVEN_ROUTE,
        words,
    };
    even.call_ready(&blocks.capture.rotate, UPDATE_CONSTANT)?;
    even.call_ready(&blocks.capture.crazy, PARITY_STATE)?;
    even.enter_ready(&blocks.capture.branch, EVEN_RETURN)?;
    if even.cursor >= COMMON_ROUTE {
        return Err(LAYOUT);
    }
    let mut common = Route {
        cursor: COMMON_ROUTE,
        words,
    };
    common.prepare(&blocks.capture.branch, false)?;
    common.prepare(&blocks.selector, false)?;
    reset(&mut common, &blocks.capture, CAPTURE, CONSTANTS)?;
    reset(&mut common, &blocks.capture, POINTER, POINTER_CONSTANTS)?;
    common.enter_ready(&blocks.capture.branch, LOOP_RETURN)?;
    if common.cursor >= BOUNDS.start {
        return Err(LAYOUT);
    }
    Ok(())
}

/// Construct a guest whose even-byte arm alone mutates recurrent state.
/// The output on EOF is the low bit of the original checksum recurrence:
/// both XOR and addition have the same low bit; adding three flips it.
/// This is a one-bit projection, not a full-byte checksum.
///
/// # Errors
/// Refuses unsupported profiles or exhausted physical route geometry.
pub fn build_relocated_recurrent_parity_source(
    profile: &ProfileDescriptor,
) -> Result<RelocatedRecurrentParitySource, BuildError> {
    let mut emitter = bootstrap(profile, SOURCE_CELLS, BOUNDS)?;
    let blocks = ParityBlocks::new(profile)?;
    let mut words = data_words()?;
    let entry = main_route(&blocks.capture, &mut words)?;
    byte_route(&blocks, &mut words)?;
    parity_routes(&blocks, &mut words)?;
    let anchors = anchors(&words)?;
    initialize_with_dispatch(&mut emitter, &words, &anchors, 2, &[
        (0, 37),
        (38, previous(EVEN_ROUTE)?),
        (FRAME, previous(ODD_ROUTE)?),
    ])?;
    go_anchored(&mut emitter, entry, &anchors)?;
    let _: u32 = emitter.append_indirect()?;
    for block in blocks
        .capture
        .ordered()
        .into_iter()
        .chain([&blocks.load, &blocks.selector])
    {
        block.emit(&mut emitter)?;
    }
    emitter
        .pad_to_entry(usize::try_from(TERMINAL).map_err(|_error| LAYOUT)?, 0)?;
    let _: u32 = emitter.append(LinearOpcode::RelocateDataPointer)?;
    let _: u32 = emitter.append(LinearOpcode::RotateData)?;
    let output = emitter.append(LinearOpcode::OutputByte)?;
    let halt = emitter.append(LinearOpcode::Halt)?;
    let [first, second, third] = &blocks.capture.reset;
    let selector = blocks.selector.operation_site()?;
    Ok(RelocatedRecurrentParitySource {
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
        load: blocks.load.operation_site()?,
        pointer: POINTER,
        selector: [
            selector,
            selector.checked_add(1).ok_or(LAYOUT)?,
            selector.checked_add(2).ok_or(LAYOUT)?,
        ],
        state: PARITY_STATE,
    })
}
