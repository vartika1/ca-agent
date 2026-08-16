#!/bin/bash
# CA Agent — full reliability check. Run before trusting the skill on any return.
# Usage: bash run_tests.sh
set -e
cd "$(dirname "$0")"
echo "══════════════════════════════════════════════════════"
echo " CA Agent — reliability suite (AY 2026-27)"
echo "══════════════════════════════════════════════════════"
fail=0
for f in tests/test_*.py; do
  printf "%-42s " "$(basename "$f")"
  if out=$(python3 "$f" 2>&1); then
    echo "${out##*$'\n'}"
  else
    echo "FAILED"; echo "$out"; fail=1
  fi
done
echo "------------------------------------------------------"
printf "%-42s " "examples/run_examples.py"
if python3 examples/run_examples.py >/dev/null 2>&1; then echo "4 worked examples PASSED"; else echo "FAILED"; fail=1; fi
printf "%-42s " "module import sanity"
if python3 -c "import scripts; from scripts import pipeline, parsers" >/dev/null 2>&1; then echo "OK"; else echo "FAILED"; fail=1; fi
echo "══════════════════════════════════════════════════════"
[ $fail -eq 0 ] && echo "ALL GREEN — engine trustworthy" || { echo "FAILURES ABOVE — do not file"; exit 1; }
