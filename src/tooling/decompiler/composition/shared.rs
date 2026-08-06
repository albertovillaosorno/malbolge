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
//   - One canonical module topology shared by both decompiler executables.
// - Must-Not:
//   - Contain decompilation semantics, acquisition, or frontend policy.
// - Allows:
//   - Inputs: Cargo binary identity plus responsibility-owned frontend modules.
//   - Outputs: one selected general or museum command execution.
//   - Side effects: delegated frontend behavior only.
// - Split-When:
//   - Another executable requires a materially different module topology.
// - Merge-When:
//   - Cargo no longer requires an executable composition surface.
// - Summary:
//   - Gives the shared renderer exactly one logical composition parent.
// - Description:
//   - Both binary targets include this topology and select one frontend.
// - Usage:
//   - Selected by the `malbolge_decompile` and `museum_convert` targets.
// - Defaults:
//   - Unknown binary identity fails explicitly without invoking a frontend.
//

// Shared module topology for the decompiler executable family.

#[path = "../application/render.rs"]
pub mod decompiler;
#[path = "cli.rs"]
pub mod decompiler_cli;
#[path = "museum.rs"]
pub mod museum_cli;

use std::io::{Error as IoError, Result as IoResult};

const DECOMPILER_BINARY: &str = "malbolge_decompile";
const MUSEUM_BINARY: &str = "museum_convert";

fn run_selected(binary_name: &str) -> IoResult<()> {
    match binary_name {
        DECOMPILER_BINARY => decompiler_cli::run(),
        MUSEUM_BINARY => museum_cli::run(),
        name => Err(IoError::other(format!(
            "unsupported decompiler binary identity: {name}"
        ))),
    }
}
