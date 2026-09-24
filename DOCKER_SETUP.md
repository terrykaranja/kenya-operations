# Docker Development Setup

This project uses Docker for development, allowing you to run the entire application stack without installing Python or Node.js locally.

## Prerequisites

- Docker Desktop for Windows (or Docker Engine on Linux/Mac)
- Git

## Quick Start

1. **Clone and navigate to the project**:
   ```bash
   cd my-track-name
   ```

2. **Copy environment file**:
   ```bash
   copy .env.example .env
   ```

3. **Edit .env file** and add your Anthropic API key:
   ```
   ANTHROPIC_API_KEY=your_actual_api_key_here
   ```

4. **Build Docker containers**:
   ```bash
   docker-build.bat
   ```

5. **Start the development environment**:
   ```bash
   docker-up.bat
   ```

6. **Access the application**:
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs
   - Frontend: http://localhost:5173

## Docker Scripts

### docker-build.bat
Builds the Docker containers for development.

### docker-up.bat
Starts all containers in detached mode:
- Backend API on port 8000
- Frontend on port 5173
- PostgreSQL (optional, requires --profile postgres)

### docker-down.bat
Stops all running containers.

### docker-backend.bat [command]
Runs commands inside the backend container.

Examples:
```bash
# Create an admin user
docker-backend.bat python -m app.cli.create_user admin password123 --admin

# Import legacy Excel data
docker-backend.bat python -m app.import_legacy resources/Seza_Stock_Ledger_Hackathon.xlsx

# Run tests
docker-backend.bat pytest

# Run database migrations
docker-backend.bat alembic upgrade head

# Open a bash shell in the container
docker-backend.bat bash
```

### docker-frontend.bat [command]
Runs commands inside the frontend container.

Examples:
```bash
# Install new dependencies
docker-frontend.bat npm install package-name

# Build for production
docker-frontend.bat npm run build

# Run linter
docker-frontend.bat npm run lint

# Open a shell in the container
docker-frontend.bat sh
```

## Development Workflow

### Hot Reload
Both backend and frontend support hot reload:
- Backend: Changes to `backend/app/` are automatically reloaded
- Frontend: Changes to `frontend/src/` are automatically reloaded

### Viewing Logs
```bash
# View all logs
docker-compose logs -f

# View only backend logs
docker-compose logs -f backend

# View only frontend logs
docker-compose logs -f frontend
```

### Database
By default, the application uses SQLite (file-based database stored in `resources/sez_ledger.db`).

To use PostgreSQL instead:
1. Uncomment the PostgreSQL configuration in `.env`
2. Start with PostgreSQL profile:
   ```bash
   docker-compose --profile postgres up -d
   ```

### Resources Directory
All data files (Excel, PDFs, etc.) should be placed in the `resources/` directory at the project root. This directory is mounted into the Docker containers and is shared between backend and frontend.

## Troubleshooting

### Port Already in Use
If ports 8000 or 5173 are already in use, edit `docker-compose.yml` to change the port mappings.

### Container Won't Start
Check the logs:
```bash
docker-compose logs backend
docker-compose logs frontend
```

### Python Modules Not Found
Rebuild the containers:
```bash
docker-down.bat
docker-build.bat
docker-up.bat
```

### Database Issues
For SQLite, the database file is in `resources/sez_ledger.db`. You can delete this file to start fresh.

For PostgreSQL, you can reset the database:
```bash
docker-compose down -v
docker-compose --profile postgres up -d
```

## Production Deployment

For production deployment, see `docker-compose.prod.yml` (to be created). The production setup uses:
- Optimized multi-stage Dockerfile
- PostgreSQL instead of SQLite
- Non-root user for security
- Health checks and restart policies
