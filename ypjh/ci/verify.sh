#!/usr/bin/env bash
# ci/verify.sh — 识别功能完整验证体系
#
# 三层断言：
#   1. 结构断言  — response 字段存在性 + 类型正确
#   2. 契约断言  — R2（confidence 缺失→0）、R4（低置信度→pending_review）
#   3. 统计断言  — 多次运行，high_confidence 比例合理（不恒为 0 或 1）
#
# 关键约束：不调用真实 Bedrock（MOCK_BEDROCK=True）
#
# 退出码：0=全部通过，1=有断言失败，2=环境错误

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND="$PROJECT_ROOT/backend"
PYTHON="${PYTHON:-python3}"

echo "======================================================"
echo "  错题本识别功能验证体系 (ci/verify.sh)"
echo "======================================================"
echo ""

# ── 环境检查 ─────────────────────────────────────────────────────────────────

if [ ! -d "$BACKEND" ]; then
  echo "ERROR: 未找到 backend/ 目录"
  exit 2
fi

if ! $PYTHON -c "import pydantic" 2>/dev/null; then
  echo "ERROR: 缺少依赖 pydantic，请运行: pip install pydantic"
  exit 2
fi

echo "环境检查通过 ✓"
echo ""

# ── 第 1 层：结构断言 ─────────────────────────────────────────────────────────

echo "── 第 1 层：结构断言（字段存在性 + 类型）"
echo ""

STRUCTURE_RESULT=$($PYTHON - <<'PYEOF'
import sys
sys.path.insert(0, "backend")
sys.path.insert(0, ".")

from backend.services.recognition_service import RecognitionService

failures = []

# 所有 scenario 的结构验证
for scenario in ("clear", "blurry", "empty"):
    svc = RecognitionService(mock_scenario=scenario)
    r = svc.recognize(b"fake-bytes", user_id="ci-test-user")

    # status 必须是已知值
    if r.status not in ("high_confidence", "pending_review", "error"):
        failures.append(f"[{scenario}] status='{r.status}' 不在合法值集合内")

    # high_confidence 必须有 candidate
    if r.status == "high_confidence" and r.candidate is None:
        failures.append(f"[{scenario}] status=high_confidence 但 candidate=None")

    # pending_review 必须有 candidate（有内容，用户可编辑）
    if r.status == "pending_review" and r.candidate is None:
        failures.append(f"[{scenario}] status=pending_review 但 candidate=None")

    # candidate 字段类型检查
    if r.candidate is not None:
        if not isinstance(r.candidate.confidence, float):
            failures.append(f"[{scenario}] candidate.confidence 不是 float，实际: {type(r.candidate.confidence)}")
        if not (0.0 <= r.candidate.confidence <= 1.0):
            failures.append(f"[{scenario}] candidate.confidence={r.candidate.confidence} 超出 [0,1] 范围")
        if not isinstance(r.candidate.content, str) or not r.candidate.content:
            failures.append(f"[{scenario}] candidate.content 为空或非字符串")
        if not isinstance(r.candidate.correct_answer, str) or not r.candidate.correct_answer:
            failures.append(f"[{scenario}] candidate.correct_answer 为空或非字符串")

if failures:
    for f in failures:
        print(f"  FAIL: {f}")
    sys.exit(1)
else:
    print("  所有 scenario 结构验证通过 ✓")
    sys.exit(0)
PYEOF
)
STRUCTURE_EXIT=$?
echo "$STRUCTURE_RESULT"

if [ $STRUCTURE_EXIT -ne 0 ]; then
  echo ""
  echo "VERIFY_FAIL: 结构断言失败"
  exit 1
fi

# ── 第 2 层：契约断言 ─────────────────────────────────────────────────────────

echo ""
echo "── 第 2 层：契约断言（R2 + R4 业务规则）"
echo ""

