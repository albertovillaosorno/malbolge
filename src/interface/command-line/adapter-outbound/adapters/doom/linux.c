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
//   - Linux adapter for canonical `malbolge doom.c` debug execution.
// - Description:
//   - Binds the portable DOOM guest ABI to SDL2 on Linux.
// - Usage:
//   - Selected by the command-line C debug path; never part of guest C.
// - Defaults:
//   - settings.json controls presentation; otherwise use a maximized 1080p
//     window with a 640x360 corrected widescreen render target.
//

//! Linux host adapter for canonical `malbolge doom.c` debugging.

#define SDL_MAIN_HANDLED
#include <SDL2/SDL.h>

#include <errno.h>
#include <limits.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#include "abi.h"

#ifdef main
#undef main
#endif

int DoomGuestMain(int argc, char **argv);

#define GUEST_MEMORY_BYTES (64 * 1024 * 1024)
#define HOST_FILE_CAPACITY 64
#define AUDIO_BLOCK_COUNT 8
#define LINUX_MOUSE_DELTA_SCALE 4
#define SETTINGS_BUFFER_BYTES 65536
#define MAX_DEBUG_ARGUMENTS 1024
#define DEFAULT_WINDOW_WIDTH 1920
#define DEFAULT_WINDOW_HEIGHT 1080
#define DEFAULT_RENDER_WIDTH 640
#define DEFAULT_RENDER_HEIGHT 360

typedef struct
{
        boolean maximized;
        int window_width;
        int window_height;
        int render_width;
        int render_height;
} debug_settings_t;

static debug_settings_t debug_settings = {
    .maximized = true,
    .window_width = DEFAULT_WINDOW_WIDTH,
    .window_height = DEFAULT_WINDOW_HEIGHT,
    .render_width = DEFAULT_RENDER_WIDTH,
    .render_height = DEFAULT_RENDER_HEIGHT,
};
static char settings_json[SETTINGS_BUFFER_BYTES];
static char *debug_arguments[MAX_DEBUG_ARGUMENTS];
static char render_height_text[16];
static char render_width_text[16];

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

static const char *SkipJsonSpace(const char *cursor)
{
    while (*cursor == ' ' || *cursor == '\t' || *cursor == '\r' ||
           *cursor == '\n')
        ++cursor;
    return cursor;
}

static boolean IsJsonHexDigit(char value)
{
    return (value >= '0' && value <= '9') || (value >= 'a' && value <= 'f') ||
           (value >= 'A' && value <= 'F');
}

static const char *SkipJsonQuoted(const char *cursor)
{
    if (cursor == NULL || *cursor != (char)0x22)
        return NULL;
    ++cursor;
    while (*cursor != 0)
    {
        if ((unsigned char)*cursor < 0x20U)
            return NULL;
        if (*cursor == (char)0x5C)
        {
            ++cursor;
            if (*cursor == 'u')
            {
                ++cursor;
                for (int index = 0; index < 4; ++index)
                {
                    if (*cursor == 0 || !IsJsonHexDigit(*cursor))
                        return NULL;
                    ++cursor;
                }
                continue;
            }
            if (*cursor != (char)0x22 && *cursor != (char)0x5C &&
                *cursor != '/' && *cursor != 'b' && *cursor != 'f' &&
                *cursor != 'n' && *cursor != 'r' && *cursor != 't')
                return NULL;
            ++cursor;
            continue;
        }
        if (*cursor == (char)0x22)
            return cursor + 1;
        ++cursor;
    }
    return NULL;
}

static int JsonHexValue(char value)
{
    if (value >= '0' && value <= '9')
        return value - '0';
    if (value >= 'a' && value <= 'f')
        return value - 'a' + 10;
    if (value >= 'A' && value <= 'F')
        return value - 'A' + 10;
    return -1;
}

