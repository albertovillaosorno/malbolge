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
//   - Pure interpreter-relative evidence gating for JIT promotion.
// - Must-Not:
//   - Read clocks, benchmark workloads, compile code, or select AOT artifacts.
// - Allows:
//   - Inputs: equivalent interpreter/in-process-native latency evidence and
//     explicit policy.
//   - Outputs: one exact promote-or-interpreter assessment with stable reason.
//   - Side effects: none.
// - Split-When:
//   - Another native tier gains an independent performance-promotion policy.
// - Merge-When:
//   - Product tier selection owns measurement and promotion atomically.
// - Summary:
//   - Requires measured interpreter-relative speedup before JIT promotion.
// - Description:
//   - Exact rational comparison fails closed on weak or mismatched evidence.
// - Usage:
//   - Assess one hot-state cohort before enabling JIT dispatch for that cohort.
// - Defaults:
//   - JIT cannot be configured below a 1.1x interpreter-relative speedup.
//

//! Exact interpreter-relative performance gate for JIT promotion.

use std::num::{NonZeroU64, NonZeroU128, NonZeroUsize};

const MINIMUM_JIT_SPEEDUP_DENOMINATOR: u64 = 10;
const MINIMUM_JIT_SPEEDUP_NUMERATOR: u64 = 11;

/// Execution boundary represented by one aggregate latency observation.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeTierPerformanceBoundary {
    /// Native execution without a process/IPC boundary in the timed region.
    InProcessNative,
    /// Normative interpreter execution for the same exact cohort.
    Interpreter,
    /// Native execution whose timed region crosses the process/IPC boundary.
    ProcessNative,
}

/// Exact aggregate latency evidence for one benchmark cohort and boundary.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct NativeTierPerformanceEvidence {
    boundary: NativeTierPerformanceBoundary,
    cohort_identity: [u8; 32],
    samples: NonZeroUsize,
    total_nanoseconds: NonZeroU128,
}

/// Caller-owned JIT promotion policy with a repository-enforced speedup floor.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct NativeTierJitPromotionPolicy {
    minimum_speedup_denominator: NonZeroU64,
    minimum_speedup_numerator: NonZeroU64,
    required_samples: NonZeroUsize,
}

/// Invalid caller configuration for the JIT promotion gate.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeTierJitPromotionPolicyError {
    /// Requested speedup is below the repository hard floor of 1.1x.
    BelowMinimumSpeedup,
}

/// Why exact evidence did not authorize JIT promotion.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeTierJitPromotionBlock {
    /// Exact integer cross multiplication could not be represented in `u128`.
    ArithmeticOverflow,
    /// Native execution missed the configured interpreter-relative speedup.
    BelowMinimumSpeedup,
    /// Interpreter and native evidence do not describe the same exact cohort.
    CohortMismatch,
    /// Evidence does not compare interpreter with in-process native execution.
    ExecutionBoundaryMismatch,
    /// One or both evidence sets have not reached the positive sample gate.
    InsufficientSamples,
    /// Equivalent evidence has different sample counts.
    SampleCountMismatch,
}

/// Exact result of one JIT performance-promotion assessment.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeTierJitPromotionAssessment {
    /// JIT remains disabled and the interpreter stays authoritative.
    Interpreter {
        /// Stable reason that promotion was not admitted.
        reason: NativeTierJitPromotionBlock,
    },
    /// Equivalent evidence proves the configured minimum native speedup.
    Promote,
}

impl NativeTierJitPromotionPolicy {
    /// Constructs the repository-minimum 1.1x JIT promotion policy.
    #[must_use]
    pub fn minimum(required_samples: NonZeroUsize) -> Self {
        let numerator = NonZeroU64::new(MINIMUM_JIT_SPEEDUP_NUMERATOR)
            .unwrap_or(NonZeroU64::MIN);
        let denominator = NonZeroU64::new(MINIMUM_JIT_SPEEDUP_DENOMINATOR)
            .unwrap_or(NonZeroU64::MIN);
        Self {
            minimum_speedup_denominator: denominator,
            minimum_speedup_numerator: numerator,
            required_samples,
        }
    }

    /// Returns the exact minimum speedup denominator.
    #[must_use]
    pub const fn minimum_speedup_denominator(self) -> NonZeroU64 {
        self.minimum_speedup_denominator
    }

    /// Returns the exact minimum speedup numerator.
    #[must_use]
    pub const fn minimum_speedup_numerator(self) -> NonZeroU64 {
        self.minimum_speedup_numerator
    }

