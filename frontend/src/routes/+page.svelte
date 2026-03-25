<script lang="ts">
	import { activeProfile } from '$lib/activeProfile.svelte';
	import { Button } from '$lib/components/ui/button';
	import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '$lib/components/ui/card';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import { profiles } from '$lib/profiles.svelte';
	import { ArrowRight, BarChart3, Briefcase, FileText, Lock, Mail, Sparkles, User } from '@lucide/svelte';

	let { data } = $props();
	const isOnboarded = $derived(data.isOnboarded);
	const profile = $derived(activeProfile.current);
	const activeProfileItem = $derived(profiles.all.find(p => p.id === activeProfile.current?.id));
	const isActiveEmpty = $derived(activeProfileItem != null && !activeProfileItem.has_content);

const cards = [
    {
      href: '/profile',
      title: 'Profile Setup',
      description: 'Manage your personal info, experience, and core skills.',
      action: 'Edit Profile',
      icon: User,
      step: 1,
      color: 'text-blue-500',
      bg: 'bg-blue-500/10'
    },
    {
      href: '/import',
      title: 'Import CV',
      description: 'Quickly populate your profile from an existing PDF or DOCX.',
      action: 'Import Data',
      icon: FileText,
      step: 2,
      color: 'text-purple-500',
      bg: 'bg-purple-500/10'
    },
    {
      href: '/generate',
      title: 'Generate CV',
      description: 'Get an ATS-optimized CV with AI-enhanced bullet points.',
      action: 'Generate ATS CV',
      icon: Sparkles,
      step: 3,
      color: 'text-amber-500',
      bg: 'bg-amber-500/10'
    },
    {
      href: '/cover-letter',
      title: 'Cover Letter',
      description: 'Write a tailored cover letter instantly from a job description.',
      action: 'Write Letter',
      icon: Mail,
      step: 4,
      color: 'text-emerald-500',
      bg: 'bg-emerald-500/10'
    },
    {
      href: '/smart-apply',
      title: 'Smart Apply',
      description: 'Paste a job URL, auto-parse details, and generate tailored CV + CL.',
      action: 'Apply Now',
      icon: Briefcase,
      step: 5,
      color: 'text-cyan-500',
      bg: 'bg-cyan-500/10'
    },
    {
      href: '/tracker',
      title: 'Application Tracker',
      description: 'Track your job applications across different stages.',
      action: 'Track Jobs',
      icon: Briefcase,
      step: 6,
      color: 'text-rose-500',
      bg: 'bg-rose-500/10'
    },
    {
      href: '/usage',
      title: 'LLM Usage',
      description: 'View AI usage statistics and logs.',
      action: 'View Stats',
      icon: BarChart3,
      step: 7,
      color: 'text-orange-500',
      bg: 'bg-orange-500/10'
    },
  ];
    const displayedCards = $derived(
      cards
        .filter((card) => !(isOnboarded && card.title === 'Import CV'))
        .map((card, index) => ({ ...card, displayStep: index + 1 }))
    );
  </script>

  <div class="flex flex-col gap-6">
    <!-- Restored Premium Hero Section -->
    <div class="relative overflow-hidden rounded-3xl bg-linear-to-br from-primary/10 via-background to-secondary/10 p-8 sm:p-10 border shadow-sm flex-shrink-0">
      <div class="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-8">
        <div class="max-w-2xl text-left">
          <div class="inline-flex items-center rounded-full border bg-background/50 px-3 py-1 text-xs font-semibold mb-6 backdrop-blur-sm uppercase tracking-widest text-muted-foreground/80">
            <Sparkles class="mr-2 h-3.5 w-3.5 text-primary" />
            AI Application Toolkit
          </div>
          <h1 class="text-3xl sm:text-4xl md:text-5xl font-black tracking-tight mb-4 text-foreground leading-[1.1]">
            {#if isOnboarded === undefined}
              <Skeleton class="h-12 w-80 rounded-xl" />
            {:else if isOnboarded && (profile?.name || profile?.label)}
              Ready for the next role, <span class="text-transparent bg-clip-text bg-linear-to-r from-primary to-purple-500">{profile.name || profile.label}</span>?
            {:else}
              Welcome to <span class="text-transparent bg-clip-text bg-linear-to-r from-primary to-purple-500">ApplyKit</span>
            {/if}
          </h1>
          <p class="text-base md:text-lg text-muted-foreground leading-relaxed max-w-xl">
            {#if isOnboarded}
              Your profile is ready. Use our AI tools to tailor your application for any job in seconds.
            {:else}
              Your self-hosted, local-first CV and cover letter generator. Keep your data private.
            {/if}
          </p>
        </div>
        
        <div class="flex flex-wrap gap-4">
          {#if !isOnboarded}
            <Button href="/onboarding" size="lg" class="rounded-full shadow-lg px-8 py-6 text-base font-bold">
              Get Started
              <ArrowRight class="ml-2 h-5 w-5" />
            </Button>
          {:else}
            <Button href="/generate" size="lg" class="rounded-full shadow-lg px-8 py-6 text-base font-bold">
              <Sparkles class="mr-2 h-5 w-5" />
              Generate CV
            </Button>
          {/if}
        </div>
      </div>
      <!-- Decorative background elements -->
      <div class="absolute -right-20 -top-20 h-80 w-80 rounded-full bg-primary/15 blur-[100px] pointer-events-none"></div>
      <div class="absolute -bottom-32 left-1/2 h-60 w-96 -translate-x-1/2 rounded-full bg-purple-500/10 blur-[100px] pointer-events-none"></div>
    </div>

    <!-- Navigation Section -->
    <div class="flex flex-col">
      <h2 class="text-base font-semibold tracking-tight mb-3 flex items-center gap-2 flex-shrink-0">
        <ArrowRight class="w-4 h-4 text-primary" />
        Quick Navigation
      </h2>
      
      <div class="rounded-xl border border-border/60 overflow-hidden bg-card/20">
        {#each displayedCards as card, i}
          {@const isRestricted = !isOnboarded && card.step > 2}
          <a
            href={isRestricted ? undefined : card.href}
            class="flex items-center gap-4 px-4 py-3.5 group transition-colors
                   {isRestricted ? 'cursor-not-allowed opacity-50' : 'cursor-pointer hover:bg-accent/60'}
                   {i < displayedCards.length - 1 ? 'border-b border-border/40' : ''}"
          >
            <div class="flex items-center justify-center w-9 h-9 rounded-lg {card.bg} {card.color} shrink-0 transition-transform duration-200 group-hover:scale-105">
              <card.icon class="w-4 h-4" />
            </div>

            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-1.5">
                <span class="text-sm font-semibold group-hover:text-primary transition-colors">
                  {card.title}
                </span>
                {#if isRestricted}
                  <Lock class="w-3 h-3 text-muted-foreground shrink-0" />
                {/if}
                {#if isOnboarded && isActiveEmpty && (card.href === '/generate' || card.href === '/cover-letter')}
                  <span class="text-[10px] text-yellow-500 font-medium">⚠ Empty</span>
                {/if}
              </div>
              <p class="text-xs text-muted-foreground truncate">
                {isRestricted ? 'Complete setup first to unlock.' : card.description}
              </p>
            </div>

            {#if !isRestricted}
              <ArrowRight class="w-4 h-4 text-muted-foreground/30 group-hover:text-primary group-hover:translate-x-0.5 transition-all shrink-0" />
            {/if}
          </a>
        {/each}
      </div>
    </div>
  </div>
