<template>
  <div class="main-view">
    <header class="app-header">
      <div class="header-left">
        <div class="brand" @click="$router.push('/')">OANP</div>
      </div>
      <div class="header-center">
        <div class="view-switcher">
          <button
            v-for="mode in ['graph', 'split', 'workbench']"
            :key="mode"
            class="switch-btn"
            :class="{ active: viewMode === mode }"
            @click="viewMode = mode"
          >
            {{ { graph: 'Graph', split: 'Split', workbench: 'Workbench' }[mode] }}
          </button>
        </div>
      </div>
      <div class="header-right">
        <div class="workflow-step">
          <span class="step-num">Step 1/4</span>
          <span class="step-name">Scenario Review</span>
        </div>
        <div class="step-divider"></div>
        <span class="status-indicator" :class="statusClass">
          <span class="dot"></span>
          {{ statusText }}
        </span>
      </div>
    </header>

    <main class="content-area">
      <!-- Left Panel: Negotiation Graph -->
      <div class="panel-wrapper left" :style="leftPanelStyle">
        <NegotiationGraph
          :parties="session.parties"
          :issues="session.issues"
          :criteria="session.criteria"
          :moves="session.moves"
          :phase="session.protocol.phase"
          @toggle-maximize="viewMode = viewMode === 'graph' ? 'split' : 'graph'"
        />
      </div>

      <!-- Right Panel: Scenario Review -->
      <div class="panel-wrapper right" :style="rightPanelStyle">
        <div class="workbench-panel">
          <div class="scroll-container">
            <!-- Card 01: Parties -->
            <div class="step-card" :class="{ completed: session.parties.length > 0 }">
              <div class="card-header">
                <div class="step-info">
                  <span class="card-step-num">01</span>
                  <span class="card-step-title">Parties & Interests</span>
                </div>
                <span class="badge" :class="session.parties.length > 0 ? 'success' : 'pending'">
                  {{ session.parties.length > 0 ? 'Loaded' : 'Waiting' }}
                </span>
              </div>
              <div class="card-content">
                <p class="api-note">GET /api/sessions/{{ sessionId }}</p>
                <div v-for="party in session.parties" :key="party.id" class="party-card">
                  <div class="party-header">
                    <span class="party-name" :style="{ color: store.partyColor(party.id) }">{{ party.name }}</span>
                    <span class="party-role">{{ party.role }}</span>
                  </div>
                </div>
              </div>
            </div>

            <!-- Card 02: Issues & Criteria -->
            <div class="step-card" :class="{ completed: session.issues.length > 0 }">
              <div class="card-header">
                <div class="step-info">
                  <span class="card-step-num">02</span>
                  <span class="card-step-title">Issues & Criteria</span>
                </div>
                <span class="badge" :class="session.issues.length > 0 ? 'success' : 'pending'">
                  {{ session.issues.length > 0 ? 'Loaded' : 'Waiting' }}
                </span>
              </div>
              <div class="card-content">
                <p class="api-note">GET /api/sessions/{{ sessionId }}</p>
                <div class="issues-list">
                  <div v-for="issue in session.issues" :key="issue.id" class="issue-row">
                    <span class="issue-name">{{ issue.name }}</span>
                    <span class="issue-type">{{ issue.type }}</span>
                    <span class="issue-range" v-if="issue.range">{{ issue.range[0] }}–{{ issue.range[1] }}</span>
                    <span class="issue-options" v-else-if="issue.options">{{ issue.options.join(' / ') }}</span>
                  </div>
                </div>
                <div v-if="session.criteria.length" class="criteria-section">
                  <span class="section-label">CRITERIA</span>
                  <div v-for="c in session.criteria" :key="c.name" class="criterion-row">
                    <span class="criterion-name">{{ c.name }}</span>
                    <span class="criterion-source">[{{ c.source }}]</span>
                  </div>
                </div>
              </div>
            </div>

            <!-- Card 03: Launch -->
            <div class="step-card active" v-if="!negotiationStarted">
              <div class="card-header">
                <div class="step-info">
                  <span class="card-step-num">03</span>
                  <span class="card-step-title">Start Negotiation</span>
                </div>
                <span class="badge accent">Ready</span>
              </div>
              <div class="card-content">
                <p class="api-note">WS /ws/{{ sessionId }}</p>
                <p class="description">
                  Connects WebSocket, generates satisfaction anchors, then begins the protocol sequence.
                </p>
                <button
                  class="action-btn"
                  :disabled="session.parties.length === 0"
                  @click="startNegotiation"
                >
                  Start Negotiation →
                </button>
              </div>
            </div>

            <!-- Setup Progress (after clicking Start) -->
            <SetupPanel
              v-if="negotiationStarted && session.isSetupPhase"
              :sessionId="sessionId"
              :parties="session.parties"
              :issues="session.issues"
              :anchorsStatus="session.anchorsStatus"
              :anchorsData="session.anchorsData"
            />
          </div>

          <!-- System Logs -->
          <div class="system-logs">
            <div class="log-header">
              <span class="log-title">SYSTEM DASHBOARD</span>
              <span class="log-id">{{ sessionId?.slice(0, 12) || 'NO_SESSION' }}</span>
            </div>
            <div class="log-content" ref="logContent">
              <div class="log-line" v-for="(log, idx) in session.logs" :key="idx">
                <span class="log-time">{{ log.time }}</span>
                <span class="log-msg">{{ log.message }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, provide, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { createSessionStore, SESSION_KEY } from '@/store/session'
import NegotiationGraph from '@/d3/NegotiationGraph.vue'
import SetupPanel from '@/components/chamber/SetupPanel.vue'

const props = defineProps({ sessionId: String })
const router = useRouter()

const store = createSessionStore()
provide(SESSION_KEY, store)

const { state: session } = store
const viewMode = ref('workbench')
const logContent = ref(null)

const leftPanelStyle = computed(() => {
  if (viewMode.value === 'graph') return { width: '100%', opacity: 1 }
  if (viewMode.value === 'workbench') return { width: '0%', opacity: 0 }
  return { width: '50%', opacity: 1 }
})

const rightPanelStyle = computed(() => {
  if (viewMode.value === 'workbench') return { width: '100%', opacity: 1 }
  if (viewMode.value === 'graph') return { width: '0%', opacity: 0 }
  return { width: '50%', opacity: 1 }
})

const statusClass = computed(() => {
  if (session.parties.length === 0) return 'loading'
  return 'ready'
})

const statusText = computed(() => {
  if (session.parties.length === 0) return 'Loading'
  return 'Ready'
})

const negotiationStarted = ref(false)

async function startNegotiation() {
  negotiationStarted.value = true
  store.connectWs(props.sessionId)
  await store.sendStart()
}

// Navigate to negotiate view once first move arrives (setup done)
watch(() => session.isSetupPhase, (isSetup) => {
  if (!isSetup && negotiationStarted.value) {
    router.push({ name: 'Negotiate', params: { sessionId: props.sessionId } })
  }
})

// Auto-scroll logs
watch(() => session.logs.length, () => {
  nextTick(() => {
    if (logContent.value) {
      logContent.value.scrollTop = logContent.value.scrollHeight
    }
  })
})

onMounted(() => {
  store.loadSession(props.sessionId)
})

onUnmounted(() => {
  // Only disconnect if we're NOT navigating to negotiate (which will take over the WS)
  // The WS will be recreated by NegotiateView anyway
})
</script>

<style scoped>
.main-view {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: #FFF;
  overflow: hidden;
  font-family: var(--font-heading);
}

/* Header */
.app-header {
  height: 60px;
  border-bottom: 1px solid var(--border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  background: #FFF;
  z-index: 100;
  position: relative;
}

.header-center {
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
}

.brand {
  font-family: var(--font-mono);
  font-weight: 800;
  font-size: 18px;
  letter-spacing: 1px;
  cursor: pointer;
}

.view-switcher {
  display: flex;
  background: #F5F5F5;
  padding: 4px;
  border-radius: 6px;
  gap: 4px;
}

.switch-btn {
  border: none;
  background: transparent;
  padding: 6px 16px;
  font-size: 12px;
  font-weight: 600;
  color: #666;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s;
}

.switch-btn.active {
  background: #FFF;
  color: #000;
  box-shadow: 0 2px 4px rgba(0,0,0,0.05);
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.workflow-step {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
}

.step-num {
  font-family: var(--font-mono);
  font-weight: 700;
  color: #999;
}

.step-name {
  font-weight: 700;
  color: #000;
}

.step-divider {
  width: 1px;
  height: 14px;
  background-color: #E0E0E0;
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: #666;
  font-weight: 500;
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #CCC;
}

.status-indicator.loading .dot { background: var(--accent); animation: pulse 1s infinite; }
.status-indicator.ready .dot { background: #4CAF50; }

@keyframes pulse { 50% { opacity: 0.5; } }

/* Content */
.content-area {
  flex: 1;
  display: flex;
  position: relative;
  overflow: hidden;
}

.panel-wrapper {
  height: 100%;
  overflow: hidden;
  transition: width 0.4s var(--ease-panel), opacity 0.3s ease;
  will-change: width, opacity;
}

.panel-wrapper.left {
  border-right: 1px solid var(--border);
}

/* Graph Placeholder */
.graph-placeholder {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: #FAFAFA;
  color: #CCC;
}

.placeholder-text {
  font-family: var(--font-mono);
  font-size: 1.2rem;
  font-weight: 700;
}

.placeholder-sub {
  font-family: var(--font-mono);
  font-size: 0.75rem;
  margin-top: 8px;
}

/* Workbench */
.workbench-panel {
  height: 100%;
  background: #FAFAFA;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.scroll-container {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* Step Cards */
.step-card {
  background: #FFF;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.04);
  border: 1px solid var(--border);
  transition: all 0.3s ease;
}

.step-card.active {
  border-color: var(--accent);
  box-shadow: 0 4px 12px rgba(255, 87, 34, 0.08);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.step-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.card-step-num {
  font-family: var(--font-mono);
  font-size: 20px;
  font-weight: 700;
  color: #E0E0E0;
}

.step-card.completed .card-step-num,
.step-card.active .card-step-num {
  color: #000;
}

.card-step-title {
  font-weight: 600;
  font-size: 14px;
  letter-spacing: 0.5px;
}

.badge {
  font-size: 10px;
  padding: 4px 8px;
  border-radius: 4px;
  font-weight: 600;
  text-transform: uppercase;
}

.badge.success { background: #E8F5E9; color: #2E7D32; }
.badge.accent { background: var(--accent); color: #FFF; }
.badge.pending { background: #F5F5F5; color: #999; }

.api-note {
  font-family: var(--font-mono);
  font-size: 10px;
  color: #999;
  margin-bottom: 12px;
}

.description {
  font-size: 12px;
  color: #666;
  line-height: 1.5;
  margin-bottom: 16px;
}

/* Party Cards */
.party-card {
  padding: 12px;
  border: 1px solid #EEE;
  margin-bottom: 8px;
  border-radius: 4px;
}

.party-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.party-name {
  font-weight: 600;
  font-size: 14px;
}

.party-role {
  font-family: var(--font-mono);
  font-size: 11px;
  color: #999;
}

/* Issues */
.issues-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 16px;
}

.issue-row {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 12px;
  padding: 8px;
  background: #F9F9F9;
  border-radius: 4px;
}

.issue-name {
  font-weight: 600;
  min-width: 120px;
}

.issue-type {
  font-family: var(--font-mono);
  font-size: 10px;
  color: #999;
  background: #F0F0F0;
  padding: 2px 6px;
  border-radius: 2px;
}

.issue-range, .issue-options {
  font-family: var(--font-mono);
  font-size: 11px;
  color: #666;
}

/* Criteria */
.criteria-section { margin-top: 12px; }

.section-label {
  display: block;
  font-size: 10px;
  color: #AAA;
  font-weight: 600;
  margin-bottom: 8px;
}

.criterion-row {
  display: flex;
  gap: 8px;
  font-size: 12px;
  margin-bottom: 4px;
}

.criterion-name { color: #333; }
.criterion-source {
  font-family: var(--font-mono);
  font-size: 10px;
  color: #999;
}

/* Action Button */
.action-btn {
  width: 100%;
  background: #000;
  color: #FFF;
  border: none;
  padding: 14px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: opacity 0.2s;
}

.action-btn:hover:not(:disabled) { opacity: 0.8; }
.action-btn:disabled { background: #CCC; cursor: not-allowed; }

/* System Logs */
.system-logs {
  background: #000;
  color: #DDD;
  padding: 16px;
  font-family: var(--font-mono);
  border-top: 1px solid #222;
  flex-shrink: 0;
}

.log-header {
  display: flex;
  justify-content: space-between;
  border-bottom: 1px solid #333;
  padding-bottom: 8px;
  margin-bottom: 8px;
  font-size: 10px;
  color: #888;
}

.log-content {
  display: flex;
  flex-direction: column;
  gap: 4px;
  height: 80px;
  overflow-y: auto;
  padding-right: 4px;
}

.log-content::-webkit-scrollbar { width: 4px; }
.log-content::-webkit-scrollbar-thumb { background: #333; border-radius: 2px; }

.log-line {
  font-size: 11px;
  display: flex;
  gap: 12px;
  line-height: 1.5;
}

.log-time { color: #666; min-width: 75px; }
.log-msg { color: #CCC; word-break: break-all; }
</style>
