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
//   - One twenty-four-distinct-byte C-to-Malbolge teaching source.
// - Must-Not:
//   - Substitute host output or claim arbitrary byte-stream lowering.
// - Allows:
//   - Inputs: pinned C frontend and guest stdio declarations.
//   - Outputs: eight printable, eight control and eight high-bit bytes.
//   - Side effects: guest byte output only.
// - Split-When:
//   - General guest byte-stream lowering supersedes finite witnesses.
// - Merge-When:
//   - Compiler examples demonstrate general mixed-byte output.
// - Summary:
//   - Emits twenty-four ordered and distinct guest-computed binary bytes.
// - Description:
//   - The compiler and real VM independently verify twenty-four ordered bytes.
// - Usage:
//   - c2malbolge --repository-tools --capsule \
//     --output .temp/emit-twenty-four.malbolge \
//     docs/technical/examples/corpus/emit-twenty-four.c
// - Defaults:
//   - This finite trace is not general C byte-stream support.
//
#include <stdio.h>

void emit(void) {
  putchar(62);
  putchar(11);
  putchar(44);
  putchar(18);
  putchar(54);
  putchar(1);
  putchar(61);
  putchar(149);
  putchar(15);
  putchar(157);
  putchar(23);
  putchar(139);
  putchar(33);
  putchar(147);
  putchar(146);
  putchar(32);
  putchar(148);
  putchar(14);
  putchar(155);
  putchar(24);
  putchar(138);
  putchar(28);
  putchar(47);
  putchar(35);
}
