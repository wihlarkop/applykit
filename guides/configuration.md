# Configuration

Backend configuration is loaded from `backend/.env` for manual installations and from Docker Compose environment values for containers.

## Common local settings

```env
DEPLOYMENT_MODE=local
DATABASE_URL=sqlite:///./applykit.db
AUTH_MODE=disabled
COOKIE_SECURE=false
DEBUG=false
CORS_ORIGINS=["http://localhost:5173"]
CREDENTIAL_KEY_FILE=.applykit/credential.key
MAX_PROVIDER_CREDENTIALS=20
```

Local mode is intentionally loopback-only. It rejects public domains, LAN origins, wildcard origins, and malformed browser origins.

## Deployment modes

### Local

```env
DEPLOYMENT_MODE=local
AUTH_MODE=disabled
COOKIE_SECURE=false
```

Use this for a single machine accessed through localhost.

### Remote

Remote mode is fail-closed and requires all of the following:

```env
DEPLOYMENT_MODE=remote
AUTH_MODE=password
COOKIE_SECURE=true
DEBUG=false
CORS_ORIGINS=["https://applykit.example.com"]
CREDENTIAL_ENCRYPTION_KEY_FILE=/run/secrets/applykit_credential_key
```

You may configure `CREDENTIAL_ENCRYPTION_KEY` instead of a key file, but configure exactly one external key source. Prefer a platform-managed secret file.

Serve the frontend and API from the same hostname. Build the frontend with a browser-reachable API URL, for example:

```bash
VITE_API_BASE_URL=https://applykit.example.com/api docker compose up --build
```

Remote startup is rejected when authentication or secure cookies are disabled, debug mode is enabled, HTTPS/CORS rules are invalid, or no external credential key is configured.

## Database

SQLite is the default:

```env
DATABASE_URL=sqlite:///./applykit.db
```

Manual commands resolve this relative to the `backend` directory. Use the provided `make` targets from the repository root to keep working directories consistent.

## API documentation

- `DEBUG=false`: `/docs`, `/redoc`, and `/openapi.json` are disabled.
- Local, unauthenticated development with `DEBUG=true`: API documentation is available on loopback.
- Remote mode rejects `DEBUG=true`.
