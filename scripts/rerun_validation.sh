#!/usr/bin/env bash
# The full re-run after a generator change (PLAN §3.3, "Re-run after decision N"; about 35 min).
# Keeps the old batches and figure cache in data/synthetic/<tag>/, then regenerates the batch
# reports, the fatigue checks, the dev / heldout / validation / validation_club matches, their
# estimates and every cached number behind the README and docs/figures. Synthetic data only.
#
#   systemd-run --user --scope -p MemoryMax=14G bash scripts/rerun_validation.sh pre40
#
# The ceiling runs with 3 workers: at 16 it runs out of memory. Do not edit src/runningbattery/sim/
# while this runs.
set -euo pipefail
TAG=${1:?usage: rerun_validation.sh <tag for the old data, e.g. pre40>}
PY=${PY:-.venv/bin/python}
JOBS=${JOBS:-16}
S=data/synthetic
C=data/figures_cache

# Never overwrite a backup: a second run with the same tag (after an aborted one) keeps the first
# copy and replaces only the new batches.
mkdir -p "$S/$TAG"
for b in dev heldout validation validation_club; do
    if [ -d "$S/$TAG/$b" ]; then
        rm -rf "${S:?}/$b"
    elif [ -d "$S/$b" ]; then
        mv "$S/$b" "$S/$TAG/"
    fi
done
if [ -d "$C" ] && [ ! -d "$S/$TAG/figures_cache" ]; then cp -r "$C" "$S/$TAG/figures_cache"; fi
mkdir -p "$C"

echo "== generator batches, seeds 1-240"
$PY -m runningbattery.sim.batch --seeds 1-240 --idsse --json "$C/sim_batch_240.json" \
    > "$C/sim_batch_240.txt"
$PY -m runningbattery.sim.batch --seeds 1-240 --no-fatigue --json "$C/sim_batch_240_off.json" \
    > "$C/sim_batch_240_off.txt"

echo "== fatigue checks, seeds 1-240"
$PY - <<EOF
import json
from concurrent.futures import ProcessPoolExecutor
from functools import partial

from runningbattery.sim import fatigue_checks as F

seeds = list(range(1, 241))
with ProcessPoolExecutor(max_workers=$JOBS) as ex:
    on = F.summarise(list(ex.map(partial(F._sim_one, fatigue=True), seeds)))
    off = F.summarise(list(ex.map(partial(F._sim_one, fatigue=False), seeds)))
json.dump({"on": on, "off": off}, open("$C/fatigue_checks_240.json", "w"), indent=1)
EOF

echo "== match folders"
{
    for s in $(seq 1 60); do printf '%s --out %s/dev/d%04d\n' "$s" "$S" "$s"; done
    for s in $(seq 61 120); do printf '%s --out %s/heldout/h%04d\n' "$s" "$S" "$s"; done
    for s in $(seq 1001 1050); do
        printf '%s --out %s/validation/v%d --vary\n' "$s" "$S" "$s"
        printf '%s --out %s/validation_club/v%d --vary --club-tests\n' "$s" "$S" "$s"
    done
} | xargs -P "$JOBS" -L 1 sh -c "$PY -m runningbattery.sim --seed \$0 \"\$@\" > /dev/null"

echo "== estimates (dev)"
ls -d "$S"/dev/d* | xargs -P "$JOBS" -n 1 sh -c "$PY -m runningbattery.engine \$0 > /dev/null"

echo "== validation"
for b in dev heldout validation; do
    $PY -m runningbattery.validate.batch "$S/$b" --json "$C/batch_$b.json" > "$C/batch_$b.txt"
done
$PY -m runningbattery.validate.batch "$S/validation_club" --mode club > "$C/batch_validation_club.txt"
for k in 1 3 5; do
    $PY -m runningbattery.validate.batch "$S/validation" --k "$k" > "$C/batch_validation_k$k.txt"
done
$PY -m runningbattery.validate.purposes "$S/dev" > "$C/purposes_dev.txt"
$PY -m runningbattery.validate.teams "$S/dev" --json "$C/teams_dev.json" > "$C/teams_dev.txt"
$PY -m runningbattery.validate.real "$S/dev" --jobs 4 --json "$C/real_check.json" \
    > "$C/real_check.txt"

echo "== ceiling (3 workers)"
$PY - <<EOF
import json
from pathlib import Path

from runningbattery.engine import params as EP
from runningbattery.validate import ceiling as C

for batch, name in (("dev", "ceiling_dev60"), ("validation", "ceiling_validation50")):
    folders = sorted(p for p in Path("$S", batch).iterdir() if p.is_dir())
    out = C.summary(C.run(folders, C.N_DRAWS, 3), EP.LOW_BATTERY)
    json.dump({"matches": len(folders), "summary": out}, open(f"$C/{name}.json", "w"), indent=1)
    print(name, C.format_summary(out), sep="\n")
EOF

echo "== figures"
$PY -m runningbattery.validate.figures
echo "done: reports in $C/*.txt"
