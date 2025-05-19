#!/bin/bash

REPO="lantzbuilds/hevy_ai_trainer"  # 🔁 Replace with your repo
TOKEN="${GH_TOKEN}"

if [[ -z "$TOKEN" ]]; then
  echo "❌ GitHub token not set. Use: export GH_TOKEN=your_token"
  exit 1
fi

cat issues.json | jq -c '.[]' | while read -r issue; do
  title=$(echo "$issue" | jq -r '.title')
  body=$(echo "$issue" | jq -r '.body')
  labels=$(echo "$issue" | jq -c '.labels')

  echo "📦 Creating issue: $title"

  curl -s -X POST "https://api.github.com/repos/$REPO/issues" \
    -H "Authorization: token $TOKEN" \
    -H "Accept: application/vnd.github+json" \
    -d @- <<EOF
{
  "title": "$title",
  "body": "$body",
  "labels": $labels
}
EOF

  echo "✅ Done"
done