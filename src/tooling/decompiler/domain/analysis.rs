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
//   - Profile-admitted initial Malbolge reverse-engineering annotations.
// - Must-Not:
//   - Claim indirect targets, future mutations, or original source recovery.
// - Allows:
//   - Inputs: one canonical profile and one admitted source artifact.
//   - Outputs: typed initial decode, state effects, and control-flow classes.
//   - Side effects: process-local allocation only.
// - Split-When:
//   - Dynamic trace or mutation-history analysis gains an independent
//     lifecycle.
// - Merge-When:
//   - Another domain model owns the same reverse-engineering facts.
// - Summary:
//   - Typed initial-state analysis for self-modifying Malbolge programs.
// - Description:
//   - Classifies only facts justified before execution mutates code or
//     pointers.
// - Usage:
//   - Consumed by readable decompiler representations and tests.
// - Defaults:
//   - Indirect targets remain unresolved and later decode is not predicted.
//

//! Typed initial-state reverse-engineering analysis.

use std::fmt::{Display, Formatter, Result as FormatResult};

use malbolge::{
    ProfileDescriptor, ProfileMachine, ProfileMachineError,
    is_source_whitespace,
};

const INITIAL_TRANSLATION: &[u8; 94] =
    b"+b(29e*j1VMEKLyC})8&m#~W>qxdRp0wkrUo[D7,XTcA\"lI\
.v%{gJh4G\\-=O@5`_3i<?Z';FNQuY]szf$!BS/|t:Pn6^Ha";

/// Initial control-flow classification before self-modification.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ControlFlow {
    /// Execution stops when this cell is reached in its initial form.
    Halt,
    /// The next code pointer is loaded indirectly from the current data cell.
    IndirectCodePointer,
    /// The committed step advances to the sequential successor.
    Sequential,
}

impl ControlFlow {
    /// Stable textual representation used by readable reports.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Halt => "halt",
            Self::IndirectCodePointer => "indirect-code-pointer-from-data",
            Self::Sequential => "sequential",
        }
    }
}

/// Effect on the data pointer or pointed-to memory.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum DataEffect {
    /// The instruction does not access the data cell.
    None,
    /// The current data cell is read without a data write.
    Read,
    /// The current data cell is read and rewritten.
    ReadWrite,
    /// The data pointer is replaced with the current data-cell value.
    ReplacePointer,
}

impl DataEffect {
    /// Stable textual representation used by readable reports.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::None => "none",
            Self::Read => "read-data-cell",
            Self::ReadWrite => "read-write-data-cell",
            Self::ReplacePointer => "replace-data-pointer-from-data",
        }
    }
}

/// Effect on the accumulator register.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum AccumulatorEffect {
    /// The instruction does not observe or change the accumulator.
    None,
    /// The instruction observes the accumulator without changing it.
    Read,
    /// The instruction reads and replaces the accumulator.
    ReadWrite,
    /// The instruction replaces the accumulator.
    Write,
}

impl AccumulatorEffect {
    /// Stable textual representation used by readable reports.
    #[must_use]
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::None => "none",
            Self::Read => "read",
            Self::ReadWrite => "read-write",
            Self::Write => "write",
        }
    }
}

/// One source cell's initial decoded annotation.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct InitialCell {
    /// Effect on the accumulator.
    pub accumulator: AccumulatorEffect,
    /// Initial control-flow class.
    pub control_flow: ControlFlow,
    /// Effect on the data pointer or data cell.
    pub data: DataEffect,
    /// Decoded instruction byte under the initial code-pointer phase.
    pub decoded: u8,
    /// Source position after ignored whitespace is removed.
    pub position: usize,
    /// Whether a committed non-halt step self-encrypts a code cell.
    pub post_step_encryption: bool,
    /// Raw admitted source byte.
    pub raw: u8,
}

/// Profile-bound initial reverse-engineering report.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct InitialAnalysis {
    cells: Vec<InitialCell>,
    profile_fingerprint: &'static str,
    profile_id: &'static str,
    profile_version: &'static str,
    source: Vec<u8>,
}

impl InitialAnalysis {
    /// Initial cell annotations in source order.
    #[must_use]
    pub fn cells(&self) -> &[InitialCell] {
        &self.cells
    }

