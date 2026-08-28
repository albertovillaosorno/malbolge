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
//   - Cross-profile execution, classic differential, and scalable-capacity
//   - tests.
// - Must-Not:
//   - Reuse production profile arithmetic to compute independent expected
//   - values.
// - Allows:
//   - Inputs: canonical profile descriptors and public classic/profile VM APIs.
//   - Outputs: exact state, memory, I/O, EOF, and address-boundary assertions.
//   - Side effects: test-process memory only.
// - Split-When:
//   - Split when another profile memory model requires independent fixtures.
// - Merge-When:
//   - Merge when classic/profile differential evidence gains one shared suite.
// - Summary:
//   - Proves 14-trit execution and 10-trit equivalence without host-width
//   - drift.
// - Description:
//   - Uses scalar ternary formulas as an independent current-profile oracle.
// - Usage:
//   - Composed by `tests/vm.rs` under the normal Cargo integration test target.
// - Defaults:
//   - Current profile uses one full 4,782,969-word execution fixture.
//

//! Profile-driven scalable VM execution and classic differential fixtures.

use malbolge::{
    Machine, ProfileMachine, ProfileMachineError, ProfileRegisters, RunOutcome,
    Termination, Word, current_profile, historical_profile, preflight_profile,
    safe_rust_profiled_capability,
};

use super::{TestResult, check_equal, normalize_result};

const CRAZY_TRIT_TABLE: [[u32; 3]; 3] = [[1, 0, 0], [1, 0, 2], [2, 2, 1]];
const CURRENT_INPUT: u8 = 0xa5;
const CURRENT_SOURCE: &[u8] = b"(=%r_L";
const NARROWING_HALT_SOURCE: &[u8] = b"QP";
const NARROWING_NOOP_HALT_SOURCE: &[u8] = b"DP";
const NARROWING_INPUT_HALT_SOURCE: &[u8] = b"uP";
const NARROWING_INPUT_OUTPUT_HALT_SOURCE: &[u8] = b"ubO";
const NARROWING_NOOP_PREFIX_HALT_SOURCE: &[u8] = b"DCBA@?>=I";
const NOOP_PREFIX_STEPS: u8 = 8;
const CURRENT_TRITS: u8 = 14;
const CURRENT_WORDS: u32 = 4_782_969;
const HISTORICAL_WORDS: u16 = 59_049;
const IO_ROUNDTRIP: &[u8] = include_bytes!(concat!(
    "../compatibility/specification/",
    "interpreter-io-roundtrip.malbolge",
));
const TERNARY_RADIX: u32 = 3;

fn scalar_crazy(mut data: u32, mut accumulator: u32, trits: u8) -> u32 {
    let mut place = 1u32;
    let mut result = 0u32;
    let mut trit = 0u8;
    while trit < trits {
        let data_digit = data.rem_euclid(TERNARY_RADIX);
        let accumulator_digit = accumulator.rem_euclid(TERNARY_RADIX);
        let row = usize::try_from(data_digit).ok().unwrap_or(0);
        let column = usize::try_from(accumulator_digit).ok().unwrap_or(0);
        let output = CRAZY_TRIT_TABLE
            .get(row)
            .and_then(|values| values.get(column))
            .copied()
            .unwrap_or(0);
        result = result.saturating_add(output.saturating_mul(place));
        place = place.saturating_mul(TERNARY_RADIX);
        data = data.div_euclid(TERNARY_RADIX);
        accumulator = accumulator.div_euclid(TERNARY_RADIX);
        trit = trit.saturating_add(1);
    }
    result
}

fn scalar_loaded_prefix(source: &[u8], trits: u8, length: usize) -> Vec<u32> {
    let mut words: Vec<u32> = source
        .iter()
        .copied()
        .filter(|byte| !byte.is_ascii_whitespace())
        .map(u32::from)
        .collect();
    while words.len() < length {
        let previous = words.last().copied().unwrap_or(0);
        let older = words
            .get(words.len().saturating_sub(2))
            .copied()
            .unwrap_or(0);
        words.push(scalar_crazy(older, previous, trits));
    }
    words
}

const fn scalar_rotate(value: u32, modulus: u32) -> u32 {
    let quotient = value.div_euclid(TERNARY_RADIX);
    let low_trit = value.rem_euclid(TERNARY_RADIX);
    quotient.saturating_add(
        low_trit.saturating_mul(modulus.div_euclid(TERNARY_RADIX)),
    )
}

