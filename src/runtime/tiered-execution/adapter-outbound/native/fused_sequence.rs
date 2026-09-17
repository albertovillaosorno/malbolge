// Copyright:
//   - Copyright © 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - MIT
// Confidential:
//   - false
// License-File:
//   - LICENSE-MIT
//
// Boundary-Contract:
// - Owns:
//   - Fused-region identity admission for already verified direct sequences.
// - Must-Not:
//   - Emit object bytes, allocate executable memory, invoke code, or replace
//   - one-step semantic verification.
// - Allows:
//   - Inputs: one exact cached or uncached verified direct sequence plan.
//   - Outputs: one canonical multieffect program, fused artifact key, and
//     ordered source-artifact provenance.
//   - Side effects: process-local allocation only.
// - Split-When:
//   - Fused byte emission or independent fused-object verification is added.
// - Merge-When:
//   - One reviewed fused backend owns both admission and candidate
//     verification.
// - Summary:
//   - Binds a verified direct sequence to one exact region-wide native
//     identity.
// - Description:
//   - Later reads satisfied by prior writes become internal dependencies;
//     contradictory full-region dependencies fail closed.
// - Usage:
//   - Admit a verified one-step sequence before any future fused emission.
// - Defaults:
//   - Ordered one-step artifact identity remains explicit provenance; object
//   - bytes are not retained by fused admission.
//

//! Region-wide identity admission for verified direct-native sequences.

use std::collections::BTreeMap;
use std::fmt::{Display, Formatter, Result as FormatResult};

use malbolge::{
    MemoryLiveIn, ProfileMachineObservation, ProfileMemoryWrite,
    RegionEffectProgram, RunOutcome,
};

use super::direct::{
    CachedVerifiedDirectSequencePlan, DirectNativeKind,
    VerifiedDirectSequencePlan,
};
use super::executable_cache::NativeExecutableSequenceKey;
use crate::execution_cache::{
    NativeArtifactKey, NativeIdentityError, NativeTargetConfig,
    NativeTargetIdentity,
};

/// Backend identity reserved for region-wide direct sequence fusion.
pub const DIRECT_FUSED_SEQUENCE_BACKEND_ID: &str = "direct-fused-sequence";
/// First region-wide direct sequence identity revision.
pub const DIRECT_FUSED_SEQUENCE_BACKEND_REVISION: u32 = 1;

/// Failure while binding one verified direct sequence to fused-region identity.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum DirectFusedSequenceAdmissionError {
    /// A verified source plan unexpectedly contains no semantic step.
    Empty,
    /// Source one-step programs use different canonical IR format revisions.
    FormatVersion {
        /// Zero-based source step whose format revision differs.
        index: usize,
    },
    /// Region-wide canonical native identity could not be constructed.
    Identity(NativeIdentityError),
    /// Ordered memory evidence cannot describe one fully applied fused region.
    MemoryDependency {
        /// Exact guest-memory address whose full-region value conflicts.
        address: u32,
        /// Zero-based source step exposing the conflict.
        index: usize,
    },
    /// A verified source position no longer has exact one-step program shape.
    ProgramShape {
        /// Zero-based source position that is no longer exactly one step.
        index: usize,
    },
    /// Fusion requires at least two independently verified source steps.
    SequenceLength {
        /// Number of verified source steps presented for fusion.
        steps: usize,
    },
    /// Source artifacts disagree on host, ISA, or native ABI assumptions.
    TargetAssumption {
        /// Zero-based source artifact whose host assumptions differ.
        index: usize,
    },
}

/// Compact immutable provenance retained from independently verified steps.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct DirectFusedSequenceSourcePlan {
    artifact_kinds: Vec<DirectNativeKind>,
    entry: ProfileMachineObservation,
    exit: ProfileMachineObservation,
    outcome: RunOutcome,
    programs: Vec<RegionEffectProgram>,
    source_key: NativeExecutableSequenceKey,
}

/// Canonical fused-region program plus exact source and target identities.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct DirectFusedSequenceAdmission {
    key: NativeArtifactKey,
    program: RegionEffectProgram,
    source_plan: DirectFusedSequenceSourcePlan,
}

impl Display for DirectFusedSequenceAdmissionError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::Empty => f.write_str("fused direct sequence is empty"),
            Self::FormatVersion { index } => write!(
                f,
                "fused direct sequence format changed at step {index}",
            ),
            Self::Identity(_error) => f.write_str(
                "fused direct sequence identity construction failed",
            ),
            Self::MemoryDependency { address, index } => write!(
                f,
                "fused direct sequence memory dependency at step {index}, \
                 address {address}",
            ),
            Self::SequenceLength { steps } => {
                write!(f, "fused direct sequence has {steps} source steps")
            },
            Self::ProgramShape { index } => write!(
                f,
                "fused direct sequence lost one-step shape at step {index}",
            ),
            Self::TargetAssumption { index } => write!(
                f,
                "fused direct sequence target changed at step {index}",
            ),
        }
    }
}

