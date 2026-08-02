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
//   - Seeded differential property between classic and profiled 1998 runtimes.
// - Must-Not:
//   - Share private transition helpers or treat the two APIs as one oracle.
// - Allows:
//   - Inputs: replayable valid fuzz cases and public runtime observation APIs.
//   - Outputs: step/state/memory equivalence or minimized replay diagnostics.
//   - Side effects: test-process memory only.
// - Split-When:
//   - Split when another canonical profile has an independent differential
//   - peer.
// - Merge-When:
//   - Merge when runtime representations become one width-safe implementation.
// - Summary:
//   - Replays generated programs through two public 1998 semantic surfaces.
// - Description:
//   - Compares every requested step and all 59,049 final memory words.
// - Usage:
//   - Runs under the deterministic property-verification Cargo target.
// - Defaults:
//   - Fixed seed and ordinal are sufficient to reproduce any generated case.
//

//! Seeded differential property over independently exposed 1998 runtimes.

use malbolge::{
    MEMORY_WORDS, Machine, MachineError, ProfileMachine, ProfileMachineError,
    StepOutcome, Termination, Word, historical_profile,
};

use crate::cases::{FuzzCase, default_seed, generate_case, shrink_candidates};

const CASE_COUNT: u32 = 24;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
struct StepObservation {
    continued: bool,
    pointer: Option<u32>,
    termination: Option<Termination>,
    value: Option<u32>,
}

impl StepObservation {
    const fn continued() -> Self {
        Self {
            continued: true,
            pointer: None,
            termination: None,
            value: None,
        }
    }

    const fn rejected(pointer: u32, value: u32) -> Self {
        Self {
            continued: false,
            pointer: Some(pointer),
            termination: None,
            value: Some(value),
        }
    }

    const fn stops(self) -> bool {
        !self.continued
    }

    const fn terminated(reason: Termination) -> Self {
        Self {
            continued: false,
            pointer: None,
            termination: Some(reason),
            value: None,
        }
    }
}

fn classic_step(machine: &mut Machine) -> Result<StepObservation, String> {
    match machine.step() {
        Ok(StepOutcome::Continued) => Ok(StepObservation::continued()),
        Ok(StepOutcome::Terminated(reason)) => {
            Ok(StepObservation::terminated(reason))
        },
        Err(MachineError::InvalidEncryptionTarget { pointer, value }) => {
            Ok(StepObservation::rejected(
                u32::from(pointer.value()),
                u32::from(value.value()),
            ))
        },
        Err(error) => Err(format!("unexpected classic step error: {error}")),
    }
}

fn profile_step(
    machine: &mut ProfileMachine,
) -> Result<StepObservation, String> {
    match machine.step() {
        Ok(StepOutcome::Continued) => Ok(StepObservation::continued()),
        Ok(StepOutcome::Terminated(reason)) => {
            Ok(StepObservation::terminated(reason))
        },
        Err(ProfileMachineError::InvalidEncryptionTarget {
            pointer,
            value,
        }) => Ok(StepObservation::rejected(pointer, value)),
        Err(error) => Err(format!("unexpected profile step error: {error}")),
    }
}

fn check_state(
    classic: &Machine,
    profiled: &ProfileMachine,
    context: &str,
) -> Result<(), String> {
    let classic_registers = classic.registers();
    let profile_registers = profiled.registers();
    let register_pair = (
        u32::from(classic_registers.accumulator.value()),
        u32::from(classic_registers.code_pointer.value()),
        u32::from(classic_registers.data_pointer.value()),
    );
    let expected_registers = (
        profile_registers.accumulator,
        profile_registers.code_pointer,
        profile_registers.data_pointer,
    );
    if register_pair != expected_registers {
        return Err(format!("{context}: registers differ"));
    }
    if classic.input_consumed() != profiled.input_consumed() {
        return Err(format!("{context}: input cursor mismatch"));
    }
    if classic.output() != profiled.output() {
        return Err(format!("{context}: output mismatch"));
    }
    if classic.termination() != profiled.termination() {
        return Err(format!("{context}: termination mismatch"));
    }
    Ok(())
}

fn check_memory(
    classic: &Machine,
    profiled: &ProfileMachine,
) -> Result<(), String> {
    for raw in 0..MEMORY_WORDS {
        let address_raw = u16::try_from(raw)
            .map_err(|error| format!("classic address conversion: {error}"))?;
        let address = Word::new(address_raw).map_err(|error| {
            format!("classic address construction: {error}")
        })?;
        let classic_value = classic
            .memory_word(address)
            .map_err(|error| format!("classic memory read: {error}"))?;
        let profile_address = u32::try_from(raw)
            .map_err(|error| format!("profile address conversion: {error}"))?;
        let profile_value = profiled
            .memory_word(profile_address)
            .map_err(|error| format!("profile memory read: {error}"))?;
        let classic_raw = u32::from(classic_value.value());
        if classic_raw != profile_value {
            return Err(format!(
                "memory address={raw}: {classic_raw} != {profile_value}"
            ));
        }
    }
    Ok(())
}

fn check_case(case: &FuzzCase) -> Result<(), String> {
    let mut classic = Machine::from_source(&case.source, case.input.clone())
        .map_err(|error| format!("classic construction failed: {error}"))?;
    let mut profiled = ProfileMachine::from_source(
        historical_profile(),
        &case.source,
        case.input.clone(),
    )
    .map_err(|error| format!("profile construction failed: {error}"))?;
    check_state(&classic, &profiled, "initial state")?;
    for step in 0..case.budget {
        let classic_observation = classic_step(&mut classic)?;
        let profile_observation = profile_step(&mut profiled)?;
        if classic_observation != profile_observation {
            return Err(format!("step {step}: observations differ"));
        }
        check_state(&classic, &profiled, &format!("after step {step}"))?;
        if classic_observation.stops() {
            break;
        }
    }
    check_memory(&classic, &profiled)
}

fn minimized_failure(case: &FuzzCase) -> FuzzCase {
    let mut minimal = case.clone();
    loop {
        let mut reduced = None;
        for candidate in shrink_candidates(&minimal) {
            if check_case(&candidate).is_err() {
                reduced = Some(candidate);
                break;
            }
        }
        let Some(candidate) = reduced else {
            return minimal;
        };
        minimal = candidate;
    }
}

#[test]
fn seeded_classic_and_profiled_1998_execution_agree() -> Result<(), String> {
    let seed = default_seed();
    for ordinal in 0..CASE_COUNT {
        let case = generate_case(seed, ordinal)?;
        if let Err(error) = check_case(&case) {
            let minimal = minimized_failure(&case);
            let source_len = minimal.source.len();
            let input_len = minimal.input.len();
            let budget = minimal.budget;
            let replay = format!(
                "case {seed:#x}/{ordinal} {source_len}/{input_len}/{budget}"
            );
            return Err(format!("{replay}: {error}"));
        }
    }
    Ok(())
}
