// File:
//   - annotated.rs
// Path:
//   - vm/src/annotated.rs
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
//   - Explicit annotated-source presentation parsing, formatting, and source
//   - maps.
// - Must-Not:
//   - Redefine raw `.malbolge` loading or bypass selected-profile validation.
// - Allows:
//   - Inputs: ASCII annotated source or canonical graphical Malbolge bytes.
//   - Outputs: canonical loaded bytes, deterministic formatting, source
//   - locations.
//   - Side effects: process-local allocation only.
// - Split-When:
//   - Split when rich compiler/decompiler annotations need a separate map
//   - format.
// - Merge-When:
//   - Merge when raw and annotated source admission become one explicit
//   - frontend.
// - Summary:
//   - Removes presentation-only whitespace/hash comments before normal loading.
// - Description:
//   - Keeps canonical Malbolge bytes authoritative while enabling readable
//   - views.
// - Usage:
//   - Used by explicit annotated VM constructors and future compiler/tooling
//   - views.
// - Defaults:
//   - Hash starts a comment only at line start when followed by space or tab.
//
// Related documents:
// - docs/technical/tooling/annotated-malbolge-source-format.md
// - docs/technical/specification/malbolge-1998.md
//
// Large file:
//   - false
//

//! Explicit presentation-only syntax for readable Malbolge source.

use std::fmt::{Display, Formatter, Result as FormatResult};

const COMMENT_MARKER: u8 = b'#';

/// Failure while preprocessing annotated source and loading canonical bytes.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum AnnotatedLoadError<LoadError> {
    /// Annotated presentation syntax was invalid.
    Annotated(AnnotatedSourceError),
    /// Canonicalized bytes were rejected by the selected loader/runtime.
    Load(LoadError),
}

impl<LoadError> Display for AnnotatedLoadError<LoadError>
where
    LoadError: Display,
{
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::Annotated(error) => Display::fmt(error, f),
            Self::Load(error) => Display::fmt(error, f),
        }
    }
}

/// Failure while canonicalizing or formatting annotated Malbolge source.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum AnnotatedSourceError {
    /// A comment contains a non-ASCII/control byte outside space/tab/graphical.
    InvalidCommentByte {
        /// Original byte offset in annotated source.
        offset: usize,
        /// Rejected byte value.
        byte: u8,
    },
    /// A non-comment presentation byte is neither ASCII whitespace nor
    /// graphical.
    InvalidPresentationByte {
        /// Original byte offset in annotated source.
        offset: usize,
        /// Rejected byte value.
        byte: u8,
    },
    /// Formatter wrap width was zero.
    ZeroWrapWidth,
}

impl Display for AnnotatedSourceError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self {
            Self::InvalidCommentByte { offset, byte } => write!(
                f,
                concat!(
                    "annotated comment byte {} at offset {}",
                    " is not admitted ASCII",
                ),
                byte, offset
            ),
            Self::InvalidPresentationByte { offset, byte } => write!(
                f,
                concat!(
                    "annotated source byte {} at offset {}",
                    " is not graphical ASCII",
                ),
                byte, offset
            ),
            Self::ZeroWrapWidth => {
                f.write_str("annotated formatter wrap width must be nonzero")
            },
        }
    }
}

/// One original annotated-source location for a canonical loaded byte.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct AnnotatedSourceLocation {
    column: usize,
    line: usize,
    offset: usize,
}

impl AnnotatedSourceLocation {
    /// Returns the one-based source column.
    #[must_use]
    pub const fn column(self) -> usize {
        self.column
    }

    /// Returns the one-based source line.
    #[must_use]
    pub const fn line(self) -> usize {
        self.line
    }

    /// Returns the zero-based original byte offset.
    #[must_use]
    pub const fn offset(self) -> usize {
        self.offset
    }
}

/// Canonical bytes plus an exact loaded-position-to-source-location map.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct CanonicalizedAnnotatedSource {
    bytes: Vec<u8>,
    locations: Vec<AnnotatedSourceLocation>,
}

impl CanonicalizedAnnotatedSource {
    /// Returns canonical graphical bytes in exact loaded-position order.
    #[must_use]
    pub fn bytes(&self) -> &[u8] {
        &self.bytes
    }

    /// Consumes the result and returns canonical graphical bytes.
    #[must_use]
    pub fn into_bytes(self) -> Vec<u8> {
        self.bytes
    }

    /// Returns one source location for each canonical loaded position.
    #[must_use]
    pub fn locations(&self) -> &[AnnotatedSourceLocation] {
        &self.locations
    }
}

#[derive(Clone, Copy, Debug)]
struct SourceCursor {
    column: usize,
    line: usize,
    line_has_code: bool,
    offset: usize,
}

impl Default for SourceCursor {
    fn default() -> Self {
        Self {
            column: 1,
            line: 1,
            line_has_code: false,
            offset: 0,
        }
    }
}

