<template>
  <div class="analysis-view">
    <StatusStrip
      :phase="metrics ? (metrics.outcome === 'agreement' ? 'settlement' : metrics.outcome === 'impasse' ? 'impasse' : 'setup') : 'setup'"
      :round="metrics?.total_rounds || 0"
      :moveCount="metrics?.total_moves || 0"
      :resolvedCount="metrics?.agreement ? Object.keys(metrics.agreement.issue_values || {}).length : 0"
      :totalIssues="issues.length"
      :convergence="metrics?.outcome === 'agreement' ? 100 : 0"
      :outcome="metrics?.outcome"
      :isAdvancedMode="!!compliance"
      :escalationTier="compliance?.current_tier"
    >
      <div class="analysis-nav">
        <button class="an-btn" :class="{ active: tab === 'report' }" @click="tab = 'report'">Report</button>
        <button class="an-btn" :class="{ active: tab === 'timeline' }" @click="tab = 'timeline'">Timeline</button>
        <button v-if="compliance" class="an-btn" :class="{ active: tab === 'compliance' }" @click="tab = 'compliance'">Compliance</button>
        <button v-if="award" class="an-btn" :class="{ active: tab === 'award' }" @click="tab = 'award'">Award</button>
      </div>
    </StatusStrip>

    <div class="an-main" v-if="metrics">
      <!-- ==================== REPORT TAB ==================== -->
      <div v-if="tab === 'report'" class="an-report">

        <!-- 1. VERDICT -->
        <div class="an-verdict" :class="metrics.outcome">
          <div class="an-verdict-text">{{ metrics.outcome === 'agreement' ? 'Agreement Reached' : 'Impasse' }}</div>
          <div class="an-verdict-stats">
            {{ metrics.total_rounds }} rounds · {{ metrics.total_moves }} moves · {{ (metrics.disclosure_rate * 100).toFixed(0) }}% disclosed
          </div>
        </div>

        <div class="an-sep"></div>

        <!-- 2. AGREEMENT TERMS -->
        <div v-if="metrics.agreement" class="an-terms-section">
          <div class="an-section-label">Agreement</div>
          <div class="an-terms-doc">
            <div v-for="(val, key) in metrics.agreement.issue_values" :key="key" class="an-term-row">
              <span class="an-term-key">{{ issueNames[key] || key }}</span>
              <span class="an-term-dots"></span>
              <span class="an-term-val">{{ formatValue(key, val) }}</span>
            </div>
          </div>
        </div>
        <div v-else class="an-no-agreement">No agreement reached</div>

        <div class="an-sep"></div>

        <!-- 3. PARTY COLUMNS -->
        <div class="an-parties">
          <div v-for="(partyId, idx) in partyIds" :key="partyId" class="an-party-col">
            <!-- Party name -->
            <div class="an-party-name" :style="{ color: getPartyColor(partyId) }">
              {{ partyNames[partyId] || partyId }}
            </div>

            <!-- Utility score -->
            <div class="an-party-utility">{{ (metrics.party_utilities?.[partyId] || 0).toFixed(2) }}</div>
            <div class="an-party-bar-track">
              <div class="an-party-bar-fill" :style="{
                width: ((metrics.party_utilities?.[partyId] || 0) * 100) + '%',
                background: getPartyColor(partyId)
              }"></div>
            </div>

            <!-- BATNA surplus + interest satisfaction -->
            <div class="an-party-meta">
              <span :class="(metrics.party_batna_surplus?.[partyId] || 0) >= 0 ? 'pos' : 'neg'">
                BATNA {{ (metrics.party_batna_surplus?.[partyId] || 0) >= 0 ? '+' : '' }}{{ (metrics.party_batna_surplus?.[partyId] || 0).toFixed(2) }}
              </span>
              <span v-if="metrics.party_interest_satisfaction?.[partyId]" class="dim">
                · Interests {{ (metrics.party_interest_satisfaction[partyId] * 100).toFixed(0) }}%
              </span>
            </div>

            <!-- BCI: What they thought -->
            <template v-if="partyBci(partyId)">
              <div class="an-party-divider"></div>
              <div class="an-bci-label">Opponent Model <span class="an-bci-conf">{{ (partyBci(partyId).confidence * 100).toFixed(0) }}%</span></div>
              <div v-for="item in partyBciWeights(partyId)" :key="item.id" class="an-bci-row">
                <span class="an-bci-issue">{{ item.name }}</span>
                <div class="an-bci-bar">
                  <div class="an-bci-fill" :style="{ width: (item.weight * 100) + '%', opacity: 0.3 + item.weight * 0.7 }"></div>
                </div>
                <span class="an-bci-weight">{{ item.weight.toFixed(2) }}</span>
              </div>
              <div v-if="partyBci(partyId).estimated_batna_utility != null" class="an-bci-batna">
                Est. BATNA {{ partyBci(partyId).estimated_batna_utility.toFixed(2) }}
              </div>
            </template>
          </div>
        </div>

        <div class="an-sep"></div>

        <!-- 4. SHARED METRICS -->
        <div class="an-shared-metrics">
          <div class="an-sm-item">
            <span class="an-sm-val">{{ metrics.social_welfare?.toFixed(2) }}</span>
            <span class="an-sm-label">Social Welfare</span>
          </div>
          <div class="an-sm-item">
            <span class="an-sm-val">{{ metrics.nash_product?.toFixed(4) }}</span>
            <span class="an-sm-label">Nash Product</span>
          </div>
          <div class="an-sm-item">
            <span class="an-sm-val">{{ metrics.integrative_index?.toFixed(2) }}</span>
            <span class="an-sm-label">Integrative Index</span>
          </div>
          <div class="an-sm-item">
            <span class="an-sm-val">{{ metrics.pareto_efficient ? '✓' : '—' }}</span>
            <span class="an-sm-label">Pareto Efficient</span>
          </div>
        </div>

        <div class="an-sep"></div>

        <!-- 5. PROCESS (stacked bar) -->
        <div class="an-process">
          <div class="an-section-label">Process</div>
          <div class="an-stacked-bar">
            <div
              v-for="(count, moveType) in metrics.move_breakdown"
              :key="moveType"
              class="an-stacked-seg"
              :style="{ flex: count, background: segColor(moveType) }"
              :title="`${MOVE_LABELS[moveType] || moveType}: ${count}`"
            ></div>
          </div>
          <div class="an-process-legend">
            <span v-for="(count, moveType) in metrics.move_breakdown" :key="moveType" class="an-proc-item">
              <span class="an-proc-dot" :style="{ background: segColor(moveType) }"></span>
              {{ MOVE_LABELS[moveType] || moveType }} {{ count }}
            </span>
          </div>
        </div>

        <!-- 6. CRITIQUE -->
        <div v-if="metrics.critique?.length" class="an-critique-section">
          <div class="an-sep"></div>
          <div v-for="(issue, idx) in metrics.critique" :key="idx" class="an-crit-row">
            <span class="an-crit-dot" :style="{ background: critColor(issue.severity) }"></span>
            <span class="an-crit-sev" :style="{ color: critColor(issue.severity) }">{{ issue.severity }}</span>
            <span class="an-crit-desc">{{ issue.description }}</span>
          </div>
        </div>

        <!-- Footer -->
        <div class="an-footer">
          <button class="an-back-btn" @click="$router.push({ name: 'Negotiate', params: { sessionId }, query: { demo: '1' } })">
            ← Back to Negotiation
          </button>
        </div>
      </div>

      <!-- ==================== TIMELINE TAB ==================== -->
      <TimelineView
        v-else-if="tab === 'timeline'"
        :moves="moves"
        :parties="parties"
        :showAllReasoning="true"
      />

      <!-- ==================== COMPLIANCE TAB ==================== -->
      <ComplianceAudit
        v-else-if="tab === 'compliance' && compliance"
        :compliance="compliance"
        :award="award"
        :tierHistory="compliance.tier_history || []"
        :parties="parties"
      />

      <!-- ==================== AWARD TAB ==================== -->
      <AwardDocument
        v-else-if="tab === 'award' && award"
        :award="award"
        :formattedText="awardFormattedText"
      />
    </div>

    <!-- Loading / Error -->
    <div v-else-if="loadError" class="an-error">
      <span class="an-error-title">Failed to load analysis</span>
      <span class="an-error-msg">{{ loadError }}</span>
      <button class="an-retry" @click="loadData">Retry</button>
    </div>
    <div v-else class="an-loading">
      <div class="an-loading-spinner"></div>
      Loading analysis...
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { getSession, getAnalysis, getMoves, getCompliance } from '@/api/endpoints'
import { MOVE_LABELS, PARTY_COLORS } from '@/types/protocol'
import StatusStrip from '@/components/chamber/StatusStrip.vue'
import TimelineView from '@/components/chamber/TimelineView.vue'
import ComplianceAudit from '@/components/chamber/ComplianceAudit.vue'
import AwardDocument from '@/components/chamber/AwardDocument.vue'

