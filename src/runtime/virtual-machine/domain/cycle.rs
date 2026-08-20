// Copyright:
//   - Copyright © 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - MIT
// Confidential:
//   - false
// License-File:
//   - LICENSE-MIT
//
// Boundary-Contract:
// - Owns:
//   - Collision-safe repeated-state classification for caller-owned VM states.
// - Must-Not:
//   - Treat a lossy key collision as proof of semantic-state equality.
// - Allows:
//   - Inputs: stable candidate keys and immutable owned semantic states.
//   - Outputs: exact repeats or explicitly diagnostic possible repeats.
//   - Side effects: caller-owned in-memory detector state only.
// - Split-When:
//   - Split when persistent or distributed state retention needs its own port.
// - Merge-When:
//   - Merge when another VM module owns identical repeated-state semantics.
// - Summary:
//   - Separates exact full-state cycle proof from hash-only diagnostics.
// - Description:
//   - Uses keys only to select candidates and confirms exact repeats with Eq.
// - Usage:
//   - Used by bounded verification and future search/cycle tooling.
// - Defaults:
//   - Hash-only repetition is always reported as possible, never exact.
//

//! Collision-safe exact and explicitly diagnostic repeated-state detection.

use std::collections::HashMap;
use std::fmt::{Display, Formatter, Result as FormatResult};
use std::hash::Hash;

/// Failure to advance one detector's stable observation sequence.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum CycleDetectionError {
    /// The detector exhausted its stable `u64` observation index.
    ObservationIndexExhausted,
}

impl Display for CycleDetectionError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::ObservationIndexExhausted => {
                f.write_str("cycle observation index exhausted")
            },
        }
    }
}

/// Result of observing one complete semantic state.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ExactCycleObservation {
    /// A retained complete semantic state compares equal.
    ExactRepeat {
        /// Observation index of the first equal complete state.
        first_seen: u64,
        /// Observation index of this confirmed repetition.
        repeated_at: u64,
    },
    /// No equal complete state has been retained previously.
    Unique {
        /// Stable zero-based observation index.
        observed_at: u64,
    },
}

/// Result of observing one lossy diagnostic key.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum DiagnosticCycleObservation {
    /// The key appeared previously, but full-state equality was not checked.
    PossibleRepeat {
        /// Observation index of the first equal diagnostic key.
        first_seen: u64,
        /// Observation index of this possible repetition.
        repeated_at: u64,
    },
    /// The key has not appeared previously in this detector.
    Unique {
        /// Stable zero-based observation index.
        observed_at: u64,
    },
}

#[derive(Clone, Debug, Eq, PartialEq)]
struct ExactEntry<State> {
    first_seen: u64,
    state: State,
}

type ExactBuckets<Key, State> = HashMap<Key, Vec<ExactEntry<State>>>;

/// Retains complete states and confirms equality after candidate-key lookup.
#[derive(Clone, Debug)]
pub struct ExactCycleDetector<State, Key> {
    buckets: ExactBuckets<Key, State>,
    next_observation: u64,
}

impl<State, Key> ExactCycleDetector<State, Key>
where
    Key: Eq + Hash,
    State: Eq,
{
    /// Constructs an empty exact detector.
    #[must_use]
    pub fn new() -> Self {
        Self {
            buckets: HashMap::new(),
            next_observation: 0,
        }
    }

    /// Observes one complete semantic state under a caller-selected key.
    ///
    /// The key only selects candidate states. An exact repeat is returned only
    /// after comparing the complete retained state with [`Eq`].
    ///
    /// # Errors
    ///
    /// Returns [`CycleDetectionError::ObservationIndexExhausted`] before any
    /// mutation when the stable observation sequence cannot advance.
    pub fn observe(
        &mut self,
        key: Key,
        state: State,
    ) -> Result<ExactCycleObservation, CycleDetectionError> {
        let observed_at = advance_observation(&mut self.next_observation)?;
        let bucket = self.buckets.entry(key).or_default();
        if let Some(entry) = bucket.iter().find(|entry| entry.state == state) {
            return Ok(ExactCycleObservation::ExactRepeat {
                first_seen: entry.first_seen,
                repeated_at: observed_at,
            });
        }
        bucket.push(ExactEntry {
            first_seen: observed_at,
            state,
        });
        Ok(ExactCycleObservation::Unique { observed_at })
    }

    /// Returns the number of retained distinct complete states.
    #[must_use]
    pub fn retained_state_count(&self) -> usize {
        self.buckets.values().map(Vec::len).sum()
    }
}

impl<State, Key> Default for ExactCycleDetector<State, Key>
where
    Key: Eq + Hash,
    State: Eq,
{
    fn default() -> Self {
        Self::new()
    }
}

/// Retains only lossy keys and reports possible, never proven, repetition.
#[derive(Clone, Debug)]
pub struct DiagnosticCycleDetector<Key> {
    first_seen: HashMap<Key, u64>,
    next_observation: u64,
}

impl<Key> DiagnosticCycleDetector<Key>
where
    Key: Eq + Hash,
{
    /// Constructs an empty diagnostic detector.
    #[must_use]
    pub fn new() -> Self {
        Self {
            first_seen: HashMap::new(),
            next_observation: 0,
        }
    }

    /// Observes one lossy key without retaining or comparing semantic state.
    ///
    /// # Errors
    ///
    /// Returns [`CycleDetectionError::ObservationIndexExhausted`] before any
    /// mutation when the stable observation sequence cannot advance.
    pub fn observe(
        &mut self,
        key: Key,
    ) -> Result<DiagnosticCycleObservation, CycleDetectionError> {
        let observed_at = advance_observation(&mut self.next_observation)?;
        if let Some(first_seen) = self.first_seen.get(&key).copied() {
            return Ok(DiagnosticCycleObservation::PossibleRepeat {
                first_seen,
                repeated_at: observed_at,
            });
        }
        let _: Option<u64> = self.first_seen.insert(key, observed_at);
        Ok(DiagnosticCycleObservation::Unique { observed_at })
    }

    /// Returns the number of distinct diagnostic keys retained.
    #[must_use]
    pub fn retained_key_count(&self) -> usize {
        self.first_seen.len()
    }
}

impl<Key> Default for DiagnosticCycleDetector<Key>
where
    Key: Eq + Hash,
{
    fn default() -> Self {
        Self::new()
    }
}

fn advance_observation(
    next_observation: &mut u64,
) -> Result<u64, CycleDetectionError> {
    let observed_at = *next_observation;
    let advanced = observed_at
        .checked_add(1)
        .ok_or(CycleDetectionError::ObservationIndexExhausted)?;
    *next_observation = advanced;
    Ok(observed_at)
}
