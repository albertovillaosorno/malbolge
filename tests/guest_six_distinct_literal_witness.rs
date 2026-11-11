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
//   - A source-independent six-distinct-byte guest arithmetic witness.
// - Must-Not:
//   - Synthesize guest output on the host or claim six-byte C lowering.
// - Allows:
//   - Inputs: canonical current-profile linear guest operations.
//   - Outputs: six exact VM bytes, 15 steps and disjoint guest data writes.
//   - Side effects: none.
// - Split-When:
//   - General guest byte sequence synthesis replaces bounded witnesses.
// - Merge-When:
//   - A source-to-guest six-byte compiler owns this physical proof.
// - Summary:
//   - Six relocated CrazyData operations emit six distinct binary bytes.
// - Description:
//   - Each byte is produced by a real VM arithmetic instruction.
// - Usage:
//   - cargo test --locked --test guest_six_distinct_literal_witness
// - Defaults:
//   - Does not admit any six-byte source C program to the compiler.

//! Six independent data writes and six distinct output bytes in the real VM.

#[path = "../src/compiler/malbolge-layout/composition/lib.rs"]
pub mod layout;

use std::collections::BTreeSet;

use layout::{LinearOpcode, encode_linear_layout};
use malbolge::{ProfileMachine, RunOutcome, current_profile};

const EXPECTED: [u8; 6] = [0x51, 0x1c, 0x4f, 0x1d, 0x50, 0x1b];

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "assertions independently bind guest arithmetic to the actual VM"
)]
#[expect(
    clippy::cognitive_complexity,
    reason = "one guest proof checks writes, steps and binary VM output"
)]
fn six_distinct_binary_bytes_are_computed_by_guest_arithmetic()
-> Result<(), String> {
    // Prefix and overall source length both affect loader-expanded data words.
    let mut operations =
        vec![LinearOpcode::NoOperation, LinearOpcode::RelocateDataPointer];
    for _ in 0usize..6 {
        operations.extend([LinearOpcode::CrazyData, LinearOpcode::OutputByte]);
    }
    operations.push(LinearOpcode::Halt);
    assert_eq!(operations.len(), 15);

    let layout = encode_linear_layout(current_profile(), &operations)
        .map_err(|error| format!("encode: {error:?}"))?;
    let writes: Vec<_> = layout
        .data_write_positions()
        .iter()
        .flatten()
        .copied()
        .collect();
    assert_eq!(writes.len(), 6);
    assert_eq!(writes.iter().copied().collect::<BTreeSet<_>>().len(), 6);
    assert!(writes.iter().all(|address| {
        usize::try_from(*address)
            .is_ok_and(|position| position >= layout.source().len())
    }));

    assert_eq!(EXPECTED.iter().copied().collect::<BTreeSet<_>>().len(), 6);
    for input in [Vec::new(), vec![0, 128, 255]] {
        let mut vm = ProfileMachine::from_source(
            current_profile(),
            layout.source(),
            input,
        )
        .map_err(|error| format!("load: {error:?}"))?;
        let outcome = vm.run(15).map_err(|error| format!("run: {error:?}"))?;
        let RunOutcome::Terminated { steps, .. } = outcome else {
            return Err(String::from("original six-byte guest did not halt"));
        };
        assert_eq!(steps, 15);
        assert_eq!(vm.input_consumed(), 0);
        assert_eq!(vm.output(), EXPECTED);
    }
    Ok(())
}

#[path = "../src/compiler/byte-echo-bridge/composition/lib.rs"]
pub mod bridge;

use bridge::ternary::{
    InputBlock, InputFunction, InputInstruction, InputScalarType,
    InputSourcePosition, InputSourceSpan, InputTerminator, TernaryProgram,
    TypedIrInput, canonical_ternary_bytes, canonical_ternary_program,
    lower_typed_ir,
};
use bridge::{ByteEchoBridgeError, encode_distinct_literal_six};

const ZERO_PREFIXED: [u8; 6] = [0, 0x51, 0x22, 0x1b, 0x37, 0x39];

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

