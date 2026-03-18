#!/bin/bash
set -e

echo "=== Intent Engine All-in-One Container Starting ==="

# Function to log with timestamp
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Optional services configuration
ENABLE_QDRANT="${ENABLE_QDRANT:-false}"
ENABLE_GO_SERVICES="${ENABLE_GO_SERVICES:-false}"

log "Optional services: Qdrant=$ENABLE_QDRANT, Go Services=$ENABLE_GO_SERVICES"

# Function to wait for a service
wait_for_service() {
    local service_name=$1
    local check_command=$2
    local max_attempts=60  # Increased from 30 to 60 (120 seconds) for model loading
    local attempt=1

    log "Waiting for $service_name..."
    while [ $attempt -le $max_attempts ]; do
        if eval "$check_command" > /dev/null 2>&1; then
            log "$service_name is ready!"
            return 0
        fi
        log "Attempt $attempt/$max_attempts - $service_name not ready yet..."
        sleep 2
        attempt=$((attempt + 1))
    done

    log "ERROR: $service_name failed to start after $max_attempts attempts"
    return 1
}

# Initialize PostgreSQL if needed
init_postgres() {
    log "Initializing PostgreSQL..."
    
    # Check if database is already initialized
    if [ -f "$PGDATA/PG_VERSION" ]; then
        log "PostgreSQL data directory already exists, skipping initialization"
        # Fix permissions if needed
        chown -R postgres:postgres "$PGDATA" 2>/dev/null || true
        return 0
    fi

    # Initialize PostgreSQL database cluster as postgres user
    log "Creating PostgreSQL database cluster..."
    
    # Find initdb path
    INITDB_PATH=$(which initdb 2>/dev/null || find /usr -name initdb -type f 2>/dev/null | head -1)
    if [ -z "$INITDB_PATH" ]; then
        INITDB_PATH="/usr/lib/postgresql/*/bin/initdb"
        # Use glob to find the actual path
        for path in /usr/lib/postgresql/*/bin/initdb; do
            if [ -x "$path" ]; then
                INITDB_PATH="$path"
                break
            fi
        done
    fi
    
    log "Using initdb at: $INITDB_PATH"
    
    su postgres -c "$INITDB_PATH -D $PGDATA" || {
        log "ERROR: Failed to initialize PostgreSQL"
        return 1
    }

    # Configure PostgreSQL to listen on all interfaces
    log "Configuring PostgreSQL..."
    cat >> "$PGDATA/postgresql.conf" << EOF
listen_addresses = '*'
port = 5432
max_connections = 100
shared_buffers = 128MB
work_mem = 4MB
maintenance_work_mem = 64MB
effective_cache_size = 512MB
checkpoint_completion_target = 0.9
wal_buffers = 4MB
default_statistics_target = 100
random_page_cost = 1.1
effective_io_concurrency = 200
EOF

    # Configure pg_hba.conf for authentication (trust for local connections)
    cat > "$PGDATA/pg_hba.conf" << EOF
# TYPE  DATABASE        USER            ADDRESS                 METHOD
local   all             all                                     trust
host    all             all             127.0.0.1/32            trust
host    all             all             ::1/128                 trust
host    all             all             0.0.0.0/0               md5
EOF

    log "PostgreSQL initialization complete"
    return 0
}

# Start PostgreSQL
start_postgres() {
    log "Starting PostgreSQL..."
    
    # Ensure proper ownership
    chown -R postgres:postgres "$PGDATA" 2>/dev/null || true
    chown -R postgres:postgres /var/run/postgresql 2>/dev/null || true
    chown -R postgres:postgres /app/data 2>/dev/null || true
    
    # Find pg_ctl path
    PGCTL_PATH=$(which pg_ctl 2>/dev/null || find /usr -name pg_ctl -type f 2>/dev/null | head -1)
    if [ -z "$PGCTL_PATH" ]; then
        for path in /usr/lib/postgresql/*/bin/pg_ctl; do
            if [ -x "$path" ]; then
                PGCTL_PATH="$path"
                break
            fi
        done
    fi
    
    # Create log directory and file
    mkdir -p /app/data
    touch /app/data/postgresql.log
    chown postgres:postgres /app/data/postgresql.log
    
    # Start PostgreSQL in background as postgres user
    su postgres -c "$PGCTL_PATH -D $PGDATA -l /app/data/postgresql.log start" || {
        log "ERROR: Failed to start PostgreSQL"
        return 1
    }

    # Wait for PostgreSQL to be ready
    wait_for_service "PostgreSQL" "pg_isready -h 127.0.0.1 -U $POSTGRES_USER" || return 1

    # Create database and user if they don't exist
    log "Setting up database..."
    
    # Wait a bit more for PostgreSQL to be fully ready
    sleep 2
    
    # Find psql path
    PSQL_PATH=$(which psql 2>/dev/null || find /usr -name psql -type f 2>/dev/null | head -1)
    if [ -z "$PSQL_PATH" ]; then
        for path in /usr/lib/postgresql/*/bin/psql; do
            if [ -x "$path" ]; then
                PSQL_PATH="$path"
                break
            fi
        done
    fi
    
    # Use postgres superuser to create role and database if they don't exist
    # With trust auth, we can connect without password
    
    # Check if user exists
    USER_EXISTS=$(su postgres -c "$PSQL_PATH -h 127.0.0.1 -tAc \"SELECT 1 FROM pg_roles WHERE rolname='$POSTGRES_USER'\"")
    if [ "$USER_EXISTS" != "1" ]; then
        log "Creating database user: $POSTGRES_USER"
        su postgres -c "$PSQL_PATH -h 127.0.0.1 -c \"CREATE ROLE $POSTGRES_USER LOGIN CREATEDB;\""
    fi

    # Check if database exists
    DB_EXISTS=$(su postgres -c "$PSQL_PATH -h 127.0.0.1 -tAc \"SELECT 1 FROM pg_database WHERE datname='$POSTGRES_DB'\"")
    if [ "$DB_EXISTS" != "1" ]; then
        log "Creating database: $POSTGRES_DB"
        su postgres -c "$PSQL_PATH -h 127.0.0.1 -c \"CREATE DATABASE $POSTGRES_DB OWNER $POSTGRES_USER;\""
        su postgres -c "$PSQL_PATH -h 127.0.0.1 -c \"GRANT ALL PRIVILEGES ON DATABASE $POSTGRES_DB TO $POSTGRES_USER;\""
    fi

    log "PostgreSQL started successfully"
    return 0
}

# Start Redis
start_redis() {
    log "Starting Redis..."
    
    # Create Redis data directory
    mkdir -p /app/data/redis
    chown -R redis:redis /app/data/redis 2>/dev/null || chown -R appuser:appuser /app/data/redis 2>/dev/null || true
    
    # Start Redis in background
    log "Starting Redis server..."
    redis-server --daemonize yes \
        --port 6379 \
        --bind 127.0.0.1 \
        --dir /app/data/redis \
        --save 30 1 \
        --loglevel warning \
        --maxmemory 512mb \
        --maxmemory-policy allkeys-lru || {
        log "ERROR: Failed to start Redis"
        return 1
    }

    # Wait for Redis to be ready
    sleep 2
    wait_for_service "Redis" "redis-cli -h 127.0.0.1 -p 6379 ping" || return 1

    log "Redis started successfully"
    return 0
}

# Start SearXNG
start_searxng() {
    log "Starting SearXNG..."

    # Create SearXNG directories
    mkdir -p /etc/searxng

    # Generate secret key if not set
    if [ -z "$SEARXNG_SECRET_KEY" ]; then
        export SEARXNG_SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))" 2>/dev/null || echo "default-secret-key-$(date +%s)")
        log "Generated SearXNG secret key"
    fi

    # Create default settings.yml if it doesn't exist
    if [ ! -f "/etc/searxng/settings.yml" ]; then
        log "Creating default SearXNG settings..."
        # Try to use project's searxng config if available
        if [ -f "/app/app/searxng/settings.yml" ]; then
            cp /app/app/searxng/settings.yml /etc/searxng/settings.yml
        else
            cat > /etc/searxng/settings.yml << EOF
use_default_settings: True
server:
    port: 8080
    bind_address: "127.0.0.1"
    secret_key: "${SEARXNG_SECRET_KEY}"
search:
    safe_search: 0
    autocomplete: ""
EOF
        fi
    fi

    # Fix permissions
    chown -R appuser:appuser /etc/searxng
    mkdir -p /app/data
    chown -R appuser:appuser /app/data

    # Start SearXNG in background as appuser
    su appuser -c "export PYTHONPATH=/usr/local/searxng && export SEARXNG_SETTINGS_PATH=/etc/searxng/settings.yml && nohup python3 /usr/local/searxng/searx/webapp.py > /app/data/searxng.log 2>&1 &"

    SEARXNG_PID=$!
    log "SearXNG started with PID: $SEARXNG_PID"

    # Wait for SearXNG to be ready
    wait_for_service "SearXNG" "curl -f http://127.0.0.1:8080/healthz" || log "WARNING: SearXNG taking longer than expected"

    return 0
}

# Start Qdrant (optional)
start_qdrant() {
    if [ "$ENABLE_QDRANT" != "true" ]; then
        log "Qdrant is disabled (set ENABLE_QDRANT=true to enable)"
        return 0
    fi

    log "Starting Qdrant..."

    # Create Qdrant directories
    mkdir -p /app/data/qdrant
    mkdir -p /qdrant/storage

    # Start Qdrant in background
    nohup /usr/local/bin/qdrant > /app/data/qdrant.log 2>&1 &
    QDRANT_PID=$!
    log "Qdrant started with PID: $QDRANT_PID"

    # Wait for Qdrant to be ready
    wait_for_service "Qdrant" "curl -f http://127.0.0.1:6333/" || log "WARNING: Qdrant taking longer than expected"

    log "Qdrant started successfully"
    return 0
}

# Start Go Search API (optional)
start_go_search_api() {
    if [ "$ENABLE_GO_SERVICES" != "true" ]; then
        log "Go Search API is disabled (set ENABLE_GO_SERVICES=true to enable)"
        return 0
    fi

    log "Starting Go Search API..."

    # Set environment variables for Go Search API
    # Use GO_SEARCH_DB_* variables if set, otherwise fall back to POSTGRES_* variables
    # First, ensure GO_SEARCH_DB_* variables have values (from docker-compose or defaults)
    : "${GO_SEARCH_DB_USER:=$POSTGRES_USER}"
    : "${GO_SEARCH_DB_PASSWORD:=$POSTGRES_PASSWORD}"
    : "${GO_SEARCH_DB_HOST:=127.0.0.1}"
    : "${GO_SEARCH_DB_PORT:=5432}"
    : "${GO_SEARCH_DB_NAME:=$POSTGRES_DB}"
    
    # Export all variables for Go process
    export GO_SEARCH_DB_USER
    export GO_SEARCH_DB_PASSWORD
    export GO_SEARCH_DB_HOST
    export GO_SEARCH_DB_PORT
    export GO_SEARCH_DB_NAME
    export GO_SEARCH_API_PORT="${GO_SEARCH_API_PORT:-8081}"
    
    # Build DATABASE_URL and POSTGRES_DSN from GO_SEARCH_DB_* variables
    export DATABASE_URL="postgresql://${GO_SEARCH_DB_USER}:${GO_SEARCH_DB_PASSWORD}@${GO_SEARCH_DB_HOST}:${GO_SEARCH_DB_PORT}/${GO_SEARCH_DB_NAME}?sslmode=disable"
    export POSTGRES_DSN="${DATABASE_URL}"
    export REDIS_URL="${REDIS_URL:-redis://127.0.0.1:6379/0}"
    export QDRANT_HOST="${QDRANT_HOST:-127.0.0.1}"
    export QDRANT_PORT="${QDRANT_PORT:-6333}"

    log "Go Search API DB Config: user=${GO_SEARCH_DB_USER}, host=${GO_SEARCH_DB_HOST}, port=${GO_SEARCH_DB_PORT}, db=${GO_SEARCH_DB_NAME}"

    # Start Go Search API in background
    nohup /usr/local/bin/search-api > /app/data/go-search-api.log 2>&1 &
    GO_SEARCH_PID=$!
    log "Go Search API started with PID: $GO_SEARCH_PID"

    # Wait for Go Search API to be ready (check on port 8081)
    wait_for_service "Go Search API" "curl -f http://127.0.0.1:${GO_SEARCH_API_PORT:-8081}/health" || log "WARNING: Go Search API taking longer than expected"

    log "Go Search API started successfully"
    return 0
}

# Start Go Unified Search API (optional)
start_go_unified_search() {
    if [ "$ENABLE_GO_SERVICES" != "true" ]; then
        log "Go Unified Search API is disabled (set ENABLE_GO_SERVICES=true to enable)"
        return 0
    fi

    log "Starting Go Unified Search API..."

    # Set environment variables for Go Unified Search API
    # Use GO_SEARCH_DB_* variables if set, otherwise fall back to POSTGRES_* variables
    # First, ensure GO_SEARCH_DB_* variables have values (from docker-compose or defaults)
    : "${GO_SEARCH_DB_USER:=$POSTGRES_USER}"
    : "${GO_SEARCH_DB_PASSWORD:=$POSTGRES_PASSWORD}"
    : "${GO_SEARCH_DB_HOST:=127.0.0.1}"
    : "${GO_SEARCH_DB_PORT:=5432}"
    : "${GO_SEARCH_DB_NAME:=$POSTGRES_DB}"

    # Export all variables for Go process
    export GO_SEARCH_DB_USER
    export GO_SEARCH_DB_PASSWORD
    export GO_SEARCH_DB_HOST
    export GO_SEARCH_DB_PORT
    export GO_SEARCH_DB_NAME
    export GO_UNIFIED_SEARCH_API_PORT="${GO_UNIFIED_SEARCH_API_PORT:-8082}"

    # Build DATABASE_URL and POSTGRES_DSN from GO_SEARCH_DB_* variables
    export DATABASE_URL="postgresql://${GO_SEARCH_DB_USER}:${GO_SEARCH_DB_PASSWORD}@${GO_SEARCH_DB_HOST}:${GO_SEARCH_DB_PORT}/${GO_SEARCH_DB_NAME}?sslmode=disable"
    export POSTGRES_DSN="${DATABASE_URL}"
    # Fix: Use 127.0.0.1 for Redis in aio container (not docker network hostname)
    export REDIS_ADDR="127.0.0.1:6379"
    export REDIS_URL="${REDIS_URL:-redis://127.0.0.1:6379/0}"
    export QDRANT_HOST="${QDRANT_HOST:-127.0.0.1}"
    export QDRANT_PORT="${QDRANT_PORT:-6333}"
    export QDRANT_ADDR="${QDRANT_HOST}:${QDRANT_PORT}"
    export SEARXNG_URL="${SEARXNG_URL:-http://127.0.0.1:8080}"
    export INTENT_ENGINE_API_URL="${INTENT_ENGINE_API_URL:-http://127.0.0.1:8000}"
    export CACHE_ENABLED="${CACHE_ENABLED:-true}"
    export CACHE_TTL_SECONDS="${CACHE_TTL_SECONDS:-3600}"
    export PARALLEL_SEARCH="${PARALLEL_SEARCH:-true}"

    log "Go Unified Search API DB Config: user=${GO_SEARCH_DB_USER}, host=${GO_SEARCH_DB_HOST}, port=${GO_SEARCH_DB_PORT}, db=${GO_SEARCH_DB_NAME}"
    log "Go Unified Search API Redis: ${REDIS_ADDR}, Qdrant: ${QDRANT_ADDR}, SearXNG: ${SEARXNG_URL}"

    # Start Go Unified Search API in background
    nohup /usr/local/bin/unified-search > /app/data/go-unified-search.log 2>&1 &
    GO_UNIFIED_PID=$!
    log "Go Unified Search API started with PID: $GO_UNIFIED_PID"

    # Wait for Go Unified Search API to be ready (check on port 8082)
    wait_for_service "Go Unified Search API" "curl -f http://127.0.0.1:${GO_UNIFIED_SEARCH_API_PORT}/health" || log "WARNING: Go Unified Search API taking longer than expected"

    log "Go Unified Search API started successfully"
    return 0
}

# Start Go Crawler Worker (optional but recommended for search functionality)
start_go_crawler() {
    if [ "$ENABLE_GO_SERVICES" != "true" ]; then
        log "Go Crawler is disabled (set ENABLE_GO_SERVICES=true to enable)"
        return 0
    fi

    log "Starting Go Crawler worker..."

    # Set environment variables for Go Crawler
    : "${GO_SEARCH_DB_USER:=$POSTGRES_USER}"
    : "${GO_SEARCH_DB_PASSWORD:=$POSTGRES_PASSWORD}"
    : "${GO_SEARCH_DB_HOST:=127.0.0.1}"
    : "${GO_SEARCH_DB_PORT:=5432}"
    : "${GO_SEARCH_DB_NAME:=$POSTGRES_DB}"

    # Export all variables for Go process
    export GO_SEARCH_DB_USER
    export GO_SEARCH_DB_PASSWORD
    export GO_SEARCH_DB_HOST
    export GO_SEARCH_DB_PORT
    export GO_SEARCH_DB_NAME
    export DATABASE_URL="postgresql://${GO_SEARCH_DB_USER}:${GO_SEARCH_DB_PASSWORD}@${GO_SEARCH_DB_HOST}:${GO_SEARCH_DB_PORT}/${GO_SEARCH_DB_NAME}?sslmode=disable"
    export REDIS_URL="${REDIS_URL:-redis://127.0.0.1:6379/0}"
    export REDIS_ADDR="127.0.0.1:6379"
    export CRAWLER_CONFIG="${CRAWLER_CONFIG:-/app/go-crawler/config.example.yaml}"

    log "Go Crawler DB Config: user=${GO_SEARCH_DB_USER}, host=${GO_SEARCH_DB_HOST}, port=${GO_SEARCH_DB_PORT}, db=${GO_SEARCH_DB_NAME}"
    log "Go Crawler Redis: ${REDIS_ADDR}"

    # Create crawler data directory
    mkdir -p /app/data/go-crawler
    chown -R appuser:appuser /app/data/go-crawler

    # Setup crawler database schema (run as postgres user)
    log "Setting up crawler database schema..."
    su postgres -c "psql -d ${POSTGRES_DB} -c \"
    DO \$\$ BEGIN
        IF NOT EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'crawled_pages') THEN
            CREATE TABLE crawled_pages (
                id SERIAL PRIMARY KEY,
                url VARCHAR(2048) NOT NULL UNIQUE,
                final_url VARCHAR(2048),
                title VARCHAR(1024),
                content TEXT,
                meta_description TEXT,
                meta_keywords TEXT,
                status_code INTEGER,
                content_type VARCHAR(255),
                content_length INTEGER,
                load_time_ms DOUBLE PRECISION,
                crawl_depth INTEGER DEFAULT 0,
                outbound_links INTEGER DEFAULT 0,
                inbound_links INTEGER DEFAULT 0,
                pagerank DOUBLE PRECISION DEFAULT 0.0,
                language VARCHAR(10) DEFAULT 'en',
                is_indexed BOOLEAN DEFAULT FALSE,
                crawled_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                next_crawl_at TIMESTAMP WITH TIME ZONE,
                content_hash VARCHAR(64),
                simhash VARCHAR(20)
            );
            CREATE INDEX IF NOT EXISTS idx_crawled_pages_url ON crawled_pages(url);
            CREATE INDEX IF NOT EXISTS idx_crawled_pages_title ON crawled_pages(title);
        END IF;
    END
    \$\$;\"" 2>/dev/null || log "WARNING: Could not create crawler tables (may already exist)"

    # Add default seed URLs to Redis (if not already present)
    log "Adding default seed URLs to crawl queue..."
    redis-cli ZADD seed_urls 10 "https://www.python.org/" 10 "https://docs.python.org/3/" 10 "https://realpython.com/" 10 "https://www.w3schools.com/python/" 10 "https://stackoverflow.com/questions/tagged/python" 2>/dev/null || log "WARNING: Could not add seed URLs to Redis"
    
    SEED_COUNT=$(redis-cli ZCARD seed_urls 2>/dev/null || echo "0")
    log "Seed URLs in queue: ${SEED_COUNT}"

    # Define default seed URLs for crawler startup
    DEFAULT_SEED_URLS="https://www.python.org/,https://docs.python.org/3/,https://realpython.com/"

    # Start Go Crawler in background with DATABASE_URL as flag and seed URLs
    cd /app/go-crawler
    nohup /usr/local/bin/go-crawler -postgres="${DATABASE_URL}" -seed="${DEFAULT_SEED_URLS}" > /app/data/go-crawler.log 2>&1 &
    GO_CRAWLER_PID=$!
    log "Go Crawler started with PID: $GO_CRAWLER_PID"

    # Wait for Go Crawler to be ready (check health if available, otherwise just wait)
    sleep 5
    if curl -f http://127.0.0.1:8081/health > /dev/null 2>&1; then
        log "Go Crawler health check passed"
    else
        log "Go Crawler started (no HTTP endpoint - worker-only process)"
    fi

    log "Go Crawler started successfully"
    return 0
}

# Start nginx
start_nginx() {
    log "Starting nginx..."
    
    # Start nginx (needs root or proper capabilities)
    if [ "$(id -u)" = "0" ]; then
        nginx || {
            log "WARNING: nginx failed to start"
            return 1
        }
    else
        # Try to start nginx with sudo or directly
        sudo nginx 2>/dev/null || nginx -g "daemon off;" &
        sleep 2
    fi

    log "nginx started"
    return 0
}

# Run database migrations
run_migrations() {
    log "Running database migrations..."
    
    cd /app
    
    # Set environment for migration tools
    export POSTGRES_HOST=127.0.0.1
    export DATABASE_URL="${DATABASE_URL:-postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@127.0.0.1:5432/${POSTGRES_DB}}"
    
    # Wait for database to be ready
    wait_for_service "PostgreSQL" "pg_isready -h 127.0.0.1 -U $POSTGRES_USER -d $POSTGRES_DB" || return 1

    # Run Python migrations
    python3 /app/scripts/init_db_standalone.py 2>&1 || {
        log "WARNING: init_db_standalone.py failed or doesn't exist"
    }

    # Run SQL migrations if they exist
    for migration_file in /app/infrastructure/database/migrations/*.sql; do
        if [ -f "$migration_file" ]; then
            log "Applying migration: $migration_file"
            PGPASSWORD="$POSTGRES_PASSWORD" psql \
                -h 127.0.0.1 \
                -U "$POSTGRES_USER" \
                -d "$POSTGRES_DB" \
                -f "$migration_file" 2>&1 || {
                log "WARNING: Migration $migration_file had issues (may already be applied)"
            }
        fi
    done

    log "Database migrations complete"
    return 0
}

# Start the main API
start_api() {
    log "Starting Intent Engine API..."
    
    cd /app
    
    # Set environment variables if not already set
    export DATABASE_URL="${DATABASE_URL:-postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@127.0.0.1:5432/${POSTGRES_DB}}"
    export REDIS_URL="${REDIS_URL:-redis://127.0.0.1:6379/0}"
    export SEARXNG_BASE_URL="${SEARXNG_BASE_URL:-http://127.0.0.1:8080}"
    export ENVIRONMENT="${ENVIRONMENT:-production}"
    
    # Start uvicorn with multiple workers
    nohup uvicorn app.main_api:app \
        --host 0.0.0.0 \
        --port 8000 \
        --workers ${WORKERS:-2} > /app/data/api.log 2>&1 &
    
    API_PID=$!
    log "API started with PID: $API_PID"

    # Wait for API to be ready
    wait_for_service "Intent Engine API" "curl -f http://127.0.0.1:8000/health/live" || return 1

    log "Intent Engine API started successfully"
    return 0
}

# Main execution
main() {
    log "Starting all services..."

    # Initialize and start PostgreSQL
    init_postgres || exit 1
    start_postgres || exit 1

    # Start Redis
    start_redis || exit 1

    # Start Qdrant (optional)
    start_qdrant || log "WARNING: Qdrant failed to start"

    # Start SearXNG
    start_searxng || log "WARNING: SearXNG failed to start, continuing without it"

    # Run database migrations BEFORE starting Go services and API
    run_migrations || log "WARNING: Some migrations failed, continuing..."

    # Start Go services (optional) - AFTER migrations
    start_go_search_api || log "WARNING: Go Search API failed to start"
    start_go_unified_search || log "WARNING: Go Unified Search API failed to start"
    start_go_crawler || log "WARNING: Go Crawler failed to start"

    # Start the main API
    start_api || exit 1

    # Start nginx
    start_nginx || log "WARNING: nginx failed to start"

    log "=== All services started successfully ==="
    log "API available at: http://localhost:80"
    log "PostgreSQL: localhost:5432"
    log "Redis: localhost:6379"
    if [ "$ENABLE_QDRANT" = "true" ]; then
        log "Qdrant: localhost:6333"
    fi
    if [ "$ENABLE_GO_SERVICES" = "true" ]; then
        log "Go Search API: localhost:8081"
        log "Go Unified Search API: localhost:8082"
        log "Go Crawler: running (worker process)"
    fi
    log "SearXNG: localhost:8080"

    # Keep container running by waiting on all background processes
    # Use a trap to handle shutdown gracefully
    trap 'log "Shutting down..."; kill $(jobs -p) 2>/dev/null; exit 0' SIGTERM SIGINT

    # Wait forever (or until container is stopped)
    while true; do
        sleep 60
        # Check if API is still running, restart if not
        if ! curl -f http://127.0.0.1:8000/health/live > /dev/null 2>&1; then
            log "WARNING: API health check failed, attempting restart..."
            pkill -f "uvicorn app.main_api:app" || true
            sleep 5
            cd /app
            nohup uvicorn app.main_api:app --host 0.0.0.0 --port 8000 --workers ${WORKERS:-2} > /app/data/api.log 2>&1 &
            log "API restart initiated"
        fi
    done
}

# Run main function
main "$@"