    /// Selected canonical profile fingerprint.
    #[must_use]
    pub const fn profile_fingerprint(&self) -> &'static str {
        self.profile_fingerprint
    }

    /// Selected canonical profile ID.
    #[must_use]
    pub const fn profile_id(&self) -> &'static str {
        self.profile_id
    }

    /// Selected canonical profile version.
    #[must_use]
    pub const fn profile_version(&self) -> &'static str {
        self.profile_version
    }

    /// Whitespace-normalized admitted source bytes.
    #[must_use]
    pub fn source(&self) -> &[u8] {
        &self.source
    }
}

/// Initial analysis failure.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum AnalysisError {
    /// Input source is invalid for the selected profile.
    InvalidSource(ProfileMachineError),
    /// A validated source position could not be represented.
    PositionOverflow,
}

impl Display for AnalysisError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::InvalidSource(error) => write!(f, "invalid source: {error}"),
            Self::PositionOverflow => f.write_str("source position overflow"),
        }
    }
}

fn initial_decoded(position: usize, raw: u8) -> Result<u8, AnalysisError> {
    let phase = position.rem_euclid(INITIAL_TRANSLATION.len());
    let cell_offset = usize::from(raw.saturating_sub(33));
    let translation = cell_offset
        .saturating_add(phase)
        .rem_euclid(INITIAL_TRANSLATION.len());
    INITIAL_TRANSLATION
        .get(translation)
        .copied()
        .ok_or(AnalysisError::PositionOverflow)
}

const fn effects(
    profile: &ProfileDescriptor,
    decoded: u8,
) -> (AccumulatorEffect, ControlFlow, DataEffect, bool) {
    if decoded == profile.input_instruction() {
        return (
            AccumulatorEffect::Write,
            ControlFlow::Sequential,
            DataEffect::None,
            true,
        );
    }
    if decoded == profile.output_instruction() {
        return (
            AccumulatorEffect::Read,
            ControlFlow::Sequential,
            DataEffect::None,
            true,
        );
    }
    match decoded {
        b'i' => (
            AccumulatorEffect::None,
            ControlFlow::IndirectCodePointer,
            DataEffect::Read,
            true,
        ),
        b'*' => (
            AccumulatorEffect::Write,
            ControlFlow::Sequential,
            DataEffect::ReadWrite,
            true,
        ),
        b'j' => (
            AccumulatorEffect::None,
            ControlFlow::Sequential,
            DataEffect::ReplacePointer,
            true,
        ),
        b'p' => (
            AccumulatorEffect::ReadWrite,
            ControlFlow::Sequential,
            DataEffect::ReadWrite,
            true,
        ),
        b'v' => (
            AccumulatorEffect::None,
            ControlFlow::Halt,
            DataEffect::None,
            false,
        ),
        _ => (
            AccumulatorEffect::None,
            ControlFlow::Sequential,
            DataEffect::None,
            true,
        ),
    }
}

/// Analyze the admitted initial program state without predicting mutations.
///
/// # Errors
///
/// Returns [`AnalysisError::InvalidSource`] when the source is not admitted by
/// `profile`, or [`AnalysisError::PositionOverflow`] if initial decode indexing
/// cannot be represented.
pub fn analyze_initial(
    profile: &'static ProfileDescriptor,
    source: &[u8],
) -> Result<InitialAnalysis, AnalysisError> {
    let _validated = ProfileMachine::from_source(profile, source, Vec::new())
        .map_err(AnalysisError::InvalidSource)?;
    let admitted = source
        .iter()
        .copied()
        .filter(|byte| !is_source_whitespace(*byte))
        .collect::<Vec<_>>();
    let mut cells = Vec::with_capacity(admitted.len());
    for (position, raw) in admitted.iter().copied().enumerate() {
        let decoded = initial_decoded(position, raw)?;
        let (accumulator, control_flow, data, post_step_encryption) =
            effects(profile, decoded);
        cells.push(InitialCell {
            accumulator,
            control_flow,
            data,
            decoded,
            position,
            post_step_encryption,
            raw,
        });
    }
    Ok(InitialAnalysis {
        cells,
        profile_fingerprint: profile.fingerprint(),
        profile_id: profile.id(),
        profile_version: profile.version(),
        source: admitted,
    })
}
