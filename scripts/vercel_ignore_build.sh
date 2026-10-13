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

# Only verified data snapshots and documentation may skip a deployment.
# Any source code, workflow, frontend, config or package change MUST build.
if printf '%s\n' "$changed" | grep -Eqv '^(public/data/(campaigns|collection_status)\.json|docs/.*)$'; then
  echo "Application or automation files changed; build required"
  exit 1
fi

echo "Only verified snapshot/docs changed; runtime fetch refreshes without rebuild"
exit 0
