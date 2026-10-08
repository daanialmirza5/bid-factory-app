import React, { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { UploadCloud, CheckCircle, XCircle, FileText } from 'lucide-react';
import { API } from '../api';

const NewRfp = () => {
    const [files, setFiles] = useState<File[]>([]);
    const [isUploading, setIsUploading] = useState(false);
    const [pipelineState, setPipelineState] = useState<'idle' | 'processing' | 'completed' | 'failed' | null>(null);
    const [uploadError, setUploadError] = useState('');
    const [bidId, setBidId] = useState<string | null>(null);
    const [previewUrl, setPreviewUrl] = useState<string | null>(null);

    const fileInputRef = useRef<HTMLInputElement>(null);
    const navigate = useNavigate();

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files.length > 0) {
            const selectedFiles = Array.from(e.target.files);
            setFiles(selectedFiles);
            setUploadError('');

            // Generate preview for the first image if present
            const firstImage = selectedFiles.find(f => f.type.startsWith('image/'));
            if (firstImage) {
                const reader = new FileReader();
                reader.onload = (e) => setPreviewUrl(e.target?.result as string);
                reader.readAsDataURL(firstImage);
            } else {
                setPreviewUrl(null);
            }
        }
    };

    const handleUpload = async () => {
        if (files.length === 0 || isUploading) return;
        setIsUploading(true);
        setUploadError('');
        try {
            // Upload the selected RFP
            const res = await API.uploadBid(files[0]);
            setBidId(res.bid_id);

            // Start processing pipeline
            setPipelineState('processing');
            try {
                const analysis = await API.analyzeBid(res.bid_id);

                if (analysis.processing_status === 'failed' || analysis.errors?.length) {
                    setUploadError(analysis.errors?.[0] ?? 'The analysis could not be completed.');
                    setPipelineState('failed');
                } else {
                    setPipelineState('completed');
                    setTimeout(() => {
                        navigate(`/bids/${res.bid_id}`);
                    }, 1500);
                }
            } catch (err: unknown) {
                setUploadError(err instanceof Error ? err.message : 'Pipeline Error');
                setPipelineState('failed');
            }
        } catch (err: unknown) {
            setUploadError(err instanceof Error ? err.message : 'Upload failed');
            setIsUploading(false);
        }
    };

    return (
        <div style={{ maxWidth: 800, margin: '0 auto' }}>
            {!isUploading && pipelineState === null ? (
                <div className="card">
                    <h2 className="mb-2">Upload RFP</h2>
                    <p className="text-muted mb-6">Drop your RFP document here to begin the BidFactory intelligence pipeline.</p>

                    <div
                        className="upload-zone"
                        onClick={() => fileInputRef.current?.click()}
                    >
                        <UploadCloud size={48} className="text-primary mb-4" style={{ margin: '0 auto' }} />
                        <h3>Click to browse or drag file here</h3>
                        <p className="text-muted mt-2">Supports .pdf and .docx (max 25 MB)</p>
                        <input
                            type="file"
                            ref={fileInputRef}
                            style={{ display: 'none' }}
                            accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                            onChange={handleFileChange}
                        />
                    </div>

                    {files.length > 0 && (
                        <div className="mt-6 p-4 border rounded-md" style={{ backgroundColor: 'var(--surface-color)' }}>
                            <div className="flex justify-between items-center bg-gray-50 p-4 rounded-md border mb-4" style={{ backgroundColor: 'var(--bg-color)' }}>
                                <div>
                                    <div style={{ fontWeight: 600 }}>Selected RFP</div>
                                    <div className="text-muted" style={{ fontSize: '0.75rem' }}>{files[0].name}</div>
                                </div>
                                <button className="btn btn-primary" onClick={handleUpload}>Analyze RFP</button>
                            </div>

                            {previewUrl ? (
                                <div className="mt-4 border rounded-md overflow-hidden bg-gray-50 flex justify-center items-center p-4">
                                    <img src={previewUrl} alt="Document Preview" style={{ maxHeight: '300px', maxWidth: '100%', objectFit: 'contain' }} />
                                </div>
                            ) : (
                                <div className="mt-4 border rounded-md bg-gray-50 flex flex-col justify-center items-center p-8 text-muted">
                                    <FileText size={48} className="mb-2 opacity-50" />
                                    <p>Text Document Uploaded</p>
                                </div>
                            )}
                        </div>
                    )}
                    {uploadError && <div className="text-error mt-4" style={{ color: 'var(--status-error)' }}>{uploadError}</div>}
                </div>
            ) : (
                <div className="card">
                    <h2>Analyzing RFP...</h2>
                    <p className="text-muted mb-6">BidFactory is orchestrating the intelligence pipeline.</p>

                    <div className="pipeline-container">
                        <div className={`pipeline-stage completed`}>
                            <div className="stage-icon"><CheckCircle size={24} /></div>
                            <div className="stage-content">
                                <div className="stage-title">RFP Upload</div>
                                <div className="stage-desc">Document binary securely ingested</div>
                            </div>
                        </div>

                        <div className={`pipeline-stage ${pipelineState === 'completed' ? 'completed' : pipelineState === 'processing' ? 'processing' : 'waiting'}`}>
                            <div className="stage-icon">{pipelineState === 'completed' ? <CheckCircle size={24} /> : <div className={pipelineState === 'processing' ? 'spinner' : ''} />}</div>
                            <div className="stage-content">
                                <div className="stage-title">Document Parser</div>
                                <div className="stage-desc">RocketRide cloud node extracting document structure</div>
                            </div>
                        </div>

                        <div className={`pipeline-stage ${pipelineState === 'completed' ? 'completed' : pipelineState === 'failed' ? 'failed' : 'waiting'}`}>
                            <div className="stage-icon">{pipelineState === 'completed' ? <CheckCircle size={24} /> : pipelineState === 'failed' ? <XCircle size={24} /> : null}</div>
                            <div className="stage-content">
                                <div className="stage-title">AI Requirement Extraction</div>
                                <div className="stage-desc">Groq via RocketRide</div>
                                {pipelineState === 'failed' && (
                                    <div style={{ color: 'var(--status-error)', fontSize: '0.875rem', marginTop: '0.25rem', fontWeight: 600 }}>{uploadError || 'Requirement extraction failed.'}</div>
                                )}
                            </div>
                        </div>

                        {/* Stages blocked if failed */}
                        <div className={`pipeline-stage ${pipelineState === 'completed' ? 'completed' : 'waiting'} ${pipelineState === 'failed' ? 'opacity-50' : ''}`}>
                            <div className="stage-icon">{pipelineState === 'completed' && <CheckCircle size={24} />}</div>
                            <div className="stage-content">
                                <div className="stage-title">Hybrid RAG</div>
                                <div className="stage-desc">Vector + lexical search for evidence</div>
                            </div>
                        </div>

                        <div className={`pipeline-stage ${pipelineState === 'completed' ? 'completed' : 'waiting'} ${pipelineState === 'failed' ? 'opacity-50' : ''}`}>
                            <div className="stage-icon">{pipelineState === 'completed' && <CheckCircle size={24} />}</div>
                            <div className="stage-content">
                                <div className="stage-title">Compliance & Responses</div>
                                <div className="stage-desc">Evaluated statuses and drafted AI responses</div>
                            </div>
                        </div>

                    </div>

                    {pipelineState === 'completed' && (
                        <div className="flex justify-between items-center mt-6">
                            <p className="text-success" style={{ color: 'var(--status-success)', fontWeight: 600 }}>Analysis completed successfully!</p>
                            <button className="btn btn-primary" onClick={() => navigate(`/bids/${bidId}`)}>View Dashboard</button>
                        </div>
                    )}
                    {pipelineState === 'failed' && (
                        <div className="panel mt-6" style={{ borderColor: 'var(--status-error)' }}>
                            <div className="panel-body flex-col gap-4">
                                <div className="flex gap-2 items-center text-error" style={{ color: 'var(--status-error)', fontWeight: 600 }}>
                                    <XCircle size={20} /> PIPELINE EXCEPTION
                                </div>
                                <p className="text-muted text-sm my-2">
                                    {uploadError || 'The analysis could not be completed.'}
                                </p>
                                <div className="flex gap-4 mt-2">
                                    <button className="btn btn-outline" onClick={() => { setIsUploading(false); setPipelineState(null); setFiles([]); }}>Upload Another RFP</button>
                                    <button className="btn btn-primary" onClick={() => navigate(`/bids/${bidId}`)}>View Partial Dashboard</button>
                                </div>
                            </div>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
};

export default NewRfp;