#[test]
fn current_profile_executes_scalable_state_and_io() -> TestResult {
    let expected = scalar_loaded_prefix(CURRENT_SOURCE, CURRENT_TRITS, 43);
    let initial_41 = expected
        .get(41)
        .copied()
        .ok_or_else(|| String::from("missing scalar memory 41"))?;
    let initial_42 = expected
        .get(42)
        .copied()
        .ok_or_else(|| String::from("missing scalar memory 42"))?;
    let expected_41 = scalar_crazy(initial_41, 0, CURRENT_TRITS);
    let expected_42 = scalar_rotate(initial_42, CURRENT_WORDS);

    let mut machine = normalize_result(ProfileMachine::from_source(
        current_profile(),
        CURRENT_SOURCE,
        vec![CURRENT_INPUT],
    ))?;
    let outcome = normalize_result(machine.run(8))?;

    check_equal(
        &outcome,
        &RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 6,
        },
        "current profile halt",
    )?;
    check_equal(&machine.input_consumed(), &1usize, "current input")?;
    check_equal(machine.output(), &[CURRENT_INPUT], "current output")?;
    check_equal(
        &machine.registers(),
        &ProfileRegisters {
            accumulator: u32::from(CURRENT_INPUT),
            code_pointer: 5,
            data_pointer: 45,
        },
        "current registers",
    )?;
    check_equal(
        &normalize_result(machine.memory_word(41))?,
        &expected_41,
        "current crazy write",
    )?;
    check_equal(
        &normalize_result(machine.memory_word(42))?,
        &expected_42,
        "current rotate write",
    )?;
    let _classic_ceiling_plus_one =
        normalize_result(machine.memory_word(59_049))?;
    let _current_max =
        normalize_result(machine.memory_word(CURRENT_WORDS - 1))?;
    check_equal(
        &machine.memory_word(CURRENT_WORDS),
        &Err(ProfileMachineError::AddressOutOfRange { address: CURRENT_WORDS }),
        "current address ceiling",
    )
}

fn check_current_projects_to_historical_state(
    current: &ProfileMachine,
    historical: &ProfileMachine,
) -> TestResult {
    let modulus = u32::from(HISTORICAL_WORDS);
    let current_registers = current.registers();
    let historical_registers = historical.registers();
    check_equal(
        &current_registers.accumulator.rem_euclid(modulus),
        &historical_registers.accumulator,
        "lockstep accumulator projection",
    )?;
    check_equal(
        &current_registers.code_pointer.rem_euclid(modulus),
        &historical_registers.code_pointer,
        "lockstep code-pointer projection",
    )?;
    check_equal(
        &current_registers.data_pointer.rem_euclid(modulus),
        &historical_registers.data_pointer,
        "lockstep data-pointer projection",
    )?;
    check_equal(current.output(), historical.output(), "lockstep output")?;
    check_equal(
        &current.input_consumed(),
        &historical.input_consumed(),
        "lockstep input consumption",
    )?;
    for address in 0..modulus {
        let current_word = normalize_result(current.memory_word(address))?;
        let historical_word =
            normalize_result(historical.memory_word(address))?;
        check_equal(
            &current_word.rem_euclid(modulus),
            &historical_word,
            "lockstep memory projection",
        )?;
    }
    Ok(())
}

#[test]
fn final_observable_match_does_not_imply_projected_lockstep() -> TestResult {
    let input = vec![CURRENT_INPUT];
    let mut historical = normalize_result(ProfileMachine::from_source(
        historical_profile(),
        CURRENT_SOURCE,
        input.clone(),
    ))?;
    let mut current = normalize_result(ProfileMachine::from_source(
        current_profile(),
        CURRENT_SOURCE,
        input,
    ))?;
    check_current_projects_to_historical_state(&current, &historical)?;
    for _ in 0u8..2 {
        let historical_outcome = normalize_result(historical.step())?;
        let current_outcome = normalize_result(current.step())?;
        check_equal(
            &current_outcome,
            &historical_outcome,
            "pre-rotate step outcome",
        )?;
        check_current_projects_to_historical_state(&current, &historical)?;
    }

    let mut historical_trace = None;
    let historical_outcome = normalize_result(
        historical.step_traced(&mut |trace| historical_trace = Some(*trace)),
    )?;
    let mut current_trace = None;
    let current_outcome = normalize_result(
        current.step_traced(&mut |trace| current_trace = Some(*trace)),
    )?;
    check_equal(&current_outcome, &historical_outcome, "rotate step outcome")?;
    check_equal(
        &current_trace.and_then(|trace| trace.decoded),
        &Some(b'*'),
        "current divergent instruction",
    )?;
    check_equal(
        &historical_trace.and_then(|trace| trace.decoded),
        &Some(b'*'),
        "historical divergent instruction",
    )?;
    let modulus = u32::from(HISTORICAL_WORDS);
    let projected = current.registers().accumulator.rem_euclid(modulus);
    if projected == historical.registers().accumulator {
        return Err(String::from("rotate unexpectedly preserved projection"));
    }
    Ok(())
}

