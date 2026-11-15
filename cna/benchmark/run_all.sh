#!/usr/bin/env bash
# Corre la matriz completa de mediciones de ping (original vs microservicio)
# y captura recursos (vmstat, procesos, docker stats) durante cada corrida.
#
# Uso: ./run_all.sh <UUID> [BASE_ORIGINAL] [BASE_MICRO] [TAG]
#   Directo (VM):  ./run_all.sh <UUID>
#   Gateway:       ./run_all.sh <UUID> https://healthchecks.arqweb.test https://healthchecks.arqweb.test/svc gateway
# Variables opcionales: N (pings por corrida, 5000) y REPS (repeticiones, 5).
set -euo pipefail
cd "$(dirname "$0")"

UUID=${1:?uuid del check}
ORIG=${2:-http://127.0.0.1:8000}
MICRO=${3:-http://127.0.0.1:8002}
TAG=${4:-directo}
N=${N:-5000}; REPS=${REPS:-5}
RSC=resources; mkdir -p results "$RSC"

# Verificación previa: ambos deben responder 200 con ese UUID
for u in "$ORIG/ping/$UUID" "$MICRO/ping/$UUID"; do
  code=$(curl -ks -o /dev/null -w '%{http_code}' "$u" || true)
  [ "$code" = "200" ] || { echo "!! $u devolvió $code (se esperaba 200)"; exit 1; }
done

measure() {   # measure <label> <url> <c>
  local label=$1 url=$2 c=$3 pids=()
  vmstat 1 > "$RSC/vmstat_${label}_c${c}.txt" & pids+=($!)
  ( while true; do date +%T; ps -eo pid,comm,%cpu,%mem --sort=-%cpu | head -6; sleep 2; done ) \
      > "$RSC/procesos_${label}_c${c}.txt" & pids+=($!)
  if [[ $label == microservicio* ]] && docker ps --format '{{.Names}}' | grep -qx ping-svc; then
    ( while true; do date +%T; docker stats --no-stream --format '{{.Name}} cpu={{.CPUPerc}} mem={{.MemUsage}}' ping-svc; sleep 2; done ) \
      > "$RSC/dockerstats_${label}_c${c}.txt" & pids+=($!)
  fi
  ./bench_ping.sh "$label" "$url" "$N" "$c" "$REPS" || true
  kill "${pids[@]}" 2>/dev/null || true
  wait 2>/dev/null || true
}

for c in 10 50; do
  # Se alterna el orden por concurrencia para no favorecer siempre al segundo (caché de PostgreSQL)
  if [ "$c" -eq 10 ]; then order=(original microservicio); else order=(microservicio original); fi
  for who in "${order[@]}"; do
    base=$ORIG; [ "$who" = "microservicio" ] && base=$MICRO
    echo "=== ${who}_${TAG}  c=${c} ==="
    measure "${who}_${TAG}" "$base/ping/$UUID" "$c"
    sleep 10
  done
done
echo ">> Listo. Generar la tabla con: ./make_table.sh"
