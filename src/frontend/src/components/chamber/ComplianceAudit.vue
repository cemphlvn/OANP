<template>
  <div class="compliance-audit">
    <!-- Institutional Framework -->
    <div class="ca-section">
      <div class="ca-section-title">INSTITUTIONAL FRAMEWORK</div>
      <div class="ca-grid">
        <div class="ca-kv">
          <span class="ca-key">Institution</span>
          <span class="ca-val">{{ institutionDisplay }}</span>
        </div>
        <div class="ca-kv">
          <span class="ca-key">Procedure</span>
          <span class="ca-val">{{ procedureDisplay }}</span>
        </div>
        <div class="ca-kv">
          <span class="ca-key">Seat</span>
          <span class="ca-val">{{ compliance?.institution?.seat || 'Not specified' }}</span>
        </div>
        <div class="ca-kv">
          <span class="ca-key">Governing Law</span>
          <span class="ca-val">{{ compliance?.institution?.governing_law || 'Not specified' }}</span>
        </div>
        <div class="ca-kv">
          <span class="ca-key">Language</span>
          <span class="ca-val">{{ compliance?.institution?.language || 'English' }}</span>
        </div>
      </div>
    </div>

    <!-- Escalation History -->
    <div class="ca-section">
      <div class="ca-section-title">ESCALATION HISTORY</div>
      <div v-if="!tierHistory || tierHistory.length === 0" class="ca-empty">
        No escalations &mdash; resolved at initial tier
      </div>
      <table v-else class="ca-table">
        <thead>
          <tr>
            <th>Round</th>
            <th>From</th>
            <th>To</th>
            <th>Reason</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(evt, i) in tierHistory" :key="i">
            <td>{{ evt.round || evt.at_round || '?' }}</td>
            <td>{{ TIER_LABELS[evt.from_tier || evt.old_tier] || '?' }}</td>
            <td>{{ TIER_LABELS[evt.to_tier || evt.new_tier] || '?' }}</td>
            <td>{{ evt.reason || '&mdash;' }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Due Process Audit Trail -->
    <div class="ca-section">
      <div class="ca-section-title">DUE PROCESS AUDIT TRAIL</div>
      <div v-if="logEntries.length === 0" class="ca-empty">No log entries recorded</div>
      <table v-else class="ca-table">
        <thead>
          <tr>
            <th>Round</th>
            <th>Party</th>
            <th>Event</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(entry, i) in logEntries" :key="i" :class="{ 'ca-row-alt': i % 2 === 1 }">
            <td>{{ entry.round || '?' }}</td>
            <td>{{ entry.party || '&mdash;' }}</td>
            <td>{{ entry.event || entry.message || entry }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Compliance Checklist -->
    <div class="ca-section">
      <div class="ca-section-title">COMPLIANCE CHECKLIST</div>
      <div class="ca-checklist">
        <div
          v-for="item in checklistItems"
          :key="item.label"
          class="ca-check-row"
        >
          <span class="ca-check-icon" :class="item.pass ? 'pass' : 'fail'">
            {{ item.pass ? '\u2713' : '\u2717' }}
          </span>
          <span class="ca-check-label">{{ item.label }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { INSTITUTION_LABELS, PROCEDURE_LABELS, TIER_LABELS } from '@/types/protocol'

const props = defineProps({
  compliance: { type: Object, default: () => ({}) },
  award: { type: Object, default: null },
  tierHistory: { type: Array, default: () => [] },
  parties: { type: Array, default: () => [] }
})

const institutionDisplay = computed(() => {
  const code = props.compliance?.institution?.code
  if (!code) return 'Not specified'
  return INSTITUTION_LABELS[code] || code
})

const procedureDisplay = computed(() => {
  const proc = props.compliance?.institution?.procedure
  if (!proc) return 'Standard'
  return PROCEDURE_LABELS[proc] || proc
})

const logEntries = computed(() => {
  const log = props.compliance?.due_process_log || []
  return log.slice(-50)
})

const checklistItems = computed(() => {
  const c = props.compliance || {}
  const totalRounds = c.total_rounds || c.round || 0
  const hardDeadline = c.hard_deadline || 20

  return [
    {
      label: 'Equal participation maintained',
      pass: c.participation_balanced !== false
    },
    {
      label: 'Phase deadlines respected',
      pass: c.phase_deadlines_exceeded !== true
    },
    {
      label: 'Hard deadline not exceeded',
      pass: totalRounds <= hardDeadline
    },
    {
      label: 'Escalation policy followed',
      pass: c.escalation_violations == null || c.escalation_violations === 0
    }
  ]
})
</script>

<style scoped>
.compliance-audit {
  font-family: var(--font-body);
  max-width: 900px;
}

.ca-section {
  padding: 20px 0;
  border-bottom: 1px solid #EEE;
}

.ca-section:last-child {
  border-bottom: none;
}

.ca-section-title {
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 1.5px;
  color: #AAA;
  margin-bottom: 14px;
}

.ca-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px 24px;
}

.ca-kv {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.ca-key {
  font-family: var(--font-mono);
  font-size: 10px;
  color: #AAA;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.ca-val {
  font-family: var(--font-mono);
  font-size: 12px;
  color: #333;
  font-weight: 600;
}

.ca-empty {
  font-size: 12px;
  color: #999;
  font-style: italic;
}

.ca-table {
  width: 100%;
  border-collapse: collapse;
  font-family: var(--font-mono);
  font-size: 11px;
}

.ca-table th {
  text-align: left;
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 0.5px;
  color: #AAA;
  text-transform: uppercase;
  padding: 6px 8px;
  border-bottom: 1px solid #EEE;
}

.ca-table td {
  padding: 6px 8px;
  color: #555;
  vertical-align: top;
}

.ca-row-alt {
  background: #FAFAFA;
}

.ca-checklist {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.ca-check-row {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 12px;
}

.ca-check-icon {
  font-family: var(--font-mono);
  font-size: 14px;
  font-weight: 700;
  width: 20px;
  text-align: center;
}

.ca-check-icon.pass {
  color: #22c55e;
}

.ca-check-icon.fail {
  color: #ef4444;
}

.ca-check-label {
  color: #555;
}
</style>
