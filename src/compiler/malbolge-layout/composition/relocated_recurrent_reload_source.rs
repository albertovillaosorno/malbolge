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
//   - Physical recovery of captured bytes after the recurrent EOF guard.
// - Must-Not:
//   - Claim source-frame admission or checksum arithmetic.
// - Allows:
//   - Inputs: exact current N15 profile.
//   - Outputs: graphical source and proposed physical capture sites.
//   - Side effects: none; normative VM replay owns acceptance.
// - Split-When:
//   - General recurrent operand allocation replaces fixed tape geometry.
// - Merge-When:
//   - Whole checksum lowering owns recurrent source operands.
// - Summary:
//   - Reload the captured encoding with two reversible crazy stores.

use malbolge::ProfileDescriptor;

use super::super::super::super::LinearOpcode;
use super::super::super::{BuildError, LAYOUT, TapeBounds};
use super::super::relocated_recurrent_access::AccessBlock;
use super::{
    ALL_ONES, ALL_TWOS, ANCHOR_START, BYTE, BYTE_ROUTE_POINTER, Blocks,
    CAPTURE, CONSTANTS, EOF, INITIAL, INPUT, MAIN_ROUTE,
    RelocatedRecurrentCaptureSource, Route, STATES, Words, access, bootstrap,
    go_anchored, initialize, insert, previous,
};

const BOUNDS: TapeBounds = TapeBounds {
    limit: 7_280_001,
    start: 7_186_001,
};
const CODE_BASE: u32 = 6_430_000;
const TERMINAL: u32 = 6_450_000;
const SOURCE_CELLS: usize = 6_450_060;
const RELOAD_ROUTE: u32 = 7_181_000;
const LOAD_CONSTANTS: [u32; 2] = [7_175_050, 7_175_052];
const RAW_CONSTANTS: [u32; 3] = [7_175_060, 7_175_062, 7_175_064];
const ECHO_OPERAND: u32 = 7_175_070;
const RAW: u32 = 7_175_080;
const RETURN_POINTER: u32 = 7_175_090;

/// Recurrent capture followed by real guest reload and byte output.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct RelocatedRecurrentReloadSource {
    /// Actual input, guard, reset and terminal effect sites.
    pub capture: RelocatedRecurrentCaptureSource,
    /// Recurrent physical output of the reloaded byte.
    pub echo: u32,
    /// Two actual reversible loads of the dirty captured word.
    pub load: [u32; 2],
    /// Physical word holding the reloaded raw byte.
    pub raw: u32,
}

type Anchors = Vec<(u32, u32)>;
type Routes = (Words, u32);

struct ReloadBlocks {
    capture: Blocks,
    echo: AccessBlock,
    load: [AccessBlock; 2],
}

impl ReloadBlocks {
    fn new(profile: &ProfileDescriptor) -> Result<Self, BuildError> {
        use LinearOpcode::{CrazyData, OutputByte};
        Ok(Self {
            capture: Blocks::new(profile, CODE_BASE)?,
            echo: access(
                profile,
                (CODE_BASE, 10, 72),
                OutputByte,
                (0, 0, true),
            )?,
            load: [
                access(profile, (CODE_BASE, 8, 93), CrazyData, (0, 4, true))?,
                access(profile, (CODE_BASE, 9, 93), CrazyData, (0, 5, true))?,
            ],
        })
    }
}

fn anchors(words: &Words) -> Result<Anchors, BuildError> {
    let mut result = Vec::new();
    let mut next_base = 0u32;
    let mut address = ANCHOR_START;
    for &target in words.keys() {
        if target < next_base {
            continue;
        }
        if address >= CAPTURE {
            return Err(LAYOUT);
        }
        result.push((address, target));
        address = address.checked_add(2).ok_or(LAYOUT)?;
        next_base = target.checked_add(192).ok_or(LAYOUT)?;
    }
    Ok(result)
}

fn data_words() -> Result<Words, BuildError> {
    let mut words = Words::new();
    insert(&mut words, CAPTURE, ALL_ONES)?;
    insert(&mut words, RAW, ALL_ONES)?;
    insert(&mut words, RETURN_POINTER, previous(MAIN_ROUTE)?)?;
    for (address, value) in STATES.into_iter().zip(INITIAL) {
        insert(&mut words, address, value)?;
    }
    for address in LOAD_CONSTANTS {
        insert(&mut words, address, ALL_TWOS)?;
    }
    for constants in [CONSTANTS, RAW_CONSTANTS] {
        for (address, value) in
            constants.into_iter().zip([ALL_ONES, ALL_TWOS, 0])
        {
            insert(&mut words, address, value)?;
        }
    }
    Ok(words)
}

