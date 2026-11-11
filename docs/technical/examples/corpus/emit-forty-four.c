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
//   - One forty-four-distinct-byte C-to-Malbolge teaching source.
// - Must-Not:
//   - Substitute host output or claim arbitrary byte-stream lowering.
// - Allows:
//   - Inputs: pinned C frontend and guest stdio declarations.
//   - Outputs: forty-four distinct binary bytes.
//   - Side effects: guest byte output only.
// - Split-When:
//   - General guest byte-stream lowering supersedes finite witnesses.
// - Merge-When:
//   - Compiler examples demonstrate general mixed-byte output.
// - Summary:
//   - Emits forty-four ordered and distinct guest-computed binary bytes.
// - Description:
//   - The compiler and real VM independently verify forty-four ordered bytes.
// - Usage:
//   - c2malbolge --repository-tools --capsule \
//     --output .temp/emit-forty-four.malbolge \
//     docs/technical/examples/corpus/emit-forty-four.c
// - Defaults:
//   - This finite trace is not general C byte-stream support.
//
#include <stdio.h>

void emit(void) {
  putchar(90);
  putchar(38);
  putchar(71);
  putchar(11);
  putchar(62);
  putchar(9);
  putchar(45);
  putchar(19);
  putchar(52);
  putchar(165);
  putchar(6);
  putchar(175);
  putchar(243);
  putchar(168);
  putchar(47);
  putchar(17);
  putchar(65);
  putchar(15);
  putchar(48);
  putchar(25);
  putchar(55);
  putchar(8);
  putchar(77);
  putchar(50);
  putchar(78);
  putchar(31);
  putchar(87);
  putchar(41);
  putchar(68);
  putchar(10);
  putchar(212);
  putchar(153);
  putchar(221);
  putchar(160);
  putchar(204);
  putchar(170);
  putchar(211);
  putchar(7);
  putchar(213);
  putchar(145);
  putchar(222);
  putchar(161);
  putchar(220);
  putchar(171);
}
