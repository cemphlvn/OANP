import { reactive, ref } from 'vue'
import { getSession, getMoves } from '@/api/endpoints'
import { OANPWebSocket } from '@/api/ws'
import { PARTY_COLORS } from '@/types/protocol'

/**
 * Creates a per-session reactive store.
 * Call once per session route, provide to children via provide/inject.
 */
export function createSessionStore() {
  const state = reactive({
    sessionId: null,
    parties: [],
    issues: [],
    criteria: [],
    constraints: [],
    protocol: {
      phase: 'setup',
      round: 0,
      total_rounds: 0,
      total_moves: 0
    },
    moves: [],
    outcome: null,
    agreement: null,
    thinkingPartyId: null,
    humanTurn: null, // { partyId, legalMoves[] } when awaiting human input
    startedAt: null,
    anchorsStatus: {}, // partyId -> 'pending' | 'done' | 'failed'
    anchorsData: {},   // partyId -> [{ description, interest_type, priority, anchors: [{condition, score, reason}] }]
    isSetupPhase: true, // true until first move arrives
    isDemoMode: false,  // true when replaying a pre-recorded demo
    issueStates: {},   // issueId -> { partyValues: { partyId: value }, agreed: bool, agreedValue: string }
    resolvedCount: 0,
    convergence: 0,    // 0-100 percentage
    logs: [],
    // Advanced mode: legal compliance
    compliance: null,       // full compliance metadata from backend
    award: null,            // AwardRecord from settlement event
    escalationTier: null,   // 'negotiation' | 'mediation' | 'arbitration'
    tierHistory: [],        // [{from_tier, to_tier, reason, at_round}]
    deadlineStatus: null,   // {type, current, limit, remaining}
    stagnationDetected: false,
    tierTransition: null,   // {from, to, reason} — triggers overlay
    // BCI opponent model
    beliefs: {},            // "observerId→targetId" -> belief payload
    beliefHistory: [],      // chronological snapshots for Beliefs view
  })

  const ws = new OANPWebSocket()
  const connectionStatus = ws.status

  // Map party IDs to colors
  function partyColor(partyId) {
    const idx = state.parties.findIndex(p => p.id === partyId)
    return idx >= 0 ? PARTY_COLORS[idx % PARTY_COLORS.length] : '#999999'
  }

  function partyName(partyId) {
    const party = state.parties.find(p => p.id === partyId)
    return party?.name || partyId
  }

  function addLog(type, message) {
    const time = new Date().toLocaleTimeString('en-US', {
      hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit'
    }) + '.' + String(new Date().getMilliseconds()).padStart(3, '0')
    state.logs.push({ time, type, message })
    if (state.logs.length > 200) state.logs.shift()
  }

  async function loadSession(sessionId) {
    state.sessionId = sessionId
    try {
      const data = await getSession(sessionId)
      state.parties = data.parties || []
      state.issues = data.issues || []
      // Initialize anchor status for each party (replace whole object for reactivity)
      const anchors = {}
      for (const party of state.parties) {
        anchors[party.id] = 'pending'
      }
      state.anchorsStatus = anchors
      state.criteria = data.criteria || []
      state.protocol = data.protocol || state.protocol
      state.moves = data.move_history || []
      state.outcome = data.outcome || null
      state.agreement = data.agreement || null
      // Load compliance data (advanced mode)
      state.compliance = data.compliance || null
      state.award = data.award || null
      if (data.compliance) {
        state.escalationTier = data.compliance.current_tier || null
        state.tierHistory = data.compliance.tier_history || []
      }
      // If moves exist or outcome is set, setup is done
      if (state.moves.length > 0 || state.outcome) {
        state.isSetupPhase = false
      }
      // If phase is not setup, mark setup done
      if (state.protocol.phase && state.protocol.phase !== 'setup') {
        state.isSetupPhase = false
      }
      // Rebuild issue states from existing moves
      for (const move of state.moves) {
        updateIssueStates(move)
      }
      addLog('system', `Session loaded: ${sessionId}`)
    } catch (err) {
      addLog('error', `Failed to load session: ${err.message}`)
    }
  }

  function connectWs(sessionId) {
    ws.connect(sessionId)
    ws.onEvent(handleEvent)
    addLog('system', 'WebSocket connecting...')
  }

  async function waitForConnection() {
    await ws.waitForOpen()
  }

  function handleEvent(event) {
    const { type, data } = event

    switch (type) {
      case 'phase_change':
        state.protocol.phase = data.phase
        state.protocol.round = data.round
        state.thinkingPartyId = null
        if (data.phase !== 'setup') {
          state.isSetupPhase = false
        }
        // Initial connect event has parties instead of message
        if (data.parties && !state.parties.length) {
          state.parties = data.parties
          const anchors = {}
          for (const p of data.parties) {
            anchors[p.id] = 'pending'
          }
          state.anchorsStatus = anchors
        }
        addLog('phase', `${data.phase.toUpperCase()}${data.message ? ' — ' + data.message : ''}`)
        break

      case 'move':
        // Attach latest BCI belief snapshot to the move (for MoveCard display)
        if (Object.keys(state.beliefs).length > 0) {
          const beliefKey = Object.keys(state.beliefs).find(
            k => k.startsWith(data.party_id + '→')
          )
          if (beliefKey) {
            data.belief_snapshot = state.beliefs[beliefKey]
          }
        }
        state.moves.push(data)
        state.protocol.total_moves = state.moves.length
        state.thinkingPartyId = null
        state.humanTurn = null
        state.isSetupPhase = false
        updateIssueStates(data)
        addLog('move', `${partyName(data.party_id)}: ${data.move_type}`)
        // Track who's thinking next (the other party)
        if (state.parties.length >= 2) {
          const nextParty = state.parties.find(p => p.id !== data.party_id)
          if (nextParty) state.thinkingPartyId = nextParty.id
        }
        break

      case 'mediator_note':
        state.moves.push({ ...data, _isMediatorNote: true })
        state.protocol.total_moves = state.moves.length
        addLog('mediator', `Mediator: ${data.move_type}`)
        break

      case 'tier_change':
        state.escalationTier = data.to_tier
        state.tierHistory.push({
          from_tier: data.from_tier,
          to_tier: data.to_tier,
          reason: data.reason,
          at_round: data.at_round,
        })
        state.tierTransition = { from: data.from_tier, to: data.to_tier, reason: data.reason }
        // Clear tier transition overlay after 3s
        setTimeout(() => { state.tierTransition = null }, 3000)
        addLog('phase', `ESCALATION: ${data.from_tier.toUpperCase()} → ${data.to_tier.toUpperCase()} (${data.reason})`)
        break

      case 'deadline_warning':
        state.deadlineStatus = {
          type: data.type,
          current: data.current,
          limit: data.limit,
          remaining: data.remaining,
        }
        addLog('system', `⚠ Deadline warning: ${data.remaining} rounds remaining (${data.type})`)
        break

      case 'stagnation_detected':
        state.stagnationDetected = true
        addLog('system', `⚠ ${data.message}`)
        // Reset after 2 rounds
        setTimeout(() => { state.stagnationDetected = false }, 30000)
        break

      case 'settlement':
        state.outcome = 'agreement'
        state.agreement = data.agreement
        state.award = data.award || null
        state.protocol.total_rounds = data.total_rounds || state.protocol.round
        state.thinkingPartyId = null
        // Mark all issues as agreed from the settlement package
        if (data.agreement?.issue_values) {
          for (const [issueId, value] of Object.entries(data.agreement.issue_values)) {
            if (!state.issueStates[issueId]) {
              state.issueStates[issueId] = { partyValues: {}, agreed: false, agreedValue: null }
            }
            state.issueStates[issueId].agreed = true
            state.issueStates[issueId].agreedValue = value
          }
          state.resolvedCount = Object.keys(data.agreement.issue_values).length
          state.convergence = 100
          state.issueStates = { ...state.issueStates }
        }
        addLog('settlement', `Agreement reached in ${data.total_rounds} rounds`)
        break

      case 'impasse':
        state.outcome = 'impasse'
        state.thinkingPartyId = null
        addLog('impasse', data.message || 'Negotiation ended in impasse')
        break

      case 'turn_request':
        state.humanTurn = {
          partyId: data.party_id,
          legalMoves: data.legal_moves || []
        }
        state.thinkingPartyId = null
        addLog('system', `Your turn: ${partyName(data.party_id)}`)
        break

      case 'setup_progress':
        addLog('setup', data.message)
        break

      case 'anchor_progress': {
        const pct = data.total_interests > 0
          ? Math.round((data.completed_interests / data.total_interests) * 100)
          : 0
        addLog('setup', `[${pct}%] ${data.party_name}: anchored "${data.interest_description}" (${data.anchor_count} anchors)`)
        break
      }

      case 'anchors_generated':
        // Replace entire object to guarantee Vue reactivity trigger
        state.anchorsStatus = { ...state.anchorsStatus, [data.party_id]: 'done' }
        if (data.interests) {
          state.anchorsData = { ...state.anchorsData, [data.party_id]: data.interests }
        }
        addLog('system', `Anchors generated for ${partyName(data.party_id)} (${data.anchor_count} anchors)`)
        break

      case 'anchors_failed':
        state.anchorsStatus = { ...state.anchorsStatus, [data.party_id]: 'failed' }
        addLog('error', `Anchor generation failed for ${partyName(data.party_id)}`)
        break

      case 'belief_update': {
        const bkey = `${data.observer_party_id}→${data.target_party_id}`
        state.beliefs[bkey] = data.belief
        state.beliefHistory.push({
          round: state.protocol.round,
          observer_party_id: data.observer_party_id,
          target_party_id: data.target_party_id,
          ...data.belief,
        })
        break
      }

      case 'validation_error':
        addLog('error', `Validation: ${data.violations?.join(', ')}`)
        break

      case 'error':
        addLog('error', data.message || 'Unknown error')
        break

      default:
        addLog('system', `Unknown event: ${type}`)
    }
  }

  async function sendStart(config = {}) {
    await ws.waitForOpen()
    state.startedAt = Date.now()
    ws.send({ type: 'start', config })
    addLog('system', 'Negotiation started')
  }

  function sendHumanMove(move) {
    ws.send({ type: 'human_move', ...move })
    state.humanTurn = null
    addLog('system', `Submitted move: ${move.move_type}`)
  }

  /** Update per-issue tracking from a move's package */
  function updateIssueStates(move) {
    if (!move.package?.issue_values) return
    const vals = move.package.issue_values
    for (const [issueId, value] of Object.entries(vals)) {
      if (!state.issueStates[issueId]) {
        state.issueStates[issueId] = { partyValues: {}, agreed: false, agreedValue: null }
      }
      state.issueStates[issueId].partyValues[move.party_id] = value
    }
    // Check for agreement on each issue
    let resolved = 0
    const issueIds = Object.keys(state.issueStates)
    for (const id of issueIds) {
      const is = state.issueStates[id]
      const values = Object.values(is.partyValues)
      if (values.length >= 2 && new Set(values).size === 1) {
        is.agreed = true
        is.agreedValue = values[0]
        resolved++
      }
    }
    state.resolvedCount = resolved
    // Convergence = resolved / total issues
    const total = state.issues.length || 1
    state.convergence = Math.round((resolved / total) * 100)
    // Trigger reactivity
    state.issueStates = { ...state.issueStates }
  }

  function disconnectWs() {
    ws.disconnect()
    addLog('system', 'WebSocket disconnected')
  }

  /**
   * Load and replay a demo recording.
   * Feeds pre-recorded events into the store with realistic timing.
   */
  let replayTimers = []
  let replaySpeed = 1 // 1x, 2x, 4x

  function loadDemo(demo) {
    // Set initial state from demo data
    state.sessionId = demo.session_id
    state.parties = demo.parties || []
    state.issues = demo.issues || []
    state.criteria = demo.criteria || []
    state.isSetupPhase = false
    state.isDemoMode = true

    // Initialize anchor status as done
    const anchors = {}
    for (const p of state.parties) anchors[p.id] = 'done'
    state.anchorsStatus = anchors

    addLog('system', `Demo loaded: ${demo.scenario_name}`)
    addLog('system', `${demo.events?.length || 0} events to replay`)
  }

  function startReplay(events, speed = 1) {
    replaySpeed = speed
    stopReplay()

    addLog('system', `Replay started (${speed}x speed)`)

    let cumulativeDelay = 0
    events.forEach((event, idx) => {
      const delay = Math.max(50, (event.delay_ms || 500) / replaySpeed)
      cumulativeDelay += delay

      const timer = setTimeout(() => {
        handleEvent({ type: event.type, data: event.data })
      }, cumulativeDelay)

      replayTimers.push(timer)
    })
  }

  function stopReplay() {
    replayTimers.forEach(t => clearTimeout(t))
    replayTimers = []
  }

  function setReplaySpeed(speed) {
    replaySpeed = speed
  }

  function disconnectWs() {
    ws.disconnect()
    stopReplay()
    addLog('system', 'Disconnected')
  }

  /** Whether this session is in advanced (legal compliance) mode. */
  function isAdvancedMode() {
    return state.compliance?.mode === 'advanced'
  }

  /** Get the current tier's round deadline (if any). */
  function tierDeadline() {
    if (!state.compliance?.escalation) return null
    const esc = state.compliance.escalation
    const tier = state.escalationTier
    if (tier === 'negotiation') return esc.negotiation_deadline_rounds
    if (tier === 'mediation') return esc.mediation_deadline_rounds
    if (tier === 'arbitration') return esc.arbitration_deadline_rounds
    return null
  }

  return {
    state,
    connectionStatus,
    partyColor,
    partyName,
    addLog,
    loadSession,
    connectWs,
    waitForConnection,
    sendStart,
    sendHumanMove,
    disconnectWs,
    loadDemo,
    startReplay,
    stopReplay,
    setReplaySpeed,
    isAdvancedMode,
    tierDeadline,
  }
}

/** Injection key for provide/inject */
export const SESSION_KEY = Symbol('oanp-session')
