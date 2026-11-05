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
//   - One twenty-seven-distinct-byte C-to-Malbolge teaching source.
// - Must-Not:
//   - Substitute host output or claim arbitrary byte-stream lowering.
// - Allows:
//   - Inputs: pinned C frontend and guest stdio declarations.
//   - Outputs: fourteen printable, five control and eight high-bit bytes.
//   - Side effects: guest byte output only.
// - Split-When:
//   - General guest byte-stream lowering supersedes finite witnesses.
// - Merge-When:
//   - Compiler examples demonstrate general mixed-byte output.
// - Summary:
//   - Emits twenty-seven ordered and distinct guest-computed binary bytes.
// - Description:
//   - The compiler and real VM independently verify twenty-seven ordered bytes.
// - Usage:
//   - c2malbolge --repository-tools --capsule \
//     --output .temp/emit-twenty-seven.malbolge \
//     docs/technical/examples/corpus/emit-twenty-seven.c
// - Defaults:
//   - This finite trace is not general C byte-stream support.
//
#include <stdio.h>

void emit(void) {
  putchar(81);
  putchar(62);
  putchar(53);
  putchar(56);
  putchar(84);
  putchar(31);
  putchar(78);
  putchar(51);
  putchar(61);
  putchar(57);
  putchar(5);
  putchar(83);
  putchar(35);
  putchar(27);
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
}
