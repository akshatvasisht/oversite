import { useState, useEffect, useRef, type ReactElement } from 'react';
import api from './api';
import { BrowserRouter as Router, Navigate, Route, Routes, useNavigate, useParams } from 'react-router-dom';
import { AuthProvider } from './AuthContext';
import AIChatPanel, { type PendingSuggestion } from './components/AIChatPanel';
import AdminDashboardPage from './components/AdminDashboard';
import { ToastProvider, useToast } from './context/ToastContext';
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
import NetworkStatus from './components/NetworkStatus';
import './App.css';

const LoginPage = () => {
  const { login, isAuthenticated, role } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState('');

  if (isAuthenticated) {
    return <Navigate to={role === 'admin' ? '/admin' : '/questions'} replace />;
  }

  const signInAs = async (user: string): Promise<void> => {
    const normalized = user.trim().toLowerCase();
    const pwd = normalized === 'admin1' || normalized === 'admin' ? 'admin123' : 'password123';
    const uName = normalized === 'admin' ? 'admin1'
      : normalized === 'testuser1' ? 'candidate1'
      : normalized === 'testuser2' ? 'candidate2'
      : normalized;

    try {
      const resp = await api.post('/auth/login', { username: uName, password: pwd });
      const { userId: loginUserId, role: loginRole, token } = resp.data;
      login(loginUserId, loginRole, token);
      navigate(loginRole === 'admin' ? '/admin' : '/questions', { replace: true });
    } catch (err) {
      console.error('Login failed', err);
      alert('Login failed. Please check your credentials.');
    }
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
              placeholder="candidate1 or admin1"
            />
            <Button type="submit">Sign In</Button>
          </form>
          <div className="demo-divider">quick access</div>
          <div className="demo-row">
            <Button type="button" variant="secondary" onClick={() => signInAs('candidate1')}>
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
  const { role, userId, logout } = useAuth();
  const navigate = useNavigate();
  const [questions, setQuestions] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (role !== 'candidate') return;
    api.get(`/questions?username=${userId}`)
      .then(res => setQuestions(res.data))
      .catch(err => console.error('Failed to fetch questions', err))
      .finally(() => setLoading(false));
  }, [role, userId]);

  if (role !== 'candidate') return <Navigate to="/login" replace />;

  const statusVariant = (status: string): 'outline' | 'secondary' | 'warning' => {
    if (status === 'submitted') return 'secondary';
    if (status === 'in progress') return 'warning';
    return 'outline';
  };

  const difficultyColor: Record<string, string> = {
    Easy: '#22c55e',
    Medium: '#f59e0b',
    Hard: '#ef4444',
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

      {loading && <p className="muted">Loading assessments...</p>}

      <div className="question-grid">
        {questions.map((question) => (
          <div key={question.id} className={`question-card ${question.status === 'submitted' ? 'done' : ''}`}>
            <div className="question-header">
              <p className="eyebrow">{question.company}</p>
              <Badge variant={statusVariant(question.status)}>{question.status}</Badge>
            </div>
            <div className="question-content">
              <h2>{question.title}</h2>
              <p className="muted" style={{ margin: 0, fontSize: 13, lineHeight: 1.5 }}>{question.description}</p>
              <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
                <span style={{ fontSize: 12, fontWeight: 600, color: difficultyColor[question.difficulty] }}>
                  {question.difficulty}
                </span>
                <span style={{ color: 'var(--text-faint)', fontSize: 12 }}>·</span>
                <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>{question.duration}</span>
                <span style={{ color: 'var(--text-faint)', fontSize: 12 }}>·</span>
                <span style={{ fontSize: 11, color: 'var(--text-faint)', fontFamily: "'JetBrains Mono', monospace" }}>
                  {question.files.join('  ')}
                </span>
              </div>
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
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [activePhase, setActivePhase] = useState<'orientation' | 'implementation' | 'verification'>('orientation');
  const [leftWidth, setLeftWidth] = useState(280);
  const [rightWidth, setRightWidth] = useState(320);
  const dragging = useRef<{ side: 'left' | 'right'; startX: number; startWidth: number } | null>(null);

  useEffect(() => {
    const onMove = (e: MouseEvent) => {
      if (!dragging.current) return;
      const dx = e.clientX - dragging.current.startX;
      if (dragging.current.side === 'left') {
        setLeftWidth(Math.max(180, Math.min(480, dragging.current.startWidth + dx)));
      } else {
        setRightWidth(Math.max(200, Math.min(560, dragging.current.startWidth - dx)));
      }
    };
    const onUp = () => { dragging.current = null; };
    document.addEventListener('mousemove', onMove);
    document.addEventListener('mouseup', onUp);
    return () => {
      document.removeEventListener('mousemove', onMove);
      document.removeEventListener('mouseup', onUp);
    };
  }, []);

  const startDrag = (side: 'left' | 'right', e: React.MouseEvent) => {
    dragging.current = { side, startX: e.clientX, startWidth: side === 'left' ? leftWidth : rightWidth };
    e.preventDefault();
  };

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
    initialElapsedSeconds,
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

  const { showToast } = useToast();

  const sendPanelEvent = (panel: string): void => {
    if (!sessionId) return;
    void api.post('/events/panel', { panel });
  };

  const execute = async (entrypoint: string): Promise<void> => {
    setTerminalLines((prev) => [...prev, `> python ${entrypoint}`]);
    try {
      const execRes = await api.post('/events/execute', { entrypoint, files });
      const { stdout, stderr, exit_code } = execRes.data as { stdout: string; stderr: string; exit_code: number };

      if (stdout) setTerminalLines((prev) => [...prev, ...stdout.split('\n').filter(l => l.trim() !== '')]);
      if (stderr) setTerminalLines((prev) => [...prev, ...stderr.split('\n').filter(l => l.trim() !== '')]);
      setTerminalLines((prev) => [...prev, `Process exited with code ${exit_code}`]);

      if (exit_code === 0) {
        showToast('Ran successfully ✓', 'success');
      } else {
        showToast('Execution failed', 'error');
      }
    } catch {
      setTerminalLines((prev) => [...prev, 'System: Execution engine unavailable.']);
      showToast('Engine unavailable', 'error');
    }
  };

  const runCode = (): Promise<void> => execute(activeFile?.filename ?? 'main.py');
  const runTests = (): Promise<void> => execute('tests/test_cart.py');

  useEffect(() => {
    setElapsedSeconds(initialElapsedSeconds);
  }, [initialElapsedSeconds]);

  useEffect(() => {
    const interval = setInterval(() => {
      setElapsedSeconds(prev => prev + 1);
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  const handlePhaseChange = async (phase: 'orientation' | 'implementation' | 'verification') => {
    setActivePhase(phase);
    try {
      await api.patch('/session/phase', { phase });
    } catch (err) {
      console.error('Failed to update phase', err);
    }
  };

  const formatTime = (seconds: number) => {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m}:${s.toString().padStart(2, '0')}`;
  };

  const confirmSubmit = async (): Promise<void> => {
    if (!sessionId) return;
    setSubmitting(true);
    try {
      await api.post('/session/end', { final_phase: 'verification' });
      showToast('Submission Successful', 'success');
    } catch {
      showToast('Failed to submit session', 'error');
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
      autosaveStatus === 'saved' ? 'Saved ✓' :
        autosaveStatus === 'error' ? 'Save failed' : 'Idle';

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

          <div className="phase-navigation">
            <button
              className={`phase-btn ${activePhase === 'orientation' ? 'active' : ''}`}
              onClick={() => handlePhaseChange('orientation')}
            >
              1. Orientation
            </button>
            <button
              className={`phase-btn ${activePhase === 'implementation' ? 'active' : ''}`}
              onClick={() => handlePhaseChange('implementation')}
            >
              2. Implementation
            </button>
            <button
              className={`phase-btn ${activePhase === 'verification' ? 'active' : ''}`}
              onClick={() => handlePhaseChange('verification')}
            >
              3. Verification
            </button>
          </div>

          <div className="session-topbar-actions">
            <div className="session-timer">{formatTime(elapsedSeconds)}</div>
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
              variant="outline"
              size="sm"
              onClick={(e) => { e.stopPropagation(); void runTests(); }}
            >
              ✓ Test
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
          <section className="problem-pane" style={{ width: leftWidth, minWidth: leftWidth }} onClick={() => sendPanelEvent('orientation')}>
            <div className="pane-title">Problem</div>
            <div className="pane-body">
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
                <h2 style={{ margin: 0 }}>Shopping Cart Debugger</h2>
                <Badge variant="warning">Medium</Badge>
              </div>

              <p style={{ marginTop: 0 }}>
                Your team's e-commerce checkout is generating <strong>incorrect totals</strong> when
                customers use a discount coupon on a large order. QA has confirmed the bug only
                appears when <em>both</em> a coupon code and a quantity-based discount are active at
                the same time.
              </p>

              <h3 style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.07em', margin: '16px 0 8px' }}>The Bug</h3>
              <p style={{ margin: '0 0 12px' }}>
                The <code style={{ background: 'var(--code-bg)', padding: '1px 5px', borderRadius: 4, fontSize: 12, fontFamily: "'JetBrains Mono', monospace" }}>DiscountEngine.apply()</code> method
                in <code style={{ background: 'var(--code-bg)', padding: '1px 5px', borderRadius: 4, fontSize: 12, fontFamily: "'JetBrains Mono', monospace" }}>discount.py</code> applies
                discounts in the wrong order, causing customers to be <strong>undercharged</strong>.
              </p>

              <h3 style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.07em', margin: '16px 0 8px' }}>Example</h3>
              <div style={{ background: 'var(--code-bg)', borderRadius: 6, padding: '10px 12px', fontSize: 12, fontFamily: "'JetBrains Mono', monospace", lineHeight: 1.7, color: '#c9d1d9', marginBottom: 12 }}>
                <div style={{ color: '#8b949e' }}># 5 shirts @ $25 + coupon SAVE20</div>
                <div>subtotal = $125.00</div>
                <div style={{ color: '#f87171' }}>wrong  → $125×0.80=$100 − $7.50 = <strong>$92.50</strong></div>
                <div style={{ color: '#4ade80' }}>correct→ $125−$7.50=$117.50 × 0.80 = <strong>$94.00</strong></div>
              </div>

              <h3 style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.07em', margin: '16px 0 8px' }}>Your Task</h3>
              <ul style={{ margin: '0 0 12px', paddingLeft: 18 }}>
                <li>Read <code style={{ background: 'var(--code-bg)', padding: '1px 4px', borderRadius: 3, fontSize: 12, fontFamily: "'JetBrains Mono', monospace" }}>discount.py</code>, <code style={{ background: 'var(--code-bg)', padding: '1px 4px', borderRadius: 3, fontSize: 12, fontFamily: "'JetBrains Mono', monospace" }}>cart.py</code>, and <code style={{ background: 'var(--code-bg)', padding: '1px 4px', borderRadius: 3, fontSize: 12, fontFamily: "'JetBrains Mono', monospace" }}>product.py</code></li>
                <li>Identify the ordering bug in <code style={{ background: 'var(--code-bg)', padding: '1px 4px', borderRadius: 3, fontSize: 12, fontFamily: "'JetBrains Mono', monospace" }}>DiscountEngine.apply()</code></li>
                <li>Fix it so all tests in <code style={{ background: 'var(--code-bg)', padding: '1px 4px', borderRadius: 3, fontSize: 12, fontFamily: "'JetBrains Mono', monospace" }}>tests/test_cart.py</code> pass</li>
                <li>Add a comment explaining the correct order</li>
              </ul>

              <h3 style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.07em', margin: '16px 0 8px' }}>Discount Rules</h3>
              <ul style={{ margin: 0, paddingLeft: 18, fontSize: 13 }}>
                <li>Quantity tiers: 3+ units → $0.75/unit, 5+ → $1.50/unit, 10+ → $3.00/unit</li>
                <li>Coupons: SAVE10 (10% off), SAVE20 (20% off), HALFOFF (50% off)</li>
                <li>Quantity discounts apply first; percentage applies to the reduced total</li>
              </ul>

              {error && <p className="error-text" style={{ marginTop: 12 }}>{error}</p>}
            </div>
          </section>

          <div className="resize-handle" onMouseDown={(e) => startDrag('left', e)} />

          <section className="workspace-pane" onClick={() => sendPanelEvent('editor')}>
            <div className="editor-toolbar">
              <span>Editing&nbsp;<strong>{activeFile?.filename ?? 'No file selected'}</strong></span>
              <span className="lang-pill">{activeFile?.language ?? 'python'}</span>
            </div>
            <div className="workspace-top">
              <FileExplorer
                files={files.filter(f => !f.filename.startsWith('tests/'))}
                activeFileId={activeFileId}
                onSelectFile={selectFile}
                onCreateFile={createFile}
              />
              <MonacoEditorWrapper
                fileId={activeFile?.fileId}
                content={activeContent}
                language={activeFile?.language ?? 'python'}
                onChange={(value) => updateActiveContent(value ?? '')}
                pendingSuggestion={pendingSuggestion}
                onResolvePending={() => setPendingSuggestion(null)}
                sessionId={sessionId}
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

          <div className="resize-handle" onMouseDown={(e) => startDrag('right', e)} />

          <section className="assistant-pane" style={{ width: rightWidth, minWidth: rightWidth }} onClick={() => sendPanelEvent('chat')}>
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
      <ToastProvider>
        <NetworkStatus />
        <Router>
          <AppRoutes />
        </Router>
      </ToastProvider>
    </AuthProvider>
  );
}

export default App;
