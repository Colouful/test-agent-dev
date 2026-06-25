#!/usr/bin/env bash
# ci/test-memory-pipeline.sh — 记忆 Pipeline 完整性测试
# 验证所有文件存在、hooks 可运行、闭环完整
set -uo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

FAILURES=0
PASS=0

assert_file_exists() {
  if [[ -f "$1" ]]; then
    echo "  ✓ $1"
    PASS=$((PASS + 1))
  else
    echo "  ✗ MISSING: $1"
    FAILURES=$((FAILURES + 1))
  fi
}

assert_dir_exists() {
  if [[ -d "$1" ]]; then
    echo "  ✓ $1/"
    PASS=$((PASS + 1))
  else
    echo "  ✗ MISSING DIR: $1/"
    FAILURES=$((FAILURES + 1))
  fi
}

assert_executable() {
  if [[ -x "$1" ]]; then
    echo "  ✓ $1 (executable)"
    PASS=$((PASS + 1))
  else
    echo "  ✗ NOT EXECUTABLE: $1"
    FAILURES=$((FAILURES + 1))
  fi
}

assert_file_contains() {
  local file="$1" pattern="$2" desc="$3"
  if grep -q "$pattern" "$file" 2>/dev/null; then
    echo "  ✓ $file contains '$desc'"
    PASS=$((PASS + 1))
  else
    echo "  ✗ $file missing '$desc'"
    FAILURES=$((FAILURES + 1))
  fi
}

assert_hook_runs() {
  local script="$1" desc="$2"
  if bash "$script" </dev/null >/dev/null 2>&1; then
    echo "  ✓ $desc runs without error"
    PASS=$((PASS + 1))
  else
    echo "  ✗ $desc fails (exit $?)"
    FAILURES=$((FAILURES + 1))
  fi
}

# ── 1. 核心文件存在性 ─────────────────────────────────────────────────────

echo "── 1. 核心文件存在性"

assert_file_exists "memory/MEMORY.md"
assert_file_exists "memory/corrections.md"
assert_file_exists "memory/exit-contract.template.md"
assert_file_exists "memory/progress.md"
assert_file_exists "memory/exit-contract.md"
assert_file_exists "memory/archive.md"
assert_file_exists "rules/proposed.md"
assert_file_exists "rules/personal.md"
assert_dir_exists "memory/daily"

echo ""

# ── 2. Hooks 存在+可执行+可运行 ───────────────────────────────────────────

echo "── 2. Hooks 完整性"

assert_executable "hooks/post-edit-check.sh"
assert_executable "hooks/session-start.sh"
assert_executable "hooks/post-compact.sh"
assert_executable "hooks/capture-correction.sh"
assert_executable "hooks/capture-session.sh"

assert_hook_runs "hooks/session-start.sh" "session-start"
assert_hook_runs "hooks/post-compact.sh" "post-compact"

echo ""

# ── 3. Settings 配置完整 ──────────────────────────────────────────────────

echo "── 3. Settings hooks 配置"

SETTINGS=".claude/settings.json"
assert_file_exists "$SETTINGS"
assert_file_contains "$SETTINGS" "SessionStart" "SessionStart hook"
assert_file_contains "$SETTINGS" "Stop" "Stop hook"
assert_file_contains "$SETTINGS" "UserPromptSubmit" "UserPromptSubmit hook"
assert_file_contains "$SETTINGS" "PostCompact" "PostCompact hook"
assert_file_contains "$SETTINGS" "PostToolUse" "PostToolUse hook"
assert_file_contains "$SETTINGS" "PreToolUse" "PreToolUse hook (git push gate)"

echo ""

# ── 4. Skills 完整 ────────────────────────────────────────────────────────

echo "── 4. Skills"

assert_file_exists "skills/distill-memory/SKILL.md"
assert_file_exists "skills/evolve-memory/SKILL.md"
assert_file_exists "skills/memory-health/SKILL.md"

assert_file_contains "skills/distill-memory/SKILL.md" "^name:" "frontmatter name"
assert_file_contains "skills/evolve-memory/SKILL.md" "^name:" "frontmatter name"
assert_file_contains "skills/memory-health/SKILL.md" "^name:" "frontmatter name"

