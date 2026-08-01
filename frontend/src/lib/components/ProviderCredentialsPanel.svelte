<script lang="ts">
  import {
    activateProviderCredential,
    addProviderCredential,
    deleteProviderCredential,
    getCredentialPolicy,
    getProviderCredentials,
    testProviderCredential,
    updateCredentialPolicy,
    updateProviderCredential,
  } from '$lib/integration-api';
  import {
    canUseAutomaticStrategy,
    credentialHealthLabel,
    credentialHealthTone,
    credentialStrategyDescription,
    credentialStrategyLabel,
  } from '$lib/provider-credentials';
  import type {
    CredentialPolicyResponse,
    CredentialStrategy,
    ProviderCredentialInfo,
  } from '$lib/provider-credential-types';
  import type { TestConnectionResponse } from '$lib/types';
  import { errorMessage } from '$lib/utils';
  import {
    Activity,
    Check,
    ChevronDown,
    CircleAlert,
    CircleCheck,
    ExternalLink,
    Eye,
    EyeOff,
    KeyRound,
    Loader2,
    Pencil,
    Plus,
    RefreshCw,
    ShieldCheck,
    Trash2,
    X,
  } from '@lucide/svelte';

  let {
    providerId,
    providerLabel,
    credentialUrl = null,
    authType = 'api_key',
    onChanged,
  }: {
    providerId: string;
    providerLabel: string;
    credentialUrl?: string | null;
    authType?: string;
    onChanged?: () => void | Promise<void>;
  } = $props();

  type EditMode = 'rename' | 'replace' | 'remove' | null;

  let credentials: ProviderCredentialInfo[] = $state([]);
  let policy: CredentialPolicyResponse = $state({
    provider_id: '',
    strategy: 'manual',
    max_attempts: 2,
  });
  let maxCredentials = $state(20);
  let loading = $state(true);
  let panelError = $state('');
  let operation = $state('');
  let addOpen = $state(false);
  let newLabel = $state('');
  let newSecret = $state('');
  let newSecretVisible = $state(false);
  let activateNew = $state(false);
  let editingId: number | null = $state(null);
  let editMode: EditMode = $state(null);
  let editValue = $state('');
  let editSecretVisible = $state(false);
  let testResults: Record<number, TestConnectionResponse> = $state({});

  const automaticAvailable = $derived(canUseAutomaticStrategy(credentials));
  const enabledCount = $derived(
    credentials.filter((credential) => credential.is_enabled).length,
  );

  $effect(() => {
    if (!providerId) return;
    loadData();
  });

  async function loadData() {
    loading = true;
    panelError = '';
    closeEditor();
    try {
      const [credentialsResponse, policyResponse] = await Promise.all([
        getProviderCredentials(providerId),
        getCredentialPolicy(providerId),
      ]);
      credentials = credentialsResponse.credentials;
      maxCredentials = credentialsResponse.max_credentials;
      policy = policyResponse;
    } catch (error) {
      panelError = errorMessage(error, 'Failed to load provider credentials.');
    } finally {
      loading = false;
    }
  }

  async function notifyChanged() {
    await onChanged?.();
  }

  function closeEditor() {
    editingId = null;
    editMode = null;
    editValue = '';
    editSecretVisible = false;
  }

  function beginEdit(credential: ProviderCredentialInfo, mode: Exclude<EditMode, null>) {
    editingId = credential.id;
    editMode = mode;
    editValue = mode === 'rename' ? credential.label : '';
    editSecretVisible = false;
    panelError = '';
  }

  async function handleAdd() {
    const label = newLabel.trim();
    const secret = newSecret.trim();
    if (!label || !secret) {
      panelError = 'Enter a label and credential.';
      return;
    }

    operation = 'add';
    panelError = '';
    try {
      await addProviderCredential(providerId, {
        label,
        secret,
        activate: credentials.length === 0 || activateNew,
      });
      newLabel = '';
      activateNew = false;
      addOpen = false;
      await loadData();
      await notifyChanged();
    } catch (error) {
      panelError = errorMessage(error, 'Failed to add credential.');
    } finally {
      newSecret = '';
      newSecretVisible = false;
      operation = '';
    }
  }

  async function handleEdit(credential: ProviderCredentialInfo) {
    if (!editMode || editMode === 'remove') return;
    const value = editValue.trim();
    if (!value) {
      panelError = editMode === 'rename' ? 'Enter a credential label.' : 'Enter a replacement credential.';
      return;
    }

    operation = `${editMode}:${credential.id}`;
    panelError = '';
    try {
      await updateProviderCredential(
        providerId,
        credential.id,
        editMode === 'rename' ? { label: value } : { secret: value },
      );
      closeEditor();
      await loadData();
      await notifyChanged();
    } catch (error) {
      panelError = errorMessage(error, 'Failed to update credential.');
    } finally {
      if (editMode === 'replace') editValue = '';
      editSecretVisible = false;
      operation = '';
    }
  }

  async function handleActivate(credential: ProviderCredentialInfo) {
    operation = `activate:${credential.id}`;
    panelError = '';
    try {
      await activateProviderCredential(providerId, credential.id);
      await loadData();
      await notifyChanged();
    } catch (error) {
      panelError = errorMessage(error, 'Failed to activate credential.');
    } finally {
      operation = '';
    }
  }

  async function handleTest(credential: ProviderCredentialInfo) {
    operation = `test:${credential.id}`;
    panelError = '';
    const nextResults = { ...testResults };
    delete nextResults[credential.id];
    testResults = nextResults;
    try {
      const result = await testProviderCredential(providerId, credential.id);
      testResults = { ...testResults, [credential.id]: result };
      await loadData();
      await notifyChanged();
    } catch (error) {
      testResults = {
        ...testResults,
        [credential.id]: {
          ok: false,
          message: errorMessage(error, 'Credential test failed.'),
        },
      };
    } finally {
      operation = '';
    }
  }

  async function handleRemove(credential: ProviderCredentialInfo) {
    operation = `remove:${credential.id}`;
    panelError = '';
    try {
      const response = await deleteProviderCredential(providerId, credential.id);
      credentials = response.credentials;
      maxCredentials = response.max_credentials;
      closeEditor();
      const nextResults = { ...testResults };
      delete nextResults[credential.id];
      testResults = nextResults;

      if (!canUseAutomaticStrategy(credentials) && policy.strategy !== 'manual') {
        policy = await updateCredentialPolicy(providerId, 'manual', 2);
      }
      await notifyChanged();
    } catch (error) {
      panelError = errorMessage(error, 'Failed to remove credential.');
    } finally {
      operation = '';
    }
  }

  async function handleStrategy(strategy: CredentialStrategy) {
    if (strategy !== 'manual' && !automaticAvailable) return;
    operation = 'policy';
    panelError = '';
    try {
      policy = await updateCredentialPolicy(
        providerId,
        strategy,
        strategy === 'manual' ? 2 : policy.max_attempts,
      );
      await notifyChanged();
    } catch (error) {
      panelError = errorMessage(error, 'Failed to update credential strategy.');
    } finally {
      operation = '';
    }
  }

  async function handleMaxAttempts(value: number) {
    if (policy.strategy === 'manual') return;
    operation = 'policy';
    panelError = '';
    try {
      policy = await updateCredentialPolicy(providerId, policy.strategy, value);
      await notifyChanged();
    } catch (error) {
      panelError = errorMessage(error, 'Failed to update retry limit.');
    } finally {
      operation = '';
    }
  }

  function toneClass(credential: ProviderCredentialInfo): string {
    const tone = credentialHealthTone(credential);
    if (tone === 'success') return 'bg-green-100 text-green-700 dark:bg-green-950/60 dark:text-green-300';
    if (tone === 'warning') return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-950/60 dark:text-yellow-300';
    if (tone === 'danger') return 'bg-red-100 text-red-700 dark:bg-red-950/60 dark:text-red-300';
    return 'bg-muted text-muted-foreground';
  }
