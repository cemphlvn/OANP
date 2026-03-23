<template>
  <div class="graph-panel" ref="panelRef">
    <div class="panel-header">
      <span class="panel-title">Negotiation Graph</span>
      <div class="header-tools">
        <button class="tool-btn" @click="$emit('refresh')" title="Refresh layout">
          <span class="icon-refresh" :class="{ spinning: loading }">↻</span>
          <span class="btn-text">Refresh</span>
        </button>
        <button class="tool-btn" @click="$emit('toggle-maximize')" title="Maximize/Restore">
          <span class="icon-maximize">⛶</span>
        </button>
      </div>
    </div>

    <div class="graph-container">
      <svg ref="svgRef" class="graph-svg"></svg>

      <!-- Live update hint -->
      <div v-if="isLive" class="live-hint">
        <div class="live-dot"></div>
        <span>Live — updating with negotiation moves</span>
      </div>

      <!-- Node detail panel -->
      <div v-if="selectedNode" class="detail-panel">
        <div class="detail-header">
          <span class="detail-type" :style="{ background: detailTypeBg }">{{ selectedNode.nodeType?.toUpperCase() }}</span>
          <span class="detail-name">{{ selectedNode.label }}</span>
          <button class="detail-close" @click="selectedNode = null">×</button>
        </div>
        <div class="detail-body">
          <!-- Party details -->
          <template v-if="selectedNode.nodeType === 'party'">
            <div class="detail-row">
              <span class="detail-label">Role:</span>
              <span class="detail-value">{{ selectedNode.meta?.role }}</span>
            </div>
            <div class="detail-row" v-if="selectedNode.meta?.interestCount">
              <span class="detail-label">Interests:</span>
              <span class="detail-value">{{ selectedNode.meta.interestCount }} total</span>
            </div>
          </template>

          <!-- Issue details -->
          <template v-if="selectedNode.nodeType === 'issue'">
            <div class="detail-row">
              <span class="detail-label">Type:</span>
              <span class="detail-value">{{ selectedNode.meta?.type }}</span>
            </div>
            <div class="detail-row" v-if="selectedNode.meta?.range">
              <span class="detail-label">Range:</span>
              <span class="detail-value mono">{{ selectedNode.meta.range[0] }} – {{ selectedNode.meta.range[1] }}</span>
            </div>
            <div class="detail-row" v-if="selectedNode.meta?.options">
              <span class="detail-label">Options:</span>
              <span class="detail-value mono">{{ selectedNode.meta.options.join(', ') }}</span>
            </div>
            <div class="detail-row" v-if="selectedNode.agreed">
              <span class="detail-label">Agreed:</span>
              <span class="detail-value agreed">{{ selectedNode.agreedValue }}</span>
            </div>
          </template>

          <!-- Interest details -->
          <template v-if="selectedNode.nodeType === 'interest'">
            <div class="detail-row">
              <span class="detail-label">Type:</span>
              <span class="detail-value">{{ selectedNode.meta?.interestType }}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">Priority:</span>
              <span class="detail-value mono">{{ selectedNode.meta?.priority }}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">Status:</span>
              <span class="detail-value" :class="selectedNode.disclosed ? 'disclosed' : 'hidden-int'">
                {{ selectedNode.disclosed ? 'Disclosed' : 'Private' }}
              </span>
            </div>
          </template>

          <!-- Criterion details -->
          <template v-if="selectedNode.nodeType === 'criterion'">
            <div class="detail-row">
              <span class="detail-label">Source:</span>
              <span class="detail-value">{{ selectedNode.meta?.source }}</span>
            </div>
            <div class="detail-row" v-if="selectedNode.meta?.referenceValue">
              <span class="detail-label">Reference:</span>
              <span class="detail-value mono">{{ selectedNode.meta.referenceValue }}</span>
            </div>
          </template>
        </div>
      </div>

      <!-- Legend -->
      <div class="graph-legend">
        <div class="legend-item"><span class="legend-circle" style="background: var(--party-a)"></span> Party</div>
        <div class="legend-item"><span class="legend-rect"></span> Issue</div>
        <div class="legend-item"><span class="legend-diamond" style="background: #06b6d4"></span> Interest</div>
        <div class="legend-item"><span class="legend-hex"></span> Criterion</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useForceGraph } from './useForceGraph'
