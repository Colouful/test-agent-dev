#!/usr/bin/env bash
# loop/worker-loop.sh — 错题本 Worker Loop（含三道熔断）
#
# 用途：在 CI / 自动化场景中反复执行验证，直到通过或触发熔断。
#
# 熔断条件（任意一个触发即停止）：
#   1. MAX_ITER  — 达到最大迭代次数（默认 10）
#   2. MAX_MIN   — 超过最大运行时间（默认 30 分钟）
#   3. CONSEC_FAIL — 连续失败次数（默认 3 次）→ 人类兜底
#
# 使用方式：
#   bash loop/worker-loop.sh                    # 运行完整验证（verify.sh + arch-check.sh）
#   MAX_ITER=3 bash loop/worker-loop.sh         # 自定义最大次数
#   TASK="bash ci/arch-check.sh" bash loop/worker-loop.sh  # 自定义任务
#
# 退出码：0=任务通过，1=熔断触发，2=环境错误

set -euo pipefail

# ── 配置 ──────────────────────────────────────────────────────────────────────

MAX_ITER="${MAX_ITER:-10}"
MAX_MIN="${MAX_MIN:-30}"
CONSEC_FAIL_LIMIT="${CONSEC_FAIL_LIMIT:-3}"
TASK="${TASK:-bash ci/verify.sh && bash ci/arch-check.sh}"
STATE_FILE="$(dirname "$0")/STATE.md"
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# ── 初始化 ────────────────────────────────────────────────────────────────────

ITER=0
CONSEC_FAIL=0
START_TS=$(date +%s)
START_TIME=$(date '+%Y-%m-%d %H:%M:%S')
LOOP_STATUS="running"

_elapsed_min() {
  echo $(( ($(date +%s) - START_TS) / 60 ))
}

_update_state() {
  local status="$1" iter="$2" last_result="$3" last_error="${4:-}"
  cat > "$STATE_FILE" <<EOF
# Worker Loop 状态记忆

## 当前状态

\`\`\`
LOOP_STATUS: $status
CURRENT_ITER: $iter
MAX_ITER: $MAX_ITER
START_TIME: $START_TIME
LAST_ERROR: ${last_error:-（无）}
LAST_RESULT: $last_result
\`\`\`

## 迭代历史

（详见本次运行的终端输出）

## 熔断记录

$([ "$status" = "breaker_triggered" ] && echo "⚠️ 熔断于第 $iter 轮，原因：$last_error" || echo "（无熔断历史）")

---
> 此文件由 \`loop/worker-loop.sh\` 自动更新。手动修改时注意保持格式。
EOF
}

# ── 人类兜底函数 ──────────────────────────────────────────────────────────────

_human_fallback() {
  local reason="$1"
  echo ""
  echo "=================================================="
  echo "  ⚠️  需要人类介入"
  echo "=================================================="
  echo ""
  echo "  熔断原因：$reason"
  echo ""
  echo "  建议排查步骤："
  echo "  1. 查看上方输出，找到最后一次失败的具体错误信息"
  echo "  2. 检查 loop/STATE.md 了解本次运行状态"
  echo "  3. 修复问题后重新运行: bash loop/worker-loop.sh"
  echo ""
  echo "  如需只跑验证（不循环）："
  echo "    bash ci/verify.sh        # 识别功能验证"
  echo "    bash ci/arch-check.sh    # 架构护栏"
  echo "    python3 ddd/score_health.py  # DDD 健康分"
  echo ""
  echo "  STATE 已写入: loop/STATE.md"
  echo "=================================================="
}

# ── 主循环 ────────────────────────────────────────────────────────────────────

cd "$PROJECT_ROOT"

echo "=================================================="
echo "  Worker Loop 启动"
echo "  MAX_ITER=$MAX_ITER  MAX_MIN=$MAX_MIN  CONSEC_FAIL_LIMIT=$CONSEC_FAIL_LIMIT"
echo "  TASK: $TASK"
echo "  START: $START_TIME"
echo "=================================================="
echo ""

_update_state "running" 0 "（尚未运行）"

while true; do
  ITER=$((ITER + 1))
  ELAPSED=$(_elapsed_min)

  echo "──────────────────────────────────────────────────"
  echo "  迭代 #$ITER / $MAX_ITER  |  已运行 ${ELAPSED}min / ${MAX_MIN}min"
  echo "──────────────────────────────────────────────────"

  # 熔断 1：超过最大迭代次数
  if [ "$ITER" -gt "$MAX_ITER" ]; then
    REASON="达到最大迭代次数 $MAX_ITER"
    echo ""
    echo "🔴 熔断触发：$REASON"
    _update_state "breaker_triggered" "$ITER" "迭代上限" "$REASON"
    _human_fallback "$REASON"
    exit 1
  fi

  # 熔断 2：超过最大时间
  if [ "$ELAPSED" -ge "$MAX_MIN" ]; then
    REASON="运行时间超过 ${MAX_MIN} 分钟"
    echo ""
    echo "🔴 熔断触发：$REASON"
    _update_state "breaker_triggered" "$ITER" "时间超限" "$REASON"
    _human_fallback "$REASON"
    exit 1
  fi

  # 执行任务
  if bash -c "$TASK" 2>&1; then
    echo ""
    echo "✅ 迭代 #$ITER 通过"
    CONSEC_FAIL=0
    _update_state "pass" "$ITER" "PASS"
    echo ""
    echo "=================================================="
    echo "  LOOP_OK — 任务在第 $ITER 轮通过 ✓"
    echo "=================================================="
    exit 0
  else
    CONSEC_FAIL=$((CONSEC_FAIL + 1))
    echo ""
    echo "❌ 迭代 #$ITER 失败（连续失败: $CONSEC_FAIL / $CONSEC_FAIL_LIMIT）"
    _update_state "running" "$ITER" "FAIL" "连续失败 $CONSEC_FAIL 次"

    # 熔断 3：连续失败过多
    if [ "$CONSEC_FAIL" -ge "$CONSEC_FAIL_LIMIT" ]; then
      REASON="连续失败 $CONSEC_FAIL 次，超过阈值 $CONSEC_FAIL_LIMIT"
      echo ""
      echo "🔴 熔断触发：$REASON"
      _update_state "breaker_triggered" "$ITER" "FAIL" "$REASON"
      _human_fallback "$REASON"
      exit 1
    fi

    echo "  等待 5 秒后重试..."
    sleep 5
  fi
done
