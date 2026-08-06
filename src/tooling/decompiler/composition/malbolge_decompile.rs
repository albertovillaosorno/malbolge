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
//   - Cargo entrypoint selecting the general decompiler frontend.
// - Must-Not:
//   - Duplicate module topology, renderer semantics, or argument policy.
// - Allows:
//   - Inputs: the canonical shared decompiler composition.
//   - Outputs: one general decompiler command execution.
//   - Side effects: delegated frontend behavior only.
// - Split-When:
//   - The general command gains an independent package lifecycle.
// - Merge-When:
//   - Cargo supports executable aliases without another target source.
// - Summary:
//   - Selects `malbolge_decompile` from one shared composition topology.
// - Description:
//   - Keeps Cargo target identity separate from shared module ownership.
// - Usage:
//   - Compiled as the `malbolge_decompile` binary.
// - Defaults:
//   - Selects only the general explicit-profile frontend.
//

//! General explicit-profile Malbolge decompiler executable.

include!("shared.rs");

fn main() -> IoResult<()> {
    run_selected(DECOMPILER_BINARY)
}
