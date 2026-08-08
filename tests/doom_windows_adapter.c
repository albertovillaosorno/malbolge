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
//   - Executable boundary tests for pure DOOM Windows adapter helpers.
// - Must-Not:
//   - Launch a game window, audio device, network endpoint, or real sleep.
// - Allows:
//   - Inputs: parser, input, lifecycle, file, geometry, and timing fixtures.
//   - Outputs: zero on success or one deterministic failure code.
//   - Side effects: test-local files and transient host virtual-memory blocks.
// - Split-When:
//   - Split when a capability family needs an independent native fixture.
// - Merge-When:
//   - Merge when another harness owns these exact Windows adapter boundaries.
// - Summary:
//   - Exercises fail-closed DOOM host adapter boundary helpers.
// - Description:
//   - Includes the product adapter and hooks selected Win32 ownership/time
//     calls.
// - Usage:
//   - Compiled and executed by `test_doom_windows_adapter.py` on Windows.
// - Defaults:
//   - No GUI, audio, network, or actual waiting is performed.
//

//! Focused native regressions for DOOM Windows host adapter boundaries.

#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#define MALBOLGE_DOOM_ADAPTER_TESTING 1
#define MALBOLGE_DOOM_ADAPTER_NO_MAIN 1
// jig-ignore-next-line: indivisible reviewed identifier
#include "../src/interface/command-line/adapter-outbound/adapters/doom/windows.c"

static int frequency_calls;
static int counter_calls;
static int timing_test_mode;
static uint64_t slept_milliseconds;
static DWORD largest_sleep;
static int sleep_calls;
static byte frame_source[321U * 200U];
static boolean close_handle_succeeds = true;
static boolean close_handle_passthrough;
static boolean transient_close_succeeds = true;
static boolean destroy_window_succeeds = true;
static UINT wave_close_result = MMSYSERR_NOERROR;
static int write_mode;
static int write_calls;
static boolean virtual_free_succeeds = true;

BOOL __stdcall MalbolgeDoomTestQueryPerformanceFrequency(LARGE_INTEGER *value)
{
    ++frequency_calls;
    if (timing_test_mode == 1)
        value->QuadPart = 0;
    else if (timing_test_mode == 2)
        value->QuadPart =
            (int64_t)(UINT64_MAX / UINT64_C(1000000000) + 1U);
    else if (timing_test_mode == 5)
        value->QuadPart = 1;
    else
        value->QuadPart = 1000;
    return TRUE;
}

BOOL __stdcall MalbolgeDoomTestQueryPerformanceCounter(LARGE_INTEGER *value)
{
    ++counter_calls;
    if (timing_test_mode == 0 && counter_calls == 1)
        return FALSE;
    if (timing_test_mode == 3)
    {
        value->QuadPart = -1;
        return TRUE;
    }
    if (timing_test_mode == 4)
    {
        value->QuadPart = counter_calls == 1 ? 5000 : 4999;
        return TRUE;
    }
    if (timing_test_mode == 5)
    {
        value->QuadPart = counter_calls == 1 ? 0 : INT64_MAX;
        return TRUE;
    }
    if (timing_test_mode == 6)
    {
        if (counter_calls == 1)
            value->QuadPart = 5000;
        else if (counter_calls == 2)
            value->QuadPart = 6500;
        else if (counter_calls == 3)
            value->QuadPart = 6000;
        else
            value->QuadPart = 7000;
        return TRUE;
    }
    value->QuadPart = counter_calls == 2 ? 5000 : 6500;
    return TRUE;
}

BOOL __stdcall MalbolgeDoomTestCloseHandle(HANDLE handle)
{
    if (!close_handle_succeeds)
        return FALSE;
    if (close_handle_passthrough)
        return CloseHandle(handle);
    return TRUE;
}

BOOL __stdcall MalbolgeDoomTestCloseTransientHandle(HANDLE handle)
{
    if (!transient_close_succeeds)
        return FALSE;
    return CloseHandle(handle);
}

BOOL __stdcall MalbolgeDoomTestDestroyWindow(HWND window)
{
    (void)window;
    return destroy_window_succeeds ? TRUE : FALSE;
}

