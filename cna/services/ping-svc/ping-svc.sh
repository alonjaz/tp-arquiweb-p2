#!/usr/bin/env bash
# ping-svc.sh - subir (Sonia) y ejecutar (compañero) el microservicio ping-svc.
#
# Uso:
#   ./ping-svc.sh subir      # Sonia: arma ping-svc/ en el repo, commit y push
#   ./ping-svc.sh instalar   # Compañero: clona, crea venv, instala y corre tests
#   ./ping-svc.sh correr     # Compañero: levanta el servicio con uvicorn (usa .env)
#   ./ping-svc.sh docker     # Compañero: build + run en Docker (modo host, como el README)
#
# Variables (se pueden sobreescribir: REPO_URL=... ./ping-svc.sh instalar)
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/alonjaz/tp-arquiweb-p2.git}"   # <- AJUSTAR
REPO_DIR="${REPO_DIR:-tp-arquiweb-p2}"
BRANCH="${BRANCH:-sonia/ping-svc}"
GIT_NAME="${GIT_NAME:-Sonia Romero}"
GIT_EMAIL="${GIT_EMAIL:-}"                 # correo de GitHub de quien sube
SRC="${SRC:-$PWD}"                         # carpeta donde están main.py, db.py, etc.

# ---------------------------------------------------------------- SONIA
# busca el primer archivo existente entre varias rutas candidatas
find_src() {
  for c in "$@"; do [ -f "$SRC/$c" ] && { echo "$SRC/$c"; return 0; }; done
  echo "Falta alguno de: $* (en $SRC)" >&2; exit 1
}
# copia sin fallar si origen y destino son el mismo archivo
put() {
  mkdir -p "$(dirname "$2")"
  if [ -e "$2" ] && [ "$(realpath "$1")" = "$(realpath "$2")" ]; then return 0; fi
  cp "$1" "$2"
}

subir() {
  [ -n "$GIT_EMAIL" ] || { echo "Definí GIT_EMAIL=tu-correo-de-github"; exit 1; }

  # Acepta archivos sueltos (main.py) o ya ordenados (app/main.py, tests/test_main.py)
  MAIN=$(find_src app/main.py main.py)
  DB=$(find_src app/db.py db.py)
  OBS=$(find_src app/observability.py observability.py)
  TST=$(find_src tests/test_main.py test_main.py)
  REQ=$(find_src requirements.txt)
  REQD=$(find_src requirements-dev.txt)
  RDM=$(find_src README.md)
  GI=$(find_src .gitignore _gitignore)
  DI=$(find_src .dockerignore _dockerignore)

  # Si se ejecuta dentro de un repo git, se usa ese; si no, se clona
  if ROOT=$(git -C "$SRC" rev-parse --show-toplevel 2>/dev/null); then
    echo "Usando repo existente: $ROOT"
  else
    [ -d "$REPO_DIR/.git" ] || git clone "$REPO_URL" "$REPO_DIR"
    ROOT=$(realpath "$REPO_DIR")
  fi
  cd "$ROOT"
  git config user.name "$GIT_NAME"
  git config user.email "$GIT_EMAIL"
  git checkout "$BRANCH" 2>/dev/null || git checkout -b "$BRANCH"

  D="$ROOT/ping-svc"
  put "$MAIN" "$D/app/main.py"
  put "$DB"   "$D/app/db.py"
  put "$OBS"  "$D/app/observability.py"
  touch "$D/app/__init__.py"
  put "$TST"  "$D/tests/test_main.py"
  put "$REQ"  "$D/requirements.txt"
  put "$REQD" "$D/requirements-dev.txt"
  put "$RDM"  "$D/README.md"
  put "$GI"   "$D/.gitignore"
  put "$DI"   "$D/.dockerignore"

  cat > "$D/pytest.ini" <<'EOF'
[pytest]
pythonpath = .
testpaths = tests
EOF

  cat > "$D/.env.example" <<'EOF'
# Copiar a .env y completar. NUNCA subir .env
DATABASE_URL=postgresql://USUARIO:CLAVE@127.0.0.1:5432/NOMBRE_BD
HOST=127.0.0.1
PORT=8001
WORKERS=2
LOG_LEVEL=INFO
EOF

  cat > "$D/Dockerfile" <<'EOF'
FROM python:3.12-slim AS build
WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.12-slim
RUN useradd --system --uid 10001 --no-create-home app
COPY --from=build /install /usr/local
WORKDIR /srv
COPY app ./app
ENV PYTHONUNBUFFERED=1 PROMETHEUS_MULTIPROC_DIR=/prom \
    HOST=127.0.0.1 PORT=8001 WORKERS=2
USER 10001
HEALTHCHECK --interval=15s --timeout=3s --retries=3 CMD ["python","-c","import os,urllib.request as u;u.urlopen('http://127.0.0.1:%s/healthz'%os.environ['PORT'])"]
CMD ["sh","-c","exec uvicorn app.main:app --host $HOST --port $PORT --workers $WORKERS"]
EOF

  # Sin secretos en el repo
  git add ping-svc
  if git ls-files --cached | grep -E '(^|/)\.env$'; then
    echo "ERROR: .env está en el índice"; exit 1
  fi
  git commit -m "ping-svc: microservicio de recepción de pings (FastAPI + PostgreSQL)" \
    || echo "(nada nuevo para commitear)"
  git push -u origin "$BRANCH"
  echo "Listo. Rama subida: $BRANCH"
}

# ---------------------------------------------------------- COMPAÑERO
instalar() {
  [ -d "$REPO_DIR/.git" ] || git clone "$REPO_URL" "$REPO_DIR"
  cd "$REPO_DIR"
  git fetch origin
  git checkout "$BRANCH"
  git pull origin "$BRANCH"
  cd ping-svc
  python3 -m venv .venv
  # shellcheck disable=SC1091
  . .venv/bin/activate
  pip install --upgrade pip
  pip install -r requirements-dev.txt
  python -m pytest -v          # no necesita base de datos (usa mocks)
  [ -f .env ] || cp .env.example .env
  echo "Tests OK. Editá ping-svc/.env con USUARIO, CLAVE y NOMBRE_BD y luego: ./ping-svc.sh correr"
}

correr() {
  cd "$REPO_DIR/ping-svc"
  # shellcheck disable=SC1091
  . .venv/bin/activate
  set -a; . ./.env; set +a
  echo "Probá en otra terminal:"
  echo "  curl -i http://127.0.0.1:${PORT:-8001}/healthz"
  echo "  curl -i http://127.0.0.1:${PORT:-8001}/readyz"
  echo "  curl -i http://127.0.0.1:${PORT:-8001}/ping/<UUID_DE_UN_CHECK>"
  echo "  curl -s http://127.0.0.1:${PORT:-8001}/metrics | head"
  exec uvicorn app.main:app --host "${HOST:-127.0.0.1}" --port "${PORT:-8001}"
}

docker_run() {
  cd "$REPO_DIR/ping-svc"
  docker build -t ping-svc:1.0.0 .
  docker rm -f ping-svc 2>/dev/null || true
  docker run -d --name ping-svc --network host --env-file .env \
    --read-only --tmpfs /prom:rw,mode=1777 --memory 256m \
    --restart unless-stopped ping-svc:1.0.0
  sleep 3
  curl -i "http://127.0.0.1:${PORT:-8001}/readyz"
}

case "${1:-}" in
  subir)     subir ;;
  instalar)  instalar ;;
  correr)    correr ;;
  docker)    docker_run ;;
  *) sed -n '2,9p' "$0"; exit 1 ;;
esac
