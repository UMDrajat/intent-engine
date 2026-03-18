-- Crawler Database Schema for AIO Container
-- This creates the crawled_pages table for the Go Crawler

-- Crawled pages table
CREATE TABLE IF NOT EXISTS crawled_pages (
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

-- Create indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_crawled_pages_url ON crawled_pages(url);
CREATE INDEX IF NOT EXISTS idx_crawled_pages_title ON crawled_pages(title);
CREATE INDEX IF NOT EXISTS idx_crawled_pages_crawled_at ON crawled_pages(crawled_at);
CREATE INDEX IF NOT EXISTS idx_crawled_pages_is_indexed ON crawled_pages(is_indexed);

-- Page links table (for PageRank calculation)
CREATE TABLE IF NOT EXISTS page_links (
    id SERIAL PRIMARY KEY,
    source_page_id INTEGER REFERENCES crawled_pages(id),
    target_url VARCHAR(4096) NOT NULL,
    anchor_text VARCHAR(2048),
    link_type VARCHAR(50) DEFAULT 'dofollow',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for page links
CREATE INDEX IF NOT EXISTS idx_page_links_source ON page_links(source_page_id);
CREATE INDEX IF NOT EXISTS idx_page_links_target ON page_links(target_url);