#[test]
fn input_output_halt_preserves_projection_for_available_byte() -> TestResult {
    let input = vec![CURRENT_INPUT];
    let mut historical = normalize_result(ProfileMachine::from_source(
        historical_profile(),
        NARROWING_INPUT_OUTPUT_HALT_SOURCE,
        input.clone(),
    ))?;
    let mut current = normalize_result(ProfileMachine::from_source(
        current_profile(),
        NARROWING_INPUT_OUTPUT_HALT_SOURCE,
        input,
    ))?;
    check_current_projects_to_historical_state(&current, &historical)?;
    for context in ["input-output input", "input-output output"] {
        let historical_outcome = normalize_result(historical.step())?;
        let current_outcome = normalize_result(current.step())?;
        check_equal(&current_outcome, &historical_outcome, context)?;
        check_equal(
            &current_outcome,
            &malbolge::StepOutcome::Continued,
            "input-output continued outcome",
        )?;
        check_current_projects_to_historical_state(&current, &historical)?;
    }
    check_equal(current.output(), &[CURRENT_INPUT], "input-output byte")?;
    let historical_halt = normalize_result(historical.step())?;
    let current_halt = normalize_result(current.step())?;
    check_equal(&current_halt, &historical_halt, "input-output halt")?;
    check_equal(
        &current_halt,
        &malbolge::StepOutcome::Terminated(Termination::HaltInstruction),
        "input-output termination",
    )?;
    check_current_projects_to_historical_state(&current, &historical)
}

#[test]
fn input_output_halt_rejects_eof_projection_after_output() -> TestResult {
    let mut historical = normalize_result(ProfileMachine::from_source(
        historical_profile(),
        NARROWING_INPUT_OUTPUT_HALT_SOURCE,
        Vec::new(),
    ))?;
    let mut current = normalize_result(ProfileMachine::from_source(
        current_profile(),
        NARROWING_INPUT_OUTPUT_HALT_SOURCE,
        Vec::new(),
    ))?;
    check_current_projects_to_historical_state(&current, &historical)?;
    let historical_input = normalize_result(historical.step())?;
    let current_input = normalize_result(current.step())?;
    check_equal(&current_input, &historical_input, "EOF input-output input")?;
    check_current_projects_to_historical_state(&current, &historical)?;
    let historical_output = normalize_result(historical.step())?;
    let current_output = normalize_result(current.step())?;
    check_equal(&current_output, &historical_output, "EOF input-output step")?;
    if current.output() == historical.output() {
        return Err(String::from(
            "EOF input-output bytes unexpectedly matched",
        ));
    }
    Ok(())
}

#[test]
fn input_then_halt_preserves_complete_projection_for_endpoint_widths()
-> TestResult {
    for input in [vec![CURRENT_INPUT], Vec::new()] {
        let mut historical = normalize_result(ProfileMachine::from_source(
            historical_profile(),
            NARROWING_INPUT_HALT_SOURCE,
            input.clone(),
        ))?;
        let mut current = normalize_result(ProfileMachine::from_source(
            current_profile(),
            NARROWING_INPUT_HALT_SOURCE,
            input,
        ))?;
        check_current_projects_to_historical_state(&current, &historical)?;
        let historical_input = normalize_result(historical.step())?;
        let current_input = normalize_result(current.step())?;
        check_equal(
            &current_input,
            &historical_input,
            "input-halt input step",
        )?;
        check_equal(
            &current_input,
            &malbolge::StepOutcome::Continued,
            "input-halt continued outcome",
        )?;
        check_current_projects_to_historical_state(&current, &historical)?;
        let historical_halt = normalize_result(historical.step())?;
        let current_halt = normalize_result(current.step())?;
        check_equal(&current_halt, &historical_halt, "input-halt halt step")?;
        check_equal(
            &current_halt,
            &malbolge::StepOutcome::Terminated(Termination::HaltInstruction),
            "input-halt termination",
        )?;
        check_current_projects_to_historical_state(&current, &historical)?;
    }
    Ok(())
}

