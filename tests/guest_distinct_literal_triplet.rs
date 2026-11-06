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
//   - Three distinct, source-bound literal bytes from real Malbolge arithmetic.
// - Must-Not:
//   - Synthesize bytes on the host or accept unwitnessed C output traces.
// - Allows:
//   - Inputs: canonical validated ternary effects under the current profile.
//   - Outputs: three exact VM-produced bytes, step counts, write addresses.
//   - Side effects: none.
// - Split-When:
//   - General multi-byte guest arithmetic supersedes finite witnesses.
// - Merge-When:
//   - The guest literal transition bridge owns arbitrary byte triples.
// - Summary:
//   - Real VM witnesses prove three separate relocated CrazyData writes.
// - Description:
//   - Checks typed SSA bindings, physical layout and guest replay.
// - Usage:
//   - RUSTC=... cargo test --locked --test guest_distinct_literal_triplet
// - Defaults:
//   - No triples except the independent bounded witnesses are admitted.

//! Three distinct guest byte outputs from three actual Malbolge `p` steps.

#[path = "../src/compiler/byte-echo-bridge/composition/lib.rs"]
pub mod bridge;
use bridge::layout::{LinearOpcode, encode_linear_layout};
use bridge::ternary::{
    InputBlock, InputFunction, InputInstruction, InputScalarType, InputSourcePosition,
    InputSourceSpan, InputTerminator, TernaryProgram, TypedIrInput, canonical_ternary_bytes,
    canonical_ternary_program, lower_typed_ir,
};
use bridge::{ByteEchoBridgeError, encode_distinct_literal_triple};
use malbolge::{ProfileMachine, RunOutcome, current_profile};

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

fn source_triplet(bytes: [u8; 3], stale: bool) -> Result<TernaryProgram, String> {
    let mut instructions = Vec::with_capacity(6);
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
            value: if stale && index == 2 { 1 } else { id },
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
                    span: span(6, 7),
                    value: None,
                },
            }],
            entry: 0,
            id: 0,
            name: String::from("guest_triplet"),
            parameter_count: 0,
            return_kind: InputScalarType::Void,
            span: span(0, 7),
        }],
        global_count: 0,
        input_format_version: 1,
        proof_obligation_count: 0,
        source_id: String::from("fixtures/guest-triplet.c"),
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
    reason = "assertions verify real guest arithmetic"
)]
fn three_distinct_bytes_are_written_by_guest_arithmetic() -> Result<(), String> {
    for (padding, expected) in [
        (0usize, *b"Z%H"),
        (1usize, *b"Q.O"),
        (2usize, *b"Y-P"),
        (4usize, *b"T\"O"),
        (6usize, *b"T\"Q"),
    ] {
        let mut operations = vec![LinearOpcode::NoOperation; padding];
        operations.extend([
            LinearOpcode::RelocateDataPointer,
            LinearOpcode::CrazyData,
            LinearOpcode::OutputByte,
            LinearOpcode::CrazyData,
            LinearOpcode::OutputByte,
            LinearOpcode::CrazyData,
            LinearOpcode::OutputByte,
            LinearOpcode::Halt,
        ]);
        let independent = encode_linear_layout(current_profile(), &operations)
            .map_err(|error| format!("layout: {error:?}"))?;
        let writes: Vec<_> = independent
            .data_write_positions()
            .iter()
            .flatten()
            .collect();
        assert_eq!(writes.len(), 3);
        assert!(writes.iter().all(|address| {
            usize::try_from(**address).is_ok_and(|value| value >= independent.source().len())
        }));
        assert!(writes[0] != writes[1] && writes[1] != writes[2] && writes[0] != writes[2]);
        let ternary = source_triplet(expected, false)?;
        let source = encode_distinct_literal_triple(&ternary, current_profile())
            .map_err(|error| format!("bridge: {error:?}"))?;
        assert_eq!(source, independent);
        for input in [Vec::new(), vec![255, 0, 128]] {
            let mut vm = ProfileMachine::from_source(current_profile(), source.source(), input)
                .map_err(|error| format!("load: {error:?}"))?;
            assert!(matches!(vm.run(operations.len()),
                Ok(RunOutcome::Terminated { steps, .. }) if steps == operations.len()));
            assert_eq!(vm.input_consumed(), 0);
            assert_eq!(vm.output(), expected);
        }
    }
    Ok(())
}

