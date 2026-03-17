package frontier

import (
	"context"
	"crypto/sha1"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"net/url"
	"strings"
	"time"

	"github.com/go-redis/redis/v8"
	"github.com/itxLikhith/intent-engine/go-crawler/pkg/models"
)

// URLFrontier manages the URL queue for crawling
type URLFrontier struct {
	client    *redis.Client
	queueKey  string
	visitedKey string // Now using a single Redis SET for visited URLs
	ctx       context.Context
}

// NewURLFrontier creates a new URL frontier
func NewURLFrontier(addr, password string, db int) (*URLFrontier, error) {
	client := redis.NewClient(&redis.Options{
		Addr:     addr,
		Password: password,
		DB:       db,
		PoolSize: 20, // Dedicated connection pool for frontier
	})

	ctx := context.Background()

	// Test connection
	if err := client.Ping(ctx).Err(); err != nil {
		return nil, fmt.Errorf("failed to connect to Redis: %w", err)
	}

	return &URLFrontier{
		client:    client,
		queueKey:  "crawl_queue",
		visitedKey: "visited_urls_set",
		ctx:       ctx,
	}, nil
}

// NormalizeURL standardizes a URL to prevent duplicate crawls of the same page
func NormalizeURL(urlStr string) string {
	u, err := url.Parse(strings.TrimSpace(urlStr))
	if err != nil {
		return urlStr
	}

	// Lowercase host
	u.Host = strings.ToLower(u.Host)
	
	// Remove default ports
	if (u.Scheme == "http" && u.Port() == "80") || (u.Scheme == "https" && u.Port() == "443") {
		u.Host = u.Hostname()
	}

	// Remove fragments
	u.Fragment = ""

	// Remove trailing slash from path
	if len(u.Path) > 1 && strings.HasSuffix(u.Path, "/") {
		u.Path = u.Path[:len(u.Path)-1]
	}

	// Sort query parameters for consistency
	q := u.Query()
	u.RawQuery = q.Encode()

	return u.String()
}

// AddURLs adds URLs to the crawl queue if they haven't been visited
func (f *URLFrontier) AddURLs(urls []string, priority int, depth int) (int, error) {
	added := 0
	
	for _, rawURL := range urls {
		normalized := NormalizeURL(rawURL)
		
		// Optimization: Check visited set BEFORE adding to queue
		visited, err := f.IsVisited(normalized)
		if err != nil || visited {
			continue
		}

		// Create compact queue item (store only what's needed for the crawl)
		item := &models.CrawlQueueItem{
			URL:         normalized,
			Priority:    priority,
			Depth:       depth,
			Status:      "pending",
			ScheduledAt: time.Now(),
		}

		// Serialize item
		data, err := json.Marshal(item)
		if err != nil {
			continue
		}

		// Add to sorted set with priority as score
		err = f.client.ZAdd(f.ctx, f.queueKey, &redis.Z{
			Score:  float64(priority),
			Member: string(data),
		}).Err()
		
		if err != nil {
			continue
		}

		added++
	}

	return added, nil
}

// GetNextURL gets the next URL to crawl based on priority using atomic ZPOPMIN
func (f *URLFrontier) GetNextURL() (*models.CrawlQueueItem, error) {
	// ZPOPMIN is atomic and returns/removes the item with the lowest score (highest priority)
	// In our case, higher priority value = higher priority, so we use ZPOPMAX if we want high priority first
	// Our Seed uses priority 10, links use 1. So ZPOPMAX is correct for "highest value first".
	results, err := f.client.ZPopMax(f.ctx, f.queueKey, 1).Result()
	if err != nil {
		return nil, fmt.Errorf("failed to get next URL: %w", err)
	}

	if len(results) == 0 {
		return nil, nil // Queue empty
	}

	// Parse queue item
	var item models.CrawlQueueItem
	memberStr, ok := results[0].Member.(string)
	if !ok {
		return nil, fmt.Errorf("invalid queue item type")
	}

	if err := json.Unmarshal([]byte(memberStr), &item); err != nil {
		return nil, fmt.Errorf("failed to parse queue item: %w", err)
	}

	// Update status to crawling
	item.Status = "crawling"
	item.UpdatedAt = time.Now()

	return &item, nil
}

// MarkCompleted marks a URL as completed (visited) in the Redis set
func (f *URLFrontier) MarkCompleted(urlStr string) error {
	normalized := NormalizeURL(urlStr)
	// Using a SET is much more memory efficient than individual keys
	return f.client.SAdd(f.ctx, f.visitedKey, normalized).Err()
}

// MarkFailed marks a URL as failed but still adds to visited to avoid retry loops
func (f *URLFrontier) MarkFailed(urlStr, errMsg string) error {
	normalized := NormalizeURL(urlStr)
	return f.client.SAdd(f.ctx, f.visitedKey, normalized).Err()
}

// IsVisited checks if a URL has been visited using Redis SISMEMBER
func (f *URLFrontier) IsVisited(urlStr string) (bool, error) {
	normalized := NormalizeURL(urlStr)
	return f.client.SIsMember(f.ctx, f.visitedKey, normalized).Result()
}

// hashURL creates a stable SHA1 hash of the URL (optional optimization for set members)
func hashURL(urlStr string) string {
	h := sha1.New()
	h.Write([]byte(urlStr))
	return hex.EncodeToString(h.Sum(nil))
}

// GetQueueSize returns the number of URLs in the queue
func (f *URLFrontier) GetQueueSize() (int64, error) {
	return f.client.ZCard(f.ctx, f.queueKey).Result()
}

// GetStats returns frontier statistics
func (f *URLFrontier) GetStats() (map[string]interface{}, error) {
	queueSize, err := f.GetQueueSize()
	if err != nil {
		return nil, err
	}

	visitedSize, err := f.client.SCard(f.ctx, f.visitedKey).Result()
	if err != nil {
		visitedSize = 0
	}

	return map[string]interface{}{
		"queue_size":   queueSize,
		"visited_size": visitedSize,
	}, nil
}

// ClearQueue removes all items from the queue (for cleanup)
func (f *URLFrontier) ClearQueue() error {
	return f.client.Del(f.ctx, f.queueKey).Err()
}

// Close closes the Redis connection
func (f *URLFrontier) Close() error {
	return f.client.Close()
}

