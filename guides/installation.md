# Installation

ApplyKit supports a stable Docker setup and a manual development setup. For normal self-hosted use, prefer a published Git tag rather than `main`.

## Docker installation from the latest stable tag

### Linux, macOS, Git Bash, or WSL

```bash
git clone https://github.com/wihlarkop/applykit.git
cd applykit
git fetch --tags
git checkout "$(git describe --tags --abbrev=0)"
docker compose up --build
```

### Windows PowerShell

```powershell
git clone https://github.com/wihlarkop/applykit.git
cd applykit
git fetch --tags
$tag = git describe --tags --abbrev=0
git checkout $tag
docker compose up --build
```

Open:

- frontend: `http://localhost:3000`
- backend: `http://localhost:8000`

The backend container runs `alembic upgrade head` before serving requests.

## Persistent Docker storage

Docker Compose uses separate volumes:

- `applykit_applykit-data` for SQLite and application data;
- `applykit_applykit-secrets` for the local credential encryption key.

Both are required to restore encrypted provider credentials. Keep their backups separate and access-controlled.

## Manual development setup

Requirements:

- Python 3.12 managed through `uv`;
- Bun;
- system libraries required by WeasyPrint on your operating system.

```bash
git clone https://github.com/wihlarkop/applykit.git
cd applykit
git switch main
cp backend/.env.example backend/.env
make install
make migrate
```

Run each service in a separate terminal:

```bash
make backend
make frontend
```

The development frontend is available at `http://localhost:5173`; the backend is at `http://localhost:8000`.

## First launch

A genuinely fresh installation opens guided setup once. You may configure a career profile and AI provider or choose **Skip for now**. Skipping does not lock non-AI features.

Profile Ready requires a name, email, at least one work-experience or education entry, and at least one skill. AI Ready requires a selected provider/model and a successful connection test for the active configuration.

## Local files

With the default manual configuration:

- database: `backend/applykit.db`;
- credential key: `backend/.applykit/credential.key`;
- environment file: `backend/.env`.

Never commit `.env`, the database, or the credential key.
