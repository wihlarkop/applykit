<script lang="ts">
  import { goto, invalidateAll } from '$app/navigation';
  import { page } from '$app/state';
  import { getModels, getSettings, testConnection, updateSettings } from '$lib/api';
  import ModelSelector from '$lib/components/ModelSelector.svelte';
  import { testConfiguredIntegration } from '$lib/integration-api';
  import {
    credentialActionLabel,
    customModelValidationError,
    isCustomModel,
    type CatalogProviderInfo,
  } from '$lib/llm-catalog';
  import {
    connectionTestMode,
    modalMode,
    modalTitle,
    primaryActionLabel,
  } from '$lib/settings-modal';
  import { toastState } from '$lib/toast.svelte';
  import type { TestConnectionResponse } from '$lib/types';
  import { errorMessage } from '$lib/utils';
  import {
    CheckCircle,
    CircleAlert,
    ExternalLink,
    Eye,
    EyeOff,
    KeyRound,
    Loader2,
    Server,
    ShieldCheck,
    Sparkles,
    X,
    XCircle,
  } from '@lucide/svelte';

  let {
    open = $bindable(false),
    initialProviderId = '',
    initialModel = '',
    initialApiKeyConfigured = false,
  }: {
    open: boolean;
    initialProviderId?: string;
    initialModel?: string;
    initialApiKeyConfigured?: boolean;
  } = $props();

  let providers: CatalogProviderInfo[] = $state([]);
  let selectedProviderId = $state('gemini');
  let selectedModel = $state('');
  let customMode = $state(false);
  let apiKey = $state('');
  let showApiKey = $state(false);
  let loading = $state(true);
  let testing = $state(false);
  let testResult: TestConnectionResponse | null = $state(null);
  let saveError = $state('');
  let source = $state<'database' | 'env' | 'none'>('none');
  let activeModel = $state('');
  let saving = $state<'activate' | 'only' | null>(null);

  const selectedProvider = $derived(
    providers.find((provider) => provider.id === selectedProviderId),
  );
  const selectedModelInfo = $derived(
    selectedProvider?.models.find((model) => model.value === selectedModel),
  );
  const mode = $derived(
    modalMode(initialProviderId, initialModel, initialApiKeyConfigured),
  );
  const isActive = $derived(
    Boolean(activeModel && activeModel.split('/', 1)[0] === selectedProviderId),
  );
  const title = $derived(modalTitle(mode, selectedProvider?.label ?? ''));
  const primaryLabel = $derived(primaryActionLabel(mode, isActive));
  const customModelError = $derived(
    customMode && selectedProvider
      ? customModelValidationError(selectedProvider.id, selectedModel)
      : null,
  );
  const unavailableCurrentModel = $derived(
    Boolean(
      initialModel &&
        selectedProvider &&
        !customMode &&
        !selectedProvider.models.some((model) => model.value === initialModel),
    ),
  );
  const canReuseStoredKey = $derived(
    Boolean(
      initialProviderId &&
        initialApiKeyConfigured &&
        selectedProvider?.requires_api_key,
    ),
  );
  const testMode = $derived(
    connectionTestMode({
      requiresApiKey: Boolean(selectedProvider?.requires_api_key),
      apiKey,
      canReuseStoredKey,
      providerId: selectedProviderId,
    }),
  );
  const canTest = $derived(
    Boolean(selectedModel && !customModelError && testMode !== 'disabled'),
  );
  const storedTestUsesOlderModel = $derived(
    testMode === 'stored' && Boolean(initialModel) && selectedModel !== initialModel,
  );
  const canSave = $derived(
    Boolean(
      selectedModel &&
        !customModelError &&
        (!selectedProvider?.requires_api_key || apiKey.trim() || canReuseStoredKey),
    ),
  );

  $effect(() => {
    if (!open) return;
    loadData();
  });

  function selectExistingModel(modelId: string): boolean {
    for (const provider of providers) {
      if (provider.models.some((model) => model.value === modelId)) {
        selectedProviderId = provider.id;
        selectedModel = modelId;
        customMode = false;
        return true;
      }
    }

    const providerId = modelId.split('/', 1)[0];
    const provider = providers.find(
      (item) => item.id === providerId && item.supports_custom_models,
    );
    if (provider) {
      selectedProviderId = provider.id;
      selectedModel = modelId;
      customMode = isCustomModel(provider, modelId);
      return true;
    }
    return false;
  }

  async function loadData() {
    loading = true;
    testResult = null;
    saveError = '';
    apiKey = '';
    showApiKey = false;
    customMode = false;

    try {
      const [modelsResponse, settingsResponse] = await Promise.all([
        getModels(),
        getSettings(),
      ]);
      providers = modelsResponse.providers as CatalogProviderInfo[];
      source = settingsResponse.source;
      activeModel = settingsResponse.model ?? '';

      if (initialProviderId) {
        const provider = providers.find((item) => item.id === initialProviderId);
        selectedProviderId = initialProviderId;
        selectedModel = initialModel || provider?.models[0]?.value || '';
        customMode = isCustomModel(provider, selectedModel);
      } else if (settingsResponse.model && selectExistingModel(settingsResponse.model)) {
        // Restore the current configuration when the modal is opened globally.
      } else if (providers.length > 0) {
        selectedProviderId = providers[0].id;
        selectedModel = providers[0].models[0]?.value ?? '';
      }
    } catch {
      saveError = 'Failed to load settings.';
    } finally {
      loading = false;
    }
  }

  function onProviderChange(id: string) {
    selectedProviderId = id;
    const provider = providers.find((item) => item.id === id);
    selectedModel = provider?.models[0]?.value ?? '';
    customMode = false;
    apiKey = '';
    testResult = null;
    saveError = '';
  }

  function toggleCustomMode() {
    if (!selectedProvider?.supports_custom_models) return;
    customMode = !customMode;
    selectedModel = customMode
      ? `${selectedProvider.id}/`
      : selectedProvider.models[0]?.value ?? '';
    testResult = null;
    saveError = '';
  }

  async function handleTest() {
    if (!canTest || !selectedProvider) return;

    testing = true;
    testResult = null;
    try {
      if (testMode === 'stored') {
        testResult = await testConfiguredIntegration(selectedProvider.id);
      } else {
        testResult = await testConnection({
          model: selectedModel.trim(),
          api_key: apiKey.trim() || null,
        });
      }
    } catch {
      testResult = {
        ok: false,
        message: 'Connection test request failed.',
      };
    } finally {
      testing = false;
    }
  }

  async function handleSave(activate: boolean) {
    if (!selectedModel) {
      saveError = 'Select a model.';
      return;
    }
    if (customModelError) {
      saveError = customModelError;
      return;
    }

    const keyToSave = apiKey.trim() || null;
    if (selectedProvider?.requires_api_key && !keyToSave && !canReuseStoredKey) {
      saveError = 'API key is required.';
      return;
    }

    saving = activate ? 'activate' : 'only';
    saveError = '';
    try {
      await updateSettings({
        model: selectedModel.trim(),
        api_key: keyToSave,
        activate,
      });
      toastState.success(
        activate
          ? isActive
            ? 'Provider settings updated.'
            : 'Saved and set as active model.'
          : keyToSave
            ? 'Provider saved without changing the active model.'
            : 'Model saved. Existing credential was kept.',
      );
      open = false;
      await invalidateAll();
      if (!page.data.isOnboarded) {
        await goto('/onboarding');
      }
    } catch (error) {
      saveError = errorMessage(error, 'Failed to save settings.');
    } finally {
      saving = null;
    }
  }

  function closeModal() {
    if (saving || testing) return;
    open = false;
  }

  function handleKeydown(event: KeyboardEvent) {
    if (event.key === 'Escape') closeModal();
  }
