# =============================================================================
# Intent Engine - Docker Compose Startup Script (Windows PowerShell)
# =============================================================================
# Usage:
#   .\docker-start.ps1 start              # Start all services
#   .\docker-start.ps1 start-basic        # Start basic services only
#   .\docker-start.ps1 start-full         # Start with Go services
#   .\docker-start.ps1 start-monitoring   # Start with monitoring
#   .\docker-start.ps1 stop               # Stop all services
#   .\docker-start.ps1 restart            # Restart all services
#   .\docker-start.ps1 logs               # View logs
#   .\docker-start.ps1 status             # Check status
#   .\docker-start.ps1 clean              # Remove containers and volumes
#   .\docker-start.ps1 health             # Check health of all services
# =============================================================================

#Requires -RunAsAdministrator

param(
    [Parameter(Position=0)]
    [ValidateSet('start', 'start-basic', 'start-full', 'start-monitoring', 'start-all', 'stop', 'restart', 'logs', 'logs-api', 'logs-db', 'status', 'health', 'clean', 'clean-volumes', 'rebuild', 'shell-api', 'shell-db', 'shell-redis', 'help')]
    [string]$Command = 'help'
)

# Colors
function Write-Info { Write-Host "[INFO] $args" -ForegroundColor Blue }
function Write-Success { Write-Host "[SUCCESS] $args" -ForegroundColor Green }
function Write-Warning { Write-Host "[WARNING] $args" -ForegroundColor Yellow }
function Write-Error-Custom { Write-Host "[ERROR] $args" -ForegroundColor Red }

# Banner
function Write-Banner {
    Write-Host ""
    Write-Host "╔═══════════════════════════════════════════════════════════╗" -ForegroundColor Blue
    Write-Host "║           Intent Engine - Docker Compose                  ║" -ForegroundColor Blue
    Write-Host "║     Privacy-First Intent-Driven Advertising Platform      ║" -ForegroundColor Blue
    Write-Host "╚═══════════════════════════════════════════════════════════╝" -ForegroundColor Blue
    Write-Host ""
}

# Usage
function Write-Usage {
    Write-Host @"
Usage: .\docker-start.ps1 <command>

Commands:
  start              Start all core services
  start-basic        Start basic services (API, DB, Redis, Qdrant, SearXNG)
  start-full         Start with Go services (crawler, indexer, search APIs)
  start-monitoring   Start with monitoring (Prometheus, Grafana)
  start-all          Start everything (core + Go + monitoring)
  stop               Stop all services
  restart            Restart all services
  logs               View logs (follow mode)
  logs-api           View API logs only
  logs-db            View database logs only
  status             Check service status
  health             Check health of all services
  clean              Stop and remove all containers and volumes
  clean-volumes      Stop and remove volumes only
  rebuild            Rebuild all containers
  shell-api          Open shell in API container
  shell-db           Open psql shell in database
  shell-redis        Open redis-cli shell
  help               Show this help message

Examples:
  .\docker-start.ps1 start
  .\docker-start.ps1 start-full
  .\docker-start.ps1 logs
  .\docker-start.ps1 health
"@
}

# Check prerequisites
function Test-Prerequisites {
    Write-Info "Checking prerequisites..."

    # Check Docker
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        Write-Error-Custom "Docker is not installed. Please install Docker Desktop first."
        exit 1
    }

    # Check Docker Compose
    $dockerComposeCmd = $null
    if (Get-Command docker-compose -ErrorAction SilentlyContinue) {
        $dockerComposeCmd = "docker-compose"
    } elseif (docker compose version -ErrorAction SilentlyContinue) {
        $dockerComposeCmd = "docker compose"
    }

    if (-not $dockerComposeCmd) {
        Write-Error-Custom "Docker Compose is not installed. Please install Docker Desktop first."
        exit 1
    }

    # Check if .env file exists
    if (-not (Test-Path ".env")) {
        Write-Warning ".env file not found. Copying from .env.docker..."
        Copy-Item ".env.docker" ".env"
        Write-Success ".env file created. Please review and customize it."
    }

    Write-Success "Prerequisites check passed."
}

