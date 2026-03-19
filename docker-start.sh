#!/bin/bash
# =============================================================================
# Intent Engine - Docker Compose Startup Script (Linux/Mac)
# =============================================================================
# Usage:
#   ./docker-start.sh start              # Start all services
#   ./docker-start.sh start-basic        # Start basic services only
#   ./docker-start.sh start-full         # Start with Go services
#   ./docker-start.sh start-monitoring   # Start with monitoring
#   ./docker-start.sh stop               # Stop all services
#   ./docker-start.sh restart            # Restart all services
#   ./docker-start.sh logs               # View logs
#   ./docker-start.sh status             # Check status
#   ./docker-start.sh clean              # Remove containers and volumes
#   ./docker-start.sh health             # Check health of all services
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_banner() {
    echo -e "${BLUE}"
    echo "╔═══════════════════════════════════════════════════════════╗"
    echo "║           Intent Engine - Docker Compose                  ║"
    echo "║     Privacy-First Intent-Driven Advertising Platform      ║"
    echo "╚═══════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

print_usage() {
    echo "Usage: $0 <command> [options]"
    echo ""
    echo "Commands:"
    echo "  start              Start all core services"
    echo "  start-basic        Start basic services (API, DB, Redis, Qdrant, SearXNG)"
    echo "  start-full         Start with Go services (crawler, indexer, search APIs)"
    echo "  start-monitoring   Start with monitoring (Prometheus, Grafana)"
    echo "  start-all          Start everything (core + Go + monitoring)"
    echo "  stop               Stop all services"
    echo "  restart            Restart all services"
    echo "  logs               View logs (follow mode)"
    echo "  logs-api           View API logs only"
    echo "  logs-db            View database logs only"
    echo "  status             Check service status"
    echo "  health             Check health of all services"
    echo "  clean              Stop and remove all containers and volumes"
    echo "  clean-volumes      Stop and remove volumes only"
    echo "  rebuild            Rebuild all containers"
    echo "  shell-api          Open shell in API container"
    echo "  shell-db           Open psql shell in database"
    echo "  shell-redis        Open redis-cli shell"
    echo "  help               Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 start"
    echo "  $0 start-full"
    echo "  $0 logs"
    echo "  $0 health"
}

check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install Docker first."
        exit 1
    fi

    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        log_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi

    # Check if .env file exists
    if [ ! -f ".env" ]; then
        log_warning ".env file not found. Copying from .env.docker..."
        cp .env.docker .env
        log_success ".env file created. Please review and customize it."
    fi

    log_success "Prerequisites check passed."
}

setup_env() {
    if [ ! -f ".env" ]; then
        log_info "Creating .env file from template..."
        cp .env.docker .env
    fi

    # Generate secret keys if not set
    if [ -z "$(grep '^SECRET_KEY=' .env)" ] || grep -q "change-this-to-a-secure-random-string" .env; then
        log_info "Generating secure SECRET_KEY..."
        SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))" 2>/dev/null || echo "dev-secret-key-$(date +%s)")
        if grep -q "^SECRET_KEY=" .env; then
            sed -i.bak "s|^SECRET_KEY=.*|SECRET_KEY=$SECRET_KEY|" .env
        else
            echo "SECRET_KEY=$SECRET_KEY" >> .env
        fi
        rm -f .env.bak
    fi

    if [ -z "$(grep '^SEARXNG_SECRET_KEY=' .env)" ] || grep -q "^SEARXNG_SECRET_KEY=$" .env; then
        log_info "Generating SEARXNG_SECRET_KEY..."
        SEARXNG_SECRET=$(openssl rand -hex 32 2>/dev/null || echo "searxng-secret-$(date +%s)")
        if grep -q "^SEARXNG_SECRET_KEY=" .env; then
            sed -i.bak "s|^SEARXNG_SECRET_KEY=.*|SEARXNG_SECRET_KEY=$SEARXNG_SECRET|" .env
        else
            echo "SEARXNG_SECRET_KEY=$SEARXNG_SECRET" >> .env
        fi
        rm -f .env.bak
    fi

    if [ -z "$(grep '^ANONYMIZATION_SALT=' .env)" ] || grep -q "generate-random-salt" .env; then
        log_info "Generating ANONYMIZATION_SALT..."
        SALT=$(python3 -c "import secrets; print(secrets.token_hex(16))" 2>/dev/null || echo "salt-$(date +%s)")
        if grep -q "^ANONYMIZATION_SALT=" .env; then
            sed -i.bak "s|^ANONYMIZATION_SALT=.*|ANONYMIZATION_SALT=$SALT|" .env
        else
            echo "ANONYMIZATION_SALT=$SALT" >> .env
        fi
        rm -f .env.bak
    fi
}

start_services() {
    local profile=$1
    local compose_cmd

    # Determine docker-compose command
    if docker compose version &> /dev/null; then
        compose_cmd="docker compose"
    else
        compose_cmd="docker-compose"
    fi

    if [ -n "$profile" ]; then
        log_info "Starting services with profile: $profile..."
        $compose_cmd up -d --profile "$profile"
    else
        log_info "Starting core services..."
        $compose_cmd up -d
    fi

    log_success "Services started successfully!"
    echo ""
    log_info "Waiting for services to be ready (this may take 1-2 minutes)..."
    sleep 30
}

stop_services() {
    log_info "Stopping all services..."

    if docker compose version &> /dev/null; then
        docker compose down
    else
        docker-compose down
    fi

    log_success "Services stopped."
}

