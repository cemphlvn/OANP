<template>
  <div class="home-container">
    <!-- Top Navigation -->
    <nav class="navbar">
      <div class="nav-brand">OANP</div>
      <div class="nav-links">
        <a href="https://github.com" target="_blank" class="github-link">
          GitHub <span class="arrow">↗</span>
        </a>
      </div>
    </nav>

    <div class="main-content">
      <!-- Hero Section -->
      <section class="hero-section">
        <div class="hero-left">
          <div class="tag-row">
            <span class="orange-tag">AGENTIC NEGOTIATION PROTOCOL</span>
            <span class="version-text">/ v0.1</span>
          </div>

          <h1 class="main-title">
            Define any dispute.<br>
            <span class="gradient-text">Watch agents resolve it.</span>
          </h1>

          <div class="hero-desc">
            <p>
              Upload a scenario or describe one in natural language.
              <span class="highlight-bold">OANP</span> deploys autonomous agents grounded in
              <span class="highlight-orange">Harvard Negotiation Principles</span> to discover
              interests, generate options, and reach Pareto-superior agreements through
              <span class="highlight-code">"principled bargaining"</span>
            </p>
            <p class="slogan-text">
              Principled negotiation, at machine speed<span class="blinking-cursor">_</span>
            </p>
          </div>

          <div class="decoration-square"></div>
        </div>

        <div class="hero-right">
          <div class="logo-container">
            <div class="protocol-diagram">
              <div class="phase-ring">
                <span v-for="phase in visiblePhases" :key="phase" class="phase-node" :style="{ color: phaseColors[phase] }">
                  {{ phase }}
                </span>
              </div>
            </div>
          </div>
          <button class="scroll-down-btn" @click="scrollToBottom">↓</button>
        </div>
      </section>

      <!-- Dashboard Section -->
      <section class="dashboard-section">
        <!-- Left: Status & Steps -->
        <div class="left-panel">
          <div class="panel-header">
            <span class="status-dot">■</span> Protocol Engine
          </div>

          <h2 class="section-title">Ready to Negotiate</h2>
          <p class="section-desc">
            9-phase finite state machine with LLM-powered negotiator, mediator, and analyst agents
          </p>

          <div class="metrics-row">
            <div class="metric-card">
              <div class="metric-value">~2s</div>
              <div class="metric-label">Avg round latency</div>
            </div>
            <div class="metric-card">
              <div class="metric-value">9 Phase</div>
              <div class="metric-label">Harvard FSM Protocol</div>
            </div>
          </div>

          <div class="steps-container">
            <div class="steps-header">
              <span class="diamond-icon">◇</span> Protocol Sequence
            </div>
            <div class="workflow-list">
              <div class="workflow-item" v-for="(step, i) in workflowSteps" :key="i">
                <span class="step-num">{{ String(i + 1).padStart(2, '0') }}</span>
                <div class="step-info">
                  <div class="step-title">{{ step.title }}</div>
                  <div class="step-desc">{{ step.desc }}</div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Right: Console -->
        <div class="right-panel">
          <div class="console-box">
            <!-- Tab Switcher -->
            <div class="console-tabs">
              <button
                class="console-tab"
                :class="{ active: activeTab === 'demos' }"
                @click="switchTab('demos')"
                v-if="demos.length > 0"
              >
                <span class="tab-num">&#9654;</span> Watch Demo
              </button>
              <button
                class="console-tab"
                :class="{ active: activeTab === 'templates' }"
                @click="switchTab('templates')"
              >
                <span class="tab-num">01</span> Scenario Templates
              </button>
              <button
                class="console-tab"
                :class="{ active: activeTab === 'builder' }"
                @click="switchTab('builder')"
              >
                <span class="tab-num">02</span> Build with AI
                <span v-if="specMessages.length > 0" class="tab-badge">{{ specMessages.length }}</span>
              </button>
            </div>

            <!-- TAB 0: Watch Demo -->
            <div v-show="activeTab === 'demos'" class="tab-content">
              <div class="console-section">
                <div class="console-header">
                  <span class="console-label">PRE-RECORDED NEGOTIATIONS</span>
                  <span class="console-meta">No API key needed</span>
                </div>

                <!-- Step 1: Card Grid (when no demo selected) -->
                <template v-if="!selectedDemo">
                  <p class="demo-intro">
                    Watch real AI negotiations unfold in real-time. Click a scenario to see details.
                  </p>
                  <div class="demo-grid">
                    <div
                      v-for="demo in demos"
                      :key="demo.session_id"
                      class="demo-card"
                      @click="selectedDemo = demo"
                    >
                      <div class="demo-card-top">
                        <span class="demo-outcome-dot" :class="demo.outcome"></span>
                        <span class="demo-event-count">{{ demo.event_count }} events</span>
                      </div>
                      <h4 class="demo-name">{{ demo.scenario_name }}</h4>
                      <p class="demo-desc">{{ truncateText(demo.description, 80) }}</p>
                      <div class="demo-footer">
                        <div class="demo-parties-preview">
                          <span v-for="(p, i) in (demo.parties || []).slice(0, 2)" :key="i" class="demo-party-chip">
                            {{ typeof p === 'string' ? p : p.name }}
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                </template>

                <!-- Step 2: Expanded Detail (when demo selected) -->
                <template v-else>
                  <button class="demo-back" @click="selectedDemo = null">
                    &#8592; Back to all demos
                  </button>

                  <div class="demo-detail">
                    <div class="dd-header">
                      <div>
                        <span class="dd-outcome" :class="selectedDemo.outcome">{{ selectedDemo.outcome }}</span>
                        <h3 class="dd-title">{{ selectedDemo.scenario_name }}</h3>
                      </div>
                      <span class="dd-events">{{ selectedDemo.event_count }} events</span>
                    </div>

                    <p class="dd-description">{{ selectedDemo.description }}</p>

                    <!-- Parties -->
                    <div class="dd-section">
                      <span class="dd-section-label">PARTIES</span>
                      <div class="dd-parties">
                        <div v-for="(party, idx) in (selectedDemo.parties || [])" :key="idx" class="dd-party">
                          <span class="dd-party-dot" :style="{ background: PARTY_COLORS[idx] || '#999' }"></span>
                          <span class="dd-party-name">{{ typeof party === 'string' ? party : party.name }}</span>
                          <span class="dd-party-role" v-if="party.role">{{ party.role }}</span>
                        </div>
                      </div>
                    </div>

                    <!-- Issues -->
                    <div class="dd-section" v-if="selectedDemo.issues?.length">
                      <span class="dd-section-label">ISSUES ({{ selectedDemo.issues.length }})</span>
                      <div class="dd-issues">
                        <span v-for="issue in selectedDemo.issues" :key="issue.id || issue" class="dd-issue-tag">
                          {{ typeof issue === 'string' ? issue : issue.name }}
                        </span>
                      </div>
                    </div>

                    <!-- Criteria -->
                    <div class="dd-section" v-if="selectedDemo.criteria?.length">
                      <span class="dd-section-label">OBJECTIVE CRITERIA</span>
                      <div v-for="c in selectedDemo.criteria" :key="c.name" class="dd-criterion">
                        <span class="dd-crit-name">{{ c.name }}</span>
                        <span class="dd-crit-source">[{{ c.source }}]</span>
                      </div>
                    </div>

                    <!-- Launch -->
                    <button class="demo-launch-btn" @click="launchDemo(selectedDemo)">
                      <span>Watch Negotiation</span>
                      <span class="demo-launch-arrow">&#9654;</span>
                    </button>
                  </div>
                </template>
              </div>
            </div>

            <!-- TAB 1: Scenario Templates -->
            <div v-show="activeTab === 'templates'" class="tab-content">
              <div class="console-section">
                <div class="console-header">
                  <span class="console-label">AVAILABLE SCENARIOS</span>
                  <span class="console-meta">{{ scenarios.length }} templates</span>
                </div>

                <div v-if="loading" class="loading-placeholder">Loading scenarios...</div>

                <div class="scenario-grid">
                  <div
                    v-for="scenario in scenarios"
                    :key="scenario.file"
                    class="scenario-card"
                    :class="{ selected: selectedScenario?.file === scenario.file }"
                    @click="selectScenario(scenario)"
                  >
                    <div class="sc-header">
                      <span class="sc-name">{{ scenario.name }}</span>
                      <span class="sc-check" v-if="selectedScenario?.file === scenario.file">■</span>
                    </div>
                    <p class="sc-desc">{{ scenario.description }}</p>
                    <div class="sc-footer">
                      <span class="sc-stat">{{ scenario.parties }} parties</span>
                      <span class="sc-dot">·</span>
                      <span class="sc-stat">{{ scenario.issues }} issues</span>
                    </div>
                  </div>
                </div>
              </div>

              <!-- Launch from template -->
              <div class="console-section btn-section">
                <div v-if="launchError" class="launch-error">{{ launchError }}</div>
                <button
                  class="start-engine-btn"
                  @click="launch"
                  :disabled="!selectedScenario || launching"
                >
                  <span v-if="!launching">Launch Negotiation</span>
                  <span v-else>Initializing...</span>
                  <span class="btn-arrow">→</span>
                </button>
              </div>
            </div>

            <!-- TAB 2: AI Scenario Builder -->
            <div v-show="activeTab === 'builder'" class="tab-content">
              <div class="console-section">
                <div class="console-header">
                  <span class="console-label">>_ AGENTIC SCENARIO BUILDER</span>
                  <span class="console-meta" v-if="specSession">
                    Turn {{ specTurn }} · {{ (specConfidence * 100).toFixed(0) }}% confident
                  </span>
                </div>

                <!-- Introduction (before first message) -->
                <div v-if="specMessages.length === 0" class="builder-intro">
                  <p class="intro-text">
                    Describe any negotiation scenario in natural language. The AI agent will ask
                    clarifying questions to build a complete scenario with parties, interests,
                    BATNAs, issues, and objective criteria.
                  </p>
                  <div class="intro-examples">
                    <span class="intro-examples-label">EXAMPLES</span>
                    <div
                      v-for="ex in builderExamples"
                      :key="ex"
                      class="intro-example"
                      @click="prompt = ex"
                    >
                      "{{ ex }}"
                    </div>
                  </div>
                </div>

                <!-- Chat history -->
                <div v-if="specMessages.length > 0" class="spec-chat" ref="specChatRef">
                  <div
                    v-for="(msg, idx) in specMessages"
                    :key="idx"
                    class="spec-message"
                    :class="msg.role"
                  >
                    <div class="spec-msg-header">
                      <span class="spec-role">{{ msg.role === 'user' ? 'You' : 'OANP Agent' }}</span>
                    </div>
                    <div class="spec-msg-body">{{ msg.text }}</div>

                    <!-- Accumulated knowledge -->
                    <div v-if="msg.known && Object.keys(msg.known).length > 0" class="spec-known">
                      <span class="spec-known-label">UNDERSTOOD SO FAR</span>
                      <div v-for="(val, key) in msg.known" :key="key" class="spec-known-row">
                        <span class="spec-known-key">{{ key }}:</span>
                        <span class="spec-known-val">{{ formatKnownValue(val) }}</span>
                      </div>
                    </div>

                    <!-- Missing info -->
                    <div v-if="msg.missing?.length > 0" class="spec-missing">
                      <span class="spec-missing-label">STILL NEEDED</span>
                      <span v-for="m in msg.missing" :key="m" class="spec-missing-tag">{{ m }}</span>
                    </div>
                  </div>

                  <!-- Loading indicator -->
                  <div v-if="specLoading" class="spec-message assistant">
                    <div class="spec-thinking">
                      <span class="thinking-dot"></span>
                      <span class="thinking-dot"></span>
                      <span class="thinking-dot"></span>
                    </div>
                  </div>
                </div>

                <!-- Input -->
                <div class="input-wrapper" :class="{ 'has-chat': specMessages.length > 0 }">
                  <textarea
                    ref="specInputRef"
                    v-model="prompt"
                    class="code-input"
                    :placeholder="specMessages.length === 0
                      ? '// Describe a negotiation scenario...'
                      : '// Answer the question above...'"
                    :rows="specMessages.length === 0 ? 4 : 2"
                    :disabled="launching || specLoading || specReady"
                    @keydown.enter.meta.prevent="sendSpecify"
                    @keydown.enter.ctrl.prevent="sendSpecify"
                  ></textarea>
                  <div class="input-footer">
                    <span class="model-badge">{{ specSession ? `session: ${specSession.slice(0, 12)}` : 'Engine: OANP v0.1' }}</span>
                    <span class="input-hint" v-if="!specReady">⌘+Enter to send</span>
                  </div>
                </div>
              </div>

              <!-- Action Buttons -->
              <div class="console-section btn-section">
                <!-- Send button (during conversation) -->
                <button
                  v-if="!specReady"
                  class="start-engine-btn"
                  :class="{ secondary: specMessages.length > 0 }"
                  @click="sendSpecify"
                  :disabled="!prompt.trim() || specLoading"
                >
                  <span v-if="specLoading">Agent is thinking...</span>
                  <span v-else-if="specMessages.length === 0">Start Building</span>
                  <span v-else>Send Response</span>
                  <span class="btn-arrow">{{ specMessages.length === 0 ? '→' : '↵' }}</span>
                </button>

                <!-- Launch generated scenario -->
                <button
                  v-if="specReady"
                  class="start-engine-btn"
                  @click="launch"
                  :disabled="launching"
                >
                  <span v-if="!launching">Launch Generated Scenario</span>
                  <span v-else>Initializing...</span>
                  <span class="btn-arrow">→</span>
                </button>

                <!-- Reset -->
                <button
                  v-if="specMessages.length > 0"
                  class="reset-btn"
                  @click="resetBuilder"
                >
                  Reset conversation
                </button>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- History -->
      <section v-if="history.length > 0" class="history-section">
        <div class="section-header-line">
          <div class="section-line"></div>
          <span class="section-label-text">Past Sessions</span>
          <div class="section-line"></div>
        </div>
        <div class="history-grid">
          <div
            v-for="session in history"
            :key="session.session_id"
            class="history-card"
            @click="navigateToSession(session)"
          >
            <div class="hcard-header">
              <span class="hcard-id">{{ session.session_id?.slice(0, 8) }}</span>
              <span class="hcard-outcome" :class="session.outcome || 'running'">
                {{ session.outcome || 'running' }}
              </span>
            </div>
            <h3 class="hcard-title">{{ session.scenario_name || 'Custom Scenario' }}</h3>
            <div class="hcard-footer">
              <span class="hcard-parties">{{ session.party_count || '?' }} parties</span>
              <span class="hcard-date">{{ formatDate(session.created_at) }}</span>
            </div>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useAppStore } from '@/store/app'