const props = defineProps({ sessionId: String })

const tab = ref('report')
const metrics = ref(null)
const parties = ref([])
const issues = ref([])
const moves = ref([])
const loadError = ref(null)
const compliance = ref(null)
const award = ref(null)
const awardFormattedText = ref(null)

const partyNames = computed(() => {
  const map = {}
  parties.value.forEach(p => { map[p.id] = p.name })
  return map
})

const partyIds = computed(() => parties.value.map(p => p.id))

const issueNames = computed(() => {
  const map = {}
  issues.value.forEach(i => { map[i.id] = i.name; map[i.name] = i.name })
  return map
})

function getPartyColor(partyId) {
  const idx = parties.value.findIndex(p => p.id === partyId)
  return idx >= 0 ? PARTY_COLORS[idx] : '#999'
}

// BCI helpers
function partyBci(partyId) {
  if (!metrics.value?.opponent_models) return null
  // Find this party's model of the other party
  const key = Object.keys(metrics.value.opponent_models).find(k => k.startsWith(partyId + '→'))
  return key ? metrics.value.opponent_models[key] : null
}

function partyBciWeights(partyId) {
  const bci = partyBci(partyId)
  if (!bci?.estimated_priorities) return []
  return Object.entries(bci.estimated_priorities)
    .map(([id, weight]) => ({ id, name: issueNames.value[id] || id, weight }))
    .sort((a, b) => b.weight - a.weight)
}

