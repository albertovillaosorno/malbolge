// Copyright:
//   - Copyright © 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - Apache-2.0
// Confidential:
//   - false
// License-File:
//   - LICENSE
//
// Boundary-Contract:
// - Owns:
//   - Exact finite guest-computed u8 constant emission and VM evidence.
// - Must-Not:
//   - Substitute host writes for guest rotate or imply general C arithmetic.
// - Allows:
//   - Inputs: canonical ternary MCTR literals and target profile identity.
//   - Outputs: bounded re-admitted source and independent true guest byte.
//   - Side effects: bounded normative VM execution only.
// - Split-When:
//   - General byte-constant synthesis owns a larger safe profile domain.
// - Merge-When:
//   - A full target backend admits this exact proof without specialized code.
// - Summary:
//   - Proves nonzero values come from real relocated guest data rotation.
// - Description:
//   - Verifies selected one-, two-, and three-output seeds and rejects drift.
// - Usage:
//   - cargo test --locked --test rotated_byte_constant_bridge.
// - Defaults:
//   - Out-of-domain byte constants fail closed without source emission.

//! Genuine guest nonzero literal output via a seed-dependent data rotation.

#[path = "../src/compiler/byte-echo-bridge/composition/lib.rs"]
pub mod bridge;

use bridge::ternary::{
    InputBlock, InputFunction, InputInstruction, InputScalarType, InputSourcePosition,
    InputSourceSpan, InputTerminator, TernaryProgram, TypedIrInput, canonical_ternary_bytes,
    canonical_ternary_program, lower_typed_ir,
};
use bridge::{
    ByteEchoBridgeError, encode_initial_zero_outputs, encode_rotated_byte_literal,
    encode_successful_latest_byte_trace,
};
use malbolge::{ProfileMachine, RunOutcome, current_profile, historical_profile};
use std::collections::BTreeMap;

// Every successful short phase, including later duplicate-byte prefixes.
const SHORT_TRIPLE_ROTATION_WITNESSES: &[(u8, usize)] = &[
    (146, 0),
    (25, 1),
    (7, 2),
    (145, 3),
    (24, 4),
    (9, 5),
    (144, 6),
    (22, 7),
    (8, 8),
    (8, 9),
    (22, 10),
    (7, 11),
    (7, 12),
    (21, 13),
    (6, 14),
    (252, 15),
    (20, 16),
    (5, 17),
    (252, 18),
    (19, 19),
    (4, 20),
    (251, 21),
    (18, 22),
    (3, 23),
    (11, 24),
    (23, 25),
];

// All successful short four-output phases; repeated bytes remain observable.
const SHORT_QUADRUPLE_ROTATION_WITNESSES: &[(u8, usize)] = &[
    (43, 0),
    (182, 1),
    (168, 2),
    (44, 3),
    (175, 4),
    (162, 5),
    (42, 6),
    (176, 7),
    (161, 8),
    (40, 9),
    (176, 10),
    (162, 11),
    (41, 12),
    (178, 13),
    (187, 14),
    (66, 15),
    (192, 16),
    (185, 17),
    (64, 18),
    (191, 19),
    (186, 20),
    (65, 21),
    (196, 22),
    (184, 23),
    (57, 24),
    (201, 25),
];

const fn pos(byte: u32) -> InputSourcePosition {
    InputSourcePosition {
        byte,
        column: byte.saturating_add(1),
        line: 1,
    }
}

const fn span(begin: u32, end: u32) -> InputSourceSpan {
    InputSourceSpan {
        begin: pos(begin),
        end: pos(end),
    }
}