impl SourceCursor {
    fn advance_carriage_return(&mut self, source: &[u8]) {
        let following_lf =
            source.get(self.offset.saturating_add(1)) == Some(&b'\n');
        let bytes = if following_lf {
            2
        } else {
            1
        };
        self.advance_newline(bytes);
    }

    const fn advance_newline(&mut self, bytes: usize) {
        self.column = 1;
        self.line = self.line.saturating_add(1);
        self.line_has_code = false;
        self.offset = self.offset.saturating_add(bytes);
    }

    const fn advance_regular(&mut self) {
        self.column = self.column.saturating_add(1);
        self.offset = self.offset.saturating_add(1);
    }

    fn advance_whitespace(&mut self, source: &[u8], byte: u8) {
        if byte == b'\r' {
            self.advance_carriage_return(source);
        } else if byte == b'\n' {
            self.advance_newline(1);
        } else {
            self.advance_regular();
        }
    }

    fn skip_comment(
        &mut self,
        source: &[u8],
    ) -> Result<(), AnnotatedSourceError> {
        while self.offset < source.len() {
            let byte = source.get(self.offset).copied().ok_or(
                AnnotatedSourceError::InvalidCommentByte {
                    offset: self.offset,
                    byte: 0,
                },
            )?;
            if byte == b'\n' {
                self.advance_newline(1);
                return Ok(());
            }
            if byte == b'\r' {
                self.advance_carriage_return(source);
                return Ok(());
            }
            if byte == b'\t' || (0x20..=0x7e).contains(&byte) {
                self.advance_regular();
            } else {
                return Err(AnnotatedSourceError::InvalidCommentByte {
                    offset: self.offset,
                    byte,
                });
            }
        }
        Ok(())
    }
}

/// Removes presentation whitespace and full-line hash comments.
///
/// A comment begins only when `#` is the first non-whitespace byte of a
/// physical line and the immediately following byte is space or tab. Bare `#`,
/// `#X`, and inline hashes remain canonical code bytes. This keeps every
/// graphical byte sequence representable without escapes.
///
/// # Errors
///
/// Returns [`AnnotatedSourceError`] for bytes outside the admitted ASCII
/// presentation surface.
pub fn canonicalize_annotated_source(
    source: &[u8],
) -> Result<CanonicalizedAnnotatedSource, AnnotatedSourceError> {
    let mut bytes = Vec::new();
    let mut locations = Vec::new();
    let mut cursor = SourceCursor::default();
    while cursor.offset < source.len() {
        if is_comment_start(source, cursor.offset, cursor.line_has_code) {
            cursor.skip_comment(source)?;
            continue;
        }
        let byte = source.get(cursor.offset).copied().ok_or(
            AnnotatedSourceError::InvalidPresentationByte {
                offset: cursor.offset,
                byte: 0,
            },
        )?;
        if byte.is_ascii_whitespace() {
            cursor.advance_whitespace(source, byte);
            continue;
        }
        if !(33..=126).contains(&byte) {
            return Err(AnnotatedSourceError::InvalidPresentationByte {
                offset: cursor.offset,
                byte,
            });
        }
        bytes.push(byte);
        locations.push(AnnotatedSourceLocation {
            column: cursor.column,
            line: cursor.line,
            offset: cursor.offset,
        });
        cursor.line_has_code = true;
        cursor.advance_regular();
    }
    Ok(CanonicalizedAnnotatedSource { bytes, locations })
}

/// Wraps canonical graphical source at a deterministic byte width.
///
/// Formatting emits LF only and never inserts horizontal whitespace into code
/// lines. Therefore it cannot accidentally create the `# ` / `#\t` full-line
/// comment marker. A trailing or line-start `#` remains ordinary code.
///
/// # Errors
///
/// Returns [`AnnotatedSourceError::ZeroWrapWidth`] for width zero or
/// [`AnnotatedSourceError::InvalidPresentationByte`] when `canonical` contains
/// anything outside graphical ASCII `33..=126`.
pub fn format_annotated_source(
    canonical: &[u8],
    width: usize,
) -> Result<Vec<u8>, AnnotatedSourceError> {
    if width == 0 {
        return Err(AnnotatedSourceError::ZeroWrapWidth);
    }
    let wrapped_lines = canonical.len().div_ceil(width);
    let mut output =
        Vec::with_capacity(canonical.len().saturating_add(wrapped_lines));
    for (position, byte) in canonical.iter().copied().enumerate() {
        if !(33..=126).contains(&byte) {
            return Err(AnnotatedSourceError::InvalidPresentationByte {
                offset: position,
                byte,
            });
        }
        if position != 0 && position.is_multiple_of(width) {
            output.push(b'\n');
        }
        output.push(byte);
    }
    Ok(output)
}

fn is_comment_start(source: &[u8], offset: usize, line_has_code: bool) -> bool {
    if line_has_code || source.get(offset) != Some(&COMMENT_MARKER) {
        return false;
    }
    matches!(source.get(offset.saturating_add(1)), Some(b' ' | b'\t'))
}
