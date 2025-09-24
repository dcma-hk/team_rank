import React, { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  Box,
  Paper,
  Typography,
  FormControl,
  FormLabel,
  RadioGroup,
  FormControlLabel,
  Radio,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Chip,
  CircularProgress,
  Alert,
} from '@mui/material'
import ExpandMoreIcon from '@mui/icons-material/ExpandMore'
import apiService from '../services/api'

const OrgPercentiles: React.FC = () => {
  const [basis, setBasis] = useState<'weighted' | 'rank'>('weighted')

  // Fetch data
  const { data: rolesData, isLoading: rolesLoading } = useQuery({
    queryKey: ['roles'],
    queryFn: apiService.getRoles,
  })

  const { data: percentilesData, isLoading: percentilesLoading, error } = useQuery({
    queryKey: ['percentiles', basis],
    queryFn: () => apiService.getPercentiles(basis),
  })

  const isLoading = rolesLoading || percentilesLoading

  const handleBasisChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setBasis(event.target.value as 'weighted' | 'rank')
  }

  if (isLoading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    )
  }

  if (error) {
    return (
      <Alert severity="error">
        Failed to load percentiles data. Please try again.
      </Alert>
    )
  }

  const roles = rolesData?.roles || []
  const buckets = percentilesData?.buckets || []

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Organizational Percentiles
      </Typography>

      {/* Basis Selection */}
      <Paper sx={{ p: 2, mb: 3 }} className="detail-card">
        <FormControl component="fieldset">
          <FormLabel component="legend">Percentile Basis</FormLabel>
          <RadioGroup
            row
            value={basis}
            onChange={handleBasisChange}
          >
            <FormControlLabel
              value="weighted"
              control={<Radio />}
              label="Weighted Score"
            />
            <FormControlLabel
              value="rank"
              control={<Radio />}
              label="Rank (within role)"
            />
          </RadioGroup>
        </FormControl>
      </Paper>

      {/* Percentiles Table */}
      <Paper className="table-container">
        <TableContainer>
          <Table>
            <TableHead>
              <TableRow className="table-header-row">
                <TableCell className="table-header-cell">Percentile</TableCell>
                {roles.map((role) => (
                  <TableCell key={role} align="center" className="table-header-cell">
                    {role}
                  </TableCell>
                ))}
              </TableRow>
            </TableHead>
            <TableBody>
              {buckets.map((bucket) => (
                <TableRow key={bucket.pct}>
                  <TableCell>
                    <Typography variant="body2" fontWeight="bold">
                      {bucket.pct}%
                    </Typography>
                  </TableCell>
                  {roles.map((role) => {
                    const roleMembers = bucket.by_role[role] || []
                    const memberCount = roleMembers.length

                    if (memberCount === 0) {
                      return (
                        <TableCell key={role} align="center">
                          <Typography variant="body2" color="text.secondary">
                            No members
                          </Typography>
                        </TableCell>
                      )
                    }

                    return (
                      <TableCell key={role} align="center">
                        <Accordion>
                          <AccordionSummary
                            expandIcon={<ExpandMoreIcon />}
                            sx={{ minHeight: 'auto', '& .MuiAccordionSummary-content': { margin: '8px 0' } }}
                          >
                            <Box textAlign="center" width="100%">
                              <Chip
                                label={`${memberCount} member${memberCount !== 1 ? 's' : ''}`}
                                size="small"
                                color="primary"
                                variant="outlined"
                              />
                            </Box>
                          </AccordionSummary>
                          <AccordionDetails sx={{ pt: 0 }}>
                            <Box>
                              {roleMembers.map((member, index) => (
                                <Box key={member.alias} sx={{ mb: 1 }}>
                                  <Typography variant="body2">
                                    <strong>{member.alias}</strong>
                                  </Typography>
                                  <Typography variant="caption" color="text.secondary">
                                    {basis === 'weighted' 
                                      ? `Score: ${member.weightedScore?.toFixed(4) || 'N/A'}`
                                      : `Rank: ${member.rank || 'N/A'}`
                                    }
                                  </Typography>
                                </Box>
                              ))}
                            </Box>
                          </AccordionDetails>
                        </Accordion>
                      </TableCell>
                    )
                  })}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </Paper>

      {/* Legend */}
      <Box sx={{ mt: 2 }}>
        <Typography variant="body2" color="text.secondary">
          <strong>Note:</strong> Percentiles are calculated within each role. 
          {basis === 'weighted' 
            ? ' Members are grouped by weighted score percentiles.'
            : ' Members are grouped by rank percentiles within their role.'
          }
          {' '}Click on member counts to expand and see individual members.
        </Typography>
      </Box>
    </Box>
  )
}

export default OrgPercentiles