</script>

<section class="rounded-xl border border-border bg-card p-4 sm:p-5">
  <div class="flex flex-wrap items-start justify-between gap-3">
    <div class="flex min-w-0 items-start gap-3">
      <div class="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
        <KeyRound class="h-4 w-4" />
      </div>
      <div>
        <p class="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">Credentials</p>
        <h3 class="mt-0.5 text-sm font-semibold">Manage access to {providerLabel}</h3>
        <p class="mt-1 text-xs text-muted-foreground">
          {credentials.length} of {maxCredentials} saved · {enabledCount} enabled
        </p>
      </div>
    </div>

    <div class="flex items-center gap-2">
      {#if credentialUrl}
        <a
          href={credentialUrl}
          target="_blank"
          rel="noopener noreferrer"
          class="inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline"
        >
          Get {authType === 'token' ? 'access token' : 'API key'}
          <ExternalLink class="h-3 w-3" />
        </a>
      {/if}
      <button
        type="button"
        onclick={() => (addOpen = !addOpen)}
        disabled={credentials.length >= maxCredentials || operation !== ''}
        class="inline-flex items-center gap-1.5 rounded-lg border border-border px-3 py-2 text-xs font-semibold hover:bg-accent disabled:opacity-50"
      >
        {#if addOpen}<X class="h-3.5 w-3.5" />Cancel{:else}<Plus class="h-3.5 w-3.5" />Add credential{/if}
      </button>
    </div>
  </div>

  {#if loading}
    <div class="mt-4 flex min-h-24 items-center justify-center gap-2 rounded-lg bg-muted/30 text-sm text-muted-foreground">
      <Loader2 class="h-4 w-4 animate-spin" />
      Loading credentials…
    </div>
  {:else}
    {#if addOpen}
      <div class="mt-4 rounded-lg border border-primary/20 bg-primary/5 p-3">
        <div class="grid gap-3 sm:grid-cols-[minmax(0,0.7fr)_minmax(0,1.3fr)]">
          <label class="space-y-1 text-xs font-medium">
            Label
            <input
              bind:value={newLabel}
              maxlength="80"
              placeholder="Personal, Work, Backup…"
              autocomplete="off"
              class="w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
            />
          </label>
          <label class="space-y-1 text-xs font-medium">
            {authType === 'token' ? 'Access token' : 'API key'}
            <div class="relative">
              <input
                type={newSecretVisible ? 'text' : 'password'}
                bind:value={newSecret}
                autocomplete="new-password"
                placeholder="Paste credential…"
                class="w-full rounded-md border border-border bg-background px-3 py-2 pr-10 text-sm"
              />
              <button
                type="button"
                onclick={() => (newSecretVisible = !newSecretVisible)}
                class="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                aria-label={newSecretVisible ? 'Hide credential' : 'Show credential'}
              >
                {#if newSecretVisible}<EyeOff class="h-4 w-4" />{:else}<Eye class="h-4 w-4" />{/if}
              </button>
            </div>
          </label>
        </div>
        {#if credentials.length > 0}
          <label class="mt-3 flex items-center gap-2 text-xs text-muted-foreground">
            <input type="checkbox" bind:checked={activateNew} class="h-4 w-4 rounded border-border" />
            Make this the active credential
          </label>
        {/if}
        <div class="mt-3 flex justify-end">
          <button
            type="button"
            onclick={handleAdd}
            disabled={operation !== '' || !newLabel.trim() || !newSecret.trim()}
            class="inline-flex items-center gap-1.5 rounded-md bg-primary px-3 py-2 text-xs font-semibold text-primary-foreground disabled:opacity-50"
          >
            {#if operation === 'add'}<Loader2 class="h-3.5 w-3.5 animate-spin" />{:else}<Plus class="h-3.5 w-3.5" />{/if}
            Save credential
          </button>
        </div>
      </div>
    {/if}

    {#if credentials.length > 0}
      <div class="mt-4 divide-y divide-border overflow-hidden rounded-lg border border-border">
        {#each credentials as credential}
          <article class="bg-background p-3">
            <div class="flex flex-col gap-3 sm:flex-row sm:items-center">
              <div class="min-w-0 flex-1">
                <div class="flex flex-wrap items-center gap-2">
                  <span class="text-sm font-semibold">{credential.label}</span>
                  {#if credential.is_active}
                    <span class="inline-flex items-center gap-1 rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-semibold uppercase text-primary">
                      <Check class="h-2.5 w-2.5" />Active
                    </span>
                  {/if}
                  <span class={`rounded px-1.5 py-0.5 text-[10px] font-semibold ${toneClass(credential)}`}>
                    {credentialHealthLabel(credential)}
                  </span>
                </div>
                <code class="mt-1 block break-all text-xs text-muted-foreground">{credential.masked_secret}</code>
                <p class="mt-1 text-[11px] text-muted-foreground">
                  Priority {credential.priority}
                  {#if credential.last_used_at} · Last used {new Date(credential.last_used_at).toLocaleString()}{/if}
                </p>
              </div>

              <div class="flex flex-wrap items-center gap-1.5">
                {#if !credential.is_active && credential.is_enabled}
                  <button
                    type="button"
                    onclick={() => handleActivate(credential)}
                    disabled={operation !== ''}
                    class="rounded-md border border-border px-2.5 py-1.5 text-xs font-medium hover:bg-accent disabled:opacity-50"
                  >
                    {operation === `activate:${credential.id}` ? 'Activating…' : 'Set active'}
                  </button>
                {/if}
                <button
                  type="button"
                  onclick={() => handleTest(credential)}
                  disabled={operation !== '' || !credential.is_enabled}
                  class="inline-flex items-center gap-1 rounded-md border border-border px-2.5 py-1.5 text-xs font-medium hover:bg-accent disabled:opacity-50"
                >
                  {#if operation === `test:${credential.id}`}<Loader2 class="h-3 w-3 animate-spin" />{:else}<Activity class="h-3 w-3" />{/if}
                  Test
                </button>
                <button type="button" onclick={() => beginEdit(credential, 'rename')} disabled={operation !== ''} class="rounded-md p-1.5 text-muted-foreground hover:bg-accent hover:text-foreground disabled:opacity-50" aria-label={`Rename ${credential.label}`}><Pencil class="h-3.5 w-3.5" /></button>
                <button type="button" onclick={() => beginEdit(credential, 'replace')} disabled={operation !== ''} class="rounded-md p-1.5 text-muted-foreground hover:bg-accent hover:text-foreground disabled:opacity-50" aria-label={`Replace ${credential.label}`}><RefreshCw class="h-3.5 w-3.5" /></button>
                <button type="button" onclick={() => beginEdit(credential, 'remove')} disabled={operation !== ''} class="rounded-md p-1.5 text-muted-foreground hover:bg-destructive/10 hover:text-destructive disabled:opacity-50" aria-label={`Remove ${credential.label}`}><Trash2 class="h-3.5 w-3.5" /></button>
              </div>
            </div>

            {#if testResults[credential.id]}
              <div class="mt-2 flex items-start gap-2 rounded-md px-2.5 py-2 text-xs {testResults[credential.id].ok ? 'bg-green-50 text-green-700 dark:bg-green-950/30 dark:text-green-300' : 'bg-red-50 text-red-700 dark:bg-red-950/30 dark:text-red-300'}">
                {#if testResults[credential.id].ok}<CircleCheck class="mt-0.5 h-3.5 w-3.5 shrink-0" />{:else}<CircleAlert class="mt-0.5 h-3.5 w-3.5 shrink-0" />{/if}
                {testResults[credential.id].message}
              </div>
            {/if}

            {#if editingId === credential.id}
              <div class="mt-3 rounded-md border border-border bg-muted/30 p-3">
                {#if editMode === 'remove'}
                  <p class="text-sm font-medium">Remove “{credential.label}”?</p>
                  <p class="mt-1 text-xs text-muted-foreground">
                    The secret cannot be recovered. {credential.is_active && credentials.length > 1 ? 'The next enabled credential becomes active.' : ''}
                  </p>
                  <div class="mt-3 flex justify-end gap-2">
                    <button type="button" onclick={closeEditor} class="rounded-md border border-border px-3 py-1.5 text-xs hover:bg-accent">Cancel</button>
                    <button type="button" onclick={() => handleRemove(credential)} disabled={operation !== ''} class="inline-flex items-center gap-1.5 rounded-md bg-destructive px-3 py-1.5 text-xs font-semibold text-destructive-foreground disabled:opacity-50">
                      {#if operation === `remove:${credential.id}`}<Loader2 class="h-3 w-3 animate-spin" />{:else}<Trash2 class="h-3 w-3" />{/if}
                      Remove
                    </button>
                  </div>
                {:else}
                  <label class="space-y-1 text-xs font-medium">
                    {editMode === 'rename' ? 'Credential label' : `New ${authType === 'token' ? 'access token' : 'API key'}`}
                    <div class="relative">
                      <input
                        type={editMode === 'replace' && !editSecretVisible ? 'password' : 'text'}
                        bind:value={editValue}
                        maxlength={editMode === 'rename' ? 80 : 4096}
                        autocomplete={editMode === 'replace' ? 'new-password' : 'off'}
                        class="w-full rounded-md border border-border bg-background px-3 py-2 {editMode === 'replace' ? 'pr-10' : ''} text-sm"
                      />
                      {#if editMode === 'replace'}
                        <button type="button" onclick={() => (editSecretVisible = !editSecretVisible)} class="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground" aria-label={editSecretVisible ? 'Hide credential' : 'Show credential'}>
                          {#if editSecretVisible}<EyeOff class="h-4 w-4" />{:else}<Eye class="h-4 w-4" />{/if}
                        </button>
                      {/if}
                    </div>
                  </label>
                  <div class="mt-3 flex justify-end gap-2">
                    <button type="button" onclick={closeEditor} class="rounded-md border border-border px-3 py-1.5 text-xs hover:bg-accent">Cancel</button>
                    <button type="button" onclick={() => handleEdit(credential)} disabled={operation !== '' || !editValue.trim()} class="inline-flex items-center gap-1.5 rounded-md bg-primary px-3 py-1.5 text-xs font-semibold text-primary-foreground disabled:opacity-50">
                      {#if operation === `${editMode}:${credential.id}`}<Loader2 class="h-3 w-3 animate-spin" />{:else}<Check class="h-3 w-3" />{/if}
                      Save
                    </button>
                  </div>
                {/if}
              </div>
            {/if}
          </article>
        {/each}
      </div>
    {:else}
      <div class="mt-4 rounded-lg border border-dashed border-border bg-muted/20 px-4 py-8 text-center">
        <KeyRound class="mx-auto h-5 w-5 text-muted-foreground" />
        <p class="mt-2 text-sm font-medium">No credentials saved</p>
        <p class="mt-1 text-xs text-muted-foreground">Add the first credential to connect this provider.</p>
      </div>
    {/if}

    <div class="mt-5 border-t border-border pt-5">
      <div class="flex items-start gap-3">
        <div class="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
          <ShieldCheck class="h-4 w-4" />
        </div>
        <div class="min-w-0 flex-1">
          <p class="text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">Credential strategy</p>
          <h3 class="mt-0.5 text-sm font-semibold">Choose how ApplyKit selects a key</h3>
        </div>
      </div>

      <div class="mt-3 grid gap-2">
        {#each ['manual', 'failover', 'round_robin'] as strategy}
          {@const typedStrategy = strategy as CredentialStrategy}
          {@const automatic = typedStrategy !== 'manual'}
          <button
            type="button"
            onclick={() => handleStrategy(typedStrategy)}
            disabled={operation !== '' || (automatic && !automaticAvailable)}
            class="flex items-start gap-3 rounded-lg border p-3 text-left transition-colors disabled:cursor-not-allowed disabled:opacity-50 {policy.strategy === typedStrategy ? 'border-primary bg-primary/5' : 'border-border hover:bg-accent/40'}"
          >
            <span class="mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-full border {policy.strategy === typedStrategy ? 'border-primary bg-primary' : 'border-muted-foreground/50'}">
              {#if policy.strategy === typedStrategy}<span class="h-1.5 w-1.5 rounded-full bg-primary-foreground"></span>{/if}
            </span>
            <span class="min-w-0 flex-1">
              <span class="flex flex-wrap items-center gap-2 text-sm font-semibold">
                {credentialStrategyLabel(typedStrategy)}
                {#if typedStrategy === 'failover'}<span class="rounded bg-green-100 px-1.5 py-0.5 text-[9px] font-semibold uppercase text-green-700 dark:bg-green-950/60 dark:text-green-300">Recommended</span>{/if}
                {#if typedStrategy === 'round_robin'}<span class="rounded bg-muted px-1.5 py-0.5 text-[9px] font-semibold uppercase text-muted-foreground">Advanced</span>{/if}
              </span>
              <span class="mt-0.5 block text-xs text-muted-foreground">{credentialStrategyDescription(typedStrategy)}</span>
              {#if automatic && !automaticAvailable}<span class="mt-1 block text-[11px] text-yellow-700 dark:text-yellow-300">Requires at least two enabled credentials.</span>{/if}
            </span>
            {#if operation === 'policy' && policy.strategy !== typedStrategy}<Loader2 class="mt-0.5 h-4 w-4 animate-spin text-muted-foreground" />{/if}
          </button>
        {/each}
      </div>

      {#if policy.strategy !== 'manual'}
        <label class="mt-3 flex items-center justify-between gap-3 rounded-lg bg-muted/40 px-3 py-2.5 text-xs">
          <span>
            <span class="font-semibold">Maximum attempts</span>
            <span class="mt-0.5 block text-muted-foreground">Includes the first credential. Lower values reduce duplicate cost risk.</span>
          </span>
          <div class="relative shrink-0">
            <select
              value={policy.max_attempts}
              onchange={(event) => handleMaxAttempts(Number(event.currentTarget.value))}
              disabled={operation !== ''}
              class="appearance-none rounded-md border border-border bg-background py-1.5 pl-3 pr-8 text-sm font-medium"
            >
              {#each [2, 3, 4, 5] as attemptCount}
                <option value={attemptCount}>{attemptCount}</option>
              {/each}
            </select>
            <ChevronDown class="pointer-events-none absolute right-2 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
          </div>
        </label>
      {/if}
    </div>
  {/if}

  {#if panelError}
    <div class="mt-3 flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700 dark:border-red-900 dark:bg-red-950/30 dark:text-red-300">
      <CircleAlert class="mt-0.5 h-3.5 w-3.5 shrink-0" />
      {panelError}
    </div>
  {/if}
</section>
