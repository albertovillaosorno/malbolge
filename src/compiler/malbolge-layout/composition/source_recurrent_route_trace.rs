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
//   - Finite raw pointer preparation and recurrent restoration evidence.
// - Must-Not:
//   - Authorize full source frames or unobserved physical control edges.
// - Allows:
//   - Inputs: canonical byte/state, physical geometry and normative trace.
//   - Outputs: ordered arithmetic receipts between guard and next input.
// - Split-When:
//   - Additional recurrent pointer encodings require independent policies.
// - Merge-When:
//   - Full source-frame verification owns these physical effects.
// - Summary:
//   - Authenticate exact operands and values in the factored byte route.

//! Verify all arithmetic outside the guard, indexed loads and commits.

use std::collections::{BTreeMap, BTreeSet};

use malbolge::{ProfileStepTrace, current_profile};

use super::super::{SourceRecurrentRouteProbe, SourceRecurrentTransitionProbe};
use super::source_recurrent_commit_trace::{Expected, Site, crazy};
use super::{Error, LookupExpectation, SourceTransitionValue};

const EFFECT_COUNT: usize = 31;
type RouteIndices = [usize; EFFECT_COUNT];

impl SourceRecurrentRouteProbe {
    pub(super) fn data_words(self) -> impl Iterator<Item = u32> + Clone {
        [self.capture_reset_constant, self.load_raw_constant]
            .into_iter()
            .chain(self.lookup_constants)
            .chain(self.raw_pointers)
            .chain(self.raw_reset_constants)
            .chain(self.raw_restore_words.into_iter().flatten())
            .chain(self.recover_raw_constants)
    }
}

struct RouteEffect {
    after_lookups: usize,
    expected: Expected,
}

struct Stage<'effects> {
    effects: &'effects mut Vec<RouteEffect>,
    lookups: usize,
}

impl Stage<'_> {
    fn fold(
        &mut self,
        site: Site,
        address: u32,
        (old, input, output): (u32, u32, u32),
    ) {
        self.effects.push(RouteEffect {
            after_lookups: self.lookups,
            expected: Expected::new(
                site,
                address,
                (Some(old), Some(input), Some(output)),
            ),
        });
    }

    fn uniform(&mut self, site: Site, address: u32, value: u32) {
        self.effects.push(RouteEffect {
            after_lookups: self.lookups,
            expected: Expected::new(
                site,
                address,
                (Some(value), None, Some(value)),
            ),
        });
    }
}

pub(super) struct RouteGeometry {
    branch: u32,
    byte_landing: u32,
    capture: u32,
    encoding: [[u32; 16]; 2],
    route: SourceRecurrentRouteProbe,
    sites: [Site; 7],
    tables: [u32; 4],
    words: [u32; 2],
}

impl RouteGeometry {
    pub(super) fn new(
        probe: &SourceRecurrentTransitionProbe<'_>,
        lookup_sites: &BTreeMap<u32, u32>,
    ) -> Result<Self, Error> {
        let guard = &probe.loop_probe.guard;
        let source = guard.io.physical_source;
        let mut occupied = lookup_sites.clone();
        let [first, second] = probe.reset_addresses;
        let [load_first, load_second] = probe.route.load_addresses;
        for (address, opcode) in [
            (guard.input_address, b'/'),
            (guard.branch_address, b'j'),
            (probe.scratch_rotate_address, b'*'),
        ] {
            let _site = Site::new(source, &mut occupied, address, opcode)?;
        }
        let sites = [
            Site::new(source, &mut occupied, guard.fold_address, b'p')?,
            Site::new(source, &mut occupied, probe.rotate_address, b'*')?,
            Site::new(source, &mut occupied, first, b'p')?,
            Site::new(source, &mut occupied, second, b'p')?,
            Site::new(source, &mut occupied, probe.commit_address, b'p')?,
            Site::new(source, &mut occupied, load_first, b'p')?,
            Site::new(source, &mut occupied, load_second, b'p')?,
        ];
        let words = probe.loop_probe.state.words;
        let mut reserved = words
            .into_iter()
            .chain(guard.classifier_words)
            .chain(guard.eof_landings)
            .chain([
                guard.capture_word,
                guard.byte_landing,
                probe.output_scratch,
            ])
            .chain(probe.scratch_words)
            .chain(probe.reset_constants.into_iter().flatten())
            .collect::<BTreeSet<_>>();
        for address in probe.route.data_words() {
            if usize::try_from(address)
                .map_or(true, |value| value < source.len())
                || address >= current_profile().memory_words()
                || !reserved.insert(address)
            {
                return Err(Error::InvalidTransitionBinding);
            }
        }
        Ok(Self {
            branch: guard.branch_address,
            byte_landing: guard.byte_landing,
            capture: guard.capture_word,
            encoding: probe.loop_probe.state.encoding,
            route: probe.route,
            sites,
            tables: probe.tables,
            words,
        })
    }

