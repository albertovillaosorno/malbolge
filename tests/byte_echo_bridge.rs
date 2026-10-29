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
//   - Executable VM evidence for the bounded ternary-to-layout byte-echo bridge.
// - Must-Not:
//   - Claim EOF, failed I/O, arbitrary C execution or general runtime linkage.
// - Allows:
//   - Inputs: freshly lowered typed projections and canonical target programs.
//   - Outputs: end-to-end VM byte-trace assertions and negative admissions.
//   - Side effects: bounded in-memory VM execution only.
// - Split-When:
//   - A broader effect trace needs distinct runtime verification.
// - Merge-When:
//   - A complete target linker shares the same exact proof obligations.
// - Summary:
//   - Verifies real executable successful-input/output SSA echo traces.
// - Description:
//   - Checks projection, stage, target encoding, profile and runtime behavior.
// - Usage:
//   - Run cargo test --locked --test byte_echo_bridge.
// - Defaults:
//   - Extra input after the declared trace is not consumed.
//
//! Bounded successful-byte-I/O integration proof on the normative VM.

#[path = "../src/compiler/byte-echo-bridge/composition/lib.rs"]
pub mod bridge;
#[path = "../src/compiler/typed-ir/composition/lib.rs"]
pub mod typed_ir;

use bridge::ternary::{
    InputBlock, InputFunction, InputInstruction, InputScalarType, InputSourcePosition,
    InputSourceSpan, InputTerminator, TernaryOperation, TernaryProgram, TypedIrInput,
    canonical_ternary_bytes, canonical_ternary_program, lower_typed_ir,
};
use bridge::{ByteEchoBridgeError, encode_successful_byte_echo};
use malbolge::{
    ProfileMachine, RunOutcome, current_profile, decode_profile_instruction, historical_profile,
};
use typed_ir::{
    BasicBlock, BasicBlockSpec, BlockId, Function, FunctionId, FunctionSpec, Instruction,
    LocatedInstruction, Module, ModuleSpec, SourcePosition, SourceSpan, Terminator, TypeDef,
    TypeEntry, TypeId, ValueId, canonical_bytes as canonical_typed_bytes, canonical_module,
    validate_module,
};

const fn position(byte: u32) -> InputSourcePosition {
    InputSourcePosition {
        byte,
        column: byte.saturating_add(1),
        line: 1,
    }
}

const fn span(start: u32, end: u32) -> InputSourceSpan {
    InputSourceSpan {
        begin: position(start),
        end: position(end),
    }
}

fn projection(pairs: usize) -> Result<TypedIrInput, String> {
    let mut instructions = Vec::with_capacity(pairs.saturating_mul(2));
    for index in 0..pairs {
        let byte = u32::try_from(index.saturating_mul(2))
            .map_err(|error| format!("fixture source offset: {error}"))?;
        let id =
            u32::try_from(index).map_err(|error| format!("fixture result identity: {error}"))?;
        instructions.push(InputInstruction::ByteInput {
            result: id,
            span: span(byte, byte.saturating_add(1)),
            type_kind: InputScalarType::U8,
        });
        instructions.push(InputInstruction::ByteOutput {
            span: span(byte.saturating_add(1), byte.saturating_add(2)),
            value: id,
        });
    }
    let end = u32::try_from(pairs.saturating_mul(2).saturating_add(1))
        .map_err(|error| format!("fixture function span: {error}"))?;
    Ok(TypedIrInput {
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
            name: String::from("echo"),
            parameter_count: 0,
            return_kind: InputScalarType::Void,
            span: span(0, end),
        }],
        global_count: 0,
        input_format_version: 1,
        proof_obligation_count: 0,
        source_id: String::from("fixtures/byte-echo.c"),
        source_sha256: [0x56; 32],
        target_profile: String::from("malbolge-2026"),
    })
}

