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
//   - Exact JIT performance-promotion policy regressions.
// - Must-Not:
//   - Benchmark wall time or claim host speedup from synthetic evidence.
// - Allows:
//   - Inputs: deterministic aggregate latency evidence and cohort identities.
//   - Outputs: exact promotion or interpreter policy assertions.
//   - Side effects: none.
// - Split-When:
//   - Host-real policy benchmarks gain an independent fixture lifecycle.
// - Merge-When:
//   - Tiered-execution policy tests own this exact gate.
// - Summary:
//   - Proves the hard 1.1x JIT promotion floor and fail-closed evidence rules.
// - Description:
//   - Exercises exact rational comparison without wall-clock flakiness.
// - Usage:
//   - Runs as an auto-discovered Cargo integration test.
// - Defaults:
//   - Weak, mismatched, insufficient, or overflowing evidence stays
//     interpreted.
//

//! Deterministic JIT performance-promotion policy evidence.

#[path = "../src/runtime/tiered-execution/composition/tier/performance_gate.rs"]
pub mod performance_gate;

use std::num::{NonZeroU64, NonZeroU128, NonZeroUsize};

use malbolge as _;
use performance_gate::{
    NativeTierJitPromotionAssessment as Assessment,
    NativeTierJitPromotionBlock as Block,
    NativeTierJitPromotionPolicy as Policy,
    NativeTierJitPromotionPolicyError as PolicyError,
    NativeTierPerformanceBoundary as Boundary,
    NativeTierPerformanceEvidence as Evidence, assess_jit_promotion,
};

const COHORT: [u8; 32] = [0x5a; 32];
const OTHER_COHORT: [u8; 32] = [0xa5; 32];

fn evidence(
    boundary: Boundary,
    cohort: [u8; 32],
    samples: usize,
    total_nanoseconds: u128,
) -> Result<Evidence, String> {
    Ok(Evidence::new(
        boundary,
        cohort,
        nonzero_usize(samples)?,
        nonzero_u128(total_nanoseconds)?,
    ))
}

fn nonzero_u128(value: u128) -> Result<NonZeroU128, String> {
    NonZeroU128::new(value)
        .ok_or_else(|| String::from("test u128 must be nonzero"))
}

fn nonzero_u64(value: u64) -> Result<NonZeroU64, String> {
    NonZeroU64::new(value)
        .ok_or_else(|| String::from("test u64 must be nonzero"))
}

fn nonzero_usize(value: usize) -> Result<NonZeroUsize, String> {
    NonZeroUsize::new(value)
        .ok_or_else(|| String::from("test usize must be nonzero"))
}

#[test]
fn arithmetic_overflow_stays_interpreted() -> Result<(), String> {
    let maximum = NonZeroU128::MAX;
    let samples = nonzero_usize(15)?;
    let interpreter =
        Evidence::new(Boundary::Interpreter, COHORT, samples, maximum);
    let native =
        Evidence::new(Boundary::InProcessNative, COHORT, samples, maximum);
    let policy = Policy::minimum(samples);
    let expected = Assessment::Interpreter {
        reason: Block::ArithmeticOverflow,
    };
    if assess_jit_promotion(interpreter, native, policy) != expected {
        return Err(String::from("overflowing evidence promoted JIT"));
    }
    Ok(())
}

#[test]
fn exact_one_point_one_speedup_promotes_jit() -> Result<(), String> {
    let interpreter = evidence(Boundary::Interpreter, COHORT, 15, 16_500)?;
    let native = evidence(Boundary::InProcessNative, COHORT, 15, 15_000)?;
    let policy = Policy::minimum(nonzero_usize(15)?);
    if assess_jit_promotion(interpreter, native, policy) != Assessment::Promote
    {
        return Err(String::from("exact 1.1x speedup did not promote JIT"));
    }
    Ok(())
}

#[test]
fn jit_policy_enforces_repository_speedup_floor() -> Result<(), String> {
    let samples = nonzero_usize(15)?;
    let rejected = Policy::new(samples, nonzero_u64(109)?, nonzero_u64(100)?);
    if rejected != Err(PolicyError::BelowMinimumSpeedup) {
        return Err(String::from("sub-1.1x JIT policy was admitted"));
    }
    let exact = Policy::minimum(samples);
    if exact.minimum_speedup_numerator().get() != 11
        || exact.minimum_speedup_denominator().get() != 10
    {
        return Err(String::from("minimum JIT policy drifted from 11/10"));
    }
    let stricter = Policy::new(samples, nonzero_u64(3)?, nonzero_u64(2)?);
    if stricter.is_err() {
        return Err(String::from("stricter JIT policy was rejected"));
    }
    Ok(())
}

