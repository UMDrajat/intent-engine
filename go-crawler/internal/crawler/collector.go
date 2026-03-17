package crawler

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"strings"
	"sync"
	"time"

	"github.com/PuerkitoBio/goquery"
	"github.com/go-redis/redis/v8"
	"github.com/gocolly/colly/v2"
	"github.com/itxLikhith/intent-engine/go-crawler/internal/frontier"
	"github.com/itxLikhith/intent-engine/go-crawler/internal/storage"
	"github.com/itxLikhith/intent-engine/go-crawler/pkg/models"
)

// Crawler represents the web crawler
type Crawler struct {
	collector   *colly.Collector
	config      *Config
	store       *storage.Storage
	frontier    *frontier.URLFrontier
	redisClient *redis.Client
	stats       *CrawlStats
	statsMutex  sync.RWMutex
	ctx         context.Context
	cancel      context.CancelFunc
}

// CrawlStats holds crawling statistics
type CrawlStats struct {
	PagesCrawled  int64
	PagesSuccess  int64
	PagesFailed   int64
	LinksFound    int64
	Duplicates    int64
	StartTime     time.Time
	Duration      time.Duration
}

// NewCrawler creates a new crawler instance
func NewCrawler(cfg *Config, store *storage.Storage, redisAddr string) (*Crawler, error) {
	// Initialize frontier
	f, err := frontier.NewURLFrontier(redisAddr, "", 0)
	if err != nil {
		return nil, fmt.Errorf("failed to create frontier: %w", err)
	}

	// Initialize Redis client for dynamic content check
	rClient := redis.NewClient(&redis.Options{
		Addr: redisAddr,
	})

	// Create Colly collector
	c := colly.NewCollector(
		colly.MaxDepth(cfg.MaxDepth),
		colly.MaxBodySize(10 * 1024 * 1024), // 10MB
		colly.UserAgent(cfg.UserAgent),
		colly.Async(true),
	)

	// Set concurrency limits
	c.Limit(&colly.LimitRule{
		DomainGlob:  "*",
		Parallelism: cfg.MaxConcurrentRequests,
		Delay:       cfg.CrawlDelay,
		RandomDelay: cfg.RandomDelay,
	})

	// Configure timeouts
	c.SetRequestTimeout(cfg.RequestTimeout)

	ctx, cancel := context.WithCancel(context.Background())

	crawler := &Crawler{
		collector:   c,
		config:      cfg,
		store:       store,
		frontier:    f,
		redisClient: rClient,
		stats: &CrawlStats{
			StartTime: time.Now(),
		},
		ctx:    ctx,
		cancel: cancel,
	}

	// Setup callbacks
	crawler.setupCallbacks()

	return crawler, nil
}

// setupCallbacks configures Colly callbacks
func (c *Crawler) setupCallbacks() {
	// Before request
	c.collector.OnRequest(func(r *colly.Request) {
		// Ensure URL is normalized
		normalized := frontier.NormalizeURL(r.URL.String())
		if r.URL.String() != normalized {
			// This shouldn't happen if we normalize before adding to queue, 
			// but good for safety.
			log.Printf("Visiting (normalized): %s", normalized)
		} else {
			log.Printf("Visiting: %s", r.URL.String())
		}
	})

	// On response
	c.collector.OnResponse(func(r *colly.Response) {
		c.statsMutex.Lock()
		c.stats.PagesCrawled++
		c.statsMutex.Unlock()

		// Parse HTML only if it's text/html
		contentType := r.Headers.Get("Content-Type")
		if !strings.Contains(strings.ToLower(contentType), "text/html") {
			return
		}

		doc, err := goquery.NewDocumentFromReader(strings.NewReader(string(r.Body)))
		if err != nil {
			log.Printf("Failed to parse HTML from %s: %v", r.Request.URL, err)
			return
		}

		// Extract page data
		page := c.extractPageData(r, doc)

		// Store page
		if err := c.store.SavePage(page); err != nil {
			log.Printf("Failed to save page %s: %v", r.Request.URL, err)
			return
		}

		// Mark as completed in frontier (using normalization internally)
		if err := c.frontier.MarkCompleted(r.Request.URL.String()); err != nil {
			log.Printf("Failed to mark %s as completed: %v", r.Request.URL, err)
		}

		c.statsMutex.Lock()
		c.stats.PagesSuccess++
		c.statsMutex.Unlock()

		// Extract and queue links
		c.extractLinks(r, doc)
	})

	// On error
	c.collector.OnError(func(r *colly.Response, err error) {
		c.statsMutex.Lock()
		c.stats.PagesFailed++
		c.statsMutex.Unlock()
		
		urlStr := ""
		if r != nil && r.Request != nil {
			urlStr = r.Request.URL.String()
			// Mark as failed to avoid retry loops
			if markErr := c.frontier.MarkFailed(urlStr, err.Error()); markErr != nil {
				log.Printf("Failed to mark URL as failed: %v", markErr)
			}
		}
		log.Printf("Error crawling %s: %v", urlStr, err)
	})
}

