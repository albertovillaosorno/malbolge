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
//   - Recurrent physical two-bit checksum state and EOF output.
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
//   - Select a two-bit checksum transition by live state and raw input.

use malbolge::{ProfileDescriptor, profile_crazy};

use super::super::super::super::LinearOpcode;
use super::super::super::{BuildError, Emitter, LAYOUT, TapeBounds};
use super::super::relocated_recurrent_access::AccessBlock;
use super::relocated_recurrent_reload_source::{anchors, main_route, reset};
use super::{
    ALL_ONES, ALL_TWOS, BYTE, BYTE_ROUTE_POINTER, Blocks, CAPTURE, CONSTANTS,
    EOF, INITIAL, MAIN_ROUTE, RelocatedRecurrentCaptureSource, Route, STATES,
    Words, access, bootstrap, code, go_anchored, initialize, insert, previous,
};

const BOUNDS: TapeBounds = TapeBounds {
    limit: 7_280_001,
    start: 7_190_001,
};
const CODE_BASE: u32 = 4_260_000;
const TERMINAL: u32 = 4_270_000;
const SOURCE_CELLS: usize = 4_270_106;
const BYTE_ROUTE: u32 = 7_182_200;
const STATE: u32 = 7_175_100;
const STATE_CONSTANTS: [u32; 3] = [7_175_060, 7_175_062, 7_175_064];
const SCRATCH: u32 = 7_175_120;
const SCRATCH_CONSTANTS: [u32; 3] = [7_175_070, 7_175_072, 7_175_074];
const LOAD_CONSTANT: u32 = 7_175_050;
const LOOKUP_CONSTANT: u32 = 7_175_052;
const RELOAD_CONSTANTS: [u32; 2] = [7_175_054, 7_175_056];
const LOOP_RETURN: u32 = 7_175_090;
// The state occupies the high trits and each input occupies six low trits.
// Rotating the column-two inverse six times on EOF emits the state: the
// fixed high prefix plus the wrapped low six twos is divisible by 256.
const TABLE_BASE: u32 = 7_179_192;
const ROW: u32 = 729;
const SEED_BASE: u32 = 7_189_500;
const SEED_STRIDE: u32 = 8;

/// Recurrent physical low-two-bit projection of the mutable checksum.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct RelocatedRecurrentMod4Source {
    /// Actual capture, dispatch, reset and terminal sites.
    pub capture: RelocatedRecurrentCaptureSource,
    /// Two recurrent load stores, with distinct continuation offsets.
    pub load: [u32; 2],
    /// Physical first and restoring indexed seed stores.
    pub lookup: [u32; 2],
    /// Physical scratch word preserving the next mask during reset.
    pub scratch: u32,
    /// Physical rotation of the selected record's all-two constant.
    pub seed_rotate: u32,
    /// Persistent encoded checksum state, also the dynamic index.
    pub state: u32,
    /// First instruction of the actual EOF decode/output sequence.
    pub terminal: u32,
}

type TerminalSites = (u32, u32);

struct Mod4Blocks {
    capture: Blocks,
    load: [AccessBlock; 2],
    lookup: [AccessBlock; 2],
}

impl Mod4Blocks {
    fn new(profile: &ProfileDescriptor) -> Result<Self, BuildError> {
        use LinearOpcode::CrazyData;
        Ok(Self {
            capture: Blocks::new(profile, CODE_BASE)?,
            load: [
                access(profile, (CODE_BASE, 8, 93), CrazyData, (0, 4, true))?,
                access(profile, (CODE_BASE, 9, 93), CrazyData, (0, 5, true))?,
            ],
            lookup: AccessBlock::indexed_load(profile, [
                code(CODE_BASE, 11, 0)?,
                code(CODE_BASE, 12, 0)?,
            ])?,
        })
    }
}

fn mask(profile: &ProfileDescriptor, state: u32) -> Result<u32, BuildError> {
    let base = TABLE_BASE
        .checked_add(ROW.checked_mul(state).ok_or(LAYOUT)?)
        .ok_or(LAYOUT)?;
    profile_crazy(base, ALL_TWOS, profile.word_trits())
        .checked_add(364)
        .ok_or(LAYOUT)
}

fn next_state(state: u32, byte: u32) -> Result<u32, BuildError> {
    let update = if byte.is_multiple_of(2) {
        state.checked_add(byte).ok_or(LAYOUT)?
    } else {
        state ^ byte
    };
    Ok(update.checked_add(3).ok_or(LAYOUT)? & 3)
}

fn data_words(profile: &ProfileDescriptor) -> Result<Words, BuildError> {
    let mut words = Words::new();
    for (address, value) in [
        (CAPTURE, ALL_ONES),
        (STATE, mask(profile, 0)?),
        (STATE.checked_add(1).ok_or(LAYOUT)?, previous(STATE)?),
        (SCRATCH, ALL_ONES),
        (LOAD_CONSTANT, ALL_TWOS),
        (LOOKUP_CONSTANT, ALL_TWOS),
        (BYTE_ROUTE_POINTER, previous(BYTE_ROUTE)?),
        (LOOP_RETURN, previous(MAIN_ROUTE)?),
    ] {
        insert(&mut words, address, value)?;
    }
    for (address, value) in STATES.into_iter().zip(INITIAL) {
        insert(&mut words, address, value)?;
    }
    for address in RELOAD_CONSTANTS {
        insert(&mut words, address, ALL_TWOS)?;
    }
    for constants in [CONSTANTS, STATE_CONSTANTS, SCRATCH_CONSTANTS] {
        for (address, value) in
            constants.into_iter().zip([ALL_ONES, ALL_TWOS, 0])
        {
            insert(&mut words, address, value)?;
        }
    }
    for landing in EOF {
        for (offset, value) in [
            (1, previous(TERMINAL)?),
            (2, ALL_TWOS),
            (3, previous(STATE)?),
        ] {
            insert(
                &mut words,
                landing.checked_add(offset).ok_or(LAYOUT)?,
                value,
            )?;
        }
    }
    Ok(words)
}

