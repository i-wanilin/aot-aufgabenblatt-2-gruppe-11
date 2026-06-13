#!/usr/bin/env bash
# Erzeugt die vier Experiment-Logs (2 je Protokoll) für die Screencasts/den Report.
# Aufruf:  bash experiments/run_all.sh
set -euo pipefail
cd "$(dirname "$0")/.."

mkdir -p experiments/logs
PY=python3

declare -A WORLDS=(
  [balanced]=config/world_balanced.json
  [overhang]=config/world_overhang.json
)

for w in balanced overhang; do
  for proto in cnp ecnp; do
    out="experiments/logs/${proto}_${w}.log"
    echo ">> ${proto^^} auf '${w}'  ->  ${out}"
    $PY src/simulate.py --world "${WORLDS[$w]}" --protocol "$proto" > "$out"
  done
done

echo
echo "Kurzvergleich (beide Protokolle, ohne Nachrichten-Log):"
for w in balanced overhang; do
  echo "── Welt: $w ──"
  $PY src/simulate.py --world "${WORLDS[$w]}" --protocol both --quiet \
    | grep -E "Protokoll|GESAMTENERGIE|Gesamtenergie|Nachrichten"
done
