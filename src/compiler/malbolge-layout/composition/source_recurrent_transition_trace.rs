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
//   - Finite physical factored lookup and commit trace.
// - Must-Not:
//   - Authorize the complete SSA frame or relax publication limits.
// - Allows:
//   - Inputs: source transition values, table geometry and normative trace.
//   - Outputs: ordered physical transition receipts.
// - Split-When:
//   - Additional table or commit shapes are needed.
// - Merge-When:
//   - Full source-frame verification owns recurrent transition semantics.
// - Summary:
//   - Tie the selected source parity and next state to actual table effects.

//! Replay the physical indexed effects of a selected source transition.

#[path = "source_recurrent_bootstrap_trace.rs"]
mod source_recurrent_bootstrap_trace;
#[path = "source_recurrent_commit_trace.rs"]
mod source_recurrent_commit_trace;
#[path = "source_recurrent_control_trace.rs"]
mod source_recurrent_control_trace;
#[path = "source_recurrent_route_trace.rs"]
mod source_recurrent_route_trace;
#[path = "source_recurrent_terminal_trace.rs"]
mod source_recurrent_terminal_trace;

use std::collections::BTreeMap;

use malbolge::{
    ProfileMachine, ProfileMemoryRead, ProfileMemoryWrite, ProfileStepTrace,
    StepOutcome, Termination, TraceInput, current_profile,
    decode_profile_instruction, encrypt_profile_cell, profile_crazy,
    profile_rotate,
};
use source_recurrent_bootstrap_trace::{BootstrapReceipt, BootstrapTableTrace};
use source_recurrent_commit_trace::{CommitGeometry, CommitTrace};
use source_recurrent_control_trace::{ControlReceipt, ControlTrace};
use source_recurrent_route_trace::{RouteGeometry, RouteTrace};
use source_recurrent_terminal_trace::TerminalTrace;

use super::super::{Effect, Error, ProjectedIo};
use super::{
    SourceRecurrentTransitionCheckpoint, SourceRecurrentTransitionProbe,
    SourceTransitionValue,
};

#[derive(Clone, Copy)]
enum LookupKind {
    Jump(u32),
    Prefix,
    Value(u32),
}

type LookupExpectations = ([LookupExpectation; 5], u32);

struct LookupExpectation {
    address: u32,
    landing: u32,
    prefix: u32,
    value: u32,
}

impl LookupExpectation {
    const fn new(address: u32, landing: u32, offset: u32, value: u32) -> Self {
        Self {
            address,
            landing,
            prefix: landing.saturating_add(offset),
            value,
        }
    }
}

#[derive(Clone, Copy)]
struct LookupStep {
    address: u32,
    cell: u32,
    kind: LookupKind,
    site: u32,
}

impl LookupStep {
    fn verify(self, trace: &ProfileStepTrace) -> Result<(), Error> {
        let before = trace.before.registers;
        let after = trace.after.registers;
        let data = trace
            .memory_reads
            .data
            .ok_or(Error::GuestTransitionMismatch)?;
        if before.code_pointer != self.site
            || before.data_pointer != self.address
            || trace.fetched_cell != Some(self.cell)
            || data.address != self.address
            || trace.result.is_err()
            || trace.memory_delta.data.is_some()
        {
            return Err(Error::GuestTransitionMismatch);
        }
        let valid = match self.kind {
            LookupKind::Jump(landing) => {
                trace.decoded == Some(b'j')
                    && data.value.checked_add(1) == Some(landing)
                    && after.data_pointer == landing
                    && after.accumulator == before.accumulator
            },
            LookupKind::Prefix => {
                trace.decoded == Some(b'p')
                    && before.accumulator
                        == current_profile().eof_word().div_euclid(2)
                    && profile_crazy(
                        data.value,
                        before.accumulator,
                        current_profile().word_trits(),
                    ) == data.value
                    && after.accumulator == data.value
            },
            LookupKind::Value(value) => {
                trace.decoded == Some(b'p')
                    && data.value == value
                    && after.accumulator == value
                    && profile_crazy(
                        data.value,
                        before.accumulator,
                        current_profile().word_trits(),
                    ) == value
            },
        };
        if !valid {
            return Err(Error::GuestTransitionMismatch);
        }
        Ok(())
    }
}