fn seed_address(state: u32) -> Result<u32, BuildError> {
    SEED_BASE
        .checked_add(state.checked_mul(SEED_STRIDE).ok_or(LAYOUT)?)
        .ok_or(LAYOUT)
}

fn table_records(
    profile: &ProfileDescriptor,
    route: &mut Route<'_>,
    blocks: &Mod4Blocks,
) -> Result<(), BuildError> {
    let [first, second] = &blocks.lookup;
    route.enter_ready(first, STATE)?;
    let continuation = previous(route.cursor)?;
    for state in 0..4u32 {
        let seed = seed_address(state)?;
        for (offset, value) in [
            (0, mask(profile, state)?),
            (1, previous(seed.checked_add(4).ok_or(LAYOUT)?)?),
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
        let end = TABLE_BASE
            .checked_add(
                ROW.checked_mul(state.checked_add(1).ok_or(LAYOUT)?)
                    .ok_or(LAYOUT)?,
            )
            .ok_or(LAYOUT)?;
        for byte in 0..=255u32 {
            let address = end.checked_sub(byte).ok_or(LAYOUT)?;
            insert(
                route.words,
                address,
                previous(seed_address(next_state(state, byte)?)?)?,
            )?;
        }
    }
    route.prepare(first, false)?;
    route.prepare(second, false)?;
    Ok(())
}

fn byte_route(
    profile: &ProfileDescriptor,
    blocks: &Mod4Blocks,
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
    let [load_first, load_second] = &blocks.load;
    let mut route = Route {
        cursor: BYTE_ROUTE,
        words,
    };
    route.prepare(&blocks.capture.branch, false)?;
    route.call_ready(&blocks.capture.rotate, LOAD_CONSTANT)?;
    route.call_ready(load_first, CAPTURE)?;
    route.call_ready(load_first, STATE)?;
    route.call_ready(&blocks.capture.rotate, LOOKUP_CONSTANT)?;
    table_records(profile, &mut route, blocks)?;
    // Save the inverse of the chosen mask before clearing the dirty index.
    route.call_ready(&blocks.capture.crazy, SCRATCH)?;
    reset(&mut route, &blocks.capture, STATE, STATE_CONSTANTS)?;
    reset(&mut route, &blocks.capture, CAPTURE, CONSTANTS)?;
    for (address, block) in RELOAD_CONSTANTS.into_iter().zip(&blocks.load) {
        route.call_ready(&blocks.capture.rotate, address)?;
        route.call_ready(block, SCRATCH)?;
    }
    route.call_ready(load_second, STATE)?;
    reset(&mut route, &blocks.capture, SCRATCH, SCRATCH_CONSTANTS)?;
    route.enter_ready(&blocks.capture.branch, LOOP_RETURN)?;
    if route.cursor >= SEED_BASE {
        return Err(LAYOUT);
    }
    Ok(())
}

fn emit_terminal(
    emitter: &mut Emitter<'_>,
) -> Result<TerminalSites, BuildError> {
    use LinearOpcode::{
        CrazyData, Halt, OutputByte, RelocateDataPointer, RotateData,
    };
    emitter
        .pad_to_entry(usize::try_from(TERMINAL).map_err(|_error| LAYOUT)?, 0)?;
    let _: u32 = emitter.append(RotateData)?;
    let _: u32 = emitter.append(RelocateDataPointer)?;
    let _: u32 = emitter.append(CrazyData)?;
    for _ in 0..6u32 {
        let _: u32 = emitter.append(RelocateDataPointer)?;
        let _: u32 = emitter.append(RotateData)?;
    }
    let output = emitter.append(OutputByte)?;
    let halt = emitter.append(Halt)?;
    Ok((output, halt))
}

/// Execute the low two bits of the original mutable checksum until EOF.
///
/// The finite transition table selects a new persistent state mask from
/// both the actual input and the previous state. The byte path emits nothing.
///
/// # Errors
/// Refuses unsupported profiles, unsafe restoration or exhausted geometry.
pub fn build_relocated_recurrent_mod4_source(
    profile: &ProfileDescriptor,
) -> Result<RelocatedRecurrentMod4Source, BuildError> {
    let mut emitter = bootstrap(profile, SOURCE_CELLS, BOUNDS)?;
    let blocks = Mod4Blocks::new(profile)?;
    let mut words = data_words(profile)?;
    let entry = main_route(&blocks.capture, &mut words)?;
    byte_route(profile, &blocks, &mut words)?;
    let anchors = anchors(&words)?;
    initialize(&mut emitter, &words, &anchors, 2)?;
    go_anchored(&mut emitter, entry, &anchors)?;
    let _: u32 = emitter.append_indirect()?;
    for block in blocks
        .capture
        .ordered()
        .into_iter()
        .chain(&blocks.load)
        .chain(&blocks.lookup)
    {
        block.emit(&mut emitter)?;
    }
    let (output, halt) = emit_terminal(&mut emitter)?;
    let [first, second, third] = &blocks.capture.reset;
    let [load_first, load_second] = &blocks.load;
    let [lookup_first, lookup_second] = &blocks.lookup;
    Ok(RelocatedRecurrentMod4Source {
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
        lookup: [
            lookup_first.start.checked_add(3).ok_or(LAYOUT)?,
            lookup_second.start.checked_add(2).ok_or(LAYOUT)?,
        ],
        scratch: SCRATCH,
        seed_rotate: lookup_second.start,
        state: STATE,
        terminal: TERMINAL,
    })
}
