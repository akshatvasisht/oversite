import { useState, type ReactElement } from 'react';
import { BrowserRouter as Router, Navigate, Route, Routes, useNavigate, useParams } from 'react-router-dom';
import { AuthProvider } from './AuthContext';
import FileExplorer from './components/FileExplorer';
import MonacoEditorWrapper from './components/MonacoEditorWrapper';
import { Badge } from './components/ui/badge';
import { Button } from './components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './components/ui/card';
import { Input } from './components/ui/input';
import { Textarea } from './components/ui/textarea';
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
    <div className="screen login-screen">
      <Card className="login-card">
        <CardHeader>
          <p className="eyebrow">MadData Assessment</p>
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
            <label htmlFor="username">Username</label>
            <Input
              id="username"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              placeholder="testuser1 or admin"
            />
            <Button type="submit">Sign In</Button>
          </form>
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
    { id: 'q1', company: 'COMPANY', title: 'QUESTION TITLE', duration: '60 min', status: 'pending' },
    { id: 'q2', company: 'COMPANY', title: 'QUESTION TITLE', duration: '60 min', status: 'submitted' },
    { id: 'q3', company: 'COMPANY', title: 'QUESTION TITLE', duration: '60 min', status: 'in progress' },
  ];

  const statusVariant = (status: string): 'outline' | 'secondary' | 'warning' => {
    if (status === 'submitted') return 'secondary';
    if (status === 'in progress') return 'warning';
    return 'outline';
  };

  return (
    <div className="screen dashboard-screen">
      <header className="topbar">
        <h1>Your Assessments</h1>
        <Button type="button" variant="outline" onClick={logout}>Logout</Button>
      </header>
      <p className="muted">Select an assignment to open the coding workspace.</p>
      <div className="question-grid">
        {questions.map((question) => (
          <Card key={question.id} className={`question-card ${question.status === 'submitted' ? 'done' : ''}`}>
            <CardHeader className="question-header">
              <p className="eyebrow">{question.company}</p>
              <Badge variant={statusVariant(question.status)}>{question.status}</Badge>
            </CardHeader>
            <CardContent className="question-content">
              <h2>{question.title}</h2>
              <p className="muted">{question.duration}</p>
              <Button
                disabled={question.status === 'submitted'}
                onClick={() => navigate(`/session/${question.id}`)}
              >
                {question.status === 'submitted' ? 'Completed' : 'Open Workspace'}
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
};

const AdminDashboard = () => {
  const { role, logout } = useAuth();
  if (role !== 'admin') return <Navigate to="/login" replace />;
  return (
    <div className="screen admin-screen">
      <Card className="admin-card">
        <CardHeader>
          <CardTitle>Admin Dashboard</CardTitle>
          <CardDescription>Review candidate sessions and scoring workflows.</CardDescription>
        </CardHeader>
        <CardContent>
          <Button variant="outline" onClick={logout}>Logout</Button>
        </CardContent>
      </Card>
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

  const runCode = (): void => {
    const name = activeFile?.filename ?? 'main.py';
    const output = ['> python ' + name, 'Execution finished.'];
    setTerminalLines((current) => [...current, ...output]);
  };

  const submit = (): void => {
    navigate('/questions');
  };

  if (loading) {
    return (
      <div className="screen loading-screen">
        <Card>
          <CardContent>
            <p>Starting session...</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="ide-shell">
      <section className="problem-pane">
        <div className="pane-title">Problem</div>
        <div className="pane-body">
          <h2>Session {id}</h2>
          <p>Build a clean and testable solution. Use multiple files if needed.</p>
          <ul>
            <li>Keep logic modular.</li>
            <li>Include edge-case handling.</li>
            <li>Explain assumptions in comments.</li>
          </ul>
          <p className="muted">Session ID: {sessionId}</p>
          {error && <p className="error-text">{error}</p>}
        </div>
      </section>
      <section className="workspace-pane">
        <div className="editor-toolbar">
          <div>
            Editing <strong>{activeFile?.filename ?? 'No file selected'}</strong>
          </div>
          <Badge variant="secondary" className="status-pill">
            Autosave: {autosaveStatus === 'saving' ? 'Saving...' : autosaveStatus === 'saved' ? 'Saved' : autosaveStatus === 'error' ? 'Save failed' : 'Idle'}
          </Badge>
          <Button variant="outline" size="sm" onClick={runCode}>Run Code</Button>
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
      <section className="assistant-pane">
        <div className="pane-title">AI Assistant</div>
        <div className="pane-body">
          <p className="assistant-msg">Ask for implementation hints, debugging help, or test-case ideas.</p>
          <Textarea rows={8} placeholder="Ask AI for help..." />
          <Button type="button">Send Prompt</Button>
          <div className="submit-box">
            <p className="muted">Final Submission</p>
            <Button type="button" onClick={submit}>Submit Solution</Button>
          </div>
        </div>
      </section>
    </div>
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
      <Route path="/admin" element={<ProtectedRoute allowedRole="admin"><AdminDashboard /></ProtectedRoute>} />
      <Route path="/admin/:candidateId" element={<ProtectedRoute allowedRole="admin"><div>Candidate Evaluation Detail</div></ProtectedRoute>} />
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
