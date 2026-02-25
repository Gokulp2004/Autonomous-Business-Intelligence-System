/**
 * api.js — API Service Layer
 *
 * All HTTP calls to the FastAPI backend go through here.
 * This keeps API logic in one place, so components stay clean.
 *
 * Uses axios for HTTP requests (cleaner than fetch for error handling).
 */

import axios from 'axios';

// In dev, Vite proxies /api to localhost:8000
// In production, VITE_API_URL points to the deployed backend
const API = axios.create({
    baseURL: import.meta.env.VITE_API_URL || '/api',
    timeout: 120000, // 2 minutes (analysis can take time)
});

// ── Upload ──────────────────────────────────────────────────────

export async function uploadFile(file) {
    const formData = new FormData();
    formData.append('file', file);

    const response = await API.post('/upload/', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
}

// ── Analysis ────────────────────────────────────────────────────

export async function runAnalysis(fileId) {
    const response = await API.post(`/analysis/run/${fileId}`);
    return response.data;
}

export async function getAnalysisResults(fileId) {
    const response = await API.get(`/analysis/results/${fileId}`);
    return response.data;
}

export async function generateInsights(fileId) {
    const response = await API.post(`/analysis/insights/${fileId}`);
    return response.data;
}

// ── Dashboard ───────────────────────────────────────────────────

export async function getDashboardSummary(fileId) {
    const response = await API.get(`/dashboard/summary/${fileId}`);
    return response.data;
}

export async function getCharts(fileId) {
    const response = await API.get(`/dashboard/charts/${fileId}`);
    return response.data;
}

// ── Chat ────────────────────────────────────────────────────────

export async function askQuestion(fileId, question, history = []) {
    const response = await API.post('/chat/ask', {
        file_id: fileId,
        question,
        history: history.map(m => ({ role: m.role, content: m.content })),
    });
    return response.data;
}

export async function getChatSuggestions(fileId) {
    const response = await API.get(`/chat/suggestions/${fileId}`);
    return response.data;
}

// ── Reports ─────────────────────────────────────────────────────

export async function generateReport(fileId, format = 'pdf') {
    const response = await API.post(`/reports/generate/${fileId}?format=${format}`);
    return response.data;
}

/**
 * Build a full download URL from the backend's relative download_url.
 * In dev: /api/reports/download/file.pdf  (Vite proxy handles it)
 * In prod: https://autobi-backend.onrender.com/api/reports/download/file.pdf
 */
export function getDownloadUrl(backendPath) {
    const apiBase = import.meta.env.VITE_API_URL;
    if (apiBase) {
        // Production: VITE_API_URL = https://...onrender.com/api
        // backendPath  = /api/reports/download/file.pdf
        // Result       = https://...onrender.com/api/reports/download/file.pdf
        return backendPath.replace(/^\/api/, apiBase);
    }
    // Dev: relative path works via Vite proxy
    return backendPath;
}

export default API;
