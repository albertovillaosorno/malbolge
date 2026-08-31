#!/usr/bin/env bash
set -euo pipefail
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
root="$(cd -- "$script_dir/../../../../.." && pwd)"
output="$script_dir/bin/malbolge"
mkdir -p "$script_dir/bin"
cd "$root"
cargo build --release --bin malbolge
cp .cache/rust/target/release/malbolge "$output"
chmod +x "$output"