    fn prepare_high(
        &self,
        effects: &mut Vec<RouteEffect>,
        (ready, prior, partial): (u32, u32, u32),
        lookup: &[LookupExpectation; 5],
    ) -> Result<(), Error> {
        let [_, rotate, _, _, commit, first, second] = self.sites;
        let [_, high] = self.words;
        let [_, ptr_high] = self.route.raw_pointers;
        let [_, carry, raw_high, high_result, _] = lookup;
        let [_, _, raw_high_c, high_c, _] = self.route.lookup_constants;
        let [recover_a, recover_b] = self.route.recover_raw_constants;
        let twos = current_profile().eof_word();
        let ones = twos.div_euclid(2);
        let intermediate = crazy(ready, twos);
        let mut stage = Stage { effects, lookups: 8 };
        stage.fold(first, high, (prior, carry.value, partial));
        stage.uniform(rotate, recover_a, twos);
        stage.fold(commit, self.capture, (ready, twos, intermediate));
        stage.uniform(rotate, recover_b, twos);
        stage.fold(second, self.capture, (intermediate, twos, ready));
        stage.fold(
            first,
            ptr_high,
            (self.raw_mask(1)?, ready, raw_high.address.saturating_sub(1)),
        );
        stage.uniform(rotate, raw_high_c, ones);
        stage.lookups = 12;
        stage.fold(
            second,
            high,
            (
                partial,
                raw_high.value,
                high_result.address.saturating_sub(1),
            ),
        );
        stage.uniform(rotate, high_c, ones);
        Ok(())
    }

    fn prepare_low(
        &self,
        effects: &mut Vec<RouteEffect>,
        raw: u32,
        lookup: &[LookupExpectation; 5],
    ) -> Result<u32, Error> {
        let [_, rotate, _, _, _, load, _] = self.sites;
        let [ptr_low, _] = self.route.raw_pointers;
        let [raw_low, _, _, _, _] = lookup;
        let [raw_low_c, _, _, _, _] = self.route.lookup_constants;
        let twos = current_profile().eof_word();
        let ones = twos.div_euclid(2);
        let captured = crazy(ones, raw);
        let ready = crazy(captured, twos);
        let mut stage = Stage { effects, lookups: 0 };
        stage.uniform(rotate, self.route.load_raw_constant, twos);
        stage.fold(load, self.capture, (captured, twos, ready));
        stage.fold(
            load,
            ptr_low,
            (self.raw_mask(0)?, ready, raw_low.address.saturating_sub(1)),
        );
        stage.uniform(rotate, raw_low_c, ones);
        Ok(ready)
    }

    fn raw_mask(&self, slot: usize) -> Result<u32, Error> {
        let index = slot.saturating_mul(2);
        let table = *self
            .tables
            .get(index)
            .ok_or(Error::InvalidTransitionBinding)?;
        Ok(crazy(table, current_profile().eof_word()).saturating_add(364))
    }

    fn reset(
        &self,
        stage: &mut Stage<'_>,
        (address, constant, old): (u32, u32, u32),
    ) {
        let [_, rotate, first, second, _, _, _] = self.sites;
        let ones = current_profile().eof_word().div_euclid(2);
        let folded = crazy(old, ones);
        stage.uniform(rotate, constant, ones);
        stage.fold(first, address, (old, ones, folded));
        stage.fold(second, address, (folded, folded, ones));
    }

    fn restore(
        &self,
        stage: &mut Stage<'_>,
        (slot, dirty): (usize, u32),
    ) -> Result<(), Error> {
        let [store, _, _, _, _, _, _] = self.sites;
        let ones = current_profile().eof_word().div_euclid(2);
        let mask = self.raw_mask(slot)?;
        let pointer = *self
            .route
            .raw_pointers
            .get(slot)
            .ok_or(Error::InvalidTransitionBinding)?;
        let constant = *self
            .route
            .raw_reset_constants
            .get(slot)
            .ok_or(Error::InvalidTransitionBinding)?;
        let [prefix, seed] = *self
            .route
            .raw_restore_words
            .get(slot)
            .ok_or(Error::InvalidTransitionBinding)?;
        let inverse = crazy(ones, mask);
        let prefix_value = crazy(0, inverse).saturating_mul(2);
        self.reset(stage, (pointer, constant, dirty));
        stage.fold(store, prefix, (prefix_value, ones, prefix_value));
        stage.fold(store, seed, (inverse, prefix_value, inverse));
        stage.fold(store, pointer, (ones, inverse, mask));
        Ok(())
    }

