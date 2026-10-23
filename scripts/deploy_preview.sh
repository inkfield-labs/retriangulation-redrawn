#!/usr/bin/env bash
# Deploy site/ to Cloudflare Pages (free tier). Everything, the line tiles included, is a static
# file on Pages: no request metering, but at most 20,000 files and 25 MiB per file, which this script checks.
# Production (branch main) is public and indexable. Other branches also get robots.txt and an X-Robots-Tag header;
# Pages itself adds noindex to preview and branch URLs.
# (Until #18 the tiles were one pmtiles file on R2; the bucket retriangulation-redrawn-tiles is no longer read.)
#
# Pages project (once): npx wrangler pages project create retriangulation-redrawn --production-branch main
#
# Usage:  scripts/deploy_preview.sh           (needs: npx wrangler logged in; site/data built by scripts/build_site.py)
# Writes: results/number_audit.md (the number audit runs first; a failed claim stops the deploy); builds a temporary
#         folder under .wrangler/ and deploys it
set -euo pipefail
cd "$(dirname "$0")/.."

# every number on the page must trace to a saved output before it goes live
.venv/bin/python -I scripts/audit_numbers.py > /dev/null \
  || { echo "number audit failed: see results/number_audit.md; fix the page or rebuild before deploying" >&2; exit 1; }

PROJECT=retriangulation-redrawn

mkdir -p .wrangler
OUT=$(mktemp -d .wrangler/deploy.XXXXXX)
trap 'rm -rf "$OUT"' EXIT
cp -r site/. "$OUT"
rm -f "$OUT/data/lines.pmtiles"  # left over from builds before #18

# Pages labels .pbf as application/octet-stream, which Cloudflare does not compress; as protobuf it is compressed
printf '/data/tiles/*\n  Content-Type: application/x-protobuf\n' > "$OUT/_headers"
if [ "${BRANCH:-main}" != main ]; then
  printf '/*\n  X-Robots-Tag: noindex\n' >> "$OUT/_headers"
  printf 'User-agent: *\nDisallow: /\n' > "$OUT/robots.txt"
fi

# Pages' free-plan limits; a deploy past them fails part-way, so stop here instead
files=$(find "$OUT" -type f | wc -l)
[ "$files" -le 20000 ] || { echo "$files files: over Pages' 20,000-file limit" >&2; exit 1; }
big=$(find "$OUT" -type f -size +25M | head -1)
[ -z "$big" ] || { echo "$big is over Pages' 25 MiB file limit" >&2; exit 1; }

npx wrangler pages deploy "$OUT" --project-name "$PROJECT" --branch "${BRANCH:-main}" --commit-dirty=true