// Value formatting
function formatValue(key, val) {
  if (!val) return val
  const s = String(val)
  // Monetary: add $ and commas
  if (/^\d{4,}$/.test(s)) {
    return '$' + Number(s).toLocaleString()
  }
  // Underscore to spaces, title case
  if (s.includes('_')) {
    return s.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
  }
  return s
}

// Process bar colors — monochrome scale with accent for accept
const SEG_COLORS = {
  propose: '#000', counter: '#333', argue: '#666',
  disclose_interest: '#999', invoke_criterion: '#AAA',
  accept: '#FF5722', reject: '#ef4444', meso: '#444',
  invoke_batna: '#CCC', request_mediation: '#DDD',
}
function segColor(moveType) { return SEG_COLORS[moveType] || '#CCC' }

// Critique colors
function critColor(severity) {
  return { high: '#ef4444', medium: '#f59e0b', low: '#999', info: '#3b82f6' }[severity] || '#CCC'
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

    if (sessionData.compliance?.mode === 'advanced') {
      try {
        const complianceData = await getCompliance(props.sessionId)
        compliance.value = complianceData.compliance
        award.value = complianceData.award
        awardFormattedText.value = complianceData.award?.formatted_text || null
      } catch (e) {
        console.warn('Compliance data unavailable:', e)
      }
    }
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
  font-family: var(--font-body);
}