    fn steps(
        &self,
        source: SourceTransitionValue,
        lookup: &[LookupExpectation; 5],
    ) -> Result<Vec<RouteEffect>, Error> {
        let [_, rotate, _, _, _, load, _] = self.sites;
        let [low, _] = self.words;
        let [raw_low, carry, raw_high, _, _] = lookup;
        let [_, carry_c, _, _, low_c] = self.route.lookup_constants;
        let ones = current_profile().eof_word().div_euclid(2);
        let [low_encoding, high_encoding] = self.encoding;
        let prior_low = *low_encoding
            .get(usize::from(source.prior_state & 15))
            .ok_or(Error::InvalidTransitionBinding)?;
        let prior_high = *high_encoding
            .get(usize::from(source.prior_state >> 4u32))
            .ok_or(Error::InvalidTransitionBinding)?;
        let mut effects = Vec::with_capacity(EFFECT_COUNT);
        let ready =
            self.prepare_low(&mut effects, u32::from(source.raw_byte), lookup)?;
        let mut low_stage = Stage {
            effects: &mut effects,
            lookups: 4,
        };
        low_stage.fold(
            load,
            low,
            (prior_low, raw_low.value, carry.address.saturating_sub(1)),
        );
        low_stage.uniform(rotate, carry_c, ones);
        let partial = crazy(prior_high, carry.value);
        self.prepare_high(&mut effects, (ready, prior_high, partial), lookup)?;
        let mut stage = Stage {
            effects: &mut effects,
            lookups: 16,
        };
        stage.uniform(rotate, low_c, ones);
        stage.lookups = 21;
        self.reset(
            &mut stage,
            (self.capture, self.route.capture_reset_constant, ready),
        );
        self.restore(&mut stage, (0, raw_low.address.saturating_sub(1)))?;
        self.restore(&mut stage, (1, raw_high.address.saturating_sub(1)))?;
        if effects.len() != EFFECT_COUNT {
            return Err(Error::InvalidTransitionBinding);
        }
        Ok(effects)
    }
}

pub(super) struct RouteTrace {
    dispatched: bool,
    effects: Vec<RouteEffect>,
    indices: RouteIndices,
    position: usize,
}

impl RouteTrace {
    pub(super) fn dispatch(
        &mut self,
        geometry: &RouteGeometry,
        trace: &ProfileStepTrace,
    ) -> Result<bool, Error> {
        if self.dispatched {
            return Ok(true);
        }
        if trace.before.registers.code_pointer == geometry.branch
            && trace.decoded == Some(b'j')
        {
            if trace.after.registers.data_pointer != geometry.byte_landing {
                return Err(Error::GuestTransitionMismatch);
            }
            self.dispatched = true;
        }
        Ok(false)
    }

    pub(super) fn finish(self) -> Result<RouteIndices, Error> {
        if !self.dispatched || self.position != self.effects.len() {
            return Err(Error::GuestTransitionMismatch);
        }
        Ok(self.indices)
    }

    pub(super) fn new(
        geometry: &RouteGeometry,
        source: SourceTransitionValue,
        lookup: &[LookupExpectation; 5],
    ) -> Result<Self, Error> {
        Ok(Self {
            dispatched: false,
            effects: geometry.steps(source, lookup)?,
            indices: [0; EFFECT_COUNT],
            position: 0,
        })
    }

    pub(super) fn observe(
        &mut self,
        lookups: usize,
        trace: &ProfileStepTrace,
        index: usize,
    ) -> Result<(), Error> {
        let effect = self
            .effects
            .get(self.position)
            .ok_or(Error::GuestTransitionMismatch)?;
        if effect.after_lookups != lookups {
            return Err(Error::GuestTransitionMismatch);
        }
        let _value = effect.expected.verify(trace)?;
        *self
            .indices
            .get_mut(self.position)
            .ok_or(Error::GuestTransitionMismatch)? = index;
        self.position = self.position.saturating_add(1);
        Ok(())
    }

    pub(super) fn require_before_lookup(
        &self,
        lookups: usize,
    ) -> Result<(), Error> {
        if self
            .effects
            .get(self.position)
            .is_some_and(|effect| effect.after_lookups <= lookups)
        {
            return Err(Error::GuestTransitionMismatch);
        }
        Ok(())
    }
}
