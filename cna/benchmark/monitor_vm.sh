#!/usr/bin/env bash
# Ejecutar EN LA VM durante la prueba (otra terminal SSH). Uso: ./monitor_vm.sh <etiqueta> [segundos=40]
LABEL=${1:?etiqueta}; SECS=${2:-40}
OUT="ping_${LABEL}_vm_$(date +%H%M%S).txt"
{ echo "## vmstat"; vmstat 1 "$SECS"; echo "## top procesos"; ps -eo pid,comm,%cpu,%mem --sort=-%cpu | head -12; echo "## free"; free -h; } | tee "$OUT"
echo "Guardado en $OUT (copiar a benchmark/results/)"
