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
//   - SDL2/Linux implementations of the version-one DOOM host-service ABI.
// - Must-Not:
//   - Embed IWAD bytes, define the game entrypoint, or alter guest semantics.
// - Allows:
//   - Inputs: portable DOOM capability calls and host window/input/audio state.
//   - Outputs: SDL2 presentation, input, files, timing, and process services.
//   - Side effects: one debug window, retained host frame storage, audio device
//     I/O, and caller-requested files.
// - Split-When:
//   - Networking or another host capability needs an independent owner.
// - Merge-When:
//   - A shared cross-platform adapter owns identical SDL2 behavior.
// - Summary:
//   - Native Linux debug adapter for the normalized portable DOOM guest.
// - Description:
//   - Runs the generated portable C guest natively for fast Linux validation.
// - Usage:
//   - Linked by build-linux.sh for local testing; never part of guest C.
// - Defaults:
//   - Decorated 1280x720 window, relative mouse in-game, no networking.
//

#define SDL_MAIN_HANDLED
#include <SDL2/SDL.h>

#include <errno.h>
#include <limits.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>

#include "abi.h"

#define GUEST_MEMORY_BYTES (64 * 1024 * 1024)
#define HOST_FILE_CAPACITY 64
#define AUDIO_BLOCK_COUNT 8
#define LINUX_MOUSE_DELTA_SCALE 4

_Alignas(16) static unsigned char guest_memory[GUEST_MEMORY_BYTES];
static FILE *file_handles[HOST_FILE_CAPACITY];

static SDL_Window *window_handle;
static SDL_Renderer *renderer;
static SDL_Texture *texture;
static doom_host_video_config_t video_config;
static uint32_t palette_rgba[256];
static uint32_t *frame_rgba;
static size_t frame_rgba_capacity;
static int texture_width;
static int texture_height;
static int mouse_buttons;

static SDL_AudioDeviceID audio_device;
static int audio_frames_per_buffer;
static int audio_channels;
static int audio_capacity_frames;

static boolean EnsureSdl(uint32_t flags)
{
    if (SDL_WasInit(0) == 0 && SDL_Init(0) != 0)
        return false;
    if ((SDL_WasInit(flags) & flags) != flags && SDL_InitSubSystem(flags) != 0)
        return false;
    return true;
}

static int MapKey(SDL_Keycode key)
{
    switch (key)
    {
        case SDLK_LEFT:
            return DOOM_HOST_KEY_LEFT;
        case SDLK_RIGHT:
            return DOOM_HOST_KEY_RIGHT;
        case SDLK_UP:
            return DOOM_HOST_KEY_UP;
        case SDLK_DOWN:
            return DOOM_HOST_KEY_DOWN;
        case SDLK_ESCAPE:
            return DOOM_HOST_KEY_ESCAPE;
        case SDLK_RETURN:
        case SDLK_KP_ENTER:
            return DOOM_HOST_KEY_ENTER;
        case SDLK_TAB:
            return DOOM_HOST_KEY_TAB;
        case SDLK_BACKSPACE:
            return DOOM_HOST_KEY_BACKSPACE;
        case SDLK_PAUSE:
            return DOOM_HOST_KEY_PAUSE;
        case SDLK_F1:
            return DOOM_HOST_KEY_F1;
        case SDLK_F2:
            return DOOM_HOST_KEY_F2;
        case SDLK_F3:
            return DOOM_HOST_KEY_F3;
        case SDLK_F4:
            return DOOM_HOST_KEY_F4;
        case SDLK_F5:
            return DOOM_HOST_KEY_F5;
        case SDLK_F6:
            return DOOM_HOST_KEY_F6;
        case SDLK_F7:
            return DOOM_HOST_KEY_F7;
        case SDLK_F8:
            return DOOM_HOST_KEY_F8;
        case SDLK_F9:
            return DOOM_HOST_KEY_F9;
        case SDLK_F10:
            return DOOM_HOST_KEY_F10;
        case SDLK_F11:
            return DOOM_HOST_KEY_F11;
        case SDLK_F12:
            return DOOM_HOST_KEY_F12;
        case SDLK_LSHIFT:
        case SDLK_RSHIFT:
            return DOOM_HOST_KEY_SHIFT;
        case SDLK_LCTRL:
        case SDLK_RCTRL:
            return DOOM_HOST_KEY_CONTROL;
        case SDLK_LALT:
        case SDLK_RALT:
            return DOOM_HOST_KEY_ALT;
        default:
            if (key >= 32 && key <= 126)
                return (int)key;
            return DOOM_HOST_KEY_NONE;
    }
}

