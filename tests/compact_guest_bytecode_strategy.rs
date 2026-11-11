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

#[path = "../algorithms/compact-guest-bytecode-strategy/echo_binding.rs"]
pub mod binding;
#[path = "../algorithms/compact-guest-bytecode-strategy/guest_payload_probe.rs"]
pub mod guest_probe;
#[path = "../algorithms/compact-guest-bytecode-strategy/isolated_dispatch.rs"]
pub mod isolated;
#[path = "../algorithms/compact-guest-bytecode-strategy/graphical_residency.rs"]
pub mod residency;
#[path = "../algorithms/compact-guest-bytecode-strategy/single_opcode.rs"]
pub mod single;
#[path = "../algorithms/compact-guest-bytecode-strategy/echo_macro.rs"]
pub mod strategy;
#[path = "../algorithms/compact-guest-bytecode-strategy/two_opcode.rs"]
pub mod two;

use malbolge::{
    ProfileMachine, RunOutcome, current_profile, decode_profile_instruction, encrypt_profile_cell,
    historical_profile,
};
use std::collections::BTreeSet;
use std::fs;
use std::io::Write as _;
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio, id};

use strategy::bridge::ternary::{
    InputBlock, InputFunction, InputInstruction, InputScalarType, InputSourcePosition,
    InputSourceSpan, InputTerminator, TernaryOperation, TernaryProgram, TypedIrInput,
    canonical_ternary_bytes, canonical_ternary_program, lower_typed_ir,
};
use strategy::{
    ECHO_MACRO_BYTES, EchoMacroError, admit_echo_macro, encode_echo_macro,
    maximum_runtime_cells_for_strict_size_win, maximum_runtime_cells_with_binding,
};

use binding::{
    BOUND_ECHO_MACRO_BYTES, BoundEchoError, admit_bound_echo_macro, encode_bound_echo_macro,
    maximum_bound_runtime_cells,
};

use residency::{
    GRAPHICAL_PAYLOAD_CELLS, GRAPHICAL_TOTAL_CELLS, GraphicalResidencyError,
    admit_bound_resident_source, embed_bound_resident_source, maximum_packed_runtime_cells,
};

use guest_probe::{
    GuestPayloadProbeError, admit_guest_indirect_dispatch_probe, admit_guest_payload_probe,
    embed_guest_indirect_dispatch_probe, embed_guest_payload_probe, guest_probe_source_cells,
    guest_read_address,
};

use isolated::{
    ISOLATED_COUNT_ADDRESS, ISOLATED_JUMP_POSITION, ISOLATED_NO_OPS, ISOLATED_PAYLOAD_START,
    ISOLATED_TOTAL_CELLS, admit_isolated_guest_dispatch, admit_isolated_guest_handlers,
    embed_isolated_guest_dispatch, embed_isolated_guest_handlers,
    validate_isolated_dispatch_geometry,
};
use single::{
    SINGLE_CEB2_START, SINGLE_ECHO_GUEST_STEPS, SINGLE_ECHO_OPCODE_RANK, SINGLE_OPCODE_ADDRESS,
    SINGLE_SOURCE_CELLS, SingleOpcodeError, admit_single_echo_opcode, embed_single_echo_opcode,
};
use two::{
    FIRST_OPCODE_ADDRESS, SECOND_OPCODE_ADDRESS, TWO_CEB2_START, TWO_GUEST_STEPS, TWO_SOURCE_CELLS,
    TwoOpcodeError, admit_two_echo_opcodes, embed_two_echo_opcodes,
};

const BOUND_PILOT_CONFIG: &str =
    include_str!("../algorithms/compact-guest-bytecode-strategy/pilot-v1.toml");

const GUEST_PROBE_CONFIG: &str =
    include_str!("../algorithms/compact-guest-bytecode-strategy/pilot-v3.toml");
const SINGLE_OPCODE_CONFIG: &str =
    include_str!("../algorithms/compact-guest-bytecode-strategy/pilot-v6.toml");
const TWO_OPCODE_CONFIG: &str =
    include_str!("../algorithms/compact-guest-bytecode-strategy/pilot-v7.toml");
const ISOLATED_DISPATCH_CONFIG: &str =
    include_str!("../algorithms/compact-guest-bytecode-strategy/pilot-v5.toml");
const ISOLATED_HANDLERS_CONFIG: &str =
    include_str!("../algorithms/compact-guest-bytecode-strategy/pilot-v5-handlers.toml");
const INDIRECT_DISPATCH_CONFIG: &str =
    include_str!("../algorithms/compact-guest-bytecode-strategy/pilot-v4.toml");

const RESIDENT_PILOT_CONFIG: &str =
    include_str!("../algorithms/compact-guest-bytecode-strategy/pilot-v2.toml");

const PILOT_CASES: [usize; 8] = [1, 2, 3, 7, 20, 64, 256, 2047];
const PILOT_CONFIG: &str =
    include_str!("../algorithms/compact-guest-bytecode-strategy/pilot-v0.toml");

struct OwnedArtifactFixture {
    root: PathBuf,
}

impl OwnedArtifactFixture {
    fn new(case: usize) -> Result<Self, String> {
        let root = Path::new(env!("CARGO_MANIFEST_DIR"))
            .join(".temp")
            .join(format!("compact-bytecode-baseline-{}-{case}", id()));
        #[expect(clippy::create_dir, reason = "never reuse another run's fixture")]
        fs::create_dir(&root).map_err(|error| format!("fixture directory: {error}"))?;
        Ok(Self { root })
    }

    fn path(&self, basename: &str) -> PathBuf {
        self.root.join(basename)
    }
}

impl Drop for OwnedArtifactFixture {
    fn drop(&mut self) {
        drop(fs::remove_dir_all(&self.root));
    }
}

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

fn compare_published_direct_baseline(pairs: usize) -> Result<(), String> {
    let fixture = OwnedArtifactFixture::new(pairs)?;
    let original = program(pairs)?;
    let macro_bytes = encode_echo_macro(&original, current_profile())
        .map_err(|error| format!("candidate: {error:?}"))?;
    let independently_expanded = admit_echo_macro(&original, current_profile(), &macro_bytes)
        .map_err(|error| format!("expanded candidate: {error:?}"))?;
    let bound = encode_bound_echo_macro(&original, current_profile())
        .map_err(|error| format!("bound candidate: {error:?}"))?;
    let bound_expanded = admit_bound_echo_macro(&original, current_profile(), &bound)
        .map_err(|error| format!("expanded bound candidate: {error:?}"))?;
    let wire = canonical_ternary_bytes(&original)
        .map_err(|error| format!("canonical source: {error:?}"))?;
    let input_path = fixture.path("source.mctr");
    let output_path = fixture.path("source.malbolge");
    fs::write(&input_path, wire).map_err(|error| format!("write ternary wire: {error}"))?;
    let outcome = Command::new(env!("CARGO_BIN_EXE_malbolge_layout"))
        .arg("--profile")
        .arg(current_profile().id())
        .arg("--output")
        .arg(&output_path)
        .arg("--")
        .arg("--ternary-file")
        .arg(&input_path)
        .output()
        .map_err(|error| format!("invoke real source publisher: {error}"))?;
    if !outcome.status.success() {
        return Err(format!(
            "publisher rejected {pairs} pairs: {}",
            String::from_utf8_lossy(&outcome.stderr),
        ));
    }
    let actual =
        fs::read(&output_path).map_err(|error| format!("read published source: {error}"))?;
    if actual != independently_expanded.source() || actual != bound_expanded.source() {
        return Err(format!(
            "published, CEB1 and independently bound CEB2 source diverge for {pairs} pairs"
        ));
    }
    Ok(())
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

#[test]
fn published_real_malbolge_baseline_matches_structural_expansion() -> Result<(), String> {
    for pairs in [1, 7, 64, 256] {
        compare_published_direct_baseline(pairs)?;
    }
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "separate bound research baseline"
)]
fn canonical_bound_echo_macro_admits_exact_direct_source() -> Result<(), String> {
    for pairs in PILOT_CASES {
        let original = program(pairs)?;
        let encoded = encode_bound_echo_macro(&original, current_profile())
            .map_err(|error| format!("bound encode {pairs}: {error:?}"))?;
        assert_eq!(encoded.len(), BOUND_ECHO_MACRO_BYTES);
        assert_eq!(&encoded[..4], b"CEB2");
        let decoded = admit_bound_echo_macro(&original, current_profile(), &encoded)
            .map_err(|error| format!("bound admit {pairs}: {error:?}"))?;
        let direct = strategy::bridge::encode_successful_byte_echo(&original, current_profile())
            .map_err(|error| format!("baseline {pairs}: {error:?}"))?;
        assert_eq!(decoded.source(), direct.source());
        assert_eq!(
            maximum_bound_runtime_cells(decoded.source().len()),
            decoded.source().len().checked_sub(39),
        );
    }
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "negative same-shape provenance tests"
)]
fn bound_candidate_rejects_valid_equal_shape_foreign_sources() -> Result<(), String> {
    let original = program(7)?;
    let encoded = encode_bound_echo_macro(&original, current_profile())
        .map_err(|error| format!("encode bound: {error:?}"))?;
    let mut alternates = Vec::new();
    let mut changed_path = original.clone();
    changed_path.source_id = String::from("research/foreign.c");
    alternates.push(changed_path);
    let mut changed_hash = original.clone();
    changed_hash.source_sha256 = [0xb7; 32];
    alternates.push(changed_hash);
    let mut changed_name = original.clone();
    changed_name
        .functions
        .first_mut()
        .ok_or("missing source function")?
        .name = String::from("foreign_echo");
    alternates.push(changed_name);
    let mut invalid_abi = original.clone();
    invalid_abi.abi_id = String::from("research-private-abi-v1");
    assert!(matches!(
        encode_bound_echo_macro(&invalid_abi, current_profile()),
        Err(BoundEchoError::Echo(EchoMacroError::Program(_))),
    ));
    for alternate in &alternates {
        let structural = encode_echo_macro(alternate, current_profile())
            .map_err(|error| format!("alternate structural: {error:?}"))?;
        assert_eq!(
            structural,
            encode_echo_macro(&original, current_profile())
                .map_err(|error| format!("original structural: {error:?}"))?
        );
        assert_eq!(
            admit_bound_echo_macro(alternate, current_profile(), &encoded),
            Err(BoundEchoError::SourceMismatch),
        );
        let distinct = encode_bound_echo_macro(alternate, current_profile())
            .map_err(|error| format!("alternate bound: {error:?}"))?;
        assert_ne!(encoded, distinct);
    }
    Ok(())
}

#[test]
#[expect(clippy::panic_in_result_fn, reason = "candidate mutation matrix")]
fn bound_candidate_rejects_every_single_byte_mutation_and_downgrade() -> Result<(), String> {
    let original = program(7)?;
    let encoded = encode_bound_echo_macro(&original, current_profile())
        .map_err(|error| format!("bound encode: {error:?}"))?;
    for size in 0..BOUND_ECHO_MACRO_BYTES {
        assert_eq!(
            admit_bound_echo_macro(
                &original,
                current_profile(),
                encoded.get(..size).ok_or("invalid candidate prefix")?
            ),
            Err(BoundEchoError::InvalidCandidate),
        );
    }
    let mut appended = encoded.to_vec();
    appended.push(0);
    assert_eq!(
        admit_bound_echo_macro(&original, current_profile(), &appended),
        Err(BoundEchoError::InvalidCandidate),
    );
    assert_eq!(
        admit_bound_echo_macro(
            &original,
            current_profile(),
            &encode_echo_macro(&original, current_profile())
                .map_err(|error| format!("legacy CEB1: {error:?}"))?
        ),
        Err(BoundEchoError::InvalidCandidate),
    );
    for position in 0..BOUND_ECHO_MACRO_BYTES {
        for replacement in u8::MIN..=u8::MAX {
            let original_byte = encoded.get(position).ok_or("candidate position")?;
            if replacement == *original_byte {
                continue;
            }
            let mut mutated = encoded;
            *mutated
                .get_mut(position)
                .ok_or("candidate mutation position")? = replacement;
            assert!(
                admit_bound_echo_macro(&original, current_profile(), &mutated).is_err(),
                "mutation {position}/{replacement} must reject",
            );
        }
    }
    assert_eq!(
        admit_bound_echo_macro(&original, historical_profile(), &encoded),
        Err(BoundEchoError::Echo(EchoMacroError::ProfileMismatch)),
    );
    Ok(())
}