fn source_six(bytes: [u8; 6], stale: bool) -> Result<TernaryProgram, String> {
    let mut instructions = Vec::with_capacity(12);
    for (index, byte) in bytes.into_iter().enumerate() {
        let id =
            u32::try_from(index).map_err(|error| format!("index: {error}"))?;
        instructions.push(InputInstruction::ConstantInteger {
            bit_width: 8,
            little_endian: vec![byte],
            result: id,
            span: span(id * 2, id * 2 + 1),
            type_kind: InputScalarType::U8,
        });
        instructions.push(InputInstruction::ByteOutput {
            span: span(id * 2 + 1, id * 2 + 2),
            value: if stale && index == 5 {
                4
            } else {
                id
            },
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
                    span: span(12, 13),
                    value: None,
                },
            }],
            entry: 0,
            id: 0,
            name: String::from("guest_six"),
            parameter_count: 0,
            return_kind: InputScalarType::Void,
            span: span(0, 13),
        }],
        global_count: 0,
        input_format_version: 1,
        proof_obligation_count: 0,
        source_id: String::from("fixtures/guest-six.c"),
        source_sha256: [0x51; 32],
        target_profile: String::from("malbolge-2026"),
    };
    let lowered =
        lower_typed_ir(&typed).map_err(|error| format!("lower: {error:?}"))?;
    let wire = canonical_ternary_bytes(&lowered)
        .map_err(|error| format!("wire: {error:?}"))?;
    let admitted = canonical_ternary_program(&wire)
        .map_err(|error| format!("admit: {error:?}"))?;
    assert_eq!(lowered, admitted, "canonical SSA changed effects");
    Ok(admitted)
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "canonical SSA is checked against real guest output"
)]
fn zero_prefix_and_five_guest_writes_are_a_six_byte_stream()
-> Result<(), String> {
    let mut operations = vec![LinearOpcode::OutputByte];
    operations.resize(11, LinearOpcode::NoOperation);
    operations.push(LinearOpcode::RelocateDataPointer);
    for _ in 0..5 {
        operations.extend([LinearOpcode::CrazyData, LinearOpcode::OutputByte]);
    }
    operations.push(LinearOpcode::Halt);
    let layout = encode_linear_layout(current_profile(), &operations)
        .map_err(|error| format!("seeded layout: {error:?}"))?;
    for input in [Vec::new(), vec![0, 128, 255]] {
        let mut vm = ProfileMachine::from_source(
            current_profile(),
            layout.source(),
            input,
        )
        .map_err(|error| format!("seeded guest load: {error:?}"))?;
        let result = vm
            .run(operations.len())
            .map_err(|error| format!("seeded guest: {error:?}"))?;
        let RunOutcome::Terminated { steps, .. } = result else {
            return Err(String::from(
                "seeded zero-prefixed guest did not halt",
            ));
        };
        assert_eq!(steps, operations.len());
        assert_eq!(vm.input_consumed(), 0);
        assert_eq!(vm.output(), ZERO_PREFIXED);
    }
    let compiled = encode_distinct_literal_six(
        &source_six(ZERO_PREFIXED, false)?,
        current_profile(),
    )
    .map_err(|error| format!("six-byte compiler: {error:?}"))?;
    for input in [Vec::new(), vec![255, 0, 128]] {
        let mut vm = ProfileMachine::from_source(
            current_profile(),
            compiled.source(),
            input,
        )
        .map_err(|error| format!("compiled load: {error:?}"))?;
        let steps = compiled.executed_code_positions().len();
        let RunOutcome::Terminated { steps: actual, .. } = vm
            .run(steps)
            .map_err(|error| format!("compiled guest: {error:?}"))?
        else {
            return Err(String::from(
                "compiled zero-prefixed guest did not halt",
            ));
        };
        assert_eq!(actual, steps);
        assert_eq!(vm.input_consumed(), 0);
        assert_eq!(vm.output(), ZERO_PREFIXED);
    }
    assert!(matches!(
        encode_distinct_literal_six(
            &source_six(ZERO_PREFIXED, true)?,
            current_profile()
        ),
        Err(ByteEchoBridgeError::UnsupportedEffectTrace)
    ));
    // Nonzero-leading streams now have their own VM-parity regression;
    // source-distinct SSA and profile drift are still rejected here.
    assert!(matches!(
        encode_distinct_literal_six(
            &source_six(ZERO_PREFIXED, false)?,
            malbolge::historical_profile()
        ),
        Err(ByteEchoBridgeError::ProfileMismatch)
    ));
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "guest-output experiment checks independently encoded source"
)]
fn nonzero_leading_six_byte_guest_stream_is_not_a_fixed_fixture()
-> Result<(), String> {
    let profile = current_profile();
    let mut operations = vec![LinearOpcode::NoOperation; 11];
    operations.push(LinearOpcode::RelocateDataPointer);
    for _ in 0..6 {
        operations.extend([LinearOpcode::CrazyData, LinearOpcode::OutputByte]);
    }
    operations.push(LinearOpcode::Halt);
    let independent = encode_linear_layout(profile, &operations)
        .map_err(|error| format!("seeded layout: {error:?}"))?;
    let mut vm = ProfileMachine::from_source(
        profile,
        independent.source(),
        Vec::new(),
    )
    .map_err(|error| format!("seeded load: {error:?}"))?;
    let outcome = vm.run(operations.len())
        .map_err(|error| format!("seeded run: {error:?}"))?;
    assert!(matches!(outcome, RunOutcome::Terminated { .. }));
    let expected: [u8; 6] = vm.output().try_into()
        .map_err(|_error| String::from("seeded output was not six bytes"))?;
    assert_eq!(expected, [53, 54, 53, 0, 80, 27]);
    assert_ne!(expected, EXPECTED);
    let compiled = encode_distinct_literal_six(
        &source_six(expected, false)?,
        profile,
    )
    .map_err(|error| format!("nonzero-prefix search {expected:?}: {error:?}"))?;
    for input in [Vec::new(), vec![0, 128, 255]] {
        let mut guest = ProfileMachine::from_source(profile, compiled.source(), input)
            .map_err(|error| format!("compiled load: {error:?}"))?;
        assert!(matches!(
            guest.run(compiled.executed_code_positions().len()),
            Ok(RunOutcome::Terminated { .. })
        ));
        assert_eq!(guest.input_consumed(), 0);
        assert_eq!(guest.output(), expected);
    }
    assert!(matches!(
        encode_distinct_literal_six(
            &source_six(expected, true)?,
            profile,
        ),
        Err(ByteEchoBridgeError::UnsupportedEffectTrace)
    ));
    Ok(())
}
