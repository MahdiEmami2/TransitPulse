# TransitPulse Acceptance Criteria

## Functional Requirements

### FR1: Data Ingestion
- **FR1.1**: System accepts CSV files with public transport delay data (columns: stop_id, stop_name, line, direction, scheduled_time, actual_time, delay_minutes, date, vehicle_id)
- **FR1.2**: System validates incoming data (required fields, data types, reasonable ranges)
- **FR1.3**: System stores validated data in PostgreSQL database
- **FR1.4**: System provides API endpoint to trigger/manual ingestion
- **FR1.5**: System logs ingestion results (rows processed, errors, duplicates)

### FR2: Historical Delay Analysis
- **FR2.1**: API endpoint returns delay statistics for a given stop/line/date range (mean, median, min, max, std dev, percentiles)
- **FR2.2**: API endpoint returns delay distribution histogram data
- **FR2.3**: API endpoint returns top N most delayed stops/lines for a period
- **FR2.4**: API endpoint returns delay trends over time (daily/weekly/monthly aggregates)

### FR3: Delay Pattern Detection
- **FR3.1**: System identifies recurring delay patterns (time-of-day, day-of-week, line-specific)
- **FR3.2**: API endpoint returns detected patterns with confidence scores
- **FR3.3**: Patterns include: rush hour delays, weekend vs weekday, specific line chronic delays

### FR4: Delay Prediction
- **FR4.1**: ML model trained on historical data predicts delay for given stop/line/time
- **FR4.2**: API endpoint accepts stop_id, line, datetime and returns predicted delay with confidence interval
- **FR4.3**: Model performance metrics (MAE, RMSE, R²) available via API
- **FR4.4**: Model retraining triggered via API endpoint

### FR5: Dashboard
- **FR5.1**: Web UI displays interactive map/stops list with delay heatmap
- **FR5.2**: UI shows historical delay charts for selected stop/line
- **FR5.3**: UI allows delay prediction query with results display
- **FR5.4**: UI responsive and accessible (WCAG 2.1 AA basics)

### FR6: API & Documentation
- **FR6.1**: OpenAPI/Swagger documentation auto-generated and accessible at /docs
- **FR6.2**: All endpoints return appropriate HTTP status codes
- **FR6.3**: Error responses follow consistent JSON schema
- **FR6.4**: API versioned (v1 prefix)

## Non-Functional Requirements

### NFR1: Performance
- API response time < 500ms for 95th percentile (simple queries)
- Dashboard loads within 3 seconds
- Ingestion processes 10,000 rows in < 10 seconds

### NFR2: Reliability
- Database transactions ensure data consistency
- Graceful handling of database connection failures
- Input validation prevents injection attacks

### NFR3: Security
- No hardcoded secrets; all config via environment variables
- SQL injection prevention via ORM parameterization
- CORS configured appropriately

### NFR4: Maintainability
- Code coverage >= 80% for critical modules
- Type hints on all public functions
- Structured logging with correlation IDs
- Modular architecture with clear separation of concerns

### NFR5: Reproducibility
- One-command setup via Docker Compose (when daemon available)
- Virtual environment setup documented for Windows PowerShell and Linux
- Synthetic data generator for demo without external dependencies

## Test Strategy

### Unit Tests (pytest)
- Data validation functions
- Delay analytics calculations
- ML model training/inference functions
- Configuration loading
- Database model methods

### Integration Tests
- API endpoint responses (status codes, schema)
- Database CRUD operations
- Ingestion pipeline end-to-1
- Model prediction API

### Test Data
- Synthetic dataset with known patterns for deterministic tests
- Edge cases: empty data, missing values, extreme delays

### CI Pipeline (GitHub Actions)
- Lint (ruff/flake8)
- Type check (mypy)
- Unit tests
- Integration tests (with testcontainers or postgres service)
- Build Docker image

## Definition of Done
- All acceptance criteria implemented and tested
- Documentation complete and matches implementation
- No critical or high-severity security findings
- Test coverage >= 80%
- ZIP archive created and verified