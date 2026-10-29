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
//   - Bounded repeat-echo compression cost and independent host-expansion evidence.
// - Must-Not:
//   - Treat compressed data as guest-executed Malbolge bytecode.
// - Allows:
//   - Inputs: fresh and canonical ternary echo programs, malformed candidates.
//   - Outputs: exact direct-layout and host-side expansion comparisons.
//   - Side effects: bounded in-memory normative VM execution only.
// - Split-When:
//   - A genuine reusable guest interpreter becomes executable.
// - Merge-When:
//   - A complete independently verified guest-bytecode backend exists.
// - Summary:
//   - Contrasts optimistic macro payload size with verified direct target code.
// - Description:
//   - Checks all 256 byte values and rejects forged bytecode/source shapes.
// - Usage:
//   - `cargo test --locked --test compact_guest_bytecode_strategy`.
// - Defaults:
//   - Size break-even is hypothetical, not a runtime result.
//
//! Research-only bytecode candidate, validated through actual direct VM code.

#[path = "../algorithms/compact-guest-bytecode-strategy/echo_macro.rs"]
pub mod strategy;

use malbolge::{ProfileMachine, RunOutcome, current_profile, historical_profile};

use strategy::bridge::ternary::{
    InputBlock, InputFunction, InputInstruction, InputScalarType, InputSourcePosition,
    InputSourceSpan, InputTerminator, TernaryOperation, TernaryProgram, TypedIrInput,
    canonical_ternary_bytes, canonical_ternary_program, lower_typed_ir,
};
use strategy::{
    ECHO_MACRO_BYTES, EchoMacroError, admit_echo_macro, encode_echo_macro,
    maximum_runtime_cells_for_strict_size_win, maximum_runtime_cells_with_binding,
};

const PILOT_CASES: [usize; 8] = [1, 2, 3, 7, 20, 64, 256, 2047];
const PILOT_CONFIG: &str =
    include_str!("../algorithms/compact-guest-bytecode-strategy/pilot-v0.toml");

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

fn source(pairs: usize) -> Result<TypedIrInput, String> {
    let mut instructions = Vec::with_capacity(pairs.saturating_mul(2));
    for index in 0..pairs {
        let byte = u32::try_from(index.saturating_mul(2))
            .map_err(|error| format!("source byte offset: {error}"))?;
        let result =
            u32::try_from(index).map_err(|error| format!("source value identity: {error}"))?;
        instructions.push(InputInstruction::ByteInput {
            result,
            span: span(byte, byte.saturating_add(1)),
            type_kind: InputScalarType::U8,
        });
        instructions.push(InputInstruction::ByteOutput {
            span: span(byte.saturating_add(1), byte.saturating_add(2)),
            value: result,
        });
    }
    let end = u32::try_from(pairs.saturating_mul(2).saturating_add(1))
        .map_err(|error| format!("function span end: {error}"))?;
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
            name: String::from("research_echo"),
            parameter_count: 0,
            return_kind: InputScalarType::Void,
            span: span(0, end),
        }],
        global_count: 0,
        input_format_version: 1,
        proof_obligation_count: 0,
        source_id: String::from("research/compact-echo.c"),
        source_sha256: [0x51; 32],
        target_profile: String::from("malbolge-2026"),
    })
}

fn program(pairs: usize) -> Result<TernaryProgram, String> {
    let lowered = lower_typed_ir(&source(pairs)?)
        .map_err(|error| format!("lower admitted research projection: {error:?}"))?;
    let bytes = canonical_ternary_bytes(&lowered)
        .map_err(|error| format!("canonical research checkpoint: {error:?}"))?;
    let decoded = canonical_ternary_program(&bytes)
        .map_err(|error| format!("restore research checkpoint: {error:?}"))?;
    if decoded != lowered {
        return Err(String::from("canonical research checkpoint mismatch"));
    }
    Ok(decoded)
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "independent direct source comparison"
)]
fn canonical_echo_macro_expands_to_identical_verified_code() -> Result<(), String> {
    for pairs in PILOT_CASES {
        let original = program(pairs)?;
        let candidate = encode_echo_macro(&original, current_profile())
            .map_err(|error| format!("encode {pairs} pairs: {error:?}"))?;
        let expanded = admit_echo_macro(&original, current_profile(), &candidate)
            .map_err(|error| format!("admit {pairs} pairs: {error:?}"))?;
        let direct = strategy::bridge::encode_successful_byte_echo(&original, current_profile())
            .map_err(|error| format!("direct layout {pairs} pairs: {error:?}"))?;
        assert_eq!(expanded.source(), direct.source());
        assert_eq!(expanded, direct);
        assert_eq!(candidate.len(), ECHO_MACRO_BYTES);
        assert_eq!(
            expanded.source().len(),
            pairs.saturating_mul(2).saturating_add(1)
        );
        assert_eq!(
            maximum_runtime_cells_for_strict_size_win(expanded.source().len()),
            expanded.source().len().checked_sub(7),
        );
    }
    Ok(())
}

