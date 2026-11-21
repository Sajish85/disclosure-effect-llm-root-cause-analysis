#!/bin/bash
# round driver: screens, then r1, r2, r3. Leak scan of /tmp and ~ after each round. Cost check via run_full CAP_STOP.
R=/Users/sajishkrishnan/d1-coincident-rca
PY=/tmp/d1runs/venv/bin/python
cd $R
for ROUND in s1,s2 r1 r2 r3; do
  M=/tmp/d1full-marker-$ROUND; touch $M
  echo "== round $ROUND start $(date)" 
  W=6 $PY -I work/run_full.py $ROUND S,O,X </dev/null
  {
    echo "round $ROUND scan $(date)"
    find /tmp -maxdepth 3 -type f -newer $M -not -path '/tmp/d1full/*' -not -path '/tmp/claude*' -not -path '/tmp/d1full-marker*' -not -path '/tmp/d1runs/venv/*' 2>/dev/null | head -50
    find ~ -maxdepth 2 -type f -newer $M -not -path "$HOME/Library/*" -not -path "$HOME/.claude/*" -not -path "$HOME/.codex/*" -not -path "$HOME/d1-coincident-rca/*" -not -path "$HOME/.Trash/*" 2>/dev/null | head -50
    echo "-- leftover run dirs:"; ls /tmp/d1full | grep -v codexhome | head
  } > results/leak_scans/scan_$ROUND.txt 2>&1
  $PY -I work/analyze_full.py > results/leak_scans/meta_$ROUND.txt 2>&1
  echo "== round $ROUND done $(date)"; tail -22 results/leak_scans/meta_$ROUND.txt | head -30
  C=$($PY -I -c "import json;print(json.load(open('$R/results/summary_full.json'))['_meta']['claude_cost_usd'])")
  echo "cumulative claude cost $C"
  $PY -I -c "import sys;sys.exit(0 if $C<115 else 1)" || { echo "COST STOP"; break; }
done
echo ALLDONE