impl From<NativeIdentityError> for DirectFusedSequenceAdmissionError {
    fn from(error: NativeIdentityError) -> Self {
        Self::Identity(error)
    }
}

impl DirectFusedSequenceSourcePlan {
    /// Returns each reviewed direct template in semantic execution order.
    #[must_use]
    pub fn artifact_kinds(&self) -> &[DirectNativeKind] {
        &self.artifact_kinds
    }

    /// Returns the exact first-step entry observation.
    #[must_use]
    pub const fn entry(&self) -> ProfileMachineObservation {
        self.entry
    }

    /// Returns the exact final-step exit observation.
    #[must_use]
    pub const fn exit(&self) -> ProfileMachineObservation {
        self.exit
    }

    fn from_cached_plan(plan: &CachedVerifiedDirectSequencePlan) -> Self {
        Self {
            artifact_kinds: plan
                .artifacts()
                .iter()
                .map(|artifact| artifact.kind())
                .collect(),
            entry: plan.entry(),
            exit: plan.exit(),
            outcome: plan.outcome(),
            programs: plan.programs().to_vec(),
            source_key: NativeExecutableSequenceKey::from_cached_plan(plan),
        }
    }

    fn from_verified_plan(plan: &VerifiedDirectSequencePlan) -> Self {
        Self {
            artifact_kinds: plan
                .artifacts()
                .iter()
                .map(super::direct::VerifiedDirectNativeArtifact::kind)
                .collect(),
            entry: plan.entry(),
            exit: plan.exit(),
            outcome: plan.outcome(),
            programs: plan.programs().to_vec(),
            source_key: NativeExecutableSequenceKey::from_plan(plan),
        }
    }

    /// Returns whether the retained source sequence contains no steps.
    #[must_use]
    pub const fn is_empty(&self) -> bool {
        self.programs.is_empty()
    }

    /// Returns the number of independently verified semantic source steps.
    #[must_use]
    pub const fn len(&self) -> usize {
        self.programs.len()
    }

    /// Returns the exact regional outcome retained from source verification.
    #[must_use]
    pub const fn outcome(&self) -> RunOutcome {
        self.outcome
    }

    /// Returns exact one-step programs in semantic execution order.
    #[must_use]
    pub fn programs(&self) -> &[RegionEffectProgram] {
        &self.programs
    }

    /// Returns exact ordered one-step artifact identity.
    #[must_use]
    pub const fn source_key(&self) -> &NativeExecutableSequenceKey {
        &self.source_key
    }
}

impl DirectFusedSequenceAdmission {
    /// Returns the exact region-wide native artifact identity.
    #[must_use]
    pub const fn key(&self) -> &NativeArtifactKey {
        &self.key
    }

    /// Returns the canonical multieffect program bound by `key`.
    #[must_use]
    pub const fn program(&self) -> &RegionEffectProgram {
        &self.program
    }

    /// Returns ordered one-step artifact identity retained as provenance.
    #[must_use]
    pub const fn source_key(&self) -> &NativeExecutableSequenceKey {
        self.source_plan.source_key()
    }

    /// Returns compact independently verified one-step source provenance.
    #[must_use]
    pub const fn source_plan(&self) -> &DirectFusedSequenceSourcePlan {
        &self.source_plan
    }
}

/// Admits one already verified direct sequence as a fused-region identity.
///
/// This does not emit or verify fused machine bytes. It composes only the
/// already admitted semantic steps, derives region-entry memory live-ins, and
/// creates a distinct region-wide target key while retaining ordered one-step
/// artifact identity as provenance.
///
/// # Errors
///
/// Returns [`DirectFusedSequenceAdmissionError`] when source assumptions cannot
/// describe one exact fully applied region or canonical identity fails.
pub fn admit_fused_direct_sequence(
    plan: &VerifiedDirectSequencePlan,
) -> Result<DirectFusedSequenceAdmission, DirectFusedSequenceAdmissionError> {
    admit_source_plan(DirectFusedSequenceSourcePlan::from_verified_plan(plan))
}

/// Admits one cache-aware verified sequence as fused-region identity.
///
/// The retained provenance copies only one-step IR, reviewed template kinds,
/// observations, outcome, and exact artifact keys. Verified object bytes remain
/// shared by the caller-owned cache and are not cloned into fused authority.
///
/// # Errors
///
/// Returns [`DirectFusedSequenceAdmissionError`] under the same fail-closed
/// dependency and target assumptions as [`admit_fused_direct_sequence`].
pub fn admit_cached_fused_direct_sequence(
    plan: &CachedVerifiedDirectSequencePlan,
) -> Result<DirectFusedSequenceAdmission, DirectFusedSequenceAdmissionError> {
    admit_source_plan(DirectFusedSequenceSourcePlan::from_cached_plan(plan))
}

