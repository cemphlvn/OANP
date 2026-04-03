<template>
  <div class="dispute-config">
    <!-- Mode Selection -->
    <div class="dc-modes">
      <div
        class="dc-mode-card"
        :class="{ active: modelValue.mode === 'streamlined' }"
        @click="update('mode', 'streamlined')"
      >
        <div class="dc-mode-label">Quick Resolve</div>
        <div class="dc-mode-desc">Fast, principled negotiation. No legal overhead.</div>
      </div>
      <div
        class="dc-mode-card"
        :class="{ active: modelValue.mode === 'advanced' }"
        @click="update('mode', 'advanced')"
      >
        <div class="dc-mode-label">Formal Procedure</div>
        <div class="dc-mode-desc">Institutional rules, deadlines, enforceable awards.</div>
      </div>
    </div>

    <!-- Advanced Config -->
    <Transition name="expand">
      <div v-if="modelValue.mode === 'advanced'" class="dc-advanced">
        <div class="dc-form-grid">
          <div class="dc-field">
            <label class="dc-label">INSTITUTION</label>
            <select
              class="dc-select"
              :value="modelValue.institution?.code"
              @change="updateInstitution('code', $event.target.value)"
            >
              <option value="" disabled>Select institution...</option>
              <option
                v-for="inst in institutions"
                :key="inst.code"
                :value="inst.code"
              >{{ INSTITUTION_LABELS[inst.code] || inst.code }} &mdash; {{ inst.name }}</option>
            </select>
          </div>
          <div class="dc-field">
            <label class="dc-label">PROCEDURE</label>
            <select
              class="dc-select"
              :value="modelValue.institution?.procedure || 'standard'"
              @change="updateInstitution('procedure', $event.target.value)"
            >
              <option v-for="(label, key) in PROCEDURE_LABELS" :key="key" :value="key">
                {{ label }}
              </option>
            </select>
          </div>
          <div class="dc-field">
            <label class="dc-label">SEAT</label>
            <input
              class="dc-input"
              type="text"
              placeholder="e.g. London, UK"
              :value="modelValue.institution?.seat || ''"
              @input="updateInstitution('seat', $event.target.value)"
            />
          </div>
          <div class="dc-field">
            <label class="dc-label">GOVERNING LAW</label>
            <input
              class="dc-input"
              type="text"
              placeholder="e.g. English law"
              :value="modelValue.institution?.governing_law || ''"
              @input="updateInstitution('governing_law', $event.target.value)"
            />
          </div>
        </div>

        <!-- Escalation Path -->
        <div class="dc-escalation">
          <div class="dc-label" style="margin-bottom: 12px;">ESCALATION PATH</div>
          <ProcessTimeline
            :tiers="ESCALATION_TIERS"
            :current-tier="ESCALATION_TIERS[0]"
            :tier-limits="modelValue.escalation?.tier_limits || { negotiation: 10, mediation: 6, arbitration: 4 }"
            :hard-deadline="modelValue.escalation?.hard_deadline || 20"
          />
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { INSTITUTION_LABELS, PROCEDURE_LABELS, ESCALATION_TIERS } from '@/types/protocol'
import ProcessTimeline from './ProcessTimeline.vue'

const props = defineProps({
  modelValue: {
    type: Object,
    default: () => ({ mode: 'streamlined', institution: {}, escalation: {} })
  },
  institutions: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['update:modelValue'])

function update(key, value) {
  emit('update:modelValue', { ...props.modelValue, [key]: value })
}

function updateInstitution(key, value) {
  const inst = { ...(props.modelValue.institution || {}), [key]: value }
  emit('update:modelValue', { ...props.modelValue, institution: inst })
}
</script>

<style scoped>
.dispute-config {
  font-family: var(--font-body);
}

.dc-modes {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-bottom: 16px;
}

.dc-mode-card {
  border: 1px solid #EEE;
  border-radius: 8px;
  padding: 16px;
  cursor: pointer;
  background: #FAFAFA;
  transition: all 0.15s;
}

.dc-mode-card:hover {
  border-color: #CCC;
}

.dc-mode-card.active {
  border-color: #000;
  background: #FFF;
  box-shadow: 0 0 0 1px #000;
}

.dc-mode-label {
  font-family: var(--font-heading);
  font-weight: 700;
  font-size: 14px;
  margin-bottom: 4px;
}

.dc-mode-desc {
  font-size: 12px;
  color: #888;
  line-height: 1.4;
}

.dc-advanced {
  border: 1px solid #EEE;
  border-radius: 8px;
  padding: 20px;
  background: #FAFAFA;
}

.dc-form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
  margin-bottom: 20px;
}

.dc-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.dc-label {
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 600;
  color: #AAA;
  letter-spacing: 1px;
}

.dc-select,
.dc-input {
  font-family: var(--font-mono);
  font-size: 12px;
  padding: 8px 10px;
  border: 1px solid #DDD;
  border-radius: 4px;
  background: #FFF;
  color: #000;
  outline: none;
  transition: border-color 0.15s;
}

.dc-select:focus,
.dc-input:focus {
  border-color: #000;
}

.dc-escalation {
  border-top: 1px solid #EEE;
  padding-top: 16px;
}

/* Expand transition */
.expand-enter-active {
  transition: all 0.3s ease;
  overflow: hidden;
}
.expand-enter-from {
  opacity: 0;
  max-height: 0;
  margin-top: 0;
}
.expand-leave-active {
  transition: all 0.2s ease;
  overflow: hidden;
}
.expand-leave-to {
  opacity: 0;
  max-height: 0;
}
</style>
