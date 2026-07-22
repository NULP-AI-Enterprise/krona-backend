#!/bin/bash

echo "=== Krona Backend Setup ==="
echo ""

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$(dirname "$SCRIPT_DIR")"
cd "$BACKEND_DIR"

echo "[1/5] Building and starting backend containers..."
docker-compose up -d --build
if [ $? -ne 0 ]; then
    echo "ERROR: docker-compose failed. Make sure Docker Desktop is running."
    exit 1
fi

echo ""
echo "[2/5] Waiting for services to be ready..."
sleep 10

echo ""
echo "[3/5] Running database migrations..."
docker-compose exec backend python manage.py makemigrations users
docker-compose exec backend python manage.py migrate

echo ""
echo "[4/5] Rebuilding Elasticsearch indexes..."
docker-compose exec backend python manage.py search_index --rebuild -f

echo ""
echo "[5/5] Seeding default data (styles & genres)..."
docker-compose exec backend python manage.py setup_defaults

echo ""
echo "=== Backend setup complete! ==="
echo "Backend:        http://localhost:8000"
echo "Elasticsearch:  http://localhost:9200"
echo "PostgreSQL:     localhost:5431"
