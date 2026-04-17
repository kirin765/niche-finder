#!/usr/bin/env bash
set -euo pipefail

src_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/deploy/desktop"
dest_dir="${XDG_DATA_HOME:-$HOME/.local/share}/applications"

mkdir -p "$dest_dir"
cp "$src_dir"/micro-niche-finder-toggle-auto-suspend.desktop "$dest_dir"/
cp "$src_dir"/micro-niche-finder-disable-auto-suspend.desktop "$dest_dir"/
cp "$src_dir"/micro-niche-finder-enable-auto-suspend.desktop "$dest_dir"/

if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database "$dest_dir" >/dev/null 2>&1 || true
fi

printf '%s\n' "Installed auto-suspend launchers into $dest_dir"