static int MouseButtonBit(uint8_t button)
{
    switch (button)
    {
        case SDL_BUTTON_LEFT:
            return 1;
        case SDL_BUTTON_MIDDLE:
            return 2;
        case SDL_BUTTON_RIGHT:
            return 4;
        default:
            return 0;
    }
}

void *DoomHost_GuestMemoryRegion(int *byte_count)
{
    if (byte_count == NULL)
        return NULL;
    *byte_count = GUEST_MEMORY_BYTES;
    return guest_memory;
}

void DoomHost_ReportError(const char *text, int length)
{
    char message[2048];
    int count;
    if (text == NULL || length < 0)
        return;
    count = length;
    if (count >= (int)sizeof(message))
        count = (int)sizeof(message) - 1;
    for (int index = 0; index < count; ++index)
        message[index] = text[index];
    message[count] = '\0';
    (void)fprintf(stderr, "DOOM fatal error: %s\n", message);
    if (window_handle != NULL)
        (void)SDL_ShowSimpleMessageBox(SDL_MESSAGEBOX_ERROR, "DOOM fatal error",
                                       message, window_handle);
}

[[noreturn]] void DoomHost_Terminate(int status)
{
    DoomHost_AudioShutdown();
    DoomHost_VideoShutdown();
    SDL_Quit();
    exit(status);
}

boolean DoomHost_VideoInitialize(const doom_host_video_config_t *config)
{
    uint32_t flags = SDL_WINDOW_SHOWN | SDL_WINDOW_RESIZABLE;
    if (config == NULL || config->logical_width <= 0 ||
        config->logical_height <= 0 || config->display_aspect_width <= 0 ||
        config->display_aspect_height <= 0)
        return false;
    if (!EnsureSdl(SDL_INIT_VIDEO | SDL_INIT_EVENTS))
    {
        (void)fprintf(stderr, "SDL video init failed: %s\n", SDL_GetError());
        return false;
    }
    video_config = *config;
    // Native debug windows stay decorated so the desktop window
    // manager can minimize, maximize, move, and close them normally.
    (void)config->borderless;
    window_handle = SDL_CreateWindow(
        config->title != NULL ? config->title : "DOOM", SDL_WINDOWPOS_CENTERED,
        SDL_WINDOWPOS_CENTERED, 1280, 720, flags);
    if (window_handle == NULL)
    {
        (void)fprintf(stderr, "SDL window failed: %s\n", SDL_GetError());
        return false;
    }
    renderer = SDL_CreateRenderer(window_handle, -1,
                                  SDL_RENDERER_ACCELERATED |
                                      SDL_RENDERER_PRESENTVSYNC);
    if (renderer == NULL)
        renderer = SDL_CreateRenderer(window_handle, -1, SDL_RENDERER_SOFTWARE);
    if (renderer == NULL)
    {
        (void)fprintf(stderr, "SDL renderer failed: %s\n", SDL_GetError());
        DoomHost_VideoShutdown();
        return false;
    }
    texture = SDL_CreateTexture(renderer, SDL_PIXELFORMAT_ARGB8888,
                                SDL_TEXTUREACCESS_STREAMING,
                                config->logical_width, config->logical_height);
    if (texture == NULL)
    {
        (void)fprintf(stderr, "SDL texture failed: %s\n", SDL_GetError());
        DoomHost_VideoShutdown();
        return false;
    }
    texture_width = config->logical_width;
    texture_height = config->logical_height;
    if (config->relative_mouse)
        DoomHost_SetRelativeMouseCapture(true);
    SDL_RaiseWindow(window_handle);
    return true;
}

