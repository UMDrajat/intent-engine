package main

import (
	"encoding/json"
	"flag"
	"log"
	"net/http"
	"os"
	"time"

	"github.com/blevesearch/bleve/v2"
	"github.com/gorilla/mux"
	"github.com/itxLikhith/intent-engine/go-crawler/internal/indexer"
	"github.com/itxLikhith/intent-engine/go-crawler/internal/storage"
	"github.com/prometheus/client_golang/prometheus/promhttp"
)

// SearchRequest represents a search request
type SearchRequest struct {
	Query   string            `json:"query"`
	Limit   int               `json:"limit"`
	Filters map[string]interface{} `json:"filters,omitempty"`
}

// SearchResponse represents a search response
type SearchResponse struct {
	Query           string                    `json:"query"`
	Results         []SearchResult            `json:"results"`
	TotalResults    int64                     `json:"total_results"`
	ProcessingTimeMs float64                  `json:"processing_time_ms"`
	EnginesUsed     []string                  `json:"engines_used"`
	RankingApplied  bool                      `json:"ranking_applied"`
}

// SearchResult represents a single search result
type SearchResult struct {
	URL             string   `json:"url"`
	Title           string   `json:"title"`
	Content         string   `json:"content"`
	Score           float64  `json:"score"`
	Rank            int      `json:"rank"`
	MatchReasons    []string `json:"match_reasons,omitempty"`
}

// HealthResponse represents health check response
type HealthResponse struct {
	Status    string                 `json:"status"`
	Timestamp time.Time              `json:"timestamp"`
	Checks    map[string]bool        `json:"checks"`
	Version   string                 `json:"version"`
}

// StatsResponse represents statistics response
type StatsResponse struct {
	IndexedDocuments uint64 `json:"indexed_documents"`
	CrawledPages     int64  `json:"crawled_pages"`
	QueueSize        int64  `json:"queue_size"`
}

var (
	searchIndexer *indexer.SearchIndexer
	bleveIndex    bleve.Index  // Fallback bleve index if SearchIndexer fails to initialize
	store         *storage.Storage
)

func main() {
	port := flag.String("port", getEnv("SERVER_PORT", "8080"), "Server port")
	blevePath := flag.String("bleve", getEnv("BLEVE_PATH", "./data/bleve"), "Bleve index path")
	badgerPath := flag.String("badger", getEnv("BADGER_PATH", "./data/badger"), "BadgerDB path")
	postgresDSN := flag.String("postgres", getEnv("POSTGRES_DSN", ""), "PostgreSQL DSN")
	flag.Parse()

	if *postgresDSN == "" {
		*postgresDSN = "postgresql://crawler:crawler@localhost:5432/intent_engine?sslmode=disable"
	}

	log.Printf("Starting Search API on port %s", *port)
	log.Printf("Bleve Path: %s", *blevePath)
	log.Printf("PostgreSQL: %s", *postgresDSN)

	// Initialize storage (read-only for API)
	storeCfg := &storage.StorageConfig{
		PostgresDSN: *postgresDSN,
		BadgerPath:  *badgerPath,
		ReadOnly:    true,
	}
	var err error
	log.Printf("Initializing storage with config: BadgerPath=%s, ReadOnly=%v", *badgerPath, true)
	store, err = storage.NewStorage(storeCfg)
	if err != nil {
		log.Fatalf("Failed to initialize storage: %v", err)
	}
	defer store.Close()
	log.Printf("Storage initialized successfully")

	// Initialize indexer
	log.Printf("Initializing indexer with Bleve path: %s (read-only)", *blevePath)

	// Check if index exists before trying to open
	if _, err := os.Stat(*blevePath); os.IsNotExist(err) {
		log.Printf("Warning: Bleve index does not exist at %s - search will return no results", *blevePath)
		log.Printf("Index will be created when first document is indexed by go-indexer")
		// Create empty index as fallback
		mapping := bleve.NewIndexMapping()
		mapping.DefaultMapping.AddFieldMappingsAt("title", bleve.NewTextFieldMapping())
		mapping.DefaultMapping.AddFieldMappingsAt("content", bleve.NewTextFieldMapping())
		mapping.DefaultMapping.AddFieldMappingsAt("meta_description", bleve.NewTextFieldMapping())
		mapping.DefaultMapping.AddFieldMappingsAt("url", bleve.NewTextFieldMapping())
		bleveIndex, err = bleve.New(*blevePath, mapping)
		if err != nil {
			log.Fatalf("Failed to create empty Bleve index: %v", err)
		}
		log.Printf("Created empty Bleve index (fallback mode)")
	} else {
		searchIndexer, err = indexer.NewSearchIndexerWithOptions(*blevePath, store, true)
		if err != nil {
			log.Fatalf("Failed to initialize indexer: %v", err)
		}
		log.Printf("Indexer initialized successfully")
	}

	// Setup defer cleanup
	defer func() {
		if searchIndexer != nil {
			searchIndexer.Close()
		}
		if bleveIndex != nil {
			bleveIndex.Close()
		}
	}()

	// Setup routes
	r := mux.NewRouter()
	r.HandleFunc("/health", healthHandler).Methods("GET", "HEAD")
	r.HandleFunc("/stats", statsHandler).Methods("GET", "HEAD")
	r.HandleFunc("/api/v1/search", searchHandler).Methods("POST")
	r.HandleFunc("/metrics", promhttp.Handler().ServeHTTP).Methods("GET")

	log.Printf("Search API ready to accept connections on :%s", *port)
	if err := http.ListenAndServe(":"+*port, r); err != nil {
		log.Fatalf("Server failed: %v", err)
	}
}

