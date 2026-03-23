<template>
  <div class="main-view">
    <header class="app-header">
      <div class="header-left">
        <div class="brand" @click="$router.push('/')">OANP</div>
      </div>
      <div class="header-center">
        <div class="view-switcher">
          <button
            v-for="mode in ['graph', 'split', 'workbench']"
            :key="mode"
            class="switch-btn"
            :class="{ active: viewMode === mode }"
            @click="viewMode = mode"
          >
            {{ { graph: 'Graph', split: 'Split', workbench: 'Workbench' }[mode] }}
          </button>
        </div>
      </div>
      <div class="header-right">
        <div class="workflow-step">
          <span class="step-num-h">Step 4/4</span>
          <span class="step-name-h">Deep Dive</span>
        </div>
      </div>
    </header>

    <main class="content-area">
      <div class="panel-wrapper" style="width: 100%; opacity: 1;">
        <div class="explore-panel">
          <div class="explore-placeholder">
            <span class="placeholder-text">Deep Dive & Replay</span>
            <span class="placeholder-sub">X-Ray party states, move replay, comparison tools</span>
            <span class="placeholder-sub">Implementation in Phase 5</span>
            <button class="back-btn" @click="$router.push({ name: 'Analysis', params: { sessionId } })">
              ← Back to Analysis
            </button>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const props = defineProps({ sessionId: String })
const viewMode = ref('workbench')
</script>

<style scoped>
.main-view {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: #FFF;
  overflow: hidden;
  font-family: var(--font-heading);
}

.app-header {
  height: 60px;
  border-bottom: 1px solid var(--border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  background: #FFF;
  z-index: 100;
  position: relative;
  flex-shrink: 0;
}

.header-center { position: absolute; left: 50%; transform: translateX(-50%); }
.brand { font-family: var(--font-mono); font-weight: 800; font-size: 18px; letter-spacing: 1px; cursor: pointer; }
.view-switcher { display: flex; background: #F5F5F5; padding: 4px; border-radius: 6px; gap: 4px; }
.switch-btn { border: none; background: transparent; padding: 6px 16px; font-size: 12px; font-weight: 600; color: #666; border-radius: 4px; cursor: pointer; transition: all 0.2s; }
.switch-btn.active { background: #FFF; color: #000; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
.header-right { display: flex; align-items: center; gap: 16px; }
.workflow-step { display: flex; align-items: center; gap: 8px; font-size: 14px; }
.step-num-h { font-family: var(--font-mono); font-weight: 700; color: #999; }
.step-name-h { font-weight: 700; color: #000; }

.content-area { flex: 1; display: flex; overflow: hidden; }
.panel-wrapper { height: 100%; overflow: hidden; }

.explore-panel { height: 100%; display: flex; align-items: center; justify-content: center; background: #FAFAFA; }

.explore-placeholder {
  text-align: center;
  color: #999;
}

.placeholder-text {
  display: block;
  font-family: var(--font-mono);
  font-size: 1.5rem;
  font-weight: 700;
  margin-bottom: 8px;
  color: #CCC;
}

.placeholder-sub {
  display: block;
  font-family: var(--font-mono);
  font-size: 0.8rem;
  margin-bottom: 4px;
}

.back-btn {
  margin-top: 24px;
  background: #000;
  color: #FFF;
  border: none;
  padding: 10px 24px;
  font-family: var(--font-mono);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  border-radius: 4px;
}

.back-btn:hover { opacity: 0.8; }
</style>
