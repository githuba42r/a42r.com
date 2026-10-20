#!/usr/bin/env bash
# Build the site and mirror website/ to the web root on oracle-cloud.
# Usage: scripts/deploy-website.sh [--dry-run]
set -euo pipefail

dry=()
case "${1:-}" in
  "") ;;
  --dry-run) dry=(-n) ;;
  *) echo "usage: $0 [--dry-run]" >&2; exit 2 ;;
esac

cd "$(dirname "${BASH_SOURCE[0]}")/.."

if [ -x .venv/bin/python ]; then py=.venv/bin/python; else py=python3; fi
"$py" -m a42r_site.build

# --delete keeps the server an exact mirror; .a42r-build is local-only.
rsync -rlvz --delete --exclude=.a42r-build --chmod=D755,F644 ${dry[@]+"${dry[@]}"} \
  website/ oracle-cloud:/opt/apps/a42r/website/