// extractPageData extracts page information from response
func (c *Crawler) extractPageData(r *colly.Response, doc *goquery.Document) *models.CrawledPage {
	urlStr := r.Request.URL.String()
	
	// Default data from static HTML
	title := doc.Find("title").First().Text()
	if title == "" {
		title = doc.Find("h1").First().Text()
	}

	description := ""
	doc.Find("meta[name=description], meta[property=\"og:description\"]").Each(func(i int, s *goquery.Selection) {
		if content, exists := s.Attr("content"); exists && description == "" {
			description = content
		}
	})

	// Improved content extraction: focus on main content if possible
	var contentBuilder strings.Builder
	doc.Find("main, article, #content, .content, .main").Each(func(i int, s *goquery.Selection) {
		contentBuilder.WriteString(s.Text())
		contentBuilder.WriteString(" ")
	})
	
	content := contentBuilder.String()
	if len(content) < 100 {
		// Fallback to body text
		content = doc.Find("body").Text()
	}

	// Dynamic Content check (Version 3.0.0 feature)
	// If this URL was recently processed by the Playwright worker, use its richer data
	if c.redisClient != nil {
		ctx := context.Background()
		dynamicKey := "dynamic_scrape:" + urlStr
		data, err := c.redisClient.Get(ctx, dynamicKey).Result()
		if err == nil {
			var dynamicData struct {
				Title       string `json:"title"`
				Description string `json:"description"`
				Content     string `json:"content"`
				HTML        string `json:"html"`
			}
			if err := json.Unmarshal([]byte(data), &dynamicData); err == nil {
				log.Printf("Using dynamic JS content for: %s", urlStr)
				if dynamicData.Title != "" {
					title = dynamicData.Title
				}
				if dynamicData.Description != "" {
					description = dynamicData.Description
				}
				if len(dynamicData.Content) > len(content) {
					content = dynamicData.Content
				}
			}
		}
	}

	// Clean up content
	content = strings.Join(strings.Fields(content), " ")

	// Limit content length
	if len(content) > 100000 {
		content = content[:100000]
	}

	return &models.CrawledPage{
		URL:             urlStr,
		FinalURL:        urlStr,
		Title:           strings.TrimSpace(title),
		Content:         content,
		MetaDescription: strings.TrimSpace(description),
		StatusCode:      r.StatusCode,
		ContentType:     r.Headers.Get("Content-Type"),
		ContentLength:   len(r.Body),
		HTMLContent:     string(r.Body),
		CrawledAt:       time.Now(),
		UpdatedAt:       time.Now(),
		IsIndexed:       false,
		Language:        "en",
	}
}

// extractLinks extracts links from page and queues them
func (c *Crawler) extractLinks(r *colly.Response, doc *goquery.Document) {
	linksFound := 0
	var linksToSave []*models.PageLink
	uniqueLinks := make(map[string]struct{})

	doc.Find("a[href]").Each(func(i int, s *goquery.Selection) {
		href, exists := s.Attr("href")
		if !exists {
			return
		}

		// Resolve and normalize URL
		baseURL := r.Request.URL
		linkURL, err := baseURL.Parse(href)
		if err != nil {
			return
		}
		
		normalized := frontier.NormalizeURL(linkURL.String())
		if _, seen := uniqueLinks[normalized]; seen {
			return
		}
		uniqueLinks[normalized] = struct{}{}

		// Skip invalid URLs
		if linkURL.Scheme != "http" && linkURL.Scheme != "https" {
			return
		}

		// Skip blocked domains
		if c.isBlockedDomain(linkURL.Host) {
			return
		}

		// Skip non-HTML content
		if c.skipURL(normalized) {
			return
		}

		// Add to link list for DB
		link := &models.PageLink{
			TargetURL:  normalized,
			AnchorText: strings.TrimSpace(s.Text()),
			LinkType:   "dofollow",
			CreatedAt:  time.Now(),
		}

		linksToSave = append(linksToSave, link)
		linksFound++
	})

	// Save links in batch
	if len(linksToSave) > 0 {
		pageIntID, err := c.store.GetPageIDByURL(r.Request.URL.String())
		if err == nil {
			if err := c.store.SaveLinks(linksToSave, pageIntID); err != nil {
				log.Printf("Failed to save %d links: %v", len(linksToSave), err)
			}
		}
	}

	// Add URLs to frontier (batch add)
	if len(linksToSave) > 0 {
		urls := make([]string, len(linksToSave))
		for i, link := range linksToSave {
			urls[i] = link.TargetURL
		}
		added, err := c.frontier.AddURLs(urls, 1, c.config.MaxDepth)
		if err != nil {
			log.Printf("Failed to add URLs to frontier: %v", err)
		} else {
			log.Printf("Added %d/%d new URLs to frontier from %s", added, len(urls), r.Request.URL)
		}
	}

	c.statsMutex.Lock()
	c.stats.LinksFound += int64(linksFound)
	c.statsMutex.Unlock()
}


