// Copyright:
//   - Copyright (c) 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - MIT
// Confidential:
//   - false
// License-File:
//   - LICENSE-MIT
//
// Boundary-Contract:
// - Owns:
//   - Product execution-IR canonicalization and native-cache identity evidence.
// - Must-Not:
//   - Depend on architecture machine code or state-graph private internals.
// - Allows:
//   - Inputs: public VM value types and product execution/cache modules.
//   - Outputs: deterministic encoding and collision-safe cache-key assertions.
//   - Side effects: test-process allocation only.
// - Split-When:
//   - Split when native backend differential fixtures need separate lifecycle.
// - Merge-When:
//   - Merge when product tiered execution tests own the same identity surface.
// - Summary:
//   - Proves portable IR and host-target cache identity are
//   - architecture-stable.
// - Description:
//   - Mutates semantic and target fields and forces bucket collisions.
// - Usage:
//   - Auto-discovered by the root Cargo workspace.
// - Defaults:
//   - Full canonical equality, never a digest alone, decides reuse.
//

//! Product tiered-execution identity and cache-key conformance.

#[path = "../src/runtime/tiered-execution/adapter-outbound/cache/main.rs"]
pub mod execution_cache;
#[path = "../src/runtime/tiered-execution/domain/ir/main.rs"]
pub mod execution_ir;
#[path = "../src/runtime/tiered-execution/adapter-outbound/native/main.rs"]
pub mod execution_native;

use std::fs::{create_dir_all, read, remove_dir_all, write};
use std::path::{Path, PathBuf};
use std::process::Command;
use std::str::from_utf8;
use std::sync::Arc;

use execution_cache::{
    HostIsa, HostOperatingSystem, NativeArtifactCache, NativeArtifactKey,
    NativeIdentityError, NativeTargetConfig, NativeTargetIdentity,
    RegionEffectIdentity,
};
use execution_ir::{
    EFFECT_IR_VERSION, EffectOp, MemoryLiveIn, RegionEffectProgram,
    StepProgramProjectionError, TargetProfileRequirement,
};
use execution_native::{
    CLANG_C23_BOOTSTRAP_BACKEND_ID, CLANG_C23_BOOTSTRAP_BACKEND_REVISION,
    CachedPreflightedExecutionTier, CoffAdmissionError,
    DIRECT_CRAZY_BACKEND_ID, DIRECT_CRAZY_BACKEND_REVISION,
    DIRECT_DEOPT_BACKEND_ID, DIRECT_DEOPT_BACKEND_REVISION,
    DIRECT_HALT_FETCH_BACKEND_ID, DIRECT_HALT_FETCH_BACKEND_REVISION,
    DIRECT_HALT_REGISTERS_BACKEND_ID, DIRECT_HALT_REGISTERS_BACKEND_REVISION,
    DIRECT_INITIAL_HALT_BACKEND_ID, DIRECT_INITIAL_HALT_BACKEND_REVISION,
    DIRECT_INPUT_BACKEND_ID, DIRECT_INPUT_BACKEND_REVISION,
    DIRECT_JUMP_CODE_BACKEND_ID, DIRECT_JUMP_CODE_BACKEND_REVISION,
    DIRECT_JUMP_DATA_BACKEND_ID, DIRECT_JUMP_DATA_BACKEND_REVISION,
    DIRECT_NO_OPERATION_BACKEND_ID, DIRECT_NO_OPERATION_BACKEND_REVISION,
    DIRECT_NON_GRAPHICAL_BACKEND_ID, DIRECT_NON_GRAPHICAL_BACKEND_REVISION,
    DIRECT_OUTPUT_BACKEND_ID, DIRECT_OUTPUT_BACKEND_REVISION,
    DIRECT_ROTATE_BACKEND_ID, DIRECT_ROTATE_BACKEND_REVISION,
    DirectCacheDisposition, DirectCrazyError, DirectDeoptError,
    DirectHaltFetchError, DirectHaltRegistersError, DirectHost,
    DirectInitialHaltError, DirectInputError, DirectJumpCodeError,
    DirectJumpDataError, DirectNativeKind, DirectNoOperationError,
    DirectNonGraphicalError, DirectOutputError, DirectRotateError,
    DirectSelectionError, DirectSequenceError, NATIVE_REGION_ABI_REVISION,
    NativeArtifactError, PreflightedExecutionTier,
    UntrustedNativeObjectArtifact, VerifiedDirectNativeCache,
    emit_direct_crazy_coff, emit_direct_deopt_coff,
    emit_direct_halt_fetch_coff, emit_direct_halt_registers_coff,
    emit_direct_initial_halt_coff, emit_direct_input_coff,
    emit_direct_jump_code_coff, emit_direct_jump_data_coff,
    emit_direct_no_operation_coff, emit_direct_non_graphical_coff,
    emit_direct_output_coff, emit_direct_rotate_coff, lower_clang_c23,
    select_cached_preflighted_execution_tier,
    select_preflighted_execution_tier, select_verified_direct_native,
    select_verified_direct_sequence, structurally_admit_coff,
    verify_direct_crazy, verify_direct_deopt_stub, verify_direct_halt_fetch,
    verify_direct_halt_registers, verify_direct_initial_halt,
    verify_direct_input, verify_direct_jump_code, verify_direct_jump_data,
    verify_direct_no_operation, verify_direct_non_graphical,
    verify_direct_output, verify_direct_rotate,
};
use malbolge::{
    ProfileMachine, ProfileMachineError, ProfileMachineIoState,
    ProfileMachineObservation, ProfileMachineState, ProfileMemoryDelta,
    ProfileMemoryRead, ProfileMemoryWrite, ProfileRegisters,
    ProfileRequirementErrorKind, ProfileStepTrace, RunOutcome, Termination,
    TraceInput, current_profile, decode_profile_instruction, preflight_profile,
    preflight_runtime_requirement, safe_rust_classic_capability,
    safe_rust_profiled_capability,
};

#[derive(Clone, Copy)]
struct CoffCompileCase {
    expected_machine: [u8; 2],
    isa: HostIsa,
}

type CollisionKeys = (NativeArtifactKey, NativeArtifactKey);

type DirectSelectionCase =
    (RegionEffectProgram, DirectNativeKind, &'static str);

fn canonical_fixture_bytes() -> Result<Vec<u8>, String> {
    decode_hex_fixture(include_str!("execution/fixtures/region-effect-v3.hex"))
}

fn decode_hex_fixture(text: &str) -> Result<Vec<u8>, String> {
    let compact = text.split_whitespace().collect::<String>();
    let (pairs, remainder) = compact.as_bytes().as_chunks::<2>();
    if !remainder.is_empty() {
        return Err(String::from("canonical fixture has odd hex length"));
    }
    let mut bytes = Vec::new();
    for pair in pairs {
        let digits = from_utf8(pair)
            .map_err(|error| format!("canonical fixture UTF-8: {error}"))?;
        let value = u8::from_str_radix(digits, 16)
            .map_err(|error| format!("canonical fixture hex: {error}"))?;
        bytes.push(value);
    }
    Ok(bytes)
}

fn expected_profile_metadata(
    program: &RegionEffectProgram,
) -> Result<Vec<u8>, String> {
    fn push_bytes(output: &mut Vec<u8>, value: &[u8]) -> Result<(), String> {
        let length = u32::try_from(value.len()).map_err(|_error| {
            String::from("profile metadata length overflow")
        })?;
        output.extend_from_slice(&length.to_le_bytes());
        output.extend_from_slice(value);
        Ok(())
    }

    let feature_count =
        u32::try_from(program.profile_requirement.features.len())
            .map_err(|_error| String::from("profile feature count overflow"))?;
    let mut bytes = Vec::new();
    bytes.extend_from_slice(b"MBPF");
    bytes.extend_from_slice(&3u16.to_le_bytes());
    bytes.extend_from_slice(&0u16.to_le_bytes());
    push_bytes(&mut bytes, program.profile_id.as_bytes())?;
    push_bytes(&mut bytes, program.profile_fingerprint.as_bytes())?;
    push_bytes(&mut bytes, program.profile_requirement.version.as_bytes())?;
    bytes.extend_from_slice(&feature_count.to_le_bytes());
    for feature in &program.profile_requirement.features {
        push_bytes(&mut bytes, feature.as_bytes())?;
    }
    bytes.push(program.profile_requirement.word_trits);
    bytes.extend_from_slice(
        &program.profile_requirement.memory_words.to_le_bytes(),
    );
    bytes.extend_from_slice(&program.required_memory_words().to_le_bytes());
    Ok(bytes)
}

fn rendered_profile_metadata(source: &str) -> Result<Vec<u8>, String> {
    let marker = "const unsigned char malbolge_profile_metadata[] = {\n";
    let start = source
        .find(marker)
        .map(|offset| offset.saturating_add(marker.len()))
        .ok_or_else(|| {
            String::from("bootstrap metadata declaration missing")
        })?;
    let remainder = source
        .get(start..)
        .ok_or_else(|| String::from("bootstrap metadata start invalid"))?;
    let end = remainder
        .find("};\n\n")
        .ok_or_else(|| String::from("bootstrap metadata terminator missing"))?;
    remainder
        .get(..end)
        .ok_or_else(|| String::from("bootstrap metadata range invalid"))?
        .split(',')
        .map(str::trim)
        .filter(|value| !value.is_empty())
        .map(|value| {
            let digits = value.strip_prefix("0x").ok_or_else(|| {
                format!("bootstrap metadata byte lacks hex prefix: {value}")
            })?;
            u8::from_str_radix(digits, 16)
                .map_err(|error| format!("bootstrap metadata hex: {error}"))
        })
        .collect()
}

fn current_profile_requirement() -> TargetProfileRequirement {
    TargetProfileRequirement::from_descriptor(current_profile())
}

fn observation(seed: u32) -> ProfileMachineObservation {
    ProfileMachineObservation {
        input_consumed: usize::try_from(seed).unwrap_or(0),
        output_len: usize::try_from(seed.saturating_add(1)).unwrap_or(0),
        registers: ProfileRegisters {
            accumulator: seed.saturating_add(2),
            code_pointer: seed.saturating_add(3),
            data_pointer: seed.saturating_add(4),
        },
        termination: None,
    }
}

fn program() -> RegionEffectProgram {
    RegionEffectProgram {
        effects: vec![EffectOp {
            after: ProfileMachineObservation {
                termination: Some(Termination::HaltInstruction),
                ..observation(10)
            },
            before: observation(1),
            input: Some(TraceInput::Byte(0x41)),
            memory_delta: ProfileMemoryDelta {
                data: Some(ProfileMemoryWrite {
                    address: 7,
                    after: 9,
                    before: 8,
                }),
                encryption: Some(ProfileMemoryWrite {
                    address: 11,
                    after: 13,
                    before: 12,
                }),
            },
            output: Some(0x42),
        }],
        format_version: EFFECT_IR_VERSION,
        memory_live_ins: vec![
            MemoryLiveIn { address: 17, value: 18 },
            MemoryLiveIn { address: 19, value: 20 },
        ],
        outcome: RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 1,
        },
        profile_fingerprint: String::from("malbolge-profile-v1:sha256:fixture"),
        profile_id: String::from("malbolge-2026.2"),
        profile_requirement: current_profile_requirement(),
        step_budget: 8,
    }
}

fn target(
    os: HostOperatingSystem,
    isa: HostIsa,
    features: Vec<String>,
) -> NativeTargetIdentity {
    NativeTargetIdentity::new(NativeTargetConfig {
        backend_id: String::from("baseline"),
        backend_revision: 3,
        host_isa: isa,
        host_os: os,
        native_abi_revision: 1,
        required_features: features,
    })
}

fn base_target_config() -> NativeTargetConfig {
    NativeTargetConfig {
        backend_id: String::from("baseline"),
        backend_revision: 3,
        host_isa: HostIsa::X86_64,
        host_os: HostOperatingSystem::Windows,
        native_abi_revision: 1,
        required_features: vec![String::from("sse2")],
    }
}

fn target_variant_configs() -> Vec<NativeTargetConfig> {
    let base = base_target_config();
    let mut linux = base.clone();
    linux.host_os = HostOperatingSystem::Linux;
    let mut aarch64 = base.clone();
    aarch64.host_isa = HostIsa::AArch64;
    let mut backend = base.clone();
    backend.backend_id = String::from("other-backend");
    let mut revision = base.clone();
    revision.backend_revision = revision.backend_revision.saturating_add(1);
    let mut abi = base.clone();
    abi.native_abi_revision = abi.native_abi_revision.saturating_add(1);
    let mut feature = base;
    feature.required_features.push(String::from("avx2"));
    vec![linux, aarch64, backend, revision, abi, feature]
}

fn assert_key_differs(
    base: &NativeArtifactKey,
    candidate: Result<NativeArtifactKey, NativeIdentityError>,
) -> Result<(), String> {
    let observed =
        candidate.map_err(|error| format!("variant key failed: {error:?}"))?;
    if &observed == base {
        Err(String::from("target assumption did not change cache key"))
    } else {
        Ok(())
    }
}

#[test]
fn canonical_ir_matches_versioned_byte_fixture() -> Result<(), String> {
    let observed = program().canonical_bytes().map_err(|error| {
        format!("canonical fixture render failed: {error:?}")
    })?;
    let expected = canonical_fixture_bytes()?;
    if observed == expected {
        Ok(())
    } else {
        Err(format!(
            "canonical IR fixture mismatch: observed={} expected={}",
            observed.len(),
            expected.len()
        ))
    }
}

#[test]
fn canonical_ir_changes_when_any_semantic_field_changes() -> Result<(), String>
{
    let baseline = program();
    let bytes = baseline
        .canonical_bytes()
        .map_err(|error| format!("canonical baseline failed: {error:?}"))?;
    let mut variants = Vec::new();

    let mut profile_id = baseline.clone();
    profile_id.profile_id.push('x');
    variants.push(profile_id);

    let mut profile_fingerprint = baseline.clone();
    profile_fingerprint.profile_fingerprint.push('x');
    variants.push(profile_fingerprint);

    let mut profile_features = baseline.clone();
    let _removed = profile_features.profile_requirement.features.pop();
    variants.push(profile_features);

    let mut profile_memory = baseline.clone();
    profile_memory.profile_requirement.memory_words = profile_memory
        .profile_requirement
        .memory_words
        .saturating_add(1);
    variants.push(profile_memory);

    let mut profile_version = baseline.clone();
    profile_version.profile_requirement.version.push('x');
    variants.push(profile_version);

    let mut profile_word_trits = baseline.clone();
    profile_word_trits.profile_requirement.word_trits = profile_word_trits
        .profile_requirement
        .word_trits
        .saturating_add(1);
    variants.push(profile_word_trits);

    let mut budget = baseline.clone();
    budget.step_budget = budget.step_budget.saturating_add(1);
    variants.push(budget);

    let mut outcome = baseline.clone();
    outcome.outcome = RunOutcome::BudgetExhausted { steps: 1 };
    variants.push(outcome);

    let mut live_in = baseline.clone();
    let first_live_in = live_in
        .memory_live_ins
        .first_mut()
        .ok_or_else(|| String::from("fixture has no memory live-in"))?;
    first_live_in.value = first_live_in.value.saturating_add(1);
    variants.push(live_in);

    let mut effect = baseline;
    let first_effect = effect
        .effects
        .first_mut()
        .ok_or_else(|| String::from("fixture has no effect"))?;
    first_effect.output = None;
    variants.push(effect);

    for variant in variants {
        let observed = variant
            .canonical_bytes()
            .map_err(|error| format!("canonical variant failed: {error:?}"))?;
        if observed == bytes {
            return Err(String::from(
                "semantic IR mutation kept canonical bytes",
            ));
        }
    }
    Ok(())
}

#[test]
fn portable_ir_derives_exact_required_memory_words() -> Result<(), String> {
    let baseline = program();
    if baseline.required_memory_words() != 20 {
        return Err(format!(
            "baseline IR memory footprint: {}",
            baseline.required_memory_words()
        ));
    }

    let mut effect_only = baseline;
    effect_only.memory_live_ins.clear();
    if effect_only.required_memory_words() != 15 {
        return Err(format!(
            "observation IR memory footprint: {}",
            effect_only.required_memory_words()
        ));
    }

    let first_effect = effect_only
        .effects
        .first_mut()
        .ok_or_else(|| String::from("fixture has no effect"))?;
    let data_write = first_effect
        .memory_delta
        .data
        .as_mut()
        .ok_or_else(|| String::from("fixture has no data write"))?;
    data_write.address = 100;
    if effect_only.required_memory_words() != 101 {
        return Err(String::from("write address was omitted from footprint"));
    }

    let max_pointer_effect = effect_only
        .effects
        .first_mut()
        .ok_or_else(|| String::from("fixture lost effect"))?;
    max_pointer_effect.after.registers.data_pointer = u32::MAX;
    if effect_only.required_memory_words() == 4_294_967_296 {
        Ok(())
    } else {
        Err(String::from("u32::MAX address footprint was truncated"))
    }
}

#[test]
fn native_identity_rejects_profile_capacity_inconsistent_ir()
-> Result<(), String> {
    let program = profile_invalid_native_program();
    let canonical = program
        .canonical_bytes()
        .map_err(|error| format!("untrusted IR transport failed: {error:?}"))?;
    if canonical.is_empty() || program.fits_declared_profile_capacity() {
        return Err(String::from("profile-invalid IR classification drifted"));
    }
    if RegionEffectIdentity::new(&program)
        != Err(NativeIdentityError::ProfileCapacity)
    {
        return Err(String::from("profile-invalid IR gained cache identity"));
    }
    let target = NativeTargetIdentity::new(base_target_config());
    if NativeArtifactKey::new(&program, target)
        == Err(NativeIdentityError::ProfileCapacity)
    {
        Ok(())
    } else {
        Err(String::from("profile-invalid IR gained native key"))
    }
}

#[test]
fn native_emitters_reject_profile_capacity_inconsistent_ir()
-> Result<(), String> {
    let program = profile_invalid_native_program();
    if lower_clang_c23(&program, native_target(HostIsa::X86_64))
        != Err(NativeArtifactError::Identity(
            NativeIdentityError::ProfileCapacity,
        ))
    {
        return Err(String::from("bootstrap admitted profile-invalid IR"));
    }
    if emit_direct_deopt_coff(&program, direct_deopt_target(HostIsa::X86_64))
        == Err(DirectDeoptError::Identity(
            NativeIdentityError::ProfileCapacity,
        ))
    {
        Ok(())
    } else {
        Err(String::from("direct deopt admitted profile-invalid IR"))
    }
}

#[test]
fn cache_key_includes_declared_profile_identity() -> Result<(), String> {
    let program = program();
    let target = NativeTargetIdentity::new(base_target_config());
    let base = NativeArtifactKey::new(&program, target.clone())
        .map_err(|error| format!("base profile key failed: {error:?}"))?;
    if base.ir().profile_id() != program.profile_id
        || base.ir().profile_fingerprint() != program.profile_fingerprint
        || base.ir().profile_requirement() != &program.profile_requirement
        || base.ir().required_memory_words() != program.required_memory_words()
    {
        return Err(String::from("native key lost exact profile identity"));
    }
    let mut renamed = program;
    renamed.profile_id = String::from("malbolge-2026.2-alias");
    let candidate = NativeArtifactKey::new(&renamed, target)
        .map_err(|error| format!("renamed profile key failed: {error:?}"))?;
    if base == candidate {
        return Err(String::from(
            "declared profile identity did not change cache key",
        ));
    }
    Ok(())
}

#[test]
fn cache_key_includes_host_and_backend_assumptions() -> Result<(), String> {
    let program = program();
    let base = NativeArtifactKey::new(
        &program,
        NativeTargetIdentity::new(base_target_config()),
    )
    .map_err(|error| format!("base key failed: {error:?}"))?;
    for config in target_variant_configs() {
        assert_key_differs(
            &base,
            NativeArtifactKey::new(&program, NativeTargetIdentity::new(config)),
        )?;
    }
    Ok(())
}

#[test]
fn process_cache_removes_all_variants_for_exact_region() -> Result<(), String> {
    let program = program();
    let mut other_program = program.clone();
    other_program.profile_id.push_str("-other");
    let x86 = NativeArtifactKey::new(
        &program,
        target(HostOperatingSystem::Windows, HostIsa::X86_64, Vec::new()),
    )
    .map_err(|error| format!("x86 region key failed: {error:?}"))?;
    let arm = NativeArtifactKey::new(
        &program,
        target(HostOperatingSystem::Windows, HostIsa::AArch64, Vec::new()),
    )
    .map_err(|error| format!("ARM region key failed: {error:?}"))?;
    let other = NativeArtifactKey::new(
        &other_program,
        target(HostOperatingSystem::Windows, HostIsa::X86_64, Vec::new()),
    )
    .map_err(|error| format!("other region key failed: {error:?}"))?;
    let identity = RegionEffectIdentity::new(&program)
        .map_err(|error| format!("region identity failed: {error:?}"))?;
    let mut cache = NativeArtifactCache::default();
    let _x86 = cache.insert(x86, "x86");
    let _arm = cache.insert(arm, "arm");
    let _other = cache.insert(other.clone(), "other");
    if cache.remove_region(&identity) != 2
        || cache.remove_region(&identity) != 0
        || cache.len() != 1
        || cache.get(&other) != Some(&"other")
    {
        Err(String::from("region invalidation crossed exact identity"))
    } else {
        Ok(())
    }
}

