#!/usr/bin/env bash
# Erzeugt die vier Experiment-Logs (2 je Protokoll) fuer Screencasts/Report.
# Aufruf: bash experiments/run_all.sh
set -euo pipefail
cd "$(dirname "$0")/.."

if [[ -n "${PY:-}" ]]; then
  PYTHON=("$PY")
elif command -v python3 >/dev/null 2>&1 && python3 -c 'print("ok")' >/dev/null 2>&1; then
  PYTHON=(python3)
elif command -v py >/dev/null 2>&1 && py -c 'print("ok")' >/dev/null 2>&1; then
  PYTHON=(py)
elif command -v python >/dev/null 2>&1 && python -c 'print("ok")' >/dev/null 2>&1; then
  PYTHON=(python)
else
  echo "Kein funktionierender Python-Interpreter gefunden." >&2
  exit 1
fi

mkdir -p experiments/logs

declare -A WORLDS=(
  [balanced]=config/world_balanced.json
  [overhang]=config/world_overhang.json
)

for w in balanced overhang; do
  for proto in cnp ecnp; do
    out="experiments/logs/${proto}_${w}.log"
    echo ">> ${proto^^} auf '${w}' -> ${out}"
    "${PYTHON[@]}" src/simulate.py --world "${WORLDS[$w]}" --protocol "$proto" > "$out"
  done
done

echo
echo "Kurzvergleich (beide Protokolle, ohne Nachrichten-Log):"
for w in balanced overhang; do
  echo "-- Welt: $w --"
  "${PYTHON[@]}" src/simulate.py --world "${WORLDS[$w]}" --protocol both --quiet \
    | grep -E "Protokoll|GESAMTENERGIE|Gesamtenergie|Nachrichten"
done
