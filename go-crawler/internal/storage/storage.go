package storage

import (
	"crypto/sha256"
	"database/sql"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"hash/fnv"
	"log"
	"strings"
	"time"

	"github.com/dgraph-io/badger/v4"
	_ "github.com/lib/pq"
	"github.com/itxLikhith/intent-engine/go-crawler/pkg/models"
)

// SimHash generates a 64-bit SimHash for a string (simple implementation)
func SimHash(text string) uint64 {
	// Simple bit-weighting simhash implementation
	v := make([]int, 64)
	words := strings.Fields(strings.ToLower(text))
	
	if len(words) == 0 {
		return 0
	}

	for _, word := range words {
		h := fnv.New64a()
		h.Write([]byte(word))
		hash := h.Sum64()
		
		for i := 0; i < 64; i++ {
			if (hash >> i & 1) == 1 {
				v[i]++
			} else {
				v[i]--
			}
		}
	}
	
	var fingerprint uint64
	for i := 0; i < 64; i++ {
		if v[i] > 0 {
			fingerprint |= 1 << i
		}
	}
	return fingerprint
}

// HammingDistance calculates the number of bits that differ between two uint64s
func HammingDistance(a, b uint64) int {
	x := a ^ b
	dist := 0
	for x > 0 {
		dist++
		x &= x - 1
	}
	return dist
}

// Storage manages both PostgreSQL and BadgerDB
type Storage struct {
	postgres *sql.DB
	badger   *badger.DB
}

// StorageConfig holds storage configuration
type StorageConfig struct {
	PostgresDSN string
	BadgerPath  string
	ReadOnly    bool
}

// NewStorage creates a new storage instance
func NewStorage(config *StorageConfig) (*Storage, error) {
	// Open BadgerDB (always enabled for optimal performance)
	opts := badger.DefaultOptions(config.BadgerPath)
	
	// Enable compression (Zstandard is default in v4 if Cgo is enabled, but let's be explicit)
	// v4 defaults to Snappy if Cgo is disabled, which is still good.
	// We'll also set a reasonable compression level if using Zstd.
	opts.IndexCacheSize = 128 << 20 // 128MB cache for index
	
	if config.ReadOnly {
		opts.ReadOnly = true
		opts.BypassLockGuard = true
		opts.Logger = nil // Reduce noise in read-only mode
	}

	var badgerDB *badger.DB
	var err error
	// Try to open BadgerDB with retries for lock acquisition
	maxRetries := 5
	if config.ReadOnly {
		maxRetries = 2 // Fewer retries for read-only
	}

	for i := 0; i < maxRetries; i++ {
		badgerDB, err = badger.Open(opts)
		if err == nil {
			log.Println("Opened BadgerDB with compression enabled")
			break
		}

		if strings.Contains(err.Error(), "Cannot acquire directory lock") && i < maxRetries-1 {
			log.Printf("Warning: BadgerDB lock busy, retrying in 1s (%d/%d)...", i+1, maxRetries)
			time.Sleep(1 * time.Second)
			continue
		}

		if config.ReadOnly {
			log.Printf("Warning: BadgerDB not available in read-only mode: %v", err)
			log.Println("Continuing without BadgerDB (HTML content will not be available)")
			err = nil 
			break
		} else {
			return nil, fmt.Errorf("failed to open BadgerDB: %w", err)
		}
	}

	// Start BadgerDB Garbage Collection in background
	if badgerDB != nil && !config.ReadOnly {
		go func() {
			ticker := time.NewTicker(5 * time.Minute)
			defer ticker.Stop()
			for range ticker.C {
			again:
				err := badgerDB.RunValueLogGC(0.5) // Reclaim if >50% is stale
				if err == nil {
					goto again
				}
			}
		}()
	}

	// Connect to PostgreSQL
	postgres, err := sql.Open("postgres", config.PostgresDSN)
	if err != nil {
		if badgerDB != nil {
			badgerDB.Close()
		}
		return nil, fmt.Errorf("failed to open PostgreSQL: %w", err)
	}

	// Test connection
	if err := postgres.Ping(); err != nil {
		if badgerDB != nil {
			badgerDB.Close()
		}
		return nil, fmt.Errorf("failed to ping PostgreSQL: %w", err)
	}

	// Set connection pool settings
	postgres.SetMaxOpenConns(50) // Increased for better concurrency
	postgres.SetMaxIdleConns(10)
	postgres.SetConnMaxLifetime(5 * time.Minute)

	log.Println("Connected to PostgreSQL (pool size: 50)")

	return &Storage{
		postgres: postgres,
		badger:   badgerDB,
	}, nil
}

