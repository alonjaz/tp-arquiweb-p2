# ---- build ----
FROM python:3.12-slim AS builder
WORKDIR /build
COPY requirements.txt .
RUN python -m venv /venv && /venv/bin/pip install --no-cache-dir -r requirements.txt

# ---- runtime ----
FROM python:3.12-slim
ENV PATH="/venv/bin:$PATH" PYTHONUNBUFFERED=1 WEB_CONCURRENCY=2
RUN useradd --system --uid 10001 --no-create-home appuser
COPY --from=builder /venv /venv
WORKDIR /srv
COPY app ./app
USER appuser
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=3s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/healthz').status==200 else 1)"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
