#!/usr/bin/env bash
# Download competition data into data/.
#   ./scripts/download_data.sh                 # everything except snapshots (~0.9 GB)
#   ./scripts/download_data.sh fastapi_11194   # ...plus the named task snapshots
#   ./scripts/download_data.sh --all           # full 22 GB dataset as one zip
set -euo pipefail
COMP=gemma-4-developer-agent
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="$ROOT/data"
mkdir -p "$DEST"

if [[ "${1:-}" == "--all" ]]; then
  kaggle competitions download -c "$COMP" -p "$DEST"
  unzip -q -o "$DEST/$COMP.zip" -d "$DEST" && rm "$DEST/$COMP.zip"
  exit 0
fi

# The API caps pages at 200 files, so follow page tokens.
list="$DEST/_files.csv"
: > "$list"
tok=""
while :; do
  page=$(kaggle competitions files -c "$COMP" --csv --page-size 200 ${tok:+--page-token "$tok"})
  grep -vE '^(Next Page Token|name,size)' <<<"$page" >> "$list" || true
  tok=$(sed -n 's/^Next Page Token = //p' <<<"$page")
  [[ -z "$tok" ]] && break
done

fetch() {
  local f="$1" dir="$DEST/$(dirname "$1")"
  [[ -f "$DEST/$f" && ! -f "$DEST/$f.kaggle-partial" ]] && return
  mkdir -p "$dir"
  kaggle competitions download -c "$COMP" -f "$f" -p "$dir" -q
  # single-file downloads may arrive zipped
  local z="$dir/$(basename "$f").zip"
  if [[ -f "$z" ]]; then unzip -q -o "$z" -d "$dir" && rm "$z"; fi
}

export -f fetch; export COMP DEST
{ cut -d, -f1 "$list" | grep -v '^snapshots/'; for id in "$@"; do echo "snapshots/$id.tgz"; done; } \
  | xargs -P 8 -I{} bash -c 'fetch "$1"' _ {}
echo "Done: $(du -sh "$DEST" | cut -f1) in $DEST"
