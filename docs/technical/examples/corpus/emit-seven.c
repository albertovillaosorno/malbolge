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
//   - One seven-distinct-byte C-to-Malbolge binary teaching source.
// - Must-Not:
//   - Substitute host output or claim general binary stream lowering.
// - Allows:
//   - Inputs: repository-pinned Clang and guest stdio declarations.
//   - Outputs: seven guest-computed bytes, including control codes.
//   - Side effects: guest byte output only.
// - Split-When:
//   - General guest byte-stream lowering supersedes exact witnesses.
// - Merge-When:
//   - Compiler examples demonstrate general mixed-byte output.
// - Summary:
//   - Emits 6, >, 5, STX, T, US, CAN from guest CrazyData effects.
// - Description:
//   - The compiler and VM independently verify seven ordered output bytes.
// - Usage:
//   - c2malbolge --repository-tools --capsule \
//     --output .temp/emit-seven.malbolge \
//     docs/technical/examples/corpus/emit-seven.c
// - Defaults:
//   - This exact finite trace is not an arbitrary guest output API.
//
#include <stdio.h>

void emit(void) {
  putchar('6');
  putchar('>');
  putchar('5');
  putchar(2);
  putchar('T');
  putchar(31);
  putchar(24);
}