DWORD __stdcall MalbolgeDoomTestGetEnvironmentVariable(
    LPCSTR name, LPSTR buffer, DWORD size)
{
    (void)name;
    (void)buffer;
    (void)size;
    return 0;
}

BOOL __stdcall MalbolgeDoomTestWriteFile(
    HANDLE file, const void *data, DWORD length, DWORD *written,
    LPOVERLAPPED overlapped)
{
    if (write_mode == 0)
        return WriteFile(file, data, length, written, overlapped);
    ++write_calls;
    if (written == NULL)
        return FALSE;
    if (write_mode == 2)
    {
        *written = 0U;
        return TRUE;
    }
    *written = length > 3U ? 3U : length;
    return TRUE;
}

void *__stdcall MalbolgeDoomTestVirtualAlloc(
    void *address, size_t size, DWORD allocation_type, DWORD protection)
{
    return VirtualAlloc(address, size, allocation_type, protection);
}

BOOL __stdcall MalbolgeDoomTestVirtualFree(
    void *address, size_t size, DWORD free_type)
{
    if (!virtual_free_succeeds)
        return FALSE;
    return VirtualFree(address, size, free_type);
}

UINT __stdcall MalbolgeDoomTestWaveOutClose(HWAVEOUT output)
{
    (void)output;
    return wave_close_result;
}

void __stdcall MalbolgeDoomTestSleep(DWORD milliseconds)
{
    ++sleep_calls;
    slept_milliseconds += (uint64_t)milliseconds;
    if (milliseconds > largest_sleep)
        largest_sleep = milliseconds;
}

static int expect_true(boolean condition, int code)
{
    return condition ? 0 : code;
}

static int test_settings_parser(void)
{
    boolean value = true;
    char text[32] = "safe";
    const char *decoy =
        "{\"note\":\"\\\"maximized\\\": true\",\"maximized\":false}";
    int failure = expect_true(
        ParseJsonBoolean(decoy, "maximized", &value) && !value, 1);
    if (failure != 0)
        return failure;
    value = true;
    failure = expect_true(
        !ParseJsonBoolean(
            "{\"maximized\":false,\"max\u0069mized\":true}",
            "maximized", &value) && value,
        2);
    if (failure != 0)
        return failure;
    value = true;
    failure = expect_true(
        !ParseJsonBoolean(
            "{\"maximized\":false,\"maximized\":true}",
            "maximized", &value) && value,
        51);
    if (failure != 0)
        return failure;
    failure = expect_true(
        ParseJsonBoolean(
            "{\"max\u0069mized\":false}", "maximized", &value) && !value,
        52);
    if (failure != 0)
        return failure;
    failure = expect_true(
        !ParseJsonString(
            "{\"iwad\":\"evil\"oops}", "iwad", text, (int)sizeof(text)) &&
            text[0] == 's',
        3);
    if (failure != 0)
        return failure;
    failure = expect_true(
        ParseJsonStringArray(
            "{\"wads\":[\"a.wad\",]}", "wads", debug_settings.wads) == 0,
        15);
    if (failure != 0)
        return failure;
    value = true;
    failure = expect_true(
        !ParseJsonBoolean(
            "{\"maximized\":false,}", "maximized", &value) && value,
        16);
    if (failure != 0)
        return failure;
    failure = expect_true(
        !ParseJsonBoolean(
            "{\"unknown\":,\"maximized\":false}", "maximized", &value) &&
            value,
        17);
    if (failure != 0)
        return failure;
    failure = expect_true(
        !ParseJsonBoolean(
            "{\"unknown\":[,],\"maximized\":false}", "maximized", &value) &&
            value,
        18);
    if (failure != 0)
        return failure;
    failure = expect_true(
        ParseJsonBoolean(
            "{\"unknown\":{\"nested\":[1,true,null]},"
            "\"maximized\":false}",
            "maximized", &value) && !value,
        19);
    if (failure != 0)
        return failure;
    value = true;
    failure = expect_true(
        !ParseJsonBoolean(
            "{\"unknown\":\"\\u12\",\"maximized\":false}",
            "maximized", &value) && value,
        20);
    if (failure != 0)
        return failure;
    return expect_true(
        !ParseJsonBoolean(
            "{\"unknown\":01,\"maximized\":false}",
            "maximized", &value) && value,
        21);
}