struct Geometry {
    commit: CommitGeometry,
    encoding: [[u32; 16]; 2],
    lookup_sites: [[u32; 2]; 5],
    pointers: [u32; 5],
    route: RouteGeometry,
    seeds: [u32; 4],
    sites: BTreeMap<u32, u32>,
    tables: [u32; 4],
}

impl Geometry {
    fn new(probe: &SourceRecurrentTransitionProbe<'_>) -> Result<Self, Error> {
        let source = probe.loop_probe.guard.io.physical_source;
        let mut sites = BTreeMap::new();
        for (index, [first, second]) in probe.lookup.iter().copied().enumerate()
        {
            if first.checked_add(1) != Some(second) {
                return Err(Error::InvalidTransitionBinding);
            }
            for (site, opcode) in [(first, b'p'), (second, b'p')] {
                let _cell = validate_site(source, &mut sites, site, opcode)?;
            }
            let offset = if [1, 4].contains(&index) {
                2
            } else {
                1
            };
            let jump = first
                .checked_sub(offset)
                .ok_or(Error::InvalidTransitionBinding)?;
            let selector =
                jump.checked_sub(1).ok_or(Error::InvalidTransitionBinding)?;
            let _selector_cell =
                validate_site(source, &mut sites, selector, b'j')?;
            let _jump_cell = validate_site(source, &mut sites, jump, b'j')?;
            if index == 4 {
                let _cell = validate_site(
                    source,
                    &mut sites,
                    first.saturating_sub(1),
                    b'j',
                )?;
            }
        }
        let commit = CommitGeometry::new(probe, &sites)?;
        let route = RouteGeometry::new(probe, &sites)?;
        validate_data_geometry(probe)?;
        let [raw_low, raw_high] = probe.route.raw_pointers;
        let [low, high] = probe.loop_probe.state.words;
        Ok(Self {
            commit,
            encoding: probe.loop_probe.state.encoding,
            lookup_sites: probe.lookup,
            pointers: [raw_low, low, raw_high, high, low],
            route,
            seeds: probe.seeds,
            sites,
            tables: probe.tables,
        })
    }

    fn step(
        &self,
        site: u32,
        address: u32,
        kind: LookupKind,
    ) -> Result<LookupStep, Error> {
        let cell = *self
            .sites
            .get(&site)
            .ok_or(Error::InvalidTransitionBinding)?;
        Ok(LookupStep {
            address,
            cell,
            kind,
            site,
        })
    }

    fn steps(
        &self,
        expectations: [LookupExpectation; 5],
    ) -> Result<Vec<LookupStep>, Error> {
        let mut steps = Vec::with_capacity(21);
        for (index, ([first, second], expected)) in
            self.lookup_sites.into_iter().zip(expectations).enumerate()
        {
            let offset = if [1, 4].contains(&index) {
                2
            } else {
                1
            };
            let selector = *self
                .pointers
                .get(index)
                .ok_or(Error::InvalidTransitionBinding)?;
            steps.push(self.step(
                first.saturating_sub(offset).saturating_sub(1),
                selector,
                LookupKind::Jump(expected.address),
            )?);
            steps.push(self.step(
                first.saturating_sub(offset),
                expected.address,
                LookupKind::Jump(expected.landing),
            )?);
            if index == 4 {
                steps.push(self.step(
                    first.saturating_sub(1),
                    expected.landing,
                    LookupKind::Jump(expected.prefix),
                )?);
            }
            steps.push(self.step(
                first,
                expected.prefix,
                LookupKind::Prefix,
            )?);
            steps.push(self.step(
                second,
                expected.prefix.saturating_add(1),
                LookupKind::Value(expected.value),
            )?);
        }
        Ok(steps)
    }
}

struct PendingTransition {
    carry: u32,
    chains: [Option<[usize; 9]>; 2],
    expected: Vec<LookupStep>,
    indices: Vec<usize>,
    input_index: usize,
    pending_commit: Option<CommitTrace>,
    route: RouteTrace,
    source: SourceTransitionValue,
}

