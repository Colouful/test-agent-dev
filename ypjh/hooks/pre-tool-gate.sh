#!/usr/bin/env bash
set -uo pipefail

# PreToolUse hook: 机械拦截不可逆操作
# exit 0 = 放行, exit 2 = BLOCK（Claude Code 原生语义）

INPUT=$(cat 2>/dev/null || true)

if [[ -z "$INPUT" ]]; then
  exit 0
fi

# 提取命令内容
CMD=""
if command -v jq &>/dev/null; then
  CMD=$(echo "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null || true)
fi
if [[ -z "$CMD" ]]; then
  CMD="$INPUT"
fi

# 拦截规则：匹配危险操作
if echo "$CMD" | grep -qE 'git\s+push|git\s+push\s'; then
  echo "⚠️ BLOCKED: git push 需要人工确认"
  exit 2
fi

if echo "$CMD" | grep -qE '\brm\s+-[rRf]|\brm\s+--force|\bunlink\s'; then
  echo "⚠️ BLOCKED: 删除操作需要人工确认"
  exit 2
fi

if echo "$CMD" | grep -qE 'aws\s+(s3\s+rm|dynamodb\s+delete|dynamodb\s+put)'; then
  echo "⚠️ BLOCKED: AWS 写入操作需要人工确认"
  exit 2
fi

# 放行
exit 0
