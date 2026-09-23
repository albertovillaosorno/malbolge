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
//   - Transactional process-local preparation of sealed verified AOT sets.
// - Must-Not:
//   - Publish partial sets, admit deoptimization stubs, execute native code, or
//   - infer state-graph transitions.
// - Allows:
//   - Inputs: exact portable region variants, runtime capability, and host.
//   - Outputs: one read-only set containing every unique verified fast path.
//   - Side effects: process-local allocation only.
// - Split-When:
//   - Durable serialization/loading or graph-transition admission gains
//   - independent ownership.
// - Merge-When:
//   - Native planning itself becomes transactionally AOT-only.
// - Summary:
//   - Builds all requested direct variants before exposing an immutable AOT
//     set.
// - Description:
//   - Verifies every variant, deduplicates exact keys, and fails atomically.
// - Usage:
//   - Called by offline or startup preparation before guest execution.
// - Defaults:
//   - Empty input, deoptimization-only variants, and any failed step fail
//     closed.
//

//! Transactional process-local preparation of verified AOT artifact sets.

use super::plan::prepare_verified_direct_target;
use super::{
    Arc, DirectHost, DirectSelectionError, Display, FormatResult, Formatter,
    RegionEffectProgram, RuntimeCapability, VerifiedAheadOfExecutionNativeSet,
    VerifiedDirectNativeCache,
};

/// Failure while preparing one complete process-local AOT artifact set.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum AheadOfExecutionPreparationError<'requirement> {
    /// One variant has no reviewed direct fast path.
    Deoptimization {
        /// Zero-based variant position that selected deoptimization.
        index: usize,
    },
    /// At least one reachable variant must be supplied.
    Empty,
    /// One variant failed profile, target, emission, or verification checks.
    Step {
        /// Zero-based failing variant position.
        index: usize,
        /// Exact direct-selection failure.
        error: Box<DirectSelectionError<'requirement>>,
    },
}

impl Display for AheadOfExecutionPreparationError<'_> {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::Empty => f.write_str(
                "ahead-of-execution preparation requires at least one variant",
            ),
            Self::Deoptimization { index } => write!(
                f,
                "ahead-of-execution variant {index} has no direct fast path"
            ),
            Self::Step { error, index } => {
                write!(f, "ahead-of-execution variant {index} failed: {error}")
            },
        }
    }
}

/// Prepares every exact reachable variant and seals the result for runtime use.
///
/// Exact duplicate artifact keys are emitted once. No caller-visible set exists
/// until every requested variant has passed profile preflight, direct fast-path
/// selection, native emission, and semantic verification.
///
/// # Errors
///
/// Returns `AheadOfExecutionPreparationError` for empty input, any variant
/// that only admits the deoptimization stub, or any failed direct selection.
/// Failure
/// discards the local preparation cache rather than publishing a partial AOT
/// set.
pub fn prepare_ahead_of_execution_native_set<'requirement>(
    programs: &'requirement [RegionEffectProgram],
    runtime: &'static RuntimeCapability,
    host: DirectHost,
) -> Result<
    VerifiedAheadOfExecutionNativeSet,
    AheadOfExecutionPreparationError<'requirement>,
> {
    prepare_ahead_of_execution_native_set_iter(programs.iter(), runtime, host)
}

pub(super) fn prepare_ahead_of_execution_native_set_iter<
    'requirement,
    Programs,
>(
    programs: Programs,
    runtime: &'static RuntimeCapability,
    host: DirectHost,
) -> Result<
    VerifiedAheadOfExecutionNativeSet,
    AheadOfExecutionPreparationError<'requirement>,
>
where
    Programs: IntoIterator<Item = &'requirement RegionEffectProgram>,
{
    let mut cache = VerifiedDirectNativeCache::default();
    let mut observed = false;
    for (index, program) in programs.into_iter().enumerate() {
        observed = true;
        let prepared = prepare_verified_direct_target(
            program,
            runtime,
            host.operating_system,
            host.isa,
        )
        .map_err(|error| AheadOfExecutionPreparationError::Step {
            index,
            error: Box::new(error),
        })?;
        if prepared.is_deoptimization() {
            return Err(AheadOfExecutionPreparationError::Deoptimization {
                index,
            });
        }
        if cache.entries.get(prepared.key()).is_some() {
            continue;
        }

        let key = prepared.key().clone();
        let artifact =
            Arc::new(prepared.emit_verified(program).map_err(|error| {
                AheadOfExecutionPreparationError::Step {
                    index,
                    error: Box::new(error),
                }
            })?);
        let _replaced = cache.entries.insert(key, artifact);
    }
    if observed {
        Ok(cache.seal())
    } else {
        Err(AheadOfExecutionPreparationError::Empty)
    }
}
