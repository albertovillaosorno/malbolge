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
//   - A guarded physical byte-parity candidate and its proposed sites.
// - Must-Not:
//   - Admit source-frame effects or claim a linked checksum iteration.
// - Allows:
//   - Inputs: exact current N15 profile.
//   - Outputs: graphical source; normative replay must verify it.
//   - Side effects: none.
// - Split-When:
//   - General data-dependent loader addressing replaces this probe.
// - Merge-When:
//   - Physical source-C parity lowering owns the complete computation.
// - Summary:
//   - Compute byte parity through two virgin-loader word classes.

//! Guarded live byte parity, separate from the signed EOF candidate.

use malbolge::ProfileDescriptor;

use super::super::{LinearOpcode, unique_graphical_cell};
use super::{
    BOOT_RETURN, BuildError, Emitter, LAYOUT, TAPE_ZERO, TapePlan,
    extended_prefix,
};

const POINTER: u32 = 7_174_469;
const NORMALIZER: u32 = 7_174_473;
const PARITY: u32 = 7_174_477;
const ONES: u32 = 7_174_481;
const SOURCE_CELLS: usize = 5_796;

/// Physical guarded parity probe; addresses remain untrusted proposals.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct RelocatedLiveParitySource {
    /// Common indirect guard transfer.
    pub branch_code_address: u32,
    /// Successful input entry.
    pub byte_arm_code_address: u32,
    /// Successful input halt.
    pub byte_halt_code_address: u32,
    /// EOF-only halt, without output or normalization.
    pub eof_halt_code_address: u32,
    /// First input site.
    pub first_input_code_address: u32,
    /// Adjacent raw input words, preserved by the parity computation.
    pub input_pair: [u32; 2],
    /// Rotate of the selected virgin loader word.
    pub lookup_code_address: u32,
    /// Output of the computed parity bit.
    pub output_code_address: u32,
    /// Scratch result word, not a source SSA destination.
    pub parity_address: u32,
    /// Final Boolean write.
    pub parity_store_code_address: u32,
    /// Scratch pointer word.
    pub pointer_address: u32,
    /// Data transfer to the selected loader word.
    pub pointer_jump_code_address: u32,
    /// Write of 3^15 - 3^6 + byte.
    pub pointer_store_code_address: u32,
    /// Graphical source including loader seed.
    pub source: Vec<u8>,
}

/// Emit a finite guarded byte parity candidate.
///
/// The byte arm constructs three masks from marker tapes and preserves the
/// saved raw byte through a complete rotation cycle. A crazy operation
/// selects one of two alternating virgin loader word classes. A read-only
/// data route reconverges, and two masks reduce the rotated word to 0 or 1.
/// True EOF halts before the tape. This is not the signed EOF candidate.
///
/// # Errors
/// Refuses unsupported profiles and impossible bounded tape geometry.
#[expect(
    clippy::too_many_lines,
    reason = "keep the exact physical emission sequence auditable"
)]
pub fn build_relocated_live_parity_source(
    profile: &ProfileDescriptor,
) -> Result<RelocatedLiveParitySource, BuildError> {
    use LinearOpcode::{
        CrazyData, Halt, NoOperation, OutputByte, RelocateDataPointer,
        RotateData,
    };
    let mut prefix = extended_prefix(profile)?;
    for (position, opcode) in
        [(108, NoOperation), (110, NoOperation), (120, Halt)]
    {
        let byte = unique_graphical_cell(profile, opcode, position)
            .map_err(|_error| LAYOUT)?;
        *prefix.source.get_mut(position).ok_or(LAYOUT)? = byte;
    }
    let mut emitter = Emitter {
        data: 7_174_418,
        profile,
        source: prefix.source,
        source_cells: SOURCE_CELLS,
    };
    let mut tape = TapePlan::new();
    let pointer = tape.tape(14_348_542, false)?;
    let normalizer = tape.tape(14_348_905, false)?;
    let parity = tape.tape(1, true)?;
    for address in [POINTER, NORMALIZER, PARITY, ONES] {
        emitter.walk(address)?;
        let _: u32 = emitter.linear(CrazyData)?;
        emitter.walk(address.checked_add(2).ok_or(LAYOUT)?)?;
        let _: u32 = emitter.linear(CrazyData)?;
    }
    emitter.prepare_tape(&tape)?;
    let _: u32 = emitter.store_tape(&pointer, POINTER, TAPE_ZERO)?;
    let _: u32 = emitter.store_tape(&normalizer, NORMALIZER, TAPE_ZERO)?;
    let _: u32 = emitter.store_tape(&parity, PARITY, ONES)?;
    let [raw, _high] = prefix.input_pair;
    for _ in 0u32..15 {
        emitter.go(raw)?;
        let _: u32 = emitter.linear(RotateData)?;
    }
    emitter.go(ONES)?;
    let _: u32 = emitter.linear(CrazyData)?;
    emitter.go(POINTER)?;
    let pointer_store_code_address = emitter.linear(CrazyData)?;
    emitter.go(POINTER)?;
    let pointer_jump_code_address = emitter.append(RelocateDataPointer)?;
    let lookup_code_address = emitter.append(RotateData)?;
    let _: u32 = emitter.append(RelocateDataPointer)?;
    // The two data paths must independently reach BOOT_RETURN. Neither
    // route reads the raw input, pointer scratch, or input-dependent mask.
    for opcode in [
        RelocateDataPointer,
        RelocateDataPointer,
        NoOperation,
        RelocateDataPointer,
        RelocateDataPointer,
        NoOperation,
        NoOperation,
        RelocateDataPointer,
        RelocateDataPointer,
        NoOperation,
        RelocateDataPointer,
        NoOperation,
        NoOperation,
        RelocateDataPointer,
    ] {
        let _: u32 = emitter.append(opcode)?;
    }
    emitter.data = BOOT_RETURN;
    emitter.go(NORMALIZER)?;
    let _: u32 = emitter.linear(CrazyData)?;
    emitter.go(PARITY)?;
    let parity_store_code_address = emitter.linear(CrazyData)?;
    let output_code_address = emitter.linear(OutputByte)?;
    let byte_halt_code_address = emitter.append(Halt)?;
    Ok(RelocatedLiveParitySource {
        branch_code_address: prefix.branch_code_address,
        byte_arm_code_address: 126,
        byte_halt_code_address,
        eof_halt_code_address: 120,
        first_input_code_address: prefix.first_input_code_address,
        input_pair: prefix.input_pair,
        lookup_code_address,
        output_code_address,
        parity_address: PARITY,
        parity_store_code_address,
        pointer_address: POINTER,
        pointer_jump_code_address,
        pointer_store_code_address,
        source: emitter.finish()?,
    })
}