func healthHandler(w http.ResponseWriter, r *http.Request) {
	checks := map[string]bool{
		"indexer": searchIndexer != nil || bleveIndex != nil,
		"storage": store != nil,
	}

	status := "healthy"
	for _, ok := range checks {
		if !ok {
			status = "degraded"
			break
		}
	}

	response := HealthResponse{
		Status:    status,
		Timestamp: time.Now(),
		Checks:    checks,
		Version:   "1.0.0",
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(response)
}

func statsHandler(w http.ResponseWriter, r *http.Request) {
	stats := StatsResponse{}

	// Get index stats from SearchIndexer or fallback bleve index
	if searchIndexer != nil {
		indexStats, err := searchIndexer.Stats()
		if err == nil {
			stats.IndexedDocuments = indexStats.DocumentCount
		}
	} else if bleveIndex != nil {
		docCount, err := bleveIndex.DocCount()
		if err == nil {
			stats.IndexedDocuments = docCount
		}
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(stats)
}

func searchHandler(w http.ResponseWriter, r *http.Request) {
	startTime := time.Now()

	// Parse request
	var req SearchRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "Invalid request", http.StatusBadRequest)
		return
	}

	if req.Query == "" {
		http.Error(w, "Query is required", http.StatusBadRequest)
		return
	}

	if req.Limit <= 0 {
		req.Limit = 10
	}
	if req.Limit > 100 {
		req.Limit = 100
	}

	// Perform search using SearchIndexer or fallback bleve index
	var searchResult *indexer.SearchResult
	var err error

	if searchIndexer != nil {
		// Use full-featured SearchIndexer
		searchResult, err = searchIndexer.Search(req.Query, req.Limit)
	} else if bleveIndex != nil {
		// Use basic bleve index (fallback mode)
		query := bleve.NewMatchQuery(req.Query)
		searchRequest := bleve.NewSearchRequest(query)
		searchRequest.Size = req.Limit
		bleveResult, bleveErr := bleveIndex.Search(searchRequest)
		if bleveErr != nil {
			log.Printf("Bleve search error: %v", bleveErr)
			http.Error(w, "Search failed", http.StatusInternalServerError)
			return
		}
		// Convert bleve result to our format
		searchResult = &indexer.SearchResult{
			Total:    int64(bleveResult.Total),
			MaxScore: bleveResult.MaxScore,
			Hits:     make([]indexer.SearchHit, len(bleveResult.Hits)),
		}
		for i, hit := range bleveResult.Hits {
			doc := &indexer.SearchDocument{}
			for field, value := range hit.Fields {
				switch field {
				case "url":
					if s, ok := value.(string); ok {
						doc.URL = s
					}
				case "title":
					if s, ok := value.(string); ok {
						doc.Title = s
					}
				case "content":
					if s, ok := value.(string); ok {
						doc.Content = s
					}
				case "meta_description":
					if s, ok := value.(string); ok {
						doc.MetaDescription = s
					}
				}
			}
			searchResult.Hits[i] = indexer.SearchHit{
				ID:       hit.ID,
				Score:    hit.Score,
				Document: doc,
			}
		}
		err = nil
	} else {
		log.Printf("No index available for search")
		http.Error(w, "Search index not available", http.StatusInternalServerError)
		return
	}

	if err != nil {
		log.Printf("Search error: %v", err)
		http.Error(w, "Search failed", http.StatusInternalServerError)
		return
	}

	// Convert to response format
	results := make([]SearchResult, len(searchResult.Hits))
	for i, hit := range searchResult.Hits {
		results[i] = SearchResult{
			URL:     hit.Document.URL,
			Title:   hit.Document.Title,
			Content: truncateContent(hit.Document.Content, 200),
			Score:   hit.Score,
			Rank:    i + 1,
		}
	}

	response := SearchResponse{
		Query:            req.Query,
		Results:          results,
		TotalResults:     searchResult.Total,
		ProcessingTimeMs: float64(time.Since(startTime).Milliseconds()),
		EnginesUsed:      []string{"bleve"},
		RankingApplied:   true,
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(response)
}

func truncateContent(content string, maxLen int) string {
	if len(content) <= maxLen {
		return content
	}
	return content[:maxLen] + "..."
}

func getEnv(key, fallback string) string {
	if value, ok := os.LookupEnv(key); ok {
		return value
	}
	return fallback
}
