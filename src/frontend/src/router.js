import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: () => import('@/views/HomeView.vue')
  },
  {
    path: '/session/:sessionId',
    name: 'Session',
    component: () => import('@/views/SessionView.vue'),
    props: true
  },
  {
    path: '/session/:sessionId/negotiate',
    name: 'Negotiate',
    component: () => import('@/views/NegotiateView.vue'),
    props: true
  },
  {
    path: '/session/:sessionId/analysis',
    name: 'Analysis',
    component: () => import('@/views/AnalysisView.vue'),
    props: true
  },
  {
    path: '/session/:sessionId/explore',
    name: 'Explore',
    component: () => import('@/views/ExploreView.vue'),
    props: true
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
