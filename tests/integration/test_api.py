"""Integration tests for the FastAPI endpoints (SQLite fallback database)."""
import pytest
from fastapi.testclient import TestClient

from transitpulse.app.main import app
from transitpulse.app.services.ingestion import generate_sample_data

CSV_HEADER = (
    "stop_id,stop_name,line,direction,scheduled_time,actual_time,"
    "delay_minutes,date,vehicle_id\n"
)


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def seeded_db(client):
    """Seed the database with synthetic data and return a clean client."""
    import asyncio

    from transitpulse.app.database import async_session, init_db
    from transitpulse.app.services.ingestion import ingest_csv_data

    async def seed():
        await init_db()
        csv_data = generate_sample_data(300)
        async with async_session() as s:
            return await ingest_csv_data(csv_data, s)

    processed, inserted, errors = asyncio.run(seed())
    assert inserted > 0, f"seeding failed: {errors[:3]}"
    return client


def test_health_check(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["service"] == "transitpulse"
    assert body["status"] in ("healthy", "degraded")


def test_root_endpoint(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "docs" in r.json()


def test_openapi_docs(client):
    assert client.get("/docs").status_code == 200
    assert client.get("/openapi.json").status_code == 200


def test_ingest_csv_roundtrip(seeded_db):
    csv = CSV_HEADER + (
        "S1,Stop1,L1,North,2026-01-01T08:00:00,2026-01-01T08:05:00,5,2026-01-01,V1\n"
    )
    r = seeded_db.post("/api/v1/ingest/", files={"file": ("data.csv", csv, "text/csv")})
    assert r.status_code == 200
    body = r.json()
    assert body["rows_processed"] == 1
    assert body["rows_inserted"] == 1
    assert body["success"] is True


def test_ingest_missing_columns(seeded_db):
    r = seeded_db.post(
        "/api/v1/ingest/",
        files={"file": ("data.csv", b"stop_id,stop_name\n1,2\n", "text/csv")},
    )
    assert r.status_code == 200
    assert r.json()["rows_inserted"] == 0
    assert "Missing columns" in r.json()["errors"][0]


def test_ingest_wrong_extension(seeded_db):
    r = seeded_db.post(
        "/api/v1/ingest/", files={"file": ("data.txt", b"foo", "text/plain")}
    )
    assert r.status_code == 400


def test_ingest_malformed_rows_reported(seeded_db):
    csv = (
        CSV_HEADER
        + "S1,Stop1,L1,North,2026-01-01T08:00:00,2026-01-01T08:05:00,5,2026-01-01,V1\n"
        + "S2,Stop2,L2,South,not-a-date,2026-01-01T08:05:00,5,2026-01-01,V1\n"
        + ",,,,2026-01-01T08:00:00,2026-01-01T08:05:00,5,2026-01-01,\n"
    )
    r = seeded_db.post("/api/v1/ingest/", files={"file": ("data.csv", csv, "text/csv")})
    assert r.status_code == 200
    body = r.json()
    assert body["rows_processed"] == 3
    assert len(body["errors"]) >= 2


def test_ingest_large_input(seeded_db):
    csv = (CSV_HEADER + "S1,Stop1,L1,North,2026-01-01T08:00:00,2026-01-01T08:05:00,5,2026-01-01,V1\n" * 3000).encode()
    r = seeded_db.post("/api/v1/ingest/", files={"file": ("data.csv", csv, "text/csv")})
    assert r.status_code == 200
    assert r.json()["rows_processed"] == 3000
    assert r.json()["rows_inserted"] == 3000


def test_list_delays(seeded_db):
    r = seeded_db.get("/api/v1/delays/?page=1&size=10")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] >= 300
    assert len(body["items"]) == 10
    assert "date" in body["items"][0]


def test_list_delays_pagination(seeded_db):
    first = seeded_db.get("/api/v1/delays/?page=1&size=10").json()
    second = seeded_db.get("/api/v1/delays/?page=2&size=10").json()
    assert first["items"][0]["id"] != second["items"][0]["id"]
    assert second["page"] == 2


def test_list_delays_filters(seeded_db):
    r = seeded_db.get("/api/v1/delays/?line=LINE_01")
    assert r.status_code == 200
    assert all(item["line"] == "LINE_01" for item in r.json()["items"])


def test_delay_statistics(seeded_db):
    r = seeded_db.get("/api/v1/delays/stats")
    assert r.status_code == 200
    body = r.json()
    assert body["count"] > 0
    for key in ("mean", "median", "min", "max", "std_dev", "p10", "p25", "p75", "p90"):
        assert key in body


def test_delay_statistics_empty_filters_return_zero(seeded_db):
    r = seeded_db.get("/api/v1/delays/stats?stop_id=DOES_NOT_EXIST")
    assert r.status_code == 200
    assert r.json()["count"] == 0


def test_delay_distribution(seeded_db):
    r = seeded_db.get("/api/v1/delays/distribution?bin_size=5")
    assert r.status_code == 200
    bins = r.json()["bins"]
    assert len(bins) > 0
    assert sum(b["count"] for b in bins) > 0


def test_delay_trends(seeded_db):
    for period in ("day", "week", "month"):
        r = seeded_db.get(f"/api/v1/delays/trends?period={period}")
        assert r.status_code == 200, period
        assert len(r.json()["trends"]) > 0, period


def test_delay_trends_invalid_period(seeded_db):
    r = seeded_db.get("/api/v1/delays/trends?period=year")
    assert r.status_code == 422


def test_top_delayed(seeded_db):
    r = seeded_db.get("/api/v1/delays/top?group_by=stop&limit=5")
    assert r.status_code == 200
    assert len(r.json()["items"]) == 5
    r = seeded_db.get("/api/v1/delays/top?group_by=line&limit=3")
    assert r.status_code == 200
    assert len(r.json()["items"]) == 3


def test_patterns(seeded_db):
    r = seeded_db.get("/api/v1/patterns/")
    assert r.status_code == 200
    patterns = r.json()["patterns"]
    types = {p["pattern_type"] for p in patterns}
    assert types == {"rush_hour", "weekend_vs_weekday", "line_chronic"}
    assert all(0.0 <= p["confidence"] <= 1.0 for p in patterns)


def test_create_delay_record(seeded_db):
    payload = {
        "stop_id": "STOP_TEST",
        "stop_name": "Test Stop",
        "line": "LINE_TEST",
        "direction": "North",
        "scheduled_time": "2026-10-16T08:00:00",
        "actual_time": "2026-10-16T08:10:00",
        "delay_minutes": 10,
        "date": "2026-10-16",
    }
    r = seeded_db.post("/api/v1/delays/", json=payload)
    assert r.status_code == 201
    assert r.json()["stop_id"] == "STOP_TEST"


def test_predict_fallback_without_model(seeded_db):
    from transitpulse.app.services.prediction import prediction_service

    prediction_service._model = None
    r = seeded_db.post(
        "/api/v1/predict/",
        json={
            "stop_id": "STOP_001",
            "line": "LINE_01",
            "direction": "North",
            "scheduled_time": "2026-10-20T08:30:00",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["model_name"] == "historical_average_v1"
    assert body["confidence_lower"] <= body["predicted_delay_minutes"] <= body["confidence_upper"]


def test_predict_after_training(seeded_db):
    r = seeded_db.post("/api/v1/predict/train")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "trained"
    assert body["algorithm"] == "HistGradientBoostingRegressor"
    assert body["mae"] is not None

    r = seeded_db.post(
        "/api/v1/predict/",
        json={
            "stop_id": "STOP_001",
            "line": "LINE_01",
            "direction": "North",
            "scheduled_time": "2026-10-20T08:30:00",
        },
    )
    assert r.status_code == 200
    assert r.json()["model_name"] == "delay_predictor_v1"


def test_train_with_empty_database(client):
    import asyncio

    from sqlalchemy import text

    from transitpulse.app.database import async_session, init_db
    from transitpulse.app.services.prediction import prediction_service

    prediction_service._model = None

    async def clear_delays():
        await init_db()
        async with async_session() as s:
            await s.execute(text("DELETE FROM delays"))
            await s.commit()

    asyncio.run(clear_delays())
    r = client.post("/api/v1/predict/train")
    assert r.status_code == 400
    assert "No delay records" in r.json()["detail"]


def test_predict_invalid_payload(seeded_db):
    r = seeded_db.post("/api/v1/predict/", json={"stop_id": ""})
    assert r.status_code == 422


def test_model_info_endpoint(seeded_db):
    r = seeded_db.get("/api/v1/predict/model/info")
    assert r.status_code == 200
    assert "metrics" in r.json()
