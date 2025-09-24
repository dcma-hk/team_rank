# SQLite Migration Guide

## Overview

The Team Stack Ranking Manager now supports both Excel/CSV files and SQLite database as data sources. This guide explains the new SQLite functionality and how to use it.

## Key Features

### 1. Dual Data Source Support
- **Excel/CSV**: Original file-based approach (default)
- **SQLite**: New database approach with better performance and data integrity

### 2. Integer-Based Scoring System
- **Scores**: Stored as integers 0-10 (instead of floats 0.0-1.0)
- **Weights**: Stored as integers 0-1000 (instead of floats 0.0-1.0)
- **Better precision**: No floating-point rounding issues

### 3. Normalized Database Schema
- **members**: Team members with roles
- **metrics**: Performance metrics with min/max bounds
- **metric_weights**: Role-specific weights for each metric
- **scores**: Individual member scores for each metric
- **expected_rankings**: Expected rankings for comparison

## Quick Start

### Option 1: Start with SQLite and Mock Data
```bash
python start_with_sqlite.py --seed
```
This will:
- Create a new SQLite database (`ranking.db`)
- Populate it with realistic mock data
- Start the server on port 8000

### Option 2: Start with Existing Excel/CSV Data
```bash
python start_with_excel.py
```
This maintains the original behavior using Excel/CSV files.

### Option 3: Migrate from Excel/CSV to SQLite
1. Start with Excel/CSV data source
2. Use the migration API endpoint: `POST /api/database/migrate`
3. Switch to SQLite data source and restart

## Configuration

Set environment variables to control data source:

```bash
# For SQLite
export DATA_SOURCE=sqlite
export SQLITE_PATH=ranking.db

# For Excel/CSV (default)
export DATA_SOURCE=excel
export EXCEL_PATH=rank.xlsx
```

## API Changes

### New Endpoints

- `GET /api/data-source` - Get current data source information
- `POST /api/database/migrate` - Migrate from Excel/CSV to SQLite
- `POST /api/database/seed` - Seed SQLite with mock data

### Existing Endpoints
All existing API endpoints work with both data sources without changes.

## Data Format Differences

### Excel/CSV Format
```csv
# Scores.csv - scores as floats (0.0-1.0)
metrics,Dev,PMO,eTrading,RISK,Max,Min,Dev01,Dev02,...
Code Quality,0.870,0.0,0.0,0.0,0.950,0.150,0.750,0.820,...
```

### SQLite Format
```sql
-- Scores as integers (0-10)
INSERT INTO scores (member_id, metric_id, score) VALUES (1, 1, 8);

-- Weights as integers (0-1000)
INSERT INTO metric_weights (metric_id, role, weight) VALUES (1, 'Dev', 870);
```

## Mock Data Specifications

When seeding mock data, the system creates:

- **40 members**: 10 each for Dev, PMO, eTrading, RISK roles
- **24 metrics**: Role-specific performance metrics
- **960 scores**: Each member scored on each metric (40 × 24)
- **40 expected rankings**: 1-10 ranking for each role

### Score Distribution
- **Relevant metrics**: Scores 3-10 (higher for role-specific metrics)
- **Non-relevant metrics**: Scores 0-5 (lower for non-applicable metrics)

### Weight Distribution
- **Role-specific weights**: 550-930 (out of 1000)
- **Non-applicable weights**: 0

## Migration Process

The migration process:
1. Reads all data from Excel/CSV files
2. Creates normalized SQLite tables
3. Converts float scores/weights to integers
4. Maintains all relationships and expected rankings

## Benefits of SQLite

1. **Performance**: Faster queries and data operations
2. **Integrity**: Foreign key constraints and data validation
3. **Scalability**: Better handling of large datasets
4. **Reliability**: ACID transactions and data consistency
5. **Portability**: Single file database, easy to backup/share

## Frontend Compatibility

The frontend remains completely unchanged and works with both data sources transparently. All existing functionality is preserved.

## File Structure

```
team_rank/
├── ranking.db              # SQLite database (created when using SQLite)
├── start_with_sqlite.py    # Start server with SQLite
├── start_with_excel.py     # Start server with Excel/CSV
├── backend/
│   ├── sqlite_data_manager.py      # SQLite data operations
│   ├── data_manager_factory.py     # Data source factory
│   └── models.py                   # Updated with SQLite models
└── ...
```

## Troubleshooting

### Common Issues

1. **Missing SQLAlchemy**: Install with `pip install sqlalchemy==2.0.23`
2. **Database locked**: Ensure no other processes are using the database
3. **Migration fails**: Check that source CSV/Excel files are valid

### Verification

Check if SQLite is working:
```bash
# Check database exists
ls -la ranking.db

# Check data was seeded
sqlite3 ranking.db "SELECT COUNT(*) FROM members;"
```

## Next Steps

1. Test the SQLite functionality with your data
2. Consider migrating to SQLite for better performance
3. Use the new integer-based scoring for more precise calculations
4. Leverage the database management endpoints for data operations