static boolean JsonKeyEquals(const char *start, const char *end,
                             const char *key)
{
    if (start == NULL || end == NULL || key == NULL || start > end)
        return false;
    while (start < end && *key != 0)
    {
        unsigned int decoded = (unsigned char)*start++;
        if (decoded == 0x5CU)
        {
            if (start >= end)
                return false;
            switch (*start++)
            {
                case (char)0x22:
                    decoded = 0x22U;
                    break;
                case (char)0x5C:
                    decoded = 0x5CU;
                    break;
                case '/':
                    decoded = (unsigned int)'/';
                    break;
                case 'b':
                    decoded = 0x08U;
                    break;
                case 'f':
                    decoded = 0x0CU;
                    break;
                case 'n':
                    decoded = 0x0AU;
                    break;
                case 'r':
                    decoded = 0x0DU;
                    break;
                case 't':
                    decoded = 0x09U;
                    break;
                case 'u':
                    {
                        unsigned int codepoint = 0U;
                        for (int index = 0; index < 4; ++index)
                        {
                            const int digit =
                                start < end ? JsonHexValue(*start++) : -1;
                            if (digit < 0)
                                return false;
                            codepoint = codepoint * 16U + (unsigned int)digit;
                        }
                        if (codepoint > 0x7FU)
                            return false;
                        decoded = codepoint;
                        break;
                    }
                default:
                    return false;
            }
        }
        if (decoded != (unsigned int)(unsigned char)*key)
            return false;
        ++key;
    }
    return start == end && *key == 0;
}

static const char *SkipJsonValueDepth(const char *cursor, int depth);

static const char *SkipJsonArray(const char *cursor, int depth)
{
    ++cursor;
    cursor = SkipJsonSpace(cursor);
    if (*cursor == ']')
        return cursor + 1;
    for (;;)
    {
        cursor = SkipJsonValueDepth(cursor, depth + 1);
        if (cursor == NULL)
            return NULL;
        cursor = SkipJsonSpace(cursor);
        if (*cursor == ']')
            return cursor + 1;
        if (*cursor != ',')
            return NULL;
        cursor = SkipJsonSpace(cursor + 1);
        if (*cursor == ']')
            return NULL;
    }
}

static const char *SkipJsonObject(const char *cursor, int depth)
{
    ++cursor;
    cursor = SkipJsonSpace(cursor);
    if (*cursor == '}')
        return cursor + 1;
    for (;;)
    {
        if (*cursor != (char)0x22)
            return NULL;
        cursor = SkipJsonQuoted(cursor);
        if (cursor == NULL)
            return NULL;
        cursor = SkipJsonSpace(cursor);
        if (*cursor != ':')
            return NULL;
        cursor = SkipJsonValueDepth(cursor + 1, depth + 1);
        if (cursor == NULL)
            return NULL;
        cursor = SkipJsonSpace(cursor);
        if (*cursor == '}')
            return cursor + 1;
        if (*cursor != ',')
            return NULL;
        cursor = SkipJsonSpace(cursor + 1);
        if (*cursor == '}')
            return NULL;
    }
}

static boolean IsJsonNumberDelimiter(char value)
{
    return value == 0 || value == ' ' || value == '\t' || value == '\r' ||
           value == '\n' || value == ',' || value == ']' || value == '}';
}

static const char *SkipJsonNumber(const char *cursor)
{
    if (*cursor == '-')
        ++cursor;
    if (*cursor == '0')
        ++cursor;
    else
    {
        if (*cursor < '1' || *cursor > '9')
            return NULL;
        do
        {
            ++cursor;
        }
        while (*cursor >= '0' && *cursor <= '9');
    }
    if (*cursor == '.')
    {
        ++cursor;
        if (*cursor < '0' || *cursor > '9')
            return NULL;
        do
        {
            ++cursor;
        }
        while (*cursor >= '0' && *cursor <= '9');
    }
    if (*cursor == 'e' || *cursor == 'E')
    {
        ++cursor;
        if (*cursor == '+' || *cursor == '-')
            ++cursor;
        if (*cursor < '0' || *cursor > '9')
            return NULL;
        do
        {
            ++cursor;
        }
        while (*cursor >= '0' && *cursor <= '9');
    }
    return IsJsonNumberDelimiter(*cursor) ? cursor : NULL;
}

static const char *SkipJsonLiteralValue(const char *cursor, const char *literal)
{
    while (*literal != 0)
    {
        if (*cursor != *literal)
            return NULL;
        ++cursor;
        ++literal;
    }
    return IsJsonNumberDelimiter(*cursor) ? cursor : NULL;
}

static const char *SkipJsonValueDepth(const char *cursor, int depth)
{
    if (cursor == NULL || depth > 64)
        return NULL;
    cursor = SkipJsonSpace(cursor);
    if (*cursor == (char)0x22)
        return SkipJsonQuoted(cursor);
    if (*cursor == '{')
        return SkipJsonObject(cursor, depth);
    if (*cursor == '[')
        return SkipJsonArray(cursor, depth);
    if (*cursor == 't')
        return SkipJsonLiteralValue(cursor, "true");
    if (*cursor == 'f')
        return SkipJsonLiteralValue(cursor, "false");
    if (*cursor == 'n')
        return SkipJsonLiteralValue(cursor, "null");
    return SkipJsonNumber(cursor);
}

