# Authentication

ApplyKit provides optional single-owner authentication. It protects one installation and all career profiles with one owner password; it is not a multi-user account system.

## Modes

```env
AUTH_MODE=disabled
AUTH_MODE=password
```

`disabled` is allowed only for local mode. Remote deployments require `password`.

## First owner setup

Run migrations and start ApplyKit with `AUTH_MODE=password`. Read the backend log for the one-time setup token:

```bash
# Docker
docker compose logs backend

# Manual
cd backend
uv run alembic upgrade head
uv run main.py
```

Open `/setup`, enter the token, and create the owner password. The token expires after 30 minutes, is stored only as a hash, and becomes invalid after owner setup.

Passwords support 12–128 character passphrases and are stored as Argon2id hashes.

## Sessions and request protection

- Normal sessions expire after 7 days.
- **Remember this device** sessions expire after 30 days.
- Expiry is absolute and does not extend with activity.
- Session and CSRF token hashes are stored in SQLite; raw session tokens remain in `HttpOnly`, `SameSite=Lax` cookies.
- Mutating requests require a session-bound CSRF token and an allowed `Origin`.
- Five failed login attempts within 10 minutes trigger a 15-minute lockout.
- Password reset revokes all sessions.

The browser warns during the final five minutes. Supported forms can recover temporary per-tab drafts after reauthentication; uploaded files are never persisted for draft recovery.

## Forgotten password

There is no email recovery. Run the reset command on the machine hosting ApplyKit:

```bash
# Docker
docker compose exec backend uv run python -m app.cli auth reset-password

# Manual
cd backend
uv run python -m app.cli auth reset-password
```

The command asks for the new password twice, clears login lockout, and revokes every active session.

## Remote deployment requirement

Use HTTPS and serve the frontend and API from the same hostname. Do not expose password mode over public plain HTTP or split the UI and API across hostnames that cannot share the required cookie boundary.
