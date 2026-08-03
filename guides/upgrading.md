# Upgrading

Upgrade the database and credential key as a matched installation. A database backup alone cannot restore encrypted provider credentials.

## Before upgrading

1. Stop ApplyKit.
2. Back up application data.
3. Back up the credential encryption key separately.
4. Record the currently deployed Git tag.
5. Read the target release notes and migration guidance.

See [Backup and restore](backup-and-restore.md) for commands.

## Docker tag upgrade

```bash
git fetch --tags
git checkout v0.2.0
docker compose up --build
```

The backend entrypoint runs Alembic migrations automatically before startup. Watch the backend logs:

```bash
docker compose logs -f backend
```

Do not switch a stable installation to `main` merely to receive unreleased changes.

## Manual upgrade

From the repository root:

```bash
git switch main
git pull --ff-only
make install
make migrate
```

Then restart:

```bash
make backend
make frontend
```

Running `make backend` before `make migrate` may stop startup with a database-schema message. Do not replace the credential key in response; migrate the database first.

## After upgrading

- Sign in and verify profiles, history, and tracker data.
- Open AI Settings and test the configured provider.
- Existing configurations need one successful retest to establish the readiness fingerprint.
- Generate a small CV or cover-letter test before relying on the installation.
- Confirm Docker volumes or manual storage paths still point to the expected data and key.

## Rollback cautions

Application code can be checked out at an older tag, but database downgrades are not performed automatically. Do not point older code at a schema it does not understand.

The safest rollback is restoring both the pre-upgrade database backup and its matching credential-key backup, then checking out the previous tag. Keep the failed upgrade data untouched until recovery is confirmed.