// Close closes both database connections
func (s *Storage) Close() error {
	var errs []string

	if s.badger != nil {
		log.Println("Closing BadgerDB and running final GC...")
		// Final GC attempt before close
		s.badger.RunValueLogGC(0.5)
		if err := s.badger.Close(); err != nil {
			errs = append(errs, fmt.Sprintf("badger close error: %v", err))
		}
	}

	if s.postgres != nil {
		log.Println("Closing PostgreSQL...")
		if err := s.postgres.Close(); err != nil {
			errs = append(errs, fmt.Sprintf("postgres close error: %v", err))
		}
	}

	if len(errs) > 0 {
		return fmt.Errorf("errors closing storage: %s", strings.Join(errs, "; "))
	}

	return nil
}

// SavePage saves a crawled page to both PostgreSQL and BadgerDB using CAS
func (s *Storage) SavePage(page *models.CrawledPage) error {
	// 1. Calculate Content Hash for CAS
	hasher := sha256.New()
	hasher.Write([]byte(page.HTMLContent))
	page.ContentHash = hex.EncodeToString(hasher.Sum(nil))
	
	// 2. Calculate SimHash for near-duplicate detection
	page.SimHash = SimHash(page.Content)

	// Start PostgreSQL transaction
	tx, err := s.postgres.Begin()
	if err != nil {
		return fmt.Errorf("failed to begin transaction: %w", err)
	}
	defer tx.Rollback()

	// Insert or update page in PostgreSQL
	// Added content_hash and simhash for deduplication
	query := `
		INSERT INTO crawled_pages (
			url, final_url, title, content, meta_description, meta_keywords,
			status_code, content_type, content_length, load_time_ms,
			crawl_depth, outbound_links, inbound_links,
			language, is_indexed, crawled_at, updated_at, next_crawl_at,
			content_hash, simhash
		) VALUES (
			$1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20
		)
		ON CONFLICT (url) DO UPDATE SET
			final_url = EXCLUDED.final_url,
			title = EXCLUDED.title,
			content = EXCLUDED.content,
			meta_description = EXCLUDED.meta_description,
			meta_keywords = EXCLUDED.meta_keywords,
			status_code = EXCLUDED.status_code,
			content_type = EXCLUDED.content_type,
			content_length = EXCLUDED.content_length,
			load_time_ms = EXCLUDED.load_time_ms,
			crawl_depth = EXCLUDED.crawl_depth,
			outbound_links = EXCLUDED.outbound_links,
			updated_at = EXCLUDED.updated_at,
			content_hash = EXCLUDED.content_hash,
			simhash = EXCLUDED.simhash
		RETURNING id
	`

	var pageID int
	err = tx.QueryRow(query,
		page.URL, page.FinalURL, page.Title, page.Content,
		page.MetaDescription, page.MetaKeywords, page.StatusCode,
		page.ContentType, page.ContentLength, page.LoadTimeMs,
		page.CrawlDepth, page.OutboundLinks, page.InboundLinks,
		page.Language, page.IsIndexed, page.CrawledAt, page.UpdatedAt, page.NextCrawlAt,
		page.ContentHash, fmt.Sprintf("%d", page.SimHash),
	).Scan(&pageID)
	if err != nil {
		return fmt.Errorf("failed to insert/update page: %w", err)
	}

	// Set the ID on the page object
	page.ID = fmt.Sprintf("page_%d", pageID)

	// CAS (Content-Addressable Storage): Store raw HTML in BadgerDB indexed by its HASH
	// This ensures multiple URLs with identical content only store one copy of the HTML.
	if page.HTMLContent != "" && s.badger != nil {
		err = s.badger.Update(func(txn *badger.Txn) error {
			// Key is content:HASH
			key := []byte("content:" + page.ContentHash)
			
			// Check if we already have this content
			_, err := txn.Get(key)
			if err == badger.ErrKeyNotFound {
				// Only store if it doesn't exist
				return txn.Set(key, []byte(page.HTMLContent))
			}
			return err
		})
		if err != nil {
			return fmt.Errorf("failed to store HTML in BadgerDB (CAS): %w", err)
		}
		
		// Map page ID to content hash for retrieval
		err = s.badger.Update(func(txn *badger.Txn) error {
			key := []byte("page_to_content:" + page.ID)
			return txn.Set(key, []byte(page.ContentHash))
		})
		if err != nil {
			return fmt.Errorf("failed to store mapping in BadgerDB: %w", err)
		}
	}

	// Commit PostgreSQL transaction
	if err := tx.Commit(); err != nil {
		return fmt.Errorf("failed to commit transaction: %w", err)
	}

	return nil
}