#[test]
fn noop_prefix_halt_preserves_complete_projection_for_endpoint_widths()
-> TestResult {
    for input in [vec![CURRENT_INPUT], Vec::new()] {
        let mut historical = normalize_result(ProfileMachine::from_source(
            historical_profile(),
            NARROWING_NOOP_PREFIX_HALT_SOURCE,
            input.clone(),
        ))?;
        let mut current = normalize_result(ProfileMachine::from_source(
            current_profile(),
            NARROWING_NOOP_PREFIX_HALT_SOURCE,
            input,
        ))?;
        check_current_projects_to_historical_state(&current, &historical)?;
        for _ in 0u8..NOOP_PREFIX_STEPS {
            let historical_noop = normalize_result(historical.step())?;
            let current_noop = normalize_result(current.step())?;
            check_equal(
                &current_noop,
                &historical_noop,
                "noop-prefix continued step",
            )?;
            check_equal(
                &current_noop,
                &malbolge::StepOutcome::Continued,
                "noop-prefix outcome",
            )?;
            check_current_projects_to_historical_state(&current, &historical)?;
        }
        let historical_halt = normalize_result(historical.step())?;
        let current_halt = normalize_result(current.step())?;
        check_equal(&current_halt, &historical_halt, "noop-prefix halt step")?;
        check_equal(
            &current_halt,
            &malbolge::StepOutcome::Terminated(Termination::HaltInstruction),
            "noop-prefix termination",
        )?;
        check_current_projects_to_historical_state(&current, &historical)?;
    }
    Ok(())
}

#[test]
fn noop_then_halt_preserves_complete_projection_for_endpoint_widths()
-> TestResult {
    for input in [vec![CURRENT_INPUT], Vec::new()] {
        let mut historical = normalize_result(ProfileMachine::from_source(
            historical_profile(),
            NARROWING_NOOP_HALT_SOURCE,
            input.clone(),
        ))?;
        let mut current = normalize_result(ProfileMachine::from_source(
            current_profile(),
            NARROWING_NOOP_HALT_SOURCE,
            input,
        ))?;
        check_current_projects_to_historical_state(&current, &historical)?;
        let historical_noop = normalize_result(historical.step())?;
        let current_noop = normalize_result(current.step())?;
        check_equal(
            &current_noop,
            &historical_noop,
            "noop fixture first step",
        )?;
        check_equal(
            &current_noop,
            &malbolge::StepOutcome::Continued,
            "noop outcome",
        )?;
        check_current_projects_to_historical_state(&current, &historical)?;
        let historical_halt = normalize_result(historical.step())?;
        let current_halt = normalize_result(current.step())?;
        check_equal(&current_halt, &historical_halt, "noop fixture halt step")?;
        check_equal(
            &current_halt,
            &malbolge::StepOutcome::Terminated(Termination::HaltInstruction),
            "noop fixture termination",
        )?;
        check_current_projects_to_historical_state(&current, &historical)?;
    }
    Ok(())
}

#[test]
fn halt_source_preserves_complete_projection_for_checked_endpoint_widths()
-> TestResult {
    for input in [vec![CURRENT_INPUT], Vec::new()] {
        let mut historical = normalize_result(ProfileMachine::from_source(
            historical_profile(),
            NARROWING_HALT_SOURCE,
            input.clone(),
        ))?;
        let mut current = normalize_result(ProfileMachine::from_source(
            current_profile(),
            NARROWING_HALT_SOURCE,
            input,
        ))?;
        check_current_projects_to_historical_state(&current, &historical)?;
        let historical_outcome = normalize_result(historical.step())?;
        let current_outcome = normalize_result(current.step())?;
        check_equal(
            &current_outcome,
            &historical_outcome,
            "halt fixture outcome",
        )?;
        check_equal(
            &current_outcome,
            &malbolge::StepOutcome::Terminated(Termination::HaltInstruction),
            "halt fixture termination",
        )?;
        check_current_projects_to_historical_state(&current, &historical)?;
    }
    Ok(())
}

