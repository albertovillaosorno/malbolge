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
//   - A source-independent five-distinct-byte guest arithmetic witness.
// - Must-Not:
//   - Synthesize output bytes on the host or claim general C compilation.
// - Allows:
//   - Inputs: canonical current-profile linear guest operations.
//   - Outputs: five VM bytes, 23 exact steps and disjoint guest data writes.
//   - Side effects: none.
// - Split-When:
//   - General guest byte-sequence synthesis replaces bounded witnesses.
// - Merge-When:
//   - General five-byte source compilation owns the physical guest proof.
// - Summary:
//   - Five relocated CrazyData operations emit Q, quote, ESC, 7, 9.
// - Description:
//   - The independently executed VM witness is binary, not just printable.
// - Usage:
//   - cargo test --locked --test guest_five_distinct_literal_witness
// - Defaults:
//   - Does not admit any five-byte source C program to the compiler.

//! Five distinct actual guest bytes produced by five arithmetic operations.

#[path = "../src/compiler/malbolge-layout/composition/lib.rs"]
pub mod layout;

use std::collections::BTreeSet;

use layout::{LinearOpcode, encode_linear_layout};
use malbolge::{ProfileMachine, RunOutcome, current_profile};

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "assertions independently bind guest arithmetic to the real VM"
)]
fn five_independent_guest_writes_emit_exact_binary_bytes() -> Result<(), String> {
    let mut operations = vec![LinearOpcode::NoOperation; 11];
    operations.push(LinearOpcode::RelocateDataPointer);
    for _ in 0..5 {
        operations.extend([LinearOpcode::CrazyData, LinearOpcode::OutputByte]);
    }
    operations.push(LinearOpcode::Halt);
    assert_eq!(operations.len(), 23);

    let source = encode_linear_layout(current_profile(), &operations)
        .map_err(|error| format!("layout: {error:?}"))?;
    let writes: Vec<u32> = source
        .data_write_positions()
        .iter()
        .flatten()
        .copied()
        .collect();
    assert_eq!(writes.len(), 5);
    assert_eq!(writes.iter().copied().collect::<BTreeSet<_>>().len(), 5);
    assert!(writes.iter().all(|address| {
        usize::try_from(*address).is_ok_and(|position| position >= source.source().len())
    }));

    for input in [Vec::new(), vec![0, 128, 255]] {
        let mut vm = ProfileMachine::from_source(current_profile(), source.source(), input)
            .map_err(|error| format!("load: {error:?}"))?;
        let outcome = vm
            .run(operations.len())
            .map_err(|error| format!("run: {error:?}"))?;
        assert!(matches!(outcome, RunOutcome::Terminated { steps, .. } if steps == 23));
        assert_eq!(vm.input_consumed(), 0);
        assert_eq!(vm.output(), b"Q\"\x1b79");
    }
    Ok(())
}

#[path = "../src/compiler/byte-echo-bridge/composition/lib.rs"]
pub mod bridge;

use bridge::ternary::{
    InputBlock, InputFunction, InputInstruction, InputScalarType, InputSourcePosition,
    InputSourceSpan, InputTerminator, TernaryProgram, TypedIrInput, canonical_ternary_bytes,
    canonical_ternary_program, lower_typed_ir,
};
use bridge::{ByteEchoBridgeError, encode_distinct_literal_quint};

const fn position(byte: u32) -> InputSourcePosition {
    InputSourcePosition {
        byte,
        column: byte + 1,
        line: 1,
    }
}

const fn span(begin: u32, end: u32) -> InputSourceSpan {
    InputSourceSpan {
        begin: position(begin),
        end: position(end),
    }
}

