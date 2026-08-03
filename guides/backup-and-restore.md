# Backup and restore

The database and credential encryption key are separate sensitive assets. Both are required to restore encrypted provider credentials, but they should not be stored together in one unrestricted location.

## Docker backup

Create local backup directories:

```bash
mkdir -p backups/data backups/secrets
```

Back up application data:

```bash
docker run --rm \
  -v applykit_applykit-data:/source:ro \
  -v "$(pwd)/backups/data":/backup \
  alpine tar czf /backup/applykit-data.tar.gz -C /source .
```

Back up the credential key separately:

```bash
docker run --rm \
  -v applykit_applykit-secrets:/source:ro \
  -v "$(pwd)/backups/secrets":/backup \
  alpine tar czf /backup/applykit-secrets.tar.gz -C /source .
```

Store the archives separately and restrict access to both.

## Manual backup

Stop the backend before copying SQLite files. Back up:

```text
backend/applykit.db
backend/.applykit/credential.key
```

Keep the database and key in separate protected locations. Also preserve the deployed Git tag and a copy of non-secret configuration values.

## Restore order

1. Stop ApplyKit.
2. Restore application data to its original path or volume.
3. Restore the matching credential key to its original path or volume.
4. Apply restrictive file permissions where supported.
5. Check out the same Git tag used when the backup was created.
6. Start ApplyKit and verify it can decrypt credentials.
7. Upgrade only after the restored installation works.

Do not allow the application to generate a new local key before restoring the original one.

## Lost key

Losing the credential encryption key makes existing encrypted provider credentials unrecoverable. Profile, CV, history, and tracker data may still be recoverable from the database, but affected provider credentials must be revoked and replaced.

Anyone who obtains both the database and key may be able to decrypt provider credentials. Treat both backups as sensitive even when stored separately.
