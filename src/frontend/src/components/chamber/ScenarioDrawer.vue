<template>
  <div class="scenario-drawer" :class="{ open }">
    <button class="sd-toggle" @click="open = !open">
      <span class="sd-toggle-icon">{{ open ? '&#9660;' : '&#9654;' }}</span>
      <span class="sd-toggle-text">Scenario Details</span>
      <span class="sd-toggle-meta">{{ parties.length }} parties · {{ issues.length }} issues</span>
    </button>

    <Transition name="drawer">
      <div v-if="open" class="sd-content">
        <div class="sd-grid">
          <!-- Parties -->
          <div class="sd-section">
            <div class="sd-section-title">PARTIES</div>
            <div v-for="(party, idx) in parties" :key="party.id" class="sd-party">
              <div class="sd-party-header">
                <span class="sd-party-dot" :style="{ background: PARTY_COLORS[idx] || '#999' }"></span>
                <span class="sd-party-name">{{ party.name }}</span>
                <span class="sd-party-role">{{ party.role }}</span>
              </div>
            </div>
          </div>

          <!-- Issues -->
          <div class="sd-section">
            <div class="sd-section-title">ISSUES</div>
            <div v-for="issue in issues" :key="issue.id" class="sd-issue">
              <span class="sd-issue-name">{{ issue.name }}</span>
              <span class="sd-issue-type">{{ issue.type }}</span>
              <span class="sd-issue-range" v-if="issue.range">{{ issue.range[0] }}–{{ issue.range[1] }}</span>
              <span class="sd-issue-range" v-else-if="issue.options">{{ issue.options.join(' / ') }}</span>
            </div>
          </div>

          <!-- Criteria -->
          <div class="sd-section" v-if="criteria.length">
            <div class="sd-section-title">CRITERIA</div>
            <div v-for="c in criteria" :key="c.name" class="sd-criterion">
              <span class="sd-crit-name">{{ c.name }}</span>
              <span class="sd-crit-source">[{{ c.source }}]</span>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { PARTY_COLORS } from '@/types/protocol'

defineProps({
  parties: { type: Array, default: () => [] },
  issues: { type: Array, default: () => [] },
  criteria: { type: Array, default: () => [] }
})

const open = ref(false)
</script>

<style scoped>
.scenario-drawer {
  border-bottom: 1px solid var(--border);
  background: #FAFAFA;
  flex-shrink: 0;
  position: relative;
  z-index: 30;
}

.sd-toggle {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 20px;
  background: none;
  border: none;
  cursor: pointer;
  font-size: 11px;
  color: #888;
  transition: all 0.15s;
}

.sd-toggle:hover { color: #333; background: #F0F0F0; }

.sd-toggle-icon { font-size: 8px; width: 12px; }
.sd-toggle-text { font-weight: 600; font-family: var(--font-mono); font-size: 10px; letter-spacing: 0.5px; }
.sd-toggle-meta { font-family: var(--font-mono); font-size: 10px; margin-left: auto; }

.sd-content {
  padding: 0 20px 12px;
  overflow: hidden;
}

.sd-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
}

.sd-section-title {
  font-family: var(--font-mono);
  font-size: 9px;
  font-weight: 700;
  color: #BBB;
  letter-spacing: 1px;
  margin-bottom: 8px;
}

.sd-party {
  margin-bottom: 6px;
}

.sd-party-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
}

.sd-party-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.sd-party-name { font-weight: 600; }
.sd-party-role { font-family: var(--font-mono); font-size: 10px; color: #999; }

.sd-issue {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 11px;
  margin-bottom: 4px;
}

.sd-issue-name { font-weight: 500; }

.sd-issue-type {
  font-family: var(--font-mono);
  font-size: 9px;
  color: #999;
  background: #F5F5F5;
  padding: 1px 5px;
  border-radius: 2px;
}

.sd-issue-range { font-family: var(--font-mono); font-size: 10px; color: #888; }

.sd-criterion {
  display: flex;
  gap: 6px;
  font-size: 11px;
  margin-bottom: 3px;
}

.sd-crit-name { color: #444; }
.sd-crit-source { font-family: var(--font-mono); font-size: 9px; color: #BBB; }

/* Transition */
.drawer-enter-active { transition: all 0.25s ease-out; }
.drawer-enter-from { max-height: 0; opacity: 0; }
.drawer-enter-to { max-height: 300px; opacity: 1; }
.drawer-leave-active { transition: all 0.2s ease-in; }
.drawer-leave-from { max-height: 300px; opacity: 1; }
.drawer-leave-to { max-height: 0; opacity: 0; }
</style>
