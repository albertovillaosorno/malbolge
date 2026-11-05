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
//   - One twenty-nine-distinct-byte C-to-Malbolge teaching source.
// - Must-Not:
//   - Substitute host output or claim arbitrary byte-stream lowering.
// - Allows:
//   - Inputs: pinned C frontend and guest stdio declarations.
//   - Outputs: eight printable, four control and seventeen high-bit bytes.
//   - Side effects: guest byte output only.
// - Split-When:
//   - General guest byte-stream lowering supersedes finite witnesses.
// - Merge-When:
//   - Compiler examples demonstrate general mixed-byte output.
// - Summary:
//   - Emits twenty-nine ordered and distinct guest-computed binary bytes.
// - Description:
//   - The compiler and real VM independently verify twenty-nine ordered bytes.
// - Usage:
//   - c2malbolge --repository-tools --capsule \
//     --output .temp/emit-twenty-nine.malbolge \
//     docs/technical/examples/corpus/emit-twenty-nine.c
// - Defaults:
//   - This finite trace is not general C byte-stream support.
//
#include <stdio.h>

void emit(void) {
  putchar(135);
  putchar(183);
  putchar(188);
  putchar(177);
  putchar(138);
  putchar(206);
  putchar(159);
  putchar(156);
  putchar(181);
  putchar(44);
  putchar(203);
  putchar(18);
  putchar(198);
  putchar(46);
  putchar(175);
  putchar(180);
  putchar(248);
  putchar(202);
  putchar(14);
  putchar(149);
  putchar(45);
  putchar(171);
  putchar(51);
  putchar(61);
  putchar(57);
  putchar(5);
  putchar(83);
  putchar(35);
  putchar(27);
}