#[test]
fn current_source_observables_match_historical_with_available_input()
-> TestResult {
    let input = vec![CURRENT_INPUT];
    let mut historical = normalize_result(ProfileMachine::from_source(
        historical_profile(),
        CURRENT_SOURCE,
        input.clone(),
    ))?;
    let mut current = normalize_result(ProfileMachine::from_source(
        current_profile(),
        CURRENT_SOURCE,
        input,
    ))?;
    let historical_outcome = normalize_result(historical.run(8))?;
    let current_outcome = normalize_result(current.run(8))?;
    check_equal(&current_outcome, &historical_outcome, "cross-width outcome")?;
    check_equal(current.output(), historical.output(), "cross-width output")?;
    check_equal(
        &current.input_consumed(),
        &historical.input_consumed(),
        "cross-width input consumption",
    )?;
    check_equal(
        &current.registers(),
        &historical.registers(),
        "cross-width registers",
    )
}

#[test]
fn current_source_rejects_ten_trit_narrowing_when_eof_is_observable()
-> TestResult {
    let mut historical = normalize_result(ProfileMachine::from_source(
        historical_profile(),
        CURRENT_SOURCE,
        Vec::new(),
    ))?;
    let mut current = normalize_result(ProfileMachine::from_source(
        current_profile(),
        CURRENT_SOURCE,
        Vec::new(),
    ))?;
    let historical_outcome = normalize_result(historical.run(8))?;
    let current_outcome = normalize_result(current.run(8))?;
    check_equal(
        &current_outcome,
        &historical_outcome,
        "cross-width EOF outcome",
    )?;
    if current.output() == historical.output() {
        return Err(String::from(
            "cross-width EOF output unexpectedly matched",
        ));
    }
    Ok(())
}

#[test]
fn current_loader_projects_to_complete_historical_memory_prefix() -> TestResult
{
    let historical = normalize_result(ProfileMachine::from_source(
        historical_profile(),
        CURRENT_SOURCE,
        Vec::new(),
    ))?;
    let current = normalize_result(ProfileMachine::from_source(
        current_profile(),
        CURRENT_SOURCE,
        Vec::new(),
    ))?;
    let historical_modulus = u32::from(HISTORICAL_WORDS);
    for address in 0..historical_modulus {
        let narrow = normalize_result(historical.memory_word(address))?;
        let wide = normalize_result(current.memory_word(address))?;
        check_equal(
            &wide.rem_euclid(historical_modulus),
            &narrow,
            "current loader projection",
        )?;
    }
    Ok(())
}

#[test]
fn profiled_historical_matches_classic_roundtrip_and_eof() -> TestResult {
    for input in [vec![0x41], Vec::new()] {
        let mut classic = normalize_result(Machine::from_source(
            IO_ROUNDTRIP,
            input.clone(),
        ))?;
        let mut profiled = normalize_result(ProfileMachine::from_source(
            historical_profile(),
            IO_ROUNDTRIP,
            input,
        ))?;
        let classic_outcome = normalize_result(classic.run(8))?;
        let profiled_outcome = normalize_result(profiled.run(8))?;
        check_equal(
            &profiled_outcome,
            &classic_outcome,
            "historical run outcome",
        )?;
        check_equal(profiled.output(), classic.output(), "historical output")?;
        check_equal(
            &profiled.input_consumed(),
            &classic.input_consumed(),
            "historical input consumption",
        )?;
        let classic_registers = classic.registers();
        check_equal(
            &profiled.registers(),
            &ProfileRegisters {
                accumulator: u32::from(classic_registers.accumulator.value()),
                code_pointer: u32::from(classic_registers.code_pointer.value()),
                data_pointer: u32::from(classic_registers.data_pointer.value()),
            },
            "historical registers",
        )?;
        for raw in 0..HISTORICAL_WORDS {
            let classic_address = normalize_result(Word::new(raw))?;
            let classic_value =
                normalize_result(classic.memory_word(classic_address))?;
            let profiled_value =
                normalize_result(profiled.memory_word(u32::from(raw)))?;
            check_equal(
                &profiled_value,
                &u32::from(classic_value.value()),
                "historical memory",
            )?;
        }
    }
    Ok(())
}

#[test]
fn profiled_runtime_capability_accepts_current_profile() -> TestResult {
    normalize_result(preflight_profile(
        current_profile(),
        u64::from(current_profile().memory_words()),
        safe_rust_profiled_capability(),
    ))
}
