#!/usr/bin/env bash
# Arma la tabla comparativa (Markdown) desde results/ping_*_resumen.txt
cd "$(dirname "$0")"
ls results/ping_*_resumen.txt >/dev/null 2>&1 || { echo "sin resultados en results/"; exit 1; }
for f in results/ping_*_resumen.txt; do
  b=$(basename "$f" _resumen.txt); b=${b#ping_}      # p.ej. original_directo_c10
  c=${b##*_c}; rest=${b%_c*}
  label=${rest%%_*}; esc=${rest#*_}
  awk -v esc="$esc" -v c="$c" -v l="$label" '{
      for(i=1;i<=NF;i++){split($i,a,"="); v[a[1]]=a[2]}
      printf "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n", esc,c,l,v["rps"],v["mean_ms"],v["p95_ms"],v["p99_ms"],v["failed_total"],v["non2xx_total"]}' "$f"
done | sort -t$'\t' -k1,1 -k2,2n -k3,3 | awk -F'\t' '
  {row[NR]=$0; if($3=="original") base[$1","$2]=$4}
  END{
    print "| Escenario | c | Servicio | req/s | media (ms) | p95 (ms) | p99 (ms) | fallidas | no-2xx | Δ req/s vs original |"
    print "|---|---|---|---|---|---|---|---|---|---|"
    for(i=1;i<=NR;i++){ split(row[i],f,"\t"); d="—"; k=f[1]","f[2]
      if(f[3]!="original" && (k in base) && base[k]>0) d=sprintf("%+.1f %%",(f[4]-base[k])/base[k]*100)
      printf "| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |\n",f[1],f[2],f[3],f[4],f[5],f[6],f[7],f[8],f[9],d }}'