#[test]
fn versioned_bound_pilot_documented_costs_remain_reproducible() {
    for value in [
        "schema = \"compact-guest-bytecode-pilot-v1\"",
        "target_profile = \"malbolge-2026\"",
        "source_blind_candidate_codec = \"CEB1-u16le\"",
        "source_bound_candidate_codec = \"CEB2-u16le-sha256\"",
        "source_bound_candidate_bytes = 38",
        "binding_domain = \"CEB2-ternary-profile-v1\"",
        "binding_material = \"selected-profile-fingerprint-and-canonical-ternary-bytes\"",
        "echo_pairs = [1, 2, 3, 7, 20, 64, 256, 2047]",
        "source_authentication = \"external-original-canonical-ternary-program-required\"",
    ] {
        assert!(BOUND_PILOT_CONFIG.lines().any(|line| line == value));
    }
    for (direct, allowance) in [
        (3, None),
        (15, None),
        (39, Some(0)),
        (41, Some(2)),
        (513, Some(474)),
        (4095, Some(4056)),
    ] {
        assert_eq!(maximum_bound_runtime_cells(direct), allowance);
    }
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "independent Python SHA-256 wire golden"
)]
fn bound_envelope_digest_matches_independent_canonical_wire_golden() -> Result<(), String> {
    let original = program(7)?;
    let encoded = encode_bound_echo_macro(&original, current_profile())
        .map_err(|error| format!("encode bound golden: {error:?}"))?;
    // Independently generated using Python hashlib.sha256 over:
    // b"CEB2-ternary-profile-v1\0" + selected fingerprint UTF-8 + b"\0" +
    // 587 exact bytes of canonical MCTR for the fixed seven-pair source().
    // The vector tests not only SHA-256 rounds but also envelope framing.
    assert_eq!(
        current_profile().fingerprint(),
        "malbolge-profile-v1:sha256:8a93ad8fee1d3be48c432c23a74cff5ed50d85e07444dcecece103e4fe22c16e",
    );
    let canonical = canonical_ternary_bytes(&original)
        .map_err(|error| format!("canonical golden source: {error:?}"))?;
    assert_eq!(canonical.len(), 587);
    assert_eq!(
        encoded[6..].iter().fold(String::new(), |mut text, byte| {
            use std::fmt::Write as _;
            assert!(write!(&mut text, "{byte:02x}").is_ok());
            text
        }),
        "5b65a62d87e7a3a3e9c938065ff4f258e4b12be3ff2932891e93523a5f1e7ebc",
    );
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "bounded literal residency experiment"
)]
fn bound_descriptor_physically_resides_in_loader_admissible_source() -> Result<(), String> {
    assert_eq!(GRAPHICAL_PAYLOAD_CELLS, 102);
    assert_eq!(
        GRAPHICAL_PAYLOAD_CELLS,
        BOUND_ECHO_MACRO_BYTES.saturating_mul(8).div_ceil(3),
    );
    assert_eq!(GRAPHICAL_TOTAL_CELLS, 105);
    for pairs in PILOT_CASES {
        let original = program(pairs)?;
        let bound = encode_bound_echo_macro(&original, current_profile())
            .map_err(|error| format!("bound {pairs}: {error:?}"))?;
        let resident = embed_bound_resident_source(&original, current_profile(), &bound)
            .map_err(|error| format!("residency {pairs}: {error:?}"))?;
        assert_eq!(resident.len(), GRAPHICAL_TOTAL_CELLS);
        assert!(resident.iter().all(|byte| (33..=126).contains(byte)));
        assert!(
            resident
                .iter()
                .copied()
                .enumerate()
                .all(|(position, glyph)| {
                    matches!(
                        decode_profile_instruction(
                            u32::from(glyph),
                            u32::try_from(position).unwrap_or(u32::MAX)
                        ),
                        Some(b'j' | b'i' | b'*' | b'p' | b'<' | b'/' | b'v' | b'o')
                    )
                })
        );
        let recovered = admit_bound_resident_source(&original, current_profile(), &resident)
            .map_err(|error| format!("read {pairs}: {error:?}"))?;
        assert_eq!(recovered, bound);
    }
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "real VM loader and guest evidence"
)]
fn loaded_ce_b2_data_is_preserved_but_never_interpreted_by_guest() -> Result<(), String> {
    let original = program(7)?;
    let bound = encode_bound_echo_macro(&original, current_profile())
        .map_err(|error| format!("bound: {error:?}"))?;
    let resident = embed_bound_resident_source(&original, current_profile(), &bound)
        .map_err(|error| format!("source: {error:?}"))?;
    for input in [0u8, 255, 128] {
        let mut vm = ProfileMachine::from_source(current_profile(), &resident, vec![input])
            .map_err(|error| format!("real profile loader: {error:?}"))?;
        for (position, glyph) in resident.iter().copied().enumerate().skip(3) {
            let address = u32::try_from(position).map_err(|error| error.to_string())?;
            assert_eq!(
                vm.memory_word(address)
                    .map_err(|error| format!("initial memory: {error:?}"))?,
                u32::from(glyph)
            );
        }
        assert!(matches!(
            vm.run(3),
            Ok(RunOutcome::Terminated { steps: 3, .. })
        ));
        assert_eq!(vm.output(), [input]);
        assert_eq!(vm.input_consumed(), 1);
        // Exact memory words remain untouched: the VM did NOT decode the CEB2
        // guest proposal or execute the extra source positions.
        for (position, glyph) in resident.iter().copied().enumerate().skip(3) {
            let address = u32::try_from(position).map_err(|error| error.to_string())?;
            assert_eq!(
                vm.memory_word(address)
                    .map_err(|error| format!("post-run memory: {error:?}"))?,
                u32::from(glyph)
            );
        }
    }
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "negative literal residency matrix"
)]
fn graphical_source_corruption_and_noncanonical_padding_are_rejected() -> Result<(), String> {
    let original = program(7)?;
    let bound = encode_bound_echo_macro(&original, current_profile())
        .map_err(|error| format!("bound: {error:?}"))?;
    let resident = embed_bound_resident_source(&original, current_profile(), &bound)
        .map_err(|error| format!("resident: {error:?}"))?;
    for size in 0..GRAPHICAL_TOTAL_CELLS {
        assert_eq!(
            admit_bound_resident_source(
                &original,
                current_profile(),
                resident.get(..size).ok_or("prefix")?
            ),
            Err(GraphicalResidencyError::LengthMismatch),
        );
    }
    let mut extended = resident.clone();
    extended.push(b'o');
    assert_eq!(
        admit_bound_resident_source(&original, current_profile(), &extended),
        Err(GraphicalResidencyError::LengthMismatch),
    );
    let mut bad_prefix = resident.clone();
    *bad_prefix.get_mut(0).ok_or("prefix byte")? = b'!';
    assert_eq!(
        admit_bound_resident_source(&original, current_profile(), &bad_prefix),
        Err(GraphicalResidencyError::PrefixMismatch),
    );
    let mut bad_glyph = resident;
    *bad_glyph.get_mut(3).ok_or("tail byte")? = b' ';
    assert_eq!(
        admit_bound_resident_source(&original, current_profile(), &bad_glyph),
        Err(GraphicalResidencyError::InvalidPayloadCell { position: 3 }),
    );
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "independently reject forged glyphs"
)]
fn loader_valid_graphical_payload_mutations_fail_host_reconstruction() -> Result<(), String> {
    let original = program(7)?;
    let bound = encode_bound_echo_macro(&original, current_profile())
        .map_err(|error| format!("bound: {error:?}"))?;
    let resident = embed_bound_resident_source(&original, current_profile(), &bound)
        .map_err(|error| format!("resident: {error:?}"))?;
    // Every alternative *loader-admissible* glyph at each payload position
    // changes at least one descriptor bit, hence the source-bound digest or
    // canonical bit padding must reject it. This tests valid-looking forgeries.
    for position in 3..GRAPHICAL_TOTAL_CELLS {
        for glyph in 33u8..=126u8 {
            if resident.get(position) == Some(&glyph) {
                continue;
            }
            let decoded = decode_profile_instruction(
                u32::from(glyph),
                u32::try_from(position).map_err(|error| error.to_string())?,
            );
            if !matches!(
                decoded,
                Some(b'j' | b'i' | b'*' | b'p' | b'<' | b'/' | b'v' | b'o')
            ) {
                continue;
            }
            let mut forged = resident.clone();
            *forged.get_mut(position).ok_or("forge slot")? = glyph;
            assert!(
                admit_bound_resident_source(&original, current_profile(), &forged).is_err(),
                "loader-valid forged glyph at {position} must reject"
            );
        }
    }
    let mut another_source = original;
    another_source.source_id = String::from("research/another-equal-trace.c");
    assert!(matches!(
        admit_bound_resident_source(&another_source, current_profile(), &resident),
        Err(GraphicalResidencyError::Binding(
            BoundEchoError::SourceMismatch
        ))
    ));
    assert!(embed_bound_resident_source(&another_source, current_profile(), &bound).is_err());
    Ok(())
}

#[test]
fn eight_loader_admissible_cells_per_position_and_real_budget() {
    for position in 0..94u32 {
        assert_eq!(
            (33u8..=126u8)
                .filter(|glyph| matches!(
                    decode_profile_instruction(u32::from(*glyph), position),
                    Some(b'j' | b'i' | b'*' | b'p' | b'<' | b'/' | b'v' | b'o')
                ))
                .count(),
            8,
            "loader alphabet at phase {position}"
        );
    }
    for (direct, allowance) in [
        (3usize, None),
        (41, None),
        (103, Some(0)),
        (129, Some(26)),
        (513, Some(410)),
        (4095, Some(3992)),
    ] {
        assert_eq!(maximum_packed_runtime_cells(direct), allowance);
    }
    for line in [
        "schema = \"compact-guest-bytecode-pilot-v2\"",
        "bound_candidate_bytes = 38",
        "loader_legal_glyphs_per_cell = 8",
        "bits_per_cell = 3",
        "payload_cells = 102",
        "canonical_pad_bits = 2",
        "halt_prefix_cells = 3",
        "source_cells = 105",
        "interpretation_status = \"no-guest-payload-decoder-or-dispatch\"",
    ] {
        assert!(RESIDENT_PILOT_CONFIG.lines().any(|entry| entry == line));
    }
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "independent source-bit projection"
)]
#[expect(clippy::integer_division, reason = "exact octet bit positions")]
#[expect(clippy::integer_division_remainder_used, reason = "exact bit indices")]
fn graphical_glyph_ordinal_matches_independent_ce_b2_bit_reference() -> Result<(), String> {
    let original = program(7)?;
    let descriptor = encode_bound_echo_macro(&original, current_profile())
        .map_err(|error| format!("bound: {error:?}"))?;
    let source = embed_bound_resident_source(&original, current_profile(), &descriptor)
        .map_err(|error| format!("resident: {error:?}"))?;
    // Independent bit projection: do not reuse the model's alphabet() or
    // source decoder. Count loader-valid glyphs smaller than each source byte.
    for (offset, glyph) in source.iter().copied().enumerate().skip(3) {
        let position = u32::try_from(offset).map_err(|error| error.to_string())?;
        let rank = (33u8..glyph)
            .filter(|byte| {
                matches!(
                    decode_profile_instruction(u32::from(*byte), position),
                    Some(b'j' | b'i' | b'*' | b'p' | b'<' | b'/' | b'v' | b'o')
                )
            })
            .count();
        assert!(rank < 8, "loader glyph must have one three-bit ordinal");
        for digit_bit in 0..3usize {
            let bit_index = offset
                .saturating_sub(3)
                .saturating_mul(3)
                .saturating_add(digit_bit);
            let expected = descriptor.get(bit_index / 8).map_or(0usize, |byte| {
                usize::from((byte >> (7 - bit_index % 8)) & 1)
            });
            let actual = (rank >> (2 - digit_bit)) & 1;
            assert_eq!(actual, expected, "descriptor bit {bit_index}");
        }
    }
    Ok(())
}

