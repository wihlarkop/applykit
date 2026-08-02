<script lang="ts">
  import { invalidateAll } from '$app/navigation';
  import { testConnection, updateSettings } from '$lib/api';
  import ModelSelector from '$lib/components/ModelSelector.svelte';
  import type { CatalogModelOption } from '$lib/llm-catalog';
  import {
    DEFAULT_OLLAMA_BASE_URL,
    normalizeOllamaBaseUrl,
    ollamaBaseUrlError,
  } from '$lib/settings-modal';
  import { toastState } from '$lib/toast.svelte';
  import type { TestConnectionResponse } from '$lib/types';
  import { Activity, CheckCircle, Loader2, Server, X, XCircle } from '@lucide/svelte';

  let {
    open = $bindable(false),
    initialModel = '',
    initialBaseUrl = DEFAULT_OLLAMA_BASE_URL,
    isActive = false,
    models = [],
    onsaved = async () => undefined,
  }: {
    open: boolean;
    initialModel?: string;
    initialBaseUrl?: string;
    isActive?: boolean;
    models?: CatalogModelOption[];
    onsaved?: () => Promise<void> | void;
  } = $props();

  let model = $state('');
  let baseUrl = $state(DEFAULT_OLLAMA_BASE_URL);
  let testing = $state(false);
  let saving = $state<'only' | 'activate' | null>(null);
  let testResult: TestConnectionResponse | null = $state(null);
  let saveError = $state('');

  const baseUrlError = $derived(ollamaBaseUrlError(baseUrl));
  const canSubmit = $derived(Boolean(model && !baseUrlError));

  $effect(() => {
    if (!open) return;
    model = initialModel || models[0]?.value || '';
    baseUrl = initialBaseUrl || DEFAULT_OLLAMA_BASE_URL;
    testResult = null;
    saveError = '';
  });

  function closeModal() {
    if (testing || saving) return;
    open = false;
  }

  async function handleTest() {
    if (!canSubmit) return;
    testing = true;
    testResult = null;
    saveError = '';
    try {
      testResult = await testConnection({
        model,
        api_key: null,
        activate: false,
        base_url: normalizeOllamaBaseUrl(baseUrl),
      });
    } catch {
      testResult = { ok: false, message: 'Connection test request failed.' };
    } finally {
      testing = false;
    }
  }

  async function handleSave(activate: boolean) {
    if (!canSubmit) return;
    saving = activate ? 'activate' : 'only';
    saveError = '';
    try {
      await updateSettings({
        model,
        api_key: null,
        activate,
        base_url: normalizeOllamaBaseUrl(baseUrl),
      });
      await onsaved();
      await invalidateAll();
      toastState.success(
        activate
          ? isActive
            ? 'Ollama settings updated.'
            : 'Ollama saved and set as active.'
          : 'Ollama settings saved.',
      );
      open = false;
    } catch {
      saveError = 'Failed to save Ollama settings.';
    } finally {
      saving = null;
    }
  }
</script>

