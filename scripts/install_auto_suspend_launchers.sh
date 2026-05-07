#!/usr/bin/env bash
set -euo pipefail

src_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/deploy/desktop"
home_dir="${HOME:-}"
dest_home=""
dest_dir=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --home)
      dest_home="$2"
      shift 2
      ;;
    --dest-dir)
      dest_dir="$2"
      shift 2
      ;;
    *)
      printf '%s\n' "Unknown argument: $1" >&2
      exit 1
      ;;
  esac
done

if [[ -n "$dest_dir" ]]; then
  :
elif [[ -n "$dest_home" ]]; then
  dest_dir="$dest_home/.local/share/applications"
else
  dest_dir="${XDG_DATA_HOME:-${home_dir}/.local/share}/applications"
fi

mkdir -p "$dest_dir"
cp "$src_dir"/micro-niche-finder-toggle-auto-suspend.desktop "$dest_dir"/
cp "$src_dir"/micro-niche-finder-disable-auto-suspend.desktop "$dest_dir"/
cp "$src_dir"/micro-niche-finder-enable-auto-suspend.desktop "$dest_dir"/

if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database "$dest_dir" >/dev/null 2>&1 || true
fi

printf '%s\n' "Installed auto-suspend launchers into $dest_dir"