#[test]
#[expect(clippy::panic_in_result_fn, reason = "canonical padding rejection")]
fn last_graphical_cell_rejects_nonzero_two_bit_padding() -> Result<(), String> {
    let original = program(7)?;
    let descriptor = encode_bound_echo_macro(&original, current_profile())
        .map_err(|error| format!("bound: {error:?}"))?;
    let mut source = embed_bound_resident_source(&original, current_profile(), &descriptor)
        .map_err(|error| format!("resident: {error:?}"))?;
    let position = u32::try_from(GRAPHICAL_TOTAL_CELLS.saturating_sub(1))
        .map_err(|error| error.to_string())?;
    let valid = (33u8..=126u8)
        .filter(|glyph| {
            matches!(
                decode_profile_instruction(u32::from(*glyph), position),
                Some(b'j' | b'i' | b'*' | b'p' | b'<' | b'/' | b'v' | b'o')
            )
        })
        .collect::<Vec<_>>();
    let final_glyph = *source.last().ok_or("no last glyph")?;
    let ordinal = valid
        .iter()
        .position(|glyph| *glyph == final_glyph)
        .ok_or("last glyph absent from loader alphabet")?;
    assert!(matches!(ordinal, 0 | 4));
    *source.last_mut().ok_or("last cell")? = *valid
        .get(ordinal.saturating_add(1))
        .ok_or("missing noncanonical glyph")?;
    assert_eq!(
        admit_bound_resident_source(&original, current_profile(), &source),
        Err(GraphicalResidencyError::NoncanonicalPadding),
    );
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "genuine VM payload execution witness"
)]
#[expect(
    clippy::integer_division,
    reason = "independent scalar base-three oracle"
)]
#[expect(
    clippy::integer_division_remainder_used,
    reason = "independent trit oracle"
)]
#[expect(
    clippy::too_many_lines,
    reason = "five-profile-VM-literal-memory witnesses"
)]
#[expect(clippy::cognitive_complexity, reason = "real guest memory read checks")]
fn guest_reads_real_ce_b2_count_glyph_through_relocation_and_rotate() -> Result<(), String> {
    assert_eq!(guest_read_address(current_profile()), Ok(53));
    assert_eq!(guest_probe_source_cells(current_profile()), Ok(143));
    let mut observed = BTreeSet::new();
    for pairs in [1usize, 7, 20, 64, 256] {
        let original = program(pairs)?;
        let descriptor = encode_bound_echo_macro(&original, current_profile())
            .map_err(|error| format!("bound {pairs}: {error:?}"))?;
        let emitted = embed_guest_payload_probe(&original, current_profile(), &descriptor)
            .map_err(|error| format!("embed {pairs}: {error:?}"))?;
        assert_eq!(emitted.len(), 143);
        let recovered = admit_guest_payload_probe(&original, current_profile(), &emitted)
            .map_err(|error| format!("recover {pairs}: {error:?}"))?;
        assert_eq!(recovered, descriptor);
        for (position, glyph) in emitted.iter().copied().enumerate() {
            let code = decode_profile_instruction(
                u32::from(glyph),
                u32::try_from(position).map_err(|error| error.to_string())?,
            );
            assert!(matches!(
                code,
                Some(b'j' | b'i' | b'*' | b'p' | b'<' | b'/' | b'v' | b'o')
            ));
        }
        assert_eq!(emitted.first(), Some(&40));
        let initial_glyph = *emitted.get(53).ok_or("missing resident count glyph")?;
        let modulus = current_profile().word_modulus();
        // Independent trit oracle, deliberately not profile_rotate().
        let glyph_word = u32::from(initial_glyph);
        let expected = glyph_word / 3 + (glyph_word % 3) * (modulus / 3);
        let expected_output =
            u8::try_from(expected % 256).map_err(|error| format!("output byte: {error}"))?;
        let mut vm = ProfileMachine::from_source(current_profile(), &emitted, Vec::new())
            .map_err(|error| format!("profile source loader {pairs}: {error:?}"))?;
        assert_eq!(
            vm.memory_word(53)
                .map_err(|error| format!("read: {error:?}"))?,
            glyph_word
        );
        assert!(matches!(
            vm.run(16),
            Ok(RunOutcome::Terminated { steps: 16, .. })
        ));
        assert_eq!(vm.output(), &[expected_output]);
        assert_eq!(vm.input_consumed(), 0);
        assert_eq!(vm.registers().code_pointer, 15);
        assert_eq!(vm.registers().data_pointer, 55);
        assert_eq!(vm.registers().accumulator, expected);
        assert_eq!(
            vm.memory_word(53)
                .map_err(|error| format!("rotated word: {error:?}"))?,
            expected,
        );
        // All other CEB2 cells were not executed or mutated by the guest.
        for position in 41u32..143u32 {
            if position == 53 {
                continue;
            }
            let offset = usize::try_from(position).map_err(|error| error.to_string())?;
            assert_eq!(
                vm.memory_word(position)
                    .map_err(|error| format!("tail: {error:?}"))?,
                u32::from(*emitted.get(offset).ok_or("tail glyph")?)
            );
        }
        let _new_output = observed.insert(expected_output);
    }
    assert!(
        observed.len() >= 2,
        "different admitted repeat counts must be guest-observable"
    );
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "adversarial host and guest distinctions"
)]
#[expect(
    clippy::integer_division,
    reason = "independent trit output projection"
)]
#[expect(
    clippy::integer_division_remainder_used,
    reason = "scalar base-three oracle"
)]
fn guest_probed_count_cell_mutation_changes_guest_output_but_fails_host_admission()
-> Result<(), String> {
    let original = program(7)?;
    let candidate = encode_bound_echo_macro(&original, current_profile())
        .map_err(|error| format!("bound: {error:?}"))?;
    let source = embed_guest_payload_probe(&original, current_profile(), &candidate)
        .map_err(|error| format!("guest probe: {error:?}"))?;
    let before = *source.get(53).ok_or("initial count cell")?;
    let mut replaced = source.clone();
    let replacement = (33u8..=126u8)
        .find(|glyph| {
            *glyph != before
                && matches!(
                    decode_profile_instruction(u32::from(*glyph), 53),
                    Some(b'j' | b'i' | b'*' | b'p' | b'<' | b'/' | b'v' | b'o')
                )
                && (u32::from(*glyph) / 3
                    + (u32::from(*glyph) % 3) * (current_profile().word_modulus() / 3))
                    % 256
                    != (u32::from(before) / 3
                        + (u32::from(before) % 3) * (current_profile().word_modulus() / 3))
                        % 256
        })
        .ok_or("no distinct loader-valid count glyph")?;
    *replaced.get_mut(53).ok_or("read cell")? = replacement;
    assert!(matches!(
        admit_guest_payload_probe(&original, current_profile(), &replaced),
        Err(GuestPayloadProbeError::Binding(_))
    ));
    let mut original_vm = ProfileMachine::from_source(current_profile(), &source, Vec::new())
        .map_err(|error| format!("old source: {error:?}"))?;
    let mut forged_vm = ProfileMachine::from_source(current_profile(), &replaced, Vec::new())
        .map_err(|error| format!("forged loader-valid source: {error:?}"))?;
    assert!(matches!(
        original_vm.run(16),
        Ok(RunOutcome::Terminated { steps: 16, .. })
    ));
    assert!(matches!(
        forged_vm.run(16),
        Ok(RunOutcome::Terminated { steps: 16, .. })
    ));
    assert_ne!(original_vm.output(), forged_vm.output());
    assert_eq!(forged_vm.input_consumed(), 0);
    assert_eq!(forged_vm.registers().data_pointer, 55);
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "host check cannot trust guest glyphs"
)]
fn guest_probe_host_rejects_shifted_truncated_and_forged_sources() -> Result<(), String> {
    let original = program(7)?;
    let candidate = encode_bound_echo_macro(&original, current_profile())
        .map_err(|error| format!("bound: {error:?}"))?;
    let source = embed_guest_payload_probe(&original, current_profile(), &candidate)
        .map_err(|error| format!("resident: {error:?}"))?;
    let mut wrong_prefix = source.clone();
    *wrong_prefix.get_mut(1).ok_or("second code glyph")? = b'!';
    assert_eq!(
        admit_guest_payload_probe(&original, current_profile(), &wrong_prefix),
        Err(GuestPayloadProbeError::InvalidSource)
    );
    let mut suffix = source.clone();
    suffix.push(b'!');
    assert_eq!(
        admit_guest_payload_probe(&original, current_profile(), &suffix),
        Err(GuestPayloadProbeError::InvalidSource)
    );
    for length in [0usize, 1, 16, 41, 53, 142] {
        assert_eq!(
            admit_guest_payload_probe(
                &original,
                current_profile(),
                source.get(..length).ok_or("truncated")?
            ),
            Err(GuestPayloadProbeError::InvalidSource),
        );
    }
    let mut other = original;
    other.source_id = String::from("research/another-count-7.c");
    assert_eq!(
        admit_guest_payload_probe(&other, current_profile(), &source),
        Err(GuestPayloadProbeError::Binding(
            BoundEchoError::SourceMismatch
        ))
    );
    assert!(embed_guest_payload_probe(&other, current_profile(), &candidate).is_err());
    Ok(())
}

#[test]
fn guest_probe_v3_configuration_pins_costs_and_no_interpreter_claim() {
    for declaration in [
        "schema = \"compact-guest-bytecode-pilot-v3\"",
        "bound_descriptor_bytes = 38",
        "payload_cells = 102",
        "payload_count_probe_ordinal = 12",
        "reached_guest_steps = 16",
        "reached_guest_code = \"j oooooooooooo * < v\"",
        "reads_genuine_source_resident_data = true",
        "interpreter_present = false",
        "repeat_echo_semantic_equivalence = false",
        "source_authentication_in_guest = false",
    ] {
        assert!(GUEST_PROBE_CONFIG.lines().any(|line| line == declaration));
    }
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "normative per-step source read evidence"
)]
#[expect(
    clippy::integer_division,
    reason = "independent ternary rotation check"
)]
#[expect(
    clippy::integer_division_remainder_used,
    reason = "independent ternary rotation check"
)]
#[expect(
    clippy::cognitive_complexity,
    reason = "complete sixteen-step trace witness"
)]
#[expect(
    clippy::too_many_lines,
    reason = "one exact guest read and write receipt"
)]
fn traced_guest_rotates_loaded_count_cell_not_a_host_supplied_literal() -> Result<(), String> {
    let original = program(7)?;
    let descriptor = encode_bound_echo_macro(&original, current_profile())
        .map_err(|error| format!("descriptor: {error:?}"))?;
    let source = embed_guest_payload_probe(&original, current_profile(), &descriptor)
        .map_err(|error| format!("guest program: {error:?}"))?;
    let original_glyph = u32::from(*source.get(53).ok_or("probe source glyph")?);
    let mut vm = ProfileMachine::from_source(current_profile(), &source, Vec::new())
        .map_err(|error| format!("real VM loader: {error:?}"))?;
    let mut events = Vec::new();
    let outcome = vm
        .run_traced(16, &mut |event| events.push(*event))
        .map_err(|error| format!("real VM trace: {error:?}"))?;
    assert!(matches!(outcome, RunOutcome::Terminated { steps: 16, .. }));
    assert_eq!(events.len(), 16);
    for (index, event) in events.iter().enumerate() {
        assert_eq!(
            event.before.registers.code_pointer,
            u32::try_from(index).map_err(|error| error.to_string())?
        );
        assert_eq!(
            event.memory_reads.fetch.map(|read| read.address),
            Some(u32::try_from(index).map_err(|error| error.to_string())?)
        );
    }
    assert_eq!(events.first().and_then(|event| event.decoded), Some(b'j'));
    assert_eq!(
        events
            .first()
            .and_then(|event| event.memory_reads.data)
            .map(|read| read.value),
        Some(40)
    );
    for event in events.iter().skip(1).take(12) {
        assert_eq!(event.decoded, Some(b'o'));
        assert_eq!(event.memory_reads.data, None);
    }
    let rotate = events.get(13).ok_or("rotation step")?;
    assert_eq!(rotate.decoded, Some(b'*'));
    assert_eq!(rotate.before.registers.data_pointer, 53);
    assert_eq!(
        rotate
            .memory_reads
            .data
            .map(|read| (read.address, read.value)),
        Some((53, original_glyph))
    );
    let expected = original_glyph / 3 + original_glyph % 3 * (current_profile().word_modulus() / 3);
    assert_eq!(
        rotate
            .memory_delta
            .data
            .map(|write| (write.address, write.before, write.after)),
        Some((53, original_glyph, expected))
    );
    assert_eq!(
        rotate.memory_delta.encryption.map(|write| write.address),
        Some(13)
    );
    let output = events.get(14).ok_or("output step")?;
    assert_eq!(output.decoded, Some(current_profile().output_instruction()));
    assert_eq!(output.output, vm.output().first().copied());
    assert_eq!(output.memory_reads.data, None);
    assert_eq!(events.get(15).and_then(|event| event.decoded), Some(b'v'));
    assert_eq!(
        vm.memory_word(53)
            .map_err(|error| format!("data: {error:?}"))?,
        expected
    );
    Ok(())
}

#[expect(
    clippy::panic_in_result_fn,
    reason = "external capsule process witness"
)]
#[expect(clippy::integer_division, reason = "independent scalar output oracle")]
#[expect(
    clippy::integer_division_remainder_used,
    reason = "base-three scalar oracle"
)]
#[expect(clippy::arithmetic_side_effects, reason = "bounded scalar trit oracle")]
fn externally_run_guest_payload_probe(pairs: usize) -> Result<u8, String> {
    let fixture = OwnedArtifactFixture::new(pairs.saturating_add(10_000))?;
    let original = program(pairs)?;
    let bound = encode_bound_echo_macro(&original, current_profile())
        .map_err(|error| format!("CEB2 {pairs}: {error:?}"))?;
    let source = embed_guest_payload_probe(&original, current_profile(), &bound)
        .map_err(|error| format!("guest source {pairs}: {error:?}"))?;
    let restored = admit_guest_payload_probe(&original, current_profile(), &source)
        .map_err(|error| format!("independent source recovery {pairs}: {error:?}"))?;
    assert_eq!(restored, bound, "capsule source must reproduce bound CEB2");
    let read = u32::from(*source.get(53).ok_or("missing count field glyph")?);
    let rotation = read / 3 + read % 3 * (current_profile().word_modulus() / 3);
    let expected = u8::try_from(rotation % 256).map_err(|error| format!("output byte: {error}"))?;
    let capsule = malbolge::build_capsule(current_profile(), &source)
        .map_err(|error| format!("capsule publisher {pairs}: {error}"))?;
    let path = fixture.path("source.malbolge");
    fs::write(&path, &capsule).map_err(|error| format!("publish {pairs}: {error}"))?;
    let output = Command::new(env!("CARGO_BIN_EXE_malbolge"))
        .env_remove("MALBOLGE_PROFILE_ADAPTIVE_WIDTH")
        .env_remove("MALBOLGE_PROFILE_RESIDENT_WORKER")
        .arg(&path)
        .arg("--report-steps")
        .output()
        .map_err(|error| format!("run actual general malbolge CLI {pairs}: {error}"))?;
    assert!(output.status.success(), "general CLI error: {output:?}");
    assert_eq!(
        output.stdout,
        [expected],
        "actual runner CEB2-derived stdout"
    );
    assert_eq!(output.stderr, b"malbolge-steps-v1:16\n", "actual VM steps");
    Ok(expected)
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "two full external process replays"
)]
fn real_general_malbolge_cli_runs_current_profile_resident_data_probe() -> Result<(), String> {
    let count_seven = externally_run_guest_payload_probe(7)?;
    let count_sixty_four = externally_run_guest_payload_probe(64)?;
    assert_ne!(count_seven, count_sixty_four);
    Ok(())
}