{#if open}
  <div
    class="fixed inset-0 z-[70] flex items-center justify-center bg-black/55 p-4"
    role="presentation"
    onclick={(event) => event.target === event.currentTarget && closeModal()}
  >
    <section
      class="w-full max-w-xl overflow-hidden rounded-2xl border border-border bg-background shadow-2xl"
      role="dialog"
      aria-modal="true"
      aria-labelledby="ollama-settings-title"
    >
      <header class="flex items-start justify-between gap-4 border-b border-border px-5 py-4">
        <div class="flex items-start gap-3">
          <div class="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10 text-primary">
            <Server class="h-5 w-5" />
          </div>
          <div>
            <h2 id="ollama-settings-title" class="text-lg font-semibold">Ollama settings</h2>
            <p class="mt-1 text-sm text-muted-foreground">Choose a model and the Ollama server ApplyKit should use.</p>
          </div>
        </div>
        <button
          type="button"
          onclick={closeModal}
          disabled={testing || saving !== null}
          class="flex h-9 w-9 items-center justify-center rounded-lg text-muted-foreground hover:bg-accent hover:text-foreground disabled:opacity-50"
          aria-label="Close Ollama settings"
        >
          <X class="h-4 w-4" />
        </button>
      </header>

      <div class="space-y-6 px-5 py-5">
        <section>
          <label class="text-sm font-semibold" for="ollama-model">Model</label>
          <p class="mt-1 text-xs text-muted-foreground">The model must already be available on the configured Ollama server.</p>
          <div class="mt-3" id="ollama-model">
            <ModelSelector {models} bind:value={model} />
          </div>
        </section>

        <section>
          <label class="text-sm font-semibold" for="ollama-base-url">Ollama Base URL</label>
          <p class="mt-1 text-xs text-muted-foreground">Enter the server root, for example <code>http://localhost:11434</code>. Do not append <code>/v1</code>.</p>
          <input
            id="ollama-base-url"
            bind:value={baseUrl}
            onblur={() => (baseUrl = normalizeOllamaBaseUrl(baseUrl))}
            placeholder={DEFAULT_OLLAMA_BASE_URL}
            spellcheck="false"
            autocomplete="url"
            class="mt-3 w-full rounded-xl border border-border bg-background px-3 py-3 font-mono text-sm outline-none focus:ring-2 focus:ring-primary/30"
          />
          {#if baseUrlError}
            <p class="mt-2 text-xs text-red-600 dark:text-red-400">{baseUrlError}</p>
          {/if}
        </section>

        <section class="rounded-xl border border-border bg-muted/20 p-4">
          <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p class="text-sm font-semibold">Verify this endpoint</p>
              <p class="mt-1 text-xs text-muted-foreground">Sends one minimal request using the model and Base URL above.</p>
            </div>
            <button
              type="button"
              onclick={handleTest}
              disabled={testing || !canSubmit}
              class="inline-flex items-center justify-center gap-2 rounded-lg border border-border bg-background px-3 py-2 text-sm font-medium hover:bg-accent disabled:opacity-50"
            >
              {#if testing}<Loader2 class="h-4 w-4 animate-spin" /> Testing…{:else}<Activity class="h-4 w-4" /> Test connection{/if}
            </button>
          </div>
          {#if testResult}
            <div class="mt-3 flex items-start gap-2 text-sm {testResult.ok ? 'text-green-700 dark:text-green-300' : 'text-red-700 dark:text-red-300'}">
              {#if testResult.ok}<CheckCircle class="mt-0.5 h-4 w-4 shrink-0" />{:else}<XCircle class="mt-0.5 h-4 w-4 shrink-0" />{/if}
              <span>{testResult.message}</span>
            </div>
          {/if}
        </section>

        {#if saveError}<p class="text-sm text-red-600 dark:text-red-400">{saveError}</p>{/if}
      </div>

      <footer class="flex flex-col-reverse gap-2 border-t border-border px-5 py-4 sm:flex-row sm:justify-end">
        <button type="button" onclick={closeModal} disabled={testing || saving !== null} class="rounded-lg border border-border px-4 py-2 text-sm font-medium hover:bg-accent disabled:opacity-50">Cancel</button>
        <button type="button" onclick={() => handleSave(false)} disabled={!canSubmit || saving !== null} class="rounded-lg border border-border px-4 py-2 text-sm font-medium hover:bg-accent disabled:opacity-50">{saving === 'only' ? 'Saving…' : 'Save'}</button>
        <button type="button" onclick={() => handleSave(true)} disabled={!canSubmit || saving !== null} class="rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground hover:bg-primary/90 disabled:opacity-50">{saving === 'activate' ? 'Saving…' : isActive ? 'Save changes' : 'Save & set active'}</button>
      </footer>
    </section>
  </div>
{/if}