import { createSession, generateScenario, specifyStep, getDemos } from '@/api/endpoints'
import { PHASE_COLORS, PARTY_COLORS } from '@/types/protocol'

const router = useRouter()
const { state: appState, loadScenarios, loadStats, loadHistory, addToHistory } = useAppStore()

const selectedScenario = ref(null)
const prompt = ref('')
const launching = ref(false)
const loading = ref(false)

// Specify (conversational scenario builder) state
const specSession = ref(null)
const specMessages = ref([])
const specLoading = ref(false)
const specTurn = ref(0)
const specConfidence = ref(0)
const specReady = ref(false)
const specNegotiationId = ref(null)
const specChatRef = ref(null)
const specInputRef = ref(null)
const activeTab = ref('templates')

const demos = ref([])
const selectedDemo = ref(null)
const scenarios = computed(() => appState.scenarios)
const history = computed(() => appState.history)
const phaseColors = PHASE_COLORS
const visiblePhases = ['discovery', 'generation', 'bargaining', 'convergence', 'settlement']

const canLaunch = computed(() => {
  return selectedScenario.value || specReady.value
})

const builderExamples = [
  'Two cofounders splitting equity after one wants to leave',
  'A landlord and tenant disagreeing over rent increase and lease terms',
  'A pharmaceutical company and a patient advocacy group negotiating drug pricing'
]

