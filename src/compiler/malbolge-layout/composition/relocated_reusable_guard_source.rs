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
//   - A source-loaded recurrent byte/EOF classifier and actual branch.
// - Must-Not:
//   - Claim checksum arithmetic or independent source-frame admission.
// - Allows:
//   - Inputs: exact current N15 profile.
//   - Outputs: graphical source and proposed recurrent effect sites.
//   - Side effects: none; normative VM replay owns acceptance.
// - Split-When:
//   - General recurrent instruction and branch allocation replaces the tape.
// - Merge-When:
//   - Complete checksum lowering owns the recurrent guard.
// - Summary:
//   - Use dirty ternary classifier state and a four-phase branch cell.

use malbolge::{
    ProfileDescriptor, decode_profile_instruction, encrypt_profile_cell,
};

use super::super::super::{LinearOpcode, unique_graphical_cell};
use super::super::relocated_eof_parity_source::composed_prefix;
use super::super::{BuildError, Emitter, LAYOUT, TapeBounds};
use super::{append_words, emit_pair, initialize_words};

const BOUNDS: TapeBounds = TapeBounds {
    limit: 7_196_001,
    start: 7_181_001,
};
const PRIME: u32 = 7_174_671;
const ROUTE: u32 = 7_174_700;
const CLASS: u32 = 7_174_718;
const CONTINUATION: u32 = 950_000;
const INPUT: u32 = 1_000_019;
const CRAZY: u32 = 1_010_022;
const BRANCH: u32 = 1_020_014;
const RELOCATE: u32 = 1_030_022;
const TERMINAL: u32 = 1_040_000;
const OUTPUT: u32 = 1_040_001;
const HALT: u32 = 1_040_002;
const SOURCE_CELLS: usize = 1_050_042;

// The five dirty words implement an invariant per-trit state machine.
// All trits except 6 and 7 have input-independent final values; those
// two see zero for every byte and two for EOF. Their combined byte
// output is (1,1); EOF produces (1,0) for odd length and (0,1)
// for even length.
const INITIAL: [u32; 5] = [2_916, 5_832, 14_334_327, 728, 7_180_650];
const BYTE: u32 = 7_180_650;
const EOF: [u32; 2] = [7_178_463, 7_179_921];

/// One recurrent physical EOF guard with an input-free bootstrap.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct RelocatedReusableGuardSource {
    /// The same physical cell performs crazy then data relocation.
    pub branch: u32,
    /// Shared crazy instruction for the first four folds.
    pub crazy: u32,
    /// Actual terminal halt, selected only by recurrent EOF.
    pub halt: u32,
    /// First and subsequent physical recurrent input site.
    pub input: u32,
    /// Actual byte-count parity output.
    pub output: u32,
    /// Physical data-pointer return instruction.
    pub relocate: u32,
    /// Start of the contiguous recurrent route.
    pub route: u32,
    /// Complete graphical source and loader seed.
    pub source: Vec<u8>,
    /// Five initially prepared dirty classifier words.
    pub states: [u32; 5],
    /// Terminal rotation loads the selected parity.
    pub terminal: u32,
}

fn previous(address: u32) -> Result<u32, BuildError> {
    address.checked_sub(1).ok_or(LAYOUT)
}

fn initialize(emitter: &mut Emitter<'_>) -> Result<(), BuildError> {
    let mut words = Vec::new();
    append_words(&mut words, PRIME, &[
        CRAZY,
        BRANCH,
        BRANCH,
        RELOCATE,
        previous(CONTINUATION)?,
    ])?;
    let mut route = vec![0, previous(INPUT)?, 0];
    for value in INITIAL.iter().take(4).copied() {
        route.extend([CRAZY, previous(CRAZY)?, value]);
    }
    let [_, _, _, _, last] = INITIAL;
    route.extend([
        BRANCH,
        BRANCH,
        previous(BRANCH)?,
        last,
        RELOCATE,
        previous(RELOCATE)?,
        CLASS.checked_sub(2).ok_or(LAYOUT)?,
    ]);
    append_words(&mut words, ROUTE, &route)?;
    for (landing, value) in EOF.into_iter().zip([3, 0]) {
        append_words(&mut words, landing.checked_add(1).ok_or(LAYOUT)?, &[
            previous(TERMINAL)?,
            value,
        ])?;
    }
    append_words(&mut words, BYTE.checked_add(1).ok_or(LAYOUT)?, &[
        INPUT,
        RELOCATE,
        previous(RELOCATE)?,
        ROUTE,
    ])?;
    initialize_words(emitter, &words)
}

fn emit_branch(emitter: &mut Emitter<'_>) -> Result<(), BuildError> {
    emitter
        .pad_to_entry(usize::try_from(BRANCH).map_err(|_error| LAYOUT)?, 0)?;
    let _: u32 = emitter.append(LinearOpcode::CrazyData)?;
    if emitter.source.last() != Some(&b'*')
        || decode_profile_instruction(u32::from(b'r'), BRANCH) != Some(b'j')
    {
        return Err(LAYOUT);
    }
    for (before, after) in
        [(b'*', b'r'), (b'r', b'}'), (b'}', b'i'), (b'i', b'*')]
    {
        if encrypt_profile_cell(u32::from(before)) != Some(u32::from(after)) {
            return Err(LAYOUT);
        }
    }
    let _: u32 = emitter.append_indirect()?;
    Ok(())
}

/// Build a source-loaded recurrent guard that emits length parity on actual
/// EOF.
///
/// Five dirty crazy folds select one of two EOF landings or the byte
/// continuation. A four-phase code cell reuses the final fold's very
/// same data operand as the branch pointer. The bootstrap read is
/// replaced by a canonical no-op; all real inputs enter the guard.
///
/// # Errors
/// Refuses unsupported profiles and changed fixed tape geometry.
pub fn build_relocated_reusable_guard_source(
    profile: &ProfileDescriptor,
) -> Result<RelocatedReusableGuardSource, BuildError> {
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
        source_cells: SOURCE_CELLS,
        tape_bounds: BOUNDS,
    };
    initialize(&mut emitter)?;
    emitter.go(PRIME)?;
    let _: u32 = emitter.append_indirect()?;
    emitter.pad_to_entry(
        usize::try_from(CONTINUATION).map_err(|_error| LAYOUT)?,
        PRIME.checked_add(5).ok_or(LAYOUT)?,
    )?;
    emitter.go(ROUTE.checked_add(1).ok_or(LAYOUT)?)?;
    let _: u32 = emitter.append_indirect()?;
    emit_pair(&mut emitter, INPUT, LinearOpcode::InputWord)?;
    emit_pair(&mut emitter, CRAZY, LinearOpcode::CrazyData)?;
    emit_branch(&mut emitter)?;
    emit_pair(&mut emitter, RELOCATE, LinearOpcode::RelocateDataPointer)?;
    emitter
        .pad_to_entry(usize::try_from(TERMINAL).map_err(|_error| LAYOUT)?, 0)?;
    let _: u32 = emitter.append(LinearOpcode::RotateData)?;
    let _: u32 = emitter.append(LinearOpcode::OutputByte)?;
    let _: u32 = emitter.append(LinearOpcode::Halt)?;
    Ok(RelocatedReusableGuardSource {
        branch: BRANCH,
        crazy: CRAZY,
        halt: HALT,
        input: INPUT,
        output: OUTPUT,
        relocate: RELOCATE,
        route: ROUTE,
        source: emitter.finish()?,
        states: [7_174_705, 7_174_708, 7_174_711, 7_174_714, CLASS],
        terminal: TERMINAL,
    })
}
