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
//   - First-iteration physical byte addition and EOF return.
// - Must-Not:
//   - Claim general checksum arithmetic, source-frame admission or a loop.
// - Allows:
//   - Inputs: exact current N15 profile.
//   - Outputs: graphical source and proposed physical effect sites.
//   - Side effects: none; normative replay owns acceptance.
// - Split-When:
//   - General physical continuation allocation replaces fixed addresses.
// - Merge-When:
//   - Complete checksum lowering owns both continuations.
// - Summary:
//   - Emit a bounded ternary carry circuit for the first byte.

use malbolge::ProfileDescriptor;

use super::super::LinearOpcode::{
    CrazyData, Halt, NoOperation, OutputByte, RelocateDataPointer, RotateData,
};
use super::relocated_eof_parity_source::composed_prefix;
use super::relocated_live_parity_source::{
    NORMALIZER, ONES, PARITY, POINTER, ParityTapes, emit_parity_lookup,
    emit_parity_result,
};
use super::{
    BuildError, Emitter, FRAME, LAYOUT, TapeBounds, TapePlan, encode_i32_cells,
};

const BOUNDS: TapeBounds = TapeBounds {
    limit: 7_177_673,
    start: 7_174_601,
};
const ZERO: u32 = 7_174_603;
const SCRATCH: u32 = 7_177_001;
const TWOS: u32 = 7_174_489;
const THREE: u32 = 7_174_493;
const ANCHOR: u32 = 7_174_497;
const MERGED: u32 = 7_174_527;
const JOIN: u32 = 7_174_515;
const COUNT: u32 = 168;

// Postfix circuits: left/right/0/2 load operands, s saves A, p combines.
// Each digit computes sum modulo three or carry independently.
const SUM: &[u8] = b"xsxs2ppsysxppsxsyps2pp";
const CARRY: &[u8] = b"0s0sxpsysxs0pppp";

/// Bounded first-iteration image, not a complete checksum loop.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct RelocatedFirstByteAddSource {
    /// Actual even/odd merged-result stores.
    pub arm_store_code_addresses: [u32; 2],
    /// Byte halt.
    pub byte_halt_code_address: u32,
    /// True EOF halt.
    pub eof_halt_code_address: u32,
    /// Adjacent input words.
    pub input_pair: [u32; 2],
    /// Merged first-iteration value.
    pub merged_address: u32,
    /// Actual parity branch.
    pub parity_branch_code_address: u32,
    /// Graphical source.
    pub source: Vec<u8>,
    /// Unmasked addition result.
    pub sum_address: u32,
    /// Initial checksum words.
    pub zero_pair: [u32; 2],
}

struct Adder<'emitter, 'profile> {
    cursor: u32,
    emitter: &'emitter mut Emitter<'profile>,
}

impl Adder<'_, '_> {
    fn copy(&mut self) -> Result<u32, BuildError> {
        let mut address = SCRATCH;
        for _ in 0u32..2 {
            if self.cursor >= COUNT {
                return Err(LAYOUT);
            }
            address = scratch_address(self.cursor)?;
            self.cursor = self.cursor.checked_add(1).ok_or(LAYOUT)?;
            self.go(address)?;
            let _: u32 = self.emitter.linear(CrazyData)?;
        }
        Ok(address)
    }

    fn evaluate(
        &mut self,
        circuit: &[u8],
        left: u32,
        right: u32,
    ) -> Result<(), BuildError> {
        let mut stack = Vec::new();
        for op in circuit {
            match op {
                b'x' => self.load(left)?,
                b'y' => self.load(right)?,
                b'0' => self.load(ZERO)?,
                b'2' => self.load(TWOS)?,
                b's' => stack.push(self.copy()?),
                b'p' => {
                    self.go(stack.pop().ok_or(LAYOUT)?)?;
                    let _: u32 = self.emitter.linear(CrazyData)?;
                },
                _ => return Err(LAYOUT),
            }
        }
        if !stack.is_empty() {
            return Err(LAYOUT);
        }
        Ok(())
    }

