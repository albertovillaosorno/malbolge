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
//   - Stable fail-closed typed-IR admission failure categories.
// - Must-Not:
//   - Carry host errors, parser diagnostics, or target-lowering failures.
// - Allows:
//   - Inputs: deterministic typed-IR validation failures.
//   - Outputs: one closed version-one error category per rejected module.
//   - Side effects: none.
// - Split-When:
//   - A failure family gains independently versioned source diagnostics.
// - Merge-When:
//   - Admission no longer needs stable machine-readable failure categories.
// - Summary:
//   - Defines deterministic typed-IR validation rejection classes.
// - Description:
//   - Categories are intentionally coarser than internal validation helpers.
// - Usage:
//   - Returned by all application-level typed-IR admission checks.
// - Defaults:
//   - Validation fails at the first deterministic category encountered.
//

//! Stable fail-closed typed compiler IR admission failures.

/// Stable version-one typed-IR validation failure category.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ValidationError {
    /// Block IDs, entry identity, or successor identities are invalid.
    BlockIdentity,
    /// One call does not match its declared callee signature.
    CallSignature,
    /// Branch/switch condition semantics are invalid.
    ControlType,
    /// One SSA value is defined more than once.
    DuplicateValue,
    /// Function identity, name, signature, or parameter shape is invalid.
    FunctionIdentity,
    /// Global identity, name, type, span, or initializer is invalid.
    GlobalIdentity,
    /// One exact integer constant is malformed for its declared type.
    IntegerConstant,
    /// An instruction operand/result combination is not type-correct.
    OperandType,
    /// Phi predecessor/value relationships do not match the CFG.
    PhiPredecessors,
    /// Module format, ABI, or target-profile identity is unsupported.
    ProfileIdentity,
    /// A verifier-visible proof obligation references invalid semantics.
    ProofObligation,
    /// A basic block cannot be reached from the declared function entry.
    Reachability,
    /// A return does not match its function signature.
    ReturnType,
    /// Source logical identity or source span is invalid.
    SourceProvenance,
    /// One SSA definition does not dominate its use.
    SsaDominance,
    /// Type-table identity/reference semantics are invalid.
    TypeTable,
    /// SSA IDs are sparse or an operand has no definition.
    ValueIdentity,
}
