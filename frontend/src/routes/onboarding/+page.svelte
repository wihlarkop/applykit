<script lang="ts">
  import { goto } from '$app/navigation';
  import { activeProfile } from '$lib/activeProfile.svelte';
  import { Button } from '$lib/components/ui/button';
  import { Badge } from '$lib/components/ui/badge';
  import { Card, CardContent, CardHeader, CardTitle } from '$lib/components/ui/card';
  import { testConfiguredIntegration } from '$lib/integration-api';
  import {
    completeOnboarding,
    getReadiness,
    skipOnboarding,
  } from '$lib/readiness-api';
  import type { ReadinessResponse } from '$lib/readiness-types';
  import {
    ArrowRight,
    BriefcaseBusiness,
    CircleCheck,
    FileUp,
    GraduationCap,
    RefreshCw,
    Settings,
    Sparkles,
    UserRound,
  } from '@lucide/svelte';

  let { data } = $props();
  let readiness = $state<ReadinessResponse | null>(data.readiness);
  let testing = $state(false);
  let skipping = $state(false);
  let completing = $state(false);
  let publicError = $state('');

  const profileId = $derived(data.activeProfileId ?? activeProfile.current?.id ?? null);
  const profile = $derived(readiness?.profile ?? null);
  const ai = $derived(readiness?.ai ?? null);
  const isReady = $derived(readiness?.applykit_ready ?? false);

  const requirementLabels: Record<string, string> = {
    name: 'Add your name',
    email: 'Add your email',
    experience_or_education: 'Add work experience or education',
    skills: 'Add at least one skill',
  };

  async function refreshReadiness(): Promise<ReadinessResponse | null> {
    if (profileId == null) return null;
    const next = await getReadiness(profileId);
    readiness = next;
    return next;
  }

  async function finishIfReady(next: ReadinessResponse | null) {
    if (!next?.applykit_ready || next.onboarding.seen || profileId == null || completing) return;
    completing = true;
    try {
      readiness = await completeOnboarding(profileId);
    } catch {
      publicError = 'ApplyKit is ready, but setup could not be finalized. Try refreshing the page.';
    } finally {
      completing = false;
    }
  }

  async function testConnection() {
    if (!ai?.provider || profileId == null || testing) return;
    testing = true;
    publicError = '';
    try {
      await testConfiguredIntegration(ai.provider);
      const next = await refreshReadiness();
      await finishIfReady(next);
    } catch {
      publicError = 'The connection test could not be completed. Review AI settings and try again.';
    } finally {
      testing = false;
    }
  }

  async function handleSkip() {
    if (profileId == null || skipping) return;
    skipping = true;
    publicError = '';
    try {
      await skipOnboarding(profileId);
      await goto('/');
    } catch {
      publicError = 'Setup could not be skipped right now. Please try again.';
      skipping = false;
    }
  }

  $effect(() => {
    const current = readiness;
    if (current?.applykit_ready && !current.onboarding.seen && !completing) {
      void finishIfReady(current);
    }
  });
</script>

