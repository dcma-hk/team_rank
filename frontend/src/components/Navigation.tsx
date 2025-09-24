import React from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { Tabs, Tab, Box } from '@mui/material'

const Navigation: React.FC = () => {
  const navigate = useNavigate()
  const location = useLocation()

  const getCurrentTab = () => {
    if (location.pathname === '/') return 0
    if (location.pathname.startsWith('/adjust')) return 1
    if (location.pathname === '/org') return 2
    if (location.pathname === '/update') return 3
    return 0
  }

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    switch (newValue) {
      case 0:
        navigate('/')
        break
      case 1:
        // Don't navigate directly to adjust page without a member
        break
      case 2:
        navigate('/org')
        break
      case 3:
        navigate('/update')
        break
    }
  }

  return (
    <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
      <Tabs value={getCurrentTab()} onChange={handleTabChange} aria-label="navigation tabs">
        <Tab label="Stack Rank Table" />
        <Tab label="Adjust Scores" disabled={!location.pathname.startsWith('/adjust')} />
        <Tab label="Org Percentiles" />
        <Tab label="Update Data" />
      </Tabs>
    </Box>
  )
}

export default Navigation
