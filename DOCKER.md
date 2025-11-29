# Docker Deployment Guide

This guide explains how to run the Grimoire Engine backend using Docker.

## Prerequisites

- Docker installed on your system
- Docker Compose (or Docker with compose plugin)

## Quick Start

1. **Create environment file**
   ```bash
   cp .env.example .env
   ```
   Edit `.env` and set your configuration values (GitHub webhook secret, API token, etc.)

2. **Build and start the service**
   ```bash
   docker compose up --build
   ```

3. **Access the API**
   - API: http://localhost:8000
   - Interactive docs: http://localhost:8000/docs
   - Health check: http://localhost:8000/health

## Docker Commands

### Build the image
```bash
docker build -t grimoire-engine-backend .
```

### Run with docker-compose
```bash
# Start in foreground
docker compose up

# Start in background
docker compose up -d

# View logs
docker compose logs -f

# Stop services
docker compose down
```

### Run container directly
```bash
docker run -p 8000:8000 \
  -v $(pwd)/data:/app/data \
  --env-file .env \
  grimoire-engine-backend
```

## Data Persistence

The SQLite database is stored in the `./data` directory, which is mounted as a volume. This ensures your data persists across container restarts.

## Health Checks

The container includes a health check that pings the `/health` endpoint every 30 seconds. You can view the health status with:

```bash
docker compose ps
```

## Environment Variables

See `.env.example` for all available configuration options. Key variables:

- `DATABASE_URL`: SQLite database path (default: `sqlite+aiosqlite:///./data/grimoire.db`)
- `GITHUB_WEBHOOK_SECRET`: Secret for validating GitHub webhooks
- `GITHUB_API_TOKEN`: Token for GitHub API requests
- `LOG_LEVEL`: Logging level (default: `INFO`)

## Troubleshooting

### Container won't start
Check logs: `docker compose logs grimoire-api`

### Database issues
Ensure the `./data` directory has proper permissions:
```bash
mkdir -p data
chmod 755 data
```

### Port already in use
Change the port mapping in `docker-compose.yml`:
```yaml
ports:
  - "8080:8000"  # Use port 8080 instead
```