static int test_settings_size(void)
{
    static const char PAYLOAD[] = "{\"maximized\":true}";
    FILE *file = NULL;
    if (fopen_s(&file, "settings.json", "wb") != 0 || file == NULL)
        return 4;
    if (fwrite(PAYLOAD, 1U, sizeof(PAYLOAD) - 1U, file) !=
        sizeof(PAYLOAD) - 1U)
        return 5;
    for (size_t index = sizeof(PAYLOAD) - 1U;
         index < sizeof(settings_json); ++index)
        if (fputc(' ', file) == EOF)
            return 6;
    if (fclose(file) != 0)
        return 7;
    debug_settings.maximized = false;
    CopyText(execution_source_override,
             (int)sizeof(execution_source_override), "stale-source");
    LoadDebugSettings();
    (void)remove("settings.json");
    return expect_true(
        !debug_settings.maximized && execution_source_override[0] == '\0', 8);
}

static int test_settings_embedded_null(void)
{
    static const char PREFIX[] = "{\"maximized\":true}";
    static const char SUFFIX[] = "trailing-invalid-json";
    FILE *file = NULL;

    if (fopen_s(&file, "settings.json", "wb") != 0 || file == NULL)
        return 95;
    if (fwrite(PREFIX, 1U, sizeof(PREFIX) - 1U, file) != sizeof(PREFIX) - 1U ||
        fputc(0, file) == EOF ||
        fwrite(SUFFIX, 1U, sizeof(SUFFIX) - 1U, file) != sizeof(SUFFIX) - 1U)
    {
        (void)fclose(file);
        (void)remove("settings.json");
        return 96;
    }
    if (fclose(file) != 0)
    {
        (void)remove("settings.json");
        return 97;
    }
    debug_settings.maximized = false;
    LoadDebugSettings();
    (void)remove("settings.json");
    return expect_true(!debug_settings.maximized, 98);
}

static int test_video_geometry(void)
{
    doom_host_video_config_t config = {
        .logical_width = 320,
        .logical_height = 200,
        .display_aspect_width = 4,
        .display_aspect_height = 3,
        .minimum_present_hz = 0,
    };
    int failure = expect_true(
        _Alignof(BITMAPINFO256) >= _Alignof(BITMAPINFO) &&
            sizeof(bitmap_info_storage.bmiColors) == 256U * sizeof(RGBQUAD) &&
            ValidVideoConfig(&config),
        9);
    if (failure != 0)
        return failure;
    config.logical_width = 2304;
    config.logical_height = 1080;
    if (!ValidVideoConfig(&config))
        return 10;
    {
        size_t scratch = 0U;
        if (AllocateFrameStorage(2304, 1080, NULL, &scratch) != NULL ||
            AllocateFrameStorage(2304, 1080, &scratch, NULL) != NULL)
            return 79;
    }
    {
        size_t stride = 0U;
        size_t capacity = 0U;
        byte *storage = AllocateFrameStorage(2304, 1080, &stride, &capacity);
        if (storage == NULL || stride != 2304U ||
            capacity != 2304U * 1080U || !ReleaseFrameStorage(storage))
            return 59;
    }
    config.logical_width = 321;
    config.logical_height = 200;
    video_config = config;
    last_frame = AllocateFrameStorage(321, 200, &last_frame_stride,
                                      &last_frame_capacity);
    if (last_frame == NULL)
        return 72;
    for (size_t index = 0U; index < sizeof(frame_source); ++index)
        frame_source[index] = (byte)(index % 251U);
    for (size_t index = 0U; index < last_frame_capacity; ++index)
        last_frame[index] = UINT8_C(0xFF);
    if (!StoreIndexedFrame(frame_source, 321, 200, 321) ||
        last_frame[0] != frame_source[0] ||
        last_frame[320] != frame_source[320] ||
        last_frame[321] != 0U || last_frame[322] != 0U ||
        last_frame[323] != 0U ||
        last_frame[324] != frame_source[321] ||
        last_frame[last_frame_capacity - 1U] != 0U ||
        !last_frame_valid || last_frame_width != 321 ||
        last_frame_height != 200 || !ReleaseFrameStorage(last_frame))
        return 73;
    last_frame = NULL;
    last_frame_capacity = 0U;
    last_frame_stride = 0U;
    last_frame_valid = false;
    config.minimum_present_hz = -1;
    if (ValidVideoConfig(&config))
        return 30;
    config.minimum_present_hz = 60;
    if (VideoWindowStyle(&config) != WS_OVERLAPPEDWINDOW ||
        ValidVideoBootstrap(NULL, (HCURSOR)(uintptr_t)1U) ||
        ValidVideoBootstrap((HINSTANCE)(uintptr_t)1U, NULL) ||
        !ValidVideoBootstrap((HINSTANCE)(uintptr_t)1U,
                             (HCURSOR)(uintptr_t)1U))
        return 31;
    config.borderless = true;
    if (VideoWindowStyle(&config) != WS_POPUP)
        return 32;
    config.borderless = false;
    video_config = config;
    debug_settings.paced_60hz = true;
    {
        int span = 0;
        if (!ShouldPaceAt60Hz())
            return 33;
        video_config.minimum_present_hz = 61;
        if (ShouldPaceAt60Hz())
            return 34;
        video_config.minimum_present_hz = 60;
        debug_settings.paced_60hz = false;
        return expect_true(
            FrameStride(321) == 324U &&
                ValidFrameGeometry(321, 200, 321) &&
                !ValidFrameGeometry(320, 200, 320) &&
                PositiveRectSpan(-8, 328, &span) && span == 336 &&
                !PositiveRectSpan(INT32_MIN, INT32_MAX, &span) &&
                !PositiveRectSpan(1, 1, &span),
            11);
    }
}