// SaveLinks saves page links to PostgreSQL
func (s *Storage) SaveLinks(links []*models.PageLink, sourcePageIntID int) error {
	if len(links) == 0 {
		return nil
	}

	tx, err := s.postgres.Begin()
	if err != nil {
		return fmt.Errorf("failed to begin transaction: %w", err)
	}
	defer tx.Rollback()

	query := `
		INSERT INTO page_links (source_page_id, target_url, anchor_text, link_type, created_at)
		VALUES ($1, $2, $3, $4, $5)
		ON CONFLICT (source_page_id, target_url) DO NOTHING
	`

	for _, link := range links {
		_, err := tx.Exec(query,
			sourcePageIntID, link.TargetURL, link.AnchorText,
			link.LinkType, link.CreatedAt,
		)
		if err != nil {
			return fmt.Errorf("failed to insert link: %w", err)
		}
	}

	if err := tx.Commit(); err != nil {
		return fmt.Errorf("failed to commit transaction: %w", err)
	}

	return nil
}

// GetPageIDByURL retrieves the integer ID for a page by URL
func (s *Storage) GetPageIDByURL(url string) (int, error) {
	query := `SELECT id FROM crawled_pages WHERE url = $1`
	var id int
	err := s.postgres.QueryRow(query, url).Scan(&id)
	if err != nil {
		return 0, fmt.Errorf("failed to get page ID by URL: %w", err)
	}
	return id, nil
}

// GetPage retrieves a page by ID
func (s *Storage) GetPage(id string) (*models.CrawledPage, error) {
	// Try to parse as integer ID first
	var page *models.CrawledPage
	var err error

	// Check if it's our generated ID format "page_123"
	if strings.HasPrefix(id, "page_") {
		intID := strings.TrimPrefix(id, "page_")
		page, err = s.GetPageByIntID(intID)
		if err == nil {
			return page, nil
		}
	}

	// Fall back to URL lookup
	query := `
		SELECT id, url, final_url, title, content, meta_description, meta_keywords,
		       status_code, content_type, content_length, load_time_ms,
		       crawl_depth, outbound_links, inbound_links, pagerank,
		       language, is_indexed, crawled_at, updated_at, next_crawl_at,
		       content_hash, simhash
		FROM crawled_pages
		WHERE url = $1
	`

	page = &models.CrawledPage{}
	var pageRank sql.NullFloat64
	var simHashStr sql.NullString
	err = s.postgres.QueryRow(query, id).Scan(
		&page.ID, &page.URL, &page.FinalURL, &page.Title, &page.Content,
		&page.MetaDescription, &page.MetaKeywords, &page.StatusCode,
		&page.ContentType, &page.ContentLength, &page.LoadTimeMs,
		&page.CrawlDepth, &page.OutboundLinks, &page.InboundLinks, &pageRank,
		&page.Language, &page.IsIndexed, &page.CrawledAt, &page.UpdatedAt, &page.NextCrawlAt,
		&page.ContentHash, &simHashStr,
	)
	if err != nil {
		return nil, fmt.Errorf("failed to query page: %w", err)
	}

	page.PageRank = pageRank.Float64
	if simHashStr.Valid {
		fmt.Sscanf(simHashStr.String, "%d", &page.SimHash)
	}

	// Convert integer ID to string format
	page.ID = fmt.Sprintf("page_%d", page.ID)

	return page, nil
}

