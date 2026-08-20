// Copyright:
//   - Copyright © 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - MIT
// Confidential:
//   - false
// License-File:
//   - LICENSE-MIT
//
// Boundary-Contract:
// - Owns:
//   - Stable compiler symbols for guest byte input and output.
// - Must-Not:
//   - Implement host I/O or target instruction lowering.
// - Allows:
//   - Inputs: no input argument and one canonical output byte.
//   - Outputs: profile input word or one abstract output byte effect.
//   - Side effects: abstract selected-profile byte I/O only.
// - Split-When:
//   - Another intrinsic family needs independent lowering.
// - Merge-When:
//   - Ternary lowering owns these exact declarations.
// - Summary:
//   - Declaration-only byte-I/O identities for downstream lowering.
// - Description:
//   - Lane 9 lowers these symbols to current `/` and `<` semantics.
// - Usage:
//   - Guest libc calls them; lane 8 provides no implementation.
// - Defaults:
//   - Input yields byte/EOF words; output has no host fallback.
//

//! Stable declaration-only byte-I/O intrinsic identities for target lowering.

#ifndef MALBOLGE_GUEST_INTRINSICS_H
#define MALBOLGE_GUEST_INTRINSICS_H

#include <stdint.h>

uint32_t malbolge_guest_intrinsic_input_word(void);
void malbolge_guest_intrinsic_output_byte(uint8_t value);

#endif
