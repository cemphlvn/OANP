import http, { withRetry } from './http'

// Health & Stats
export const getHealth = () => http.get('/health')
export const getStats = () => http.get('/api/stats')

// Scenarios — backend returns { scenarios: [...] }
export const getScenarios = () => http.get('/api/scenarios').then(d => d.scenarios || d)

// Sessions
export const createSession = (scenarioPath) =>
  withRetry(() => http.post('/api/sessions', { scenario_path: scenarioPath || null }))

export const getSession = (sessionId) =>
  http.get(`/api/sessions/${sessionId}`)

export const getMoves = (sessionId) =>
  http.get(`/api/sessions/${sessionId}/moves`)

export const getAnalysis = (sessionId) =>
  http.get(`/api/sessions/${sessionId}/analysis`)

// Generation
export const generateScenario = (prompt) =>
  withRetry(() => http.post('/api/generate', { prompt }))

// Multi-turn specify
export const specifyStep = (sessionId, message) =>
  http.post('/api/specify', { session_id: sessionId || null, message })

// Demos
export const getDemos = () => http.get('/api/demos').then(d => d.demos || d)
export const getDemo = (sessionId) => http.get(`/api/demos/${sessionId}`)
