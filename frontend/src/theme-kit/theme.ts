import { createTheme, ThemeOptions } from '@mui/material/styles';

// Common theme configuration
const common = {
  typography: {
    fontFamily: '"Inter", "Roboto", "Helvetica", "Arial", sans-serif',
    fontSize: 14,
    h1: { fontSize: '2rem', fontWeight: 700 },
    h2: { fontSize: '1.75rem', fontWeight: 600 },
    h3: { fontSize: '1.5rem', fontWeight: 600 },
    h4: { fontSize: '1.25rem', fontWeight: 600 },
    h5: { fontSize: '1.125rem', fontWeight: 600 },
    h6: { fontSize: '1rem', fontWeight: 600 },
    body1: { fontSize: '0.875rem' },
    body2: { fontSize: '0.75rem' },
    button: { textTransform: 'none' as const, fontWeight: 600 },
  },
  shape: { borderRadius: 10 },
  spacing: 8,
  breakpoints: {
    values: { xs: 0, sm: 600, md: 900, lg: 1200, xl: 1536 },
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: { textTransform: 'none', borderRadius: 8, fontWeight: 600, fontSize: '14px' },
        contained: { boxShadow: 'none', '&:hover': { boxShadow: 'none' } },
      },
    },
    MuiPaper: {
      styleOverrides: { root: { borderRadius: 10, boxShadow: '0 2px 4px rgba(0, 0, 0, 0.1)' } },
    },
    MuiCard: {
      styleOverrides: { root: { borderRadius: 10, boxShadow: '0 2px 4px rgba(0, 0, 0, 0.1)' } },
    },
    MuiTableContainer: {
      styleOverrides: { root: { borderRadius: '10px', boxShadow: '0px 1px 2px rgba(0, 0, 0, 0.06)', overflow: 'hidden' } },
    },
    MuiTableHead: {
      styleOverrides: {
        root: {
          backgroundColor: 'rgba(37, 99, 235, 0.05)',
          '& .MuiTableCell-head': {
            padding: '12px 16px', fontSize: '13px', fontWeight: 600, color: 'text.secondary', textTransform: 'uppercase', letterSpacing: '0.5px',
          },
        },
      },
    },
    MuiTableBody: {
      styleOverrides: { root: { '& .MuiTableRow-root': { '&:hover': { backgroundColor: 'rgba(37, 99, 235, 0.02)' } } } },
    },
    MuiTableCell: {
      styleOverrides: {
        root: { padding: '16px' },
        head: { fontWeight: 600, fontSize: '13px', color: 'text.secondary', textTransform: 'uppercase', letterSpacing: '0.5px' },
        body: { fontSize: '14px' },
      },
    },
    MuiTable: { styleOverrides: { root: { borderRadius: 10 } } },
    MuiChip: {
      styleOverrides: {
        root: { borderRadius: 16, fontWeight: 600, fontSize: '12px', height: 24, lineHeight: 1.4 },
        sizeSmall: { fontSize: '11px', height: 22 },
      },
    },
    MuiIconButton: {
      styleOverrides: { root: { borderRadius: '50%', width: 32, height: 32, '&:hover': { backgroundColor: 'rgba(37, 99, 235, 0.1)' } } },
    },
    MuiToolbar: { styleOverrides: { root: { minHeight: '64px !important' } } },
  },
} satisfies ThemeOptions;

// Light theme
export const lightTheme = createTheme({
  ...common,
  palette: {
    mode: 'light',
    primary: { main: '#2563EB', dark: '#1D4ED8', light: '#60A5FA' },
    secondary: { main: '#0EA5E9' },
    success: { main: '#16A34A' },
    warning: { main: '#D97706' },
    error: { main: '#DC2626' },
    info: { main: '#0EA5E9' },
    text: { primary: '#111827', secondary: '#374151', disabled: '#9CA3AF' },
    background: { default: '#F9FAFB', paper: '#FFFFFF' },
    divider: '#E5E7EB',
  },
});

// Dark theme
export const darkTheme = createTheme({
  ...common,
  palette: {
    mode: 'dark',
    primary: { main: '#5B8CFF', dark: '#4F7CFF', light: '#7BA3FF' },
    secondary: { main: '#38BDF8' },
    success: { main: '#22C55E' },
    warning: { main: '#F59E0B' },
    error: { main: '#F87171' },
    info: { main: '#38BDF8' },
    text: { primary: '#F3F4F6', secondary: '#D1D5DB', disabled: '#9CA3AF' },
    background: { default: '#0B1016', paper: '#111827' },
    divider: '#2D343B',
  },
  components: {
    ...common.components,
    MuiPaper: { styleOverrides: { root: { borderRadius: 10, boxShadow: '0 2px 4px rgba(0, 0, 0, 0.3)', backgroundImage: 'none' } } },
    MuiTableHead: {
      styleOverrides: {
        root: {
          backgroundColor: 'rgba(91, 140, 255, 0.08)',
          '& .MuiTableCell-head': {
            padding: '12px 16px', fontSize: '13px', fontWeight: 600, color: '#D1D5DB', textTransform: 'uppercase', letterSpacing: '0.5px', borderBottom: '1px solid #2D343B',
          },
        },
      },
    },
    MuiTableBody: {
      styleOverrides: {
        root: {
          '& .MuiTableRow-root': {
            '&:hover': { backgroundColor: 'rgba(91, 140, 255, 0.04)' },
            '&:nth-of-type(odd)': { backgroundColor: 'rgba(255, 255, 255, 0.02)' },
          },
        },
      },
    },
    MuiTableCell: { styleOverrides: { root: { borderBottom: '1px solid #2D343B' }, body: { color: '#D1D5DB' } } },
    MuiDialog: { styleOverrides: { paper: { backgroundImage: 'none', backgroundColor: '#111827' } } },
    MuiDialogTitle: { styleOverrides: { root: { color: '#F3F4F6' } } },
    MuiDialogContent: { styleOverrides: { root: { color: '#D1D5DB' } } },
    MuiAlert: {
      styleOverrides: {
        root: { borderRadius: 8 },
        standardError: { backgroundColor: 'rgba(248, 113, 113, 0.1)', color: '#F87171', '& .MuiAlert-icon': { color: '#F87171' } },
        standardWarning: { backgroundColor: 'rgba(245, 158, 11, 0.1)', color: '#F59E0B', '& .MuiAlert-icon': { color: '#F59E0B' } },
        standardSuccess: { backgroundColor: 'rgba(34, 197, 94, 0.1)', color: '#22C55E', '& .MuiAlert-icon': { color: '#22C55E' } },
      },
    },
  },
});

// Function to get theme based on mode
export const getTheme = (isDarkMode: boolean) => (isDarkMode ? darkTheme : lightTheme);

// Default export for convenience
export default lightTheme;
