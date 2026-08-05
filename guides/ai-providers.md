# AI providers

Open **AI Settings** to connect providers, select models, manage credentials, configure routing, and test the active configuration.

## Models

ApplyKit includes a release-managed provider/model catalog and supports validated custom model IDs where the provider allows them. A selected model is shown as Catalog, Custom, or Unavailable when it is no longer present in the current catalog.

## Credentials

Remote providers can store multiple labeled credentials. Secrets are encrypted before database persistence and returned to the frontend only as masked metadata.

Available operations include:

- add, rename, replace, test, activate, and remove credentials;
- enable or disable credentials;
- inspect health, cooldown, priority, and last-used metadata;
- disconnect a provider and remove its provider-specific configuration.

Ollama is keyless and does not require a placeholder API key.

## Routing strategies

- **Manual:** use only the active credential.
- **Automatic failover:** try the active credential, then eligible credentials by priority.
- **Round robin:** begin at the persisted cursor and advance after a successful request.

Automatic strategies require at least two enabled credentials and use bounded attempts. Authentication failures disable the affected credential; rate limits and safe transient failures use cooldowns. Streaming requests are never retried after output has begun.

## Ollama

The default Base URL is:

```text
http://localhost:11434
```

You may configure local, LAN, domain, or reverse-proxy HTTP/HTTPS endpoints. ApplyKit normalizes trailing slashes, rejects malformed URLs, and does not append `/v1` automatically.

## AI readiness

AI Ready requires:

- an active provider and model;
- an active credential when the provider requires one;
- a successful connection test for that exact configuration.

The trusted fingerprint includes provider, model, normalized Base URL, and active credential ID/version. Changing any of them invalidates the prior result. Existing installations need one successful retest after upgrading to v1.2.0.

Connection failures are exposed through sanitized public categories such as authentication failure, endpoint unreachable, unavailable model, rate limit, or configuration changed. Raw provider exceptions and secrets are not returned.
