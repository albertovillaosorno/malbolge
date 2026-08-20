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
//   - Exact agreement verification across labeled backend observations.
// - Must-Not:
//   - Infer equivalence from hashes, partial state, or backend authority.
// - Allows:
//   - Inputs: at least two labeled observations of one semantic case.
//   - Outputs: exact agreement or deterministic mismatch diagnostics.
//   - Side effects: none.
// - Split-When:
//   - Split when persistent evidence transport needs an independent schema.
// - Merge-When:
//   - Merge when another VM module owns identical candidate agreement rules.
// - Summary:
//   - Compares complete backend observations against one explicit reference.
// - Description:
//   - Rejects missing peers and names the first exact mismatch
//     deterministically.
// - Usage:
//   - Used by Rust/C and optional accelerator differential verification.
// - Defaults:
//   - The first candidate is the reference, never implicit semantic authority.
//

//! Exact labeled-candidate differential verification.

use std::fmt::{Display, Formatter, Result as FormatResult};

/// One labeled semantic observation supplied to differential verification.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct DifferentialCandidate<Backend, Observation> {
    backend: Backend,
    observation: Observation,
}

impl<Backend, Observation> DifferentialCandidate<Backend, Observation> {
    /// Returns the backend label attached to this observation.
    #[must_use]
    pub const fn backend(&self) -> &Backend {
        &self.backend
    }

    /// Constructs one labeled semantic observation.
    #[must_use]
    pub const fn new(backend: Backend, observation: Observation) -> Self {
        Self { backend, observation }
    }

    /// Returns the complete observation supplied by this backend.
    #[must_use]
    pub const fn observation(&self) -> &Observation {
        &self.observation
    }
}

/// Rejection returned by exact differential candidate verification.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum DifferentialVerificationError<Backend> {
    /// Fewer than two independent candidates were supplied.
    InsufficientCandidates {
        /// Exact number of supplied candidates.
        observed: usize,
    },
    /// One candidate differs from the explicit first reference observation.
    Mismatch {
        /// Backend whose observation first differed.
        candidate: Backend,
        /// Explicit first backend used as the reference.
        reference: Backend,
    },
}

impl<Backend> Display for DifferentialVerificationError<Backend>
where
    Backend: Display,
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::InsufficientCandidates { observed } => {
                f.write_str("differential verification requires at least 2 ")?;
                write!(f, "candidates; observed {observed}")
            },
            Self::Mismatch { candidate, reference } => {
                write!(
                    f,
                    "differential candidate {candidate} disagrees with "
                )?;
                write!(f, "reference {reference}")
            },
        }
    }
}

/// Verifies exact equality across at least two labeled observations.
///
/// The first candidate is the explicit comparison reference. No backend label
/// receives semantic authority from this ordering.
///
/// # Errors
///
/// Returns [`DifferentialVerificationError::InsufficientCandidates`] for fewer
/// than two observations, or [`DifferentialVerificationError::Mismatch`] for
/// the first complete observation that differs from the reference.
pub fn verify_differential_candidates<Backend, Observation>(
    candidates: &[DifferentialCandidate<Backend, Observation>],
) -> Result<(), DifferentialVerificationError<Backend>>
where
    Backend: Clone,
    Observation: Eq,
{
    let Some((reference, remaining)) = candidates.split_first() else {
        return Err(DifferentialVerificationError::InsufficientCandidates {
            observed: 0,
        });
    };
    if remaining.is_empty() {
        return Err(DifferentialVerificationError::InsufficientCandidates {
            observed: 1,
        });
    }
    for candidate in remaining {
        if candidate.observation != reference.observation {
            return Err(DifferentialVerificationError::Mismatch {
                candidate: candidate.backend.clone(),
                reference: reference.backend.clone(),
            });
        }
    }
    Ok(())
}
