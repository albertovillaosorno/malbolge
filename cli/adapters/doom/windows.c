// File:
//   - windows.c
// Path:
//   - cli/adapters/doom/windows.c
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
//   - Win32 implementations of the version-one DOOM host-service ABI.
// - Must-Not:
//   - Embed IWAD bytes, define the game entrypoint, or alter guest semantics.
// - Allows:
//   - Inputs: portable DOOM capability calls and host window/input/audio state.
//   - Outputs: Win32 presentation, input, files, timing, and process services.
//   - Side effects: one debug window, audio device I/O, and caller-requested files.
// - Split-When:
//   - Split when networking or another capability requires an independent owner.
// - Merge-When:
//   - Merge when a shared cross-platform adapter owns identical Win32 behavior.
// - Summary:
//   - Native Windows debug adapter used by `malbolge doom.c`.
// - Description:
//   - Makes the generated portable C artifact quickly runnable during debugging.
// - Usage:
//   - Linked transiently by the CLI; never distributed as part of `doom.c`.
// - Defaults:
//   - Windowed 1280x720 presentation, native files, no networking.
//
// Related documents:
// - cli/README.md
// - docs/technical/runtime/execution/cross-platform-native-capability-runners.md
//
// Large file:
//   - false

#include <stddef.h>
#include <stdint.h>

typedef int BOOL;
typedef int32_t LONG;
typedef uint8_t BYTE;
typedef uint16_t WORD;
typedef uint16_t ATOM;
typedef uint32_t DWORD;
typedef uint32_t UINT;
typedef uintptr_t DWORD_PTR;
typedef uintptr_t WPARAM;
typedef intptr_t LPARAM;
typedef intptr_t LRESULT;
typedef void *HANDLE;
typedef HANDLE HWND;
typedef HANDLE HINSTANCE;
typedef HANDLE HICON;
typedef HANDLE HCURSOR;
typedef HANDLE HBRUSH;
typedef HANDLE HDC;
typedef HANDLE HWAVEOUT;
typedef char *LPSTR;
typedef const char *LPCSTR;
typedef LRESULT (*WNDPROC)(HWND, UINT, WPARAM, LPARAM);

typedef struct { LONG x; LONG y; } POINT;
typedef struct { LONG left; LONG top; LONG right; LONG bottom; } RECT;
typedef struct {
    HWND hwnd;
    UINT message;
    WPARAM wParam;
    LPARAM lParam;
    DWORD time;
    POINT pt;
    DWORD lPrivate;
} MSG;
typedef struct {
    UINT cbSize;
    UINT style;
    WNDPROC lpfnWndProc;
    int cbClsExtra;
    int cbWndExtra;
    HINSTANCE hInstance;
    HICON hIcon;
    HCURSOR hCursor;
    HBRUSH hbrBackground;
    LPCSTR lpszMenuName;
    LPCSTR lpszClassName;
    HICON hIconSm;
} WNDCLASSEXA;
typedef struct {
    HDC hdc;
    BOOL fErase;
    RECT rcPaint;
    BOOL fRestore;
    BOOL fIncUpdate;
    BYTE rgbReserved[32];
} PAINTSTRUCT;
typedef struct { int64_t QuadPart; } LARGE_INTEGER;
typedef struct {
    DWORD biSize;
    LONG biWidth;
    LONG biHeight;
    WORD biPlanes;
    WORD biBitCount;
    DWORD biCompression;
    DWORD biSizeImage;
    LONG biXPelsPerMeter;
    LONG biYPelsPerMeter;
    DWORD biClrUsed;
    DWORD biClrImportant;
} BITMAPINFOHEADER;
typedef struct { BYTE rgbBlue; BYTE rgbGreen; BYTE rgbRed; BYTE rgbReserved; } RGBQUAD;
typedef struct { BITMAPINFOHEADER bmiHeader; RGBQUAD bmiColors[1]; } BITMAPINFO;
typedef struct {
    WORD wFormatTag;
    WORD nChannels;
    DWORD nSamplesPerSec;
    DWORD nAvgBytesPerSec;
    WORD nBlockAlign;
    WORD wBitsPerSample;
    WORD cbSize;
} WAVEFORMATEX;
typedef struct wavehdr_tag {
    LPSTR lpData;
    DWORD dwBufferLength;
    DWORD dwBytesRecorded;
    DWORD_PTR dwUser;
    DWORD dwFlags;
    DWORD dwLoops;
    struct wavehdr_tag *lpNext;
    DWORD_PTR reserved;
} WAVEHDR;
__declspec(dllimport) HINSTANCE __stdcall GetModuleHandleA(LPCSTR);
__declspec(dllimport) ATOM __stdcall RegisterClassExA(const WNDCLASSEXA *);
__declspec(dllimport) DWORD __stdcall GetLastError(void);
__declspec(dllimport) BOOL __stdcall AdjustWindowRect(RECT *, DWORD, BOOL);
__declspec(dllimport) HWND __stdcall CreateWindowExA(DWORD, LPCSTR, LPCSTR, DWORD,
    int, int, int, int, HWND, HANDLE, HINSTANCE, void *);
__declspec(dllimport) BOOL __stdcall ShowWindow(HWND, int);
__declspec(dllimport) BOOL __stdcall UpdateWindow(HWND);
__declspec(dllimport) BOOL __stdcall SetForegroundWindow(HWND);
__declspec(dllimport) BOOL __stdcall SetWindowTextA(HWND, LPCSTR);
__declspec(dllimport) int __stdcall GetSystemMetrics(int);
__declspec(dllimport) BOOL __stdcall DestroyWindow(HWND);
__declspec(dllimport) LRESULT __stdcall DefWindowProcA(HWND, UINT, WPARAM, LPARAM);
__declspec(dllimport) BOOL __stdcall GetClientRect(HWND, RECT *);
__declspec(dllimport) BOOL __stdcall ClientToScreen(HWND, POINT *);
__declspec(dllimport) HWND __stdcall GetForegroundWindow(void);
__declspec(dllimport) HWND __stdcall SetCapture(HWND);
__declspec(dllimport) BOOL __stdcall ReleaseCapture(void);
__declspec(dllimport) HWND __stdcall GetCapture(void);
__declspec(dllimport) int __stdcall ShowCursor(BOOL);
__declspec(dllimport) BOOL __stdcall SetCursorPos(int, int);
__declspec(dllimport) BOOL __stdcall PeekMessageA(MSG *, HWND, UINT, UINT, UINT);
__declspec(dllimport) LRESULT __stdcall DispatchMessageA(const MSG *);
__declspec(dllimport) DWORD __stdcall GetEnvironmentVariableA(
    LPCSTR, LPSTR, DWORD);