impl PendingTransition {
    fn begin_commit(
        &mut self,
        geometry: &Geometry,
        step: LookupStep,
    ) -> Result<(), Error> {
        let (slot, nibble) = match self.indices.len() {
            16 => (1, self.source.next_state >> 4u32),
            21 => (0, self.source.next_state & 15),
            _ => return Ok(()),
        };
        let LookupKind::Value(lookup) = step.kind else {
            return Err(Error::GuestTransitionMismatch);
        };
        let value = *geometry
            .encoding
            .get(slot)
            .and_then(|row| row.get(usize::from(nibble)))
            .ok_or(Error::InvalidTransitionBinding)?;
        // The state was the selected table predecessor before its
        // two-fold dirty reset. Bind that old value as well.
        let first = if slot == 1 {
            13
        } else {
            17
        };
        let dirty_state = self
            .expected
            .get(first)
            .and_then(|entry| entry.address.checked_sub(1))
            .ok_or(Error::InvalidTransitionBinding)?;
        self.pending_commit =
            Some(CommitTrace::new(slot, value, lookup, dirty_state));
        Ok(())
    }

    fn finish(
        self,
        next: ProjectedIo,
        index: usize,
    ) -> Result<SourceRecurrentTransitionCheckpoint, Error> {
        let [Some(low), Some(high)] = self.chains else {
            return Err(Error::GuestTransitionMismatch);
        };
        if self.pending_commit.is_some()
            || self.indices.len() != self.expected.len()
            || !matches!(next.effect, Effect::Input(_))
            || next.state.map(|state| state.value)
                != Some(self.source.next_state)
        {
            return Err(Error::GuestTransitionMismatch);
        }
        let source = self.source;
        Ok(SourceRecurrentTransitionCheckpoint {
            arm_result: source.arm_result,
            arm_value: source.arm_value,
            carry: self.carry,
            commit_effect_indices: [low, high],
            commit_indices: [
                *low.get(5).ok_or(Error::GuestTransitionMismatch)?,
                *high.get(5).ok_or(Error::GuestTransitionMismatch)?,
            ],
            condition: source.condition,
            input_index: self.input_index,
            lookup_indices: self.indices,
            next_input_index: index,
            next_state: source.next_state,
            parity: source.parity,
            prior_state: source.prior_state,
            raw_byte: source.raw_byte,
            route_effect_indices: self.route.finish()?,
            source_block: source.source_block,
            source_target: source.source_target,
        })
    }

    fn new(
        geometry: &Geometry,
        source: SourceTransitionValue,
        index: usize,
    ) -> Result<Self, Error> {
        if !source.arm_checked {
            return Err(Error::InvalidTransitionBinding);
        }
        let (expectations, carry) = lookup_expectations(geometry, source)?;
        let route = RouteTrace::new(&geometry.route, source, &expectations)?;
        Ok(Self {
            carry,
            chains: [None, None],
            expected: geometry.steps(expectations)?,
            indices: Vec::with_capacity(21),
            input_index: index,
            pending_commit: None,
            route,
            source,
        })
    }

    fn observe(
        &mut self,
        geometry: &Geometry,
        trace: &ProfileStepTrace,
        index: usize,
    ) -> Result<(), Error> {
        if !self.route.dispatch(&geometry.route, trace)? {
            return Ok(());
        }
        let before = trace.before.registers;
        let site = before.code_pointer;
        if self.pending_commit.is_some() {
            if matches!(trace.decoded, Some(b'p' | b'*')) {
                return self.observe_commit(geometry, trace, index);
            }
            if geometry.sites.contains_key(&site) && trace.decoded == Some(b'j')
            {
                return Err(Error::GuestTransitionMismatch);
            }
        } else if geometry.commit.is_unbound_effect(trace) {
            return Err(Error::GuestTransitionMismatch);
        }
        if geometry.sites.contains_key(&site)
            && matches!(trace.decoded, Some(b'j' | b'p' | b'*'))
        {
            self.route.require_before_lookup(self.indices.len())?;
            let step = self
                .expected
                .get(self.indices.len())
                .ok_or(Error::GuestTransitionMismatch)?;
            step.verify(trace)?;
            self.indices.push(index);
            self.begin_commit(geometry, *step)?;
        } else if matches!(trace.decoded, Some(b'p' | b'*')) {
            self.route.observe(self.indices.len(), trace, index)?;
        }
        Ok(())
    }

