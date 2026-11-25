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
//   - Exact post-input recurrent control and code-restoration evidence.
// - Must-Not:
//   - Authorize initialization, general source frames or publication.
// - Allows:
//   - Inputs: proposed envelope sites and the real normative trace.
//   - Outputs: finite control-route and complete restoration receipts.
// - Split-When:
//   - Other recurrent control schedules require independent policies.
// - Merge-When:
//   - General source-frame verification owns the physical control proof.

//! Check all post-bootstrap active calls and inert encryption transfers.

#[path = "source_recurrent_control_bootstrap.rs"]
mod source_recurrent_control_bootstrap;
#[path = "source_recurrent_control_bootstrap_code.rs"]
mod source_recurrent_control_bootstrap_code;

use core::iter::{once, repeat_n};
use std::collections::BTreeMap;

use malbolge::{
    ProfileMachine, ProfileStepTrace, StepOutcome, TraceInput,
    decode_profile_instruction, encrypt_profile_cell,
};
pub(super) use source_recurrent_control_bootstrap::BootstrapRoute;
use source_recurrent_control_bootstrap_code::BootstrapCode;

use super::super::{Effect, Error, ProjectedIo};
use super::SourceRecurrentTransitionProbe;

const INVALID: Error = Error::InvalidTransitionBinding;
const MISMATCH: Error = Error::GuestTransitionMismatch;
const MAX_PREPARATIONS: usize = 2_048;

type Envelopes = BTreeMap<u32, Envelope>;
type Fetched = (u8, usize);
type IndexedTrace = (usize, ProfileStepTrace);
pub(super) type ControlReceipt = (usize, usize, usize);

#[derive(Clone, Copy, Eq, PartialEq)]
enum Transfer {
    Backedge,
    Bridge,
    Guard,
    Ordinary,
}

#[derive(Clone, Copy)]
struct Call {
    operand: u32,
    site: u32,
    transfer: Transfer,
}

impl Call {
    const fn branch(site: u32, operand: u32, transfer: Transfer) -> Self {
        Self { operand, site, transfer }
    }

    const fn new(site: u32, operand: u32) -> Self {
        Self {
            operand,
            site,
            transfer: Transfer::Ordinary,
        }
    }
}

#[derive(Clone)]
struct Envelope {
    before: u32,
    cells: Vec<u32>,
    exit: u32,
    start: u32,
}

impl Envelope {
    fn lookup(source: &[u8], site: u32, index: usize) -> Result<Self, Error> {
        let ops: &[u8] = match index {
            1 => b"jjjoppji",
            4 => b"jjjjppji",
            _ => b"jjjppji",
        };
        let offset = if [1, 4].contains(&index) {
            4
        } else {
            3
        };
        Self::new(source, site.checked_sub(offset).ok_or(INVALID)?, ops)
    }

    fn new(source: &[u8], start: u32, ops: &[u8]) -> Result<Self, Error> {
        let base = usize::try_from(start).map_err(|_error| INVALID)?;
        let end = base.checked_add(ops.len()).ok_or(INVALID)?;
        let cells = source.get(base..end).ok_or(INVALID)?;
        for (offset, (&cell, &opcode)) in cells.iter().zip(ops).enumerate() {
            let address = start
                .checked_add(u32::try_from(offset).map_err(|_error| INVALID)?)
                .ok_or(INVALID)?;
            if decode_profile_instruction(u32::from(cell), address)
                != Some(opcode)
            {
                return Err(INVALID);
            }
        }
        Ok(Self {
            before: 0,
            cells: cells.iter().copied().map(u32::from).collect(),
            exit: u32::try_from(end.checked_sub(1).ok_or(INVALID)?)
                .map_err(|_error| INVALID)?,
            start,
        })
    }

    fn offset(&self, address: u32) -> Result<usize, Error> {
        let offset = address.checked_sub(self.start).ok_or(MISMATCH)?;
        usize::try_from(offset).map_err(|_error| MISMATCH)
    }