fn source_quint(bytes: [u8; 5], stale: bool) -> Result<TernaryProgram, String> {
    let mut instructions = Vec::with_capacity(10);
    for (index, byte) in bytes.into_iter().enumerate() {
        let id = u32::try_from(index).map_err(|error| format!("index: {error}"))?;
        instructions.push(InputInstruction::ConstantInteger {
            bit_width: 8,
            little_endian: vec![byte],
            result: id,
            span: span(id * 2, id * 2 + 1),
            type_kind: InputScalarType::U8,
        });
        instructions.push(InputInstruction::ByteOutput {
            span: span(id * 2 + 1, id * 2 + 2),
            value: if stale && index == 4 { 3 } else { id },
        });
    }
    let typed = TypedIrInput {
        abi_id: String::from("malbolge-c32-v1"),
        functions: vec![InputFunction {
            blocks: vec![InputBlock {
                id: 0,
                instructions,
                phi_count: 0,
                terminator: InputTerminator::Return {
                    span: span(10, 11),
                    value: None,
                },
            }],
            entry: 0,
            id: 0,
            name: String::from("guest_quint"),
            parameter_count: 0,
            return_kind: InputScalarType::Void,
            span: span(0, 11),
        }],
        global_count: 0,
        input_format_version: 1,
        proof_obligation_count: 0,
        source_id: String::from("fixtures/guest-quint.c"),
        source_sha256: [0x51; 32],
        target_profile: String::from("malbolge-2026"),
    };
    let lowered = lower_typed_ir(&typed).map_err(|error| format!("lower: {error:?}"))?;
    let wire = canonical_ternary_bytes(&lowered).map_err(|error| format!("wire: {error:?}"))?;
    let admitted = canonical_ternary_program(&wire).map_err(|error| format!("admit: {error:?}"))?;
    assert_eq!(lowered, admitted, "canonical MCTR changed effects");
    Ok(admitted)
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "assertions bind canonical SSA effects to physical guest output"
)]
fn canonical_five_byte_bridge_matches_independently_executed_layout() -> Result<(), String> {
    let mut operations = vec![LinearOpcode::NoOperation; 11];
    operations.push(LinearOpcode::RelocateDataPointer);
    for _ in 0..5 {
        operations.extend([LinearOpcode::CrazyData, LinearOpcode::OutputByte]);
    }
    operations.push(LinearOpcode::Halt);
    let independent = encode_linear_layout(current_profile(), &operations)
        .map_err(|error| format!("independent layout: {error:?}"))?;
    let actual =
        encode_distinct_literal_quint(&source_quint(*b"Q\"\x1b79", false)?, current_profile())
            .map_err(|error| format!("bridge: {error:?}"))?;
    assert_eq!(actual.source(), independent.source());
    assert_eq!(actual.profile_id(), independent.profile_id());
    assert_eq!(
        actual.data_write_positions(),
        independent.data_write_positions()
    );
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "source-independent guest VM verifies dynamic five-byte layout"
)]
fn zero_prefixed_five_byte_bridge_executes_real_guest() -> Result<(), String> {
    let expected = *b"\0T=4>";
    let compiled = encode_distinct_literal_quint(
        &source_quint(expected, false)?,
        current_profile(),
    )
    .map_err(|error| format!("zero-prefixed bridge: {error:?}"))?;
    let steps = compiled.executed_code_positions().len();
    let writes: Vec<_> = compiled
        .data_write_positions()
        .iter()
        .flatten()
        .copied()
        .collect();
    assert!(steps <= 126);
    assert!(writes.len() >= 4);
    assert_eq!(
        writes.iter().copied().collect::<BTreeSet<_>>().len(),
        writes.len()
    );
    for input in [Vec::new(), vec![0, 128, 255]] {
        let mut vm = ProfileMachine::from_source(
            current_profile(),
            compiled.source(),
            input,
        )
        .map_err(|error| format!("guest load: {error:?}"))?;
        assert!(matches!(vm.run(steps),
            Ok(RunOutcome::Terminated { steps: actual, .. }) if actual == steps));
        assert_eq!(vm.input_consumed(), 0);
        assert_eq!(vm.output(), expected);
    }
    assert!(matches!(
        encode_distinct_literal_quint(
            &source_quint(*b"\x01T=4>", false)?,
            current_profile(),
        ),
        Err(ByteEchoBridgeError::UnsupportedEffectTrace)
    ));
    Ok(())
}


#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "assertions check independent bridge fail-closed behavior"
)]
fn unproved_or_stale_five_byte_ir_refuses() -> Result<(), String> {
    for (bytes, stale) in [
        (*b"Q\"\x1b78", false),
        (*b"Q\"\x1a79", false),
        (*b"Q\"\x1b79", true),
        (*b"Q\"\x1b77", false),
    ] {
        let source = source_quint(bytes, stale)?;
        assert!(matches!(
            encode_distinct_literal_quint(&source, current_profile()),
            Err(ByteEchoBridgeError::UnsupportedEffectTrace)
        ));
    }
    assert!(matches!(
        encode_distinct_literal_quint(
            &source_quint(*b"Q\"\x1b79", false)?,
            malbolge::historical_profile()
        ),
        Err(ByteEchoBridgeError::ProfileMismatch)
    ));
    Ok(())
}