// GetPageByIntID retrieves a page by integer ID
func (s *Storage) GetPageByIntID(intID string) (*models.CrawledPage, error) {
	query := `
		SELECT id, url, final_url, title, content, meta_description, meta_keywords,
		       status_code, content_type, content_length, load_time_ms,
		       crawl_depth, outbound_links, inbound_links, pagerank,
		       language, is_indexed, crawled_at, updated_at, next_crawl_at,
		       content_hash, simhash
		FROM crawled_pages
		WHERE id = $1
	`

	page := &models.CrawledPage{}
	var pageRank sql.NullFloat64
	var simHashStr sql.NullString
	err := s.postgres.QueryRow(query, intID).Scan(
		&page.ID, &page.URL, &page.FinalURL, &page.Title, &page.Content,
		&page.MetaDescription, &page.MetaKeywords, &page.StatusCode,
		&page.ContentType, &page.ContentLength, &page.LoadTimeMs,
		&page.CrawlDepth, &page.OutboundLinks, &page.InboundLinks, &pageRank,
		&page.Language, &page.IsIndexed, &page.CrawledAt, &page.UpdatedAt, &page.NextCrawlAt,
		&page.ContentHash, &simHashStr,
	)
	if err != nil {
		return nil, fmt.Errorf("failed to query page: %w", err)
	}

	page.PageRank = pageRank.Float64
	if simHashStr.Valid {
		fmt.Sscanf(simHashStr.String, "%d", &page.SimHash)
	}

	// Convert integer ID to string format
	page.ID = fmt.Sprintf("page_%d", page.ID)

	return page, nil
}

// GetPageHTML retrieves raw HTML using the CAS mapping
func (s *Storage) GetPageHTML(id string) (string, error) {
	if s.badger == nil {
		return "", fmt.Errorf("BadgerDB not available")
	}

	var contentHash string
	// 1. Get content hash for the page ID
	err := s.badger.View(func(txn *badger.Txn) error {
		key := []byte("page_to_content:" + id)
		item, err := txn.Get(key)
		if err != nil {
			return err
		}
		return item.Value(func(val []byte) error {
			contentHash = string(val)
			return nil
		})
	})
	if err != nil {
		return "", fmt.Errorf("failed to get content hash for page %s: %w", id, err)
	}

	// 2. Get content using the hash
	var html string
	err = s.badger.View(func(txn *badger.Txn) error {
		key := []byte("content:" + contentHash)
		item, err := txn.Get(key)
		if err != nil {
			return err
		}
		return item.Value(func(val []byte) error {
			html = string(val)
			return nil
		})
	})
	if err != nil {
		return "", fmt.Errorf("failed to get content for hash %s: %w", contentHash, err)
	}

	return html, nil
}

// UpdatePageRank updates PageRank score for a page
func (s *Storage) UpdatePageRank(id string, score float64) error {
	query := `UPDATE crawled_pages SET pagerank = $1, updated_at = $2 WHERE id = $3`
	_, err := s.postgres.Exec(query, score, time.Now(), id)
	return err
}