const workflowSteps = [
  { title: 'Scenario Setup', desc: 'Define parties, interests, BATNAs, issues, and objective criteria' },
  { title: 'Anchor Generation', desc: 'LLM grounds satisfaction scoring with concrete reference points' },
  { title: 'Discovery & Generation', desc: 'Agents exchange interests and propose initial options' },
  { title: 'Bargaining & Convergence', desc: 'Principled negotiation toward Pareto-superior agreement' },
  { title: 'Analysis', desc: 'Utility scores, Nash product, integrative index, automated critique' }
]

function switchTab(tab) {
  activeTab.value = tab
  if (tab === 'templates') {
    // Clear builder state doesn't reset — user can switch back
  }
}

function resetBuilder() {
  specMessages.value = []
  specSession.value = null
  specReady.value = false
  specNegotiationId.value = null
  specTurn.value = 0
  specConfidence.value = 0
  prompt.value = ''
}

function formatKnownValue(val) {
  if (val === null || val === undefined) return '—'
  if (Array.isArray(val)) return val.join(', ')
  if (typeof val === 'object') return JSON.stringify(val, null, 0)
  return String(val)
}

function selectScenario(scenario) {
  selectedScenario.value = selectedScenario.value?.file === scenario.file ? null : scenario
  if (selectedScenario.value) {
    prompt.value = ''
    // Clear specify state if switching to template
    specMessages.value = []
    specSession.value = null
    specReady.value = false
  }
}

