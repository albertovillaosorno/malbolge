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
//   - One forty-eight-distinct-byte C-to-Malbolge teaching source.
// - Must-Not:
//   - Substitute host output or claim arbitrary byte-stream lowering.
// - Allows:
//   - Inputs: pinned C frontend and guest stdio declarations.
//   - Outputs: forty-eight distinct binary bytes.
//   - Side effects: guest byte output only.
// - Split-When:
//   - General guest byte-stream lowering supersedes finite witnesses.
// - Merge-When:
//   - Compiler examples demonstrate general mixed-byte output.
// - Summary:
//   - Emits forty-eight ordered and distinct guest-computed binary bytes.
// - Description:
//   - The compiler and real VM independently verify forty-eight ordered bytes.
// - Usage:
//   - c2malbolge --repository-tools --capsule \
//     --output .temp/emit-forty-eight.malbolge \
//     docs/technical/examples/corpus/emit-forty-eight.c
// - Defaults:
//   - This finite trace is not general C byte-stream support.
//
#include <stdio.h>

void emit(void) {
  putchar(81);
  putchar(55);
  putchar(52);
  putchar(56);
  putchar(251);
  putchar(206);
  putchar(159);
  putchar(152);
  putchar(184);
  putchar(180);
  putchar(131);
  putchar(205);
  putchar(4);
  putchar(202);
  putchar(28);
  putchar(27);
  putchar(46);
  putchar(79);
  putchar(139);
  putchar(207);
  putchar(167);
  putchar(162);
  putchar(149);
  putchar(214);
  putchar(150);
  putchar(161);
  putchar(175);
  putchar(197);
  putchar(186);
  putchar(224);
  putchar(157);
  putchar(225);
  putchar(185);
  putchar(65);
  putchar(71);
  putchar(92);
  putchar(42);
  putchar(68);
  putchar(41);
  putchar(14);
  putchar(50);
  putchar(78);
  putchar(49);
  putchar(24);
  putchar(31);
  putchar(76);
  putchar(32);
  putchar(23);
}
