<script lang="ts">
  import { page } from '$app/stores';
  import ProfileSwitcher from '$lib/components/ProfileSwitcher.svelte';
  import SettingsButton from '$lib/components/SettingsButton.svelte';
  import ThemeToggle from '$lib/components/ThemeToggle.svelte';
  import Toaster from '$lib/components/Toaster.svelte';
  import { themeState } from '$lib/theme.svelte';
  import '../app.css';

  let { data, children } = $props();
  const isOnboarded = $derived(data.isOnboarded);

  function navClass(href: string) {
    return `px-3 py-1.5 rounded-md text-sm transition-colors ${
      $page.url.pathname === href
        ? 'bg-accent text-accent-foreground font-medium'
        : 'text-muted-foreground hover:text-foreground hover:bg-accent/50'
    }`;
  }

  // Dark mode effect
  $effect(() => {
    if (typeof document !== 'undefined') {
      const isDark = themeState.current === 'dark';
      document.documentElement.classList.toggle('dark', isDark);
      localStorage.setItem('theme', themeState.current);
    }
  });
</script>

<div class="min-h-screen flex flex-col bg-muted/40">
  <header class="sticky top-0 z-60 border-b bg-card">
    <div class="mx-auto max-w-5xl px-4 py-3 flex items-center justify-between">
      <div class="flex items-center gap-4 min-w-0">
        <a
          href={isOnboarded ? '/' : '/onboarding'}
          class="font-bold text-lg tracking-tight hover:text-primary transition-colors shrink-0"
        >ApplyKit</a>

        {#if isOnboarded}
          <nav class="flex items-center gap-1 animate-in fade-in slide-in-from-left-2 duration-500 overflow-x-auto">
            <a href="/" class={navClass('/')}>Dashboard</a>
            <span class="w-px h-4 bg-border mx-2 shrink-0"></span>
            <a href="/cover-letter" class={navClass('/cover-letter')}>Cover Letter</a>
            <a href="/generate" class={navClass('/generate')}>Generate CV</a>
            <span class="w-px h-4 bg-border mx-2 shrink-0"></span>
            <a href="/history" class={navClass('/history')}>History</a>
            <a href="/tracker" class={navClass('/tracker')}>Tracker</a>
          </nav>
        {/if}
      </div>

      {#if isOnboarded}
        <div class="flex items-center gap-3 animate-in fade-in duration-500 shrink-0">
          <ProfileSwitcher />
          <ThemeToggle />
          <SettingsButton />
        </div>
      {/if}
    </div>
  </header>

  <main class="flex-1 mx-auto w-full max-w-5xl px-4 py-8">
    {@render children()}
  </main>

  <Toaster />
</div>
