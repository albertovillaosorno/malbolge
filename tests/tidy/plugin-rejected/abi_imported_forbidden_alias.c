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
//   - Rejected guest-C evidence for a forbidden type imported from a header.
// - Must-Not:
//   - Treat the included header as the selected translation unit.
// - Allows:
//   - Inputs: one included alias and one explicit source declaration.
//   - Outputs: source-local MALBOLGE-ABI-006 rejection evidence.
//   - Side effects: none.
// - Split-When:
//   - Split when another imported exclusion needs independent evidence.
// - Merge-When:
//   - Merge when imported-type use is covered by equivalent source evidence.
// - Summary:
//   - Reject a source use of a forbidden type alias imported from a header.
// - Description:
//   - Ensures main-file matching does not let forbidden included aliases pass.
// - Usage:
//   - Consumed by native-analysis plugin regression tests.
// - Defaults:
//   - Included declaration locations are not user-facing diagnostics here.
//

//! Uses one forbidden integer alias imported from a test header.

#include "abi_forbidden_alias.h"

ImportedWideInteger value;
