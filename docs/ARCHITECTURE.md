# TransitPulse Architecture

## Overview
TransitPulse is a FastAPI-based web application for public transportation delay analysis and prediction. It follows a modular, layered architecture with clear separation of concerns.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Client Layer                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │  Dashboard   │  │  API Clients │  │  Ingestion Scripts   │  │
│  │  (HTML/JS)   │  │  (curl, etc) │  │  (CSV import)        │  │
│  └──────┬───────┘  └──────┬───────┘  └──────────┬────────────┘  │
└─────────┼─────────────────┼─────────────────────┼───────────────┘
          │                 │                     │
          ▼                 ▼                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                      API Layer (FastAPI)                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │  /api/v1/    │  │  /api/v1/    │  │  /api/v1/            │  │
│  │  delays      │  │  patterns    │  │  predict             │  │
│  │  (history)   │  │  (analysis)  │  │  (ML inference)      │  │
│  └──────┬───────┘  └──────┬───────┘  └──────────┬────────────┘  │
└─────────┼─────────────────┼─────────────────────┼───────────────┘
          │                 │                     │
          ▼                 ▼                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Service Layer                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │  Delay       │  │  Pattern     │  │  Prediction          │  │
│  │  Analytics   │  │  Detection   │  │  Service             │  │
│  └──────┬───────┘  └──────┬───────┘  └──────────┬────────────┘  │
└─────────┼─────────────────┼─────────────────────┼───────────────┘
          │                 │                     │
          ▼                 ▼                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Data Access Layer                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │  Delay       │  │  Stop/Line   │  │  Model               │  │
│  │  Repository  │  │  Repository  │  │  Repository          │  │
│  └──────┬───────┘  └──────┬───────┘  └──────────┬────────────┘  │
└─────────┼─────────────────┼─────────────────────┼───────────────┘
          │                 │                     │
          ▼                 ▼                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Database (PostgreSQL)                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │  delays      │  │  stops       │  │  models              │  │
│  │  table       │  │  table       │  │  table               │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Module Structure

```
transitpulse/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app factory
│   ├── config.py               # Configuration (pydantic-settings)
│   ├── database.py             # SQLAlchemy engine, session
│   ├── models/
│   │   ├── __init__.py
│   │   ├── delay.py            # DelayRecord, Stop, Line models
│   │   └── ml_model.py         # TrainedModel model
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── delay.py            # Pydantic schemas for delays
│   │   ├── analytics.py        # Response schemas
│   │   └── prediction.py       # Prediction request/response
│   ├── api/
│   │   ├── __init__.py
│   │   ├── v1/
│   │   │   ├── __init__.py
│   │   │   ├── delays.py       # Delay history endpoints
│   │   │   ├── patterns.py     # Pattern detection endpoints
│   │   │   ├── predict.py      # Prediction endpoints
│   │   │   └── ingestion.py    # Data ingestion endpoints
│   │   └── deps.py             # FastAPI dependencies
│   ├── services/
│   │   ├── __init__.py
│   │   ├── analytics.py        # Delay statistics calculations
│   │   ├── patterns.py         # Pattern detection algorithms
│   │   ├── prediction.py       # ML model inference
│   │   └── ingestion.py        # Data validation and import
│   ├── ml/
│   │   ├── __init__.py
│   │   ├── train.py            # Model training pipeline
│   │   ├── model.py            # Model wrapper (sklearn)
│   │   └── features.py         # Feature engineering
│   └── utils/
│       ├── __init__.py
│       ├── logging.py          # Structured logging setup
│       └── validation.py       # Data validation helpers
├── data/
│   ├── synthetic.py            # Synthetic data generator
│   └── sample_delays.csv       # Sample dataset
├── tests/
│   ├── __init__.py
│   ├── conftest.py             # Pytest fixtures
│   ├── unit/
│   │   ├── test_analytics.py
│   │   ├── test_patterns.py
│   │   ├── test_prediction.py
│   │   ├── test_validation.py
│   │   └── test_config.py
│   └── integration/
│       ├── test_api_delays.py
│       ├── test_api_patterns.py
│       ├── test_api_predict.py
│       └── test_ingestion.py
├── scripts/
│   ├── generate_data.py        # CLI for synthetic data
│   ├── train_model.py          # CLI for model training
│   └── ingest.py               # CLI for CSV ingestion
├── docker/
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── docker-compose.test.yml
├── .github/
│   └── workflows/
│       └── ci.yml
├── requirements.txt
├── requirements-dev.txt
├── pyproject.toml
├── .env.example
├── .gitignore
├── README.md
└── PLAN.md
```

