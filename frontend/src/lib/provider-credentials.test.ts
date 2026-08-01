import { describe, expect, test } from 'bun:test';

import {
  canUseAutomaticStrategy,
  credentialHealthLabel,
  credentialStrategyDescription,
  credentialStrategyLabel,
  enabledCredentialCount,
} from '$lib/provider-credentials';
import type { ProviderCredentialInfo } from '$lib/types';

const credentials: ProviderCredentialInfo[] = [
  {
    id: 1,
    provider_id: 'openai',
    label: 'Personal',
    masked_secret: 'sk-p••••••onal',
    is_active: true,
    is_enabled: true,
    priority: 1,
    health_status: 'healthy',
    cooldown_until: null,
    last_tested_at: null,
    last_used_at: null,
    created_at: '2026-08-02T00:00:00Z',
    updated_at: '2026-08-02T00:00:00Z',
  },
  {
    id: 2,
    provider_id: 'openai',
    label: 'Backup',
    masked_secret: 'sk-b••••••ckup',
    is_active: false,
    is_enabled: true,
    priority: 2,
    health_status: 'rate_limited',
    cooldown_until: '2026-08-02T00:05:00Z',
    last_tested_at: null,
    last_used_at: null,
    created_at: '2026-08-02T00:00:00Z',
    updated_at: '2026-08-02T00:00:00Z',
  },
];

describe('credential strategy presentation', () => {
  test('uses clear labels and descriptions', () => {
    expect(credentialStrategyLabel('manual')).toBe('Manual');
    expect(credentialStrategyLabel('failover')).toBe('Automatic failover');
    expect(credentialStrategyLabel('round_robin')).toBe('Round robin');
    expect(credentialStrategyDescription('failover')).toContain('unavailable');
  });

  test('automatic strategies require at least two enabled credentials', () => {
    expect(enabledCredentialCount(credentials)).toBe(2);
    expect(canUseAutomaticStrategy(credentials)).toBe(true);
    expect(
      canUseAutomaticStrategy([
        credentials[0],
        { ...credentials[1], is_enabled: false },
      ]),
    ).toBe(false);
  });
});

describe('credential health labels', () => {
  test('explains common health states without exposing secrets', () => {
    expect(credentialHealthLabel(credentials[0])).toBe('Healthy');
    expect(credentialHealthLabel(credentials[1])).toBe('Rate limited · cooling down');
    expect(
      credentialHealthLabel({
        ...credentials[0],
        health_status: 'invalid',
        is_enabled: false,
      }),
    ).toBe('Invalid · disabled');
  });
});