    fn simple(
        source: &[u8],
        site: u32,
        op: u8,
        (before, after): (usize, usize),
    ) -> Result<Self, Error> {
        let mut ops = vec![b'j'];
        ops.extend(repeat_n(b'o', before));
        ops.push(op);
        ops.extend(repeat_n(b'o', after));
        ops.extend(*b"ji");
        let prefix = u32::try_from(before).map_err(|_error| INVALID)?;
        let start =
            site.checked_sub(prefix.saturating_add(1)).ok_or(INVALID)?;
        let mut envelope = Self::new(source, start, &ops)?;
        envelope.before = prefix;
        Ok(envelope)
    }
}

#[derive(Clone, Copy, Eq, PartialEq)]
enum Phase {
    Bridge,
    Byte,
    Main,
    Terminal,
}

struct Plan {
    bridge: Call,
    byte: Vec<Call>,
    byte_landing: u32,
    byte_limit: u32,
    byte_root: u32,
    envelopes: BTreeMap<u32, Envelope>,
    eof: [u32; 2],
    main: Vec<Call>,
    main_entry: u32,
    main_limit: u32,
    main_root: u32,
    source_extent: u32,
    terminal: u32,
}

impl Plan {
    fn call(&self, phase: Phase, position: usize) -> Result<Call, Error> {
        match phase {
            Phase::Main => self.main.get(position).copied(),
            Phase::Bridge => (position == 0).then_some(self.bridge),
            Phase::Byte => self.byte.get(position).copied(),
            Phase::Terminal => None,
        }
        .ok_or(MISMATCH)
    }

    fn in_route(&self, phase: Phase, cursor: u32) -> bool {
        match phase {
            Phase::Main => (self.main_root..self.main_limit).contains(&cursor),
            Phase::Bridge => {
                (self.byte_landing..self.bridge.operand).contains(&cursor)
            },
            Phase::Byte => (self.byte_root..self.byte_limit).contains(&cursor),
            Phase::Terminal => self.eof.contains(&cursor),
        }
    }

    fn new(probe: &SourceRecurrentTransitionProbe<'_>) -> Result<Self, Error> {
        let guard = &probe.loop_probe.guard;
        let route = &probe.route;
        let eof_first = *guard.eof_landings.iter().min().ok_or(INVALID)?;
        let byte_limit = *probe.tables.iter().min().ok_or(INVALID)?;
        if !(route.main_route < route.main_entry
            && route.main_entry < eof_first
            && guard.byte_landing < route.byte_bridge_word
            && route.byte_bridge_word < route.byte_route
            && route.byte_route < byte_limit)
        {
            return Err(INVALID);
        }
        Ok(Self {
            bridge: Call::branch(
                guard.branch_address,
                route.byte_bridge_word,
                Transfer::Bridge,
            ),
            byte: byte_calls(probe),
            byte_landing: guard.byte_landing,
            byte_limit,
            byte_root: route.byte_route,
            envelopes: envelopes(probe)?,
            eof: guard.eof_landings,
            main: main_calls(probe)?,
            main_entry: route.main_entry,
            main_limit: eof_first,
            main_root: route.main_route,
            source_extent: u32::try_from(guard.io.physical_source.len())
                .map_err(|_error| INVALID)?,
            terminal: probe.terminal_address,
        })
    }
}

struct Execution {
    call: Option<Call>,
    cells: Vec<u32>,
    cursor: u32,
    envelope: Envelope,
    next_code: u32,
    next_data: u32,
    preparations: usize,
}

impl Execution {
    fn active_transfer(
        &self,
        trace: &ProfileStepTrace,
        offset: usize,
        opcode: u8,
    ) -> Result<Option<Transfer>, Error> {
        let Some(call) = self.call else {
            return if b"ji*p/<v".contains(&opcode) || !unchanged(trace) {
                Err(MISMATCH)
            } else {
                Ok(None)
            };
        };
        let address = trace.before.registers.code_pointer;
        let data = trace.after.registers.data_pointer;
        if self.envelope.cells.get(offset) != self.cells.get(offset)
            || (address == self.envelope.start
                && Some(data) != call.operand.checked_sub(self.envelope.before))
        {
            return Err(MISMATCH);
        }
        if address.checked_add(1) != Some(self.envelope.exit) {
            return Ok(None);
        }
        if call.transfer != Transfer::Ordinary {
            return Ok(Some(call.transfer));
        }
        if data != self.cursor.saturating_add(2) {
            return Err(MISMATCH);
        }
        Ok(None)
    }

