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
//   - Cargo entrypoint selecting the museum conversion frontend.
// - Must-Not:
//   - Duplicate module topology, renderer semantics, or argument policy.
// - Allows:
//   - Inputs: the canonical shared decompiler composition.
//   - Outputs: one local museum conversion command execution.
//   - Side effects: delegated frontend behavior only.
// - Split-When:
//   - Museum conversion gains an independent package lifecycle.
// - Merge-When:
//   - Cargo supports executable aliases without another target source.
// - Summary:
//   - Selects `museum_convert` from one shared composition topology.
// - Description:
//   - Keeps Cargo target identity separate from shared module ownership.
// - Usage:
//   - Compiled as the `museum_convert` binary.
// - Defaults:
//   - Selects only the frozen historical-profile frontend.
//

//! Local historical museum conversion executable.

include!("shared.rs");

fn main() -> IoResult<()> {
    run_selected(MUSEUM_BINARY)
}
