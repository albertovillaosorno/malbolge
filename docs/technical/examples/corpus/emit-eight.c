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
//   - One eight-distinct-byte C-to-Malbolge binary teaching source.
// - Must-Not:
//   - Substitute host output or claim arbitrary byte-stream lowering.
// - Allows:
//   - Inputs: repository-pinned Clang and guest stdio declarations.
//   - Outputs: eight separately computed guest bytes including controls.
//   - Side effects: guest byte output only.
// - Split-When:
//   - General guest byte-stream lowering supersedes exact witnesses.
// - Merge-When:
//   - Compiler examples demonstrate general mixed-byte output.
// - Summary:
//   - Emits S, space, ETB, <, 6, SOH, R, ACK from guest arithmetic.
// - Description:
//   - The compiler and VM independently verify eight source-ordered bytes.
// - Usage:
//   - c2malbolge --repository-tools --capsule \
//     --output .temp/emit-eight.malbolge \
//     docs/technical/examples/corpus/emit-eight.c
// - Defaults:
//   - This exact finite trace is not general C string-output support.
//
#include <stdio.h>

void emit(void) {
  putchar('S');
  putchar(32);
  putchar(23);
  putchar('<');
  putchar('6');
  putchar(1);
  putchar('R');
  putchar(6);
}