fn source(value: u8, outputs: usize) -> Result<TernaryProgram, String> {
    let mut instructions = vec![InputInstruction::ConstantInteger {
        bit_width: 8,
        little_endian: vec![value],
        result: 0,
        span: span(0, 1),
        type_kind: InputScalarType::U8,
    }];
    for index in 0..outputs {
        let start = u32::try_from(index.saturating_add(1))
            .map_err(|error| format!("literal output span: {error}"))?;
        instructions.push(InputInstruction::ByteOutput {
            span: span(start, start.saturating_add(1)),
            value: 0,
        });
    }
    let end = u32::try_from(outputs.saturating_add(2))
        .map_err(|error| format!("literal return span: {error}"))?;
    let typed = TypedIrInput {
        abi_id: String::from("malbolge-c32-v1"),
        functions: vec![InputFunction {
            blocks: vec![InputBlock {
                id: 0,
                instructions,
                phi_count: 0,
                terminator: InputTerminator::Return {
                    span: span(end.saturating_sub(1), end),
                    value: None,
                },
            }],
            entry: 0,
            id: 0,
            name: String::from("one_literal_output"),
            parameter_count: 0,
            return_kind: InputScalarType::Void,
            span: span(0, end),
        }],
        global_count: 0,
        input_format_version: 1,
        proof_obligation_count: 0,
        source_id: String::from("fixtures/rotated-constant.c"),
        source_sha256: [0x73; 32],
        target_profile: String::from("malbolge-2026"),
    };
    let lowered =
        lower_typed_ir(&typed).map_err(|error| format!("literal ternary lowering: {error:?}"))?;
    let canonical = canonical_ternary_bytes(&lowered)
        .map_err(|error| format!("literal canonical MCTR encode: {error:?}"))?;
    let admitted = canonical_ternary_program(&canonical)
        .map_err(|error| format!("literal canonical MCTR decode: {error:?}"))?;
    if admitted != lowered {
        return Err(String::from(
            "literal ternary byte-for-byte roundtrip drift",
        ));
    }
    Ok(admitted)
}

#[test]
fn all_seeded_nonzero_literals_execute_real_guest_rotate_output() -> Result<(), String> {
    for (byte, noops) in [
        (4, 23),
        (5, 20),
        (6, 16),
        (9, 7),
        (10, 4),
        (11, 1),
        (18, 24),
        (19, 21),
        (20, 18),
        (21, 6),
        (22, 3),
        (23, 0),
        (251, 22),
        (253, 19),
    ] {
        let program = source(byte, 1)?;
        let layout = encode_rotated_byte_literal(&program, current_profile())
            .map_err(|error| format!("seeded {byte} target rejected: {error:?}"))?;
        if layout.source().len() != noops + 4
            || layout.executed_code_positions().len() != noops + 4
            || layout
                .data_write_positions()
                .iter()
                .filter(|x| x.is_some())
                .count()
                != 1
        {
            return Err(format!("seeded literal {byte} geometry drift"));
        }
        // Each bridge admission already checks one actual VM output.
        // Repeat under nonempty stdin for representative short/high seeds.
        if [4, 23, 253].contains(&byte) {
            let mut vm =
                ProfileMachine::from_source(current_profile(), layout.source(), vec![255, 0, 128])
                    .map_err(|error| format!("guest seeded {byte} load: {error:?}"))?;
            if !matches!(vm.run(noops + 4),
                Ok(RunOutcome::Terminated { steps, .. }) if steps == noops + 4)
                || vm.output() != [byte]
                || vm.input_consumed() != 0
            {
                return Err(format!("guest seeded {byte} output diverged"));
            }
        }
        if encode_initial_zero_outputs(&program, current_profile()).is_ok()
            || encode_successful_latest_byte_trace(&program, current_profile()).is_ok()
        {
            return Err(format!("old byte trace mode admitted nonzero {byte}"));
        }
    }
    Ok(())
}

#[test]
fn seeded_literals_refuse_unsupported_values_and_profiles() -> Result<(), String> {
    const WITNESSED: &[u8] = &[4, 5, 6, 9, 10, 11, 18, 19, 20, 21, 22, 23, 251, 253];
    for byte in u8::MIN..=u8::MAX {
        if WITNESSED.contains(&byte) {
            continue;
        }
        let program = source(byte, 1)?;
        if encode_rotated_byte_literal(&program, current_profile())
            != Err(ByteEchoBridgeError::UnsupportedEffectTrace)
        {
            return Err(format!("unverified u8 literal {byte} admitted"));
        }
    }
    let valid = source(23, 1)?;
    if encode_rotated_byte_literal(&valid, historical_profile())
        != Err(ByteEchoBridgeError::ProfileMismatch)
    {
        return Err(String::from("foreign profile admitted"));
    }
    Ok(())
}

