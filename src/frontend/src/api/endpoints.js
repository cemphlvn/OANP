import http, { withRetry } from './http'

// Health & Stats
export const getHealth = () => http.get('/health')
export const getStats = () => http.get('/api/stats')

// Scenarios — backend returns { scenarios: [...] }
export const getScenarios = () => http.get('/api/scenarios').then(d => d.scenarios || d)

// Sessions
export const createSession = (scenarioPath, advancedConfig = null) =>
  withRetry(() => http.post('/api/sessions', {
    scenario_path: scenarioPath || null,
    ...(advancedConfig || {})
  }))

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

// Institutions (advanced mode)
export const getInstitutions = () =>
  http.get('/api/institutions').then(d => d.institutions || d)

export const getInstitution = (institutionId) =>
  http.get(`/api/institutions/${institutionId}`)

// Compliance (advanced mode)
export const getCompliance = (sessionId) =>
  http.get(`/api/sessions/${sessionId}/compliance`)

// Demos
export const getDemos = () => http.get('/api/demos').then(d => d.demos || d)
export const getDemo = (sessionId) => http.get(`/api/demos/${sessionId}`)
