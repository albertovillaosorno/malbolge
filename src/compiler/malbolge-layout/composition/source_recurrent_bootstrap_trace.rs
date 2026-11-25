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
//   - Initial materialization of finite factored transition data.
// - Must-Not:
//   - Trust the builder's word plan or authorize source publication.
// - Allows:
//   - Inputs: independently admitted geometry and real VM observations.
//   - Outputs: required table/seed stores and untouched unreachable slots.
//   - Side effects: none.
// - Split-When:
//   - Multiple independent transition-table representations are supported.
// - Merge-When:
//   - General source-frame verification owns bootstrap data admission.

#[path = "source_recurrent_bootstrap_auxiliary.rs"]
mod source_recurrent_bootstrap_auxiliary;
#[path = "source_recurrent_bootstrap_frame.rs"]
mod source_recurrent_bootstrap_frame;

use std::collections::{BTreeMap, BTreeSet};

use malbolge::{
    ProfileMachine, ProfileStepTrace, StepOutcome, current_profile,
    decode_profile_instruction, encrypt_profile_cell, profile_crazy,
    profile_rotate,
};
use source_recurrent_bootstrap_frame::ClassifierPlan;

use super::source_recurrent_control_trace::BootstrapRoute;
use super::{
    Error, Geometry, SourceRecurrentTransitionProbe, high_selector,
    inverse_rotation, record,
};

const OUTPUT_SPLIT: u32 = 2_187;

#[derive(Clone, Copy)]
enum Expected {
    Auxiliary(u32),
    Classifier,
    Continuation(usize),
    Exact(u32),
    Frame(u32),
    OutputHigh { nibble: u32, site: u32 },
    OutputLow { nibble: u32, site: u32 },
    Prefix(u32),
    RouteCandidate,
    TerminalRotation { value: u32, site: u32 },
    Untouched,
}

impl Expected {
    const fn is_auxiliary(self) -> bool {
        matches!(self, Self::Auxiliary(_) | Self::TerminalRotation { .. })
    }

    const fn is_frame(self) -> bool {
        matches!(self, Self::Classifier | Self::Frame(_))
    }

    fn matches(self, value: u32) -> bool {
        match self {
            Self::Auxiliary(expected)
            | Self::Exact(expected)
            | Self::Frame(expected)
            | Self::TerminalRotation { value: expected, .. } => {
                value == expected
            },
            Self::OutputHigh { nibble, .. } => high_contribution(value, nibble),
            Self::OutputLow { nibble, .. } => low_contribution(value, nibble),
            Self::Prefix(seed) => {
                let ones = current_profile().eof_word().div_euclid(2);
                crazy(value, ones) == value && crazy(seed, value) == seed
            },
            Self::Classifier
            | Self::Continuation(_)
            | Self::RouteCandidate
            | Self::Untouched => true,
        }
    }

    const fn output_site(self) -> Option<u32> {
        match self {
            Self::OutputHigh { site, .. } | Self::OutputLow { site, .. } => {
                Some(site)
            },
            Self::Auxiliary(_)
            | Self::Classifier
            | Self::Continuation(_)
            | Self::Exact(_)
            | Self::Frame(_)
            | Self::Prefix(_)
            | Self::RouteCandidate
            | Self::TerminalRotation { .. }
            | Self::Untouched => None,
        }
    }

    const fn rotation_site(self) -> Option<u32> {
        match self {
            Self::TerminalRotation { site, .. } => Some(site),
            Self::Auxiliary(_)
            | Self::Classifier
            | Self::Continuation(_)
            | Self::Exact(_)
            | Self::Frame(_)
            | Self::OutputHigh { .. }
            | Self::OutputLow { .. }
            | Self::Prefix(_)
            | Self::RouteCandidate
            | Self::Untouched => None,
        }
    }
}

#[derive(Clone, Copy)]
struct Cell {
    consumed: bool,
    expected: Expected,
    last_store: Option<usize>,
    value: u32,
}

