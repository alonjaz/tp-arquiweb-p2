# Proyecto Integrador II — De Monolito a Cloud Native: Healthchecks

**Materia:** Arquitectura Web — FP-UNA 2026
**Docente:** José Rodrigo Benítez Paredes
**Integrantes:** Jazmín Alonso (checks-svc), Sonia Romero (ping-svc), Diego Castillo (alerts-svc)
**Repositorio:** https://github.com/alonjaz/tp-arquiweb-p2 — tag `v2.0.0`
**Fecha:** 15 de noviembre de 2026

## 1. Resumen ejecutivo

Se extrajeron funcionalidades del monolito Healthchecks hacia microservicios contenerizados aplicando el patrón Strangler Fig, sin modificar el código del monolito. Los servicios comparten la base PostgreSQL original, lo que permite revertir cualquier ruta en menos de un minuto. La medición comparativa de la API de gestión de checks muestra que el microservicio atiende **20,3 peticiones por segundo frente a 15,2 del monolito**, con una latencia media de **196,8 ms frente a 263,0 ms**, sin peticiones fallidas en ninguno de los dos escenarios.

## 2. El monolito y el objetivo

Healthchecks es una aplicación Django con PostgreSQL que vigila tareas programadas: cada tarea registra un *check*, avisa periódicamente mediante un *ping*, y el sistema alerta cuando una tarea deja de avisar.

Se seleccionaron tres funcionalidades que representan tres perfiles de carga distintos:

| Funcionalidad | Servicio | Responsable | Perfil de carga |
|---|---|---|---|
| API de gestión de checks (`/api/v3/checks/`) | checks-svc | Jazmín | Lectura y escritura por API |
| Recepción de pings (`/ping/<uuid>`) | ping-svc | Sonia | Escritura intensiva |
| Evaluación de estados y alertas (`sendalerts`) | alerts-svc | Diego | Proceso en segundo plano |

## 3. Bloque I — Diseño y descomposición

El diseño completo está en `cna/docs/bloque-I/`:

- **A1 — Análisis y mapa de contextos.** Las 23 tablas de la base se verificaron con `information_schema`. La matriz de acoplamiento muestra que `api_check` y `api_flip` son usadas por los tres servicios, lo que impide una extracción con base por servicio.
- **A2 — ADR-006 a ADR-010.** Strangler Fig, comunicación síncrona por REST sin broker, Docker Compose, base compartida y stack unificado en Python. Cada decisión con alternativa descartada y consecuencias negativas reconocidas.
- **A3 — Contratos.** OpenAPI 3.1.0 por servicio, validados sin errores. El contrato AsyncAPI queda declarado como diseño para trabajo futuro, no implementado.
- **A4 — Modelo C4 y secuencias.** Niveles 1 y 2, más dos diagramas de secuencia con caminos de error (401 al crear un check, 404 al recibir un ping).
- **A5 — Migración y riesgos.** Orden de extracción de menor a mayor riesgo, reversión en menos de un minuto cambiando el destino de una ruta en Nginx, y matriz de riesgos con mitigaciones.

## 4. Bloque II — Construcción y despliegue

### 4.1 checks-svc

FastAPI con psycopg 3, Pydantic y prometheus-client. Replica los endpoints del monolito con el mismo contrato, autenticando con una clave de API de 32 caracteres en el header `X-Api-Key` contra `accounts_project`. Expone `/healthz`, `/readyz` (verifica la base, 503 si falla) y `/metrics`. Emite logs JSON a stdout y propaga `X-Request-ID`. Cuenta con **15 pruebas automatizadas** que se ejecutan con un solo comando.

**Desviación declarada:** la operación DELETE devuelve `{"ok": true}` en lugar del objeto eliminado.

### 4.2 ping-svc

FastAPI con psycopg 3. Replica la recepción de pings sobre `api_check`, `api_ping` y `api_flip`, respetando el límite de retención definido en `accounts_profile`. Expone `/healthz`, `/readyz` y `/metrics`, con pruebas automatizadas y desviaciones declaradas en su README.

### 4.3 alerts-svc

En desarrollo al momento de la entrega. Es el último de la secuencia de migración por ser el de mayor riesgo, dado que produce efectos fuera del sistema (notificaciones).

### 4.4 Contenerización

| Servicio | Imagen | Usuario | Memoria | CPU | Sistema de archivos | Healthcheck |
|---|---|---|---|---|---|---|
| checks-svc | `checks-svc:1.0.0-10d59dc` | no root (uid 10001) | 256 MB | 0.5 | solo lectura | sí |
| ping-svc | `ping-svc:1.0.0` | no root | 256 MB | 0.5 | solo lectura | sí |

Ambas imágenes usan construcción multietapa sobre `python:3.12-slim`, con etiqueta versionada (nunca `:latest`) y configuración exclusivamente por variables de entorno. Ningún secreto queda en el código ni en la imagen.

### 4.5 Integración y gateway

`cna/deploy/docker-compose.yml` define el levantamiento de los servicios junto a un gateway Nginx que materializa el Strangler Fig: `/api/v3/checks/` se dirige a checks-svc, `/ping/` a ping-svc, y **todo lo no migrado continúa hacia el monolito**. La base PostgreSQL permanece en el anfitrión y los contenedores la alcanzan mediante `host.docker.internal`.

Esta configuración se publica como parte del diseño de integración y **no fue ejecutada ni validada de extremo a extremo** al momento de la entrega, dado que alerts-svc no está terminado. Así se declara en el encabezado del propio archivo y en el README del repositorio.

## 5. Bloque III — Operación