static int test_focus_loss_releases_input(void)
{
    event_read = 0U;
    event_write = 0U;
    for (int key = 0; key < HOST_KEY_STATE_CAPACITY; ++key)
    {
        key_down[key] = false;
        key_press_pending[key] = false;
        key_release_pending[key] = false;
    }
    mouse_buttons = 5;
    mouse_buttons_pending = false;
    key_down['w'] = true;
    key_down[DOOM_HOST_KEY_SHIFT] = true;

    ReleaseHeldInputEvents();
    if (key_down['w'] || key_down[DOOM_HOST_KEY_SHIFT] || mouse_buttons != 0 ||
        key_press_pending['w'] || key_press_pending[DOOM_HOST_KEY_SHIFT] ||
        key_release_pending['w'] || key_release_pending[DOOM_HOST_KEY_SHIFT] ||
        mouse_buttons_pending)
        return 35;
    if (event_write != 3U ||
        event_queue[0].type != DOOM_HOST_EVENT_MOUSE ||
        event_queue[0].mouse_buttons != 0 ||
        event_queue[1].type != DOOM_HOST_EVENT_KEY_UP ||
        event_queue[1].key != 'w' ||
        event_queue[2].type != DOOM_HOST_EVENT_KEY_UP ||
        event_queue[2].key != DOOM_HOST_KEY_SHIFT)
        return 36;

    event_read = 0U;
    event_write = EVENT_QUEUE_CAPACITY - 1U;
    key_down['w'] = true;
    key_release_pending['w'] = false;
    window_has_focus = true;
    (void)DoomWindowProc(NULL, WM_KEYUP, (WPARAM)'W', 0);
    if (!key_down['w'] || !key_release_pending['w'])
        return 37;
    event_read = 1U;
    RetryPendingInputEvents();
    if (key_down['w'] || key_release_pending['w'] ||
        event_queue[EVENT_QUEUE_CAPACITY - 1U].type != DOOM_HOST_EVENT_KEY_UP ||
        event_queue[EVENT_QUEUE_CAPACITY - 1U].key != 'w')
        return 38;

    event_read = 0U;
    event_write = EVENT_QUEUE_CAPACITY - 1U;
    key_down['w'] = false;
    key_press_pending['w'] = false;
    key_release_pending['w'] = false;
    (void)DoomWindowProc(NULL, WM_KEYDOWN, (WPARAM)'W', 0);
    if (!key_press_pending['w'] || key_down['w'])
        return 67;
    event_read = 1U;
    RetryPendingInputEvents();
    if (key_press_pending['w'] || !key_down['w'] ||
        event_queue[EVENT_QUEUE_CAPACITY - 1U].type !=
            DOOM_HOST_EVENT_KEY_DOWN ||
        event_queue[EVENT_QUEUE_CAPACITY - 1U].key != 'w')
        return 68;

    event_read = 0U;
    event_write = EVENT_QUEUE_CAPACITY - 1U;
    key_down['w'] = true;
    key_press_pending['w'] = false;
    key_release_pending['w'] = false;
    (void)DoomWindowProc(NULL, WM_KEYUP, (WPARAM)'W', 0);
    if (!key_release_pending['w'] || !key_down['w'])
        return 74;
    (void)DoomWindowProc(NULL, WM_KEYDOWN, (WPARAM)'W', 0);
    if (!key_release_pending['w'] || !key_press_pending['w'])
        return 75;
    event_read = 2U;
    RetryPendingInputEvents();
    if (key_release_pending['w'] || key_press_pending['w'] || !key_down['w'] ||
        event_queue[EVENT_QUEUE_CAPACITY - 1U].type != DOOM_HOST_EVENT_KEY_UP ||
        event_queue[0].type != DOOM_HOST_EVENT_KEY_DOWN ||
        event_queue[0].key != 'w')
        return 76;

    event_read = 0U;
    event_write = EVENT_QUEUE_CAPACITY - 1U;
    mouse_buttons = 1;
    mouse_buttons_pending = false;
    (void)DoomWindowProc(NULL, WM_LBUTTONUP, 0, 0);
    if (mouse_buttons != 0 || !mouse_buttons_pending)
        return 39;
    event_read = 1U;
    RetryPendingInputEvents();
    if (mouse_buttons_pending ||
        event_queue[EVENT_QUEUE_CAPACITY - 1U].type != DOOM_HOST_EVENT_MOUSE ||
        event_queue[EVENT_QUEUE_CAPACITY - 1U].mouse_buttons != 0)
        return 50;

    event_read = 0U;
    event_write = 0U;
    window_has_focus = false;
    return 0;
}