#[test]
fn marginal_native_speedup_stays_interpreted() -> Result<(), String> {
    let interpreter = evidence(Boundary::Interpreter, COHORT, 15, 16_499)?;
    let native = evidence(Boundary::InProcessNative, COHORT, 15, 15_000)?;
    let policy = Policy::minimum(nonzero_usize(15)?);
    let expected = Assessment::Interpreter {
        reason: Block::BelowMinimumSpeedup,
    };
    if assess_jit_promotion(interpreter, native, policy) != expected {
        return Err(String::from("sub-1.1x evidence promoted JIT"));
    }
    Ok(())
}

#[test]
fn mismatched_cohort_identity_stays_interpreted() -> Result<(), String> {
    let interpreter = evidence(Boundary::Interpreter, COHORT, 15, 16_500)?;
    let native = evidence(Boundary::InProcessNative, OTHER_COHORT, 15, 15_000)?;
    let policy = Policy::minimum(nonzero_usize(15)?);
    let expected = Assessment::Interpreter {
        reason: Block::CohortMismatch,
    };
    if assess_jit_promotion(interpreter, native, policy) != expected {
        return Err(String::from("mismatched cohort promoted JIT"));
    }
    Ok(())
}

#[test]
fn process_native_speedup_never_authorizes_jit() -> Result<(), String> {
    let policy = Policy::minimum(nonzero_usize(15)?);
    let assessment = assess_jit_promotion(
        evidence(Boundary::Interpreter, COHORT, 15, 30_000)?,
        evidence(Boundary::ProcessNative, COHORT, 15, 10_000)?,
        policy,
    );
    let expected = Assessment::Interpreter {
        reason: Block::ExecutionBoundaryMismatch,
    };
    if assessment != expected {
        return Err(String::from(
            "process-native speedup crossed the in-process JIT boundary",
        ));
    }
    Ok(())
}

#[test]
fn retained_two_step_process_totals_stay_interpreted() -> Result<(), String> {
    let policy = Policy::minimum(nonzero_usize(15)?);
    let retained = [
        ([1; 32], 34_236, 466_215),
        ([2; 32], 46_159, 755_040),
        ([4; 32], 64_447, 1_538_451),
    ];
    for (cohort, interpreter_total, native_total) in retained {
        let assessment = assess_jit_promotion(
            evidence(Boundary::Interpreter, cohort, 15, interpreter_total)?,
            evidence(Boundary::ProcessNative, cohort, 15, native_total)?,
            policy,
        );
        let expected = Assessment::Interpreter {
            reason: Block::ExecutionBoundaryMismatch,
        };
        if assessment != expected {
            return Err(String::from(
                "retained process evidence crossed the in-process JIT boundary",
            ));
        }
    }
    Ok(())
}

#[test]
fn weak_or_unpaired_samples_stay_interpreted() -> Result<(), String> {
    let policy = Policy::minimum(nonzero_usize(15)?);
    let insufficient = assess_jit_promotion(
        evidence(Boundary::Interpreter, COHORT, 14, 15_400)?,
        evidence(Boundary::InProcessNative, COHORT, 14, 14_000)?,
        policy,
    );
    let expected_insufficient = Assessment::Interpreter {
        reason: Block::InsufficientSamples,
    };
    if insufficient != expected_insufficient {
        return Err(String::from("insufficient evidence promoted JIT"));
    }
    let unpaired = assess_jit_promotion(
        evidence(Boundary::Interpreter, COHORT, 16, 17_600)?,
        evidence(Boundary::InProcessNative, COHORT, 15, 15_000)?,
        policy,
    );
    let expected_unpaired = Assessment::Interpreter {
        reason: Block::SampleCountMismatch,
    };
    if unpaired != expected_unpaired {
        return Err(String::from("unpaired evidence promoted JIT"));
    }
    Ok(())
}
