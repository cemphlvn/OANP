<template>
  <div class="xray-view">
    <!-- Party A Mind -->
    <div class="xray-col xray-mind">
      <div class="xray-col-header mind-header">
        <span class="col-dot" :style="{ background: partyAColor }"></span>
        {{ partyAName }}'s Mind
      </div>
      <div class="xray-col-body" ref="colARef">
        <MoveCard
          v-for="m in partyAMoves"
          :key="m.id"
          :move="m"
          :partyName="partyAName"
          :partyColor="partyAColor"
          :showReasoning="true"
        />
        <div v-if="partyAMoves.length === 0" class="xray-empty">No moves yet</div>
      </div>
    </div>

    <!-- Public Moves -->
    <div class="xray-col xray-public">
      <div class="xray-col-header public-header">
        Public Moves
      </div>
      <div class="xray-col-body" ref="publicRef">
        <template v-for="(item, idx) in publicItems" :key="item._key">
          <div v-if="item._isPhaseBreak" class="xray-phase-break">
            <span :style="{ color: phaseColor(item.phase) }">{{ item.phase.toUpperCase() }}</span>
          </div>
          <MoveCard
            v-else
            :move="item"
            :partyName="getPartyName(item.party_id)"
            :partyColor="getPartyColor(item.party_id)"
            :showReasoning="false"
          />
        </template>
        <div v-if="props.moves.length === 0" class="xray-empty">Waiting for moves...</div>
      </div>
    </div>

    <!-- Party B Mind -->
    <div class="xray-col xray-mind">
      <div class="xray-col-header mind-header">
        <span class="col-dot" :style="{ background: partyBColor }"></span>
        {{ partyBName }}'s Mind
      </div>
      <div class="xray-col-body" ref="colBRef">
        <MoveCard
          v-for="m in partyBMoves"
          :key="m.id"
          :move="m"
          :partyName="partyBName"
          :partyColor="partyBColor"
          :showReasoning="true"
        />
        <div v-if="partyBMoves.length === 0" class="xray-empty">No moves yet</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch, nextTick } from 'vue'
import MoveCard from './MoveCard.vue'
import { PARTY_COLORS, PHASE_COLORS } from '@/types/protocol'

const props = defineProps({
  moves: { type: Array, default: () => [] },
  parties: { type: Array, default: () => [] }
})

const colARef = ref(null)
const colBRef = ref(null)
const publicRef = ref(null)

const partyAId = computed(() => props.parties[0]?.id)
const partyBId = computed(() => props.parties[1]?.id)
const partyAName = computed(() => props.parties[0]?.name || 'Party A')
const partyBName = computed(() => props.parties[1]?.name || 'Party B')
const partyAColor = computed(() => PARTY_COLORS[0])
const partyBColor = computed(() => PARTY_COLORS[1])

const partyAMoves = computed(() => props.moves.filter(m => m.party_id === partyAId.value))
const partyBMoves = computed(() => props.moves.filter(m => m.party_id === partyBId.value))

// Public items: moves interleaved with phase break markers, each with a unique _key
const publicItems = computed(() => {
  const result = []
  let lastPhase = null
  for (const m of props.moves) {
    if (m.phase && m.phase !== lastPhase) {
      result.push({ _isPhaseBreak: true, phase: m.phase, _key: `pb-${m.phase}-${m.round}` })
      lastPhase = m.phase
    }
    result.push({ ...m, _key: `mv-${m.id || result.length}` })
  }
  return result
})

function getPartyName(partyId) {
  if (partyId === 'mediator') return 'Mediator'
  const p = props.parties.find(p => p.id === partyId)
  return p?.name || partyId
}

function getPartyColor(partyId) {
  if (partyId === 'mediator') return '#22c55e'
  const idx = props.parties.findIndex(p => p.id === partyId)
  return idx >= 0 ? PARTY_COLORS[idx] : '#999'
}

function phaseColor(phase) {
  return PHASE_COLORS[phase] || '#999'
}

// Auto-scroll all columns
watch(() => props.moves.length, () => {
  nextTick(() => {
    colARef.value?.scrollTo({ top: colARef.value.scrollHeight, behavior: 'smooth' })
    colBRef.value?.scrollTo({ top: colBRef.value.scrollHeight, behavior: 'smooth' })
    publicRef.value?.scrollTo({ top: publicRef.value.scrollHeight, behavior: 'smooth' })
  })
})
</script>

<style scoped>
.xray-view {
  display: flex;
  height: 100%;
  overflow: hidden;
}

.xray-col {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  border-right: 1px solid var(--border);
}

.xray-col:last-child { border-right: none; }

.xray-col-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  border-bottom: 2px solid var(--border);
  font-size: 12px;
  font-weight: 700;
  flex-shrink: 0;
  letter-spacing: 0.3px;
}

.mind-header {
  background: #FFFBF5;
  color: #886;
}

.public-header {
  background: #FAFAFA;
  color: #666;
  justify-content: center;
}

.col-dot { width: 8px; height: 8px; border-radius: 50%; }

.xray-col-body {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.xray-mind .xray-col-body {
  background: #FEFCF8;
}

.xray-empty {
  text-align: center;
  color: #CCC;
  font-family: var(--font-mono);
  font-size: 11px;
  padding: 40px 0;
}

.xray-phase-break {
  text-align: center;
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 2px;
  padding: 8px 0;
  opacity: 0.6;
}
</style>