async function sendSpecify() {
  const text = prompt.value.trim()
  if (!text || specLoading.value) return

  specLoading.value = true
  selectedScenario.value = null // Clear template selection

  // Add user message to chat
  specMessages.value.push({ role: 'user', text })
  prompt.value = ''

  try {
    const result = await specifyStep(specSession.value, text)

    specSession.value = result.session_id
    specTurn.value = result.turn || specTurn.value + 1
    specConfidence.value = result.confidence || 0

    if (result.type === 'question') {
      specMessages.value.push({
        role: 'assistant',
        text: result.question,
        known: result.known,
        missing: result.missing
      })
    } else if (result.type === 'ready') {
      specReady.value = true
      specNegotiationId.value = result.negotiation_session_id
      specMessages.value.push({
        role: 'assistant',
        text: 'Scenario is ready! I\'ve created a complete negotiation setup. Click "Launch Generated Scenario" to begin.',
        known: result.known
      })
    }
  } catch (err) {
    specMessages.value.push({
      role: 'assistant',
      text: `Error: ${err.message || 'Failed to process. Try again.'}`
    })
  } finally {
    specLoading.value = false
    // Auto-scroll chat
    nextTick(() => {
      if (specChatRef.value) {
        specChatRef.value.scrollTop = specChatRef.value.scrollHeight
      }
    })
  }
}

const launchError = ref('')

async function launch() {
  // Allow launch from either tab
  const hasTemplate = selectedScenario.value
  const hasGenerated = specReady.value && specNegotiationId.value

  if ((!hasTemplate && !hasGenerated) || launching.value) return

  launching.value = true
  launchError.value = ''

  try {
    let sessionId
    let scenarioName

    if (hasTemplate) {
      const data = await createSession(selectedScenario.value.file)
      if (data.error) {
        launchError.value = data.error
        return
      }
      sessionId = data.session_id
      scenarioName = selectedScenario.value.name
    } else if (hasGenerated) {
      sessionId = specNegotiationId.value
      scenarioName = 'Generated Scenario'
    }

    if (sessionId) {
      addToHistory({
        session_id: sessionId,
        scenario_name: scenarioName,
        created_at: new Date().toISOString(),
        outcome: null
      })
      router.push({ name: 'Session', params: { sessionId } })
    } else {
      launchError.value = 'No session ID returned from backend'
    }
  } catch (err) {
    console.error('Launch failed:', err)
    launchError.value = err.response?.data?.error || err.message || 'Failed to create session'
  } finally {
    launching.value = false
  }
}

function navigateToSession(session) {
  const route = session.outcome
    ? { name: 'Analysis', params: { sessionId: session.session_id } }
    : { name: 'Session', params: { sessionId: session.session_id } }
  router.push(route)
}

function formatDate(dateStr) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

function truncateText(text, max) {
  if (!text) return ''
  return text.length > max ? text.slice(0, max) + '...' : text
}

function launchDemo(demo) {
  router.push({ name: 'Negotiate', params: { sessionId: demo.session_id }, query: { demo: '1' } })
}

function scrollToBottom() {
  window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' })
}

onMounted(async () => {
  loading.value = true
  await Promise.all([loadScenarios(), loadStats()])
  loadHistory()
  // Load demos (non-blocking)
  getDemos().then(d => {
    demos.value = d || []
    if (d?.length > 0) activeTab.value = 'demos' // Auto-select demos tab if available
  }).catch(() => {})
  loading.value = false
})
</script>