    fn go(&mut self, target: u32) -> Result<(), BuildError> {
        let emitter = &mut *self.emitter;
        if emitter.data > target {
            emitter.reset()?;
        }
        if emitter.data < SCRATCH && target >= SCRATCH {
            if emitter.data > ANCHOR {
                emitter.reset()?;
            }
            emitter.walk(ANCHOR)?;
            emitter.jump(SCRATCH)?;
        }
        emitter.walk(target)
    }

    fn load(&mut self, address: u32) -> Result<(), BuildError> {
        if [ZERO, ONES, TWOS].contains(&address) {
            self.go(address)?;
            let _: u32 = self.emitter.linear(RotateData)?;
        } else {
            // Two involutive folds with all twos preserve the operand.
            for _ in 0u32..2 {
                self.go(TWOS)?;
                let _: u32 = self.emitter.linear(RotateData)?;
                self.go(address)?;
                let _: u32 = self.emitter.linear(CrazyData)?;
            }
        }
        Ok(())
    }

    fn run(&mut self) -> Result<u32, BuildError> {
        self.load(ZERO)?;
        for slot in 0..COUNT {
            let address = scratch_address(slot)?;
            self.go(address)?;
            let _: u32 = self.emitter.linear(CrazyData)?;
            self.emitter.walk(address.checked_add(2).ok_or(LAYOUT)?)?;
            let _: u32 = self.emitter.linear(CrazyData)?;
        }
        let (mut left, mut right) = (MERGED, THREE);
        // Six rounds suffice for byte + 3; carry never leaves the low six
        // trits.
        for _ in 0u32..6 {
            self.evaluate(SUM, left, right)?;
            let sum = self.copy()?;
            self.evaluate(CARRY, left, right)?;
            let carry = self.copy()?;
            for _ in 0u32..14 {
                self.go(carry)?;
                let _: u32 = self.emitter.linear(RotateData)?;
            }
            (left, right) = (sum, carry);
        }
        if self.cursor != COUNT {
            return Err(LAYOUT);
        }
        self.load(left)?;
        Ok(left)
    }
}

fn scratch_address(slot: u32) -> Result<u32, BuildError> {
    slot.checked_mul(4)
        .and_then(|offset| SCRATCH.checked_add(offset))
        .ok_or(LAYOUT)
}

fn arm(
    emitter: &mut Emitter<'_>,
    raw: u32,
    result: u32,
) -> Result<u32, BuildError> {
    for _ in 0u32..2 {
        emitter.go(TWOS)?;
        let _: u32 = emitter.linear(RotateData)?;
        // M7174490 is a scratch pointer, not the virgin reset word.
        emitter.walk(7_174_492)?;
        emitter.jump(FRAME)?;
        emitter.walk(raw)?;
        let _: u32 = emitter.linear(CrazyData)?;
    }
    emitter.go(result)?;
    let _: u32 = emitter.linear(CrazyData)?;
    emitter.go(MERGED)?;
    let site = emitter.linear(CrazyData)?;
    emitter.go(JOIN)?;
    let _: u32 = emitter.append_indirect()?;
    Ok(site)
}

