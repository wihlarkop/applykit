<script lang="ts">
  import { Eye, EyeOff, CheckCircle, XCircle, Loader2 } from '@lucide/svelte';
  import { getSettings, updateSettings, testConnection, getModels } from '$lib/api';
  import { settingsStore } from '$lib/settingsStore.svelte';
  import { toastState } from '$lib/toast.svelte';
  import type { ProviderInfo, TestConnectionResponse } from '$lib/types';

  let { open = $bindable(false) }: { open: boolean } = $props();

  let providers: ProviderInfo[] = $state([]);
  let selectedProviderId = $state('gemini');
  let selectedModel = $state('');
  let apiKey = $state('');
  let showApiKey = $state(false);
  let loading = $state(true);
  let saving = $state(false);
  let testing = $state(false);
  let testResult: TestConnectionResponse | null = $state(null);
  let saveError = $state('');
  let source = $state<'database' | 'env' | 'none'>('none');

  const selectedProvider = $derived(providers.find((p) => p.id === selectedProviderId));

  $effect(() => {
    if (!open) return;
    loadData();
  });

  async function loadData() {
    loading = true;
    testResult = null;
    saveError = '';
    try {
      const [modelsRes, settingsRes] = await Promise.all([getModels(), getSettings()]);
      providers = modelsRes.providers;
      source = settingsRes.source;

      if (settingsRes.model) {
        // Find which provider owns this model string
        for (const p of providers) {
          if (p.models.some((m) => m.value === settingsRes.model)) {
            selectedProviderId = p.id;
            selectedModel = settingsRes.model;
            break;
          }
        }
      } else if (providers.length > 0) {
        selectedProviderId = providers[0].id;
        selectedModel = providers[0].models[0]?.value ?? '';
      }
      // Don't pre-fill API key for security — user must re-enter to change
    } catch {
      saveError = 'Failed to load settings.';
    } finally {
      loading = false;
    }
  }

  function onProviderChange(id: string) {
    selectedProviderId = id;
    const prov = providers.find((p) => p.id === id);
    selectedModel = prov?.models[0]?.value ?? '';
    // Ollama needs no key; set a placeholder so the backend validation passes
    apiKey = id === 'ollama' ? 'ollama' : '';
    testResult = null;
  }

  async function handleTest() {
    if (!selectedModel) return;
    const keyToTest = selectedProvider?.requires_api_key ? apiKey : 'ollama';
    if (selectedProvider?.requires_api_key && !keyToTest) return;
    testing = true;
    testResult = null;
    try {
      testResult = await testConnection({ model: selectedModel, api_key: keyToTest });
    } catch {
      testResult = { ok: false, message: 'Request failed.' };
    } finally {
      testing = false;
    }
  }

  async function handleSave() {
    if (!selectedModel) {
      saveError = 'Select a model.';
      return;
    }
    const keyToSave = selectedProvider?.requires_api_key ? apiKey : 'ollama';
    if (selectedProvider?.requires_api_key && !keyToSave) {
      saveError = 'API key is required.';
      return;
    }
    saving = true;
    saveError = '';
    try {
      await updateSettings({ model: selectedModel, api_key: keyToSave });
      settingsStore.notify();
      toastState.success('Settings saved successfully.');
      open = false;
    } catch (e: any) {
      saveError = e?.message ?? 'Failed to save settings.';
    } finally {
      saving = false;
    }
  }

  function handleKeydown(e: KeyboardEvent) {
    if (e.key === 'Escape') open = false;
  }
</script>

<svelte:window onkeydown={handleKeydown} />