impl Cell {
    const fn consume_output(
        &mut self,
        trace: &ProfileStepTrace,
        (site, value): (u32, u32),
    ) -> Result<(), Error> {
        if self.consumed
            || trace.before.registers.code_pointer != site
            || trace.before.registers.accumulator
                != current_profile().eof_word()
        {
            return Err(Error::GuestTransitionMismatch);
        }
        self.consumed = true;
        self.value = value;
        Ok(())
    }

    const fn consume_rotation(
        &mut self,
        trace: &ProfileStepTrace,
        (site, value): (u32, u32),
        opcode: u8,
    ) -> Result<(), Error> {
        if self.consumed
            || opcode != b'*'
            || trace.before.registers.code_pointer != site
        {
            return Err(Error::GuestTransitionMismatch);
        }
        self.consumed = true;
        self.value = value;
        Ok(())
    }

    fn observe(
        &mut self,
        trace: &ProfileStepTrace,
        index: usize,
        initialized: bool,
    ) -> Result<(), Error> {
        if matches!(self.expected, Expected::Untouched) {
            return Err(Error::GuestTransitionMismatch);
        }
        let (opcode, value) = match trace.decoded {
            Some(b'p') => {
                (b'p', crazy(self.value, trace.before.registers.accumulator))
            },
            Some(b'*')
                if initialized
                    && (self.expected.is_auxiliary()
                        || self.expected.is_frame()) =>
            {
                (
                    b'*',
                    profile_rotate(
                        self.value,
                        current_profile().memory_words(),
                    ),
                )
            },
            _ => return Err(Error::GuestTransitionMismatch),
        };
        verify_store(trace, self.value, value, opcode)?;
        if initialized {
            if self.expected.is_frame() {
                self.value = value;
            } else if let Some(site) = self.expected.output_site() {
                self.consume_output(trace, (site, value))?;
            } else if let Some(site) = self.expected.rotation_site() {
                self.consume_rotation(trace, (site, value), opcode)?;
            } else if self.value != value {
                return Err(Error::GuestTransitionMismatch);
            }
        } else {
            self.last_store = Some(index);
            self.value = value;
        }
        Ok(())
    }
}

type TablePlan = BTreeMap<u32, Expected>;
// (table words, route words, auxiliary words, frame words,
// unreachable slots, last materializing step).
pub(super) type BootstrapReceipt = (usize, usize, usize, usize, usize, usize);

pub(super) struct BootstrapTableTrace {
    cells: BTreeMap<u32, Cell>,
    classifier: ClassifierPlan,
    first_input: Option<usize>,
    receipt: Option<BootstrapReceipt>,
    route_reads: BTreeSet<u32>,
    source_extent: u32,
    state_words: [u32; 2],
}

impl BootstrapTableTrace {
    fn complete(&self, index: usize) -> Result<BootstrapReceipt, Error> {
        let mut materialized = 0usize;
        let mut auxiliary = 0usize;
        let mut frame = 0usize;
        let mut unreachable = 0usize;
        let mut last = 0usize;
        for cell in self.cells.values() {
            if matches!(cell.expected, Expected::RouteCandidate) {
                continue;
            }
            if matches!(cell.expected, Expected::Untouched) {
                unreachable = unreachable.saturating_add(1);
                continue;
            }
            let store = cell
                .last_store
                .filter(|store| *store < index)
                .ok_or(Error::GuestTransitionMismatch)?;
            if !cell.expected.matches(cell.value) {
                return Err(Error::GuestTransitionMismatch);
            }
            if cell.expected.is_auxiliary() {
                auxiliary = auxiliary.saturating_add(1);
            } else if cell.expected.is_frame() {
                frame = frame.saturating_add(1);
            } else {
                materialized = materialized.saturating_add(1);
            }
            last = last.max(store);
        }
        self.classifier.verify(&self.cells)?;
        Ok((materialized, 0, auxiliary, frame, unreachable, last))
    }

