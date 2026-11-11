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
//   - One nine-distinct-byte C-to-Malbolge binary teaching source.
// - Must-Not:
//   - Substitute host output or claim arbitrary byte-stream lowering.
// - Allows:
//   - Inputs: repository-pinned Clang and guest stdio declarations.
//   - Outputs: nine distinct guest bytes, seven with the high bit set.
//   - Side effects: guest byte output only.
// - Split-When:
//   - General guest byte-stream lowering supersedes finite witnesses.
// - Merge-When:
//   - Compiler examples demonstrate general mixed-byte output.
// - Summary:
//   - Emits T, =, and seven distinct high-bit bytes in guest arithmetic.
// - Description:
//   - The compiler and VM independently verify nine source-ordered bytes.
// - Usage:
//   - c2malbolge --repository-tools --capsule \
//     --output .temp/emit-nine.malbolge \
//     docs/technical/examples/corpus/emit-nine.c
// - Defaults:
//   - This exact finite trace is not general C string-output support.
//
#include <stdio.h>

void emit(void) {
  putchar(84);
  putchar(61);
  putchar(141);
  putchar(209);
  putchar(192);
  putchar(180);
  putchar(191);
  putchar(210);
  putchar(162);
}
