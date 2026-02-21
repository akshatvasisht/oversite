import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { useParams } from 'react-router-dom';
import { AuthProvider, useAuth } from './AuthContext';
import MonacoEditorWrapper from './components/MonacoEditorWrapper';

// --- Placeholders for Pages ---
const LoginPage = () => {
  const { login } = useAuth();
  return (
    <div style={{ padding: '20px' }}>
      <h1>Login</h1>
      <button onClick={() => login('admin', 'admin')}>Login as Admin</button>
      <button onClick={() => login('testuser1', 'candidate')} style={{ marginLeft: '10px' }}>Login as Candidate</button>
    </div>
  );
};

const QuestionsPage = () => {
  const { role, logout } = useAuth();
  if (role !== 'candidate') return <Navigate to="/login" replace />;
  return (
    <div style={{ padding: '20px' }}>
      <h1>Questions (Candidate)</h1>
      <button onClick={logout}>Logout</button>
    </div>
  );
};

const AdminDashboard = () => {
  const { role, logout } = useAuth();
  if (role !== 'admin') return <Navigate to="/login" replace />;
  return (
    <div style={{ padding: '20px' }}>
      <h1>Admin Dashboard</h1>
      <button onClick={logout}>Logout</button>
    </div>
  );
};

const SessionPage = () => {
  const { id } = useParams();
  const starterCode = `def solve():
    nums = [1, 2, 3]
    return sum(nums)

print(solve())
`;

  return (
    <div style={{ padding: '20px' }}>
      <h1>Session {id}</h1>
      <MonacoEditorWrapper content={starterCode} />
    </div>
  );
};

// --- Route Guard ---
const ProtectedRoute = ({ children, allowedRole }: { children: React.ReactElement, allowedRole?: 'admin' | 'candidate' }) => {
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
      <Route path="/admin/:candidateId" element={<ProtectedRoute allowedRole="admin"><div>Admin Detail</div></ProtectedRoute>} />
      <Route path="/session/:id" element={<SessionPage />} />

      {/* Default fallback */}
      <Route path="/" element={<Navigate to="/session/test" replace />} />
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