    fn observe_commit(
        &mut self,
        geometry: &Geometry,
        trace: &ProfileStepTrace,
        index: usize,
    ) -> Result<(), Error> {
        let chain = self
            .pending_commit
            .as_mut()
            .ok_or(Error::GuestTransitionMismatch)?;
        let Some(indices) = chain.observe(&geometry.commit, trace, index)?
        else {
            return Ok(());
        };
        let slot = self
            .chains
            .get_mut(chain.slot)
            .ok_or(Error::GuestTransitionMismatch)?;
        if slot.replace(indices).is_some() {
            return Err(Error::GuestTransitionMismatch);
        }
        self.pending_commit = None;
        Ok(())
    }
}

pub(in super::super) struct TransitionTrace {
    bootstrap: Option<BootstrapTableTrace>,
    pub(super) checkpoints: Vec<SourceRecurrentTransitionCheckpoint>,
    control: ControlTrace,
    geometry: Geometry,
    pending: Option<PendingTransition>,
    source_extent: u32,
    started: bool,
    pub(super) terminal: TerminalTrace,
}

impl TransitionTrace {
    pub(super) fn bootstrap_code_words(&self) -> Result<usize, Error> {
        self.control.bootstrap_code_words()
    }

    pub(super) fn bootstrap_receipt(&self) -> Result<BootstrapReceipt, Error> {
        self.bootstrap
            .as_ref()
            .ok_or(Error::GuestTransitionMismatch)?
            .receipt()
    }

    pub(super) fn control_receipt(&self) -> Result<ControlReceipt, Error> {
        self.control.receipt()
    }

    pub(in super::super) fn finish(
        &mut self,
        vm: &ProfileMachine,
    ) -> Result<(), Error> {
        if self.pending.is_some() {
            return Err(Error::GuestTransitionMismatch);
        }
        let _control = self.control.receipt()?;
        if let Some(bootstrap) = self.bootstrap.as_mut() {
            let route = self.control.bootstrap_route(
                vm,
                self.geometry.lookup_sites.map(|[site, _]| site),
            )?;
            bootstrap.finish(vm, &route)?;
        }
        self.terminal.receipt().map(|_receipt| ())
    }

    pub(super) fn initial_entry(&self) -> Result<[usize; 2], Error> {
        self.control.initial_entry()
    }

    pub(in super::super) fn new(
        probe: &SourceRecurrentTransitionProbe<'_>,
    ) -> Result<Self, Error> {
        Ok(Self {
            bootstrap: None,
            checkpoints: Vec::new(),
            control: ControlTrace::new(probe)?,
            geometry: Geometry::new(probe)?,
            pending: None,
            source_extent: u32::try_from(
                probe.loop_probe.guard.io.physical_source.len(),
            )
            .map_err(|_error| Error::InvalidTransitionBinding)?,
            started: false,
            terminal: TerminalTrace::new(probe)?,
        })
    }

