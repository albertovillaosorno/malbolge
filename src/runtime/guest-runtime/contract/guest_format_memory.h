// Copyright:
//   - Copyright © 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - MIT
// Confidential:
//   - false
// License-File:
//   - LICENSE-MIT
//
// Boundary-Contract:
// - Owns:
//   - Bounded guest-object access for resolved %s and %n conversions.
// - Must-Not:
//   - Infer pointer provenance, expose host pointer identity, or use host libc.
// - Allows:
//   - Inputs: one caller-validated live guest object and a resolved conversion.
//   - Outputs: deterministic narrow-string bytes or canonical count storage.
//   - Side effects: bounded sink writes for %s or guest-object bytes for %n.
// - Split-When:
//   - Wide strings or another pointer-backed conversion needs separate policy.
// - Merge-When:
//   - Complete formatter execution owns this exact guest-memory boundary.
// - Summary:
//   - Executes pointer-backed printf conversions inside one proven guest
//     object.
// - Description:
//   - Object pointers use the malbolge-c32-v1 logical offset-plus-one encoding.
// - Usage:
//   - Called after parser admission and atomic promoted-argument resolution.
// - Defaults:
//   - Null, out-of-object, unterminated, misaligned, or overflowing access
//     fails.
//

//! Guest-object memory boundary for narrow string and count formatting.

#ifndef MALBOLGE_GUEST_FORMAT_MEMORY_H
#define MALBOLGE_GUEST_FORMAT_MEMORY_H

#include "guest_format_args.h"

#include <stdint.h>

typedef struct MalbolgeGuestMemoryView {
  uint8_t *bytes;
  uint32_t extent;
  uint32_t encoded_base;
} MalbolgeGuestMemoryView;

MalbolgeGuestRuntimeStatus malbolge_guest_memory_view_validate(
    const MalbolgeGuestMemoryView *view);
MalbolgeGuestRuntimeStatus malbolge_guest_format_execute_memory(
    MalbolgeGuestFormatSink *sink, MalbolgeGuestMemoryView *view,
    const MalbolgeGuestResolvedFormatArgument *resolved);

#endif
