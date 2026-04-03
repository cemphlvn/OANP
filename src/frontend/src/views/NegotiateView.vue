<template>
  <div class="negotiate-view">
    <!-- Status Strip + View Toggle -->
    <StatusStrip
      :phase="session.protocol.phase"
      :round="session.protocol.round"
      :totalRounds="session.protocol.total_rounds"
      :moveCount="session.moves.length"
      :resolvedCount="session.resolvedCount"
      :totalIssues="session.issues.length"
      :convergence="session.convergence"
      :outcome="session.outcome"
      :isAdvancedMode="store.isAdvancedMode()"
      :escalationTier="session.escalationTier"
      :tierDeadline="store.tierDeadline()"
      :stagnationDetected="session.stagnationDetected"
      :complianceOpen="complianceSidebarOpen"
      @viewAnalysis="goToAnalysis"
      @toggleCompliance="complianceSidebarOpen = !complianceSidebarOpen"
    >
      <ViewToggle v-model="viewMode" />
    </StatusStrip>

    <!-- Expandable scenario details -->
    <ScenarioDrawer
      v-if="!session.isSetupPhase"
      :parties="session.parties"
      :issues="session.issues"
      :criteria="session.criteria"
    />

    <!-- Main content area with collapsible left panel -->
    <div class="nv-main">
      <!-- Setup Phase (full width) -->
      <SetupPanel
        v-if="session.isSetupPhase"
        :sessionId="sessionId"
        :parties="session.parties"
        :issues="session.issues"
        :anchorsStatus="session.anchorsStatus"
        :anchorsData="session.anchorsData"
      />

      <!-- Active Negotiation: left panel + right content -->
      <template v-else>
        <!-- Left Panel: Graph (collapsible) -->
        <div class="nv-left" :class="{ collapsed: !leftPanelOpen }" :style="{ width: leftPanelOpen ? leftPanelWidth + 'px' : '0px' }">
          <div class="nv-left-inner" v-show="leftPanelOpen">
            <NegotiationGraph
              :key="'graph-' + graphKey"
              :parties="session.parties"
              :issues="session.issues"
              :criteria="session.criteria"
              :moves="session.moves"
              :phase="session.protocol.phase"
              :activePartyId="session.thinkingPartyId"
              :outcome="session.outcome"
              :agreement="session.agreement"
              :isLive="!isFinished"
            />
          </div>
          <!-- Resize handle -->
          <div class="nv-left-resize" @mousedown="startLeftResize" v-if="leftPanelOpen"></div>
        </div>

        <!-- Left panel toggle -->
        <button class="nv-left-toggle" @click="toggleLeftPanel" :title="leftPanelOpen ? 'Hide Graph' : 'Show Graph'">
          <span class="toggle-icon">{{ leftPanelOpen ? '◂' : '▸' }}</span>
          <span class="toggle-label" v-if="!leftPanelOpen">Graph</span>
        </button>

        <!-- Right: Active view -->
        <div class="nv-right">
          <Arena
            v-if="viewMode === 'arena'"
            :moves="session.moves"
            :parties="session.parties"
            :thinkingPartyId="session.thinkingPartyId"
            :isAdvancedMode="store.isAdvancedMode()"
            :escalationTier="session.escalationTier"
          />
          <XRayView
            v-else-if="viewMode === 'xray'"
            :moves="session.moves"
            :parties="session.parties"
          />
          <TimelineView
            v-else-if="viewMode === 'timeline'"
            :moves="session.moves"
            :parties="session.parties"
            :thinkingPartyId="session.thinkingPartyId"
          />
        </div>

        <!-- Compliance Sidebar (advanced mode, collapsible right) -->
        <div v-if="store.isAdvancedMode() && complianceSidebarOpen" class="nv-compliance">
          <ComplianceSidebar
            :compliance="session.compliance"
            :moves="session.moves"
            :parties="session.parties"
            :tierHistory="session.tierHistory"
            :deadlineStatus="session.deadlineStatus"
            :stagnationDetected="session.stagnationDetected"
            @close="complianceSidebarOpen = false"
          />
        </div>
      </template>
    </div>

    <!-- Issue Tracker (always visible after setup) -->
    <IssueTracker
      v-if="!session.isSetupPhase"
      :issues="session.issues"
      :issueStates="session.issueStates"
      :parties="session.parties"
      :agreement="session.agreement"
    />

    <!-- System Log (resizable) -->
    <div class="nv-log" :style="{ height: logHeight + 'px' }">
      <div class="log-drag-handle" @mousedown="startLogResize">
        <span class="drag-dots">&#8230;</span>
      </div>
      <div class="log-header">
        <span class="log-title">SYSTEM DASHBOARD</span>
        <div class="log-controls">
          <button class="log-size-btn" @click="logHeight = logHeight === 40 ? 160 : 40" :title="logHeight <= 40 ? 'Expand' : 'Collapse'">
            {{ logHeight <= 40 ? '&#9650;' : '&#9660;' }}
          </button>
          <span class="log-id">{{ sessionId?.slice(0, 12) }}</span>
        </div>
      </div>
      <div class="log-content" ref="logRef" v-show="logHeight > 50">
        <div class="log-line" v-for="(log, idx) in session.logs" :key="idx">
          <span class="log-time">{{ log.time }}</span>
          <span class="log-type" :class="'lt-' + log.type">{{ log.type }}</span>
          <span class="log-msg" :class="'lm-' + log.type">{{ log.message }}</span>
        </div>
      </div>
    </div>

    <!-- Phase Transition Overlay -->
    <PhaseTransition
      :visible="showPhaseTransition"
      :phase="phaseTransitionData.phase"
      :message="phaseTransitionData.message"
    />

    <!-- Tier Transition Overlay (advanced mode) -->
    <TierTransition
      v-if="session.tierTransition"
      :visible="!!session.tierTransition"
      :from="session.tierTransition?.from"
      :to="session.tierTransition?.to"
      :reason="session.tierTransition?.reason"
    />

    <!-- Settlement Card Overlay -->
    <SettlementCard
      :visible="showSettlement"
      :agreement="session.agreement"
      :rounds="session.protocol.round"
      :moveCount="session.moves.length"
      :award="session.award"
      @close="showSettlement = false"
      @viewAnalysis="goToAnalysis"
    />
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted, provide, nextTick } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { createSessionStore, SESSION_KEY } from '@/store/session'
import { getDemo } from '@/api/endpoints'