#[test]
fn process_cache_removes_all_regions_for_exact_target() -> Result<(), String> {
    let program = program();
    let mut other_program = program.clone();
    other_program.profile_id.push_str("-other");
    let x86_target =
        target(HostOperatingSystem::Windows, HostIsa::X86_64, Vec::new());
    let arm_target =
        target(HostOperatingSystem::Windows, HostIsa::AArch64, Vec::new());
    let x86 = NativeArtifactKey::new(&program, x86_target.clone())
        .map_err(|error| format!("x86 target key failed: {error:?}"))?;
    let other_x86 = NativeArtifactKey::new(&other_program, x86_target.clone())
        .map_err(|error| format!("other x86 key failed: {error:?}"))?;
    let arm = NativeArtifactKey::new(&program, arm_target)
        .map_err(|error| format!("ARM target key failed: {error:?}"))?;
    let mut cache = NativeArtifactCache::default();
    let _x86 = cache.insert(x86, "x86");
    let _other_x86 = cache.insert(other_x86, "other-x86");
    let _arm = cache.insert(arm.clone(), "arm");
    if cache.remove_target(&x86_target) != 2
        || cache.remove_target(&x86_target) != 0
        || cache.len() != 1
        || cache.get(&arm) != Some(&"arm")
    {
        Err(String::from(
            "target invalidation crossed exact assumptions",
        ))
    } else {
        Ok(())
    }
}

#[test]
fn portable_ir_uses_shared_runtime_diagnostic() -> Result<(), String> {
    let program = program();
    let current = current_profile();
    let Err(canonical) = preflight_profile(
        current,
        current.memory_words(),
        safe_rust_classic_capability(),
    ) else {
        return Err(String::from(
            "classic runtime unexpectedly admitted current profile",
        ));
    };
    let Err(portable) = preflight_runtime_requirement(
        &program.profile_id,
        &program.profile_requirement,
        safe_rust_classic_capability(),
    ) else {
        return Err(String::from(
            "classic runtime unexpectedly admitted portable requirement",
        ));
    };
    if format!("{portable}") != format!("{canonical}") {
        return Err(String::from(
            "portable IR requirement changed shared runtime diagnostic",
        ));
    }
    preflight_runtime_requirement(
        &program.profile_id,
        &program.profile_requirement,
        safe_rust_profiled_capability(),
    )
    .map_err(|error| format!("profiled runtime rejected portable IR: {error}"))
}

#[test]
fn required_feature_order_is_canonical() -> Result<(), String> {
    let program = program();
    let left = NativeArtifactKey::new(
        &program,
        target(HostOperatingSystem::Linux, HostIsa::X86_64, vec![
            String::from("avx2"),
            String::from("sse2"),
        ]),
    )
    .map_err(|error| format!("left feature key failed: {error:?}"))?;
    let right = NativeArtifactKey::new(
        &program,
        target(HostOperatingSystem::Linux, HostIsa::X86_64, vec![
            String::from("sse2"),
            String::from("avx2"),
            String::from("sse2"),
        ]),
    )
    .map_err(|error| format!("right feature key failed: {error:?}"))?;
    if left == right {
        Ok(())
    } else {
        Err(String::from(
            "feature order/duplicates changed canonical key",
        ))
    }
}

const fn constant_bucket_digest(_bytes: &[u8]) -> u64 {
    0
}

const fn alternate_bucket_digest(_bytes: &[u8]) -> u64 {
    1
}

fn forced_collision_keys() -> Result<CollisionKeys, String> {
    let left_program = program();
    let mut right_program = left_program.clone();
    let first_effect = right_program
        .effects
        .first_mut()
        .ok_or_else(|| String::from("collision fixture has no effect"))?;
    first_effect.output = Some(0x43);
    let left = NativeArtifactKey::with_digest(
        &left_program,
        target(HostOperatingSystem::Windows, HostIsa::X86_64, Vec::new()),
        constant_bucket_digest,
    )
    .map_err(|error| format!("left collision key failed: {error:?}"))?;
    let right = NativeArtifactKey::with_digest(
        &right_program,
        target(HostOperatingSystem::Windows, HostIsa::X86_64, Vec::new()),
        constant_bucket_digest,
    )
    .map_err(|error| format!("right collision key failed: {error:?}"))?;
    Ok((left, right))
}

#[test]
fn cache_digest_never_participates_in_exact_identity() -> Result<(), String> {
    let program = program();
    let target =
        target(HostOperatingSystem::Windows, HostIsa::X86_64, Vec::new());
    let left = NativeArtifactKey::with_digest(
        &program,
        target.clone(),
        constant_bucket_digest,
    )
    .map_err(|error| format!("left digest key failed: {error:?}"))?;
    let right = NativeArtifactKey::with_digest(
        &program,
        target,
        alternate_bucket_digest,
    )
    .map_err(|error| format!("right digest key failed: {error:?}"))?;
    if left.bucket_digest() == right.bucket_digest()
        || left.ir().bucket_digest() == right.ir().bucket_digest()
        || left != right
        || left.ir() != right.ir()
    {
        return Err(String::from("lookup digest changed exact identity"));
    }

    let mut cache = NativeArtifactCache::default();
    if cache.insert(left.clone(), "left").is_some()
        || cache.get(&right) != Some(&"left")
        || cache.insert(right.clone(), "right") != Some("left")
        || cache.len() != 1
        || cache.get(&left) != Some(&"right")
        || cache.remove(&right) != Some("right")
        || !cache.is_empty()
    {
        Err(String::from("cache promoted digest to reuse authority"))
    } else {
        Ok(())
    }
}

#[test]
fn cache_equality_ignores_bucket_accelerator_layout() -> Result<(), String> {
    let program = program();
    let target =
        target(HostOperatingSystem::Windows, HostIsa::X86_64, Vec::new());
    let left_key = NativeArtifactKey::with_digest(
        &program,
        target.clone(),
        constant_bucket_digest,
    )
    .map_err(|error| format!("left cache key failed: {error:?}"))?;
    let right_key = NativeArtifactKey::with_digest(
        &program,
        target,
        alternate_bucket_digest,
    )
    .map_err(|error| format!("right cache key failed: {error:?}"))?;
    let mut left = NativeArtifactCache::default();
    let mut right = NativeArtifactCache::default();
    let _left = left.insert(left_key, "value");
    let _right = right.insert(right_key.clone(), "value");
    if left != right {
        return Err(String::from("cache equality retained bucket layout"));
    }
    let _changed = right.insert(right_key, "changed");
    if left == right {
        Err(String::from("cache equality ignored retained values"))
    } else {
        Ok(())
    }
}

#[test]
fn forced_bucket_collision_never_authorizes_reuse() -> Result<(), String> {
    let (left, right) = forced_collision_keys()?;
    if left.bucket_digest() != right.bucket_digest() {
        return Err(String::from("forced cache digest did not collide"));
    }
    if left == right {
        return Err(String::from(
            "bucket collision incorrectly merged cache keys",
        ));
    }
    Ok(())
}

#[test]
fn process_cache_confirms_full_keys_after_collision() -> Result<(), String> {
    let (left, right) = forced_collision_keys()?;
    let mut cache = NativeArtifactCache::default();
    if !cache.is_empty() {
        return Err(String::from("new native cache was not empty"));
    }
    if cache.insert(left.clone(), "left").is_some()
        || cache.insert(right.clone(), "right").is_some()
        || cache.len() != 2
        || cache.get(&left) != Some(&"left")
        || cache.get(&right) != Some(&"right")
    {
        return Err(String::from("collision bucket lost exact entries"));
    }
    if cache.insert(left.clone(), "left-replaced") != Some("left")
        || cache.len() != 2
        || cache.get(&left) != Some(&"left-replaced")
        || cache.get(&right) != Some(&"right")
    {
        return Err(String::from("exact replacement crossed collision key"));
    }
    if cache.remove(&left) != Some("left-replaced")
        || cache.get(&left).is_some()
        || cache.get(&right) != Some(&"right")
        || cache.len() != 1
    {
        return Err(String::from("exact removal crossed collision key"));
    }
    cache.clear();
    if cache.is_empty() && cache.get(&right).is_none() {
        Ok(())
    } else {
        Err(String::from("native cache clear retained an entry"))
    }
}

const fn native_observation(
    input_consumed: usize,
    output_len: usize,
    registers: ProfileRegisters,
    termination: Option<Termination>,
) -> ProfileMachineObservation {
    ProfileMachineObservation {
        input_consumed,
        output_len,
        registers,
        termination,
    }
}

const fn native_first_effect(
    entry: ProfileMachineObservation,
    middle: ProfileMachineObservation,
) -> EffectOp {
    EffectOp {
        after: middle,
        before: entry,
        input: Some(TraceInput::Byte(0x41)),
        memory_delta: ProfileMemoryDelta {
            data: Some(ProfileMemoryWrite {
                address: 7,
                after: 9,
                before: 8,
            }),
            encryption: Some(ProfileMemoryWrite {
                address: 11,
                after: 13,
                before: 12,
            }),
        },
        output: Some(0x42),
    }
}

const fn native_second_effect(
    middle: ProfileMachineObservation,
    exit: ProfileMachineObservation,
) -> EffectOp {
    EffectOp {
        after: exit,
        before: middle,
        input: None,
        memory_delta: ProfileMemoryDelta {
            data: Some(ProfileMemoryWrite {
                address: 7,
                after: 10,
                before: 9,
            }),
            encryption: Some(ProfileMemoryWrite {
                address: 11,
                after: 14,
                before: 13,
            }),
        },
        output: None,
    }
}

fn native_program() -> RegionEffectProgram {
    let entry = native_observation(
        0,
        0,
        ProfileRegisters {
            accumulator: 3,
            code_pointer: 4,
            data_pointer: 5,
        },
        None,
    );
    let middle = native_observation(
        1,
        1,
        ProfileRegisters {
            accumulator: 6,
            code_pointer: 7,
            data_pointer: 8,
        },
        None,
    );
    let exit = native_observation(
        1,
        1,
        ProfileRegisters {
            accumulator: 9,
            code_pointer: 10,
            data_pointer: 11,
        },
        Some(Termination::HaltInstruction),
    );
    RegionEffectProgram {
        effects: vec![
            native_first_effect(entry, middle),
            native_second_effect(middle, exit),
        ],
        format_version: EFFECT_IR_VERSION,
        memory_live_ins: vec![MemoryLiveIn { address: 17, value: 18 }],
        outcome: RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 2,
        },
        profile_fingerprint: String::from(
            "malbolge-profile-v1:sha256:native-bootstrap-fixture",
        ),
        profile_id: String::from("malbolge-2026.2"),
        profile_requirement: current_profile_requirement(),
        step_budget: 2,
    }
}

fn profile_invalid_native_program() -> RegionEffectProgram {
    let mut program = native_program();
    program.profile_requirement.memory_words = 1;
    program
}

fn native_target(isa: HostIsa) -> NativeTargetIdentity {
    NativeTargetIdentity::new(NativeTargetConfig {
        backend_id: String::from(CLANG_C23_BOOTSTRAP_BACKEND_ID),
        backend_revision: CLANG_C23_BOOTSTRAP_BACKEND_REVISION,
        host_isa: isa,
        host_os: HostOperatingSystem::Windows,
        native_abi_revision: NATIVE_REGION_ABI_REVISION,
        required_features: Vec::new(),
    })
}

fn direct_deopt_target(isa: HostIsa) -> NativeTargetIdentity {
    NativeTargetIdentity::new(NativeTargetConfig {
        backend_id: String::from(DIRECT_DEOPT_BACKEND_ID),
        backend_revision: DIRECT_DEOPT_BACKEND_REVISION,
        host_isa: isa,
        host_os: HostOperatingSystem::Windows,
        native_abi_revision: NATIVE_REGION_ABI_REVISION,
        required_features: Vec::new(),
    })
}

fn direct_halt_registers_program() -> RegionEffectProgram {
    let before = ProfileMachineObservation {
        input_consumed: 0x0000_0001_2345_6789,
        output_len: 0x0000_0002_3456_789a,
        registers: ProfileRegisters {
            accumulator: 0x1234_5678,
            code_pointer: 0x0034_5678,
            data_pointer: 0x0013_579b,
        },
        termination: None,
    };
    let after = ProfileMachineObservation {
        termination: Some(Termination::HaltInstruction),
        ..before
    };
    RegionEffectProgram {
        effects: vec![EffectOp {
            after,
            before,
            input: None,
            memory_delta: ProfileMemoryDelta::default(),
            output: None,
        }],
        format_version: EFFECT_IR_VERSION,
        memory_live_ins: Vec::new(),
        outcome: RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 1,
        },
        profile_fingerprint: String::from(
            "malbolge-profile-v1:sha256:direct-halt-registers-fixture",
        ),
        profile_id: String::from("malbolge-2026.2"),
        profile_requirement: current_profile_requirement(),
        step_budget: 1,
    }
}

fn direct_halt_registers_target(isa: HostIsa) -> NativeTargetIdentity {
    NativeTargetIdentity::new(NativeTargetConfig {
        backend_id: String::from(DIRECT_HALT_REGISTERS_BACKEND_ID),
        backend_revision: DIRECT_HALT_REGISTERS_BACKEND_REVISION,
        host_isa: isa,
        host_os: HostOperatingSystem::Windows,
        native_abi_revision: NATIVE_REGION_ABI_REVISION,
        required_features: Vec::new(),
    })
}

fn direct_halt_fetch_program() -> RegionEffectProgram {
    let before = ProfileMachineObservation {
        input_consumed: 0x0000_0001_2345_6789,
        output_len: 0x0000_0002_3456_789a,
        registers: ProfileRegisters {
            accumulator: 0xdead_beef,
            code_pointer: 5,
            data_pointer: 7,
        },
        termination: None,
    };
    let after = ProfileMachineObservation {
        termination: Some(Termination::HaltInstruction),
        ..before
    };
    RegionEffectProgram {
        effects: vec![EffectOp {
            after,
            before,
            input: None,
            memory_delta: ProfileMemoryDelta::default(),
            output: None,
        }],
        format_version: EFFECT_IR_VERSION,
        memory_live_ins: vec![MemoryLiveIn { address: 5, value: 76 }],
        outcome: RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 1,
        },
        profile_fingerprint: String::from(
            "malbolge-profile-v1:sha256:direct-halt-fetch-fixture",
        ),
        profile_id: String::from("malbolge-2026.2"),
        profile_requirement: current_profile_requirement(),
        step_budget: 1,
    }
}

fn direct_halt_fetch_target(isa: HostIsa) -> NativeTargetIdentity {
    NativeTargetIdentity::new(NativeTargetConfig {
        backend_id: String::from(DIRECT_HALT_FETCH_BACKEND_ID),
        backend_revision: DIRECT_HALT_FETCH_BACKEND_REVISION,
        host_isa: isa,
        host_os: HostOperatingSystem::Windows,
        native_abi_revision: NATIVE_REGION_ABI_REVISION,
        required_features: Vec::new(),
    })
}

fn direct_non_graphical_program() -> RegionEffectProgram {
    let before = ProfileMachineObservation {
        input_consumed: 0x0000_0001_2345_6789,
        output_len: 0x0000_0002_3456_789a,
        registers: ProfileRegisters {
            accumulator: 0xdead_beef,
            code_pointer: 5,
            data_pointer: 7,
        },
        termination: None,
    };
    let after = ProfileMachineObservation {
        termination: Some(Termination::NonGraphicalCell),
        ..before
    };
    RegionEffectProgram {
        effects: vec![EffectOp {
            after,
            before,
            input: None,
            memory_delta: ProfileMemoryDelta::default(),
            output: None,
        }],
        format_version: EFFECT_IR_VERSION,
        memory_live_ins: vec![MemoryLiveIn { address: 5, value: 0 }],
        outcome: RunOutcome::Terminated {
            reason: Termination::NonGraphicalCell,
            steps: 1,
        },
        profile_fingerprint: String::from(
            "malbolge-profile-v1:sha256:direct-non-graphical-fixture",
        ),
        profile_id: String::from("malbolge-2026.2"),
        profile_requirement: current_profile_requirement(),
        step_budget: 1,
    }
}

fn direct_non_graphical_target(isa: HostIsa) -> NativeTargetIdentity {
    NativeTargetIdentity::new(NativeTargetConfig {
        backend_id: String::from(DIRECT_NON_GRAPHICAL_BACKEND_ID),
        backend_revision: DIRECT_NON_GRAPHICAL_BACKEND_REVISION,
        host_isa: isa,
        host_os: HostOperatingSystem::Windows,
        native_abi_revision: NATIVE_REGION_ABI_REVISION,
        required_features: Vec::new(),
    })
}

fn direct_jump_code_program() -> RegionEffectProgram {
    let before = ProfileMachineObservation {
        input_consumed: 0x0000_0001_2345_6789,
        output_len: 0x0000_0002_3456_789a,
        registers: ProfileRegisters {
            accumulator: 0xdead_beef,
            code_pointer: 5,
            data_pointer: 7,
        },
        termination: None,
    };
    let after = ProfileMachineObservation {
        registers: ProfileRegisters {
            accumulator: 0xdead_beef,
            code_pointer: 12,
            data_pointer: 8,
        },
        ..before
    };
    RegionEffectProgram {
        effects: vec![EffectOp {
            after,
            before,
            input: None,
            memory_delta: ProfileMemoryDelta {
                data: None,
                encryption: Some(ProfileMemoryWrite {
                    address: 11,
                    after: 33,
                    before: 68,
                }),
            },
            output: None,
        }],
        format_version: EFFECT_IR_VERSION,
        memory_live_ins: vec![
            MemoryLiveIn { address: 5, value: 93 },
            MemoryLiveIn { address: 7, value: 11 },
            MemoryLiveIn { address: 11, value: 68 },
        ],
        outcome: RunOutcome::BudgetExhausted { steps: 1 },
        profile_fingerprint: String::from(
            "malbolge-profile-v1:sha256:direct-jump-code-fixture",
        ),
        profile_id: String::from("malbolge-2026.2"),
        profile_requirement: current_profile_requirement(),
        step_budget: 1,
    }
}

fn direct_jump_code_target(isa: HostIsa) -> NativeTargetIdentity {
    NativeTargetIdentity::new(NativeTargetConfig {
        backend_id: String::from(DIRECT_JUMP_CODE_BACKEND_ID),
        backend_revision: DIRECT_JUMP_CODE_BACKEND_REVISION,
        host_isa: isa,
        host_os: HostOperatingSystem::Windows,
        native_abi_revision: NATIVE_REGION_ABI_REVISION,
        required_features: Vec::new(),
    })
}

fn direct_jump_data_program() -> RegionEffectProgram {
    let before = ProfileMachineObservation {
        input_consumed: 0x0000_0001_2345_6789,
        output_len: 0x0000_0002_3456_789a,
        registers: ProfileRegisters {
            accumulator: 0xdead_beef,
            code_pointer: 5,
            data_pointer: 7,
        },
        termination: None,
    };
    let after = ProfileMachineObservation {
        registers: ProfileRegisters {
            accumulator: 0xdead_beef,
            code_pointer: 6,
            data_pointer: 124,
        },
        ..before
    };
    RegionEffectProgram {
        effects: vec![EffectOp {
            after,
            before,
            input: None,
            memory_delta: ProfileMemoryDelta {
                data: None,
                encryption: Some(ProfileMemoryWrite {
                    address: 5,
                    after: 93,
                    before: 35,
                }),
            },
            output: None,
        }],
        format_version: EFFECT_IR_VERSION,
        memory_live_ins: vec![
            MemoryLiveIn { address: 5, value: 35 },
            MemoryLiveIn { address: 7, value: 123 },
        ],
        outcome: RunOutcome::BudgetExhausted { steps: 1 },
        profile_fingerprint: String::from(
            "malbolge-profile-v1:sha256:direct-jump-data-fixture",
        ),
        profile_id: String::from("malbolge-2026.2"),
        profile_requirement: current_profile_requirement(),
        step_budget: 1,
    }
}

fn direct_jump_data_target(isa: HostIsa) -> NativeTargetIdentity {
    NativeTargetIdentity::new(NativeTargetConfig {
        backend_id: String::from(DIRECT_JUMP_DATA_BACKEND_ID),
        backend_revision: DIRECT_JUMP_DATA_BACKEND_REVISION,
        host_isa: isa,
        host_os: HostOperatingSystem::Windows,
        native_abi_revision: NATIVE_REGION_ABI_REVISION,
        required_features: Vec::new(),
    })
}

fn direct_crazy_program() -> RegionEffectProgram {
    let before = ProfileMachineObservation {
        input_consumed: 0x0000_0001_2345_6789,
        output_len: 0x0000_0002_3456_789a,
        registers: ProfileRegisters {
            accumulator: 20,
            code_pointer: 5,
            data_pointer: 7,
        },
        termination: None,
    };
    let after = ProfileMachineObservation {
        registers: ProfileRegisters {
            accumulator: 2_391_494,
            code_pointer: 6,
            data_pointer: 8,
        },
        ..before
    };
    RegionEffectProgram {
        effects: vec![EffectOp {
            after,
            before,
            input: None,
            memory_delta: ProfileMemoryDelta {
                data: Some(ProfileMemoryWrite {
                    address: 7,
                    after: 2_391_494,
                    before: 10,
                }),
                encryption: Some(ProfileMemoryWrite {
                    address: 5,
                    after: 91,
                    before: 57,
                }),
            },
            output: None,
        }],
        format_version: EFFECT_IR_VERSION,
        memory_live_ins: vec![
            MemoryLiveIn { address: 5, value: 57 },
            MemoryLiveIn { address: 7, value: 10 },
        ],
        outcome: RunOutcome::BudgetExhausted { steps: 1 },
        profile_fingerprint: String::from(
            "malbolge-profile-v1:sha256:direct-crazy-fixture",
        ),
        profile_id: String::from("malbolge-2026.2"),
        profile_requirement: current_profile_requirement(),
        step_budget: 1,
    }
}

