import { useCallback } from 'react';
import {
  Eye, MousePointerClick, Target, Percent,
  DollarSign, Activity, Users, Radio,
  BarChart3, AlertTriangle, RefreshCw
} from 'lucide-react';
import MetricCard from '../components/MetricCard';
import { useApi } from '../hooks/useApi';
import { useWebSocket } from '../hooks/useWebSocket';
import { getCampaignPerformance } from '../api/client';
import { mockCampaignPerformance } from '../api/mockData';
import './AnalyticsPage.css';

function formatNumber(n) {
  if (n == null) return '—';
  if (n >= 1000000) return (n / 1000000).toFixed(1) + 'M';
  if (n >= 1000) return (n / 1000).toFixed(1) + 'K';
  return n.toLocaleString();
}

function AnalyticsPage() {
  const wsUrl = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws/analytics`;
  const { metrics, connected } = useWebSocket(wsUrl);

  const campaignFetcher = useCallback(() => getCampaignPerformance(), []);
  const { data: campaigns, loading: campaignsLoading, isDemo, refetch } = useApi(
    campaignFetcher,
    mockCampaignPerformance
  );

  return (
    <div className="analytics-page animate-fade-in">
      <div className="page-header animate-slide-up">
        <div className="page-header-text">
          <span className="page-kicker">Dashboard</span>
          <h1 className="page-title">Analytics</h1>
          <p className="page-subtitle">Real-time campaign insights and performance metrics.</p>
        </div>
        <div className="connection-status">
          <span className={`status-dot ${connected ? 'live' : metrics ? 'demo' : 'offline'}`} />
          <span className="status-label">
            {connected ? 'Live' : metrics ? 'Demo' : 'Offline'}
          </span>
        </div>
      </div>

      {/* Live Metrics */}
      <section className="metrics-section animate-slide-up delay-100">
        <h2 className="section-title">Live Metrics</h2>
        <div className="metrics-grid">
          <MetricCard
            label="Impressions"
            value={formatNumber(metrics?.impressions)}
            icon={Eye}
            delay={0.1}
          />
          <MetricCard
            label="Clicks"
            value={formatNumber(metrics?.clicks)}
            icon={MousePointerClick}
            delay={0.15}
          />
          <MetricCard
            label="Conversions"
            value={formatNumber(metrics?.conversions)}
            icon={Target}
            delay={0.2}
          />
          <MetricCard
            label="Click-Through Rate"
            value={metrics?.ctr != null ? `${metrics.ctr.toFixed(2)}%` : '—'}
            icon={Percent}
            delay={0.25}
          />
        </div>
      </section>

      {/* Secondary Metrics */}
      <section className="metrics-section animate-slide-up delay-200">
        <h2 className="section-title">Performance</h2>
        <div className="metrics-grid">
          <MetricCard
            label="Cost per Click"
            value={metrics?.cpc != null ? `$${metrics.cpc.toFixed(2)}` : '—'}
            icon={DollarSign}
            delay={0.1}
          />
          <MetricCard
            label="Return on Ad Spend"
            value={metrics?.roas != null ? `${metrics.roas.toFixed(1)}x` : '—'}
            icon={Activity}
            delay={0.15}
          />
          <MetricCard
            label="Active Campaigns"
            value={metrics?.active_campaigns ?? '—'}
            icon={Radio}
            delay={0.2}
          />
          <MetricCard
            label="Live Users"
            value={formatNumber(metrics?.live_users)}
            icon={Users}
            delay={0.25}
          />
        </div>
      </section>

      {/* Campaign Performance Table */}
      <section className="table-section animate-slide-up delay-300">
        <div className="section-header">
          <h2 className="section-title">
            <BarChart3 size={18} /> Campaign Performance
          </h2>
          <button className="refresh-button" onClick={refetch}>
            <RefreshCw size={14} /> Refresh
          </button>
        </div>

        {campaignsLoading ? (
          <div className="table-skeleton">
            <div className="skeleton-item" style={{ '--delay': '0s', height: '60px' }} />
            <div className="skeleton-item" style={{ '--delay': '0.1s', height: '60px' }} />
            <div className="skeleton-item" style={{ '--delay': '0.2s', height: '60px' }} />
          </div>
        ) : campaigns && campaigns.length > 0 ? (
          <div className="table-card">
            {isDemo && <div className="demo-banner">Demo data — connect backend for live metrics</div>}
            <table className="data-table">
              <thead>
                <tr>
                  <th>Campaign</th>
                  <th>Impressions</th>
                  <th>Clicks</th>
                  <th>CTR</th>
                  <th>CPC</th>
                  <th>ROAS</th>
                </tr>
              </thead>
              <tbody>
                {campaigns.map((c) => (
                  <tr key={c.campaign_id}>
                    <td className="campaign-name">{c.campaign_name}</td>
                    <td>{formatNumber(c.impressions)}</td>
                    <td>{formatNumber(c.clicks)}</td>
                    <td>{c.ctr.toFixed(2)}%</td>
                    <td>${c.cpc.toFixed(2)}</td>
                    <td className="roas-cell">{c.roas.toFixed(1)}x</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="empty-state">
            <AlertTriangle size={24} />
            <p>No campaign data available.</p>
          </div>
        )}
      </section>
    </div>
  );
}

export default AnalyticsPage;
