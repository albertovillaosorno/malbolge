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
//   - One twenty-two-distinct-byte C-to-Malbolge teaching source.
// - Must-Not:
//   - Substitute host output or claim arbitrary byte-stream lowering.
// - Allows:
//   - Inputs: pinned C frontend and guest stdio declarations.
//   - Outputs: ten printable, eight control and four high-bit bytes.
//   - Side effects: guest byte output only.
// - Split-When:
//   - General guest byte-stream lowering supersedes finite witnesses.
// - Merge-When:
//   - Compiler examples demonstrate general mixed-byte output.
// - Summary:
//   - Emits twenty-two ordered and distinct guest-computed binary bytes.
// - Description:
//   - The compiler and real VM independently verify twenty-two ordered bytes.
// - Usage:
//   - c2malbolge --repository-tools --capsule \
//     --output .temp/emit-twenty-two.malbolge \
//     docs/technical/examples/corpus/emit-twenty-two.c
// - Defaults:
//   - This finite trace is not general C byte-stream support.
//
#include <stdio.h>

void emit(void) {
  putchar(57);
  putchar(22);
  putchar(55);
  putchar(5);
  putchar(65);
  putchar(12);
  putchar(48);
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
  putchar(31);
}
