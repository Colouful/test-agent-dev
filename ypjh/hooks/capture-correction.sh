#!/usr/bin/env bash
set -uo pipefail

CORRECTIONS="/workshop/ypjh/memory/corrections.md"

# 从 stdin 读取 JSON（Claude Code UserPromptSubmit 传入）
INPUT=$(cat 2>/dev/null || true)

# 无内容则静默退出
if [[ -z "$INPUT" ]]; then
  exit 0
fi

# 提取用户消息文本：尝试 jq 解析 JSON，失败则用原文
MSG=""
if command -v jq &>/dev/null; then
  MSG=$(echo "$INPUT" | jq -r '.input.content // .input // empty' 2>/dev/null || true)
fi
if [[ -z "$MSG" ]]; then
  MSG="$INPUT"
fi

# 匹配纠正信号词（中文 + 英文）
if echo "$MSG" | grep -qiE '不对|应该是|错了|别这么|搞反|不是这样|wrong|should be|don'\''t|stop|revert|不要这样|改回来'; then
  TIMESTAMP=$(date "+%Y-%m-%d %H:%M")
  SNIPPET=$(echo "$MSG" | head -c 120)
  echo "- [${TIMESTAMP}] ${SNIPPET}" >> "$CORRECTIONS"
fi

exit 0
