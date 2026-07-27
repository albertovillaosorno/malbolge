// File:
//   - museum.rs
// Path:
//   - tools/decompile/museum.rs
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
//   - Minimal local conversion policy for historical museum specimens.
// - Must-Not:
//   - Download, vendor, license, or silently reinterpret historical programs.
// - Allows:
//   - Inputs: one caller-supplied classic Malbolge file and one C output path.
//   - Outputs: one local generated C view through the general decompiler
//     backend.
//   - Side effects: local filesystem reads/writes only.
// - Split-When:
//   - Split when museum provenance automation exceeds conversion policy.
// - Merge-When:
//   - Merge when no museum-specific profile choice remains.
// - Summary:
//   - Converts local museum specimens through the professional decompiler.
// - Description:
//   - Fixes semantics to frozen `malbolge-1998` and performs no acquisition.
// - Usage:
//   - Delegated by the `museum_convert` Cargo composition root.
// - Defaults:
//   - Historical profile only; output remains local and rebuildable.
//
// Related documents:
// - examples/museum/README.md
// - tools/decompile/README.md
//
// Large file:
//   - false

//! Museum-specific local conversion policy over the general C backend.

use std::env;
use std::fs::{read, write};
use std::io::{Error as IoError, Result as IoResult};
use std::path::PathBuf;

use malbolge::historical_profile;

use crate::decompiler;

/// Converts one locally supplied historical specimen to a local C view.
///
/// # Errors
///
/// Returns an I/O error for malformed arguments, local file operations, or
/// semantic rendering rejection under the frozen historical profile.
pub fn run() -> IoResult<()> {
    let mut arguments = env::args_os().skip(1);
    let input = arguments.next().map(PathBuf::from).ok_or_else(|| {
        IoError::other("usage: museum_convert INPUT OUTPUT.c")
    })?;
    let output = arguments.next().map(PathBuf::from).ok_or_else(|| {
        IoError::other("usage: museum_convert INPUT OUTPUT.c")
    })?;
    if arguments.next().is_some() {
        return Err(IoError::other("usage: museum_convert INPUT OUTPUT.c"));
    }
    let source = read(input)?;
    let rendered = decompiler::render_c(historical_profile(), &source)
        .map_err(|error| IoError::other(error.to_string()))?;
    write(output, rendered.as_bytes())
}