import { PARTY_COLORS, MEDIATOR_COLOR, MOVE_COLORS } from '@/types/protocol'

const props = defineProps({
  parties: { type: Array, default: () => [] },
  issues: { type: Array, default: () => [] },
  criteria: { type: Array, default: () => [] },
  moves: { type: Array, default: () => [] },
  phase: { type: String, default: 'setup' },
  activePartyId: { type: String, default: null },
  outcome: { type: String, default: null },
  agreement: { type: Object, default: null },
  loading: { type: Boolean, default: false },
  isLive: { type: Boolean, default: false }
})

defineEmits(['refresh', 'toggle-maximize'])

const panelRef = ref(null)
const svgRef = ref(null)
const selectedNode = ref(null)

// Build graph data from protocol state
const graphNodes = computed(() => {
  const nodes = []

  // Party nodes
  props.parties.forEach((party, idx) => {
    nodes.push({
      id: party.id,
      label: party.name,
      nodeType: 'party',
      color: PARTY_COLORS[idx % PARTY_COLORS.length],
      isActive: party.id === props.activePartyId,
      meta: {
        role: party.role,
        interestCount: 0 // Updated below if interests are visible
      }
    })
  })

  // Issue nodes
  props.issues.forEach(issue => {
    const agreedValue = props.agreement?.issue_values?.[issue.id]
    nodes.push({
      id: issue.id,
      label: issue.name,
      nodeType: 'issue',
      agreed: !!agreedValue,
      agreedValue,
      meta: {
        type: issue.type,
        range: issue.range,
        options: issue.options
      }
    })
  })

  // Criterion nodes
  props.criteria.forEach(criterion => {
    nodes.push({
      id: `criterion-${criterion.name}`,
      label: criterion.name,
      nodeType: 'criterion',
      meta: {
        source: criterion.source,
        referenceValue: criterion.reference_value,
        appliesTo: criterion.applies_to
      }
    })
  })

  // Interest nodes from disclosed interests in moves
  const disclosedInterests = new Map()
  props.moves.forEach(move => {
    if (move.move_type === 'disclose_interest' && move.disclosed_interest) {
      const di = move.disclosed_interest
      const key = `interest-${move.party_id}-${di.description?.slice(0, 30)}`
      disclosedInterests.set(key, {
        ...di,
        partyId: move.party_id,
        nodeId: key
      })
    }
  })

  disclosedInterests.forEach((interest, key) => {
    const partyIdx = props.parties.findIndex(p => p.id === interest.partyId)
    nodes.push({
      id: key,
      label: interest.description?.slice(0, 25) + (interest.description?.length > 25 ? '...' : ''),
      nodeType: 'interest',
      disclosed: true,
      color: '#06b6d4',
      meta: {
        interestType: interest.interest_type,
        priority: interest.priority,
        relatedIssues: interest.related_issues,
        partyId: interest.partyId
      }
    })
  })

  // Mediator node (if mediator moves exist)
  const hasMediatorMoves = props.moves.some(m => m._isMediatorNote)
  if (hasMediatorMoves) {
    nodes.push({
      id: 'mediator',
      label: 'Mediator',
      nodeType: 'mediator',
      color: MEDIATOR_COLOR
    })
  }

  return nodes
})

