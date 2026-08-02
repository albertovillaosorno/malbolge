// File:
//   - tiered_execution.rs
// Path:
//   - tests/tiered_execution.rs
//
// Copyright:
//   - Copyright (c) 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - MIT
// Confidential:
//   - false
// License-File:
//   - LICENSE
// Path-Rule:
//   - All paths in this header are repository-root relative.
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
// Related documents:
// - execution/ir/README.md
// - execution/cache/README.md
//
// Large file:
//   - false
//

//! Product tiered-execution identity and cache-key conformance.

#[path = "../execution/cache/main.rs"]
pub mod execution_cache;
#[path = "../execution/ir/main.rs"]
pub mod execution_ir;
#[path = "../execution/native/main.rs"]
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
    TargetProfileRequirement,
};
use execution_native::{
    CLANG_C23_BOOTSTRAP_BACKEND_ID, CLANG_C23_BOOTSTRAP_BACKEND_REVISION,
    CachedPreflightedExecutionTier, CoffAdmissionError,
    DIRECT_DEOPT_BACKEND_ID, DIRECT_DEOPT_BACKEND_REVISION,
    DIRECT_HALT_REGISTERS_BACKEND_ID, DIRECT_HALT_REGISTERS_BACKEND_REVISION,
    DIRECT_INITIAL_HALT_BACKEND_ID, DIRECT_INITIAL_HALT_BACKEND_REVISION,
    DirectCacheDisposition, DirectDeoptError, DirectHaltRegistersError,
    DirectHost, DirectInitialHaltError, DirectNativeKind, DirectSelectionError,
    NATIVE_REGION_ABI_REVISION, NativeArtifactError, PreflightedExecutionTier,
    UntrustedNativeObjectArtifact, VerifiedDirectNativeCache,
    emit_direct_deopt_coff, emit_direct_halt_registers_coff,
    emit_direct_initial_halt_coff, lower_clang_c23,
    select_cached_preflighted_execution_tier,
    select_preflighted_execution_tier, select_verified_direct_native,
    structurally_admit_coff, verify_direct_deopt_stub,
    verify_direct_halt_registers, verify_direct_initial_halt,
};
use malbolge::{
    ProfileMachineObservation, ProfileMemoryDelta, ProfileMemoryWrite,
    ProfileRegisters, ProfileRequirementErrorKind, RunOutcome, Termination,
    TraceInput, current_profile, preflight_profile,
    preflight_runtime_requirement, safe_rust_classic_capability,
    safe_rust_profiled_capability,
};

#[derive(Clone, Copy)]
struct CoffCompileCase {
    expected_machine: [u8; 2],
    isa: HostIsa,
}

type CollisionKeys = (NativeArtifactKey, NativeArtifactKey);

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
        input_consumed: 0,
        output_len: 0,
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

#[test]
fn direct_selector_chooses_fast_path_or_verified_deopt_deterministically()
-> Result<(), String> {
    for isa in [HostIsa::X86_64, HostIsa::AArch64] {
        let fast = select_verified_direct_native(
            &direct_initial_halt_program(),
            safe_rust_profiled_capability(),
            HostOperatingSystem::Windows,
            isa,
        )
        .map_err(|error| error.to_string())?;
        if fast.kind() != DirectNativeKind::InitialHalt
            || fast.key().target().backend_id()
                != DIRECT_INITIAL_HALT_BACKEND_ID
            || fast.object().is_empty()
        {
            return Err(String::from(
                "direct selector missed initial-halt fast path",
            ));
        }

        let register_halt = select_verified_direct_native(
            &direct_halt_registers_program(),
            safe_rust_profiled_capability(),
            HostOperatingSystem::Windows,
            isa,
        )
        .map_err(|error| error.to_string())?;
        if register_halt.kind() != DirectNativeKind::HaltRegisters
            || register_halt.key().target().backend_id()
                != DIRECT_HALT_REGISTERS_BACKEND_ID
            || register_halt.object().is_empty()
        {
            return Err(String::from(
                "direct selector missed register-bound halt fast path",
            ));
        }

        let fallback = select_verified_direct_native(
            &native_program(),
            safe_rust_profiled_capability(),
            HostOperatingSystem::Windows,
            isa,
        )
        .map_err(|error| error.to_string())?;
        if fallback.kind() != DirectNativeKind::Deopt
            || fallback.key().target().backend_id() != DIRECT_DEOPT_BACKEND_ID
            || fallback.object().is_empty()
        {
            return Err(String::from(
                "direct selector failed verified deopt fallback",
            ));
        }
        if fast.target_triple() != fallback.target_triple() {
            return Err(String::from(
                "direct selector changed target triple by tier",
            ));
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

#[test]
fn direct_fast_paths_reject_undersized_profile_capacity() -> Result<(), String>
{
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
    if !source.contains("/* Profile ID: malbolge-2026.2 */") {
        return Err(String::from("native source lost profile identity"));
    }
    let fingerprint_comment =
        format!("/* Profile fingerprint: {} */", program.profile_fingerprint);
    if !source.contains(&fingerprint_comment) {
        return Err(String::from("native source lost profile fingerprint"));
    }
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
