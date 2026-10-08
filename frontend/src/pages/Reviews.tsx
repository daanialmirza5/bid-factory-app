import { useEffect, useState } from 'react';
import { API, ReviewItem, Requirement } from '../api';

const Reviews = () => {
    const [reviews, setReviews] = useState<ReviewItem[]>([]);
    const [reqs, setReqs] = useState<Record<string, Requirement>>({});
    const [selectedReview, setSelectedReview] = useState<ReviewItem | null>(null);

    useEffect(() => {
        API.getAllReviews().then(data => {
            setReviews(data.items);

            // Gather unique bid IDs from reviews
            const bidIds = Array.from(new Set(data.items.map(r => r.bid_id)));
            // Fetch requirements for all those bids
            Promise.all(bidIds.map(bidId => API.getRequirements(bidId)))
                .then(reqArrays => {
                    const newReqs: Record<string, Requirement> = {};
                    reqArrays.flat().forEach(r => {
                        newReqs[r.requirement_id] = r;
                    });
                    setReqs(prev => ({ ...prev, ...newReqs }));
                })
                .catch(console.error);

        }).catch(console.error);
    }, []);

    const handleAction = async (action: 'approve' | 'reject' | 'needs-revision') => {
        if (!selectedReview) return;
        try {
            await API.reviewAction(selectedReview.review_id, action);
            const data = await API.getAllReviews();
            setReviews(data.items);
            setSelectedReview(data.items.find(i => i.review_id === selectedReview.review_id) || null);
        } catch (e) {
            console.error(e);
        }
    };

    const pending = reviews.filter(r => r.review_status === 'PENDING' || r.status === 'pending'); // Handling enum capitalization

    return (
        <div>
            <p className="text-muted mb-6">Review proposed responses and compliance evidence.</p>

            <div className="flex gap-6">
                <div style={{ flex: 1 }}>
                    <div className="table-container">
                        <table>
                            <thead>
                                <tr>
                                    <th>Requirement</th>
                                    <th>Status</th>
                                    <th>Compliance</th>
                                </tr>
                            </thead>
                            <tbody>
                                {pending.length === 0 && (
                                    <tr><td colSpan={3} className="text-center py-6 text-muted">No pending reviews.</td></tr>
                                )}
                                {pending.map(r => (
                                    <tr key={r.review_id} onClick={() => setSelectedReview(r)} style={{ cursor: 'pointer', background: selectedReview?.review_id === r.review_id ? 'var(--status-info-bg)' : '' }}>
                                        <td>
                                            <div style={{ fontWeight: 500, marginBottom: '4px' }}>
                                                {reqs[r.requirement_id]?.requirement_text ? (reqs[r.requirement_id]?.requirement_text.substring(0, 50) + '...') : r.requirement_id.substring(0, 8)}
                                            </div>
                                            <div className="text-muted" style={{ fontSize: '0.75rem' }}>{r.requirement_id}</div>
                                        </td>
                                        <td>
                                            <span className="badge badge-warning">{r.review_status || r.status}</span>
                                        </td>
                                        <td>
                                            <span className="badge badge-neutral">{r.compliance_status}</span>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>

                {selectedReview && (
                    <div className="card" style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
                        <div className="flex justify-between items-center mb-6">
                            <h3>Review Details</h3>
                            <span className="badge badge-info">{selectedReview.review_status || selectedReview.status}</span>
                        </div>

                        <div className="mb-4 p-4 border rounded-md" style={{ background: 'var(--bg-color)', position: 'relative' }}>
                            <div className="badge badge-warning" style={{ position: 'absolute', top: '-10px', right: '10px' }}>Requires Review</div>
                            <h4 className="text-primary text-sm mb-2">Original Requirement</h4>
                            <p style={{ fontWeight: 500, fontSize: '1rem', lineHeight: '1.5' }}>
                                {reqs[selectedReview.requirement_id]?.requirement_text || selectedReview.requirement_id}
                            </p>
                            <div className="flex gap-4 mt-4">
                                <div><span className="badge badge-neutral text-xs">Compliance: {selectedReview.compliance_status}</span></div>
                                <div><span className="badge badge-neutral text-xs">Confidence: {(selectedReview.confidence * 100).toFixed(0)}%</span></div>
                            </div>
                        </div>

                        <div className="mb-6">
                            <h4 className="text-muted text-sm mb-2" style={{ fontSize: '0.75rem' }}>Evidence ({selectedReview.supporting_evidence?.length || 0})</h4>
                            <div className="flex-col gap-2">
                                {selectedReview.supporting_evidence?.map((ev, i) => (
                                    <div key={i} className="p-3 bg-gray-50 border rounded-md" style={{ background: 'var(--bg-color)', fontSize: '0.875rem' }}>
                                        <div className="flex justify-between mb-2">
                                            <span style={{ fontWeight: 600 }}>{ev.document_name}</span>
                                            <span className="text-primary">{ev.similarity_score?.toFixed(2)}</span>
                                        </div>
                                        <div className="text-muted mb-2" style={{ fontSize: '0.75rem' }}>Section: {ev.section || 'Unknown'}</div>
                                        <p style={{ fontStyle: 'italic' }}>"{ev.retrieved_text}"</p>
                                    </div>
                                ))}
                            </div>
                        </div>

                        <div className="mb-6">
                            <h4 className="text-muted text-sm mb-2" style={{ fontSize: '0.75rem' }}>AI Proposed Response</h4>
                            <div className="p-4 border rounded-md" style={{ background: 'var(--bg-color)' }}>
                                {selectedReview.proposed_response}
                            </div>
                        </div>

                        <div className="border-t pt-4 flex gap-4">
                            <button className="btn btn-outline" style={{ flex: 1 }} onClick={() => handleAction('reject')}>Reject</button>
                            <button className="btn btn-outline" style={{ flex: 1 }} onClick={() => handleAction('needs-revision')}>Revise</button>
                            <button className="btn btn-primary" style={{ flex: 2 }} onClick={() => handleAction('approve')}>Approve</button>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};

export default Reviews;
