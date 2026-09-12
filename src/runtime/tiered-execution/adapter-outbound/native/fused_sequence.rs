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
//   - Inputs: one exact `VerifiedDirectSequencePlan`.
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
//   - Ordered one-step artifact identity remains explicit provenance.
//

//! Region-wide identity admission for verified direct-native sequences.

use std::collections::BTreeMap;
use std::fmt::{Display, Formatter, Result as FormatResult};

use malbolge::{MemoryLiveIn, ProfileMemoryWrite, RegionEffectProgram};

use super::direct::VerifiedDirectSequencePlan;
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

/// Canonical fused-region program plus exact source and target identities.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct DirectFusedSequenceAdmission {
    key: NativeArtifactKey,
    program: RegionEffectProgram,
    source_key: NativeExecutableSequenceKey,
    source_plan: VerifiedDirectSequencePlan,
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
            Self::SequenceLength { steps } => write!(
                f,
                "fused direct sequence requires two steps; received {steps}",
            ),
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
        &self.source_key
    }

    /// Returns the complete independently verified one-step source evidence.
    #[must_use]
    pub const fn source_plan(&self) -> &VerifiedDirectSequencePlan {
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
    if plan.len() < 2 {
        return Err(DirectFusedSequenceAdmissionError::SequenceLength {
            steps: plan.len(),
        });
    }
    let program = compose_fused_program(plan)?;
    let target = fused_target(plan)?;
    let key = NativeArtifactKey::new(&program, target)?;
    Ok(DirectFusedSequenceAdmission {
        key,
        program,
        source_key: NativeExecutableSequenceKey::from_plan(plan),
        source_plan: plan.clone(),
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
        .is_some_and(|value| *value != write.before)
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
    plan: &VerifiedDirectSequencePlan,
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
    plan: &VerifiedDirectSequencePlan,
) -> Result<NativeTargetIdentity, DirectFusedSequenceAdmissionError> {
    let first = plan
        .artifacts()
        .first()
        .ok_or(DirectFusedSequenceAdmissionError::Empty)?
        .key()
        .target();
    let mut required_features = Vec::new();
    for (index, artifact) in plan.artifacts().iter().enumerate() {
        let target = artifact.key().target();
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