## Data Flow

### 1. Data Ingestion Flow
```
CSV File → Validation → Transform → Database (delays table) → Log Result
```

### 2. Historical Analysis Flow
```
API Request → Query Repository → Aggregate (SQL/Pandas) → Format Response → JSON
```

### 3. Pattern Detection Flow
```
API Request → Query Repository → Statistical Analysis → Detect Patterns → Format Response → JSON
```

### 4. Prediction Flow
```
API Request → Load Model → Feature Engineering → Predict → Confidence Interval → Format Response → JSON
```

### 5. Model Training Flow (Batch)
```
Historical Data → Feature Engineering → Train (sklearn) → Evaluate → Persist Model → Store Metrics
```

## Database Schema

### delays table
| Column | Type | Description |
|--------|------|-------------|
| id | BIGSERIAL | Primary key |
| stop_id | VARCHAR(50) | Stop identifier |
| stop_name | VARCHAR(200) | Human-readable stop name |
| line | VARCHAR(50) | Line/route identifier |
| direction | VARCHAR(50) | Direction of travel |
| scheduled_time | TIMESTAMP | Planned arrival/departure |
| actual_time | TIMESTAMP | Actual arrival/departure |
| delay_minutes | INTEGER | Delay in minutes (can be negative) |
| date | DATE | Service date |
| vehicle_id | VARCHAR(50) | Vehicle identifier |
| created_at | TIMESTAMP | Ingestion timestamp |

Indexes: (stop_id, date), (line, date), (date)

### stops table
| Column | Type | Description |
|--------|------|-------------|
| stop_id | VARCHAR(50) | Primary key |
| stop_name | VARCHAR(200) | |
| latitude | DOUBLE PRECISION | Optional, for map display |
| longitude | DOUBLE PRECISION | Optional |
| lines | TEXT[] | Lines serving this stop |

### models table
| Column | Type | Description |
|--------|------|-------------|
| id | BIGSERIAL | Primary key |
| name | VARCHAR(100) | Model name/version |
| algorithm | VARCHAR(50) | e.g., "LinearRegression" |
| parameters | JSONB | Hyperparameters |
| metrics | JSONB | MAE, RMSE, R², etc. |
| model_blob | BYTEA | Pickled model |
| trained_at | TIMESTAMP | Training timestamp |
| is_active | BOOLEAN | Currently deployed model |

## Configuration

All configuration via environment variables (pydantic-settings):

| Variable | Default | Description |
|----------|---------|-------------|
| DATABASE_URL | postgresql://user:pass@localhost:5432/transitpulse | PostgreSQL connection |
| APP_HOST | 0.0.0.0 | Server host |
| APP_PORT | 8000 | Server port |
| LOG_LEVEL | INFO | Logging level |
| MODEL_PATH | ./models/latest.pkl | Default model path |
| CORS_ORIGINS | * | CORS allowed origins |
| SYNTHETIC_DATA_DAYS | 365 | Days of synthetic data to generate |

## API Design

### RESTful Endpoints (v1)

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/v1/delays | List delays with filters |
| GET | /api/v1/delays/stats | Statistics for stop/line/date range |
| GET | /api/v1/delays/distribution | Histogram data |
| GET | /api/v1/delays/trends | Time-series aggregates |
| GET | /api/v1/delays/top | Top N delayed stops/lines |
| GET | /api/v1/patterns | Detected delay patterns |
| POST | /api/v1/predict | Predict delay for stop/line/time |
| GET | /api/v1/predict/model/info | Model metadata and metrics |
| POST | /api/v1/ingest | Trigger CSV ingestion |
| GET | /api/v1/health | Health check |