/// Proves that the real profile VM chooses its next fetched instruction from
/// an admitted CEB2 count-bearing source cell rather than host-side staging.
#[expect(clippy::panic_in_result_fn, reason = "source-bound guest jump receipt")]
#[expect(
    clippy::cognitive_complexity,
    reason = "reached guest data/code/encryption assertions"
)]
#[expect(
    clippy::too_many_lines,
    reason = "exact guest indirect read/jump/fetch trace"
)]
fn verify_guest_count_indirect_dispatch(pairs: usize) -> Result<u32, String> {
    let original = program(pairs)?;
    let candidate = encode_bound_echo_macro(&original, current_profile())
        .map_err(|error| format!("bound {pairs}: {error:?}"))?;
    let source = embed_guest_indirect_dispatch_probe(&original, current_profile(), &candidate)
        .map_err(|error| format!("embedded dispatch {pairs}: {error:?}"))?;
    assert_eq!(source.len(), 143, "same resident CEB2 placement");
    assert_eq!(source.get(13).copied(), Some(85), "jumps via XLAT1 i@13");
    let read_glyph = u32::from(*source.get(53).ok_or("missing count glyph")?);
    let fetched_address = read_glyph.saturating_add(1);
    assert!(
        (41..143).contains(&fetched_address),
        "must fetch stored data as code"
    );
    let recovered = admit_guest_indirect_dispatch_probe(&original, current_profile(), &source)
        .map_err(|error| format!("host source binding {pairs}: {error:?}"))?;
    assert_eq!(recovered, candidate, "independent source binding");
    let mut vm = ProfileMachine::from_source(current_profile(), &source, Vec::new())
        .map_err(|error| format!("normative loader {pairs}: {error:?}"))?;
    let mut events = Vec::new();
    let prefix = vm
        .run_traced(14, &mut |event| events.push(*event))
        .map_err(|error| format!("normative guest dispatch {pairs}: {error:?}"))?;
    assert!(
        matches!(prefix, RunOutcome::BudgetExhausted { steps: 14 }),
        "guest must reach code-pointer jump on its fourteenth step"
    );
    assert_eq!(
        events.len(),
        14,
        "13 prefix operations and one indirect jump"
    );
    let jump = events.get(13).ok_or("missing reached guest jump")?;
    assert_eq!(jump.decoded, Some(b'i'), "real jump-code instruction");
    assert_eq!(
        jump.before.registers.code_pointer, 13,
        "jump source address"
    );
    assert_eq!(
        jump.before.registers.data_pointer, 53,
        "count cell data address"
    );
    assert_eq!(
        jump.memory_reads
            .data
            .map(|read| (read.address, read.value)),
        Some((53, read_glyph)),
        "semantic read from loaded CEB2 source"
    );
    assert_eq!(
        jump.memory_reads.encryption.map(|read| read.address),
        Some(read_glyph),
        "post-jump XLAT2 targets operand-selected C"
    );
    assert_eq!(
        jump.memory_delta.encryption.map(|write| write.address),
        Some(read_glyph),
        "actual source cell mutated by jump encryption"
    );
    assert_eq!(
        vm.registers().code_pointer,
        fetched_address,
        "actual guest C advances from payload-selected C"
    );
    assert_eq!(vm.registers().data_pointer, 54, "guest D successor after i");
    assert!(
        vm.output().is_empty(),
        "dispatch prefix must not produce echo output"
    );
    let original_target_byte = *source
        .get(usize::try_from(fetched_address).map_err(|error| error.to_string())?)
        .ok_or("missing guest target")?;
    let mut fetched = None;
    let _result = vm
        .step_traced(&mut |event| fetched = Some(*event))
        .map_err(|error| format!("indirect payload fetch {pairs}: {error:?}"))?;
    let reached = fetched.ok_or("missing guest indirect fetch receipt")?;
    assert_eq!(
        reached.before.registers.code_pointer, fetched_address,
        "fetched code must come from descriptor-selected address"
    );
    assert_eq!(
        reached
            .memory_reads
            .fetch
            .map(|read| (read.address, read.value)),
        Some((fetched_address, u32::from(original_target_byte))),
        "guest executes a fetched descriptor glyph, not staged host code"
    );
    assert_eq!(
        reached.decoded,
        decode_profile_instruction(u32::from(original_target_byte), fetched_address),
        "execution decodes the original resident graphical byte at selected phase"
    );
    Ok(fetched_address)
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "exhaust all eight graphical count ranks"
)]
fn all_eight_loader_valid_count_glyphs_drive_distinct_guest_dispatch_targets() -> Result<(), String>
{
    // Bits 36..38 select low-byte count bits 3, 2, 1: (n >> 1) & 7.
    // Rank zero uses n=32 rather than invalid zero echo pairs.
    let mut observed = BTreeSet::new();
    for (pairs, exact_target) in [
        (32usize, 46u32),
        (2, 47),
        (4, 65),
        (6, 81),
        (8, 82),
        (10, 104),
        (12, 110),
        (14, 123),
    ] {
        let reached = verify_guest_count_indirect_dispatch(pairs)?;
        assert_eq!(
            reached, exact_target,
            "independent count-rank oracle for n={pairs}"
        );
        let _distinct = observed.insert(reached);
    }
    assert_eq!(
        observed.len(),
        8,
        "all count glyph ordinals dispatch differently"
    );
    Ok(())
}

#[test]
#[expect(clippy::panic_in_result_fn, reason = "guest/host tampering boundary")]
fn loader_valid_count_mutation_redirects_guest_but_fails_source_bound_admission()
-> Result<(), String> {
    let program = program(12)?;
    let candidate = encode_bound_echo_macro(&program, current_profile())
        .map_err(|error| format!("candidate: {error:?}"))?;
    let original = embed_guest_indirect_dispatch_probe(&program, current_profile(), &candidate)
        .map_err(|error| format!("source: {error:?}"))?;
    let mut tampered = original.clone();
    let old_count = *tampered.get(53).ok_or("original count byte")?;
    let replacement = (33u8..=126u8)
        .find(|&byte| {
            byte != old_count
                && matches!(
                    decode_profile_instruction(u32::from(byte), 53),
                    Some(b'j' | b'i' | b'*' | b'p' | b'<' | b'/' | b'v' | b'o')
                )
        })
        .ok_or("no alternate loader-valid count glyph")?;
    *tampered.get_mut(53).ok_or("replacement count byte")? = replacement;
    assert!(
        admit_guest_indirect_dispatch_probe(&program, current_profile(), &tampered).is_err(),
        "malformed CEB2 cannot pass independently bound host admission"
    );
    let mut vm_before = ProfileMachine::from_source(current_profile(), &original, Vec::new())
        .map_err(|error| format!("original loader: {error:?}"))?;
    let mut vm_after = ProfileMachine::from_source(current_profile(), &tampered, Vec::new())
        .map_err(|error| format!("tampered loader: {error:?}"))?;
    assert!(matches!(
        vm_before.run(14),
        Ok(RunOutcome::BudgetExhausted { steps: 14 })
    ));
    assert!(matches!(
        vm_after.run(14),
        Ok(RunOutcome::BudgetExhausted { steps: 14 })
    ));
    assert_ne!(
        vm_before.registers().code_pointer,
        vm_after.registers().code_pointer,
        "guest dispatch must be controlled by actual CEB2 glyph"
    );
    assert_eq!(
        vm_after.registers().code_pointer,
        u32::from(replacement).saturating_add(1)
    );
    let mut wrong_dispatch = original.clone();
    *wrong_dispatch.get_mut(13).ok_or("dispatch code")? = b'!';
    assert_eq!(
        admit_guest_indirect_dispatch_probe(&program, current_profile(), &wrong_dispatch),
        Err(GuestPayloadProbeError::InvalidSource)
    );
    let mut foreign = program;
    foreign.source_id = String::from("research/forged-count-source.c");
    assert!(admit_guest_indirect_dispatch_probe(&foreign, current_profile(), &original).is_err());
    Ok(())
}

#[test]
fn indirect_dispatch_v4_config_does_not_claim_bytecode_interpretation() {
    for line in [
        "schema = \"compact-guest-bytecode-pilot-v4\"",
        "source_cells = 143",
        "count_glyph_memory_address = 53",
        "first_indirect_jump_step = 14",
        "first_data_selected_fetch_step = 15",
        "jump_target = \"initial_M[53] + 1\"",
        "indirect_dispatch_is_guest_executed = true",
        "packed_ordinal_decoded_by_guest = false",
        "count_loop_present = false",
        "bytecode_interpreter_present = false",
        "semantic_equivalence_to_echo_trace = false",
    ] {
        assert!(
            INDIRECT_DISPATCH_CONFIG
                .lines()
                .any(|actual| actual == line),
            "missing v4 bound declaration: {line}"
        );
    }
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "negative guest code/data overlap witness"
)]
fn indirect_jump_encrypts_descriptor_cell_and_breaks_original_source_binding() -> Result<(), String>
{
    let original = program(12)?;
    let candidate = encode_bound_echo_macro(&original, current_profile())
        .map_err(|error| format!("bound source: {error:?}"))?;
    let source = embed_guest_indirect_dispatch_probe(&original, current_profile(), &candidate)
        .map_err(|error| format!("source: {error:?}"))?;
    let encrypted_address = usize::from(*source.get(53).ok_or("count glyph")?);
    assert!(
        (41..143).contains(&encrypted_address),
        "code/data overlap inside CEB2"
    );
    let original_cell = *source
        .get(encrypted_address)
        .ok_or("original target cell")?;
    let encrypted_cell = encrypt_profile_cell(u32::from(original_cell))
        .ok_or("XLAT2 cannot encrypt graphical source")?;
    assert_ne!(
        encrypted_cell,
        u32::from(original_cell),
        "this witnessed dispatch must mutate the descriptor code/data cell"
    );
    let mut vm = ProfileMachine::from_source(current_profile(), &source, Vec::new())
        .map_err(|error| format!("normative loader: {error:?}"))?;
    let result = vm
        .run(14)
        .map_err(|error| format!("guest dispatch: {error:?}"))?;
    assert!(
        matches!(result, RunOutcome::BudgetExhausted { steps: 14 }),
        "source dispatch must be committed before checking data destruction"
    );
    let actual_cell = vm
        .memory_word(u32::try_from(encrypted_address).map_err(|error| error.to_string())?)
        .map_err(|error| format!("encrypted physical cell: {error:?}"))?;
    assert_eq!(
        actual_cell, encrypted_cell,
        "profile VM must encrypt the source-resident bytecode cell"
    );
    let mut mutated_image = source;
    *mutated_image
        .get_mut(encrypted_address)
        .ok_or("modified cell")? = u8::try_from(actual_cell).map_err(|error| error.to_string())?;
    assert!(
        admit_guest_indirect_dispatch_probe(&original, current_profile(), &mutated_image).is_err(),
        "original CEB2 source binding no longer holds after guest XLAT2"
    );
    Ok(())
}

