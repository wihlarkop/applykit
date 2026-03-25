<script lang="ts">
  import { page } from '$app/state';
  import ProfileSwitcher from '$lib/components/ProfileSwitcher.svelte';
  import SettingsButton from '$lib/components/SettingsButton.svelte';
  import ThemeToggle from '$lib/components/ThemeToggle.svelte';
  import Toaster from '$lib/components/Toaster.svelte';
  import { themeState } from '$lib/theme.svelte';
  import { Menu, X, Zap } from '@lucide/svelte';
  import '../app.css';

  let { data, children } = $props();
  const isOnboarded = $derived(data.isOnboarded);
  let mobileMenuOpen = $state(false);

  function navClass(href: string) {
    return `px-3 py-1.5 rounded-md text-sm transition-colors ${
      page.url.pathname === href
        ? 'bg-accent text-accent-foreground font-medium'
        : 'text-muted-foreground hover:text-foreground hover:bg-accent/50'
    }`;
  }

  function mobileNavClass(href: string) {
    return `flex items-center gap-2 px-4 py-3 text-sm transition-colors border-b border-border/50 last:border-0 ${
      page.url.pathname === href
        ? 'bg-accent text-accent-foreground font-medium'
        : 'text-foreground hover:bg-accent/50'
    }`;
  }

  // Close mobile menu on route change
  $effect(() => {
    page.url.pathname;
    mobileMenuOpen = false;
  });

  // Dark mode effect
  $effect(() => {
    const isDark = themeState.current === 'dark';
    document.documentElement.classList.toggle('dark', isDark);
    localStorage.setItem('theme', themeState.current);
  });
</script>

<div class="min-h-screen flex flex-col bg-muted/40">
  <header class="sticky top-0 z-60 border-b bg-card">
    <div class="mx-auto max-w-5xl px-4 py-3 flex items-center justify-between gap-3">
      <!-- Left: logo + desktop nav -->
      <div class="flex items-center gap-4 min-w-0">
        <a
          href={isOnboarded ? '/' : '/onboarding'}
          class="font-bold text-lg tracking-tight hover:text-primary transition-colors shrink-0"
        >ApplyKit</a>

        {#if isOnboarded}
          <!-- Desktop nav — hidden on mobile -->
          <nav class="hidden md:flex items-center gap-1 animate-in fade-in slide-in-from-left-2 duration-500">
            <a href="/" class={navClass('/')}>Dashboard</a>
            <span class="w-px h-4 bg-border mx-2 shrink-0"></span>
            <a href="/cover-letter" class={navClass('/cover-letter')}>Cover Letter</a>
            <a href="/generate" class={navClass('/generate')}>Generate CV</a>
            <a href="/smart-apply" class="{navClass('/smart-apply')} flex items-center gap-1.5">
              <Zap class="w-3.5 h-3.5" />
              Smart Apply
            </a>
            <span class="w-px h-4 bg-border mx-2 shrink-0"></span>
            <a href="/history" class={navClass('/history')}>History</a>
            <a href="/tracker" class={navClass('/tracker')}>Tracker</a>
          </nav>
        {/if}
      </div>

      <!-- Right: controls + mobile hamburger -->
      <div class="flex items-center gap-2 shrink-0">
        {#if isOnboarded}
          <ProfileSwitcher />
          <ThemeToggle />
          <SettingsButton />
          <!-- Hamburger — visible on mobile only -->
          <button
            onclick={() => mobileMenuOpen = !mobileMenuOpen}
            class="md:hidden flex items-center justify-center w-8 h-8 rounded-md hover:bg-accent transition-colors"
            aria-label="Toggle menu"
          >
            {#if mobileMenuOpen}
              <X class="w-4.5 h-4.5" />
            {:else}
              <Menu class="w-4.5 h-4.5" />
            {/if}
          </button>
        {/if}
      </div>
    </div>

    <!-- Mobile menu dropdown -->
    {#if isOnboarded && mobileMenuOpen}
      <div class="md:hidden border-t border-border bg-card animate-in slide-in-from-top-2 duration-200">
        <nav class="mx-auto max-w-5xl">
          <a href="/" class={mobileNavClass('/')}>Dashboard</a>
          <a href="/cover-letter" class={mobileNavClass('/cover-letter')}>Cover Letter</a>
          <a href="/generate" class={mobileNavClass('/generate')}>Generate CV</a>
          <a href="/smart-apply" class="{mobileNavClass('/smart-apply')} gap-2">
            <Zap class="w-3.5 h-3.5 text-primary" />
            Smart Apply
          </a>
          <a href="/history" class={mobileNavClass('/history')}>History</a>
          <a href="/tracker" class={mobileNavClass('/tracker')}>Tracker</a>
        </nav>
      </div>
    {/if}
  </header>

  <main class="flex-1 mx-auto w-full max-w-5xl px-4 py-8">
    {@render children()}
  </main>

  <Toaster />
</div>
