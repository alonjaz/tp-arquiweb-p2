# TP Integrador II — De Monolito a Cloud Native: Healthchecks

**Arquitectura Web — FP-UNA 2026**
Migración de tres funcionalidades del monolito Healthchecks a microservicios contenerizados, aplicando el patrón Strangler Fig y sin modificar el código del monolito.

| Integrante | Microservicio | Funcionalidad |
|---|---|---|
| Jazmín Alonso | `checks-svc` | API de gestión de checks (`/api/v3/checks/`) |
| Sonia Romero | `ping-svc` | Recepción de pings (`/ping/<uuid>`) |
| Diego Castillo | `alerts-svc` | Evaluación de estados y alertas (proceso en segundo plano) |

## Estructura

```
cna/
├── services/        Código de los tres microservicios
│   ├── checks-svc/
│   ├── ping-svc/
│   └── alerts-svc/
├── contracts/       Contratos OpenAPI de cada servicio
├── deploy/          docker-compose.yml y configuración de Nginx
├── benchmark/       Scripts y resultados de las mediciones con ab
└── docs/            Bloque I (diseño), informe final y evidencias
    └── bloque-I/    A1 análisis, A2 ADR, A3 contratos, A4 diagramas, A5 riesgos
```

## Despliegue en un comando

Requisitos: Docker Engine con el plugin Compose, y PostgreSQL con la base de Healthchecks corriendo en la máquina anfitriona.

```bash
cd cna/deploy
cp .env.example .env     # completar las credenciales de la base
docker compose up -d
```

Verificar que los servicios quedaron saludables:

```bash
docker compose ps
curl -s http://localhost/healthz
```

## Arquitectura

Nginx actúa como punto de entrada y deriva cada ruta a su servicio: `/api/v3/checks/` a checks-svc y `/ping/` a ping-svc. Las rutas no migradas siguen yendo al monolito. alerts-svc no recibe tráfico HTTP porque corre en segundo plano. Los tres servicios comparten la misma base PostgreSQL que el monolito, lo que permite revertir cualquier ruta en menos de un minuto.

Las decisiones de diseño están documentadas en [`cna/docs/bloque-I/A2-adr.md`](cna/docs/bloque-I/A2-adr.md).

## Ramas

- `main` — integración de los microservicios
- `healthchecks-original` — código del monolito, solo lectura
- `feat/checks-svc`, `feat/ping-svc`, `feat/alerts-svc` — ramas de trabajo
