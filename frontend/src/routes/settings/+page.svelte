<script lang="ts">
  import { invalidateAll } from '$app/navigation';
  import { page } from '$app/state';
  import { activateProvider, disconnectProvider, getIntegrations } from '$lib/api';
  import SettingsModal from '$lib/components/SettingsModal.svelte';
  import { toastState } from '$lib/toast.svelte';
  import type { IntegrationInfo } from '$lib/types';
  import { ChevronRight, CircleAlert, CircleCheck, Pencil, Plus, Settings, Zap } from '@lucide/svelte';

  let modalOpen = $state(false);
  let modalProviderId = $state('');
  let modalModel = $state('');
  let modalApiKey = $state('');
  let integrations: IntegrationInfo[] = $state([]);
  let loading = $state(true);
  let activating = $state('');
  let confirmingActivate = $state('');
  let disconnecting = $state('');
  let confirmingDisconnect = $state('');

  const PROVIDER_COLORS: Record<string, string> = {
    gemini: '#8b5cf6',
    anthropic: '#f59e0b',
    openai: '#10b981',
    ollama: '#3b82f6',
  };

  const PROVIDER_ICONS: Record<string, string> = {
    gemini: '✦',
    anthropic: '◆',
    openai: '⬡',
    ollama: '⬢',
  };

  $effect(() => { loadIntegrations(); });

  async function loadIntegrations() {
    loading = true;
    try {
      const res = await getIntegrations();
      integrations = res.integrations;
    } finally {
      loading = false;
    }
  }

  function openEdit(integration: IntegrationInfo) {
    modalProviderId = integration.id;
    modalModel = integration.current_model ?? '';
    modalOpen = true;
    // Store apiKey for pre-filling in modal
    modalApiKey = integration.api_key ?? '';
  }

  async function handleActivate(providerId: string) {
    activating = providerId;
    try {
      await activateProvider(providerId);
      await invalidateAll();
      await loadIntegrations();
      toastState.success('Provider switched successfully.');
    } catch {
      toastState.error('Failed to switch provider.');
    } finally {
      activating = '';
      confirmingActivate = '';
    }
  }

  async function handleDisconnect(providerId: string) {
    disconnecting = providerId;
    try {
      const res = await disconnectProvider(providerId);
      integrations = res.integrations;
      await invalidateAll();
      toastState.success('Provider disconnected.');
    } catch {
      toastState.error('Failed to disconnect provider.');
    } finally {
      disconnecting = '';
      confirmingDisconnect = '';
    }
  }

  const anyConfigured = $derived(integrations.some((i) => i.api_key_configured));
</script>

