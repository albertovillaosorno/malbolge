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
//   - A real supported source-C to guest-byte-output example.
// - Must-Not:
//   - Rely on host process exit, arbitrary libc, or unsupported guest lowering.
// - Allows:
//   - Inputs: repository-pinned Clang and public guest stdio declaration.
//   - Outputs: two VM-verified ASCII A bytes.
//   - Side effects: guest byte output only.
// - Split-When:
//   - Additional supported examples require distinct guest semantics.
// - Merge-When:
//   - The compiler demonstration suite owns all versioned guest examples.
// - Summary:
//   - Compile two source character literals with an implicit void return.
// - Description:
//   - The installed compiler and normative VM verify actual guest output.
// - Usage:
//   - c2malbolge --repository-tools --capsule --output .temp/emit-aa.malbolge
//     src/interface/command-line/composition/examples/emit-aa.c
// - Defaults:
//   - No general printf, main-return or mixed-byte support is implied.
//
#include <stdio.h>

void emit(void) {
  putchar('A');
  putchar('A');
}
