# KSITI Docker Deployment

The application is now fully configured to run via Docker Compose, leveraging the full stack architecture:
- **FastAPI** (API Gateway)
- **Celery Worker** (Asynchronous background task processing)
- **PostgreSQL + PostGIS** (Relational & Spatial Database)
- **Redis** (Message Broker & Results Backend)

## How to run:
From the root of the `ksiti_master` directory, simply run:
```bash
docker-compose up -d --build
```

## What it does:
1. Boots **PostgreSQL** (with PostGIS installed).
2. Boots **Redis**.
3. Boots the **FastAPI** server on port `8000`. On boot, it automatically applies `Base.metadata.create_all` and creates the `postgis` extension.
4. Boots the **Celery Worker** to listen for `process_deed` tasks.

## Local (No-Docker) Compatibility
The code will continue to work if you run it locally without Docker:
- If `POSTGRES_HOST` is not provided, it falls back to SQLite (`ksiti_local.db`).
- If `REDIS_URL` is not provided, Celery automatically falls back to synchronous execution (`task_always_eager=True`).
