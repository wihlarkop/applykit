import type { IntegrationInfo, TestConnectionResponse } from '$lib/types';

export type IntegrationTestStatus = 'testing' | 'success' | 'failure';

export interface IntegrationTestState {
  status: IntegrationTestStatus;
  message: string;
}

export interface IntegrationTestSummary {
  total: number;
  passed: number;
  failed: number;
}

export type IntegrationTester = (providerId: string) => Promise<TestConnectionResponse>;
export type IntegrationTestUpdater = (
  providerId: string,
  state: IntegrationTestState,
) => void;

export function connectedIntegrations(
  integrations: IntegrationInfo[],
): IntegrationInfo[] {
  return integrations.filter(
    (integration) =>
      integration.api_key_configured ||
      (integration.id === 'ollama' && Boolean(integration.current_model)),
  );
}

export async function testConnectedIntegrations(
  integrations: IntegrationInfo[],
  testProvider: IntegrationTester,
  onUpdate: IntegrationTestUpdater,
  concurrency = 3,
): Promise<IntegrationTestSummary> {
  const candidates = connectedIntegrations(integrations);
  let nextIndex = 0;
  let passed = 0;
  let failed = 0;

  async function worker(): Promise<void> {
    while (nextIndex < candidates.length) {
      const currentIndex = nextIndex;
      nextIndex += 1;
      const integration = candidates[currentIndex];

      onUpdate(integration.id, {
        status: 'testing',
        message: 'Testing connection…',
      });

      let response: TestConnectionResponse;
      try {
        response = await testProvider(integration.id);
      } catch {
        response = {
          ok: false,
          message: 'Connection test request failed.',
        };
      }

      if (response.ok) {
        passed += 1;
        onUpdate(integration.id, {
          status: 'success',
          message: response.message,
        });
      } else {
        failed += 1;
        onUpdate(integration.id, {
          status: 'failure',
          message: response.message,
        });
      }
    }
  }

  const workerCount = Math.min(
    Math.max(1, concurrency),
    candidates.length,
  );
  await Promise.all(Array.from({ length: workerCount }, () => worker()));

  return {
    total: candidates.length,
    passed,
    failed,
  };
}
