#!/bin/bash
# Quick lint check — аналог tsc-filter.sh з ElectroBoard
# Показує перші 15 помилок + загальний рахунок (економія токенів)

cd "$(dirname "$0")/.."

if ! command -v ruff &> /dev/null && [ ! -f "venv/Scripts/ruff.exe" ]; then
    echo "ruff not installed. Run: pip install ruff"
    exit 1
fi

RUFF=${RUFF:-venv/Scripts/ruff}

echo "=== Ruff Check ==="
ERRORS=$($RUFF check voicetype/ scripts/ 2>&1)
COUNT=$(echo "$ERRORS" | grep -c "^voicetype\|^scripts")

if [ "$COUNT" -eq 0 ]; then
    echo "OK — no issues found"
else
    echo "$ERRORS" | head -15
    if [ "$COUNT" -gt 15 ]; then
        echo "... and $((COUNT - 15)) more errors (total: $COUNT)"
    fi
    echo ""
    echo "Auto-fix: $RUFF check --fix voicetype/ scripts/"
fi
