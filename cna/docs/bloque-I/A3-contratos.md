# Bloque I – A3: Contratos de API

## 1. Alcance

El TP original pide contratos **OpenAPI** (sincrónicos) y **AsyncAPI** (eventos). En esta implementación **AsyncAPI no aplica**, porque la arquitectura no usa broker ni mensajería asíncrona: la comunicación es síncrona por REST y el estado compartido se resuelve en la base común. Esta decisión está justificada en el **ADR-007**.

Por lo tanto, los contratos de la arquitectura entregada son exclusivamente OpenAPI, uno por servicio, almacenados en `cna/contracts/`. En ese mismo directorio se incluye además un contrato AsyncAPI como diseño propuesto para trabajo futuro, documentado en la sección 8.

## 2. Contrato de checks-svc

- **Archivo:** `cna/contracts/checks-svc.openapi.yaml`
- **Especificación:** OpenAPI 3.1.0
- **Versión del contrato:** 1.0.0
- **Generación:** producido automáticamente por FastAPI a partir del código, de modo que el contrato no puede desincronizarse de la implementación.

### Operaciones expuestas

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/v3/checks/` | Lista los checks del proyecto (filtros opcionales `tag` y `slug`) |
| POST | `/api/v3/checks/` | Crea un check (201 Created) |
| GET | `/api/v3/checks/{code}` | Obtiene un check por UUID |
| POST | `/api/v3/checks/{code}` | Actualiza un check |
| PUT | `/api/v3/checks/{code}` | Actualiza un check |
| DELETE | `/api/v3/checks/{code}` | Elimina un check y sus filas dependientes |
| GET | `/healthz` | Liveness: el proceso responde |
| GET | `/readyz` | Readiness: verifica la conexión a la base (503 si falla) |
| GET | `/metrics` | Métricas en formato Prometheus |

### Esquemas de datos

`CheckIn` (creación) y `CheckUpdate` (actualización), validados con Pydantic. Los errores de validación devuelven 422 con el esquema `HTTPValidationError`.

### Autenticación

Esquema `ApiKeyAuth`: clave de API de 32 caracteres enviada en el header `X-Api-Key`, validada contra `accounts_project.api_key`. Se aplica de forma global a todas las operaciones del contrato. Las rutas de salud y métricas quedan fuera del alcance público del gateway.

### Desviación conocida

La operación DELETE devuelve `{"ok": true}` en lugar del objeto del check eliminado, que es lo que devuelve el monolito. Es la única diferencia de contrato respecto del original y queda declarada aquí y en el README del servicio.

## 3. Contrato de ping-svc

- **Archivo:** `cna/contracts/ping-svc.openapi.yaml`
- **Especificación:** OpenAPI 3.1.0
- **Versión del contrato:** 1.0.0
- **Generación:** redactado a mano. FastAPI no describiría con fidelidad las respuestas reales (texto `OK`, `not found`, `invalid url format` con tipo `text/html`) ni las cinco variantes de método y las rutas con barra final, que se declaran con `add_api_route`.

### Operaciones expuestas

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET, HEAD, POST, PUT, OPTIONS | `/ping/{code}` | Registra un ping de éxito para el check |
| GET, HEAD, POST, PUT, OPTIONS | `/ping/{code}/{suffix}` | Acción `start`, `fail`, `log` o exit status 0-255 |
| GET | `/healthz` | Liveness: el proceso responde |
| GET | `/readyz` | Readiness: ejecuta `SELECT 1` en PostgreSQL (503 si falla) |
| GET | `/metrics` | Métricas Prometheus (`http_requests_total`, `http_request_duration_seconds`) |

Las variantes con barra final (`/ping/{code}/` y `/ping/{code}/{suffix}/`) se comportan igual y se documentan en la descripción de la operación.

### Parámetros y respuestas

- `code` (ruta): UUID del check. `suffix` (ruta): `start`, `fail`, `log` o entero.
- `rid` (query, opcional): UUID que correlaciona un `start` con su ping de fin.
- `X-Request-ID` (header, opcional): se propaga y se devuelve; si falta o es inválido, el servicio genera uno.
- Cuerpo opcional (POST/PUT), truncado a `PING_BODY_LIMIT` bytes (10000 por defecto).
- Códigos: `200` (`OK`), `400` (`rid` inválido o exit status > 255), `404` (UUID o sufijo inválido, o check inexistente), `503` (error de base de datos).
- Cabeceras de respuesta: `X-Request-ID`, `Ping-Body-Limit`, `Cache-Control` y `Access-Control-Allow-Origin`, iguales a las del original.

### Autenticación

No tiene esquema de seguridad, igual que el monolito: el UUID del check actúa como secreto de acceso. No hay clave de API.

### Desviaciones conocidas

Declaradas también en el README del servicio:

- No implementa el ping por slug (`/ping/<key>/<slug>`, `?create=1`).
- No almacena cuerpos en S3: siempre se guardan en `api_ping.body_raw`.
- No aplica límites de tasa del original.
- El límite de cuerpo por defecto es 10000 bytes (`PING_BODY_LIMIT`).

## 4. Contrato de alerts-svc

`alerts-svc` ejecuta el proceso `sendalerts` en segundo plano, sin rutas HTTP de negocio. No requiere contrato OpenAPI propio.

## 5. Versionado

- **Versión de la ruta:** se mantienen las rutas heredadas del monolito (`/api/v3/` en `checks-svc`; `/ping/{code}` en `ping-svc`, que no tiene prefijo de versión). El patrón Strangler Fig exige que el contrato expuesto al cliente sea idéntico al original, de modo que el cliente no distinga si lo atiende el monolito o el microservicio.
- **Versión del contrato:** se usa versionado semántico en `info.version`. Los agregados compatibles suben la versión menor; un cambio que rompa compatibilidad obligaría a publicar una nueva versión de ruta (por ejemplo `/api/v4/`) y a mantener ambas durante la transición.

## 6. F5-E4: Validación de los contratos

**checks-svc.** El contrato se carga sin errores en Swagger Editor. La etiqueta **OAS 3.1** confirma la especificación, el botón **Authorize** confirma que el esquema de autenticación fue reconocido, y el candado en cada operación confirma que la seguridad se aplica a todos los endpoints.

<img width="992" height="748" alt="F5-E4: contrato de checks-svc validado sin errores en Swagger Editor" src="https://github.com/user-attachments/assets/6cf7e05b-0f0f-4669-925a-032f35b6e3b2" />

**ping-svc.** Se validó con Spectral (conjunto de reglas `spectral:oas`):

```bash
cd cna/contracts
npx --yes @stoplight/spectral-cli lint ping-svc.openapi.yaml
```

Resultado esperado: `0 errors`. Salida guardada en `cna/docs/F5-E4-ping-svc-lint.txt`.

<img width="1028" height="338" alt="F5-E4-ping-svc-lint" src="https://github.com/user-attachments/assets/96399961-89d3-4a04-a6fb-42662e5d3be7" />


## 7. Estado de los contratos del sistema

| Servicio | Contrato | Estado |
|----------|----------|--------|
| checks-svc | `cna/contracts/checks-svc.openapi.yaml` | Publicado y validado |
| ping-svc | `cna/contracts/ping-svc.openapi.yaml` | Publicado y validado (Spectral, 0 errores) |
| alerts-svc | — | No expone API HTTP; es un proceso en segundo plano, por lo que no requiere contrato OpenAPI |

## 8. Contrato de eventos (diseño propuesto, no implementado)

El archivo `cna/contracts/asyncapi.yaml` documenta un contrato AsyncAPI 3.0.0 con el sobre común de evento y su política de versionado, pensado para una evolución futura del sistema hacia comunicación asíncrona.

**No forma parte de la arquitectura entregada.** La implementación actual no utiliza broker ni mensajería: la comunicación entre servicios es síncrona por REST y el estado compartido se resuelve en la base común, según el **ADR-007**. El contrato de eventos queda registrado como insumo de diseño para el trabajo futuro mencionado en el A5.