fn direct_crazy_target(isa: HostIsa) -> NativeTargetIdentity {
    NativeTargetIdentity::new(NativeTargetConfig {
        backend_id: String::from(DIRECT_CRAZY_BACKEND_ID),
        backend_revision: DIRECT_CRAZY_BACKEND_REVISION,
        host_isa: isa,
        host_os: HostOperatingSystem::Windows,
        native_abi_revision: NATIVE_REGION_ABI_REVISION,
        required_features: Vec::new(),
    })
}

fn direct_input_byte_program() -> RegionEffectProgram {
    let before = ProfileMachineObservation {
        input_consumed: 2,
        output_len: 0x0000_0002_3456_789a,
        registers: ProfileRegisters {
            accumulator: 0xdead_beef,
            code_pointer: 5,
            data_pointer: 7,
        },
        termination: None,
    };
    let after = ProfileMachineObservation {
        input_consumed: 3,
        registers: ProfileRegisters {
            accumulator: 0x41,
            code_pointer: 6,
            data_pointer: 8,
        },
        ..before
    };
    RegionEffectProgram {
        effects: vec![EffectOp {
            after,
            before,
            input: Some(TraceInput::Byte(0x41)),
            memory_delta: ProfileMemoryDelta {
                data: None,
                encryption: Some(ProfileMemoryWrite {
                    address: 5,
                    after: 57,
                    before: 94,
                }),
            },
            output: None,
        }],
        format_version: EFFECT_IR_VERSION,
        memory_live_ins: vec![MemoryLiveIn { address: 5, value: 94 }],
        outcome: RunOutcome::BudgetExhausted { steps: 1 },
        profile_fingerprint: String::from(
            "malbolge-profile-v1:sha256:direct-input-byte-fixture",
        ),
        profile_id: String::from("malbolge-2026.2"),
        profile_requirement: current_profile_requirement(),
        step_budget: 1,
    }
}

fn direct_input_eof_program() -> RegionEffectProgram {
    let before = ProfileMachineObservation {
        input_consumed: 2,
        output_len: 0x0000_0002_3456_789a,
        registers: ProfileRegisters {
            accumulator: 0xdead_beef,
            code_pointer: 5,
            data_pointer: 7,
        },
        termination: None,
    };
    let after = ProfileMachineObservation {
        registers: ProfileRegisters {
            accumulator: 4_782_968,
            code_pointer: 6,
            data_pointer: 8,
        },
        ..before
    };
    RegionEffectProgram {
        effects: vec![EffectOp {
            after,
            before,
            input: Some(TraceInput::EndOfInput),
            memory_delta: ProfileMemoryDelta {
                data: None,
                encryption: Some(ProfileMemoryWrite {
                    address: 5,
                    after: 57,
                    before: 94,
                }),
            },
            output: None,
        }],
        format_version: EFFECT_IR_VERSION,
        memory_live_ins: vec![MemoryLiveIn { address: 5, value: 94 }],
        outcome: RunOutcome::BudgetExhausted { steps: 1 },
        profile_fingerprint: String::from(
            "malbolge-profile-v1:sha256:direct-input-eof-fixture",
        ),
        profile_id: String::from("malbolge-2026.2"),
        profile_requirement: current_profile_requirement(),
        step_budget: 1,
    }
}

fn direct_input_target(isa: HostIsa) -> NativeTargetIdentity {
    NativeTargetIdentity::new(NativeTargetConfig {
        backend_id: String::from(DIRECT_INPUT_BACKEND_ID),
        backend_revision: DIRECT_INPUT_BACKEND_REVISION,
        host_isa: isa,
        host_os: HostOperatingSystem::Windows,
        native_abi_revision: NATIVE_REGION_ABI_REVISION,
        required_features: Vec::new(),
    })
}

fn direct_output_program() -> RegionEffectProgram {
    let before = ProfileMachineObservation {
        input_consumed: 0x0000_0001_2345_6789,
        output_len: 3,
        registers: ProfileRegisters {
            accumulator: 0xdead_bea8,
            code_pointer: 5,
            data_pointer: 7,
        },
        termination: None,
    };
    let after = ProfileMachineObservation {
        output_len: 4,
        registers: ProfileRegisters {
            accumulator: 0xdead_bea8,
            code_pointer: 6,
            data_pointer: 8,
        },
        ..before
    };
    RegionEffectProgram {
        effects: vec![EffectOp {
            after,
            before,
            input: None,
            memory_delta: ProfileMemoryDelta {
                data: None,
                encryption: Some(ProfileMemoryWrite {
                    address: 5,
                    after: 68,
                    before: 112,
                }),
            },
            output: Some(0xa8),
        }],
        format_version: EFFECT_IR_VERSION,
        memory_live_ins: vec![MemoryLiveIn { address: 5, value: 112 }],
        outcome: RunOutcome::BudgetExhausted { steps: 1 },
        profile_fingerprint: String::from(
            "malbolge-profile-v1:sha256:direct-output-fixture",
        ),
        profile_id: String::from("malbolge-2026.2"),
        profile_requirement: current_profile_requirement(),
        step_budget: 1,
    }
}

fn direct_output_target(isa: HostIsa) -> NativeTargetIdentity {
    NativeTargetIdentity::new(NativeTargetConfig {
        backend_id: String::from(DIRECT_OUTPUT_BACKEND_ID),
        backend_revision: DIRECT_OUTPUT_BACKEND_REVISION,
        host_isa: isa,
        host_os: HostOperatingSystem::Windows,
        native_abi_revision: NATIVE_REGION_ABI_REVISION,
        required_features: Vec::new(),
    })
}

fn direct_rotate_program() -> RegionEffectProgram {
    let before = ProfileMachineObservation {
        input_consumed: 0x0000_0001_2345_6789,
        output_len: 0x0000_0002_3456_789a,
        registers: ProfileRegisters {
            accumulator: 0xdead_beef,
            code_pointer: 5,
            data_pointer: 7,
        },
        termination: None,
    };
    let after = ProfileMachineObservation {
        registers: ProfileRegisters {
            accumulator: 1_594_326,
            code_pointer: 6,
            data_pointer: 8,
        },
        ..before
    };
    RegionEffectProgram {
        effects: vec![EffectOp {
            after,
            before,
            input: None,
            memory_delta: ProfileMemoryDelta {
                data: Some(ProfileMemoryWrite {
                    address: 7,
                    after: 1_594_326,
                    before: 10,
                }),
                encryption: Some(ProfileMemoryWrite {
                    address: 5,
                    after: 122,
                    before: 34,
                }),
            },
            output: None,
        }],
        format_version: EFFECT_IR_VERSION,
        memory_live_ins: vec![
            MemoryLiveIn { address: 5, value: 34 },
            MemoryLiveIn { address: 7, value: 10 },
        ],
        outcome: RunOutcome::BudgetExhausted { steps: 1 },
        profile_fingerprint: String::from(
            "malbolge-profile-v1:sha256:direct-rotate-fixture",
        ),
        profile_id: String::from("malbolge-2026.2"),
        profile_requirement: current_profile_requirement(),
        step_budget: 1,
    }
}

fn direct_rotate_target(isa: HostIsa) -> NativeTargetIdentity {
    NativeTargetIdentity::new(NativeTargetConfig {
        backend_id: String::from(DIRECT_ROTATE_BACKEND_ID),
        backend_revision: DIRECT_ROTATE_BACKEND_REVISION,
        host_isa: isa,
        host_os: HostOperatingSystem::Windows,
        native_abi_revision: NATIVE_REGION_ABI_REVISION,
        required_features: Vec::new(),
    })
}

fn direct_no_operation_program() -> RegionEffectProgram {
    let before = ProfileMachineObservation {
        input_consumed: 0x0000_0001_2345_6789,
        output_len: 0x0000_0002_3456_789a,
        registers: ProfileRegisters {
            accumulator: 0xdead_beef,
            code_pointer: 5,
            data_pointer: 7,
        },
        termination: None,
    };
    let after = ProfileMachineObservation {
        registers: ProfileRegisters {
            accumulator: 0xdead_beef,
            code_pointer: 6,
            data_pointer: 8,
        },
        ..before
    };
    RegionEffectProgram {
        effects: vec![EffectOp {
            after,
            before,
            input: None,
            memory_delta: ProfileMemoryDelta {
                data: None,
                encryption: Some(ProfileMemoryWrite {
                    address: 5,
                    after: 65,
                    before: 77,
                }),
            },
            output: None,
        }],
        format_version: EFFECT_IR_VERSION,
        memory_live_ins: vec![MemoryLiveIn { address: 5, value: 77 }],
        outcome: RunOutcome::BudgetExhausted { steps: 1 },
        profile_fingerprint: String::from(
            "malbolge-profile-v1:sha256:direct-no-operation-fixture",
        ),
        profile_id: String::from("malbolge-2026.2"),
        profile_requirement: current_profile_requirement(),
        step_budget: 1,
    }
}

fn direct_no_operation_target(isa: HostIsa) -> NativeTargetIdentity {
    NativeTargetIdentity::new(NativeTargetConfig {
        backend_id: String::from(DIRECT_NO_OPERATION_BACKEND_ID),
        backend_revision: DIRECT_NO_OPERATION_BACKEND_REVISION,
        host_isa: isa,
        host_os: HostOperatingSystem::Windows,
        native_abi_revision: NATIVE_REGION_ABI_REVISION,
        required_features: Vec::new(),
    })
}

fn direct_initial_halt_program() -> RegionEffectProgram {
    let before = ProfileMachineObservation {
        input_consumed: 0,
        output_len: 0,
        registers: ProfileRegisters::default(),
        termination: None,
    };
    let after = ProfileMachineObservation {
        termination: Some(Termination::HaltInstruction),
        ..before
    };
    RegionEffectProgram {
        effects: vec![EffectOp {
            after,
            before,
            input: None,
            memory_delta: ProfileMemoryDelta::default(),
            output: None,
        }],
        format_version: EFFECT_IR_VERSION,
        memory_live_ins: Vec::new(),
        outcome: RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 1,
        },
        profile_fingerprint: String::from(
            "malbolge-profile-v1:sha256:direct-initial-halt-fixture",
        ),
        profile_id: String::from("malbolge-2026.2"),
        profile_requirement: current_profile_requirement(),
        step_budget: 1,
    }
}

fn direct_initial_halt_target(isa: HostIsa) -> NativeTargetIdentity {
    NativeTargetIdentity::new(NativeTargetConfig {
        backend_id: String::from(DIRECT_INITIAL_HALT_BACKEND_ID),
        backend_revision: DIRECT_INITIAL_HALT_BACKEND_REVISION,
        host_isa: isa,
        host_os: HostOperatingSystem::Windows,
        native_abi_revision: NATIVE_REGION_ABI_REVISION,
        required_features: Vec::new(),
    })
}

fn assert_cached_direct_cycle(
    cache: &mut VerifiedDirectNativeCache,
    program: &RegionEffectProgram,
    expected_kind: DirectNativeKind,
    expected_len: usize,
) -> Result<(), String> {
    let inserted = select_cached_preflighted_execution_tier(
        program,
        safe_rust_profiled_capability(),
        DirectHost::new(HostOperatingSystem::Windows, HostIsa::X86_64),
        cache,
    )
    .map_err(|error| error.to_string())?;
    let CachedPreflightedExecutionTier::Direct {
        artifact: inserted_artifact,
        cache: DirectCacheDisposition::Inserted,
    } = inserted
    else {
        return Err(String::from("cache miss did not insert direct artifact"));
    };
    let uncached = select_verified_direct_native(
        program,
        safe_rust_profiled_capability(),
        HostOperatingSystem::Windows,
        HostIsa::X86_64,
    )
    .map_err(|error| error.to_string())?;
    if inserted_artifact.kind() != expected_kind
        || inserted_artifact.key() != uncached.key()
        || inserted_artifact.object() != uncached.object()
        || cache.len() != expected_len
    {
        return Err(String::from("inserted direct artifact identity drifted"));
    }

    let hit = select_cached_preflighted_execution_tier(
        program,
        safe_rust_profiled_capability(),
        DirectHost::new(HostOperatingSystem::Windows, HostIsa::X86_64),
        cache,
    )
    .map_err(|error| error.to_string())?;
    let CachedPreflightedExecutionTier::Direct {
        artifact: hit_artifact,
        cache: DirectCacheDisposition::Hit,
    } = hit
    else {
        return Err(String::from("exact direct cache key was not reused"));
    };
    if Arc::ptr_eq(&hit_artifact, &inserted_artifact)
        && cache.len() == expected_len
    {
        Ok(())
    } else {
        Err(String::from("direct cache hit cloned or changed artifact"))
    }
}

#[test]
fn cached_tier_planner_reuses_each_verified_template() -> Result<(), String> {
    let mut cache = VerifiedDirectNativeCache::default();
    if !cache.is_empty() {
        return Err(String::from("new verified direct cache was not empty"));
    }
    let cases = [
        (direct_initial_halt_program(), DirectNativeKind::InitialHalt),
        (
            direct_halt_registers_program(),
            DirectNativeKind::HaltRegisters,
        ),
        (direct_halt_fetch_program(), DirectNativeKind::HaltFetch),
        (
            direct_non_graphical_program(),
            DirectNativeKind::NonGraphical,
        ),
        (direct_jump_code_program(), DirectNativeKind::JumpCode),
        (direct_jump_data_program(), DirectNativeKind::JumpData),
        (direct_crazy_program(), DirectNativeKind::Crazy),
        (direct_rotate_program(), DirectNativeKind::Rotate),
        (direct_input_byte_program(), DirectNativeKind::Input),
        (direct_output_program(), DirectNativeKind::Output),
        (direct_no_operation_program(), DirectNativeKind::NoOperation),
        (native_program(), DirectNativeKind::Deopt),
    ];
    for (index, (program, kind)) in cases.iter().enumerate() {
        assert_cached_direct_cycle(&mut cache, program, *kind, index + 1)?;
    }
    cache.clear();
    if cache.is_empty() {
        Ok(())
    } else {
        Err(String::from(
            "verified direct cache clear retained artifacts",
        ))
    }
}

fn seed_verified_direct_cache(
    program: &RegionEffectProgram,
    cache: &mut VerifiedDirectNativeCache,
) -> Result<(), String> {
    let seeded = select_cached_preflighted_execution_tier(
        program,
        safe_rust_profiled_capability(),
        DirectHost::new(HostOperatingSystem::Windows, HostIsa::X86_64),
        cache,
    )
    .map_err(|error| error.to_string())?;
    if matches!(seeded, CachedPreflightedExecutionTier::Direct {
        cache: DirectCacheDisposition::Inserted,
        ..
    }) && cache.len() == 1
    {
        Ok(())
    } else {
        Err(String::from("failed to seed verified direct cache"))
    }
}

fn assert_cached_runtime_preflight(
    program: &RegionEffectProgram,
    cache: &mut VerifiedDirectNativeCache,
) -> Result<(), String> {
    let Err(error) = select_cached_preflighted_execution_tier(
        program,
        safe_rust_classic_capability(),
        DirectHost::new(HostOperatingSystem::Windows, HostIsa::X86_64),
        cache,
    ) else {
        return Err(String::from("cache hit bypassed runtime preflight"));
    };
    let DirectSelectionError::Profile(profile) = error else {
        return Err(String::from("cached runtime error changed category"));
    };
    if profile.kind() == ProfileRequirementErrorKind::RuntimeCapabilityMissing
        && cache.len() == 1
    {
        Ok(())
    } else {
        Err(String::from("cached path lost MALBOLGE-PROFILE-001"))
    }
}

fn assert_cached_host_selection(
    program: &RegionEffectProgram,
    cache: &mut VerifiedDirectNativeCache,
) -> Result<(), String> {
    let tier = select_cached_preflighted_execution_tier(
        program,
        safe_rust_profiled_capability(),
        DirectHost::new(HostOperatingSystem::Linux, HostIsa::X86_64),
        cache,
    )
    .map_err(|error| error.to_string())?;
    if tier == CachedPreflightedExecutionTier::Interpreter && cache.len() == 1 {
        Ok(())
    } else {
        Err(String::from("cache hit bypassed host-format selection"))
    }
}

fn assert_cached_capacity_preflight(
    program: &RegionEffectProgram,
    cache: &mut VerifiedDirectNativeCache,
) -> Result<(), String> {
    let mut overflow = program.clone();
    let address = current_profile().memory_words();
    let effect = overflow
        .effects
        .first_mut()
        .ok_or_else(|| String::from("initial-halt fixture has no effect"))?;
    effect.before.registers.code_pointer = address;
    effect.after.registers.code_pointer = address;
    let Err(error) = select_cached_preflighted_execution_tier(
        &overflow,
        safe_rust_profiled_capability(),
        DirectHost::new(HostOperatingSystem::Windows, HostIsa::X86_64),
        cache,
    ) else {
        return Err(String::from("cache lookup bypassed capacity preflight"));
    };
    let DirectSelectionError::Profile(profile) = error else {
        return Err(String::from("cached capacity error changed category"));
    };
    if profile.kind() == ProfileRequirementErrorKind::ProfileCapacityExceeded
        && cache.len() == 1
    {
        Ok(())
    } else {
        Err(String::from("cached path lost MALBOLGE-PROFILE-002"))
    }
}

fn insert_cached_direct_for_isa(
    cache: &mut VerifiedDirectNativeCache,
    program: &RegionEffectProgram,
    isa: HostIsa,
) -> Result<Arc<execution_native::VerifiedDirectNativeArtifact>, String> {
    let selected = select_cached_preflighted_execution_tier(
        program,
        safe_rust_profiled_capability(),
        DirectHost::new(HostOperatingSystem::Windows, isa),
        cache,
    )
    .map_err(|error| error.to_string())?;
    let CachedPreflightedExecutionTier::Direct {
        artifact,
        cache: DirectCacheDisposition::Inserted,
    } = selected
    else {
        return Err(String::from("direct cache fixture was not inserted"));
    };
    Ok(artifact)
}

fn hit_cached_direct_for_isa(
    cache: &mut VerifiedDirectNativeCache,
    program: &RegionEffectProgram,
    isa: HostIsa,
) -> Result<Arc<execution_native::VerifiedDirectNativeArtifact>, String> {
    let selected = select_cached_preflighted_execution_tier(
        program,
        safe_rust_profiled_capability(),
        DirectHost::new(HostOperatingSystem::Windows, isa),
        cache,
    )
    .map_err(|error| error.to_string())?;
    let CachedPreflightedExecutionTier::Direct {
        artifact,
        cache: DirectCacheDisposition::Hit,
    } = selected
    else {
        return Err(String::from("direct cache fixture was not reused"));
    };
    Ok(artifact)
}

#[test]
fn verified_direct_cache_invalidation_is_exact_and_nonrevoking()
-> Result<(), String> {
    let program = direct_initial_halt_program();
    let mut cache = VerifiedDirectNativeCache::default();
    let first = select_cached_preflighted_execution_tier(
        &program,
        safe_rust_profiled_capability(),
        DirectHost::new(HostOperatingSystem::Windows, HostIsa::X86_64),
        &mut cache,
    )
    .map_err(|error| error.to_string())?;
    let CachedPreflightedExecutionTier::Direct {
        artifact: first_artifact,
        cache: DirectCacheDisposition::Inserted,
    } = first
    else {
        return Err(String::from("failed to seed invalidation fixture"));
    };
    if !cache.invalidate(&first_artifact)
        || !cache.is_empty()
        || cache.invalidate(&first_artifact)
        || first_artifact.object().is_empty()
    {
        return Err(String::from(
            "exact invalidation violated cache ownership",
        ));
    }
    let second = select_cached_preflighted_execution_tier(
        &program,
        safe_rust_profiled_capability(),
        DirectHost::new(HostOperatingSystem::Windows, HostIsa::X86_64),
        &mut cache,
    )
    .map_err(|error| error.to_string())?;
    let CachedPreflightedExecutionTier::Direct {
        artifact: second_artifact,
        cache: DirectCacheDisposition::Inserted,
    } = second
    else {
        return Err(String::from("invalidated key did not reinsert"));
    };
    if Arc::ptr_eq(&first_artifact, &second_artifact)
        || first_artifact.key() != second_artifact.key()
        || first_artifact.object() != second_artifact.object()
        || !cache.invalidate(&first_artifact)
        || !cache.is_empty()
    {
        Err(String::from("invalidation changed exact-key semantics"))
    } else {
        Ok(())
    }
}

