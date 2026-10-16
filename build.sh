#!/usr/bin/env bash
# Regenerate visa pages from brands.json, rebuild the site, and redeploy to GitHub Pages.
# Usage: /workspace/passport-site/build.sh        (add --no-deploy to only build)
set -euo pipefail
SITE="$(cd "$(dirname "$0")" && pwd)"; STAMPS="${STAMPS_DIR:-/workspace/stamps}"
(cd "$STAMPS" && python3 passport.py --pages --back)
python3 "$SITE/gen.py"
[[ "${1:-}" == "--no-deploy" ]] && { echo "built (not deployed): $SITE/index.html"; exit 0; }
cd "$SITE"; touch .nojekyll
git add -A
git commit -qm "Update passport $(date '+%Y-%m-%d %H:%M')" || echo "no changes to commit"
git push -q origin main
echo "deployed: https://jarroddellachiesa.github.io/tinned-fish-passport/ (live in ~1 min)"
