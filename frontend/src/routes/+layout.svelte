<script lang="ts">
  import { goto } from '$app/navigation';
  import { page } from '$app/state';
  import { logoutOwner } from '$lib/auth-api';
  import { authState } from '$lib/auth-state.svelte';
  import ProfileSwitcher from '$lib/components/ProfileSwitcher.svelte';
  import SessionExpiryBanner from '$lib/components/SessionExpiryBanner.svelte';
  import SettingsButton from '$lib/components/SettingsButton.svelte';
  import SettingsNav from '$lib/components/SettingsNav.svelte';
  import ThemeToggle from '$lib/components/ThemeToggle.svelte';
  import Toaster from '$lib/components/Toaster.svelte';
  import { themeState } from '$lib/theme.svelte';
  import { toastState } from '$lib/toast.svelte';
  import { LogOut, Menu, X, Zap } from '@lucide/svelte';
  import '../app.css';

  let { data, children } = $props();
  const isOnboarded = $derived(data.isOnboarded);
  const isAuthRoute = $derived(data.isAuthRoute);
  const onSettings = $derived(page.url.pathname.startsWith('/settings'));
  let mobileMenuOpen = $state(false);
  let signingOut = $state(false);

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

  async function signOut() {
    if (signingOut) return;
    signingOut = true;
    try {
      await logoutOwner();
      authState.clearSession();
      await goto('/login');
    } catch (error) {
      toastState.error(error instanceof Error ? error.message : 'Could not sign out.');
    } finally {
      signingOut = false;
    }
  }

  $effect(() => {
    page.url.pathname;
    mobileMenuOpen = false;
  });

  $effect(() => {
    const isDark = themeState.current === 'dark';
    document.documentElement.classList.toggle('dark', isDark);
    localStorage.setItem('theme', themeState.current);
  });

  $effect(() => {
    if (
      !isAuthRoute
      && authState.authMode === 'password'
      && !authState.authenticated
      && !authState.checking
    ) {
      const returnTo = encodeURIComponent(`${page.url.pathname}${page.url.search}`);
      void goto(`/login?returnTo=${returnTo}`);
    }
  });
</script>

{#if isAuthRoute}
  {@render children()}
  <Toaster />
{:else}
  <div class="min-h-screen flex flex-col bg-muted/40">
    <header class="sticky top-0 z-60 border-b bg-card">
      <div class="mx-auto max-w-5xl px-4 py-3 flex items-center justify-between gap-3">
        <div class="flex items-center gap-4 min-w-0">
          <a
            href={isOnboarded ? '/' : '/onboarding'}
            class="font-bold text-lg tracking-tight hover:text-primary transition-colors shrink-0"
          >ApplyKit</a>

          {#if isOnboarded}
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

        <div class="flex items-center gap-2 shrink-0">
          {#if isOnboarded}
            <ProfileSwitcher />
            <ThemeToggle />
            <SettingsButton />
            {#if authState.authMode === 'password'}
              <button
                type="button"
                onclick={signOut}
                disabled={signingOut}
                class="hidden md:inline-flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-sm text-muted-foreground transition-colors hover:bg-accent hover:text-foreground disabled:opacity-50"
              >
                <LogOut class="h-4 w-4" />Sign out
              </button>
            {/if}
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
          {:else}
            <ThemeToggle />
            {#if authState.authMode === 'password'}
              <button
                type="button"
                onclick={signOut}
                disabled={signingOut}
                class="inline-flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-sm text-muted-foreground transition-colors hover:bg-accent hover:text-foreground disabled:opacity-50"
              >
                <LogOut class="h-4 w-4" />Sign out
              </button>
            {/if}
          {/if}
        </div>
      </div>

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
            {#if authState.authMode === 'password'}
              <button
                type="button"
                onclick={signOut}
                disabled={signingOut}
                class="flex w-full items-center gap-2 px-4 py-3 text-left text-sm text-foreground transition-colors hover:bg-accent/50 disabled:opacity-50"
              >
                <LogOut class="h-4 w-4" />Sign out
              </button>
            {/if}
          </nav>
        </div>
      {/if}
    </header>

    {#if authState.authMode === 'password' && authState.authenticated}
      <SessionExpiryBanner />
    {/if}

    <main class="flex-1 mx-auto w-full max-w-5xl px-4 py-8">
      {#if onSettings}
        <div class="mb-6"><SettingsNav /></div>
      {/if}
      {@render children()}
    </main>

    <Toaster />
  </div>
{/if}
