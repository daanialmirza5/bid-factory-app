import { apiUrl } from '../config';
// api/index.ts

// These directly reflect backend/schemas and backend/models
export interface Bid {
    id: string;
    bid_id: string;
    rfp: { filename: string; file_size: number; uploaded_at: string; title: string };
    processing_status: 'pending' | 'processing' | 'completed' | 'failed';
}

export interface Requirement {
    requirement_id: string;
    requirement_text: string;
    category?: string;
    priority?: string;
    compliance_type?: string;
    source_section?: string;
    source_page?: number;
}

export interface Evidence {
    document_name: string;
    source_path: string;
    page_number?: number;
    section?: string;
    retrieved_text: string;
    similarity_score: number;
    metadata: { hybrid_scores?: { semantic: number; lexical: number } } & Record<string, unknown>;
}

export interface ComplianceResult {
    requirement: Requirement;
    status: 'covered' | 'partially_covered' | 'not_found' | 'needs_human_review';
    confidence: number;
    evidence_missing: boolean;
    supporting_evidence: Evidence[];
    conflict_analysis?: {
        conflict_detected: boolean;
        severity?: string;
        reason?: string;
        conflicting_evidence?: Evidence[];
    };
}

export interface ProposedResponse {
    requirement_id: string;
    proposed_response: string;
    needs_human_review: boolean;
}

export interface ReviewItem {
    review_id: string;
    bid_id: string;
    requirement_id: string;
    proposed_response: string;
    compliance_status: string;
    confidence: number;
    supporting_evidence: Evidence[];
    conflict_analysis?: {
        conflict_detected: boolean;
        severity?: string;
        reason?: string;
        conflicting_evidence?: Evidence[];
    };
    status: 'pending' | 'approved' | 'rejected' | 'needs_revision';
    review_status?: string;
    reviewer_comment?: string;
}

// Map the real APIs
export const API = {
    // Bids
    uploadBid: async (file: File) => {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('title', file.name);
        const res = await fetch(apiUrl('/api/bids/upload'), { method: 'POST', body: formData });
        if (!res.ok) throw new Error('Upload failed');
        return res.json();
    },

    analyzeBid: async (bidId: string) => {
        const res = await fetch(apiUrl(`/api/bids/${bidId}/analyze`), { method: 'POST' });
        if (!res.ok) {
            const body = await res.json().catch(() => null);
            throw new Error(body?.errors?.[0] ?? body?.detail ?? 'Analysis failed');
        }
        return res.json();
    },

    getBid: async (bidId: string) => {
        const res = await fetch(apiUrl(`/api/bids/${bidId}`));
        if (!res.ok) throw new Error('Fetch bid failed');
        return res.json() as Promise<Bid>;
    },

    getBids: async () => {
        const res = await fetch(apiUrl(`/api/bids`));
        if (!res.ok) throw new Error('Fetch bids failed');
        return res.json() as Promise<Bid[]>;
    },

    getRequirements: async (bidId: string) => {
        const res = await fetch(apiUrl(`/api/bids/${bidId}/requirements`));
        if (!res.ok) throw new Error('Fetch reqs failed');
        return res.json() as Promise<Requirement[]>;
    },

    getReviews: async (bidId: string) => {
        const res = await fetch(apiUrl(`/api/bids/${bidId}/reviews`));
        if (!res.ok) throw new Error('Fetch reviews failed');
        return res.json() as Promise<{ items: ReviewItem[] }>;
    },

    getAllReviews: async () => {
        const res = await fetch(apiUrl(`/api/reviews`));
        if (!res.ok) throw new Error('Fetch all reviews failed');
        return res.json() as Promise<{ items: ReviewItem[], total_pending: number }>;
    },

    reviewAction: async (reviewId: string, action: 'approve' | 'reject' | 'needs-revision', comment?: string) => {
        const res = await fetch(apiUrl(`/api/reviews/${reviewId}/${action}`), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ reviewer_comment: comment })
        });
        if (!res.ok) throw new Error('Review action failed');
        return res.json();
    },

    // Knowledge Base
    searchKB: async (query: string) => {
        const res = await fetch(apiUrl(`/api/knowledge-base/search?query=${encodeURIComponent(query)}`));
        if (!res.ok) throw new Error('KB search failed');
        return res.json();
    }
};
