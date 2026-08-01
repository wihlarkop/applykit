<script lang="ts">
  import { invalidateAll } from '$app/navigation';
  import { activateProvider, disconnectProvider, getIntegrations, getModels } from '$lib/api';
  import SettingsModal from '$lib/components/SettingsModal.svelte';
  import { testConfiguredIntegration } from '$lib/integration-api';
  import {
    connectedIntegrations,
    testConnectedIntegrations,
    type IntegrationTestState,
    type IntegrationTestSummary,
  } from '$lib/integration-testing';
  import {
    credentialActionLabel,
    type CatalogProviderInfo,
  } from '$lib/llm-catalog';
  import {
    groupIntegrations,
    integrationModelKind,
    settingsOverview,
    type IntegrationModelKind,
  } from '$lib/settings-integrations';
  import { toastState } from '$lib/toast.svelte';
  import type { IntegrationInfo } from '$lib/types';
  import {
    Activity,
    BarChart3,
    CircleAlert,
    CircleCheck,
    ExternalLink,
    KeyRound,
    Loader2,
    MoreHorizontal,
    Pencil,
    Plus,
    Settings,
    Trash2,
    Zap,
  } from '@lucide/svelte';

  let modalOpen = $state(false);
  let modalProviderId = $state('');
  let modalModel = $state('');
  let modalApiKeyConfigured = $state(false);
  let integrations: IntegrationInfo[] = $state([]);
  let providers: CatalogProviderInfo[] = $state([]);
  let loading = $state(true);
  let activating = $state('');
  let confirmingActivate = $state('');
  let disconnecting = $state('');
  let confirmingDisconnect = $state('');
  let testStates = $state<Record<string, IntegrationTestState>>({});
  let testingAll = $state(false);
  let testSummary = $state<IntegrationTestSummary | null>(null);

  const PROVIDER_COLORS: Record<string, string> = {
    anthropic: '#d97706',
    deepseek: '#2563eb',
    gemini: '#7c3aed',
    groq: '#ea580c',
    huggingface: '#ca8a04',
    mistral: '#dc2626',
    ollama: '#2563eb',
    openai: '#059669',
    openrouter: '#4f46e5',
    xai: '#52525b',
  };

  const PROVIDER_MARKS: Record<string, string> = {
    anthropic: 'A',
    deepseek: 'D',
    gemini: 'G',
    groq: 'G',
    huggingface: 'HF',
    mistral: 'M',
    ollama: 'O',
    openai: 'O',
    openrouter: 'OR',
    xai: 'xAI',
  };

  $effect(() => {
    loadData();
  });

  async function loadData() {
    loading = true;
    try {
      const [integrationsResponse, modelsResponse] = await Promise.all([
        getIntegrations(),
        getModels(),
      ]);
      integrations = integrationsResponse.integrations;
      providers = modelsResponse.providers as CatalogProviderInfo[];
    } catch {
      toastState.error('Failed to load AI integrations.');
    } finally {
      loading = false;
    }
  }

  function providerFor(providerId: string): CatalogProviderInfo | undefined {
    return providers.find((provider) => provider.id === providerId);
  }

  function openEdit(integration: IntegrationInfo) {
    modalProviderId = integration.id;
    modalModel = integration.current_model ?? '';
    modalApiKeyConfigured = integration.api_key_configured;
    modalOpen = true;
  }

  async function handleActivate(providerId: string) {
    activating = providerId;
    try {
      await activateProvider(providerId);
      await invalidateAll();
      await loadData();
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
      const response = await disconnectProvider(providerId);
      integrations = response.integrations;
      const nextStates = { ...testStates };
      delete nextStates[providerId];
      testStates = nextStates;
      testSummary = null;
      await invalidateAll();
      toastState.success('Provider disconnected.');
    } catch {
      toastState.error('Failed to disconnect provider.');
    } finally {
      disconnecting = '';
      confirmingDisconnect = '';
    }
  }

  function updateTestState(providerId: string, state: IntegrationTestState) {
    testStates = { ...testStates, [providerId]: state };
  }

  async function handleTestIntegration(providerId: string) {
    updateTestState(providerId, {
      status: 'testing',
      message: 'Testing connection…',
    });
    testSummary = null;

    try {
      const result = await testConfiguredIntegration(providerId);
      updateTestState(providerId, {
        status: result.ok ? 'success' : 'failure',
        message: result.message,
      });
    } catch {
      updateTestState(providerId, {
        status: 'failure',
        message: 'Connection test request failed.',
      });
    }
  }

  async function handleTestAll() {
    testingAll = true;
    testSummary = null;
    try {
      testSummary = await testConnectedIntegrations(
        integrations,
        testConfiguredIntegration,
        updateTestState,
      );
    } finally {
      testingAll = false;
    }
  }

  function modelKindLabel(kind: IntegrationModelKind): string {
    if (kind === 'catalog') return 'Catalog';
    if (kind === 'custom') return 'Custom';
    return 'Unavailable';
  }

  function modelKindClass(kind: IntegrationModelKind): string {
    if (kind === 'catalog') {
      return 'bg-blue-100 text-blue-700 dark:bg-blue-950/60 dark:text-blue-300';
    }
    if (kind === 'custom') {
      return 'bg-purple-100 text-purple-700 dark:bg-purple-950/60 dark:text-purple-300';
    }
    return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-950/60 dark:text-yellow-300';
  }

  const grouped = $derived(groupIntegrations(integrations));
  const overview = $derived(settingsOverview(integrations));
  const testableIntegrations = $derived(connectedIntegrations(integrations));