// isBlockedDomain checks if domain is blocked
func (c *Crawler) isBlockedDomain(domain string) bool {
	for _, blocked := range c.config.BlockedDomains {
		if strings.Contains(domain, blocked) {
			return true
		}
	}
	return false
}

// skipURL checks if URL should be skipped
func (c *Crawler) skipURL(urlStr string) bool {
	skipPatterns := []string{
		".jpg", ".jpeg", ".png", ".gif", ".svg", ".ico", ".webp",
		".pdf", ".doc", ".docx", ".xls", ".xlsx",
		".zip", ".rar", ".tar", ".gz",
		".mp3", ".mp4", ".avi", ".mov",
		".css", ".js", ".woff", ".woff2",
		"login", "signup", "register", "checkout",
	}

	lowerURL := strings.ToLower(urlStr)
	for _, pattern := range skipPatterns {
		if strings.Contains(lowerURL, pattern) {
			return true
		}
	}
	return false
}

// Seed adds initial URL to crawl queue
func (c *Crawler) Seed(urlStr string) error {
	log.Printf("Seeding URL: %s", urlStr)
	_, err := c.frontier.AddURLs([]string{urlStr}, 10, 0) // High priority for seed
	return err
}

// Crawl starts the crawling process
func (c *Crawler) Crawl(ctx context.Context) (*CrawlStats, error) {
	log.Println("Starting crawl process...")

	// Create ticker for periodic checks
	ticker := time.NewTicker(100 * time.Millisecond)
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			log.Println("Crawl cancelled")
			return c.getStats(), nil
		case <-c.ctx.Done():
			log.Println("Crawl cancelled (internal)")
			return c.getStats(), nil
		case <-ticker.C:
		}

		// Check if we've reached max pages
		c.statsMutex.RLock()
		if c.stats.PagesCrawled >= int64(c.config.MaxPages) {
			c.statsMutex.RUnlock()
			log.Println("Reached max pages limit")
			break
		}
		c.statsMutex.RUnlock()

		// Get next URL from frontier
		urlItem, err := c.frontier.GetNextURL()
		if err != nil {
			log.Printf("Failed to get next URL: %v", err)
			time.Sleep(time.Second)
			continue
		}

		if urlItem == nil {
			// Queue is empty, wait a bit and check again
			time.Sleep(500 * time.Millisecond)
			continue
		}

		// Visit URL
		if err := c.collector.Visit(urlItem.URL); err != nil {
			log.Printf("Failed to visit %s: %v", urlItem.URL, err)
			// Mark as failed
			if markErr := c.frontier.MarkFailed(urlItem.URL, err.Error()); markErr != nil {
				log.Printf("Failed to mark URL as failed: %v", markErr)
			}
		}
	}

	return c.getStats(), nil
}

// Stop stops the crawler gracefully
func (c *Crawler) Stop() {
	log.Println("Stopping crawler...")
	if c.cancel != nil {
		c.cancel()
	}
	// Colly collector doesn't have a Stop method
	// The context cancellation will stop the crawl loop
}

// getStats returns current crawl statistics
func (c *Crawler) getStats() *CrawlStats {
	c.statsMutex.RLock()
	defer c.statsMutex.RUnlock()

	stats := *c.stats
	stats.Duration = time.Since(stats.StartTime)
	return &stats
}

// GetStats returns crawl statistics
func (c *Crawler) GetStats() *CrawlStats {
	return c.getStats()
}

// generatePageID generates a unique ID for a page
func generatePageID(urlStr string) string {
	// Simple hash-based ID - in production use proper hashing
	h := 0
	for i := 0; i < len(urlStr); i++ {
		h = 31*h + int(urlStr[i])
	}
	return fmt.Sprintf("page_%d", h)
}
