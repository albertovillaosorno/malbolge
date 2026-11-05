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
//   - One fourteen-distinct-byte C-to-Malbolge teaching source.
// - Must-Not:
//   - Substitute host output or claim arbitrary byte-stream lowering.
// - Allows:
//   - Inputs: pinned C frontend and guest stdio declarations.
//   - Outputs: twelve printable bytes and two nontext control bytes.
//   - Side effects: guest byte output only.
// - Split-When:
//   - General guest byte-stream lowering supersedes finite witnesses.
// - Merge-When:
//   - Compiler examples demonstrate general mixed-byte output.
// - Summary:
//   - Emits fourteen ordered and distinct guest-computed binary bytes.
// - Description:
//   - The compiler and real VM independently verify fourteen ordered bytes.
// - Usage:
//   - c2malbolge --repository-tools --capsule \
//     --output .temp/emit-fourteen.malbolge \
//     docs/technical/examples/corpus/emit-fourteen.c
// - Defaults:
//   - This finite trace is not general C byte-stream support.
//
#include <stdio.h>

void emit(void) {
  putchar(89);
  putchar(69);
  putchar(44);
  putchar(72);
  putchar(83);
  putchar(23);
  putchar(76);
  putchar(79);
  putchar(61);
  putchar(64);
  putchar(91);
  putchar(49);
  putchar(25);
  putchar(52);
}
