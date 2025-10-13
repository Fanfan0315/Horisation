# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Horisation is a Flask-based web application for CSV/Excel data analysis and financial modeling. It provides file upload, preview, data summarization, and financial calculation capabilities through a web interface.

## Architecture

### Backend Structure
- **app.py**: Main Flask application entry point with route definitions
- **Backend/Controller/**: Request handling and business logic
  - `csvcontroller.py`: Blueprint-based API endpoints for CSV/Excel operations with encoding fallback
  - `csv_handling.py`: Core data processing functions (cleaning, merging, exporting)
- **Backend/Horfunc/**: Financial and analytical functions
  - `finpkg.py`: Monte Carlo price simulation using Geometric Brownian Motion
- **Backend/Sandbox/**: Experimental/testing code

### Frontend Structure
- **Template/**: Jinja2 HTML templates
  - `Home.html`: Base layout template
  - `CSV.html`: CSV upload and preview interface
  - `hormemo.html`: Memo/notes interface
  - `limit.html`: Limit tracking interface
  - `horbase.html`: Shared base template components
- **Static/**: Frontend assets
  - `js/horcsv.js`: CSV upload, drag-drop, preview/summary client logic
  - `js/hormemo.js`: Memo functionality
  - `css/`: Styling files
  - `pic/`: Images

### Data Flow
1. User uploads CSV/Excel via drag-drop or file picker
2. Frontend JavaScript (horcsv.js) sends file to API endpoint
3. Backend attempts UTF-8 encoding, falls back to GBK/GB2312/Big5/etc.
4. Pandas processes the file and returns preview or summary
5. Results rendered in browser table

## Development Commands

### Running the Application
```bash
# Start development server
python app.py

# Server runs on http://localhost:5000 with debug mode enabled
```

### Key Dependencies
```bash
# Install required packages
pip install flask pandas numpy openpyxl xlrd
```

**Note**: Excel support requires:
- `.xlsx` files → `openpyxl`
- `.xls` files → `xlrd`

### Testing Endpoints

**Preview API** (first N rows):
```bash
# Default UTF-8
curl -X POST -F "file=@data.csv" "http://localhost:5000/api/csv/preview?n=10"

# Custom encoding
curl -X POST -F "file=@data.csv" "http://localhost:5000/api/csv/preview?n=5&encoding=gbk"

# Custom separator
curl -X POST -F "file=@data.csv" "http://localhost:5000/api/csv/preview?sep=%3B"  # semicolon
```

**Summary API** (full file statistics):
```bash
curl -X POST -F "file=@data.csv" "http://localhost:5000/api/csv/summary"
```

## Important Technical Details

### Encoding Handling
The `csvcontroller.py` implements robust encoding detection with fallback chain:
1. UTF-8 (with PyArrow if available)
2. UTF-8-SIG (BOM handling)
3. Local encodings: GBK → GB2312 → Big5 → Shift_JIS → CP1252
4. Final fallback: Latin1

**When adding encoding support**: Update the fallback list in `_read_csv_with_fallback()` at line 58.

### File Upload Configuration
- Max file size: 100MB (`MAX_BYTES` in csvcontroller.py:11)
- Max request size: 20MB (`MAX_CONTENT_LENGTH` in app.py:16)
- Allowed extensions: `.csv`, `.xls`, `.xlsx`
- Upload directory: `_uploads/` (created automatically)

**To change limits**: Update both `MAX_BYTES` and `app.config['MAX_CONTENT_LENGTH']`.

### Data Processing Pipeline

**CSV Cleaning** (`csv_handling.py`):
- Column names: Uppercase + strip whitespace + deduplicate
- Cell values: Strip whitespace for string columns
- Deduplication: Drop duplicates with configurable `subset` and `keep` parameters

**DataFrame Merging** (`concat_dfs()`):
- Vertical concatenation (row-wise)
- Column union (missing columns filled with NaN)
- Optional column aliasing for name normalization

### Financial Functions

**Monte Carlo Simulation** (`finpkg.py`):
```python
simulate_price(S0, vol_annual, T, seed=None, basis=252)
```
- Uses Geometric Brownian Motion: `S_T = S0 * exp(-0.5σ²T + σ√T * Z)`
- Default basis: 252 trading days
- Reads from `PFE_Results.xlsx` for batch calculations

## Common Development Tasks

### Adding New API Endpoints
1. Add route function to `csvcontroller.py` blueprint
2. Use `_get_file_and_bytes()` helper for file validation
3. Return `jsonify({'ok': True/False, ...})` format
4. Register blueprint in `app.py` if creating new module

### Adding New Templates
1. Create HTML in `Template/` directory
2. Extend `Home.html` base template using `{% extends "Home.html" %}`
3. Add route in `app.py` with `active_page` parameter
4. Link static files via `{{ url_for('static', filename='...') }}`

### Modifying File Processing
- **Preview logic**: Edit `read_csv_preview()` in csvcontroller.py:127
- **Summary logic**: Edit `summarize_csv()` in csvcontroller.py:138
- **Type inference**: Regex patterns in summarize_csv:166-172
- **Missing value detection**: Line 147 checks for '', 'nan', 'None', NaN

### Frontend JavaScript Patterns
- Uses vanilla JavaScript with IIFE pattern `(() => { ... })()`
- DOM selection: `const $ = (id) => document.getElementById(id)`
- Drag-drop counter pattern prevents flicker (dragCounter)
- Fetch API with FormData for file uploads

## Routes

- `/` → Home page
- `/csv` → CSV upload workspace
- `/hormemo` → Memo interface
- `/limit` → Limit tracking
- `/api/csv/preview` → Preview first N rows
- `/api/csv/summary` → Full file statistics

## Template Variables
- `active_page`: Highlights current nav item ('home', 'csv', 'hormemo', 'limit')
- Static files: `{{ url_for('static', filename='path') }}`
- Templates: `{{ url_for('template', filename='path') }}`