__declspec(dllimport) HCURSOR __stdcall LoadCursorA(HINSTANCE, LPCSTR);
__declspec(dllimport) HDC __stdcall BeginPaint(HWND, PAINTSTRUCT *);
__declspec(dllimport) BOOL __stdcall EndPaint(HWND, const PAINTSTRUCT *);
__declspec(dllimport) HDC __stdcall GetDC(HWND);
__declspec(dllimport) int __stdcall ReleaseDC(HWND, HDC);
__declspec(dllimport) BOOL __stdcall PatBlt(HDC, int, int, int, int, DWORD);
__declspec(dllimport) int __stdcall SetStretchBltMode(HDC, int);
__declspec(dllimport) int __stdcall StretchDIBits(HDC, int, int, int, int, int, int,
    int, int, const void *, const BITMAPINFO *, UINT, DWORD);
__declspec(dllimport) int __stdcall MessageBoxA(HWND, LPCSTR, LPCSTR, UINT);
__declspec(dllimport) BOOL __stdcall QueryPerformanceFrequency(LARGE_INTEGER *);
__declspec(dllimport) BOOL __stdcall QueryPerformanceCounter(LARGE_INTEGER *);
__declspec(dllimport) void __stdcall Sleep(DWORD);
__declspec(dllimport) void __stdcall ExitProcess(UINT);
__declspec(dllimport) HANDLE __stdcall CreateFileA(LPCSTR, DWORD, DWORD, void *, DWORD, DWORD, HANDLE);
__declspec(dllimport) BOOL __stdcall CloseHandle(HANDLE);
__declspec(dllimport) BOOL __stdcall ReadFile(HANDLE, void *, DWORD, DWORD *, void *);
__declspec(dllimport) BOOL __stdcall WriteFile(HANDLE, const void *, DWORD, DWORD *, void *);
__declspec(dllimport) BOOL __stdcall GetFileSizeEx(HANDLE, LARGE_INTEGER *);
__declspec(dllimport) BOOL __stdcall SetFilePointerEx(HANDLE, LARGE_INTEGER, LARGE_INTEGER *, DWORD);
__declspec(dllimport) UINT __stdcall waveOutOpen(HWAVEOUT *, UINT, const WAVEFORMATEX *, DWORD_PTR, DWORD_PTR, DWORD);
__declspec(dllimport) UINT __stdcall waveOutPrepareHeader(HWAVEOUT, WAVEHDR *, UINT);
__declspec(dllimport) UINT __stdcall waveOutUnprepareHeader(HWAVEOUT, WAVEHDR *, UINT);
__declspec(dllimport) UINT __stdcall waveOutWrite(HWAVEOUT, WAVEHDR *, UINT);
__declspec(dllimport) UINT __stdcall waveOutReset(HWAVEOUT);
__declspec(dllimport) UINT __stdcall waveOutClose(HWAVEOUT);

#define FALSE 0
#define TRUE 1
#define CS_OWNDC 0x0020U
#define WS_OVERLAPPEDWINDOW 0x00CF0000UL
#define SW_SHOW 5
#define SW_MAXIMIZE 3
#define SM_CXSCREEN 0
#define SM_CYSCREEN 1
#define CW_USEDEFAULT ((int)0x80000000U)
#define PM_REMOVE 0x0001U
#define WM_CLOSE 0x0010U
#define WM_SETFOCUS 0x0007U
#define WM_KILLFOCUS 0x0008U
#define WM_PAINT 0x000FU
#define WM_ERASEBKGND 0x0014U
#define WM_QUIT 0x0012U
#define WM_KEYDOWN 0x0100U
#define WM_KEYUP 0x0101U
#define WM_SYSKEYDOWN 0x0104U
#define WM_SYSKEYUP 0x0105U
#define WM_MOUSEMOVE 0x0200U
#define WM_LBUTTONDOWN 0x0201U
#define WM_LBUTTONUP 0x0202U
#define WM_RBUTTONDOWN 0x0204U
#define WM_RBUTTONUP 0x0205U
#define WM_MBUTTONDOWN 0x0207U
#define WM_MBUTTONUP 0x0208U
#define VK_BACK 0x08U
#define VK_TAB 0x09U
#define VK_RETURN 0x0DU
#define VK_SHIFT 0x10U
#define VK_CONTROL 0x11U
#define VK_MENU 0x12U
#define VK_PAUSE 0x13U
#define VK_ESCAPE 0x1BU
#define VK_SPACE 0x20U
#define VK_LEFT 0x25U
#define VK_UP 0x26U
#define VK_RIGHT 0x27U
#define VK_DOWN 0x28U
#define VK_F1 0x70U
#define VK_F2 0x71U
#define VK_F3 0x72U
#define VK_F4 0x73U
#define VK_F5 0x74U
#define VK_F6 0x75U
#define VK_F7 0x76U
#define VK_F8 0x77U
#define VK_F9 0x78U
#define VK_F10 0x79U
#define VK_F11 0x7AU
#define VK_F12 0x7BU
#define VK_LSHIFT 0xA0U
#define VK_RSHIFT 0xA1U
#define VK_LCONTROL 0xA2U
#define VK_RCONTROL 0xA3U
#define VK_LMENU 0xA4U
#define VK_RMENU 0xA5U
#define VK_OEM_1 0xBAU
#define VK_OEM_PLUS 0xBBU
#define VK_OEM_COMMA 0xBCU
#define VK_OEM_MINUS 0xBDU
#define VK_OEM_PERIOD 0xBEU
#define VK_OEM_2 0xBFU
#define VK_OEM_3 0xC0U
#define VK_OEM_4 0xDBU
#define VK_OEM_5 0xDCU
#define VK_OEM_6 0xDDU
#define VK_OEM_7 0xDEU
#define ERROR_CLASS_ALREADY_EXISTS 1410UL
#define MB_OK 0x00000000U
#define MB_ICONERROR 0x00000010U
#define BI_RGB 0UL
#define BLACKNESS 0x00000042UL
#define COLORONCOLOR 3
#define DIB_RGB_COLORS 0U
#define SRCCOPY 0x00CC0020UL
#define GENERIC_READ 0x80000000UL
#define GENERIC_WRITE 0x40000000UL
#define FILE_SHARE_READ 0x00000001UL
#define CREATE_ALWAYS 2UL
#define OPEN_EXISTING 3UL
#define FILE_ATTRIBUTE_NORMAL 0x00000080UL
#define FILE_BEGIN 0UL
#define INVALID_HANDLE_VALUE ((HANDLE)(intptr_t)-1)
#define WAVE_FORMAT_PCM 1U
#define WAVE_MAPPER ((UINT)-1)
#define CALLBACK_NULL 0UL
#define MMSYSERR_NOERROR 0U
#define WHDR_DONE 0x00000001UL
#define IDC_ARROW ((LPCSTR)(uintptr_t)32512U)

static int MouseX(LPARAM value)
{
    return (int)(int16_t)(uint16_t)((uintptr_t)value & UINT16_MAX);
}

