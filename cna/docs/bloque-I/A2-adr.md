# Bloque I – A2: Registro de Decisiones de Arquitectura (ADR-006 a ADR-010)

Cada ADR sigue el formato del TP I: **Estado, Contexto, Decisión, Consecuencias** y al menos una **alternativa descartada**.

## ADR-006: Estrategia de migración — Strangler Fig

- **Estado:** Aceptado
- **Contexto:** Healthchecks es un monolito Django que debe seguir operando mientras se extraen funcionalidades. No se puede detener el servicio ni reescribirlo de una sola vez.
- **Decisión:** Aplicar el patrón Strangler Fig. Nginx se ubica delante del monolito y desvía ruta por ruta hacia los microservicios: `/api/v3/checks/` hacia checks-svc y `/ping/<uuid>` hacia ping-svc. alerts-svc no recibe tráfico HTTP porque es un proceso en segundo plano. El código del monolito no se modifica.
- **Consecuencias:**
  - (+) Migración gradual y reversible: si un servicio falla, se vuelve a apuntar la ruta al monolito.
  - (+) El cliente no nota el cambio, porque el contrato de la API se mantiene idéntico.
  - (−) Durante la transición conviven dos implementaciones de la misma función y hay que mantener ambas.
  - (−) Nginx se convierte en un punto único de falla.
- **Alternativa descartada:** Reescritura completa (*big bang*). Se descarta por el riesgo alto y porque no permite volver atrás de forma controlada.

## ADR-007: Comunicación síncrona por REST, sin broker

- **Estado:** Aceptado
- **Contexto:** Los tres servicios necesitan compartir información sobre el estado de los checks. La consigna adaptada por la cátedra indica no utilizar un broker de mensajes.
- **Decisión:** Comunicación síncrona por HTTP/REST con JSON y contratos OpenAPI. El estado compartido se resuelve a través de la base de datos común.
- **Consecuencias:**
  - (+) Más simple de construir, depurar y explicar en la defensa.
  - (+) Menor consumo de RAM, al no agregar un contenedor adicional.
  - (−) Acoplamiento temporal: si un servicio está caído, quien lo invoca recibe un error inmediato.
  - (−) No hay reintentos automáticos ni garantía de entrega de mensajes.
- **Alternativa descartada:** Broker de mensajes (RabbitMQ o NATS JetStream). Se descarta por la complejidad operativa y el consumo de memoria en una VM con recursos limitados.

## ADR-008: Orquestación con Docker Compose

- **Estado:** Aceptado
- **Contexto:** La integración final se despliega sobre una única VM con recursos acotados.
- **Decisión:** Usar Docker Compose, con límites de memoria y CPU, healthchecks y política de reinicio por servicio.
- **Consecuencias:**
  - (+) Despliegue en un solo comando (`docker compose up -d`), como exige el TP.
  - (+) Consumo mínimo de recursos frente a un orquestador completo.
  - (−) Sin escalado automático ni alta disponibilidad entre nodos.
  - (−) Si la VM cae, cae todo el sistema: no hay tolerancia a fallos de infraestructura.
- **Alternativa descartada:** k3s o Docker Swarm. Se descartan porque agregan consumo y complejidad operativa que una sola VM no justifica.

## ADR-009: Base de datos PostgreSQL compartida

- **Estado:** Aceptado (decisión indicada por la cátedra)
- **Contexto:** Los servicios operan sobre las tablas del monolito. Según la matriz de acoplamiento del A1, `api_check` y `api_flip` son utilizadas por los tres servicios, y `accounts_project` y `accounts_profile` son tablas globales de cuentas. Separarlas exigiría migrar y sincronizar datos.
- **Decisión:** Mantener una única base PostgreSQL compartida. Cada servicio escribe principalmente en sus propias tablas y valida la autenticación contra `accounts_project`.
- **Consecuencias:**
  - (+) Consistencia inmediata, sin necesidad de sincronizar datos entre bases.
  - (+) Migración más rápida y reversión instantánea (el monolito sigue leyendo las mismas tablas).
  - (−) Acoplamiento por esquema: un cambio en una tabla puede romper a otro servicio.
  - (−) La base es un punto único de falla y un cuello de botella compartido.
- **Alternativa descartada:** *Database per service*. Se descarta por el tiempo disponible y por la necesidad de sincronización que implicaría. Queda registrada como mejora futura.

## ADR-010: Stack tecnológico de los servicios

- **Estado:** Aceptado
- **Contexto:** Cada microservicio puede implementarse en un lenguaje distinto. El TP valora el uso de varios lenguajes como punto adicional, pero la cátedra confirmó que un solo lenguaje es válido.
- **Decisión:** El equipo optó por unificar los tres servicios en Python con FastAPI. checks-svc usa FastAPI + psycopg 3 (con `psycopg_pool`) + Pydantic + prometheus-client. La cátedra confirmó que usar un solo lenguaje es válido, por lo que se priorizó un stack común para los tres servicios.
- **Consecuencias:**
  - (+) FastAPI genera el contrato OpenAPI automáticamente y valida los datos con Pydantic.
  - (+) psycopg 3 se instala sin compilar, a diferencia de psycopg2 en las versiones recientes de Python.
  - (+) Un solo stack para los tres servicios facilita la defensa individual, donde cada integrante debe explicar cualquier servicio.
  - (−) Se renuncia al punto adicional por independencia tecnológica entre lenguajes.
  - (−) No se demuestra en la práctica una de las ventajas de los microservicios (elegir el lenguaje por servicio), aunque la arquitectura igualmente lo permite.
- **Alternativa descartada:** Django REST Framework, el mismo framework del monolito. Se descarta porque es más pesado para un microservicio y arrastraría la estructura del monolito, lo que contradice el objetivo de la extracción.
