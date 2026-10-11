<script lang="ts">
  import { activeProfile } from '$lib/activeProfile.svelte';
  import { getCvHistory, listApplications } from '$lib/api';
  import ReadinessChecklist from '$lib/components/ReadinessChecklist.svelte';
  import { Button } from '$lib/components/ui/button';
  import { Skeleton } from '$lib/components/ui/skeleton';
  import { presentNextAction } from '$lib/dashboard-next-action';
  import { profiles } from '$lib/profiles.svelte';
  import { getLatestResumeReadiness } from '$lib/resume-readiness-api';
  import type {
    ResumeReadinessBand,
    ResumeReadinessStatus,
  } from '$lib/resume-readiness-types';
  import {
    ArrowRight,
    BarChart3,
    Briefcase,
    FileCheck2,
    FileText,
    Mail,
    Sparkles,
    User,
  } from '@lucide/svelte';

  let { data } = $props();
  const readiness = $derived(data.readiness);
  const profile = $derived(activeProfile.current);
  const activeProfileItem = $derived(
    profiles.all.find((item) => item.id === profile?.id),
  );
  const isActiveEmpty = $derived(
    activeProfileItem != null && !activeProfileItem.has_content,
  );

  let contextLoading = $state(false);
  let hasGeneratedResume = $state(false);
  let resumeReadinessStatus = $state<ResumeReadinessStatus | null>(null);
  let resumeReadinessBand = $state<ResumeReadinessBand | null>(null);
  let applicationCount = $state(0);
  let loadSequence = 0;

  $effect(() => {
    const profileId = activeProfile.current?.id ?? null;
    const sequence = ++loadSequence;
    hasGeneratedResume = false;
    resumeReadinessStatus = null;
    resumeReadinessBand = null;
    applicationCount = 0;
    if (profileId == null) return;

    contextLoading = true;
    Promise.all([
      getCvHistory({ profile_id: profileId, sort: 'date_desc', limit: 1 }),
      listApplications({ profile_id: profileId, sort: 'date_desc' }),
    ])
      .then(async ([cvHistory, applications]) => {
        if (sequence !== loadSequence) return;
        applicationCount = applications.total;
        const latestCv = cvHistory.items[0];
        hasGeneratedResume = latestCv != null;
        if (!latestCv) return;
        const analysis = await getLatestResumeReadiness(latestCv.id);
        if (sequence !== loadSequence || !analysis) return;
        resumeReadinessStatus = analysis.status;
        resumeReadinessBand = analysis.overall.band;
      })
      .catch(() => {
        // The primary readiness checklist remains useful when optional context fails.
      })
      .finally(() => {
        if (sequence === loadSequence) contextLoading = false;
      });
  });

  const nextAction = $derived(
    presentNextAction({
      profileReady: readiness?.profile.ready ?? false,
      aiReady: readiness?.ai.ready ?? false,
      hasGeneratedResume,
      resumeReadinessStatus,
      resumeReadinessBand,
      applicationCount,
    }),
  );

  const cards = [
    {
      href: '/profile',
      title: 'Career Profile',
      description: 'Manage factual career evidence used across ApplyKit.',
      icon: User,
    },
    {
      href: '/resume',
      title: 'Resume',
      description: 'Generate, validate, and download a saved resume version.',
      icon: FileCheck2,
    },
    {
      href: '/cover-letter',
      title: 'Cover Letter',
      description: 'Prepare a role-specific letter from verified profile evidence.',
      icon: Mail,
    },
    {
      href: '/documents',
      title: 'Documents',
      description: 'Review saved resumes and cover letters.',
      icon: FileText,
    },
    {
      href: '/applications',
      title: 'Applications',
      description: 'Track application status and follow-up work.',
      icon: Briefcase,
    },
    {
      href: '/usage',
      title: 'LLM Usage',
      description: 'Review sanitized provider usage and operational costs.',
      icon: BarChart3,
    },
  ];
</script>

<div class="flex flex-col gap-6">
  <section class="relative overflow-hidden rounded-3xl border bg-linear-to-br from-primary/10 via-background to-secondary/10 p-8 shadow-sm sm:p-10">
    <div class="relative z-10 flex flex-col justify-between gap-8 md:flex-row md:items-end">
      <div class="max-w-2xl text-left">
        <div class="mb-5 inline-flex items-center rounded-full border bg-background/60 px-3 py-1 text-xs font-semibold uppercase tracking-widest text-muted-foreground backdrop-blur-sm">
          <Sparkles class="mr-2 h-3.5 w-3.5 text-primary" />
          Your next action
        </div>

        {#if readiness === undefined}
          <Skeleton class="h-12 w-80 rounded-xl" />
        {:else}
          <h1 class="text-3xl font-black leading-tight tracking-tight sm:text-4xl">
            {nextAction.title}
          </h1>
          <p class="mt-3 max-w-xl text-base leading-relaxed text-muted-foreground md:text-lg">
            {nextAction.description}
          </p>
          {#if profile?.label}
            <p class="mt-3 text-sm text-muted-foreground">
              Active profile: <span class="font-semibold text-foreground">{profile.icon} {profile.label}</span>
            </p>
          {/if}
        {/if}
      </div>

      <div class="flex shrink-0 flex-wrap gap-3">
        <Button href={nextAction.href} size="lg" class="rounded-full px-8 py-6 text-base font-bold shadow-lg">
          {nextAction.actionLabel}
          <ArrowRight class="h-5 w-5" />
        </Button>
      </div>
    </div>

    {#if contextLoading}
      <div class="relative z-10 mt-5 text-xs text-muted-foreground">Checking your latest work…</div>
    {/if}

    <div class="pointer-events-none absolute -right-20 -top-20 h-80 w-80 rounded-full bg-primary/15 blur-[100px]"></div>
    <div class="pointer-events-none absolute -bottom-32 left-1/2 h-60 w-96 -translate-x-1/2 rounded-full bg-purple-500/10 blur-[100px]"></div>
  </section>

  {#if readiness}
    <ReadinessChecklist {readiness} />
  {/if}

  <section>
    <h2 class="mb-3 flex items-center gap-2 text-base font-semibold tracking-tight">
      <ArrowRight class="h-4 w-4 text-primary" />
      Workspace
    </h2>

    <div class="overflow-hidden rounded-xl border border-border/60 bg-card/20">
      {#each cards as card, index}
        <a
          href={card.href}
          class="group flex items-center gap-4 px-4 py-3.5 transition-colors hover:bg-accent/60 {index < cards.length - 1 ? 'border-b border-border/40' : ''}"
        >
          <div class="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary transition-transform group-hover:scale-105">
            <card.icon class="h-4 w-4" />
          </div>
          <div class="min-w-0 flex-1">
            <div class="flex items-center gap-1.5">
              <span class="text-sm font-semibold transition-colors group-hover:text-primary">{card.title}</span>
              {#if isActiveEmpty && (card.href === '/resume' || card.href === '/cover-letter')}
                <span class="text-[10px] font-medium text-yellow-600 dark:text-yellow-400">Empty profile</span>
              {/if}
            </div>
            <p class="truncate text-xs text-muted-foreground">{card.description}</p>
          </div>
          <ArrowRight class="h-4 w-4 shrink-0 text-muted-foreground/30 transition-all group-hover:translate-x-0.5 group-hover:text-primary" />
        </a>
      {/each}
    </div>
  </section>
</div>
