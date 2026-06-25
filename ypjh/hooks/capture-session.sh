#!/usr/bin/env bash
set -uo pipefail

DAILY_FILE="/workshop/ypjh/memory/daily/$(date +%Y-%m-%d).md"
TIMESTAMP=$(date +%H:%M)

FILES=$(git -C /workshop/ypjh diff --name-only HEAD~1 2>/dev/null | tr '\n' ', ' | sed 's/,$//' || true)
COMMITS=$(git -C /workshop/ypjh log --oneline -3 --no-decorate 2>/dev/null || true)

{
  echo ""
  echo "## ${TIMESTAMP} | session"
  echo "**改动文件：** ${FILES:-无}"
  echo "**Git：** ${COMMITS:-无近期提交}"
  echo ""
} >> "$DAILY_FILE" || true
