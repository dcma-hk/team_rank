import React, { useState, useRef } from 'react'
import {
  Box,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  TextField,
  Typography,
  Alert,
  LinearProgress,
  Chip,
  Stack,
  IconButton,
  Tooltip,
} from '@mui/material'
import {
  CloudUpload as CloudUploadIcon,
  Close as CloseIcon,
  FileUpload as FileUploadIcon,
} from '@mui/icons-material'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import apiService from '../services/api'

interface ExcelUploadProps {
  open: boolean
  onClose: () => void
  availableSnapshots?: string[]
  currentSnapshot?: string
}

const ExcelUpload: React.FC<ExcelUploadProps> = ({
  open,
  onClose,
  availableSnapshots = [],
  currentSnapshot = '',
}) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [selectedSnapshot, setSelectedSnapshot] = useState<string>('')
  const [customSnapshot, setCustomSnapshot] = useState<string>('')
  const [useCustomSnapshot, setUseCustomSnapshot] = useState<boolean>(false)
  const [error, setError] = useState<string | null>(null)
  const [dragOver, setDragOver] = useState<boolean>(false)
  const [successMessage, setSuccessMessage] = useState<string | null>(null)
  
  const fileInputRef = useRef<HTMLInputElement>(null)
  const queryClient = useQueryClient()

  // Upload mutation
  const uploadMutation = useMutation({
    mutationFn: ({ file, snapshot }: { file: File; snapshot: string }) =>
      apiService.uploadExcelData(file, snapshot),
    onSuccess: (data) => {
      // Set success message with details
      setSuccessMessage(`Successfully uploaded data to snapshot ${data.snapshot}. Processed ${data.records_processed} records.`)

      // Invalidate queries to refresh data
      queryClient.invalidateQueries({ queryKey: ['rankings'] })
      queryClient.invalidateQueries({ queryKey: ['scores'] })
      queryClient.invalidateQueries({ queryKey: ['snapshots'] })

      // Show success message briefly before closing
      setTimeout(() => {
        handleReset()
        onClose()
      }, 3000)
    },
    onError: (error: Error) => {
      setError(error.message)
    },
  })

  const handleFileSelect = (file: File) => {
    if (!file.name.toLowerCase().endsWith('.xlsx') && !file.name.toLowerCase().endsWith('.xls')) {
      setError('Please select an Excel file (.xlsx or .xls)')
      return
    }
    
    setSelectedFile(file)
    setError(null)
  }

  const handleFileInputChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (file) {
      handleFileSelect(file)
    }
  }

  const handleDragOver = (event: React.DragEvent) => {
    event.preventDefault()
    setDragOver(true)
  }

  const handleDragLeave = (event: React.DragEvent) => {
    event.preventDefault()
    setDragOver(false)
  }

  const handleDrop = (event: React.DragEvent) => {
    event.preventDefault()
    setDragOver(false)
    
    const file = event.dataTransfer.files[0]
    if (file) {
      handleFileSelect(file)
    }
  }

  const handleSnapshotChange = (value: string) => {
    if (value === 'custom') {
      setUseCustomSnapshot(true)
      setSelectedSnapshot('')
    } else {
      setUseCustomSnapshot(false)
      setSelectedSnapshot(value)
      setCustomSnapshot('')
    }
  }

  const handleUpload = () => {
    if (!selectedFile) {
      setError('Please select a file')
      return
    }

    const snapshot = useCustomSnapshot ? customSnapshot : selectedSnapshot
    if (!snapshot) {
      setError('Please select or enter a snapshot')
      return
    }

    // Validate snapshot format
    const snapshotRegex = /^\d{4}H[12]$/
    if (!snapshotRegex.test(snapshot)) {
      setError('Snapshot must be in format YYYYH1 or YYYYH2 (e.g., 2024H1)')
      return
    }

    uploadMutation.mutate({ file: selectedFile, snapshot })
  }

  const handleReset = () => {
    setSelectedFile(null)
    setSelectedSnapshot('')
    setCustomSnapshot('')
    setUseCustomSnapshot(false)
    setError(null)
    setSuccessMessage(null)
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  const handleClose = () => {
    if (!uploadMutation.isPending) {
      handleReset()
      onClose()
    }
  }

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="sm" fullWidth>
      <DialogTitle>
        <Box display="flex" alignItems="center" justifyContent="space-between">
          <Box display="flex" alignItems="center" gap={1}>
            <FileUploadIcon />
            Upload Excel Data
          </Box>
          <IconButton onClick={handleClose} disabled={uploadMutation.isPending}>
            <CloseIcon />
          </IconButton>
        </Box>
      </DialogTitle>
      
      <DialogContent>
        <Stack spacing={3}>
          {/* File Upload Area */}
          <Box>
            <Typography variant="subtitle2" gutterBottom>
              Select Excel File
            </Typography>
            <Box
              sx={{
                border: 2,
                borderColor: dragOver ? 'primary.main' : 'grey.300',
                borderStyle: 'dashed',
                borderRadius: 2,
                p: 3,
                textAlign: 'center',
                bgcolor: dragOver ? 'action.hover' : 'background.paper',
                cursor: 'pointer',
                transition: 'all 0.2s ease-in-out',
                '&:hover': {
                  borderColor: 'primary.main',
                  bgcolor: 'action.hover',
                },
              }}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".xlsx,.xls"
                onChange={handleFileInputChange}
                style={{ display: 'none' }}
              />
              
              <CloudUploadIcon sx={{ fontSize: 48, color: 'text.secondary', mb: 1 }} />
              
              {selectedFile ? (
                <Box>
                  <Typography variant="body1" color="primary">
                    {selectedFile.name}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
                  </Typography>
                </Box>
              ) : (
                <Box>
                  <Typography variant="body1" gutterBottom>
                    Drag and drop your Excel file here, or click to browse
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Supports .xlsx and .xls files
                  </Typography>
                </Box>
              )}
            </Box>
          </Box>

          {/* Snapshot Selection */}
          <Box>
            <Typography variant="subtitle2" gutterBottom>
              Target Snapshot
            </Typography>
            <FormControl fullWidth>
              <InputLabel>Select Snapshot</InputLabel>
              <Select
                value={useCustomSnapshot ? 'custom' : selectedSnapshot}
                onChange={(e) => handleSnapshotChange(e.target.value)}
                label="Select Snapshot"
              >
                {availableSnapshots.map((snapshot) => (
                  <MenuItem key={snapshot} value={snapshot}>
                    {snapshot}
                    {snapshot === currentSnapshot && ' (Current)'}
                  </MenuItem>
                ))}
                <MenuItem value="custom">Enter Custom Snapshot...</MenuItem>
              </Select>
            </FormControl>
            
            {useCustomSnapshot && (
              <TextField
                fullWidth
                label="Custom Snapshot"
                placeholder="e.g., 2024H1"
                value={customSnapshot}
                onChange={(e) => setCustomSnapshot(e.target.value)}
                sx={{ mt: 2 }}
                helperText="Format: YYYYH1 or YYYYH2"
              />
            )}
          </Box>

          {/* Upload Progress */}
          {uploadMutation.isPending && (
            <Box>
              <Typography variant="body2" gutterBottom>
                Uploading...
              </Typography>
              <LinearProgress />
            </Box>
          )}

          {/* Error Display */}
          {error && (
            <Alert severity="error" onClose={() => setError(null)}>
              {error}
            </Alert>
          )}

          {/* Success Message */}
          {successMessage && (
            <Alert severity="success">
              {successMessage}
            </Alert>
          )}

          {/* Info */}
          <Alert severity="info">
            <Typography variant="body2">
              <strong>Note:</strong> The uploaded data will replace all existing data for the selected snapshot.
              Make sure your Excel file follows the same format as the current data source with:
            </Typography>
            <Box component="ul" sx={{ mt: 1, mb: 0, pl: 2 }}>
              <li>A "Scores" sheet containing metric data</li>
              <li>First column named "metrics" with metric names</li>
              <li>Subsequent columns with member aliases (Dev01, PMO01, etc.)</li>
              <li>Score values as numbers between the metric's min/max range</li>
            </Box>
          </Alert>
        </Stack>
      </DialogContent>
      
      <DialogActions>
        <Button onClick={handleClose} disabled={uploadMutation.isPending}>
          Cancel
        </Button>
        <Button
          onClick={handleUpload}
          variant="contained"
          disabled={!selectedFile || (!selectedSnapshot && !customSnapshot) || uploadMutation.isPending}
          startIcon={<CloudUploadIcon />}
        >
          Upload
        </Button>
      </DialogActions>
    </Dialog>
  )
}

export default ExcelUpload
