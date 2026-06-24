#!/usr/bin/env bash
# hooks/human-gate.sh
# 不可逆操作前的人类确认 Gate
# 使用方法：bash hooks/human-gate.sh "<操作描述>"
# 退出码：0=用户确认，1=用户拒绝/取消

OPERATION="${1:-未说明的操作}"

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║          ⚠️  人类 Gate — 需要确认          ║"
echo "╚══════════════════════════════════════════╝"
echo ""
echo "即将执行不可逆操作："
echo "  >> $OPERATION"
echo ""
echo "此操作无法自动撤销。"
echo ""
read -r -p "确认继续？(yes/no): " ANSWER

case "$ANSWER" in
  yes|YES|y|Y)
    echo "[gate] 用户已确认：$OPERATION"
    exit 0
    ;;
  *)
    echo "[gate] 用户取消操作。"
    exit 1
    ;;
esac
