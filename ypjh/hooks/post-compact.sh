#!/usr/bin/env bash
# hooks/post-compact.sh
# 上下文压缩后触发：提醒 agent 更新 exit-contract，防止关键状态随压缩丢失
# 触发时机：PostCompact

MEMORY_DIR="$(dirname "$0")/../memory"

echo "=== [post-compact] 上下文已压缩 ==="
echo ""
echo "请立即更新以下记忆文件，确保关键状态不丢失："
echo "  1. $MEMORY_DIR/progress.md — 更新已完成的 Lab"
echo "  2. $MEMORY_DIR/exit-contract.md — 更新"下一个会话入口"和"已尝试但失败的方案""
echo ""
echo "=== [post-compact] 记忆更新提醒完毕 ==="
