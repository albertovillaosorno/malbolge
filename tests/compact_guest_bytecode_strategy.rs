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
#[path = "../algorithms/compact-guest-bytecode-strategy/graphical_residency.rs"]
pub mod residency;
#[path = "../algorithms/compact-guest-bytecode-strategy/echo_macro.rs"]
pub mod strategy;

use malbolge::{
    ProfileMachine, RunOutcome, current_profile, decode_profile_instruction, historical_profile,
};
use std::collections::BTreeSet;
use std::fs;
use std::path::{Path, PathBuf};
use std::process::{Command, id};

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

const BOUND_PILOT_CONFIG: &str =
    include_str!("../algorithms/compact-guest-bytecode-strategy/pilot-v1.toml");

const GUEST_PROBE_CONFIG: &str =
    include_str!("../algorithms/compact-guest-bytecode-strategy/pilot-v3.toml");
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

#[expect(clippy::missing_trait_methods, reason = "owned test fixture cleanup")]
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
