import { useCallback } from 'react';
import {
  ShieldCheck, Lock, FileCheck, ClipboardList,
  CheckCircle2, Users, XCircle, Percent,
  AlertTriangle, RefreshCw, Activity
} from 'lucide-react';
import MetricCard from '../components/MetricCard';
import { useApi } from '../hooks/useApi';
import { getConsentSummary, getAuditStats } from '../api/client';
import { mockConsentSummary, mockAuditStats } from '../api/mockData';
import './PrivacyPage.css';

function formatNumber(n) {
  if (n == null) return '—';
  return n.toLocaleString();
}

function PrivacyPage() {
  const consentFetcher = useCallback(() => getConsentSummary(), []);
  const auditFetcher = useCallback(() => getAuditStats(), []);

  const { data: consent, loading: consentLoading, isDemo: consentDemo, refetch: refetchConsent } = useApi(
    consentFetcher,
    mockConsentSummary
  );
  const { data: audit, loading: auditLoading, isDemo: auditDemo, refetch: refetchAudit } = useApi(
    auditFetcher,
    mockAuditStats
  );

  const isDemo = consentDemo || auditDemo;
  const maxByType = consent?.by_type
    ? Math.max(...Object.values(consent.by_type))
    : 1;

  const maxDaily = audit?.daily_counts
    ? Math.max(...audit.daily_counts.map((d) => d.count))
    : 1;

  return (
    <div className="privacy-page animate-fade-in">
      <div className="page-header animate-slide-up">
        <div className="page-header-text">
          <span className="page-kicker">Compliance</span>
          <h1 className="page-title">Privacy</h1>
          <p className="page-subtitle">Consent management and compliance audit trail.</p>
        </div>
        {isDemo && <span className="demo-tag">Demo</span>}
      </div>

      {/* Consent Overview */}
      <section className="privacy-section animate-slide-up delay-100">
        <div className="section-header">
          <h2 className="section-title"><ShieldCheck size={18} /> Consent Overview</h2>
          <button className="refresh-button" onClick={() => { refetchConsent(); refetchAudit(); }}>
            <RefreshCw size={14} /> Refresh
          </button>
        </div>

        {consentLoading ? (
          <div className="metrics-grid">
            {[0, 1, 2, 3].map((i) => (
              <div key={i} className="skeleton-item metric-skeleton" style={{ '--delay': `${i * 0.1}s` }} />
            ))}
          </div>
        ) : consent ? (
          <div className="metrics-grid">
            <MetricCard
              label="Total Consents"
              value={formatNumber(consent.total_consents)}
              icon={Users}
              delay={0.1}
            />
            <MetricCard
              label="Granted"
              value={formatNumber(consent.granted_consents)}
              icon={CheckCircle2}
              delay={0.15}
            />
            <MetricCard
              label="Denied"
              value={formatNumber(consent.denied_consents)}
              icon={XCircle}
              delay={0.2}
            />
            <MetricCard
              label="Compliance Rate"
              value={consent.overall_compliance_rate != null
                ? `${consent.overall_compliance_rate.toFixed(1)}%`
                : '—'}
              icon={Percent}
              delay={0.25}
            />
          </div>
        ) : null}
      </section>

      {/* Consent by Type */}
      {consent?.by_type && (
        <section className="privacy-section animate-slide-up delay-200">
          <h2 className="section-title"><ClipboardList size={18} /> Consent by Type</h2>
          <div className="bar-chart-card">
            {Object.entries(consent.by_type).map(([type, count]) => (
              <div key={type} className="bar-row">
                <span className="bar-label">{type}</span>
                <div className="bar-track">
                  <div
                    className="bar-fill"
                    style={{ width: `${(count / maxByType) * 100}%` }}
                  />
                </div>
                <span className="bar-value">{formatNumber(count)}</span>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Audit Trail */}
      <section className="privacy-section animate-slide-up delay-300">
        <h2 className="section-title"><FileCheck size={18} /> Audit Trail</h2>

        {auditLoading ? (
          <div className="skeleton-item" style={{ '--delay': '0s', height: '200px' }} />
        ) : audit ? (
          <>
            <div className="audit-overview">
              <div className="audit-stat-card">
                <div className="audit-stat-value">{formatNumber(audit.total_events)}</div>
                <div className="audit-stat-label">Total Events</div>
              </div>
              <div className="audit-stat-card accent">
                <div className="audit-stat-value">{formatNumber(audit.recent_activity)}</div>
                <div className="audit-stat-label">Last 24 Hours</div>
              </div>
            </div>

            {/* Events by Type */}
            {audit.events_by_type && (
              <div className="event-type-grid">
                {Object.entries(audit.events_by_type).map(([type, count]) => (
                  <div key={type} className="event-type-card">
                    <span className="event-type-count">{formatNumber(count)}</span>
                    <span className="event-type-name">{type.replace(/_/g, ' ')}</span>
                  </div>
                ))}
              </div>
            )}

            {/* Daily Activity */}
            {audit.daily_counts?.length > 0 && (
              <div className="daily-activity">
                <h3 className="subsection-title"><Activity size={16} /> Daily Activity</h3>
                <div className="daily-bars">
                  {audit.daily_counts.map((day) => (
                    <div key={day.date} className="daily-bar-col">
                      <div className="daily-bar-wrapper">
                        <div
                          className="daily-bar"
                          style={{ height: `${(day.count / maxDaily) * 100}%` }}
                        />
                      </div>
                      <span className="daily-label">
                        {new Date(day.date).toLocaleDateString('en', { weekday: 'short' })}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        ) : (
          <div className="empty-state">
            <AlertTriangle size={24} />
            <p>No audit data available.</p>
          </div>
        )}
      </section>

      {/* Privacy Badges */}
      <section className="privacy-section animate-slide-up delay-400">
        <h2 className="section-title"><Lock size={18} /> Privacy Guarantees</h2>
        <div className="badges-grid">
          <div className="privacy-badge-card">
            <ShieldCheck size={28} className="badge-icon" />
            <h3>Privacy Enhanced</h3>
            <p>All search results are scored for privacy compliance and tracker exposure.</p>
          </div>
          <div className="privacy-badge-card">
            <Lock size={28} className="badge-icon" />
            <h3>Tracking Blocked</h3>
            <p>Third-party trackers are identified and blocked before results reach you.</p>
          </div>
          <div className="privacy-badge-card">
            <FileCheck size={28} className="badge-icon" />
            <h3>Zero Collection</h3>
            <p>Intent data is session-scoped and never persisted beyond your session TTL.</p>
          </div>
        </div>
      </section>
    </div>
  );
}

export default PrivacyPage;
