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
//   - One thirty-four-distinct-byte C-to-Malbolge teaching source.
// - Must-Not:
//   - Substitute host output or claim arbitrary byte-stream lowering.
// - Allows:
//   - Inputs: pinned C frontend and guest stdio declarations.
//   - Outputs: thirty-four distinct binary bytes.
//   - Side effects: guest byte output only.
// - Split-When:
//   - General guest byte-stream lowering supersedes finite witnesses.
// - Merge-When:
//   - Compiler examples demonstrate general mixed-byte output.
// - Summary:
//   - Emits thirty-four ordered and distinct guest-computed binary bytes.
// - Description:
//   - The compiler and real VM independently verify thirty-four ordered bytes.
// - Usage:
//   - c2malbolge --repository-tools --capsule \
//     --output .temp/emit-thirty-four.malbolge \
//     docs/technical/examples/corpus/emit-thirty-four.c
// - Defaults:
//   - This finite trace is not general C byte-stream support.
//
#include <stdio.h>

void emit(void) {
  putchar(63);
  putchar(17);
  putchar(44);
  putchar(20);
  putchar(57);
  putchar(4);
  putchar(168);
  putchar(80);
  putchar(54);
  putchar(61);
  putchar(66);
  putchar(68);
  putchar(47);
  putchar(11);
  putchar(214);
  putchar(156);
  putchar(227);
  putchar(160);
  putchar(210);
  putchar(173);
  putchar(147);
  putchar(224);
  putchar(159);
  putchar(228);
  putchar(170);
  putchar(213);
  putchar(174);
  putchar(9);
  putchar(212);
  putchar(172);
  putchar(225);
  putchar(158);
  putchar(226);
  putchar(171);
}