    pub(super) fn finish(
        &mut self,
        vm: &ProfileMachine,
        route: &BootstrapRoute,
    ) -> Result<(), Error> {
        let (tables, _, auxiliary, frame, unreachable, mut last) =
            self.receipt()?;
        let input = self.first_input.ok_or(Error::GuestTransitionMismatch)?;
        if self
            .route_reads
            .iter()
            .any(|address| !route.words.contains_key(address))
        {
            return Err(Error::GuestTransitionMismatch);
        }
        self.verify_consumed()?;
        for (&address, cell) in &self.cells {
            if vm
                .memory_word(address)
                .map_err(|_error| Error::GuestTransitionMismatch)?
                != cell.value
            {
                return Err(Error::GuestTransitionMismatch);
            }
            if let Expected::Continuation(slot) = cell.expected
                && route.continuations.get(slot) != Some(&cell.value)
            {
                return Err(Error::GuestTransitionMismatch);
            }
        }
        for (&address, &value) in &route.words {
            let cell = self
                .cells
                .get(&address)
                .ok_or(Error::GuestTransitionMismatch)?;
            if !matches!(cell.expected, Expected::RouteCandidate)
                || cell.value != value
            {
                return Err(Error::GuestTransitionMismatch);
            }
            let store = cell
                .last_store
                .filter(|store| *store < input)
                .ok_or(Error::GuestTransitionMismatch)?;
            last = last.max(store);
        }
        self.receipt = Some((
            tables,
            route.words.len(),
            auxiliary,
            frame,
            unreachable,
            last,
        ));
        Ok(())
    }

    pub(super) fn new(
        geometry: &Geometry,
        vm: &ProfileMachine,
        route_addresses: Vec<u32>,
        probe: &SourceRecurrentTransitionProbe<'_>,
    ) -> Result<Self, Error> {
        let source_extent =
            u32::try_from(probe.loop_probe.guard.io.physical_source.len())
                .map_err(|_error| Error::InvalidTransitionBinding)?;
        let mut plan = BTreeMap::new();
        raw_tables(geometry, &mut plan)?;
        low_table(geometry, &mut plan)?;
        high_table(geometry, &mut plan)?;
        output_table(probe, &mut plan)?;
        source_recurrent_bootstrap_auxiliary::auxiliary_words(
            probe, &mut plan,
        )?;
        let classifier = ClassifierPlan::new(probe, &mut plan)?;
        for address in route_addresses {
            if address < source_extent {
                return Err(Error::InvalidTransitionBinding);
            }
            insert(&mut plan, address, Expected::RouteCandidate)?;
        }
        let state_words = probe.loop_probe.state.words;
        if state_words.iter().any(|address| plan.contains_key(address)) {
            return Err(Error::InvalidTransitionBinding);
        }
        let mut cells = BTreeMap::new();
        for (address, expected) in plan {
            if address < source_extent
                || address >= current_profile().memory_words()
            {
                return Err(Error::InvalidTransitionBinding);
            }
            let value = vm
                .memory_word(address)
                .map_err(|_error| Error::InvalidTransitionBinding)?;
            let _previous = cells.insert(address, Cell {
                consumed: false,
                expected,
                last_store: None,
                value,
            });
        }
        Ok(Self {
            cells,
            classifier,
            first_input: None,
            receipt: None,
            route_reads: BTreeSet::new(),
            source_extent,
            state_words,
        })
    }

