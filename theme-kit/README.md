# SVG Kimi Frontend Theme Kit

This folder contains a portable theme and style kit extracted from the frontend so you can reuse the look-and-feel in other apps.

Contents:
- theme.ts: MUI light/dark themes with component overrides and tokens
- ThemeContext.tsx: Simple dark/light mode context (localStorage + prefers-color-scheme)
- styles.css: Global CSS tokens/utilities (status colors, stage colors, spacing, radius, common utility classes)
- index.ts: Barrel exports for convenience

## How to Use in Another React + MUI App

1) Copy this `theme-kit` folder into your target project (or publish as an internal npm package if you prefer).

2) Ensure dependencies exist in the target app:
   - @mui/material
   - @emotion/react
   - @emotion/styled

3) Import the CSS tokens once (e.g., in main.tsx or App.tsx):
   import './theme-kit/styles.css';

4) Wrap your app with the theme providers:

   import { ThemeProvider } from '@mui/material/styles';
   import CssBaseline from '@mui/material/CssBaseline';
   import { CustomThemeProvider, useThemeMode } from './theme-kit/ThemeContext';
   import { getTheme } from './theme-kit/theme';

   const ThemedApp: React.FC = () => {
     const { isDarkMode } = useThemeMode();
     const theme = getTheme(isDarkMode);
     return (
       <ThemeProvider theme={theme}>
         <CssBaseline />
         {/* your app here */}
       </ThemeProvider>
     );
   };

   // At the root:
   <CustomThemeProvider>
     <ThemedApp />
   </CustomThemeProvider>

5) Toggle dark/light anywhere:
   import { useThemeMode } from './theme-kit/ThemeContext';
   const { isDarkMode, toggleTheme } = useThemeMode();

6) Optional: Include Inter font for best typography match
   Add in index.html <head>:
   <link rel="preconnect" href="https://fonts.googleapis.com">
   <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous">
   <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">

## Notes
- The styles.css defines CSS variables and utility classes for status chips, stage colors, spacing, and shared surfaces used throughout the app.
- MUI component overrides in theme.ts replicate the rounded surfaces, compact tables, and subdued elevation.
- If your target app does not use MUI, you can still reuse styles.css; the MUI theme will not apply without MUI.

