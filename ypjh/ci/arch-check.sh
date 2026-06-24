#!/usr/bin/env bash
# ci/arch-check.sh — 架构护栏
# 检测 ARCH-1/2/3 违规（裸字符串/confidence_score 可 NULL/user_id 缺失）
# 用法: bash ci/arch-check.sh
# 退出码: 0=通过, 1=违规, 2=无源码(跳过)

set -uo pipefail

SRC_DIR="backend"
PASS=0
FAIL=1
SKIP=2

echo "=== 架构护栏检查 (ARCH-1/2/3) ==="

# 无 backend/ 目录时跳过
if [ ! -d "$SRC_DIR" ]; then
  echo "ARCH_SKIP: 未找到 $SRC_DIR 目录，跳过检查（业务代码未创建）"
  exit $SKIP
fi

VIOLATIONS=0
VIOLATION_FILES=""

# ── ARCH-1: 禁止裸字符串存储题目 ────────────────────────────────────────

# 模式 1: raw_text / raw_content 字段赋值（直接裸字符串存储）
while IFS= read -r -d '' file; do
  if grep -nE 'raw_text\s*=|raw_content\s*=|\.raw_text\b|\.raw_content\b' "$file" 2>/dev/null | grep -v '^\s*#' | grep -q .; then
    echo "ARCH_FAIL [ARCH-1]: $file — 发现 raw_text/raw_content 字段（禁止裸字符串存储）"
    VIOLATIONS=$((VIOLATIONS + 1))
    VIOLATION_FILES="$VIOLATION_FILES $file"
  fi
done < <(find "$SRC_DIR" -name "*.py" -not -path "*/tests/*" -print0)

# 模式 2: Question 对象构造时只有 content 没有 correct_answer（不完整的结构化存储）
while IFS= read -r -d '' file; do
  if grep -nP 'Question\([^)]*content\s*=[^)]+\)' "$file" 2>/dev/null | grep -qv 'correct_answer' 2>/dev/null || true; then
    match=$(grep -nP 'Question\([^)]*content\s*=[^)]+\)' "$file" 2>/dev/null | grep -v 'correct_answer' 2>/dev/null || true)
    if [ -n "$match" ]; then
      echo "ARCH_FAIL [ARCH-1]: $file — Question() 构造缺少 correct_answer 字段（结构不完整）"
      echo "  $match"
      VIOLATIONS=$((VIOLATIONS + 1))
      VIOLATION_FILES="$VIOLATION_FILES $file"
    fi
  fi
done < <(find "$SRC_DIR" -name "*.py" -not -path "*/tests/*" -print0)

# 模式 3: 直接把 Bedrock 原始返回写入 content（绕过 check_question_schema）
while IFS= read -r -d '' file; do
  match=$(grep -nE 'content\s*=\s*(result|response|raw)\b' "$file" 2>/dev/null || true)
  if [ -n "$match" ]; then
    echo "ARCH_FAIL [ARCH-1]: $file — 疑似将 Bedrock 原始返回直接赋值给 content（绕过 schema 校验）"
    echo "  $match"
    VIOLATIONS=$((VIOLATIONS + 1))
    VIOLATION_FILES="$VIOLATION_FILES $file"
  fi
done < <(find "$SRC_DIR" -name "*.py" -not -path "*/tests/*" -print0)

# ── ARCH-2: confidence_score 不得为 NULL ──────────────────────────────────

# 模式 4: confidence_score 字段定义为 Optional（允许 NULL）
while IFS= read -r -d '' file; do
  match=$(grep -nE 'confidence_score\s*:\s*float\s*\|\s*None|confidence_score\s*=\s*Column.*nullable\s*=\s*True' "$file" 2>/dev/null || true)
  if [ -n "$match" ]; then
    echo "ARCH_FAIL [ARCH-2]: $file — confidence_score 允许 NULL（禁止，识别置信度是不可回溯元数据）"
    echo "  $match"
    VIOLATIONS=$((VIOLATIONS + 1))
    VIOLATION_FILES="$VIOLATION_FILES $file"
  fi
done < <(find "$SRC_DIR" -name "*.py" -not -path "*/tests/*" -print0)

# ── ARCH-3: 所有 Repository 查询必须带 user_id 过滤 ──────────────────────

# 模式 5: repositories/ 下的 async def 查询函数缺少 user_id 参数
if [ -d "$SRC_DIR/repositories" ]; then
  while IFS= read -r -d '' file; do
    # 找所有 async def 函数，检查其中 select/query/filter 行是否缺 user_id
    while IFS= read -r func_line; do
      func_name=$(echo "$func_line" | grep -oP '(?<=async def )\w+' || true)
      # 跳过 __init__ 和无 DB 操作的函数
      if [[ "$func_name" == "__init__" ]] || [[ -z "$func_name" ]]; then
        continue
      fi
      # 检查该函数签名是否有 user_id 参数
      if ! grep -A 5 "async def $func_name" "$file" 2>/dev/null | grep -q 'user_id'; then
        # 检查函数体是否有 select/where/filter 数据库操作（说明是查询函数）
        if grep -A 20 "async def $func_name" "$file" 2>/dev/null | grep -qE 'select\(|\.where\(|\.filter\(|scalars\(\)'; then
          echo "ARCH_FAIL [ARCH-3]: $file — 函数 ${func_name}() 有 DB 查询但缺少 user_id 参数（R1 违规）"
          VIOLATIONS=$((VIOLATIONS + 1))
          VIOLATION_FILES="$VIOLATION_FILES $file"
        fi
      fi
    done < <(grep -n 'async def ' "$file" 2>/dev/null || true)
  done < <(find "$SRC_DIR/repositories" -name "*.py" -not -path "*/tests/*" -print0 2>/dev/null)
fi

# ── 结果汇总 ───────────────────────────────────────────────────────────────

echo ""
if [ "$VIOLATIONS" -eq 0 ]; then
  echo "ARCH_OK: 未发现架构违规 ✓（ARCH-1/2/3 全部通过）"
  exit $PASS
else
  echo "ARCH_FAIL: 发现 $VIOLATIONS 处违规，违规文件:$VIOLATION_FILES"
  echo ""
  echo "修复指引："
  echo "  ARCH-1: 将 raw_text/raw_content 替换为结构化字段（content, correct_answer, wrong_answer）"
  echo "          先调用 mcp/check_question_schema.py 校验识别结果，再构造 Question 对象"
  echo "          参考 rules/architecture.md ARCH-1 和 rules/personal.md R3"
  echo "  ARCH-2: confidence_score 字段改为 float（非 Optional），默认值用 0.0"
  echo "          参考 rules/architecture.md ARCH-2 和 rules/personal.md R2"
  echo "  ARCH-3: Repository 查询函数必须接收 user_id: str 参数并用于 WHERE 过滤"
  echo "          参考 rules/architecture.md ARCH-3 和 rules/personal.md R1"
  exit $FAIL
fi
