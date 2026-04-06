import { Sparkles } from 'lucide-react';
import classNames from 'classnames';
import './Header.css';

function Header({ currentPage, onNavigate }) {
  return (
    <header className="header animate-fade-in">
      <div className="logo-container">
        <div className="logo-mark"><Sparkles size={20} /></div>
        <span className="logo-text">Intent Engine</span>
      </div>
      <nav className="nav-links">
        {['search', 'analytics', 'privacy'].map((page) => (
          <a
            key={page}
            href="#"
            className={classNames('nav-link', { active: currentPage === page })}
            onClick={(e) => { e.preventDefault(); onNavigate(page); }}
          >
            {page.charAt(0).toUpperCase() + page.slice(1)}
          </a>
        ))}
      </nav>
    </header>
  );
}

export default Header;