show_status() {
    log_info "Service Status:"
    echo ""

    if docker compose version &> /dev/null; then
        docker compose ps
    else
        docker-compose ps
    fi
}

show_logs() {
    local service=$1

    if docker compose version &> /dev/null; then
        if [ -n "$service" ]; then
            docker compose logs -f "$service"
        else
            docker compose logs -f
        fi
    else
        if [ -n "$service" ]; then
            docker-compose logs -f "$service"
        else
            docker-compose logs -f
        fi
    fi
}

check_health() {
    log_info "Checking service health..."
    echo ""

    # Check API
    if curl -f http://localhost:8000/health/live &> /dev/null; then
        log_success "✓ API is healthy"
    else
        log_error "✗ API is not responding"
    fi

    # Check PostgreSQL
    if docker exec intent-engine-postgres pg_isready -U intent_user &> /dev/null; then
        log_success "✓ PostgreSQL is healthy"
    else
        log_error "✗ PostgreSQL is not responding"
    fi

    # Check Redis
    if docker exec intent-engine-redis valkey-cli ping &> /dev/null; then
        log_success "✓ Redis is healthy"
    else
        log_error "✗ Redis is not responding"
    fi

    # Check Qdrant
    if curl -f http://localhost:6333/ &> /dev/null; then
        log_success "✓ Qdrant is healthy"
    else
        log_warning "✗ Qdrant is not responding (may be disabled)"
    fi

    # Check SearXNG
    if curl -f http://localhost:8080/healthz &> /dev/null; then
        log_success "✓ SearXNG is healthy"
    else
        log_warning "✗ SearXNG is not responding (may still be starting)"
    fi

    # Check Go Search API (if enabled)
    if curl -f http://localhost:8081/health &> /dev/null; then
        log_success "✓ Go Search API is healthy"
    else
        log_info "○ Go Search API is not responding (may be disabled)"
    fi

    # Check Go Unified Search API (if enabled)
    if curl -f http://localhost:8082/health &> /dev/null; then
        log_success "✓ Go Unified Search API is healthy"
    else
        log_info "○ Go Unified Search API is not responding (may be disabled)"
    fi

    # Check Prometheus (if enabled)
    if curl -f http://localhost:9090/-/healthy &> /dev/null; then
        log_success "✓ Prometheus is healthy"
    else
        log_info "○ Prometheus is not responding (may be disabled)"
    fi

    # Check Grafana (if enabled)
    if curl -f http://localhost:3000/api/health &> /dev/null; then
        log_success "✓ Grafana is healthy"
    else
        log_info "○ Grafana is not responding (may be disabled)"
    fi

    echo ""
    log_info "Health check complete!"
}

clean_all() {
    log_warning "This will remove all containers and volumes!"
    read -p "Are you sure? (y/N): " confirm
    if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
        log_info "Aborted."
        exit 0
    fi

    log_info "Stopping and removing all containers and volumes..."

    if docker compose version &> /dev/null; then
        docker compose down -v --remove-orphans
    else
        docker-compose down -v --remove-orphans
    fi

    log_success "Cleanup complete."
}

clean_volumes() {
    log_warning "This will remove all volumes!"
    read -p "Are you sure? (y/N): " confirm
    if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
        log_info "Aborted."
        exit 0
    fi

    log_info "Stopping containers and removing volumes..."

    if docker compose version &> /dev/null; then
        docker compose down -v
    else
        docker-compose down -v
    fi

    log_success "Volumes removed."
}

rebuild() {
    log_info "Rebuilding all containers..."

    if docker compose version &> /dev/null; then
        docker compose build --no-cache
    else
        docker-compose build --no-cache
    fi

    log_success "Rebuild complete."
}

shell_api() {
    log_info "Opening shell in API container..."
    docker exec -it intent-engine-api /bin/bash
}

shell_db() {
    log_info "Opening psql shell in database..."
    docker exec -it intent-engine-postgres psql -U intent_user -d intent_engine
}

shell_redis() {
    log_info "Opening redis-cli shell..."
    docker exec -it intent-engine-redis valkey-cli
}

# Main script
print_banner

if [ $# -eq 0 ]; then
    print_usage
    exit 0
fi

command=$1
shift

check_prerequisites
setup_env

case $command in
    start)
        start_services
        ;;
    start-basic)
        start_services
        ;;
    start-full)
        log_info "Enabling Go services..."
        export ENABLE_GO_SERVICES=true
        start_services "go-services"
        ;;
    start-monitoring)
        start_services "monitoring"
        ;;
    start-all)
        log_info "Enabling all optional services..."
        export ENABLE_GO_SERVICES=true
        start_services "go-services monitoring"
        ;;
    stop)
        stop_services
        ;;
    restart)
        stop_services
        start_services
        ;;
    logs)
        show_logs
        ;;
    logs-api)
        show_logs "intent-engine-api"
        ;;
    logs-db)
        show_logs "intent-engine-postgres"
        ;;
    status)
        show_status
        ;;
    health)
        check_health
        ;;
    clean)
        clean_all
        ;;
    clean-volumes)
        clean_volumes
        ;;
    rebuild)
        rebuild
        ;;
    shell-api)
        shell_api
        ;;
    shell-db)
        shell_db
        ;;
    shell-redis)
        shell_redis
        ;;
    help|--help|-h)
        print_usage
        ;;
    *)
        log_error "Unknown command: $command"
        print_usage
        exit 1
        ;;
esac