    pub(in super::super) fn observe(
        &mut self,
        trace: &ProfileStepTrace,
        index: usize,
        projected_event: Option<ProjectedIo>,
    ) -> Result<(), Error> {
        let input = projected_event
            .is_some_and(|event| matches!(event.effect, Effect::Input(_)));
        if let Some(bootstrap) = self.bootstrap.as_mut() {
            bootstrap.observe(trace, index, input && !self.started)?;
        }
        if input {
            self.started = true;
        }
        if self.started
            && (trace.before.registers.code_pointer >= self.source_extent
                || trace
                    .memory_reads
                    .encryption
                    .is_some_and(|read| read.address >= self.source_extent)
                || trace
                    .memory_delta
                    .encryption
                    .is_some_and(|write| write.address >= self.source_extent)
                || trace
                    .memory_delta
                    .data
                    .is_some_and(|write| write.address < self.source_extent))
        {
            return Err(Error::GuestTransitionMismatch);
        }
        if self.started {
            verify_access_roles(trace, self.source_extent)?;
        }
        self.control.observe(trace, index, projected_event)?;
        self.terminal.observe(trace, index, projected_event)?;
        if let Some(event) = projected_event {
            if let Some(pending) = self.pending.take() {
                self.checkpoints.push(pending.finish(event, index)?);
            }
            if matches!(event.effect, Effect::Input(TraceInput::Byte(_))) {
                let source =
                    event.transition.ok_or(Error::InvalidTransitionBinding)?;
                self.pending = Some(PendingTransition::new(
                    &self.geometry,
                    source,
                    index,
                )?);
            }
        } else if let Some(pending) = self.pending.as_mut() {
            pending.observe(&self.geometry, trace, index)?;
        }
        Ok(())
    }

    pub(in super::super) fn with_bootstrap(
        probe: &SourceRecurrentTransitionProbe<'_>,
        vm: &ProfileMachine,
    ) -> Result<Self, Error> {
        let mut audit = Self::new(probe)?;
        audit.bootstrap = Some(BootstrapTableTrace::new(
            &audit.geometry,
            vm,
            audit.control.bootstrap_addresses(
                audit.geometry.lookup_sites.map(|[site, _]| site),
            )?,
            probe,
        )?);
        Ok(audit)
    }
}

fn validate_data_geometry(
    probe: &SourceRecurrentTransitionProbe<'_>,
) -> Result<(), Error> {
    let [raw_low, low, raw_high, high] = probe.tables;
    let [raw_low_seed, low_seed, raw_high_seed, high_seed] = probe.seeds;
    let ranges = [
        (raw_low.saturating_add(474), raw_low.saturating_add(729)),
        (low.saturating_add(5), low.saturating_add(432)),
        (raw_high.saturating_add(474), raw_high.saturating_add(729)),
        (high.saturating_add(487), high.saturating_add(11_626)),
        (raw_low_seed, raw_low_seed.saturating_add(127)),
        (low_seed, low_seed.saturating_add(263)),
        (raw_high_seed, raw_high_seed.saturating_add(255)),
        (high_seed, high_seed.saturating_add(127)),
    ];
    let guard = &probe.loop_probe.guard;
    let source_length = guard.io.physical_source.len();
    if probe.tables.into_iter().chain(probe.seeds).any(|base| {
        usize::try_from(base).map_or(true, |address| address < source_length)
    }) {
        return Err(Error::InvalidTransitionBinding);
    }
    let reserved = probe
        .loop_probe
        .state
        .words
        .into_iter()
        .chain(guard.classifier_words)
        .chain(guard.eof_landings)
        .chain([guard.capture_word, guard.byte_landing, probe.output_scratch])
        .chain(probe.scratch_words)
        .chain(probe.reset_constants.into_iter().flatten())
        .chain(probe.route.data_words())
        .chain(
            probe
                .output_constants
                .into_iter()
                .flatten()
                .flat_map(|address| [address, address.saturating_add(1)]),
        )
        .chain([probe.output_scratch.saturating_add(1)]);
    for (index, (start, end)) in ranges.iter().copied().enumerate() {
        if usize::try_from(start)
            .map_or(true, |address| address < source_length)
            || end >= current_profile().memory_words()
            || reserved
                .clone()
                .any(|address| (start..=end).contains(&address))
            || ranges.iter().skip(index.saturating_add(1)).any(
                |(other_start, other_end)| {
                    start <= *other_end && *other_start <= end
                },
            )
        {
            return Err(Error::InvalidTransitionBinding);
        }
    }
    Ok(())
}

