<template>
  <div class="issue-tracker">
    <div class="it-label">ISSUES</div>
    <div class="it-cards">
      <div
        v-for="issue in issueCards"
        :key="issue.id"
        class="it-card"
        :class="{ agreed: issue.agreed }"
      >
        <div class="it-name">{{ issue.name }}</div>

        <!-- Agreed state -->
        <div v-if="issue.agreed" class="it-agreed">
          <span class="it-check">&#10003;</span>
          <span class="it-agreed-val">{{ issue.agreedValue }}</span>
        </div>

        <!-- Contested state -->
        <div v-else class="it-contested">
          <div class="it-party-vals">
            <div class="it-pval" v-if="issue.partyAVal">
              <span class="it-pval-dot" :style="{ background: PARTY_COLORS[0] }"></span>
              <span class="it-pval-text">{{ truncate(issue.partyAVal, 18) }}</span>
            </div>
            <div class="it-pval" v-if="issue.partyBVal">
              <span class="it-pval-dot" :style="{ background: PARTY_COLORS[1] }"></span>
              <span class="it-pval-text">{{ truncate(issue.partyBVal, 18) }}</span>
            </div>
            <div v-if="!issue.partyAVal && !issue.partyBVal" class="it-no-vals">No proposals yet</div>
          </div>
          <div class="it-gap-bar">
            <div
              class="it-gap-fill"
              :class="gapClass(issue.gapPct)"
              :style="{ width: (100 - issue.gapPct) + '%' }"
            ></div>
          </div>
          <!-- BCI opponent weight indicator -->
          <div v-if="issue.oppWeight != null" class="it-bci-row" :class="bciConfClass(issue.oppConf)">
            <span class="it-bci-label">OPP</span>
            <span class="it-bci-val">{{ issue.oppWeight.toFixed(2) }}</span>
            <div class="it-bci-bar">
              <div class="it-bci-fill" :style="{ width: (issue.oppWeight * 100) + '%' }"></div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { PARTY_COLORS } from '@/types/protocol'

const props = defineProps({
  issues: { type: Array, default: () => [] },
  issueStates: { type: Object, default: () => ({}) },
  parties: { type: Array, default: () => [] },
  agreement: { type: Object, default: null },
  beliefs: { type: Object, default: () => ({}) },
})

function truncate(s, n) {
  if (!s) return ''
  s = String(s)
  return s.length > n ? s.slice(0, n) + '...' : s
}

function gapClass(pct) {
  if (pct <= 0) return 'agreed'
  if (pct > 50) return 'high'
  return 'low'
}

function bciConfClass(conf) {
  if (conf > 0.6) return 'it-bci-conf-high'
  if (conf > 0.3) return 'it-bci-conf-mid'
  return 'it-bci-conf-low'
}

const issueCards = computed(() => {
  const partyAId = props.parties[0]?.id
  const partyBId = props.parties[1]?.id

  return props.issues.map(issue => {
    const is = props.issueStates[issue.id] || {}
    const agreedValue = props.agreement?.issue_values?.[issue.id] || is.agreedValue
    const agreed = !!agreedValue || is.agreed

    const partyAVal = is.partyValues?.[partyAId] || null
    const partyBVal = is.partyValues?.[partyBId] || null

    let gapPct = 100
    if (agreed) {
      gapPct = 0
    } else if (partyAVal && partyBVal) {
      if (String(partyAVal) === String(partyBVal)) gapPct = 0
      else if (!isNaN(partyAVal) && !isNaN(partyBVal)) {
        const a = parseFloat(partyAVal)
        const b = parseFloat(partyBVal)
        const max = Math.max(Math.abs(a), Math.abs(b)) || 1
        gapPct = Math.min(100, Math.round((Math.abs(a - b) / max) * 100))
      } else gapPct = 50
    }

    // BCI: get opponent weight for this issue
    // Show Party A's model of Party B (what does A think B cares about?)
    let oppWeight = null
    let oppConf = 0
    if (partyAId && partyBId) {
      const bkey = `${partyAId}→${partyBId}`
      const b = props.beliefs[bkey]
      if (b?.estimated_priorities && b.confidence >= 0.005) {
        oppWeight = b.estimated_priorities[issue.id] ?? b.estimated_priorities[issue.name] ?? null
        oppConf = b.confidence
      }
    }

    return { id: issue.id, name: issue.name, agreed, agreedValue, partyAVal, partyBVal, gapPct, oppWeight, oppConf }
  })
})
</script>

<style scoped>
.issue-tracker {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 16px;
  border-top: 1px solid var(--border);
  background: #FAFAFA;
  flex-shrink: 0;
  overflow: hidden;
}

.it-label {
  font-family: var(--font-mono);
  font-size: 9px;
  font-weight: 700;
  color: #BBB;
  letter-spacing: 1px;
  writing-mode: vertical-rl;
  transform: rotate(180deg);
  flex-shrink: 0;
}

.it-cards {
  display: flex;
  gap: 8px;
  overflow-x: auto;
  flex: 1;
  padding: 2px 0;
}

.it-cards::-webkit-scrollbar { height: 3px; }
.it-cards::-webkit-scrollbar-thumb { background: #CCC; border-radius: 2px; }

.it-card {
  min-width: 160px;
  max-width: 200px;
  padding: 10px 12px;
  background: #FFF;
  border: 1px solid var(--border);
  border-radius: 6px;
  flex-shrink: 0;
  transition: all 0.3s;
}

.it-card.agreed {
  border-color: #22c55e;
  background: #F0FDF4;
}

.it-name {
  font-size: 11px;
  font-weight: 600;
  margin-bottom: 8px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* Agreed */
.it-agreed {
  display: flex;
  align-items: center;
  gap: 6px;
}

.it-check { color: #22c55e; font-size: 14px; font-weight: 700; }

.it-agreed-val {
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: 600;
  color: #22c55e;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* Contested */
.it-contested {}

.it-party-vals {
  display: flex;
  flex-direction: column;
  gap: 3px;
  margin-bottom: 6px;
}

.it-pval {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 10px;
}

.it-pval-dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  flex-shrink: 0;
}

.it-pval-text {
  font-family: var(--font-mono);
  font-size: 10px;
  color: #555;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.it-no-vals {
  font-size: 10px;
  color: #CCC;
  font-style: italic;
}

.it-gap-bar {
  height: 4px;
  background: #F0F0F0;
  border-radius: 2px;
  overflow: hidden;
}

.it-gap-fill {
  height: 100%;
  border-radius: 2px;
  transition: width 0.6s ease;
}

.it-gap-fill.agreed { background: #22c55e; }
.it-gap-fill.low { background: #3b82f6; }
.it-gap-fill.high { background: var(--accent); }

/* BCI opponent weight indicator */
.it-bci-row {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-top: 4px;
  transition: opacity 0.3s ease;
}
.it-bci-conf-low { opacity: 0.7; }
.it-bci-conf-mid { opacity: 0.85; }
.it-bci-conf-high { opacity: 1.0; }

.it-bci-label {
  font-family: var(--font-mono);
  font-size: 8px;
  color: #BBB;
  letter-spacing: 1px;
  text-transform: uppercase;
}
.it-bci-val {
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 600;
  color: #000;
  min-width: 24px;
}
.it-bci-bar {
  flex: 1;
  height: 3px;
  background: #F0F0F0;
  border-radius: 1.5px;
  overflow: hidden;
}
.it-bci-fill {
  height: 100%;
  background: var(--accent);
  border-radius: 1.5px;
  transition: width 0.6s ease;
}
</style>