const graphEdges = computed(() => {
  const edges = []

  // Party → Issue edges (based on proposals)
  const latestProposals = new Map() // key: `partyId-issueId`
  props.moves.forEach(move => {
    if (move.package?.issue_values) {
      Object.keys(move.package.issue_values).forEach(issueId => {
        latestProposals.set(`${move.party_id}-${issueId}`, {
          partyId: move.party_id,
          issueId,
          value: move.package.issue_values[issueId]
        })
      })
    }
  })

  latestProposals.forEach(({ partyId, issueId, value }) => {
    const partyIdx = props.parties.findIndex(p => p.id === partyId)
    edges.push({
      id: `pos-${partyId}-${issueId}`,
      source: partyId,
      target: issueId,
      type: 'party-issue',
      color: (PARTY_COLORS[partyIdx % PARTY_COLORS.length]) + '55',
      width: 1.5,
      label: value
    })
  })

  // Criterion → Issue edges
  props.criteria.forEach(criterion => {
    (criterion.applies_to || []).forEach(issueId => {
      edges.push({
        id: `crit-${criterion.name}-${issueId}`,
        source: `criterion-${criterion.name}`,
        target: issueId,
        type: 'criterion-issue',
        color: '#a855f733',
        width: 1,
        dashed: true
      })
    })
  })

  // Interest → Issue edges (use disclosed interests from moves directly, not graphNodes)
  const disclosedInterests = new Map()
  props.moves.forEach(move => {
    if (move.move_type === 'disclose_interest' && move.disclosed_interest) {
      const di = move.disclosed_interest
      const key = `interest-${move.party_id}-${di.description?.slice(0, 30)}`
      disclosedInterests.set(key, { ...di, partyId: move.party_id })
    }
  })

  disclosedInterests.forEach((interest, nodeId) => {
    (interest.related_issues || []).forEach(issueId => {
      if (props.issues.some(i => i.id === issueId)) {
        edges.push({
          id: `int-${nodeId}-${issueId}`,
          source: nodeId,
          target: issueId,
          type: 'interest-issue',
          color: '#06b6d433',
          width: 1,
          dashed: true
        })
      }
    })
  })

  // Move edges — only last 4 moves, use move.id for stable keys
  const recentMoves = props.moves.slice(-4)
  recentMoves.forEach((move) => {
    if (move._isMediatorNote || move.party_id === 'mediator') return // skip mediator move edges
    const otherParties = props.parties.filter(p => p.id !== move.party_id)
    otherParties.forEach(other => {
      edges.push({
        id: `move-${move.id}-${other.id}`,
        source: move.party_id,
        target: other.id,
        type: 'move',
        color: (MOVE_COLORS[move.move_type] || '#999') + '33',
        width: 1.5,
        opacity: 0.3
      })
    })
  })

  return edges
})

const detailTypeBg = computed(() => {
  if (!selectedNode.value) return '#000'
  const type = selectedNode.value.nodeType
  if (type === 'party') return selectedNode.value.color || '#3b82f6'
  if (type === 'issue') return '#666'
  if (type === 'interest') return '#06b6d4'
  if (type === 'criterion') return '#a855f7'
  if (type === 'mediator') return '#22c55e'
  return '#000'
})

function handleNodeClick(node) {
  selectedNode.value = selectedNode.value?.id === node.id ? null : node
}

const { pulseNode, flashEdge, markAgreed, revealInterest } = useForceGraph(svgRef, {
  nodes: graphNodes,
  edges: graphEdges,
  onNodeClick: handleNodeClick
})

// Pulse active party
watch(() => props.activePartyId, (id) => {
  if (id) pulseNode(id)
})

// Flash edges on new moves
let lastMoveCount = 0
watch(() => props.moves.length, (count) => {
  if (count > lastMoveCount && count > 0) {
    const move = props.moves[count - 1]
    if (move.party_id) {
      const target = props.parties.find(p => p.id !== move.party_id)
      if (target) {
        const partyIdx = props.parties.findIndex(p => p.id === move.party_id)
        flashEdge(move.party_id, target.id, PARTY_COLORS[partyIdx % PARTY_COLORS.length])
      }
    }
    // Reveal interest
    if (move.move_type === 'disclose_interest' && move.disclosed_interest) {
      const key = `interest-${move.party_id}-${move.disclosed_interest.description?.slice(0, 30)}`
      revealInterest(key)
    }
  }
  lastMoveCount = count
})

// Mark issues agreed on settlement
watch(() => props.agreement, (agreement) => {
  if (agreement?.issue_values) {
    Object.keys(agreement.issue_values).forEach(issueId => {
      markAgreed(issueId)
    })
  }
})
</script>