static const char *SkipJsonValue(const char *cursor)
{
    return SkipJsonValueDepth(cursor, 0);
}

static const char *FindJsonValue(const char *json, const char *key)
{
    const char *cursor;
    const char *found = NULL;

    if (json == NULL || key == NULL || *key == 0)
        return NULL;
    cursor = SkipJsonSpace(json);
    if (*cursor != '{')
        return NULL;
    ++cursor;

    for (;;)
    {
        const char *name_start;
        const char *name_end;
        const char *value;
        const char *after_value;
        boolean matches;

        cursor = SkipJsonSpace(cursor);
        if (*cursor == '}')
        {
            cursor = SkipJsonSpace(cursor + 1);
            return *cursor == 0 ? found : NULL;
        }
        if (*cursor != (char)0x22)
            return NULL;
        name_start = cursor + 1;
        name_end = SkipJsonQuoted(cursor);
        if (name_end == NULL)
            return NULL;
        matches = JsonKeyEquals(name_start, name_end - 1, key);
        cursor = SkipJsonSpace(name_end);
        if (*cursor != ':')
            return NULL;
        value = SkipJsonSpace(cursor + 1);
        if (matches)
        {
            if (found != NULL)
                return NULL;
            found = value;
        }
        after_value = SkipJsonValue(value);
        if (after_value == NULL)
            return NULL;
        cursor = SkipJsonSpace(after_value);
        if (*cursor == ',')
        {
            cursor = SkipJsonSpace(cursor + 1);
            if (*cursor == '}')
                return NULL;
            continue;
        }
        if (*cursor != '}')
            return NULL;
    }
}

static boolean IsJsonTokenTerminator(char value)
{
    return value == '\0' || value == ' ' || value == '\t' || value == '\r' ||
           value == '\n' || value == ',' || value == '}' || value == ']';
}

static boolean MatchJsonLiteral(const char *cursor, const char *literal,
                                const char **end)
{
    if (cursor == NULL || literal == NULL || end == NULL)
        return false;
    while (*literal != '\0')
    {
        if (*cursor == '\0' || *cursor != *literal)
            return false;
        ++cursor;
        ++literal;
    }
    if (!IsJsonTokenTerminator(*cursor))
        return false;
    *end = cursor;
    return true;
}

static boolean ParseJsonBoolean(const char *json, const char *key,
                                boolean *value)
{
    const char *cursor = FindJsonValue(json, key);
    const char *end = NULL;

    if (cursor == NULL || value == NULL)
        return false;
    if (MatchJsonLiteral(cursor, "true", &end))
    {
        *value = true;
        return true;
    }
    if (MatchJsonLiteral(cursor, "false", &end))
    {
        *value = false;
        return true;
    }
    return false;
}

static boolean ParsePositiveInt(const char **cursor_ptr, int *value)
{
    const char *cursor = SkipJsonSpace(*cursor_ptr);
    int result = 0;
    int digits = 0;

    while (*cursor >= '0' && *cursor <= '9')
    {
        const int digit = *cursor - '0';
        if (result > (INT32_MAX - digit) / 10)
            return false;
        result = result * 10 + digit;
        ++cursor;
        ++digits;
    }
    if (digits == 0 || result <= 0)
        return false;
    *cursor_ptr = cursor;
    *value = result;
    return true;
}

static boolean ParseJsonResolution(const char *json, const char *key,
                                   int *width, int *height)
{
    const char *cursor = FindJsonValue(json, key);

    if (cursor == NULL || *cursor != '[')
        return false;
    ++cursor;
    if (!ParsePositiveInt(&cursor, width))
        return false;
    cursor = SkipJsonSpace(cursor);
    if (*cursor != ',')
        return false;
    ++cursor;
    if (!ParsePositiveInt(&cursor, height))
        return false;
    cursor = SkipJsonSpace(cursor);
    if (*cursor != ']')
        return false;
    ++cursor;
    cursor = SkipJsonSpace(cursor);
    return IsJsonTokenTerminator(*cursor);
}

static boolean HasArgument(int argc, char **argv, const char *name)
{
    for (int index = 1; index < argc; ++index)
        if (strcmp(argv[index], name) == 0)
            return true;
    return false;
}

