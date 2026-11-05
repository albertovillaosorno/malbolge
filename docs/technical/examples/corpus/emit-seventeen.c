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
//   - One seventeen-distinct-byte C-to-Malbolge teaching source.
// - Must-Not:
//   - Substitute host output or claim arbitrary byte-stream lowering.
// - Allows:
//   - Inputs: pinned C frontend and guest stdio declarations.
//   - Outputs: twelve printable and five control bytes.
//   - Side effects: guest byte output only.
// - Split-When:
//   - General guest byte-stream lowering supersedes finite witnesses.
// - Merge-When:
//   - Compiler examples demonstrate general mixed-byte output.
// - Summary:
//   - Emits seventeen ordered and distinct guest-computed binary bytes.
// - Description:
//   - The compiler and real VM independently verify seventeen ordered bytes.
// - Usage:
//   - c2malbolge --repository-tools --capsule \
//     --output .temp/emit-seventeen.malbolge \
//     docs/technical/examples/corpus/emit-seventeen.c
// - Defaults:
//   - This finite trace is not general C byte-stream support.
//
#include <stdio.h>

void emit(void) {
  putchar(89);
  putchar(63);
  putchar(44);
  putchar(72);
  putchar(80);
  putchar(27);
  putchar(24);
  putchar(50);
  putchar(21);
  putchar(77);
  putchar(75);
  putchar(59);
  putchar(66);
  putchar(15);
  putchar(68);
  putchar(48);
  putchar(23);
}
