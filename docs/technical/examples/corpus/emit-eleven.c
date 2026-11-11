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
//   - One eleven-distinct-byte C-to-Malbolge binary teaching source.
// - Must-Not:
//   - Substitute host output or claim general binary stream lowering.
// - Allows:
//   - Inputs: pinned C frontend and guest stdio declarations.
//   - Outputs: eleven specific source-ordered binary bytes.
//   - Side effects: guest byte output only.
// - Split-When:
//   - General guest byte-stream lowering supersedes finite witnesses.
// - Merge-When:
//   - Compiler examples demonstrate general mixed-byte output.
// - Summary:
//   - Emits P, two control bytes, 6, ENQ and six high-bit bytes.
// - Description:
//   - The compiler and real VM independently verify eleven source-ordered bytes.
// - Usage:
//   - c2malbolge --repository-tools --capsule \
//     --output .temp/emit-eleven.malbolge \
//     docs/technical/examples/corpus/emit-eleven.c
// - Defaults:
//   - This exact finite trace is not general C byte-stream support.
//
#include <stdio.h>

void emit(void) {
  putchar('P');
  putchar(29);
  putchar(26);
  putchar('6');
  putchar(5);
  putchar(180);
  putchar(186);
  putchar(179);
  putchar(132);
  putchar(207);
  putchar(158);
}