static int test_quit_and_shutdown_input_boundaries(void)
{
    doom_host_event_t event = {0};

    event_read = 0U;
    event_write = EVENT_QUEUE_CAPACITY - 1U;
    quit_pending = false;
    (void)DoomWindowProc(NULL, WM_CLOSE, 0, 0);
    if (!quit_pending)
        return 53;
    event_read = 1U;
    RetryPendingQuitEvent();
    if (quit_pending ||
        event_queue[EVENT_QUEUE_CAPACITY - 1U].type != DOOM_HOST_EVENT_QUIT)
        return 54;

    event_read = 0U;
    event_write = EVENT_QUEUE_CAPACITY - 1U;
    quit_pending = false;
    (void)DoomWindowProc(
        NULL, WM_SYSKEYDOWN, (WPARAM)VK_F4, (LPARAM)(1UL << 29U));
    if (!quit_pending)
        return 78;
    event_read = 1U;
    RetryPendingQuitEvent();
    if (quit_pending ||
        event_queue[EVENT_QUEUE_CAPACITY - 1U].type != DOOM_HOST_EVENT_QUIT)
        return 79;

    window_handle = NULL;
    mouse_capture_requested = false;
    relative_mouse = true;
    DoomHost_SetRelativeMouseCapture(true);
    if (mouse_capture_requested || DoomHost_PollEvent(&event))
        return 55;
    relative_mouse = false;
    event_read = 0U;
    event_write = 0U;
    quit_pending = false;
    return 0;
}

static int test_debug_argument_boundaries(void)
{
    char program[] = "doom";
    char value[] = "value";
    char *small_argv[] = {program, value};
    char *full_argv[MAX_DEBUG_ARGUMENTS];
    int count;

    debug_settings.iwad[0] = 0;
    debug_settings.language[0] = 0;
    debug_settings.wad_count = 0;
    count = BuildDebugArguments(2, small_argv);
    if (count != 2 || debug_arguments[count] != NULL)
        return 26;
    if (BuildDebugArguments(-1, small_argv) != -1 ||
        BuildDebugArguments(1, NULL) != -1)
        return 27;
    small_argv[1] = NULL;
    if (BuildDebugArguments(2, small_argv) != -1)
        return 28;
    small_argv[1] = value;

    for (int index = 0; index < MAX_DEBUG_ARGUMENTS; ++index)
        full_argv[index] = value;
    if (BuildDebugArguments(MAX_DEBUG_ARGUMENTS, full_argv) != -1)
        return 29;
    return 0;
}

