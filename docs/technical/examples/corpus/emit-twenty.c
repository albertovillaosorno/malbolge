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
//   - One twenty-distinct-byte C-to-Malbolge teaching source.
// - Must-Not:
//   - Substitute host output or claim arbitrary byte-stream lowering.
// - Allows:
//   - Inputs: pinned C frontend and guest stdio declarations.
//   - Outputs: three printable, five control and twelve high-bit bytes.
//   - Side effects: guest byte output only.
// - Split-When:
//   - General guest byte-stream lowering supersedes finite witnesses.
// - Merge-When:
//   - Compiler examples demonstrate general mixed-byte output.
// - Summary:
//   - Emits twenty ordered and distinct guest-computed binary bytes.
// - Description:
//   - The compiler and real VM independently verify twenty ordered bytes.
// - Usage:
//   - c2malbolge --repository-tools --capsule \
//     --output .temp/emit-twenty.malbolge \
//     docs/technical/examples/corpus/emit-twenty.c
// - Defaults:
//   - This finite trace is not general C byte-stream support.
//
#include <stdio.h>

void emit(void) {
  putchar(62);
  putchar(20);
  putchar(53);
  putchar(18);
  putchar(63);
  putchar(10);
  putchar(164);
  putchar(156);
  putchar(173);
  putchar(163);
  putchar(26);
  putchar(168);
  putchar(162);
  putchar(149);
  putchar(171);
  putchar(159);
  putchar(152);
  putchar(29);
  putchar(172);
  putchar(174);
}
