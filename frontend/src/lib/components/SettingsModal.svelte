<script lang="ts">
  import { goto, invalidateAll } from '$app/navigation';
  import { page } from '$app/state';
  import { getModels, getSettings, testConnection, updateSettings } from '$lib/api';
  import {
    credentialActionLabel,
    customModelValidationError,
    isCustomModel,
    type CatalogProviderInfo,
  } from '$lib/llm-catalog';
  import { toastState } from '$lib/toast.svelte';
  import type { TestConnectionResponse } from '$lib/types';
  import { errorMessage } from '$lib/utils';
  import { CheckCircle, CircleAlert, ExternalLink, Eye, EyeOff, Loader2, XCircle } from '@lucide/svelte';
  import ModelSelector from '$lib/components/ModelSelector.svelte';

  let { open = $bindable(false), initialProviderId = '', initialModel = '', initialApiKeyConfigured = false }: {
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

  const selectedProvider = $derived(providers.find((p) => p.id === selectedProviderId));
  const selectedModelInfo = $derived(selectedProvider?.models.find((model) => model.value === selectedModel));
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
    Boolean(initialProviderId && initialApiKeyConfigured && selectedProvider?.requires_api_key),
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
      const [modelsRes, settingsRes] = await Promise.all([getModels(), getSettings()]);
      providers = modelsRes.providers as CatalogProviderInfo[];
      source = settingsRes.source;

      if (initialProviderId) {
        const provider = providers.find((item) => item.id === initialProviderId);
        selectedProviderId = initialProviderId;
        selectedModel = initialModel || provider?.models[0]?.value || '';
        customMode = isCustomModel(provider, selectedModel);
      } else if (settingsRes.model && selectExistingModel(settingsRes.model)) {
        // Selection was restored from saved settings.
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
    if (!selectedModel || customModelError) return;
    const keyToTest = apiKey.trim() || null;
    if (selectedProvider?.requires_api_key && !keyToTest) return;
    testing = true;
    testResult = null;
    try {
      testResult = await testConnection({ model: selectedModel.trim(), api_key: keyToTest });
    } catch {
      testResult = { ok: false, message: 'Request failed.' };
    } finally {
      testing = false;
    }
  }

  let saving = $state<'activate' | 'key' | null>(null);

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
    saving = activate ? 'activate' : 'key';
    saveError = '';
    try {
      await updateSettings({ model: selectedModel.trim(), api_key: keyToSave, activate });
      toastState.success(
        activate
          ? 'Saved and set as active model.'
          : keyToSave
            ? 'API key saved.'
            : 'Model saved. Existing API key was kept.',
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

  function handleKeydown(event: KeyboardEvent) {
    if (event.key === 'Escape') open = false;
  }
</script>

<svelte:window onkeydown={handleKeydown} />

{#if open}
  <div
    class="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4"
    onclick={() => (open = false)}
    onkeydown={(event) => event.key === 'Escape' && (open = false)}
    role="dialog"
    tabindex="-1"
    aria-modal="true"
    aria-label="LLM Settings"
  >
    <div
      class="bg-background border border-border rounded-lg shadow-xl w-full max-w-md p-6 space-y-5"
      onclick={(event) => event.stopPropagation()}
      role="presentation"
    >
      <div class="flex items-center justify-between">
        <h2 class="text-lg font-semibold">{initialProviderId && selectedProvider ? selectedProvider.label : 'LLM Settings'}</h2>
        <button onclick={() => (open = false)} class="text-muted-foreground hover:text-foreground text-lg leading-none" aria-label="Close">✕</button>
      </div>

      {#if loading}
        <div class="flex items-center justify-center py-8 text-muted-foreground gap-2">
          <Loader2 class="w-5 h-5 animate-spin" />
          Loading…
        </div>
      {:else}
        {#if source === 'env'}
          <p class="text-xs text-muted-foreground bg-muted rounded px-2 py-1.5">
            Currently using config from <code class="font-mono">.env</code> file. Saving here will override it.
          </p>
        {/if}

        {#if !initialProviderId}
          <div class="space-y-1.5">
            <p class="text-sm font-medium">Provider</p>
            <div class="flex flex-wrap gap-2">
              {#each providers as provider}
                <button
                  onclick={() => onProviderChange(provider.id)}
                  class="px-3 py-1.5 rounded-md text-sm border transition-colors {selectedProviderId === provider.id
                    ? 'bg-primary text-primary-foreground border-primary'
                    : 'border-border hover:bg-accent'}"
                >{provider.label}</button>
              {/each}
            </div>
          </div>
        {:else}
          <p class="text-sm font-medium">{selectedProvider?.label}</p>
        {/if}

        <div class="space-y-1.5">
          <div class="flex items-center justify-between gap-3">
            <label for={customMode ? 'custom-model-input' : undefined} class="text-sm font-medium">Model</label>
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

          {#if customMode}
            <input
              id="custom-model-input"
              bind:value={selectedModel}
              placeholder={`${selectedProvider?.id ?? 'provider'}/model-name`}
              maxlength="200"
              spellcheck="false"
              autocomplete="off"
              class="w-full rounded-md border border-border bg-background px-3 py-2 font-mono text-sm outline-none focus:ring-2 focus:ring-primary/30"
            />
            <div class="flex items-center justify-between gap-3">
              <span class="rounded bg-purple-100 px-1.5 py-0.5 text-[10px] font-semibold uppercase text-purple-800 dark:bg-purple-950 dark:text-purple-300">Custom</span>
              <span class="text-[11px] text-muted-foreground">Use the full LiteLLM model ID.</span>
            </div>
            {#if customModelError}
              <p class="text-xs text-red-600 dark:text-red-400">{customModelError}</p>
            {/if}
          {:else}
            <ModelSelector
              models={selectedProvider?.models ?? []}
              bind:value={selectedModel}
              unavailableValue={unavailableCurrentModel ? initialModel : ''}
            />
          {/if}

          {#if unavailableCurrentModel && selectedModel === initialModel}
            <div class="flex items-start gap-2 rounded-md border border-yellow-200 bg-yellow-50 px-3 py-2 text-xs text-yellow-800 dark:border-yellow-900 dark:bg-yellow-950/30 dark:text-yellow-300">
              <CircleAlert class="w-4 h-4 shrink-0" />
              <span>This model is no longer included in this ApplyKit release. Select an active model to replace it.</span>
            </div>
          {:else if selectedModelInfo}
            <div class="flex flex-wrap gap-1.5 pt-0.5">
              {#if selectedModelInfo.status !== 'stable'}
                <span class="rounded bg-yellow-100 px-1.5 py-0.5 text-[10px] font-semibold uppercase text-yellow-800 dark:bg-yellow-950 dark:text-yellow-300">{selectedModelInfo.status}</span>
              {/if}
              {#if selectedModelInfo.free_tier}
                <span class="rounded bg-green-100 px-1.5 py-0.5 text-[10px] font-semibold uppercase text-green-800 dark:bg-green-950 dark:text-green-300">Free tier</span>
              {/if}
              {#if selectedProvider?.local}
                <span class="rounded bg-blue-100 px-1.5 py-0.5 text-[10px] font-semibold uppercase text-blue-800 dark:bg-blue-950 dark:text-blue-300">Local</span>
              {/if}
              {#each selectedModelInfo.traits as trait}
                <span class="rounded bg-muted px-1.5 py-0.5 text-[10px] uppercase text-muted-foreground">{trait.replaceAll('_', ' ')}</span>
              {/each}
            </div>
          {/if}
        </div>

        {#if selectedProvider?.requires_api_key}
          <div class="space-y-1.5">
            <div class="flex items-center justify-between gap-3">
              <label for="api-key-input" class="text-sm font-medium">{selectedProvider.auth_type === 'token' ? 'Access Token' : 'API Key'}</label>
              {#if selectedProvider.credential_url}
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
            <div class="relative">
              <input
                id="api-key-input"
                type={showApiKey ? 'text' : 'password'}
                bind:value={apiKey}
                placeholder={canReuseStoredKey ? 'Leave blank to keep the current credential' : 'Enter your credential…'}
                class="w-full border border-border rounded-md px-3 py-2 pr-10 text-sm bg-background"
                autocomplete="new-password"
              />
              <button type="button" onclick={() => (showApiKey = !showApiKey)} class="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground" aria-label={showApiKey ? 'Hide credential' : 'Show credential'}>
                {#if showApiKey}<EyeOff class="w-4 h-4" />{:else}<Eye class="w-4 h-4" />{/if}
              </button>
            </div>
            {#if canReuseStoredKey}
              <p class="text-xs text-muted-foreground">A credential is already configured. Enter a new value only to replace it.</p>
            {/if}
          </div>
        {:else}
          <p class="text-sm text-muted-foreground">This provider runs locally and does not require an API key.</p>
        {/if}

        <div class="space-y-2">
          <button
            onclick={handleTest}
            disabled={testing || !selectedModel || Boolean(customModelError) || (selectedProvider?.requires_api_key && !apiKey)}
            class="w-full px-4 py-2 rounded-md border border-border text-sm hover:bg-accent disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
          >
            {#if testing}<Loader2 class="w-4 h-4 animate-spin" />Testing…{:else}Test Connection{/if}
          </button>

          {#if testResult}
            <div class="flex items-start gap-2 text-sm {testResult.ok ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}">
              {#if testResult.ok}<CheckCircle class="w-4 h-4 shrink-0 mt-0.5" />{:else}<XCircle class="w-4 h-4 shrink-0 mt-0.5" />{/if}
              <span>{testResult.message}</span>
            </div>
          {/if}
        </div>

        {#if saveError}<p class="text-sm text-red-600">{saveError}</p>{/if}

        <div class="flex justify-end gap-2 pt-1 flex-wrap">
          <button onclick={() => (open = false)} class="px-4 py-2 rounded-md text-sm border border-border hover:bg-accent">Cancel</button>
          {#if initialProviderId && selectedProvider?.requires_api_key}
            <button
              onclick={() => handleSave(false)}
              disabled={saving !== null || !selectedModel || Boolean(customModelError) || (!apiKey && !canReuseStoredKey)}
              class="px-4 py-2 rounded-md text-sm border border-border hover:bg-accent disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {#if saving === 'key'}<Loader2 class="w-4 h-4 animate-spin" />{/if}
              {apiKey ? 'Save Credential' : 'Save Model'}
            </button>
          {/if}
          <button
            onclick={() => handleSave(true)}
            disabled={saving !== null || !selectedModel || Boolean(customModelError) || (selectedProvider?.requires_api_key && !apiKey && !canReuseStoredKey)}
            class="px-4 py-2 rounded-md text-sm bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            {#if saving === 'activate'}<Loader2 class="w-4 h-4 animate-spin" />{/if}
            {initialProviderId ? 'Save & Set Active' : 'Save'}
          </button>
        </div>
      {/if}
    </div>
  </div>
{/if}
