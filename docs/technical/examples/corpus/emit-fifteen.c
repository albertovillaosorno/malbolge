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
//   - One fifteen-distinct-byte C-to-Malbolge teaching source.
// - Must-Not:
//   - Substitute host output or claim arbitrary byte-stream lowering.
// - Allows:
//   - Inputs: pinned C frontend and guest stdio declarations.
//   - Outputs: four printable, two control and nine high-bit bytes.
//   - Side effects: guest byte output only.
// - Split-When:
//   - General guest byte-stream lowering supersedes finite witnesses.
// - Merge-When:
//   - Compiler examples demonstrate general mixed-byte output.
// - Summary:
//   - Emits fifteen ordered and distinct guest-computed binary bytes.
// - Description:
//   - The compiler and real VM independently verify fifteen ordered bytes.
// - Usage:
//   - c2malbolge --repository-tools --capsule \
//     --output .temp/emit-fifteen.malbolge \
//     docs/technical/examples/corpus/emit-fifteen.c
// - Defaults:
//   - This finite trace is not general C byte-stream support.
//
#include <stdio.h>

void emit(void) {
  putchar(81);
  putchar(46);
  putchar(25);
  putchar(56);
  putchar(62);
  putchar(137);
  putchar(210);
  putchar(173);
  putchar(163);
  putchar(183);
  putchar(200);
  putchar(136);
  putchar(8);
  putchar(213);
  putchar(198);
}
