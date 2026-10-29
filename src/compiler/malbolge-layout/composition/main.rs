// Copyright:
//   - Copyright © 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - Apache-2.0
// Confidential:
//   - false
// License-File:
//   - LICENSE
//
// Boundary-Contract:
// - Owns:
//   - Explicit-profile verified machine-subset source emission executable.
// - Must-Not:
//   - Claim C lowering or infer a target profile from an output extension.
// - Allows:
//   - Inputs: exact profile, fresh output path and bounded decoded operations.
//   - Outputs: new `.malbolge` source; no modification of existing targets.
//   - Side effects: bounded same-directory atomic artifact publication.
// - Split-When:
//   - Full compiled-C emitter replaces the explicit machine-subset command.
// - Merge-When:
//   - A verified final source publisher subsumes this isolated frontend.
// - Summary:
//   - Wires bounded ternary echo and graphical artifact publication.
// - Description:
//   - Standalone source artifact validation and no-overwrite publication.
// - Usage:
//   - `cargo run --bin malbolge_layout -- --profile ID --output PATH -- OPS`.
// - Defaults:
//   - Fail closed without exact target profile, final halt or fresh path.
//

//! Explicit-profile source emitter for the bounded verified machine subset.

#[expect(
    clippy::too_many_lines,
    clippy::duplicate_mod,
    reason = "existing independently validated bridge includes ternary decoder and layout"
)]
#[path = "../../byte-echo-bridge/composition/lib.rs"]
pub mod bridge;
#[path = "cli.rs"]
pub mod cli;
#[path = "lib.rs"]
pub mod layout;

use std::process::ExitCode;

fn main() -> ExitCode {
    cli::run()
}
