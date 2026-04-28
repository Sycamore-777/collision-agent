# Deployment

## Local Python + Node

1. Install backend dependencies: `python -m pip install -e .[dev]`
2. Install frontend dependencies: `cd frontend && npm install`
3. Start backend: `uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 8000`
4. Start frontend: `cd frontend && npm run dev`

## Docker Compose

`docker-compose up --build`

Services:

- `postgres`
- `backend`
- `frontend`

## Environment Notes

- Default DB: SQLite
- Compose DB: PostgreSQL
- Default storage: local `data/`
- Real LLM: configure `BASE_URL`, `API_KEY`, `MODEL_NAME`

## Troubleshooting

- Missing table errors: ensure the app started once or run Alembic under `backend/alembic.ini`
- Empty external context: the client falls back to local mock assets when remote fetch fails
- Mock LLM output: check `LLM_ENABLED`, `BASE_URL`, `API_KEY`, and `MODEL_NAME`

