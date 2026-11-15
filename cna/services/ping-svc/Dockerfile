# ---- build ----
FROM python:3.12-slim AS builder
WORKDIR /build
COPY requirements.txt .
RUN python -m venv /venv && /venv/bin/pip install --no-cache-dir -r requirements.txt

# ---- runtime ----
FROM python:3.12-slim
ENV PATH="/venv/bin:$PATH" PYTHONUNBUFFERED=1 WEB_CONCURRENCY=2 HOST=0.0.0.0 PORT=8000 PROMETHEUS_MULTIPROC_DIR=/prom
RUN useradd --system --uid 10001 --no-create-home appuser
COPY --from=builder /venv /venv
RUN mkdir /prom && chown appuser /prom
WORKDIR /srv
COPY app ./app
USER appuser
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=3s --retries=3 \
  CMD python -c "import os,urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:%s/healthz' % os.environ.get('PORT','8000')).status==200 else 1)"
CMD ["sh", "-c", "exec uvicorn app.main:app --host ${HOST} --port ${PORT} --no-access-log"]
