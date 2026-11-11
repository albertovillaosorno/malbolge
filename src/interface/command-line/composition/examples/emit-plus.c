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
//   - A real single-character source-C to guest-byte-output example.
// - Must-Not:
//   - Approximate an unsupported guest byte with host-side output logic.
// - Allows:
//   - Inputs: repository-pinned Clang and public guest stdio declaration.
//   - Outputs: one VM-verified ASCII plus-sign byte.
//   - Side effects: guest byte output only.
// - Split-When:
//   - General C character-stream support supersedes seeded byte emission.
// - Merge-When:
//   - The compiler demonstration suite owns all versioned guest examples.
// - Summary:
//   - Compile a single C character literal to a real guest output byte.
// - Description:
//   - The installed compiler and normative VM execute the witness.
// - Usage:
//   - c2malbolge --repository-tools --capsule --output .temp/emit-plus.malbolge
//     src/interface/command-line/composition/examples/emit-plus.c
// - Defaults:
//   - No arbitrary C output-string or guest libc support is implied.
//
#include <stdio.h>

void emit(void) {
  putchar('+');
}
