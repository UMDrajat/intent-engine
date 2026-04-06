const API_BASE = '/api';

async function request(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) throw new Error(`API ${res.status}: ${res.statusText}`);
  return res.json();
}

export function searchAPI(query, options = {}) {
  return request('/search', {
    method: 'POST',
    body: JSON.stringify({
      query,
      extract_intent: true,
      rank_results: true,
      max_results: 20,
      ...options,
    }),
  });
}

export function getConsentSummary() {
  return request('/consent-summary');
}

export function getAuditStats() {
  return request('/audit-stats');
}

export function getCampaignPerformance() {
  return request('/reports/campaign-performance');
}

export function getHealthDetailed() {
  return request('/health/detailed');
}

export function connectAnalyticsWS() {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  return new WebSocket(`${protocol}//${window.location.host}/ws/analytics`);
}
