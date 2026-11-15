#!/usr/bin/env bash
# Uso: ./bench_ping.sh <etiqueta> <URL_PING> [N=5000] [C=10] [REPS=5]
#   original : ./bench_ping.sh original      https://healthchecks.arqweb.test/ping/<UUID>
#   micro    : ./bench_ping.sh microservicio https://healthchecks.arqweb.test/svc/ping/<UUID>
# Ejecutar desde el ANFITRIÓN (igual que el ab de la Entrega 4 del TP1).
set -euo pipefail
LABEL=${1:?etiqueta}; URL=${2:?url}; N=${3:-5000}; C=${4:-10}; REPS=${5:-5}
OUT="$(dirname "$0")/results"; mkdir -p "$OUT"
CSV="$OUT/ping_${LABEL}.csv"
echo "label,run,n,c,rps,mean_ms,p95_ms,p99_ms,max_ms,failed" > "$CSV"

echo ">> Calentamiento (200 pings, no se registra)"
ab -n 200 -c "$C" "$URL" > /dev/null 2>&1 || true

for i in $(seq 1 "$REPS"); do
  RAW="$OUT/ping_${LABEL}_run${i}.txt"
  ab -n "$N" -c "$C" "$URL" > "$RAW" 2>&1
  rps=$(awk '/Requests per second/{print $4}' "$RAW")
  mean=$(awk '/Time per request:.*\(mean\)$/{print $4}' "$RAW")
  p95=$(awk '$1=="95%"{print $2}' "$RAW")
  p99=$(awk '$1=="99%"{print $2}' "$RAW")
  max=$(awk '$1=="100%"{print $2}' "$RAW")
  fail=$(awk '/Failed requests/{print $3}' "$RAW")
  echo "$LABEL,$i,$N,$C,$rps,$mean,$p95,$p99,$max,$fail" | tee -a "$CSV"
  sleep 3
done

echo ">> Resumen (promedio de $REPS corridas)"
awk -F, 'NR>1{r+=$5;m+=$6;p+=$7;f+=$10;n++} END{printf "rps=%.2f  mean_ms=%.2f  p95_ms=%.1f  failed_total=%d\n", r/n,m/n,p/n,f}' "$CSV" \
  | tee "$OUT/ping_${LABEL}_resumen.txt"
