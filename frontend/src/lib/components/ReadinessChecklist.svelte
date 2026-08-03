<script lang="ts">
  import { goto } from '$app/navigation';
  import { activeProfile } from '$lib/activeProfile.svelte';
  import { Button } from '$lib/components/ui/button';
  import {
    dismissReadinessChecklist,
    getReadiness,
  } from '$lib/readiness-api';
  import type { ReadinessResponse } from '$lib/readiness-types';
  import { testConfiguredIntegration } from '$lib/integration-api';
  import {
    AlertTriangle,
    Check,
    ChevronRight,
    CircleCheck,
    RefreshCw,
    Settings,
    Sparkles,
    UserRound,
    X,
  } from '@lucide/svelte';

  let {
    readiness,
  }: {
    readiness: ReadinessResponse;
  } = $props();

  let current = $state(readiness);
  let testing = $state(false);
  let dismissing = $state(false);
  let publicError = $state('');

  $effect(() => {
    current = readiness;
    publicError = '';
  });

  const profileName = $derived(
    activeProfile.current?.name || activeProfile.current?.label || `Profile ${current.profile.profile_id}`,
  );

  async function refresh() {
    current = await getReadiness(current.profile.profile_id);
  }

  async function testConnection() {
    if (!current.ai.provider || testing) return;
    testing = true;
    publicError = '';
    try {
      await testConfiguredIntegration(current.ai.provider);
      await refresh();
    } catch {
      publicError = 'The connection test could not be completed. Review AI settings and try again.';
    } finally {
      testing = false;
    }
  }

  async function dismiss() {
    if (dismissing) return;
    dismissing = true;
    publicError = '';
    try {
      current = await dismissReadinessChecklist(current.profile.profile_id);
    } catch {
      publicError = 'The readiness summary could not be dismissed. Please try again.';
    } finally {
      dismissing = false;
    }
  }

  function open(path: string) {
    void goto(path);
  }
</script>

{#if current.checklist_visible}
  {#if current.applykit_ready}
    <section class="rounded-2xl border border-green-200 bg-linear-to-r from-green-50 via-background to-primary/5 p-5 shadow-sm dark:border-green-900 dark:from-green-950/20" aria-label="ApplyKit readiness">
      <div class="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
        <div class="flex items-start gap-4">
          <div class="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-green-600 text-white shadow-lg shadow-green-600/20">
            <CircleCheck class="h-6 w-6" />
          </div>
          <div>
            <h2 class="text-lg font-bold">ApplyKit Ready</h2>
            <p class="mt-1 text-sm text-muted-foreground">
              {profileName} is ready and {current.ai.model ?? 'the active AI model'} has a verified connection.
            </p>
          </div>
        </div>
        <div class="flex flex-wrap gap-2 sm:justify-end">
          <Button href="/onboarding" variant="outline" size="sm">View setup</Button>
          <Button onclick={dismiss} variant="ghost" size="sm" disabled={dismissing} aria-label="Dismiss ApplyKit Ready summary">
            <X class="h-4 w-4" /> {dismissing ? 'Dismissing…' : 'Dismiss'}
          </Button>
        </div>
      </div>
      {#if publicError}<p class="mt-3 text-sm font-medium text-destructive">{publicError}</p>{/if}
    </section>
  {:else}
    <section class="overflow-hidden rounded-2xl border bg-card shadow-sm" aria-label="ApplyKit readiness checklist">
      <div class="flex flex-col justify-between gap-4 border-b p-5 sm:flex-row sm:items-start">
        <div>
          <div class="flex items-center gap-2">
            <Sparkles class="h-5 w-5 text-primary" />
            <h2 class="text-lg font-bold">Finish setting up ApplyKit</h2>
          </div>
          <p class="mt-1 text-sm text-muted-foreground">
            {Number(current.profile.ready) + Number(current.ai.ready)} of 2 readiness checks complete · active profile: {profileName}
          </p>
        </div>
        <Button onclick={dismiss} variant="ghost" size="sm" disabled={dismissing}>
          <X class="h-4 w-4" /> {dismissing ? 'Dismissing…' : 'Dismiss'}
        </Button>
      </div>

      <div class="grid md:grid-cols-2">
        <div class="flex gap-4 p-5 md:border-r">
          <div class="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl {current.profile.ready ? 'bg-green-100 text-green-700 dark:bg-green-950 dark:text-green-300' : 'bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-300'}">
            {#if current.profile.ready}<Check class="h-5 w-5" />{:else}<UserRound class="h-5 w-5" />{/if}
          </div>
          <div class="min-w-0 flex-1">
            <h3 class="font-semibold">{current.profile.ready ? 'Profile Ready' : 'Profile needs attention'}</h3>
            <p class="mt-1 text-sm leading-relaxed text-muted-foreground">
              {#if current.profile.ready}
                Core requirements are complete. Profile completeness is {current.profile.completeness}%.
              {:else}
                Add the missing core information. Completeness is currently {current.profile.completeness}%.
              {/if}
            </p>
            <div class="mt-3 flex flex-wrap gap-2">
              <Button onclick={() => open('/profile')} size="sm" variant={current.profile.ready ? 'outline' : 'default'}>
                {current.profile.ready ? 'Review recommendations' : 'Complete profile'}
                <ChevronRight class="h-4 w-4" />
              </Button>
              {#if !current.profile.ready}
                <Button href="/import" size="sm" variant="ghost">Import CV</Button>
              {/if}
            </div>
          </div>
        </div>

        <div class="flex gap-4 border-t p-5 md:border-t-0">
          <div class="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl {current.ai.ready ? 'bg-green-100 text-green-700 dark:bg-green-950 dark:text-green-300' : 'bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-300'}">
            {#if current.ai.ready}<Check class="h-5 w-5" />{:else}<AlertTriangle class="h-5 w-5" />{/if}
          </div>
          <div class="min-w-0 flex-1">
            <h3 class="font-semibold">
              {current.ai.ready
                ? 'AI Ready'
                : current.ai.status === 'not_configured'
                  ? 'Configure AI'
                  : current.ai.status === 'configuration_changed'
                    ? 'AI configuration changed'
                    : current.ai.status === 'retest_required'
                      ? 'AI needs one connection test'
                      : 'AI connection needs attention'}
            </h3>
            <p class="mt-1 text-sm leading-relaxed text-muted-foreground">{current.ai.message}</p>
            <div class="mt-3 flex flex-wrap gap-2">
              {#if current.ai.provider && !current.ai.ready}
                <Button onclick={testConnection} size="sm" disabled={testing}>
                  <RefreshCw class="h-4 w-4 {testing ? 'animate-spin' : ''}" />
                  {testing ? 'Testing…' : current.ai.tested_at ? 'Test again' : 'Test connection'}
                </Button>
              {/if}
              {#if !current.ai.ready}
                <Button onclick={() => open('/settings')} size="sm" variant="outline">
                  <Settings class="h-4 w-4" />
                  {current.ai.status === 'not_configured' ? 'Configure AI' : 'Fix AI settings'}
                </Button>
              {/if}
            </div>
          </div>
        </div>
      </div>

      {#if publicError}
        <p class="border-t bg-destructive/5 px-5 py-3 text-sm font-medium text-destructive">{publicError}</p>
      {/if}
    </section>
  {/if}
{/if}