static int test_text_and_lifecycle_boundaries(void)
{
    char text[32] = {0};
    int length = 0;
    doom_host_video_config_t video = {
        .logical_width = 320,
        .logical_height = 200,
        .display_aspect_width = 4,
        .display_aspect_height = 3,
    };
    doom_host_audio_config_t audio = {
        .sample_rate = 44100,
        .channel_count = 2,
        .frames_per_buffer = AUDIO_FRAMES_PER_BLOCK,
    };

    AppendDecimal(text, &length, (int)sizeof(text), INT32_MIN);
    text[length] = 0;
    if (strcmp(text, "-2147483648") != 0)
        return 22;

    {
        WNDCLASSEXA expected = {0};
        WNDCLASSEXA actual = {0};
        expected.style = CS_OWNDC;
        expected.lpfnWndProc = DoomWindowProc;
        expected.hInstance = (HINSTANCE)(uintptr_t)1U;
        actual = expected;
        if (!MatchingWindowClass(&expected, &actual) ||
            MatchingWindowClass(NULL, &actual) ||
            MatchingWindowClass(&expected, NULL))
            return 99;
        actual.lpfnWndProc = DefWindowProcA;
        if (MatchingWindowClass(&expected, &actual))
            return 100;
        actual = expected;
        actual.style = 0U;
        if (MatchingWindowClass(&expected, &actual))
            return 101;
        actual = expected;
        actual.hInstance = (HINSTANCE)(uintptr_t)2U;
        if (MatchingWindowClass(&expected, &actual))
            return 102;

        expected = (WNDCLASSEXA){0};
        actual = (WNDCLASSEXA){0};
        expected.cbSize = sizeof(expected);
        expected.style = CS_OWNDC;
        expected.lpfnWndProc = DoomWindowProc;
        expected.hInstance = GetModuleHandleA(NULL);
        expected.lpszClassName = "MalbolgeDoomAdapterBoundaryClass";
        actual.cbSize = sizeof(actual);
        if (expected.hInstance == NULL || !RegisterClassExA(&expected) ||
            !GetClassInfoExA(expected.hInstance, expected.lpszClassName,
                             &actual) ||
            !MatchingWindowClass(&expected, &actual))
            return 103;
    }

    window_handle = (HWND)(uintptr_t)1U;
    if (DoomHost_VideoInitialize(&video))
        return 23;
    bitmap_info = &bitmap_info_storage;
    destroy_window_succeeds = false;
    if (DestroyVideoWindow() || window_handle == NULL || bitmap_info == NULL)
        return 40;
    destroy_window_succeeds = true;
    if (!DestroyVideoWindow() || window_handle != NULL || bitmap_info != NULL)
        return 41;

    last_frame = AllocateFrameStorage(320, 200, &last_frame_stride,
                                      &last_frame_capacity);
    if (last_frame == NULL)
        return 61;
    virtual_free_succeeds = false;
    if (DestroyVideoWindow() || last_frame == NULL ||
        last_frame_capacity == 0U || last_frame_stride == 0U)
        return 62;
    virtual_free_succeeds = true;
    if (!DestroyVideoWindow() || last_frame != NULL ||
        last_frame_capacity != 0U || last_frame_stride != 0U)
        return 63;

    audio_output = (HWAVEOUT)(uintptr_t)1U;
    audio_initialized = true;
    if (DoomHost_AudioInitialize(&audio))
        return 24;
    wave_close_result = 1U;
    if (CloseAudioOutput() || audio_output == NULL || audio_initialized)
        return 42;
    wave_close_result = MMSYSERR_NOERROR;
    if (!CloseAudioOutput() || audio_output != NULL || audio_initialized)
        return 43;

    bitmap_info = &bitmap_info_storage;
    video_config = video;
    last_frame = AllocateFrameStorage(320, 200, &last_frame_stride,
                                      &last_frame_capacity);
    if (last_frame == NULL)
        return 60;
    last_frame_valid = true;
    last_frame_width = 320;
    last_frame_height = 200;
    event_read = 1U;
    event_write = 2U;
    mouse_buttons = 7;
    relative_mouse = true;
    mouse_capture_requested = true;
    window_has_focus = true;
    last_present_ns = UINT64_C(17);
    fps_window_start_ns = UINT64_C(19);
    fps_window_frames = 3;
    displayed_fps = 60;
    trace_title_update_ns = UINT64_C(23);
    CopyText(trace_language, (int)sizeof(trace_language), "C");
    CopyText(trace_source, (int)sizeof(trace_source), "old.c");
    CopyText(trace_instruction, (int)sizeof(trace_instruction), "old");
    trace_location = UINT64_C(29);
    DoomHost_VideoShutdown();
    if (bitmap_info != NULL || last_frame != NULL ||
        last_frame_capacity != 0U ||
        last_frame_stride != 0U || last_frame_valid || last_frame_width != 0 ||
        last_frame_height != 0 || event_read != 0U || event_write != 0U ||
        mouse_buttons != 0 || relative_mouse || mouse_capture_requested ||
        window_has_focus || last_present_ns != 0U ||
        fps_window_start_ns != 0U || fps_window_frames != 0 ||
        displayed_fps != 0 || trace_title_update_ns != 0U ||
        strcmp(trace_language, "C") != 0 ||
        strcmp(trace_source, "old.c") != 0 ||
        strcmp(trace_instruction, "old") != 0 ||
        trace_location != UINT64_C(29))
        return 25;
    return 0;
}

