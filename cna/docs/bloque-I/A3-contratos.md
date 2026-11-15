# Bloque I – A3: Contratos de API

## 1. Alcance

El TP original pide contratos **OpenAPI** (sincrónicos) y **AsyncAPI** (eventos). En esta implementación **AsyncAPI no aplica**, porque la arquitectura no usa broker ni mensajería asíncrona: la comunicación es síncrona por REST y el estado compartido se resuelve en la base común. Esta decisión está justificada en el **ADR-007**.

Por lo tanto, los contratos del sistema son exclusivamente OpenAPI, uno por servicio, almacenados en `cna/contracts/`.

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

## 3. Versionado

- **Versión de la ruta:** se mantiene `/api/v3/` heredada del monolito. El patrón Strangler Fig exige que el contrato expuesto al cliente sea idéntico al original, de modo que el cliente no distinga si lo atiende el monolito o el microservicio.
- **Versión del contrato:** se usa versionado semántico en `info.version`. Los agregados compatibles suben la versión menor; un cambio que rompa compatibilidad obligaría a publicar una nueva versión de ruta (`/api/v4/`) y a mantener ambas durante la transición.

## 4. F5-E4: Validación del contrato

El contrato se carga sin errores en un validador de OpenAPI. La etiqueta **OAS 3.1** confirma la especificación, el botón **Authorize** confirma que el esquema de autenticación fue reconocido, y el candado en cada operación confirma que la seguridad se aplica a todos los endpoints.

<img width="992" height="748" alt="F5-E4: contrato de checks-svc validado sin errores en Swagger Editor" src="https://github.com/user-attachments/assets/6cf7e05b-0f0f-4669-925a-032f35b6e3b2" />

## 5. Estado de los contratos del sistema

| Servicio | Contrato | Estado |
|----------|----------|--------|
| checks-svc | `cna/contracts/checks-svc.openapi.yaml` | Publicado y validado |
| ping-svc | `cna/contracts/ping-svc.openapi.yaml` | Pendiente de publicar por el responsable del servicio |
| alerts-svc | — | No expone API HTTP; es un proceso en segundo plano, por lo que no requiere contrato OpenAPI |
