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
//   - One twenty-three-distinct-byte C-to-Malbolge teaching source.
// - Must-Not:
//   - Substitute host output or claim arbitrary byte-stream lowering.
// - Allows:
//   - Inputs: pinned C frontend and guest stdio declarations.
//   - Outputs: ten printable, seven control and six high-bit bytes.
//   - Side effects: guest byte output only.
// - Split-When:
//   - General guest byte-stream lowering supersedes finite witnesses.
// - Merge-When:
//   - Compiler examples demonstrate general mixed-byte output.
// - Summary:
//   - Emits twenty-three ordered and distinct guest-computed binary bytes.
// - Description:
//   - The compiler and real VM independently verify twenty-three ordered bytes.
// - Usage:
//   - c2malbolge --repository-tools --capsule \
//     --output .temp/emit-twenty-three.malbolge \
//     docs/technical/examples/corpus/emit-twenty-three.c
// - Defaults:
//   - This finite trace is not general C byte-stream support.
//
#include <stdio.h>

void emit(void) {
  putchar(66);
  putchar(14);
  putchar(47);
  putchar(23);
  putchar(57);
  putchar(4);
  putchar(142);
  putchar(36);
  putchar(159);
  putchar(27);
  putchar(160);
  putchar(35);
  putchar(151);
  putchar(21);
  putchar(40);
  putchar(39);
  putchar(41);
  putchar(20);
  putchar(50);
  putchar(30);
  putchar(139);
  putchar(38);
  putchar(146);
}
