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
git checkout v1.3.0
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

## v1.3.0 database changes

Version 1.3.0 adds immutable Role Evidence Match storage:

- `role_match_analysis`
- `role_match_requirement`
- `role_match_evidence`
- `role_match_override`
- a nullable link from generated cover letters to their audited analysis

Docker runs these migrations automatically. Manual installations must run `make migrate` before starting the new backend.

Existing cover letters and application history remain available. Older free-form results are labeled **Legacy AI fit score** and are **not recalculated** or silently converted into Role Evidence Match. A new analysis creates a new versioned snapshot; it does not overwrite the legacy record.

Before relying on the feature after upgrading:

1. Open Smart Apply or Cover Letter.
2. Run a new Role Evidence Match analysis.
3. Confirm the result shows match, confidence, and eligibility separately.
4. Open the detailed breakdown and verify the extracted requirements and evidence.
5. Review any result marked **Analysis needs review** rather than treating it as a score.

See [Role Evidence Match](role-evidence-match.md) for formulas, fairness guardrails, overrides, and limitations.

## After upgrading

- Sign in and verify profiles, history, and tracker data.
- Open AI Settings and test the configured provider.
- Existing configurations need one successful retest to establish the readiness fingerprint.
- Generate a small CV or cover-letter test before relying on the installation.
- Confirm Docker volumes or manual storage paths still point to the expected data and key.
- Confirm new cover-letter history shows either **Evidence match** or **Legacy score** so the two metrics are not confused.

## Rollback cautions

Application code can be checked out at an older tag, but database downgrades are not performed automatically. Do not point older code at a schema it does not understand.

The safest rollback is restoring both the pre-upgrade database backup and its matching credential-key backup, then checking out the previous tag. Keep the failed upgrade data untouched until recovery is confirmed.

Rolling back from v1.3.0 without restoring the pre-upgrade database leaves `role_match_analysis` and related tables in a schema older code does not understand. Restore the matched backup rather than deleting audit data manually.
