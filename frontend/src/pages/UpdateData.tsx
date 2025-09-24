import React, { useState, useEffect } from 'react'
import { useMutation, useQueryClient, useQuery } from '@tanstack/react-query'
import {
  Box,
  Typography,
  TextField,
  Button,
  Alert,
  Grid,
  Card,
  CardContent,
  CardActions,
  CircularProgress,
  Snackbar,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  IconButton,
} from '@mui/material'
import {
  ContentPaste as PasteIcon,
  Save as SaveIcon,
  Add as AddIcon,
  Delete as DeleteIcon,
} from '@mui/icons-material'
import { DataGrid, GridColDef, GridRowModel, GridRenderCellParams } from '@mui/x-data-grid'
import apiService from '../services/api'

interface ExpectedRankingRow {
  id: string
  alias: string
  rank: number
}

interface RoleRow {
  id: string
  alias: string
  role: string
}

const UpdateData: React.FC = () => {
  const queryClient = useQueryClient()

  // State for expected rankings table
  const [expectedRankingsRows, setExpectedRankingsRows] = useState<ExpectedRankingRow[]>([])
  const [expectedRankingsError, setExpectedRankingsError] = useState<string>('')

  // State for roles table
  const [rolesRows, setRolesRows] = useState<RoleRow[]>([])
  const [rolesError, setRolesError] = useState<string>('')

  // Dialog states
  const [rankingsDialogOpen, setRankingsDialogOpen] = useState<boolean>(false)
  const [rolesDialogOpen, setRolesDialogOpen] = useState<boolean>(false)
  const [rankingsTextInput, setRankingsTextInput] = useState<string>('')
  const [rolesTextInput, setRolesTextInput] = useState<string>('')

  // Success message state
  const [successMessage, setSuccessMessage] = useState<string>('')
  const [showSuccess, setShowSuccess] = useState<boolean>(false)

  // Fetch current data
  const { data: members, isLoading: membersLoading } = useQuery({
    queryKey: ['members'],
    queryFn: apiService.getMembers,
  })

  const { data: rankings, isLoading: rankingsLoading } = useQuery({
    queryKey: ['rankings'],
    queryFn: () => apiService.getRankings(),
  })

  // Utility functions to convert data to table rows
  const convertMembersToRoleRows = (members: any[]): RoleRow[] => {
    return members.map((member, index) => ({
      id: `role-${index}`,
      alias: member.alias,
      role: member.role,
    }))
  }

  const convertRankingsToRows = (rankings: any[]): ExpectedRankingRow[] => {
    return rankings
      .filter(ranking => ranking.expected_rank != null)
      .sort((a, b) => {
        // Sort by role first, then by expected rank
        if (a.role !== b.role) {
          return a.role.localeCompare(b.role)
        }
        return (a.expected_rank || 0) - (b.expected_rank || 0)
      })
      .map((ranking, index) => ({
        id: `ranking-${index}`,
        alias: ranking.alias,
        rank: ranking.expected_rank,
      }))
  }

  // Load current data when components mount or data changes
  useEffect(() => {
    if (members && !membersLoading) {
      const roleRows = convertMembersToRoleRows(members)
      setRolesRows(roleRows)
    }
  }, [members, membersLoading])

  useEffect(() => {
    if (rankings && !rankingsLoading) {
      const rankingRows = convertRankingsToRows(rankings)
      setExpectedRankingsRows(rankingRows)
    }
  }, [rankings, rankingsLoading])

  // Delete handlers - just remove from local state
  const handleDeleteExpectedRanking = (id: string) => {
    setExpectedRankingsRows((prevRows) =>
      prevRows.filter(row => row.id !== id)
    )
  }

  const handleDeleteRole = (id: string) => {
    setRolesRows((prevRows) =>
      prevRows.filter(row => row.id !== id)
    )
  }

  // Table column definitions
  const expectedRankingsColumns: GridColDef[] = [
    {
      field: 'alias',
      headerName: 'Alias',
      width: 150,
      editable: true,
    },
    {
      field: 'rank',
      headerName: 'Expected Rank',
      width: 150,
      type: 'number',
      editable: true,
    },
    {
      field: 'actions',
      headerName: 'Actions',
      width: 80,
      sortable: false,
      disableColumnMenu: true,
      renderCell: (params: GridRenderCellParams) => (
        <IconButton
          size="small"
          color="error"
          onClick={() => handleDeleteExpectedRanking(params.row.id)}
        >
          <DeleteIcon fontSize="small" />
        </IconButton>
      ),
    },
  ]

  const rolesColumns: GridColDef[] = [
    {
      field: 'alias',
      headerName: 'Alias',
      width: 150,
      editable: true,
    },
    {
      field: 'role',
      headerName: 'Role',
      width: 150,
      editable: true,
    },
    {
      field: 'actions',
      headerName: 'Actions',
      width: 80,
      sortable: false,
      disableColumnMenu: true,
      renderCell: (params: GridRenderCellParams) => (
        <IconButton
          size="small"
          color="error"
          onClick={() => handleDeleteRole(params.row.id)}
        >
          <DeleteIcon fontSize="small" />
        </IconButton>
      ),
    },
  ]

  // Parse comma-separated text functions
  const parseExpectedRankingsText = (text: string): ExpectedRankingRow[] => {
    try {
      const lines = text.trim().split('\n').filter(line => line.trim())
      return lines.map((line, index) => {
        const parts = line.split(',').map(part => part.trim())
        if (parts.length !== 2) {
          throw new Error(`Line ${index + 1}: Expected 2 columns (alias,rank), got ${parts.length}`)
        }

        const [alias, rankStr] = parts
        const rank = parseInt(rankStr, 10)

        if (!alias) {
          throw new Error(`Line ${index + 1}: Alias cannot be empty`)
        }

        if (isNaN(rank) || rank < 1) {
          throw new Error(`Line ${index + 1}: Rank must be a positive integer`)
        }

        return {
          id: `ranking-${index}`,
          alias,
          rank,
        }
      })
    } catch (error) {
      throw error
    }
  }

  const parseRolesText = (text: string): RoleRow[] => {
    try {
      const lines = text.trim().split('\n').filter(line => line.trim())
      return lines.map((line, index) => {
        const parts = line.split(',').map(part => part.trim())
        if (parts.length !== 2) {
          throw new Error(`Line ${index + 1}: Expected 2 columns (alias,role), got ${parts.length}`)
        }

        const [alias, role] = parts

        if (!alias || !role) {
          throw new Error(`Line ${index + 1}: Alias and role cannot be empty`)
        }

        return {
          id: `role-${index}`,
          alias,
          role,
        }
      })
    } catch (error) {
      throw error
    }
  }

  // Mutations
  const updateExpectedRankingsMutation = useMutation({
    mutationFn: apiService.updateExpectedRankings,
    onSuccess: (data) => {
      setSuccessMessage(data.message)
      setShowSuccess(true)
      setExpectedRankingsError('')
      // Refresh data to show updated values
      queryClient.invalidateQueries({ queryKey: ['rankings'] })
    },
    onError: (error: any) => {
      setExpectedRankingsError(error.response?.data?.detail || 'Failed to update expected rankings')
    },
  })

  const updateRolesMutation = useMutation({
    mutationFn: apiService.updateRoles,
    onSuccess: (data) => {
      setSuccessMessage(data.message)
      setShowSuccess(true)
      setRolesError('')
      // Refresh data to show updated values
      queryClient.invalidateQueries({ queryKey: ['rankings'] })
      queryClient.invalidateQueries({ queryKey: ['roles'] })
      queryClient.invalidateQueries({ queryKey: ['members'] })
    },
    onError: (error: any) => {
      setRolesError(error.response?.data?.detail || 'Failed to update roles')
    },
  })



  // Handler functions
  const handleExpectedRankingsRowUpdate = (newRow: GridRowModel) => {
    setExpectedRankingsRows((prevRows) =>
      prevRows.map((row) => (row.id === newRow.id ? { ...newRow } as ExpectedRankingRow : row))
    )
    return newRow
  }

  const handleRolesRowUpdate = (newRow: GridRowModel) => {
    setRolesRows((prevRows) =>
      prevRows.map((row) => (row.id === newRow.id ? { ...newRow } as RoleRow : row))
    )
    return newRow
  }

  const handleAddExpectedRankingRow = () => {
    const newRow: ExpectedRankingRow = {
      id: `ranking-${Date.now()}`,
      alias: '',
      rank: 1,
    }
    setExpectedRankingsRows((prevRows) => [...prevRows, newRow])
  }

  const handleAddRoleRow = () => {
    const newRow: RoleRow = {
      id: `role-${Date.now()}`,
      alias: '',
      role: '',
    }
    setRolesRows((prevRows) => [...prevRows, newRow])
  }

  const handleUpdateExpectedRankings = () => {
    try {
      const rankings = expectedRankingsRows.map(row => ({
        alias: row.alias,
        rank: row.rank,
      }))

      setExpectedRankingsError('')
      updateExpectedRankingsMutation.mutate({ rankings })
    } catch (error: any) {
      setExpectedRankingsError(error.message)
    }
  }

  const handleUpdateRoles = () => {
    try {
      const roles = rolesRows.map(row => ({
        alias: row.alias,
        role: row.role,
      }))

      setRolesError('')
      updateRolesMutation.mutate({ roles })
    } catch (error: any) {
      setRolesError(error.message)
    }
  }

  // Dialog handlers
  const handleRankingsDialogSubmit = () => {
    try {
      const parsedRows = parseExpectedRankingsText(rankingsTextInput)
      setExpectedRankingsRows(parsedRows)
      setRankingsDialogOpen(false)
      setRankingsTextInput('')
      setExpectedRankingsError('')
    } catch (error: any) {
      setExpectedRankingsError(error.message)
    }
  }

  const handleRolesDialogSubmit = () => {
    try {
      const parsedRows = parseRolesText(rolesTextInput)
      setRolesRows(parsedRows)
      setRolesDialogOpen(false)
      setRolesTextInput('')
      setRolesError('')
    } catch (error: any) {
      setRolesError(error.message)
    }
  }


  const isLoading = membersLoading || rankingsLoading

  return (
    <Box>
      <Typography variant="h4" component="h1" gutterBottom>
        Update Data
      </Typography>

      <Typography variant="body1" color="text.secondary" paragraph>
        The current data from the database is shown in editable tables below. You can edit cells directly
        or use "Copy from Text" to paste comma-separated data. When you update, the data in the database
        will be completely replaced with your changes.
      </Typography>

      {isLoading && (
        <Box display="flex" justifyContent="center" alignItems="center" minHeight="200px">
          <CircularProgress />
          <Typography variant="body2" sx={{ ml: 2 }}>
            Loading current data...
          </Typography>
        </Box>
      )}

      {!isLoading && (
        <Grid container spacing={3}>
        {/* Expected Rankings Section */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Expected Rankings
              </Typography>

              <Typography variant="body2" color="text.secondary" paragraph>
                Edit cells directly in the table below. Click "Copy from Text" to paste comma-separated data.
              </Typography>

              <Box sx={{ height: 400, width: '100%', mb: 2 }}>
                <DataGrid
                  rows={expectedRankingsRows}
                  columns={expectedRankingsColumns}
                  processRowUpdate={handleExpectedRankingsRowUpdate}
                  hideFooter
                  disableRowSelectionOnClick
                />
              </Box>

              {expectedRankingsError && (
                <Alert severity="error" sx={{ mb: 2 }}>
                  {expectedRankingsError}
                </Alert>
              )}
            </CardContent>

            <CardActions>
              <Button
                startIcon={<PasteIcon />}
                onClick={() => setRankingsDialogOpen(true)}
                variant="outlined"
                size="small"
              >
                Copy from Text
              </Button>

              <Button
                startIcon={<AddIcon />}
                onClick={handleAddExpectedRankingRow}
                variant="outlined"
                size="small"
              >
                Add Row
              </Button>

              <Button
                startIcon={updateExpectedRankingsMutation.isPending ? <CircularProgress size={16} /> : <SaveIcon />}
                onClick={handleUpdateExpectedRankings}
                variant="contained"
                disabled={updateExpectedRankingsMutation.isPending || expectedRankingsRows.length === 0}
                size="small"
              >
                Update Rankings
              </Button>
            </CardActions>
          </Card>
        </Grid>

        {/* Roles Section */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Roles
              </Typography>

              <Typography variant="body2" color="text.secondary" paragraph>
                Edit cells directly in the table below. Click "Copy from Text" to paste comma-separated data.
              </Typography>

              <Box sx={{ height: 400, width: '100%', mb: 2 }}>
                <DataGrid
                  rows={rolesRows}
                  columns={rolesColumns}
                  processRowUpdate={handleRolesRowUpdate}
                  hideFooter
                  disableRowSelectionOnClick
                />
              </Box>

              {rolesError && (
                <Alert severity="error" sx={{ mb: 2 }}>
                  {rolesError}
                </Alert>
              )}
            </CardContent>

            <CardActions>
              <Button
                startIcon={<PasteIcon />}
                onClick={() => setRolesDialogOpen(true)}
                variant="outlined"
                size="small"
              >
                Copy from Text
              </Button>

              <Button
                startIcon={<AddIcon />}
                onClick={handleAddRoleRow}
                variant="outlined"
                size="small"
              >
                Add Row
              </Button>

              <Button
                startIcon={updateRolesMutation.isPending ? <CircularProgress size={16} /> : <SaveIcon />}
                onClick={handleUpdateRoles}
                variant="contained"
                disabled={updateRolesMutation.isPending || rolesRows.length === 0}
                size="small"
              >
                Update Roles
              </Button>
            </CardActions>
          </Card>
        </Grid>
      </Grid>
      )}

      {/* Expected Rankings Dialog */}
      <Dialog
        open={rankingsDialogOpen}
        onClose={() => setRankingsDialogOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>Copy Expected Rankings from Text</DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary" paragraph>
            Paste comma-separated data below. Format: alias,rank (one per line)
            <br />
            Example: Dev01,1
          </Typography>
          <TextField
            fullWidth
            multiline
            rows={10}
            variant="outlined"
            placeholder="Dev01,1&#10;Dev02,2&#10;PMO01,1"
            value={rankingsTextInput}
            onChange={(e) => setRankingsTextInput(e.target.value)}
            sx={{ mt: 2 }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setRankingsDialogOpen(false)}>
            Cancel
          </Button>
          <Button
            onClick={handleRankingsDialogSubmit}
            variant="contained"
            disabled={!rankingsTextInput.trim()}
          >
            Update Table
          </Button>
        </DialogActions>
      </Dialog>

      {/* Roles Dialog */}
      <Dialog
        open={rolesDialogOpen}
        onClose={() => setRolesDialogOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>Copy Roles from Text</DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary" paragraph>
            Paste comma-separated data below. Format: alias,role (one per line)
            <br />
            Example: Dev01,Dev
          </Typography>
          <TextField
            fullWidth
            multiline
            rows={10}
            variant="outlined"
            placeholder="Dev01,Dev&#10;Dev02,Dev&#10;PMO01,PMO"
            value={rolesTextInput}
            onChange={(e) => setRolesTextInput(e.target.value)}
            sx={{ mt: 2 }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setRolesDialogOpen(false)}>
            Cancel
          </Button>
          <Button
            onClick={handleRolesDialogSubmit}
            variant="contained"
            disabled={!rolesTextInput.trim()}
          >
            Update Table
          </Button>
        </DialogActions>
      </Dialog>

      {/* Success Snackbar */}
      <Snackbar
        open={showSuccess}
        autoHideDuration={6000}
        onClose={() => setShowSuccess(false)}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert onClose={() => setShowSuccess(false)} severity="success" sx={{ width: '100%' }}>
          {successMessage}
        </Alert>
      </Snackbar>
    </Box>
  )
}

export default UpdateData