/// Emit first-byte XOR/add identity arms from the zero checksum, then add
/// three using a ternary carry circuit.
///
/// Output truncates to a byte; no
/// canonical masked source word or second iteration is established.
///
/// # Errors
/// Refuses unsupported profiles and exhausted physical layouts.
#[expect(
    clippy::too_many_lines,
    reason = "auditable physical sequence"
)]
pub fn build_relocated_first_byte_add_source(
    profile: &ProfileDescriptor,
) -> Result<RelocatedFirstByteAddSource, BuildError> {
    let prefix = composed_prefix(profile)?;
    let [raw, high] = prefix.input_pair;
    let mut emitter = Emitter {
        data: 7_174_418,
        profile,
        source: prefix.source,
        source_cells: 355_194,
        tape_bounds: BOUNDS,
    };
    let mut plan = TapePlan::with_bounds(BOUNDS);
    let byte = plan.tape(49_999, false)?;
    let eof = plan.tape(349_999, false)?;
    let parity = ParityTapes::allocate(&mut plan)?;
    let constants = [14_348_906, 3, 7_177_000, 79_999, 81_999, 84_999]
        .into_iter()
        .map(|value| plan.tape(value, false))
        .collect::<Result<Vec<_>, _>>()?;
    let [lo, hi] = encode_i32_cells(u32::MAX);
    let eof_low = plan.tape(lo, false)?;
    let eof_high = plan.tape(hi, false)?;
    emitter.prepare_odd_pairs(&[
        POINTER, NORMALIZER, PARITY, ONES, 7_174_485, TWOS, THREE, ANCHOR,
        7_174_501, 7_174_511, JOIN, 7_174_519, 7_174_523, MERGED, 7_174_535,
    ])?;
    emitter.prepare_tape(&plan)?;
    let _: u32 = emitter.store_tape(&byte, 7_174_485, ZERO)?;
    let _: u32 = emitter.store_tape(&eof, 7_174_535, ZERO)?;
    emitter.go(7_174_423)?;
    let _: u32 = emitter.append(RelocateDataPointer)?;
    let _: u32 = emitter.append(RelocateDataPointer)?;
    emitter.append_route(b"ooooojoojooooojooj")?;
    for _ in 0u32..68 {
        let _: u32 = emitter.append(NoOperation)?;
    }
    let _: u32 = emitter.append_indirect()?;
    emitter.pad_to_entry(50_000, 7_174_486)?;
    parity.store(&mut emitter, ZERO)?;
    for (tape, address) in constants
        .iter()
        .zip([TWOS, THREE, ANCHOR, 7_174_501, 7_174_511, JOIN])
    {
        let _: u32 = emitter.store_tape(tape, address, ZERO)?;
    }
    let _lookup = emit_parity_lookup(&mut emitter, raw)?;
    emitter.append_route(b"ojojoojjjjoojoj")?;
    let _: u32 = emit_parity_result(&mut emitter)?;
    emitter.jump(FRAME)?;
    emitter.walk(PARITY)?;
    let _: u32 = emitter.append(RelocateDataPointer)?;
    emitter.append_route(b"oooojojojoooooooooooooooooooooooj")?;
    emitter.append_route(b"oooooooooooooooooooooooooooooooooooooooooooo")?;
    let parity_branch_code_address = emitter.append_indirect()?;
    emitter.pad_to_entry(80_000, 7_174_502)?;
    let even = arm(&mut emitter, raw, 7_174_519)?;
    emitter.pad_to_entry(82_000, 7_174_512)?;
    let odd = arm(&mut emitter, raw, 7_174_523)?;
    emitter.pad_to_entry(85_000, 7_174_516)?;
    let sum_address = Adder {
        cursor: 0,
        emitter: &mut emitter,
    }
    .run()?;
    let _: u32 = emitter.linear(OutputByte)?;
    let byte_halt_code_address = emitter.append(Halt)?;
    emitter.pad_to_entry(350_000, 7_174_536)?;
    emitter.prepare_pair()?;
    let _: u32 = emitter.store_tape(&eof_low, raw, ZERO)?;
    let _: u32 = emitter.store_tape(&eof_high, high, ZERO)?;
    emitter.go(ZERO)?;
    let _: u32 = emitter.linear(RotateData)?;
    emitter.reset()?;
    emitter.walk(7_174_454)?;
    let _: u32 = emitter.linear(CrazyData)?;
    let _: u32 = emitter.linear(CrazyData)?;
    let _: u32 = emitter.linear(OutputByte)?;
    let eof_halt_code_address = emitter.append(Halt)?;
    Ok(RelocatedFirstByteAddSource {
        arm_store_code_addresses: [even, odd],
        byte_halt_code_address,
        eof_halt_code_address,
        input_pair: prefix.input_pair,
        merged_address: MERGED,
        parity_branch_code_address,
        source: emitter.finish()?,
        sum_address,
        zero_pair: prefix.zero_pair,
    })
}