    /// Constructs a JIT policy no weaker than the repository 1.1x floor.
    ///
    /// # Errors
    ///
    /// Returns [`NativeTierJitPromotionPolicyError::BelowMinimumSpeedup`] when
    /// the requested exact ratio is below 11/10.
    pub fn new(
        required_samples: NonZeroUsize,
        minimum_speedup_numerator: NonZeroU64,
        minimum_speedup_denominator: NonZeroU64,
    ) -> Result<Self, NativeTierJitPromotionPolicyError> {
        let numerator = NonZeroU128::from(minimum_speedup_numerator).get();
        let denominator = NonZeroU128::from(minimum_speedup_denominator).get();
        let requested = numerator
            .saturating_mul(u128::from(MINIMUM_JIT_SPEEDUP_DENOMINATOR));
        let floor = denominator
            .saturating_mul(u128::from(MINIMUM_JIT_SPEEDUP_NUMERATOR));
        if requested < floor {
            return Err(NativeTierJitPromotionPolicyError::BelowMinimumSpeedup);
        }
        Ok(Self {
            minimum_speedup_denominator,
            minimum_speedup_numerator,
            required_samples,
        })
    }

    /// Returns the minimum observations required from each execution mode.
    #[must_use]
    pub const fn required_samples(self) -> NonZeroUsize {
        self.required_samples
    }
}

impl NativeTierPerformanceEvidence {
    /// Returns the exact execution boundary represented by this evidence.
    #[must_use]
    pub const fn boundary(self) -> NativeTierPerformanceBoundary {
        self.boundary
    }

    /// Returns the caller-bound exact cohort identity.
    #[must_use]
    pub const fn cohort_identity(self) -> [u8; 32] {
        self.cohort_identity
    }

    /// Constructs exact aggregate latency evidence for one canonical cohort.
    #[must_use]
    pub const fn new(
        boundary: NativeTierPerformanceBoundary,
        cohort_identity: [u8; 32],
        samples: NonZeroUsize,
        total_nanoseconds: NonZeroU128,
    ) -> Self {
        Self {
            boundary,
            cohort_identity,
            samples,
            total_nanoseconds,
        }
    }

    /// Returns the positive number of observations represented by this
    /// evidence.
    #[must_use]
    pub const fn samples(self) -> NonZeroUsize {
        self.samples
    }

    /// Returns the positive exact aggregate observed latency in nanoseconds.
    #[must_use]
    pub const fn total_nanoseconds(self) -> NonZeroU128 {
        self.total_nanoseconds
    }
}

/// Assesses equivalent interpreter/native evidence before JIT promotion.
#[must_use]
pub fn assess_jit_promotion(
    interpreter: NativeTierPerformanceEvidence,
    native: NativeTierPerformanceEvidence,
    policy: NativeTierJitPromotionPolicy,
) -> NativeTierJitPromotionAssessment {
    if interpreter.boundary() != NativeTierPerformanceBoundary::Interpreter
        || native.boundary() != NativeTierPerformanceBoundary::InProcessNative
    {
        return blocked(NativeTierJitPromotionBlock::ExecutionBoundaryMismatch);
    }
    if interpreter.cohort_identity() != native.cohort_identity() {
        return blocked(NativeTierJitPromotionBlock::CohortMismatch);
    }
    if interpreter.samples().get() < policy.required_samples().get()
        || native.samples().get() < policy.required_samples().get()
    {
        return blocked(NativeTierJitPromotionBlock::InsufficientSamples);
    }
    if interpreter.samples() != native.samples() {
        return blocked(NativeTierJitPromotionBlock::SampleCountMismatch);
    }
    let numerator = NonZeroU128::from(policy.minimum_speedup_numerator()).get();
    let denominator =
        NonZeroU128::from(policy.minimum_speedup_denominator()).get();
    let Some(native_weighted) =
        native.total_nanoseconds().get().checked_mul(numerator)
    else {
        return blocked(NativeTierJitPromotionBlock::ArithmeticOverflow);
    };
    let Some(interpreter_weighted) = interpreter
        .total_nanoseconds()
        .get()
        .checked_mul(denominator)
    else {
        return blocked(NativeTierJitPromotionBlock::ArithmeticOverflow);
    };
    if native_weighted <= interpreter_weighted {
        NativeTierJitPromotionAssessment::Promote
    } else {
        blocked(NativeTierJitPromotionBlock::BelowMinimumSpeedup)
    }
}

const fn blocked(
    reason: NativeTierJitPromotionBlock,
) -> NativeTierJitPromotionAssessment {
    NativeTierJitPromotionAssessment::Interpreter { reason }
}
