# ---------- Etapa 1: construcción (instala las librerías) ----------
FROM python:3.12-slim AS builder
WORKDIR /build
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY requirements.txt .
# Solo las librerías que el servicio usa en ejecución (sin pytest ni httpx)
RUN grep -Ev '^(pytest|httpx)' requirements.txt > req-run.txt \
 && pip install --no-cache-dir -r req-run.txt

# ---------- Etapa 2: imagen final (liviana) ----------
FROM python:3.12-slim
# Usuario sin privilegios (no root)
RUN useradd --uid 10001 --no-create-home --shell /usr/sbin/nologin appuser
WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
COPY app/ ./app/
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8001
USER 10001
EXPOSE 8001
# Chequeo de salud: pregunta a /healthz (con python, sin curl)
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD python -c "import os,urllib.request;urllib.request.urlopen('http://localhost:'+os.environ.get('PORT','8001')+'/healthz')" || exit 1
# El puerto sale de la variable PORT
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
