# Team Stack Ranking Manager

A web application for managers to view, compare, and adjust the stack rank of team members based on role-specific weighted metrics.

## Features

- **Stack Rank Table**: View team member rankings with role-based filtering and mismatch highlighting
- **Score Adjustment**: Guided interface to adjust member scores with preview and validation
- **Organizational Percentiles**: View team distribution across percentile buckets by role
- **Role-Aware Ranking**: Separate rankings within each role cohort using weighted metrics
- **Excel Integration**: Load data from Excel files and save changes back

## Architecture

### Backend (FastAPI + Python)

- **FastAPI** web framework with automatic API documentation
- **Pandas** for data manipulation and Excel file handling
- **OpenPyXL** for Excel file read/write operations
- **Pydantic** for data validation and serialization

### Frontend (React + TypeScript)

- **React 18** with TypeScript for type safety
- **Material-UI (MUI)** for consistent UI components
- **React Query** for efficient data fetching and caching
- **React Router** for client-side routing
- **Vite** for fast development and building

## Quick Start

### Prerequisites

- Python 3.8+
- Node.js 16+
- npm or yarn

### Backend Setup

1. Install Python dependencies:

```bash
pip install -r requirements.txt
```

2. Configure environment (optional):

```bash
cp .env.example .env
# Edit .env with your settings
```

3. Start the backend server:

```bash
python start_backend.py
```

The backend will be available at `http://localhost:8000`
API documentation at `http://localhost:8000/docs`

### Frontend Setup

1. Navigate to frontend directory:

```bash
cd frontend
```

2. Install dependencies:

```bash
npm install
```

3. Start the development server:

```bash
npm run dev
```

The frontend will be available at `http://localhost:3000`

## Data Sources

The application supports two data sources:

### 1. Excel/CSV Files (Default)

The traditional data source using Excel files with three sheets or CSV files.

### 2. SQLite Database (New)

A modern database approach with proper relational structure and integer-based scoring.

## Data Source Configuration

Set the `DATA_SOURCE` environment variable to choose your data source:

- `DATA_SOURCE=excel` - Use Excel/CSV files (default)
- `DATA_SOURCE=sqlite` - Use SQLite database

### Quick Start Options

**Option 1: Start with Excel/CSV (existing data)**

```bash
python start_with_excel.py
```

**Option 2: Start with SQLite and seed mock data**

```bash
python start_with_sqlite.py --seed
```

**Option 3: Start with SQLite (empty database)**

```bash
python start_with_sqlite.py
```

## Data Format

### Excel/CSV Format

The application expects data in Excel format with three sheets:

### Roles Sheet

```csv
alias,role
Dev01,Dev
PMO01,PMO
ET01,eTrading
RISK01,RISK
```

### Scores Sheet

```csv
metrics,Dev,PMO,eTrading,RISK,Max,Min,Dev01,PMO01,ET01,RISK01,...
Code Quality,0.87,0.0,0.0,0.0,0.95,0.15,0.75,0.5,0.5,0.5,...
Planning Accuracy,0.0,0.88,0.0,0.0,0.95,0.15,0.5,0.82,0.5,0.5,...
```

### ExpectedRanking Sheet

```csv
alias,role,rank
Dev01,Dev,5
PMO01,PMO,3
ET01,eTrading,2
RISK01,RISK,1
```

### SQLite Database Format

The SQLite database uses a normalized relational structure:

**Tables:**

- `members` - Team members (id, alias, role)
- `metrics` - Performance metrics (id, name, min_value, max_value)
- `metric_weights` - Role-specific weights for metrics (metric_id, role, weight as integer 0-1000)
- `scores` - Individual scores (member_id, metric_id, score as integer 0-10)
- `expected_rankings` - Expected rankings (member_id, rank)

**Key Differences from Excel/CSV:**

- Scores are stored as integers (0-10) instead of floats
- Weights are stored as integers (0-1000) instead of floats (0.0-1.0)
- Proper foreign key relationships between tables
- Better data integrity and query performance

## API Endpoints

### GET Endpoints

- `GET /api/roles` - Get all roles and member counts
- `GET /api/members` - Get all team members
- `GET /api/metrics` - Get all metrics with role weights
- `GET /api/scores` - Get all member scores
- `GET /api/rankings?roles=Dev,PMO` - Get rankings for specified roles
- `GET /api/mismatches` - Get members with rank mismatches
- `GET /api/percentiles?basis=weighted` - Get percentile distribution

### POST Endpoints

- `POST /api/adjust/preview` - Preview score adjustments
- `POST /api/adjust/apply` - Apply score changes and save

### Database Management Endpoints (New)

- `GET /api/data-source` - Get current data source information
- `POST /api/database/migrate` - Migrate data from Excel/CSV to SQLite
- `POST /api/database/seed` - Seed SQLite database with mock data

## Core Algorithms

### Weighted Score Calculation

For each member, the weighted score is calculated as:

```
weighted_score = Σ(metric_score × role_weight) for all applicable metrics
```

### Ranking Algorithm

- Rankings are calculated within role cohorts
- Uses dense ranking (ties get same rank, next rank continues sequentially)
- Deterministic tie-breaking by member alias

### Auto-Adjustment Algorithm

1. Calculate target weighted score based on reference member and percentage
2. Distribute score changes proportionally across selected metrics by role weight
3. Apply min/max clamping with iterative refinement
4. Report achieved score and any clamped metrics

## Configuration

Environment variables (`.env` file):

```
EXCEL_PATH=rank.xlsx
PORT=8000
LOG_LEVEL=INFO
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

## Development

### Running Tests

```bash
python test_backend.py
```

### Building for Production

```bash
# Backend
python -m uvicorn main:app --host 0.0.0.0 --port 8000

# Frontend
cd frontend
npm run build
```

## Troubleshooting

### Common Issues

1. **Excel file not found**: Ensure `rank.xlsx` exists or CSV files are available as fallback
2. **CORS errors**: Check that frontend URL is in `CORS_ORIGINS` environment variable
3. **Data validation errors**: Verify Excel/CSV file format matches expected schema

### Logs

Backend logs are written to console with configurable log level.

## License

This project is for internal use only.