# Setup environment
function Setup-Env {
    if (-not (Test-Path ".env")) {
        Write-Info "Creating .env file from template..."
        Copy-Item ".env.docker" ".env"
    }

    # Generate SECRET_KEY if not set
    $envContent = Get-Content ".env" -Raw
    if ($envContent -match "SECRET_KEY=change-this-to-a-secure-random-string" -or -not ($envContent -match "SECRET_KEY=.+")) {
        Write-Info "Generating secure SECRET_KEY..."
        $secretKey = -join ((65..90) + (97..122) + (48..57) + [int[]][char[]]"-_" | Get-Random -Count 32 | ForEach-Object {[char]$_})
        if ($envContent -match "SECRET_KEY=.+") {
            $envContent = $envContent -replace "SECRET_KEY=.*", "SECRET_KEY=$secretKey"
        } else {
            $envContent += "`nSECRET_KEY=$secretKey"
        }
        $envContent | Set-Content ".env" -NoNewline
    }

    # Generate SEARXNG_SECRET_KEY if not set
    if ($envContent -match "^SEARXNG_SECRET_KEY=$" -or -not ($envContent -match "^SEARXNG_SECRET_KEY=.+")) {
        Write-Info "Generating SEARXNG_SECRET_KEY..."
        $searxngSecret = -join ((48..57) + (97..102) | Get-Random -Count 64 | ForEach-Object {[char]$_})
        if ($envContent -match "^SEARXNG_SECRET_KEY=.*") {
            $envContent = $envContent -replace "^SEARXNG_SECRET_KEY=.*", "SEARXNG_SECRET_KEY=$searxngSecret"
        } else {
            $envContent += "`nSEARXNG_SECRET_KEY=$searxngSecret"
        }
        $envContent | Set-Content ".env" -NoNewline
    }
}

# Get docker-compose command
function Get-DockerComposeCmd {
    if (Get-Command docker-compose -ErrorAction SilentlyContinue) {
        return "docker-compose"
    } elseif (docker compose version -ErrorAction SilentlyContinue) {
        return "docker compose"
    }
    return "docker-compose"
}

# Start services
function Start-Services {
    param([string]$Profile)

    $dockerComposeCmd = Get-DockerComposeCmd

    if ($Profile) {
        Write-Info "Starting services with profile: $Profile..."
        Invoke-Expression "$dockerComposeCmd up -d --profile $Profile"
    } else {
        Write-Info "Starting core services..."
        Invoke-Expression "$dockerComposeCmd up -d"
    }

    Write-Success "Services started successfully!"
    Write-Host ""
    Write-Info "Waiting for services to be ready (this may take 1-2 minutes)..."
    Start-Sleep -Seconds 30
}

# Stop services
function Stop-Services {
    Write-Info "Stopping all services..."

    $dockerComposeCmd = Get-DockerComposeCmd
    Invoke-Expression "$dockerComposeCmd down"

    Write-Success "Services stopped."
}

# Show status
function Show-Status {
    Write-Info "Service Status:"
    Write-Host ""

    $dockerComposeCmd = Get-DockerComposeCmd
    Invoke-Expression "$dockerComposeCmd ps"
}

# Show logs
function Show-Logs {
    param([string]$Service)

    $dockerComposeCmd = Get-DockerComposeCmd

    if ($Service) {
        Invoke-Expression "$dockerComposeCmd logs -f $Service"
    } else {
        Invoke-Expression "$dockerComposeCmd logs -f"
    }
}

# Check health
function Check-Health {
    Write-Info "Checking service health..."
    Write-Host ""

    # Check API
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/health/live" -TimeoutSec 5 -UseBasicParsing
        if ($response.StatusCode -eq 200) {
            Write-Success "✓ API is healthy"
        } else {
            Write-Error-Custom "✗ API is not responding"
        }
    } catch {
        Write-Error-Custom "✗ API is not responding"
    }

    # Check PostgreSQL
    try {
        docker exec intent-engine-postgres pg_isready -U intent_user 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Write-Success "✓ PostgreSQL is healthy"
        } else {
            Write-Error-Custom "✗ PostgreSQL is not responding"
        }
    } catch {
        Write-Error-Custom "✗ PostgreSQL is not responding"
    }

    # Check Redis
    try {
        docker exec intent-engine-redis valkey-cli ping 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Write-Success "✓ Redis is healthy"
        } else {
            Write-Error-Custom "✗ Redis is not responding"
        }
    } catch {
        Write-Error-Custom "✗ Redis is not responding"
    }

    # Check Qdrant
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:6333/" -TimeoutSec 5 -UseBasicParsing
        if ($response.StatusCode -eq 200) {
            Write-Success "✓ Qdrant is healthy"
        } else {
            Write-Warning "✗ Qdrant is not responding (may be disabled)"
        }
    } catch {
        Write-Warning "✗ Qdrant is not responding (may be disabled)"
    }

    # Check SearXNG
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8080/healthz" -TimeoutSec 5 -UseBasicParsing
        if ($response.StatusCode -eq 200) {
            Write-Success "✓ SearXNG is healthy"
        } else {
            Write-Warning "✗ SearXNG is not responding (may still be starting)"
        }
    } catch {
        Write-Warning "✗ SearXNG is not responding (may still be starting)"
    }

    # Check Go Search API
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8081/health" -TimeoutSec 5 -UseBasicParsing
        if ($response.StatusCode -eq 200) {
            Write-Success "✓ Go Search API is healthy"
        } else {
            Write-Info "○ Go Search API is not responding (may be disabled)"
        }
    } catch {
        Write-Info "○ Go Search API is not responding (may be disabled)"
    }

    # Check Go Unified Search API
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8082/health" -TimeoutSec 5 -UseBasicParsing
        if ($response.StatusCode -eq 200) {
            Write-Success "✓ Go Unified Search API is healthy"
        } else {
            Write-Info "○ Go Unified Search API is not responding (may be disabled)"
        }
    } catch {
        Write-Info "○ Go Unified Search API is not responding (may be disabled)"
    }

    # Check Prometheus
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:9090/-/healthy" -TimeoutSec 5 -UseBasicParsing
        if ($response.StatusCode -eq 200) {
            Write-Success "✓ Prometheus is healthy"
        } else {
            Write-Info "○ Prometheus is not responding (may be disabled)"
        }
    } catch {
        Write-Info "○ Prometheus is not responding (may be disabled)"
    }

    # Check Grafana
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:3000/api/health" -TimeoutSec 5 -UseBasicParsing
        if ($response.StatusCode -eq 200) {
            Write-Success "✓ Grafana is healthy"
        } else {
            Write-Info "○ Grafana is not responding (may be disabled)"
        }
    } catch {
        Write-Info "○ Grafana is not responding (may be disabled)"
    }

    Write-Host ""
    Write-Info "Health check complete!"
}

