import { useState, useRef, useEffect } from 'react';
import './index.css';
import Upload from './components/Upload';
import Dashboard from './components/Dashboard';

interface AnalyzeResponse {
  summary: string;
  findings: string[];
  charts: any[];
  recommendations: string[];
}

interface ChatTurn {
  id: string;
  query: string;
  response: AnalyzeResponse | null;
  loading: boolean;
  error: string | null;
}

function App() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const chatEndRef = useRef<HTMLDivElement>(null);

  const handleUploadComplete = (id: string) => {
    setSessionId(id);
    setTurns([]);
  };

  const scrollToBottom = () => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [turns]);

  const handleAnalyze = async (query: string) => {
    if (!sessionId || !query.trim()) return;
    
    const turnId = Math.random().toString(36).substring(7);
    const newTurn: ChatTurn = { id: turnId, query, response: null, loading: true, error: null };
    
    setTurns(prev => [...prev, newTurn]);

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
      
      setTurns(prev => prev.map(t => t.id === turnId ? { ...t, loading: false, response: result } : t));
    } catch (err: any) {
      setTurns(prev => prev.map(t => t.id === turnId ? { ...t, loading: false, error: err.message } : t));
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
          <div className="chat-interface">
            <div className="chat-history">
              {turns.length === 0 && (
                <div className="empty-chat">
                  <p>Upload successful. Start asking questions about your crime data!</p>
                </div>
              )}
              {turns.map((turn, idx) => (
                <div key={turn.id} className="chat-turn">
                  <div className="user-message">
                    <span className="avatar user-avatar">Q</span>
                    <div className="message-content">{turn.query}</div>
                  </div>
                  
                  <div className="ai-message">
                    <span className="avatar ai-avatar">A</span>
                    <div className="message-content">
                      {turn.loading ? (
                        <div className="loading-indicator">Analyzing data...</div>
                      ) : turn.error ? (
                        <div className="error-message">{turn.error}</div>
                      ) : turn.response ? (
                        <Dashboard data={turn.response} isLatest={idx === turns.length - 1} />
                      ) : null}
                    </div>
                  </div>
                </div>
              ))}
              <div ref={chatEndRef} />
            </div>

            <div className="query-box sticky-query">
              <form onSubmit={(e) => {
                e.preventDefault();
                const fd = new FormData(e.currentTarget);
                const q = fd.get('query') as string;
                if (q) handleAnalyze(q);
                e.currentTarget.reset();
              }}>
                <textarea 
                  name="query" 
                  placeholder="e.g., Which district has the highest crime rate?" 
                  rows={2} 
                  required
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault();
                      e.currentTarget.form?.dispatchEvent(new Event('submit', { cancelable: true, bubbles: true }));
                    }
                  }}
                />
                <button type="submit" disabled={turns.some(t => t.loading)}>
                  Analyze
                </button>
              </form>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