#[test]
#[expect(clippy::panic_in_result_fn, reason = "normative VM byte trace oracle")]
fn all_successful_byte_values_execute_via_host_expansion() -> Result<(), String> {
    let original = program(256)?;
    let candidate = encode_echo_macro(&original, current_profile())
        .map_err(|error| format!("encode: {error:?}"))?;
    let expanded = admit_echo_macro(&original, current_profile(), &candidate)
        .map_err(|error| format!("expand: {error:?}"))?;
    let input = (0..=u8::MAX).collect::<Vec<_>>();
    let mut vm = ProfileMachine::from_source(current_profile(), expanded.source(), input.clone())
        .map_err(|error| format!("normative VM source: {error:?}"))?;
    assert!(matches!(
        vm.run(513),
        Ok(RunOutcome::Terminated { steps: 513, .. })
    ));
    assert_eq!(vm.output(), input);
    assert_eq!(vm.input_consumed(), 256);
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "reject complete malicious candidate set"
)]
fn candidate_parser_rejects_truncation_magic_count_and_trailing_data() -> Result<(), String> {
    let original = program(7)?;
    let canonical = encode_echo_macro(&original, current_profile())
        .map_err(|error| format!("canonical candidate: {error:?}"))?;
    for cut in 0..ECHO_MACRO_BYTES {
        assert_eq!(
            admit_echo_macro(
                &original,
                current_profile(),
                canonical.get(..cut).ok_or("missing candidate prefix")?
            ),
            Err(EchoMacroError::InvalidCandidate),
        );
    }
    let mut appended = canonical.to_vec();
    appended.push(0);
    assert_eq!(
        admit_echo_macro(&original, current_profile(), &appended),
        Err(EchoMacroError::InvalidCandidate),
    );
    for index in 0..4 {
        let mut corrupted = canonical;
        let byte = corrupted.get_mut(index).ok_or("missing version byte")?;
        *byte ^= 0xff;
        assert_eq!(
            admit_echo_macro(&original, current_profile(), &corrupted),
            Err(EchoMacroError::InvalidCandidate),
        );
    }
    for count in [0u16, 1, 6, 8, 2048, u16::MAX] {
        let mut corrupted = canonical;
        let Some(pair_bytes) = corrupted.get_mut(4..6) else {
            return Err(String::from("missing count bytes"));
        };
        pair_bytes.copy_from_slice(&count.to_le_bytes());
        assert_eq!(
            admit_echo_macro(&original, current_profile(), &corrupted),
            Err(EchoMacroError::InvalidCandidate),
        );
    }
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "explicit failure edge comparisons"
)]
fn candidate_rejects_invalid_profile_shape_and_unrepresentable_size() -> Result<(), String> {
    let original = program(2)?;
    assert_eq!(
        encode_echo_macro(&original, historical_profile()),
        Err(EchoMacroError::ProfileMismatch),
    );
    let canonical = encode_echo_macro(&original, current_profile())
        .map_err(|error| format!("canonical candidate: {error:?}"))?;
    assert_eq!(
        admit_echo_macro(&original, historical_profile(), &canonical),
        Err(EchoMacroError::ProfileMismatch),
    );
    assert_eq!(
        encode_echo_macro(&program(0)?, current_profile()),
        Err(EchoMacroError::UnsupportedSource),
    );
    assert_eq!(
        encode_echo_macro(&program(2048)?, current_profile()),
        Err(EchoMacroError::UnsupportedSource),
    );
    let mut substituted = original;
    let [function] = substituted.functions.as_mut_slice() else {
        return Err(String::from("missing function"));
    };
    let Some(TernaryOperation::ByteOutput { value, .. }) = function.operations.get_mut(3) else {
        return Err(String::from("missing later output"));
    };
    *value = 0;
    assert_eq!(
        encode_echo_macro(&substituted, current_profile()),
        Err(EchoMacroError::UnsupportedSource),
    );
    assert_eq!(
        admit_echo_macro(&substituted, current_profile(), &canonical),
        Err(EchoMacroError::UnsupportedSource),
    );
    Ok(())
}

