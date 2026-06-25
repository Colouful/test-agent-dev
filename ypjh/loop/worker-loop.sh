#!/usr/bin/env bash
# loop/worker-loop.sh — Worker Loop（熔断 + 记忆 + 2-Strike）
#
# 退出码：
#   0 = 验证通过（修好了）
#   1 = 达到最大轮数或 3-strike，未收敛
#   2 = 时间超限
#   3 = 环境错误（verify.sh 本身坏了）
#
# 用法：
#   bash loop/worker-loop.sh
#   MAX_ITER=3 MAX_SECONDS=120 bash loop/worker-loop.sh
set -uo pipefail

# ── 配置 ──────────────────────────────────────────────────────────────────────

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

MAX_ITER="${MAX_ITER:-5}"
MAX_SECONDS="${MAX_SECONDS:-300}"
CONSEC_FAIL_LIMIT="${CONSEC_FAIL_LIMIT:-3}"
TASK="${TASK:-修复识别功能的 bug，使 ci/verify.sh 通过}"
STATE_FILE="loop/STATE.md"
VERIFY_CMD="bash ci/verify.sh"

START_TIME=$(date +%s)

# ── 初始化 ────────────────────────────────────────────────────────────────────

echo "═══════════════════════════════════════════════════════"
echo "  Worker Loop 启动"
echo "  MAX_ITER=$MAX_ITER  MAX_SECONDS=${MAX_SECONDS}s  CONSEC_FAIL=$CONSEC_FAIL_LIMIT"
echo "═══════════════════════════════════════════════════════"
echo ""

# 清空 STATE.md
: > "$STATE_FILE"

# 环境检查：verify.sh 存在且基本可用
if [ ! -x "ci/verify.sh" ]; then
  echo "LOOP_EXIT code=3 reason=verify.sh_not_found elapsed=0s rounds=0"
  exit 3
fi

# ── 辅助函数 ──────────────────────────────────────────────────────────────────

elapsed_seconds() {
  echo $(( $(date +%s) - START_TIME ))
}

extract_fail_stage() {
  # 从 verify 输出中提取失败阶段关键词
  echo "$1" | grep -o "第 [0-9] 层" | tail -1 || echo "unknown"
}

# ── 主循环 ────────────────────────────────────────────────────────────────────

CONSEC_FAILS=0
LAST_STAGE=""
PREV_STAGE=""
STRIKE_COUNT=0

for (( i=1; i<=MAX_ITER; i++ )); do
  echo "── 第 ${i}/${MAX_ITER} 轮 ──────────────────────────────────"
  echo ""

  # 1. 时间检查
  ELAPSED=$(elapsed_seconds)
  if [ "$ELAPSED" -ge "$MAX_SECONDS" ]; then
    echo ""
    echo "⏱ 时间超限（${ELAPSED}s >= ${MAX_SECONDS}s）"
    echo ""
    echo "LOOP_EXIT code=2 reason=timeout elapsed=${ELAPSED}s rounds=$((i-1))"
    exit 2
  fi

  # 2. 构建上下文
  CONTEXT="任务：$TASK

项目根目录：$PROJECT_ROOT
验证命令：$VERIFY_CMD
当前是第 ${i} 轮尝试（共 $MAX_ITER 轮上限）。
"

  # 追加历史教训
  if [ -s "$STATE_FILE" ]; then
    CONTEXT="${CONTEXT}
── 历史记录（前几轮的失败教训）──
$(cat "$STATE_FILE")
── 历史结束 ──

请根据上面的失败记录避开已尝试的方向。
"
  fi

  # 2-Strike 升级：连续两轮同阶段失败
  if [ "$STRIKE_COUNT" -ge 2 ]; then
    CONTEXT="${CONTEXT}
⚠️ 前两轮在同一个地方失败了（${LAST_STAGE}）。不要继续用类似方法修。
请先：1. 分析 root cause  2. 提出不同思路  3. 再动手修
"
  fi

  # 3. 调用 claude
  echo "  调用 Claude 修复..."
  AGENT_OUTPUT=$(claude -p "$CONTEXT" --dangerously-skip-permissions 2>&1 | tail -c 2000 || true)
  AGENT_SUMMARY=$(echo "$AGENT_OUTPUT" | head -c 80)

  # 4. 运行验证
  echo "  运行 ci/verify.sh..."
  VERIFY_OUTPUT=$($VERIFY_CMD 2>&1) && VERIFY_EXIT=0 || VERIFY_EXIT=$?

  # 5. 判定结果
  if [ "$VERIFY_EXIT" -eq 0 ]; then
    ELAPSED=$(elapsed_seconds)
    echo ""
    echo "$VERIFY_OUTPUT" | tail -5
    echo ""
    echo "═══════════════════════════════════════════════════════"
    echo "  ✓ 验证通过！"
    echo "═══════════════════════════════════════════════════════"
    echo ""
    echo "LOOP_EXIT code=0 reason=verify_pass elapsed=${ELAPSED}s rounds=$i"

    # 记录成功到 STATE.md
    {
      echo ""
      echo "## 第 ${i} 轮 ($(date +%H:%M:%S))"
      echo "**尝试方向：** ${AGENT_SUMMARY}"
      echo "**结果：** 通过 ✓"
      echo "---"
    } >> "$STATE_FILE"

    exit 0
  fi

  # 验证失败
  FAIL_LINE=$(echo "$VERIFY_OUTPUT" | grep -E "VERIFY_FAIL|FAIL:" | head -1 || echo "未知错误")
  CURRENT_STAGE=$(extract_fail_stage "$VERIFY_OUTPUT")

  echo "  ✗ 验证失败: $FAIL_LINE"

  # 6. 追加本轮记录到 STATE.md
  {
    echo ""
    echo "## 第 ${i} 轮 ($(date +%H:%M:%S))"
    echo "**尝试方向：** ${AGENT_SUMMARY}"
    echo "**结果：** 失败"
    echo "**错误摘要：** ${FAIL_LINE}"
    echo "---"
  } >> "$STATE_FILE"

  # 7. Strike 计算
  if [ "$CURRENT_STAGE" = "$LAST_STAGE" ] && [ -n "$LAST_STAGE" ]; then
    STRIKE_COUNT=$((STRIKE_COUNT + 1))
  else
    STRIKE_COUNT=1
  fi

  PREV_STAGE="$LAST_STAGE"
  LAST_STAGE="$CURRENT_STAGE"

  # 8. 3-Strike 熔断
  if [ "$STRIKE_COUNT" -ge "$CONSEC_FAIL_LIMIT" ]; then
    ELAPSED=$(elapsed_seconds)
    echo ""
    echo "═══════════════════════════════════════════════════════"
    echo "  ✗ 3-Strike 熔断：连续 ${STRIKE_COUNT} 轮在「${CURRENT_STAGE}」失败"
    echo "  需要人工介入"
    echo "═══════════════════════════════════════════════════════"
    echo ""
    echo "LOOP_EXIT code=1 reason=3-strike_${CURRENT_STAGE} elapsed=${ELAPSED}s rounds=$i"
    exit 1
  fi

  CONSEC_FAILS=$((CONSEC_FAILS + 1))
  echo ""
done

# ── 达到最大轮数 ──────────────────────────────────────────────────────────────

ELAPSED=$(elapsed_seconds)
echo ""
echo "═══════════════════════════════════════════════════════"
echo "  ✗ 达到最大轮数（$MAX_ITER），未收敛"
echo "═══════════════════════════════════════════════════════"
echo ""
echo "LOOP_EXIT code=1 reason=max_iter elapsed=${ELAPSED}s rounds=$MAX_ITER"
exit 1
