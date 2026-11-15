# ping-svc (Sonia)

Microservicio que reemplaza la ruta `/ping/<uuid>` de Healthchecks v4.0 (FastAPI + PostgreSQL).
Comparte la misma base PostgreSQL del TP1.

## Etapa 1 – Estudio de la funcionalidad (para el informe)
| Pregunta | Respuesta |
|---|---|
| Archivo que la implementa | `hc/api/views.py` → vista `ping()`; lógica en `hc/api/models.py` → `Check.ping()`; rutas en `hc/api/urls.py` |
| Tablas que lee/escribe | `api_check` (lee y actualiza status, last_ping, n_pings, alert_after…), `api_ping` (inserta el ping), `api_flip` (inserta al cambiar de estado) |
| Petición | `GET/HEAD/POST/PUT /ping/<uuid>[/start\|/fail\|/log\|/<0-255>]`, opcional `?rid=<uuid>`, cuerpo ≤ 100 KB |
| Respuesta | `200 OK` (texto `OK`), `404 not found` (UUID desconocido/ inválido), `400` (rid inválido) |

> Verificar en el repo clonado: `grep -n "def ping" -A60 hc/api/views.py hc/api/models.py`

## Lógica replicada del original (contrastada con el código de v4.0)
`views.ping`, `Check.ping`, `get_grace_start`, `going_down_after`, `create_flip`, `prune`, `match_keywords`
y los esquemas de `api_check`, `api_ping`, `api_flip`.

### Dos pasos obligatorios antes de construir la imagen
```bash
# 1) Igualar versiones de cronsim y oncalendar con las de Healthchecks
grep -in "cronsim\|oncalendar" healthchecks/requirements.txt   # ya igualado: cronsim==2.7, oncalendar==1.1
grep -n "import.*OnCalendar\|import.*CronSim" healthchecks/hc/api/models.py
#    -> copiar esas versiones a ping-svc/requirements.txt
# 2) prune() consulta accounts_profile y accounts_project: confirmar columnas
sudo -u postgres psql -d <BD> -c '\d accounts_profile' -c '\d accounts_project' -c '\d api_notification'
#    Se asume: accounts_profile.user_id, accounts_project.owner_id, api_notification.owner_id/created
```

## Etapa 0 – Conexión a PostgreSQL: MODO HOST (sin tocar PostgreSQL ni ufw)
El contenedor usa la red de la VM (`--network host`), así que llega a PostgreSQL por
`127.0.0.1:5432` igual que Gunicorn. Escucha solo en `127.0.0.1:8001` (HOST/PORT del `.env`);
el 8000 ya lo ocupa Gunicorn.

Trade-off a documentar en el informe: se pierde el aislamiento de red del contenedor
a cambio de no abrir PostgreSQL a las redes Docker (superficie expuesta menor, P10).

## Ejecutar
```bash
cd ping-svc
cp .env.example .env && nano .env          # solo USUARIO, CLAVE y NOMBRE_BD
docker build -t ping-svc:1.0.0 .
docker run -d --name ping-svc --network host --env-file .env \
  --read-only --tmpfs /prom:rw,mode=1777 --memory 256m --restart unless-stopped ping-svc:1.0.0
curl -i http://127.0.0.1:8001/readyz
curl -i http://127.0.0.1:8001/ping/<UUID_DE_UN_CHECK>   # → 200 OK
```
(Alternativa con red puente: exige configurar `listen_addresses`, `pg_hba.conf` y `ufw`; no recomendada.)

## Pruebas
```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt
pytest -q tests
```

## Verificar equivalencia con el original
```bash
curl -s https://healthchecks.arqweb.test/svc/ping/<UUID> -k     # microservicio
sudo -u postgres psql -d <BD> -c "select status,last_ping,n_pings from api_check where code='<UUID>';"
sudo -u postgres psql -d <BD> -c "select n,kind,method,remote_addr,created from api_ping order by id desc limit 3;"
```
La UI de Healthchecks debe mostrar el nuevo "Last Ping".

## Limitaciones conocidas (documentar en el informe)
- No implementa ping por slug (`/ping/<key>/<slug>`, `?create=1`), ni almacenamiento S3 (cuerpo siempre en `body_raw`).
- No se aplican límites de tasa del original (si los hubiera) ni el chequeo de `valid_ip` más allá de guardar NULL si no es IP.
- `prune()` corre en el hilo de la petición cada 100 pings, igual que el original.
