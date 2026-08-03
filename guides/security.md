# Security

ApplyKit is local-first and self-hosted, but secure operation still depends on correct deployment, backups, provider-key permissions, and host security.

## Credential encryption

Provider secrets are encrypted with Fernet before database persistence. The database stores ciphertext, a masked display value, a keyed duplicate-detection fingerprint, and operational metadata.

Local manual installations create the key at:

```text
backend/.applykit/credential.key
```

Docker stores it separately from application data at:

```text
/run/applykit-secrets/credential.key
```

During an upgrade, ApplyKit can migrate a legacy Docker key from `/data/credential.key`. It copies the key atomically, validates encrypted credentials, and removes the old copy only after successful validation.

ApplyKit refuses to create a replacement key when encrypted credentials already exist. A missing, corrupted, or incorrect key stops startup rather than making stored credentials unreadable.

## Deployment boundary

- Local mode accepts loopback browser origins only.
- Remote mode requires password authentication, HTTPS origins, secure cookies, disabled debug mode, and an external encryption key.
- Scraping rejects private-network and unsafe URLs before network access.
- Public errors, usage records, audit events, and connection results exclude raw provider exceptions and plaintext secrets.
- Untrusted CV and job-description content is isolated in LLM prompts and structured responses are validated.

## Provider-key precautions

Use a dedicated provider key with:

- minimum required permissions;
- spending and rate limits;
- separate personal and work credentials;
- immediate revocation after suspected exposure.

## Limitations

Credential encryption does not protect against an administrator or attacker who obtains both the database and key, privileged memory inspection, malware observing a key during entry, compromised provider accounts, or secrets already present in old external logs/backups.

ApplyKit does not currently provide encryption-key rotation or a rotation UI. Do not change or delete the key without a supported migration procedure.

## Reporting

When reporting a security problem, do not include API keys, passwords, session tokens, encryption keys, private CV content, or database files in public issues.
