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
//   - One ten-distinct-byte C-to-Malbolge binary teaching source.
// - Must-Not:
//   - Substitute host output or claim arbitrary byte-stream lowering.
// - Allows:
//   - Inputs: pinned C frontend and guest stdio declarations.
//   - Outputs: two printable ASCII bytes and eight distinct high-bit bytes.
//   - Side effects: guest byte output only.
// - Split-When:
//   - General guest byte-stream lowering supersedes finite witnesses.
// - Merge-When:
//   - Compiler examples demonstrate general mixed-byte output.
// - Summary:
//   - Emits Q, a quote mark, and eight distinct high-bit binary bytes.
// - Description:
//   - The compiler and real VM independently verify ten source-ordered bytes.
// - Usage:
//   - c2malbolge --repository-tools --capsule \
//     --output .temp/emit-ten.malbolge \
//     docs/technical/examples/corpus/emit-ten.c
// - Defaults:
//   - This exact finite trace is not general C byte-stream support.
//
#include <stdio.h>

void emit(void) {
  putchar('Q');
  putchar('"');
  putchar(253);
  putchar(206);
  putchar(165);
  putchar(152);
  putchar(186);
  putchar(182);
  putchar(135);
  putchar(203);
}