### 5.1 Observabilidad

Los dos servicios implementados exponen métricas Prometheus en `/metrics`, con contador de peticiones por código de estado e histograma de latencia. Los logs se emiten en JSON a stdout con `timestamp`, `level`, `service`, `request_id` y `message`, y el `X-Request-ID` se propaga y se devuelve, lo que permite correlacionar una petición entre el gateway y el servicio.

### 5.2 Rendimiento comparado

Ver sección 6.

### 5.3 Seguridad

La configuración se realiza únicamente por variables de entorno; los archivos `.env` no se versionan y se publican sus plantillas `.env.example` sin valores reales. Los contenedores corren como usuario no root, con sistema de archivos de solo lectura y límites de memoria y CPU.

### 5.4 Resiliencia

Cada contenedor define política de reinicio, y checks-svc incorpora healthcheck en su imagen. El diseño prevé que, al detener un servicio, su ruta responda con error en el gateway mientras el monolito continúa operando, y que la reversión completa se logre cambiando el destino de la ruta en Nginx y recargando la configuración. Los experimentos de caída y recuperación quedaron pendientes de ejecución.

## 6. Mediciones

### 6.1 Metodología

Herramienta ApacheBench (`ab`), 200 peticiones con concurrencia 4, sobre la misma VM y la misma base de datos para ambos escenarios, de forma consecutiva y sin otra carga activa.

**Advertencia metodológica:** el monolito se ejecuta sobre el servidor de desarrollo de Django (WSGIServer), más lento que un servidor de producción. La comparación es válida como referencia relativa, pero la diferencia en un despliegue productivo sería menor.

### 6.2 Resultados

| Escenario | Peticiones/s | Latencia media | p95 | Fallidas |
|---|---:|---:|---:|---:|
| Monolito — GET `/api/v3/checks/` | 15,21 | 263,0 ms | 413 ms | 0 |
| checks-svc — GET `/api/v3/checks/` | 20,33 | 196,8 ms | 283 ms | 0 |

Salidas crudas en `cna/benchmark/`.

### 6.3 Análisis

El microservicio atiende un 34 % más de peticiones por segundo y responde con un 25 % menos de latencia media, con una dispersión menor en el percentil 95. La diferencia es consistente con el menor peso del stack: FastAPI sobre un servidor ASGI frente al stack completo de Django con su capa ORM y su middleware. No se observaron fallos en ninguno de los dos escenarios, lo que confirma que el microservicio sostiene la carga con el mismo contrato que el original.

Las mediciones de ping-svc y alerts-svc quedaron pendientes.

## 7. Conclusiones

**Qué mejoró.** El servicio extraído muestra mejor rendimiento y latencia más estable. La contenerización permite desplegarlo y reemplazarlo sin afectar al monolito, y cada servicio puede evolucionar y escalar por separado.

**Qué se volvió más complejo.** Hay más piezas que operar, y el gateway pasa a ser un punto único de falla. La base compartida mantiene acoplados a los servicios por el esquema.

**Limitaciones.** Una sola VM, base compartida en lugar de una por servicio, sin broker, el monolito medido sobre un servidor de desarrollo, y la integración no validada de extremo a extremo.

**Trabajo futuro.** Completar alerts-svc, validar la integración, migrar a base por servicio, incorporar un broker para desacoplar la comunicación (contrato ya diseñado en `cna/contracts/asyncapi.yaml`) y escalar horizontalmente los servicios de mayor tráfico.

## 8. Matriz de evidencias

| Prueba | Evidencia | Ítem | Descripción | Resultado |
|---|---|---|---|---|
| P26 | F5-E1 | A1 | Tablas de la base vía `information_schema` | 23 tablas verificadas |
| P27 | F5-E2 | A1 | Matriz de acoplamiento tabla × servicio | `api_check` y `api_flip` compartidas por los tres |
| P28 | F5-E3 | A1 | Mapa de contextos (DDD) | Núcleo compartido |
| P29 | F5-E4 | A3 | Contratos OpenAPI validados | 0 errores en ambos |
| P30 | F5-E5 | A4 | Diagrama C4 nivel 1 | Publicado |
| P31 | F5-E6 | A4 | Diagrama C4 nivel 2 | Publicado |
| P32 | F5-E7 | A4 | Secuencias con caminos de error | 401 y 404 documentados |
| P33 | F6-E1 | B2 | Pruebas automatizadas de checks-svc | 15 pruebas, todas pasan |
| P34 | F6-E2 | B2 | `/healthz` y `/readyz` | Responden correctamente |
| P35 | F6-E3 | B2 | `/metrics` en formato Prometheus | Contador e histograma presentes |
| P36 | F6-E4 | B2 | Logs JSON y propagación de `X-Request-ID` | Verificado |
| P37 | F6-E5 | B3 | `docker inspect`: usuario, límites, healthcheck | uid 10001, 256 MB, 0.5 CPU, solo lectura, healthy |
| P38 | F7-E1 | C2 | Medición comparativa monolito vs checks-svc | 20,3 vs 15,2 peticiones/s |

Evidencias detalladas en `cna/docs/`.

## 9. Estado de la entrega

| Componente | Estado |
|---|---|
| Bloque I completo (A1 a A5) | Entregado |
| checks-svc | Completo, contenerizado, probado y medido |
| ping-svc | Completo y contenerizado |
| alerts-svc | En desarrollo |
| Compose y gateway Nginx | Configuración publicada, no validada de extremo a extremo |
| Mediciones | Completas para checks-svc; pendientes para los otros servicios |
| Experimentos de resiliencia | Pendientes |
