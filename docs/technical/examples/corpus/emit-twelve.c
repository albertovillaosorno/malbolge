// Copyright:
//   - Copyright © 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - LicenseRef-Proprietary
// Confidential:
//   - true
// License-File:
//   - LICENSE
//
// Boundary-Contract:
// - Owns:
//   - One twelve-distinct-byte C-to-Malbolge teaching source.
// - Must-Not:
//   - Substitute host output or claim arbitrary byte-stream lowering.
// - Allows:
//   - Inputs: pinned C frontend and guest stdio declarations.
//   - Outputs: four ASCII bytes and eight high-bit binary bytes.
//   - Side effects: guest byte output only.
// - Split-When:
//   - General guest byte-stream lowering supersedes finite witnesses.
// - Merge-When:
//   - Compiler examples demonstrate general mixed-byte output.
// - Summary:
//   - Emits Q748 followed by eight distinct high-bit bytes.
// - Description:
//   - The compiler and real VM independently verify twelve ordered bytes.
// - Usage:
//   - c2malbolge --repository-tools --capsule \
//     --output .temp/emit-twelve.malbolge \
//     docs/technical/examples/corpus/emit-twelve.c
// - Defaults:
//   - This finite trace is not general C byte-stream support.
//
#include <stdio.h>

void emit(void) {
  putchar('Q');
  putchar('7');
  putchar('4');
  putchar('8');
  putchar(251);
  putchar(206);
  putchar(159);
  putchar(152);
  putchar(184);
  putchar(180);
  putchar(131);
  putchar(205);
}
