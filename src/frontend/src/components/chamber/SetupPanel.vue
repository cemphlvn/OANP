<template>
  <div class="setup-panel">
    <div class="sp-inner">
      <div class="sp-header">
        <span class="sp-icon">&#9671;</span>
        <span class="sp-title">Setting Up Negotiation</span>
      </div>

      <p class="sp-desc">
        Generating satisfaction anchors for each party. These ground utility
        scoring with concrete reference points throughout the negotiation.
      </p>

      <!-- Step 01: Session -->
      <div class="sp-step completed">
        <div class="sp-step-head">
          <span class="sp-num">01</span>
          <span class="sp-name">Session Initialized</span>
          <span class="sp-badge done">Done</span>
        </div>
        <div class="sp-step-body">
          <div class="sp-row"><span class="sp-k">Session</span><span class="sp-v mono">{{ sessionId?.slice(0, 16) }}</span></div>
          <div class="sp-row"><span class="sp-k">Parties</span><span class="sp-v">{{ partyNames }}</span></div>
          <div class="sp-row"><span class="sp-k">Issues</span><span class="sp-v">{{ issueCount }} issues</span></div>
        </div>
      </div>

      <!-- Step 02: Anchors -->
      <div class="sp-step" :class="allDone ? 'completed' : 'active'">
        <div class="sp-step-head">
          <span class="sp-num">02</span>
          <span class="sp-name">Satisfaction Anchors</span>
          <span class="sp-badge" :class="allDone ? 'done' : 'working'">{{ allDone ? 'Done' : 'Generating...' }}</span>
        </div>
        <div class="sp-step-body">
          <div v-for="party in parties" :key="party.id" class="sp-anchor-party" :class="anchorsStatus[party.id]">
            <span class="sp-adot" :style="{ background: getColor(party.id) }"></span>
            <span class="sp-aname">{{ party.name }}</span>
            <span class="sp-astatus">
              <template v-if="anchorsStatus[party.id] === 'done'">&#10003; {{ countAnchors(party.id) }} anchors</template>
              <template v-else-if="anchorsStatus[party.id] === 'failed'">&#10007; Failed</template>
              <template v-else><span class="sp-spinner"></span> Generating...</template>
            </span>
          </div>

          <!-- Show anchor details when done -->
          <div v-for="party in parties" :key="'d-'+party.id">
            <div v-if="anchorsData[party.id]" class="sp-anchor-details">
              <div v-for="(interest, i) in anchorsData[party.id]" :key="i" class="sp-interest">
                <div class="sp-int-head">
                  <span class="sp-int-type" :style="{ background: intColor(interest.interest_type) }">{{ interest.interest_type?.toUpperCase() }}</span>
                  <span class="sp-int-desc">{{ interest.description }}</span>
                </div>
                <div class="sp-anchors">
                  <div v-for="(a, j) in interest.anchors" :key="j" class="sp-anchor-row">
                    <span class="sp-ascore" :style="{ color: scoreColor(a.score) }">{{ a.score.toFixed(2) }}</span>
                    <span class="sp-acond">{{ a.condition }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Step 03: Begin -->
      <div class="sp-step" :class="{ active: allDone }">
        <div class="sp-step-head">
          <span class="sp-num">03</span>
          <span class="sp-name">Begin Negotiation</span>
          <span class="sp-badge" :class="allDone ? 'working' : 'pending'">{{ allDone ? 'Starting...' : 'Waiting' }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { PARTY_COLORS, INTEREST_TYPE_COLORS } from '@/types/protocol'

const props = defineProps({
  sessionId: String,
  parties: { type: Array, default: () => [] },
  issues: { type: Array, default: () => [] },
  anchorsStatus: { type: Object, default: () => ({}) },
  anchorsData: { type: Object, default: () => ({}) }
})

const partyNames = computed(() => props.parties.map(p => p.name).join(' vs '))
const issueCount = computed(() => props.issues.length)

const allDone = computed(() => {
  if (props.parties.length === 0) return false
  return props.parties.every(p => props.anchorsStatus[p.id] === 'done')
})

function getColor(id) {
  const idx = props.parties.findIndex(p => p.id === id)
  return idx >= 0 ? PARTY_COLORS[idx] : '#999'
}

function countAnchors(id) {
  const data = props.anchorsData[id]
  if (!data) return 0
  return data.reduce((s, i) => s + (i.anchors?.length || 0), 0)
}

function intColor(type) { return INTEREST_TYPE_COLORS[type] || '#999' }

function scoreColor(s) {
  if (s >= 0.8) return '#22c55e'
  if (s >= 0.5) return '#f59e0b'
  return '#ef4444'
}
</script>

<style scoped>
.setup-panel {
  height: 100%;
  overflow-y: auto;
  background: #FAFAFA;
}

.sp-inner { max-width: 560px; margin: 0 auto; padding: 28px 20px; }

.sp-header { display: flex; align-items: center; gap: 10px; margin-bottom: 10px; }
.sp-icon { color: var(--accent); font-size: 1.2rem; }
.sp-title { font-size: 1.1rem; font-weight: 600; }

.sp-desc { font-size: 0.85rem; color: var(--gray-text); line-height: 1.6; margin-bottom: 24px; }

.sp-step {
  background: #FFF; border: 1px solid var(--border);
  border-radius: 8px; padding: 16px 20px; margin-bottom: 14px;
  transition: all 0.3s;
}

.sp-step.active { border-color: var(--accent); box-shadow: 0 4px 12px rgba(255,87,34,0.08); }

.sp-step-head { display: flex; align-items: center; gap: 12px; }

.sp-num {
  font-family: var(--font-mono); font-size: 18px; font-weight: 700; color: #E0E0E0;
}

.sp-step.active .sp-num, .sp-step.completed .sp-num { color: #000; }

.sp-name { font-weight: 600; font-size: 13px; flex: 1; }

.sp-badge {
  font-family: var(--font-mono); font-size: 10px; font-weight: 600;
  padding: 3px 8px; border-radius: 4px; text-transform: uppercase;
}

.sp-badge.done { background: #E8F5E9; color: #2E7D32; }
.sp-badge.working { background: var(--accent); color: #FFF; }
.sp-badge.pending { background: #F5F5F5; color: #999; }

.sp-step-body { margin-top: 12px; padding-top: 12px; border-top: 1px solid #F0F0F0; }

.sp-row { display: flex; justify-content: space-between; font-size: 12px; padding: 3px 0; }
.sp-k { color: #999; }
.sp-v { color: #333; font-weight: 500; }
.sp-v.mono { font-family: var(--font-mono); }

.sp-anchor-party {
  display: flex; align-items: center; gap: 10px;
  padding: 10px 12px; background: #F9F9F9; border-radius: 6px;
  font-size: 12px; margin-bottom: 6px;
}

.sp-anchor-party.done { background: #F0FAF0; }

.sp-adot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.sp-aname { font-weight: 600; flex: 1; }

.sp-astatus {
  font-family: var(--font-mono); font-size: 11px; color: #999;
  display: flex; align-items: center; gap: 6px;
}

.sp-anchor-party.done .sp-astatus { color: #2E7D32; }

.sp-spinner {
  width: 12px; height: 12px; border: 2px solid #FFCCBC;
  border-top-color: var(--accent); border-radius: 50%;
  animation: sp-spin 1s linear infinite; display: inline-block;
}

@keyframes sp-spin { to { transform: rotate(360deg); } }

/* Anchor details */
.sp-anchor-details { margin-top: 8px; }

.sp-interest { margin-bottom: 10px; }

.sp-int-head { display: flex; align-items: center; gap: 6px; margin-bottom: 4px; }

.sp-int-type {
  font-family: var(--font-mono); font-size: 8px; font-weight: 700;
  color: #FFF; padding: 2px 5px; border-radius: 2px;
}

.sp-int-desc { font-size: 11px; color: #444; }

.sp-anchors { padding-left: 4px; }

.sp-anchor-row {
  display: flex; align-items: baseline; gap: 8px;
  font-size: 10px; padding: 2px 0;
}

.sp-ascore { font-family: var(--font-mono); font-weight: 700; min-width: 32px; text-align: right; }
.sp-acond { font-family: var(--font-mono); color: #666; }
</style>