static int test_fps_counter_boundaries(void)
{
    fps_window_start_ns = UINT64_C(100);
    fps_window_frames = (uint32_t)INT32_MAX;
    displayed_fps = 0;
    UpdateFpsWindow(UINT64_C(100));
    if (fps_window_frames != (uint32_t)INT32_MAX || displayed_fps != 0)
        return 46;
    UpdateFpsWindow(UINT64_C(500000100));
    if (fps_window_frames != 0U || displayed_fps != INT32_MAX)
        return 47;
    fps_window_start_ns = 0U;
    displayed_fps = 0;
    return 0;
}

static int test_file_close_ownership(void)
{
    doom_host_file_t file = 99U;
    doom_host_net_endpoint_t endpoint = 99U;

    if (DoomHost_FileOpenRead(NULL, &file) || file != 0U)
        return 69;
    file = 99U;
    if (DoomHost_FileOpenRead("missing-doom-adapter-file.tmp", &file) ||
        file != 0U)
        return 70;
    if (DoomHost_NetResolve("localhost", 1, &endpoint) || endpoint != 0U)
        return 71;
    endpoint = 99U;
    if (DoomHost_NetReceive(NULL, 0, &endpoint) != -1 || endpoint != 0U)
        return 80;

    file_handles[1] = (void *)(uintptr_t)1U;
    close_handle_succeeds = false;
    DoomHost_FileClose(1U);
    if (file_handles[1] == NULL)
        return 44;
    close_handle_succeeds = true;
    DoomHost_FileClose(1U);
    if (file_handles[1] != NULL)
        return 45;
    return 0;
}

