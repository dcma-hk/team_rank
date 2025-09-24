import React, { useState, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  Box,
  Paper,
  Typography,
  Button,
  ButtonGroup,
  Tooltip,
  CircularProgress,
  Alert,
} from '@mui/material'
import { DataGrid, GridColDef, GridRowParams } from '@mui/x-data-grid'
import apiService, { RankingEntry, Metric } from '../services/api'

const StackRankTable: React.FC = () => {
  const navigate = useNavigate()
  const [selectedRole, setSelectedRole] = useState<string | null>(null)

  // Fetch data
  const { data: rolesData, isLoading: rolesLoading } = useQuery({
    queryKey: ['roles'],
    queryFn: apiService.getRoles,
  })

  const { data: metrics, isLoading: metricsLoading } = useQuery({
    queryKey: ['metrics'],
    queryFn: apiService.getMetrics,
  })

  const { data: rankings, isLoading: rankingsLoading, error: rankingsError } = useQuery({
    queryKey: ['rankings', selectedRole],
    queryFn: () => apiService.getRankings(selectedRole ? [selectedRole] : undefined),
  })

  const { data: scoresData, isLoading: scoresLoading } = useQuery({
    queryKey: ['scores'],
    queryFn: apiService.getScores,
  })

  const isLoading = rolesLoading || metricsLoading || rankingsLoading || scoresLoading

  // Handle role selection
  const handleRoleChange = (role: string | null) => {
    setSelectedRole(role)
  }

  // Create metric columns with tooltips - only show metrics applicable to selected role
  const metricColumns: GridColDef[] = useMemo(() => {
    if (!metrics || !scoresData) return []

    // If no role is selected, show all metrics
    if (!selectedRole) {
      return metrics.map((metric: Metric, index: number) => ({
        field: `metric_${index}`,
        headerName: metric.id,
        width: 80,
        type: 'number',
        headerClassName: 'table-header-cell',
        renderHeader: () => (
          <Tooltip title={metric.name} arrow placement="top" disablePortal={false} PopperProps={{ style: { zIndex: 2000 } }}>
            <span>{metric.id}</span>
          </Tooltip>
        ),
        valueGetter: (params) => {
          const memberAlias = params.row.alias
          const memberScores = scoresData.scores[memberAlias]
          return memberScores ? memberScores[metric.name] || 0 : 0
        },
        valueFormatter: (params) => {
          return typeof params.value === 'number' ? params.value.toFixed(2) : ''
        },
      }))
    }

    // Filter metrics to only show those with weight > 0 for selected role
    const applicableMetrics = metrics.filter((metric: Metric) => {
      return (metric.weights_by_role[selectedRole] || 0) > 0
    })

    return applicableMetrics.map((metric: Metric, index: number) => ({
      field: `metric_${index}`,
      headerName: metric.id,
      width: 80,
      type: 'number',
      headerClassName: 'table-header-cell',
      renderHeader: () => (
        <Tooltip title={metric.name} arrow placement="top" disablePortal={false} PopperProps={{ style: { zIndex: 2000 } }}>
          <span>{metric.id}</span>
        </Tooltip>
      ),
      valueGetter: (params) => {
        const memberAlias = params.row.alias
        const memberScores = scoresData.scores[memberAlias]
        return memberScores ? memberScores[metric.name] || 0 : 0
      },
      valueFormatter: (params) => {
        return typeof params.value === 'number' ? params.value.toFixed(2) : ''
      },
    }))
  }, [metrics, scoresData, selectedRole])

  // Define main columns
  const columns: GridColDef[] = [
    {
      field: 'alias',
      headerName: 'Alias',
      width: 120,
      headerClassName: 'table-header-cell',
      renderCell: (params) => (
        <Box
          sx={{
            color: params.row.mismatch ? 'error.main' : 'inherit',
            fontWeight: params.row.mismatch ? 'bold' : 'normal',
            cursor: params.row.mismatch ? 'pointer' : 'default',
          }}
          onClick={() => {
            if (params.row.mismatch) {
              navigate(`/adjust/${params.row.alias}`)
            }
          }}
        >
          {params.value}
        </Box>
      ),
    },
    ...(!selectedRole
      ? [
          {
            field: 'role',
            headerName: 'Role',
            width: 120,
            headerClassName: 'table-header-cell',
          } as GridColDef,
        ]
      : []),
    {
      field: 'rank',
      headerName: 'Rank',
      width: 80,
      type: 'number',
      headerClassName: 'table-header-cell',
      renderCell: (params) => (
        <Box
          sx={{
            color: params.row.mismatch ? 'error.main' : 'inherit',
            fontWeight: params.row.mismatch ? 'bold' : 'normal',
            cursor: params.row.mismatch ? 'pointer' : 'default',
          }}
          onClick={() => {
            if (params.row.mismatch) {
              navigate(`/adjust/${params.row.alias}`)
            }
          }}
        >
          {params.value}
        </Box>
      ),
    },
    {
      field: 'expected_rank',
      headerName: 'Expected Rank',
      width: 120,
      type: 'number',
      headerClassName: 'table-header-cell',
      renderCell: (params) => (
        <Box
          sx={{
            color: params.row.mismatch ? 'error.main' : 'inherit',
            fontWeight: params.row.mismatch ? 'bold' : 'normal',
          }}
        >
          {params.value || ''}
        </Box>
      ),
    },
    {
      field: 'weighted_score',
      headerName: 'Weighted Score',
      width: 140,
      type: 'number',
      headerClassName: 'table-header-cell',
      valueFormatter: (params) => {
        return typeof params.value === 'number' ? params.value.toFixed(4) : ''
      },
    },
    ...metricColumns,
  ]

  // Process data for DataGrid
  const rows = useMemo(() => {
    if (!rankings) return []

    return rankings.map((entry: RankingEntry, index: number) => ({
      id: index,
      alias: entry.alias,
      role: entry.role,
      rank: entry.rank,
      expected_rank: entry.expected_rank,
      weighted_score: entry.weighted_score,
      mismatch: entry.mismatch,
    }))
  }, [rankings])

  if (isLoading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    )
  }

  if (rankingsError) {
    return (
      <Alert severity="error">
        Failed to load rankings data. Please try again.
      </Alert>
    )
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Stack Rank Table
      </Typography>

      {/* Role Filter */}
      <Box sx={{ mb: 3 }}>
        <Typography variant="body2" sx={{ mb: 1, color: 'text.secondary' }}>
          Filter by Role
        </Typography>
        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
          <Button
            variant={selectedRole === null ? 'contained' : 'outlined'}
            onClick={() => handleRoleChange(null)}
            sx={{ mb: 1 }}
          >
            All Roles
          </Button>
          {rolesData?.roles.map((role) => (
            <Button
              key={role}
              variant={selectedRole === role ? 'contained' : 'outlined'}
              onClick={() => handleRoleChange(role)}
              sx={{ mb: 1 }}
            >
              {role} ({rolesData.countsByRole[role]})
            </Button>
          ))}
        </Box>
      </Box>

      {/* Data Grid */}
      <Paper sx={{ height: 600, width: '100%' }} className="table-container">
        <DataGrid
          rows={rows}
          columns={columns}
          initialState={{
            pagination: {
              paginationModel: { page: 0, pageSize: 25 },
            },
            sorting: {
              sortModel: [
                { field: 'role', sort: 'asc' },
                { field: 'rank', sort: 'asc' },
              ],
            },
          }}
          pageSizeOptions={[25, 50, 100]}
          disableColumnMenu
          disableRowSelectionOnClick
          onRowClick={(params: GridRowParams) => {
            if (params.row.mismatch) {
              navigate(`/adjust/${params.row.alias}`)
            }
          }}
          sx={{
            // Match Org Percentiles table header styling
            '& .MuiDataGrid-columnHeaders': {
              backgroundColor: (theme) =>
                theme.palette.mode === 'dark'
                  ? 'rgba(91, 140, 255, 0.08)'
                  : 'rgba(37, 99, 235, 0.05)',
              borderBottom: '1px solid',
              borderColor: 'divider',
              overflow: 'visible', // allow tooltips in headers to fully render
            },
            '& .MuiDataGrid-columnHeader': {
              overflow: 'visible',
            },
            '& .MuiDataGrid-columnHeaderTitle': {
              fontWeight: 600,
              fontSize: '13px',
              textTransform: 'uppercase',
              letterSpacing: '0.5px',
              color: 'text.secondary',
            },
            '& .MuiDataGrid-row:hover': {
              cursor: 'default',
            },
            '& .mismatch-row:hover': {
              cursor: 'pointer',
            },
          }}
          getRowClassName={(params) =>
            params.row.mismatch ? 'mismatch-row' : ''
          }
          slotProps={{
            row: {
              style: {
                cursor: 'default',
              },
            },
          }}
        />
      </Paper>

      {/* Legend */}
      <Box sx={{ mt: 2 }}>
        <Typography variant="body2" color="text.secondary">
          <strong>Note:</strong> Highlighted entries indicate mismatches between current rank and expected rank. 
          Click on highlighted entries to adjust scores.
        </Typography>
      </Box>
    </Box>
  )
}

export default StackRankTable
