#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DRY_RUN=false

if [[ "${1:-}" == "--dry-run" ]]; then
  DRY_RUN=true
fi

targets=(
  ".agents"
  ".claude"
  ".github"
  ".gitnexus"
  ".superpowers"
  ".trae"
  ".worktrees"
)

for target in "${targets[@]}"; do
  path="${ROOT}/${target}"
  [[ -e "$path" ]] || continue

  if [[ "$DRY_RUN" == true ]]; then
    printf 'Would remove %s\n' "$target"
  else
    rm -rf -- "$path"
    printf 'Removed %s\n' "$target"
  fi
done
