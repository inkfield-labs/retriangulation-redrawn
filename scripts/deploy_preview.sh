#!/usr/bin/env bash
# Deploy site/ to the private Cloudflare Pages preview (free tier). The 103 MB lines.pmtiles exceeds Pages' 25 MiB
# per-file limit, so it is served from the R2 bucket's r2.dev URL and the deploy copy of app.js points there.
# The deploy folder also gets robots.txt and an X-Robots-Tag header so the preview stays out of search engines.
# The bucket is filled once by hand (wrangler r2 object put ... --remote); this script never uploads to R2.
#
# Usage:  scripts/deploy_preview.sh           (needs: npx wrangler logged in; site/data built by scripts/build_site.py)
# Writes: nothing in the repo; builds a temporary folder under .wrangler/ and deploys it
set -euo pipefail
cd "$(dirname "$0")/.."

PROJECT=retriangulation-redrawn
BUCKET=retriangulation-redrawn-tiles
R2_URL=$(npx wrangler r2 bucket dev-url get "$BUCKET" | grep -o 'https://[^'"'"' ]*r2\.dev')

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
