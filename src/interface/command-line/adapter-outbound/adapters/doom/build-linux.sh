#!/usr/bin/env bash
set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
repo_root=$(cd -- "$script_dir/../../../../../.." && pwd)
guest_root="$repo_root/src/research/algorithms/domain/algorithms/doom"
guest="$guest_root/quality/out/doom_fixed/linuxdoom-1.10"
build="$repo_root/.temp/doom-linux-obj"
output="$repo_root/.temp/doom-linux"
clang="$repo_root/.dependencies/llvm/22.1.8/bin/clang"

rm -rf "$build"
mkdir -p "$build"

# The guest owns its libc-like memory/string primitives. These flags are part of
# the native-debug contract: without them a hosted compiler may rewrite those
# primitives back into calls to themselves.
for source in "$guest"/*.c; do
    object="$build/$(basename "${source%.c}").o"
    "$clang" -std=c23 -O2 -Wall -Wextra -Werror \
        -ffreestanding -fno-builtin -I"$guest" \
        -c "$source" -o "$object"
done

"$clang" -std=c23 -O2 -Wall -Wextra -Werror \
    -I"$script_dir" $(pkg-config --cflags sdl2) \
    -c "$script_dir/linux.c" -o "$build/linux.o"

"$clang" "$build"/*.o $(pkg-config --libs sdl2) -lm -o "$output"
printf '%s\n' "$output"
