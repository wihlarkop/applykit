<script lang="ts">
	import { activeProfile } from '$lib/activeProfile.svelte';
	import { Button } from '$lib/components/ui/button';
	import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '$lib/components/ui/card';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import { profiles } from '$lib/profiles.svelte';
	import { ArrowRight, FileText, Lock, Mail, Sparkles, User } from '@lucide/svelte';

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
  ];
    const displayedCards = $derived(
      cards
        .filter((card) => !(isOnboarded && card.title === 'Import CV'))
        .map((card, index) => ({ ...card, displayStep: index + 1 }))
    );
  </script>

  <div class="space-y-10 pb-10">
    <div class="relative overflow-hidden rounded-3xl bg-linear-to-br from-primary/10 via-background to-secondary/10 p-8 sm:p-12 border shadow-sm">
      <div class="relative z-10 max-w-2xl">
        <div class="inline-flex items-center rounded-full border bg-background/50 px-3 py-1 text-sm font-medium mb-6 backdrop-blur-sm">
          <Sparkles class="mr-2 h-4 w-4 text-primary" />
          AI-Powered Application Toolkit
        </div>
        <h1 class="text-4xl sm:text-5xl font-extrabold tracking-tight mb-4 text-foreground">
          {#if isOnboarded === undefined}
            <Skeleton class="h-12 w-64 rounded-xl" />
          {:else if isOnboarded && (profile?.name || profile?.label)}
            Ready for the next role, <span class="text-transparent bg-clip-text bg-linear-to-r from-primary to-purple-500">{profile.name || profile.label}</span>?
          {:else}
            Welcome to <span class="text-transparent bg-clip-text bg-linear-to-r from-primary to-purple-500">ApplyKit</span>
          {/if}
        </h1>
        <p class="text-lg text-muted-foreground mb-8 leading-relaxed">
          {#if isOnboarded}
            Your profile is ready. Use our AI tools to tailor your application for any job in seconds.
          {:else}
            Your self-hosted, local-first CV and cover letter generator.
            Keep your data private while leveraging AI to land your dream job.
          {/if}
        </p>
        <div class="flex flex-wrap gap-4">
          {#if !isOnboarded}
            <Button href="/onboarding" size="lg" class="rounded-full shadow-md">
              Get Started
              <ArrowRight class="ml-2 h-4 w-4" />
            </Button>
            <Button href="/onboarding" variant="outline" size="lg" class="rounded-full bg-background/50 backdrop-blur-sm">
              Import Existing CV
            </Button>
          {:else}
            <Button href="/generate" size="lg" class="rounded-full shadow-md">
              <Sparkles class="mr-2 h-4 w-4" />
              Generate ATS CV
            </Button>
            <Button href="/cover-letter" variant="outline" size="lg" class="rounded-full bg-background/50 backdrop-blur-sm">
              <Mail class="mr-2 h-4 w-4" />
              Write Cover Letter
            </Button>
          {/if}
        </div>
      </div>
      <!-- Decorative background elements -->
      <div class="absolute -right-20 -top-20 h-75 w-75 rounded-full bg-primary/20 blur-[80px] pointer-events-none"></div>
      <div class="absolute -bottom-32 left-1/2 h-62.5 w-100 -translate-x-1/2 rounded-full bg-purple-500/20 blur-[80px] pointer-events-none"></div>
    </div>

    <div>
      <h2 class="text-2xl font-bold tracking-tight mb-6 flex items-center gap-2">
        <ArrowRight class="w-6 h-6 text-primary" />
        Your Application Workflow
      </h2>
      <div class="grid gap-6 sm:grid-cols-2 {displayedCards.length === 4 ? 'lg:grid-cols-4' : 'lg:grid-cols-3'}">
        {#each displayedCards as card}
          {@const isRestricted = !isOnboarded && card.step > 2}
          <Card class="relative overflow-hidden group {restrictedCardClass(isRestricted)} transition-all duration-300 bg-card">
            <div class="absolute top-0 right-0 w-24 h-24 bg-linear-to-b from-primary/5 to-transparent rounded-bl-full pointer-events-none z-0"></div>

            <CardHeader class="relative z-10 pb-4">
              <div class="flex items-start justify-between mb-4">
                <div class="flex items-center justify-center w-12 h-12 rounded-xl {card.bg} {card.color} shadow-sm {restrictedIconClass(isRestricted)} transition-transform duration-300">
                  <card.icon class="w-6 h-6" />
                </div>
                <span class="text-4xl font-black text-muted/30 group-hover:text-primary/10 transition-colors">
                  {card.displayStep}
                </span>
              </div>
            <CardTitle class="text-xl mb-1 flex items-center gap-2">
              {card.title}
              {#if isRestricted}
                <Lock class="w-4 h-4 text-muted-foreground" />
              {/if}
            </CardTitle>
            <CardDescription class="text-sm line-clamp-2 min-h-10">
              {#if isRestricted}
                Complete your profile setup first to unlock this feature.
              {:else}
                {card.description}
              {/if}
            </CardDescription>
            {#if isOnboarded && isActiveEmpty && (card.href === '/generate' || card.href === '/cover-letter')}
              <span class="inline-flex items-center gap-1 text-xs text-yellow-600 dark:text-yellow-400 font-medium mt-1"><span>⚠</span> Profile is empty</span>
            {/if}
          </CardHeader>
          <CardContent class="relative z-10">
            <Button
              href={isRestricted ? undefined : card.href}
              variant="outline"
              disabled={isRestricted}
              class="w-full transition-all duration-300 {restrictedBtnClass(isRestricted)}"
            >
              {#if isRestricted}
                Locked
              {:else}
                {card.action}
              {/if}
            </Button>
          </CardContent>
        </Card>
      {/each}
    </div>
  </div>
</div>
