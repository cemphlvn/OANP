<template>
  <div class="analysis-view">
    <!-- Status Strip -->
    <StatusStrip
      :phase="metrics?.outcome === 'agreement' ? 'settlement' : metrics?.outcome === 'impasse' ? 'impasse' : 'setup'"
      :round="metrics?.total_rounds || 0"
      :moveCount="metrics?.total_moves || 0"
      :resolvedCount="metrics?.agreement ? Object.keys(metrics.agreement.issue_values || {}).length : 0"
      :totalIssues="issues.length"
      :convergence="metrics?.outcome === 'agreement' ? 100 : 0"
      :outcome="metrics?.outcome"
    >
      <div class="analysis-nav">
        <button class="an-btn" :class="{ active: tab === 'report' }" @click="tab = 'report'">Report</button>
        <button class="an-btn" :class="{ active: tab === 'timeline' }" @click="tab = 'timeline'">Timeline</button>
      </div>
    </StatusStrip>

    <!-- Main content -->
    <div class="an-main">
      <!-- Loading -->
      <div v-if="!metrics && !loadError" class="an-loading">
        <div class="an-loading-spinner"></div>
        <span>Loading analysis...</span>
      </div>

      <!-- Error -->
      <div v-else-if="loadError" class="an-error">
        <span class="an-error-title">Failed to load analysis</span>
        <span class="an-error-msg">{{ loadError }}</span>
        <button class="an-retry" @click="loadData">Retry</button>
      </div>

      <!-- Report Tab -->
      <div v-else-if="tab === 'report'" class="an-report">
        <!-- Outcome Header -->
        <div class="an-outcome-bar" :class="metrics.outcome">
          <span class="an-outcome-badge">{{ metrics.outcome === 'agreement' ? 'Agreement Reached' : 'Impasse' }}</span>
          <span class="an-outcome-stats">{{ metrics.total_rounds }} rounds · {{ metrics.total_moves }} moves · {{ (metrics.disclosure_rate * 100).toFixed(0) }}% disclosed</span>
        </div>

        <div class="an-grid">
          <!-- Left: Agreement + Utilities -->
          <div class="an-col">
            <!-- Agreement Terms -->
            <div v-if="metrics.agreement" class="an-card">
              <div class="an-card-title">Final Agreement</div>
              <div class="an-terms">
                <div v-for="(val, key) in metrics.agreement.issue_values" :key="key" class="an-term">
                  <span class="an-term-key">{{ key }}</span>
                  <span class="an-term-val">{{ val }}</span>
                </div>
              </div>
            </div>

            <!-- Party Utilities -->
            <div class="an-card">
              <div class="an-card-title">Party Utilities</div>
              <div v-for="(util, partyId) in metrics.party_utilities" :key="partyId" class="an-util-row">
                <div class="an-util-header">
                  <span class="an-util-dot" :style="{ background: getPartyColor(partyId) }"></span>
                  <span class="an-util-name">{{ partyNames[partyId] || partyId }}</span>
                  <span class="an-util-score">{{ util.toFixed(2) }}</span>
                </div>
                <div class="an-util-bar-wrap">
                  <div class="an-util-bar" :style="{ width: (util * 100) + '%', background: getPartyColor(partyId) }"></div>
                </div>
                <div class="an-util-meta" v-if="metrics.party_batna_surplus?.[partyId] != null">
                  BATNA surplus: <strong>+{{ metrics.party_batna_surplus[partyId].toFixed(2) }}</strong>
                </div>
              </div>
            </div>
          </div>

          <!-- Right: Metrics + Process + Critique -->
          <div class="an-col">
            <!-- Efficiency Metrics -->
            <div class="an-card">
              <div class="an-card-title">Efficiency Metrics</div>
              <div class="an-metrics-grid">
                <div class="an-metric">
                  <span class="an-metric-val">{{ metrics.social_welfare?.toFixed(2) }}</span>
                  <span class="an-metric-lbl">Social Welfare</span>
                </div>
                <div class="an-metric">
                  <span class="an-metric-val">{{ metrics.nash_product?.toFixed(3) }}</span>
                  <span class="an-metric-lbl">Nash Product</span>
                </div>
                <div class="an-metric">
                  <span class="an-metric-val">{{ metrics.integrative_index?.toFixed(2) }}</span>
                  <span class="an-metric-lbl">Integrative Index</span>
                </div>
                <div class="an-metric">
                  <span class="an-metric-val" :class="metrics.pareto_efficient ? 'yes' : 'no'">{{ metrics.pareto_efficient ? 'Yes' : 'No' }}</span>
                  <span class="an-metric-lbl">Pareto Efficient</span>
                </div>
              </div>
            </div>

            <!-- Move Breakdown -->
            <div class="an-card">
              <div class="an-card-title">Move Breakdown</div>
              <div class="an-breakdown">
                <div v-for="(count, moveType) in metrics.move_breakdown" :key="moveType" class="an-bd-row">
                  <span class="an-bd-badge" :style="{ background: MOVE_COLORS[moveType] || '#999' }">{{ MOVE_LABELS[moveType] || moveType }}</span>
                  <span class="an-bd-bar-wrap">
                    <span class="an-bd-bar" :style="{ width: (count / metrics.total_moves * 100) + '%', background: MOVE_COLORS[moveType] || '#999' }"></span>
                  </span>
                  <span class="an-bd-count">{{ count }}</span>
                </div>
              </div>
              <div v-if="metrics.phases_visited?.length" class="an-phases">
                <span class="an-phases-label">PHASES VISITED</span>
                <div class="an-phase-tags">
                  <span v-for="p in metrics.phases_visited" :key="p" class="an-phase-tag" :style="{ borderColor: PHASE_COLORS[p], color: PHASE_COLORS[p] }">{{ p }}</span>
                </div>
              </div>
            </div>

            <!-- Critique -->
            <div v-if="metrics.critique?.length" class="an-card">
              <div class="an-card-title">Critique</div>
              <div v-for="(issue, idx) in metrics.critique" :key="idx" class="an-critique-item">
                <span class="an-crit-badge" :class="issue.severity">{{ issue.severity }}</span>
                <span class="an-crit-desc">{{ issue.description }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Navigate to Explore -->
        <div class="an-footer">
          <button class="an-explore-btn" @click="$router.push({ name: 'Negotiate', params: { sessionId } })">
            ← Back to Negotiation
          </button>
        </div>
      </div>

      <!-- Timeline Tab -->
      <TimelineView
        v-else-if="tab === 'timeline'"
        :moves="moves"
        :parties="parties"
        :showAllReasoning="true"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { getSession, getAnalysis, getMoves } from '@/api/endpoints'
import { PHASE_COLORS, MOVE_LABELS, MOVE_COLORS, PARTY_COLORS } from '@/types/protocol'
import StatusStrip from '@/components/chamber/StatusStrip.vue'
import TimelineView from '@/components/chamber/TimelineView.vue'

const props = defineProps({ sessionId: String })

const tab = ref('report')
const metrics = ref(null)
const parties = ref([])
const issues = ref([])
const moves = ref([])
const loadError = ref(null)

const partyNames = computed(() => {
  const map = {}
  parties.value.forEach(p => { map[p.id] = p.name })
  return map
})

function getPartyColor(partyId) {
  const idx = parties.value.findIndex(p => p.id === partyId)
  return idx >= 0 ? PARTY_COLORS[idx] : '#999'
}

async function loadData() {
  loadError.value = null
  try {
    const [sessionData, analysisData, movesData] = await Promise.all([
      getSession(props.sessionId),
      getAnalysis(props.sessionId),
      getMoves(props.sessionId)
    ])
    if (sessionData.error) throw new Error(sessionData.error)
    if (analysisData.error) throw new Error(analysisData.error)

    parties.value = sessionData.parties || []
    issues.value = sessionData.issues || []
    moves.value = movesData?.moves || sessionData.move_history || []
    metrics.value = analysisData
  } catch (err) {
    console.error('Failed to load analysis:', err)
    loadError.value = err.message || 'Unknown error'
  }
}

onMounted(loadData)
</script>

<style scoped>
.analysis-view {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: #FFF;
  overflow: hidden;
  font-family: var(--font-heading);
}

.an-main {
  flex: 1;
  overflow-y: auto;
}

/* Nav tabs in StatusStrip */
.analysis-nav {
  display: flex;
  background: #F5F5F5;
  padding: 3px;
  border-radius: 6px;
  gap: 3px;
}

.an-btn {
  border: none;
  background: transparent;
  padding: 5px 14px;
  font-size: 11px;
  font-weight: 600;
  color: #999;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.15s;
}

.an-btn.active {
  background: #FFF;
  color: #000;
  box-shadow: 0 1px 3px rgba(0,0,0,0.08);
}

/* Loading */
.an-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 300px;
  gap: 16px;
  color: #999;
  font-family: var(--font-mono);
  font-size: 13px;
}