    pub(super) fn observe(
        &mut self,
        trace: &ProfileStepTrace,
        index: usize,
        first_input: bool,
    ) -> Result<(), Error> {
        if first_input && self.receipt.is_none() {
            self.receipt = Some(self.complete(index)?);
            self.first_input = Some(index);
        }
        if trace
            .memory_reads
            .fetch
            .into_iter()
            .chain(trace.memory_reads.encryption)
            .any(|read| {
                read.address >= self.source_extent
                    && self.cells.contains_key(&read.address)
            })
            || trace.memory_delta.encryption.is_some_and(|write| {
                write.address >= self.source_extent
                    && self.cells.contains_key(&write.address)
            })
        {
            return Err(Error::GuestTransitionMismatch);
        }
        self.observe_read(trace)?;
        let address = trace.before.registers.data_pointer;
        if self.receipt.is_some()
            && let Some(write) = trace.memory_delta.data
            && (!self.cells.contains_key(&write.address)
                && !self.state_words.contains(&write.address))
        {
            return Err(Error::GuestTransitionMismatch);
        }
        if let Some(write) = trace.memory_delta.data
            && write.address != address
            && self.cells.contains_key(&write.address)
        {
            return Err(Error::GuestTransitionMismatch);
        }
        if matches!(trace.decoded, Some(b'p' | b'*'))
            && let Some(cell) = self.cells.get_mut(&address)
        {
            if trace.before.registers.code_pointer >= self.source_extent {
                return Err(Error::GuestTransitionMismatch);
            }
            if self.receipt.is_some()
                && matches!(cell.expected, Expected::RouteCandidate)
            {
                return Err(Error::GuestTransitionMismatch);
            }
            cell.observe(trace, index, self.receipt.is_some())?;
        } else if trace
            .memory_delta
            .data
            .is_some_and(|write| self.cells.contains_key(&write.address))
        {
            return Err(Error::GuestTransitionMismatch);
        }
        Ok(())
    }

    fn observe_read(&mut self, trace: &ProfileStepTrace) -> Result<(), Error> {
        let Some(read) = trace.memory_reads.data else {
            return Ok(());
        };
        let initialized = self.receipt.is_some();
        let Some(cell) = self.cells.get(&read.address) else {
            return if initialized && !self.state_words.contains(&read.address) {
                Err(Error::GuestTransitionMismatch)
            } else {
                Ok(())
            };
        };
        if read.value != cell.value
            || (initialized && matches!(cell.expected, Expected::Untouched))
        {
            return Err(Error::GuestTransitionMismatch);
        }
        if initialized && matches!(cell.expected, Expected::RouteCandidate) {
            let _new = self.route_reads.insert(read.address);
        }
        Ok(())
    }

    pub(super) fn receipt(&self) -> Result<BootstrapReceipt, Error> {
        self.receipt.ok_or(Error::GuestTransitionMismatch)
    }

    fn verify_consumed(&self) -> Result<(), Error> {
        let consumed = self.cells.values().filter(|cell| cell.consumed);
        if consumed
            .clone()
            .filter(|cell| cell.expected.output_site().is_some())
            .count()
            != 2
            || consumed
                .filter(|cell| cell.expected.rotation_site().is_some())
                .count()
                != 3
        {
            return Err(Error::GuestTransitionMismatch);
        }
        Ok(())
    }
}

fn crazy(data: u32, accumulator: u32) -> u32 {
    profile_crazy(data, accumulator, current_profile().word_trits())
}

fn insert(
    plan: &mut TablePlan,
    address: u32,
    expected: Expected,
) -> Result<(), Error> {
    if plan.insert(address, expected).is_some() {
        return Err(Error::InvalidTransitionBinding);
    }
    Ok(())
}

fn pointer(
    plan: &mut TablePlan,
    address: u32,
    landing: u32,
) -> Result<(), Error> {
    insert(
        plan,
        address,
        Expected::Exact(
            landing
                .checked_sub(1)
                .ok_or(Error::InvalidTransitionBinding)?,
        ),
    )
}

fn pair(
    plan: &mut TablePlan,
    address: u32,
    value: u32,
    slot: usize,
) -> Result<(), Error> {
    insert(plan, address, Expected::Prefix(value))?;
    insert(plan, address.saturating_add(1), Expected::Exact(value))?;
    insert(
        plan,
        address.saturating_add(2),
        Expected::Continuation(slot),
    )
}