fn program(pairs: usize) -> Result<TernaryProgram, String> {
    lower_typed_ir(&projection(pairs)?)
        .map_err(|error| format!("fresh typed projection: {error:?}"))
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "assertions verify generated VM behavior"
)]
#[expect(
    clippy::cognitive_complexity,
    reason = "real VM trace and stage proof in one test"
)]
fn lowered_byte_echo_runs_as_real_malbolge() -> Result<(), String> {
    for count in [1, 2, 3, 7, 64] {
        let lowered = program(count)?;
        let canonical =
            canonical_ternary_bytes(&lowered).map_err(|error| format!("wire encode: {error:?}"))?;
        let restored = canonical_ternary_program(&canonical)
            .map_err(|error| format!("wire decode: {error:?}"))?;
        assert_eq!(restored, lowered);
        let profile = current_profile();
        let layout = encode_successful_byte_echo(&restored, profile)
            .map_err(|error| format!("bridge: {error:?}"))?;
        assert_eq!(layout.source().len(), count * 2 + 1);
        assert_eq!(layout.profile_id(), profile.id());
        assert_eq!(layout.profile_fingerprint(), profile.fingerprint());
        for (position, byte) in layout.source().iter().enumerate() {
            let expected = if position == count * 2 {
                b'v'
            } else if position & 1 == 0 {
                profile.input_instruction()
            } else {
                profile.output_instruction()
            };
            assert_eq!(
                decode_profile_instruction(
                    u32::from(*byte),
                    u32::try_from(position).map_err(|error| format!("position: {error}"))?,
                ),
                Some(expected)
            );
        }
        let input = [0, 255, 13, 10, 128, 65, 42]
            .into_iter()
            .cycle()
            .take(count)
            .collect::<Vec<_>>();
        let mut machine = ProfileMachine::from_source(profile, layout.source(), input.clone())
            .map_err(|error| format!("load: {error:?}"))?;
        assert!(matches!(
            machine.run(count * 2 + 1),
            Ok(RunOutcome::Terminated { .. })
        ));
        assert_eq!(machine.output(), input);
        assert_eq!(machine.input_consumed(), count);
        assert_eq!(layout.executed_code_positions().len(), count * 2 + 1);
        assert_eq!(layout.encrypted_code_positions().len(), count * 2);
    }
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "negative admission assertions in test"
)]
fn bridge_rejects_foreign_profile_and_unsupported_shapes() -> Result<(), String> {
    let profile = current_profile();
    let original = program(2)?;
    assert_eq!(
        encode_successful_byte_echo(&original, historical_profile()),
        Err(ByteEchoBridgeError::ProfileMismatch),
    );
    let mut no_pairs = program(0)?;
    assert_eq!(
        encode_successful_byte_echo(&no_pairs, profile),
        Err(ByteEchoBridgeError::UnsupportedEffectTrace),
    );
    no_pairs.functions.push(
        original
            .functions
            .first()
            .ok_or("missing echo function")?
            .clone(),
    );
    assert!(matches!(
        encode_successful_byte_echo(&no_pairs, profile),
        Err(ByteEchoBridgeError::InvalidProgram(_)),
    ));
    let mut reordered = original.clone();
    reordered
        .functions
        .first_mut()
        .ok_or("missing function")?
        .operations
        .swap(1, 2);
    assert_eq!(
        encode_successful_byte_echo(&reordered, profile),
        Err(ByteEchoBridgeError::UnsupportedEffectTrace),
    );
    let mut old_value = original.clone();
    let operation = old_value
        .functions
        .first_mut()
        .and_then(|function| function.operations.get_mut(3))
        .ok_or("missing second output")?;
    let TernaryOperation::ByteOutput { value, .. } = operation else {
        return Err(String::from("expected byte output"));
    };
    *value = 0;
    assert_eq!(
        encode_successful_byte_echo(&old_value, profile),
        Err(ByteEchoBridgeError::UnsupportedEffectTrace),
    );
    let mut foreign = original;
    foreign.target_profile = String::from("malbolge-1998");
    assert!(matches!(
        encode_successful_byte_echo(&foreign, profile),
        Err(ByteEchoBridgeError::InvalidProgram(_)),
    ));
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "negative admission assertions in test"
)]
fn bridge_rejects_non_echo_computation_and_value_returns() -> Result<(), String> {
    let profile = current_profile();
    let mut changed = projection(2)?;
    let instructions = &mut changed
        .functions
        .first_mut()
        .and_then(|function| function.blocks.first_mut())
        .ok_or("missing input function block")?
        .instructions;
    instructions.push(InputInstruction::ConstantInteger {
        bit_width: 8,
        little_endian: vec![0],
        result: 2,
        span: span(4, 5),
        type_kind: InputScalarType::U8,
    });
    let extra = lower_typed_ir(&changed).map_err(|error| format!("lower value: {error:?}"))?;
    assert_eq!(
        encode_successful_byte_echo(&extra, profile),
        Err(ByteEchoBridgeError::UnsupportedEffectTrace),
    );
    let mut returning = projection(1)?;
    let function = returning
        .functions
        .first_mut()
        .ok_or("missing return function")?;
    function.return_kind = InputScalarType::U8;
    function
        .blocks
        .first_mut()
        .ok_or("missing return block")?
        .terminator = InputTerminator::Return {
        span: span(2, 3),
        value: Some(0),
    };
    let return_program =
        lower_typed_ir(&returning).map_err(|error| format!("lower value return: {error:?}"))?;
    assert_eq!(
        encode_successful_byte_echo(&return_program, profile),
        Err(ByteEchoBridgeError::UnsupportedEffectTrace),
    );
    Ok(())
}

