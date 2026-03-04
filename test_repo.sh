#!/bin/bash

echo ""
echo "======================================"
echo " Running Pancake Test Suite"
echo "======================================"
echo ""

PASS=0
FAIL=0 

for test in tests/*.py; do
    echo "Running $test"

    if python "$test"; then
        echo "[PASS]  $test"
        PASS=$((PASS+1))
    else
        echo "[FAIL]  $test"
        FAIL=$((FAIL+1))
    fi

    echo ""
done

echo "======================================"
echo " Tests complete"
echo "======================================"
echo ""

echo "$PASS Passed"
echo "$FAIL Failed"
echo ""