fn main_route(blocks: &Blocks, words: &mut Words) -> Result<u32, BuildError> {
    let mut route = Route {
        cursor: MAIN_ROUTE,
        words,
    };
    // The initial invocation skips this restoration; a loop return
    // has just executed the branch block and must restore it.
    route.prepare(&blocks.branch, false)?;
    let entry = route.cursor;
    route.call_ready(&blocks.input, INPUT)?;
    route.call_ready(&blocks.crazy, CAPTURE)?;
    for address in STATES {
        route.call_ready(&blocks.crazy, address)?;
    }
    let [_, _, _, _, _, class] = STATES;
    route.enter_ready(&blocks.branch, class)?;
    if route.cursor >= EOF.into_iter().min().ok_or(LAYOUT)? {
        return Err(LAYOUT);
    }
    Ok(entry)
}

fn reset(
    route: &mut Route<'_>,
    blocks: &Blocks,
    operand: u32,
    constants: [u32; 3],
) -> Result<(), BuildError> {
    for (address, block) in constants.into_iter().zip(&blocks.reset) {
        route.call_ready(&blocks.rotate, address)?;
        route.call_ready(block, operand)?;
    }
    Ok(())
}

fn byte_route(
    blocks: &ReloadBlocks,
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
    insert(words, BYTE_ROUTE_POINTER, previous(RELOAD_ROUTE)?)?;
    let mut route = Route {
        cursor: RELOAD_ROUTE,
        words,
    };
    route.prepare(&blocks.capture.branch, false)?;
    for (address, block) in LOAD_CONSTANTS.into_iter().zip(&blocks.load) {
        route.call_ready(&blocks.capture.rotate, address)?;
        route.call_ready(block, CAPTURE)?;
    }
    route.call_ready(&blocks.capture.crazy, RAW)?;
    route.call_ready(&blocks.echo, ECHO_OPERAND)?;
    reset(&mut route, &blocks.capture, CAPTURE, CONSTANTS)?;
    reset(&mut route, &blocks.capture, RAW, RAW_CONSTANTS)?;
    route.enter_ready(&blocks.capture.branch, RETURN_POINTER)?;
    if route.cursor >= BOUNDS.start {
        return Err(LAYOUT);
    }
    Ok(())
}

fn routes(blocks: &ReloadBlocks) -> Result<Routes, BuildError> {
    let mut words = data_words()?;
    let entry = main_route(&blocks.capture, &mut words)?;
    byte_route(blocks, &mut words)?;
    for (landing, value) in EOF.into_iter().zip([3, 0]) {
        insert(
            &mut words,
            landing.checked_add(1).ok_or(LAYOUT)?,
            previous(TERMINAL)?,
        )?;
        insert(&mut words, landing.checked_add(2).ok_or(LAYOUT)?, value)?;
    }
    Ok((words, entry))
}

/// Reload and emit each actual byte after recurrent EOF dispatch.
///
/// The two crazy loads restore the encoded capture and pass it to
/// an all-one word whose actual store recovers the original byte.
/// Both dirty words are reset before the backedge. EOF skips reload.
///
/// # Errors
/// Refuses unsupported profiles, unsafe restoration and exhausted geometry.
pub fn build_relocated_recurrent_reload_source(
    profile: &ProfileDescriptor,
) -> Result<RelocatedRecurrentReloadSource, BuildError> {
    let mut emitter = bootstrap(profile, SOURCE_CELLS, BOUNDS)?;
    let blocks = ReloadBlocks::new(profile)?;
    let (words, entry) = routes(&blocks)?;
    let anchors = anchors(&words)?;
    initialize(&mut emitter, &words, &anchors, 2)?;
    go_anchored(&mut emitter, entry, &anchors)?;
    let _: u32 = emitter.append_indirect()?;
    for block in blocks
        .capture
        .ordered()
        .into_iter()
        .chain(blocks.load.iter())
        .chain([&blocks.echo])
    {
        block.emit(&mut emitter)?;
    }
    emitter
        .pad_to_entry(usize::try_from(TERMINAL).map_err(|_error| LAYOUT)?, 0)?;
    let _: u32 = emitter.append(LinearOpcode::RotateData)?;
    let output = emitter.append(LinearOpcode::OutputByte)?;
    let halt = emitter.append(LinearOpcode::Halt)?;
    let [first, second, third] = &blocks.capture.reset;
    let [load_first, load_second] = &blocks.load;
    Ok(RelocatedRecurrentReloadSource {
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
        load: [load_first.operation_site()?, load_second.operation_site()?],
        raw: RAW,
    })
}
