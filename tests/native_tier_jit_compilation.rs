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
//   - Focused bounded JIT compiler-port/application fallback regressions.
// - Must-Not:
//   - Execute native code or claim semantic admission of fake artifacts.
// - Allows:
//   - Inputs: deterministic fake compiler outcomes and positive budgets.
//   - Outputs: exact candidate/fallback assertions.
//   - Side effects: test-process mutation only.
// - Split-When:
//   - A production JIT adapter gains an independent lifecycle fixture.
// - Merge-When:
//   - Tiered execution tests own the same bounded compilation use case.
// - Summary:
//   - Proves compiler-side budgets fail closed before artifact admission.
// - Description:
//   - Rechecks reported time/size and preserves every fallback reason.
// - Usage:
//   - Runs as an auto-discovered Cargo integration test.
// - Defaults:
//   - No fake outcome is trusted beyond the application recheck.
//

//! Bounded JIT compilation port/application contract evidence.

#[path = "../src/runtime/tiered-execution/application/jit_compilation.rs"]
pub mod jit_compilation;
#[path = "../src/runtime/tiered-execution/port-outbound/jit_compiler.rs"]
pub mod jit_compiler_port;

use std::num::{NonZeroU64, NonZeroUsize};

use jit_compilation::{
    NativeTierJitCompilationAttempt as Attempt,
    NativeTierJitCompilationFallback as Fallback, attempt_jit_compilation,
};
use jit_compiler_port::{
    NativeTierJitCompilationBudget as Budget,
    NativeTierJitCompilationRequest as Request, NativeTierJitCompiler,
    NativeTierJitCompilerOutcome as Outcome,
};
use malbolge as _;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum FakeCompilerError {
    Failed,
}

#[derive(Clone, Debug, Eq, PartialEq)]
enum FakeCompilerOutcome {
    BudgetExhausted(u64),
    Cancelled,
    Compiled {
        artifact: Vec<u8>,
        elapsed_nanoseconds: u64,
        object_bytes: usize,
    },
    Error,
    Unsupported,
}

#[derive(Debug)]
struct FakeCompiler {
    calls: usize,
    expected_identity: u64,
    observed_budget: Option<Budget>,
    outcome: FakeCompilerOutcome,
}

impl NativeTierJitCompiler<u64, Vec<u8>, FakeCompilerError> for FakeCompiler {
    fn compile(
        &mut self,
        request: Request<'_, u64>,
    ) -> Result<Outcome<Vec<u8>>, FakeCompilerError> {
        self.calls = self.calls.saturating_add(1);
        if *request.identity != self.expected_identity {
            return Err(FakeCompilerError::Failed);
        }
        self.observed_budget = Some(request.budget);
        match &self.outcome {
            FakeCompilerOutcome::BudgetExhausted(elapsed_nanoseconds) => {
                Ok(Outcome::BudgetExhausted {
                    elapsed_nanoseconds: *elapsed_nanoseconds,
                })
            },
            FakeCompilerOutcome::Cancelled => Ok(Outcome::Cancelled),
            FakeCompilerOutcome::Compiled {
                artifact,
                elapsed_nanoseconds,
                object_bytes,
            } => Ok(Outcome::Compiled {
                artifact: artifact.clone(),
                elapsed_nanoseconds: *elapsed_nanoseconds,
                object_bytes: *object_bytes,
            }),
            FakeCompilerOutcome::Error => Err(FakeCompilerError::Failed),
            FakeCompilerOutcome::Unsupported => Ok(Outcome::Unsupported),
        }
    }
}

const fn budget() -> Budget {
    Budget {
        maximum_nanoseconds: NonZeroU64::MIN,
        maximum_object_bytes: NonZeroUsize::MIN,
    }
}

const fn compiler(outcome: FakeCompilerOutcome) -> FakeCompiler {
    FakeCompiler {
        calls: 0,
        expected_identity: 7,
        observed_budget: None,
        outcome,
    }
}

#[test]
fn bounded_jit_candidate_preserves_exact_request() {
    let budget = Budget {
        maximum_nanoseconds: NonZeroU64::new(50).unwrap_or(NonZeroU64::MIN),
        maximum_object_bytes: NonZeroUsize::new(64)
            .unwrap_or(NonZeroUsize::MIN),
    };
    let mut compiler = compiler(FakeCompilerOutcome::Compiled {
        artifact: vec![1, 2, 3],
        elapsed_nanoseconds: 49,
        object_bytes: 64,
    });
    let attempt = attempt_jit_compilation(&mut compiler, &7, budget);
    assert_eq!(attempt, Attempt::Candidate {
        artifact: vec![1, 2, 3],
        elapsed_nanoseconds: 49,
        object_bytes: 64,
    });
    assert_eq!(compiler.calls, 1);
    assert_eq!(compiler.observed_budget, Some(budget));
}

#[test]
fn compiler_non_candidate_outcomes_stay_interpreted() {
    let cases = [
        (
            FakeCompilerOutcome::BudgetExhausted(1),
            Fallback::BudgetExhausted { elapsed_nanoseconds: 1 },
        ),
        (FakeCompilerOutcome::Cancelled, Fallback::Cancelled),
        (
            FakeCompilerOutcome::Error,
            Fallback::Compiler(FakeCompilerError::Failed),
        ),
        (FakeCompilerOutcome::Unsupported, Fallback::Unsupported),
    ];
    for (outcome, expected) in cases {
        let mut compiler = compiler(outcome);
        assert_eq!(
            attempt_jit_compilation(&mut compiler, &7, budget()),
            Attempt::Interpreter { reason: expected }
        );
    }
}

#[test]
fn compiled_claim_over_latency_limit_stays_interpreted() {
    let mut compiler = compiler(FakeCompilerOutcome::Compiled {
        artifact: vec![1],
        elapsed_nanoseconds: 2,
        object_bytes: 1,
    });
    assert_eq!(
        attempt_jit_compilation(&mut compiler, &7, budget()),
        Attempt::Interpreter {
            reason: Fallback::LatencyLimit {
                maximum_nanoseconds: NonZeroU64::MIN,
                observed_nanoseconds: 2,
            },
        }
    );
}

#[test]
fn compiled_claim_over_object_limit_stays_interpreted() {
    let mut compiler = compiler(FakeCompilerOutcome::Compiled {
        artifact: vec![1, 2],
        elapsed_nanoseconds: 1,
        object_bytes: 2,
    });
    assert_eq!(
        attempt_jit_compilation(&mut compiler, &7, budget()),
        Attempt::Interpreter {
            reason: Fallback::ObjectByteLimit {
                maximum_bytes: NonZeroUsize::MIN,
                observed_bytes: 2,
            },
        }
    );
}
