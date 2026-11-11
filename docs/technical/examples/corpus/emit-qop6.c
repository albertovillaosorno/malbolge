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
//   - A six-distinct-byte C-to-Malbolge binary teaching source.
// - Must-Not:
//   - Substitute host output or claim general binary stream lowering.
// - Allows:
//   - Inputs: repository-pinned Clang and guest stdio declarations.
//   - Outputs: six separately computed guest bytes including three controls.
//   - Side effects: guest byte output only.
// - Split-When:
//   - General guest byte-stream lowering supersedes exact witnesses.
// - Merge-When:
//   - Compiler examples demonstrate general mixed-byte output.
// - Summary:
//   - Emits Q, FS, O, GS, P, ESC using guest CrazyData effects.
// - Description:
//   - The compiler and VM independently verify six source-ordered bytes.
// - Usage:
//   - c2malbolge --repository-tools --capsule \
//     --output .temp/emit-qop6.malbolge \
//     docs/technical/examples/corpus/emit-qop6.c
// - Defaults:
//   - This sequence is a finite witness, not an arbitrary output API.
//
#include <stdio.h>

void emit(void) {
  putchar(81);
  putchar(28);
  putchar(79);
  putchar(29);
  putchar(80);
  putchar(27);
}