#[test]
fn verified_cache_invalidates_program_variants() -> Result<(), String> {
    let program = direct_initial_halt_program();
    let survivor = native_program();
    let mut cache = VerifiedDirectNativeCache::default();
    let x86 =
        insert_cached_direct_for_isa(&mut cache, &program, HostIsa::X86_64)?;
    let arm =
        insert_cached_direct_for_isa(&mut cache, &program, HostIsa::AArch64)?;
    let survivor_artifact =
        insert_cached_direct_for_isa(&mut cache, &survivor, HostIsa::X86_64)?;
    let mut invalid = program.clone();
    invalid.profile_requirement.memory_words = 0;
    if cache.invalidate_program(&invalid)
        != Err(NativeIdentityError::ProfileCapacity)
        || cache.len() != 3
    {
        return Err(String::from("invalid program mutated verified cache"));
    }
    if cache
        .invalidate_program(&program)
        .map_err(|error| format!("{error:?}"))?
        != 2
        || cache
            .invalidate_program(&program)
            .map_err(|error| format!("{error:?}"))?
            != 0
        || cache.len() != 1
        || x86.object().is_empty()
        || arm.object().is_empty()
    {
        return Err(String::from("program invalidation lost exact variants"));
    }
    let new_x86 =
        insert_cached_direct_for_isa(&mut cache, &program, HostIsa::X86_64)?;
    let new_arm =
        insert_cached_direct_for_isa(&mut cache, &program, HostIsa::AArch64)?;
    let survivor_plan = select_cached_preflighted_execution_tier(
        &survivor,
        safe_rust_profiled_capability(),
        DirectHost::new(HostOperatingSystem::Windows, HostIsa::X86_64),
        &mut cache,
    )
    .map_err(|error| error.to_string())?;
    let CachedPreflightedExecutionTier::Direct {
        artifact: survivor_hit,
        cache: DirectCacheDisposition::Hit,
    } = survivor_plan
    else {
        return Err(String::from("unrelated program was invalidated"));
    };
    if Arc::ptr_eq(&x86, &new_x86)
        || Arc::ptr_eq(&arm, &new_arm)
        || x86.key() != new_x86.key()
        || arm.key() != new_arm.key()
        || !Arc::ptr_eq(&survivor_artifact, &survivor_hit)
        || cache.len() != 3
    {
        Err(String::from("program invalidation changed cache semantics"))
    } else {
        Ok(())
    }
}

#[test]
fn verified_cache_invalidates_exact_target_regions() -> Result<(), String> {
    let program = native_program();
    let mut variant = program.clone();
    variant.profile_fingerprint.push('x');
    let halt = direct_initial_halt_program();
    let mut cache = VerifiedDirectNativeCache::default();
    let x86 =
        insert_cached_direct_for_isa(&mut cache, &program, HostIsa::X86_64)?;
    let x86_variant =
        insert_cached_direct_for_isa(&mut cache, &variant, HostIsa::X86_64)?;
    let arm =
        insert_cached_direct_for_isa(&mut cache, &program, HostIsa::AArch64)?;
    let halt_x86 =
        insert_cached_direct_for_isa(&mut cache, &halt, HostIsa::X86_64)?;
    if x86.kind() != DirectNativeKind::Deopt
        || x86_variant.kind() != DirectNativeKind::Deopt
        || halt_x86.kind() != DirectNativeKind::InitialHalt
        || cache.invalidate_target(&x86) != 2
        || cache.invalidate_target(&x86_variant) != 0
        || cache.len() != 2
        || x86.object().is_empty()
        || x86_variant.object().is_empty()
    {
        return Err(String::from(
            "verified target invalidation crossed identity",
        ));
    }
    let arm_hit =
        hit_cached_direct_for_isa(&mut cache, &program, HostIsa::AArch64)?;
    let halt_hit =
        hit_cached_direct_for_isa(&mut cache, &halt, HostIsa::X86_64)?;
    let new_x86 =
        insert_cached_direct_for_isa(&mut cache, &program, HostIsa::X86_64)?;
    let new_variant =
        insert_cached_direct_for_isa(&mut cache, &variant, HostIsa::X86_64)?;
    if !Arc::ptr_eq(&arm, &arm_hit)
        || !Arc::ptr_eq(&halt_x86, &halt_hit)
        || Arc::ptr_eq(&x86, &new_x86)
        || Arc::ptr_eq(&x86_variant, &new_variant)
        || x86.key() != new_x86.key()
        || x86_variant.key() != new_variant.key()
        || cache.len() != 4
    {
        Err(String::from("target invalidation changed reuse semantics"))
    } else {
        Ok(())
    }
}

#[test]
fn cached_tier_planner_preflights_before_lookup() -> Result<(), String> {
    let program = direct_initial_halt_program();
    let mut cache = VerifiedDirectNativeCache::default();
    seed_verified_direct_cache(&program, &mut cache)?;
    assert_cached_runtime_preflight(&program, &mut cache)?;
    assert_cached_host_selection(&program, &mut cache)?;
    assert_cached_capacity_preflight(&program, &mut cache)
}

#[test]
fn tier_planner_uses_interpreter_only_for_missing_direct_format()
-> Result<(), String> {
    let direct = select_preflighted_execution_tier(
        &direct_initial_halt_program(),
        safe_rust_profiled_capability(),
        HostOperatingSystem::Windows,
        HostIsa::X86_64,
    )
    .map_err(|error| error.to_string())?;
    let PreflightedExecutionTier::Direct(artifact) = direct else {
        return Err(String::from("Windows direct tier selected interpreter"));
    };
    if artifact.kind() != DirectNativeKind::InitialHalt {
        return Err(String::from("tier planner changed direct specialization"));
    }
    for host_os in [HostOperatingSystem::Linux, HostOperatingSystem::MacOs] {
        let selected = select_preflighted_execution_tier(
            &native_program(),
            safe_rust_profiled_capability(),
            host_os,
            HostIsa::X86_64,
        )
        .map_err(|error| error.to_string())?;
        if selected != PreflightedExecutionTier::Interpreter {
            return Err(format!("{host_os:?} did not select interpreter"));
        }
    }
    Ok(())
}

#[test]
fn tier_planner_preserves_profile_errors_before_fallback() -> Result<(), String>
{
    let current = direct_initial_halt_program();
    let Err(runtime_error) = select_preflighted_execution_tier(
        &current,
        safe_rust_classic_capability(),
        HostOperatingSystem::Linux,
        HostIsa::X86_64,
    ) else {
        return Err(String::from("runtime mismatch degraded to interpreter"));
    };
    let DirectSelectionError::Profile(runtime_profile) = runtime_error else {
        return Err(format!(
            "runtime mismatch changed category: {runtime_error}"
        ));
    };
    if runtime_profile.kind()
        != ProfileRequirementErrorKind::RuntimeCapabilityMissing
    {
        return Err(String::from("runtime mismatch lost MALBOLGE-PROFILE-001"));
    }

    let mut overflow = direct_initial_halt_program();
    let address = current_profile().memory_words();
    let effect = overflow
        .effects
        .first_mut()
        .ok_or_else(|| String::from("initial-halt fixture has no effect"))?;
    effect.before.registers.data_pointer = address;
    effect.after.registers.data_pointer = address;
    let Err(capacity_error) = select_preflighted_execution_tier(
        &overflow,
        safe_rust_profiled_capability(),
        HostOperatingSystem::Linux,
        HostIsa::X86_64,
    ) else {
        return Err(String::from("capacity mismatch degraded to interpreter"));
    };
    let DirectSelectionError::Profile(capacity_profile) = capacity_error else {
        return Err(format!(
            "capacity mismatch changed category: {capacity_error}"
        ));
    };
    if capacity_profile.kind()
        == ProfileRequirementErrorKind::ProfileCapacityExceeded
    {
        Ok(())
    } else {
        Err(String::from("capacity mismatch lost MALBOLGE-PROFILE-002"))
    }
}

fn selected_direct_triple(
    program: &RegionEffectProgram,
    isa: HostIsa,
    kind: DirectNativeKind,
    backend_id: &str,
) -> Result<&'static str, String> {
    let selected = select_verified_direct_native(
        program,
        safe_rust_profiled_capability(),
        HostOperatingSystem::Windows,
        isa,
    )
    .map_err(|error| error.to_string())?;
    if selected.kind() != kind
        || selected.key().target().backend_id() != backend_id
        || selected.object().is_empty()
    {
        Err(format!("direct selector missed {backend_id}"))
    } else {
        Ok(selected.target_triple())
    }
}

fn direct_selection_cases() -> Vec<DirectSelectionCase> {
    let mut cases = direct_selection_terminal_cases();
    cases.extend(direct_selection_effect_cases());
    cases
}

fn direct_selection_terminal_cases() -> Vec<DirectSelectionCase> {
    vec![
        (
            direct_initial_halt_program(),
            DirectNativeKind::InitialHalt,
            DIRECT_INITIAL_HALT_BACKEND_ID,
        ),
        (
            direct_halt_registers_program(),
            DirectNativeKind::HaltRegisters,
            DIRECT_HALT_REGISTERS_BACKEND_ID,
        ),
        (
            direct_halt_fetch_program(),
            DirectNativeKind::HaltFetch,
            DIRECT_HALT_FETCH_BACKEND_ID,
        ),
        (
            direct_non_graphical_program(),
            DirectNativeKind::NonGraphical,
            DIRECT_NON_GRAPHICAL_BACKEND_ID,
        ),
    ]
}

fn direct_selection_effect_cases() -> Vec<DirectSelectionCase> {
    vec![
        (
            direct_jump_code_program(),
            DirectNativeKind::JumpCode,
            DIRECT_JUMP_CODE_BACKEND_ID,
        ),
        (
            direct_jump_data_program(),
            DirectNativeKind::JumpData,
            DIRECT_JUMP_DATA_BACKEND_ID,
        ),
        (
            direct_crazy_program(),
            DirectNativeKind::Crazy,
            DIRECT_CRAZY_BACKEND_ID,
        ),
        (
            direct_rotate_program(),
            DirectNativeKind::Rotate,
            DIRECT_ROTATE_BACKEND_ID,
        ),
        (
            direct_input_byte_program(),
            DirectNativeKind::Input,
            DIRECT_INPUT_BACKEND_ID,
        ),
        (
            direct_output_program(),
            DirectNativeKind::Output,
            DIRECT_OUTPUT_BACKEND_ID,
        ),
        (
            direct_no_operation_program(),
            DirectNativeKind::NoOperation,
            DIRECT_NO_OPERATION_BACKEND_ID,
        ),
        (
            native_program(),
            DirectNativeKind::Deopt,
            DIRECT_DEOPT_BACKEND_ID,
        ),
    ]
}

#[test]
fn direct_selector_chooses_fast_path_or_verified_deopt_deterministically()
-> Result<(), String> {
    for isa in [HostIsa::X86_64, HostIsa::AArch64] {
        let mut expected = None;
        for (program, kind, backend_id) in direct_selection_cases() {
            let triple =
                selected_direct_triple(&program, isa, kind, backend_id)?;
            if let Some(previous) = expected
                && previous != triple
            {
                return Err(String::from("direct tier changed target triple"));
            }
            expected = Some(triple);
        }
    }
    Ok(())
}

#[test]
fn direct_selector_prioritizes_program_capacity() -> Result<(), String> {
    let mut program = direct_initial_halt_program();
    let overflow_address = current_profile().memory_words();
    let effect = program
        .effects
        .first_mut()
        .ok_or_else(|| String::from("initial-halt fixture has no effect"))?;
    effect.before.registers.code_pointer = overflow_address;
    effect.after.registers.code_pointer = overflow_address;

    let Err(error) = select_verified_direct_native(
        &program,
        safe_rust_classic_capability(),
        HostOperatingSystem::Linux,
        HostIsa::X86_64,
    ) else {
        return Err(String::from("profile-capacity overflow was selected"));
    };
    let DirectSelectionError::Profile(profile_error) = error else {
        return Err(format!("program capacity lost precedence: {error}"));
    };
    if profile_error.kind()
        != ProfileRequirementErrorKind::ProfileCapacityExceeded
    {
        return Err(format!("program capacity category: {profile_error}"));
    }
    let expected = concat!(
        "MALBOLGE-PROFILE-002 profile=malbolge-2026.2 version=2026.2 ",
        "constraint=profile-capacity-ceiling required_memory_words=4782970 ",
        "profile_memory_words=4782969"
    );
    if profile_error.to_string() == expected {
        Ok(())
    } else {
        Err(format!("program capacity diagnostic: {profile_error}"))
    }
}

#[test]
fn direct_selector_prioritizes_profile_preflight() -> Result<(), String> {
    let program = direct_initial_halt_program();
    let Err(error) = select_verified_direct_native(
        &program,
        safe_rust_classic_capability(),
        HostOperatingSystem::Linux,
        HostIsa::X86_64,
    ) else {
        return Err(String::from(
            "unsupported profile reached direct native construction",
        ));
    };
    let DirectSelectionError::Profile(profile_error) = error else {
        return Err(format!(
            "profile preflight lost precedence to direct selection: {error}"
        ));
    };
    let current = current_profile();
    let Err(canonical) = preflight_profile(
        current,
        current.memory_words(),
        safe_rust_classic_capability(),
    ) else {
        return Err(String::from("canonical current profile was admitted"));
    };
    if format!("{profile_error}") == format!("{canonical}") {
        Ok(())
    } else {
        Err(String::from(
            "direct selector changed shared profile diagnostic",
        ))
    }
}

#[test]
fn direct_selector_rejects_unsupported_host_format_without_fallback()
-> Result<(), String> {
    for host_os in [HostOperatingSystem::Linux, HostOperatingSystem::MacOs] {
        if select_verified_direct_native(
            &native_program(),
            safe_rust_profiled_capability(),
            host_os,
            HostIsa::X86_64,
        ) != Err(DirectSelectionError::TargetFormat)
        {
            return Err(format!(
                "unsupported direct host {host_os:?} was admitted"
            ));
        }
    }
    Ok(())
}

#[test]
fn direct_halt_register_objects_are_byte_exact_and_semantically_admitted()
-> Result<(), String> {
    let cases = [
        (
            HostIsa::X86_64,
            include_str!(
                "execution/fixtures/native-halt-registers-x86_64-coff.hex"
            ),
        ),
        (
            HostIsa::AArch64,
            include_str!(
                "execution/fixtures/native-halt-registers-aarch64-coff.hex"
            ),
        ),
    ];
    let program = direct_halt_registers_program();
    for (isa, fixture) in cases {
        let artifact = emit_direct_halt_registers_coff(
            &program,
            direct_halt_registers_target(isa),
        )
        .map_err(|error| error.to_string())?;
        if artifact.object() != decode_hex_fixture(fixture)? {
            return Err(format!(
                "direct register-halt fixture mismatch for {isa:?}"
            ));
        }
        let verified = verify_direct_halt_registers(&artifact, &program)
            .map_err(|error| error.to_string())?;
        if verified.key() != artifact.key()
            || verified.object() != artifact.object()
            || verified.target_triple() != artifact.target_triple()
        {
            return Err(String::from(
                "verified register-halt identity drifted",
            ));
        }
    }
    Ok(())
}

#[test]
fn direct_halt_observation_revision_rejects_v4_identity() -> Result<(), String>
{
    let obsolete = NativeTargetIdentity::new(NativeTargetConfig {
        backend_id: String::from(DIRECT_HALT_REGISTERS_BACKEND_ID),
        backend_revision: 4,
        host_isa: HostIsa::X86_64,
        host_os: HostOperatingSystem::Windows,
        native_abi_revision: NATIVE_REGION_ABI_REVISION,
        required_features: Vec::new(),
    });
    if emit_direct_halt_registers_coff(
        &direct_halt_registers_program(),
        obsolete,
    ) == Err(DirectHaltRegistersError::TargetBackend)
    {
        Ok(())
    } else {
        Err(String::from("historical halt revision was admitted"))
    }
}

fn assert_halt_counter_identity_rejected(
    artifact: &UntrustedNativeObjectArtifact,
    program: &RegionEffectProgram,
) -> Result<(), String> {
    let mut mismatch = program.clone();
    let effect = mismatch.effects.first_mut().ok_or_else(|| {
        String::from("register-halt counter fixture lost effect")
    })?;
    effect.before.input_consumed =
        effect.before.input_consumed.saturating_add(1);
    effect.after.input_consumed = effect.after.input_consumed.saturating_add(1);
    if verify_direct_halt_registers(artifact, &mismatch)
        == Err(DirectHaltRegistersError::ProgramShape)
    {
        Ok(())
    } else {
        Err(String::from("counter-mismatched halt object was admitted"))
    }
}

#[test]
fn direct_halt_registers_rejects_ir_and_opcode_tampering() -> Result<(), String>
{
    let program = direct_halt_registers_program();
    let artifact = emit_direct_halt_registers_coff(
        &program,
        direct_halt_registers_target(HostIsa::X86_64),
    )
    .map_err(|error| error.to_string())?;
    let mut mutated_object = artifact.object().to_vec();
    let immediate = 0x1234_5678u32.to_le_bytes();
    let offset = mutated_object
        .windows(immediate.len())
        .position(|window| window == immediate)
        .ok_or_else(|| {
            String::from("register-halt accumulator immediate missing")
        })?;
    let first = mutated_object.get_mut(offset).ok_or_else(|| {
        String::from("register-halt immediate offset invalid")
    })?;
    *first ^= 1;
    let tampered = UntrustedNativeObjectArtifact::from_emitter_output(
        artifact.key().clone(),
        mutated_object,
        artifact.target_triple(),
    );
    let _structural = structurally_admit_coff(&tampered).map_err(|error| {
        format!("tampered register-halt structure: {error}")
    })?;
    if verify_direct_halt_registers(&tampered, &program)
        != Err(DirectHaltRegistersError::ObjectBytes)
    {
        return Err(String::from("tampered register-halt object was admitted"));
    }

    assert_halt_counter_identity_rejected(&artifact, &program)?;

    let mut with_output = program;
    let first_effect = with_output
        .effects
        .first_mut()
        .ok_or_else(|| String::from("register-halt fixture lost effect"))?;
    first_effect.output = Some(0x41);
    if emit_direct_halt_registers_coff(
        &with_output,
        direct_halt_registers_target(HostIsa::X86_64),
    ) != Err(DirectHaltRegistersError::ProgramShape)
    {
        return Err(String::from("register-halt output mutation was admitted"));
    }
    Ok(())
}

#[test]
fn direct_halt_fetch_objects_are_byte_exact_and_semantically_admitted()
-> Result<(), String> {
    let cases = [
        (
            HostIsa::X86_64,
            include_str!(
                "execution/fixtures/native-halt-fetch-x86_64-coff.hex"
            ),
        ),
        (
            HostIsa::AArch64,
            include_str!(
                "execution/fixtures/native-halt-fetch-aarch64-coff.hex"
            ),
        ),
    ];
    let program = direct_halt_fetch_program();
    for (isa, fixture) in cases {
        let artifact = emit_direct_halt_fetch_coff(
            &program,
            direct_halt_fetch_target(isa),
        )
        .map_err(|error| error.to_string())?;
        if artifact.object() != decode_hex_fixture(fixture)? {
            return Err(format!(
                "direct halt-fetch fixture mismatch for {isa:?}"
            ));
        }
        let verified = verify_direct_halt_fetch(&artifact, &program)
            .map_err(|error| error.to_string())?;
        if verified.key() != artifact.key()
            || verified.object() != artifact.object()
            || verified.target_triple() != artifact.target_triple()
        {
            return Err(String::from("verified halt-fetch identity drifted"));
        }
    }
    Ok(())
}

fn assert_halt_fetch_shape_rejections(
    program: &RegionEffectProgram,
) -> Result<(), String> {
    let mut wrong_decode = program.clone();
    let decoded_live_in = wrong_decode
        .memory_live_ins
        .first_mut()
        .ok_or_else(|| String::from("halt-fetch fixture lost live-in"))?;
    decoded_live_in.value = 77;
    if emit_direct_halt_fetch_coff(
        &wrong_decode,
        direct_halt_fetch_target(HostIsa::X86_64),
    ) != Err(DirectHaltFetchError::ProgramShape)
    {
        return Err(String::from("non-halt graphical live-in was admitted"));
    }
    let mut wrong_address = program.clone();
    let address_live_in =
        wrong_address.memory_live_ins.first_mut().ok_or_else(|| {
            String::from("halt-fetch fixture lost address live-in")
        })?;
    address_live_in.address = 6;
    if emit_direct_halt_fetch_coff(
        &wrong_address,
        direct_halt_fetch_target(HostIsa::X86_64),
    ) == Err(DirectHaltFetchError::ProgramShape)
    {
        Ok(())
    } else {
        Err(String::from("wrong halt-fetch live-in was admitted"))
    }
}

fn assert_halt_fetch_revision_rejected(
    program: &RegionEffectProgram,
) -> Result<(), String> {
    let obsolete = NativeTargetIdentity::new(NativeTargetConfig {
        backend_id: String::from(DIRECT_HALT_FETCH_BACKEND_ID),
        backend_revision: 1,
        host_isa: HostIsa::X86_64,
        host_os: HostOperatingSystem::Windows,
        native_abi_revision: NATIVE_REGION_ABI_REVISION,
        required_features: Vec::new(),
    });
    if emit_direct_halt_fetch_coff(program, obsolete)
        == Err(DirectHaltFetchError::TargetBackend)
    {
        Ok(())
    } else {
        Err(String::from("obsolete halt-fetch revision was admitted"))
    }
}

