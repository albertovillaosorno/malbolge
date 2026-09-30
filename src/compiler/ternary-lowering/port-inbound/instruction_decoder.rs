// Copyright:
//   - Copyright © 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - Apache-2.0
// Confidential:
//   - false
// License-File:
//   - LICENSE-APACHE-2.0
//
// Boundary-Contract:
// - Owns:
//   - Minimal inverse-encoding dependency on canonical Malbolge instruction
//     decode.
// - Must-Not:
//   - Copy XLAT1, import VM implementation types, or execute machine state.
// - Allows:
//   - Inputs: graphical source cell and exact code-pointer position.
//   - Outputs: decoded instruction byte or rejection.
//   - Side effects: none.
// - Split-When:
//   - Another target encoding family requires an independent decoder contract.
// - Merge-When:
//   - Another inbound port owns this exact graphical instruction translation.
// - Summary:
//   - Lets lowering invert canonical decoding without duplicating its table.
// - Description:
//   - Production composition supplies the repository's normative VM decoder.
// - Usage:
//   - Used only by deterministic target-cell encoding.
// - Defaults:
//   - Missing or ambiguous inverse encodings fail closed.
//

//! Inbound canonical profile instruction-decoder port.

/// Canonical graphical profile instruction decoding dependency.
pub trait ProfileInstructionDecoder {
    /// Decodes one source cell at one exact code-pointer position.
    fn decode(&self, cell: u32, code_pointer: u32) -> Option<u8>;
}