fn validate_site(
    source: &[u8],
    sites: &mut BTreeMap<u32, u32>,
    site: u32,
    opcode: u8,
) -> Result<u32, Error> {
    let cell = usize::try_from(site)
        .ok()
        .and_then(|address| source.get(address))
        .copied()
        .map(u32::from)
        .ok_or(Error::InvalidTransitionBinding)?;
    if sites.insert(site, cell).is_some()
        || decode_profile_instruction(cell, site) != Some(opcode)
    {
        return Err(Error::InvalidTransitionBinding);
    }
    Ok(cell)
}

const fn inverse_rotation(value: u32) -> u32 {
    value
        .rem_euclid(4_782_969)
        .saturating_mul(3)
        .saturating_add(value.div_euclid(4_782_969))
}

fn high_selector(high: u32, parity: u32, high_table: u32) -> u32 {
    let profile = current_profile();
    let ones = profile.eof_word().div_euclid(2);
    let low = profile_crazy(
        ones,
        high.saturating_add(parity.saturating_mul(27)),
        profile.word_trits(),
    );
    let upper = profile_crazy(ones, high_table, profile.word_trits());
    upper
        .saturating_sub(upper.rem_euclid(19_683))
        .saturating_add(19_602)
        .saturating_add(low.rem_euclid(81))
}

const fn record(base: u32, index: u32) -> u32 {
    base.saturating_add(index.saturating_mul(8))
}

fn lookup_expectations(
    geometry: &Geometry,
    value: SourceTransitionValue,
) -> Result<LookupExpectations, Error> {
    let [raw_low, low, raw_high, high] = geometry.tables;
    let [raw_low_seed, low_seed, raw_high_seed, high_seed] = geometry.seeds;
    let raw = u32::from(value.raw_byte);
    let prior = u32::from(value.prior_state);
    let low_intermediate = (if value.parity == 0 {
        (prior & 15).saturating_add(raw & 15)
    } else {
        (prior ^ raw) & 15
    })
    .saturating_add(3);
    let carry = low_intermediate.div_euclid(16);
    let low_record = record(low_seed, low_intermediate);
    let raw_low_record = record(raw_low_seed, raw & 15);
    let raw_high_record = record(
        raw_high_seed,
        (raw >> 4u32).saturating_mul(2).saturating_add(value.parity),
    );
    let high_record = record(high_seed, u32::from(value.next_state >> 4u32));
    let low_address = low
        .saturating_add((prior & 15).saturating_add(1).saturating_mul(27))
        .saturating_sub(raw & 15);
    let high_address = high
        .saturating_add(487)
        .saturating_add((prior >> 4u32).saturating_mul(729))
        .saturating_add(carry.saturating_mul(81))
        .saturating_add(value.parity.saturating_mul(27))
        .saturating_add(raw >> 4u32);
    let [
        raw_low_value,
        carry_value,
        high_selector_value,
        high_result,
        low_result,
    ] = lookup_values(geometry, value, carry)?;
    Ok((
        [
            LookupExpectation::new(
                raw_low.saturating_add(729).saturating_sub(raw),
                raw_low_record,
                0,
                raw_low_value,
            ),
            LookupExpectation::new(low_address, low_record, 1, carry_value),
            LookupExpectation::new(
                raw_high.saturating_add(729).saturating_sub(raw),
                raw_high_record,
                0,
                high_selector_value,
            ),
            LookupExpectation::new(high_address, high_record, 0, high_result),
            LookupExpectation::new(low_address, low_record, 4, low_result),
        ],
        carry,
    ))
}
fn lookup_values(
    geometry: &Geometry,
    value: SourceTransitionValue,
    carry: u32,
) -> Result<[u32; 5], Error> {
    let raw = u32::from(value.raw_byte);
    let [_, _, _, high] = geometry.tables;
    let profile = current_profile();
    let twos = profile.eof_word();
    let ones = twos.div_euclid(2);
    let raw_low_value = profile_crazy(
        profile_crazy(ones, raw & 15, profile.word_trits()),
        twos,
        profile.word_trits(),
    );
    let carry_value = match carry {
        0 => twos.saturating_sub(81),
        1 => twos,
        2 => twos.saturating_sub(162),
        _ => return Err(Error::InvalidTransitionBinding),
    };
    let [low_encoding, high_encoding] = geometry.encoding;
    let low_mask = *low_encoding
        .get(usize::from(value.next_state & 15))
        .ok_or(Error::InvalidTransitionBinding)?;
    let high_mask = *high_encoding
        .get(usize::from(value.next_state >> 4u32))
        .ok_or(Error::InvalidTransitionBinding)?;
    Ok([
        raw_low_value,
        carry_value,
        high_selector(raw >> 4u32, value.parity, high),
        inverse_rotation(high_mask),
        inverse_rotation(low_mask),
    ])
}