void DoomHost_VideoShutdown(void)
{
    if (texture != NULL)
        SDL_DestroyTexture(texture);
    if (renderer != NULL)
        SDL_DestroyRenderer(renderer);
    if (window_handle != NULL)
        SDL_DestroyWindow(window_handle);
    texture = NULL;
    renderer = NULL;
    window_handle = NULL;
    texture_width = 0;
    texture_height = 0;
    free(frame_rgba);
    frame_rgba = NULL;
    frame_rgba_capacity = 0;
    if (SDL_WasInit(SDL_INIT_VIDEO) != 0)
        SDL_QuitSubSystem(SDL_INIT_VIDEO | SDL_INIT_EVENTS);
}

boolean DoomHost_PollEvent(doom_host_event_t *event)
{
    SDL_Event source;
    if (event == NULL)
        return false;
    while (SDL_PollEvent(&source))
    {
        *event = (doom_host_event_t) {0};
        switch (source.type)
        {
            case SDL_QUIT:
                event->type = DOOM_HOST_EVENT_QUIT;
                return true;
            case SDL_KEYDOWN:
            case SDL_KEYUP:
                {
                    const int mapped = MapKey(source.key.keysym.sym);
                    if (mapped == DOOM_HOST_KEY_NONE)
                        continue;
                    if (source.type == SDL_KEYDOWN && source.key.repeat != 0)
                        continue;
                    event->type = source.type == SDL_KEYDOWN
                                      ? DOOM_HOST_EVENT_KEY_DOWN
                                      : DOOM_HOST_EVENT_KEY_UP;
                    event->key = mapped;
                    return true;
                }
            case SDL_MOUSEMOTION:
                event->type = DOOM_HOST_EVENT_MOUSE;
                event->mouse_buttons = mouse_buttons;
                event->mouse_dx = source.motion.xrel * LINUX_MOUSE_DELTA_SCALE;
                event->mouse_dy = source.motion.yrel * LINUX_MOUSE_DELTA_SCALE;
                return true;
            case SDL_MOUSEBUTTONDOWN:
            case SDL_MOUSEBUTTONUP:
                {
                    const int bit = MouseButtonBit(source.button.button);
                    if (bit == 0)
                        continue;
                    if (source.type == SDL_MOUSEBUTTONDOWN)
                        mouse_buttons |= bit;
                    else
                        mouse_buttons &= ~bit;
                    event->type = DOOM_HOST_EVENT_MOUSE;
                    event->mouse_buttons = mouse_buttons;
                    return true;
                }
            default:
                break;
        }
    }
    return false;
}

void DoomHost_SetRelativeMouseCapture(boolean capture)
{
    (void)SDL_SetRelativeMouseMode(capture ? SDL_TRUE : SDL_FALSE);
    if (window_handle != NULL)
        SDL_SetWindowGrab(window_handle, capture ? SDL_TRUE : SDL_FALSE);
}

void DoomHost_SetPalette(const byte *rgb_palette, int color_count)
{
    if (rgb_palette == NULL || color_count < 0)
        return;
    if (color_count > 256)
        color_count = 256;
    for (int index = 0; index < color_count; ++index)
    {
        const uint32_t red = rgb_palette[index * 3 + 0];
        const uint32_t green = rgb_palette[index * 3 + 1];
        const uint32_t blue = rgb_palette[index * 3 + 2];
        palette_rgba[index] =
            UINT32_C(0xff000000) | (red << 16) | (green << 8) | blue;
    }
}

