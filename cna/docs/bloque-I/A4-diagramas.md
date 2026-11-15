# Bloque I – A4: Modelo C4 y Diagramas de Secuencia

El modelo C4 describe el sistema en niveles de detalle crecientes. El **nivel 1** muestra el sistema como una sola caja y quiénes interactúan con él. El **nivel 2** abre esa caja y muestra las piezas desplegadas y cómo se comunican.

## F5-E5: C4 Nivel 1 — Contexto

```mermaid
flowchart TB
    admin([Usuario administrador<br/>gestiona los checks])
    agent([Trabajo programado / cron<br/>envia los pings])
    sistema[Plataforma Healthchecks<br/>monolito + microservicios]
    canales[Canales de notificacion<br/>correo y otros]

    admin -->|crea y edita checks via API| sistema
    agent -->|avisa que se ejecuto| sistema
    sistema -->|notifica cuando un check vence| canales
```

**Quiénes participan:** el usuario administrador define qué tareas vigilar; los trabajos programados avisan cada vez que se ejecutan correctamente; y el sistema notifica hacia afuera cuando una tarea deja de avisar.

## F5-E6: C4 Nivel 2 — Contenedores

```mermaid
flowchart TB
    admin([Usuario]) -->|HTTPS| nginx[Nginx<br/>API Gateway]
    agent([cron / trabajo]) -->|HTTPS| nginx

    nginx -->|/api/v3/checks/| checks[checks-svc<br/>FastAPI - contenedor<br/>puerto 8001]
    nginx -->|/ping/uuid| ping[ping-svc<br/>FastAPI - contenedor]
    nginx -->|rutas no migradas| mono[Monolito Healthchecks<br/>Django - puerto 8000]

    alerts[alerts-svc<br/>FastAPI - contenedor<br/>proceso en segundo plano]
    db[(PostgreSQL<br/>base compartida)]
    canales[Canales de notificacion]

    checks --> db
    ping --> db
    alerts --> db
    mono --> db
    alerts -->|envia alertas| canales
```

**Coherencia con lo desplegado:** cada caja corresponde a un contenedor real del `docker-compose`, salvo el monolito y PostgreSQL, que corren directamente en la VM. Nginx es el único punto de entrada expuesto; los servicios no publican puertos al exterior. alerts-svc no recibe tráfico HTTP porque es un proceso en segundo plano, por eso no cuelga de Nginx.

## F5-E7a: Secuencia — Crear un check, con camino de error 401

```mermaid
sequenceDiagram
    participant C as Cliente
    participant N as Nginx
    participant S as checks-svc
    participant DB as PostgreSQL

    C->>N: POST /api/v3/checks/ con X-Api-Key y JSON
    N->>S: reenvia la peticion
    S->>S: valida el cuerpo con Pydantic
    S->>DB: SELECT id FROM accounts_project WHERE api_key = clave

    alt Clave valida
        DB-->>S: id del proyecto
        S->>DB: INSERT INTO api_check
        DB-->>S: check creado
        S-->>N: 201 Created con el JSON del check
        N-->>C: 201 Created
    else Clave ausente o invalida
        DB-->>S: sin resultados
        S-->>N: 401 Unauthorized
        N-->>C: 401 Unauthorized
    end
```

**Camino de error:** si la clave no existe en `accounts_project`, el servicio corta antes de tocar la tabla `api_check`. No se crea nada y el cliente recibe 401. La validación de autenticación ocurre siempre antes de cualquier escritura.

## F5-E7b: Secuencia — Recibir un ping y disparar una alerta, con camino de error 404

```mermaid
sequenceDiagram
    participant J as Trabajo / cron
    participant N as Nginx
    participant P as ping-svc
    participant DB as PostgreSQL
    participant A as alerts-svc

    J->>N: GET /ping/uuid
    N->>P: reenvia la peticion
    P->>DB: SELECT id FROM api_check WHERE code = uuid

    alt UUID existe
        DB-->>P: check encontrado
        P->>DB: INSERT INTO api_ping
        P->>DB: UPDATE api_check con el nuevo estado
        P->>DB: INSERT INTO api_flip si el estado cambio
        P-->>N: 200 OK
        N-->>J: 200 OK
    else UUID inexistente
        DB-->>P: sin resultados
        P-->>N: 404 Not Found
        N-->>J: 404 Not Found
    end

    Note over A,DB: Mas tarde, en segundo plano
    A->>DB: busca checks vencidos y flips sin procesar
    DB-->>A: lista de checks caidos
    A->>DB: INSERT INTO api_notification
    A->>A: envia la alerta por el canal configurado
```

**Camino de error:** un UUID que no existe devuelve 404 y no genera ninguna fila, igual que en el monolito. **Interacción entre servicios:** ping-svc escribe el cambio de estado en `api_flip` y alerts-svc lo consume más tarde desde la base, sin llamarse entre sí. Ese es el acoplamiento por base compartida descrito en el ADR-009.