// Chamber components
import StatusStrip from '@/components/chamber/StatusStrip.vue'
import ViewToggle from '@/components/chamber/ViewToggle.vue'
import Arena from '@/components/chamber/Arena.vue'
import XRayView from '@/components/chamber/XRayView.vue'
import TimelineView from '@/components/chamber/TimelineView.vue'
import IssueTracker from '@/components/chamber/IssueTracker.vue'
import SetupPanel from '@/components/chamber/SetupPanel.vue'
import PhaseTransition from '@/components/chamber/PhaseTransition.vue'
import TierTransition from '@/components/chamber/TierTransition.vue'
import ComplianceSidebar from '@/components/chamber/ComplianceSidebar.vue'
import SettlementCard from '@/components/chamber/SettlementCard.vue'
import NegotiationGraph from '@/d3/NegotiationGraph.vue'
import ScenarioDrawer from '@/components/chamber/ScenarioDrawer.vue'

const props = defineProps({ sessionId: String })
const router = useRouter()
const route = useRoute()

// Session store
const store = createSessionStore()
provide(SESSION_KEY, store)
const { state: session } = store
const complianceSidebarOpen = ref(false)

// UI state
const viewMode = ref('arena')
const logRef = ref(null)
const logHeight = ref(160)
const graphKey = ref(0)
const leftPanelOpen = ref(true)
const leftPanelWidth = ref(420)
const showSettlement = ref(false)
const showPhaseTransition = ref(false)
const phaseTransitionData = ref({ phase: '', message: '' })

