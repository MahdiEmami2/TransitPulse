# Security

## Secrets

- No secrets are committed. All configuration comes from environment
  variables (optionally a local `.env`, which is git-ignored via
  `.gitignore`).
- `.env.example` documents every variable with placeholder values only.

## Database access

- All queries go through the SQLAlchemy ORM with parameterized statements;
  no string-concatenated SQL is used anywhere.
- The only raw SQL is `SELECT 1` for the health check, passed via
  `text()` with no user input.
- Users supply filter values through FastAPI query parameters, which become
  bound parameters.

## Input validation

- CSV uploads: extension check, column check, per-row type/range validation
  (`transitpulse/app/utils/validation.py`). Invalid rows are rejected with
  explicit error messages, never silently stored.
- API payloads are validated by Pydantic schemas (types and required
  fields); invalid payloads return 422.
- Query parameters are range-checked (pagination, bin sizes, limits).

## Upload handling

- Only in-memory parsing of the uploaded CSV via `pandas.read_csv`; uploaded
  files are never written to disk or executed.
- File size is bounded by the server/proxy configuration; ingestion is
  batched (`INGEST_BATCH_SIZE`).

## Dependencies

- Versions are bounded ranges in `requirements.txt` and `pyproject.toml`.
- Run `pip audit` regularly; CI linting (`ruff`) runs in the workflow.

## Known limitations

- No authentication: the API is unauthenticated by design for the demo.
  Write endpoints (ingest, train, create record) must be protected before
  any real deployment.
- CORS defaults to `*` for development; restrict `CORS_ORIGINS` in
  production.
- Model artifacts are persisted with `pickle`; only load model files you
  produced yourself.
