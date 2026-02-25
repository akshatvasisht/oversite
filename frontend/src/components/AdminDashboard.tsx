import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api';
import { useAuth } from '../hooks/useAuth';
import { Button } from './ui/button';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Badge } from './ui/badge';

interface SessionRow {
    session_id: string;
    username: string;
    label: 'over_reliant' | 'balanced' | 'strategic' | null;
    score: number | null;
    date_submitted: string | null;
    status: 'Submitted' | 'In Progress';
}

const LABEL_VARIANT: Record<string, 'default' | 'warning' | 'success' | 'secondary'> = {
    strategic: 'success',
    balanced: 'secondary',
    over_reliant: 'warning',
};

function fmt(iso: string | null): string {
    if (!iso) return '—';
    return new Date(iso).toLocaleString([], { dateStyle: 'short', timeStyle: 'short' });
}

/**
 * Administrative overview of all candidate assessment sessions.
 * 
 * Provides a high-level summary of session status, evaluation labels, 
 * and weighted performance scores.
 */
export default function AdminDashboard() {
    const { logout } = useAuth();
    const navigate = useNavigate();
    const [sessions, setSessions] = useState<SessionRow[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        api.get('/analytics/overview')
            .then((res) => {
                setSessions((res.data as { sessions: SessionRow[] }).sessions ?? []);
            })
            .catch(() => {
                setError('Analytics service is currently unreachable. Please ensure the backend is running.');
            })
            .finally(() => setLoading(false));
    }, []);

    return (
        <div className="screen admin-screen">
            <header className="dashboard-topbar">
                <div>
                    <p className="eyebrow">OverSite</p>
                    <h1>Admin Dashboard</h1>
                </div>
                <Button variant="outline" onClick={logout}>Logout</Button>
            </header>

            {loading && (
                <div className="flex items-center justify-center p-12">
                    <p className="muted animate-pulse">Loading candidate sessions...</p>
                </div>
            )}

            {error && (
                <Card className="border-red-200 bg-red-50/50 mt-8">
                    <CardHeader>
                        <CardTitle className="text-red-700">Connection Error</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <p className="text-red-600">{error}</p>
                    </CardContent>
                </Card>
            )}

            {!loading && sessions.length === 0 && !error && (
                <Card className="mt-8 border-dashed">
                    <CardHeader>
                        <CardTitle className="text-center text-muted-foreground">No Sessions Yet</CardTitle>
                    </CardHeader>
                    <CardContent className="text-center">
                        <p className="muted max-w-md mx-auto">
                            Candidates will appear here once they start their assessments.
                            Share your assessment links to start collecting data.
                        </p>
                    </CardContent>
                </Card>
            )}

            {sessions.length > 0 && (
                <div className="admin-table-wrap">
                    <table className="admin-table">
                        <thead>
                            <tr>
                                <th>Candidate</th>
                                <th>Status</th>
                                <th>Label</th>
                                <th>Score</th>
                                <th>Submitted</th>
                                <th></th>
                            </tr>
                        </thead>
                        <tbody>
                            {sessions.map((row) => (
                                <tr key={row.session_id} className={row.status === 'Submitted' ? 'row-clickable' : 'row-muted'}>
                                    <td>{row.username}</td>
                                    <td>
                                        <Badge variant={row.status === 'Submitted' ? 'secondary' : 'outline'}>
                                            {row.status}
                                        </Badge>
                                    </td>
                                    <td>
                                        {row.label
                                            ? <Badge variant={LABEL_VARIANT[row.label] ?? 'secondary'}>{row.label.replace('_', ' ')}</Badge>
                                            : <span className="muted">—</span>
                                        }
                                    </td>
                                    <td>
                                        {row.score != null
                                            ? <strong>{row.score.toFixed(1)}</strong>
                                            : <span className="muted">—</span>
                                        }
                                    </td>
                                    <td className="muted">{fmt(row.date_submitted)}</td>
                                    <td>
                                        {row.status === 'Submitted' && (
                                            <Button
                                                size="sm"
                                                variant="outline"
                                                onClick={() => navigate(`/admin/${row.session_id}`)}
                                            >
                                                View Report
                                            </Button>
                                        )}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    );
}