<style scoped>
.home-container {
  min-height: 100vh;
  background: var(--white);
  font-family: var(--font-heading);
  color: var(--black);
}

/* Navbar */
.navbar {
  height: 60px;
  background: var(--black);
  color: var(--white);
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 40px;
}

.nav-brand {
  font-family: var(--font-mono);
  font-weight: 800;
  letter-spacing: 1px;
  font-size: 1.2rem;
}

.github-link {
  color: var(--white);
  font-family: var(--font-mono);
  font-size: 0.9rem;
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 8px;
  transition: opacity 0.2s;
}

.github-link:hover { opacity: 0.8; }

.arrow { font-family: sans-serif; }

/* Main Content */
.main-content {
  max-width: 1400px;
  margin: 0 auto;
  padding: 60px 40px;
}

/* Hero */
.hero-section {
  display: flex;
  justify-content: space-between;
  margin-bottom: 80px;
  position: relative;
}

.hero-left {
  flex: 1;
  padding-right: 60px;
}

.tag-row {
  display: flex;
  align-items: center;
  gap: 15px;
  margin-bottom: 25px;
  font-family: var(--font-mono);
  font-size: 0.8rem;
}

.orange-tag {
  background: var(--accent);
  color: var(--white);
  padding: 4px 10px;
  font-weight: 700;
  letter-spacing: 1px;
  font-size: 0.7rem;
}

.version-text {
  color: #999;
  font-weight: 500;
  letter-spacing: 0.5px;
}

.main-title {
  font-size: 4rem;
  line-height: 1.15;
  font-weight: 500;
  margin: 0 0 40px 0;
  letter-spacing: -2px;
  color: var(--black);
}