fn raw_tables(geometry: &Geometry, plan: &mut TablePlan) -> Result<(), Error> {
    let [raw_low, _, raw_high, high] = geometry.tables;
    let [low_seed, _, high_seed, _] = geometry.seeds;
    for raw in 0..256u32 {
        let low_index = raw & 15;
        let high_index = (raw >> 4u32).saturating_mul(2) | (raw & 1);
        for (table, seed, index) in [
            (raw_low, low_seed, low_index),
            (raw_high, high_seed, high_index),
        ] {
            pointer(
                plan,
                table.saturating_add(729).saturating_sub(raw),
                record(seed, index),
            )?;
        }
    }
    let twos = current_profile().eof_word();
    let ones = twos.div_euclid(2);
    for low in 0..16u32 {
        pair(
            plan,
            record(low_seed, low),
            crazy(crazy(ones, low), twos),
            0,
        )?;
    }
    for high_index in 0..32u32 {
        pair(
            plan,
            record(high_seed, high_index),
            high_selector(
                high_index.div_euclid(2),
                high_index.rem_euclid(2),
                high,
            ),
            2,
        )?;
    }
    Ok(())
}

fn low_contribution(value: u32, nibble: u32) -> bool {
    let twos = current_profile().eof_word();
    let ones = twos.div_euclid(2);
    let accumulator = crazy(value, twos);
    accumulator.rem_euclid(OUTPUT_SPLIT) == OUTPUT_SPLIT.saturating_sub(1)
        && crazy(ones, accumulator)
            .div_euclid(OUTPUT_SPLIT)
            .saturating_mul(OUTPUT_SPLIT)
            .rem_euclid(256)
            == nibble
}

fn low_table(geometry: &Geometry, plan: &mut TablePlan) -> Result<(), Error> {
    let [_, table, _, _] = geometry.tables;
    let [_, seed, _, _] = geometry.seeds;
    let [encoding, _] = geometry.encoding;
    for state in 0..16u32 {
        for raw in 0..16u32 {
            let update = (if raw.is_multiple_of(2) {
                state.saturating_add(raw)
            } else {
                state ^ raw
            })
            .saturating_add(3);
            let address = table
                .saturating_add(state.saturating_add(1).saturating_mul(27))
                .saturating_sub(raw);
            pointer(plan, address, record(seed, update))?;
        }
    }
    let twos = current_profile().eof_word();
    for update in 3..=32u32 {
        let address = record(seed, update);
        let carry = match update.div_euclid(16) {
            0 => twos.saturating_sub(81),
            1 => twos,
            2 => twos.saturating_sub(162),
            _ => return Err(Error::InvalidTransitionBinding),
        };
        let mask = encoding
            .get(
                usize::try_from(update & 15)
                    .map_err(|_error| Error::InvalidTransitionBinding)?,
            )
            .copied()
            .ok_or(Error::InvalidTransitionBinding)?;
        pointer(plan, address, address.saturating_add(4))?;
        pair(plan, address.saturating_add(1), carry, 1)?;
        pair(plan, address.saturating_add(4), inverse_rotation(mask), 4)?;
    }
    Ok(())
}

fn high_table(geometry: &Geometry, plan: &mut TablePlan) -> Result<(), Error> {
    let [_, _, _, table] = geometry.tables;
    let [_, _, _, seed] = geometry.seeds;
    let [_, encoding] = geometry.encoding;
    for state in 0..16u32 {
        for raw in 0..16u32 {
            high_edges(plan, (table, seed), (state, raw))?;
        }
        let mask = encoding
            .get(
                usize::try_from(state)
                    .map_err(|_error| Error::InvalidTransitionBinding)?,
            )
            .copied()
            .ok_or(Error::InvalidTransitionBinding)?;
        pair(plan, record(seed, state), inverse_rotation(mask), 3)?;
    }
    Ok(())
}