#[test]
fn direct_halt_fetch_rejects_ir_opcode_and_revision_tampering()
-> Result<(), String> {
    let program = direct_halt_fetch_program();
    let artifact = emit_direct_halt_fetch_coff(
        &program,
        direct_halt_fetch_target(HostIsa::X86_64),
    )
    .map_err(|error| error.to_string())?;
    let mut mutated_object = artifact.object().to_vec();
    let commit = [0xc6u8, 0x41, 0x4c, 0x01];
    let offset = mutated_object
        .windows(commit.len())
        .position(|window| window == commit)
        .ok_or_else(|| String::from("halt-fetch commit opcode missing"))?;
    let immediate = mutated_object
        .get_mut(offset.saturating_add(3))
        .ok_or_else(|| String::from("halt-fetch commit immediate missing"))?;
    *immediate = 2;
    let tampered = UntrustedNativeObjectArtifact::from_emitter_output(
        artifact.key().clone(),
        mutated_object,
        artifact.target_triple(),
    );
    let _structural = structurally_admit_coff(&tampered)
        .map_err(|error| format!("tampered halt-fetch structure: {error}"))?;
    if verify_direct_halt_fetch(&tampered, &program)
        != Err(DirectHaltFetchError::ObjectBytes)
    {
        return Err(String::from("tampered halt-fetch object was admitted"));
    }
    assert_halt_fetch_shape_rejections(&program)?;
    assert_halt_fetch_revision_rejected(&program)
}

#[test]
fn direct_jump_code_objects_are_byte_exact_and_semantically_admitted()
-> Result<(), String> {
    let cases = [
        (
            HostIsa::X86_64,
            include_str!("execution/fixtures/native-jump-code-x86_64-coff.hex"),
        ),
        (
            HostIsa::AArch64,
            include_str!(
                "execution/fixtures/native-jump-code-aarch64-coff.hex"
            ),
        ),
    ];
    let program = direct_jump_code_program();
    for (isa, fixture) in cases {
        let artifact =
            emit_direct_jump_code_coff(&program, direct_jump_code_target(isa))
                .map_err(|error| error.to_string())?;
        if artifact.object() != decode_hex_fixture(fixture)? {
            return Err(format!(
                "direct jump-code fixture mismatch for {isa:?}"
            ));
        }
        let verified = verify_direct_jump_code(&artifact, &program)
            .map_err(|error| error.to_string())?;
        if verified.key() != artifact.key()
            || verified.object() != artifact.object()
            || verified.target_triple() != artifact.target_triple()
        {
            return Err(String::from("verified jump-code identity drifted"));
        }
    }
    Ok(())
}

fn assert_jump_code_live_in_rejections(
    program: &RegionEffectProgram,
) -> Result<(), String> {
    let mut wrong_decode = program.clone();
    wrong_decode
        .memory_live_ins
        .first_mut()
        .ok_or_else(|| String::from("jump-code fixture lost code live-in"))?
        .value = 35;
    if emit_direct_jump_code_coff(
        &wrong_decode,
        direct_jump_code_target(HostIsa::X86_64),
    ) != Err(DirectJumpCodeError::ProgramShape)
    {
        return Err(String::from("jump-data decode was admitted as jump-code"));
    }

    let mut wrong_target = program.clone();
    wrong_target
        .memory_live_ins
        .get_mut(1)
        .ok_or_else(|| String::from("jump-code fixture lost data live-in"))?
        .value = 12;
    if emit_direct_jump_code_coff(
        &wrong_target,
        direct_jump_code_target(HostIsa::X86_64),
    ) != Err(DirectJumpCodeError::ProgramShape)
    {
        return Err(String::from("wrong jump-code target was admitted"));
    }

    let mut wrong_encryption = program.clone();
    wrong_encryption
        .memory_live_ins
        .get_mut(2)
        .ok_or_else(|| {
            String::from("jump-code fixture lost encryption live-in")
        })?
        .value = 69;
    if emit_direct_jump_code_coff(
        &wrong_encryption,
        direct_jump_code_target(HostIsa::X86_64),
    ) == Err(DirectJumpCodeError::ProgramShape)
    {
        Ok(())
    } else {
        Err(String::from(
            "wrong jump-code encryption live-in was admitted",
        ))
    }
}

fn assert_jump_code_transition_rejections(
    program: &RegionEffectProgram,
) -> Result<(), String> {
    let mut aliased = program.clone();
    aliased
        .memory_live_ins
        .get_mut(1)
        .ok_or_else(|| String::from("jump-code fixture lost data live-in"))?
        .value = 5;
    if emit_direct_jump_code_coff(
        &aliased,
        direct_jump_code_target(HostIsa::X86_64),
    ) != Err(DirectJumpCodeError::ProgramShape)
    {
        return Err(String::from("aliased jump-code was admitted"));
    }

    let mut wrong_exit = program.clone();
    wrong_exit
        .effects
        .first_mut()
        .ok_or_else(|| String::from("jump-code fixture lost effect"))?
        .after
        .registers
        .code_pointer = 13;
    if emit_direct_jump_code_coff(
        &wrong_exit,
        direct_jump_code_target(HostIsa::X86_64),
    ) != Err(DirectJumpCodeError::ProgramShape)
    {
        return Err(String::from("wrong jump-code exit was admitted"));
    }

    let mut wrong_delta = program.clone();
    wrong_delta
        .effects
        .first_mut()
        .and_then(|operation| operation.memory_delta.encryption.as_mut())
        .ok_or_else(|| String::from("jump-code fixture lost encryption"))?
        .after = 34;
    if emit_direct_jump_code_coff(
        &wrong_delta,
        direct_jump_code_target(HostIsa::X86_64),
    ) == Err(DirectJumpCodeError::ProgramShape)
    {
        Ok(())
    } else {
        Err(String::from("wrong jump-code encryption was admitted"))
    }
}

fn assert_jump_code_revision_rejected(
    program: &RegionEffectProgram,
) -> Result<(), String> {
    let obsolete = NativeTargetIdentity::new(NativeTargetConfig {
        backend_id: String::from(DIRECT_JUMP_CODE_BACKEND_ID),
        backend_revision: 0,
        host_isa: HostIsa::X86_64,
        host_os: HostOperatingSystem::Windows,
        native_abi_revision: NATIVE_REGION_ABI_REVISION,
        required_features: Vec::new(),
    });
    if emit_direct_jump_code_coff(program, obsolete)
        == Err(DirectJumpCodeError::TargetBackend)
    {
        Ok(())
    } else {
        Err(String::from("obsolete jump-code revision was admitted"))
    }
}

#[test]
fn direct_jump_code_rejects_ir_opcode_and_revision_tampering()
-> Result<(), String> {
    let program = direct_jump_code_program();
    let artifact = emit_direct_jump_code_coff(
        &program,
        direct_jump_code_target(HostIsa::X86_64),
    )
    .map_err(|error| error.to_string())?;
    let mut mutated_object = artifact.object().to_vec();
    let commit = [0xc7u8, 0x82, 0x2c, 0x00, 0x00, 0x00, 0x21, 0x00, 0x00, 0x00];
    let offset = mutated_object
        .windows(commit.len())
        .position(|window| window == commit)
        .ok_or_else(|| String::from("jump-code commit opcode missing"))?;
    let immediate = mutated_object
        .get_mut(offset.saturating_add(6))
        .ok_or_else(|| String::from("jump-code commit immediate missing"))?;
    *immediate = 34;
    let tampered = UntrustedNativeObjectArtifact::from_emitter_output(
        artifact.key().clone(),
        mutated_object,
        artifact.target_triple(),
    );
    let _structural = structurally_admit_coff(&tampered)
        .map_err(|error| format!("tampered jump-code structure: {error}"))?;
    if verify_direct_jump_code(&tampered, &program)
        != Err(DirectJumpCodeError::ObjectBytes)
    {
        return Err(String::from("tampered jump-code object was admitted"));
    }
    assert_jump_code_live_in_rejections(&program)?;
    assert_jump_code_transition_rejections(&program)?;
    assert_jump_code_revision_rejected(&program)
}

#[test]
fn direct_jump_data_objects_are_byte_exact_and_semantically_admitted()
-> Result<(), String> {
    let cases = [
        (
            HostIsa::X86_64,
            include_str!("execution/fixtures/native-jump-data-x86_64-coff.hex"),
        ),
        (
            HostIsa::AArch64,
            include_str!(
                "execution/fixtures/native-jump-data-aarch64-coff.hex"
            ),
        ),
    ];
    let program = direct_jump_data_program();
    for (isa, fixture) in cases {
        let artifact =
            emit_direct_jump_data_coff(&program, direct_jump_data_target(isa))
                .map_err(|error| error.to_string())?;
        if artifact.object() != decode_hex_fixture(fixture)? {
            return Err(format!(
                "direct jump-data fixture mismatch for {isa:?}"
            ));
        }
        let verified = verify_direct_jump_data(&artifact, &program)
            .map_err(|error| error.to_string())?;
        if verified.key() != artifact.key()
            || verified.object() != artifact.object()
            || verified.target_triple() != artifact.target_triple()
        {
            return Err(String::from("verified jump-data identity drifted"));
        }
    }
    Ok(())
}

fn assert_jump_data_shape_rejections(
    program: &RegionEffectProgram,
) -> Result<(), String> {
    let mut wrong_decode = program.clone();
    wrong_decode
        .memory_live_ins
        .first_mut()
        .ok_or_else(|| String::from("jump-data fixture lost code live-in"))?
        .value = 77;
    if emit_direct_jump_data_coff(
        &wrong_decode,
        direct_jump_data_target(HostIsa::X86_64),
    ) != Err(DirectJumpDataError::ProgramShape)
    {
        return Err(String::from("no-op decode was admitted as jump-data"));
    }

    let mut aliased = program.clone();
    let effect = aliased
        .effects
        .first_mut()
        .ok_or_else(|| String::from("jump-data fixture lost effect"))?;
    effect.before.registers.data_pointer = 5;
    if emit_direct_jump_data_coff(
        &aliased,
        direct_jump_data_target(HostIsa::X86_64),
    ) != Err(DirectJumpDataError::ProgramShape)
    {
        return Err(String::from("aliased jump-data was admitted"));
    }

    let mut wrong_exit = program.clone();
    wrong_exit
        .effects
        .first_mut()
        .ok_or_else(|| String::from("jump-data fixture lost effect"))?
        .after
        .registers
        .data_pointer = 125;
    if emit_direct_jump_data_coff(
        &wrong_exit,
        direct_jump_data_target(HostIsa::X86_64),
    ) != Err(DirectJumpDataError::ProgramShape)
    {
        return Err(String::from("wrong jump-data exit was admitted"));
    }

    let mut wrong_delta = program.clone();
    wrong_delta
        .effects
        .first_mut()
        .and_then(|operation| operation.memory_delta.encryption.as_mut())
        .ok_or_else(|| String::from("jump-data fixture lost encryption"))?
        .after = 94;
    if emit_direct_jump_data_coff(
        &wrong_delta,
        direct_jump_data_target(HostIsa::X86_64),
    ) == Err(DirectJumpDataError::ProgramShape)
    {
        Ok(())
    } else {
        Err(String::from("wrong jump-data encryption was admitted"))
    }
}

fn assert_jump_data_revision_rejected(
    program: &RegionEffectProgram,
) -> Result<(), String> {
    let obsolete = NativeTargetIdentity::new(NativeTargetConfig {
        backend_id: String::from(DIRECT_JUMP_DATA_BACKEND_ID),
        backend_revision: 0,
        host_isa: HostIsa::X86_64,
        host_os: HostOperatingSystem::Windows,
        native_abi_revision: NATIVE_REGION_ABI_REVISION,
        required_features: Vec::new(),
    });
    if emit_direct_jump_data_coff(program, obsolete)
        == Err(DirectJumpDataError::TargetBackend)
    {
        Ok(())
    } else {
        Err(String::from("obsolete jump-data revision was admitted"))
    }
}

#[test]
fn direct_jump_data_rejects_ir_opcode_and_revision_tampering()
-> Result<(), String> {
    let program = direct_jump_data_program();
    let artifact = emit_direct_jump_data_coff(
        &program,
        direct_jump_data_target(HostIsa::X86_64),
    )
    .map_err(|error| error.to_string())?;
    let mut mutated_object = artifact.object().to_vec();
    let commit = [0xc7u8, 0x82, 0x14, 0x00, 0x00, 0x00, 0x5d, 0x00, 0x00, 0x00];
    let offset = mutated_object
        .windows(commit.len())
        .position(|window| window == commit)
        .ok_or_else(|| String::from("jump-data commit opcode missing"))?;
    let immediate = mutated_object
        .get_mut(offset.saturating_add(6))
        .ok_or_else(|| String::from("jump-data commit immediate missing"))?;
    *immediate = 94;
    let tampered = UntrustedNativeObjectArtifact::from_emitter_output(
        artifact.key().clone(),
        mutated_object,
        artifact.target_triple(),
    );
    let _structural = structurally_admit_coff(&tampered)
        .map_err(|error| format!("tampered jump-data structure: {error}"))?;
    if verify_direct_jump_data(&tampered, &program)
        != Err(DirectJumpDataError::ObjectBytes)
    {
        return Err(String::from("tampered jump-data object was admitted"));
    }
    assert_jump_data_shape_rejections(&program)?;
    assert_jump_data_revision_rejected(&program)
}

#[test]
fn direct_crazy_objects_are_byte_exact_and_semantically_admitted()
-> Result<(), String> {
    let cases = [
        (
            HostIsa::X86_64,
            include_str!("execution/fixtures/native-crazy-x86_64-coff.hex"),
        ),
        (
            HostIsa::AArch64,
            include_str!("execution/fixtures/native-crazy-aarch64-coff.hex"),
        ),
    ];
    let program = direct_crazy_program();
    for (isa, fixture) in cases {
        let artifact =
            emit_direct_crazy_coff(&program, direct_crazy_target(isa))
                .map_err(|error| error.to_string())?;
        if artifact.object() != decode_hex_fixture(fixture)? {
            return Err(format!("direct crazy fixture mismatch for {isa:?}"));
        }
        let verified = verify_direct_crazy(&artifact, &program)
            .map_err(|error| error.to_string())?;
        if verified.key() != artifact.key()
            || verified.object() != artifact.object()
            || verified.target_triple() != artifact.target_triple()
        {
            return Err(String::from("verified crazy identity drifted"));
        }
    }
    Ok(())
}

fn assert_crazy_decode_and_alias_rejected(
    program: &RegionEffectProgram,
) -> Result<(), String> {
    let mut wrong_decode = program.clone();
    wrong_decode
        .memory_live_ins
        .first_mut()
        .ok_or_else(|| String::from("crazy fixture lost code live-in"))?
        .value = 34;
    if emit_direct_crazy_coff(
        &wrong_decode,
        direct_crazy_target(HostIsa::X86_64),
    ) != Err(DirectCrazyError::ProgramShape)
    {
        return Err(String::from("rotate decode was admitted as crazy"));
    }
    let mut aliased = program.clone();
    aliased
        .effects
        .first_mut()
        .ok_or_else(|| String::from("crazy fixture lost effect"))?
        .before
        .registers
        .data_pointer = 5;
    if emit_direct_crazy_coff(&aliased, direct_crazy_target(HostIsa::X86_64))
        != Err(DirectCrazyError::ProgramShape)
    {
        return Err(String::from("aliased crazy was admitted"));
    }
    Ok(())
}

fn assert_crazy_value_rejections(
    program: &RegionEffectProgram,
) -> Result<(), String> {
    let mut out_of_domain = program.clone();
    out_of_domain
        .effects
        .first_mut()
        .ok_or_else(|| String::from("crazy fixture lost effect"))?
        .before
        .registers
        .accumulator = current_profile().memory_words();
    if emit_direct_crazy_coff(
        &out_of_domain,
        direct_crazy_target(HostIsa::X86_64),
    ) != Err(DirectCrazyError::ProgramShape)
    {
        return Err(String::from("out-of-domain crazy accumulator admitted"));
    }
    let mut wrong_exit = program.clone();
    wrong_exit
        .effects
        .first_mut()
        .ok_or_else(|| String::from("crazy fixture lost effect"))?
        .after
        .registers
        .accumulator = 2_391_495;
    if emit_direct_crazy_coff(&wrong_exit, direct_crazy_target(HostIsa::X86_64))
        != Err(DirectCrazyError::ProgramShape)
    {
        return Err(String::from("wrong crazy accumulator was admitted"));
    }
    Ok(())
}

fn assert_crazy_delta_rejections(
    program: &RegionEffectProgram,
) -> Result<(), String> {
    let mut wrong_data = program.clone();
    wrong_data
        .effects
        .first_mut()
        .and_then(|effect| effect.memory_delta.data.as_mut())
        .ok_or_else(|| String::from("crazy fixture lost data write"))?
        .after = 2_391_495;
    if emit_direct_crazy_coff(&wrong_data, direct_crazy_target(HostIsa::X86_64))
        != Err(DirectCrazyError::ProgramShape)
    {
        return Err(String::from("wrong crazy data write was admitted"));
    }
    let mut wrong_encryption = program.clone();
    wrong_encryption
        .effects
        .first_mut()
        .and_then(|effect| effect.memory_delta.encryption.as_mut())
        .ok_or_else(|| String::from("crazy fixture lost encryption write"))?
        .after = 92;
    if emit_direct_crazy_coff(
        &wrong_encryption,
        direct_crazy_target(HostIsa::X86_64),
    ) != Err(DirectCrazyError::ProgramShape)
    {
        return Err(String::from("wrong crazy encryption was admitted"));
    }
    Ok(())
}

fn assert_crazy_revision_rejected(
    program: &RegionEffectProgram,
) -> Result<(), String> {
    let obsolete = NativeTargetIdentity::new(NativeTargetConfig {
        backend_id: String::from(DIRECT_CRAZY_BACKEND_ID),
        backend_revision: 0,
        host_isa: HostIsa::X86_64,
        host_os: HostOperatingSystem::Windows,
        native_abi_revision: NATIVE_REGION_ABI_REVISION,
        required_features: Vec::new(),
    });
    if emit_direct_crazy_coff(program, obsolete)
        == Err(DirectCrazyError::TargetBackend)
    {
        Ok(())
    } else {
        Err(String::from("obsolete crazy revision was admitted"))
    }
}

#[test]
fn direct_crazy_rejects_ir_and_opcode_tampering() -> Result<(), String> {
    let program = direct_crazy_program();
    let artifact =
        emit_direct_crazy_coff(&program, direct_crazy_target(HostIsa::X86_64))
            .map_err(|error| error.to_string())?;
    let mut mutated_object = artifact.object().to_vec();
    let commit = [0xc7u8, 0x82, 0x1c, 0, 0, 0, 0xc6, 0x7d, 0x24, 0];
    let offset = mutated_object
        .windows(commit.len())
        .position(|window| window == commit)
        .ok_or_else(|| String::from("crazy data commit opcode missing"))?;
    let immediate = mutated_object
        .get_mut(offset.saturating_add(6))
        .ok_or_else(|| String::from("crazy data commit immediate missing"))?;
    *immediate = 0xc7;
    let tampered = UntrustedNativeObjectArtifact::from_emitter_output(
        artifact.key().clone(),
        mutated_object,
        artifact.target_triple(),
    );
    let _structural = structurally_admit_coff(&tampered)
        .map_err(|error| format!("tampered crazy structure: {error}"))?;
    if verify_direct_crazy(&tampered, &program)
        != Err(DirectCrazyError::ObjectBytes)
    {
        return Err(String::from("tampered crazy object was admitted"));
    }
    assert_crazy_decode_and_alias_rejected(&program)?;
    assert_crazy_value_rejections(&program)?;
    assert_crazy_delta_rejections(&program)?;
    assert_crazy_revision_rejected(&program)
}

#[test]
fn direct_input_objects_are_byte_exact_and_semantically_admitted()
-> Result<(), String> {
    let cases = [
        (
            direct_input_byte_program(),
            HostIsa::X86_64,
            include_str!(
                "execution/fixtures/native-input-byte-x86_64-coff.hex"
            ),
        ),
        (
            direct_input_byte_program(),
            HostIsa::AArch64,
            include_str!(
                "execution/fixtures/native-input-byte-aarch64-coff.hex"
            ),
        ),
        (
            direct_input_eof_program(),
            HostIsa::X86_64,
            include_str!("execution/fixtures/native-input-eof-x86_64-coff.hex"),
        ),
        (
            direct_input_eof_program(),
            HostIsa::AArch64,
            include_str!(
                "execution/fixtures/native-input-eof-aarch64-coff.hex"
            ),
        ),
    ];
    for (program, isa, fixture) in cases {
        let artifact =
            emit_direct_input_coff(&program, direct_input_target(isa))
                .map_err(|error| error.to_string())?;
        if artifact.object() != decode_hex_fixture(fixture)? {
            return Err(format!("direct input fixture mismatch for {isa:?}"));
        }
        let verified = verify_direct_input(&artifact, &program)
            .map_err(|error| error.to_string())?;
        if verified.key() != artifact.key()
            || verified.object() != artifact.object()
            || verified.target_triple() != artifact.target_triple()
        {
            return Err(String::from("verified input identity drifted"));
        }
    }
    Ok(())
}