.an-main { flex: 1; overflow-y: auto; }

.an-report {
  max-width: 720px;
  margin: 0 auto;
  padding: 0 24px 48px;
}

/* Navigation */
.analysis-nav { display: flex; background: #F5F5F5; padding: 3px; border-radius: 6px; gap: 3px; }
.an-btn {
  border: none; background: transparent; padding: 5px 14px;
  font-size: 11px; font-weight: 600; color: #999; border-radius: 4px;
  cursor: pointer; font-family: var(--font-heading); transition: all 0.15s;
}
.an-btn.active { background: #FFF; color: #000; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }
.an-btn:hover:not(.active) { color: #666; }

/* 1. VERDICT */
.an-verdict {
  text-align: center;
  padding: 48px 0 40px;
}
.an-verdict-text {
  font-family: var(--font-heading);
  font-size: 24px;
  font-weight: 700;
  letter-spacing: 2px;
  text-transform: uppercase;
  color: #000;
}
.an-verdict.impasse .an-verdict-text { color: #ef4444; }
.an-verdict-stats {
  font-family: var(--font-mono);
  font-size: 11px;
  color: #999;
  margin-top: 8px;
}

/* Separator */
.an-sep {
  height: 1px;
  background: #F0F0F0;
  margin: 0 60px;
}
@media (max-width: 600px) { .an-sep { margin: 0 20px; } }

/* 2. AGREEMENT TERMS */
.an-terms-section { padding: 32px 0; }
.an-section-label {
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 1.5px;
  text-transform: uppercase;
  color: #BBB;
  text-align: center;
  margin-bottom: 20px;
}
.an-terms-doc {
  max-width: 400px;
  margin: 0 auto;
}
.an-term-row {
  display: flex;
  align-items: baseline;
  padding: 6px 0;
}
.an-term-key {
  font-family: var(--font-body);
  font-size: 13px;
  color: #666;
  white-space: nowrap;
}
.an-term-dots {
  flex: 1;
  border-bottom: 1px dotted #E0E0E0;
  margin: 0 8px;
  min-width: 20px;
  position: relative;
  top: -3px;
}
.an-term-val {
  font-family: var(--font-mono);
  font-size: 13px;
  font-weight: 600;
  color: #000;
  white-space: nowrap;
}
.an-no-agreement {
  text-align: center;
  padding: 32px 0;
  font-family: var(--font-mono);
  font-size: 13px;
  color: #999;
}

/* 3. PARTY COLUMNS */
.an-parties {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 48px;
  padding: 32px 0;
}
@media (max-width: 600px) {
  .an-parties { grid-template-columns: 1fr; gap: 32px; }
}
.an-party-col { min-width: 0; }

.an-party-name {
  font-family: var(--font-heading);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 1px;
  text-transform: uppercase;
  margin-bottom: 8px;
  opacity: 0.7;
}
.an-party-utility {
  font-family: var(--font-mono);
  font-size: 36px;
  font-weight: 700;
  color: #000;
  line-height: 1;
  margin-bottom: 6px;
}
.an-party-bar-track {
  height: 4px;
  background: #F0F0F0;
  border-radius: 2px;
  margin-bottom: 8px;
  overflow: hidden;
}
.an-party-bar-fill {
  height: 100%;
  border-radius: 2px;
  transition: width 0.6s ease;
}
.an-party-meta {
  font-family: var(--font-mono);
  font-size: 11px;
  color: #999;
}
.an-party-meta .pos { color: #22c55e; }
.an-party-meta .neg { color: #ef4444; }
.an-party-meta .dim { color: #BBB; }

/* BCI in party columns */
.an-party-divider {
  margin: 16px 0;
  border-top: 1px solid #F0F0F0;
}
.an-bci-label {
  font-family: var(--font-mono);
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 1px;
  text-transform: uppercase;
  color: #CCC;
  margin-bottom: 8px;
}
.an-bci-conf {
  font-weight: 600;
  color: #999;
  text-transform: none;
  letter-spacing: 0;
}
.an-bci-row {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 2px 0;
}
.an-bci-issue {
  font-family: var(--font-mono);
  font-size: 10px;
  color: #666;
  min-width: 70px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.an-bci-bar {
  flex: 1;
  height: 4px;
  background: #F0F0F0;
  border-radius: 2px;
  overflow: hidden;
}
.an-bci-fill {
  height: 100%;
  background: #000;
  border-radius: 2px;
}
.an-bci-weight {
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 600;
  min-width: 28px;
  text-align: right;
}
.an-bci-batna {
  margin-top: 6px;
  font-family: var(--font-mono);
  font-size: 10px;
  color: #CCC;
}

/* 4. SHARED METRICS */
.an-shared-metrics {
  display: flex;
  justify-content: space-between;
  max-width: 480px;
  margin: 0 auto;
  padding: 24px 0;
}
.an-sm-item { text-align: center; }
.an-sm-val {
  display: block;
  font-family: var(--font-mono);
  font-size: 14px;
  font-weight: 700;
  color: #000;
  margin-bottom: 2px;
}
.an-sm-label {
  font-family: var(--font-mono);
  font-size: 9px;
  color: #999;
  letter-spacing: 0.5px;
}

/* 5. PROCESS */
.an-process { padding: 24px 0; }
.an-stacked-bar {
  display: flex;
  height: 8px;
  border-radius: 4px;
  overflow: hidden;
  gap: 1px;
  margin-bottom: 10px;
}
.an-stacked-seg {
  transition: flex 0.6s ease;
  min-width: 2px;
}
.an-process-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 14px;
  font-family: var(--font-mono);
  font-size: 10px;
  color: #999;
}
.an-proc-item { display: flex; align-items: center; gap: 4px; }
.an-proc-dot { width: 6px; height: 6px; border-radius: 1px; }

/* 6. CRITIQUE */
.an-critique-section { padding: 24px 0; }
.an-crit-row {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 6px 0;
}
.an-crit-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  margin-top: 5px;
  flex-shrink: 0;
}
.an-crit-sev {
  font-family: var(--font-mono);
  font-size: 9px;
  font-weight: 600;
  min-width: 48px;
}
.an-crit-desc {
  font-family: var(--font-body);
  font-size: 12px;
  color: #444;
  line-height: 1.6;
}

/* Footer */
.an-footer {
  margin-top: 24px;
  padding-top: 20px;
  border-top: 1px solid var(--border);
}
.an-back-btn {
  background: none;
  border: 1px solid var(--border);
  padding: 10px 20px;
  font-family: var(--font-mono);
  font-size: 12px;
  font-weight: 600;
  color: #666;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.15s;
}
.an-back-btn:hover { border-color: #999; color: #333; }

/* Loading / Error */
.an-loading {
  display: flex; flex-direction: column; align-items: center;
  justify-content: center; height: 300px; gap: 16px; color: #999;
  font-family: var(--font-mono); font-size: 12px;
}
.an-loading-spinner {
  width: 24px; height: 24px; border: 3px solid #F0F0F0;
  border-top-color: var(--accent); border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.an-error {
  display: flex; flex-direction: column; align-items: center;
  justify-content: center; height: 300px; gap: 12px;
}
.an-error-title { font-weight: 600; color: #C62828; }
.an-error-msg { font-family: var(--font-mono); font-size: 12px; color: #999; }
.an-retry {
  background: #000; color: #FFF; border: none; padding: 8px 20px;
  border-radius: 4px; cursor: pointer; font-family: var(--font-mono);
}
.an-retry:hover { background: var(--accent); }
</style>
