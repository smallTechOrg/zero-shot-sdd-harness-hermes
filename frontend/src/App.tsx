import { useState } from 'react';
import './index.css';
import Upload from './components/Upload';
import Dashboard from './components/Dashboard';

interface AnalyzeResponse {
  summary: string;
  findings: string[];
  charts: any[];
  recommendations: string[];
}

function App() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<AnalyzeResponse | null>(null);

  const handleUploadComplete = (id: string) => {
    setSessionId(id);
    setError(null);
  };

  const handleAnalyze = async (query: string) => {
    if (!sessionId) return;
    setLoading(true);
    setError(null);
    try {
      const response = await fetch('/api/analyze', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ session_id: sessionId, query })
      });
      
      const result = await response.json();
      
      if (!response.ok) {
        throw new Error(result.detail || 'Analysis failed');
      }
      
      setData(result);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app-container">
      <header className="app-header">
        <h1>Crime Statistics Analysis</h1>
        <p>AI-Powered Detectives Dashboard</p>
      </header>

      <main className="app-main">
        {!sessionId ? (
          <Upload onUploadComplete={handleUploadComplete} />
        ) : (
          <div className="analysis-section">
            <div className="query-box">
              <h2>Ask a Question</h2>
              <form onSubmit={(e) => {
                e.preventDefault();
                const fd = new FormData(e.currentTarget);
                handleAnalyze(fd.get('query') as string);
              }}>
                <textarea 
                  name="query" 
                  placeholder="e.g., Which district has the highest crime rate?" 
                  rows={3} 
                  required
                />
                <button type="submit" disabled={loading}>
                  {loading ? 'Analyzing...' : 'Analyze'}
                </button>
              </form>
            </div>

            {error && <div className="error-message">{error}</div>}

            {data && <Dashboard data={data} />}
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
