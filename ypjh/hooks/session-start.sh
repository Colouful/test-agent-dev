#!/usr/bin/env bash
# hooks/session-start.sh
# 会话启动时自动加载记忆，防止跨会话状态丢失
# 触发时机：SessionStart（在 .claude/settings.local.json 中配置）

MEMORY_DIR="$(dirname "$0")/../memory"

echo "=== [session-start] 加载项目记忆 ==="
echo ""

if [ -f "$MEMORY_DIR/exit-contract.md" ]; then
  echo "--- exit-contract（上次交接）---"
  cat "$MEMORY_DIR/exit-contract.md"
  echo ""
fi

if [ -f "$MEMORY_DIR/progress.md" ]; then
  echo "--- progress（当前进度）---"
  cat "$MEMORY_DIR/progress.md"
  echo ""
fi

echo "=== [session-start] 记忆加载完毕。请从 exit-contract 中的"下一个会话入口"继续。==="
