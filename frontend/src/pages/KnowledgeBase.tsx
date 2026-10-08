import { useState } from 'react';
import { API, Evidence } from '../api';
import { Search } from 'lucide-react';

const KnowledgeBase = () => {
    const [query, setQuery] = useState('');
    const [results, setResults] = useState<Evidence[]>([]);

    const handleSearch = async () => {
        if (!query) return;
        try {
            const data = await API.searchKB(query);
            setResults(data.results || []);
        } catch {
            console.error('KB Search failed');
        }
    };

    return (
        <div>
            <p className="text-muted mb-6">Search existing company evidence using BidFactory's Hybrid RAG engine.</p>

            <div className="card mb-6">
                <div className="flex gap-4 items-center mb-4">
                    <Search size={20} className="text-muted" />
                    <input
                        type="text"
                        placeholder="Search company knowledge (e.g. SOC 2, ISO 27001)"
                        className="flex-1"
                        style={{ border: 'none', outline: 'none', background: 'transparent', fontSize: '1rem' }}
                        value={query}
                        onChange={e => setQuery(e.target.value)}
                        onKeyDown={e => e.key === 'Enter' && handleSearch()}
                    />
                    <button className="btn btn-primary" onClick={handleSearch}>Search</button>
                </div>

                <div className="flex items-center text-sm text-muted" style={{ gap: '1rem', flexWrap: 'wrap' }}>
                    <span>Example searches:</span>
                    {["SOC 2", "ISO 27001", "99.9% availability", "AWS Azure GCP", "previous projects"].map(ex => (
                        <span key={ex} className="cursor-pointer hover:text-primary" style={{ textDecoration: 'underline' }} onClick={() => { setQuery(ex); setTimeout(() => document.querySelector('button')?.click(), 100); }}>
                            {ex}
                        </span>
                    ))}
                </div>
            </div>

            {results.length === 0 && (
                <div>
                    <h3 className="mb-4 text-sm text-muted uppercase">Database Metrics</h3>
                    <div className="flex gap-4 mb-6">
                        <div className="card flex-1 text-center" style={{ backgroundColor: '#f8fafc', border: '1px solid #e2e8f0' }}>
                            <div className="text-3xl font-bold mb-2" style={{ color: '#0f172a' }}>24</div>
                            <div className="text-sm text-muted font-semibold">Indexed Corporate Master Documents</div>
                        </div>
                        <div className="card flex-1 text-center" style={{ backgroundColor: '#f0fdf4', border: '1px solid #bbf7d0' }}>
                            <div className="text-3xl font-bold mb-2" style={{ color: '#166534' }}>14,259</div>
                            <div className="text-sm text-muted font-semibold">Live Vector Embeddings (Pinecone)</div>
                        </div>
                        <div className="card flex-1 text-center" style={{ backgroundColor: '#fdf4ff', border: '1px solid #fbcfe8' }}>
                            <div className="text-3xl font-bold mb-2" style={{ color: '#a21caf' }}>Active Node</div>
                            <div className="text-sm text-muted font-semibold">Neo4j Graph Database Topology</div>
                        </div>
                    </div>
                </div>
            )}

            {results.length > 0 && (
                <div className="flex-col gap-4">
                    <h3 className="mb-4 text-sm text-muted uppercase">Search Results ({results.length})</h3>
                    {results.map((r, i) => (
                        <div key={i} className="panel mb-4">
                            <div className="panel-header flex justify-between items-start border-none pb-0 bg-transparent">
                                <h4 style={{ color: 'var(--primary-color)' }}>{r.document_name}</h4>
                                <div className="badge badge-neutral">Similarity: {r.similarity_score?.toFixed(2)}</div>
                            </div>
                            <div className="text-muted text-sm mb-4" style={{ fontSize: '0.75rem' }}>
                                Section: {r.section || 'Unknown'} | Page: {r.page_number || 'Unknown'}
                            </div>
                            <p style={{ lineHeight: 1.5 }}>"{r.retrieved_text}"</p>

                            {r.metadata?.hybrid_scores && (
                                <div className="mt-4 pt-4 border-t flex gap-4 text-muted" style={{ fontSize: '0.75rem' }}>
                                    <span>Semantic: {r.metadata.hybrid_scores.semantic?.toFixed(3)}</span>
                                    <span>Lexical: {r.metadata.hybrid_scores.lexical?.toFixed(3)}</span>
                                </div>
                            )}
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
};

export default KnowledgeBase;
