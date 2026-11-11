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
//   - One nineteen-distinct-byte C-to-Malbolge teaching source.
// - Must-Not:
//   - Substitute host output or claim arbitrary byte-stream lowering.
// - Allows:
//   - Inputs: pinned C frontend and guest stdio declarations.
//   - Outputs: twelve printable and seven control bytes.
//   - Side effects: guest byte output only.
// - Split-When:
//   - General guest byte-stream lowering supersedes finite witnesses.
// - Merge-When:
//   - Compiler examples demonstrate general mixed-byte output.
// - Summary:
//   - Emits nineteen ordered and distinct guest-computed binary bytes.
// - Description:
//   - The compiler and real VM independently verify nineteen ordered bytes.
// - Usage:
//   - c2malbolge --repository-tools --capsule \
//     --output .temp/emit-nineteen.malbolge \
//     docs/technical/examples/corpus/emit-nineteen.c
// - Defaults:
//   - This finite trace is not general C byte-stream support.
//
#include <stdio.h>

void emit(void) {
  putchar(83);
  putchar(33);
  putchar(26);
  putchar(60);
  putchar(56);
  putchar(3);
  putchar(23);
  putchar(85);
  putchar(14);
  putchar(73);
  putchar(43);
  putchar(16);
  putchar(70);
  putchar(22);
  putchar(64);
  putchar(76);
  putchar(58);
  putchar(25);
  putchar(88);
}
