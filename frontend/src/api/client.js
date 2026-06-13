/**
 * API Client — Axios instance configured for the Django backend.
 */

import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || '';

const api = axios.create({
  baseURL: `${API_BASE_URL}/api`,
  headers: {
    'Content-Type': 'application/json',
  },
});

// ─── CSV Upload ──────────────────────────────────────────

export const uploadCSV = async (file) => {
  const formData = new FormData();
  formData.append('file', file);

  const response = await api.post('/upload/', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data;
};

// ─── Import Sessions ─────────────────────────────────────

export const getImportSessions = async () => {
  const response = await api.get('/import-sessions/');
  return response.data;
};

export const getImportSession = async (id) => {
  const response = await api.get(`/import-sessions/${id}/`);
  return response.data;
};

// ─── Expenses ────────────────────────────────────────────

export const getExpenses = async (params = {}) => {
  const response = await api.get('/expenses/', { params });
  return response.data;
};

export const getExpense = async (id) => {
  const response = await api.get(`/expenses/${id}/`);
  return response.data;
};

// ─── Balances & Settlements ──────────────────────────────

export const getBalances = async (sessionId) => {
  const params = sessionId ? { session: sessionId } : {};
  const response = await api.get('/balances/', { params });
  return response.data;
};

export const getSettlements = async (sessionId) => {
  const params = sessionId ? { session: sessionId } : {};
  const response = await api.get('/settlements/', { params });
  return response.data;
};

// ─── Persons ─────────────────────────────────────────────

export const getPersons = async () => {
  const response = await api.get('/persons/');
  return response.data;
};

export const createPerson = async (data) => {
  const response = await api.post('/persons/', data);
  return response.data;
};

export const updatePerson = async (id, data) => {
  const response = await api.patch(`/persons/${id}/`, data);
  return response.data;
};

// ─── Anomalies ───────────────────────────────────────────

export const getAnomalies = async (params = {}) => {
  const response = await api.get('/anomalies/', { params });
  return response.data;
};

// ─── Config ──────────────────────────────────────────────

export const getConfig = async () => {
  const response = await api.get('/config/');
  return response.data;
};

export const updateConfig = async (data) => {
  const response = await api.patch('/config/', data);
  return response.data;
};

export default api;
