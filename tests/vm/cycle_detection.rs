// Copyright:
//   - Copyright (c) 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - MIT
// Confidential:
//   - false
// License-File:
//   - LICENSE-MIT
//
// Boundary-Contract:
// - Owns:
//   - Exact and diagnostic repeated-state detector regression evidence.
// - Must-Not:
//   - Accept key collisions as exact VM-state repetition.
// - Allows:
//   - Inputs: classic checkpoints and deliberately colliding diagnostic keys.
//   - Outputs: exact-repeat and possible-repeat classifications.
//   - Side effects: test-local allocations only.
// - Split-When:
//   - Split when profile-specific cycle fixtures gain independent ownership.
// - Merge-When:
//   - Merge when another VM test owns identical collision-boundary evidence.
// - Summary:
//   - Proves that only complete checkpoint equality authorizes exact cycles.
// - Description:
//   - Forces key collisions and deterministic replay over real VM states.
// - Usage:
//   - Executed by the Cargo `vm` integration-test target.
// - Defaults:
//   - Diagnostic repetition remains explicitly unproved.
//

//! Exact and diagnostic cycle-detection regression evidence.

use malbolge::{
    DiagnosticCycleDetector, DiagnosticCycleObservation, ExactCycleDetector,
    ExactCycleObservation, Machine, MachineState, ProfileMachine,
    ProfileMachineState, StepOutcome, Word, historical_profile,
};

use super::{TestResult, check_equal, normalize_result};

const COLLIDING_KEY: u8 = 7;

fn classic_checkpoints() -> TestResult<(MachineState, MachineState)> {
    let mut machine =
        normalize_result(Machine::from_source(b"ubO", Vec::new()))?;
    let initial = machine.snapshot_state();
    let _: StepOutcome = normalize_result(machine.step())?;
    Ok((initial, machine.snapshot_state()))
}

fn mutated_classic_checkpoint(seed: u8) -> TestResult<MachineState> {
    let machine = normalize_result(Machine::from_source(b"ubO", Vec::new()))?;
    let state = machine.snapshot_state();
    let mut registers = state.registers();
    registers.accumulator = Word::from_byte(seed);
    Ok(MachineState::new(
        state.memory().clone(),
        registers,
        state.io().clone(),
    ))
}

fn profile_checkpoints()
-> TestResult<(ProfileMachineState, ProfileMachineState)> {
    let mut machine = normalize_result(ProfileMachine::from_source(
        historical_profile(),
        b"ubO",
        Vec::new(),
    ))?;
    let initial = machine.snapshot_state();
    let _: StepOutcome = normalize_result(machine.step())?;
    Ok((initial, machine.snapshot_state()))
}

fn replay_exact_observations() -> TestResult<Vec<ExactCycleObservation>> {
    let (initial, advanced) = classic_checkpoints()?;
    let mut detector = ExactCycleDetector::new();
    [
        detector.observe(COLLIDING_KEY, initial.clone()),
        detector.observe(COLLIDING_KEY, advanced.clone()),
        detector.observe(COLLIDING_KEY, initial),
        detector.observe(COLLIDING_KEY, advanced),
    ]
    .into_iter()
    .map(normalize_result)
    .collect()
}

#[test]
fn exact_detector_confirms_checkpoint_after_key_collision() -> TestResult {
    let observations = replay_exact_observations()?;
    check_equal(
        &observations,
        &vec![
            ExactCycleObservation::Unique { observed_at: 0 },
            ExactCycleObservation::Unique { observed_at: 1 },
            ExactCycleObservation::ExactRepeat {
                first_seen: 0,
                repeated_at: 2,
            },
            ExactCycleObservation::ExactRepeat {
                first_seen: 1,
                repeated_at: 3,
            },
        ],
        "collision-safe exact observations",
    )?;
    let (initial, advanced) = classic_checkpoints()?;
    let mut detector = ExactCycleDetector::new();
    let _: ExactCycleObservation =
        normalize_result(detector.observe(COLLIDING_KEY, initial))?;
    let _: ExactCycleObservation =
        normalize_result(detector.observe(COLLIDING_KEY, advanced))?;
    check_equal(
        &detector.retained_state_count(),
        &2,
        "distinct full states retained under one key",
    )
}

#[test]
fn exact_detector_rejects_seeded_state_mutation() -> TestResult {
    let original = normalize_result(Machine::from_source(b"ubO", Vec::new()))?
        .snapshot_state();
    let mutated = mutated_classic_checkpoint(19)?;
    let mut detector = ExactCycleDetector::new();
    let first =
        normalize_result(detector.observe(COLLIDING_KEY, original.clone()))?;
    let mutation = normalize_result(detector.observe(COLLIDING_KEY, mutated))?;
    let repeat = normalize_result(detector.observe(COLLIDING_KEY, original))?;
    check_equal(
        &[first, mutation, repeat],
        &[
            ExactCycleObservation::Unique { observed_at: 0 },
            ExactCycleObservation::Unique { observed_at: 1 },
            ExactCycleObservation::ExactRepeat {
                first_seen: 0,
                repeated_at: 2,
            },
        ],
        "seeded mutation rejection",
    )
}

#[test]
fn exact_detector_supports_profile_checkpoints() -> TestResult {
    let (initial, advanced) = profile_checkpoints()?;
    let mut detector = ExactCycleDetector::new();
    let first =
        normalize_result(detector.observe(COLLIDING_KEY, initial.clone()))?;
    let collision =
        normalize_result(detector.observe(COLLIDING_KEY, advanced))?;
    let repeat = normalize_result(detector.observe(COLLIDING_KEY, initial))?;
    check_equal(
        &[first, collision, repeat],
        &[
            ExactCycleObservation::Unique { observed_at: 0 },
            ExactCycleObservation::Unique { observed_at: 1 },
            ExactCycleObservation::ExactRepeat {
                first_seen: 0,
                repeated_at: 2,
            },
        ],
        "profile checkpoint cycle classification",
    )
}

#[test]
fn exact_detector_replay_is_deterministic() -> TestResult {
    check_equal(
        &replay_exact_observations()?,
        &replay_exact_observations()?,
        "exact detector deterministic replay",
    )
}

#[test]
fn diagnostic_detector_never_claims_exact_repetition() -> TestResult {
    let mut detector = DiagnosticCycleDetector::new();
    let first = normalize_result(detector.observe(COLLIDING_KEY))?;
    let second = normalize_result(detector.observe(COLLIDING_KEY))?;
    check_equal(
        &[first, second],
        &[
            DiagnosticCycleObservation::Unique { observed_at: 0 },
            DiagnosticCycleObservation::PossibleRepeat {
                first_seen: 0,
                repeated_at: 1,
            },
        ],
        "hash-only detector classifications",
    )?;
    check_equal(
        &detector.retained_key_count(),
        &1,
        "diagnostic key retention",
    )
}
