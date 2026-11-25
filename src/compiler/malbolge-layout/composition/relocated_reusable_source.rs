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
//   - A source-loaded repeating physical input/crazy/output sequence.
// - Must-Not:
//   - Claim EOF termination, checksum semantics or source-frame admission.
// - Allows:
//   - Inputs: exact current N15 profile.
//   - Outputs: graphical source and proposed physical instruction sites.
//   - Side effects: none; normative VM replay owns acceptance.
// - Split-When:
//   - A general recurrent instruction allocator replaces the fixed tape.
// - Merge-When:
//   - Complete checksum lowering owns reusable instruction scheduling.
// - Summary:
//   - Reprime two-cycle instruction cells by actual indirect transfers.

#[path = "relocated_recurrent_access.rs"]
mod relocated_recurrent_access;
#[path = "relocated_recurrent_capture_source.rs"]
mod relocated_recurrent_capture_source;
#[path = "relocated_reusable_guard_source.rs"]
mod relocated_reusable_guard_source;

use malbolge::{ProfileDescriptor, encrypt_profile_cell};
pub use relocated_recurrent_capture_source::{
    RelocatedRecurrentCaptureSource, RelocatedRecurrentReloadSource,
    build_relocated_recurrent_capture_source,
    build_relocated_recurrent_reload_source,
};
pub use relocated_reusable_guard_source::{
    RelocatedReusableGuardSource, build_relocated_reusable_guard_source,
};

use super::super::LinearOpcode;
use super::relocated_eof_parity_source::composed_prefix;
use super::{BuildError, Emitter, LAYOUT, TapeBounds, TapePlan};

const BOUNDS: TapeBounds = TapeBounds {
    limit: 7_179_001,
    start: 7_175_001,
};
const ONES: u32 = 7_174_601;
const ZERO: u32 = 7_174_603;
const TWOS: u32 = 7_174_605;
const PRIME: u32 = 7_174_671;
const ROUTE: u32 = 7_174_700;
const STATE: u32 = 7_174_705;
const CONTINUATION: u32 = 140_000;
const INPUT: u32 = 150_071;
const CRAZY: u32 = 151_050;
const OUTPUT: u32 = 152_027;
const RELOCATE: u32 = 153_002;
const SOURCE_CELLS: usize = 154_128;
const ALL_TWOS: u32 = 14_348_906;

/// A recurrent physical input, dirty crazy store, output and data reset.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct RelocatedReusableSource {
    /// Physical crazy operation, reused on one mutable data word.
    pub crazy: u32,
    /// Physical input instruction.
    pub input: u32,
    /// Physical output instruction.
    pub output: u32,
    /// Physical data-pointer relocation.
    pub relocate: u32,
    /// First physical route word.
    pub route: u32,
    /// Complete graphical source including its loader seed.
    pub source: Vec<u8>,
    /// Mutable data word, initially zero.
    pub state: u32,
}

fn after_store(emitter: &mut Emitter<'_>) -> Result<(), BuildError> {
    // Targets are initialized in ascending order. The next even loader
    // word is still a virgin frame-reset pointer.
    if !emitter.data.is_multiple_of(2) {
        emitter.walk(emitter.data.checked_add(1).ok_or(LAYOUT)?)?;
    }
    Ok(())
}

fn reset_word(
    emitter: &mut Emitter<'_>,
    address: u32,
) -> Result<(), BuildError> {
    for constant in [ONES, TWOS, ZERO] {
        emitter.go(constant)?;
        let _: u32 = emitter.linear(LinearOpcode::RotateData)?;
        emitter.go(address)?;
        let _: u32 = emitter.linear(LinearOpcode::CrazyData)?;
        after_store(emitter)?;
    }
    Ok(())
}

fn emit_pair(
    emitter: &mut Emitter<'_>,
    address: u32,
    opcode: LinearOpcode,
) -> Result<(), BuildError> {
    let entry = usize::try_from(address).map_err(|_error| LAYOUT)?;
    emitter.pad_to_entry(entry, 0)?;
    let _: u32 = emitter.append(opcode)?;
    // All four active instructions must have the exact F/J encryption
    // cycle. An indirect jump encrypts its target, not the fetched i.
    if emitter.source.last() != Some(&b'F')
        || encrypt_profile_cell(u32::from(b'F')) != Some(u32::from(b'J'))
        || encrypt_profile_cell(u32::from(b'J')) != Some(u32::from(b'F'))
    {
        return Err(LAYOUT);
    }
    let _: u32 = emitter.append_indirect()?;
    Ok(())
}

