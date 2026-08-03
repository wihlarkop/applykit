<script lang="ts">
  import { goto } from '$app/navigation';
  import { getReadiness } from '$lib/readiness-api';
  import type { AiReadiness, ReadinessResponse } from '$lib/readiness-types';
  import { testConfiguredIntegration } from '$lib/integration-api';
  import { Button } from '$lib/components/ui/button';
  import { AlertTriangle, CircleCheck, RefreshCw, Settings, Sparkles } from '@lucide/svelte';

  let {
    ai,
    profileId,
    onrefreshed,
    compact = false,
  }: {
    ai: AiReadiness;
    profileId: number;
    onrefreshed?: (readiness: ReadinessResponse) => void;
    compact?: boolean;
  } = $props();

  let testing = $state(false);
  let publicError = $state('');

  const needsConfiguration = $derived(ai.status === 'not_configured' || !ai.provider);
  const ready = $derived(ai.ready);

  async function testConnection() {
    if (!ai.provider || testing) return;
    testing = true;
    publicError = '';
    try {
      await testConfiguredIntegration(ai.provider);
      const next = await getReadiness(profileId);
      onrefreshed?.(next);
    } catch {
      publicError = 'The connection test could not be completed. Review AI settings and try again.';
    } finally {
      testing = false;
    }
  }

  function openSettings() {
    void goto('/settings');
  }
</script>

{#if ready}
  <div class="flex items-start gap-3 rounded-xl border border-green-200 bg-green-50/80 p-4 text-green-950 dark:border-green-900 dark:bg-green-950/20 dark:text-green-100">
    <CircleCheck class="mt-0.5 h-5 w-5 shrink-0 text-green-600 dark:text-green-400" />
    <div class="min-w-0 flex-1">
      <p class="font-semibold">AI Ready</p>
      {#if !compact}
        <p class="mt-1 text-sm text-green-800/80 dark:text-green-200/70">{ai.message}</p>
      {/if}
    </div>
  </div>
{:else}
  <div class="rounded-xl border border-amber-200 bg-amber-50/80 p-4 dark:border-amber-900 dark:bg-amber-950/20">
    <div class="flex items-start gap-3">
      {#if needsConfiguration}
        <Sparkles class="mt-0.5 h-5 w-5 shrink-0 text-amber-600 dark:text-amber-400" />
      {:else}
        <AlertTriangle class="mt-0.5 h-5 w-5 shrink-0 text-amber-600 dark:text-amber-400" />
      {/if}
      <div class="min-w-0 flex-1">
        <p class="font-semibold text-amber-950 dark:text-amber-100">
          {needsConfiguration ? 'AI setup required' : 'AI connection needs attention'}
        </p>
        <p class="mt-1 text-sm text-amber-900/75 dark:text-amber-200/70">{ai.message}</p>
        {#if publicError}
          <p class="mt-2 text-sm font-medium text-destructive">{publicError}</p>
        {/if}
        <div class="mt-3 flex flex-wrap gap-2">
          {#if !needsConfiguration}
            <Button size="sm" onclick={testConnection} disabled={testing}>
              <RefreshCw class="h-4 w-4 {testing ? 'animate-spin' : ''}" />
              {testing ? 'Testing…' : ai.tested_at ? 'Test again' : 'Test connection'}
            </Button>
          {/if}
          <Button size="sm" variant={needsConfiguration ? 'default' : 'outline'} onclick={openSettings}>
            <Settings class="h-4 w-4" />
            {needsConfiguration ? 'Configure AI' : 'Fix AI settings'}
          </Button>
        </div>
      </div>
    </div>
  </div>
{/if}
