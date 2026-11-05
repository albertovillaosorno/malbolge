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
//   - One sixteen-distinct-byte C-to-Malbolge teaching source.
// - Must-Not:
//   - Substitute host output or claim arbitrary byte-stream lowering.
// - Allows:
//   - Inputs: pinned C frontend and guest stdio declarations.
//   - Outputs: four printable, four control and eight high-bit bytes.
//   - Side effects: guest byte output only.
// - Split-When:
//   - General guest byte-stream lowering supersedes finite witnesses.
// - Merge-When:
//   - Compiler examples demonstrate general mixed-byte output.
// - Summary:
//   - Emits sixteen ordered and distinct guest-computed binary bytes.
// - Description:
//   - The compiler and real VM independently verify sixteen ordered bytes.
// - Usage:
//   - c2malbolge --repository-tools --capsule \
//     --output .temp/emit-sixteen.malbolge \
//     docs/technical/examples/corpus/emit-sixteen.c
// - Defaults:
//   - This finite trace is not general C byte-stream support.
//
#include <stdio.h>

void emit(void) {
  putchar(63);
  putchar(73);
  putchar(54);
  putchar(19);
  putchar(90);
  putchar(10);
  putchar(186);
  putchar(179);
  putchar(195);
  putchar(134);
  putchar(204);
  putchar(170);
  putchar(1);
  putchar(7);
  putchar(213);
  putchar(197);
}