</script>

<svelte:window onkeydown={handleKeydown} />

{#if open}
  <div
    class="fixed inset-0 z-50 flex items-end justify-center bg-black/55 sm:items-center sm:p-4"
    onclick={closeModal}
    onkeydown={(event) => event.key === 'Escape' && closeModal()}
    role="dialog"
    tabindex="-1"
    aria-modal="true"
    aria-labelledby="provider-settings-title"
  >
    <div
      class="flex max-h-[94vh] w-full max-w-2xl flex-col overflow-hidden rounded-t-2xl border border-border bg-background shadow-2xl sm:max-h-[calc(100vh-2rem)] sm:rounded-2xl"
      onclick={(event) => event.stopPropagation()}
      role="presentation"
    >
      <header class="flex items-start justify-between gap-4 border-b border-border px-5 py-4 sm:px-6 sm:py-5">
        <div class="min-w-0">
          <div class="flex flex-wrap items-center gap-2">
            <h2 id="provider-settings-title" class="text-lg font-semibold tracking-tight">
              {title}
            </h2>
            {#if !loading && selectedProvider}
              {#if isActive}
                <span class="inline-flex items-center gap-1 rounded-full bg-green-100 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-green-700 dark:bg-green-950/60 dark:text-green-300">
                  <span class="h-1.5 w-1.5 rounded-full bg-green-500"></span>
                  Active
                </span>
              {:else if mode === 'edit'}
                <span class="inline-flex items-center gap-1 rounded-full bg-blue-100 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-blue-700 dark:bg-blue-950/60 dark:text-blue-300">
                  <CheckCircle class="h-3 w-3" />
                  Connected
                </span>
              {:else}
                <span class="rounded-full bg-muted px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
                  Not configured
                </span>
              {/if}
            {/if}
          </div>
          <p class="mt-1 text-sm text-muted-foreground">
            Choose a model, configure access, verify the connection, then save.
          </p>
        </div>
        <button
          onclick={closeModal}
          disabled={saving !== null || testing}
          class="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-accent hover:text-foreground disabled:opacity-50"
          aria-label="Close provider settings"
        >
          <X class="h-4 w-4" />
        </button>
      </header>

      {#if loading}
        <div class="flex min-h-72 flex-1 items-center justify-center gap-2 text-muted-foreground">
          <Loader2 class="h-5 w-5 animate-spin" />
          Loading provider settings…
        </div>
      {:else}
        <div class="flex-1 space-y-5 overflow-y-auto px-5 py-5 sm:px-6">
          {#if source === 'env'}
            <div class="flex items-start gap-3 rounded-xl border border-blue-200 bg-blue-50 p-3 text-sm text-blue-800 dark:border-blue-900 dark:bg-blue-950/30 dark:text-blue-300">
              <CircleAlert class="mt-0.5 h-4 w-4 shrink-0" />
              <span>
                ApplyKit currently uses configuration from <code class="font-mono">.env</code>.
                Saving here will override it with the database configuration.
              </span>
            </div>
          {/if}

          <section class="rounded-xl border border-border bg-card p-4 sm:p-5">
            <div class="flex items-start gap-3">
              <div class="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                <Server class="h-4 w-4" />
              </div>
              <div class="min-w-0 flex-1">
                <div class="flex items-center justify-between gap-3">
                  <div>
                    <p class="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">Provider</p>
                    <h3 class="mt-0.5 text-sm font-semibold">Choose where ApplyKit sends AI requests</h3>
                  </div>
                </div>

                {#if !initialProviderId}
                  <select
                    value={selectedProviderId}
                    onchange={(event) => onProviderChange(event.currentTarget.value)}
                    class="mt-3 w-full rounded-lg border border-border bg-background px-3 py-2.5 text-sm outline-none focus:ring-2 focus:ring-primary/30"
                    aria-label="AI provider"
                  >
                    {#each providers as provider}
                      <option value={provider.id}>{provider.label}</option>
                    {/each}
                  </select>
                {:else}
                  <div class="mt-3 flex items-center justify-between gap-3 rounded-lg bg-muted/50 px-3 py-2.5">
                    <div>
                      <p class="text-sm font-medium">{selectedProvider?.label}</p>
                      <p class="text-xs text-muted-foreground">
                        {#if selectedProvider?.local}
                          Local provider · no credential required
                        {:else if selectedProvider?.auth_type === 'token'}
                          Access token authentication
                        {:else}
                          API key authentication
                        {/if}
                      </p>
                    </div>
                    {#if selectedProvider?.local}
                      <span class="rounded bg-blue-100 px-2 py-1 text-[10px] font-semibold uppercase text-blue-700 dark:bg-blue-950 dark:text-blue-300">Local</span>
                    {/if}
                  </div>
                {/if}
              </div>
            </div>
          </section>

          <section class="rounded-xl border border-border bg-card p-4 sm:p-5">
            <div class="flex items-start gap-3">
              <div class="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                <Sparkles class="h-4 w-4" />
              </div>
              <div class="min-w-0 flex-1">
                <div class="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p class="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">Model</p>
                    <h3 class="mt-0.5 text-sm font-semibold">Select the model for this provider</h3>
                  </div>
                  {#if selectedProvider?.supports_custom_models}
                    <button
                      type="button"
                      onclick={toggleCustomMode}
                      class="text-xs font-medium text-primary hover:underline"
                    >
                      {customMode ? 'Choose from catalog' : 'Use custom model ID'}
                    </button>
                  {/if}
                </div>

                <div class="mt-3">
                  {#if customMode}
                    <input
                      id="custom-model-input"
                      bind:value={selectedModel}
                      placeholder={`${selectedProvider?.id ?? 'provider'}/model-name`}
                      maxlength="200"
                      spellcheck="false"
                      autocomplete="off"
                      class="w-full rounded-lg border border-border bg-background px-3 py-2.5 font-mono text-sm outline-none focus:ring-2 focus:ring-primary/30"
                    />
                    <div class="mt-2 flex flex-wrap items-center justify-between gap-2">
                      <span class="rounded bg-purple-100 px-2 py-1 text-[10px] font-semibold uppercase text-purple-700 dark:bg-purple-950 dark:text-purple-300">Custom model</span>
                      <span class="text-xs text-muted-foreground">Use the full LiteLLM model ID.</span>
                    </div>
                    {#if customModelError}
                      <p class="mt-2 text-xs text-red-600 dark:text-red-400">{customModelError}</p>
                    {/if}
                  {:else}
                    <ModelSelector
                      models={selectedProvider?.models ?? []}
                      bind:value={selectedModel}
                      unavailableValue={unavailableCurrentModel ? initialModel : ''}
                    />
                  {/if}
                </div>

                {#if unavailableCurrentModel && selectedModel === initialModel}
                  <div class="mt-3 flex items-start gap-2 rounded-lg border border-yellow-200 bg-yellow-50 px-3 py-2.5 text-xs text-yellow-800 dark:border-yellow-900 dark:bg-yellow-950/30 dark:text-yellow-300">
                    <CircleAlert class="h-4 w-4 shrink-0" />
                    <span>This model is no longer in the current catalog. Select an active model to replace it.</span>
                  </div>
                {:else if selectedModelInfo}
                  <div class="mt-3 flex flex-wrap gap-1.5">
                    <span class="rounded bg-blue-100 px-2 py-1 text-[10px] font-semibold uppercase text-blue-700 dark:bg-blue-950 dark:text-blue-300">Catalog</span>
                    {#if selectedModelInfo.status !== 'stable'}
                      <span class="rounded bg-yellow-100 px-2 py-1 text-[10px] font-semibold uppercase text-yellow-800 dark:bg-yellow-950 dark:text-yellow-300">{selectedModelInfo.status}</span>
                    {/if}
                    {#if selectedModelInfo.free_tier}
                      <span class="rounded bg-green-100 px-2 py-1 text-[10px] font-semibold uppercase text-green-700 dark:bg-green-950 dark:text-green-300">Free tier</span>
                    {/if}
                    {#if selectedProvider?.local}
                      <span class="rounded bg-blue-100 px-2 py-1 text-[10px] font-semibold uppercase text-blue-700 dark:bg-blue-950 dark:text-blue-300">Local</span>
                    {/if}
                    {#each selectedModelInfo.traits as trait}
                      <span class="rounded bg-muted px-2 py-1 text-[10px] uppercase text-muted-foreground">{trait.replaceAll('_', ' ')}</span>
                    {/each}
                  </div>
                {/if}
              </div>
            </div>
          </section>

          <section class="rounded-xl border border-border bg-card p-4 sm:p-5">
            <div class="flex items-start gap-3">
              <div class="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                <KeyRound class="h-4 w-4" />
              </div>
              <div class="min-w-0 flex-1">
                <div class="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p class="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">Credential</p>
                    <h3 class="mt-0.5 text-sm font-semibold">
                      {#if selectedProvider?.requires_api_key}
                        {selectedProvider.auth_type === 'token' ? 'Provide an access token' : 'Provide an API key'}
                      {:else}
                        No credential required
                      {/if}
                    </h3>
                  </div>
                  {#if selectedProvider?.credential_url}
                    <a
                      href={selectedProvider.credential_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      class="inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline"
                    >
                      {credentialActionLabel(selectedProvider.auth_type)}
                      <ExternalLink class="h-3 w-3" />
                    </a>
                  {/if}
                </div>

                {#if selectedProvider?.requires_api_key}
                  {#if canReuseStoredKey}
                    <div class="mt-3 flex items-center gap-2 rounded-lg border border-green-200 bg-green-50 px-3 py-2 text-xs text-green-700 dark:border-green-900 dark:bg-green-950/30 dark:text-green-300">
                      <ShieldCheck class="h-4 w-4 shrink-0" />
                      A credential is already saved. Leave the field empty to keep using it.
                    </div>
                  {/if}
                  <div class="relative mt-3">
                    <input
                      id="api-key-input"
                      type={showApiKey ? 'text' : 'password'}
                      bind:value={apiKey}
                      placeholder={canReuseStoredKey ? 'Enter a new value only to replace it' : 'Enter your credential…'}
                      class="w-full rounded-lg border border-border bg-background px-3 py-2.5 pr-11 text-sm outline-none focus:ring-2 focus:ring-primary/30"
                      autocomplete="new-password"
                    />
                    <button
                      type="button"
                      onclick={() => (showApiKey = !showApiKey)}
                      class="absolute right-2.5 top-1/2 flex h-8 w-8 -translate-y-1/2 items-center justify-center rounded-md text-muted-foreground hover:bg-accent hover:text-foreground"
                      aria-label={showApiKey ? 'Hide credential' : 'Show credential'}
                    >
                      {#if showApiKey}
                        <EyeOff class="h-4 w-4" />
                      {:else}
                        <Eye class="h-4 w-4" />
                      {/if}
                    </button>
                  </div>
                {:else}
                  <p class="mt-3 text-sm text-muted-foreground">
                    This provider runs locally. ApplyKit will connect without an API key or access token.
                  </p>
                {/if}
              </div>
            </div>
          </section>

          <section class="rounded-xl border border-border bg-card p-4 sm:p-5">
            <div class="flex items-start gap-3">
              <div class="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                <ShieldCheck class="h-4 w-4" />
              </div>
              <div class="min-w-0 flex-1">
                <p class="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">Verification</p>
                <div class="mt-0.5 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                  <div>
                    <h3 class="text-sm font-semibold">Test before saving</h3>
                    <p class="mt-1 text-xs text-muted-foreground">
                      {#if testMode === 'stored'}
                        Uses the credential and model already saved securely on the backend.
                      {:else if selectedProvider?.local}
                        Sends one minimal request to your local provider.
                      {:else}
                        Sends one minimal request with the credential entered above.
                      {/if}
                    </p>
                  </div>
                  <button
                    onclick={handleTest}
                    disabled={testing || !canTest}
                    class="inline-flex shrink-0 items-center justify-center gap-2 rounded-lg border border-border px-3.5 py-2 text-sm font-medium transition-colors hover:bg-accent disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {#if testing}
                      <Loader2 class="h-4 w-4 animate-spin" />
                      Testing…
                    {:else if testMode === 'stored'}
                      Test saved connection
                    {:else}
                      Test connection
                    {/if}
                  </button>
                </div>

                {#if storedTestUsesOlderModel}
                  <div class="mt-3 flex items-start gap-2 rounded-lg border border-yellow-200 bg-yellow-50 px-3 py-2 text-xs text-yellow-800 dark:border-yellow-900 dark:bg-yellow-950/30 dark:text-yellow-300">
                    <CircleAlert class="h-4 w-4 shrink-0" />
                    The saved connection test uses the previously saved model. Save this model first to test it with the stored credential.
                  </div>
                {/if}

                {#if testResult}
                  <div class="mt-3 flex items-start gap-2 rounded-lg border px-3 py-2.5 text-sm {testResult.ok
                    ? 'border-green-200 bg-green-50 text-green-700 dark:border-green-900 dark:bg-green-950/30 dark:text-green-300'
                    : 'border-red-200 bg-red-50 text-red-700 dark:border-red-900 dark:bg-red-950/30 dark:text-red-300'}">
                    {#if testResult.ok}
                      <CheckCircle class="mt-0.5 h-4 w-4 shrink-0" />
                    {:else}
                      <XCircle class="mt-0.5 h-4 w-4 shrink-0" />
                    {/if}
                    <div>
                      <p class="font-medium">{testResult.ok ? 'Connection successful' : 'Connection failed'}</p>
                      <p class="mt-0.5 text-xs opacity-90">{testResult.message}</p>
                    </div>
                  </div>
                {/if}
              </div>
            </div>
          </section>

          {#if saveError}
            <div class="flex items-start gap-2 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-900 dark:bg-red-950/30 dark:text-red-300">
              <XCircle class="mt-0.5 h-4 w-4 shrink-0" />
              <span>{saveError}</span>
            </div>
          {/if}
        </div>

        <footer class="border-t border-border bg-background/95 px-5 py-4 backdrop-blur sm:px-6">
          <div class="flex flex-col-reverse gap-2 sm:flex-row sm:items-center sm:justify-between">
            <button
              onclick={closeModal}
              disabled={saving !== null || testing}
              class="inline-flex items-center justify-center rounded-lg border border-border px-4 py-2.5 text-sm font-medium transition-colors hover:bg-accent disabled:opacity-50"
            >
              Cancel
            </button>

            <div class="flex flex-col-reverse gap-2 sm:flex-row">
              {#if !isActive}
                <button
                  onclick={() => handleSave(false)}
                  disabled={saving !== null || testing || !canSave}
                  class="inline-flex items-center justify-center gap-2 rounded-lg border border-border px-4 py-2.5 text-sm font-semibold transition-colors hover:bg-accent disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {#if saving === 'only'}
                    <Loader2 class="h-4 w-4 animate-spin" />
                  {/if}
                  Save only
                </button>
              {/if}
              <button
                onclick={() => handleSave(true)}
                disabled={saving !== null || testing || !canSave}
                class="inline-flex items-center justify-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-sm font-semibold text-primary-foreground shadow-sm transition-colors hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {#if saving === 'activate'}
                  <Loader2 class="h-4 w-4 animate-spin" />
                {/if}
                {primaryLabel}
              </button>
            </div>
          </div>
          {#if !isActive}
            <p class="mt-2 text-center text-[11px] text-muted-foreground sm:text-right">
              Save only keeps the current active provider unchanged.
            </p>
          {/if}
        </footer>
      {/if}
    </div>
  </div>
{/if}
