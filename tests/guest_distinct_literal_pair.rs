// Copyright:
//   - Copyright © 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - LicenseRef-Proprietary
// Confidential:
//   - true
// License-File:
//   - LICENSE
//
// Boundary-Contract:
// - Owns:
//   - Exact two-distinct-literal guest VM witness and mutable-data evidence.
// - Must-Not:
//   - Substitute host output, claim arbitrary byte-pair synthesis, or infer C.
// - Allows:
//   - Inputs: current-profile relocated CrazyData layouts.
//   - Outputs: verified guest output bytes, steps, and data writes.
//   - Side effects: none outside bounded guest execution.
// - Split-When:
//   - A complete arbitrary byte-pair composer subsumes finite witnesses.
// - Merge-When:
//   - The canonical layout test owns two-arithmetic byte transitions.
// - Summary:
//   - Proves two different bytes arise from two real guest crazy operations.
// - Description:
//   - Each padding phase binds both outputs to loader-expanded memory.
// - Usage:
//   - cargo test --locked --test guest_distinct_literal_pair
// - Defaults:
//   - Source-bound byte pairs require independent guest VM verification.

//! Independent two-different-byte witness for the actual Malbolge VM.

#[path = "../src/compiler/byte-echo-bridge/composition/lib.rs"]
pub mod bridge;

use bridge::layout::{self, LinearOpcode, encode_linear_layout};
use bridge::ternary::{
    InputBlock, InputFunction, InputInstruction, InputScalarType,
    InputSourcePosition, InputSourceSpan, InputTerminator, TernaryProgram,
    TypedIrInput, canonical_ternary_bytes, canonical_ternary_program,
    lower_typed_ir,
};
use bridge::{ByteEchoBridgeError, encode_distinct_literal_pair};
use malbolge::{ProfileMachine, RunOutcome, current_profile};

fn witnessed_pair(padding: usize) -> Result<layout::LinearLayout, String> {
    let profile = current_profile();
    let mut operations = vec![LinearOpcode::NoOperation; padding];
    operations.extend([
        LinearOpcode::RelocateDataPointer,
        LinearOpcode::CrazyData,
        LinearOpcode::OutputByte,
        LinearOpcode::CrazyData,
        LinearOpcode::OutputByte,
        LinearOpcode::Halt,
    ]);
    let encoded = encode_linear_layout(profile, &operations)
        .map_err(|error| format!("encode: {error:?}"))?;
    let writes: Vec<u32> = encoded
        .data_write_positions()
        .iter()
        .flatten()
        .copied()
        .collect();
    let [first_write, second_write] = writes.as_slice() else {
        return Err(String::from(
            "exactly two guest data-write witnesses required",
        ));
    };
    if first_write == second_write
        || writes.iter().any(|address| {
            usize::try_from(*address)
                .is_ok_and(|value| value < encoded.source().len())
        })
    {
        return Err(String::from(
            "two independent out-of-source guest writes required",
        ));
    }
    Ok(encoded)
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "test assertions are intentional after fallible setup"
)]
fn two_distinct_printables_use_actual_guest_arithmetic() -> Result<(), String> {
    for (padding, expected) in [
        (0usize, b"Y/".as_slice()),
        (1, b"Y$".as_slice()),
        (2, b"Q.".as_slice()),
    ] {
        let layout = witnessed_pair(padding)?;
        let step_bound = padding + 6;
        for input in [Vec::new(), vec![0, 128, 255]] {
            let mut vm = ProfileMachine::from_source(
                current_profile(),
                layout.source(),
                input,
            )
            .map_err(|error| format!("load: {error:?}"))?;
            let outcome = vm
                .run(step_bound)
                .map_err(|error| format!("run: {error:?}"))?;
            assert!(
                matches!(outcome, RunOutcome::Terminated { steps, .. } if steps == step_bound)
            );
            assert_eq!(vm.input_consumed(), 0);
            assert_eq!(
                vm.output(),
                expected,
                "source-position-specific VM output"
            );
        }
    }
    Ok(())
}

const fn position(byte: u32) -> InputSourcePosition {
    InputSourcePosition {
        byte,
        column: byte.saturating_add(1),
        line: 1,
    }
}

const fn span(begin: u32, end: u32) -> InputSourceSpan {
    InputSourceSpan {
        begin: position(begin),
        end: position(end),
    }
}

