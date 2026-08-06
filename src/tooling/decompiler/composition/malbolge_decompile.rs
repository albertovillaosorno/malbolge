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
//   - Cargo entrypoint and sole module topology for decompilation.
// - Must-Not:
//   - Duplicate renderer semantics or infer profile and representation policy.
// - Allows:
//   - Inputs: explicit CLI arguments and responsibility-owned modules.
//   - Outputs: one general decompiler command execution.
//   - Side effects: delegated frontend behavior only.
// - Split-When:
//   - The general command gains an independent package lifecycle.
// - Merge-When:
//   - No independent executable composition policy remains.
// - Summary:
//   - Owns the single general decompiler executable topology.
// - Description:
//   - Wires the renderer and explicit CLI under one logical root.
// - Usage:
//   - Compiled as the `malbolge_decompile` binary.
// - Defaults:
//   - Selects only the general explicit-profile frontend.
//

//! General explicit-profile Malbolge decompiler executable.

#[path = "../application/render.rs"]
pub mod decompiler;
#[path = "cli.rs"]
pub mod decompiler_cli;

use std::io::Result as IoResult;

fn main() -> IoResult<()> {
    decompiler_cli::run()
}
