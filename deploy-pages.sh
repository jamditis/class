#!/usr/bin/env bash
# Deploy class Jekyll site to Cloudflare Pages (personal account)
# Builds Jekyll locally, then uploads _site/
set -euo pipefail
cd "$(dirname "$0")/docs"

export CLOUDFLARE_API_TOKEN=$(pass show claude/api/cloudflare-full)
export CLOUDFLARE_ACCOUNT_ID="3d4b1d36109e30866bb7516502224b2c"

echo "Building Jekyll site..."
# Override baseurl for Cloudflare Pages (site is at root, not /class/)
JEKYLL_ARGS="--baseurl \"\""
if command -v bundle &>/dev/null; then
  bundle exec jekyll build $JEKYLL_ARGS
elif command -v jekyll &>/dev/null; then
  jekyll build $JEKYLL_ARGS
else
  echo "Error: Jekyll not installed. Install with: gem install jekyll bundler"
  exit 1
fi

COMMIT_MSG=$(git -C .. log -1 --format="%h %s" 2>/dev/null || echo "manual deploy")
echo "Deploying class site..."
echo "Commit: $COMMIT_MSG"

# Clear wrangler account cache (prevents cross-account contamination)
rm -f "$HOME/node_modules/.cache/wrangler/wrangler-account.json" "$HOME/node_modules/.cache/wrangler/pages.json" 2>/dev/null

npx wrangler pages deploy _site \
  --project-name=class-site \
  --branch=main \
  --commit-message="$COMMIT_MSG" --commit-dirty=true

echo "Done: https://class-site-16m.pages.dev"
