#!/usr/bin/env bash
set -uo pipefail

FILE="${1:-}"

if [[ "$FILE" != *.py ]]; then
  exit 0
fi

bash /workshop/ypjh/ci/arch-check.sh
rc=$?

if [[ $rc -ne 0 ]]; then
  echo "ARCH_FAIL: ci/arch-check.sh failed for $FILE (exit $rc)"
  exit 1
fi