fn route_words() -> Result<[u32; 12], BuildError> {
    Ok([
        INPUT,
        INPUT.checked_sub(1).ok_or(LAYOUT)?,
        0,
        CRAZY,
        CRAZY.checked_sub(1).ok_or(LAYOUT)?,
        0,
        OUTPUT,
        OUTPUT.checked_sub(1).ok_or(LAYOUT)?,
        0,
        RELOCATE,
        RELOCATE.checked_sub(1).ok_or(LAYOUT)?,
        ROUTE.checked_sub(1).ok_or(LAYOUT)?,
    ])
}

fn initialize_words(
    emitter: &mut Emitter<'_>,
    words: &[(u32, u32)],
) -> Result<(), BuildError> {
    let mut plan = TapePlan::with_bounds(emitter.tape_bounds);
    let twos = plan.tape(ALL_TWOS, false)?;
    let mut destinations = Vec::new();
    let mut prior = TWOS;
    for &(address, value) in words {
        if address <= prior || address >= emitter.tape_bounds.start {
            return Err(LAYOUT);
        }
        prior = address;
        destinations.push((address, plan.tape(value, false)?));
    }
    emitter.prepare_odd_pairs(&[ONES, TWOS])?;
    emitter.prepare_tape(&plan)?;
    let _: u32 = emitter.store_tape(&twos, TWOS, ZERO)?;
    for (address, tape) in destinations {
        reset_word(emitter, address)?;
        let _: u32 = emitter.store_tape(&tape, address, ZERO)?;
        after_store(emitter)?;
    }
    Ok(())
}

fn append_words(
    destinations: &mut Vec<(u32, u32)>,
    start: u32,
    values: &[u32],
) -> Result<(), BuildError> {
    for (offset, value) in values.iter().copied().enumerate() {
        let address = start
            .checked_add(u32::try_from(offset).map_err(|_error| LAYOUT)?)
            .ok_or(LAYOUT)?;
        destinations.push((address, value));
    }
    Ok(())
}

fn initialize(emitter: &mut Emitter<'_>) -> Result<(), BuildError> {
    let mut destinations = Vec::new();
    append_words(&mut destinations, PRIME, &[
        CRAZY,
        OUTPUT,
        RELOCATE,
        CONTINUATION.checked_sub(1).ok_or(LAYOUT)?,
    ])?;
    append_words(&mut destinations, ROUTE, &route_words()?)?;
    initialize_words(emitter, &destinations)
}

/// Emit a source-loaded loop that physically reuses four instructions.
///
/// Each input is combined with the previous state by crazy and emitted;
/// EOF is deliberately another raw input word, not a termination guard.
///
/// # Errors
/// Refuses unsupported profiles and changed bounded code/tape geometry.
pub fn build_relocated_reusable_source(
    profile: &ProfileDescriptor,
) -> Result<RelocatedReusableSource, BuildError> {
    let prefix = composed_prefix(profile)?;
    let mut emitter = Emitter {
        data: 7_174_418,
        profile,
        source: prefix.source,
        source_cells: SOURCE_CELLS,
        tape_bounds: BOUNDS,
    };
    initialize(&mut emitter)?;
    emitter.go(PRIME)?;
    let _: u32 = emitter.append_indirect()?;
    emitter.pad_to_entry(
        usize::try_from(CONTINUATION).map_err(|_error| LAYOUT)?,
        PRIME.checked_add(4).ok_or(LAYOUT)?,
    )?;
    emitter.go(ROUTE.checked_add(1).ok_or(LAYOUT)?)?;
    let _: u32 = emitter.append_indirect()?;
    for (address, opcode) in [
        (INPUT, LinearOpcode::InputWord),
        (CRAZY, LinearOpcode::CrazyData),
        (OUTPUT, LinearOpcode::OutputByte),
        (RELOCATE, LinearOpcode::RelocateDataPointer),
    ] {
        emit_pair(&mut emitter, address, opcode)?;
    }
    Ok(RelocatedReusableSource {
        crazy: CRAZY,
        input: INPUT,
        output: OUTPUT,
        relocate: RELOCATE,
        route: ROUTE,
        source: emitter.finish()?,
        state: STATE,
    })
}
