// File:
//   - mode.rs
// Path:
//   - vm/src/mode.rs
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
//   - Stable execution-mode identity and explicit mode parsing.
// - Must-Not:
//   - Select historical compatibility implicitly or grant verifier authority.
// - Allows:
//   - Inputs: explicit execution-mode names.
//   - Outputs: typed mode identity and deterministic parse diagnostics.
//   - Side effects: none.
// - Split-When:
//   - Split when another semantic profile needs an independent identity scheme.
// - Merge-When:
//   - Merge when execution mode no longer has independent public meaning.
// - Summary:
//   - Names normative execution and the opt-in Ben compatibility mode.
// - Description:
//   - Provides one stable identity for traces, diagnostics, caches, and
//   - benches.
// - Usage:
//   - Passed explicitly to the execution facade; default is specification mode.
// - Defaults:
//   - `Specification` is the only verifier-eligible execution mode.
//
// Related documents:
// - docs/technical/runtime/vm/specification-and-legacy-interpreter-modes.md
// - docs/technical/adr/specification-authority-and-malbolge-evolution.md
//
// Large file:
//   - false
//

//! Stable identity for normative and historical-compatibility execution.

use std::fmt::{Display, Formatter, Result as FormatResult};
use std::str::FromStr;

/// Stable execution-mode identity.
#[derive(Clone, Copy, Debug, Default, Eq, PartialEq)]
pub enum ExecutionMode {
    /// Explicit compatibility mode for selected reproducible Ben defects.
    LegacyBen,
    /// Normative written-specification semantics.
    #[default]
    Specification,
}

impl ExecutionMode {
    /// Returns whether results from this mode may satisfy verifier obligations.
    #[must_use]
    pub const fn is_verifier_eligible(self) -> bool {
        matches!(self, Self::Specification)
    }

    /// Returns the stable identity used in traces, diagnostics, and cache keys.
    #[must_use]
    pub const fn stable_id(self) -> &'static str {
        match self {
            Self::LegacyBen => "legacy-ben",
            Self::Specification => "specification",
        }
    }
}

impl Display for ExecutionMode {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        f.write_str(self.stable_id())
    }
}

/// Failure to parse one explicit execution-mode name.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ExecutionModeParseError {
    requested: String,
}

impl ExecutionModeParseError {
    /// Returns the unrecognized mode name supplied by the caller.
    #[must_use]
    pub fn requested(&self) -> &str {
        &self.requested
    }
}

impl Display for ExecutionModeParseError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        write!(f, "unknown execution mode `{}`", self.requested)
    }
}

impl FromStr for ExecutionMode {
    type Err = ExecutionModeParseError;

    fn from_str(requested: &str) -> Result<Self, Self::Err> {
        match requested {
            "legacy-ben" => Ok(Self::LegacyBen),
            "specification" => Ok(Self::Specification),
            _ => Err(ExecutionModeParseError {
                requested: requested.to_owned(),
            }),
        }
    }
}