#[test]
fn bounded_triple_search_keeps_fibonacci_prefix_explicitly_unsupported()
-> Result<(), String> {
    // First three conditional_fibonacci.c bytes, computed independently
    // from the state updates and the odd-arm XOR 0x5a.
    let prefix = [0x02, 0x59, 0x5f];
    let source = source_triplet(prefix, false)?;
    assert!(matches!(
        encode_distinct_literal_triple(&source, current_profile()),
        Err(ByteEchoBridgeError::UnsupportedEffectTrace)
    ));
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "assert actual guest arithmetic and independent SSA proof"
)]
fn expanded_triple_grammar_realizes_mixed_and_strided_bytes()
-> Result<(), String> {
    for (expected, minimum_writes) in [
        ([b'Z', 0x0a, 0xde], 3usize),
        ([b'Q', b'.', b'Z'], 3),
    ] {
        let program = source_triplet(expected, false)?;
        let layout = encode_distinct_literal_triple(&program, current_profile())
            .map_err(|error| format!("triple {expected:?}: {error:?}"))?;
        let writes: Vec<_> = layout
            .data_write_positions()
            .iter()
            .flatten()
            .copied()
            .collect();
        assert_eq!(writes.len(), minimum_writes);
        assert_eq!(
            writes.iter().copied().collect::<std::collections::BTreeSet<_>>().len(),
            3
        );
        assert!(writes.iter().all(|&address| {
            address >= layout.source().len() as u32
        }));
        for input in [Vec::new(), vec![0, 255, 128]] {
            let mut vm = ProfileMachine::from_source(
                current_profile(), layout.source(), input,
            ).map_err(|error| format!("triple load: {error:?}"))?;
            assert!(matches!(
                vm.run(layout.source().len()),
                Ok(RunOutcome::Terminated { .. })
            ));
            assert_eq!(vm.input_consumed(), 0);
            assert_eq!(vm.output(), expected);
        }
    }
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "assertions verify fail-closed triples"
)]
fn unproved_or_stale_triples_refuse() -> Result<(), String> {
    for (bytes, stale) in [
        (*b"Z%Z", true),
        (*b"Q.O", true),
        (*b"T\"O", true),
    ] {
        let source = source_triplet(bytes, stale)?;
        assert!(matches!(
            encode_distinct_literal_triple(&source, current_profile()),
            Err(ByteEchoBridgeError::UnsupportedEffectTrace)
        ));
    }
    assert!(matches!(
        encode_distinct_literal_triple(
            &source_triplet(*b"Q.O", false)?,
            malbolge::historical_profile()
        ),
        Err(ByteEchoBridgeError::ProfileMismatch)
    ));
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "verify nonadjacent repetition under the normative guest VM"
)]
fn nonadjacent_equal_bytes_require_three_guest_writes() -> Result<(), String> {
    let expected = *b"Z%Z";
    let program = source_triplet(expected, false)?;
    let layout = encode_distinct_literal_triple(&program, current_profile())
        .map_err(|error| format!("nonadjacent triple: {error:?}"))?;
    let writes: Vec<_> = layout
        .data_write_positions()
        .iter()
        .flatten()
        .copied()
        .collect();
    assert_eq!(writes.len(), 3);
    assert_eq!(
        writes
            .iter()
            .copied()
            .collect::<std::collections::BTreeSet<_>>()
            .len(),
        3
    );
    assert!(
        writes
            .iter()
            .all(|&position| { position >= layout.source().len() as u32 })
    );
    for input in [Vec::new(), vec![255, 0, 128]] {
        let mut vm = ProfileMachine::from_source(
            current_profile(),
            layout.source(),
            input,
        )
        .map_err(|error| format!("nonadjacent guest load: {error:?}"))?;
        assert!(matches!(
            vm.run(layout.source().len()),
            Ok(RunOutcome::Terminated { .. })
        ));
        assert_eq!(vm.input_consumed(), 0);
        assert_eq!(vm.output(), expected);
    }
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "verify repeated guest outputs and separate source SSA identities"
)]
fn adjacent_equal_bytes_reuse_a_real_guest_accumulator() -> Result<(), String> {
    let expected = *b"88>";
    let program = source_triplet(expected, false)?;
    let layout = encode_distinct_literal_triple(&program, current_profile())
        .map_err(|error| format!("repeated triple: {error:?}"))?;
    let writes: Vec<_> = layout
        .data_write_positions()
        .iter()
        .flatten()
        .copied()
        .collect();
    assert_eq!(
        writes.len(),
        2,
        "one arithmetic write per changed guest byte"
    );
    assert_ne!(writes[0], writes[1]);
    assert!(
        writes
            .iter()
            .all(|&position| position >= layout.source().len() as u32)
    );
    for input in [Vec::new(), vec![255, 0, 128]] {
        let mut vm = ProfileMachine::from_source(
            current_profile(),
            layout.source(),
            input,
        )
        .map_err(|error| format!("load: {error:?}"))?;
        assert!(matches!(
            vm.run(layout.source().len()),
            Ok(RunOutcome::Terminated { .. })
        ));
        assert_eq!(vm.input_consumed(), 0);
        assert_eq!(vm.output(), expected);
    }
    let stale = source_triplet(expected, true)?;
    assert!(matches!(
        encode_distinct_literal_triple(&stale, current_profile()),
        Err(ByteEchoBridgeError::UnsupportedEffectTrace)
            | Err(ByteEchoBridgeError::InvalidProgram(_))
    ));
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "independent SSA and actual uniform guest output are asserted"
)]
fn uniform_source_distinct_triple_reuses_one_guest_write()
-> Result<(), String> {
    let expected = *b"ZZZ";
    let program = source_triplet(expected, false)?;
    let layout = encode_distinct_literal_triple(&program, current_profile())
        .map_err(|error| format!("uniform triple: {error:?}"))?;
    let writes: Vec<_> = layout
        .data_write_positions()
        .iter()
        .flatten()
        .copied()
        .collect();
    assert_eq!(writes.len(), 1);
    assert!(writes[0] >= layout.source().len() as u32);
    let outputs = layout
        .source()
        .iter()
        .enumerate()
        .filter(|entry| {
            let (position, cell) = *entry;
            malbolge::decode_profile_instruction(
                u32::from(*cell), position as u32,
            ) == Some(current_profile().output_instruction())
        })
        .count();
    assert_eq!(outputs, 3);
    for input in [Vec::new(), vec![255, 0, 128]] {
        let mut vm = ProfileMachine::from_source(
            current_profile(), layout.source(), input,
        ).map_err(|error| format!("uniform triple load: {error:?}"))?;
        assert!(matches!(
            vm.run(layout.source().len()),
            Ok(RunOutcome::Terminated { .. })
        ));
        assert_eq!(vm.input_consumed(), 0);
        assert_eq!(vm.output(), expected);
    }
    let stale = source_triplet(expected, true)?;
    assert!(matches!(
        encode_distinct_literal_triple(&stale, current_profile()),
        Err(ByteEchoBridgeError::UnsupportedEffectTrace)
    ));
    Ok(())
}