fn assert_input_shape_rejections() -> Result<(), String> {
    let mut wrong_decode = direct_input_byte_program();
    wrong_decode
        .memory_live_ins
        .first_mut()
        .ok_or_else(|| String::from("input fixture lost live-in"))?
        .value = 112;
    if emit_direct_input_coff(
        &wrong_decode,
        direct_input_target(HostIsa::X86_64),
    ) != Err(DirectInputError::ProgramShape)
    {
        return Err(String::from("output decode was admitted as input"));
    }
    let mut wrong_byte = direct_input_byte_program();
    wrong_byte
        .effects
        .first_mut()
        .ok_or_else(|| String::from("input fixture lost effect"))?
        .input = Some(TraceInput::Byte(0x42));
    if emit_direct_input_coff(&wrong_byte, direct_input_target(HostIsa::X86_64))
        != Err(DirectInputError::ProgramShape)
    {
        return Err(String::from("wrong input byte was admitted"));
    }
    let mut wrong_cursor = direct_input_byte_program();
    wrong_cursor
        .effects
        .first_mut()
        .ok_or_else(|| String::from("input fixture lost effect"))?
        .after
        .input_consumed = 4;
    if emit_direct_input_coff(
        &wrong_cursor,
        direct_input_target(HostIsa::X86_64),
    ) != Err(DirectInputError::ProgramShape)
    {
        return Err(String::from("wrong input cursor was admitted"));
    }
    let mut wrong_eof = direct_input_eof_program();
    wrong_eof
        .effects
        .first_mut()
        .ok_or_else(|| String::from("EOF fixture lost effect"))?
        .after
        .registers
        .accumulator = 4_782_967;
    if emit_direct_input_coff(&wrong_eof, direct_input_target(HostIsa::X86_64))
        != Err(DirectInputError::ProgramShape)
    {
        return Err(String::from("wrong EOF word was admitted"));
    }
    Ok(())
}

fn assert_input_revision_rejected() -> Result<(), String> {
    let obsolete = NativeTargetIdentity::new(NativeTargetConfig {
        backend_id: String::from(DIRECT_INPUT_BACKEND_ID),
        backend_revision: 0,
        host_isa: HostIsa::X86_64,
        host_os: HostOperatingSystem::Windows,
        native_abi_revision: NATIVE_REGION_ABI_REVISION,
        required_features: Vec::new(),
    });
    if emit_direct_input_coff(&direct_input_byte_program(), obsolete)
        == Err(DirectInputError::TargetBackend)
    {
        Ok(())
    } else {
        Err(String::from("obsolete input revision was admitted"))
    }
}

#[test]
fn direct_input_rejects_ir_and_opcode_tampering() -> Result<(), String> {
    let program = direct_input_byte_program();
    let artifact =
        emit_direct_input_coff(&program, direct_input_target(HostIsa::X86_64))
            .map_err(|error| error.to_string())?;
    let mut mutated_object = artifact.object().to_vec();
    let guard = [0x43u8, 0x80, 0x3c, 0x13, 0x41];
    let offset = mutated_object
        .windows(guard.len())
        .position(|window| window == guard)
        .ok_or_else(|| String::from("input byte guard missing"))?;
    let byte = mutated_object
        .get_mut(offset.saturating_add(4))
        .ok_or_else(|| String::from("input byte immediate missing"))?;
    *byte = 0x42;
    let tampered = UntrustedNativeObjectArtifact::from_emitter_output(
        artifact.key().clone(),
        mutated_object,
        artifact.target_triple(),
    );
    let _structural = structurally_admit_coff(&tampered)
        .map_err(|error| format!("tampered input structure: {error}"))?;
    if verify_direct_input(&tampered, &program)
        != Err(DirectInputError::ObjectBytes)
    {
        return Err(String::from("tampered input object was admitted"));
    }
    assert_input_shape_rejections()?;
    assert_input_revision_rejected()
}

#[test]
fn direct_output_objects_are_byte_exact_and_semantically_admitted()
-> Result<(), String> {
    let cases = [
        (
            HostIsa::X86_64,
            include_str!("execution/fixtures/native-output-x86_64-coff.hex"),
        ),
        (
            HostIsa::AArch64,
            include_str!("execution/fixtures/native-output-aarch64-coff.hex"),
        ),
    ];
    let program = direct_output_program();
    for (isa, fixture) in cases {
        let artifact =
            emit_direct_output_coff(&program, direct_output_target(isa))
                .map_err(|error| error.to_string())?;
        if artifact.object() != decode_hex_fixture(fixture)? {
            return Err(format!("direct output fixture mismatch for {isa:?}"));
        }
        let verified = verify_direct_output(&artifact, &program)
            .map_err(|error| error.to_string())?;
        if verified.key() != artifact.key()
            || verified.object() != artifact.object()
            || verified.target_triple() != artifact.target_triple()
        {
            return Err(String::from("verified output identity drifted"));
        }
    }
    Ok(())
}

fn assert_output_shape_rejections(
    program: &RegionEffectProgram,
) -> Result<(), String> {
    let mut wrong_decode = program.clone();
    wrong_decode
        .memory_live_ins
        .first_mut()
        .ok_or_else(|| String::from("output fixture lost live-in"))?
        .value = 77;
    if emit_direct_output_coff(
        &wrong_decode,
        direct_output_target(HostIsa::X86_64),
    ) != Err(DirectOutputError::ProgramShape)
    {
        return Err(String::from("no-op decode was admitted as output"));
    }
    let mut wrong_output = program.clone();
    wrong_output
        .effects
        .first_mut()
        .ok_or_else(|| String::from("output fixture lost effect"))?
        .output = Some(0xa9);
    if emit_direct_output_coff(
        &wrong_output,
        direct_output_target(HostIsa::X86_64),
    ) != Err(DirectOutputError::ProgramShape)
    {
        return Err(String::from("wrong output byte was admitted"));
    }
    let mut wrong_length = program.clone();
    wrong_length
        .effects
        .first_mut()
        .ok_or_else(|| String::from("output fixture lost effect"))?
        .after
        .output_len = 5;
    if emit_direct_output_coff(
        &wrong_length,
        direct_output_target(HostIsa::X86_64),
    ) != Err(DirectOutputError::ProgramShape)
    {
        return Err(String::from("wrong output length was admitted"));
    }
    Ok(())
}

fn assert_output_revision_rejected(
    program: &RegionEffectProgram,
) -> Result<(), String> {
    let obsolete = NativeTargetIdentity::new(NativeTargetConfig {
        backend_id: String::from(DIRECT_OUTPUT_BACKEND_ID),
        backend_revision: 0,
        host_isa: HostIsa::X86_64,
        host_os: HostOperatingSystem::Windows,
        native_abi_revision: NATIVE_REGION_ABI_REVISION,
        required_features: Vec::new(),
    });
    if emit_direct_output_coff(program, obsolete)
        == Err(DirectOutputError::TargetBackend)
    {
        Ok(())
    } else {
        Err(String::from("obsolete output revision was admitted"))
    }
}

#[test]
fn direct_output_rejects_ir_and_opcode_tampering() -> Result<(), String> {
    let program = direct_output_program();
    let artifact = emit_direct_output_coff(
        &program,
        direct_output_target(HostIsa::X86_64),
    )
    .map_err(|error| error.to_string())?;
    let mut mutated_object = artifact.object().to_vec();
    let commit = [0x43u8, 0xc6, 0x04, 0x13, 0xa8];
    let offset = mutated_object
        .windows(commit.len())
        .position(|window| window == commit)
        .ok_or_else(|| String::from("output byte commit missing"))?;
    let byte = mutated_object
        .get_mut(offset.saturating_add(4))
        .ok_or_else(|| String::from("output byte immediate missing"))?;
    *byte = 0xa9;
    let tampered = UntrustedNativeObjectArtifact::from_emitter_output(
        artifact.key().clone(),
        mutated_object,
        artifact.target_triple(),
    );
    let _structural = structurally_admit_coff(&tampered)
        .map_err(|error| format!("tampered output structure: {error}"))?;
    if verify_direct_output(&tampered, &program)
        != Err(DirectOutputError::ObjectBytes)
    {
        return Err(String::from("tampered output object was admitted"));
    }
    assert_output_shape_rejections(&program)?;
    assert_output_revision_rejected(&program)
}

#[test]
fn direct_rotate_objects_are_byte_exact_and_semantically_admitted()
-> Result<(), String> {
    let cases = [
        (
            HostIsa::X86_64,
            include_str!("execution/fixtures/native-rotate-x86_64-coff.hex"),
        ),
        (
            HostIsa::AArch64,
            include_str!("execution/fixtures/native-rotate-aarch64-coff.hex"),
        ),
    ];
    let program = direct_rotate_program();
    for (isa, fixture) in cases {
        let artifact =
            emit_direct_rotate_coff(&program, direct_rotate_target(isa))
                .map_err(|error| error.to_string())?;
        if artifact.object() != decode_hex_fixture(fixture)? {
            return Err(format!("direct rotate fixture mismatch for {isa:?}"));
        }
        let verified = verify_direct_rotate(&artifact, &program)
            .map_err(|error| error.to_string())?;
        if verified.key() != artifact.key()
            || verified.object() != artifact.object()
            || verified.target_triple() != artifact.target_triple()
        {
            return Err(String::from("verified rotate identity drifted"));
        }
    }
    Ok(())
}

fn assert_rotate_shape_rejections(
    program: &RegionEffectProgram,
) -> Result<(), String> {
    let mut wrong_decode = program.clone();
    wrong_decode
        .memory_live_ins
        .first_mut()
        .ok_or_else(|| String::from("rotate fixture lost code live-in"))?
        .value = 35;
    if emit_direct_rotate_coff(
        &wrong_decode,
        direct_rotate_target(HostIsa::X86_64),
    ) != Err(DirectRotateError::ProgramShape)
    {
        return Err(String::from("jump-data decode was admitted as rotate"));
    }
    let mut aliased = program.clone();
    aliased
        .effects
        .first_mut()
        .ok_or_else(|| String::from("rotate fixture lost effect"))?
        .before
        .registers
        .data_pointer = 5;
    if emit_direct_rotate_coff(&aliased, direct_rotate_target(HostIsa::X86_64))
        != Err(DirectRotateError::ProgramShape)
    {
        return Err(String::from("aliased rotate was admitted"));
    }
    let mut out_of_domain = program.clone();
    out_of_domain
        .memory_live_ins
        .get_mut(1)
        .ok_or_else(|| String::from("rotate fixture lost data live-in"))?
        .value = current_profile().memory_words();
    if emit_direct_rotate_coff(
        &out_of_domain,
        direct_rotate_target(HostIsa::X86_64),
    ) != Err(DirectRotateError::ProgramShape)
    {
        return Err(String::from("out-of-domain rotate data was admitted"));
    }
    let mut wrong_exit = program.clone();
    wrong_exit
        .effects
        .first_mut()
        .ok_or_else(|| String::from("rotate fixture lost effect"))?
        .after
        .registers
        .accumulator = 1_594_327;
    if emit_direct_rotate_coff(
        &wrong_exit,
        direct_rotate_target(HostIsa::X86_64),
    ) != Err(DirectRotateError::ProgramShape)
    {
        return Err(String::from("wrong rotate accumulator was admitted"));
    }
    assert_rotate_delta_rejections(program)
}

fn assert_rotate_delta_rejections(
    program: &RegionEffectProgram,
) -> Result<(), String> {
    let mut wrong_data = program.clone();
    wrong_data
        .effects
        .first_mut()
        .and_then(|effect| effect.memory_delta.data.as_mut())
        .ok_or_else(|| String::from("rotate fixture lost data write"))?
        .after = 1_594_327;
    if emit_direct_rotate_coff(
        &wrong_data,
        direct_rotate_target(HostIsa::X86_64),
    ) != Err(DirectRotateError::ProgramShape)
    {
        return Err(String::from("wrong rotate data write was admitted"));
    }
    let mut wrong_encryption = program.clone();
    wrong_encryption
        .effects
        .first_mut()
        .and_then(|effect| effect.memory_delta.encryption.as_mut())
        .ok_or_else(|| String::from("rotate fixture lost encryption write"))?
        .after = 123;
    if emit_direct_rotate_coff(
        &wrong_encryption,
        direct_rotate_target(HostIsa::X86_64),
    ) == Err(DirectRotateError::ProgramShape)
    {
        Ok(())
    } else {
        Err(String::from("wrong rotate encryption was admitted"))
    }
}

fn assert_rotate_revision_rejected(
    program: &RegionEffectProgram,
) -> Result<(), String> {
    let obsolete = NativeTargetIdentity::new(NativeTargetConfig {
        backend_id: String::from(DIRECT_ROTATE_BACKEND_ID),
        backend_revision: 0,
        host_isa: HostIsa::X86_64,
        host_os: HostOperatingSystem::Windows,
        native_abi_revision: NATIVE_REGION_ABI_REVISION,
        required_features: Vec::new(),
    });
    if emit_direct_rotate_coff(program, obsolete)
        == Err(DirectRotateError::TargetBackend)
    {
        Ok(())
    } else {
        Err(String::from("obsolete rotate revision was admitted"))
    }
}

#[test]
fn direct_rotate_rejects_ir_and_opcode_tampering() -> Result<(), String> {
    let program = direct_rotate_program();
    let artifact = emit_direct_rotate_coff(
        &program,
        direct_rotate_target(HostIsa::X86_64),
    )
    .map_err(|error| error.to_string())?;
    let mut mutated_object = artifact.object().to_vec();
    let commit = [0xc7u8, 0x82, 0x1c, 0x00, 0x00, 0x00, 0xd6, 0x53, 0x18, 0x00];
    let offset = mutated_object
        .windows(commit.len())
        .position(|window| window == commit)
        .ok_or_else(|| String::from("rotate data commit opcode missing"))?;
    let immediate = mutated_object
        .get_mut(offset.saturating_add(6))
        .ok_or_else(|| String::from("rotate data commit immediate missing"))?;
    *immediate = 0xd7;
    let tampered = UntrustedNativeObjectArtifact::from_emitter_output(
        artifact.key().clone(),
        mutated_object,
        artifact.target_triple(),
    );
    let _structural = structurally_admit_coff(&tampered)
        .map_err(|error| format!("tampered rotate structure: {error}"))?;
    if verify_direct_rotate(&tampered, &program)
        != Err(DirectRotateError::ObjectBytes)
    {
        return Err(String::from("tampered rotate object was admitted"));
    }
    assert_rotate_shape_rejections(&program)?;
    assert_rotate_revision_rejected(&program)
}

#[test]
fn direct_no_operation_objects_are_byte_exact_and_semantically_admitted()
-> Result<(), String> {
    let cases = [
        (
            HostIsa::X86_64,
            include_str!(
                "execution/fixtures/native-no-operation-x86_64-coff.hex"
            ),
        ),
        (
            HostIsa::AArch64,
            include_str!(
                "execution/fixtures/native-no-operation-aarch64-coff.hex"
            ),
        ),
    ];
    let program = direct_no_operation_program();
    for (isa, fixture) in cases {
        let artifact = emit_direct_no_operation_coff(
            &program,
            direct_no_operation_target(isa),
        )
        .map_err(|error| error.to_string())?;
        if artifact.object() != decode_hex_fixture(fixture)? {
            return Err(format!(
                "direct no-operation fixture mismatch for {isa:?}"
            ));
        }
        let verified = verify_direct_no_operation(&artifact, &program)
            .map_err(|error| error.to_string())?;
        if verified.key() != artifact.key()
            || verified.object() != artifact.object()
            || verified.target_triple() != artifact.target_triple()
        {
            return Err(String::from("verified no-operation identity drifted"));
        }
    }
    Ok(())
}

fn assert_no_operation_shape_rejections(
    program: &RegionEffectProgram,
) -> Result<(), String> {
    let mut wrong_decode = program.clone();
    wrong_decode
        .memory_live_ins
        .first_mut()
        .ok_or_else(|| String::from("no-operation fixture lost live-in"))?
        .value = 76;
    if emit_direct_no_operation_coff(
        &wrong_decode,
        direct_no_operation_target(HostIsa::X86_64),
    ) != Err(DirectNoOperationError::ProgramShape)
    {
        return Err(String::from("halt decode was admitted as no-operation"));
    }

    let mut wrong_pointer = program.clone();
    wrong_pointer
        .effects
        .first_mut()
        .ok_or_else(|| String::from("no-operation fixture lost effect"))?
        .after
        .registers
        .code_pointer = 7;
    if emit_direct_no_operation_coff(
        &wrong_pointer,
        direct_no_operation_target(HostIsa::X86_64),
    ) != Err(DirectNoOperationError::ProgramShape)
    {
        return Err(String::from("wrong no-operation pointer was admitted"));
    }

    let mut wrong_delta = program.clone();
    wrong_delta
        .effects
        .first_mut()
        .and_then(|effect| effect.memory_delta.encryption.as_mut())
        .ok_or_else(|| String::from("no-operation fixture lost encryption"))?
        .after = 66;
    if emit_direct_no_operation_coff(
        &wrong_delta,
        direct_no_operation_target(HostIsa::X86_64),
    ) == Err(DirectNoOperationError::ProgramShape)
    {
        Ok(())
    } else {
        Err(String::from("wrong no-operation encryption was admitted"))
    }
}

fn assert_no_operation_revision_rejected(
    program: &RegionEffectProgram,
) -> Result<(), String> {
    let obsolete = NativeTargetIdentity::new(NativeTargetConfig {
        backend_id: String::from(DIRECT_NO_OPERATION_BACKEND_ID),
        backend_revision: 1,
        host_isa: HostIsa::X86_64,
        host_os: HostOperatingSystem::Windows,
        native_abi_revision: NATIVE_REGION_ABI_REVISION,
        required_features: Vec::new(),
    });
    if emit_direct_no_operation_coff(program, obsolete)
        == Err(DirectNoOperationError::TargetBackend)
    {
        Ok(())
    } else {
        Err(String::from("obsolete no-operation revision was admitted"))
    }
}

#[test]
fn direct_no_operation_rejects_ir_opcode_and_revision_tampering()
-> Result<(), String> {
    let program = direct_no_operation_program();
    let artifact = emit_direct_no_operation_coff(
        &program,
        direct_no_operation_target(HostIsa::X86_64),
    )
    .map_err(|error| error.to_string())?;
    let mut mutated_object = artifact.object().to_vec();
    let commit = [0x42u8, 0xc7, 0x04, 0x8a, 0x41, 0x00, 0x00, 0x00];
    let offset = mutated_object
        .windows(commit.len())
        .position(|window| window == commit)
        .ok_or_else(|| String::from("no-operation commit opcode missing"))?;
    let immediate = mutated_object
        .get_mut(offset.saturating_add(4))
        .ok_or_else(|| String::from("no-operation commit immediate missing"))?;
    *immediate = 66;
    let tampered = UntrustedNativeObjectArtifact::from_emitter_output(
        artifact.key().clone(),
        mutated_object,
        artifact.target_triple(),
    );
    let _structural = structurally_admit_coff(&tampered)
        .map_err(|error| format!("tampered no-operation structure: {error}"))?;
    if verify_direct_no_operation(&tampered, &program)
        != Err(DirectNoOperationError::ObjectBytes)
    {
        return Err(String::from("tampered no-operation object was admitted"));
    }
    assert_no_operation_shape_rejections(&program)?;
    assert_no_operation_revision_rejected(&program)
}

#[test]
fn direct_non_graphical_objects_are_byte_exact_and_semantically_admitted()
-> Result<(), String> {
    let cases = [
        (
            HostIsa::X86_64,
            include_str!(
                "execution/fixtures/native-non-graphical-x86_64-coff.hex"
            ),
        ),
        (
            HostIsa::AArch64,
            include_str!(
                "execution/fixtures/native-non-graphical-aarch64-coff.hex"
            ),
        ),
    ];
    let program = direct_non_graphical_program();
    for (isa, fixture) in cases {
        let artifact = emit_direct_non_graphical_coff(
            &program,
            direct_non_graphical_target(isa),
        )
        .map_err(|error| error.to_string())?;
        if artifact.object() != decode_hex_fixture(fixture)? {
            return Err(format!(
                "direct non-graphical fixture mismatch for {isa:?}"
            ));
        }
        let verified = verify_direct_non_graphical(&artifact, &program)
            .map_err(|error| error.to_string())?;
        if verified.key() != artifact.key()
            || verified.object() != artifact.object()
            || verified.target_triple() != artifact.target_triple()
        {
            return Err(String::from(
                "verified non-graphical identity drifted",
            ));
        }
    }
    Ok(())
}

fn assert_non_graphical_shape_rejections(
    program: &RegionEffectProgram,
) -> Result<(), String> {
    let mut graphical = program.clone();
    let graphical_live_in = graphical
        .memory_live_ins
        .first_mut()
        .ok_or_else(|| String::from("non-graphical fixture lost live-in"))?;
    graphical_live_in.value = 33;
    if emit_direct_non_graphical_coff(
        &graphical,
        direct_non_graphical_target(HostIsa::X86_64),
    ) != Err(DirectNonGraphicalError::ProgramShape)
    {
        return Err(String::from("graphical live-in was admitted"));
    }
    let mut wrong_address = program.clone();
    let address_live_in =
        wrong_address.memory_live_ins.first_mut().ok_or_else(|| {
            String::from("non-graphical fixture lost address live-in")
        })?;
    address_live_in.address = 6;
    if emit_direct_non_graphical_coff(
        &wrong_address,
        direct_non_graphical_target(HostIsa::X86_64),
    ) == Err(DirectNonGraphicalError::ProgramShape)
    {
        Ok(())
    } else {
        Err(String::from("wrong fetch live-in was admitted"))
    }
}

