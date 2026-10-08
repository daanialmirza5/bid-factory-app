import { useNavigate } from 'react-router-dom';
import { ArrowRight, Zap, Shield, FileText } from 'lucide-react';

const LandingPage = () => {
    const navigate = useNavigate();

    return (
        <div style={{ backgroundColor: '#0a0a0a', minHeight: '100vh', color: '#ffffff', fontFamily: 'Inter, sans-serif' }}>
            {/* Navbar */}
            <nav style={{ display: 'flex', justifyContent: 'space-between', padding: '1.5rem 3rem', alignItems: 'center', borderBottom: '1px solid rgba(255,255,255,0.1)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                    <img src="/logo.png" alt="BidWise Logo" style={{ width: '32px', height: '32px', borderRadius: '4px' }} />
                    <span style={{ fontSize: '1.5rem', fontWeight: 700, letterSpacing: '-0.5px' }}>BidWise</span>
                </div>
                <div>
                    <button
                        onClick={() => navigate('/login')}
                        style={{ backgroundColor: 'transparent', border: 'none', color: '#fff', cursor: 'pointer', fontWeight: 600, marginRight: '2rem' }}
                    >
                        Sign In
                    </button>
                    <button
                        onClick={() => navigate('/login')}
                        style={{ backgroundColor: '#4f46e5', color: '#fff', padding: '0.6rem 1.2rem', borderRadius: '6px', border: 'none', cursor: 'pointer', fontWeight: 600 }}
                    >
                        Get Started
                    </button>
                </div>
            </nav>

            {/* Hero Section */}
            <main style={{ maxWidth: '1200px', margin: '0 auto', padding: '6rem 2rem', textAlign: 'center', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                <h1 style={{ fontSize: '4rem', fontWeight: 800, lineHeight: 1.1, marginBottom: '1.5rem', letterSpacing: '-1px', color: '#ffffff' }}>
                    Automate Your <span style={{ color: '#818cf8' }}>RFP Responses</span> <br />With Enterprise AI
                </h1>
                <p style={{ fontSize: '1.25rem', color: '#a1a1aa', maxWidth: '600px', marginBottom: '3rem', lineHeight: 1.6 }}>
                    BidWise instantly reads complex client requirements, searches your corporate knowledge base, and drafts compliance-perfect proposals in seconds.
                </p>

                <div style={{ display: 'flex', gap: '1rem' }}>
                    <button
                        onClick={() => navigate('/login')}
                        style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', backgroundColor: '#4f46e5', color: '#fff', padding: '1rem 2rem', borderRadius: '8px', border: 'none', cursor: 'pointer', fontSize: '1.1rem', fontWeight: 600, boxShadow: '0 4px 14px rgba(79, 70, 229, 0.4)' }}
                    >
                        Continue to Enterprise Login <ArrowRight size={20} />
                    </button>
                </div>

                {/* Metrics / Features */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '2rem', marginTop: '6rem', textAlign: 'left', width: '100%', maxWidth: '1000px' }}>
                    <div style={{ padding: '2rem', backgroundColor: 'rgba(255,255,255,0.03)', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.05)' }}>
                        <Zap size={32} color="#818cf8" style={{ marginBottom: '1rem' }} />
                        <h3 style={{ fontSize: '1.2rem', fontWeight: 600, marginBottom: '0.5rem', color: '#ffffff' }}>Instant Extraction</h3>
                        <p style={{ color: '#a1a1aa', lineHeight: 1.5 }}>Automatically extract hundreds of technical requirements from PDFs and Word documents perfectly.</p>
                    </div>
                    <div style={{ padding: '2rem', backgroundColor: 'rgba(255,255,255,0.03)', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.05)' }}>
                        <FileText size={32} color="#818cf8" style={{ marginBottom: '1rem' }} />
                        <h3 style={{ fontSize: '1.2rem', fontWeight: 600, marginBottom: '0.5rem', color: '#ffffff' }}>Graph RAG AI</h3>
                        <p style={{ color: '#a1a1aa', lineHeight: 1.5 }}>We search your precise internal policies using Neo4j Graph topologies and dense vector embeddings.</p>
                    </div>
                    <div style={{ padding: '2rem', backgroundColor: 'rgba(255,255,255,0.03)', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.05)' }}>
                        <Shield size={32} color="#818cf8" style={{ marginBottom: '1rem' }} />
                        <h3 style={{ fontSize: '1.2rem', fontWeight: 600, marginBottom: '0.5rem', color: '#ffffff' }}>Human-in-the-Loop</h3>
                        <p style={{ color: '#a1a1aa', lineHeight: 1.5 }}>Total control. Your experts review and approve every AI-generated response before final export.</p>
                    </div>
                </div>
            </main>
        </div>
    );
};

export default LandingPage;
