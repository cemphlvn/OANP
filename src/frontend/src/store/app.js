import { reactive } from 'vue'
import { getScenarios, getStats } from '@/api/endpoints'

const HISTORY_KEY = 'oanp_history'

const state = reactive({
  scenarios: [],
  stats: { sessions_total: 0 },
  history: [],
  loading: false
})

export function useAppStore() {
  async function loadScenarios() {
    try {
      const data = await getScenarios()
      state.scenarios = data
    } catch (err) {
      console.error('[OANP] Failed to load scenarios:', err)
    }
  }

  async function loadStats() {
    try {
      const data = await getStats()
      state.stats = data
    } catch (err) {
      console.error('[OANP] Failed to load stats:', err)
    }
  }

  function loadHistory() {
    try {
      const raw = localStorage.getItem(HISTORY_KEY)
      state.history = raw ? JSON.parse(raw) : []
    } catch {
      state.history = []
    }
  }

  function addToHistory(session) {
    // Prepend, deduplicate by session_id, keep last 50
    state.history = [
      session,
      ...state.history.filter(s => s.session_id !== session.session_id)
    ].slice(0, 50)
    localStorage.setItem(HISTORY_KEY, JSON.stringify(state.history))
  }

  function removeFromHistory(sessionId) {
    state.history = state.history.filter(s => s.session_id !== sessionId)
    localStorage.setItem(HISTORY_KEY, JSON.stringify(state.history))
  }

  return {
    state,
    loadScenarios,
    loadStats,
    loadHistory,
    addToHistory,
    removeFromHistory
  }
}