fn assert_non_graphical_revision_rejected(
    program: &RegionEffectProgram,
) -> Result<(), String> {
    let obsolete = NativeTargetIdentity::new(NativeTargetConfig {
        backend_id: String::from(DIRECT_NON_GRAPHICAL_BACKEND_ID),
        backend_revision: 1,
        host_isa: HostIsa::X86_64,
        host_os: HostOperatingSystem::Windows,
        native_abi_revision: NATIVE_REGION_ABI_REVISION,
        required_features: Vec::new(),
    });
    if emit_direct_non_graphical_coff(program, obsolete)
        == Err(DirectNonGraphicalError::TargetBackend)
    {
        Ok(())
    } else {
        Err(String::from("obsolete non-graphical revision was admitted"))
    }
}

#[test]
fn direct_non_graphical_rejects_ir_opcode_and_revision_tampering()
-> Result<(), String> {
    let program = direct_non_graphical_program();
    let artifact = emit_direct_non_graphical_coff(
        &program,
        direct_non_graphical_target(HostIsa::X86_64),
    )
    .map_err(|error| error.to_string())?;
    let mut mutated_object = artifact.object().to_vec();
    let commit = [0xc6u8, 0x41, 0x4c, 0x02];
    let offset = mutated_object
        .windows(commit.len())
        .position(|window| window == commit)
        .ok_or_else(|| String::from("non-graphical commit opcode missing"))?;
    let immediate = mutated_object
        .get_mut(offset.saturating_add(3))
        .ok_or_else(|| {
            String::from("non-graphical commit immediate missing")
        })?;
    *immediate = 1;
    let tampered = UntrustedNativeObjectArtifact::from_emitter_output(
        artifact.key().clone(),
        mutated_object,
        artifact.target_triple(),
    );
    let _structural = structurally_admit_coff(&tampered).map_err(|error| {
        format!("tampered non-graphical structure: {error}")
    })?;
    if verify_direct_non_graphical(&tampered, &program)
        != Err(DirectNonGraphicalError::ObjectBytes)
    {
        return Err(String::from("tampered non-graphical object was admitted"));
    }
    assert_non_graphical_shape_rejections(&program)?;
    assert_non_graphical_revision_rejected(&program)
}

#[test]
fn direct_initial_halt_objects_are_byte_exact_and_semantically_admitted()
-> Result<(), String> {
    let cases = [
        (
            HostIsa::X86_64,
            include_str!(
                "execution/fixtures/native-initial-halt-x86_64-coff.hex"
            ),
        ),
        (
            HostIsa::AArch64,
            include_str!(
                "execution/fixtures/native-initial-halt-aarch64-coff.hex"
            ),
        ),
    ];
    let program = direct_initial_halt_program();
    for (isa, fixture) in cases {
        let artifact = emit_direct_initial_halt_coff(
            &program,
            direct_initial_halt_target(isa),
        )
        .map_err(|error| error.to_string())?;
        if artifact.object() != decode_hex_fixture(fixture)? {
            return Err(format!(
                "direct initial-halt fixture mismatch for {isa:?}"
            ));
        }
        let verified = verify_direct_initial_halt(&artifact, &program)
            .map_err(|error| error.to_string())?;
        if verified.key() != artifact.key()
            || verified.object() != artifact.object()
            || verified.target_triple() != artifact.target_triple()
        {
            return Err(String::from("verified initial-halt identity drifted"));
        }
    }
    Ok(())
}

#[test]
fn direct_initial_halt_rejects_ir_and_opcode_tampering() -> Result<(), String> {
    let program = direct_initial_halt_program();
    let artifact = emit_direct_initial_halt_coff(
        &program,
        direct_initial_halt_target(HostIsa::X86_64),
    )
    .map_err(|error| error.to_string())?;

    let mut mutated_object = artifact.object().to_vec();
    let commit = [0xc6u8, 0x41, 0x4c, 0x01];
    let offset = mutated_object
        .windows(commit.len())
        .position(|window| window == commit)
        .ok_or_else(|| String::from("initial-halt commit opcode missing"))?;
    let immediate = mutated_object
        .get_mut(offset.saturating_add(3))
        .ok_or_else(|| String::from("initial-halt commit immediate missing"))?;
    *immediate = 2;
    let tampered = UntrustedNativeObjectArtifact::from_emitter_output(
        artifact.key().clone(),
        mutated_object,
        artifact.target_triple(),
    );
    let _structural = structurally_admit_coff(&tampered)
        .map_err(|error| format!("tampered initial-halt structure: {error}"))?;
    if verify_direct_initial_halt(&tampered, &program)
        != Err(DirectInitialHaltError::ObjectBytes)
    {
        return Err(String::from("tampered initial-halt object was admitted"));
    }

    let mut with_live_in = program.clone();
    with_live_in
        .memory_live_ins
        .push(MemoryLiveIn { address: 7, value: 8 });
    if emit_direct_initial_halt_coff(
        &with_live_in,
        direct_initial_halt_target(HostIsa::X86_64),
    ) != Err(DirectInitialHaltError::ProgramShape)
    {
        return Err(String::from("initial-halt live-in mutation was admitted"));
    }

    let mut with_input = program;
    let first = with_input.effects.first_mut().ok_or_else(|| {
        String::from("initial-halt fixture lost first effect")
    })?;
    first.input = Some(TraceInput::EndOfInput);
    if emit_direct_initial_halt_coff(
        &with_input,
        direct_initial_halt_target(HostIsa::X86_64),
    ) != Err(DirectInitialHaltError::ProgramShape)
    {
        return Err(String::from("initial-halt input mutation was admitted"));
    }
    Ok(())
}

fn assert_jump_code_capacity_rejected() -> Result<(), String> {
    let mut jump_code = direct_jump_code_program();
    jump_code.profile_requirement.memory_words = 12;
    if emit_direct_jump_code_coff(
        &jump_code,
        direct_jump_code_target(HostIsa::X86_64),
    ) == Err(DirectJumpCodeError::ProgramShape)
    {
        Ok(())
    } else {
        Err(String::from(
            "jump-code profile-capacity mismatch was admitted",
        ))
    }
}

fn assert_jump_data_capacity_rejected() -> Result<(), String> {
    let mut jump_data = direct_jump_data_program();
    jump_data.profile_requirement.memory_words = 124;
    if emit_direct_jump_data_coff(
        &jump_data,
        direct_jump_data_target(HostIsa::X86_64),
    ) == Err(DirectJumpDataError::ProgramShape)
    {
        Ok(())
    } else {
        Err(String::from(
            "jump-data profile-capacity mismatch was admitted",
        ))
    }
}

fn assert_crazy_capacity_rejected() -> Result<(), String> {
    let mut crazy = direct_crazy_program();
    crazy.profile_requirement.memory_words = 7;
    if emit_direct_crazy_coff(&crazy, direct_crazy_target(HostIsa::X86_64))
        == Err(DirectCrazyError::ProgramShape)
    {
        Ok(())
    } else {
        Err(String::from("crazy profile-capacity mismatch was admitted"))
    }
}

fn assert_input_capacity_rejected() -> Result<(), String> {
    let mut input = direct_input_byte_program();
    input.profile_requirement.memory_words = 8;
    if emit_direct_input_coff(&input, direct_input_target(HostIsa::X86_64))
        == Err(DirectInputError::ProgramShape)
    {
        Ok(())
    } else {
        Err(String::from("input profile-capacity mismatch was admitted"))
    }
}

fn assert_output_capacity_rejected() -> Result<(), String> {
    let mut output = direct_output_program();
    output.profile_requirement.memory_words = 8;
    if emit_direct_output_coff(&output, direct_output_target(HostIsa::X86_64))
        == Err(DirectOutputError::ProgramShape)
    {
        Ok(())
    } else {
        Err(String::from(
            "output profile-capacity mismatch was admitted",
        ))
    }
}

fn assert_rotate_capacity_rejected() -> Result<(), String> {
    let mut rotate = direct_rotate_program();
    rotate.profile_requirement.memory_words = 7;
    if emit_direct_rotate_coff(&rotate, direct_rotate_target(HostIsa::X86_64))
        == Err(DirectRotateError::ProgramShape)
    {
        Ok(())
    } else {
        Err(String::from(
            "rotate profile-capacity mismatch was admitted",
        ))
    }
}

fn assert_initial_halt_capacity_rejected() -> Result<(), String> {
    let mut initial_halt = direct_initial_halt_program();
    initial_halt.profile_requirement.memory_words = 0;
    if emit_direct_initial_halt_coff(
        &initial_halt,
        direct_initial_halt_target(HostIsa::X86_64),
    ) == Err(DirectInitialHaltError::ProgramShape)
    {
        Ok(())
    } else {
        Err(String::from(
            "initial-halt profile-capacity mismatch was admitted",
        ))
    }
}

#[test]
fn direct_fast_paths_reject_undersized_profile_capacity() -> Result<(), String>
{
    assert_jump_code_capacity_rejected()?;
    assert_crazy_capacity_rejected()?;
    assert_input_capacity_rejected()?;
    assert_output_capacity_rejected()?;
    assert_rotate_capacity_rejected()?;
    assert_jump_data_capacity_rejected()?;
    let mut register_halt = direct_halt_registers_program();
    register_halt.profile_requirement.memory_words = 1;
    if emit_direct_halt_registers_coff(
        &register_halt,
        direct_halt_registers_target(HostIsa::X86_64),
    ) != Err(DirectHaltRegistersError::ProgramShape)
    {
        return Err(String::from(
            "register-halt profile-capacity mismatch was admitted",
        ));
    }

    let mut halt_fetch = direct_halt_fetch_program();
    halt_fetch.profile_requirement.memory_words = 5;
    if emit_direct_halt_fetch_coff(
        &halt_fetch,
        direct_halt_fetch_target(HostIsa::X86_64),
    ) != Err(DirectHaltFetchError::ProgramShape)
    {
        return Err(String::from(
            "halt-fetch profile-capacity mismatch was admitted",
        ));
    }

    let mut no_operation = direct_no_operation_program();
    no_operation.profile_requirement.memory_words = 8;
    if emit_direct_no_operation_coff(
        &no_operation,
        direct_no_operation_target(HostIsa::X86_64),
    ) != Err(DirectNoOperationError::ProgramShape)
    {
        return Err(String::from(
            "no-operation profile-capacity mismatch was admitted",
        ));
    }

    let mut non_graphical = direct_non_graphical_program();
    non_graphical.profile_requirement.memory_words = 5;
    if emit_direct_non_graphical_coff(
        &non_graphical,
        direct_non_graphical_target(HostIsa::X86_64),
    ) != Err(DirectNonGraphicalError::ProgramShape)
    {
        return Err(String::from(
            "non-graphical profile-capacity mismatch was admitted",
        ));
    }

    assert_initial_halt_capacity_rejected()
}

#[test]
fn direct_deopt_objects_are_byte_exact_and_semantically_admitted()
-> Result<(), String> {
    let cases = [
        (
            HostIsa::X86_64,
            include_str!("execution/fixtures/native-deopt-x86_64-coff.hex"),
        ),
        (
            HostIsa::AArch64,
            include_str!("execution/fixtures/native-deopt-aarch64-coff.hex"),
        ),
    ];
    for (isa, fixture) in cases {
        let artifact =
            emit_direct_deopt_coff(&native_program(), direct_deopt_target(isa))
                .map_err(|error| error.to_string())?;
        let expected = decode_hex_fixture(fixture)?;
        if artifact.object() != expected {
            return Err(format!("direct deopt fixture mismatch for {isa:?}"));
        }
        let verified = verify_direct_deopt_stub(&artifact)
            .map_err(|error| error.to_string())?;
        if verified.key() != artifact.key()
            || verified.object() != artifact.object()
            || verified.target_triple() != artifact.target_triple()
        {
            return Err(String::from("verified direct deopt identity drifted"));
        }
    }
    Ok(())
}

fn assert_direct_profile_metadata_mismatch(
    program: &RegionEffectProgram,
    artifact: &UntrustedNativeObjectArtifact,
) -> Result<(), String> {
    let mut renamed_program = program.clone();
    renamed_program.profile_id = String::from("malbolge-2026.2-alias");
    let renamed = emit_direct_deopt_coff(
        &renamed_program,
        direct_deopt_target(HostIsa::X86_64),
    )
    .map_err(|error| error.to_string())?;
    let mismatched = UntrustedNativeObjectArtifact::from_emitter_output(
        renamed.key().clone(),
        artifact.object().to_vec(),
        artifact.target_triple(),
    );
    if structurally_admit_coff(&mismatched)
        != Err(CoffAdmissionError::ProfileMetadata)
    {
        return Err(String::from("object/key profile mismatch was admitted"));
    }

    let mut geometry_program = program.clone();
    geometry_program.profile_requirement.word_trits = geometry_program
        .profile_requirement
        .word_trits
        .saturating_add(1);
    let geometry = emit_direct_deopt_coff(
        &geometry_program,
        direct_deopt_target(HostIsa::X86_64),
    )
    .map_err(|error| error.to_string())?;
    let geometry_mismatch = UntrustedNativeObjectArtifact::from_emitter_output(
        geometry.key().clone(),
        artifact.object().to_vec(),
        artifact.target_triple(),
    );
    if structurally_admit_coff(&geometry_mismatch)
        != Err(CoffAdmissionError::ProfileMetadata)
    {
        return Err(String::from("object/key geometry mismatch was admitted"));
    }
    Ok(())
}

fn assert_direct_profile_footprint_mismatch(
    program: &RegionEffectProgram,
    artifact: &UntrustedNativeObjectArtifact,
) -> Result<(), String> {
    let mut footprint_program = program.clone();
    let footprint_live_in = footprint_program
        .memory_live_ins
        .first_mut()
        .ok_or_else(|| String::from("profile fixture has no memory live-in"))?;
    footprint_live_in.address = footprint_live_in.address.saturating_add(1);
    let footprint = emit_direct_deopt_coff(
        &footprint_program,
        direct_deopt_target(HostIsa::X86_64),
    )
    .map_err(|error| error.to_string())?;
    if footprint.key().ir().required_memory_words()
        == artifact.key().ir().required_memory_words()
    {
        return Err(String::from("footprint mutation kept native identity"));
    }
    let mismatch = UntrustedNativeObjectArtifact::from_emitter_output(
        footprint.key().clone(),
        artifact.object().to_vec(),
        artifact.target_triple(),
    );
    if structurally_admit_coff(&mismatch)
        == Err(CoffAdmissionError::ProfileMetadata)
    {
        Ok(())
    } else {
        Err(String::from("object/key footprint mismatch was admitted"))
    }
}

fn assert_missing_direct_profile_metadata(
    artifact: &UntrustedNativeObjectArtifact,
) -> Result<(), String> {
    let mut missing = artifact.object().to_vec();
    let section_name = b".mbprof";
    let section_offset = missing
        .windows(section_name.len())
        .position(|window| window == section_name)
        .ok_or_else(|| String::from("direct object lacks profile section"))?;
    let section_marker = missing
        .get_mut(section_offset.saturating_add(1))
        .ok_or_else(|| String::from("profile section name offset invalid"))?;
    *section_marker = b'x';
    let missing_artifact = UntrustedNativeObjectArtifact::from_emitter_output(
        artifact.key().clone(),
        missing,
        artifact.target_triple(),
    );
    if structurally_admit_coff(&missing_artifact)
        != Err(CoffAdmissionError::ProfileMetadata)
    {
        return Err(String::from(
            "direct object without metadata was admitted",
        ));
    }
    Ok(())
}

fn assert_tampered_direct_profile_metadata(
    artifact: &UntrustedNativeObjectArtifact,
) -> Result<(), String> {
    let mut tampered = artifact.object().to_vec();
    let metadata_offset = tampered
        .windows(4)
        .position(|window| window == b"MBPF")
        .ok_or_else(|| String::from("direct object lacks profile metadata"))?;
    let metadata_version = tampered
        .get_mut(metadata_offset.saturating_add(4))
        .ok_or_else(|| {
            String::from("profile metadata version offset invalid")
        })?;
    *metadata_version ^= 1;
    let tampered_artifact = UntrustedNativeObjectArtifact::from_emitter_output(
        artifact.key().clone(),
        tampered,
        artifact.target_triple(),
    );
    if structurally_admit_coff(&tampered_artifact)
        != Err(CoffAdmissionError::ProfileMetadata)
    {
        return Err(String::from("tampered profile metadata was admitted"));
    }
    Ok(())
}

#[test]
fn direct_profile_metadata_rejects_missing_tampered_and_mismatched_identity()
-> Result<(), String> {
    let program = native_program();
    let artifact =
        emit_direct_deopt_coff(&program, direct_deopt_target(HostIsa::X86_64))
            .map_err(|error| error.to_string())?;
    assert_missing_direct_profile_metadata(&artifact)?;
    assert_tampered_direct_profile_metadata(&artifact)?;
    assert_direct_profile_metadata_mismatch(&program, &artifact)?;
    assert_direct_profile_footprint_mismatch(&program, &artifact)
}

#[test]
fn direct_deopt_semantic_admission_rejects_byte_and_target_tampering()
-> Result<(), String> {
    let artifact = emit_direct_deopt_coff(
        &native_program(),
        direct_deopt_target(HostIsa::X86_64),
    )
    .map_err(|error| error.to_string())?;
    let mut mutated = artifact.object().to_vec();
    let opcode = [0xb8u8, 0x01, 0x00, 0x00, 0x00, 0xc3];
    let offset = mutated
        .windows(opcode.len())
        .position(|window| window == opcode)
        .ok_or_else(|| {
            String::from("direct x86 deopt opcode fixture missing")
        })?;
    let first = mutated
        .get_mut(offset)
        .ok_or_else(|| String::from("direct deopt opcode offset invalid"))?;
    *first = 0x90;
    let tampered = UntrustedNativeObjectArtifact::from_emitter_output(
        artifact.key().clone(),
        mutated,
        artifact.target_triple(),
    );
    let _structurally_admitted =
        structurally_admit_coff(&tampered).map_err(|error| {
            format!("tampered structure unexpectedly rejected: {error}")
        })?;
    if verify_direct_deopt_stub(&tampered) != Err(DirectDeoptError::ObjectBytes)
    {
        return Err(String::from("tampered direct deopt opcode was admitted"));
    }

    let mut wrong_backend = base_target_config();
    wrong_backend.backend_id = String::from("not-direct-deopt");
    wrong_backend.backend_revision = DIRECT_DEOPT_BACKEND_REVISION;
    wrong_backend.native_abi_revision = NATIVE_REGION_ABI_REVISION;
    if emit_direct_deopt_coff(
        &native_program(),
        NativeTargetIdentity::new(wrong_backend),
    ) != Err(DirectDeoptError::TargetBackend)
    {
        return Err(String::from("wrong direct-deopt backend was admitted"));
    }
    Ok(())
}

#[test]
fn bootstrap_profile_metadata_requirement_starts_at_revision_two()
-> Result<(), String> {
    let program = native_program();
    let direct =
        emit_direct_deopt_coff(&program, direct_deopt_target(HostIsa::X86_64))
            .map_err(|error| error.to_string())?;
    let revision_two_key =
        NativeArtifactKey::new(&program, native_target(HostIsa::X86_64))
            .map_err(|error| format!("bootstrap v2 key: {error:?}"))?;
    let revision_two = UntrustedNativeObjectArtifact::from_emitter_output(
        revision_two_key,
        direct.object().to_vec(),
        direct.target_triple(),
    );
    let _admitted_revision_two = structurally_admit_coff(&revision_two)
        .map_err(|error| format!("bootstrap v2 metadata rejected: {error}"))?;

    let mut missing = direct.object().to_vec();
    let section = b".mbprof";
    let offset = missing
        .windows(section.len())
        .position(|window| window == section)
        .ok_or_else(|| {
            String::from("bootstrap fixture lacks metadata section")
        })?;
    let marker =
        missing.get_mut(offset.saturating_add(1)).ok_or_else(|| {
            String::from("bootstrap metadata name offset invalid")
        })?;
    *marker = b'x';
    let revision_two_missing =
        UntrustedNativeObjectArtifact::from_emitter_output(
            revision_two.key().clone(),
            missing.clone(),
            direct.target_triple(),
        );
    if structurally_admit_coff(&revision_two_missing)
        != Err(CoffAdmissionError::ProfileMetadata)
    {
        return Err(String::from("bootstrap v2 admitted missing metadata"));
    }

    let revision_one_target = NativeTargetIdentity::new(NativeTargetConfig {
        backend_id: String::from(CLANG_C23_BOOTSTRAP_BACKEND_ID),
        backend_revision: 1,
        host_isa: HostIsa::X86_64,
        host_os: HostOperatingSystem::Windows,
        native_abi_revision: NATIVE_REGION_ABI_REVISION,
        required_features: Vec::new(),
    });
    let revision_one_key =
        NativeArtifactKey::new(&program, revision_one_target)
            .map_err(|error| format!("bootstrap v1 key: {error:?}"))?;
    let revision_one_missing =
        UntrustedNativeObjectArtifact::from_emitter_output(
            revision_one_key,
            missing,
            direct.target_triple(),
        );
    let _admitted_revision_one = structurally_admit_coff(&revision_one_missing)
        .map_err(|error| format!("historical bootstrap v1 changed: {error}"))?;
    Ok(())
}

