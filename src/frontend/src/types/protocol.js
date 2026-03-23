/**
 * Protocol constants — mirrors backend src/protocol/types.py
 */

export const PHASES = [
  'setup',
  'alignment',
  'discovery',
  'generation',
  'bargaining',
  'convergence',
  'settlement',
  'impasse',
  'arbitration'
]

export const MOVE_TYPES = [
  'propose',
  'counter',
  'argue',
  'disclose_interest',
  'invoke_criterion',
  'meso',
  'accept',
  'reject',
  'invoke_batna',
  'request_mediation'
]

export const PHASE_COLORS = {
  setup: '#737373',
  alignment: '#737373',
  discovery: '#06b6d4',
  generation: '#a855f7',
  bargaining: '#f59e0b',
  convergence: '#3b82f6',
  settlement: '#22c55e',
  impasse: '#ef4444',
  arbitration: '#737373'
}

export const PHASE_LABELS = {
  setup: 'Setup',
  alignment: 'Alignment',
  discovery: 'Discovery',
  generation: 'Generation',
  bargaining: 'Bargaining',
  convergence: 'Convergence',
  settlement: 'Settlement',
  impasse: 'Impasse',
  arbitration: 'Arbitration'
}

export const MOVE_LABELS = {
  propose: 'Proposal',
  counter: 'Counter',
  argue: 'Argument',
  disclose_interest: 'Interest Disclosed',
  invoke_criterion: 'Criterion Invoked',
  meso: 'Multiple Offers',
  accept: 'Accepted',
  reject: 'Rejected',
  invoke_batna: 'Walked Away',
  request_mediation: 'Requested Mediation'
}

export const MOVE_COLORS = {
  propose: '#3b82f6',
  counter: '#8b5cf6',
  argue: '#f59e0b',
  disclose_interest: '#06b6d4',
  invoke_criterion: '#a855f7',
  meso: '#6366f1',
  accept: '#22c55e',
  reject: '#ef4444',
  invoke_batna: '#f59e0b',
  request_mediation: '#d946ef'
}

export const INTEREST_TYPE_COLORS = {
  need: '#06b6d4',
  desire: '#3b82f6',
  fear: '#ef4444',
  concern: '#f59e0b'
}

export const PARTY_COLORS = ['#3b82f6', '#d946ef', '#f59e0b', '#06b6d4', '#22c55e']

export const MEDIATOR_COLOR = '#22c55e'

/** Legal moves per phase */
export const LEGAL_MOVES = {
  discovery: ['disclose_interest', 'propose'],
  generation: ['propose', 'meso', 'disclose_interest'],
  bargaining: ['propose', 'counter', 'argue', 'invoke_criterion', 'accept', 'reject', 'invoke_batna', 'meso'],
  convergence: ['propose', 'counter', 'argue', 'invoke_criterion', 'accept', 'reject'],
  impasse: ['request_mediation', 'invoke_batna']
}

/** Event types from WebSocket */
export const EVENT_TYPES = [
  'phase_change',
  'move',
  'mediator_note',
  'settlement',
  'impasse',
  'turn_request',
  'anchors_generated',
  'anchors_failed',
  'validation_error',
  'error'
]