<style scoped>
.graph-panel {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #FAFAFA;
  overflow: hidden;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid var(--border);
  background: #FFF;
  flex-shrink: 0;
}

.panel-title {
  font-family: var(--font-mono);
  font-size: 12px;
  font-weight: 600;
  color: #666;
  letter-spacing: 0.5px;
}

.header-tools {
  display: flex;
  gap: 8px;
}

.tool-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  background: none;
  border: 1px solid var(--border);
  padding: 4px 10px;
  font-size: 11px;
  font-family: var(--font-mono);
  color: #666;
  cursor: pointer;
  border-radius: 4px;
  transition: all 0.15s;
}

.tool-btn:hover { border-color: #999; color: #333; }

.icon-refresh { display: inline-block; }
.icon-refresh.spinning { animation: spin 1s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

.btn-text { font-size: 10px; }

.graph-container {
  flex: 1;
  position: relative;
  overflow: hidden;
}

.graph-svg {
  width: 100%;
  height: 100%;
  display: block;
}

/* Live hint */
.live-hint {
  position: absolute;
  top: 12px;
  left: 12px;
  display: flex;
  align-items: center;
  gap: 8px;
  font-family: var(--font-mono);
  font-size: 10px;
  color: #999;
  background: rgba(255,255,255,0.9);
  padding: 6px 12px;
  border-radius: 4px;
  border: 1px solid var(--border);
}

.live-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--accent);
  animation: pulse-live 1.5s infinite;
}

@keyframes pulse-live {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}

/* Detail Panel */
.detail-panel {
  position: absolute;
  top: 12px;
  right: 12px;
  width: 260px;
  background: rgba(255,255,255,0.97);
  border: 1px solid var(--border);
  border-radius: 6px;
  box-shadow: 0 4px 16px rgba(0,0,0,0.06);
  overflow: hidden;
  animation: fadeIn 0.2s ease-out;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(4px); }
  to { opacity: 1; transform: translateY(0); }
}

.detail-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  border-bottom: 1px solid var(--border);
  background: #FAFAFA;
}

.detail-type {
  font-family: var(--font-mono);
  font-size: 8px;
  font-weight: 700;
  color: #FFF;
  padding: 2px 6px;
  border-radius: 2px;
  text-transform: uppercase;
}

.detail-name {
  font-size: 13px;
  font-weight: 600;
  flex: 1;
}

.detail-close {
  background: none;
  border: none;
  font-size: 16px;
  color: #999;
  cursor: pointer;
  line-height: 1;
}

.detail-close:hover { color: #333; }

.detail-body {
  padding: 12px;
}

.detail-row {
  display: flex;
  gap: 8px;
  font-size: 11px;
  margin-bottom: 6px;
}

.detail-label {
  color: #999;
  min-width: 65px;
}

.detail-value {
  color: #333;
}

.detail-value.mono {
  font-family: var(--font-mono);
}

.detail-value.agreed {
  color: #22c55e;
  font-weight: 600;
  font-family: var(--font-mono);
}

.detail-value.disclosed { color: #06b6d4; }
.detail-value.hidden-int { color: #999; font-style: italic; }

/* Legend */
.graph-legend {
  position: absolute;
  bottom: 12px;
  left: 12px;
  display: flex;
  gap: 16px;
  font-family: var(--font-mono);
  font-size: 9px;
  color: #999;
  background: rgba(255,255,255,0.9);
  padding: 6px 12px;
  border-radius: 4px;
  border: 1px solid var(--border);
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 4px;
}

.legend-circle {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.legend-rect {
  width: 12px;
  height: 8px;
  border-radius: 2px;
  border: 1px solid #CCC;
  background: #F5F5F5;
}

.legend-diamond {
  width: 7px;
  height: 7px;
  transform: rotate(45deg);
}

.legend-hex {
  width: 8px;
  height: 8px;
  background: #a855f733;
  border: 1px solid #a855f7;
  clip-path: polygon(50% 0%, 100% 25%, 100% 75%, 50% 100%, 0% 75%, 0% 25%);
}
</style>
