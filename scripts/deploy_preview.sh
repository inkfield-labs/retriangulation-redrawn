#!/usr/bin/env bash
# Deploy site/ to the private Cloudflare Pages preview (free tier). The 103 MB lines.pmtiles exceeds Pages' 25 MiB
# per-file limit, so it is served from the R2 bucket's r2.dev URL and the deploy copy of app.js points there.
# The deploy folder also gets robots.txt and an X-Robots-Tag header so the preview stays out of search engines.
# This script never touches R2 except one HEAD request. The CORS allowlist (scripts/r2_cors.json) names the production
# pages.dev host and localhost:8766 only, so branch-preview hostnames (<hash>.pages.dev) cannot load the tiles.
#
# One-time bucket setup (free tier: Standard class only, exactly one object). Upload once; re-upload only when
# lines.pmtiles changes. Never loop uploads or list calls.
#   npx wrangler r2 bucket create retriangulation-redrawn-tiles --location weur --storage-class Standard
#   npx wrangler r2 bucket dev-url enable retriangulation-redrawn-tiles
#   npx wrangler r2 bucket cors set retriangulation-redrawn-tiles --file scripts/r2_cors.json
#   npx wrangler r2 object put retriangulation-redrawn-tiles/lines.pmtiles --file site/data/lines.pmtiles --remote \
#     --content-type application/octet-stream --storage-class Standard
# Pages project (once): npx wrangler pages project create retriangulation-redrawn --production-branch main
#
# Usage:  scripts/deploy_preview.sh           (needs: npx wrangler logged in; site/data built by scripts/build_site.py)
# Writes: nothing in the repo; builds a temporary folder under .wrangler/ and deploys it
set -euo pipefail
cd "$(dirname "$0")/.."

PROJECT=retriangulation-redrawn
BUCKET=retriangulation-redrawn-tiles
R2_URL=$(npx wrangler r2 bucket dev-url get "$BUCKET" | grep -o 'https://[^'"'"' ]*r2\.dev')

# the tiles must be there before the page that points at them goes live
[ "$(curl -s -o /dev/null -I -w '%{http_code}' "$R2_URL/lines.pmtiles")" = 200 ] \
  || { echo "no 200 from $R2_URL/lines.pmtiles: upload the tiles first (see header)" >&2; exit 1; }

mkdir -p .wrangler
OUT=$(mktemp -d .wrangler/deploy.XXXXXX)
trap 'rm -rf "$OUT"' EXIT
cp -r site/. "$OUT"
rm "$OUT/data/lines.pmtiles"

# point the tiles at R2 (the one TILES line in app.js) and fail loudly if the line was not found
sed -i "s|^const TILES = .*|const TILES = \"$R2_URL/lines.pmtiles\";|" "$OUT/app.js"
grep -q "^const TILES = \"$R2_URL/lines.pmtiles\";\$" "$OUT/app.js"

printf '/*\n  X-Robots-Tag: noindex\n' > "$OUT/_headers"
printf 'User-agent: *\nDisallow: /\n' > "$OUT/robots.txt"

npx wrangler pages deploy "$OUT" --project-name "$PROJECT" --branch main --commit-dirty=true