    fn check_fetch(&self, trace: &ProfileStepTrace) -> Result<Fetched, Error> {
        let before = trace.before.registers;
        let offset = self.envelope.offset(before.code_pointer)?;
        let cell = *self.cells.get(offset).ok_or(MISMATCH)?;
        let opcode = decode_profile_instruction(cell, before.code_pointer)
            .ok_or(MISMATCH)?;
        if before.code_pointer != self.next_code
            || before.data_pointer != self.next_data
            || trace.fetched_cell != Some(cell)
            || trace.decoded != Some(opcode)
            || trace.result != Ok(StepOutcome::Continued)
        {
            return Err(MISMATCH);
        }
        Ok((opcode, offset))
    }

    fn exit(&self, trace: &ProfileStepTrace) -> Result<u32, Error> {
        let (opcode, _) = self.check_fetch(trace)?;
        let before = trace.before.registers;
        let after = trace.after.registers;
        if opcode != b'i'
            || before.code_pointer != self.envelope.exit
            || after.code_pointer != jump_value(trace)?
            || after.data_pointer != before.data_pointer.saturating_add(1)
        {
            return Err(MISMATCH);
        }
        after.code_pointer.checked_sub(1).ok_or(MISMATCH)
    }

    fn first_input(&mut self) -> Result<(), Error> {
        // Bootstrap already executed the input envelope's entry j. Track
        // the one dirty cell without replaying an imaginary input call.
        let first = self.cells.first_mut().ok_or(MISMATCH)?;
        *first = encrypt_profile_cell(*first).ok_or(MISMATCH)?;
        let call = self.call.ok_or(MISMATCH)?;
        self.next_code = call.site;
        self.next_data = call.operand;
        Ok(())
    }

    fn new(envelope: Envelope, call: Call, cursor: u32) -> Self {
        let next_code = envelope.start;
        Self {
            call: Some(call),
            cells: envelope.cells.clone(),
            cursor,
            envelope,
            next_code,
            next_data: cursor.saturating_add(1),
            preparations: 0,
        }
    }

    fn normal(
        &mut self,
        trace: &ProfileStepTrace,
    ) -> Result<Option<Transfer>, Error> {
        let (opcode, offset) = self.check_fetch(trace)?;
        let before = trace.before.registers;
        let after = trace.after.registers;
        let address = before.code_pointer;
        let transfer = self.active_transfer(trace, offset, opcode)?;
        let expected_data = if opcode == b'j' {
            jump_value(trace)?
        } else {
            before.data_pointer.checked_add(1).ok_or(MISMATCH)?
        };
        if opcode == b'i'
            || after.code_pointer != address.saturating_add(1)
            || after.data_pointer != expected_data
            || (trace.memory_delta.data.is_some() && !b"p*".contains(&opcode))
            || (!b"p*/j".contains(&opcode) && !unchanged(trace))
        {
            return Err(MISMATCH);
        }
        let cell = self.cells.get_mut(offset).ok_or(MISMATCH)?;
        *cell = encrypted(trace, address, *cell)?;
        self.next_code = after.code_pointer;
        self.next_data = after.data_pointer;
        Ok(transfer)
    }

    fn restore(
        &mut self,
        trace: &ProfileStepTrace,
        target: u32,
    ) -> Result<(), Error> {
        if self.restored() || self.preparations >= MAX_PREPARATIONS {
            return Err(MISMATCH);
        }
        let offset = self.envelope.offset(target)?;
        let cell = self.cells.get_mut(offset).ok_or(MISMATCH)?;
        *cell = encrypted(trace, target, *cell)?;
        self.call = None;
        self.preparations = self.preparations.saturating_add(1);
        self.next_code = trace.after.registers.code_pointer;
        self.next_data = trace.after.registers.data_pointer;
        Ok(())
    }

