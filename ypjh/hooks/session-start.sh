#!/usr/bin/env bash
set -uo pipefail

echo "=== [session-start] 加载项目记忆 ==="

CONTRACT="/workshop/ypjh/memory/exit-contract.md"
PROGRESS="/workshop/ypjh/memory/progress.md"
CORRECTIONS="/workshop/ypjh/memory/corrections.md"
MEMORY="/workshop/ypjh/memory/MEMORY.md"
PERSONAL="/workshop/ypjh/rules/personal.md"
DAILY_DIR="/workshop/ypjh/memory/daily"

# 注入 MEMORY.md（全量）
if [[ -s "$MEMORY" ]]; then
  echo ""
  echo "--- MEMORY ---"
  cat "$MEMORY"
  echo ""
fi

# 注入 rules/personal.md（全量）
if [[ -s "$PERSONAL" ]]; then
  echo ""
  echo "--- rules/personal ---"
  cat "$PERSONAL"
  echo ""
fi

# 注入 exit-contract
if [[ -s "$CONTRACT" ]]; then
  echo ""
  echo "--- exit-contract（上次交接）---"
  cat "$CONTRACT"
  echo ""
fi

# 注入 progress
if [[ -s "$PROGRESS" ]]; then
  echo ""
  echo "--- progress（当前进度）---"
  cat "$PROGRESS"
  echo ""
fi

# 注入最近 corrections（最多 10 条）
if [[ -s "$CORRECTIONS" ]]; then
  echo ""
  echo "--- corrections（最近 10 条纠正）---"
  tail -n 10 "$CORRECTIONS"
  echo ""
fi

# 智能提醒：检查未蒸馏的 daily 日志数
if [[ -d "$DAILY_DIR" ]]; then
  UNDISTILLED=$(grep -rL '<!--distilled' "$DAILY_DIR"/*.md 2>/dev/null | wc -l | xargs)
  UNDISTILLED=${UNDISTILLED:-0}
  if [[ "$UNDISTILLED" -ge 3 ]]; then
    echo ""
    echo "📋 你有 ${UNDISTILLED} 个未蒸馏的日志。本次会话结束前，建议运行 /distill-memory 整理记忆。"
  fi
fi

# 智能提醒：检查积压纠正数
if [[ -s "$CORRECTIONS" ]]; then
  CORR_COUNT=$(wc -l < "$CORRECTIONS" | xargs)
  if [[ "$CORR_COUNT" -gt 10 ]]; then
    echo ""
    echo "⚡ 有 ${CORR_COUNT} 条积压纠正。建议运行 /evolve-memory 检查是否有复发模式可提案为规则。"
  fi
fi

echo ""
echo "=== [session-start] 记忆加载完毕。请从 exit-contract 中的下一个会话入口继续。==="
