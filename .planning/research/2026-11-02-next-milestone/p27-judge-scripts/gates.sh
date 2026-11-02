#!/bin/sh
# Gates for the pointer-form change: unit+arch groups, then make validate. Output to tmp/p27/gates.out.
cd "$(dirname "$0")/../.." || exit 1
export AI_KIT_REFUSE_REAL_HOME=1
{
  echo "== unit+arch"; date
  timeout 900 python3 tools/run_unittest_parallel.py --group unit --group arch 2>&1 | tail -25
  echo "exit-unit-arch=$?"
  echo "== validate"; date
  timeout 900 make validate 2>&1 | tail -30
  echo "exit-validate=$?"
  date
} > tmp/p27/gates.out 2>&1
echo "done" >> tmp/p27/gates.out