static boolean HasRenderArgument(int argc, char **argv)
{
    return HasArgument(argc, argv, "-render-scale") ||
           HasArgument(argc, argv, "-render-height") ||
           HasArgument(argc, argv, "-render-width");
}

static boolean AppendDebugArgument(int *count, char *value)
{
    if (count == NULL || value == NULL || *count < 0 ||
        *count >= MAX_DEBUG_ARGUMENTS - 1)
        return false;
    debug_arguments[*count] = value;
    ++*count;
    return true;
}

static boolean CorrectedRenderWidth(int display_width, int height,
                                    int *guest_width)
{
    int64_t scaled_width;
    int64_t minimum_width;

    if (guest_width == NULL || display_width <= 0 || height < 200 ||
        height % 5 != 0)
        return false;
    scaled_width = (int64_t)display_width * 6;
    if (scaled_width % 5 != 0 || scaled_width / 5 > INT_MAX)
        return false;
    *guest_width = (int)(scaled_width / 5);
    minimum_width = (int64_t)8 * height / 5;
    return (int64_t)*guest_width >= minimum_width && (*guest_width & 1) == 0;
}

static void LoadDebugSettings(void)
{
    FILE *file;
    long size;
    size_t bytes_read;
    int width;
    int height;

    file = fopen("settings.json", "rb");
    if (file == NULL)
        return;
    if (fseek(file, 0, SEEK_END) != 0)
    {
        (void)fclose(file);
        return;
    }
    size = ftell(file);
    if (size < 0 || size >= (long)sizeof(settings_json) ||
        fseek(file, 0, SEEK_SET) != 0)
    {
        (void)fclose(file);
        return;
    }
    bytes_read = fread(settings_json, 1, (size_t)size, file);
    if (fclose(file) != 0 || bytes_read != (size_t)size)
        return;
    for (size_t index = 0; index < bytes_read; ++index)
        if (settings_json[index] == '\0')
            return;
    settings_json[bytes_read] = '\0';

    (void)ParseJsonBoolean(settings_json, "maximized",
                           &debug_settings.maximized);
    if (ParseJsonResolution(settings_json, "resolution", &width, &height) &&
        width >= 320 && height >= 200)
    {
        debug_settings.window_width = width;
        debug_settings.window_height = height;
    }
    if (ParseJsonResolution(settings_json, "render_resolution", &width,
                            &height) &&
        width >= 320 && height >= 200)
    {
        debug_settings.render_width = width;
        debug_settings.render_height = height;
    }
}

static int BuildDebugArguments(int argc, char **argv)
{
    static char arg_render_height[] = "-render-height";
    static char arg_render_width[] = "-render-width";
    int count = 0;
    int guest_width;

    for (int index = 0; index < argc; ++index)
        if (!AppendDebugArgument(&count, argv[index]))
            return -1;
    if (!HasRenderArgument(argc, argv))
    {
        if (!CorrectedRenderWidth(debug_settings.render_width,
                                  debug_settings.render_height, &guest_width))
        {
            (void)fprintf(stderr,
                          "Invalid render_resolution in settings.json\n");
            return -1;
        }
        if (snprintf(render_height_text, sizeof(render_height_text), "%d",
                     debug_settings.render_height) <= 0 ||
            snprintf(render_width_text, sizeof(render_width_text), "%d",
                     guest_width) <= 0)
            return -1;
        if (!AppendDebugArgument(&count, arg_render_height) ||
            !AppendDebugArgument(&count, render_height_text) ||
            !AppendDebugArgument(&count, arg_render_width) ||
            !AppendDebugArgument(&count, render_width_text))
            return -1;
    }
    debug_arguments[count] = NULL;
    return count;
}

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
    if (debug_settings.maximized)
        flags |= SDL_WINDOW_MAXIMIZED;
    window_handle = SDL_CreateWindow(
        config->title != NULL ? config->title : "DOOM", SDL_WINDOWPOS_CENTERED,
        SDL_WINDOWPOS_CENTERED, debug_settings.window_width,
        debug_settings.window_height, flags);
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
#ifndef MALBOLGE_DOOM_ADAPTER_NO_MAIN
int main(int argc, char **argv)
{
    int debug_argc;

    LoadDebugSettings();
    debug_argc = BuildDebugArguments(argc, argv);
    if (debug_argc < 0)
        return 2;
    return DoomGuestMain(debug_argc, debug_arguments);
}
#endif
