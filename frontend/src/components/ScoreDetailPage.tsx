import { useEffect, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import api from '../api';
import { Badge } from './ui/badge';
import { Button } from './ui/button';

interface SessionDetail {
    session_id: string;
    username: string;
    overall_label: 'over_reliant' | 'balanced' | 'strategic' | null;
    weighted_score: number | null;
    structural_scores: Record<string, number> | null;
    prompt_quality_scores: Record<string, number> | null;
    review_scores: Record<string, number> | null;
    llm_narrative: string | null;
    chunk_acceptance_rate: number | null;
    verification_frequency: number | null;
    reprompt_ratio: number | null;
    time_by_panel_editor_pct: number | null;
    time_by_panel_chat_pct: number | null;
    orientation_duration_s: number | null;
    iteration_depth: number | null;
}

const LABEL_VARIANT: Record<string, 'default' | 'warning' | 'success' | 'secondary'> = {
    strategic: 'success',
    balanced: 'secondary',
    over_reliant: 'warning',
};

const LABEL_COLOR: Record<string, string> = {
    strategic: '#4ade80',
    balanced: '#60a5fa',
    over_reliant: '#fbbf24',
};

function ScoreBar({ value }: { value: number }) {
    const pct = ((value - 1) / 4) * 100;
    const color = value >= 4 ? '#4ade80' : value >= 3 ? '#60a5fa' : value >= 2 ? '#fbbf24' : '#f87171';
    return (
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <div style={{ flex: 1, height: 5, background: '#2a2a2a', borderRadius: 3, overflow: 'hidden' }}>
                <div style={{ width: `${pct}%`, height: '100%', background: color, borderRadius: 3 }} />
            </div>
            <span style={{ fontSize: 12, fontWeight: 600, minWidth: 28, color, fontFamily: "'JetBrains Mono', monospace" }}>{value.toFixed(1)}</span>
        </div>
    );
}

function RubricBreakdown({ structural, promptQuality, review }: {
    structural: Record<string, number> | null;
    promptQuality: Record<string, number> | null;
    review: Record<string, number> | null;
}) {
    const sections = [
        { label: 'Structural Behavior', scores: structural },
        { label: 'Prompt Quality', scores: promptQuality },
        { label: 'Critical Review', scores: review },
    ];

    return (
        <div className="rubric-sections">
            {sections.map(({ label, scores }) => (
                <div key={label} className="rubric-section">
                    <h4 className="rubric-section-title">{label}</h4>
                    {scores
                        ? Object.entries(scores).map(([key, val]) => (
                            <div key={key} className="rubric-row">
                                <span className="rubric-label">{key.replace(/_/g, ' ')}</span>
                                <ScoreBar value={val} />
                            </div>
                        ))
                        : <p className="muted" style={{ fontSize: 13 }}>Not yet computed.</p>
                    }
                </div>
            ))}
        </div>
    );
}

function NarrativeReport({ sessionId, initial }: { sessionId: string; initial: string | null }) {
    const [narrative, setNarrative] = useState<string | null>(initial);
    const [polling, setPolling] = useState(!initial);
    const retriesRef = useRef(0);
    const MAX_RETRIES = 3;

    useEffect(() => {
        if (!polling) return;

        const timer = setInterval(async () => {
            try {
                const res = await api.get(`/analytics/session/${sessionId}`);
                const text = (res.data as { llm_narrative: string | null }).llm_narrative;
                if (text) {
                    setNarrative(text);
                    setPolling(false);
                    clearInterval(timer);
                }
            } catch {
                // keep polling
            }
            retriesRef.current += 1;
            if (retriesRef.current >= MAX_RETRIES) {
                setPolling(false);
                clearInterval(timer);
            }
        }, 5000);

        return () => clearInterval(timer);
    }, [polling, sessionId]);

    if (narrative) {
        return (
            <div className="narrative-body">
                <pre className="narrative-text">{narrative}</pre>
            </div>
        );
    }

    if (polling) {
        return (
            <div className="narrative-skeleton">
                <div className="skeleton-line" />
                <div className="skeleton-line" style={{ width: '80%' }} />
                <div className="skeleton-line" style={{ width: '60%' }} />
                <p className="muted" style={{ fontSize: 12, marginTop: 8 }}>Generating report...</p>
            </div>
        );
    }

    return <p className="muted" style={{ fontSize: 13 }}>Report unavailable — try refreshing.</p>;
}

export default function ScoreDetailPage() {
    const { candidateId } = useParams<{ candidateId: string }>();
    const navigate = useNavigate();
    const [data, setData] = useState<SessionDetail | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        if (!candidateId) return;
        api.get(`/analytics/session/${candidateId}`)
            .then((res) => setData(res.data as SessionDetail))
            .catch(() => setError('Could not load session data.'))
            .finally(() => setLoading(false));
    }, [candidateId]);

    if (loading) return <div className="screen"><p className="muted">Loading...</p></div>;
    if (error || !data) return (
        <div className="screen">
            <p className="muted">{error ?? 'Session not found.'}</p>
            <Button variant="outline" onClick={() => navigate('/admin')}>Back</Button>
        </div>
    );

    return (
        <div className="screen score-detail-screen">
            <header className="dashboard-topbar">
                <div>
                    <p className="eyebrow">Candidate Report</p>
                    <h1>{data.username}</h1>
                </div>
                <Button variant="outline" onClick={() => navigate('/admin')}>← Back</Button>
            </header>

            <div className="score-detail-grid">
                <div className="score-summary-card">
                    <h3>Overall Assessment</h3>
                    {data.overall_label
                        ? (
                            <>
                                <Badge variant={LABEL_VARIANT[data.overall_label] ?? 'secondary'} style={{ fontSize: 14, padding: '6px 14px' }}>
                                    {data.overall_label.replace('_', ' ')}
                                </Badge>
                                <p style={{ fontSize: 36, fontWeight: 700, margin: '12px 0 4px', color: LABEL_COLOR[data.overall_label], fontFamily: "'JetBrains Mono', monospace" }}>
                                    {data.weighted_score?.toFixed(2) ?? '—'}<span style={{ fontSize: 16, fontWeight: 400, color: 'var(--text-faint)' }}> / 5.0</span>
                                </p>
                            </>
                        )
                        : <p className="muted">Scoring in progress...</p>
                    }

                    <div className="metrics-grid">
                        {[
                            ['Acceptance Rate', data.chunk_acceptance_rate, '%', 100],
                            ['Verification Frequency', data.verification_frequency, 'x', null],
                            ['Reprompt Ratio', data.reprompt_ratio, '', null],
                            ['Time in Editor', data.time_by_panel_editor_pct, '%', 100],
                            ['Time in Chat', data.time_by_panel_chat_pct, '%', 100],
                            ['Orientation Time', data.orientation_duration_s, 's', null],
                            ['Iteration Depth', data.iteration_depth, '', null],
                        ].map(([label, val]) => (
                            <div key={String(label)} className="metric-item">
                                <span className="metric-label">{label}</span>
                                <span className="metric-value">{val != null ? String(typeof val === 'number' ? val.toFixed(1) : val) : '—'}</span>
                            </div>
                        ))}
                    </div>
                </div>

                <div className="score-rubric-card">
                    <h3>Rubric Breakdown</h3>
                    <RubricBreakdown
                        structural={data.structural_scores}
                        promptQuality={data.prompt_quality_scores}
                        review={data.review_scores}
                    />
                </div>

                <div className="score-narrative-card">
                    <h3>AI Narrative</h3>
                    <NarrativeReport sessionId={data.session_id} initial={data.llm_narrative} />
                </div>
            </div>
        </div>
    );
}
