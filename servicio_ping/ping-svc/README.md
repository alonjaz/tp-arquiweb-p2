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

## Etapa 0 – PostgreSQL accesible desde el contenedor (en la VM)
PostgreSQL escucha solo en 127.0.0.1; el contenedor llega por la IP del puente Docker.
```bash
sudo nano /etc/postgresql/16/main/postgresql.conf
#   listen_addresses = 'localhost,172.17.0.1'
echo "host  <BD>  <USUARIO>  172.16.0.0/12  scram-sha-256" | sudo tee -a /etc/postgresql/16/main/pg_hba.conf
sudo systemctl restart postgresql
sudo ufw allow from 172.16.0.0/12 to any port 5432 proto tcp   # solo redes Docker
sudo ss -lntp | grep 5432      # debe verse 127.0.0.1 y 172.17.0.1, NO 0.0.0.0
```
(El firewall sigue sin exponer 5432 a la red host-only.)

## Ejecutar
```bash
cd ping-svc
cp .env.example .env && nano .env          # credenciales de local_settings.py
docker build -t ping-svc:1.0.0 .
docker run -d --name ping-svc --env-file .env --add-host host.docker.internal:host-gateway \
  -p 127.0.0.1:8001:8000 --read-only --memory 256m ping-svc:1.0.0
curl -i http://127.0.0.1:8001/readyz
curl -i http://127.0.0.1:8001/ping/<UUID_DE_UN_CHECK>   # → 200 OK
```

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