// Log resize drag
function startLogResize(e) {
  e.preventDefault()
  const startY = e.clientY
  const startH = logHeight.value
  function onMove(ev) {
    const delta = startY - ev.clientY
    logHeight.value = Math.max(40, Math.min(400, startH + delta))
  }
  function onUp() {
    document.removeEventListener('mousemove', onMove)
    document.removeEventListener('mouseup', onUp)
  }
  document.addEventListener('mousemove', onMove)
  document.addEventListener('mouseup', onUp)
}

const isFinished = computed(() => session.outcome === 'agreement' || session.outcome === 'impasse')

function toggleLeftPanel() {
  leftPanelOpen.value = !leftPanelOpen.value
  if (leftPanelOpen.value) graphKey.value++ // re-mount graph with fresh dimensions
}

function startLeftResize(e) {
  e.preventDefault()
  const startX = e.clientX
  const startW = leftPanelWidth.value
  function onMove(ev) {
    leftPanelWidth.value = Math.max(280, Math.min(700, startW + (ev.clientX - startX)))
  }
  function onUp() {
    document.removeEventListener('mousemove', onMove)
    document.removeEventListener('mouseup', onUp)
    graphKey.value++ // re-mount graph after resize
  }
  document.addEventListener('mousemove', onMove)
  document.addEventListener('mouseup', onUp)
}

// Show settlement card when agreement is reached
watch(() => session.outcome, (val) => {
  if (val === 'agreement') {
    // Slight delay for dramatic effect
    setTimeout(() => { showSettlement.value = true }, 500)
  }
})

// Show phase transition overlay on phase changes
watch(() => session.protocol.phase, (newPhase, oldPhase) => {
  if (newPhase && newPhase !== oldPhase && newPhase !== 'setup') {
    phaseTransitionData.value = {
      phase: newPhase,
      message: '' // Could extract from the phase_change event
    }
    showPhaseTransition.value = true
    setTimeout(() => { showPhaseTransition.value = false }, 1800)
  }
})

// Auto-scroll log
watch(() => session.logs.length, () => {
  nextTick(() => {
    logRef.value?.scrollTo({ top: logRef.value.scrollHeight, behavior: 'smooth' })
  })
})

function goToAnalysis() {
  router.push({ name: 'Analysis', params: { sessionId: props.sessionId } })
}

onMounted(async () => {
  const isDemo = route.query.demo === '1'

  if (isDemo) {
    // Demo mode: load pre-recorded event stream and replay
    try {
      const demo = await getDemo(props.sessionId)
      if (demo.error) {
        store.addLog('error', `Demo not found: ${demo.error}`)
        return
      }
      store.loadDemo(demo)
      // Start replay after a short delay for the UI to render
      setTimeout(() => {
        store.startReplay(demo.events, 1)
      }, 500)
    } catch (err) {
      store.addLog('error', `Failed to load demo: ${err.message}`)
    }
    return
  }

  // Normal mode: load session from backend
  await store.loadSession(props.sessionId)

  // Completed sessions: moves already loaded, skip WebSocket
  if (session.outcome || session.moves.length > 0) {
    store.addLog('system', `Loaded completed session (${session.moves.length} moves, ${session.outcome})`)
    return
  }

  // Live session: connect WebSocket
  store.connectWs(props.sessionId)

  // Only send start if this is a direct navigation (not from SessionView)
  if (session.moves.length === 0 && !session.outcome && session.protocol.phase === 'setup') {
    setTimeout(async () => {
      if (session.moves.length === 0 && session.protocol.phase === 'setup' && !session.outcome) {
        await store.sendStart()
      }
    }, 2000)
  }
})

onUnmounted(() => {
  if (!session.outcome || session.outcome === null) {
    store.disconnectWs()
  }
})
</script>

<style scoped>
.negotiate-view {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: #FFF;
  overflow: hidden;
  font-family: var(--font-heading);
}

.nv-main {
  flex: 1;
  overflow: hidden;
  display: flex;
  position: relative;
}