<div class="max-w-2xl space-y-6">
  <div>
    <h1 class="text-2xl font-bold flex items-center gap-2">
      <Settings class="w-6 h-6 text-primary" />
      Settings
    </h1>
    <p class="text-sm text-muted-foreground mt-1">Manage your AI integrations. You can connect multiple providers and switch between them.</p>
  </div>

  <!-- Active model status -->
  {#if !loading}
    {@const active = integrations.find((i) => i.is_active)}
    {#if active}
      <div class="flex items-center gap-3 rounded-lg border border-border bg-muted/30 px-4 py-3">
        <div class="w-2 h-2 rounded-full bg-green-500 shrink-0 animate-pulse"></div>
        <div class="flex-1 min-w-0">
          <span class="text-xs text-muted-foreground">Active model</span>
          <p class="text-sm font-medium font-mono truncate">{active.current_model ?? active.label}</p>
        </div>
        <span class="text-xs text-muted-foreground">{active.label}</span>
      </div>
    {:else}
      <div class="flex items-center gap-3 rounded-lg border border-yellow-200 bg-yellow-50 dark:border-yellow-900 dark:bg-yellow-950/30 px-4 py-3">
        <CircleAlert class="w-4 h-4 text-yellow-500 shrink-0" />
        <p class="text-sm text-yellow-700 dark:text-yellow-400">No active model — configure a provider to enable AI features.</p>
      </div>
    {/if}
  {/if}

  <div class="space-y-3">
    <h2 class="text-sm font-medium text-muted-foreground uppercase tracking-wide">AI Integrations</h2>

    {#if loading}
      {#each [1, 2, 3, 4] as _}
        <div class="border border-border rounded-lg p-4 bg-card animate-pulse h-20"></div>
      {/each}
    {:else}
      {#each integrations as integration}
        {@const color = PROVIDER_COLORS[integration.id] ?? '#6b7280'}
        {@const icon = PROVIDER_ICONS[integration.id] ?? '◉'}
        <div class="border rounded-lg p-4 bg-card flex items-center gap-4 transition-colors {integration.is_active ? 'border-l-4 border-l-primary border-primary/20 bg-primary/5' : 'border-border'}">
          <!-- Icon -->
          <div class="w-10 h-10 rounded-lg flex items-center justify-center shrink-0 text-base font-bold" style="background:{color}18; color:{color}">
            {icon}
          </div>

          <!-- Info -->
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-2 flex-wrap">
              <span class="text-sm font-medium">{integration.label}</span>
              {#if integration.is_active}
                <span class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wide" style="background:{color}20; color:{color}">
                  <Zap class="w-2.5 h-2.5" />
                  Active
                </span>
              {/if}
            </div>
            {#if integration.api_key_configured}
              <div class="flex items-center gap-1.5 mt-0.5">
                <CircleCheck class="w-3 h-3 text-green-500 shrink-0" />
                <span class="text-xs text-muted-foreground">
                  Connected
                  {#if integration.masked_api_key}
                    · <code class="text-xs bg-muted px-1 rounded">{integration.masked_api_key}</code>
                  {/if}
                </span>
              </div>
            {:else if integration.id === 'ollama'}
              <div class="flex items-center gap-1.5 mt-0.5">
                <span class="text-xs text-muted-foreground">Local · no API key needed</span>
              </div>
            {:else}
              <div class="flex items-center gap-1.5 mt-0.5">
                <CircleAlert class="w-3 h-3 text-muted-foreground/60 shrink-0" />
                <span class="text-xs text-muted-foreground">Not configured</span>
              </div>
            {/if}
            {#if integration.current_model}
              <p class="text-xs font-mono font-semibold text-foreground mt-0.5">
                {integration.current_model.split('/').pop()}
              </p>
            {/if}
          </div>

          <!-- Actions -->
          <div class="flex items-center gap-2 shrink-0">
            {#if (integration.api_key_configured || integration.id === 'ollama') && !integration.is_active}
              {#if confirmingActivate === integration.id}
                <div class="flex items-center gap-1.5">
                  <span class="text-xs text-muted-foreground">Switch to {integration.label}?</span>
                  <button
                    onclick={async () => { await handleActivate(integration.id); }}
                    disabled={activating === integration.id}
                    class="px-2.5 py-1 rounded-md text-xs font-semibold bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50 transition-colors"
                  >Yes</button>
                  <button
                    onclick={() => confirmingActivate = ''}
                    class="px-2.5 py-1 rounded-md text-xs border border-border hover:bg-accent transition-colors"
                  >No</button>
                </div>
              {:else}
                <button
                  onclick={() => confirmingActivate = integration.id}
                  disabled={activating === integration.id}
                  class="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium border transition-colors disabled:opacity-50"
                  style="border-color:{color}50; color:{color}; background:{color}0a"
                >
                  <Zap class="w-3 h-3" />
                  Set Active
                </button>
              {/if}
            {/if}
            {#if integration.api_key_configured && !integration.is_active && integration.id !== 'ollama'}
              {#if confirmingDisconnect === integration.id}
                <div class="flex items-center gap-1.5">
                  <span class="text-xs text-muted-foreground">Remove key?</span>
                  <button
                    onclick={() => handleDisconnect(integration.id)}
                    disabled={disconnecting === integration.id}
                    class="px-2.5 py-1 rounded-md text-xs font-semibold bg-destructive text-destructive-foreground hover:bg-destructive/90 disabled:opacity-50 transition-colors"
                  >Yes</button>
                  <button
                    onclick={() => confirmingDisconnect = ''}
                    class="px-2.5 py-1 rounded-md text-xs border border-border hover:bg-accent transition-colors"
                  >No</button>
                </div>
              {:else}
                <button
                  onclick={() => confirmingDisconnect = integration.id}
                  disabled={disconnecting === integration.id}
                  class="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium border border-border text-muted-foreground hover:bg-destructive/10 hover:text-destructive hover:border-destructive/30 transition-colors"
                >
                  Remove
                </button>
              {/if}
            {/if}
            <button
              onclick={() => openEdit(integration)}
              class="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm border border-border hover:bg-accent transition-colors text-muted-foreground"
            >
              {#if integration.api_key_configured || integration.id === 'ollama'}
                <Pencil class="w-3.5 h-3.5" />
                Edit
              {:else}
                <Plus class="w-3.5 h-3.5" />
                Connect
              {/if}
            </button>
          </div>
        </div>
      {/each}

      {#if !anyConfigured}
        <p class="text-xs text-muted-foreground text-center py-2">
          Connect at least one provider to enable AI features.
        </p>
      {/if}
    {/if}
  </div>
</div>

<SettingsModal bind:open={modalOpen} initialProviderId={modalProviderId} initialModel={modalModel} initialApiKey={modalApiKey} />