.an-loading-spinner {
  width: 24px;
  height: 24px;
  border: 3px solid #EEE;
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: an-spin 0.8s linear infinite;
}

@keyframes an-spin { to { transform: rotate(360deg); } }

/* Error */
.an-error {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 300px;
  gap: 12px;
}

.an-error-title { font-weight: 600; color: #C62828; }
.an-error-msg { font-family: var(--font-mono); font-size: 12px; color: #999; }

.an-retry {
  background: #000;
  color: #FFF;
  border: none;
  padding: 8px 20px;
  font-family: var(--font-mono);
  font-size: 12px;
  cursor: pointer;
  border-radius: 4px;
}

.an-retry:hover { background: var(--accent); }

/* Report */
.an-report {
  padding: 24px;
  max-width: 1100px;
  margin: 0 auto;
}

/* Outcome Bar */
.an-outcome-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-radius: 8px;
  margin-bottom: 24px;
}

.an-outcome-bar.agreement { background: #F0FDF4; border: 1px solid #BBF7D0; }
.an-outcome-bar.impasse { background: #FEF2F2; border: 1px solid #FECACA; }

.an-outcome-badge {
  font-family: var(--font-mono);
  font-size: 13px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.an-outcome-bar.agreement .an-outcome-badge { color: #166534; }
.an-outcome-bar.impasse .an-outcome-badge { color: #991B1B; }

.an-outcome-stats {
  font-family: var(--font-mono);
  font-size: 11px;
  color: #888;
}

/* Grid */
.an-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}

@media (max-width: 800px) {
  .an-grid { grid-template-columns: 1fr; }
}

.an-col {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* Cards */
.an-card {
  background: #FFF;
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 20px;
}

.an-card-title {
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: 700;
  color: #999;
  text-transform: uppercase;
  letter-spacing: 1px;
  margin-bottom: 16px;
}

/* Agreement Terms */
.an-terms { }

.an-term {
  display: flex;
  justify-content: space-between;
  padding: 8px 0;
  border-bottom: 1px solid #F0F0F0;
  font-size: 13px;
}

.an-term:last-child { border-bottom: none; }
.an-term-key { color: #666; }
.an-term-val { font-family: var(--font-mono); font-weight: 600; }

/* Utility */
.an-util-row {
  margin-bottom: 16px;
}

.an-util-row:last-child { margin-bottom: 0; }

.an-util-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.an-util-dot { width: 10px; height: 10px; border-radius: 50%; }
.an-util-name { font-weight: 600; font-size: 13px; flex: 1; }
.an-util-score { font-family: var(--font-mono); font-size: 18px; font-weight: 700; }

.an-util-bar-wrap {
  height: 6px;
  background: #F0F0F0;
  border-radius: 3px;
  overflow: hidden;
  margin-bottom: 4px;
}

.an-util-bar {
  height: 100%;
  border-radius: 3px;
  transition: width 0.6s ease;
}

.an-util-meta {
  font-family: var(--font-mono);
  font-size: 10px;
  color: #999;
}

.an-util-meta strong { color: #22c55e; }

/* Metrics Grid */
.an-metrics-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.an-metric {
  text-align: center;
  padding: 14px;
  background: #F9F9F9;
  border-radius: 6px;
}

.an-metric-val {
  display: block;
  font-family: var(--font-mono);
  font-size: 20px;
  font-weight: 700;
  margin-bottom: 4px;
}

.an-metric-val.yes { color: #22c55e; }
.an-metric-val.no { color: #ef4444; }

.an-metric-lbl {
  font-size: 9px;
  color: #999;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

/* Move Breakdown */
.an-breakdown { margin-bottom: 12px; }

.an-bd-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 6px;
}

.an-bd-badge {
  font-family: var(--font-mono);
  font-size: 8px;
  font-weight: 700;
  color: #FFF;
  padding: 2px 6px;
  border-radius: 3px;
  min-width: 70px;
  text-align: center;
  text-transform: uppercase;
}

.an-bd-bar-wrap {
  flex: 1;
  height: 4px;
  background: #F0F0F0;
  border-radius: 2px;
  overflow: hidden;
}

.an-bd-bar {
  height: 100%;
  border-radius: 2px;
}

.an-bd-count {
  font-family: var(--font-mono);
  font-size: 12px;
  font-weight: 600;
  min-width: 20px;
  text-align: right;
}

/* Phases */
.an-phases { margin-top: 12px; }

.an-phases-label {
  font-family: var(--font-mono);
  font-size: 9px;
  font-weight: 700;
  color: #BBB;
  letter-spacing: 1px;
  margin-bottom: 8px;
  display: block;
}

.an-phase-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.an-phase-tag {
  font-family: var(--font-mono);
  font-size: 9px;
  font-weight: 600;
  padding: 3px 8px;
  border: 1px solid;
  border-radius: 3px;
  text-transform: uppercase;
}

/* Critique */
.an-critique-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 8px 0;
  border-bottom: 1px solid #F5F5F5;
  font-size: 12px;
}

.an-critique-item:last-child { border-bottom: none; }

.an-crit-badge {
  font-family: var(--font-mono);
  font-size: 8px;
  font-weight: 700;
  text-transform: uppercase;
  padding: 2px 6px;
  border-radius: 2px;
  min-width: 40px;
  text-align: center;
  flex-shrink: 0;
}

.an-crit-badge.high { background: #FFEBEE; color: #C62828; }
.an-crit-badge.medium { background: #FFF3E0; color: #E65100; }
.an-crit-badge.low { background: #F5F5F5; color: #666; }
.an-crit-badge.info { background: #E3F2FD; color: #1565C0; }

.an-crit-desc { color: #444; line-height: 1.5; }

/* Footer */
.an-footer {
  margin-top: 24px;
  padding-top: 20px;
  border-top: 1px solid var(--border);
  display: flex;
  gap: 12px;
}

.an-explore-btn {
  background: none;
  border: 1px solid var(--border);
  padding: 10px 20px;
  font-family: var(--font-mono);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  border-radius: 4px;
  color: #666;
  transition: all 0.15s;
}

.an-explore-btn:hover { border-color: #999; color: #333; }
</style>
