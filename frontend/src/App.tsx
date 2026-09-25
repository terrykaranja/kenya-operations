import { useCallback, useEffect, useState } from 'react';
import amexLogo from './assets/amex-logo.png';
import { getMe, logout } from './services/api';
import type { ExtractionResponse, User } from './types/api';
import { Toast, useToast } from './components/ui/Toast';
import { LoginScreen } from './components/screens/LoginScreen';
import { DashboardScreen } from './components/screens/DashboardScreen';
import { UploadScreen } from './components/screens/UploadScreen';
import { ImportReviewScreen } from './components/screens/ImportReviewScreen';
import { ExportReviewScreen } from './components/screens/ExportReviewScreen';
import { SearchScreen } from './components/screens/SearchScreen';
import { AuditScreen } from './components/screens/AuditScreen';
import { DownloadScreen } from './components/screens/DownloadScreen';
import { AdminScreen } from './components/screens/AdminScreen';

type Page = 'dashboard' | 'upload-import' | 'upload-export' | 'review-import' | 'review-export' | 'search' | 'audit' | 'download' | 'admin';

function App() {
  const [user, setUser] = useState<User | null>(null);
  const [authChecked, setAuthChecked] = useState(false);
  const [page, setPage] = useState<Page>('dashboard');
  const [extraction, setExtraction] = useState<ExtractionResponse | null>(null);
  const { toast, show: showToast, clear: clearToast } = useToast();

  // Check if already logged in
  useEffect(() => {
    getMe()
      .then(setUser)
      .catch(() => {})
      .finally(() => setAuthChecked(true));
  }, []);

  const handleLogout = async () => {
    await logout().catch(() => {});
    setUser(null);
    setPage('dashboard');
  };

  const navigate = useCallback((p: string) => setPage(p as Page), []);

  if (!authChecked) {
    return <div className="min-h-screen flex items-center justify-center bg-brand-white font-body text-charcoal/60">Loading...</div>;
  }

  if (!user) {
    return (
      <>
        <LoginScreen onLogin={u => { setUser(u); setPage('dashboard'); }} />
        {toast && <Toast message={toast.message} type={toast.type} onClose={clearToast} />}
      </>
    );
  }

  const navItems: { key: Page; label: string; adminOnly?: boolean }[] = [
    { key: 'dashboard', label: 'Dashboard' },
    { key: 'search', label: 'Search' },
    { key: 'audit', label: 'Audit Log' },
    { key: 'download', label: 'Download' },
    { key: 'admin', label: 'Admin', adminOnly: true },
  ];

  return (
    <div className="min-h-screen bg-brand-white text-charcoal">
      {/* Header */}
      <header className="border-b border-cool-steel/30 bg-white sticky top-0 z-40">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-3">
          <div className="flex items-center gap-6">
            <img src={amexLogo} alt="AMEX Healthcare" className="h-7 w-auto" />
            <nav className="flex gap-1">
              {navItems
                .filter(n => !n.adminOnly || user.is_admin)
                .map(n => (
                  <button
                    key={n.key}
                    onClick={() => setPage(n.key)}
                    className={`px-3 py-1.5 rounded font-body text-sm transition-colors ${
                      page === n.key ? 'bg-oxblood/10 text-oxblood font-medium' : 'text-charcoal/70 hover:text-charcoal hover:bg-cool-steel/10'
                    }`}
                  >
                    {n.label}
                  </button>
                ))}
            </nav>
          </div>
          <div className="flex items-center gap-4">
            <span className="font-body text-sm text-charcoal/60">{user.username}</span>
            <button onClick={handleLogout} className="font-body text-sm text-oxblood hover:underline">Sign Out</button>
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="mx-auto max-w-6xl px-6 py-8">
        {page === 'dashboard' && <DashboardScreen onNavigate={navigate} />}

        {page === 'upload-import' && (
          <UploadScreen
            docType="import"
            onExtracted={result => { setExtraction(result); setPage('review-import'); }}
            onNavigate={navigate}
          />
        )}

        {page === 'upload-export' && (
          <UploadScreen
            docType="export"
            onExtracted={result => { setExtraction(result); setPage('review-export'); }}
            onNavigate={navigate}
          />
        )}

        {page === 'review-import' && extraction && (
          <ImportReviewScreen
            extraction={extraction}
            onConfirmed={() => { setExtraction(null); setPage('dashboard'); }}
            onNavigate={navigate}
            showToast={showToast}
          />
        )}

        {page === 'review-export' && extraction && (
          <ExportReviewScreen
            extraction={extraction}
            onConfirmed={() => { setExtraction(null); setPage('dashboard'); }}
            onNavigate={navigate}
            showToast={showToast}
          />
        )}

        {page === 'search' && <SearchScreen onNavigate={navigate} showToast={showToast} />}
        {page === 'audit' && <AuditScreen onNavigate={navigate} showToast={showToast} />}
        {page === 'download' && <DownloadScreen isAdmin={user.is_admin} onNavigate={navigate} showToast={showToast} />}
        {page === 'admin' && user.is_admin && <AdminScreen currentUser={user} onNavigate={navigate} showToast={showToast} />}
      </main>

      {/* Footer */}
      <footer className="border-t border-cool-steel/20 py-4 mt-8">
        <p className="text-center font-body text-xs text-charcoal/40">
          SEZ Ledger Automation &mdash; Kenya Operations Track #11 &mdash; AMEX Healthcare Hackathon
        </p>
      </footer>

      {toast && <Toast message={toast.message} type={toast.type} onClose={clearToast} />}
    </div>
  );
}

export default App;
