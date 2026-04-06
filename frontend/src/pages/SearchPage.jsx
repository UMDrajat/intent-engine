import { useState, useRef } from 'react';
import {
  Search, ArrowRight, ShieldCheck, Zap, Filter, ChevronRight,
  CheckCircle2, Brain, Clock, Globe, Lock
} from 'lucide-react';
import classNames from 'classnames';
import { searchAPI } from '../api/client';
import { mockSearchResponse } from '../api/mockData';
import './SearchPage.css';

function SearchPage() {
  const [query, setQuery] = useState('');
  const [isSearching, setIsSearching] = useState(false);
  const [response, setResponse] = useState(null);
  const [hasSearched, setHasSearched] = useState(false);
  const [isDemo, setIsDemo] = useState(false);
  const inputRef = useRef(null);

  const handleSearch = async (e) => {
    e?.preventDefault();
    const q = query.trim() || inputRef.current?.value?.trim();
    if (!q) return;

    setIsSearching(true);
    setHasSearched(true);
    setResponse(null);

    try {
      const data = await searchAPI(q);
      setResponse(data);
      setIsDemo(false);
    } catch {
      const mock = { ...mockSearchResponse, query: q };
      setResponse(mock);
      setIsDemo(true);
    } finally {
      setIsSearching(false);
    }
  };

  const handleSuggestion = (text) => {
    setQuery(text);
    setTimeout(() => {
      const fakeEvent = { preventDefault: () => {} };
      handleSearch(fakeEvent);
    }, 0);
  };

  const results = response?.results || [];
  const intent = response?.extracted_intent;

  return (
    <div className={classNames('search-page', { 'has-results': hasSearched })}>
      <div className="hero-section">
        <div className="hero-text animate-slide-up">
          <span className="hero-kicker">Welcome to the future</span>
          <h1 className="hero-title">
            Search driven by <br />
            <em>true intent.</em>
          </h1>
          <p className="hero-subtitle">
            A privacy-first semantic engine that aligns results<br />
            with your authentic goals — no tracking required.
          </p>
        </div>

        <form className="search-container animate-slide-up delay-100" onSubmit={handleSearch}>
          <div className={classNames('search-box', { focused: isSearching })}>
            <Search className="search-icon" size={24} />
            <input
              ref={inputRef}
              type="text"
              placeholder="What are you trying to accomplish?"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="search-input"
            />
            <button
              type="submit"
              className={classNames('search-button', { loading: isSearching, visible: query.length > 0 })}
              disabled={isSearching}
            >
              {isSearching ? <div className="spinner" /> : <ArrowRight size={20} />}
            </button>
          </div>

          {!hasSearched && (
            <div className="search-suggestions animate-fade-in delay-200">
              <span className="suggestion-label"><Zap size={14} /> Try:</span>
              <button type="button" onClick={() => handleSuggestion('learn python')}>learn python</button>
              <button type="button" onClick={() => handleSuggestion('best laptop for programming')}>best laptop for programming</button>
            </div>
          )}
        </form>
      </div>

      {hasSearched && (
        <div className="results-container animate-slide-up delay-200">
          {isSearching ? (
            <div className="results-skeleton">
              <div className="skeleton-item" style={{ '--delay': '0s' }} />
              <div className="skeleton-item" style={{ '--delay': '0.1s' }} />
              <div className="skeleton-item" style={{ '--delay': '0.2s' }} />
            </div>
          ) : results.length > 0 ? (
            <div className="results-list">
              {/* Intent Detection Card */}
              {intent && (
                <div className="intent-card animate-fade-in">
                  <div className="intent-header">
                    <Brain size={18} />
                    <span className="intent-title">Intent Detected</span>
                    <span className="intent-confidence">{(intent.confidence * 100).toFixed(0)}% confident</span>
                  </div>
                  <div className="intent-body">
                    <div className="intent-detail">
                      <span className="intent-label">Goal</span>
                      <span className="intent-badge">{intent.goal?.replace(/_/g, ' ')}</span>
                    </div>
                    {intent.complexity && (
                      <div className="intent-detail">
                        <span className="intent-label">Complexity</span>
                        <span className="intent-value">{intent.complexity}</span>
                      </div>
                    )}
                    {intent.use_cases?.length > 0 && (
                      <div className="intent-detail">
                        <span className="intent-label">Use Cases</span>
                        <div className="intent-pills">
                          {intent.use_cases.map((uc) => (
                            <span key={uc} className="intent-pill">{uc.replace(/_/g, ' ').toLowerCase()}</span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Results Header */}
              <div className="results-header">
                <div className="results-header-left">
                  <h2>Curated Results</h2>
                  <div className="results-meta">
                    {response?.processing_time_ms && (
                      <span className="meta-item"><Clock size={13} /> {response.processing_time_ms.toFixed(0)}ms</span>
                    )}
                    {response?.engines_used?.length > 0 && (
                      <span className="meta-item"><Globe size={13} /> {response.engines_used.join(', ')}</span>
                    )}
                    {response?.tracking_blocked && (
                      <span className="meta-item privacy-badge"><Lock size={13} /> Tracking blocked</span>
                    )}
                    {isDemo && (
                      <span className="meta-item demo-badge">Demo</span>
                    )}
                  </div>
                </div>
                <button className="filter-button"><Filter size={16} /> Refine</button>
              </div>

              {/* Result Cards */}
              <div className="results-grid">
                {results.map((result, i) => (
                  <article
                    key={result.url || i}
                    className="result-card animate-slide-up"
                    style={{ animationDelay: `${0.1 * i}s` }}
                  >
                    <div className="result-meta">
                      <span className="result-provider">
                        <CheckCircle2 size={14} className="verified-icon" /> {result.engine || 'search'}
                      </span>
                      <div className="result-scores">
                        {result.privacy_score != null && (
                          <span className="privacy-score-badge">
                            <ShieldCheck size={14} /> {(result.privacy_score * 100).toFixed(0)}%
                          </span>
                        )}
                        <div className="result-score">
                          {((result.ranked_score || result.original_score || 0) * 100).toFixed(0)}% Match
                        </div>
                      </div>
                    </div>
                    <h3 className="result-title">{result.title}</h3>
                    <p className="result-snippet">{result.content}</p>

                    <div className="result-footer">
                      <div className="result-tags">
                        {(result.match_reasons || result.tags || []).map((tag) => (
                          <span key={tag} className="tag">{tag}</span>
                        ))}
                      </div>
                      <a
                        href={result.url || '#'}
                        className="result-link"
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        Read full <ChevronRight size={16} />
                      </a>
                    </div>
                  </article>
                ))}
              </div>
            </div>
          ) : (
            <div className="no-results animate-fade-in">
              <p>No results found for your precise intent.</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default SearchPage;