fn verify_access_data(
    trace: &ProfileStepTrace,
    opcode: u8,
    data: ProfileMemoryRead,
) -> Result<(), Error> {
    let mismatch = Error::GuestTransitionMismatch;
    let before = trace.before.registers;
    let after = trace.after.registers;
    let profile = current_profile();
    let value = match opcode {
        b'p' => {
            profile_crazy(data.value, before.accumulator, profile.word_trits())
        },
        b'*' => profile_rotate(data.value, profile.memory_words()),
        b'i' | b'j' => {
            return if trace.memory_delta.data.is_none()
                && before.accumulator == after.accumulator
            {
                Ok(())
            } else {
                Err(mismatch)
            };
        },
        _ => return Err(mismatch),
    };
    if after.accumulator != value
        || trace.memory_delta.data
            != (data.value != value).then_some(ProfileMemoryWrite {
                address: data.address,
                before: data.value,
                after: value,
            })
    {
        return Err(mismatch);
    }
    Ok(())
}

fn verify_access_encryption(
    trace: &ProfileStepTrace,
    opcode: u8,
    cell: u32,
) -> Result<(), Error> {
    let mismatch = Error::GuestTransitionMismatch;
    let before = trace.before.registers;
    let after = trace.after.registers;
    if opcode == b'v' {
        return if trace.result
            == Ok(StepOutcome::Terminated(Termination::HaltInstruction))
            && trace.memory_reads.encryption.is_none()
            && trace.memory_delta.encryption.is_none()
            && before == after
        {
            Ok(())
        } else {
            Err(mismatch)
        };
    }
    let target = if opcode == b'i' {
        after.code_pointer.checked_sub(1).ok_or(mismatch)?
    } else {
        before.code_pointer
    };
    let read = trace.memory_reads.encryption.ok_or(mismatch)?;
    let encrypted = encrypt_profile_cell(read.value).ok_or(mismatch)?;
    if trace.result != Ok(StepOutcome::Continued)
        || read.address != target
        || (target == before.code_pointer && read.value != cell)
        || trace.memory_delta.encryption
            != (read.value != encrypted).then_some(ProfileMemoryWrite {
                address: target,
                before: read.value,
                after: encrypted,
            })
    {
        return Err(mismatch);
    }
    Ok(())
}

// The recurrent envelopes execute in source memory and read expanded data.
// Check semantic access roles even when replay begins at a checkpoint and
// the full bootstrap address/value journal is not present.
fn verify_access_roles(
    trace: &ProfileStepTrace,
    source_extent: u32,
) -> Result<(), Error> {
    let mismatch = Error::GuestTransitionMismatch;
    let before = trace.before.registers;
    let cell = trace.fetched_cell.ok_or(mismatch)?;
    let opcode = trace.decoded.ok_or(mismatch)?;
    if trace.memory_reads.fetch
        != Some(ProfileMemoryRead {
            address: before.code_pointer,
            value: cell,
        })
        || decode_profile_instruction(cell, before.code_pointer) != Some(opcode)
    {
        return Err(mismatch);
    }
    verify_access_encryption(trace, opcode, cell)?;
    if !matches!(opcode, b'i' | b'j' | b'p' | b'*') {
        return if trace.memory_reads.data.is_none()
            && trace.memory_delta.data.is_none()
        {
            Ok(())
        } else {
            Err(mismatch)
        };
    }
    let data = trace.memory_reads.data.ok_or(mismatch)?;
    if data.address != before.data_pointer || data.address < source_extent {
        return Err(mismatch);
    }
    verify_access_data(trace, opcode, data)
}
