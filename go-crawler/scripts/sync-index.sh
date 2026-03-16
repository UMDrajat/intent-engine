#!/bin/sh
# Index Sync Script - Syncs Bleve index from indexer to search API
# Runs periodically to keep search index up-to-date

set -e

INDEXER_PATH="${INDEXER_BLEVE_PATH:-/data/indexer/bleve}"
SEARCH_PATH="${SEARCH_BLEVE_PATH:-/data/bleve}"
SYNC_INTERVAL="${SYNC_INTERVAL:-60}"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

log "Starting index sync service"
log "Indexer path: $INDEXER_PATH"
log "Search path: $SEARCH_PATH"
log "Sync interval: ${SYNC_INTERVAL}s"

# Wait for indexer to have an index
while [ ! -d "$INDEXER_PATH/store" ]; do
    log "Waiting for indexer to create initial index..."
    sleep 5
done

# Initial sync
log "Performing initial index sync..."
mkdir -p "$SEARCH_PATH"
rsync -av --delete "$INDEXER_PATH/" "$SEARCH_PATH/"

log "Initial sync complete. Starting periodic sync (every ${SYNC_INTERVAL}s)..."

# Periodic sync
while true; do
    # Check if indexer path exists
    if [ -d "$INDEXER_PATH/store" ]; then
        # Sync with atomic rename to avoid partial reads
        # We use a sibling directory for temp sync
        TEMP_PATH="${SEARCH_PATH}.tmp"
        
        # Sync to temp directory
        if rsync -av --delete "$INDEXER_PATH/" "$TEMP_PATH/"; then
            # Atomic swap using rsync into target (best for keeping service running)
            log "Applying index update..."
            rsync -av --delete "$TEMP_PATH/" "$SEARCH_PATH/"
            rm -rf "$TEMP_PATH"
            log "Index sync completed successfully"
        else
            log "Warning: Sync failed, retrying next interval"
            rm -rf "$TEMP_PATH"
        fi
    else
        log "Warning: Indexer path not found, skipping sync"
    fi
    
    sleep "$SYNC_INTERVAL"
done