/// Independent normative VM check of guest-source separated code and CEB2 data.
#[expect(
    clippy::panic_in_result_fn,
    reason = "exact guest jump and source trace"
)]
#[expect(
    clippy::too_many_lines,
    reason = "exact 82-step code/data separation witness"
)]
#[expect(
    clippy::cognitive_complexity,
    reason = "real profile-machine CEB2 preservation oracle"
)]
fn verify_isolated_guest_dispatch(pairs: usize) -> Result<u32, String> {
    let original = program(pairs)?;
    let candidate = encode_bound_echo_macro(&original, current_profile())
        .map_err(|error| format!("bound {pairs}: {error:?}"))?;
    let source = embed_isolated_guest_dispatch(&original, current_profile(), &candidate)
        .map_err(|error| format!("emit separated {pairs}: {error:?}"))?;
    assert_eq!(source.len(), ISOLATED_TOTAL_CELLS, "complete bound source");
    let restored = admit_isolated_guest_dispatch(&original, current_profile(), &source)
        .map_err(|error| format!("admit separated {pairs}: {error:?}"))?;
    assert_eq!(restored, candidate, "source-bound CEB2 must round-trip");
    for (position, &glyph) in source.iter().enumerate() {
        assert!(
            matches!(
                decode_profile_instruction(
                    u32::from(glyph),
                    u32::try_from(position).map_err(|error| error.to_string())?
                ),
                Some(b'j' | b'i' | b'*' | b'p' | b'<' | b'/' | b'v' | b'o')
            ),
            "loader-valid all cells for n={pairs} at position={position}"
        );
    }
    let read_glyph = u32::from(
        *source
            .get(ISOLATED_COUNT_ADDRESS)
            .ok_or("missing separated source count cell")?,
    );
    assert!(
        read_glyph < u32::try_from(ISOLATED_PAYLOAD_START).map_err(|error| error.to_string())?,
        "count-selected C cannot alias CEB2"
    );
    let mut vm = ProfileMachine::from_source(current_profile(), &source, Vec::new())
        .map_err(|error| format!("loader {pairs}: {error:?}"))?;
    let mut reached = None;
    let outcome = vm
        .run_traced(82, &mut |trace| {
            if trace.before.registers.code_pointer == 81 {
                reached = Some(*trace);
            }
        })
        .map_err(|error| format!("real dispatch {pairs}: {error:?}"))?;
    assert!(
        matches!(outcome, RunOutcome::BudgetExhausted { steps: 82 }),
        "guest commits j, eighty o and one i for n={pairs}"
    );
    let jump = reached.ok_or("missing genuine guest i trace")?;
    assert_eq!(jump.decoded, Some(b'i'), "native indirect jump opcode");
    assert_eq!(
        jump.before.registers.code_pointer, 81,
        "reached i at address 81"
    );
    assert_eq!(
        jump.before.registers.data_pointer, 121,
        "guest D points to CEB2 count"
    );
    assert_eq!(
        jump.memory_reads
            .data
            .map(|read| (read.address, read.value)),
        Some((121, read_glyph)),
        "guest read physical descriptor count glyph"
    );
    assert_eq!(
        jump.memory_delta.encryption.map(|write| write.address),
        Some(read_glyph),
        "XLAT2 physically rewrites a code cell only"
    );
    assert_eq!(
        vm.registers().code_pointer,
        read_glyph.saturating_add(1),
        "CEB2 count glyph determines actual next guest fetch"
    );
    assert_eq!(
        vm.registers().data_pointer,
        122,
        "D advances after true jump"
    );
    assert!(vm.output().is_empty(), "this is a control-flow-only probe");
    let mut recovered_memory_image = source.clone();
    for position in ISOLATED_PAYLOAD_START..ISOLATED_TOTAL_CELLS {
        let addr = u32::try_from(position).map_err(|error| error.to_string())?;
        let unchanged = vm
            .memory_word(addr)
            .map_err(|error| format!("VM tail {position}: {error:?}"))?;
        assert_eq!(
            unchanged,
            u32::from(*source.get(position).ok_or("source tail")?),
            "all 102 data glyphs must survive guest self-encryption at {position}"
        );
        *recovered_memory_image
            .get_mut(position)
            .ok_or("image tail")? = u8::try_from(unchanged).map_err(|error| error.to_string())?;
    }
    assert_eq!(
        admit_isolated_guest_dispatch(&original, current_profile(), &recovered_memory_image),
        Ok(candidate),
        "untouched runtime payload must stay authenticated by the host"
    );
    Ok(read_glyph)
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "full eight-rank guest code separation"
)]
fn isolated_dispatch_retains_bound_ce_b2_across_all_eight_guest_jumps() -> Result<(), String> {
    assert_eq!(validate_isolated_dispatch_geometry(), Ok(()));
    assert_eq!(ISOLATED_NO_OPS, 80);
    assert_eq!(ISOLATED_JUMP_POSITION, 81);
    assert_eq!(ISOLATED_PAYLOAD_START, 109);
    assert_eq!(ISOLATED_COUNT_ADDRESS, 121);
    assert_eq!(ISOLATED_TOTAL_CELLS, 211);
    let mut observed = BTreeSet::new();
    for (pairs, expected_value) in [
        (32usize, 35u32),
        (2, 41),
        (4, 54),
        (6, 71),
        (8, 72),
        (10, 90),
        (12, 106),
        (14, 107),
    ] {
        let actual = verify_isolated_guest_dispatch(pairs)?;
        assert_eq!(
            actual, expected_value,
            "independent loader glyph rank/phase oracle at n={pairs}"
        );
        let _distinct = observed.insert(actual);
    }
    assert_eq!(observed.len(), 8, "all 8 rank branches must vary");
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "reference search of bounded code-data boundary"
)]
fn eighty_guest_noops_are_minimum_for_all_rank_separation_in_fixed_template() -> Result<(), String>
{
    // Independent reference: for a prefix 'j@0', N 'o', 'i@(N+1)',
    // data begins at N+29, and count glyph appears at N+41. If any legal
    // graphical glyph >= data start, that rank's XLAT2 writes payload.
    for nop_count in 0usize..=80usize {
        let payload_start = nop_count.saturating_add(29);
        let count_address = nop_count.saturating_add(41);
        let choices = (33u8..=126u8)
            .filter(|byte| {
                matches!(
                    decode_profile_instruction(
                        u32::from(*byte),
                        u32::try_from(count_address).unwrap_or(u32::MAX)
                    ),
                    Some(b'j' | b'i' | b'*' | b'p' | b'<' | b'/' | b'v' | b'o')
                )
            })
            .collect::<Vec<_>>();
        assert_eq!(
            choices.len(),
            8,
            "each loader position has exactly 8 glyphs"
        );
        let highest = choices.iter().copied().max().ok_or("missing alphabet")?;
        assert_eq!(
            usize::from(highest) < payload_start,
            nop_count == 80,
            "independent exhaustive 0..80 code/data separation bound at N={nop_count}"
        );
    }
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "host candidate corruption matrix"
)]
fn isolated_dispatch_rejects_forged_glyphs_and_source_identity() -> Result<(), String> {
    let original = program(12)?;
    let candidate = encode_bound_echo_macro(&original, current_profile())
        .map_err(|error| format!("source: {error:?}"))?;
    let source = embed_isolated_guest_dispatch(&original, current_profile(), &candidate)
        .map_err(|error| format!("source: {error:?}"))?;
    let mut corrupted_code = source.clone();
    *corrupted_code.get_mut(ISOLATED_JUMP_POSITION).ok_or("i")? = b'!';
    assert_eq!(
        admit_isolated_guest_dispatch(&original, current_profile(), &corrupted_code),
        Err(GuestPayloadProbeError::InvalidSource)
    );
    let mut corrupted_count = source.clone();
    let original_glyph = *source.get(ISOLATED_COUNT_ADDRESS).ok_or("count")?;
    let other = (33u8..=126u8)
        .find(|&glyph| {
            glyph != original_glyph
                && matches!(
                    decode_profile_instruction(u32::from(glyph), 121),
                    Some(b'j' | b'i' | b'*' | b'p' | b'<' | b'/' | b'v' | b'o')
                )
        })
        .ok_or("alternate valid count glyph")?;
    *corrupted_count
        .get_mut(ISOLATED_COUNT_ADDRESS)
        .ok_or("new count")? = other;
    assert!(
        admit_isolated_guest_dispatch(&original, current_profile(), &corrupted_count).is_err(),
        "loader admissibility is not enough for source-bound CEB2 acceptance"
    );
    for length in [0usize, 1, 81, 109, 121, 210] {
        let short = source.get(..length).ok_or("truncated source")?;
        assert_eq!(
            admit_isolated_guest_dispatch(&original, current_profile(), short),
            Err(GuestPayloadProbeError::InvalidSource)
        );
    }
    let mut too_long = source.clone();
    too_long.push(b'!');
    assert_eq!(
        admit_isolated_guest_dispatch(&original, current_profile(), &too_long),
        Err(GuestPayloadProbeError::InvalidSource)
    );
    let mut foreign = original;
    foreign.source_id = String::from("research/forged-ceb2.c");
    assert!(
        admit_isolated_guest_dispatch(&foreign, current_profile(), &source).is_err(),
        "equal pair count but different source must reject"
    );
    assert!(
        embed_isolated_guest_dispatch(&foreign, current_profile(), &candidate).is_err(),
        "publisher must never embed a foreign bound source"
    );
    Ok(())
}

#[test]
fn isolated_dispatch_v5_configuration_pins_non_equivalence_and_guest_work() {
    for line in [
        "schema = \"compact-guest-bytecode-pilot-v5\"",
        "payload_cells = 102",
        "reached_noops = 80",
        "reached_indirect_jump_position = 81",
        "source_pad_after_jump = 27",
        "payload_start = 109",
        "payload_count_glyph_address = 121",
        "source_cells = 211",
        "reached_guest_steps_for_jump = 82",
        "full_eight_rank_source_separation = true",
        "count_selected_jump_mutates_payload = false",
        "bytecode_interpreter_present = false",
        "semantic_echo_equivalence = false",
    ] {
        assert!(
            ISOLATED_DISPATCH_CONFIG
                .lines()
                .any(|actual| actual == line),
            "missing pinned research invariant: {line}"
        );
    }
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "bounded dynamic guest IO handler execution"
)]
#[expect(
    clippy::cognitive_complexity,
    reason = "three distinct data-selected guest handlers"
)]
#[expect(
    clippy::too_many_lines,
    reason = "three complete guest handler/I-O witnesses"
)]
fn isolated_bound_count_selects_real_guest_echo_or_halt_handler() -> Result<(), String> {
    for (pairs, expected_steps, expected_input_count, expected_code) in [
        (10usize, 85usize, 1usize, 91u32),
        (12, 83, 0, 107),
        (14, 83, 0, 108),
    ] {
        let original = program(pairs)?;
        let candidate = encode_bound_echo_macro(&original, current_profile())
            .map_err(|error| format!("bound {pairs}: {error:?}"))?;
        let source = embed_isolated_guest_handlers(&original, current_profile(), &candidate)
            .map_err(|error| format!("emit bound handlers {pairs}: {error:?}"))?;
        assert_eq!(source.len(), 211, "handlers do not change data footprint");
        let recovered = admit_isolated_guest_handlers(&original, current_profile(), &source)
            .map_err(|error| format!("admit bound handlers {pairs}: {error:?}"))?;
        assert_eq!(
            recovered, candidate,
            "all IO handlers retain CEB2 source digest"
        );
        let initial_glyph = u32::from(
            *source
                .get(ISOLATED_COUNT_ADDRESS)
                .ok_or("descriptor count cell")?,
        );
        assert_eq!(
            initial_glyph.saturating_add(1),
            expected_code,
            "guest source count cell selects actual handler entry"
        );
        for value in [0u8, 255, 128] {
            let mut machine = ProfileMachine::from_source(current_profile(), &source, vec![value])
                .map_err(|error| format!("profiled VM load {pairs}: {error:?}"))?;
            let outcome = machine
                .run(90)
                .map_err(|error| format!("real guest handler {pairs}: {error:?}"))?;
            assert!(
                matches!(outcome, RunOutcome::Terminated { .. }),
                "guest handler must actually halt without host IO callbacks"
            );
            let RunOutcome::Terminated {
                steps: reported_steps,
                ..
            } = outcome
            else {
                return Err(format!("guest handler budget exceeded at n={pairs}"));
            };
            assert_eq!(
                reported_steps, expected_steps,
                "exact matched source-data-directed guest work at n={pairs}"
            );
            assert_eq!(
                machine.input_consumed(),
                expected_input_count,
                "exact bounded guest input reads at n={pairs}"
            );
            let expected_output = if pairs == 10 { vec![value] } else { Vec::new() };
            assert_eq!(
                machine.output(),
                expected_output,
                "rank-five handler echoes one byte; ranks six/seven halt"
            );
            for pos in ISOLATED_PAYLOAD_START..ISOLATED_TOTAL_CELLS {
                let address = u32::try_from(pos).map_err(|error| error.to_string())?;
                assert_eq!(
                    machine
                        .memory_word(address)
                        .map_err(|error| format!("payload {pos}: {error:?}"))?,
                    u32::from(*source.get(pos).ok_or("payload byte")?),
                    "guest input/output/halt handler must not modify CEB2 at {pos}"
                );
            }
        }
    }
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "reject unsupported guest handler encodings"
)]
fn isolated_handler_host_rejects_unsupported_ranks_and_code_tampering() -> Result<(), String> {
    for pairs in [32usize, 2, 4, 6, 8] {
        let original = program(pairs)?;
        let candidate = encode_bound_echo_macro(&original, current_profile())
            .map_err(|error| format!("candidate {pairs}: {error:?}"))?;
        let code = embed_isolated_guest_handlers(&original, current_profile(), &candidate);
        let expected_rank = (pairs >> 1usize) & 7usize;
        assert_eq!(
            code,
            Err(GuestPayloadProbeError::UnsupportedGuestHandlerRank {
                rank: expected_rank,
            }),
            "unsupported count rank must reject without an executable source"
        );
    }
    let original = program(10)?;
    let candidate = encode_bound_echo_macro(&original, current_profile())
        .map_err(|error| format!("candidate: {error:?}"))?;
    let source = embed_isolated_guest_handlers(&original, current_profile(), &candidate)
        .map_err(|error| format!("emit: {error:?}"))?;
    for position in [91usize, 92, 93, 107, 108] {
        let mut changed = source.clone();
        *changed.get_mut(position).ok_or("guest handler")? = b'!';
        assert_eq!(
            admit_isolated_guest_handlers(&original, current_profile(), &changed),
            Err(GuestPayloadProbeError::InvalidSource),
            "every changed code-handler cell must reject"
        );
    }
    let mut other = original;
    other.source_id = String::from("research/foreign-handler.c");
    assert!(
        admit_isolated_guest_handlers(&other, current_profile(), &source).is_err(),
        "host must reject matching count with wrong source profile binding"
    );
    Ok(())
}