void DoomHost_PresentIndexed8(const byte *pixels, int width, int height,
                              int pitch)
{
    size_t needed;
    int output_width;
    int output_height;
    SDL_Rect destination;
    if (pixels == NULL || renderer == NULL || width <= 0 || height <= 0 ||
        pitch < width)
        return;
    needed = (size_t)width * (size_t)height;
    if (needed > frame_rgba_capacity)
    {
        uint32_t *replacement =
            realloc(frame_rgba, needed * sizeof(*replacement));
        if (replacement == NULL)
            return;
        frame_rgba = replacement;
        frame_rgba_capacity = needed;
    }
    if (texture == NULL || texture_width != width || texture_height != height)
    {
        if (texture != NULL)
            SDL_DestroyTexture(texture);
        texture = SDL_CreateTexture(renderer, SDL_PIXELFORMAT_ARGB8888,
                                    SDL_TEXTUREACCESS_STREAMING, width, height);
        if (texture == NULL)
            return;
        texture_width = width;
        texture_height = height;
    }
    for (int y = 0; y < height; ++y)
    {
        for (int x = 0; x < width; ++x)
            frame_rgba[(size_t)y * (size_t)width + (size_t)x] =
                palette_rgba[pixels[y * pitch + x]];
    }
    if (SDL_UpdateTexture(texture, NULL, frame_rgba,
                          width * (int)sizeof(uint32_t)) != 0)
        return;
    if (SDL_GetRendererOutputSize(renderer, &output_width, &output_height) != 0)
        return;
    {
        const double desired = (double)video_config.display_aspect_width /
                               (double)video_config.display_aspect_height;
        const double actual = (double)output_width / (double)output_height;
        if (actual > desired)
        {
            destination.h = output_height;
            destination.w = (int)((double)output_height * desired + 0.5);
            destination.x = (output_width - destination.w) / 2;
            destination.y = 0;
        }
        else
        {
            destination.w = output_width;
            destination.h = (int)((double)output_width / desired + 0.5);
            destination.x = 0;
            destination.y = (output_height - destination.h) / 2;
        }
    }
    (void)SDL_SetRenderDrawColor(renderer, 0, 0, 0, 255);
    (void)SDL_RenderClear(renderer);
    (void)SDL_RenderCopy(renderer, texture, NULL, &destination);
    SDL_RenderPresent(renderer);
}

boolean DoomHost_AudioInitialize(const doom_host_audio_config_t *config)
{
    SDL_AudioSpec desired;
    SDL_AudioSpec obtained;
    if (config == NULL || config->sample_rate <= 0 ||
        config->channel_count <= 0 || config->frames_per_buffer <= 0)
        return false;
    if (!EnsureSdl(SDL_INIT_AUDIO))
    {
        (void)fprintf(stderr, "SDL audio init failed: %s\n", SDL_GetError());
        return false;
    }
    SDL_zero(desired);
    desired.freq = config->sample_rate;
    desired.format = AUDIO_S16SYS;
    desired.channels = (uint8_t)config->channel_count;
    desired.samples = (uint16_t)config->frames_per_buffer;
    desired.callback = NULL;
    audio_device = SDL_OpenAudioDevice(NULL, 0, &desired, &obtained, 0);
    if (audio_device == 0)
    {
        (void)fprintf(stderr, "SDL audio open failed: %s\n", SDL_GetError());
        return false;
    }
    if (obtained.freq != desired.freq || obtained.format != desired.format ||
        obtained.channels != desired.channels)
    {
        (void)fprintf(stderr, "SDL audio format mismatch\n");
        DoomHost_AudioShutdown();
        return false;
    }
    audio_frames_per_buffer = config->frames_per_buffer;
    audio_channels = config->channel_count;
    audio_capacity_frames = AUDIO_BLOCK_COUNT * audio_frames_per_buffer;
    SDL_PauseAudioDevice(audio_device, 0);
    return true;
}

void DoomHost_AudioShutdown(void)
{
    if (audio_device != 0)
    {
        SDL_ClearQueuedAudio(audio_device);
        SDL_CloseAudioDevice(audio_device);
    }
    audio_device = 0;
    audio_frames_per_buffer = 0;
    audio_channels = 0;
    audio_capacity_frames = 0;
    if (SDL_WasInit(SDL_INIT_AUDIO) != 0)
        SDL_QuitSubSystem(SDL_INIT_AUDIO);
}

int DoomHost_AudioWritableFrames(void)
{
    uint32_t queued_bytes;
    int queued_frames;
    if (audio_device == 0 || audio_channels <= 0)
        return 0;
    queued_bytes = SDL_GetQueuedAudioSize(audio_device);
    queued_frames = (int)(queued_bytes / ((uint32_t)audio_channels *
                                          (uint32_t)sizeof(int16_t)));
    if (queued_frames >= audio_capacity_frames)
        return 0;
    return audio_capacity_frames - queued_frames;
}