#[test]
#[expect(
    clippy::too_many_lines,
    reason = "typed IR fixture and independent VM admission in one test"
)]
#[expect(
    clippy::panic_in_result_fn,
    reason = "real typed IR canonical admission assertions"
)]
fn canonical_typed_ir_byte_echo_reaches_executable_layout() -> Result<(), String> {
    let span = |start, end| {
        let position = |byte: u32| SourcePosition::new(byte, 1, byte.saturating_add(1));
        SourceSpan::new(position(start), position(end))
    };
    let byte_type = TypeId::new(0);
    let signature = TypeId::new(1);
    let module = Module::new(ModuleSpec {
        abi_id: String::from("malbolge-c32-v1"),
        format_version: typed_ir::TYPED_IR_VERSION,
        functions: vec![Function::new(FunctionSpec {
            blocks: vec![BasicBlock::new(BasicBlockSpec {
                id: BlockId::new(0),
                instructions: vec![
                    LocatedInstruction::new(
                        Instruction::ByteInput {
                            result: ValueId::new(0),
                            type_id: byte_type,
                        },
                        span(0, 1),
                    ),
                    LocatedInstruction::new(
                        Instruction::ByteOutput {
                            value: ValueId::new(0),
                        },
                        span(1, 2),
                    ),
                ],
                phis: Vec::new(),
                span: span(0, 3),
                terminator: Terminator::Return { value: None },
                terminator_span: span(2, 3),
            })],
            entry: BlockId::new(0),
            id: FunctionId::new(0),
            name: String::from("echo"),
            parameters: Vec::new(),
            signature,
            span: span(0, 3),
        })],
        globals: Vec::new(),
        proof_obligations: Vec::new(),
        source_id: String::from("fixtures/byte-echo.c"),
        source_sha256: [0x56; 32],
        target_profile: String::from("malbolge-2026"),
        types: vec![
            TypeEntry::new(byte_type, TypeDef::U8),
            TypeEntry::new(signature, TypeDef::function(Vec::new(), None, false)),
        ],
    });
    validate_module(&module).map_err(|error| format!("typed IR admission: {error:?}"))?;
    let bytes = canonical_typed_bytes(&module)
        .map_err(|error| format!("typed IR serialization: {error:?}"))?;
    let restored =
        canonical_module(&bytes).map_err(|error| format!("typed IR restoration: {error:?}"))?;
    assert_eq!(restored, module);
    let expected = projection(1)?;
    assert_eq!(restored.abi_id(), expected.abi_id);
    assert_eq!(restored.source_id(), expected.source_id);
    assert_eq!(*restored.source_sha256(), expected.source_sha256);
    assert_eq!(restored.target_profile(), expected.target_profile);
    assert_eq!(restored.functions().len(), expected.functions.len());
    let input = lowered_verified_typed_echo(&restored, &expected)?;
    let layout = encode_successful_byte_echo(&input, current_profile())
        .map_err(|error| format!("typed-IR to Malbolge: {error:?}"))?;
    let mut machine = ProfileMachine::from_source(current_profile(), layout.source(), vec![173])
        .map_err(|error| format!("VM load: {error:?}"))?;
    assert!(matches!(machine.run(3), Ok(RunOutcome::Terminated { .. })));
    assert_eq!(machine.output(), &[173]);
    Ok(())
}