// GetStats returns crawl statistics
func (s *Storage) GetStats() (*models.CrawlStats, error) {
	query := `
		SELECT 
			COUNT(*) as total_pages,
			COUNT(CASE WHEN is_indexed = true THEN 1 END) as pages_indexed,
			AVG(load_time_ms) as avg_load_time
		FROM crawled_pages
	`

	stats := &models.CrawlStats{}
	err := s.postgres.QueryRow(query).Scan(
		&stats.TotalPages, &stats.PagesIndexed, &stats.AvgLoadTimeMs,
	)
	if err != nil {
		return nil, fmt.Errorf("failed to query stats: %w", err)
	}

	return stats, nil
}

// UpdateStats updates daily crawl statistics
func (s *Storage) UpdateStats(pagesCrawled, pagesFailed, pagesIndexed, linksExtracted int) error {
	query := `
		INSERT INTO crawl_stats (stat_date, pages_crawled, pages_failed, pages_indexed, links_extracted, updated_at)
		VALUES (CURRENT_DATE, $1, $2, $3, $4, NOW())
		ON CONFLICT (stat_date) DO UPDATE SET
			pages_crawled = crawl_stats.pages_crawled + EXCLUDED.pages_crawled,
			pages_failed = crawl_stats.pages_failed + EXCLUDED.pages_failed,
			pages_indexed = crawl_stats.pages_indexed + EXCLUDED.pages_indexed,
			links_extracted = crawl_stats.links_extracted + EXCLUDED.links_extracted,
			updated_at = NOW()
	`
	_, err := s.postgres.Exec(query, pagesCrawled, pagesFailed, pagesIndexed, linksExtracted)
	return err
}

// GetUnindexedPages returns pages that haven't been indexed yet
func (s *Storage) GetUnindexedPages(limit int) ([]*models.CrawledPage, error) {
	query := `
		SELECT id, url, final_url, title, content, meta_description, meta_keywords,
		       status_code, content_type, content_length, load_time_ms,
		       crawl_depth, outbound_links, inbound_links, pagerank,
		       language, is_indexed, crawled_at, updated_at, next_crawl_at,
		       content_hash, simhash
		FROM crawled_pages
		WHERE is_indexed = false
		ORDER BY crawled_at ASC
		LIMIT $1
	`

	rows, err := s.postgres.Query(query, limit)
	if err != nil {
		return nil, fmt.Errorf("failed to query unindexed pages: %w", err)
	}
	defer rows.Close()

	var pages []*models.CrawledPage
	for rows.Next() {
		page := &models.CrawledPage{}
		var pageRank sql.NullFloat64
		var simHashStr sql.NullString
		err := rows.Scan(
			&page.ID, &page.URL, &page.FinalURL, &page.Title, &page.Content,
			&page.MetaDescription, &page.MetaKeywords, &page.StatusCode,
			&page.ContentType, &page.ContentLength, &page.LoadTimeMs,
			&page.CrawlDepth, &page.OutboundLinks, &page.InboundLinks, &pageRank,
			&page.Language, &page.IsIndexed, &page.CrawledAt, &page.UpdatedAt, &page.NextCrawlAt,
			&page.ContentHash, &simHashStr,
		)
		if err != nil {
			return nil, fmt.Errorf("failed to scan page: %w", err)
		}
		page.PageRank = pageRank.Float64
		if simHashStr.Valid {
			fmt.Sscanf(simHashStr.String, "%d", &page.SimHash)
		}
		pages = append(pages, page)
	}

	return pages, rows.Err()
}

// MarkAsIndexed marks a page as indexed
func (s *Storage) MarkAsIndexed(id string) error {
	query := `UPDATE crawled_pages SET is_indexed = true, updated_at = $1 WHERE id = $2`
	_, err := s.postgres.Exec(query, time.Now(), id)
	return err
}

// SerializeTermFrequencies converts term frequencies to JSON
func SerializeTermFrequencies(terms map[string]int) (string, error) {
	data, err := json.Marshal(terms)
	if err != nil {
		return "", err
	}
	return string(data), nil
}

// DeserializeTermFrequencies converts JSON to term frequencies
func DeserializeTermFrequencies(data string) (map[string]int, error) {
	var terms map[string]int
	err := json.Unmarshal([]byte(data), &terms)
	return terms, err
}
