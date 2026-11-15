# Proyecto Integrador II — De Monolito a Cloud Native: Healthchecks

**Materia:** Arquitectura Web — FP-UNA 2026
**Docente:** José Rodrigo Benítez Paredes
**Integrantes:** Jazmín Alonso (checks-svc), Sonia Romero (ping-svc), Diego Castillo (alerts-svc)
**Repositorio:** https://github.com/alonjaz/tp-arquiweb-p2 — tag `v2.0.0`
**Fecha:** noviembre de 2026

## 1. Resumen ejecutivo
*(Media página. Qué se hizo, qué se midió y cuál fue el resultado principal. Se escribe al final, cuando ya estén los números.)*

## 2. Introducción
### 2.1 El monolito de partida
*(Qué es Healthchecks, qué hace, sobre qué corre: Django + PostgreSQL en una VM.)*
### 2.2 Objetivo y alcance
*(Extraer 3 funcionalidades a microservicios sin modificar el monolito. Qué queda fuera del alcance.)*

## 3. Bloque I — Diseño y descomposición
*(Resumen de una página; el detalle está en `cna/docs/bloque-I/`.)*
### 3.1 Análisis del monolito y mapa de contextos → `A1-analisis.md`
### 3.2 Decisiones de arquitectura (ADR-006 a ADR-010) → `A2-adr.md`
### 3.3 Contratos de API → `A3-contratos.md`
### 3.4 Modelo C4 y secuencias → `A4-diagramas.md`
### 3.5 Plan de migración y riesgos → `A5-migracion-riesgos.md`
**Responsable:** Jazmín *(ya entregado)*

## 4. Bloque II — Construcción y despliegue
### 4.1 Infraestructura
*(Recursos de la VM, Docker Engine, red.)* — **Diego**
### 4.2 Microservicios
*(Uno por integrante: qué funcionalidad cubre, endpoints, tablas que toca, pruebas automatizadas, configuración por variables de entorno.)*
- 4.2.1 checks-svc — **Jazmín**
- 4.2.2 ping-svc — **Sonia**
- 4.2.3 alerts-svc — **Diego**
### 4.3 Contenerización
*(Tabla con: imagen, tamaño, usuario, límites, healthcheck y etiqueta de cada servicio.)* — **cada uno la suya**
### 4.4 Integración y gateway
*(docker-compose, rutas de Nginx, despliegue en un comando.)* — **Diego**

## 5. Bloque III — Operación
### 5.1 Resiliencia
*(Qué pasa al detener cada servicio: respuesta del gateway, efecto sobre el monolito, tiempo de recuperación.)* — **Grupo**
### 5.2 Rendimiento comparado
*(Ver sección 6.)* — **Sonia**
### 5.3 Observabilidad
*(Métricas Prometheus, logs JSON, correlación por X-Request-ID.)* — **cada uno la suya**
### 5.4 Seguridad
*(Secretos solo por variables de entorno, rotación de la clave de API, escaneo de imágenes.)* — **Grupo**
### 5.5 Matriz de pruebas y defensa
*(Ver sección 8.)* — **Grupo**

## 6. Mediciones y comparación
### 6.1 Metodología
*(Herramienta `ab`, parámetros usados, misma VM y misma base en ambos casos, cantidad de corridas. Declarar que el monolito corre sobre el servidor de desarrollo de Django, que es más lento que uno de producción.)*
### 6.2 Resultados

| Funcionalidad | Escenario | Req/s | Latencia media (ms) | p95 (ms) | Fallidas |
|---|---|---|---|---|---|
| Gestión de checks (GET) | Monolito | 15,21 | 263,0 | 413 | 0 |
| Gestión de checks (GET) | checks-svc | 20,33 | 196,8 | 283 | 0 |
| Recepción de pings | Monolito | | | | |
| Recepción de pings | ping-svc | | | | |
| Detección de caída | Monolito | | | | |
| Detección de caída | alerts-svc | | | | |

### 6.3 Análisis
*(Interpretar con prudencia: citar la variación y relacionarla con el consumo de CPU y memoria observado. No afirmar causas que las mediciones no demuestren.)*

## 7. Conclusiones
### 7.1 Qué mejoró y qué empeoró
### 7.2 Limitaciones de este trabajo
*(Una sola VM, base compartida, sin broker, servidor de desarrollo en el monolito.)*
### 7.3 Trabajo futuro
*(Base por servicio, broker para desacoplar, escalado horizontal.)*

## 8. Matriz de evidencias

| Prueba | Evidencia | Bloque | Ítem | Descripción | Resultado |
|---|---|---|---|---|---|
| P26 | F5-E1 | I | A1 | Tablas de la base vía information_schema | OK |
| P27 | F5-E2 | I | A1 | Matriz de acoplamiento | OK |
| P28 | F5-E3 | I | A1 | Mapa de contextos | OK |
| P29 | F5-E4 | I | A3 | Contrato OpenAPI validado | OK |
| P30 | F5-E5 | I | A4 | C4 nivel 1 | OK |
| P31 | F5-E6 | I | A4 | C4 nivel 2 | OK |
| P32 | F5-E7 | I | A4 | Secuencias con caminos de error | OK |
| … | | | | *(continuar con las evidencias de los Bloques II y III)* | |

## 9. Anexos
*(Enlaces a los documentos del Bloque I, a los contratos y a los resultados crudos de las mediciones.)*