#[test]
fn isolated_handlers_pilot_pins_guest_io_non_equivalence() {
    for declaration in [
        "schema = \"compact-guest-bytecode-pilot-v5-handlers\"",
        "accepted_count_glyph_ranks = [5, 6, 7]",
        "rank_5_handler = \"input@91-output@92-halt@93\"",
        "rank_5_guest_steps = 85",
        "rank_5_input_bytes = 1",
        "rank_5_output_bytes = 1",
        "rank_6_handler = \"halt@107\"",
        "rank_7_handler = \"halt@108\"",
        "source_payload_remains_unmodified = true",
        "count_ordinal_guest_decoding = false",
        "full_bytecode_interpreter_present = false",
        "semantic_equivalence_to_n_pair_echo = false",
    ] {
        assert!(
            ISOLATED_HANDLERS_CONFIG
                .lines()
                .any(|line| line == declaration),
            "missing pinned handler assumption: {declaration}"
        );
    }
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "actual external Malbolge guest handlers"
)]
fn source_selected_guest_handlers_run_through_real_general_malbolge_cli() -> Result<(), String> {
    for (pairs, expected_output, exact_steps) in
        [(10usize, vec![255u8], 85usize), (12, Vec::new(), 83)]
    {
        let owned = OwnedArtifactFixture::new(pairs.saturating_add(20_000))?;
        let original = program(pairs)?;
        let candidate = encode_bound_echo_macro(&original, current_profile())
            .map_err(|error| format!("bound {pairs}: {error:?}"))?;
        let source = embed_isolated_guest_handlers(&original, current_profile(), &candidate)
            .map_err(|error| format!("source: {error:?}"))?;
        assert_eq!(
            admit_isolated_guest_handlers(&original, current_profile(), &source),
            Ok(candidate),
            "public CLI only receives host-admitted source"
        );
        let capsule = malbolge::build_capsule(current_profile(), &source)
            .map_err(|error| format!("capsule: {error}"))?;
        let path = owned.path("isolated-handler.malbolge");
        fs::write(&path, capsule).map_err(|error| format!("write: {error}"))?;
        let mut child = Command::new(env!("CARGO_BIN_EXE_malbolge"))
            .env_remove("MALBOLGE_PROFILE_ADAPTIVE_WIDTH")
            .env_remove("MALBOLGE_PROFILE_RESIDENT_WORKER")
            .arg(&path)
            .arg("--input-stdin")
            .arg("--report-steps")
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .spawn()
            .map_err(|error| format!("actual runner start {pairs}: {error}"))?;
        let mut stdin = child.stdin.take().ok_or("missing child stdin")?;
        stdin
            .write_all(&[255u8])
            .map_err(|error| format!("input: {error}"))?;
        drop(stdin);
        let output = child
            .wait_with_output()
            .map_err(|error| format!("actual runner result: {error}"))?;
        assert!(
            output.status.success(),
            "general CLI failed for n={pairs}: {output:?}"
        );
        assert_eq!(
            output.stdout, expected_output,
            "actual guest I/O differs from independent count-route oracle"
        );
        assert_eq!(
            output.stderr,
            format!("malbolge-steps-v1:{exact_steps}\n").as_bytes(),
            "the external runner must receipt exact guest steps"
        );
    }
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "real guest/direct 1-op semantic parity"
)]
#[expect(
    clippy::too_many_lines,
    reason = "full guest trace, source-bound data and direct oracle"
)]
#[expect(
    clippy::cognitive_complexity,
    reason = "disjoint native opcode and source checks"
)]
fn one_guest_bytecode_opcode_matches_independent_complete_one_pair_echo() -> Result<(), String> {
    let original = program(1)?;
    let candidate = encode_bound_echo_macro(&original, current_profile())
        .map_err(|error| format!("CEB2: {error:?}"))?;
    let source = embed_single_echo_opcode(&original, current_profile(), &candidate)
        .map_err(|error| format!("emit guest opcode: {error:?}"))?;
    assert_eq!(source.len(), SINGLE_SOURCE_CELLS, "exact emitted size");
    assert_eq!(SINGLE_SOURCE_CELLS, 224);
    assert_eq!(SINGLE_CEB2_START, 122);
    assert_eq!(SINGLE_OPCODE_ADDRESS, 121);
    assert_eq!(SINGLE_ECHO_OPCODE_RANK, 5);
    assert_eq!(
        source.get(121),
        Some(&90),
        "literal loader graphical opcode"
    );
    assert_eq!(
        admit_single_echo_opcode(&original, current_profile(), &source),
        Ok(candidate),
        "recover exact CEB2 from 102 re-ranked data cells"
    );
    for (index, &glyph) in source.iter().enumerate() {
        let position = u32::try_from(index).map_err(|error| error.to_string())?;
        assert!(
            matches!(
                decode_profile_instruction(u32::from(glyph), position),
                Some(b'j' | b'i' | b'*' | b'p' | b'<' | b'/' | b'v' | b'o')
            ),
            "all code/opcode/data positions must satisfy canonical loader {index}"
        );
    }
    let direct = strategy::bridge::encode_successful_byte_echo(&original, current_profile())
        .map_err(|error| format!("independent direct layout: {error:?}"))?;
    assert_eq!(direct.source().len(), 3, "one pair direct code is 3 cells");
    for byte in [0u8, 1, 127, 128, 255] {
        let mut guest = ProfileMachine::from_source(current_profile(), &source, vec![byte])
            .map_err(|error| format!("guest loader: {error:?}"))?;
        let mut indirect = None;
        let outcome = guest
            .run_traced(SINGLE_ECHO_GUEST_STEPS, &mut |event| {
                if event.before.registers.code_pointer == 81 {
                    indirect = Some(*event);
                }
            })
            .map_err(|error| format!("guest VM: {error:?}"))?;
        assert!(
            matches!(outcome, RunOutcome::Terminated { steps: 85, .. }),
            "full guest opcode must terminate, not exhaust its budget"
        );
        let event = indirect.ok_or("missing reached bytecode dispatch")?;
        assert_eq!(event.decoded, Some(b'i'), "real VM indirect opcode");
        assert_eq!(
            event.before.registers.data_pointer, 121,
            "physical opcode operand at D=121"
        );
        assert_eq!(
            event
                .memory_reads
                .data
                .map(|read| (read.address, read.value)),
            Some((121, 90)),
            "read actual embedded opcode from guest memory"
        );
        assert_eq!(
            event.memory_delta.encryption.map(|write| write.address),
            Some(90),
            "native jump mutates code, not bytecode"
        );
        assert_eq!(guest.output(), &[byte], "guest byte-for-byte echo oracle");
        assert_eq!(guest.input_consumed(), 1, "exact one input byte");
        let mut baseline =
            ProfileMachine::from_source(current_profile(), direct.source(), vec![byte])
                .map_err(|error| format!("direct source loader: {error:?}"))?;
        assert!(
            matches!(baseline.run(3), Ok(RunOutcome::Terminated { steps: 3, .. })),
            "direct one-pair baseline must perform exactly three guest steps"
        );
        assert_eq!(
            guest.output(),
            baseline.output(),
            "equivalent one-byte trace for actual direct and bytecode guest"
        );
        assert_eq!(
            guest.input_consumed(),
            baseline.input_consumed(),
            "equivalent successful input consumption for guest and direct"
        );
        let mut restored_image = source.clone();
        for index in SINGLE_CEB2_START..SINGLE_SOURCE_CELLS {
            let address = u32::try_from(index).map_err(|error| error.to_string())?;
            let actual_word = guest
                .memory_word(address)
                .map_err(|error| format!("guest data {index}: {error:?}"))?;
            assert_eq!(
                actual_word,
                u32::from(*source.get(index).ok_or("source CEB2 glyph")?),
                "all 102 CEB2 glyphs remain unmodified by guest opcode {index}"
            );
            *restored_image.get_mut(index).ok_or("restored CEB2")? =
                u8::try_from(actual_word).map_err(|error| error.to_string())?;
        }
        assert_eq!(
            admit_single_echo_opcode(&original, current_profile(), &restored_image),
            Ok(candidate),
            "source-bound CEB2 remains intact in real guest VM"
        );
    }
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "source-bound bytecode rejection matrix"
)]
#[expect(
    clippy::too_many_lines,
    reason = "all source/data tampering and unsupported counts"
)]
#[expect(
    clippy::cognitive_complexity,
    reason = "all malformed count/code/data cases"
)]
fn one_guest_opcode_rejects_nontrivial_count_and_changed_code_or_payload() -> Result<(), String> {
    for pairs in [2usize, 7, 10, 64] {
        let original = program(pairs)?;
        let candidate = encode_bound_echo_macro(&original, current_profile())
            .map_err(|error| format!("encode: {error:?}"))?;
        assert_eq!(
            embed_single_echo_opcode(&original, current_profile(), &candidate),
            Err(SingleOpcodeError::UnsupportedEchoCount),
            "all non-single echo programs must be rejected without output"
        );
    }
    let original = program(1)?;
    let candidate = encode_bound_echo_macro(&original, current_profile())
        .map_err(|error| format!("encode: {error:?}"))?;
    let source = embed_single_echo_opcode(&original, current_profile(), &candidate)
        .map_err(|error| format!("emit: {error:?}"))?;
    for position in [0usize, 1, 80, 81, 91, 92, 93, 120, 121] {
        let mut wrong = source.clone();
        *wrong.get_mut(position).ok_or("code position")? = b'!';
        assert_eq!(
            admit_single_echo_opcode(&original, current_profile(), &wrong),
            Err(SingleOpcodeError::InvalidSource),
            "changed exact opcode/native code must reject at {position}"
        );
    }
    for position in [122usize, 123, 224 - 1] {
        let mut wrong = source.clone();
        let original_glyph = *wrong.get(position).ok_or("data position")?;
        let replacement = (33u8..=126u8)
            .find(|&glyph| {
                glyph != original_glyph
                    && matches!(
                        decode_profile_instruction(
                            u32::from(glyph),
                            u32::try_from(position).unwrap_or(u32::MAX)
                        ),
                        Some(b'j' | b'i' | b'*' | b'p' | b'<' | b'/' | b'v' | b'o')
                    )
            })
            .ok_or("second loader-valid data glyph")?;
        *wrong.get_mut(position).ok_or("changed data cell")? = replacement;
        assert!(
            admit_single_echo_opcode(&original, current_profile(), &wrong).is_err(),
            "even loader-admissible mutated descriptor must fail binding"
        );
    }
    for shortened in [0usize, 1, 91, 121, 122, 223] {
        assert_eq!(
            admit_single_echo_opcode(
                &original,
                current_profile(),
                source.get(..shortened).ok_or("source prefix")?
            ),
            Err(SingleOpcodeError::InvalidSource),
            "truncated source rejects"
        );
    }
    let mut extended = source.clone();
    extended.push(b'!');
    assert_eq!(
        admit_single_echo_opcode(&original, current_profile(), &extended),
        Err(SingleOpcodeError::InvalidSource),
        "excess source cells reject"
    );
    let mut foreign = original;
    foreign.source_id = String::from("research/forged-echo-one.c");
    assert!(
        admit_single_echo_opcode(&foreign, current_profile(), &source).is_err(),
        "source identity is included in host SHA-256 provenance check"
    );
    Ok(())
}

#[test]
fn single_guest_echo_opcode_config_pins_complete_bounded_semantics() {
    for declaration in [
        "schema = \"compact-guest-bytecode-pilot-v6\"",
        "source_cells = 224",
        "code_prefix_and_opcode_cells = 122",
        "opcode_address = 121",
        "opcode_rank = 5",
        "opcode_graphical_word = 90",
        "opcode_name = \"ECHO_ONE\"",
        "protected_descriptor_start = 122",
        "protected_descriptor_cells = 102",
        "required_original_echo_pairs = 1",
        "guest_steps = 85",
        "full_single_operation_semantic_parity = true",
        "bytecode_count_loop_present = false",
        "guest_source_authentication_present = false",
        "multi_operation_interpreter_present = false",
    ] {
        assert!(
            SINGLE_OPCODE_CONFIG.lines().any(|line| line == declaration),
            "missing pinned one-opcode research constraint: {declaration}"
        );
    }
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "real CLI direct-vs-bytecode parity"
)]
#[expect(
    clippy::too_many_lines,
    reason = "both real capsule publishers and stdin runners"
)]
fn one_opcode_is_equivalent_to_direct_echo_through_general_malbolge_cli() -> Result<(), String> {
    let fixture = OwnedArtifactFixture::new(31_001)?;
    let original = program(1)?;
    let bound = encode_bound_echo_macro(&original, current_profile())
        .map_err(|error| format!("bound original: {error:?}"))?;
    let guest_source = embed_single_echo_opcode(&original, current_profile(), &bound)
        .map_err(|error| format!("guest opcode source: {error:?}"))?;
    assert_eq!(
        admit_single_echo_opcode(&original, current_profile(), &guest_source),
        Ok(bound),
        "only source-bound admitted program is published"
    );
    let direct = strategy::bridge::encode_successful_byte_echo(&original, current_profile())
        .map_err(|error| format!("direct compiler: {error:?}"))?;
    for (basename, payload) in [
        ("direct.malbolge", direct.source()),
        ("guest-opcode.malbolge", guest_source.as_slice()),
    ] {
        let capsule = malbolge::build_capsule(current_profile(), payload)
            .map_err(|error| format!("capsule {basename}: {error:?}"))?;
        fs::write(fixture.path(basename), capsule)
            .map_err(|error| format!("write capsule {basename}: {error}"))?;
    }
    for byte in [0u8, 128, 255] {
        let mut outputs = Vec::new();
        for (basename, expected_steps) in
            [("direct.malbolge", 3usize), ("guest-opcode.malbolge", 85)]
        {
            let mut child = Command::new(env!("CARGO_BIN_EXE_malbolge"))
                .env_remove("MALBOLGE_PROFILE_ADAPTIVE_WIDTH")
                .env_remove("MALBOLGE_PROFILE_RESIDENT_WORKER")
                .arg(fixture.path(basename))
                .arg("--input-stdin")
                .arg("--report-steps")
                .stdin(Stdio::piped())
                .stdout(Stdio::piped())
                .stderr(Stdio::piped())
                .spawn()
                .map_err(|error| format!("start {basename}: {error}"))?;
            let mut stdin = child.stdin.take().ok_or("missing native runner stdin")?;
            stdin
                .write_all(&[byte])
                .map_err(|error| format!("send {basename} input: {error}"))?;
            drop(stdin);
            let output = child
                .wait_with_output()
                .map_err(|error| format!("wait {basename}: {error}"))?;
            assert!(
                output.status.success(),
                "real CLI failed on {basename}, byte {byte}: {output:?}"
            );
            assert_eq!(
                output.stdout,
                [byte],
                "guest/direct external source must echo the exact input byte"
            );
            assert_eq!(
                output.stderr,
                format!("malbolge-steps-v1:{expected_steps}\n").as_bytes(),
                "real runner step receipt must match independent exact work"
            );
            outputs.push(output.stdout);
        }
        assert_eq!(
            outputs.first(),
            outputs.get(1),
            "two independent native CLI processes must produce same stdout"
        );
    }
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "loader-valid alternative opcode tampering"
)]
fn changed_loader_valid_bytecode_opcode_rejects_without_fallback() -> Result<(), String> {
    let original = program(1)?;
    let candidate = encode_bound_echo_macro(&original, current_profile())
        .map_err(|error| format!("bound: {error:?}"))?;
    let source = embed_single_echo_opcode(&original, current_profile(), &candidate)
        .map_err(|error| format!("opcode source: {error:?}"))?;
    let expected = *source
        .get(SINGLE_OPCODE_ADDRESS)
        .ok_or("opcode source glyph")?;
    for byte in (33u8..=126u8).filter(|&glyph| {
        glyph != expected
            && matches!(
                decode_profile_instruction(u32::from(glyph), 121),
                Some(b'j' | b'i' | b'*' | b'p' | b'<' | b'/' | b'v' | b'o')
            )
    }) {
        let mut different = source.clone();
        *different
            .get_mut(SINGLE_OPCODE_ADDRESS)
            .ok_or("opcode cell")? = byte;
        assert_eq!(
            admit_single_echo_opcode(&original, current_profile(), &different),
            Err(SingleOpcodeError::InvalidSource),
            "alternative loader-valid bytecode opcode {byte} must reject"
        );
    }
    Ok(())
}

