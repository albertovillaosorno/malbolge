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
//   - Finite recurrent route-tape and record-continuation admission.
// - Must-Not:
//   - Trust the emitter's restoration schedule or authorize publication.
// - Allows:
//   - Inputs: admitted control envelopes and actual immutable VM words.
//   - Outputs: exact required route words and five continuation values.
//   - Side effects: none.
// - Split-When:
//   - Additional recurrent route shapes need independent policies.
// - Merge-When:
//   - General source-frame verification owns the full bootstrap proof.

use std::collections::BTreeMap;

use malbolge::{
    ProfileMachine, decode_profile_instruction, encrypt_profile_cell,
};

use super::{
    Call, Envelope, Error, INVALID, MAX_PREPARATIONS, MISMATCH, Plan, Transfer,
};

const MAX_ROUTE_WORDS: u32 = 32_768;

pub(in super::super) struct BootstrapRoute {
    pub(in super::super) continuations: [u32; 5],
    pub(in super::super) words: BTreeMap<u32, u32>,
}

struct Tape<'machine> {
    cursor: u32,
    limit: u32,
    vm: &'machine ProfileMachine,
    words: BTreeMap<u32, u32>,
}

impl Tape<'_> {
    fn call(&mut self, call: Call, envelope: &Envelope) -> Result<u32, Error> {
        let _entry =
            self.next(Some(envelope.start.checked_sub(1).ok_or(INVALID)?))?;
        let _operand = self.next(Some(
            call.operand
                .checked_sub(envelope.before)
                .and_then(|word| word.checked_sub(1))
                .ok_or(INVALID)?,
        ))?;
        self.cursor.checked_sub(1).ok_or(INVALID)
    }

    fn next(&mut self, expected: Option<u32>) -> Result<u32, Error> {
        if self.cursor >= self.limit {
            return Err(MISMATCH);
        }
        let word = self.read(self.cursor, expected)?;
        self.cursor = self.cursor.checked_add(1).ok_or(MISMATCH)?;
        Ok(word)
    }

    fn prepare(&mut self, envelope: &Envelope) -> Result<(), Error> {
        // The final indirect cell is not encrypted by its own instruction.
        let (_exit, original) = envelope.cells.split_last().ok_or(INVALID)?;
        let mut dirty = original
            .iter()
            .copied()
            .map(|cell| encrypt_profile_cell(cell).ok_or(INVALID))
            .collect::<Result<Vec<_>, _>>()?;
        for _ in 0..MAX_PREPARATIONS {
            if dirty == original {
                return Ok(());
            }
            let target = self.next(None)?;
            let offset = envelope.offset(target)?;
            let suffix = dirty
                .get_mut(offset..)
                .filter(|cells| !cells.is_empty())
                .ok_or(MISMATCH)?;
            restore_suffix(suffix, target)?;
            let skipped = u32::try_from(suffix.len().saturating_sub(1))
                .map_err(|_error| MISMATCH)?;
            self.cursor = self
                .cursor
                .checked_add(skipped)
                .filter(|word| *word <= self.limit)
                .ok_or(MISMATCH)?;
        }
        if dirty == original {
            Ok(())
        } else {
            Err(MISMATCH)
        }
    }

    fn read(
        &mut self,
        address: u32,
        expected: Option<u32>,
    ) -> Result<u32, Error> {
        let value = self.vm.memory_word(address).map_err(|_error| MISMATCH)?;
        if expected.is_some_and(|word| word != value)
            || self.words.insert(address, value).is_some()
        {
            return Err(MISMATCH);
        }
        Ok(value)
    }
}

pub(super) fn bootstrap_addresses(
    plan: &Plan,
    lookup: [u32; 5],
) -> Result<Vec<u32>, Error> {
    let bridge_start = plan.byte_landing;
    let mut addresses = Vec::new();
    for (start, limit) in [
        (plan.main_root, plan.main_limit),
        (bridge_start, plan.bridge.operand),
        (plan.byte_root, plan.byte_limit),
    ] {
        if limit
            .checked_sub(start)
            .is_none_or(|span| span > MAX_ROUTE_WORDS)
        {
            return Err(INVALID);
        }
        addresses.extend(start..limit);
    }
    addresses.push(plan.bridge.operand);
    for &call in plan.main.iter().chain(&plan.byte) {
        let envelope = plan.envelopes.get(&call.site).ok_or(INVALID)?;
        match call.transfer {
            Transfer::Backedge => addresses.push(call.operand),
            Transfer::Ordinary if !lookup.contains(&call.site) => {
                addresses.push(return_address(call, envelope)?);
            },
            Transfer::Bridge | Transfer::Guard | Transfer::Ordinary => {},
        }
    }
    Ok(addresses)
}

