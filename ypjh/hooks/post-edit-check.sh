#!/usr/bin/env bash
# hooks/post-edit-check.sh
# 编辑 Python 文件后自动跑架构护栏
# 触发时机：PostToolUse(Edit) on *.py files

FILE="${1:-}"

if [[ "$FILE" == *.py ]]; then
  echo ">>> [hook] 编辑了 Python 文件，运行架构护栏..."
  bash "$(dirname "$0")/../ci/arch-check.sh"
  STATUS=$?
  if [ $STATUS -eq 1 ]; then
    echo ">>> [hook] ARCH_FAIL — 请修复后重新提交"
    exit 1
  fi
fi