echo ""

# ── 5. Agents 完整 ────────────────────────────────────────────────────────

echo "── 5. Agents"

assert_file_exists ".claude/agents/test-runner.md"
assert_file_exists ".claude/agents/test-author.md"

assert_file_contains ".claude/agents/test-runner.md" "^name:" "frontmatter name"
assert_file_contains ".claude/agents/test-author.md" "^name:" "frontmatter name"

echo ""

# ── 6. MEMORY.md 结构 ─────────────────────────────────────────────────────

echo "── 6. MEMORY.md 结构"

assert_file_contains "memory/MEMORY.md" "Key Decisions" "Key Decisions section"
assert_file_contains "memory/MEMORY.md" "Lessons Learned" "Lessons Learned section"
assert_file_contains "memory/MEMORY.md" "Recurring Patterns" "Recurring Patterns section"

echo ""

# ── 7. PreToolUse hook 行为 ───────────────────────────────────────────────

echo "── 7. PreToolUse git push 拦截"

# 模拟 git push 命令输入，应返回 exit 2（BLOCK）
PRETOOL_HOOK="hooks/pre-tool-gate.sh"
assert_executable "$PRETOOL_HOOK"

if [[ -x "$PRETOOL_HOOK" ]]; then
  # 测试：git push 应被拦截
  if echo '{"tool_name":"Bash","tool_input":{"command":"git push origin main"}}' | bash "$PRETOOL_HOOK" >/dev/null 2>&1; then
    echo "  ✗ git push NOT blocked (should exit 2)"
    FAILURES=$((FAILURES + 1))
  else
    EXIT_CODE=$?
    if [[ $EXIT_CODE -eq 2 ]]; then
      echo "  ✓ git push blocked (exit 2)"
      PASS=$((PASS + 1))
    else
      echo "  ✗ git push exit=$EXIT_CODE (expected 2)"
      FAILURES=$((FAILURES + 1))
    fi
  fi

  # 测试：普通命令应放行
  if echo '{"tool_name":"Bash","tool_input":{"command":"ls -la"}}' | bash "$PRETOOL_HOOK" >/dev/null 2>&1; then
    echo "  ✓ normal command passes"
    PASS=$((PASS + 1))
  else
    echo "  ✗ normal command blocked"
    FAILURES=$((FAILURES + 1))
  fi

  # 测试：git commit 应放行
  if echo '{"tool_name":"Bash","tool_input":{"command":"git commit -m test"}}' | bash "$PRETOOL_HOOK" >/dev/null 2>&1; then
    echo "  ✓ git commit passes"
    PASS=$((PASS + 1))
  else
    echo "  ✗ git commit blocked"
    FAILURES=$((FAILURES + 1))
  fi

  # 测试：rm -rf 应被拦截
  if echo '{"tool_name":"Bash","tool_input":{"command":"rm -rf /tmp/test"}}' | bash "$PRETOOL_HOOK" >/dev/null 2>&1; then
    echo "  ✗ rm -rf NOT blocked (should exit 2)"
    FAILURES=$((FAILURES + 1))
  else
    EXIT_CODE=$?
    if [[ $EXIT_CODE -eq 2 ]]; then
      echo "  ✓ rm -rf blocked (exit 2)"
      PASS=$((PASS + 1))
    else
      echo "  ✗ rm -rf exit=$EXIT_CODE (expected 2)"
      FAILURES=$((FAILURES + 1))
    fi
  fi
fi

echo ""

# ── 总结 ──────────────────────────────────────────────────────────────────

echo "════════════════════════════════════════════════════════"
echo "  通过: $PASS / 失败: $FAILURES"

if [[ $FAILURES -eq 0 ]]; then
  echo "  PIPELINE_OK — 记忆 Pipeline 完整性验证通过"
  echo "════════════════════════════════════════════════════════"
  exit 0
else
  echo "  PIPELINE_FAIL — $FAILURES 项缺失或错误"
  echo "════════════════════════════════════════════════════════"
  exit 1
fi
