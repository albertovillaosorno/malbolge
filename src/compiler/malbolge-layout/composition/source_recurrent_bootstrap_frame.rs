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
//   - Mutable recurrent operand initialization and finite classifier closure.
// - Must-Not:
//   - Trust emitter classifier seeds or authorize complete SSA publication.
// - Allows:
//   - Inputs: admitted geometry and observed first-input operand values.
//   - Outputs: required mutable stores and closed classifier transitions.
//   - Side effects: none.
// - Split-When:
//   - Additional recurrent classifier shapes need distinct proofs.
// - Merge-When:
//   - A general source-frame verifier owns these recurrent operands.

use std::collections::{BTreeMap, BTreeSet};

use malbolge::{current_profile, profile_crazy};

use super::{
    Cell, Error, Expected, SourceRecurrentTransitionProbe, TablePlan, crazy,
    insert,
};

pub(super) struct ClassifierPlan {
    byte: u32,
    eof: [u32; 2],
    words: [u32; 6],
}

impl ClassifierPlan {
    pub(super) fn new(
        probe: &SourceRecurrentTransitionProbe<'_>,
        plan: &mut TablePlan,
    ) -> Result<Self, Error> {
        let guard = &probe.loop_probe.guard;
        let twos = current_profile().eof_word();
        let ones = twos.div_euclid(2);
        for address in [guard.capture_word, probe.output_scratch]
            .into_iter()
            .chain(probe.scratch_words)
        {
            insert(plan, address, Expected::Frame(ones))?;
        }
        let [raw_low, _, raw_high, _] = probe.tables;
        for (table, address) in [raw_low, raw_high]
            .into_iter()
            .zip(probe.route.raw_pointers)
        {
            insert(
                plan,
                address,
                Expected::Frame(crazy(table, twos).saturating_add(364)),
            )?;
        }
        for address in guard.classifier_words {
            insert(plan, address, Expected::Classifier)?;
        }
        Ok(Self {
            byte: guard
                .byte_landing
                .checked_sub(1)
                .ok_or(Error::InvalidTransitionBinding)?,
            eof: [
                guard.eof_landings[0]
                    .checked_sub(1)
                    .ok_or(Error::InvalidTransitionBinding)?,
                guard.eof_landings[1]
                    .checked_sub(1)
                    .ok_or(Error::InvalidTransitionBinding)?,
            ],
            words: guard.classifier_words,
        })
    }

    pub(super) fn verify(
        &self,
        cells: &BTreeMap<u32, Cell>,
    ) -> Result<(), Error> {
        let mut seeds = [0; 6];
        for (seed, address) in seeds.iter_mut().zip(self.words) {
            *seed = cells
                .get(&address)
                .ok_or(Error::GuestTransitionMismatch)?
                .value;
        }
        self.verify_seeds(seeds)
    }

    fn verify_seeds(&self, seeds: [u32; 6]) -> Result<(), Error> {
        // Crazy is digitwise. Prove a closed set of reachable six-word
        // states separately for every equal EOF digit. Keep both differing
        // EOF digits correlated: checking them separately would admit a
        // third, unauthorized landing from a mixed pair of digits.
        let mut varying = Vec::new();
        for index in 0..current_profile().word_trits() {
            let place = 3u32.pow(u32::from(index));
            let [first, second] = self.eof.map(|word| digit(word, place));
            if first == second {
                constant_digit(
                    seeds.map(|word| digit(word, place)),
                    place,
                    digit(self.byte, place),
                    first,
                )?;
            } else {
                varying.push(place);
            }
        }
        let [first, second] = varying.as_slice() else {
            return Err(Error::InvalidTransitionBinding);
        };
        // Both varying digits are above all byte digits. Their states
        // therefore advance synchronously on one encoded byte digit.
        if u8::try_from(*first).is_ok() || u8::try_from(*second).is_ok() {
            return Err(Error::InvalidTransitionBinding);
        }
        let places = [*first, *second];
        let state = places.map(|place| seeds.map(|word| digit(word, place)));
        let byte = places.map(|place| digit(self.byte, place));
        let eof = self.eof.map(|word| places.map(|place| digit(word, place)));
        correlated_digits(state, byte, eof)
    }
}

const fn digit(word: u32, place: u32) -> u32 {
    word.div_euclid(place).rem_euclid(3)
}

fn fold(mut state: [u32; 6], raw: u32) -> [u32; 6] {
    // The capture starts all-one, as separately required by the plan.
    let mut accumulator = profile_crazy(1, raw, 1);
    for word in &mut state {
        accumulator = profile_crazy(*word, accumulator, 1);
        *word = accumulator;
    }
    state
}

const fn last([_, _, _, _, _, result]: [u32; 6]) -> u32 {
    result
}

fn constant_digit(
    initial: [u32; 6],
    place: u32,
    byte: u32,
    eof: u32,
) -> Result<(), Error> {
    let mut seen = BTreeSet::new();
    let mut pending = vec![initial];
    // At any ternary position the digits of 0..=255 form a prefix
    // of 0,1,2. Explore their exact set; EOF always has digit two.
    let maximum = u32::from(u8::MAX).div_euclid(place).min(2);
    while let Some(state) = pending.pop() {
        if !seen.insert(state) {
            continue;
        }
        if last(fold(state, 2)) != eof {
            return Err(Error::GuestTransitionMismatch);
        }
        for raw in 0..=maximum {
            let next = fold(state, raw);
            if last(next) != byte {
                return Err(Error::GuestTransitionMismatch);
            }
            pending.push(next);
        }
    }
    Ok(())
}

fn correlated_digits(
    mut state: [[u32; 6]; 2],
    byte: [u32; 2],
    eof: [[u32; 2]; 2],
) -> Result<(), Error> {
    let mut seen = BTreeSet::new();
    let mut landings = BTreeSet::new();
    while seen.insert(state) {
        // The admitted shape has a short synchronous cycle; a larger
        // shape must provide another bounded proof, not stall replay.
        if seen.len() > 729 {
            return Err(Error::GuestTransitionMismatch);
        }
        let terminal = state.map(|words| last(fold(words, 2)));
        if !eof.contains(&terminal) {
            return Err(Error::GuestTransitionMismatch);
        }
        let _new = landings.insert(terminal);
        state = state.map(|words| fold(words, 0));
        if state.map(last) != byte {
            return Err(Error::GuestTransitionMismatch);
        }
    }
    if landings.len() != 2 {
        return Err(Error::GuestTransitionMismatch);
    }
    Ok(())
}

#[cfg(test)]
#[path = "../../../../tests/compiler/source_recurrent_bootstrap_frame.rs"]
mod tests;
