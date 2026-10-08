import { useEffect, useState } from 'react';
import { API, Bid } from '../api';
import { Link } from 'react-router-dom';

const Bids = () => {
    const [bids, setBids] = useState<Bid[]>([]);

    useEffect(() => {
        API.getBids().then(setBids).catch(console.error);
    }, []);

    return (
        <div>
            <div className="flex justify-between items-center mb-6">
                <p className="text-muted">Manage all RFPs and generated bids.</p>
                <Link to="/new-rfp" className="btn btn-primary">Upload RFP</Link>
            </div>

            <div className="table-container">
                <table>
                    <thead>
                        <tr>
                            <th>Bid / RFP</th>
                            <th>Status</th>
                            <th>Date</th>
                            <th>Action</th>
                        </tr>
                    </thead>
                    <tbody>
                        {bids.map(bid => (
                            <tr key={bid.bid_id}>
                                <td>
                                    <div style={{ fontWeight: 600 }}>{bid.rfp.title}</div>
                                    <div className="text-muted" style={{ fontSize: '0.75rem' }}>{bid.rfp.filename} ({Math.round(bid.rfp.file_size / 1024)} KB)</div>
                                </td>
                                <td>
                                    <span className={`badge badge-${bid.processing_status === 'completed' ? 'success' : bid.processing_status === 'failed' ? 'error' : 'info'}`}>
                                        {bid.processing_status}
                                    </span>
                                </td>
                                <td>{new Date(bid.rfp.uploaded_at).toLocaleString()}</td>
                                <td>
                                    <Link to={`/bids/${bid.bid_id}`} className="text-primary font-medium">View Analysis →</Link>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
};

export default Bids;