    fn restored(&self) -> bool {
        self.cells == self.envelope.cells
    }

    fn verify_initial_entry(
        &mut self,
        indirect: &ProfileStepTrace,
        entry: &ProfileStepTrace,
        extent: u32,
    ) -> Result<(), Error> {
        let before = indirect.before.registers;
        let after = indirect.after.registers;
        let target = self.envelope.start.checked_sub(1).ok_or(MISMATCH)?;
        let fetched = indirect.fetched_cell.ok_or(MISMATCH)?;
        if indirect.decoded != Some(b'i')
            || decode_profile_instruction(fetched, before.code_pointer)
                != Some(b'i')
            || before.code_pointer >= extent
            || before.data_pointer != self.cursor
            || indirect.result != Ok(StepOutcome::Continued)
            || jump_value(indirect)? != self.envelope.start
            || after.code_pointer != self.envelope.start
            || after.data_pointer != self.next_data
            || indirect.after != entry.before
        {
            return Err(MISMATCH);
        }
        let cell = indirect.memory_reads.encryption.ok_or(MISMATCH)?.value;
        let _predecessor = encrypted(indirect, target, cell)?;
        if self.normal(entry)?.is_some() {
            return Err(MISMATCH);
        }
        Ok(())
    }
}

pub(super) struct ControlTrace {
    active: Option<Execution>,
    bootstrap_code: BootstrapCode,
    calls: usize,
    eof: bool,
    initial_entry: Option<[usize; 2]>,
    phase: Phase,
    plan: Plan,
    position: usize,
    prelude: [Option<IndexedTrace>; 2],
    preparations: usize,
    steps: usize,
}

impl ControlTrace {
    fn activate(&mut self, cursor: u32) -> Result<Execution, Error> {
        let call = self.plan.call(self.phase, self.position)?;
        if self.phase == Phase::Main
            && self.position == 0
            && cursor != self.plan.main_entry
        {
            return Err(MISMATCH);
        }
        let envelope = self
            .plan
            .envelopes
            .get(&call.site)
            .cloned()
            .ok_or(INVALID)?;
        self.position = self.position.saturating_add(1);
        self.calls = self.calls.saturating_add(1);
        Ok(Execution::new(envelope, call, cursor))
    }

    fn begin_input(
        &mut self,
        trace: &ProfileStepTrace,
        index: usize,
    ) -> Result<(), Error> {
        let mut active = self.activate(self.plan.main_entry)?;
        if index == 0 {
            // Internal checkpoint forks start with the input itself. A full
            // source-loaded proof must separately require the entry receipt.
            active.first_input()?;
        } else {
            let [Some((indirect_index, indirect)), Some((entry_index, entry))] =
                self.prelude
            else {
                return Err(MISMATCH);
            };
            active.verify_initial_entry(
                &indirect,
                &entry,
                self.plan.source_extent,
            )?;
            if indirect_index.checked_add(1) != Some(entry_index)
                || entry_index.checked_add(1) != Some(index)
                || entry.after != trace.before
            {
                return Err(MISMATCH);
            }
            self.bootstrap_code.complete(index)?;
            self.initial_entry = Some([indirect_index, entry_index]);
        }
        self.active = Some(active);
        Ok(())
    }

    pub(super) fn bootstrap_addresses(
        &self,
        lookup: [u32; 5],
    ) -> Result<Vec<u32>, Error> {
        source_recurrent_control_bootstrap::bootstrap_addresses(
            &self.plan, lookup,
        )
    }

    pub(super) fn bootstrap_code_words(&self) -> Result<usize, Error> {
        let _entry = self.initial_entry()?;
        Ok(self.bootstrap_code.words())
    }

