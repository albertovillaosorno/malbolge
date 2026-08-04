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
//   - Stable interpreter-authority and specification-comparison mode identity.
// - Must-Not:
//   - Make specification comparison implicit or grant it verifier authority.
// - Allows:
//   - Inputs: explicit execution-mode names.
//   - Outputs: typed mode identity and deterministic parse diagnostics.
//   - Side effects: none.
// - Split-When:
//   - Split when another semantic profile needs an independent identity scheme.
// - Merge-When:
//   - Merge when execution mode no longer has independent public meaning.
// - Summary:
//   - Names interpreter-authority execution and specification comparison.
// - Description:
//   - Provides one stable identity for traces, diagnostics, caches, and
//   - benches.
// - Usage:
//   - Passed explicitly to the execution facade; default is interpreter mode.
// - Defaults:
//   - `Interpreter` is the only verifier-eligible execution mode.
//

//! Stable identity for interpreter-authority and specification execution.

use std::fmt::{Display, Formatter, Result as FormatResult};
use std::str::FromStr;

/// Stable execution-mode identity.
#[derive(Clone, Copy, Debug, Default, Eq, PartialEq)]
pub enum ExecutionMode {
    /// Normative behavior of Ben Olmstead's original interpreter where defined.
    #[default]
    Interpreter,
    /// Explicit written-specification comparison semantics.
    Specification,
}

impl ExecutionMode {
    /// Returns whether results from this mode may satisfy verifier obligations.
    #[must_use]
    pub const fn is_verifier_eligible(self) -> bool {
        matches!(self, Self::Interpreter)
    }

    /// Returns the stable identity used in traces, diagnostics, and cache keys.
    #[must_use]
    pub const fn stable_id(self) -> &'static str {
        match self {
            Self::Interpreter => "interpreter",
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
            "interpreter" | "reference-interpreter" | "legacy-ben" => {
                Ok(Self::Interpreter)
            },
            "specification" => Ok(Self::Specification),
            _ => Err(ExecutionModeParseError {
                requested: requested.to_owned(),
            }),
        }
    }
}
