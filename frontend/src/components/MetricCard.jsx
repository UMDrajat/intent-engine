import { TrendingUp, TrendingDown } from 'lucide-react';
import classNames from 'classnames';
import './MetricCard.css';

function MetricCard({ label, value, icon: Icon, trend, delay = 0 }) {
  return (
    <div
      className={classNames('metric-card', 'animate-slide-up')}
      style={{ animationDelay: `${delay}s` }}
    >
      <div className="metric-header">
        {Icon && (
          <div className="metric-icon">
            <Icon size={18} />
          </div>
        )}
        {trend !== undefined && (
          <span className={classNames('metric-trend', { positive: trend >= 0, negative: trend < 0 })}>
            {trend >= 0 ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
            {Math.abs(trend).toFixed(1)}%
          </span>
        )}
      </div>
      <div className="metric-value">{value}</div>
      <div className="metric-label">{label}</div>
    </div>
  );
}

export default MetricCard;