    pub(super) fn bootstrap_route(
        &self,
        vm: &ProfileMachine,
        lookup: [u32; 5],
    ) -> Result<BootstrapRoute, Error> {
        source_recurrent_control_bootstrap::bootstrap_route(
            &self.plan, vm, lookup,
        )
    }

    pub(super) fn initial_entry(&self) -> Result<[usize; 2], Error> {
        self.initial_entry.ok_or(MISMATCH)
    }

    fn leave(
        &mut self,
        mut active: Execution,
        trace: &ProfileStepTrace,
    ) -> Result<(), Error> {
        let target = active.exit(trace)?;
        let cursor = trace.before.registers.data_pointer;
        if !self.plan.in_route(self.phase, cursor) {
            return Err(MISMATCH);
        }
        if (active.envelope.start..active.envelope.exit).contains(&target) {
            if self.phase == Phase::Terminal {
                return Err(MISMATCH);
            }
            active.restore(trace, target)?;
            self.preparations = self.preparations.saturating_add(1);
            self.active = Some(active);
            return Ok(());
        }
        let cell = trace.memory_reads.encryption.ok_or(MISMATCH)?.value;
        let _encrypted = encrypted(trace, target, cell)?;
        if self.phase == Phase::Terminal {
            if target.checked_add(1) != Some(self.plan.terminal) {
                return Err(MISMATCH);
            }
            return Ok(());
        }
        if !active.restored() {
            return Err(MISMATCH);
        }
        let next = self.activate(cursor)?;
        if target.checked_add(1) != Some(next.envelope.start) {
            return Err(MISMATCH);
        }
        self.active = Some(next);
        Ok(())
    }

    pub(super) fn new(
        probe: &SourceRecurrentTransitionProbe<'_>,
    ) -> Result<Self, Error> {
        let plan = Plan::new(probe)?;
        let bootstrap_code = BootstrapCode::new(
            &plan,
            probe.loop_probe.guard.io.physical_source,
        )?;
        Ok(Self {
            active: None,
            bootstrap_code,
            calls: 0,
            eof: false,
            initial_entry: None,
            phase: Phase::Main,
            plan,
            position: 0,
            prelude: [None; 2],
            preparations: 0,
            steps: 0,
        })
    }

    pub(super) fn observe(
        &mut self,
        trace: &ProfileStepTrace,
        index: usize,
        projected_event: Option<ProjectedIo>,
    ) -> Result<(), Error> {
        if let Some(event) = projected_event
            && let Effect::Input(input) = event.effect
        {
            self.eof = input == TraceInput::EndOfInput;
            if self.steps == 0 {
                self.begin_input(trace, index)?;
            }
        }
        if self.steps == 0 && self.active.is_none() {
            self.bootstrap_code.observe(trace, index)?;
            let [_, previous] = self.prelude;
            self.prelude = [previous, Some((index, *trace))];
            return Ok(());
        }
        self.steps = self.steps.saturating_add(1);
        let Some(mut active) = self.active.take() else {
            return if self.phase == Phase::Terminal {
                Ok(())
            } else {
                Err(MISMATCH)
            };
        };
        if trace.before.registers.code_pointer == active.envelope.exit {
            return self.leave(active, trace);
        }
        if let Some(transfer) = active.normal(trace)? {
            self.transfer(transfer, trace.after.registers.data_pointer)?;
        }
        self.active = Some(active);
        Ok(())
    }

    pub(super) fn receipt(&self) -> Result<ControlReceipt, Error> {
        if self.phase != Phase::Terminal
            || self.active.is_some()
            || self.steps == 0
        {
            return Err(MISMATCH);
        }
        Ok((self.calls, self.preparations, self.steps))
    }

    fn transfer(
        &mut self,
        transfer: Transfer,
        landing: u32,
    ) -> Result<(), Error> {
        self.phase = match transfer {
            Transfer::Guard if self.eof && self.plan.eof.contains(&landing) => {
                Phase::Terminal
            },
            Transfer::Guard
                if !self.eof && landing == self.plan.byte_landing =>
            {
                Phase::Bridge
            },
            Transfer::Bridge if landing == self.plan.byte_root => Phase::Byte,
            Transfer::Backedge if landing == self.plan.main_root => Phase::Main,
            Transfer::Ordinary
            | Transfer::Guard
            | Transfer::Bridge
            | Transfer::Backedge => return Err(MISMATCH),
        };
        self.position = 0;
        Ok(())
    }
}

