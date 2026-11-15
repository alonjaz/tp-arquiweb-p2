# Mediciones de ping-svc (Etapas 3 y 5)

Métrica: **pings por segundo** (`Requests per second` de `ab`) sobre `/ping/<uuid>`.

## Condiciones (deben ser idénticas en ambas rondas)
- Misma VM, mismo check (UUID), mismo Nginx/TLS, mismo cliente (anfitrión).
- `ab -n 5000 -c 10` (+ ronda extra con `-c 50`), 5 repeticiones, 1 calentamiento.
- Mismo nº de workers (Gunicorn del original vs `WEB_CONCURRENCY=2` del servicio).
- Nada más corriendo en la VM.

## Procedimiento
```bash
# Etapa 3 – referencia (Healthchecks original, sin tocar)
./bench_ping.sh original https://healthchecks.arqweb.test/ping/<UUID>
./bench_ping.sh original_c50 https://healthchecks.arqweb.test/ping/<UUID> 5000 50

# Etapa 5 – microservicio (ruta A/B /svc/ping/)
./bench_ping.sh microservicio https://healthchecks.arqweb.test/svc/ping/<UUID>
./bench_ping.sh microservicio_c50 https://healthchecks.arqweb.test/svc/ping/<UUID> 5000 50
```
En la VM, en paralelo: `./monitor_vm.sh original` / `./monitor_vm.sh microservicio`.

## POST con cuerpo (opcional)
```bash
echo "job ok" > body.txt
ab -n 3000 -c 10 -p body.txt -T text/plain https://healthchecks.arqweb.test/ping/<UUID>
```

## Tabla comparativa (completar con results/*_resumen.txt)
| Escenario | Concurrencia | req/s (prom.) | Latencia media (ms) | p95 (ms) | Fallidas |
|---|---|---|---|---|---|
| Original (Gunicorn+Django) | 10 | | | | |
| ping-svc (FastAPI) | 10 | | | | |
| Original | 50 | | | | |
| ping-svc | 50 | | | | |

Interpretar con prudencia: un microservicio añade contenedor + salto de red local;
no afirmar causalidad sin respaldo (correlacionar con `vmstat`/`ps`).