pub(super) fn readmit_fused_direct_sequence(
    plan: &DirectFusedSequenceSourcePlan,
) -> Result<DirectFusedSequenceAdmission, DirectFusedSequenceAdmissionError> {
    admit_source_plan(plan.clone())
}

fn admit_source_plan(
    source_plan: DirectFusedSequenceSourcePlan,
) -> Result<DirectFusedSequenceAdmission, DirectFusedSequenceAdmissionError> {
    if source_plan.len() < 2 {
        return Err(DirectFusedSequenceAdmissionError::SequenceLength {
            steps: source_plan.len(),
        });
    }
    let program = compose_fused_program(&source_plan)?;
    let target = fused_target(&source_plan)?;
    let key = NativeArtifactKey::new(&program, target)?;
    Ok(DirectFusedSequenceAdmission {
        key,
        program,
        source_plan,
    })
}

fn admit_live_in(
    current: &mut BTreeMap<u32, u32>,
    entry: &mut BTreeMap<u32, u32>,
    live_in: MemoryLiveIn,
    index: usize,
) -> Result<(), DirectFusedSequenceAdmissionError> {
    match current.get(&live_in.address) {
        Some(value) if *value != live_in.value => {
            Err(DirectFusedSequenceAdmissionError::MemoryDependency {
                address: live_in.address,
                index,
            })
        },
        Some(_value) => Ok(()),
        None => {
            let _current_previous =
                current.insert(live_in.address, live_in.value);
            let _entry_previous = entry.insert(live_in.address, live_in.value);
            Ok(())
        },
    }
}

fn admit_write(
    current: &mut BTreeMap<u32, u32>,
    write: ProfileMemoryWrite,
    index: usize,
) -> Result<(), DirectFusedSequenceAdmissionError> {
    if current
        .get(&write.address)
        .is_none_or(|value| *value != write.before)
    {
        return Err(DirectFusedSequenceAdmissionError::MemoryDependency {
            address: write.address,
            index,
        });
    }
    let _previous = current.insert(write.address, write.after);
    Ok(())
}

fn compose_fused_program(
    plan: &DirectFusedSequenceSourcePlan,
) -> Result<RegionEffectProgram, DirectFusedSequenceAdmissionError> {
    let first = plan
        .programs()
        .first()
        .ok_or(DirectFusedSequenceAdmissionError::Empty)?;
    let mut current_memory = BTreeMap::new();
    let mut entry_live_ins = BTreeMap::new();
    let mut effects = Vec::with_capacity(plan.len());
    for (index, program) in plan.programs().iter().enumerate() {
        if program.format_version != first.format_version {
            return Err(DirectFusedSequenceAdmissionError::FormatVersion {
                index,
            });
        }
        let [effect] = program.effects.as_slice() else {
            return Err(DirectFusedSequenceAdmissionError::ProgramShape {
                index,
            });
        };
        for live_in in program.memory_live_ins.iter().copied() {
            admit_live_in(
                &mut current_memory,
                &mut entry_live_ins,
                live_in,
                index,
            )?;
        }
        for write in [effect.memory_delta.data, effect.memory_delta.encryption]
            .into_iter()
            .flatten()
        {
            admit_write(&mut current_memory, write, index)?;
        }
        effects.push(*effect);
    }
    Ok(RegionEffectProgram {
        effects,
        format_version: first.format_version,
        memory_live_ins: entry_live_ins
            .into_iter()
            .map(|(address, value)| MemoryLiveIn { address, value })
            .collect(),
        outcome: plan.outcome(),
        profile_fingerprint: first.profile_fingerprint.clone(),
        profile_id: first.profile_id.clone(),
        profile_requirement: first.profile_requirement.clone(),
        step_budget: plan.len(),
    })
}

fn fused_target(
    plan: &DirectFusedSequenceSourcePlan,
) -> Result<NativeTargetIdentity, DirectFusedSequenceAdmissionError> {
    let first = plan
        .source_key()
        .artifact_keys()
        .first()
        .ok_or(DirectFusedSequenceAdmissionError::Empty)?
        .target();
    let mut required_features = Vec::new();
    for (index, artifact_key) in
        plan.source_key().artifact_keys().iter().enumerate()
    {
        let target = artifact_key.target();
        if target.host_isa() != first.host_isa()
            || target.host_os() != first.host_os()
            || target.native_abi_revision() != first.native_abi_revision()
        {
            return Err(DirectFusedSequenceAdmissionError::TargetAssumption {
                index,
            });
        }
        required_features.extend(target.required_features().iter().cloned());
    }
    Ok(NativeTargetIdentity::new(NativeTargetConfig {
        backend_id: String::from(DIRECT_FUSED_SEQUENCE_BACKEND_ID),
        backend_revision: DIRECT_FUSED_SEQUENCE_BACKEND_REVISION,
        host_isa: first.host_isa(),
        host_os: first.host_os(),
        native_abi_revision: first.native_abi_revision(),
        required_features,
    }))
}