fn byte_calls(probe: &SourceRecurrentTransitionProbe<'_>) -> Vec<Call> {
    let route = &probe.route;
    let guard = &probe.loop_probe.guard;
    let capture = guard.capture_word;
    let [low, high] = probe.loop_probe.state.words;
    let [ptr_low, ptr_high] = route.raw_pointers;
    let [load_first, load_second] = route.load_addresses;
    let [
        [raw_low, _],
        [carry, _],
        [raw_high, _],
        [high_result, _],
        [low_result, _],
    ] = probe.lookup;
    let [raw_low_c, carry_c, raw_high_c, high_c, low_c] =
        route.lookup_constants;
    let [recover_a, recover_b] = route.recover_raw_constants;
    let rotate = probe.rotate_address;
    let mut calls = vec![
        Call::new(rotate, route.load_raw_constant),
        Call::new(load_first, capture),
        Call::new(load_first, ptr_low),
        Call::new(rotate, raw_low_c),
        Call::new(raw_low, ptr_low),
        Call::new(load_first, low),
        Call::new(rotate, carry_c),
        Call::new(carry, low),
        Call::new(load_first, high),
        Call::new(rotate, recover_a),
        Call::new(probe.commit_address, capture),
        Call::new(rotate, recover_b),
        Call::new(load_second, capture),
        Call::new(load_first, ptr_high),
        Call::new(rotate, raw_high_c),
        Call::new(raw_high, ptr_high),
        Call::new(load_second, high),
        Call::new(rotate, high_c),
        Call::new(high_result, high),
    ];
    let [scratch_low, scratch_high] = probe.scratch_words;
    let [reset_low, reset_high] = probe.reset_constants;
    commit_calls(&mut calls, probe, (high, scratch_high), reset_high);
    calls.extend([Call::new(rotate, low_c), Call::new(low_result, low)]);
    commit_calls(&mut calls, probe, (low, scratch_low), reset_low);
    finish_byte_calls(&mut calls, probe);
    calls
}

fn commit_calls(
    calls: &mut Vec<Call>,
    probe: &SourceRecurrentTransitionProbe<'_>,
    (state, scratch): (u32, u32),
    [state_reset, scratch_reset]: [u32; 2],
) {
    calls.push(Call::new(probe.loop_probe.guard.fold_address, scratch));
    reset_calls(calls, probe, (state, state_reset));
    calls.extend([
        Call::new(probe.scratch_rotate_address, scratch),
        Call::new(probe.commit_address, state),
    ]);
    reset_calls(calls, probe, (scratch, scratch_reset));
}

fn encrypted(
    trace: &ProfileStepTrace,
    address: u32,
    cell: u32,
) -> Result<u32, Error> {
    let next = encrypt_profile_cell(cell).ok_or(MISMATCH)?;
    if trace
        .memory_reads
        .encryption
        .map(|read| (read.address, read.value))
        != Some((address, cell))
        || trace
            .memory_delta
            .encryption
            .map(|write| (write.address, write.before, write.after))
            != (next != cell).then_some((address, cell, next))
    {
        return Err(MISMATCH);
    }
    Ok(next)
}

