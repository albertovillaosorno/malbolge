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
//   - Explicit typed-IR basic blocks, phi merges, and final terminators.
// - Must-Not:
//   - Encode implicit fallthrough, exception unwinding, or target instruction
//     flow.
// - Allows:
//   - Inputs: ordered phi/instruction lists and explicit successor identities.
//   - Outputs: version-one control-flow graph values.
//   - Side effects: none.
// - Split-When:
//   - Exceptional or coroutine control flow gains an independent contract.
// - Merge-When:
//   - Control-flow and non-terminating instructions share one versioned policy.
// - Summary:
//   - Makes CFG edges and SSA predecessor merges explicit and portable.
// - Description:
//   - Every block owns exactly one final terminator by construction.
// - Usage:
//   - Stored inside typed-IR functions and checked by CFG admission.
// - Defaults:
//   - Phi incoming edges are explicit predecessor/value pairs.
//

//! Basic blocks, phi merges, and explicit terminators for typed compiler IR.

use super::ids::{BlockId, TypeId, ValueId};
use super::instruction::{IntegerConstant, LocatedInstruction};
use super::source::SourceSpan;

/// One predecessor/value edge of a phi merge.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct PhiIncoming {
    block: BlockId,
    value: ValueId,
}

impl PhiIncoming {
    /// Returns the predecessor block.
    #[must_use]
    pub const fn block(self) -> BlockId {
        self.block
    }

    /// Creates one explicit predecessor/value edge.
    #[must_use]
    pub const fn new(block: BlockId, value: ValueId) -> Self {
        Self { block, value }
    }

    /// Returns the incoming SSA value.
    #[must_use]
    pub const fn value(self) -> ValueId {
        self.value
    }
}

/// One typed SSA merge at basic-block entry.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct Phi {
    incoming: Vec<PhiIncoming>,
    result: ValueId,
    span: SourceSpan,
    type_id: TypeId,
}

impl Phi {
    /// Returns predecessor/value edges in canonical order.
    #[must_use]
    pub fn incoming(&self) -> &[PhiIncoming] {
        &self.incoming
    }

    /// Creates one phi merge.
    #[must_use]
    pub const fn new(
        result: ValueId,
        type_id: TypeId,
        incoming: Vec<PhiIncoming>,
        span: SourceSpan,
    ) -> Self {
        Self {
            incoming,
            result,
            span,
            type_id,
        }
    }

    /// Returns the SSA result identity.
    #[must_use]
    pub const fn result(&self) -> ValueId {
        self.result
    }

    /// Returns exact normalized source provenance.
    #[must_use]
    pub const fn span(&self) -> SourceSpan {
        self.span
    }

    /// Returns the shared incoming/result type.
    #[must_use]
    pub const fn type_id(&self) -> TypeId {
        self.type_id
    }
}

/// One explicit integer switch case.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct SwitchCase {
    constant: IntegerConstant,
    target: BlockId,
}

impl SwitchCase {
    /// Returns the exact selector constant.
    #[must_use]
    pub const fn constant(&self) -> &IntegerConstant {
        &self.constant
    }

    /// Creates one selector-constant/target pair.
    #[must_use]
    pub const fn new(constant: IntegerConstant, target: BlockId) -> Self {
        Self { constant, target }
    }

    /// Returns the selected target block.
    #[must_use]
    pub const fn target(&self) -> BlockId {
        self.target
    }
}

/// Required final control-flow operation of one basic block.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum Terminator {
    /// Conditional branch.
    Branch {
        /// Boolean condition.
        condition: ValueId,
        /// False successor.
        false_target: BlockId,
        /// True successor.
        true_target: BlockId,
    },
    /// Unconditional jump.
    Jump {
        /// Successor block.
        target: BlockId,
    },
    /// Function return.
    Return {
        /// Optional return value.
        value: Option<ValueId>,
    },
    /// Integer switch.
    Switch {
        /// Ordered explicit selector cases.
        cases: Vec<SwitchCase>,
        /// Default successor.
        default_target: BlockId,
        /// Integer selector value.
        selector: ValueId,
    },
}

/// Construction payload for one untrusted basic block.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct BasicBlockSpec {
    /// Stable block identity.
    pub id: BlockId,
    /// Ordered non-phi instructions.
    pub instructions: Vec<LocatedInstruction>,
    /// Ordered phi merges.
    pub phis: Vec<Phi>,
    /// Complete block source span.
    pub span: SourceSpan,
    /// Required final control-flow operation.
    pub terminator: Terminator,
    /// Exact normalized terminator provenance.
    pub terminator_span: SourceSpan,
}

/// One ordered basic block with a required final terminator.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct BasicBlock {
    id: BlockId,
    instructions: Vec<LocatedInstruction>,
    phis: Vec<Phi>,
    span: SourceSpan,
    terminator: Terminator,
    terminator_span: SourceSpan,
}

impl BasicBlock {
    /// Returns the block identity.
    #[must_use]
    pub const fn id(&self) -> BlockId {
        self.id
    }

    /// Returns ordered non-phi instructions.
    #[must_use]
    pub fn instructions(&self) -> &[LocatedInstruction] {
        &self.instructions
    }

    /// Creates one explicit basic block from an untrusted construction payload.
    #[must_use]
    pub fn new(spec: BasicBlockSpec) -> Self {
        Self {
            id: spec.id,
            instructions: spec.instructions,
            phis: spec.phis,
            span: spec.span,
            terminator: spec.terminator,
            terminator_span: spec.terminator_span,
        }
    }

    /// Returns ordered phi merges.
    #[must_use]
    pub fn phis(&self) -> &[Phi] {
        &self.phis
    }

    /// Returns normalized source provenance.
    #[must_use]
    pub const fn span(&self) -> SourceSpan {
        self.span
    }

    /// Returns the final control-flow operation.
    #[must_use]
    pub const fn terminator(&self) -> &Terminator {
        &self.terminator
    }

    /// Returns exact normalized terminator provenance.
    #[must_use]
    pub const fn terminator_span(&self) -> SourceSpan {
        self.terminator_span
    }
}
