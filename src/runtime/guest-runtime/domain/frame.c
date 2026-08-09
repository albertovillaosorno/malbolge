// Copyright:
//   - Copyright (c) 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - MIT
// Confidential:
//   - false
// License-File:
//   - LICENSE-MIT
//
// Boundary-Contract:
// - Owns:
//   - Canonical malbolge-c32-v1 hidden frame codec and shape checks.
// - Must-Not:
//   - Serialize native pointers, return addresses, or host stack state.
// - Allows:
//   - Inputs: fixed guest frame fields or exact 32-byte wire.
//   - Outputs: validated fields or deterministic frame rejection.
//   - Side effects: caller-owned frame or wire output only.
// - Split-When:
//   - Another calling-convention version needs its own codec.
// - Merge-When:
//   - Compiler lowering owns this exact guest-frame representation.
// - Summary:
//   - Little-endian codec for the version-one hidden frame header.
// - Description:
//   - Validates extent, argument block, alignment, and zero flags.
// - Usage:
//   - Used by startup helpers and downstream ternary lowering.
// - Defaults:
//   - Optional pointer fields use raw zero for canonical null.
//

//! Canonical hidden guest call-frame header representation and admission.

#include "guest_runtime.h"

#include <stddef.h>

#define FRAME_ALIGNMENT UINT32_C(16)
#define OFFSET_ARGUMENT_BLOCK UINT32_C(16)
#define OFFSET_CONTINUATION_ID UINT32_C(4)
#define OFFSET_FLAGS UINT32_C(28)
#define OFFSET_FRAME_EXTENT UINT32_C(12)
#define OFFSET_FUNCTION_ID UINT32_C(8)
#define OFFSET_PREVIOUS_FRAME UINT32_C(0)
#define OFFSET_RESULT_BLOCK UINT32_C(20)
#define OFFSET_VARIADIC_BEGIN UINT32_C(24)

static uint32_t read_u32(const uint8_t *bytes) {
  return (uint32_t)bytes[0] | ((uint32_t)bytes[1] << 8U) |
         ((uint32_t)bytes[2] << 16U) | ((uint32_t)bytes[3] << 24U);
}

static void write_u32(uint8_t *bytes, uint32_t value) {
  bytes[0] = (uint8_t)(value & UINT32_C(255));
  bytes[1] = (uint8_t)((value >> 8U) & UINT32_C(255));
  bytes[2] = (uint8_t)((value >> 16U) & UINT32_C(255));
  bytes[3] = (uint8_t)((value >> 24U) & UINT32_C(255));
}

static void copy_wire(uint8_t *destination, const uint8_t *source) {
  uint32_t index = 0U;

  while (index < MALBOLGE_GUEST_FRAME_HEADER_SIZE) {
    destination[index] = source[index];
    ++index;
  }
}

MalbolgeGuestRuntimeStatus
malbolge_guest_frame_validate(const MalbolgeGuestFrameHeader *frame) {
  if (frame == NULL) {
    return MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT;
  }
  if (frame->frame_extent < MALBOLGE_GUEST_FRAME_HEADER_SIZE ||
      (frame->frame_extent & (FRAME_ALIGNMENT - UINT32_C(1))) != UINT32_C(0) ||
      frame->argument_block == UINT32_C(0) || frame->flags != UINT32_C(0)) {
    return MALBOLGE_GUEST_RUNTIME_INVALID_FRAME;
  }
  return MALBOLGE_GUEST_RUNTIME_VALID;
}

MalbolgeGuestRuntimeStatus
malbolge_guest_frame_encode(const MalbolgeGuestFrameHeader *frame,
                            uint8_t *wire, uint32_t wire_size) {
  uint8_t encoded[MALBOLGE_GUEST_FRAME_HEADER_SIZE];
  MalbolgeGuestRuntimeStatus status = MALBOLGE_GUEST_RUNTIME_VALID;

  if (wire == NULL || wire_size != MALBOLGE_GUEST_FRAME_HEADER_SIZE) {
    return MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT;
  }
  status = malbolge_guest_frame_validate(frame);
  if (status != MALBOLGE_GUEST_RUNTIME_VALID) {
    return status;
  }
  write_u32(encoded + OFFSET_PREVIOUS_FRAME, frame->previous_frame);
  write_u32(encoded + OFFSET_CONTINUATION_ID, frame->continuation_id);
  write_u32(encoded + OFFSET_FUNCTION_ID, frame->function_id);
  write_u32(encoded + OFFSET_FRAME_EXTENT, frame->frame_extent);
  write_u32(encoded + OFFSET_ARGUMENT_BLOCK, frame->argument_block);
  write_u32(encoded + OFFSET_RESULT_BLOCK, frame->result_block);
  write_u32(encoded + OFFSET_VARIADIC_BEGIN, frame->variadic_begin);
  write_u32(encoded + OFFSET_FLAGS, frame->flags);
  copy_wire(wire, encoded);
  return MALBOLGE_GUEST_RUNTIME_VALID;
}

MalbolgeGuestRuntimeStatus
malbolge_guest_frame_decode(const uint8_t *wire, uint32_t wire_size,
                            MalbolgeGuestFrameHeader *frame) {
  MalbolgeGuestFrameHeader decoded;
  MalbolgeGuestRuntimeStatus status = MALBOLGE_GUEST_RUNTIME_VALID;

  if (wire == NULL || frame == NULL ||
      wire_size != MALBOLGE_GUEST_FRAME_HEADER_SIZE) {
    return MALBOLGE_GUEST_RUNTIME_INVALID_ARGUMENT;
  }
  decoded.previous_frame = read_u32(wire + OFFSET_PREVIOUS_FRAME);
  decoded.continuation_id = read_u32(wire + OFFSET_CONTINUATION_ID);
  decoded.function_id = read_u32(wire + OFFSET_FUNCTION_ID);
  decoded.frame_extent = read_u32(wire + OFFSET_FRAME_EXTENT);
  decoded.argument_block = read_u32(wire + OFFSET_ARGUMENT_BLOCK);
  decoded.result_block = read_u32(wire + OFFSET_RESULT_BLOCK);
  decoded.variadic_begin = read_u32(wire + OFFSET_VARIADIC_BEGIN);
  decoded.flags = read_u32(wire + OFFSET_FLAGS);
  status = malbolge_guest_frame_validate(&decoded);
  if (status != MALBOLGE_GUEST_RUNTIME_VALID) {
    return status;
  }
  frame->previous_frame = decoded.previous_frame;
  frame->continuation_id = decoded.continuation_id;
  frame->function_id = decoded.function_id;
  frame->frame_extent = decoded.frame_extent;
  frame->argument_block = decoded.argument_block;
  frame->result_block = decoded.result_block;
  frame->variadic_begin = decoded.variadic_begin;
  frame->flags = decoded.flags;
  return MALBOLGE_GUEST_RUNTIME_VALID;
}
