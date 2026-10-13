#!/usr/bin/env bash
# Vercel "Ignored Build Step": exit 0 SKIPS, exit 1 BUILDS.
# Once search fetches the newest audited JSON at runtime, snapshot-only
# commits no longer need a fresh server bundle. Fail open to building if the
# Git state is unavailable or ambiguous.
set -euo pipefail

if ! changed="$(git diff-tree --no-commit-id --name-only -r HEAD)"; then
  echo "Cannot inspect Git changes; build to be safe"
  exit 1
fi
if [[ -z "$changed" ]]; then
  echo "No reliable changed-file list; build to be safe"
  exit 1
fi

# Runtime JSON, collector-only Python tools and GitHub workflows do not
# affect the TanStack Start production bundle. Always build for src/,
# package/config, public assets outside the live JSON snapshot and other files.
if printf '%s\n' "$changed" | grep -Eqv '^(public/data/(campaigns|collection_status)\.json|docs/.*|scripts/.*|\.github/workflows/.*)$'; then
  echo "App/UI, asset or build config changed; build required"
  exit 1
fi

echo "Only data/collector/workflow/docs changed; live snapshot refreshes without rebuild"
exit 0