fn assert_bootstrap_source_profile_metadata(
    program: &RegionEffectProgram,
    source: &str,
) -> Result<(), String> {
    if !source.contains("/* Profile ID: malbolge-2026.2 */") {
        return Err(String::from("native source lost profile identity"));
    }
    let fingerprint_comment =
        format!("/* Profile fingerprint: {} */", program.profile_fingerprint);
    if !source.contains(&fingerprint_comment) {
        return Err(String::from("native source lost profile fingerprint"));
    }
    if !source.contains(r#"#pragma section(".mbprof", read)"#)
        || !source.contains(r#"__declspec(allocate(".mbprof"))"#)
        || !source.contains("/* Backend: clang-c23-bootstrap rev 2 / ABI 1 */")
    {
        return Err(String::from(
            "native source lost bootstrap metadata policy",
        ));
    }
    if rendered_profile_metadata(source)? == expected_profile_metadata(program)?
    {
        Ok(())
    } else {
        Err(String::from("native source profile metadata drifted"))
    }
}

#[test]
fn native_bootstrap_source_is_deterministic_atomic_and_key_bound()
-> Result<(), String> {
    let program = native_program();
    let first = lower_clang_c23(&program, native_target(HostIsa::X86_64))
        .map_err(|error| error.to_string())?;
    let second = lower_clang_c23(&program, native_target(HostIsa::X86_64))
        .map_err(|error| error.to_string())?;
    if first != second {
        return Err(String::from(
            "native bootstrap source is not deterministic",
        ));
    }
    let expected_key =
        NativeArtifactKey::new(&program, native_target(HostIsa::X86_64))
            .map_err(|error| {
                format!("native expected key failed: {error:?}")
            })?;
    if first.key() != &expected_key {
        return Err(String::from("native source lost exact artifact key"));
    }
    let source = first.source();
    assert_bootstrap_source_profile_metadata(&program, source)?;
    let guard = source
        .find("state->memory_words <= MB_U64(7)")
        .ok_or_else(|| String::from("native memory preflight missing"))?;
    if !source.contains("return MB_NATIVE_INVALID_ARGUMENT")
        || !source.contains("return MB_NATIVE_GUARD_MISS")
    {
        return Err(String::from("native status split is missing"));
    }
    let commit = source
        .find("state->output[MB_U64(0)] = MB_U8(66);")
        .ok_or_else(|| String::from("native output commit missing"))?;
    let final_write = source
        .find("state->memory[MB_U64(7)] = MB_U32(10);")
        .ok_or_else(|| String::from("collapsed final memory write missing"))?;
    if guard >= commit || guard >= final_write {
        return Err(String::from("native commit precedes complete preflight"));
    }
    if source.contains("state->memory[MB_U64(7)] = MB_U32(9);") {
        return Err(String::from(
            "intermediate memory state leaked into commit",
        ));
    }
    Ok(())
}

#[test]
fn native_bootstrap_rejects_structural_and_target_mismatches()
-> Result<(), String> {
    let mut broken_chain = native_program();
    let second = broken_chain
        .effects
        .get_mut(1)
        .ok_or_else(|| String::from("native fixture has no second effect"))?;
    second.before.registers.accumulator = 99;
    if lower_clang_c23(&broken_chain, native_target(HostIsa::X86_64))
        != Err(NativeArtifactError::ObservationChain)
    {
        return Err(String::from(
            "broken native observation chain was admitted",
        ));
    }

    let mut post_termination = native_program();
    let first = post_termination
        .effects
        .first_mut()
        .ok_or_else(|| String::from("native fixture has no first effect"))?;
    first.after.termination = Some(Termination::HaltInstruction);
    let post_termination_second = post_termination
        .effects
        .get_mut(1)
        .ok_or_else(|| String::from("native fixture has no second effect"))?;
    post_termination_second.before.termination =
        Some(Termination::HaltInstruction);
    if lower_clang_c23(&post_termination, native_target(HostIsa::X86_64))
        != Err(NativeArtifactError::ObservationChain)
    {
        return Err(String::from(
            "native lowering admitted effects after termination",
        ));
    }

    let mut feature_target = NativeTargetConfig {
        backend_id: String::from(CLANG_C23_BOOTSTRAP_BACKEND_ID),
        backend_revision: CLANG_C23_BOOTSTRAP_BACKEND_REVISION,
        host_isa: HostIsa::X86_64,
        host_os: HostOperatingSystem::Windows,
        native_abi_revision: NATIVE_REGION_ABI_REVISION,
        required_features: vec![String::from("avx2")],
    };
    if lower_clang_c23(
        &native_program(),
        NativeTargetIdentity::new(feature_target.clone()),
    ) != Err(NativeArtifactError::TargetFeatures)
    {
        return Err(String::from("bootstrap claimed unsupported CPU features"));
    }
    feature_target.backend_id = String::from("direct-x86");
    feature_target.required_features.clear();
    if lower_clang_c23(
        &native_program(),
        NativeTargetIdentity::new(feature_target),
    ) != Err(NativeArtifactError::TargetBackend)
    {
        return Err(String::from("wrong native backend identity was admitted"));
    }
    Ok(())
}

#[test]
fn native_bootstrap_compiles_real_x86_64_and_aarch64_coff_objects()
-> Result<(), String> {
    let root = Path::new(env!("CARGO_MANIFEST_DIR"));
    let clang = root.join(".dependencies/llvm/22.1.8/bin/clang.exe");
    if !clang.is_file() {
        return Err(format!("pinned Clang missing: {}", clang.display()));
    }
    let temporary = native_test_directory(root);
    if temporary.exists() {
        remove_dir_all(&temporary)
            .map_err(|error| format!("native temp cleanup: {error}"))?;
    }
    create_dir_all(&temporary)
        .map_err(|error| format!("native temp create: {error}"))?;

    let program = native_program();
    let cases = [
        CoffCompileCase {
            expected_machine: [0x64u8, 0x86u8],
            isa: HostIsa::X86_64,
        },
        CoffCompileCase {
            expected_machine: [0x64u8, 0xaau8],
            isa: HostIsa::AArch64,
        },
    ];
    for case in cases {
        check_compiled_coff_case(&clang, &temporary, &program, case)?;
    }
    remove_dir_all(&temporary)
        .map_err(|error| format!("native temp final cleanup: {error}"))?;
    Ok(())
}

fn check_compiled_coff_case(
    clang: &Path,
    temporary: &Path,
    program: &RegionEffectProgram,
    case: CoffCompileCase,
) -> Result<(), String> {
    let candidate = lower_clang_c23(program, native_target(case.isa))
        .map_err(|error| error.to_string())?;
    let stem = match case.isa {
        HostIsa::X86_64 => "x86_64",
        HostIsa::AArch64 => "aarch64",
    };
    let source_path = temporary.join(format!("{stem}.c"));
    let object_path = temporary.join(format!("{stem}.obj"));
    write(&source_path, candidate.source().as_bytes())
        .map_err(|error| format!("native source write: {error}"))?;
    compile_native_object(
        clang,
        candidate.target_triple(),
        &source_path,
        &object_path,
    )?;
    let object = read(&object_path)
        .map_err(|error| format!("native object read: {error}"))?;
    let artifact =
        UntrustedNativeObjectArtifact::from_compiler_output(&candidate, object)
            .map_err(|error| error.to_string())?;
    if artifact.key() != candidate.key()
        || artifact.target_triple() != candidate.target_triple()
    {
        return Err(String::from("native object lost source identity"));
    }
    if artifact.object().get(..2) != Some(case.expected_machine.as_slice()) {
        return Err(format!("unexpected COFF machine for {stem}"));
    }
    let admitted = structurally_admit_coff(&artifact)
        .map_err(|error| format!("COFF structural admission: {error}"))?;
    if admitted.key() != artifact.key()
        || admitted.object() != artifact.object()
        || admitted.target_triple() != artifact.target_triple()
    {
        return Err(String::from("COFF admission changed artifact identity"));
    }
    if case.isa == HostIsa::X86_64 {
        check_rejected_coff_mutations(&candidate, &artifact)?;
    }
    Ok(())
}

fn check_rejected_coff_mutations(
    source: &execution_native::UntrustedNativeSourceArtifact,
    artifact: &UntrustedNativeObjectArtifact,
) -> Result<(), String> {
    let truncated = artifact.object().iter().copied().take(16).collect();
    let truncated_artifact =
        UntrustedNativeObjectArtifact::from_compiler_output(source, truncated)
            .map_err(|error| error.to_string())?;
    if structurally_admit_coff(&truncated_artifact)
        != Err(CoffAdmissionError::Bounds)
    {
        return Err(String::from("truncated COFF object was admitted"));
    }

    let mut wrong_machine = artifact.object().to_vec();
    let machine = wrong_machine
        .get_mut(..2)
        .ok_or_else(|| String::from("COFF fixture has no machine field"))?;
    machine.copy_from_slice(&0xaa64u16.to_le_bytes());
    let wrong_machine_artifact =
        UntrustedNativeObjectArtifact::from_compiler_output(
            source,
            wrong_machine,
        )
        .map_err(|error| error.to_string())?;
    if structurally_admit_coff(&wrong_machine_artifact)
        != Err(CoffAdmissionError::Machine)
    {
        return Err(String::from("wrong COFF machine was admitted"));
    }

    let mut wrong_entry = artifact.object().to_vec();
    let entry = b"malbolge_native_region_apply";
    let offset = wrong_entry
        .windows(entry.len())
        .position(|window| window == entry)
        .ok_or_else(|| String::from("COFF fixture has no native entry name"))?;
    let first = wrong_entry
        .get_mut(offset)
        .ok_or_else(|| String::from("COFF entry name offset is invalid"))?;
    *first = b'X';
    let wrong_entry_artifact =
        UntrustedNativeObjectArtifact::from_compiler_output(
            source,
            wrong_entry,
        )
        .map_err(|error| error.to_string())?;
    if structurally_admit_coff(&wrong_entry_artifact)
        != Err(CoffAdmissionError::ExtraExternalFunction)
    {
        return Err(String::from("renamed native entry was admitted"));
    }
    Ok(())
}

fn native_test_directory(root: &Path) -> PathBuf {
    root.join(".temp/native-bootstrap-tests")
}

fn compile_native_object(
    clang: &Path,
    target: &str,
    source: &Path,
    object: &Path,
) -> Result<(), String> {
    let output = Command::new(clang)
        .args([
            "-std=c23",
            "-ffreestanding",
            "-nostdinc",
            "-Wall",
            "-Wextra",
            "-Werror",
            "-O2",
            "-c",
            "-target",
            target,
        ])
        .arg(source)
        .arg("-o")
        .arg(object)
        .output()
        .map_err(|error| format!("native Clang launch failed: {error}"))?;
    if output.status.success() {
        return Ok(());
    }
    Err(format!(
        "native Clang failed: {}",
        String::from_utf8_lossy(&output.stderr)
    ))
}

fn direct_normative_sequence_traces() -> Result<Vec<ProfileStepTrace>, String> {
    let base =
        ProfileMachine::from_source(current_profile(), b"(=%`qL", Vec::new())
            .map_err(|error| format!("direct sequence base load: {error}"))?;
    let mut memory = base.snapshot_state().memory().to_vec();
    *memory
        .get_mut(5)
        .ok_or_else(|| String::from("direct sequence code cell 5 missing"))? =
        34;
    let output_cell = (33u32..=126u32)
        .find(|cell| decode_profile_instruction(*cell, 6) == Some(b'/'))
        .ok_or_else(|| String::from("phase-six output cell missing"))?;
    *memory
        .get_mut(6)
        .ok_or_else(|| String::from("direct sequence code cell 6 missing"))? =
        output_cell;
    *memory
        .get_mut(7)
        .ok_or_else(|| String::from("direct sequence data cell 7 missing"))? =
        10;
    let io = ProfileMachineIoState::new(Vec::new(), 0, Vec::new(), None)
        .map_err(|error| format!("direct sequence IO: {error}"))?;
    let state = ProfileMachineState::new(
        current_profile(),
        memory,
        ProfileRegisters {
            accumulator: 20,
            code_pointer: 5,
            data_pointer: 7,
        },
        io,
    )
    .map_err(|error| format!("direct sequence state: {error}"))?;
    let mut machine = ProfileMachine::from_snapshot(state);
    let mut traces = Vec::new();
    let outcome = machine
        .run_traced(2, &mut |trace: &ProfileStepTrace| traces.push(*trace))
        .map_err(|error| format!("direct sequence trace: {error}"))?;
    if outcome != (RunOutcome::BudgetExhausted { steps: 2 }) {
        return Err(format!("direct sequence outcome mismatch: {outcome:?}"));
    }
    Ok(traces)
}

fn direct_normative_sequence_programs()
-> Result<Vec<RegionEffectProgram>, String> {
    direct_normative_sequence_traces()?
        .iter()
        .map(|trace| {
            RegionEffectProgram::from_profile_step_trace(trace).map_err(
                |error| format!("direct sequence projection: {error:?}"),
            )
        })
        .collect()
}

#[test]
fn normative_trace_sequence_selects_mixed_exact_direct_steps()
-> Result<(), String> {
    let traces = direct_normative_sequence_traces()?;
    let programs = direct_normative_sequence_programs()?;
    let [first_program, second_program] = programs.as_slice() else {
        return Err(String::from("direct sequence program length mismatch"));
    };
    let [first_trace, second_trace] = traces.as_slice() else {
        return Err(String::from("direct sequence trace length mismatch"));
    };
    let second_fetch = second_trace
        .memory_reads
        .fetch
        .ok_or_else(|| String::from("direct sequence second fetch missing"))?;
    if first_program.memory_live_ins
        != [MemoryLiveIn { address: 5, value: 34 }, MemoryLiveIn {
            address: 7,
            value: 10,
        }]
        || second_program.memory_live_ins
            != [MemoryLiveIn {
                address: second_fetch.address,
                value: second_fetch.value,
            }]
        || first_trace.decoded != Some(b'*')
        || second_trace.decoded != Some(b'/')
        || second_trace.output != Some(0xd6)
    {
        let detail = format!("traces={traces:?} programs={programs:?}");
        return Err(format!("direct sequence VM evidence mismatch: {detail}"));
    }
    for isa in [HostIsa::X86_64, HostIsa::AArch64] {
        let plan = select_verified_direct_sequence(
            &programs,
            safe_rust_profiled_capability(),
            HostOperatingSystem::Windows,
            isa,
        )
        .map_err(|error| format!("direct sequence select: {error}"))?;
        let [rotate, output] = plan.artifacts() else {
            return Err(format!("direct sequence plan length: {plan:?}"));
        };
        if plan.len() != 2
            || plan.entry() != first_trace.before
            || plan.exit() != second_trace.after
            || plan.outcome() != (RunOutcome::BudgetExhausted { steps: 2 })
            || rotate.kind() != DirectNativeKind::Rotate
            || output.kind() != DirectNativeKind::Output
        {
            return Err(format!("direct sequence plan mismatch: {plan:?}"));
        }
    }
    Ok(())
}

#[test]
fn trace_projection_rejects_conflicting_same_address_reads()
-> Result<(), String> {
    let mut trace = direct_normative_sequence_traces()?
        .first()
        .copied()
        .ok_or_else(|| String::from("direct sequence trace missing"))?;
    trace.memory_reads.encryption =
        Some(ProfileMemoryRead { address: 5, value: 35 });
    let result = RegionEffectProgram::from_profile_step_trace(&trace);
    if result != Err(StepProgramProjectionError::ConflictingMemoryRead) {
        return Err(format!("conflicting trace read admitted: {result:?}"));
    }
    Ok(())
}

fn assert_projection_error(
    trace: &ProfileStepTrace,
    expected: StepProgramProjectionError,
) -> Result<(), String> {
    let observed = RegionEffectProgram::from_profile_step_trace(trace);
    if observed == Err(expected) {
        Ok(())
    } else {
        let detail = format!("observed={observed:?} expected={expected:?}");
        Err(format!("trace projection error mismatch: {detail}"))
    }
}

#[test]
fn trace_projection_rejects_inconsistent_evidence() -> Result<(), String> {
    let baseline = direct_normative_sequence_traces()?
        .first()
        .copied()
        .ok_or_else(|| String::from("direct sequence trace missing"))?;

    let mut missing_fetch = baseline;
    missing_fetch.memory_reads.fetch = None;
    assert_projection_error(
        &missing_fetch,
        StepProgramProjectionError::MissingFetch,
    )?;

    let mut wrong_address = baseline;
    let fetch = wrong_address
        .memory_reads
        .fetch
        .as_mut()
        .ok_or_else(|| String::from("direct sequence fetch missing"))?;
    fetch.address = fetch.address.saturating_add(1);
    assert_projection_error(
        &wrong_address,
        StepProgramProjectionError::FetchAddress,
    )?;

    let mut wrong_value = baseline;
    wrong_value.fetched_cell = wrong_value.fetched_cell.map(|value| value ^ 1);
    assert_projection_error(
        &wrong_value,
        StepProgramProjectionError::FetchValue,
    )?;

    let mut outcome = baseline;
    outcome.after.termination = Some(Termination::HaltInstruction);
    assert_projection_error(&outcome, StepProgramProjectionError::Outcome)?;

    let mut rejected = baseline;
    rejected.result = Err(ProfileMachineError::TranslationTableInvariant);
    assert_projection_error(
        &rejected,
        StepProgramProjectionError::RejectedTrace,
    )?;

    let mut terminated = baseline;
    terminated.before.termination = Some(Termination::HaltInstruction);
    assert_projection_error(
        &terminated,
        StepProgramProjectionError::TerminatedEntry,
    )
}

#[test]
fn direct_sequence_rejects_non_unit_programs() -> Result<(), String> {
    let mut programs = direct_normative_sequence_programs()?;
    programs
        .get_mut(0)
        .ok_or_else(|| String::from("first shape program missing"))?
        .step_budget = 2;
    let result = select_verified_direct_sequence(
        &programs,
        safe_rust_profiled_capability(),
        HostOperatingSystem::Windows,
        HostIsa::X86_64,
    );
    if result == Err(DirectSequenceError::ProgramShape { index: 0 }) {
        Ok(())
    } else {
        Err(format!("non-unit direct sequence admitted: {result:?}"))
    }
}

#[test]
fn direct_sequence_rejects_empty_discontinuous_and_profile_mixed_shapes()
-> Result<(), String> {
    let empty = select_verified_direct_sequence(
        &[],
        safe_rust_profiled_capability(),
        HostOperatingSystem::Windows,
        HostIsa::X86_64,
    );
    if empty != Err(DirectSequenceError::Empty) {
        return Err(format!("empty direct sequence admitted: {empty:?}"));
    }

    let mut discontinuous = direct_normative_sequence_programs()?;
    let second = discontinuous.get_mut(1).ok_or_else(|| {
        String::from("second direct sequence program missing")
    })?;
    let effect = second
        .effects
        .first_mut()
        .ok_or_else(|| String::from("second direct sequence effect missing"))?;
    effect.before.registers.accumulator ^= 1;
    let chain_result = select_verified_direct_sequence(
        &discontinuous,
        safe_rust_profiled_capability(),
        HostOperatingSystem::Windows,
        HostIsa::X86_64,
    );
    if chain_result != Err(DirectSequenceError::ObservationChain { index: 1 }) {
        return Err(format!(
            "discontinuous direct sequence admitted: {chain_result:?}"
        ));
    }

    let mut profile_mixed = direct_normative_sequence_programs()?;
    profile_mixed
        .get_mut(1)
        .ok_or_else(|| String::from("second profile program missing"))?
        .profile_id
        .push_str("-other");
    let profile_result = select_verified_direct_sequence(
        &profile_mixed,
        safe_rust_profiled_capability(),
        HostOperatingSystem::Windows,
        HostIsa::X86_64,
    );
    if profile_result != Err(DirectSequenceError::ProfileMismatch { index: 1 })
    {
        return Err(format!(
            "profile-mixed direct sequence admitted: {profile_result:?}"
        ));
    }
    Ok(())
}

#[test]
fn direct_sequence_preserves_step_selection_errors() -> Result<(), String> {
    let programs = direct_normative_sequence_programs()?;
    let result = select_verified_direct_sequence(
        &programs,
        safe_rust_profiled_capability(),
        HostOperatingSystem::Linux,
        HostIsa::X86_64,
    );
    let Err(DirectSequenceError::Step { error, index: 0 }) = result else {
        return Err(format!("direct sequence step error changed: {result:?}"));
    };
    if *error == DirectSelectionError::TargetFormat {
        Ok(())
    } else {
        Err(format!("direct sequence target error changed: {error}"))
    }
}

#[test]
fn direct_sequence_rejects_hidden_deopt_and_post_termination_steps()
-> Result<(), String> {
    let mut hidden_deopt = direct_normative_sequence_programs()?;
    hidden_deopt
        .get_mut(1)
        .ok_or_else(|| String::from("second deopt program missing"))?
        .memory_live_ins
        .clear();
    let deopt_result = select_verified_direct_sequence(
        &hidden_deopt,
        safe_rust_profiled_capability(),
        HostOperatingSystem::Windows,
        HostIsa::X86_64,
    );
    if deopt_result != Err(DirectSequenceError::Deoptimization { index: 1 }) {
        return Err(format!(
            "hidden deopt direct sequence admitted: {deopt_result:?}"
        ));
    }

    let terminal = [direct_halt_fetch_program(), direct_no_operation_program()];
    let terminal_result = select_verified_direct_sequence(
        &terminal,
        safe_rust_profiled_capability(),
        HostOperatingSystem::Windows,
        HostIsa::X86_64,
    );
    if terminal_result
        != Err(DirectSequenceError::TerminationBeforeEnd { index: 0 })
    {
        return Err(format!(
            "post-termination direct step admitted: {terminal_result:?}"
        ));
    }
    Ok(())
}
