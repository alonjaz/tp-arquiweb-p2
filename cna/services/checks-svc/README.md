# checks-svc

Microservicio que extrae del monolito Healthchecks la API de gestion de checks (`/api/v3/checks/`). Mantiene el mismo contrato (URLs, header `X-Api-Key`, JSON y codigos de estado) para poder reemplazar al monolito detras de Nginx (patron Strangler Fig). Usa la misma base PostgreSQL que el monolito.

## Endpoints
- `GET /api/v3/checks/` lista los checks del proyecto
- `POST /api/v3/checks/` crea un check
- `GET /api/v3/checks/{uuid}` obtiene un check
- `POST` o `PUT /api/v3/checks/{uuid}` actualiza un check
- `DELETE /api/v3/checks/{uuid}` borra un check
- `GET /healthz` (vivo), `GET /readyz` (listo, verifica la base), `GET /metrics` (Prometheus)

Autenticacion: header `X-Api-Key` de 32 caracteres, validado contra `accounts_project.api_key`.

## Configuracion (variables de entorno)
`DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `PORT` (8001), `SITE_ROOT`, `PING_ENDPOINT`, `SERVICE_NAME`, `LOG_LEVEL`. Ver `.env.example`. El archivo `.env` real no se versiona.

## Pruebas
    python -m pytest -q

## Contenedor
    docker build -t checks-svc:1.0.0-<hash-commit> .
    docker run -d --name checks-svc --network host --env-file .env --read-only --tmpfs /tmp --memory 256m --cpus 0.5 checks-svc:1.0.0-<hash-commit>

Imagen multi-stage sobre python:3.12-slim, usuario no root (uid 10001), HEALTHCHECK sobre `/healthz`.

## Diferencia conocida con el monolito
`DELETE` responde `{"ok": true}`; el monolito devuelve el check borrado. El codigo de estado y el efecto en la base son los mismos.
