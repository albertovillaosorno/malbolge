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
//   - Cargo composition for the general Malbolge decompiler executable.
// - Must-Not:
//   - Contain decompilation semantics, argument policy, or profile fallback.
// - Allows:
//   - Inputs: responsibility-owned decompiler renderer and CLI modules.
//   - Outputs: one Cargo auto-discovered executable.
//   - Side effects: delegated CLI behavior only.
// - Split-When:
//   - Split when another executable needs a different product composition.
// - Merge-When:
//   - Merge when Cargo no longer needs this composition surface.
// - Summary:
//   - Thin Cargo entrypoint for professional Malbolge decompilation.
// - Description:
//   - Keeps reverse-engineering implementation under `tools/decompile/`.
// - Usage:
//   - Invoked as the `malbolge_decompile` binary.
// - Defaults:
//   - Adds no behavior beyond delegated modules.
//

//! Cargo composition root for the general Malbolge decompiler.

#[path = "../application/render.rs"]
pub mod decompiler;
#[path = "cli.rs"]
pub mod decompiler_cli;

use std::io::Result as IoResult;

fn main() -> IoResult<()> {
    decompiler_cli::run()
}
