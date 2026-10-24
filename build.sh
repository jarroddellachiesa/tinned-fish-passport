#!/usr/bin/env bash
# Regenerate visa pages from brands.json, rebuild the site, back up the source into the repo, and redeploy.
# Usage: /workspace/passport-site/build.sh                 render all pages + back cover, build, deploy
#        /workspace/passport-site/build.sh --page=KEY      render only that brand's page (others untouched)
#        /workspace/passport-site/build.sh --no-render     reuse existing PNGs
#        add --no-deploy to any of the above to build without pushing
# Restore after a box reset:  git clone https://github.com/jarroddellachiesa/tinned-fish-passport /workspace/passport-site
#                             && cp -r /workspace/passport-site/src/stamps /workspace/stamps
# NOTE: never delete CNAME (custom domain tinnedfishpassport.dellachiesa.us); icons are made by icons/make_icons.py.
set -euo pipefail
[[ -f "$(dirname "$0")/CNAME" ]] || { echo "CNAME missing - refusing to deploy"; exit 1; }
SITE="$(cd "$(dirname "$0")" && pwd)"; STAMPS="${STAMPS_DIR:-/workspace/stamps}"
RENDER=(--pages --back); DEPLOY=1
for a in "$@"; do case "$a" in
  --page=*) RENDER=("$a");; --no-render) RENDER=();; --no-deploy) DEPLOY=0;;
  *) echo "unknown option $a"; exit 2;; esac; done
[[ ${#RENDER[@]} -gt 0 ]] && (cd "$STAMPS" && python3 passport.py "${RENDER[@]}")
python3 "$SITE/gen.py"
# back up the renderer source + data + logos + rendered PNGs into the repo
mkdir -p "$SITE/src/stamps/logos"
cp "$STAMPS"/{passport.py,brands.json,logos.json} "$STAMPS"/passport_*.png "$SITE/src/stamps/"
find "$STAMPS/logos" -maxdepth 1 -type f \( -name '*.svg' -o -name '*.png' \) -exec cp {} "$SITE/src/stamps/logos/" \;
[[ $DEPLOY == 1 ]] || { echo "built (not deployed): $SITE/index.html"; exit 0; }
cd "$SITE"; touch .nojekyll
git add -A
git commit -qm "Update passport $(date '+%Y-%m-%d %H:%M')" || echo "no changes to commit"
git push -q origin main
echo "deployed: https://tinnedfishpassport.dellachiesa.us/ (live in ~1 min)"
