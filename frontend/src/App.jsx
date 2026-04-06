import { useState } from 'react';
import Header from './components/Header';
import SearchPage from './pages/SearchPage';
import AnalyticsPage from './pages/AnalyticsPage';
import PrivacyPage from './pages/PrivacyPage';
import './App.css';

function App() {
  const [currentPage, setCurrentPage] = useState('search');

  return (
    <div className="app-container">
      <Header currentPage={currentPage} onNavigate={setCurrentPage} />
      <main className="main-content" key={currentPage}>
        {currentPage === 'search' && <SearchPage />}
        {currentPage === 'analytics' && <AnalyticsPage />}
        {currentPage === 'privacy' && <PrivacyPage />}
      </main>
    </div>
  );
}

export default App;