{#if readiness === null || profile === null || ai === null}
  <div class="mx-auto flex min-h-[70vh] max-w-3xl items-center justify-center">
    <Card class="w-full border-dashed">
      <CardContent class="flex flex-col items-center gap-4 py-14 text-center">
        <RefreshCw class="h-8 w-8 animate-spin text-primary" />
        <div>
          <p class="font-semibold">Loading guided setup…</p>
          <p class="mt-1 text-sm text-muted-foreground">Your existing profile and provider data are not being changed.</p>
        </div>
      </CardContent>
    </Card>
  </div>
{:else if isReady && readiness.onboarding.seen}
  <div class="mx-auto flex min-h-[72vh] max-w-3xl items-center justify-center py-10">
    <Card class="w-full overflow-hidden border-green-200 bg-linear-to-br from-green-50 via-background to-primary/5 shadow-xl dark:border-green-900 dark:from-green-950/20">
      <CardContent class="flex flex-col items-center px-6 py-14 text-center sm:px-12">
        <div class="mb-6 flex h-20 w-20 items-center justify-center rounded-3xl bg-green-600 text-white shadow-lg shadow-green-600/20">
          <CircleCheck class="h-10 w-10" />
        </div>
        <Badge class="mb-4 bg-green-600">ApplyKit Ready</Badge>
        <h1 class="text-4xl font-black tracking-tight sm:text-5xl">You are ready to build your next application.</h1>
        <p class="mt-4 max-w-xl text-base leading-relaxed text-muted-foreground sm:text-lg">
          Your active profile meets the core requirements and the current AI configuration has been verified.
        </p>
        <div class="mt-8 flex flex-wrap justify-center gap-3">
          <Button href="/" size="lg" variant="outline">Go to Dashboard</Button>
          <Button href="/generate" size="lg">
            Create your first CV
            <ArrowRight class="h-4 w-4" />
          </Button>
        </div>
      </CardContent>
    </Card>
  </div>
{:else}
  <div class="mx-auto grid max-w-5xl gap-8 py-6 lg:grid-cols-[minmax(0,1.35fr)_minmax(300px,.65fr)] lg:py-10">
    <section>
      <Badge variant="outline" class="border-primary/25 bg-primary/5 px-3 py-1 text-primary">
        <Sparkles class="h-3.5 w-3.5" /> Guided setup
      </Badge>
      <h1 class="mt-5 max-w-3xl text-4xl font-black leading-[1.05] tracking-[-0.045em] sm:text-5xl lg:text-6xl">
        Get ApplyKit ready for your next application.
      </h1>
      <p class="mt-4 max-w-2xl text-base leading-relaxed text-muted-foreground sm:text-lg">
        Complete two practical checks. You can Skip for now, continue using non-AI features, and return from the dashboard whenever convenient.
      </p>

      <div class="mt-8 space-y-4">
        <Card class="border-2 {profile.ready ? 'border-green-200 dark:border-green-900' : 'border-primary/35 shadow-lg shadow-primary/5'}">
          <CardHeader class="pb-3">
            <div class="flex flex-col justify-between gap-4 sm:flex-row sm:items-start">
              <div class="flex gap-4">
                <div class="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl {profile.ready ? 'bg-green-100 text-green-700 dark:bg-green-950 dark:text-green-300' : 'bg-primary/10 text-primary'}">
                  {#if profile.ready}<CircleCheck class="h-6 w-6" />{:else}<UserRound class="h-6 w-6" />{/if}
                </div>
                <div>
                  <CardTitle class="flex flex-wrap items-center gap-2 text-xl">
                    Profile Ready
                    <Badge variant={profile.ready ? 'default' : 'secondary'} class={profile.ready ? 'bg-green-600' : ''}>
                      {profile.ready ? 'Ready' : 'Needs attention'}
                    </Badge>
                  </CardTitle>
                  <p class="mt-2 text-sm leading-relaxed text-muted-foreground">
                    Name, email, work experience or education, and at least one skill make the active profile ready.
                  </p>
                </div>
              </div>
              <Button href="/profile" variant={profile.ready ? 'outline' : 'default'}>
                {profile.ready ? 'Review profile' : 'Complete profile'}
              </Button>
            </div>
          </CardHeader>
          {#if !profile.ready}
            <CardContent class="pt-0">
              <div class="ml-0 grid gap-2 rounded-xl bg-muted/50 p-4 sm:ml-16">
                {#each profile.missing_requirements as requirement}
                  <div class="flex items-center gap-2 text-sm">
                    <span class="h-1.5 w-1.5 rounded-full bg-amber-500"></span>
                    {requirementLabels[requirement]}
                  </div>
                {/each}
                <div class="mt-2 flex flex-wrap gap-2">
                  <Button href="/import" size="sm" variant="outline"><FileUp class="h-4 w-4" /> Import CV</Button>
                  <Button href="/profile" size="sm" variant="ghost"><UserRound class="h-4 w-4" /> Enter manually</Button>
                </div>
              </div>
            </CardContent>
          {/if}
        </Card>

        <Card class="border-2 {ai.ready ? 'border-green-200 dark:border-green-900' : 'border-primary/35 shadow-lg shadow-primary/5'}">
          <CardHeader class="pb-3">
            <div class="flex flex-col justify-between gap-4 sm:flex-row sm:items-start">
              <div class="flex gap-4">
                <div class="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl {ai.ready ? 'bg-green-100 text-green-700 dark:bg-green-950 dark:text-green-300' : 'bg-primary/10 text-primary'}">
                  {#if ai.ready}<CircleCheck class="h-6 w-6" />{:else}<Sparkles class="h-6 w-6" />{/if}
                </div>
                <div>
                  <CardTitle class="flex flex-wrap items-center gap-2 text-xl">
                    AI Ready
                    <Badge variant={ai.ready ? 'default' : 'secondary'} class={ai.ready ? 'bg-green-600' : ''}>
                      {ai.ready ? 'Ready' : ai.status === 'not_configured' ? 'Not configured' : 'Needs test'}
                    </Badge>
                  </CardTitle>
                  <p class="mt-2 text-sm leading-relaxed text-muted-foreground">{ai.message}</p>
                  {#if ai.model}
                    <p class="mt-1 text-xs font-medium text-muted-foreground">Active model: {ai.model}</p>
                  {/if}
                </div>
              </div>
              <div class="flex flex-wrap gap-2 sm:justify-end">
                {#if ai.provider && !ai.ready}
                  <Button onclick={testConnection} disabled={testing}>
                    <RefreshCw class="h-4 w-4 {testing ? 'animate-spin' : ''}" />
                    {testing ? 'Testing…' : ai.tested_at ? 'Test again' : 'Test connection'}
                  </Button>
                {/if}
                <Button href="/settings" variant={ai.status === 'not_configured' ? 'default' : 'outline'}>
                  <Settings class="h-4 w-4" />
                  {ai.status === 'not_configured' ? 'Configure AI' : 'Fix AI settings'}
                </Button>
              </div>
            </div>
          </CardHeader>
        </Card>
      </div>

      {#if publicError}
        <p class="mt-4 rounded-xl border border-destructive/25 bg-destructive/5 p-3 text-sm font-medium text-destructive">{publicError}</p>
      {/if}

      <div class="mt-6 flex flex-wrap items-center gap-3">
        <Button onclick={handleSkip} variant="outline" disabled={skipping}>
          {skipping ? 'Skipping…' : 'Skip for now'}
        </Button>
        <p class="max-w-xl text-xs leading-relaxed text-muted-foreground">
          Skipping never disables Profile, Tracker, or other non-AI features. AI actions provide focused setup guidance only when needed.
        </p>
      </div>
    </section>

    <aside class="h-fit overflow-hidden rounded-3xl bg-linear-to-br from-slate-950 via-indigo-950 to-purple-900 p-6 text-white shadow-2xl lg:sticky lg:top-24">
      <p class="text-xs font-bold uppercase tracking-[0.18em] text-white/55">Active profile</p>
      <div class="mt-5 flex items-center gap-3">
        <div class="flex h-13 w-13 items-center justify-center rounded-2xl bg-white/10 text-lg font-black ring-1 ring-white/10">
          {activeProfile.current?.icon ?? '💼'}
        </div>
        <div>
          <p class="font-bold">{activeProfile.current?.name || activeProfile.current?.label || 'Default profile'}</p>
          <p class="mt-0.5 text-xs text-white/55">Profile ID {profile.profile_id}</p>
        </div>
      </div>

      <div class="mt-8 flex items-center justify-between text-sm">
        <span class="font-semibold">Profile completeness</span>
        <span class="font-black">{profile.completeness}%</span>
      </div>
      <div class="mt-2 h-2 overflow-hidden rounded-full bg-white/10">
        <div class="h-full rounded-full bg-linear-to-r from-violet-400 to-blue-400" style={`width: ${profile.completeness}%`}></div>
      </div>

      <div class="mt-6 space-y-3">
        <div class="flex items-center justify-between gap-3 rounded-xl border border-white/10 bg-white/7 p-3 text-sm">
          <span class="flex items-center gap-2"><BriefcaseBusiness class="h-4 w-4" /> Core profile requirements</span>
          <span class="font-bold text-violet-200">{profile.ready ? 'Ready' : 'Incomplete'}</span>
        </div>
        <div class="flex items-center justify-between gap-3 rounded-xl border border-white/10 bg-white/7 p-3 text-sm">
          <span class="flex items-center gap-2"><Sparkles class="h-4 w-4" /> AI connection</span>
          <span class="font-bold text-violet-200">{ai.ready ? 'Verified' : 'Pending'}</span>
        </div>
        <div class="flex items-center justify-between gap-3 rounded-xl border border-white/10 bg-white/7 p-3 text-sm">
          <span class="flex items-center gap-2"><GraduationCap class="h-4 w-4" /> Recommendations</span>
          <span class="font-bold text-violet-200">{profile.recommendations.length}</span>
        </div>
      </div>

      <p class="mt-6 text-xs leading-relaxed text-white/55">
        Completeness is advisory. It helps improve your profile, but does not block readiness and does not guarantee hiring outcomes.
      </p>
    </aside>
  </div>
{/if}