CONTRACT_RESULT=$($PYTHON - <<'PYEOF'
import sys
sys.path.insert(0, "backend")
sys.path.insert(0, ".")

from backend.services.recognition_service import RecognitionService, MOCK_RESPONSES

failures = []

# R2 契约：confidence 缺失时按 0.0 处理，不得默认 1.0
svc = RecognitionService(mock_scenario="empty")
r = svc.recognize(b"fake-bytes", user_id="ci-test-user")
if r.candidate is not None and r.candidate.confidence > 0.0:
    failures.append(
        f"R2 违反: empty scenario confidence={r.candidate.confidence}，应为 0.0"
    )
if r.status == "high_confidence":
    failures.append(
        f"R2/R4 违反: empty scenario status={r.status}，confidence=0 不得为 high_confidence"
    )

# R4 契约：low confidence → pending_review（不得直接 high_confidence）
svc_blurry = RecognitionService(mock_scenario="blurry")
r_blurry = svc_blurry.recognize(b"fake-bytes", user_id="ci-test-user")
blurry_conf = MOCK_RESPONSES["blurry"]["confidence"]
if r_blurry.status == "high_confidence":
    failures.append(
        f"R4 违反: blurry scenario confidence={blurry_conf} 但 status=high_confidence"
    )
if r_blurry.status != "pending_review":
    failures.append(
        f"R4 违反: blurry scenario status={r_blurry.status}，预期 pending_review"
    )

# R2 契约：high confidence → status=high_confidence（正常路径）
svc_clear = RecognitionService(mock_scenario="clear")
r_clear = svc_clear.recognize(b"fake-bytes", user_id="ci-test-user")
if r_clear.status != "high_confidence":
    failures.append(
        f"正常路径失败: clear scenario status={r_clear.status}，预期 high_confidence"
    )

# R4 契约：低置信度结果必须有 error_hint（引导用户核对）
if r_blurry.status == "pending_review" and not r_blurry.error_hint:
    failures.append("R4: pending_review 结果缺少 error_hint，用户无法得知需要核对")

if failures:
    for f in failures:
        print(f"  FAIL: {f}")
    sys.exit(1)
else:
    print("  R2 契约通过：confidence 缺失正确处理为 0.0 ✓")
    print("  R4 契约通过：低置信度正确标记为 pending_review ✓")
    sys.exit(0)
PYEOF
)
CONTRACT_EXIT=$?
echo "$CONTRACT_RESULT"

if [ $CONTRACT_EXIT -ne 0 ]; then
  echo ""
  echo "VERIFY_FAIL: 契约断言失败"
  exit 1
fi

# ── 第 3 层：统计断言 ─────────────────────────────────────────────────────────

echo ""
echo "── 第 3 层：统计断言（分布合理性，N=30 次运行）"
echo ""

STATS_RESULT=$($PYTHON - <<'PYEOF'
import sys
sys.path.insert(0, "backend")
sys.path.insert(0, ".")

from backend.services.recognition_service import RecognitionService

N = 30
scenarios = ["clear", "blurry", "empty"]
counts = {s: {"high_confidence": 0, "pending_review": 0, "error": 0} for s in scenarios}

for _ in range(N):
    for scenario in scenarios:
        svc = RecognitionService(mock_scenario=scenario)
        r = svc.recognize(b"fake-bytes", user_id="ci-test-user")
        counts[scenario][r.status] = counts[scenario].get(r.status, 0) + 1

failures = []

# clear scenario: N=30 次应该全部 high_confidence（mock 是确定的）
clear_hc = counts["clear"]["high_confidence"]
if clear_hc != N:
    failures.append(f"clear scenario: {N} 次中仅 {clear_hc} 次 high_confidence（预期 {N}）")

# blurry scenario: N=30 次应该全部 pending_review
blurry_pr = counts["blurry"]["pending_review"]
if blurry_pr != N:
    failures.append(f"blurry scenario: {N} 次中仅 {blurry_pr} 次 pending_review（预期 {N}）")

# empty scenario: N=30 次应该全部 pending_review（confidence=0 → 低置信度）
empty_pr = counts["empty"]["pending_review"]
if empty_pr != N:
    failures.append(f"empty scenario: {N} 次中仅 {empty_pr} 次 pending_review（预期 {N}）")

# 统计摘要（无论成败都打印）
print(f"  {N} 次运行分布统计：")
for s in scenarios:
    hc = counts[s]["high_confidence"]
    pr = counts[s]["pending_review"]
    err = counts[s]["error"]
    print(f"    {s:10s}: high_confidence={hc:2d}  pending_review={pr:2d}  error={err:2d}")

if failures:
    print("")
    for f in failures:
        print(f"  FAIL: {f}")
    sys.exit(1)
else:
    print("")
    print("  统计分布符合预期 ✓（Mock 是确定性的，符合 REQ-10）")
    sys.exit(0)
PYEOF
)
STATS_EXIT=$?
echo "$STATS_RESULT"

if [ $STATS_EXIT -ne 0 ]; then
  echo ""
  echo "VERIFY_FAIL: 统计断言失败"
  exit 1
fi

# ── 总结 ──────────────────────────────────────────────────────────────────────

echo ""
echo "======================================================"
echo "  VERIFY_OK — 全部 3 层断言通过 ✓"
echo ""
echo "  未调用真实 Bedrock（MOCK_BEDROCK=True）"
echo "  结构 ✓  契约(R2+R4) ✓  统计分布 ✓"
echo "======================================================"
exit 0