#[test]
#[expect(clippy::panic_in_result_fn, reason = "state-validated guest parity")]
#[expect(clippy::too_many_lines, reason = "bounded VM state-restoration checks")]
#[expect(
    clippy::cognitive_complexity,
    reason = "guest/direct VM boundary matrix"
)]
fn independent_vm_restores_cover_byte_boundary_matrix_for_single_opcode() -> Result<(), String> {
    const BOUNDARY_VALUES: [u8; 21] = [
        0, 1, 2, 15, 16, 31, 32, 63, 64, 95, 96, 127, 128, 159, 160, 191, 192, 223, 224, 254, 255,
    ];
    let original = program(1)?;
    let candidate = encode_bound_echo_macro(&original, current_profile())
        .map_err(|error| format!("CEB2: {error:?}"))?;
    let guest_source = embed_single_echo_opcode(&original, current_profile(), &candidate)
        .map_err(|error| format!("isolated opcode: {error:?}"))?;
    assert_eq!(
        admit_single_echo_opcode(&original, current_profile(), &guest_source),
        Ok(candidate),
        "only admitted bound source can enter VM"
    );
    let direct = strategy::bridge::encode_successful_byte_echo(&original, current_profile())
        .map_err(|error| format!("separately admitted direct layout: {error:?}"))?;
    // Load each large 15-trit memory only once. Each independent profile VM
    // case reconstructs/validates an exact initial state, without relying on
    // the prior self-encrypted code, consumed inputs or changed registers.
    let guest_initial = ProfileMachine::from_source(current_profile(), &guest_source, Vec::new())
        .map_err(|error| format!("guest memory loader: {error:?}"))?
        .snapshot_state();
    let direct_initial =
        ProfileMachine::from_source(current_profile(), direct.source(), Vec::new())
            .map_err(|error| format!("direct memory loader: {error:?}"))?
            .snapshot_state();
    let mut total_cases = 0usize;
    for value in BOUNDARY_VALUES {
        let mut guest = ProfileMachine::from_state(
            current_profile(),
            guest_initial.memory().to_vec(),
            vec![value],
            malbolge::ProfileRegisters::default(),
        )
        .map_err(|error| format!("guest {value} full-state admission: {error:?}"))?;
        let mut direct_vm = ProfileMachine::from_state(
            current_profile(),
            direct_initial.memory().to_vec(),
            vec![value],
            malbolge::ProfileRegisters::default(),
        )
        .map_err(|error| format!("direct {value} full-state admission: {error:?}"))?;
        assert!(
            matches!(guest.run(85), Ok(RunOutcome::Terminated { steps: 85, .. })),
            "one-byte guest {value} must reach one-opcode halt"
        );
        assert!(
            matches!(
                direct_vm.run(3),
                Ok(RunOutcome::Terminated { steps: 3, .. })
            ),
            "direct byte {value} must reach 3-step halt"
        );
        assert_eq!(
            guest.output(),
            &[value],
            "guest ECHO_ONE must echo each independently reset boundary byte"
        );
        assert_eq!(
            guest.output(),
            direct_vm.output(),
            "the two independent VM code images must agree at byte {value}"
        );
        assert_eq!(
            guest.input_consumed(),
            direct_vm.input_consumed(),
            "the two images must consume exactly one byte {value}"
        );
        assert_eq!(guest.input_consumed(), 1, "exactly one operand per opcode");
        for address in [122u32, 123, 160, 223] {
            assert_eq!(
                guest
                    .memory_word(address)
                    .map_err(|error| format!("payload sample {address}: {error:?}"))?,
                u32::from(
                    *guest_source
                        .get(usize::try_from(address).map_err(|error| error.to_string())?)
                        .ok_or("payload sample")?
                ),
                "source-bound CEB2 memory must remain protected for {value}"
            );
        }
        total_cases = total_cases.saturating_add(1);
    }
    assert_eq!(
        total_cases,
        BOUNDARY_VALUES.len(),
        "all independently state-reset byte-boundary cases must run"
    );
    Ok(())
}

#[test]
#[expect(clippy::panic_in_result_fn, reason = "EOF and excess-input parity")]
#[expect(
    clippy::cognitive_complexity,
    reason = "EOF/trailing VM parity oracles"
)]
fn guest_echo_one_opcode_agrees_with_direct_on_eof_and_trailing_input() -> Result<(), String> {
    let original = program(1)?;
    let candidate = encode_bound_echo_macro(&original, current_profile())
        .map_err(|error| format!("original CEB2: {error:?}"))?;
    let guest_source = embed_single_echo_opcode(&original, current_profile(), &candidate)
        .map_err(|error| format!("encoded one-opcode source: {error:?}"))?;
    let direct_source = strategy::bridge::encode_successful_byte_echo(&original, current_profile())
        .map_err(|error| format!("independent direct one-pair layout: {error:?}"))?;
    for input in [Vec::new(), vec![16u8, 32, 255]] {
        let mut guest =
            ProfileMachine::from_source(current_profile(), &guest_source, input.clone())
                .map_err(|error| format!("guest load: {error:?}"))?;
        let mut direct =
            ProfileMachine::from_source(current_profile(), direct_source.source(), input.clone())
                .map_err(|error| format!("direct load: {error:?}"))?;
        assert!(
            matches!(guest.run(85), Ok(RunOutcome::Terminated { steps: 85, .. })),
            "guest ECHO_ONE terminates even with empty or excess input"
        );
        assert!(
            matches!(direct.run(3), Ok(RunOutcome::Terminated { steps: 3, .. })),
            "independent direct echo terminates in three steps"
        );
        assert_eq!(
            guest.output(),
            direct.output(),
            "identical EOF or trailing-input stdout semantics"
        );
        assert_eq!(
            guest.input_consumed(),
            direct.input_consumed(),
            "identical EOF or trailing-input consumption"
        );
        assert_eq!(
            guest.input_consumed(),
            usize::from(!input.is_empty()),
            "EOF consumes nothing; excess input consumes one byte"
        );
        if let Some(first) = input.first() {
            assert_eq!(
                guest.output(),
                &[*first],
                "trailing input is never echoed by a one-opcode program"
            );
        }
    }
    Ok(())
}

#[test]
fn two_graphical_guest_operations_config_pins_bounded_semantics() {
    for declaration in [
        "schema = \"compact-guest-bytecode-pilot-v7\"",
        "operation_count = 2",
        "required_echo_pairs = 2",
        "source_cells = 227",
        "first_opcode_address = 121",
        "first_opcode_word = 90",
        "second_opcode_address = 124",
        "second_opcode_word = 104",
        "source_bound_descriptor_start = 125",
        "source_bound_descriptor_cells = 102",
        "reached_guest_steps = 88",
        "guest_opcode_read_count = 2",
        "guest_repetition_loop_present = false",
        "guest_sha256_authentication_present = false",
        "general_bytecode_interpreter_present = false",
    ] {
        assert!(
            TWO_OPCODE_CONFIG.lines().any(|line| line == declaration),
            "missing v7 research contract: {declaration}"
        );
    }
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "two semantic guest opcodes with independent direct oracle"
)]
#[expect(
    clippy::too_many_lines,
    reason = "all reached branches and source-bound payload traces"
)]
#[expect(
    clippy::cognitive_complexity,
    reason = "two real indirect instruction trace receipts"
)]
fn two_real_graphical_guest_opcodes_match_two_pair_direct_echo() -> Result<(), String> {
    let original = program(2)?;
    let candidate = encode_bound_echo_macro(&original, current_profile())
        .map_err(|error| format!("original 2-pair digest: {error:?}"))?;
    let guest_source = embed_two_echo_opcodes(&original, current_profile(), &candidate)
        .map_err(|error| format!("emit two-op guest source: {error:?}"))?;
    assert_eq!(guest_source.len(), TWO_SOURCE_CELLS, "exact 227 positions");
    assert_eq!(TWO_SOURCE_CELLS, 227);
    assert_eq!(TWO_CEB2_START, 125);
    assert_eq!(FIRST_OPCODE_ADDRESS, 121);
    assert_eq!(SECOND_OPCODE_ADDRESS, 124);
    assert_eq!(guest_source.get(121), Some(&90), "first physical opcode");
    assert_eq!(guest_source.get(124), Some(&104), "second physical opcode");
    assert_eq!(
        admit_two_echo_opcodes(&original, current_profile(), &guest_source),
        Ok(candidate),
        "host must reconstruct exact CEB2 from new-phase glyphs"
    );
    for (address, &glyph) in guest_source.iter().enumerate() {
        assert!(
            matches!(
                decode_profile_instruction(
                    u32::from(glyph),
                    u32::try_from(address).map_err(|error| error.to_string())?
                ),
                Some(b'j' | b'i' | b'*' | b'p' | b'<' | b'/' | b'v' | b'o')
            ),
            "entire graphical source must pass normative loader at {address}"
        );
    }
    let direct = strategy::bridge::encode_successful_byte_echo(&original, current_profile())
        .map_err(|error| format!("independent 2-pair direct layout: {error:?}"))?;
    assert_eq!(direct.source().len(), 5, "direct code only five cells");
    for input in [vec![0u8, 255], vec![255, 0], vec![128, 129]] {
        let mut guest =
            ProfileMachine::from_source(current_profile(), &guest_source, input.clone())
                .map_err(|error| format!("loader for two opcode VM: {error:?}"))?;
        let mut indirect = Vec::new();
        let outcome = guest
            .run_traced(TWO_GUEST_STEPS, &mut |trace| {
                if trace.before.registers.code_pointer == 81
                    || trace.before.registers.code_pointer == 93
                {
                    indirect.push(*trace);
                }
            })
            .map_err(|error| format!("two-op guest VM: {error:?}"))?;
        assert!(
            matches!(outcome, RunOutcome::Terminated { steps: 88, .. }),
            "two guest opcodes must halt after exactly 88 native steps"
        );
        assert_eq!(indirect.len(), 2, "two actual data-derived reached jumps");
        for (index, (code, data, glyph)) in [(81u32, 121u32, 90u32), (93, 124, 104)]
            .into_iter()
            .enumerate()
        {
            let step = indirect.get(index).ok_or("missing real guest jump trace")?;
            assert_eq!(step.decoded, Some(b'i'), "guest must execute native i");
            assert_eq!(
                step.before.registers.code_pointer, code,
                "guest jumps at two separate code positions"
            );
            assert_eq!(
                step.before.registers.data_pointer, data,
                "second D advanced by first native input/output"
            );
            assert_eq!(
                step.memory_reads
                    .data
                    .map(|read| (read.address, read.value)),
                Some((data, glyph)),
                "physical source opcode read, not host-injected"
            );
            assert_eq!(
                step.memory_delta.encryption.map(|write| write.address),
                Some(glyph),
                "native self-encryption stays in code-only region"
            );
            assert_eq!(
                step.after.registers.code_pointer,
                glyph.saturating_add(1),
                "real C pointer advances after indirect target"
            );
        }
        assert_eq!(guest.output(), input, "two bytes echoed in original order");
        assert_eq!(
            guest.input_consumed(),
            2,
            "exactly two real guest input reads"
        );
        let mut direct_vm =
            ProfileMachine::from_source(current_profile(), direct.source(), input.clone())
                .map_err(|error| format!("independent direct loader: {error:?}"))?;
        assert!(
            matches!(
                direct_vm.run(5),
                Ok(RunOutcome::Terminated { steps: 5, .. })
            ),
            "independent direct code executes exactly five instructions"
        );
        assert_eq!(
            guest.output(),
            direct_vm.output(),
            "complete equivalent two-byte guest/direct output trace"
        );
        assert_eq!(
            guest.input_consumed(),
            direct_vm.input_consumed(),
            "complete equivalent input consumption trace"
        );
        for position in TWO_CEB2_START..TWO_SOURCE_CELLS {
            let address = u32::try_from(position).map_err(|error| error.to_string())?;
            assert_eq!(
                guest
                    .memory_word(address)
                    .map_err(|error| format!("guest memory {position}: {error:?}"))?,
                u32::from(*guest_source.get(position).ok_or("bound source glyph")?),
                "both real guest operations must preserve all 102 CEB2 words"
            );
        }
    }
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "bounded two-opcode negative matrix"
)]
#[expect(
    clippy::cognitive_complexity,
    reason = "forge source/count, phase-valid alternatives"
)]
#[expect(
    clippy::too_many_lines,
    reason = "complete input/code/payload forgery matrix"
)]
fn two_graphical_opcodes_reject_bad_counts_and_forged_source() -> Result<(), String> {
    for pairs in [1usize, 3, 7, 10, 64] {
        let original = program(pairs)?;
        let candidate = encode_bound_echo_macro(&original, current_profile())
            .map_err(|error| format!("candidate n={pairs}: {error:?}"))?;
        assert_eq!(
            embed_two_echo_opcodes(&original, current_profile(), &candidate),
            Err(TwoOpcodeError::UnsupportedEchoCount),
            "reject every tested other echo count n={pairs}"
        );
    }
    let original = program(2)?;
    let candidate = encode_bound_echo_macro(&original, current_profile())
        .map_err(|error| format!("candidate: {error:?}"))?;
    let source = embed_two_echo_opcodes(&original, current_profile(), &candidate)
        .map_err(|error| format!("two-op source: {error:?}"))?;
    for index in [0usize, 81, 91, 92, 93, 105, 106, 107, 121, 124] {
        let mut corrupted = source.clone();
        *corrupted.get_mut(index).ok_or("code or opcode cell")? = b'!';
        assert_eq!(
            admit_two_echo_opcodes(&original, current_profile(), &corrupted),
            Err(TwoOpcodeError::InvalidSource),
            "changed code or opcode fails before guest reaches index={index}"
        );
    }
    for index in [121usize, 124] {
        let original_word = *source.get(index).ok_or("loaded graphical opcode")?;
        for replacement in (33u8..=126u8).filter(|&glyph| {
            glyph != original_word
                && matches!(
                    decode_profile_instruction(
                        u32::from(glyph),
                        u32::try_from(index).unwrap_or(u32::MAX)
                    ),
                    Some(b'j' | b'i' | b'*' | b'p' | b'<' | b'/' | b'v' | b'o')
                )
        }) {
            let mut forged = source.clone();
            *forged.get_mut(index).ok_or("forged opcode")? = replacement;
            assert_eq!(
                admit_two_echo_opcodes(&original, current_profile(), &forged),
                Err(TwoOpcodeError::InvalidSource),
                "other loader-valid graphical opcode must not pass host admission"
            );
        }
    }
    for index in [TWO_CEB2_START, TWO_CEB2_START + 1, TWO_SOURCE_CELLS - 1] {
        let mut forged = source.clone();
        let original_glyph = *forged.get(index).ok_or("payload cell")?;
        let replacement = (33u8..=126u8)
            .find(|&glyph| {
                glyph != original_glyph
                    && matches!(
                        decode_profile_instruction(
                            u32::from(glyph),
                            u32::try_from(index).unwrap_or(u32::MAX)
                        ),
                        Some(b'j' | b'i' | b'*' | b'p' | b'<' | b'/' | b'v' | b'o')
                    )
            })
            .ok_or("alternate loader-valid CEB2 source glyph")?;
        *forged.get_mut(index).ok_or("mutated descriptor source")? = replacement;
        assert!(
            admit_two_echo_opcodes(&original, current_profile(), &forged).is_err(),
            "changed phase-valid CEB2 payload must not pass original digest"
        );
    }
    for cut in [0usize, 1, 121, 124, 125, 226] {
        assert_eq!(
            admit_two_echo_opcodes(
                &original,
                current_profile(),
                source.get(..cut).ok_or("source truncated prefix")?
            ),
            Err(TwoOpcodeError::InvalidSource),
            "reject truncated shape"
        );
    }
    let mut oversized = source.clone();
    oversized.push(b'!');
    assert_eq!(
        admit_two_echo_opcodes(&original, current_profile(), &oversized),
        Err(TwoOpcodeError::InvalidSource),
        "reject excess byte"
    );
    let mut foreign = original;
    foreign.source_id = String::from("research/forged-two-opcodes.c");
    assert!(
        admit_two_echo_opcodes(&foreign, current_profile(), &source).is_err(),
        "equal-count but foreign canonical source must fail digest admission"
    );
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "real CLI two-op source/direct parity"
)]
#[expect(
    clippy::too_many_lines,
    reason = "two independently published verified guest sources"
)]
fn two_sequential_guest_opcodes_match_direct_in_general_malbolge_cli() -> Result<(), String> {
    let fixture = OwnedArtifactFixture::new(32_002)?;
    let original = program(2)?;
    let candidate = encode_bound_echo_macro(&original, current_profile())
        .map_err(|error| format!("bound two-pair source: {error:?}"))?;
    let guest = embed_two_echo_opcodes(&original, current_profile(), &candidate)
        .map_err(|error| format!("two-opcode source: {error:?}"))?;
    assert_eq!(
        admit_two_echo_opcodes(&original, current_profile(), &guest),
        Ok(candidate),
        "external process must receive exact admitted source"
    );
    let direct = strategy::bridge::encode_successful_byte_echo(&original, current_profile())
        .map_err(|error| format!("independent direct compiler: {error:?}"))?;
    for (basename, bytes) in [
        ("two-direct.malbolge", direct.source()),
        ("two-guest.malbolge", guest.as_slice()),
    ] {
        let capsule = malbolge::build_capsule(current_profile(), bytes)
            .map_err(|error| format!("capsule {basename}: {error:?}"))?;
        fs::write(fixture.path(basename), capsule)
            .map_err(|error| format!("publish {basename}: {error}"))?;
    }
    for input in [vec![0u8, 255], vec![255, 0]] {
        let mut outputs = Vec::new();
        for (basename, expected_steps) in
            [("two-direct.malbolge", 5usize), ("two-guest.malbolge", 88)]
        {
            let mut child = Command::new(env!("CARGO_BIN_EXE_malbolge"))
                .env_remove("MALBOLGE_PROFILE_ADAPTIVE_WIDTH")
                .env_remove("MALBOLGE_PROFILE_RESIDENT_WORKER")
                .arg(fixture.path(basename))
                .arg("--input-stdin")
                .arg("--report-steps")
                .stdin(Stdio::piped())
                .stdout(Stdio::piped())
                .stderr(Stdio::piped())
                .spawn()
                .map_err(|error| format!("spawn {basename}: {error}"))?;
            let mut stdin = child.stdin.take().ok_or("missing runner stdin")?;
            stdin
                .write_all(&input)
                .map_err(|error| format!("write {basename} stdin: {error}"))?;
            drop(stdin);
            let output = child
                .wait_with_output()
                .map_err(|error| format!("wait {basename}: {error}"))?;
            assert!(
                output.status.success(),
                "two-byte guest/direct external runner failed: {output:?}"
            );
            assert_eq!(
                output.stdout, input,
                "real general CLI must echo both submitted bytes in order"
            );
            assert_eq!(
                output.stderr,
                format!("malbolge-steps-v1:{expected_steps}\n").as_bytes(),
                "real CLI must report exact guest/native instruction count"
            );
            outputs.push(output.stdout);
        }
        assert_eq!(
            outputs.first(),
            outputs.get(1),
            "independent guest/direct CLI processes must agree byte for byte"
        );
    }
    Ok(())
}

