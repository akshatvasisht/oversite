import { useState, type ReactElement } from 'react';
import api from './api';
import { BrowserRouter as Router, Navigate, Route, Routes, useNavigate, useParams } from 'react-router-dom';
import { AuthProvider } from './AuthContext';
import AIChatPanel, { type PendingSuggestion } from './components/AIChatPanel';
import AdminDashboardPage from './components/AdminDashboard';
import FileExplorer from './components/FileExplorer';
import MonacoEditorWrapper from './components/MonacoEditorWrapper';
import ScoreDetailPage from './components/ScoreDetailPage';
import { Badge } from './components/ui/badge';
import { Button } from './components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './components/ui/card';
import { Input } from './components/ui/input';
import { useAuth } from './hooks/useAuth';
import { useAutosave } from './hooks/useAutosave';
import { useSession } from './hooks/useSession';
import './App.css';

const LoginPage = () => {
  const { login, isAuthenticated, role } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState('');

  if (isAuthenticated) {
    return <Navigate to={role === 'admin' ? '/admin' : '/questions'} replace />;
  }

  const signInAs = (user: string): void => {
    const normalized = user.trim().toLowerCase();
    const loginRole = normalized === 'admin' ? 'admin' : 'candidate';
    login(normalized, loginRole);
    navigate(loginRole === 'admin' ? '/admin' : '/questions', { replace: true });
  };

  return (
    <div className="login-screen">
      <p className="login-brand">MadData</p>
      <Card className="login-card">
        <CardHeader>
          <CardTitle>Sign In</CardTitle>
          <CardDescription>Use your assigned test account to continue.</CardDescription>
        </CardHeader>
        <CardContent>
          <form
            onSubmit={(event) => {
              event.preventDefault();
              if (username.trim()) signInAs(username);
            }}
            className="login-form"
          >
            <label htmlFor="username" style={{ fontSize: 13, color: 'var(--text-muted)', fontWeight: 500 }}>Username</label>
            <Input
              id="username"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              placeholder="testuser1 or admin"
            />
            <Button type="submit">Sign In</Button>
          </form>
          <div className="demo-divider">quick access</div>
          <div className="demo-row">
            <Button type="button" variant="secondary" onClick={() => signInAs('testuser1')}>
              Demo Candidate
            </Button>
            <Button type="button" variant="secondary" onClick={() => signInAs('admin')}>
              Demo Admin
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

const QuestionsPage = () => {
  const { role, logout } = useAuth();
  const navigate = useNavigate();
  if (role !== 'candidate') return <Navigate to="/login" replace />;

  const questions = [
    { id: 'q1', company: 'MadData', title: 'Data Pipeline Challenge', duration: '60 min', status: 'pending' },
  ];

  const statusVariant = (status: string): 'outline' | 'secondary' | 'warning' => {
    if (status === 'submitted') return 'secondary';
    if (status === 'in progress') return 'warning';
    return 'outline';
  };

  return (
    <div className="screen dashboard-screen">
      <div className="dashboard-topbar">
        <div>
          <p className="eyebrow">MadData</p>
          <h1>Your Assessments</h1>
        </div>
        <Button type="button" variant="outline" onClick={logout}>Logout</Button>
      </div>
      <p className="muted" style={{ marginBottom: 20, fontSize: 14 }}>Select an assignment to open the coding workspace.</p>
      <div className="question-grid">
        {questions.map((question) => (
          <div key={question.id} className={`question-card ${question.status === 'submitted' ? 'done' : ''}`}>
            <div className="question-header">
              <p className="eyebrow">{question.company}</p>
              <Badge variant={statusVariant(question.status)}>{question.status}</Badge>
            </div>
            <div className="question-content">
              <h2>{question.title}</h2>
              <p className="muted" style={{ margin: 0, fontSize: 13 }}>{question.duration}</p>
              <Button
                disabled={question.status === 'submitted'}
                onClick={() => navigate(`/session/${question.id}`)}
              >
                {question.status === 'submitted' ? 'Completed' : 'Open Workspace'}
              </Button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};


const SessionPage = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [terminalLines, setTerminalLines] = useState<string[]>([
    'System: Environment ready.',
    'System: Run your solution to verify output.',
  ]);
  const [pendingSuggestion, setPendingSuggestion] = useState<PendingSuggestion | null>(null);
  const [showSubmitModal, setShowSubmitModal] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const { userId, setSessionId } = useAuth();
  const {
    loading,
    error,
    sessionId,
    files,
    activeFileId,
    activeFile,
    activeContent,
    selectFile,
    createFile,
    updateActiveContent,
    saveEditorEvent,
  } = useSession({
    routeSessionId: id ?? 'test',
    username: userId ?? 'candidate',
    setSessionIdInContext: setSessionId,
  });
  const { status: autosaveStatus } = useAutosave({
    fileId: activeFile?.fileId ?? null,
    content: activeContent,
    onSave: saveEditorEvent,
    delayMs: 2000,
  });

  const sendPanelEvent = (panel: string): void => {
    if (!sessionId) return;
    void api.post('/events/panel', { panel });
  };

  const runCode = async (): Promise<void> => {
    const name = activeFile?.filename ?? 'main.py';
    const cmd = `python ${name}`;
    setTerminalLines((prev) => [...prev, `> ${cmd}`]);
    try {
      await api.post('/events/execute', { command: cmd, exit_code: 0, output: 'Execution finished.' });
      setTerminalLines((prev) => [...prev, 'Execution finished.']);
    } catch {
      setTerminalLines((prev) => [...prev, 'Execution finished.']);
    }
  };

  const confirmSubmit = async (): Promise<void> => {
    if (!sessionId) return;
    setSubmitting(true);
    try {
      await api.post('/session/end', { final_phase: 'verification' });
    } catch {
      // best-effort — navigate regardless
    } finally {
      setSubmitting(false);
      setShowSubmitModal(false);
      navigate('/questions');
    }
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh', background: 'var(--bg-base)' }}>
        <p style={{ color: 'var(--text-muted)', fontSize: 14 }}>Starting session...</p>
      </div>
    );
  }

  const autosaveLabel =
    autosaveStatus === 'saving' ? 'Saving...' :
    autosaveStatus === 'saved'  ? 'Saved ✓' :
    autosaveStatus === 'error'  ? 'Save failed' : 'Idle';

  return (
    <>
      {showSubmitModal && (
        <div className="modal-overlay">
          <div className="modal-card">
            <h3>End Session?</h3>
            <p className="muted" style={{ margin: 0, fontSize: 13 }}>This will submit your solution and cannot be undone.</p>
            <div className="modal-actions">
              <Button variant="outline" onClick={() => setShowSubmitModal(false)} disabled={submitting}>Cancel</Button>
              <Button onClick={() => void confirmSubmit()} disabled={submitting}>
                {submitting ? 'Submitting...' : 'Confirm Submit'}
              </Button>
            </div>
          </div>
        </div>
      )}

      <div className="ide-wrapper">
        {/* Top nav bar */}
        <div className="session-topbar">
          <span className="session-topbar-brand">MadData</span>
          <span className="session-topbar-sep">›</span>
          <span className="session-topbar-title">Session {id}</span>
          <div className="session-topbar-actions">
            <Badge variant="secondary" className="status-pill">
              {autosaveLabel}
            </Badge>
            <Button
              variant="outline"
              size="sm"
              onClick={(e) => { e.stopPropagation(); void runCode(); }}
            >
              ▶ Run
            </Button>
            <Button
              size="sm"
              onClick={(e) => { e.stopPropagation(); setShowSubmitModal(true); }}
            >
              Submit
            </Button>
          </div>
        </div>

        {/* IDE panels */}
        <div className="ide-shell">
          <section className="problem-pane" onClick={() => sendPanelEvent('orientation')}>
            <div className="pane-title">Problem</div>
            <div className="pane-body">
              <h2>Session {id}</h2>
              <p>Build a clean and testable solution. Use multiple files if needed.</p>
              <ul>
                <li>Keep logic modular.</li>
                <li>Include edge-case handling.</li>
                <li>Explain assumptions in comments.</li>
              </ul>
              {sessionId && <p className="muted">Session: {sessionId.slice(0, 8)}…</p>}
              {error && <p className="error-text">{error}</p>}
            </div>
          </section>

          <section className="workspace-pane" onClick={() => sendPanelEvent('editor')}>
            <div className="editor-toolbar">
              <span>Editing&nbsp;<strong>{activeFile?.filename ?? 'No file selected'}</strong></span>
              <span className="lang-pill">{activeFile?.language ?? 'python'}</span>
            </div>
            <div className="workspace-top">
              <FileExplorer
                files={files}
                activeFileId={activeFileId}
                onSelectFile={selectFile}
                onCreateFile={createFile}
              />
              <MonacoEditorWrapper
                fileId={activeFile?.fileId}
                content={activeContent}
                language={activeFile?.language ?? 'python'}
                onChange={(value) => updateActiveContent(value ?? '')}
              />
            </div>
            <div className="terminal-pane">
              <div className="terminal-title">Terminal</div>
              <div className="terminal-body">
                {terminalLines.map((line, index) => (
                  <div key={`${line}-${index}`}>{line}</div>
                ))}
              </div>
            </div>
          </section>

          <section className="assistant-pane" onClick={() => sendPanelEvent('chat')}>
            <div className="pane-title">AI Assistant</div>
            <AIChatPanel
              sessionId={sessionId}
              activeFileId={activeFileId}
              activeContent={activeContent}
              pendingSuggestion={pendingSuggestion}
              onSuggestion={setPendingSuggestion}
              onResolvePending={() => setPendingSuggestion(null)}
            />
            <div className="submit-box">
              <p className="muted">Final Submission</p>
              <Button
                type="button"
                style={{ width: '100%' }}
                onClick={(e) => { e.stopPropagation(); setShowSubmitModal(true); }}
              >
                Submit Solution
              </Button>
            </div>
          </section>
        </div>
      </div>
    </>
  );
};

const ProtectedRoute = ({ children, allowedRole }: { children: ReactElement, allowedRole?: 'admin' | 'candidate' }) => {
  const { isAuthenticated, role } = useAuth();
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  if (allowedRole && role !== allowedRole) {
    return <Navigate to={role === 'admin' ? '/admin' : '/questions'} replace />;
  }
  return children;
};

const AppRoutes = () => {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/questions" element={<ProtectedRoute allowedRole="candidate"><QuestionsPage /></ProtectedRoute>} />
      <Route path="/admin" element={<ProtectedRoute allowedRole="admin"><AdminDashboardPage /></ProtectedRoute>} />
      <Route path="/admin/:candidateId" element={<ProtectedRoute allowedRole="admin"><ScoreDetailPage /></ProtectedRoute>} />
      <Route path="/session/:id" element={<ProtectedRoute allowedRole="candidate"><SessionPage /></ProtectedRoute>} />
      <Route path="/" element={<Navigate to="/login" replace />} />
    </Routes>
  );
};

function App() {
  return (
    <AuthProvider>
      <Router>
        <AppRoutes />
      </Router>
    </AuthProvider>
  );
}

export default App;