{#if open}
  <div
    class="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4"
    onclick={() => (open = false)}
    role="dialog"
    aria-modal="true"
    aria-label="LLM Settings"
  >
    <div
      class="bg-background border border-border rounded-lg shadow-xl w-full max-w-md p-6 space-y-5"
      onclick={(e) => e.stopPropagation()}
      role="presentation"
    >
      <div class="flex items-center justify-between">
        <h2 class="text-lg font-semibold">LLM Settings</h2>
        <button
          onclick={() => (open = false)}
          class="text-muted-foreground hover:text-foreground text-lg leading-none"
          aria-label="Close"
        >✕</button>
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

        <!-- Provider tabs -->
        <div class="space-y-1.5">
          <p class="text-sm font-medium">Provider</p>
          <div class="flex flex-wrap gap-2">
            {#each providers as p}
              <button
                onclick={() => onProviderChange(p.id)}
                class="px-3 py-1.5 rounded-md text-sm border transition-colors {selectedProviderId === p.id
                  ? 'bg-primary text-primary-foreground border-primary'
                  : 'border-border hover:bg-accent'}"
              >
                {p.label}
              </button>
            {/each}
          </div>
        </div>

        <!-- Model dropdown -->
        <div class="space-y-1.5">
          <label for="model-select" class="text-sm font-medium">Model</label>
          <select
            id="model-select"
            bind:value={selectedModel}
            class="w-full border border-border rounded-md px-3 py-2 text-sm bg-background"
          >
            {#each selectedProvider?.models ?? [] as m}
              <option value={m.value}>{m.label}</option>
            {/each}
          </select>
        </div>

        <!-- API key -->
        {#if selectedProvider?.requires_api_key}
          <div class="space-y-1.5">
            <label for="api-key-input" class="text-sm font-medium">API Key</label>
            <div class="relative">
              <input
                id="api-key-input"
                type={showApiKey ? 'text' : 'password'}
                bind:value={apiKey}
                placeholder="Enter your API key…"
                class="w-full border border-border rounded-md px-3 py-2 pr-10 text-sm bg-background"
                autocomplete="off"
              />
              <button
                type="button"
                onclick={() => (showApiKey = !showApiKey)}
                class="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                aria-label={showApiKey ? 'Hide API key' : 'Show API key'}
              >
                {#if showApiKey}
                  <EyeOff class="w-4 h-4" />
                {:else}
                  <Eye class="w-4 h-4" />
                {/if}
              </button>
            </div>
          </div>
        {:else}
          <p class="text-sm text-muted-foreground">
            Ollama runs locally — no API key required. Make sure Ollama is running on port 11434.
          </p>
        {/if}

        <!-- Test connection -->
        <div class="space-y-2">
          <button
            onclick={handleTest}
            disabled={testing || !selectedModel || (selectedProvider?.requires_api_key && !apiKey)}
            class="w-full px-4 py-2 rounded-md border border-border text-sm hover:bg-accent disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
          >
            {#if testing}
              <Loader2 class="w-4 h-4 animate-spin" />
              Testing…
            {:else}
              Test Connection
            {/if}
          </button>

          {#if testResult}
            <div class="flex items-start gap-2 text-sm {testResult.ok ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}">
              {#if testResult.ok}
                <CheckCircle class="w-4 h-4 shrink-0 mt-0.5" />
              {:else}
                <XCircle class="w-4 h-4 shrink-0 mt-0.5" />
              {/if}
              <span>{testResult.message}</span>
            </div>
          {/if}
        </div>

        {#if saveError}
          <p class="text-sm text-red-600">{saveError}</p>
        {/if}

        <!-- Actions -->
        <div class="flex justify-end gap-3 pt-1">
          <button
            onclick={() => (open = false)}
            class="px-4 py-2 rounded-md text-sm border border-border hover:bg-accent"
          >
            Cancel
          </button>
          <button
            onclick={handleSave}
            disabled={saving || !selectedModel || (selectedProvider?.requires_api_key && !apiKey)}
            class="px-4 py-2 rounded-md text-sm bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            {#if saving}<Loader2 class="w-4 h-4 animate-spin" />{/if}
            Save
          </button>
        </div>
      {/if}
    </div>
  </div>
{/if}