fn high_contribution(value: u32, nibble: u32) -> bool {
    let twos = current_profile().eof_word();
    let ones = twos.div_euclid(2);
    let scratch = crazy(ones, crazy(value, twos));
    scratch.div_euclid(OUTPUT_SPLIT) == ones.div_euclid(OUTPUT_SPLIT)
        && crazy(scratch, twos)
            .rem_euclid(OUTPUT_SPLIT)
            .rem_euclid(256)
            == nibble.saturating_mul(16)
}

fn high_edges(
    plan: &mut TablePlan,
    (table, seed): (u32, u32),
    (state, raw): (u32, u32),
) -> Result<(), Error> {
    for parity in 0..2u32 {
        for carry in 0..3u32 {
            let address = table
                .saturating_add(487)
                .saturating_add(state.saturating_mul(729))
                .saturating_add(carry.saturating_mul(81))
                .saturating_add(parity.saturating_mul(27))
                .saturating_add(raw);
            if parity == 1 && carry == 2 {
                insert(plan, address, Expected::Untouched)?;
                continue;
            }
            let next = (if parity == 0 {
                state.saturating_add(raw)
            } else {
                state ^ raw
            })
            .saturating_add(carry)
                & 15;
            pointer(plan, address, record(seed, next))?;
        }
    }
    Ok(())
}

fn output_table(
    probe: &SourceRecurrentTransitionProbe<'_>,
    plan: &mut TablePlan,
) -> Result<(), Error> {
    let [_, low, _, high] = probe.tables;
    for nibble in 0..16u32 {
        let high_address = high
            .saturating_add(504)
            .saturating_add(nibble.saturating_mul(729));
        let low_address = low
            .saturating_add(5)
            .saturating_add(nibble.saturating_mul(27));
        for (address, expected) in [
            (high_address, Expected::OutputHigh {
                nibble,
                site: probe.terminal_address.saturating_add(17),
            }),
            (low_address, Expected::OutputLow {
                nibble,
                site: probe.terminal_address.saturating_add(28),
            }),
        ] {
            insert(plan, address, expected)?;
            pointer(plan, address.saturating_add(1), probe.output_scratch)?;
        }
    }
    Ok(())
}

fn verify_store(
    trace: &ProfileStepTrace,
    old: u32,
    value: u32,
    opcode: u8,
) -> Result<(), Error> {
    let before = trace.before.registers;
    let after = trace.after.registers;
    let site = before.code_pointer;
    let address = before.data_pointer;
    let cell = trace.fetched_cell.ok_or(Error::GuestTransitionMismatch)?;
    let encrypted =
        encrypt_profile_cell(cell).ok_or(Error::GuestTransitionMismatch)?;
    if trace.profile != current_profile()
        || trace.result != Ok(StepOutcome::Continued)
        || decode_profile_instruction(cell, site) != Some(opcode)
        || trace
            .memory_reads
            .fetch
            .map(|read| (read.address, read.value))
            != Some((site, cell))
        || trace
            .memory_reads
            .encryption
            .map(|read| (read.address, read.value))
            != Some((site, cell))
        || trace
            .memory_delta
            .encryption
            .map(|write| (write.address, write.before, write.after))
            != (cell != encrypted).then_some((site, cell, encrypted))
        || trace
            .memory_reads
            .data
            .map(|read| (read.address, read.value))
            != Some((address, old))
        || trace
            .memory_delta
            .data
            .map(|write| (write.address, write.before, write.after))
            != (old != value).then_some((address, old, value))
        || after.accumulator != value
        || address.checked_add(1) != Some(after.data_pointer)
        || site.checked_add(1) != Some(after.code_pointer)
        || trace.input.is_some()
        || trace.output.is_some()
    {
        return Err(Error::GuestTransitionMismatch);
    }
    Ok(())
}