// The original typed-IR producer and this separate semantic projection must
// agree on the full supported effect sequence and terminator before lowering.
fn lowered_verified_typed_echo(
    module: &Module,
    projected: &TypedIrInput,
) -> Result<TernaryProgram, String> {
    let [function] = module.functions() else {
        return Err(String::from("not one function"));
    };
    let [block] = function.blocks() else {
        return Err(String::from("not one block"));
    };
    let [first, second] = block.instructions() else {
        return Err(String::from("not two instructions"));
    };
    let [projected_function] = projected.functions.as_slice() else {
        return Err(String::from("not one projected function"));
    };
    let [projected_block] = projected_function.blocks.as_slice() else {
        return Err(String::from("not one projected block"));
    };
    let [
        InputInstruction::ByteInput {
            result,
            span: source_in,
            type_kind,
        },
        InputInstruction::ByteOutput {
            value,
            span: source_out,
        },
    ] = projected_block.instructions.as_slice()
    else {
        return Err(String::from("wrong projected operation kinds"));
    };
    let (
        Instruction::ByteInput {
            result: original,
            type_id,
        },
        Instruction::ByteOutput { value: output },
    ) = (first.instruction(), second.instruction())
    else {
        return Err(String::from("wrong typed operation kinds"));
    };
    if *result != original.value()
        || *result != output.value()
        || *value != output.value()
        || *type_id != TypeId::new(0)
        || *type_kind != InputScalarType::U8
        || *source_in != span_from_typed(first.span())
        || *source_out != span_from_typed(second.span())
        || projected_block.terminator
            != (InputTerminator::Return {
                span: span_from_typed(block.terminator_span()),
                value: None,
            })
    {
        return Err(String::from("typed and projected effects diverge"));
    }
    lower_typed_ir(projected).map_err(|error| format!("typed projection: {error:?}"))
}

const fn span_from_typed(source: SourceSpan) -> InputSourceSpan {
    let start = source.begin();
    let end = source.end();
    InputSourceSpan {
        begin: InputSourcePosition {
            byte: start.byte(),
            column: start.column(),
            line: start.line(),
        },
        end: InputSourcePosition {
            byte: end.byte(),
            column: end.column(),
            line: end.line(),
        },
    }
}

#[test]
#[expect(clippy::panic_in_result_fn, reason = "bounds rejection assertion")]
fn overly_large_echo_trace_rejects_before_source_emission() -> Result<(), String> {
    let lowered = program(2048)?;
    assert_eq!(
        encode_successful_byte_echo(&lowered, current_profile()),
        Err(ByteEchoBridgeError::Layout(
            bridge::layout::LinearLayoutError::TooLong
        )),
    );
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "all-byte VM output comparison is the test oracle"
)]
fn all_256_successful_guest_byte_values_execute_exactly() -> Result<(), String> {
    // One execution covers every possible successful u8 byte, including
    // NUL, high-bit bytes and 0xff, without conflating 0xff with EOF.
    const BYTE_VALUES: usize = 256;
    let lowered = program(BYTE_VALUES)?;
    let wire = canonical_ternary_bytes(&lowered)
        .map_err(|error| format!("all-byte ternary encode: {error:?}"))?;
    let restored = canonical_ternary_program(&wire)
        .map_err(|error| format!("all-byte ternary restore: {error:?}"))?;
    assert_eq!(restored, lowered);
    let layout = encode_successful_byte_echo(&restored, current_profile())
        .map_err(|error| format!("all-byte target encode: {error:?}"))?;
    assert_eq!(layout.source().len(), 513);
    let bytes = (0..=u8::MAX).collect::<Vec<_>>();
    let mut machine =
        ProfileMachine::from_source(current_profile(), layout.source(), bytes.clone())
            .map_err(|error| format!("all-byte VM load: {error:?}"))?;
    assert!(matches!(
        machine.run(513),
        Ok(RunOutcome::Terminated { steps: 513, .. })
    ));
    assert_eq!(machine.output(), bytes);
    assert_eq!(machine.input_consumed(), BYTE_VALUES);
    Ok(())
}
