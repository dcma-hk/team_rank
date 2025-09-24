import React from 'react'
import { Routes, Route } from 'react-router-dom'
import { Container, AppBar, Toolbar, Typography, Box, IconButton } from '@mui/material'
import { Brightness4, Brightness7 } from '@mui/icons-material'
import { useThemeMode } from './theme-kit/ThemeContext'
import StackRankTable from './pages/StackRankTable'
import AdjustScores from './pages/AdjustScores'
import OrgPercentiles from './pages/OrgPercentiles'
import UpdateData from './pages/UpdateData'
import Navigation from './components/Navigation'

function App() {
  const { isDarkMode, toggleTheme } = useThemeMode()

  return (
    <Box sx={{ flexGrow: 1 }}>
      <AppBar position="static" elevation={0}>
        <Toolbar>
          <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
            Team Stack Ranking Manager
          </Typography>
          <IconButton
            color="inherit"
            onClick={toggleTheme}
            aria-label="toggle theme"
          >
            {isDarkMode ? <Brightness7 /> : <Brightness4 />}
          </IconButton>
        </Toolbar>
      </AppBar>

      <Navigation />

      <Container maxWidth="xl" sx={{ mt: 3, mb: 3 }}>
        <Routes>
          <Route path="/" element={<StackRankTable />} />
          <Route path="/adjust/:alias" element={<AdjustScores />} />
          <Route path="/org" element={<OrgPercentiles />} />
          <Route path="/update" element={<UpdateData />} />
        </Routes>
      </Container>
    </Box>
  )
}

export default App