static int test_file_write_all_progress(void)
{
    static const byte DATA[] = {1U, 2U, 3U, 4U, 5U, 6U, 7U};
    doom_host_file_t file = 0U;

    if (!DoomHost_FileWriteAll("write-all-empty.tmp", NULL, 0) ||
        !DoomHost_FileOpenRead("write-all-empty.tmp", &file) ||
        DoomHost_FileSize(file) != 0 ||
        DoomHost_FileReadAt(file, 99, NULL, 0) != 0)
    {
        if (ValidFile(file))
            DoomHost_FileClose(file);
        (void)remove("write-all-empty.tmp");
        return 58;
    }
    close_handle_passthrough = true;
    DoomHost_FileClose(file);
    close_handle_passthrough = false;
    (void)remove("write-all-empty.tmp");

    write_mode = 0;
    if (!DoomHost_FileWriteAll("write-all-real.tmp", DATA,
                               (int)sizeof(DATA)))
        return 77;
    {
        byte observed[sizeof(DATA)] = {0};
        file = 0U;
        if (!DoomHost_FileOpenRead("write-all-real.tmp", &file) ||
            DoomHost_FileSize(file) != (int)sizeof(DATA) ||
            DoomHost_FileReadAt(file, 0, observed, (int)sizeof(observed)) !=
                (int)sizeof(observed) ||
            memcmp(observed, DATA, sizeof(DATA)) != 0)
        {
            if (ValidFile(file))
            {
                close_handle_passthrough = true;
                DoomHost_FileClose(file);
                close_handle_passthrough = false;
            }
            (void)remove("write-all-real.tmp");
            return 78;
        }
        close_handle_passthrough = true;
        DoomHost_FileClose(file);
        close_handle_passthrough = false;
    }
    (void)remove("write-all-real.tmp");

    transient_close_succeeds = false;
    if (DoomHost_FileWriteAll("write-all-close.tmp", DATA,
                              (int)sizeof(DATA)) ||
        pending_write_handle == NULL)
        return 64;
    if (DoomHost_FileWriteAll("write-all-blocked.tmp", DATA,
                              (int)sizeof(DATA)))
        return 65;
    transient_close_succeeds = true;
    if (!RetryPendingWriteHandle() || pending_write_handle != NULL)
        return 66;
    (void)remove("write-all-close.tmp");
    (void)remove("write-all-blocked.tmp");

    write_mode = 1;
    write_calls = 0;
    if (!DoomHost_FileWriteAll("write-all-test.tmp", DATA, (int)sizeof(DATA)) ||
        write_calls != 3)
    {
        (void)remove("write-all-test.tmp");
        write_mode = 0;
        return 56;
    }
    write_mode = 2;
    write_calls = 0;
    if (DoomHost_FileWriteAll("write-all-test.tmp", DATA, (int)sizeof(DATA)) ||
        write_calls != 1)
    {
        (void)remove("write-all-test.tmp");
        write_mode = 0;
        return 57;
    }
    write_mode = 0;
    (void)remove("write-all-test.tmp");
    return 0;
}

static void ResetTimingTest(int mode)
{
    performance_frequency.QuadPart = 0;
    performance_origin.QuadPart = 0;
    performance_last_counter.QuadPart = 0;
    frequency_calls = 0;
    counter_calls = 0;
    timing_test_mode = mode;
}

static int test_timing(void)
{
    ResetTimingTest(0);
    if (DoomHost_MonotonicNanoseconds() != 0 ||
        performance_frequency.QuadPart != 0)
        return 12;
    if (DoomHost_MonotonicNanoseconds() != UINT64_C(1500000000) ||
        frequency_calls != 2 || counter_calls != 3)
        return 13;

    for (int mode = 1; mode <= 5; ++mode)
    {
        ResetTimingTest(mode);
        if (DoomHost_MonotonicNanoseconds() != 0)
            return 81 + mode;
        if (mode <= 3 && performance_frequency.QuadPart != 0)
            return 87 + mode;
    }
    ResetTimingTest(6);
    if (DoomHost_MonotonicNanoseconds() != UINT64_C(1500000000) ||
        DoomHost_MonotonicNanoseconds() != 0 ||
        performance_last_counter.QuadPart != 6500 ||
        DoomHost_MonotonicNanoseconds() != UINT64_C(2000000000) ||
        performance_last_counter.QuadPart != 7000)
        return 94;
    ResetTimingTest(0);

    slept_milliseconds = 0;
    largest_sleep = 0;
    sleep_calls = 0;
    DoomHost_SleepNanoseconds(UINT64_MAX);
    return expect_true(
        slept_milliseconds == UINT64_MAX / UINT64_C(1000000) + 1U &&
            largest_sleep == (DWORD)0xFFFFFFFEU && sleep_calls > 1,
        14);
}

int main(void)
{
    int failure = test_settings_parser();
    if (failure == 0)
        failure = test_settings_size();
    if (failure == 0)
        failure = test_settings_embedded_null();
    if (failure == 0)
        failure = test_video_geometry();
    if (failure == 0)
        failure = test_focus_loss_releases_input();
    if (failure == 0)
        failure = test_quit_and_shutdown_input_boundaries();
    if (failure == 0)
        failure = test_debug_argument_boundaries();
    if (failure == 0)
        failure = test_text_and_lifecycle_boundaries();
    if (failure == 0)
        failure = test_fps_counter_boundaries();
    if (failure == 0)
        failure = test_file_close_ownership();
    if (failure == 0)
        failure = test_file_write_all_progress();
    if (failure == 0)
        failure = test_timing();
    return failure;
}