#[test]
fn seeded_literals_repeat_guest_output_without_new_rotation() -> Result<(), String> {
    for (byte, padding) in [(64, 19), (183, 0), (200, 21)] {
        let program = source(byte, 2)?;
        let layout = encode_rotated_byte_literal(&program, current_profile())
            .map_err(|error| format!("repeat {byte} x2: {error:?}"))?;
        if layout.source().len() != padding + 5
            || layout
                .data_write_positions()
                .iter()
                .filter(|x| x.is_some())
                .count()
                != 1
        {
            return Err(format!("repeat {byte} geometry changed"));
        }
        let mut vm =
            ProfileMachine::from_source(current_profile(), layout.source(), vec![255, 0, 128])
                .map_err(|error| format!("repeat {byte} guest load: {error:?}"))?;
        if !matches!(vm.run(layout.executed_code_positions().len()),
            Ok(RunOutcome::Terminated { steps, .. })
                if steps == layout.executed_code_positions().len())
            || vm.input_consumed() != 0
            || vm.output() != [byte, byte]
        {
            return Err(format!("repeat {byte} guest VM mismatch"));
        }
        if encode_rotated_byte_literal(&source(byte, 1)?, current_profile()).is_ok() {
            return Err(format!("repeated {byte} leaked into single-output seeds"));
        }
    }
    for (byte, outputs) in [(23, 0), (23, 2), (183, 3), (183, 100)] {
        if encode_rotated_byte_literal(&source(byte, outputs)?, current_profile())
            != Err(ByteEchoBridgeError::UnsupportedEffectTrace)
        {
            return Err(format!("unproved seeded shape {byte} x{outputs} admitted"));
        }
    }
    Ok(())
}

#[test]
fn witnessed_triple_literals_reuse_the_real_rotated_accumulator() -> Result<(), String> {
    // Distinct phases, including a new small byte and high-bit bytes.
    for (byte, padding) in [(146, 0), (7, 2), (252, 15), (3, 23), (23, 25)] {
        let admitted = source(byte, 3)?;
        let layout = encode_rotated_byte_literal(&admitted, current_profile())
            .map_err(|error| format!("triple {byte} target rejected: {error:?}"))?;
        if layout.source().len() != padding + 6
            || layout.executed_code_positions().len() != padding + 6
            || layout
                .data_write_positions()
                .iter()
                .filter(|position| position.is_some())
                .count()
                != 1
        {
            return Err(format!("triple {byte} source or memory geometry drift"));
        }
        let mut vm =
            ProfileMachine::from_source(current_profile(), layout.source(), vec![255, 0, 128])
                .map_err(|error| format!("triple {byte} guest load: {error:?}"))?;
        if !matches!(vm.run(padding + 6),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == padding + 6)
            || vm.output() != [byte, byte, byte]
            || vm.input_consumed() != 0
        {
            return Err(format!("triple {byte} guest output or halt diverged"));
        }
    }
    for (byte, outputs) in [(3, 1), (3, 2), (146, 2), (252, 4), (183, 3)] {
        if encode_rotated_byte_literal(&source(byte, outputs)?, current_profile())
            != Err(ByteEchoBridgeError::UnsupportedEffectTrace)
        {
            return Err(format!("unproven triple shape {byte} x{outputs} admitted"));
        }
    }
    Ok(())
}

#[test]
fn witnessed_four_output_literals_reuse_guest_rotation() -> Result<(), String> {
    for (byte, padding) in [(43, 0), (182, 1), (192, 16), (201, 25)] {
        let admitted = source(byte, 4)?;
        let layout = encode_rotated_byte_literal(&admitted, current_profile())
            .map_err(|error| format!("four-output {byte} rejected: {error:?}"))?;
        if layout.source().len() != padding + 7
            || layout.executed_code_positions().len() != padding + 7
            || layout
                .data_write_positions()
                .iter()
                .filter(|position| position.is_some())
                .count()
                != 1
        {
            return Err(format!("four-output {byte} geometry drift"));
        }
        let mut vm =
            ProfileMachine::from_source(current_profile(), layout.source(), vec![0, 255, 128])
                .map_err(|error| format!("four-output {byte} guest load: {error:?}"))?;
        if !matches!(vm.run(padding + 7),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == padding + 7)
            || vm.output() != [byte; 4]
            || vm.input_consumed() != 0
        {
            return Err(format!("four-output {byte} guest execution diverged"));
        }
    }
    for (byte, outputs) in [(43, 1), (43, 2), (43, 3), (43, 5), (3, 4)] {
        if encode_rotated_byte_literal(&source(byte, outputs)?, current_profile())
            != Err(ByteEchoBridgeError::UnsupportedEffectTrace)
        {
            return Err(format!("unproved four-output seed {byte} x{outputs}"));
        }
    }
    Ok(())
}

