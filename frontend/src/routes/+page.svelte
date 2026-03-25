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

	function restrictedCardClass(isRestricted: boolean): string {
		return isRestricted
			? 'opacity-75 grayscale-[0.5]'
			: 'hover:shadow-xl hover:border-primary/50 hover:-translate-y-1';
	}

	function restrictedBtnClass(isRestricted: boolean): string {
		return isRestricted ? '' : 'group-hover:bg-primary group-hover:text-primary-foreground group-hover:border-transparent group-hover:shadow-md';
	}

	function restrictedIconClass(isRestricted: boolean): string {
		return isRestricted ? '' : 'group-hover:scale-110';
	}

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

  <div class="h-[calc(100dvh-2.5rem)] flex flex-col gap-6 overflow-hidden">
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
    <div class="flex-1 flex flex-col min-h-0 min-w-0">
      <h2 class="text-base font-semibold tracking-tight mb-3 flex items-center gap-2 flex-shrink-0">
        <ArrowRight class="w-4 h-4 text-primary" />
        Quick Navigation
      </h2>
      
      <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4 h-fit pb-2">
        {#each displayedCards as card}
          {@const isRestricted = !isOnboarded && card.step > 2}
          <a 
            href={isRestricted ? undefined : card.href}
            class="relative flex flex-col group {restrictedCardClass(isRestricted)} transition-all duration-400 
                   bg-card/30 backdrop-blur-lg border border-white/5 rounded-xl overflow-hidden h-48 sm:h-44
                   hover:bg-card/50 hover:border-primary/20 hover:shadow-xl hover:shadow-primary/5
                   {isRestricted ? 'cursor-not-allowed' : 'cursor-pointer'}"
          >
            <div class="absolute top-0 right-0 w-16 h-16 bg-linear-to-b from-primary/10 to-transparent rounded-bl-full pointer-events-none z-0 opacity-40 group-hover:opacity-100 transition-opacity"></div>
            
            <div class="p-4 flex flex-col h-full relative z-10">
              <div class="flex items-start justify-between mb-3">
                <div class="flex items-center justify-center w-9 h-9 rounded-lg {card.bg} {card.color} shadow-sm transition-transform duration-400 group-hover:scale-110">
                  <card.icon class="w-4.5 h-4.5" />
                </div>
                <span class="text-2xl font-black text-muted/15 group-hover:text-primary/10 transition-colors duration-400">
                  {card.displayStep}
                </span>
              </div>
              
              <div class="flex-1 min-w-0">
                <h3 class="text-sm sm:text-base font-bold mb-1 line-clamp-1 group-hover:text-primary transition-colors">
                  {card.title}
                  {#if isRestricted}
                    <Lock class="w-3 h-3 text-muted-foreground inline mb-0.5" />
                  {/if}
                </h3>
                <p class="text-[10px] sm:text-[11px] text-muted-foreground leading-relaxed line-clamp-2 sm:line-clamp-3">
                  {#if isRestricted}
                    Complete setup first to unlock this feature.
                  {:else}
                    {card.description}
                  {/if}
                </p>
              </div>

              {#if isOnboarded && isActiveEmpty && (card.href === '/generate' || card.href === '/cover-letter')}
                <div class="mt-2 text-[10px] text-yellow-500 font-medium flex items-center gap-1">
                  <span>⚠</span> Profile Empty
                </div>
              {/if}
              
              {#if !isRestricted}
                <div class="mt-2 text-[10px] font-bold text-primary flex items-center gap-1 opacity-0 group-hover:opacity-100 transform translate-x-[-4px] group-hover:translate-x-0 transition-all duration-500">
                  Go to {card.title} <ArrowRight class="w-3 h-3" />
                </div>
              {/if}
            </div>
          </a>
        {/each}
      </div>
    </div>
  </div>
