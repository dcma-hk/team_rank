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
  snapshot?: string
}

export interface PercentileBucket {
  pct: number
  by_role: Record<string, Array<{ alias: string; weightedScore?: number; rank?: number }>>
}

export interface SnapshotInfo {
  current_snapshot: string
  available_snapshots: string[]
}

export interface ExpectedRankingUpdate {
  alias: string
  rank: number
}

export interface RoleUpdate {
  alias: string
  role: string
}

export interface BulkExpectedRankingUpdate {
  rankings: ExpectedRankingUpdate[]
}

export interface BulkRoleUpdate {
  roles: RoleUpdate[]
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

  async getScores(snapshot?: string): Promise<{
    metrics: string[]
    members: string[]
    scores: Record<string, Record<string, number>>
    current_snapshot?: string
    available_snapshots?: string[]
    requested_snapshot?: string
  }> {
    const params = snapshot ? { snapshot } : {}
    const response = await api.get('/scores', { params })
    return response.data
  },

  async getRankings(roles?: string[], snapshot?: string): Promise<RankingEntry[]> {
    const params: Record<string, string> = {}
    if (roles) params.roles = roles.join(',')
    if (snapshot) params.snapshot = snapshot
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

  async getSnapshots(): Promise<SnapshotInfo> {
    const response = await api.get('/snapshots')
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

  async uploadExcelData(file: File, snapshot: string): Promise<{
    ok: boolean
    message: string
    snapshot: string
    records_processed: number
    updated_at: string
  }> {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('snapshot', snapshot)

    const response = await api.post('/upload/excel', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return response.data
  },

  async updateExpectedRankings(request: BulkExpectedRankingUpdate): Promise<{
    ok: boolean
    message: string
    updated_count: number
    updated_at: string
  }> {
    const response = await api.post('/update/expected-rankings', request)
    return response.data
  },

  async updateRoles(request: BulkRoleUpdate): Promise<{
    ok: boolean
    message: string
    updated_count: number
    updated_at: string
  }> {
    const response = await api.post('/update/roles', request)
    return response.data
  },


}

export default apiService
