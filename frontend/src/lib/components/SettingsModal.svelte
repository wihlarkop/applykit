<script lang="ts">
  import { tick } from 'svelte';
  import { goto, invalidateAll } from '$app/navigation';
  import { page } from '$app/state';
  import { getModels, getSettings, testConnection, updateSettings } from '$lib/api';
  import ModelSelector from '$lib/components/ModelSelector.svelte';
  import ProviderCredentialsPanel from '$lib/components/ProviderCredentialsPanel.svelte';
  import {
    getCredentialPolicy,
    getProviderCredentials,
    testConfiguredIntegration,
    updateCredentialPolicy,
  } from '$lib/integration-api';
  import {
    credentialActionLabel,
    customModelValidationError,
    isCustomModel,
    type CatalogProviderInfo,
  } from '$lib/llm-catalog';
  import {
    canUseAutomaticStrategy,
    credentialStrategyDescription,
    credentialStrategyLabel,
  } from '$lib/provider-credentials';
  import type {
    CredentialStrategy,
    ProviderCredentialInfo,
  } from '$lib/provider-credential-types';
  import {
    defaultSettingsTab,
    footerActionForTab,
    type ProviderSettingsTab,
  } from '$lib/settings-modal-tabs';
  import {
    connectionTestMode,
    focusRestorationTarget,
    focusTrapTarget,
    modalMode,
    modalTitle,
    primaryActionLabel,
    saveSettingsWithRefresh,
  } from '$lib/settings-modal';
  import { toastState } from '$lib/toast.svelte';
  import type { TestConnectionResponse } from '$lib/types';
  import { errorMessage } from '$lib/utils';
  import {
    Activity,
    CheckCircle,
    CircleAlert,
    ExternalLink,
    Eye,
    EyeOff,
    KeyRound,
    Loader2,
    Route,
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
    onsaved = async () => undefined,
  }: {
    open: boolean;
    initialProviderId?: string;
    initialModel?: string;
    initialApiKeyConfigured?: boolean;
    onsaved?: () => Promise<void> | void;
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
  let hasStoredCredential = $state(false);
  let activeTab: ProviderSettingsTab = $state('model');
  let credentialSummary: ProviderCredentialInfo[] = $state([]);
  let routingStrategy: CredentialStrategy = $state('manual');
  let routingMaxAttempts = $state(2);
  let savedRoutingStrategy: CredentialStrategy = $state('manual');
  let savedRoutingMaxAttempts = $state(2);
  let savingRouting = $state(false);
  let parentRefreshFailed = $state(false);
  let refreshingParent = $state(false);
  let panelElement: HTMLElement | undefined = $state();
  let previouslyFocused: HTMLElement | null = null;
  let previousBodyOverflow = '';
  let previousBodyPosition = '';
  let previousBodyTop = '';
  let previousBodyLeft = '';
  let previousBodyWidth = '';
  let lockedScrollX = 0;
  let lockedScrollY = 0;

  const selectedProvider = $derived(
    providers.find((provider) => provider.id === selectedProviderId),
  );
  const selectedModelInfo = $derived(
    selectedProvider?.models.find((model) => model.value === selectedModel),
  );
  const managesCredentialVault = $derived(
    Boolean(initialProviderId && selectedProvider?.requires_api_key),
  );
  const mode = $derived(
    modalMode(initialProviderId, initialModel, hasStoredCredential),
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
    Boolean(hasStoredCredential && selectedProvider?.requires_api_key),
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
        (!selectedProvider?.requires_api_key ||
          hasStoredCredential ||
          (!managesCredentialVault && apiKey.trim())),
    ),
  );
  const automaticRoutingAvailable = $derived(
    canUseAutomaticStrategy(credentialSummary),
  );
  const routingDirty = $derived(
    routingStrategy !== savedRoutingStrategy ||
      routingMaxAttempts !== savedRoutingMaxAttempts,
  );

  $effect(() => {
    if (!open) return;
    loadData();
  });

  $effect(() => {
    if (!open || typeof document === 'undefined') return;

    previouslyFocused = document.activeElement instanceof HTMLElement
      ? document.activeElement
      : null;
    lockedScrollX = window.scrollX;
    lockedScrollY = window.scrollY;
    previousBodyOverflow = document.body.style.overflow;
    previousBodyPosition = document.body.style.position;
    previousBodyTop = document.body.style.top;
    previousBodyLeft = document.body.style.left;
    previousBodyWidth = document.body.style.width;
    document.body.style.overflow = 'hidden';
    document.body.style.position = 'fixed';
    document.body.style.top = `-${lockedScrollY}px`;
    document.body.style.left = `-${lockedScrollX}px`;
    document.body.style.width = '100%';
    void tick().then(() => panelElement?.focus());

    return () => {
      document.body.style.overflow = previousBodyOverflow;
      document.body.style.position = previousBodyPosition;
      document.body.style.top = previousBodyTop;
      document.body.style.left = previousBodyLeft;
      document.body.style.width = previousBodyWidth;
      const replacementTrigger = Array.from(
        document.querySelectorAll<HTMLElement>('[data-provider-settings-trigger]'),
      ).find(
        (element) => element.dataset.providerSettingsTrigger === initialProviderId,
      ) ?? null;
      focusRestorationTarget([
        previouslyFocused,
        replacementTrigger,
        document.getElementById('ai-settings-heading'),
      ])?.focus({ preventScroll: true });
      window.scrollTo(lockedScrollX, lockedScrollY);
    };
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

  async function refreshCredentialState(providerId = selectedProviderId) {
    const provider = providers.find((item) => item.id === providerId);
    if (!provider?.requires_api_key) {
      hasStoredCredential = false;
      credentialSummary = [];
      routingStrategy = 'manual';
      routingMaxAttempts = 2;
      savedRoutingStrategy = 'manual';
      savedRoutingMaxAttempts = 2;
      return;
    }

    try {
      const [credentialsResponse, policyResponse] = await Promise.all([
        getProviderCredentials(providerId),
        getCredentialPolicy(providerId),
      ]);
      credentialSummary = credentialsResponse.credentials;
      hasStoredCredential = credentialsResponse.credentials.some(
        (credential) => credential.is_active && credential.is_enabled,
      );
      routingStrategy = policyResponse.strategy;
      routingMaxAttempts = policyResponse.max_attempts;
      savedRoutingStrategy = policyResponse.strategy;
      savedRoutingMaxAttempts = policyResponse.max_attempts;
      await invalidateAll();
    } catch {
      hasStoredCredential = initialApiKeyConfigured;
    }
  }

  async function loadData() {
    loading = true;
    testResult = null;
    saveError = '';
    apiKey = '';
    showApiKey = false;
    customMode = false;
    hasStoredCredential = initialApiKeyConfigured;
    parentRefreshFailed = false;

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
        if (provider?.requires_api_key) {
          await refreshCredentialState(initialProviderId);
        }
        activeTab = defaultSettingsTab({
          isExistingProvider: true,
          requiresCredential: Boolean(provider?.requires_api_key),
        });
      } else if (settingsResponse.model && selectExistingModel(settingsResponse.model)) {
        hasStoredCredential = settingsResponse.api_key_configured;
        activeTab = 'model';
      } else if (providers.length > 0) {
        selectedProviderId = providers[0].id;
        selectedModel = providers[0].models[0]?.value ?? '';
        hasStoredCredential = false;
        activeTab = 'model';
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
    hasStoredCredential = false;
    credentialSummary = [];
    activeTab = 'model';
    testResult = null;
    saveError = '';
    parentRefreshFailed = false;
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

  function selectTab(tab: ProviderSettingsTab) {
    activeTab = tab;
    saveError = '';
    testResult = null;
  }

  async function handleTabKeydown(event: KeyboardEvent, currentTab: ProviderSettingsTab) {
    const tabs: ProviderSettingsTab[] = ['model', 'credentials', 'routing'];
    const currentIndex = tabs.indexOf(currentTab);
    let nextIndex = currentIndex;

    if (event.key === 'ArrowRight') nextIndex = (currentIndex + 1) % tabs.length;
    else if (event.key === 'ArrowLeft') nextIndex = (currentIndex - 1 + tabs.length) % tabs.length;
    else if (event.key === 'Home') nextIndex = 0;
    else if (event.key === 'End') nextIndex = tabs.length - 1;
    else return;

    event.preventDefault();
    const nextTab = tabs[nextIndex];
    selectTab(nextTab);
    await tick();
    document.getElementById(`provider-tab-${nextTab}`)?.focus();
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

    const keyToSave = managesCredentialVault ? null : apiKey.trim() || null;
    if (selectedProvider?.requires_api_key && !keyToSave && !hasStoredCredential) {
      saveError = 'Add a credential before saving this provider.';
      return;
    }

    saving = activate ? 'activate' : 'only';
    saveError = '';
    try {
      const result = await saveSettingsWithRefresh(
        () =>
          updateSettings({
            model: selectedModel.trim(),
            api_key: keyToSave,
            activate,
          }),
        async () => {
          await onsaved();
        },
      );

      if (result.status === 'save_failed') {
        saveError = errorMessage(result.error, 'Failed to save settings.');
        return;
      }
      if (result.status === 'refresh_failed') {
        saveError = 'Provider saved, but the settings list could not refresh. Try refreshing again.';
        parentRefreshFailed = true;
        return;
      }

      parentRefreshFailed = false;

      toastState.success(
        activate
          ? isActive
            ? 'Model settings updated.'
            : 'Saved and set as active model.'
          : 'Model saved without changing the active provider.',
      );
      open = false;
      await invalidateAll();
      if (!page.data.isOnboarded) {
        await goto('/onboarding');
      }
    } catch (error) {
      saveError = errorMessage(error, 'Failed to save settings.');
    } finally {
      apiKey = '';
      showApiKey = false;
      saving = null;
    }
  }

  async function handleCredentialChanged() {
    try {
      await refreshCredentialState(selectedProviderId);
      await onsaved();
      parentRefreshFailed = false;
    } catch {
      saveError = 'Credential saved, but the settings list could not refresh.';
      parentRefreshFailed = true;
    }
  }

  async function retryParentRefresh() {
    refreshingParent = true;
    try {
      await onsaved();
      parentRefreshFailed = false;
      saveError = '';
      toastState.success('Settings list refreshed.');
    } catch {
      saveError = 'The settings list still could not refresh. Try again.';
    } finally {
      refreshingParent = false;
    }
  }

  async function handleSaveRouting() {
    if (!selectedProvider || !routingDirty) return;
    if (routingStrategy !== 'manual' && !automaticRoutingAvailable) {
      saveError = 'Automatic routing requires at least two enabled credentials.';
      return;
    }

    savingRouting = true;
    saveError = '';
    try {
      const response = await updateCredentialPolicy(
        selectedProvider.id,
        routingStrategy,
        routingStrategy === 'manual' ? 2 : routingMaxAttempts,
      );
      routingStrategy = response.strategy;
      routingMaxAttempts = response.max_attempts;
      savedRoutingStrategy = response.strategy;
      savedRoutingMaxAttempts = response.max_attempts;
      toastState.success('Credential routing updated.');
      await invalidateAll();
    } catch (error) {
      saveError = errorMessage(error, 'Failed to update credential routing.');
    } finally {
      savingRouting = false;
    }
  }

  function closeModal() {
    if (saving || testing || savingRouting) return;
    apiKey = '';
    showApiKey = false;
    open = false;
  }

  function handleBackdropClick(event: MouseEvent) {
    if (event.target === event.currentTarget) closeModal();
  }

  function handleKeydown(event: KeyboardEvent) {
    if (event.key === 'Escape') {
      closeModal();
      return;
    }
    if (event.key !== 'Tab' || !panelElement) return;

    const focusable = Array.from(
      panelElement.querySelectorAll<HTMLElement>(
        'button:not([disabled]), a[href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
      ),
    ).filter((element) => !element.hasAttribute('hidden'));
    if (focusable.length === 0) return;

    const target = focusTrapTarget(
      focusable,
      document.activeElement instanceof HTMLElement
        ? document.activeElement
        : null,
      panelElement,
      event.shiftKey,
    );
    if (target) {
      event.preventDefault();
      target.focus();
    }
  }
</script>

<svelte:window onkeydown={handleKeydown} />

{#if open}
  <div
    class="panel-overlay fixed inset-0 z-[70] bg-black/55"
    onclick={handleBackdropClick}
    role="presentation"
  >
    <div
      bind:this={panelElement}
      class="provider-panel ml-auto flex h-full w-full max-w-[46rem] flex-col overflow-hidden border-l border-border bg-background shadow-2xl"
      role="dialog"
      tabindex="-1"
      aria-modal="true"
      aria-labelledby="provider-settings-title"
    >
      <header class="flex shrink-0 items-start justify-between gap-4 border-b border-border px-5 py-4 sm:px-6">
        <div class="flex min-w-0 items-start gap-3">
          <div class="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary">
            <Sparkles class="h-5 w-5" />
          </div>
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
                {:else if hasStoredCredential}
                  <span class="inline-flex items-center gap-1 rounded-full bg-blue-100 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-blue-700 dark:bg-blue-950/60 dark:text-blue-300">
                    <CheckCircle class="h-3 w-3" /> Connected
                  </span>
                {:else}
                  <span class="rounded-full bg-muted px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
                    Not configured
                  </span>
                {/if}
              {/if}
            </div>
            {#if managesCredentialVault}
              <p class="mt-1 text-sm text-muted-foreground">
                {credentialSummary.length} credential{credentialSummary.length === 1 ? '' : 's'} &middot;
                {credentialStrategyLabel(savedRoutingStrategy)} strategy
              </p>
            {:else}
              <p class="mt-1 text-sm text-muted-foreground">
                Choose a provider and model, verify access, then save.
              </p>
            {/if}
          </div>
        </div>
        <button
          onclick={closeModal}
          disabled={saving !== null || testing || savingRouting}
          class="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-accent hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 disabled:opacity-50"
          aria-label="Close provider settings"
        >
          <X class="h-4 w-4" />
        </button>
      </header>

      {#if managesCredentialVault}
        <div class="flex shrink-0 overflow-x-auto border-b border-border bg-background px-5 sm:px-6" role="tablist" aria-label="Provider settings sections">
          <button
            id="provider-tab-model"
            type="button"
            role="tab"
            onclick={() => selectTab('model')}
            onkeydown={(event) => handleTabKeydown(event, 'model')}
            aria-selected={activeTab === 'model'}
            aria-controls="provider-settings-content"
            tabindex={activeTab === 'model' ? 0 : -1}
            class="inline-flex min-h-12 shrink-0 items-center gap-2 border-b-2 px-3 py-3 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-primary/40 {activeTab === 'model' ? 'border-primary text-foreground' : 'border-transparent text-muted-foreground hover:text-foreground'}"
          >
            <Sparkles class="h-4 w-4" /> Model
          </button>
          <button
            id="provider-tab-credentials"
            type="button"
            role="tab"
            onclick={() => selectTab('credentials')}
            onkeydown={(event) => handleTabKeydown(event, 'credentials')}
            aria-selected={activeTab === 'credentials'}
            aria-controls="provider-settings-content"
            tabindex={activeTab === 'credentials' ? 0 : -1}
            class="inline-flex min-h-12 shrink-0 items-center gap-2 border-b-2 px-3 py-3 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-primary/40 {activeTab === 'credentials' ? 'border-primary text-foreground' : 'border-transparent text-muted-foreground hover:text-foreground'}"
          >
            <KeyRound class="h-4 w-4" /> Credentials
            <span class="rounded-full bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground">
              {credentialSummary.length}
            </span>
          </button>
          <button
            id="provider-tab-routing"
            type="button"
            role="tab"
            onclick={() => selectTab('routing')}
            onkeydown={(event) => handleTabKeydown(event, 'routing')}
            aria-selected={activeTab === 'routing'}
            aria-controls="provider-settings-content"
            tabindex={activeTab === 'routing' ? 0 : -1}
            class="inline-flex min-h-12 shrink-0 items-center gap-2 border-b-2 px-3 py-3 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-primary/40 {activeTab === 'routing' ? 'border-primary text-foreground' : 'border-transparent text-muted-foreground hover:text-foreground'}"
          >
            <Route class="h-4 w-4" /> Routing
          </button>
        </div>
      {/if}

      {#if loading}
        <div class="flex min-h-80 flex-1 items-center justify-center gap-2 text-muted-foreground">
          <Loader2 class="h-5 w-5 animate-spin" />
          Loading provider settings...
        </div>
      {:else}
        <div
          id={managesCredentialVault ? 'provider-settings-content' : undefined}
          role={managesCredentialVault ? 'tabpanel' : undefined}
          aria-labelledby={managesCredentialVault ? `provider-tab-${activeTab}` : undefined}
          class="min-h-0 flex-1 overflow-y-auto overscroll-contain px-5 py-5 sm:px-6"
        >
          {#if source === 'env' && activeTab === 'model'}
            <div class="mb-5 flex items-start gap-3 rounded-xl border border-blue-200 bg-blue-50 p-3 text-sm text-blue-800 dark:border-blue-900 dark:bg-blue-950/30 dark:text-blue-300">
              <CircleAlert class="mt-0.5 h-4 w-4 shrink-0" />
              <span>
                ApplyKit currently uses configuration from <code class="font-mono">.env</code>.
                Saving here will override it with database settings.
              </span>
            </div>
          {/if}

          {#if activeTab === 'model'}
            <div class="mx-auto max-w-2xl space-y-7">
              {#if !initialProviderId}
                <section>
                  <div class="flex items-center gap-2">
                    <Server class="h-4 w-4 text-primary" />
                    <h3 class="text-base font-semibold">Provider</h3>
                  </div>
                  <p class="mt-1 text-sm text-muted-foreground">
                    Choose where ApplyKit sends AI requests.
                  </p>
                  <select
                    value={selectedProviderId}
                    onchange={(event) => onProviderChange(event.currentTarget.value)}
                    class="mt-3 w-full rounded-xl border border-border bg-background px-3 py-3 text-sm outline-none focus:ring-2 focus:ring-primary/30"
                    aria-label="AI provider"
                  >
                    {#each providers as provider}
                      <option value={provider.id}>{provider.label}</option>
                    {/each}
                  </select>
                </section>
                <div class="border-t border-border"></div>
              {/if}

              <section>
                <div class="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <div class="flex items-center gap-2">
                      <Sparkles class="h-4 w-4 text-primary" />
                      <h3 class="text-base font-semibold">Model</h3>
                    </div>
                    <p class="mt-1 text-sm text-muted-foreground">
                      Select the model used for this provider.
                    </p>
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
                      bind:value={selectedModel}
                      placeholder={`${selectedProvider?.id ?? 'provider'}/model-name`}
                      maxlength="200"
                      spellcheck="false"
                      autocomplete="off"
                      class="w-full rounded-xl border border-border bg-background px-3 py-3 font-mono text-sm outline-none focus:ring-2 focus:ring-primary/30"
                    />
                    <div class="mt-2 flex flex-wrap items-center justify-between gap-2">
                      <span class="rounded bg-purple-100 px-2 py-1 text-[10px] font-semibold uppercase text-purple-700 dark:bg-purple-950 dark:text-purple-300">
                        Custom model
                      </span>
                      <span class="text-xs text-muted-foreground">Use the full LiteLLM model ID.</span>
                    </div>
                    {#if customModelError}
                      <p class="mt-2 text-xs text-red-600 dark:text-red-400">
                        {customModelError}
                      </p>
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
                    Select an active catalog model to replace this unavailable model.
                  </div>
                {:else if selectedModelInfo}
                  <div class="mt-3 flex flex-wrap gap-1.5">
                    <span class="rounded bg-blue-100 px-2 py-1 text-[10px] font-semibold uppercase text-blue-700 dark:bg-blue-950 dark:text-blue-300">
                      Catalog
                    </span>
                    {#if selectedModelInfo.status !== 'stable'}
                      <span class="rounded bg-yellow-100 px-2 py-1 text-[10px] font-semibold uppercase text-yellow-800 dark:bg-yellow-950 dark:text-yellow-300">
                        {selectedModelInfo.status}
                      </span>
                    {/if}
                    {#if selectedModelInfo.free_tier}
                      <span class="rounded bg-green-100 px-2 py-1 text-[10px] font-semibold uppercase text-green-700 dark:bg-green-950 dark:text-green-300">
                        Free tier
                      </span>
                    {/if}
                    {#each selectedModelInfo.traits as trait}
                      <span class="rounded bg-muted px-2 py-1 text-[10px] uppercase text-muted-foreground">
                        {trait.replaceAll('_', ' ')}
                      </span>
                    {/each}
                  </div>
                {/if}
              </section>

              {#if !managesCredentialVault}
                <div class="border-t border-border"></div>
                <section>
                  <div class="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <div class="flex items-center gap-2">
                        <KeyRound class="h-4 w-4 text-primary" />
                        <h3 class="text-base font-semibold">
                          {selectedProvider?.requires_api_key
                            ? selectedProvider.auth_type === 'token'
                              ? 'Access token'
                              : 'API key'
                            : 'Local access'}
                        </h3>
                      </div>
                      <p class="mt-1 text-sm text-muted-foreground">
                        {selectedProvider?.requires_api_key
                          ? 'Enter the first credential for this provider.'
                          : 'This provider runs locally and does not need a credential.'}
                      </p>
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
                    <div class="relative mt-3">
                      <input
                        type={showApiKey ? 'text' : 'password'}
                        bind:value={apiKey}
                        placeholder="Enter your credential…"
                        class="w-full rounded-xl border border-border bg-background px-3 py-3 pr-11 text-sm outline-none focus:ring-2 focus:ring-primary/30"
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
                  {/if}
                </section>
              {/if}

              <div class="border-t border-border"></div>
              <section>
                <div class="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                  <div>
                    <div class="flex items-center gap-2">
                      <ShieldCheck class="h-4 w-4 text-primary" />
                      <h3 class="text-base font-semibold">Test model connection</h3>
                    </div>
                    <p class="mt-1 text-sm text-muted-foreground">
                      {#if testMode === 'stored'}
                        Uses the active credential stored securely on the backend.
                      {:else if selectedProvider?.local}
                        Sends one minimal request to the local provider.
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
                      <Loader2 class="h-4 w-4 animate-spin" /> Testing…
                    {:else}
                      <Activity class="h-4 w-4" /> Test connection
                    {/if}
                  </button>
                </div>

                {#if storedTestUsesOlderModel}
                  <div class="mt-3 flex items-start gap-2 rounded-lg border border-yellow-200 bg-yellow-50 px-3 py-2 text-xs text-yellow-800 dark:border-yellow-900 dark:bg-yellow-950/30 dark:text-yellow-300">
                    <CircleAlert class="h-4 w-4 shrink-0" />
                    Save this model first; the test currently uses the previously saved model.
                  </div>
                {/if}

                {#if testResult}
                  <div class="mt-3 flex items-start gap-2 rounded-lg border px-3 py-2.5 text-sm {testResult.ok ? 'border-green-200 bg-green-50 text-green-700 dark:border-green-900 dark:bg-green-950/30 dark:text-green-300' : 'border-red-200 bg-red-50 text-red-700 dark:border-red-900 dark:bg-red-950/30 dark:text-red-300'}">
                    {#if testResult.ok}
                      <CheckCircle class="mt-0.5 h-4 w-4 shrink-0" />
                    {:else}
                      <XCircle class="mt-0.5 h-4 w-4 shrink-0" />
                    {/if}
                    <div>
                      <p class="font-medium">
                        {testResult.ok ? 'Connection successful' : 'Connection failed'}
                      </p>
                      <p class="mt-0.5 text-xs opacity-90">{testResult.message}</p>
                    </div>
                  </div>
                {/if}
              </section>
            </div>
          {:else if activeTab === 'credentials' && selectedProvider}
            <ProviderCredentialsPanel
              providerId={selectedProvider.id}
              providerLabel={selectedProvider.label}
              credentialUrl={selectedProvider.credential_url}
              authType={selectedProvider.auth_type}
              onChanged={handleCredentialChanged}
            />
          {:else if activeTab === 'routing'}
            <div class="mx-auto max-w-2xl space-y-5">
              <div>
                <div class="flex items-center gap-2">
                  <Route class="h-4 w-4 text-primary" />
                  <h3 class="text-base font-semibold">Credential routing</h3>
                </div>
                <p class="mt-1 text-sm text-muted-foreground">
                  Choose how ApplyKit selects a credential for each request.
                </p>
              </div>

              <div class="grid gap-3">
                {#each ['manual', 'failover', 'round_robin'] as strategy}
                  {@const typedStrategy = strategy as CredentialStrategy}
                  {@const automatic = typedStrategy !== 'manual'}
                  <button
                    type="button"
                    onclick={() => (routingStrategy = typedStrategy)}
                    disabled={automatic && !automaticRoutingAvailable}
                    class="flex items-start gap-3 rounded-xl border p-4 text-left transition-colors disabled:cursor-not-allowed disabled:opacity-50 {routingStrategy === typedStrategy ? 'border-primary bg-primary/5' : 'border-border hover:bg-accent/40'}"
                  >
                    <span class="mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-full border {routingStrategy === typedStrategy ? 'border-primary bg-primary' : 'border-muted-foreground/50'}">
                      {#if routingStrategy === typedStrategy}
                        <span class="h-1.5 w-1.5 rounded-full bg-primary-foreground"></span>
                      {/if}
                    </span>
                    <span class="min-w-0 flex-1">
                      <span class="flex flex-wrap items-center gap-2 text-sm font-semibold">
                        {credentialStrategyLabel(typedStrategy)}
                        {#if typedStrategy === 'failover'}
                          <span class="rounded bg-green-100 px-1.5 py-0.5 text-[9px] font-semibold uppercase text-green-700 dark:bg-green-950/60 dark:text-green-300">
                            Recommended
                          </span>
                        {/if}
                        {#if typedStrategy === 'round_robin'}
                          <span class="rounded bg-muted px-1.5 py-0.5 text-[9px] font-semibold uppercase text-muted-foreground">
                            Advanced
                          </span>
                        {/if}
                      </span>
                      <span class="mt-1 block text-xs text-muted-foreground">
                        {credentialStrategyDescription(typedStrategy)}
                      </span>
                      {#if automatic && !automaticRoutingAvailable}
                        <span class="mt-1 block text-[11px] text-yellow-700 dark:text-yellow-300">
                          Requires at least two enabled credentials.
                        </span>
                      {/if}
                    </span>
                  </button>
                {/each}
              </div>

              {#if routingStrategy !== 'manual'}
                <label class="flex items-center justify-between gap-4 rounded-xl border border-border bg-muted/30 px-4 py-3 text-sm">
                  <span>
                    <span class="font-semibold">Maximum attempts</span>
                    <span class="mt-0.5 block text-xs text-muted-foreground">
                      Includes the first credential. Lower values reduce duplicate cost risk.
                    </span>
                  </span>
                  <select
                    bind:value={routingMaxAttempts}
                    class="rounded-lg border border-border bg-background px-3 py-2 text-sm font-medium"
                  >
                    {#each [2, 3, 4, 5] as attemptCount}
                      <option value={attemptCount}>{attemptCount}</option>
                    {/each}
                  </select>
                </label>
              {/if}
            </div>
          {/if}

          {#if saveError}
            <div role="alert" class="mx-auto mt-5 flex max-w-2xl items-start gap-3 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-900 dark:bg-red-950/30 dark:text-red-300">
              <XCircle class="mt-0.5 h-4 w-4 shrink-0" />
              <div class="min-w-0 flex-1">
                <p>{saveError}</p>
                {#if parentRefreshFailed}
                  <button
                    type="button"
                    onclick={retryParentRefresh}
                    disabled={refreshingParent}
                    class="mt-2 inline-flex min-h-9 items-center justify-center gap-2 rounded-lg border border-red-300 bg-background px-3 py-1.5 text-xs font-semibold text-red-700 transition-colors hover:bg-red-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-500/40 disabled:opacity-50 dark:border-red-800 dark:text-red-300 dark:hover:bg-red-950"
                  >
                    {#if refreshingParent}
                      <Loader2 class="h-3.5 w-3.5 animate-spin" />
                    {/if}
                    Retry refresh
                  </button>
                {/if}
              </div>
            </div>
          {/if}
        </div>

        <footer class="shrink-0 border-t border-border bg-background/95 px-5 py-4 backdrop-blur sm:px-6">
          {#if activeTab === 'credentials'}
            <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <p class="text-xs text-muted-foreground">
                Credential changes are saved immediately.
              </p>
              <button
                onclick={closeModal}
                class="inline-flex min-h-11 items-center justify-center rounded-lg bg-primary px-4 py-2.5 text-sm font-semibold text-primary-foreground hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
              >
                {footerActionForTab('credentials')}
              </button>
            </div>
          {:else if activeTab === 'routing'}
            <div class="flex flex-col-reverse gap-2 sm:flex-row sm:items-center sm:justify-between">
              <button
                onclick={closeModal}
                disabled={savingRouting}
                class="inline-flex min-h-11 items-center justify-center rounded-lg border border-border px-4 py-2.5 text-sm font-medium hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onclick={handleSaveRouting}
                disabled={savingRouting || !routingDirty || (routingStrategy !== 'manual' && !automaticRoutingAvailable)}
                class="inline-flex min-h-11 items-center justify-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-sm font-semibold text-primary-foreground hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {#if savingRouting}
                  <Loader2 class="h-4 w-4 animate-spin" />
                {/if}
                {footerActionForTab('routing')}
              </button>
            </div>
          {:else}
            <div class="flex flex-col-reverse gap-2 sm:flex-row sm:items-center sm:justify-between">
              <button
                onclick={closeModal}
                disabled={saving !== null || testing}
                class="inline-flex min-h-11 items-center justify-center rounded-lg border border-border px-4 py-2.5 text-sm font-medium transition-colors hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 disabled:opacity-50"
              >
                Cancel
              </button>
              <div class="flex flex-col-reverse gap-2 sm:flex-row">
                {#if !isActive}
                  <button
                    onclick={() => handleSave(false)}
                    disabled={saving !== null || testing || !canSave}
                    class="inline-flex min-h-11 items-center justify-center gap-2 rounded-lg border border-border px-4 py-2.5 text-sm font-semibold transition-colors hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 disabled:cursor-not-allowed disabled:opacity-50"
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
                  class="inline-flex min-h-11 items-center justify-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-sm font-semibold text-primary-foreground shadow-sm transition-colors hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {#if saving === 'activate'}
                    <Loader2 class="h-4 w-4 animate-spin" />
                  {/if}
                  {isActive ? footerActionForTab('model') : primaryLabel}
                </button>
              </div>
            </div>
          {/if}
        </footer>
      {/if}
    </div>
  </div>
{/if}

<style>
  .panel-overlay {
    animation: overlay-in 180ms ease-out;
  }

  .provider-panel {
    animation: panel-in 220ms cubic-bezier(0.22, 1, 0.36, 1);
  }

  @keyframes overlay-in {
    from { background-color: rgb(0 0 0 / 0%); }
  }

  @keyframes panel-in {
    from { transform: translateX(100%); }
  }

  @media (prefers-reduced-motion: reduce) {
    .panel-overlay,
    .provider-panel {
      animation: none;
    }
  }
</style>
