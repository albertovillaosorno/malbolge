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
//   - Portable source-byte provenance carried by typed compiler IR.
// - Must-Not:
//   - Carry physical filesystem paths, host offsets, or editor-specific ranges.
// - Allows:
//   - Inputs: normalized logical source byte/line/column positions.
//   - Outputs: exact immutable source positions and half-open spans.
//   - Side effects: none.
// - Split-When:
//   - Macro/include expansion requires a separately versioned provenance graph.
// - Merge-When:
//   - Another domain value owns the same logical-source coordinate contract.
// - Summary:
//   - Preserves normalized source coordinates without physical path leakage.
// - Description:
//   - Byte offsets are zero-based; line and column values are one-based.
// - Usage:
//   - Attached to functions, globals, blocks, and future diagnostics.
// - Defaults:
//   - Admission rejects zero line/column and reversed byte spans.
//

//! Portable normalized-source provenance for typed compiler IR.

/// One logical source position.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct SourcePosition {
    byte: u32,
    column: u32,
    line: u32,
}

impl SourcePosition {
    /// Returns the zero-based source byte offset.
    #[must_use]
    pub const fn byte(self) -> u32 {
        self.byte
    }

    /// Returns the one-based source column.
    #[must_use]
    pub const fn column(self) -> u32 {
        self.column
    }

    /// Returns the one-based source line.
    #[must_use]
    pub const fn line(self) -> u32 {
        self.line
    }

    /// Creates one source position from normalized coordinates.
    #[must_use]
    pub const fn new(byte: u32, line: u32, column: u32) -> Self {
        Self { byte, column, line }
    }
}

/// One half-open logical source span.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct SourceSpan {
    begin: SourcePosition,
    end: SourcePosition,
}

impl SourceSpan {
    /// Returns the inclusive begin position.
    #[must_use]
    pub const fn begin(self) -> SourcePosition {
        self.begin
    }

    /// Returns the exclusive end position.
    #[must_use]
    pub const fn end(self) -> SourcePosition {
        self.end
    }

    /// Creates one half-open normalized source span.
    #[must_use]
    pub const fn new(begin: SourcePosition, end: SourcePosition) -> Self {
        Self { begin, end }
    }
}
