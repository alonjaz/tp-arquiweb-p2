# Bloque I – A5: Plan de Migración y Matriz de Riesgos

## 1. Orden de extracción (de menor a mayor riesgo)

El criterio general es extraer primero lo más aislado y reversible, y dejar para el final lo que produce efectos fuera del sistema.

### Paso 1 — checks-svc

Es un CRUD con contrato claro y el de menor volumen de tráfico. Si algo falla, basta con devolver la ruta al monolito y no se pierde nada, porque la base es la misma.

**Criterio de "hecho":**
- Las pruebas automatizadas pasan (15 pruebas: autenticación, CRUD, salud y métricas).
- `/healthz` y `/readyz` responden correctamente.
- El contrato OpenAPI valida sin errores.
- El GET y el POST a través de Nginx devuelven lo mismo que el monolito, con el mismo contrato.

### Paso 2 — ping-svc

Es la ruta de mayor tráfico del sistema, pero su lógica es simple: recibe un aviso, registra el ping y actualiza el estado del check.

**Criterio de "hecho":**
- Los pings actualizan `api_check`, `api_ping` y `api_flip` igual que el monolito.
- Respeta el límite de retención de pings definido en `accounts_profile`.
- El aislamiento de fallos está probado: si el contenedor cae, la ruta migrada devuelve error y el monolito sigue respondiendo.

### Paso 3 — alerts-svc

Es el más riesgoso porque corre en segundo plano y tiene efectos hacia afuera: envía notificaciones. Un error acá se ve fuera del sistema y no se puede "deshacer".

**Criterio de "hecho":**
- Detecta una caída en un tiempo comparable al del monolito.
- Registra la notificación en `api_notification`.
- No duplica alertas ya enviadas por el monolito.

## 2. Estrategia de reversión (menos de 1 minuto)

Cada ruta migrada apunta a su microservicio desde Nginx. Para volver al monolito:

1. En el bloque de la ruta correspondiente, cambiar el destino:

```nginx
# De esto:
proxy_pass http://checks-svc:8001;

# A esto:
proxy_pass http://monolito:8000;
```

2. Validar la configuración y recargar sin cortar el servicio:

```bash
sudo nginx -t && sudo nginx -s reload
```

La recarga de Nginx toma segundos y no interrumpe las conexiones en curso.

**Por qué la reversión es inmediata:** los microservicios no modificaron el esquema de la base. Al compartir PostgreSQL con el monolito (ADR-009), no hay datos que migrar de vuelta ni sincronización pendiente: el monolito sigue leyendo y escribiendo exactamente las mismas tablas. Esta es la contrapartida positiva del acoplamiento por base compartida.

## 3. Matriz de riesgos

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|:------------:|:-------:|------------|
| Punto único de falla en Nginx (gateway) | Media | Alto | Healthcheck y política de reinicio; reversión al monolito en menos de 1 minuto |
| Falla de la base compartida | Baja | Alto | Es la misma base que ya usaba el monolito, por lo que el riesgo no aumenta respecto del original; respaldos periódicos |
| Acoplamiento por esquema compartido: un cambio de tabla rompe otro servicio | Media | Medio | No modificar el esquema durante la migración; contratos OpenAPI versionados; coordinar cualquier cambio entre los tres servicios |
| Consumo de RAM en una sola VM | Media | Medio | Límite de 256 MB y 0.5 CPU por contenedor; verificación con `docker stats` durante las mediciones |
| Latencia de red entre contenedores y la base | Baja | Bajo | Todos los servicios y la base corren en la misma VM; se mide con `ab` antes y después |
| Secretos compartidos entre servicios | Media | Alto | Configuración solo por variables de entorno en archivos `.env` no versionados; rotación de la clave de API; `.env.example` publicado sin valores reales |
| Acoplamiento temporal sin broker: si un servicio cae, quien lo invoca recibe un error | Media | Medio | Healthcheck y reinicio automático por contenedor; timeouts configurados en Nginx |
| Inestabilidad de la VM de desarrollo (bloqueos del kernel bajo carga) | Media | Bajo | Apagado limpio con `poweroff` en lugar de guardar estado; cargas de prueba moderadas durante las mediciones |

**Nota de adaptación:** el enunciado original incluye el riesgo de "consistencia eventual visible al usuario". En esta arquitectura ese riesgo **no aplica**, porque al no haber broker ni replicación de datos, todas las escrituras ocurren contra la misma base y la consistencia es inmediata (ADR-007 y ADR-009). En su lugar se documenta el riesgo que sí existe en este diseño: el acoplamiento por esquema compartido.

## 4. Estado de la migración

| Servicio | Estado | Observación |
|----------|--------|-------------|
| checks-svc | Extraído y contenerizado | Criterios de "hecho" cumplidos; pendiente la integración final tras Nginx |
| ping-svc | Extraído y contenerizado | Pendiente la integración final |
| alerts-svc | En desarrollo | Último de la secuencia, según el orden de riesgo definido |
| Monolito | Intacto | No se modificó su código, conforme al ADR-006 |
