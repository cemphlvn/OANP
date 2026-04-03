<template>
  <div class="award-document">
    <div class="ad-page">
      <!-- Pre-formatted text mode -->
      <pre v-if="formattedText" class="ad-preformatted">{{ formattedText }}</pre>

      <!-- Structured document mode -->
      <template v-else-if="award">
        <!-- Header -->
        <div class="ad-header-rule"></div>
        <div class="ad-title">{{ awardTypeLabel }}</div>
        <div class="ad-header-rule"></div>

        <!-- Institutional Info -->
        <div v-if="award.institution" class="ad-meta-section">
          <div class="ad-meta-line">Administered under: {{ institutionName }} Rules</div>
          <div v-if="award.procedure" class="ad-meta-line">Procedure: {{ procedureName }}</div>
        </div>

        <!-- Date, Seat, Governing Law -->
        <div class="ad-meta-section">
          <div v-if="award.date || award.issued_at" class="ad-meta-line">
            Date: {{ award.date || award.issued_at }}
          </div>
          <div v-if="award.seat" class="ad-meta-line">Seat: {{ award.seat }}</div>
          <div v-if="award.governing_law" class="ad-meta-line">
            Governing Law: {{ award.governing_law }}
          </div>
        </div>

        <div class="ad-rule"></div>

        <!-- Parties -->
        <div class="ad-section">
          <div class="ad-section-heading">PARTIES</div>
          <div
            v-for="party in (award.parties || [])"
            :key="party.name || party"
            class="ad-party-line"
          >
            <span class="ad-party-name">{{ party.name || party }}</span>
            <span v-if="party.role" class="ad-party-role">({{ party.role }})</span>
          </div>
        </div>

        <div class="ad-rule"></div>

        <!-- Terms -->
        <div class="ad-section">
          <div class="ad-section-heading">TERMS</div>
          <div
            v-for="(val, key) in (award.terms || award.issue_values || {})"
            :key="key"
            class="ad-term-line"
          >
            <span class="ad-term-key">{{ key }}:</span>
            <span class="ad-term-val">{{ val }}</span>
          </div>
        </div>

        <div class="ad-rule"></div>

        <!-- Reasons -->
        <div v-if="award.reasons" class="ad-section">
          <div class="ad-section-heading">REASONS</div>
          <div class="ad-reasons-text">{{ award.reasons }}</div>
        </div>

        <div v-if="award.reasons" class="ad-rule"></div>

        <!-- Signatures -->
        <div v-if="award.signatures && award.signatures.length" class="ad-section">
          <div class="ad-section-heading">SIGNATURES</div>
          <div
            v-for="(sig, i) in award.signatures"
            :key="i"
            class="ad-sig-block"
          >
            <div class="ad-sig-party">{{ sig.party || sig.name }}</div>
            <div class="ad-sig-detail" v-if="sig.timestamp">Signed: {{ sig.timestamp }}</div>
            <div class="ad-sig-detail" v-if="sig.method">Method: {{ sig.method }}</div>
          </div>
        </div>

        <div v-if="award.signatures && award.signatures.length" class="ad-rule"></div>

        <!-- Integrity Verification -->
        <div v-if="award.hash || award.integrity" class="ad-section">
          <div class="ad-section-heading">INTEGRITY VERIFICATION</div>
          <div class="ad-hash-block">
            <div v-if="award.hash" class="ad-hash-line">
              SHA-256: {{ award.hash }}
            </div>
            <div v-if="award.integrity?.document_hash" class="ad-hash-line">
              Document: {{ award.integrity.document_hash }}
            </div>
            <div v-if="award.integrity?.chain_hash" class="ad-hash-line">
              Chain: {{ award.integrity.chain_hash }}
            </div>
          </div>
        </div>
      </template>

      <div v-else class="ad-empty">No award data available</div>
    </div>

    <!-- Award Compliance Checklist -->
    <div v-if="award" class="ad-checklist-section">
      <div class="ad-checklist-title">AWARD COMPLIANCE CHECKLIST</div>
      <div class="ad-checklist">
        <div
          v-for="item in complianceChecklist"
          :key="item.label"
          class="ad-check-row"
        >
          <span class="ad-check-icon" :class="item.pass ? 'pass' : 'fail'">
            {{ item.pass ? '\u2713' : '\u2717' }}
          </span>
          <span class="ad-check-label">{{ item.label }}</span>
          <span class="ad-check-standard">{{ item.standard }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { AWARD_TYPES, INSTITUTION_LABELS, PROCEDURE_LABELS } from '@/types/protocol'

const props = defineProps({
  award: { type: Object, default: null },
  formattedText: { type: String, default: '' }
})

const awardTypeLabel = computed(() => {
  const t = props.award?.award_type || props.award?.type || 'consent_award'
  return AWARD_TYPES[t] || t.replace(/_/g, ' ').toUpperCase()
})

const institutionName = computed(() => {
  const code = props.award?.institution?.code || props.award?.institution
  if (!code) return 'Ad Hoc'
  return INSTITUTION_LABELS[code] || code
})

const procedureName = computed(() => {
  const proc = props.award?.procedure
  if (!proc) return null
  return PROCEDURE_LABELS[proc] || proc
})

const complianceChecklist = computed(() => {
  const a = props.award || {}
  return [
    {
      label: 'Parties identified',
      pass: !!(a.parties && a.parties.length > 0),
      standard: 'NYC Art. V(1)(a)'
    },
    {
      label: 'Seat stated',
      pass: !!a.seat,
      standard: 'NYC Art. V(1)(e)'
    },
    {
      label: 'Governing law stated',
      pass: !!a.governing_law,
      standard: 'UNCITRAL Art. 34(2)'
    },
    {
      label: 'Terms specified',
      pass: !!(a.terms || a.issue_values),
      standard: 'NYC Art. IV(1)'
    },
    {
      label: 'Reasons stated',
      pass: !!a.reasons,
      standard: 'UNCITRAL Art. 31(2)'
    },
    {
      label: 'Signatures present',
      pass: !!(a.signatures && a.signatures.length > 0),
      standard: 'NYC Art. IV(1)(a)'
    },
    {
      label: 'Date of award',
      pass: !!(a.date || a.issued_at),
      standard: 'SC s.52(2)(b)'
    },
    {
      label: 'Integrity hash recorded',
      pass: !!(a.hash || a.integrity),
      standard: 'Digital verification'
    }
  ]
})
</script>

<style scoped>
.award-document {
  display: flex;
  flex-direction: column;
  align-items: center;
  font-family: var(--font-mono);
}

.ad-page {
  background: #FFF;
  max-width: 800px;
  width: 100%;
  padding: 48px 56px;
  border: 1px solid #EEE;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
  line-height: 1.7;
  font-size: 12px;
  color: #222;
}

.ad-preformatted {
  white-space: pre-wrap;
  word-break: break-word;
  font-family: var(--font-mono);
  font-size: 12px;
  line-height: 1.7;
  margin: 0;
  color: #222;
}

.ad-header-rule {
  border: none;
  border-top: 3px double #000;
  margin: 8px 0;
}

.ad-title {
  text-align: center;
  font-size: 16px;
  font-weight: 800;
  letter-spacing: 3px;
  padding: 12px 0;
  text-transform: uppercase;
}

.ad-meta-section {
  margin: 16px 0;
}

.ad-meta-line {
  font-size: 11px;
  color: #555;
  margin-bottom: 4px;
}

.ad-rule {
  border: none;
  border-top: 1px solid #DDD;
  margin: 20px 0;
}

.ad-section {
  margin: 16px 0;
}

.ad-section-heading {
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 1.5px;
  color: #000;
  margin-bottom: 12px;
  text-transform: uppercase;
}

.ad-party-line {
  margin-bottom: 4px;
}

.ad-party-name {
  font-weight: 700;
}

.ad-party-role {
  color: #888;
  margin-left: 6px;
  font-size: 11px;
}

.ad-term-line {
  display: flex;
  gap: 12px;
  margin-bottom: 4px;
  padding: 4px 0;
  border-bottom: 1px dotted #EEE;
}

.ad-term-key {
  color: #888;
  min-width: 160px;
}

.ad-term-val {
  font-weight: 600;
  color: #000;
}

.ad-reasons-text {
  font-size: 11px;
  color: #444;
  line-height: 1.8;
  white-space: pre-wrap;
}

.ad-sig-block {
  margin-bottom: 12px;
  padding-left: 12px;
  border-left: 2px solid #EEE;
}

.ad-sig-party {
  font-weight: 700;
  margin-bottom: 2px;
}

.ad-sig-detail {
  font-size: 10px;
  color: #888;
}

.ad-hash-block {
  background: #F9F9F9;
  border: 1px solid #EEE;
  border-radius: 4px;
  padding: 12px;
}

.ad-hash-line {
  font-size: 10px;
  color: #666;
  word-break: break-all;
  margin-bottom: 4px;
}

.ad-hash-line:last-child {
  margin-bottom: 0;
}

.ad-empty {
  color: #999;
  font-style: italic;
  text-align: center;
  padding: 40px 0;
}

/* Compliance Checklist */
.ad-checklist-section {
  max-width: 800px;
  width: 100%;
  margin-top: 24px;
  padding: 20px 0;
}

.ad-checklist-title {
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 1.5px;
  color: #AAA;
  margin-bottom: 14px;
}

.ad-checklist {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.ad-check-row {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 12px;
  padding: 6px 0;
  border-bottom: 1px solid #F5F5F5;
}

.ad-check-icon {
  font-size: 14px;
  font-weight: 700;
  width: 20px;
  text-align: center;
}

.ad-check-icon.pass {
  color: #22c55e;
}

.ad-check-icon.fail {
  color: #ef4444;
}

.ad-check-label {
  flex: 1;
  color: #555;
}

.ad-check-standard {
  font-family: var(--font-mono);
  font-size: 10px;
  color: #BBB;
}
</style>