static int MouseY(LPARAM value)
{
    return (int)(int16_t)(uint16_t)(((uintptr_t)value >> 16U) & UINT16_MAX);
}

#include "abi.h"

#ifdef main
#undef main
#endif

int DoomGuestMain(int argc, char **argv);

#define GUEST_MEMORY_BYTES (64 * 1024 * 1024)
#define HOST_FILE_CAPACITY 64
#define EVENT_QUEUE_CAPACITY 256
#define AUDIO_BLOCK_COUNT 8
#define AUDIO_FRAMES_PER_BLOCK 512
#define AUDIO_CHANNELS 2
#define WINDOW_CLIENT_WIDTH 1280
#define WINDOW_CLIENT_HEIGHT 720
#define SETTINGS_BUFFER_BYTES 65536
#define WAD_ROUTE_BYTES 4096
#define LANGUAGE_NAME_BYTES 64
#define SETTINGS_WAD_CAPACITY 512
#define MAX_DEBUG_ARGUMENTS 1024

typedef struct
{
    boolean maximized;
    int window_width;
    int window_height;
    boolean paced_60hz;
    boolean show_fps;
    char iwad[WAD_ROUTE_BYTES];
    char language[LANGUAGE_NAME_BYTES];
    char wads[SETTINGS_WAD_CAPACITY][WAD_ROUTE_BYTES];
    int wad_count;
} debug_settings_t;

static debug_settings_t debug_settings = {
    .maximized = false,
    .window_width = WINDOW_CLIENT_WIDTH,
    .window_height = WINDOW_CLIENT_HEIGHT,
    .paced_60hz = false,
    .show_fps = false,
    .iwad = {0},
    .language = {0},
    .wads = {{0}},
    .wad_count = 0,
};

_Alignas(16) static unsigned char guest_memory[GUEST_MEMORY_BYTES];
static char settings_json[SETTINGS_BUFFER_BYTES];
static char fallback_iwad[WAD_ROUTE_BYTES];
static char *debug_arguments[MAX_DEBUG_ARGUMENTS];
static char fatal_error_message[4096];
static HWND window_handle;
static HINSTANCE instance_handle;
static doom_host_video_config_t video_config;
static BITMAPINFO *bitmap_info;
static unsigned char bitmap_info_storage[sizeof(BITMAPINFOHEADER) + 256U * sizeof(RGBQUAD)];
static doom_host_event_t event_queue[EVENT_QUEUE_CAPACITY];
static unsigned int event_read;
static unsigned int event_write;
static int mouse_buttons;
static boolean relative_mouse;
static boolean mouse_capture_requested;
static boolean mouse_centering;
static boolean mouse_captured;
static boolean window_has_focus;
static LARGE_INTEGER performance_frequency;

#define HOST_FRAME_MAX_WIDTH 1280
#define HOST_FRAME_MAX_HEIGHT 600
static byte last_frame[HOST_FRAME_MAX_WIDTH * HOST_FRAME_MAX_HEIGHT];
static int last_frame_width;
static int last_frame_height;
static boolean last_frame_valid;
static LARGE_INTEGER performance_origin;
static uint64_t last_present_ns;
static uint64_t fps_window_start_ns;
static int fps_window_frames;
static int displayed_fps;
static char trace_language[24] = "HOST";
static char trace_source[64] = "startup";
static char trace_instruction[128] = "initializing";
static uint64_t trace_location;
static uint64_t trace_title_update_ns;

static HWAVEOUT audio_output;
static WAVEHDR audio_headers[AUDIO_BLOCK_COUNT];
static int16_t audio_samples[AUDIO_BLOCK_COUNT][AUDIO_FRAMES_PER_BLOCK * AUDIO_CHANNELS];
static boolean audio_busy[AUDIO_BLOCK_COUNT];
static boolean audio_initialized;

static void *file_handles[HOST_FILE_CAPACITY];

static const char *SkipJsonSpace(const char *cursor)
{
    while (*cursor == ' ' || *cursor == '\t' || *cursor == '\r' || *cursor == '\n')
        ++cursor;
    return cursor;
}

static const char *FindJsonValue(const char *json, const char *key)
{
    const char *cursor = json;
    int key_length = 0;

    while (key[key_length] != '\0')
        ++key_length;
    while (*cursor != '\0')
    {
        if (*cursor == '"')
        {
            const char *name = cursor + 1;
            int index = 0;
            while (index < key_length && name[index] == key[index])
                ++index;
            if (index == key_length && name[index] == '"')
            {
                cursor = SkipJsonSpace(name + index + 1);
                if (*cursor != ':')
                    return NULL;
                return SkipJsonSpace(cursor + 1);
            }
        }
        ++cursor;
    }
    return NULL;
}

