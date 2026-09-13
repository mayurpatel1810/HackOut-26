/**
 * The single place the browser talks to the server.
 *
 * The page only ever calls the Spring Boot gateway. The Python AI service is
 * internal and is never addressable from the browser, so there is no route by
 * which a user could reach the engines directly.
 */

const BASE = import.meta.env.VITE_API_BASE || '/api';
const TOKEN_KEY = 'ecoforge.token';

export function getToken() {
  try { return localStorage.getItem(TOKEN_KEY) || ''; } catch { return ''; }
}
export function setToken(token) {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token);
    else localStorage.removeItem(TOKEN_KEY);
  } catch { /* private mode: the session simply lasts for this tab */ }
}

export class ApiError extends Error {
  constructor(message, { status, fields, requestId } = {}) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.fields = fields || {};
    this.requestId = requestId;
  }
}

async function request(path, { method = 'GET', body, signal } = {}) {
  const headers = { Accept: 'application/json' };
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;

  let res;
  try {
    res = await fetch(`${BASE}${path}`, {
      method,
      headers,
      signal,
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch (err) {
    if (err.name === 'AbortError') throw err;
    throw new ApiError(
      'EcoForge could not reach the server. Check that the backend is running, ' +
      'then try again.',
      { status: 0 },
    );
  }

  if (res.status === 401) {
    setToken('');
    throw new ApiError('Your session has expired. Please sign in again.', { status: 401 });
  }

  const text = await res.text();
  const data = text ? safeJson(text) : null;

  if (!res.ok) {
    throw new ApiError(
      (data && (data.message || data.detail)) ||
        'That request could not be completed.',
      { status: res.status, fields: data?.fields, requestId: data?.requestId },
    );
  }
  return data;
}

function safeJson(text) {
  try { return JSON.parse(text); } catch { return { message: text }; }
}

const get = (p, o) => request(p, { ...o, method: 'GET' });
const post = (p, body, o) => request(p, { ...o, method: 'POST', body });
const put = (p, body, o) => request(p, { ...o, method: 'PUT', body });

export const api = {
  // --- auth ---------------------------------------------------------------
  register: (payload) => post('/auth/register', payload),
  login: (payload) => post('/auth/login', payload),

  // --- factories ----------------------------------------------------------
  listFactories: () => get('/factories'),
  getFactory: (id) => get(`/factories/${id}`),
  createFactory: (payload) => post('/factories', payload),
  updateFactory: (id, payload) => put(`/factories/${id}`, payload),
  getActivity: (id) => get(`/factories/${id}/activity`),
  saveActivity: (id, payload) => put(`/factories/${id}/activity`, payload),

  // --- analysis -----------------------------------------------------------
  analyze: (id, options, signal) =>
    post(`/factories/${id}/analyze`, options ?? {}, { signal }),
  anomalies: (id) => get(`/factories/${id}/anomalies`),

  // --- decisions ----------------------------------------------------------
  optimise: (id, budgetInr, options) =>
    post(`/optimization/${id}`, { budgetInr, options }),
  budgetCurve: (id, budgets, options) =>
    post(`/optimization/${id}/curve`, { budgets, options }),
  simulate: (id, selection, options) =>
    post(`/simulations/${id}`, { selection, options }),
  actionPlan: (id, budgetInr, options) =>
    post(`/factories/${id}/action-plan`, { budgetInr, options }),

  // --- evidence & copilot --------------------------------------------------
  evidence: (id, payload) => post(`/factories/${id}/evidence`, payload),
  copilot: (id, payload) => post(`/factories/${id}/copilot`, payload),
  extract: (text) => post('/copilot/extract', { text }),
  factorSources: () => get('/evidence/sources'),
  aiHealth: () => get('/public/ai-health'),

  // --- reports -------------------------------------------------------------
  report: (id, budgetInr, options) => post(`/reports/${id}`, { budgetInr, options }),
};
