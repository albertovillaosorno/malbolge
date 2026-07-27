// File:
//   - museum_convert.rs
// Path:
//   - src/bin/museum_convert.rs
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
//   - Cargo composition for the local museum conversion helper.
// - Must-Not:
//   - Contain acquisition, licensing, decompilation semantics, or CLI policy.
// - Allows:
//   - Inputs: general renderer and museum-specific local conversion policy.
//   - Outputs: one Cargo auto-discovered helper executable.
//   - Side effects: delegated local conversion behavior only.
// - Split-When:
//   - Split when another museum executable needs independent policy.
// - Merge-When:
//   - Merge when Cargo no longer needs this composition surface.
// - Summary:
//   - Thin Cargo entrypoint for local historical-file conversion.
// - Description:
//   - Keeps museum conversion policy under the decompiler responsibility.
// - Usage:
//   - Invoked as the `museum_convert` binary.
// - Defaults:
//   - Adds no behavior beyond delegated modules.
//
// Related documents:
// - examples/museum/README.md
// - tools/decompile/README.md
//
// Large file:
//   - false

//! Cargo composition root for the museum conversion helper.

#[path = "../../tools/decompile/render.rs"]
pub mod decompiler;
#[path = "../../tools/decompile/museum.rs"]
pub mod museum_cli;

use std::io::Result as IoResult;

fn main() -> IoResult<()> {
    museum_cli::run()
}