#[test]
fn four_output_seed_table_admits_exactly_the_witnessed_byte_domain() -> Result<(), String> {
    let mut expected = BTreeMap::new();
    for (byte, padding) in SHORT_QUADRUPLE_ROTATION_WITNESSES {
        _ = expected.entry(*byte).or_insert(*padding);
    }
    let mut witnessed = BTreeMap::new();
    for byte in u8::MIN..=u8::MAX {
        let admitted = source(byte, 4)?;
        match encode_rotated_byte_literal(&admitted, current_profile()) {
            Ok(layout) => {
                let Some(padding) = expected.get(&byte) else {
                    return Err(format!("unwitnessed four-output byte {byte} admitted"));
                };
                if layout.source().len() != padding + 7
                    || layout.executed_code_positions().len() != padding + 7
                    || layout
                        .data_write_positions()
                        .iter()
                        .filter(|position| position.is_some())
                        .count()
                        != 1
                {
                    return Err(format!("four-output {byte} seed geometry drift"));
                }
                _ = witnessed.insert(byte, layout.source().len() - 7);
            }
            Err(ByteEchoBridgeError::UnsupportedEffectTrace) => {
                if expected.contains_key(&byte) {
                    return Err(format!("four-output witnessed byte {byte} rejected"));
                }
            }
            Err(error) => return Err(format!("unexpected four-output error {byte}: {error:?}")),
        }
    }
    if witnessed != expected {
        return Err(format!("four-output byte-domain mismatch: {witnessed:?}"));
    }
    Ok(())
}

#[test]
#[ignore = "full short-phase source/VM search: run optimized with --ignored"]
fn independently_rederive_three_output_rotation_witnesses() -> Result<(), String> {
    use bridge::layout::{LinearOpcode, encode_linear_layout};

    // Finite 0..26 no-op prefixes only. This is not a claim that all 94
    // decoder phases or all 256 literal values have been synthesized.
    let mut witnessed = Vec::new();
    for padding in 0..26 {
        let mut operations = vec![LinearOpcode::NoOperation; padding];
        operations.extend([
            LinearOpcode::RelocateDataPointer,
            LinearOpcode::RotateData,
            LinearOpcode::OutputByte,
            LinearOpcode::OutputByte,
            LinearOpcode::OutputByte,
            LinearOpcode::Halt,
        ]);
        let Ok(layout) = encode_linear_layout(current_profile(), &operations) else {
            continue;
        };
        let Ok(mut vm) =
            ProfileMachine::from_source(current_profile(), layout.source(), Vec::new())
        else {
            continue;
        };
        if !matches!(vm.run(operations.len()),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == operations.len())
            || vm.input_consumed() != 0
        {
            continue;
        }
        let [first, second, third] = vm.output() else {
            continue;
        };
        if *first != 0 && first == second && first == third {
            witnessed.push((*first, padding));
        }
    }
    if witnessed.as_slice() != SHORT_TRIPLE_ROTATION_WITNESSES {
        return Err(format!("triple source/VM witness drift: {witnessed:?}"));
    }
    Ok(())
}

#[test]
#[ignore = "bounded four-output witness scan: run optimized with --ignored"]
fn independently_rederive_four_output_rotation_witnesses() -> Result<(), String> {
    use bridge::layout::{LinearOpcode, encode_linear_layout};

    let mut witnessed = Vec::new();
    for padding in 0..26 {
        let mut operations = vec![LinearOpcode::NoOperation; padding];
        operations.extend([
            LinearOpcode::RelocateDataPointer,
            LinearOpcode::RotateData,
            LinearOpcode::OutputByte,
            LinearOpcode::OutputByte,
            LinearOpcode::OutputByte,
            LinearOpcode::OutputByte,
            LinearOpcode::Halt,
        ]);
        let Ok(layout) = encode_linear_layout(current_profile(), &operations) else {
            continue;
        };
        let Ok(mut vm) =
            ProfileMachine::from_source(current_profile(), layout.source(), Vec::new())
        else {
            continue;
        };
        if !matches!(vm.run(operations.len()),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == operations.len())
            || vm.input_consumed() != 0
        {
            continue;
        }
        let [first, second, third, fourth] = vm.output() else {
            continue;
        };
        if *first != 0 && first == second && first == third && first == fourth {
            witnessed.push((*first, padding));
        }
    }
    if witnessed.as_slice() != SHORT_QUADRUPLE_ROTATION_WITNESSES {
        return Err(format!(
            "four-output source/VM witness drift: {witnessed:?}"
        ));
    }
    Ok(())
}