.gradient-text {
  background: linear-gradient(90deg, #000000 0%, #444444 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  display: inline-block;
}

.hero-desc {
  font-size: 1.05rem;
  line-height: 1.8;
  color: var(--gray-text);
  max-width: 640px;
  margin-bottom: 50px;
  font-weight: 400;
  text-align: justify;
}

.hero-desc p { margin-bottom: 1.5rem; }

.highlight-bold { color: var(--black); font-weight: 700; }
.highlight-orange { color: var(--accent); font-weight: 700; font-family: var(--font-mono); }

.highlight-code {
  background: rgba(0, 0, 0, 0.05);
  padding: 2px 6px;
  border-radius: 2px;
  font-family: var(--font-mono);
  font-size: 0.9em;
  color: var(--black);
  font-weight: 600;
}

.slogan-text {
  font-size: 1.2rem;
  font-weight: 520;
  color: var(--black);
  letter-spacing: 1px;
  border-left: 3px solid var(--accent);
  padding-left: 15px;
  margin-top: 20px;
}

.blinking-cursor {
  color: var(--accent);
  animation: blink 1s step-end infinite;
  font-weight: 700;
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}

.decoration-square {
  width: 16px;
  height: 16px;
  background: var(--accent);
}

.hero-right {
  flex: 0.6;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  align-items: flex-end;
}

.logo-container {
  width: 100%;
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 200px;
}

.protocol-diagram {
  display: flex;
  align-items: center;
  justify-content: center;
}

.phase-ring {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  justify-content: center;
  max-width: 300px;
}

.phase-node {
  font-family: var(--font-mono);
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 1px;
  padding: 6px 12px;
  border: 1px solid currentColor;
  opacity: 0.6;
}

.scroll-down-btn {
  width: 40px;
  height: 40px;
  border: 1px solid var(--border);
  background: transparent;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  color: var(--accent);
  font-size: 1.2rem;
  transition: all 0.2s;
}

.scroll-down-btn:hover { border-color: var(--accent); }

/* Dashboard */
.dashboard-section {
  display: flex;
  gap: 60px;
  border-top: 1px solid var(--border);
  padding-top: 60px;
  align-items: flex-start;
}

.left-panel { flex: 0.8; }
.right-panel { flex: 1.2; }

.panel-header {
  font-family: var(--font-mono);
  font-size: 0.8rem;
  color: #999;
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 20px;
}

.status-dot { color: var(--accent); font-size: 0.8rem; }

.section-title {
  font-size: 2rem;
  font-weight: 520;
  margin: 0 0 15px 0;
}

.section-desc {
  color: var(--gray-text);
  margin-bottom: 25px;
  line-height: 1.6;
}

.metrics-row {
  display: flex;
  gap: 20px;
  margin-bottom: 15px;
}

.metric-card {
  border: 1px solid var(--border);
  padding: 20px 30px;
  min-width: 150px;
}

.metric-value {
  font-family: var(--font-mono);
  font-size: 1.8rem;
  font-weight: 520;
  margin-bottom: 5px;
}

.metric-label {
  font-size: 0.85rem;
  color: #999;
}

/* Steps */
.steps-container {
  border: 1px solid var(--border);
  padding: 30px;
}

.steps-header {
  font-family: var(--font-mono);
  font-size: 0.8rem;
  color: #999;
  margin-bottom: 25px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.diamond-icon { font-size: 1.2rem; line-height: 1; }

.workflow-list {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.workflow-item {
  display: flex;
  align-items: flex-start;
  gap: 20px;
}

.step-num {
  font-family: var(--font-mono);
  font-weight: 700;
  color: var(--black);
  opacity: 0.3;
}

.step-title {
  font-weight: 520;
  font-size: 1rem;
  margin-bottom: 4px;
}

.step-desc {
  font-size: 0.85rem;
  color: var(--gray-text);
}

/* Console */
.console-box {
  border: 1px solid #CCC;
  padding: 0;
}

/* Tabs */
.console-tabs {
  display: flex;
  border-bottom: 1px solid #EEE;
}

.console-tab {
  flex: 1;
  padding: 14px 20px;
  border: none;
  background: #FAFAFA;
  font-family: var(--font-mono);
  font-size: 0.8rem;
  font-weight: 600;
  color: #999;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  gap: 8px;
  justify-content: center;
}

.console-tab:first-child { border-right: 1px solid #EEE; }

.console-tab.active {
  background: #FFF;
  color: var(--black);
}

.console-tab:hover:not(.active) { color: #666; }

.tab-num {
  font-weight: 700;
  opacity: 0.3;
}

.console-tab.active .tab-num { opacity: 1; }

.tab-badge {
  font-size: 0.6rem;
  background: var(--accent);
  color: #FFF;
  padding: 1px 5px;
  border-radius: 8px;
  font-weight: 700;
}

.tab-content { padding: 0; }

.console-section { padding: 20px; }
.console-section.btn-section { padding-top: 0; }

.console-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 15px;
  font-family: var(--font-mono);
  font-size: 0.75rem;
  color: #666;
}

/* Scenario Cards Grid */
.loading-placeholder {
  padding: 20px;
  text-align: center;
  font-family: var(--font-mono);
  font-size: 0.85rem;
  color: #999;
}

.scenario-grid {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 420px;
  overflow-y: auto;
}

.scenario-grid::-webkit-scrollbar { width: 4px; }
.scenario-grid::-webkit-scrollbar-thumb { background: #CCC; border-radius: 2px; }

.scenario-card {
  border: 1px solid #EEE;
  padding: 14px 16px;
  cursor: pointer;
  transition: all 0.15s;
  background: #FAFAFA;
}

.scenario-card:hover {
  border-color: #CCC;
  background: #F5F5F5;
}

.scenario-card.selected {
  border-color: var(--black);
  background: var(--black);
  color: var(--white);
}

.sc-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}

.sc-name {
  font-weight: 600;
  font-size: 0.9rem;
}

.sc-check {
  color: var(--accent);
  font-size: 0.8rem;
}

.scenario-card.selected .sc-check { color: var(--white); }

.sc-desc {
  font-size: 0.8rem;
  color: #888;
  line-height: 1.5;
  margin-bottom: 8px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.scenario-card.selected .sc-desc { color: #AAA; }

.sc-footer {
  display: flex;
  align-items: center;
  gap: 6px;
  font-family: var(--font-mono);
  font-size: 0.7rem;
  color: #AAA;
}

.scenario-card.selected .sc-footer { color: #888; }

.sc-dot { opacity: 0.4; }

/* Demo section */
.demo-intro {
  font-size: 0.85rem;
  color: var(--gray-text);
  line-height: 1.6;
  margin-bottom: 16px;
}

.demo-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  max-height: 420px;
  overflow-y: auto;
}

.demo-grid::-webkit-scrollbar { width: 4px; }
.demo-grid::-webkit-scrollbar-thumb { background: #CCC; border-radius: 2px; }

.demo-card {
  border: 1px solid #EEE;
  padding: 14px 16px;
  cursor: pointer;
  transition: all 0.2s;
  background: #FAFAFA;
  border-radius: 6px;
  display: flex;
  flex-direction: column;
}

.demo-card:hover {
  border-color: var(--accent);
  background: #FFF;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.04);
}

.demo-card-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.demo-outcome-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.demo-outcome-dot.agreement { background: #22c55e; }
.demo-outcome-dot.impasse { background: #ef4444; }

.demo-event-count {
  font-family: var(--font-mono);
  font-size: 0.65rem;
  color: #BBB;
}

.demo-name {
  font-weight: 600;
  font-size: 0.85rem;
  margin: 0 0 6px 0;
  line-height: 1.3;
}

.demo-desc {
  font-size: 0.75rem;
  color: #999;
  line-height: 1.4;
  flex: 1;
  margin-bottom: 10px;
}

.demo-footer { margin-top: auto; }

.demo-parties-preview {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.demo-party-chip {
  font-family: var(--font-mono);
  font-size: 0.6rem;
  padding: 2px 6px;
  background: #F0F0F0;
  border-radius: 3px;
  color: #777;
}

/* Demo detail (step 2) */
.demo-back {
  background: none;
  border: none;
  cursor: pointer;
  font-family: var(--font-mono);
  font-size: 0.8rem;
  color: #999;
  padding: 0;
  margin-bottom: 16px;
  transition: color 0.15s;
}

.demo-back:hover { color: var(--accent); }

.demo-detail {
  animation: dd-fade-in 0.2s ease-out;
}

@keyframes dd-fade-in {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

.dd-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 16px;
}

.dd-outcome {
  font-family: var(--font-mono);
  font-size: 0.65rem;
  font-weight: 700;
  text-transform: uppercase;
  padding: 2px 8px;
  border-radius: 3px;
  display: inline-block;
  margin-bottom: 6px;
}

.dd-outcome.agreement { background: #E8F5E9; color: #2E7D32; }
.dd-outcome.impasse { background: #FFEBEE; color: #C62828; }

.dd-title {
  font-size: 1.1rem;
  font-weight: 700;
  margin: 0;
  line-height: 1.3;
}

.dd-events {
  font-family: var(--font-mono);
  font-size: 0.75rem;
  color: #BBB;
  white-space: nowrap;
}

.dd-description {
  font-size: 0.85rem;
  color: var(--gray-text);
  line-height: 1.7;
  margin-bottom: 20px;
}

.dd-section {
  margin-bottom: 16px;
}

.dd-section-label {
  display: block;
  font-family: var(--font-mono);
  font-size: 0.6rem;
  font-weight: 700;
  color: #BBB;
  letter-spacing: 1px;
  margin-bottom: 8px;
}

.dd-parties {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.dd-party {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.85rem;
}

.dd-party-dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
.dd-party-name { font-weight: 600; }
.dd-party-role { font-family: var(--font-mono); font-size: 0.7rem; color: #999; }

.dd-issues {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.dd-issue-tag {
  font-family: var(--font-mono);
  font-size: 0.7rem;
  padding: 4px 10px;
  background: #F5F5F5;
  border: 1px solid #EEE;
  border-radius: 4px;
  color: #555;
}

.dd-criterion {
  display: flex;
  gap: 8px;
  font-size: 0.8rem;
  margin-bottom: 4px;
}

.dd-crit-name { color: #444; }
.dd-crit-source { font-family: var(--font-mono); font-size: 0.65rem; color: #BBB; }

.demo-launch-btn {
  width: 100%;
  background: var(--black);
  color: var(--white);
  border: none;
  padding: 16px 20px;
  font-family: var(--font-mono);
  font-weight: 700;
  font-size: 1rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
  border-radius: 4px;
  margin-top: 20px;
  transition: all 0.2s;
  letter-spacing: 0.5px;
}

.demo-launch-btn:hover { background: var(--accent); }

.demo-launch-arrow { font-size: 0.9rem; }

/* Builder Intro */
.builder-intro {
  margin-bottom: 16px;
}

.intro-text {
  font-size: 0.85rem;
  color: var(--gray-text);
  line-height: 1.6;
  margin-bottom: 16px;
}

.intro-examples {
  border: 1px solid #EEE;
  background: #FAFAFA;
  padding: 12px;
}

.intro-examples-label {
  display: block;
  font-family: var(--font-mono);
  font-size: 0.65rem;
  font-weight: 600;
  color: #AAA;
  letter-spacing: 1px;
  margin-bottom: 10px;
}

.intro-example {
  font-size: 0.8rem;
  color: #555;
  padding: 8px 10px;
  cursor: pointer;
  border-left: 2px solid transparent;
  transition: all 0.15s;
  font-style: italic;
  margin-bottom: 4px;
}

.intro-example:hover {
  background: #F0F0F0;
  border-left-color: var(--accent);
  color: var(--black);
}

/* Input */
.input-wrapper {
  border: 1px solid #DDD;
  background: #FAFAFA;
}

.input-wrapper.has-chat {
  border-top: none;
}

.code-input {
  width: 100%;
  border: none;
  background: transparent;
  padding: 16px 20px;
  font-family: var(--font-mono);
  font-size: 0.85rem;
  line-height: 1.6;
  resize: none;
  outline: none;
  min-height: 60px;
}

.input-footer {
  display: flex;
  justify-content: space-between;
  padding: 0 16px 8px;
}

.model-badge {
  font-family: var(--font-mono);
  font-size: 0.65rem;
  color: #BBB;
}

.input-hint {
  font-family: var(--font-mono);
  font-size: 0.65rem;
  color: #CCC;
}

/* Launch error */
.launch-error {
  font-family: var(--font-mono);
  font-size: 0.75rem;
  color: #C62828;
  background: #FFEBEE;
  padding: 8px 12px;
  border-radius: 4px;
  margin-bottom: 8px;
}

/* Reset button */
.reset-btn {
  width: 100%;
  background: transparent;
  color: #999;
  border: none;
  padding: 10px;
  font-family: var(--font-mono);
  font-size: 0.75rem;
  cursor: pointer;
  margin-top: 6px;
  transition: color 0.15s;
}

.reset-btn:hover { color: var(--accent); }

/* Launch Button */
.start-engine-btn {
  width: 100%;
  background: var(--black);
  color: var(--white);
  border: none;
  padding: 20px;
  font-family: var(--font-mono);
  font-weight: 700;
  font-size: 1.1rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
  transition: all 0.3s ease;
  letter-spacing: 1px;
  overflow: hidden;
}

.start-engine-btn:not(:disabled) {
  animation: pulse-border 2s infinite;
}

.start-engine-btn:hover:not(:disabled) {
  background: var(--accent);
  transform: translateY(-2px);
}

.start-engine-btn:active:not(:disabled) {
  transform: translateY(0);
}

.start-engine-btn:disabled {
  background: #E5E5E5;
  color: #999;
  cursor: not-allowed;
}

@keyframes pulse-border {
  0% { box-shadow: 0 0 0 0 rgba(0, 0, 0, 0.2); }
  70% { box-shadow: 0 0 0 6px rgba(0, 0, 0, 0); }
  100% { box-shadow: 0 0 0 0 rgba(0, 0, 0, 0); }
}

/* History */
.history-section {
  margin-top: 80px;
}

.section-header-line {
  display: flex;
  align-items: center;
  gap: 20px;
  margin-bottom: 30px;
}

.section-line {
  flex: 1;
  height: 1px;
  background: var(--border);
}

.section-label-text {
  font-family: var(--font-mono);
  font-size: 0.85rem;
  color: #999;
  letter-spacing: 1px;
}

.history-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 20px;
}

.history-card {
  border: 1px solid var(--border);
  padding: 20px;
  cursor: pointer;
  transition: all 0.2s;
}

.history-card:hover {
  border-color: #CCC;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.04);
}

.hcard-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.hcard-id {
  font-family: var(--font-mono);
  font-size: 0.75rem;
  color: #999;
}

.hcard-outcome {
  font-family: var(--font-mono);
  font-size: 0.65rem;
  font-weight: 600;
  text-transform: uppercase;
  padding: 2px 8px;
  border-radius: 2px;
}

.hcard-outcome.agreement { background: #E8F5E9; color: #2E7D32; }
.hcard-outcome.impasse { background: #FFEBEE; color: #C62828; }
.hcard-outcome.running { background: #FFF3E0; color: #E65100; }

.hcard-title {
  font-size: 1rem;
  font-weight: 520;
  margin-bottom: 12px;
}

.hcard-footer {
  display: flex;
  justify-content: space-between;
  font-size: 0.8rem;
  color: #999;
}

/* Thinking dots */
.spec-thinking {
  display: flex;
  gap: 4px;
  padding: 4px 0;
}

.thinking-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #CCC;
  animation: spec-think 1.4s infinite ease-in-out both;
}

.thinking-dot:nth-child(1) { animation-delay: 0s; }
.thinking-dot:nth-child(2) { animation-delay: 0.2s; }
.thinking-dot:nth-child(3) { animation-delay: 0.4s; }

@keyframes spec-think {
  0%, 80%, 100% { transform: scale(0.6); opacity: 0.4; }
  40% { transform: scale(1); opacity: 1; }
}

/* Specify Chat */
.spec-chat {
  max-height: 280px;
  overflow-y: auto;
  border: 1px solid #EEE;
  background: #FAFAFA;
  margin-bottom: 12px;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.spec-chat::-webkit-scrollbar { width: 4px; }
.spec-chat::-webkit-scrollbar-thumb { background: #CCC; border-radius: 2px; }

.spec-message {
  padding: 10px 12px;
  border-radius: 6px;
  font-size: 0.85rem;
  line-height: 1.6;
}

.spec-message.user {
  background: var(--black);
  color: var(--white);
  margin-left: 40px;
}

.spec-message.assistant {
  background: #FFF;
  border: 1px solid #EEE;
  margin-right: 40px;
}

.spec-msg-header {
  margin-bottom: 4px;
}

.spec-role {
  font-family: var(--font-mono);
  font-size: 0.7rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  opacity: 0.6;
}

.spec-msg-body {
  white-space: pre-wrap;
}

.spec-known {
  margin-top: 10px;
  padding-top: 8px;
  border-top: 1px dashed #EEE;
}

.spec-known-label, .spec-missing-label {
  display: block;
  font-family: var(--font-mono);
  font-size: 0.65rem;
  font-weight: 600;
  color: #999;
  margin-bottom: 6px;
  letter-spacing: 1px;
}

.spec-known-row {
  font-size: 0.75rem;
  display: flex;
  gap: 6px;
  margin-bottom: 2px;
}

.spec-known-key {
  font-family: var(--font-mono);
  color: #666;
  font-weight: 600;
}

.spec-known-val {
  color: #333;
  word-break: break-word;
}

.spec-missing {
  margin-top: 8px;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.spec-missing-tag {
  font-family: var(--font-mono);
  font-size: 0.7rem;
  padding: 2px 8px;
  background: #FFF3E0;
  color: #E65100;
  border-radius: 3px;
}

/* Button row */
.btn-row {
  margin-bottom: 8px;
}

.start-engine-btn.secondary {
  background: #FFF;
  color: var(--black);
  border: 2px solid var(--black);
}

.start-engine-btn.secondary:hover:not(:disabled) {
  background: #F5F5F5;
  transform: translateY(-1px);
}

.describe-btn {
  width: 100%;
  background: transparent;
  color: var(--gray-text);
  border: 1px dashed #CCC;
  padding: 12px;
  font-family: var(--font-mono);
  font-size: 0.85rem;
  cursor: pointer;
  margin-top: 8px;
  transition: all 0.2s;
}

.describe-btn:hover:not(:disabled) {
  border-color: var(--accent);
  color: var(--accent);
}

.describe-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Responsive */
@media (max-width: 1024px) {
  .dashboard-section { flex-direction: column; }
  .hero-section { flex-direction: column; }
  .hero-left { padding-right: 0; margin-bottom: 40px; }
}
</style>