fn envelopes(
    probe: &SourceRecurrentTransitionProbe<'_>,
) -> Result<Envelopes, Error> {
    let guard = &probe.loop_probe.guard;
    let source = guard.io.physical_source;
    let mut result = BTreeMap::new();
    let [first, second] = probe.reset_addresses;
    let [load_first, load_second] = probe.route.load_addresses;
    for (site, op, before, after) in [
        (guard.input_address, b'/', 0, 0),
        (guard.fold_address, b'p', 1, 0),
        (first, b'p', 0, 1),
        (second, b'p', 0, 2),
        (probe.commit_address, b'p', 0, 3),
        (probe.rotate_address, b'*', 0, 0),
        (load_first, b'p', 0, 4),
        (load_second, b'p', 0, 5),
        (probe.scratch_rotate_address, b'*', 0, 3),
    ] {
        insert_envelope(
            &mut result,
            site,
            Envelope::simple(source, site, op, (before, after))?,
        )?;
    }
    let branch = guard.branch_address;
    insert_envelope(
        &mut result,
        branch,
        Envelope::new(source, branch.checked_sub(1).ok_or(INVALID)?, b"jji")?,
    )?;
    for (index, [site, _]) in probe.lookup.into_iter().enumerate() {
        insert_envelope(
            &mut result,
            site,
            Envelope::lookup(source, site, index)?,
        )?;
    }
    if result
        .values()
        .any(|entry| entry.exit >= probe.terminal_address.saturating_sub(1))
    {
        return Err(INVALID);
    }
    Ok(result)
}

fn finish_byte_calls(
    calls: &mut Vec<Call>,
    probe: &SourceRecurrentTransitionProbe<'_>,
) {
    let guard = &probe.loop_probe.guard;
    let capture = guard.capture_word;
    let route = &probe.route;
    reset_calls(calls, probe, (capture, route.capture_reset_constant));
    for ((pointer, constant), seeds) in route
        .raw_pointers
        .into_iter()
        .zip(route.raw_reset_constants)
        .zip(route.raw_restore_words)
    {
        reset_calls(calls, probe, (pointer, constant));
        for address in seeds.into_iter().chain([pointer]) {
            calls.push(Call::new(guard.fold_address, address));
        }
    }
    calls.push(Call::branch(
        guard.branch_address,
        route.loop_return_word,
        Transfer::Backedge,
    ));
}

fn insert_envelope(
    envelopes: &mut BTreeMap<u32, Envelope>,
    site: u32,
    envelope: Envelope,
) -> Result<(), Error> {
    // Reserve the predecessor too: an active-entry i encrypts it, not
    // the first fetched cell. It cannot be any other active envelope.
    if envelope.start == 0
        || envelopes.values().any(|other| {
            envelope.start.saturating_sub(1) <= other.exit
                && other.start.saturating_sub(1) <= envelope.exit
        })
        || envelopes.insert(site, envelope).is_some()
    {
        return Err(INVALID);
    }
    Ok(())
}

fn jump_value(trace: &ProfileStepTrace) -> Result<u32, Error> {
    let read = trace.memory_reads.data.ok_or(MISMATCH)?;
    if read.address != trace.before.registers.data_pointer || !unchanged(trace)
    {
        return Err(MISMATCH);
    }
    read.value.checked_add(1).ok_or(MISMATCH)
}

fn main_calls(
    probe: &SourceRecurrentTransitionProbe<'_>,
) -> Result<Vec<Call>, Error> {
    let guard = &probe.loop_probe.guard;
    let mut calls =
        vec![Call::new(guard.input_address, probe.route.input_word)];
    for address in once(guard.capture_word).chain(guard.classifier_words) {
        calls.push(Call::new(guard.fold_address, address));
    }
    let class = *guard.classifier_words.last().ok_or(INVALID)?;
    calls.push(Call::branch(guard.branch_address, class, Transfer::Guard));
    Ok(calls)
}

fn reset_calls(
    calls: &mut Vec<Call>,
    probe: &SourceRecurrentTransitionProbe<'_>,
    (operand, constant): (u32, u32),
) {
    let [first, second] = probe.reset_addresses;
    calls.extend([
        Call::new(probe.rotate_address, constant),
        Call::new(first, operand),
        Call::new(second, operand),
    ]);
}

const fn unchanged(trace: &ProfileStepTrace) -> bool {
    trace.before.registers.accumulator == trace.after.registers.accumulator
        && trace.memory_delta.data.is_none()
        && trace.input.is_none()
        && trace.output.is_none()
}
