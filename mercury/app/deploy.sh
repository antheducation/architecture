#!/usr/bin/env bash
# Deploiement de MERCURY CAD AI X.
#   ./deploy.sh local    installation locale et demarrage
#   ./deploy.sh docker   construction et lancement des conteneurs
#   ./deploy.sh test     suite de tests uniquement
set -euo pipefail
cd "$(dirname "$0")"

MODE="${1:-local}"
PORT="${MERCURY_PORT:-8000}"

verifier_python() {
  if ! command -v python3 >/dev/null 2>&1; then
    echo "[X] Python 3 est requis : https://www.python.org/downloads/"
    exit 1
  fi
  local version
  version="$(python3 -c 'import sys; print(sys.version_info[0]*100+sys.version_info[1])')"
  if [ "$version" -lt 310 ]; then
    echo "[X] Python 3.10 minimum requis (detecte : $version)"
    exit 1
  fi
}

case "$MODE" in
  local)
    verifier_python
    echo "[1/4] Environnement isole"
    python3 -m venv .venv
    # shellcheck disable=SC1091
    source .venv/bin/activate
    echo "[2/4] Dependances"
    pip install --quiet --upgrade pip
    pip install --quiet -r requirements.txt
    echo "[3/4] Tests"
    pytest -q
    echo "[4/4] Demarrage sur le port $PORT"
    exec uvicorn API.main:app --host 0.0.0.0 --port "$PORT"
    ;;
  docker)
    command -v docker >/dev/null 2>&1 || { echo "[X] Docker absent"; exit 1; }
    echo "[1/2] Construction"
    docker compose build
    echo "[2/2] Demarrage"
    docker compose up -d
    echo "API   : http://localhost:$PORT"
    echo "Client: http://localhost:8080"
    ;;
  test)
    verifier_python
    pytest -q
    ;;
  *)
    echo "Usage : ./deploy.sh [local|docker|test]"
    exit 1
    ;;
esac
