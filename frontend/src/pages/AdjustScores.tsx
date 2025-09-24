import React, { useState, useMemo } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Box,
  Paper,
  Typography,
  Button,
  TextField,
  Checkbox,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Alert,
  CircularProgress,
  Divider,
  Slider,
} from '@mui/material'
import {
  Person as PersonIcon,
  TrendingUp as TrendingUpIcon,
  Flag as FlagIcon
} from '@mui/icons-material'
import apiService, { ScoreAdjustmentPreview } from '../services/api'

const AdjustScores: React.FC = () => {
  const { alias } = useParams<{ alias: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const [selectedMetrics, setSelectedMetrics] = useState<string[]>([])
  const [targetPercent, setTargetPercent] = useState<number>(5.0)
  const [preview, setPreview] = useState<ScoreAdjustmentPreview | null>(null)
  const [previewError, setPreviewError] = useState<string | null>(null)

  const [editedScores, setEditedScores] = useState<Record<string, number>>({})

  // Fetch data
  const { data: members, isLoading: membersLoading } = useQuery({
    queryKey: ['members'],
    queryFn: apiService.getMembers,
  })

  const { data: metrics, isLoading: metricsLoading } = useQuery({
    queryKey: ['metrics'],
    queryFn: apiService.getMetrics,
  })

  const { data: rankings, isLoading: rankingsLoading } = useQuery({
    queryKey: ['rankings'],
    queryFn: () => apiService.getRankings(),
  })

  const { data: scores, isLoading: scoresLoading } = useQuery({
    queryKey: ['scores'],
    queryFn: () => apiService.getScores(),
  })

  // Mutations
  const previewMutation = useMutation({
    mutationFn: apiService.previewAdjustment,
    onSuccess: (data) => {
      setPreview(data)
      setPreviewError(null)
      // Prefill editable values with proposed scores from preview
      setEditedScores(prev => ({ ...prev, ...data.proposed }))
    },
    onError: (error: any) => {
      setPreviewError(error.response?.data?.detail || 'Failed to preview adjustment')
      setPreview(null)
    },
  })

  const applyMutation = useMutation({
    mutationFn: apiService.applyAdjustment,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['rankings'] })
      queryClient.invalidateQueries({ queryKey: ['scores'] })
      navigate('/')
    },
    onError: (error: any) => {
      setPreviewError(error.response?.data?.detail || 'Failed to apply adjustment')
    },
  })

  const isLoading = membersLoading || metricsLoading || rankingsLoading || scoresLoading

  // Get current member info
  const currentMember = useMemo(() => {
    if (!members || !alias) return null
    return members.find(m => m.alias === alias)
  }, [members, alias])

  // Get current ranking info
  const currentRanking = useMemo(() => {
    if (!rankings || !alias) return null
    return rankings.find(r => r.alias === alias)
  }, [rankings, alias])

  // Get applicable metrics for the member's role
  const applicableMetrics = useMemo(() => {
    if (!metrics || !currentMember) return []
    return metrics.filter(m => (m.weights_by_role[currentMember.role] || 0) > 0)
  }, [metrics, currentMember])

  // Get reference member info
  const referenceMember = useMemo(() => {
    if (!rankings || !currentRanking || !currentRanking.expected_rank) return null

    const targetRank = currentRanking.expected_rank < currentRanking.rank
      ? Math.max(1, currentRanking.expected_rank)
      : currentRanking.expected_rank

    return rankings.find(r =>
      r.role === currentRanking.role &&
      r.rank === targetRank &&
      r.alias !== alias
    )

  }, [rankings, currentRanking, alias])

  // Helpers for scores/weights and totals
  const weightByMetricName = useMemo(() => {
    const map: Record<string, number> = {}
    if (currentMember) {
      applicableMetrics.forEach(m => {
        map[m.name] = m.weights_by_role[currentMember.role] || 0
      })
    }
    return map
  }, [applicableMetrics, currentMember])

  const getCurrentScore = (metricName: string) =>
    (alias && scores?.scores?.[alias]?.[metricName] !== undefined)
      ? (scores!.scores[alias!][metricName] || 0)
      : 0

  const getRefScore = (metricName: string) =>
    (referenceMember && scores?.scores?.[referenceMember.alias]?.[metricName] !== undefined)
      ? (scores!.scores[referenceMember!.alias][metricName] || 0)
      : 0

  const getEditedValue = (metricName: string) => {
    const s = editedScores[metricName]
    if (s !== undefined) return s
    const p = preview?.proposed?.[metricName]
    if (p !== undefined) return p
    return getCurrentScore(metricName)
  }

  const totals = useMemo(() => {
    let memberWeighted = 0
    let refWeighted = 0
    applicableMetrics.forEach(m => {
      const w = weightByMetricName[m.name] || 0
      const mv = getEditedValue(m.name)
      const rv = referenceMember ? getRefScore(m.name) : 0
      memberWeighted += mv * w
      refWeighted += rv * w
    })
    return { memberWeighted, refWeighted, delta: memberWeighted - refWeighted }
  }, [applicableMetrics, editedScores, preview, scores, alias, referenceMember, weightByMetricName])

  // Helper function to determine if a cell should be highlighted
  const shouldHighlightMemberCell = (metricName: string, memberVal: number, refVal: number | null, weight: number) => {
    if (!currentRanking || !referenceMember || refVal === null || weight <= 0) return false

    const expectedRank = currentRanking.expected_rank
    const currentRank = currentRanking.rank

    if (!expectedRank || expectedRank === currentRank) return false

    // If expected rank is higher (lower number), member should have higher scores
    if (expectedRank < currentRank) {
      return memberVal < refVal
    }
    // If expected rank is lower (higher number), member should have lower scores
    else {
      return memberVal > refVal
    }
  }

  // Handle metric selection
  const handleMetricToggle = (metricName: string) => {
    setSelectedMetrics(prev => {
      const isCurrentlySelected = prev.includes(metricName)

      if (isCurrentlySelected) {
        // When unchecking, revert to original value
        setEditedScores(prevScores => {
          const newScores = { ...prevScores }
          delete newScores[metricName] // Remove edited value to revert to original
          return newScores
        })
        return prev.filter(m => m !== metricName)
      } else {
        return [...prev, metricName]
      }
    })
  }

  // Handle calculate button
  const handleCalculate = () => {
    if (!alias || selectedMetrics.length === 0) return

    previewMutation.mutate({
      alias,
      selected_metrics: selectedMetrics,
      percent: targetPercent,
    })
  }

  // Check if there are any changes from original scores
  const hasChanges = useMemo(() => {
    return Object.keys(editedScores).some(metricName => {
      const editedValue = editedScores[metricName]
      const originalValue = getCurrentScore(metricName)
      return Math.abs(editedValue - originalValue) > 0.0001 // Use small epsilon for floating point comparison
    })
  }, [editedScores, scores, alias])

  // Handle save button
  const handleSave = () => {
    if (!alias || !hasChanges) return

    const changes: Record<string, number> = {}
    // Only include metrics that have actually changed from their original values
    Object.keys(editedScores).forEach((metricName) => {
      const editedValue = editedScores[metricName]
      const originalValue = getCurrentScore(metricName)
      if (Math.abs(editedValue - originalValue) > 0.0001) {
        changes[metricName] = editedValue
      }
    })

    if (Object.keys(changes).length === 0) return

    applyMutation.mutate({
      alias,
      changes,
    })
  }

  // Handle next button
  const handleNext = () => {
    // This would navigate to the next member with mismatches
    // For now, just go back to the main table
    navigate('/')
  }

  if (isLoading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">

        <CircularProgress />
      </Box>
    )
  }

  if (!currentMember || !currentRanking) {
    return (
      <Alert severity="error">
        Member not found or no ranking data available.
      </Alert>
    )
  }



  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Adjust Scores - {alias}
      </Typography>

      {/* Member Info */}
      <Paper sx={{ p: 3, mb: 3, borderRadius: 2 }} className="detail-card">
        <Typography variant="h6" gutterBottom sx={{ mb: 3, fontWeight: 600, color: 'text.primary' }}>
          Member Information
        </Typography>

        <Box sx={{
          display: 'flex',
          gap: 2,
          flexWrap: 'wrap',
          justifyContent: 'space-between',
          '@media (max-width: 768px)': {
            flexDirection: 'column'
          }
        }}>
          {/* Role Card */}
          <Box className="member-info-card" sx={{
            flex: '1 1 0',
            minWidth: '160px',
            p: 2.5,
            backgroundColor: 'background.paper',
            borderRadius: 2,
            border: '1px solid',
            borderColor: 'divider',
            position: 'relative'
          }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1 }}>
              <Typography variant="body2" sx={{
                color: 'text.secondary',
                fontWeight: 500,
                fontSize: '0.875rem'
              }}>
                Role
              </Typography>
              <PersonIcon sx={{
                color: 'primary.main',
                fontSize: '1.25rem'
              }} />
            </Box>
            <Typography variant="h4" sx={{
              color: 'text.primary',
              fontWeight: 700,
              fontSize: '1.75rem',
              lineHeight: 1.2
            }}>
              {currentMember?.role || 'N/A'}
            </Typography>
          </Box>

          {/* Current Rank Card */}
          <Box className="member-info-card" sx={{
            flex: '1 1 0',
            minWidth: '160px',
            p: 2.5,
            backgroundColor: 'background.paper',
            borderRadius: 2,
            border: '1px solid',
            borderColor: 'divider',
            position: 'relative'
          }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1 }}>
              <Typography variant="body2" sx={{
                color: 'text.secondary',
                fontWeight: 500,
                fontSize: '0.875rem'
              }}>
                Current Rank
              </Typography>
              <TrendingUpIcon sx={{
                color: currentRanking?.rank > (currentRanking?.expected_rank || currentRanking?.rank)
                  ? 'error.main'
                  : 'success.main',
                fontSize: '1.25rem'
              }} />
            </Box>
            <Typography variant="h4" sx={{
              color: 'text.primary',
              fontWeight: 700,
              fontSize: '1.75rem',
              lineHeight: 1.2
            }}>
              {currentRanking?.rank || 'N/A'}
            </Typography>
          </Box>

          {/* Expected Rank Card */}
          <Box className="member-info-card" sx={{
            flex: '1 1 0',
            minWidth: '160px',
            p: 2.5,
            backgroundColor: 'background.paper',
            borderRadius: 2,
            border: '1px solid',
            borderColor: 'divider',
            position: 'relative'
          }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1 }}>
              <Typography variant="body2" sx={{
                color: 'text.secondary',
                fontWeight: 500,
                fontSize: '0.875rem'
              }}>
                Expected Rank
              </Typography>
              <FlagIcon sx={{
                color: 'info.main',
                fontSize: '1.25rem'
              }} />
            </Box>
            <Typography variant="h4" sx={{
              color: 'text.primary',
              fontWeight: 700,
              fontSize: '1.75rem',
              lineHeight: 1.2
            }}>
              {currentRanking?.expected_rank || 'Not set'}
            </Typography>
          </Box>
        </Box>
      </Paper>



      {/* Target Delta Input */}
      <Paper sx={{ p: 2, mb: 3 }} className="detail-card">
        <Typography variant="h6" gutterBottom>
          Target Adjustment
        </Typography>
        <Box sx={{ mb: 2 }}>
          <Typography variant="body2" color="text.secondary" gutterBottom>
            Target Percent: {targetPercent.toFixed(1)}%
          </Typography>
          <Slider
            value={targetPercent}
            onChange={(_, newValue) => setTargetPercent(newValue as number)}
            min={0.1}
            max={50}
            step={0.1}
            marks={[
              { value: 0.1, label: '0.1%' },
              { value: 5, label: '5%' },
              { value: 10, label: '10%' },
              { value: 25, label: '25%' },
              { value: 50, label: '50%' }
            ]}
            valueLabelDisplay="auto"
            sx={{ mt: 1, mb: 1 }}
          />
        </Box>
        <Box>
          <Button
            variant="contained"
            onClick={handleCalculate}
            disabled={selectedMetrics.length === 0 || previewMutation.isPending}
            sx={{ mr: 2 }}
          >
            {previewMutation.isPending ? 'Calculating...' : 'Calculate'}
          </Button>
          <Button variant="outlined" onClick={handleNext} sx={{ mr: 2 }}>
            Next
          </Button>
          <Button
            variant="contained"
            color="success"
            onClick={handleSave}
            disabled={!hasChanges || applyMutation.isPending}
          >
            {applyMutation.isPending ? 'Saving...' : 'Save'}
          </Button>
        </Box>
      </Paper>

      {/* Error Display */}
      {previewError && (
        <Alert severity="error" sx={{ mb: 3 }}>

          {previewError}
        </Alert>
      )}

      {/* Adjust Scores Table */}
      <Paper sx={{ p: 2 }} className="detail-card">
        <Typography variant="h6" gutterBottom>
          Adjust Scores
        </Typography>

        <TableContainer>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell padding="checkbox">Select</TableCell>
                <TableCell>Metric</TableCell>
                <TableCell align="center">Weight</TableCell>
                <TableCell align="right">{alias}</TableCell>
                {referenceMember && (
                  <TableCell align="right">{referenceMember.alias}</TableCell>
                )}
                {referenceMember && (
                  <TableCell align="right">Difference</TableCell>
                )}
              </TableRow>
            </TableHead>
            <TableBody>
              {applicableMetrics.map((metric) => {
                const metricName = metric.name
                const isEditable = selectedMetrics.includes(metricName)
                const memberVal = getEditedValue(metricName)
                const refVal = referenceMember ? getRefScore(metricName) : null
                const weight = weightByMetricName[metricName] || 0
                const difference = refVal !== null ? memberVal - refVal : null

                // Determine if this cell should be highlighted as causing wrong ranking
                const shouldHighlight = shouldHighlightMemberCell(metricName, memberVal, refVal, weight)

                return (
                  <TableRow
                    key={metricName}
                    sx={{
                      backgroundColor: isEditable ? 'action.hover' : 'inherit',
                      '&:hover': { backgroundColor: 'action.selected' }
                    }}
                  >
                    <TableCell padding="checkbox">
                      <Checkbox
                        checked={isEditable}
                        onChange={(e) => {
                          e.stopPropagation()
                          handleMetricToggle(metricName)
                        }}
                        onClick={(e) => e.stopPropagation()}
                        size="small"
                        color="primary"
                      />
                    </TableCell>
                    <TableCell>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        {metricName}
                        {isEditable && (
                          <Box
                            sx={{
                              width: 8,
                              height: 8,
                              borderRadius: '50%',
                              backgroundColor: 'primary.main'
                            }}
                          />
                        )}
                      </Box>
                    </TableCell>
                    <TableCell align="center">
                      <Typography variant="body2" color="text.secondary">
                        {Math.round(weight)}
                      </Typography>
                    </TableCell>
                    <TableCell
                      align="right"
                      sx={{
                        backgroundColor: shouldHighlight ? 'rgba(244, 67, 54, 0.1)' : 'inherit',
                        borderLeft: shouldHighlight ? '3px solid #f44336' : 'none'
                      }}
                    >
                      {isEditable ? (
                        <TextField
                          size="small"
                          type="number"
                          value={memberVal}
                          onChange={(e) => {
                            const v = parseFloat(e.target.value)
                            const clamped = isNaN(v) ? 0 : Math.min(Math.max(v, 0), 10)
                            setEditedScores(prev => ({ ...prev, [metricName]: clamped }))
                          }}
                          onClick={(e) => e.stopPropagation()}
                          onFocus={(e) => e.stopPropagation()}
                          inputProps={{
                            step: 0.0001,
                            min: 0,
                            max: 10,
                            style: { MozAppearance: 'textfield' } // Remove arrows in Firefox
                          }}
                          sx={{
                            '& .MuiInputBase-input': {
                              textAlign: 'right',
                              fontWeight: 'bold',
                              backgroundColor: shouldHighlight ? 'rgba(244, 67, 54, 0.05)' : 'inherit'
                            },
                            // Remove arrows in Chrome, Safari, Edge
                            '& input[type=number]::-webkit-outer-spin-button': {
                              WebkitAppearance: 'none',
                              margin: 0,
                            },
                            '& input[type=number]::-webkit-inner-spin-button': {
                              WebkitAppearance: 'none',
                              margin: 0,
                            }
                          }}
                        />
                      ) : (
                        <Typography
                          variant="body2"
                          sx={{
                            fontWeight: isEditable ? 'bold' : 'normal',
                            color: isEditable ? 'primary.main' : shouldHighlight ? 'error.main' : 'inherit'
                          }}
                        >
                          {Math.round(memberVal)}
                        </Typography>
                      )}
                    </TableCell>
                    {referenceMember && (
                      <TableCell align="right">
                        <Typography variant="body2" color="text.secondary">
                          {refVal !== null ? Math.round(refVal) : '-'}
                        </Typography>
                      </TableCell>
                    )}
                    {referenceMember && (
                      <TableCell align="right">
                        {difference !== null ? (
                          <Typography
                            variant="body2"
                            sx={{
                              color: difference > 0 ? 'success.main' : difference < 0 ? 'error.main' : 'text.secondary',
                              fontWeight: Math.abs(difference) > 0.01 ? 'bold' : 'normal'
                            }}
                          >
                            {difference > 0 ? '+' : ''}{Math.round(difference)}
                          </Typography>
                        ) : (
                          '-'
                        )}
                      </TableCell>
                    )}
                  </TableRow>
                )
              })}
            </TableBody>
          </Table>
        </TableContainer>

        {referenceMember && (
          <Box sx={{ mt: 2 }}>
            <Divider sx={{ mb: 2 }} />
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
              <Typography variant="h6" color="text.primary">
                Summary
              </Typography>
            </Box>
            <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 2 }}>
              <Box sx={{ textAlign: 'center', p: 1, backgroundColor: 'primary.light', borderRadius: 1 }}>
                <Typography variant="body2" color="primary.contrastText" gutterBottom>
                  {alias} Total
                </Typography>
                <Typography variant="h6" color="primary.contrastText">
                  {Math.round(totals.memberWeighted)}
                </Typography>
              </Box>
              <Box sx={{ textAlign: 'center', p: 1, backgroundColor: 'grey.200', borderRadius: 1 }}>
                <Typography variant="body2" color="text.secondary" gutterBottom>
                  {referenceMember.alias} Total
                </Typography>
                <Typography variant="h6" color="text.primary">
                  {Math.round(totals.refWeighted)}
                </Typography>
              </Box>
              <Box sx={{
                textAlign: 'center',
                p: 1,
                backgroundColor: totals.delta > 0 ? 'success.light' : totals.delta < 0 ? 'error.light' : 'grey.100',
                borderRadius: 1
              }}>
                <Typography
                  variant="body2"
                  color={totals.delta > 0 ? 'success.contrastText' : totals.delta < 0 ? 'error.contrastText' : 'text.secondary'}
                  gutterBottom
                >
                  Difference
                </Typography>
                <Typography
                  variant="h6"
                  color={totals.delta > 0 ? 'success.contrastText' : totals.delta < 0 ? 'error.contrastText' : 'text.primary'}
                  sx={{ fontWeight: 'bold' }}
                >
                  {totals.delta > 0 ? '+' : ''}{Math.round(totals.delta)}
                </Typography>
              </Box>
            </Box>
            <Box sx={{ mt: 1, textAlign: 'center' }}>
              <Typography variant="body2" color="text.secondary">
                {totals.delta > 0
                  ? `${alias} is ${Math.round(totals.delta)} points ahead of ${referenceMember.alias}`
                  : totals.delta < 0
                    ? `${alias} is ${Math.round(Math.abs(totals.delta))} points behind ${referenceMember.alias}`
                    : `${alias} and ${referenceMember.alias} have equal weighted scores`
                }
              </Typography>
            </Box>
          </Box>
        )}
      </Paper>
    </Box>
  )
}

export default AdjustScores
