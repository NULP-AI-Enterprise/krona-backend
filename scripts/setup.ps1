Write-Host "=== Krona Backend Setup ===" -ForegroundColor Cyan
Write-Host ""

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$BackendDir = Split-Path -Parent $ScriptDir
Set-Location $BackendDir

Write-Host "[1/5] Building and starting backend containers..." -ForegroundColor Yellow
docker-compose up -d --build
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: docker-compose failed. Make sure Docker Desktop is running." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "[2/5] Waiting for services to be ready..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

Write-Host ""
Write-Host "[3/5] Running database migrations..." -ForegroundColor Yellow
docker-compose exec backend python manage.py makemigrations users
docker-compose exec backend python manage.py migrate

Write-Host ""
Write-Host "[4/5] Rebuilding Elasticsearch indexes..." -ForegroundColor Yellow
docker-compose exec backend python manage.py search_index --rebuild -f

Write-Host ""
Write-Host "[5/5] Seeding default data (styles & genres)..." -ForegroundColor Yellow
docker-compose exec backend python manage.py setup_defaults

Write-Host ""
Write-Host "=== Backend setup complete! ===" -ForegroundColor Green
Write-Host "Backend:        http://localhost:8000"
Write-Host "Elasticsearch:  http://localhost:9200"
Write-Host "PostgreSQL:     localhost:5431"
