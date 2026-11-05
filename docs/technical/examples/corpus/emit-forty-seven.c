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
//   - One forty-seven-distinct-byte C-to-Malbolge teaching source.
// - Must-Not:
//   - Substitute host output or claim arbitrary byte-stream lowering.
// - Allows:
//   - Inputs: pinned C frontend and guest stdio declarations.
//   - Outputs: forty-seven distinct binary bytes.
//   - Side effects: guest byte output only.
// - Split-When:
//   - General guest byte-stream lowering supersedes finite witnesses.
// - Merge-When:
//   - Compiler examples demonstrate general mixed-byte output.
// - Summary:
//   - Emits forty-seven ordered and distinct guest-computed binary bytes.
// - Description:
//   - The compiler and real VM independently verify forty-seven ordered bytes.
// - Usage:
//   - c2malbolge --repository-tools --capsule \
//     --output .temp/emit-forty-seven.malbolge \
//     docs/technical/examples/corpus/emit-forty-seven.c
// - Defaults:
//   - This finite trace is not general C byte-stream support.
//
#include <stdio.h>

void emit(void) {
  putchar(5);
  putchar(252);
  putchar(205);
  putchar(167);
  putchar(216);
  putchar(194);
  putchar(187);
  putchar(195);
  putchar(215);
  putchar(64);
  putchar(65);
  putchar(89);
  putchar(36);
  putchar(90);
  putchar(28);
  putchar(27);
  putchar(46);
  putchar(79);
  putchar(47);
  putchar(26);
  putchar(72);
  putchar(185);
  putchar(253);
  putchar(211);
  putchar(23);
  putchar(157);
  putchar(51);
  putchar(183);
  putchar(176);
  putchar(59);
  putchar(175);
  putchar(55);
  putchar(81);
  putchar(29);
  putchar(80);
  putchar(56);
  putchar(54);
  putchar(74);
  putchar(53);
  putchar(20);
  putchar(44);
  putchar(63);
  putchar(45);
  putchar(10);
  putchar(70);
  putchar(38);
  putchar(17);
}