# Clean all
function Clean-All {
    $confirm = Read-Host "This will remove all containers and volumes! Are you sure? (y/N)"
    if ($confirm -ne 'y' -and $confirm -ne 'Y') {
        Write-Info "Aborted."
        exit 0
    }

    Write-Info "Stopping and removing all containers and volumes..."

    $dockerComposeCmd = Get-DockerComposeCmd
    Invoke-Expression "$dockerComposeCmd down -v --remove-orphans"

    Write-Success "Cleanup complete."
}

# Clean volumes
function Clean-Volumes {
    $confirm = Read-Host "This will remove all volumes! Are you sure? (y/N)"
    if ($confirm -ne 'y' -and $confirm -ne 'Y') {
        Write-Info "Aborted."
        exit 0
    }

    Write-Info "Stopping containers and removing volumes..."

    $dockerComposeCmd = Get-DockerComposeCmd
    Invoke-Expression "$dockerComposeCmd down -v"

    Write-Success "Volumes removed."
}

# Rebuild
function Rebuild {
    Write-Info "Rebuilding all containers..."

    $dockerComposeCmd = Get-DockerComposeCmd
    Invoke-Expression "$dockerComposeCmd build --no-cache"

    Write-Success "Rebuild complete."
}

# Shell API
function Shell-API {
    Write-Info "Opening shell in API container..."
    docker exec -it intent-engine-api /bin/bash
}

# Shell DB
function Shell-DB {
    Write-Info "Opening psql shell in database..."
    docker exec -it intent-engine-postgres psql -U intent_user -d intent_engine
}

# Shell Redis
function Shell-Redis {
    Write-Info "Opening redis-cli shell..."
    docker exec -it intent-engine-redis valkey-cli
}

# Main
Write-Banner

Test-Prerequisites
Setup-Env

switch ($Command) {
    'start' { Start-Services }
    'start-basic' { Start-Services }
    'start-full' {
        Write-Info "Enabling Go services..."
        $env:ENABLE_GO_SERVICES = "true"
        Start-Services -Profile "go-services"
    }
    'start-monitoring' { Start-Services -Profile "monitoring" }
    'start-all' {
        Write-Info "Enabling all optional services..."
        $env:ENABLE_GO_SERVICES = "true"
        Start-Services -Profile "go-services monitoring"
    }
    'stop' { Stop-Services }
    'restart' {
        Stop-Services
        Start-Services
    }
    'logs' { Show-Logs }
    'logs-api' { Show-Logs -Service "intent-engine-api" }
    'logs-db' { Show-Logs -Service "intent-engine-postgres" }
    'status' { Show-Status }
    'health' { Check-Health }
    'clean' { Clean-All }
    'clean-volumes' { Clean-Volumes }
    'rebuild' { Rebuild }
    'shell-api' { Shell-API }
    'shell-db' { Shell-DB }
    'shell-redis' { Shell-Redis }
    'help' { Write-Usage }
    default {
        Write-Error-Custom "Unknown command: $Command"
        Write-Usage
        exit 1
    }
}
