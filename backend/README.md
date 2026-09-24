# Backend — FastAPI

Python 3.11+ FastAPI service for the SEZ Ledger Automation Tool (Kenya
Operations). See the [project plan](../README.md) for the full phase
breakdown; this README covers day-to-day backend commands.

Prefer running everything through Docker (`../docker-up.sh` /
`docker-backend.sh`) per the project's Docker-first constraint. The local venv
steps below are for editors/IDE tooling and quick local test runs.

## Setup

```bash
cd backend
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

## Run

```bash
uvicorn app.main:app --reload
```

- API: http://localhost:8000
- Interactive docs (Swagger UI): http://localhost:8000/docs
- Health check: http://localhost:8000/health

## Tests

```bash
pytest
```

## Database migrations

```bash
alembic revision --autogenerate -m "describe the change"
alembic upgrade head
```

## Creating a user

```bash
python -m app.cli.create_user <username> <password> [--admin]
```

## Project structure

```
backend/
├── app/
│   ├── main.py        # FastAPI app, CORS, router registration
│   ├── db.py           # SQLAlchemy engine/session, Base
│   ├── auth.py          # password hashing + JWT session tokens
│   ├── deps.py           # get_db / get_current_user / require_admin
│   ├── resources.py       # helper for reading files from /resources
│   ├── models/             # SQLAlchemy models (users, ledger lines, audit log, config)
│   ├── schemas/             # Pydantic request/response schemas
│   ├── routers/             # API endpoints (auth, admin, ...)
│   ├── services/            # business logic (Phase 3+)
│   ├── extraction/          # PDF extraction layer (Phase 4)
│   ├── excel/               # Excel generation (Phase 3.3, 7.3)
│   └── cli/                 # one-off/admin CLI commands
├── alembic/                 # database migrations
├── tests/                   # pytest suite
└── requirements.txt
```

## Adding your own endpoints

1. Create a new file under `app/routers/`, define an `APIRouter`.
2. Register it in `app/main.py` with `app.include_router(...)`.
3. Any data file you need (CSV, JSON, PDF, etc.) goes in the **top-level `/resources`**
   folder — never inside `backend/`. Load it with `resource_path()` from `app/resources.py`.
