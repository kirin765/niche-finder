# Micro Niche Finder

Production-oriented Python service that discovers Korean micro niche SaaS opportunities using Naver DataLab signals and OpenAI structured outputs.

## Stack

- Python 3.12
- FastAPI
- PostgreSQL
- SQLAlchemy
- Alembic
- OpenAI Responses API

## Quick start

1. Create a Python 3.12 virtual environment.
2. Install dependencies:

```bash
pip install -e ".[dev]"
```

3. Copy [.env.example](/Users/kiwankim/niche-finder/.env.example) to `.env` and fill in credentials.
4. Run migrations:

```bash
alembic upgrade head
```

5. Start the API:

```bash
uvicorn apps.api.main:app --reload
```

## Sample API requests

Create a seed category:

```bash
curl -X POST http://localhost:8000/api/v1/seeds \
  -H "Content-Type: application/json" \
  -d '{
    "name": "스마트스토어 운영",
    "description": "한국 소형 셀러의 반복 업무 탐색"
  }'
```

Run the full pipeline:

```bash
curl -X POST http://localhost:8000/api/v1/pipeline/run \
  -H "Content-Type: application/json" \
  -d '{
    "seed_category_id": 1,
    "candidate_count": 20,
    "top_k": 10
  }'
```

List reports:

```bash
curl http://localhost:8000/api/v1/reports?limit=10
```

## Structure

- `apps/api`: FastAPI entrypoint and routes
- `apps/worker`: periodic collector worker entrypoints
- `src/micro_niche_finder/config`: settings and database bootstrap
- `src/micro_niche_finder/domain`: typed domain models and schemas
- `src/micro_niche_finder/repos`: persistence repositories
- `src/micro_niche_finder/services`: LLM, DataLab, scoring, clustering, reporting
- `src/micro_niche_finder/jobs`: modular pipeline jobs
- `alembic`: migrations

## Periodic collection

Bootstrapping schedules for existing query groups:

```bash
python scripts/bootstrap_collection_schedules.py
```

Running one budgeted collector cycle:

```bash
python -m apps.worker.run_collector --max-calls 5
```

Ubuntu deployment artifacts live under [deploy/ubuntu.md](/Users/kiwankim/niche-finder/deploy/ubuntu.md) and [deploy/systemd](/Users/kiwankim/niche-finder/deploy/systemd).

## Notes

- OpenAI integration uses the Responses API and JSON schema structured outputs.
- Naver DataLab data is treated as relative trend signal, not absolute demand.
- The repository includes tests for the rule-based scoring engine.