pub(super) fn bootstrap_route(
    plan: &Plan,
    vm: &ProfileMachine,
    lookup: [u32; 5],
) -> Result<BootstrapRoute, Error> {
    let mut tape = Tape {
        cursor: plan.byte_root,
        limit: plan.byte_limit,
        vm,
        words: BTreeMap::new(),
    };
    walk_main(&mut tape, plan)?;
    walk_bridge(&mut tape, plan)?;
    tape.cursor = plan.byte_root;
    tape.limit = plan.byte_limit;
    tape.prepare(plan.envelopes.get(&plan.bridge.site).ok_or(INVALID)?)?;
    let mut continuations = [None; 5];
    for &call in &plan.byte {
        let envelope = plan.envelopes.get(&call.site).ok_or(INVALID)?;
        let continuation = tape.call(call, envelope)?;
        if call.transfer == Transfer::Backedge {
            let _word = tape.read(
                call.operand,
                Some(plan.main_root.checked_sub(1).ok_or(INVALID)?),
            )?;
            continue;
        }
        if let Some(index) = lookup.iter().position(|site| *site == call.site) {
            set_continuation(&mut continuations, index, continuation)?;
        } else {
            let _word =
                tape.read(return_address(call, envelope)?, Some(continuation))?;
        }
        tape.prepare(envelope)?;
    }
    let [
        Some(first),
        Some(second),
        Some(third),
        Some(fourth),
        Some(fifth),
    ] = continuations
    else {
        return Err(INVALID);
    };
    Ok(BootstrapRoute {
        continuations: [first, second, third, fourth, fifth],
        words: tape.words,
    })
}

fn restore_suffix(suffix: &mut [u32], target: u32) -> Result<(), Error> {
    for (index, cell) in suffix.iter_mut().enumerate() {
        let address = target
            .checked_add(u32::try_from(index).map_err(|_error| MISMATCH)?)
            .ok_or(MISMATCH)?;
        if index != 0
            && decode_profile_instruction(*cell, address)
                .is_none_or(|opcode| b"ji*p/<v".contains(&opcode))
        {
            return Err(MISMATCH);
        }
        *cell = encrypt_profile_cell(*cell).ok_or(MISMATCH)?;
    }
    Ok(())
}

fn return_address(call: Call, envelope: &Envelope) -> Result<u32, Error> {
    let distance = envelope
        .exit
        .checked_sub(call.site)
        .and_then(|value| value.checked_sub(1))
        .ok_or(INVALID)?;
    call.operand.checked_add(distance).ok_or(INVALID)
}

fn set_continuation(
    continuations: &mut [Option<u32>; 5],
    index: usize,
    value: u32,
) -> Result<(), Error> {
    let slot = continuations.get_mut(index).ok_or(INVALID)?;
    if slot.replace(value).is_some() {
        return Err(INVALID);
    }
    Ok(())
}

fn walk_bridge(tape: &mut Tape<'_>, plan: &Plan) -> Result<(), Error> {
    tape.cursor = plan.byte_landing;
    tape.limit = plan.bridge.operand;
    let envelope = plan.envelopes.get(&plan.bridge.site).ok_or(INVALID)?;
    tape.prepare(envelope)?;
    let _continuation = tape.call(plan.bridge, envelope)?;
    let _word = tape.read(
        plan.bridge.operand,
        Some(plan.byte_root.checked_sub(1).ok_or(INVALID)?),
    )?;
    Ok(())
}

fn walk_main(tape: &mut Tape<'_>, plan: &Plan) -> Result<(), Error> {
    tape.cursor = plan.main_root;
    tape.limit = plan.main_limit;
    tape.prepare(plan.envelopes.get(&plan.bridge.site).ok_or(INVALID)?)?;
    if tape.cursor != plan.main_entry {
        return Err(MISMATCH);
    }
    for &call in &plan.main {
        let envelope = plan.envelopes.get(&call.site).ok_or(INVALID)?;
        let continuation = tape.call(call, envelope)?;
        if call.transfer == Transfer::Guard {
            continue;
        }
        let _word =
            tape.read(return_address(call, envelope)?, Some(continuation))?;
        tape.prepare(envelope)?;
    }
    Ok(())
}