### Error Response Format
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Human-readable description",
    "details": {}
  }
}
```

## Machine Learning

### Model: Delay Prediction
- **Algorithm**: Gradient Boosting Regressor (sklearn HistGradientBoostingRegressor)
- **Features**: 
  - Temporal: hour, day_of_week, month, is_weekend, is_holiday
  - Spatial: stop_id (encoded), line (encoded)
  - Historical: rolling average delay (1h, 24h, 7d), recent trend
- **Target**: delay_minutes (continuous)
- **Evaluation**: MAE, RMSE, R² on temporal holdout split

### Training Pipeline
1. Load historical data from database
2. Feature engineering (time features, lag features, encodings)
3. Temporal train/test split (last 20% by date)
4. Hyperparameter tuning (optuna or grid search)
5. Train final model on full training set
6. Evaluate on test set
7. Persist model and metrics to database
8. Update active model pointer

## Security Considerations

- SQL injection: SQLAlchemy ORM with parameterized queries
- Input validation: Pydantic schemas on all API inputs
- Secrets: Environment variables only, .env.example for documentation
- CORS: Configurable origins
- Rate limiting: Consider adding (middleware) for production

## Observability

- Structured JSON logging with correlation IDs
- Request/response logging middleware
- Database query logging (configurable)
- Health check endpoint for orchestration
- Metrics: request latency, error rates, prediction latency

## Deployment

### Docker Compose (Development)
- app: FastAPI application
- db: PostgreSQL 16
- (optional) pgadmin: Database UI

### Production Considerations
- Gunicorn with Uvicorn workers
- Reverse proxy (nginx) for TLS termination
- PostgreSQL connection pooling (PgBouncer)
- Model serving: in-process (current) or separate service (future)
- Monitoring: Prometheus + Grafana
- Logging aggregation: ELK or similar

## Implementation Stages

### Stage 1: Foundation (Week 1)
- Project setup, config, database models, basic FastAPI app
- Docker Compose for local development
- Basic health check endpoint

### Stage 2: Data Ingestion & Storage (Week 1-2)
- CSV ingestion pipeline with validation
- Synthetic data generator
- Basic CRUD for delays

### Stage 3: Analytics API (Week 2)
- Statistics endpoints (mean, median, percentiles)
- Distribution histogram
- Trends over time
- Top delayed stops/lines

### Stage 4: Pattern Detection (Week 2-3)
- Time-of-day pattern analysis
- Day-of-week analysis
- Line-specific chronic delays
- Pattern API endpoints

### Stage 5: ML Prediction (Week 3)
- Feature engineering
- Model training pipeline
- Prediction API
- Model persistence and versioning

### Stage 6: Dashboard (Week 3-4)
- Simple HTML/JS dashboard
- Delay heatmap visualization
- Historical charts
- Prediction query form

### Stage 7: Testing & Quality (Week 4)
- Unit tests for all services
- Integration tests for API
- CI/CD pipeline
- Code review fixes

### Stage 8: Documentation & Packaging (Week 4)
- README with setup instructions
- API documentation
- German project summary
- ZIP archive creation

## Technology Choices Rationale

| Component | Choice | Reason |
|-----------|--------|--------|
| Web Framework | FastAPI | Modern, async, auto OpenAPI, type-safe |
| ORM | SQLAlchemy 2.0 | Mature, async support, flexible |
| Database | PostgreSQL | Robust, analytical queries, JSONB for model storage |
| ML | scikit-learn | No GPU needed, interpretable, production-ready |
| Validation | Pydantic v2 | Fast, integrates with FastAPI |
| Config | pydantic-settings | Type-safe environment config |
| Testing | pytest | Standard, powerful fixtures |
| Linting | ruff | Fast, comprehensive |
| Type Check | mypy | Static analysis |
| Container | Docker | Reproducible environments |

## Future Extensibility

- Real-time data feeds (GTFS-RT, SIRI)
- Multiple model support (ensemble, A/B testing)
- User authentication and personalization
- Mobile app API
- Multi-city support
- Advanced analytics (anomaly detection, root cause)