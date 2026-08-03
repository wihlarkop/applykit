<script lang="ts">
  import { activeProfile } from '$lib/activeProfile.svelte';
  import ReadinessChecklist from '$lib/components/ReadinessChecklist.svelte';
  import { Button } from '$lib/components/ui/button';
  import { Skeleton } from '$lib/components/ui/skeleton';
  import { profiles } from '$lib/profiles.svelte';
  import {
    ArrowRight,
    BarChart3,
    Briefcase,
    FileText,
    Mail,
    Sparkles,
    User,
  } from '@lucide/svelte';

  let { data } = $props();
  const readiness = $derived(data.readiness);
  const profile = $derived(activeProfile.current);
  const activeProfileItem = $derived(profiles.all.find((item) => item.id === profile?.id));
  const isActiveEmpty = $derived(activeProfileItem != null && !activeProfileItem.has_content);

  const cards = [
    {
      href: '/profile',
      title: 'Profile Setup',
      description: 'Manage your personal info, experience, and core skills.',
      icon: User,
      color: 'text-blue-500',
      bg: 'bg-blue-500/10',
    },
    {
      href: '/import',
      title: 'Import CV',
      description: 'Quickly populate your profile from an existing PDF or DOCX.',
      icon: FileText,
      color: 'text-purple-500',
      bg: 'bg-purple-500/10',
    },
    {
      href: '/generate',
      title: 'Generate CV',
      description: 'Get an ATS-optimized CV with AI-enhanced bullet points.',
      icon: Sparkles,
      color: 'text-amber-500',
      bg: 'bg-amber-500/10',
    },
    {
      href: '/cover-letter',
      title: 'Cover Letter',
      description: 'Write a tailored cover letter from a job description.',
      icon: Mail,
      color: 'text-emerald-500',
      bg: 'bg-emerald-500/10',
    },
    {
      href: '/smart-apply',
      title: 'Smart Apply',
      description: 'Parse a job and prepare tailored application materials.',
      icon: Briefcase,
      color: 'text-cyan-500',
      bg: 'bg-cyan-500/10',
    },
    {
      href: '/tracker',
      title: 'Application Tracker',
      description: 'Track your job applications across different stages.',
      icon: Briefcase,
      color: 'text-rose-500',
      bg: 'bg-rose-500/10',
    },
    {
      href: '/usage',
      title: 'LLM Usage',
      description: 'View AI usage statistics and sanitized operational logs.',
      icon: BarChart3,
      color: 'text-orange-500',
      bg: 'bg-orange-500/10',
    },
  ];
</script>

<div class="flex flex-col gap-6">
  <section class="relative overflow-hidden rounded-3xl border bg-linear-to-br from-primary/10 via-background to-secondary/10 p-8 shadow-sm sm:p-10">
    <div class="relative z-10 flex flex-col justify-between gap-8 md:flex-row md:items-center">
      <div class="max-w-2xl text-left">
        <div class="mb-6 inline-flex items-center rounded-full border bg-background/50 px-3 py-1 text-xs font-semibold uppercase tracking-widest text-muted-foreground/80 backdrop-blur-sm">
          <Sparkles class="mr-2 h-3.5 w-3.5 text-primary" />
          AI Application Toolkit
        </div>
        <h1 class="mb-4 text-3xl font-black leading-[1.1] tracking-tight text-foreground sm:text-4xl md:text-5xl">
          {#if readiness === undefined}
            <Skeleton class="h-12 w-80 rounded-xl" />
          {:else if profile?.name || profile?.label}
            Ready for the next role,
            <span class="bg-linear-to-r from-primary to-purple-500 bg-clip-text text-transparent">{profile.name || profile.label}</span>?
          {:else}
            Welcome to <span class="bg-linear-to-r from-primary to-purple-500 bg-clip-text text-transparent">ApplyKit</span>
          {/if}
        </h1>
        <p class="max-w-xl text-base leading-relaxed text-muted-foreground md:text-lg">
          {#if readiness?.applykit_ready}
            Your active profile and AI connection are ready for tailored application work.
          {:else}
            Keep working while the readiness checklist guides only the setup that still needs attention.
          {/if}
        </p>
      </div>

      <div class="flex flex-wrap gap-3">
        <Button href="/generate" size="lg" class="rounded-full px-8 py-6 text-base font-bold shadow-lg">
          <Sparkles class="h-5 w-5" /> Generate CV
        </Button>
      </div>
    </div>
    <div class="pointer-events-none absolute -right-20 -top-20 h-80 w-80 rounded-full bg-primary/15 blur-[100px]"></div>
    <div class="pointer-events-none absolute -bottom-32 left-1/2 h-60 w-96 -translate-x-1/2 rounded-full bg-purple-500/10 blur-[100px]"></div>
  </section>

  {#if readiness}
    <ReadinessChecklist {readiness} />
  {/if}

  <section class="flex flex-col">
    <h2 class="mb-3 flex items-center gap-2 text-base font-semibold tracking-tight">
      <ArrowRight class="h-4 w-4 text-primary" /> Quick Navigation
    </h2>

    <div class="overflow-hidden rounded-xl border border-border/60 bg-card/20">
      {#each cards as card, index}
        <a
          href={card.href}
          class="group flex cursor-pointer items-center gap-4 px-4 py-3.5 transition-colors hover:bg-accent/60 {index < cards.length - 1 ? 'border-b border-border/40' : ''}"
        >
          <div class="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg {card.bg} {card.color} transition-transform duration-200 group-hover:scale-105">
            <card.icon class="h-4 w-4" />
          </div>
          <div class="min-w-0 flex-1">
            <div class="flex items-center gap-1.5">
              <span class="text-sm font-semibold transition-colors group-hover:text-primary">{card.title}</span>
              {#if isActiveEmpty && (card.href === '/generate' || card.href === '/cover-letter')}
                <span class="text-[10px] font-medium text-yellow-500">⚠ Empty profile</span>
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