fn source_pair(
    first: u8,
    second: u8,
    stale: bool,
) -> Result<TernaryProgram, String> {
    let typed = TypedIrInput {
        abi_id: String::from("malbolge-c32-v1"),
        functions: vec![InputFunction {
            blocks: vec![InputBlock {
                id: 0,
                instructions: vec![
                    InputInstruction::ConstantInteger {
                        bit_width: 8,
                        little_endian: vec![first],
                        result: 0,
                        span: span(0, 1),
                        type_kind: InputScalarType::U8,
                    },
                    InputInstruction::ByteOutput {
                        span: span(1, 2),
                        value: 0,
                    },
                    InputInstruction::ConstantInteger {
                        bit_width: 8,
                        little_endian: vec![second],
                        result: 1,
                        span: span(2, 3),
                        type_kind: InputScalarType::U8,
                    },
                    InputInstruction::ByteOutput {
                        span: span(3, 4),
                        value: u32::from(!stale),
                    },
                ],
                phi_count: 0,
                terminator: InputTerminator::Return {
                    span: span(4, 5),
                    value: None,
                },
            }],
            entry: 0,
            id: 0,
            name: String::from("distinct_literals"),
            parameter_count: 0,
            return_kind: InputScalarType::Void,
            span: span(0, 5),
        }],
        global_count: 0,
        input_format_version: 1,
        proof_obligation_count: 0,
        source_id: String::from("fixtures/distinct-literals.c"),
        source_sha256: [0x47; 32],
        target_profile: String::from("malbolge-2026"),
    };
    let lowered =
        lower_typed_ir(&typed).map_err(|error| format!("lower: {error:?}"))?;
    let wire = canonical_ternary_bytes(&lowered)
        .map_err(|error| format!("wire: {error:?}"))?;
    let restored = canonical_ternary_program(&wire)
        .map_err(|error| format!("re-admit: {error:?}"))?;
    if restored != lowered {
        return Err(String::from(
            "independent MCTR round-trip changed the trace",
        ));
    }
    Ok(restored)
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "test assertions are intentional after fallible setup"
)]
fn source_bound_pair_bridge_matches_guest_witness() -> Result<(), String> {
    for (first, second, padding) in
        [(b'Y', b'/', 0usize), (b'Y', b'$', 1), (b'Q', b'.', 2)]
    {
        let program = source_pair(first, second, false)?;
        let encoded = encode_distinct_literal_pair(&program, current_profile())
            .map_err(|error| format!("pair {first}/{second}: {error:?}"))?;
        let original = witnessed_pair(padding)?;
        assert_eq!(encoded, original, "independent layout recipe differs");
        let mut vm = ProfileMachine::from_source(
            current_profile(),
            encoded.source(),
            Vec::new(),
        )
        .map_err(|error| format!("bridge guest: {error:?}"))?;
        assert!(matches!(vm.run(padding + 6),
            Ok(RunOutcome::Terminated { steps, .. }) if steps == padding + 6));
        assert_eq!(vm.output(), [first, second]);
    }
    Ok(())
}

#[test]
fn previously_unwitnessed_binary_pair_uses_verified_guest_arithmetic()
-> Result<(), String> {
    let expected = [0x02, 0xcf];
    let program = source_pair(expected[0], expected[1], false)?;
    let layout = encode_distinct_literal_pair(&program, current_profile())
        .map_err(|error| format!("binary pair: {error:?}"))?;
    let writes: Vec<_> =
        layout.data_write_positions().iter().flatten().collect();
    assert_eq!(writes.len(), 2);
    assert_ne!(writes[0], writes[1]);
    assert!(
        writes
            .iter()
            .all(|address| **address >= layout.source().len() as u32)
    );
    for input in [Vec::new(), vec![0, 128, 255]] {
        let mut vm = ProfileMachine::from_source(
            current_profile(),
            layout.source(),
            input,
        )
        .map_err(|error| format!("binary guest load: {error:?}"))?;
        assert!(matches!(vm.run(100), Ok(RunOutcome::Terminated { .. })));
        assert_eq!(vm.input_consumed(), 0);
        assert_eq!(vm.output(), expected);
    }
    Ok(())
}

#[test]
fn newly_admitted_qz_pair_replays_in_guest_vm() -> Result<(), String> {
    let expected = [b'Q', b'Z'];
    let program = source_pair(expected[0], expected[1], false)?;
    let layout = encode_distinct_literal_pair(&program, current_profile())
        .map_err(|error| format!("QZ pair: {error:?}"))?;
    for input in [Vec::new(), vec![0, 128, 255]] {
        let mut vm = ProfileMachine::from_source(
            current_profile(),
            layout.source(),
            input,
        )
        .map_err(|error| format!("QZ guest load: {error:?}"))?;
        assert!(matches!(vm.run(100), Ok(RunOutcome::Terminated { .. })));
        assert_eq!(vm.input_consumed(), 0);
        assert_eq!(vm.output(), expected);
    }
    Ok(())
}

#[test]
fn source_bound_pair_accepts_composed_arithmetic() -> Result<(), String> {
    // A separate source-backed C loop proves 2, 3 ^ 54 = 53.
    let expected = [2, 53];
    let program = source_pair(expected[0], expected[1], false)?;
    let layout = encode_distinct_literal_pair(&program, current_profile())
        .map_err(|error| format!("composed pair: {error:?}"))?;
    let writes: Vec<_> =
        layout.data_write_positions().iter().flatten().collect();
    assert_eq!(writes.len(), 3);
    assert_eq!(
        writes
            .iter()
            .copied()
            .collect::<std::collections::BTreeSet<_>>()
            .len(),
        3
    );
    for input in [Vec::new(), vec![0, 128, 255]] {
        let mut vm = ProfileMachine::from_source(
            current_profile(),
            layout.source(),
            input,
        )
        .map_err(|error| format!("composed guest load: {error:?}"))?;
        assert!(matches!(vm.run(100), Ok(RunOutcome::Terminated { .. })));
        assert_eq!(vm.input_consumed(), 0);
        assert_eq!(vm.output(), expected);
    }
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "test assertions are intentional after fallible setup"
)]
fn source_bound_pair_bridge_refuses_unproved_or_stale_effects()
-> Result<(), String> {
    for (first, second, stale) in
        [(0xff, b'Z', false), (b'Q', b'.', true), (b'Q', b'Q', false)]
    {
        let program = source_pair(first, second, stale)?;
        assert!(
            matches!(
                encode_distinct_literal_pair(&program, current_profile()),
                Err(ByteEchoBridgeError::UnsupportedEffectTrace)
            ),
            "unexpected pair: {first:#04x}/{second:#04x}, stale={stale}"
        );
    }
    let program = source_pair(b'Q', b'.', false)?;
    assert!(matches!(
        encode_distinct_literal_pair(&program, malbolge::historical_profile()),
        Err(ByteEchoBridgeError::ProfileMismatch)
    ));
    Ok(())
}
