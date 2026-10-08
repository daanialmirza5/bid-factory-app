import React, { useState } from 'react';
import { auth } from '../firebase';
import { createUserWithEmailAndPassword, signInWithEmailAndPassword } from 'firebase/auth';
import { useNavigate } from 'react-router-dom';

const Login = () => {
    const [isLogin, setIsLogin] = useState(true);
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [errorMsg, setErrorMsg] = useState('');
    const navigate = useNavigate();

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setErrorMsg('');
        try {
            if (isLogin) {
                await signInWithEmailAndPassword(auth, email, password);
            } else {
                await createUserWithEmailAndPassword(auth, email, password);
            }
            // Navigate strictly to the protected area
            navigate('/bids');
        } catch (error: unknown) {
            setErrorMsg(error instanceof Error ? error.message : 'Authentication failed');
        }
    };

    return (
        <div style={{ display: 'flex', height: '100vh', justifyContent: 'center', alignItems: 'center', background: 'var(--bg-color)' }}>
            <div className="card" style={{ width: '400px', padding: '2rem' }}>
                <h2 style={{ textAlign: 'center', marginBottom: '1.5rem', color: 'var(--primary-color)' }}>
                    BidFactory Auth
                </h2>

                {errorMsg && (
                    <div style={{ background: '#fef2f2', color: '#991b1b', padding: '0.75rem', borderRadius: '6px', marginBottom: '1rem', fontSize: '14px', border: '1px solid #f87171' }}>
                        {errorMsg}
                    </div>
                )}

                <div style={{ display: 'flex', gap: '1rem', marginBottom: '1.5rem' }}>
                    <button
                        style={{ flex: 1, padding: '0.5rem', borderBottom: isLogin ? '2px solid var(--primary-color)' : '2px solid transparent', background: 'none', border: 'none', cursor: 'pointer', fontWeight: 600, color: isLogin ? 'var(--primary-color)' : 'gray' }}
                        onClick={() => setIsLogin(true)}
                    >
                        Login
                    </button>
                    <button
                        style={{ flex: 1, padding: '0.5rem', borderBottom: !isLogin ? '2px solid var(--primary-color)' : '2px solid transparent', background: 'none', border: 'none', cursor: 'pointer', fontWeight: 600, color: !isLogin ? 'var(--primary-color)' : 'gray' }}
                        onClick={() => setIsLogin(false)}
                    >
                        Sign Up
                    </button>
                </div>

                <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                    <div>
                        <label style={{ display: 'block', fontSize: '0.875rem', marginBottom: '0.25rem' }}>Enterprise Email</label>
                        <input
                            type="email"
                            required
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            style={{ width: '100%', padding: '0.75rem', borderRadius: '6px', border: '1px solid #d1d5db', outline: 'none' }}
                            placeholder="user@enterprise.com"
                        />
                    </div>
                    <div>
                        <label style={{ display: 'block', fontSize: '0.875rem', marginBottom: '0.25rem' }}>Password (Min 6 Chars)</label>
                        <input
                            type="password"
                            required
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            style={{ width: '100%', padding: '0.75rem', borderRadius: '6px', border: '1px solid #d1d5db', outline: 'none' }}
                            placeholder="••••••••"
                        />
                    </div>
                    <button type="submit" className="btn btn-primary" style={{ width: '100%', marginTop: '1rem', padding: '0.75rem' }}>
                        {isLogin ? 'Sign In to Workspace' : 'Create Enterprise Account'}
                    </button>
                </form>
                <div style={{ textAlign: 'center', marginTop: '1rem', fontSize: '0.75rem', color: 'gray' }}>
                    Secured by Firebase Enterprise Authentication
                </div>
            </div>
        </div>
    );
};

export default Login;