#[test]
#[expect(clippy::panic_in_result_fn, reason = "empty/excess input guest parity")]
#[expect(
    clippy::too_many_lines,
    reason = "bounded multi-stream full-state VM comparisons"
)]
#[expect(
    clippy::cognitive_complexity,
    reason = "two independent profile VM semantics"
)]
fn two_guest_opcodes_match_direct_on_eof_short_and_trailing_input() -> Result<(), String> {
    let original = program(2)?;
    let candidate = encode_bound_echo_macro(&original, current_profile())
        .map_err(|error| format!("bound two-pair IR: {error:?}"))?;
    let source = embed_two_echo_opcodes(&original, current_profile(), &candidate)
        .map_err(|error| format!("two-op guest emitter: {error:?}"))?;
    assert_eq!(
        admit_two_echo_opcodes(&original, current_profile(), &source),
        Ok(candidate),
        "source must be bound before VM replay"
    );
    let direct = strategy::bridge::encode_successful_byte_echo(&original, current_profile())
        .map_err(|error| format!("direct two-byte publisher: {error:?}"))?;
    // Copy validated full-width initial state for each different input stream
    // rather than mistakenly executing already self-encrypted guest code.
    let guest_initial = ProfileMachine::from_source(current_profile(), &source, Vec::new())
        .map_err(|error| format!("original guest loader: {error:?}"))?
        .snapshot_state();
    let direct_initial =
        ProfileMachine::from_source(current_profile(), direct.source(), Vec::new())
            .map_err(|error| format!("original direct loader: {error:?}"))?
            .snapshot_state();
    for input in [
        vec![],
        vec![0u8],
        vec![255],
        vec![0, 255],
        vec![7, 129, 255],
        vec![0, 1, 2, 3],
    ] {
        let mut guest = ProfileMachine::from_state(
            current_profile(),
            guest_initial.memory().to_vec(),
            input.clone(),
            malbolge::ProfileRegisters::default(),
        )
        .map_err(|error| format!("guest validated checkpoint: {error:?}"))?;
        let mut direct_vm = ProfileMachine::from_state(
            current_profile(),
            direct_initial.memory().to_vec(),
            input.clone(),
            malbolge::ProfileRegisters::default(),
        )
        .map_err(|error| format!("direct validated checkpoint: {error:?}"))?;
        assert!(
            matches!(
                guest.run(TWO_GUEST_STEPS),
                Ok(RunOutcome::Terminated { steps: 88, .. })
            ),
            "guest two-opcode dispatch must halt even on EOF or extra input"
        );
        assert!(
            matches!(
                direct_vm.run(5),
                Ok(RunOutcome::Terminated { steps: 5, .. })
            ),
            "direct two-pair guest must halt even on EOF or extra input"
        );
        assert_eq!(
            guest.output(),
            direct_vm.output(),
            "guest vs direct stdout must match under EOF and excess input"
        );
        assert_eq!(
            guest.output().len(),
            2,
            "each of two output operations writes a byte"
        );
        assert_eq!(
            guest.input_consumed(),
            direct_vm.input_consumed(),
            "guest vs direct must consume identical available input bytes"
        );
        assert_eq!(
            guest.input_consumed(),
            input.len().min(2),
            "each program only consumes up to two provided input bytes"
        );
        for address in [125u32, 126, 155, 190, 226] {
            assert_eq!(
                guest
                    .memory_word(address)
                    .map_err(|error| format!("guest payload address {address}: {error:?}"))?,
                u32::from(
                    *source
                        .get(usize::try_from(address).map_err(|error| error.to_string())?)
                        .ok_or("source glyph")?
                ),
                "source-bound CEB2 tail must remain unchanged after all I/O modes"
            );
        }
    }
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "real second graphical guest dispatch mutation witness"
)]
#[expect(
    clippy::too_many_lines,
    reason = "native guest branch versus host trust boundary"
)]
#[expect(
    clippy::cognitive_complexity,
    reason = "real two-code-pointer trace witness"
)]
fn loader_valid_second_opcode_mutation_redirects_actual_guest_but_fails_host_admission()
-> Result<(), String> {
    let original = program(2)?;
    let candidate = encode_bound_echo_macro(&original, current_profile())
        .map_err(|error| format!("source-bound two-pair descriptor: {error:?}"))?;
    let source = embed_two_echo_opcodes(&original, current_profile(), &candidate)
        .map_err(|error| format!("original exact guest source: {error:?}"))?;
    let mut changed = source.clone();
    let original_glyph = *changed
        .get(SECOND_OPCODE_ADDRESS)
        .ok_or("original second guest opcode")?;
    assert_eq!(original_glyph, 104, "normative second source glyph");
    // Graphical 87 is a valid loader cell at position 124. The actual guest
    // uses its *numeric word*, redirecting second C to address 88 instead of
    // 105. No host-provided VM register or mock instruction is involved.
    let forged_glyph = 87u8;
    assert_eq!(
        decode_profile_instruction(u32::from(forged_glyph), 124),
        Some(b'/'),
        "mutated second opcode remains a graphical loader-valid source word"
    );
    *changed
        .get_mut(SECOND_OPCODE_ADDRESS)
        .ok_or("second opcode cell")? = forged_glyph;
    assert_eq!(
        admit_two_echo_opcodes(&original, current_profile(), &source),
        Ok(candidate),
        "original source remains bound and admitted"
    );
    assert_eq!(
        admit_two_echo_opcodes(&original, current_profile(), &changed),
        Err(TwoOpcodeError::InvalidSource),
        "host rejects mutated code identity before publication"
    );
    for (test_source, expected_word) in [(&source, 104u32), (&changed, 87u32)] {
        let mut machine = ProfileMachine::from_source(current_profile(), test_source, vec![0, 255])
            .map_err(|error| format!("normative VM load: {error:?}"))?;
        let mut second = None;
        let outcome = machine
            .run_traced(85, &mut |event| {
                if event.before.registers.code_pointer == 93 {
                    second = Some(*event);
                }
            })
            .map_err(|error| format!("guest second jump: {error:?}"))?;
        assert!(
            matches!(outcome, RunOutcome::BudgetExhausted { steps: 85 }),
            "run exactly to the second native indirect jump, before handler"
        );
        let jump = second.ok_or("missing second reached guest indirect trace")?;
        assert_eq!(jump.decoded, Some(b'i'), "must genuinely execute i@93");
        assert_eq!(
            jump.before.registers.data_pointer, 124,
            "second opcode is read from source position 124"
        );
        assert_eq!(
            jump.memory_reads
                .data
                .map(|read| (read.address, read.value)),
            Some((124, expected_word)),
            "real guest reads changed graphical word"
        );
        assert_eq!(
            jump.memory_delta.encryption.map(|write| write.address),
            Some(expected_word),
            "self-encryption follows actual guest target C"
        );
        assert_eq!(
            machine.registers().code_pointer,
            expected_word.saturating_add(1),
            "guest control flow follows actual source byte, not host source check"
        );
        assert_eq!(
            machine.output(),
            &[0u8],
            "first operation is unaffected by the later opcode change"
        );
        assert_eq!(
            machine.input_consumed(),
            1,
            "first byte was truly consumed before second dispatch"
        );
    }
    Ok(())
}