</script>

<div class="mx-auto max-w-5xl space-y-8">
  <header class="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
    <div>
      <h1 class="flex items-center gap-2 text-2xl font-bold tracking-tight">
        <Settings class="h-6 w-6 text-primary" />
        AI Settings
      </h1>
      <p class="mt-1 max-w-2xl text-sm text-muted-foreground">
        Connect providers, choose the active model, and verify every integration from one place.
      </p>
    </div>
    <a
      href="/usage"
      class="inline-flex w-fit items-center gap-2 rounded-lg border border-border bg-card px-3 py-2 text-sm font-medium text-muted-foreground shadow-sm transition-colors hover:bg-accent hover:text-foreground"
    >
      <BarChart3 class="h-4 w-4" />
      View usage
    </a>
  </header>

  {#if loading}
    <section class="animate-pulse overflow-hidden rounded-2xl border border-border bg-card">
      <div class="h-40 bg-muted/50"></div>
      <div class="grid grid-cols-3 gap-px border-t border-border bg-border">
        {#each [1, 2, 3] as _}
          <div class="h-20 bg-card"></div>
        {/each}
      </div>
    </section>
    <div class="grid gap-4 lg:grid-cols-2">
      {#each [1, 2, 3, 4] as _}
        <div class="h-60 animate-pulse rounded-xl border border-border bg-card"></div>
      {/each}
    </div>
  {:else}
    <section class="overflow-hidden rounded-2xl border border-border bg-card shadow-sm">
      <div class="grid gap-6 p-5 sm:p-6 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-center">
        <div class="flex min-w-0 items-start gap-4">
          <div class="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary">
            {#if overview.active}
              <Zap class="h-5 w-5" />
            {:else}
              <CircleAlert class="h-5 w-5" />
            {/if}
          </div>
          <div class="min-w-0">
            <p class="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">
              Active configuration
            </p>
            {#if overview.active}
              <div class="mt-1 flex flex-wrap items-center gap-2">
                <h2 class="text-lg font-semibold">{overview.active.label}</h2>
                <span class="inline-flex items-center gap-1 rounded-full bg-green-100 px-2 py-0.5 text-[11px] font-semibold text-green-700 dark:bg-green-950/60 dark:text-green-300">
                  <span class="h-1.5 w-1.5 rounded-full bg-green-500"></span>
                  Active
                </span>
              </div>
              <code class="mt-1 block break-all text-sm text-muted-foreground">
                {overview.active.current_model ?? 'No model selected'}
              </code>
            {:else}
              <h2 class="mt-1 text-lg font-semibold">No active provider</h2>
              <p class="mt-1 text-sm text-muted-foreground">
                Connect a provider below, then set it as active to enable AI features.
              </p>
            {/if}
          </div>
        </div>

        <div class="lg:text-right">
          <button
            onclick={handleTestAll}
            disabled={testingAll || testableIntegrations.length === 0}
            class="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-sm font-semibold text-primary-foreground shadow-sm transition-colors hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-50 sm:w-auto"
          >
            {#if testingAll}
              <Loader2 class="h-4 w-4 animate-spin" />
              Testing all…
            {:else}
              <Activity class="h-4 w-4" />
              Test all connected
            {/if}
          </button>
          <p class="mt-2 max-w-sm text-xs text-muted-foreground lg:max-w-xs">
            Sends one minimal request to each connected provider and may incur a small charge.
          </p>
        </div>
      </div>

      <div class="grid gap-px border-t border-border bg-border sm:grid-cols-3">
        <div class="bg-card px-5 py-4">
          <p class="text-2xl font-semibold">{overview.connectedCount}</p>
          <p class="text-xs text-muted-foreground">Connected providers</p>
        </div>
        <div class="bg-card px-5 py-4">
          <p class="text-2xl font-semibold">{overview.credentialCount}</p>
          <p class="text-xs text-muted-foreground">Credentials saved</p>
        </div>
        <div class="bg-card px-5 py-4">
          {#if testSummary}
            <p class="text-2xl font-semibold">{testSummary.passed}/{testSummary.total}</p>
            <p class="text-xs text-muted-foreground">
              Passed latest test{testSummary.failed ? ` · ${testSummary.failed} failed` : ''}
            </p>
          {:else}
            <p class="text-2xl font-semibold">—</p>
            <p class="text-xs text-muted-foreground">Not tested this session</p>
          {/if}
        </div>
      </div>
    </section>

    <section class="space-y-4">
      <div class="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 class="text-base font-semibold">Connected</h2>
          <p class="text-sm text-muted-foreground">
            Providers ready to use with their saved model and credential.
          </p>
        </div>
        <span class="rounded-full bg-muted px-2.5 py-1 text-xs font-medium text-muted-foreground">
          {grouped.connected.length} configured
        </span>
      </div>

      {#if grouped.connected.length > 0}
        <div class="grid gap-4 lg:grid-cols-2">
          {#each grouped.connected as integration}
            {@const color = PROVIDER_COLORS[integration.id] ?? '#6b7280'}
            {@const mark = PROVIDER_MARKS[integration.id] ?? integration.label.slice(0, 2).toUpperCase()}
            {@const provider = providerFor(integration.id)}
            {@const testState = testStates[integration.id]}
            {@const modelKind = integrationModelKind(integration, providers)}
            <article class="rounded-xl border border-border bg-card p-5 shadow-sm transition-colors hover:border-primary/30">
              <div class="flex items-start gap-3">
                <div
                  class="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl text-xs font-bold"
                  style="background:{color}18; color:{color}"
                  aria-hidden="true"
                >
                  {mark}
                </div>
                <div class="min-w-0 flex-1">
                  <div class="flex flex-wrap items-center gap-2">
                    <h3 class="font-semibold">{integration.label}</h3>
                    {#if integration.is_active}
                      <span class="inline-flex items-center gap-1 rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-primary">
                        <Zap class="h-2.5 w-2.5" />
                        Active
                      </span>
                    {/if}
                  </div>
                  <p class="mt-0.5 text-xs text-muted-foreground">
                    {#if provider?.local}
                      Local provider · no credential required
                    {:else}
                      Credential configured
                    {/if}
                  </p>
                </div>

                {#if integration.api_key_configured && !integration.is_active && integration.id !== 'ollama'}
                  <details class="relative shrink-0">
                    <summary
                      class="flex h-8 w-8 cursor-pointer list-none items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-accent hover:text-foreground [&::-webkit-details-marker]:hidden"
                      aria-label={`More actions for ${integration.label}`}
                    >
                      <MoreHorizontal class="h-4 w-4" />
                    </summary>
                    <div class="absolute right-0 z-20 mt-2 w-60 rounded-lg border border-border bg-popover p-3 text-popover-foreground shadow-lg">
                      {#if confirmingDisconnect === integration.id}
                        <p class="text-sm font-medium">Remove saved credential?</p>
                        <p class="mt-1 text-xs text-muted-foreground">
                          This provider will move back to Available providers.
                        </p>
                        <div class="mt-3 flex gap-2">
                          <button
                            onclick={() => handleDisconnect(integration.id)}
                            disabled={disconnecting === integration.id}
                            class="inline-flex flex-1 items-center justify-center gap-1.5 rounded-md bg-destructive px-2.5 py-1.5 text-xs font-semibold text-destructive-foreground disabled:opacity-50"
                          >
                            {#if disconnecting === integration.id}
                              <Loader2 class="h-3 w-3 animate-spin" />
                            {:else}
                              <Trash2 class="h-3 w-3" />
                            {/if}
                            Remove
                          </button>
                          <button
                            onclick={() => (confirmingDisconnect = '')}
                            class="rounded-md border border-border px-2.5 py-1.5 text-xs hover:bg-accent"
                          >
                            Cancel
                          </button>
                        </div>
                      {:else}
                        <button
                          onclick={() => (confirmingDisconnect = integration.id)}
                          class="flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-sm text-destructive hover:bg-destructive/10"
                        >
                          <Trash2 class="h-4 w-4" />
                          Remove credential
                        </button>
                      {/if}
                    </div>
                  </details>
                {/if}
              </div>

              <div class="mt-4 rounded-lg border border-border/70 bg-muted/30 p-3">
                <div class="flex flex-wrap items-center justify-between gap-2">
                  <span class="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
                    Selected model
                  </span>
                  {#if modelKind}
                    <span class={`rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase ${modelKindClass(modelKind)}`}>
                      {modelKindLabel(modelKind)}
                    </span>
                  {/if}
                </div>
                <code class="mt-1.5 block break-all text-sm font-medium">
                  {integration.current_model ?? 'No model selected'}
                </code>
                {#if modelKind === 'unavailable'}
                  <p class="mt-2 text-xs text-yellow-700 dark:text-yellow-300">
                    This model is no longer in the current catalog. Edit the provider to replace it.
                  </p>
                {/if}
              </div>

              <div class="mt-3 flex items-center gap-2 text-xs text-muted-foreground">
                {#if provider?.local}
                  <CircleCheck class="h-3.5 w-3.5 text-blue-500" />
                  Ready on this device
                {:else}
                  <KeyRound class="h-3.5 w-3.5 text-green-500" />
                  {integration.masked_api_key ?? 'Credential stored securely'}
                {/if}
              </div>

              {#if testState}
                <div class="mt-3 flex items-start gap-2 rounded-lg px-3 py-2 text-xs {testState.status === 'success' ? 'bg-green-50 text-green-700 dark:bg-green-950/30 dark:text-green-300' : testState.status === 'failure' ? 'bg-red-50 text-red-700 dark:bg-red-950/30 dark:text-red-300' : 'bg-muted text-muted-foreground'}">
                  {#if testState.status === 'testing'}
                    <Loader2 class="mt-0.5 h-3.5 w-3.5 shrink-0 animate-spin" />
                  {:else if testState.status === 'success'}
                    <CircleCheck class="mt-0.5 h-3.5 w-3.5 shrink-0" />
                  {:else}
                    <CircleAlert class="mt-0.5 h-3.5 w-3.5 shrink-0" />
                  {/if}
                  <span>{testState.message}</span>
                </div>
              {/if}

              <div class="mt-4 flex flex-col gap-2 sm:flex-row sm:flex-wrap">
                {#if !integration.is_active}
                  {#if confirmingActivate === integration.id}
                    <div class="flex flex-1 items-center gap-2 rounded-lg border border-primary/20 bg-primary/5 p-2">
                      <span class="flex-1 text-xs">Set {integration.label} as active?</span>
                      <button
                        onclick={() => handleActivate(integration.id)}
                        disabled={activating === integration.id}
                        class="rounded-md bg-primary px-2.5 py-1.5 text-xs font-semibold text-primary-foreground disabled:opacity-50"
                      >
                        {activating === integration.id ? 'Switching…' : 'Confirm'}
                      </button>
                      <button
                        onclick={() => (confirmingActivate = '')}
                        class="rounded-md px-2 py-1.5 text-xs text-muted-foreground hover:bg-accent"
                      >
                        Cancel
                      </button>
                    </div>
                  {:else}
                    <button
                      onclick={() => (confirmingActivate = integration.id)}
                      class="inline-flex flex-1 items-center justify-center gap-1.5 rounded-lg bg-primary px-3 py-2 text-sm font-semibold text-primary-foreground transition-colors hover:bg-primary/90"
                    >
                      <Zap class="h-3.5 w-3.5" />
                      Set active
                    </button>
                  {/if}
                {/if}
                <button
                  onclick={() => handleTestIntegration(integration.id)}
                  disabled={testingAll || testState?.status === 'testing'}
                  class="inline-flex flex-1 items-center justify-center gap-1.5 rounded-lg border border-border px-3 py-2 text-sm font-medium transition-colors hover:bg-accent disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {#if testState?.status === 'testing'}
                    <Loader2 class="h-3.5 w-3.5 animate-spin" />
                    Testing…
                  {:else}
                    <Activity class="h-3.5 w-3.5" />
                    Test
                  {/if}
                </button>
                <button
                  onclick={() => openEdit(integration)}
                  class="inline-flex flex-1 items-center justify-center gap-1.5 rounded-lg border border-border px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
                >
                  <Pencil class="h-3.5 w-3.5" />
                  Edit
                </button>
              </div>
            </article>
          {/each}
        </div>
      {:else}
        <div class="rounded-xl border border-dashed border-border bg-muted/20 px-6 py-10 text-center">
          <div class="mx-auto flex h-11 w-11 items-center justify-center rounded-full bg-muted">
            <Plus class="h-5 w-5 text-muted-foreground" />
          </div>
          <h3 class="mt-3 font-medium">No providers connected yet</h3>
          <p class="mt-1 text-sm text-muted-foreground">
            Choose a provider from the list below to configure your first AI model.
          </p>
        </div>
      {/if}
    </section>

    {#if grouped.available.length > 0}
      <section class="space-y-4">
        <div>
          <h2 class="text-base font-semibold">Available providers</h2>
          <p class="text-sm text-muted-foreground">
            Add another provider now and switch between models whenever you need.
          </p>
        </div>

        <div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {#each grouped.available as integration}
            {@const color = PROVIDER_COLORS[integration.id] ?? '#6b7280'}
            {@const mark = PROVIDER_MARKS[integration.id] ?? integration.label.slice(0, 2).toUpperCase()}
            {@const provider = providerFor(integration.id)}
            <article class="flex flex-col rounded-xl border border-border bg-card p-4 transition-colors hover:border-primary/30 hover:bg-accent/20">
              <div class="flex items-start gap-3">
                <div
                  class="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg text-[11px] font-bold"
                  style="background:{color}18; color:{color}"
                  aria-hidden="true"
                >
                  {mark}
                </div>
                <div class="min-w-0 flex-1">
                  <h3 class="font-medium">{integration.label}</h3>
                  <p class="mt-0.5 text-xs text-muted-foreground">
                    {#if provider?.local}
                      Local · no API key
                    {:else if provider?.auth_type === 'token'}
                      Access token required
                    {:else}
                      API key required
                    {/if}
                  </p>
                </div>
              </div>

              <p class="mt-4 flex-1 text-sm text-muted-foreground">
                {#if provider?.local}
                  Run supported models locally without sending a credential to ApplyKit.
                {:else}
                  Save a provider credential and select the model you want ApplyKit to use.
                {/if}
              </p>

              <div class="mt-4 flex items-center justify-between gap-3">
                {#if provider?.credential_url}
                  <a
                    href={provider.credential_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    class="inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline"
                  >
                    {credentialActionLabel(provider.auth_type)}
                    <ExternalLink class="h-3 w-3" />
                  </a>
                {:else}
                  <span class="text-xs text-muted-foreground">Ready to configure</span>
                {/if}
                <button
                  onclick={() => openEdit(integration)}
                  class="inline-flex items-center gap-1.5 rounded-lg bg-primary px-3 py-2 text-sm font-semibold text-primary-foreground transition-colors hover:bg-primary/90"
                >
                  <Plus class="h-3.5 w-3.5" />
                  Connect
                </button>
              </div>
            </article>
          {/each}
        </div>
      </section>
    {/if}
  {/if}
</div>

<SettingsModal
  bind:open={modalOpen}
  initialProviderId={modalProviderId}
  initialModel={modalModel}
  initialApiKeyConfigured={modalApiKeyConfigured}
/>
