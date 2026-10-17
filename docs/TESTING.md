# Testing

## How to run

```bash
pip install -r requirements.txt pytest pytest-asyncio
pytest tests -v
```

The suite runs against the SQLite development fallback (configured in
`tests/conftest.py`) and does not require PostgreSQL or Docker. Each run uses
a fresh temporary database and model path.

## Test strategy

- **Unit tests** (`tests/unit/`):
  - `test_validation.py` — required fields, type checks, delay ranges, and
    actual/scheduled time consistency.
  - `test_features.py` — feature engineering column agreement between
    training and prediction, unseen-category encoding, empty history, and
    the model train/predict/persist roundtrip.
- **Integration tests** (`tests/integration/test_api.py`) — every endpoint:
  health, docs, ingestion (valid, missing columns, malformed rows, wrong
  extension, large input), listing/pagination/filters, statistics, empty
  result sets, distribution, trends (day/week/month + invalid period), top
  delayed, patterns, prediction (fallback baseline and after training),
  retraining on an empty database, and invalid payloads.

Edge cases covered: empty input, wrong input, large input (3000 rows),
malformed records, missing columns, unknown stop/line, and untrained-model
requests.

## Last executed result

```
41 passed
```

(Executed with Python 3.12, FastAPI 0.143, SQLAlchemy 2.1, pandas 2.2,
scikit-learn 1.9 on Linux.)
