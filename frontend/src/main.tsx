import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ThemeProvider } from '@mui/material/styles'
import CssBaseline from '@mui/material/CssBaseline'
import { CustomThemeProvider, useThemeMode } from './theme-kit/ThemeContext'
import { getTheme } from './theme-kit/theme'
import './theme-kit/styles.css'
import App from './App'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutes
      refetchOnWindowFocus: false,
    },
  },
})

const ThemedApp: React.FC = () => {
  const { isDarkMode } = useThemeMode()
  const theme = getTheme(isDarkMode)

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </ThemeProvider>
  )
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <CustomThemeProvider>
        <ThemedApp />
      </CustomThemeProvider>
    </QueryClientProvider>
  </React.StrictMode>,
)