void DoomHost_AudioSubmitS16(const int16_t *samples, int frame_count,
                             int channel_count)
{
    uint32_t bytes;
    if (audio_device == 0 || samples == NULL || frame_count <= 0 ||
        channel_count != audio_channels)
        return;
    bytes = (uint32_t)frame_count * (uint32_t)channel_count *
            (uint32_t)sizeof(int16_t);
    (void)SDL_QueueAudio(audio_device, samples, bytes);
}

static boolean ValidFile(doom_host_file_t file)
{
    return file > 0 && file < HOST_FILE_CAPACITY && file_handles[file] != NULL;
}

boolean DoomHost_FileOpenRead(const char *path, doom_host_file_t *file)
{
    FILE *opened;
    int index;
    if (path == NULL || file == NULL)
        return false;
    opened = fopen(path, "rb");
    if (opened == NULL)
        return false;
    for (index = 1; index < HOST_FILE_CAPACITY; ++index)
        if (file_handles[index] == NULL)
            break;
    if (index == HOST_FILE_CAPACITY)
    {
        (void)fclose(opened);
        return false;
    }
    file_handles[index] = opened;
    *file = (doom_host_file_t)index;
    return true;
}

void DoomHost_FileClose(doom_host_file_t file)
{
    if (!ValidFile(file))
        return;
    (void)fclose(file_handles[file]);
    file_handles[file] = NULL;
}

int DoomHost_FileSize(doom_host_file_t file)
{
    long size;
    if (!ValidFile(file))
        return -1;
    if (fseek(file_handles[file], 0, SEEK_END) != 0)
        return -1;
    size = ftell(file_handles[file]);
    if (size < 0 || size > INT_MAX)
        return -1;
    return (int)size;
}

int DoomHost_FileReadAt(doom_host_file_t file, int offset, byte *data,
                        int length)
{
    size_t count;
    if (!ValidFile(file) || offset < 0 || data == NULL || length < 0)
        return -1;
    if (fseek(file_handles[file], offset, SEEK_SET) != 0)
        return -1;
    count = fread(data, 1, (size_t)length, file_handles[file]);
    if (count > (size_t)INT_MAX)
        return -1;
    return (int)count;
}

boolean DoomHost_FileWriteAll(const char *path, const byte *data, int length)
{
    FILE *file;
    size_t written;
    if (path == NULL || data == NULL || length < 0)
        return false;
    file = fopen(path, "wb");
    if (file == NULL)
        return false;
    written = fwrite(data, 1, (size_t)length, file);
    if (fclose(file) != 0)
        return false;
    return written == (size_t)length;
}

boolean DoomHost_NetOpen(int local_port)
{
    (void)local_port;
    return false;
}

void DoomHost_NetClose(void)
{
}

boolean DoomHost_NetResolve(const char *host, int port,
                            doom_host_net_endpoint_t *endpoint)
{
    (void)host;
    (void)port;
    (void)endpoint;
    return false;
}

boolean DoomHost_NetSend(doom_host_net_endpoint_t endpoint, const byte *data,
                         int length)
{
    (void)endpoint;
    (void)data;
    (void)length;
    return false;
}

int DoomHost_NetReceive(byte *data, int capacity,
                        doom_host_net_endpoint_t *source)
{
    (void)data;
    (void)capacity;
    (void)source;
    return 0;
}

uint64_t DoomHost_MonotonicNanoseconds(void)
{
    struct timespec value;
    if (clock_gettime(CLOCK_MONOTONIC, &value) != 0)
        return 0;
    return (uint64_t)value.tv_sec * UINT64_C(1000000000) +
           (uint64_t)value.tv_nsec;
}

void DoomHost_SleepNanoseconds(uint64_t nanoseconds)
{
    struct timespec request;
    request.tv_sec = (time_t)(nanoseconds / UINT64_C(1000000000));
    request.tv_nsec = (long)(nanoseconds % UINT64_C(1000000000));
    while (nanosleep(&request, &request) != 0 && errno == EINTR)
    {
    }
}

void DoomHost_DebugExecutionActivity(const char *language, const char *source,
                                     uint64_t location, const char *instruction)
{
    (void)language;
    (void)source;
    (void)location;
    (void)instruction;
}
