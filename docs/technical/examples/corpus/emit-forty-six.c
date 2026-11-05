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
//   - One forty-six-distinct-byte C-to-Malbolge teaching source.
// - Must-Not:
//   - Substitute host output or claim arbitrary byte-stream lowering.
// - Allows:
//   - Inputs: pinned C frontend and guest stdio declarations.
//   - Outputs: forty-six distinct binary bytes.
//   - Side effects: guest byte output only.
// - Split-When:
//   - General guest byte-stream lowering supersedes finite witnesses.
// - Merge-When:
//   - Compiler examples demonstrate general mixed-byte output.
// - Summary:
//   - Emits forty-six ordered and distinct guest-computed binary bytes.
// - Description:
//   - The compiler and real VM independently verify forty-six ordered bytes.
// - Usage:
//   - c2malbolge --repository-tools --capsule \
//     --output .temp/emit-forty-six.malbolge \
//     docs/technical/examples/corpus/emit-forty-six.c
// - Defaults:
//   - This finite trace is not general C byte-stream support.
//
#include <stdio.h>

void emit(void) {
  putchar(84);
  putchar(34);
  putchar(79);
  putchar(35);
  putchar(83);
  putchar(30);
  putchar(9);
  putchar(8);
  putchar(226);
  putchar(171);
  putchar(221);
  putchar(126);
  putchar(192);
  putchar(125);
  putchar(186);
  putchar(129);
  putchar(188);
  putchar(123);
  putchar(42);
  putchar(16);
  putchar(48);
  putchar(14);
  putchar(47);
  putchar(17);
  putchar(45);
  putchar(163);
  putchar(255);
  putchar(167);
  putchar(0);
  putchar(162);
  putchar(1);
  putchar(166);
  putchar(252);
  putchar(207);
  putchar(165);
  putchar(206);
  putchar(159);
  putchar(210);
  putchar(161);
  putchar(204);
  putchar(144);
  putchar(227);
  putchar(174);
  putchar(225);
  putchar(173);
  putchar(228);
}
