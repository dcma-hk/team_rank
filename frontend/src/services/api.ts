import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 10000,
})

// Types
export interface Member {
  alias: string
  role: string
}

export interface Metric {
  id: string
  name: string
  weights_by_role: Record<string, number>
  min_value: number
  max_value: number
}

export interface RankingEntry {
  alias: string
  role: string
  weighted_score: number
  rank: number
  expected_rank?: number
  mismatch: boolean
}

export interface ScoreAdjustmentPreview {
  proposed: Record<string, number>
  achieved_weighted_score: number
  hit_clamps: string[]
}

export interface ScoreAdjustmentRequest {
  alias: string
  selected_metrics: string[]
  percent: number
}

export interface ScoreAdjustmentApply {
  alias: string
  changes: Record<string, number>
}

export interface PercentileBucket {
  pct: number
  by_role: Record<string, Array<{ alias: string; weightedScore?: number; rank?: number }>>
}

// API functions
export const apiService = {
  // GET endpoints
  async getRoles(): Promise<{ roles: string[]; countsByRole: Record<string, number> }> {
    const response = await api.get('/roles')
    return response.data
  },

  async getMembers(): Promise<Member[]> {
    const response = await api.get('/members')
    return response.data
  },

  async getMetrics(): Promise<Metric[]> {
    const response = await api.get('/metrics')
    return response.data
  },

  async getScores(): Promise<{
    metrics: string[]
    members: string[]
    scores: Record<string, Record<string, number>>
  }> {
    const response = await api.get('/scores')
    return response.data
  },

  async getRankings(roles?: string[]): Promise<RankingEntry[]> {
    const params = roles ? { roles: roles.join(',') } : {}
    const response = await api.get('/rankings', { params })
    return response.data
  },

  async getMismatches(): Promise<RankingEntry[]> {
    const response = await api.get('/mismatches')
    return response.data
  },

  async getPercentiles(basis: 'weighted' | 'rank' = 'weighted'): Promise<{
    buckets: PercentileBucket[]
  }> {
    const response = await api.get('/percentiles', { params: { basis } })
    return response.data
  },

  // POST endpoints
  async previewAdjustment(request: ScoreAdjustmentRequest): Promise<ScoreAdjustmentPreview> {
    const response = await api.post('/adjust/preview', request)
    return response.data
  },

  async applyAdjustment(request: ScoreAdjustmentApply): Promise<{
    ok: boolean
    updatedAt: string
    rankings: RankingEntry[]
  }> {
    const response = await api.post('/adjust/apply', request)
    return response.data
  },
}

export default apiService
