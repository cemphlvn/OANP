import { ref } from 'vue'

/**
 * OANP WebSocket client — connects to FastAPI backend for real-time
 * negotiation event streaming. Port of lib/ws.ts to Vue 3.
 */
export class OANPWebSocket {
  constructor() {
    this.ws = null
    this.handlers = []
    this.reconnectAttempts = 0
    this.maxReconnectAttempts = 5
    this.sessionId = null
    this.status = ref('disconnected') // 'connecting' | 'connected' | 'disconnected' | 'error'
  }

  connect(sessionId) {
    this.sessionId = sessionId
    this.status.value = 'connecting'
    this._openPromiseResolve = null

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = import.meta.env.VITE_OANP_BACKEND
      ? new URL(import.meta.env.VITE_OANP_BACKEND).host
      : window.location.host
    const url = `${protocol}//${host}/ws/${sessionId}`

    this._openPromise = new Promise(resolve => {
      this._openPromiseResolve = resolve
    })

    this.ws = new WebSocket(url)

    this.ws.onopen = () => {
      this.reconnectAttempts = 0
      this.status.value = 'connected'
      if (this._openPromiseResolve) {
        this._openPromiseResolve()
        this._openPromiseResolve = null
      }
    }

    this.ws.onmessage = (event) => {
      try {
        const parsed = JSON.parse(event.data)
        this.handlers.forEach(h => h(parsed))
      } catch {
        console.error('[OANP WS] Failed to parse:', event.data)
      }
    }

    this.ws.onclose = () => {
      this.status.value = 'disconnected'
      if (this.reconnectAttempts < this.maxReconnectAttempts && this.sessionId) {
        this.reconnectAttempts++
        const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 10000)
        setTimeout(() => this.connect(this.sessionId), delay)
      }
    }

    this.ws.onerror = () => {
      this.status.value = 'error'
    }
  }

  onEvent(handler) {
    this.handlers.push(handler)
    return () => {
      this.handlers = this.handlers.filter(h => h !== handler)
    }
  }

  /**
   * Wait for the WebSocket connection to open.
   * Returns immediately if already open.
   */
  async waitForOpen() {
    if (this.ws?.readyState === WebSocket.OPEN) return
    if (this._openPromise) await this._openPromise
  }

  send(data) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data))
    } else {
      console.warn('[OANP WS] send() called but socket not open, readyState:', this.ws?.readyState)
    }
  }

  disconnect() {
    this.maxReconnectAttempts = 0
    this.ws?.close()
    this.ws = null
    this.status.value = 'disconnected'
  }
}
