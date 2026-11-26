# QAAI — Q&A Platform on AWS EC2

Conversational student course evaluation with protected reviewer analytics, designed for a single-node EC2 deployment. Students complete a guided evaluation; reviewers sign in to see aggregated dashboards and themes.

## Stack

- Backend: FastAPI, SQLAlchemy, Alembic, MySQL 8.4.
- Auth: JWT access tokens and bcrypt password hashes; analytics routes require a reviewer account.
- AI: Ollama `gemma3:270m` running on the Docker host, plus `faster-whisper` for audio transcription.
- Frontend: Next.js 15, React 19, Tailwind CSS.
- Deployment: Docker Compose with Nginx as reverse proxy on one EC2 host.

## Setup

1. Copy the example environment file and replace the placeholder secrets (database password, JWT secret, reviewer seed password):

   ```bash
   cp .env.example .env
   ```

2. Run Ollama on the host and pull the configured model:

   ```bash
   ollama pull gemma3:270m
   ```

   The backend reaches it through `host.docker.internal`, as configured in `.env`.

3. Build and start the stack:

   ```bash
   docker compose up -d --build
   ```

4. Seed structure and the reviewer account:

   ```bash
   docker compose exec backend python -m app.seed
   ```

   Sign in with the seed credentials from `.env`.

## Access

- UI: `http://localhost:3000`
- API: `http://localhost:8000/api` (health check at `/api/health`)
- Nginx proxies public traffic to the frontend and backend containers.

## Tests

Backend tests live in `backend/tests/` and use pytest:

```bash
cd backend
pytest
```

## Deployment notes

Deployment notes were cleaned; no infrastructure details are published. Configure DNS, TLS and host firewall rules for your own environment before exposing the service.
