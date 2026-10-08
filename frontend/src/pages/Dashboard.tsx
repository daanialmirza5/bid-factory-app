import { useEffect, useState } from 'react';
import { API, Bid } from '../api';
import { Link } from 'react-router-dom';

const Dashboard = () => {
    const [bids, setBids] = useState<Bid[]>([]);
    const [reviewsCount, setReviewsCount] = useState(0);

    useEffect(() => {
        API.getBids().then(setBids).catch(console.error);
        API.getAllReviews().then(r => setReviewsCount(r.total_pending)).catch(console.error);
    }, []);

    const totalBids = bids.length;
    const processing = bids.filter(b => b.processing_status === 'processing').length;

    return (
        <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '2rem 0' }}>
            <div style={{ marginBottom: '3rem', borderBottom: '1px solid #eaeaea', paddingBottom: '1.5rem' }}>
                <h1 style={{ fontSize: '2rem', fontWeight: 600, color: '#111827', margin: '0 0 0.5rem 0' }}>
                    Bid-Factory: AI-Powered RFP Compliance
                </h1>
                <p style={{ color: '#6b7280', fontSize: '1rem', margin: 0 }}>
                    Automate requirement extraction, verify compliance securely against your company knowledge base using Hybrid RAG, and generate AI-driven responses.
                </p>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1.5rem', marginBottom: '3rem' }}>
                <div style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: '12px', padding: '1.5rem', boxShadow: '0 1px 2px rgba(0,0,0,0.05)' }}>
                    <div style={{ fontSize: '0.875rem', fontWeight: 500, color: '#6b7280', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Active Pipelines</div>
                    <div style={{ fontSize: '2.5rem', fontWeight: 600, color: '#111827', marginTop: '0.5rem' }}>{totalBids}</div>
                </div>
                <div style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: '12px', padding: '1.5rem', boxShadow: '0 1px 2px rgba(0,0,0,0.05)' }}>
                    <div style={{ fontSize: '0.875rem', fontWeight: 500, color: '#6b7280', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Processing</div>
                    <div style={{ fontSize: '2.5rem', fontWeight: 600, color: '#3b82f6', marginTop: '0.5rem' }}>{processing}</div>
                </div>
                <div style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: '12px', padding: '1.5rem', boxShadow: '0 1px 2px rgba(0,0,0,0.05)' }}>
                    <div style={{ fontSize: '0.875rem', fontWeight: 500, color: '#6b7280', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Pending Approvals</div>
                    <div style={{ fontSize: '2.5rem', fontWeight: 600, color: '#f59e0b', marginTop: '0.5rem' }}>{reviewsCount}</div>
                </div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
                <h2 style={{ fontSize: '1.25rem', fontWeight: 600, color: '#111827', margin: 0 }}>Recent Analysis Tasks</h2>
                <Link to="/new-rfp" style={{ background: '#111827', color: '#fff', padding: '0.6rem 1.2rem', borderRadius: '6px', fontWeight: 500, textDecoration: 'none', fontSize: '0.9rem' }}>
                    + New Pipeline
                </Link>
            </div>

            <div style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: '12px', overflow: 'hidden', boxShadow: '0 1px 3px rgba(0,0,0,0.03)' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
                    <thead style={{ background: '#f9fafb', borderBottom: '1px solid #e5e7eb' }}>
                        <tr>
                            <th style={{ padding: '1rem', fontSize: '0.75rem', fontWeight: 600, color: '#6b7280', textTransform: 'uppercase' }}>Document Target</th>
                            <th style={{ padding: '1rem', fontSize: '0.75rem', fontWeight: 600, color: '#6b7280', textTransform: 'uppercase' }}>Status</th>
                            <th style={{ padding: '1rem', fontSize: '0.75rem', fontWeight: 600, color: '#6b7280', textTransform: 'uppercase' }}>Date</th>
                            <th style={{ padding: '1rem', fontSize: '0.75rem', fontWeight: 600, color: '#6b7280', textTransform: 'uppercase', textAlign: 'right' }}>Action</th>
                        </tr>
                    </thead>
                    <tbody>
                        {bids.length === 0 ? (
                            <tr>
                                <td colSpan={4} style={{ padding: '3rem 1rem', textAlign: 'center', color: '#6b7280' }}>
                                    <div style={{ marginBottom: '1rem' }}>No workloads have been processed yet.</div>
                                    <Link to="/new-rfp" style={{ color: '#3b82f6', textDecoration: 'underline' }}>Start your first analysis</Link>
                                </td>
                            </tr>
                        ) : (
                            bids.map((bid, i) => (
                                <tr key={bid.bid_id} style={{ borderBottom: i === bids.length - 1 ? 'none' : '1px solid #f3f4f6' }}>
                                    <td style={{ padding: '1rem' }}>
                                        <div style={{ fontWeight: 500, color: '#111827' }}>{bid.rfp.title}</div>
                                        <div style={{ fontSize: '0.8rem', color: '#6b7280', marginTop: '0.2rem' }}>{bid.rfp.filename}</div>
                                    </td>
                                    <td style={{ padding: '1rem' }}>
                                        <span style={{
                                            padding: '0.25rem 0.75rem',
                                            borderRadius: '9999px',
                                            fontSize: '0.75rem',
                                            fontWeight: 500,
                                            background: bid.processing_status === 'completed' ? '#dcfce7' : bid.processing_status === 'failed' ? '#fee2e2' : '#dbeafe',
                                            color: bid.processing_status === 'completed' ? '#166534' : bid.processing_status === 'failed' ? '#991b1b' : '#1e40af'
                                        }}>
                                            {bid.processing_status.toUpperCase()}
                                        </span>
                                    </td>
                                    <td style={{ padding: '1rem', fontSize: '0.875rem', color: '#4b5563' }}>
                                        {new Date(bid.rfp.uploaded_at).toLocaleDateString()}
                                    </td>
                                    <td style={{ padding: '1rem', textAlign: 'right' }}>
                                        <Link to={`/bids/${bid.bid_id}`} style={{ color: '#3b82f6', fontWeight: 500, fontSize: '0.875rem', textDecoration: 'none' }}>
                                            View Report →
                                        </Link>
                                    </td>
                                </tr>
                            ))
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    );
};

export default Dashboard;