#[test]
fn candidate_never_claims_interpreter_break_even_without_runtime() {
    assert_eq!(maximum_runtime_cells_for_strict_size_win(0), None);
    assert_eq!(maximum_runtime_cells_for_strict_size_win(3), None);
    assert_eq!(maximum_runtime_cells_for_strict_size_win(5), None);
    assert_eq!(maximum_runtime_cells_for_strict_size_win(7), Some(0));
    assert_eq!(maximum_runtime_cells_for_strict_size_win(41), Some(34));
    assert_eq!(maximum_runtime_cells_for_strict_size_win(513), Some(506));
    assert_eq!(maximum_runtime_cells_for_strict_size_win(4095), Some(4088));
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "bit-for-bit hostile bytecode oracle"
)]
fn all_single_byte_candidate_mutations_fail_admission() -> Result<(), String> {
    let original = program(7)?;
    let canonical = encode_echo_macro(&original, current_profile())
        .map_err(|error| format!("canonical candidate: {error:?}"))?;
    for position in 0..ECHO_MACRO_BYTES {
        for replacement in u8::MIN..=u8::MAX {
            let mut modified = canonical;
            let Some(byte) = modified.get_mut(position) else {
                return Err(String::from("missing candidate byte"));
            };
            if *byte == replacement {
                continue;
            }
            *byte = replacement;
            assert_eq!(
                admit_echo_macro(&original, current_profile(), &modified),
                Err(EchoMacroError::InvalidCandidate),
                "mutated candidate byte {position} to {replacement}",
            );
        }
    }
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "explicitly documents missing authentication"
)]
fn macro_is_not_independent_source_or_provenance_authentication() -> Result<(), String> {
    let original = program(3)?;
    let candidate = encode_echo_macro(&original, current_profile())
        .map_err(|error| format!("encode: {error:?}"))?;
    let mut alternate = original.clone();
    alternate.source_id = String::from("research/another-echo.c");
    alternate.source_sha256 = [0xb7; 32];
    assert_ne!(original, alternate);
    let reconstructed = admit_echo_macro(&alternate, current_profile(), &candidate)
        .map_err(|error| format!("same-length alternate program: {error:?}"))?;
    let baseline = strategy::bridge::encode_successful_byte_echo(&alternate, current_profile())
        .map_err(|error| format!("alternate direct source: {error:?}"))?;
    assert_eq!(reconstructed, baseline);
    // The descriptor alone cannot establish which source was intended.
    // Product adoption must bind it to the exact canonical source bytes.
    Ok(())
}

#[test]
fn versioned_pilot_config_cannot_silently_drift_from_test_cases() {
    let documented = "echo_pairs = [1, 2, 3, 7, 20, 64, 256, 2047]";
    assert_eq!(PILOT_CASES, [1, 2, 3, 7, 20, 64, 256, 2047]);
    assert_eq!(
        PILOT_CONFIG
            .lines()
            .filter(|line| line.starts_with("echo_pairs ="))
            .collect::<Vec<_>>(),
        vec![documented],
    );
    for requirement in [
        "schema = \"compact-guest-bytecode-pilot-v0\"",
        "target_profile = \"malbolge-2026\"",
        "ternary_codec = \"malbolge-ternary-ir-v1\"",
        "candidate_codec = \"CEB1-u16le\"",
        "candidate_descriptor_bytes = 6",
        "hypothetical_binding_cells = 32",
        "max_direct_code_cells = 4096",
        "execution_mode = \"host-expansion-to-verified-direct-malbolge-source\"",
    ] {
        assert!(PILOT_CONFIG.lines().any(|line| line == requirement));
    }
}

#[test]
fn hypothetical_32_cell_binding_changes_break_even_without_proving_authentication() {
    for (direct, ceiling) in [
        (3usize, None),
        (5, None),
        (7, None),
        (15, None),
        (41, Some(2)),
        (129, Some(90)),
        (513, Some(474)),
        (4095, Some(4056)),
    ] {
        assert_eq!(maximum_runtime_cells_with_binding(direct, 32), ceiling);
    }
    assert_eq!(
        maximum_runtime_cells_with_binding(usize::MAX, usize::MAX),
        None
    );
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "maximum-size direct VM trace oracle"
)]
fn maximum_admitted_echo_program_executes_all_guest_io_in_order() -> Result<(), String> {
    const PAIRS: usize = 2047;
    let canonical = program(PAIRS)?;
    let code = encode_echo_macro(&canonical, current_profile())
        .map_err(|error| format!("largest legal macro: {error:?}"))?;
    let expanded = admit_echo_macro(&canonical, current_profile(), &code)
        .map_err(|error| format!("largest legal direct program: {error:?}"))?;
    assert_eq!(expanded.source().len(), 4095);
    let input = [0, 255, 128, 10, 13, 65, 42]
        .into_iter()
        .cycle()
        .take(PAIRS)
        .collect::<Vec<_>>();
    let mut vm = ProfileMachine::from_source(current_profile(), expanded.source(), input.clone())
        .map_err(|error| format!("largest legal VM load: {error:?}"))?;
    assert!(matches!(
        vm.run(4095),
        Ok(RunOutcome::Terminated { steps: 4095, .. })
    ));
    assert_eq!(vm.output(), input);
    assert_eq!(vm.input_consumed(), PAIRS);
    Ok(())
}
