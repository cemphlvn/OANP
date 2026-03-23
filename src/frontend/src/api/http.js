import axios from 'axios'

const http = axios.create({
  baseURL: import.meta.env.VITE_OANP_BACKEND || '',
  timeout: 60000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// Response interceptor — unwrap data
http.interceptors.response.use(
  response => response.data,
  error => {
    if (error.code === 'ECONNABORTED') {
      console.error('[OANP] Request timeout')
    }
    if (error.message === 'Network Error') {
      console.error('[OANP] Network error — check backend connection')
    }
    return Promise.reject(error)
  }
)

/**
 * Retry wrapper with exponential backoff.
 */
export async function withRetry(fn, maxRetries = 3, baseDelay = 1000) {
  for (let i = 0; i < maxRetries; i++) {
    try {
      return await fn()
    } catch (error) {
      if (i === maxRetries - 1) throw error
      const delay = baseDelay * Math.pow(2, i)
      await new Promise(resolve => setTimeout(resolve, delay))
    }
  }
}

export default http
