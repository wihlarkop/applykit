import type {
  CredentialStrategy,
  ProviderCredentialInfo,
} from '$lib/provider-credential-types';

export function credentialStrategyLabel(strategy: CredentialStrategy): string {
  if (strategy === 'failover') return 'Automatic failover';
  if (strategy === 'round_robin') return 'Round robin';
  return 'Manual';
}

export function credentialStrategyDescription(strategy: CredentialStrategy): string {
  if (strategy === 'failover') {
    return 'Use the active credential first, then try another healthy credential when it is unavailable.';
  }
  if (strategy === 'round_robin') {
    return 'Distribute new requests across healthy credentials in sequence.';
  }
  return 'Always use the credential marked as active.';
}

export function enabledCredentialCount(
  credentials: ProviderCredentialInfo[],
): number {
  return credentials.filter((credential) => credential.is_enabled).length;
}

export function canUseAutomaticStrategy(
  credentials: ProviderCredentialInfo[],
): boolean {
  return enabledCredentialCount(credentials) >= 2;
}

export function credentialHealthLabel(
  credential: ProviderCredentialInfo,
): string {
  if (!credential.is_enabled || credential.health_status === 'invalid') {
    return 'Invalid · disabled';
  }
  if (credential.health_status === 'rate_limited') {
    return credential.cooldown_until
      ? 'Rate limited · cooling down'
      : 'Rate limited';
  }
  if (credential.health_status === 'degraded') return 'Temporarily unavailable';
  if (credential.health_status === 'healthy') return 'Healthy';
  if (credential.health_status === 'unhealthy') return 'Connection failed';
  return 'Not tested';
}

export function credentialHealthTone(
  credential: ProviderCredentialInfo,
): 'neutral' | 'success' | 'warning' | 'danger' {
  if (!credential.is_enabled || credential.health_status === 'invalid') return 'danger';
  if (credential.health_status === 'healthy') return 'success';
  if (
    credential.health_status === 'rate_limited' ||
    credential.health_status === 'degraded'
  ) {
    return 'warning';
  }
  if (credential.health_status === 'unhealthy') return 'danger';
  return 'neutral';
}
