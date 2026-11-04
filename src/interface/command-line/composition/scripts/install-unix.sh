#!/usr/bin/env bash
set -euo pipefail
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
destination="${1:-$HOME/.local/bin}"
mkdir -p "$destination"
ln -sfn "$script_dir/malbolge" "$destination/malbolge"
ln -sfn "$script_dir/c2malbolge" "$destination/c2malbolge"
printf 'Installed malbolge shim: %s/malbolge\n' "$destination"
printf 'Installed c2malbolge shim: %s/c2malbolge\n' "$destination"
printf 'Ensure %s is in PATH.\n' "$destination"