/* Left panel (graph) */
.nv-left {
  height: 100%;
  border-right: 1px solid var(--border);
  transition: width 0.3s var(--ease-panel);
  overflow: hidden;
  flex-shrink: 0;
  position: relative;
}

.nv-left.collapsed {
  border-right: none;
}

.nv-left-inner {
  width: 100%;
  height: 100%;
}

.nv-left-resize {
  position: absolute;
  top: 0;
  right: -3px;
  width: 6px;
  height: 100%;
  cursor: ew-resize;
  z-index: 10;
}

.nv-left-resize:hover {
  background: var(--accent);
  opacity: 0.3;
}

.nv-left-toggle {
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  z-index: 20;
  background: #FFF;
  border: 1px solid var(--border);
  border-left: none;
  border-radius: 0 6px 6px 0;
  padding: 8px 4px;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #999;
  transition: all 0.15s;
  box-shadow: 2px 0 8px rgba(0,0,0,0.04);
}

.nv-left.collapsed ~ .nv-left-toggle {
  left: 0;
}

.nv-left:not(.collapsed) ~ .nv-left-toggle {
  /* Position right at the edge of the left panel */
  /* This is handled by the flex layout — toggle sits after nv-left */
}

.nv-left-toggle:hover { color: var(--accent); border-color: var(--accent); }

.toggle-icon { font-size: 11px; line-height: 1; }

.toggle-label {
  writing-mode: vertical-rl;
  font-family: var(--font-mono);
  font-size: 9px;
  font-weight: 600;
  letter-spacing: 1px;
  text-transform: uppercase;
}

/* Right panel (active view) */
.nv-right {
  flex: 1;
  height: 100%;
  overflow: hidden;
  min-width: 0;
}

/* Compliance sidebar (advanced mode, right side) */
.nv-compliance {
  width: 280px;
  height: 100%;
  border-left: 1px solid var(--border);
  flex-shrink: 0;
  overflow-y: auto;
}

/* System Log */
.nv-log {
  background: #000;
  color: #DDD;
  padding: 0 20px 10px;
  font-family: var(--font-mono);
  border-top: 1px solid #222;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.log-drag-handle {
  height: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: ns-resize;
  user-select: none;
  color: #444;
  font-size: 16px;
  letter-spacing: 2px;
  flex-shrink: 0;
}

.log-drag-handle:hover { color: #888; }

.log-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid #333;
  padding-bottom: 6px;
  margin-bottom: 6px;
  font-size: 10px;
  color: #666;
  flex-shrink: 0;
}

.log-controls {
  display: flex;
  align-items: center;
  gap: 10px;
}

.log-size-btn {
  background: none;
  border: 1px solid #333;
  color: #666;
  font-size: 10px;
  cursor: pointer;
  padding: 1px 6px;
  border-radius: 3px;
  line-height: 1;
}

.log-size-btn:hover { border-color: #666; color: #AAA; }

.log-content {
  display: flex;
  flex-direction: column;
  gap: 2px;
  flex: 1;
  overflow-y: auto;
}

.log-content::-webkit-scrollbar { width: 4px; }
.log-content::-webkit-scrollbar-thumb { background: #333; border-radius: 2px; }

.log-line {
  font-size: 11px;
  display: flex;
  gap: 8px;
  line-height: 1.5;
}

.log-time { color: #555; min-width: 75px; flex-shrink: 0; }

.log-type {
  min-width: 44px; font-size: 9px; font-weight: 600;
  text-transform: uppercase; letter-spacing: 0.5px; flex-shrink: 0;
}

.lt-system { color: #666; }
.lt-setup { color: var(--accent); }
.lt-phase { color: #06b6d4; }
.lt-move { color: #a855f7; }
.lt-mediator { color: #22c55e; }
.lt-settlement { color: #22c55e; }
.lt-impasse { color: #ef4444; }
.lt-error { color: #ef4444; }

.log-msg { color: #AAA; word-break: break-word; }
.lm-setup { color: #FF8A65; }
.lm-phase { color: #4DD0E1; }
.lm-error { color: #EF9A9A; }
.lm-settlement { color: #A5D6A7; }
</style>
