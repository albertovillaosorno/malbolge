// File:
//   - abi.h
// Path:
//   - cli/adapters/doom/abi.h
//
// Copyright:
//   - Copyright (c) 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - MIT
// Confidential:
//   - false
// License-File:
//   - LICENSE
// Path-Rule:
//   - All paths in this header are repository-root relative.
//
// Boundary-Contract:
// - Owns:
//   - C declarations shared by the portable DOOM core and debug host adapters.
// - Must-Not:
//   - Encode one operating system implementation or guest execution policy.
// - Allows:
//   - Inputs: version-one DOOM host capability requests.
//   - Outputs: stable C types and function signatures.
//   - Side effects: none.
// - Split-When:
//   - Split when a later ABI version is intentionally introduced.
// - Merge-When:
//   - Merge when the canonical capability ABI moves to a shared runtime header.
// - Summary:
//   - Version-one DOOM host-service C ABI for native debugging.
// - Description:
//   - Keeps the debug adapter type-compatible with generated single-TU DOOM.
// - Usage:
//   - Included by host adapters, never by the generated `doom.c` artifact.
// - Defaults:
//   - Integer-valued historical DOOM booleans remain `int`.
//
// Related documents:
// - cli/README.md
// - docs/technical/runtime/execution/versioned-host-capability-call-abi.md
//
// Large file:
//   - false

#ifndef MALBOLGE_CLI_DOOM_ABI_H
#define MALBOLGE_CLI_DOOM_ABI_H

#include <stdint.h>

typedef int boolean;
typedef unsigned char byte;

typedef enum
{
    DOOM_HOST_EVENT_NONE,
    DOOM_HOST_EVENT_KEY_DOWN,
    DOOM_HOST_EVENT_KEY_UP,
    DOOM_HOST_EVENT_MOUSE,
    DOOM_HOST_EVENT_QUIT
} doom_host_event_type_t;

typedef enum
{
    DOOM_HOST_KEY_NONE = 0,
    DOOM_HOST_KEY_LEFT = 256,
    DOOM_HOST_KEY_RIGHT,
    DOOM_HOST_KEY_UP,
    DOOM_HOST_KEY_DOWN,
    DOOM_HOST_KEY_ESCAPE,
    DOOM_HOST_KEY_ENTER,
    DOOM_HOST_KEY_TAB,
    DOOM_HOST_KEY_BACKSPACE,
    DOOM_HOST_KEY_PAUSE,
    DOOM_HOST_KEY_F1,
    DOOM_HOST_KEY_F2,
    DOOM_HOST_KEY_F3,
    DOOM_HOST_KEY_F4,
    DOOM_HOST_KEY_F5,
    DOOM_HOST_KEY_F6,
    DOOM_HOST_KEY_F7,
    DOOM_HOST_KEY_F8,
    DOOM_HOST_KEY_F9,
    DOOM_HOST_KEY_F10,
    DOOM_HOST_KEY_F11,
    DOOM_HOST_KEY_F12,
    DOOM_HOST_KEY_SHIFT,
    DOOM_HOST_KEY_CONTROL,
    DOOM_HOST_KEY_ALT
} doom_host_key_t;

typedef struct
{
    doom_host_event_type_t type;
    int key;
    int mouse_buttons;
    int mouse_dx;
    int mouse_dy;
} doom_host_event_t;

typedef struct
{
    int logical_width;
    int logical_height;
    int display_aspect_width;
    int display_aspect_height;
    int minimum_present_hz;
    boolean borderless;
    boolean relative_mouse;
    const char *title;
} doom_host_video_config_t;

typedef uint32_t doom_host_file_t;
typedef uint32_t doom_host_net_endpoint_t;

typedef struct
{
    int sample_rate;
    int channel_count;
    int frames_per_buffer;
} doom_host_audio_config_t;

void *DoomHost_GuestMemoryRegion(int *byte_count);
void DoomHost_ReportError(const char *text, int length);
[[noreturn]] void DoomHost_Terminate(int status);
boolean DoomHost_VideoInitialize(const doom_host_video_config_t *config);
void DoomHost_VideoShutdown(void);
boolean DoomHost_PollEvent(doom_host_event_t *event);
void DoomHost_SetPalette(const byte *rgb_palette, int color_count);
void DoomHost_PresentIndexed8(const byte *pixels, int width, int height,
                              int pitch);
boolean DoomHost_AudioInitialize(const doom_host_audio_config_t *config);
void DoomHost_AudioShutdown(void);
int DoomHost_AudioWritableFrames(void);
void DoomHost_AudioSubmitS16(const int16_t *samples, int frame_count,
                             int channel_count);
boolean DoomHost_FileOpenRead(const char *path, doom_host_file_t *file);
void DoomHost_FileClose(doom_host_file_t file);
int DoomHost_FileSize(doom_host_file_t file);
int DoomHost_FileReadAt(doom_host_file_t file, int offset, byte *data,
                        int length);
boolean DoomHost_FileWriteAll(const char *path, const byte *data, int length);
boolean DoomHost_NetOpen(int local_port);
void DoomHost_NetClose(void);
boolean DoomHost_NetResolve(const char *host, int port,
                            doom_host_net_endpoint_t *endpoint);
boolean DoomHost_NetSend(doom_host_net_endpoint_t endpoint, const byte *data,
                         int length);
int DoomHost_NetReceive(byte *data, int capacity,
                        doom_host_net_endpoint_t *source);
uint64_t DoomHost_MonotonicNanoseconds(void);
void DoomHost_SleepNanoseconds(uint64_t nanoseconds);

#endif