static boolean ParseJsonBoolean(const char *json, const char *key, boolean *value)
{
    const char *cursor = FindJsonValue(json, key);

    if (cursor == NULL)
        return false;
    if (cursor[0] == 't' && cursor[1] == 'r' && cursor[2] == 'u' && cursor[3] == 'e')
    {
        *value = true;
        return true;
    }
    if (cursor[0] == 'f' && cursor[1] == 'a' && cursor[2] == 'l' &&
        cursor[3] == 's' && cursor[4] == 'e')
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

static boolean ParseJsonResolution(const char *json, int *width, int *height)
{
    const char *cursor = FindJsonValue(json, "resolution");

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
    return *cursor == ']';
}

static boolean ParseJsonStringValue(const char **cursor_ptr, char *output,
                                    int capacity)
{
    const char *cursor = SkipJsonSpace(*cursor_ptr);
    int length = 0;

    if (*cursor != '"' || capacity <= 0)
        return false;
    ++cursor;
    while (*cursor != '\0' && *cursor != '"')
    {
        char value = *cursor++;
        if (value == '\\')
        {
            const char escaped = *cursor++;
            if (escaped == '\\' || escaped == '"' || escaped == '/')
                value = escaped;
            else
                return false;
        }
        if (length + 1 >= capacity)
            return false;
        output[length++] = value;
    }
    if (*cursor != '"')
        return false;
    ++cursor;
    output[length] = '\0';
    *cursor_ptr = cursor;
    return true;
}

static boolean ParseJsonString(const char *json, const char *key, char *output,
                               int capacity)
{
    const char *cursor = FindJsonValue(json, key);

    if (cursor == NULL)
        return false;
    return ParseJsonStringValue(&cursor, output, capacity);
}

static int ParseJsonStringArray(const char *json, const char *key,
                                char output[SETTINGS_WAD_CAPACITY][WAD_ROUTE_BYTES])
{
    const char *cursor = FindJsonValue(json, key);
    int count = 0;

    if (cursor == NULL || *cursor != '[')
        return 0;
    ++cursor;
    for (;;)
    {
        cursor = SkipJsonSpace(cursor);
        if (*cursor == ']')
            return count;
        if (count >= SETTINGS_WAD_CAPACITY ||
            !ParseJsonStringValue(&cursor, output[count], WAD_ROUTE_BYTES))
            return -1;
        ++count;
        cursor = SkipJsonSpace(cursor);
        if (*cursor == ']')
            return count;
        if (*cursor != ',')
            return -1;
        ++cursor;
    }
}

static void LoadDebugSettings(void)
{
    HANDLE file;
    DWORD bytes_read = 0;
    int width;
    int height;

    file = CreateFileA("settings.json", GENERIC_READ, FILE_SHARE_READ, NULL,
                       OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, NULL);
    if (file == INVALID_HANDLE_VALUE)
        return;
    if (!ReadFile(file, settings_json, (DWORD)(sizeof(settings_json) - 1U),
                  &bytes_read, NULL))
    {
        (void)CloseHandle(file);
        return;
    }
    (void)CloseHandle(file);
    settings_json[bytes_read] = '\0';

    (void)ParseJsonBoolean(settings_json, "maximized", &debug_settings.maximized);
    (void)ParseJsonBoolean(settings_json, "vsync", &debug_settings.paced_60hz);
    (void)ParseJsonBoolean(settings_json, "show_fps", &debug_settings.show_fps);
    if (ParseJsonResolution(settings_json, &width, &height) &&
        width >= 320 && height >= 200)
    {
        debug_settings.window_width = width;
        debug_settings.window_height = height;
    }
    if (!ParseJsonString(settings_json, "iwad", debug_settings.iwad,
                         (int)sizeof(debug_settings.iwad)))
    {
        (void)ParseJsonString(settings_json, "wadroute", debug_settings.iwad,
                              (int)sizeof(debug_settings.iwad));
    }
    (void)ParseJsonString(settings_json, "language", debug_settings.language,
                          (int)sizeof(debug_settings.language));
    debug_settings.wad_count =
        ParseJsonStringArray(settings_json, "wads", debug_settings.wads);
    if (debug_settings.wad_count < 0)
    {
        debug_settings.wad_count = 0;
        (void)MessageBoxA(NULL, "Invalid wads array in settings.json",
                          "DOOM settings", MB_OK | MB_ICONERROR);
    }
}

static boolean HasArgument(int argc, char **argv, const char *name)
{
    for (int index = 1; index < argc; ++index)
    {
        const char *left = argv[index];
        const char *right = name;
        while (*left != '\0' && *left == *right)
        {
            ++left;
            ++right;
        }
        if (*left == '\0' && *right == '\0')
            return true;
    }
    return false;
}

static boolean AppendDebugArgument(int *count, char *value)
{
    if (*count < 0 || *count >= MAX_DEBUG_ARGUMENTS)
        return false;
    debug_arguments[*count] = value;
    ++*count;
    return true;
}

static int BuildDebugArguments(int argc, char **argv)
{
    static char arg_iwad[] = "-iwad";
    static char arg_file[] = "-file";
    static char arg_language[] = "-default-language";
    int count = 0;
    const boolean has_iwad = HasArgument(argc, argv, arg_iwad);
    const boolean has_file = HasArgument(argc, argv, arg_file);
    const boolean has_language = HasArgument(argc, argv, arg_language);

    for (int index = 0; index < argc; ++index)
        if (!AppendDebugArgument(&count, argv[index]))
            return -1;

    if (!has_language && debug_settings.language[0] != '\0')
    {
        if (!AppendDebugArgument(&count, arg_language) ||
            !AppendDebugArgument(&count, debug_settings.language))
            return -1;
    }
    if (!has_iwad)
    {
        char *iwad = NULL;
        if (debug_settings.iwad[0] != '\0')
            iwad = debug_settings.iwad;
        else
        {
            const DWORD length = GetEnvironmentVariableA(
                "MALBOLGE_DOOM_FALLBACK_IWAD", fallback_iwad,
                (DWORD)sizeof(fallback_iwad));
            if (length > 0 && length < (DWORD)sizeof(fallback_iwad))
                iwad = fallback_iwad;
        }
        if (iwad != NULL &&
            (!AppendDebugArgument(&count, arg_iwad) ||
             !AppendDebugArgument(&count, iwad)))
            return -1;
    }
    if (!has_file && debug_settings.wad_count > 0)
    {
        if (!AppendDebugArgument(&count, arg_file))
            return -1;
        for (int index = 0; index < debug_settings.wad_count; ++index)
            if (!AppendDebugArgument(&count, debug_settings.wads[index]))
                return -1;
    }
    return count;
}

int main(int argc, char **argv)
{
    int debug_argc;

    LoadDebugSettings();
    debug_argc = BuildDebugArguments(argc, argv);
    if (debug_argc < 0)
    {
        (void)MessageBoxA(NULL, "Too many DOOM debug arguments",
                          "DOOM settings", MB_OK | MB_ICONERROR);
        return 2;
    }
    return DoomGuestMain(debug_argc, debug_arguments);
}

static void AppendText(char *output, int *length, int capacity,
                       const char *text)
{
    if (output == NULL || length == NULL || text == NULL || capacity <= 0)
        return;
    while (*text != '\0' && *length + 1 < capacity)
        output[(*length)++] = *text++;
}

static void AppendDecimal(char *text, int *length, int capacity, int value)
{
    char reversed[16];
    int count = 0;

    if (value < 0)
    {
        if (*length + 1 < capacity)
            text[(*length)++] = '-';
        value = -value;
    }
    if (value == 0)
        reversed[count++] = '0';
    while (value > 0 && count < (int)sizeof(reversed))
    {
        reversed[count++] = (char)('0' + value % 10);
        value /= 10;
    }
    while (count > 0 && *length + 1 < capacity)
        text[(*length)++] = reversed[--count];
}

static void AppendUnsignedDecimal(char *text, int *length, int capacity,
                                  uint64_t value)
{
    char reversed[32];
    int count = 0;

    if (value == 0)
        reversed[count++] = '0';
    while (value > 0 && count < (int)sizeof(reversed))
    {
        reversed[count++] = (char)('0' + value % UINT64_C(10));
        value /= UINT64_C(10);
    }
    while (count > 0 && *length + 1 < capacity)
        text[(*length)++] = reversed[--count];
}

static void CopyText(char *output, int capacity, const char *text)
{
    int length = 0;

    if (output == NULL || capacity <= 0)
        return;
    if (text != NULL)
        AppendText(output, &length, capacity, text);
    output[length] = '\0';
}

static const char *SourceBasename(const char *path)
{
    const char *base = path;

    if (path == NULL)
        return "unknown";
    for (const char *cursor = path; *cursor != '\0'; ++cursor)
        if (*cursor == '/' || *cursor == '\\')
            base = cursor + 1;
    return base;
}

static void UpdateFpsTitle(void)
{
    char title[256];
    int length = 0;

    if (window_handle == NULL)
        return;
    if (!debug_settings.show_fps)
    {
        (void)SetWindowTextA(window_handle, "DOOM");
        return;
    }
    AppendText(title, &length, (int)sizeof(title), "FPS ");
    AppendDecimal(title, &length, (int)sizeof(title), displayed_fps);
    AppendText(title, &length, (int)sizeof(title), " - ");
    AppendText(title, &length, (int)sizeof(title), trace_language);
    AppendText(title, &length, (int)sizeof(title), " ");
    AppendText(title, &length, (int)sizeof(title), trace_source);
    if (trace_location > 0)
    {
        AppendText(title, &length, (int)sizeof(title),
                   trace_language[0] == 'C' &&
                           trace_language[1] == '\0'
                       ? ":"
                       : "@");
        AppendUnsignedDecimal(title, &length, (int)sizeof(title),
                              trace_location);
    }
    AppendText(title, &length, (int)sizeof(title), " ");
    AppendText(title, &length, (int)sizeof(title), trace_instruction);
    title[length] = '\0';
    (void)SetWindowTextA(window_handle, title);
}

void DoomHost_DebugExecutionActivity(const char *language,
                                     const char *source,
                                     uint64_t location,
                                     const char *instruction)
{
    const uint64_t now = DoomHost_MonotonicNanoseconds();

    CopyText(trace_language, (int)sizeof(trace_language), language);
    CopyText(trace_source, (int)sizeof(trace_source), SourceBasename(source));
    CopyText(trace_instruction, (int)sizeof(trace_instruction), instruction);
    trace_location = location;
    if (trace_title_update_ns == 0 ||
        now - trace_title_update_ns >= UINT64_C(100000000))
    {
        trace_title_update_ns = now;
        UpdateFpsTitle();
    }
}

static void QueueEvent(const doom_host_event_t *event)
{
    const unsigned int next = (event_write + 1U) % EVENT_QUEUE_CAPACITY;
    if (event == NULL || next == event_read)
        return;
    event_queue[event_write] = *event;
    event_write = next;
}

static int TranslateVirtualKey(WPARAM key)
{
    if (key >= 'A' && key <= 'Z')
        return (int)('a' + (char)(key - 'A'));
    if (key >= '0' && key <= '9')
        return (int)key;

    switch (key)
    {
        case VK_LEFT: return DOOM_HOST_KEY_LEFT;
        case VK_RIGHT: return DOOM_HOST_KEY_RIGHT;
        case VK_UP: return DOOM_HOST_KEY_UP;
        case VK_DOWN: return DOOM_HOST_KEY_DOWN;
        case VK_ESCAPE: return DOOM_HOST_KEY_ESCAPE;
        case VK_RETURN: return DOOM_HOST_KEY_ENTER;
        case VK_TAB: return DOOM_HOST_KEY_TAB;
        case VK_BACK: return DOOM_HOST_KEY_BACKSPACE;
        case VK_PAUSE: return DOOM_HOST_KEY_PAUSE;
        case VK_F1: return DOOM_HOST_KEY_F1;
        case VK_F2: return DOOM_HOST_KEY_F2;
        case VK_F3: return DOOM_HOST_KEY_F3;
        case VK_F4: return DOOM_HOST_KEY_F4;
        case VK_F5: return DOOM_HOST_KEY_F5;
        case VK_F6: return DOOM_HOST_KEY_F6;
        case VK_F7: return DOOM_HOST_KEY_F7;
        case VK_F8: return DOOM_HOST_KEY_F8;
        case VK_F9: return DOOM_HOST_KEY_F9;
        case VK_F10: return DOOM_HOST_KEY_F10;
        case VK_F11: return DOOM_HOST_KEY_F11;
        case VK_F12: return DOOM_HOST_KEY_F12;
        case VK_SHIFT: case VK_LSHIFT: case VK_RSHIFT: return DOOM_HOST_KEY_SHIFT;
        case VK_CONTROL: case VK_LCONTROL: case VK_RCONTROL: return DOOM_HOST_KEY_CONTROL;
        case VK_MENU: case VK_LMENU: case VK_RMENU: return DOOM_HOST_KEY_ALT;
        case VK_SPACE: return ' ';
        case VK_OEM_PLUS: return '=';
        case VK_OEM_MINUS: return '-';
        case VK_OEM_COMMA: return ',';
        case VK_OEM_PERIOD: return '.';
        case VK_OEM_1: return ';';
        case VK_OEM_2: return '/';
        case VK_OEM_3: return '`';
        case VK_OEM_4: return '[';
        case VK_OEM_5: return '\\';
        case VK_OEM_6: return ']';
        case VK_OEM_7: return '\'';
        default: return DOOM_HOST_KEY_NONE;
    }
}

static void RenderLastFrame(HDC dc);

static boolean WantsMouseCapture(void)
{
    return relative_mouse && mouse_capture_requested && window_has_focus;
}

static void CenterMouse(void)
{
    RECT client;
    POINT center;

    if (window_handle == NULL || !mouse_captured ||
        GetForegroundWindow() != window_handle)
        return;
    if (!GetClientRect(window_handle, &client))
        return;
    center.x = (client.right - client.left) / 2;
    center.y = (client.bottom - client.top) / 2;
    if (!ClientToScreen(window_handle, &center))
        return;
    mouse_centering = true;
    (void)SetCursorPos(center.x, center.y);
}

static void SetMouseCaptured(boolean capture)
{
    if (capture == mouse_captured)
        return;

    mouse_captured = capture;
    mouse_centering = false;
    if (capture)
    {
        (void)SetCapture(window_handle);
        while (ShowCursor(FALSE) >= 0) {}
        CenterMouse();
    }
    else
    {
        if (GetCapture() == window_handle)
            (void)ReleaseCapture();
        while (ShowCursor(TRUE) < 0) {}
    }
}

static void UpdateMouseCapture(void)
{
    SetMouseCaptured(WantsMouseCapture());
}

void DoomHost_SetRelativeMouseCapture(boolean capture)
{
    mouse_capture_requested = capture;
    UpdateMouseCapture();
}

static LRESULT __stdcall DoomWindowProc(HWND window, UINT message, WPARAM wparam, LPARAM lparam)
{
    doom_host_event_t event = {0};

    switch (message)
    {
        case WM_CLOSE:
            event.type = DOOM_HOST_EVENT_QUIT;
            QueueEvent(&event);
            return 0;

        case WM_SETFOCUS:
            window_has_focus = true;
            UpdateMouseCapture();
            return 0;

        case WM_KILLFOCUS:
            window_has_focus = false;
            SetMouseCaptured(false);
            return 0;

        case WM_KEYDOWN:
        case WM_SYSKEYDOWN:
            if (message == WM_KEYDOWN && wparam == VK_F5 &&
                (lparam & (LPARAM)(1UL << 30U)) == 0)
            {
                debug_settings.show_fps = !debug_settings.show_fps;
                UpdateFpsTitle();
                return 0;
            }
            if (message == WM_SYSKEYDOWN && wparam == VK_F4 &&
                (lparam & (LPARAM)(1UL << 29U)) != 0)
            {
                event.type = DOOM_HOST_EVENT_QUIT;
                QueueEvent(&event);
                return 0;
            }
            if ((lparam & (LPARAM)(1UL << 30U)) == 0)
            {
                event.type = DOOM_HOST_EVENT_KEY_DOWN;
                event.key = TranslateVirtualKey(wparam);
                if (event.key != DOOM_HOST_KEY_NONE)
                    QueueEvent(&event);
            }
            return 0;

        case WM_KEYUP:
        case WM_SYSKEYUP:
            event.type = DOOM_HOST_EVENT_KEY_UP;
            event.key = TranslateVirtualKey(wparam);
            if (event.key != DOOM_HOST_KEY_NONE)
                QueueEvent(&event);
            return 0;

        case WM_LBUTTONDOWN: mouse_buttons |= 1; break;
        case WM_LBUTTONUP: mouse_buttons &= ~1; break;
        case WM_MBUTTONDOWN: mouse_buttons |= 2; break;
        case WM_MBUTTONUP: mouse_buttons &= ~2; break;
        case WM_RBUTTONDOWN: mouse_buttons |= 4; break;
        case WM_RBUTTONUP: mouse_buttons &= ~4; break;

        case WM_MOUSEMOVE:
            if (mouse_captured && GetForegroundWindow() == window)
            {
                RECT client;
                const int x = MouseX(lparam);
                const int y = MouseY(lparam);
                int center_x;
                int center_y;

                if (!GetClientRect(window, &client))
                    return 0;
                center_x = (client.right - client.left) / 2;
                center_y = (client.bottom - client.top) / 2;
                if (mouse_centering && x == center_x && y == center_y)
                {
                    mouse_centering = false;
                    return 0;
                }
                if (x != center_x || y != center_y)
                {
                    event.type = DOOM_HOST_EVENT_MOUSE;
                    event.mouse_buttons = mouse_buttons;
                    event.mouse_dx = x - center_x;
                    event.mouse_dy = y - center_y;
                    QueueEvent(&event);
                    CenterMouse();
                }
            }
            return 0;

        case WM_ERASEBKGND:
            return 1;

        case WM_PAINT:
        {
            PAINTSTRUCT paint;
            HDC dc = BeginPaint(window, &paint);
            if (dc != NULL)
                RenderLastFrame(dc);
            (void)EndPaint(window, &paint);
            return 0;
        }

        default:
            return DefWindowProcA(window, message, wparam, lparam);
    }

    event.type = DOOM_HOST_EVENT_MOUSE;
    event.mouse_buttons = mouse_buttons;
    QueueEvent(&event);
    return 0;
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
    int copy_length;
    if (text == NULL || length < 0)
        return;
    copy_length = length;
    if (copy_length >= (int)sizeof(fatal_error_message))
        copy_length = (int)sizeof(fatal_error_message) - 1;
    for (int i = 0; i < copy_length; ++i)
        fatal_error_message[i] = text[i];
    fatal_error_message[copy_length] = '\0';
    (void)MessageBoxA(window_handle, fatal_error_message, "DOOM fatal error",
                      MB_OK | MB_ICONERROR);
}

[[noreturn]] void DoomHost_Terminate(int status)
{
    ExitProcess((UINT)status);
    for (;;) {}
}

boolean DoomHost_VideoInitialize(const doom_host_video_config_t *config)
{
    WNDCLASSEXA window_class = {0};
    RECT rectangle = {0, 0, debug_settings.window_width,
                      debug_settings.window_height};
    DWORD style = WS_OVERLAPPEDWINDOW;
    int window_width;
    int window_height;
    int window_x;
    int window_y;

    if (config == NULL || config->logical_width <= 0 || config->logical_height <= 0 ||
        config->display_aspect_width <= 0 || config->display_aspect_height <= 0)
        return false;

    video_config = *config;
    relative_mouse = config->relative_mouse;
    bitmap_info = (BITMAPINFO *)(void *)bitmap_info_storage;
    for (unsigned int i = 0; i < sizeof(bitmap_info_storage); ++i)
        bitmap_info_storage[i] = 0;
    bitmap_info->bmiHeader.biSize = sizeof(BITMAPINFOHEADER);
    bitmap_info->bmiHeader.biWidth = config->logical_width;
    bitmap_info->bmiHeader.biHeight = -config->logical_height;
    bitmap_info->bmiHeader.biPlanes = 1;
    bitmap_info->bmiHeader.biBitCount = 8;
    bitmap_info->bmiHeader.biCompression = BI_RGB;
    bitmap_info->bmiHeader.biClrUsed = 256;
    bitmap_info->bmiHeader.biClrImportant = 256;

    instance_handle = GetModuleHandleA(NULL);
    window_class.cbSize = sizeof(window_class);
    window_class.style = CS_OWNDC;
    window_class.lpfnWndProc = DoomWindowProc;
    window_class.hInstance = instance_handle;
    window_class.hCursor = LoadCursorA(NULL, IDC_ARROW);
    window_class.lpszClassName = "MalbolgeDoomWindow";
    if (!RegisterClassExA(&window_class) && GetLastError() != ERROR_CLASS_ALREADY_EXISTS)
        return false;

    if (!AdjustWindowRect(&rectangle, style, FALSE))
        return false;
    window_width = rectangle.right - rectangle.left;
    window_height = rectangle.bottom - rectangle.top;
    window_x = (GetSystemMetrics(SM_CXSCREEN) - window_width) / 2;
    window_y = (GetSystemMetrics(SM_CYSCREEN) - window_height) / 2;
    if (window_x < 0)
        window_x = 0;
    if (window_y < 0)
        window_y = 0;
    window_handle = CreateWindowExA(0, window_class.lpszClassName,
                                    config->title != NULL ? config->title : "DOOM",
                                    style, window_x, window_y, window_width,
                                    window_height, NULL, NULL, instance_handle, NULL);
    if (window_handle == NULL)
        return false;

    ShowWindow(window_handle, debug_settings.maximized ? SW_MAXIMIZE : SW_SHOW);
    (void)UpdateWindow(window_handle);
    UpdateFpsTitle();
    (void)SetForegroundWindow(window_handle);
    window_has_focus = GetForegroundWindow() == window_handle;
    UpdateMouseCapture();
    return true;
}

void DoomHost_VideoShutdown(void)
{
    SetMouseCaptured(false);
    if (window_handle != NULL)
    {
        (void)DestroyWindow(window_handle);
        window_handle = NULL;
    }
}

boolean DoomHost_PollEvent(doom_host_event_t *event)
{
    MSG message;
    if (event == NULL)
        return false;

    UpdateMouseCapture();
    while (event_read == event_write && PeekMessageA(&message, NULL, 0, 0, PM_REMOVE))
    {
        if (message.message == WM_QUIT)
        {
            doom_host_event_t quit = {0};
            quit.type = DOOM_HOST_EVENT_QUIT;
            QueueEvent(&quit);
            break;
        }
        (void)DispatchMessageA(&message);
    }
    UpdateMouseCapture();

    if (event_read == event_write)
        return false;
    *event = event_queue[event_read];
    event_read = (event_read + 1U) % EVENT_QUEUE_CAPACITY;
    return true;
}

void DoomHost_SetPalette(const byte *rgb_palette, int color_count)
{
    RGBQUAD *colors;
    if (rgb_palette == NULL || color_count != 256 || bitmap_info == NULL)
        return;
    colors = bitmap_info->bmiColors;
    for (int i = 0; i < 256; ++i)
    {
        colors[i].rgbRed = rgb_palette[i * 3];
        colors[i].rgbGreen = rgb_palette[i * 3 + 1];
        colors[i].rgbBlue = rgb_palette[i * 3 + 2];
        colors[i].rgbReserved = 0;
    }
}

static void RenderLastFrame(HDC dc)
{
    RECT client;
    int client_width;
    int client_height;
    int draw_width;
    int draw_height;
    int draw_x;
    int draw_y;

    if (dc == NULL || !last_frame_valid || bitmap_info == NULL ||
        !GetClientRect(window_handle, &client))
        return;

    client_width = client.right - client.left;
    client_height = client.bottom - client.top;
    if ((int64_t)client_width * video_config.display_aspect_height <=
        (int64_t)client_height * video_config.display_aspect_width)
    {
        draw_width = client_width;
        draw_height = (int)((int64_t)client_width * video_config.display_aspect_height /
                            video_config.display_aspect_width);
    }
    else
    {
        draw_height = client_height;
        draw_width = (int)((int64_t)client_height * video_config.display_aspect_width /
                           video_config.display_aspect_height);
    }
    draw_x = (client_width - draw_width) / 2;
    draw_y = (client_height - draw_height) / 2;

    if (draw_y > 0)
    {
        (void)PatBlt(dc, 0, 0, client_width, draw_y, BLACKNESS);
        (void)PatBlt(dc, 0, draw_y + draw_height, client_width,
                     client_height - draw_y - draw_height, BLACKNESS);
    }
    if (draw_x > 0)
    {
        (void)PatBlt(dc, 0, draw_y, draw_x, draw_height, BLACKNESS);
        (void)PatBlt(dc, draw_x + draw_width, draw_y,
                     client_width - draw_x - draw_width, draw_height, BLACKNESS);
    }

    (void)SetStretchBltMode(dc, COLORONCOLOR);
    (void)StretchDIBits(dc, draw_x, draw_y, draw_width, draw_height,
                        0, 0, last_frame_width, last_frame_height, last_frame,
                        bitmap_info, DIB_RGB_COLORS, SRCCOPY);
}

void DoomHost_PresentIndexed8(const byte *pixels, int width, int height, int pitch)
{
    HDC dc;

    if (window_handle == NULL || pixels == NULL || width <= 0 || height <= 0 ||
        pitch < width || width > HOST_FRAME_MAX_WIDTH ||
        height > HOST_FRAME_MAX_HEIGHT)
        return;

    for (int y = 0; y < height; ++y)
    {
        const byte *source = pixels + (size_t)y * (size_t)pitch;
        byte *destination = last_frame + (size_t)y * (size_t)width;
        for (int x = 0; x < width; ++x)
            destination[x] = source[x];
    }
    last_frame_width = width;
    last_frame_height = height;
    last_frame_valid = true;

    {
        uint64_t now = DoomHost_MonotonicNanoseconds();
        if (debug_settings.paced_60hz && last_present_ns != 0)
        {
            const uint64_t target_ns = UINT64_C(16666667);
            const uint64_t elapsed = now - last_present_ns;
            if (elapsed < target_ns)
            {
                const uint64_t remaining = target_ns - elapsed;
                if (remaining >= UINT64_C(2000000))
                    Sleep((DWORD)((remaining - UINT64_C(1000000)) / UINT64_C(1000000)));
                do
                {
                    now = DoomHost_MonotonicNanoseconds();
                } while (now - last_present_ns < target_ns);
            }
        }
        last_present_ns = now;
        if (fps_window_start_ns == 0)
            fps_window_start_ns = now;
        ++fps_window_frames;
        if (now - fps_window_start_ns >= UINT64_C(500000000))
        {
            const uint64_t duration = now - fps_window_start_ns;
            displayed_fps = (int)(((uint64_t)fps_window_frames * UINT64_C(1000000000) +
                                  duration / 2U) / duration);
            fps_window_start_ns = now;
            fps_window_frames = 0;
            UpdateFpsTitle();
        }
    }

    dc = GetDC(window_handle);
    if (dc != NULL)
    {
        RenderLastFrame(dc);
        (void)ReleaseDC(window_handle, dc);
    }
}

boolean DoomHost_AudioInitialize(const doom_host_audio_config_t *config)
{
    WAVEFORMATEX format = {0};
    if (config == NULL || config->sample_rate != 44100 || config->channel_count != 2 ||
        config->frames_per_buffer != AUDIO_FRAMES_PER_BLOCK)
        return false;

    format.wFormatTag = WAVE_FORMAT_PCM;
    format.nChannels = AUDIO_CHANNELS;
    format.nSamplesPerSec = (DWORD)config->sample_rate;
    format.wBitsPerSample = 16;
    format.nBlockAlign = (WORD)(AUDIO_CHANNELS * sizeof(int16_t));
    format.nAvgBytesPerSec = format.nSamplesPerSec * format.nBlockAlign;
    if (waveOutOpen(&audio_output, WAVE_MAPPER, &format, 0, 0, CALLBACK_NULL) != MMSYSERR_NOERROR)
        return false;

    for (int block = 0; block < AUDIO_BLOCK_COUNT; ++block)
    {
        WAVEHDR *header = &audio_headers[block];
        for (unsigned int i = 0; i < sizeof(*header); ++i)
            ((unsigned char *)(void *)header)[i] = 0;
        header->lpData = (LPSTR)(void *)audio_samples[block];
        header->dwBufferLength = sizeof(audio_samples[block]);
        if (waveOutPrepareHeader(audio_output, header, sizeof(*header)) != MMSYSERR_NOERROR)
        {
            waveOutReset(audio_output);
            for (int prepared = 0; prepared < block; ++prepared)
                (void)waveOutUnprepareHeader(audio_output, &audio_headers[prepared],
                                             sizeof(audio_headers[prepared]));
            (void)waveOutClose(audio_output);
            audio_output = NULL;
            return false;
        }
        audio_busy[block] = false;
    }
    audio_initialized = true;
    return true;
}

void DoomHost_AudioShutdown(void)
{
    if (!audio_initialized)
        return;
    (void)waveOutReset(audio_output);
    for (int block = 0; block < AUDIO_BLOCK_COUNT; ++block)
        (void)waveOutUnprepareHeader(audio_output, &audio_headers[block],
                                     sizeof(audio_headers[block]));
    (void)waveOutClose(audio_output);
    audio_output = NULL;
    audio_initialized = false;
}

static void ReclaimAudioBlocks(void)
{
    for (int block = 0; block < AUDIO_BLOCK_COUNT; ++block)
    {
        if (audio_busy[block] && (audio_headers[block].dwFlags & WHDR_DONE) != 0)
            audio_busy[block] = false;
    }
}

int DoomHost_AudioWritableFrames(void)
{
    int free_blocks = 0;
    if (!audio_initialized)
        return 0;
    ReclaimAudioBlocks();
    for (int block = 0; block < AUDIO_BLOCK_COUNT; ++block)
        if (!audio_busy[block])
            ++free_blocks;
    return free_blocks * AUDIO_FRAMES_PER_BLOCK;
}

void DoomHost_AudioSubmitS16(const int16_t *samples, int frame_count, int channel_count)
{
    if (!audio_initialized || samples == NULL || frame_count != AUDIO_FRAMES_PER_BLOCK ||
        channel_count != AUDIO_CHANNELS)
        return;
    ReclaimAudioBlocks();
    for (int block = 0; block < AUDIO_BLOCK_COUNT; ++block)
    {
        if (!audio_busy[block])
        {
            const int sample_count = frame_count * channel_count;
            for (int i = 0; i < sample_count; ++i)
                audio_samples[block][i] = samples[i];
            audio_headers[block].dwBufferLength =
                (DWORD)(sample_count * (int)sizeof(int16_t));
            audio_headers[block].dwFlags &= ~WHDR_DONE;
            if (waveOutWrite(audio_output, &audio_headers[block],
                             sizeof(audio_headers[block])) == MMSYSERR_NOERROR)
                audio_busy[block] = true;
            return;
        }
    }
}

static boolean ValidFile(doom_host_file_t file)
{
    return file > 0 && file < HOST_FILE_CAPACITY && file_handles[file] != NULL;
}

boolean DoomHost_FileOpenRead(const char *path, doom_host_file_t *file)
{
    HANDLE handle;
    int index;
    if (path == NULL || file == NULL)
        return false;
    for (index = 1; index < HOST_FILE_CAPACITY; ++index)
        if (file_handles[index] == NULL)
            break;
    if (index >= HOST_FILE_CAPACITY)
        return false;

    handle = CreateFileA(path, GENERIC_READ, FILE_SHARE_READ, NULL, OPEN_EXISTING,
                         FILE_ATTRIBUTE_NORMAL, NULL);
    if (handle == INVALID_HANDLE_VALUE)
        return false;
    file_handles[index] = handle;
    *file = (doom_host_file_t)index;
    return true;
}

void DoomHost_FileClose(doom_host_file_t file)
{
    if (!ValidFile(file))
        return;
    (void)CloseHandle((HANDLE)file_handles[file]);
    file_handles[file] = NULL;
}

int DoomHost_FileSize(doom_host_file_t file)
{
    LARGE_INTEGER size;
    if (!ValidFile(file))
        return -1;
    if (!GetFileSizeEx((HANDLE)file_handles[file], &size) || size.QuadPart < 0 ||
        size.QuadPart > INT32_MAX)
        return -1;
    return (int)size.QuadPart;
}

int DoomHost_FileReadAt(doom_host_file_t file, int offset, byte *data, int length)
{
    DWORD read_count = 0;
    if (!ValidFile(file) || offset < 0 || data == NULL || length < 0)
        return -1;
    {
        LARGE_INTEGER position;
        position.QuadPart = offset;
        if (!SetFilePointerEx((HANDLE)file_handles[file], position, NULL, FILE_BEGIN))
            return -1;
    }
    if (!ReadFile((HANDLE)file_handles[file], data, (DWORD)length, &read_count, NULL))
        return -1;
    return (int)read_count;
}

boolean DoomHost_FileWriteAll(const char *path, const byte *data, int length)
{
    HANDLE handle;
    DWORD written = 0;
    if (path == NULL || data == NULL || length < 0)
        return false;
    handle = CreateFileA(path, GENERIC_WRITE, 0, NULL, CREATE_ALWAYS,
                         FILE_ATTRIBUTE_NORMAL, NULL);
    if (handle == INVALID_HANDLE_VALUE)
        return false;
    if (!WriteFile(handle, data, (DWORD)length, &written, NULL) ||
        written != (DWORD)length)
    {
        (void)CloseHandle(handle);
        return false;
    }
    (void)CloseHandle(handle);
    return true;
}

boolean DoomHost_NetOpen(int local_port) { (void)local_port; return false; }
void DoomHost_NetClose(void) {}
boolean DoomHost_NetResolve(const char *host, int port, doom_host_net_endpoint_t *endpoint)
{
    (void)host; (void)port; (void)endpoint; return false;
}
boolean DoomHost_NetSend(doom_host_net_endpoint_t endpoint, const byte *data, int length)
{
    (void)endpoint; (void)data; (void)length; return false;
}
int DoomHost_NetReceive(byte *data, int capacity, doom_host_net_endpoint_t *source)
{
    (void)data; (void)capacity; (void)source; return -1;
}

uint64_t DoomHost_MonotonicNanoseconds(void)
{
    LARGE_INTEGER now;
    uint64_t ticks;
    if (performance_frequency.QuadPart <= 0)
    {
        if (!QueryPerformanceFrequency(&performance_frequency) ||
            !QueryPerformanceCounter(&performance_origin))
            return 0;
    }
    if (!QueryPerformanceCounter(&now) || now.QuadPart < performance_origin.QuadPart)
        return 0;
    ticks = (uint64_t)(now.QuadPart - performance_origin.QuadPart);
    return ticks / (uint64_t)performance_frequency.QuadPart * UINT64_C(1000000000) +
           ticks % (uint64_t)performance_frequency.QuadPart * UINT64_C(1000000000) /
               (uint64_t)performance_frequency.QuadPart;
}

void DoomHost_SleepNanoseconds(uint64_t nanoseconds)
{
    DWORD milliseconds = (DWORD)((nanoseconds + UINT64_C(999999)) / UINT64_C(1000000));
    if (milliseconds > 0)
        Sleep(milliseconds);
}
