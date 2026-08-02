#!/usr/bin/env bash
set -euo pipefail
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
destination="${1:-$HOME/.local/bin}"
mkdir -p "$destination"
ln -sfn "$script_dir/malbolge" "$destination/malbolge"
printf 'Installed malbolge shim: %s/malbolge\n' "$destination"
printf 'Ensure %s is in PATH.\n' "$destination"
